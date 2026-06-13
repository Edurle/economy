"""Plague system: triggers when species overpopulates, spreads and kills."""

import numpy as np

from config import (
    SpeciesKind, SPECIES_PARAMS,
    PLAGUE_TRIGGER_RATIO, PLAGUE_CURE_RATIO,
    PLAGUE_SPREAD_CHANCE, PLAGUE_ENERGY_DAMAGE,
)
from ecs.world import World
from ecs.components import Position, Species, Health


class PlagueSystem:
    DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def __init__(self):
        self.active_plagues: set[int] = set()  # set of SpeciesKind values

    def update(self, world: World) -> None:
        # Check trigger conditions for each species
        for kind in SpeciesKind:
            params = SPECIES_PARAMS[kind]
            cap = params["population_cap"]
            count = world.count_species(kind)
            ki = int(kind)

            if ki not in self.active_plagues:
                if count >= cap * PLAGUE_TRIGGER_RATIO:
                    self.active_plagues.add(ki)
                    # Infect a few individuals to start
                    self._infect_random(world, kind, count // 10)
                    world.log_event(f"瘟疫爆发: {params['name']}种群过密！")
            else:
                if count <= cap * PLAGUE_CURE_RATIO:
                    self.active_plagues.discard(ki)
                    world.log_event(f"瘟疫消退: {params['name']}")

        if not self.active_plagues:
            return

        # Spread plague among adjacent same-species
        pos_lookup: dict[tuple[int, int], list[int]] = {}
        for eid, pos, sp in world.query(Position, Species):
            if eid in world.entities:
                pos_lookup.setdefault((pos.x, pos.y), []).append(eid)

        new_infections: list[int] = []

        for eid, pos, sp in world.query(Position, Species):
            if eid not in world.entities:
                continue
            health = world.get_component(eid, Health)
            if health is None or health.diseased:
                continue
            ki = int(sp.kind)
            if ki not in self.active_plagues:
                continue

            # Check adjacent same-species for infected individuals
            for dx, dy in self.DIRS:
                cell = (pos.x + dx, pos.y + dy)
                if cell not in pos_lookup:
                    continue
                for other_eid in pos_lookup[cell]:
                    if other_eid == eid:
                        continue
                    other_sp = world.get_component(other_eid, Species)
                    if other_sp and other_sp.kind == sp.kind:
                        other_health = world.get_component(other_eid, Health)
                        if other_health and other_health.diseased:
                            if np.random.random() < PLAGUE_SPREAD_CHANCE:
                                new_infections.append(eid)
                                break

        for eid in new_infections:
            health = world.get_component(eid, Health)
            if health and not health.diseased:
                health.diseased = True
                health.sick_timer = 30  # sick for up to 30 ticks

    def _infect_random(self, world: World, kind: SpeciesKind, n: int) -> None:
        candidates = []
        for eid, sp in world.query(Species):
            if eid in world.entities and sp.kind == kind:
                candidates.append(eid)
        np.random.shuffle(candidates)
        for eid in candidates[:n]:
            health = world.get_component(eid, Health)
            if health:
                health.diseased = True
                health.sick_timer = 30

    def infect_at(self, world: World, x: int, y: int, radius: int = 3) -> None:
        """God-mode: infect all animals of same species near (x, y)."""
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                cell = (x + dx, y + dy)
                for eid, pos, sp in world.query(Position, Species):
                    if eid not in world.entities:
                        continue
                    if (pos.x, pos.y) == cell:
                        health = world.get_component(eid, Health)
                        if health and not health.diseased:
                            health.diseased = True
                            health.sick_timer = 30
                            ki = int(sp.kind)
                            self.active_plagues.add(ki)
