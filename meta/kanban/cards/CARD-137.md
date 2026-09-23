# CARD-137: Recalibrate the medium/hard cutoff so medium is reachable

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/137-recalibrate-medium-cutoff
**Worktree:** ../PythonProject4-CARD-137
**Source:** owner, 2026-09-23 (5 medium puzzles in 300 on production)
**Idea:** —
**Wave:** 24
**Depends on:** —
**Touches:** src/nonogram/difficulty.py, tests/test_difficulty_tiers.py, tests/property/test_difficulty_calibration.py, docs/GENERATION_ALGORITHM.md
**Review score:** —
**Started:** 2026-09-23T06:21:22Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Medium is effectively unreachable. The tier is defined as "needed line deduction but
**no** probe at all", and in random grids a single probe anywhere promotes the whole
puzzle to hard — the owner measures 5 medium in 300 production puzzles; the local DB
shows 10 easy / 2 medium / 9 hard, with the hard scores spread 67..99.

That spread is the opening. `score = band_low(rung) + share * band_width(rung)` already
measures **how much** of the grid needed the hardest rung, so a 67 (one probe in an
otherwise line-solvable grid) and a 99 (probing nearly everywhere) are different puzzles
wearing one label. ADR-0005's two cutoff constants are the recalibration the module's own
docstring says is owed.

Owner decision (2026-09-23): keep three tiers; move the medium/hard boundary so **medium
= needed a little non-trivial work, hard = needed a lot**. Not a new signal, not a
removed tier.

**Step 1 — measure, then STOP.** Build a seeded corpus with the existing generator
across the supported size range and densities (no new solver entry point; score what the
one verifying solve already measured). Report, for candidate medium/hard cutoffs (at
least 75 / 80 / 85 / 90), the resulting easy / medium / hard shares overall and per
longest-side bucket (<=15, 16-20, 21-25, 26-30 — the book's own buckets, FR-034). Hand
that table back to the dispatcher and **do not pick the constant yourself**: the owner
chooses, against the 40/40/20 default plan.

**Step 2 — apply the chosen cutoff.** One constant in `src/nonogram/difficulty.py`
(`classify` stays the single classifier — the AST guard in tests/test_difficulty_tiers.py
must stay green). Update the module docstring's band arithmetic, the tier tests, and
`docs/GENERATION_ALGORITHM.md`. Regrading stored puzzles is the panel's existing
`POST /regrade` action — do not write a migration, and do not run it against the owner's
database.

## Acceptance criteria

- New: with the chosen cutoff, a seeded corpus of at least 200 line-solvable puzzles
  classifies into all three tiers, and medium holds at least 20% of them.
  test: TestDifficulty_MediumIsReachableOnASeededCorpus
- New: the tier of a puzzle is monotone in its score — no score classifies harder than a
  higher score (ADR-0029/R1 cross-rung monotonicity is unchanged).
  test: PropertyTest_Difficulty_TierIsMonotoneInScore
- Unchanged: `Tier.GUESS` is still keyed on `branch_nodes > 0`, never on a threshold
  (EC-015), and easy/medium/hard still contain only line-solvable puzzles.
  test: existing tests/test_difficulty_tiers.py (must stay green unmodified except for
  the cutoff figure itself)

## Guardrails

- G-1: `classify` remains the ONLY place a score is compared against the cutoffs; the
  AST walk in tests/test_difficulty_tiers.py must keep passing.
- G-2: No solver re-entry, no clock, no size, no density in the grade (NFR-007, CON-014,
  ADR-0029/R3). Scoring still reads only what the verifying solve measured.
- G-3: Do not edit `src/nonogram/export/**`, `src/nonogram/admin/**`, or
  `tests/fixtures/a4_golden/**`. The book pipeline reads the tier and must not care.
- G-4: No database migration, and no write to the owner's database.

## Architecture context

- **FR:** FR-026
- **NFR:** NFR-007
- **CON:** CON-014
- **ADR:** ADR-0005 (the two cutoff constants), ADR-0029 (strategy ladder), ADR-0031
  (three tiers), ADR-0025 (GUESS)
- **Components:** COMP-006
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner, 2026-09-23: "it's really difficult to generate a puzzle with medium
  difficulty — from 300 puzzles on prod only 5 are medium. Maybe we remove medium, or
  redefine it as only one of not trivial strategies applied". Removing the tier was
  rejected: the plan matrix, stored plans, the readiness gate, level order, dividers and
  the answer-key headings all assume three levels and are merged, and a two-level book
  drops the beginner-to-expert promise.
- [Architect] ADR-0005/ADR-0029/ADR-0031 need the new reading written back once the
  cutoff is chosen — queued in inputs/raw-requirements.md, not done in the worktree.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)
