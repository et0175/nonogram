# CARD-169: The Finalise screen's guide preview shows "How to Solve Nonograms" and its worked example, read from the generator

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/169-finalise-guide-preview
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (CARD-167 follow-up; IDEA-085, WSJF 9.0)
**Idea:** IDEA-085
**Wave:** 33
**Depends on:** —
**Touches:** src/nonogram/admin/templates/book_finalize.html, src/nonogram/admin/app.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/static/admin.css, tests/test_book_finalise_guide_preview.py (new)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (read from the code).** CARD-167 changed the printed guide
page. `BookPDFGenerator.create_guide_page` (src/nonogram/admin/book_pdf_generator.py)
now prints `GUIDE_TITLE` ("How to Solve Nonograms"), an intro paragraph, the
tier counts, and the worked example `WORKED_EXAMPLE_STEPS`: four `ExampleStep`s
(clue 3 1 on 6 squares), each with a `caption`, a short `label`, and the
`filled` / `crossed` square sets. It closes with "Every puzzle in this book has
exactly one solution. The answers are at the back of the book."

The Finalise screen did not follow. `src/nonogram/admin/templates/book_finalize.html`
(the "Guide page" card, lines ~46-70) still hard-codes:
- the heading "How to use this book";
- a "Difficulty levels" list (Easy / Medium / Hard counts);
- an "Instructions" list: "Fill in the grid based on the clues", "Check your
  work against the answer key", "Have fun!".

The Contents card (line ~78) also says "Guide page (instructions and
difficulty summary)". The preview no longer describes the page the owner is
about to upload.

**Target behaviour.** The preview mirrors the printed page's content, and
takes its text from the generator so the two cannot drift.

1. **One source of text.** The intro paragraph and the closing sentence are
   string literals inside `create_guide_page`'s `set_page`. Hoist them to
   module constants beside `GUIDE_TITLE` (e.g. `GUIDE_INTRO`, `GUIDE_CLOSING`).
   `create_guide_page` uses the constants. This is a pure refactor: the
   printed page's pixels must not change (G-1).
2. **The route passes the generator's content.** The Finalise view
   (`app.py`, the `/book/<book_id>/finalize` GET handler, context dict built
   at ~line 4457) adds the title, intro, steps and closing to the template
   context. Read them through the module at request time
   (`book_pdf_generator.GUIDE_TITLE`, not a name bound at import), so the
   preview always shows what the generator would print. COMP-009 may import
   its own generator: `app.py` already imports `BookPDFGenerator` and
   `tier_breakdown` from it (line ~105), and `tier_breakdown` is the
   precedent for "one helper feeds both the screen and the printed page".
3. **The template renders that content.** In the Guide page card:
   - heading = the title; then the intro;
   - the counts, as today (`puzzle_count`, `easy_count`, `medium_count`,
     `hard_count`; the same numbers the printed page gets);
   - "Worked example: the clue 3 1 on a row of 6 squares." — build this line
     from `WORKED_EXAMPLE_CLUE` / `WORKED_EXAMPLE_LENGTH`, as the generator
     should too if it is hoisted (it is a literal today; hoisting it is in
     scope under the same pixel guardrail);
   - each step's full `caption`, with a small 6-square strip under it: one
     cell per square, marked filled / crossed / blank from that step's sets.
     Plain HTML + CSS (ADR-0038/R1: no framework, no build step), drawn with
     existing tokens; give each cell a stable class or `data-state` so a test
     can read it;
   - the closing sentence.
   No "Have fun!", no "Check your work against the answer key" list.
4. **Contents card.** Change "Guide page (instructions and difficulty
   summary)" to describe the new page, e.g. "Guide page (how to solve, a
   worked example, and the difficulty summary)".

The preview shows the full form of the page. It does not imitate the
fallback forms (captions-only, labels-only) the generator picks on small
trims; that is a fit decision for the PDF, not content.

## Acceptance criteria

- **AC-1:** *Given* a draft book with 3 easy puzzles, *when* `GET /book/<id>/finalize` is rendered, *then* the Guide page card's heading is `GUIDE_TITLE` ("How to Solve Nonograms") and the strings "How to use this book", "Have fun!" and "Fill in the grid based on the clues" appear nowhere on the page.
  *test: TestFinaliseGuidePreview_TitledLikeThePrintedPage (in tests/test_book_finalise_guide_preview.py)*
- **AC-2:** *Given* the book of AC-1, *when* the page is rendered, *then* the guide card holds every `WORKED_EXAMPLE_STEPS[i].caption` in step order, and the strip under step *i* has `WORKED_EXAMPLE_LENGTH` cells whose filled / crossed / blank states equal that step's `filled` / `crossed` sets.
  *test: TestFinaliseGuidePreview_ShowsTheWorkedExampleStepByStep (in tests/test_book_finalise_guide_preview.py)*
- **AC-3:** *Given* the generator module's `GUIDE_TITLE` and first step caption monkeypatched to sentinel strings, *when* the page is rendered, *then* the preview shows the sentinels — the screen reads the generator's text, it does not keep its own copy.
  *test: TestFinaliseGuidePreview_ReadsTheGeneratorsText (in tests/test_book_finalise_guide_preview.py)*
- **AC-4:** *Given* a book with 2 easy, 1 medium and 1 hard puzzle, *when* the page is rendered, *then* the guide card shows the intro and closing sentences equal to the generator's constants and counts 4 / 2 / 1 / 1, and the Contents card no longer says "instructions and difficulty summary".
  *test: TestFinaliseGuidePreview_CountsIntroAndClosing (in tests/test_book_finalise_guide_preview.py)*
- **AC-5:** The hoist of the intro / closing / worked-example heading into constants leaves the printed guide page pixel-identical.
  *test: the existing book pixel baseline (tests/helpers/book_corpus.py → tests/fixtures/book_baseline_card167.json) and tests/test_book_guide_page.py stay green unchanged*

## Guardrails

- G-1: The book interior's pixels do not move. `tests/fixtures/book_baseline_card167.json` stays the baseline (no new fixture), and `tests/test_book_guide_page.py` / `tests/test_book_guide_page_type.py` pass unedited. CON-020's 10 pt floor and CARD-149's type assertions are untouched.
- G-2: CARD-153 / CARD-129 Finalise counts and refusals are unchanged: `tests/test_book_finalise_gutter.py` passes unedited (page count, "About", unreadable-sheet reason, gutter refusal).
- G-3: No change to the guide page's content or layout logic (fallback forms, title shrink, `example_line_layout`). This card changes what the screen shows, not what the PDF prints.
- G-4: ADR-0036/R1 / CON-019 A4 golden: no layout or export code is touched.
- G-5: Layering: COMP-009's `app.py` imports only from its own `book_pdf_generator`; `test_every_import_in_the_package_points_inward` stays green. No JavaScript is added to the Finalise page (ADR-0038/R1).

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-169` (54 rules). A projection — fix the source artifact, never this list._

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
- ADR-0038/R5 — pyproject.toml package-data for nonogram.admin includes static/*.js alongside templates/*.html and static/*.css, so the player's script ships in every built wheel. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correc… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a n… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decode… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a paramet… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution. A type size is a physical measure - points or millimetres converted… (check: review-lens)
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

- **FR:** FR-041 (AC-324..AC-326, amended 2026-10-04: the guide page's title and worked example — this card makes the screen describe it); FR-043 (guide page = interior page 1, which the preview's footnote already states); FR-030 / CARD-129 (Finalise page counts, guarded)
- **CON:** CON-020 (10 pt floor, guarded via G-1)
- **ADR:** ADR-0036/R1 (default PageSpec byte-identical), ADR-0038/R1 (hand-written HTML/CSS, no build step)
- **Components:** COMP-009 (admin panel: Finalise route, template, guide-page generator)
- **Trace:** meta/architecture/trace.yml (COMP-009); no new requirement — the preview has no AC of its own in requirements.yml, so these ACs are card-local

## Design context

- **Screen:** Book scaffolding step 4, Finalise & export (`book_finalize.html`), the "Guide page — generated" card and the Contents card.
- **Design system:** meta/design/ — Pressroom direction (brief.md), tokens.css; existing `.guide-preview` styles in src/nonogram/admin/static/admin.css (~line 308) on `--grid-paper`. The step strip should read like the printed example: square cells, filled in ink, crossed with an X, a heavier outer frame; reuse tokens, no new colour. If the strip earns a reusable name, add a short entry to meta/design/components.md (optional; note it as SCOPE+).
- **Renders:** ~/Documents/nonogram-reviews/CARD-169/ (owner visual check: a screenshot of the Finalise screen's guide card beside CARD-167's guide-book1-8.5x11.png)

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-085 (CARD-167 follow-up recorded in CARD-167's Worktree notes: "book_finalize.html's guide preview still reads 'How to use this book' with the old instruction list").
- [Verified 2026-10-04] Generator constants: `GUIDE_TITLE` (book_pdf_generator.py:418), `WORKED_EXAMPLE_CLUE` / `WORKED_EXAMPLE_LENGTH` (:422-423), `ExampleStep` (caption, label, filled, crossed — 0-based square indices), `WORKED_EXAMPLE_STEPS` (:448). The intro paragraph, the "This book contains N puzzles:" lines, "Worked example: the clue 3 1 on a row of 6 squares." and the closing sentence are literals inside `create_guide_page`'s nested `set_page` (~:1574-1600).
- [Verified] Template: guide card at book_finalize.html:46-70, Contents line at :78. The route is `app.py:4246` (`/book/<book_id>/finalize`), context dict ~:4457, render at :4502. `app.py:105` already imports from `nonogram.admin.book_pdf_generator`.
- [Verified] No existing test asserts the old preview text ("How to use this book", "Have fun!", "Difficulty levels" grep over tests/ hits only tests/test_book_guide_page.py, which is about the PDF's OLD_TITLE). So no test needs updating for the removal.
- [Test fixture] `tests/test_book_finalise_gutter.py`'s `panel` fixture / `Shelf.shown(book_id)` (GET finalize, records written straight to the store) is the cheapest way to render the page without uniqueness proofs; reuse its pattern, do not import across test modules unless via tests/helpers/.
- [Pixel check] Before and after the hoist, run tests/test_book_guide_page.py and the book baseline test (tests/helpers/book_corpus.py users); the fingerprint must reproduce card167's recording unchanged.
