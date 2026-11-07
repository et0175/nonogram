# CARD-396: The kill-matrix reproductions run their cells in parallel — same cells, same verdicts, a fraction of the 192 seconds

**Status:** ready
**Priority:** P2
**Category:** ops
**Estimate:** 2c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner ruling 2026-11-07 ("I'd do a+c, after measurement"; memory gate-time-cuts-a-and-c): C = pure speed, NO coverage move, each saving proven by a before/after --durations on the file alone. Measurement: ~/Documents/nonogram-reviews/suite-profile-2026-11-07/gate-card388-durations.txt (contended full run; shares only).
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/kill_matrix.py, tests/test_kill_matrix.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/test_kill_matrix.py` costs 240.6 s in the measured run (5.2 % of the suite). 192.5 s of it is two tests: `test_ac7_the_four_arm_grid_of_card_257_reproduces` (171.1 s) and `test_ac7_the_lock_guard_file_reproduces_130_of_130_pass_and_reached` (21.4 s). Each runs a grid of mutant cells, one child pytest per cell, SEQUENTIALLY, each on a clean copy of the shipped tree (the instrument's `G-5` temp tree, `tests/kill_matrix.py`). The cells are independent by construction ("two sequential mutants each see a clean shipped" is already asserted), so the wall-clock is the sum of the cells where it could be the longest cell. With CARD-395 these two tests are wave-close-only at the gate, so this card's saving lands at the wave close, in every CARD-260-style review that fires the matrix, and in any local full run; it is written as a separate card because its files are disjoint from CARD-395's and its value does not depend on it.

## What to implement

1. Run the cells of a `Matrix` concurrently (a bounded worker pool, default `min(4, cpu_count - 1)`, settable by one environment variable the test pins to 1 for the determinism cell), each worker on its OWN temp tree copy; results are collected into the cell order the matrix declares, so the verdict table is byte-identical to the sequential one.
2. The instrument's refusals stay exactly where they are (lock held by a foreign worktree, leaked patch, line-shifting mutant, unparsable mutant). A refusal in any worker aborts the matrix with the same exception type, and every temp tree is removed (G-5's "a failed restore keeps it" behaviour is per tree).
3. Measure: the two reproductions alone, before and after, `--durations=0`, three runs each, idle host, and record the cells' total CPU against the wall-clock (parallel children contend with each other; the speed-up is not assumed to be linear).

## Acceptance criteria

* **AC-1** (same verdicts): the two reproductions pass unmodified (same cell-for-cell expectations: six `DOC-NAME-DEL` RED, four `DOC-HEAD-DEL` RED, `NAMES-BLIND` RED with three NOT-REACHED, `POINTER-*` RED, `CONTROLS-RENAME-ONLY` PASS, SHIPPED all-PASS; and 130 of 130 for the lock guard). (test: the existing ac7 cells.)
* **AC-2** (order and determinism): a matrix run with 1 worker and with N workers returns an identical `Matrix` (cell order, outcomes, reached sets); the instrument's output does not depend on completion order. (test: a new cell on a small synthetic target; plant: a collector that appends in completion order reds it.)
* **AC-3** (isolation holds under concurrency): two cells whose mutants touch the same target file do not see each other's edit (each worker's tree is its own); a worker that leaks a patch is reported as `LeakedPatch`, not absorbed. (test: new cells; plant: workers sharing one tree red the first.)
* **AC-4** (cleanup and refusal): after a refusal mid-matrix no temp tree remains; a foreign lock still raises `LockHeld` before any worker starts. (test: the existing G-5 / lock cells plus one new.)
* **AC-5** (measured): the before/after of the two reproductions on the file alone is pasted in the card with the host cells; the saving is stated in seconds and as a ratio against the cells' summed time. If the measured wall-clock saving is under 30 % the card records the null result, reverts the pool and closes without merging the pool (CARD-235's precedent: a measured null is a result).
* **AC-6** (nothing moved, G-4): node-id set difference against the merge-base is empty (no removed, no renamed, no skip); node ids stay stable because CARD-395's registry names them.

## Guardrails

* **G-1** No cell removed, no mutant weakened, no verdict re-derived by the new code path; the pool only changes WHEN cells run.
* **G-2** `tests/kill_matrix.py` still imports only the stdlib and `tests.full_suite_lock` (its own header contract).
* **G-3** The suite's other tests are never run in parallel by this card; only a matrix's children are.

## System contract

* CARD-260 / CARD-256 — the kill instrument's six traps stay refused (check: `tests/test_kill_matrix.py` AC-1..AC-6 cells, unchanged)
* ADR-0039/R4 — a control must be able to fail (check: AC-2 and AC-3 plants)

## Worktree notes

(none yet)
