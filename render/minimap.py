"""Minimap: compact overview of the full world with camera viewport indicator."""

import numpy as np
import pygame

from config import (
    GRID_W, GRID_H, VIEWPORT_WIDTH, VIEWPORT_HEIGHT, TILE_SIZE,
    TerrainType, SpeciesKind, SPECIES_PARAMS, TERRAIN_COLORS,
)
from ecs.world import World
from ecs.components import Position, Species


MINI_TILE = 3   # pixels per grid cell on minimap
MINI_W = GRID_W * MINI_TILE   # 192
MINI_H = GRID_H * MINI_TILE   # 192
MINI_RIGHT = MINI_W + 16      # x offset for content beside minimap


class Minimap:
    """Renders a 128x128 overview of the entire 64x64 world."""

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
        """Draw terrain colors to the cached terrain surface."""
        for tx in range(GRID_W):
            for ty in range(GRID_H):
                t_val = int(world.terrain[tx, ty])
                color = TERRAIN_COLORS[TerrainType(t_val)]
                # Darken if no grass on grassland/forest
                if t_val in (TerrainType.GRASSLAND, TerrainType.FOREST):
                    g = world.grass_level[tx, ty]
                    factor = 0.4 + 0.6 * (g / 100.0)
                    color = tuple(int(c * factor) for c in color)
                px, py = tx * MINI_TILE, ty * MINI_TILE
                self._terrain_surf.fill(color, (px, py, MINI_TILE, MINI_TILE))
