"""One-off headless integration check of the map editor screen. Not a
pytest suite — run directly: SDL_VIDEODRIVER=dummy python tests/check_editor.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame

pygame.init()
screen = pygame.display.set_mode((1200, 800))

from nanobot.ui.map_editor.map_editor import MapEditorScreen


def mouse_down(editor, pos, button=1):
    editor.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button))


def mouse_up(editor, pos, button=1):
    editor.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=button))


def mouse_move(editor, pos, rel=(0, 0)):
    editor.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=rel))


def key_down(editor, key, unicode=""):
    editor.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode, mod=0))


editor = MapEditorScreen((1200, 800))

# Helper: screen position for a grid cell, given current zoom/scroll/canvas origin.
def cell_screen_pos(editor, gx, gy):
    from nanobot.ui.map_editor.map_canvas_renderer import CELL_SIZE
    size = CELL_SIZE * editor.zoom
    return (int(editor.canvas_rect.x + gx * size + size / 2 - editor.scroll_x),
            int(editor.canvas_rect.y + gy * size + size / 2 - editor.scroll_y))


# --- Terrain paint ---
editor.activate_tool("terrain")
pos = cell_screen_pos(editor, 10, 10)
mouse_down(editor, pos)
mouse_up(editor, pos)
idx = 10 * editor.doc.width + 10
print("terrain painted (LOW by default, should stay LOW):", editor.doc._cells[idx]["density"])

# --- Habitas placement + duplicate guard + undo ---
editor.activate_tool("habitas")
before = len(editor.doc.habitas_points)
hpos = cell_screen_pos(editor, 20, 20)
mouse_down(editor, hpos)
mouse_up(editor, hpos)
print("habitas after place:", len(editor.doc.habitas_points), "was", before)
mouse_down(editor, hpos)  # duplicate
mouse_up(editor, hpos)
print("habitas after duplicate attempt (should be unchanged):", len(editor.doc.habitas_points))
editor._undo()
print("habitas after undo (should be back to", before, "):", len(editor.doc.habitas_points))

# --- Zone drag-to-place ---
editor.activate_tool("zone")
zones_before = len(editor.doc.injection_zones)
p1 = cell_screen_pos(editor, 40, 40)
p2 = cell_screen_pos(editor, 45, 44)
mouse_down(editor, p1)
mouse_move(editor, p2)
mouse_up(editor, p2)
print("zones after drag-place (should be +1):", len(editor.doc.injection_zones), "was", zones_before)
print("new zone rect:", editor.doc.injection_zones[-1]["rect"], "player:", editor.doc.injection_zones[-1]["player"])

# --- Edit tool: select + resize zone corner ---
editor.activate_tool("edit")
idx = len(editor.doc.injection_zones) - 1
rect = editor.doc.injection_zones[idx]["rect"]
corner_screen = cell_screen_pos(editor, rect[0], rect[1])
mouse_down(editor, corner_screen)
print("selected after click on corner:", editor.edit_selected_type, "idx=", editor.edit_selected_index,
      "corner=", editor.zone_resize_corner)
new_corner_screen = cell_screen_pos(editor, rect[0] + 1, rect[1] + 1)
mouse_move(editor, new_corner_screen)
print("resized rect:", editor.doc.injection_zones[idx]["rect"])
mouse_up(editor, new_corner_screen)

# --- Edit tool: AZN quantity inline editor ---
editor.activate_tool("edit")
azn_pos = editor.doc.azn_nodes[0]["position"]
azn_screen = cell_screen_pos(editor, *azn_pos)
mouse_down(editor, azn_screen)
mouse_up(editor, azn_screen)
print("selected azn:", editor.edit_selected_type, "idx=", editor.edit_selected_index)
key_down(editor, pygame.K_RETURN)
print("editing_quantity now:", editor.current_tool.editing_quantity, "buffer:", editor.current_tool.quantity_buffer)
key_down(editor, pygame.K_BACKSPACE)
key_down(editor, ord("9"), "9")
key_down(editor, ord("9"), "9")
key_down(editor, pygame.K_RETURN)
print("new azn quantity:", editor.doc.azn_nodes[0]["quantity"])

# --- Save / load round trip via the real screen methods ---
output_path = os.path.join(os.path.dirname(__file__), "..", "maps", "check_editor_output.json")
editor._do_save("check_editor_output.json")
print("saved file exists:", os.path.exists(output_path))
ok = editor._load_map_from_file(output_path)
print("reload ok:", ok)
print("reloaded habitas/azn/zones:", len(editor.doc.habitas_points), len(editor.doc.azn_nodes), len(editor.doc.injection_zones))
os.remove(output_path)  # this is a test artifact, not a real map

print("ALL OK")
