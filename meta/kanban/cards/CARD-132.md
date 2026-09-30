# CARD-132: Books list — actual vs planned count and tier split, exact short/over hints, sort by completeness

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/132-books-list-plan-stats
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-16 (FR-039)
**Idea:** —
**Wave:** 26
**Depends on:** CARD-123, CARD-124, CARD-130
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/books_list.html, tests/test_books_list_plan_stats.py
**Review score:** 8.5 (2 cycles)
**Started:** 2026-09-30T07:36:59Z
**Closed:** 2026-09-30T11:35:00Z
**Actual:** 0.5d
**Merge commit:** 32fcc52
**Blocked by:** —

## What to implement

1. **Per row on `/books`:**
   - the actual count against the planned count ("132 / 150");
   - the actual-against-planned split per tier ("easy 50 / 60 · medium 60 / 60 · hard 22 / 30");
   - a status hint when any longest-side × tier cell is short of or over its plan, using
     **exact counts** per ADR-0035 (for example "26–30 × hard: short 7", "over 1"). This
     is a to-do list, not the gate's ±3 pp.
   A plan-less book shows its count alone.
2. **Sort by completeness:** actual / planned count, most complete first. How plan-less
   books sort is not stated. Put them last and record that.
3. The counts come from CARD-119's `selection_cells` / `planned_cells`, the one
   bucketing function. The page reads data only.

## Acceptance criteria

- **AC-230** — given a book with a plan of 150 holding 132 puzzles, when the books list is rendered, then its row shows 132 / 150.
  *test:* `TestBooksList_ShowsActualVsPlannedCount`
- **AC-231** — given a book planned at 60/60/30 holding 50 easy, 60 medium and 22 hard puzzles, when the books list is rendered, then its row shows easy 50 / 60 · medium 60 / 60 · hard 22 / 30.
  *test:* `TestBooksList_ShowsPerTierActualVsPlan`
- **AC-232** — given a book whose 26-30 x hard bucket holds 5 against a plan of 12, when the books list is rendered, then its row carries a short-bucket hint.
  *test:* `TestBooksList_HintsShortBucket`
- **AC-233** — given a book whose every bucket holds exactly its planned count, when the books list is rendered, then its row carries no hint.
  *test:* `TestBooksList_NoHintWhenOnPlan`
- **AC-234** — given three books at 20 / 100, 150 / 150 and 132 / 150, when the list is sorted by completeness, then the order is 150 / 150, 132 / 150, 20 / 100.
  *test:* `TestBooksList_SortsByCompleteness`
- **AC-235** — given a book created before distribution plans existed, with no stored plan and 40 puzzles, when the books list is rendered, then its row shows 40 with no planned figure.
  *test:* `TestBooksList_BookWithoutPlanShowsCountOnly`

## Guardrails

- G-1: Reads only. No schema change and no writes (Increment 16 "COMP-010 (reads only)"). Do not edit `src/nonogram/db/**`, `migrations/**` or `src/nonogram/admin/book_manager.py` (the latter is owned by CARD-131 this wave).
- G-2: One bucketing function. The hint uses `book_plan.bucket_of` / `selection_cells` (EC-024).
- G-3: The hint uses exact counts, and the gate's ±3 pp is not reused here (ADR-0035 (d)).
- G-4: Do not edit `src/nonogram/admin/book_pdf_generator.py`, which is owned by CARD-128 this wave, or `src/nonogram/admin/templates/_confirm_membership_change.html` / `book_detail.html`, which are owned by CARD-131 this wave.

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

- **FR:** FR-039
- **NFR:** —
- **ADR:** ADR-0035
- **Components:** COMP-009, COMP-010 (reads only)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** DataTable (reuse — new columns, sortable by completeness), ProgressBar (reuse — actual/planned), TierChip (reuse — per-tier split), StatusChip or Flash (inline) for the short/over hint (text, not colour alone)
- **Screens:** /books
- **Standards:** forge:engineering-standards §11

## Worktree notes

- [Env] forge 2026.8.17
- [Guardrail provenance] G-1 and G-4 exclude files because CARD-131 and CARD-128 "owned" them
  "this wave". Both have since merged (293f921, 557c7ac), so the ownership reason has lapsed —
  but the exclusions stand as scope boundaries: this card is reads-only over the books list and
  has no business in `book_manager.py`, `book_pdf_generator.py`, `book_detail.html` or
  `_confirm_membership_change.html` regardless of who last held them.
- [Seams already in place] `book_plan.bucket_of` (line 128), `planned_cells` (348) and
  `selection_cells` (353) all exist from CARD-119, so G-2's "one bucketing function" is a reuse
  requirement, not something to build. The `/books` route is `app.py:2127`, the template has no
  planned/completeness markup at all today.

### What was built

`/books` now renders every book against its distribution plan. Per row:

* the **count against the plan** — "132 / 150" — with a ProgressBar beneath it
  whose accessible name repeats both numbers in words, so the figure is never
  carried by a bar length alone;
* the **per-tier split**, "easy 50 / 60 · medium 60 / 60 · hard 22 / 30", each
  tier named by the existing TierChip macro (`_tier.html`);
* the **to-do list**: one chip per longest-side × tier cell that is off its
  plan, with the **exact** count it is off by ("26-30 × hard: short 7",
  "16-20 × hard: over 2"). A book on its plan says "On plan" in words.
* a plan-less book shows its count alone and points at Print setup
  (ADR-0035 (c)'s remedy).

The list is **sorted by completeness** (actual / planned, most complete first);
the order it had before — newest first — stays reachable as `?sort=created`,
and both column heads are real `<a>` links, which is the DataTable pattern.

Guardrails held: reads only (`src/nonogram/db/**`, `migrations/**`,
`book_manager.py` untouched — G-1); every count comes from `book_plan`'s
`planned_cells` / `selection_cells` and the one `bucket_of` (G-2) — the route
divides two numbers and words a direction, and decides no cell membership;
the hints are exact counts, never the gate's ±3 pp (G-3); `book_pdf_generator.py`,
`_confirm_membership_change.html` and `book_detail.html` untouched (G-4).

### AC → test

All in `tests/test_books_list_plan_stats.py`.

| AC | test |
| --- | --- |
| AC-230 | `TestBooksList_ShowsActualVsPlannedCount` |
| AC-231 | `TestBooksList_ShowsPerTierActualVsPlan` |
| AC-232 | `TestBooksList_HintsShortBucket` |
| AC-233 | `TestBooksList_NoHintWhenOnPlan` |
| AC-234 | `TestBooksList_SortsByCompleteness` |
| AC-235 | `TestBooksList_BookWithoutPlanShowsCountOnly` |

Cross-checks beside them: `TestBooksList_HintsOverBucket` (CK-1, decision 2),
`TestBooksList_PlanlessBookSortsLast` (CK-2, decision 1),
`TestBooksList_SortsBackToNewestFirst` (CK-3) and
`test_PropertyTest_BooksList_HintsAreEveryOffPlanCellExactly` (CK-4) — a
seeded 24-book corpus (`random.Random`, no `hypothesis`, minimum case count
asserted in the test) whose expected hints are bucketed by the test file's
**own** copy of the longest-side bounds, with sizes drawn from anywhere inside
each range rather than pinned to its top. So "the page uses the one bucketing
function" is checked by a second opinion that has to meet it on a 17 × 12, not
only on a 20 × 20.

All 17 tests **execute** in in-memory mode — the route reads a stored plan and
a stored record per member, and neither read needs a database, so none of them
can skip for want of `nonogram_test`.

### The decisions the card left open

_Two when the card was built; a third was ruled on in review cycle 1 (F-005)._

1. **A plan-less book sorts last.** FR-039 does not say. It has no
   completeness at all — there is no denominator — so it cannot be placed
   among the books that have one, and it goes after every planned book
   *including one at 0 / 150*: the list is a to-do list against the plan, and
   a book with no plan yet is not further along than a book that has one and
   has not started filling it. Chosen, not fallen out of the sort — the key is
   `(planned is None, -Fraction(actual, planned))`, so the tail is explicit
   and ties keep `get_all_books`' own order (newest first, stable sort).
   Pinned by `TestBooksList_PlanlessBookSortsLast`.
2. **"short" and "over" are one hint list, not two.** AC-232 pins only short.
   A cell is off its plan in exactly one direction, both directions are work
   the owner has to do before the book can leave draft, and one list keeps a
   table row readable; splitting them would put the same cell's two possible
   states in two places. The direction is a **word** in the chip, so the hint
   reads without the tint behind it (§11). Pinned by
   `TestBooksList_HintsOverBucket`, both singly and mixed.

3. **An over-plan book ties with an on-plan one — the sort ratio is clamped
   at 1.** The owner's ruling (2026-09-30), after review cycle 1 (F-005) found
   the ratio uncapped: 160 / 150 is 16/15 and was sorting ahead of 150 / 150
   and ahead of everything else. `/books` is a **to-do list**, and a book ten
   over its plan still has work to do — decide which ten to drop — so it must
   not outrank a book that is exactly right. The key is therefore
   `-min(Fraction(1), Fraction(actual, planned))`, which makes the two one tie,
   broken by `get_all_books`' own newest-first order through the same stable
   sort the plan-less tail relies on. The clamp is for the **order only**: the
   row still reads "160 / 150" and still carries its "over 10" hint, and
   `percent` / `complete` are untouched — they cap on their own account, so
   both rows draw a full bar as they did. AC-234 stops at 150 / 150 and does
   not cover this, so it is pinned by
   `TestBooksList_OverPlanBookTiesWithOnPlanBook`.

Two smaller calls, recorded so a later reader need not guess:

* The planned total is the plan's own `count`, not the matrix's sum — the same
  denominator the readiness gate divides by (ADR-0035 (b), `off_plan_cells`).
  The two differ only for a hand-edited matrix that disagrees with its general
  plan, and Print setup already warns about that.
* The actual count is the number of members that fall in a plan cell
  (`sum(selection_cells(...))`), so the headline figure is always the sum of
  its own per-tier split and the row cannot contradict itself. A member id no
  row matches counts towards no cell — the verdict `selection_cells` and
  `BookManager._selection_records` already make.

### SCOPE+

* `SCOPE+ src/nonogram/admin/static/admin.css` — the hint chip needed an
  off-plan state and the bar needed a table-row height. Two lines, one of them
  widening the existing `.stat-cell[data-over="true"]` selector to cover
  `[data-off-plan="true"]` with the same declarations, plus `.plan-progress`.
  Tokens only — no new colour, px or font literal; `tests/test_admin_design_tokens.py`
  stays green. `meta/design/tokens.css` and its served mirror are untouched.

### Suite

`5352 passed, 2 failed, 7 skipped` — the two failures are the known stale
heading assertions from the 2026-09-14 rename
(`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`
and `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders`),
untouched by this card. 17 tests added; nothing else moved.

### Cycle 1 review (2026-09-30)

- [Review 1/3] **8.0** · risk LOW · lane FAST ·
  `meta/review/20260930T083128Z-CARD-132-cycle1.yml` · 0 critical, 0 important, 4 minor + 2
  out-of-scope. Meets `min_score: 8`. Mutation ran (not deferred): **6 of 6 killed**, and two of
  them — the plan-less tail and the per-tier figures — were killed by a single test each, so the
  tests discriminate individually rather than only en masse. Restore proven by SHA-256 on both
  mutated files. Nothing the orchestrator pre-verified was wrong.
- **G-2 ✓ mechanically verified.** No second bucketing rule in production code: no bound, no
  range check, no `max(w,h)`, no label string encoding a bound, no size sort key. All twelve cell
  keys come from `selection_cells`/`planned_cells`; the route iterates `PLAN_BUCKETS`/`PLAN_TIERS`
  and takes labels from `bucket.label`. The template encodes nothing — the hint is built in
  Python and passed whole.
- **G-3 ✓, and the second-definition risk is provably safe-directional.** The card does create a
  second textual definition of "off plan" (exact, in the adapter) beside `book_manager`'s
  tolerance-based one — G-3 requires exactly that. The list's off-set is `|d| > 0`; the gate's is
  `|d|·100 > 3·plan.count`; `plan.count >= 1` by INV-005. So every gate-offending cell is also a
  list hint, and therefore **"On plan" implies the gate passes** — the dangerous direction cannot
  occur. The reverse (gate passes, hints still shown) is the intended to-do-list semantics.
- One row-internal inconsistency the card chose deliberately: the headline denominator is
  `plan.count` (the gate's, per ADR-0035 (b)) while the per-tier denominators are matrix column
  sums, so a hand-edited matrix that disagrees with its split can read "145 / 150" *and* "On
  plan". Print setup already warns about that disagreement.
- Sort verified: no `ZeroDivisionError` reachable (`DistributionPlan.__post_init__` refuses
  `count < 1` and the key guards anyway), stable so ties and the plan-less tail keep newest-first,
  and `Fraction` is unnecessary but legal — stdlib, so ADR-0006/R1 is untouched.
- Accessibility ✓ in substance: the direction is a word in every state ("short 7", "over 2",
  "On plan", "No plan yet"), the figure is text before the bar and repeated in the bar's
  `aria-label`, and the new sortable heads are real `<a>` links that work with JavaScript off —
  better than the house pattern in `_puzzle_table.html`, which uses `href="#"` plus JS.
  `tests/test_admin_design_tokens.py`: 6 passed.
- **F-005 (minor, and the one worth a decision):** the sort ratio is uncapped, so **160 / 150
  sorts ahead of 150 / 150** — and ahead of everything. Both rows draw a full bar, so only the
  hint text distinguishes an over-plan book from an on-plan one. For a to-do list the book ten
  over its plan arguably has *more* outstanding work, not less. AC-234 pins only the three
  under-plan cases; no test covers an over-plan book's position; and the card records two open
  decisions but not this third one — which matters because "the open decisions are written down"
  is this card's own standard.
- F-001 (minor) N+1: `/books` goes from one query to `1 + B + Σ|members|` store reads. Graded low
  — no NFR, single-user local panel, same pattern as the existing gate.
- F-002/F-003 (minor, one root cause) `meta/design/components.md` is now stale for the two reused
  components: it still says ProgressBar is "Used by: batch status", and that DataTable sortable
  heads carry `sort_by` where these carry `sort`. Also `data-status="generating"` is borrowed for
  a partially-filled book — renders correctly today by falling through to the accent default, but
  a future rule written for real batch "generating" would reach this bar.
- F-004 (minor) no `aria-sort` on the `<th>` and the `↓` is unlabelled link text; systemic (the
  puzzle table has the same gap), so a nit rather than a regression here.
- **[Model defect, second sighting] ADR-0006/R1's declared check
  `TestDependencyBaseline_IsExactlyPillowAndNumpy` does not exist** — it appears only as a comment
  in `tests/test_export_pdf.py` and in the ADR's own `check:` field. CARD-148's cycle-2 review
  flagged the same thing independently. The ADR claims a mechanical check it does not have; route
  to the architect station to write the test or re-type the check as `review-lens`.
- **Outstanding and not substitutable: nobody has looked at `/books` in a browser.**
  `review.visual: off` (no `make run` target), so no screenshot, runtime log, axe scan or baseline
  diff exists for this card. The static checks above are the only mechanical guard it got.
- [Review sync] 1 report → meta/review/

### [Fix 1] — review cycle 1 (8.0, no Critical, no Important) → f94f29e

Suite after the fix: **5355 passed, 2 failed, 7 skipped** — the same two known
stale heading assertions, untouched. 3 tests added (20 in the card's file now),
and all 3 **execute** in in-memory mode; nothing else moved.

* **F-005 fixed** — the completeness sort ratio is clamped at 1, so an over-plan
  book ties with an on-plan one instead of outranking it. Recorded as decision 3
  above (the owner's ruling of 2026-09-30) and in `_books_by_completeness`'s
  docstring. Displayed figures, `percent` and `complete` unchanged. Pinned by
  `TestBooksList_OverPlanBookTiesWithOnPlanBook` (3 cases: the over-plan book
  does not lead an on-plan one made after it; the tie flips with creation order
  rather than with the excess, so it is a tie and not a reversed ranking; and
  the row still reads "160 / 150" with its "over 10" hint). Verified to fail on
  the pre-fix uncapped key.
* **F-003 fixed** — the plan bar is `data-status="partial"`, not the batch
  lifecycle's `generating`: it shows a fill level, not a job in flight, so a
  future rule written for real batch behaviour cannot reach it. Rendering is
  identical — neither word has a `.progress-bar[data-status=…]` rule, so both
  fall through to the accent default.
* **F-004 fixed** — both heads this card added carry `aria-sort` on the `<th>`
  ("descending" when current, "none" otherwise — the list offers no ascending
  order, so none is invented), the ↓ is `aria-hidden`, and the direction repeats
  in `visually-hidden` text (the Bootstrap 5.3 utility this template already
  uses). `_puzzle_table.html` deliberately untouched: the same gap there is
  systemic and belongs in its own card.
* **F-006 fixed** — `.table .stat-line { margin-bottom: 0; }` removed from
  admin.css. Confirmed dead first: the four `.stat-line` call sites are
  books_list.html:73 / :80, both already `mb-0`, and book_select_puzzles.html:53
  / :160, neither inside a `.table`. The two `mb-0` classes stay; this card
  added the rule, so the rule is what goes.
* **F-002 fixed** — `meta/design/components.md` reconciled (see SCOPE+ below).
* **F-001 left open** — the N+1 on `/books`. Graded low by the reviewer and
  accepted: no NFR pins admin page latency, the audience is one Puzzle Creator
  at a desk, and the same per-member read pattern is already what the readiness
  gate and the selection screen do. Revisit when a shelf grows past a handful of
  full books, or when CARD-131 releases `book_manager.py` and one public
  selection-records accessor can serve the gate, the selection screen and this
  list at once. On the backlog.
* **F-007 left open** — the missing warning line for an unresolvable member id.
  Out of scope: the remedy is the shared accessor above, so a mirrored log line
  now would be duplicated logic to delete later.
* **ADR-0006/R1's dead `check:` ref** — not touched. A model defect for the
  architect station, not a code fix.

Guardrails held again: reads only, no `src/nonogram/db/**`, `migrations/**` or
`book_manager.py` edit (G-1); every count still comes from `planned_cells` /
`selection_cells` and the one `bucket_of`, and the clamp introduces no bound,
range check, `max(w,h)` or bucket label — it divides the two numbers the route
already had (G-2), and the test file's own `BUCKET_BOUNDS` stays independent;
the hints are still exact counts and the gate's ±3 pp is not referenced, so the
list's off-plan set remains a strict superset of the gate's and "On plan" still
implies the gate passes (G-3); `book_pdf_generator.py`,
`_confirm_membership_change.html` and `book_detail.html` untouched (G-4). No new
colour, px or font literal — this fix only deletes one CSS declaration;
`tests/test_admin_design_tokens.py` green, `meta/design/tokens.css` and its
served mirror untouched. No existing test weakened, retargeted or deleted, and
CK-4's asserted floors (`CORPUS_CASES = 24`, `seen_short >= 20`,
`seen_over >= 20`) are unchanged.

#### SCOPE+ (Fix 1)

* `SCOPE+ meta/design/components.md` — review cycle 1 F-002/F-003 (root cause
  RC-1): the inventory was stale **because of this card**, which made the books
  list a second ProgressBar consumer and introduced a second sort-parameter
  name. ProgressBar's "Used by" now names the books list and its
  `.plan-progress` variant with that variant's own states (partial / complete,
  fill levels rather than job lifecycle). DataTable now says honestly that two
  query-parameter names are in use — `sort_by` in `_puzzle_table.html`, the
  older one, and `sort` on `/books` — names `sort` as the convention going
  forward, and notes that the puzzle table keeps `sort_by` until a
  design-system card renames it. Documentation only; no token, colour, px or
  font literal, and `meta/design/tokens.css` is untouched.

### Cycle 2 (2026-09-30) — on the fix round

- [Review 2/3] **8.5** (cycle 1: 8.0) · risk LOW · lane FAST ·
  `meta/review/20260930T091551Z-CARD-132-cycle2.yml` · 0 critical, 0 important, 2 minor.
  Certification ran, not deferred. **Ready to merge.**
- **The clamp is right, and mutation-proven from three directions.** Rendered a six-book shelf
  (300/150, 160/150, 150/150, 149/150, 0/150, plan-less) created in reverse order: the page
  reads 150/150, 160/150, 300/150, 149/150, 0/150, plan-less. It is a genuine **tie** — the
  300-over book sits behind the 160-over one purely because it is older, so the tie-break is
  creation order and not the size of the excess, which is exactly what the owner ruled. Nothing
  the old key got right is now wrong: 150/150 keys −1 and 149/150 keys −149/150, so exactly-at-
  plan still leads a book fractionally under, and the plan-less tail is still decided by the
  first tuple element before the ratio is looked at. Three mutants: the clamp removed (killed),
  over-plan penalised strictly below instead of tied (killed — the tests discriminate a tie from
  "merely sorts lower"), and the tie ordered by size of excess (killed).
- `data-status="partial"` renders identically — verified by exhaustive grep, not by inspection
  of one file: every `[data-status]` rule in the served CSS (`admin.css` only), `tokens.css` and
  its mirror (none), and Bootstrap 5.3 (namespaces everything `data-bs-*`, ships no
  `[data-status]`). The `generating` rule that did exist needed class `badge` and could never
  have reached this element.
- The `aria-sort` macro is correct, not merely present: on the `<th>`, valid tokens, the
  non-current column claims no direction it lacks, values swap under `?sort=created`, no
  escaping artifact, and blast radius contained (both macros local to `books_list.html`; the
  other seven heads byte-identical).
- The deleted CSS rule was genuinely dead — all five `.stat-line` uses in the repo checked, not
  two files.
- No test was weakened: the test file is **+59/−0** in the fix commit, and all four CK-4 floors
  (24 / 20 / 20 / the independent `BUCKET_BOUNDS` oracle) are untouched. 20 tests, 20 execute.
- Minor, both left open for the owner's call:
  - **F-008** neither the `aria-sort` values nor `partial` has an assertion — **both mutants
    SURVIVED**. Two of the fix round's three production changes are untested in a file whose 20
    tests pin every other decision by name. The escaping mechanism is the fragile part: a future
    `|e`, `|string`, or moving the attribute into Python would drop it silently with no red test.
    Two lines close it.
  - **F-009** `meta/design/components.md:47` now *over-claims*: it describes the `aria-sort`
    treatment as the DataTable spec, true only for `/books` — `_puzzle_table.html` still has
    `href="#"` + JS, no `aria-sort`, a bare arrow. The inverse of cycle 1's RC-1: the inventory
    is now ahead of the code and reads as done. One clause fixes it.
- **[The orchestrator's brief was wrong, and the reviewer caught it]** I told cycle 2 the branch
  was based on current main. It was not: the merge base was a008fc0 and main had advanced three
  commits (two of them mine, written after the brief). `git diff main..HEAD` therefore counted
  CARD-149's card and the new doc as deletions this card never made. Verified independently —
  `comm -12` over the two file lists is empty, so there was no code risk, and the reviewer
  reviewed the correct three-dot diff. Rebased since: the branch is now c13e430 + 0876738 on
  main at 1b3212e, and the two-dot diff reads honestly at 5 files, +932/−17.
- [Build gate] PASSED on the REBASED commits: **5364 tests, 5355 passed, 2 failed, 7 skipped** —
  the two long-known stale-heading failures.
- [Review sync] 2 report(s) → meta/review/
- **Still outstanding: nobody has looked at `/books` in a browser.** The reviewer's parting note
  is worth acting on — look at an over-plan row specifically. It draws a full green "complete"
  bar and now sits at the top tied with an exact book; only the words ("160 / 150", "over 10")
  distinguish the two. The owner's ruling settled the *order*, not that appearance.

### Orchestrator gates (2026-09-30)

- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/templates/books_list.html,
  src/nonogram/admin/static/admin.css (SCOPE+), tests/test_books_list_plan_stats.py — one
  commit, 84728d0.
- [Build gate] PASSED, re-run by the orchestrator: 5361 tests, 5352 passed, 2 failed, 7
  skipped. The two failures are the known stale-heading assertions, untouched. 5361 = the
  5344 baseline + this card's 17.
- [Guard] G-1/G-4 verified mechanically: the diff names no `src/nonogram/db/**`, no
  `migrations/**`, and neither `book_manager.py`, `book_pdf_generator.py`,
  `_confirm_membership_change.html` nor `book_detail.html`. G-2: the new route code reads
  `planned_cells`/`selection_cells` and defines no bucket bounds of its own. G-3: no ±3 pp
  tolerance anywhere in the new code. The CSS SCOPE+ is token-only — `var(--space-1)`,
  `var(--space-2)`, one widened selector reusing the existing declarations, and a
  `margin-bottom: 0` (a zero, not a px literal).
- [Note] The implementation agent OVERWROTE the `## Worktree notes` section in the worktree
  card copy rather than appending to it, discarding the orchestrator's `[Env]`,
  `[Guardrail provenance]` and `[Seams already in place]` bullets. They survived because the
  main-repo copy is the orchestrator's own and was edited there; the sync appended the agent's
  sections beneath them. Worth knowing as a card-ownership hazard: had those bullets existed
  only in the worktree, they would be gone.

### Orchestrator gates after Fix 1 (2026-09-30)

- [Build gate] PASSED on f94f29e, re-run by the orchestrator rather than taken on the agent's
  word: **5364 tests, 5355 passed, 2 failed, 7 skipped** — exactly the numbers the fix round
  reported. 5364 = 5361 + the 3 new clamp tests. The two failures are the known stale-heading
  assertions, untouched.
- [Card ownership hazard, second occurrence on this card] The fix agent again OVERWROTE the
  worktree card's notes rather than appending, and this time it cost something: **decision 3 —
  the owner's clamp ruling — existed only in the worktree copy**, which is deleted at merge,
  while the main copy still read "The two decisions the card left open". The section was pulled
  across by hand during the cycle-2 sync. Worth stating plainly because this card's whole value
  is that its open decisions are written down, and the one the owner personally ruled on was
  the one at risk of vanishing.

### [Fix 2] — review cycle 2 (8.5, no Critical, no Important) → 2046b80

Appended, not overwritten: the notes above (including decision 3, the owner's clamp ruling)
are read and left exactly as they stand.

Cycle 2 is not a gate failure — 8.5, no Critical, no Important, the card already mergeable.
Two Minor findings closed because both are cheap and one of them is an untested attribute,
which is how a fix rots.

- **F-008 (the two unpinned markup changes) → fixed.** Seven tests in
  `tests/test_books_list_plan_stats.py`, plus three raw-markup read helpers (`head_of`,
  `heads_of`, `plan_bar_of`) beside the file's existing fragment readers.
  - `CK-6 TestBooksList_SortableHeadsAnnounceTheirOrder` — the sorted head carries
    `aria-sort="descending"` and the other sortable head `aria-sort="none"`; the pair SWAPS
    under `?sort=created` (so the macro's argument is pinned too); exactly two heads carry the
    attribute and they are Puzzles and Created; and `aria-sort=&` appears nowhere while
    `aria-sort="` appears exactly twice, so an escaped render goes red.
  - `CK-7 TestBooksList_PlanBarSaysWhichFillItIs` — 132/150 draws `data-status="partial"` with
    `generating` nowhere in the bar; 150/150 and 160/150 both draw `complete`.
  - Both surviving mutants now die, each applied then restored by exact copy with the restore
    verified by sha256 (`e79dd668…fac4`): swapping the `aria-sort` values → 2 failed;
    reverting `partial` to `generating` → 1 failed.
  - **A correction to the finding itself, worth keeping:** `|e` and `|string` are *not* the
    escaping failure mode it names. Both were tried as mutants and both left the file green —
    `escape()` and `soft_str()` are no-ops on `Markup`. The reachable mutations are
    `|forceescape` and moving the attribute into a Python-side string; `|forceescape` was run
    and killed by 3 tests. The correction lives in CK-6's docstring so it is not re-derived.
- **F-009 (components.md over-claiming) → fixed.** One clause appended inside the same
  DataTable paragraph, saying the `aria-sort` head treatment is `books_list.html` only and
  that `_puzzle_table.html` has yet to follow (`href="#"` plus script, no `aria-sort`, arrow
  unwrapped, direction unsaid). The `sort_by` vs `sort` half is good and was left alone. All
  three claims re-read against `_puzzle_table.html:19-33` before writing them. No new card:
  f94f29e's commit message already names the deferral.
- **F-001, F-007, F-010 left open** as the report has them — two by standing decision, one an
  orchestrator concern (the branch has since been rebased; this Fix 2 sits on
  c13e430 + 0876738 + 2046b80).

- [Scope] Two files, tests and documentation only: `tests/test_books_list_plan_stats.py`
  (+140) and `meta/design/components.md` (+4/-1). **No production behaviour changed** —
  `app.py` and `books_list.html` are byte-identical to 0876738, which the mutation restores
  verify by checksum.
- [Guard] G-1/G-4: nothing under `src/nonogram/db/**` or `migrations/**`, and neither
  `book_manager.py`, `book_pdf_generator.py`, `_confirm_membership_change.html` nor
  `book_detail.html` appears in the diff. G-2: no bound, range check, `max(w,h)` or bucket
  label added anywhere — `BUCKET_BOUNDS` is untouched and still independent of `book_plan`.
  G-3: no tolerance introduced. No colour, px or font literal added
  (`tests/test_admin_design_tokens.py` green in the full run below).
- [Existing tests] None weakened, retargeted or deleted. CK-4's floors are verbatim:
  `CORPUS_CASES = 24`, `seen_short >= 20`, `seen_over >= 20`.
- [Suite] **5371 tests, 5362 passed, 2 failed, 7 skipped** (286.90s). 5371 = 5364 + the 7 new
  tests; passed rises by exactly 7 and skipped does not move, so the new tests EXECUTE —
  in-memory mode, the fixture deletes `DATABASE_URL` and no database is consulted. The two
  failures are the known stale-heading assertions in
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`
  and `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders`,
  untouched. The card's own file: 27 passed, up from 20. No database was created, dropped or
  recreated.

- [Build gate] PASSED on 2046b80, re-run by the orchestrator: **5371 tests, 5362 passed,
  2 failed, 7 skipped** — the two long-known stale-heading failures. Confirmed independently
  that Fix 2 changed no production code: `git diff --name-only 0876738 HEAD -- src/` is empty.
- [Correction carried from Fix 2, worth keeping] Cycle 2's F-008 named `|e` and `|string` as
  the escaping failure mode. They are not: both are no-ops on `Markup`, so no test can go red
  on them and none should claim to. The reachable mutations are `|forceescape` and moving the
  attribute into a Python-side string — `|forceescape` is now killed by
  `test_the_attribute_is_markup_and_not_escaped_text`. Recorded so nobody re-derives it.
