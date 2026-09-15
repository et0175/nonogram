# CARD-095: An image batch stops on its own clock, as a random batch does

**Status:** in progress
**Priority:** P3
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** yes
**Branch:** card/095-image-batch-clock
**Worktree:** ../PythonProject4-CARD-095
**Source:** owner — "open a card for the image batch time limit" (CARD-094 out-of-scope observation)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-088 (merged) — the batch clock this reuses; CARD-086 (merged) — gunicorn's 120 s timeout
**Touches:** src/nonogram/admin/app.py (the image-batch generate route, `_generate_image_puzzle`), a new test module, docs/GENERATION_ALGORITHM.md (§9.2)
**Review score:** —
**Started:** 2026-09-15
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

CARD-088 gave the **random** batch a clock: `generate_batch` stops starting
candidates once `BATCH_BUDGET_SECONDS` (75 s) has passed, so a request's worst
case is 75 + `GENERATION_BUDGET_SECONDS` = 105 s, inside gunicorn's
`--timeout 120` (`tests/test_admin_serving.py` asserts the relationship).

The **image** batch never got one. The `/batch/generate-puzzles` route
loops over every loaded picture inside one request, and for each picture calls
`admin.app._generate_image_puzzle`, which tries the predicted extent and — if
that is abandoned — up to two neighbour extents. **Every one of those is a
separate `orchestrator.generate` with its own 30 s deadline**, so one picture can
cost up to three deadlines, and nothing stops the loop.

When a request passes 120 s gunicorn kills the worker. What the owner then sees:

- a 502 or a dropped connection instead of the results page;
- the puzzles made before the kill **are** stored — the route stores each as it
  goes — but the batch record says otherwise: `create_batch(source="images")`
  marks the batch `COMPLETE` *before any picture is processed*, and
  `puzzle_count` is written only after the loop, so the record reads
  "COMPLETE, 0 puzzles" with puzzles attached;
- the loaded pictures are not cleared, so the next attempt re-runs all of them,
  including the ones already made.

## Measured while scoping

Every picture in `pictures/` (25) through `orchestrator.generate` in image mode,
at a bare size of 20 and of 30. This is `generate` alone — without the admin's
neighbour retries and without `measure_quality` — so it is a floor on the
route's cost, not a ceiling.

| size | made | abandoned | timed out | median | slowest | total |
|---|---|---|---|---|---|---|
| 20 | 17 | 8 | 0 | 0.01 s | 0.67 s | 1.1 s |
| 30 | 16 | 8 | **1** | 0.02 s | **30.00 s** (`butterfly.png`) | 35.2 s |

The typical picture is free. The risk is entirely in the tail, and it is real:

- one picture in 25 reached the 30 s deadline at 30x30;
- **8 in 25 are abandoned at each size**, and each abandonment makes the admin
  try up to two more extents — each of which may itself run to a deadline.

So a 50-picture book at the Large preset needs only a handful of pictures like
`butterfly.png` to pass 120 s. Rare per batch, total when it happens.

### Why checking the clock between pictures is not enough

`BATCH_BUDGET_SECONDS` works for the random path because one candidate is at
most one 30 s deadline, so "check before each candidate" bounds the request at
75 + 30. An image picture is up to **three** deadlines (predicted extent plus
two neighbours), so a between-pictures check alone allows 75 + 90 = 165 s —
still past 120. The clock has to be consulted **before each extent attempt**,
which restores the same 105 s ceiling the random path has.

## Acceptance criteria

- **AC-1** (the clock is checked before every generate call) — before starting a
  picture, and before each neighbour extent inside `_generate_image_puzzle`, the
  route checks the batch clock; once `BATCH_BUDGET_SECONDS` has passed it starts
  nothing more. A picture in progress finishes its current extent. The worst
  case is therefore `BATCH_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS`, the same
  sum `tests/test_admin_serving.py` already holds against the server timeout.
  *test:* a scripted clock and scripted `generate` — pictures after the budget
  are not attempted; a picture whose predicted extent was abandoned after the
  budget does not try its neighbours.
- **AC-2** (a clock stop is reported as a clock stop) — the results page and the
  batch record say how many pictures were **not attempted** because the batch
  ran out of time, separately from pictures skipped (`CANNOT_FIT`), abandoned or
  errored — the same distinction CARD-088 draws between bad luck and a request
  that will stop in the same place again.
- **AC-3** (the batch record is true while the batch runs) — `puzzle_count` is
  updated as each puzzle is stored, not only after the loop, so a worker killed
  anyway leaves a record that matches the store.
- **AC-4** (one bound) — the image path reads `BATCH_BUDGET_SECONDS`; no new
  constant (INV-003). The clock is injectable the way `generate_batch`'s
  `monotonic` is, so the tests need no sleeping.
- **AC-5** (nothing changes for a batch that fits) — a batch that finishes inside
  the budget produces exactly today's puzzles, notes and redirect.
- **AC-6** (the doc follows) — `docs/GENERATION_ALGORITHM.md` §9.2 describes the
  image batch's clock; the reference checker still passes.

## Guardrails

- **G-1** — the random path is untouched; `generate_batch` and CARD-093's
  hand-off do not change.
- **G-2** — no change to how one picture is generated: fit policy, the
  neighbour order, `measure_quality`, the quality filter and the store call stay
  exactly as they are. The card decides only *whether to start* the next attempt.
- **G-3** — not moving batch generation off the request. That is CARD-088's Q-2,
  still open; this card makes the request safe while it stays synchronous.
- **G-4** — `nonogram_admin.db`, `src/nonogram.egg-info/*` and the stray PDFs
  stay uncommitted; commit with explicit pathspecs only.

## Out-of-scope observation

- **A third of pictures are abandoned in image mode** (8 of 25 at both 20 and 30
  in the probe above, before the admin's neighbour retries). That is a quality
  question about the conversion and the nudge, not a time limit, and deserves
  its own look.

## Open questions for the owner

- **Q-1 — what happens to the pictures a stopped batch never started?**
  - **(a) Keep them loaded (recommended).** The route clears only the pictures it
    attempted, so the next batch runs the rest without a re-upload, and the
    results page says "N pictures were not started — run another batch for them".
  - **(b) Clear everything, as today.** Simplest; the owner re-uploads the rest.
- **Q-2 — status of a batch the clock stopped?** Proposed: **`COMPLETE` with a
  note**, matching CARD-093's decision for a random batch that stopped early with
  puzzles made; `ERROR` only if the clock stopped it before any puzzle.
