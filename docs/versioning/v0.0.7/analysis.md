# v0.0.7 — Run Match Workspace, Panning, Sprite Visibility Analysis

**Status:** Complete
**Depends on:** [../v0.0.6/changelog.md](../v0.0.6/changelog.md)

---

## 1. Trigger

Three pieces of feedback after actually using the playback viewer
(the screen "Run Match" opens into):

1. "selecting the world, and strategies should be on the run match
   window[], and option to change and then it restart the simulation."
2. "on the run match you can zoom but not pan or scrol[l]."
3. "It looks like not using the actual sprites for the bots and stuff."

## 2. Where map/strategy selection actually lived

v0.0.5 put the map/strategy pickers on the main menu — the screen
*before* "Run Match," not the screen the user actually watches a match
on. Changing your mind about a strategy mid-session meant leaving the
viewer, going back to the menu, re-picking, clicking Run Match again,
and waiting for a brand new screen to open. The user's framing —
selection "should be on the run match window" — is a request to move
where this lives to where the user is actually looking, plus a
mechanism to restart with the change in place, which didn't exist
anywhere before this version (the main menu's "Run Match" creates a new
match and opens a new `PlaybackViewer`; there was no way to re-run an
*existing* one from inside it).

## 3. Panning: a real interaction gap, not a missing feature

Confirmed directly: the existing pan code (`event.buttons[1]` checked
during `MOUSEMOTION`) worked correctly when tested with a synthetic
event carrying `buttons=(0,1,0)` — the logic was never broken. The gap
is that it requires holding the **middle mouse button** while dragging,
an interaction many trackpads have no comfortable way to perform at all,
and many mice make awkward (a hard click straight down on the scroll
wheel). "You can zoom but not pan" reads exactly like what happens when
the only pan method needs hardware the user doesn't have a good way to
use — zoom (scroll wheel) worked because every pointing device has a
wheel; pan (middle-drag) didn't because not every device has a usable
middle button.

## 4. Sprite visibility: confirmed by rendering a close-up crop

Rendered a bot at the (old) default zoom of 1.0 and cropped tightly
around it: the sprite resolved to roughly a 10×10 pixel region — at that
size, `bot_nanoai.png`'s actual gray/cyan ring design is indistinguishable
from a generic blurry circle, and the team-color ring drawn around it
visually dominates entirely. The code was correctly blitting the real
sprite the whole time (confirmed in v0.0.4) — the user's "looks like not
using the actual sprites" is an accurate description of what it visually
reads as, even though it's technically false as a claim about the code.
Re-rendering the same bot at a 1.5x zoom with a smaller icon inset
produced a crop where the ring-and-center-dot design is clearly
legible — see changelog for the side-by-side reasoning.

## 5. Scope boundary

This version changes `nanobot/ui/playback/playback_viewer.py` (the bulk
of the work), `nanobot/ui/widgets.py` (a new shared `FilePickerModal`,
extracted because this version needed the exact modal-list-picker logic
a second time), `nanobot/ui/main_menu.py` (refactored to use the shared
widget instead of its own copy — mechanical, not a behavior change), and
`main.py` (one bug fix described in §6). No simulation logic, scoring,
or JSON formats changed.

## 6. Bug found while building this: ESCAPE bypassed the new picker

`main.py`'s ESCAPE handling checked `getattr(self.current, "modal", None)
is not None` to decide whether to let the current screen handle Escape
itself (e.g. to dismiss a dialog) versus jumping straight to the main
menu. `PlaybackViewer` (and the refactored `MainMenu`) now hold their
modal-like state in `self.picker` (a `FilePickerModal`), not
`self.modal` — so this check returned `False` even while the picker was
open, meaning pressing Escape to close the map/strategy picker would
have jumped straight past it to the main menu instead, discarding
whatever the user was doing on this screen. Caught before it shipped by
testing the exact key sequence (open picker, press Escape, check both
"picker closed" and "still on the same screen") rather than only
checking the picker's own internal Escape handling in isolation.
