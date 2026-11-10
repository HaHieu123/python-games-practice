"""Audio and display settings screen."""

import pygame

from .game_options import GameOptions
from .settings import COLOR_ACCENT, COLOR_MUTED, COLOR_TEXT, SCREEN_WIDTH
from .ui_components import draw_button, draw_overlay, draw_panel, draw_text


class SettingsScreen:
    """Draw settings and map pointer positions to volume values."""

    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 54)
        self.heading_font = pygame.font.Font(None, 29)
        self.body_font = pygame.font.Font(None, 22)
        self.button_font = pygame.font.Font(None, 28)
        self.slider_rect = pygame.Rect(SCREEN_WIDTH // 2 - 180, 360, 360, 12)
        self.back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 110, 558, 220, 46)
        self.option_rects: list[tuple[pygame.Rect, str]] = []

    def draw(
        self,
        surface: pygame.Surface,
        volume: float,
        options: GameOptions | None = None,
    ) -> None:
        draw_overlay(surface, 195)
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 300, 130, 600, 490)
        draw_panel(surface, panel, fill=(23, 29, 39))
        draw_text(surface, "Settings", self.title_font, COLOR_TEXT, (SCREEN_WIDTH // 2, 180), center=True)
        draw_text(surface, "AUDIO", self.heading_font, COLOR_ACCENT, (SCREEN_WIDTH // 2 - 205, 233))
        draw_text(surface, "Master volume", self.body_font, COLOR_TEXT, (SCREEN_WIDTH // 2 - 205, 264))
        draw_text(surface, f"{round(volume * 100)}%", self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2 + 205, 264))

        self.slider_rect = pygame.Rect(SCREEN_WIDTH // 2 - 180, 292, 360, 12)
        pygame.draw.rect(surface, (49, 58, 71), self.slider_rect, border_radius=7)
        fill_rect = self.slider_rect.copy()
        fill_rect.width = round(self.slider_rect.width * max(0.0, min(1.0, volume)))
        if fill_rect.width:
            pygame.draw.rect(surface, COLOR_ACCENT, fill_rect, border_radius=7)
        knob_x = self.slider_rect.left + round(self.slider_rect.width * max(0.0, min(1.0, volume)))
        pygame.draw.circle(surface, (13, 18, 24), (knob_x, self.slider_rect.centery), 12)
        pygame.draw.circle(surface, COLOR_TEXT, (knob_x, self.slider_rect.centery), 8)
        pygame.draw.circle(surface, COLOR_ACCENT, (knob_x, self.slider_rect.centery), 4)

        draw_text(
            surface, "Drag the slider or use the left/right arrow keys.",
            self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2, 320), center=True,
        )
        self.option_rects = []
        if options is not None:
            draw_text(surface, "ACCESSIBILITY & PRESENTATION", self.heading_font, COLOR_ACCENT, (SCREEN_WIDTH // 2 - 205, 359))
            values = (
                ("Animation speed", f"{options.animation_speed:g}x", "animation_speed"),
                ("Screen shake", "On" if options.screen_shake else "Off", "screen_shake"),
                ("Damage numbers", "On" if options.damage_numbers else "Off", "damage_numbers"),
                ("Colorblind palette", "On" if options.colorblind_mode else "Off", "colorblind_mode"),
            )
            for index, (label, value, action) in enumerate(values):
                y = 390 + index * 36
                draw_text(surface, label, self.body_font, COLOR_TEXT, (SCREEN_WIDTH // 2 - 195, y))
                rect = pygame.Rect(SCREEN_WIDTH // 2 + 90, y - 4, 170, 30)
                draw_button(surface, rect, value, self.body_font, selected=True)
                self.option_rects.append((rect, action))
        draw_button(surface, self.back_rect, "Back", self.button_font, selected=True)

    def set_volume_from_position(self, position: tuple[int, int]) -> float:
        """Convert a pointer coordinate to a clamped 0.0-1.0 volume."""
        return max(0.0, min(1.0, (position[0] - self.slider_rect.left) / self.slider_rect.width))

    def hit_slider(self, position: tuple[int, int]) -> bool:
        """Return whether a pointer is close enough to interact with the slider."""
        expanded = self.slider_rect.inflate(0, 36)
        return expanded.collidepoint(position)

    def click(self, position: tuple[int, int]) -> str | None:
        """Return the action for a clicked settings control."""
        if self.back_rect.collidepoint(position):
            return "back"
        for rect, action in self.option_rects:
            if rect.collidepoint(position):
                return f"toggle:{action}"
        return None
