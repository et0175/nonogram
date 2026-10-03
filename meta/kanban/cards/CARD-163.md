# CARD-163: The puzzle player keeps the picture name hidden until it's solved

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/163-player-hides-picture-name
**Worktree:** —
**Source:** owner decision 2026-10-03 on CARD-162 review finding F-007; raw-requirements.md Delta 2026-10-03 (b); FR-044 amended (AC-322, AC-323)
**Idea:** —
**Wave:** 31
**Depends on:** CARD-162
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/app.py, tests/test_puzzle_solver_page.py, tests/test_puzzle_solver_progress.py, src/nonogram/admin/static/solver.js
**Review score:** 9.3 (cycle 1/3)
**Started:** 2026-10-03T16:13:13Z
**Closed:** 2026-10-03T16:54:33Z
**Actual:** 0.1d
**Merge commit:** 159d6ad
**Blocked by:** —

## What to implement

CARD-160's player page prints the picture's name in its header,
`<h1>Puzzle {{ title }}</h1>`, and in the browser tab,
`{% block title %}Puzzle {{ title }} …`. The picture name is the answer: the
solved state reveals it (AC-316, AC-319), and the printed book never prints it
on a puzzle page (ADR-0037/R1).

1. Before the puzzle is solved, the visible header and the document title
   show the puzzle's **size and tier** (e.g. "25×15 · Medium"), never the
   picture name.
2. The solved state still reveals the name, as CARD-162 built it. Don't
   change the solved banner. If the tab title should also gain the name on
   solve, that's fine but not required; keep it consistent with the header.
3. The embedded JSON payload may keep carrying the name for the solved
   reveal (CON-021 already allows the solution in the page for the admin
   player). The requirement is about what the page **shows**.
4. Update the CARD-160 tests that assert the old "Puzzle <title>" header.
   Update them for the new behaviour; don't weaken them.
5. **Ride-along, CARD-162 F-010 (Minor):** the solver.js header says the reset
   confirmation closes on an undo or redo "button or key — even one that
   changes nothing", but only the key no-op is tested, so mutant M11 survives.
   Add a `redo-button-noop` case to `_CHANGES` in
   `TestSolverProgress_ResetAfterConfirm::test_a_board_change_while_asking_closes_the_confirmation`
   (tests/test_puzzle_solver_progress.py) and show it kills M11. Test-only;
   no behaviour change.

## Acceptance criteria

_Verbatim from FR-044 in meta/architecture/requirements.yml (amended 2026-10-03, Delta (b))._

- **AC-322** (negative): *Given* a stored puzzle with a picture name, whose player page is loaded and not yet solved, *when* the page's visible header and the browser document title are read, *then* neither contains the picture name.
  *test: TestSolverPage_HidesThePictureNameUntilSolved*
- **AC-323** (happy): *Given* the unsolved player page of AC-322, for a 25x15 puzzle of tier "medium", *when* the page's visible header is read, *then* it shows the puzzle's size "25x15" and its tier "medium" in place of the name.
  *test: TestSolverPage_HidesThePictureNameUntilSolved*

## Guardrails

- G-1: AC-316 and AC-319 still hold: the solved state shows the picture name, also under reduced motion. CARD-162's tests stay green without edits.
- G-2: No change to marking, history, error count or solved logic (`solver_state.js`, and `solver.js` beyond what the header needs).
- G-3: Other admin screens keep showing names. The puzzle list, detail modal and books are the owner's review tools, not the player.
- G-4: No new runtime dependency (ADR-0006/R1).

## System contract

_Assembled 2026-10-03 by `system_rules.py --card CARD-163` (53 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit… (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when… (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn;… (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on… (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp <… (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the… (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a… (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no… (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the… (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle… (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the… (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin… (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm… (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R5 — pyproject.toml package-data for nonogram.admin includes static/*.js alongside templates/*.html and static/*.css, so the player's script ships in every built wheel. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No… (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode)… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031,… (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's… (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5… (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is… (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns… (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the… (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-044 (AC-322, AC-323; AC-316/AC-319 unchanged); US-028; CAP-007
- **ADR:** ADR-0038; ADR-0037/R1 (the printed-page parallel)
- **CON:** CON-021
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ (tokens only)
- **Screens:** /puzzle/<id>/solve (header, before and after solve)
- **Renders:** ~/Documents/nonogram-reviews/CARD-163/ (unsolved header, solved state)

## Worktree notes

- [Origin] Cut 2026-10-03 at the owner's decision on CARD-162 F-007 ("hide it until solved"). Runs after CARD-162 because both edit the player page.
- [Scope] 2026-10-03 — CARD-162 F-010 folded in at the dispatcher (one test case, same file area); Touches gains tests/test_puzzle_solver_progress.py and solver.js (header comment only, if the wording needs it).
- [Env] forge 2026.8.17
- [Impl] 2026-10-03 — commit 0f668fc. `puzzle_solve` passes `extent=(width, height)` from the payload (len(grid[0]), len(grid); ADR-0022/R1 width first). Header is `<h1>Puzzle {{ extent[0] }}x{{ extent[1] }}</h1>` + the unchanged tier badge; tab title is `Puzzle 25x15 · MEDIUM - Nonogram admin` (no tier → `Puzzle 25x15 - Nonogram admin`). `title` now reaches only the solved banner (`data-player-solved-name`), unchanged. Payload unchanged (it never carried the name). Template header comment fixed (the banner no longer "names the picture with the same title as the header"); route docstring says where the name goes.
- [Impl] Size uses ASCII "x" to match AC-323's literal "25x15" (other admin screens use "×"). The tier badge renders `tier.value.upper()` = "MEDIUM" (CARD-160's existing spelling, kept); AC-323's "medium" is therefore asserted case-insensitively (`"medium" in header.lower().split()`) and pinned exactly as rendered (`header == "Puzzle 25x15 MEDIUM"`).
- [Tests] New `TestSolverPage_HidesThePictureNameUntilSolved` (tests/test_puzzle_solver_page.py): AC-322 (memory+sqlite) — name "Quokka lantern"/source "quokka-lantern.png" absent from header text and <title>, paired with a positive check that the same name IS in the (hidden) solved banner; AC-323 (memory+sqlite); one browser test — after the board is drawn and after setBoard solves it, header and document.title are unchanged and the banner shows the name (backs the template claim that solver.js rewrites neither; solver.js has no reference to h1/document.title and was not edited). CARD-160 `TestSolverPageHeader` updated: "Puzzle 25x15" instead of "Puzzle Snowy owl"; the no-tier case now also pins the title; the source/id fallback test now asserts the fallback lands in the banner and never in header/title.
- [Tests] F-010: `redo-button-noop` added to `_CHANGES` (Redo clicked with force=True — it is aria-disabled, which Playwright treats as unclickable). The no-op branch condition changed from `change == "redo-key-noop"` to `change in ("redo-key-noop", "redo-button-noop")` so the new case takes the existing no-op assertions; no existing assertion or case changed.
- [Tests] Ran tests/test_puzzle_solver_page.py + test_puzzle_solver_progress.py + test_puzzle_solver_marking.py: 176 passed, 0 skipped (browser tests executed under Chromium; new ones confirmed PASSED with -rA).
- M11 (undo/redo click handler skips commit while aria-disabled: `if (!gesture && actions[name].getAttribute("aria-disabled") !== "true") commit(...)`) → test_a_board_change_while_asking_closes_the_confirmation[redo-button-noop] FAILED (other 5 cases passed); reverted, `git diff --stat solver.js` empty, the case PASSED.
- MUTATION name back in <h1> → TestSolverPage_HidesThePictureNameUntilSolved (ac322, ac323, browser) + TestSolverPageHeader failed (9)
- MUTATION name back in <title> → ac322, ac323, browser, header no-tier + fallback tests failed (9)
- MUTATION width/height swapped in extent → ac323, browser, header size tests failed (7)
- MUTATION tier badge dropped from header → ac323, browser, header tier tests failed (7)
- MUTATION tier dropped from <title> → ac323 (both stores) + browser failed (3)
- MUTATION banner loses the name → ac322 (both stores), browser, fallback test failed (5) — the negative check is not vacuous
- [Scope] Files: puzzle_solve.html, app.py, tests/test_puzzle_solver_page.py, tests/test_puzzle_solver_progress.py. solver.js untouched (its header claim "button or key — even one that changes nothing" is now true as tested). No SCOPE+. Not done: tab title gaining the name on solve (optional; skipped).
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_page.py, tests/test_puzzle_solver_progress.py
- [Build gate] test_scope: full (config) — cycle gate runs the full suite under the repo flock
- [Build gate] PASSED (full, 527s) — 6034 passed, 9 skipped, 2 failed = exactly the two known main-baseline failures (test_size_configuration_applied, test_batch_creation_form_renders)
- [System contract] fresh system_rules.py --card CARD-163 = card section (53 rules, no drift)
- [Scope gate] cycle 1: IN_SCOPE — 4 files, all in Touches; comp_spread none (COMP-009); no structural guardrail hit (solver.js / solver_state.js untouched); no ready sibling to poach
- [Review 1/3] Score: 9.3 — crit: 0, imp: 0 (minor: 3 — F-001 template comment 'Its' antecedent, F-002 ASCII 'x' vs '×' owner call, F-003 Redo aria-disabled precondition unasserted; mutation check ran: 6/6 killed incl. M11)
- [Review sync] 1 report(s) → meta/review/ (20261003T163239Z-CARD-163-cycle1.yml)
- [Adversarial] no gating findings in cycle 1 — nothing to verify
- [Review 1/3] Step 8h coverage: 53/53 card rule ids have a verdict line (12 ✓, 41 ⚠ no_eligible_fact, 0 ✗); count line present
- [Review 1/3] Score: 9.3 ✓ threshold reached + no critical/important
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0022/R1) — ADR-0006/R1's named ref is carried by tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed (docstring alias; requirements.yml:4888 still calls the ref nonexistent — model note, not this card); ADR-0022/R1 swap mutant re-killed (7 failures), file restored byte-exact
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-322 ✓ demonstrated — evidence: TestSolverPage_HidesThePictureNameUntilSolved::test_ac322_neither_the_header_nor_the_tab_title_contains_the_name PASSED [memory] + [sqlite] (header text and <title> lack name and source file; name present in hidden banner); browser case test_the_drawn_page_keeps_the_name_out_of_the_header_until_the_banner_reveals_it PASSED (Chromium, 0 skipped)
  AC-323 ✓ demonstrated — evidence: test_ac323_the_header_shows_25x15_and_medium_in_place_of_the_name PASSED [memory] + [sqlite] (header == 'Puzzle 25x15 MEDIUM', 'medium' case-insensitive; title == 'Puzzle 25x15 · MEDIUM - Nonogram admin')
  G-1 ✓ demonstrated — evidence: tests/test_puzzle_solver_progress.py 44 passed incl. TestSolverProgress_SolvedWhenBlacksMatch (AC-316) and TestSolverProgress_ReducedMotion::test_ac319_… (AC-319); diff additive only (one _CHANGES entry, comment, condition widened to route the new case to the existing no-op assertions); no existing case/assertion removed, weakened or retargeted
  G-2 ✓ demonstrated — evidence: git diff main...HEAD -- src/nonogram/admin/static/ = 0 lines (committed + uncommitted); marking+page 132 passed, progress 44 passed
  G-3 ✓ demonstrated — evidence: no list/modal/book template or details handler in the diff; rename/list, detail API, TestBookDetail_ListsPuzzlesByTitle, TestBookArrange_ShowsTheCustomTitleOfEachRow passed (bounded: no test asserts the modal's #puzzleDetailTitle text)
  G-4 ✓ demonstrated — evidence: pyproject.toml not in diff, no new import; test_the_dependency_baseline_is_still_closed (realises TestDependencyBaseline_IsExactlyPillowAndNumpy), test_the_core_dependency_baseline_is_untouched, test_pytest_playwright_is_a_dev_only_dependency passed
- [Docs] forge:readme on changed dirs (src/nonogram/admin, src/nonogram/admin/templates, tests): no README in the admin dirs (per-directory README convention is an open owner decision — not created); tests/README.md does not describe the player and no file was added/removed — skipped, current
- [Mutation] 8f ran in cycle 1 (passing cycle): 6/6 killed — M11 (redo-button-noop kills it; other 5 cases survive it), M-E solver.js writes name to document.title, M-C extent swapped, M-F name in visually-hidden span in <h1>, M-G id in tab title; plus the implementer's 6 MUTATION lines
- [Renders] ~/Documents/nonogram-reviews/CARD-163/: unsolved-header-1440.png, unsolved-header-390.png, unsolved-tab-title-annotated-1440.png (tab title overlaid as a labelled annotation), solved-1440.png, solved-390.png, titles.txt — eyeballed: header 'Puzzle 25x15' + MEDIUM badge, banner 'Solved: Snowy owl'; tab title stays size·tier after solve (optional reveal not done)
- [Commit] success commit 0f668fc (implementation commit; review cycle 1 passed with no fix changes, so /commit had nothing further to commit). Open Minor: F-001 template comment 'Its' antecedent, F-002 '25x15' ASCII vs design '×' (owner call), F-003 Redo aria-disabled precondition unasserted before the click
- [Merged] 2026-10-03 — 159d6ad into main (--no-ff). Merge gate: rebase was a no-op (main still at 19acc73 = branch base); the merged tree is the one that passed the full suite (6034 passed, only the 2 baseline failures); not re-run — the wave-31 smoke test runs next. Deferral scan: 0 hits. Trace: FR-044 already lists TestSolverPage_HidesThePictureNameUntilSolved. F-001/F-003 to backlog; F-002 ("25x15" vs "25×15") raised to the owner.
