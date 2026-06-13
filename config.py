"""Global configuration: all tunable parameters for the ecosystem simulation."""

from enum import IntEnum

# ============================================================
# Window / Rendering
# ============================================================
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
TILE_SIZE = 16                 # native tile sprite size in pixels
VIEWPORT_WIDTH = 800           # camera viewport area on screen
VIEWPORT_HEIGHT = 770          # leave room for status bar
PANEL_WIDTH = WINDOW_WIDTH - VIEWPORT_WIDTH   # 400
PANEL_HEIGHT = VIEWPORT_HEIGHT                 # 770
STATUS_BAR_HEIGHT = WINDOW_HEIGHT - VIEWPORT_HEIGHT  # 30
FPS = 60

# Camera
CAMERA_PAN_SPEED = 400.0       # pixels per second for keyboard panning
CAMERA_MIN_ZOOM = 0.5          # zoom out limit
CAMERA_MAX_ZOOM = 4.0          # zoom in limit
CAMERA_EDGE_SCROLL = False     # edge scrolling (optional)

# ============================================================
# World
# ============================================================
GRID_W = 64
GRID_H = 64
SEASON_LENGTH = 50            # ticks per season

# ============================================================
# Enums
# ============================================================
class TerrainType(IntEnum):
    GRASSLAND = 0
    FOREST    = 1
    WATER     = 2
    DESERT    = 3
    MOUNTAIN  = 4
    SNOW      = 5

class SpeciesKind(IntEnum):
    RABBIT = 0
    SHEEP  = 1
    DEER   = 2
    FOX    = 3
    WOLF   = 4

class State(IntEnum):
    IDLE           = 0
    FORAGING       = 1
    FLEEING        = 2
    HUNTING        = 3
    MATING         = 4
    SEEKING_WATER  = 5

class Season(IntEnum):
    SPRING = 0
    SUMMER = 1
    AUTUMN = 2
    WINTER = 3

SEASON_NAMES = {Season.SPRING: "春", Season.SUMMER: "夏",
                Season.AUTUMN: "秋", Season.WINTER: "冬"}

# ============================================================
# Species Parameters
# ============================================================
SPECIES_PARAMS = {
    SpeciesKind.RABBIT: {
        "name":          "兔子",
        "init_energy":   30,
        "max_energy":    60,
        "init_hydration": 40,
        "max_hydration": 80,
        "max_age":       30,
        "vision":        3,
        "speed":         2,
        "breed_energy":  25,
        "breed_cooldown": 5,
        "food_gain":     10,     # energy gained per grass eaten
        "population_cap": 200,
        "color":         (200, 200, 200),
        "size":          1,
    },
    SpeciesKind.SHEEP: {
        "name":          "羊",
        "init_energy":   50,
        "max_energy":    100,
        "init_hydration": 60,
        "max_hydration": 100,
        "max_age":       50,
        "vision":        4,
        "speed":         1,
        "breed_energy":  55,
        "breed_cooldown": 10,
        "food_gain":     15,
        "population_cap": 150,
        "color":         (240, 240, 240),
        "size":          2,
    },
    SpeciesKind.DEER: {
        "name":          "鹿",
        "init_energy":   80,
        "max_energy":    150,
        "init_hydration": 70,
        "max_hydration": 120,
        "max_age":       70,
        "vision":        5,
        "speed":         1,
        "breed_energy":  70,
        "breed_cooldown": 15,
        "food_gain":     25,
        "population_cap": 80,
        "color":         (150, 100, 60),
        "size":          2,
    },
    SpeciesKind.FOX: {
        "name":          "狐狸",
        "init_energy":   70,
        "max_energy":    120,
        "init_hydration": 60,
        "max_hydration": 100,
        "max_age":       80,
        "vision":        7,
        "speed":         2,
        "breed_energy":  40,
        "breed_cooldown": 10,
        "food_gain":     0,
        "population_cap": 80,
        "color":         (230, 120, 40),
        "size":          2,
    },
    SpeciesKind.WOLF: {
        "name":          "狼",
        "init_energy":   90,
        "max_energy":    160,
        "init_hydration": 70,
        "max_hydration": 120,
        "max_age":       100,
        "vision":        8,
        "speed":         1,
        "breed_energy":  55,
        "breed_cooldown": 15,
        "food_gain":     0,
        "population_cap": 50,
        "color":         (180, 50, 50),
        "size":          2,
    },
}

# Herbivores (eat grass)
HERBIVORES = {SpeciesKind.RABBIT, SpeciesKind.SHEEP, SpeciesKind.DEER}
# Carnivores (eat other animals)
CARNIVORES = {SpeciesKind.FOX, SpeciesKind.WOLF}

# ============================================================
# Predator-Prey Relationships
# ============================================================
PREY_MAP = {
    SpeciesKind.FOX:  {SpeciesKind.RABBIT: 0.70, SpeciesKind.SHEEP: 0.15},
    SpeciesKind.WOLF: {SpeciesKind.SHEEP: 0.65, SpeciesKind.DEER: 0.55, SpeciesKind.FOX: 0.30},
}

# Species that each prey flees from
PREDATOR_MAP = {
    SpeciesKind.RABBIT: {SpeciesKind.FOX, SpeciesKind.WOLF},
    SpeciesKind.SHEEP:  {SpeciesKind.WOLF},
    SpeciesKind.DEER:   {SpeciesKind.WOLF},
    SpeciesKind.FOX:    {SpeciesKind.WOLF},
}

PREY_ENERGY_TRANSFER = 1.0   # predator gains 100% of prey's remaining energy

# Deer require multiple wolves to hunt successfully
DEER_HUNT_WOLF_COUNT = 2

# ============================================================
# Grass / Plant System
# ============================================================
GRASS_GROWTH_RATE = 2.0
GRASS_MAX = 100.0
BUSH_GRASS_MULTIPLIER = 1.5   # forest grows grass faster

# ============================================================
# Environment Effects
# ============================================================
SEASON_GRASS_MULT = {Season.SPRING: 2.0, Season.SUMMER: 1.0, Season.AUTUMN: 0.5, Season.WINTER: 0.15}
SEASON_ENERGY_MULT = {Season.SPRING: 1.0, Season.SUMMER: 1.0, Season.AUTUMN: 1.2, Season.WINTER: 1.3}
SEASON_RAIN_CHANCE = {Season.SPRING: 0.08, Season.SUMMER: 0.12, Season.AUTUMN: 0.04, Season.WINTER: 0.02}
SEASON_BREED_MULT = {Season.SPRING: 1.2, Season.SUMMER: 1.0, Season.AUTUMN: 0.8, Season.WINTER: 0.3}

# Season-specific winter grass decay
WINTER_GRASS_DECAY = 0.3       # grass_level -= 0.3 per tick in winter (slow)

# ============================================================
# Weather
# ============================================================
RAIN_RADIUS_MIN = 5
RAIN_RADIUS_MAX = 12
RAIN_DURATION_MIN = 5
RAIN_DURATION_MAX = 15
RAIN_GRASS_BOOST = 5.0         # grass_level += 5 per tick under rain
DROUGHT_THRESHOLD = 50         # ticks without rain to trigger drought
DROUGHT_GRASS_DECAY = 3.0     # grass_level -= 3 per tick in drought
WATER_DRINK_DISTANCE = 1       # drink from water if adjacent

# ============================================================
# Fire
# ============================================================
FIRE_DROUGHT_TICKS = 20        # need 20+ ticks without rain before fire can start
FIRE_GRASS_THRESHOLD = 80      # grass must be >= 80 to catch fire
FIRE_IGNITE_CHANCE = 0.001     # per cell per tick when conditions met
FIRE_SPREAD_CHANCE = 0.40      # spread to adjacent grassland per tick
FIRE_DURATION_MIN = 3
FIRE_DURATION_MAX = 5
FIRE_ANIMAL_DEATH_CHANCE = 0.50
FIRE_ASH_DURATION = 30         # ash buff lasts 30 ticks
FIRE_ASH_GROWTH_MULT = 3.0     # grass grows 3x faster on ash

# ============================================================
# Plague
# ============================================================
PLAGUE_TRIGGER_RATIO = 0.90    # trigger at 90% of population cap
PLAGUE_CURE_RATIO = 0.40       # cured when population drops to 40% of cap
PLAGUE_SPREAD_CHANCE = 0.15    # chance to infect adjacent same-species per tick
PLAGUE_ENERGY_DAMAGE = 5.0     # infected lose 5 energy per tick

# ============================================================
# Vitality Cost Per Tick
# ============================================================
BASE_ENERGY_COST = 0.8        # energy consumed per tick
BASE_HYDRATION_COST = 0.5     # hydration consumed per tick
DESERT_HYDRATION_MULT = 2.0    # desert: 2x hydration loss
SNOW_ENERGY_MULT = 1.2         # snow: 1.2x energy loss
SNOW_HYDRATION_MULT = 1.2      # snow: 1.2x hydration loss

# ============================================================
# Reproduction
# ============================================================
OFFSPRING_ENERGY_RATIO = 0.10  # each parent gives 10% energy to offspring

# ============================================================
# Terrain Colors
# ============================================================
TERRAIN_COLORS = {
    TerrainType.GRASSLAND: (124, 200, 100),
    TerrainType.FOREST:    (40, 120, 50),
    TerrainType.WATER:     (60, 130, 200),
    TerrainType.DESERT:    (230, 210, 140),
    TerrainType.MOUNTAIN:  (130, 120, 115),
    TerrainType.SNOW:      (230, 240, 245),
}

FIRE_COLOR = (255, 80, 0)
ASH_COLOR = (80, 60, 50)
