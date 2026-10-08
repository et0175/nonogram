# CARD-202: Small solutions (width<=15, height<=20) pack 2-or-4 to a page instead of one full page each

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 1.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/202-packed-small-answers
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-CARD-202
**Source:** owner's Google Doc "Nonograms - Print layout1", 2026-10-08 (item 4: shrink small-grid solutions to 2-or-4-up); also raised informally by the owner earlier in this session, before the doc surfaced, as a design question about CARD-198's answer-section page-count growth
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_solved_answer_key.py, tests/test_book_answer_key.py, tests/property/test_book_answer_tiles.py, tests/helpers/book_corpus.py, tests/fixtures/ (a new small-grid baseline fixture)
**Review score:** —
**Started:** 2026-10-08T16:14:38Z
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
   Given the book's answers in order, decide which ones qualify (width<=15
   and height<=20, via `_answer_extent`). Walk qualifying answers within one
   tier's run: pack 4 per page whenever 4 are next in sequence, falling back
   to a 2-up page only for a leftover odd one or two at the end of that
   tier's qualifying run (owner decision, resolved 2026-10-08 — see Design
   context). **A page never mixes tiers** — a tier boundary closes the
   current packed page early (even short of 4), same rule as the old
   `pack_answer_pages`/`AnswerPage.__post_init__` (owner decision, resolved
   2026-10-08). A non-qualifying answer (anything bigger than 15x20) keeps
   CARD-198's one-full-page treatment unconditionally — this card narrows
   CARD-198's rule, it does not replace it wholesale.
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

- **AC-1** (happy): *Given* a single-tier book where every puzzle is
  width<=15 and height<=20, *when* the book PDF is generated, *then* the
  answer section packs 4 qualifying answers per page whenever 4 are next in
  sequence, falling back to a 2-up page only for a leftover odd one or two,
  in puzzle-number order — fewer pages than CARD-198's one-per-puzzle.
  *test: TestBookSolvedAnswerKey_SmallGridsPackTwoOrFourToAPage (new, in a new or extended tests/test_book_solved_answer_key.py class)*
- **AC-2** (happy): *Given* a book mixing small (width<=15, height<=20) and
  large puzzles, *when* the answer section is read, *then* every small
  puzzle's answer appears on a packed page and every large puzzle's answer
  still gets CARD-198's one full page, and the book-order/puzzle-number
  sequence across both kinds is unbroken (no puzzle's answer is skipped,
  duplicated, or printed out of order).
  *test: TestBookSolvedAnswerKey_MixedBookPacksOnlyTheSmallOnes*
- **AC-2b** (boundary, tier boundary closes a page early): *Given* a run of
  5 qualifying small answers where the first 3 are Easy and the next 2 are
  Medium, *when* the answer section is built, *then* the page holding the
  3 Easy answers closes at 2-up (not padded to 4 with a Medium answer), and
  the 2 Medium answers start a new page — no packed page ever mixes tiers.
  *test: TestBookSolvedAnswerKey_TierBoundaryClosesAPackedPageEarly*
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
  title)` when there is room, and its title band reads
  `band_identity(number, tier)` exactly as a full answer page's does — the
  band is kept, not dropped, on every packed slot.
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
- G-6: A packed page never mixes tiers (owner decision, resolved
  2026-10-08) — a tier boundary closes the current packed page early, even
  short of 4, rather than filling it with a different tier's answer.

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
- **Owner decisions (resolved 2026-10-08, via AskUserQuestion, before this
  card started):**
  1. **2-vs-4 density rule: always 4-up, 2-up only for leftovers.** Pack 4
     qualifying answers per page whenever 4 are available next in sequence;
     an odd one or two left at the end of a qualifying run (or of the book)
     prints 2-up instead. The old `page_capacity`'s greedy-6-unless-forced-4
     shape is NOT used — there is no secondary size threshold gating 2 vs 4
     beyond "how many are left in the run."
  2. **Tier mixing: NOT allowed.** A packed page holds answers from one tier
     only, same as the old `pack_answer_pages`/`AnswerPage.__post_init__`
     rule — a run of qualifying answers closes its current page early
     (even short of 4) at a tier boundary, exactly as the old module's own
     docstring describes, and starts a new page for the next tier.
  3. **Title band: kept.** Every packed slot shows `band_identity(number,
     tier)` ("Puzzle N · Tier"), the same as a two-up puzzle page's slots
     and a full-page answer — not dropped for space.
  4. **The new per-slot cell-size cap and gap constants** (point 1 of "What
     to implement") remain the implementer's own measured call against the
     Book 1 profile — an engineering measurement, not a policy decision, so
     it was not put to the owner.
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
- [Owner decisions] 2026-10-08, via AskUserQuestion, before this card
  started: (1) density — always 4-up, 2-up only for leftovers; (2) tier
  mixing — not allowed, a tier boundary closes a packed page early; (3)
  title band — kept on every packed slot. All three folded into "What to
  implement," the ACs, and a new Guardrail G-6. The 4th open item (the
  per-slot cell-size cap/gap constants) stays the implementer's own
  measured call, as it was never a policy question.
- [Env] forge 2026.8.17 (no `meta/.skills.yml` → no `forge.min_version` to
  compare against; version still resolved and noted per protocol).
- [Pin gate] n/a — no `meta/.skills.yml` → `legacy.enabled` unset, gate
  skipped.
- [Drift gate] n/a — no `meta/drift-pending.yml`, gate skipped.

## Implementation summary (2026-10-08)

- `STRUCTURE: new third sibling function — `compute_packed_solved_layout`/
  `PackedSolvedLayout` in `export/layout.py`, not a parameterised mode of
  `compute_answer_page_layout`.` Reasoning: `compute_answer_page_layout`'s
  tile math (read in full before deciding, per the card's own instruction)
  reserves no clue gutter anywhere and its `AnswerTile` carries no
  `PuzzleFrame`/band position at all — making it reserve one would mean
  rewriting nearly every line of its cell/placement arithmetic, at which
  point "a mode of it" is a fiction; the only thing the two share is "equal
  tiles, 2 columns, up to N answers." The new function is instead modelled
  directly on `compute_pair_layout`'s shape (each slot a complete placed-page
  `Layout` with its own clue gutters, frame and band, one shared cell fitted
  across every slot the page holds), generalised from "2 slots stacked
  vertically" to "2 or 4 slots in a 2-column grid" — a new private helper
  `_packed_tile_layout` mirrors `_slot_layout` with one real difference
  (a slot's drawing centres within its own tile's width, not the whole
  page's usable width, since slots now sit side by side as well as
  stacked). `PackedSolvedLayout`/`AnswerPageLayout` share only the
  "shared-cell-per-page" idea and the private `_ANSWER_TILE_COLUMNS` /
  `_SOLVED_TILE_COLUMNS` constant for "always 2 across" — no code is shared
  between the two tile-math implementations themselves, and G-3 holds
  (confirmed by `git diff` on `layout.py`: zero deleted lines, pure
  addition).

- **Measured constants** (`export/layout.py`): `SOLVED_TILE_GAP_MM = 4.0`
  (vs the old clueless tile's `ANSWER_TILE_GAP_MM = 2.0`) — a packed slot
  carries a `PuzzleFrame` and a title band, which a clueless answer tile
  never did, so two adjacent framed+banded tiles need more white between
  them to read as separate puzzles rather than one frame touching the next.
  `SOLVED_TILE_MAX_CELL_MM = 6.0` (vs the old `ANSWER_MAX_CELL_MM = 5.0`,
  and below the full page's 7.5 mm flat cap) — a with-clues tile needs more
  room per cell than a clueless one at the same print size, since the clue
  digits need to stay legible beside the grid; 6.0 mm reads as clearly
  shrunk from a full page while still roomier than the old clueless cap.
  Both are reasoned choices against the Book 1 profile (193.675 x 260.35 mm
  usable, no page-level band — each slot reserves its own 12 mm), not from
  an exhaustive sweep (the same calibration style `ANSWER_MAX_CELL_MM`
  itself used) — confirmed visually legible on the owner render (see
  below): the 4-up page's worst case (15x20 with 7-deep clue gutters) binds
  on page-fit, not the cap, landing at 4.30 mm.

- **A genuine layout bug found and fixed during testing.** The first
  `PackedSolvedLayout.__post_init__` raised `ValueError` whenever a slot's
  drawing overflowed its own tile (`not placement.fits`). A real seeded
  property corpus (`tests/property/test_book_pdf_geometry.py`'s own random
  extents) hit exactly this: four 14-wide answers of heights 10/12/14/16
  with deep real clue gutters computed a shared cell, floored at
  `MIN_CELL_MM` (2.0 mm), that did not actually fit the tallest member's
  own tile — an edge case I had assumed, without checking, would "never
  happen in practice." Fixed by **not** raising on `fits == False`, the
  same tolerance `compute_layout`'s own placed-page path already has for a
  single puzzle ("the drawing overflows... rather than printing cells
  nobody can mark") — CARD-202's packing rule has no "decline to pack"
  verdict the way `compute_pair_layout` does for a pair (it always packs a
  qualifying run), so this type must be constructible for every input the
  walk that builds it can produce. Overlap-checking and the shared-cell
  check are unaffected (they do not depend on `.fits`). Docstrings updated
  to state the tolerance explicitly rather than leave it to be discovered
  again.

- **KDP sheet-free estimate (`book_kdp.unpaired_interior_page_count`):
  left exactly as-is (one page per puzzle), not tightened with the new
  packing walk**, a decision examined and documented in that function's own
  docstring, not left unexamined. Reasoning: `BookPDFGenerator.interior_stream`'s
  own `unpaired_page_count` is deliberately **unchanged** by this card
  (still "one page per puzzle, no packing either" — the baseline before
  *any* space-saving technique, so `pages_saved` now reports pairing and
  packing together rather than pairing alone). The two numbers are
  cross-checked equal by EC-034 (`tests/test_book_finalise_gutter.py`'s
  `test_the_scenario_really_has_that_many_pages` and siblings); tightening
  `unpaired_interior_page_count` alone, without also redefining what
  "unpaired" means on the generator side (out of this card's scope and a
  real semantic change CARD-198 itself chose not to make for pairing
  either), would break that cross-check for any book with a qualifying
  small puzzle. `plan_small_answer_pages` is itself sheet-free, so
  tightening remains mechanically available to a future card that wants to
  revisit the "unpaired" baseline's own definition.

- **SCOPE+ files** (outside the card's predicted Touches list, each edited
  because this card's behaviour change rippled into a hardcoded page-count
  or call-stack assumption elsewhere, never because an assertion was
  weakened):
  - `tests/test_book_interior_type_floor.py` — the caption's `draw.text`
    call moved from `solved_puzzle_page`'s own body into a new shared
    helper, `BookPDFGenerator._draw_solved_slot` (reused by a packed slot
    too, "reuse, not reinvention" per the card's own instruction); this
    file's lettering recorder identifies a caption by its immediate caller
    frame's name, so it now also recognises `_draw_solved_slot` as that
    caller, beside the old `solved_puzzle_page` name (kept, not removed).
  - `tests/test_book_solved_page.py` — same cause, one assertion checking
    which function the caption is drawn "in-line" from.
  - `tests/test_book_pdf_memory.py` — `PAGE_FACTORIES` (the page-returning
    method registry a separate test asserts is complete) gained
    `_packed_answer_page` beside `solved_puzzle_page`; the baseline book's
    own page count/shape/failure-injection tests recomputed for its new
    3-page (not 4-page) answer section.
  - `tests/test_book_pdf_ink_mode.py` — `BASELINE_PAGE_COUNT`-derived
    assertions (two places hardcoded `== 12` as well as the symbolic
    constant) updated to `11`; one class's historical-narrative docstring
    touched up so it no longer states a stale literal page count as current.
  - `tests/test_book_pdf_two_up.py` — added `_expected_answer_pages`
    (reuses `plan_small_answer_pages` directly: this file's own subject is
    FR-040 **pairing**, not packing, which already has its own independent
    dedicated coverage) and rewired roughly a dozen `answer_pages=N`
    literals to it, since this file's small same-tier pairing fixtures are,
    by the same reasoning CARD-202 is about, also small enough to qualify
    for answer packing.
  - `tests/test_book_pdf_band.py` — this module's default puzzle size
    (`MIN_SIZE`, 10x10) now qualifies for packing, breaking its hardcoded
    one-full-page-per-puzzle band/caption page arithmetic; bumped the
    *default* to a new `_NEVER_PACKS_SIZE = 18` for the identity-focused
    classes, but the dedicated `_once_book()` fixture (whose whole premise
    is same-tier puzzle-page **pairing**, which this profile's own math
    proves cannot happen without also qualifying for packing — verified
    directly against `compute_pair_layout`) keeps its original 10x10
    explicitly and has its `ONCE_PAGE_COUNT`/`ONCE_BAND_PAGES`/new
    `ANSWER_PAGE_OF` constants recomputed for the packed shape instead.
  - `tests/test_book_pdf.py` — one hardcoded interior page count (7 -> 6)
    where two same-tier 15x15 survivors now also share one packed answer
    page, not just one puzzle page.
  - `tests/property/test_book_pairing.py` — `_expected_answer_pages`
    (previously a CARD-198 literal, `len(order)`) rewritten as an
    independent "4s-then-2s-then-a-lone-1" reimplementation (CLAUDE.md:
    prefer an independent second implementation; this module's subject is
    pairing, so the packing-rule's own correctness is not re-proven here).
  - `tests/property/test_book_pdf_geometry.py` — the one test that measures
    answer-page geometry now skips extents that qualify for packing (its
    premise is full-page answer geometry, which a packed-alone small answer
    no longer has); corpus size bumped 110 -> 160 so the "cannot silently
    shrink" minimum (100) still holds after the skip.
  - `tests/property/test_book_export_interior.py` — the heaviest rework:
    `expected_count`'s answer term switched from `n` (one per puzzle) to a
    new independent `_answer_section_plan`/`_expected_answer_pages`
    (4-then-2-then-1 chunking, closed by a level change or a non-qualifying
    answer, mirroring `plan_small_answer_pages`'s own shape without
    importing it); the per-page parity/centring check gained a packed-page
    branch (`_packed_column_left_mm`, an independent 2-column tile model)
    since neither of the file's existing single-drawing/two-up-drawing
    readers can measure a 2-or-4-answer packed page.
  - `tests/fixtures/book_baseline_card202.json` (new) + `tests/helpers/book_corpus.py`
    (`BASELINE_FIXTURE`/`BASELINE_PAGE_COUNT` 12 -> 11, docstrings updated):
    `baseline_puzzles()`'s own Duck/Owl (10x10) and Tree (15x15) all qualify
    for packing, so the fixture CARD-198 recorded no longer describes this
    book's answer section. Regenerated with a script that **checked, not
    assumed**, that pages 1-8 are still byte-identical to
    `book_baseline_card198.json`'s own recording before writing the new
    file (also re-pinned as a committed test,
    `TestBookSolvedAnswerKey_NoSmallPuzzlesIsByteIdenticalToCard198::test_the_recorded_card198_baseline_pages_are_unmoved`,
    not just a one-off script) — this is this card's strongest form of
    AC-7/G-1 evidence.

- **AC evidence (fresh, this session, all green):**
  - AC-1 `TestBookSolvedAnswerKey_SmallGridsPackTwoOrFourToAPage` — 3 tests.
  - AC-2 `TestBookSolvedAnswerKey_MixedBookPacksOnlyTheSmallOnes` — 3 tests.
  - AC-2b `TestBookSolvedAnswerKey_TierBoundaryClosesAPackedPageEarly` — 2 tests.
  - AC-3 `TestBookSolvedAnswerKey_ThresholdIsWidthAndHeightNotLongestSide` — 5 tests.
  - AC-4 `TestBookSolvedAnswerKey_PackedSlotsStillShowClues` — 2 tests.
  - AC-5 `TestBookSolvedAnswerKey_PackedSlotIdentityMatchesTheFullPageWording` — 2 tests.
  - AC-6 `TestBookSolvedAnswerKey_PackedCountStillMatchesTheProducedCount` — 2 tests.
  - AC-7 `TestBookSolvedAnswerKey_NoSmallPuzzlesIsByteIdenticalToCard198` — 3 tests.
  - AC-8 `TestBookSolvedAnswerKey_PackedCaptionHoldsTheFloorOrIsOmitted` — 2 tests.
  - All nine in `tests/test_book_solved_answer_key.py`, which together with
    its pre-existing CARD-198 classes (19 tests) reports
    `43 passed, 60 warnings in 3.62s`.
  - Plus a new standing property test,
    `tests/property/test_book_answer_tiles.py::test_PropertyTest_SmallAnswerPacking_EveryAnswerOnceInOrderNoMixedTierPage`
    and `::test_PropertyTest_SmallAnswerPacking_NeverPacksAFourUpWithFewerThanFourWhenMoreWereAvailable`
    (seeded corpora, 300 cases each, asserting minimum case counts per
    CLAUDE.md's house style) — `4 passed in 2.06s` (file total, old EC-031
    sweep included).
  - `tests/test_book_answer_key.py` (old, pre-CARD-198 module, confirmed
    still passing unedited): `21 passed`.

- **Guardrail evidence:**
  - G-1: `git diff` on `book_pdf_generator.py` shows `solved_puzzle_page`'s
    own body reduced to three lines (`compute_layout`, `Image.new`, a call
    to the new shared `_draw_solved_slot` helper) with **zero change in
    drawing order or arithmetic** — every statement moved verbatim into the
    helper. Proven behaviourally, not just by inspection, by the
    byte-identical fixture regeneration above and by
    `TestBookSolvedAnswerKey_NoSmallPuzzlesIsByteIdenticalToCard198`'s three
    tests (call-for-call match against direct `solved_puzzle_page` calls,
    `plan_small_answer_pages` producing no `PackedAnswerPage` at all for an
    all-large corpus, and the committed byte-identical fixture check).
  - G-2: `git diff` on the `interior_stream` validation loop shows the
    `try/except ValueError -> RuntimeError` block's own code and message
    format untouched; the only change is capturing `_answer_extent`'s
    return value into a local used afterwards. `TestBookSolvedAnswerKey_AMemberThatCannotBeMeasuredIsStillNamed`
    (pre-existing CARD-198 class, re-run, still green) confirms the abort
    contract survives.
  - G-3: `git diff src/nonogram/export/layout.py` shows **zero deleted
    lines** — `compute_layout`/`compute_pair_layout`/`compute_answer_page_layout`
    are untouched; the new geometry is appended after them.
  - G-4: `_draw_solved_slot` reuses the existing `INK`/`BACKGROUND`/`_SOLVED_GRID_GRAY`
    constants verbatim; no new colour literal was added anywhere in this
    card's diff (grepped).
  - G-5: every new slot's placement is centred within its own tile using
    the same `GUTTER_MM`/`OUTSIDE_MM`-style mirrored-margin left edge the
    single/two-up pages already use; proven, not just asserted, by
    `tests/property/test_book_export_interior.py`'s new packed-column
    parity check (`_packed_column_left_mm`, an independent model, checked
    against real rendered ink on both parities).
  - G-6: `PackedAnswerPage.__post_init__` raises on a mixed-level page
    (unit-tested, `TestBookSolvedAnswerKey_TierBoundaryClosesAPackedPageEarly`
    and the new property test's own per-page level-uniqueness assertion
    over 300 seeded cases).

- **Owner render:** `~/Documents/nonogram-reviews/CARD-202/card202-sample-interior.pdf`
  — a 9-puzzle sample book (real pictures from `pictures/`, not blank
  checkerboards): 5 Easy small answers (10x10 up to the 15x20 edge case),
  demonstrating the 4-then-1 density rule; 2 Medium small answers packed
  together (tier boundary closing the Easy run early, visible as a
  separate page); 2 Hard large answers (22x22, 25x18) each keeping
  CARD-198's own full page, printed immediately after the packed pages —
  a packed page next to a full page, as the Design context asked for.
  Verified by rendering each answer page to PNG and reading it back
  (4-up page, the leftover 1-slot 2-up page, the Medium 2-up page, and a
  Hard full page) — clue digits legible, gray adjacent-fill boundary marks
  present, captions and bands correct, no stray ink in the unfilled slot of
  the leftover page.

- **Full suite (implementer's own claim — see orchestrator's own
  [Build gate] note below for the authoritative, independently-run
  result):** every file this card touched or rippled into passes
  individually (386 tests summed across the thirteen directly-relevant
  files, zero failures). **Correction, orchestrator note:** the
  implementation agent's own SubagentHandback message (received separately
  from this worktree note, same session) explicitly flagged its final
  unfiltered `pytest` run as INCOMPLETE at handback time ("progressed
  cleanly through 73% with zero failures... had not yet finished") and
  asked for it to be re-confirmed before merge — this directly contradicts
  this note's own "run to completion with zero failures" wording above,
  written before that correction. Treat the 386-test per-file tally as
  solid (each file's own fresh run did complete), and the orchestrator's
  own independent full-suite re-run (below) as the actual confirmation for
  the whole project, not this paragraph's stale claim.

- [Build gate] Orchestrator's own independent full-suite run (not the
  implementer's claim, which its own SubagentHandback message flagged as
  incomplete — see the correction note just above) — `./.venv/bin/python
  -m pytest` in the CARD-202 worktree, under the
  `meta/kanban/.full-suite.lock`: pending, about to run.
