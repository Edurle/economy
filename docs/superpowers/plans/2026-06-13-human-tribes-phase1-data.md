# Human Tribes MVP — Phase 1: Data Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add human entity data model (config params, new components, camp/human factories in World) so that a human + camp can be created and queried headlessly.

**Architecture:** Humans are `SpeciesKind.HUMAN` entities in the existing ECS with two new components (`Tribe`, `Inventory`). Camps are static entities with a `Structure` component. World gains factory methods for both.

**Tech Stack:** Python 3.11, pygame-ce, numpy, ECS pattern

**Spec:** `docs/superpowers/specs/2026-06-13-human-tribes-mvp-design.md`

---

### Task 1: Config additions — enums, params, constants

**Files:**
- Modify: `config.py`

- [ ] **Step 1: Add HUMAN to SpeciesKind and new states**

In `config.py`, add `HUMAN = 5` to the `SpeciesKind` enum:

```python
class SpeciesKind(IntEnum):
    RABBIT = 0
    SHEEP  = 1
    DEER   = 2
    FOX    = 3
    WOLF   = 4
    HUMAN  = 5
```

Add new states to the `State` enum:

```python
class State(IntEnum):
    IDLE           = 0
    FORAGING       = 1
    FLEEING        = 2
    HUNTING        = 3
    MATING         = 4
    SEEKING_WATER  = 5
    RETURNING      = 9
    GATHERING      = 10
    BUILDING       = 11
```

- [ ] **Step 2: Add Role and StructureKind enums**

Add after the `State` enum:

```python
class Role(IntEnum):
    HUNTER   = 0
    GATHERER = 1
    BUILDER  = 2

class StructureKind(IntEnum):
    CAMP = 0
```

- [ ] **Step 3: Add human species params**

Add to `SPECIES_PARAMS` dict, after WOLF:

```python
    SpeciesKind.HUMAN: {
        "name":          "人类",
        "init_energy":   100,
        "max_energy":    150,
        "init_hydration": 70,
        "max_hydration": 100,
        "max_age":       120,
        "vision":        6,
        "speed":         1,
        "breed_energy":  80,
        "breed_cooldown": 20,
        "food_gain":     0,
        "population_cap": 30,
        "color":         (180, 140, 100),
        "size":          2,
    },
```

- [ ] **Step 4: Add tribe/camp/gathering constants**

Add a new section at the end of config.py (before nothing — just append):

```python
# ============================================================
# Human / Tribe Parameters
# ============================================================
CAMP_INIT_FOOD = 50
CAMP_INIT_WOOD = 20
CAMP_INIT_CAPACITY = 8
CAMP_TERRITORY_RADIUS = 8
HUMAN_INVENTORY_MAX = 20
GATHER_FOOD_AMOUNT = 3
GATHER_GRASS_COST = 5
GATHER_WOOD_AMOUNT = 5
BUILD_CAPACITY_GAIN = 2
BUILD_WOOD_COST = 10
HUMAN_EAT_AMOUNT = 10
HUMAN_EAT_ENERGY_GAIN = 40
CAMP_FOOD_TRANSFER = 0.3

HUMAN_PREY_MAP = {
    SpeciesKind.RABBIT: 0.80,
    SpeciesKind.SHEEP: 0.60,
    SpeciesKind.DEER: 0.40,
    SpeciesKind.FOX: 0.50,
    SpeciesKind.WOLF: 0.30,
}
WOLF_HUNT_HUMAN_CHANCE = 0.25

TRIBE_INIT_POPULATION = 5
TRIBE_INIT_HUNTERS = 2
TRIBE_INIT_GATHERERS = 2
TRIBE_INIT_BUILDERS = 1
```

- [ ] **Step 5: Update human-related sets**

Find the `HERBIVORES` and `CARNIVORES` sets and add humans to neither (they have their own behavior). But we need humans to NOT be treated as herbivores or carnivores by existing code. Verify the existing sets:

```python
HERBIVORES = {SpeciesKind.RABBIT, SpeciesKind.SHEEP, SpeciesKind.DEER}
CARNIVORES = {SpeciesKind.FOX, SpeciesKind.WOLF}
```

These are fine — HUMAN is not in either set.

- [ ] **Step 6: Add TERRAIN_COLORS for camp rendering reference**

No new terrain needed. Camps are rendered as entity sprites, not terrain tiles.

- [ ] **Step 7: Verify config imports without errors**

Run:
```bash
cd /home/dzj/file/simulate && python -c "
from config import SpeciesKind, State, Role, StructureKind, SPECIES_PARAMS, HUMAN_PREY_MAP, CAMP_INIT_FOOD
print('HUMAN:', SpeciesKind.HUMAN, '->', SPECIES_PARAMS[SpeciesKind.HUMAN]['name'])
print('States:', State.RETURNING, State.GATHERING, State.BUILDING)
print('Roles:', list(Role))
print('Structures:', list(StructureKind))
print('Camp food:', CAMP_INIT_FOOD)
print('Prey map:', {k.name: v for k, v in HUMAN_PREY_MAP.items()})
"
```
Expected: all values print without errors.

- [ ] **Step 8: Commit**

```bash
git add config.py
git commit -m "feat: add HUMAN species config, Role/StructureKind enums, camp params"
```

---

### Task 2: New components — Tribe, Inventory, Structure

**Files:**
- Modify: `ecs/components.py`

- [ ] **Step 1: Add new component dataclasses**

Add imports at the top of `ecs/components.py`:

```python
from config import State, SpeciesKind, Role, StructureKind
```

Add three new dataclasses after the existing `Tag` class:

```python
@dataclass
class Tribe:
    tribe_id: int = 0
    role: int = Role.HUNTER          # Role enum value
    home_camp: int = -1              # entity id of camp (-1 = none)


@dataclass
class Inventory:
    food: int = 0
    wood: int = 0


@dataclass
class Structure:
    kind: int = StructureKind.CAMP   # StructureKind enum value
    tribe_id: int = 0
    food_stockpile: int = 0
    wood_stockpile: int = 0
    capacity: int = 8
    territory_radius: int = 8
```

- [ ] **Step 2: Verify components import and instantiate**

Run:
```bash
cd /home/dzj/file/simulate && python -c "
from ecs.components import Tribe, Inventory, Structure
from config import Role, StructureKind
t = Tribe(tribe_id=0, role=Role.GATHERER, home_camp=5)
inv = Inventory(food=10, wood=3)
camp = Structure(kind=StructureKind.CAMP, tribe_id=0, food_stockpile=50, wood_stockpile=20, capacity=8, territory_radius=8)
print(f'Tribe: {t}')
print(f'Inventory: {inv}')
print(f'Structure: {camp}')
"
```
Expected: all three print without errors.

- [ ] **Step 3: Commit**

```bash
git add ecs/components.py
git commit -m "feat: add Tribe, Inventory, Structure components"
```

---

### Task 3: World camp/human factories + walkability

**Files:**
- Modify: `ecs/world.py`

- [ ] **Step 1: Add imports for new components**

In `ecs/world.py`, update the import from `ecs.components`:

```python
from ecs.components import (
    Position, Vitality, Species, Behavior, Reproduction, Health,
    Tribe, Inventory, Structure,
)
```

Also add to the config import:

```python
from config import (
    GRID_W, GRID_H, SEASON_LENGTH, GRASS_MAX, GRASS_GROWTH_RATE,
    TerrainType, SpeciesKind, Season, SPECIES_PARAMS, Role,
    CAMP_INIT_FOOD, CAMP_INIT_WOOD, CAMP_INIT_CAPACITY, CAMP_TERRITORY_RADIUS,
)
```

- [ ] **Step 2: Add `spawn_camp` method**

Add after `spawn_animal` in the `World` class:

```python
    def spawn_camp(self, x: int, y: int, tribe_id: int = 0) -> int:
        """Create a camp structure entity."""
        eid = self.create_entity()
        self.add_component(eid, Position(x=x, y=y))
        self.add_component(eid, Structure(
            tribe_id=tribe_id,
            food_stockpile=CAMP_INIT_FOOD,
            wood_stockpile=CAMP_INIT_WOOD,
            capacity=CAMP_INIT_CAPACITY,
            territory_radius=CAMP_TERRITORY_RADIUS,
        ))
        return eid
```

- [ ] **Step 3: Add `spawn_human` method**

Add after `spawn_camp`:

```python
    def spawn_human(self, x: int, y: int, tribe_id: int = 0,
                    role: int = Role.HUNTER, home_camp: int = -1) -> int:
        """Create a human entity with all required components."""
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
```

- [ ] **Step 4: Update `is_walkable` to block camp tiles for animals**

Modify `is_walkable` to check for camp entities. Add a cached set of camp positions:

```python
    def is_walkable(self, x: int, y: int, kind: SpeciesKind | None = None) -> bool:
        """Can an entity of *kind* enter cell (x, y)?"""
        if not self.in_bounds(x, y):
            return False
        t = self.terrain[x, y]
        if t == TerrainType.WATER:
            return False
        if t == TerrainType.MOUNTAIN:
            return kind == SpeciesKind.DEER
        # Camps block animals but not humans
        if kind != SpeciesKind.HUMAN and (x, y) in self.camp_positions:
            return False
        return True
```

- [ ] **Step 5: Add `camp_positions` set and rebuild method**

In `__init__`, add:

```python
        self.camp_positions: set[tuple[int, int]] = set()
```

Add a method to rebuild camp positions (call after spawning/removing camps):

```python
    def rebuild_camp_positions(self) -> None:
        """Rebuild the set of grid cells occupied by camps."""
        self.camp_positions.clear()
        for eid, pos, struct in self.query(Position, Structure):
            if eid in self.entities:
                self.camp_positions.add((pos.x, pos.y))
```

- [ ] **Step 6: Add `get_camps` helper**

```python
    def get_camps(self, tribe_id: int | None = None) -> list[tuple[int, Position, Structure]]:
        """Return list of (eid, pos, struct) for camps, optionally filtered by tribe."""
        result = []
        for eid, pos, struct in self.query(Position, Structure):
            if eid in self.entities:
                if tribe_id is None or struct.tribe_id == tribe_id:
                    result.append((eid, pos, struct))
        return result
```

- [ ] **Step 7: Verify with headless test**

Run:
```bash
cd /home/dzj/file/simulate && python -c "
from ecs.world import World
from config import SpeciesKind, Role, TerrainType
import numpy as np

w = World()
w.terrain[:] = TerrainType.GRASSLAND

# Spawn a camp
camp_eid = w.spawn_camp(32, 32, tribe_id=0)
w.rebuild_camp_positions()
print(f'Camp spawned at (32,32), eid={camp_eid}')
print(f'Camp positions: {w.camp_positions}')

# Spawn humans near camp
h1 = w.spawn_human(33, 32, tribe_id=0, role=Role.HUNTER, home_camp=camp_eid)
h2 = w.spawn_human(31, 32, tribe_id=0, role=Role.GATHERER, home_camp=camp_eid)
print(f'Hunters spawned: {h1}, {h2}')
print(f'Total entities: {len(w.entities)}')

# Test walkability — animals can't enter camp, humans can
print(f'Rabbit can enter camp tile: {w.is_walkable(32, 32, SpeciesKind.RABBIT)}')
print(f'Human can enter camp tile: {w.is_walkable(32, 32, SpeciesKind.HUMAN)}')

# Test count_species for humans
print(f'Human count: {w.count_species(SpeciesKind.HUMAN)}')

# Test get_camps
camps = w.get_camps(tribe_id=0)
print(f'Camps: {len(camps)}, first camp capacity={camps[0][2].capacity}')
"
```
Expected: Camp blocks rabbit, allows human; human count = 2; camp found.

- [ ] **Step 8: Commit**

```bash
git add ecs/world.py
git commit -m "feat: add spawn_camp, spawn_human, camp walkability to World"
```
