# CARD-505: Three test-instrument costs: the wave-3 stub tests, the Makefile's PY default, the fifth-rule capture settle

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/505-test-instrument-costs
**Worktree:** —
**Source:** roadmap wave 6 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-172, IDEA-194, IDEA-208 (WSJF 2.31 each).
**Idea:** IDEA-172, IDEA-194, IDEA-208
**Wave:** 85
**Created wave:** 85
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_wave3_image_generation.py, tests/test_wave3_e2e.py, Makefile, CLAUDE.md, tests/test_puzzle_solver_fifth_rule.py
**UI surface:** —
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-172.** Test functions whose body is only a docstring and `pass` carry no evidence but count as passes (or skips). Re-read 2026-11-20: tests/test_wave3_image_generation.py has 22 bare `pass` lines over fixtures `client` and `batch_generator_service`; tests/test_wave3_e2e.py has none now (the idea said 4, so that half may be closed). Whether these hold a DB fixture (and so sit in the 29-skip unarmed baseline) is unmeasured.
2. **IDEA-194.** Makefile `PY ?= ./.venv/bin/python`, which no card worktree has, so `make impact-set` / `make test-impact` / `make test-gate` exit 127 there unless `PY=` is passed. Still so on 2026-11-20.
3. **IDEA-208.** tests/test_puzzle_solver_fifth_rule.py `_quiet` waits `4 * _RESIZE_SETTLE` and then reads the draw count once; measured at CARD-271 to double the file's wall-clock (27.35 s vs about 13.4 s). Polling the draw count until it is stable is the deterministic cheaper shape.

## What to implement

Re-verify each first (ast for the stubs); drop any already closed with one line.

1. Delete the stub tests that assert nothing (owner's "fewer tests"); keep any that asserts something. Report which, and whether any was in the unarmed skip baseline. If the baseline moves, say the new figure and its reasons; the orchestrator updates the memory note.
2. The Makefile's PY default works from a card worktree (e.g. fall back to the main checkout's venv, found via `git rev-parse --git-common-dir`), and still prefers `./.venv/bin/python` where it exists. Update CLAUDE.md's "pass PY=" sentence to match.
3. `_quiet` polls the draw count until two reads agree (bounded), with no fixed `4 *` settle; measure the file's wall-clock before and after (three runs each).

## Acceptance criteria

* **AC-1**: no test function under tests/ whose body is only a docstring/`pass` (ast count before and after reported).
* **AC-2**: `make -n test-gate` from a card worktree with no PY resolves to an existing interpreter; from main it still names ./.venv/bin/python.
* **AC-3**: the fifth-rule file is green 3 runs in a row and faster (figures); control: a poll that returns after one read lets a planted late redraw through, or the existing assertions red under a planted too-early read (show one).
* **AC-4**: net test count reported (it goes down by the stubs deleted).

## Guardrails

* **G-1**: the Makefile change must not alter what `make test-gate` / `make test-wave-close` select or run; compare `make -n` output before and after from main.
* **G-2**: a deleted test is listed by node id in the notes.

## Worktree notes
