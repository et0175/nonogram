# CARD-187: The puzzle player shows the percent of correctly marked cells next to the error counter

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/187-player-percent-solved
**Worktree:** —
**Source:** owner's solver test doc 2026-10-05, item 3 (owner decision: correctly marked cells / all cells; wrong marks and "?" don't count; 100% only when solved)
**Idea:** —
**Wave:** 35
**Depends on:** CARD-186
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_percent.py, tests/test_puzzle_solver_marking.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-10-06T11:43:45Z
**Closed:** 2026-10-06T16:55:12Z
**Actual:** 0.6d
**Merge commit:** b291141
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).** The player page
(`/puzzle/<id>/solve`, `templates/puzzle_solve.html`) shows one counter,
`<p class="player-errors" id="puzzle-player-errors" role="status"
aria-atomic="true">Errors: <span data-player-errors>0</span></p>` (template
line 70). CARD-183 (wave 34) adds "Hints: N" (`.player-hints`,
`data-player-hints`, its own `role=status`) next to it. There is no progress
figure.

- `static/solver_state.js` has the progress functions `errorCount(board,
  solution)` and `isSolved(board, solution)` (lines ~297–319). `isSolved`
  needs every solution-filled cell FILLED and no solution-empty cell FILLED.
  EMPTY marks are optional: a solution-empty cell may stay UNKNOWN on a
  solved board.
- `static/solver.js` `showProgress()` (~line 251) re-derives the error count
  and the solved state from `history.board` on every `commit`. `commit` runs
  for every recorded change: click, drag release, Undo, Redo, Reset (a
  recorded `resetStroke`), the `setBoard` seam, and (after CARD-183) Hint.
  A drag's live preview goes through `show`, not `commit`, so progress does
  not change mid-drag. It writes the counter only when its text changed, so
  the live region does not re-announce.

**Target behaviour.**

1. **A pure function in `solver_state.js`.** Add
   `solvedPercent(board, solution)`, returning an integer 0..100.
   - A cell is *correct* when it is FILLED and its solution is filled, or
     EMPTY and its solution is empty.
   - UNKNOWN, a wrong mark, and CARD-186's "?" state are never correct.
   - **Rounding rule:** if `isSolved(board, solution)` is true, return 100.
     Otherwise return `floor(100 × correct / (width × height))`.
   - Why this is safe: `correct === width × height` means every cell matches,
     which implies solved. So an unsolved board always gets at most 99. 99.9%
     shows as 99, never 100. 100% appears exactly when the puzzle is solved.
   - Why the solved override: a solved board may leave white cells
     undecided (FR-044 AC-316). Without it, the page would show "Solved"
     next to, for example, "64%". The owner said "100% only when solved".
     The card reads that as "100% exactly when solved". (Owner-visible
     default (a).)
   - Integer maths only in the definition: compute `Math.floor((100 *
     correct) / total)`. Grids are at most 30×30 (`limits.MAX_SIZE`), so this
     is exact. The test checks it against Python's `100 * correct // total`.
   - It reads only the current board, like `errorCount`: never a running
     total.
2. **The page.**
   - Add `<p class="player-progress" id="puzzle-player-progress">Progress:
     <span class="player-progress-count" data-player-progress>0%</span></p>`
     in the counter row. DOM order: Errors, then Hints (CARD-183), then
     Progress. All three stay together on the row's right side. (Owner-visible
     default (b): label and placement.) _Amended 2026-10-06 (owner decision,
     "accept as built"): visually Progress sits LEFT of Errors (the counters
     are drawn right to left so "Hints: N" keeps the toolbar's right end,
     CARD-183's test), and where the row has no room (~1280 px) Progress
     wraps onto a line below, on the right; DOM order stays Errors → Hints →
     Progress._
   - `showProgress()` sets it to `solvedPercent(history.board,
     payload.solution) + "%"`, writing only when the text changed (same
     pattern as the error count). So it follows every mark, drag release,
     Undo, Redo, Hint, Reset and `setBoard`, and not the drag preview.
   - Style `.player-progress` / `.player-progress-count` like
     `.player-errors` / `.player-errors-count` (`admin.css` ~lines 451–452):
     tokens only, tabular numerals, no colour literals. It must not break the
     toolbar wrap at 390 px.
3. **Screen readers are not flooded.** The percent changes on almost every
   mark, so it is **not** a live region. `#puzzle-player-progress` has no
   `role=status`/`role=alert`, no `aria-live` other than `off`, and no live
   ancestor. It is read on demand. Nothing new is written to
   `#puzzle-player-announce` for a percent change. The solved announcement
   stays as it is. (Owner-visible default (c). The other option, announcing
   at milestones such as 25/50/75%, is not built.)
4. **No network, no storage.** The percent is derived in the browser from
   the current board and the payload's solution (ADR-0038/R2, R6). Nothing is
   sent or stored. Persistence of the board (a separate card for item 1)
   needs nothing from this card: the percent is re-derived on load.

**Owner-visible defaults this card picks (say them at review, see Design context):**
- (a) Solved shows 100% even if some white cells are still undecided.
  Otherwise the rule is floor, so 99.9% shows 99%.
- (b) Label "Progress: N%". _Placement amended 2026-10-06 (owner decision): shown left of "Errors: N" / "Hints: N" (DOM order Errors → Hints → Progress), wrapping below on the right at ~1280 px; the original "placed after" is replaced._
  "Solved: N%" was avoided because the solved banner already reads
  "Solved: <name>".
- (c) The percent is silent for screen readers. It is not announced on change.

## Acceptance criteria

- **AC-1:** Given a seeded corpus of at least 200 boards per shape over (10, 10), (15, 10), (10, 25) and (30, 30), mixing UNKNOWN, correct, wrong and "?" cells, solved boards (with and without undecided whites) and near-misses, when `solvedPercent` runs in the browser, then it equals a Python oracle written in the test: 100 if the board is solved by the cell-by-cell rule, else `100 * correct // (width * height)`. The test asserts minimums of ≥ 50 solved boards, ≥ 30 solved boards with an undecided white, and ≥ 50 boards containing "?".
  *test: PropertyTest_SolverPercent_MatchesTheDefinition (in tests/test_puzzle_solver_percent.py)*
- **AC-2:** Given explicit 30×30 boards, when `solvedPercent` runs, then: a blank board gives 0; an unsolved board with 899 of 900 cells correct (the one miss is a solution-filled cell left UNKNOWN) gives 99, not 100; the same board with a wrong mark in place of the miss gives 99; a solved board with every white undecided gives 100; and every unsolved board in AC-1's corpus gives at most 99.
  *test: TestSolverPercent_FloorsAndReaches100OnlyWhenSolved (in tests/test_puzzle_solver_percent.py)*
- **AC-3:** Given a board, when one UNKNOWN cell is changed to "?", then the percent is unchanged. Given every solution-filled cell FILLED and one solution-empty cell marked "?", then the percent is below 100 and the solved state does not appear.
  *test: TestSolverPercent_QuestionMarksNeverCount (in tests/test_puzzle_solver_percent.py)*
- **AC-4:** Given a blank 15×15 player page, when a correct click, a drag (the percent is read during the preview and after release), Undo, Redo, Hint, Reset with confirm, Undo of that reset, and `setBoard` are done in turn, then after each recorded step the shown "Progress: N%" equals the test's Python oracle on the page's board, and it does not change during the drag preview.
  *test: TestSolverPercent_FollowsEveryRecordedChange (in tests/test_puzzle_solver_percent.py)*
- **AC-5:** Given the player page at desktop width and at 390 px, when the counter row is read, then `#puzzle-player-progress` comes after `#puzzle-player-errors` and the hint counter in DOM order, reads "Progress: 0%", sits on the same row as the error counter at desktop width, and the page has no horizontal scroll at 390 px.
  *test: TestSolverPercent_SitsNextToTheCounters (in tests/test_puzzle_solver_percent.py)*
- **AC-6:** Given the player page, when `#puzzle-player-progress` and its ancestors are inspected and five ordinary marks are made, then none of them has `role` status/alert/log or an `aria-live` other than `off`, and `#puzzle-player-announce` stays empty through the five marks.
  *test: TestSolverPercent_DoesNotFloodScreenReaders (in tests/test_puzzle_solver_percent.py)*
- **AC-7:** Given a loaded player page, when 20 strokes of clicks and drags are made and the percent changes, then the browser issues no network request.
  *test: TestSolverPercent_NoRequestPerMark (in tests/test_puzzle_solver_percent.py)*
- **AC-8:** Owner render: a 15×15 board at 0%, part-way (with errors and a hint shown), and solved at 100%, at desktop width and at 390 px, saved in ~/Documents/nonogram-reviews/CARD-187/.
  *test: review-lens (owner visual check of the renders)*

## Guardrails

- G-1: Every existing player test stays green unchanged: `tests/test_puzzle_solver_page.py`, `tests/test_puzzle_solver_marking.py`, `tests/test_puzzle_solver_progress.py`, plus CARD-182's `tests/test_puzzle_solver_phone.py`, CARD-183's `tests/test_puzzle_solver_hint.py` and CARD-186's tests. That includes `test_the_count_is_a_live_region` (the error counter keeps `role=status` and reads exactly "Errors: 0"), EC-036/EC-037, AC-311 and AC-319. _Amended 2026-10-06 (owner decision on the CARD-187 escalation): one exception — `tests/test_puzzle_solver_marking.py::TestSolverMarking_RevealsNoCorrectness` may strip the progress count in `_STRIPPED`, docstring "Narrowed again by CARD-187: the progress % reveals progress by the owner's choice, like the error count". No other player test changes._
- G-2: ADR-0038/R4: `solvedPercent` lives in `solver_state.js`, with no DOM, globals, colour literals or the substring `import ` (`test_the_state_module_touches_no_dom`, `test_the_scripts_carry_no_colour_literals`).
- G-3: The definitions of `errorCount` and `isSolved` do not change. `solvedPercent` calls `isSolved`; it does not copy or alter it.
- G-4: ADR-0038/R2 and CON-021: no request per mark and no new payload key (the "no more, no fewer keys" payload test in `test_puzzle_solver_page.py` ~line 227 stays green).
- G-5: The solved banner, its announcement in `#puzzle-player-announce`, the lock, and the reduced-motion rule (`admin.css` ~line 479) are unchanged.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-187` (52 rules). A projection — fix the source artifact, never this list._

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

- **Formalized 2026-10-06:** FR-044 AC-351..AC-354, EC-045

- **FR-044** (puzzle player, AC-296..AC-323, EC-035..EC-037). The progress ACs are AC-312..AC-317 with EC-036 (solved predicate) and EC-037 (error count). There is no AC for a percent. This card adds card-local ACs only.
- **ADR-0038** R1 (plain JS/CSS), R2 (no request per mark), R4 (pure state module), R6 (solution shipped only to the admin player; the percent needs it).
- **CON-021** (play only in the admin player, nothing persisted), CON-017.
- Components: COMP-008 area (admin panel adapter, `src/nonogram/admin/`). TERM-037 (puzzle player), TERM-038 (error count).
- Trace: owner's solver test doc 2026-10-05 item 3 → CARD-187 → FR-044 (extension, no AC id yet).

## Design context

- **Screen:** the admin puzzle player, `/puzzle/<id>/solve`: the toolbar's counter row ("Errors: N", "Hints: N", "Progress: N%").
- **Owner-visible defaults:** (a)–(c) in "What to implement": 100% when solved even with undecided whites, floor otherwise; the "Progress: N%" label and its place (amended 2026-10-06: left of the other counters visually, DOM after them, wrapping below at ~1280 px); silent for screen readers. The owner confirms or overrides these from the renders before merge.
- **Renders:** ~/Documents/nonogram-reviews/CARD-187/ (owner visual check). PNG frames: 0%, part-way with errors and a hint, solved 100% (on a board with undecided whites, to show default (a)), each at desktop width and at 390 px.

## Worktree notes

- [Origin] Owner's solver test doc 2026-10-05, item 3: "Show % of solved cells, next to the error counter." Owner decision: correctly marked cells (dark or white matching the solution) / all cells; wrong marks and "?" don't count; 100% only when solved.
- [Spec] No FR AC covers a percent. The ACs are card-local. Raise an architect delta at the next pass: add an AC and an EC to FR-044 mirroring AC-1/AC-2 (definition + rounding), and TERM for "progress percent". Do not edit meta/ from the card.
- [Order] Depends on CARD-186 ("?" state; its constant name and its rule that "?" blocks solved are what AC-1/AC-3 use). CARD-183 (Hint, hint counter) and CARD-182 (tap targets, admin.css) are wave 34 and merge first. AC-4's Hint step and AC-5's DOM order assume CARD-183's `data-player-action="hint"` and `.player-hints`. Rebase on all three.
- [Facts] `isSolved` ignores EMPTY marks (a solved board may hold UNKNOWN whites). That is why the definition says "isSolved → 100" and does not rely on floor alone. With floor alone, a solved board would often show below 100. `correct === total` implies solved, so floor alone can never show 100 on an unsolved board.
- [Facts] The error counter's exact text is pinned: `test_the_count_is_a_live_region` asserts `#puzzle-player-errors` reads `["Errors:", "0"]`. So the percent must be its own element, not text added inside the errors `<p>`.
- [Facts] Harness to reuse: `browser_page`, `live`, `_open` (test_puzzle_solver_page.py ~561–598); `_cell`, `_drag`, `_button`, GRID 15×15 (test_puzzle_solver_marking.py); the pure-module corpus pattern `_corpus` / `_EVAL` / `_run_corpus` and `_set` (test_puzzle_solver_progress.py ~735–850); the no-request pattern of `TestSolverMarking_NoRequestPerMark` (test_puzzle_solver_marking.py:799). Mark browser tests `@pytest.mark.browser`.
- [AC cross-check] All ACs re-read against "What to implement": the rounding rule (solved → 100, else floor), "?" never correct, the update points (every commit, not the drag preview), the DOM order Errors → Hints → Progress, and the non-live element all agree. No edits were needed.
- [Env] forge 2026.8.17
- [BLOCKER] guardrail conflict: G-1 vs AC-4 — tests/test_puzzle_solver_marking.py::TestSolverMarking_RevealsNoCorrectness::test_marking_all_but_the_last_solution_cell_changes_nothing_but_cell_states (CARD-161 G-2, already narrowed by CARD-162 and CARD-188) asserts that correct marks which do not yet solve the puzzle change nothing in body.outerHTML except data-state / aria-pressed / aria-disabled / is-circled. AC-4 (FR-044 AC-351) requires "Progress: N%" to follow every recorded change, so the same correct marks necessarily change the text of [data-player-progress]: the feature is, by owner decision, a display of correctness. Verified as the sole cause: with the percent write in showProgress disabled the test passes (3 passed); with it enabled it fails (1 failed, 2 passed). G-1 forbids narrowing that test ("stays green unchanged ... do not weaken, retarget"). Not dodged by writing the percent through CSSOM / an <html> custom property — that would hide correctness from the test while showing it on screen. Proposed resolution (the precedent of CARD-162 and CARD-188): narrow _STRIPPED in that test to also strip the progress count, e.g. `.replace(/(data-player-progress="?"?>)\d+%/, '$1')`, and amend its docstring "Narrowed again by CARD-187: the progress percent is a view of correctness by owner decision (FR-044 AC-351)". Needs the orchestrator/owner to lift G-1 for that one test.
- [Partial work committed] solvedPercent in solver_state.js (calls isSolved; errorCount/isSolved untouched), the counter wiring in solver.js showProgress (written only when its text changes; not a live region; nothing written to #puzzle-player-announce), the template element and its CSS. tests/test_puzzle_solver_percent.py is NOT written yet; no mutants run yet; no owner renders yet.
- [Layout finding — needs owner eyes] Two other G-1 tests constrain where "Progress: N%" can go: TestSolverHint_PlacesTheButtonAndTheCounter pins "Hints: N" at the toolbar's right end (1440 and 390 px), and TestSolverMaybe_FourToolsKeepOneToolbarRowAt1280 needs tools + history + Errors + Hints on one row at 1280 x 720, where there is no room for a third counter (toolbar 980 px; 176 px left after the tools and history; the three counters need ~264). Implemented: the three counters share a new wrapper .player-counters (no role) holding .player-counters-pair (Errors, Hints) and then Progress, laid out row-reverse + wrap with flex-basis 0. Result: at 1440 one line reading Progress, Errors, Hints (Hints at the right end); at 1280 Errors + Hints stay on the toolbar row and Progress drops onto a line below them, at the right. DOM order is Errors, Hints, Progress (AC-354 as formalized), but VISUALLY Progress is left of Errors — a deviation from owner default (b)'s "placed after", forced by CARD-183's right-end test. The toolbar now aligns items to the top of the row (align-items: flex-start, was center) and the pair is as tall as a .btn (calc(2 * 0.4rem + 2 * var(--border-width) + 1.5rem)) so the 1280 one-row test still sees one row (measured: buttons 148..186.78, counters 149.39..185.39, same centre). With these changes every other existing player test passed in a run before the pair-height fix (2 failed, 286 passed: the conflict test above and the 1280 row test); after the fix the 1280 test passes (targeted run: 1 failed [the conflict test], 2 passed).
- SCOPE+ none (all changes are in the card's Touches files).
- [Escalated] 2026-10-06 implementation blocker — station: decompose. G-1 requires tests/test_puzzle_solver_marking.py::TestSolverMarking_RevealsNoCorrectness::test_marking_all_but_the_last_solution_cell_changes_nothing_but_cell_states to stay green unchanged; AC-4 (FR-044 AC-351) requires "Progress: N%" to change on exactly those correct non-solving marks. Orchestrator verified the test exists as described and is the CARD-161 G-2 test already narrowed by CARD-162/CARD-188. Route: amend G-1 to except that one test (allow narrowing its _STRIPPED to drop the progress count, docstring "Narrowed again by CARD-187"), then /kanban review CARD-187 (partial work kept at 2c01f7f, worktree kept). Also needs owner view: layout default (b) could not hold under CARD-183/CARD-186 G-1 tests — Progress renders LEFT of Errors (and wraps below at 1280), not after Hints; decide whether to relax those tests or accept.
- [Owner decision] 2026-10-06 — the % may reveal progress (G-1 narrowed as above); layout accepted as built: Progress left of Errors (DOM order Errors → Hints → Progress), wrapping below on the right at ~1280 px; default (b) "Progress after Hints" replaced.
- [Resumed] 2026-10-06 after owner decision — implementation agent resumed from 2c01f7f (same agent, context kept); card text (item 2, default (b), Design context) aligned with the accepted layout.
- [Review entry] 2026-10-06 — implementation committed (2c01f7f, fc3f647); review cycle 1 started; full-suite gate running under the lock. Worktree notes synced from the worktree (CARD SYNC PROTOCOL step 2).
- [Review sync] 1 report(s) → meta/review/ (20261006T131252Z-CARD-187-cycle1.yml; validated as parsable YAML).
- [Review 1/3] Score: 8 — crit: 0, imp: 1 (F-1: unmeasured align-items change on .player-toolbar), minor: 3 (F-2 visual/DOM order, owner-accepted; F-3 comment outruns its assertions; F-4 tautological corpus-size check). G-1 and G-5 both ⚠ partial (reviewer ran a subset, not the full guarded set). AC-8 ⚠ partial (owner visual sign-off pending, expected).
- [Severity gate 1/3] Score >= threshold (8 >= 8) but 0 critical / 1 important findings — fix mandatory. Resuming: dispatch forge:fix for F-1..F-4, then a full re-run of G-1/G-5's complete guarded test set and the full-suite gate under the lock, then review cycle 2.
- [Fix 1] 2026-10-06 — fix commit 728c7d0 (test/comment only; no production CSS or JS changed). Fix agent a5ae9408a07615d92 closed F-1 (new TestSolverPercent_AlignItemsFlexStartKeepsHistoryAndSlotAtTheirRowsTop and TestSolverPercent_SolvedBannerNeverOverlapsTheNewCounters), F-3 (test_hints_and_errors_share_the_row_at_1440, test_pair_is_as_tall_as_a_toolbar_button), F-2 (puzzle_solve.html comment, no code change), F-4 (corpus-shrink comment). ⚠ The agent terminated on an API spend-limit error before it delivered its FIXED/DECLARATIONS lines, so there is no FIXED-line contract to run; the orchestrator verified the diff directly instead.
- [Fix 1 verification] orchestrator-run: tests/test_puzzle_solver_percent.py 22 passed. Mutant spot-checks: align-items reverted to center → TestSolverPercent_AlignItemsFlexStart…[chromium-1280-720] FAILED; pair min-height removed → test_pair_is_as_tall_as_a_toolbar_button FAILED; both restored clean.
- [Build gate] PASSED (full, 1111.73s; full suite under meta/kanban/.full-suite.lock, released after): 6547 passed, 9 skipped, 0 failed, exit 0 (output: scratchpad card187_full_suite.out). This full run is also the G-1/G-5 suite-wide evidence: it includes every guarded player file (page, marking, progress, phone, hint, maybe) and the card's percent file.

[Notes sync 2026-10-06] worktree notes pulled into main (CARD SYNC step 2):
- [Resumed 2026-10-06] after the owner decision: G-1 narrowing applied to tests/test_puzzle_solver_marking.py::TestSolverMarking_RevealsNoCorrectness (`_STRIPPED` also strips the count inside `[data-player-progress]`, docstring "Narrowed again by CARD-187: the progress % reveals progress by the owner's choice, like the error count"). No other existing player test changed.
- [Tests] tests/test_puzzle_solver_percent.py: test_PropertyTest_SolverPercent_MatchesTheDefinition (EC-045 / AC-1; 300 boards per shape over 10x10, 15x10, 10x25, 30x30; asserted minimums: >= 200 boards, >= 50 solved, >= 30 solved with an undecided white, >= 50 with "?", >= 30 solved boards whose cell floor is < 100, and >= 10 unsolved 30x30 boards at 99), TestSolverPercent_FloorsAndReaches100OnlyWhenSolved (AC-2), TestSolverPercent_QuestionMarksNeverCount (AC-3), TestSolverPercent_FollowsEveryRecordedChange (AC-4, plus "an unchanged percent is not rewritten" via MutationObserver), TestSolverPercent_SitsNextToTheCounters (AC-5: DOM order; "Progress: 0%"; tabular numerals and the error count's font/size/colour at 1440/1280/390; same row and left of Errors at 1440; at 1280 below the pair, at the toolbar's right end, buttons at the toolbar's top, pair centred on the buttons' row; no horizontal scroll at 390), TestSolverPercent_DoesNotFloodScreenReaders (AC-6), TestSolverPercent_NoRequestPerMark (AC-7), TestSolverPercent_IsRightAfterAReloadRestoresTheBoard (CARD-185 reload). Note on AC-4: one correct cell of 225 floors to 0%, so the click step asserts 0 == oracle; the drag (15 cells) moves it to 6–7%.
- [Results] tests/test_puzzle_solver_percent.py: 16 passed. All player tests (tests/test_puzzle_solver_*.py): 304 passed, 1 warning in 301.62s.
- [Mutants] (scratchpad card187_mutants.py; each restored after its run; expected outcome met for all 26):
- [Owner default] (a)/(c) — implemented as drafted; (b) per owner decision 2026-10-06 (Progress left of Errors, DOM order Errors → Hints → Progress, wraps below at the right at ~1280 px).
- [Renders] ~/Documents/nonogram-reviews/CARD-187/: 01-blank-0pct-{1440,1280,390}.png, 02-partway-errors-hint-{1440,1280,390}.png (Errors 2, Hints 1, Progress 32%), 03-solved-100pct-undecided-whites-{1440,1280,390}.png (every white undecided, Progress 100%). Heights 900 / 800 / 844; no console errors or warnings during rendering.
- DESIGN-REGISTER: player toolbar counters — new `.player-counters` (no role; flex row-reverse, wrap, flex-basis 0) holding `.player-counters-pair` (Errors, Hints; as tall as a toolbar .btn) and `.player-progress` / `.player-progress-count` ("Progress: N%", non-live, styled like the error count: --font-num, tabular-nums, --text-base, --color-text; label --text-sm --color-text-secondary). Visual order Progress, Errors, Hints (Hints at the toolbar's right end); at ~1280 px Progress wraps below the pair at the right. `.player-toolbar` items now align to the row's top (align-items: flex-start).
- [Comments re-checked] admin.css / template / solver.js / solver_state.js comments narrowed to what the tests bound (1440 same line, 1280 drop-below and centring, non-live, announce untouched, ≤ 99 unsolved).
- [Review sync] 1 report(s) → meta/review/ (20261006T163140Z-CARD-187-cycle2.yml; validated as parsable YAML).
- [Review 2/3] Score: 9 — crit: 0, imp: 0, minor: 2 (C2-1 WCAG 1.3.2 rationale for the visual-vs-DOM order is a record gap, owner-accepted; C2-2 admin.css comment cites TestSolverPercent_SitsNextToTheCounters for Hints at the right end, which only test_puzzle_solver_hint.py:612 asserts). Confirmation mode over fix delta 728c7d0. F-1 (important) closed. G-1 ✓ fresh 288/288 on the complete guarded set; G-5 ✓ fresh (34 solved/lock/reduced subset + sweep + long-name + hidden-tools); AC-1..7, EC-045, G-2..G-4 ✓; AC-8 ⚠ owner visual sign-off pending (renders in ~/Documents/nonogram-reviews/CARD-187/).
- [Severity gate 2/3] no critical/important findings — success path. Minor C2-1, C2-2 left open (comment-only, do not gate). Verdicts come from the cycle-2 review agent's own fresh runs; the AC/EC/G gate was not run as a separate agent.
- [Docs step] forge:readme skipped: no file or directory added or removed except tests/test_puzzle_solver_percent.py (new, in tests/); tests/README.md does not enumerate player test files, so it is current.
- [Success] branch head 728c7d0 is the success commit (fix commit after review cycle 1 folded into the card's commit series: 2c01f7f, fc3f647, 728c7d0). No code left uncommitted in the worktree; the meta/ review reports and card are not committed (meta excluded).
- [AC/EC check] All criteria/constraints ✓ (evidence, cycle-2 gate over commit 728c7d0):
- AC-1 ✓ demonstrated — evidence: tests/test_puzzle_solver_percent.py::test_PropertyTest_SolverPercent_MatchesTheDefinition PASSED (file run: 22 passed).
- AC-2 ✓ demonstrated — evidence: ::TestSolverPercent_FloorsAndReaches100OnlyWhenSolved::test_explicit_boards and ::test_no_unsolved_board_reads_100 PASSED.
- AC-3 ✓ demonstrated — evidence: ::TestSolverPercent_QuestionMarksNeverCount::test_an_undecided_cell_marked_maybe_leaves_the_percent and ::test_one_maybe_on_a_white_blocks_100 PASSED.
- AC-4 ✓ demonstrated — evidence: ::TestSolverPercent_FollowsEveryRecordedChange::test_every_step and ::test_an_unchanged_percent_is_not_rewritten PASSED.
- AC-5 ✓ demonstrated — evidence: ::TestSolverPercent_SitsNextToTheCounters (test_order_text_and_style[1440/1280/390], test_same_row_left_of_errors_at_1440, test_below_the_pair_at_the_right_at_1280, test_no_horizontal_scroll_at_390, test_hints_and_errors_share_the_row_at_1440, test_pair_is_as_tall_as_a_toolbar_button) PASSED.
- AC-6 ✓ demonstrated — evidence: ::TestSolverPercent_DoesNotFloodScreenReaders::test_silent PASSED.
- AC-7 ✓ demonstrated — evidence: ::TestSolverPercent_NoRequestPerMark::test_twenty_strokes PASSED.
- AC-8 ⚠ partial — owner visual check pending (renders: ~/Documents/nonogram-reviews/CARD-187/, 9 PNGs at 1280/1440/390). Not a code gap.
- EC-045 ✓ demonstrated — evidence: test_PropertyTest_SolverPercent_MatchesTheDefinition PASSED (4 shapes, seeded corpus, minimums asserted in the body).
- G-1 ✓ demonstrated — evidence: complete guarded player set 288 passed, 0 failed (cycle-2 run); full suite 6547 passed, 9 skipped, 0 failed, exit 0. Only edit to an existing test: the approved _STRIPPED narrowing in tests/test_puzzle_solver_marking.py.
- G-2 ✓ demonstrated — evidence: TestPlayerAssets::test_the_state_module_touches_no_dom and ::test_the_scripts_carry_no_colour_literals PASSED.
- G-3 ✓ demonstrated — evidence: errorCount and isSolved bodies unchanged in the branch diff; solvedPercent calls isSolved.
- G-4 ✓ demonstrated — evidence: TestSolverPage_ShowsTheClues::test_the_payload_has_exactly_the_documented_shape[memory] and [sqlite] PASSED.
- G-5 ✓ demonstrated — evidence: solved/lock/banner/reduced-motion subset 34 passed; BoardDoesNotMoveOnSolveAtAnyWidth::test_sweep, LongNameBanner::test_wraps, HiddenToolsAreOutOfReachWhenSolved::test_out_of_reach PASSED.
Epistemics: the per-item lines are from the cycle-2 review agent's runs of these named tests; the orchestrator re-ran only tests/test_puzzle_solver_percent.py (22 passed) and the full suite (6547 passed).
  M01 drop isSolved override — KILLED by test_PropertyTest_SolverPercent_MatchesTheDefinition, FloorsAndReaches100…::test_explicit_boards
  M02 Math.round — KILLED by property, test_explicit_boards, test_no_unsolved_board_reads_100
  M03 Math.ceil — KILLED by property, test_explicit_boards, test_no_unsolved_board_reads_100
  M04 "?" counts as correct — KILLED by property, QuestionMarksNeverCount (both tests)
  M05 "?" on a white counts (edge) — KILLED by property, QuestionMarksNeverCount::test_one_maybe_on_a_white_blocks_100
  M06 UNKNOWN on a white counts — KILLED by property, test_explicit_boards
  M07 a wrong black counts — KILLED by property
  M08 Math.trunc (equivalent for non-negatives) — survived, as expected
  M09 percent written in the drag preview (show) — KILLED by FollowsEveryRecordedChange::test_every_step
  M10 unconditional write — KILLED by FollowsEveryRecordedChange::test_an_unchanged_percent_is_not_rewritten
  M11 percent written to #puzzle-player-announce — KILLED by DoesNotFloodScreenReaders::test_silent
  M12 percent never written — KILLED by test_every_step, test_an_unchanged_percent_is_not_rewritten, NoRequestPerMark, IsRightAfterAReload…
  M13 not shown at load (0% after reload) — KILLED by IsRightAfterAReloadRestoresTheBoard::test_reload
  M14 role=status on the counter — KILLED by test_silent
  M15 aria-live=polite on .player-counters — KILLED by test_silent
  M16 aria-live=off on the counter (edge, allowed) — survived, as expected
  M17 Progress before the pair in the DOM — KILLED by SitsNextToTheCounters (order at 1440/1280/390, left-of at 1440, below-the-pair at 1280)
  M18 counters not row-reverse — KILLED by test_same_row_left_of_errors_at_1440, test_below_the_pair_at_the_right_at_1280
  M19 toolbar align-items: center again — KILLED by test_below_the_pair_at_the_right_at_1280
  M20 pair min-height removed — KILLED by test_below_the_pair_at_the_right_at_1280
  M21 proportional numerals — KILLED by test_order_text_and_style (3 widths)
  M22 counter 420px wide — KILLED by test_no_horizontal_scroll_at_390
  M23 counters wrapper nowrap — KILLED by test_below_the_pair_at_the_right_at_1280
  N1 a correct mark adds a class on the board (narrowing tight) — KILLED by RevealsNoCorrectness::test_marking_all_but_the_last_solution_cell_changes_nothing_but_cell_states
  N2 a correct mark writes the percent outside the count (title on the <p>, narrowing edge) — KILLED by the same test
  N3 a correct mark changes the errors text — KILLED by the same test
  The unmutated percent-only change passes that test (in the 304-pass run).
- [Merge gate] rebased onto 18baff0; full suite 6580 passed, 9 skipped, exit 0 (785s, under the lock). Owner: "merge now, check later" (renders in ~/Documents/nonogram-reviews/CARD-187/). Merged b291141.
