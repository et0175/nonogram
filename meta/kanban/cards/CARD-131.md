# CARD-131: A published book confirms before its puzzles change, and going back never discards later work

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/131-published-confirm-and-no-discard
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-16 (FR-038 INV-008 + EC-026 half)
**Idea:** —
**Wave:** 26
**Depends on:** CARD-126, CARD-130
**Touches:** src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/_confirm_membership_change.html, src/nonogram/admin/templates/book_detail.html, src/nonogram/admin/templates/book_select_puzzles.html, tests/test_book_published_confirm.py, tests/property/test_book_workflow.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

1. **INV-008: confirmation, not refusal.** `add_puzzles_to_book` and
   `remove_puzzle_from_book` currently refuse a published book outright (both storage
   modes). They now take a `confirmed: bool` argument. On a published book, if
   unconfirmed, they change nothing and return a "needs confirmation" outcome. If
   confirmed, they apply the change. This is the one behaviour this increment removes
   (Collapses: "the published-book refusal turned confirmation"). Non-published books
   behave as before. CARD-121's floor and override rule and CARD-126's end-of-level
   placement still apply on the confirmed path.
2. **Routes** (`/book/<id>/add-puzzles`, `/book/<id>/remove-puzzle`, and the selection
   step's POST): when the outcome is "needs confirmation", render a confirmation
   (`_confirm_membership_change.html`) that names the book, its status and the change.
   Re-POSTing with `confirm=1` applies it.
3. **Back-navigation never discards (EC-026).** Only an explicit add, remove, reorder
   or retitle changes the selection set, the order or the custom titles. Audit every
   step's POST handler (Print setup, general info, selection, arrange, finalise) for
   side-effect writes to `puzzle_ids`/`puzzle_titles`, and list them in Worktree notes.
   Changing the plan keeps the selection (AC-228). Removing a puzzle keeps the rest of
   the arrangement and its titles (AC-229). Its title entry is dropped, and so is its
   floor override (CARD-121).
4. **Back to draft** (owner decision 2026-09-22 (c); FR-037/FR-038 amended, INV-012,
   ADR-0035 clarification). Adding or removing puzzles on a book that has **left draft**
   (`ready_for_pdf`, `pdf_generated`, `ready_for_kdp`, or `published` once confirmed)
   sets its status to **draft** in the same store write, in both storage modes and on
   every route (selection step, paste-IDs form, remove). The book must then pass
   CARD-124's plan check again before it leaves draft (AC-282). An **unconfirmed**
   change to a published book changes nothing, status included (AC-280). A change on a
   draft book leaves it in draft. Reorder and retitle are **not** membership changes
   and keep the status: the owner named add and remove only, and FR-038's
   `_meta.open_question` records the question. Note it in Worktree notes.

## Increment 16 checkpoint

From `/books`, a `pdf_generated` book opens into the step workflow with all five steps
linked, and its title is edited in place (CARD-130). Adding a puzzle to a published
120-puzzle book without confirming leaves 120 and asks; confirming makes 121 and returns the book to draft (this card). A puzzle added to a
`pdf_generated` book likewise returns it to draft. The list shows "132 / 150" and "easy 50 / 60 · medium 60 / 60 · hard 22 / 30"
for the seeded fixtures, hints a short 26-30 × hard bucket, and sorts 150/150, 132/150,
20/100 (CARD-132).

## Acceptance criteria

- **AC-226** (INV-008) — given a published book holding 120 puzzles, when a puzzle is added without confirmation, then the book still holds the same 120 puzzles and the response asks for confirmation.
  *test:* `TestBookPublished_PuzzleChangeRequiresConfirmation`
- **AC-227** (INV-008) — given the same published book holding 120 puzzles, when a puzzle is added with confirmation, then the book holds 121 puzzles.
  *test:* `TestBookPublished_ConfirmedPuzzleChangeApplied`
- **AC-228** — given a book with a plan of 150 and 40 puzzles selected, when the plan's count is changed to 120 on Print setup, then the same 40 puzzles remain selected.
  *test:* `TestBookPlanChange_KeepsSelection`
- **AC-229** — given a book arranged A, B, C, D with a custom title on each, when puzzle B is removed, then the arrangement is A, C, D with the same custom titles on A, C and D.
  *test:* `TestBookRemovePuzzle_KeepsRestOfArrangement`
- **AC-277** (INV-012, added 2026-09-22 (c)) — given a book in status pdf_generated holding 120 puzzles, when a puzzle is added, then the book's status is draft.
  *test:* `TestBookMembership_AddOnNonDraftReturnsToDraft`
- **AC-278** (INV-012, added 2026-09-22 (c)) — given a book in status ready_for_pdf holding 120 puzzles, when a puzzle is removed, then the book's status is draft.
  *test:* `TestBookMembership_RemoveOnNonDraftReturnsToDraft`
- **AC-279** (INV-012, added 2026-09-22 (c)) — given a published book holding 120 puzzles, when a puzzle is added with confirmation, then the book's status is draft.
  *test:* `TestBookPublished_ConfirmedChangeReturnsToDraft`
- **AC-280** (INV-008, added 2026-09-22 (c)) — given a published book holding 120 puzzles, when a puzzle is added without confirmation, then the book's status remains published.
  *test:* `TestBookPublished_UnconfirmedChangeKeepsStatus`
- **AC-281** (INV-012, added 2026-09-22 (c)) — given a book in status ready_for_kdp holding 120 puzzles, when a puzzle's id is pasted into the detail page's add-puzzles form (POST /book/<id>/add-puzzles), then the book's status is draft — the paste-IDs route returns it to draft too.
  *test:* `TestBookAddPuzzlesByIds_NonDraftReturnsToDraft`
- **AC-282** (FR-037, INV-012, added 2026-09-22 (c)) — given a 100-puzzle book that passed the check and reached pdf_generated, returned to draft by adding 4 medium 16-20 puzzles and removing 4 easy ones so its 16-20 x medium cell holds 14 against a plan of 10, when the book is marked ready, then the transition is rejected and the status remains draft.
  *test:* `TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership`

## Engineering constraints

- **EC-026** (consistency) — For any book and any sequence of step visits and plan edits, the selection set, the arrangement order and the custom titles change only through an explicit add, remove, reorder or retitle — never as a side effect of revisiting a step or editing the plan.
  *test:* `PropertyTest_BookWorkflow_BackNavigationNeverDiscardsLaterWork`
- **EC-033** (consistency, INV-012; added 2026-09-22 (c)) — For any book, any starting status and any sequence of adds and removes over every route (selection step, paste-IDs form, remove, any future route ending in the book store), a book whose membership differs from the membership it last left draft with is in draft — no route leaves a non-draft book holding a changed membership, for every sequence, not only the measured examples.
  *test:* `PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists`

## Guardrails

- G-1: No schema change (Increment 16). Do not edit `src/nonogram/db/**` or `migrations/**`.
- G-2: Out of scope: one puzzle in several books (ADR-0033). The one-book-per-puzzle rule and the `puzzles.book_id` mirror stay as they are.
- G-3: Book assembly never changes a puzzle's grid, clues, tier or strategies (ADR-0033/R1).
- G-4: CARD-121's floor rule and CARD-126's level placement hold on the confirmed path. test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence.
- G-5: Do not edit `src/nonogram/admin/templates/books_list.html`, which is owned by CARD-132 this wave, or `src/nonogram/admin/book_pdf_generator.py`, which is owned by CARD-128 this wave.

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

- **FR:** FR-038 (AC-226..AC-229, AC-277..AC-281, EC-033), FR-037 (AC-282)
- **NFR:** —
- **ADR:** ADR-0033, ADR-0035
- **Components:** COMP-009, COMP-010 (reads only)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** Modal or inline confirm panel — **register "ConfirmChange" in components.md** if no existing entry fits (states: asking · confirmed · cancelled), Button (reuse — primary "Confirm change", secondary "Cancel"), Flash / Alert (reuse — warning)
- **Screens:** /book/<id> (add-puzzles, remove-puzzle), /book/<id>/select-puzzles (published book)
- **Standards:** forge:engineering-standards §11

## Worktree notes

—

- [Handover from CARD-124, 2026-09-23] A plan edit now returns a non-draft book to draft, which opens a two-step path around the published-membership guard: edit the plan (book -> draft), then POST /add-puzzles. FR-038's confirmation must actually land here — do not assume the old outright refusal still covers a published book.

- [Handover from CARD-121, 2026-09-23] INV-012: a fully-refused submission must NOT demote a book — the return-to-draft write belongs AFTER the floor filter. A comment marks the spot in book_manager.py. INV-012 still has no implementation and no tests.
