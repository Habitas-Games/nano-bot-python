# v0.0.9 — Picker Placement Correction Analysis

**Status:** Complete
**Depends on:** [../v0.0.8/changelog.md](../v0.0.8/changelog.md)

---

## 1. What was asked vs. what was built

The user's original v0.0.7 request: "selecting the world, and
strategies should be on the run match windown [window], and option to
change and then it restart the simmulation." Read in isolation this is
ambiguous between "also put it there" and "move it there instead" — but
the user has now clarified directly it meant the latter: the map/
strategy pickers should live on the match/playback screen *only*,
replacing their v0.0.5 home on the main menu, not duplicating into a
second location.

v0.0.7 added the pickers (and a Restart button) to `PlaybackViewer`
correctly, but never removed the original copies from `MainMenu` —
since both screens ended up with picker UI, the result didn't match
what was asked for even though the playback-viewer half of it was right.

## 2. Why this is worth a version of its own rather than folding into v0.0.7's record

v0.0.7's changelog already describes, accurately, what was actually
built in v0.0.7 — rewriting it after the fact to pretend the main menu's
pickers were never added would misrepresent that version's real history
and verification trail. This version records the correction as its own
step: what was removed, why, and that the playback viewer (the screen
that was actually the point of the request) is unchanged.

## 3. Scope

Only `nanobot/ui/main_menu.py`. `playback_viewer.py`'s pickers/Restart
button (the part of v0.0.7 that was correct) are untouched.
