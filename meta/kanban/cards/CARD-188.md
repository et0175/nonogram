# CARD-188: The puzzle player circles a clue number once the player's marks settle its run

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/188-player-circle-solved-clues
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-05 (owner's solver test doc 2026-10-05, item 4)
**Idea:** —
**Wave:** 34
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_clues.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).** The player page
(`/puzzle/<id>/solve`) draws each clue box once, in `solver.js:clueBox`: a
`th.player-clue.is-row` / `.is-col` with one `span.player-clue-num` per
number and an `aria-label` like "Row 3: 2 2". Nothing about a clue number
ever changes after that. `solver.js:start` → `showProgress` re-derives the
error count and the solved state from `history.board` on every commit
(stroke, undo, redo, reset, `setBoard`). `solver_state.js` has no notion of
runs or clues.

**Owner's request (item 4).** Circle a clue number when it is solved: its run
is all dark and the cells on both sides are white dots or the edge. When it
is not clear which clue number a dark run belongs to (owner's example: clue
"2 2" and only one closed run of 2), leave the numbers uncircled.

**Target behaviour.**

1. **Words used here.** In one line, a cell is *dark* (FILLED), *white*
   (EMPTY) or *undecided* (anything else: UNKNOWN, and the "?" mark if the
   "?" brush card has merged first). A *closed run* is a maximal run of dark
   cells whose neighbour on each side is a white cell or the line's edge.
   The rule reads only the player's **marks**, never the solution.

2. **The rule, for one line with clue `c = [c1..ck]` (k ≥ 1, no zeros).**
   A clue number is circled when rule A or rule B circles it.
   - **Rule A, walk in from each edge.** From the left edge: skip white
     cells. Stop at the line's end or at an undecided cell. At a dark cell,
     find its run. If the run is not closed (an undecided cell follows it),
     stop. If it is closed, its length is L, and the next unassigned clue
     number from this edge is exactly L, assign the run to that number,
     circle it, and keep walking after the run. Otherwise stop. **A closed
     run whose length does not match its anchored clue number stops the walk
     from that edge.** Nothing after it is assigned from that edge. Then do
     the same from the right edge, assigning from `ck` backwards. The two
     walks are independent: a stop on one side does not stop the other.
     The circled set is the union of both walks.
   - **Rule B, the whole line.** If every dark run in the line is closed and
     their lengths, left to right, equal `c` exactly (same count, same
     lengths), circle every number of the clue.
   - Nothing else circles a number. In particular a closed run is never
     matched by length alone (see owner-visible default (b)).

3. **A "0" clue** (payload `[0]`, an empty line) is circled only when every
   cell of the line is white. A blank or "?" cell leaves it uncircled.

4. **Examples** (D dark, W white, . undecided; these are the AC-2 table):

   | Clue | Line (10 cells unless shown) | Circled | Why |
   |---|---|---|---|
   | 2 2 | `...WDDW...` | none | Owner's example. Both edges start on `.`; one closed run is not "2 2". |
   | 2 2 | `DDW.......` | first 2 | Left walk: closed run of 2 = c1. Right walk stops at once. |
   | 2 2 | `WDDWWDDW..` | both | Left walk assigns both runs. |
   | 2 2 | `DD.DD.....` | none | Neither run is closed. Marks match the solution, still no circle: white dots are needed. |
   | 1 1 | `.WDW.WDW.` (9) | both | Rule B: every dark run closed, lengths are exactly "1 1". |
   | 1 1 1 | `WDWD......` | first 1 | The second run is open on its right, so the left walk stops. |
   | 3 1 | `DDW....WDW` | 1 | Left walk: closed 2 ≠ 3, stop. Right walk: closed 1 = c2. |
   | 3 1 | `.WDDDW....` | none | The 3 is obvious by length, but rule A starts on `.` and rule B fails. Conservative on purpose. |
   | 0 | `WWWWW` (5) | 0 | Every cell white. |
   | 0 | `WW.WW` (5) | none | One cell undecided. |

5. **Wrong marks can circle numbers. That is by design.** The rule reads
   marks, so a wrong but self-consistent mark circles a number (clue "2",
   solution in cells 0–1, player marks `..WDDW....` → "2" circled by rule
   B). The `3 1` / `DDW....WDW` row above circles "1" although the marks
   cannot fit the clue. The circle never claims the mark is right; the
   error count does that job.

6. **Safety property (the conservative guarantee).** For any line whose
   marks fit at least one placement of its clue, every number the rule
   circles is one a brute force also circles. The brute force enumerates
   every placement of the clue that agrees with the dark and white cells,
   and circles number i only if run i covers the same cells in every
   placement *and* those cells are a closed run of the marks. (For a "0"
   clue it circles iff every cell is white.) Rule A is safe because its
   walked prefix is fully decided and ends at a white cell or the edge, so
   every placement holds exactly those runs first. Rule B is safe because a
   closed run is exactly one placement run, so k closed runs are all k runs.
   The rule is not complete: the brute force circles more (e.g. the `3 1`
   row above). A prototype run of 20,000 seeded lines (lengths 1–12) found
   no violation and 429 brute-force-only circles.

7. **State module (`solver_state.js`).** Add two pure functions, no DOM:
   - `circledNumbers(clue, cells)` → a frozen array of booleans, one per
     clue number (`[0]` gives one boolean). `cells` is one line of cell
     states.
   - `circledClues(board, rows, columns)` → frozen
     `{rows: [[bool...]] * height, columns: [[bool...]] * width}` from the
     board's lines and the payload's clues (ADR-0038/R3: clues are never
     re-derived from the solution; the solution is not an argument).

8. **Rendering (`solver.js`, `admin.css`).**
   - `showProgress` (the one place re-derived on every commit) also applies
     `circledClues(history.board, payload.rows, payload.columns)`: each
     `span.player-clue-num` gets or loses `.is-circled`. Keep the spans by
     row/column at draw time so no query runs per commit. This covers every
     commit path: click, drag end, undo, redo, Ctrl/Cmd+Z, reset, `setBoard`,
     and CARD-183's hint.
   - During a drag the circles follow the recorded board, not the preview,
     like the error count.
   - The solved lock does not hide circles. A solved board circles what its
     marks support and nothing more (see owner-visible default (c)).
   - CSS: `.player-clue-num.is-circled` draws a round outline around the
     digit using a token colour (no literal; the scripts stay colour-free).
     The digit keeps its ink and size. Two-digit numbers (up to 30) get a
     pill shape that still clears the digits. Every `.player-clue-num`
     reserves the outline space (e.g. a transparent border of the same
     width), so circling never moves a number, a clue box or a cell. No
     transition or animation, so the existing reduced-motion rule needs no
     change.
   - The clue box `aria-label` and each span's text stay as they are.

**Owner-visible defaults this card picks (say them at review):**
- (a) The circle shape and colour: a thin round outline in the grid-ink
  token around the digit, digit unchanged.
- (b) No length-only matching. A closed run whose length occurs once in the
  clue would also be provably safe to circle (the `.WDDDW....` / "3 1"
  case). The card leaves it out because the owner asked for "conservative".
  The owner may ask for it as a follow-up.
- (c) A solved board is not special-cased: a line with no white dots keeps
  its numbers uncircled even after the banner shows. The alternative is
  "circle every number once the puzzle is solved".

## Acceptance criteria

- **AC-1:** Given a seeded corpus of at least 5,000 lines (lengths 1–12; clues from random solution lines; marks a random mix of dark, white and undecided, with some flipped marks), when `circledNumbers` runs in the browser on each line whose marks fit at least one placement, then every circled number is also circled by the test's brute force (built on `tests/helpers/brute_force_oracle.py` `line_candidates`, as defined in "What to implement" 6). The test asserts ≥ 3,000 fitting lines, ≥ 1,000 with at least one circle, ≥ 300 "0"-clue or all-white lines, and ≥ 100 lines where the brute force circles something the rule does not (so the oracle is not trivially equal).
  *test: PropertyTest_SolverClues_NeverCirclesWhatBruteForceDoesNot (in tests/test_puzzle_solver_clues.py)*
- **AC-2:** Given each row of the examples table in "What to implement" 4, when `circledNumbers` runs, then it returns exactly the "Circled" column, including the owner's "2 2" example (none), the mismatch that stops one walk but not the other (`3 1`, `DDW....WDW` → only 1), and both "0" rows.
  *test: TestSolverClues_RuleExamples (in tests/test_puzzle_solver_clues.py)*
- **AC-3:** Given a seeded corpus of at least 500 lines, each marked exactly as its solution line with every other cell white, when `circledNumbers` runs, then every number is circled.
  *test: PropertyTest_SolverClues_AFullyMarkedLineCirclesEverything (in tests/test_puzzle_solver_clues.py)*
- **AC-4:** Given boards over shapes (10, 10), (15, 10) and (10, 25), at least 100 per shape, when `circledClues` runs, then each row and column entry equals `circledNumbers` of that line, and transposing the board and swapping rows/columns gives the transposed result.
  *test: PropertyTest_SolverClues_BoardIsLineByLine (in tests/test_puzzle_solver_clues.py)*
- **AC-5:** Given a 15×15 player page, when real clicks and a real drag close a run that matches its edge clue number, then that `span.player-clue-num` gets `.is-circled`; Undo removes it, Redo brings it back, and Reset clears every circle. No other number changes.
  *test: TestSolverClues_CirclesFollowEveryCommit (in tests/test_puzzle_solver_clues.py)*
- **AC-6:** Given the owner's case on a page (a row with clue "2 2", one closed run of 2 in the middle, undecided cells around it, set by `setBoard`), when the clue box is read, then neither "2" is circled.
  *test: TestSolverClues_AmbiguousRunStaysUncircled (in tests/test_puzzle_solver_clues.py)*
- **AC-7:** Given a page, when a drag that would close a run is in progress (pointer still down), then no circle changes until the pointer is released.
  *test: TestSolverClues_DragPreviewDoesNotCircle (in tests/test_puzzle_solver_clues.py)*
- **AC-8:** Given a board, when numbers become circled, then the bounding boxes of every cell, every clue box and every `span.player-clue-num` are unchanged, and the span texts and the clue boxes' `aria-label`s are unchanged.
  *test: TestSolverClues_CirclingMovesNothing (in tests/test_puzzle_solver_clues.py)*
- **AC-9:** Given a circled number, when its computed style is read, then it shows an outline (non-zero border width, round radius) whose colour differs from the clue box background, and a two-digit circled number's outline box is at least as wide as its text.
  *test: TestSolverClues_TheCircleIsVisible (in tests/test_puzzle_solver_clues.py)*
- **AC-10:** Owner render: a 15×15 board mid-solve with several circled numbers (row and column clues, a two-digit clue, the owner's "2 2" case uncircled), at desktop width and at 390 px, saved in ~/Documents/nonogram-reviews/CARD-188/.
  *test: review-lens (owner visual check of the renders)*

## Guardrails

- G-1: Every existing player test stays green unchanged: `tests/test_puzzle_solver_page.py`, `tests/test_puzzle_solver_marking.py`, `tests/test_puzzle_solver_progress.py` (EC-035 replay, EC-036/EC-037, AC-310 keyboard and labels, AC-311 no request per mark, AC-319 reduced motion, "the banner takes the tools' place and the board does not move"). The clue-text read at `test_puzzle_solver_page.py` ~line 604 still sees only the digits.
- G-2: ADR-0038/R4: `circledNumbers` and `circledClues` live in `solver_state.js`, with no DOM, globals or `import ` (`test_the_state_module_touches_no_dom`) and no colour literals (`test_the_scripts_carry_no_colour_literals`).
- G-3: ADR-0038/R2 and R3: no network request when circles change. The rule takes the payload's clues and never the solution. The payload shape is unchanged.
- G-4: FR-044 behaviour is unchanged: click cycle, drags, error count, solved predicate, lock, confirmed reset. Circles are a read-only view of the board.
- G-5: COMP-005 (`src/nonogram/solver/`) and `src/nonogram/clues.py` are not modified.
- G-6: CON-021 / CON-017: circles are derived, never stored or sent.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-188` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR-044** (puzzle player, AC-296..AC-323, EC-035..EC-037; statement at requirements.yml ~line 3700). It says nothing about clue numbers changing. This card adds card-local ACs only; FR-044 needs an architect delta (see Worktree notes).
- **ADR-0038** R1 (plain JS, no framework), R2 (no request per mark), R3 (payload clues only), R4 (pure state module).
- **CON-021**, CON-017 (nothing persisted or sent).
- **CON-005 / COMP-005**: unchanged. `tests/helpers/brute_force_oracle.py` `line_candidates` is the test oracle (it must keep not importing `nonogram.solver`).
- Components: COMP-008 area (admin panel adapter, `src/nonogram/admin/`). TERM-037 (puzzle player).
- Trace: owner solver test doc 2026-10-05 item 4 → CARD-188 → FR-044 (extension, no AC id yet).

## Design context

- **Screen:** the admin puzzle player, `/puzzle/<id>/solve`: the row and column clue boxes.
- **Owner-visible defaults:** (a) circle shape and colour, (b) no length-only matching, (c) no "circle all on solve". The owner confirms or overrides from the renders before merge.
- **Renders:** ~/Documents/nonogram-reviews/CARD-188/ (owner visual check). PNGs at desktop width and 390 px: a mid-solve 15×15 with several circled row and column numbers, one two-digit circled number, and the owner's "2 2" case left uncircled; plus a before/after pair showing one click circling a number.

## Worktree notes

- [Origin] Owner's solver test doc "Solver - test" 2026-10-05, item 4: circle solved clue numbers; leave them uncircled when the run's clue number is unclear. No IDEA id.
- [Spec] FR-044 has no AC for clue circles. ACs here are card-local. Raise an architect delta at the next architecture pass: add a sentence to FR-044's statement and ACs/an EC mirroring AC-1..AC-9 (AC-1 is a standing property, a candidate EC). Do not edit meta/ from the card.
- [Facts] The rule was prototyped in Python against `line_candidates` before drafting: 20,000 seeded lines, 16,045 with fitting marks, 0 safety violations, 429 brute-force-only circles, 1,127 lines with no fitting placement where the rule still circled something (the by-design wrong-marks case, excluded from AC-1). The AC-2 table was checked against that prototype.
- [Facts] Brute-force oracle for AC-1: `line_candidates(clue, length)` (tests/helpers/brute_force_oracle.py:77) takes the non-canonical clue (`(0,)` for an empty line), same as the payload. Filter by dark → True, white → False. A line with no fitting placement is skipped in AC-1. Keep lengths ≤ 12 (2^12 patterns per line).
- [Facts] Browser harness to reuse: `browser_page`, `live`, `_open` (test_puzzle_solver_page.py ~561–598); `_cell`, `_states`, `_button`, `_drag`, GRID 15×15 in test_puzzle_solver_marking.py; the pure-module call pattern `page.evaluate("async (...) => { const S = await import('/static/solver_state.js'); ... }")` as in test_puzzle_solver_progress.py `_PURE` / `_EVAL`. Batch the AC-1 corpus into a few `evaluate` calls, not one per line. Mark tests `@pytest.mark.browser`.
- [Facts] Avoid the class name `is-solved` for circles: `table.is-solved` and `.player-toolbar.is-solved` already exist (`showProgress`), and descendant selectors under `.player-board.is-solved` would collide. Use `.is-circled`.
- [Facts] `solver_state.js` may not contain `import ` and the scripts may carry no `#rgb` literal. All logic goes in solver_state.js; colours go in admin.css via tokens.
- [Conflict] Wave-34 siblings edit the same files. CARD-183 (hint) adds to `solver_state.js`, `solver.js`, `admin.css` and the counter row; CARD-182 edits the player block of `admin.css` (~lines 405–480, the `.player-clue` rules are at ~414–418). The "?" brush card (item 2) adds a fourth cell state: this card treats every state other than FILLED/EMPTY as undecided, so it needs no change when "?" lands; add a "?" row to AC-2 if that card merged first. The click-order card (item 5) does not affect this one. Rebase on whichever merges first.
- [Scope] Accessibility: circles are visual only; the clue box `aria-label` is unchanged (AC-8). Announcing circles is out of scope.
- [AC cross-check] All ACs re-read against "What to implement": AC-1 limits the safety check to lines with a fitting placement, as section 6 states; AC-2 rows are section 4's table verbatim; AC-7 matches "circles follow the recorded board, not the preview"; AC-8 matches the reserved outline space and unchanged aria-label. No edits were needed.
