"""Player entity, regeneration, and a procedural pygame.draw sprite."""

from dataclasses import dataclass, field
import math

import pygame

from .animation import Animation


@dataclass
class Player:
    """Player position, combat stats, facing, and run-wide counters."""

    x: int
    y: int
    max_hp: int = 100
    hp: int = 100
    atk: int = 12
    defense: int = 3
    gold: int = 0
    gold_earned: int = 0
    enemies_killed: int = 0
    floors_cleared: int = 0
    facing: str = "down"
    regen_delay: float = field(default=0.0, init=False, repr=False)
    regen_accumulator: float = field(default=0.0, init=False, repr=False)
    hurt_timer: float = field(default=0.0, init=False, repr=False)
    animation_time: float = field(default=0.0, init=False, repr=False)
    animation_action_time: float = field(default=0.0, init=False, repr=False)
    animation: Animation = field(default_factory=Animation, init=False, repr=False, compare=False)
    _glow_surface: pygame.Surface = field(
        default_factory=lambda: pygame.Surface((64, 64), pygame.SRCALPHA),
        init=False,
        repr=False,
        compare=False,
    )
    _shadow_surface: pygame.Surface = field(
        default_factory=lambda: pygame.Surface((40, 16), pygame.SRCALPHA),
        init=False,
        repr=False,
        compare=False,
    )
    _sprite_surface: pygame.Surface = field(
        default_factory=lambda: pygame.Surface((48, 54), pygame.SRCALPHA),
        init=False,
        repr=False,
        compare=False,
    )
    _hurt_tint: pygame.Surface = field(
        default_factory=lambda: pygame.Surface((48, 54), pygame.SRCALPHA),
        init=False,
        repr=False,
        compare=False,
    )

    def take_damage(self, amount: int) -> int:
        """Apply damage after defense and return the actual HP lost."""
        actual_damage = max(1, amount - self.defense)
        previous_hp = self.hp
        self.hp = max(0, self.hp - actual_damage)
        lost = previous_hp - self.hp
        if lost:
            self.regen_delay = 3.0
            self.regen_accumulator = 0.0
            self.hurt_timer = 0.25
            self.animation.set_state("death" if self.hp <= 0 else "hurt", force=True)
        return lost

    def heal(self, amount: int) -> int:
        """Restore up to ``amount`` HP and return the amount restored."""
        previous_hp = self.hp
        self.hp = min(self.max_hp, self.hp + max(0, amount))
        return self.hp - previous_hp

    def use_potion(self) -> int:
        """Apply the standard instant +30 HP potion heal."""
        return self.heal(30)

    def add_gold(self, amount: int) -> None:
        """Add non-negative gold and update the run's earned-gold counter."""
        earned = max(0, amount)
        self.gold += earned
        self.gold_earned += earned

    def face(self, dx: int, dy: int) -> None:
        """Update facing from the most recent cardinal input or target."""
        if abs(dx) > abs(dy):
            self.facing = "right" if dx > 0 else "left"
        elif dy:
            self.facing = "down" if dy > 0 else "up"
        self.animation.set_facing(self.facing)

    def set_animation_state(self, state: str, *, force: bool = False) -> None:
        self.animation.set_state(state, force=force)
        if state == "walk":
            self.animation_action_time = 0.24
        elif state in {"attack", "hurt"}:
            self.animation_action_time = 0.0

    def update(self, dt: float) -> int:
        """Advance timers and passive HP regeneration; return whole HP gained."""
        dt = max(0.0, dt)
        self.animation_time += dt
        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.animation_action_time = max(0.0, self.animation_action_time - dt)
        if self.animation.state in {"hurt", "attack"} and self.animation.finished:
            self.animation.set_state("idle", force=True)
        elif self.animation.state == "walk" and self.animation_action_time == 0:
            self.animation.set_state("idle", force=True)
        self.animation.update(dt)
        regen_dt = max(0.0, dt - self.regen_delay)
        self.regen_delay = max(0.0, self.regen_delay - dt)
        if self.hp >= self.max_hp or self.hp <= 0 or self.regen_delay > 0:
            return 0

        self.regen_accumulator += regen_dt * 0.5
        whole_hp = int(self.regen_accumulator)
        if whole_hp <= 0:
            return 0
        restored = self.heal(whole_hp)
        self.regen_accumulator -= restored
        if self.hp >= self.max_hp:
            self.regen_accumulator = 0.0
        return restored

    def draw(self, surface: pygame.Surface, center: tuple[int, int]) -> None:
        """Draw the glow, ground shadow, and layered armor sprite."""
        sprite_width, sprite_height = 48, 54
        sprite_rect = pygame.Rect(
            center[0] - sprite_width // 2,
            center[1] - sprite_height // 2,
            sprite_width,
            sprite_height,
        )

        # Tạo quầng sáng cộng màu theo nhiều vòng để nhân vật nổi khỏi nền tối.
        glow = self._glow_surface
        glow.fill((0, 0, 0, 0))
        for radius, alpha in ((25, 5), (21, 7), (17, 9), (13, 12)):
            pygame.draw.circle(glow, (48, 132, 255, alpha), (32, 32), radius)
        surface.blit(
            glow,
            (center[0] - 32, center[1] - 32),
            special_flags=pygame.BLEND_RGB_ADD,
        )

        # Bóng elip nằm ngay dưới chân để tạo cảm giác nhân vật bám mặt đất.
        shadow = self._shadow_surface
        shadow.fill((0, 0, 0, 0))
        pygame.draw.ellipse(shadow, (0, 0, 0, 112), (2, 2, 36, 11))
        surface.blit(shadow, (center[0] - 20, center[1] + 13))

        sprite = self._sprite_surface
        sprite.fill((0, 0, 0, 0))
        gold = (209, 166, 82)
        gold_light = (249, 218, 133)
        steel = (104, 139, 171)
        steel_light = (184, 211, 227)
        armor = (54, 100, 139)
        armor_light = (92, 153, 195)
        skin = (232, 183, 143)
        dark = (29, 38, 48)

        # Giáp thân bo góc, có mảng sáng bên trái và đường viền kim loại.
        body_bob = -1 if self.animation.state == "idle" and self.animation.frame else 0
        body_top = 20 + body_bob
        pygame.draw.rect(sprite, dark, (10, body_top, 28, 27), border_radius=9)
        pygame.draw.rect(sprite, armor, (12, body_top, 24, 25), border_radius=8)
        pygame.draw.rect(sprite, armor_light, (14, body_top + 3, 6, 18), border_radius=3)
        pygame.draw.line(sprite, (139, 183, 207), (13, body_top + 2), (17, body_top + 1), 2)
        pygame.draw.line(sprite, (35, 67, 94), (34, body_top + 4), (34, body_top + 19), 2)

        # Thắt lưng tối màu và khóa đồng làm rõ ranh giới giữa thân với chân.
        pygame.draw.rect(sprite, (37, 43, 48), (12, 36, 24, 5), border_radius=2)
        pygame.draw.rect(sprite, gold, (22, 35, 5, 6), border_radius=1)
        pygame.draw.line(sprite, gold_light, (23, 36), (23, 39), 1)

        # Tay áo và găng tay được đặt hai bên thân giáp.
        pygame.draw.line(sprite, steel, (12, 26), (8, 36), 5)
        pygame.draw.line(sprite, steel_light, (11, 27), (9, 33), 2)
        pygame.draw.circle(sprite, skin, (8, 37), 3)
        pygame.draw.line(sprite, steel, (36, 26), (39, 34), 5)
        pygame.draw.circle(sprite, skin, (40, 35), 3)

        # Đầu có màu da, viền đậm và mũ sắt phủ phần trên.
        pygame.draw.circle(sprite, dark, (24, 14), 10)
        pygame.draw.circle(sprite, skin, (24, 14), 8)
        pygame.draw.circle(sprite, (255, 215, 177), (21, 15), 2)
        pygame.draw.ellipse(sprite, steel, (14, 4, 20, 14))
        pygame.draw.arc(sprite, steel_light, (15, 3, 18, 12), math.pi, 2 * math.pi, 2)
        pygame.draw.line(sprite, dark, (15, 12), (33, 12), 2)
        pygame.draw.line(sprite, gold, (22, 6), (26, 6), 2)

        # Mắt trượt theo hướng nhìn để thể hiện rõ bốn hướng di chuyển.
        eye_offset = {
            "up": (0, -2),
            "down": (0, 2),
            "left": (-2, 0),
            "right": (2, 0),
        }.get(self.facing, (0, 1))
        eye_y = 15 + eye_offset[1]
        eye_left = 21 + eye_offset[0]
        eye_right = 27 + eye_offset[0]
        pygame.draw.circle(sprite, (49, 39, 38), (eye_left, eye_y), 1)
        pygame.draw.circle(sprite, (49, 39, 38), (eye_right, eye_y), 1)

        # Thanh kiếm xoay theo hướng nhìn; chuôi và chắn tay vẫn tách biệt.
        sword_start = {
            "up": (38, 27),
            "down": (10, 27),
            "left": (13, 18),
            "right": (35, 18),
        }.get(self.facing, (35, 18))
        sword_end = {
            "up": (41, 10),
            "down": (7, 45),
            "left": (5, 14),
            "right": (43, 14),
        }.get(self.facing, (43, 14))
        if self.animation.state == "attack":
            sword_end = (sword_end[0], sword_end[1] + (-5, -12, -5)[self.animation.frame])
        pygame.draw.line(sprite, dark, sword_start, sword_end, 5)
        pygame.draw.line(sprite, gold, sword_start, sword_end, 2)
        pygame.draw.line(
            sprite, steel_light,
            (sword_start[0] + (sword_end[0] - sword_start[0]) // 2,
             sword_start[1] + (sword_end[1] - sword_start[1]) // 2),
            sword_end,
            2,
        )
        pygame.draw.line(
            sprite, gold_light,
            (sword_start[0] - 3, sword_start[1] + 3),
            (sword_start[0] + 3, sword_start[1] - 3),
            2,
        )

        if self.hurt_timer > 0:
            # Lọc toàn bộ điểm ảnh của sprite thành tông đỏ trong 15 khung hình.
            tint = self._hurt_tint
            tint.fill((255, 92, 92, 255))
            sprite.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        if self.hp <= 0:
            sprite.set_alpha(round(255 * (1.0 - self.animation.frame / 3)))
        surface.blit(sprite, sprite_rect)

    def to_dict(self) -> dict[str, int | str]:
        """Serialize player state to JSON-compatible values."""
        return {
            "x": self.x, "y": self.y, "max_hp": self.max_hp, "hp": self.hp,
            "atk": self.atk, "defense": self.defense, "gold": self.gold,
            "gold_earned": self.gold_earned, "enemies_killed": self.enemies_killed,
            "floors_cleared": self.floors_cleared, "facing": self.facing,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Player":
        """Reconstruct a player from saved primitive values."""
        player = cls(
            x=int(data["x"]),
            y=int(data["y"]),
            max_hp=int(data["max_hp"]),
            hp=int(data["hp"]),
            atk=int(data["atk"]),
            defense=int(data["defense"]),
            gold=int(data.get("gold", 0)),
            gold_earned=int(data.get("gold_earned", 0)),
            enemies_killed=int(data.get("enemies_killed", 0)),
            floors_cleared=int(data.get("floors_cleared", 0)),
            facing=str(data.get("facing", "down")),
        )
        if player.facing not in {"up", "down", "left", "right"}:
            player.facing = "down"
        return player
