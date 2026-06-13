"""Predation system: carnivores and humans hunt and kill prey.

Includes both adjacency-based attacks and a ranged 'pounce' mechanic.
Humans hunt animals for food (stores in Inventory). Wolves can attack humans.
"""

import numpy as np

from config import (
    SpeciesKind, CARNIVORES, PREY_MAP, PREY_ENERGY_TRANSFER,
    DEER_HUNT_WOLF_COUNT, SPECIES_PARAMS,
    HUMAN_PREY_MAP, WOLF_HUNT_HUMAN_CHANCE, CAMP_FOOD_TRANSFER,
    HUMAN_INVENTORY_MAX,
)
from ecs.world import World
from ecs.components import Position, Vitality, Species, Behavior, Inventory
from config import State


class PredationSystem:
    DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    POUNCE_DISTANCE = 3
    POUNCE_CHANCE = 0.65

    def update(self, world: World) -> None:
        pos_lookup: dict[tuple[int, int], list[int]] = {}
        for eid, pos, sp in world.query(Position, Species):
            if eid in world.entities:
                pos_lookup.setdefault((pos.x, pos.y), []).append(eid)

        to_kill: set[int] = set()

        for eid, pos, vit, sp in world.query(Position, Vitality, Species):
            if eid not in world.entities or eid in to_kill:
                continue

            prey_chances = self._get_prey_map(sp.kind)
            if not prey_chances:
                continue

            hunted = False

            # Phase 1: adjacency attack
            for dx, dy in self.DIRS:
                if hunted:
                    break
                cell = (pos.x + dx, pos.y + dy)
                if cell not in pos_lookup:
                    continue
                for other_eid in pos_lookup[cell]:
                    if other_eid == eid or other_eid in to_kill:
                        continue
                    other_sp = world.get_component(other_eid, Species)
                    if other_sp is None or other_sp.kind not in prey_chances:
                        continue

                    success_chance = prey_chances[other_sp.kind]
                    if np.random.random() < success_chance:
                        self._consume(eid, sp.kind, vit, other_eid, world)
                        to_kill.add(other_eid)
                        hunted = True
                        break

            if hunted:
                continue

            # Phase 2: ranged pounce (only when HUNTING)
            behav = world.get_component(eid, Behavior)
            if behav is None or behav.state != State.HUNTING or behav.target < 0:
                continue
            if behav.target in to_kill or behav.target not in world.entities:
                continue

            target_pos = world.get_component(behav.target, Position)
            target_sp = world.get_component(behav.target, Species)
            if target_pos is None or target_sp is None:
                continue
            if target_sp.kind not in prey_chances:
                continue

            dist = abs(pos.x - target_pos.x) + abs(pos.y - target_pos.y)
            if dist <= self.POUNCE_DISTANCE:
                pounce_chance = prey_chances[target_sp.kind] * self.POUNCE_CHANCE
                if np.random.random() < pounce_chance:
                    self._consume(eid, sp.kind, vit, behav.target, world)
                    to_kill.add(behav.target)

        for eid in to_kill:
            world.remove_entity(eid)

    def _get_prey_map(self, hunter_kind: int) -> dict:
        """Return prey map for the given hunter species."""
        if hunter_kind == SpeciesKind.HUMAN:
            return HUMAN_PREY_MAP
        if hunter_kind == SpeciesKind.WOLF:
            merged = dict(PREY_MAP.get(SpeciesKind.WOLF, {}))
            merged[SpeciesKind.HUMAN] = WOLF_HUNT_HUMAN_CHANCE
            return merged
        return PREY_MAP.get(hunter_kind, {})

    def _consume(self, hunter_eid: int, hunter_kind: int,
                 hunter_vit, prey_eid: int, world: World) -> None:
        """Handle prey consumption — different for animals vs humans."""
        prey_sp = world.get_component(prey_eid, Species)
        if prey_sp is None:
            return
        prey_params = SPECIES_PARAMS[prey_sp.kind]

        if hunter_kind == SpeciesKind.HUMAN:
            inv = world.get_component(hunter_eid, Inventory)
            if inv:
                gained_food = int(prey_params["max_energy"] * CAMP_FOOD_TRANSFER)
                inv.food = min(HUMAN_INVENTORY_MAX, inv.food + gained_food)
        else:
            gained = prey_params["max_energy"] * PREY_ENERGY_TRANSFER * 0.6
            hunter_vit.energy = min(hunter_vit.max_energy, hunter_vit.energy + gained)
