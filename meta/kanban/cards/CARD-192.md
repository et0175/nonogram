# CARD-192: The Arrangement page can show one longest-side size, with what is left or over against the plan

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/192-arrange-size-filter
**Worktree:** —
**Source:** owner admin-panel amendments, 2026-10-06 (owner request: Arrangement filter by longest size with left/over info; owner decision: compare against the book's plan)
**Idea:** —
**Wave:** 35
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/static/admin.css, tests/test_book_arrange_size_filter.py (new)
**Review score:** 9.2 (cycle 1/3)
**Started:** 2026-10-06T13:04:58Z
**Closed:** 2026-10-06T17:07:38Z
**Actual:** 0.5d
**Merge commit:** da93164
**Blocked by:** —

## What to implement

The owner wants to look at one longest-side size on the Arrangement step (step 3)
and see, for that size, how far each level is from the book's plan.

**Current behaviour (read from code).**
- `app.py:arrange_puzzles_in_book` (GET/POST `/book/<book_id>/arrange-puzzles`,
  ~line 4086) lists every member, grouped by level through
  `book_mgr.puzzle_levels`. It reads no query parameter. It shows no plan figure.
- Every form on `book_arrange_puzzles.html` posts with no `action`, so it posts
  to the page's own URL. The route re-renders after a POST; it does not redirect.
- The plan-vs-actual per longest side × tier already exists, once:
  `app.py:_plan_progress(book, kept_ids)` (~line 3475). It builds `tab_progress`
  (one entry per bucket, each with `tiers` rows of `label/selected/planned/over`
  and a `total`) from `_selected_cells` (book members + pending ticks, through
  `book_plan.selection_cells`) and `_readable_plan` → `book_plan.planned_cells`.
  The selection step (`select_puzzles_for_book`) shows these figures in its tabs.
- The plan's size axis is the four longest-side buckets (`book_plan.LongestSideBucket`:
  `<=15`, `16-20`, `21-25`, `26-30`, decided by `book_plan.bucket_of`). The plan
  has no number for a single side such as 20. So the filter's sizes are these
  four buckets.

**Target behaviour.**
1. **Filter.** The route reads `?bucket=<label>` from `request.args`, through the
   existing `_TABS_BY_LABEL` (same labels as the selection step's tabs). No
   parameter, or a value that names no bucket, means "All sizes": the page is
   exactly as today. A chosen bucket keeps only the rows for which
   `_is_in_tab(puzzle, bucket)` is true. Rows of other sizes are hidden. A row
   whose stored size is outside 10..30 belongs to no bucket and is hidden too.
   An ungraded row in the bucket is shown under its Ungraded heading (it counts
   toward no plan cell, as today everywhere).
2. **Filter control.** Above the list: "All sizes" plus one link per bucket, each a
   plain GET link (`?bucket=16-20`), the current one marked with `aria-current`.
   Reuse the selection step's `.tabs`/`.tab` look; no `role="tablist"` (these
   are links, not tabs). Add CSS only if those classes do not fit.
3. **Plan line.** When a bucket is chosen, one line above the list reads, per
   level, members vs plan for that bucket, with the gap in words:
   `16-20: Easy 18 / 20 (2 left) · Medium 22 / 20 (2 over) · Hard 10 / 10 (on plan) · Total 50 / 50`.
   The figures come from `_plan_progress(book, [])["tab_progress"]`, the entry
   whose `bucket` is the chosen one. No second computation. "left" is
   `planned − selected` when positive, "over" is `selected − planned` when
   positive. Over is marked by the word, never colour alone (`data-over="true"`
   as `figure_cell` does). Counts are exact, as on `/books` (ADR-0035 / FR-039),
   not FR-037's ±3 pp gate.
   - `kept_ids` is `[]`: this page counts what the book holds, not pending
     selection-step ticks.
   - A book with no readable plan (`plan_present` false) shows the counts alone
     and one sentence pointing to Print setup (step 1), as the selection step does.
   - "All sizes" shows no plan line (the page stays as today).
4. **Level headings while filtered.** Each level heading says `(N shown of M)`.
   A level with no row of the chosen size keeps its heading and says
   "No puzzles of this size in this level." Page labels and divider-page lines
   keep their real page numbers (the plan is the whole book's).
5. **Moves while filtered: off.** Owner-visible choice, the simpler safe one.
   With a bucket chosen, the up/down buttons and the typed-position box are not
   rendered. One line says: "Reordering is off while one size is shown. Show all
   sizes to move puzzles." Title editing and Remove stay. Reason: a move acts on
   the level's full order (`moved_within_level`), so a click could swap with a
   hidden neighbour and look like nothing happened. The route's POST handling
   is unchanged: a move posted anyway still acts on the full order, which is safe.
6. **Persistence.** The filter survives every action on the page for free,
   because the forms post to the current URL, query string included. Two
   places build a URL by hand and must carry `bucket` when it is set:
   - the Remove confirmation (`_ask_to_confirm(... url_for("arrange_puzzles_in_book", book_id=book_id) ...)`, ~line 4184);
   - nothing else on this page (the Finish button leaves the step on purpose).
7. Works in both storage modes: the route reads only through `book_mgr`,
   `puzzle_review` and `_plan_progress`, which already serve both.

## Acceptance criteria

- **AC-1:** Given a book holding a 15×15, an 18×16 and a 25×21 puzzle, when `/arrange-puzzles?bucket=16-20` is rendered, then only the 18×16 row is listed; with no `bucket`, all three are listed.
  *test: TestArrangeSizeFilter_ShowsOnlyTheChosenBucket (in tests/test_book_arrange_size_filter.py, both storage modes)*
- **AC-2:** Given a plan of 16-20 easy 20 / medium 20 / hard 10 and members in 16-20 of 18 easy, 22 medium, 10 hard, when `?bucket=16-20` is rendered, then the plan line reads `Easy 18 / 20 (2 left)`, `Medium 22 / 20 (2 over)` with the medium figure carrying `data-over="true"`, and `Hard 10 / 10 (on plan)`.
  *test: TestArrangeSizeFilter_PlanLineShowsLeftAndOver (in tests/test_book_arrange_size_filter.py)*
- **AC-3:** Given the same book, when the selection step's 16-20 tab and the arrange page's 16-20 plan line are both rendered with no pending ticks, then their per-tier planned and selected numbers are equal.
  *test: TestArrangeSizeFilter_SameNumbersAsSelectionTab (in tests/test_book_arrange_size_filter.py)*
- **AC-4:** Given a book with no stored plan, when `?bucket=16-20` is rendered, then the line shows member counts with no `/ planned` figure and names Print setup.
  *test: TestArrangeSizeFilter_PlanLessBookShowsCountsOnly (in tests/test_book_arrange_size_filter.py)*
- **AC-5:** Given `?bucket=16-20`, when the page is rendered, then it has no `move_up`, `move_down` or `set_position` form and shows the "Reordering is off" line; with no `bucket`, those forms are present as today.
  *test: TestArrangeSizeFilter_MovesOffWhileFiltered (in tests/test_book_arrange_size_filter.py)*
- **AC-6:** Given `?bucket=16-20`, when the owner saves a title and when the owner confirms a Remove, then the page that comes back is still filtered to 16-20 (the confirm form's action carries `bucket=16-20`).
  *test: TestArrangeSizeFilter_FilterSurvivesTitleAndRemove (in tests/test_book_arrange_size_filter.py)*
- **AC-7:** Given `?bucket=nonsense`, when the page is rendered, then every member is listed and no plan line is shown.
  *test: TestArrangeSizeFilter_UnknownBucketMeansAllSizes (in tests/test_book_arrange_size_filter.py)*

## Guardrails

- G-1: The unfiltered page is unchanged apart from the filter links: same rows, order, numbering, page labels and move controls. Pinned by tests/test_book_level_order.py, tests/test_book_arrange_position.py, tests/test_book_arrange_page_breaks.py.
- G-2: One plan-vs-actual computation. The plan line reads `_plan_progress`; no new counting of cells, no new bucket thresholds (EC-024, `bucket_of` is the only bucketing). Membership comes from the book's own list, never the `puzzles.book_id` mirror (ADR-0033/R1).
- G-3: The selection step's tabs and `/books` "Against plan" figures are unchanged (tests/test_book_select_tabs.py, tests/test_books_list_plan_stats.py).
- G-4: INV-009 keeps its one enforcement point (`moved_within_level`); this card adds no move logic and changes no POST branch except the confirm URL.
- G-5: The page writes nothing on GET (EC-026). No book PDF pixel changes, so no book baseline changes.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-192` (52 rules). A projection — fix the source artifact, never this list._

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

- FR-036 (longest-side buckets, planned vs selected per tier; AC-208..AC-214 wording), EC-024 (one bucketing function).
- FR-034 (the plan matrix), FR-039 (exact short/over against the plan, ADR-0035), FR-037 (±3 pp gate; NOT used here — named so nobody reaches for it).
- FR-041 / INV-009 (book runs easy → medium → hard, moves stay inside a level).
- ADR-0033/R1 (book's own list), ADR-0035 (plan comparison), ADR-0019/R1 (adapter reads the param, domain decides).
- COMP-009 admin panel, CTX-001. Trace: FR-036 → CAP-006 → COMP-009 (trace.yml `req: FR-036`). This card adds no FR; card-local ACs only.

## Design context

- **Screen:** admin panel, book scaffolding step 3 "Arrangement" (`book_arrange_puzzles.html`).
- **Owner-visible defaults chosen here:** filter granularity is the plan's four buckets, not a single side; "All sizes" is the default; moves are hidden while filtered (with a one-line reason); plan line wording `Easy 18 / 20 (2 left)` / `(2 over)` / `(on plan)`; level headings `(N shown of M)`.
- **Renders:** ~/Documents/nonogram-reviews/CARD-192/ (owner visual check before merge): the page unfiltered, filtered to one bucket with a left and an over cell, a plan-less book filtered, and the filtered page at phone width.

## Worktree notes

- [Origin] Owner admin-panel amendments 2026-10-06: Arrangement filter by longest size with left/over info. Owner decision: compare against the book's plan, same numbers as the selection page's tabs. No IDEA.
- [Owner decision needed / flagged] The owner's example says "20:". The plan has no per-side numbers, only the four buckets, so this card filters by bucket (`16-20`). If the owner wants an exact-side filter, the plan line cannot be per side; that would be a different card.
- [Owner-visible choice] Moves are hidden while filtered (option "disable moves"), not "moves act on the full order". It is the simpler safe one; the server still accepts a posted move and applies it to the full order.
- [Overlap: CARD-191] Drafted in parallel: a sort-by-size button on this same page. Both cards touch `app.py:arrange_puzzles_in_book` and `book_arrange_puzzles.html`. Whichever merges second rebases. If CARD-191's button reorders the book, it is a reorder control and must also be hidden while a bucket is chosen (item 5 here); the second card to merge owns that line.
- [Facts] `arrange_puzzles_in_book` ~line 4086; Remove confirm `url_for` ~line 4184; `_TABS_BY_LABEL` line 3284; `_selected_cells` 3435; `_tier_figures` 3443; `_plan_progress` 3475; `_is_in_tab` 3506; `_readable_plan` 2814; `_printed_places` module-level 783. Line numbers shift; find by name.
- [Facts] `_plan_progress` does its own bulk read of members. The arrange route already bulk-reads them (`puzzle_review.get_puzzles`); one extra read per render is accepted rather than adding a second entry point to the computation.
- [Facts] The selection step's `figure_cell`/`figure_row` macros are inline in `book_select_puzzles.html`, not a shared partial. Do not move them (keeps Touches off that file); write the plan line in the arrange template.
- [Tests] Reuse the shelf, panel and both-mode fixtures from tests/test_book_level_order.py (`MODES`, `sqlite_session_scope`), as tests/test_book_arrange_position.py does. No existing test pins the absence of a query param, so none should need updating.
- [Conditional Touches] `src/nonogram/admin/static/admin.css` only if the reused `.tabs`/`.tab` classes do not fit plain links.
- [AC cross-check] Re-read AC-1..AC-7 against items 1–7: filter by `_is_in_tab` (AC-1), plan line from `_plan_progress` with `kept_ids=[]` (AC-2, AC-3), plan-less (AC-4), moves off (AC-5), persistence incl. confirm URL (AC-6), unknown → all sizes, no plan line (AC-7). They agree; no changes needed.
- [Owner decision] 2026-10-06 — filter and left/over line work by plan band (≤15, 16–20, 21–25, 26–30); up/down moves, the position box and the Sort button are hidden while a band is shown, with a one-line note.

### Implementation (wave 35, branch card/192-arrange-size-filter)

- Route `arrange_puzzles_in_book` reads `?bucket=<label>` from `request.args` through the existing `_TABS_BY_LABEL`. No or unknown bucket = the page as before. A chosen band keeps rows by the existing `_is_in_tab` (after the page plan is computed over the whole book, so page labels and divider lines keep their printed numbers). Plan figures come from `_plan_progress(current_book, [])["tab_progress"]`, entry whose bucket is the band; `current_book` is re-read because a POST above may have changed the book. No new counting, no new thresholds, no move logic, no POST branch changed except the Remove confirm URL (carries `bucket`).
- Template: `.tabs`/`.tab` plain GET links in a `<nav aria-label="Filter by longest side">` (no role=tablist); plan line `p.stat-line#bandPlan` with the existing `.stat-cell`/`.stat-caption`/`.stat-sep` classes; over = word + `data-over="true"`; moves, position box and header Sort button hidden while a band is shown; Remove and title stay. No CSS change to admin.css.
- No new endpoint (server-rendered page; no API/contract work). No I/O added beyond the route's existing `_plan_progress` read.
- Scope: Touches only app.py, book_arrange_puzzles.html, tests/test_book_arrange_size_filter.py (new). admin.css not needed. No SCOPE+ entries.

[Owner default] plan bands (<=15, 16–20, 21–25, 26–30) — implemented as drafted
[Owner default] moves, position box and Sort hidden while a band is shown — implemented as drafted

Deviations to review (small, flagged here rather than silently chosen):
- The card says "Print setup (step 1)". The stepper numbers Print setup as step 2 (General info is step 1), so the sentence uses `stepper.book_step_number(1)`, which prints 2. The number shown is the true step number.
- Total figure: a tier says "(on plan)" when exact; the total says nothing when exact, so the card example `Total 50 / 50` reads literally, and it carries "(N left)"/"(N over)" when not exact.
- Plan-less book: counts only, sentence "This book has no distribution plan yet, so only the member counts are shown. Set the plan in Print setup (step 2) to see planned vs selected."

[Mutant] filter inverted (`not _is_in_tab`) → killed by ShowsOnlyTheChosenBucket::test_the_chosen_band_lists_only_its_rows, PropertyBandIsExactlyItsMembers
[Mutant] out-of-range row shown under every band (`except SizeOutOfRange: return True`) → killed by ShowsOnlyTheChosenBucket::test_a_size_outside_the_supported_range_is_under_no_band, PropertyBandIsExactlyItsMembers
[Mutant] unknown bucket falls back to first band → killed by UnknownBucketMeansAllSizes::test_a_bucket_that_names_no_band_lists_everything_and_shows_no_plan_line, test_an_empty_bucket_is_the_same_as_none, ShowsOnlyTheChosenBucket::test_with_no_bucket_all_three_are_listed
[Mutant] ungraded rows dropped under a band → killed by ShowsOnlyTheChosenBucket::test_an_ungraded_row_in_the_band_is_shown_under_the_ungraded_heading
[Mutant] plan line reads the first band's figures → killed by PlanLineShowsLeftAndOver::test_the_line_reads_left_over_and_on_plan_per_level, SameNumbersAsSelectionTab
[Mutant] plan line from whole-book progress → killed by PlanLineShowsLeftAndOver::test_the_line_reads_left_over_and_on_plan_per_level, SameNumbersAsSelectionTab, PlanLessBookShowsCountsOnly
[Mutant] plan line reads a stale (pre-POST) book → killed by FilterSurvivesTitleAndRemove::test_confirming_a_remove_comes_back_still_filtered (total 2 / 3 after the removal)
[Mutant] left gap also at zero (`gap >= 0`) → killed by PlanLineShowsLeftAndOver::test_the_line_reads_left_over_and_on_plan_per_level, test_only_the_over_figure_carries_the_over_marker
[Mutant] over gap also at zero (`gap <= 0`) → killed by PlanLineShowsLeftAndOver::test_the_line_reads_left_over_and_on_plan_per_level, test_only_the_over_figure_carries_the_over_marker
[Mutant] over marker on every planned figure → killed by PlanLineShowsLeftAndOver::test_only_the_over_figure_carries_the_over_marker
[Mutant] total says "(on plan)" too → killed by PlanLineShowsLeftAndOver::test_the_line_reads_left_over_and_on_plan_per_level, test_only_the_over_figure_carries_the_over_marker
[Mutant] moves not hidden while filtered → killed by MovesOffWhileFiltered::test_the_filtered_page_has_no_reorder_control_and_says_so
[Mutant] position box not hidden while filtered → killed by MovesOffWhileFiltered::test_the_filtered_page_has_no_reorder_control_and_says_so
[Mutant] Sort button not hidden while filtered → killed by MovesOffWhileFiltered::test_the_filtered_page_has_no_reorder_control_and_says_so
[Mutant] Remove button hidden while filtered → killed by MovesOffWhileFiltered::test_the_filtered_page_has_no_reorder_control_and_says_so
[Mutant] reorder-off line text removed → killed by MovesOffWhileFiltered::test_the_filtered_page_has_no_reorder_control_and_says_so
[Mutant] confirm URL drops the band → killed by FilterSurvivesTitleAndRemove::test_removing_asks_with_a_confirm_action_that_carries_the_band
[Mutant] aria-current dropped from the band link → killed by FilterSurvivesTitleAndRemove::test_saving_a_title_comes_back_still_filtered, test_confirming_a_remove_comes_back_still_filtered
[Mutant] "All sizes" marked is-current while a band is shown → killed by ShowsOnlyTheChosenBucket::test_the_chosen_band_lists_only_its_rows
[Mutant] level heading shows the level count, not shown → killed by ShowsOnlyTheChosenBucket::test_each_level_says_how_many_of_it_is_shown
[Mutant] empty-level sentence on every level in a band → killed by ShowsOnlyTheChosenBucket::test_each_level_says_how_many_of_it_is_shown
[Mutant] plan-less sentence removed → killed by PlanLessBookShowsCountsOnly::test_counts_with_no_planned_figure_and_a_pointer_to_print_setup (first run this survived: the stepper also names Print setup; the test was tightened to the sentence)
[Mutant] plan-less figure prints a planned slot → killed by PlanLessBookShowsCountsOnly::test_counts_with_no_planned_figure_and_a_pointer_to_print_setup
Result: 23 of 23 mutants killed in the final run. Mutant runner: scratchpad card192_mutants.py (restores the files; hashes verified after each run).

Edge bounds: the out-of-range claim is bounded by the exception-branch mutant (killed) and by the property corpus, which includes MIN_SIZE-1 and MAX_SIZE+1 rows (both 9 and 31 are generated). The 9-sided row is covered only through the seeded corpus, not a dedicated named test.

[Flake] none observed. The known flake (test_book_ready_gate.py::…test_save_plan_returns_the_book_to_draft[db-ready_for_pdf]) was not run.

Test evidence (literal pytest output):
- tests/test_book_arrange_size_filter.py: `38 passed in 4.08s` (-v per class: ShowsOnlyTheChosenBucket 12, PlanLineShowsLeftAndOver 6, SameNumbersAsSelectionTab 2, PlanLessBookShowsCountsOnly 2, MovesOffWhileFiltered 4, FilterSurvivesTitleAndRemove 6, UnknownBucketMeansAllSizes 4, PropertyBandIsExactlyItsMembers 2; each class x memory and db)
- Guardrails with the new file: `268 passed in 12.88s` (test_book_arrange_size_filter, test_book_level_order, test_book_arrange_position, test_book_arrange_page_breaks, test_book_select_tabs, test_books_list_plan_stats, test_book_arrange_sort_by_size)

[Render] ~/Documents/nonogram-reviews/CARD-192/arrange-all.png (unfiltered, 1280px)
[Render] ~/Documents/nonogram-reviews/CARD-192/arrange-16-20-left-over.png (16-20 band, "Easy 3 / 4 (1 left)", "Medium 5 / 4 (1 over)", reorder-off line; 1280px)
[Render] ~/Documents/nonogram-reviews/CARD-192/arrange-planless-filtered.png (plan-less book, 16-20 band, 1280px)
[Render] ~/Documents/nonogram-reviews/CARD-192/arrange-16-20-phone.png (16-20 band at 390px)
Renders are PNG screenshots from headless Chromium (playwright) of the real app served on loopback in memory mode; the horizontal overflow check reads 0px at both widths. The owner's visual check is still pending.

DESIGN-REGISTER: band-link strip (`nav` of `.tabs`/`.tab` plain links, aria-current) — arrange page, above the level list — "All sizes" plus one link per plan band; the current one is marked; no new CSS.
DESIGN-REGISTER: band plan line (`p.stat-line#bandPlan`, `.stat-cell[data-over]`) — arrange page, shown only when a band is chosen — per-level "(N left)" / "(N over)" / "(on plan)" in words, over also data-over; plan-less variant shows counts only.
DESIGN-REGISTER: reorder-off note (`p#reorder-off`) — arrange page, when a band is chosen — states why moves, position box and Sort are absent.
DESIGN-REGISTER: "(N shown of M)" level heading — arrange page level headings, when a band is chosen.
DESIGN-REGISTER: "No puzzles of this size in this level." empty-level note — arrange page, a level with no row in the band.
DESIGN-REGISTER: plan-less sentence (Print setup pointer) — arrange page plan line, when the book has no stored plan.

Open for reviewer: the owner's pre-merge visual check of the four renders; the "Total" and "(step 2)" deviations above.

[Scope] src/nonogram/admin/app.py, src/nonogram/admin/templates/book_arrange_puzzles.html, tests/test_book_arrange_size_filter.py
[Build gate] PASSED (full, 829.6s/13:49) — 6596 passed, 9 skipped, 0 failed (main's wave-34 baseline: 6498 passed, 9 skipped). Known flake test_book_ready_gate.py db-ready_for_pdf did not fail.
[System contract] section fresh — system_rules.py --card CARD-192 returns the same 52 ids as the card's section (no refresh needed).
[Review sync] 1 report(s) → meta/review/
[Review 1/3] Score: 9.2 — crit: 0, imp: 0
[Review 1/3] Score: 9.2 ✓ threshold reached + no critical/important
[Review 1/3] Mutation check: 4 of 23 re-derived by reviewer (inverted filter, Remove confirm URL drops bucket, gap>0→>=0, moves-off guard) — all matched the card's mutant log
[8h spot-check] 1/3 reproduced (CON-015: LOOPBACK_HOST at app.py:372 and create_app().run(host=LOOPBACK_HOST) at app.py:5665 unchanged by the diff; TestAdminPanel_BindsLoopbackOnlyByDefault 7 passed)
[8h spot-check] ✗ ADR-0006/R1 not reproduced as cited — the conclusion holds (diff adds no third-party import), but the check ref TestDependencyBaseline_IsExactlyPillowAndNumpy names no collected test (docstring only, tests/test_export_pdf.py:1250); the live guard is tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed (1 passed). OUT-OF-SCOPE: the system-rule check ref is stale in the model — route: architect (fix the ADR-0006 check ref), not this card.
[8h spot-check] ✗ CON-011 not reproduced as worded — "the diff defines no new size-range check" holds for production code; the test helper in_band() uses MIN_SIZE/MAX_SIZE as an oracle (test code, not production). The check ref PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30 is a docstring; the live test is test_every_source_mode_rejects_every_side_outside_ten_to_thirty (3 passed). OUT-OF-SCOPE: stale check ref in the model, same route as ADR-0006/R1.
[Review 1/3] ⚠ Step 8h holds failed re-derivation (ADR-0006/R1, CON-011) — next cycle re-checks these two verdicts against the live test names; no code change is requested.
[Review sync] 1 report(s) → meta/review/ (cycle 2)
[Review 2/3] Score: 9.2 — crit: 0, imp: 0 (holds re-derived against live test names; both stale check refs are out-of-scope model observations)
[Review 2/3] Minor: reorder-off line reads "Show all sizes to move puzzles or sort them." — card quotes "Show all sizes to move puzzles."; the added clause is accurate (Sort is hidden too). Kept as built; owner's visual check of record.
[Review 2/3] Out-of-scope (model): ADR-0006/R1 and CON-011 check refs are docstrings, not collected tests; re-point to test_the_dependency_baseline_is_still_closed and test_every_source_mode_rejects_every_side_outside_ten_to_thirty. Route: architect. Tooling gap: system_rules.py --verify-refs accepts docstring mentions.
[Review 2/3] Out-of-scope (card text): "Print setup (step 1)" — stepper prints step 2; implementation correct.
[Review 2/3] Mutation check: 6 of 6 re-run mutants killed (filter inverted, confirm URL drops band, unknown bucket to first band, left gap at zero, Sort not hidden, empty-level note on every level).
[AC/EC check] All criteria/constraints ✓ (evidence, no EC section on this card; G verified):
  AC-1 ✓ demonstrated — ShowsOnlyTheChosenBucket::test_the_chosen_band_lists_only_its_rows, test_with_no_bucket_all_three_are_listed (38 passed, both modes)
  AC-2 ✓ demonstrated — PlanLineShowsLeftAndOver::test_the_line_reads_left_over_and_on_plan_per_level (exact line), test_only_the_over_figure_carries_the_over_marker
  AC-3 ✓ demonstrated — SameNumbersAsSelectionTab::test_the_arrange_line_and_the_selection_tab_agree_tier_by_tier
  AC-4 ✓ demonstrated — PlanLessBookShowsCountsOnly::test_counts_with_no_planned_figure_and_a_pointer_to_print_setup
  AC-5 ✓ demonstrated — MovesOffWhileFiltered::test_the_filtered_page_has_no_reorder_control_and_says_so
  AC-6 ✓ demonstrated — FilterSurvivesTitleAndRemove (title save and confirmed remove both return filtered to 16-20; confirm action carries bucket=16-20)
  AC-7 ✓ demonstrated — UnknownBucketMeansAllSizes::test_a_bucket_that_names_no_band_lists_everything_and_shows_no_plan_line
  G-1 ✓ demonstrated — test_book_level_order, test_book_arrange_position, test_book_arrange_page_breaks pass
  G-2 ✓ demonstrated — route calls _plan_progress(current_book, []); no new bucket literal in the app.py diff
  G-3 ✓ demonstrated — test_book_select_tabs, test_books_list_plan_stats pass
  G-4 ✓ demonstrated — POST move/position/sort bodies untouched; only the Remove confirm URL changed
  G-5 ✓ demonstrated — writes only under POST; no PDF/baseline files in the diff
  Pytest: tests/test_book_arrange_size_filter.py "38 passed"; guardrail set (5 files, 197 tests) "197 passed in 7.70s".
[Docs] skipped — no directory structure or purpose change (tests/README.md does not list test files; no README in src/nonogram/admin).
[Commit] no new code to commit: implementation is 04791f4 (tests + app.py + template). Worktree paths outside meta/ are clean. Trailer on 04791f4 reads Co-Authored-By: Claude Sonnet 5, not the Opus 5.5 the brief names; not amended (rule: never --amend). Dispatcher to decide at done.
[Success] SUCCESS COMMIT = 04791f4. Review score 9.2 (cycle 2/3, 0 critical/important). Card status review.

- [Merge gate] rebased onto c0fcfbb; full suite 6596 passed, 9 skipped, exit 0 (775s, under the lock). Owner: "merge now, check later" (renders in ~/Documents/nonogram-reviews/CARD-192/). Merged da93164.
