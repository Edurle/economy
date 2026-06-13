"""Movement system: moves animals based on their behaviour state."""

import numpy as np

from config import (
    GRID_W, GRID_H, State, SpeciesKind, TerrainType, SPECIES_PARAMS,
)
from ecs.world import World
from ecs.components import Position, Species, Behavior


class MovementSystem:
    DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def update(self, world: World) -> None:
        animals = world.query(Position, Species, Behavior)
        occupied: set[tuple[int, int]] = set()

        # Build occupied set for collision avoidance (one animal per cell)
        for eid, pos, sp, behav in animals:
            if eid in world.entities:
                occupied.add((pos.x, pos.y))

        for eid, pos, sp, behav in animals:
            if eid not in world.entities:
                continue
            params = SPECIES_PARAMS[sp.kind]
            steps = params["speed"]

            # Large animals slowed in forest
            if world.terrain[pos.x, pos.y] == TerrainType.FOREST:
                if sp.kind in (SpeciesKind.DEER, SpeciesKind.WOLF):
                    steps = max(1, steps - 1)

            for _ in range(steps):
                occupied.discard((pos.x, pos.y))
                dx, dy = self._choose_direction(world, eid, pos, sp, behav, occupied)
                if dx == 0 and dy == 0:
                    occupied.add((pos.x, pos.y))
                    break
                nx, ny = pos.x + dx, pos.y + dy
                if world.is_walkable(nx, ny, sp.kind) and (nx, ny) not in occupied:
                    pos.x, pos.y = nx, ny
                    occupied.add((nx, ny))
                else:
                    occupied.add((pos.x, pos.y))
                    break

    def _choose_direction(self, world, eid, pos, sp, behav, occupied):
        state = behav.state

        if state == State.SEEKING_WATER:
            return self._toward_water(world, pos, sp)

        if state == State.FLEEING and behav.target >= 0:
            threat_pos = world.get_component(behav.target, Position)
            if threat_pos:
                return self._away_from(pos, threat_pos.x, threat_pos.y, world, sp)

        if state == State.HUNTING and behav.target >= 0:
            prey_pos = world.get_component(behav.target, Position)
            if prey_pos:
                return self._toward(pos, prey_pos.x, prey_pos.y, world, sp, occupied)

        if state == State.FORAGING:
            return self._toward_grass(world, pos, sp, occupied)

        if state == State.MATING and behav.target >= 0:
            mate_pos = world.get_component(behav.target, Position)
            if mate_pos:
                return self._toward(pos, mate_pos.x, mate_pos.y, world, sp, occupied)

        if state == State.RETURNING and behav.target >= 0:
            target_pos = world.get_component(behav.target, Position)
            if target_pos:
                return self._toward(pos, target_pos.x, target_pos.y, world, sp, occupied)

        if state == State.GATHERING:
            return self._toward_grass(world, pos, sp, occupied)

        if state == State.BUILDING:
            return (0, 0)

        # IDLE: random walk
        return self._random_dir(world, pos, sp)

    def _toward(self, pos, tx, ty, world, sp, occupied):
        """Move toward target (tx, ty)."""
        best = (0, 0)
        best_dist = abs(pos.x - tx) + abs(pos.y - ty)
        for dx, dy in self.DIRS:
            nx, ny = pos.x + dx, pos.y + dy
            if not world.is_walkable(nx, ny, sp.kind) or (nx, ny) in occupied:
                continue
            d = abs(nx - tx) + abs(ny - ty)
            if d < best_dist:
                best_dist = d
                best = (dx, dy)
        return best

    def _away_from(self, pos, tx, ty, world, sp):
        """Move away from threat at (tx, ty)."""
        best = (0, 0)
        best_dist = abs(pos.x - tx) + abs(pos.y - ty)
        for dx, dy in self.DIRS:
            nx, ny = pos.x + dx, pos.y + dy
            if not world.is_walkable(nx, ny, sp.kind):
                continue
            d = abs(nx - tx) + abs(ny - ty)
            if d > best_dist:
                best_dist = d
                best = (dx, dy)
        return best

    def _toward_water(self, world, pos, sp):
        """Move toward nearest water cell."""
        best = (0, 0)
        best_dist = float('inf')
        radius = 8
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = pos.x + dx, pos.y + dy
                if world.in_bounds(nx, ny) and world.terrain[nx, ny] == TerrainType.WATER:
                    d = abs(dx) + abs(dy)
                    if d < best_dist:
                        best_dist = d
                        # Step toward it
                        sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
                        sy = 1 if dy > 0 else (-1 if dy < 0 else 0)
                        # Prefer x if closer in x, else y
                        if abs(dx) >= abs(dy) and sx != 0:
                            step = (sx, 0)
                        elif sy != 0:
                            step = (0, sy)
                        else:
                            step = (sx, sy)
                        if world.is_walkable(pos.x + step[0], pos.y + step[1], sp.kind):
                            best = step
        return best

    def _toward_grass(self, world, pos, sp, occupied):
        """Move toward nearest cell with grass_level > 20."""
        best = (0, 0)
        best_dist = float('inf')
        radius = 5
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = pos.x + dx, pos.y + dy
                if world.in_bounds(nx, ny) and world.grass_level[nx, ny] > 20:
                    d = abs(dx) + abs(dy)
                    if d < best_dist:
                        best_dist = d
                        sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
                        sy = 1 if dy > 0 else (-1 if dy < 0 else 0)
                        if abs(dx) >= abs(dy) and sx != 0:
                            step = (sx, 0)
                        elif sy != 0:
                            step = (0, sy)
                        else:
                            step = (0, 0)
                        if step != (0, 0) and world.is_walkable(pos.x + step[0], pos.y + step[1], sp.kind):
                            best = step
        return best

    def _random_dir(self, world, pos, sp):
        dirs = list(self.DIRS)
        np.random.shuffle(dirs)
        for dx, dy in dirs:
            if world.is_walkable(pos.x + dx, pos.y + dy, sp.kind):
                return (dx, dy)
        return (0, 0)
