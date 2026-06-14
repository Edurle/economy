"""Research system: scholars generate research points, tech auto-unlocks."""

from config import Role, SCHOLAR_RESEARCH_RATE
from ecs.world import World
from ecs.components import Tribe, Structure
from resources import TECH_TREE


class ResearchSystem:
    def update(self, world: World) -> None:
        # Count scholars per camp
        scholar_counts: dict[int, int] = {}
        for eid, tribe in world.query(Tribe):
            if eid not in world.entities:
                continue
            if tribe.role == Role.SCHOLAR and tribe.home_camp >= 0:
                scholar_counts[tribe.home_camp] = scholar_counts.get(tribe.home_camp, 0) + 1

        for eid, struct in world.query(Structure):
            if eid not in world.entities:
                continue

            # Accumulate research points
            count = scholar_counts.get(eid, 0)
            if count > 0:
                struct.research_points += SCHOLAR_RESEARCH_RATE * count

            # Try to unlock techs (lowest tier first)
            available = [
                (key, tech) for key, tech in TECH_TREE.items()
                if key not in struct.researched_tech
                and all(req in struct.researched_tech for req in tech.requires)
            ]
            available.sort(key=lambda x: x[1].tier)

            for tech_key, tech in available:
                if struct.research_points >= tech.research_cost:
                    struct.research_points -= tech.research_cost
                    struct.researched_tech.add(tech_key)
                    world.log_event(f"科技解锁: {tech.name}")
