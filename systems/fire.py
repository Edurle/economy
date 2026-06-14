"""Fire system: ignition, spread, and ash buff after burning."""

import numpy as np

from config import (
    TerrainType, Season,
    FIRE_DROUGHT_TICKS, FIRE_GRASS_THRESHOLD, FIRE_IGNITE_CHANCE,
    FIRE_SPREAD_CHANCE, FIRE_DURATION_MIN, FIRE_DURATION_MAX,
    FIRE_ANIMAL_DEATH_CHANCE, FIRE_ASH_DURATION,
    FIRE_COLOR,
)
from ecs.world import World
from ecs.components import Position, Species


class FireSystem:
    DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def update(self, world: World) -> None:
        # Only fires can start in summer after prolonged drought
        can_ignite = (Season(world.season) == Season.SUMMER and
                      world.drought_timer >= FIRE_DROUGHT_TICKS)

        # Ignition (sparse — only roll dice for flammable tiles)
        if can_ignite:
            flammable = ((world.terrain == int(TerrainType.GRASSLAND)) &
                         (world.grass_level >= FIRE_GRASS_THRESHOLD) &
                         (world.fire_map == 0))
            n_flammable = int(flammable.sum())
            if n_flammable > 0:
                flammable_coords = np.argwhere(flammable)
                ignite_mask = np.random.random(n_flammable) < FIRE_IGNITE_CHANCE
                ignite_coords = flammable_coords[ignite_mask]
                if len(ignite_coords) > 0:
                    world.fire_map[ignite_coords[:, 0], ignite_coords[:, 1]] = (
                        np.random.randint(FIRE_DURATION_MIN, FIRE_DURATION_MAX + 1,
                                          size=len(ignite_coords))).astype(np.int8)
                    world.log_event("草地起火！")

        # Spread fire
        burning = world.fire_map > 0
        if burning.any():
            # Build set of burning cells
            burn_coords = np.argwhere(burning)
            for x, y in burn_coords:
                if world.fire_map[x, y] <= 0:
                    continue
                for dx, dy in self.DIRS:
                    nx, ny = x + dx, y + dy
                    if not world.in_bounds(nx, ny):
                        continue
                    if world.fire_map[nx, ny] != 0:
                        continue
                    t = world.terrain[nx, ny]
                    if t == TerrainType.GRASSLAND and world.grass_level[nx, ny] >= 20:
                        if np.random.random() < FIRE_SPREAD_CHANCE:
                            world.fire_map[nx, ny] = np.random.randint(
                                FIRE_DURATION_MIN, FIRE_DURATION_MAX + 1)

            # Kill animals on burning cells
            burning_cells = set()
            burn_coords = np.argwhere(world.fire_map > 0)
            for x, y in burn_coords:
                burning_cells.add((int(x), int(y)))

            to_kill = []
            for eid, pos, sp in world.query(Position, Species):
                if eid not in world.entities:
                    continue
                if (pos.x, pos.y) in burning_cells:
                    if np.random.random() < FIRE_ANIMAL_DEATH_CHANCE:
                        to_kill.append(eid)
            for eid in to_kill:
                world.remove_entity(eid)

            # Apply fire effects: burn grass, tick duration
            for x, y in np.argwhere(world.fire_map > 0):
                world.grass_level[x, y] = 0
                world.fire_map[x, y] -= 1
                # When fire goes out, leave ash buff
                if world.fire_map[x, y] <= 0:
                    world.ash_buff[x, y] = FIRE_ASH_DURATION

    def ignite_at(self, world: World, x: int, y: int) -> None:
        """God-mode: start a fire at a specific cell."""
        if world.terrain[x, y] == TerrainType.GRASSLAND:
            world.fire_map[x, y] = FIRE_DURATION_MAX
            world.log_event("上帝引火！")
