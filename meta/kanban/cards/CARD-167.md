# CARD-167: The guide page becomes "How to Solve Nonograms" with a worked example, still on one page

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/167-guide-page-how-to-solve
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (owner decision on IDEA-071; FR-041 AC-324..AC-326)
**Idea:** IDEA-071
**Wave:** 32
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_guide_page.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-10-04T07:04:19Z
**Closed:** 2026-10-04T09:07:40Z
**Actual:** 0.3d
**Merge commit:** e77df9b
**Blocked by:** —

## What to implement

The book's guide page (interior page 1, `BookPDFGenerator.create_guide_page`)
is titled "How to Use This Book". It prints a puzzle-count breakdown and three
lines ending "Have fun!": an orientation stub. Owner decision (2026-10-04):

1. Retitle it **"How to Solve Nonograms"**.
2. Add a **short worked example** on the same page: one line (row or column)
   with its clue, shown solved step by step from the clue to the finished line.
   For example: clue "3 1" on a 6-cell line, then the overlap that must be
   filled, then the gap, then the finished line. Draw it with the book's own
   cell and rule styles, so it looks like the puzzles. Keep the existing
   count breakdown if it still fits.
3. It **stays one page**. Interior page count and parity are unchanged (FR-043:
   guide page = right-hand page 1). All text holds CON-020's 10 pt floor.

The full 1–2 page tutorial the owner's design doc describes is NOT this card.
It waits for the page layout to be final and gets its own requirement.

## Acceptance criteria

_Verbatim from FR-041 (amended 2026-10-04)._

- **AC-324** (happy): *Given* a Book 1 profile book with 3 easy 20x20 puzzles, *when* the book is exported and the interior PDF's page 1 (the guide page, FR-043) is read, *then* its title reads "How to Solve Nonograms" and the old title "How to Use This Book" appears nowhere on it.
  *test: TestGuidePage_TitledHowToSolveNonograms*
- **AC-325** (happy): *Given* the book of AC-324, *when* the guide page is read, *then* the same single page carries a worked example (one line with its clue, shown solved step by step from that clue to the finished line), with no part of the example continuing onto interior page 2, and its text holds CON-020's 10 pt floor.
  *test: TestGuidePage_CarriesAWorkedExampleOnOnePage*
- **AC-326** (boundary): *Given* one Book 1 profile book exported with the "How to Use This Book" guide page and again with the "How to Solve Nonograms" guide page carrying its worked example, *when* the two interior PDFs are compared, *then* both hold the same number of pages, the guide page is exactly one page (interior page 1) in each, and every later page keeps its parity (FR-043).
  *test: TestGuidePage_WorkedExampleLeavesPageCountAndParityUnchanged*

## Guardrails

- G-1: The CON-019 golden A4 tripwire stays green. No change to CLI/web exports or puzzle-page geometry.
- G-2: Every interior page except the guide page is byte-for-byte unchanged in content (puzzle pages, dividers, answer key). Compare against main.
- G-3: The page plan's counts (`interior_stream` page count, the `_as_planned` tripwire) are unchanged. CARD-129's KDP gutter check and CARD-153's Finalise counts must not move.
- G-4: The interior stays black-and-white (CARD-147, DeviceGray). The worked example adds no colour.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-167` (53 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit… (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when… (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn;… (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on… (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp <… (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the… (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a… (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no… (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the… (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle… (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the… (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin… (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm… (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution. A type size is a physical measure - points or millimetres converted… (check: review-lens)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No… (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode)… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031,… (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's… (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5… (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is… (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns… (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the… (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-041 (AC-324..AC-326, amended 2026-10-04); FR-043 (guide page = interior page 1, parity); CON-020 (10 pt floor)
- **ADR:** ADR-0036/R1 (default PageSpec byte-identical), ADR-0037 (book page typography)
- **Components:** COMP-007, COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Output:** interior PDF page 1
- **Renders:** ~/Documents/nonogram-reviews/CARD-167/ (the guide page at Book 1 trim, plus a 6×9 trim; the owner checks it on paper alongside the proof measurements)

## Worktree notes

- [Origin] Roadmap wave 1 (IDEA-071), owner decision 2026-10-04: small fix now, full tutorial later.
- [Env] forge 2026.8.17
- [Implementation 2026-10-04] Commits `8e2c4bd` (feature + tests) and `3d0f2bf` (new pixel baseline, its own commit as CARD-149/146/147 did).
  `create_guide_page` is retitled "How to Solve Nonograms" (`GUIDE_TITLE`) and draws the worked example `WORKED_EXAMPLE_STEPS`:
  clue 3 1 on 6 squares — 1. the clue (blank line), 2. overlap (squares 2,3 filled), 3. gap (the crossing column empties
  square 1, so the 3 is 2-4 and square 5 is crossed), 4. solved (square 6 filled). Step 3 takes one fact from the crossing
  column: a line determined by its own clue alone has zero slack and so no overlap step to show; the caption says so.
  Each step's line comes from `example_line_layout(spec)` = `compute_layout(((3,1),), ((0,),)*6, guide page spec)` (placeholder
  column clues, column gutter cropped), stroked by the module's existing `_stroke_drawing`/`_write_clues` (the two-up page's
  reimplementation of png's private helpers) — so pitch 7.5 mm, thin 3 px (>= 0.25 mm), heavy 6 px, frame and clue face are the
  book's own. Filled squares in INK; crossed squares are an X at the layout's thin rule (the only new mark; no new stroke weight).
  Text is wrapped to the usable measure (`wrap_words`). Three forms, first that fits above the bottom margin: full (intro,
  counts, example with captions, closing) -> example with captions only -> example with short labels. Book 1 and 6x9 get the
  full form; the 10 cm minimum trim gets the labels form; the full form also pushes to the captions-only form at CARD-149's
  hypothetical 600 DPI. The title shrinks a pixel at a time only when wider than the measure (10 cm trim: 1042 px > 919 px), never
  below body size. Font sizes at Book 1 are unchanged (92/46 px), so `MACHINE_FACE_SIZES` and the font fingerprint are unchanged.
- [Tests] tests/test_book_guide_page.py (15 tests), all read off the exported PDF's pixels: AC-324 finds the new title by FFT
  template search (and, as a control, finds the OLD title on the old-page export); AC-325 reads 4 ruled lines, their clue digits
  (matched against Pillow's default-face digits), each square's state, checks step 2 = intersection of all placements of 3 1
  (test's own brute force), monotone steps, unique finished line, rule widths (thin >= 0.25 mm, heavy = 2x thin, same widths as the
  20x20 puzzle page), every mark inside CON-018's frame, every type line and clue digit >= 10 pt, 6x9 trim likewise, page 2
  identical to the old export's page 2. AC-326 exports the same book with a test-local transcription of the old guide page
  (`old_guide_page`, monkeypatched) and compares: equal page counts, page 1 = each export's own guide page, pages 2..N
  digest-identical, puzzle pages' observed centre offset matches odd/even parity.
  Premise recorded in the floor test: each line is measured top-to-baseline, so every copy line must reach cap height; step 2 was
  reworded because "way." wrapped onto its own x-height-only line at Book 1.
- SCOPE+ tests/test_book_guide_page_type.py — CARD-149's type tests: TITLE_AS_IT_STANDS follows the retitle; `type_bands` excludes
  bands with a ruled row (> 300 px unbroken ink: the example's lines) so the same 11/22 pt and 1.4x leading assertions still measure
  every line of type; the "no two lines touch" check now runs over ALL ink bands (stronger). No floor/geometry assertion weakened;
  the 48-case trim corpus and min-trim fit tests unchanged and green.
- SCOPE+ tests/test_book_pdf_memory.py — page-kind test: the guide page now carries filled squares, so the "no solid ink blocks"
  negative check runs over pages 2-8 (page 1 is still positively identified as the generator's guide page).
- SCOPE+ tests/helpers/book_corpus.py — BASELINE_FIXTURE repointed to the new tests/fixtures/book_baseline_card167.json (chain
  bullet added). Fingerprint reproduced first; compared all 11 pages vs CARD-147: only page 1 moved (G-2 evidence);
  interior_bytes 2,273,541 -> 2,436,675.
- SCOPE+ tests/test_book_pdf_ink_mode.py — colour-interior test compares pages 2-11 against CARD-146 as before and page 1 against
  card167's recording; colour length read from card167's `colour_interior_bytes` (2,845,318; CARD-146 had 2,680,175).
- [Guardrails] G-1: no export/layout code touched; CON-019/layout tests in the full suite. G-2: baseline comparison above. G-3: no
  page-plan change; an extra page after the guide trips `_as_planned` (mutation M10). G-4: drawn in INK on white, written DeviceGray
  as before (ink-mode tests green).
- [Mutations] each applied to book_pdf_generator.py, targeted tests run, reverted:
  M1 title back to old -> AC-324 tests + CARD-149 title box fail; M2 example dropped -> 3 AC-325 tests (+600 DPI test) fail;
  M3 body 9 pt -> 10 pt floor tests fail; M4 no fallback forms -> CARD-149 min-trim + corpus fit fail; M5 overlap wrong ({1,2,3})
  -> steps test fails; M6 title never shrinks -> min-trim fit fails; M7 clue font 30 px (7.2 pt) -> clue-digit floor fails;
  M8 crosses not drawn -> steps test fails; M9 heavy rules thinned -> rule-style test fails (it survived first; that test was added
  because of it); M10 extra page after guide -> AC-326 tests error on the `_as_planned` RuntimeError; M11 strips pasted off-page ->
  4 AC-325 tests fail.
- [Renders] ~/Documents/nonogram-reviews/CARD-167/guide-book1-8.5x11.png, guide-6x9.png, guide-min-10cm.png (+ *-with-usable-frame.png,
  red rectangle = usable area). Looked at all three: Book 1 — full form in the top ~55% of the page, captions mostly one line,
  four example lines left-aligned at 7.5 mm squares, lower half empty. 6x9 — full form, captions wrap to two lines, ends ~3/4 down
  the frame. 10 cm — title shrunk to the measure, four lines with short labels, fits with the last line ~20 px above the bottom margin.
  All ink inside the frame; X marks and the heavy 5th rule read like the puzzles. Script (not committed):
  scratchpad card167/card167_render.py.
- [Follow-up, not done — out of scope] src/nonogram/admin/templates/book_finalize.html's guide preview still reads "How to use this
  book" with the old instruction list; the CARD-149 type-test module docstring's headroom numbers describe the old text.
- [Full suite] 2026-10-04, under the shared lock, on 3d0f2bf: 6049 passed, 9 skipped, 2 failed — exactly the two known baseline failures (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders).
- [Scope] src/nonogram/admin/book_pdf_generator.py, tests/fixtures/book_baseline_card167.json, tests/helpers/book_corpus.py, tests/test_book_guide_page.py, tests/test_book_guide_page_type.py, tests/test_book_pdf_ink_mode.py, tests/test_book_pdf_memory.py
- [Eyeball] orchestrator viewed guide-book1-8.5x11.png and guide-6x9.png: retitled page, intro, 150/50/50/50 counts, four 6-square example lines (clue 3 1 in the puzzles' clue box, thin inner rules, heavy frame, X crosses), closing line; all inside the margins, Book 1 ends ~55% down, 6x9 ~80% down; example logic checked by hand (overlap 2-3; with square 1 empty: 2-4 filled, 5 gap, 6 filled). Note: adjacent filled squares merge into one black block (no rule between them), same as solid fills.
- [Scope gate] ⚠ grown: 5 of 7 files outside Touches (tests/test_book_guide_page_type.py, tests/test_book_pdf_memory.py, tests/test_book_pdf_ink_mode.py, tests/helpers/book_corpus.py, tests/fixtures/book_baseline_card167.json — all test-side, each recorded SCOPE+); no component spread beyond COMP-009, no sibling poached, no structural guardrail
- [Build gate] PASSED (full, 9m21s; 6049 passed, 9 skipped, 2 failed = exactly the two known baseline failures on main)
- [Baseline] coordinator 2026-10-04: main at 4899076 (CARD-164, CARD-168 merged) is fully green; gate now requires zero failures. Branch not rebased (coordinator rebases at done); the two ex-baseline tests are fixed by CARD-164 on main, so they will be checked on a throwaway merge of main+branch.
- [Review 1/3] Score: 8.0 — crit: 0, imp: 1 (before adversarial verification)
- [Review sync] 1 report(s) → meta/review/
- [Adversarial] F-001 CONFIRMED (narrowed) — new subset assertion at test_book_guide_page_type.py:652 is vacuous and the note's '(stronger)' claim is false; main's old assertion was equally vacuous, so no guard weakened vs main, but the comment claims protection nothing provides
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Fix 1] pre-gate: 4 named tests (5 cases) green; FIXED F-001/F-002/F-003/F-004/F-006, SKIPPED F-005 (owner question)
- [Fix 1] declarations: 0 updated, 0 confirmed, 2 none; 3 doc (module docstring, test docstrings, card note correction)
- [Correction, Fix 1] The SCOPE+ note above calling the type module's "no two lines touch" check "(stronger)" was false: its
  `set(guide_bands) <= set(every_band)` could never fail (type_bands filters ink_bands), and neither could the neighbour loop
  (ink_bands only splits at a blank row) — nor could main's `len(guide_bands) == len(ink_bands(page))`. Replaced by real checks on
  the four-puzzle Book 1 page: exactly 14 lines of type, exactly 4 drawn bands, all four the same height.
- [Fix 1] review cycle 1. F-001: test_no_two_lines_ink_runs_together pins 14 type lines / 4 drawings / equal drawing heights,
  docstring says only that. F-002: module docstring now says the module trims the example layout to one row, draws fills/crosses
  and places it. F-003: new parametrized test_the_10cm_trim_holds_10pt_in_its_fallback_forms (10x10 cm = short-label form, 5 type
  lines; 10x14 cm = captions-only form, 11 type lines) measures type and clue digits >= 10 pt; the title-shrink clamp (never below
  body size) is still NOT covered — no stored trim reaches it. F-004: clue-digit floor test asserts 4 lines x 2 glyphs; 6x9 test adds
  clue-digit floor and rule widths. F-006: TextFitsTheUsableFrame docstring rewritten for the wrapped three-form page. F-005
  (Step 3 imports a crossing-column fact) left to the owner, example unchanged. No pixel change (docstring only in
  book_pdf_generator.py). Mutations (each applied, run, restored by rewriting the file; byte-compared to the saved original):
  caption pasted half a leading up onto its drawing -> 12 == 14 fails; last caption dropped -> 13 == 14; Easy/Medium lines
  touching -> 13 == 14; same caption mutation with the count check disabled -> height check fails ({94,125,126}); fallback forms'
  type at 30 px -> both 10 cm cases fail, Book 1 floor test still passes; narrow-trim example clues at 30 px -> 10 cm cases fail at
  6.71 pt; clues not drawn -> clue floor test + 6x9 test fail; example vertical rules all heavy -> 6x9 test fails on widths.
- [Observed, not fixed — out of scope] the cap-height measurement's premise (every line reaches cap height) fails on some trims
  not under test: at 11x17 cm the step-2 caption wraps "way." onto its own line, and at 10x25 cm a wrapped line has only "t"
  ascenders; both measure 8.36 pt although the body is set at 11 pt. A copy/wrap question, not a CON-020 breach.
- [Build gate] PASSED (full, 9m13s; 6051 passed, 9 skipped, 2 failed = only the two tests CARD-164 fixed on main, absent from this un-rebased branch; to be confirmed on a main+branch merge before commit)
- [Review 2/3] Score: 9.0 — crit: 0, imp: 0
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Score: 9.0 ✓ threshold reached + no critical/important; Step 8h covered all 53 card rule ids (11 ✓, 42 ⚠ no_eligible_fact, 0 ✗); 8f mutation: 7 mutants, 3 killed, 4 survived (title clamp — declared uncovered; wrap '>'→'>=' and fit '<='→'<' — boundary-equivalent; no gap after drawing — Minor F-103)
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0037/R2, CON-020, INV-013) — caveats: pure-black is shown by code (INK=(0,0,0)) and a pixel probe, not by a test; clue digits hold 13.2 pt via the mm-capped pitch, with no explicit point floor
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-324 ✓ demonstrated — TestGuidePage_TitledHowToSolveNonograms 3/3 PASSED (new title found on page 1 by pixel search; old title found 0 times at 22 pt and 11 pt; control finds it on the old page)
  AC-325 ✓ demonstrated — TestGuidePage_CarriesAWorkedExampleOnOnePage 10/10 PASSED (4 ruled 6-square lines, clue 31, monotone steps from empty via overlap to the unique finished line, page 2 unchanged, all marks in frame, type and clue digits >= 10 pt at Book 1, 6x9, 10 cm fallbacks)
  AC-326 ✓ demonstrated — TestGuidePage_WorkedExampleLeavesPageCountAndParityUnchanged 3/3 PASSED (equal page count, page 1 = own guide page, pages 2..N identical, puzzle-page offsets match parity, 3 puzzles checked)
  G-1 ✓ demonstrated — test_export_a4_golden.py, test_layout_page_spec.py, test_book_finalise_gutter.py 252 passed; no export/cli/web file in the diff
  G-2 ✓ demonstrated — TestBookPdfMemory_PagesAreUnchanged 5/5 PASSED; card147 vs card167 baseline differ only at page 1 (font fingerprint unchanged)
  G-3 ✓ demonstrated — 0 diff lines touch interior_stream/_as_planned; gutter/Finalise, interior-cover, interior property and same-plan tests green, unchanged vs main
  G-4 ✓ demonstrated — test_book_pdf_ink_mode.py all PASSED (DeviceGray, one channel); rendered guide page has 0 pixels with R!=G!=B
- [Docs] forge:readme over changed dirs: src/nonogram/admin, tests/helpers, tests/fixtures have no README (per-directory README convention is a pending owner decision — none created); tests/README.md does not list book test files — structure/purpose unchanged, skipped
- [Build gate] merge check: main 4899076 + this branch (incl. Fix 1) merged in a throwaway detached worktree — full suite exit 0: 6057 passed, 9 skipped, 0 failed (9m28s); throwaway worktree removed
- [Commit] success commit e8d4731 on card/167-guide-page-how-to-solve (branch: 8e2c4bd, 3d0f2bf, e8d4731; 7 files, +1152/−79 vs 7e57b1c). Card stays in review until done merges it.
- [Merged] 2026-10-04 — e77df9b into main (--no-ff). Rebased onto 70b24f1 (CARD-164/165/168) cleanly; merge gate: full suite under the lock, exit 0 — 6069 passed, 0 failed. Deferral scan: 2 incidental hits (a test comment's 'placeholders', the baseline fixture's warning). Owner questions raised: guide-page empty space (Book 1 content ends ~55% down), F-005 (the '3 1' example needs one crossing-column fact). Backlog: Finalise's guide preview still shows the old text; F-101/F-103 minors; divider/cover type set in px not pt.
