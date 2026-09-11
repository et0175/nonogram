# CARD-062: Admin batch — retry an abandoned picture at long side ±1 before giving up

**Status:** ready
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
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
   For a square extent the "long side" is ambiguous; use the axis the picture
   is longer on (width when the picture is square).
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
  short side than predicted; candidates follow the ordering rule in step 1
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
