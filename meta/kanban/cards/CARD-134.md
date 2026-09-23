# CARD-134: The answer key in the book PDF — puzzle-number order, 6-up / 4-up pages, "Puzzle N — Title" captions

**Status:** blocked
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
**Touches:** src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_answer_key.py, tests/property/test_book_answer_key.py, src/nonogram/export/png.py (G-1a: the caption face only), tests/test_book_pdf_band.py (G-2a: the two retargeted methods only)
**Review score:** 8.0 (cycle 2/3)
**Started:** 2026-09-23
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** escalated — decompose: G-2a authorises two methods of TestBookPdf_AnswerKeyCarriesPictureTitle; the class's THIRD method was made vacuous by this card and needs the same authorisation to be retargeted or deleted (one ruling; nothing else on the card is open)

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
- G-1a (**decompose ruling, 2026-09-23** — narrow exception to G-1): ONE edit inside `src/nonogram/export/png.py` is permitted and required — the caption FACE used by `render_answer_page`. `ImageFont.load_default` has no U+2014, so "Puzzle 7 — Snowflake" prints a .notdef box and AC-268 is unsatisfiable as written. Load the packaged DejaVu through `importlib.resources`, exactly as `_band_font` and `pdf._draw_header` already do; ADR-0006/R1 explicitly permits non-executable static assets, so the dependency baseline is untouched. Nothing else in `export/**` may change: no tile geometry, no cell fitting, no grid lines — ADR-0036/R2 stands. The fix MUST ship a test that distinguishes rendered ink from the unmapped separator; comparing one render of a face against another render of the same face cannot see this defect, which is why no existing test caught it. G-3 (CON-019) still binds and the golden tripwire must stay green — answer pages are not CLI exports, so it should not move at all.
- G-2: The picture title prints only in the answer key, never on a puzzle page (ADR-0037/R1). test: TestBookPdf_PuzzlePageCarriesNoPictureTitle, TestBookPdf_AnswerKeyCarriesPictureTitle (CARD-117) stay green.
- G-2a (**decompose ruling, 2026-09-23** — authorized retarget): two methods of `TestBookPdf_AnswerKeyCarriesPictureTitle` (tests/test_book_pdf_band.py:343-397) assert a whole answer page byte-for-byte against `render_pages(payload_with_name, spec)[1]` — the clued page FR-042 DELETES. That is mutually exclusive with AC-261/270/292, so the card may retarget those two methods onto the new answer-page form. The RULE is unchanged and must still hold: the picture title prints only in the answer key, never on a puzzle page. Only CARD-117's pinned form changes, and the retargeted assertions must be at least as strong — assert the title's ink is present on the answer page and absent from the puzzle page, not merely that the render did not raise. `TestBookPdf_PuzzlePageCarriesNoPictureTitle` is NOT in scope and stays byte-identical.
- G-3: CLI and web A4 output stay byte-identical (CON-019). test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden, PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry.
- G-4: Answer pages are decided at PDF time, and nothing is stored (Increment 15 Rollback). Do not edit `src/nonogram/db/**`, `migrations/**` or `src/nonogram/admin/book_manager.py`.
- G-5: Do not edit `src/nonogram/admin/book_proof.py`, `src/nonogram/admin/app.py`, `src/nonogram/admin/templates/book_setup_print.html`, `src/nonogram/admin/templates/book_detail.html`, `src/nonogram/admin/templates/books_list.html` or `src/nonogram/admin/templates/_stepper.html`. They are owned by CARD-118 / CARD-130 this wave.
- G-6: Out of scope: solution hints (deferred, not Book 1). The puzzle section's level order and divider pages are CARD-128's.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data … (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, … (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode … (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by more than 2x from the … (check: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the other side from the source's … (check: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dimensions from one. (check: review-lens)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniqueness from the fact that a grid … (check: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit on one lineage, is a named … (check: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that set holds no filled/empty … (check: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws nothing from the injected Random … (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DENSITY and MAX_DENSITY are the … (check: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density grounds, and no module's … (check: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the share of cells settled … (check: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the … (check: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of … (check: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them, intersected), and are … (check: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all (empty or None … (check: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid it was handed and refuses, … (check: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never satisfies a quality minimum, … (check: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id). (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percentage points of that cell's … (check: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place … (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool … (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory … (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses … (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and … (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is … (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a parameter: no supported call into … (check: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not pass the door in force. With … (check: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-019 — Adding book-specific page geometry (a trim, margins, a title band, a portrait-only rule, the 7.5 mm standard cell) never changes the CLI's or the web UI's exports: for any generation request the PNG, … (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured … (check: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (check: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit … (check: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; … (check: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest … (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that … (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the … (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-042 (AC-261, AC-263, AC-264, AC-266, AC-268..AC-270, AC-290..AC-292, EC-030); FR-041 (answer-key level headings)
- **NFR:** —
- **ADR:** ADR-0036, ADR-0037
- **Components:** COMP-009, COMP-007 (consumed)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

### [CARD-134, 2026-09-23] Implementation summary — TWO BLOCKERS — both RESOLVED 2026-09-23 by the decompose ruling

**[BLOCKER — RESOLVED 2026-09-23 by the decompose ruling G-1a; fixed in 81b68c0] guardrail conflict: G-1 vs AC-268 — CARD-133's `render_answer_page`
sets every caption in `ImageFont.load_default()`, which has no U+2014, so
"Puzzle 7 — Snowflake" prints "Puzzle 7 ▯ Snowflake" on the page.**

Measured, not inferred (`src/nonogram/export/png.py:277`,
`ImageFont.load_default(size=tile.caption_font_size)`):

| face | U+2014 bitmap == U+FFFF (a codepoint no face has) | advance |
|---|---|---|
| Pillow's default | **True** — i.e. `.notdef` | 21 px |
| the packaged DejaVu Sans (`export.pdf.FONT_PACKAGE`) | False | 41 px |

The same trap `book_pdf_generator._band_font` was written for: its docstring
already records that U+00B7 "is not in Pillow's embedded ASCII default face — a
band set in that would print a `.notdef` box", and it reads the packaged face
through `importlib.resources` for exactly that reason. The answer key's caption
line does not, and the level heading ("Easy") is unaffected only because it is
ASCII.

The fix is one line in `export/png.render_answer_page` — set the caption (and
the heading, for the same reason) in the packaged face, as
`_set_band`/`pdf._draw_header` already do — and **G-1 forbids this card from
touching `src/nonogram/export/**` at all**, with "if something is missing there,
escalate". So it is escalated rather than worked around: the two workarounds
available here (drop the em dash for an ASCII hyphen, or draw the caption in the
admin panel) each break something else — AC-268 states the em dash, and drawing
the caption here would be exactly the "the admin panel places no lettering of
its tiles" half of ADR-0036/R2.

**Note for whoever fixes it: no test in the tree can catch this.** Every caption
assertion — mine included — compares the generator's page against a page built
by the *same* renderer, so both sides print the same `.notdef` box and agree.
It was found by rendering the proof pages and looking at them. A fix should come
with a check that the caption's ink differs from the ink of a caption whose
separator is replaced by an unmapped codepoint.

**[BLOCKER — RESOLVED 2026-09-23 by the decompose ruling G-2a; fixed in 81b68c0] guardrail conflict: G-2 vs AC-261 — `TestBookPdf_AnswerKeyCarriesPictureTitle`
pins the one-answer-page-per-puzzle key byte-for-byte, which FR-042 replaces.**

Two of that class's three methods fail and cannot be made to pass by any
implementation that satisfies FR-042:

- `test_the_answer_page_carries_the_title_and_the_same_identity` and
  `test_the_answer_number_is_the_number_printed_on_the_puzzle` assert
  `pages[3 + count + index] == render_pages(payload_with_name, spec)[1]` — a
  **full** answer page carrying the puzzle's clues and a header band reading
  "Snowflake — Puzzle 1 · Easy". After FR-042 that page does not exist: the
  answer prints as a tile of a packed key under the caption "Puzzle 1 —
  Snowflake". AC-261/AC-270/AC-292 and this assertion are mutually exclusive.
- The third method and the whole of `TestBookPdf_PuzzlePageCarriesNoPictureTitle`
  stay green unchanged, and so does
  `PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle`.

G-2's **rule** survives FR-042 intact — the picture's title still prints only in
the answer key and never on a puzzle page (ADR-0037/R1) — it is only the *form*
those two CARD-117 tests pin it in that FR-042 changes. `tests/test_book_pdf_band.py`
has therefore **not been touched**: retargeting them at the caption is a CARD-117
decision, not this card's, and the guardrail says so. The retarget itself is
small (compare against `render_answer_page([(grid, "Puzzle 1 — Snowflake")], 6,
spec, "Easy")`, as `tests/test_book_answer_key.py` does throughout).

### What was built

- **`src/nonogram/admin/book_answer_key.py` (new)** — the packing walk as a pure
  function over value objects. No PIL, no `PageSpec`, no geometry: `Answer`
  (number, extent, level), `AnswerPage` (answers + heading, with `capacity`
  **derived** from the answers so a page and its tiling cannot drift apart),
  `page_capacity`, `level_heading`, `answer_title`, `answer_caption`,
  `pack_answer_pages`. Both types are valid by construction — a page of two
  levels, of seven answers, or of five with a large one among them cannot be
  built — so INV-011 is a property of the type and not only of the walk.
- **`book_pdf_generator.py`** — `answer_key(payloads, ids=)` (payloads →
  `Answer`s → `pack_answer_pages`), `custom_titles()` (reads
  `books.puzzle_titles` off a `Book`, a row or a mapping, without importing
  `book_manager` and without swallowing an exception), `_answer_page(...)` (one
  `render_answer_page` call per page, on that page's own spec) replacing the
  per-puzzle loop; `_banded` became `_puzzle_payload` (the answer half had no
  caller left).
- **Page counts.** `interior_page_count(puzzle_count, puzzle_pages=None,
  answer_pages=None)` — both variable terms default to one page each, so the
  **one-argument call `app.py:3323` makes is unchanged in meaning**: the
  un-paired, un-packed plan, the upper bound that screen has always labelled
  "~" (CARD-129/EC-034 owns making it exact; the bound is now wider). The
  divider is still `2 + len(plan)` and the key starts at `3 + len(plan)`.
  `Interior`/`BookExport` gained `answer_page_count` (divider not counted).
  `Interior.unpaired_page_count` is computed with the **packed** answer term on
  both sides of the subtraction, so `pages_saved` still measures pairing alone.
- **Failure naming.** The answer walk runs before any page is drawn and raises
  `RuntimeError("puzzle 'p4' could not be laid out: ...")` through
  `_named_puzzles`, matching `puzzle_pages`. Its own tripwire — the key must
  hold puzzles 1..n — is taken over `interior`'s *input*, like the puzzle
  walk's, not over the walk's own output.
- **Decision (documented in `answer_caption`):** a puzzle with neither a custom
  book title nor a name is captioned "Puzzle 7" and stops — no dangling em
  dash. Same reasoning as `band_identity`'s ungraded band.
- **Decision (documented in `pack_answer_pages`):** the heading marks the first
  page of a level's *run*. For any order a book can be in (INV-009 groups by
  tier) a run is a level, which is AC-291 exactly; a legacy order that returns
  to a level already left gets a second heading rather than an unheaded run
  that would read as a continuation.

### EC-030 — one thing the wording needs

`tests/property/test_book_answer_key.py` proves EC-030 over a 440-book seeded
corpus **plus** an exhaustive enumeration of every book of up to 3 puzzles over
a 5-size × 3-level alphabet (1,125 orders at length 3).

EC-030's `ceil(n / 4) + (L - 1)` bound holds for `L` = the number of level
**runs**. Over an order that is not grouped by level it is not merely wrong but
unreachable by *any* walk that also keeps "no page holds two levels": easy,
medium, easy is 3 answers over 2 levels and needs 3 pages, while the bound is 2.
Since INV-009 groups a book's order by tier, runs = levels for every order a
book can be in, and the two readings coincide — but the corpus checks both, and
requires ≥150 genuinely grouped books so the literal bound is well exercised.
**Suggest amending EC-030's wording to "L level runs (= non-empty levels for
any INV-009-grouped order)".**

### SCOPE+ (existing shared files changed, all additively or as the collision list foresaw)

- `SCOPE+ tests/test_book_pdf.py` — `TestBookPdf_PageSizeEqualsStoredTrim`'s
  page count (3 answer pages → 1, named as a `PAGES` constant with its
  make-up); `TestBookPdf_UnbuildablePuzzleNeverShiftsALaterPage` 6 → 5;
  `TestBookPdf_PagePlanGuardIsLive`'s monkeypatch signature gains
  `answer_pages=None` and passes it through, so the guard is still proved live
  and the assertion text is unchanged.
- `SCOPE+ tests/test_book_pdf_two_up.py` — 16 bare page-count literals replaced
  by `_interior_pages(puzzle_pages=…, answer_pages=…)`, which names both terms
  at every call site instead of leaving either a literal. No pairing assertion
  changed.
- `SCOPE+ tests/test_book_export_interior_cover.py` — `_interior_pages()` +
  `STANDARD_BOOK_PAGES`; `TestBookFinalise_PageCountIsTheExportsPagePlan` split
  into three tests, all still cross-checked against the **written PDF's** page
  tree: the plan given every term equals the file exactly, the one-argument
  plan bounds the file from above, and Finalise shows that bound. A
  `puzzle_count` of 7 was added so the two-answer-page case is covered.
- `SCOPE+ tests/property/test_book_pairing.py` — `_expected_answer_pages()`, an
  independent second implementation of the key's page count for that corpus.
- `SCOPE+ tests/property/test_book_pdf_geometry.py` — EC-032's absolute
  `drawing_left_mm` prediction now applies to the puzzle pages; the answer pages
  carry the parity half that a tiled page still states sharply (same answer, two
  parities, shift = gutter − outside) plus a containment check. Nothing dropped.
- `SCOPE+ tests/property/test_book_export_interior.py` — EC-034/INV-013 gained
  an independent `_answer_page_plan()` and `_expected_answer_left_mm()` (CARD-133's
  tile arithmetic written out in mm), so every answer page's **leftmost grid** is
  still measured against its own parity's left margin. New corpus floors require
  ≥20 answer pages, both tilings and ≥10 headed pages.

### Render proof (`~/Documents/nonogram-reviews/CARD-134/`)

`01-six-up-easy-heading.png`, `02-six-up-second-page-no-heading.png`,
`03-mixed-1.png` (4-up, 10x10 / 20x15 / 12x20 / 30x30), `04-mixed-2.png`.

What I saw:

1. **The `.notdef` box in every caption** — the first blocker above. Reads
   "Puzzle 1 ▯ Snowflake". The heading "Easy" is clean.
2. **The ragged bottom is real and worse than CARD-133 feared** — the owner
   question it left open. On `03-mixed-1.png` the 10x10 in the top-left tile
   occupies about a third of its tile's height, and because every grid hangs
   from its caption the whole top row of tiles has a deep white band under it
   while the tiles below start at their own fixed line. A mixed page reads as
   two unrelated rows rather than as a grid. Vertically centring each grid in
   its tile would halve the worst gap. **It is `export/` geometry (G-1), so
   nothing was changed here — it is for the owner to decide and for CARD-133 to
   do.** A 6-up page of same-size answers (`01`) reads well.
3. Level headings, page breaks per level, captions (apart from the dash) and
   the 6-up / 4-up switch all look right on paper.

### Suite state

Full suite green apart from the one known pre-existing e2e failure
(`test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`,
deselected) **and the two G-2 tests named in the second blocker**. All ten
AC-named test classes and `PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook`
pass. `AC-293` / `TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages`
(named in INV-011's check list) was deliberately left to CARD-128, which the
card assigns it to.

- [Handover from CARD-133, 2026-09-23] Call `from nonogram.export.layout import compute_answer_page_layout` -> (extents, capacity, page_spec, heading=None) -> AnswerPageLayout, and `from nonogram.export.png import render_answer_page` -> (answers, capacity, page_spec, heading=None) -> Image. Import from the submodules, not the package. extents/answers in fill order (left->right, top->bottom), 1..capacity, capacity in {4,6}, page_spec for THAT page's parity (its band_mm is ignored), same heading to both.
- [Handover from CARD-133 — CRITICAL] The 3.19 mm answer-cell floor is NOT enforced by the type: a 25x25 six-up returns 3.178 mm and a 30x30 six-up 2.648 mm with no error. Owning "six-up only while every answer on the page is <=20 on its longest side" (INV-011) is THIS card's job; re-check it, do not assume CARD-133 guarantees it.

- [Handover from CARD-117, 2026-09-23] A two-up page needs TWO bands on one sheet, but the export draws one band per render_pages call — that is a COMP-007 conversation, settle it with CARD-127 rather than working around it in the PDF layer.


- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured).
- [Scope] src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_answer_key.py, tests/property/test_book_answer_key.py, tests/test_book_pdf.py, tests/test_book_pdf_two_up.py, tests/test_book_export_interior_cover.py, tests/property/test_book_export_interior.py, tests/property/test_book_pairing.py, tests/property/test_book_pdf_geometry.py (commit 2cb5883).
- [Build gate] FAILED (full, under the repo full-suite lock, run twice) — exactly 2 failures, both `tests/test_book_pdf_band.py::TestBookPdf_AnswerKeyCarriesPictureTitle` (`test_the_answer_page_carries_the_title_and_the_same_identity`, `test_the_answer_number_is_the_number_printed_on_the_puzzle`) — the G-2 conflict below, not a code defect. The known pre-existing `test_size_configuration_applied` was deselected. Nothing else red.
- [Guard] BLOCKER CHECK fired: 2 `[BLOCKER]` markers in the worktree notes. No review cycle was started.
- [Orchestrator verification] Both blockers re-derived independently before escalating, not taken on the agent's word:
  * G-1 vs AC-268 — in this venv `ImageFont.load_default(size=24)` renders U+2014 byte-identically to U+FFFF (`.notdef`), while "A" differs; `src/nonogram/export/png.py:277` is the call that sets every answer caption in that face. So the printed caption is "Puzzle 7 ▯ Snowflake". Confirmed.
  * G-2 vs AC-261 — `tests/test_book_pdf_band.py:343-397`: two of the three methods assert a whole answer page byte-for-byte against `render_pages(payload_with_name, spec)[1]`, the full clued page FR-042 deletes. No implementation satisfies both. Confirmed.
- [Escalated] 2026-09-23 — station: decompose. Two guardrail↔AC conflicts, neither weakenable in the worktree. (1) G-1 forbids `src/nonogram/export/**` and tells this card to escalate if something is missing there; what is missing is a caption face carrying U+2014 in CARD-133's `render_answer_page` — a one-line change to read the packaged DejaVu through `importlib.resources`, exactly as `book_pdf_generator._band_font` and `export.pdf._draw_header` already do, and it must ship with a test comparing the caption's ink against the same caption with an unmapped separator, because every existing caption assertion compares one render of that face with another and agrees on the box. (2) G-2 names two CARD-117 tests that pin the one-answer-page-per-puzzle form FR-042 replaces; G-2's rule (the title prints only in the key) survives, only the form changes — retargeting them at `render_answer_page([(grid, "Puzzle 1 — Snowflake")], 6, spec, "Easy")` is a CARD-117/decompose decision. Route: fix the card contract (widen G-1 for that one line or cut a card against `export/`; retarget G-2's test list), then `/kanban review CARD-134`. Worktree and branch KEPT; commit 2cb5883 stands. Do NOT weaken either guardrail in the worktree.
- [Owner] Renders in ~/Documents/nonogram-reviews/CARD-134/ (01-six-up-easy-heading.png, 02-six-up-second-page-no-heading.png, 03-mixed-1.png, 04-mixed-2.png). Two things to eyeball: the `.notdef` box standing where the em dash belongs in every caption, and CARD-133's open question now answered with evidence — grids hang from their captions, so a mixed 4-up page (03) has a deep white band under its top row and reads as two unrelated rows. Vertically centring each grid in its tile is `export/` geometry and CARD-133's to do.
- [Architect] EC-030's `ceil(n / 4) + (L - 1)` bound holds for L = level **runs**, not non-empty levels: easy/medium/easy is 3 answers over 2 levels and needs 3 pages against a bound of 2. INV-009 groups every real book by tier so the two readings coincide; suggested wording "L level runs (= non-empty levels for any INV-009-grouped order)".

- [Escalation resolved 2026-09-23, station decompose] Both blockers ruled on by the
  dispatcher, above as G-1a and G-2a. Blocker 1 (the em-dash .notdef box) gets a narrow,
  test-backed exception to G-1 rather than a separate card: the defect is one line in the
  face CARD-133 chose, the card already owns the caption text, and splitting it would
  serialize the last card of the wave behind a one-line fix. Blocker 2 (CARD-117's two
  byte-equality methods) is an authorized retarget: the rule survives intact, only its
  pinned form moves. Neither ruling widens the card's Touches beyond export/png.py and
  tests/test_book_pdf_band.py.

### [CARD-134, 2026-09-23] G-1a and G-2a applied — both blockers CLEARED

Both `[BLOCKER]` write-ups above are historical and now **resolved**; nothing in
this run routed around a guardrail. Two files changed on top of commit 2cb5883,
exactly the two the rulings authorize.

**FIX 1 (G-1a) — `src/nonogram/export/png.py`, the answer key's face.**
Added `FONT_PACKAGE` / `FONT_RESOURCE` (the same package *data* `export.pdf`
names, ADR-0006/R1's static asset) plus `_lettering_font_bytes()` /
`_lettering_font(size)` — `importlib.resources` + an `lru_cache`, mirroring
`pdf._font_bytes`/`_header_font` and `book_pdf_generator._band_font` rather
than inventing a third pattern. `render_answer_page` now sets its captions and
its heading in that face instead of `ImageFont.load_default(...)`. Nothing else
in `export/**` moved: no tile geometry, no cell fitting, no grid line, no
vertical centring (ADR-0036/R2 stands, and the ragged bottom is still CARD-133's
and the owner's). `_clue_font` deliberately stays on Pillow's default — clue
digits are ASCII decimals and CON-019's A4 tripwire rules every CLI page.

The resource address is *spelled out again* in `png.py` rather than imported
from `pdf.py`: `pdf` imports `png` (`render_image` is the raster a PDF page is
saved from), so importing it back would be a cycle. `test_cli.py`'s AST guard is
untouched by this — no `nonogram.admin` import was created — and a new test pins
the two spellings equal so the two modules cannot drift to two different files.

**Heading-face decision: the heading takes the packaged face too.** Chosen
deliberately, not by accident of the diff. Three reasons: the caption and the
heading are the same lettering on one page doing the same job, and two typefaces
across two adjacent lines reads as a slip; a level *label* is a display string
(ADR-0031 data), not structurally-ASCII like a clue digit, so the coverage
argument that forces the caption also applies to it; and the cost is nil, the
face being already read and cached. It does change rendered pixels, so it was
checked that this card's own ACs still measure what they claim: every caption
and heading AC compares the generator's page against a `render_answer_page`
page, so both sides move together and the comparison is still about *which*
answers, captions and headings — and AC-291's heading check is `answer_grids` /
`text_lines_above_the_first_grid`, read off ink, which is face-independent.
CARD-133's `tests/test_layout_answer_tiles.py` (incl.
`test_the_caption_and_heading_are_the_only_other_ink`) and
`tests/property/test_book_answer_tiles.py` are green unchanged.

**The new test — `TestBookAnswerKey_CaptionSeparatorIsADrawnGlyph`**
(`tests/test_book_answer_key.py`, under AC-268, three methods):

- `test_the_em_dash_is_ink_an_unmapped_codepoint_would_not_have_made` — the
  assertion no existing test could make. The page captioned
  "Puzzle 7 — Snowflake" is compared with the *same* page captioned
  "Puzzle 7 ￿ Snowflake" (U+FFFF: permanently unassigned, so every face
  rasterizes it to its own `.notdef`). A face without U+2014 draws the two
  identically; the packaged one cannot.
- `test_the_separator_prints_as_a_bar_and_the_unmapped_one_does_not` — the
  positive half, so the first assertion is not satisfied by *any* second glyph.
  The separator's own ink is isolated by difference against the same page with
  an empty caption (which prints nothing and keeps the geometry), and an em dash
  must measure at least 3x wider than tall while the `.notdef` control must not.
  Measured in this venv: U+2014 is 44x4 px and its `.notdef` 24x42 px, so the
  threshold sits nowhere near either.
- `test_the_face_is_the_packaged_one_the_pdf_header_already_uses` — the
  anti-drift pin, `png.FONT_PACKAGE/RESOURCE == pdf.FONT_PACKAGE/RESOURCE`.

Mutation-checked: with the caption line reverted to `load_default` both of the
first two methods fail, and the rest of the file still passes — which is the
whole point of the class.

**FIX 2 (G-2a) — `tests/test_book_pdf_band.py`, the authorized retarget.**
Only the two named methods of `TestBookPdf_AnswerKeyCarriesPictureTitle` and the
helpers they needed. `TestBookPdf_PuzzlePageCarriesNoPictureTitle` and the
class's third method (`test_the_title_is_ink_the_answer_band_would_not_have_without_it`,
still green unchanged) are byte-identical.

Added beside `BAND_TEMPLATE`: `ANSWER_CAPTION = "Puzzle {number} — {title}"` and
`UNTITLED_ANSWER_CAPTION = "Puzzle {number}"` — FR-042's caption written out
here as a second implementation, never `book_answer_key.answer_caption` run
twice — plus `_answer_page(entries, page_number, heading)`, the packed-page twin
of `_pages_with_band`.

ADR-0037/R1 is now asserted in both directions on one book, which is strictly
more than the byte-equality it replaces:

- **absent** — the puzzle page is still, pixel for pixel, the page of a payload
  carrying `name=None`, so "Snowflake" is nowhere on it (kept from the original,
  and its band line now comes from `expected_band(number, tier)` rather than a
  hand-spelled literal, so one `number` feeds the band and the caption);
- **present** — the answer page equals the packed page captioned
  "Puzzle 1 — Snowflake" under the heading "Easy", exactly — so a wrong number,
  a wrong title, a wrong heading or a wrong tiling fails it;
- **contributing** — that page is *not* the page captioned "Puzzle 1", so the
  title is shown to be ink rather than a string that was merely offered.

`test_the_answer_number_is_the_number_printed_on_the_puzzle` keeps its
three-puzzle / three-tier book (now three answer pages, one per level, AC-290)
and applies the same present + contributing pair to each of pages 6, 7 and 8, so
an answer captioned from its interior position would read "Puzzle 6" and be
caught exactly as before.

### Render proof, re-rendered (`~/Documents/nonogram-reviews/CARD-134/`)

The same four pages, overwritten, and looked at:

1. **The `.notdef` box is gone.** Every caption reads "Puzzle 1 — Snowflake"
   with a real em dash — a flat bar at x-height, correctly spaced, on both the
   six-up and the four-up pages. Confirmed on the full-resolution crops, not
   only on a thumbnail.
2. The headings ("Easy", "Hard") now set in the same face as the captions; the
   page reads as one piece of typography rather than two.
3. **The ragged bottom is unchanged and still open** — `03-mixed-1.png` still
   shows the 10x10 ending far above the 20x15 beside it, because grids hang
   from their captions. That is `export/` geometry outside G-1a's one-line
   exception (ADR-0036/R2), so it was deliberately left alone: still CARD-133's
   to do and the owner's to rule on.

- [Scope, G-1a/G-2a run] + src/nonogram/export/png.py (the answer key's lettering
  face only), + tests/test_book_pdf_band.py (the two retargeted methods and their
  helpers only), and tests/test_book_answer_key.py (the new class). On top of the
  scope recorded at 2cb5883; nothing under `src/nonogram/db/**`, `migrations/**`,
  `book_manager.py`, `book_proof.py`, `app.py` or the four named templates was
  touched (G-4, G-5), and the CON-019 golden tripwire did not move (G-3).
- [Unblocked] 2026-09-23 — decompose ruled on both blockers (G-1a, G-2a above). Touches grown by exactly the two files the ruling names, and by nothing else. Pipeline resumed at the fix step; base stays the merge-base 679e78a (main has moved to 2089004; the dispatcher rebases at merge).
- [Blocker check] both `[BLOCKER` markers above are retired: ruled on by decompose (G-1a, G-2a) and fixed in 81b68c0. No live blocker remains; entering the review phase.
- [Scope] src/nonogram/export/png.py, src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_answer_key.py, tests/property/test_book_answer_key.py, tests/test_book_pdf_band.py + the 6 SCOPE+ test files (2cb5883, 81b68c0).
- [System contract] section stale — refreshed from the model before review cycle 1: +ADR-0023/R1, +CON-019 / −none (44 → 46 rules). CON-019 is the card's own G-3 tripwire, so its absence from the projection mattered.
- [Build gate] PASSED (full, 246s) — exit 0, ~4881 tests, 0 failures; 1 deselected (the known pre-existing tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied). Run under the repo full-suite lock via fcntl.flock (flock(1) does not exist on macOS) with a private --basetemp.
- [Scope gate] GROWN — 12 changed files, 6 inside Touches (incl. the two G-1a/G-2a additions), 6 existing test files outside it, all recorded as SCOPE+ because they pinned the one-page-per-answer arithmetic FR-042 replaces. comp_spread 0 (COMP-009 + COMP-007, both in the card's Components). guardrail_hits 0: export/png.py and test_book_pdf_band.py are authorized by G-1a/G-2a and are in Touches; no hit on G-3/G-4/G-5 globs. Judged against the MERGE-BASE 679e78a, never against main. SCOPE NOTE passed to the reviewer.
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1. Step 8h: 46 rules checked (13 ✓ holds with evidence, 33 ⚠ unchecked/no_eligible_fact, 0 ✗) — full coverage of the refreshed card section, count line present.
- [Review sync] 1 report(s) → meta/review/ (20260923T173011Z-CARD-134-cycle1.yml)
- [Adversarial] F-001 (self-referential Finalise assertion, tests/test_book_export_interior_cover.py:640) CONFIRMED — the skeptic reproduced the self-reference (app.py:3323 makes the same one-arg call that the assertion recomputes; the merge-base form used the written PDF's own page count) and mutated book_pdf_generator's one-arg default path: all 10 tests of TestBookFinalise_PageCountIsTheExportsPagePlan passed blind to it. Correction recorded: the finding's second half is wrong — the exact one-argument value IS still pinned, by the unchanged literal `~8` at tests/test_book_export_interior_cover.py:360, which is what the mutation actually killed. Severity kept as the reviewer assigned; the fix is one line.
- [Severity gate 1/3] Score 8.5 >= threshold 8 but 1 confirmed important finding — fix mandatory, success path closed.
- [Fix 1] FIXED F-001 (expected value back to the file's own independent `_interior_pages` helper; mutation-verified — breaking interior_page_count's one-arg path now fails this assertion, where before it passed blind), FIXED F-002 (the `_answer_extent` docstring's claimed cross-check now exists: TestBookAnswerKey_TheExtentReaderAgreesWithTheRenderer), FIXED F-005 (the SCOPE+ note's "Nothing dropped" over-claim corrected). SKIPPED F-003 (renaming `answer_page_number` would touch TestBookPdf_PuzzlePageCarriesNoPictureTitle, which G-2a requires byte-identical — follow-up card) and F-004 (the heading face is a documented decision inside G-1a).
- [Fix 1] declarations: 0 updated, 0 confirmed, 1 none (F-001 local), plus 1 doc (`_answer_extent`) and 1 card-notes correction — both verified present in the diff, not merely claimed.
- [Fix pre-gate] PASSED — exactly the tests the FIXED lines name: TestBookFinalise_PageCountIsTheExportsPagePlan, TestBookFinalise_OffersBothDownloads, TestBookAnswerKey_TheExtentReaderAgreesWithTheRenderer → 18 passed.
- [Build gate] PASSED (full, 242s) — exit 0, 0 failures, 1 deselected (known pre-existing). Under the repo full-suite lock.
- [Review 2/3] Score: 8.0 — crit: 0, imp: 1 (new). Cycle 1's five findings all verified resolved by re-derivation, not on the fix agent's word: F-001 killed by the reviewer's own mutation of interior_page_count's one-argument path, F-002's cross-check confirmed to run BOTH readers, F-003's skip confirmed correct (TestBookPdf_PuzzlePageCarriesNoPictureTitle byte-compared at 679e78a vs HEAD — identical, 1933 bytes), F-004 and F-005 documented. Step 8h: 46 rules checked (13 ✓ holds, all re-derived fresh this cycle, 33 ⚠ unchecked/no_eligible_fact, 0 ✗) — full coverage, count line present. 8f mutation check ran (2 mutants, both restored).
- [Review sync] 1 report(s) → meta/review/ (20260923T175650Z-CARD-134-cycle2.yml)
- [Adversarial] F-006 (tests/test_book_pdf_band.py:432 `test_the_title_is_ink_the_answer_band_would_not_have_without_it` is now vacuous) CONFIRMED by an independent skeptic's own mutation: forcing `book_answer_key.answer_title` to return None makes the class's two RETARGETED methods FAIL and this one PASS (2 failed, 1 passed; baseline 3 passed). Both of its assertions measured title-independent — the packed page differs from the old-form page in ~3.0% of pixels whether the title is there or not (different page KINDS), and `_has_ink(_band_strip(page))` returns True even with heading=None and an untitled caption (18275 ink px), because the answer tile itself intrudes into the 12 mm strip. Correction to the finding: the mechanism is the tile, not only the "Easy" heading. Mutation restored byte-for-byte (shasum verified).
- [Severity gate 2/3] Score 8.0 >= threshold 8 but 1 confirmed important finding — success path closed.
- [Review 2/3] ⚠ improvement stalled — Δscore: -0.5, Δcrit+imp: 0. READ THIS WITH THE EVIDENCE, NOT AS A SPINNING LOOP: the check's two conditions are met mechanically, but its stated purpose ("escalate only if the loop is not progressing; if findings go away, give more cycles") is not. All five cycle-1 findings were independently verified RESOLVED this cycle — the reviewer re-derived each rather than trusting the fix agent, killing F-001 with its own mutation and byte-comparing the frozen class at 679e78a vs HEAD. The count stayed at 1 because one finding closed and a DIFFERENT, older defect opened: F-006 is in the original implementation (2cb5883), not in anything the cycle-1 fix touched, so it is not a family regression (streak 0) and no fix of this loop produced it.
- [Escalated] 2026-09-23 — station: decompose (second escalation, genuinely different from the first). ONE narrow contract question, everything else on this card is done. F-006's fix must touch `test_the_title_is_ink_the_answer_band_would_not_have_without_it`, the third method of TestBookPdf_AnswerKeyCarriesPictureTitle. G-2a authorises exactly two methods of that class; the third is neither authorised nor frozen (only TestBookPdf_PuzzlePageCarriesNoPictureTitle is frozen byte-identical, and it is untouched and verified identical). I will not widen a guardrail in the worktree, so I am asking for the ruling instead of taking the reading. Options, with my recommendation:
  (a) EXTEND G-2a to that third method and RETARGET it — compare the packed answer page against the same packed page drawn from a `name=None` payload, which is the like-for-like comparison its two siblings already make. Strictly stronger than today and keeps a third independent witness for ADR-0037/R1. **Recommended.**
  (b) EXTEND G-2a and DELETE the method — sibling 1 already carries the "contributing" half (`!= _answer_page([... UNTITLED_ANSWER_CAPTION ...])`), so it is subsumed. Cheapest, loses a witness.
  (c) AUTHORISE NEITHER — then the only honest action left is to amend the card note that currently presents this method as live coverage, and the dead test ships. Not recommended: a vacuous test with a name that claims a property is what the next reader will trust.
  Route: rule on (a)/(b)/(c), then `/kanban review CARD-134` — the worktree, both commits and the uncommitted cycle-1 fixes are all KEPT. Do NOT redo the card; nothing about the implementation is in question.
- [State at escalation] Implementation committed 2cb5883 + 81b68c0; cycle-1 fixes present but UNCOMMITTED (that is the procedure's fix loop, not an oversight). Full suite green (242s, exit 0, 0 failures, known pre-existing e2e deselected). Both review reports synced. The formal AC/EC/G verification gate has NOT run — it runs only on the success path — but cycle 1 and cycle 2 both walked all ten ACs and EC-030 against named tests and found them satisfied, and cycle 2's Step 8h reported 46/46 rules with 0 violations.
