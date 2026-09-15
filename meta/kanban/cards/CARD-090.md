# CARD-090: The retry bound moves to 30 — the middle value the owner took after seeing the curve

**Status:** done
**Priority:** P2
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** yes
**Branch:** card/090-raise-the-retry-bound-to-30
**Worktree:** ../PythonProject4-CARD-090
**Source:** owner — "looking at numbers it looks like it make sence to use a middle value like 30 for the upper bound"
**Idea:** —
**Wave:** 1
**Depends on:** CARD-089 (merged d575708) — whose measurement this acts on
**Touches:** src/nonogram/orchestrator.py (one constant), meta/architecture/decisions/adr/0002-retry-and-nudge-bounds.md, meta/ops/retry_bound_sweep.py, tests/test_resample.py, tests/test_orchestrator.py
**Review score:** — (merged without a review cycle, at the owner's call)
**Started:** 2026-09-14
**Closed:** 2026-09-15
**Actual:** —
**Merge commit:** 5d4bc3a
**Blocked by:** —

## Why

CARD-089 measured the bound and the owner left it at 20, which was the right
call on the evidence then in hand: the question had been posed as 20-vs-40, and
40 is a doubling nobody had asked for. Having looked at the curve, the owner has
now taken the middle value:

> looking at numbers it looks like it make sence to use a middle value like 30
> for the upper bound

The curve CARD-089 produced, 100 seeded requests per bound through the real
`orchestrator.generate`:

| extent | bound | made | abandoned | timed out | success | median | p95 | max | total |
|---|---|---|---|---|---|---|---|---|---|
| 25x25 | 20 | 100 | 0 | 0 | 100% | 0.31 s | 1.33 s | 1.87 s | 45 s |
| 25x25 | 40 | 100 | 0 | 0 | 100% | 0.31 s | 1.34 s | 2.07 s | 47 s |
| 25x25 | 60 | 100 | 0 | 0 | 100% | 0.32 s | 1.32 s | 2.25 s | 47 s |
| 30x30 | **20** | 85 | **14** | 1 | **85%** | 3.68 s | 16.20 s | 30.01 s | **583 s** |
| 30x30 | 40 | 96 | 3 | 1 | 96% | 2.86 s | 14.73 s | 30.01 s | 482 s |
| 30x30 | 60 | 98 | 1 | 1 | 98% | 2.07 s | 11.39 s | 30.00 s | 375 s |

Three facts from that table decide this card, and the third is the one that
makes the change cheap:

1. **25x25 and below never needed anything.** The bound is invisible there at
   every value tried. Whatever this card does, it does it for 30x30.
2. **The abandonments at 20 are mostly false negatives.** 11 of the 14 grids
   abandoned at bound 20 are produced at bound 40 — from the *same seeds*, so
   the difference is the budget and not a different set of grids. A user hitting
   one of those saw "infeasible" for a request that was perfectly feasible.
3. **A larger bound is not slower — it is faster.** Total wall-clock *falls*
   monotonically as the bound rises (583 s → 482 s → 375 s), because an
   abandonment is the expensive outcome: it burns the whole budget and returns
   nothing, while a success usually lands early. Per-request worst case is
   pinned at 30 s by `GENERATION_BUDGET_SECONDS` regardless of the bound, which
   is why `max` is 30.0 s in every 30x30 row.

Fact 3 is what ADR-0002 got wrong, and it got it wrong twice in the same
paragraph. Its rejection of `50_retries_10_nudges` rests on two claims that the
data contradicts: that a bigger bound "directly worsens the worst-case failure
latency" (it does not — the deadline sets worst case, and total time went down),
and that "a combination that cannot be satisfied in 20 attempts is not
meaningfully more likely to be satisfied in 50" (11 of 14 were). CARD-089 left
the ADR untouched on the grounds that its *conclusion* still stood once the
owner had re-made the decision with numbers in hand. The conclusion no longer
stands, so this card revises it. See AC-3.

## What 30 buys, and the honest gap

30 was never measured. CARD-089 ran 20, 40 and 60. Straight-line interpolation
between 85% and 96% puts 30 near 92%, but the curve has no reason to be linear —
the conversions are concentrated wherever those particular seeds' repair
lineages happen to terminate. AC-1 therefore measures 30 before the constant
moves, rather than shipping an interpolation.

The measurement is directly comparable to CARD-089's without re-running it:
`seed_base` in the harness depends only on the extent, so bound 30 at 100
requests sees exactly the seeds bounds 20, 40 and 60 saw.

## Acceptance criteria

- **AC-1** (30 is measured, not interpolated) — the sweep is run at bound 30
  across 25x25 and 30x30 at 100 requests, seeded, and this card records the row
  beside CARD-089's. If 30 lands materially short of the 40 result, the card
  reports that and the owner decides again rather than the constant moving on
  an assumption.
  *evidence:* `meta/ops/retry_bound_sweep.py 100 30 25,30`
- **AC-2** (the bound moves to 30) — `MAX_RETRY_ATTEMPTS` is 30, and
  `MAX_REGENERATE_ATTEMPTS` / `MAX_RESAMPLE_ATTEMPTS` still derive from it by
  identity rather than repeating a literal.
  *test:* `test_the_two_loops_share_one_bound_constant` (the `is` assertions
  stay; only the pinned value changes)
- **AC-3** (ADR-0002 is revised, not contradicted silently) — the ADR carries
  the measurement, marks the `50_retries_10_nudges` rejection reasoning as
  superseded on both of its claims, and its History gains this card. Two tests
  exist *specifically* to stop this constant drifting away from the ADR
  (`test_the_regenerate_bound_is_the_adr_0002_value`,
  `test_the_two_loops_share_one_bound_constant`); satisfying them by editing the
  number and leaving the ADR saying 20 would defeat the thing they are for.
- **AC-4** (the deadline's behaviour is stated correctly) — the per-request
  deadline binds about 1 request in 100 at 30x30 and does so *independently of
  the bound* (1 timeout at 20, at 40 and at 60 alike). The card and the ADR say
  that rather than the stronger "the deadline does not bind", which CARD-088 and
  CARD-089's own G-3 both asserted and neither had measured.
  *test:* `test_every_attempt_in_one_request_shares_one_deadline`
  (`tests/test_timeout.py:498`) already holds the mechanism that makes this
  true -- one deadline per *request*, shared by every attempt in it -- so a
  larger bound cannot extend a request's wall clock. It must keep passing.
- **AC-5** (the batch ceiling still holds) — CARD-088's
  `BATCH_BUDGET_SECONDS` / `MAX_BATCH_COUNT` / `DEFAULT_BATCH_COUNT` arithmetic
  is untouched and `tests/test_admin_serving.py` still passes. A longer retry
  budget must not silently push a batch past the gunicorn timeout.
- **AC-6** (the harness can ask a new question) — `retry_bound_sweep.py` takes
  the bounds and extents as arguments instead of hardcoding `(20, 40, 60)`, so
  the next person asking "is 30 still right?" re-runs it instead of editing it.

## Guardrails

- **G-1** — `MAX_NUDGE_ATTEMPTS` (5) does not move. It is POL-002's bound, it is
  deliberately independent of this one (ADR-0002 decided the two together but
  they answer different questions), and no image-mode measurement was taken.
  `test_the_nudge_bound_is_five_and_is_its_own_constant` must keep passing --
  note its `MAX_NUDGE_ATTEMPTS != MAX_RETRY_ATTEMPTS` assertion is what stops
  a retune collapsing the two families, and 30 keeps them apart.
- **G-2** — `MAX_CONSECUTIVE_REPAIRS` (K, 3) does not move. ADR-0024's
  interleaving split is a separate open question (CARD-089 Q-1) and the
  measurement says it is probably the *larger* lever; changing both at once
  would make neither attributable.
- **G-3** — `MAX_CONSECUTIVE_ABANDONMENTS` (3) and `BATCH_BUDGET_SECONDS` (75)
  do not move. INV-003: one bound per question.
- **G-4** — no new constant. The change is one number and the documents that
  justify it; a second bound introduced here would be exactly the drift ADR-0002
  names as its one structural risk.
- **G-5** — `nonogram_admin.db`, `src/nonogram.egg-info/*` and the stray PDFs
  stay uncommitted (standing repository noise, CARD-077 G-6 / CARD-080 G-5).
  Commit with explicit pathspecs only; main carries the owner's own uncommitted
  design-system work.

## Open questions for the owner

- **Q-1** — CARD-089's Q-1 stands and this card does not touch it: recalibrate
  K (`MAX_CONSECUTIVE_REPAIRS`)? The measurement suggests POL-006's repair
  carries roughly three times the weight of the retry budget, which would make
  K the more valuable number to tune. The harness now takes arguments, so the
  sweep is re-runnable against it.

## Measurement — AC-1 ran, and 30 beat its interpolation

`PYTHONPATH=src python meta/ops/retry_bound_sweep.py 100 30 25,30`, same seeds
as CARD-089's rows:

| extent | bound | made | abandoned | timed out | success |
|---|---|---|---|---|---|
| 25x25 | 30 | 100 | 0 | 0 | 100% |
| 30x30 | 20 | 85 | 14 | 1 | 85% |
| 30x30 | **30** | **95** | **4** | **1** | **95%** |
| 30x30 | 40 | 96 | 3 | 1 | 96% |
| 30x30 | 60 | 98 | 1 | 1 | 98% |

**30 converts ten of the fourteen abandonments** — against the ~92% a straight
line between 20 and 40 predicted. It captures ten of the eleven conversions
bound 40 delivers, and the curve is visibly flat after it: the owner's middle
value sits at the knee. AC-1's release condition ("if 30 lands materially short
of 40, the owner decides again") is not met — one request short, not material.

**The timeout count is 1 at every bound, 20 through 60.** That is the evidence
AC-4 rests on: one seed in a hundred is hard enough to reach the 30 s deadline,
and it does so whatever the retry budget is, because the deadline is per request
and every attempt shares it.

### Two caveats about this row

- **Counts compare across runs; wall clock does not.** Outcomes are
  deterministic given the seed and the bound, so the made/abandoned columns line
  up with CARD-089's exactly. The timing columns do not — this run's 25x25 total
  was 32 s against CARD-089's 45 s on the same seeds, which is machine load, not
  the bound. CARD-089's *within-run* observation (total wall clock falling
  583 s -> 482 s -> 375 s as the bound rose) is the trustworthy timing claim, and
  the ADR cites that rather than comparing this row's 340 s to it.
- **The sweep shared the CPU with a test run for part of its 30x30 row.** That
  was a mistake: contention inflates timings and can, in principle, push a
  borderline request past the deadline and turn a "made" into a "timed out".
  It did not happen here — the timeout count is 1, identical to every
  uncontended row — so the counts stand. The timing columns for this row are
  omitted from the table above for that reason.

## Outcome

- `MAX_RETRY_ATTEMPTS` is **30** (`src/nonogram/orchestrator.py`), and its
  docstring carries the measurement. The aliases still derive by identity.
- **ADR-0002 revised to R1.** The Decision section carries an R1 note at the
  number; the `50_retries_10_nudges` rejection is marked superseded on both of
  its claims with the table; History gains this card. The original text is kept
  so the superseded reasoning stays legible.
- **Four test literals were really statements about the bound**, not about the
  behaviour they described — `redraws == 5`, `repairs == 15`,
  `lineages_at_repair_cap == 5`, `repeated_attempts == 10`, across three
  ADR-0024 recovery tests. The retune broke all of them at once. They are now
  derived by `_RecoveryShape` in `tests/test_orchestrator.py` from the two
  constants (a lineage costs one redraw plus K repairs, so the budget divides
  into whole lineages and at most one partial). The derivation reproduces the
  old values at 20 and the new ones at 30 exactly, so the tests assert the law
  instead of one sample of it.
- The two *deliberate* value pins (`test_the_regenerate_bound_is_the_adr_0002_value`,
  `test_the_two_loops_share_one_bound_constant`) were updated to 30, and stay
  pins: their job is to fail when the constant and the ADR move apart.
- `orchestrator.py`'s batch-abandonment docstring said `generate_batch(count=200)`
  would spend `200 x 20 = 4000` solves. CARD-088 made `count=200` unreachable and
  this card moved the 20, so it now reads `50 x 30 = 1500`. Noted because it is a
  doc correction outside the constant's own block.
- `meta/ops/retry_bound_sweep.py` takes bounds and extents as arguments (AC-6);
  the shipped-bound marker reads `MAX_RETRY_ATTEMPTS` instead of assuming 20.
- G-1..G-4 held: `MAX_NUDGE_ATTEMPTS` 5, `MAX_CONSECUTIVE_REPAIRS` 3,
  `MAX_CONSECUTIVE_ABANDONMENTS` 3, `BATCH_BUDGET_SECONDS` 75 — none touched, no
  new constant.
- **Full suite: two failures, neither this card's.**
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`
  (looks for a "Fixed" label) and
  `tests/test_difficulty_tiers.py::test_the_admin_puzzle_list_gives_the_fourth_tier_a_badge_of_its_own`
  (parses an inline `background-color:` off a tier badge) fail identically on
  untouched main `f7e9e60`, checked in a detached worktree. Both assert on admin
  markup that the Pressroom design-system commits (`f773015` onward) changed;
  left for that work rather than patched from a card about a retry constant.

