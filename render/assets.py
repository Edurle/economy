"""Procedural asset generation: 16x16 pixel-art tiles and entity sprites.

All graphics are generated at startup and cached as pygame Surfaces.
No external image files required.
"""

import numpy as np
import pygame

from config import TILE_SIZE, TerrainType, SpeciesKind, Role, TERRAIN_COLORS


def generate_assets() -> dict:
    """Generate and return all tile/sprite assets."""
    return {
        "terrain": _gen_terrain_tiles(),
        "grass_overlay": _gen_grass_overlays(),
        "animals": _gen_animal_sprites(),
        "animals_diseased": _gen_animal_sprites_diseased(),
        "humans": _gen_human_sprites(),
        "camp": _draw_camp(),
        "fire_frames": _gen_fire_frames(),
        "rain_drop": _gen_rain_drop(),
        "snow_flake": _gen_snow_flake(),
        "deposits": _gen_deposit_sprites(),
    }


# ============================================================
# Terrain Tiles (16x16 each)
# ============================================================
def _gen_terrain_tiles() -> dict:
    tiles = {}
    rng = np.random.RandomState(42)

    for t_type, base_color in TERRAIN_COLORS.items():
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
        surf.fill(base_color)

        if t_type == TerrainType.GRASSLAND:
            _texture_grass(surf, rng)
        elif t_type == TerrainType.FOREST:
            _texture_forest(surf, rng)
        elif t_type == TerrainType.WATER:
            _texture_water(surf, rng)
        elif t_type == TerrainType.DESERT:
            _texture_desert(surf, rng)
        elif t_type == TerrainType.MOUNTAIN:
            _texture_mountain(surf, rng)
        elif t_type == TerrainType.SNOW:
            _texture_snow(surf, rng)

        tiles[t_type] = surf.convert()

    return tiles


def _tex_pixel(surf, x, y, color):
    if 0 <= x < TILE_SIZE and 0 <= y < TILE_SIZE:
        surf.set_at((x, y), color)


def _texture_grass(surf, rng):
    c = TERRAIN_COLORS[TerrainType.GRASSLAND]
    dark = (max(0, c[0]-30), max(0, c[1]-25), max(0, c[2]-20))
    light = (min(255, c[0]+20), min(255, c[1]+25), min(255, c[2]+15))
    for _ in range(20):
        x, y = rng.randint(0, TILE_SIZE), rng.randint(0, TILE_SIZE)
        col = dark if rng.random() < 0.5 else light
        _tex_pixel(surf, x, y, col)
    # A few darker grass blades
    for _ in range(5):
        x = rng.randint(1, TILE_SIZE - 1)
        y = rng.randint(1, TILE_SIZE - 2)
        _tex_pixel(surf, x, y, dark)
        _tex_pixel(surf, x, y + 1, dark)


def _texture_forest(surf, rng):
    c = TERRAIN_COLORS[TerrainType.FOREST]
    dark = (max(0, c[0]-15), max(0, c[1]-20), max(0, c[2]-10))
    trunk = (80, 55, 35)
    # Canopy bumps
    for cx, cy in [(5, 5), (11, 4), (8, 10), (4, 11), (12, 11)]:
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx*dx + dy*dy <= 4:
                    _tex_pixel(surf, cx+dx, cy+dy, dark)
    # Tree trunks
    for _ in range(3):
        x = rng.randint(2, TILE_SIZE - 3)
        _tex_pixel(surf, x, 13, trunk)
        _tex_pixel(surf, x, 14, trunk)


def _texture_water(surf, rng):
    c = TERRAIN_COLORS[TerrainType.WATER]
    light = (min(255, c[0]+25), min(255, c[1]+25), min(255, c[2]+15))
    # Wave lines
    for y in [3, 7, 11]:
        for x in range(1, TILE_SIZE - 3):
            if rng.random() < 0.5:
                _tex_pixel(surf, x, y, light)
                _tex_pixel(surf, x + 1, y, light)


def _texture_desert(surf, rng):
    c = TERRAIN_COLORS[TerrainType.DESERT]
    dark = (max(0, c[0]-20), max(0, c[1]-20), max(0, c[2]-15))
    light = (min(255, c[0]+10), min(255, c[1]+10), min(255, c[2]+5))
    for _ in range(15):
        x, y = rng.randint(0, TILE_SIZE), rng.randint(0, TILE_SIZE)
        col = dark if rng.random() < 0.4 else light
        _tex_pixel(surf, x, y, col)


def _texture_mountain(surf, rng):
    c = TERRAIN_COLORS[TerrainType.MOUNTAIN]
    dark = (max(0, c[0]-25), max(0, c[1]-20), max(0, c[2]-20))
    light = (min(255, c[0]+20), min(255, c[1]+20), min(255, c[2]+20))
    # Rocky triangle shape
    peak_x, peak_y = 8, 3
    for dy in range(6):
        half_w = dy + 1
        y = peak_y + dy
        for dx in range(-half_w, half_w + 1):
            x = peak_x + dx
            col = light if dy <= 1 else dark
            _tex_pixel(surf, x, y, col)
    # Scattered rocks
    for _ in range(6):
        x, y = rng.randint(0, TILE_SIZE), rng.randint(8, TILE_SIZE)
        _tex_pixel(surf, x, y, dark)


def _texture_snow(surf, rng):
    c = TERRAIN_COLORS[TerrainType.SNOW]
    sparkle = (255, 255, 255)
    shadow = (200, 215, 230)
    for _ in range(10):
        x, y = rng.randint(0, TILE_SIZE), rng.randint(0, TILE_SIZE)
        col = sparkle if rng.random() < 0.5 else shadow
        _tex_pixel(surf, x, y, col)


# ============================================================
# Grass Level Overlays (5 stages)
# ============================================================
def _gen_grass_overlays() -> list:
    """Semi-transparent green overlays indicating grass density."""
    overlays = []
    for level in range(5):
        alpha = int(20 + level * 40)  # 20, 60, 100, 140, 180
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        surf.fill((30, 120, 30, alpha))
        # Add a few brighter grass blade pixels at higher levels
        if level >= 2:
            rng = np.random.RandomState(level * 7)
            bright = (60, 180, 60, alpha)
            for _ in range(level * 3):
                x = rng.randint(0, TILE_SIZE)
                y = rng.randint(0, TILE_SIZE)
                surf.set_at((x, y), bright)
        overlays.append(surf.convert_alpha())
    return overlays


# ============================================================
# Animal Sprites (16x16 each)
# ============================================================
def _gen_animal_sprites() -> dict:
    sprites = {}
    sprites[SpeciesKind.RABBIT] = _draw_rabbit()
    sprites[SpeciesKind.SHEEP] = _draw_sheep()
    sprites[SpeciesKind.DEER] = _draw_deer()
    sprites[SpeciesKind.FOX] = _draw_fox()
    sprites[SpeciesKind.WOLF] = _draw_wolf()
    return sprites


def _draw_rabbit() -> pygame.Surface:
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    gray = (200, 200, 200)
    dark = (150, 150, 150)
    # Ears
    pygame.draw.line(s, gray, (6, 2), (6, 6), 1)
    pygame.draw.line(s, gray, (9, 2), (9, 6), 1)
    # Body (small oval)
    pygame.draw.circle(s, gray, (8, 10), 4)
    # Eye
    s.set_at((9, 8), dark)
    return s.convert_alpha()


def _draw_sheep() -> pygame.Surface:
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    white = (240, 240, 240)
    dark = (180, 180, 180)
    # Fluffy body
    for cx, cy in [(6, 9), (10, 9), (8, 7), (8, 11)]:
        pygame.draw.circle(s, white, (cx, cy), 3)
    # Head
    pygame.draw.circle(s, dark, (11, 8), 2)
    return s.convert_alpha()


def _draw_deer() -> pygame.Surface:
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    brown = (140, 90, 50)
    dark = (100, 65, 35)
    # Body
    pygame.draw.ellipse(s, brown, (4, 7, 9, 5))
    # Antlers
    pygame.draw.line(s, dark, (6, 6), (4, 3), 1)
    pygame.draw.line(s, dark, (6, 6), (7, 3), 1)
    pygame.draw.line(s, dark, (10, 6), (9, 3), 1)
    pygame.draw.line(s, dark, (10, 6), (12, 3), 1)
    # Legs
    for lx in [5, 7, 10, 12]:
        pygame.draw.line(s, dark, (lx, 11), (lx, 14), 1)
    return s.convert_alpha()


def _draw_fox() -> pygame.Surface:
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    orange = (230, 120, 40)
    dark = (180, 80, 20)
    white = (255, 200, 150)
    # Body (pointed)
    pygame.draw.ellipse(s, orange, (3, 7, 10, 5))
    # Head
    pygame.draw.circle(s, orange, (11, 9), 2)
    # Ear
    pygame.draw.line(s, dark, (11, 7), (11, 5), 1)
    pygame.draw.line(s, dark, (12, 7), (13, 5), 1)
    # Tail tip
    s.set_at((3, 9), white)
    return s.convert_alpha()


def _draw_wolf() -> pygame.Surface:
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    dark_red = (150, 40, 40)
    gray = (100, 80, 80)
    black = (60, 40, 40)
    # Body (elongated)
    pygame.draw.ellipse(s, dark_red, (2, 7, 12, 5))
    # Head
    pygame.draw.circle(s, dark_red, (12, 9), 2)
    # Ears (pointed)
    pygame.draw.line(s, black, (12, 7), (11, 4), 1)
    pygame.draw.line(s, black, (13, 7), (14, 4), 1)
    # Eye
    s.set_at((12, 8), (255, 200, 0))
    # Tail
    pygame.draw.line(s, gray, (2, 9), (0, 8), 2)
    return s.convert_alpha()


def _gen_animal_sprites_diseased() -> dict:
    """Same animal sprites with purple disease tint."""
    sprites = {}
    base = _gen_animal_sprites()
    for kind, surf in base.items():
        tinted = surf.copy()
        tinted.fill((160, 0, 180, 0), special_flags=pygame.BLEND_RGBA_ADD)
        # Overlay purple ring
        pygame.draw.circle(tinted, (180, 0, 200, 120), (8, 8), 7, 1)
        sprites[kind] = tinted.convert_alpha()
    return sprites


# ============================================================
# Human Sprites (16x16 each, per role)
# ============================================================
def _gen_human_sprites() -> dict:
    sprites = {}
    for role in Role:
        sprites[int(role)] = _draw_human(role)
    return sprites


def _draw_human(role: int = Role.HUNTER) -> pygame.Surface:
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    skin = (220, 180, 140)
    tunic = (140, 110, 70)
    # Role accent colors
    accents = {Role.HUNTER: (200, 50, 50), Role.GATHERER: (50, 160, 50), Role.BUILDER: (50, 80, 200), Role.MINER: (220, 160, 30), Role.SCHOLAR: (160, 80, 200)}
    accent = accents.get(role, (200, 50, 50))
    # Head
    pygame.draw.circle(s, skin, (8, 4), 2)
    # Body (tunic)
    pygame.draw.rect(s, tunic, (6, 6, 5, 5))
    # Accent stripe (role indicator)
    pygame.draw.rect(s, accent, (6, 7, 5, 1))
    # Arms
    pygame.draw.line(s, skin, (5, 8), (5, 10), 1)
    pygame.draw.line(s, skin, (11, 8), (11, 10), 1)
    # Legs
    pygame.draw.line(s, tunic, (7, 11), (7, 14), 1)
    pygame.draw.line(s, tunic, (9, 11), (9, 14), 1)
    return s.convert_alpha()


def _draw_camp() -> pygame.Surface:
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    tent_color = (160, 120, 70)
    tent_dark = (110, 80, 45)
    fire_orange = (255, 140, 0)
    fire_yellow = (255, 220, 0)
    # Tent (triangle)
    pygame.draw.polygon(s, tent_color, [(3, 13), (8, 4), (13, 13)])
    pygame.draw.polygon(s, tent_dark, [(3, 13), (8, 4), (13, 13)], 1)
    # Tent entrance
    pygame.draw.polygon(s, tent_dark, [(6, 13), (8, 9), (10, 13)])
    # Campfire
    pygame.draw.circle(s, fire_orange, (12, 12), 2)
    s.set_at((12, 11), fire_yellow)
    s.set_at((11, 12), fire_yellow)
    return s.convert_alpha()


# ============================================================
# Effect Sprites
# ============================================================
def _gen_fire_frames() -> list:
    """Two animation frames of a fire tile."""
    frames = []
    rng = np.random.RandomState(99)
    for frame in range(2):
        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        # Base glow
        pygame.draw.circle(s, (255, 80, 0, 180), (8, 10), 5)
        pygame.draw.circle(s, (255, 160, 0, 140), (8, 9), 3)
        # Flames
        offsets = [(8, 4), (5, 6), (11, 6)]
        for fx, fy in offsets:
            fy2 = fy - frame
            pygame.draw.circle(s, (255, 200, 0, 200), (fx, fy2), 2)
            s.set_at((fx, fy2 - 1), (255, 255, 150, 255))
        frames.append(s.convert_alpha())
    return frames


def _gen_rain_drop() -> pygame.Surface:
    """A single rain drop streak."""
    s = pygame.Surface((3, 6), pygame.SRCALPHA)
    pygame.draw.line(s, (100, 150, 220, 180), (2, 0), (0, 5), 1)
    return s.convert_alpha()


def _gen_snow_flake() -> pygame.Surface:
    """A single small snowflake."""
    s = pygame.Surface((4, 4), pygame.SRCALPHA)
    pygame.draw.circle(s, (240, 245, 255, 200), (2, 2), 1)
    return s.convert_alpha()


# ============================================================
# Mineral Deposit Sprites (16x16 each, per deposit type)
# ============================================================
def _gen_deposit_sprites() -> dict:
    """Generate crystal/ore overlay sprites for each depositable resource."""
    from resources import DEPOSITABLE, RESOURCE_REGISTRY
    sprites = {}
    for idx, key in enumerate(DEPOSITABLE):
        rdef = RESOURCE_REGISTRY[key]
        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        color = rdef.color
        dark = tuple(max(0, c - 50) for c in color)
        light = tuple(min(255, c + 40) for c in color)
        # Draw 3-4 crystal clusters scattered on the tile
        spots = [(4, 5), (10, 4), (7, 10), (11, 11)]
        for sx, sy in spots:
            # Crystal shape (small diamond)
            sz = 2
            pts = [(sx, sy - sz), (sx + sz, sy), (sx, sy + sz), (sx - sz, sy)]
            pygame.draw.polygon(s, color, pts)
            pygame.draw.polygon(s, dark, pts, 1)
            # Highlight pixel
            s.set_at((sx, sy - 1), light)
        sprites[idx] = s.convert_alpha()
    return sprites
