"""Gathering system: humans gather food/wood and deposit at camp.

Handles GATHERING state (consume tile resources) and RETURNING state
(deposit inventory, eat from stockpile).
"""

from config import (
    SpeciesKind, TerrainType, State,
    GATHER_FOOD_AMOUNT, GATHER_GRASS_COST, GATHER_WOOD_AMOUNT,
    HUMAN_INVENTORY_MAX, HUMAN_EAT_AMOUNT, HUMAN_EAT_ENERGY_GAIN,
)
from ecs.world import World
from ecs.components import Position, Species, Behavior, Tribe, Inventory, Vitality, Structure


class GatheringSystem:
    def update(self, world: World) -> None:
        for eid, pos, sp, behav, inv in world.query(
            Position, Species, Behavior, Inventory
        ):
            if eid not in world.entities or sp.kind != SpeciesKind.HUMAN:
                continue

            if behav.state == State.GATHERING:
                self._gather(world, pos, inv)

            elif behav.state == State.RETURNING:
                self._return_to_camp(world, eid, pos, behav, inv)

    def _gather(self, world: World, pos, inv: Inventory) -> None:
        """Gather resources from current tile."""
        tx, ty = pos.x, pos.y
        t = world.terrain[tx, ty]

        if t == TerrainType.FOREST:
            if inv.wood < HUMAN_INVENTORY_MAX:
                world.terrain[tx, ty] = TerrainType.GRASSLAND
                inv.wood += GATHER_WOOD_AMOUNT
                world.grass_level[tx, ty] = 10.0
                world.log_event("人类砍伐了一片森林")

        elif t == TerrainType.GRASSLAND:
            if inv.food < HUMAN_INVENTORY_MAX and world.grass_level[tx, ty] >= GATHER_GRASS_COST:
                world.grass_level[tx, ty] -= GATHER_GRASS_COST
                inv.food += GATHER_FOOD_AMOUNT

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

        # Deposit carried resources
        if inv.food > 0:
            camp_struct.food_stockpile += inv.food
            inv.food = 0
        if inv.wood > 0:
            camp_struct.wood_stockpile += inv.wood
            inv.wood = 0

        # Eat from stockpile if hungry
        vit = world.get_component(eid, Vitality)
        if vit and vit.energy < vit.max_energy * 0.40 and camp_struct.food_stockpile > 0:
            eat_amount = min(HUMAN_EAT_AMOUNT, camp_struct.food_stockpile)
            camp_struct.food_stockpile -= eat_amount
            vit.energy = min(vit.max_energy, vit.energy + HUMAN_EAT_ENERGY_GAIN)
