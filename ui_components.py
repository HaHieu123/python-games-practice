"""Reusable drawing helpers for the game's screens."""

import pygame

from .settings import COLOR_ACCENT, COLOR_MUTED, COLOR_PANEL, COLOR_TEXT


def draw_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    position: tuple[int, int],
    *,
    center: bool = False,
) -> pygame.Rect:
    """Render text and return its destination rectangle."""
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if center:
        rect.center = position
    else:
        rect.topleft = position
    surface.blit(rendered, rect)
    return rect


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill: tuple[int, int, int] = COLOR_PANEL,
) -> None:
    """Draw a raised panel with a fine border and top highlight."""
    shadow = rect.move(0, 6)
    pygame.draw.rect(surface, (8, 11, 16), shadow, border_radius=16)
    pygame.draw.rect(surface, fill, rect, border_radius=16)
    pygame.draw.rect(surface, (67, 76, 91), rect, width=1, border_radius=16)
    pygame.draw.line(
        surface, (75, 86, 103),
        (rect.left + 18, rect.top + 1), (rect.right - 18, rect.top + 1), 1,
    )


def draw_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    *,
    enabled: bool = True,
    selected: bool = False,
    subtitle: str | None = None,
) -> None:
    """Draw a rounded menu button with hover/selection and disabled styles."""
    if not enabled:
        fill = (35, 40, 49)
        border = (52, 59, 70)
        text_color = (116, 124, 137)
    elif selected:
        fill = (48, 77, 75)
        border = COLOR_ACCENT
        text_color = COLOR_TEXT
    else:
        fill = (38, 45, 56)
        border = (65, 75, 91)
        text_color = COLOR_TEXT

    pygame.draw.rect(surface, fill, rect, border_radius=10)
    pygame.draw.rect(surface, border, rect, width=1, border_radius=10)
    if subtitle:
        draw_text(surface, label, font, text_color, (rect.left + 20, rect.top + 8))
        subtitle_font = pygame.font.Font(None, 20)
        draw_text(surface, subtitle, subtitle_font, COLOR_MUTED, (rect.left + 20, rect.top + 34))
    else:
        draw_text(surface, label, font, text_color, rect.center, center=True)


def draw_overlay(surface: pygame.Surface, alpha: int = 190) -> None:
    """Dim the current screen before drawing a modal panel."""
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((5, 8, 13, alpha))
    surface.blit(shade, (0, 0))
