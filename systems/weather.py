"""Weather system: manages rainfall areas and drought tracking."""

import numpy as np

from config import (
    GRID_W, GRID_H, SEASON_RAIN_CHANCE, Season,
    RAIN_RADIUS_MIN, RAIN_RADIUS_MAX,
    RAIN_DURATION_MIN, RAIN_DURATION_MAX,
    RAIN_GRASS_BOOST, DROUGHT_THRESHOLD, DROUGHT_GRASS_DECAY,
    TerrainType,
)
from ecs.world import World


class WeatherSystem:
    def __init__(self):
        self.rain_centers: list[list] = []  # [cx, cy, radius, remaining_ticks]

    def update(self, world: World) -> None:
        season = Season(world.season)
        rain_chance = SEASON_RAIN_CHANCE[season]

        # Clear previous rain map
        world.rain_map[:] = False

        # Tick existing rain centers
        active = []
        for center in self.rain_centers:
            cx, cy, radius, remaining = center
            remaining -= 1
            if remaining > 0:
                self._apply_rain(world, cx, cy, radius)
                center[3] = remaining
                active.append(center)
        self.rain_centers = active

        # Attempt to start new rain
        if np.random.random() < rain_chance:
            cx = np.random.randint(0, GRID_W)
            cy = np.random.randint(0, GRID_H)
            radius = np.random.randint(RAIN_RADIUS_MIN, RAIN_RADIUS_MAX + 1)
            duration = np.random.randint(RAIN_DURATION_MIN, RAIN_DURATION_MAX + 1)
            self.rain_centers.append([cx, cy, radius, duration])
            self._apply_rain(world, cx, cy, radius)
            world.drought_timer = 0
        else:
            world.drought_timer += 1

        # Drought effect on grass
        if world.drought_timer > DROUGHT_THRESHOLD:
            growable = (world.terrain == TerrainType.GRASSLAND) | (world.terrain == TerrainType.FOREST)
            world.grass_level -= DROUGHT_GRASS_DECAY * growable.astype(np.float32)
            world.grass_level = np.maximum(world.grass_level, 0)

            # Severe drought: grassland degrades to desert
            if world.drought_timer > DROUGHT_THRESHOLD + 30:
                degraded = growable & (world.grass_level < 5)
                world.terrain[degraded & (world.terrain == TerrainType.GRASSLAND)] = TerrainType.DESERT

    def _apply_rain(self, world: World, cx: int, cy: int, radius: int) -> None:
        x0 = max(0, cx - radius)
        x1 = min(GRID_W, cx + radius + 1)
        y0 = max(0, cy - radius)
        y1 = min(GRID_H, cy + radius + 1)
        for x in range(x0, x1):
            for y in range(y0, y1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                    world.rain_map[x, y] = True

    def trigger_rain_at(self, world: World, cx: int, cy: int, radius: int = 20) -> None:
        """God-mode: manually trigger rain at a location."""
        duration = 10
        self.rain_centers.append([cx, cy, radius, duration])
        self._apply_rain(world, cx, cy, radius)
        world.drought_timer = 0
