# CARD-532: Test prose stops stating the retired 4.8 mm cell floor as current

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap wave 15, cut 2026-11-23 on the owner's "pick the next no-decision wave from the backlog". IDEA-173.
**Idea:** IDEA-173
**Wave:** 94
**Created wave:** 94
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/ (docstrings and comments in the files listed below)
**UI surface:** —
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

NFR-008's amendment of 2026-10-17 lowered the printed-cell floor from 4.8 mm to 4.75 mm (`book_manager.py`'s floor comment, CARD-121; `MIN_CELL_MM`). Re-checked on main at the cut: `git grep -n "4.8 mm" -- tests` gives 15 lines in 13 files. Some are correct history ("the retired 4.8 mm floor", "lowered the floor from 4.8 mm to 4.75 mm"). Others state 4.8 mm as the floor in force, for example `test_book_ready_gate.py` ("against the 4.8 mm floor (INV-006)"), `test_layout_page_spec.py` ("above the 4.8 mm floor") and `test_book_published_confirm.py` ("misses the 4.8 mm floor"). A reader then reasons from the wrong number.

## What to implement

1. Classify every `4.8 mm` line in `tests/` as history (true as written) or a present-tense claim. Record the table in `## Worktree notes`.
2. Rewrite each present-tense claim to name the floor in force. Name it by its source (`MIN_CELL_MM` / INV-006), or say 4.75 mm, whichever the surrounding prose already does. Leave history lines alone.
3. Where the prose describes a fixture's relation to the floor ("misses", "clears", "far above"), measure that fixture's printed cell against 4.75 mm and record the figure. If the claim is false at 4.75 mm (for example, a "misses the floor" fixture printing between 4.75 and 4.8 mm), stop and report it rather than fix it. That would be a test that no longer tests what it says, and it needs its own card.
4. Prose only: no assertion, fixture or test name changes. Net tests 0.

## Acceptance criteria

- AC-1: every remaining `4.8 mm` in `tests/` is history, and the worktree notes' table shows it.
- AC-2: every fixture-versus-floor sentence touched has its measured cell size recorded, and is true at 4.75 mm.
- AC-3: `git diff` touches comments and docstrings only. The touched files pass, and the collected test ids are unchanged.

## Worktree notes
