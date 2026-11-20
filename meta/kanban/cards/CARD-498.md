# CARD-498: The registry's honest-dead check refs: each one points at a real test or says honestly that none checks it

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/498-honest-dead-refs
**Worktree:** ../PythonProject4-card-498
**Source:** roadmap wave 5 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-216, WSJF 3.08 (partly; the rescore counted 11 as a floor).
**Idea:** IDEA-216
**Wave:** 84
**Created wave:** 84
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, meta/architecture/trace.yml, tests/test_check_ref_resolution.py
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-20T09:21Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/test_check_ref_resolution.py` pins a class it calls **honest-dead**: registry check refs (requirements.yml `test:`/`check:`/`tests:`) that both of its resolvers agree name a test existing nowhere. On main 2026-11-20 the pin is `HONEST_DEAD = (11, …)`. Each such ref reads as "mechanically checked" while nothing checks it (memory: ADR check refs must be honest).

## What to implement

For each of the 11 (list them by the module's own helpers, never by text search):

1. If a real test verifies the AC's claim (find it by `ast`, read it, and confirm it can fail when the claim is broken), re-point the ref to it.
2. If none does, either write the narrowest test (only where cheap and the AC is mandatory) or mark the ref honestly in the registry's existing convention for an unchecked criterion (find how the registry already says "not mechanically checked", e.g. a review-lens marker), never by deleting the AC.
3. Re-derive the module's frozen classes as sets (HONEST_DEAD, and every class an edit moves), explain each delta, and keep the module's pin rules.

## Acceptance criteria

* **AC-1**: HONEST_DEAD is 0, or every remaining member is listed in the notes with why it stays and how the registry now says so.
* **AC-2**: every re-pointed ref's test is shown able to fail on the AC's claim (one mutant or a reading of its assertion, recorded per ref).
* **AC-3**: the forge_1 validator reports no new finding (compare `--phase all --format json` before and after); tests/test_check_ref_resolution.py green with re-derived pins.
* **AC-4**: net test count at most +2.

## Guardrails

* **G-1**: no AC is deleted or weakened to make a ref resolve.
* **G-2**: a synced review YAML must not be what makes a ref resolve (memory: review YAMLs revive dead check refs); confirm by `ast` def lines.

## Worktree notes

### Implementation round 0 (2026-11-20)

**Premise, re-verified.** `_verdicts()` of tests/test_check_ref_resolution.py on the unchanged tree reproduced all nine pins; the honest-dead class was 11 (predicate `not loose and not strict`), by declaration site: four on FR-001's trace.yml row, five on NFR-005's trace.yml row, two (AC-291, AC-292) in requirements.yml plus FR-042's trace.yml row. Not one has a def/class line (independent `ast` index of tests/ and src/).

**Per ref** (refs named here by site and old spelling; this file is Markdown, outside both resolvers):

| ref (old) | AC | verdict | new ref / marker | evidence |
|---|---|---|---|---|
| 4x TestGenerateRandom_* (FR-001 trace row) | AC-001..AC-004 (superseded) | retired criteria; AC-002 false at MAX_SIZE=30 | delisted, `tests: []`; names kept as prose in the row's notes | owner's 2026-10-31 carrier decision already dropped the same four from requirements.yml; not re-pointed (CARD-317's reason) |
| TestLayout_10x10CellMeasures9mm | NFR-005 AC-080 | claim live | `test_a_small_grid_takes_the_comfort_cap` | M1 (10-cell value 9.0 -> 8.0): `assert 7.9586... == 9.0 ± 0.2` |
| TestLayout_30x30CellMeasures6point5mm | NFR-005 (pre-amendment) | claim FALSE today; successor AC-081 | `test_a_large_grid_is_page_fit_bound_not_cap_bound` (AC-081's test) | M2 (cap as floor, `max(cap, page_fit)`): `assert (3324 - (2 * 142)) <= 2197`. Reading: its `< 6.5` assert cannot fail on a 30x30 -- the cap truncates to 76 px = 6.435 mm; the fit bound is what reds |
| TestLayout_NonSquareGridUsesLargerDimension | AC-082 | claim live | `test_the_cap_comes_from_the_larger_dimension_regardless_of_orientation` | M3 (`larger_dimension = columns`): tall case `assert 8.9746... == 8.6 ± 0.2` |
| TestLayout_InterpolatesBetweenTabulatedCellSizes | AC-083 | claim live | `test_the_cap_interpolates_between_the_chosen_cell_sizes` | M4 (curve stepped): `assert 8.9746... == 8.4 ± 0.2` |
| PropertyTest_Layout_CellSizeNonIncreasingInLargerDimension | NFR-005 (pre-amendment) | claim FALSE today; successor AC-104 | `test_the_same_larger_dimension_does_not_guarantee_the_same_cell_size` (AC-104's test) | M5 (cell = cap alone): `assert ('portrait', 'portrait') == ('landscape', 'portrait')` -- reds at its orientation assert, before the 5.00/4.91 asserts |
| TestBookAnswerKey_HeadingOnlyOnLevelFirstPage | FR-042 AC-291 | TRUE today, unwitnessed at its boundary | `test:` dropped + comment; delisted from FR-042 row | rendered 8 easy + 1 medium: pages 17/18/19 heads EASY/EASY/MEDIUM. Nearest test `test_the_answer_number_is_the_number_printed_on_the_puzzle` stays GREEN under M6 (a level's later page loses its level), while the render under M6 shows page 18 `['SOLUTIONS', 'PUZZLES 5–8']` -- so a re-point would be false |
| TestBookAnswerKey_SolutionsDividerPrecedesAnswerKey | FR-042 AC-292 | content clause FALSE today | `test:` dropped + comment; delisted from FR-042 row | run: `divider_page(SOLUTIONS_SLOT, ...)` == `create_solutions_opener` (eyebrow, "Solutions", blurb, folio) and != word-only `create_divider_page`. Position half held by `test_the_interior_is_that_section_between_the_guide_and_the_key` (named in the comment, not re-pointed) |

The five new trace refs are `def` lines in tests/test_export_image.py found by `ast` (one each, no other def contains them), collected and run by node id; none is resolved by anything under meta/review/ (the validator domain hit is their own module). Neither AC-291 nor AC-292 is invariant-bound, so per the brief no test was written; AC-291 is cheap to test (the render above is ~2 s) if the owner wants it. AC-292's wording vs the printed opener is an owner/architect call; no card owns it.

**The registry's "not checked" convention** is the one CARD-316 measured and CARD-481 followed: drop the AC's `test:` and say why in a comment. `kind: review-lens` on an AC is a measured no-op on the validator of record (requirements.yml AC-378's comment).

**Classes re-derived as sets** (`_verdicts()`/`_declared_refs()`, edits reverted and reapplied):
HONEST_DEAD 11 -> 0 (OUT 11, IN 0, all withdrawals); CENSUS 603 -> 597 (OUT the 11, IN the 5 defs); TRACE_TESTS 515 -> 509 (same sets); DEFINED 478 -> 483 (IN the 5); BOOKKEEPING_ONLY, FALSELY_ALIVE, FALSELY_DEAD, RESOLVED_FROM_AFAR, SAME_FILE_PROSE unmoved (empty symmetric differences; SAME_FILE_PROSE selects node ids only). Departure helper: honest-dead withdrawal warning 12 -> 21 (9 of the 11 are in the stored snapshot), bookkeeping-only 6 -> 8 (AC-291/AC-292's digests); no `losses`. Snapshots not trimmed, per their notes. Pin notes name no ref.

**Control (pins).** New pins with the registry edits reverted: 3 failed -- `test_the_two_directions_of_disagreement_are_exactly_the_measured_ones` ("the 'honest-dead' class moved: measured (11, 'ee3c6c612e2a0aa2'), baseline (0, 'e3b0c44298fc1c14')"), `test_a_ref_with_a_real_definition_is_not_reported` ("the 'defined' class moved: measured (478, ...), baseline (483, ...)"), `test_the_trace_tests_lists_agree_with_an_independent_reading` (its TRACE_TESTS assert precedes its CENSUS assert, so CENSUS is evidenced by the snapshot's 603 vs pinned 597, not by its own red line). Restored; `git diff --stat` shows only the three intended files.

**Validator of record** (forge_1 validate.py, `--root <worktree>/meta/architecture --phase all --format json`; the tree root reports the model files missing): 105 WARN -> 105 WARN, 0 errors both. OUT: AC-291's and AC-292's dead-ref warnings. IN: "acceptance criterion has no 'test'" on the same two locators -- the one-for-one swap CARD-316/CARD-481 recorded. FR-001/NFR-005 trace warnings unchanged (the validator only resolves `covered` rows' tests; both rows are partial).

**Gate** (unarmed, `-o addopts= -rfs`): tests/test_check_ref_resolution.py, test_impact_set.py, test_nfr001_generation_time.py, test_approval_guess_gate.py, test_book_page_packing_doc.py, test_grid_bound_agreement.py, test_public_player.py, test_public_player_pages.py (every module that reads requirements.yml/trace.yml, found by `ast`), test_export_image.py (the new refs' module), test_kanban_review_record.py: **468 passed, 1 xfailed, 0 skipped**. Net collected tests: 10708 -> 10708 (+0).

**Measurement trap, recorded.** The first mutant pass showed M2 green: M1, M2 and the original are byte-identical in length and were written within one second, so CPython reused M1's `.pyc` (mtime+size check). Rerun with `PYTHONDONTWRITEBYTECODE=1` after deleting those `.pyc`s gives the reds above; the pycs were deleted again after restoring.

[Review 1/3] Score: 9.5, nothing gating, certified. Pins re-derived independently as sets on git-initialised archive copies (CENSUS 603->597, TRACE_TESTS 515->509, DEFINED 478->483, HONEST_DEAD 11->0; the other classes unmoved; fingerprints equal the pinned tuples); each of the five re-pointed tests read against its AC and red under the reviewer's own layout mutant (AC-081's `< 6.5` alone cannot fail, as the notes say — its fit bound does); AC-291 true and untested at its boundary (a level-dropping mutant survived 1070 of 1071 book tests); AC-292's content clause false (page 16 byte-equal to `create_solutions_opener`); withdrawal shape follows CARD-316's AC-378; FR-001's row follows the owner's 2026-10-31 decision; validator 105 WARN both sides, two dead-ref warnings swapped for "no test" on the same criteria. F-001 (low) trace.yml's FR-001 note still said the four names "are kept listed": fixed inline by the orchestrator ("were kept listed (until 2026-11-20, see CARD-498 below)"). F-002 (low, optional) an AC-291 test at +0: not taken. F-003 (info) AC-292 needs an owner decision: asked 2026-11-20. F-004 (info, out of scope) requirements.yml's NFR-005 labels are falsely-alive class names, so the two registries now name different tests for the same ACs: recorded for the backlog.
**Owner amendment of AC-292 (2026-11-20, "yes, reword AC-292 to match the page"; review F-003).** Done by the orchestrator on this branch. AC-292's `given` now names the condition the opener depends on (divider pages on, no uploaded Solutions picture) and its `then` says the page between the puzzle section and the answer key is the Solutions opener drawn by `create_solutions_opener`; the page's look (rule, "PUZZLES 1–N", "Solutions", the grey line, folio) is in the comment, because a `then` listing them drew the validator's "bundles several outcomes" warning. `test:` names two existing tests (comma-separated, the registry's form): `test_no_divider_page_is_drawn_at_all_including_solutions` (the SOLUTIONS page drawn is the opener, after the three level dividers; none with dividers off) and `test_the_interior_is_that_section_between_the_guide_and_the_key` (its position). The opener's words are drawn into the image, so no test reads them as text; said in the comment. Pins re-derived as sets with the module's helpers: CENSUS 597 -> 599 and DEFINED 483 -> 485, OUT 0, IN exactly those two names each; the other six classes unchanged (8 of 8 match after the edit). forge_1 validator: 105 -> 104 WARN, the one change AC-292's "no test" warning gone, none new.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 5701 passed / 15 skipped (the selection's db_required tests with DATABASE_URL unset, plus the setrlimit platform skip) / 1 xfailed / 0 failed, plus 5 marked passed in the lifted files.
