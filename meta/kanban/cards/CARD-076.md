# CARD-076: Difficulty by strategy ladder and the Guess tier — no clock, no size, one classifier

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/076-strategy-ladder-guess-tier
**Worktree:** ../PythonProject4-CARD-076
**Source:** meta/architecture/handoff.md#increment-10 (scoring + tier half; FR-029 persistence/export/admin is CARD-072, the DB re-grade is CARD-077)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-073
**Touches:** src/nonogram/difficulty.py (rewrite), src/nonogram/orchestrator.py (Puzzle.difficulty_tier / difficulty_in_requested_tier / record_difficulty go through the one classifier; generate_batch tier validation), src/nonogram/cli.py (--difficulty help lists four tiers), src/nonogram/web/pages.py (tier options from the enum — already enum-driven, verify), src/nonogram/export/__init__.py, src/nonogram/export/json_export.py, src/nonogram/export/csv_export.py (difficulty may be "guess"; SCHEMA_VERSION bump per ADR-0023/R2 if a reader would reject it), src/nonogram/admin/templates/puzzles_list.html (tier badge for Guess), src/nonogram/admin/image_to_puzzle.py (retire the private tier derivation, ADR-0025/R2), tests/test_difficulty.py (rewrite), tests/test_difficulty_tiers.py, tests/property/test_difficulty_ladder.py (new), tests/test_resample.py, tests/test_cli.py, tests/test_export_json.py, tests/test_export_csv.py, docs/GENERATION_ALGORITHM.md (§7 rewrite, §10.2 finding 3), meta/architecture/requirements.yml (AC-020/AC-022/AC-023 re-wording), meta/architecture/decisions/adr/0013-*.md (Superseded stamp already present — verify), 0005-*.md, 0015-*.md, 0023-*.md (History entries), meta/architecture/decisions/resolved.yml (DEC-013 superseded note), meta/architecture/decisions/adr/0029-*.md (2026-09-13 band-edge correction — made at card start, already on the branch)
**Review score:** —
**Started:** 2026-09-13T18:45Z
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
   hardest rung present + band width x share of cells settled at that rung,
   over THREE rungs whose band edges are ADR-0005's cutoff constants:
   `simple_overlap` 0..33, `line_dp` 33..66, `probe_contradiction` 66..100
   (widths 33, 33, 34); share = cells settled at the top rung / total cells.

   **Two corrections this card was written before — do not re-derive these
   numbers from the card's original text.** (a) The four 25-wide bands are
   stale: `cross_line` left the ladder in ADR-0029's 2026-09-12 revision,
   which is what put the 33/66 cutoffs on rung boundaries. (b) The
   33.33/66.67 edges that revision wrote are corrected to the cutoff
   constants by ADR-0029's 2026-09-13 History entry: a puzzle topping out at
   `simple_overlap` has a within-rung share of exactly 1.0 by definition
   (measured 1.000 in 420 of 420 line-solvable grids), so at a width of
   33.33 it scores 33.33, lands above `EASY_MAX_SCORE = 33.0` and classifies
   **Medium** — emptying the Easy band and making AC-118 unsatisfiable. With
   the edges at the cutoffs it scores exactly 33.0 and classifies Easy,
   because the cutoffs are inclusive upper bounds.

   Pure function of the rung counts and
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

### Measured before implementation started (2026-09-13)

462 uniquely-solvable random grids, 10x10/12x12/15x15 at densities 30/45/60,
graded by top rung:

| top rung | count | share of line-solvable | within-rung share range |
|---|---:|---:|---|
| `simple_overlap` | 420 | 90.9% | 1.000..1.000 |
| `line_dp` | 16 | 3.5% | 0.053..0.862 |
| `probe_contradiction` | 26 | 5.6% | 0.056..0.947 |
| branched (-> `Tier.GUESS`) | 0 | 0% | — |

Three things follow, and each one changes how this card should be built:

1. **AC-118 is satisfiable, but only just for Medium.** All three bands are
   populated, so the criterion holds — but a 200-puzzle corpus will carry
   roughly 7 Medium puzzles. Sample across densities and extents; a corpus
   drawn at one density can miss the band entirely. This is CARD-073 review
   finding F-004 ("`line_dp` is rare, ~3% of grids") measured out.
2. **`Tier.GUESS` is unreachable from the generator.** 0 of 462 here, and 0 of
   6,620 in ADR-0029's own measurement. AC-120, AC-121 and EC-015 therefore
   cannot be tested on generated puzzles — they need synthetic signal records
   with `branch_nodes > 0`. Do not spend time hunting for a branching grid;
   ADR-0025's History already records the tier as a deliberate safety net.
3. **Easy is a single point on the scale.** Every puzzle that never leaves
   overlap scores exactly 33.0, because all of its settled cells are at that
   rung by definition. So the within-rung ordering ADR-0005's recalibration is
   waiting on does not exist inside the bottom band. Record it with the AC-118
   distribution; G-5 says do not retune here.

### ADR-0029 band-edge correction

Made on this branch before implementation, because the card could not be built
as written: see ADR-0029's 2026-09-13 History entry and item 1 above. No cutoff
constant moved, ADR-0025/R2's `(score, branch_nodes)` signature is unchanged,
and no rung changes hands — it corrects a band edge that sat a third of a point
above the cutoff it was supposed to be.

### AC-118 measurement — the calibration input (2026-09-13, implementation)

Corpus: **292 uniquely-solvable random puzzles**, built by
`tests/test_difficulty.py::_line_solvable_corpus` (seed 118, 21 extent/density
cells, 14 puzzles wanted per cell, 645 grids drawn). Every one is graded through
the real `compute_clues` -> `solve` -> `score_difficulty`; draws that are not
puzzles are dropped before grading, as the generator drops them.

| tier | rung | n | share | score range |
|---|---|---:|---:|---|
| Easy | `simple_overlap` | 258 | 88.4% | 33.000 only |
| Medium | `line_dp` | 8 | 2.7% | 36.667 .. 59.400 |
| Hard | `probe_contradiction` | 26 | 8.9% | 68.116 .. 98.640 |
| Guess | — (branched) | 0 | 0% | — |

Per extent (tier counts):

| extent | Easy | Medium | Hard |
|---|---:|---:|---:|
| 10x10 | 64 | 2 | 4 |
| 12x12 | 47 | 2 | 7 |
| 15x15 | 49 | 4 | 15 |
| 20x20 | 42 | 0 | 0 |
| 25x25 | 28 | 0 | 0 |
| 30x30 | 28 | 0 | 0 |

Per density (tier counts):

| density | Easy | Medium | Hard |
|---|---:|---:|---:|
| 45 | 15 | 5 | 20 |
| 50 | 34 | 3 | 5 |
| 55 | 41 | 0 | 1 |
| 60 | 56 | 0 | 0 |
| 65 | 28 | 0 | 0 |
| 70 | 56 | 0 | 0 |
| 75 | 28 | 0 | 0 |

**AC-118 holds**: all three bands are populated. Band coverage was checked at
seeds 118, 2026 and 7 before 118 was pinned — Medium came out at 8, 13 and 7
puzzles, so the margin is real rather than an artefact of the first seed tried.

Four things the numbers say, none of them acted on here (G-5):

1. **Easy is a single point.** All 258 Easy puzzles score exactly 33.000, because
   a puzzle that tops out at `simple_overlap` has settled *every* cell there and
   its within-rung share is 1.0 by definition. The within-rung ordering ADR-0005's
   recalibration is waiting on therefore does not exist inside the bottom band —
   which is where 88% of the corpus is. Pinned as a test
   (`test_every_corpus_puzzle_that_never_left_overlap_scores_the_same_point`) so
   the recalibration has to change it on purpose.
2. **The other two rungs do spread.** `line_dp` occupies 36.7..59.4 of its 33..66
   band and `probe_contradiction` 68.1..98.6 of its 66..100, so the secondary
   count is doing real work where it can do any.
3. **Where the bands live is a property of the source, not of the extent.**
   Medium and Hard are concentrated at densities 45-50 and at the smaller
   extents — 25 of the 34 non-Easy puzzles are at density 45 or 50. That is why
   the corpus plan samples those cells at all: a corpus drawn at one density, or
   only at the fast high-density end, misses Medium entirely and the AC-118 test
   would look flaky rather than wrong. A separate measurement over 12,000 draws
   at 10x10..15x15 puts `line_dp` at 22% of unique 12x12 grids at density 45,
   0.4% at density 55 and 0% at 65+.
4. **Guess stays measured-unreachable.** 0 of 292 here, on top of 0 of 462
   pre-implementation and 0 of 6,620 in ADR-0029's own sweep. AC-120, AC-121 and
   EC-015 are therefore tested against synthetic signal records, and the zero is
   itself pinned (`test_no_corpus_puzzle_needed_a_real_branch`) so that the day a
   source does produce a branching grid is a test failure somebody reads.

**A consequence for `--difficulty` worth flagging to the owner.** Under ADR-0013
every line-solvable puzzle scored under 15, so `--difficulty easy` was satisfied
by the first candidate and Medium/Hard were unreachable without guessing. Under
the ladder all four tiers mean something, and that cuts both ways: `easy` is now
a real filter that rejects ~85% of candidates at density 45, and a Medium request
at a density where `line_dp` does not occur will exhaust POL-004's budget and
abandon. The behaviour is correct and is what FR-026 asked for; it is a change in
what a user experiences, not only in what a number says.

### Benchmark (card item 7)

`tests/bench_generate.py` 20x20, uncensored `report()`, same machine, back to back:

| | p95 (nearest-rank, n=20) |
|---|---|
| base (8a05238) | 20.614 s |
| this branch | 20.793 s |

+0.87%, and every one of the 20 samples matches its baseline to within ~1% with
the identical outcome (unique / abandoned / timeout) per seed. Well within noise.
The corpus is dominated by abandoned density-30/40 runs, i.e. by solver search,
which this card does not touch.

The scorer itself got *cheaper*, which is the number that speaks to the card's
concern ("the resample loop scores every candidate"): `score_difficulty` +
`classify` over one 20x20 record measures **0.246 us/call on this branch against
2.155 us/call on base**, an 8.8x reduction — the clue-density sum over every line
left the formula with the density term. AC-037's gate test is `xfail` on both
trees for the pre-existing reason (p95 is 20.6 s against ADR-0001's 5 s cap);
CARD-076 does not move it.
