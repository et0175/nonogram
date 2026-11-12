# CARD-430: The compact zoom is one joined control: a pill on a phone, a block across the landscape strip

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.25d)
<!-- Basis: CSS only, in admin.css's compact and landscape blocks; the player's zoom tests are the check. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-12 (project thread): "can you propose a different design for a zoom button when it's small?"; of three mockups chose "option A" (a joined pill), "but in the landscape mode we have 2 columns of buttons, probably your long side fits better".
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-428, CARD-429
**Touches:** src/nonogram/admin/static/admin.css
**Review score:** — (no review cycle; merged on the gates)
**Started:** 2026-11-12T11:05Z
**Closed:** 2026-11-12T11:23Z
**Actual:** one owner session (wall clock excluded, owner ruling)
**Merge commit:** cabe4c50
**Blocked by:** —

## What to implement

In the compact toolbar (`max-width: 600px` or `max-height: 500px`) the zoom group's three members (minus, plus, the readout that is also the Fit button) become one bordered control divided by hairlines: a rounded pill in a row. In the landscape strip (two 44 px columns), where a one-row pill would leave each member about 30 px, it is one rounded block spanning both columns: minus and plus side by side, the readout across the row below (CARD-428's arrangement, now joined). The DOM order is unchanged (CARD-429's focus order), every member keeps its 44 px target, and a focus ring is drawn inside the clip.

## Acceptance criteria

- **AC-1** *Given* the compact toolbar, *then* the zoom group is one bordered control with no gap between its members, each at least 44 px; in the landscape strip, minus and plus share a row and the readout spans the row below, inside the same border. (test: `tests/test_puzzle_solver_phone.py`, `tests/test_puzzle_solver_zoom.py` — the existing geometry cells)

## Worktree notes
- **[Gate, 2026-11-12]** Player set: 1398 passed, 3 red, all the pill's first draft: a 1 px BORDER on the group made the compact toolbar 2 px taller and moved the board (`TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted[600x844]` 97 != 95, `TestSolverPhone_MirroredGutterSticks`, and the base-css FROZEN table). The edge is now a `box-shadow` ring, which takes no room: the two geometry cells pass unchanged. FROZEN re-recorded for the zoom buttons' intended look (square corners, no own border), green against the real Bootstrap and the project stylesheet. Re-run after the fix: clues, phone, zoom, base-css and design tokens, 163 passed.
