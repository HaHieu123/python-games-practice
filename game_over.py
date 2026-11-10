"""Run-completion screen and post-run navigation."""

import pygame

from .player import Player
from .settings import COLOR_ACCENT, COLOR_BACKGROUND, COLOR_MUTED, COLOR_STAIRS, COLOR_TEXT, FLOOR_COUNT, SCREEN_WIDTH
from .ui_components import draw_button, draw_panel, draw_text


class GameOverScreen:
    """Show a clear victory/defeat summary and next-step actions."""

    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 76)
        self.heading_font = pygame.font.Font(None, 31)
        self.body_font = pygame.font.Font(None, 25)
        self.button_font = pygame.font.Font(None, 28)
        self.button_rects: list[tuple[pygame.Rect, str]] = []

    def draw(
        self,
        surface: pygame.Surface,
        player: Player,
        victory: bool,
        run_seconds: float = 0.0,
        damage_dealt: int = 0,
        damage_taken: int = 0,
        is_new_game_plus: bool = False,
    ) -> None:
        """Draw the run summary and return/retry menu."""
        surface.fill(COLOR_BACKGROUND)
        for radius, color in ((230, (23, 31, 40)), (174, (27, 39, 47)), (120, (32, 48, 52))):
            pygame.draw.circle(surface, color, (SCREEN_WIDTH // 2, 220), radius)
        pygame.draw.circle(surface, COLOR_STAIRS if victory else (177, 82, 83), (SCREEN_WIDTH // 2, 220), 46)
        pygame.draw.circle(surface, (244, 224, 172), (SCREEN_WIDTH // 2, 220), 19)

        title = "The depths are conquered" if victory else "Your journey ends"
        color = COLOR_ACCENT if victory else (225, 125, 120)
        if is_new_game_plus:
            title = f"New Game+ · {title}"
        draw_text(surface, title, self.title_font, color, (SCREEN_WIDTH // 2, 355), center=True)
        draw_text(
            surface,
            "A hard-won escape from the Fivefold Depths." if victory else "The dungeon keeps what it claims.",
            self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2, 396), center=True,
        )

        panel = pygame.Rect(300, 435, 680, 126)
        draw_panel(surface, panel, fill=(23, 29, 39))
        summary = (
            (f"{player.floors_cleared}/{FLOOR_COUNT}", "FLOORS", COLOR_ACCENT),
            (str(player.enemies_killed), "FOES DEFEATED", COLOR_TEXT),
            (str(player.gold_earned), "GOLD EARNED", COLOR_STAIRS),
        )
        for index, (value, label, value_color) in enumerate(summary):
            center_x = 410 + index * 230
            draw_text(surface, value, self.heading_font, value_color, (center_x, 477), center=True)
            draw_text(surface, label, self.body_font, COLOR_MUTED, (center_x, 516), center=True)
        elapsed = int(run_seconds)
        stats = (
            f"Time {elapsed // 60:02}:{elapsed % 60:02}",
            f"Damage dealt {damage_dealt}",
            f"Damage taken {damage_taken}",
        )
        for index, label in enumerate(stats):
            draw_text(surface, label, self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2, 570 + index * 22), center=True)

        self.button_rects = []
        actions = (("Try again", "new"), ("Main menu", "menu"))
        for index, (label, action) in enumerate(actions):
            rect = pygame.Rect(440 + index * 210, 640, 190, 44)
            draw_button(surface, rect, label, self.button_font, selected=index == 0)
            self.button_rects.append((rect, action))

    def click(self, position: tuple[int, int]) -> str | None:
        """Return the post-run action clicked, if any."""
        for rect, action in self.button_rects:
            if rect.collidepoint(position):
                return action
        return None
