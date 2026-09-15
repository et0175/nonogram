# CARD-091: K was a guess ADR-0024 scheduled for measurement — measure it, and move it if the curve says so

**Status:** in progress
**Priority:** P2
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/091-recalibrate-consecutive-repairs
**Worktree:** ../PythonProject4-CARD-091
**Source:** owner — "open the card for MAX_CONSECUTIVE_REPAIRS" (CARD-089 Q-1, CARD-090 Q-1)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-090 (merged 5d4bc3a) — the bound K splits is now 30
**Touches:** src/nonogram/orchestrator.py (one constant), meta/architecture/decisions/adr/0024-random-mode-repair-then-redraw.md, meta/ops/retry_bound_sweep.py, tests/test_orchestrator.py, tests/property/test_recovery_bound.py
**Review score:** —
**Started:** 2026-09-15
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

`MAX_CONSECUTIVE_REPAIRS` (K) decides how many times in a row random-mode
recovery may repair one non-unique grid (POL-006) before it gives up on that
lineage and draws a fresh grid (POL-001). It is not a bound — every repair and
every redraw advance the one counter `MAX_RETRY_ATTEMPTS` (30) bounds — it is
how that budget is *split* between the two reactions.

ADR-0024 chose 3 and said in writing that the choice was unmeasured and the
measurement owed:

> K is chosen without measurement. Three consecutive repairs is a guess about
> how often a lineage converges versus wanders; it may prove too tight
> (escaping lineages one flip from unique) or too loose (spending budget on
> wandering ones). **The recalibration is owed, not optional**, and needs a
> seeded corpus that records per-seed lineage outcomes.

CARD-074 recorded K=0 against K=3 and, by its own mandate, stopped there. No
other value has ever been run. Meanwhile CARD-089 found that repair is doing
most of the work at the extent where abandonment happens: raw 30x30 draws are
unique 2.7% of the time (27% of requests would succeed inside 20 pure draws),
yet the pipeline succeeded 85% at that bound. The number carrying that weight
is the one nobody has tuned.

## Measurement taken while scoping — K=3 looks too tight

25 seeded requests at 30x30, density 50, bound 30, K=3 (the first 25 of the
sweep harness's seeds, so they line up with CARD-089/090's rows). Every run's
`Puzzle.recovery` was captured, abandoned runs included. 24 made, 1 abandoned.

A capped lineage always costs exactly one redraw plus K repairs, so the depth
at which an accepted puzzle was found is `repairs - K * lineages_at_repair_cap`
— derivable from the existing log, no instrumentation needed:

| accepted at repair depth | 0 (the draw itself) | 1 | 2 | **3 (= K, the last allowed)** |
|---|---|---|---|---|
| puzzles | 2 | 3 | 5 | **14** |

**Acceptances climb with depth and pile up at the cap.** Fourteen of 24 accepted
puzzles were found on the very last repair K permits. If lineages were mostly
wandering, acceptances would thin out with depth; they do the opposite. That is
the "too tight" reading ADR-0024 named: a lineage one more flip from unique is
being thrown away, and the budget is spent redrawing a fresh 2.7% grid instead.

The other failure mode is rare here. Only **7 of 233 repairs (3%)** re-judged a
grid their own lineage had already seen — the flip-back cycle CARD-074
measured at ~7% of lineages. So across 59 capped lineages, almost all were cut
off while still reaching new grids.

Two limits on this, both reasons for AC-1 rather than a shortcut past it:

- **25 requests is a probe**, and 24/25 succeeded already, so it cannot show
  what a larger K *converts*. It shows where acceptances happen, not how many
  more a different K would produce.
- **A larger K raises the cost of the rare cycling lineage.** A lineage
  bouncing between two grids burns every remaining repair up to K. At K=3 that
  costs at most 2 wasted solves; at K=12 it costs 11, out of a budget of 30.
  Whether that outweighs the gain is exactly what the sweep has to answer.

## Acceptance criteria

- **AC-1** (K is swept, not argued) — 100 seeded requests per K at 30x30 and
  25x25, density 50, bound 30, for K ∈ {0, 3, 5, 8, 12}. The run is recorded in
  this card: made / abandoned / timed out, and total solver attempts per
  accepted puzzle. K=0 is the pure-redraw control (ADR-0024's rollback switch);
  K=3 is today. **The machine runs nothing else while it measures** — CARD-090
  ran a test suite alongside its sweep, which inflated timings and could have
  turned a borderline request into a timeout.
  *evidence:* `meta/ops/retry_bound_sweep.py` with a K axis (AC-5)
- **AC-2** (the acceptance-depth histogram is reported) — for each K, how many
  accepted puzzles were found at each repair depth, derived as above. This is
  what tells a K that is *converging* apart from one that happens to score
  well, and it is the per-seed lineage record ADR-0024 said the recalibration
  needs.
- **AC-3** (the decision rule is stated before the numbers are read) — K moves
  to the **smallest** value whose 30x30 success is within one request of the
  best K measured, provided its total wall clock is not worse than K=3's. If
  no K beats 3 by more than one request, K stays at 3 and the card closes as a
  measurement, as CARD-089 did. Smallest-within-noise is preferred because a
  larger K costs more on cycling lineages that this corpus may under-sample.
- **AC-4** (ADR-0024 is revised if K moves, and gains History either way) — the
  Negative consequence "K is chosen without measurement" is marked as
  discharged with the table; the Decision's "initial value **3**, to be
  recalibrated" says what K is now and why. The two tests that pin K
  (`tests/test_orchestrator.py:1506`, `tests/property/test_recovery_bound.py:439`)
  move with it and stay pins.
- **AC-5** (the harness gets a K axis) — `retry_bound_sweep.py` accepts the
  repair values to sweep alongside bounds and extents, restores the constant
  afterwards the way it already restores the bound, and prints the depth
  histogram. The CARD-089/090 command lines keep producing the same output.
- **AC-6** (ADR-0024's rollback switch still works) — `MAX_CONSECUTIVE_REPAIRS = 0`
  still reproduces the pure-redraw loop exactly, down to the rng draws, whatever
  the shipped K is. The existing tests that set K=0 keep passing.

## Guardrails

- **G-1** — `MAX_RETRY_ATTEMPTS` stays 30. CARD-090 just moved it; moving both
  numbers in one card would make neither attributable.
- **G-2** — K stays a split, not a bound (ADR-0024/R2). No change to
  `run_bounded`'s accounting: a run still makes at most `MAX_RETRY_ATTEMPTS`
  attempts whatever K is. `tests/property/test_recovery_bound.py` must keep
  passing.
- **G-3** — the repair *rule* does not change: same region, same deterministic
  pair choice, same re-verify through the one judge path (ADR-0024/R1, R4).
  In particular a repeated grid is still recorded and not acted on — see Q-2.
  This card tunes a number.
- **G-4** — `MAX_NUDGE_ATTEMPTS` (5), `MAX_CONSECUTIVE_ABANDONMENTS` (3),
  `BATCH_BUDGET_SECONDS` (75) and `GENERATION_BUDGET_SECONDS` (30) do not move.
- **G-5** — library mode is untouched: it never repairs, so K cannot affect it.
- **G-6** — `nonogram_admin.db`, `src/nonogram.egg-info/*` and the stray PDFs
  stay uncommitted; commit with explicit pathspecs only.

## Open questions for the owner

- **Q-1** — are {0, 3, 5, 8, 12} the right values to sweep? They bracket the
  probe's signal without approaching K ≥ 29, which at bound 30 would mean one
  lineage per request — ADR-0024's rejected `pure_repair` alternative rather
  than a retune of the chosen one. Estimated cost: about 45 minutes of quiet
  machine for the full table, most of it at 30x30.
- **Q-2** — if a large K wins, should a lineage that returns to a grid it has
  already seen end immediately instead of spending its remaining repairs
  bouncing? That would make a larger K nearly free on cycling lineages, but it
  is a change to ADR-0024/R4's rule, which the code comment at the repeat
  check explicitly says a K card does not have the mandate to make. Proposed
  default: **not in this card** — measure K alone first; if cycling shows up as
  the cost that decides between two K values, open it as its own card.
