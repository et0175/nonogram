# CARD-197: A new full-page solved layout: clues top and left, light-gray gridlines between filled cells

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1.25d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/197-solved-page-renderer
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-CARD-197
**Source:** owner's Google Doc "Nonograms - Print layout1", 2026-10-07 (owner decisions on the book's answer-key replacement)
**Idea:** —
**Wave:** 37
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_solved_page.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-10-07T11:51:38Z
**Closed:** 2026-10-07T14:55:00Z
**Actual:** 0.1d
**Merge commit:** 81156b1
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- A regular (unsolved) puzzle page is drawn by `BookPDFGenerator.puzzle_pages`/`_two_up_page`
  (`src/nonogram/admin/book_pdf_generator.py:1995-2036`) using three private helpers that
  reimplement `export/`'s drawing (CLAUDE.md's reimplement-rather-than-import-across rule,
  the same precedent as `solver/propagate.py`'s `mask_runs`): `_stroke_drawing` (line 719,
  strokes every `Layout.vertical_lines`/`horizontal_lines`, thin first then the every-5th/
  border lines, then the placed page's `PuzzleFrame` — all pure black, `INK`), `_write_clues`
  (line 788, writes every `Layout.clue_entries` centred on its placed point, Pillow's default
  face) and `_set_band` (line 809, writes a title line into `header_band()`'s strip, shrinking
  once if too wide, the packaged DejaVu face via `_band_font`). Every coordinate comes from
  `nonogram.export.layout.compute_layout`/`header_band`, read-only (ADR-0036/R2) — nothing here
  fits a cell or places a line itself.
- The book's **solved** output today is only the packed 6-up/4-up answer key (FR-042, INV-011):
  `BookPDFGenerator._answer_page` (line 1961) calls `export.png.render_answer_page`, which calls
  `png._draw_answer` (line 297): it fills each solved cell black (`draw.rectangle`, `INK`) and
  **then re-strokes `_draw_grid` over the fills** — but `_draw_grid` draws every grid line in the
  *same* `INK` black the fill uses, so a run of adjacent filled cells reads as one solid black
  blob with no visible division (confirmed by CARD-167's own observation in its Worktree notes:
  "adjacent filled squares merge into one black block (no rule between them), same as solid
  fills"). The CLI/web single-puzzle answer page (`export/pdf.py`'s `_reveal`, line 251) does the
  same thing with no grid redraw at all — it paints each filled cell's full rectangle (from one
  grid-line position to the next, `xs[column]`..`xs[column+1]`) in the same black, directly over
  whatever line was already there. **Grepped the whole export/admin print path for an existing
  gray or "between filled cells" knob: there is none.** `_draw_grid`/`_stroke_drawing` take no
  colour parameter; no `AnswerTile`/`Layout` field distinguishes a filled-adjacent boundary from
  any other. This is genuinely new code, not a flag to flip. (The only "gray" in the codebase is
  the UI's `--grid-ink` CSS token (`static/tokens.css:50`, a dark navy `#1c2333`, screen-only) and
  `color-mix` tints derived from it for the on-screen player — neither is a grayscale-print value
  and neither is reachable from `admin/book_pdf_generator.py` without pulling CSS into a PDF.)
- The book's packed answer key never shows clues (FR-042: "no row or column clues") and captions
  each tile "Puzzle N — Title" (`book_answer_key.answer_caption`, line 219, `CAPTION_SEPARATOR =
  " — "`; `answer_title`, line 200, resolves the per-book custom title else the puzzle's stored
  name). A puzzle page's own band is `band_identity(puzzle_number, stored_tier)` (line 559),
  `"Puzzle 12 · Easy"` (`BAND_SEPARATOR = " · "`) — a different separator for a different join,
  by design (`book_answer_key.py:102-111`'s own comment).
- `BookPDFGenerator.page_spec(page_number)` (line 1479) is the one door onto the book's sheet
  (`book_page_spec.book_page_spec`): at Book 1 (`book_page_spec.py:207-218`) it reserves the
  12 mm title band at the top and a flat 7.5 mm cell cap (not the A4 comfort curve), 0.375 in
  (9.525 mm) top/bottom/outside margins and 0.5 in gutter. A puzzle's cell is
  `min(7.5 mm cap, page fit)`: for a small or mid grid the flat cap binds and the drawing does
  not reach the usable area's bottom edge, leaving slack between `Layout.page.drawing_bottom`
  and `Layout.page.usable_bottom`; for a large, page-fit-bound grid (e.g. 30x30) that slack can
  shrink to zero. No existing book page reserves a caption line below a *puzzle*-geometry
  drawing — only the answer key's tiles do (`layout.ANSWER_CAPTION_MM = 6.0`,
  `layout.ANSWER_TEXT_FONT_MM = 10 * 25.4 / 72`, exactly 10 pt), inside their own, different,
  band-less `AnswerTile` geometry.

**Target: one new method, `BookPDFGenerator.solved_puzzle_page(payload, puzzle_number,
page_number, title=None)` → `Image.Image`**, added beside `_answer_page`/`_two_up_page` (same
file, same layer, same pattern: the caller resolves the title via `answer_title`/
`custom_titles()` before calling, exactly as `_answer_page` already does). It is a rendering
primitive only — nothing calls it from `interior`/`interior_stream`/`answer_key` yet; wiring it
into the book's real answer-key packing (replacing the 6-up/4-up pages) is CARD-198.

1. `layout = compute_layout(payload.row_clues, payload.column_clues, self.page_spec(page_number))`
   — the **same** call, same `PageSpec`, an unsolved puzzle page at that position would use.
   Nothing is re-derived (ADR-0036/R2): same cell, same gutters, same frame, same band.
2. A fresh `RGB` image at `layout.width x layout.height`, `BACKGROUND` white.
3. Fill every solved cell black, using `layout.vertical_lines`/`horizontal_lines` positions as
   the cell boundaries — the same `xs`/`ys` approach `pdf._reveal` uses (line 274-289) — so a
   filled cell lands exactly between its two already-placed grid lines.
4. `_stroke_drawing(draw, layout)` — **reused verbatim, unedited**. Draws every grid line and the
   frame in pure black, over the fills, exactly as a regular book page does. This is what keeps
   ADR-0037/R2 ("every thin/heavy rule under the book PageSpec is pure black") true to the
   letter: nothing here recolours *the* thin or heavy rule.
5. **New code, this card's actual addition:** for every pair of grid-adjacent cells that are
   *both* filled, re-stroke the one line segment between them in light gray, at that line's own
   already-computed width (`GridLine.width` — the thin or the heavy weight, whichever that
   boundary already is, so the every-5th counting rhythm survives in gray across a filled run
   too). Concretely: for each interior vertical boundary `c` (`1 <= c <= columns - 1`) and each
   row `r`, if `grid[r][c-1]` and `grid[r][c]` are both filled, draw a gray segment at
   `x = xs[c]` from `y = ys[r]` to `y = ys[r+1]`, width `layout.vertical_lines[c].width`;
   symmetrically for horizontal boundaries. An outer border (`c == 0` or `c == columns`) is never
   "between two filled cells" (one side is outside the grid) and is never touched. This is an
   *additional* mark layered on top of step 4's already-black line, not a recolouring of it —
   see Guardrails G-2 and Worktree notes for why that reading is what keeps ADR-0037/R2 intact.
   **Light-gray token, decided here because none exists:** RGB `(160, 160, 160)` — grepped the
   whole export/admin print path and the CSS tokens for an existing gray convention; there is
   none to reuse (see above). `(160, 160, 160)` is roughly equidistant from black (0) and white
   (255) in printed density, stays an exact grayscale value under the book's own `(v, v, v) ->
   v` RGB-to-`"L"` conversion (`book_pdf_generator.py` ~line 2763, CARD-147's B&W interior mode —
   so the mark is DeviceGray-compatible by construction, never a colour), and is clearly
   distinguishable from both ends by a pixel test (`|v - 0| = 160`, `|v - 255| = 95`). Name it
   a module constant, e.g. `_SOLVED_GRID_GRAY`, so CARD-198 and the owner's render can see it in
   one place. **The owner confirms this specific tone on the render before CARD-198 ships it.**
6. `_write_clues(draw, layout)` — reused verbatim. Clue digits are exempt from CON-020's 10 pt
   floor (2026-10-06 amendment), exactly as on a regular puzzle page.
7. Title band: `_set_band(draw, header_band(layout), band_identity(puzzle_number,
   payload.difficulty), room)` — **reused verbatim**, the same call `_two_up_page` makes for each
   slot's band. This reads "Puzzle N · Tier" (or "Puzzle N" with no tier), the book's own existing
   band-identity wording — not the doc image's literal "No. 8", and not a new string.
8. Caption: a new small draw, below the drawing. Text is `answer_caption(puzzle_number, title)`
   from `book_answer_key.py` (already imported in this module) — **"Puzzle N — Title"**, reused
   verbatim from today's packed answer key rather than inventing a third wording. (This repeats
   "Puzzle N" that the band above already shows; that duplication is the deliberate cost of reuse
   over invention — flagged for the owner in Design context below, alongside the gray tone.) Font
   is the packaged DejaVu face at `layout.ANSWER_TEXT_FONT_MM` in device pixels (exactly 10 pt —
   the literal CON-020 floor, reused from `export.layout`, never shrunk further) via this module's
   own `_band_font`. Centred (`anchor="mm"`) in the slack between `layout.page.drawing_bottom` and
   `layout.page.usable_bottom`, horizontally centred between `layout.page.drawing_left` and
   `drawing_right` — i.e. inside the usable area the layout already measured, never inside the
   trim margin. **If that slack is smaller than the caption's own line height, omit the caption**
   rather than overlap the drawing or spill into the margin — this is a real limit of a
   page-fit-bound puzzle (e.g. a 30x30 at Book 1, which can leave near-zero slack); it is not
   solved by this card (CON-019-style discipline: reuse the layout, never re-derive its sizes).

**ADR-0037/R1 cross-check (brief's own question, confirmed by reading FR-033/AC-193/AC-194).**
FR-033's rule, as ADR-0037/R1 restates it, is "a puzzle's picture title appears only on its
answer-key page, never on its puzzle page" — not "never on any page." `TestBookPdf_AnswerKeyCarriesPictureTitle`
(AC-194) already asserts the opposite of a blanket ban: the title *does* print on the
answer-key page today. This card's output is a solution page — the book's other kind of page —
so printing the title and caption here is the existing, confirmed exception, not a new one.

**ADR-0038 is unrelated** (the puzzle player, admin-only interactive solving — nothing here
touches `static/`, `templates/puzzle_solve.html` or `solver.js`).

## Acceptance criteria

- **AC-1** (happy): *Given* a puzzle's solved grid and clues, *when*
  `solved_puzzle_page(payload, n, page_number)` renders it, *then* every row and column clue on
  the page equals `nonogram.clues.encode_line` of the grid's rows/columns, placed top and left at
  exactly the coordinates `compute_layout` would place them on an *unsolved* puzzle page of the
  same clues and the same `page_number`.
  *test: TestBookSolvedPage_CluesMatchTheGridAndTheUnsolvedPlacement (in tests/test_book_solved_page.py)*
- **AC-2** (happy): *Given* a solved grid with a run of 2+ adjacent filled cells (row or
  column), *when* the page is rendered, *then* every filled cell's interior pixel is pure black
  (0,0,0) and every pixel on the one grid-line segment directly between two filled cells of that
  run equals the chosen light-gray tone, distinguishable by exact value from both pure black and
  pure white.
  *test: TestBookSolvedPage_GrayGridlinesBetweenFilledCells*
- **AC-3** (boundary): *Given* the same page, *when* a line between a filled and an empty cell,
  an outer border line, or a line between two empty cells is read, *then* it is pure black — the
  new gray tone appears nowhere except a boundary strictly between two filled cells.
  *test: TestBookSolvedPage_GrayOnlyBetweenFilledCells*
- **AC-4** (happy): *Given* a puzzle number and its solver tier, *when* the page is rendered,
  *then* its title band reads exactly `band_identity(number, tier)` would ("Puzzle N · Tier", or
  "Puzzle N" with no tier) — the same text an unsolved page's band would show for that puzzle.
  *test: TestBookSolvedPage_TitleBandMatchesBandIdentity*
- **AC-5** (happy): *Given* a puzzle whose cell is cap-bound (comfort/flat cap wins over page
  fit, leaving slack below the drawing) and a resolved title, *when* the page is rendered,
  *then* a caption reading `answer_caption(number, title)` ("Puzzle N — Title") is drawn centred
  below the drawing, entirely inside the usable area (never inside the trim margin, never
  overlapping the grid).
  *test: TestBookSolvedPage_CaptionReadsThePictureName*
- **AC-6** (boundary): *Given* a puzzle whose cell is page-fit-bound (e.g. a 30x30 at Book 1
  trim) so no slack remains below the drawing, *when* the page is rendered, *then* no caption
  pixel is drawn outside the usable area or over the grid — the caption is omitted rather than
  corrupting the page.
  *test: TestBookSolvedPage_CaptionOmittedWhenNoSlack*
- **AC-7** (negative): *Given* the rendered page, *when* every piece of type on it is measured
  (the title band, the caption), *then* each holds CON-020's 10 pt floor at the page's own DPI;
  the clue digits are exempt (CON-020's 2026-10-06 amendment) and are not checked against it.
  *test: TestBookSolvedPage_TextHoldsTheTenPointFloor*
- **AC-8** (negative): *Given* the rendered page, *when* every pixel is read, *then* every
  pixel's R, G and B channels are equal (DeviceGray-compatible, no colour — CARD-147's B&W
  interior convention) for both the black ink and the new gray tone.
  *test: TestBookSolvedPage_NoColour*
- **AC-9** (happy): *Given* the same clues and `page_number`, *when* an unsolved puzzle page
  (`render_pages`/`puzzle_pages`' single-page path) and this card's solved page are both
  rendered, *then* their cell size, gutter depth, every grid-line position and the frame are
  identical — only the fill and the new gray marks differ.
  *test: TestBookSolvedPage_SameGeometryAsTheUnsolvedPage*

## Guardrails

- G-1: CON-019's golden A4 path is untouched — `tests/test_export_a4_golden.py` passes unedited.
  No file under `src/nonogram/export/**` is touched; every call this card makes into `export/` is
  read-only (`compute_layout`, `header_band`), the same calls `_two_up_page` already makes.
- G-2: ADR-0037/R2 ("every thin/heavy rule under the book PageSpec is pure black") stays literally
  true: `_stroke_drawing` is called, never edited, so the grid's own thin and heavy rules are
  still drawn pure black everywhere, including over a filled run. The new gray mark is an
  *additional* stroke on top, confined to this new method — `tests/test_book_pdf_band.py`,
  `tests/test_book_puzzle_frame.py` and `tests/test_book_pdf_two_up.py` pass unedited (no existing
  page gains gray ink).
- G-3: FR-042/INV-011's packed answer key (`pack_answer_pages`, `render_answer_page`, the 6-up/
  4-up pages) is unchanged — this card adds a new, uncalled method; `tests/test_book_answer_key.py`
  passes unedited. Wiring it into the real packing is CARD-198, not this card.
- G-4: The interior's page count and parity (`_as_planned`, `interior_stream`, `InteriorStream`)
  are unchanged — nothing in `interior_pages`/`interior`/`interior_stream`/`export_interior` calls
  `solved_puzzle_page` yet. `tests/test_book_pdf_memory.py` and the gutter/Finalise tests pass
  unedited.
- G-5: Black-and-white only (CARD-147). The new gray tone is a literal `(v, v, v)` RGB tuple, not
  a named colour or a third channel-unequal value; `tests/test_book_pdf_ink_mode.py` passes
  unedited (this card adds no call on that path).

## Failure matrix

- No failure-bearing boundaries: `solved_puzzle_page` is a pure rendering primitive, called with
  already-validated inputs (`ExportPayload`, a 1-based `puzzle_number`/`page_number`, an optional
  resolved `title`) — no I/O, no concurrency, no retries, no network, no database, nothing awaited.
  It does one thing `_two_up_page`/`_answer_page` already do in the same file: call
  `export.layout.compute_layout`/`header_band` (both total functions of their arguments), draw on an
  in-memory `Image`, and return it. The two apparent "failure" spots are not boundaries the card
  owns:
  - `layout.page is None` after `compute_layout(..., self.page_spec(page_number))`: `page_spec`
    always returns a `PageSpec` with a parity (it is built from `book_page_spec`, which always sets
    one — see ADR-0036's "Mirrored margins"), so this is an unreachable total-function guard, not a
    real failure mode — the same one `_two_up_page` keeps for the same reason (and the same
    `# pragma: no cover` treatment).
  - The caption's slack/omission check (AC-6) is not a failure: it is the one DECLARED behaviour
    branch this card owns, and it is bounded and deterministic — `slack >= line_height` draws the
    caption, otherwise it is omitted. Nothing raises, nothing degrades; a page-fit-bound puzzle
    simply prints with one fewer piece of text. Declared behaviour, not a failure: omit the caption
    when the slack is smaller than its own line height (ascent + descent at the literal 10 pt /
    `ANSWER_TEXT_FONT_MM` floor), bounded below by zero (a puzzle whose cell is fully page-fit-bound,
    e.g. AC-6's 23x10 checkerboard at Book 1, where slack is exactly 0).

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-197` (53 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scala… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniq… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit… (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when th… (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws n… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN… (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on dens… (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction… (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzz… (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pur… (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with th… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attributi… (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the gr… (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle neve… (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membersh… (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percent… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel… (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm toolcha… (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correc… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a n… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decode… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a paramet… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, whos… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No ot… (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) nev… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR… (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement,… (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm… (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is a… (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns i… (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the bo… (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** none yet, by design — like CARD-144's `PuzzleFrame`, the full-page solved layout is
  owner intake (the Google Doc, 2026-10-07) not yet formalised into its own FR; FR-042/INV-011
  (today's packed 6-up/4-up answer key) is the current, unaffected requirement, since nothing
  this card adds is wired in (G-3). FR-033/AC-193/AC-194 (title only on the answer-key page, never
  the puzzle page) is cited above and confirmed, not contradicted, by this card's caption.
- **ADR:** ADR-0036/R1 (default A4 path byte-identical — untouched, G-1), ADR-0036/R2 (book
  geometry only through COMP-007's layout functions — this card fits nothing new, every mark is
  at an already-computed coordinate), ADR-0037/R1 (title only on an answer/solution page —
  confirmed above), ADR-0037/R2 (book rules pure black — preserved to the letter, see G-2 and
  "What to implement" step 4/5).
- **CON:** CON-019 (CLI/web geometry unchanged, G-1), CON-020 (10 pt floor, with the 2026-10-06
  clue-digit exemption — AC-7), CON-011 (10..30 cell sides — the primitive is not size-limited,
  though the owner-visible render demos only two sizes).
- **Components:** COMP-007 (layout functions consumed, read-only), COMP-009 (new method lives
  here, `src/nonogram/admin/book_pdf_generator.py`).
- **Trace:** meta/architecture/trace.yml — not updated by this card (no FR exists yet to trace
  against); revisit when CARD-198 or the architect station formalises the new layout.

## Design context

- **Output:** a new book-interior page kind, not yet reachable from any export route (standalone
  primitive; CARD-198 wires it into the book's real answer-key packing).
- **Owner-visible defaults this card picks (need confirmation before CARD-198):**
  - The light-gray gridline tone: RGB `(160, 160, 160)` — no existing project convention to
    reuse, reasoning above.
  - The caption repeats "Puzzle N" (via `answer_caption`'s existing wording), which the title band
    above already shows — a deliberate reuse-over-invention choice, not a new format.
  - A page-fit-bound puzzle (very large grids on a small trim) may print with no caption at all,
    rather than an overlapping or clipped one (AC-6).
- **Renders:** ~/Documents/nonogram-reviews/CARD-197/ (owner visual check before merge, and before
  CARD-198 wires this in) — a 10x10 and a 20x20 puzzle, both at Book 1 trim, each rendered through
  `solved_puzzle_page`. The owner confirms the gray tone and the title/caption wording. (Both
  demoed sizes are cap-bound at Book 1, so both show a caption; a page-fit-bound size such as
  30x30 is not part of this render set — AC-6 covers that case by test instead.)

## Worktree notes

- [Origin] Owner's Google Doc "Nonograms - Print layout1", 2026-10-07: a new full-page solved
  answer layout (clues top+left, light-gray internal gridlines, title+caption), replacing the
  compact 6-up answer key. Owner has accepted the page-count consequence (~6x more answer pages)
  for CARD-198, which is out of this card's scope.
- [Verified facts the implementer must not re-derive]
  - `_stroke_drawing`/`_write_clues`/`_set_band` are at `book_pdf_generator.py:719/788/809`;
    `_two_up_page` (line 1995) is the precedent for composing a page by hand from these three
    plus `compute_layout`/`header_band`, rather than through `render_pages`.
  - `png._draw_answer` (export/png.py:297) and `pdf._reveal` (export/pdf.py:251) are the two
    existing "fill then stroke" paths; both currently merge adjacent filled cells into one solid
    black run — confirmed by CARD-167's own Worktree-notes observation, re-confirmed here by
    reading `_draw_grid`'s fill colour (`INK`, the same as the cell fill). No existing colour
    knob anywhere in `export/` or `admin/book_pdf_generator.py` — grepped for gray/grey across
    both and only found `layout.py:287`'s *comment* ("a grey square") and the UI-only
    `--grid-ink` CSS token (`static/tokens.css:50`), which is a dark navy screen colour, not a
    grayscale print value, and not reachable from this module without pulling CSS into a PDF.
  - `book_page_spec.BOOK1_PROFILE` (book_page_spec.py:207-218): 7.5 mm flat cell cap (not the A4
    comfort curve), 9.525 mm top/bottom/outside margins, 0.5 in gutter, 12 mm band. A 10x10 and
    a 20x20 are cap-bound at this trim (plenty of slack below the drawing for a caption); a
    30x30 is very likely page-fit-bound (little to no slack) — this is *why* the brief's own
    render list picks 10x10/20x20 and why AC-6 exists as a separate, test-only case.
  - `layout.ANSWER_TEXT_FONT_MM = 10 * 25.4 / 72` is *exactly* 10 pt (`layout.py:2011`) — reusing
    it for the caption guarantees CON-020's floor by construction, with no shrink-to-fit needed
    (the existing packed answer key's own captions don't shrink for width either, only the
    heading's height is capped — same reasoning applies here).
  - `book_answer_key.answer_caption`/`answer_title` are already imported into
    `book_pdf_generator.py` (lines 316-317) — no new import needed for the caption text.
- [Tension flagged, not resolved here] ADR-0037/R2's statement is scoped to "every thin/heavy
  rule under the book PageSpec" being pure black. This card's reading — the gray mark is a new,
  additional stroke layered on an unedited, still-pure-black `_stroke_drawing` call, not a
  recolouring of "the thin rule" or "the heavy rule" — keeps R2 literally true, and is the
  reading this card is built against (see G-2). If a reviewer or the architect station reads R2
  more broadly (any mark on a book rule's coordinate must be black), that is an ADR-0037
  amendment question for CARD-198's station, not a reason to block this card, which the owner
  has already approved the *visual* outcome of (the Google Doc reference image).
- [AC cross-check] Re-read AC-1..AC-9 against "What to implement": the body's 8 steps map
  1:1 onto AC-1 (step 1/6), AC-2/AC-3 (step 5), AC-4 (step 7), AC-5/AC-6 (step 8), AC-7 (CON-020
  cross-cut), AC-8 (the gray-tone token choice), AC-9 (step 1's "same call" claim, made testable).
  No AC asks for an order or a case the body doesn't also describe.
- [Estimate] 1.25d, **above the brief's 1-day flag.** Split suggestion if it needs to divide: (a)
  the drawing primitive itself — fill, reused stroke/clue calls, the new gray-boundary marks, the
  title band, AC-1..AC-4/AC-9 and their tests (~0.75d); (b) the caption (including the
  slack/omission logic), AC-5..AC-8, the full mutation pass and the two owner-visible renders
  (~0.5d). Kept as one card per the brief's instruction; CARD-198 (the real wiring into the
  book's answer-key packing) already depends on this one regardless of whether it splits.
- [Not in this card] Wiring `solved_puzzle_page` into `answer_key`/`interior`/`interior_stream`,
  replacing the 6-up/4-up pages, the page-count/KDP-gutter recomputation that follows from ~6x
  more answer pages, and any requirements-delta/ADR amendment formalising the new layout — all
  CARD-198 and the architect station.
- [Owner decision] 2026-10-07 — keep both numbers (band + caption); caption reuses answer_caption("Puzzle N — Title") as drafted.
- [Env] forge 2026.8.17
- [Owner default] light-gray gridline tone RGB(160,160,160) — implemented as drafted, pending owner render confirmation.
- [Owner default] caption repeats "Puzzle N" via answer_caption as drafted — implemented as drafted.

- [Implementation summary, 2026-10-07] `BookPDFGenerator.solved_puzzle_page` implemented in
  `src/nonogram/admin/book_pdf_generator.py`, beside `_answer_page`/`_two_up_page`, exactly
  following the card's 8 steps: `compute_layout` (same call an unsolved page would make) ->
  fill solved cells (`_reveal`'s xs/ys approach, reimplemented) -> `_stroke_drawing` (verbatim) ->
  new gray-boundary marks -> `_write_clues` (verbatim) -> `_set_band` (verbatim) -> the caption
  (new, with the slack/line-height omission check). New module constant `_SOLVED_GRID_GRAY =
  (160, 160, 160)` added beside `_BAND_WIDTH_RATIO`/`_MIN_BAND_FONT_RATIO`. `ANSWER_TEXT_FONT_MM`
  added to the existing `nonogram.export.layout` import (additive).

- STRUCTURE: the mm->px conversion for the caption's 10 pt floor is reimplemented locally
  (`round(ANSWER_TEXT_FONT_MM / 25.4 * self.dpi)`) rather than importing `export.layout`'s private
  `_mm_to_px` — CLAUDE.md's reimplement-rather-than-import-across rule (the same precedent as
  `solver/propagate.py`'s `mask_runs`), and it reads `self.dpi` (this page's own resolution)
  rather than the hard-coded module constant `_mm_to_px` closes over, which is the more honest
  dependency even though the two are numerically identical today (`self.dpi == DPI` always).

- STRUCTURE: the caption's "is there room" test is the font's own `ascent + descent`
  (`ImageFont.FreeTypeFont.getmetrics()`), not a second hard-coded mm constant — the card asks only
  for "the caption's own line height", and the font this card already draws the caption in is the
  one honest source for what its own line height is, with nothing new to keep in sync against a
  type-size change later.

- STRUCTURE: both new boundary loops (vertical and horizontal) use direct `grid[r][c-1]`/
  `grid[r][c]` indexing rather than a defensive helper — `c` only ever ranges `1..columns-1` and
  `r` only `0..rows-1` (and symmetrically for the horizontal loop), so every index is in-bounds by
  construction once `range(1, layout.columns)`/`range(1, layout.rows)` is used; the outer border
  (`c == 0`/`c == columns`) is structurally unreachable rather than guarded.

- MUTANT: flipped `and` to `or` in the vertical-boundary condition (`grid[r][c-1] and grid[r][c]`)
  -> `TestBookSolvedPage_GrayOnlyBetweenFilledCells` (both
  `test_a_filled_to_empty_boundary_is_black` and
  `test_every_interior_boundary_matches_its_both_filled_verdict`) failed as expected; reverted.
- MUTANT: flipped `and` to `or` in the horizontal-boundary condition (`grid[r-1][c] and grid[r][c]`)
  -> `TestBookSolvedPage_GrayOnlyBetweenFilledCells::test_every_interior_boundary_matches_its_both_filled_verdict`
  failed as expected; reverted.
- MUTANT: flipped the caption's slack check from `slack >= line_height` to `slack < line_height`
  -> `TestBookSolvedPage_CaptionOmittedWhenNoSlack::test_the_rendered_page_is_identical_whatever_the_title`
  failed as expected (the caption started varying with the title at zero slack); reverted.
- MUTANT: the band text call `band_identity(puzzle_number, payload.difficulty)` changed to
  `band_identity(puzzle_number, None)` -> every
  `TestBookSolvedPage_TitleBandMatchesBandIdentity` test failed as expected (the ungraded-tier
  parametrised case still passed, which is itself consistent — `None` is what it already asserts);
  reverted.
- MUTANT: the caption text call `answer_caption(puzzle_number, title)` changed to
  `answer_caption(puzzle_number, None)` ->
  `TestBookSolvedPage_CaptionReadsThePictureName::test_changing_the_title_changes_only_the_caption_area`
  failed as expected; reverted.

- [SCOPE+] `tests/test_book_pdf_memory.py` — one additive line. That file's own
  `TestBookPdfMemory_TheInstrumentWrapsEveryPageFactory::test_every_page_returning_method_is_in_page_factories`
  is a hand-maintained completeness guard: its own docstring says a new `-> Image.Image` method on
  `BookPDFGenerator` "would have to be added to `PAGE_FACTORIES` by hand anyway, and this test's own
  message is where a reader is told so." `solved_puzzle_page` is honestly annotated `-> Image.Image`
  like every sibling page factory (the card's own target signature), so this guard fails until the
  new name is added to the `PAGE_FACTORIES` tuple — a one-line, purely additive registration with a
  comment explaining why, not a change to any assertion. G-4's own substance (nothing in
  `interior_pages`/`interior`/`interior_stream`/`export_interior` calls `solved_puzzle_page`) is
  unaffected and still holds; every other test in that file, and the file's other guardrail-named
  siblings (G-1/G-2/G-3/G-5), pass with no further edits. Not removing the method's return
  annotation to dodge this: that would create a real blind spot for the memory instrument the day
  CARD-198 wires this method in for real, which is exactly the failure (F-6) the guard exists to
  catch.

- [Render] wrote `~/Documents/nonogram-reviews/CARD-197/solved-10x10.png` and
  `solved-20x20.png` (via a throwaway, uncommitted script run from the scratchpad, not from the
  repo) — a 10x10 and a 20x20 synthetic solved grid (a hollow border plus a filled cross through
  the middle, so both the border and the cross carry runs of 2+ adjacent filled cells), at Book 1
  trim, with plausible titles ("Snowflake"/"Sailboat"), puzzle numbers (8/23) and tiers
  (Easy/Medium). Both renders show the band ("Puzzle N · Tier"), the clues top+left, the caption
  ("Puzzle N — Title") below the drawing, and the light-gray boundary marks between filled cells —
  visually confirmed at full resolution before hand-off. The owner confirms the gray tone and the
  band/caption wording on these two renders before CARD-198 wires the method in for real.

- [Test run] `/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python -m pytest` from the
  worktree root: full suite green (see hand-off report for the exact count), all 7 guardrail test
  files (`test_export_a4_golden.py`, `test_book_pdf_band.py`, `test_book_puzzle_frame.py`,
  `test_book_pdf_two_up.py`, `test_book_answer_key.py`, `test_book_pdf_memory.py`,
  `test_book_pdf_ink_mode.py`) pass, and the new `tests/test_book_solved_page.py` (27 tests, one
  class per AC plus supporting cases) passes.

- [Scope gate] ⚠ grown: 1 file outside Touches (`tests/test_book_pdf_memory.py`, see [SCOPE+]
  above) — orchestrator classified as GROWN not VIOLATED: G-4 names that file as evidence a
  behavioral invariant holds ("pass unedited"), not as a structural do-not-touch path like G-1's
  explicit `export/**` prohibition; the edit is purely additive (one tuple entry). Also checked:
  only 1/8 of CARD-198's own predicted Touches set for the same file — well under the 30%
  poaching threshold. Forwarded to the reviewer as a SCOPE NOTE for independent judgment.
- [Build gate] PASSED (full, 811s / 13m31s) — 6656 passed, 9 skipped, 0 failed (full-suite lock
  acquired/released around the run).
- [Review 1/3] Score: 7.5 — crit: 0, imp: 1. Important finding: ADR-0037/R2's literal text
  ("every thin/heavy rule ... pure black") is contradicted by the new method's own rendered
  pixels at filled-adjacent boundaries (gray, not black) — flagged by the reviewer as
  self-disclosed by the implementer (Worktree notes "[Tension flagged...]" + G-2) and inert
  today (zero callers), but filed as Important pending an explicit ADR-0037 amendment/carve-out
  before CARD-198 gives this method a live caller. Also: G-4/scope independently re-verified by
  the reviewer as ✓ holds (purely additive registration, confirmed via `grep -rn
  solved_puzzle_page` — zero callers outside the two test files). 2/5 claimed mutants
  independently re-run and confirmed killed. Targeted suite (8 files) 357 passed, 1 skipped,
  62.77s. 3 Minor findings (tautological AC-1 sub-test, a duplicated mm->px formula instead of
  reusing this file's own `type_px()`, asymmetric indexing defensiveness) — none gating. System
  contract: 53/53 rules covered (7 ✓ holds, 45 ⚠ unchecked/no_eligible_fact, 1 ✗ violated =
  ADR-0037/R2 above).
- [Review sync] 1 report(s) → meta/review/ (20261007T131458Z-CARD-197-cycle1.yml, validated
  yaml.safe_load).
- [Adversarial] REFUTED the one Important finding (ADR-0037/R2 literal-text tension,
  book_pdf_generator.py:2152) — independent skeptic found: (1) ADR-0037 itself scopes R2's
  `code:` to `src/nonogram/export/layout.py`, not this file; (2) the card's own Worktree notes
  ("[Tension flagged, not resolved here]") and G-2 already anticipated and explicitly deferred
  this exact reading question to CARD-198's station, "not a reason to block this card"; (3) zero
  reachable callers today (G-3/G-4); (4) the reviewer's own Verdict paragraph already concedes
  "not a defect in this card" — contradicting its own "Important (should fix)" filing. Recount
  after this cycle: crit 0, imp 0. Downgraded to an informational/deferred note for CARD-198 /
  an ADR-0037 amendment discussion — carried forward, not fixed in this card's code.
- [Severity gate 1/3] Score 7.5 < min_score 8 — fix mandatory regardless of the findings
  recount (score threshold is independently necessary). Proceeding to the fix loop to raise the
  score via the non-gating Minor findings (optional quality polish), since no Critical/Important
  finding survived adversarial verification.
- [Fix 1] F-001 (tautological AC-1 sub-test) FIXED — test:
  TestBookSolvedPage_CluesMatchTheGridAndTheUnsolvedPlacement::test_clue_gutters_match_the_unsolved_pages_pixel_for_pixel
  (the tautological assertion removed; this sibling pixel-comparison test is AC-1's real,
  retained evidence). F-002 (duplicated mm->px formula) FIXED — test: full suite (see below);
  caption's font-size computation now calls this file's own `type_px()` instead of
  reimplementing its formula inline; verified algebraically equivalent
  (`type_px(mm * 72/25.4, dpi) == round(mm/25.4*dpi)`). F-003 (indexing-style asymmetry) SKIPPED
  — cosmetic only, no test exercises the mismatch, "fixing" it either removes the loops'
  existing in-bounds-by-construction guarantee or invents a guard shape that doesn't fit;
  reasoning recorded by the fix agent directly in Worktree notes. F-004 (the adversarially
  refuted ADR-0037/R2 finding) explicitly NOT acted on in code — confirmed via diff inspection
  that the gray-boundary rendering logic and every AC-2/AC-3 test are byte-identical to the
  pre-fix commit 47a472b; only an informational acknowledgement note was added.
  DECLARATIONS: F-001/F-002 — none (both are local: no bound, lifecycle, blast radius, error
  class or config meaning changed; F-002 is a pure refactor to an existing equivalent helper).
  Verified myself (orchestrator) by reading both diffs directly, not just the fix agent's own
  summary.
- [Build gate] PASSED (full, 893.95s / 14m54s) — 6655 passed, 9 skipped, 0 failed (one fewer
  pass than cycle 1's 6656, fully accounted for by F-001's removed tautological test; no
  regressions). Full-suite lock acquired/released around the run (one stale-looking appearance
  flagged mid-run by the dispatcher's own monitoring — confirmed not actually stale: the process
  was still legitimately running and completed normally at 893.95s, within the ~9-15 min range
  prior cycles on this repo have shown).
- [Review 2/3] Score: 9.0 — crit: 0, imp: 0 ✓ threshold reached + no critical/important.
  F-001/F-002 independently re-verified RESOLVED (F-001: the surviving sibling test genuinely
  calls `solved_puzzle_page` and pixel-compares both clue gutters against an independently
  rendered unsolved page; F-002: `type_px()` call verified mathematically equivalent to the old
  inline formula across 8 DPI values). F-003 CORRECTLY LEFT AS-IS (re-confirmed the in-bounds
  invariant holds by construction). F-004 NOT RE-RAISED — the cycle-2 reviewer independently
  re-derived the same conclusion from the primary sources (ADR-0037's own `code:` scope, the
  card's pre-declared deferral, a fresh zero-callers grep) rather than deferring to the prior
  skeptic, and filed `ADR-0037/R2 ✓ holds (as literally scoped)` instead of a finding. 2 new
  Minors (both non-gating): F-003 carried forward as a documentation suggestion, and a
  frame-introspection coupling note on the AC-7 caller-attribution spy test. 1 out-of-scope
  observation (CON-020's standing checker doesn't yet walk this uncalled method — correctly
  not blocking, relevant to CARD-198's wiring step). System contract: 53/53 rules covered (10 ✓
  holds, 43 ⚠ unchecked/no_eligible_fact, 0 ✗ violated). Fresh targeted suite: 356 passed, 1
  skipped, 50.73s. One additional mutant independently re-run this cycle (band_identity-call
  flip) and confirmed killed, beyond cycle 1's 2 — 3/5 claimed mutants now independently
  reproduced in total.
- [Review sync] 1 report(s) → meta/review/ (20261007T143006Z-CARD-197-cycle2.yml, validated
  yaml.safe_load, overall_score 9.0).
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0036/R1, CON-020) — independent
  skeptic re-ran the cited tests fresh (dependency-baseline test, 63/63 test_export_a4_golden.py,
  3/3 TestBookSolvedPage_TextHoldsTheTenPointFloor) and re-read the cited code directly; also
  independently reconfirmed the reviewer's CON-020 out-of-scope observation (the standing
  checker `TestInteriorType_EveryFaceHoldsTheFloor` genuinely does not yet reach
  `solved_puzzle_page` — zero production callers — so AC-7's own test is correctly the live
  evidence here, not the standing checker).
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — TestBookSolvedPage_CluesMatchTheGridAndTheUnsolvedPlacement::test_clue_gutters_match_the_unsolved_pages_pixel_for_pixel
  PASSED; confirmed it genuinely calls `solved_puzzle_page` and pixel-compares both clue gutters
  against an independently rendered unsolved page (cycle-1's F-001 fix verified real, not
  cosmetic).
  AC-2 ✓ demonstrated — TestBookSolvedPage_GrayGridlinesBetweenFilledCells (3 tests) PASSED.
  AC-3 ✓ demonstrated — TestBookSolvedPage_GrayOnlyBetweenFilledCells (4 tests, incl. an
  exhaustive every-interior-boundary sweep) PASSED.
  AC-4 ✓ demonstrated — TestBookSolvedPage_TitleBandMatchesBandIdentity (6 tests) PASSED.
  AC-5 ✓ demonstrated — TestBookSolvedPage_CaptionReadsThePictureName (3 tests) PASSED.
  AC-6 ✓ demonstrated — TestBookSolvedPage_CaptionOmittedWhenNoSlack (3 tests) PASSED.
  AC-7 ✓ demonstrated — TestBookSolvedPage_TextHoldsTheTenPointFloor (3 tests) PASSED.
  AC-8 ✓ demonstrated — TestBookSolvedPage_NoColour (2 tests) PASSED.
  AC-9 ✓ demonstrated — TestBookSolvedPage_SameGeometryAsTheUnsolvedPage (2 tests) PASSED.
  G-1 ✓ demonstrated — no file under src/nonogram/export/** in either the commit or the
  uncommitted delta; tests/test_export_a4_golden.py 63/63 passed.
  G-2 ✓ demonstrated — `_stroke_drawing` body unedited (still `fill=INK` only, no new
  param/branch); gray marks drawn by a separate new loop strictly after the verbatim call;
  tests/test_book_pdf_band.py + test_book_puzzle_frame.py + test_book_pdf_two_up.py 143/143
  passed.
  G-3 ✓ demonstrated — `grep -rn solved_puzzle_page` shows zero call sites in
  pack_answer_pages/render_answer_page/answer-key code; tests/test_book_answer_key.py 56/56
  passed.
  G-4 ✓ demonstrated — same grep: zero call sites in interior_pages/interior/interior_stream/
  export_interior; the one test_book_pdf_memory.py edit is confirmed (via diff against
  47a472b's parent) to be exactly one additive PAGE_FACTORIES tuple entry, no assertion
  touched/removed/reordered; tests/test_book_pdf_memory.py 27 passed, 1 skipped (pre-existing).
  G-5 ✓ demonstrated — `_SOLVED_GRID_GRAY = (160, 160, 160)`, a literal plain tuple;
  tests/test_book_pdf_ink_mode.py 41/41 passed.
  No Engineering constraints section on this card (confirmed absent, correctly skipped).
  All 9 AC + all 5 G items: demonstrated. failing_items: empty.
- [Docs step] changed_dirs = src/nonogram/admin/, tests/. No README.md exists under
  src/nonogram/admin/ today, and none of this card's sibling cards touching the same file
  (CARD-144/145/147/167/193/196...) created one — consistent with the backlog's own open item
  ("per-directory READMEs convention" is an undecided owner decision, not yet adopted for this
  directory) — skipped, no README created. tests/README.md exists but is explicitly scoped to
  "Wave 1" features (batch history/puzzle preview/bulk ops) and lists only 4 of the hundreds of
  test files that now exist in tests/ — it has evidently not been kept in sync for any of the
  many cards since Wave 1, so adding an entry for tests/test_book_solved_page.py here would be
  inconsistent with its established (unmaintained-for-this-scope) treatment — left unedited.
- [Success commit] 70d6ad9 "fix: CARD-197 review-cycle polish — real AC-1 test, reuse type_px
  for the caption" on branch card/197-solved-page-renderer, on top of the implementation commit
  47a472b. Committed with explicit pathspecs (src/nonogram/admin/book_pdf_generator.py,
  tests/test_book_solved_page.py only) — nothing under meta/ committed from the worktree.
  Card parked at Status: review, cycle 2/3, score 9.0, pending `/kanban done`/merge (not run by
  this orchestrator per the wave-37 brief). Pre-existing repo hook fired
  "forge: source files changed — how-it-works docs may be stale" on commit — informational,
  not an error; docs refresh is a post-wave step (cmd-run), not this card's job.
