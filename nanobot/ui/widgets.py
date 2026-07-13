"""Minimal immediate-mode-ish button widget for pygame, which has no
built-in UI toolkit. Shared by the main menu, map editor sidebar, and
playback controls so each doesn't reinvent button hit-testing/rendering."""

from __future__ import annotations

import os
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


def draw_hover_tooltips(surface: "pygame.Surface", buttons: list[Button]) -> None:
    """Draw the tooltip of whichever button is hovered, if any. Call last
    in a screen's draw() so the tooltip overlays everything. The map editor
    sidebar had the only tooltip rendering in the app; buttons elsewhere
    (playback viewer) set .tooltip too, which silently never appeared."""
    for btn in buttons:
        if not (btn.enabled and btn.hovered and btn.tooltip):
            continue
        font = get_font(12)
        label = font.render(btn.tooltip, True, (20, 20, 20))
        pad = 5
        box = pygame.Rect(btn.rect.left, btn.rect.bottom + 4,
                          label.get_width() + pad * 2, label.get_height() + pad * 2)
        box.left = max(4, min(box.left, surface.get_width() - box.width - 4))
        if box.bottom > surface.get_height() - 4:
            box.bottom = btn.rect.top - 4
        pygame.draw.rect(surface, (235, 230, 200), box, border_radius=3)
        pygame.draw.rect(surface, (40, 40, 30), box, width=1, border_radius=3)
        surface.blit(label, (box.x + pad, box.y + pad))
        return


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


class FilePickerModal:
    """A centered modal listing files to choose from, click a row to pick
    one. Originally written once for the main menu's map/strategy
    pickers; pulled out here once the playback viewer needed the exact
    same behavior, rather than copy-pasting the same ~50 lines twice."""

    def __init__(self):
        self._title = ""
        self._files: list[str] = []
        self._labels: list[str] = []
        self._on_select: Callable[[str], None] | None = None
        self._on_delete: Callable[[str], None] | None = None
        self._box_rect = pygame.Rect(0, 0, 0, 0)
        self._file_rects: list[tuple[pygame.Rect, int]] = []  # (rect, files-index)
        self._delete_rects: list[tuple[pygame.Rect, int]] = []
        self._scroll = 0

    @property
    def is_open(self) -> bool:
        return self._on_select is not None

    def open(self, title: str, files: list[str], on_select: Callable[[str], None],
             labels: list[str] | None = None,
             on_delete: "Callable[[str], None] | None" = None) -> None:
        """`labels`, if given, is what each row displays (e.g. a filename
        plus its age for replays); selection still returns the file path.
        `on_delete`, if given, puts an [x] on each row — clicking it calls
        the callback and removes the row, keeping the modal open (used by
        the replay browser to clean up old replays)."""
        self._title = title
        self._files = list(files)
        self._labels = labels if labels is not None else [_basename(p) for p in files]
        self._on_select = on_select
        self._on_delete = on_delete
        self._scroll = 0

    def close(self) -> None:
        self._on_select = None
        self._on_delete = None

    def handle_event(self, event: "pygame.event.Event") -> bool:
        """Returns True if the event was consumed (always True while open,
        since the modal should block whatever's underneath it)."""
        if not self.is_open:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, self._scroll - event.y * 2)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            for rect, i in self._delete_rects:
                if rect.collidepoint(event.pos):
                    path = self._files.pop(i)
                    self._labels.pop(i)
                    if self._on_delete:
                        self._on_delete(path)
                    if not self._files:
                        self.close()
                    return True
            for rect, i in self._file_rects:
                if rect.collidepoint(event.pos):
                    path = self._files[i]
                    on_select = self._on_select
                    self.close()
                    on_select(path)
                    return True
            if not self._box_rect.collidepoint(event.pos):
                self.close()
            return True
        return True

    def draw(self, surface: "pygame.Surface", screen_size: tuple[int, int]) -> None:
        if not self.is_open:
            return
        overlay = pygame.Surface(screen_size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        font = get_font(12)
        extra = 30 if self._on_delete else 0
        box_w = max(360, max((font.size(lbl)[0] for lbl in self._labels), default=0) + 44 + extra)
        visible = max(1, min(len(self._files), (screen_size[1] - 140) // 28))
        max_scroll = max(0, len(self._files) - visible)
        self._scroll = min(self._scroll, max_scroll)
        footer = 22 if max_scroll > 0 else 0
        box_h = 56 + 28 * visible + footer
        box_x = (screen_size[0] - box_w) // 2
        box_y = (screen_size[1] - box_h) // 2
        self._box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(surface, (45, 48, 58), self._box_rect, border_radius=6)
        pygame.draw.rect(surface, (90, 95, 110), self._box_rect, width=2, border_radius=6)

        draw_text(surface, self._title, (box_x + 16, box_y + 14), size=14)
        mouse = pygame.mouse.get_pos()
        rects, del_rects = [], []
        for row, i in enumerate(range(self._scroll, min(len(self._files), self._scroll + visible))):
            r = pygame.Rect(box_x + 12, box_y + 44 + row * 28, box_w - 24 - extra, 24)
            hovered = r.collidepoint(mouse)
            pygame.draw.rect(surface, (60, 64, 78) if hovered else (38, 40, 50), r, border_radius=3)
            draw_text(surface, self._labels[i], (r.x + 8, r.y + 4), size=12)
            rects.append((r, i))
            if self._on_delete:
                xr = pygame.Rect(r.right + 6, r.y + 3, 18, 18)
                xh = xr.collidepoint(mouse)
                pygame.draw.rect(surface, (95, 52, 52) if xh else (58, 44, 48), xr, border_radius=3)
                xl = get_font(11).render("x", True, (235, 185, 185))
                surface.blit(xl, xl.get_rect(center=xr.center))
                del_rects.append((xr, i))
        self._file_rects = rects
        self._delete_rects = del_rects
        if max_scroll > 0:
            draw_text(surface, f"{self._scroll + 1}-{self._scroll + visible} of {len(self._files)}  (scroll)",
                      (box_x + 16, box_y + box_h - 20), size=10, color=(140, 144, 158))
            self._draw_scrollbar(surface, box_x + box_w - 8, box_y + 44, 28 * visible,
                                 self._scroll, visible, len(self._files))

    @staticmethod
    def _draw_scrollbar(surface, x: int, y: int, height: int, scroll: int, visible: int, total: int) -> None:
        pygame.draw.rect(surface, (30, 32, 40), (x, y, 4, height), border_radius=2)
        thumb_h = max(18, int(height * visible / total))
        thumb_y = y + int((height - thumb_h) * (scroll / max(1, total - visible)))
        pygame.draw.rect(surface, (110, 116, 134), (x, thumb_y, 4, thumb_h), border_radius=2)


def _basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def _ask_directory(initial: str) -> str | None:
    """Open the OS folder picker (tkinter). Returns the chosen absolute
    path, "" if the user cancelled, or None if no dialog is available
    (headless / tkinter missing) — callers fall back to typed paths.
    Module-level so tests can monkeypatch it."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(initialdir=initial, title="Choose folder")
        root.destroy()
        return path or ""
    except Exception as e:
        print(f"OS folder dialog unavailable ({e}); type the path instead")
        return None


class FileBrowserModal:
    """A navigable file browser modal: shows the current folder's
    subdirectories plus files matching the given extensions, click a
    folder to enter it (".." to go up), click a file to choose it. In
    multi-select mode files toggle a checkmark instead and an "Add"
    button confirms the whole set at once — one at a time or several
    in a single visit both work.

    Unlike FilePickerModal (a fixed list for cases like "recent
    replays"), this browses the real filesystem: map and strategy
    files are no longer confined to the project's maps/ and
    strategies/ folders."""

    ROW_H = 26

    def __init__(self):
        self._title = ""
        self._dir = ""
        self._extensions: tuple[str, ...] = ()
        self._on_select: "Callable[[list[str]], None] | None" = None
        self._multi = False
        self._selected: set[str] = set()
        self._scroll = 0
        self._box_rect = pygame.Rect(0, 0, 0, 0)
        self._row_rects: list[tuple[pygame.Rect, str, bool]] = []  # (rect, path, is_dir)
        self._confirm_rect: pygame.Rect | None = None
        self._cancel_rect: pygame.Rect | None = None
        self._folder_rect: pygame.Rect | None = None
        self._path_rect: pygame.Rect | None = None
        # Click the path line to type/paste a folder directly — the
        # keyboard-only fallback when the OS dialog isn't available.
        self._editing_path = False
        self._path_buffer = ""

    @property
    def is_open(self) -> bool:
        return self._on_select is not None

    def open(self, title: str, start_dir: str, extensions: tuple[str, ...],
             on_select: "Callable[[list[str]], None]", multi: bool = False) -> None:
        """`on_select` always receives a list of absolute paths (length 1
        in single mode). `extensions` like (".py",)."""
        self._title = title
        self._dir = os.path.abspath(start_dir if os.path.isdir(start_dir) else os.path.expanduser("~"))
        self._extensions = extensions
        self._on_select = on_select
        self._multi = multi
        self._selected = set()
        self._scroll = 0
        self._filter = ""
        self._editing_path = False
        self._path_buffer = ""

    def close(self) -> None:
        self._on_select = None

    def _entries(self) -> list[tuple[str, bool]]:
        """(absolute path, is_dir) — parent first, then dirs, then
        matching files, both alphabetical; hidden/cache dirs skipped."""
        entries: list[tuple[str, bool]] = []
        parent = os.path.dirname(self._dir)
        if parent != self._dir:
            entries.append((parent, True))
        try:
            names = sorted(os.listdir(self._dir), key=str.lower)
        except OSError:
            names = []
        needle = self._filter.lower()
        for name in names:
            if name.startswith(".") or name == "__pycache__":
                continue
            if needle and needle not in name.lower():
                continue
            full = os.path.join(self._dir, name)
            if os.path.isdir(full):
                entries.append((full, True))
        for name in names:
            if name.startswith("."):
                continue
            if needle and needle not in name.lower():
                continue
            full = os.path.join(self._dir, name)
            if os.path.isfile(full) and name.lower().endswith(self._extensions):
                entries.append((full, False))
        return entries

    def _finish(self, paths: list[str]) -> None:
        on_select = self._on_select
        self.close()
        if on_select and paths:
            on_select(paths)

    def _navigate_to(self, path: str) -> bool:
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            return False
        self._dir = path
        self._scroll = 0
        self._filter = ""
        return True

    def _open_os_dialog(self) -> None:
        chosen = _ask_directory(self._dir)
        if chosen:
            self._navigate_to(chosen)
        elif chosen is None:
            # No dialog on this system — drop into typed-path mode so the
            # button still leads somewhere useful.
            self._editing_path = True
            self._path_buffer = self._dir

    def handle_event(self, event: "pygame.event.Event") -> bool:
        if not self.is_open:
            return False
        if event.type == pygame.KEYDOWN:
            if self._editing_path:
                if event.key == pygame.K_RETURN:
                    if self._navigate_to(self._path_buffer):
                        self._editing_path = False
                    # not a dir: stay in edit mode so the user can fix it
                elif event.key == pygame.K_ESCAPE:
                    self._editing_path = False
                elif event.key == pygame.K_BACKSPACE:
                    self._path_buffer = self._path_buffer[:-1]
                elif event.unicode and event.unicode.isprintable() and len(self._path_buffer) < 200:
                    self._path_buffer += event.unicode
                return True
            if event.key == pygame.K_ESCAPE:
                # First Esc clears an active filter; second closes.
                if self._filter:
                    self._filter = ""
                else:
                    self.close()
            elif event.key == pygame.K_RETURN and self._multi and self._selected:
                self._finish(sorted(self._selected))
            elif event.key == pygame.K_BACKSPACE:
                self._filter = self._filter[:-1]
                self._scroll = 0
            elif event.unicode and event.unicode.isprintable() and len(self._filter) < 30:
                # Type-to-filter: narrows the listing by substring.
                self._filter += event.unicode
                self._scroll = 0
            return True
        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, self._scroll - event.y * 2)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._folder_rect and self._folder_rect.collidepoint(event.pos):
                self._open_os_dialog()
                return True
            if self._path_rect and self._path_rect.collidepoint(event.pos):
                self._editing_path = True
                self._path_buffer = self._dir
                return True
            self._editing_path = False
            if self._confirm_rect and self._confirm_rect.collidepoint(event.pos) \
                    and self._multi and self._selected:
                self._finish(sorted(self._selected))
                return True
            if self._cancel_rect and self._cancel_rect.collidepoint(event.pos):
                self.close()
                return True
            for rect, path, is_dir in self._row_rects:
                if rect.collidepoint(event.pos):
                    if is_dir:
                        self._dir = path
                        self._scroll = 0
                        self._filter = ""
                    elif self._multi:
                        self._selected.symmetric_difference_update({path})
                    else:
                        self._finish([path])
                    return True
            if not self._box_rect.collidepoint(event.pos):
                self.close()
            return True
        # swallow everything else while open (modal)
        return event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)

    def _shorten(self, path: str, max_px: int, font: "pygame.font.Font") -> str:
        if font.size(path)[0] <= max_px:
            return path
        while path and font.size("..." + path)[0] > max_px:
            path = path[1:]
        return "..." + path

    def draw(self, surface: "pygame.Surface", screen_size: tuple[int, int]) -> None:
        if not self.is_open:
            return
        overlay = pygame.Surface(screen_size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        box_w = min(640, screen_size[0] - 60)
        box_h = min(520, screen_size[1] - 60)
        box_x = (screen_size[0] - box_w) // 2
        box_y = (screen_size[1] - box_h) // 2
        self._box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(surface, (45, 48, 58), self._box_rect, border_radius=6)
        pygame.draw.rect(surface, (90, 95, 110), self._box_rect, width=2, border_radius=6)

        draw_text(surface, self._title, (box_x + 16, box_y + 12), size=14)
        font12 = get_font(12)
        self._path_rect = pygame.Rect(box_x + 12, box_y + 31, box_w - 24 - (150 if self._filter else 100), 19)
        if self._editing_path:
            pygame.draw.rect(surface, (20, 22, 30), self._path_rect)
            pygame.draw.rect(surface, (120, 180, 130), self._path_rect, width=1)
            shown = self._shorten(self._path_buffer + "_", self._path_rect.width - 10, font12)
            draw_text(surface, shown, (self._path_rect.x + 5, self._path_rect.y + 2), size=12, color=(220, 224, 235))
            draw_text(surface, "Enter to go, Esc cancels", (box_x + box_w - 16 - font12.size("Enter to go, Esc cancels")[0], box_y + 34),
                      size=12, color=(150, 190, 160))
        else:
            hovered_path = self._path_rect.collidepoint(pygame.mouse.get_pos())
            if hovered_path:
                pygame.draw.rect(surface, (44, 47, 58), self._path_rect, border_radius=3)
            path_label = self._shorten(self._dir, self._path_rect.width - 10, font12)
            draw_text(surface, path_label, (self._path_rect.x + 5, self._path_rect.y + 2), size=12,
                      color=(190, 195, 210) if hovered_path else (150, 155, 168))
            if self._filter:
                flt = f"filter: {self._filter}  (Esc clears)"
                fw = font12.size(flt)[0]
                draw_text(surface, flt, (box_x + box_w - 16 - fw, box_y + 34), size=12, color=(200, 190, 120))
            else:
                hint = "click path to edit | type to filter"
                hw = get_font(10).size(hint)[0]
                draw_text(surface, hint, (box_x + box_w - 16 - hw, box_y + 36), size=10, color=(110, 114, 128))

        list_top = box_y + 56
        footer_h = 44
        visible = max(1, (box_h - (list_top - box_y) - footer_h) // self.ROW_H)
        entries = self._entries()
        max_scroll = max(0, len(entries) - visible)
        self._scroll = min(self._scroll, max_scroll)
        mouse = pygame.mouse.get_pos()

        rows = []
        for i, (path, is_dir) in enumerate(entries[self._scroll:self._scroll + visible]):
            r = pygame.Rect(box_x + 12, list_top + i * self.ROW_H, box_w - 24, self.ROW_H - 2)
            hovered = r.collidepoint(mouse)
            pygame.draw.rect(surface, (60, 64, 78) if hovered else (38, 40, 50), r, border_radius=3)
            if is_dir:
                # The parent entry is the only dir equal to dirname(cwd)
                # (children are strictly below it), so this is unambiguous.
                name = ".." if path == os.path.dirname(self._dir) else os.path.basename(path)
                draw_text(surface, f"[{name}]", (r.x + 8, r.y + 5), size=12, color=(150, 190, 235))
            else:
                x = r.x + 8
                if self._multi:
                    cb = pygame.Rect(x, r.y + 6, 13, 13)
                    pygame.draw.rect(surface, (20, 22, 30), cb, border_radius=2)
                    pygame.draw.rect(surface, (120, 126, 142), cb, width=1, border_radius=2)
                    if path in self._selected:
                        pygame.draw.rect(surface, (110, 200, 130), cb.inflate(-5, -5), border_radius=1)
                    x = cb.right + 8
                draw_text(surface, os.path.basename(path), (x, r.y + 5), size=12)
            rows.append((r, path, is_dir))
        self._row_rects = rows

        if max_scroll > 0:
            # x offset clears the Folder... button that lives at the
            # footer's left edge.
            draw_text(surface, f"{self._scroll + 1}-{min(len(entries), self._scroll + visible)} of {len(entries)} (scroll)",
                      (box_x + 120, box_y + box_h - footer_h + 16), size=10, color=(120, 124, 138))
            FilePickerModal._draw_scrollbar(surface, box_x + box_w - 10, list_top,
                                            visible * self.ROW_H, self._scroll, visible, len(entries))

        folder = Button((box_x + 16, box_y + box_h - 38, 92, 28), "Folder...",
                        tooltip="Pick a folder with the system dialog (or click the path above to type one)")
        folder.hovered = folder.rect.collidepoint(mouse)
        folder.draw(surface)
        self._folder_rect = folder.rect

        self._confirm_rect = None
        if self._multi:
            n = len(self._selected)
            confirm = Button((box_x + box_w - 240, box_y + box_h - 38, 110, 28), f"Add ({n})")
            confirm.enabled = n > 0
            confirm.hovered = confirm.rect.collidepoint(mouse)
            confirm.draw(surface)
            self._confirm_rect = confirm.rect
        cancel = Button((box_x + box_w - 116, box_y + box_h - 38, 100, 28), "Cancel")
        cancel.hovered = cancel.rect.collidepoint(mouse)
        cancel.draw(surface)
        self._cancel_rect = cancel.rect
        draw_hover_tooltips(surface, [folder])
