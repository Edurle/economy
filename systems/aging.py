"""Aging system: tick age, consume energy, apply disease damage, check death."""

import numpy as np

from config import (
    Season, SEASON_ENERGY_MULT, BASE_ENERGY_COST,
    TerrainType, SNOW_ENERGY_MULT, PLAGUE_ENERGY_DAMAGE,
    SPECIES_PARAMS,
)
from ecs.world import World
from ecs.components import Position, Vitality, Species, Health, Reproduction


class AgingSystem:
    def update(self, world: World) -> None:
        season_energy_mult = SEASON_ENERGY_MULT[Season(world.season)]
        dead: list[int] = []

        for eid, pos, vit, sp in world.query(Position, Vitality, Species):
            if eid not in world.entities:
                continue
            params = SPECIES_PARAMS[sp.kind]

            # Age
            vit.age += 1

            # Energy cost (seasonal + terrain)
            cost = BASE_ENERGY_COST * season_energy_mult
            t = world.terrain[pos.x, pos.y]
            if t == TerrainType.SNOW:
                cost *= SNOW_ENERGY_MULT
            vit.energy -= cost

            # Disease damage
            health = world.get_component(eid, Health)
            if health and health.diseased:
                vit.energy -= PLAGUE_ENERGY_DAMAGE
                health.sick_timer -= 1
                if health.sick_timer <= 0:
                    health.diseased = False

            # Tick reproduction cooldown
            repro = world.get_component(eid, Reproduction)
            if repro and repro.cooldown > 0:
                repro.cooldown -= 1

            # Death checks
            if vit.energy <= 0 or vit.hydration <= 0 or vit.age > vit.max_age:
                dead.append(eid)

        for eid in dead:
            world.remove_entity(eid)
