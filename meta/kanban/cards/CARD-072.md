# CARD-072: Record the solving strategies a puzzle needs and save them with the puzzle

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/072-record-solving-strategies
**Worktree:** —
**Source:** owner request 2026-09-12 ("save the strategies needed for solving together with the puzzle"), plus docs/GENERATION_ALGORITHM.md §6-§7; follow-up card, not decomposed from handoff.md
**Idea:** —
**Wave:** —
**Depends on:** CARD-073, CARD-076
**Touches:** src/nonogram/solver/search.py, src/nonogram/solver/propagate.py, src/nonogram/orchestrator.py (Puzzle aggregate, judge_candidate, record_candidate), src/nonogram/export/__init__.py, src/nonogram/export/json_export.py, src/nonogram/web/metadata.py, src/nonogram/admin/batch_generator.py, src/nonogram/admin/app.py, src/nonogram/admin/puzzle_review.py, src/nonogram/admin/templates/** (detail + list filter), tests/property/test_export_roundtrip.py, tests/test_solver.py or a new tests/test_solver_strategies.py, tests/property/test_solver_strategies.py (new), tests/test_batch_generator.py, tests/test_puzzle_review.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

A puzzle book needs to say what a solver must know to finish a puzzle, and
the admin review needs to filter on it. Today the pieces exist but nothing
connects them:

- The DB column `strategies_used` exists (`src/nonogram/db/models.py:63`,
  JSON, nullable) but is written as `[]` for random batches
  (`src/nonogram/admin/batch_generator.py:346`) and for image batches
  (`src/nonogram/admin/app.py:476`), and as a hardcoded sample
  `['LineLogic', 'ConstraintProp']` at
  `src/nonogram/admin/puzzle_review.py:730`.
- The JSON export (`src/nonogram/export/__init__.py`, `ExportPayload`
  at L95-146) carries no strategies at all.
- The only taxonomy in the repo, the `Strategy` enum in
  `src/nonogram/analysis/strategy_counter.py`, belongs to the orphaned
  `analysis/` package (CARD-053 may delete it) and is never fed by the
  real solver.

The real solver (`src/nonogram/solver/`) reasons with one placement DP per
line (`line_intersection`), a fixed-point sweep, probing, and branching
(`docs/GENERATION_ALGORITHM.md` §6-§7). So the strategies a puzzle needs
must be *derived from that solve*, not from a second solver.

**Sequencing (updated 2026-09-12 by the Increment 8..12 decompose).**
This card is **Increment 10's delivery card for FR-029** (persistence,
export and admin display of the strategies list — see
`meta/architecture/handoff.md#increment-10`; the scoring/tier half is
CARD-076 and the DB re-grade is CARD-077). The decision that gated item 1
has landed: ADR-0025 (DEC-030 — "requires guessing" is a fourth tier
`guess`, keyed on `branch_nodes >= 1`) and ADR-0029 (DEC-031 — the
strategy ladder `simple_overlap` < `line_dp` < `cross_line` <
`probe_contradiction`) confirm the provisional taxonomy below as the
decided one (FR-029's `enum_provisional` note is closed by CARD-076).
Item 1 is therefore **unblocked**, but it now **depends on CARD-073
landing first**: that card puts the per-cell rung tags, the per-rung
counts and the ordered rung list on `SolveSignals` (ADR-0029/R2), so item
1 shrinks to reading that ordered list and appending `guess` iff
`branch_nodes > 0` (EC-017) — no second classifier in this card. Item 1
also follows CARD-076 so that the tier value `guess` and the strategy
`guess` derive from the same fact through the one classifier
(ADR-0025/R2). Items 2-4 (storage, export, display) can start once
CARD-073 is merged; they no longer need a provisional enum. Export
ordering with the other wave-2 schema touches: CARD-076 (`difficulty` may
be `guess`) -> this card (`strategies`) -> CARD-079 (`binarisation`).
Rules now binding on this card: ADR-0029/R2 (one derivation from the one
verifying solve — AC-135 is its check), ADR-0029/R3 / CON-014 (no clock
in the list — EC-018), ADR-0029/R4 (no `clues.py` import in the solver),
ADR-0025/R1 (`guess` present iff branched).

## What to implement

1. **Solver telemetry** (COMP-005, `SolveSignals` in
   `src/nonogram/solver/search.py:197-248`): report, for the deciding
   solve, which strategies were required, as an ordered list drawn from a
   fixed enum. Taxonomy confirmed by ADR-0029 (2026-09-12); the rung tags
   and the ordered rung list are delivered by CARD-073 — this item consumes
   them and appends `guess`:
   - `simple_overlap` — a deduction the leftmost/rightmost overlap rule
     alone yields;
   - `line_dp` — a deduction only the full placement intersection yields;
   - `cross_line` — a deduction that needed cells fed from perpendicular
     lines, i.e. any sweep after the first;
   - `probe_contradiction` — a value forced because its opposite
     contradicted;
   - `guess` — a real branch.

   Classification must be computed from the same solve, never by
   re-solving (ADR-0013's "no solver re-entry" rule, `difficulty.py:7-12`).
   Overlap-vs-DP classification: for a line deduction, re-derive the
   simple overlap masks natively (sum of runs + gaps vs length) and
   compare — a native reimplementation, no import of `clues.py`
   (ADR-0007 lateral-import rule, enforced by `tests/test_cli.py`; see
   `solver/propagate.py`'s `mask_runs` for the precedent).
2. **Aggregate:** expose `Puzzle.strategies` (`tuple[str, ...]`) on the
   orchestrator aggregate, recorded in `judge_candidate` off
   `verdict.signals` alongside `difficulty_score`
   (`src/nonogram/orchestrator.py:1167-1198`), and reset by
   `record_candidate` the same way the score is (`orchestrator.py:654-670`).
3. **Persistence + export:** `puzzle_review.add_puzzle(strategies_used=...)`
   receives the real list for random AND image batches
   (`batch_generator.py:335-346` and `app.py:465-476`); remove the
   hardcoded sample at `puzzle_review.py:730`; add `strategies` to
   `ExportPayload` and to the JSON export
   (`src/nonogram/export/json_export.py`). CSV/PDF unchanged unless the
   addition is trivial. Web metadata (`src/nonogram/web/metadata.py`)
   shows it only if it already shows difficulty.
4. **Admin display:** show the strategies on the puzzle detail/review
   page and allow filtering the puzzle list by strategy — reuse the
   CARD-066 status-filter pattern (route param pinned to the enum, error
   branch, template select).

## Acceptance criteria

- **AC-1** — A puzzle solved by line logic in one sweep reports exactly
  the line strategies used and no `cross_line` / `probe_contradiction` /
  `guess`; a puzzle whose solve branched reports `guess`. A
  property-style test over a seeded corpus (stdlib `random.Random`,
  minimum case count asserted in the test, no hypothesis) checks:
  `guess` in strategies iff `branch_nodes > 0`.
- **AC-2** — `strategies` is deterministic for a given clue set (same
  clues → same list), independent of wall-clock.
- **AC-3** — JSON export of a generated puzzle contains a `strategies`
  array; round-trip test in the style of
  `tests/property/test_export_roundtrip.py`.
- **AC-4** — Admin: a random batch stores non-empty `strategies_used` for
  every puzzle; the puzzle list filters by strategy; the hardcoded sample
  at `puzzle_review.py:730` is gone.
- **AC-5** — No change to the solver's verdicts:
  `tests/property/test_solver_uniqueness.py` and `tests/test_solver.py`
  unchanged and passing; solve time on the 20x20 benchmark
  (`tests/bench_generate.py`) within noise.

## Guardrails

- G-1: Never re-run the search to classify — strategies come from the
  one deciding solve (ADR-0013 no-re-entry rule).
- G-2: Never import across capability modules; the enum lives in the
  solver (or a new import-free shared module next to `errors.py` /
  `limits.py`) — not in `analysis/strategy_counter.py`, which CARD-053
  may delete. `tests/test_cli.py`'s structural guard must stay green.
- G-3: Solver verdicts (`count`, `solution`) are untouched; the oracle in
  `tests/helpers/brute_force_oracle.py` is not edited.
- G-4: DB migration must keep existing rows valid — the column is already
  nullable; no NOT NULL, no backfill that rewrites accepted puzzles.
- G-5: Do not start item 1 before CARD-073 (rung tags on
  `SolveSignals`) and CARD-076 (the `(score, branch_nodes)` classifier)
  are merged; the enum members are the ADR-0029 ones — do not invent a
  second taxonomy or a second `guess` derivation (ADR-0025/R2,
  ADR-0029/R2).
- G-6: Commit only your own files — the working tree carries a large
  standing set of unrelated staged/untracked changes; use explicit
  pathspecs.

## Worktree notes

—
