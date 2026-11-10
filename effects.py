"""Delta-time projectiles, particles, damage text, and impact helpers."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
import random

import pygame

from .enemy import Enemy
from .map_generator import DungeonMap
from .settings import TILE_SIZE


@dataclass
class Particle:
    """A fading particle with world-space motion, gravity, and friction."""

    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    lifetime: float
    radius: float = 3.0
    gravity: float = 0.0
    friction: float = 0.0
    age: float = 0.0

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime

    def update(self, dt: float) -> None:
        dt = max(0.0, dt)
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        drag = math.exp(-self.friction * dt)
        self.vx *= drag
        self.vy *= drag

    def draw(self, surface: pygame.Surface, camera: tuple[int, int]) -> None:
        if not self.alive:
            return
        progress = min(1.0, self.age / self.lifetime)
        alpha = round(255 * (1.0 - progress))
        radius = max(1, round(self.radius * (1.0 - progress * 0.45)))
        position = (round(self.x - camera[0]), round(self.y - camera[1]))
        pygame.draw.circle(surface, (*self.color, alpha), position, radius)


@dataclass
class DamageText:
    """Floating outlined damage numbers that rise and fade in world space."""

    x: float
    y: float
    amount: int
    lifetime: float = 0.55
    age: float = 0.0
    rise_speed: float = 42.0
    font: pygame.font.Font = field(default_factory=lambda: pygame.font.Font(None, 25), repr=False)

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime

    def update(self, dt: float) -> None:
        self.age += max(0.0, dt)
        self.y -= self.rise_speed * max(0.0, dt)

    def draw(self, surface: pygame.Surface, camera: tuple[int, int]) -> None:
        if not self.alive:
            return
        progress = min(1.0, self.age / self.lifetime)
        text = self.font.render(str(self.amount), True, (255, 255, 255))
        outline = self.font.render(str(self.amount), True, (214, 63, 53))
        text.set_alpha(round(255 * (1.0 - progress)))
        outline.set_alpha(round(255 * (1.0 - progress)))
        rect = text.get_rect(center=(round(self.x - camera[0]), round(self.y - camera[1])))
        for offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            surface.blit(outline, rect.move(offset))
        surface.blit(text, rect)


@dataclass
class Projectile:
    """A glowing shot that homes toward its target and collides with enemies."""

    x: float
    y: float
    target: Enemy
    damage: int
    speed: float = 430.0
    color: tuple[int, int, int] = (88, 190, 255)
    radius: float = 7.0
    trail: deque[tuple[float, float]] = field(default_factory=lambda: deque(maxlen=8), repr=False)
    alive: bool = True

    def update(
        self,
        dt: float,
        enemies: list[Enemy],
        dungeon: DungeonMap,
    ) -> Enemy | None:
        """Move toward the live target and return an enemy hit this frame."""
        if not self.alive:
            return None
        dt = max(0.0, dt)
        if not self.target.alive:
            self.alive = False
            return None

        target_x = self.target.x * TILE_SIZE + TILE_SIZE / 2
        target_y = self.target.y * TILE_SIZE + TILE_SIZE / 2
        previous_x, previous_y = self.x, self.y
        dx, dy = target_x - self.x, target_y - self.y
        distance = math.hypot(dx, dy)
        if distance:
            travel = min(distance, self.speed * dt)
            self.x += dx / distance * travel
            self.y += dy / distance * travel
        self.trail.append((self.x, self.y))

        tile_x, tile_y = int(self.x // TILE_SIZE), int(self.y // TILE_SIZE)
        if not dungeon.is_walkable(tile_x, tile_y):
            self.alive = False
            return None

        for enemy in enemies:
            if not enemy.alive:
                continue
            enemy_x = enemy.x * TILE_SIZE + TILE_SIZE / 2
            enemy_y = enemy.y * TILE_SIZE + TILE_SIZE / 2
            segment_x = self.x - previous_x
            segment_y = self.y - previous_y
            segment_length_sq = segment_x * segment_x + segment_y * segment_y
            if segment_length_sq:
                projection = max(
                    0.0,
                    min(
                        1.0,
                        ((enemy_x - previous_x) * segment_x
                         + (enemy_y - previous_y) * segment_y) / segment_length_sq,
                    ),
                )
                closest_x = previous_x + projection * segment_x
                closest_y = previous_y + projection * segment_y
            else:
                closest_x, closest_y = self.x, self.y
            if math.hypot(enemy_x - closest_x, enemy_y - closest_y) <= self.radius + 8:
                self.alive = False
                return enemy

        return None

    def draw(self, surface: pygame.Surface, camera: tuple[int, int]) -> None:
        """Draw eight fading trail orbs and the bright projectile head."""
        for index, (trail_x, trail_y) in enumerate(self.trail):
            progress = (index + 1) / max(1, len(self.trail))
            alpha = round(28 + progress * 145)
            radius = max(2, round(self.radius * (0.28 + progress * 0.48)))
            pygame.draw.circle(
                surface,
                (*self.color, alpha),
                (round(trail_x - camera[0]), round(trail_y - camera[1])),
                radius,
            )
        center = (round(self.x - camera[0]), round(self.y - camera[1]))
        pygame.draw.circle(surface, (*self.color, 95), center, round(self.radius + 5))
        pygame.draw.circle(surface, (*self.color, 240), center, round(self.radius))
        pygame.draw.circle(surface, (255, 255, 255, 255), center, max(2, round(self.radius * 0.42)))


@dataclass
class ScreenShake:
    """Short-lived screen-space shake with a configurable pixel intensity."""

    intensity: float = 6.0
    duration: float = 0.15
    remaining: float = 0.0

    def trigger(self) -> None:
        self.remaining = self.duration

    def update(self, dt: float) -> tuple[int, int]:
        if self.remaining <= 0:
            return 0, 0
        strength = self.intensity * self.remaining / self.duration
        offset = round(random.uniform(-strength, strength)), round(random.uniform(-strength, strength))
        self.remaining = max(0.0, self.remaining - max(0.0, dt))
        return offset


def spawn_hit_particles(
    position: tuple[float, float],
    count: int = 14,
) -> list[Particle]:
    """Create orange impact sparks with randomized velocity and a short fade."""
    particles: list[Particle] = []
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(65, 230)
        particles.append(
            Particle(
                x=position[0],
                y=position[1],
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 35,
                color=random.choice(((255, 112, 42), (255, 168, 61), (255, 219, 122))),
                lifetime=random.uniform(0.3, 0.6),
                radius=random.uniform(2, 4),
                gravity=260,
                friction=2.2,
            )
        )
    return particles


def spawn_heal_particles(position: tuple[float, float], count: int = 5) -> list[Particle]:
    """Create small green motes that rise above the player when HP is restored."""
    particles: list[Particle] = []
    for _ in range(count):
        particles.append(
            Particle(
                x=position[0] + random.uniform(-12, 12),
                y=position[1] - random.uniform(8, 24),
                vx=random.uniform(-12, 12),
                vy=random.uniform(-45, -20),
                color=random.choice(((83, 232, 132), (131, 255, 170), (47, 190, 104))),
                lifetime=random.uniform(0.45, 0.75),
                radius=random.uniform(2, 3.5),
                friction=1.0,
            )
        )
    return particles


def spawn_damage_text(position: tuple[float, float], amount: int) -> DamageText:
    """Create a white damage number with a high-contrast red outline."""
    return DamageText(position[0], position[1], max(0, amount))
