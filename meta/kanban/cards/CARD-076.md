# CARD-076: Difficulty by strategy ladder and the Guess tier — no clock, no size, one classifier

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/076-strategy-ladder-guess-tier
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-10 (scoring + tier half; FR-029 persistence/export/admin is CARD-072, the DB re-grade is CARD-077)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-073
**Touches:** src/nonogram/difficulty.py (rewrite), src/nonogram/orchestrator.py (Puzzle.difficulty_tier / difficulty_in_requested_tier / record_difficulty go through the one classifier; generate_batch tier validation), src/nonogram/cli.py (--difficulty help lists four tiers), src/nonogram/web/pages.py (tier options from the enum — already enum-driven, verify), src/nonogram/export/__init__.py, src/nonogram/export/json_export.py, src/nonogram/export/csv_export.py (difficulty may be "guess"; SCHEMA_VERSION bump per ADR-0023/R2 if a reader would reject it), src/nonogram/admin/templates/puzzles_list.html (tier badge for Guess), src/nonogram/admin/image_to_puzzle.py (retire the private tier derivation, ADR-0025/R2), tests/test_difficulty.py (rewrite), tests/test_difficulty_tiers.py, tests/property/test_difficulty_ladder.py (new), tests/test_resample.py, tests/test_cli.py, tests/test_export_json.py, tests/test_export_csv.py, docs/GENERATION_ALGORITHM.md (§7 rewrite, §10.2 finding 3), meta/architecture/requirements.yml (AC-020/AC-022/AC-023 re-wording), meta/architecture/decisions/adr/0013-*.md (Superseded stamp already present — verify), 0005-*.md, 0015-*.md, 0023-*.md (History entries), meta/architecture/decisions/resolved.yml (DEC-013 superseded note)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Under ADR-0013 a puzzle solved by line logic alone scores <= 15 whatever
its depth (`difficulty.py` proves it by construction), so a printed-book
"Hard" today means "needs guessing" — the opposite of what a book wants —
and the `time_pressure` term (weight 0.15) makes the same seed classify
differently on a slower host (§10.2 finding 3), breaking ADR-0015 under
`--difficulty`. Two owner decisions replace this: ADR-0025 (DEC-030) makes
"requires guessing" a fourth tier `guess` keyed on `branch_nodes >= 1`, so
Easy/Medium/Hard contain only line-solvable puzzles; ADR-0029 (DEC-031)
grades line-solvable puzzles by the rung of the hardest technique the one
verifying solve required — the rung tags CARD-073 emits — with no clock,
size or density term (NFR-007, CON-014). ADR-0013 is retired.

**Sequencing.** After CARD-073 (rung tags and per-rung counts on
`SolveSignals`). Parallel with CARD-074 possible (shared file:
`orchestrator.py`, disjoint regions — conflict-graph matter). CARD-077 (DB
re-grade) and CARD-072 item 1 wait on this card. Precedes CARD-079 so the
export schema is touched in order (guess value here, `strategies` in
CARD-072, `binarisation` in CARD-079).

## What to implement

1. **`difficulty.py` rewrite (COMP-006).** Score = band start of the
   hardest rung present + 25 x share of cells settled at that rung
   (ADR-0029: `simple_overlap` 0..25, `line_dp` 25..50, `cross_line`
   50..75, `probe_contradiction` 75..100; share = cells settled at the top
   rung / total cells). Pure function of the rung counts and
   `branch_nodes` — `elapsed_seconds`, size and density never enter
   (ADR-0029/R3, CON-014). Retire `SignalWeights`, `SIGNAL_WEIGHTS`,
   `NormalizedSignals`, `clue_density`, `SECONDS_PER_CELL_BUDGET`,
   `HARDEST_DENSITY`. The `SolverSignals` protocol gains the per-rung
   members; the module still never imports the solver (ADR-0007).
2. **`Tier` gains `GUESS`** (value `guess`, label "Guess"). The single
   classifier `classify(score, branch_nodes)` lives in `difficulty.py`:
   EC-015 first (`branch_nodes > 0` -> `Tier.GUESS`), then the 33/66
   bands on the remainder (ADR-0025/R1). `tier_for_score(score)` alone can
   no longer classify a result — remove it or make it the band-only helper
   the classifier calls, never called by anyone else. Cutoffs
   `EASY_MAX_SCORE`/`MEDIUM_MAX_SCORE` stay 33/66 (ADR-0005 revised, not
   re-drawn; the tier-per-rung recalibration is OWED after AC-118's
   corpus — record the distribution, do not retune here).
   `parse_tier` and its error message (AC-021) list four tiers.
3. **Orchestrator (COMP-002).** `Puzzle.difficulty_tier`,
   `difficulty_in_requested_tier` and `record_difficulty` go through the
   one classifier with `(score, branch_nodes)` from the verifying solve's
   signals — no module derives a tier on its own (ADR-0025/R2). POL-004
   stays a single tier test: requesting `guess` is a legitimate request the
   resample loop can satisfy. `generate_batch`'s tier validation (CARD-070)
   accepts the fourth value.
4. **Every `Tier` consumer handles the fourth member** (ADR-0025
   Negative): CLI `--difficulty` help and exit-code tests; web form options
   (already `list(difficulty.Tier)` — verify and pin); export `difficulty`
   may be `"guess"` (ADR-0023: bump `SCHEMA_VERSION` only if an existing
   reader could not survive — a reader parsing through `Tier(...)` on the
   old enum would reject it, so likely yes; JSON and CSV together,
   ADR-0023/R2 exact-version rule); ADR-0016 filename `<name>-guess.pdf`
   (DEC-026's held `<name>-<WxH>-<difficulty>.pdf` gains the same fourth
   value — note it on DEC-026, do not resolve it); admin badge colour for
   `Guess` in `puzzles_list.html`; `admin/image_to_puzzle.py:114-121`'s
   private size-based tier derivation and hardcoded `strategies_used`
   sample violate ADR-0025/R2 — retire the function or route it through
   the classifier (CARD-049 already routes admin image generation through
   the pipeline; confirm it is dead and delete, else fix).
5. **Docs and registry follow-ups named by the ADRs:**
   - `docs/GENERATION_ALGORITHM.md` §7 rewritten around rungs and the
     Guess tier; §10.2 finding 3 marked closed.
   - `requirements.yml`: AC-020 re-worded (four tiers), AC-022 and AC-023
     superseded by AC-118/AC-119 with a dated note (FR-003/AC-009
     convention — id kept, `superseded_by` noted, test name not reused);
     FR-029's `enum_provisional` note closed (members confirmed).
   - ADR-0005 revision note (bands now sit over rungs; recalibration
     owed), ADR-0015 History (reproducibility now holds with
     `--difficulty`), ADR-0023 History (difficulty value set grows;
     version bump if taken). ADR-0013 already carries the Superseded
     stamp — verify; mark DEC-013 superseded in `resolved.yml`.
     History/notes only — no Decision text rewritten.
6. **Calibration input (AC-118):** a 200-puzzle seeded line-solvable corpus
   (10x10..30x30) graded, its tier distribution and per-rung counts written
   to Worktree notes — the input for the owed tier-per-rung recalibration.
7. `tests/bench_generate.py` at 20x20 within noise (the resample loop
   scores every candidate).

## Acceptance criteria

- **AC-118** — given a seeded corpus of >= 200 line-solvable puzzles
  (count 1, branch_nodes 0) spanning 10x10..30x30, when each is scored,
  then at least one scores inside each of Easy, Medium and Hard.
  *test:* `TestScoreDifficulty_LineSolvableCorpusSpansAllThreeBands`
- **AC-119** — given two line-solvable 20x20 puzzles A (2 sweeps, 90%
  decided first sweep) and B (12 sweeps, 20% first sweep), when scored,
  then B's score is strictly greater than A's. Cover the same-top-rung
  tiebreak too (ADR-0029 Negative).
  *test:* `TestScoreDifficulty_DeeperLineReasoningScoresHigher`
- **AC-120** — given a puzzle whose solve branched (branch_nodes >= 1),
  when scored, then its tier is `Tier.GUESS`.
  *test:* `TestScoreDifficulty_RequiresGuessingAttributeSetWhenSearchBranched`
- **AC-121** — given a puzzle solved with branch_nodes 0, when scored, then
  its tier is never `Tier.GUESS`, whatever band its depth places it in.
  *test:* `TestScoreDifficulty_RequiresGuessingAttributeClearForLineSolvable`
- **AC-122** (NFR-007) — given two signal records identical except
  elapsed_seconds 0.001s and 4.9s, when scored, then the scores are equal
  to the last digit.
  *test:* `TestScoreDifficulty_IgnoresElapsedSeconds`
- **AC-123** (NFR-007) — given seed 42, 20x20, density 40, `--difficulty
  Medium`, run twice with an injected clock at 1x and 50x, then both runs
  return the same grid and the same resample attempt count.
  *test:* `TestResample_SameSeedSameTierUnderDilatedClock`
- **AC-020 (re-worded)** / **AC-021** — `--difficulty guess` is accepted;
  `Extreme` is rejected with a message naming the four tiers.
  *tests:* `TestSelectDifficulty_AcceptsValidTier`,
  `TestSelectDifficulty_RejectsUnknownTier`
- **AC-A** (handoff checkpoint) — `nonogram generate --mode random --size
  20 --density 25 --difficulty hard --seed 7` returns a puzzle that never
  branched, with an identical score and tier under a dilated clock.
  *test:* `TestGenerate_HardTierIsLineSolvableAndMachineIndependent`
- **AC-B** — export round-trip of a `guess`-tier puzzle in JSON and CSV
  (EC-002 style); the old schema version is refused if bumped
  (`TestExport_RejectsSupersededSchemaVersion` re-pinned).
  *test:* `TestExport_RoundTripsGuessTier`

## Engineering constraints

- **EC-015** — For any uniquely solvable puzzle, the tier is `guess` iff
  the verifying solve's branch_nodes > 0 — a fact about the solve, never a
  threshold on the score. Seeded corpus, minimum case count asserted.
  *test:* `PropertyTest_ScoreDifficulty_RequiresGuessingIffSearchBranched`
- **EC-016** — For any two signal records that differ only in
  elapsed_seconds, `score_difficulty` returns the same score and the tier
  decision is the same — every extent, clue set and elapsed value.
  *test:* `PropertyTest_ScoreDifficulty_IndependentOfElapsedTime` (this is
  CON-014's declared check — it flips CON-014 to `covered`)
- **EC(ADR-0029/R1)** — for line-solvable puzzles of the same extent, the
  score is monotone in ladder order: any puzzle topping out at a higher
  rung scores strictly above any puzzle topping out at a lower one, and
  within a rung the order follows the settled-cell share.
  *test:* `PropertyTest_ScoreDifficulty_MonotoneInRungOrder`
- **EC(ADR-0025/R2)** — exactly one tier classifier exists, in
  `difficulty.py`; no other module under `src/nonogram/**` compares a score
  against `EASY_MAX_SCORE`/`MEDIUM_MAX_SCORE` or derives a tier from
  `branch_nodes` (ast walk, same style as `tests/test_cli.py`'s import guard).
  *test:* `test_no_module_but_difficulty_classifies_a_tier`

## Guardrails

- G-1: The scorer never re-enters the solver — no `solve` call, no
  re-propagation, in `difficulty.py` or in the orchestrator's scoring path
  (ADR-0029/R2, ADR-0013's carried-forward rule).
- G-2: No clock, size or density term in the score, the tier decision or
  anything feeding POL-004 (ADR-0029/R3, CON-014, NFR-007).
- G-3: No lateral imports — `difficulty.py` never imports `solver`; the
  protocol grows instead (ADR-0007; test_every_import_in_the_package_points_inward).
- G-4: No edits under `src/nonogram/solver/` — the rung definitions and
  tags are CARD-073's; if a tag is wrong, stop and note it, do not patch
  the solver here. The oracle and `tests/property/test_solver_uniqueness.py`
  untouched.
- G-5: Cutoffs stay 33/66 (ADR-0005 revised, not re-drawn); the
  tier-per-rung recalibration is recorded as owed with the AC-118
  distribution, not done.
- G-6: Do not write `strategies_used`, the JSON `strategies` array or the
  admin strategy filter — CARD-072's scope. Do not re-grade stored rows —
  CARD-077's scope; stored `difficulty_score`/`difficulty_tier` are left as
  they are by this card.
- G-7: Do not touch the random-mode recovery loop (CARD-074) or the nudge
  (CARD-075); `orchestrator.py` edits limited to the tier/score path and
  `generate_batch` validation.
- G-8: ADR-0005/0015/0023 edits are History/revision notes; ADR-0013's
  Decision text is not rewritten; DEC-026 is annotated, not resolved.
- G-9: Commit only your own files — explicit pathspecs
  (`nonogram_admin.db`, `*.pdf`, `egg-info` are standing noise).

## System contract

- ADR-0025/R1 — branch_nodes > 0 -> Tier.GUESS; branch_nodes == 0 never
  GUESS; Easy/Medium/Hard contain only line-solvable puzzles (check:
  PropertyTest_ScoreDifficulty_RequiresGuessingIffSearchBranched)
- ADR-0025/R2 — exactly one tier classifier, in difficulty.py, taking
  (score, branch_nodes) (check: test_no_module_but_difficulty_classifies_a_tier)
- ADR-0029/R1 — score derived from the hardest rung present and the share
  settled at it; deeper scores strictly higher; corpus spans every band
  (check: TestScoreDifficulty_DeeperLineReasoningScoresHigher,
  TestScoreDifficulty_LineSolvableCorpusSpansAllThreeBands)
- ADR-0029/R2 — one derivation from the one verifying solve; no second
  solver entry (check: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve
  lands with CARD-072; review-lens here)
- ADR-0029/R3 — no clock, size or density term (check:
  PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- CON-014 — wall-clock time never enters the score or tier decision; scope
  difficulty.py + orchestrator.py (check: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- CON-004 — difficulty remains a classifier of produced candidates, never a
  construction target (check: review-lens)
- ADR-0023/R1 — export records width/height, never a scalar size (check:
  review-lens); ADR-0023/R2 — decoder accepts only its own SCHEMA_VERSION
  by exact comparison (check: TestExport_RejectsSupersededSchemaVersion)
- ADR-0016 — PDF filed as `<name>-<difficulty>.pdf`; the value set gains
  `guess` (check: tests/test_export_pdf.py)
- ADR-0007 — no lateral imports (check: test_every_import_in_the_package_points_inward)
- ADR-0015 — same seed, same run, now also with --difficulty (check:
  TestResample_SameSeedSameTierUnderDilatedClock)

## Architecture context

- **FR:** FR-026 (AC-118..AC-121), FR-008 (AC-020 re-worded, AC-021),
  FR-009 (AC-022/AC-023 superseded), FR-010 (tier decision)
- **NFR:** NFR-007 (AC-122, AC-123), NFR-001 (bench)
- **CON:** CON-014 (flips to covered), CON-004
- **EC:** EC-015, EC-016
- **ADR:** ADR-0025 (R1, R2), ADR-0029 (R1, R2, R3), ADR-0013 (retired),
  ADR-0005 / ADR-0015 / ADR-0023 (History), ADR-0016 + DEC-026 (fourth
  filename value), ADR-0007
- **Domain:** POL-004 (single tier test), CAP-004
- **Components:** COMP-006 (rewrite), COMP-002 (classifier call), COMP-001 /
  COMP-007 / COMP-008 + admin (fourth tier value)
- **Trace:** meta/architecture/trace.yml (FR-026, NFR-007, CON-014 rows)

**Checkpoint (handoff, tightened to this card's half):** `nonogram generate
--mode random --size 20 --density 25 --difficulty hard --seed 7` returns a
puzzle that never branched, on two different machines (dilated clock) with
the identical score and tier; the 200-puzzle corpus shows all three
line-solvable tiers populated and every branching puzzle in Guess. (The
re-grade half of the checkpoint is CARD-077's.)
**Collapses:** FR-026, NFR-007, CON-014, EC-015, EC-016, the "Hard means
requires guessing" product risk, the ADR-0015 reproducibility caveat.
**Rollback:** Everything on this card reverts with the branch (no stored
data is touched here — the point of no return is CARD-077's batch).

## Worktree notes

—
