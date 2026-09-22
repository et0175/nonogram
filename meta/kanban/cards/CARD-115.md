# CARD-115: The book's PageSpec from its stored trim and margins, Book 1 profile as the fallback (and margin defaults)

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/115-book-page-spec-builder
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-13
**Idea:** —
**Wave:** 22
**Depends on:** CARD-114
**Touches:** src/nonogram/admin/book_page_spec.py, src/nonogram/admin/print_specs.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, src/nonogram/db/models.py, migrations/versions/011_book_margin_defaults.py, tests/test_book_page_spec.py
**Review score:** 8.5 (cycle 1/3)
**Started:** 2026-09-22T17:35:05Z
**Closed:** 2026-09-22T18:19:49Z
**Actual:** 0.1d
**Merge commit:** 9f15c55
**Blocked by:** —

## What to implement

COMP-009 builds the book's `PageSpec` (CARD-114) from its stored print specification.
Every later book card calls this builder: the PDF (CARD-116), the proof pages
(CARD-118), the floor tile/refusal/finalise count (CARD-121/123) and the two-up pairing
(CARD-127).

1. **`admin/book_page_spec.py`**
   - `BOOK1_PROFILE` holds CON-018's constants: trim 21.59 × 27.94 cm, gutter 1.27 cm,
     outside/top/bottom 0.95 cm, no bleed, and the 12 mm band (TERM-028).
   - `book_page_spec(book) -> PageSpec` reads `trim_width_cm`/`trim_height_cm` and
     `gutter_margin_cm`/`outside_margin_cm` from the stored book. An **empty or missing
     margin falls back to the profile**. Top and bottom have no column and always come
     from CON-018. The spec it returns is portrait-only, has the flat 7.5 mm cap
     (NFR-008) and the ADR-0037 stroke minimum.
   - **Page parity** (2026-09-22 (c), ADR-0036 clarification "Mirrored margins"):
     `book_page_spec(book, page_number)` returns the spec for that page's position.
     Page 1 of the **interior** PDF is right-hand (odd), so its gutter margin is on the
     left. Interior page 1 is the guide page: the cover is a separate file and is never
     numbered (2026-09-22 (d), FR-043, CARD-135). `page_number` is always the interior
     position the generator reports.
     An even page puts the gutter on the right. Parity changes only which side each
     margin sits on, never the usable size, so `book_cell_mm` (below) needs no page
     number: build it on either parity and it gives the same cell.
   - `book_cell_mm(spec, row_clues, column_clues) -> float` is the one call that
     returns a puzzle's cell on the book. It is a thin wrapper over
     `compute_layout(..., page_spec=spec)`: convert px to mm and nothing else. This is
     the "one computation" EC-021 relies on. **The admin never fits a cell itself**
     (ADR-0036/R2).
2. **Migration `011_book_margin_defaults.py`** (COMP-010) adds server defaults
   `gutter_margin_cm = '1.27'` and `outside_margin_cm = '0.95'`, with a working
   `downgrade`. Give `models.py` the same column defaults. **Do not backfill existing
   NULLs.** AC-178 requires an empty legacy row to keep working through the fallback,
   and the Rollback clause relies on old rows staying valid under the old code. Number
   the file with the next free revision at implementation time (CARD-120 is planned to
   take 010) and chain `down_revision` correctly.
3. **Book creation stores the profile** (AC-181). `BookManager.create_book`, and the
   `/book/create` route when the owner leaves the print fields empty, store the CON-018
   trim and margins. Do this in both storage modes (in-memory and DB; CARD-101/108
   precedent). Today's `print_specs.py` defaults must agree with `BOOK1_PROFILE`. Import
   the constant; never write the numbers twice.

## Acceptance criteria

- **AC-181** — given a new book created in the admin panel with no print-setup values entered, when its stored print specification is read, then it holds the CON-018 profile — trim 21.59 x 27.94 cm, gutter 1.27 cm, outside 0.95 cm.
  *test:* `TestBookCreate_StoresBook1PrintProfile`
- (builder half of AC-178, the PDF half is CARD-116) — given a book row whose `gutter_margin_cm` and `outside_margin_cm` are empty, when its PageSpec is built, then it equals the one built from the CON-018 margins, and `book_cell_mm` for a 30×30 with 9-deep gutters gives 4.97 mm (±0.05).
  *test:* `TestBookPageSpec_EmptyMarginsFallBackToBook1Profile`
- **AC-272** (FR-030, added 2026-09-22 (c)) — given a Book 1 profile book (gutter 1.27 cm, outside 0.95 cm), when the usable area of its interior page 3 (a right-hand page) is computed, then it spans 12.7 mm to 206.375 mm from the page's left trim edge — the gutter margin on the left.
  *test:* `TestBookPageSpec_OddPageGutterOnLeft`
- **AC-273** (FR-030, added 2026-09-22 (c)) — given the same Book 1 profile book, when the usable area of its interior page 4 (a left-hand page) is computed, then it spans 9.525 mm to 203.2 mm from the page's left trim edge — the gutter margin on the right.
  *test:* `TestBookPageSpec_EvenPageGutterOnRight`

## Guardrails

- G-1: The admin panel fits no cells and places no grid lines itself. `book_cell_mm` only converts `compute_layout`'s result (ADR-0036/R2).
- G-2: Do not edit `src/nonogram/export/**` (CARD-114's PageSpec, parity included, is used as delivered; CARD-125 and CARD-133 own `export/layout.py` this wave).
- G-3: Existing book rows keep valid values under the old code. The migration adds defaults only, has a downgrade, and backfills nothing (Increment 13 Rollback).
- G-4: Do not edit `src/nonogram/admin/templates/book_select_puzzles.html`. It is owned by CARD-122 this wave.

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

- **FR:** FR-030
- **NFR:** NFR-008
- **CON:** CON-018
- **ADR:** ADR-0036
- **Components:** COMP-009, COMP-010
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

- [Handover from CARD-114, 2026-09-22] The book cell is an exact fractional value: `book_cell_mm` must read `layout.page.cell_mm`, NOT convert `layout.cell` (that gives 4.57 mm instead of 4.61). Also pin here the 7.5 mm cap and a minimum margin; CARD-114 minors F-001 (np.float64 trim error names no field), F-003 (no upper bound on trim size) are yours to close if the spec builder validates trims.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

- [CARD-115 implementation, 2026-09-22]
  - `admin/book_page_spec.py` (new): `BOOK1_PROFILE` (CON-018, stated once in inches; derives the exact mm for PageSpec and the 2-decimal cm strings the `books` table stores), `book_page_spec(book, page_number=1)` (odd = gutter left, interior page 1 is right-hand; portrait-only, flat 7.5 mm cap, 0.25 mm thin-rule minimum, top/bottom always from the profile), `book_cell_mm(spec, rows, cols)` = `compute_layout(..., page_spec=spec).page.cell_mm` (handover acted on: exact 4.61 mm, not the px 4.57; raises on a parity-less spec). No fitting of its own (G-1).
  - Stored-form rule (design note): 0.375 in = 0.9525 cm is stored as "0.95"; a stored value equal to the profile's own storage form is read as the profile's exact value (9.525 mm), any other value as the cm it says. This is what makes AC-272/273 (206.375 / 9.525 mm) hold for a book storing "0.95", and makes empty margins and CON-018 margins the identical sheet (AC-178).
  - Validation in the builder, each error naming the column: non-numeric / NaN / inf / bool / non-scalar stored values; trims outside KDP 10..30 x 10..48 cm; side margin below `MIN_SIDE_MARGIN_MM` = 6.35 mm (KDP 0.25 in); margins leaving no usable width; `page_number` not an int >= 1. KDP trim bounds now live in book_page_spec and `PrintSpecValidator` aliases them (one statement).
  - **F-001 CLOSED** (in admin/, export/ untouched): a bad stored trim raises ValueError naming `trim_width_cm`/`trim_height_cm`; a NumPy scalar is read through `str()` and reaches PageSpec as a plain Python float. **F-003 CLOSED**: stored trims above 30 x 48 cm (and below 10 cm) are refused with the column named.
  - `print_specs.py`: defaults (trim and, new, gutter/outside) read from `BOOK1_PROFILE`; `create_spec` fills empty margins with the profile.
  - `book_manager.py`: `Book` dataclass gains the print columns (default None = empty = profile fallback); `create_book` stores `BOOK1_PROFILE.stored_columns()` in both modes; `_row_to_book` reads the columns.
  - `app.py` unchanged: `/book/create` has no print fields, so it stores the profile through `create_book` (route tested in both modes).
  - `db/models.py`: margins get `default` + `server_default` '1.27'/'0.95' (still nullable). Migration `011_book_margin_defaults.py` (down_revision '010'): server defaults only, no backfill, downgrade removes the defaults; tested up -> down -> up against a temp SQLite DB.
  - Tests: `tests/test_book_page_spec.py` (TestBookCreate_StoresBook1PrintProfile, TestBookPageSpec_EmptyMarginsFallBackToBook1Profile, TestBookPageSpec_OddPageGutterOnLeft, TestBookPageSpec_EvenPageGutterOnRight, TestBookPageSpec_FlatStandardCellCap, TestBookPageSpec_MinimumSideMargin, TestBookPageSpec_RefusesBadStoredTrimNamingTheColumn, TestBookCellMm_OnlyReadsComputeLayout, TestMigration011); `tests/property/test_book_page_spec.py` (PropertyTest_BookPageSpec_ParityMovesMarginsNeverUsableSize, PropertyTest_BookPageSpec_EmptyMarginsBuildTheCon018Sheet, PropertyTest_BookPageSpec_CellNeverAboveStandardCell; seeded, min counts asserted).
  - SCOPE+ tests/test_book_scaffolding.py — `test_spec_to_dict` pinned the old default `gutter_margin_cm is None`; now asserts the CON-018 margins (one assertion changed, one added).
  - Follow-up (not in this card's ACs, flagged for CARD-116/owner): the Print setup route (`setup_print`) still writes the chosen trim only into `book_metadata.size`, never into `trim_width_cm`/`trim_height_cm`, so `book_page_spec` sees the profile trim even after the owner picks another trim. Whoever owns Print setup persistence should write the columns.

- [Scope] migrations/versions/011_book_margin_defaults.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/print_specs.py, src/nonogram/db/models.py, tests/property/test_book_page_spec.py, tests/test_book_page_spec.py, tests/test_book_scaffolding.py

- [Build gate] PASSED (full, 153s; 4087 passed, 26 skipped, 1 deselected — known pre-existing e2e TestFlow2BatchImageUpload::test_size_configuration_applied)

- [Visual] not a UI card (no ## Design context, Skill python-pro); no Makefile run target — review runs static-only

- [Review 1/3] Score: 8.5 — crit: 0, imp: 1 (F-001 MIN_SIDE_MARGIN_MM refuses AC-179's stored 0.60 cm gutter)

- [Review 1/3] Step 8h: 44/44 rules given verdict lines (10 ✓ holds, 34 ⚠ unchecked no_eligible_fact, 0 ✗)

- [Review sync] 1 report(s) → meta/review/

- [Adversarial] F-001 (MIN_SIDE_MARGIN_MM vs AC-179's 0.60 cm gutter) REFUTED — FR-030 puts the gutter's own lower bound at 0.375 in = 9.525 mm, above the builder's 6.35 mm floor, so the floor refuses no gutter any requirement permits; the card's handover explicitly asked to pin a minimum margin; AC-179's test is CARD-129's (wave 27) and does not exist. Dropped from the count. What survives is a forward note for CARD-129: reconcile AC-179's illustrative 0.60 cm with the floor, in the file it owns.

- [Review 1/3] Score: 8.5 ✓ threshold reached + no critical/important (1 important refuted by adversarial verification)

- [8h spot-check] 3/3 sampled holds reproduced (ADR-0036/R1, ADR-0036/R2, ADR-0019/R1) — golden A4 tripwire + fixtures untouched and green, book_cell_mm verified arithmetic-free with the 'pixel cell' mutant killed, inward-import guard green and covering admin→export

- [AC/EC check] All criteria/constraints ✓ (evidence): AC-181 ✓ demonstrated — TestBookCreate_StoresBook1PrintProfile 7/7 (both storage modes + /book/create route, CON-018 dict equality on a fresh book/row); AC-178 (builder half) ✓ demonstrated — TestBookPageSpec_EmptyMarginsFallBackToBook1Profile 5/5, 30x30 nine-deep cell 4.966 mm (approx 4.97 +/-0.05), null/blank/missing and a real legacy NULL row all build the CON-018 sheet; AC-272 ✓ demonstrated — TestBookPageSpec_OddPageGutterOnLeft 3/3, page 3 spans 12.7 -> 206.375 mm, cross-checked on the placed page; AC-273 ✓ demonstrated — TestBookPageSpec_EvenPageGutterOnRight 8/8, page 4 spans 9.525 -> 203.2 mm; G-1 ✓ demonstrated — TestBookCellMm_OnlyReadsComputeLayout 3/3 + module read: no fitting in admin/, no existing test weakened; G-2 ✓ demonstrated — structural, no src/nonogram/export/** path in the changed-file set; G-3 ✓ demonstrated — TestMigration011 2/2 on a temp SQLite DB (no backfill, new rows defaulted, up->down->up, legacy rows still build a valid spec), 011 contains no UPDATE/execute; G-4 ✓ demonstrated — structural, book_select_puzzles.html not in the diff. Gate: PASS (28 passed, 0 failed).

- [Docs] no README in the directories this card touched (src/nonogram/admin, src/nonogram/db, migrations/versions — the repo keeps none there); tests/README.md is a wave-1 admin-suite guide with no file index, unchanged by one new module in an existing package. Skipped as current.

- [Commit] success commit 4c19d82 — the implementation agent committed its own work (code only, explicit pathspecs, nothing under meta/, no DB or egg-info); at the success gate /commit had an empty diff, so no second commit was made.

- [Done] main unchanged since branch base 631c0be; the card's full-suite gate (4087 passed) ran on this tree. Merged 9f15c55 (--no-ff). Deferral scan: 0 hits. Handover notes pushed to CARD-116 and CARD-129.
