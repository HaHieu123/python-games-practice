"""Boss definitions, combat phases, telegraph state machine, and UI."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import TYPE_CHECKING

import pygame

from .animation import Animation
from .boss_attacks import attack_preview, execute_attack
from .enemy import Enemy
from .map_generator import DungeonMap
from .player import Player
from .settings import COLOR_ACCENT, COLOR_MUTED, COLOR_TEXT, SCREEN_WIDTH, TILE_SIZE, TileType
from .ui_components import draw_overlay, draw_panel, draw_text

if TYPE_CHECKING:
    from .boss_attacks import BossProjectile


@dataclass
class BossTurn:
    """Effects produced by a boss state-machine transition."""

    attack: str | None = None
    damage: int = 0
    summons: list[Enemy] = field(default_factory=list)
    shots: list[tuple[float, float, int]] = field(default_factory=list)
    phase_changed: bool = False


class Boss(Enemy):
    """Base boss with weighted attacks and IDLE/TELEGRAPH/EXECUTE/RECOVER AI."""

    boss_id = "boss"
    title = "Dungeon Boss"
    lore = "A dangerous guardian waits in the depths."
    base_phase = 1
    base_attacks: tuple[tuple[str, int, int], ...] = ()

    def __init__(
        self,
        x: int,
        y: int,
        *,
        hp: int,
        atk: int,
        defense: int,
        gold_reward: int,
        is_new_game_plus: bool = False,
    ) -> None:
        multiplier = 1.5 if is_new_game_plus else 1.0
        super().__init__(
            x=x,
            y=y,
            name=self.title,
            hp=round(hp * multiplier),
            atk=round(atk * multiplier),
            gold_reward=gold_reward * (2 if is_new_game_plus else 1),
            enemy_type=self.boss_id,
            defense=defense,
        )
        self.max_hp = self.hp
        self.state = "IDLE"
        self.attack_name: str | None = None
        self.telegraph_turns = 0
        self.recover_turns = 0
        self.turn_count = 0
        self.next_egg_turn = 5
        self.phase = self.base_phase
        self.telegraph_target = (x, y)
        self.shield_turns = 0
        self.flight_turns = 0
        self._phase_status_pending = False
        self.enraged = False
        self.is_new_game_plus = is_new_game_plus
        self.animation = Animation()

    @property
    def is_boss(self) -> bool:
        return True

    def take_damage(self, amount: int, *, melee: bool = False) -> bool:
        """Apply boss defense, shield/flight immunity, and phase transitions."""
        if self.shield_turns > 0 or (melee and self.flight_turns > 0):
            return False
        previous_phase = self.phase
        self.hp = max(0, self.hp - max(1, amount - self.defense))
        if self.hp <= 0:
            self.animation.set_state("death", force=True)
            return True
        self._check_phase(previous_phase)
        self.animation.set_state("hurt", force=True)
        if self.state == "TELEGRAPH" and self.enraged:
            self.telegraph_turns = min(self.telegraph_turns, 1)
        self._phase_changed_pending = self.phase != previous_phase
        self._phase_status_pending = self._phase_changed_pending
        return False

    def _check_phase(self, previous_phase: int) -> None:
        ratio = self.hp / max(1, self.max_hp)
        if self.boss_id == "skeleton_lord" and ratio <= 0.5 and self.phase == 1:
            self.phase = 2
            self.shield_turns = 2
        elif self.boss_id == "demon_chicken":
            self.phase = 1 if ratio > 0.66 else 2 if ratio > 0.33 else 3
            if self.phase > previous_phase:
                self.flight_turns = 3
        elif self.boss_id == "slime_king" and ratio <= 0.3:
            self.enraged = True
            self.phase = 2

    def take_boss_turn(self, player: Player, dungeon: DungeonMap) -> BossTurn:
        """Advance one boss AI turn and return resulting attacks and summons."""
        self.turn_count += 1
        phase_changed = getattr(self, "_phase_changed_pending", False)
        self._phase_changed_pending = False
        if self._phase_status_pending:
            self._phase_status_pending = False
        else:
            self.shield_turns = max(0, self.shield_turns - 1)
            self.flight_turns = max(0, self.flight_turns - 1)

        # Mỗi lượt của người chơi chỉ đẩy máy trạng thái boss tiến thêm một bước.
        if self.state == "RECOVER":
            self.recover_turns -= 1
            if self.recover_turns <= 0:
                self.state = "IDLE"
            return BossTurn(phase_changed=phase_changed)

        if self.state == "TELEGRAPH":
            self.telegraph_turns -= 1
            if self.telegraph_turns > 0:
                return BossTurn(phase_changed=phase_changed)
            result = self._execute(player, dungeon)
            result.phase_changed = result.phase_changed or phase_changed
            return result

        attack = self._choose_attack()
        self.state = "TELEGRAPH"
        self.attack_name = attack
        # Khóa ô mục tiêu tại lúc báo trước để người chơi có cơ hội né đòn.
        self.telegraph_target = (player.x, player.y)
        self.telegraph_turns = self._telegraph_duration(attack)
        if attack == "egg_bomb":
            self.telegraph_turns = 2
        if self.telegraph_turns <= 0:
            result = self._execute(player, dungeon)
            result.phase_changed = result.phase_changed or phase_changed
            return result
        return BossTurn(phase_changed=phase_changed)

    def _choose_attack(self) -> str:
        attacks = list(self.base_attacks)
        if self.phase >= 2:
            attacks.extend(self.phase_attacks())
        if self.boss_id == "demon_chicken" and self.turn_count >= self.next_egg_turn:
            self.next_egg_turn += 5
            return "egg_bomb"
        names = [name for name, weight, _ in attacks]
        weights = [weight for _, weight, _ in attacks]
        return random.choices(names, weights=weights, k=1)[0]

    def _telegraph_duration(self, attack: str) -> int:
        if self.enraged:
            return 0
        if attack in {"egg_bomb"}:
            return 2
        return 1

    def _execute(self, player: Player, dungeon: DungeonMap) -> BossTurn:
        attack = self.attack_name
        self.state = "EXECUTE"
        self.animation.set_state("attack", force=True)
        damage, summons, shots = execute_attack(self, attack or "", player, dungeon, [])
        self.state = "RECOVER"
        self.recover_turns = 1
        self.attack_name = None
        self._after_execute(attack)
        return BossTurn(attack, damage, summons, shots)

    def _after_execute(self, attack: str | None) -> None:
        if attack == "teleport":
            return

    def phase_attacks(self) -> list[tuple[str, int, int]]:
        return []

    def preview(self, player: Player, dungeon: DungeonMap) -> set[tuple[int, int]]:
        if self.state != "TELEGRAPH" or self.attack_name is None:
            return set()
        return attack_preview(self, player, dungeon, self.attack_name)

    def draw(self, surface: pygame.Surface, center: tuple[int, int], time: float = 0.0) -> None:
        """Draw a large, phase-tinted procedural boss sprite."""
        if not self.alive:
            return
        sprite = pygame.Surface((64, 64), pygame.SRCALPHA)
        tint = (210, 72, 75) if self.enraged or self.phase == 3 else (122, 70, 167)
        if self.boss_id == "slime_king":
            bounce = abs(math.sin(time * (7 if self.enraged else 4))) * 7
            body = pygame.Rect(7, 18 + round(bounce), 50, 37 - round(bounce / 2))
            pygame.draw.ellipse(sprite, (47, 105, 88), body)
            pygame.draw.ellipse(sprite, (*tint, 235), body.inflate(-8, -8))
            pygame.draw.circle(sprite, (245, 239, 213), (25, 32), 5)
            pygame.draw.circle(sprite, (245, 239, 213), (42, 32), 5)
            pygame.draw.circle(sprite, (34, 41, 39), (26, 33), 2)
            pygame.draw.circle(sprite, (34, 41, 39), (43, 33), 2)
            pygame.draw.polygon(sprite, (231, 184, 82), [(21, 17), (25, 5), (30, 18), (36, 4), (41, 18)])
        elif self.boss_id == "skeleton_lord":
            pygame.draw.circle(sprite, tint, (32, 16), 15)
            pygame.draw.circle(sprite, (222, 219, 198), (32, 21), 17, 5)
            pygame.draw.circle(sprite, (42, 34, 44), (27, 21), 4)
            pygame.draw.circle(sprite, (42, 34, 44), (38, 21), 4)
            pygame.draw.line(sprite, (223, 219, 198), (32, 34), (32, 57), 6)
            pygame.draw.line(sprite, (209, 205, 185), (17, 42), (47, 42), 4)
            pygame.draw.polygon(sprite, (197, 194, 179), [(20, 7), (26, 0), (32, 8), (38, 0), (45, 10)])
            pygame.draw.line(sprite, (206, 204, 194), (48, 36), (59, 12), 4)
        else:
            wing = round(math.sin(time * 10) * 7)
            pygame.draw.polygon(sprite, tint, [(28, 27), (4, 8 + wing), (14, 38), (31, 44)])
            pygame.draw.polygon(sprite, tint, [(36, 27), (60, 8 - wing), (50, 38), (33, 44)])
            pygame.draw.ellipse(sprite, (226, 178, 76), (15, 16, 35, 38))
            pygame.draw.circle(sprite, (250, 230, 196), (26, 29), 5)
            pygame.draw.circle(sprite, (250, 230, 196), (39, 29), 5)
            pygame.draw.circle(sprite, (37, 28, 24), (27, 30), 2)
            pygame.draw.circle(sprite, (37, 28, 24), (40, 30), 2)
            pygame.draw.polygon(sprite, (241, 134, 43), [(27, 38), (38, 38), (32, 47)])
            pygame.draw.polygon(sprite, (206, 78, 42), [(24, 53), (28, 60), (31, 53), (35, 60), (39, 53)])
        surface.blit(sprite, sprite.get_rect(center=center))
        if self.shield_turns:
            pygame.draw.circle(surface, (105, 205, 255), center, 39, 3)
        if self.flight_turns:
            pygame.draw.ellipse(surface, (188, 198, 219), (center[0] - 25, center[1] + 25, 50, 9))

    def serialize_boss(self) -> dict[str, int | str | bool]:
        return {
            "boss_id": self.boss_id,
            "x": self.x, "y": self.y, "hp": self.hp,
            "state": self.state, "attack_name": self.attack_name or "",
            "telegraph_turns": self.telegraph_turns, "recover_turns": self.recover_turns,
            "turn_count": self.turn_count, "phase": self.phase,
            "next_egg_turn": self.next_egg_turn,
            "target_x": self.telegraph_target[0], "target_y": self.telegraph_target[1],
            "shield_turns": self.shield_turns, "flight_turns": self.flight_turns,
            "enraged": self.enraged, "is_new_game_plus": self.is_new_game_plus,
        }

    @classmethod
    def from_state(cls, data: dict[str, object]) -> Boss:
        boss_cls = BOSS_TYPES[str(data["boss_id"])]
        boss = boss_cls(int(data["x"]), int(data["y"]), is_new_game_plus=bool(data.get("is_new_game_plus", False)))
        boss.hp = int(data["hp"])
        boss.state = str(data.get("state", "IDLE"))
        boss.attack_name = str(data.get("attack_name", "")) or None
        boss.telegraph_turns = int(data.get("telegraph_turns", 0))
        boss.recover_turns = int(data.get("recover_turns", 0))
        boss.turn_count = int(data.get("turn_count", 0))
        boss.next_egg_turn = int(data.get("next_egg_turn", (boss.turn_count // 5 + 1) * 5))
        boss.phase = int(data.get("phase", 1))
        boss.telegraph_target = (
            int(data.get("target_x", boss.x)),
            int(data.get("target_y", boss.y)),
        )
        boss.shield_turns = int(data.get("shield_turns", 0))
        boss.flight_turns = int(data.get("flight_turns", 0))
        boss._phase_status_pending = False
        boss.enraged = bool(data.get("enraged", False))
        return boss


class SlimeKing(Boss):
    boss_id = "slime_king"
    title = "Giant Slime King"
    lore = "The oldest thing in the caverns, grown fat on forgotten travelers."
    base_attacks = (("jump_slam", 4, 1), ("summon_slimes", 2, 1), ("acid_spit", 3, 1))

    def __init__(self, x: int, y: int, *, is_new_game_plus: bool = False) -> None:
        super().__init__(x, y, hp=150, atk=12, defense=3, gold_reward=75, is_new_game_plus=is_new_game_plus)

    def phase_attacks(self) -> list[tuple[str, int, int]]:
        return [("jump_slam", 6, 1), ("summon_slimes", 2, 1), ("acid_spit", 4, 0)]


class SkeletonLord(Boss):
    boss_id = "skeleton_lord"
    title = "Skeleton Lord"
    lore = "A fallen monarch whose crown binds an army of bone."
    base_attacks = (("summon_skeletons", 2, 1), ("bone_volley", 4, 1), ("charge", 3, 1))

    def __init__(self, x: int, y: int, *, is_new_game_plus: bool = False) -> None:
        super().__init__(x, y, hp=250, atk=18, defense=6, gold_reward=150, is_new_game_plus=is_new_game_plus)

    def phase_attacks(self) -> list[tuple[str, int, int]]:
        return [("teleport", 2, 0), ("bone_volley", 5, 1), ("charge", 4, 1)]

    def _execute(self, player: Player, dungeon: DungeonMap) -> BossTurn:
        if self.attack_name == "teleport":
            legal = [
                (x, y)
                for y, row in enumerate(dungeon.tiles)
                for x, tile in enumerate(row)
                if tile != TileType.WALL
                and max(abs(x - player.x), abs(y - player.y)) >= 5
            ]
            if legal:
                self.x, self.y = random.choice(legal)
            self.state = "RECOVER"
            self.recover_turns = 1
            self.attack_name = None
            return BossTurn("teleport")
        return super()._execute(player, dungeon)


class DemonChicken(Boss):
    boss_id = "demon_chicken"
    title = "Demon Chicken"
    lore = "The final guardian, hatched where the world itself began to burn."
    base_attacks = (("fire_breath", 4, 1), ("feather_barrage", 4, 1), ("dive", 2, 1))

    def __init__(self, x: int, y: int, *, is_new_game_plus: bool = False) -> None:
        super().__init__(x, y, hp=400, atk=25, defense=10, gold_reward=300, is_new_game_plus=is_new_game_plus)

    def phase_attacks(self) -> list[tuple[str, int, int]]:
        if self.phase == 2:
            return [("dive", 6, 1), ("feather_barrage", 4, 1)]
        if self.phase == 3:
            return [("dive", 7, 0), ("fire_breath", 6, 0), ("feather_barrage", 6, 0)]
        return []

    def _execute(self, player: Player, dungeon: DungeonMap) -> BossTurn:
        result = super()._execute(player, dungeon)
        if self.phase == 3 and result.attack == "dive":
            result.summons.extend(_spawn_chicks(self, dungeon, player))
        return result


BOSS_TYPES: dict[str, type[Boss]] = {
    SlimeKing.boss_id: SlimeKing,
    SkeletonLord.boss_id: SkeletonLord,
    DemonChicken.boss_id: DemonChicken,
}
BOSS_FLOORS = {2: SlimeKing, 4: SkeletonLord, 6: DemonChicken}


def _spawn_chicks(boss: Boss, dungeon: DungeonMap, player: Player) -> list[Enemy]:
    candidates = [
        (x, y)
        for y in range(max(1, boss.y - 3), min(dungeon.height - 1, boss.y + 4))
        for x in range(max(1, boss.x - 3), min(dungeon.width - 1, boss.x + 4))
        if dungeon.is_walkable(x, y)
        and (x, y) not in {(boss.x, boss.y), (player.x, player.y)}
    ]
    return [
        Enemy(x, y, name="Demon chick", hp=28, atk=12, gold_reward=10, enemy_type="bat")
        for x, y in candidates[:4]
    ]


class BossIntroScreen:
    """Brief dramatic boss introduction card."""

    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 62)
        self.body_font = pygame.font.Font(None, 27)

    def draw(self, surface: pygame.Surface, boss: Boss) -> None:
        draw_overlay(surface, 215)
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 370, 210, 740, 300)
        draw_panel(surface, panel, fill=(28, 25, 34))
        draw_text(surface, "A PRESENCE STIRS", self.body_font, COLOR_ACCENT, (SCREEN_WIDTH // 2, 260), center=True)
        draw_text(surface, boss.title, self.title_font, COLOR_TEXT, (SCREEN_WIDTH // 2, 322), center=True)
        draw_text(surface, boss.lore, self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2, 374), center=True)
        draw_text(surface, "Press Enter to face the guardian", self.body_font, COLOR_ACCENT, (SCREEN_WIDTH // 2, 455), center=True)


class BossHealthBar:
    """Large animated boss health bar with phase and shield states."""

    def __init__(self) -> None:
        self.ratio = 1.0
        self.font = pygame.font.Font(None, 26)
        self.small_font = pygame.font.Font(None, 20)

    def update(self, dt: float, boss: Boss) -> None:
        target = max(0.0, boss.hp / max(1, boss.max_hp))
        self.ratio += (target - self.ratio) * (1 - math.exp(-7 * max(0.0, dt)))

    def draw(self, surface: pygame.Surface, boss: Boss, dt: float = 0.0) -> None:
        self.update(dt, boss)
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 310, 18, 620, 66)
        pygame.draw.rect(surface, (15, 18, 25), panel, border_radius=10)
        pygame.draw.rect(surface, (110, 75, 84), panel, width=1, border_radius=10)
        draw_text(surface, boss.title, self.font, COLOR_TEXT, (panel.centerx, panel.top + 19), center=True)
        phase_label = f"PHASE {boss.phase}"
        if boss.enraged:
            phase_label = "ENRAGED"
        elif boss.shield_turns:
            phase_label = f"SHIELDED · {boss.shield_turns}"
        elif boss.flight_turns:
            phase_label = f"FLYING · {boss.flight_turns}"
        draw_text(surface, phase_label, self.small_font, COLOR_ACCENT, (panel.right - 74, panel.top + 19), center=True)
        bar = pygame.Rect(panel.left + 18, panel.top + 40, panel.width - 36, 14)
        pygame.draw.rect(surface, (58, 31, 39), bar, border_radius=6)
        fill = bar.copy()
        fill.width = round(bar.width * max(0.0, min(1.0, self.ratio)))
        if fill.width:
            pygame.draw.rect(surface, (196, 55, 66), fill, border_radius=6)
        pygame.draw.rect(surface, (233, 226, 226), bar, width=1, border_radius=6)


def draw_boss_telegraph(
    surface: pygame.Surface,
    boss: Boss,
    player: Player,
    dungeon: DungeonMap,
    camera: tuple[int, int],
    elapsed: float,
    colorblind_mode: bool = False,
) -> None:
    """Highlight preview tiles with a delta-time pulsing alpha overlay."""
    for x, y in boss.preview(player, dungeon):
        tile_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        alpha = round(60 + 110 * (0.5 + 0.5 * math.sin(elapsed * 8)))
        color = (245, 196, 39, alpha) if colorblind_mode else (243, 51, 60, alpha)
        pygame.draw.rect(tile_surface, color, tile_surface.get_rect())
        surface.blit(tile_surface, (x * TILE_SIZE - camera[0], y * TILE_SIZE - camera[1]))
    if boss.attack_name:
        label = pygame.font.Font(None, 23).render(
            f"{boss.title}: {boss.attack_name.replace('_', ' ').upper()}",
            True,
            (255, 190, 185),
        )
        surface.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 102)))
