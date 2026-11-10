"""Boss attack targeting, telegraphs, and turn-based attack execution."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING
import pygame

from .enemy import Enemy
from .map_generator import DungeonMap
from .player import Player
from .settings import TILE_SIZE


@dataclass
class BossProjectile:
    """Enemy bolt that follows a straight, delta-time path toward the hero."""

    x: float
    y: float
    vx: float
    vy: float
    damage: int
    color: tuple[int, int, int] = (151, 226, 104)
    remaining: float = 2.5
    alive: bool = True

    def update(self, dt: float, player: Player, dungeon: DungeonMap) -> bool:
        if not self.alive:
            return False
        dt = max(0.0, dt)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.remaining -= dt
        tile_x, tile_y = int(self.x // TILE_SIZE), int(self.y // TILE_SIZE)
        if self.remaining <= 0 or not dungeon.is_walkable(tile_x, tile_y):
            self.alive = False
            return False
        player_x = player.x * TILE_SIZE + TILE_SIZE / 2
        player_y = player.y * TILE_SIZE + TILE_SIZE / 2
        if math.hypot(self.x - player_x, self.y - player_y) <= 16:
            player.take_damage(self.damage)
            self.alive = False
            return False
        return True

    def draw(self, surface: pygame.Surface, camera: tuple[int, int]) -> None:
        point = round(self.x - camera[0]), round(self.y - camera[1])
        pygame.draw.circle(surface, (*self.color, 80), point, 11)
        pygame.draw.circle(surface, (*self.color, 230), point, 6)
        pygame.draw.circle(surface, (255, 247, 215, 255), point, 2)


def create_boss_projectiles(
    origin: tuple[float, float],
    target: tuple[float, float],
    damage: int,
    count: int,
    spread_degrees: float,
    color: tuple[int, int, int],
) -> list[BossProjectile]:
    """Create a volley with evenly spaced directions around the target vector."""
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    base_angle = math.atan2(dy, dx)
    if count == 1:
        offsets = [0.0]
    else:
        spread = math.radians(spread_degrees)
        offsets = [spread * (index / (count - 1) * 2 - 1) for index in range(count)]
    return [
        BossProjectile(
            origin[0],
            origin[1],
            math.cos(base_angle + offset) * 250,
            math.sin(base_angle + offset) * 250,
            damage,
            color,
        )
        for offset in offsets
    ]

if TYPE_CHECKING:
    from .boss import Boss


def line_tiles(start: tuple[int, int], end: tuple[int, int], limit: int = 12) -> list[tuple[int, int]]:
    """Build cardinal cells along a line for charge and breath previews."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    if abs(dx) >= abs(dy):
        step = (1 if dx > 0 else -1, 0)
    else:
        step = (0, 1 if dy > 0 else -1)
    return [
        (start[0] + step[0] * distance, start[1] + step[1] * distance)
        for distance in range(1, limit + 1)
    ]


def attack_preview(boss: Boss, player: Player, dungeon: DungeonMap, attack: str) -> set[tuple[int, int]]:
    """Return all currently threatened tiles for the pulsing telegraph."""
    # Dùng cùng mục tiêu đã khóa với lúc thi triển để vùng cảnh báo luôn nhất quán.
    px, py = boss.telegraph_target
    if attack == "fire_breath":
        return {
            (x, y)
            for y in range(max(0, boss.y - 5), min(dungeon.height, boss.y + 6))
            for x in range(max(0, boss.x - 5), min(dungeon.width, boss.x + 6))
            if _inside_cone((boss.x, boss.y), (px, py), (x, y), 5, math.pi / 4)
        }
    if attack in {"bone_volley", "feather_barrage"}:
        return {
            (x, y)
            for y in range(max(0, boss.y - 7), min(dungeon.height, boss.y + 8))
            for x in range(max(0, boss.x - 7), min(dungeon.width, boss.x + 8))
            if _inside_cone(
                (boss.x, boss.y), (px, py), (x, y), 7, math.radians(32),
            )
        }
    if attack in {"jump_slam", "dive", "egg_bomb"}:
        radius = 4 if attack == "egg_bomb" else (2 if attack == "dive" else 1)
        return {
            (x, y)
            for y in range(max(0, py - radius), min(dungeon.height, py + radius + 1))
            for x in range(max(0, px - radius), min(dungeon.width, px + radius + 1))
        }
    if attack == "acid_spit":
        radius = 7
        return {
            (x, y)
            for x in range(max(0, px - radius), min(dungeon.width, px + radius + 1))
            for y in range(max(0, py - radius), min(dungeon.height, py + radius + 1))
            if math.hypot(x - boss.x, y - boss.y) <= radius
        }
    if attack == "charge":
        return set(line_tiles((boss.x, boss.y), (px, py), 3))
    return set()


def has_line_of_sight(dungeon: DungeonMap, start: tuple[int, int], end: tuple[int, int]) -> bool:
    """Check intermediate tiles for a wall that blocks an egg-bomb blast."""
    distance = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
    if distance <= 1:
        return True
    for step in range(1, distance):
        x = round(start[0] + (end[0] - start[0]) * step / distance)
        y = round(start[1] + (end[1] - start[1]) * step / distance)
        if not dungeon.is_walkable(x, y):
            return False
    return True


def _inside_cone(
    origin: tuple[int, int],
    target: tuple[int, int],
    point: tuple[int, int],
    distance_limit: int,
    half_angle: float,
) -> bool:
    direction_x, direction_y = target[0] - origin[0], target[1] - origin[1]
    point_x, point_y = point[0] - origin[0], point[1] - origin[1]
    direction_length = math.hypot(direction_x, direction_y)
    point_length = math.hypot(point_x, point_y)
    if point_length > distance_limit:
        return False
    if direction_length == 0 or point_length == 0:
        return point_length == 0
    cosine = (direction_x * point_x + direction_y * point_y) / (direction_length * point_length)
    return cosine >= math.cos(half_angle)


def execute_attack(
    boss: Boss,
    attack: str,
    player: Player,
    dungeon: DungeonMap,
    enemies: list[Enemy],
) -> tuple[int, list[Enemy], list[tuple[float, float, int]]]:
    """Resolve one boss pattern and return damage, summons, and ranged shots."""
    damage = 0
    summons: list[Enemy] = []
    shots: list[tuple[float, float, int]] = []

    if attack in {"jump_slam", "dive"}:
        radius = 2 if attack == "dive" else 1
        target_x, target_y = boss.telegraph_target
        if abs(player.x - target_x) <= radius and abs(player.y - target_y) <= radius:
            damage = boss.atk
    elif attack == "acid_spit":
        shots.append((boss.x * TILE_SIZE + 16, boss.y * TILE_SIZE + 16, boss.atk))
    elif attack == "summon_slimes":
        summons.extend(_spawn_minions(boss, dungeon, player, 2, "Slime", 18, max(4, boss.atk // 2)))
    elif attack == "summon_skeletons":
        summons.extend(_spawn_minions(boss, dungeon, player, 3, "Skeleton", 26, max(6, boss.atk // 2)))
    elif attack == "bone_volley":
        shots.extend(
            (boss.x * TILE_SIZE + 16, boss.y * TILE_SIZE + 16, max(4, boss.atk // 2))
            for _ in range(5)
        )
    elif attack == "charge":
        cells = line_tiles((boss.x, boss.y), boss.telegraph_target, 3)
        for x, y in cells:
            if not dungeon.is_walkable(x, y):
                break
            boss.x, boss.y = x, y
            if (x, y) == (player.x, player.y):
                damage = boss.atk
                break
    elif attack == "fire_breath":
        if (
            _inside_cone(
                (boss.x, boss.y), boss.telegraph_target, (player.x, player.y), 5, math.pi / 4,
            )
            and has_line_of_sight(dungeon, (boss.x, boss.y), (player.x, player.y))
        ):
            damage = boss.atk
    elif attack == "feather_barrage":
        shots.extend(
            (boss.x * TILE_SIZE + 16, boss.y * TILE_SIZE + 16, max(5, boss.atk // 3))
            for _ in range(5)
        )
    elif attack == "egg_bomb":
        target_x, target_y = boss.telegraph_target
        # Tường chắn đường nhìn sẽ bảo vệ người chơi khỏi vụ nổ trứng.
        if (
            abs(player.x - target_x) <= 4
            and abs(player.y - target_y) <= 4
            and has_line_of_sight(dungeon, (boss.x, boss.y), (player.x, player.y))
        ):
            damage = boss.atk * 2

    return damage, summons, shots


def _spawn_minions(
    boss: Boss,
    dungeon: DungeonMap,
    player: Player,
    count: int,
    name: str,
    hp: int,
    attack: int,
) -> list[Enemy]:
    candidates = [
        (x, y)
        for y in range(max(1, boss.y - 3), min(dungeon.height - 1, boss.y + 4))
        for x in range(max(1, boss.x - 3), min(dungeon.width - 1, boss.x + 4))
        if dungeon.is_walkable(x, y)
        and (x, y) not in {(boss.x, boss.y), (player.x, player.y)}
    ]
    return [
        Enemy(x, y, name=name, hp=hp, atk=attack, enemy_type="slime" if "Slime" in name else "skeleton")
        for x, y in candidates[:count]
    ]
