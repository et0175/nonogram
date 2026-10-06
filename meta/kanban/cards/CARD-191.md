# CARD-191: On the Arrangement step, a "Sort by size" button orders each level by longest side, then shortest side

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/191-arrange-sort-by-size
**Worktree:** —
**Source:** owner admin-panel amendments, 2026-10-06 (owner request: "Sort by size" on the Arrangement page; owner decision: it reorders and saves, the printed order follows, up/down moves keep working afterwards, no undo)
**Idea:** —
**Wave:** 35
**Depends on:** —
**Touches:** src/nonogram/admin/book_plan.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_arrange_puzzles.html, tests/test_book_arrange_sort_by_size.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- The Arrangement step is `app.py:arrange_puzzles_in_book` (route
  `/book/<book_id>/arrange-puzzles`, GET and POST, line ~4086). Its POST
  branches on `action`: `move_up`, `move_down`, `set_position`, `set_title`,
  `delete`, `finish`. It re-renders (no redirect) and shows the book through
  `BookManager.puzzle_levels`, one section per non-empty level (Easy, Medium,
  Hard, then an "Ungraded" tail when a row has no tier).
- Every order change goes through `BookManager.reorder_puzzles`
  (`book_manager.py` line ~1545). It checks the book exists, the ids are the
  book's membership (`ValueError`), and the order is grouped by level
  (`book_plan.is_level_order`, else `LevelBoundary`). Then it writes a fresh
  list in both storage modes (memory dict; DB `Book.puzzle_ids`).
- Moves (`_move_within_level`) compute the new order with
  `book_plan.moved_within_level`, which works on the **grouped** view
  (`book_level_order`). So a move on a legacy mixed book writes the grouped
  order back.
- Reorder does **not** change the book's status. The module comment at
  `book_manager.py` ~line 455 says so (owner decision 2026-09-22 (c): only add
  and remove return a book to draft, INV-012). It is pinned by
  `tests/test_book_published_confirm.py::test_reorder_and_retitle_keep_the_status`
  (a `move_puzzle_up` on a `pdf_generated` book keeps `pdf_generated`).
- Each row on the page already shows `width×height` from the bulk record read
  (`puzzle_review.get_puzzles`, CARD-157). There is no size sort anywhere on
  this step today.

**Target behaviour.**

1. **Pure ordering function** in `book_plan.py`, beside `moved_within_level`:
   `sorted_by_size_within_level(puzzle_ids, tier_of, size_of)`. It returns the
   grouped order (`book_level_order`) with each level sorted by the key
   `(max(width, height), min(width, height))`, **ascending** (smallest first,
   the same direction FR-036's selection tabs use).
   - **Tie-break: stable.** Puzzles with an equal key (e.g. 15×20 and 20×15,
     or two 20×20) keep their current relative order. Use Python's stable
     `sorted` over the grouped order; never sort by id.
   - A puzzle whose size cannot be read (`size_of` answers `None`: no row, no
     store) goes to the **end of its level**, keeping its current relative
     order. Same quiet rule as `_tier_of`: an order has no false-"ready"
     failure mode, so this never raises.
   - The Ungraded tail is a section on screen, so it is sorted the same way and
     stays last.
   - Levels never mix: the result always satisfies `is_level_order`.
   - Idempotent: sorting a sorted order returns it unchanged.
2. **Store method** `BookManager.sort_puzzles_by_size(book_id) -> bool`. It
   reads tiers (`_tier_of`) and sizes in one bulk read each (CARD-157 style,
   outside any writing session), computes the order, and:
   - if the new order equals the stored order, writes **nothing** and returns
     `False` (no `updated_at` bump);
   - else writes it through `reorder_puzzles` (so INV-009's one enforcement
     point and both storage branches stay in one place) and returns `True`.
   - Unknown book: `ValueError("Book not found")`, as `_move_within_level` does.
   - **Status: unchanged**, exactly like moves (a reorder is not a membership
     change; INV-012 / FR-038 open_question). No return to draft.
   - On a legacy mixed book the grouped and sorted order is written, as a move
     would.
3. **Route**: a new POST `action == "sort_by_size"` branch in
   `arrange_puzzles_in_book`. Flash on `True`:
   "Sorted each level by size: longest side, then shortest side." (success).
   On `False`: "Each level is already in size order; the order is unchanged."
   (success — not an error, mirrors the `set_position` no-op). The existing
   `LevelBoundary` / `ValueError` handlers cover failures. The page then
   re-renders from the stored order as today, so the page breaks shown are the
   new order's page plan (`_printed_places`) with no extra code.
4. **Template**: one "Sort by size" button in the "Puzzles in book" card
   header, a `<form method="POST">` with `action=sort_by_size`, styled
   `btn btn-sm btn-outline-secondary` (existing classes; no new CSS). Shown only
   when the book has puzzles. Because there is no undo, the form carries
   `onsubmit="return confirm('Sort every level by size? Your own order inside
   each level is replaced. There is no undo.')"`, the same pattern the remove
   button uses. Its `title` says what it does: "Sort each level by longest
   side, then shortest side".
5. **One button sorts every level.** The sort acts on the **stored** book,
   never on a filtered subset of rows (see CARD-192 overlap in Worktree notes).
6. **Moves keep working afterwards**: nothing about moves changes; they act on
   the stored (now sorted) order. Nothing remembers that a sort happened.

**Print effect (say it to the owner, do not engineer around it).** The printed
order follows the stored order (FR-041), so after a sort the PDF prints the new
order and puzzle numbers 1..n follow it. INV-010 pairs two puzzles on one page
only when they are **adjacent** in the book order, share a tier and both fit
one shared cell. So sorting changes which puzzles pair, and can change the
interior page count and the Finalise counts for that book. That is the
intended result of the owner's action, not a regression. No PDF drawing code
changes.

## Acceptance criteria

- **AC-1** (happy): *Given* a book with easy puzzles stored as 25×25, 15×15, 20×15, 30×20, a medium 20×20 and a medium 10×10, *when* "Sort by size" is posted, *then* the stored order is easy 15×15, 20×15, 25×25, 30×20, then medium 10×10, 20×20 — each level ascending by longest side then shortest side, easy still before medium — in both storage modes.
  *test: TestArrangeSortBySize_SortsEachLevelByLongestThenShortest (in tests/test_book_arrange_sort_by_size.py)*
- **AC-2** (boundary): *Given* an easy level stored as A 20×15, B 15×20, C 20×20, D 20×15, *when* the sort runs, *then* the order is A, B, D, C — equal keys (A, B, D all longest 20, shortest 15) keep their current relative order.
  *test: TestArrangeSortBySize_EqualSizesKeepTheirCurrentOrder (in tests/test_book_arrange_sort_by_size.py)*
- **AC-3** (boundary): *Given* a book the sort has just ordered, *when* "Sort by size" is posted again, *then* the stored order and the book's `updated_at` are unchanged and the page says the order is unchanged.
  *test: TestArrangeSortBySize_SecondPostChangesNothing (in tests/test_book_arrange_sort_by_size.py)*
- **AC-4** (happy): *Given* a book in `pdf_generated` (and one in `ready_for_pdf`), *when* the sort changes its order, *then* its status is unchanged — the same verdict a move gets.
  *test: TestArrangeSortBySize_KeepsTheStatusAsAMoveDoes (in tests/test_book_arrange_sort_by_size.py)*
- **AC-5** (happy): *Given* a book just sorted, *when* a puzzle is moved up through the arrange route, *then* the move is applied to the sorted order (insertion inside its level) and the stored order shows it.
  *test: TestArrangeSortBySize_MovesStillWorkAfterASort (in tests/test_book_arrange_sort_by_size.py)*
- **AC-6** (happy): *Given* a book whose sort changes which puzzles are adjacent, *when* the arrange page re-renders after the sort, *then* every row's `data-page` equals the page `BookPDFGenerator.section_plan` gives that puzzle for the new stored order (the screen shows the new pairing, not the old).
  *test: TestArrangeSortBySize_PageBreaksFollowTheSortedOrder (in tests/test_book_arrange_sort_by_size.py)*
- **AC-7** (boundary): *Given* a legacy mixed stored order (medium, easy, hard, easy) and a puzzle id with no readable size, *when* the sort runs, *then* the stored order is grouped easy, medium, hard, each level size-sorted, and the unsized puzzle is last in its level.
  *test: TestArrangeSortBySize_GroupsALegacyOrderAndPutsUnsizedLast (in tests/test_book_arrange_sort_by_size.py)*
- **AC-8** (property): *For any* seeded book (corpus built with `random.Random`, sizes 10..30 non-square included, three tiers plus ungraded, a minimum case count asserted in the test), the sort's result is a permutation of the membership, satisfies INV-009 grouping, is non-decreasing by (longest, shortest) inside each level, keeps the input relative order among equal keys, and sorting it again returns it unchanged. Expected keys are computed in the test from the sizes the test itself chose, never by calling the function under test.
  *test: PropertyTest_ArrangeSortBySize_GroupedStableAndIdempotent (in tests/test_book_arrange_sort_by_size.py)*
- **AC-9** (happy): *Given* a book with puzzles, *when* the arrange page renders, *then* it carries one "Sort by size" POST form (`action=sort_by_size`) with a confirm prompt naming that there is no undo; *given* an empty book, the button is absent.
  *test: TestArrangeSortBySize_ButtonIsOnThePage (in tests/test_book_arrange_sort_by_size.py)*

## Guardrails

- G-1: INV-009 keeps one enforcement point. The sort writes through `reorder_puzzles`; no second grouping rule. `tests/test_book_level_order.py`, `tests/property/test_book_order.py` and `tests/test_book_arrange_position.py` stay green unchanged.
- G-2: Moves, typed positions, add and remove behave exactly as today. `test_reorder_and_retitle_keep_the_status` and the INV-012 tests in `tests/test_book_published_confirm.py` stay green unchanged.
- G-3: No PDF drawing, page-plan or pairing code changes (`book_pdf_generator.py`, `section_plan`, CON-019 A4 golden, book pixel baselines, ADR-0036/R1). Only the stored order moves; a book that is not sorted prints byte-identically.
- G-4: Membership, custom titles and the plan are untouched by a sort (EC-026).
- G-5: No grading: tiers are read from the stored row (ADR-0033/R1, `tier_of_record`), sizes from the stored `width`/`height`. Nothing is re-derived from a grid.
- G-6: Capability-module import guard stays green (`tests/test_cli.py`); the pure function lives in `book_plan.py`, which imports nothing new.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-191` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-041 (book order easy -> medium -> hard; within a level the owner's arrangement; AC-257/AC-258 moves), FR-038 (reorder keeps status; `_meta.open_question`), FR-040 (pairing), FR-036 (size key precedent: longest side buckets, shorter side ascending). No FR AC covers a size sort, so the ACs above are card-local.
- **Invariants:** INV-009 (grouped by tier — the sort keeps tiers grouped; it is an explicit owner reorder), INV-010 (pairing depends on adjacency — sorting changes pairs), INV-012 (membership only; a reorder does not return to draft).
- **EC:** EC-026 (order changes only through an explicit add, remove, reorder or retitle — a sort is an explicit reorder).
- **Commands/events:** CMD-022 ReorderBookPuzzles -> EVT-023 BookPuzzlesReordered (precondition INV-009).
- **ADR:** ADR-0035 (readiness gate; its clarification is INV-012), ADR-0033/R1 (tier read from the row).
- **Components:** COMP-009 (Admin Panel); COMP-007 consulted only through `section_plan` for the page labels.
- **Trace:** meta/architecture/trace.yml

## Design context

- Screen: Books · Arrangement step, `/book/<book_id>/arrange-puzzles`.
- New control: one "Sort by size" button (`btn-sm btn-outline-secondary`) in the "Puzzles in book" card header, with a confirm prompt. Owner-visible defaults chosen here: button placement, the confirm wording, the two flash texts, ascending direction.
- What the owner SEES change after a sort: rows reorder inside each level, puzzle numbers renumber, page labels and "two puzzles" pairings move.
- Renders: ~/Documents/nonogram-reviews/CARD-191/ (owner visual check before merge). Before/after screenshots of one book with mixed sizes in all three levels, including at least one page label that changes pairing, plus a screenshot of the confirm prompt.

## Worktree notes

- [Origin] Owner admin-panel amendments 2026-10-06: "Sort by size" on the Arrangement page. Owner decision: reorders and saves, printed order follows, up/down keep working, no undo.
- [Verified] Reorder keeps status today: `book_manager.py` ~line 455 comment; pinned by `tests/test_book_published_confirm.py:1110` (`test_reorder_and_retitle_keep_the_status`). The sort mirrors that.
- [Verified] Fixtures to reuse: `tests/test_book_level_order.py` has `Shelf` (parametrised over both storage modes via `MODES`, sqlite via `sqlite_session_scope`), `Panel`, `admin_app`, `text_of`, `body`. `Shelf.puzzle(tier, size)` makes **square** puzzles only; the new file needs a local helper for non-square sizes (a fully filled w×h grid is uniquely solvable). Import, do not edit, that file (as `tests/test_book_arrange_position.py` does).
- [Verified] Page labels on the arrange page come from `app.py:_printed_places` (~line 783) over `BookPDFGenerator.section_plan`; AC-6 compares against that seam. AC-253 notes 20×20 puzzles do not pair at Book 1 profile, so AC-6 needs sizes the plan really pairs — pick them by asking `section_plan`, do not assume.
- [Choice] Ascending (smallest first) and a confirm prompt are this card's defaults, not owner words. Ungraded tail is sorted too and stays last. Unsized puzzles go last in their level.
- [Overlap] CARD-192 (same page: longest-size filter + plan left/over) is drafted in parallel and will touch the same two files: `app.py:arrange_puzzles_in_book` and `templates/book_arrange_puzzles.html` (card header / side column). Expect a textual conflict; whichever merges second rebases. Rule for both: the sort acts on the stored level as a whole, never only on rows a filter shows.
- [Model note] INV-009's text says the within-level order is "changed only by an explicit move inside that level". A sort is an explicit owner reorder (CMD-022; EC-026 already says "reorder"), so it is allowed, but the architect may want INV-009's wording to say "explicit reorder" rather than "move". Card commits exclude meta/, so this is a note for the architect, not part of the change.
- [AC cross-check] Re-read AC-1..AC-9 against the body: direction (ascending), tie-break (stable), unsized-last, no-op writes nothing, status unchanged all agree. AC-1's expected order was written by hand from the key (longest, shortest): 15×15 (15,15) < 20×15 (20,15) < 25×25 (25,25) < 30×20 (30,20). No fixes needed.
- [Owner decision] 2026-10-06 — smallest first (longest side, then shortest) inside each level; one button sorts all levels; confirm prompt says there is no undo. Hidden while CARD-192's size filter is active (whichever merges second wires that).
