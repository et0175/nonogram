# CARD-144: A frame around the puzzle on book pages — the clue bands boxed, the CLI untouched

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/144-book-puzzle-frame
**Worktree:** ../PythonProject4-CARD-144
**Source:** owner, 2026-09-23 ("I'd add a frame around puzzle, around the top and left sides"), shape and scope settled by AskUserQuestion the same day
**Idea:** —
**Wave:** 26
**Depends on:** CARD-141
**Touches:** src/nonogram/export/layout.py, src/nonogram/export/png.py, src/nonogram/export/pdf.py, tests/test_book_puzzle_frame.py
**Review score:** —
**Started:** 2026-09-24T18:09:15Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

A book puzzle page draws the clue bands as bare numbers beside the grid. The owner asked for
the classic framed look: one rectangle around the whole block, with the clue bands boxed off
from the grid and an empty corner box.

    +---+-------+
    |   | 2   1 |      <- column clue band, boxed
    |   | 1   3 |
    +---+-------+
    | 1 | | | | |
    | 2 | | | | |      <- row clue band, boxed
    | 3 | | | | |
    +---+-------+

1. **Book pages only.** The owner chose this over framing standalone exports, so CON-019
   stands and the golden A4 fixtures are not touched. Carry it as a new optional `PageSpec`
   field defaulting to *off*, so `compute_layout` called without a PageSpec produces exactly
   today's A4 geometry and ink (ADR-0036/R1). The book's PageSpec turns it on; the CLI and
   web paths never do.
2. **The frame is ink, not geometry.** Draw it on the boundaries the layout already computes
   — the outer edge of the clue gutters and the grid's existing outer border, which already
   serves as the divider between band and grid. The cell size, the drawing's position and
   the gutter depths must not move by a single pixel: every measured figure stays as it is
   (4.97 mm on the 30x30 with 9-deep clues, 7.5 mm on the 15x15, the two-up 7.39 mm pair).
   If a cell figure changes, the implementation has gone wrong.
3. **Weights follow ADR-0037/R2.** The frame uses the heavy rule — the same weight as the
   grid's outer border, twice the thin rule, pure black. It must not introduce a third
   weight.
4. **Both trims.** The owner likes 6x9 and 8.5x11 alike, so the frame must sit correctly on
   any stored trim and on both page parities, and on a two-up page it frames each puzzle of
   the pair separately, not the pair as a whole.

Out of scope: framing answer-key tiles (they are a packed grid of their own and the owner
did not ask), the guide, divider or cover pages, and any change to the band that carries
"Puzzle N · Tier".

## Acceptance criteria

- New: on the book PageSpec a puzzle page carries a closed rectangle around clues and grid,
  with the clue bands boxed and the corner empty.
  test: TestPuzzleFrame_BookPageCarriesTheFrame
- New: `compute_layout` without a PageSpec, and every CLI/web export, are byte-identical to
  before this card.
  test: TestPuzzleFrame_DefaultPageSpecIsUnchanged
- New: the cell size and drawing origin on the book PageSpec are unchanged by the frame, for
  a 30x30 with 9-deep clues and a 15x15.
  test: TestPuzzleFrame_GeometryIsUnmovedByTheFrame
- New: every frame rule is the heavy weight, at least twice the thin rule, in pure black.
  test: TestPuzzleFrame_UsesTheHeavyRuleOnly
- New: on a two-up page each puzzle is framed separately.
  test: TestPuzzleFrame_PairIsFramedPerPuzzle

## Guardrails

- G-1: CON-019 — CLI and web A4 output stay byte-identical, and
  `tests/fixtures/a4_golden/**` is NOT regenerated or edited. The tripwire must not move at
  all. test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden,
  PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry
- G-2: ADR-0037/R2 — thin rules at least 0.25 mm, heavy exactly twice the thin, pure black.
  No new stroke weight.
- G-3: Geometry is unchanged. This card adds ink only; no cell fitting, gutter depth or
  origin may move. CARD-116's and CARD-118's measured figures stay green.
- G-4: Do not edit `src/nonogram/admin/**` — the panel decides no geometry (ADR-0036/R2).

## Architecture context

- **FR:** FR-041 (book page layout)
- **CON:** CON-019 (byte-identity), CON-018 (margins)
- **ADR:** ADR-0036 (PageSpec, geometry ownership), ADR-0037 (stroke weights)
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner, 2026-09-23, reviewing the CARD-118 proof renders on both trims. The frame
  shape was chosen from three sketches (boxed clue bands, one plain outer rectangle, or an
  open top-and-left L) and the scope from two (book pages only, or everywhere). The owner
  took the boxed clue bands, book pages only — explicitly keeping CON-019 intact rather than
  amending it and regenerating the goldens.
- [Why it waits for CARD-141] Both edit `src/nonogram/export/layout.py`.

- [What shipped] `PageSpec` gains an optional `frame: bool | None = None` and a
  resolved `PageSpec.framed`; `Layout` gains `frame: PuzzleFrame | None = None`,
  built by one helper that both `compute_layout`'s placed path and
  `_slot_layout` (two-up) call. `png._draw_frame` strokes it after the grid.
  `pdf.py` needed no code — both its pages are the PNG raster, so the frame
  arrives on the blank page and on the revealed one for free; only its
  docstrings changed. New file `tests/test_book_puzzle_frame.py`, 45 tests.

- [Frame vs boundary — the decision, and where it is pinned] The frame is drawn
  **on** its four boundaries, so Pillow centres each stroke there and half a
  heavy rule (3 px of 6, 0.25 mm) falls outside the drawing box on every side.
  That is the same thing the grid's own outer border already does — it hangs
  3 px right of `grid_right` — and the frame's right and bottom sides *are*
  that border, so an inset frame would sit a full rule out of step with the two
  sides it continues. Measured on a rendered page, the frame's left rule
  occupies offsets `-2..+3` about the drawing's left edge and the grid's right
  border the identical `-2..+3` about `grid_right`.
  `TestPuzzleFrame_UsesTheHeavyRuleOnly.test_the_frame_straddles_its_boundary_exactly_as_the_grids_border_does`
  requires those two offset lists to be equal and to straddle zero, so an
  inset frame and a half-rule-out-of-step frame both fail it.

- [Deviation from the card: what turns the frame on] The card says "the book's
  PageSpec turns it on", but the book's `PageSpec` is built in
  `src/nonogram/admin/book_page_spec.py`, which guardrail G-4 forbids editing.
  The frame is therefore defaulted rather than set: `frame=None` (the default)
  means *a placed page is framed, a drawing-sized image is not*, which is
  "book pages only" stated in COMP-007 — the component ADR-0036/R2 says owns
  print geometry — instead of in the panel. `DEFAULT_PAGE_SPEC.framed` is
  False, so CON-019 is untouched, and an explicit `frame=True/False` still
  overrides either way. No file under `src/nonogram/admin/**` was edited.

- [Known gap, and it is G-4's] A **two-up** page is composed by
  `admin/book_pdf_generator._stroke_drawing`, which deliberately reimplements
  the grid stroking from `slot.vertical_lines`/`slot.horizontal_lines` and so
  does not draw `slot.frame`. The pair geometry *is* framed per puzzle —
  `compute_pair_layout` gives each slot its own `PuzzleFrame` on its own
  drawing box, which `TestPuzzleFrame_PairIsFramedPerPuzzle` pins — but nothing
  yet strokes it, so a printed two-up page has no frame. Closing it is one line
  in `_stroke_drawing` (stroke `slot.frame` after the lines), in a file G-4 put
  out of bounds for this card. Measured, not assumed: interior page 3 of the
  CARD-145 baseline book (the two-up page) is byte-identical to its
  pre-frame recording, while interiors 2 and 4 (the single-puzzle pages) moved.
  **A follow-up card is needed for the two-up rendering.**

- [Geometry] Unmoved, as the card requires: the 30x30 with 9-deep clues still
  prints at 4.97 mm and the 15x15 at the 7.5 mm cap, and
  `replace(framed_layout, frame=None) == unframed_layout` holds field for
  field over a seeded corpus of 240 cases across three trims (8.5x11, 6x9,
  7x10) and both parities. Every CARD-116/CARD-118 measurement stayed green
  once the ink measurer was taught about the frame (below).

- [SCOPE+ — test helpers and the book baseline] The frame is ink, so everything
  that measures a book page off its ink had to learn it exists:
  - `SCOPE+ tests/helpers/page_ink.py` — `drawing_of` counts grid rules by
    counting full-extent ink runs, and the frame's left and top sides are two
    more of those, so `columns`, `rows` and therefore the measured cell were
    all one out. It now tells the frame from the grid the way it tells
    everything else — by where it is: the leftmost full-height rule is the
    frame's exactly when its own ink covers the point the horizontal rules
    start from. No call site changed.
  - `SCOPE+ tests/helpers/two_up_ink.py` — `split_row` cut at the widest gap
    between rule rows, and on a framed single page the frame-top-to-grid-top
    gap (a whole clue gutter, 4 cells) is wider than the 12 mm band that
    separates two slots, so a one-puzzle page was being cut through its own
    gutter. The cut now goes through the widest gap **no vertical rule
    crosses**, which is a real property of the page rather than a ratio, and
    `_GAP_RATIO` is gone.
  - `SCOPE+ tests/fixtures/book_baseline_card144.json` (new),
    `tests/fixtures/book_baseline_card145.json` (+2 fields),
    `tests/helpers/book_corpus.py`, `tests/test_book_pdf_memory.py`
    (docstring) — CARD-145 recorded a per-page pixel baseline of the book's
    interior. This card deliberately changes two of those eight pages, which
    is exactly the case that fixture's own `warning` provides for: "a later
    card that deliberately changes a page's content records a NEW baseline in
    a commit of its own, with its own card number, and says so here." Done as
    written — new fixture under this card's number naming the two changed
    pages and why, `BASELINE_FIXTURE` repointed, the old file left otherwise
    unedited with a `superseded_by`/`superseded_note` pair. No digest was
    rewritten to make a test fail less.

- [G-1] `tests/fixtures/a4_golden/**` untouched;
  `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` and
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` were run
  first and stayed green throughout.

- [The stale FR-042 formula at requirements.yml:3295] Not depended on. Answer
  tiles are out of this card's scope, nothing here sizes anything from that
  formula, and `compute_answer_page_layout` was not touched — a test asserts
  an answer tile carries no frame. The staleness CARD-141's review found is
  still there for whichever card owns it.

- [Proof renders] `~/Documents/nonogram-reviews/CARD-144/` — the CARD-118
  proof pages on both trims (8.5x11 and 6x9), now framed, plus interior pages
  2, 3 and 4 of the baseline book, which show the framed single pages beside
  the still-unframed two-up page.

[Touches drift] tests/fixtures/book_baseline_card144.json, tests/fixtures/book_baseline_card145.json, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/helpers/two_up_ink.py, tests/test_book_pdf_memory.py — 6 files beyond Touches, all declared SCOPE+
[Runtime conflict] OBSERVED, not predicted: CARD-144 and CARD-128 are both editing tests/fixtures/book_baseline_card145.json, tests/helpers/book_corpus.py and tests/test_book_pdf_memory.py. Neither card's Touches named them, so the conflict graph could not serialize them. Both are independently re-recording CARD-145's per-page book baseline for their own change. Merge order matters and the second card must re-record, not resolve textually.
[Unmet AC] The "two-up framed per puzzle" AC passes as GEOMETRY only. A printed two-up page carries NO frame: admin/book_pdf_generator._stroke_drawing composes it from slot.vertical_lines/horizontal_lines and never draws slot.frame. Measured, not assumed — interior page 3 is byte-identical to its pre-frame recording while pages 2 and 4 moved. The fix is one line in a file G-4 put out of bounds, and which CARD-128 is editing right now.
