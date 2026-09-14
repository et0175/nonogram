# CARD-088: A batch stops on its own clock, not on the worker's

**Status:** ready
**Priority:** P1
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/088-batch-has-its-own-deadline
**Worktree:** ../PythonProject4-CARD-088
**Source:** owner proposal — "reduce max number of pictures in batch to 50"
**Idea:** —
**Wave:** 1
**Depends on:** CARD-086 (merged f381d62) — the worker timeout this card exists to stay inside
**Touches:** src/nonogram/orchestrator.py (the batch loop + one constant), src/nonogram/admin/batch_generator.py (the note), src/nonogram/admin/app.py (the form default), src/nonogram/admin/templates/batch_create.html, tests/test_batch_abandonment.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

`generate_batch` runs **synchronously inside the request**, and since CARD-086
the deployed panel is served by gunicorn with `--timeout 120`. A batch that
outlives the worker is killed mid-run and the whole thing is lost — after doing
all the work.

Measured today, density 50, the value the admin hardcodes:

| sizes | per puzzle | count=50 | count=100 | count=200 | fits in 120s |
|---|---|---|---|---|---|
| `[25]` | 0.55 s | 27 s | 55 s | 110 s | ~218 |
| `[30]` | **3.90 s** | **195 s** | 390 s | 779 s | **~30** |

Three facts follow, and the third is the live one:

1. The current cap of **200** is unreachable at large extents — a 200-puzzle
   30x30 batch would need 13 minutes and gets 2.
2. The owner's proposed cap of **50** is a real improvement at 25x25 and still
   fails at 30x30 (195 s against a 120 s worker).
3. **The create-batch form defaults `count` to 100**
   (`admin/app.py:817`), which already dies at 30x30 today.

### Why a deadline rather than a smaller number

A flat count cannot be right at both ends: the same 50 is trivially safe at
20x20 (3 s) and fatally slow at 30x30 (195 s). A cap tuned for the worst extent
would throttle the common one by a factor of sixty.

What the batch actually needs is the thing every other long-running path in
this codebase already has — **its own bound on its own question**:

- CARD-083 gave the batch a bound on *how many candidates it may abandon*
  (`MAX_CONSECUTIVE_ABANDONMENTS`), because the per-puzzle retry budget did not
  answer "when is this batch hopeless?".
- CARD-086 gave the re-grade run a bound on *how long it may work*
  (`REGRADE_BUDGET_SECONDS`), because the per-row solve budget did not answer
  "when will this outlive the worker?".

This card is the same move a third time, on the one remaining request-bound
loop. INV-003 and ADR-0002 ask for one bound per question, and "how long may a
batch work?" has never had one.

The shortfall machinery already exists: `generate_batch` may already return
fewer puzzles than asked (CARD-083) and `batch_generator` already renders a
sentence saying so. A time-based stop reuses both — a short batch is a shape
the caller and the UI already understand.

## What is decided

1. **`BATCH_BUDGET_SECONDS`** bounds the whole run, checked **before** each
   candidate so one that starts always finishes. The ceiling is therefore
   `BATCH_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS`, exactly as CARD-086's
   is, and `start.sh`'s `--timeout` must clear the sum.
2. **The count cap drops 200 -> 50**, as the owner proposed — but as a sanity
   bound, not the mechanism. 50 at the *typical* extent is a reasonable ask; it
   is the deadline that makes 50 safe at every extent.
3. **The form default drops 100 -> 20.** A default should be a number that
   works everywhere, and 20 completes in under 80 s at the worst supported
   extent.
4. **The batch says which bound stopped it.** "Fewer than you asked for because
   candidates were abandoned" and "fewer because time ran out" are different
   facts about a batch, and a caller re-running blindly on the second will get
   the same answer again.

## Acceptance criteria

- **AC-1** (the batch has its own clock) — `generate_batch` stops starting new
  candidates once `BATCH_BUDGET_SECONDS` has elapsed and returns what it has.
  *test:* `TestBatch_StopsOnItsOwnClock`
- **AC-2** (the ceiling clears the worker) — `BATCH_BUDGET_SECONDS +
  GENERATION_BUDGET_SECONDS` is less than `start.sh`'s `--timeout`, asserted by
  reading the flag, as CARD-086 does for the re-grade route.
  *test:* `test_the_worker_timeout_clears_the_batch_ceiling` in `tests/test_admin_serving.py`
- **AC-3** (a stopped batch says so, distinctly) — the return carries enough
  for a caller to tell "abandoned candidates" from "ran out of time", and
  `batch_generator`'s note says which. A batch stopped by the clock does not
  claim its missing puzzles "could not be made uniquely solvable".
  *test:* `TestBatch_SaysWhichBoundStoppedIt`
- **AC-4** (the count cap) — `count` is validated 1..50; 51 is refused with a
  message naming the new ceiling.
  *test:* `TestBatch_CountCap`
- **AC-5** (the form default) — the create-batch form defaults to 20, in both
  the route's fallback and the template, and the two agree.
  *test:* `test_the_form_default_count_is_safe_at_every_extent`
- **AC-6** (nothing else changes) — a batch that fits its budget returns
  exactly what it returns today, including the existing abandonment note.
  *test:* the existing `tests/test_batch_abandonment.py`, unmodified
- **AC-7** (measured) — `BATCH_BUDGET_SECONDS` is chosen against the measured
  per-puzzle costs above, and the card records what a batch of 50 costs at each
  supported extent after the change.

## Guardrails

- **G-1** — `MAX_RETRY_ATTEMPTS`, `MAX_NUDGE_ATTEMPTS`,
  `MAX_CONSECUTIVE_REPAIRS` and `MAX_CONSECUTIVE_ABANDONMENTS` are untouched.
  This card adds a bound on a question that has none; it does not retune the
  four that are already answered.
- **G-2** — **`GENERATION_BUDGET_SECONDS` stays 30.** The owner proposed 45,
  and the measurement says it would change nothing: across 160 draws from 20x20
  to 30x30 the slowest solve was **0.82 s** against a 30 s bound, and
  end-to-end at 30x30 the whole request (all retries) ran a median 1.70 s and a
  max 11.44 s with **zero** timeouts. The 4-in-25 failures at that extent ran
  out of *retries*, not time. Raising the deadline rescues nothing until the
  retry bound rises first — see the open question below. It is also an
  ADR-0001/ADR-0011 number, so changing it is an ADR revision, not a constant edit.
- **G-3** — `SolverTimeout` stays uncaught by the batch loop (CARD-083). A
  batch-level clock does not become a reason to swallow the per-request one.
- **G-4** — no change to what a puzzle *is*: grading, uniqueness and the
  pipeline are untouched.

## Open questions for the owner

- **Q-1** — should `MAX_RETRY_ATTEMPTS` (20) rise? It is the binding constraint
  at 30x30: 4 of 25 requests there were abandoned with the clock barely used.
  Raising it is the only change that would convert those into puzzles. It needs
  its own measurement — how many abandonments a larger budget actually
  converts, against a seeded corpus — so it is a separate card, not an item here.
- **Q-2** — should batch generation move **off** the request entirely? It is
  the real fix; this card keeps it synchronous and merely stops it overrunning.
  Nothing in `src/nonogram/admin/` runs in a thread today, so it would be the
  first, and that is a decision rather than an edit.

## Measurements taken while scoping

Solve wall-clock, density 50, 40 draws per extent, fresh 30 s budget each:

| extent | median | p90 | max | timeouts |
|---|---|---|---|---|
| 20x20 | 0.01 s | 0.02 s | 0.05 s | 0 |
| 25x25 | 0.04 s | 0.16 s | 0.33 s | 0 |
| 28x28 | 0.11 s | 0.46 s | 0.66 s | 0 |
| 30x30 | 0.38 s | 0.75 s | 0.82 s | 0 |

Whole requests through `orchestrator.generate`, 25 per extent, retries included
against the single 30 s budget:

| extent | median | max | abandoned | timeouts |
|---|---|---|---|---|
| 20x20 | 0.05 s | 0.26 s | 0 | 0 |
| 25x25 | 0.21 s | 2.71 s | 1 | 0 |
| 30x30 | 1.70 s | 11.44 s | **4** | **0** |

A note earlier in this session claimed 30x30 "reaches ADR-0011's deadline
(`SolverTimeout`) instead" of abandoning. It does not reproduce: 0 timeouts in
65 draws. It abandons on the retry bound. The claim is corrected here because
it is the premise the deadline proposal rested on.

## Worktree notes

_(none yet)_
