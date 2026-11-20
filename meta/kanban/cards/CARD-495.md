# CARD-495: A stored "guess" row is Hard in the database filter too; the arrange row fits a phone

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/495-guess-filter-and-phone-buttons
**Worktree:** ../PythonProject4-card-495
**Source:** owner 2026-11-20 ("yes, fix both"), on CARD-494 review F-005 and F-007.
**Idea:** —
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py, tests/test_admin_tier_surfaces.py, src/nonogram/admin/static/admin.css, tests/test_book_arrange_play_link.py
**UI surface:** admin puzzle filter (tier); admin book arrange page on a phone
**Review score:** —
**Started:** 2026-11-20T07:48Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **CARD-494 F-005.** `filter_puzzles`' database branch matched only the wanted tier's value and label, exactly; the in-memory branch reads every row through `tier_of_record`, which reads the retired "guess" as Hard (and any case or surrounding space). So on the live panel (database mode) a stored "guess" row appeared under no tier filter. Measured on sqlite 2026-11-20: Hard returned hard and Hard rows, not guess.
2. **CARD-494 F-007.** On a 390 px phone the arrange page's move and delete buttons ended 44 px past the puzzle card and the page scrolled sideways (426 px in 390); the 120 px preview lay over the info column. Measured 2026-11-20 with the panel's own stylesheets and Bootstrap.

## What to implement

1. The database branch matches every stored spelling `tier_of_record` reads as the wanted tier, compared trimmed and lower-cased (as the tier sort already does), derived from `_TIER_RANK_BY_SPELLING`, so the two branches cannot drift.
2. On a phone the arrange row stays inside its card at 320-820 px: preview at its 80 px column, the middle column may shrink, the info line wraps; at 360 px and under the title takes its own row.

## Acceptance criteria

* **AC-1**: the same rows ("guess", "Guess", " GUESS ", "hard", "HARD", "easy") filtered for Hard and Easy give the same ids in the in-memory store and a SQLite-backed one; control: main's database branch reds it.
* **AC-2**: at the phone viewport the row's title and actions end inside the row and the page does not scroll sideways; control: main's admin.css reds it.
* **AC-3**: net test count 0.

## Guardrails

* **G-1**: a requested value that names no tier keeps the exact comparison (no widening on a typo).
* **G-2**: desktop arrange layout unchanged (the CSS sits in the existing max-width 820 px rule and a new 360 px rule).

## Worktree notes
