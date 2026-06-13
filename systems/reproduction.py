"""Reproduction system: adjacent same-species animals breed when conditions met."""

import numpy as np

from config import (
    SpeciesKind, SPECIES_PARAMS, OFFSPRING_ENERGY_RATIO,
)
from ecs.world import World
from ecs.components import Position, Vitality, Species, Behavior, Reproduction


class ReproductionSystem:
    DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def update(self, world: World) -> None:
        # Build position lookup
        pos_lookup: dict[tuple[int, int], list[int]] = {}
        for eid, pos, sp, vit, repro in world.query(Position, Species, Vitality, Reproduction):
            if eid in world.entities:
                pos_lookup.setdefault((pos.x, pos.y), []).append(eid)

        spawned: list = []
        bred: set[int] = set()

        for eid, pos, sp, vit, repro in world.query(Position, Species, Vitality, Reproduction):
            if eid not in world.entities or eid in bred:
                continue
            params = SPECIES_PARAMS[sp.kind]

            # Check breeding conditions
            if vit.energy < params["breed_energy"]:
                continue
            if repro.cooldown > 0:
                continue

            # Check population cap
            if world.count_species(sp.kind) >= params["population_cap"]:
                continue

            # Find an adjacent mate
            mate_eid = None
            for dx, dy in self.DIRS:
                cell = (pos.x + dx, pos.y + dy)
                if cell not in pos_lookup:
                    continue
                for other_eid in pos_lookup[cell]:
                    if other_eid == eid or other_eid in bred:
                        continue
                    other_sp = world.get_component(other_eid, Species)
                    other_vit = world.get_component(other_eid, Vitality)
                    other_repro = world.get_component(other_eid, Reproduction)
                    if (other_sp and other_sp.kind == sp.kind and
                            other_vit and other_vit.energy >= params["breed_energy"] and
                            other_repro and other_repro.cooldown <= 0):
                        mate_eid = other_eid
                        break
                if mate_eid is not None:
                    break

            if mate_eid is None:
                continue

            # Find empty adjacent cell for offspring
            birth_pos = None
            for dx, dy in self.DIRS:
                nx, ny = pos.x + dx, pos.y + dy
                if world.is_walkable(nx, ny, sp.kind) and (nx, ny) not in pos_lookup:
                    birth_pos = (nx, ny)
                    break

            if birth_pos is None:
                continue

            # Parents contribute energy
            mate_vit = world.get_component(mate_eid, Vitality)
            mate_repro = world.get_component(mate_eid, Reproduction)
            vit.energy -= vit.max_energy * OFFSPRING_ENERGY_RATIO
            mate_vit.energy -= mate_vit.max_energy * OFFSPRING_ENERGY_RATIO

            # Set cooldowns
            repro.cooldown = params["breed_cooldown"]
            mate_repro.cooldown = params["breed_cooldown"]
            bred.add(eid)
            bred.add(mate_eid)

            # Spawn offspring
            spawned.append((sp.kind, birth_pos[0], birth_pos[1]))

        for kind, x, y in spawned:
            world.spawn_animal(kind, x, y, is_offspring=True)
