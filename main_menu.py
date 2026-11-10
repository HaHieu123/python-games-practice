"""Polished title screen and main-menu navigation."""

import pygame

from .settings import (
    COLOR_ACCENT,
    COLOR_BACKGROUND,
    COLOR_MUTED,
    COLOR_STAIRS,
    COLOR_TEXT,
    GAME_TITLE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from .ui_components import draw_button, draw_panel, draw_text


class MainMenu:
    """Draw the title screen and expose keyboard/mouse menu selection."""

    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 76)
        self.heading_font = pygame.font.Font(None, 34)
        self.body_font = pygame.font.Font(None, 24)
        self.button_font = pygame.font.Font(None, 31)
        self.options = [
            ("New expedition", "new"),
            ("New Game+", "new_game_plus"),
            ("Continue journey", "continue"),
            ("Settings", "settings"),
            ("Quit", "quit"),
        ]
        self.selected_index = 0
        self.button_rects: list[pygame.Rect] = []

    def draw(
        self,
        surface: pygame.Surface,
        *,
        can_continue: bool,
        can_new_game_plus: bool = False,
        message: str = "",
        message_timer: float = 0,
    ) -> None:
        """Draw the menu, title art, controls, and optional status message."""
        surface.fill(COLOR_BACKGROUND)
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(surface, (22, 27, 36), (x, 0), (x, SCREEN_HEIGHT), 1)
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(surface, (22, 27, 36), (0, y), (SCREEN_WIDTH, y), 1)

        art_center = (360, 342)
        pygame.draw.circle(surface, (27, 37, 48), art_center, 190)
        pygame.draw.circle(surface, (59, 77, 86), art_center, 158, 2)
        pygame.draw.circle(surface, (31, 45, 54), art_center, 126)
        pygame.draw.polygon(
            surface, (102, 91, 72),
            [(235, 350), (278, 278), (326, 350), (365, 282), (412, 350),
             (462, 270), (489, 350), (489, 421), (235, 421)],
        )
        pygame.draw.polygon(
            surface, (53, 65, 67),
            [(267, 352), (300, 312), (329, 352), (364, 316), (395, 352),
             (430, 307), (457, 352), (457, 397), (267, 397)],
        )
        pygame.draw.circle(surface, COLOR_STAIRS, (360, 368), 26)
        pygame.draw.circle(surface, (245, 219, 148), (360, 368), 11)
        for point in ((274, 258), (443, 247), (488, 441), (236, 435)):
            pygame.draw.circle(surface, COLOR_ACCENT, point, 4)

        title_rect = draw_text(
            surface, GAME_TITLE, self.title_font, COLOR_TEXT, (690, 128),
        )
        draw_text(
            surface, "DESCEND. ENDURE. RETURN.", self.heading_font,
            COLOR_ACCENT, (title_rect.left, 184),
        )
        draw_text(
            surface, "A turn-based journey beneath the old world.",
            self.body_font, COLOR_MUTED, (title_rect.left, 221),
        )

        panel = pygame.Rect(690, 250, 430, 390)
        draw_panel(surface, panel, fill=(23, 29, 39))
        draw_text(surface, "THE DESCENT", self.body_font, COLOR_MUTED, (720, 263))
        self.button_rects = []
        for index, (label, _) in enumerate(self.options):
            rect = pygame.Rect(715, 294 + index * 62, 380, 48)
            enabled = (
                can_new_game_plus if index == 1
                else can_continue if index == 2
                else True
            )
            draw_button(
                surface,
                rect,
                label,
                self.button_font,
                enabled=enabled,
                selected=index == self.selected_index,
            )
            self.button_rects.append(rect)

        draw_text(
            surface, "WASD / arrows  Move     I  Inventory     Esc  Pause",
            self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2, 666), center=True,
        )
        if message_timer > 0 and message:
            draw_text(surface, message, self.body_font, COLOR_STAIRS, (SCREEN_WIDTH // 2, 632), center=True)

    def move_selection(self, direction: int, can_continue: bool, can_new_game_plus: bool = False) -> None:
        """Move selection to the next enabled option."""
        for _ in self.options:
            self.selected_index = (self.selected_index + direction) % len(self.options)
            if (
                (self.selected_index != 1 or can_new_game_plus)
                and (self.selected_index != 2 or can_continue)
            ):
                return

    def activate(self, can_continue: bool, can_new_game_plus: bool = False) -> str | None:
        """Return the action for the currently selected enabled option."""
        if self.selected_index == 1 and not can_new_game_plus:
            return None
        if self.selected_index == 2 and not can_continue:
            return None
        return self.options[self.selected_index][1]

    def click(self, position: tuple[int, int], can_continue: bool, can_new_game_plus: bool = False) -> str | None:
        """Return the clicked action, if an enabled button was hit."""
        for index, rect in enumerate(self.button_rects):
            if rect.collidepoint(position):
                if index == 1 and not can_new_game_plus:
                    return None
                if index == 2 and not can_continue:
                    return None
                self.selected_index = index
                return self.options[index][1]
        return None
