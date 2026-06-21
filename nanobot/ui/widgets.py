"""Minimal immediate-mode-ish button widget for pygame, which has no
built-in UI toolkit. Shared by the main menu, map editor sidebar, and
playback controls so each doesn't reinvent button hit-testing/rendering."""

from __future__ import annotations

from typing import Callable

import pygame

FONT_CACHE: dict[int, "pygame.font.Font"] = {}


def get_font(size: int = 14) -> "pygame.font.Font":
    if size not in FONT_CACHE:
        FONT_CACHE[size] = pygame.font.SysFont("sans", size)
    return FONT_CACHE[size]


class Button:
    def __init__(self, rect: tuple[int, int, int, int], text: str,
                 on_click: Callable[[], None] | None = None,
                 toggle: bool = False, pressed: bool = False,
                 tooltip: str = "", icon: "pygame.Surface | None" = None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.toggle = toggle
        self.pressed = pressed
        self.tooltip = tooltip
        self.icon = icon
        self.enabled = True
        self.hovered = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.toggle:
                    self.pressed = not self.pressed
                if self.on_click:
                    self.on_click()
                return True
        return False

    def draw(self, surface: "pygame.Surface") -> None:
        if not self.enabled:
            bg = (40, 40, 40)
            fg = (110, 110, 110)
        elif self.pressed:
            bg = (70, 130, 90)
            fg = (235, 235, 235)
        elif self.hovered:
            bg = (60, 64, 78)
            fg = (235, 235, 235)
        else:
            bg = (45, 48, 58)
            fg = (215, 218, 228)

        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        pygame.draw.rect(surface, (20, 22, 30), self.rect, width=1, border_radius=4)

        if self.icon and self.text:
            font = get_font(13)
            label = font.render(self.text, True, fg)
            gap = 6
            total_w = self.icon.get_width() + gap + label.get_width()
            left = self.rect.centerx - total_w // 2
            surface.blit(self.icon, self.icon.get_rect(centery=self.rect.centery, left=left))
            surface.blit(label, label.get_rect(centery=self.rect.centery, left=left + self.icon.get_width() + gap))
        elif self.icon:
            icon_rect = self.icon.get_rect(center=self.rect.center)
            surface.blit(self.icon, icon_rect)
        elif self.text:
            font = get_font(13)
            label = font.render(self.text, True, fg)
            surface.blit(label, label.get_rect(center=self.rect.center))


class ButtonGroup:
    """A set of mutually-exclusive toggle buttons (only one pressed at a time)."""

    def __init__(self, buttons: list[Button] | None = None):
        self.buttons = buttons or []

    def add(self, button: Button) -> Button:
        button.toggle = True
        self.buttons.append(button)
        return button

    def handle_event(self, event: pygame.event.Event) -> Button | None:
        for btn in self.buttons:
            if btn.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 \
                    and btn.rect.collidepoint(event.pos):
                for other in self.buttons:
                    other.pressed = (other is btn)
                if btn.on_click:
                    btn.on_click()
                return btn
            btn.handle_event(event)
        return None

    def set_pressed(self, button: Button) -> None:
        for btn in self.buttons:
            btn.pressed = (btn is button)

    def draw(self, surface: "pygame.Surface") -> None:
        for btn in self.buttons:
            btn.draw(surface)


def draw_text(surface: "pygame.Surface", text: str, pos: tuple[int, int],
              size: int = 14, color: tuple[int, int, int] = (215, 218, 228)) -> None:
    font = get_font(size)
    surface.blit(font.render(text, True, color), pos)


class Slider:
    """A horizontal scrubber — click or drag anywhere on the track to jump
    straight to that value, matching the Godot HUD's "Jump to turn" slider
    (HSlider) rather than only stepping one increment per click."""

    def __init__(self, rect: tuple[int, int, int, int], min_value: int, max_value: int,
                 value: int = 0, on_change: Callable[[int], None] | None = None):
        self.rect = pygame.Rect(rect)
        self.min_value = min_value
        self.max_value = max_value
        self.value = value
        self.on_change = on_change
        self._dragging = False

    def set_range(self, min_value: int, max_value: int) -> None:
        self.min_value = min_value
        self.max_value = max(max_value, min_value)
        self.value = max(self.min_value, min(self.max_value, self.value))

    def set_value(self, value: int) -> None:
        self.value = max(self.min_value, min(self.max_value, value))

    def _value_at(self, x: int) -> int:
        span = max(1, self.max_value - self.min_value)
        t = max(0.0, min(1.0, (x - self.rect.x) / self.rect.width))
        return self.min_value + round(t * span)

    def handle_event(self, event: "pygame.event.Event") -> bool:
        if self.max_value <= self.min_value:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self._dragging = True
            self.value = self._value_at(event.pos[0])
            if self.on_change:
                self.on_change(self.value)
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self.value = self._value_at(event.pos[0])
            if self.on_change:
                self.on_change(self.value)
            return True
        return False

    def draw(self, surface: "pygame.Surface") -> None:
        track = pygame.Rect(self.rect.x, self.rect.centery - 2, self.rect.width, 4)
        pygame.draw.rect(surface, (20, 22, 30), track, border_radius=2)
        span = max(1, self.max_value - self.min_value)
        t = (self.value - self.min_value) / span
        handle_x = self.rect.x + int(t * self.rect.width)
        pygame.draw.circle(surface, (120, 200, 140), (handle_x, self.rect.centery), 6)
        pygame.draw.circle(surface, (20, 22, 30), (handle_x, self.rect.centery), 6, width=1)
