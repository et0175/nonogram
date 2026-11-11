# CARD-422: A puzzle opened from the Christmas book wears its garland and green heading too

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: CARD-421's drawing code moved into a shared module and stylesheet, two published files added, the play loader attaches them for a Christmas book's puzzle, the existing Christmas cell extended. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/422-puzzle-decor
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-422
**Source:** owner 2026-11-11, after CARD-421's landing: "Looks good. Please apply it to individual puzzles also (they now appear without new theme)" — a puzzle opened from the book carried only CARD-420's colour tokens (cream ground, gold-edged buttons), which read as no theme.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-420, CARD-421
**Touches:** player/decor.js, player/decor.css, player/pages.js, player/player.css, player/book.html, player/assemble.py, tests/test_book_landing_page.py, tests/test_public_player.py
**Review score:** —
**Started:** 2026-11-11T09:30Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

1. **One home for the decorations.** CARD-421's garland and snow move out of `pages.js` into `player/decor.js` (`decorate(panels)`) and their placement into `player/decor.css`, both published (`PLAYER_FILES`). The landing imports and links them as before.
2. **The puzzle.** When the play loader applies a Christmas book's theme, it attaches `/decor.css` and calls `decorate()` with no panels: the garland across the top and the heading in pine. The board is not decorated. A puzzle outside a Christmas book links no stylesheet beyond the admin's own, as before.

## Acceptance criteria

- **AC-1** *Given* `/play/<key>?book=<slug>` of a Christmas book holding the key, *then* one garland hangs at the top, the heading is pine, `/decor.css` is attached, and the board carries no decoration; *given* any other way in, *then* no garland and no `/decor.css`. (test: `tests/test_book_landing_page.py::test_a_christmas_book_dresses_its_landing_and_the_puzzles_opened_from_it`)

## Worktree notes

- **[Implementation, 2026-11-11]** `decor.css` is attached by the loader rather than linked in the page's head: `TestSharedUi_ThePageRuns` holds an ordinary puzzle to the admin's three stylesheets, and that stays true. The loader's dynamic imports are now `/decor.js` and `/solver.js` (`test_the_runtime_dependency_baseline_is_untouched` re-pointed). Plant: the loader never calls `decorate()` -> the garland arm red (`0 == 1`). Also fixed on the way: `docs/deploy/player.md` backticked `--no-reload`, the same red as CARD-420's `--player-wave`.
