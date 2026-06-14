"""World generation: Perlin-noise based natural terrain distribution."""

import numpy as np

try:
    from noise import snoise2
    HAS_NOISE = True
except ImportError:
    HAS_NOISE = False

from config import (
    GRID_W, GRID_H, TerrainType, GRASS_MAX,
    Role, TRIBE_INIT_HUNTERS, TRIBE_INIT_GATHERERS, TRIBE_INIT_BUILDERS,
    TRIBE_INIT_MINERS, TRIBE_INIT_SCHOLARS,
)
from ecs.world import World
from ecs.components import SpeciesKind
from resources import DEPOSIT_CONFIG, DEPOSITABLE, depositable_index


def _smooth_noise_fallback(x, y, seed=0):
    """Fallback pseudo-noise if the `noise` package is unavailable."""
    n = int(x * 374761393 + y * 668265263 + seed * 982451653)
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF


def _noise2d(x, y, seed=0, scale=0.06):
    """Sample 2-D noise in [-1, 1] range."""
    if HAS_NOISE:
        return snoise2(x * scale + seed, y * scale + seed, octaves=4)
    else:
        v = _smooth_noise_fallback(x * scale, y * scale, seed)
        return v * 2 - 1


def generate_terrain(world: World, seed: int = 42) -> None:
    """Fill world.terrain with natural terrain using layered noise."""
    elevation = np.zeros((GRID_W, GRID_H), dtype=np.float32)
    moisture = np.zeros((GRID_W, GRID_H), dtype=np.float32)

    for x in range(GRID_W):
        for y in range(GRID_H):
            # Large-scale elevation (scale adjusted for 64x64 grid)
            e = (_noise2d(x, y, seed=seed, scale=0.08) +
                 0.5 * _noise2d(x, y, seed=seed + 1, scale=0.16) +
                 0.25 * _noise2d(x, y, seed=seed + 2, scale=0.32))
            elevation[x, y] = e

            # Moisture / humidity
            m = (_noise2d(x, y, seed=seed + 100, scale=0.1) +
                 0.5 * _noise2d(x, y, seed=seed + 101, scale=0.2))
            moisture[x, y] = m

    # Normalise
    e_min, e_max = elevation.min(), elevation.max()
    elevation = (elevation - e_min) / (e_max - e_min + 1e-9)
    m_min, m_max = moisture.min(), moisture.max()
    moisture = (moisture - m_min) / (m_max - m_min + 1e-9)

    for x in range(GRID_W):
        for y in range(GRID_H):
            e = elevation[x, y]
            m = moisture[x, y]
            if e < 0.22:
                world.terrain[x, y] = TerrainType.WATER
            elif e > 0.82:
                world.terrain[x, y] = TerrainType.MOUNTAIN
            elif e > 0.75:
                world.terrain[x, y] = TerrainType.MOUNTAIN
            elif m < 0.28 and e > 0.4:
                world.terrain[x, y] = TerrainType.DESERT
            elif m > 0.6 and 0.3 < e < 0.75:
                world.terrain[x, y] = TerrainType.FOREST
            else:
                world.terrain[x, y] = TerrainType.GRASSLAND

    # Smooth out single-cell islands of water (optional simple cleanup)
    _smooth_water(world)

    # Generate mineral deposits on mountain tiles
    _generate_deposits(world)

    # Initialise grass on grassland and forest tiles
    for x in range(GRID_W):
        for y in range(GRID_H):
            t = world.terrain[x, y]
            if t == TerrainType.GRASSLAND:
                world.grass_level[x, y] = np.random.uniform(30, GRASS_MAX)
            elif t == TerrainType.FOREST:
                world.grass_level[x, y] = np.random.uniform(40, GRASS_MAX)


def _generate_deposits(world: World) -> None:
    """Assign mineral deposits to mountain tiles based on DEPOSIT_CONFIG."""
    keys = list(DEPOSIT_CONFIG.keys())
    for x in range(GRID_W):
        for y in range(GRID_H):
            if world.terrain[x, y] != TerrainType.MOUNTAIN:
                continue
            roll = np.random.random()
            cumulative = 0.0
            for res_key in keys:
                cfg = DEPOSIT_CONFIG[res_key]
                cumulative += cfg["prob"]
                if roll < cumulative:
                    idx = depositable_index(res_key)
                    world.deposits[x, y] = idx
                    lo, hi = cfg["amount"]
                    world.deposit_amount[x, y] = np.random.uniform(lo, hi)
                    break


def _smooth_water(world: World) -> None:
    """Remove tiny 1-cell water puddles that are likely noise artifacts."""
    water = world.terrain == TerrainType.WATER
    for x in range(1, GRID_W - 1):
        for y in range(1, GRID_H - 1):
            if not water[x, y]:
                continue
            neighbours = sum(int(water[nx, ny])
                             for nx, ny in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)))
            if neighbours == 0:
                world.terrain[x, y] = TerrainType.GRASSLAND


def populate_initial(world: World) -> None:
    """Scatter initial populations. Predators are clustered so they can find mates."""
    # Herbivores: scattered
    herb_counts = {
        SpeciesKind.RABBIT: 40,
        SpeciesKind.SHEEP: 30,
        SpeciesKind.DEER: 12,
    }
    for kind, n in herb_counts.items():
        placed = 0
        attempts = 0
        while placed < n and attempts < n * 50:
            attempts += 1
            x = np.random.randint(0, GRID_W)
            y = np.random.randint(0, GRID_H)
            if world.is_walkable(x, y, kind):
                world.spawn_animal(kind, x, y)
                placed += 1

    # Predators: clustered in groups so they can find mates
    predator_clusters = [
        (SpeciesKind.FOX, 3, 5),     # 3 groups of 5 foxes = 15
        (SpeciesKind.WOLF, 2, 5),    # 2 groups of 5 wolves = 10
    ]
    for kind, n_clusters, group_size in predator_clusters:
        placed = 0
        for _ in range(n_clusters):
            # Pick a cluster center
            for _attempt in range(50):
                cx = np.random.randint(5, GRID_W - 5)
                cy = np.random.randint(5, GRID_H - 5)
                if world.is_walkable(cx, cy, kind):
                    break
            # Place a cluster of animals near (cx, cy)
            count = 0
            for _ in range(group_size * 10):
                if count >= group_size:
                    break
                dx = np.random.randint(-3, 4)
                dy = np.random.randint(-3, 4)
                x, y = cx + dx, cy + dy
                if world.is_walkable(x, y, kind):
                    world.spawn_animal(kind, x, y)
                    count += 1
                    placed += 1

    # Human tribe: spawn camp + initial humans
    _spawn_initial_tribe(world)


def _spawn_initial_tribe(world: World) -> None:
    """Find a good camp location and spawn the initial human tribe."""
    best_x, best_y = GRID_W // 2, GRID_H // 2
    best_score = -1

    for _ in range(200):
        x = np.random.randint(4, GRID_W - 4)
        y = np.random.randint(4, GRID_H - 4)
        if world.terrain[x, y] != TerrainType.GRASSLAND:
            continue
        if (x, y) in world.camp_positions:
            continue
        # Score: near water, on grassland
        score = 0
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                nx, ny = x + dx, y + dy
                if world.in_bounds(nx, ny):
                    if world.terrain[nx, ny] == TerrainType.WATER:
                        score += 3
                    elif world.terrain[nx, ny] == TerrainType.GRASSLAND:
                        score += 1
                    elif world.terrain[nx, ny] == TerrainType.FOREST:
                        score += 2
        if score > best_score:
            best_score = score
            best_x, best_y = x, y

    camp_eid = world.spawn_camp(best_x, best_y, tribe_id=0)
    world.log_event(f"部落营地建立于 ({best_x}, {best_y})")

    role_counts = {
        Role.HUNTER: TRIBE_INIT_HUNTERS,
        Role.GATHERER: TRIBE_INIT_GATHERERS,
        Role.BUILDER: TRIBE_INIT_BUILDERS,
        Role.MINER: TRIBE_INIT_MINERS,
        Role.SCHOLAR: TRIBE_INIT_SCHOLARS,
    }
    for role, count in role_counts.items():
        for _ in range(count * 10):
            if count <= 0:
                break
            dx = np.random.randint(-2, 3)
            dy = np.random.randint(-2, 3)
            x, y = best_x + dx, best_y + dy
            if world.is_walkable(x, y, SpeciesKind.HUMAN):
                world.spawn_human(x, y, tribe_id=0, role=role, home_camp=camp_eid)
                count -= 1
