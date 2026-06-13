"""ECS component dataclasses — pure data, no logic."""

from dataclasses import dataclass, field
from config import State, SpeciesKind, Role, StructureKind


@dataclass
class Position:
    x: int
    y: int


@dataclass
class Vitality:
    energy: float
    hydration: float
    age: int = 0
    max_energy: float = 0.0
    max_hydration: float = 0.0
    max_age: int = 0


@dataclass
class Species:
    kind: SpeciesKind


@dataclass
class Behavior:
    state: State = State.IDLE
    target: int = -1   # target entity id, -1 = none


@dataclass
class Reproduction:
    cooldown: int = 0


@dataclass
class Health:
    diseased: bool = False
    sick_timer: int = 0


@dataclass
class Tag:
    """Optional marker tags for special entities."""
    is_offspring: bool = False


@dataclass
class Tribe:
    tribe_id: int = 0
    role: int = Role.HUNTER
    home_camp: int = -1


@dataclass
class Inventory:
    food: int = 0
    wood: int = 0


@dataclass
class Structure:
    kind: int = StructureKind.CAMP
    tribe_id: int = 0
    food_stockpile: int = 0
    wood_stockpile: int = 0
    capacity: int = 8
    territory_radius: int = 8
