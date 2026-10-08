# CARD-202: Small solutions (width<=15, height<=20) pack 2-or-4 to a page instead of one full page each

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout1", 2026-10-08 (item 4: shrink small-grid solutions to 2-or-4-up); also raised informally by the owner earlier in this session, before the doc surfaced, as a design question about CARD-198's answer-section page-count growth
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_solved_answer_key.py, tests/test_book_answer_key.py, tests/property/test_book_answer_tiles.py, tests/helpers/book_corpus.py, tests/fixtures/ (a new small-grid baseline fixture)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- Since CARD-198, every drawable puzzle's solution prints on its own full
  page: `BookPDFGenerator.interior_stream`'s `produce()` loop
  (`book_pdf_generator.py` ~2603-2618) calls `solved_puzzle_page(payload, n,
  page_number, title)` once per puzzle, in book order, and
  `InteriorStream.answer_page_count`/`unpaired_page_count` both read
  `len(payloads)` — unconditionally one page per puzzle, with nothing left
  to pack (CARD-198's own Guardrail G-5 and "What to implement" point 3).
- `solved_puzzle_page` (`book_pdf_generator.py` 1972-2150, read in full) draws
  **with clues**: `compute_layout(payload.row_clues, payload.column_clues,
  self.page_spec(page_number))` gives it the same cell/gutter/frame geometry
  an unsolved puzzle page would get, then fills, re-strokes gray boundaries
  between filled-adjacent cells (CARD-197), writes clues (`_write_clues`),
  the title band (`_set_band`/`band_identity`, "Puzzle N · Tier") and a
  caption below the drawing (`answer_caption`/`answer_title`, "Puzzle N —
  Title", omitted when the slack below the drawing is smaller than the
  caption's own line height).
- The **old**, pre-CARD-198 packed key (`book_answer_key.py`, read in full —
  left in the module unedited per CARD-198's Guardrail G-5, no longer called
  by production) packed 6-up (longest side <= `SIX_UP_LONGEST_SIDE = 20`) or
  4-up (`page_capacity`, `pack_answer_pages`), with **no clues at all**
  (FR-042's old statement: "no row or column clues") and no per-slot title
  band — only a caption. Its geometry comes from
  `export/layout.py`'s `compute_answer_page_layout`/`AnswerPageLayout`/
  `AnswerTile` (read in full): `ANSWER_TILE_CAPACITIES = (4, 6)` (2 columns x
  2 or 3 rows), each tile sized `min(ANSWER_MAX_CELL_MM=5.0mm, tile-width-fit,
  tile-height-fit)`, with `ANSWER_CAPTION_MM = 6.0` reserved per tile for the
  caption and **no gutter reserved for clues anywhere in the tile math** —
  the old layout was built for a clueless tile and has no notion of a clue
  gutter's width/height.
- `pack_answer_pages` additionally requires **every answer on one page to
  share one level/tier** (`AnswerPage.__post_init__`: "an answer page holds
  one level, not ..."), closes a page late (the next answer joins only if
  the page with it still fits its own capacity), and gives every level's
  first page a heading, every later page of the same run none.
- **This card's "2 or 4" threshold is a different rule from the old
  `SIX_UP_LONGEST_SIDE`/`page_capacity`:** the owner's doc states a literal
  rectangle bound — width<=15 **and** height<=20 (asymmetric, both sides
  checked separately) — not a single longest-side bound the old module used.
  `_answer_extent` (`book_pdf_generator.py` 1393-1420, read in full) already
  reads a payload's `(width, height)` by the same rectangle check CARD-198's
  eager validation pass reuses; this card's threshold check reuses that
  reader rather than inventing a second one.

**The real gap this card must close, not just wire around.** Reusing
`compute_answer_page_layout` as-is does **not** satisfy the owner's broader
"full solved page with clues" direction CARD-197/198 already shipped and the
owner already approved: that function's tile math reserves no clue gutter at
all, and its renderer (`export/png.py`'s `render_answer_page`) draws no clue
digits. Packing 2-or-4 small solutions onto a shared page **while keeping
clues** needs a new tiling geometry — most honestly, a new function beside
`compute_pair_layout`/`compute_answer_page_layout` in `export/layout.py`
(COMP-007, ADR-0036/R2: "book page geometry is computed only by COMP-007's
layout functions") that, for each of 2 or 4 slots, calls the same
cell-sizing math `compute_layout` already does (clue gutter reserved,
`drawing_bottom`/`usable_bottom` slack for a caption, per the two-up
precedent `compute_pair_layout`/`PairLayout` already sets for exactly two
simultaneous `Layout`s sharing one page). **This is this card's main
estimate risk** (see Worktree notes) — it is not a renderer-only change,
it is a new COMP-007 layout primitive.

1. **New layout geometry (`export/layout.py`).** Add a 2-up and a 4-up
   tiling layout that reserves each slot's own clue gutters (reusing
   `compute_layout`'s cell-sizing approach per slot, analogous to how
   `compute_pair_layout` builds two `Layout`s that share one page today —
   read that function in full, 1735-1855-ish, before designing this one).
   Each slot's cell size is capped well below a full-page puzzle's size
   (the owner's whole point is "shrink" — a literal 7.5mm/5mm-class cap per
   slot, the implementer's own measured call against the Book 1 profile,
   analogous to `ANSWER_MAX_CELL_MM`/`TWO_UP_MIN_CELL_MM`'s precedent of a
   named, measured constant rather than an arbitrary one). Name the new cap
   and gap constants explicitly (e.g. `SOLVED_TILE_MAX_CELL_MM`,
   `SOLVED_TILE_GAP_MM`) rather than reusing `ANSWER_MAX_CELL_MM`/
   `ANSWER_TILE_GAP_MM` verbatim, since the old constants were tuned for a
   clueless tile and a with-clues tile needs more room per cell at the same
   print size — re-derive, do not assume the old numbers still fit.
2. **New packing rule (`book_answer_key.py` or a sibling pure module).**
   Given the book's answers in order, decide which ones qualify
   (width<=15 and height<=20, via `_answer_extent`) and how 2-vs-4 density is
   chosen for a page of qualifying answers — **a real open decision, not
   resolved by this brief** (see Design context). Whether a page may mix
   answers of different tiers (the old `pack_answer_pages` forbids it; the
   doc does not say) is a second open decision. A non-qualifying answer
   (anything bigger than 15x20) keeps CARD-198's one-full-page treatment
   unconditionally — this card narrows CARD-198's rule, it does not replace
   it wholesale.
3. **Renderer (`book_pdf_generator.py`).** A new page-drawing method beside
   `solved_puzzle_page`/`_two_up_page` that, for a page of 2 or 4 small
   answers, calls the new layout for each slot and draws each slot with the
   **same drawing steps** `solved_puzzle_page` already uses (fill, CARD-197's
   gray boundary marks, `_write_clues`, `_set_band`, caption with its
   slack/omission check) — reuse, not reinvention, same precedent as
   `_two_up_page` reusing `_stroke_drawing`/`_write_clues`/`_set_band` for
   each of its two slots.
4. **`interior_stream`/`InteriorStream`.** `answer_page_count` becomes the
   number of answer pages the new packing walk actually produces (<=
   `len(payloads)`, strictly less whenever at least one small puzzle packs),
   replacing CARD-198's unconditional `len(payloads)`. The eager validation
   pass (CARD-198's rectangle check, `RuntimeError("puzzle <id> could not be
   laid out: ...")`) is unaffected — it is extent validation, not packing,
   and still runs before any page is drawn.
5. **`book_kdp.unpaired_interior_page_count`.** CARD-198 dropped this
   function's packing estimate entirely (`answer_pages=len(ordered)`, one
   per puzzle, sheet-free). This card's packing, when it fires, makes that
   upper bound *looser than the real count* again for books with small
   puzzles (same shape as the gap CARD-198's own notes flagged for
   `unpaired_interior_page_count` the other direction) — decide and document
   whether this sheet-free estimate is tightened back up (partially
   restoring a packing estimate there) or left as a known-loose upper bound,
   and say which; do not silently leave it unexamined.
6. **A genuine, if partial, mitigation for CARD-198's own flagged risk.**
   CARD-198's Design context flagged, unresolved: "a previously-finalising
   book can now refuse outright [from the 300/590-page KDP ceiling] purely
   from page growth alone" (demonstrated: a 444-puzzle corpus went
   299->669 pages). This card reduces answer-section page count for books
   whose puzzles are small enough to qualify — note this honestly as a
   partial mitigation (only the width<=15/height<=20 subset benefits; a book
   of all-large puzzles sees no improvement from this card) rather than
   claiming it resolves CARD-198's flagged risk in general.

## Acceptance criteria

- **AC-1** (happy): *Given* a book where every puzzle is width<=15 and
  height<=20, *when* the book PDF is generated, *then* the answer section
  holds fewer pages than one-per-puzzle would, packed 2-or-4 per page per
  this card's density rule (rule to be pinned by the implementer's resolved
  design decision — see Design context), in puzzle-number order.
  *test: TestBookSolvedAnswerKey_SmallGridsPackTwoOrFourToAPage (new, in a new or extended tests/test_book_solved_answer_key.py class)*
- **AC-2** (happy): *Given* a book mixing small (width<=15, height<=20) and
  large puzzles, *when* the answer section is read, *then* every small
  puzzle's answer appears on a packed page and every large puzzle's answer
  still gets CARD-198's one full page, and the book-order/puzzle-number
  sequence across both kinds is unbroken (no puzzle's answer is skipped,
  duplicated, or printed out of order).
  *test: TestBookSolvedAnswerKey_MixedBookPacksOnlyTheSmallOnes*
- **AC-3** (boundary, the threshold edge): *Given* an answer exactly
  15 wide x 20 tall, and one 16 wide (or 21 tall), *when* the answer section
  is built, *then* the 15x20 answer qualifies for packing and the
  16-wide/21-tall one does not — the check is width<=15 AND height<=20,
  not a longest-side bound.
  *test: TestBookSolvedAnswerKey_ThresholdIsWidthAndHeightNotLongestSide*
- **AC-4** (happy, clues preserved): *Given* a packed small-answer slot,
  *when* it is read, *then* its row and column clues are present and equal
  `nonogram.clues.encode_line` of its grid — the packed page is not a
  reversion to the old clueless tile.
  *test: TestBookSolvedAnswerKey_PackedSlotsStillShowClues*
- **AC-5** (happy, caption/band per slot): *Given* a packed page, *when*
  each slot is read, *then* its caption reads `answer_caption(number,
  title)` when there is room, and [its title band reads `band_identity`/is
  dropped per the implementer's resolved design decision — see Design
  context] — pin whichever this card ships.
  *test: TestBookSolvedAnswerKey_PackedSlotIdentityMatchesTheFullPageWording*
- **AC-6** (negative, page-count/parity preserved): *Given* any book,
  *when* `InteriorStream.answer_page_count` and `_as_planned`'s own tripwire
  are checked against a real export, *then* the planned count equals the
  produced count, and FR-043/INV-013 parity still holds at every interior
  position.
  *test: TestBookSolvedAnswerKey_PackedCountStillMatchesTheProducedCount*
- **AC-7** (negative, CARD-198 regression guard): *Given* a book where no
  puzzle qualifies (every one is width>15 or height>20), *when* the book PDF
  is generated, *then* its answer section is byte-identical to CARD-198's
  one-page-per-puzzle output — this card changes nothing for a book with no
  small puzzles.
  *test: TestBookSolvedAnswerKey_NoSmallPuzzlesIsByteIdenticalToCard198*
- **AC-8** (negative, CON-020): *Given* a packed slot's caption (not the
  clue digits, which stay exempt), *when* it is measured, *then* it holds
  CON-020's 10pt floor whenever it is drawn, or is cleanly omitted (never
  shrunk below the floor) when the slot has no room, the same
  slack/omission discipline `solved_puzzle_page`'s caption already has.
  *test: TestBookSolvedAnswerKey_PackedCaptionHoldsTheFloorOrIsOmitted*

## Guardrails

- G-1: A puzzle whose width>15 or height>20 is drawn exactly as
  `solved_puzzle_page` already draws it today (CARD-197/198, unedited) —
  this card narrows which puzzles get a full page, it does not change the
  full-page drawing itself.
- G-2: CARD-198's eager validation pass (the rectangle-extent check and its
  `RuntimeError("puzzle <id> could not be laid out: ...")` abort shape,
  matched by `app.py`'s `_is_an_unpackable_row`) is unedited and still runs
  before any page is drawn.
- G-3: `compute_layout`/`compute_pair_layout`/`compute_answer_page_layout`
  (the three existing COMP-007 layout entry points) are not edited by this
  card — a new, additional layout function is added beside them, per
  ADR-0036/R2's "layout functions place, nothing else does."
- G-4: Black-and-white only (CARD-147) — the new renderer draws no colour
  beyond CARD-197's existing `(v, v, v)` gray-gridline tone.
- G-5: FR-030/ADR-0036 mirrored-margin placement is respected by every new
  slot exactly as it already is for a two-up page's two slots.

## System contract

_Assembled 2026-10-08 by `system_rules.py --card CARD-202` (55 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scala… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dimens… (check: review-lens)
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
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-members… (check: review-lens)
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
- CON-019 — Adding book-specific page geometry (a trim, margins, a title band, a portrait-only rule, the 7.5 mm standard cell) never changes the CLI's or the web UI's exports: fo… (check: test: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
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

_(Note: CON-019 appears here because `Touches` includes `src/nonogram/export/layout.py` — a new layout function proposed by this card. Not-yet-checked rules (`review-lens`) are narrative design rules this card's own review cycle must judge directly, not test-automated today.)_

## Architecture context

- **FR:** FR-042/INV-011 (the book's answer key) — this card further amends
  the statement CARD-198 already made partially stale (CARD-198's own
  Architecture context already flagged FR-042/INV-011 as needing an
  architect-station delta; this card adds a second, different packing rule
  on top, which the same delta should capture once both cards have
  shipped). No edit to `meta/architecture/**` is made by this card itself
  (kanban cards only read `meta/architecture/`, per the kanban skill's own
  "What the skill does not do").
- **ADR:** ADR-0036/R2 (layout functions are the only place that places
  things — this card's new tiling geometry must live in `export/layout.py`,
  not in `book_pdf_generator.py`/`book_answer_key.py`), ADR-0037/R1 (title
  only on an answer/solution page — already the case for `solved_puzzle_page`
  and unaffected by packing it smaller).
- **CON:** CON-020 (10pt floor, clue-digit exemption — AC-8), CON-011
  (10..30 cell sides — the threshold check does not change which grids a
  book may hold, only how its answer pages are tiled).
- **Components:** COMP-007 (`export/layout.py`, new tiling function),
  COMP-009 (`book_pdf_generator.py`/`book_answer_key.py`/`book_kdp.py`, the
  packing rule and renderer).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card (no
  edit under `meta/`); revisit alongside CARD-198's own already-flagged
  FR-042/INV-011 delta once both cards have shipped.

## Design context

- **Output:** the book's answer-key section — a subset of its pages (small
  puzzles) packed 2-or-4 to a page with clues, the rest (CARD-198's
  one-per-puzzle full pages) unchanged.
- **Owner decisions needed before this card is implemented (flagged here,
  not guessed at):**
  1. **The exact 2-vs-4 density rule.** Candidates: (a) mirror the old
     `page_capacity`'s greedy "4 unless everything on the page is small
     enough for 6" shape, adapted to a 2/4 choice by some new secondary
     threshold; (b) always 4-up when 4 qualifying answers are available in
     sequence, falling back to 2-up only for a leftover odd one or two; (c)
     something else. The doc's "2 or 4" does not by itself pin which.
  2. **Whether a packed page may mix tiers.** The old `pack_answer_pages`
     forbids mixing levels on one page (`AnswerPage.__post_init__`); the
     doc's ask says nothing about tier. Keeping that constraint costs more
     pages (a level boundary closes a page early, as the old module's own
     docstring explains); dropping it packs tighter but loses the
     one-level-per-page property CARD-198's "no separate level-heading or
     divider page" decision leaned on (every page's own band already names
     its tier — a mixed-tier packed page still shows each slot's own tier
     via its own band, so this may be a safe relaxation, but it is a real
     behavior change from the pre-CARD-198 key and needs an explicit call).
  3. **Whether a packed slot keeps its title band** (`band_identity`,
     "Puzzle N · Tier") the way a two-up puzzle page's slots do, or drops it
     for space the way CARD-198 dropped the old per-level heading — flag
     this rather than silently picking, the same discipline CARD-198 used
     for its own level-heading removal.
  4. **The new per-slot cell-size cap and gap constants** (point 1 of "What
     to implement") — a real measured value against the Book 1 profile,
     not yet derived in this draft.
- **Renders:** `~/Documents/nonogram-reviews/CARD-202/` (owner visual check
  before merge) — a small sample book mixing a few small puzzles (some at
  exactly the 15x20 edge, some well inside it) with a couple of large ones,
  showing a packed page next to a CARD-198 full page, so the owner can
  judge legibility of the shrunk clues and confirm the chosen density rule
  before merge — same render discipline CARD-197/198 both used for their
  own owner-visible defaults.

## Worktree notes

- [Origin] Owner's Google Doc "Nonograms - Print layout1", 2026-10-08, item
  4: "Solutions - please shrink grids that with height<=20 and width<=15 so
  that it'd be possible to have 2 or 4 solutions on page." Also discussed
  informally with the owner earlier in this session (before the doc
  surfaced) as a reaction to CARD-198's "~6x more answer pages" growth —
  treat the direction as owner-confirmed; the open items below are
  mechanism questions, not whether to build this.
- [Verified facts the implementer must not re-derive]
  - `solved_puzzle_page` (`book_pdf_generator.py` 1972-2150) is CARD-197's
    full-page-with-clues renderer, reused by this card's packed-slot
    drawing steps (fill, gray-boundary marks, `_write_clues`, `_set_band`,
    caption with slack/omission).
  - `_answer_extent` (`book_pdf_generator.py` 1393-1420) is the existing
    `(width, height)` rectangle reader to reuse for the 15x20 threshold
    check — do not add a second extent reader.
  - `book_answer_key.py` (`pack_answer_pages`/`AnswerPage`/`Answer`/
    `page_capacity`/`SIX_UP`/`FOUR_UP`/`SIX_UP_LONGEST_SIDE`) is the
    **old, pre-CARD-198** packing precedent, left in the module unedited
    per CARD-198's Guardrail G-5 but **not directly reusable**: it was
    built around a longest-side-only threshold (20) and a clueless tile
    geometry, neither of which matches this card's width/height-pair
    threshold or its keep-the-clues requirement. Read it for the *shape*
    of a packing walk (forward-only, closes late, one-level-per-page), not
    for a drop-in function to call.
  - `export/layout.py`'s `compute_answer_page_layout`/`AnswerPageLayout`/
    `AnswerTile` (2149-2266+) is the old **clueless** tiling geometry —
    `ANSWER_TILE_CAPACITIES = (4, 6)`, no 2-up capacity exists today, no
    clue gutter reserved anywhere in its tile math. This card needs a
    **new** tiling function (point 1 of "What to implement") — confirmed
    by reading this function in full, not assumed.
  - `compute_pair_layout`/`PairLayout` (1665-1855) is the existing
    precedent for two `Layout`s (each with its own clue gutters) sharing
    one page, `TWO_UP_MIN_CELL_MM = 7.0` is its own cell floor — the
    closest existing analogue to what this card's 2-up slot needs, though
    built for same-size puzzle pairing (INV-010), not for a shrink-to-pack
    rule.
  - `tests/helpers/book_corpus.py`'s two documented fixtures
    (`baseline_puzzles`, 4 puzzles / 12 interior pages;
    `corpus_puzzles`, 150 puzzles / ~305 interior pages) are CARD-198's own
    numbers — neither fixture's exact puzzle sizes were confirmed against
    this card's 15x20 threshold while drafting; the implementer must check
    whether either exercises the new packing path, and very likely needs a
    **new small-grid fixture** (CARD-198 added its own new baseline
    fixture for the same reason — follow that precedent) committed in its
    own commit per the card-pipeline-brief rule ("Touches lists the book
    baseline files for pixel changes").
- [Tension flagged, not resolved here] Whether this card's new layout
  function belongs in `export/layout.py` as a true third sibling of
  `compute_layout`/`compute_pair_layout`/`compute_answer_page_layout`, or
  whether it is closer to a parameterised generalisation of
  `compute_answer_page_layout` that gains an optional "reserve clue
  gutters" mode — both keep ADR-0036/R2's letter (COMP-007 is the only
  place that places things); which is the better shape is an implementation
  judgment call, not pinned by this brief.
- [AC cross-check] AC-1/AC-2/AC-3 map to "What to implement" points 1-2,
  AC-4/AC-5 to point 3 (clues-preserved + the two open per-slot design
  questions), AC-6 to point 4, AC-7 to the "narrows, does not replace"
  framing throughout, AC-8 to CON-020. No AC asks for an order or a case
  the body doesn't also describe.
- [Estimate] 1.5d, above the brief's 1-day flag, because of the new
  COMP-007 layout primitive (point 1) — this is architecturally the same
  weight class as CARD-197 (a new rendering/layout primitive) plus CARD-198
  (a packing-rule + page-count-ripple wiring job), not a small tweak to
  either. If it needs to split: (a) the new layout geometry + the packing
  rule's resolved density/tier/band decisions, with their own tests
  (~0.75-1d); (b) the renderer wiring into `interior_stream`, the KDP
  sheet-free-estimate decision, the new fixture, and the owner-visible
  render (~0.5-0.75d).
- [Not in this card] Formalising the requirements delta (amending
  FR-042/INV-011 a second time, after CARD-198's own pending delta, to
  state this card's packing rule) and updating `meta/architecture/trace.yml`
  — architect-station follow-up, same pattern CARD-198 used for its own
  FR-042 staleness.
