# CARD-062: Admin batch — retry an abandoned picture at long side ±1 before giving up

**Status:** done
**Priority:** P2
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/062-abandon-retry-long-side
**Worktree:** —
**Source:** CARD-061 visual check on the owner's pictures (2026-09-11); owner asked for this card the same day
**Idea:** —
**Wave:** —
**Depends on:** CARD-061
**Touches:** src/nonogram/admin/app.py (the image loop in `generate_batch_puzzles`, currently lines ~337-421), src/nonogram/admin/image_manager.py (only if a candidate-extent helper belongs next to `predict_size()`), tests
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-09-11T14:33:18Z
**Closed:** 2026-09-11T16:57:00Z
**Actual:** 0.1d
**Merge commit:** 696871d
**Blocked by:** —

## Why

CARD-061 made the admin "small" preset follow each picture's shape (10 on the
short side) instead of forcing 10x10. On the owner's 13
`christmas/balls/*.jpg` pictures that clearly improved the result, but 3
pictures that used to generate as forced squares are now **abandoned** at
their true shape: the converted grid is not uniquely solvable even after the
5 bounded pixel nudges, so `orchestrator.generate()` raises
`GenerationAbandoned`. The admin batch loop (`app.py:399-404`) records that as
an error and skips the picture (CARD-049 AC-2), so these pictures silently
drop out of "small" batches.

Measured 2026-09-11 (generation is **deterministic** per picture and extent:
5 runs each were always 5/5 or 0/5, so retrying the *same* extent is
pointless — only a different extent can help):

| picture | predicted | long −1 | long +1 |
|---|---|---|---|
| b3 | 10x12 abandoned | 10x11 ok | 10x13 abandoned |
| c12 | 17x10 abandoned | 16x10 ok | 18x10 ok |
| c14 | 10x13 abandoned | 10x12 ok | 10x14 ok |
| b4 | 10x12 abandoned | 10x11 abandoned | 10x13 abandoned |

One cell on the long side rescues every case except b4, which fails at
every size tried (and failed as a 10x10 before CARD-061 too). One cell barely
changes how much of the picture is kept: the shape stays within a few percent
of the picture's ratio.

## What to implement

1. In `generate_batch_puzzles`'s per-image loop, when `orchestrator.generate()`
   raises **`GenerationAbandoned`** for the predicted `(width, height)`, try
   the two neighbouring extents that change the **long side** by −1 and +1
   and keep the short side, in this order:
   - drop a candidate that would put a side outside 10..30 (a 10x10 square
     has only the +1 neighbour; a 30-long side has only −1);
   - try the rest ordered by how much of the picture they keep — closest to
     the picture's ink-bounding-box ratio first (`ImageFile._source_shape()`),
     ties → the smaller extent first.
   Use the first one that generates. At most **2 extra `generate()` calls
   per picture**.
   For a square extent the "long side" is ambiguous, so it only moves
   toward the picture's shape: the picture's longer axis grows by one, or
   its shorter axis shrinks by one (width counts as longer for a square
   picture). So 30x30 for a slightly landscape picture retries at 30x29,
   never at 29x30. (Refined after review cycle 1; the first wording moved
   the picture's longer axis both ways.)
2. If a neighbour succeeds, store that puzzle as normal — its real
   `puzzle.width`/`puzzle.height` already flow into `add_puzzle()` — and add
   one info line to the batch results naming the change, e.g.
   `c12.jpg: generated at 16x10 — 17x10 had no unique solution`.
3. If the predicted extent and every neighbour are abandoned, record the
   error exactly as today (same message format, same batch-continues
   behaviour).
4. Only `GenerationAbandoned` triggers a retry. Other `NonogramError`s
   (e.g. a solver timeout or an unreadable picture) and generic exceptions
   keep today's handling — a different extent will not fix them.

Note for the implementer: the preview (`predict_size()`, CARD-058's note)
is computed before generation, so a rescued picture's preview will show the
predicted size, one cell off from what was stored. That is acceptable for
this card — the results line is where the change is reported; do not change
the preview (G-2).

## Acceptance criteria

- **AC-1** — given a picture abandoned at its predicted extent whose −1 or
  +1 neighbour is uniquely solvable, when the batch runs, then a puzzle is
  stored at that neighbour extent. Tested deterministically with
  `orchestrator.generate` monkeypatched to abandon at the predicted extent
  and succeed at a chosen neighbour (the pattern
  `tests/test_admin_image_uniqueness.py::test_ac2_…` already uses).
- **AC-2** — the batch results show which picture was adjusted, from what
  extent to what extent.
- **AC-3** — a picture abandoned at the predicted extent and at both
  neighbours is recorded as an error with today's message, the batch
  continues, and `generate()` was called at most 3 times for it.
- **AC-4** — a picture that fails with any error other than
  `GenerationAbandoned` is not retried: exactly one `generate()` call.
- **AC-5** — a picture that succeeds at its predicted extent is generated
  exactly once, at that extent — unchanged from today.
- **AC-6** — no retried extent has a side outside 10..30 or a different
  short side than predicted (for a square extent: never moves away from the
  picture's shape, per step 1); candidates follow the ordering rule in step 1
  (unit-tested on the candidate list itself, including the square and the
  30-long edge cases).

## Guardrails

- G-1: Do not touch `orchestrator.py`, `sourcing/`, `solver/` or `cli.py`.
  The CLI keeps reporting abandonment as an error — there the user chose the
  size and gets told; this is admin-only, like CARD-058's substitution.
- G-2: Do not change `predict_size()`, `size_substitution()` or the preview
  pages.
- G-3: Never weaken uniqueness: no change to the pixel-nudge bound, the
  solver or `judge_candidate`. The retry asks for a different extent, never
  a weaker check.
- G-4: Never retry the same extent — generation is deterministic, so a
  repeat is a wasted solver run.

## Worktree notes

[Env] forge 2026.8.17 (no `meta/.skills.yml`, so no min_version comparison).

**Implementation** (commit `3a559fa`):
- `ImageFile.neighbour_extents(extent)` (`image_manager.py`) returns the
  long side −1/+1 with the short side unchanged. A candidate with a side
  outside 10..30 is dropped. The rest are sorted by how much of the picture
  they keep (the ink bounding box's ratio against the grid's), ties going to
  the smaller area. For a square extent, the long axis is the picture's
  longer axis (width for a square picture). If the source shape is
  degenerate, both candidates come back in plain −1, +1 order.
- `_generate_image_puzzle(image, width, height)` (module-level in `app.py`)
  tries the predicted extent, then each neighbour, once each (G-4). Only
  `GenerationAbandoned` moves on to the next extent. Anything else
  propagates on the first attempt. When every candidate is abandoned it
  re-raises the *predicted* extent's own error, so the batch error line
  reads exactly as before (AC-3).
- The batch loop collects an `adjustments` list and flashes it as "info"
  lines (first 3, then "... and N more size adjustments"), the same pattern
  it already uses for errors.
- `orchestrator.py`, `sourcing/`, `solver/` and `cli.py` are untouched
  (G-1). So are `predict_size()`, `size_substitution()` and the templates
  (G-2). The nudge bound and uniqueness check are untouched too (G-3).

**Tests** — `tests/test_card_062_abandon_retry.py`, 12 tests. Seven unit
tests pin the candidate rule: ordering both ways, portrait, the square
cases, the 30-long edge, the degenerate source, and a 2000-case seeded
corpus checking range, short side unchanged, and exactly one long-axis
cell. Five run the real Flask batch route with `orchestrator.generate`
patched to abandon at chosen extents and run for real otherwise, covering
AC-1/2/3/4/5 and the 3-line flash cap. Red→green: against `main`'s
unchanged code, 10 fail and 2 pass. The 2 that pass are the
"unchanged-behaviour" pins: AC-4 (not retried, one call) and AC-5
(success, one call).

**Regression** — the new file, CARD-061/058/047/050 tests,
`test_image_batch_size_fix`, `test_wave3_e2e`, `test_admin_image_uniqueness`
and the import guard: 94 passed, 4 skipped.

**Real pictures** (owner's `christmas/balls`, the worktree's code via
`_generate_image_puzzle`):
- small: b3 10x12 → stored 10x11; c12 17x10 → 16x10; c14 10x13 → 10x12.
  b4 is still abandoned after 10x12, 10x11 and 10x13.
- large: b3 24x30 → stored 24x29, so all 13 pictures now generate at large.
  b4, c12 and c14 succeed at their predicted extent, with no retry.

**Known and accepted by the card:** a rescued picture's preview (computed
before generation) still shows the predicted size, one cell off from what is
stored. The results line is where the change is reported.

[Review 1/3] Score: 9.0 — crit: 0, imp: 0, minor: 3
[Review sync] 1 report(s) → meta/review/ (20260911T163753Z-CARD-062-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review, independent agent): AC-1..AC-6 and G-1..G-4
all held. The reviewer patched 8 wrong implementations in memory (no retry,
retry on every error, re-raise the last error, same-extent retry, wrong
axis, no range filter, no ordering, wrong square axis) and the tests caught
all of them. The real-picture results reproduced exactly (b3 at small
tried 10x13 first, then stored 10x11). The regression set gave 94 passed,
4 skipped. The full suite has 38–39 failures on both the branch and a clean
extract of `main`, with identical sets apart from flaky async wave1/wave2
tests. Minors:
(1) the adjustment line was recorded before the quality filter and
storage, so a rescued puzzle the filter then drops was still announced as
generated;
(2) the square-extent rule followed the card literally but misfired at the
top of the range: 30x30 for a slightly landscape picture could only become
29x30, a portrait grid;
(3) a non-abandon error on a neighbour attempt (e.g. a solver timeout)
replaced the predicted extent's abandonment message.
Out of scope: the area tie-break can never fire with integer dimensions.
Worst-case cost per abandoned picture: 3 calls × 6 solves, up to 90s in the
request against 30s before. Measured calls take 0.00–0.04s. Severity gate
OPEN.

[Fix delta after cycle 1] All three Minors fixed:
- (1) the adjustment is appended after `generated_count += 1`, so only
  stored puzzles are announced;
- (2) a square extent now moves only toward the picture's shape: grow its
  longer axis or shrink its shorter one, so 30x30 for a landscape picture →
  30x29. This refines the card's own square-extent rule, and AC-6's "short
  side unchanged" reads, for a square, as "never away from the picture's
  shape";
- (3) on a neighbour, any other `NonogramError` ends the retry and the
  predicted extent's abandonment is reported. On the predicted extent the
  AC-4 behaviour is unchanged.
New tests: the quality-filtered rescue announces nothing; a neighbour's
different error reports the abandonment; the 30x30 and 20x20 square cases;
the corpus assertion is updated for squares. Red check: against `3a559fa`
these 4 tests fail and the other 10 pass. Regression set: 96 passed,
4 skipped. Commit `4d68ac2`.

[Review 2/3] Score: 9.5 — crit: 0, imp: 0, minor: 1 (confirmation mode, delta 3a559fa..4d68ac2)
[Review sync] 1 report(s) → meta/review/ (20260911T165447Z-CARD-062-cycle2.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 2 summary: pure confirmation. It re-verified AC-1..AC-6 and G-1, G-2
and G-4, and carried G-3. It compared the old and new square rules over
63,126 square cases (every in-range square × 3,006 source shapes). The new
candidate never keeps less of the picture, non-square extents are
unchanged, and no square gets zero candidates or its own extent. It drove
`_generate_image_puzzle` through 80 mixes of success, abandon,
`NonogramError` and generic error: 0 mismatches, never raises `None`, at
most 3 calls. The 4-fail/10-pass red check reproduced. Regression set:
97 passed, 4 skipped. Minor: the card body still stated the old square
rule; amended above in step 1 and AC-6 at done. Out of scope: a generic
(non-`NonogramError`) exception on a neighbour still replaces the
abandonment message; no reachable trigger was found (the only bare raise on
the image path is `pragma: no cover`). Severity gate OPEN. Cleared on
cycle 2 of 3.

[8h spot-check] 2/2 sampled holds reproduced independently: the adjustment
append is directly after `generated_count += 1` (`app.py:431-433`);
1010x1000 at 30x30 → `[(30, 29)]`.

[AC/EC check] All criteria/guardrails ✓ (evidence):
AC-1 ✓ demonstrated — patched-route rescue test; real b3/c12/c14 stored at the neighbour extent (reproduced by both reviewers).
AC-2 ✓ demonstrated — exact results line and 3-line cap tested; a quality-filtered rescue announces nothing.
AC-3 ✓ demonstrated — at most 3 calls and the predicted extent's own message; 80-sequence drive, 0 mismatches.
AC-4 ✓ demonstrated — a non-abandon error at the prediction is raised after one call; the mutant was caught.
AC-5 ✓ demonstrated — one call on success.
AC-6 ✓ demonstrated — 2000-case corpus plus square/edge unit tests, under the step-1 square rule as amended.
G-1..G-4 ✓ demonstrated — empty diffs over the guarded paths and templates; nudge bound unchanged; no repeated extent.

[Commit] 2 commits on the branch: 3a559fa (implementation + tests),
4d68ac2 (cycle-1 minors).
