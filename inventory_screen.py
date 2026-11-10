"""Inventory overlay for player gear, carried items, and character stats."""

import pygame

from .player import Player
from .settings import COLOR_ACCENT, COLOR_MUTED, COLOR_STAIRS, COLOR_TEXT, SCREEN_HEIGHT, SCREEN_WIDTH
from .ui_components import draw_button, draw_overlay, draw_panel, draw_text


class InventoryScreen:
    """Display carried resources and currently empty item/equipment slots."""

    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 48)
        self.heading_font = pygame.font.Font(None, 28)
        self.body_font = pygame.font.Font(None, 23)
        self.button_font = pygame.font.Font(None, 26)
        self.close_rect = pygame.Rect(795, 180, 34, 34)

    def draw(self, surface: pygame.Surface, player: Player) -> None:
        """Draw the inventory modal with equipment, pack, and character cards."""
        draw_overlay(surface, 195)
        panel = pygame.Rect(300, 130, 680, 480)
        draw_panel(surface, panel, fill=(23, 29, 39))
        draw_text(surface, "Adventurer's pack", self.title_font, COLOR_TEXT, (340, 158))
        draw_text(surface, "EQUIPMENT", self.heading_font, COLOR_ACCENT, (342, 232))
        draw_text(surface, "BACKPACK", self.heading_font, COLOR_ACCENT, (590, 232))

        gear_labels = ("Weapon", "Armor", "Charm")
        for index, label in enumerate(gear_labels):
            rect = pygame.Rect(340, 274 + index * 76, 215, 62)
            pygame.draw.rect(surface, (31, 38, 49), rect, border_radius=9)
            pygame.draw.rect(surface, (62, 73, 88), rect, width=1, border_radius=9)
            pygame.draw.rect(surface, (56, 68, 80), (rect.left + 12, rect.top + 12, 38, 38), border_radius=7)
            pygame.draw.circle(surface, COLOR_STAIRS, (rect.left + 31, rect.top + 31), 8, 2)
            draw_text(surface, label, self.body_font, COLOR_TEXT, (rect.left + 62, rect.top + 12))
            draw_text(surface, "Empty slot", self.body_font, COLOR_MUTED, (rect.left + 62, rect.top + 34))

        slot_size, gap = 52, 8
        for row in range(3):
            for column in range(3):
                x = 590 + column * (slot_size + gap)
                y = 274 + row * (slot_size + gap)
                rect = pygame.Rect(x, y, slot_size, slot_size)
                pygame.draw.rect(surface, (31, 38, 49), rect, border_radius=8)
                pygame.draw.rect(surface, (62, 73, 88), rect, width=1, border_radius=8)
                pygame.draw.line(surface, (48, 58, 71), (x + 16, y + 29), (x + 42, y + 29), 1)

        stats = pygame.Rect(790, 274, 160, 178)
        pygame.draw.rect(surface, (31, 38, 49), stats, border_radius=10)
        draw_text(surface, "FIELD NOTES", self.body_font, COLOR_MUTED, (802, 290))
        stat_lines = (
            (f"HP {player.hp}/{player.max_hp}", COLOR_TEXT),
            (f"Attack {player.atk}", COLOR_TEXT),
            (f"Defense {player.defense}", COLOR_TEXT),
            (f"Gold {player.gold}", COLOR_STAIRS),
        )
        for index, (line, color) in enumerate(stat_lines):
            draw_text(surface, line, self.body_font, color, (802, 326 + index * 30))

        draw_text(
            surface, "Items and equipment will appear here as you explore.",
            self.body_font, COLOR_MUTED, (340, 526),
        )
        draw_button(surface, self.close_rect, "X", self.button_font)
        draw_text(
            surface, "Press I or Esc to close", self.body_font, COLOR_ACCENT,
            (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 78), center=True,
        )

    def click(self, position: tuple[int, int]) -> bool:
        """Return whether the close control was clicked."""
        return self.close_rect.collidepoint(position)
