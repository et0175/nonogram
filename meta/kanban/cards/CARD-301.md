# CARD-301: NFR-001's 5-second p95 gate has never run — `bench_generate.py` is not a file pytest opens, and its docstring says it is

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/301-the-bench-file-pytest-never-opens
**Worktree:** —
**Source:** orchestrator, 2026-10-25, from CARD-294's fix round 1. The guard that round built for its own critical finding (`tests/test_collected_names.py`) found a **second instance of the same family on the day it was written**, in a file belonging to no card. Independently re-measured by the orchestrator before this card was cut.
**Idea:** —
**Wave:** —
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/bench_generate.py, meta/architecture/requirements.yml, tests/test_collected_names.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this is P1

**A performance requirement has been reading as verified while its verifier has
never executed once.**

`tests/bench_generate.py` declares three module-level `test_*` functions, one of
them the verifier for **NFR-001/AC-037** — the 5-second p95 generation bound. Its
own docstring states that it *"runs inside `pytest -q` with the rest of the
suite"*. It does not. Measured twice, independently:

- the fix round: a bare `pytest --collect-only` from the repo root collects
  **9,224** tests and **none** is in that file;
- the orchestrator, separately: `pytest --collect-only -q | grep -c bench_generate`
  = **0**.

The cause is the same one that produced CARD-294's cycle-1 critical finding, one
level over: pytest's `python_files` default is `test_*.py`/`*_test.py`, and
`bench_generate.py` matches neither. `pyproject.toml`'s
`[tool.pytest.ini_options]` sets only `testpaths` and `addopts`, so the default
applies. CARD-294's cycle 1 only ran the file by naming it on the command line,
which is exactly how a file like this stays invisible: every deliberate
invocation works, and the suite never touches it.

**This is the same defect class as CARD-294's F-1 and it is worth saying plainly:
one card's guard found another card's hole within hours of existing.** That is the
argument for the guard, and this card is the first thing it caught.

## What to implement

1. **Decide where AC-037's verifier lives, and make it run.** The two routes are
   not equivalent and the choice is the card's real content:
   - rename the file to a `test_*.py` spelling so the suite collects it — but
     note this touches the **frozen render-set snapshot** that CARD-294's G-7 and
     `tests/test_suite_profile.py` reason about, and it adds a benchmark's wall
     clock to every full-suite run, which this board has spent three cards
     cheapening (CARD-218, CARD-219, CARD-287);
   - or move AC-037's assertion into a file the suite already opens and leave
     the bench script as a deliberate standalone, keeping its three functions as
     a profiling entry point.
   The second is probably right — a p95 benchmark inside the gate is a flaky gate
   — but **measure the suite-cost consequence of the first before declining it**,
   because "probably right" is how this board gets claims wider than their
   controls.
2. **Correct the docstring either way.** It currently asserts a falsehood about
   its own execution, which is the class of defect `TestGuardProse_*` exists to
   catch and which four cards have now been gated on.
3. **Re-check the other two functions in the file.** Only AC-037 was traced; the
   other two may verify nothing anybody claims, in which case say so rather than
   preserving them by default.
4. **Unpin it from the guard.** `tests/test_collected_names.py::…::test_the_files_pytest_never_opens_are_the_two_known_ones`
   currently pins `tests/bench_generate.py` (with `tests/integration_tests.py`, a
   standalone script by design) **with its reason**. When this card resolves the
   file, that pin must shrink to one entry in the same commit — a pin outliving
   its hole is the declaration-outliving-its-hole defect, and this board has
   gated on it repeatedly.

## Acceptance criteria

- **AC-1** (the requirement's verifier executes): *Given* a bare `pytest` run
  from the repo root with no file named on the command line, *then* NFR-001/AC-037's
  verifier is collected and runs, **or** AC-037's `test:` names a different
  verifier that is. (test: a `--collect-only` assertion naming the resolved node
  id; the existing `test_collected_names.py` guard must agree.)
- **AC-2** (the pin shrinks with the hole): *Given* the resolution, *then*
  `test_the_files_pytest_never_opens_are_the_two_known_ones` holds **one**
  entry, changed in the same commit as the mechanism, and still **reds** when a
  third uncollected file is planted. (test: the named test plus its mutation.)
- **AC-3** (the docstring stops lying): *Given* the file as it ships, *then* no
  docstring in it claims an execution context it does not have. (test:
  `TestGuardProse_EveryNamedControlExists`' family, or a named successor.)
- **AC-4** (the suite cost is measured, not assumed): *Given* whichever route is
  taken, *then* the decision records the benchmark's wall clock and what adding
  it to every full-suite run would cost, measured rather than estimated — and if
  the route declines collection, that figure is the reason. (**gate**: the
  measurement on the card.)

## Guardrails

- G-1: **No production behaviour change.** `git diff --name-only main...HEAD -- src/`
  must be empty. This card changes what runs, never what the generator does.
- G-2: Do not change `pyproject.toml`'s `python_files`/`python_classes` to make
  this file collect. Widening the global pattern to catch one file would pull in
  every other non-test module under `testpaths` and is the blunt instrument this
  board would have to undo later; CARD-294's guard reads pytest's **effective**
  patterns, so it would silently follow the widening rather than object to it.
- G-3: No new runtime dependency (ADR-0006/R1); stdlib + Pillow + NumPy.
- G-4: Do not weaken `tests/test_collected_names.py`'s default-deny rule or its
  5,000-name floor to accommodate this file. The pin is the designed route.

## Architecture context

- **NFR:** NFR-001 (AC-037, the 5 s p95 bound; note AC-038 beside it is already
  `status: superseded` because 50×50 became invalid at `MAX_SIZE=30`)
- **ADR:** ADR-0039 (R1 controls that can fail, R2 default-deny)
- **Components:** COMP-002
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
