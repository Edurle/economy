"""ECS component dataclasses — pure data, no logic."""

from dataclasses import dataclass, field
from config import State, SpeciesKind


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
