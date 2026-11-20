# CARD-507: A long solved-puzzle name no longer moves the desktop board: the banner text takes the compact two-line --text-xs clamp

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/507-solved-name-clamp
**Worktree:** —
**Source:** roadmap wave 7 (cut 2026-11-20 on the owner's "go with option 2, start wave 7"). IDEA-218, owner decision 2026-11-20: option 2 of five (ellipsis, two-line --text-xs clamp, reserved line, wider tools box, leave it).
**Idea:** IDEA-218
**Wave:** 86
**Created wave:** 86
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_*.py
**UI surface:** puzzle player (admin, and the public player built from the same files): the solved banner at desktop widths
**Review score:** —
**Blocked by:** —

## Why this card exists

Measured by CARD-506 and its review (2026-11-20): the solved banner wraps inside the 13rem tools box and pushes the board down at desktop widths. 10-12 characters 0 px; 14-24 characters +12.8 px; 26 without spaces +62.4 px; 50-60 +62.4 px; 100 +136.8 px; at 390 px wide, 0 for every length. The compact (phone) rule already sets the banner's text span to `--text-xs`, `--leading-tight`, clamped to two lines (`.player-solved > span` inside the compact media block of admin.css). The owner chose to apply that same treatment at desktop widths.

## What to implement

1. Re-measure the shift on this branch's base first (the lengths above, at 1440x900 and 1100x700, 15x15 and 30x30 boards), in a browser run.
2. Apply the compact rule's text treatment (`--text-xs`, `--leading-tight`, two-line `-webkit-line-clamp`, overflow hidden) to the banner text at every width. Prefer moving the declaration out of the media block over duplicating it. Keep the phone layout exactly as it is.
3. The full name stays in the DOM (the clamp is visual only), so the banner's accessible name and the text a screen reader announces are unchanged.

## Acceptance criteria

* **AC-1**: at 1440x900 and 1100x700, for solved names of 10, 24, 26 (no spaces), 60 and 100 characters, the board's top edge moves 0 px between the unsolved and solved states (or by no more than the box's existing short-name height, stated with its measured figure).
* **AC-2**: the banner text never shows more than two lines at any width; a long name is cut, not wrapped further.
* **AC-3**: at 390x844 every computed value of the banner and the board is unchanged against the base (a before/after measurement).
* **AC-4**: the banner's accessible text still contains the full name.
* **AC-5**: the board-shift assertion is folded into an existing solved-banner test (net test count 0, or +1 at most if no existing test can carry it; report it). Its control: remove the new rule and the test reds with the measured shift.

## Guardrails

* **G-1**: the player files are the public player's source: the public player test set (tests/test_player_*.py, tests/test_public_*.py) runs green. The orchestrator publishes after merge only on the owner's say.
* **G-2**: no other visible change. Short names (that fit on one line today) render at the new text size; state that change and its measured size in the notes, because the owner sees it.

## Worktree notes
