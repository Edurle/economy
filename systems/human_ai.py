"""Human AI system: decision-making for human entities.

Runs BEFORE the regular AISystem. Sets Behavior state/target for all
HUMAN entities based on a priority decision tree.
"""

import numpy as np
from collections import defaultdict

from config import (
    GRID_W, GRID_H, State, SpeciesKind, Season, SEASON_BREED_MULT,
    SPECIES_PARAMS, Role, TerrainType,
    HUMAN_PREY_MAP, HUMAN_INVENTORY_MAX, CAMP_INIT_CAPACITY,
    BUILD_WOOD_COST,
)
from ecs.world import World
from ecs.components import Position, Vitality, Species, Behavior, Reproduction, Tribe, Inventory, Structure


class HumanAISystem:
    def __init__(self):
        self._grid: dict[tuple[int, int], list[int]] = defaultdict(list)

    def _rebuild_index(self, world: World) -> None:
        self._grid.clear()
        for eid, pos, sp in world.query(Position, Species):
            if eid in world.entities:
                self._grid[(pos.x, pos.y)].append(eid)

    def update(self, world: World) -> None:
        self._rebuild_index(world)
        breed_mult = SEASON_BREED_MULT[Season(world.season)]
        camps = world.get_camps()
        camp_lookup = {camp[0]: camp for camp in camps}

        for eid, pos, vit, sp, behav, repro, tribe, inv in world.query(
            Position, Vitality, Species, Behavior, Reproduction, Tribe, Inventory
        ):
            if eid not in world.entities or sp.kind != SpeciesKind.HUMAN:
                continue

            vision = SPECIES_PARAMS[SpeciesKind.HUMAN]["vision"]
            max_e = vit.max_energy
            max_h = vit.max_hydration

            camp_data = camp_lookup.get(tribe.home_camp)
            camp_struct = camp_data[2] if camp_data else None

            # 1. Flee from wolves (2+ within vision)
            wolf_count = 0
            nearest_wolf = None
            nearest_wolf_dist = 999
            for dx in range(-vision, vision + 1):
                for dy in range(-vision, vision + 1):
                    cell = (pos.x + dx, pos.y + dy)
                    for other_eid in self._grid.get(cell, []):
                        if other_eid == eid:
                            continue
                        other_sp = world.get_component(other_eid, Species)
                        if other_sp and other_sp.kind == SpeciesKind.WOLF:
                            wolf_count += 1
                            d = abs(dx) + abs(dy)
                            if d < nearest_wolf_dist:
                                nearest_wolf_dist = d
                                nearest_wolf = other_eid
            if wolf_count >= 2 and nearest_wolf is not None:
                behav.state = State.FLEEING
                behav.target = nearest_wolf
                continue

            # 2. Seek water
            if vit.hydration < max_h * 0.25:
                behav.state = State.SEEKING_WATER
                behav.target = -1
                continue

            # 3. Eat from camp stockpile when hungry
            if vit.energy < max_e * 0.40 and camp_struct and camp_struct.food_stockpile > 0:
                behav.state = State.RETURNING
                behav.target = tribe.home_camp
                continue

            # 4. Gatherers/Miners: gather when inventory not full
            if tribe.role in (Role.GATHERER, Role.MINER) and (inv.food + inv.total_resources) < HUMAN_INVENTORY_MAX:
                # If carrying stuff, deposit at camp first
                if inv.food > 0 or inv.total_resources > 0:
                    behav.state = State.RETURNING
                    behav.target = tribe.home_camp if camp_data else -1
                    continue
                if tribe.role == Role.MINER:
                    behav.state = State.MINING
                else:
                    behav.state = State.GATHERING
                behav.target = -1
                continue

            # 4.5. Scholars: stay at camp to research
            if tribe.role == Role.SCHOLAR:
                if camp_data:
                    camp_pos = camp_data[1]
                    dist = abs(pos.x - camp_pos.x) + abs(pos.y - camp_pos.y)
                    if dist > 1:
                        behav.state = State.RETURNING
                        behav.target = tribe.home_camp
                        continue
                behav.state = State.IDLE
                behav.target = -1
                continue

            # 5. Hunters: hunt when camp food is low
            if tribe.role == Role.HUNTER:
                camp_food = camp_struct.food_stockpile if camp_struct else 0
                if camp_food < 20:
                    prey_kinds = set(HUMAN_PREY_MAP.keys())
                    prey = self._find_nearest_animal(world, pos.x, pos.y, vision, prey_kinds)
                    if prey is not None:
                        behav.state = State.HUNTING
                        behav.target = prey
                        continue

            # 6. Builders: expand camp when needed
            if tribe.role == Role.BUILDER and camp_struct:
                pop = world.count_species(SpeciesKind.HUMAN)
                if (pop >= camp_struct.capacity - 2 and
                        camp_struct.get_res("wood") >= BUILD_WOOD_COST):
                    behav.state = State.BUILDING
                    behav.target = tribe.home_camp
                    continue

            # 7. Reproduce when well-fed
            if (vit.energy >= SPECIES_PARAMS[SpeciesKind.HUMAN]["breed_energy"] and
                    repro.cooldown <= 0 and
                    np.random.random() < breed_mult * 0.8):
                mate_radius = max(vision, 10)
                mate = self._find_nearest_human(world, pos.x, pos.y, mate_radius, exclude=eid)
                if mate is not None:
                    behav.state = State.MATING
                    behav.target = mate
                    continue

            # 8. Idle — return to camp vicinity
            if camp_data:
                camp_pos = camp_data[1]
                dist = abs(pos.x - camp_pos.x) + abs(pos.y - camp_pos.y)
                if dist > camp_struct.territory_radius:
                    behav.state = State.RETURNING
                    behav.target = tribe.home_camp
                    continue
            behav.state = State.IDLE
            behav.target = -1

    def _find_nearest_animal(self, world, x, y, radius, kinds):
        best = None
        best_dist = 9999
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                cell = (x + dx, y + dy)
                for eid in self._grid.get(cell, []):
                    sp = world.get_component(eid, Species)
                    if sp is None or sp.kind not in kinds:
                        continue
                    d = abs(dx) + abs(dy)
                    if d < best_dist:
                        best_dist = d
                        best = eid
        return best

    def _find_nearest_human(self, world, x, y, radius, exclude=-1):
        best = None
        best_dist = 9999
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                cell = (x + dx, y + dy)
                for eid in self._grid.get(cell, []):
                    if eid == exclude:
                        continue
                    sp = world.get_component(eid, Species)
                    if sp is None or sp.kind != SpeciesKind.HUMAN:
                        continue
                    d = abs(dx) + abs(dy)
                    if d < best_dist:
                        best_dist = d
                        best = eid
        return best
