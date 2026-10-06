# CARD-190: Puzzle review's size filter goes by the longest side, like book selection

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/190-review-filter-longest-side
**Worktree:** —
**Source:** owner admin-panel amendments, 2026-10-06 (owner request: "the cell-size filter from–to should work like book selection: filter by the LONGEST side from–to, not by either side"; owner decision: REPLACE the either-side behaviour — a 25×15 counts as 25 only — with the same wording as book selection)
**Idea:** —
**Wave:** 35
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/puzzle_review.py, src/nonogram/admin/templates/puzzles_list.html, tests/test_admin_filter_side_range_and_name.py
**Review score:** 9.5 (cycle 3/3)
**Started:** 2026-10-06T09:58:45Z
**Closed:** 2026-10-06T11:28:16Z
**Actual:** 0.2d
**Merge commit:** 22ce971
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**
The Puzzle review page is `GET /puzzles` (`app.py:puzzles_list`, template
`templates/puzzles_list.html`). Its "Size (cells), either side" field is two
number inputs, `size_from` and `size_to`.
- `app.py:_side_range_from_args` (line 1383) reads them into a `(low, high)` pair.
- `puzzles_list` (line 2175, passed at line 2216) and `api_puzzles` (line 5148)
  put that pair into `PuzzleFilter.side_range`.
- `PuzzleFilter.side_range` (`puzzle_review.py` line 111) matches a grid when
  *at least one* side is inside the range. Both stores do this:
  in-memory at lines 876-879 (`any(low <= side <= high ...)`), DB at lines
  998-1002 (`or_(width.between, height.between)`).
- So today a 25×15 is found by 10–15 *and* by 21–25.

**Book selection already has the longest-side filter.**
CARD-122 added `PuzzleFilter.longest_side_range` (`puzzle_review.py` line 163).
It matches on `max(width, height)`, in both stores:
in-memory at lines 883-889, DB at lines 1003-1017 (a `CASE`, so SQLite and
Postgres agree). A row with a side outside `MIN_SIZE..MAX_SIZE` matches no
range, the same verdict as `book_plan.bucket_of`. The book's tabs drive it
(`app.py` line 3962). Bounds go through the same `_side_bounds` validator.

**Target behaviour.** Reuse that one implementation. Do not write a second.
1. `_side_range_from_args` feeds `longest_side_range` instead of `side_range`,
   in both `puzzles_list` and `api_puzzles`. The URL parameters stay
   `size_from` / `size_to`, so bookmarks, pagination links (template line 7)
   and `return_to` redirects keep working and now mean "longest side".
   Rename the helper to say what it returns (e.g. `_longest_side_range_from_args`).
2. Remove `PuzzleFilter.side_range` once nothing sets it: the field and its
   comment, the `to_dict` / `from_dict` keys, the validation call (line 844),
   and both store branches (876-879, 998-1002). Update the `longest_side_range`
   comment (lines 147-162), which contrasts it with `side_range`.
   Leave `_side_bounds` as is; `longest_side_range` uses it.
3. Template (lines 52-60): label "Longest side (cells)", aria-labels
   "Longest side from" / "Longest side to". This is book selection's wording
   (its tablist is `aria-label="Longest side"`, its heading "Longest side
   <=15"). Keep the ids, names, `min`/`max` and the `MIN_SIZE-MAX_SIZE`
   placeholder.
4. Update the comment in `puzzles_list` (line 2173, "either side, from/to")
   and the docstring of `tests/test_admin_filter_side_range_and_name.py`.

**Tests that pin either-side and must be replaced** (all in
`tests/test_admin_filter_side_range_and_name.py`):
- `test_a_range_matches_when_either_side_falls_inside` — asserts either-side
  semantics outright. Delete; AC-1/AC-2 replace it.
- `test_a_longest_side_range_asks_about_max_width_height_not_either_side` —
  asserts `side_range` "still means what it meant". Drop the `side_range`
  half; keep the longest-side assertion.
- `test_an_open_bound_means_the_supported_limit` — builds `PuzzleFilter(side_range=...)`.
  Port to `longest_side_range` (its data gives the same answer).
- `test_an_impossible_range_is_reported_not_swallowed` — builds
  `PuzzleFilter(side_range=...)`. Fold its `(5, 5)` case into
  `test_an_impossible_longest_side_range_is_reported_too` and delete it.

## Acceptance criteria

- **AC-1:** Given the in-memory panel holding a 25×15 and a 15×12, when `/puzzles?size_from=10&size_to=15` is rendered, then only the 15×12 is listed and the header reads "Puzzles (1 total)"; and `/puzzles?size_from=21&size_to=25` lists only the 25×15.
  *test: TestPuzzleReview_SizeFilterUsesLongestSide (in tests/test_admin_filter_side_range_and_name.py, store = memory)*
- **AC-2:** Given the same two puzzles in the DB-backed panel (SQLite via `sqlite_session_scope`, built like CARD-160's `_build_app` in tests/test_puzzle_solver_page.py, asserting the store really is DB), when the same two URLs are rendered, then the lists and totals are the same as AC-1.
  *test: TestPuzzleReview_SizeFilterUsesLongestSide (in tests/test_admin_filter_side_range_and_name.py, store = sqlite)*
- **AC-3:** Given more matching puzzles than one page, all with longest side in range, plus wide rows whose short side only is in range, when `/puzzles?size_from=10&size_to=15&limit=2` is rendered, then the total counts only the longest-side members and the pagination links still carry `size_from=10&amp;size_to=15`.
  *test: TestPuzzleReview_SizeFilterPagesItsOwnMembers (in tests/test_admin_filter_side_range_and_name.py)*
- **AC-4:** Given the in-memory panel holding a 25×15 and a 15×12, when `/api/puzzles?size_from=10&size_to=15` is called, then the JSON lists only the 15×12.
  *test: TestPuzzlesApi_SizeRangeUsesLongestSide (in tests/test_admin_filter_side_range_and_name.py)*
- **AC-5:** Given `/puzzles` with no filters, when it is rendered, then the size field's label reads "Longest side (cells)", the two inputs carry aria-labels "Longest side from" / "Longest side to", and the words "either side" are not on the page.
  *test: TestPuzzleReview_SizeFilterLabelSaysLongestSide (in tests/test_admin_filter_side_range_and_name.py)*
- **AC-6:** `PuzzleFilter` no longer has a `side_range` field, and no code under `src/` builds or reads one; longest-side filtering exists only as `PuzzleFilter.longest_side_range`.
  *test: review-lens (grep `side_range` in src/ finds only `longest_side_range`; constructing `PuzzleFilter(side_range=...)` raises `TypeError`)*

## Guardrails

- G-1: Book selection is unchanged. `longest_side_range`'s semantics and both store branches stay as they are; `tests/test_book_select_tabs.py` (incl. `TestBookSelect_SizeRangeFilterReplacedByTab`, AC-216) and `tests/property/test_longest_side_buckets.py` (EC-024) pass unchanged.
- G-2: The existing longest-side tests in `tests/test_admin_filter_side_range_and_name.py` keep their assertions: `test_the_longest_side_range_pages_its_own_members_and_counts_them`, `test_a_row_outside_the_supported_range_belongs_to_no_longest_side_range`, `test_the_database_branch_of_the_longest_side_range_narrows_to_the_bucket`, and the book-tab sort tests.
- G-3: The input ids/names `size_from` / `size_to`, their `min`/`max` and placeholder stay. `tests/test_card_063_limits.py::test_the_puzzle_list_filter_renders_the_range` passes unchanged.
- G-4: The exact-extent `size` parameter and `PuzzleFilter.size` stay. `test_the_exact_size_parameter_still_works_for_the_api` passes unchanged.
- G-5: An inverted or out-of-range pair still shows "Filter error" on the page and a 400 from the API (`test_an_inverted_range_on_the_page_is_a_filter_error`).
- G-6: No other review-page filter, sort or pagination behaviour changes (`tests/test_puzzles_list_pagination.py`, `tests/test_card_066_status_filter.py` pass unchanged).

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-190` (54 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scala… (check: review-lens)
- ADR-0022/R2 — Each grid side is validated to 10..30 inclusive, as a pure domain function inward of the CLI adapter, for every source mode. The CLI parses the --size NxM form but nev… (check: test: TestValidateExtent_RejectsSideAboveThirty)
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
- ADR-0031/R2 — A solve that branched is reported as the `guess` strategy (solver.STRATEGY_GUESS) in FR-029's strategies list, never as a tier. (check: test: TestTiers_BranchingIsAStrategyNotATier)
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

- **FR:** — (the review list's size filter has no FR; owner request). Aligns the review page with FR-036's longest-side bucketing (TERM-027, EC-024); AC-216 (no size range on book selection) is untouched.
- **ADR:** ADR-0022/R1 (a grid's extent is two numbers — the exact-size check stays), ADR-0032 (the store's filter is the query, so LIMIT pages members)
- **CON:** CON-011 (supported side range via `nonogram.limits`)
- **Components:** COMP-009 (Admin Panel), COMP-010 (Persistence — DB branch of the same filter)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Screen:** Puzzle review list (`/puzzles`), filter bar, size field.
- **Owner-visible change:** label "Size (cells), either side" becomes "Longest side (cells)"; aria-labels "Side from/to" become "Longest side from/to". Layout, placeholder and field positions are unchanged. What the field returns changes (a 25×15 now appears only for ranges holding 25).
- **Renders:** ~/Documents/nonogram-reviews/CARD-190/ (owner visual check before merge): the filter bar with no filter, and with `size_from=21&size_to=25` over a corpus holding a 25×15 and a 15×12, in both stores' result lists.

## Worktree notes

- [Origin] Roadmap wave 1: — (owner request 2026-10-06, no IDEA). Owner decision: replace either-side with longest side; same wording as book selection.
- [Facts] Line numbers as of main 1f22c6a: `app.py` 1383-1387 (`_side_range_from_args`), 2173-2175 + 2216 (`puzzles_list`), 5148 (`api_puzzles`), 3962 (book tab uses `longest_side_range`); `puzzle_review.py` 105-111 (`side_range`), 147-163 (`longest_side_range` + comment), 169/190 (`to_dict`/`from_dict`), 788-806 (`_side_bounds`), 844-847 (validation), 876-889 (memory branches), 998-1017 (DB branches); `puzzles_list.html` 7 (pagination query) and 52-60 (the field).
- [Facts] Only two callers build `side_range`: `puzzles_list` and `api_puzzles`, both via `_side_range_from_args`. No template, doc or other test references `side_range`; book selection rejects `size_from`/`size_to` itself (`_RETIRED_SIZE_PARAMS`, app.py 3298) and is not affected.
- [Facts] `test_the_page_reads_from_and_to_and_keeps_them_in_pagination` (20×30 in 25–30) passes under both semantics, so it is not a discriminator; AC-1/AC-3 are. Keep it.
- [Scope] `/api/puzzles` follows the page because both share the helper; AC-4 pins that. If the owner wants the API kept on either-side, AC-4 and item 2 (removing `side_range`) change — see the open question in the hand-back.
- [AC cross-check] ACs re-read against the body: AC-1/2 = items 1-2 (both stores); AC-3 = the pagination link from template line 7; AC-4 = item 1's API half; AC-5 = item 3's wording; AC-6 = item 2. No disagreement found; nothing changed.
- [Owner decision] 2026-10-06 — /api/puzzles switches to longest side too (AC-4 stands; side_range removed); label "Longest side (cells)" confirmed.
- [Env] forge 2026.8.17
- [Owner default] /api/puzzles switches to longest side; label "Longest side (cells)" — implemented as drafted (owner decision 2026-10-06)
- [System contract] fresh lens (system_rules.py --card CARD-190) = card section, 54 rules — no refresh needed
- [Done] `/puzzles` and `/api/puzzles` feed `size_from`/`size_to` into `PuzzleFilter.longest_side_range` through the renamed `app.py:_longest_side_range_from_args`. URL params unchanged. `PuzzleFilter.side_range` is removed: the field, its comment, the `to_dict`/`from_dict` keys, the validation call and both store branches. The `longest_side_range` comment no longer contrasts with `side_range`. `_side_bounds` is untouched; its local parameter is still *named* `side_range`, which is the only non-`longest_side_range` hit for `grep side_range src/` (the card said to leave `_side_bounds` as is).
- [Done] Template label is now "Longest side (cells)" and the aria-labels are "Longest side from"/"Longest side to". Ids, names, min/max and placeholder are unchanged. Updated the `puzzles_list` comment and the test module docstring.
- [Done] tests/test_admin_filter_side_range_and_name.py: deleted `test_a_range_matches_when_either_side_falls_inside`. Removed the `side_range` half of `test_a_longest_side_range_asks_about_max_width_height_not_either_side`. Ported `test_an_open_bound_means_the_supported_limit` to `longest_side_range`. Folded `(5, 5)` into `test_an_impossible_longest_side_range_is_reported_too` and deleted `test_an_impossible_range_is_reported_not_swallowed`. Added TestPuzzleReview_SizeFilterUsesLongestSide (AC-1/AC-2, parametrised memory/sqlite through a local copy of CARD-160's `_build_app`, which asserts the store is the one named), TestPuzzleReview_SizeFilterPagesItsOwnMembers (AC-3, both stores), TestPuzzlesApi_SizeRangeUsesLongestSide (AC-4), TestPuzzleReview_SizeFilterLabelSaysLongestSide (AC-5) and `test_the_filter_has_no_either_side_field_any_more` (AC-6: no such dataclass field, and `PuzzleFilter(side_range=...)` raises TypeError).
- [Finding] AC-3's literal `size_from=10&amp;size_to=15` comes from the row actions' escaped `return_to` hidden input (`_puzzle_table.html`), not from the pagination links. The `preserve_filters` macro writes a raw `&` (`size_from=10&size_to=15`), so mutant M12 (pagination link drops size_to) survived the literal check alone. The AC-3 test now asserts both: the `&amp;` literal (return_to) and that every `page-link` href holds `size_from=10&size_to=15&`. The older `test_the_page_reads_from_and_to_and_keeps_them_in_pagination` has the same blind spot. I left it unchanged per G-2/G-6.
- SCOPE+ tests/test_card_065_follow_ups.py: `test_ac3_the_filters_are_labelled_in_cells[puzzles_list.html]` and `test_ac3_the_rendered_puzzle_filter_says_cells` asserted the literal "Size (cells)", which AC-5's mandated label cannot contain. I retargeted both asserts to "Longest side (cells)", which still pins the unit as cells, and added a one-line comment. No guardrail names these tests, and the card's [Facts] missed them.
- [Mutants] (run by scratchpad card190_mutants.py against the test file; every one killed)
- [Mutants] M1 memory longest branch back to either-side (`any(...)`): killed by TestPuzzleReview_SizeFilterUsesLongestSide::test_ten_to_fifteen…[memory], TestPuzzleReview_SizeFilterPagesItsOwnMembers[memory] and TestPuzzlesApi_SizeRangeUsesLongestSide
- [Mutants] M2 DB longest branch back to `or_(width.between, height.between)`: killed by TestPuzzleReview_SizeFilterUsesLongestSide::test_ten_to_fifteen…[sqlite] and TestPuzzleReview_SizeFilterPagesItsOwnMembers[sqlite]
- [Mutants] M3 memory `max(sides)` -> `min(sides)`: killed by both TestPuzzleReview_SizeFilterUsesLongestSide tests[memory] (incl. 21–25) and TestPuzzlesApi_SizeRangeUsesLongestSide
- [Mutants] M4 DB CASE picks the shorter side: killed by both TestPuzzleReview_SizeFilterUsesLongestSide tests[sqlite] and TestPuzzleReview_SizeFilterPagesItsOwnMembers[sqlite]
- [Mutants] M5 `puzzles_list` passes `longest_side_range=None`: killed by TestPuzzleReview_SizeFilterUsesLongestSide and TestPuzzleReview_SizeFilterPagesItsOwnMembers (both stores)
- [Mutants] M6 `api_puzzles` passes `longest_side_range=None`: killed by TestPuzzlesApi_SizeRangeUsesLongestSide
- [Mutants] M7 helper ignores `size_to`: killed by TestPuzzleReview_SizeFilterUsesLongestSide::test_ten_to_fifteen…, TestPuzzleReview_SizeFilterPagesItsOwnMembers and TestPuzzlesApi_SizeRangeUsesLongestSide
- [Mutants] M8 label reverted to "Size (cells), either side": killed by TestPuzzleReview_SizeFilterLabelSaysLongestSide. M9 label "Side (cells)": same. M10/M11 aria-label from/to reverted: same.
- [Mutants] M12 pagination macro drops `size_to`: killed by TestPuzzleReview_SizeFilterPagesItsOwnMembers (both stores). It survived before the href assertion was added; see [Finding].
- [Mutants] M14 `return_to` hidden input removed: killed by TestPuzzleReview_SizeFilterPagesItsOwnMembers
- [Mutants] M13 `side_range` field re-added to PuzzleFilter: killed by test_the_filter_has_no_either_side_field_any_more
- [Renders] ~/Documents/nonogram-reviews/CARD-190/ (.html + .png each), rendered from a live loopback server: {before,after}-nofilter-{memory,sqlite}, {before,after}-21-25-{memory,sqlite}, {before,after}-10-15-{memory,sqlite}. The corpus is a 25×15 and a 15×12. "before" is main's code (git archive of main). Before: 10–15 lists 2 and 21–25 lists 1. After: 10–15 lists only the 15×12 and 21–25 lists only the 25×15, in both stores. Label: "Size (cells), either side" became "Longest side (cells)", which fits the col-md-2 field at 1400px.
- [Tests] Targeted runs, 358 passed: test_admin_filter_side_range_and_name, test_book_select_tabs, property/test_longest_side_buckets, test_card_063_limits, test_puzzles_list_pagination, test_card_066_status_filter, test_cli, test_card_065_follow_ups, test_puzzle_review, test_admin_review_actions, test_admin_rename_strategies_batches, test_strategies, test_admin_tier_surfaces. test_admin_design_tokens also passes (6).
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/puzzle_review.py, src/nonogram/admin/templates/puzzles_list.html, tests/test_admin_filter_side_range_and_name.py, tests/test_card_065_follow_ups.py
- [Build gate] impact underivable (test_scope: full) — full suite
- [Scope gate] in_scope — 1 of 5 files outside Touches (tests/test_card_065_follow_ups.py, SCOPE+ recorded: label assertions AC-5 forces); comp_spread none (COMP-009 only); no sibling poached; no structural guardrails
- [Build gate] PASSED (full, 772s) — 6518 passed, 9 skipped
- [Review 1/3] Score: 9.5 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: 54/54 card rules have a verdict line (9 ✓, 45 ⚠ no_eligible_fact, 0 ✗); count line present
- [Review 1/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Review 1/3] mutation check: 9/9 killed (R1-R9, reviewer-run)
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0022/R1) — one fresh skeptic agent covering all three
- [AC/EC check] Failed: AC-6 ⚠ partial — TypeError half holds (test_the_filter_has_no_either_side_field_any_more PASSED), but the AC's literal check fails: grep -rn side_range src/ | grep -v longest_side_range still hits puzzle_review.py:780,788-790 (the local parameter name of _side_bounds(side_range)). AC-1..AC-5 ✓, G-1..G-6 ✓ (88 named tests passed)
- [Fix 1] AC-6: _side_bounds' local parameter renamed side_range → bounds (pure rename; message text unchanged). FIXED AC-6 — test: n/a (review-lens grep now empty). [Fix 1] declarations: 0 updated, 0 confirmed, 1 none
- [Build gate] PASSED (full, 786s; 6517 passed, 9 skipped, 1 flake) — test_admin_binding.py::TestAdminPanel_BindsLoopbackOnlyByDefault::test_the_port_stays_free_on_every_other_interface failed once (port 61651 taken on 192.168.0.109 by another process during the run — concurrent pipelines); file untouched by the card, fix delta is a parameter rename; re-run in isolation 3/3 green (33 passed each); passed in the gate-0 full run
- [Review 1/3] (re-entry after AC/EC fix, confirmation mode) Score: 9.7 — crit: 0, imp: 0; Step 8h coverage 54/54 (9 ✓, 45 ⚠, 0 ✗; 43 carried delta-clean); mutation +3/3 killed on renamed _side_bounds
- [Review sync] 2 report(s) → meta/review/
- [Review 1/3] Score: 9.7 ✓ threshold reached + no critical/important
- [Note] O-003: the worktree [Done] note saying _side_bounds' parameter is still named side_range is superseded by [Fix 1] (renamed to bounds)
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — TestPuzzleReview_SizeFilterUsesLongestSide::test_ten_to_fifteen_lists_only_the_15x12[memory] + ::test_twenty_one_to_twenty_five_lists_only_the_25x15[memory] PASSED
  AC-2 ✓ demonstrated — same two tests [sqlite] PASSED; _build_app asserts the DB store
  AC-3 ✓ demonstrated — TestPuzzleReview_SizeFilterPagesItsOwnMembers::test_the_total_counts_members_and_the_links_keep_the_range[memory]/[sqlite] PASSED
  AC-4 ✓ demonstrated — TestPuzzlesApi_SizeRangeUsesLongestSide::test_the_api_lists_only_the_15x12 PASSED
  AC-5 ✓ demonstrated — TestPuzzleReview_SizeFilterLabelSaysLongestSide::test_the_field_is_labelled_longest_side PASSED
  AC-6 ✓ demonstrated — grep -rn side_range src/ | grep -v longest_side_range empty; PuzzleFilter(side_range=...) raises TypeError; test_the_filter_has_no_either_side_field_any_more PASSED
  G-1 ✓ demonstrated — test_book_select_tabs.py 42 passed (incl. TestBookSelect_SizeRangeFilterReplacedByTab 3), property/test_longest_side_buckets.py 2 passed, both files unchanged
  G-2 ✓ demonstrated — the 3 named longest-side tests + 4 book-tab sort tests PASSED, bodies unchanged
  G-3 ✓ demonstrated — test_card_063_limits.py::test_the_puzzle_list_filter_renders_the_range PASSED, file unchanged
  G-4 ✓ demonstrated — test_the_exact_size_parameter_still_works_for_the_api PASSED, unchanged
  G-5 ✓ demonstrated — test_an_inverted_range_on_the_page_is_a_filter_error PASSED; API 400 + page 'Filter error' checked directly for 25/15, from=31, to=9
  G-6 ✓ demonstrated — test_puzzles_list_pagination.py 13 passed, test_card_066_status_filter.py 12 passed, both unchanged
- [8h spot-check] 3/4 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0022/R1)
- [8h spot-check] ✗ CON-011 not reproduced — the cited tests pass and _side_bounds enforces 10..30 today, but an edge mutant survives: changing the high-bound check to MAX_SIZE + 1 survives test_admin_filter_side_range_and_name.py, test_book_select_tabs.py and property/test_longest_side_buckets.py (no test pins high <= MAX_SIZE exactly, e.g. (None, 31) / (10, 31)); open-high → MAX_SIZE+50 survives the cited tests (killed only by uncited test_an_open_bound_means_the_supported_limit). The verdict's 'M1-M3 killed' are reviewer-local mutants that did not bound the high edge. → cycle 2
- [Review 2/3] Score: 9.5 — crit: 0, imp: 0 (full review; F-003 Minor: no test pins _side_bounds' 10..30 edge — E1/E4 edge mutants survive, pre-existing on main, behaviour correct by probe; F-002 Minor carried)
- [Review sync] 3 report(s) → meta/review/
- [Review 2/3] Step 8h coverage 54/54 (9 ✓ incl. CON-011 ✓ bounded with the edge gap stated, 45 ⚠, 0 ✗)
- [Review 2/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Docs] forge:readme: no README in src/nonogram/admin/ or templates/ (per-directory README convention is an open owner decision in the backlog); tests/README.md and docs/ hold no reference to side_range / 'either side' / 'Size (cells)' — nothing to update
- [8h spot-check] 3/4 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0022/R1 — caveat: verdict line's second test lives in test_admin_filter_side_range_and_name.py, not test_grid_dimensions.py)
- [8h spot-check] ✗ CON-011 not reproduced — the stated limit (edge not pinned; E1/E4 survive, E2/E3 equivalent), the cited line and the g5 probe all re-derive, but the cited 'tests/property/test_grid_dimensions.py 46 PASSED (this run)' does not: that file collects 22 tests (22 passed). → cycle 3
- [Review 3/3] Score: 9.5 — crit: 0, imp: 0 (full review; every count tied to a named command; F-002/F-003 Minor still open; O-004/O-005 out of scope)
- [Review sync] 4 report(s) → meta/review/
- [Review 3/3] Step 8h coverage 54/54 (9 ✓, 45 ⚠, 0 ✗); the cycle-2 '46' traced to a two-file run misattributed to test_grid_dimensions.py
- [Review 3/3] Score: 9.5 ✓ threshold reached + no critical/important
- [8h spot-check] 4/4 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0022/R1, CON-011 — CON-011 included beyond the cap as the twice-contested rule)
- [AC/EC check] cycle-3 success path: tree identical to the one the second AC/EC check verified (puzzle_review.py sha1 95a84bd8…, no other change) — that evidence (AC-1..AC-6, G-1..G-6 ✓ demonstrated) stands for this tree
- [Commit] success commit 1eaefac on card/190-review-filter-longest-side (implementation ef30b40 + AC-6 rename 1eaefac); diff vs main: 5 files, +154 −73
- [Merge gate] rebased onto 527e9c3; full suite 6518 passed, 9 skipped, exit 0 (822s, under the lock). Owner: "merge now, check later" (renders in ~/Documents/nonogram-reviews/CARD-190/). Merged 22ce971.
