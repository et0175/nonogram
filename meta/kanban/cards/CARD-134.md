# CARD-134: The answer key in the book PDF — puzzle-number order, 6-up / 4-up pages, "Puzzle N — Title" captions

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/134-book-answer-key
**Worktree:** ../PythonProject4-CARD-134
**Source:** meta/architecture/handoff.md#increment-15 (COMP-009 half of FR-042, added by the 2026-09-22 (c) delta)
**Idea:** —
**Wave:** 25
**Depends on:** CARD-117, CARD-133
**Touches:** src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_answer_key.py, tests/property/test_book_answer_key.py
**Review score:** —
**Started:** 2026-09-23
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Today `BookPDFGenerator` appends one full answer page per puzzle, clues included, after
a "SOLUTIONS" divider. A 150-puzzle book therefore passes 300 pages. FR-042 (owner
decision BK-8) packs the answer key instead. This card owns the walk and the captions.
CARD-133 owns the tile geometry and drawing (ADR-0036/R2).

1. **`admin/book_answer_key.py` — the packing walk, a pure function.**
   `pack_answer_pages(answers) -> list[AnswerPage]`. `answers` holds each puzzle's
   `(number, width, height, level)` in **puzzle-number order** (INV-011), `level` being
   the puzzle's tier. It walks them in order:
   - a page's capacity is **6** while every answer on it is at most 20 on its longest
     side, and **4** once it holds one longer than 20;
   - the next answer goes on the current page when the page, **with it**, stays within
     its capacity. Otherwise it starts a new page. So 5 small answers followed by a
     25×25 close a 6-up page of 5 (AC-263), and 3 small answers + a 25×25 + a small
     one make a 4-up page of 4 followed by a new page (AC-264);
   - **each level starts a new answer page** (decided 2026-09-22 (d), FR-042 amended):
     an answer whose level differs from the current page's starts a new page even when
     the page has room (AC-290). No page holds two levels (INV-011 amended). The first
     page of each level is marked `heading = level name` ("Easy", "Medium", "Hard");
     later pages of the level carry none (AC-291);
   - every answer appears exactly once, and the page count lies between
     `ceil(n / 6)` and `ceil(n / 4) + (L − 1)` for L non-empty levels (EC-030
     amended — at most 2 pages more than before).
2. **Captions.** Each answer is captioned **"Puzzle N — Title"** (an em dash). N is
   the puzzle's number in the book, the same N the puzzle page's band shows
   (CARD-117). Title is the puzzle's **custom book title** (`puzzle_titles`, set on the
   arrangement step) when one is set, and otherwise the puzzle's name. This is the
   **only** place the title prints (ADR-0037/R1). The owner confirmed this rule on
   2026-09-22 (d): the per-book title set in Arrangement, else the puzzle's name.
3. **Generator.** Replace the one-answer-page-per-puzzle loop in
   `book_pdf_generator.py`. Build the pages from `pack_answer_pages`, and draw each one
   with CARD-133's `render_answer_page(..., capacity, page_spec, heading)`, where
   `page_spec` is the book spec for that page's **interior** position (**mirrored
   margins**: pass that page's parity, counted from interior page 1, CARD-135) and
   `heading` is the page's level heading or None. CARD-133 reserves the heading line
   and applies the 5 mm answer-cell cap. The admin panel fits no cell and places no
   grid line (ADR-0036/R2).
   **SOLUTIONS divider** (decided 2026-09-22 (d)): keep today's "SOLUTIONS" page — one
   trim-size page carrying only that word — immediately after the last puzzle page and
   before the first answer page (AC-292). It is not a level divider and carries no
   heading, band or number.
4. **Page count.** The generator's page-count report (CARD-127) includes the
   answer-key pages and the SOLUTIONS divider. CARD-129's finalise gutter check reads
   that total, which is the interior's (AC-271 and AC-288 are CARD-129's). Report the
   answer-key page count separately too (divider not counted), for the Increment 15
   checkpoint.
5. **Decided 2026-09-22 (d)** (FR-042 `_meta.open_question` 1–3 closed by the owner):
   level headings sit at the top of each level's first answer page, which always starts
   a new page (this card); the SOLUTIONS divider stays (this card); answer cells are
   capped at 5 mm (CARD-133). CARD-128 prints the puzzle section in level order and
   asserts the three-level default plan end to end (AC-293).

## Acceptance criteria

- **AC-261** (INV-011) — given a Book 1 profile book of 12 easy 15x15 puzzles, numbered 1..12, when the book PDF is generated, then the answer key is 2 pages, the first holding answers 1-6 and the second answers 7-12, each in 2 columns x 3 rows read left to right, top to bottom.
  *test:* `TestBookAnswerKey_SixUpInPuzzleNumberOrder`
- **AC-263** (INV-011) — given a Book 1 profile book whose puzzles 1-5 are 15x15 and puzzle 6 is 25x25, when the book PDF is generated, then the first answer page is a 6-up page holding answers 1-5, and answer 6 starts the next page.
  *test:* `TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage`
- **AC-264** (INV-011) — given a Book 1 profile book whose puzzles 1-3 are 15x15, puzzle 4 is 25x25 and puzzle 5 is 15x15, when the book PDF is generated, then the first answer page is a 4-up page (2 x 2) holding answers 1-4, and answer 5 starts the next page.
  *test:* `TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20`
- **AC-266** (INV-011) — given a Book 1 profile book of 6 puzzles, puzzle 1 being 20 wide x 15 tall and puzzles 2-6 15x15, when the book PDF is generated, then the answer key is one 6-up page holding answers 1-6 — a longest side of exactly 20 keeps the page 6-up.
  *test:* `TestBookAnswerKey_LongestSideTwentyStaysSixUp`
- **AC-268** — given a book whose puzzle 7 is named "Snowflake" and has no custom book title, when the book PDF is generated, then answer 7's caption reads "Puzzle 7 — Snowflake".
  *test:* `TestBookAnswerKey_CaptionPuzzleNumberAndTitle`
- **AC-269** (reworded 2026-09-22 (d)) — given a book whose puzzle 7 is named "Snowflake" and was given the per-book title "Winter Star" in Arrangement, when the book PDF is generated, then answer 7's caption reads "Puzzle 7 — Winter Star".
  *test:* `TestBookAnswerKey_CaptionUsesCustomBookTitle`
- **AC-270** (INV-011) — given a Book 1 profile book of 150 puzzles — the default plan's count and BK-8's 90 / 60 size split — all of one tier, puzzles 1-90 at most 20 on the longest side and puzzles 91-150 longer, when the book PDF is generated, then the answer key is 30 answer pages (the SOLUTIONS divider not counted) — 15 six-up pages then 15 four-up pages — where one page per answer would take 150.
  *test:* `TestBookAnswerKey_DefaultPlanTakesThirtyPages`
- **AC-290** (INV-011, added 2026-09-22 (d)) — given a Book 1 profile book of 4 easy then 3 medium puzzles, all 15x15, numbered 1..7, when the book PDF is generated, then the answer key is 2 answer pages — answers 1-4 on the first and answers 5-7 on the second — the medium level starts a new page although the first had room for 2 more.
  *test:* `TestBookAnswerKey_EachLevelStartsNewAnswerPage`
- **AC-291** (added 2026-09-22 (d)) — given a Book 1 profile book of 8 easy puzzles then 1 medium puzzle, all 15x15, when its answer pages are read, then the first answer page carries the heading "Easy" above its tiles, the second answer page (answers 7-8) carries no heading, and the third carries the heading "Medium".
  *test:* `TestBookAnswerKey_HeadingOnlyOnLevelFirstPage`
- **AC-292** (added 2026-09-22 (d)) — given a Book 1 profile book of 3 easy 15x15 puzzles, when the book PDF is generated, then the page immediately after the last puzzle page and immediately before the first answer page carries only the word "SOLUTIONS".
  *test:* `TestBookAnswerKey_SolutionsDividerPrecedesAnswerKey`

## Engineering constraints

- **EC-030** (consistency, INV-011; amended 2026-09-22 (d)) — For any book order of any length and any mix of puzzle sizes 10..30 and tiers, the answer key holds every member puzzle's answer exactly once in puzzle-number order; no page holds more than 6 answers, nor more than 4 when any answer on it is longer than 20; no page holds answers of two levels; a page is closed only when the next answer would push it past its capacity or belongs to the next level; and the answer-key page count (the SOLUTIONS divider not counted) lies between ceil(n / 6) and ceil(n / 4) + (L - 1) for n answers over L non-empty levels — for every order, not only the measured examples.
  *test:* `PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook`

## Guardrails

- G-1: The admin panel decides only which answers go on which page, and the caption text. It fits no cell and places no tile or grid line itself (ADR-0036/R2). Do not edit `src/nonogram/export/**`: CARD-133's calls are consumed as delivered. If something is missing there, escalate.
- G-2: The picture title prints only in the answer key, never on a puzzle page (ADR-0037/R1). test: TestBookPdf_PuzzlePageCarriesNoPictureTitle, TestBookPdf_AnswerKeyCarriesPictureTitle (CARD-117) stay green.
- G-3: CLI and web A4 output stay byte-identical (CON-019). test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden, PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry.
- G-4: Answer pages are decided at PDF time, and nothing is stored (Increment 15 Rollback). Do not edit `src/nonogram/db/**`, `migrations/**` or `src/nonogram/admin/book_manager.py`.
- G-5: Do not edit `src/nonogram/admin/book_proof.py`, `src/nonogram/admin/app.py`, `src/nonogram/admin/templates/book_setup_print.html`, `src/nonogram/admin/templates/book_detail.html`, `src/nonogram/admin/templates/books_list.html` or `src/nonogram/admin/templates/_stepper.html`. They are owned by CARD-118 / CARD-130 this wave.
- G-6: Out of scope: solution hints (deferred, not Book 1). The puzzle section's level order and divider pages are CARD-128's.

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

- **FR:** FR-042 (AC-261, AC-263, AC-264, AC-266, AC-268..AC-270, AC-290..AC-292, EC-030); FR-041 (answer-key level headings)
- **NFR:** —
- **ADR:** ADR-0036, ADR-0037
- **Components:** COMP-009, COMP-007 (consumed)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

- [Handover from CARD-133, 2026-09-23] Call `from nonogram.export.layout import compute_answer_page_layout` -> (extents, capacity, page_spec, heading=None) -> AnswerPageLayout, and `from nonogram.export.png import render_answer_page` -> (answers, capacity, page_spec, heading=None) -> Image. Import from the submodules, not the package. extents/answers in fill order (left->right, top->bottom), 1..capacity, capacity in {4,6}, page_spec for THAT page's parity (its band_mm is ignored), same heading to both.
- [Handover from CARD-133 — CRITICAL] The 3.19 mm answer-cell floor is NOT enforced by the type: a 25x25 six-up returns 3.178 mm and a 30x30 six-up 2.648 mm with no error. Owning "six-up only while every answer on the page is <=20 on its longest side" (INV-011) is THIS card's job; re-check it, do not assume CARD-133 guarantees it.

- [Handover from CARD-117, 2026-09-23] A two-up page needs TWO bands on one sheet, but the export draws one band per render_pages call — that is a COMP-007 conversation, settle it with CARD-127 rather than working around it in the PDF layer.
