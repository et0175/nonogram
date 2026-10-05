# CARD-188: The puzzle player circles a clue number once the player's marks settle its run

**Status:** done
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
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_marking.py
**Review score:** 9.0 (cycle 4, owner-granted)
**Started:** 2026-10-05T07:46:37Z
**Closed:** 2026-10-05T17:00:25Z
**Actual:** 1.2d
**Merge commit:** 0d7c82e
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

- G-1: Every existing player test stays green unchanged: `tests/test_puzzle_solver_page.py`, `tests/test_puzzle_solver_marking.py`, `tests/test_puzzle_solver_progress.py` (EC-035 replay, EC-036/EC-037, AC-310 keyboard and labels, AC-311 no request per mark, AC-319 reduced motion, "the banner takes the tools' place and the board does not move"). The clue-text read at `test_puzzle_solver_page.py` ~line 604 still sees only the digits. _Amended 2026-10-05 (owner decision on the CARD-188 escalation): one exception — `tests/test_puzzle_solver_marking.py::TestSolverMarking_RevealsNoCorrectness` may add ` is-circled` to its `_STRIPPED` normalisation, with its docstring reworded to say clue circles are a read-only view of the marks, not of correctness. No other change to that test or any other player test._
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
- [Env] forge 2026.8.17
- [BLOCKER] guardrail conflict: G-1 vs AC-5 — the existing test `tests/test_puzzle_solver_marking.py::TestSolverMarking_RevealsNoCorrectness::test_marking_all_but_the_last_solution_cell_changes_nothing_but_cell_states` marks every solution cell but the last (black marks only) on `_unique_grid(15, 15, seed=161)` and asserts that `document.body.outerHTML`, with only ` data-state="…"` and ` aria-(pressed|disabled)="…"` stripped, does not change. That grid has full-length lines (rows 2, 8, 10, 13 and columns 0, 10 have clue "15"). Fully black, each is a closed run at both edges, so the card's rule has to circle it (rule A from either edge, rule B, AC-3; AC-5 requires the circle to be the `.is-circled` class on `span.player-clue-num`). The class shows up in outerHTML, so that test fails (1 failed, 190 passed over page/marking/progress/clues/design-token files). No honest implementation satisfies both: any DOM-visible circle breaks that test, and hiding it inside a stripped attribute (e.g. `data-state="circled"`) would just game it. Suggested resolution (owner/orchestrator decision, not taken here): narrow that test the way CARD-162 narrowed it before, e.g. also strip ` is-circled` in `_STRIPPED` and update its docstring to say clue circles (CARD-188) are a read-only view of the marks, not of correctness.
- [Status] Implemented and committed as partial work: `circledNumbers` / `circledClues` (solver_state.js, appended), the `showProgress` → `paintCircles` hook with the spans collected once at draw time (solver.js, separate import line plus two appended functions), the `.is-circled` CSS with a reserved transparent border (admin.css, appended), and tests/test_puzzle_solver_clues.py (AC-1..AC-9, 9 tests, all passing; AC-1 counts: 5,068 fitting, 2,277 with a circle, 1,000 "0"/all-white, 204 brute-only, 0 violations). Because of the stop rule, NOT done: the mutation pass, the AC-10 owner renders, and the final console check beyond AC-5's `_watch_problems` (clean).
- [Owner default] (a) circle shape/colour, (b) no length-only matching, (c) solved board not special-cased — implemented as drafted
- [Blocker check] reproduced by orchestrator: TestSolverMarking_RevealsNoCorrectness → 1 failed, 1 passed (test_marking_all_but_the_last_solution_cell_changes_nothing_but_cell_states; .is-circled appears in body.outerHTML on the 'all but last cell' board, whose clue-15 lines are fully black)
- [Escalated] 2026-10-05T07:57:44Z — implementation agent [BLOCKER] guardrail conflict G-1 vs AC-5: G-1 keeps tests/test_puzzle_solver_marking.py green UNCHANGED, but its test_marking_all_but_the_last_solution_cell_changes_nothing_but_cell_states asserts body.outerHTML (minus data-state/aria-pressed/disabled) is unchanged after marking all but the last solution cell; on seed-161's 15×15 grid the clue-15 lines (rows 2,8,10,13; cols 0,10) are fully black closed runs, which rule A/B/AC-3 must circle, and AC-5 makes the circle the .is-circled class, visible in outerHTML. Verified (orchestrator re-ran: 1 failed). Feature itself built and its 9 AC-1..AC-9 tests green in implementation commit 25df421 (AC-1: 5,068 fitting lines, 0 safety violations, 204 brute-force-only); no review cycle run; mutation pass and AC-10 renders not done; worktree clean apart from meta/ · station: decompose · route: owner amends G-1 to allow narrowing that one test as CARD-162 did (add .replace(/ is-circled/g, '') to _STRIPPED and reword its docstring: clue circles are a read-only view of the marks, not of correctness), then /kanban review CARD-188 (resume: fix agent applies the narrowing + mutation pass + AC-10 renders, then the review cycle). Alternative (not recommended): drop AC-5's class requirement and render circles outside the DOM tree (constructed stylesheet) — that games the test's intent.
- [Owner decision] 2026-10-05 — G-1 narrowed (route 1): RevealsNoCorrectness strips ` is-circled`. Unblocked; resumes after CARD-182 merges (shared admin.css edge).
- [Resume] 2026-10-05 — orchestrator: worktree card synced from main (amended G-1, Touches += tests/test_puzzle_solver_marking.py); branch rebased cleanly onto main f9af283 (implementation commit now c1241c4); implementation agent resumed for the narrowing, mutation pass and AC-10 renders
- [Blocker resolved] Owner amended G-1 (2026-10-05, route 1). Applied exactly that and nothing else in the test: `_STRIPPED` in tests/test_puzzle_solver_marking.py gains `.replace(/ is-circled(?=[" ])/g, '')`, and the TestSolverMarking_RevealsNoCorrectness docstring now says clue circles are a read-only view of the marks, not of correctness. The lookahead removes only the whole `is-circled` token. It can never be the first class: solver.js draws every span with `className = "player-clue-num"`, and paintCircles only appends via `classList.toggle`, so the token is always preceded by a space. Mutant [18] shows the strip is needed, mutant [19] shows the narrowed test still catches any other class change.
- [Tests] tests/test_puzzle_solver_clues.py now has 14 tests. AC-8 and AC-9 are parametrized at 1440 and 390 px. AC-8 also compares the digits' own text boxes. AC-9 asserts a two-digit row number is a pill (wider than tall) at least as wide as its text plus both borders. New `TestSolverClues_RuleExamples::test_a_mismatched_closed_run_stops_its_walk` pins "otherwise stop" on non-fitting marks, which AC-1 cannot see. New `TestSolverClues_EveryNumberKeepsAOneCellSlot` checks that every row number's margin box is one cell wide and every column number's one cell tall, at both widths. Run of page/marking/progress/clues/phone/design-token files: 211 passed. AC-1 corpus counts: 5,068 fitting, 2,277 with a circle, 1,000 "0"/all-white, 204 brute-force-only, 0 violations.
- [Mutation] A: mismatch check `!==` → `<` (longer run accepted) → killed by TestSolverClues_RuleExamples::test_a_mismatched_closed_run_stops_its_walk (equivalent on fitting lines, so AC-1 cannot kill it)
- [Mutation] A: drop closed-run check → killed by TestSolverClues_RuleExamples::test_each_row_circles_what_the_table_says; alone also by test_PropertyTest_SolverClues_NeverCirclesWhatBruteForceDoesNot
- [Mutation] A: mismatch skips the run instead of stopping → killed by TestSolverClues_RuleExamples::test_a_mismatched_closed_run_stops_its_walk
- [Mutation] A: skip right-edge walk → killed by TestSolverClues_RuleExamples::test_each_row_circles_what_the_table_says (survives AC-3 alone: on a fully marked line the left walk circles everything)
- [Mutation] B: drop rule B → killed by TestSolverClues_RuleExamples::test_each_row_circles_what_the_table_says
- [Mutation] B: ignore run closedness → killed by TestSolverClues_RuleExamples::test_each_row_circles_what_the_table_says
- [Mutation] "0" clue circles with an undecided cell → killed by TestSolverClues_RuleExamples; alone also by test_PropertyTest_SolverClues_NeverCirclesWhatBruteForceDoesNot
- [Mutation] "0" clue never circled → killed by test_PropertyTest_SolverClues_AFullyMarkedLineCirclesEverything (alone)
- [Mutation] circledClues reads columns with the wrong stride → killed by test_PropertyTest_SolverClues_BoardIsLineByLine
- [Mutation] circles applied to the drag preview → killed by TestSolverClues_DragPreviewDoesNotCircle
- [Mutation] showProgress does not paint circles → killed by TestSolverClues_CirclesFollowEveryCommit; alone also by TestSolverClues_AmbiguousRunStaysUncircled
- [Mutation] circles only added, never removed (the undo/redo/reset path; all of them go through commit → showProgress, there is no separate undo toggle) → killed by TestSolverClues_CirclesFollowEveryCommit
- [Mutation] digit count never set (no pill) → killed by TestSolverClues_TheCircleIsVisible[desktop]
- [Mutation] circle colour = clue box background → killed by TestSolverClues_TheCircleIsVisible[desktop]
- [Mutation] square corners → killed by TestSolverClues_TheCircleIsVisible[desktop]
- [Mutation] narrowed `_STRIPPED` without the is-circled strip → killed by TestSolverMarking_RevealsNoCorrectness::test_marking_all_but_the_last_solution_cell_changes_nothing_but_cell_states
- [Mutation] paintCircles also toggles a second class `is-settled` → killed by that same narrowed test, so it still catches changes other than the circle class
- [Mutation] Method: each mutant was applied by exact string replacement and reverted by restoring the captured file content (cmp-verified, never git checkout). Runner: scratchpad/card188_mutate.py. No survivors remain.
- [Scope] src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_marking.py
- [Scope gate] in_scope — 5/5 files inside Touches (G-1 amendment added test_puzzle_solver_marking.py); no G-5 hit (src/nonogram/solver/**, src/nonogram/clues.py untouched)
- [Build gate] impact underivable (review.test_scope: full) — full suite
- [Build gate] PASSED (full, 637s; 6356 passed, 9 skipped; lock wait 338s)
- [Review 1/3] Score: 7.5 — crit: 0, imp: 1 (F-001 pending adversarial verification)
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h: 52/52 card rules have a verdict line (9 ✓, 43 ⚠ no_eligible_fact, 0 ✗) — coverage guard passed
- [Adversarial] F-001 CONFIRMED — skeptic measured 30×30 @1440: every two-digit row/column span 15.22×15.22 circle around 12.45 px text, ring cuts '12'/'17'/'30'; 390 px pill 22×20 with 1.33 px clearance
- [Review 1/3] Score: 7.5 — crit: 0, imp: 1 (confirmed) — below threshold; fix cycle 1
- DESIGN-REGISTER ClueBox: circled — a clue number its marks settle gets a thin round outline in --grid-ink (pill for two digits), drawn in a transparent border every number reserves, so nothing moves _(Superseded by [Fix 1] F-001: the ring is now the number's ::before, out of layout; see the [Fix 1] lines.)_
- [Rebase fix] After the rebase onto CARD-182's phone sizing, the first CSS broke two CARD-182 tests: the 1440 30×30 cell width (a two-digit column pill widened its column in table intrinsic sizing) and the 390 px scrolled touch drag (sub-pixel margins drifted the row clue width by 0.47 px). Fixed inside the card's own CSS block and hook. solver.js `clueNumbersOf` sets `--player-clue-digits` on each span once at draw time. admin.css computes the pill width from it in `ch`, caps a column pill at cell minus a heavy rule, and uses CSS `round()` so circle insets and row margins are whole pixels, keeping every slot exactly one cell. The 30×30 board at 390 px is now 1087.797 px wide, the same as main. _(Superseded by [Fix 1] F-001: the ring is now the number's ::before, out of layout; see the [Fix 1] lines.)_
- [Mutation] reserved transparent border dropped (border only when circled) → killed by TestSolverClues_CirclingMovesNothing[desktop] (the digits' text box moves; the border-box span box does not, which is why AC-8 now measures the digits too) _(Superseded by [Fix 1] F-001: the ring is now the number's ::before, out of layout; see the [Fix 1] lines.)_
- [Mutation] TEST-CLAIM (CSS comment "the gaps are whole pixels, so sub-pixel rounding cannot drift a long clue"): row margins without round() → killed by TestSolverClues_EveryNumberKeepsAOneCellSlot[desktop]; circle inset without round() → killed by TestSolverClues_EveryNumberKeepsAOneCellSlot[desktop] _(Superseded by [Fix 1] F-001: the ring is now the number's ::before, out of layout; see the [Fix 1] lines.)_
- [Mutation] TEST-CLAIM (CSS comment "a column clue's box is never wider than its column less a heavy rule"): cap removed → killed by tests/test_puzzle_solver_phone.py::TestSolverPhone_DesktopSizingUnchanged[30x30] _(Superseded by [Fix 1] F-001: the ring is now the number's ::before, out of layout; see the [Fix 1] lines.)_
- [Renders] AC-10, made by scratchpad/card188_render.py over the `live` fixture (temp SQLite, loopback), device scale 2, browser console clean on every page: ~/Documents/nonogram-reviews/CARD-188/mid-solve-desktop-1440.png, mid-solve-desktop-1440-board.png, mid-solve-phone-390.png, mid-solve-phone-390-board.png, mid-solve-phone-390-scrolled-right.png, click-before-desktop-1440.png, click-after-desktop-1440.png. Mid-solve: 13 column numbers and many row numbers circled, the two-digit "12" and "15" pills circled, the owner's "2 2" row (row 8, one closed run of 2 mid-row) uncircled. The click pair: row 10 ("1 7 1 3"), clicking cell 2 (black → white) circles its "1". The board shows "Errors: 1" before that click, because the set-up black mark is wrong; the click fixes it. Eyeballed: circles are visible, nothing overlaps, and the pills clear their digits. The tightest spot is a "12" pill next to a "2" circle, about 3 px apart at 1440. Row/column numbers above are 1-based; the code's indices are 0-based. _(Re-rendered in [Fix 1]; the "pills clear their digits" eyeball held at 15×15 only — at 30×30/1440 it did not, which was F-001.)_
- DESIGN-REGISTER ClueBox: pill width comes from the digit count (`--player-clue-digits`, set by solver.js at draw time); each number keeps exactly a one-cell slot. _(Superseded by [Fix 1] F-001: the ring is now the number's ::before, out of layout; see the [Fix 1] lines.)_
- [Fix 1] F-002 — `test_the_outline` resolves `--grid-ink` inside the board (a probe element with `color: var(--grid-ink)`) and asserts the ring colour equals it.
- [Fix 1] F-003 — CSS `round()` is no longer used: the ring is out of layout, so nothing needs whole-pixel insets or margins. No browser floor beyond what main's CSS already needs.
- [Fix 1][Known, not claimed] At a heavy-rule column on the 30×30 at 1440 px the two-digit pill (≈ 16.7 px) is wider than that column's content box (cell − 2 px ≈ 15.7 px), so it laps ≈ 0.5 px onto the column rules on each side (≈ 0.3 px at 390). Keeping it inside would leave ≈ 0.45 px digit clearance, below the 0.5 px the test asks. Not tested, not claimed in comments; visible in 30x30-desktop-1440-board.png as rings touching the vertical rules.
- [Fix 1][Mutation] no pill (ring width = circle) → killed by TestSolverClues_TheCircleIsVisible::test_the_outline[desktop,phone] and ::test_two_digit_rings_clear_their_digits_on_a_30x30[desktop,phone]
- [Fix 1][Mutation] solver.js never sets --player-clue-digits → killed by the same four tests
- [Fix 1][Mutation] ring put back in layout (::before position: relative; display: inline-block) → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[desktop,phone], TestSolverClues_EveryNumberKeepsAOneCellSlot[desktop,phone], tests/test_puzzle_solver_phone.py TestSolverPhone_DesktopSizingUnchanged[15x15,25x15,30x30], the 390 px scrolled touch drag and the column-band swipe
- [Fix 1][Mutation] clearance 0 → killed by test_the_outline[desktop,phone] and test_two_digit_rings_clear_their_digits_on_a_30x30[desktop,phone]
- [Fix 1][Mutation] TEST-CLAIM edge (CSS comment "the pill still clears its digits"): clearance 0.02 cell (≈ 0.35 px at 17 px) → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[desktop]
- [Fix 1][Mutation] ring border only when circled (uncircled border 0) → killed by test_the_outline[desktop,phone]
- [Fix 1][Mutation] ring colour = clue box background → killed by test_the_outline[desktop,phone]
- [Fix 1][Mutation] F-002: ring colour --color-text-secondary → killed by test_the_outline[desktop,phone] (the new resolved --grid-ink comparison is the first assertion it fails)
- [Fix 1][Mutation] square corners → killed by test_the_outline[desktop,phone]
- [Fix 1][Mutation] Method: exact string replacement, restored from captured content and compared (never git checkout). Runner: scratchpad/card188_fix1_mutate.py. No survivors.
- [Fix 1][Tests] page/marking/progress/clues/phone/design-token files: 213 passed (211 + the two 30×30 cases).
- [Fix 1][Renders] scratchpad/card188_render.py re-run (device scale 2, console clean): all earlier files refreshed, plus ~/Documents/nonogram-reviews/CARD-188/30x30-desktop-1440-board.png, 30x30-phone-390-board.png, 30x30-{desktop-1440,phone-390}-row-clue.png, 30x30-{desktop-1440,phone-390}-col-clues-0.png (the two-digit 30×30, fully marked). Eyeballed zoomed crops: at 1440 the "12 17"/"16 13" row pills and the run of "30" column pills clear their digits with a visible gap, and adjacent rings do not touch, but they are tight (about one device pixel between "30" rings); at 390 the gaps are clearly visible.
- [Fix 1] pre-gate: named tests green (TheCircleIsVisible + EveryNumberKeepsAOneCellSlot + CirclingMovesNothing 8 passed; TestSolverPhone_DesktopSizingUnchanged 3 passed); declarations: 3 updated (admin.css card block, solver.js comment, test docstrings + superseded card notes), 0 confirmed, 0 none
- [Build gate] PASSED (full, 651s; 6358 passed, 9 skipped — after fix 1)
- [Review 2/3] Score: 8.0 — crit: 0, imp: 1 (F-004 pending adversarial verification); F-001/F-002/F-003 ✓ resolved; confirmation mode; 8f-mutation deferred(cost)
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h: 52/52 card rules have a verdict line (9 ✓, 43 ⚠, 0 ✗; carried lines delta-clean) — coverage guard passed
- [Adversarial] F-004 CONFIRMED — skeptic: 30×30 at 1100×700 and 900×600 clamps to the 14 px cell floor (height-driven); ring 13.5×12.31, 4 adjacent '30' column ring pairs at 0.000 px gap; 1366×768 → 14.2 px, gap 0.031; docstring/CSS comment treat ~17 px as the smallest desktop cell
- [Review 2/3] Score: 8.0 — crit: 0, imp: 1 (confirmed; fix-introduced, attributed to Fix 1's ring-width declaration) — fix cycle 2. Stalled check: Δscore +0.5 (≥ min_improvement 0.5) → not stalled. Family streak 1 (ring geometry bound) — below the escalation threshold of 2
- [Fix 1] F-001 — two-digit numbers on a 30×30 at 1440 px (cell ≈ 17 px) were w = h circles whose ring crossed the digits, because the ring was the span's own border and the span had to fit the one-cell slot with whole-pixel margins. The ring is now `.player-clue-num::before` (position: absolute, pointer-events: none, box-sizing: border-box), centred on the number, `--player-circle` (0.88 cell) tall and `--player-ring` = max(circle, digits·1ch + 2·(clearance 0.05 cell + ring width)) wide. It takes no part in layout, so the spans went back to main's own layout (the card's width/height/margin/padding/border overrides on `.player-clue-num` are gone; only `position: relative` is added): every number keeps main's one-cell slot, and the CARD-182 sizing tests pass unchanged. Circling still only changes a border colour (the ring is always there, transparent). Measured at 1440 on the two-digit 30×30 (cell 17.67): every two-digit ring clears its digits by ≥ 0.92 px each side, nearest two rings 0.53 px apart; phone-depth 30×30 (cell 16.80): ≥ 0.83 px, rings ≥ 0.97 px apart; 390 px (cell 24): ≥ 1.6 px, rings ≥ 0.9 px apart; 10×10 and 15×15: ≥ 1.8 px, rings ≥ 1.47 px apart. solver.js still sets `--player-clue-digits` at draw time; its comment now names `--player-ring`. [superseded by Fix 2 for the ring width: --player-ring is now also capped, see [Fix 2] F-004]
- [Fix 1] F-001 tests — `TestSolverClues_TheCircleIsVisible::test_the_outline` now reads the ring's (::before) computed style; new `TestSolverClues_TheCircleIsVisible::test_two_digit_rings_clear_their_digits_on_a_30x30[desktop|phone]` on a 30×30 whose rows are all pairs of two-digit numbers and whose columns include ten adjacent "30"s, fully marked (every number circled): asserts the 1440 cell is < 18 px and the 390 cell 24 px, every ring is position: absolute, ≥ 20 circled two-digit numbers per axis, each with ≥ 0.5 px between its text box and the ring's inner edge on both sides and wider than tall, and no two rings (all numbers) touch. [superseded by Fix 2]
- [Fix 1][Mutation] TEST-CLAIM edge (CSS comment "touches no other ring"): clearance 0.09 cell → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[desktop,phone] (rings touch) [superseded by Fix 2]
- DESIGN-REGISTER ClueBox: circled — a clue number its marks settle gets a thin round ring in --grid-ink drawn by its ::before (out of layout, centred on the digits): a circle for one digit, a pill as wide as the digits plus clearance for two; the ring is always present and transparent until circled, so nothing moves and each number keeps main's one-cell slot. [superseded by Fix 2]
- [Fix 2] F-004 — the cycle-1 claim "on a 30×30 at about 17 px the pill touches no other ring" left out the 14 px cell floor (`--player-cell-min`, reached in ordinary desktop windows because the cell clamp also reads the viewport height). There two "30" column rings touched: the ring is centred on its span, the span's box excludes the th's right rule, so a thin-rule column next to a heavy-rule column has digit centres a cell − (heavy − thin)/2 = 13.5 px apart, and the ring was 13.5 px wide. Mechanism change: `--player-ring` is now `min(max(circle, digits·1ch + 2·(clearance + ring width)), cell − (--player-rule-major − --player-rule)/2 − --player-ring-gap)`, with the new `--player-ring-gap: 0.25px` on `.player-board`. `--player-rule` and `--player-rule-major` (the board's rule widths) now also size the ring — a second job, stated in the CSS comment. The ring stays centred on the digits (re-centring on the column pitch would cost up to 1 px of digit clearance on one side, below 0.5 px at 14 px). Digits, fonts, slots and uncircled numbers are unchanged. CSS comment and the `TestSolverClues_TheCircleIsVisible` docstring now claim only what the test checks: on a 30×30 at the 14 px floor, ≈ 17 px (1440) and 24 px (390), the pill clears its digits by ≥ 0.5 px and any two rings are ≥ `--player-ring-gap` (0.25 px) apart.
- [Fix 2] F-004 tests — `test_two_digit_rings_clear_their_digits_on_a_30x30` gains a `[floor]` case (1100×700, asserts the cell is exactly 14), and its cell asserts are now exact per viewport (14 / ≈ 17.67 / 24). "No two rings touch" became "every pair of rings is ≥ `_RING_GAP` (0.25 px, = `--player-ring-gap`) apart, less 0.01 px for 1/64 px layout rounding", on all three cases. The digit clearance (≥ 0.5 px each side) and pill (wider than tall) asserts are unchanged and now also run at 14 px.
- [Fix 2] F-004 measured (two-digit 30×30, fully circled; scratchpad/card188_skeptic2_test.py probe): 1100×700 and 900×600 cell 14.00, ring 13.25×12.31, digit clearance ≥ 0.56 px, nearest rings 0.250 px apart; 1366×768 cell 14.20, clearance 0.58, gap 0.250; 1280×800 cell 15.05, clearance 0.70, gap 0.250; 1440×900 cell 17.67, clearance 0.92, gap 0.531 (unchanged from Fix 1, so the cap does not bite there); 1920×1080 cell 22.41, clearance 1.45, gap 0.797; 390×844 and 820×1180 cell 24, clearance 1.62, gap 0.906. No touching pairs anywhere.
- [Fix 2][Mutation] cap removed (ring = max(circle, digits + clearance + ring)) → killed by TestSolverClues_TheCircleIsVisible::test_two_digit_rings_clear_their_digits_on_a_30x30[floor]
- [Fix 2][Mutation] cap ignores the heavy rule (cell − gap) → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor]
- [Fix 2][Mutation] TEST-CLAIM edge (CSS comment "any two rings are at least --player-ring-gap apart"): asserted bound kept at 0.25, `--player-ring-gap: 0.2px` → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor]
- [Fix 2][Mutation] TEST-CLAIM edge (CSS comment "the pill clears its digits by at least 0.5 px", at 14 px): `--player-ring-gap: 0.45px` (clearance ≈ 0.46 px) → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor]
- [Fix 2][Mutation] Method: exact string replacement, restored from captured content and compared in place. Runner: scratchpad/card188_fix2_mutate.py. No survivors.
- [Fix 2] F-005 — SKIPPED (owner call, minor). At the 14 px floor the narrowest two-digit pill that keeps 0.5 px digit clearance with a 1 px ring is ≈ 13.1 px, wider than a heavy-rule column's 12 px content box, so a pill there cannot stay off the vertical rules without shrinking the digits. With the cap the lap at a heavy-rule column is ≈ 0.6 px (computed from ring 13.25 px centred 6 px into a 12 px box, not measured; it was 0.75 px). 1440 is unchanged (≈ 0.5 px, see [Fix 1][Known, not claimed]).
- [Fix 2][Known, not claimed] Rule laps (column pills onto vertical rules, row pills onto horizontal rules at 14 px) are not tested and not claimed in comments.
- [Fix 2][Tests] page/marking/progress/clues/phone/design-token files: 214 passed (213 + the new [floor] case). AC-8, TestSolverClues_EveryNumberKeepsAOneCellSlot and TestSolverPhone_* pass unchanged.
- [Fix 2][Renders] scratchpad/card188_render.py re-run (device scale 2, console clean): all earlier files refreshed, plus ~/Documents/nonogram-reviews/CARD-188/30x30-desktop-1100x700-board.png, 30x30-desktop-1100x700-row-clue.png, 30x30-desktop-1100x700-col-clues-0.png and zoomed column-clue crops 30x30-{desktop-1100x700,desktop-1440,phone-390}-col-clues-zoom.png (the first ten "30" columns, heavy rule after column 5). Eyeballed: at 14 px the ten "30" pills read as separate rings with the digits inside; the gap between neighbours is a quarter pixel, so at device scale 2 they look nearly touching across the column rules. 1440 looks as in Fix 1.
- [Fix 2] pre-gate: named test green (TestSolverClues_TheCircleIsVisible 5 passed incl. the new [floor] case); declarations: 1 updated (ring-width cap + admin.css comment + test docstring + superseded card notes; --player-rule/--player-rule-major gain a second job, stated in the comment), 0 confirmed, 0 none; F-005 SKIPPED (minor, owner call)
- [Build gate] PASSED (full, 652s; 6359 passed, 9 skipped — after fix 2)
- [Review 3/3] Score: 8.0 — crit: 0, imp: 1 (F-006 pending adversarial verification); F-004 ✓ resolved; full review; 8f-mutation RAN: 9 mutants, 6 killed, 3 survived (M3 → F-007 minor; M7/M9 → F-006 important)
- [Review sync] 3 report(s) → meta/review/
- [Review 3/3] Step 8h: 52/52 card rules have a verdict line (9 ✓, 43 ⚠, 0 ✗) — coverage guard passed
- [Adversarial] F-006 CONFIRMED — skeptic: M9 (ring top: calc(-1 * var(--player-circle)), entirely above its number) and M7 (top: 0) each pass all 32 tests of test_puzzle_solver_clues.py + test_puzzle_solver_phone.py; _RINGS top/bottom feed only shift-invariant checks (pill shape, pairwise gaps); 'centred on the number' (admin.css:490) and 'clears its digits … on each side' (test docstring ~615) are unbacked vertically; restore verified (cmp, git diff sha 03daf51b… unchanged)
- [Review 3/3] ⚠ improvement stalled — Δscore: 0.0, Δcrit+imp: 0
- [Review 3/3] Score: 8.0 ⚠ max cycles reached
- [Escalated] 2026-10-05T13:38:42Z — review cycles exhausted at 8.0 (3/3; stalled: Δscore 0.0, Δcrit+imp 0). One gating finding left: F-006 (Important, skeptic-CONFIRMED, found by the deferred 8f mutation check): no test pins the clue ring's vertical position — mutants M7 (admin.css ring top: 0) and M9 (ring entirely above its number) survive the whole clues+phone suite, so 'centred on the number' (admin.css:490) and 'clears its digits … on each side' (test_puzzle_solver_clues.py ~615) are unbacked vertically. The code itself is correct (reviewer: rule logic, commit wiring, 14 px ring cap all hold; 52/52 8h verdicts, 0 ✗; AC-1..AC-10 and G-1..G-6 ✓ per reviewer; full suite 6359 passed / 9 skipped on this working tree). Minor open: F-005 (pills lap vertical column rules ~0.5–0.6 px, owner call), F-007 (rule A far-edge mutant end<=length survives; add ((1,2),'WWWWWWWWWD',[True,False]) + mirror to STOPS), F-008 (no device-scale-1 floor render), F-009 (0.01 px tolerance < the 1/64 px rounding its comment cites). Commits on branch: c1241c4, 5060056; fix-cycle-1 and fix-cycle-2 edits (admin.css, solver.js, tests/test_puzzle_solver_clues.py) are UNCOMMITTED in the worktree. Reports synced: meta/review/20261005T114751Z-, 20261005T123812Z-, 20261005T132134Z-CARD-188-cycle{1,2,3}.yml · station: implementation (code defect — a test gap; card and requirement sound) · route: manual fix — in test_two_digit_rings_clear_their_digits_on_a_30x30 (or test_the_outline) add textTop/textBottom to _RINGS and assert each ring's vertical centre is within ~0.5 px of its digits' text-box centre at floor/desktop/phone (centring, not containment); confirm M7 and M9 are now killed; optionally F-007 rows and F-009 tolerance (1/64); then /kanban review CARD-188 (one confirmation cycle + AC/EC/G gate + success commit). Owner also looks at the renders in ~/Documents/nonogram-reviews/CARD-188/ (AC-10, defaults a/b/c, F-005 rule lap, F-008 1x crop) before merge.
- [Owner decision] 2026-10-05 — "Targeted fix + 1 review": add the vertical-centring assertion (F-006) plus F-007/F-009, one confirmation review. Unblocked → review. Runs alongside CARD-183 (dispatcher choice: the fix is test-side in this card's own test file; merge order decides the rebase).
- [Fix 3] F-007 — TestSolverClues_RuleExamples.STOPS gains `((1, 2), "WWWWWWWWWD", [True, False])` and its mirror `((2, 1), "DWWWWWWWWW", [False, True])`, derived from the card's rule A (a closed run ending at the walk's far edge is closed; the right walk's run of 1 ≠ anchored 2 stops it; rule B: 1 run ≠ 2 numbers).
- [Fix 3] F-009 — ring-gap tolerance is now `_RING_GAP - 1 / 64` and the comment says "less one 1/64 px layout unit"; claim and value agree.
- [Fix 3][Mutation] solver_state.js walkIn `end < length` → `end <= length` → killed by TestSolverClues_RuleExamples::test_a_mismatched_closed_run_stops_its_walk (restored from captured bytes, cmp OK).
- [Fix 3][Tests] page/marking/progress/clues/phone/design-token files: 214 passed (no test added; STOPS rows are one parametrized-free test). admin.css and solver.js untouched by this fix.
- [Escalated] 2026-10-05T13:53:20Z — targeted fix (owner grant): F-007 and F-009 fixed test-only (F-007 far-edge mutant end<=length now killed; 214 passed on the six player files), but F-006's vertical-centring assertion exposes a REAL defect: row-number rings are centred on the inline-block box, not the digits — ring centre minus digit text-box centre at 1440 (17.67 px cell) is +0.805 px for rows (+1.10..1.24 px vs glyph ink, ~4 px clearance above / ~1.5 px below), +0.32 cols; 14 px floor +0.20 rows; 24 px +0.21 rows. No honest ≤0.5 px centring test passes; 'centred on the number' (admin.css:490) and the DESIGN-REGISTER 'centred on the digits' hold for the box only. Per owner instruction no redesign attempted. Nothing committed beyond c1241c4/5060056; fix-1/2/3 edits UNCOMMITTED (admin.css, solver.js, tests/test_puzzle_solver_clues.py); main moved (CARD-181), not rebased; full suite not re-run · station: implementation (production CSS defect, owner decision on placement) · route: owner picks — (a) production fix: give row numbers an explicit height/line-height like column numbers (or centre the ring on the text), then F-006 test (centre within 0.5 px at 14/17.67/24 px, kill M7/M9/±1 px) + one confirmation review; or (b) accept the 1440 row offset as a visual tolerance and narrow the 'centred' claims to the box, with a test pinning box-centring (kills M7/M9) — then confirmation review
- [Owner decision] 2026-10-05 — route (a) "Fix it": row numbers get the same height/line-height as column numbers so rings centre on the digits; F-006 test ≤0.5 px at 14 / 17.67 / 24 px cells (kills M7, M9, ±1 px); one confirmation review. Unblocked → review.
- DESIGN-REGISTER ClueBox: circled — a clue number its marks settle gets a thin round ring in --grid-ink drawn by its ::before (out of layout, centred on the digits): a circle for one digit, a pill as wide as the digits plus clearance for two, capped so neighbouring rings keep --player-ring-gap between them; the ring is always present and transparent until circled, so nothing moves and each number keeps main's one-cell slot. [superseded by Fix 4]
- [BLOCKER] F-006 exposes a real defect: the ring is centred on the number's *box* (admin.css `top: calc(50% - var(--player-circle) / 2)`, confirmed: ring top = (box height − ring height)/2 exactly), but a row number is an `inline-block` with `line-height` = font-size, and that box does not sit centred on its digits. Ring vertical centre minus the digits' Range text-box centre on the 30×30, all circled numbers: 14 px floor (1100×700) row +0.203, col −0.016; 1440 (17.67 px) row **+0.805**, col +0.320; 390 (24 px) row +0.211, col −0.008 px (positive = ring lower). Against the glyph ink centre (canvas `measureText` actualBoundingBox on the computed font, baseline from the text box + fontBoundingBoxAscent, both baseline estimates agree to 0.000): row +0.20…0.32 / +1.10…1.24 / +0.36…0.56, col −0.02…0.10 / +0.61…0.76 / +0.14…0.34 px. So at 1440 a row pill sits ~1.2 px low on its digits (ink clearance ≈ 4 px above vs ≈ 1.5 px below inside a 13.4 px inner height). The requested assertion (centre within ~0.5 px of the text-box centre) fails at desktop/1440 rows; a tolerance loose enough to pass (≥ 0.85 px) cannot kill a −1 px edge mutant there, so no honest centring test fits the current CSS. The claims "centred on the number" (admin.css comment) and "centred on the digits" (DESIGN-REGISTER ClueBox line) hold for the box, not the digits. No assertion added; not redesigned (test-only scope). Route: owner decides whether to fix placement (e.g. give row numbers an explicit line-height/height like column numbers, or centre on the text) in a production change, then re-run F-006. [resolved by Fix 4]
- [Fix 3][Mutation] M7, M9 and the ±1 px centring edge mutant — not run: F-006 is blocked (no centring assertion exists to kill them). [superseded by Fix 4]
- [Fix 4] F-006 — production: one rule added inside the card's Clue circles block, `.player-board .player-clue.is-row .player-clue-num { height: var(--player-cell); line-height: var(--player-cell); margin: calc(var(--player-rule-major) / -2) 0; }`. Row numbers now get the column numbers' cell height and cell line-height, so the ring (still centred on the number's box, `top: calc(50% - var(--player-circle) / 2)` unchanged) centres on the digits. The negative margin of half the heavy rule above and below is needed because a row clue box's content is a cell less its bottom rule: without it every row grows by 1 px (measured), and half the *thin* rule is not enough — the rows ending in a heavy rule (every 5th) still grew by 1 px (measured; that was the first attempt). Height alone is needed too: line-height without height left rows 17.6875 px at 1440 (cell 17.671875). A cell-less-rule line-height (13 px at 14) was tried and rejected: it put the row ring +0.48/+0.82/+0.49 px off its digits. Column rings, digit font/size/letter-spacing, the ring itself, row box widths and every number's one-cell slot are unchanged. Row digits move down inside their clue box by ≈ 0.2–0.5 px as a consequence of being centred in a cell-tall line box (digits' text-box top relative to the th: 0.80/1.30 → 1.0/1.5 px at 14, 0.53/1.03 → 1.0/1.5 at 1440, 2.80/3.30 → 3.0/3.5 at 390; the two values are heavy-rule rows / other rows). Columns were already within 0.5 px (≤ +0.32), so they were not touched.
- [Fix 4] F-006 test — `_RINGS` gains `textTop`/`textBottom` (the number's Range text box). `test_two_digit_rings_clear_their_digits_on_a_30x30` [floor 1100×700 cell 14 / desktop 1440 ≈17.67 / phone 390 cell 24] now asserts (1) every one of the 30 row clue boxes is exactly one cell tall (±0.001 px), and (2) every ring — one and two digits, ≥ 30 rows and ≥ 30 columns, circled or not — has its horizontal and vertical centre within 0.5 px of its digits' text-box centre; the centring check runs before the left/right clearance loop so horizontal shifts are reported by it. Docstring now says the clearance is "on the left and on the right" (not "on each side"), and states the centring and the one-cell row box. admin.css comment: "centred on the number" → "centred on the number's box", plus the row height/line-height/margin rationale and "the ring's centre is within 0.5 px of the digits' text box centre, across and down" on the 30×30 at 14/≈17/24 px; the clearance sentence now says "on the left and on the right". No other test file changed (G-1).
- [Fix 4] F-006 measured (ring centre − digits' text-box centre, all rings on the two-digit 30×30, positive = ring right/lower; dx / dy): rows 14 px +0.008 / −0.016, 17.67 px 0.000 / +0.320, 24 px −0.008 / −0.008; columns 14 px −0.016…+0.008 / −0.016, 17.67 px −0.016…+0.016 / +0.320, 24 px −0.008…+0.008 / −0.008. Before Fix 4 rows were dy +0.203 / +0.805 / +0.211. Probe: scratchpad/card188_fix4_probe.py (removed from tests/ after use).
- [Fix 4][Mutation] M7 ring `top: 0` → killed by TestSolverClues_TheCircleIsVisible::test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] (centring assert)
- [Fix 4][Mutation] M9 ring `top: calc(-1 * var(--player-circle))` → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] (centring assert)
- [Fix 4][Mutation] edge: ring top +1 px → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] (centring assert, dy 0.98/1.32/0.99)
- [Fix 4][Mutation] edge: ring top −1 px → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] (centring assert, dy −1.0/−0.68/−1.0)
- [Fix 4][Mutation] edge: ring left +1 px → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] (centring assert, horizontal)
- [Fix 4][Mutation] edge: ring left −1 px → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] (centring assert, horizontal)
- [Fix 4][Mutation] ring `left: 0` → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] (centring assert)
- [Fix 4][Mutation] row height/line-height fix reverted (whole new rule removed) → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[desktop] (centring assert, row dy +0.805; at 14 and 24 px the pre-fix offset is ≈ 0.2 px, inside the tolerance)
- [Fix 4][Mutation] edge: row line-height cell − 1 px → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] (centring assert)
- [Fix 4][Mutation] row line-height removed (height + margin kept) → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] (row clue box height assert)
- [Fix 4][Mutation] row height removed (line-height + margin kept) → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[desktop] (row clue box height assert, 17.6875 ≠ 17.671875)
- [Fix 4][Mutation] edge: row margin half the thin rule instead of the heavy → killed by test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] (row clue box height assert, heavy-rule rows 15/18.67/25)
- [Fix 4][Mutation] row negative margin removed → killed by TestSolverClues_EveryNumberKeepsAOneCellSlot::test_slots[desktop,phone], test_two_digit_rings_clear_their_digits_on_a_30x30[floor,desktop,phone] and tests/test_puzzle_solver_page.py::TestSolverPageFits::test_the_largest_board_fits_a_laptop_screen[row-clues,column-clues]
- [Fix 4][Mutation] Method: exact string replacement in admin.css, restored from captured bytes, `cmp` OK after every run (never git checkout). Runner: scratchpad/card188_fix4_mutate.py, log scratchpad/card188_fix4_mutants.log. No survivors.
- [Fix 4][Tests] page/marking/progress/clues/phone/design-token files: 214 passed (no test added; the new asserts are inside the existing 30×30 test). AC-8, TestSolverClues_EveryNumberKeepsAOneCellSlot, TestSolverPhone_* (incl. DesktopSizingUnchanged and the 390 px scrolled drag) and the G-1-protected page/marking/progress files pass unchanged; only tests/test_puzzle_solver_clues.py changed.
- [Fix 4][Renders] scratchpad/card188_render.py re-run (device scale 2): every file in ~/Documents/nonogram-reviews/CARD-188/ refreshed, incl. 30x30-{desktop-1100x700,desktop-1440,phone-390}-{board,row-clue,col-clues-0,col-clues-zoom}.png. Eyeballed 4× zooms of the row-clue crops ("16 13"): at 14, 1440 and 390 the digits sit centred top-to-bottom in their pills; the 1440 pill no longer rides low on its digits (it was ≈ 1.2 px low on the ink).
- DESIGN-REGISTER ClueBox: circled — a clue number its marks settle gets a thin round ring in --grid-ink drawn by its ::before (out of layout, centred on the number's box, which for row and column numbers alike is a cell tall with a cell's line-height, so the ring centres on the digits within 0.5 px): a circle for one digit, a pill as wide as the digits plus clearance for two, capped so neighbouring rings keep --player-ring-gap between them; the ring is always present and transparent until circled, so nothing moves, each number keeps main's one-cell slot and each row clue box stays a cell tall.
- [Fix 4] pre-gate: named test green (TestSolverClues_TheCircleIsVisible 5 passed); declarations: 1 updated (admin.css comment: ring centred on the number's box + row cell-tall line box, 0.5 px centring at 14/17.67/24 px; test docstring narrowed to left/right clearance + centring; DESIGN-REGISTER refreshed)
- [Fix commit] fix-1..4 edits committed as c38f9e1 (explicit pathspecs: admin.css, solver.js, tests/test_puzzle_solver_clues.py); branch rebased onto main 5567118 (CARD-181) — c9215d7, 1b42098, c38f9e1
- [Build gate] PASSED (full, 631s; 6440 passed, 9 skipped — after fix 4, rebased on 5567118)
- [Review 4/3] Score: 9.0 — crit: 0, imp: 0 (owner-granted confirmation cycle); F-006/F-007/F-009 ✓ resolved; F-005, F-008 open as Minor; 8f-mutation RAN: 10/10 killed
- [Review sync] 4 report(s) → meta/review/
- [Review 4/3] Step 8h: 52/52 card rules have a verdict line (9 ✓, 43 ⚠ carried delta-clean, 0 ✗) — coverage guard passed
- [Review 4/3] Score: 9.0 ✓ threshold reached + no critical/important
- [Docs] forge:readme check on changed dirs: tests/README.md keeps no per-file inventory (generic run/coverage guide — still current); src/nonogram/admin/static/ has no README and the per-directory README convention is an open owner decision (backlog) — no README change
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0038/R2, ADR-0038/R3, ADR-0038/R4)
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-1 ✓ test_PropertyTest_SolverClues_NeverCirclesWhatBruteForceDoesNot PASSED (6000 seeded lines, min counts asserted in-test); AC-2 ✓ TestSolverClues_RuleExamples PASSED (table + STOPS); AC-3 ✓ test_PropertyTest_SolverClues_AFullyMarkedLineCirclesEverything PASSED (600 lines); AC-4 ✓ test_PropertyTest_SolverClues_BoardIsLineByLine PASSED (120 boards × 3 shapes); AC-5 ✓ TestSolverClues_CirclesFollowEveryCommit PASSED; AC-6 ✓ TestSolverClues_AmbiguousRunStaysUncircled PASSED; AC-7 ✓ TestSolverClues_DragPreviewDoesNotCircle PASSED; AC-8 ✓ TestSolverClues_CirclingMovesNothing[desktop,phone] PASSED; AC-9 ✓ TestSolverClues_TheCircleIsVisible (incl. 30×30 floor/desktop/phone) PASSED; AC-10 ✓ demonstrated as a deliverable — renders exist and show the listed content (mid-solve 15×15 at 1440 and 390, circled row/column numbers, two-digit '12'/'15', owner's '2 2' uncircled, click before/after) [the agent marked it ⚠ partial only because the owner's visual sign-off is outside this gate; per the wave brief that sign-off is a pre-merge check, recorded here, not a code gap]; G-1 ✓ page/marking/progress 176 passed, page/progress diff empty, marking diff = the amendment only; G-2 ✓ touches_no_dom + no_colour_literals PASSED; G-3 ✓ no network/storage API in added lines, circledClues(history.board, payload.rows, payload.columns); G-4 ✓ marking/progress green, unweakened; G-5 ✓ no diff under src/nonogram/solver/ or clues.py; G-6 ✓ circles are class toggles only
- [Commit] success commit 1f378cc (empty marker commit carrying the review summary; all code already in c9215d7, 1b42098, c38f9e1) — diff vs main: 5 files, +871/−2
- [Merge gate] branched from 5567118 (= main at merge); pipeline full suite 6440 passed, 9 skipped (same tree, not re-run). Owner: "merge now, check later" (renders in ~/Documents/nonogram-reviews/CARD-188/). Merged 0d7c82e.
