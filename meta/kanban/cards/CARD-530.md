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
**Review score:** 8.5 (cycle 1/3)
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

### 2026-11-23 implementation (CARD-530)

**Premise, re-verified before any change** (a script over `_collection_drift(collected, _baseline_node_ids())`): exactly three added, three removed. Removed: the two `TestSolverClues_RepeatedLengthDoesNotCircle` ids (in `ADDED_SINCE_BEFORE`, CARD-213, not in the artefact) and the zoom id `TestSolverZoom_PinchOnAClueBoxIsNotTheBoardsZoom::test_a_pinch_starting_on_a_column_clue_box_is_left_to_the_browser[chromium]` (in CARD-217's artefact, not allowlisted). The change is 9fd47469 (merged by 8f799d5b). The old zoom test came from 49aec834, whose file header is CARD-195; its class docstring said AC-8.

**What changed** (tests/test_browser_fixture_scope.py only):
- `ADDED_SINCE_BEFORE`: the two CARD-213 clue entries struck, with a comment naming them, as CARD-435 did. The two `TestSolverClues_RepeatedLengthCirclesWhereOnlyOneFits` ids and the zoom replacement `TestSolverZoom_PinchOnAClueBoxIsTheBoardsZoom::test_a_pinch_starting_on_a_column_clue_box_zooms_the_board[chromium]` added, attributed to CARD-530. Each reason was read from the test body and docstring.
- New `RETIRED_SINCE_BEFORE` (`old id -> (card, replacement id, reason)`) with the one zoom entry. New `_retirement_problems(table, collected)` with nine refusals: entry shape; old id not in CARD-217's record; old id still collected; replacement not collected; replacement with no `ADDED_SINCE_BEFORE` entry; replacement carried by another card's allowlist entry; one replacement shared by two old ids; attribution not `CARD-\d+`; a reason under 8 words. The card's AC-2 lists five of these. The other four close holes in the same rule: a recorded test is retired only together with a replacement of its own.
- `_baseline_node_ids` takes `retirements` and derives `(recorded after renames - retired) | allowlist`.
- `test_the_family_collects_exactly_what_card_217_measured`: it now asserts `_retirement_problems(RETIRED_SINCE_BEFORE, ids) == []` against the real collection. The count message reads `recorded - retired + allowlisted` (AC-1), and the "tests removed" message names the retirement table.
- `test_the_baseline_goes_red_in_both_directions`: claim 3 now also loops over retirement tables `({}, RETIRED_SINCE_BEFORE)`. `dropped` is now taken from `_recorded_node_ids()` minus the retired ids, not from the derivation under test. A new assert says the real table lets through exactly the ids it names. Claim 4's size check passes `retirements={}`, keeping its original claim that renames are 1 -> 1.
- `test_a_recorded_rename_is_a_move_and_an_unrecorded_one_goes_red`: it compares against the raw artefact, so its three derivations pass `retirements={}`.
- New `test_the_retirement_table_refuses_what_it_claims_to`: one broken table or tree per refusal, each asserted by its own message, with the fragment-distinct and no-nesting checks copied from the rename control. The last assert is the real table against its derived tree.

**Controls** (mutation applied to a pristine copy, named test run, file restored; `cmp` showed it byte-identical afterwards). All 18 went red at the named assert:
- Each of the 9 refusals deleted (its `problems.append` made a no-op): `test_the_retirement_table_refuses_what_it_claims_to` red at `assert len(hits) == 1` for that refusal's own case (9/9).
- A refusal that refuses the real table (`if old in collected` -> `if True`): red at `assert _retirement_problems(RETIRED_SINCE_BEFORE, tree) == []`.
- Two cases given one fragment: red at `assert len(set(fragments)) == len(fragments)`. One fragment nested in another: red at `assert nested == []`.
- `- set(retired)` deleted from `_baseline_node_ids`: baseline control red at the real-retirement `_collection_drift` assert. The family test is red at `assert drift["removed"] == []` (tests removed: the zoom id).
- A retirement that retires every recorded id: baseline control red at claim 3's loop assert (`removed: [dropped]`).
- The real table not consulted by default (`retired = {} if retirements is None`): baseline control red at the real-retirement assert.
- The zoom entry's replacement pointed at another card's allowlisted test: the drift stays clean, but the family test is red at `assert _retirement_problems(RETIRED_SINCE_BEFORE, ids) == []`.
- AC-3: the zoom retirement entry deleted, so a recorded test is gone with no entry. The family test is red at `assert drift["removed"] == []` with "tests removed: [...left_to_the_browser[chromium]]".

**Gate** (unarmed, `-o addopts= -rfs`):
- tests/test_browser_fixture_scope.py whole: 34 passed, 0 failed, 0 skipped (86 s).
- Neighbours: the three registered tests (`TestSolverClues_RepeatedLengthCirclesWhereOnlyOneFits`, `TestSolverZoom_PinchOnAClueBoxIsTheBoardsZoom`): 3 passed.
- tests/test_kanban_review_record.py after the card edit: 71 passed, 0 skipped.

**Net test count**: 10695 before, 10696 after (+1, `test_the_retirement_table_refuses_what_it_claims_to`). Everything else extends existing tests.

[Review 1/3] Score: 8.5, one gating finding, not certified. Re-derived: tests/test_browser_fixture_scope.py 34 passed, 0 skipped, on this branch and merged with CARD-527 in a scratch clone (no conflicts); 5 of 18 controls red at their asserts; the reason lines match what each test asserts; the same-card and one-replacement rules hold; no existing claim weakened. F-001 (Important): `_retirement_problems` links the old id and the replacement only by the card name, so a card can retire a recorded test in any file by naming one of its own allowlisted tests (measured: a page.py test retired against a clue test, drift empty, every guard green); the table's comment overclaims. F-002 (medium): a comment in `test_the_baseline_goes_red_in_both_directions` still describes `before` as the record after renames and claim 4 as pinning it. F-003 (low): one clue reason says the page is checked with rule E off; only the Python rule is. F-004 (info): a recorded test that was renamed cannot be retired; fails closed.

### Fix round 1 (review 1)

- **F-001**: `_retirement_problems` gains a tenth refusal. The old id and its replacement must share the file part before `::` ("... lives in a different file"). The zoom entry satisfies it.
  - `test_the_retirement_table_refuses_what_it_claims_to` gains the case "another file's replacement". It names the first id CARD-530 allowlisted in a file other than the zoom file.
  - The `RETIRED_SINCE_BEFORE` comment is narrowed to what is enforced. It now also says what is not enforced: nothing checks that the replacement tests the same thing, and within one file a card can still name any test it allowlisted there.
  - Before the fix, the reviewer's /private/tmp/claude-501/card530-review/abuse.py printed `problems: []`. After it, the script prints the "lives in a different file" problem. Its `drift` line stays empty, because the drift does not consult the refusals.
- **F-002**: the comment above `before = _baseline_node_ids({})` now says `before` is the recorded family after renames and the real retirements, so artefact size minus `len(RETIRED_SINCE_BEFORE)`. It says claim 4 pins the retirement-free derivation to the artefact's size, and claim 3 pins what the retirements take out.
- **F-003**: the reason for `test_the_repeated_value_circles_the_one_that_fits` now says that the test's independent Python rule, with rule E off, circles nothing on the same marks. It no longer makes that claim about the page.
- **F-004**: no change. Retiring a renamed recorded test fails closed: the renamed target is refused as "not in CARD-217's record", and the raw source subtracts nothing, so the family goes red.

**Controls, round 1** (pristine copies restored; `cmp` and `git diff --stat` were clean afterwards):
- Same-file refusal deleted: `test_the_retirement_table_refuses_what_it_claims_to` is red at `assert len(hits) == 1` ("another file's replacement: 'lives in a different file' matched 0 of []").
- Reviewer's abuse replayed against the real collection. `TestPlayerAssets::test_every_admin_asset_ships_in_the_wheel` was removed from tests/test_puzzle_solver_page.py for the run, and its retirement entry was added with the CARD-530 clue test as the replacement. `test_the_family_collects_exactly_what_card_217_measured` is red at `assert _retirement_problems(RETIRED_SINCE_BEFORE, ids) == []`. The same abuse with the refusal also deleted passes, so the new refusal is the only thing that catches it.
- The 18 round-0 controls, re-run on the fixed file: 18/18 red at the same asserts.

**Gate, round 1** (unarmed, `-o addopts= -rfs`):
- tests/test_browser_fixture_scope.py whole: 34 passed, 0 failed, 0 skipped (100 s).
- The three registered tests: 3 passed.
- tests/test_kanban_review_record.py: see the hand-back.

**Net test count**: 10696 (round 0 was also 10696; the new case is inside an existing test). Against the pre-card count of 10695 the card is +1.
