"""Room-and-corridor dungeon generation."""

from dataclasses import dataclass, field
import random
from typing import TypeAlias

from .settings import MAP_HEIGHT, MAP_WIDTH, TileType

Grid: TypeAlias = list[list[TileType]]


@dataclass(frozen=True)
class Room:
    """A rectangular room described by its top-left coordinate and size."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        """Return the integer center tile of this room."""
        return self.x + self.width // 2, self.y + self.height // 2

    def intersects(self, other: "Room", padding: int = 1) -> bool:
        """Return whether two rooms overlap, including a small spacing margin."""
        return not (
            self.x + self.width + padding <= other.x
            or other.x + other.width + padding <= self.x
            or self.y + self.height + padding <= other.y
            or other.y + other.height + padding <= self.y
        )


@dataclass
class DungeonMap:
    """Generated dungeon grid and key positions for one floor."""

    width: int
    height: int
    tiles: Grid
    rooms: list[Room] = field(default_factory=list)
    start: tuple[int, int] = (1, 1)
    stairs: tuple[int, int] = (1, 1)

    def is_walkable(self, x: int, y: int) -> bool:
        """Return whether a coordinate is in bounds and not a wall."""
        return (
            0 <= x < self.width
            and 0 <= y < self.height
            and self.tiles[y][x] != TileType.WALL
        )

    def to_dict(self) -> dict[str, object]:
        """Convert the map to JSON-compatible primitive values."""
        return {
            "width": self.width,
            "height": self.height,
            "tiles": [[int(tile) for tile in row] for row in self.tiles],
            "rooms": [
                {"x": room.x, "y": room.y, "width": room.width, "height": room.height}
                for room in self.rooms
            ],
            "start": list(self.start),
            "stairs": list(self.stairs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "DungeonMap":
        """Rebuild a map from saved primitive values."""
        width = int(data["width"])
        height = int(data["height"])
        tile_rows = data["tiles"]
        if not isinstance(tile_rows, list) or len(tile_rows) != height:
            raise ValueError("Saved dungeon has an invalid tile grid.")
        tiles = [
            [TileType(int(value)) for value in row]
            for row in tile_rows
            if isinstance(row, list)
        ]
        if len(tiles) != height or any(len(row) != width for row in tiles):
            raise ValueError("Saved dungeon has an invalid tile grid.")
        rooms_data = data.get("rooms", [])
        rooms = [
            Room(
                int(room["x"]), int(room["y"]),
                int(room["width"]), int(room["height"]),
            )
            for room in rooms_data
        ]
        start_data = data["start"]
        stairs_data = data["stairs"]
        start = (int(start_data[0]), int(start_data[1]))
        stairs = (int(stairs_data[0]), int(stairs_data[1]))
        return cls(width, height, tiles, rooms, start, stairs)


def _carve_room(grid: Grid, room: Room) -> None:
    """Carve the interior of a room into the grid."""
    for y in range(room.y, room.y + room.height):
        for x in range(room.x, room.x + room.width):
            grid[y][x] = TileType.FLOOR


def _carve_horizontal(grid: Grid, x1: int, x2: int, y: int) -> None:
    """Carve a horizontal corridor between two x coordinates."""
    for x in range(min(x1, x2), max(x1, x2) + 1):
        grid[y][x] = TileType.FLOOR


def _carve_vertical(grid: Grid, y1: int, y2: int, x: int) -> None:
    """Carve a vertical corridor between two y coordinates."""
    for y in range(min(y1, y2), max(y1, y2) + 1):
        grid[y][x] = TileType.FLOOR


def generate_dungeon(
    width: int = MAP_WIDTH,
    height: int = MAP_HEIGHT,
    seed: int | None = None,
) -> DungeonMap:
    """Generate a connected, room-based dungeon with stairs to the next floor.

    A seed may be supplied for repeatable generation, useful for tests and
    debugging. Corridors connect every accepted room in sequence.
    """
    if width < 30 or height < 20:
        raise ValueError("Dungeon dimensions must be at least 30 by 20 tiles.")

    rng = random.Random(seed)
    grid = [[TileType.WALL for _ in range(width)] for _ in range(height)]
    rooms: list[Room] = []
    target_rooms = 12

    for _ in range(160):
        if len(rooms) >= target_rooms:
            break
        room_width = rng.randint(6, 12)
        room_height = rng.randint(5, 9)
        room = Room(
            rng.randint(1, width - room_width - 2),
            rng.randint(1, height - room_height - 2),
            room_width,
            room_height,
        )
        if any(room.intersects(existing) for existing in rooms):
            continue
        _carve_room(grid, room)
        if rooms:
            previous_x, previous_y = rooms[-1].center
            current_x, current_y = room.center
            # Nối từng phòng mới với phòng trước để bảo đảm toàn bộ tầng liên thông.
            if rng.choice((True, False)):
                _carve_horizontal(grid, previous_x, current_x, previous_y)
                _carve_vertical(grid, previous_y, current_y, current_x)
            else:
                _carve_vertical(grid, previous_y, current_y, previous_x)
                _carve_horizontal(grid, previous_x, current_x, current_y)
        rooms.append(room)

    if len(rooms) < 2:
        raise RuntimeError("Could not generate enough rooms for a dungeon.")

    start = rooms[0].center
    stairs = rooms[-1].center
    grid[stairs[1]][stairs[0]] = TileType.STAIRS_DOWN
    return DungeonMap(width, height, grid, rooms, start, stairs)
