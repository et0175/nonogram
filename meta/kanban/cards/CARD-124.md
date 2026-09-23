# CARD-124: The readiness gate — no book leaves draft unless it matches its planned book (±3 pp per cell, planned-total denominator)

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/124-book-readiness-gate
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-14 (FR-037, ADR-0035)
**Idea:** —
**Wave:** 22
**Depends on:** CARD-119, CARD-120
**Touches:** src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, tests/test_book_ready_gate.py, tests/property/test_book_ready_gate.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-09-22T22:16:55Z
**Closed:** 2026-09-23T00:57:21Z
**Actual:** 0.3d
**Merge commit:** 238c6c0
**Blocked by:** —

## What to implement

1. **`BookManager.set_book_status`** gates **every transition out of draft**, whatever
   the target status (`ready_for_pdf`, `pdf_generated`, `ready_for_kdp`, `published`).
   This closes today's status-jump bypass (ADR-0035 (a)). The check:
   - no stored plan → refused, with a message to store a plan on Print setup first
     (ADR-0035 (c));
   - otherwise, for each of the 12 longest-side × tier cells, actual share = count /
     **planned total** and planned share = planned cell / planned total (ADR-0035 (b)).
     The transition succeeds only if every cell satisfies |actual − planned| ≤ 3.0 pp,
     **inclusive**.
   - A refusal leaves the status unchanged and names **every** offending cell with its
     actual and planned share ("16–20 × medium: 14% against 10%").
   Counts come from CARD-119's `selection_cells` / `planned_cells`, the one bucketing
   function. Compare in integer arithmetic (or exact fractions) so that 3.0 pp is not
   lost to float rounding (AC-219). Both storage modes.
2. The **`POST /book/<id>/status`** route, and any other route that moves a book out of
   draft (check the finalize and generate-pdf routes for implicit status writes and
   list them in Worktree notes), go through `set_book_status` and flash the refusal
   text.
3. **State the non-draft membership stance explicitly** (decided by the owner
   2026-09-22 (c); ADR-0035 clarification "Membership change after draft", INV-012).
   **The gate runs at the transition out of draft only**, and adding or removing puzzles
   on a book that has left draft **returns it to draft**, so it passes this gate again
   before it can leave (FR-037 AC-282). CARD-131 implements the return to draft on the
   membership paths. This card only states the rule in the `set_book_status` docstring
   and leaves no bypass: a book returned to draft goes through the same gate as any
   other draft book. The earlier stance ("neither re-runs the check nor returns the
   book to draft") is superseded.
4. ⚑ **Live-DB behaviour change** (Rollback): a plan-less draft book can no longer leave
   draft until a plan is stored. ADR-0034's default makes that one save. Existing
   non-draft books are unaffected.

## Acceptance criteria

- **AC-218** (INV-007) — given a draft book with a plan of 100 puzzles and 100 selected, every longest-side x tier cell within 3 points of its plan, when the book is marked ready, then the status transitions to the ready status.
  *test:* `TestBookReady_AcceptsWhenEveryCellWithinTolerance`
- **AC-219** (INV-007) — given the same 100-puzzle book whose 16-20 x medium cell holds 13 against a plan of 10 (13% vs 10%), every other cell within 3 points, when the book is marked ready, then the status transitions to the ready status — exactly 3.0 points is inside the tolerance.
  *test:* `TestBookReady_ExactlyThreePointsAccepted`
- **AC-220** (INV-007) — given the same 100-puzzle book whose 16-20 x medium cell holds 14 against a plan of 10 (14% vs 10%), when the book is marked ready, then the transition is rejected with the status remaining draft.
  *test:* `TestBookReady_RefusedBeyondThreePoints`
- **AC-221** — given the same refused 100-puzzle book, when the refusal is shown, then it names the 16-20 x medium cell with 14% against 10%.
  *test:* `TestBookReady_RefusalNamesOffendingCell`

_ADR-0035 Neutral: "the card adds criteria for the under-filled and plan-less cases". Carried as card-level criteria (derived from ADR-0035's Decision, not invented):_

- CK-1 — given a draft book with a plan of 100 at the right mix but only 50 selected (every cell at half its planned share), when it is marked ready, then it is refused (planned-total denominator).
  *test:* `TestBookReady_UnderFilledBookRefusedAgainstPlannedTotal`
- CK-2 — given a draft book with no stored plan and puzzles selected, when it is marked `ready_for_pdf`, then it is refused with a message pointing to Print setup.
  *test:* `TestBookReady_PlanlessBookRefusedWithRemedy`

## Engineering constraints

- **EC-025** (consistency, INV-007) — For any plan and any selection, marking the book ready succeeds if and only if every one of the 12 longest-side x tier cells is within +/-3 percentage points of its planned share — no route to the ready status bypasses the check, for every combination of counts, not only the measured examples.
  *test:* `PropertyTest_BookReady_GateIffEveryCellWithinTolerance`
- EC(ADR-0035/R1): no book leaves draft (to any other status) unless it has a stored plan and every longest-side × tier cell's count, divided by the planned total, is within ±3 pp of that cell's planned share. This holds for every target status, including a direct `draft → ready_for_kdp` or `draft → published` jump.
  *test:* `TestBookStatus_EveryExitFromDraftIsGatedOnThePlan`

## Guardrails

- G-1: No status-order rule is added. ADR-0035 gates exits from draft and explicitly does not add a mandatory status chain the requirements never asked for.
- G-2: Do not edit `src/nonogram/admin/book_plan.py`. The one bucketing and counting function is CARD-119's; consume it (EC-024).
- G-3: Do not edit `src/nonogram/admin/book_page_spec.py`, `src/nonogram/db/**` or `migrations/**`. They are owned by CARD-115 this wave. The gate needs no schema change.
- G-4: Do not edit `src/nonogram/admin/templates/book_select_puzzles.html`. It is owned by CARD-122 this wave.

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

- **FR:** FR-037
- **NFR:** —
- **ADR:** ADR-0035, ADR-0034
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** Flash / Alert (reuse — danger variant, one line per offending cell), StatusChip (reuse, unchanged)
- **Screens:** /book/<id> (status form), any step that posts a status change
- **Standards:** forge:engineering-standards §11

## Worktree notes

—

- [Handover from CARD-120, 2026-09-22] O-4: Print setup currently lets the plan be edited on a book that has left draft. Decide here whether a plan edit on a non-draft book returns it to draft (as a membership change does, ADR-0035 clarification) or is refused.

- [Handover from CARD-122, 2026-09-23] app.py edits are confined to the imports and create_app's ~2203-2645 region, nothing reordered. Reuse puzzle_review.PuzzleFilter.longest_side_range and BOOK_TAB_SORT instead of filtering in Python. INV-012's "returns it to draft" half is implemented nowhere and its six named tests do not exist — that is CARD-131's scope, but the gate you build must not assume it.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

### CARD-124 implementation, 2026-09-23

`[Owner decision, CARD-124] Plan edit on a non-draft book returns the book to draft (same rule as a membership change, ADR-0035 clarification). Alternative considered and rejected: refuse the edit. Rationale: the plan IS what the gate measured the selection against, so editing it unmakes the verdict that let the book out — refusing the edit would instead freeze a wrong plan behind a status.`

Implemented in `BookManager.save_plan` (the domain seam, both storage modes), not in the route,
so every caller of save_plan gets it; `POST /book/<id>/setup-print` reads the status before the
save and flashes "The plan changed, so the book is back in draft…" as a warning.

**Where the gate lives.** `BookManager.set_book_status` calls `_refuse_unless_the_planned_book`,
which runs only when `current == draft and new != draft` and raises `ValueError` (the exception
`set_book_status` already raises for its other two rules — no new hierarchy). The verdict itself
is two module-level pure functions in `book_manager.py`: `off_plan_cells(plan, puzzles)` and
`ready_refusal(plan, puzzles)`, computed once from (plan, records) and applied identically in
both storage modes. Counts come from CARD-119's `selection_cells` / `planned_cells` only (EC-024,
G-2 kept: `book_plan.py` untouched). The comparison is
`abs(actual - planned) * 100 <= 3 * plan.count`, exact integers, so AC-219 (13 vs 10 of 100)
passes and AC-220 (14 vs 10) fails. Denominator is `plan.count` — "the book that was planned",
never zero (INV-005); for a hand-edited matrix that disagrees with its split the cells are still
measured against the stated total, which is documented on `off_plan_cells`.

**Route audit** (every route that could move a book out of draft — all of them now go through the
gated `set_book_status`, and none writes a status behind its back):

| route | status write | verdict |
|---|---|---|
| `POST /book/<id>/status` (~3079) | `set_book_status(book_id, form status)` | gated; already catches `ValueError` and flashes `Error: <refusal>` — no change needed, test drives it |
| `POST /book/<id>/finalize` (~2726), `action=save_and_finish` | `set_book_status(..., ready_for_pdf)` | gated; its `except Exception` flashes the refusal and the page re-renders with the status unchanged |
| `POST /book/<id>/generate-pdf` (~3095) | **none** — writes `set_pdf_url` (metadata) only | not an exit from draft; a draft book can still export a PDF, which ADR-0035 does not gate |
| `POST /book/<id>/download-pdf` (~2991) | **none** | pure export |
| `POST /book/<id>/delete` (~3003) | **none** (reads `book.status`) | unchanged |
| `POST /book/<id>/setup-print` (~2087) | **new**: `save_plan` returns a non-draft book to draft | the owner decision above |

Grep of the whole admin package for writes to a book's status finds exactly three: `create_book`
(draft), `save_plan` (back to draft, new) and `set_book_status` (gated). No bypass.

**SCOPE+ tests/test_book_manager.py** — the gate changes `set_book_status`'s contract, and three
tests encoded the old one (advance / publish a book of placeholder puzzle ids with the default
150-puzzle plan). They now store `EMPTY_SELECTION_PLAN` first, with a comment saying why: those
ids resolve to no record, so the plan their selection matches is the one that plans no cell.
**SCOPE+ tests/test_card_108_delete_book_releases.py** — same cause, one line: the published-book
test plans its single 10x10 easy puzzle (`ONE_SMALL_EASY_PUZZLE`) before publishing.

**Tests.** `tests/test_book_ready_gate.py` (AC-218/219/220/221, CK-1, CK-2,
`TestBookStatus_EveryExitFromDraftIsGatedOnThePlan`, `TestBookPlanEdit_OnANonDraftBookReturnsItToDraft`),
every storage-level class parametrised over memory and DB (real SQLite); the two user-facing
halves — the status route flashing the offending cell, and Print setup returning a book to draft —
through the Flask test client, since there is no browser harness. `tests/property/test_book_ready_gate.py`
holds `test_PropertyTest_BookReady_GateIffEveryCellWithinTolerance` (repo convention for the
property-test name): 600 seeded cases from `random.Random`, half drawn inside the tolerance band
and half around it so both boundaries and both verdicts are measured, with an independent
`Fraction`-based oracle over the counts each case was *built* from, minimum case and per-verdict
counts asserted in the test; plus the plan-less case and a 24-case sub-corpus driven through real
books in **both** storage modes for **every** non-draft target status. Full suite green (only the
known pre-existing `TestFlow2BatchImageUpload::test_size_configuration_applied` deselected).

**Handover to CARD-131** — what the gate assumes of the membership paths:
1. INV-012's "returns it to draft" half is still unimplemented here; `add_puzzles_to_book` /
   `remove_puzzle_from_book` do **not** touch the status, and the gate does not assume they do.
   When you add it, write `BookStatus.DRAFT.value` the way `save_plan` now does (both storage
   modes, no extra flag) — nothing else is needed, because a book back in draft leaves it only
   through `set_book_status`, which is the same gate as for any other draft book.
2. `_refuse_unless_the_planned_book` is keyed on the *current* status being draft, so a book you
   return to draft is re-judged on its new membership automatically. There is no "already
   approved" memo to invalidate.
3. One test asserts the "gate runs at the exit only" half by dropping the stored plan of a book
   that has already left draft (`test_the_gate_runs_at_the_exit_only`) rather than by changing its
   membership, so it stays true once CARD-131 lands.
4. `_selection_records` reads the selection through `self.puzzle_store`; a manager built without a
   store logs and reads the book as empty, which refuses rather than waves through.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)
- [System contract] fresh lens run (`system_rules.py --card CARD-124`) returned the same 44 rule ids as the card's `## System contract` section — no refresh needed.
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, tests/property/test_book_ready_gate.py, tests/test_book_manager.py, tests/test_book_ready_gate.py, tests/test_card_108_delete_book_releases.py
- [Build gate] impact underivable (python-pro, no pytest-testmon installed) — full suite
- [Build gate] PASSED (full, 152s) — 4245 passed, 28 skipped, 0 failed (known pre-existing `TestFlow2BatchImageUpload::test_size_configuration_applied` deselected)
- [Scope gate] ⚠ grown: 2 files outside Touches (tests/test_book_manager.py, tests/test_card_108_delete_book_releases.py — both declared SCOPE+ by the implementation agent; contract change to `set_book_status` broke three pre-existing tests that encoded the old contract). No COMP spread (all files map to COMP-009), no sibling poaching, no guardrail hits: book_plan.py, book_page_spec.py, src/nonogram/db/**, migrations/** and templates/book_select_puzzles.html are all absent from the diff.
- [Visual] no `make run` target in this repo (no Makefile) — visual capture degraded to static-only; user-facing ACs are covered by Flask test-client tests instead of a browser harness.

- [Review 1/3] Score: 6.5 — crit: 0, imp: 2
- [Review sync] 1 report(s) → meta/review/20260922T230607Z-CARD-124-cycle1.yml
- [Review 1/3] Step 8h coverage: all 44 card rules carry a verdict line (9 ✓ holds, 35 ⚠ unchecked — 33 no_eligible_fact, INV-008/INV-012 check_ref_missing, 0 ✗). No extra ids beyond the card's section.
- [Adversarial] F-002 (`save_plan` un-publishes a published book, "violates INV-008") REFUTED — INV-008 and ADR-0035's clarification both scope to a published book's *puzzle membership*, and `save_plan` provably writes only `distribution_plan`/`status`/`updated_at`. FR-038 (requirements.yml:2731-2732) explicitly REPLACES the blanket published-book refusal with a confirmation, and AC-225 requires every step page to render 200 whatever the status, so reaching Print setup on a published book is required, not a leak. The behaviour is also not silent (the route flashes a warning). A confirmation step here would be a NEW requirement pairing with FR-038 — CARD-131's scope, and G-1 forbids adding it here. Residue kept as a cheap test gap, not a finding.
- [Adversarial] F-001 (DB mode: check and status write span two sessions — TOCTOU "regression") REFUTED as framed. The structure is as described (session 1 reads/checks at book_manager.py:940-953, the gate runs outside any session at 958, session 2 blind-writes at 960-969; no version column, no row lock). But the *regression* half is false, proven by execution: the skeptic raced a concurrent publish into the PRE-CARD single-session `set_book_status` (`git show main:`) and clobbered it identically — SQLAlchemy's pysqlite dialect runs the SELECT outside any transaction and only BEGINs at the first DML, and the same holds on Postgres READ COMMITTED (session.py sets no isolation_level). ADR-0035/R1 is new in this card, so it never had a non-sequential guarantee to lose; published-immutability was already sequential-only. Net effect of the card: the pre-existing window widens by the gate's compute time. Real, pre-existing, whole-DB-layer property — recorded as a follow-up observation, not a defect of this card.
- [Review 1/3] After adversarial verification: crit: 0, imp: 0 (both Important findings refuted). Score 6.5 < min_score 8, so the success path stays closed on score alone and the card goes to a fix round on the three Minor findings + the test gap the F-002 skeptic surfaced.

### Review cycle 1 fix round, 2026-09-23 (score 6.5 → resubmit)

**F-001 (TOCTOU in the DB branch) — refuted as framed, documented instead.** The pre-card
single-session code has the identical exposure: SQLAlchemy's pysqlite dialect runs the SELECT
outside any transaction and only BEGINs at the first DML, and a Postgres READ COMMITTED session
behaves the same way, so the single `with` block never made the check and the write atomic. No
session restructuring, no locking, no version column — that is a whole-DB-layer property and
rewriting it here would grow into CARD-115's territory. Instead `set_book_status`'s docstring now
carries a short "What the guarantee is worth under concurrency" paragraph stating honestly that
the check and the write are not atomic and the guarantee is sequential-only, accepted because the
panel is a single-user loopback tool (CON-015).

> **Out of scope — follow-up card suggested (atomicity of the status verdict).** If the panel ever
> serves more than one writer, the status write needs to be atomic with the rule that authorises
> it: a compare-and-swap on `(status, puzzle_ids)` or a row lock inside the write session, applied
> across the whole book/puzzle storage layer rather than in `set_book_status` alone. Today's cost
> of not having it is zero (one owner, one browser); the cost of adding it here would be a
> storage-layer rewrite inside a 0.5d feature card.

**F-002 (`save_plan` un-publishes a published book) — refuted, behaviour kept.** INV-008 and
ADR-0035's clarification scope their confirmation to a published book's *puzzle membership*;
`save_plan` writes `distribution_plan`, `status` and `updated_at` and never touches the selection
(`TestSavePlan_NeverTouchesTheSelection` pins that). FR-038 (requirements.yml:2731-2732) replaces
the blanket published-book refusal with a confirmation, and AC-225 requires every step page to
render 200 whatever the status. Adding a published carve-out or a confirmation step here would be
a new requirement (CARD-131's scope) and G-1 forbids adding status rules. The uniform rule is the
card's recorded owner decision. The *test gap* the finding exposed is real and is closed below.

**M-1 (F-003) — Print setup no longer demotes a book on an unchanged re-save.** `setup_print` now
compares the submitted plan with the stored one (`_readable_plan`'s `current`, which is what
`revise_plan` already revises from) and drops the submission when they are equal, so an idempotent
re-save stores nothing, moves nothing and flashes nothing about the plan — the flash no longer
asserts a change that did not happen. `DistributionPlan` is frozen, so `==` is exact; a plan is
never equal to `None`, so the first save of a plan-less book still happens (pinned by its own
test). Strictly additive: one `else:` branch on the existing `try`, nothing in app.py reordered.

**M-2 (F-004) — `_selection_records` made genuinely fail-closed. Option (a) was taken.**
*Why (a) and not (b):* the honest docstring option would have left a real hole in place — a
store-less manager approving a book against a plan every cell of which is within 3 pp of zero —
and the cost of closing it turned out to be one fixture line, not a new file in the diff.
*The invariant enforced:* **the gate never concludes "this is the planned book" from a selection it
could not read.** *The discriminator:* `puzzle_store is None` **and** the book holds at least one
puzzle id — not "the store is absent", which is the correlated neighbour the finding's own wording
reached for. A book holding no ids is genuinely empty: nothing needs resolving, no conclusion is
drawn from an unread fact, and `set_book_status`'s pre-existing "Must have puzzles" rule already
refuses it a step earlier. Conversely a store that holds no row for an id *has answered* — that id
contributes to no cell, the same verdict `selection_cells` makes on a record with an
unrecognisable tier — which is pre-card behaviour this card did not change.
Both sides are driven as tests (`TestBookReady_UnreadableSelectionIsRefused`), in the finding's own
configuration: a store-less manager, one unresolvable id, and the degenerate `count=1` all-zero
plan that the old code approved, asserting the specific outcome (`ValueError` and the status still
`draft`) for every non-draft target, in both storage modes. `create_app` wires a store on both
branches (app.py:952/957), so this is a wiring error, not a reachable state of the panel.
Declarations corrected with it: the `_selection_records` docstring, its log line (now `error`, and
it no longer says "sees an empty book"), the `Raises:` of `_refuse_unless_the_planned_book`, and
handover note 4 above. `tests/test_book_manager.py`'s fixture now wires a real in-memory
`PuzzleReviewService` the way `create_app` does, which makes the `EMPTY_SELECTION_PLAN` comment
truthful (the placeholder ids resolve to no *row*, not to no *store*) and is the better test.
`tests/test_card_108_delete_book_releases.py` already used a real store and needed no change.

**M-3 (F-005) — N+1 left in place, recorded.** No local mitigation exists: `PuzzleReviewService`
exposes no batched read, and `PuzzleFilter.book_id` reads the `Puzzle.book_id` mirror rather than
`Book.puzzle_ids`, so using it would silently change which side of membership the gate measures.
Adding a batch getter means editing `puzzle_review.py`, outside this card's Touches.

> **Out of scope — follow-up card suggested (batched selection read).**
> `BookManager._selection_records` calls `PuzzleReviewService.get_puzzle` once per puzzle id, and
> in DB mode that method opens its own session per call. Cost: a 150-puzzle book pays 150 sessions
> and 150 SELECTs for one status change, and `tests/property/test_book_ready_gate.py`'s storage
> corpus pays it 24 times per parameterisation. Fix: a `get_puzzles(ids)` on the store doing one
> chunked `WHERE id IN (...)`, with `_selection_records` calling it; the in-memory branch keeps its
> dict lookup.

**Test gap closed.** `TestBookPlanEdit_OnANonDraftBookReturnsItToDraft::test_save_plan_returns_the_book_to_draft`
is now parametrised over `OUT_OF_DRAFT` instead of `ready_for_kdp` alone, so the plan-edit rule is
pinned at `published` too — the one non-draft status where the other two domain writers
(`set_book_status`, `add_puzzles_to_book`) behave differently.

**SCOPE+ tests/test_book_plan_storage.py** — comments only, no assertion touched. The section
banner (:657) and the `TestSavePlan_NeverTouchesTheSelection` docstring (:680) still said
"`save_plan` writes plan columns only", which this card made false: `save_plan` also writes
`status`. Both now say so and note that the books under test are in draft, where the rule leaves
them — which is why the existing assertions still hold unchanged.

**Design-context deviation, for the owner to eyeball.** The card's Design context asks the refusal
alert for "one line per offending cell"; `ready_refusal` joins the offenders with "; " into a
single danger alert (one Flash/Alert, all cells named). The behaviour is unchanged by this round —
flagged here deliberately so the owner can look at the rendered `/book/<id>` refusal and say
whether the joined form is acceptable or the alert should break per cell.

- [Fix 1] FIXED F-001 (docstring only — refuted as framed), M-1, M-2, TESTGAP, STALECOMMENT, DESIGNNOTE; SKIPPED F-002 (refuted), M-3 (no local mitigation — batch read needs puzzle_review.py, outside Touches; recorded as a follow-up).
- [Fix 1] declarations: 3 updated (doc `set_book_status`, doc `setup_print`, doc `_selection_records` + `_refuse_unless_the_planned_book` Raises + the log line + handover note 4), 0 confirmed, 4 none.
- [Fix 1] FIX PRE-GATE PASSED — the fix's own named tests run in isolation: tests/test_book_ready_gate.py::TestBookPlanEdit_OnANonDraftBookReturnsItToDraft and ::TestBookReady_UnreadableSelectionIsRefused, 26 passed.
- [Build gate] PASSED (full, 153s) — 4264 passed, 26 skipped, 0 failed. CARD-113 golden A4 tripwire files untouched.
- [Scope gate] grown (unchanged verdict, already noted): +tests/test_book_plan_storage.py (comments only, SCOPE+ declared). Still no guardrail hits.
- [Review 2/3] Score: 9.0 ✓ threshold reached + no critical/important — crit: 0, imp: 0, 3 minor (all additive: one guard, two tests).
- [Review sync] 2 report(s) → meta/review/ (20260922T230607Z-CARD-124-cycle1.yml, 20260922T233915Z-CARD-124-cycle2.yml)
- [Review 2/3] Step 8h coverage: all 44 card rules carry a verdict line (12 ✓ holds, 32 ⚠ unchecked — 31 no_eligible_fact, INV-012 check_ref_missing, 0 ✗). No extra ids beyond the card's section.
- [8h spot-check] INV-008 ✓ reproduced — `save_plan` writes exactly distribution_plan/status/updated_at in both modes, calls no helper, never touches puzzle_ids/order/puzzle_titles/the `Puzzle.book_id` mirror; `TestSavePlan_NeverTouchesTheSelection` green (4 passed) and its assertion block byte-identical to main. INV-008's own text (aggregates.yml:71-74) constrains a published book's *puzzle membership*, not its status, so the cycle-1 "violates INV-008" claim does not survive the invariant's wording. Three caveats recorded below for CARD-131 and the owner.
- [Handover to CARD-131 / owner-visible, from the INV-008 spot-check] ⚑ The card opens a two-step path around the published-book membership guard: `add_puzzles_to_book`'s only guard is `if status == PUBLISHED` (book_manager.py:475, :498), and `save_plan` now returns a published book to draft, so `POST /book/<id>/setup-print` (edit the plan) followed by `POST /book/<id>/add-puzzles` changes what was a published book's membership with no confirmation. This does NOT violate INV-008 as worded — at the instant membership changes the book is already in `draft` — and FR-038 is meant to replace that outright refusal with a confirmation anyway, which is CARD-131's scope. But the card removes the only thing enforcing INV-008's spirit on the add path, so CARD-131 should land the confirmation rather than assume the old refusal still covers it.
- [Out-of-scope, pre-existing] INV-008 is already unenforced on the remove path in main: `remove_puzzle_from_book` (book_manager.py:518-575) has no published-status check in either mode and `POST /book/<id>/remove-puzzle` calls it unguarded. Unchanged by this card. Also: all three of INV-008's declared checks (TestBookPublished_ConfirmedPuzzleChangeApplied / _PuzzleChangeRequiresConfirmation / _UnconfirmedChangeKeepsStatus) exist nowhere under tests/ — the invariant is currently unverified, not verified-green.
- [8h spot-check] ADR-0035/R1 ✓ reproduced — named tests green (TestBookStatus_EveryExitFromDraftIsGatedOnThePlan 30 passed; test_no_exit_from_draft_bypasses_it_in_either_storage_mode 8 passed, memory×db × 4 non-draft targets, asserting both an accepted and a refused population). `_refuse_unless_the_planned_book` (book_manager.py:881-902) is called on both branches immediately before the status write. Independent scan of all of src/ confirms exactly three book-status writers, all in book_manager.py (create_book→draft, save_plan→draft, set_book_status gated) — no SQLAlchemy update()/bulk_update, no raw SQL, no setattr on a book, no status write in book_membership.py, book_pdf_generator.py or app.py. Invalid/case-variant/empty/None target statuses are rejected before any write.
- [8h spot-check note, not a violation] The gate's guard is `if current_status != DRAFT or new_status == DRAFT: return`, so a book whose STORED status were None/""/"DRAFT"/an unknown legacy value would move to published ungated. Outside ADR-0035/R1 (which constrains books *leaving draft*) and unreachable in this codebase: `create_book` is the only row creator and always writes `draft`, and migration 001 declares `books.status` with `server_default='draft'`.
- [8h spot-check] ✗ INV-007 `✓ holds` NOT reproduced — the gate's substance re-derives (all four declared checks collected and green, 89 passed; the predicate at book_manager.py:161-167 is pure integer arithmetic over the full 12-cell product, AST-confirmed zero true-division and zero float literals in `off_plan_cells`/`_whole_percent`/`ready_refusal`; the oracle in tests/property/test_book_ready_gate.py:116-123 is independent `Fraction` arithmetic over the counts each case was built from, with >=500 total and >=100 per-verdict asserted inside the test and a real 300/300 accepted/refused split; the denominator is always `plan.count`). What failed: (a) the verdict's cited measurement "integer vs float predicates disagree on 48 triples over count 1..1000" reproduces under NONE of 18 formulation×range combinations tried (0, 135, 149, 290, 311, 315, 361, 511, 1849, 5959 — never 48); (b) the line cite 126-164 stops two lines short of the predicate (165-166). The qualitative claim did hold emphatically: every disagreement in every formulation sits exactly on the bound, and the integer form is load-bearing against double-dividing float forms (5959 and 290 disagreements) though not against `abs(a-p)/t*100` (0). AC-219's own numbers agree under all three float forms, so the ACs do not pin the integer choice — the property corpus does (7 of 600 cases put a cell exactly on the bound).
- [8h spot-check] INV-007 counter-evidence, triaged: (1) a book can hold `ready_for_kdp` with a cell 40 pp off plan by adding puzzles after it left draft — this is INV-012's membership half, explicitly deferred to CARD-131 by the card and by `set_book_status`'s docstring, and the card narrows rather than opens it (`save_plan` closes the plan-edit half of the same rule). NOT a defect of this card. (2) `off_plan_cells`'s own docstring (book_manager.py:144-146) claims "'Ready' therefore means the planned book, not merely the planned mix — an under-filled selection fails even when its proportions are right"; that holds only when the plan's matrix sums to `plan.count`, which the code elsewhere explicitly permits it not to (a hand-edited `disagrees_with_split` matrix lets a 5-puzzle selection pass a plan of 100). A false declaration this card introduced → sent to a fix round.

### Review cycle 2 fix round, 2026-09-23 (score 9.0, zero Critical/Important)

Four small additive items: three Minor findings the reviewer asked to fold in, plus one false
declaration this card introduced that an independent skeptic falsified. No redesign, nothing
reordered, `app.py` not touched at all this round.

**C2-M1 (F-001) — a damaged stored plan now reads as no plan.** `_refuse_unless_the_planned_book`
wraps its `get_plan` call in `except InvalidPlan`, logs it and continues with `plan = None`, so
the owner of a book whose `distribution_plan` document will not decode sees `NO_PLAN_REFUSAL`
("Store one on Print setup first") instead of `InvalidPlan: the puzzle count must be a whole
number of at least 1, got 0`. Same pattern as `app._readable_plan` (CARD-120), which is what lets
Print setup be the screen that repairs the document. Fail-closed before and after — the status
never moved either way — so ADR-0035/R1 is unchanged; what changed is the **error class** at that
seam. *Declarations re-derived with it:* the `NO_PLAN_REFUSAL` comment (a damaged document gets
the same remedy), `_refuse_unless_the_planned_book`'s own docstring and `Raises:` ("no
`InvalidPlan` leaves here"), `ready_refusal`'s docstring (`plan is None` now covers both facts,
collapsed by its caller), `set_book_status`'s `Raises:` (every refusal it makes is a `ValueError`
carrying the owner's text, so the route needs no second except clause) and its gate paragraph, and
`get_plan` — which never declared that it raises `InvalidPlan` at all and now does, saying that a
*damaged* plan is not the same fact as *no* plan and that its two screen-facing callers each
collapse it themselves.

**C2-M2 (F-002) — the no-op re-save test now discriminates the edit-mark round trip.** It used to
start from `AC_PLAN_AS_STORED` (all 12 cells edited), where `revise_plan`'s round trip is trivially
preserved. It now settles **the route's own** fixed point (`_settle_print_setup` posts the
identical form until the stored plan stops moving — three POSTs, asserted rather than assumed,
because an arbitrary matrix is not a fixed point on first submission), asserts the settled plan
carries a *partial* edit set (`frozenset() < edited < EVERY_CELL`), then promotes the book and
posts the same form once more. Killed by two mutations: dropping the `shown.edited` branch of
`is_edited` (never settles) and disabling the `new_plan == current` shortcut (book demoted to
draft). Test-only; no behaviour change.

**C2-M3 (F-003) — the second user-facing exit from draft is now pinned.** One Flask-test-client
case beside the status-route one: an off-plan draft book, `POST /book/<id>/finalize` with
`action=save_and_finish`, asserting 200, the offending cell in the rendered page and the status
still `draft`. The route was **not** changed. The flash is read out of the response body rather
than the session because this exit re-renders (200) instead of redirecting, so the template has
already consumed it. Killed by two mutations (no-op'ing the `set_book_status` call; dropping the
exception text from the bare `except Exception`'s flash).

**C2-M4 (declaration) — `off_plan_cells`'s "ready means the planned book" claim corrected; no
behaviour touched, `book_plan.py` untouched (G-2).** The old sentence — "an under-filled selection
fails even when its proportions are right" — is true only when the plan's 12 cells sum to
`plan.count`. FR-034 deliberately allows a hand-edited matrix that disagrees with its split
(warned about, never refused), and the gate measures such a plan's cells against the *stated*
total anyway, so `DistributionPlan(count=100, split=(45,40,15), cells=((5,0,0),(0,0,0),(0,0,0),(0,0,0)))`
is satisfied by exactly 5 puzzles with every cell 0 pp off. That is not an INV-007 hole (INV-007 is
per cell; every cell is on its plan) and the behaviour is correct as designed — only the sentence
was wrong. The docstring now names the condition, and the section banner above it stopped claiming
the unqualified version. `TestBookReady_UnderFilledBookRefusedAgainstPlannedTotal` gained a case
asserting that CK-1 holds *because* `AC_PLAN`'s matrix sums to its count.

> **Reachability (asked for explicitly): UI-reachable, not construction-only.** `_plan_from_form`
> validates whole numbers, a split summing to 100 and a count of at least 1, and hands the matrix
> straight to `revise_plan`; nothing anywhere compares the matrix with the count. Verified by
> running the real call: `revise_plan(None, 100, Split(45,40,15), ((5,0,0),(0,0,0),(0,0,0),(0,0,0)))`
> returns exactly that plan, `disagrees_with_split` True — i.e. an owner who types those 12 values
> into Print setup stores it. Pinned by
> `TestBookReady_DisagreeingMatrixIsMeasuredAgainstTheStatedTotal::test_such_a_plan_is_reachable_through_the_print_setup_form`,
> alongside the gate-level cases (5 passes; 8 of a planned 5 is 3 pp of the stated 100 and passes;
> 9 is 4 pp and is refused — measured against the matrix's own sum, 8 would be 60 pp out).

> **Noted, not fixed — outside this card's file set.** ADR-0035 itself carries the unqualified
> claim (`meta/architecture/decisions/adr/0035-book-readiness-gate-against-the-plan.md`, Decision
> and Neutral: "'Ready' means the planned book: an under-filled book fails even if its proportions
> are right"). It is the origin of the docstring's wording and has the same blind spot for a
> matrix that disagrees with its split. Correcting an ADR is not a code fix round's business; the
> code now states the precise rule, and whoever revises ADR-0035 next should carry the condition
> across.

Full suite green with the one known pre-existing deselection.

- [Fix 2] FIXED C2-M1 (damaged stored plan now refused with ADR-0035 (c)'s Print-setup remedy instead of a raw `InvalidPlan` decode message), C2-M2 (no-op re-save test now actually discriminates the `edited` round trip), C2-M3 (the `finalize`/`save_and_finish` exit from draft now has a route test), C2-M4 (the false `off_plan_cells` docstring claim corrected).
- [Fix 2] declarations: 6 updated (doc `_refuse_unless_the_planned_book` + its `Raises:`, doc `set_book_status` `Raises:` and gate paragraph, doc `get_plan` — which never declared `InvalidPlan` at all, doc `ready_refusal`, the `NO_PLAN_REFUSAL` comment, doc `off_plan_cells`), 0 confirmed, 2 none.
- [Fix 2] FIX PRE-GATE PASSED — the fix's own named tests run in isolation: 37 passed across TestBookReady_PlanlessBookRefusedWithRemedy, TestBookPlanEdit_OnANonDraftBookReturnsItToDraft, TestBookReady_RefusalNamesOffendingCell, TestBookReady_DisagreeingMatrixIsMeasuredAgainstTheStatedTotal, TestBookReady_UnderFilledBookRefusedAgainstPlannedTotal. The fix agent additionally mutation-killed each one (e.g. denominator `plan.count` → matrix sum fails both storage modes).
- [Build gate] PASSED (full, 1104s incl. waiting on the repo full-suite lock) — 4274 passed, 26 skipped, 0 failed.
- [Touches drift] Final diff touches 7 code files; the card's Touches predicted 4. SCOPE+ (all three declared on the card): tests/test_book_manager.py, tests/test_card_108_delete_book_releases.py (both: the gate changed `set_book_status`'s contract and these encoded the old one), tests/test_book_plan_storage.py (comments only, invalidated by `save_plan` now also writing `status`). Verdict GROWN, not runaway — no COMP spread, no sibling poaching, no guardrail hits.
- [Scope gate] Weakening check, mechanical: `git diff main -- tests/ src/` removes NO line containing `assert`, `pytest.raises`, `xfail` or `skip` anywhere in the diff. The only removed lines in the three out-of-scope files are one fixture body + docstring (test_book_manager.py) and two stale comments (test_book_plan_storage.py); test_card_108 removes nothing. No existing test was weakened, retargeted or deleted — they were extended.
- [Architect follow-up, owner-visible] ADR-0035 itself carries the same unqualified claim the C2-M4 fix corrected in code: its Decision and Neutral sections say "'Ready' means the planned book: an under-filled book fails even if its proportions are right." That holds only when the plan's 12 cells sum to `plan.count`, and Print setup lets the owner store a matrix that does not (verified UI-reachable: `_plan_from_form` validates whole numbers, a split summing to 100 and count >= 1, but nothing compares the matrix with the count, and `disagrees_with_split` warns without refusing per FR-034). A plan of 100 whose cells sum to 5 is therefore satisfied by 5 puzzles. Not an INV-007 hole (INV-007 is per cell, and every cell is on its plan) and not this card's to fix — for whoever revises ADR-0035 next.

- [AC/EC check] All criteria/constraints ✓ (evidence — fresh, re-derived by an independent gate agent that ran each named test itself):
  - AC-218 ✓ demonstrated — `TestBookReady_AcceptsWhenEveryCellWithinTolerance::test_the_book_reaches_the_ready_status[memory] PASSED`, `[db] PASSED`, plus `test_the_scenario_really_is_inside_the_tolerance PASSED`
  - AC-219 ✓ demonstrated — `TestBookReady_ExactlyThreePointsAccepted::test_thirteen_against_ten_of_a_hundred_passes[memory|db] PASSED`, `test_that_cell_is_exactly_the_tolerance_out PASSED`
  - AC-220 ✓ demonstrated — `TestBookReady_RefusedBeyondThreePoints::test_the_transition_is_rejected_and_the_book_stays_draft[memory|db] PASSED`, `test_only_that_cell_is_out PASSED`
  - AC-221 ✓ demonstrated — `TestBookReady_RefusalNamesOffendingCell`, 5/5 PASSED incl. `test_the_status_route_flashes_it` and `test_the_finalize_route_flashes_it`; asserts the literal "16-20 x medium: 14% against 10%"
  - CK-1 ✓ demonstrated — `TestBookReady_UnderFilledBookRefusedAgainstPlannedTotal::test_half_a_book_is_refused[memory|db] PASSED` + two data-pinning cases
  - CK-2 ✓ demonstrated — `TestBookReady_PlanlessBookRefusedWithRemedy`, 5/5 PASSED; refusal asserted to contain "no stored plan" and "Print setup"
  - EC-025 ✓ demonstrated — `tests/property/test_book_ready_gate.py::test_PropertyTest_BookReady_GateIffEveryCellWithinTolerance PASSED`. Name resolution checked, not assumed: `grep "^def PropertyTest_" tests/` → 0 hits, `grep "def test_PropertyTest_" tests/` → 23 hits, so the `test_` prefix is genuinely repo-wide. Property quality audited: seeded `random.Random(20260923)`, CORPUS=600, no hypothesis; minimum case count asserted INSIDE the test (>=500 total, >=100 per verdict); independent `fractions.Fraction` oracle over the counts each case was built from, never calling selection_cells/planned_cells/off_plan_cells, with a separate test pinning `Fraction(READY_TOLERANCE_POINTS,100) == TOLERANCE` so oracle and code can disagree; both directions of the iff exercised in quantity.
  - EC(ADR-0035/R1) ✓ demonstrated — `TestBookStatus_EveryExitFromDraftIsGatedOnThePlan`, 30 parametrized cases PASSED, exhausting all 4 non-draft targets × both storage modes in three scenarios (off-plan refused, plan-less refused, matching accepted) plus draft→draft-not-gated and gate-runs-at-exit-only. The count dimension it does not vary is covered by the corpus-based `test_no_exit_from_draft_bypasses_it_in_either_storage_mode` (same independent oracle, 24 cases per target×mode), green.
  - G-1 ✓ demonstrated (behavioral) — the guard is `if current_status != DRAFT or new_status == DRAFT: return` (book_manager.py:940): no predecessor/successor table, no ordering comparison, no allowed-transition map. `test_a_matching_book_reaches_every_target_directly[{memory,db}-{ready_for_pdf,pdf_generated,ready_for_kdp,published}]` 8/8 PASSED, incl. draft→published direct. `git diff main -- tests/ | grep -E '^-\s*(def test|class Test)'` → no output: no test removed, weakened or retargeted.
  - G-2 ✓ demonstrated (structural) — `src/nonogram/admin/book_plan.py` absent from the union of `git diff --name-only main...HEAD` and `git status --porcelain`.
  - G-3 ✓ demonstrated (structural) — `src/nonogram/admin/book_page_spec.py`, `src/nonogram/db/**`, `migrations/**` all absent from the same union.
  - G-4 ✓ demonstrated (structural) — `src/nonogram/admin/templates/book_select_puzzles.html` absent from the same union.
  - CARD-113 A4 golden tripwire ✓ intact — tests/test_export_a4_golden.py, tests/property/test_cli_exports_byte_identity.py and tests/fixtures/a4_golden/** absent from the diff and clean in `git status`; both test files green (66 passed).
  Epistemics as stated by the gate: the guardrail verdicts are bounded to the file paths this card's diff touches (committed + uncommitted at check time), not a claim about the rest of the repo; runtime coverage is the card's named tests plus the two tripwire files, not the full suite (the full suite ran separately at the build gate).
- [Docs] forge:readme skipped with reason: this card changed no directory structure or purpose (a domain rule added to an existing module, two test files added to existing test directories). `src/nonogram/admin/` and `tests/property/` have no README, and CLAUDE.md forbids creating documentation files proactively. `tests/README.md` exists but is a Wave-1-era artifact that enumerates only three feature test files and no book tests at all — stale repo-wide, not because of this card; adding a CARD-124 entry to a list omitting every other book test file would make it less coherent, not more. Recorded as an out-of-scope observation instead.
- [Commit] df2c758 `fix(books): close the readiness gate's fail-open paths and no-op re-save` (parent ddd1534). 5 files, explicit pathspecs: src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, tests/test_book_manager.py, tests/test_book_plan_storage.py, tests/test_book_ready_gate.py. Verified after the fact: nothing under meta/ entered either commit (the card file and both review YAMLs are still uncommitted in the worktree), no nonogram_admin.db / test.db / egg-info / pic1 / pictures. Message ends with the required Co-Authored-By line. Not pushed, not merged, not rebased; the main checkout was not touched.
- [Note] A repo hook printed "forge: source files changed — how-it-works docs may be stale" (suggests /forge:explain). Not run — out of this card's scope and post-wave work.

   store cannot see the selection and **raises** (`UNREADABLE_SELECTION_REFUSAL`), so the
   transition is refused outright. See the fix round below — reading it as an empty book was not
   fail-closed.

- [Done] main unchanged since branch base 168eae0; the card's final full-suite gate (4274 passed) ran on this tree. Merged 238c6c0 (--no-ff). Deferral scan: 0 hits. O-4 answered: a plan edit on a non-draft book returns it to draft. Two architect items queued to raw-requirements (ADR-0035 text, FR-038 confirmation path); follow-ups to CARD-131 and the backlog.
