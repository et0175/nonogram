# CARD-297: The table of contents and the answer pages as operators — the solution tiles, their headers, and the QR slot

**Status:** in progress
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/297-toc-and-answer-pages-as-operators
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-297
**Source:** ADR-0042 (DEC-048), 2026-10-25; CARD-293's spike §6 item 4 (the non-puzzle pages, less the guide — CARD-296 — and less the dividers, which the owner left raster). Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 64
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** CARD-294, CARD-295, CARD-227
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_solved_answer_key.py, tests/test_book_toc.py, tests/test_book_answer_key.py, tests/test_book_qr_slot.py, tests/test_layout_answer_tiles.py
**Review score:** —
**Started:** 2026-10-29
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The two remaining vector page kinds ADR-0042/R1 names, now that the puzzle page
(CARD-295) and the guide (CARD-296) are done:

1. **The table of contents** — its rows, the puzzle numbers, names and folios,
   and its leader dots.
2. **The answer pages** — the solution tiles with their grids, each tile's header
   (number, picture name, difficulty dots), the level headings and the SOLUTIONS
   divider's text. **The answer key is the only place the book prints a picture's
   title** (ADR-0037/R1, FR-033/AC-194) — that stays exactly true.
3. **The QR slot**, where the page reserves one. The QR *glyph* is a grid of
   black squares, so it is rectangles, not an image — but see G-4: making the QR
   codes real and scannable is CARD-210's, and it is blocked.

The answer tiles' grids should reuse CARD-295's grid routine rather than growing
a third copy — same reasoning as CARD-296's AC-4.

**Depends on CARD-295** and not only on CARD-294, because of that reuse: the tile
is a small puzzle grid, and the dependency is what stops this card reimplementing
one.

## Acceptance criteria

- **AC-1** (neither page kind carries a bitmap): *Given* an interior whose TOC
  and answer pages are written by this card, *then* no page of either kind
  references an image XObject. (test:
  `TestAnswerAndTocPages_CarryNoImageXObject`.)
- **AC-2** (the answer key still prints the title, and it is still the only place
  that does): *Given* a book, *then* each solution tile's header carries the
  picture's name, and no puzzle page anywhere in the interior does. (test:
  `TestAnswerKey_IsTheOnlyPlaceTheTitleIsPrinted` — the second half is the half
  that can fail, and it must be asserted over the whole interior, not over the
  answer section.)
- **AC-3** (the tiles are the grid routine, not a third copy): *Given* the
  answer tiles, *then* they are drawn through CARD-295's grid routine, derived
  from the module's AST and default-DENY per ADR-0039/R2. (test:
  `TestAnswerTiles_ReuseTheGridRoutine`.)
- **AC-4** (the TOC's rows say what the page plan says): *Given* a book, *then*
  every TOC row's number, name and folio equals the page plan's, read from the
  **written PDF's content stream** and compared against the plan — not against a
  rendered bitmap. (test: `TestToc_EveryRowMatchesThePagePlan`.)
  **CARD-219 already moved this file's assertions off pixels and onto the page
  plan** — seven positional tests converted, `solved_puzzle_page` renders
  **1225 → 175 (−85.7 %)**, the file's AC-1 group down to **0.78 s**. Build on
  that; do not reintroduce a render to check a number the plan states.
- **AC-5** (the difficulty dots on a tile header are the priced primitive):
  *Given* a tile header's dots, *then* they render as round shapes at the stated
  diameter, read back by poppler. (test:
  `TestAnswerTileHeader_DifficultyDotsAreRound` — the same primitive CARD-294
  priced and CARD-296 first used; three users, one implementation.)
- **AC-6** (the answer caption's face still holds the floor): *Given* the vector
  answer pages, *then* the answer caption holds CON-020's 10 pt floor, asserted
  against the stream's `Tf` sizes. (test:
  `TestAnswerPages_CaptionHoldsTheFloorInTheStream`. Note the caption is **omitted
  on the 10×10 cm minimum trim** — CARD-197's AC-6 omits it rather than overlap
  the drawing — so the assertion must be conditional on the profile exactly as
  `tests/test_book_interior_type_floor.py:369` already is, or it will fail on
  `min-trim` for the wrong reason.)

## Engineering constraints

- **EC(ADR-0042/R3):** neither writer derives geometry, across every book profile
  and every tile count per page. test:
  `PropertyTest_AnswerAndToc_WriterDerivesNoGeometry`.
- **EC(ADR-0037/R1):** across a seeded corpus of books, the picture's title
  appears on answer pages and nowhere else in the interior. test: AC-2's test
  extended over the corpus, with a minimum case count asserted inside it.

## Guardrails

- **G-1: do not redesign either page.** CARD-232 makes solutions fixed tiles four
  to a page in a 2×2 grid; CARD-233 gives a tile one header; CARD-209 packs
  wide-but-short solutions three to a page. **All three are queued and gated.**
  This card ports today's design to the new medium so those cards are written
  against a vector page from the start.
- **G-2: do not touch the SOLUTIONS divider's page as a raster surface.** The
  section dividers stay raster by the owner's 2026-10-25 decision and CARD-231
  redesigns them. The divider's *text* is a face CON-020's `:355` sibling
  requires to keep being recorded — leave that path drawing as it does.
- **G-3: do not touch the cover.** Raster by ADR-0042/R2.
- **G-4: do not make the QR codes real.** CARD-210 — *"Each puzzle's QR code
  becomes a real, scannable link"* — is **blocked**, waiting on the URL base
  CARD-285 produces. This card draws the slot as it is drawn today, in operators.
  A card that helpfully makes the QR scannable has taken a blocked card's scope.
- **G-5: this file holds the suite's largest pixel concentration — convert only
  this card's page kinds.** `tests/test_book_solved_answer_key.py` alone has **47
  pixel-reading sites**, the most of any file in the tree
  (`meta/profiling/adr-0042-migration-census.md`). Convert the answer/TOC ones;
  leave the rest to CARD-299, and do not reach into
  `tests/test_book_export_interior_cover.py` — it is CARD-276's (in flight),
  CARD-287's and CARD-292's at once.
- **G-6: no test deleted, renamed, skipped or merged — `parametrize` ids
  included.** (**gate**: node-id set difference with `-o addopts=''`.)
- **G-7: corpus minimums are never lowered;** `tests/fixtures/**` is never
  regenerated.
- **G-8: probes stay OUT of `tests/`** — `RENDER_HEAVY_SNAPSHOT` greps
  `solved_puzzle_page` and `puzzle_pages` among its eight idioms, and
  `tests/test_book_toc.py` is already in its 33-entry snapshot.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators; no image XObject (check: review-lens → CARD-298)
- ADR-0042/R2 — a raster page needs a declaration with a live reason (check: review-lens → CARD-298)
- ADR-0042/R3 — the writer consumes positions and derives none (check: review-lens)
- ADR-0036/R2 — the answer tiles are laid out by COMP-007's layout with the book's PageSpec (check: review-lens)
- ADR-0037/R1 — the answer key is the only place the title is printed (check: review-lens)
- CON-020 — no interior text for the reader below 10 pt at the page's own resolution (check: TestInteriorType_EveryFaceHoldsTheFloor)
- INV-013 — the interior holds no cover page and parity counts from interior page 1 (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived and default-DENY (check: review-lens)
- ADR-0006/R1 — the dependency baseline is exactly stdlib + Pillow + NumPy (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)

## Architecture context

- **FR:** FR-033 (AC-194 — the title's one home), FR-042 (the answer key), FR-040, FR-041, FR-043
- **NFR:** NFR-008
- **ADR:** ADR-0042 (R1, R2, R3), ADR-0036/R2, ADR-0037/R1, ADR-0039/R1-R2
- **Components:** COMP-009; COMP-007's layout consumed
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- **CARD-219's work is the precedent to copy, not just respect.** It converted
  `tests/test_book_toc.py`'s positional assertions to read the page plan and
  measured the result: page bitmaps **2712 → 556 (−79.5 %)**, interleaved wall
  clock **17.86 → 5.65 s median (−68 %)**. It also left a fence —
  `test_the_drawn_tie_is_still_carried_here` — so a later card cannot quietly
  undo the conversion. Read that fence before touching the file.
- `src/nonogram/admin/book_pdf_generator.py` is a `conflict.hotspot`.

## [Reuse claim VERIFIED — 2026-10-26, orchestrator] AC-3 stands; CARD-295's round was wrong about its own routine

CARD-295's implementation round reported that this card's central reuse claim
does not reach: *"an `AnswerTile` is explicitly not a `Layout` and carries no
`GridLine`s … its tile grid needs either lines from COMP-007 or its own walk"*,
and recommended correcting AC-3 before dispatch. **That is false, and AC-3 needs
no correction.** Measured rather than read:

- **`AnswerTile` carries `GridLine`s.** `dataclasses.fields` gives it
  `vertical_lines: tuple[GridLine, ...]` and `horizontal_lines: tuple[GridLine, ...]`
  — the same two fields `Layout` has, alongside `thin_rule`, `thick_rule` and
  the four `grid_*` edges.
- **The routine does not take a `Layout`.** CARD-295 built
  `draw_grid_lines(stream, verticals: Sequence[GridLine], horizontals: Sequence[GridLine], *, grey)`,
  and `draw_ruled_grid(stream, layout, …)` is only the `Layout` convenience door
  onto it. It reads `line.start`, `line.end`, `line.position` and `line.width`
  and nothing else.
- **Driven functionally**: an `AnswerTile` built from a real layout's lines (11
  vertical, 11 horizontal) was passed straight to `draw_grid_lines` — *OK, no
  `Layout` involved*. (The probe then raised on my own counting code, which
  called `.count(' m')` on the `bytes` that `render()` returns; the drawing call
  itself succeeded.)

**The irony is worth keeping, because it is the wave's pattern inverted.** That
round *designed* the sequence-taking signature precisely so a non-`Layout` caller
could use it — "the split IS the consumability the dispatch asked for" — and then
reported that a non-`Layout` caller could not. Nine rounds on this board have
disagreed with their brief and been right; this is the first to disagree with
**itself** and be wrong, by **understating** its own work rather than overstating
it. Had the note been relayed and AC-3 "corrected", it would have **removed a
true requirement and licensed a third grid copy** — exactly what AC-3 exists to
prevent.

**Dispatch status: NOT dispatchable.** Two of three dependencies are unmet —
CARD-295 is `in_progress` (review cycle 1), CARD-227 is `ready` and unstarted.

## [Dependencies MET — 2026-10-29, orchestrator] superseding the line above; dispatched into wave 64

All three are `done` and merged, re-read from the card files rather than from
the board: **CARD-294** `b850bbbd`, **CARD-295** `ec6e4a06`, **CARD-227**
`8579094a` (wave 63, merged 2026-10-28). The reuse claim AC-3 rests on was
already verified above against CARD-295's real signature, and that signature is
now on main — so AC-3 is checkable, not predicted.

**Conflict graph, measured at dispatch rather than taken from the `Wave:`
comments.** CARD-301 is the wave's other card:
`CARD-301 ∩ CARD-297 = ∅` (3 paths vs 6, all nine present on disk), overlap
`0/min(3,6) = 0.000` against `max_overlap 0.3`. Hotspots: this card holds
`src/nonogram/admin/book_pdf_generator.py`, CARD-301 holds **none** of the
eight, so the shared-hotspot rule does not fire either. **Concurrent, under
the owner's cap of 2.** The `meta/architecture/requirements.yml` edge that
serialized CARD-301 against CARD-284 is moot — CARD-284 merged at `8492b63c`.
