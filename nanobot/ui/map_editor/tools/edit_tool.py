"""Select + move/resize elements. AZN quantity editing is an inline
text-entry overlay (press Enter while an AZN node is selected, type
digits, Enter to confirm / Escape to cancel) rather than a modal dialog —
pygame has no built-in dialog widgets, and this is simpler and arguably
nicer UX than the Godot version's popup ConfirmationDialog+SpinBox.

Selection (editor.edit_selected_type/index) lives on the editor, not
here, because the canvas renderer needs to read it to draw the highlight
— it stays decoupled from tool classes, same split as the Godot port.
Selection deliberately persists across switching to another tool and
back (matches that port's behavior too)."""

from __future__ import annotations

import pygame

from nanobot.ui.map_editor import map_document_ops as ops
from nanobot.ui.map_editor.tools.editor_tool import EditorTool


class EditTool(EditorTool):
    def __init__(self, editor):
        super().__init__(editor)
        self.editing_quantity = False
        self.quantity_buffer = ""

    def on_deactivate(self) -> None:
        self.editing_quantity = False

    def handle_press(self, grid_pos: tuple[int, int], button: int) -> bool:
        if button != 1 or not self.editor.doc.is_in_bounds(*grid_pos):
            return False
        self.editing_quantity = False

        element = ops.find_element_at(self.editor.doc, *grid_pos)
        if element["type"] != "none":
            self.editor.edit_selected_type = element["type"]
            self.editor.edit_selected_index = element["index"]
            self.editor.last_paint_pos = grid_pos
            self.editor.history.save_state(self.editor.doc)

            self.editor.zone_resize_corner = ""
            if element["type"] == "zone":
                self.editor.zone_resize_corner = ops.detect_zone_corner(
                    self.editor.doc, grid_pos[0], grid_pos[1], element["index"])

            return True
        else:
            self.editor.edit_selected_type = ""
            self.editor.edit_selected_index = -1
            self.editor.zone_resize_corner = ""
            return True

    def handle_drag(self, grid_pos: tuple[int, int], rel: tuple[int, int]) -> None:
        e = self.editor
        if e.edit_selected_type == "" or not e.doc.is_in_bounds(*grid_pos):
            return

        if e.edit_selected_type == "habitas":
            ops.move_habitas(e.doc, e.edit_selected_index, grid_pos)
        elif e.edit_selected_type == "azn":
            ops.move_azn(e.doc, e.edit_selected_index, grid_pos)
        elif e.edit_selected_type == "zone":
            if e.zone_resize_corner:
                ops.resize_zone(e.doc, e.edit_selected_index, e.zone_resize_corner, *grid_pos)
            else:
                offset = (grid_pos[0] - e.last_paint_pos[0], grid_pos[1] - e.last_paint_pos[1])
                if offset != (0, 0) and ops.move_zone(e.doc, e.edit_selected_index, offset):
                    e.last_paint_pos = grid_pos

    def handle_key(self, event: "pygame.event.Event") -> bool:
        e = self.editor

        if self.editing_quantity:
            if event.key == pygame.K_RETURN:
                qty = max(1, min(9999, int(self.quantity_buffer) if self.quantity_buffer else 1))
                e.history.save_state(e.doc)
                ops.set_azn_quantity(e.doc, e.edit_selected_index, qty)
                self.editing_quantity = False
            elif event.key == pygame.K_ESCAPE:
                self.editing_quantity = False
            elif event.key == pygame.K_BACKSPACE:
                self.quantity_buffer = self.quantity_buffer[:-1]
            elif event.unicode.isdigit() and len(self.quantity_buffer) < 4:
                self.quantity_buffer += event.unicode
            return True

        if event.key == pygame.K_RETURN and e.edit_selected_type == "azn":
            self.editing_quantity = True
            self.quantity_buffer = str(e.doc.azn_nodes[e.edit_selected_index]["quantity"])
            return True

        return False

    def get_status_text(self) -> str:
        if self.editing_quantity:
            return f"Editing AZN quantity: {self.quantity_buffer}_ | Enter to confirm, Esc to cancel"
        return "Tool: Edit ✏ | Click element to edit, drag to move | Enter on AZN to edit quantity"

    def get_cursor(self) -> int:
        return pygame.SYSTEM_CURSOR_HAND
