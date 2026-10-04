# CARD-165: The book page numbers puzzles the way the printed book will

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/165-book-page-printed-numbers
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (CARD-158 review F-004)
**Idea:** IDEA-046
**Wave:** 32
**Depends on:** —
**Touches:** src/nonogram/admin/templates/book_detail.html, src/nonogram/admin/app.py, tests/test_book_detail_page.py
**Review score:** 9.0 (cycle 1/3)
**Started:** 2026-10-04T08:14:04Z
**Closed:** 2026-10-04T08:52:42Z
**Actual:** 0.1d
**Merge commit:** 3e14de2
**Blocked by:** —

## What to implement

`/book/<id>` lists the book's puzzles with a "#" column that is the row's
position in `book.puzzle_ids` (`book_detail.html` ~:157, `loop.index`). The
printed book numbers puzzles differently: in print order, grouped by level
(FR-041; `BookManager.puzzle_levels`), counting from 1. So the "#" on screen
doesn't match the "Puzzle N" the owner will see on the printed page.

1. Show each member puzzle's **printed puzzle number**: the N its band will
   carry. Compute it from the same print-order function the PDF uses. Don't
   re-derive the order a second way.
2. List the rows in print order, so the numbers run 1, 2, 3… down the table
   and the table reads like the book.
3. A member that the interior can't draw has no printed number. The PDF drops
   it and doesn't leave a gap (CARD-140 F-007). Show "—" with a short reason
   rather than a misleading number.

## Acceptance criteria

- **AC-1:** For a book whose stored order mixes levels, the book page lists members in print order (all Easy, then Medium, then Hard), and the "#" of each row equals the "Puzzle N" number the PDF's band gives that puzzle.
  *test: TestBookDetail_NumbersPuzzlesLikeTheBook*
- **AC-2:** A member the interior can't draw shows "—" and a reason instead of a number, and the numbers of the other rows still match the PDF.
  *test: TestBookDetail_UndrawableMemberHasNoNumber*

## Guardrails

- G-1: No change to the PDF, print order or band text. The page reads the order; it never defines it (FR-041).
- G-2: CARD-158's behaviour stays: titles, tier badges, both downloads, trim row. Its tests stay green.
- G-3: Read with the bulk read (`get_puzzles`, CARD-157). No per-row database sessions.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-165` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-041 (level print order), FR-043 (the interior's numbering); no AC states the book page's numbering yet
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Screens:** /book/<id>
- **Renders:** ~/Documents/nonogram-reviews/CARD-165/

## Worktree notes

- [Origin] Roadmap wave 1 (IDEA-046, CARD-158 F-004).
- [Env] forge 2026.8.17
- [Impl] `book_detail` (src/nonogram/admin/app.py) now asks `BookPDFGenerator(book).section_plan(rows)` — the seam `interior_stream` calls — for the order and the numbers. `rows` = copies of the `get_puzzles` records that exist, in `book.puzzle_ids` order (what `_book_puzzles` feeds the export; still one bulk read, G-3). Members are listed in `plan.puzzles` order; "#" of `plan.printed[k]` is k+1, matched by row identity (CARD-140 F-003 precedent). Undrawable row → "— Not printed: cannot be drawn" in place; member with no record → listed after the planned rows, "— Not printed: puzzle not found". Plan failure follows the arrange-route precedent: (RuntimeError, ValueError) logged as warning, anything else logged with traceback; rows fall back to stored order with "— Number unknown: no page plan" and an `alert-warning` (#numbers-unavailable) pointing to Finalise. No change to book_pdf_generator.py, print order or band text (G-1).
- [Impl] Template book_detail.html: "#" cell prints `member.number` (`data-printed-number`) or "—" + `subtle` reason (`data-unprinted`); the banner reuses the arrange screen's `alert alert-warning` pattern. No new tokens/classes.
- [G-2] One CARD-158 test updated: `TestBookDetail_ListsPuzzlesByTitle::test_a_member_whose_puzzle_is_gone_is_labelled_by_its_id` asserted the stored-order listing with the missing member first; under AC-1 (print order) a member with no record is not printed and is listed last. Only the expected order of its three assertions changed (title/tier/id checks kept). `_Page` parser extended additively to read the "#" cell (`hash`).
- [AC map] AC-1 → TestBookDetail_NumbersPuzzlesLikeTheBook (print-order listing; 1..n; each "#" equals the band text the real `/download-pdf` interior draws, captured by spying `_puzzle_payload` and identifying pages by row clues; repeated id numbered twice; stored order not rewritten; seeded 14-book corpus vs two oracles — a stable level sort written in the test, and the export plan's `numbers` resolved via `SectionPlan.ids` over `get_puzzle` rows — asserting ≥3 undrawable and ≥3 missing cases). AC-2 → TestBookDetail_UndrawableMemberHasNoNumber (dash + reason, next row takes next number; other numbers equal the exported bands; no-record member; unreadable trim → banner + warning, no traceback; unexpected failure → traceback logged; intact book has no banner).
- [Tests] tests/test_book_detail_page.py (37), tests/test_book_arrange_page_breaks.py, tests/test_cli.py, tests/test_book_pdf_levels.py — 169 passed.
- Mutation self-check: number from 0 → caught by test_numbers_run_from_one_down_the_table (+6)
- Mutation self-check: stored order instead of print order (iterate rows, not plan.puzzles) → caught by test_lists_a_mixed_stored_order_in_print_order (+3)
- Mutation self-check: number undrawable rows (enumerate plan.puzzles) → caught by test_shows_a_dash_and_a_reason_instead_of_a_number, test_the_other_numbers_still_match_the_pdf, corpus test
- Mutation self-check: skip the no-record case → caught by test_a_member_with_no_record_has_no_number, corpus test, CARD-158's gone-member test
- Mutation self-check: no copy of records (repeated id collides) → caught by test_a_repeated_member_is_numbered_at_each_place_it_prints
- Mutation self-check: template prints loop.index → caught by AC-2 tests + corpus test
- Mutation self-check: template shows a number for an unprinted row → caught by AC-2 tests + corpus test
- Mutation self-check: drop the (RuntimeError, ValueError) clause → caught by test_a_book_whose_page_plan_cannot_be_built_shows_no_numbers
- Mutation self-check: unexpected failure logged as warning → caught by test_an_unexpected_plan_failure_is_logged_with_its_traceback
- Mutation self-check: no failure banner → caught by both plan-failure tests
- [Renders] ~/Documents/nonogram-reviews/CARD-165/a-mixed-levels.{html,png}, b-undrawable-and-missing.{html,png}, c-no-page-plan.{html,png} (CSS inlined; PNG via playwright chromium). Script: scratchpad card165_render.py.
- DESIGN-REGISTER book-detail puzzle table "#" cell, unprinted state — "—" (aria-hidden) over a `subtle` one-line reason; plus a "numbers unavailable" `alert alert-warning` above the table (same pattern as the arrange screen's #page-plan-unavailable).
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/templates/book_detail.html, tests/test_book_detail_page.py
- [System contract] fresh assembly (system_rules.py --card CARD-165) = card section, 52 rules — no refresh needed
- [Build gate] impact underivable (python-pro, no pytest-testmon; test_scope full) — full suite
- [Build gate] PASSED (full, 498s) — 6052 passed, 9 skipped, 0 failed
- [Scope gate] in_scope — 3/3 files within Touches; book_pdf_generator.py untouched (G-1)
- [Review 1/3] Score: 9.0 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: 52/52 card rules have a verdict line (11 holds, 41 unchecked no_eligible_fact, 0 violated)
- [Review 1/3] Mutation check (reviewer): 7 mutants, 6 killed, 1 survived (M4 fallback de-dup of repeated ids → F-003 Minor)
- [Review 1/3] Score: 9.0 ✓ threshold reached + no critical/important
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0033/R1) — caveats: ADR-0033/R1 copy cited at app.py:4787 is at :4788; its cited test checks order only, the hold rests on the code read
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — TestBookDetail_NumbersPuzzlesLikeTheBook 6/6 PASSED (print-order listing; band "Puzzle N · Tier" spied from a real /download-pdf; 14-book seeded corpus vs two oracles)
  AC-2 ✓ demonstrated — TestBookDetail_UndrawableMemberHasNoNumber 6/6 PASSED (cells 1, — Not printed: cannot be drawn, 2, 3; other rows equal exported bands)
  G-1 ✓ demonstrated — no diff under book_pdf_generator.py / book_plan.py / export/**; test_book_pdf_levels, test_book_pdf_band, test_book_level_order green (141 passed)
  G-2 ✓ demonstrated — test_book_detail_page.py 37 passed; one CARD-158 test re-ordered only (missing member last, per AC-1), all title/tier/id assertions kept
  G-3 ✓ demonstrated — test_titles_are_read_in_one_pass PASSED (one get_puzzles, get_puzzle raises); section_plan does no DB work; in-memory mode only
- [Docs] forge:readme — no structural change (no new files/dirs); src/nonogram/admin has no README (per-directory README convention is an open owner decision); tests/README.md current
- [Commit] success commit 6b71dec (implementation commit; no further card changes outside meta/ — nothing left for /commit)
- [Review] open Minor findings: F-001 (AC-1 band spy sees one-up pages only; no pairing fixture), F-002 (banner points to Finalise on the unexpected-failure path too), F-003 (fallback with repeated id untested, mutant M4 survived); out-of-scope F-004 (components.md DataTable state — DESIGN-REGISTER at merge)
- [Merged] 2026-10-04 — 3e14de2 into main (--no-ff). Merge gate: rebase was a no-op (main still at 4899076 = branch base); the merged tree is the one that passed the full suite (6052 passed, 0 failed); not re-run. Deferral scan: 0 hits. DESIGN-REGISTER applied (components.md: book detail printed-number cell + no-plan banner). F-001..F-003 captured to backlog.
