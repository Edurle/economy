"""Cleanup system: record population stats each tick."""

from ecs.world import World


class CleanupSystem:
    def update(self, world: World) -> None:
        world.record_population()
