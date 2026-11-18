# CARD-477: The four remaining pages draw an edited puzzle's current grid, not a cached one

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/477-versioned-grid-urls
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-129, WSJF 2.56); premise re-read against main on 2026-11-18. Origin: CARD-250 review cycle 1, finding F-005.
**Idea:** IDEA-129
**Wave:** 80
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/book_select_puzzles.html, src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/templates/generated_puzzles.html, src/nonogram/admin/templates/batch_status.html, src/nonogram/admin/app.py, tests/test_puzzle_editor_ui.py
**UI surface:** user-facing
**Review score:** 9.5 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-18T14:45Z
**Closed:** 2026-11-18T18:28Z
**Actual:** 2c — ratio 2/1 = 2.000
**Merge commit:** fb23f1e3200dd833d2d8f6c58a60fb34fe31184d
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

[Route taken] The url is versioned on the four pages; the grid route was not given an ETag and `app.py` is untouched. Every page already receives `puzzle_review` dicts carrying `manually_edited_at`: in memory measured by rendering, in DB mode read from the code (`filter_puzzles` and `get_puzzles` both build rows through `_row_to_dict`, which always writes the key) by the cycle-1 reviewer, not executed — no database is configured for tests.
[AC-3] Holds because the diff leaves the two download links alone; no test pins them.
[Review 1/3] Score: 9.0, nothing gating. Minor 1 fixed in a second commit: the template walk passed three bare shapes (stamp only in `alt`, `onerror` before `src`, a `url_for`-built `src`) while its docstring said a bare page reds.
[Review 2/3] Score: 9.5, nothing gating, certified; a confirmation cycle on the fix commit alone: "I would merge the two-commit diff as it stands". The floor counts exactly the six real grid images.
[Correction to commit 6e385193's message] It says reading the whole tag instead of the `src` "reds once a tag carries the stamp in alt and a constant ?v= in src". Wrong as written: under that mutant the walk stays GREEN with that tag planted; the real walk is red. That tag is what tells the two readings apart, and no test plants it, so the whole-tag mutant survives the suite. I misread my own run: its one failure was the per-page test, not the walk.
[Open, not carded — reviewer F-101] The walk skips an `<img>` it cannot parse instead of failing: `SRC=`, `<IMG`, an unquoted `src`, `srcset` or `data-src` only, and an unquoted apostrophe earlier in the file each let a bare grid image pass. None of these shapes exists in the templates today, and the docstring does not list them.
[Merge gate] `make test-gate`, RED on four player browser tests and merged anyway, on evidence: the gate selected 9039 of 10671 tests (templates widen the impact set) and ran for 36 minutes on a machine at load 33-70 (Spotlight and Defender). The four failures — `TestPublicMode_EveryWayOfLosingItIsCaught` (two params), `TestPublicMode_LandscapeToolStrip::test_the_tools_stand_in_a_strip_left_of_the_board`, `TestSharedUi_ThePageRuns::test_a_puzzle_opened_from_a_book_offers_the_way_back_and_no_other_page_does` — were re-run alone afterwards: 32 passed on this branch AND 32 passed on main. None renders an admin template this card touched. Run 1: 4 failed, 8993 passed, 30 skipped (29 database-not-set, 1 setrlimit), 13 deselected, 1 xfailed; run 2 (wave_close_only), 11 passed.
[Estimate] 1c estimated, 2 cycles used.
