# Resource System: Stone, Iron, Copper, Gold

## Goal
Add depletable mineral deposits (stone, iron ore, copper ore, gold ore) to mountain tiles. Add MINER role. Migrate inventory/stockpile to dict-based storage for all material resources. Food stays separate (energy system).

## Design Decisions
- Deposits deplete: finite amount per tile, becomes barren when exhausted
- Humans with MINER role can enter MOUNTAIN tiles
- Dict-based inventory: `resources: {ResourceKind: amount}` for materials, `food: int` stays separate
- New `ResourceKind` enum: WOOD, STONE, IRON_ORE, COPPER_ORE, GOLD_ORE
- New `Role.MINER = 3`

---

## Phase 1: Data Layer (config.py, components.py, world.py)

### 1.1 config.py
- Add `ResourceKind(IntEnum)`: WOOD=0, STONE=1, IRON_ORE=2, COPPER_ORE=3, GOLD_ORE=4
- Add `Role.MINER = 3`
- Add constants:
  ```
  DEPOSIT_DENSITY = 0.45       # % of mountain tiles with deposits
  DEPOSIT_AMOUNT_MIN = 20
  DEPOSIT_AMOUNT_MAX = 80
  DEPOSIT_PROBABILITIES = {STONE: 0.50, IRON_ORE: 0.25, COPPER_ORE: 0.15, GOLD_ORE: 0.10}
  MINE_AMOUNT = 5              # units per mining action
  TRIBE_INIT_MINERS = 1
  ```
- Add `RESOURCE_COLORS` dict (wood=brown, stone=gray, iron=rust, copper=orange, gold=yellow)
- Add `RESOURCE_NAMES` dict (Chinese labels)
- Add `RESOURCE_GATHER_AMOUNT` dict (per-resource yield per action: wood=5, stone=5, iron=3, copper=3, gold=2)

### 1.2 ecs/components.py
- `Inventory`: keep `food: int`, add `resources: dict = field(default_factory=dict)`
  - Helper methods: `get_res(kind) -> int`, `add_res(kind, amount)`, `total_resources -> int` (property)
- `Structure`: keep `food_stockpile: int`, add `stockpile: dict = field(default_factory=dict)`
  - Same helper methods
- Remove old `wood: int` field from Inventory, `wood_stockpile: int` from Structure

### 1.3 ecs/world.py
- Add two numpy arrays:
  - `self.deposits = np.full((GRID_W, GRID_H), -1, dtype=np.int8)` — ResourceKind or -1
  - `self.deposit_amount = np.zeros((GRID_W, GRID_H), dtype=np.float32)` — remaining amount
- `is_walkable()`: allow `SpeciesKind.HUMAN` to enter MOUNTAIN tiles (currently only DEER)
- `spawn_human()`: add MINER to default role options

---

## Phase 2: World Generation (world_gen.py)

### 2.1 Add `_generate_deposits(world)`
- Iterate MOUNTAIN tiles
- For each, roll `random() < DEPOSIT_DENSITY`
- If hit, assign deposit kind via weighted random from `DEPOSIT_PROBABILITIES`
- Set `deposit_amount` to `uniform(DEPOSIT_AMOUNT_MIN, DEPOSIT_AMOUNT_MAX)`
- Call after terrain generation in `generate_terrain()`

### 2.2 Update `_spawn_initial_tribe()`
- Add `Role.MINER: TRIBE_INIT_MINERS` to tribe composition dict

---

## Phase 3: Systems Migration

### 3.1 systems/gathering.py (15 references to migrate)
**`_gather()` method — GATHERER branch (existing):**
- `inv.wood` → `inv.get_res(ResourceKind.WOOD)` / `inv.add_res(ResourceKind.WOOD, amount)`
- `inv.food` stays as-is (food field unchanged)
- Forest→wood: `inv.add_res(ResourceKind.WOOD, RESOURCE_GATHER_AMOUNT[ResourceKind.WOOD])`

**`_gather()` method — new MINER branch:**
```python
if tribe.role == Role.MINER:
    dep_kind = world.deposits[tx, ty]
    if dep_kind >= 0 and world.deposit_amount[tx, ty] > 0:
        amount = min(MINE_AMOUNT, int(world.deposit_amount[tx, ty]))
        inv.add_res(dep_kind, amount)
        world.deposit_amount[tx, ty] -= amount
        if world.deposit_amount[tx, ty] <= 0:
            world.deposits[tx, ty] = -1
```

**`_return_to_camp()` method:**
- Deposit all resources from `inv.resources` → `camp.stockpile`, then clear
- `inv.food` → `camp.food_stockpile` (unchanged logic)
- Eating from stockpile (unchanged)

### 3.2 systems/human_ai.py (10 references)
- Line 84: `(inv.food + inv.wood) < HUMAN_INVENTORY_MAX` → `inv.food + inv.total_resources < HUMAN_INVENTORY_MAX`
- Line 84: `tribe.role == Role.GATHERER` → also handle MINER: `(tribe.role in (Role.GATHERER, Role.MINER))`
- Line 86: `inv.food > 0 or inv.wood > 0` → `inv.food > 0 or inv.total_resources > 0`
- Add MINER priority: seek nearest mountain tile with deposit → set GATHERING state
- Line 95: hunting stays HUNTER-only
- Line 106-109: builder checks `camp.get_res(ResourceKind.WOOD) >= BUILD_WOOD_COST` instead of `camp.wood_stockpile`
- Line 78: `camp_struct.food_stockpile` stays (food unchanged)

### 3.3 systems/building.py (4 references)
- `camp_struct.wood_stockpile` → `camp_struct.get_res(ResourceKind.WOOD)`
- `camp_struct.wood_stockpile -= BUILD_WOOD_COST` → `camp_struct.add_res(ResourceKind.WOOD, -BUILD_WOOD_COST)`

### 3.4 systems/predation.py (2 references)
- `inv.food = min(HUMAN_INVENTORY_MAX, inv.food + gained_food)` stays (food field unchanged)

### 3.5 systems/reproduction.py (1 reference)
- Add `Role.MINER` to child role random choice

### 3.6 systems/movement.py
- Add MINING state handling if needed (or reuse GATHERING state — MINER uses GATHERING state)

---

## Phase 4: Rendering

### 4.1 render/assets.py
- Add deposit sprites: small colored crystal/ore icons per ResourceKind (16×16)
- Add to `generate_assets()` return dict under `"deposits"` key
- Add MINER role accent color (e.g. yellow/amber) in `_draw_human()`

### 4.2 render/map_renderer.py
- New render pass: for tiles where `world.deposits[tx,ty] >= 0`, blit deposit sprite overlay
- Depleted tiles (amount=0 but deposits=-1): no overlay (already barren)
- Camp stockpile display (line 102): show total resources, not just food
- Tooltip (`render_cell_info`): show deposit kind + remaining amount for mountain tiles

### 4.3 render/ui_panel.py
- Population stats: add MINER count if any exist
- Camp info: could show resource breakdown (future)

---

## Phase 5: Other Files

### 5.1 input/god_mode.py
- Add `Role.MINER` to random role choice for PLACE_HUMAN tool

### 5.2 world_gen.py
- Already covered in Phase 2

### 5.3 main.py
- No new systems needed (GatheringSystem handles MINER via role check)
- Verify all systems work with new component shape

---

## Migration Checklist (all `inv.wood` / `.wood_stockpile` references)

| File | Line | Old | New |
|------|------|-----|-----|
| gathering.py:36 | `inv.wood < HUMAN_INVENTORY_MAX` | `inv.total_resources < HUMAN_INVENTORY_MAX` |
| gathering.py:38 | `inv.wood += GATHER_WOOD_AMOUNT` | `inv.add_res(ResourceKind.WOOD, ...)` |
| gathering.py:43 | `inv.food < HUMAN_INVENTORY_MAX` | `(inv.food + inv.total_resources) < HUMAN_INVENTORY_MAX` |
| gathering.py:45 | `inv.food += GATHER_FOOD_AMOUNT` | unchanged |
| gathering.py:62-64 | `inv.food > 0` / deposit food | unchanged |
| gathering.py:65-67 | `inv.wood > 0` / deposit wood | iterate `inv.resources` dict |
| human_ai.py:84 | `inv.food + inv.wood` | `inv.food + inv.total_resources` |
| human_ai.py:86 | `inv.food > 0 or inv.wood > 0` | `inv.food > 0 or inv.total_resources > 0` |
| human_ai.py:109 | `camp.wood_stockpile >= BUILD_WOOD_COST` | `camp.get_res(WOOD) >= BUILD_WOOD_COST` |
| building.py:29 | `camp.wood_stockpile >= BUILD_WOOD_COST` | `camp.get_res(WOOD) >= BUILD_WOOD_COST` |
| building.py:30 | `camp.wood_stockpile -= BUILD_WOOD_COST` | `camp.add_res(WOOD, -BUILD_WOOD_COST)` |
| map_renderer.py:102 | `struct.food_stockpile` | unchanged (food bar stays) |

---

## Testing
1. Headless: spawn world, verify deposits generated on mountains
2. Headless: run 300 ticks, verify MINERs mine deposits, deposits deplete
3. Headless: verify wood still works (FOREST→GRASSLAND conversion)
4. Headless: verify camp stockpile accumulates stone/iron/copper/gold
5. Visual: deposit sprites visible on mountain tiles
6. Visual: MINER sprite distinct from other roles
7. Visual: depleted deposits disappear from map
