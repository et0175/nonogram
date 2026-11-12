# CARD-430: The compact zoom is one joined control: a pill on a phone, a block across the landscape strip

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.25d)
<!-- Basis: CSS only, in admin.css's compact and landscape blocks; the player's zoom tests are the check. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/430-zoom-pill
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-430
**Source:** owner 2026-11-12 (project thread): "can you propose a different design for a zoom button when it's small?"; of three mockups chose "option A" (a joined pill), "but in the landscape mode we have 2 columns of buttons, probably your long side fits better".
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-428, CARD-429
**Touches:** src/nonogram/admin/static/admin.css
**Review score:** —
**Started:** 2026-11-12T11:05Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

In the compact toolbar (`max-width: 600px` or `max-height: 500px`) the zoom group's three members (minus, plus, the readout that is also the Fit button) become one bordered control divided by hairlines: a rounded pill in a row. In the landscape strip (two 44 px columns), where a one-row pill would leave each member about 30 px, it is one rounded block spanning both columns: minus and plus side by side, the readout across the row below (CARD-428's arrangement, now joined). The DOM order is unchanged (CARD-429's focus order), every member keeps its 44 px target, and a focus ring is drawn inside the clip.

## Acceptance criteria

- **AC-1** *Given* the compact toolbar, *then* the zoom group is one bordered control with no gap between its members, each at least 44 px; in the landscape strip, minus and plus share a row and the readout spans the row below, inside the same border. (test: `tests/test_puzzle_solver_phone.py`, `tests/test_puzzle_solver_zoom.py` — the existing geometry cells)

## Worktree notes
