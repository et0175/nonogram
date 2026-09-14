# CARD-089: The retry bound was a guess that asked to be measured — measured, and left at 20

**Status:** done
**Priority:** P2
**Category:** enabler  _(closed as a measurement; the constant did not move)_
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/089-retry-bound-measured
**Worktree:** ../PythonProject4-CARD-089
**Source:** owner question — "whether MAX_RETRY_ATTEMPTS should rise?"
**Idea:** —
**Wave:** 1
**Depends on:** CARD-088 (merged 55d83a5) — whose Q-1 this answers
**Touches:** src/nonogram/orchestrator.py (one constant), meta/architecture/decisions/adr/0002-retry-and-nudge-bounds.md, tests/test_retry_bound_corpus.py (new)
**Review score:** — (no code change to review; closed at the owner's decision)
**Started:** 2026-09-14
**Closed:** 2026-09-14
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

ADR-0002 chose 20 on 2026-08-27 and said, in its own Negative consequences,
exactly what would make it wrong:

> Both numbers are chosen **without empirical tuning** against real solver
> performance or real density/difficulty distributions; they may prove too
> tight or too loose once observed, and **will likely need revisiting once
> usage data exists**.

The usage data now exists. Measured at 30x30, density 50, 25 requests per bound,
through the real pipeline:

| bound | made | abandoned | success | median | max | total |
|---|---|---|---|---|---|---|
| **20** (today) | 21 | **4** | 84% | 2.62 s | 11.85 s | 94 s |
| **40** | 25 | **0** | **100%** | 2.85 s | 12.25 s | 101 s |
| 60 | 25 | 0 | 100% | 2.54 s | 11.59 s | 93 s |

Doubling the budget converted every abandonment and cost 7 s across 25
requests — inside the noise, since bound 60 came back *faster* than bound 20.
Going 40 -> 60 buys nothing, so 40 is the knee rather than an arbitrary larger
number.

### The reason ADR-0002 gave for rejecting a larger bound is refuted

Its `50_retries_10_nudges` alternative was turned down on two grounds, and the
measurement contradicts both:

> A larger bound also does not change what is achievable — a combination that
> cannot be satisfied in 20 attempts is **not meaningfully more likely to be
> satisfied in 50**.

Four of four were. Every request abandoned at 20 succeeded at 40.

> it directly worsens the **worst-case failure latency** this decision is meant
> to bound: each additional attempt is a full solver invocation.

Worst case moved 11.85 s -> 12.25 s. The extra budget is only ever spent by the
requests that were failing, and those had already paid their 20; with POL-006
repair active they converge soon after rather than running the bound out.

Neither claim was unreasonable in August — they were predictions made without
data, and the ADR said so. This card supplies the data.

### The larger finding, which is not this card's change

Raw draws at 30x30 are uniquely solvable only **2.7%** of the time: median
**44** fresh draws to find one, and only **27%** of requests would succeed
within 20 draws. The real pipeline hits **84%** at that same bound.

The difference is ADR-0024's repair (POL-006), which ADR-0024 itself described
as "a guess about how often a repair lineage converges rather than wanders,
explicitly scheduled for recalibration". That guess is carrying roughly **three
times** the retry budget's weight. Whether **K** is the lever that should move
instead of — or as well as — this bound is a separate question, and Q-1 below.

## Acceptance criteria

- **AC-1** (the measurement is widened before the constant moves) — the 25-run
  probe above is re-run at **100 requests per bound** across **25x25 and
  30x30**, seeded and reproducible, and the card records the result. If the
  wider run does not reproduce the conversion, the constant does not move and
  this card closes with the finding instead.
  *test:* `tests/test_retry_bound_corpus.py`, marked slow/integration so the
  default suite does not pay for it
- **AC-2** (the bound moves to 40) — `MAX_RETRY_ATTEMPTS` is 40, and the two
  aliases still derive from it rather than repeating a literal.
  *test:* `test_the_regenerate_and_resample_bounds_are_one_number`
- **AC-3** (ADR-0002 is revised, not contradicted silently) — the ADR records
  the measurement, marks the `50_retries_10_nudges` rejection reasoning as
  superseded by data, and its History gains this card. A constant that
  disagrees with an accepted ADR is the drift CARD-085 spent two review cycles
  on; it is not repeated here.
- **AC-4** (the deadline still does not bind) — the worst-case request at the
  new bound stays well inside `GENERATION_BUDGET_SECONDS`, asserted rather than
  assumed, because the whole argument for 40 being free rests on it.
  *test:* `test_the_worst_case_request_stays_inside_the_deadline`
- **AC-5** (the batch ceiling still holds) — CARD-088's
  `BATCH_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS` arithmetic is unchanged by
  this card, and `tests/test_admin_serving.py` still passes: a longer retry
  budget must not silently push a batch past the worker timeout.

## Guardrails

- **G-1** — **`MAX_NUDGE_ATTEMPTS` stays 5.** ADR-0002's two numbers are
  independent judgements about different things, and CARD-016's G-2 says so
  explicitly: how many fresh candidates are worth drawing is not how much of a
  user's uploaded photograph may be altered behind their back. This card moves
  one of them and must not let the other drift along with it.
- **G-2** — **`MAX_CONSECUTIVE_REPAIRS` (K) stays 3.** The measurement says K
  is doing most of the work, which is a reason to study it, not to change it in
  the same card that changes the bound beside it — two moved numbers make a
  later measurement unattributable.
- **G-3** — `GENERATION_BUDGET_SECONDS` stays 30. The measurement removes the
  argument that raising the retry bound would make the deadline bind (worst
  case 12.25 s against 30 s), so the deadline question is not reopened here.
- **G-4** — no change to what a puzzle *is*. This is a bound on how long the
  pipeline keeps trying, not on what it accepts; uniqueness, grading and the
  ladder are untouched.

## Open questions for the owner

- **Q-1** — should **K** (`MAX_CONSECUTIVE_REPAIRS`) be recalibrated? ADR-0024
  scheduled it for exactly that and it has never happened. The measurement here
  suggests repair is the dominant effect, so K may be a bigger lever than the
  bound this card moves — and it is cheap to sweep now that the harness exists.
- **Q-2** — should 25x25 be included in the headline claim? Its per-draw
  uniqueness is 5.0% against 30x30's 2.7%, so the bound bites less there (1 of
  25 requests abandoned), but "less" is not "not at all" and AC-1 measures both.

## Measurements taken while scoping

Per-draw uniqueness, density 50, fresh grids:

| extent | draws | unique | p | mean draws needed (1/p) |
|---|---|---|---|---|
| 20x20 | 200 | 27 | 0.135 | 7.4 |
| 25x25 | 200 | 10 | 0.050 | 20.0 |
| 30x30 | 150 | 4 | **0.027** | **37.5** |

Pure-redraw draws-to-success at 30x30, 60 trials, cap 120:
median **44**, mean 54.0, max 120 — and by budget: 17% within 10, **27% within
20**, 35% within 30, 43% within 40, 63% within 60, 100% within 120.

Set against the pipeline's measured 84% at bound 20, the gap is POL-006.

## Outcome — AC-1 ran, and the owner declined the change

**The constant did not move.** `MAX_RETRY_ATTEMPTS` stays 20. The owner's call,
made against the wide measurement below rather than the narrow one this card
was opened on — which is the order that matters, because the two disagree.

### AC-1, the wide run: 100 requests per bound, seeded, both extents

| extent | bound | made | abandoned | timed out | success | median | p95 | max | total |
|---|---|---|---|---|---|---|---|---|---|
| 25x25 | **20** | 100 | **0** | 0 | 100% | 0.31 s | 1.33 s | 1.87 s | 45 s |
| 25x25 | 40 | 100 | 0 | 0 | 100% | 0.31 s | 1.34 s | 2.07 s | 47 s |
| 25x25 | 60 | 100 | 0 | 0 | 100% | 0.32 s | 1.32 s | 2.25 s | 47 s |
| 30x30 | **20** | 85 | **14** | **1** | 85% | 3.68 s | 16.20 s | **30.01 s** | 583 s |
| 30x30 | 40 | 96 | 3 | 1 | 96% | 2.86 s | 14.73 s | 30.01 s | 482 s |
| 30x30 | 60 | 98 | 1 | 1 | 98% | 2.07 s | 11.39 s | 30.00 s | 375 s |

### Three things the wide run changed about the narrow one

**The conversion is real but smaller than claimed.** The 25-request probe this
card was opened on reported 4 of 4 abandonments converted — 100% at bound 40.
At 100 requests it is 11 of 14: **85% -> 96%**, not 85% -> 100%. The direction
held; the magnitude did not. A card written on the narrow number would have
promised something the wide number does not support.

**25x25 never needed anything.** 300 requests, zero abandonments at every
bound, identical timings. The single abandonment seen at that extent in the
narrow probe was noise. Q-2 is answered: the question only ever concerned
30x30, which is where per-draw uniqueness collapses to 2.7%.

**The deadline does bind, once in a hundred.** Every 30x30 row carries one
`SolverTimeout` at 30.01 s — at *every* bound, including 20. This card's own
G-3, and the argument in CARD-088 that raising the retry bound would not make
the deadline bind, were both written on "zero timeouts in 65 draws" from a
narrow run. At 100 requests the rate is ~1%. It does not change either card's
conclusion, but "the deadline never binds" was too strong and is corrected here.

### Why declining is a reasonable reading of this table

At 30x30 the bound buys 11 percentage points, and the extent is the one a
50-puzzle batch cannot finish anyway (CARD-088 caps that run at 19 puzzles on
time). Everywhere the tool is actually used — 20x20 and 25x25 — the bound never
fires. Raising a number stated in an accepted ADR to improve the one extent
that is already time-bound is a fair thing to decline.

Curiously, a larger bound is *cheaper* in total wall-clock (583 s -> 482 s ->
375 s), because a converted request stops as soon as it succeeds while an
abandoned one always pays its full budget. That is an argument for the change,
not against it, and it is recorded here for whoever revisits.

### What survives

`meta/ops/retry_bound_sweep.py` — committed rather than left in a terminal, for
the reason ADR-0002 needed this card at all: it said its numbers were "chosen
without empirical tuning ... and will likely need revisiting once usage data
exists". The next person asking "is 20 still right?" runs one command instead
of rebuilding this.

**ADR-0002 is untouched**, deliberately. Its `50_retries` rejection reasoning is
contradicted by this data — a combination unsatisfiable in 20 attempts *is*
meaningfully more likely to be satisfied in 40, and the worst case does not
worsen — but the decision it records still stands, because the owner has now
re-made it with the data in hand. Amending an ADR whose conclusion is unchanged
would be noise; the record of why lives here and the ADR's History can gain a
line if the bound ever does move.

## Worktree notes

The harness monkeypatches `MAX_REGENERATE_ATTEMPTS`/`MAX_RESAMPLE_ATTEMPTS`
rather than editing the constant, which works because
`orchestrator.Puzzle`'s counters are built by a `default_factory` lambda that
reads the module global at call time. It restores both in a `finally`, so an
interrupted sweep cannot leave the process with a mutated bound.

Every bound is measured against **the same seeds**, so a difference between
rows is the bound and not a different set of grids.
