"""AI system: each animal decides its behaviour state every tick."""

import numpy as np
from collections import defaultdict

from config import (
    GRID_W, GRID_H, State, SpeciesKind, Season, SEASON_BREED_MULT,
    SPECIES_PARAMS, HERBIVORES, CARNIVORES, PREY_MAP, PREDATOR_MAP,
)
from ecs.world import World
from ecs.components import Position, Vitality, Species, Behavior, Reproduction


class SpatialIndex:
    """Grid-based spatial hash for O(1) neighbour lookups."""

    def __init__(self):
        self.grid: dict[tuple[int, int], list[int]] = defaultdict(list)

    def clear(self) -> None:
        self.grid.clear()

    def insert(self, eid: int, x: int, y: int) -> None:
        self.grid[(x, y)].append(eid)

    def query_radius(self, x: int, y: int, radius: int):
        """Yield entity ids within *radius* cells of (x, y)."""
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                cell = (x + dx, y + dy)
                if cell in self.grid:
                    yield from self.grid[cell]


class AISystem:
    def __init__(self):
        self.spatial = SpatialIndex()

    def _rebuild_index(self, world: World) -> None:
        self.spatial.clear()
        for eid, pos, vit, sp in world.get_entities_with(Position, Vitality, Species):
            if eid in world.entities:
                self.spatial.insert(eid, pos.x, pos.y)

    def update(self, world: World) -> None:
        self._rebuild_index(world)
        breed_mult = SEASON_BREED_MULT[Season(world.season)]

        animals = world.query(Position, Vitality, Species, Behavior, Reproduction)

        for eid, pos, vit, sp, behav, repro in animals:
            if eid not in world.entities:
                continue
            params = SPECIES_PARAMS[sp.kind]
            vision = params["vision"]
            max_e = vit.max_energy
            max_h = vit.max_hydration

            # Priority 1: seek water
            if vit.hydration < max_h * 0.25:
                behav.state = State.SEEKING_WATER
                behav.target = -1
                continue

            # Priority 2: flee from predators
            if sp.kind in PREDATOR_MAP:
                threat = self._find_nearest(world, pos.x, pos.y, vision, PREDATOR_MAP[sp.kind])
                if threat is not None:
                    behav.state = State.FLEEING
                    behav.target = threat
                    continue

            # Priority 3: forage when starving (below 30% energy)
            if vit.energy < max_e * 0.30:
                if sp.kind in CARNIVORES and sp.kind in PREY_MAP:
                    prey_kinds = set(PREY_MAP[sp.kind].keys())
                    prey = self._find_nearest(world, pos.x, pos.y, vision, prey_kinds)
                    if prey is not None:
                        behav.state = State.HUNTING
                        behav.target = prey
                        continue
                behav.state = State.FORAGING
                behav.target = -1
                continue

            # Priority 4: mate when well-fed (before hunting — prevents over-hunting)
            if (vit.energy >= params["breed_energy"] and
                    repro.cooldown <= 0 and
                    np.random.random() < breed_mult * 0.8):
                mate_radius = max(vision, 10)
                mate = self._find_nearest(world, pos.x, pos.y, mate_radius, {sp.kind}, exclude=eid)
                if mate is not None:
                    behav.state = State.MATING
                    behav.target = mate
                    continue

            # Priority 5: hunt prey (carnivores with moderate energy)
            if sp.kind in CARNIVORES and sp.kind in PREY_MAP:
                prey_kinds = set(PREY_MAP[sp.kind].keys())
                prey = self._find_nearest(world, pos.x, pos.y, vision, prey_kinds)
                if prey is not None:
                    behav.state = State.HUNTING
                    behav.target = prey
                    continue

            # Default: idle
            behav.state = State.IDLE
            behav.target = -1

    def _find_nearest(self, world: World, x: int, y: int, radius: int,
                      kinds: set[SpeciesKind], exclude: int = -1) -> int | None:
        """Find nearest entity of one of *kinds* within *radius* of (x, y)."""
        best = None
        best_dist = float('inf')
        for eid in self.spatial.query_radius(x, y, radius):
            if eid == exclude or eid not in world.entities:
                continue
            sp = world.get_component(eid, Species)
            if sp is None or sp.kind not in kinds:
                continue
            pos = world.get_component(eid, Position)
            if pos is None:
                continue
            d = abs(pos.x - x) + abs(pos.y - y)
            if d < best_dist:
                best_dist = d
                best = eid
        return best
