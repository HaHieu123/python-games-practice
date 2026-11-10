"""Pause overlay with resume, save, settings, and menu actions."""

import pygame

from .settings import COLOR_MUTED, COLOR_TEXT, SCREEN_HEIGHT, SCREEN_WIDTH
from .ui_components import draw_button, draw_overlay, draw_panel, draw_text


class PauseMenu:
    """Draw the pause menu and report clicked actions."""

    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 56)
        self.body_font = pygame.font.Font(None, 23)
        self.button_font = pygame.font.Font(None, 29)
        self.button_rects: list[tuple[pygame.Rect, str]] = []

    def draw(self, surface: pygame.Surface, message: str = "") -> None:
        draw_overlay(surface, 190)
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 220, 125, 440, 500)
        draw_panel(surface, panel, fill=(23, 29, 39))
        draw_text(surface, "Journey paused", self.title_font, COLOR_TEXT, (SCREEN_WIDTH // 2, 180), center=True)
        draw_text(surface, "Take a breath before the next descent.", self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2, 220), center=True)
        self.button_rects = []
        actions = (
            ("Resume", "resume"),
            ("Save expedition", "save"),
            ("Settings", "settings"),
            ("Return to main menu", "menu"),
        )
        for index, (label, action) in enumerate(actions):
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 170, 270 + index * 66, 340, 52)
            draw_button(surface, rect, label, self.button_font, selected=index == 0)
            self.button_rects.append((rect, action))
        if message:
            draw_text(surface, message, self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2, 560), center=True)
        draw_text(surface, "Esc  Resume", self.body_font, COLOR_MUTED, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 64), center=True)

    def click(self, position: tuple[int, int]) -> str | None:
        for rect, action in self.button_rects:
            if rect.collidepoint(position):
                return action
        return None
