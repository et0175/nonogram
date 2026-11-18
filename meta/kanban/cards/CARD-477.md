# CARD-477: The four remaining pages draw an edited puzzle's current grid, not a cached one

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-129, WSJF 2.56); premise re-read against main on 2026-11-18. Origin: CARD-250 review cycle 1, finding F-005.
**Idea:** IDEA-129
**Wave:** —
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/book_select_puzzles.html, src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/templates/generated_puzzles.html, src/nonogram/admin/templates/batch_status.html, src/nonogram/admin/app.py, tests/test_puzzle_editor_ui.py
**UI surface:** user-facing
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

After a hand edit, the puzzle list and the detail modal show the new grid because CARD-250 versioned their image URL with `manually_edited_at`. Four other pages still request the bare `/api/puzzle/<id>/grid` and so can redraw the pre-edit grid from the browser cache: book selection, book arrangement, generated puzzles and batch status. The owner picks puzzles for a book on two of them.

## What to implement

Version the grid URL on the four pages the way `_puzzle_table.html` does. If a page's puzzle objects do not carry `manually_edited_at`, carry it there rather than inventing a second key. Only if a surface genuinely cannot know the edit time, give `api_puzzle_grid_from_puzzle` a validator (ETag from the edit time) instead — say in the notes which route was taken and why.

## Acceptance criteria

* **AC-1**: for an edited puzzle, each of the four pages renders a grid URL that differs from the one it rendered before the edit; for an unedited puzzle the URL is unchanged.
* **AC-2**: no template under `src/nonogram/admin/templates/` renders an unversioned `<img>` grid URL for an object that has an edit time — derived by walking the templates, so a fifth page cannot be added bare.
* **AC-3**: the two download links (`/grid/download`, `/grid/download-pdf`) are unchanged.
* **AC-4**: tests extend whichever cells already assert the versioned list URL (a `?v=` assertion exists in `tests/test_puzzle_editor_ui.py`; not read further when this card was cut); net test count reported.

## Guardrails

* **G-1**: the list row and the detail modal (CARD-250) keep their current URLs byte for byte.
* **G-2**: no change to what the grid route draws.

## Worktree notes

—
