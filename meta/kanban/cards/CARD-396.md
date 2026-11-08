# CARD-396: The kill-matrix reproductions run their cells in parallel — same cells, same verdicts, a fraction of the 192 seconds

**Status:** done
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
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/kill_matrix.py, tests/test_kill_matrix.py
**Review score:** 8.6 (cycle 2/3 - CERTIFIED; cycle 1: 7.5 NOT certified; cycle 2: 8.6 CERTIFIED)
**Started:** —
**Closed:** 2026-11-08T04:07Z
**Actual:** —
**Merge commit:** 49c3a7a144632d9a5ad1192903e5c1e0cadf60d4
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

- Design: `Runner(workers=N)`; N>1 measures SHIPPED + each mutant as tasks on N threads, each thread on its OWN copy of repo_root (minus `.git`, `.full-suite.lock`, venvs, caches) with its own cp -p backups; results stored by task index and read in declared order; lowest-index refusal raised; LockHeld raised by the parent before any copy. Path outside repo_root -> serial. The earlier premise "each cell on a clean copy" was false: the serial runner edits the real tree in place.
- Deviation: `workers` defaults to 1 on the Runner (in-place reading that 3 existing cells rely on, measured); `km.default_workers()` is the derived rule (env KILL_MATRIX_WORKERS, else min(4, cpus-1), floor 1); the ac7 four-arm grid passes it. Tests never set the variable.
- Measured (mine, solo, host with ordinary desktop background load): four-arm grid 14 cells, workers=1 81.0/87.0/94.9 s, default (4) 31.2/29.5/30.2 s; direct-call 1/2/4/6 workers = 81.1/52.1/31.5/29.5 s (cap 4 kept). Verdict JSON (figure, table, every cell, raw cells, records, exit codes, collected counts, shipped_between) byte-identical serial vs 2/4/6 workers. Lock-guard reproduction is ONE cell (SHIPPED only, no mutants) so the pool cannot help it: 6-10 s solo (the 21 s carried figure was contended). Whole test_kill_matrix.py with the 10 new cells: 113 s.
- AC-5: saving on the four-arm grid ~64 % (>= 30 %), pool kept. PLAIN STATEMENT (review F-2): the grid saves ~44-50 s, but the new cells cost; the net on the whole `test_kill_matrix.py` is in the fix-round note below. Once CARD-395 marks the ac7 reproductions wave_close_only, an ordinary gate loses the grid saving and keeps the new cells, so the card pays at wave close and in local full runs only.
- Declared bounds (F-6): the real tree is never edited with workers>1 (better than serial). SIGINT: parent exits after in-flight children finish, no orphan, lane trees removed. SIGTERM: parent dies at once, in-flight child pytests finish alone, lane trees stay in the temp dir. Hard kill by the hang guard cannot clean up.
- Fix round (review cycle 1): F-1 lock cell now spies on shutil.copytree (zero copies before the refusal) with a plant that skips the parent's check once; F-3 new cells 10 -> 7 (completion-order plant folded into the same-matrix cell, shared-tree plant into the two-cells cell, lowest-declared refusal into the refusal cell); F-4 refusal cell asserts later cells are never entered, same-matrix cell asserts `.git` (a FILE in the fixture), the lock file, `.env`, `*.db` are absent from every lane copy; F-7 lane copy excludes `.env`, `.env.*`, `*.db`, `*.sqlite*` (a target needing them runs with workers=1); F-8 `KILL_MATRIX_WORKERS=''` is an error.
- Fix-round timings (mine, solo, whole `tests/test_kill_matrix.py`, serial baseline = main at the same time in a scratch worktree): before 110.1 / 118.6 s (76 tests), after 78.8 / 84.1 s (83 tests): net about 31-34 s with the 7 new cells included (reviewer measured 15 s at 10 cells). Node ids: 76 -> 83, none removed or renamed.
- Plant -> killing cell (each run on a restored file): parent lock pre-check removed -> foreign_lock; completion-order collector -> same_matrix; shared tree -> two_cells (also leak, refusal, lock, same_matrix as collateral); `.git` or `.env` not skipped -> same_matrix; no skip of later cells -> refusal; lane trees not removed -> refusal; highest-index refusal raised -> refusal; path outside root handed to a lane -> outside_root; cap 5 -> worker_count_rule.

### Review record

[Review 1/3] Score: 7.5 (threshold 8.0 NOT reached; 0 blockers; NOT CERTIFIED). The lock cell could not fail, the saving was overstated, over-testing; fixed in the fix round above. Reviewer-reported, not re-run by the orchestrator.

[Review 2/3] Score: 8.6 (threshold 8.0 reached; 0 blockers; CERTIFIED). Reviewer-reported, not re-run by the orchestrator.

### Closing note (merge gate, 2026-11-08)

**Merged as 49a7a144** (`--no-ff` of `card/396-parallel-kill-matrix`, tip 46fdef67 after merging main). **Size datum (mine, `git diff --shortstat c15f9148 card/396-parallel-kill-matrix`): 3 files changed, 713 insertions, 16 deletions.** Estimate 2c against 2 review cycles = ratio 1.0; no wall-clock Actual (the clock measures the queue).

**Gate (mine):** the owner-policy impact selection: `scripts/impact_set.py --gate --against main` on the staged merge answered `SELECTION`, rc 0, 4740 of 11659 collected (40.7%), 54 test files (43 always-on). Run with `DATABASE_URL` armed to the main checkout's per-worktree test database, `-o addopts= -q -rEfs --durations=15 -p no:cacheprovider`: **4738 passed, 1 skipped, 1 xfailed in 1565.65 s (0:26:05)**; the one skip is the setrlimit platform gate in tests/test_book_pdf_memory.py. Fast sanity first (11 modules, unarmed): 1247 passed, 11 skipped (database not reachable, unarmed). Tree hash before and after the run 5c73e11f.

**What the merge delivers:** `Runner(workers=N)` in tests/kill_matrix.py (threads, each on its own copy of repo_root without .git, the lock file, .env and *.db; results in declared order), `km.default_workers()` and `KILL_MATRIX_WORKERS`; `tests/test_kill_matrix.py` 76 -> 83 node ids. Honest saving: the whole file about 122 s -> about 76 s solo, the four-arm grid about 86 s -> about 28 s; once CARD-395 marks test_ac7_* wave_close_only this pays at wave close only.

**What it does NOT deliver:** no change to which tests the gate runs; no coverage move.

**Carried (low, no new cards):** (1) the refusal cell's entered-set check is a subset check (tolerates SLOW/BAD-B entering; it still kills the skip plant); (2) at an ordinary gate after CARD-395 the 7 new cells cost about 12 s that only wave close repays; (3) the hard-kill-by-hang-guard bound is documented, not probed.
