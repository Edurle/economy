"""Grass growth system: regenerates grass_level on grassland and forest tiles."""

import numpy as np

from config import (
    GRID_W, GRID_H, GRASS_GROWTH_RATE, GRASS_MAX, BUSH_GRASS_MULTIPLIER,
    TerrainType, Season, SEASON_GRASS_MULT, WINTER_GRASS_DECAY,
    RAIN_GRASS_BOOST, FIRE_ASH_GROWTH_MULT,
)
from ecs.world import World


class GrassSystem:
    def update(self, world: World) -> None:
        season_mult = SEASON_GRASS_MULT[Season(world.season)]

        # Vectorised growth on grassland and forest
        is_grass = world.terrain == TerrainType.GRASSLAND
        is_forest = world.terrain == TerrainType.FOREST
        growable = is_grass | is_forest

        # Rain boost
        rain_boost = world.rain_map.astype(np.float32) * RAIN_GRASS_BOOST

        # Ash buff multiplier
        ash_mult = np.where(world.ash_buff > 0, FIRE_ASH_GROWTH_MULT, 1.0).astype(np.float32)

        # Forest grows faster
        forest_mult = np.where(is_forest, BUSH_GRASS_MULTIPLIER, 1.0).astype(np.float32)

        if season_mult > 0:
            growth = (GRASS_GROWTH_RATE * season_mult * forest_mult * ash_mult + rain_boost) * growable
            world.grass_level = np.clip(world.grass_level + growth, 0, GRASS_MAX)
        else:
            # Winter: grass stops growing and decays
            decay = WINTER_GRASS_DECAY * growable.astype(np.float32)
            world.grass_level = np.clip(world.grass_level - decay, 0, GRASS_MAX)

        # Ash buff tick-down
        world.ash_buff = np.maximum(world.ash_buff - 1, 0)
