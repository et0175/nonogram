# CARD-180: Book selection: `?status=all` lists every status instead of nothing

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/180-book-select-status-all
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-05 (owner decision on IDEA-088, 2026-10-05: "all" lists every status)
**Idea:** IDEA-088
**Wave:** 34
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_select_puzzles.html, tests/test_status_filter_default.py
**Review score:** 9.5 (1 cycle)
**Started:** 2026-10-05T11:40:39Z
**Closed:** 2026-10-05T12:31:56Z
**Actual:** 0.1d
**Merge commit:** ef83b2c
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**
`app.py:select_puzzles_for_book` (~:3872) reads
`status = request.values.get("status") or "approved"` and passes it unchanged
to `PuzzleFilter(status=...)`. Both stores filter by equality
(`puzzle_review.py` ~:919 in memory, ~:1031 in SQL). `all` is not a puzzle
status, so `?status=all` matches nothing and the tab is empty. CARD-166 pinned
this on purpose in `test_all_is_matched_literally_as_before`
(`tests/test_status_filter_default.py`:113-119).

**Owner decision (2026-10-05).** `?status=all` lists puzzles of every status
the store holds (today `PuzzleStatus`: draft, approved, rejected, in_book).

**Target behaviour.**
1. In `select_puzzles_for_book`, when the status value is exactly `all`, pass
   `status=None` to `PuzzleFilter` (None already means "no status filter" in
   both stores). Keep `context["status"] = "all"`. The hidden `status` field
   in `book_select_puzzles.html` (~:123) and `_tab_query` (~:3335) then carry
   `all` through tab switches, page moves, Apply and a refused add, the same
   way they carry any other value. Do not turn it into `""`: an empty value
   means the approved-only default (CARD-166).
2. Nothing else about the query changes. `book_id="unassigned"`, the
   longest-side tab, `BOOK_TAB_SORT`, paging and the three cross-checks stay
   as they are. So puzzles already in a book stay hidden under `all` too.
3. **Can the owner add the non-approved tiles? Yes. That is already true
   today, and this card keeps it.** No approved-only rule for book membership
   exists anywhere:
   - `book_manager.add_puzzles_reporting_refusals` (~:1170) checks the
     published-book question (INV-008), the 4.8 mm floor with overrides
     (FR-031/INV-006) and return-to-draft (INV-012). It never reads a puzzle's
     curation status.
   - `/book/<id>/add-puzzles` (paste IDs, ~:4936) has no status check either.
   - `?status=draft` and `?status=rejected` already offer selectable tiles
     (CARD-166 G-2 pinned them).
   - FR-036 (`requirements.yml` ~:2557) and ADR-0032/ADR-0033 have no
     approved-only rule for books. The only "approved only" text in the docs
     is legacy AC-158, which is about export, not books.
   - `PuzzleReviewService.assign_to_book` leaves the curation status alone, so
     a draft puzzle added to a book stays "draft" (ADR-0033/R1).

   So under `all` every tile stays selectable, with the same floor flag and
   override as today. Do NOT add a status rule to the store. That would be a
   new membership rule and needs its own owner decision.
4. **Make the status visible on the tile (owner-visible).** Today the tiles
   show no status at all. Under `all`, draft and rejected tiles would look the
   same as approved ones. Add one `info-row` "Status" to every tile whose
   status is not `approved`, with the status word as text (`in_book` shown as
   "in book"). Use the existing `info-row` / `info-label` / `info-value`
   markup, no new CSS. Approved tiles get no new row, so the default page
   looks exactly as it does today.
5. **Empty-state copy.** The empty tab says "No approved puzzles with a
   longest side of X match these filters…" (~:259). When the status is `all`,
   say "No puzzles with a longest side of X match these filters. Try another
   tab." Keep the current copy for every other case.
6. An unknown value (for example `?status=bogus`) still matches nothing, as
   today. Only the exact string `all` is special.

**Scope note: puzzle list (`/puzzles`), not changed here.**
`puzzles_list` (~:2163) treats `?status=all` as an unknown status. It flashes
"Unknown status 'all' — showing every status instead" and lists every status.
The result already matches this card's meaning of `all`. Only the flash is
odd. Leave it alone (CARD-066 AC-1 tests); a follow-up could accept `all`
quietly there.

## Acceptance criteria

- **AC-1:** *Given* a book and two puzzles of each status draft, approved and rejected on the <=15 tab, *when* `/book/<id>/select-puzzles?status=all` is rendered, *then* exactly those six puzzles are offered (both stores).
  *test: TestStatusFilter_AllOffersEveryStatus (in tests/test_status_filter_default.py)*
- **AC-2:** *Given* the same stock with one approved puzzle already added to the book, *when* `?status=all` is rendered, *then* that puzzle is not offered and the other five are.
  *test: TestStatusFilter_AllStillHidesPuzzlesInABook (in tests/test_status_filter_default.py)*
- **AC-3:** *Given* the page at `?status=all`, *when* the owner switches tab, moves page or presses Apply (POST with `status=all`), *then* the redirect URL carries `status=all` and the landing page offers every status.
  *test: TestStatusFilter_AllSurvivesTabSwitchAndApply (in tests/test_status_filter_default.py)*
- **AC-4:** *Given* the page at `?status=all`, *when* the owner ticks one draft and one rejected tile and presses Add, *then* both join the book and each puzzle keeps its own status (draft, rejected).
  *test: TestStatusFilter_AllTilesCanBeAddedAndKeepTheirStatus (in tests/test_status_filter_default.py)*
- **AC-5:** *Given* the page at `?status=all`, *when* it is rendered, *then* each draft or rejected tile shows a "Status" row naming its status, and no approved tile shows one; the default page (no `status`) shows no "Status" row.
  *test: TestStatusFilter_NonApprovedTilesNameTheirStatus (in tests/test_status_filter_default.py)*
- **AC-6:** *Given* a tab with no puzzles, *when* it is rendered at `?status=all`, *then* the empty-state text does not contain "approved"; at the default it still does.
  *test: TestStatusFilter_AllEmptyTabDoesNotSayApproved (in tests/test_status_filter_default.py)*
- **AC-7:** *Given* the same stock, *when* `?status=bogus` is rendered, *then* no puzzle is offered (only the exact value `all` is special).
  *test: TestStatusFilter_UnknownValueStillMatchesNothing (in tests/test_status_filter_default.py)*

## Guardrails

- G-1: An absent or empty `status` still offers approved puzzles only. `TestStatusFilter_EmptyValueKeepsTheApprovedDefault` stays unchanged and green (CARD-166 AC-3).
- G-2: Explicit `approved`, `draft` and `rejected` filter exactly as today. `test_an_explicit_status_offers_exactly_its_puzzles` stays unchanged. The ONE pinned test this card replaces is `test_all_is_matched_literally_as_before`; its guard role ("unknown does not widen") moves to AC-7.
- G-3: The book store is untouched. No status rule is added to `add_puzzles_reporting_refusals` or `/book/<id>/add-puzzles`. The floor and overrides (INV-006: `PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride`, `TestBookAddPuzzles_RefusesBelowFloorWithoutOverride`), INV-008 and INV-012 tests stay green.
- G-4: ADR-0033/R1: adding a puzzle to a book never changes its curation status.
- G-5: ADR-0032/R1 storage boundary (`add_puzzle`) is untouched.
- G-6: Tabs, tier order, paging and the planned-vs-selected figures (FR-036, AC-208..AC-217) are unchanged: `tests/test_book_select_tabs.py` and `tests/test_book_select_floor_tiles.py` stay green.
- G-7: The puzzle-list route (`puzzles_list`) is unchanged: `tests/test_card_066_status_filter.py` stays green.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-180` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-036 (book selection filters; approved-only default, CARD-166); FR-031 (4.8 mm floor, unchanged)
- **Invariants:** INV-006, INV-008, INV-012 (must still hold; not touched)
- **ADRs:** ADR-0032/R1 (storage boundary, untouched), ADR-0033/R1 (membership never changes a puzzle's status)
- **Components:** COMP-009 (Admin Panel)
- **Trace:** meta/architecture/trace.yml (FR-036 row, ~:1762)

## Design context

- **Screen:** /book/<id>/select-puzzles (Puzzle selection step), at `?status=all` and at the default.
- **Owner-visible changes:** (a) draft/rejected tiles appear under `all` and are selectable, as they already are under `?status=draft`; (b) a new "Status" row on non-approved tiles; (c) neutral empty-state copy under `all`. The default page must look unchanged.
- **Renders:** ~/Documents/nonogram-reviews/CARD-180/ (owner visual check before merge): the <=15 tab at `?status=all` with mixed tiles, an empty tab at `?status=all`, and the default page for comparison.

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-088 (owner decision 2026-10-05: `?status=all` lists every status). Follows CARD-166 G-2, which pinned the empty result.
- [Facts] Route: `app.py:select_puzzles_for_book`, status line ~:3872 (`request.values.get("status") or "approved"`). `_SELECT_FILTERS` ~:3263 already includes `status`; `_tab_query` ~:3335 copies it from the form. The hidden `status` input is `book_select_puzzles.html` ~:123; the empty-state `<p>` is ~:259. `PuzzleFilter.status=None` means "no filter" in both stores (`puzzle_review.py` ~:919, ~:1031). Tile dicts already carry `status` in both stores (`puzzle_review.py` ~:290 for SQL).
- [Pinned test to replace] `tests/test_status_filter_default.py::TestStatusFilter_ExplicitValuesFilterAsBefore::test_all_is_matched_literally_as_before` (:113-119) asserts `?status=all` offers `set()`. Delete it and add AC-1 and AC-7 in its place. Reuse the file's `stocked` fixture and `_offered` helper (both stores).
- [No approved-only rule] Verified: `add_puzzles_reporting_refusals` (~:1170) and `/book/<id>/add-puzzles` (~:4936) never read curation status; no FR/ADR/INV demands approved-only membership. That is why AC-4 expects the add to succeed. If the owner wants such a rule, it is a new card.
- [Open for owner, non-blocking] (1) `in_book` is a `PuzzleStatus` value. A puzzle with status `in_book` but no `book_id` (a pre-CARD-100 leftover) would show under `all`. `mark_in_book` has no production caller, so none should exist; the card shows it like any other status ("in book"). (2) The page has no visible status control; `all` is reachable by URL only. Adding a status select is out of scope.
- [AC cross-check] Re-read AC-1..AC-7 against What to implement: AC-2 matches item 2 (book_id filter kept), AC-3 matches item 1 (`all` kept literal, never `""`), AC-4 matches item 3, AC-5 matches item 4 (row only on non-approved tiles), AC-6 matches item 5, AC-7 matches item 6. No contradictions found; nothing changed.
- [Env] forge 2026.8.17
- [Implemented 2026-10-05, commit 7be6ac6] `app.py:select_puzzles_for_book`: `store_status = None if status == "all" else status` is passed to `PuzzleFilter`; `context["status"]` stays the raw value, so the hidden field and `_tab_query` carry `all` unchanged (no edit needed there). Template: one `info-row` "Status" on tiles whose status is not `approved` (`replace('_', ' ')`, so `in_book` reads "in book"), existing markup only, no new CSS; an `{% elif status == 'all' %}` empty-state branch with the neutral copy, the approved copy kept for every other case. Tests: `test_all_is_matched_literally_as_before` deleted (G-2) and seven AC classes added in tests/test_status_filter_default.py. The CARD-166 `stocked` fixture is behaviour-identical (now calls a shared `_stock(panel, measurable=False)`); the new classes use a `measurable` fixture with the same six puzzles but real stored clues, because the floor refuses an unmeasurable cell and AC-2/AC-4 need puzzles that can actually join a book. Both stores (memory, sqlite) via the file's existing `panel` fixture.
- [Mutants] each applied alone, tests/test_status_filter_default.py run, reverted (script: scratchpad card180_mutants.py):
  M1 drop the `== "all"` -> None mapping — killed by AllOffersEveryStatus, AllStillHidesPuzzlesInABook, AllSurvivesTabSwitchAndApply, AllTilesCanBeAddedAndKeepTheirStatus, NonApprovedTilesNameTheirStatus.
  M2 map "" to all too (`or "all"`) — killed by EmptyValueKeepsTheApprovedDefault (CARD-166), NonApprovedTilesNameTheirStatus::test_no_row_on_the_default_page, AllEmptyTabDoesNotSayApproved.
  M3 match `all` case-insensitively — killed by UnknownValueStillMatchesNothing (ALL/All).
  M4 match via strip().startswith("all") — killed by UnknownValueStillMatchesNothing (all-of-them / " all").
  M5 any unknown value -> None — killed by UnknownValueStillMatchesNothing.
  M6 drop `book_id="unassigned"` under all — first run SURVIVED (the route's per-row `book_id is None` cross-check hides the row); AllStillHidesPuzzlesInABook then got a "(5 available)" assertion (the store's own count), now killed by it.
  M7 context status -> "" under all — killed by AllSurvivesTabSwitchAndApply, AllEmptyTabDoesNotSayApproved.
  M8 hidden field turns `all` into "" — first run SURVIVED (the AC-3 test posted a hand-written `status=all`); the test now posts the value read from the rendered hidden field, now killed by AllSurvivesTabSwitchAndApply.
  M9 Status row on every tile (drop the condition) — killed by NonApprovedTilesNameTheirStatus (rows_under_all, no_row_on_the_default_page).
  M10 Status row on no tile — killed by NonApprovedTilesNameTheirStatus.
  M11 Status row only on draft — killed by NonApprovedTilesNameTheirStatus (rows_under_all, in_book).
  M12 `in_book` rendered raw — killed by NonApprovedTilesNameTheirStatus::test_in_book_reads_as_two_words.
  M13 revert the empty copy under all — killed by AllEmptyTabDoesNotSayApproved.
  M14 neutral copy for every status — killed by AllEmptyTabDoesNotSayApproved (default still says approved).
- [Owner default] `in_book` is shown like any status, as "in book" — implemented as drafted (test_in_book_reads_as_two_words writes a leftover in_book row with no book_id directly, since no public method produces that shape).
- [Owner default] No status control on the page; `all` is reachable by URL only — implemented as drafted.
- [Renders] ~/Documents/nonogram-reviews/CARD-180/: after-status-all-mixed.png (<=15 tab, 3 approved/3 draft/3 rejected), after-status-all-empty-tab.png (26-30 tab at ?status=all), before-default.png (main, no status), after-default.png (this branch, no status), before-status-all.png (main at ?status=all, empty, for contrast); matching .html beside each. before-default.html and after-default.html are byte-identical. BEFORE rendered from a temporary detached worktree of main in the scratchpad, removed afterwards.
- [Note for owner, not changed] The page's lede still reads "pick the approved grids that go in" under `?status=all` too; the card scoped only the empty-state copy, so it was left alone.
- [Scope] Only the three Touches files changed; no SCOPE+.
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/templates/book_select_puzzles.html, tests/test_status_filter_default.py
- [Build gate] impact underivable (test_scope: full) — full suite
- [Build gate] PASSED (full, 670s) — 6397 passed, 9 skipped
- [Review 1/3] Score: 9.5 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h: 52 rules checked (10 ✓, 42 ⚠ no_eligible_fact, 0 ✗) — all card ids covered
- [Review 1/3] 8f-mutation: 8/8 killed (reviewer-run)
- [Review 1/3] Score: 9.5 ✓ threshold reached + no critical/important
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0032/R1) — the ADR-0019/R1 count '1 passed, 98 deselected' differs from the skeptic's own run (93/6405 deselected, invocation-dependent); the orchestrator confirmed the reviewer's transcript holds that literal line from its own batch run
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-1 ✓ demonstrated — AllOffersEveryStatus '2 passed, 38 deselected, 3 warnings in 0.38s'; AC-2 ✓ demonstrated — AllStillHidesPuzzlesInABook '2 passed, 38 deselected, 5 warnings in 0.22s'; AC-3 ✓ demonstrated — AllSurvivesTabSwitchAndApply '6 passed, 34 deselected, 7 warnings in 0.44s'; AC-4 ✓ demonstrated — AllTilesCanBeAddedAndKeepTheirStatus '2 passed, 38 deselected, 5 warnings in 0.23s'; AC-5 ✓ demonstrated — NonApprovedTilesNameTheirStatus '6 passed, 34 deselected, 7 warnings in 0.39s'; AC-6 ✓ demonstrated — AllEmptyTabDoesNotSayApproved '2 passed, 38 deselected, 3 warnings in 0.21s'; AC-7 ✓ demonstrated — UnknownValueStillMatchesNothing '10 passed, 30 deselected, 11 warnings in 0.58s'; G-1 ✓ demonstrated — EmptyValueKeepsTheApprovedDefault '4 passed, 36 deselected, 5 warnings in 0.31s' (body unchanged); G-2 ✓ demonstrated — test_an_explicit_status_offers_exactly_its_puzzles '6 passed, 34 deselected, 7 warnings in 0.39s' (only the permitted test deleted); G-3 ✓ demonstrated — book_manager.py no diff, add-puzzles route outside every hunk; INV-006 '14 passed, 70 deselected', INV-008 '35 passed, 51 deselected', INV-012 '36 passed, 52 deselected'; G-4 ✓ demonstrated — AC-4 test asserts status kept '2 passed, 38 deselected' (checks status only); G-5 ✓ demonstrated — puzzle_review.py no diff, TestStorageBoundary_AsksTheSolverNotTheCaller '2 passed, 42 deselected in 0.02s'; G-6 ✓ demonstrated — test_book_select_tabs.py + test_book_select_floor_tiles.py '83 passed, 189 warnings in 4.58s' (unchanged); G-7 ✓ demonstrated — test_card_066_status_filter.py '12 passed in 0.37s' (unchanged). No EC section.
- [Docs] forge:readme: no README in src/nonogram/admin/ or templates/; tests/README.md does not list per-file tests; no file added/removed/renamed — no README change needed
- DESIGN-REGISTER: PuzzleTile → Parts: 'a Status info-row (info-label Status / info-value = the status word, in_book shown as "in book") on every tile whose status is not approved; approved tiles carry no row (CARD-180)'. EmptyState → Book selection under ?status=all: 'No puzzles with a longest side of X match these filters. Try another tab.' (CARD-180)
- [Commit] success commit 7be6ac6 — the implementation commit stands as the card's commit: review cycle 1 passed with no fix, so no further change existed to commit (verified: git status shows only meta/ files)
- [Merge gate] branched from 35a89b1 (= main at merge); pipeline full suite 6397 passed, 9 skipped (same tree, not re-run). Owner: "merge now, check later" (renders in ~/Documents/nonogram-reviews/CARD-180/). Merged ef83b2c.
