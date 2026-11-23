# CARD-529: test_book_pdf_band.py's glyph cache stops keeping whole uncropped arrays alive

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/529-glyph-cache-copy
**Worktree:** ../PythonProject4-card-529
**Source:** roadmap wave 14, cut 2026-11-23 on the owner's "pick a no-decision wave from the backlog". IDEA-212 (CARD-218 review cycle 2 finding).
**Idea:** IDEA-212
**Wave:** 93
**Created wave:** 93
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_pdf_band.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-23T09:35Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

In `tests/test_book_pdf_band.py`, `_set_once` is an unbounded `@lru_cache`. It returns `_cropped(...)`, a numpy slice: a view that keeps the whole uncropped base array alive. Measured on 2026-10-24 at CARD-218 review cycle 2: the cache held 666 entries and 24.4 MB for the rest of every session that touched the file. The backlog item's title says about 111 MB; the body's figure is 24.4 MB, and neither figure has been re-measured. The code shape was re-confirmed on 2026-11-18. The file already has a retention control naming these caches.

## What to implement

1. Re-measure on main: run the file alone and size `_set_once`'s retained memory by the bases its arrays keep alive (numpy `nbytes` of each `.base`), and state the figure.
2. Make the cache keep only what it returns, for example a `.copy()` of the cropped region, so the uncropped base can be freed. Keep the cache itself, since its speed is why it exists.
3. Re-measure retained bytes and the file's run time, before and after.

## Acceptance criteria

* **AC-1**: after the change, every cached array owns its data (no `.base`, or a base no larger than itself). Put that check inside the file's existing retention control. Control: removing the copy turns it red.
* **AC-2**: retained bytes before and after are stated, measured the same way both times. The file's run time does not grow by more than 5%.
* **AC-3**: no test result changes: the same tests pass before and after, and the net test count is 0.

## Guardrails

* **G-1**: tests-only card; nothing under src/ changes.

## Worktree notes
