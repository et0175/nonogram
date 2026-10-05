# CARD-183: The puzzle player gets a Hint button that reveals one deducible cell

**Status:** ready
**Priority:** P3
**Category:** feature
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/183-player-hint-button
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-05 (owner decision on IDEA-074: reveal one cell that line logic could deduce now, set to its correct state, counted as a hint, undoable)
**Idea:** IDEA-074
**Wave:** 34
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_hint.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).** The player page
(`/puzzle/<id>/solve`, `templates/puzzle_solve.html`) has three tools, Undo,
Redo, Reset and an error counter. There is no hint. FR-044's statement ends
"Hints are out of scope", and its comment block says "Hints are OUT of V1".
The owner has now decided to add one (2026-10-05).

- `static/solver_state.js` is the pure state module (ADR-0038/R4). It holds
  boards, strokes (`makeStroke` → frozen `{cells, state}`), the history
  (`record`, `undo`, `redo`) and progress (`errorCount`, `isSolved`). It has
  no line logic.
- `static/solver.js` is the renderer. `wireMarking` turns input into strokes
  and calls `commit`, which repaints, re-derives progress (`showProgress`),
  closes the reset confirmation and refreshes the controls.
- The payload already carries `rows`, `columns` (from `compute_clues`, the one
  encoder) and `solution` (admin only, ADR-0038/R6). A hint needs nothing new
  from the server.

**Target behaviour.**

1. **A line solver in `solver_state.js`.** Add a pure
   `lineForced(clue, cells)`. `clue` is one payload clue (`[0]` means an
   empty line). `cells` is one line of cell states. It returns the line with
   every cell that all valid placements agree on set to FILLED or EMPTY. It
   returns `null` when no placement fits. It is a native reimplementation of
   the same idea as `nonogram.solver.propagate.line_intersection`. Do not
   port its bitmasks. A plain DP over (position, run index), or a
   leftmost/rightmost-placement walk, is enough: lines are at most 30 cells
   (`limits.MAX_SIZE`).
2. **Which cells are "deducible now".** Add a pure
   `hintCell(board, rows, columns, solution)`:
   - Build the *knowns*. A cell is known when the player marked it correctly
     (FILLED where the solution is filled, EMPTY where it is empty). **Wrong
     marks count as undecided.** Undecided cells stay undecided.
   - Because the knowns agree with the solution, every line has at least one
     valid placement (the solution's own line), so `lineForced` never returns
     `null` here. The function must still handle `null` (treat it as "no
     deduction from this line").
   - A cell is *deducible* when it is UNKNOWN on the player's board and
     `lineForced` of its row or of its column, applied once to the knowns,
     forces it. This is one pass over each line, not propagation to a fixed
     point.
   - Return the first deducible cell in row-major order, as
     `{row, col, state, deduced: true}`. `state` is the forced state. It
     always equals the solution's state, because the solution fits every
     line. The function must still take `state` from the solution, not from
     the deduction.
   - **Fallback.** If no UNKNOWN cell is deducible, return the first UNKNOWN
     cell in row-major order with its solution state, as
     `{..., deduced: false}`.
   - If no cell is UNKNOWN, return `null`.
   - Clues come from the payload's `rows`/`columns`. They are never
     re-derived from the solution (ADR-0038/R3).
3. **A hint stroke.** Add `hintStroke(row, col, state)`. It returns a frozen
   stroke `{cells: [[row, col]], state, hint: true}`. `applyStroke`, `replay`,
   `record`, `undo` and `redo` stay as they are: they already ignore extra
   fields. So a hint is one stroke, one undo step, and EC-035 replay still
   holds. Add `hintCount(history)`: the number of `history.done` entries whose
   stroke has `hint === true`.
4. **The page (`solver.js`, `puzzle_solve.html`).**
   - Add a **Hint** button, `data-player-action="hint"`, in the
     `.player-history` group between Redo and Reset. It is a real button with
     an accessible name, reachable by Tab and working on Enter or Space, like
     the AC-310 controls.
   - Pressing it records `hintStroke` for `hintCell(...)` through the same
     `commit` path every stroke uses.
   - The button says `aria-disabled="true"` and does nothing when
     `hintCell` returns `null`, when the board is solved (locked), or during
     a drag.
   - Add a counter **"Hints: N"** next to "Errors:"
     (`data-player-hints`, in its own `role=status` element). N is
     `hintCount(history)`, re-derived on every commit like the error count.
   - The hinted cell carries `.is-hinted` until the next commit, so the player
     can see which cell changed. Style it with a token outline in `admin.css`.
     No animation runs under `prefers-reduced-motion` (the existing
     reduced-motion rule at `admin.css` ~line 480 must still cover it).
   - The live region `#puzzle-player-announce` (or the hint counter's own
     status) says what was revealed, e.g. "Hint: row 3, column 7 is black."
     When the fallback was used, it adds that no cell follows from one line
     right now (for example, "Hint: no cell follows from a single line yet;
     row 3, column 7 is black (from the solution).").
5. **How a hint meets the error count and the solved state.**
   - A hint only fills an UNKNOWN cell, with its correct state. So it never
     changes the error count: UNKNOWN never counted, and a correct mark never
     counts. Existing wrong marks stay on the board and keep counting.
   - A hint that completes the last solution-filled cell solves the puzzle.
     The solved state and the lock follow, exactly as for any stroke. Undoing
     a reset made from solved still brings the lock back (unchanged).
   - Undo removes the hinted mark and lowers the hint count by one. Redo puts
     both back.
   - Reset is a recorded stroke that keeps the history, so it does **not**
     clear the hint count. `setBoard` (the test seam) starts a new history, so
     the count reads 0 after it.

**Owner-visible defaults this card picks (say them at review, see Design context):**
- (a) Wrong marks are ignored when deducing, and the hint never touches them.
  The alternative is "a hint corrects a wrong mark first".
- (b) Row-major choice: the first deducible cell, top-left first.
- (c) Fallback to any undecided cell from the solution, labelled as such.
- (d) The hint count follows the undo history. Undo takes a hint back; reset
  does not clear the count. The alternative is a "hints used" total that
  never goes down.
- (e) Button placement and label (Hint, between Redo and Reset), the
  "Hints: N" counter, and the `.is-hinted` outline.

## Acceptance criteria

- **AC-1:** Given a seeded corpus of at least 2,000 lines (lengths 1–30, clues taken from random solution lines, knowns a random subset of that solution line, plus at least 200 lines whose knowns contradict their clue), when `lineForced` runs on each line in the browser, then its forced cells and its `null` verdicts match Python's `nonogram.solver.propagate.line_intersection` on every line. The minimum counts are asserted in the test.
  *test: PropertyTest_SolverHint_LineForcedMatchesThePythonLineSolver (in tests/test_puzzle_solver_hint.py)*
- **AC-2:** Given every line of length ≤ 12 in a seeded corpus of at least 500, when `lineForced` runs, then it equals the intersection of `tests/helpers/brute_force_oracle.py` `line_candidates` filtered by the knowns (`null` when none fit).
  *test: PropertyTest_SolverHint_LineForcedMatchesBruteForce (in tests/test_puzzle_solver_hint.py)*
- **AC-3:** Given a seeded corpus of at least 200 boards per shape over (10, 10), (15, 10), (10, 25) and (30, 30), mixing correct, wrong and undecided marks, when `hintCell` runs, then (i) it returns `null` iff no cell is UNKNOWN; (ii) otherwise the cell is UNKNOWN on the board and its state is the solution's; (iii) `deduced` is true, and the cell is the first row-major deducible cell, iff a Python oracle written in the test (correct marks only, one `line_intersection` pass per row and per column) finds one; (iv) otherwise it is the first UNKNOWN cell row-major. The test asserts minimums of ≥ 30 fallback cases, ≥ 50 boards with wrong marks, and ≥ 20 boards where a wrong mark hides a deduction.
  *test: PropertyTest_SolverHint_RevealsTheFirstDeducibleCell (in tests/test_puzzle_solver_hint.py)*
- **AC-4:** Given a blank 15×15 player page, when Hint is pressed by a real click, then exactly one cell changes. It is the cell the test's Python oracle names, with its solution state. The page shows "Hints: 1" and the error count is unchanged.
  *test: TestSolverHint_RevealsOneCell (in tests/test_puzzle_solver_hint.py)*
- **AC-5:** Given a board with two wrong marks (error count 2) set by `setBoard`, when Hint is pressed, then the wrong marks are unchanged, the error count still reads 2, and the revealed cell is the oracle's choice computed with the wrong marks ignored.
  *test: TestSolverHint_IgnoresWrongMarks (in tests/test_puzzle_solver_hint.py)*
- **AC-6:** Given a board where no UNKNOWN cell is line-deducible but some are UNKNOWN, when Hint is pressed, then the first UNKNOWN cell row-major gets its solution state and the announcement says it came from the solution.
  *test: TestSolverHint_FallsBackToTheSolution (in tests/test_puzzle_solver_hint.py)*
- **AC-7:** Given one hint after two ordinary strokes, when Undo is pressed once and then Redo once, then after the undo the cell is UNKNOWN again and "Hints: 0" shows; after the redo the cell is back and "Hints: 1" shows. Ctrl/Cmd+Z behaves the same.
  *test: TestSolverHint_IsOneUndoableStroke (in tests/test_puzzle_solver_hint.py)*
- **AC-8:** Given a board one solution-filled cell short of solved, whose missing cell is the next hint, when Hint is pressed, then the solved state appears, the board locks, and Hint says `aria-disabled="true"` and changes no cell when pressed again.
  *test: TestSolverHint_CanSolveAndThenLocks (in tests/test_puzzle_solver_hint.py)*
- **AC-9:** Given a board with no UNKNOWN cell that is not solved (every cell marked, some wrong), when the controls are read, then Hint says `aria-disabled="true"` and pressing it changes nothing.
  *test: TestSolverHint_DisabledWithNothingToReveal (in tests/test_puzzle_solver_hint.py)*
- **AC-10:** Given the player page, when Hint is reached by Tab and operated by Enter and by Space, then each press reveals one cell. It has the accessible name "Hint", and three hints issue no network request.
  *test: TestSolverHint_KeyboardAndNoRequest (in tests/test_puzzle_solver_hint.py)*
- **AC-11:** Given `prefers-reduced-motion: reduce`, when a hint is revealed, then no CSS animation or transition runs on the hinted cell or the toolbar.
  *test: TestSolverHint_ReducedMotion (in tests/test_puzzle_solver_hint.py)*
- **AC-12:** Owner render: a 15×15 board before, during (outline on the revealed cell, "Hints: 1") and after a fallback hint, at desktop width and at 390 px, saved in ~/Documents/nonogram-reviews/CARD-183/.
  *test: review-lens (owner visual check of the renders)*

## Guardrails

- G-1: Every existing player test stays green unchanged: `tests/test_puzzle_solver_page.py`, `tests/test_puzzle_solver_marking.py`, `tests/test_puzzle_solver_progress.py`. That includes EC-035 (`PropertyTest_SolverHistory_ReplayReproducesTheBoard`), EC-036/EC-037, AC-310 keyboard and labels, AC-311 no request per mark, AC-319 reduced motion, and the "banner takes the tools' place and the board does not move" test.
- G-2: ADR-0038/R4: all hint logic (`lineForced`, `hintCell`, `hintStroke`, `hintCount`) lives in `solver_state.js`, which keeps no DOM, globals or `import` (pinned by `test_the_state_module_touches_no_dom`). It also keeps no colour literals (`test_the_scripts_carry_no_colour_literals`).
- G-3: ADR-0038/R2 and R3: no network request per hint. The client uses the payload's clues and never re-derives clues from the solution. The payload shape (`test` at `test_puzzle_solver_page.py` ~line 227, "no more, no fewer keys") is unchanged.
- G-4: CON-021 / CON-017: no hint count or hint history is persisted or sent anywhere (no storage, no request).
- G-5: FR-044 behaviour is unchanged: the click cycle, drags, the error-count definition, the solved predicate, the lock, and the confirmed reset. A hint is an extra stroke kind, not a change to any of them.
- G-6: COMP-005 (`src/nonogram/solver/`) is not modified. It is only imported from the test tree as a cross-check oracle.
- G-7: The existing usage paragraph `#puzzle-player-hint` / `.player-hint` keeps its id, class and text. New names must not reuse "player-hint" (see Worktree notes).

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-183` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR-044** (puzzle player, AC-296..AC-323, EC-035..EC-037). Its statement says "Hints are out of scope". This card adds card-local ACs only. FR-044 probably wants an architect delta (see Worktree notes).
- **ADR-0038** R1 (plain JS, no framework or vendored lib), R2 (no request per mark), R3 (payload clues only), R4 (pure state module), R6 (solution shipped only to the admin player; the fallback depends on it).
- **CON-021** (play only in the admin player, nothing persisted, solution only for admin), CON-017, CON-015/CON-016.
- **CON-005 / COMP-005**: the uniqueness solver is unchanged. Its `line_intersection` is used only as a test oracle (legal from `tests/`, per CLAUDE.md's `mask_runs` precedent).
- Components: COMP-008 area (admin panel adapter, `src/nonogram/admin/`). TERM-037 (puzzle player), TERM-038 (error count), TERM-039 (stroke).
- Trace: IDEA-074 → CARD-183 → FR-044 (extension, no AC id yet).

## Design context

- **Screen:** the admin puzzle player, `/puzzle/<id>/solve`: the toolbar's history group and the counter row, plus the hinted cell's outline on the board.
- **Owner-visible defaults:** (a)–(e) in "What to implement": wrong marks ignored, row-major choice, labelled fallback, hint count that follows undo, and button, label and outline placement. The owner confirms or overrides these from the renders before merge.
- **Renders:** ~/Documents/nonogram-reviews/CARD-183/ (owner visual check). Include PNG frames or a short GIF: blank board → Hint → outline and "Hints: 1" → a fallback hint with its announcement → Undo. Show desktop width and 390 px, so the extra button and counter can be seen not to break the toolbar wrap.

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-074 "Online solver hint button", owner decision 2026-10-05: reveal one cell, an unknown cell line logic could deduce now, set to its correct state, counted as a hint, undoable.
- [Spec] There is no FR AC for hints. FR-044's statement says "Hints are out of scope" (requirements.yml ~line 3714), and its comment says "Hints are OUT of V1" (~line 3684). The ACs here are card-local. Raise an architect delta: amend FR-044's statement, and add ACs/an EC mirroring AC-1..AC-11, at the next architecture pass. Do not edit meta/ from the card.
- [Facts] `solver_state.js` may not contain the substring `import ` (test_puzzle_solver_page.py `test_the_state_module_touches_no_dom`). So the line solver cannot live in a separate module imported by solver_state.js. Put all of it in solver_state.js. No new static file is needed, so the wheel test at test_puzzle_solver_page.py ~line 501 and `pyproject.toml` package-data stay as they are.
- [Facts] The name "hint" is already taken by the usage paragraph `<p class="player-hint" id="puzzle-player-hint">`, which `wireMarking` un-hides (`solver.js` last lines of `wireMarking`). Use `data-player-action="hint"` for the button, and `.player-hints` / `data-player-hints` for the counter.
- [Facts] `record` drops a stroke that changes no cell. A hint always changes an UNKNOWN cell, so it is always a step. `applyStroke` ignores fields other than `cells`/`state`, so `hint: true` survives undo/redo inside `done`/`undone` with no change to the history code.
- [Facts] Python cross-check: `line_intersection(runs, length, known_filled, known_empty)` takes the canonical clue (`canonical_clue((0,)) == ()`) and bitmasks (bit i = cell i). It returns `(filled, empty, placements)` or `None`. Existing unit tests are in tests/test_solver.py ~line 483. The brute-force `line_candidates(clue, length)` is in tests/helpers/brute_force_oracle.py:77. It takes the non-canonical clue (`(0,)` for empty).
- [Facts] Browser harness to reuse: fixtures `browser_page`, `live`, `_open` (test_puzzle_solver_page.py ~561–598). Marking helpers (`_cell`, `_states`, `_button`, `_drag`, GRID 15×15) are in test_puzzle_solver_marking.py. The pure-module pattern is `page.evaluate("async (...) => { const S = await import('/static/solver_state.js'); ... }")`, as in test_puzzle_solver_progress.py `_PURE` / `_EVAL`. Mark tests `@pytest.mark.browser`.
- [Facts] For AC-6, build the fallback board from a known non-line-solvable configuration. One way: leave undecided only a 2×2 block whose two diagonals both fit their lines given everything else. Or find such a board by seeded search in the test and assert one was found. A blank board of a line-solvable puzzle will not trigger the fallback.
- [Conflict] CARD-182 also edits the player's CSS/JS. Overlap is likely in `admin.css` (the "Puzzle player" block, ~lines 433–480) and possibly `solver.js`/`puzzle_solve.html`. Rebase on whichever merges first. Keep this card's CSS to the new counter, the button's place in `.player-history`, and `.is-hinted`.
- [Future] The fallback reads the solution, which only the admin player may hold (ADR-0038/R6). A public player (IDEA-075) must replace the fallback, and any hint that uses the solution, with server-side or solution-free logic.
- [AC cross-check] All ACs re-read against "What to implement": the row-major choice, wrong marks ignored, fallback, `null` → disabled, hint count tied to undo, and the solved lock all agree. No edits were needed.
