"""Gathering system: humans gather food/wood/minerals and deposit at camp.

Handles GATHERING state (consume tile resources) and RETURNING state
(deposit inventory, eat from stockpile).
"""

from config import (
    SpeciesKind, TerrainType, State,
    GATHER_FOOD_AMOUNT, GATHER_GRASS_COST,
    HUMAN_INVENTORY_MAX, HUMAN_EAT_AMOUNT, HUMAN_EAT_ENERGY_GAIN,
    Role,
)
from ecs.world import World
from ecs.components import Position, Species, Behavior, Tribe, Inventory, Vitality, Structure
from resources import DEPOSITABLE, MINE_YIELD, GATHER_WOOD_AMOUNT, deposit_key


class GatheringSystem:
    def update(self, world: World) -> None:
        for eid, pos, sp, behav, inv in world.query(
            Position, Species, Behavior, Inventory
        ):
            if eid not in world.entities or sp.kind != SpeciesKind.HUMAN:
                continue

            tribe = world.get_component(eid, Tribe)

            if behav.state == State.GATHERING:
                self._gather(world, pos, inv, tribe)

            elif behav.state == State.MINING:
                self._mine(world, pos.x, pos.y, inv)

            elif behav.state == State.RETURNING:
                self._return_to_camp(world, eid, pos, behav, inv)

    def _gather(self, world: World, pos, inv: Inventory, tribe) -> None:
        """Gather resources from current tile (GATHERER only)."""
        tx, ty = pos.x, pos.y
        t = world.terrain[tx, ty]

        if t == TerrainType.FOREST:
            if inv.total_resources < HUMAN_INVENTORY_MAX:
                world.terrain[tx, ty] = TerrainType.GRASSLAND
                inv.add_res("wood", GATHER_WOOD_AMOUNT)
                world.grass_level[tx, ty] = 10.0
                world.log_event("人类砍伐了一片森林")

        elif t == TerrainType.GRASSLAND:
            if (inv.food + inv.total_resources) < HUMAN_INVENTORY_MAX and world.grass_level[tx, ty] >= GATHER_GRASS_COST:
                world.grass_level[tx, ty] -= GATHER_GRASS_COST
                inv.food += GATHER_FOOD_AMOUNT

    def _mine(self, world: World, tx: int, ty: int, inv: Inventory) -> None:
        """Mine mineral deposits from a mountain tile."""
        dep_idx = int(world.deposits[tx, ty])
        if dep_idx < 0 or world.deposit_amount[tx, ty] <= 0:
            return
        if inv.total_resources >= HUMAN_INVENTORY_MAX:
            return

        res_key = deposit_key(dep_idx)
        if res_key is None:
            return

        yield_amt = MINE_YIELD.get(res_key, 3)
        amount = min(yield_amt, int(world.deposit_amount[tx, ty]))
        inv.add_res(res_key, amount)
        world.deposit_amount[tx, ty] -= amount
        if world.deposit_amount[tx, ty] <= 0:
            world.deposits[tx, ty] = -1
            world.log_event(f"{res_key} 矿脉已耗尽")

    def _return_to_camp(self, world: World, eid: int, pos, behav, inv: Inventory) -> None:
        """Deposit inventory and eat at camp."""
        if behav.target < 0:
            return
        camp_struct = world.get_component(behav.target, Structure)
        camp_pos = world.get_component(behav.target, Position)
        if camp_struct is None or camp_pos is None:
            return

        at_camp = (pos.x == camp_pos.x or
                   abs(pos.x - camp_pos.x) + abs(pos.y - camp_pos.y) <= 1)
        if not at_camp:
            return

        # Deposit carried food
        if inv.food > 0:
            camp_struct.food_stockpile += inv.food
            inv.food = 0

        # Deposit carried resources
        for res_key, amount in list(inv.resources.items()):
            camp_struct.add_res(res_key, amount)
        inv.resources.clear()

        # Eat from stockpile if hungry
        vit = world.get_component(eid, Vitality)
        if vit and vit.energy < vit.max_energy * 0.40 and camp_struct.food_stockpile > 0:
            eat_amount = min(HUMAN_EAT_AMOUNT, camp_struct.food_stockpile)
            camp_struct.food_stockpile -= eat_amount
            vit.energy = min(vit.max_energy, vit.energy + HUMAN_EAT_ENERGY_GAIN)
