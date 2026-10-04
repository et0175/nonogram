# CARD-175: On a phone, a /books row folds its off-plan hints behind one summary line

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/175-books-hints-compact-on-phone
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (IDEA-047, from CARD-158 review finding F-005)
**Idea:** IDEA-047
**Wave:** 33
**Depends on:** —
**Touches:** src/nonogram/admin/templates/books_list.html, src/nonogram/admin/static/admin.css, tests/test_books_list_plan_stats.py, tests/test_books_list_mobile.py (new)
**Review score:** 9.6 (cycle 2/3)
**Started:** 2026-10-04T14:27:57Z
**Closed:** 2026-10-04T17:07:34Z
**Actual:** 0.3d
**Merge commit:** ecca05d
**Blocked by:** —

## What to implement

**Current behaviour (verified on main 2e071b4).**
`books_list.html` renders an "Against plan" cell per row. For a book with a
plan, the cell holds two `<p class="stat-line">` lines:
1. the per-tier split (`easy 2 / 60 · medium 1 / 60 · hard 1 / 30`);
2. the to-do list: one `<span class="stat-cell" data-off-plan="true">` per
   off-plan cell, e.g. `16-20 × easy: short 28`.

The hints come from `app.py:_book_plan_stats` (the `hints` list, built at
about line 2491). There is one hint per longest-side bucket × tier cell that
is off plan: 4 buckets × 3 tiers (`book_plan.BUCKETS`, `book_plan.TIERS`), so
up to 12 hints. `.stat-line` is `display: flex; flex-wrap: wrap`
(`admin.css:245`), so each chip wraps onto its own line.

At 390 px the table sits in `.table-responsive` (horizontal scroll). The
narrow hints column then stacks every chip, and even breaks chips mid-text.
CARD-158's renders show each row about 650 px tall, mostly empty space beside
the title and actions (`~/Documents/nonogram-reviews/CARD-158/after-books-390.png`,
`after-books-390-scrolled-to-actions.png`). At 1440 px the same 10-hint row
is about 330 px tall (`after-books-1440.png`). That desktop look is the one
to keep.

**Target behaviour.**
- When a book has hints, wrap the to-do list in a disclosure:
  `<details class="plan-hints">` with a `<summary>` that states the count in
  words, e.g. "10 cells off plan". Use singular "1 cell off plan" for one.
  The summary must not contain the words "short" or "over".
  `TestBooksList_NoHintWhenOnPlan` forbids those words only on an on-plan
  row, but the summary is clearer without them.
- **At ≤ 820 px** (the panel's existing breakpoint, `admin.css:330`) the
  disclosure starts closed. The row shows the tier split plus the one summary
  line. Tapping the summary opens the full list.
- **At > 820 px** the row looks as it does today. Hide the summary and force
  the list visible. Suggested CSS:
  `@supports selector(::details-content)` around
  `@media (min-width: 821px) { .plan-hints > summary { display: none } .plan-hints::details-content { content-visibility: visible; display: contents } }`.
  If a browser lacks `::details-content`, it keeps a working disclosure on
  desktop too. The list is never hidden without a way to open it. No
  JavaScript.
- Chips keep their exact markup: `stat-cell`, `data-off-plan="true"`, the
  same text, in the same order. The existing `hints_of` regex and the CK-4
  corpus test read them unchanged. Each chip should not break mid-text
  (`white-space: nowrap` on chips inside `.plan-hints`).
- "On plan" and "No plan yet — set one in Print setup" rows are unchanged.
  They get no `<details>`.
- Tokens only (no hex, no new colours). `test_the_stylesheet_uses_tokens_not_literals`
  pins this. The summary uses `--text-sm` and `--color-text-secondary`, like
  other secondary row text.
- Record the new state as a `DESIGN-REGISTER` line in Worktree notes (DataTable "plan hints":
  closed disclosure ≤ 820 px, always open above). Do not edit `meta/design/components.md`: card
  commits exclude `meta/`; the dispatcher applies the line at merge.

## Acceptance criteria

- **AC-1:** Given a book with 10 off-plan cells, when /books renders, then its Against-plan cell holds exactly one `<details class="plan-hints">`, whose `<summary>` reads "10 cells off plan", and all 10 `data-off-plan` chips sit inside that `<details>`, in the order `_book_plan_stats` returns them.
  *test: TestBooksList_HintsFoldBehindASummary (in tests/test_books_list_plan_stats.py)*
- **AC-2:** Given a book with exactly one off-plan cell, when /books renders, then the summary reads "1 cell off plan". Given an on-plan book or a plan-less book, the row has no `<details>` and still says "On plan" or "No plan yet".
  *test: TestBooksList_HintSummaryCountsAndAbsence (in tests/test_books_list_plan_stats.py)*
- **AC-3:** Given that 10-hint book in Chromium at 390 × 844, when /books loads, then the summary is visible, no chip is visible, the row's height is ≤ 220 px, and the page does not scroll sideways (`documentElement.scrollWidth ≤ innerWidth`). Clicking the summary makes all 10 chips visible.
  *test: TestBooksListMobile_RowIsCompactAtPhoneWidth (in tests/test_books_list_mobile.py, `@pytest.mark.browser`)*
- **AC-4:** Given the same book at 1440 × 900, when /books loads, then the summary is not visible and all 10 chips are visible without any click (desktop unchanged).
  *test: TestBooksListMobile_DesktopShowsEveryHint (in tests/test_books_list_mobile.py, `@pytest.mark.browser`)*

## Guardrails

- G-1: The hint data does not change: same cells, exact counts, wording `_PLAN_HINT`, order (FR-039, ADR-0035 (d)). `app.py` should need no change. Every existing test in `tests/test_books_list_plan_stats.py` (AC-230..AC-235, CK-2..CK-4) passes unmodified.
- G-2: No route, sort, export or PDF behaviour changes. CARD-158's cover/interior buttons and lost-cover hint (`TestBookPages_OfferBothExportFiles`, `tests/test_book_detail_page.py`) are untouched.
- G-3: Design system only: no page-local `<style>`, no hex literals, no inline colours (`tests/test_admin_design_tokens.py`). No JavaScript added to this page.
- G-4: CARD-158's 390 px no-sideways-scroll fix (`.table-responsive { position: relative; }`) stays. AC-3 re-asserts it.
- G-5: Browser tests follow ADR-0038/R7–R8. Reuse `browser_page` / `browser_type` / `_build_app` from `tests/test_puzzle_solver_page.py`, as `tests/test_book_setup_print_mobile.py` does. They fail loudly if Chromium is missing. They never skip silently.
- G-6: The owner checks rendered pages (memory: owner validates visually) before merge.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-175` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR-039** (books list plan statistics): AC-230..AC-235. This card changes presentation only. The FR-039 trace entry lists COMP-009 / CAP-006 / ADR-0035.
- **ADR-0035** (d): hints carry exact counts. The disclosure must not round or hide that count.
- **ADR-0038** R7/R8: pytest-playwright + Chromium, dev extra only, loud failure when the browser is absent.
- **COMP-009** Admin Panel, CTX-001. No other component is touched.
- Trace: FR-039 → COMP-009 → `books_list.html` + `admin.css`. The new tests are evidence of presentation, not new FR-039 ACs. Append them to the FR-039 trace tests only if the dispatcher's write-back convention does that for card-local ACs.

## Design context

- **Screen:** /books, at 390 px (phone) and 1440 px (desktop). Component: DataTable "Against plan" cell (`meta/design/components.md` DataTable; brief: Pressroom, medium density, WCAG 2.1 AA).
- **Disclosure:** a native `<details>`/`<summary>`. It is keyboard-focusable and announced as expandable without ARIA additions. The chips keep their warning tint plus the words "short"/"over", so the hint still reads without colour.
- **Renders:** ~/Documents/nonogram-reviews/CARD-175/ — `before-books-390.png`, `after-books-390.png` (closed), `after-books-390-open.png`, `after-books-1440.png` (must match CARD-158's `after-books-1440.png` layout). Use a book with ~10 hints, like CARD-158's "Christmas Nonograms for Adults" fixture. Owner visual check.

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-047 (WSJF 1.5, roadmap estimate 0.25d; card says 0.5d because of the two browser tests). Source: CARD-158 review F-005 (`meta/review/20261002T172339Z-CARD-158-cycle1.yml`), "collapse hints on narrow viewports".
- [Facts] Template hint block: `books_list.html`, the `{% if stats.hints %}` branch inside the Against-plan `<td>` (about lines 88–96 on main 2e071b4). The visually-hidden "Off plan:" label lives inside that `<p>`. Keep it inside the `<details>` body, or fold it into the summary.
- [Facts] `tests/test_books_list_plan_stats.py:280` `hints_of` reads chips with `data-off-plan="true"[^>]*>(.*?)</span>`. Don't add `data-off-plan` to the summary, or every exact-list assertion there will fail.
- [Facts] `row_of` (`:262`) and `Shelf.listing` (`:236`) are the HTML helpers. Build AC-1/AC-2 on them. The `shelf` fixture builds books with chosen plans and cells.
- [Facts] Browser test pattern to copy: `tests/test_book_setup_print_mobile.py`. It has a live server over `sqlite_session_scope` on 127.0.0.1:0, `PHONE = {"width": 390, "height": 844}`, and a console-error check. For AC-3/AC-4, seed a book with a plan and few members, so most cells are short (CARD-158's renders had 10 hints from 4 members on a 150 plan).
- [Open] The 220 px bound in AC-3 is a target, not a measured value. The actions column alone stacks four buttons at 390 px (about 150 px in CARD-158's render). Measure the closed row first. If the actions column alone exceeds 220 px, record the measured figure here and set the bound just above it. Don't restyle the actions in this card.
- [Env] forge 2026.8.17
- [System contract] fresh assembly (system_rules.py --card CARD-175) matches the card section — 52 rules, no change
- [Done] `books_list.html`: when a book has hints, the to-do `<p class="stat-line">` (chips and the visually-hidden "Off plan:" label unchanged) now sits inside `<details class="plan-hints">` with `<summary>N cells off plan</summary>` ("1 cell off plan" for one; no "short"/"over", no `data-off-plan`). "On plan" and "No plan yet" branches untouched. No app.py change, no JS, no page-local style.
- [Done] `admin.css` (tokens only): summary in `--text-sm` / `--color-text-secondary`; `.plan-hints .stat-cell { white-space: nowrap }`; `@supports selector(::details-content) { @media (min-width: 821px) { summary hidden; ::details-content { content-visibility: visible; display: contents } } }`. Without `::details-content` support the plain native disclosure remains — by construction, not tested (only Chromium, which supports it, is exercised).
- [Done] Tests: `tests/test_books_list_plan_stats.py` gained two classes only (TestBooksList_HintsFoldBehindASummary — AC-1; TestBooksList_HintSummaryCountsAndAbsence — AC-2); `git diff` shows 0 removed lines, every pre-existing test unmodified and green (G-1). New `tests/test_books_list_mobile.py` (`@pytest.mark.browser`, fixtures imported from test_puzzle_solver_page per G-5, clean-console check): TestBooksListMobile_RowIsCompactAtPhoneWidth (AC-3, incl. no sideways scroll / G-4 and a per-chip one-line check after opening) and TestBooksListMobile_DesktopShowsEveryHint (AC-4). Ran: plan_stats + mobile + admin_design_tokens + book_detail_page + book_setup_print_mobile + every other test reading /books (property/test_book_workflow, book_guide_page_type, book_pdf_ink_mode, book_proof_pages, book_puzzle_frame, book_trim_persistence, book_workflow_steps): 477 passed. Full suite not run (orchestrator).
- [Measured] Chromium, 390x844, 10-hint book on a 150 plan with 4 members: closed row 175.9 px (actions column alone 148.1 px, so the [Open] 220 px bound stands unchanged); opened row 364.5 px; same row on main 667.5 px. At 1440x900: 333.6 px after vs 337.5 px on main (the ~4 px is column-width redistribution: "hard" now fits the split's first line).
- [Mutation] each mutant applied, targeted tests run, reverted (files byte-compared to backups): M1 hints guard → `stats.plan_present` (on-plan rows get <details>) KILLED by TestBooksList_HintSummaryCountsAndAbsence + TestBooksList_NoHintWhenOnPlan; M2 always "cells" KILLED by TestBooksList_HintSummaryCountsAndAbsence; M3 desktop @supports rule disabled KILLED by TestBooksListMobile_DesktopShowsEveryHint; M4 `white-space: nowrap` removed KILLED by TestBooksListMobile_RowIsCompactAtPhoneWidth (first survived — chips are flex items so getClientRects was 1; the check now counts line boxes of a Range over each chip's text); M5 chips moved outside <details> KILLED by TestBooksList_HintsFoldBehindASummary, TestBooksList_HintSummaryCountsAndAbsence and both browser classes; M6 `<details open>` KILLED by TestBooksListMobile_RowIsCompactAtPhoneWidth + TestBooksList_HintsFoldBehindASummary; M7 G-4 `.table-responsive { position: relative }` removed KILLED by TestBooksListMobile_RowIsCompactAtPhoneWidth; M8 summary hidden at every width KILLED by TestBooksListMobile_RowIsCompactAtPhoneWidth. Every new class failed on at least one mutant.
- [Renders] ~/Documents/nonogram-reviews/CARD-175/: before-books-390.png (main checkout code, read-only via PYTHONPATH, no bytecode written), before-books-1440.png, after-books-390.png (closed), after-books-390-open.png, after-books-1440.png. Seeded SQLite in a temp dir; "Christmas Nonograms for Adults" (150 plan, 2 easy + 2 medium members, 10 hints) plus an on-plan "Winter Animals". 390 shots scroll the table to the Against-plan column. after-books-1440 matches CARD-158's after-books-1440 layout (tier split, then ten stacked chips, no summary, same columns/actions). At 390 the closed summary wraps to two lines ("10 cells off / plan") in the narrow column — owner to judge.
- DESIGN-REGISTER DataTable "plan hints": native <details class="plan-hints"> disclosure on /books — closed by default with a count summary ("N cells off plan", singular "1 cell off plan"), so closed at ≤ 820 px; above 820 px, inside @supports selector(::details-content), the summary is hidden and the list forced visible (always open). Chips keep stat-cell / data-off-plan markup and are white-space: nowrap inside it. On-plan and plan-less rows carry no disclosure.
- No SCOPE+: only the four Touches files changed.
- [Scope] src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/books_list.html, tests/test_books_list_mobile.py, tests/test_books_list_plan_stats.py
- [Build gate] PASSED (full, 616s; 6097 passed, 9 skipped; waited 997s for the full-suite lock)
- [Scope gate] cycle 1: IN_SCOPE — 4 files, all in Touches; no guardrail glob hit
- [Review 1/3] Score: 9.5 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: 52/52 card rules have a verdict line (4 ✓, 48 ⚠ no_eligible_fact, 0 ✗)
- [Review 1/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Adversarial] cycle 1: no Critical/Important findings — nothing to verify (F-001..F-003 Minor, non-gating)
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0038/R7, ADR-0038/R8). ADR-0038/R8: the skeptic reproduced the substance (fixtures pytest.fail on missing Chromium; a live PLAYWRIGHT_BROWSERS_PATH=/nonexistent run gave 6 loud errors naming 'playwright install chromium (ADR-0038/R8)'; 0 skips) but could not match the cited '84 passed, 0 skipped' count to a target; the orchestrator re-ran the reviewer's stated target set (test_books_list_plan_stats + test_books_list_mobile + test_admin_design_tokens + test_book_detail_page) → '84 passed' exactly, so the cited element re-derives
- [Mutation check] reviewer cycle 1: 8 mutants, 7 killed, 1 survivor (content-visibility: visible dropped) argued equivalent in Chromium — display: contents gives ::details-content no box. Implementer's own 8 mutants all killed. Every new test class killed ≥1 mutant
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-1 ✓ demonstrated — TestBooksList_HintsFoldBehindASummary 4/4 PASSED (one <details class=plan-hints>, summary '10 cells off plan', 10 chips inside in hardcoded bucket-then-tier order, none outside); AC-2 ✓ demonstrated — TestBooksList_HintSummaryCountsAndAbsence 4/4 PASSED ('1 cell off plan', '2 cells off plan', on-plan/plan-less rows without <details>); AC-3 ✓ demonstrated — TestBooksListMobile_RowIsCompactAtPhoneWidth 4/4 PASSED in Chromium 390x844, 0 skipped (summary visible/no chip, row ≤ 220 px, scrollWidth ≤ innerWidth, click shows 10 chips, clean console); AC-4 ✓ demonstrated — TestBooksListMobile_DesktopShowsEveryHint 2/2 PASSED at 1440x900; G-1 ✓ demonstrated — test_books_list_plan_stats.py 35 passed, numstat 130/0, app.py not in diff; G-2 ✓ demonstrated — test_book_detail_page + test_admin_design_tokens 43 passed incl. 13 TestBookPages_OfferBothExportFiles, no route/PDF/export file in diff; G-3 ✓ demonstrated — test_admin_design_tokens passed, no <style>/<script>/hex/style= in added src lines; G-4 ✓ demonstrated — admin.css:110 .table-responsive { position: relative; } intact, AC-3 scroll test passed; G-5 ✓ demonstrated — fixtures from test_puzzle_solver_page.py:547-566 pytest.fail on missing Chromium/playwright, no skip; G-6 ✓ demonstrated (pipeline's part: renders produced before merge) — ~/Documents/nonogram-reviews/CARD-175/ holds before-books-390/1440, after-books-390, after-books-390-open, after-books-1440; the owner's own sign-off is a pending human step. No EC section on this card
- [Docs] forge:readme: no structural change in changed dirs (admin/templates, admin/static have no README; tests/README.md is a wave-1 narrative that does not index files) — skipped as current
- [Commit] the passing cycle left no uncommitted code: f6a8a65 (implementation commit, 4 files, +351/−5) is the success commit; nothing under meta/ committed
- [Owner check pending] G-6: owner to eyeball ~/Documents/nonogram-reviews/CARD-175/ before merge; open owner choices raised by review: F-003 (closed summary wraps to two lines at 390 px — 'nowrap' on summary is an option), F-001 (summary uses browser-default focus ring, not --color-focus), F-002 (plural test comments claim per-cell hints it doesn't assert) — all Minor, non-gating
- [Owner decision] 2026-10-04 via coordinator: "Merge, keep it on one line" — F-003 to be fixed: closed plan-hints summary stays on one line at 390 px (nowrap), with a Chromium test shown failing without it; confirmation review follows
- [Fix 1] F-003 (owner, 2026-10-04: "Merge, keep it on one line"): `admin.css` `.plan-hints > summary` gains `white-space: nowrap` (no new tokens or literals); the CSS comment now says the closed summary stays on one line. New test TestBooksListMobile_RowIsCompactAtPhoneWidth::test_the_closed_summary_is_one_line (Chromium, 390x844, same fixtures and clean-console check): a Range over the closed summary's contents yields line boxes at exactly 1 distinct top. Mutation: nowrap removed, so the test FAILED (`AssertionError: 2`; the other 6 in the file passed); reverted, admin.css byte-identical to its backup (cmp). Targeted run (mobile + plan_stats + design_tokens): 48 passed. AC-3 still holds: the row stays ≤ 220 px and there is no sideways scroll. Re-rendered from this branch: ~/Documents/nonogram-reviews/CARD-175/after-books-390.png (closed; the summary reads "▶ 10 cells off plan" on one line), after-books-390-open.png, after-books-1440.png. Measured in Chromium: closed row at 390 px is 168.8 px (was 175.9 px with the two-line summary; actions column 148.1 px); open row is 364.5 px; 1440 row is 333.6 px (both unchanged).
- DESIGN-REGISTER (supersedes the earlier DESIGN-REGISTER line) DataTable "plan hints": native <details class="plan-hints"> disclosure on /books, closed by default with a count summary ("N cells off plan", singular "1 cell off plan") that is white-space: nowrap, so the closed summary is one line at 390 px. Closed at ≤ 820 px; above 820 px, inside @supports selector(::details-content), the summary is hidden and the list forced visible (always open). Chips keep stat-cell / data-off-plan markup and are white-space: nowrap inside it. On-plan and plan-less rows carry no disclosure.
- [Fix 1] declarations: 2 updated (CSS comment; superseding DESIGN-REGISTER line), 0 confirmed, 0 none — pre-gate: named test test_the_closed_summary_is_one_line PASSED
- [Review 2/3] Score: 9.6 — crit: 0, imp: 0 (confirmation mode; F-003 ✓ resolved; new Minor F-004: stale '~176 px' comment in test_books_list_mobile.py:39)
- [Scope gate] cycle 2: IN_SCOPE — fix delta admin.css, test_books_list_mobile.py
- [Review 2/3] Step 8h coverage: 52/52 (4 ✓, 48 ⚠ no_eligible_fact, 0 ✗)
- [Review 2/3] Score: 9.6 ✓ threshold reached + no critical/important
- [Review sync] 2 report(s) → meta/review/
- [8h spot-check] cycle 2: 3/3 sampled holds reproduced (ADR-0038/R1, ADR-0038/R7, ADR-0038/R8)
- [AC/EC check] All criteria/constraints ✓ (evidence, re-check after owner fix): AC-1 ✓ demonstrated — test_books_list_plan_stats.py 35 passed incl. TestBooksList_HintsFoldBehindASummary; AC-2 ✓ demonstrated — TestBooksList_HintSummaryCountsAndAbsence passed; AC-3 ✓ demonstrated — test_books_list_mobile.py 7 passed, 0 skipped (390x844: summary visible, 0 chips, row ≤ 220, scrollWidth ≤ innerWidth, click shows 10, clean console); AC-4 ✓ demonstrated — desktop class passed at 1440x900; G-1 ✓ demonstrated — 35 passed, 130/0 vs merge-base, app.py unchanged; G-2 ✓ demonstrated — book_detail + design_tokens 43 passed, TestBookPages_OfferBothExportFiles 13 passed; G-3 ✓ demonstrated — design tokens test + bounded grep clean; G-4 ✓ demonstrated — admin.css:110 intact, no-sideways-scroll test passed; G-5 ✓ demonstrated — fixtures pytest.fail on missing Chromium/playwright, 0 skips; G-6 ✓ demonstrated — after-books-390.png shows the one-line closed summary, test_the_closed_summary_is_one_line passes (render mtime predates admin.css mtime only because the reviewer restored admin.css from backup after mutants; shasum identical per the reviewer). No EC section
- [Owner check] G-6 accepted by owner 2026-10-04 with the one-line summary change
- [Build gate] PASSED (full, 597s; 6098 passed, 9 skipped; after Fix 1)
- [Mutation check] cycle 2: 3/3 mutants on the summary nowrap killed by test_the_closed_summary_is_one_line
- [Commit] success commit 850e5e4 (owner fix on top of f6a8a65); branch total 4 files, +366/−5 vs b05c443; nothing under meta/ committed
- [Merge gate] rebased onto edd61be; full suite 6167 passed, 9 skipped, exit 0 (600s, under the lock). Merged ecca05d.
- [Design] DESIGN-REGISTER (superseding line) applied to meta/design/components.md under DataTable.
