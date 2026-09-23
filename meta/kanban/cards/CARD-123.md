# CARD-123: Every tile shows its cell on the book's trim, below-floor flagged with an override control; finalise counts below-floor puzzles

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/123-tile-cell-and-floor-count
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-14 (surface half of FR-031; closes Increment 14)
**Idea:** —
**Wave:** 24
**Depends on:** CARD-121, CARD-122
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_select_puzzles.html, src/nonogram/admin/templates/book_finalize.html, tests/test_book_select_floor_tiles.py, tests/property/test_book_membership_floor.py
**Review score:** 9.3 (cycle 2/3)
**Started:** 2026-09-23T03:55:53Z
**Closed:** 2026-09-23T06:14:13Z
**Actual:** 0.3d
**Merge commit:** 8b7b78e
**Blocked by:** —

## What to implement

1. **Tile cell.** Every tile on the selection tabs shows the puzzle's cell on the book's
   current trim and margins, already capped at 7.5 mm, computed with CARD-115's
   `book_cell_mm(book_page_spec(book), …)`. It is the same call CARD-121's refusal and
   CARD-116's PDF make. Format: one decimal place is too coarse near the floor (4.84 vs
   4.8), so use two decimals ("4.61 mm").
2. **Below-floor flag** on a tile under 4.8 mm, plus an **explicit override control**
   (e.g. a labelled "Include below floor" checkbox bound to the `override_<id>` field
   CARD-121 reads). A wide grid carries **no flag of its own** (FR-032 amended; AC-191/192
   retired). Only the floor flags.
3. **Finalise summary** (`book_finalize.html`) counts the book's puzzles below the floor,
   **recomputed on the book's current trim and margins** every time it renders. It is
   not read from stored overrides, so a trim change after curation shows up (AC-188).
4. Extend `PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride` with the
   agreement half of EC-021: for any puzzle and trim, the tile's value, the add
   refusal's value and the finalise count's per-puzzle verdict are one number.

## Increment 14 checkpoint (this card closes it)

A new book's Print setup shows 150 at 40/40/20 and the AC-198 matrix (≤15: 20/7/0,
16-20: 30/27/6, 21-25: 10/20/12, 26-30: 0/6/12). The plan survives leaving and
reopening (CARD-119/120). On the selection step, a 30×25 puzzle with a 12-deep row clue
shows 4.61 mm with a below-floor flag. It is refused on both the tab and the paste-IDs
route, and then accepted with an override that the finalise summary counts
(CARD-121/123). A 100-puzzle book with one cell at 14% against 10% is refused with that
cell named, a `draft → ready_for_kdp` jump is refused the same way, and at 13% it passes
(CARD-124). Put a rendered selection tab and the finalise summary in
`~/Documents/nonogram-reviews/CARD-123/` for the owner's eye.

## Acceptance criteria

- **AC-182** — given a Book 1 profile book and a 30-wide x 25-tall puzzle whose row-clue gutter is 12 entries deep and column-clue gutter 8 deep (42 cells across, 4.61 mm on the trim), when the puzzle-selection step lists it, then its tile shows a 4.61 mm cell with a below-floor flag.
  *test:* `TestBookSelect_TileShowsCellAndBelowFloorFlag`
- **AC-241** — given a Book 1 profile book and a 25-wide x 12-tall puzzle whose book cell is 6.0 mm (above the 4.8 mm floor), when the puzzle-selection step lists it, then its tile carries no flag — neither a wide-grid flag nor a below-floor flag.
  *test:* `TestBookSelect_WideGridAboveFloorCarriesNoFlag`
- **AC-187** — given a book holding 150 puzzles, 2 of them added below the floor with overrides, when the finalise step renders its summary, then the summary reports 2 puzzles below the 4.8 mm floor.
  *test:* `TestBookFinalize_SummaryCountsPuzzlesBelowFloor`
- **AC-188** — given a Book 1 profile book holding a 20x20 puzzle with 8-deep row- and column-clue gutters (6.92 mm on 8.5 x 11), no puzzle below the floor, when its trim is changed to 6 x 9 in and the finalise summary is rendered, then the summary reports 1 puzzle below the floor (4.65 mm on the new trim).
  *test:* `TestBookFinalize_SummaryRecountsBelowFloorAfterTrimChange`
- **AC-239** (NFR-008) — given a Book 1 profile book holding a 30-wide x 25-tall puzzle with a 12-deep row-clue gutter, when its book cell is computed, then cell < 4.8 mm (4.61 mm) and the puzzle is flagged below the floor (FR-031).
  *test:* `TestBookCell_TwelveDeepBandFallsBelowFloor` — _flag half here; the 4.61 mm cell is CARD-114._

## Engineering constraints

- **EC-021** (consistency, INV-006) — For any puzzle, any stored trim and margins and every add route (selection step, paste-IDs form, any future route ending in the book store), a puzzle whose book cell is below 4.8 mm becomes a member only together with a stored override for its id; and the tile's cell, the add refusal and the finalise count all come from the one computation FR-030's PDF uses, so no two of them can disagree about a puzzle.
  *test:* `PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride`

## Guardrails

- G-1: One computation. Tile, refusal and finalise count all call `book_cell_mm`, and the admin fits no cell itself (ADR-0036/R2, EC-021).
- G-2: No wide-grid flag. AC-191/AC-192 are retired, and only the floor flags a tile (FR-032 amended 2026-09-22 (b)).
- G-3: Out of scope: BK-UI-8 (unstated add-puzzles ask; back to the owner).
- G-4: Do not edit `src/nonogram/admin/book_manager.py` or `src/nonogram/admin/templates/book_arrange_puzzles.html`. They are owned by CARD-126 this wave. Do not edit `src/nonogram/admin/book_pdf_generator.py`, which is owned by CARD-117 this wave.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as … (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it … (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from … (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by more than 2x from the source's INK BOUNDING BOX … (check: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the other side from the source's own aspect ratio, … (check: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniqueness from the fact that a grid was repaired. (check: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit on one lineage, is a named constant beside it and is … (check: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that set holds no filled/empty pair), so the filled … (check: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws nothing from the injected Random or from host state, … (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DENSITY and MAX_DENSITY are the only statement of … (check: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density grounds, and no module's documentation claims … (check: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the share of cells settled at that rung; each … (check: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the tier is derived from … (check: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of the solve and … (check: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them, intersected), and are re-derived natively inside … (check: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all (empty or None per-cell tags, an all-zero … (check: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid it was handed and refuses, with … (check: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never satisfies a quality minimum, is never the left … (check: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id). (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percentage points of that cell's planned share. (check: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the … (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form … (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This … (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an … (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a parameter: no supported call into nonogram.admin.app widens … (check: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not pass the door in force. With it unset (the … (check: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured maximum bound (NFR-002). (check: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (check: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit move inside that level … (check: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; pairing never changes … (check: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 … (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; … (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the interior's; the cover is … (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-031, FR-032 (AC-241)
- **NFR:** NFR-008
- **ADR:** ADR-0036
- **Components:** COMP-009, COMP-007 (consumed)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md (direction + anti-patterns), tokens.css (all visual values), components.md (inventory + states)
- **UI components:** PuzzleTile (extend — add a "below floor" state with its cell value and an override checkbox; update components.md's PuzzleTile states), StatBlock (reuse on finalise for the below-floor count; "zero" renders 0, never hidden), Flash / Alert (reuse — refusal message naming mm vs floor)
- **Screens:** /book/<id>/select-puzzles, /book/<id>/finalize
- **Standards:** forge:engineering-standards §11 (tokens-only styling, all listed states, a11y minimum — the flag is text, not colour alone)

## Worktree notes

—

- [Handover from CARD-121, 2026-09-23] Use BookManager.below_floor(book_id, puzzle_ids) -> a FloorRefusal per below-floor puzzle carrying cell_mm (already the tile's and the finalise count's computation); floor_refusals(...) is the same minus overridden ids. Known limitation, fails safe: an override ticked on tab A and committed from tab B is not carried — the puzzle is refused by name.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

- [CARD-123, 2026-09-23] **Done.** The tile's cell, the floor flag with its
  override control, and the finalise count — all three through
  `book_cell_mm(book_page_spec(book), …)`, nothing fitted in the admin (G-1,
  ADR-0036/R2).

  *What was added.* Three nested helpers in `create_app`, immediately above
  `select_puzzles_for_book` (additive, nothing reordered): `_clue_lines`
  (stored clue field → the tuple-of-tuples `compute_layout` takes,
  reimplemented natively rather than imported from `book_manager` — the
  project's rule for logic two modules need, and held to the store's own
  answer by the property test), `_book_cells(book, records)` →
  `{id: cell in mm | None}`, and `_misses_the_floor(cell)` (`None` counts as
  missing it, the posture `BookManager.below_floor` already takes). Both
  routes gained context keys only: the selection step `book_cells` +
  `floor_mm`, finalise `below_floor` / `below_floor_count` / `floor_mm`, the
  count recomputed on the book's current print columns every render and never
  read back from the stored overrides (AC-188).

  *G-2 checked before touching anything:* there was no wide-grid flag in
  `book_select_puzzles.html` to begin with, so AC-241 is "still none" plus a
  test that pins it. G-4 held: `book_manager.py`,
  `book_arrange_puzzles.html` and `book_pdf_generator.py` untouched —
  `below_floor`/`floor_refusals` are called, never modified, and no new
  `BookManager` method was needed.

  *SCOPE+ `src/nonogram/admin/static/admin.css`* — the card's Touches list
  omitted it, but §11 is tokens-only styling and the new PuzzleTile state
  needs a rule. Two changes, both inside the tile's own block: a `.tile-flag`
  group (warning border, the flag sentence, the override row), and
  `.puzzle-tile:has(input:checked)` narrowed to
  `.puzzle-tile:has(.puzzle-checkbox:checked)` — a tile now holds a second
  checkbox, and "selected" is the pick, not the override.

  *SCOPE+ `meta/design/components.md`* (not committed, as meta/ never is) —
  PuzzleTile gained its "below floor" state and its Book-cell info row;
  StatBlock's "zero" state now names the finalise figure.

  *Tests.* `tests/test_book_select_floor_tiles.py` (new, 28 tests) carries
  AC-182 / AC-241 / AC-187 / AC-188 / AC-239 under the class names the ACs
  name, plus the unmeasurable-cell postures and a G-1 guard that swaps
  `book_cell_mm` out and watches both screens follow it.
  `tests/property/test_book_membership_floor.py` gained EC-021's *agreement*
  half: over 16 stored trims x 24 puzzles (384 per-puzzle agreements, both
  verdicts well past the vacuity floor) the tile's rendered figure, the
  store's refusal and the finalise count are asserted to be one number.
  Full suite: 4467 passed, 26 skipped, 1 failed — the known pre-existing
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`.

  *Owner renders* in `~/Documents/nonogram-reviews/CARD-123/` (HTML with the
  stylesheet and the grid previews inlined, plus PNGs from headless Chrome):
  `select-tab-below-floor` (4.61 mm flagged with the override control beside
  4.84 mm and 6.46 mm carrying nothing), `finalize-below-floor-count` (1) and
  `finalize-after-trim-change` (the same book on 6 x 9 in: 3, nothing
  re-added).

- [Handover] The tile is machine-readable as well as legible:
  `<div class="puzzle-tile" data-puzzle-id="…" data-book-cell-mm="4.61"
  data-below-floor="true">`, the cell attribute absent when no cell can be
  computed and the flag attribute absent when the puzzle clears the floor;
  the finalise figure is `<dd … data-below-floor-count="N">`. A later card
  that needs either figure should read those rather than re-measure.
  CARD-121's known limitation is unchanged and still fails safe: an override
  ticked on one selection tab and committed from another is not carried, and
  the puzzle is refused by name.

- [For the owner, outside this card] The finalise Summary's "Trim size" row
  still reads `book.metadata.size` (it renders e.g. "8x10 × 27.94 cm"), not
  the print columns the cell is measured on. Visible in the renders. That row
  is CARD-136's territory (Print setup storing the chosen trim), so it was
  left alone here.

- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/book_finalize.html, src/nonogram/admin/templates/book_select_puzzles.html, tests/property/test_book_membership_floor.py, tests/test_book_select_floor_tiles.py

- [Scope gate] in_scope — 1 file outside Touches (src/nonogram/admin/static/admin.css, declared SCOPE+), 1/6 = 17% < 25%; comp_spread 0 (all COMP-009); no poaching beyond the dispatcher's predicted CARD-136 edge.

- [Guard] structural guardrail G-4 clean: book_manager.py, book_arrange_puzzles.html, book_pdf_generator.py absent from the diff.

- [Build gate] PASSED (full, 196s) — 4467 passed, 26 skipped, 0 failed, exit 0; only the known pre-existing tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied deselected. Private --basetemp (sibling worktrees share pytest's tmp root).

- [Visual] no Makefile run target — no app-boot capture; the implementation's owner renders in ~/Documents/nonogram-reviews/CARD-123/ (select-tab-below-floor, finalize-below-floor-count, finalize-after-trim-change; .html + .png) serve as the rendered evidence. Orchestrator eyeballed both: 4.84 / 4.61 / 6.46 mm on the tiles, the 4.61 mm tile alone flagged with a text sentence + "Include below floor" checkbox, no wide-grid flag anywhere; finalise counts 3 after the 6x9 trim change and names each puzzle's mm.

- [Review 1/3] Score: 9.0 — crit: 0, imp: 0. Risk LOW, lane FAST. Five Minor findings (floor verdict stated twice; cell keyed by str() in the helper but by raw id in the template; an unreadable print spec degrades to N per-tile "not measurable" without naming the remedy; _clue_lines copied; the EC agreement half runs in-memory only). Step 8h: 44 rules checked, 17 holds / 27 unchecked (typed no_eligible_fact) / 0 violated.

- [Review sync] 1 report(s) -> meta/review/20260923T051957Z-CARD-123-cycle1.yml

- [8h spot-check] 2/3 sampled holds reproduced (ADR-0036/R2, ADR-0036/R1 — the latter with the A4 golden tripwire confirmed byte-identical by blob hash and green, 125 passed).

- [8h spot-check] x INV-006 not reproduced — the rule itself re-derives (no membership write, book_manager.py zero hunks, the rendered override_<id> field is the pre-existing one _submitted_overrides reads, CARD-121's cross-tab limitation still fails safe) but the verdict's cited evidence over-claims: "both halves ... memory and db" is honoured by one test. Only test_PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride carries @parametrize(mode=[memory, db]); the CARD-123 agreement half (tile_refusal_and_count_are_one_number), which is the half this card adds, runs in-memory only. Same gap the cycle-1 reviewer logged as Minor F-005.

- [AC/EC check] All criteria/constraints OK (evidence): AC-182 / AC-241 / AC-187 / AC-188 / AC-239 demonstrated by their named test classes (22 passed), EC-021 demonstrated in both halves (6 passed; 24 puzzles x 16 stored specs = 384 agreements, MIN_DECISIONS 300, anti-vacuity floors 40/40), G-1 demonstrated by the monkeypatched-book_cell_mm guard, G-2 by the no-wide-flag assertions plus a bounded grep, G-3 by absence over this diff, G-4 structurally by the changed-file list. No existing test was weakened, retargeted or deleted (git diff of tests/ removes 4 lines, all a delegation inside Corpus.below_floor).

- [AC/EC check] Noted, non-blocking: AC-241's fixture is 6.05 mm rather than the card's 6.0 mm, which is unreachable at 25x12 on the Book 1 profile (193.675 mm usable width over a whole number of cells gives 6.05 or 5.87). The test documents the substitution and asserts the criterion's substance. Worth an architect amendment to the AC's figure.

- [Fix 1] Minor round entered on the 8h spot-check failure: F-005 (parametrize EC-021's agreement half over both storage modes), F-002 (template keyed the cell lookup by raw id while the helper keys by str(id) - a wrong verdict wearing the fail-closed posture), F-001 (the floor verdict stated twice, so G-1's "one computation" held for the cell but not the decision). F-004 declined: CLAUDE.md mandates native reimplementation over a lateral import. F-003 declined: new UX behaviour, belongs on a follow-up card.

- [Fix 1] pre-gate PASSED — the three named tests exist and are green (9 tests, exit 0): tile_refusal_and_count_are_one_number (now parametrized memory/db), TestBookSelectTile_CellLookupIsKeyedLikeTheRouteFilesIt, TestBookSelectTile_TheFloorVerdictIsMadeOnce.

- [Fix 1] declarations: 0 updated, 0 confirmed, 3 none (all three fixes local — no bound, lifecycle, blast radius, error class or config meaning changed; the data-puzzle-id / data-book-cell-mm / data-below-floor / data-below-floor-count handover contract is unchanged in name, presence rule and value).

- [Build gate] PASSED (full, 199s) — 4475 passed (+8), 26 skipped, 0 failed, exit 0; same single known pre-existing e2e deselection, private --basetemp.

- [Scope gate] in_scope (cycle 2) — the fix round edited only app.py, book_select_puzzles.html and the two test files; the changed-file set against main is unchanged at 6, admin.css still the only SCOPE+ file, G-4 paths still absent.

- [Review 2/3] Score: 9.3 — crit: 0, imp: 0 (confirmation mode). All three fixed findings re-derived at full depth: F-005's db mode instrumented and proved genuinely DB-backed (3 sessions opened while rendering the route, 24 rows in sqlite, 0 books in the in-memory singleton), per-mode anti-vacuity figures 384 agreements / 186 flagged / 198 unflagged; F-002 reproduced as a REAL latent bug — the pre-fix template flagged a 6.05 mm UUID-id puzzle as below the floor and offered an override; F-001 confirmed, with the honest caveat that the ast guard is a forward regression guard, not a pre/post discriminator (its sibling template test is). No existing test weakened: 17 deleted lines are the replaced fixture body and [mode]-prefixed messages, no assertion removed.

- [Review 2/3] Step 8h: 44 rules checked, 13 holds / 31 unchecked / 0 violated. INV-006 and ADR-0036/R2 re-derived rather than carried, as required after the cycle-1 spot-check failure. INV-006's citation is now precise about storage modes and names the two route-level membership tests that remain memory-only instead of folding them in.

- [Review sync] 2 report(s) -> meta/review/ (cycle1, cycle2)

- [8h spot-check] 3/3 sampled holds reproduced (INV-006, CON-015, CON-016). INV-006's previously-failed citation now re-derives exactly: an independent skeptic instrumented the db parametrization itself (2704 sessions opened through the sqlite factory, app.book_manager a fresh DB-backed instance rather than the in-memory singleton, membership persisted in the books.puzzle_ids column read back with a plain sqlite3 connection outside SQLAlchemy) and collected the per-node storage-mode table, confirming the verdict is neither too broad nor too narrow. CON-015/CON-016: the fix round's DATABASE_URL/session_scope work is test-only monkeypatch — create_app's signature, the LOOPBACK_HOST constant, the 47 routes and the single before_request door are all byte-identical to the merge base.

- [8h spot-check] One recorded imprecision, non-gating: the INV-006 verdict says "app.py's only add call"; there are two (app.py:2685 and :3266), both pre-existing and both funnelling through BookManager, so the conclusion is unaffected.

- [8h spot-check] Noted by the skeptic, safe: F-001's set-membership refactor flips the failure direction for a MISSING key from flagged to unflagged. A genuinely unmeasurable cell still flags (_misses_the_floor(None) is True). A missing key is what F-002 eliminated, and the direction is safe regardless — unflagged means no override control is rendered, so the store refuses the puzzle. The store remains the only gate.

- [AC/EC check] All criteria/constraints ✓ (evidence, re-run against the post-fix working tree): AC-182 ✓ demonstrated (5 PASSED; the 30x25 grid with a 12-deep row gutter and 8-deep column gutter is BUILT, the tile sliced out of the real rendered route shows 4.61 mm + the flag in words + name="override_<id>", and the scraped field name is re-POSTed to prove it is the control that admits). AC-241 ✓ (4 PASSED; cell >= FLOOR_MM asserted so "no flag" is not vacuous). AC-187 ✓ (4 PASSED; 150 members and exactly 2 overrides asserted before the render). AC-188 ✓ (5 PASSED; the trim really rewritten on the stored row, re-rendered, 4.65 mm, and a companion test with NO stored override still counting 1). AC-239 ✓ (4 PASSED; a shallower band on the same 30-wide extent clears the floor, so the flag is attributable to the band). EC-021 ✓ both halves, both parametrizations (7 PASSED; 384 agreements vs MIN_DECISIONS 300, 186 flagged / 198 unflagged vs MIN_OF_EACH_VERDICT 40, cells spanning 2.12-7.50 mm; an independent mutation probe shifting book_cell_mm by +0.5 mm turned BOTH parametrizations red, so the test bites). G-1 ✓, G-2 ✓, G-3 ✓, G-4 ✓ structural against the merge base 17c647b (a two-dot diff is misleading here because CARD-117 has landed on main).

- [AC/EC check] Shared-fixture rewrite checked line by line, where a silent weakening would hide: the old admin_app body moved verbatim into panel_in_mode(monkeypatch, None); no removed `def test`, `class Test` or `assert` line anywhere in tests/; assert counts rose 64->78 and 28->29; the only edits to existing assertions are [mode] prefixes in message strings. 112 coupled pre-existing tests (test_book_floor.py, test_book_select_tabs.py) green against the changed app.py and template.

- [Docs] forge:readme skipped with reason. Of the changed directories only tests/ has a README, and it is a stale "Wave 1" document whose ## Test Files index already omits ~20 later files (test_book_floor.py, test_book_select_tabs.py among them); adding this card's one file to that index would make it more misleading, and rewriting it is not this card's scope. src/nonogram/admin, its templates/ and static/, and tests/property have no README, and creating one in the wave's hottest directory (CARD-117/126/136 all editing there) would generate merge conflicts for no acceptance value.

- [CARD-123, 2026-09-23] **Review cycle 1 fix round** (9.0, no critical/important;
  three Minor findings, two declined). Nothing the owner sees changed — every
  element, attribute and word of the tile and of the finalise summary is
  unchanged (the tab's HTML differs only by the blank line a third `{% set %}`
  leaves before each tile), so the renders in
  `~/Documents/nonogram-reviews/CARD-123/` still stand and were left alone.

  *F-005 — the agreement half ran in one storage mode.* EC-021's membership
  half is parametrised `["memory", "db"]`; the agreement half took the
  in-memory-only `admin_app` fixture, so the INV-006 verdict claimed more than
  the test established. The fixture is now a `panel_in_mode(monkeypatch,
  factory)` context manager: `create_app` resolves its session factory fresh
  per call, so setting `DATABASE_URL` and pointing `nonogram.db.session_scope`
  at the test's own SQLite scope yields a genuinely DB-backed panel — store,
  book manager and routes — with no server and no Postgres. It asserts
  `_session_factory is not None` so the db half cannot silently be the memory
  half run twice. `admin_app` is that context manager with `factory=None`;
  the new `admin_panel` fixture is parametrised over both and yields
  `(mode, app, factory)`. Corpus size, `MIN_DECISIONS` and the
  `flagged_seen`/`unflagged_seen` anti-vacuity guards are unchanged (so both
  modes now clear them independently), and every message carries `[mode]`.

  *F-002 — cell looked up by raw id, keyed by `str(id)`.* `_book_cells` files
  every cell under `str(record["id"])` while the template did
  `book_cells.get(puzzle.id)`. Both modes hand out string ids today, so it
  agreed by accident; a `uuid.UUID` or int id would have missed silently and
  rendered "not measurable" plus a below-floor flag — a wrong verdict wearing
  the fail-closed posture, and the one shape the property test cannot catch
  (its corpus is string-keyed too). The template now keys
  `{% set puzzle_key = puzzle.id|string %}` once and uses it for both lookups.

  *F-001 — the floor verdict was stated twice.* `_misses_the_floor` in the
  route and an inline `cell_mm is none or cell_mm < floor_mm` in the markup.
  A new `_below_floor_ids(cells)` turns a cell mapping into the set of ids
  that miss the floor; the selection route passes it as `below_floor_ids` and
  the finalise route filters on it, so `FLOOR_MM` is now compared in exactly
  one function on the admin side and the template is handed a verdict rather
  than making one. `_misses_the_floor` keeps its fan-in through that helper.

  *Contract untouched.* `data-puzzle-id`, `data-book-cell-mm`,
  `data-below-floor` and `data-below-floor-count` are unchanged in name,
  presence rule and value; no bound, lifecycle, blast radius, error class or
  config field moved. The new `below_floor_ids` is a template context key, not
  a public boundary.

  *Tests.* `tests/test_book_select_floor_tiles.py` gained
  `TestBookSelectTile_CellLookupIsKeyedLikeTheRouteFilesIt` (a record carrying
  a `uuid.UUID` id — its cell is found, a 6.05 mm puzzle is not flagged, a
  4.61 mm one still is, and the markup's key is pinned) and
  `TestBookSelectTile_TheFloorVerdictIsMadeOnce` (an `ast` walk of `app.py`
  asserting `FLOOR_MM` is compared in exactly one function, `_misses_the_floor`;
  the template makes no comparison of its own; and both screens follow the one
  computation). All five structural/behavioural guards were watched to fail
  against the pre-fix template. 35 in that file, 154 across the four files the
  fix round ran.

  *Declined, on purpose.* F-004 (`_clue_lines` copied rather than imported
  from `book_manager`) is what CLAUDE.md mandates — reimplement natively
  rather than import laterally, enforced by the structural guard in
  `tests/test_cli.py`. F-003 (an unreadable print spec renders N per-tile
  "not measurable" messages without naming the remedy) is real but is new UX
  behaviour — a banner plus suppressing the per-tile override in that state —
  not a correction to what this card built; it belongs on a follow-up card.

- [Handover] The tile is machine-readable as well as legible:
  `<div class="puzzle-tile" data-puzzle-id="…" data-book-cell-mm="4.61"
  data-below-floor="true">`, the cell attribute absent when no cell can be
  computed and the flag attribute absent when the puzzle clears the floor;
  the finalise figure is `<dd … data-below-floor-count="N">`. A later card
  that needs either figure should read those rather than re-measure.
  CARD-121's known limitation is unchanged and still fails safe: an override
  ticked on one selection tab and committed from another is not carried, and
  the puzzle is refused by name.

- [For the owner, outside this card] The finalise Summary's "Trim size" row
  still reads `book.metadata.size` (it renders e.g. "8x10 × 27.94 cm"), not
  the print columns the cell is measured on. Visible in the renders. That row
  is CARD-136's territory (Print setup storing the chosen trim), so it was
  left alone here.

- [Commit] SUCCESS. Two commits on card/123-tile-cell-and-floor-count: 103ca6e (implementation) and 4f984b7 (review fix round). Staged with explicit pathspecs; nothing under meta/ committed, no nonogram_admin.db, no egg-info. The worktree is clean apart from meta/design/components.md, the card file and the two review YAMLs, all of which are orchestrator/worktree artefacts by design.

- [Golden tripwire] CARD-113's A4 golden is untouched and green — tests/test_export_a4_golden.py, tests/property/test_cli_exports_byte_identity.py and tests/fixtures/a4_golden/** are byte-identical to the merge base by blob hash and were never regenerated (125 passed under the named check).

- [Handover] For CARD-136, which owns Print setup and also edits book_finalize.html: the finalise Summary's "Trim size" row still reads book.metadata.size and renders nonsense like "8x10 x 27.94 cm" — it does not read the print columns the floor figure is measured on. Visible in ~/Documents/nonogram-reviews/CARD-123/finalize-*.png. Left alone here deliberately.

- [Handover] Follow-up wanted, no card yet: an unreadable stored print spec degrades into N per-tile "Cell cannot be measured on this book" messages, each with an override control that cannot succeed, and never names the remedy (re-save Print setup). Fails closed in both directions, so it is a UX gap rather than a correctness one.

- [For the architect] AC-241 states 6.0 mm, which is unreachable at 25x12 on the Book 1 profile: 193.675 mm of usable width over a whole number of cells gives 6.05 or 5.87, never 6.00. The test uses 6.05 mm and documents the substitution. Worth amending the AC's figure so criterion and test read identically.

- [Done] rebased onto main 86e50ee (after CARD-117), full suite on the rebased tree with a private --basetemp: only the pre-existing e2e failure. Merged 8b7b78e (--no-ff). Deferral scan: 0 hits. SCOPE+ admin.css (tokens-only rule for the new tile state). AC-241 figure queued to the architect; finalise trim-row gap handed to CARD-136.
