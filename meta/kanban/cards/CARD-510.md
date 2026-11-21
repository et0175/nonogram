# CARD-510: Independently re-fire CARD-276's six mutant cells, or declare each one unfired with its reason

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/510-refire-276-mutants
**Worktree:** —
**Source:** roadmap wave 7, added 2026-11-20 on the owner's "add IDEA-215 to this wave too". IDEA-215 (WSJF 3.08), split out of CARD-300 (skipped) on 2026-10-28, where it was AC-5.
**Idea:** IDEA-215
**Wave:** 86
**Created wave:** 86
**Deferred waves:** 0
**Depends on:** —
**Touches:** none in src/ or tests/ (a measurement; results go on this card)
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-21T00:19Z
**Closed:** 2026-11-21T03:59Z
**Actual:** 1c — ratio 1/1 = 1.0
**Merge commit:** 67b434d30b3de2a9017b167b226ad2610d491ba1
**Blocked by:** —

## Why this card exists

CARD-276 (done, merged `f794d5a8` at review 6.5, NOT certified) owed AC-5: fire the six kill-matrix cells N8, N12b, N13, N14, N16, N18 against CARD-262's `ac479658` and against CARD-276's own HEAD. Its implementation round did fire them once and recorded a table (CARD-276, section "5. The six unfired cells (AC-5)": against `ac479658` N8 = 1, N12b = 5, N13 = 1, N14 = 2, N16 = 1, N18 = 1 FAIL cells; against HEAD N8h = 1, N13h = 0 declared no-op, N14 = 2, N16 = 1, N18 = 1, N12b no analogue). Review cycle 2 accepted that table on trust and called it "the largest single thing I did not measure". What is owed is an independent re-run, or a written declaration per cell, with no code change.

## What to implement

1. Read CARD-276 section 5 (the domain: committed `tests/kill_matrix.py`, `Pass.RECORDING`, `ast.Assert` node counts, child instrumentation off, ANY-RED aggregation, line-count-preserving mutants, SHIPPED re-run FAIL-free between mutants) and its mutant definitions. Read tests/kill_matrix.py's own API by import.
2. Re-create each mutant from its definition (not from CARD-276's scratch scripts, if any survive) and fire it against `git archive` copies of `ac479658` and of CARD-276's merged tree (`f794d5a8`), under /private/tmp/claude-501/card510/, never in a worktree. Confirm each copy is the code under test (`__file__`).
3. Record a table per tree: cell, mechanism deleted, FAIL count, the assertion nodes it reds (by test name), and whether it matches CARD-276's table. A mismatch is a finding: say which number is right and why.
4. A cell that cannot be fired faithfully (its mechanism or the instrument no longer supports it at that commit) is declared unfired with its concrete reason.
5. One line on whether each cell's mechanism still exists on today's main (by `ast`); no firing on main is required.

## Acceptance criteria

* **AC-1**: each of the six cells, against both trees, is fired and recorded with its FAIL count and red nodes, or declared unfired with its reason (N12b has no HEAD analogue by CARD-276's AC-4: confirm that by `ast`, do not assume it).
* **AC-2**: SHIPPED (unmutated) is FAIL-free on each tree, re-run between mutants; every mutant is shown to change the file (the instrument's `old` present, the mutated bytes differ).
* **AC-3**: no change under src/ or tests/; net test count 0.

## Guardrails

* **G-1**: never run a mutant in the worktree or the main checkout; scratch copies only. `git diff --stat` on the worktree is empty apart from this card at hand-back.
* **G-2**: no database is needed; if a selected test is db_required, say it skipped and why.

## Worktree notes

### Implementation round (2026-11-21) — the six cells re-fired, on whole-file selections

**Domain for every figure:** each copy's own `tests/kill_matrix.py`, imported from the copy, with its `__file__` asserted to be the copy's (the instrument is byte-identical at `ac479658`, `ced5e648` and `f794d5a8`). `Pass.RECORDING`, `ast.Assert` **node** counts, child instrumentation **off**, ANY-RED. The selection is the **whole** `tests/test_book_export_interior_cover.py`, not a targeted subset, so no cell is NOT-REACHED because of the selection. SHIPPED was re-run by `Runner.run` between every pair of mutants and was FAIL-free every time. pytest exited 0 on every mutant, so every kill below is the matrix's reading, not the exit code. The mutants were rebuilt from the definitions in CARD-262's mutant table and CARD-276 section 5. CARD-276's scratch scripts were not used.

**The trees:** each one came from `git archive <sha> | tar -x` under `/private/tmp/claude-501/card510/`. A probe plugin run in each copy printed `nonogram.__file__`, `tests.__file__`, `tests.kill_matrix.__file__` and the target's `__file__`, and every one was under that copy's own `src/` or `tests/`. Target sha256:
* `ac479658`: `55311d7b…`, the bytes CARD-276 names.
* `f794d5a8`: `9be1e17a…`.
* `ced5e648`: `4a2a28eb…`, the bytes CARD-276's HEAD table was fired against (its section 12).

Each target's sha256 after the run equalled its sha256 before. Plain runs, with `-o addopts= -rfs`:
* `ac479658`: **90 passed**.
* `f794d5a8`: **127 passed**.
* 0 failed and **0 skipped** on both, so G-2 holds and no test is `db_required`.

A copy has no `.git`, so its `full_suite_lock.default_lock_path` resolves to the copy's own `meta/kanban/.full-suite.lock`, which does not exist. The copies therefore never read the board's lock. I checked that the main checkout's lock was absent before starting the runs.

**The one NOT-REACHED node on every tree:** `TestBookFinalise_CoverPathOutsideTheCoverDirIsIgnored::test_no_export_prints_the_outside_file`, `assert not same_page(page, …)`. It is the `status_code == 200` arm, and every route takes the 302 arm. It is not a selection bound and it is unrelated to the six mechanisms.

**AC-2, every mutant changes the file:** `apply_edit` from the copy's own instrument found each `old` the stated number of times (`occurrence=2` where there are two). The mutated sha256 differs from the pristine one in every case, and `assert_shapes` of the mutated text equals that of the pristine text. The instrument's own topology check passed for every mutant.

#### `ac479658`: 184 nodes, SHIPPED 0 FAIL of 183 reached, 90 collected

| cell | mechanism deleted (edit) | FAIL | red nodes (test) | vs CARD-276 |
|---|---|---|---|---|
| N8 | `ast.Attribute` branch's one-step gate: `if cls.ONE_STEP_ANCHOR not in exempt:` → `if False:`, occurrence 2 | **1** | :4631 `test_the_declared_blind_spots_are_still_silent` (absorbed rows) | **matches**: 1, and :4604 PASSes. CARD-276's correction of CARD-262's "2" stands. |
| N12b | `ONE_STEP_ANCHOR` removed from `CALLEE_EXEMPTIONS` (the line replaced by a comment) | **6** | :3583 `test_each_door_axis_arm_catches_a_shape_the_other_misses`; :3866 `test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`; :3941, :3967 `test_every_callee_exemption_is_read_twice_on_its_own_branch`; :4591, :4604 `test_the_declared_blind_spots_are_still_silent` | **mismatch: 6, not 5.** See finding F-1. |
| N13 | cross row R1b in `MEASURED_BLIND_SPOTS`: `_d = _x` → `_d = _x()` | **1** | :4604 `test_the_declared_blind_spots_are_still_silent` | matches |
| N14 | `authority = set(dir(builtins)) \| set(dir(operator))` → `set() \| set()` | **2** | :4214, :4220 `test_no_door_axis_arm_branches_on_a_dynamic_access_idiom` | matches |
| N16 | `_plant_refusals`' window: `refusal[0] > own` → `refusal[0] > 0` | **1** | :3967 `test_every_callee_exemption_is_read_twice_on_its_own_branch` | matches |
| N18 | own-instance surface rule: `if holder is None or key[1] not in surface.get(holder, ()):` → `if False:` | **6** | :3538, :3551 `test_every_door_shape_is_read_or_refused_and_never_silent`; :3583 `test_each_door_axis_arm_catches_a_shape_the_other_misses`; :3913 `test_each_door_reaching_shape_is_refused_by_the_mechanism_that_refuses_it`; :4044, :4057 `test_the_receiver_resolution_bound_is_reported_rather_than_capped` | **mismatch: 6, not 1.** See F-1. |

#### `f794d5a8` (CARD-276 merged): 205 nodes, SHIPPED 0 FAIL of 204 reached, 127 collected

| cell | mechanism deleted (edit) | FAIL | red nodes (test) | vs CARD-276 |
|---|---|---|---|---|
| N8h | `ast.Attribute` branch's fixed-point gate: `blocked = anchor_refusal(key, call)` → `blocked = None`, occurrence 2 | **5** | :4024, :4037 `test_every_door_shape_is_read_or_refused_and_never_silent`; :4077 `test_each_door_axis_arm_catches_a_shape_the_other_misses`; :5695 `test_a_chain_of_any_length_is_read_or_refused_and_never_silent`; :5918 `test_no_door_shape_is_laundered_by_an_unrelated_resolving_occurrence` | **mismatch: 5, not 1.** See F-1 and F-2. A second spelling, `if blocked is not None:` → `if False:` in the same branch, reds the **same 5 nodes**. |
| N12b | none: the class does not exist | **unfired** | — | **confirmed by `ast`, not assumed.** There are 0 `Name` and 0 `Attribute` nodes for `ONE_STEP_ANCHOR` and 0 `Constant` nodes equal to its old value. `CALLEE_EXEMPTIONS` is the 4 classes plus `"a chain whose terminal is a definition or an import"`. See F-3 for that class. |
| N13h | W30 row's plain alias: `_d = _x` → `_d = _x()` | **0** | — | matches CARD-276's declared no-op. The mutated bytes differ, so it is a real edit that nothing observable reads. |
| N14 | as above | **2** | :4750, :4756 `test_no_door_axis_arm_branches_on_a_dynamic_access_idiom` | matches (same two assertions) |
| N16 | as above | **1** | :4503 `test_every_callee_exemption_is_read_twice_on_its_own_branch` | matches. This is the assertion `ced5e648`:4214 holds. |
| N18 | as above | **9** | :4024, :4037, :4077, :4449 `test_each_door_reaching_shape_is_refused_by_the_mechanism_that_refuses_it`; :4580, :4593 `test_the_receiver_resolution_bound_is_reported_rather_than_capped`; :5765 `test_a_door_installed_from_outside_the_text_survives_one_resolving_occurrence`; :5845 `test_a_name_nested_inside_a_method_is_not_the_classs_attribute_surface`; :5918 | **mismatch: 9, not 1.** See F-1 and F-2. |

**Supplementary, not N12b:** removing the successor class `"a chain whose terminal is a definition or an import"` from `CALLEE_EXEMPTIONS` reds **8**:
* :4402 (the zero-cost classes equality);
* :4477 and :4503 (`test_every_callee_exemption_is_read_twice_on_its_own_branch`);
* :5181 and :5194 (`test_the_declared_blind_spots_are_still_silent`);
* :5736 `test_a_chain_whose_terminal_this_module_shows_is_resolved_not_refused`;
* :6007 and :6018 `test_the_anchor_resolution_bound_is_reported_rather_than_capped`.

#### Findings

* **F-1: CARD-276's cells for N12b, N18 and N8h are selection-bound counts, presented as the cell.** CARD-276 says its selection was targeted, but it never names the 5 or 16 tests. On the **same bytes**, the whole file reds more nodes. Each extra node is in a test that existed at those bytes but was outside the selection:
  * N12b at `ac479658`: +:3583 (`test_each_door_axis_arm_catches_a_shape_the_other_misses`, the one section 6 of CARD-276 says it left out of every selection).
  * N18 at `ac479658`: +:3538, :3551, :3583, :4044, :4057.

  To separate selection from later edits, N8h and N18 were also fired on `ced5e648` (`4a2a28eb…`, 198 nodes, the same as CARD-276 section 12; SHIPPED 0 FAIL of 197 reached, 104 collected):
  * N8h reds **4**: :3773, :3786 `test_every_door_shape_is_read_or_refused_and_never_silent`, :3826 `test_each_door_axis_arm_catches_a_shape_the_other_misses`, and :5080.
  * N18 reds **6**: :3773, :3786, :3826, :4160, :4291 and :4304.

  CARD-276's own M1 row (section 6) shows :3773 and :3786 red under a one-step anchor, so the door-shapes test was simply not in its AC-5 batch. **The right numbers are the whole-file ones.** CARD-276's 1/5/1 are correct only inside its undisclosed selections. Every node it named is in my red sets, so it named nothing wrong; it only missed nodes. The "matches CARD-262" column compared two narrow selections with each other. Each node CARD-276 named for N8, N13, N14 and N16 is reproduced, and those four counts agree.
* **F-2: on the merged tree the remaining differences come from tests added after `ced5e648`**, by CARD-276's fix rounds:
  * N8h: 4 → 5 (+:5918, the laundering test).
  * N18: 6 → 9 (+:5765, :5845, :5918).
* **F-3: "N12b has no HEAD analogue" is true by name and false by position.** `ONE_STEP_ANCHOR` is gone. The terminal class now holds the same structural slot: the fifth class, the one zero-cost class, kept alive by its blind-spot row. Removing it reds 8 nodes, so that membership has controls. This is recorded as a reading only. No card is warranted, because the cell is covered.

#### Each mechanism on today's main (`1ba56d75`), by `ast` over `tests/test_book_export_interior_cover.py`; not fired

* N8/N8h: the one-step gate is absent (0 `If` nodes on `cls.ONE_STEP_ANCHOR not in exempt`). The fixed point exists: `anchored_to_a_fixed_point` is defined and both `blocked = anchor_refusal(key, call)` assignments are present.
* N12b: absent (0 `ONE_STEP_ANCHOR` names).
* N13/N13h: both cross-row plain-alias constants are present.
* N14: the authority derivation is present (1).
* N16: `_plant_refusals` and its window condition are present.
* N18: the surface-rule `If` is present (1).

**AC-3 / G-1:**
* Nothing changed under `src/` or `tests/`, and no mutant ran in the worktree or in main.
* `git diff --stat main...HEAD` shows this card only.
* Collected count before and after is the same, `10689`, so the net change is 0.

[Review 1/3] Score: 9.5, nothing gating, certified. The reviewer re-fired on its own `git archive` copies with its own mutants: on `ac479658` whole-file N12b = 6 and N18 = 6, the same nodes; on `f794d5a8` N8h = 5, the same mutated sha. Narrowed to the five tests that hold CARD-276's named nodes, it gives N8 = 1, N12b = 5, N18 = 1, exactly CARD-276's table, so the selection explanation in F-1 is now measured, not inferred. F-001 (low): F-1 was stated as an inference; the narrow run settles it. F-002 (low): the HEAD-table N14 and N16 were matched to `ced5e648` lines by assertion text, not re-fired on those bytes (the mapping checked correct). F-003 (info): `1ba56d75` is the branch's merge-base, not main's tip; the target file is identical in both.

**Merge gate (orchestrator).** `make test-gate BASE=main` (a selection): 1 failed / 4133 passed / 14 skipped / 8 deselected. The one red, `test_the_assembly_helper_drives_the_assembler_and_writes_nothing_itself`, was not this card's: main's wave-7 publish record (`57aafb2a`) wrote the CSS token `--text-xs` in backticks in docs/deploy/player.md, and that test reads every backticked `--word` on the page as an assembly-helper flag. Reworded on main (`98f79a43`), merged in; tests/test_public_player_pages.py plus tests/test_kanban_review_record.py then 104 passed, 0 skipped.
