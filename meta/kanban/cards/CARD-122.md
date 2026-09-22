# CARD-122: Puzzle selection by longest-side tab — planned-vs-selected headers, whole-book summary, tier-then-shorter-side sort

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/122-select-by-longest-side-tab
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-14 (FR-036)
**Idea:** —
**Wave:** 22
**Depends on:** CARD-119, CARD-120
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_select_puzzles.html, tests/test_book_select_tabs.py
**Review score:** 8.5 (cycle 3/3)
**Started:** 2026-09-22T18:20:03Z
**Closed:** 2026-09-22T22:16:40Z
**Actual:** 0.5d
**Merge commit:** 37f1b68
**Blocked by:** —

## What to implement

1. **Four tabs** on `/book/<id>/select-puzzles`: ≤15 · 16–20 · 21–25 · 26–30. The trace
   note suggests a server-rendered `?bucket=` parameter on the existing route; FR-036's
   open question (separate routes or client-side tabs) is not a blocker, so record the
   choice. Each puzzle is listed on exactly one tab, using CARD-119's `bucket_of`.
   Never re-derive the bucket.
2. **Selections survive tab switches** (AC-211). Server-side, a selection is submitted
   per tab and kept (in the session or as book membership, according to what the current
   step does today; record which). Switching tabs never drops it.
3. **Headers.** Each tab shows, per tier and in total, `selected / planned` for its
   bucket, from CARD-119's `selection_cells` and `planned_cells` against the stored
   plan. Over-plan cells are marked as over. The same summary for the whole book sits
   above the tabs. If a book has no plan, show the selected counts alone and link to
   Print setup (ADR-0035's remedy).
4. **Sort inside a tab:** tier (easy, medium, hard), then shorter side ascending.
5. **Filters:** theme, name, quality and difficulty still apply inside a tab. The
   **size-range filter (`size_from`/`size_to`) is removed**, replaced by the tab.
6. Tiles keep their current content in this card. The per-tile cell and below-floor
   flag are CARD-123.

## Acceptance criteria

- **AC-208** — given a 15-wide x 30-tall puzzle available for a book, when puzzle selection is rendered, then the puzzle is listed on the 26-30 tab only.
  *test:* `TestBookSelect_PuzzleListedUnderLongestSideTab`
- **AC-209** — given a 15-wide x 16-tall puzzle available for a book, when puzzle selection is rendered, then the puzzle is listed on the 16-20 tab, not the <=15 tab.
  *test:* `TestBookSelect_LongestSideSixteenGoesToSecondTab`
- **AC-210** — given a 15x15 puzzle available for a book, when puzzle selection is rendered, then the puzzle is listed on the <=15 tab.
  *test:* `TestBookSelect_LongestSideFifteenGoesToFirstTab`
- **AC-211** — given 3 puzzles selected on the <=15 tab, when the owner switches to the 21-25 tab and back, then the same 3 puzzles are still selected.
  *test:* `TestBookSelect_SelectionKeptAcrossTabSwitch`
- **AC-212** — given a plan of 21-25 easy 10 / medium 20 / hard 12 and 8 easy, 20 medium, 14 hard puzzles selected in that bucket, when the 21-25 tab is rendered, then its header reads 21-25: easy 8 / 10 · medium 20 / 20 · hard 14 / 12.
  *test:* `TestBookSelect_TabHeaderShowsPlannedVsActual`
- **AC-213** — given the same 21-25 bucket with 14 hard selected against a plan of 12, when the 21-25 tab is rendered, then the hard cell is marked over plan.
  *test:* `TestBookSelect_OverPlanCellMarked`
- **AC-214** — given a plan with 60 easy puzzles and 12 easy selected on the <=15 tab plus 30 on the 16-20 tab, when puzzle selection is rendered, then the whole-book summary above the tabs reads easy 42 / 60.
  *test:* `TestBookSelect_BookSummarySumsAllTabs`
- **AC-215** — given a 21-25 bucket holding a hard 25x21, an easy 25x18, an easy 22x16 and a medium 25x25 puzzle, when the 21-25 tab is rendered, then the order is easy 22x16, easy 25x18, medium 25x25, hard 25x21.
  *test:* `TestBookSelect_TabSortsByTierThenShorterSide`
- **AC-216** — given any book on the puzzle-selection step, when the page is rendered, then it carries no size_from or size_to field.
  *test:* `TestBookSelect_SizeRangeFilterReplacedByTab`
- **AC-217** — given a 21-25 bucket holding 3 easy, 2 medium and 4 hard puzzles, when the 21-25 tab is filtered by difficulty hard, then exactly the 4 hard puzzles are listed.
  *test:* `TestBookSelect_ExistingFiltersApplyInsideTab`

## Engineering constraints

- **EC-024** (consistency) — For every extent of 10..30 x 10..30, the longest-side bucketing assigns the puzzle to exactly one of the four buckets, chosen by max(width, height) alone — the four tabs partition the supported size range with no gap and no overlap, and one bucketing function serves the plan (FR-034), the tabs and the readiness check (FR-037).
  *test:* `PropertyTest_LongestSideBuckets_PartitionEveryExtent` (CARD-119 — add a route-level case: every available puzzle appears on exactly one rendered tab)

## Guardrails

- G-1: One bucketing function. The route and the template import `book_plan.bucket_of`, and no second `max(w, h)` threshold table appears (EC-024).
- G-2: Out of scope: BK-UI-8 (the owner's unfinished "When adding puzzles to book, please add a possibility to …"). It goes back to the owner and is not guessed here.
- G-3: Assigned-puzzle exclusion (a puzzle held by another book is not offered) stays as it is (ADR-0033, one book per puzzle).
- G-4: Do not edit `src/nonogram/admin/book_manager.py` or `src/nonogram/admin/book_page_spec.py`. They are owned by CARD-124 / CARD-115 this wave.
- G-5: Do not edit `src/nonogram/export/**`. It is owned by CARD-125 this wave.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as … (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it … (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from … (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by more than 2x from the source's INK BOUNDING BOX … (check: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the other side from the source's own aspect ratio, … (check: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniqueness from the fact that a grid was repaired. (check: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit on one lineage, is a named constant beside it and is … (check: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that set holds no filled/empty pair), so the filled … (check: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws nothing from the injected Random or from host state, … (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DENSITY and MAX_DENSITY are the only statement of … (check: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density grounds, and no module's documentation claims … (check: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the share of cells settled at that rung; each … (check: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the tier is derived from … (check: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of the solve and … (check: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them, intersected), and are re-derived natively inside … (check: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all (empty or None per-cell tags, an all-zero … (check: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid it was handed and refuses, with … (check: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never satisfies a quality minimum, is never the left … (check: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id). (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percentage points of that cell's planned share. (check: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the … (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form … (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This … (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an … (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a parameter: no supported call into nonogram.admin.app widens … (check: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not pass the door in force. With it unset (the … (check: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured maximum bound (NFR-002). (check: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (check: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit move inside that level … (check: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; pairing never changes … (check: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 … (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; … (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the interior's; the cover is … (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-036
- **NFR:** —
- **ADR:** ADR-0033, ADR-0035 (plan-less remedy)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md (direction + anti-patterns), tokens.css (all visual values), components.md (inventory + states)
- **UI components:** PuzzleTile (reuse), FilterBar (reuse — size-range fields removed), TierChip (reuse), StatBlock (reuse for the planned-vs-selected summary; "emphasised" state for over-plan), Stepper (reuse); longest-side tabs — **register a "Tabs" entry in components.md** (states: default · current · with-over-plan marker)
- **Screens:** /book/<id>/select-puzzles (four tabs)
- **Standards:** forge:engineering-standards §11 (tokens-only styling, all listed states, a11y minimum — tabs keyboard-reachable, current tab announced)

## Worktree notes

—

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

- [Review sync] implementation notes pulled from worktree (commit 9d556e6)

### The two choices the card asks to record

**(a) How the tabs are implemented — server-rendered `?bucket=` on the existing
route.** No new routes, no client-side tab widget. Each tab is a real
`<button type="submit" name="go_bucket" value="21-25">` inside the step's own
form; pressing one POSTs the tab that is being left, the route folds its ticks
into the kept selection and redirects to `?bucket=21-25`. So every tab is a
distinct URL (browser back/forward walk them, and a tab can be linked or
bookmarked), the tabs are keyboard-reachable controls rather than `div onclick`,
and the current one is announced with `aria-selected="true"` + `aria-current`.
This is the option the requirements doc's own Open-items line already settled
("a `?bucket=` parameter on the selection route, so browser back/forward works").

**(b) Where a selection lives across tab switches — the session, not book
membership.** What the step does *today* is: tick tiles, press "Add selected
puzzles", and `book_mgr.add_puzzles_to_book` commits once and moves on to step 3.
That single commit point is kept. A tab switch must not commit (a half-made
selection is not a membership change, and committing on every switch would bounce
a non-draft book back to draft per INV-012 for nothing), and a committed puzzle
would vanish from the list anyway — the step only offers unassigned puzzles
(G-3, ADR-0033). So the ticks are kept in `session["book_selection"][book_id]`
and folded tab by tab (`shown_ids` names every tile a tab offered, so unticking
on its own tab really drops it while the other tabs are untouched). "Add
selected" still commits the whole kept set, once, and clears it.
The planned-vs-selected figures count **book membership ∪ kept ticks**, so the
headers answer "how am I doing" while the tick is still pending.

### What was built

- `src/nonogram/admin/app.py` — additive: a `# CARD-122` block of helpers
  immediately above `select_puzzles_for_book` (`_selected_tab`, `_tab_query`,
  `_kept_selection`/`_keep_selection`/`_drop_selection`/`_fold_tab_into_selection`,
  `_selected_cells`, `_tier_figures`, `_plan_progress`, `_is_in_tab`,
  `_tab_order`) plus the route itself. No existing route touched, nothing
  reordered — CARD-124 lands on the same file.
- G-1: the route imports `book_plan.bucket_of`, `planned_cells` and
  `selection_cells` and calls them; there is no second `max(w, h)` and no second
  threshold table. The store query is narrowed with the *bucket's own*
  `low`/`high` (a superset, since a puzzle's longest side is one of its sides)
  and `bucket_of` alone decides the tab.
- Sort inside a tab: tier (easy → medium → hard) then shorter side ascending,
  ungraded last, id as the final tie-break so renders are stable.
- Filters: theme, name, quality and difficulty still apply inside a tab;
  `size_from`/`size_to` are gone (AC-216).
- Plan-less book: the selected counts alone plus a link to Print setup
  (ADR-0035's remedy). Over-plan cells carry `data-over="true"` **and** the word
  "over" in the text, so the marker is not colour alone.

### Scope notes

- `SCOPE+ src/nonogram/admin/static/admin.css` — the Tabs and StatLine styles.
  Templates may not carry a `<style>` block or a colour literal
  (`tests/test_admin_design_tokens.py`), so token-only CSS has nowhere else to
  live. Additive: one new block before the existing "Puzzle selection tiles"
  section, nothing existing changed.
- `SCOPE+ tests/test_card_063_limits.py`, `SCOPE+ tests/test_card_065_follow_ups.py`
  — three assertions pinned the size-range inputs *on this template*, which
  AC-216 removes. `test_the_book_puzzle_filter_renders_the_range` was retargeted
  to assert the field is gone and that the four tabs tile `MIN_SIZE..MAX_SIZE`;
  `book_select_puzzles.html` was dropped from two parametrize lists (the other
  templates still carry both assertions, and the "never says pixels" half of
  CARD-065's rule was kept for this template in a test of its own). No
  guardrailed behaviour was weakened — the removals are exactly the behaviour
  this card's AC deletes.
- `meta/design/components.md` — "Tabs" registered as the card asks (states:
  default · hover · current · with-over-plan marker), plus "StatLine" for the
  planned-vs-selected summary. (meta/ is not committed.)

### Tests

`tests/test_book_select_tabs.py`, 20 tests, all green: one class per AC named as
the card names it, plus `test_PropertyTest_LongestSideBuckets_PartitionEveryExtent`
— the route-level case this card adds to CARD-119's property (every one of the
441 supported extents is offered on exactly one rendered tab, on the tab
`bucket_of` names; tabs are read page by page because the store caps a page at
100 rows). The function-name spelling follows the existing
`tests/property/test_longest_side_buckets.py`, since pytest collects `test_*`,
not `PropertyTest*`. Evidence class is the Flask test client throughout — this
project has no browser harness.

Known pre-existing failure, not this card's:
`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`.

- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/book_select_puzzles.html, tests/test_book_select_tabs.py, tests/test_card_063_limits.py, tests/test_card_065_follow_ups.py
- [Build gate] PASSED (full, 237s) — exit 0, known pre-existing e2e failure deselected (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied)
- [Scope gate] ⚠ grown: 3 files outside Touches (src/nonogram/admin/static/admin.css, tests/test_card_063_limits.py, tests/test_card_065_follow_ups.py) — comp_spread 0 (COMP-009 only), no guardrail hit, no sibling poaching (CARD-124 overlap 25% < 30%)
- [Visual] no Makefile run target and no browser harness in this project — review runs static-only (rendered result not verified)

- [Review 1/3] Score: 5.0 — crit: 1, imp: 4
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: 44/44 card rules carry a verdict line (14 ✓ holds, 30 ⚠ unchecked no_eligible_fact, 0 ✗)
- [Adversarial] F-001 (tabs drop 371/441 puzzles at default paging) CONFIRMED — reproduced independently: <=15 renders 0/36, 16-20 0/85, 21-25 20/135, 26-30 50/185; side_range is an either-side superset sliced before _is_in_tab, and no pagination control exists (has_more passed but never rendered)
- [Adversarial] F-003 (EC-024 property test issues ?limit=100&offset=N the product never emits) CONFIRMED — the page emits no pagination control at all and deliberately does not use the panel's own _puzzle_table.html paginated partial; route passes limit/offset/has_more into the context and the template never renders them
- [Adversarial] F-002 ("(N available)" counts the post-slice page, renders a false "(0 available)" + empty state) CONFIRMED — reproduced: 12 genuine <=15 members rendered as "(0 available)"; note the skeptic's caveat that the store's own total_count is the either-side SUPERSET (72), so the fix must make the query bucket-exact, not merely swap in result.total_count
- [Adversarial] F-005 (tab-strip over-plan marker is colour-only) CONFIRMED — .tab[data-over="true"] .tab-count sets `color` alone (admin.css:219) with no text/glyph/weight/aria cue in the button; the word "over" does not occur anywhere on the rendered page when the over-plan bucket is not the current tab, and components.md:155 registers the state while the StatLine entry explicitly promises "never colour alone"
- [Adversarial] F-004 (kept selection in the signed session cookie overflows ~4093 B) CONFIRMED — SecureCookieSessionInterface confirmed on the real app, ids are 36-char UUIDs (db/models.py:52); measured Set-Cookie: 133 ids = 4068 B fits, 134 = 4098 B overflows; DEFAULT_PLAN is 150 puzzles and "Select all" x3 tabs reaches it, so the ceiling sits below the product's own default book size
- [Review 1/3] all 5 gating findings CONFIRMED by independent skeptics (0 refuted) — F-001/F-002/F-003 share one root cause: bucket membership is decided in Python after the store has already paginated an either-side superset
- [Fix 1] FIXED F-001..F-005 (all five gating findings) + F-007..F-010; SKIPPED F-006 (one-query _selected_cells would read the puzzles.book_id mirror, which BookManager writes only when given a puzzle store — a correctness change dressed as a perf one; needs a bulk get_puzzles(ids), wider than this card's scope exception). Fix pre-gate: the named tests were run directly — TestBookSelect_TabOffersItsOwnMembersAtDefaultPaging, TestBookSelect_AvailableCountIsTheTabsOwnTotal, TestBookSelect_PendingSelectionDoesNotRideInTheCookie, TestBookSelect_OverPlanTabMarkedBeyondColour, test_PropertyTest_LongestSideBuckets_PartitionEveryExtent — all present and green (91 passed across the four touched test files)
- [Touches drift] card diff vs merge base 2dd96af is 8 code files; 5 outside Touches: src/nonogram/admin/puzzle_review.py (SCOPE+, additive PuzzleFilter.longest_side_range for F-001), src/nonogram/admin/static/admin.css, tests/test_admin_filter_side_range_and_name.py (+67/-0), tests/test_card_063_limits.py, tests/test_card_065_follow_ups.py
- [Scope gate] cycle 2: GROWN (unchanged) — no guardrail hit (book_manager.py / book_page_spec.py / export/** untouched), comp_spread 0 (COMP-009 only), CARD-124 overlap still 25% < 30%; no existing test weakened (the only deletions are this card's own new file and the AC-216 retarget already judged necessary)
- [Build gate] PASSED (full, 192s) — 4122 passed, 26 skipped, 1 deselected (the known pre-existing e2e failure); golden A4 tripwire green and untouched
- [Fix 1] declarations: 8 updated, 2 confirmed, 1 none — doc PuzzleFilter.longest_side_range / select_puzzles_for_book / _pending_selections / _SELECT_FILTERS / _RETIRED_SIZE_PARAMS, components.md Tabs entry, card notes choices (a) and (b); (b) FALSIFIED and rewritten — pending ticks are now server-side, not in the session cookie; confirmed-still-correct: StatLine entry, INV-012 commit point
- [Fix 1] verify-by-revert done by the fix agent: every new test fails on 9d556e6 with the finding's own symptom (F-004 measured 4546 B > 4093 limit once ids are re-keyed to the DB's 36-char UUID shape)
- [Fix 1] design change stated, not hidden: a pending selection's lifetime is now the admin process's — a restart or a 33rd concurrent browser session drops uncommitted ticks (bounded LRU of 32 tokens). Nothing committed is at risk; CON-015 makes the panel single-process loopback. NEEDS OWNER AWARENESS.
- [Review 2/3] Score: 6.5 — crit: 1, imp: 0 (Δscore +1.5, Δcrit+imp -4 — not stalled)
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h coverage: 44/44 card rules carry a verdict line (16 ✓ holds, 28 ⚠ unchecked no_eligible_fact, 0 ✗) — re-derived, not carried
- [Review 2/3] all five cycle-1 findings verified RESOLVED (F-001..F-005); F-006 skip judged legitimate; no test weakened; every scope excess judged necessary
- [Review 2/3] ⚠ same defect CLASS as F-001 reappeared one layer over: work applied AFTER the store's slice. Cycle 1 it was the bucket filter; cycle 2 it is the tier-then-shorter-side sort. Streak 1 (escalates at 2) — the cycle-2 fix is told to address the class, not the instance.
- [Adversarial] F-011 (tier-then-shorter-side sort applied per page, not per tab) CONFIRMED — the route passes no sort_by, so the store uses its default "batch_id,-size,quality", slices at _SELECT_PAGE=50 (store caps limit at 100), and app.py:2556 sorts only the returned page; measured 60 members of 21-25: page 1 easy x17 / medium x17 / hard x16, page 2 RESTARTS easy x3 / medium x3 / hard x4 — a hard 25x21 renders before an easy 25x19. AC-215's own 4-puzzle test is one page, so it cannot see it; the EC-024 walks compare sorted() on both sides and assert membership only
- [Fix 2] FIXED F-011 (the Critical) + F-012..F-016 (all five minors); SKIPPED the cycle-1-deferred N+1 (info severity, follow-up card for a bulk get_puzzles(ids)). Fix pre-gate: all 21 named tests exist and are green
- [Fix 2] declarations: 6 updated, 1 confirmed, 0 none — doc PuzzleFilter.sort_by (token grammar), _apply_sort_to_query, _tab_order (now documented as the cross-check, not the mechanism), _pending_selections, _drop_selection, book_plan.bucket_of (the two-part pushdown contract); components.md Tabs entry; card notes. No EXISTING sort token changed meaning — pinned by test_the_existing_sort_tokens_still_mean_what_they_meant (PuzzleFilter has 49 callers, so the change is additive, not a default edit)
- [Fix 2] post-slice sweep done as asked: 6 operations classified (a) inside the query, 3 (b) provable no-ops (_is_in_tab and the route's _tab_order are now no-ops BY CONSTRUCTION and pinned by a store-page-vs-rendered-page test), 0 remaining (c). This closes the defect class that cost cycles 1 and 2
- [Fix 2] verify-by-revert: removing only sort_by=BOOK_TAB_SORT reproduces the finding's own symptom (page 2 restarting at easy)
- [Scope gate] cycle 3: GROWN (unchanged) — +SCOPE+ src/nonogram/admin/book_plan.py, DOCSTRING-ONLY (17 added lines, verified no non-comment change). Guarded paths verified empty in the diff vs base: src/nonogram/export/**, book_manager.py, book_page_spec.py, and the golden A4 tripwire. AC-215's own 4-puzzle test byte-identical to 9d556e6 — extended, not replaced
- [Build gate] PASSED (full, 151s) — 4140 passed, 26 skipped, 1 deselected (+18 tests from the cycle-2 fix); golden A4 tripwire green and untouched
- [Review 3/3] Score: 8.5 ✓ threshold reached + no critical/important (Δscore +2.0, Δcrit+imp -1)
- [Review sync] 3 report(s) → meta/review/
- [Review 3/3] Step 8h coverage: 44/44 card rules carry a verdict line (16 ✓ holds, 28 ⚠ unchecked no_eligible_fact, 0 ✗) — re-derived with fresh evidence, not carried
- [Review 3/3] defect class CLOSED — the reviewer redid the post-slice sweep independently and reached the same 6 (a) / 3 (b) / 0 (c), proving both 'provable no-op' claims (_is_in_tab and the route's _tab_order) rather than accepting them. Family-regression streak ends at 1; no escalation
- [Review 3/3] mutation spot-check run (deferred certification, no gating findings): swapping the first two terms of BOOK_TAB_SORT was killed by 3 tests; file restored and sha-verified
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, INV-012) — each by an independent skeptic that re-ran the named check and re-derived the evidence rather than reading the reviewer's prose
- [8h spot-check] INV-012 caveat surfaced by the re-derivation, NOT a regression from this card: the invariant's "returns it to draft as part of that change" half is not implemented anywhere in the repo — add_puzzles_to_book/remove_puzzle_from_book never reset status, and the six named INV-012 tests do not exist (CARD-131 owns them). Identical at base 2dd96af, so CARD-122 neither introduces nor worsens it. Empirically: all four new POST controls (go_bucket/go_offset/go_filter/go_clear), plus forged and combined variants, leave a ready_for_pdf book's status and membership untouched
- [AC/EC check] All criteria/constraints ✓ (evidence): 16 demonstrated, 0 partial, 0 contradicted, 0 unverified — AC-208..AC-217, EC-024, G-1..G-5. Each AC evidenced by the named test run as a Flask-test-client spec against the real route (the accepted evidence class here: no browser/e2e harness exists). EC-024 verified in BOTH halves — CARD-119's exhaustive 441-extent partition (minimum asserted in-test, expected bucket derived independently of bucket_of) and this card's route-level walk, whose primary parametrisation uses ONLY the URL the product emits (?bucket=<label>, then the rendered "Next page" submit followed through its 302); the ?limit/&offset walk survives only as a labelled second case. G-4/G-5 verified structurally (guarded globs absent from both the committed and uncommitted change sets); G-3 verified behaviourally (tests/test_card_100_book_membership.py + test_card_108, 71 passed, neither file in the card's diff)
- [AC/EC check] G-1 note, not a failure: the card's literal wording says "the route and the template import book_plan.bucket_of". A Jinja template cannot import; the template consumes `tab_progress`/`current_bucket` handed down by the route and carries no thresholds of its own, so the substance of G-1 holds. Worth rewording the guardrail at the decompose station rather than in the worktree
- [Docs] no README change: src/ carries no per-directory READMEs anywhere in this project (creating one for src/nonogram/admin would invent a convention, and CLAUDE.md forbids proactive doc files). tests/README.md exists but is a stale "Wave 1" document that CARD-113/115/119/120/125 all left untouched — repairing it is a repo-wide chore, not this card's scope. The card's own documentation landed as docstrings (the bucket_of pushdown contract, PuzzleFilter.sort_by's token grammar) and meta/design/components.md (Tabs + StatLine)
- [Commit] 223fa3e feat(book-select): page and order the longest-side tabs inside the store query — 8 files, +1315/-66 (on top of 9d556e6). Staged by explicit pathspec; nothing under meta/ committed
- [Review sync] 3 report(s) → meta/review/ with fixed_in: 223fa3e stamped on every resolved finding (F-006, the N+1, deliberately left status: open — it is the follow-up card)
- [Handover → CARD-124] this card's app.py edits are confined to imports + create_app's 2203-2645 region; no existing route touched, nothing reordered. New shared helper you may want: puzzle_review.PuzzleFilter.longest_side_range and BOOK_TAB_SORT (both additive; no existing sort token changed meaning)
- [Handover → CARD-131] INV-012's "returns it to draft as part of that change" half is NOT implemented anywhere in the repo — add_puzzles_to_book/remove_puzzle_from_book never reset status, and the six named INV-012 tests do not exist. Unchanged by this card (identical at base 2dd96af), confirmed empirically
- [Follow-up card needed] bulk PuzzleReviewService.get_puzzles(ids): _selected_cells does one get_puzzle per book member plus per kept tick, up to ~300 DB sessions per render on a DEFAULT_PLAN book. The obvious one-query fix is WRONG (it reads the puzzles.book_id mirror, which BookManager writes only when it has a puzzle store)
- [Follow-up card needed] pre-existing, not this card: a hand-typed empty ?status= turns the approved-only default off (request.values.get("status", "approved") returns the default only when the key is absent). Same pattern on the puzzle-list route

*Re-derived after review cycle 1 and still correct, with one addition:* a tab
now has **pages**, and a page is the same mechanism — a
`<button type="submit" name="go_offset" value="50">` that POSTs, folds the
page's ticks into the kept selection and redirects to `?bucket=…&offset=50`.
So every page of every tab is a real URL too. The current tab is announced by
`aria-selected="true"` alone; `aria-current="page"` is gone (these controls
submit a form, they do not navigate — F-010).
**(b) Where a selection lives across tab switches — pending state, not book
membership; and since review cycle 1 it is held server-side, not in the
cookie.** What the step does *today* is: tick tiles, press "Add selected
(G-3, ADR-0033). So the ticks are kept as *pending* state and folded tab by
tab (`shown_ids` names every tile a tab offered — now every tile a *page* of
a tab offered — so unticking on its own page really drops it while every
other page and tab is untouched). "Add selected" still commits the whole kept
set, once, and clears it.
**Correction (review cycle 1, F-004).** The first implementation put that
pending set in `session["book_selection"][book_id]` — the *signed cookie*,
since the panel uses Flask's default client-side session. 150 UUID ids is a
4.5 KB cookie against a 4093-byte limit, and an over-long cookie is discarded
by the browser whole and in silence, taking `unit_preference` and
`book_<id>_cover_path` with it; a default-plan book is exactly 150 puzzles and
the page has a "Select all" button. The ids now live in
`create_app`'s own `_pending_selections` map, keyed by a short
`secrets.token_urlsafe` token that is the only thing in the cookie.
What that changes, stated rather than assumed: **a pending selection's
lifetime is now this process's.** Restarting the panel, or opening a 33rd
browser session (`_PENDING_SELECTION_TOKENS`) before returning to this one,
drops ticks that were never committed. Nothing committed is at risk and the
commit point is unchanged — `add_puzzles_to_book`, once, still the only one
(INV-012 unaffected). The panel is a single-process loopback tool (CON-015),
so there is no second worker that could miss the map.
**Re-derived in review cycle 2, with two additions.** (i) The pending set now
has a way *out* other than committing or restarting: "Clear all selected"
(`go_clear`) drops it through `_drop_selection`, deliberately **before** the
tab's ticks are folded, since the page's own ticks are part of what is being
cleared (F-003). That is a lifecycle addition, not a change: the map is still
process-local, the commit point is still one. (ii) Werkzeug's dev server is
threaded, so the map really is shared mutable state under concurrent requests
(F-005). Every mutation of `_pending_selections` and of the per-book lists
inside it is now taken under a module-level `threading.Lock()`, held for one
dict operation and never across a call that takes it again — so the map is
guarded rather than assumed single-threaded, and the docstring says which.
**(c) What "Apply" on the filter card does — it submits the step (cycle 2,
F-002).** The Filters card used to be its own `method="GET"` form: pressing
Apply navigated away without POSTing the step, so the tiles ticked since the
page loaded were dropped with no message, while the pagination footer promised
"Ticks are kept as you move". The filter controls now belong to the step's own
form through HTML5 `form="puzzleForm"` (a card cannot nest a form inside
another), and Apply is a `name="go_filter"` submit that takes the same
fold-then-redirect path as `go_bucket` and `go_offset`. It lands on **page 1**
of the same tab, because the page numbers the owner left belong to the old
result set. The four filter names are no longer repeated as hidden inputs in
the step's form — a hidden twin would submit each name twice — while `status`,
which has no visible control, still travels as one.
  `selection_cells` and calls them; there is no second `max(w, h)` threshold
  table. The store query is narrowed with the *bucket's own* `low`/`high` and
  `bucket_of` alone names the tab.
  **Corrected in review cycle 1 (F-001).** That narrowing used to be
  `side_range=(low, high)`, which the store reads as "*either* side in range" —
  a strict superset of the tab. The store sorted and LIMITed the superset and
  the route dropped the non-members afterwards, so with 441 available puzzles
  the four tabs rendered 70 of them and 371 were unreachable. The bucket is now
  part of the query: `longest_side_range=(bucket.low, bucket.high)`, which the
  store implements as `max(width, height)` (a CASE in SQL — SQLite's two-arg
  `max()` is Postgres' `greatest()`, and the expression has to mean one thing).
  The `(low, high)` pair still comes from `book_plan` and nowhere else, and
  `_is_in_tab`/`bucket_of` still names the tab; what changed is that LIMIT now
  bites on the tab's own members.
- Pages of a tab (F-001/F-003): the panel's list is paged with
  `button.page-link name="go_offset"` controls — submit buttons, not links, so
  a page move keeps the page's ticks the way a tab switch does. `limit` and
  `offset` in `_SELECT_FILTERS` were dead entries and are now real (F-007):
  `limit` is carried across a move, `offset` is set by the control pressed.
- The header's "(N available)" is the store's count of that same query, not
  the surviving slice of a page (F-002); the "no approved puzzles" empty state
  shows only when that total is genuinely 0.
- A retired `?size=` / `?size_from=` / `?size_to=` on this route is now
  answered with a flash rather than silently ignored (F-009).
  **Corrected in review cycle 2 (F-001).** That order used to be a
  `sorted(result.puzzles, key=_tab_order)` at the route — applied to the rows
  the store had *already* sliced with LIMIT/OFFSET, so each page was an
  arbitrary subset of the tab re-sorted in isolation and the tier sequence
  restarted at easy on page 2. Measured: 70 members of the 21-25 tab rendered
  easy×17 · medium×17 · hard×16 on page 1, then easy×7 · medium×6 · hard×7 on
  page 2. Three of the four tabs are multi-page on the owner's corpus
  (36/85/135/185 members at `_SELECT_PAGE = 50`), so AC-215's order was wrong
  on all three. The order is now a `sort_by` the **store** applies, before it
  counts and before it slices: `puzzle_review.BOOK_TAB_SORT` =
  `tier_rank,shorter_side,longer_side,id`. `_tab_order` stays at the route as
  the cross-check, the same way `_is_in_tab` does — it is that sort spelled in
  Python term for term, so re-sorting a page by it returns the page it was
  handed.
  It is the same defect class as cycle 1's F-001, one step along: **anything
  that decides which rows the owner sees, or in what order, has to happen
  inside the store query, because LIMIT/OFFSET have already run by the time
  the route sees `result.puzzles`.** Both halves of that sentence now live in
  the query, and the *post-slice sweep* below names every operation that is
  left.
### Post-slice sweep (review cycle 2)
Every operation the route applies to `result.puzzles`, or to anything derived
from it, and what each one is:
| Operation | Verdict |
| --- | --- |
| `longest_side_range=(bucket.low, bucket.high)` | (a) inside the query (cycle 1) |
| `sort_by=BOOK_TAB_SORT` | (a) inside the query (cycle 2, this fix) |
| `p.get("book_id") is None` | (b) provable no-op — restates `book_id="unassigned"`, which both store backends already apply (G-3) |
| `_is_in_tab(p, bucket)` | (b) provable no-op — the buckets partition `MIN_SIZE..MAX_SIZE`, so a row whose longest side is in `[low, high]` is a row `bucket_of` puts on this tab |
| `sorted(..., key=_tab_order)` | (b) provable no-op — `_tab_order` is `BOOK_TAB_SORT` term for term |
| `total_count=result.total_count` | (a) the store's `count()` of the same query, taken before the slice |
| `has_more=result.has_more` | (a) `offset + limit < total`, computed in the store from the same figures |
| `_page_window(result.total_count, result.limit, result.offset)` | (a) arithmetic over the store's totals — it never reads the returned rows |
| `_plan_progress(book, kept_ids)` / `_selected_cells` | not derived from the page at all: book membership ∪ kept ticks, resolved by id through `get_puzzle`. No tab and no page bounds it, which is why the whole-book summary reads the same on every tab |
The last three are the ones worth stating out loud: the "(N available)" figure,
the pagination window and the planned-vs-selected summary are the three places
a page slice would be easiest to mistake for the whole, and none of them reads
one. Pinned by `test_the_route_changes_nothing_about_the_page_the_store_returned`
(the store's page and the rendered page are the same ids in the same order, on
page 2 as much as page 1), `TestBookSelect_AvailableCountIsTheTabsOwnTotal` and
`test_the_whole_book_summary_is_the_same_on_every_tab`.
  "over" in the text, so the marker is not colour alone — and since review
  cycle 1 (F-005) the *tab strip* does too: an over-plan tab's `.tab-count`
  carries a `.tab-over` chip reading "over". The strip is the only place the
  other three tabs signal anything, and it used to signal in colour only.
  planned-vs-selected summary. (meta/ is not committed.) Re-derived in review
  cycle 1: the Tabs entry now records the `.tab-over` word (F-005), the
  `aria-controls`/no-`aria-current` wiring (F-010) and the tab's pages.
- `SCOPE+ src/nonogram/admin/puzzle_review.py` — F-001's sound fix needs the
  bucket inside the query, and the store is the only place that can express
  it. One appended field, `PuzzleFilter.longest_side_range`, with its branch
  in each of the two backends plus `to_dict`/`from_dict`. Strictly additive:
  no existing field was reordered or re-read, and `side_range` still means
  "either side in range" for the review page that drives it. Its own tests sit
  beside that filter's, in `tests/test_admin_filter_side_range_and_name.py`.
  **Widened in review cycle 2, and for the same reason:** the tab's *order*
  has to be in the query too, so the `sort_by` grammar gained three computed
  tokens — `tier_rank`, `shorter_side`, `longer_side` — beside the existing
  `id`, plus the named `BOOK_TAB_SORT` that spells AC-215's order in them.
  Still strictly additive: no field was reordered, and **no existing token
  changed meaning** — `difficulty` still sorts the stored *string*, `-size` is
  still width descending, and `PuzzleFilter().sort_by` is still
  `"batch_id,-size,quality"`, which the puzzle-list and batch routes
  (app.py:1741/1782/1860/1865) drive. Pinned by
  `test_the_existing_sort_tokens_still_mean_what_they_meant`.
  `tier_rank` reads `book_plan.TIERS` — the *existing* tier order, imported,
  not a second ladder (G-1) — through `difficulty.tier_of_record`, so a row
  carrying either spelling ranks the same; the SQL branch's CASE table is
  *derived* by calling that same Python function, so the two backends cannot
  drift. `test_both_backends_spell_the_same_book_tab_order` runs the same
  corpus through an in-memory store and a real SQLite one and compares the
  rendered order, which also closes cycle 2's "DB branch read but not run"
  coverage gap.
- `SCOPE+ src/nonogram/admin/book_plan.py` — docstring only, no behaviour.
  Review cycle 2's F-006 asked for `bucket_of`'s "both sides inside
  MIN_SIZE..MAX_SIZE" clause to be recorded as the contract the store's
  pushdown must mirror, since it is restated in the two store backends. It is
  now written into `bucket_of`'s own docstring as a two-part contract, and
  `PuzzleFilter.longest_side_range` points at it instead of re-arguing it.
  `TIERS` is also *read* from here by `puzzle_review` now (import only).
`tests/test_book_select_tabs.py`, 29 tests, all green: one class per AC named as
`bucket_of` names). The function-name spelling follows the existing
Review cycle 1 added the cases whose *given* is the screen's given:
- the property test is parametrised over two walks. The first, **"as the page
  renders it"**, loads each tab at the default URL — no `limit`, no `offset`,
  because the page emits neither — and follows the "Next page" control it
  renders. The second keeps the old hand-paged walk at the store's cap. Only
  the first speaks for the product (F-003); on the pre-fix code it fails with
  "371 puzzles were offered on no tab at all".
- `TestBookSelect_TabOffersItsOwnMembersAtDefaultPaging` (F-001),
  `TestBookSelect_AvailableCountIsTheTabsOwnTotal` (F-002),
  `TestBookSelect_PendingSelectionDoesNotRideInTheCookie` (F-004, measured in
  bytes against Werkzeug's 4093 limit, on ids re-keyed to the database's UUID
  shape) and `TestBookSelect_OverPlanTabMarkedBeyondColour` (F-005). Every one
  of them fails on `9d556e6` with the finding's own symptom (verified by
  reverting the source and re-running).
- `tests/test_admin_filter_side_range_and_name.py` gained the store-level half:
  "either side in range" and "longest side in range" name different sets, and
  LIMIT bites on the members.
- `tests/test_card_063_limits.py`'s retargeted test now reads the rendered tab
  strip instead of restating two `BUCKETS` constants (F-008).
Review cycle 2 added the cases whose corpus outgrows one page, which is where
the defect lives:
- `TestBookSelect_TabOrderHoldsAcrossTheTabsPages` (F-001) — 70 members of the
  21-25 tab with the tiers round-robined across the shorter sides, walked the
  way the screen is walked (default URL, then the rendered "Next page"
  control). Four cases: the concatenated pages equal the card's order
  (computed independently from what the test built, not from `_tab_order`);
  the tier sequence never restarts; the shorter side climbs inside each tier
  across pages; and the rendered page equals the store's page id for id. On
  the pre-fix code the first three fail with the finding's own symptom —
  `page sizes [50, 20], tiers [0×17, 1×17, 2×16, 0×7, 1×6, 2×7]`.
- `TestBookSelect_ApplyingAFilterKeepsThisPagesTicks` (F-002),
  `TestBookSelect_ClearingThisPageAndClearingEverything` (F-003) and
  `TestBookSelect_TabStripImplementsTheTabsPatternItDeclares` (F-004).
- `tests/test_admin_filter_side_range_and_name.py` gained the store-level half
  again: the tab sort is a tier *rank* (not the tier string), an ungraded row
  sorts last, LIMIT slices that order rather than some other one, the two
  backends spell it identically against a real SQLite engine, and the existing
  tokens are unchanged.
### Noted, not fixed
- F-006 (N+1 in `_selected_cells`: one `get_puzzle` per book member). The
  obvious one-query replacement — `filter_puzzles(PuzzleFilter(book_id=...))`
  — reads the `puzzles.book_id` **mirror**, and `BookManager._mirror_onto_puzzles`
  writes it only when the manager was given a puzzle store; a manager without
  one (the shape half this project's tests build) keeps the book's half alone
  and logs that it did. Swapping the loop for that query would therefore make
  the planned-vs-selected figures depend on whether the mirror happens to be
  written, which is a correctness change dressed as a performance one. Doing
  it properly needs a bulk `get_puzzles(ids)` on the store — a second, wider
  change to `puzzle_review.py` than this card's scope exception allows. Left
  as it is, deliberately.

- [Done] rebased onto main 3f7e61e (after CARD-125), full suite on the rebased tree: only the pre-existing e2e failure. Merged 37f1b68 (--no-ff). Deferral scan: 0 hits. SCOPE+ recorded by the pipeline (puzzle_review.py pushdown, admin.css, 3 existing test files, book_plan docstring) — scope gate GROWN, never violated. Two follow-ups and two card-text defects captured to backlog.
