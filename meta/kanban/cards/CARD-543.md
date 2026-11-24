# CARD-543: The public-mode mutant matrix's clean control survives a loaded machine

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
**Source:** roadmap wave 19, cut 2026-11-24 on the owner's "card both" (the two proposals recorded at the Wave 18 close).
**Idea:** —
**Wave:** 98
**Created wave:** 98
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_player_public_mode.py
**UI surface:** —
**Review score:** —
**Started:** —
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
