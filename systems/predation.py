"""Predation system: carnivores hunt and kill prey.

Includes both adjacency-based attacks and a ranged 'pounce' mechanic
so predators can catch fleeing prey at the same speed.
"""

import numpy as np

from config import (
    SpeciesKind, CARNIVORES, PREY_MAP, PREY_ENERGY_TRANSFER,
    DEER_HUNT_WOLF_COUNT, SPECIES_PARAMS,
)
from ecs.world import World
from ecs.components import Position, Vitality, Species, Behavior
from config import State


class PredationSystem:
    DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    POUNCE_DISTANCE = 3    # predators can pounce within this Manhattan distance
    POUNCE_CHANCE = 0.65   # chance per tick when in pounce range

    def update(self, world: World) -> None:
        # Build a position -> entity lookup for this tick
        pos_lookup: dict[tuple[int, int], list[int]] = {}
        for eid, pos, sp in world.query(Position, Species):
            if eid in world.entities:
                pos_lookup.setdefault((pos.x, pos.y), []).append(eid)

        to_kill: set[int] = set()

        for eid, pos, vit, sp in world.query(Position, Vitality, Species):
            if eid not in world.entities or sp.kind not in CARNIVORES:
                continue
            if eid in to_kill:
                continue
            if sp.kind not in PREY_MAP:
                continue

            prey_chances = PREY_MAP[sp.kind]
            hunted = False

            # Phase 1: adjacency attack (full success rate)
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
                    if other_sp is None:
                        continue

                    if not self._can_hunt(sp.kind, other_sp, other_eid, world, pos_lookup, eid, pos):
                        continue

                    success_chance = prey_chances[other_sp.kind]
                    if np.random.random() < success_chance:
                        self._consume_prey(vit, other_eid, world)
                        to_kill.add(other_eid)
                        hunted = True
                        break

            if hunted:
                continue

            # Phase 2: ranged pounce (reduced success rate, only when HUNTING)
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
                if not self._can_hunt(sp.kind, target_sp, behav.target, world, pos_lookup, eid, pos):
                    continue
                pounce_chance = prey_chances[target_sp.kind] * self.POUNCE_CHANCE
                if np.random.random() < pounce_chance:
                    self._consume_prey(vit, behav.target, world)
                    to_kill.add(behav.target)

        for eid in to_kill:
            world.remove_entity(eid)

    def _can_hunt(self, pred_kind, prey_sp, prey_eid, world, pos_lookup, pred_eid, pred_pos) -> bool:
        """Check if predator can hunt this prey."""
        prey_chances = PREY_MAP.get(pred_kind, {})
        return prey_sp.kind in prey_chances

    def _consume_prey(self, predator_vit, prey_eid, world) -> None:
        """Transfer energy from prey to predator."""
        prey_vit = world.get_component(prey_eid, Vitality)
        prey_sp = world.get_component(prey_eid, Species)
        if prey_vit and prey_sp:
            # Gain the prey's max_energy (guaranteed sustenance)
            params = SPECIES_PARAMS[prey_sp.kind]
            gained = params["max_energy"] * PREY_ENERGY_TRANSFER * 0.6
            predator_vit.energy = min(predator_vit.max_energy, predator_vit.energy + gained)

    def _count_adjacent_wolves(self, world, x, y, pos_lookup, exclude_eid):
        count = 0
        for dx, dy in self.DIRS:
            cell = (x + dx, y + dy)
            if cell not in pos_lookup:
                continue
            for eid in pos_lookup[cell]:
                if eid == exclude_eid:
                    continue
                sp = world.get_component(eid, Species)
                if sp and sp.kind == SpeciesKind.WOLF:
                    count += 1
        return count
