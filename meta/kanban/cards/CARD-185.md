# CARD-185: The puzzle player reopens a puzzle in the state it was left in (this browser only)

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/185-player-resume-in-browser
**Worktree:** —
**Source:** owner's solver test doc 2026-10-05, item 1
**Idea:** —
**Wave:** 35
**Depends on:** CARD-183, CARD-186
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_resume.py, tests/test_puzzle_solver_progress.py, tests/test_puzzle_solver_maybe.py
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-10-06T06:13:30Z
**Closed:** 2026-10-06T09:01:23Z
**Actual:** 0.3d
**Merge commit:** ae25661
**Blocked by:** —

## What to implement

**Owner decision (2026-10-05, "Solver - test" doc, item 1).** Closing the tab
mid-puzzle and coming back reopens the puzzle in the same state. This browser
only: the state goes to `localStorage`, one entry per puzzle, written on every
change, with no server call (ADR-0038/R2). It restores the board, the error
count, the hint count (CARD-183) and the undo/redo history. Reset clears it.
A solved puzzle reopens solved.

**Current behaviour (verified by reading the code).**
- `static/solver.js` `start()` (~lines 227–296) always begins at
  `createBoard(payload.width, payload.height)` and a fresh `createHistory`.
  Nothing is read from or written to browser storage. Closing the tab loses
  every mark.
- Every recorded change goes through one path: `wireMarking`'s `commit`
  (~line 337) calls the player's `commit(next)` in `start()`. That repaints and
  runs `showProgress()`. Strokes, undo, redo, the confirmed reset (~line 411)
  and the `setBoard` seam all use it. A drag preview uses `show()` and is not
  recorded.
- The history is `{board, done: [{stroke, before}], undone: [stroke]}`
  (`solver_state.js`). The error count and the solved state are functions of
  the current board only. CARD-183 makes the hint count a function of
  `history.done` (strokes with `hint: true`). So saving the strokes is enough
  to restore all three.
- Two existing tests pin "no storage": `test_puzzle_solver_progress.py:727`
  asserts `localStorage.length + sessionStorage.length == 0`, and
  `test_puzzle_solver_page.py:527` forbids the substring `localStorage` in
  `solver_state.js`.

**Target behaviour.**

1. **Pure functions in `solver_state.js` (no DOM, no storage).**
   - `SAVE_VERSION = 1`.
   - `saveKey(puzzleId)` returns `"nonogram-player:" + puzzleId`. The key has
     no version in it; the version lives in the value, so a future format
     replaces the same entry instead of leaving an orphan.
   - `gridFingerprint(solution)` returns a 32-bit FNV-1a hash (hex string) of
     the solution read row-major as `"1"`/`"0"`. The solution itself is never
     saved.
   - `serializeState(history, payload)` returns a JSON string:
     `{v: 1, id, width, height, rows, columns, grid, done: [stroke...],
     undone: [stroke...]}`. `rows`/`columns` are copied from the payload.
     `grid` is `gridFingerprint(payload.solution)`. `done` lists the strokes of
     `history.done` in order, `undone` lists `history.undone` in its stack
     order. A saved stroke is `{cells: [[row, col], ...], state}` plus
     `hint: true` only when the stroke has it. No other field is saved.
   - `deserializeState(text, payload)` returns a history, or `null` when the
     text cannot be trusted. It never throws, whatever the text. It returns
     `null` when:
     - the text is not JSON, or not an object;
     - `v` is not `SAVE_VERSION`;
     - `id`, `width` or `height` differ from the payload;
     - `rows` or `columns` are not deep-equal to the payload's (clue
       mismatch);
     - `grid` differs from `gridFingerprint(payload.solution)` (the stored
       puzzle's grid changed);
     - any stroke is malformed: `cells` is not an array of `[int, int]` inside
       the board, `state` is not in `CELL_STATES` (which includes CARD-186's
       "?" state once it lands), or `hint` is present and not `true`;
     - a `done` stroke changes no cell when replayed (`record` would drop it),
       or an `undone` stroke could not be redone as a step.
     Otherwise it rebuilds the history from a blank board with the existing
     functions (`createHistory`, `record`, `undo`). The result has the same
     board, the same `done` strokes and the same `undone` stack as the history
     that was saved.
2. **Storage access in `solver.js` only.**
   - At start-up, after the board is drawn and before the first
     `showProgress()`, read `localStorage.getItem(saveKey(payload.id))`. If
     `deserializeState` gives a history, start from it. If it gives `null`
     for an entry that exists, remove that entry and start blank.
   - After every recorded change (the player's `commit` in `start()`), write
     `serializeState(history, payload)` under the key. That covers strokes,
     hints, undo, redo and `setBoard`. A drag preview writes nothing.
   - A confirmed reset removes the key instead of writing it. The in-page
     undo of that reset still works as today (FR-044), and the next recorded
     change writes the entry again.
   - Every storage access, including reading the `window.localStorage`
     property itself, is wrapped in `try`/`catch`. When storage is disabled
     or throws (private mode, `SecurityError`, quota), the player works
     exactly as it does today and nothing is logged to the console. When a
     write fails, try once to remove the key, so a reload never shows an older
     state than the one on screen.
   - No network request is added. The payload shape is unchanged.
3. **What a reopened page shows.**
   - The board, the error count and "Hints: N" match the state before the
     reload. Undo and Redo work across the reload, with the same steps.
   - A board that was solved reopens solved: the banner shows and the board
     is locked, through the existing `showProgress()` path. Reset is
     available as usual.
   - The selected tool is not saved. It is the filled tool at load, as today.

**Owner-visible defaults this card picks (confirm from the renders):**
- (a) Reset clears the saved entry. After reset and reload the board is blank
  and the reset can no longer be undone. Before a reload, Undo still brings
  the marks back, as today.
- (b) A puzzle restored solved shows the solved banner and plays the existing
  solved animation (none under reduced motion), as on a fresh solve.
- (c) The tool selection is not restored.
- (d) Two tabs on the same puzzle: the last change written wins. There is no
  sync between tabs.
- (e) Entries for deleted puzzles stay in the browser until the browser data
  is cleared. Nothing prunes them.

## Acceptance criteria

- **AC-1:** Given a seeded corpus of at least 300 random histories over shapes (10, 10), (15, 10), (10, 25) and (30, 30), built from clicks, drags, resets, hints, "?" marks, undos and redos, when each is passed through `serializeState` then `deserializeState`, then the board, the `done` strokes (cells, state, hint flag), the `undone` stack, `errorCount` and `hintCount` all equal the original's. The test asserts minimums: ≥ 50 histories with a non-empty redo stack, ≥ 50 with a hint, ≥ 50 with a "?" mark, ≥ 30 that end solved.
  *test: PropertyTest_SolverResume_SaveAndRestoreRoundTrip (in tests/test_puzzle_solver_resume.py)*
- **AC-2:** Given at least 500 corrupted saves made from valid ones (truncated text, wrong `v`, wrong `id`, changed size, one clue number changed, wrong `grid`, a cell out of range, an unknown state, a non-`true` `hint`, a no-op `done` stroke, non-object JSON), when `deserializeState` runs on each, then it returns `null` and never throws. Each corruption kind appears at least 20 times, asserted in the test.
  *test: PropertyTest_SolverResume_RejectsAnyUntrustedSave (in tests/test_puzzle_solver_resume.py)*
- **AC-3:** Given a 15×15 player page with five strokes, one hint, one "?" mark and one undo, when the page is reloaded, then the board, "Errors: N" and "Hints: N" are the same as before, Redo puts back the undone stroke, and Undo then steps back through the earlier strokes in order.
  *test: TestSolverResume_ReloadRestoresBoardCountsAndHistory (in tests/test_puzzle_solver_resume.py)*
- **AC-4:** Given a solved board, when the page is reloaded, then the solved banner shows, the board is locked (a click changes no cell), and Reset is available.
  *test: TestSolverResume_SolvedPuzzleReopensSolved (in tests/test_puzzle_solver_resume.py)*
- **AC-5:** Given a board with marks, when Reset is confirmed, then the puzzle's storage key is absent; after a reload the board is blank, both counters read 0, and Undo and Redo are disabled.
  *test: TestSolverResume_ResetClearsTheSave (in tests/test_puzzle_solver_resume.py)*
- **AC-6:** Given a saved entry for puzzle A, when it is copied under puzzle B's key (same size, different grid, `id` rewritten to B), and also when the entry holds corrupt JSON, and also when its `v` is 2, then opening B (or reloading) shows a blank board, logs nothing to the console, raises no page error, and the next mark writes a valid entry.
  *test: TestSolverResume_UntrustedSaveStartsFresh (in tests/test_puzzle_solver_resume.py)*
- **AC-7:** Given an init script that makes `localStorage.setItem` throw a `QuotaExceededError`, and separately one that makes reading `window.localStorage` throw a `SecurityError`, when the player is used (marks, undo, reset, solve), then every action works as without storage, and the console and page-error logs stay empty.
  *test: TestSolverResume_BrokenStorageDegradesSilently (in tests/test_puzzle_solver_resume.py)*
- **AC-8:** Given a loaded player page, when twenty strokes, two undos, a hint and a reload are made, then no network request is issued for any mark (ADR-0038/R2), and the entry under the puzzle's key changes after each recorded change.
  *test: TestSolverResume_SavesEveryChangeWithoutARequest (in tests/test_puzzle_solver_resume.py)*
- **AC-9:** Given `solver_state.js`, when its source is read, then the new functions exist there and it still has no `document`, `window`, `globalThis`, `fetch`, `localStorage` or `import ` (the existing check, unchanged).
  *test: test_the_state_module_touches_no_dom (in tests/test_puzzle_solver_page.py, unchanged)*
- **AC-10:** Owner render: a 15×15 board with marks before and after a reload, a solved board after a reload, and a blank board after Reset and reload, saved in ~/Documents/nonogram-reviews/CARD-185/.
  *test: review-lens (owner visual check of the renders)*

## Guardrails

- G-1: Every existing player test stays green unchanged, with one exception: the storage assertion at `test_puzzle_solver_progress.py:727`. It becomes "`sessionStorage` is empty and `localStorage` holds at most one key, `saveKey(this puzzle's id)`". Its request and console assertions stay as they are. This includes EC-035 `PropertyTest_SolverHistory_ReplayReproducesTheBoard`, AC-311 `TestSolverMarking_NoRequestPerMark`, and CARD-183's and CARD-186's tests.
- G-2: ADR-0038/R4: `serializeState`, `deserializeState`, `saveKey` and `gridFingerprint` live in `solver_state.js` and stay pure. All `localStorage` access is in `solver.js`. `test_the_state_module_touches_no_dom` is not edited.
- G-3: ADR-0038/R2/R3: no network request per mark, nothing new sent to the server, and the payload keeps exactly its keys (`test_the_payload_has_exactly_the_documented_shape`, `test_puzzle_solver_page.py` ~line 225).
- G-4: CON-021 / CON-017 server side: nothing about play is written to a database, file or server. `TestSolverPage_WritesNothing` (AC-302) stays green. The solution grid is never written to storage, only its fingerprint.
- G-5: FR-044 behaviour is unchanged: the click and drag rules, the error count, the solved predicate, the lock, the confirmed reset and its in-page undo. CARD-183's hint rules (count follows undo) and CARD-186's "?" rules are unchanged.
- G-6: No new static file, so `pyproject.toml` package-data and the wheel test stay as they are. No colour literals in the scripts (`test_the_scripts_carry_no_colour_literals`).
- G-7: No console output from storage handling, in any case (the `_watch_problems` checks in `test_puzzle_solver_progress.py` stay empty).

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-185` (52 rules). A projection — fix the source artifact, never this list._

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

- **Formalized 2026-10-06:** FR-044 AC-360..AC-365, EC-046, EC-047; CON-021 amended 2026-10-06 (this-browser localStorage admitted)

- **FR-044** (puzzle player, AC-296..AC-323, EC-035..EC-037). Its statement ends "no play state is persisted", and its comment says every mark "is gone when the page closes" (requirements.yml ~lines 3681–3714). This card contradicts both on the browser side. Card-local ACs only; an architect delta is needed (see Worktree notes).
- **CON-021** says play state is never "written to a database, file or server". Browser `localStorage` is none of the three, but CON-021's intent ("Play state is never persisted") needs the delta to say so explicitly. **CON-017** (no persistence on the server side) is unchanged.
- **ADR-0038** R1 (plain JS), R2 (no request per mark, `TestSolverMarking_NoRequestPerMark`), R3 (payload clues only), R4 (pure state module), R6 (solution only in the admin player; never stored).
- Components: COMP-008 area (admin panel adapter, `src/nonogram/admin/`). TERM-037 (puzzle player), TERM-038 (error count), TERM-039 (stroke).
- Trace: owner doc "Solver - test" item 1 → CARD-185 → FR-044 (extension, no AC id yet).

## Design context

- **Screen:** the admin puzzle player, `/puzzle/<id>/solve`. Nothing new is drawn; what changes is what the page shows when it is reopened.
- **Owner-visible defaults:** (a)–(e) in "What to implement": Reset clears the save, a restored solved puzzle replays the solved animation, the tool is not restored, last tab wins, no pruning. The owner confirms or overrides these from the renders before merge.
- **Renders:** ~/Documents/nonogram-reviews/CARD-185/ (owner visual check). PNG frames or a short GIF: marks with a hint and a "?" → reload → same board and counters; solved → reload → solved banner; Reset → reload → blank.

## Worktree notes

- [Origin] Owner's solver test doc ("Solver - test", Google Doc, 2026-10-05), item 1: reopen the puzzle in the same state. Owner decision: this browser only, `localStorage` per puzzle, written on every change with no server call; restores board, error count, hint count and undo/redo; cleared on Reset; a solved puzzle reopens solved. No IDEA id.
- [Depends] CARD-183 adds `hint: true` strokes and `hintCount(history)`; the save must carry the `hint` flag, or the hint count is lost on reload. CARD-186 adds the "?" cell state; `deserializeState` checks states against `CELL_STATES`, so "?" marks round-trip once it is in that list. Build on both after they merge. AC-1 and AC-3 use hints and "?" marks, so they need both.
- [Spec] FR-044's statement ("no play state is persisted") and CON-021's "Play state is never persisted" need an architect delta: allow browser-local saving of the admin player's state, keep the server-side ban. Do not edit meta/ from the card. CARD-183's own G-4 ("no storage") is superseded by this card for the hint count.
- [Facts] `test_puzzle_solver_page.py:527` strips only `//` comments before searching `solver_state.js` for `localStorage`, `window`, etc. Do not write those words in a `/* */` comment there either.
- [Facts] `test_puzzle_solver_progress.py:727` (`TestSolverProgress_StaysInThePage`) ends on an Undo of a reset from solved, so the board is solved and an entry exists at the end. That one assertion must change (G-1). Nothing else in the three existing player test files reads storage.
- [Facts] pytest-playwright's `page` fixture (via `browser_page`, `test_puzzle_solver_page.py:561`) gives a fresh browser context per test, and `live` serves on an ephemeral port, so storage never leaks between tests. `page.reload()` inside one test keeps the storage, which is what the reload tests need. Use `page.add_init_script` for AC-7's broken storage. `_watch_problems` (`test_puzzle_solver_progress.py:188`) collects console and page errors.
- [Facts] `record` drops a stroke that changes no cell, so a valid saved `done` list replays one step per stroke. Rebuilding the redo stack: record the `undone` strokes from the top of the stack down, then undo that many times; check each was a step. The pure-module test pattern is `page.evaluate("async (...) => { const S = await import('/static/solver_state.js'); ... }")`, as in `test_puzzle_solver_progress.py` `_PURE`.
- [Facts] Write after the player's `commit` in `start()`, not in `show()`: drag previews must not write. The confirmed reset is the handler at `solver.js` ~line 411; it must leave the key absent after its `commit`.
- [Conflict] CARD-183 and CARD-186 both edit `solver_state.js` and `solver.js`, and the other "Solver - test" cards (items 2–5) may too. Rebase after them. Keep this card's changes to the four pure functions, the start-up read, the write after commit, and the reset removal.
- [AC cross-check] All ACs re-read against "What to implement". Reset removal (AC-5) matches default (a); the invalidation list in AC-2/AC-6 matches item 1's `null` cases; AC-8's "changes after each recorded change" matches "write after every recorded change", with drag previews excluded in the body and not tested as writes. No edits were needed.
- [Architect 2026-10-06] CON-021 is amended: this-browser localStorage per puzzle is admitted (nothing on the server, no request per mark). FR-044 AC-360..AC-365 / EC-046..EC-047 formalize this card. NOTE: CARD-186's AC-15 test (TestSolverMaybe_NoRequestPerMark) asserts local/session storage stays empty — this card must narrow it to "nothing but this puzzle's one save" (added to Touches).
- [Env] forge 2026.8.17
- [System contract] fresh assembly (system_rules.py --card CARD-185, 2026-10-06) = card section: 52 ids, no +/−; CON-021 statement injected in its amended 2026-10-06 wording
- [Implementation] agent spawned 2026-10-06T06:20Z (general-purpose, no model param); G-1 storage exception extended to tests/test_puzzle_solver_hint.py:870 (same pattern; card [Spec] note: CARD-183 G-4 superseded) — to be recorded as SCOPE+
- [Impl 2026-10-06] Commit 7bf1c4a on card/185-player-resume-in-browser. `solver_state.js`: SAVE_VERSION = 1, saveKey(id) = "nonogram-player:" + id, gridFingerprint (32-bit FNV-1a of the solution row-major "1"/"0", 8 hex digits), serializeState, deserializeState (pure; JSON.parse in its own try; null for anything untrusted; rebuilds with createHistory/record/undo, redo stack recorded top-down then undone). `solver.js`: one small adapter `browserSave(key)` {read, write, forget}, each localStorage access (incl. reading `window.localStorage`) in its own try/catch, silent; start() reads before the first showProgress (untrusted entry → forget, blank start); the player's `commit` writes after showProgress (strokes, hints, undo, redo, setBoard; `show()` = drag preview writes nothing); the confirmed-reset handler calls `player.forget()` after its commit; a failed write → one removeItem.
- [Impl] Save format: `{v:1, id, width, height, rows, columns, grid, done:[stroke...], undone:[stroke...]}`, stroke = `{cells:[[r,c],...], state}` + `hint:true` only on hint strokes (CARD-183's `hint` field is the only extra stroke field today). States checked against CELL_STATES (incl. CARD-186 "maybe"). Never the solution.
- [Impl] Design decision not in the card: setBoard (test seam) can start a history at a NON-blank board, which a blank-board replay cannot reproduce. serializeState returns null for such a history (start board = done[0].before, or board when done is empty) and solver.js removes the key then, so a reload starts blank instead of restoring a wrong board. Tests: TestSolverResumeModule_OnlyABlankStartIsSaved, TestSolverResume_SetBoardStartIsNotSaved. Consequence: tests that set up via setBoard (e.g. progress.py's `_solve`) leave no save.
- [Impl] Extra tests beyond the named ones (same file): TestSolverResumeModule_KeyAndFingerprint (saveKey / FNV-1a vs Python), TestSolverResumeModule_OnlyABlankStartIsSaved, TestSolverResume_SavesEveryChangeWithoutARequest::test_a_drag_preview_writes_nothing, TestSolverResume_SetBoardStartIsNotSaved. AC-4's solved board is reached by real input only (row drags + clicks), since a setBoard start is not saved.
- SCOPE+ tests/test_puzzle_solver_hint.py — the storage assertion at ~870 narrowed exactly like progress.py:727 (G-1 exception extended per the card's [Spec] note: CARD-183 G-4 superseded); request/console asserts unchanged. (Plus `_ONLY_THIS_SAVE` added to its import list from progress.py.)
- [Impl] G-1 exceptions applied: progress.py:727 and maybe.py:900 (two lines: the evaluate and its assert) now assert `_ONLY_THIS_SAVE` (new constant in progress.py: sessionStorage empty and localStorage empty or exactly one key 'nonogram-player:' + payload.id). Request and console asserts untouched. Honest scope: progress.py:727's flow ends on a setBoard-started history, so it ends with NO entry — it pins "nothing else stored", not the key name; the maybe/hint tests end with exactly one entry and were shown failing on a saveKey-prefix mutant ("nonogram-player-").
- [Impl] test_the_state_module_touches_no_dom unchanged and green; none of document/window/globalThis/fetch/localStorage/"import " appears in solver_state.js outside `//` comments. No new static file; no colour literals.
- [Mutants] Each applied alone, resume file run, reverted (script: scratchpad card185_mutants.py). All 27 killed: v-check dropped → RejectsAnyUntrustedSave; id-check → Rejects; size-check → Rejects; rows-check → Rejects; columns-check → Rejects; grid-check → Rejects; no-op check (`next === history`) → Rejects; hint !== true accepted → Rejects; row edge `< height`→`<=` → Rejects; col edge `< width`→`<=` → Rejects; `row >= 0` dropped → Rejects; pair length `=== 2`→`>= 1` → Rejects; state check dropped → Rejects (throws); JSON.parse try dropped → Rejects + UntrustedSaveStartsFresh[corrupt-json]; redo stack order (`.reverse()` dropped) → SaveAndRestoreRoundTrip; hint flag not saved → RoundTrip + ReloadRestores + Rejects; blank-start null dropped → OnlyABlankStartIsSaved + SetBoardStartIsNotSaved; FNV offset changed → KeyAndFingerprint + RoundTrip + UntrustedSaveStartsFresh; skip the write in commit → 10 page tests incl. ReloadRestores, SavesEveryChange, ResetClears, SolvedReopens; reset without forget (= write instead of remove) → ResetClearsTheSave; setItem try dropped → BrokenStorage (both); failed write without remove → BrokenStorage::test_quota_exceeded; getItem/`window.localStorage` try dropped → BrokenStorage::test_security_error; removeItem try dropped → test_security_error; write inside show() → test_a_drag_preview_writes_nothing; untrusted entry kept at load → UntrustedSaveStartsFresh (all 3); restored history ignored → ReloadRestores, SavesEveryChange, quota test, ... Survivors: none.
- [Owner default] (a) Reset clears the saved entry; after reset + reload the board is blank and the reset cannot be undone; before a reload Undo still brings the marks back (and writes the entry again) — implemented as drafted (TestSolverResume_ResetClearsTheSave).
- [Owner default] (b) A puzzle restored solved shows the banner and plays the existing solved animation (none under reduced motion) through the unchanged showProgress transition — implemented as drafted (banner/lock/announce/.is-solved asserted in TestSolverResume_SolvedPuzzleReopensSolved; the animation itself is the existing CSS on .is-solved, not separately asserted here).
- [Owner default] (c) The tool selection is not restored (Black pressed after reload) — implemented as drafted (asserted in ReloadRestores).
- [Owner default] (d) Two tabs on one puzzle: last write wins, no sync — implemented as drafted (no code; not tested).
- [Owner default] (e) Entries for deleted puzzles are never pruned — implemented as drafted (no code; not tested).
- [Renders] ~/Documents/nonogram-reviews/CARD-185/: 00-main-today-after-reload.png (main 40b0a17: same marks, reload → blank, counters 0), 01-marks-before-reload.png (15×15: black drag, black click, white drag, two "?", one hint, a black click; Errors 8, Hints 1), 02-marks-after-reload.png (identical board and counters), 03-solved-after-reload.png ("Solved: Lighthouse" banner, board locked, Undo/Redo/Hint disabled, Reset enabled), 04-blank-after-reset-and-reload.png (blank, Errors 0, Hints 0, Undo/Redo/Reset disabled). All five viewed. Script: scratchpad card185_renders.py (live-fixture approach: temp SQLite, loopback, ephemeral port).
- [Tests] tests/test_puzzle_solver_resume.py: 15 passed. All tests/test_puzzle_solver_*.py: 281 passed, 0 failed (4:28). Full suite not run (orchestrator's).
- [Scope] src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, tests/test_puzzle_solver_hint.py, tests/test_puzzle_solver_maybe.py, tests/test_puzzle_solver_progress.py, tests/test_puzzle_solver_resume.py
- [Scope gate] cycle 1: IN_SCOPE — 1/6 files outside Touches (tests/test_puzzle_solver_hint.py, SCOPE+ recorded, 17% < 25%); no comp spread; guardrails structural: none hit
- [Build gate] PASSED (full, 898s) — 6513 passed, 9 skipped (baseline 6498 + 15 new)
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1 (pre-adversarial; F-001 undone-stroke no-op rejection untested, mutant survives)
- [Review sync] 1 report(s) → meta/review/
- [Adversarial] F-001 CONFIRMED — skeptic reproduced the surviving mutant (line 644 check disabled for undone strokes: resume file 15 passed); _corrupt no-op kind only inserts into done
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Fix 1] F-001 (cycle 1): AC-2 property test (test_PropertyTest_SolverResume_RejectsAnyUntrustedSave) gains corruption kind `undone-no-op` — a copy of the last done stroke appended as the new top of `undone` (the next redo, which would change no cell); 50 cases, all asserted null, covered by the existing `min(counts.values()) >= 20` per-kind assertion (every usable base save has a non-empty `done`). Docstring names the new kind. No production change. Resume file: 15 passed.
- [Fix 1 mutants] Backup + cmp-verified restore, no git restore. (1) solver_state.js:644 → `if (next === history && done.includes(stroke)) return null;` (check off for undone strokes): RejectsAnyUntrustedSave FAILS on `undone-no-op` (verdict 'history'). (2) → `if (next === history && !done.includes(stroke)) return null;` (check off for done strokes): RejectsAnyUntrustedSave FAILS on the existing `no-op` kind. Unmutated: 15 passed.
- [Fix 1 correction] The [Mutants] line's "Survivors: none" was incomplete: the partial mutant (check disabled for undone strokes only) survived cycle 1 — killed now by `undone-no-op`. Its "no-op check (`next === history`) → Rejects" entry stays correct. The deserializeState docstring (solver_state.js:617-621, "an `undone` stroke that cannot be redone as a step") is re-checked and confirmed, now backed by a test. AC-2's card wording lists only "a no-op `done` stroke"; the test now goes further than AC-2 lists (card wording is the architect's, not edited here).
- [Fix 1] pre-gate: FIXED F-001 named test test_PropertyTest_SolverResume_RejectsAnyUntrustedSave — 1 passed; DECLARATIONS line present
- [Fix 1] declarations: 1 updated (test docstring), 1 confirmed (deserializeState docstring), 0 none
- [Build gate] PASSED (full, 900s) — 6513 passed, 9 skipped
- [Scope gate] cycle 2: IN_SCOPE (fix delta: tests/test_puzzle_solver_resume.py only)
- [Review 2/3] Score: 9.5 — crit: 0, imp: 0 (confirmation mode; F-001 ✓ resolved, M7 killed; F-002/F-003/F-004/F-005 Minor open; 8f mutation 8/8 killed)
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h coverage: 52/52 card rule ids have a verdict line (12 ✓, 40 ⚠ no_eligible_fact, 0 ✗; 41 carried delta-clean)
- [Review 2/3] Score: 9.5 ✓ threshold reached + no critical/important
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0038/R1, ADR-0038/R2, ADR-0038/R3)
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — test_PropertyTest_SolverResume_SaveAndRestoreRoundTrip PASSED (seeded, 320 histories; in-test minimums ≥300 / redo≥50 / hint≥50 / maybe≥50 / solved≥30)
  AC-2 ✓ demonstrated — test_PropertyTest_SolverResume_RejectsAnyUntrustedSave PASSED (12 kinds × 50 = 600; min per kind ≥20 asserted)
  AC-3 ✓ demonstrated — TestSolverResume_ReloadRestoresBoardCountsAndHistory::test_reload_restores PASSED
  AC-4 ✓ demonstrated — TestSolverResume_SolvedPuzzleReopensSolved::test_solved_reopens_solved PASSED
  AC-5 ✓ demonstrated — TestSolverResume_ResetClearsTheSave::test_reset_clears PASSED
  AC-6 ✓ demonstrated — TestSolverResume_UntrustedSaveStartsFresh [other-puzzle] [corrupt-json] [version-2] PASSED
  AC-7 ✓ demonstrated — TestSolverResume_BrokenStorageDegradesSilently::test_quota_exceeded, ::test_security_error PASSED
  AC-8 ✓ demonstrated — TestSolverResume_SavesEveryChangeWithoutARequest::test_saves_every_change PASSED
  AC-9 ✓ demonstrated — TestPlayerAssets::test_the_state_module_touches_no_dom PASSED, file unedited
  AC-10 ✓ demonstrated (observable check only) — 4 named renders present and viewed; owner sign-off is a pre-merge check outside this gate
  G-1 ✓ demonstrated — all 8 tests/test_puzzle_solver_*.py: 281 passed; only storage asserts changed in progress.py:733, maybe.py ~901, hint.py ~871 (hint.py = SCOPE+ extension, not in G-1's literal text); request/console asserts intact
  G-2..G-7 ✓ demonstrated — see AC-check agent output (payload shape, WritesNothing, no new static file, no colour literals, no console call in diff)
- [Docs] forge:readme: no README in src/nonogram/admin/static/; no directory structure/purpose change (new test file only) — skipped (per-directory README convention is an open owner decision in the backlog)
- [Commit] success commit a7e72d2 (fix F-001, test-only) on top of 7bf1c4a (implementation); diff vs main: 6 files, +908/−7
- [Open Minor] F-002 owner check: after Reset, the next change re-saves the full pre-reset history (reset is an undoable stroke), so reset → one mark → reload → Undo walks back past the reset; card text "the next recorded change writes the entry again" vs default (a) "Reset clears it" — owner to confirm. F-003 setBoard non-blank start not saved (card/AC-365 wording). F-004 G-1 exception extended to hint.py:870 (record in G-1). F-005 undone-no-op corruption only at top of redo stack (breadth).
- [Owner decision] 2026-10-06 — F-002: keep Reset undoable (a reload after Reset + a mark can still Undo past the reset); renders accepted.
- [Merge gate] branched from 40b0a17 (= main at merge); pipeline full suite 6513 passed, 9 skipped (same tree, not re-run). Owner accepted the renders and kept Reset undoable (F-002). Merged ae25661.
