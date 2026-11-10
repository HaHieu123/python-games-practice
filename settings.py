"""Shared configuration and primitive game constants."""

from enum import Enum, IntEnum, auto

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TILE_SIZE = 32

# Dungeon dimensions in tiles. The viewport follows the player through this map.
MAP_WIDTH = 80
MAP_HEIGHT = 50
VIEW_COLUMNS = SCREEN_WIDTH // TILE_SIZE
VIEW_ROWS = SCREEN_HEIGHT // TILE_SIZE
FLOOR_COUNT = 6
ENEMY_SIGHT_RANGE = 8
SAVE_VERSION = 1
GAME_TITLE = "The Fivefold Depths"

COLOR_BACKGROUND = (16, 19, 26)
COLOR_WALL = (49, 56, 70)
COLOR_FLOOR = (91, 83, 73)
COLOR_FLOOR_ALT = (98, 89, 77)
COLOR_STAIRS = (225, 190, 94)
COLOR_PLAYER = (88, 177, 245)
COLOR_ENEMY = (210, 83, 83)
COLOR_TEXT = (235, 238, 243)
COLOR_MUTED = (167, 176, 190)
COLOR_ACCENT = (112, 190, 149)
COLOR_PANEL = (27, 32, 42)
COLOR_HP = (210, 69, 76)
COLOR_HP_BG = (74, 47, 53)


class TileType(IntEnum):
    """Tile values stored in the dungeon grid and save file."""

    WALL = 0
    FLOOR = 1
    STAIRS_DOWN = 2


class GameState(Enum):
    """Top-level screens/states used by the game state machine."""

    MENU = auto()
    PLAYING = auto()
    INVENTORY = auto()
    PAUSED = auto()
    SETTINGS = auto()
    SHOP = auto()
    BOSS_INTRO = auto()
    BOSS_DEATH = auto()
    PLAYER_DEATH = auto()
    GAME_OVER = auto()
