# CARD-294: The interior's drawing vocabulary — the embedded face and the operator set, curves included, proved by an engine that did not write them

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/294-interior-drawing-vocabulary
**Worktree:** —
**Source:** ADR-0042 (DEC-048), 2026-10-25; CARD-293's spike §1 and §6 item 2. Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 60
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf_vector_primitives.py, tests/test_book_pdf.py, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card is first, and why it is `architectural`

It is the phase's **walking skeleton through the riskiest path**, and the risk is
one specific thing.

CARD-293 proved the mechanism cheap: **163 code lines** for font embedding,
**22.4×** smaller files, **8.5×** faster per page, and DejaVuSans embedded whole
costs **379,441 B Flate — less than ONE raster page (381,564 B)**, so glyph
subsetting is pointless. All of that is measured, in
`meta/profiling/card-293-vector-interior-comparison.md`, and the prototype that
measured it is committed at `scripts/card293_vector_probe.py`.

But the spike drew **one puzzle page**. Its G-3 said so explicitly, and §6 named
the consequence: *"nobody has priced redrawing the guide's worked example, the
pipeline diagram and the difficulty legend as operators."* Reading the spike's
own primitive table, the gap is concrete: it drew **straight lines, rectangles,
fills and text**. It never drew a **round shape**. The difficulty dots and the
guide's legend need curves — in PDF, cubic Béziers via the `c` operator, because
PostScript/PDF has no circle primitive — and that is **the only primitive in the
interior nobody has emitted or measured**.

So this card exists to price the unknown **first**, while it is still cheap to
learn the answer, instead of discovering it in the fourth card of a phase built
on the assumption that it is easy. That is the handoff ordering rule — maximum
uncertainty collapsed per unit effort goes first — applied honestly: if curves
turn out to be awkward, the phase finds out in card 1, not card 4.

`Complexity: architectural` on two of the four objective signals: it is the
**first implementation of ADR-0042**, and it lays the vocabulary every later
card in the phase copies.

## What to implement

A vocabulary, not a page. Nothing in this card draws a puzzle, a guide or a
table of contents — those are CARD-295, CARD-296 and CARD-297, and each consumes
what this card builds.

1. **The embedded face.** DejaVuSans, embedded **whole** and FlateDecoded once
   per file, as the PDF font objects (`/FontFile2` descendant, the descriptor,
   the widths). The face already ships: `src/nonogram/export/fonts/DejaVuSans.ttf`,
   declared as `nonogram.export` package data in `pyproject.toml:79`, reached
   today through `FONT_RESOURCE = "fonts/DejaVuSans.ttf"` (`export/pdf.py:139`,
   `export/png.py:106`). **Read it through the same resource mechanism** — do not
   add a second path to the same file, and do not add a dependency: ADR-0006/R1
   says a static asset shipping as package data *is not* a dependency change, and
   that is the clause this card relies on.
   - **Subsetting is deliberately not done** (ADR-0042/R5). It saves ~365 KB
     against a file that was 9 MB. If you find yourself writing a glyph-set
     walker, stop — that is the card growing past its slice.
   - **A base-14 substitute is forbidden** (R5), because every type measurement
     in this tree — `type_px`, the band face, the guide face, CON-020's 10 pt
     floor — is DejaVu's. Helvetica would silently change all of them.
2. **The operator set.** The content-stream vocabulary the page cards need:
   - text showing with an explicit `Tf` size (the operator CON-020's rewritten
     floor check will read — see CARD-299);
   - straight lines and rectangles, stroked and filled;
   - stroke widths in points, and grey tones via `g`/`G`;
   - **curves (`c`), for round shapes** — the unpriced primitive. Price it:
     report what a circle of a given radius costs in operators and in lines of
     code, and whether a four-Bézier approximation is accurate enough for a
     difficulty dot at the sizes the book actually prints.
3. **Report the price.** Append the measured cost of the curve primitive to
   `meta/profiling/card-293-vector-interior-comparison.md` (or a sibling
   artefact, if that file reads better left closed) — lines of code, operators
   per shape, and the verdict on accuracy. **This is a deliverable, not a note:**
   the phase's remaining four cards were scoped on the assumption that curves are
   cheap, and the next orchestrator needs the number rather than the assumption.
4. **Flip ADR-0042/R5's check.** R5's check is currently `{kind: review-lens}`
   with the planned test name in a comment beside it. Write
   `tests/test_book_pdf.py::test_the_interior_embeds_the_projects_own_face` and
   flip R5 to `{kind: test, ref: <that node id>}` **in the same change**. The
   lens is a placeholder for exactly this card; leaving it after the card merges
   is a rule that quietly stopped being verified.

## Acceptance criteria

This card is traced to no FR — the interior's *medium* is an ADR decision, not a
requirement, and ADR-0042/R7 is explicit that the ADR sets no reader-facing
figure. Its criteria therefore come from the ADR's rules, which is why the ECs
below carry the weight.

- **AC-1** (the face is the project's own, embedded whole): *Given* an interior
  PDF written by the new vocabulary, *then* it carries exactly one embedded
  FlateDecoded DejaVuSans font file and no base-14 reference, and the embedded
  bytes match `src/nonogram/export/fonts/DejaVuSans.ttf`. (test:
  `tests/test_book_pdf.py::test_the_interior_embeds_the_projects_own_face` — the
  node id ADR-0042/R5's comment names, so the flip in item 4 lands on a real test.)
- **AC-2** (the vocabulary is read back by an engine that did not write it):
  *Given* each primitive — text, line, rectangle, fill, grey, **curve** — *then*
  a PDF containing it is parsed and rendered by an **independent** engine
  (poppler, as the spike used) and the shape is found where the writer said it
  would be. (test: `TestVectorPrimitives_AnIndependentEngineFindsEachShape`.)
  **This is the card's load-bearing control**: a writer checked only against its
  own reader proves that two of my functions agree, which is the failure mode
  this project's test style names explicitly — prefer an independent second
  implementation over re-deriving a value with the function under test.
- **AC-3** (the curve is priced, not assumed): *Given* the round-shape primitive,
  *then* the artefact records its cost in lines and operators and states whether
  the approximation is accurate enough at the printed dot's real size, **with the
  measurement that establishes it**. A verdict of "awkward and more expensive
  than expected" is a **valid outcome and a finding**, not a failure — it is what
  the card was ordered first to discover. (**gate**: the figures recorded.)
- **AC-4** (type sizes are physical, never pixels): *Given* any text the
  vocabulary emits, *then* its size is set as points against the page, so a page
  written at a different DPI carries the same point size. (test:
  `TestVectorPrimitives_PointSizeIsIndependentOfDpi` — the vector sibling of
  `TestDividerPage_PointSizeIsIndependentOfDpi`, which already holds this for the
  raster path and must keep passing.)
- **AC-5** (the baseline stays shut): *Given* this card's branch, *then*
  `pyproject.toml`'s runtime dependencies are unchanged and no PDF or font
  library is imported anywhere. (test: the existing
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`, which
  is ADR-0042/R4's live check — do not rewrite it, just keep it green.)

## Engineering constraints

- **EC(ADR-0042/R5):** every interior file embeds the project's own face whole
  and exactly once — not once per page, not once per text object. The font
  objects are written once per document however many pages show text.
  test: `PropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts`
  (genuinely multi-case: a corpus of books across page counts, asserting one
  embedded face per file and a per-page cost of zero font bytes).
- **EC(ADR-0042/R4):** no new runtime dependency, at any page count or page kind.
  test: covered by AC-5's existing baseline test; do not duplicate it.

## Guardrails

- **G-1: this card draws no page.** No puzzle grid, no guide, no TOC, no answer
  tile, no divider. Those are CARD-295/296/297, and a vocabulary card that also
  draws a page is the scope gate's textbook case.
- **G-2: do not touch the cover.** It is raster by ADR-0042/R2 — it is a
  photograph. `tests/test_book_cover.py` and `same_page(cover_page,
  expected_cover)` at `tests/property/test_book_export_interior.py:652` stay
  exactly as they are. See `meta/profiling/adr-0042-migration-census.md`'s "What
  is not in the set" before converting any pixel assertion.
- **G-3: do not touch the section dividers.** Raster for now by owner decision
  2026-10-25 — they are getting a nicer design in CARD-231, which is born vector.
- **G-4: do not edit `src/nonogram/export/**`.** The face is *read* from there
  through the existing resource mechanism; nothing in `export/` changes. CON-019
  holds COMP-007's CLI and web exports byte-for-byte identical, and ADR-0042 does
  not reach them.
- **G-5: no geometry.** This vocabulary emits what it is handed. It computes no
  coordinate, no width and no tone of its own (ADR-0042/R3, restating
  ADR-0036/R2). The `Layout` consumer is CARD-295's.
- **G-6: do not lower a corpus minimum or regenerate `tests/fixtures/**`.**
- **G-7: probes stay OUT of `tests/`.** `meta/profiling/rank_durations.py:45`
  defines the frozen render set by grepping eight idioms over `tests/**/*.py`,
  and `tests/test_suite_profile.py:482` asserts the live grep **equal** to a
  33-entry snapshot — a throwaway probe under `tests/` naming `interior(` reds
  the suite. Use `scripts/` or the scratchpad, as CARD-293 did.
- **G-8: ADR-0042/R5's lens must not survive this card.** Item 4's flip is part
  of the card. Merging with R5 still `review-lens` ships a rule whose delivery
  card is closed and whose check is a placeholder.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R3 — the vector writer consumes positions and derives none (check: review-lens)
- ADR-0042/R4 — hand-rolled, no new dependency; ADR-0006/R1 stays closed (check: tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed)
- ADR-0042/R5 — DejaVuSans embedded whole and Flated once per file; no base-14 (check: review-lens → this card's AC-1)
- ADR-0042/R7 — this ADR does not set the grid's weights itself; it removed the device floor, and ADR-0037/R2 is where the weights live (as of 2026-10-25, the owner's 0.3 / 0.8 / 1.3 pt, bound to the vector medium). This card sets no weight either — CARD-227 lands them in wave 62 (check: review-lens)
- ADR-0006/R1 — the runtime dependency set is exactly stdlib + Pillow + NumPy; a font shipping as package data is not a dependency change (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0036/R2 — book page geometry is COMP-007's `compute_layout` with a PageSpec (check: review-lens)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE, never a silent pass (check: review-lens)
- CON-020 — no interior text for the reader below 10 pt at the page's own resolution, clue digits excepted (check: TestInteriorType_EveryFaceHoldsTheFloor)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)

## Architecture context

- **FR/NFR:** none — the interior's medium is an ADR decision, not a requirement. CON-020 and CON-019 apply as standing constraints.
- **ADR:** **ADR-0042** (R3, R4, R5, R7 — this card is its first implementation), ADR-0006/R1, ADR-0036/R2, ADR-0039/R1-R2
- **Components:** COMP-009 (the book generator). COMP-007's layout is *consumed*, not changed.
- **Trace:** not applicable — no requirement's verifying test changes in this card. CARD-299 is where the registry's verifying tests move.

## Worktree notes

- **Start from the probe, don't restart from scratch.**
  `scripts/card293_vector_probe.py` is 1,099 lines of *proven* code — the font
  embedding read back by poppler with 540 clue digits rendered, the stream
  writer, and the 41-line stream assertion that replaced 168 lines of pixel
  archaeology and still discriminates under mutation. It merged (`ef49d656`)
  precisely so this card would build from it. What it does **not** contain is the
  curve primitive.
- **The load-bearing finding from the spike, worth re-reading before you start:**
  `book_pdf_generator._write_pdf` has not called `Image.save(save_all=)` since
  CARD-145 — it drives `PIL.PdfParser` directly (`:379`, `:7047`, `:7105`),
  writing the object table, catalog, pages, content streams, xref and trailer by
  hand. **The PDF plumbing already ships inside the file that changes.** A vector
  page replaces one of the three objects a page writes; the font objects are
  three more, once per file. This is why ADR-0042/R4 could keep the dependency
  baseline shut without strain.
- **Scheduling.** CARD-273 moves nine modules (including
  `book_pdf_generator.py`) to `src/nonogram/book/`. It has not run. This phase
  deliberately does **not** wait for it — CARD-273's blast radius is large and
  the interior is the owner's current subject — but **name and place new modules
  so that move stays mechanical**: a new file beside `book_pdf_generator.py`
  moves with it in the same `git mv`. Re-point `Touches:` on both cards if
  CARD-273 lands first.
- **`src/nonogram/admin/book_pdf_generator.py` is a `conflict.hotspot`.** Every
  card in this phase touches it, so `run` will serialize them regardless of wave.
  The waves below express the dependency, not an expectation of parallelism.
