"""Crafting system: auto-craft recipes at camp when inputs available and tech unlocked."""

from ecs.world import World
from ecs.components import Structure
from resources import RECIPE_REGISTRY


class CraftingSystem:
    def update(self, world: World) -> None:
        for eid, struct in world.query(Structure):
            if eid not in world.entities:
                continue

            for recipe_key, recipe in RECIPE_REGISTRY.items():
                # Check tech requirement
                if recipe.required_tech and recipe.required_tech not in struct.researched_tech:
                    continue

                # Check cooldown
                timer = struct.craft_timers.get(recipe_key, 0)
                if timer > 0:
                    struct.craft_timers[recipe_key] = timer - 1
                    continue

                # Check inputs available
                if any(struct.get_res(k) < v for k, v in recipe.inputs.items()):
                    continue

                # Consume inputs
                for k, v in recipe.inputs.items():
                    struct.add_res(k, -v)

                # Produce outputs
                for k, v in recipe.outputs.items():
                    struct.add_res(k, v)

                # Reset cooldown
                struct.craft_timers[recipe_key] = recipe.craft_time
