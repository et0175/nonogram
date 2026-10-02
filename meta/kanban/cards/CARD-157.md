# CARD-157: Read a book's puzzles in one query, not one session per puzzle

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/157-bulk-puzzle-read
**Worktree:** —
**Source:** CARD-122 F-006, CARD-124 follow-up, CARD-126 F-002 (backlog); code re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 30
**Depends on:** CARD-156
**Touches:** src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, tests/test_puzzle_review_bulk_read.py (new)
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-10-02T16:09:16Z
**Closed:** 2026-10-02T17:00:26Z
**Actual:** 0.1d
**Merge commit:** 32e30b9
**Blocked by:** —

## What to implement

In DB mode, `PuzzleReviewService.get_puzzle` (`puzzle_review.py:1096`) opens a new
session for every call. Three book paths call it once per puzzle:

| Path | Where | Cost on a 150-puzzle default-plan book |
|---|---|---|
| Book selection: `_selected_cells` | `app.py:3179` | one session per member + per ticked puzzle, up to ~300 per render |
| A book's status change re-reads its selection | via `BookManager._selection_records` | ~150 per change |
| Arrange/order: `_tier_of` → `_stored_tier` | `book_manager.py:1662`, :1699 | ~150 per arrow click; called from :1264, :1526, :1656, :1737 |

## What to do

1. Add `PuzzleReviewService.get_puzzles(ids) -> Dict[str, record]`: one session,
   one `WHERE id IN (…)` query, returning the same record shape `get_puzzle`
   returns. Ids that don't match or aren't UUIDs are left out of the result
   instead of raising, matching how each caller handles a missing record today.
   Memory mode reads from the dict.
2. Use it in all three paths. `_tier_of` keeps its `known=` behaviour.

**Read this before writing the query.** The obvious one-query fix is wrong:
filtering by `puzzles.book_id` reads the book-membership **mirror**, which
`BookManager` writes only when it was given a puzzle store (CARD-122 Fix 1
notes). The bulk read must go by **id**, taking the ids from the book's own
`puzzle_ids` plus the ticked ones, exactly as each caller does now. ADR-0033/R1:
book assembly may write the mirror, but nothing reads membership from it.

## Acceptance criteria

- **AC-1:** `get_puzzles` returns the same records as calling `get_puzzle` on
  each id, for a mix of present, absent and malformed ids, in both memory and
  DB mode.
  *test: PropertyTest_BulkRead_MatchesPerIdReads (seeded corpus, at least 200 cases)*
- **AC-2:** Rendering book selection, changing a book's status, and moving a
  puzzle on the arrange screen each open a bounded number of sessions that
  doesn't grow with the book's size.
  *test: TestBookPaths_SessionCountDoesNotScaleWithBookSize*
- **AC-3:** A book whose `puzzles.book_id` mirror is stale or empty still shows
  its full membership on all three paths.
  *test: TestBulkRead_IgnoresTheMembershipMirror*

## Guardrails

- G-1: Don't read membership from `puzzles.book_id` (ADR-0033/R1).
- G-2: Screen output on all three paths is unchanged; their existing tests stay
  green without edits.
- G-3: No schema change, no new index unless measured as needed.

## Architecture context

- **ADR:** ADR-0033/R1, ADR-0031 (tiers are read from the row, never re-derived)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## System contract

_Assembled 2026-10-02 by system_rules.py --card CARD-157 (scope: Touches globs); 47 mandatory rules._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as package data instead, and doing so is not a dependency change. (test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it may import the orchestrator but no capability module may import it or cli.py. (test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer. (review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by more than 2x from the source's INK BOUNDING BOX ratio — not from its as-decoded file ratio — is refused rather than cropped. The bounding box is computed and judged before any crop is applied, so a refused request is still refused before any cropping runs. (test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the other side from the source's own aspect ratio, clamped to MIN_SIZE at the bottom only and never at the top. A source whose ratio exceeds N/5 is refused with a message naming the smallest N that would accommodate it, never silently clamped. (test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniqueness from the fact that a grid was repaired. (test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit on one lineage, is a named constant beside it and is never a second bound; exhausting the counter raises GenerationAbandoned whichever kind of attempt came last. (test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that set holds no filled/empty pair), so the filled count is preserved and no cell outside the region changes. (test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws nothing from the injected Random or from host state, so a seed replays the same repair lineage everywhere. (review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DENSITY and MAX_DENSITY are the only statement of that range. (test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density grounds, and no module's documentation claims that one does. (test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the share of cells settled at that rung; each rung is the fixed point of its technique, so the rung of a cell is a function of the clue set alone; a deeper solve of the same extent scores strictly higher, and the line-solvable corpus populates every score band. (test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the tier is derived from that same list — no second derivation, no second solver entry. The ladder's fixed points are phases of that one monotone forward solve — each continues from the board the previous left, the board is never reset and the search is never re-entered — so running a cheaper technique to exhaustion before a dearer one is not re-solving. (test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of the solve and branch_nodes, identical on every machine. (test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them, intersected), and are re-derived natively inside the solver package; the solver never imports clues.py or any other capability module for the purpose (ADR-0007). (test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all (empty or None per-cell tags, an all-zero per-rung histogram, an empty rung list). For uniquely-solvable clue sets, rung attribution is invariant under transposition and under line-visit order — a clue set and its transpose yield the same per-rung cell counts, the same rung list and the same score — and a change to the solver's iteration order may change how a fixed point is reached but never which cells belong to which rung. The invariance holds trivially for the non-unique ones too, since both orientations report nothing. (test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0031/R1 — Tier has exactly three members — easy, medium, hard — and every one has a score band. classify takes the score alone; no module derives a tier from branch_nodes. (test: TestTiers_ThreeBandsAndNoFourthTier)
- ADR-0031/R2 — A solve that branched is reported as the `guess` strategy (solver.STRATEGY_GUESS) in FR-029's strategies list, never as a tier. (test: TestTiers_BranchingIsAStrategyNotATier)
- ADR-0031/R3 — A stored difficulty_tier of "guess" reads back as Tier.HARD and is never rewritten by this decision; no migration runs and no production database is touched. (test: TestTiers_LegacyGuessRowReadsAsHard)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid it was handed and refuses, with NotUniquelySolvable, any grid whose clues do not have exactly one solution — including one whose solve timed out or could not be attempted. No caller's assurance substitutes for that check, and no admin path writes a puzzle row by another route. (test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never satisfies a quality minimum, is never the left operand of an order comparison, and renders as "N/A" wherever a score would be shown — templates, API responses and the book PDF alike, the book omitting the /100 denominator that a non-number does not take. recognizability carries the same rule in its own vocabulary. (test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id). (review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percentage points of that cell's planned share. (test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's socket-reach half is discharged by more than a threshold visible only in requirements.yml. (test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form request target whose authority is not a loopback name (NFR-004). Restates NFR-004 as a gate-enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's browser-mediated-reach half is discharged too, not only its socket-reach half (CON-009): binding to 127.0.0.1 alone does not stop this, since a browser sets Host from the request's target url, not from the page's origin. (test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This supersedes the 10..50 range FR-001 carried; FR-001 is marked status: superseded, superseded_by: FR-019, and FR-019 restates the behaviour over the narrowed range. (test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an explanatory error rather than converted (FR-021). The centred crop of FR-020 retains exactly min(r_src, r_tgt) / max(r_src, r_tgt) of the source with r = width/height, so this is exactly the rule "never silently discard more than half the user's picture". Retaining exactly 50% (a ratio difference of exactly 2x) is ACCEPTED — the boundary is inclusive. (test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a parameter: no supported call into nonogram.admin.app widens it, and no module under src/nonogram/admin/ names another bind address in code. Restates NFR-003 for the second inbound HTTP surface, which CON-009 does not reach. (test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not pass the door in force. With it unset (the default), it refuses any request whose Host header does not name this machine — a bare authority, no userinfo, path, query or fragment, a port absent or all digits, and a host component in {localhost, 127.0.0.1, ::1} — and refuses a request carrying no Host header at all. With it set, it refuses any request whose Host is not exactly that hostname (a loopback Host included), any request not carrying the configured credential, and any request the browser marks as started by another site (a Sec-Fetch-Site outside {same-origin, none}, or an Origin whose host is not that hostname). The wrong-host refusal is indistinguishable from "no such page" in both modes, so it tells a scanner nothing. Holds however the socket was bound, including when the bind was widened by an option outside this package's control. (test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured maximum bound (NFR-002). (test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit move inside that level (FR-041). (test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; pairing never changes the book order (FR-040). (test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 once it holds one longer than 20; no answer-key page holds answers of two levels (FR-042). (test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; ADR-0035 clarification). (test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the interior's; the cover is produced as a separate file (FR-043). (test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Worktree notes

- [Origin] Three cards each left their own N+1 on the backlog. They share one
  missing method. Cut on 2026-10-02.
- [Order] Depends on CARD-156 so the DB-mode tests here run against a fixture
  that doesn't drop tables underneath them.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +47 (card had no section) / −0
- [Impl] `PuzzleReviewService.get_puzzles(ids)` added: memory mode reads the dict (same
  live objects get_puzzle returns); DB mode is one session, one `WHERE id IN (...)`,
  none at all when no id parses. Keyed by the id as given; absent, non-UUID strings,
  unhashable values and non-str/non-UUID values are left out (exactly the ids
  get_puzzle answers None for or that callers caught ValueError/TypeError on). One
  fresh dict per input id, so two spellings of one row never share a record.
- [Impl] Callers switched: app.py `_selected_cells`; BookManager `_selection_records`
  (order + repeats preserved; one warning naming every unmatched id, replacing the
  per-malformed-id warning); `_tier_of` → new `_stored_tiers` (bulk; `known=`
  carried and never re-read). Membership ids always come from `book.puzzle_ids`
  (+ ticks); nothing reads `puzzles.book_id` (G-1). No schema/migration/index (G-3).
- [Impl] The arrange route re-renders after a move (no redirect), and its render loop
  did `get_puzzle` + `get_puzzle_title` per row (2 sessions/row). Both replaced in
  app.py: one `get_puzzles` over the listed ids and the titles from one `get_book`
  read (same dict `get_puzzle_title` reads). Needed for AC-2 on "moving a puzzle on
  the arrange screen"; same file, in scope.
- [Behaviour] A malformed ticked id on book selection used to raise ValueError in DB
  mode (500); it now counts towards no cell, as an absent id always did.
- [Measured] Sessions opened through the store + book manager (real Postgres,
  CountingFactory around the services' session_scope), book of N members + N ticks:
  | path | before N=6 | before N=60 | after N=6 | after N=60 |
  |---|---|---|---|---|
  | GET select-puzzles | 15 | 123 | 4 | 4 |
  | POST status (gate) | 8 | 62 | 3 | 3 |
  | POST arrange move_down (+render) | 29 | 245 | 9 | 9 |
- [Follow-up] `_book_member_records` (books list, app.py) still reads one session per
  member per book — not one of this card's three paths; left for the backlog.
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/puzzle_review.py, tests/test_puzzle_review_bulk_read.py
- [Build gate] PASSED (full, 398s) — 5803 passed, 9 skipped, 2 failed; the 2 failures are exactly the known main baseline (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders)
- [Scope gate] in_scope — 4/4 changed files inside Touches; comp spread none (all COMP-009); siblings CARD-158/159 overlap 1/5 of their Touches (app.py) — below the poach threshold
- [Adversarial] F-001 CONFIRMED — skeptic reproduced: arrange render's custom_title read (app.py:4126) is new code; no test asserts a custom title on the arrange page; mutant custom_title=None passes every arrange-related test file (two locked runs, rc=0)
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1
- [Review 1/3] Step 8h coverage: 47/47 card rules have a verdict line (14 holds, 33 unchecked no_eligible_fact, 0 violated)
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Review sync] 1 report(s) → meta/review/ (20261002T163626Z-CARD-157-cycle1.yml)
- [Fix 1] FIXED F-001 (test-only: TestBookArrange_ShowsTheCustomTitleOfEachRow, memory+db; kills M7 in both modes), FIXED F-002 (one DEBUG line naming unmatched ids in _stored_tiers; both branch directions tested), FIXED F-003 (doc-only: _selection_records docstring records the widened WARNING trigger), SKIPPED F-004 (out of scope → backlog). Pre-gate: named tests 6 passed, 0 skipped
- [Fix 1] declarations: 0 updated, 0 confirmed, 1 none (F-001); docs re-derived: BookManager._stored_tiers (F-002), BookManager._selection_records (F-003)
- [Build gate] PASSED (full, 378s) — 5809 passed, 9 skipped, 2 failed = the known main baseline
- [Scope gate] cycle 2: in_scope — fix delta book_manager.py + tests/test_puzzle_review_bulk_read.py, both inside Touches
- [Review 2/3] Score: 9.5 — crit: 0, imp: 0 (confirmation mode; F-001/F-002/F-003 ✓ resolved by re-derivation, M7 re-killed memory+db)
- [Review 2/3] Step 8h coverage: 47/47 card rules have a verdict line, all fresh (14 holds, 33 unchecked no_eligible_fact, 0 violated)
- [Review 2/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Mutation] 8f certifying cycle 2: 7 mutants, 7 killed, 0 survived (M7 arrange custom_title=None memory+db, M9 F-002 guard negated, M10 debug names matched ids, M11 malformed id→nil UUID, M12 memory unhashable re-raise, M13 no-row id→HARD, M14 gate drops repeats); cycle 1: 8 mutants, 7 killed, M7 survived → F-001, since fixed
- [Review sync] 2 report(s) → meta/review/ (cycle1, 20261002T165334Z-CARD-157-cycle2.yml)
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0031/R3) — named tests re-run green, diff import/migration scans clean; ADR-0031/R3 skeptic notes the verdict's 'delta adds only a DEBUG line' undersells the bulk _stored_tiers change, conclusion stands (legacy 'guess' row orders HARD on the bulk path, unrewritten)
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — test_PropertyTest_BulkRead_MatchesPerIdReads[memory] and [db] PASSED (db ran, not skipped); 240 seeded cases (random.Random(157)), cases >= 200 asserted in-test, <= 1 session per call in DB mode
  AC-2 ✓ demonstrated — TestBookPaths_SessionCountDoesNotScaleWithBookSize::test_the_three_paths_cost_the_same_at_both_sizes PASSED on Postgres: 6-puzzle {select 4, status 3, arrange 9} = 60-puzzle {select 4, status 3, arrange 9} (before: 15/123, 8/62, 29/245)
  AC-3 ✓ demonstrated — TestBulkRead_IgnoresTheMembershipMirror 4 tests x [memory, db] = 8 PASSED; mirror cleared on 2 members and pointed at a decoy book on 2, asserted wrong before driving the paths
  G-1 ✓ demonstrated — src diff book_id grep: 6 hits = 4 comments, 1 get_book(book_id), 1 removed line; only added predicate Puzzle.id.in_ (puzzle_review.py:1162); AC-3 green both modes (bounded to this diff)
  G-2 ✓ demonstrated — 7 existing path test files 286 passed, 0 skipped; git diff main --stat -- tests lists only the new file
  G-3 ✓ demonstrated — changed-file list has no alembic/, src/nonogram/db/, migration or model file
- [Docs] skipped — src/nonogram/admin/ has no README (per-directory README convention is an open owner decision, backlog); tests/README.md names no book test file, so the new test file changes nothing it states
- [Commit] f0561cb on card/157-bulk-puzzle-read (cycle-1 fixes; implementation fd3a82f) — explicit pathspecs, nothing under meta/; card diff vs main: app.py +15/-10, book_manager.py +48/-33, puzzle_review.py +54/-0, tests/test_puzzle_review_bulk_read.py +640 (new)
- [Merged] 2026-10-02 — 32e30b9 into main (--no-ff). Merge gate: rebase was a no-op (main still at 3c3c3ac = branch base), so the merged tree is the one that passed gate 2 (378s; only the 2 baseline failures); not re-run — the wave-30 smoke test runs the full suite on main at wave end. Deferral scan: 0 hits. No trace write-back: no FR on the card. F-004 captured to backlog.
