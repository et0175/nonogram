# CARD-053: Document or remove the orphaned generation/ and analysis/ packages

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/053-generation-analysis-drift
**Worktree:** —
**Source:** meta/review/20260910T170025Z.yml#F-005
**Idea:** —
**Wave:** —
**Depends on:** CARD-050
**Touches:** src/nonogram/__init__.py, src/nonogram/generation/**, src/nonogram/analysis/**, meta/architecture/domain/contexts.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`src/nonogram/generation/` and `src/nonogram/analysis/` are not mentioned in
`src/nonogram/__init__.py`'s own architecture docstring (the package's canonical
component map: `cli`, `web`, `orchestrator`, `sourcing`, `clues`, `solver`,
`difficulty`, `export` — nothing else). Grep-verified: nothing in
`cli.py`/`web/**`/`admin/**`/`orchestrator.py` imports either package; their only
importers are each other (`generation/random_generator.py` imports `analysis`)
and their own dedicated test files (`test_random_generator.py`,
`test_quality_metric.py`, `test_strategy_counter.py`).

**Note the overlap with CARD-050**: that card's AC-3 already fixes
`generation/random_generator.py`'s broken `from src.nonogram.analysis...` import
(to `from nonogram.analysis...`) as part of wiring `nonogram.analysis.quality_metric`
into real image-mode quality scoring. **Do not duplicate that fix here** — this
card is the remaining, bigger call: what happens to these two packages as a
whole, now that `analysis.quality_metric` has a real production caller (via
CARD-050) but `generation.random_generator` and `analysis.strategy_counter`
still don't.

1. Decide, and record the decision (as an ADR or a note in the existing
   architecture docstring — implementer's judgment on which fits given this
   project's current level of formality):
   - **Keep and document** `nonogram.analysis.quality_metric` (now a real
     dependency of the admin panel per CARD-050) as a proper component in
     `src/nonogram/__init__.py`'s architecture map, and in
     `meta/architecture/domain/contexts.yml` if the project's model is being
     kept current.
   - **Remove** `nonogram.generation/` (`random_generator.py`) and
     `nonogram.analysis.strategy_counter` if nothing ends up depending on them
     after CARD-050 — confirm this with a fresh grep before deleting anything,
     since CARD-050 may be implemented differently than anticipated.
2. If anything is removed, remove its dedicated tests too
   (`tests/test_random_generator.py`, `tests/test_strategy_counter.py`, and the
   parts of `tests/test_quality_metric.py` that test removed code, if any —
   `quality_metric.py` itself is expected to survive per CARD-050).
3. If `nonogram.analysis.quality_metric` is kept, confirm (after CARD-050 lands)
   that every remaining import of it in the codebase uses the `nonogram.analysis...`
   form consistently — no module should import the same file two different ways.

## Acceptance criteria

- **AC-1** — given the decision is made, when `src/nonogram/__init__.py`'s
  architecture docstring is read, then it accurately lists every package that
  actually exists under `src/nonogram/` with a real production caller — no
  component is present in code but absent from the map, and no component is
  claimed in the map but absent from code.
- **AC-2** — given whatever is kept, when the whole test suite runs, then no
  import in the codebase uses the `from src.nonogram...` style found in the
  original `random_generator.py` (grep for `from src\.nonogram` should return
  nothing after this card, whether that file survives or is deleted).

## Guardrails

- G-1: Do not touch `src/nonogram/analysis/quality_metric.py`'s own logic —
  CARD-050 owns wiring it in; this card only decides the surrounding packages'
  fate and updates documentation/tests accordingly.
