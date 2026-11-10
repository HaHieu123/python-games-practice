"""Enemy definitions and simple turn-based chase behavior."""

from dataclasses import dataclass
import math
from math import hypot

import pygame

from .animation import Animation
from .map_generator import DungeonMap
from .player import Player
from .settings import ENEMY_SIGHT_RANGE


@dataclass
class Enemy:
    """A basic enemy that pursues and attacks the player."""

    x: int
    y: int
    name: str = "Cave rat"
    hp: int = 24
    atk: int = 7
    gold_reward: int = 5
    enemy_type: str = "slime"
    defense: int = 0
    animation: Animation | None = None
    animation_action: str = "idle"
    animation_action_time: float = 0.0
    animation_clock: float = 0.0

    def __post_init__(self) -> None:
        if self.animation is None:
            self.animation = Animation()

    @property
    def alive(self) -> bool:
        """Return whether this enemy still has hit points."""
        return self.hp > 0

    def take_damage(self, amount: int) -> bool:
        """Apply damage and return whether the enemy was defeated."""
        self.hp = max(0, self.hp - max(0, amount - self.defense))
        if self.animation is not None:
            self.animation.set_state("death" if not self.alive else "hurt", force=True)
            self.animation_action = "death" if not self.alive else "hurt"
            self.animation_action_time = 0.0
        return not self.alive

    def update_animation(self, dt: float, moving: bool = False, attacking: bool = False) -> None:
        """Advance procedural animation and request the state implied by AI."""
        if self.animation is None:
            return
        self.animation_clock += max(0.0, dt)
        if self.animation_action_time > 0:
            self.animation_action_time = max(0.0, self.animation_action_time - dt)
        if not self.alive:
            requested = "death"
        elif self.animation_action in {"hurt", "attack"} and self.animation_action_time > 0:
            requested = self.animation_action
        elif moving:
            requested = "walk"
        else:
            requested = "idle"
        if requested != self.animation.state:
            self.animation.set_state(requested, force=requested in {"hurt", "attack", "death"})
        self.animation.update(dt)

    def draw(self, surface: pygame.Surface, center: tuple[int, int], time: float = 0.0) -> None:
        """Draw a small procedural slime, bat, or skeleton animation."""
        frame = self.animation.frame if self.animation is not None else 0
        facing = self.animation.facing if self.animation is not None else "down"
        sprite = pygame.Surface((38, 42), pygame.SRCALPHA)
        if self.enemy_type == "bat":
            flap = -5 if frame % 2 == 0 else 5
            pygame.draw.polygon(sprite, (105, 78, 145), [(18, 15), (3, 8 + flap), (8, 24), (18, 20)])
            pygame.draw.polygon(sprite, (105, 78, 145), [(20, 15), (35, 8 + flap), (30, 24), (20, 20)])
            pygame.draw.circle(sprite, (115, 91, 157), (19, 20), 8)
            pygame.draw.circle(sprite, (245, 71, 76), (16, 19), 2)
            pygame.draw.circle(sprite, (245, 71, 76), (22, 19), 2)
        elif self.enemy_type == "skeleton":
            bob = (0, -2, 0, 2)[frame % 4]
            pygame.draw.line(sprite, (211, 210, 192), (19, 15 + bob), (19, 31), 4)
            pygame.draw.circle(sprite, (222, 220, 199), (19, 11 + bob), 9)
            pygame.draw.circle(sprite, (45, 42, 43), (16, 11 + bob), 2)
            pygame.draw.circle(sprite, (45, 42, 43), (22, 11 + bob), 2)
            pygame.draw.line(sprite, (206, 204, 184), (12, 21), (26, 21), 3)
            leg_swing = 4 if frame % 2 else -4
            pygame.draw.line(sprite, (202, 200, 181), (19, 30), (14 + leg_swing, 39), 3)
            pygame.draw.line(sprite, (202, 200, 181), (19, 30), (24 - leg_swing, 39), 3)
            if self.animation is not None and self.animation.state == "attack":
                pygame.draw.line(sprite, (224, 218, 190), (27, 21), (35, 10), 3)
        else:
            # Slime stretches while airborne and flattens at the end of its hop.
            squash = 1.0 + 0.14 * math.sin((time or self.animation_clock) * 4.5)
            body_rect = pygame.Rect(5, 15 + round((1 - squash) * 7), 28, round(21 * squash))
            pygame.draw.ellipse(sprite, (48, 142, 106), body_rect)
            pygame.draw.ellipse(sprite, (101, 220, 166), body_rect.inflate(-8, -8))
            pygame.draw.circle(sprite, (27, 49, 43), (15, 25), 2)
            pygame.draw.circle(sprite, (27, 49, 43), (24, 25), 2)
            pygame.draw.arc(sprite, (33, 75, 58), (14, 25, 12, 8), 3.2, 6.1, 1)

        if self.animation is not None and self.animation.state == "hurt":
            tint = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
            tint.fill((255, 60, 60, 180))
            sprite.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        if not self.alive and self.animation is not None:
            sprite.set_alpha(round(255 * (4 - self.animation.frame) / 4))
        surface.blit(sprite, sprite.get_rect(center=center))

    def take_turn(self, dungeon: DungeonMap, player: Player) -> bool:
        """Move toward the player or attack if adjacent; return whether attacked."""
        if not self.alive or max(abs(self.x - player.x), abs(self.y - player.y)) > ENEMY_SIGHT_RANGE:
            return False

        dx = player.x - self.x
        dy = player.y - self.y
        if self.animation is not None:
            if abs(dx) > abs(dy):
                self.animation.set_facing("right" if dx > 0 else "left")
            elif dy:
                self.animation.set_facing("down" if dy > 0 else "up")
        if max(abs(dx), abs(dy)) <= 1:
            player.take_damage(self.atk)
            self.animation_action = "attack"
            self.animation_action_time = 0.35
            return True

        # Choose the closest legal cardinal step; avoid allowing diagonal wall clipping.
        candidates = []
        if dx:
            candidates.append((self.x + (1 if dx > 0 else -1), self.y))
        if dy:
            candidates.append((self.x, self.y + (1 if dy > 0 else -1)))
        candidates.sort(key=lambda point: hypot(point[0] - player.x, point[1] - player.y))
        for next_x, next_y in candidates:
            if (next_x, next_y) != (player.x, player.y) and dungeon.is_walkable(next_x, next_y):
                self.x, self.y = next_x, next_y
                self.animation_action = "walk"
                self.animation_action_time = 0.25
                break
        return False

    def to_dict(self) -> dict[str, int | str]:
        """Serialize enemy state to JSON-compatible values."""
        return {
            "x": self.x, "y": self.y, "name": self.name, "hp": self.hp,
            "atk": self.atk, "gold_reward": self.gold_reward,
            "enemy_type": self.enemy_type, "defense": self.defense,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Enemy":
        """Reconstruct an enemy from saved primitive values."""
        return cls(
            x=int(data["x"]), y=int(data["y"]),
            name=str(data.get("name", "Cave rat")),
            hp=int(data["hp"]), atk=int(data["atk"]),
            gold_reward=int(data.get("gold_reward", 5)),
            enemy_type=str(data.get("enemy_type", "slime")),
            defense=int(data.get("defense", 0)),
        )
