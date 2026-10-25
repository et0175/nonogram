# CARD-295: The puzzle page as operators — the grid, the frame, the clue digits and the band, drawn from the Layout it is handed

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/295-puzzle-page-as-operators
**Worktree:** —
**Source:** ADR-0042 (DEC-048), 2026-10-25; CARD-293's spike §6 item 3. Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 61
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** CARD-294
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf_band.py, tests/test_book_cell_size.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The puzzle page — the book's dominant page kind — drawn as PDF content-stream
operators instead of a 25.2 MB raster bitmap written as a JPEG XObject.

The spike already prototyped exactly this page and measured it:
`scripts/card293_vector_probe.py`, **1.37 ms against 11.7 ms per page**, **407,976
B against 9,157,535 B for 24 pages**, and the clue digits rendered and read back
by poppler. This card productionizes that, consuming CARD-294's vocabulary.

1. **The grid** — cell lines, every-fifth-line rules, the outer border, at the
   weights and tones COMP-007's `Layout` states. See G-2: this card changes no
   weight.
2. **The frame** and the clue gutters.
3. **The clue digits**, set in the embedded face at the point size the layout
   gives, inside the clue cells.
4. **The band** — "Puzzle N · Tier" (ADR-0037/R1: the puzzle page never prints
   the picture's title; the answer key is the only place the title appears).

**Every coordinate, width and tone comes from `compute_layout` with the book's
PageSpec.** This card computes no geometry — ADR-0042/R3 restates ADR-0036/R2 for
exactly this reason: *a fresh renderer is where geometry gets re-derived by
accident.* If you need a number the `Layout` does not give you, that is a finding
to raise, not a number to compute here.

## Acceptance criteria

- **AC-1** (the page carries no bitmap): *Given* an interior whose puzzle pages
  are written by this card, *then* no puzzle page references an image XObject.
  (test: `TestPuzzlePage_CarriesNoImageXObject`. ADR-0042/R1's own derived test is
  CARD-298's, which checks *every* interior page kind at once; this one is the
  page-local control that fails first.)
- **AC-2** (the drawing is the layout's, not the writer's): *Given* a `Layout`,
  *then* every line position, stroke width and grey tone in the emitted content
  stream equals the value the `Layout` states, compared against an **independent**
  recomputation rather than against the writer's own output. (test:
  `PropertyTest_PuzzlePage_EveryCoordinateComesFromTheLayout` — genuinely
  multi-case over a seeded corpus of extents, trims and densities, with a minimum
  case count asserted inside the test so the corpus cannot silently shrink.)
- **AC-3** (the clue digits are right, and read by an engine that did not write
  them): *Given* a puzzle page, *then* each clue cell's digits match
  `clues.encode_line` for that row/column, read back from the rendered PDF by
  poppler. (test: `TestPuzzlePage_EveryClueDigitRendersWhereTheLayoutPutIt`. The
  spike did this with 540 digits; keep that order of magnitude.)
- **AC-4** (the band says what it always said): *Given* a puzzle page, *then* the
  band shows the number and tier and **not** the picture's title. (test:
  `TestPuzzlePage_BandCarriesNumberAndTierAndNeverTheTitle` — ADR-0037/R1.)
- **AC-5** (the interior shrinks, measured): *Given* the Book 1 corpus, *then*
  the written interior's puzzle-page bytes and generation time are recorded
  against the raster figures, and the direction matches the spike's. (**gate**:
  the two figures recorded with the load average at both ends, per CARD-292's
  AC-6 convention. A regression against the spike is a finding, not a rounding
  error.)

## Engineering constraints

- **EC(ADR-0042/R3):** the writer derives no geometry, for any page in any book
  profile — not a fallback, not a rounding, not a default when the `Layout` is
  silent. test: `PropertyTest_PuzzlePage_WriterDerivesNoGeometry` (multi-case: a
  `Layout` stub whose every accessor is recorded, asserting the stream contains no
  number the stub was not asked for).
- **EC(ADR-0042/R1):** no interior page this card writes references an image
  XObject, at any page count. test: AC-1's test, extended over the corpus.

## Guardrails

- **G-1: do not change a single rule weight or tone.** The instruction is
  unchanged by the owner's 2026-10-25 decision, but its **reason** is now the
  opposite of what it was, so read it again rather than from memory.
  **It was:** the weights were undecided, so nobody could ship them.
  **It now is:** the weights **are** decided — the owner chose 0.3 / 0.8 / 1.3 pt
  on CARD-293's proof, and ADR-0037/R2 carries them — but **CARD-227 is the card
  that lands them**, one wave after this one (wave 62). This card draws the grid
  at **the weights COMP-007 computes today**, so that the weight change arrives
  as one reviewable diff in one place instead of being smuggled into the medium
  change where no test is watching for it.
  There is also a concrete cost to grabbing it: **CARD-298 records the book
  baselines once**, deliberately after CARD-227, so a single recording captures
  both the medium and the widths. Shipping 0.3 pt here makes the phase pay for
  two baseline recordings and muddles which change moved which bytes.
- **G-2: do not touch `src/nonogram/export/**`.** The `Layout` is consumed, never
  changed. CON-019 holds the CLI and web exports byte-identical.
- **G-3: do not touch the cover or the dividers.** Raster by ADR-0042/R2 and by
  the owner's 2026-10-25 decision respectively. Read
  `meta/profiling/adr-0042-migration-census.md`'s "What is not in the set".
- **G-4: do not convert this file's pixel assertions wholesale.** The three test
  files in `Touches:` hold **50 pixel-reading sites** between them
  (`test_book_pdf_band.py` 41, `test_book_puzzle_frame.py` 7,
  `test_book_cell_size.py` 2). Convert the ones about **this page kind**, leave
  the rest, and do not reach into files this card does not own —
  `test_book_solved_answer_key.py` (47 sites) is CARD-297's.
- **G-5: no test deleted, renamed, skipped or merged — including `parametrize`
  ids.** The collected node-id set loses nothing. (**gate**: set difference with
  `-o addopts=''`; removals 0, additions named. **A reworded param id is a deleted
  node id** — CARD-282's fix round nearly shipped exactly that.)
- **G-6: corpus minimums are never lowered;** `tests/fixtures/**` is never
  regenerated.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators; no image XObject (check: review-lens → CARD-298)
- ADR-0042/R3 — the writer consumes positions and derives none (check: review-lens)
- ADR-0042/R7 — no rule weight is set here; ADR-0037 is not revised (check: review-lens)
- ADR-0036/R2 — book page geometry is COMP-007's `compute_layout` with a PageSpec (check: review-lens)
- ADR-0037/R1 — the puzzle page never prints the picture's title (check: review-lens)
- CON-018 / INV-006 — the printed cell never falls below 4.75 mm (check: TestBookCellSize_HoldsTheFloor)
- CON-020 — no interior text below 10 pt, clue digits excepted — their size follows the cell (check: TestInteriorType_EveryFaceHoldsTheFloor)
- CON-019 — book geometry never changes the CLI's or web UI's exports (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0006/R1 — the dependency baseline is exactly stdlib + Pillow + NumPy (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)

## Architecture context

- **FR:** FR-033 (the puzzle page's band and line thresholds — **its figures are untouched here**, see G-1), FR-041 (the printed grid's rules)
- **NFR:** NFR-008
- **ADR:** ADR-0042 (R1, R3, R7), ADR-0036/R2, ADR-0037/R1, ADR-0039/R1
- **Components:** COMP-009; COMP-007's layout consumed
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- `src/nonogram/admin/book_pdf_generator.py` is a `conflict.hotspot` and every
  card in this phase touches it — `run` serializes them whatever the wave says.
- The spike's 41-line content-stream assertion is the model for AC-2's shape, and
  it **passes at 0.48 pt and fails at 0.3 pt** (its AC-4), so it discriminates on
  exactly the quantity G-1 forbids changing. Reuse the shape, not the thresholds.
