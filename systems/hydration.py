"""Hydration system: animals drink from adjacent water and lose hydration."""

import numpy as np

from config import (
    GRID_W, GRID_H, TerrainType, Season,
    DESERT_HYDRATION_MULT, SNOW_HYDRATION_MULT, BASE_HYDRATION_COST,
)
from ecs.world import World
from ecs.components import Position, Vitality


class HydrationSystem:
    def update(self, world: World) -> None:
        winter = Season(world.season) == Season.WINTER

        for eid, pos, vit in world.query(Position, Vitality):
            if eid not in world.entities:
                continue

            # Drink if adjacent to water (winter: 50% chance frozen)
            if world.adjacent_water(pos.x, pos.y):
                if winter and np.random.random() < 0.5:
                    pass  # frozen, can't drink
                else:
                    vit.hydration = vit.max_hydration
                continue

            # Compute hydration loss
            loss = BASE_HYDRATION_COST
            t = world.terrain[pos.x, pos.y]
            if t == TerrainType.DESERT:
                loss *= DESERT_HYDRATION_MULT
            elif t == TerrainType.SNOW:
                loss *= SNOW_HYDRATION_MULT

            vit.hydration -= loss
