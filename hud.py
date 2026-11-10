"""In-game status bar and dungeon minimap."""

import math

import pygame

from .map_generator import DungeonMap
from .player import Player
from .enemy import Enemy
from .settings import (
    COLOR_ACCENT,
    COLOR_ENEMY,
    COLOR_FLOOR,
    COLOR_MUTED,
    COLOR_PANEL,
    COLOR_PLAYER,
    COLOR_STAIRS,
    COLOR_TEXT,
    FLOOR_COUNT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from .ui_components import draw_text


class HUD:
    """Draw run status, player vitals, controls, and a compact map."""

    def __init__(self) -> None:
        self.font = pygame.font.Font(None, 29)
        self.small_font = pygame.font.Font(None, 22)
        self.tiny_font = pygame.font.Font(None, 18)
        self.displayed_hp_ratio = 1.0
        self.colorblind_mode = False

    def update(self, dt: float, player: Player) -> None:
        """Animate the displayed HP fill toward the player's actual vitality."""
        target = max(0.0, min(1.0, player.hp / max(1, player.max_hp)))
        blend = 1.0 - math.exp(-10.0 * max(0.0, dt))
        self.displayed_hp_ratio += (target - self.displayed_hp_ratio) * blend

    def draw(
        self,
        surface: pygame.Surface,
        player: Player,
        dungeon: DungeonMap,
        enemies: list[Enemy],
        floor: int,
        message: str = "",
        message_timer: float = 0,
    ) -> None:
        """Render the HUD over the lower edge of the game viewport."""
        bar = pygame.Rect(0, SCREEN_HEIGHT - 84, SCREEN_WIDTH, 84)
        pygame.draw.rect(surface, (15, 19, 26), bar)
        pygame.draw.line(surface, (66, 75, 88), bar.topleft, bar.topright, 1)

        self._stat_card(surface, pygame.Rect(18, 650, 132, 54), "DEPTH", f"{floor:02}/{FLOOR_COUNT}", COLOR_TEXT)
        self._stat_card(surface, pygame.Rect(160, 650, 140, 54), "GOLD", f"{player.gold}", COLOR_STAIRS)
        self._stat_card(
            surface,
            pygame.Rect(310, 650, 155, 54),
            "COMBAT",
            f"ATK {player.atk}   DEF {player.defense}",
            COLOR_MUTED,
        )

        hp_rect = pygame.Rect(482, 662, 254, 26)
        pygame.draw.rect(surface, (13, 17, 22), hp_rect, border_radius=9)
        hp_fill = pygame.Rect(
            hp_rect.left + 3,
            hp_rect.top + 3,
            round((hp_rect.width - 6) * self.displayed_hp_ratio),
            hp_rect.height - 6,
        )
        if self.displayed_hp_ratio > 0.6:
            hp_color = (63, 151, 218) if self.colorblind_mode else (64, 190, 105)
        elif self.displayed_hp_ratio >= 0.3:
            hp_color = (235, 182, 53)
        else:
            hp_color = (190, 65, 186) if self.colorblind_mode else (218, 66, 66)
        if hp_fill.width:
            pygame.draw.rect(surface, hp_color, hp_fill, border_radius=7)
        pygame.draw.rect(surface, (240, 244, 249), hp_rect, width=2, border_radius=9)
        draw_text(
            surface, f"HP {player.hp} / {player.max_hp}",
            self.small_font, (255, 255, 255), hp_rect.center, center=True,
        )
        if message_timer > 0 and message:
            draw_text(surface, message, self.small_font, COLOR_ACCENT, (760, 661))
        else:
            draw_text(
                surface, "WASD Move     F Bolt     I Pack     Esc Pause",
                self.tiny_font, COLOR_MUTED, (760, 678),
            )
        self._draw_minimap(surface, dungeon, player, enemies)

    def _stat_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        value: str,
        color: tuple[int, int, int],
    ) -> None:
        pygame.draw.rect(surface, COLOR_PANEL, rect, border_radius=8)
        pygame.draw.rect(surface, (57, 67, 80), rect, width=1, border_radius=8)
        draw_text(surface, label, self.tiny_font, COLOR_MUTED, (rect.left + 10, rect.top + 5))
        draw_text(surface, value, self.small_font, color, (rect.left + 10, rect.top + 26))

    def _draw_minimap(
        self,
        surface: pygame.Surface,
        dungeon: DungeonMap,
        player: Player,
        enemies: list[Enemy],
    ) -> None:
        scale = 2
        width, height = dungeon.width * scale, dungeon.height * scale
        panel = pygame.Rect(SCREEN_WIDTH - width - 28, 14, width + 14, height + 34)
        pygame.draw.rect(surface, (14, 18, 25), panel, border_radius=8)
        pygame.draw.rect(surface, (75, 86, 101), panel, width=1, border_radius=8)
        draw_text(surface, "FLOOR MAP", self.tiny_font, COLOR_MUTED, (panel.left + 7, panel.top + 5))
        origin = (panel.left + 7, panel.top + 22)
        for y, row in enumerate(dungeon.tiles):
            for x, tile in enumerate(row):
                if tile != 0:
                    color = COLOR_STAIRS if tile == 2 else COLOR_FLOOR
                    pygame.draw.rect(surface, color, (origin[0] + x * scale, origin[1] + y * scale, scale, scale))
        for enemy in enemies:
            if enemy.alive:
                pygame.draw.rect(
                    surface, COLOR_ENEMY,
                    (origin[0] + enemy.x * scale, origin[1] + enemy.y * scale, scale, scale),
                )
        pygame.draw.rect(
            surface, COLOR_PLAYER,
            (origin[0] + player.x * scale - 1, origin[1] + player.y * scale - 1, 4, 4),
        )
