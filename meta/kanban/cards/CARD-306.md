# CARD-306: The vector puzzle page grows its sheet furniture — folio, frame rules, grid-size label and QR block — because a page with no number cannot ship

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** `src/nonogram/admin/book_puzzle_vector.py`'s own module docstring, which raises the gap and names CARD-298 for it; CARD-295's handoff; confirmed by CARD-298's implementation round, 2026-10-29. Cut by the orchestrator on owner decision after CARD-298 hit the scope gate.
**Idea:** —
**Wave:** 67
**Created wave:** 65
**Deferred waves:** 0
**Depends on:** CARD-298, CARD-299
**Touches:** src/nonogram/admin/book_puzzle_vector.py, src/nonogram/admin/book_vector.py, tests/test_book_puzzle_page_vector.py, tests/test_book_pdf.py, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

**No card owns this, and three cards have now each discovered it.**
`book_puzzle_vector`'s own docstring states the gap and names CARD-298 as the
card that will close it — *"the card that makes the medium real per page is
CARD-298, and it cannot land a vector puzzle page that has no page number on
it."* CARD-298 was narrowed to the mechanism card on 2026-10-29 and **cannot**
close it. CARD-295 made the same attribution. So the gap has been correctly
identified twice and assigned twice to a card that does not own it.

Measured on `main` after CARD-298's round: `book_puzzle_vector` draws the puzzle
grid and its clues and **no sheet furniture at all** — no folio (page number), no
frame rules, no grid-size label, no QR block. The raster path draws all of it in
`book_pdf_generator`: `_draw_page_frame` (whose footer is **all-or-nothing**),
`_draw_qr_caption`, and the QR checkerboard.

**The ordering constraint that makes this a separate card rather than a clause.**
A vector puzzle page cannot ship before (a) CARD-298's per-page medium exists —
done — and (b) CARD-299's readers stop asserting one image XObject per page. Until
both land, furniture code written here is unreachable, and unreachable drawing
code cannot be reviewed against a render. CARD-298's round declined to write it
for exactly that reason (~400 lines behind a blocker), and that judgement is
adopted rather than re-litigated.

## What to implement

1. **The folio.** The page number, in the position and face the raster path uses.
   Derive the position from the same `PageSpec`/layout source the raster footer
   reads — do **not** transcribe coordinates. `_draw_page_frame`'s footer is
   all-or-nothing, so the vector version must be too: a page with a frame and no
   number, or a number and no frame, is a defect, not a degraded state.
2. **The frame rules**, at the stroke weights ADR-0037/R2 and FR-033 pin. These
   already have property tests reading drawn ink
   (`tests/property/test_book_layout.py:364`,
   `tests/property/test_book_two_up.py:682`) which CARD-299 re-expresses against
   the stream — so this card's rules must satisfy the **re-expressed** versions,
   not today's pixel ones.
3. **The grid-size label.**
4. **The QR block.** The checkerboard is the part most likely to be approximated;
   it is a bitmap by nature. **Decide explicitly** whether the QR stays an image
   XObject on an otherwise-vector page — which CARD-298's machinery permits only
   via a declaration with a reason and an `expires_with` — or becomes drawn
   rectangles. Either is defensible; an undeclared one is not, and
   `page_medium`'s default-DENY will refuse the page rather than ship it.
5. **One definition per piece of furniture, not two.** The raster and vector paths
   must not each carry their own copy of the footer's geometry. Follow CARD-298's
   precedent in `book_vector.py` (`write_face_objects`/`write_vector_page` were
   made public precisely so the mixed writer did not transcribe the
   `/FontDescriptor` a second time).

## Acceptance criteria

- **AC-1** (the furniture is on the page): *Given* a vector puzzle page written
  through `_write_pdf`, *then* its content stream carries the folio, the frame
  rules, the grid-size label and the QR block — each asserted by its own operators
  in the stream, not by a rendered bitmap.
- **AC-2** (the footer stays all-or-nothing): *Given* a page where the folio is
  suppressed, *then* the frame is too, and vice versa — **both directions**, with a
  mutant for each.
- **AC-3** (one definition): *Given* the module AST, *then* the geometry of each
  piece of furniture is read from a single source shared with the raster path,
  derived and default-DENY per ADR-0039/R2 — a second transcription is a FAILURE.
- **AC-4** (the QR's medium is declared): *Given* the written page, *then* the QR
  block is either operators, or an image XObject covered by a live
  `_RASTER_DECLARATIONS`-style declaration with a reason and an `expires_with`.
  An undeclared XObject on a vector page must be **refused by the writer**, not
  merely reported.
- **AC-5** (an owner render exists): *Given* the converted page, *then* a rendered
  puzzle page is produced under `~/Documents/nonogram-reviews/CARD-306/` for the
  owner's visual check. **Standing rule: image-pipeline changes need a rendered
  eyeball, not just green tests.**

## Engineering constraints

- **EC(ADR-0037/R2, FR-033):** across a seeded corpus spanning trims, page counts
  and tier mixes, every frame rule on a vector puzzle page meets the stroke-weight
  floor read from the stream, with a minimum case count asserted inside the test.
- **EC(all-or-nothing footer):** across the same corpus, the count of pages
  carrying a folio equals the count carrying a frame.

## Guardrails

- **G-1: do not change the raster puzzle page's bytes.** Until this card's own
  conversion card flips the declaration, the shipped puzzle page is raster, and
  the 21 book baselines must not move. A baseline that reds here is a **finding**.
- **G-2: do not transcribe coordinates.** A magic number copied from
  `_draw_page_frame` is the defect AC-3 exists to catch.
- **G-3: no test deleted, renamed, skipped or merged — `parametrize` ids
  included.** (**gate**: node-id set difference with `-o addopts=''`.)
- **G-4: do not flip ADR-0042/R1.** R1 is true only when all four interior kinds
  are operators; this card converts one piece of one kind. R1's flip belongs to
  whichever card lands last. CARD-298 and CARD-299 each refused this flip for the
  same reason.
- **G-5: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`).

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators (check: review-lens — NOT this card's to flip)
- ADR-0042/R2 — a raster page is declared with a reason; an expired declaration is a defect (check: CARD-298's derived guard)
- ADR-0042/R3 — the writer consumes positions and derives none (check: review-lens)
- ADR-0037/R2, FR-033 — stroke weights (check: CARD-299's re-expressed stream readings)
- ADR-0039/R1 — a claim needs a control that CAN fail; two mutants, one at the claim's edge (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- CON-020 — the 10 pt interior type floor (check: CARD-299's re-expressed test)
- ADR-0006/R1 — the dependency baseline is exactly stdlib + Pillow + NumPy (check: **DEAD REF** — `TestDependencyBaseline_IsExactlyPillowAndNumpy` has zero definitions in this repo; verify the SUBSTANCE and see CARD-307)

## Architecture context

- **FR:** FR-033, FR-043, FR-030
- **NFR:** NFR-008
- **ADR:** ADR-0042 (R1, R2, R3), ADR-0037/R2, ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** no row is re-stamped here; R1's flip is a later card's.

## Worktree notes

- The puzzle page is the **only** interior kind the generator can already call:
  `book_pdf_generator:400` imports `book_puzzle_vector`, while
  `book_guide_vector:103`, `book_toc_vector:60` and `book_answer_vector:62` all
  import `book_pdf_generator` at module level and so cannot be called from its
  page walk without a cycle. That asymmetry is why the puzzle page is first and
  why the other three need a different assembly point — a fact worth carrying into
  whichever card converts them.
