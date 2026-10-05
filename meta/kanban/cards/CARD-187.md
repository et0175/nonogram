# CARD-187: The puzzle player shows the percent of correctly marked cells next to the error counter

**Status:** ready
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
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_percent.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
     default (b): label and placement.)
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
- (b) Label "Progress: N%", placed after "Errors: N" and "Hints: N".
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

- G-1: Every existing player test stays green unchanged: `tests/test_puzzle_solver_page.py`, `tests/test_puzzle_solver_marking.py`, `tests/test_puzzle_solver_progress.py`, plus CARD-182's `tests/test_puzzle_solver_phone.py`, CARD-183's `tests/test_puzzle_solver_hint.py` and CARD-186's tests. That includes `test_the_count_is_a_live_region` (the error counter keeps `role=status` and reads exactly "Errors: 0"), EC-036/EC-037, AC-311 and AC-319.
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
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium… (check: review-lens)
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

- **FR-044** (puzzle player, AC-296..AC-323, EC-035..EC-037). The progress ACs are AC-312..AC-317 with EC-036 (solved predicate) and EC-037 (error count). There is no AC for a percent. This card adds card-local ACs only.
- **ADR-0038** R1 (plain JS/CSS), R2 (no request per mark), R4 (pure state module), R6 (solution shipped only to the admin player; the percent needs it).
- **CON-021** (play only in the admin player, nothing persisted), CON-017.
- Components: COMP-008 area (admin panel adapter, `src/nonogram/admin/`). TERM-037 (puzzle player), TERM-038 (error count).
- Trace: owner's solver test doc 2026-10-05 item 3 → CARD-187 → FR-044 (extension, no AC id yet).

## Design context

- **Screen:** the admin puzzle player, `/puzzle/<id>/solve`: the toolbar's counter row ("Errors: N", "Hints: N", "Progress: N%").
- **Owner-visible defaults:** (a)–(c) in "What to implement": 100% when solved even with undecided whites, floor otherwise; the "Progress: N%" label and its place after the other counters; silent for screen readers. The owner confirms or overrides these from the renders before merge.
- **Renders:** ~/Documents/nonogram-reviews/CARD-187/ (owner visual check). PNG frames: 0%, part-way with errors and a hint, solved 100% (on a board with undecided whites, to show default (a)), each at desktop width and at 390 px.

## Worktree notes

- [Origin] Owner's solver test doc 2026-10-05, item 3: "Show % of solved cells, next to the error counter." Owner decision: correctly marked cells (dark or white matching the solution) / all cells; wrong marks and "?" don't count; 100% only when solved.
- [Spec] No FR AC covers a percent. The ACs are card-local. Raise an architect delta at the next pass: add an AC and an EC to FR-044 mirroring AC-1/AC-2 (definition + rounding), and TERM for "progress percent". Do not edit meta/ from the card.
- [Order] Depends on CARD-186 ("?" state; its constant name and its rule that "?" blocks solved are what AC-1/AC-3 use). CARD-183 (Hint, hint counter) and CARD-182 (tap targets, admin.css) are wave 34 and merge first. AC-4's Hint step and AC-5's DOM order assume CARD-183's `data-player-action="hint"` and `.player-hints`. Rebase on all three.
- [Facts] `isSolved` ignores EMPTY marks (a solved board may hold UNKNOWN whites). That is why the definition says "isSolved → 100" and does not rely on floor alone. With floor alone, a solved board would often show below 100. `correct === total` implies solved, so floor alone can never show 100 on an unsolved board.
- [Facts] The error counter's exact text is pinned: `test_the_count_is_a_live_region` asserts `#puzzle-player-errors` reads `["Errors:", "0"]`. So the percent must be its own element, not text added inside the errors `<p>`.
- [Facts] Harness to reuse: `browser_page`, `live`, `_open` (test_puzzle_solver_page.py ~561–598); `_cell`, `_drag`, `_button`, GRID 15×15 (test_puzzle_solver_marking.py); the pure-module corpus pattern `_corpus` / `_EVAL` / `_run_corpus` and `_set` (test_puzzle_solver_progress.py ~735–850); the no-request pattern of `TestSolverMarking_NoRequestPerMark` (test_puzzle_solver_marking.py:799). Mark browser tests `@pytest.mark.browser`.
- [AC cross-check] All ACs re-read against "What to implement": the rounding rule (solved → 100, else floor), "?" never correct, the update points (every commit, not the drag preview), the DOM order Errors → Hints → Progress, and the non-live element all agree. No edits were needed.
