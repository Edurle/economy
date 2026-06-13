"""Tile-based map renderer with camera viewport culling and sprite rendering."""

import pygame
import numpy as np

from config import (
    GRID_W, GRID_H, TILE_SIZE, VIEWPORT_WIDTH, VIEWPORT_HEIGHT,
    TerrainType, SpeciesKind, SPECIES_PARAMS, GRASS_MAX,
)
from ecs.world import World
from ecs.components import Position, Species, Vitality, Health


class TileMapRenderer:
    """Renders only the visible portion of the world using pre-generated tiles/sprites."""

    def __init__(self):
        self.viewport_surface = pygame.Surface((VIEWPORT_WIDTH, VIEWPORT_HEIGHT))
        self._zoom_cache: dict = {}   # {zoom_key: {tile_type: scaled_surf}}
        self._cached_zoom = -1.0

    def render(self, world: World, camera, assets: dict) -> pygame.Surface:
        """Render the visible world region to the viewport surface."""
        surf = self.viewport_surface
        surf.fill((15, 15, 20))

        x0, y0, x1, y1 = camera.visible_tiles
        ts = camera.tile_pixel_size
        tile_px = max(1, int(ts))
        zoom_changed = abs(camera.zoom - self._cached_zoom) > 0.01
        if zoom_changed:
            self._rebuild_zoom_cache(camera.zoom, assets)
            self._cached_zoom = camera.zoom

        # ---- Terrain tiles ----
        for tx in range(x0, x1):
            for ty in range(y0, y1):
                sx, sy = camera.world_to_screen(tx, ty)
                if sx >= VIEWPORT_WIDTH or sy >= VIEWPORT_HEIGHT:
                    continue
                t_val = int(world.terrain[tx, ty])
                tile_surf = self._zoom_cache.get(t_val)
                if tile_surf:
                    surf.blit(tile_surf, (sx, sy))

        # ---- Grass overlays ----
        for tx in range(x0, x1):
            for ty in range(y0, y1):
                t_val = int(world.terrain[tx, ty])
                if t_val not in (TerrainType.GRASSLAND, TerrainType.FOREST):
                    continue
                grass = world.grass_level[tx, ty]
                if grass < 5:
                    continue
                level = min(4, int(grass / (GRASS_MAX / 5)))
                overlay = self._zoom_cache.get(f"grass_{level}")
                if overlay:
                    sx, sy = camera.world_to_screen(tx, ty)
                    surf.blit(overlay, (sx, sy))

        # ---- Fire ----
        for tx in range(x0, x1):
            for ty in range(y0, y1):
                if world.fire_map[tx, ty] > 0:
                    sx, sy = camera.world_to_screen(tx, ty)
                    frame = assets["fire_frames"][world.tick % 2]
                    scaled = pygame.transform.scale(frame, (tile_px, tile_px))
                    surf.blit(scaled, (sx, sy))

        # ---- Ash buff tint ----
        for tx in range(x0, x1):
            for ty in range(y0, y1):
                if world.ash_buff[tx, ty] > 0:
                    sx, sy = camera.world_to_screen(tx, ty)
                    ash = pygame.Surface((tile_px, tile_px), pygame.SRCALPHA)
                    ash.fill((40, 30, 20, 80))
                    surf.blit(ash, (sx, sy))

        # ---- Rain particles ----
        for tx in range(x0, x1):
            for ty in range(y0, y1):
                if world.rain_map[tx, ty]:
                    self._draw_rain(surf, tx, ty, camera)

        # ---- Animals (culled to viewport) ----
        for eid, pos, sp in world.query(Position, Species):
            if eid not in world.entities:
                continue
            if not (x0 <= pos.x < x1 and y0 <= pos.y < y1):
                continue
            sx, sy = camera.world_to_screen(pos.x, pos.y)
            if sx < -tile_px or sx >= VIEWPORT_WIDTH or sy < -tile_px or sy >= VIEWPORT_HEIGHT:
                continue

            health = world.get_component(eid, Health)
            if health and health.diseased:
                sprite_pool = assets["animals_diseased"]
            else:
                sprite_pool = assets["animals"]

            sprite = sprite_pool.get(sp.kind)
            if sprite:
                if tile_px != TILE_SIZE:
                    sprite = pygame.transform.scale(sprite, (tile_px, tile_px))
                surf.blit(sprite, (sx, sy))

        # ---- Grid lines (subtle, only at high zoom) ----
        if camera.zoom >= 2.0:
            grid_color = (0, 0, 0, 30)
            line_surf = pygame.Surface((VIEWPORT_WIDTH, VIEWPORT_HEIGHT), pygame.SRCALPHA)
            for tx in range(x0, x1 + 1):
                sx, _ = camera.world_to_screen(tx, 0)
                if 0 <= sx < VIEWPORT_WIDTH:
                    pygame.draw.line(line_surf, grid_color, (sx, 0), (sx, VIEWPORT_HEIGHT))
            for ty in range(y0, y1 + 1):
                _, sy = camera.world_to_screen(0, ty)
                if 0 <= sy < VIEWPORT_HEIGHT:
                    pygame.draw.line(line_surf, grid_color, (0, sy), (VIEWPORT_WIDTH, sy))
            surf.blit(line_surf, (0, 0))

        return surf

    def render_cell_info(self, world: World, camera, screen_x: int, screen_y: int) -> list[str]:
        """Return info strings about the cell at screen (screen_x, screen_y)."""
        gx, gy = camera.screen_to_grid(screen_x, screen_y)
        if not world.in_bounds(gx, gy):
            return []

        terrain_names = {
            TerrainType.GRASSLAND: "草地", TerrainType.FOREST: "森林",
            TerrainType.WATER: "水域", TerrainType.DESERT: "沙漠",
            TerrainType.MOUNTAIN: "山地", TerrainType.SNOW: "雪地",
        }
        lines = [f"({gx},{gy})"]
        t = TerrainType(world.terrain[gx, gy])
        lines.append(f"地形: {terrain_names.get(t, '?')}")
        lines.append(f"草量: {world.grass_level[gx, gy]:.0f}")
        if world.fire_map[gx, gy] > 0:
            lines.append("着火!")
        if world.rain_map[gx, gy]:
            lines.append("降雨中")

        for eid, pos, sp in world.query(Position, Species):
            if eid in world.entities and pos.x == gx and pos.y == gy:
                vit = world.get_component(eid, Vitality)
                health = world.get_component(eid, Health)
                name = SPECIES_PARAMS[sp.kind]["name"]
                sick = " (病)" if health and health.diseased else ""
                if vit:
                    lines.append(f"{name}: E{vit.energy:.0f} W{vit.hydration:.0f} A{vit.age}{sick}")
        return lines

    # ----------------------------------------------------------------
    # Internals
    # ----------------------------------------------------------------
    def _rebuild_zoom_cache(self, zoom: float, assets: dict) -> None:
        """Pre-scale all tiles and overlays for the current zoom level."""
        self._zoom_cache = {}
        tile_px = max(1, int(TILE_SIZE * zoom))

        for t_type, tile_surf in assets["terrain"].items():
            self._zoom_cache[int(t_type)] = pygame.transform.scale(tile_surf, (tile_px, tile_px))

        for level, overlay in enumerate(assets["grass_overlay"]):
            self._zoom_cache[f"grass_{level}"] = pygame.transform.scale(overlay, (tile_px, tile_px))

    def _draw_rain(self, surf, tx, ty, camera):
        """Draw a few rain drops on a tile."""
        drop = None  # will use assets if passed; for now draw simple lines
        sx, sy = camera.world_to_screen(tx, ty)
        ts = max(1, int(camera.tile_pixel_size))
        rng_offset = (tx * 7 + ty * 13) % ts
        for i in range(2):
            dx = (rng_offset + i * 5) % ts
            dy = (rng_offset + i * 3 + (camera.offset[0] + camera.offset[1]) * 0.5) % ts
            ix, iy = int(sx + dx), int(sy + dy)
            if 0 <= ix < VIEWPORT_WIDTH and 0 <= iy < VIEWPORT_HEIGHT:
                pygame.draw.line(surf, (100, 150, 220), (ix, iy), (ix - 2, iy + 4), 1)
