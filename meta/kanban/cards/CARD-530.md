# CARD-530: The browser-family registry records the three tests Player QA v3 renamed, and can retire a recorded test whose claim the owner inverted

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/530-qa-v3-registry
**Worktree:** ../PythonProject4-card-530
**Source:** found 2026-11-23 by CARD-527's implementation and review (F-005): main has been red since the Player QA v3 merge (8f799d5b), which renamed three browser tests without updating tests/test_browser_fixture_scope.py's registry. Added to wave 14 because it reds every merge gate.
**Idea:** —
**Wave:** 93
**Created wave:** 93
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_browser_fixture_scope.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-23T09:07Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured` fails on main. Commit 9fd47469 (Player QA v3, the owner's own QA round, no card) changed three browser tests:

- In `tests/test_puzzle_solver_clues.py`, `TestSolverClues_RepeatedLengthDoesNotCircle` (two tests, both registered in `ADDED_SINCE_BEFORE` by CARD-213) became `TestSolverClues_RepeatedLengthCirclesWhereOnlyOneFits`. `test_the_repeated_value_circles_nothing` became `test_the_repeated_value_circles_the_one_that_fits`, an inverted claim: the owner wanted the one 2 that fits circled. `test_the_same_marks_circle_a_two_that_occurs_once` moved class unchanged.
- In `tests/test_puzzle_solver_zoom.py`, `TestSolverZoom_PinchOnAClueBoxIsNotTheBoardsZoom::test_a_pinch_starting_on_a_column_clue_box_is_left_to_the_browser[chromium]` became `TestSolverZoom_PinchOnAClueBoxIsTheBoardsZoom::test_a_pinch_starting_on_a_column_clue_box_zooms_the_board[chromium]`, also an inverted claim (CARD-195's test).

The two clue tests can follow the CARD-435 precedent: strike their old `ADDED_SINCE_BEFORE` entries and add the new ids. The zoom test cannot. It is in CARD-217's recorded artefact, which "must not disappear", and `RENAMED_SINCE_BEFORE` admits only a change inside a node id's `[...]`. The registry has no way to retire a recorded test whose claim the owner inverted. Every entry also needs a `CARD-\d+` attribution, and QA v3 had no card. This card is that attribution.

## What to implement

1. Re-verify on main: the family-collection test fails with exactly these three ids added and these three removed.
2. Strike the two CARD-213 clue entries and add the two new ids to `ADDED_SINCE_BEFORE`, attributed to CARD-530. The why line names Player QA v3 (9fd47469) and what each test now claims, read from the test, not this card.
3. Add the narrowest mechanism that lets a CARD-217-recorded id be retired together with its replacement. For example, a table of retirements `old id -> (card, replacement id, why)`, where the replacement must be collected and must be in `ADDED_SINCE_BEFORE`, and the old id must be in the artefact and not collected. It must not let a card delete a recorded browser test with no replacement: follow how `_rename_problems` refuses a rename whose two sides are different tests, and drive the refusals the same way `test_the_rename_table_refuses_what_it_claims_to` does. Retire the zoom id through it.

## Acceptance criteria

* **AC-1**: `test_the_family_collects_exactly_what_card_217_measured` passes on this branch. The count assertion's derivation includes the retirement table.
* **AC-2**: the retirement table refuses each of the following, one case per refusal, each asserted against its own message: an old id that is not in the artefact, an old id that is still collected, a replacement that is not collected or not in `ADDED_SINCE_BEFORE`, and an attribution that is not `CARD-\d+`. Control: deleting each refusal turns its own case red.
* **AC-3**: deleting a recorded browser test with no retirement entry still reds the family test. Show it with a control.
* **AC-4**: report the net test count; extend existing tests where they fit.

## Guardrails

* **G-1**: tests-only; the three tests themselves and src/ are untouched.
* **G-2**: do not touch CARD-527's or CARD-528's files beyond this one test file. CARD-527 also edits tests/test_browser_fixture_scope.py, in other regions, so keep the diff to the registry tables and their helpers and tests.

## Worktree notes
