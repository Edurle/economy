"""Minimap: compact overview of the full world with camera viewport indicator."""

import numpy as np
import pygame

from config import (
    GRID_W, GRID_H, VIEWPORT_WIDTH, VIEWPORT_HEIGHT,
    TerrainType, SpeciesKind, SPECIES_PARAMS, TERRAIN_COLORS,
)
from ecs.world import World
from ecs.components import Position, Species


MINI_TILE = max(1, 192 // max(GRID_W, GRID_H))   # auto-scale pixels per cell
MINI_W = GRID_W * MINI_TILE
MINI_H = GRID_H * MINI_TILE
MINI_RIGHT = MINI_W + 16      # x offset for content beside minimap

# Pre-build a lookup table: terrain int -> RGB uint8 array (3,)
_LUT_SIZE = max(int(t) for t in TERRAIN_COLORS) + 1
_TERRAIN_LUT = np.zeros((_LUT_SIZE, 3), dtype=np.uint8)
for _t, _c in TERRAIN_COLORS.items():
    _TERRAIN_LUT[int(_t)] = _c


class Minimap:
    """Renders a scaled overview of the entire world."""

    def __init__(self):
        self.surface = pygame.Surface((MINI_W, MINI_H))
        self._terrain_dirty = True
        self._terrain_surf = pygame.Surface((MINI_W, MINI_H))

    def render(self, world: World, camera, panel_x: int, panel_y: int) -> pygame.Surface:
        """Render the minimap. Returns the surface."""
        # Redraw terrain only occasionally (every 30 ticks) for performance
        if world.tick % 30 == 0 or self._terrain_dirty:
            self._draw_terrain(world)
            self._terrain_dirty = False

        self.surface.blit(self._terrain_surf, (0, 0))

        # Draw animals as colored pixels
        for eid, pos, sp in world.query(Position, Species):
            if eid not in world.entities:
                continue
            mx, my = pos.x * MINI_TILE, pos.y * MINI_TILE
            color = SPECIES_PARAMS[sp.kind]["color"]
            self.surface.set_at((mx, my), color)
            if MINI_TILE > 1:
                self.surface.set_at((mx + 1, my), color)
                self.surface.set_at((mx, my + 1), color)

        # Draw camera viewport rectangle
        x0, y0 = camera.screen_to_grid(0, 0)
        x1, y1 = camera.screen_to_grid(VIEWPORT_WIDTH, VIEWPORT_HEIGHT)
        rect_x = max(0, x0) * MINI_TILE
        rect_y = max(0, y0) * MINI_TILE
        rect_w = min(GRID_W, x1) * MINI_TILE - rect_x
        rect_h = min(GRID_H, y1) * MINI_TILE - rect_y
        if rect_w > 0 and rect_h > 0:
            pygame.draw.rect(self.surface, (255, 255, 0),
                             (rect_x, rect_y, rect_w, rect_h), 1)

        return self.surface

    def screen_to_grid(self, mx: int, my: int) -> tuple[int, int]:
        """Convert minimap pixel coords to world grid coords."""
        return mx // MINI_TILE, my // MINI_TILE

    @property
    def rect(self):
        return pygame.Rect(0, 0, MINI_W, MINI_H)

    def _draw_terrain(self, world: World) -> None:
        """Draw terrain colors to the cached terrain surface (vectorized)."""
        colors = _TERRAIN_LUT[world.terrain].copy()  # (GRID_W, GRID_H, 3)

        # Darken low-grass areas on grassland/forest
        grass_mask = ((world.terrain == int(TerrainType.GRASSLAND)) |
                      (world.terrain == int(TerrainType.FOREST)))
        if grass_mask.any():
            factor = 0.4 + 0.6 * np.clip(world.grass_level.astype(np.float32) / 100.0, 0, 1)
            for c in range(3):
                layer = colors[:, :, c].astype(np.float32)
                layer[grass_mask] *= factor[grass_mask]
                colors[:, :, c] = layer.astype(np.uint8)

        if MINI_TILE > 1:
            colors = np.repeat(np.repeat(colors, MINI_TILE, axis=0), MINI_TILE, axis=1)

        pygame.surfarray.blit_array(self._terrain_surf, colors)
