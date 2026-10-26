# CARD-295: The puzzle page as operators — the grid, the frame, the clue digits and the band, drawn from the Layout it is handed

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/295-puzzle-page-as-operators
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-295
**Source:** ADR-0042 (DEC-048), 2026-10-25; CARD-293's spike §6 item 3. Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 61
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** CARD-294
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf_band.py, tests/test_book_cell_size.py
**Review score:** —
**Started:** 2026-10-26
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

## [Routed in from CARD-294 cycle 2 — 2026-10-25, N-2] `_cap_height`'s three paths, two of them uncontrolled

**CORRECTED 2026-10-26: this is CARD-296's, not yours.** It was written here
first, on the orchestrator's claim that you are "the first card that centres
strings on `FontMetrics`". You are not: wave 61 is ordered **guide-first**, so
CARD-296 runs before you, and its item 3 draws *"the explanatory body text and
headings, in the embedded face"*. The full routing now lives on **CARD-296**.

**You inherit it only if CARD-296's round declines it** — which that card is
told to do explicitly rather than silently. Read the rest of this section as
background either way, because you set the clue digits in the same face and the
silent-zero hole below would reach them too.

CARD-294 fixed a real 10.8 % error in `_cap_height` (`src/nonogram/admin/book_vector.py`):
`font_metrics` had fallen back to `0.7 × ascender`, and the bundled DejaVuSans
ships `OS/2` **version 1, 86 bytes, with no `sCapHeight` at all**, so the
fallback was *always* what shipped — **650**/1000 em where FreeType measures
**729**. It now reads `H`'s own `glyf`/`loca` bounding box and reproduces
FreeType exactly. The existing poppler control had absorbed the error because
its tolerance is 15 % and the error was 12.2 %.

**What CARD-294 did NOT control, measured by its cycle 2 and inherited by you:**
the function has three reachable paths and the shipped face exercises exactly
one (`OS/2` v1; `indexToLocFormat` **1**, i.e. long `loca`). Uncontrolled:

1. the **`OS/2 ≥ 2` branch** — which CARD-294's card *states* as behaviour
   ("version ≥ 2 still wins where a face has it") and no test exercises;
2. the **short-`loca`** branch (`indexToLocFormat == 0`), reviewed against spec
   but never executed — there is no short-`loca` face in this repo;
3. **both raises.**

All three were judged **correct on review**, so this is missing controls, not
missing behaviour. One residual hole is real rather than cosmetic: **a v2+ face
with `sCapHeight = 0` returns 0 with no fallback and no error** — a silent zero
in the number every string on your pages is centred on.

**Why it is yours and not CARD-294's:** the project ships exactly one face, and
at CARD-294's merge *no module under `src/` imports `book_vector` at all*, so the
risk was nil and the control had no consumer to be written beside. You give it
one. If you centre anything on `cap_height`, the cheapest honest control is a
synthetic face per branch (a v2 `OS/2` carrying a real `sCapHeight`, one
carrying `0`, and a short-`loca` face) rather than a comment asserting the
branches work — CARD-294's own cycle 1 critical finding was a control that could
not fail, and its cycle 2 N-1 was a figure whose scope was hand-held.

If you decide these controls are not yours either, **say so with a reason and
name who owns them** rather than passing them on silently: a declaration that
outlives its hole is the defect this board gates on most.

## [DISPATCH 2026-10-26 — wave 61, orchestrator] The grid routine's direction has REVERSED

**CARD-296 is PARKED, not merged**, so `src/nonogram/admin/book_guide_vector.py`
and its `draw_line_diagram` are **not on main** — they exist only in a kept
worktree at `0b91ab18`. CARD-296's AC-4 says *"CARD-295 should consume it rather
than write a second one"*. **That is now backwards.** You write the routine; the
card that re-enters consumes yours.

So: make it **consumable**. A routine that takes a `Layout` plus what to draw and
knows nothing about a puzzle page specifically is one CARD-296 can adopt; one
shaped around your page is a second implementation by another name, and that is
exactly what CARD-296's AC-4 exists to prevent.

**What IS on main:** CARD-294's vocabulary, `src/nonogram/admin/book_vector.py`
— the embedded face, the operator set, `round_mark`, `write_vector_pdf`. Merged
`b850bbbd`. Consume it; do not rebuild it.

**You also inherit CARD-296's F-302**, because you are the card its AC-4 exists
to constrain. Its default-DENY guard over "which routines may read a `Layout`'s
grid" has a measured hole: a frozen dataclass with one `sheet: Layout` field and
a `stroke` method draws a **complete second ruled grid** and passes — the
annotation arm reads *function parameters* only, and the rebinding arm skips an
`AnnAssign` with no value, which is what a dataclass field is. Five more escape
at helper level (tuple unpack, a `Layout`-returning helper, walrus, comprehension
target, `for` target, unannotated default). If you build a guard of that kind,
build it without that hole — or name the limit **by its shape** and say who owns
closing it.

## [Correction to the round's own handback — 2026-10-26, orchestrator]

The round's item 6 ("CARD-297's reuse, as its card words it, does not reach")
is **false**, verified at the source and functionally: `AnswerTile` carries
`vertical_lines`/`horizontal_lines` as `tuple[GridLine, ...]`, and this round's
own `draw_grid_lines` takes **two `GridLine` sequences**, not a `Layout` —
`draw_ruled_grid` is just the `Layout` door onto it. An `AnswerTile`'s lines
drive it directly, with no `Layout` involved.

So the routine's reach is **wider than its author claimed**. This is the first
round in this wave to be wrong by understating its own work; the standing
pattern has been the reverse. Recorded on CARD-297, whose AC-3 needs no change.
