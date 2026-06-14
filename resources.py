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
# Recipe System
# ============================================================
@dataclass(frozen=True)
class RecipeDef:
    key: str
    name: str
    inputs: Dict[str, int]
    outputs: Dict[str, int]
    required_tech: str = ""
    craft_time: int = 5
    workstation: str = ""


RECIPE_REGISTRY: Dict[str, RecipeDef] = {
    "craft_plank": RecipeDef(
        "craft_plank", "制作木板",
        inputs={"wood": 2}, outputs={"plank": 1},
        required_tech="stone_tools", craft_time=5,
    ),
    "craft_brick": RecipeDef(
        "craft_brick", "烧制砖块",
        inputs={"stone": 3, "coal": 1}, outputs={"brick": 1},
        required_tech="stone_tools", craft_time=8,
    ),
    "smelt_copper": RecipeDef(
        "smelt_copper", "冶炼铜锭",
        inputs={"copper_ore": 2, "coal": 1}, outputs={"copper_ingot": 1},
        required_tech="copper_working", craft_time=10,
    ),
    "smelt_gold": RecipeDef(
        "smelt_gold", "冶炼金锭",
        inputs={"gold_ore": 2, "coal": 1}, outputs={"gold_ingot": 1},
        required_tech="copper_working", craft_time=10,
    ),
    "smelt_iron": RecipeDef(
        "smelt_iron", "冶炼铁锭",
        inputs={"iron_ore": 2, "coal": 2}, outputs={"iron_ingot": 1},
        required_tech="iron_working", craft_time=12,
    ),
    "smelt_steel": RecipeDef(
        "smelt_steel", "炼钢",
        inputs={"iron_ingot": 1, "coal": 3}, outputs={"steel": 1},
        required_tech="steel_making", craft_time=20,
    ),
}


# ============================================================
# Tech Tree
# ============================================================
@dataclass(frozen=True)
class TechNode:
    key: str
    name: str
    description: str
    research_cost: int             # research points needed
    requires: Tuple[str, ...]      # prerequisite tech keys
    unlocks_recipes: Tuple[str, ...]
    tier: int


TECH_TREE: Dict[str, TechNode] = {
    "stone_tools": TechNode(
        "stone_tools", "石器时代",
        "掌握基础工具制作，可以加工木材和石材",
        research_cost=20,
        requires=(),
        unlocks_recipes=("craft_plank", "craft_brick"),
        tier=0,
    ),
    "copper_working": TechNode(
        "copper_working", "铜器时代",
        "掌握铜和贵金属的冶炼技术",
        research_cost=50,
        requires=("stone_tools",),
        unlocks_recipes=("smelt_copper", "smelt_gold"),
        tier=1,
    ),
    "iron_working": TechNode(
        "iron_working", "铁器时代",
        "掌握铁的冶炼技术，更坚固的材料",
        research_cost=100,
        requires=("copper_working",),
        unlocks_recipes=("smelt_iron",),
        tier=2,
    ),
    "steel_making": TechNode(
        "steel_making", "钢铁时代",
        "掌握炼钢技术，最强韧的金属材料",
        research_cost=200,
        requires=("iron_working",),
        unlocks_recipes=("smelt_steel",),
        tier=3,
    ),
}
