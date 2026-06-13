"""Building system: builders expand camp capacity using wood stockpile."""

from config import (
    SpeciesKind, State, BUILD_CAPACITY_GAIN, BUILD_WOOD_COST,
)
from ecs.world import World
from ecs.components import Position, Species, Behavior, Structure


class BuildingSystem:
    def update(self, world: World) -> None:
        for eid, pos, sp, behav in world.query(Position, Species, Behavior):
            if eid not in world.entities or sp.kind != SpeciesKind.HUMAN:
                continue
            if behav.state != State.BUILDING or behav.target < 0:
                continue

            camp_struct = world.get_component(behav.target, Structure)
            camp_pos = world.get_component(behav.target, Position)
            if camp_struct is None or camp_pos is None:
                continue

            # Must be at or adjacent to camp
            dist = abs(pos.x - camp_pos.x) + abs(pos.y - camp_pos.y)
            if dist > 1:
                continue

            # Expand camp
            if camp_struct.get_res("wood") >= BUILD_WOOD_COST:
                camp_struct.add_res("wood", -BUILD_WOOD_COST)
                camp_struct.capacity += BUILD_CAPACITY_GAIN
                world.log_event(
                    f"营地扩建！容量提升至 {camp_struct.capacity}"
                )
