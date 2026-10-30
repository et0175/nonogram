# CARD-215: Given cells print — a black cell for a revealed filled cell, a dot for a revealed white one

**Status:** blocked
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** true
**Skill:** python-pro
**TDD:** —
**Branch:** card/215-render-given-cells
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 ("## Puzzle generator — … I propose to include black\\white cells in the puzzle grid to make it uniquely solvable. Not sure how to practically add "white" cells to .pdf document (as a dot perhabs)"); owner decision 2026-10-13 via AskUserQuestion — "Cut them now as POC cards"
**Idea:** —
**Wave:** —
**Depends on:** CARD-214
**Touches:** src/nonogram/export/__init__.py, src/nonogram/export/png.py, src/nonogram/export/svg.py, src/nonogram/export/pdf.py, src/nonogram/export/json_export.py, src/nonogram/export/csv_export.py, src/nonogram/export/layout.py, tests/test_export_image.py, tests/test_export_pdf.py, tests/test_export_json.py, tests/test_export_csv.py, tests/test_given_cells_render.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** owner decision 2026-10-30 — **the generator is not being publicly delivered yet, so revealed cells are not needed.** *"I'd postpone revealed cells, we'll not public deliver generator yet."* The generation half already shipped (**CARD-214**, done), so nothing is half-built by waiting: what is postponed is only the *presentation* of given cells — printing them (CARD-215) and locking them in the player (CARD-216). **Unblock when the generator is delivered publicly**, which is the condition the decision names (`/forge:kanban unblock CARD-215` / `CARD-216`).

## What to implement

**Current behaviour (verified by reading the code).**

- Every renderer takes one boundary record, `export.ExportPayload`
  (`export/__init__.py:124`): grid, clues, seed, mode, extent, density,
  strategies. A blank puzzle page draws **no** cell state at all — `png._draw_grid`
  (`png.py:164`) strokes rules, `_draw_clues` (`:218`) writes digits, and the
  solution is only ever drawn on a solved/answer page.
- `json_export` round-trips the payload (`document` / `parse` / `decode`, with
  per-field validation and clue-count cross-checks); `csv_export` writes its own
  flat form. Neither has a concept of a pre-revealed cell.
- CON-019 and `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` pin the
  exports: for a payload without givens nothing here may move by a pixel.

**What changes.** Givens become a payload field and a drawn mark:

1. **Boundary type.** `ExportPayload` gains `givens` — the same
   `list[list[bool | None]]` shape CARD-214 defined (`True` = revealed filled,
   `False` = revealed white, `None` = not revealed), defaulting to no givens so
   every existing construction site keeps working. The field is validated like
   the grid is: shape must match the grid's extent, and a given's value must
   equal the grid's own cell (a given that contradicts the solution is a
   malformed payload, not a puzzle).
2. **Marks (one definition, three renderers).** Geometry comes from
   `export/layout.py` (ADR-0036/R2) — the given-dot's radius and the cell box
   are layout's to compute, not a renderer's:
   - revealed **filled** → the cell is filled in pure `INK`, exactly as a
     solved page fills a cell (reuse that definition; do not invent a second
     fill);
   - revealed **white** → a small centred dot in `INK`, sized as a fraction of
     the cell that holds at the smallest cell the system can print
     (`MIN_CELL_MM` / the book floor) and never touches the cell's rules.
   PNG, SVG and PDF all draw from the same layout numbers, so the three agree
   by construction — the same "two sinks on one raster" relationship CON-006
   already describes for PNG/PDF.
3. **Metadata.** `json_export.document` writes `givens` (and `parse`/`decode`
   read it back, with the same validation as step 1, so a round trip is
   lossless); `csv_export` records them in its own flat form. A payload with no
   givens writes **no new field** — the files stay byte-identical (AC-6).
4. **The book interior.** A book puzzle page is drawn by COMP-009 from the same
   payload, so a member puzzle carrying givens prints them too. Nothing about
   the book's own geometry changes.

## Acceptance criteria

- **AC-1** (happy, PNG): *Given* a payload with one revealed filled cell and
  one revealed white cell, *when* a PNG is rendered, *then* the filled cell's
  box is solid `INK` and the white cell holds a centred dot, and no other cell
  is marked. (test: `TestGivenCellsRender_PngDrawsBothMarks`)
- **AC-2** (happy, SVG): *Given* the same payload, *when* the SVG is rendered,
  *then* it carries exactly one filled rect and one circle at those two cells'
  layout coordinates. (test: `TestGivenCellsRender_SvgDrawsBothMarks`)
- **AC-3** (happy, PDF): *Given* the same payload, *when* the PDF is rendered,
  *then* its puzzle page's pixels equal the PNG's for the same layout (CON-006's
  one-raster relationship holds for givens too). (test:
  `TestGivenCellsRender_PdfMatchesThePng`)
- **AC-4** (happy, round trip): *Given* the same payload, *when* it is written
  as JSON and parsed back, *then* the parsed payload's givens are identical.
  (test: `TestExportJson_GivensRoundTrip`)
- **AC-5** (edge, malformed): *Given* a payload whose given contradicts the
  grid, or whose givens grid is the wrong shape, *when* it is parsed or
  rendered, *then* a `NonogramError` subclass is raised naming the offending
  cell — never a silently-ignored field. (test:
  `TestExportJson_RefusesContradictoryGivens`)
- **AC-6** (guard, byte-identical): *Given* any payload **without** givens,
  *when* PNG, SVG, PDF, JSON and CSV are written, *then* every byte is
  identical to before this card. (test:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`,
  `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`)
- **AC-7** (edge, smallest cell): *Given* the smallest cell the system prints
  (the book floor and `MIN_CELL_MM`), *when* a white given is drawn, *then* the
  dot is at least 1 device pixel across and does not touch the cell's rules.
  (test: `TestGivenCellsRender_DotHoldsAtTheSmallestCell`)
- **AC-8** (happy, book page): *Given* a book member puzzle carrying givens,
  *when* the interior is exported, *then* its puzzle page shows them and its
  answer page is unchanged (the answer already shows every filled cell). (test:
  `TestBookPdf_MemberWithGivensPrintsThem`)

## Guardrails

- G-1: Exports of a payload without givens stay byte-identical (CON-019,
  ADR-0036/R1).
- G-2: No geometry in a renderer — the dot's size and position come from
  `export/layout.py` (ADR-0036/R2).
- G-3: Export metadata records extent as separate width/height; no scalar
  "size" field joins the schema (ADR-0023/R1).
- G-4: A renderer must not re-check the export gate or re-derive clues — it
  draws what the payload says (the payload's existing contract, guardrail G-3
  of `export/__init__.py`).
- G-5: Out of scope — choosing the givens (CARD-214 owns it), persisting them
  (CARD-216), the player.
- G-6: No new runtime dependency (ADR-0006/R1).

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-215 --root meta/architecture` (55 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dim… (check: review-lens)
- ADR-0023/R2 — A decoder accepts only its own SCHEMA_VERSION, by exact comparison, and raises an error naming both the file's version and its own. It never attempts a best-effort … (check: test: TestExport_RejectsSupersededSchemaVersion)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_47 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-011/FR-016 (the printable puzzle), FR-013 (export formats),
  FR-030 (export metadata).
- **ADR:** ADR-0012 (boundary values), ADR-0023/R1, ADR-0036/R1, ADR-0036/R2,
  ADR-0006/R1.
- **CON:** CON-006, CON-019.
- **Components:** COMP-007 (`export/**`, `layout.py`), COMP-009 (the book
  interior consumes the same payload).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

- **[Postponed 2026-10-30, owner decision]** Not a defect and not a re-scope — a sequencing call: revealed cells have no audience until the generator ships publicly. **Two things this card carries are worth not losing while it waits.** (1) Its own text flags a false clause: *"the dot is at least **1 device pixel** across"*, which it already answers with *"should be: the same design without that clause"* — a device-pixel floor is meaningless for a vector interior (ADR-0042/R7), and that correction is owed whenever this card resumes. (2) Its `## System contract` quotes a **superseded** ADR-0037/R2 — *"at least 0.25 mm … twice the thin rule, in pure black"* — which the 2026-10-17 amendment replaced with three weights, grey rather than black, and a 2-device-pixel floor. That row is false as quoted and must be re-derived at the next decompose, not carried forward.

—

## Architecture revision (2026-10-25)

**Reason:** ADR-0042 (DEC-048) accepted 2026-10-25 — the book interior is written
as PDF content-stream operators; the cover stays raster because it is a
photograph, and the section dividers stay raster for now by owner decision the
same day. The phase that converts the interior is CARD-294..CARD-299 (waves
60-64), and this card is scheduled after it.

**Was:** given cells print as a black cell for a revealed filled cell and a dot
for a revealed empty one, with the card's own AC requiring **"the dot is at least
1 device pixel across"**.

**Should be:** the same design without that clause. "At least 1 device pixel" is a
**device-floor constraint with no meaning in a vector interior** — there is no
device pixel in a content stream, and the dot's size is whatever the layout states
in millimetres.

**Delta:**
- Drop the device-pixel clause from the AC and restate the dot's size as a
  physical measure.
- The dot is a **round shape**, so it needs the curve primitive CARD-294 prices
  (its AC-3) and CARD-296/297 first use. Read that recorded figure before
  estimating this card.
- Its tests move from ink measurement to content-stream assertions.
