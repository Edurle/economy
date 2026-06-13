"""Foraging system: herbivores eat grass on their current tile."""

from config import (
    State, SpeciesKind, HERBIVORES, SPECIES_PARAMS, TerrainType,
)
from ecs.world import World
from ecs.components import Position, Vitality, Species, Behavior


class ForagingSystem:
    def update(self, world: World) -> None:
        for eid, pos, vit, sp, behav in world.query(Position, Vitality, Species, Behavior):
            if eid not in world.entities:
                continue
            if sp.kind not in HERBIVORES:
                continue
            # Forage when hungry or explicitly foraging
            needs_food = vit.energy < vit.max_energy * 0.7
            if not (behav.state == State.FORAGING or needs_food):
                continue

            grass = world.grass_level[pos.x, pos.y]
            if grass < 5:
                continue

            params = SPECIES_PARAMS[sp.kind]
            eat_amount = min(grass, 10)
            world.grass_level[pos.x, pos.y] -= eat_amount
            vit.energy = min(vit.max_energy, vit.energy + eat_amount * (params["food_gain"] / 10))
