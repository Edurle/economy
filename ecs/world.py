"""ECS World: entity management + grid data + global state."""

from __future__ import annotations
import numpy as np
from collections import defaultdict, deque

from config import (
    GRID_W, GRID_H, SEASON_LENGTH, GRASS_MAX, GRASS_GROWTH_RATE,
    TerrainType, SpeciesKind, Season, SPECIES_PARAMS, Role,
    CAMP_INIT_FOOD, CAMP_INIT_WOOD, CAMP_INIT_CAPACITY, CAMP_TERRITORY_RADIUS,
)
from ecs.components import (
    Position, Vitality, Species, Behavior, Reproduction, Health,
    Tribe, Inventory, Structure,
)


class World:
    """Central world holding grid arrays, ECS storage, and global state."""

    def __init__(self):
        # ---- Grid arrays (numpy for performance) ----
        self.terrain: np.ndarray = np.zeros((GRID_W, GRID_H), dtype=np.int8)
        self.grass_level: np.ndarray = np.zeros((GRID_W, GRID_H), dtype=np.float32)
        self.ash_buff: np.ndarray = np.zeros((GRID_W, GRID_H), dtype=np.int16)
        self.fire_map: np.ndarray = np.zeros((GRID_W, GRID_H), dtype=np.int8)
        self.rain_map: np.ndarray = np.zeros((GRID_W, GRID_H), dtype=np.bool_)
        self.snow_edge: int = 0
        self.pre_snow_terrain: np.ndarray | None = None  # backup before snow

        # ---- Camp positions (blocking) ----
        self.camp_positions: set[tuple[int, int]] = set()

        # ---- ECS storage ----
        self._next_id: int = 0
        self.entities: set[int] = set()
        # component_type -> {entity_id: component}
        self._components: dict[type, dict[int, object]] = defaultdict(dict)

        # ---- Global state ----
        self.season: int = int(Season.SPRING)
        self.season_timer: int = SEASON_LENGTH
        self.drought_timer: int = 0
        self.tick: int = 0
        self.speed: int = 1
        self.paused: bool = False

        # ---- Statistics ----
        self.population_history: dict[int, deque] = {
            int(k): deque(maxlen=500) for k in SpeciesKind
        }
        self.events_log: deque = deque(maxlen=20)
        self._pop_cache: dict[int, int] = {}   # cached population counts per tick
        self._pop_cache_tick: int = -1

    # --------------------------------------------------------
    # Entity management
    # --------------------------------------------------------
    def create_entity(self) -> int:
        eid = self._next_id
        self._next_id += 1
        self.entities.add(eid)
        return eid

    def remove_entity(self, eid: int) -> None:
        self.entities.discard(eid)
        for comp_dict in self._components.values():
            comp_dict.pop(eid, None)

    def add_component(self, eid: int, component) -> None:
        self._components[type(component)][eid] = component

    def get_component(self, eid: int, comp_type: type):
        return self._components[comp_type].get(eid)

    def has_component(self, eid: int, comp_type: type) -> bool:
        return eid in self._components[comp_type]

    def get_entities_with(self, *comp_types: type):
        """Yield (eid, comp1, comp2, ...) for entities that have ALL given components."""
        if not comp_types:
            return
        first = self._components[comp_types[0]]
        rest_sets = [set(self._components[ct].keys()) for ct in comp_types[1:]]
        for eid in first:
            if eid not in self.entities:
                continue
            if all(eid in s for s in rest_sets):
                yield (eid,) + tuple(self._components[ct][eid] for ct in comp_types)

    def query(self, *comp_types: type):
        """Alias for get_entities_with — convenience."""
        return list(self.get_entities_with(*comp_types))

    # --------------------------------------------------------
    # Animal factory
    # --------------------------------------------------------
    def spawn_animal(self, kind: SpeciesKind, x: int, y: int, is_offspring: bool = False) -> int:
        """Create an animal entity with all required components."""
        p = SPECIES_PARAMS[kind]
        eid = self.create_entity()
        self.add_component(eid, Position(x=x, y=y))
        self.add_component(eid, Vitality(
            energy=p["init_energy"] if not is_offspring else p["init_energy"] * 0.5,
            hydration=p["init_hydration"] if not is_offspring else p["init_hydration"] * 0.7,
            age=0,
            max_energy=p["max_energy"],
            max_hydration=p["max_hydration"],
            max_age=p["max_age"],
        ))
        self.add_component(eid, Species(kind=kind))
        self.add_component(eid, Behavior())
        self.add_component(eid, Reproduction(cooldown=0))
        self.add_component(eid, Health())
        return eid

    # --------------------------------------------------------
    # Human / Camp factories
    # --------------------------------------------------------
    def spawn_camp(self, x: int, y: int, tribe_id: int = 0) -> int:
        eid = self.create_entity()
        self.add_component(eid, Position(x=x, y=y))
        self.add_component(eid, Structure(
            tribe_id=tribe_id,
            food_stockpile=CAMP_INIT_FOOD,
            wood_stockpile=CAMP_INIT_WOOD,
            capacity=CAMP_INIT_CAPACITY,
            territory_radius=CAMP_TERRITORY_RADIUS,
        ))
        self.camp_positions.add((x, y))
        return eid

    def spawn_human(self, x: int, y: int, tribe_id: int = 0,
                    role: int = Role.HUNTER, home_camp: int = -1) -> int:
        p = SPECIES_PARAMS[SpeciesKind.HUMAN]
        eid = self.create_entity()
        self.add_component(eid, Position(x=x, y=y))
        self.add_component(eid, Vitality(
            energy=p["init_energy"],
            hydration=p["init_hydration"],
            age=0,
            max_energy=p["max_energy"],
            max_hydration=p["max_hydration"],
            max_age=p["max_age"],
        ))
        self.add_component(eid, Species(kind=SpeciesKind.HUMAN))
        self.add_component(eid, Behavior())
        self.add_component(eid, Reproduction(cooldown=0))
        self.add_component(eid, Health())
        self.add_component(eid, Tribe(tribe_id=tribe_id, role=role, home_camp=home_camp))
        self.add_component(eid, Inventory())
        return eid

    def rebuild_camp_positions(self) -> None:
        self.camp_positions.clear()
        for eid, pos, struct in self.query(Position, Structure):
            if eid in self.entities:
                self.camp_positions.add((pos.x, pos.y))

    def get_camps(self, tribe_id: int | None = None) -> list[tuple[int, Position, Structure]]:
        result = []
        for eid, pos, struct in self.query(Position, Structure):
            if eid in self.entities:
                if tribe_id is None or struct.tribe_id == tribe_id:
                    result.append((eid, pos, struct))
        return result

    # --------------------------------------------------------
    # Grid helpers
    # --------------------------------------------------------
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < GRID_W and 0 <= y < GRID_H

    def is_walkable(self, x: int, y: int, kind: SpeciesKind | None = None) -> bool:
        """Can an entity of *kind* enter cell (x, y)?"""
        if not self.in_bounds(x, y):
            return False
        t = self.terrain[x, y]
        if t == TerrainType.WATER:
            return False
        if t == TerrainType.MOUNTAIN:
            # Only deer can cross mountains
            return kind == SpeciesKind.DEER
        # Camps block animals but not humans
        if kind != SpeciesKind.HUMAN and (x, y) in self.camp_positions:
            return False
        return True

    def adjacent_water(self, x: int, y: int) -> bool:
        """Is any 4-neighbour cell water?"""
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny) and self.terrain[nx, ny] == TerrainType.WATER:
                return True
        return False

    def count_species(self, kind: SpeciesKind) -> int:
        """Count living entities of a given species (cached per tick)."""
        if self._pop_cache_tick != self.tick:
            self._rebuild_pop_cache()
        return self._pop_cache.get(int(kind), 0)

    def _rebuild_pop_cache(self) -> None:
        """Rebuild the population count cache for the current tick."""
        self._pop_cache = {int(k): 0 for k in SpeciesKind}
        self._pop_cache_tick = self.tick
        comp_dict = self._components.get(Species, {})
        for eid, sp in comp_dict.items():
            if eid in self.entities:
                self._pop_cache[int(sp.kind)] = self._pop_cache.get(int(sp.kind), 0) + 1

    # --------------------------------------------------------
    # Population tracking
    # --------------------------------------------------------
    def record_population(self) -> None:
        for kind in SpeciesKind:
            self.population_history[int(kind)].append(self.count_species(kind))

    def log_event(self, msg: str) -> None:
        self.events_log.append((self.tick, msg))
