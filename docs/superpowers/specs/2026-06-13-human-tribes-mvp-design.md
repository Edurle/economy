# Human Tribes MVP Design

## Overview

Add humans as a new `SpeciesKind.HUMAN` in the existing ECS, organized into tribes. MVP scope: 1 tribe, basic survival mechanics (hunting, gathering, building). Architecture supports future expansion to multiple tribes, technology progression, and diplomacy.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Human role | Autonomous civilization | Fits god-view gameplay; player observes and intervenes |
| Tribe differentiation | Cultural + tech (future) | MVP: single tribe; structure for expansion |
| Ecosystem interaction | Deep | Humans hunt animals, gather resources, change terrain |
| Tribe relations | War + diplomacy (future) | MVP: single tribe; later expansion |
| Implementation | SpeciesKind in existing ECS | Reuses 80% of infrastructure |

## 1. Human Entity Design

### 1.1 Components

Humans reuse existing components and add two new ones:

**Existing (reused):**
- `Position` — grid location
- `Vitality` — energy, hydration, age, max values
- `Species` — kind = `SpeciesKind.HUMAN`
- `Behavior` — state, target
- `Reproduction` — cooldown

**New: `Tribe`**
```python
@dataclass
class Tribe:
    tribe_id: int       # which tribe this human belongs to
    role: int           # Role enum: HUNTER, GATHERER, BUILDER
    home_camp: int      # entity id of camp this human belongs to (-1 if none)
```

**New: `Inventory`**
```python
@dataclass
class Inventory:
    food: int = 0       # carried food (max 20)
    wood: int = 0       # carried wood (max 20)
```

**New: `Structure` (for camp entities)**
```python
@dataclass
class Structure:
    kind: int           # StructureKind enum: CAMP
    tribe_id: int       # owning tribe
    food_stockpile: int # stored food
    wood_stockpile: int # stored wood
    capacity: int       # max population this camp supports
    territory_radius: int  # preferred activity radius
```

### 1.2 Enums

```python
class Role(IntEnum):
    HUNTER = 0
    GATHERER = 1
    BUILDER = 2

class StructureKind(IntEnum):
    CAMP = 0
```

### 1.3 Human Species Params

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
    "food_gain":     0,       # humans eat from stockpile, not grass
    "population_cap": 30,
    "color":         (180, 140, 100),
    "size":          2,
}
```

### 1.4 Camp Entity

A camp is a static entity placed on the grid:
- Has `Position`, `Structure` (which includes `tribe_id`)
- Does NOT have Vitality/Behavior/Reproduction/Tribe
- Does NOT have Vitality/Behavior/Reproduction
- Blocks animal movement (not walkable for animals)
- Walkable for humans (it's their home)
- Renders as tent + campfire icon

## 2. Human AI (HumanAISystem)

New system that runs BEFORE the regular `AISystem`. Sets `Behavior` for all HUMAN entities. Regular `AISystem` skips HUMAN entities.

### 2.1 Decision Priority Tree

| Priority | Condition | Action |
|----------|-----------|--------|
| 1. Flee | Wolves within vision AND count >= 2 | FLEE from nearest wolf |
| 2. Drink | hydration < 25% max | SEEKING_WATER |
| 3. Eat | energy < 40% max AND camp food_stockpile > 0 | RETURN_TO_CAMP, eat from stockpile |
| 4. Gather | role=GATHERER AND inventory not full | FORAGING (gather berries/wood) |
| 5. Hunt | role=HUNTER AND camp food_stockpile < 20 | HUNTING nearest animal |
| 6. Build | role=BUILDER AND population >= capacity - 2 AND wood_stockpile >= 10 | BUILDING (go to camp, consume wood) |
| 7. Reproduce | energy >= breed_energy AND cooldown=0 AND camp has capacity | MATING |
| 8. Idle | default | Return to camp vicinity, wander |

### 2.2 State Machine

New states added to `State` enum:
```python
RETURNING   = 9   # heading back to camp to deposit/store
GATHERING   = 10  # actively gathering resources at a tile
BUILDING    = 11  # building/expanding at camp
```

## 3. Ecosystem Interaction

### 3.1 Hunting (extends PredationSystem)

Humans hunt animals via the existing `PredationSystem` with these rules:
- Prey map for HUMAN: `{RABBIT: 0.80, SHEEP: 0.60, DEER: 0.40, FOX: 0.50, WOLF: 0.30}`
- Deer require 2+ adjacent humans (same rule as wolf-deer)
- On kill: human gains food in Inventory (not direct energy), prey entity removed
- Food transfer: `gained_food = prey_max_energy * 0.3` (carry back to camp)

Wolves can attack humans:
- Wolf hunts HUMAN with 0.25 success rate
- On kill: human entity removed, wolf gains energy

### 3.2 Gathering (new GatheringSystem)

When human is on a tile in GATHERING state:
- **Grassland**: `grass_level -= 5`, `inventory.food += 3`
- **Forest**: convert `FOREST → GRASSLAND`, `inventory.wood += 5`
- Grass below 0: cannot gather (tile depleted)
- Forest conversion is permanent (deforestation effect)

When inventory is full OR camp food is sufficient, human returns to camp:
- Deposits food/wood into camp stockpile
- Resumes gathering

### 3.3 Building (new BuildingSystem)

When BUILDER human is at camp with enough wood:
- Expand camp capacity: `capacity += 2`, `wood_stockpile -= 10`
- Trigger condition: `population >= capacity - 2` (approaching limit)

### 3.4 Eating

When human is at camp and hungry:
- Consume from `food_stockpile`: `stockpile -= 10`, `energy += 40`
- If stockpile is empty: human enters GATHERING/HUNTING to get food

## 4. Camp Lifecycle

### 4.1 Camp Placement

Initial camp placed at world generation:
- On GRASSLAND tile near water source
- Initial values: `food_stockpile=50, wood_stockpile=20, capacity=8, territory_radius=8`

### 4.2 Camp Mechanics

- Humans prefer to stay within `territory_radius` of their camp
- If a human strays too far, priority shifts to RETURNING
- Camp food_stockpile depletes as humans eat
- Camp wood_stockpile depletes as builders expand
- If food_stockpile = 0 for extended time: humans starve (energy drops)

## 5. Rendering

### 5.1 Human Sprite (16x16)

Procedurally generated pixel art:
- Brown tunic body (distinct from animal shapes)
- Skin-tone head (beige circle)
- Small enough to be distinguishable at zoom 1.0
- Role indicated by accent color: Hunter=red, Gatherer=green, Builder=blue

### 5.2 Camp Sprite (16x16)

- Triangle tent shape (brown/tan)
- Small campfire (orange/yellow) next to tent
- Smoke particle effect (optional)
- Food stockpile bar above camp (green progress bar)

### 5.3 Territory Overlay (optional, future)

- Semi-transparent colored circle showing camp territory
- Toggle with a key

## 6. God Mode Integration

### 6.1 New Tools

| Tool | Action |
|------|--------|
| Place Human | Spawn HUMAN at grid position, assign to nearest camp (or create new camp if none) |
| Remove Human | Remove human entity |
| Place Camp | Create camp entity at grid position |
| Remove Camp | Remove camp entity, humans become campless |

### 6.2 Toolbar

Add human/camp buttons to existing toolbar. Place Human tool cycles through roles (or uses a sub-menu).

## 7. UI Panel

### 7.1 Population Stats

Add row: `人类: N` in population display.

### 7.2 Event Log

New event types:
- `"部落建造了新营地"` — camp placed
- `"猎手杀死了一头鹿"` — human killed a deer
- `"营地食物耗尽"` — camp stockpile hit 0
- `"部落人口达到 N"` — population milestone
- `"人类砍伐了一片森林"` — deforestation event

## 8. World Generation

In `world_gen.py`:
- After animal population, spawn 1 camp at a good location (grassland near water, away from wolf clusters)
- Spawn 5 humans at/near camp (2 hunters, 2 gatherers, 1 builder)
- Initial roles: randomized but weighted

## 9. System Execution Order

Updated main loop system order:
```
SeasonSystem
WeatherSystem
GrassSystem
FireSystem
PlagueSystem
HumanAISystem          ← NEW (before AISystem)
AISystem               ← modified: skip HUMAN
MovementSystem         ← modified: humans avoid camps, animals avoid camps
ForagingSystem         ← skip HUMAN
GatheringSystem        ← NEW
PredationSystem        ← modified: human hunting + wolf attacks human
HydrationSystem        ← unchanged (works for humans)
BuildingSystem         ← NEW
ReproductionSystem     ← modified: human reproduction at camp
AgingSystem            ← unchanged
CleanupSystem          ← modified: handle camp removal
```

## 10. Config Additions

```python
# Human roles
class Role(IntEnum):
    HUNTER = 0
    GATHERER = 1
    BUILDER = 2

# Camp/tribe params
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
CAMP_FOOD_TRANSFER = 0.3  # prey_max_energy * this = food gained on kill

# Human prey map (separate from animal predator system)
HUMAN_PREY_MAP = {
    SpeciesKind.RABBIT: 0.80,
    SpeciesKind.SHEEP: 0.60,
    SpeciesKind.DEER: 0.40,
    SpeciesKind.FOX: 0.50,
    SpeciesKind.WOLF: 0.30,
}
WOLF_HUNT_HUMAN_CHANCE = 0.25

# Initial tribe spawn
TRIBE_INIT_POPULATION = 5
TRIBE_INIT_HUNTERS = 2
TRIBE_INIT_GATHERERS = 2
TRIBE_INIT_BUILDERS = 1
```

## 11. Files to Create/Modify

### New files:
- `ecs/components.py` — add `Tribe`, `Inventory`, `Structure` dataclasses
- `systems/human_ai.py` — `HumanAISystem`
- `systems/gathering.py` — `GatheringSystem`
- `systems/building.py` — `BuildingSystem`

### Modified files:
- `config.py` — add HUMAN params, Role enum, camp params, human prey map
- `ecs/world.py` — add camp entity creation, camp querying helpers
- `ecs/components.py` — add new State values (RETURNING, GATHERING, BUILDING)
- `systems/ai.py` — skip HUMAN entities
- `systems/movement.py` — camp collision rules
- `systems/predation.py` — human hunting + wolf attacks human
- `systems/reproduction.py` — human reproduction at camp
- `systems/cleanup.py` — handle camp entity removal
- `render/assets.py` — human + camp sprites
- `render/map_renderer.py` — render camp entities
- `render/ui_panel.py` — human population display
- `input/god_mode.py` — place/remove human + camp
- `world_gen.py` — spawn initial tribe
- `main.py` — add new systems to loop, add god mode tools

## 12. Future Expansion (out of MVP scope)

- Multiple tribes with territory borders
- Tribe diplomacy (war, alliance, trade)
- Technology tree (stone → bronze → iron age)
- Domestication (humans raise sheep/cattle)
- Agriculture (humans plant crops, new terrain type)
- Tribe split/merge mechanics
