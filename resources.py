"""Extensible resource registry for the ecosystem simulation.

All resources are string-keyed for infinite extensibility.
Add a new resource by adding an entry to RESOURCE_REGISTRY.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ============================================================
# Resource Definition
# ============================================================
@dataclass(frozen=True)
class ResourceDef:
    key: str
    name: str            # Chinese display name
    color: Tuple[int, int, int]
    category: str        # "raw" | "refined" | "tool"
    tier: int            # 0=stone age, 1=copper, 2=bronze, 3=iron
    depositable: bool = False


# ============================================================
# Resource Registry — add resources here to extend the game
# ============================================================
RESOURCE_REGISTRY: Dict[str, ResourceDef] = {
    # --- Raw materials (tier 0) ---
    "wood":         ResourceDef("wood",         "木材",   (140, 90, 50),   "raw", 0, depositable=False),
    "stone":        ResourceDef("stone",        "石头",   (160, 160, 160), "raw", 0, depositable=True),
    "coal":         ResourceDef("coal",         "煤炭",   (60, 60, 60),    "raw", 0, depositable=True),
    "iron_ore":     ResourceDef("iron_ore",     "铁矿",   (180, 130, 100), "raw", 0, depositable=True),
    "copper_ore":   ResourceDef("copper_ore",   "铜矿",   (200, 140, 60),  "raw", 0, depositable=True),
    "gold_ore":     ResourceDef("gold_ore",     "金矿",   (230, 200, 50),  "raw", 0, depositable=True),

    # --- Refined materials (tier 1+) ---
    "plank":        ResourceDef("plank",        "木板",   (170, 120, 70),  "refined", 1),
    "brick":        ResourceDef("brick",        "砖块",   (180, 90, 60),   "refined", 1),
    "copper_ingot": ResourceDef("copper_ingot", "铜锭",   (220, 140, 70),  "refined", 1),
    "iron_ingot":   ResourceDef("iron_ingot",   "铁锭",   (200, 200, 210), "refined", 2),
    "gold_ingot":   ResourceDef("gold_ingot",   "金锭",   (240, 210, 60),  "refined", 2),
    "steel":        ResourceDef("steel",        "钢材",   (180, 190, 200), "refined", 3),
}


# ============================================================
# Depositable resources — drives world generation
# ============================================================
DEPOSITABLE: List[str] = [
    "stone",
    "coal",
    "iron_ore",
    "copper_ore",
    "gold_ore",
]

DEPOSIT_CONFIG: Dict[str, dict] = {
    "stone":      {"prob": 0.25, "amount": (30, 80)},
    "coal":       {"prob": 0.15, "amount": (20, 60)},
    "iron_ore":   {"prob": 0.20, "amount": (20, 50)},
    "copper_ore": {"prob": 0.12, "amount": (15, 40)},
    "gold_ore":   {"prob": 0.08, "amount": (10, 30)},
}

# Yield per mining action by resource key
MINE_YIELD: Dict[str, int] = {
    "stone":      5,
    "coal":       5,
    "iron_ore":   3,
    "copper_ore": 3,
    "gold_ore":   2,
}

# Wood yield per forest chop
GATHER_WOOD_AMOUNT = 5


# ============================================================
# Helper functions
# ============================================================
def res_name(key: str) -> str:
    """Get Chinese display name for a resource key."""
    r = RESOURCE_REGISTRY.get(key)
    return r.name if r else key


def res_color(key: str) -> Tuple[int, int, int]:
    """Get render color for a resource key."""
    r = RESOURCE_REGISTRY.get(key)
    return r.color if r else (128, 128, 128)


def all_raw() -> List[str]:
    """All raw material resource keys."""
    return [k for k, v in RESOURCE_REGISTRY.items() if v.category == "raw"]


def all_refined() -> List[str]:
    """All refined material resource keys."""
    return [k for k, v in RESOURCE_REGISTRY.items() if v.category == "refined"]


def depositable_index(key: str) -> int:
    """Index into DEPOSITABLE list, or -1 if not depositable."""
    try:
        return DEPOSITABLE.index(key)
    except ValueError:
        return -1


def deposit_key(idx: int) -> str | None:
    """Convert deposit array index back to resource key."""
    if 0 <= idx < len(DEPOSITABLE):
        return DEPOSITABLE[idx]
    return None


# ============================================================
# Recipe System (skeleton — filled in tech tree phase)
# ============================================================
@dataclass(frozen=True)
class RecipeDef:
    key: str
    name: str
    inputs: Dict[str, int]        # {"iron_ore": 2, "coal": 1}
    outputs: Dict[str, int]       # {"iron_ingot": 1}
    required_tech: str = ""       # tech node key, "" = always available
    craft_time: int = 5           # ticks to complete
    workstation: str = ""         # building type needed, "" = craft anywhere


RECIPE_REGISTRY: Dict[str, RecipeDef] = {}
# Example (future):
# RECIPE_REGISTRY["smelt_iron"] = RecipeDef(
#     "smelt_iron", "冶炼铁锭",
#     inputs={"iron_ore": 2, "coal": 1},
#     outputs={"iron_ingot": 1},
#     required_tech="iron_working",
#     craft_time=10,
#     workstation="smelter",
# )


# ============================================================
# Tech Tree (skeleton — filled in tech tree phase)
# ============================================================
@dataclass(frozen=True)
class TechNode:
    key: str
    name: str
    description: str
    cost: Dict[str, int]          # research cost in resources
    requires: Tuple[str, ...]     # prerequisite tech keys
    unlocks_recipes: Tuple[str, ...]  # recipe keys unlocked
    tier: int


TECH_TREE: Dict[str, TechNode] = {}
# Example (future):
# TECH_TREE["bronze_working"] = TechNode(
#     "bronze_working", "青铜冶炼",
#     "解锁铜锭和锡锭冶炼为青铜",
#     cost={"copper_ingot": 10, "research_points": 20},
#     requires=("copper_working",),
#     unlocks_recipes=("smelt_bronze",),
#     tier=1,
# )
