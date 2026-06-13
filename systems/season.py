"""Season system: cycles through spring/summer/autumn/winter, manages snow spread."""

import numpy as np

from config import (
    SEASON_LENGTH, GRID_W, GRID_H, Season, SEASON_NAMES, TerrainType,
)
from ecs.world import World


class SeasonSystem:
    def update(self, world: World) -> None:
        world.season_timer -= 1
        if world.season_timer <= 0:
            old_season = Season(world.season)
            world.season = int((world.season + 1) % 4)
            world.season_timer = SEASON_LENGTH
            new_season = Season(world.season)
            world.log_event(f"季节变化: {SEASON_NAMES[old_season]} -> {SEASON_NAMES[new_season]}")

            # On entering winter, backup terrain and start snow spread
            if new_season == Season.WINTER:
                world.snow_edge = 0
                world.pre_snow_terrain = world.terrain.copy()
                world.log_event("寒冬来临，北方开始降雪")

            # On leaving winter, restore all terrain immediately
            if old_season == Season.WINTER and new_season != Season.WINTER:
                self._restore_terrain(world)
                world.snow_edge = 0

        # Snow spread during winter (limited to 1/3 of map)
        if Season(world.season) == Season.WINTER:
            snow_limit = GRID_H // 3
            if world.tick % 8 == 0 and world.snow_edge < snow_limit:
                world.snow_edge += 1
                for x in range(GRID_W):
                    y = world.snow_edge - 1
                    if world.terrain[x, y] not in (TerrainType.WATER, TerrainType.MOUNTAIN):
                        world.terrain[x, y] = TerrainType.SNOW
        elif world.snow_edge > 0:
            # Gradual snow recede in non-winter
            if world.tick % 6 == 0:
                self._recede_snow(world)

    def _recede_snow(self, world: World) -> None:
        """Gradually restore terrain as snow recedes."""
        if world.pre_snow_terrain is None:
            return
        if world.snow_edge > 0:
            # Restore the bottom-most snow row
            row = world.snow_edge - 1
            for x in range(GRID_W):
                if world.terrain[x, row] == TerrainType.SNOW:
                    world.terrain[x, row] = world.pre_snow_terrain[x, row]
            world.snow_edge -= 1

    def _restore_terrain(self, world: World) -> None:
        """Restore all snow-covered terrain from backup."""
        if world.pre_snow_terrain is not None:
            snow_mask = world.terrain == TerrainType.SNOW
            world.terrain[snow_mask] = world.pre_snow_terrain[snow_mask]
            world.pre_snow_terrain = None
