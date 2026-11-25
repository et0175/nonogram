# CARD-545: The merge gate and the wave close keep the Mac awake while they run

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/545-caffeinate-gates
**Worktree:** ../PythonProject4-card-545
**Source:** roadmap wave 20, cut 2026-11-25 on the owner's "card the caffeinate change" (proposed at the Wave 19 close).
**Idea:** —
**Wave:** 99
**Created wave:** 99
**Deferred waves:** 0
**Depends on:** —
**Touches:** Makefile, tests/test_wave_close_marker.py (only if a Makefile assertion there needs the new form), CLAUDE.md (only the Commands section's one line on the gate/close targets, if the run form changes what it says)
**UI surface:** —
**Review score:** —
**Started:** 2026-11-25T08:57Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-543 measured that the browser-test timeouts at the CARD-535 and CARD-542 gates were macOS idle sleep during the run: Playwright's timer counts time asleep, and both reds overlap an "Idle Sleep" in `pmset -g log`. Only that one test now tolerates a sleep; every other browser test in `make test-gate` and `make test-wave-close` is still exposed. The orchestrator has been wrapping its own gate script in `caffeinate -i` since 2026-11-25, but a gate run straight from `make` is not.

## What to implement

1. Verify first: confirm on this machine that `caffeinate -i <cmd>` holds a `PreventUserIdleSystemSleep` assertion for the command's lifetime and returns the command's exit status unchanged (run it on a command that exits non-zero, and read `pmset -g assertions` while it runs). Record both.
2. Make `test-gate` and `test-wave-close` (and `test-marked`, if it shares the same run path) run their pytest commands under `caffeinate -i` when `caffeinate` is on PATH, and run them unchanged when it is not (Linux CI, Docker). The exit status each target reports, and its existing refusals (for example `test-wave-close` refusing `-m`/`-k`/`--deselect`/`--ignore` in `PYTEST_ADDOPTS`), must be unchanged.
3. Do not wrap anything with a timeout or retry, and do not touch the full-suite lock or `tests/conftest.py`.
4. If `CLAUDE.md`'s Commands section describes these targets in a way the change makes untrue, correct that one line; otherwise leave it.

## Acceptance criteria

- AC-1: the verification in step 1 is recorded in `## Worktree notes` with commands and output, backed by a run.
- AC-2: with the change, each changed target holds the sleep assertion while its pytest runs (shown by `pmset -g assertions` during a short run, for example `make test-marked` or a target run with a tiny selection if the Makefile allows one), keeps a failing exit status failing (one control: a run made to fail still exits non-zero), and runs without `caffeinate` on PATH (one run with PATH stripped of `/usr/bin/caffeinate`, recorded).
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes

### Implementation round 1 (2026-11-25)

**Verdict:** done; all three ACs met by the runs below. Scratch paths below are this session's scratchpad (`$S`).

**AC-1 -- caffeinate verified on this machine (step 1).**
`caffeinate -i sh -c 'sleep 3; exit 7' & sleep 1; pmset -g assertions | grep -iE "caffeinate|PreventUserIdleSystemSleep"; wait $!; echo exit=$?`
- during the run: `pid 16686(caffeinate): PreventUserIdleSystemSleep named: "caffeinate command-line tool" / Details: caffeinate asserting on behalf of 'sh' (pid 16684)`
- after: `caffeinate exit=7`, and pid 16686 is gone from `pmset -g assertions` (only two unrelated `caffeinate asserting for 300 secs` holders, not started here, remain).
So the assertion lasts as long as the command does, and the command's exit status comes back unchanged.

**Change (Makefile).** A new variable, and three recipe lines get a prefix:
- `KEEPAWAKE ?= $(if $(shell command -v caffeinate 2>/dev/null),caffeinate -i)`: this is `caffeinate -i` when caffeinate is on PATH and empty when it is not. `KEEPAWAKE=` on the command line turns it off.
- `test-wave-close`: `$(KEEPAWAKE) $(PY) -m pytest` (the PYTEST_ADDOPTS refusal comes before it and is untouched)
- `test-marked`: `$(KEEPAWAKE) $(PY) -m pytest -m wave_close_only`
- `test-gate`: `... echo "+ $$cmd"; $(KEEPAWAKE) sh -c "$$cmd" || rc=1; ...` (each `run N:` command is wrapped; the impact_set derivation and the 12/3/other exit paths are untouched)
- `test` and `test-impact` are not changed (`test` must stay the bare line, AC-7 of CARD-395).
No timeout or retry was added. The lock and conftest were not touched. CLAUDE.md's Commands lines are still true ("runs everything bare"), so CLAUDE.md is not changed.

**AC-2 -- runs.** A harness (`$S/watch.sh`) starts the command in the background and samples `pmset -g assertions` every 0.3 s until the command exits. The selection is narrowed with a node id in PYTEST_ADDOPTS (a positional node id is not one of the options the wave close refuses), so `full_suite_lock.is_full_suite` is False and no lock is taken.
- `PYTEST_ADDOPTS="'tests/test_wave_close_marker.py::TestWaveCloseMarker_TheWaveCloseIsBare::test_make_test_and_the_wave_close_are_the_bare_pytest_line'" make test-wave-close`: echoes `caffeinate -i .../.venv/bin/python -m pytest`, `1 passed`, exit 0. pmset during the run: `caffeinate asserting on behalf of '.../.venv/bin/python' (pid 19208)`, PreventUserIdleSystemSleep.
- Failing control, same target with node `...::test_does_not_exist`: `ERROR: not found`, `make: *** [test-wave-close] Error 4`, exit 2. The assertion was held (pid 19249). pytest's 4 reaches make through caffeinate.
- `test-marked` with PYTEST_ADDOPTS naming one unmarked node (`tests/property/test_book_pdf_geometry.py::test_a_page_box_one_pixel_off_the_trim_reds_the_trim_assertion`): echoes `caffeinate -i .../python -m pytest -m wave_close_only`, `1 deselected`, `make: *** [test-marked] Error 5`, exit 2. The assertion was held on behalf of python (pid 19005). No marked test was run, because every marked test is a heavy sweep.
- `test-gate`: a real gate on this diff is FULL (the Makefile is unanalysable), so it was not run. Instead, the exact expanded loop line from `make -n test-gate` (`printf '%s\n' "$cmds" | { rc=0; while IFS= read -r cmd; do echo "+ $cmd"; caffeinate -i sh -c "$cmd" || rc=1; done; exit $rc; }`) was run with `cmds` set by hand. With one passing pytest node: `1 passed`, exit 0, assertion on behalf of 'sh' (pid 21700). With that node plus a not-found node: exit 1, one assertion per command (pids 21735, 21782).
- Without caffeinate: PATH=`$S/nocaf-bin:/bin:/usr/sbin:/sbin`, where nocaf-bin symlinks every `/usr/bin/*` except caffeinate (`command -v caffeinate` finds nothing). `make test-wave-close` with the passing node echoes the bare `.../python -m pytest`, `1 passed`, exit 0, and pmset shows no caffeinate assertion. With the not-found node: `Error 4`, exit 2. With `PYTEST_ADDOPTS='-k foo'`: the refusal message and exit 2, as before. `make -n` under the same PATH expands test-gate's loop to `... echo "+ $cmd";  sh -c "$cmd" || rc=1; ...` and test-marked to the bare `.../python -m pytest -m wave_close_only`. `make -n KEEPAWAKE= test-marked` gives the bare line too.

**AC-3 -- test budget.** Only existing assertions were changed: `tests/test_wave_close_marker.py::TestWaveCloseMarker_TheWaveCloseIsBare::test_make_test_and_the_wave_close_are_the_bare_pytest_line` now expects the `$(KEEPAWAKE) ` prefix on test-wave-close and test-marked. No test was added. Net test count: 0 (`--collect-only` on test_wave_close_marker.py + test_impact_set.py gives 236 before and after).
`.venv/bin/python -m pytest tests/test_wave_close_marker.py tests/test_impact_set.py -o addopts= -q`: 236 passed, exit 0. The PYTEST_ADDOPTS refusal test runs `make` with caffeinate present and passed.
