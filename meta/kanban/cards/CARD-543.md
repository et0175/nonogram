# CARD-543: The public-mode mutant matrix's clean control survives a loaded machine

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/543-public-control-load
**Worktree:** ../PythonProject4-card-543
**Source:** roadmap wave 19, cut 2026-11-24 on the owner's "card both" (the two proposals recorded at the Wave 18 close).
**Idea:** —
**Wave:** 98
**Created wave:** 98
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_player_public_mode.py
**UI surface:** —
**Review score:** 9.5 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-24T19:06Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant` reddened two merge gates on 2026-11-24 (CARD-535 and CARD-542). Both times it was the clean control, not the mutant: `the control (sweep) is not green on the real files: ['sweep aborted: TimeoutError: Locator.click: Timeout 10000ms exceeded.']`. Re-run alone, the file gave 27 passed each time (206 s and 218 s). `sweep_problems` sets `page.set_default_timeout(timeout)` with `timeout=10000`, and turns any exception into a problem, so a slow click on a busy machine reads as a lost property. A gate red that is not a defect costs a full re-run and teaches the reader to ignore this test.

## What to implement

1. Verify first. Reproduce the abort under load: run the parametrized test while the machine is busy (for example a few CPU-bound processes beside it, or the gate's own concurrency), and record which click times out and how long the slowest clean sweep takes. If it cannot be reproduced, record the attempts and the measured sweep durations instead.
2. Make the clean control tolerate load without weakening the matrix: every mutant in `MUTANTS` must still red its check. Prefer the smallest change that the measurement supports (for example a longer click timeout for the sweep in this test, sized from the measured slowest sweep with margin), over retries that could also hide a real abort.
3. If the same 3 s / 5 s timeouts of the other checks (`stall_problems`, `refusal_problems`, `save_problems`, `admin_mode_problems`, `sealed_problems`) show the same abort under the same load, treat them the same way; otherwise leave them and record why.
4. Do not touch the player's source files (`src/nonogram/admin/static/solver*.js`).

## Acceptance criteria

- AC-1: the verdict (reproduced or not, which click, the measured durations) is recorded in `## Worktree notes` with the command used, backed by a run, never by reading code alone.
- AC-2: under the load recorded in AC-1, the clean control of `test_the_check_is_green_on_the_real_files_and_red_on_the_mutant` is green across every parametrized case; and with the change in place every mutant still reds its check (the full parametrize passes). Record both runs.
- AC-3: owner's test budget: change existing tests rather than add; net test count 0; report it.

## Worktree notes

**Verdict (AC-1): reproduced; two causes, both measured. The sweep's 10 s click abort is a SYSTEM SLEEP, not CPU load; CPU load separately aborts the stall control's 3 s goto.** All runs below are only `tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant` (or named cases of it), from this worktree with `/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python -m pytest -o addopts= -q -p no:cacheprovider`. Load = N `yes > /dev/null` processes started and killed (trap) by the same script (`loaded_run.sh <N> ...`), plus whatever the machine was already running (1-min load average quoted). A scratch plugin (`-p clicktimer`, not committed) timed every Playwright action and every check call, with wall-clock and monotonic time.

- **Run 1, before the change.** Load: 16 `yes` (more than the later limit of 8), load average 144-183. Result: 3 failed / 24 passed in 474.39 s. All 3 reds were the STALL clean control: `aborted: TimeoutError: Page.goto: Timeout 3000ms exceeded.` (each a real 3.0 s). Clean sweeps took 11.5-14.6 s and stayed green; no single clean-sweep click took over 1 s.
- **Run 2, before the change.** Load: 8 `yes`, load average 89 falling to 22. Result: 27 passed in 244.60 s. The slowest single action in any clean sweep was 0.31 s (a goto), and clean sweeps took 9.2-11.7 s. CPU load does not make sweep clicks slow.
- **What did reproduce `Locator.click: Timeout ...ms exceeded`: a system sleep.** From 21:39 local the machine cycled DarkWake (~45 s) / Sleep (~15 min) (`pmset -g log`). In that state a clean-sweep click on `[data-player-probe]` raised `Locator.click: Timeout 30000ms exceeded` after 0.451 s of awake (monotonic) time. Another raised `Page.goto: Timeout 30000ms exceeded` after 0.463 s, with 900.9 s of sleep inside the call. Playwright's clock counts the sleep; Python's `time.monotonic` does not. So a sleep mid-action fires the timeout whatever its length.
- **The gate reds line up with sleeps.** `pmset -g log` shows 'Idle Sleep' at 08:10:46 and 08:40:26 in the CARD-535 gate window (merge 08:56, gate 22 min plus two re-runs). It shows 'Idle Sleep' at 16:33:12 and 17:22:46 in the CARD-542 gate window (gate after 16:29, 21.5 min plus re-runs). A drift sampler (`time.time() - time.monotonic()`) logged `23:22:04 drift jump 100.4` across one sleep.

**The change: `tests/test_player_public_mode.py`, test only; the player's files are untouched.**
1. `_CONTROL_TIMEOUT = 30000`: the clean control's Playwright timeout, about twice the slowest whole clean sweep measured under load (14.6 s). The mutant keeps each check's own timeout (3 s / 5 s / 10 s), so its verdict is unchanged. This covers the stall goto aborts of run 1 (card item 3). It is passed to every check as `timeout=`; `_hint_check`/`_solved_check` ignore it as before.
2. `_awake(run)`: re-runs a check call, on a fresh page and a fresh served tree, only when `time.time() - time.monotonic()` drifted by 2 s or more during it, i.e. the machine slept. It makes at most 3 attempts and is applied to both the clean and the mutant call. A run the machine stayed awake through is returned as it is, so an abort on an awake machine is never retried away. A mutant that reds only because of a sleep is also re-run, which makes the matrix stricter.
A longer timeout alone would not have fixed the gate reds: the 30 s timeout still aborted across a sleep (above).

**AC-2, after the change (fix1).** Load: 8 `yes`, load average 10-83, with the machine's sleep cycling live. Result: `27 passed in 255.72s` (pytest's monotonic awake time; 23:22-00:02 wall). That is 57 check calls in all:
- 27 awake clean runs, all `[]`; the slowest clean sweep took 12.69 s.
- 27 awake mutant runs, every one non-empty, so every mutant in `MUTANTS` still reds its check.
- 3 calls slept (312.9 s, 916.7 s, 900.9 s) and were re-run. One of them, at 23:59:58, was the gate's failure itself: a clean sweep `sweep aborted: TimeoutError: Page.goto: Timeout 30000ms exceeded.` after 1.22 s of awake time. `_awake` re-ran it, and it was green at 00:00:11.

**Final plain run, after the change** (no plugin, no added load, sleep cycling live): `pytest tests/test_player_public_mode.py -o addopts= -q -p no:cacheprovider -rfEs` gave 79 passed, 1 warning in 278.51 s, 0 skipped, exit 0.

**AC-3.** `--collect-only` of the file: 79 tests on HEAD, 79 with the change, so the net test count is 0. Two existing tests were changed and none added.

**Not done, outside this card's Touches:** a gate on this laptop can still lose any browser test to an idle sleep, and only this test now tolerates it. Running the gate under `caffeinate -i` (Makefile `test-gate`/`test-wave-close`) would prevent the sleep itself. That needs a decision; it is not changed here.

**Process incident.** One measurement run (19:38Z, pid 9634) passed node ids that zsh expanded as subscripts (`$T[...]`). pytest got no node id, started the whole suite and took the full-suite lock. I killed it, which left the lock stale; it blocked CARD-544 for 16 min until the coordinator removed it. Later runs quoted the ids and were bounded by a watchdog.

[Review 1/3] Score: 9.5, not certified. One medium finding is open. Verified by running, from this worktree: the full parametrize gave 27 passed in 196.70s, awake throughout, so every mutant still reds its check. The whole file gave 79 passed, 0 skipped, exit 0. `--collect-only` gave 79 on head and 79 with main's copy of the file, so the net test count is 0. A probe (temporary `_CONTROL_TIMEOUT = 1` plus a print per `_awake` attempt, reverted) gave 2 failed and exactly 2 attempts for 2 cases: on an awake machine a red control is returned on its first run, never retried away. The sleep detector is sound. `time.monotonic` is `mach_absolute_time()` here, which stops in sleep; an NTP step costs at most one harmless re-run; and `range(3)` bounds the loop. pmset shows Idle Sleep at 08:10:46, 08:40:26, 16:33:12 and 17:22:46, as the notes state. F-001 (medium, open): AC-2 asks for green "under the load recorded in AC-1", but the after-change run used 8 `yes` (load 10-83). The CPU-load stall reds were reproduced only at 16 `yes` (load 144-183), and at 8 `yes` the unchanged test was already 27/27. So no recorded run backs "this covers the stall goto aborts of run 1". Either run at the reproducing load or record that this half is argued from the margin. F-002 (low): `_awake` returns a slept result once its 3 attempts run out, where it could fail loudly. F-003 (info): the figures in the new comments come from an uncommitted scratch plugin. Report: meta/review/CARD-543-review-1.yml (gitignored; sync it before removing the worktree).

**Fix round 1 (F-001, F-002, F-003).**
- **F-001 is closed by a run at the reproducing load.** This was the only run above the 8-process cap. `--collect-only` of the parametrize collected 27 ids; crossing them with the `"stall"` entries of `MUTANTS` gave 5 cases: `[hint-falls-back-to-revealing-a-cell-stall]`, `[hint-disabled-again-where-no-line-decides]`, `[hint-reveals-a-cell-where-no-line-decides]`, `[hint-is-silent-where-no-line-decides]`, `[hint-counts-where-no-line-decides]`. The command was `f001_run.sh`. It read the 5 quoted ids into an array, refusing to start unless there were exactly 5 well-formed ids, then ran `MAXSECS=600 caffeinate -is loaded_run.sh 16 ...`: 16 `yes` processes started and trap-killed by that script, a 600 s watchdog, and `caffeinate` held for that run only, on the changed code. Result: `5 passed in 142.83s`, exit 0, 07:04:26-07:08:23 local. Load average was 198.7 at the start, 259.8 at the end, and 242-247 at check time. The machine stayed awake: `pmset -g log` shows DarkWake at 07:00:37 and the next Sleep at 07:08:26, nothing in between, and every check call measured 0.0 s slept. All 5 clean stall controls were green. Their slowest action was a `Page.goto` of 3.53 s; that exceeds the old 3 s and would have aborted the control as in run 1, but it is absorbed by `_CONTROL_TIMEOUT`. Of the other clean gotos, 2.25 s, 1.95 s, 1.21 s and 1.56 s were all within it. All 5 mutants were red. One observation, not changed here: at this load `[hint-reveals-a-cell-where-no-line-decides]` was red only through its own 3 s `Page.goto` timeout (3.003 s), not through its assertion. The mutant keeps the check's own timeout by design, so at load ~245 a stall mutant can be "caught" by the load. At load 22-89 (run 2) the same mutant red by its assertion.
- **F-002: `_awake` now fails loudly when every attempt slept.** It calls `pytest.fail("the machine slept through all 3 attempts ([...] s); no verdict: ...")` instead of returning a result the sleep may have decided. Probe: a scratch script, `probe_awake.py`, run with `PYTHONPATH=.:src`. It replaced the module's `time` with a fake whose `time()` gains an injected offset per run, and made no tree edit, so there was nothing to revert. Results: no sleep returned after 1 run; one sleep then awake returned after 2 runs; 3 sleeps raised `pytest.fail: the machine slept through all 3 attempts ([900.0, 900.0, 900.0] s); no verdict: [...]` after 3 runs.
- **F-003: the timing figures come from an uncommitted scratch plugin.** This applies to every per-action duration, check duration and "slept" figure in these notes and in the code comments: 0.31 s, 0.451 s, 3.53 s, 14.6 s, 12.69 s, and the slept seconds. They come from `clicktimer.py`, a scratch pytest plugin that wraps Playwright `Locator`/`Page` methods and the module's `CHECKS`. It is not in the tree, so a reader cannot rerun it from here. It was run as `CLICKLOG=<log> PYTHONPATH=<scratch>/plug python -m pytest -p clicktimer -p no:cacheprovider -o addopts= -q <node ids>`, inside `loaded_run.sh <N> <log> <out> <node ids>`, which also starts and trap-kills N `yes` and a watchdog. The pass/fail counts are plain pytest summaries.

[Review 2/3] Score: 9.5, certified. F-001, F-002 and F-003 are resolved. F-001: the recorded run at 16 `yes` (load average 198.7-259.8, above Run 1's) gave 5 passed. Its slowest clean goto took 3.53 s, past the old 3 s and absorbed by `_CONTROL_TIMEOUT`. pmset corroborates the awake window (DarkWake 07:00:37, next Sleep 07:08:26). I did not re-run it (no CPU load allowed). F-002: my fake-clock probe (scratch `c543_probe2.py`, no tree edit) shows 3 sleeps raise `pytest.fail` after 3 runs, an awake red on the real clock runs once, 1 or 2 sleeps then awake return after 2 or 3 runs, a -5 s step costs one re-run, and 1.9 s costs none. F-003: the notes now attribute every figure to the uncommitted `clicktimer.py`. Re-run from this worktree: the parametrize gave 27 passed in 203.92s, awake throughout; the whole file gave 79 passed, 0 skipped, exit 0; 79 collected, so the net test count is 0. F-004 (low, out of scope, not gating): at load ~245 a stall mutant can be red through its own 3 s timeout rather than its assertion, as the notes record. This predates the card. Report: meta/review/CARD-543-review-2.yml (gitignored; sync it before removing the worktree).

**Orchestrator.** F-004 (a stall mutant at load ~245 reds through its own 3 s goto rather than its assertion) recorded, not carded: it predates this card, needs that load to show, and fails safe toward a red.
