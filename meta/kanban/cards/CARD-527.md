# CARD-527: Every browser-test file must declare its page isolation, not only the test_puzzle_solver_* files

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/527-page-isolation-all-browser-files
**Worktree:** ../PythonProject4-card-527
**Source:** roadmap wave 14, cut 2026-11-23 on the owner's "pick a no-decision wave from the backlog". IDEA-181 (CARD-246 finding).
**Idea:** IDEA-181
**Wave:** 93
**Created wave:** 93
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_browser_fixture_scope.py; the browser-test files it newly covers, only if one needs a declaration
**UI surface:** —
**Review score:** —
**Started:** 2026-11-23T08:10Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-235's `PAGE_ISOLATION` table in `tests/test_browser_fixture_scope.py` makes each browser-test file say how it isolates its page between tests, so a test cannot quietly depend on another test's page state. Its file list comes from the glob `tests/test_puzzle_solver_*.py`, so a browser-test file under any other name is never asked. CARD-246 (`tests/test_puzzle_editor_ui.py`) declared its isolation locally, by hand. The backlog triage on 2026-11-18 counted about 13 browser files outside the glob, by a text search that was not confirmed by collection.

## What to implement

1. Re-verify on main: derive the set of browser-test files the way the suite itself identifies them (the browser marker or fixture, resolved by collection or `ast`, not by text search), and list which fall outside the glob.
2. Make the isolation guard cover that whole set, so a new browser-test file under any name fails the suite until it declares its isolation. Each file that is newly covered gets its declaration, using CARD-235's existing categories, with the reason checked against how the file actually sets up its page.
3. Fold CARD-246's local declaration into the shared table if that is now redundant (one source, not two).

## Acceptance criteria

* **AC-1**: the guard's file set is derived from the suite's own browser-test identification, not from a filename glob. A test proves that the set equals the files collection marks as browser tests. Control: a mutant that restores the glob turns that test red.
* **AC-2**: every browser-test file has exactly one declaration, and a declaration for a file that no longer exists is refused. Controls: deleting one newly added declaration turns a named test red, and so does adding one for a missing file.
* **AC-3**: each new declaration's category matches the file's actual page setup, judged per file in the notes with the fixture each file uses.
* **AC-4**: no browser test's behaviour changes, so no fixture scope moves. Report the net test count; the owner's budget is to extend existing tests.

## Guardrails

* **G-1**: tests-only card; nothing under src/ changes.
* **G-2**: do not change any fixture scope; if a file's isolation looks wrong, record it in the notes as a finding, do not fix it here.

## Worktree notes
