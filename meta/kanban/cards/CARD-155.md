# CARD-155: One difficulty classifier — retire the prototype's 30/70 tiers

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** CARD-138 handover and CARD-137 leftovers (backlog); code re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 29
**Depends on:** —
**Touches:** src/nonogram/analysis/strategy_counter.py, src/nonogram/analysis/__init__.py, src/nonogram/difficulty.py, tests/test_difficulty_tiers.py, tests/test_strategy_counter.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

ADR-0031/R1 says `difficulty.classify` is the only place a score becomes a tier.
`src/nonogram/analysis/strategy_counter.py:137-142` has a second
easy/medium/hard mapping on bare `30` and `70` literals, inside
`calculate_difficulty_from_strategies`.

The AST guard in `tests/test_difficulty_tiers.py` (:447, `_CUTOFF_NAMES`) only
recognises the cutoff **names** `EASY_MAX_SCORE` and `MEDIUM_MAX_SCORE`, so it
can't see a literal. It also doesn't know CARD-137's newer cutoff names
(`RUNG_OVERLAP_MAX_SCORE` and its siblings in `difficulty.py`).

Today nothing in production calls `calculate_difficulty_from_strategies`. It is
exported from `nonogram.analysis` and used only by `tests/test_strategy_counter.py`.
So the second classifier is dormant, not live. It's one import away from
becoming a second source of truth, and the guard wouldn't notice.

Also from CARD-137: `difficulty.py`'s docstring still has the retired "fourth
tier" section, with an example `classify(score, branch_nodes)` that raises
`TypeError`.

## What to do

1. Remove the tier output from `calculate_difficulty_from_strategies` (return the
   score only), or delete the prototype function if nothing needs it. Check
   `src/nonogram/__init__.py`'s package docstring, which mentions it.
   **Don't** route its score through `classify`: its 0-100 scale is not the
   solver score `classify` expects.
2. Add the CARD-137 cutoff names to `_CUTOFF_NAMES`, and extend the guard so a
   string literal `"Easy"`/`"Medium"`/`"Hard"` assigned outside `difficulty.py`
   fails it. Use a narrow rule: catching tier strings is enough, numeric literals
   are too noisy.
3. Remove the stale "fourth tier" section from `difficulty.py`'s docstring.

## Acceptance criteria

- **AC-1:** No module outside `difficulty.py` maps a score to a tier name.
  *test: the extended guard in tests/test_difficulty_tiers.py*
- **AC-2:** The guard fails if the old 30/70 mapping is put back in
  `strategy_counter.py` (checked by temporarily restoring it).
  *test: the extended guard*

## Guardrails

- G-1: No stored puzzle's tier changes, and `classify` and its cutoffs are untouched.
- G-2: The capability-module import guard in `tests/test_cli.py` stays green.

## Architecture context

- **ADR:** ADR-0031/R1 (one classifier)
- **Components:** COMP-006
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Why P3] Dormant code: no production caller today. It's cheap to remove now and
  easy to reintroduce by accident later.
