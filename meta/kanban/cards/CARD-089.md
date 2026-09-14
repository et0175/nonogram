# CARD-089: The retry bound was a guess that asked to be measured, and the measurement says 40

**Status:** ready
**Priority:** P2
**Category:** enabler
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
**Review score:** —
**Started:** —
**Closed:** —
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

## Worktree notes

_(none yet)_
