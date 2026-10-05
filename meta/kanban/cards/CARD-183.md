# CARD-183: The puzzle player gets a Hint button that reveals one deducible cell

**Status:** done
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
**Review score:** 9.0 (cycle 3/3)
**Started:** 2026-10-05T13:41:10Z
**Closed:** 2026-10-05T17:32:39Z
**Actual:** 0.5d
**Merge commit:** bd8eccb
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
- [Env] forge 2026.8.17
- [Owner default] (a)–(d) wrong marks ignored, row-major, labelled fallback, undo-tracked hint count — implemented as drafted. (e) Hints: N counter + .is-hinted outline as drafted; the Hint button is AFTER Reset, not between Redo and Reset (G-1 Tab-order test conflict — see the [Orchestrator] note); owner pre-merge decision
- [Built] solver_state.js: `lineForced(clue, cells)` (forward/backward reachability DP over (position, runs placed); null when no placement fits), `hintCell(board, rows, columns, solution)` (knowns = correct marks only; first row-major UNKNOWN cell forced by one pass over its row or column, else first UNKNOWN as `deduced: false`, else null; state always from the solution; a null line deduces nothing), `hintStroke(row, col, state)` (frozen stroke + `hint: true`), `hintCount(history)` (hint strokes on `done`). No change to applyStroke/record/undo/redo/replay.
- [Built] solver.js: `player.nextHint` (start() computes hintCell from the recorded board + payload rows/columns/solution); Hint click records hintStroke through the shared `commit`; `refresh` sets Hint `aria-disabled` = locked || gesture in progress || nextHint() null, and refresh now also runs at pointerdown and pointercancel so the gesture state shows; `commit(next, hint)` moves `.is-hinted` to the revealed cell (removed on the next commit); `showProgress` re-derives "Hints: N" and puts the hint text in #puzzle-player-announce unless that commit changed the solved state (then the solved text wins). Texts: "Hint: row R, column C is black|white." / "Hint: no cell follows from a single line yet; row R, column C is black|white (from the solution)."
- [Built] puzzle_solve.html: Hint button (`data-player-action="hint"`, text label, no icon — _icons.html has no fitting icon and is outside scope) and `<p class="player-hints" role="status">Hints: <span data-player-hints>`. admin.css: `.player-hints`/`.player-hints-count` (as the error counter), `.player-cell.is-hinted` (2px --color-accent outline inset by the major rule, inset --grid-paper ring, `player-hinted-in` outline-colour fade over 2×--duration-base; the existing reduced-motion rule covers it via `.player-stage *` — no change to that rule).
- [Owner default changed — (e) placement] Hint is the LAST button of `.player-history` (after Reset; DOM after the reset confirmation), not between Redo and Reset. Reason: G-1 — `test_puzzle_solver_marking.py::test_each_control_has_a_name_and_is_reachable_by_tab` collects the first six distinct controls reached by Tab and asserts they equal [Black, White, Undecided, Undo, Redo, Reset]; with Hint before Reset it reads [..., Redo, Hint] and fails (shown: moved Hint before Reset → `AssertionError: assert ['Black', 'Wh...Redo', 'Hint'] == ['Black', 'Wh...edo', 'Reset']`, restored). A CSS `order` hack would put visual order and focus order out of step (WCAG 2.4.3), so it was not used. No AC fixes the position. If the owner wants Hint between Redo and Reset, that test's CONTROLS list must be amended in a follow-up.
- [Owner-visible] At 390 px the Hint button wraps onto its own row under Undo/Redo/Reset, so the board starts one control row (~44 px) lower than on main (compare 01-before-main-blank-390.png with 02-blank-390.png). At 1440 everything stays on one row; "Hints: N" sits right of "Errors: N".
- [Results] `tests/test_puzzle_solver_hint.py tests/test_puzzle_solver_page.py tests/test_puzzle_solver_marking.py tests/test_puzzle_solver_progress.py` → `198 passed, 1 warning in 142.22s`. The three existing files are unchanged (176 passed on their own).
- [Mutation log] each mutant applied alone, the named tests run, then restored (runner: scratchpad card183/card183_mutate.py):
- M1 lineForced FILLED on canFill alone — KILLED by test_PropertyTest_SolverHint_LineForcedMatchesThePythonLineSolver
- M2 lineForced drops the separator check after a run — KILLED by ...LineForcedMatchesThePythonLineSolver
- M3 lineForced never returns null — KILLED by ...LineForcedMatchesThePythonLineSolver
- M4 lineForced fit edge `start + length <= n` → `<` — KILLED by ...LineForcedMatchesThePythonLineSolver
- M5 lineForced without `clue.filter(n > 0)` ([0] read as one run of length 0) — SURVIVED; equivalent mutant: a 0-length run consumes exactly one non-FILLED cell, which on lines of ≥ 1 cell admits the same placements as "no runs". Kept the filter for readability; no claim rests on it.
- M6 hintCell takes wrong marks at face value — KILLED by test_PropertyTest_SolverHint_RevealsTheFirstDeducibleCell (also targeted by TestSolverHint_IgnoresWrongMarks)
- M7 hintCell returns null when any line is null — KILLED by TestSolverHintModule::test_cases
- M8 hintCell state from the deduction instead of the solution — KILLED by TestSolverHintModule::test_cases
- M9 hintCell has no fallback (null) — KILLED by ...RevealsTheFirstDeducibleCell
- M10 fallback = last UNKNOWN cell — KILLED by ...RevealsTheFirstDeducibleCell
- M11 hintCell ignores column deductions — KILLED by ...RevealsTheFirstDeducibleCell
- M12 hintCell column-major order — KILLED by ...RevealsTheFirstDeducibleCell
- M13 hintCount counts every done stroke — KILLED by TestSolverHintModule::test_cases
- M14 hintStroke without hint: true — KILLED by TestSolverHintModule::test_cases
- M15 aria-disabled ignores the lock — KILLED by TestSolverHint_CanSolveAndThenLocks::test_locked_with_cells_still_undecided
- M16 aria-disabled ignores a gesture — KILLED by TestSolverHint_DisabledWithNothingToReveal::test_disabled_during_a_drag
- M17 aria-disabled ignores hintCell null — KILLED by TestSolverHint_DisabledWithNothingToReveal::test_no_undecided_cell
- M18 click handler ignores the lock — KILLED by TestSolverHint_CanSolveAndThenLocks::test_locked_with_cells_still_undecided
- M19 click handler ignores a gesture — KILLED by TestSolverHint_DisabledWithNothingToReveal::test_disabled_during_a_drag
- M20 no refresh at pointerdown — KILLED by ...test_disabled_during_a_drag
- M21 no refresh at pointercancel — KILLED by ...test_enabled_again_after_a_cancelled_drag
- M22 .is-hinted never added — KILLED by TestSolverHint_RevealsOneCell::test_one_click_reveals_the_oracles_cell
- M23 .is-hinted never removed — KILLED by TestSolverHint_RevealsOneCell::test_the_outline_moves_on_with_the_next_commit
- M24 fallback announced with the deduction text — KILLED by TestSolverHint_FallsBackToTheSolution
- M25 hint text overwrites the solved announcement — KILLED by TestSolverHint_CanSolveAndThenLocks::test_the_last_hint_solves
- M26 hint counter never re-derived — KILLED by TestSolverHint_RevealsOneCell::test_one_click_reveals_the_oracles_cell
- M27 reduced-motion rule without `.player-stage *` — KILLED by TestSolverHint_ReducedMotion::test_reduced_motion
- M28 .is-hinted without outline — KILLED by TestSolverHint_RevealsOneCell::test_the_hinted_cell_carries_an_accent_outline
- M29 .is-hinted without animation — KILLED by TestSolverHint_ReducedMotion::test_without_reduced_motion_the_hinted_cell_animates (the control that makes AC-11's zero meaningful)
- [Not tested / not claimed] The colour contrast of the outline on a black cell is shown only in the renders (03-after-one-hint-*.png, the revealed cell is black), not by a test; the CSS comment describes the rule and makes no visibility claim.
- [Console] Every render run asserted no console error/warning, page error, failed request or HTTP ≥ 400 on the player page (both widths, main and this branch).
- [Spec] Architect delta still owed (see [Spec] above): FR-044 "Hints are out of scope" contradicts this card; also record the changed default (e) Hint placement after Reset.
- DESIGN-REGISTER HistoryControls — gains Hint (`button[data-player-action="hint"]`, text label "Hint", no icon) as the last button of `.player-history`, after Reset (Tab order of the earlier controls unchanged); disabled = aria-disabled="true" while the board is solved (locked), while a pointer gesture is in progress, or when no cell is undecided; pressing it then changes nothing. Wraps to its own row at 390 px.
- DESIGN-REGISTER HintCounter — "Hints: N" right after "Errors: N" at the end of the toolbar row (`p.player-hints[role=status]`, `.player-hints-count`, styled as ErrorCounter); N = hint strokes on the undo stack: undo lowers it, redo raises it, reset keeps it, setBoard zeroes it.
- DESIGN-REGISTER PlayerBoard — new cell state `.is-hinted`: the cell the last hint revealed, until the next commit; 2px --color-accent outline inset by the major rule width with an inset --grid-paper ring, fading in over 2×--duration-base (`player-hinted-in`); no animation under prefers-reduced-motion. Tokens: --color-accent, --grid-paper, --duration-base, --ease.
- DESIGN-REGISTER SolvedBanner / live region — #puzzle-player-announce also carries the hint text ("Hint: row R, column C is black|white." or, on the fallback, "Hint: no cell follows from a single line yet; row R, column C is black|white (from the solution)."); a hint that solves the board announces the solved text instead.
- [Scope] src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_hint.py
- [Orchestrator] Owner default (e) deviation verified: Hint between Redo and Reset makes test_puzzle_solver_marking.py::test_each_control_has_a_name_and_is_reachable_by_tab (G-1, CONTROLS = [...,'Redo','Reset'], first-6-distinct Tab walk) collect 'Hint' instead of 'Reset'. Hint placed after Reset. Owner pre-merge decision: accept, or a follow-up changes that test's CONTROLS.
- [System contract] fresh assembly (52 rules) identical to the card section — no refresh
- [Build gate] PASSED (full, 650s) — 6445 passed, 9 skipped
- [Scope gate] cycle 1: in_scope (5 files, all in Touches; no guardrail hits)
- [Review 1/3] Score: 6.5 — crit: 0, imp: 3 (pre-adversarial; F-001 AC-3 hide predicate, F-002 outline test claims, F-003 position claims untested)
- [Review sync] 1 report(s) → meta/review/
- [Adversarial] F-001 CONFIRMED — seed 1833: 181 counted, 112 truly hide, 69 earlier-spurious (card183_skeptic_f001.py)
- [Adversarial] F-002 CONFIRMED — outline red, no offset, no ring: accent_outline test still 1 passed
- [Adversarial] F-003 CONFIRMED — no test checks Hint in .player-history after Reset, or .player-hints after .player-errors, nor any box axis
- [Review 1/3] after adversarial: crit 0, imp 3 confirmed → fix 1
- [Owner default note] F-006 (stale card note) corrected by the orchestrator in both card copies
- [Fix 1] pre-gate: named tests 4 passed (F-001, F-002, F-003 x2 widths); F-004 n/a (render); F-005 SKIPPED (two live regions required by item 4 + AC-6)
- [Fix 1] declarations: 0 updated, 0 confirmed-matrix, 4 doc/comment/notes narrowed-or-tested, 0 none — no production behaviour changed (tests, comments, renders only)
- [Renders] ~/Documents/nonogram-reviews/CARD-183/: 01-before-main-blank-{1440,390}.png (main's toolbar, before this card), 02-blank-{1440,390}.png, 03-after-one-hint-{1440,390}.png (outline on the revealed black cell, "Hints: 1", live-region text shown in a yellow render-only annotation bar), 04a-fallback-board-before-hint-{1440,390}.png (15×15 line-logic fixed point — [Fix 1] F-004: re-rendered on a unique 15×15 grid from a seeded search, scratchpad card183/card183_fallback15.py, seed 183, draw 43, 89 cells undecided; the AC-6 test itself still uses its 10×10 board), 04b-fallback-hint-with-announcement-{1440,390}.png (fallback announcement in the annotation bar; at 390 px the stage is scrolled so the revealed cell, row 1 column 14, is in view and the row clues are scrolled off), 05-after-undo-{1440,390}.png (cell undecided again, "Hints: 0").
- [Fix 1] review cycle 1 (meta/review/20261005T141509Z-CARD-183-cycle1.yml). Mutants applied one at a time and restored by rewriting the original text (runner: scratchpad card183/card183_mutate_fix1.py; file hashes compared before/after):
- [Fix 1] F-001 AC-3 now counts a board as "hidden" only when, wrong marks taken at face value, neither the revealed cell's row nor its column forces it (`_face_value_forces`). Seed 1833: 181 boards change the hint at face value, 112 truly hide the cell; asserted `hidden >= 20` and `changed > hidden`.
- [Fix 1] mutant F1a — test's `hidden` reverted to the weak predicate (face-value hint != want) — killed by test_PropertyTest_SolverHint_RevealsTheFirstDeducibleCell (`assert 181 > 181`)
- [Fix 1] mutant F1b (M6 re-run) — hintCell takes wrong marks at face value — killed by test_PropertyTest_SolverHint_RevealsTheFirstDeducibleCell
- [Fix 1] mutant F2a — outline colour --color-accent → --color-success — killed by TestSolverHint_RevealsOneCell::test_the_hinted_cell_carries_an_accent_outline
- [Fix 1] mutant F2b — outline-offset dropped — killed by ...test_the_hinted_cell_carries_an_accent_outline
- [Fix 1] mutant F2c — box-shadow paper ring dropped — killed by ...test_the_hinted_cell_carries_an_accent_outline
- [Fix 1] mutant F2d — ring colour --grid-paper → --color-accent-tint — killed by ...test_the_hinted_cell_carries_an_accent_outline
- [Fix 1] mutant F2e (edge) — ring width 2× → 1× the major rule — killed by ...test_the_hinted_cell_carries_an_accent_outline
- [Fix 1] mutant F2f (edge) — outline-offset −1× → −0.5× the major rule — killed by ...test_the_hinted_cell_carries_an_accent_outline
- [Fix 1] mutant F2g (edge) — outline width major rule → minor rule — killed by ...test_the_hinted_cell_carries_an_accent_outline
- [Fix 1] mutant F3a — Hint button moved before Reset — killed by TestSolverHint_PlacesTheButtonAndTheCounter::test_dom_order_and_boxes[1440 and 390]
- [Fix 1] mutant F3b — Hint button moved outside .player-history — killed by ...test_dom_order_and_boxes[1440 and 390]
- [Fix 1] mutant F3c — .player-hints moved before .player-errors — killed by ...test_dom_order_and_boxes[1440 and 390]
- [Fix 1] mutant F3d — .player-hints `order: -1` (DOM unchanged, visually first) — killed by ...test_dom_order_and_boxes[1440 and 390]
- [Fix 1] mutant F3e — .player-hints `flex-basis: 100%` (own row, DOM unchanged) — killed by ...test_dom_order_and_boxes[1440 and 390]
- [Fix 1] mutant F3f (edge) — .player-errors loses `margin-left: auto` (counters not at the toolbar's right end) — killed by ...test_dom_order_and_boxes[1440 and 390]
- [Fix 1] mutant F3g — Hint forced onto its own row at desktop width — killed by ...test_dom_order_and_boxes[1440]
- [Fix 1] mutant F3h — .player-history `flex-wrap: nowrap` (Hint stays on Reset's row at 390) — killed by ...test_dom_order_and_boxes[390]
- [Fix 1] F-005 skipped: the counter must stay its own role=status region (card item 4) and AC-6's announcement test reads #puzzle-player-announce; dropping either live region changes accepted behaviour. Two polite updates per hint remain (order not guaranteed).
- [Fix 1] Results: four player test files → `200 passed, 1 warning in 139.99s`.
- [Build gate] PASSED (full, 641s) — 6447 passed, 9 skipped
- [Scope gate] cycle 2: in_scope (same 5 files; no guardrail hits)
- [Review 2/3] Score: 7.5 — crit: 0, imp: 2 (pre-adversarial; F-009 outline docstring 'any other cell', F-010 'fading in' comment — both attributed to fix 1; F-001..F-004 resolved)
- [Review sync] 2 report(s) → meta/review/
- [Adversarial] F-009 CONFIRMED — mutant outlining the hinted cell's right neighbour: RevealsOneCell 3 passed
- [Adversarial] F-010 CONFIRMED — animation tests only count animations; nothing reads the keyframe (read-only analysis)
- [Review 2/3] after adversarial: crit 0, imp 2 confirmed → fix 2. Family check: both attributed to fix 1 (its declared docstring/comment rewrites) — family 'outline/animation claims exceed assertions', streak 1 (<2, continue). Stalled check: Δscore +1.0, Δcrit+imp +1 → not stalled
- [Tests] tests/test_puzzle_solver_hint.py — 24 tests (22 + 2 from [Fix 1]): AC-1 (2,700 lines, 300 contradicting, every length 1–30), AC-2 (700 lines ≤ 12 cells, 100 contradicting), AC-3 (240 boards × 4 shapes; asserted ≥30 fallbacks, ≥50 boards with wrong marks, ≥20 where face-value wrong marks hide the deduction — neither the revealed cell's row nor its column forces it at face value ([Fix 1] F-001; the weaker "face-value hint differs" count is kept and asserted strictly larger), ≥30 nulls, ≥200 deductions), a hand-picked module test (hintStroke frozen + hint:true; hintCount through click/hint/hint/undo/redo/reset = [0,1,2,1,2,2]; replay still equals the board; state from the solution when clues disagree with it; null row → column still deduces; null row + null column → fallback; lineForced edge cases), AC-4..AC-11 in Chromium (plus: outline moves with the next commit; computed outline on the hinted cell — colour = resolved --color-accent, width = major rule, offset = minus the major rule, inset --grid-paper ring of twice the major rule ([Fix 1] F-002) — and outline-style none on every other td.player-cell ([Fix 2] F-009); DOM order and boxes of Hint and "Hints: N" at 1440 and 390 px ([Fix 1] F-003); reset keeps the count, setBoard zeroes it; Hint disabled when locked with cells still undecided; disabled during a drag and re-enabled after a cancelled drag; control test that the hinted cell does animate without reduced motion: one animation, named player-hinted-in, whose first keyframe (offset 0) sets outlineColor to transparent / rgba(0, 0, 0, 0) ([Fix 2] F-010)). AC-6's board: a seeded 10×10 grid that the solver reports unique but line logic leaves undecided at its fixed point (found in the test, asserted).
- [Fix 2] review cycle 2 (meta/review/20261005T144624Z-CARD-183-cycle2.yml). Claims and tests only — no CSS rule, JS or template change. Mutants applied one at a time to admin.css from a backup copy and restored from it, sha1 compared after each (runner: scratchpad card183/card183_fix2_mutants.py):
- [Fix 2] F-009 test_the_hinted_cell_carries_an_accent_outline now asserts outline-style none on every td.player-cell except the hinted one (and that there are 15×15 − 1 of them), replacing the single (14, 14) read; docstring says exactly that.
- [Fix 2] mutant M1 (edge, = review D1) — `.player-cell.is-hinted + .player-cell { outline: 2px solid var(--color-accent) }` (the hinted cell's right neighbour) — killed by TestSolverHint_RevealsOneCell::test_the_hinted_cell_carries_an_accent_outline (`[[0, 1]] == []`)
- [Fix 2] mutant M2 — `.player-cell[data-row="7"][data-col="7"] { outline: ... }` (a middle cell) — killed by ...test_the_hinted_cell_carries_an_accent_outline (`[[7, 7]] == []`)
- [Fix 2] F-010 test_without_reduced_motion_the_hinted_cell_animates now asserts the one animation is `player-hinted-in` and its first keyframe has offset 0 and outlineColor in ("transparent", "rgba(0, 0, 0, 0)") — read from effect.getKeyframes(), no mid-animation sampling. admin.css comment (comment only): "fading in" → "the outline colour fades in from transparent"; "styled alike" dropped (no test compares the counters' styles).
- [Fix 2] mutant M3 (= review D2) — keyframe `from { outline-color: transparent }` → `from { outline-offset: 0 }` — killed by TestSolverHint_ReducedMotion::test_without_reduced_motion_the_hinted_cell_animates (outlineColor None)
- [Fix 2] mutant M4 (edge) — keyframe from `outline-color: var(--color-success)` (a colour fade, not from transparent) — killed by ...test_without_reduced_motion_the_hinted_cell_animates (`'rgb(47, 107, 58)' in (...)`)
- [Fix 2] mutant M5 (edge) — the hinted cell runs `player-solved-in` instead — killed by ...test_without_reduced_motion_the_hinted_cell_animates (`'player-solved-in' == 'player-hinted-in'`)
- [Fix 2] F-011 skipped — same as F-005 above (two polite live-region updates per hint); behaviour change, owner decides at review.
- [Fix 2] F-012 skipped, OWNER NOTE — with the reset confirmation open, Tab from "Keep marks" reaches Hint (it follows the confirmation in the DOM); pressing Hint commits, and commit calls closeConfirm, which moves focus to Reset, so a second Enter opens the reset confirmation instead of giving a second hint. Not changed on the final review cycle (solver.js out of scope); owner to decide.
- [Fix 2] Results: four player test files → `200 passed, 1 warning in 135.21s (0:02:15)`; tests/test_puzzle_solver_hint.py three runs → `24 passed, 1 warning in 20.34s`, `24 passed, 1 warning in 20.69s`, `24 passed, 1 warning in 21.39s`.
- [Fix 2] pre-gate: named tests 2 passed (F-009, F-010); F-011/F-012 SKIPPED (behaviour changes; owner notes)
- [Fix 2] declarations: 0 matrix, 2 doc/comment narrowed-and-tested, 0 none — tests + CSS comment only
- [Build gate] PASSED (full, 642s) — 6447 passed, 9 skipped
- [Scope gate] cycle 3: in_scope (same 5 files; no guardrail hits)
- [Review 3/3] Score: 9.0 — crit: 0, imp: 0 (F-009, F-010 resolved; 8f mutation run: 12/12 killed R1–R12; Minor F-013 control-test timing headroom, F-014 owner decisions F-011/F-012)
- [Review 3/3] Score: 9.0 ✓ threshold reached + no critical/important
- [Review 3/3] Step 8h coverage: 52/52 card rules addressed (10 ✓, 42 ⚠ no_eligible_fact, 0 ✗); per-rule lines in the YAML
- [Review sync] 3 report(s) → meta/review/
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0038/R2, ADR-0038/R3, ADR-0038/R4)
- [AC/EC check] Failed: AC-12 ⚠ partial — no 'after a fallback hint' frame on the 15×15 fallback board (05-after-undo belongs to the deducible sequence); 04b-390 annotation banner covers board rows. AC-1..AC-11 ✓, G-1..G-7 ✓ (no EC section)
- [Renders] ~/Documents/nonogram-reviews/CARD-183/ (current full set, AC-12; every file at 1440 and 390 px): 01-before-main-blank-{1440,390}.png (main's toolbar before this card, 15×15 marking GRID from tests/test_puzzle_solver_marking.py); 02-blank-{1440,390}.png (this card's toolbar with Hint and "Hints: 0", blank board); 03-after-one-hint-{1440,390}.png (deducible hint on the marking GRID: outline on the revealed black cell, "Hints: 1", live-region text in the annotation bar); 05-after-undo-{1440,390}.png (that deducible hint undone on the marking GRID: cell undecided again, "Hints: 0"); fallback sequence on the seeded 15×15 board (scratchpad card183/card183_fallback15.py, seed 183, draw 43, line-logic fixed point with 89 undecided cells): 04a-fallback-board-before-hint-{1440,390}.png (before: no outline, "Hints: 0"; at 390 the board's right columns scroll inside the stage), 04b-fallback-hint-with-announcement-{1440,390}.png (during: outline on the revealed cell row 1 column 14 (white), "Hints: 1", annotation quoting "Hint: no cell follows from a single line yet; row 1, column 14 is white (from the solution)."; at 390 the stage is scrolled so that cell is in view), 04c-fallback-after-undo-{1440,390}.png (after Undo: row 1 column 14 undecided again, no outline, "Hints: 0", Undo disabled / Redo enabled), 04d-fallback-after-next-commit-{1440,390}.png (alternative "after": Hint again, then the next commit fills row 1 column 15: no outline, the revealed white cell kept, "Hints: 1"). The 04c/04d annotations say the live region still holds the hint text unchanged, so nothing new is announced.
- [AC-12 fix] Render-only, no repository file changed except these notes. New scratchpad script card183/card183_render_ac12.py (run with pytest, ROOT=worktree; it asserts nonogram is imported from the worktree's src) re-rendered 04a/04b and added 04c (required "after Undo" frame on the same 15×15 fallback board) and 04d (after the next commit). The annotation bar is no longer position:fixed over the board: it is an in-flow block appended after the page content, with a dashed border and the label "RENDER ANNOTATION (not part of the page)", so it never covers the board or toolbar and the full-page screenshot includes it. Every frame's state is asserted in the script (Hints count, .is-hinted count, "(from the solution)" in the announcement, no console errors) and was checked by eye.
- [AC-12 fix] 03/05 re-rendered with the same below-content annotation bar (scratchpad card183/card183_render_ac12_0305.py, ROOT=worktree, asserts state): 03-after-one-hint-{1440,390}.png (marking GRID, deducible hint: outline on row 1 column 1 (black), "Hints: 1", annotation "Hint: row 1, column 1 is black.") and 05-after-undo-{1440,390}.png (after Undo: cell undecided, no outline, "Hints: 0", annotation notes the live region still holds the hint text). 01/02 carry no annotation bar and were not re-rendered.
- [Build gate] impact: render-only AC-12 fix — no src/tests change since the 642s full run (6447 passed, 9 skipped); gate not re-run
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-1 ✓ test_PropertyTest_SolverHint_LineForcedMatchesThePythonLineSolver passed (≥2000 lines, ≥200 null asserted) · AC-2 ✓ ...LineForcedMatchesBruteForce passed (≥500) · AC-3 ✓ ...RevealsTheFirstDeducibleCell passed (4 shapes ≥200, fallbacks ≥30, wrong ≥50, hidden ≥20) · AC-4..AC-11 ✓ their named TestSolverHint_* classes passed (hint file: 24 passed, 0 skipped) · AC-12 ✓ renders 01–05 incl. 04a–04d 15×15 fallback at 1440/390, owner sign-off pending · G-1 ✓ page+marking+progress 176 passed, unchanged vs main · G-2 ✓ no-DOM + colour-literal tests 2 passed, 4 exports in solver_state.js · G-3 ✓ payload shape + no-request 5 passed, payload.rows/columns · G-4 ✓ no storage/request APIs in added lines · G-5 ✓ suites green, unchanged · G-6 ✓ src/nonogram/solver diff empty · G-7 ✓ #puzzle-player-hint paragraph identical to main. No EC section.
- [Docs] no per-directory README under src/nonogram/admin/{static,templates} (convention is an open owner decision); tests/README.md does not list player test files — no README change
- [Commit] success commit 9e6c101 (on top of implementation f1bcac2) — branch card/183-player-hint-button, 5 files +1097/−12; nothing under meta/ committed
- [Owner decision] 2026-10-05 Hint after Reset accepted; AC-12 renders accepted
- [Rebase onto 0d7c82e] rebased onto main f25bcbc (incl. CARD-188 0d7c82e): new commits ed7932c (feat) + c3d3fb8 (success, was 9e6c101). Conflicts in solver_state.js and solver.js were two adjacent new blocks — both kept verbatim (circledNumbers/circledClues + lineForced/hintCell/hintStroke/hintCount; paintCircles + hintText); admin.css auto-merged; showProgress keeps CARD-188's paintCircles call alongside the hint counter/announce. Keep-both only, no semantic merge → no confirmation review. Six player files: 232 passed. Full suite (lock): run 1 — 1 failed (test_puzzle_solver_page.py::TestSolverPageFits::test_the_largest_board_fits_a_laptop_screen[row-clues]: server 500 in app.puzzle_solve → get_puzzle UUID parse with DATABASE_URL set, before any player JS; passes 3/3 in isolation); run 2 — 6464 passed, 9 skipped. Flake noted for the dispatcher.
- [Merge gate] rebased onto f25bcbc (CARD-188 merged; both features kept); full suite 6464 passed, 9 skipped (second run; first run hit a one-off 500 in TestSolverPageFits[row-clues], passed 3/3 in isolation). Owner accepted Hint after Reset and the AC-12 renders. Merged bd8eccb.
