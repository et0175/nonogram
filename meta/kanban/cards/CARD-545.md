# CARD-545: The merge gate and the wave close keep the Mac awake while they run

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap wave 20, cut 2026-11-25 on the owner's "card the caffeinate change" (proposed at the Wave 19 close).
**Idea:** —
**Wave:** 99
**Created wave:** 99
**Deferred waves:** 0
**Depends on:** —
**Touches:** Makefile, tests/test_wave_close_marker.py (only if a Makefile assertion there needs the new form), CLAUDE.md (only the Commands section's one line on the gate/close targets, if the run form changes what it says)
**UI surface:** —
**Review score:** —
**Started:** —
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
