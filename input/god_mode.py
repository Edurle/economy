"""God Mode input handler: applies player's tool actions to the world.

All methods accept grid coordinates (gx, gy), not screen pixels.
The caller (main.py) is responsible for screen-to-grid conversion via Camera.
"""

import numpy as np

from config import (
    SpeciesKind, TerrainType, GRASS_MAX, Role,
)
from ecs.world import World
from render.toolbar import (
    TOOL_PLACE_ANIMAL, TOOL_CHANGE_TERRAIN,
    TOOL_RAIN, TOOL_FIRE, TOOL_PLAGUE, TOOL_CLEAR,
    TOOL_PLACE_HUMAN, TOOL_PLACE_CAMP,
)


class GodMode:
    def __init__(self):
        self.brush_size = 1       # radius of effect for clicks

    def apply_click(self, world: World, tool: int,
                    species: SpeciesKind, terrain: TerrainType,
                    gx: int, gy: int, weather_sys=None, fire_sys=None,
                    plague_sys=None) -> None:
        """Apply the selected tool at grid coords (gx, gy)."""
        if not world.in_bounds(gx, gy):
            return

        if tool == TOOL_PLACE_ANIMAL:
            self._place_animals(world, species, gx, gy)
        elif tool == TOOL_CHANGE_TERRAIN:
            self._change_terrain(world, terrain, gx, gy)
        elif tool == TOOL_RAIN:
            if weather_sys:
                weather_sys.trigger_rain_at(world, gx, gy)
        elif tool == TOOL_FIRE:
            if fire_sys:
                fire_sys.ignite_at(world, gx, gy)
        elif tool == TOOL_PLAGUE:
            if plague_sys:
                plague_sys.infect_at(world, gx, gy)
        elif tool == TOOL_CLEAR:
            self._clear_area(world, gx, gy)
        elif tool == TOOL_PLACE_HUMAN:
            self._place_human(world, gx, gy)
        elif tool == TOOL_PLACE_CAMP:
            self._place_camp(world, gx, gy)

    def _place_animals(self, world: World, kind: SpeciesKind, gx: int, gy: int) -> None:
        for dx in range(-self.brush_size, self.brush_size + 1):
            for dy in range(-self.brush_size, self.brush_size + 1):
                x, y = gx + dx, gy + dy
                if world.is_walkable(x, y, kind):
                    if np.random.random() < 0.5:
                        world.spawn_animal(kind, x, y)

    def _change_terrain(self, world: World, terrain: TerrainType, gx: int, gy: int) -> None:
        for dx in range(-self.brush_size, self.brush_size + 1):
            for dy in range(-self.brush_size, self.brush_size + 1):
                x, y = gx + dx, gy + dy
                if world.in_bounds(x, y):
                    world.terrain[x, y] = terrain
                    if terrain == TerrainType.GRASSLAND:
                        world.grass_level[x, y] = GRASS_MAX * 0.5
                    elif terrain in (TerrainType.WATER, TerrainType.DESERT,
                                     TerrainType.MOUNTAIN, TerrainType.SNOW):
                        world.grass_level[x, y] = 0

    def _clear_area(self, world: World, gx: int, gy: int) -> None:
        from ecs.components import Position, Species
        world.grass_level[gx, gy] = 0
        to_remove = []
        for eid, pos, sp in world.query(Position, Species):
            if eid in world.entities:
                if abs(pos.x - gx) <= self.brush_size and abs(pos.y - gy) <= self.brush_size:
                    to_remove.append(eid)
        for eid in to_remove:
            world.remove_entity(eid)

    def _place_human(self, world: World, gx: int, gy: int) -> None:
        """Place a human near (gx,gy), assigned to nearest camp or new camp."""
        if not world.is_walkable(gx, gy, SpeciesKind.HUMAN):
            return
        camps = world.get_camps()
        if camps:
            camp_eid = camps[0][0]
            tribe_id = camps[0][2].tribe_id
        else:
            camp_eid = world.spawn_camp(gx, gy)
            tribe_id = 0
        role = int(np.random.choice([Role.HUNTER, Role.GATHERER, Role.BUILDER]))
        world.spawn_human(gx, gy, tribe_id=tribe_id, role=role, home_camp=camp_eid)

    def _place_camp(self, world: World, gx: int, gy: int) -> None:
        """Place a camp at (gx,gy)."""
        if not world.in_bounds(gx, gy):
            return
        camps = world.get_camps()
        tribe_id = camps[0][2].tribe_id if camps else 0
        world.spawn_camp(gx, gy, tribe_id=tribe_id)
        world.log_event("部落建造了新营地")
