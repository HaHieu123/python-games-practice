"""Between-floor shop screen and item price presentation."""

import pygame

from .player import Player
from .settings import COLOR_ACCENT, COLOR_MUTED, COLOR_STAIRS, COLOR_TEXT, SCREEN_HEIGHT, SCREEN_WIDTH
from .ui_components import draw_button, draw_overlay, draw_panel, draw_text


class ShopScreen:
    """Present available upgrades and return selected purchase actions."""

    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 52)
        self.heading_font = pygame.font.Font(None, 28)
        self.body_font = pygame.font.Font(None, 23)
        self.button_font = pygame.font.Font(None, 25)
        self.item_rects: list[tuple[pygame.Rect, str]] = []
        self.continue_rect = pygame.Rect(SCREEN_WIDTH // 2 - 150, 566, 300, 52)

    def draw(
        self,
        surface: pygame.Surface,
        player: Player,
        next_floor: int,
        heal_price: int,
        attack_price: int,
        defense_price: int,
        message: str = "",
    ) -> None:
        """Draw the shop over the current floor."""
        draw_overlay(surface, 215)
        panel = pygame.Rect(300, 92, 680, 550)
        draw_panel(surface, panel, fill=(23, 29, 39))
        draw_text(surface, "The Wayfarer's Rest", self.title_font, COLOR_TEXT, (SCREEN_WIDTH // 2, 146), center=True)
        draw_text(
            surface, f"Supplies before Floor {next_floor}",
            self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2, 186), center=True,
        )
        gold_panel = pygame.Rect(SCREEN_WIDTH // 2 - 95, 216, 190, 42)
        pygame.draw.rect(surface, (39, 43, 48), gold_panel, border_radius=10)
        draw_text(
            surface, f"YOUR GOLD   {player.gold}",
            self.heading_font, COLOR_STAIRS, gold_panel.center, center=True,
        )

        offers = (
            ("heal", "Field rations", "Restore up to 30 vitality", heal_price, "HEAL"),
            ("attack", "Sharpened edge", "Increase attack by 2", attack_price, "ATK +2"),
            ("defense", "Reinforced armor", "Increase defense by 1", defense_price, "DEF +1"),
        )
        self.item_rects = []
        for index, (action, name, description, price, emblem) in enumerate(offers):
            rect = pygame.Rect(345, 278 + index * 82, 590, 68)
            pygame.draw.rect(surface, (31, 38, 49), rect, border_radius=10)
            pygame.draw.rect(surface, (62, 73, 88), rect, width=1, border_radius=10)
            pygame.draw.circle(surface, (54, 68, 78), (rect.left + 38, rect.centery), 22)
            draw_text(surface, emblem, self.body_font, COLOR_ACCENT, (rect.left + 38, rect.centery), center=True)
            draw_text(surface, name, self.heading_font, COLOR_TEXT, (rect.left + 76, rect.top + 8))
            draw_text(surface, description, self.body_font, COLOR_MUTED, (rect.left + 76, rect.top + 39))
            buy_rect = pygame.Rect(rect.right - 144, rect.top + 12, 126, 44)
            draw_button(
                surface,
                buy_rect,
                f"Buy  {price} G",
                self.button_font,
                enabled=player.gold >= price,
            )
            self.item_rects.append((buy_rect, action))

        if message:
            draw_text(
                surface, message, self.body_font, COLOR_ACCENT,
                (SCREEN_WIDTH // 2, 542), center=True,
            )
        draw_button(surface, self.continue_rect, "Continue to next floor", self.button_font, selected=True)
        draw_text(
            surface, "1 / 2 / 3  Purchase     Enter  Continue",
            self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 32), center=True,
        )

    def click(self, position: tuple[int, int]) -> str | None:
        """Return the shop action clicked by the player."""
        if self.continue_rect.collidepoint(position):
            return "continue"
        for rect, action in self.item_rects:
            if rect.collidepoint(position):
                return action
        return None

    @staticmethod
    def action_for_key(key: int) -> str | None:
        """Map number keys to shop offerings, or Enter to leaving the shop."""
        return {
            pygame.K_1: "heal",
            pygame.K_2: "attack",
            pygame.K_3: "defense",
            pygame.K_RETURN: "continue",
            pygame.K_ESCAPE: "continue",
        }.get(key)
