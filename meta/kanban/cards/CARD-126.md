# CARD-126: The book order runs easy → medium → hard — moves stay within a level, new puzzles land at the end of theirs

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/126-book-level-order
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-15 (FR-041 order half; dividers and printing are CARD-128)
**Idea:** —
**Wave:** 24
**Depends on:** CARD-121
**Touches:** src/nonogram/admin/book_manager.py, src/nonogram/admin/book_plan.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_arrange_puzzles.html, tests/test_book_level_order.py, tests/property/test_book_order.py
**Review score:** 9.0 (cycle 1/3)
**Started:** 2026-09-23T03:55:53Z
**Closed:** 2026-09-23T06:26:23Z
**Actual:** 0.3d
**Merge commit:** ea35a7f
**Blocked by:** —

## What to implement

INV-009 applies to the stored order (TERM-032). COMP-010 sees order writes only, with no
schema change.

1. **`book_level_order(puzzle_ids, tier_of) -> list`** is a pure helper. Put it in
   `admin/book_plan.py` beside the other book-order and plan functions, or in a small new
   module; record which. It returns the order grouped easy, medium, hard, keeping the
   stored relative order within each level. It is **the one grouping** used by moves,
   adds, the arrange page and CARD-128's PDF. A legacy mixed arrangement is grouped by
   it without rewriting the stored list (AC-260's printing half is CARD-128).
2. **Moves (CMD-022 → EVT-023).** `move_puzzle_up` / `move_puzzle_down` /
   `reorder_puzzles` move a puzzle **only within its level**. A move that would carry it
   across a level boundary is **refused, and the order is unchanged** (AC-258). The
   route flashes the reason. On a legacy mixed book, a move operates on the grouped
   view and writes back the grouped order. Record this; it is the only point where a
   legacy order gets normalised.
3. **Adds.** `add_puzzles_to_book` places each new puzzle **at the end of its tier's
   level** (owner answer, trace FR-041 note). It keeps CARD-121's floor/override
   behaviour intact.
4. **Arrange page** (`book_arrange_puzzles.html`) shows the order grouped under level
   headings, and hides or disables the up/down controls at a level's first or last
   position.
5. Tier comes from the stored tier (`tier_of_record`), never re-graded (ADR-0033/R1).

## Acceptance criteria

- **AC-257** (INV-009) — given a book arranged E1, E2, M1, when E2 is moved up, then the order is E2, E1, M1.
  *test:* `TestBookArrange_MoveWithinLevelKeepsOwnerOrder`
- **AC-258** (INV-009) — given a book arranged E1, E2, M1, M2, when M1 is moved up, then the order stays E1, E2, M1, M2 — the move would cross the easy/medium boundary.
  *test:* `TestBookArrange_MoveAcrossLevelBoundaryRefused`
- **AC-259** (INV-009) — given a book arranged E1, E2, M1, H1, when an easy puzzle E3 is added, then E3 sits before M1 in the book order (inside the easy level).
  *test:* `TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel`

## Engineering constraints

- **EC-029** (consistency, INV-009) — For any book and any sequence of adds, removes and moves, the book order stays grouped by tier (easy, then medium, then hard); the relative order of two puzzles of one level changes only through an explicit move within that level; and the book PDF holds exactly one divider per non-empty level, immediately before that level's first puzzle, with puzzle numbers 1..n unbroken — for every sequence, not only the measured examples.
  *test:* `PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence` — _write the property here with its edit-sequence half (grouping plus within-level relative order under random add/remove/move sequences, in both storage modes); CARD-128 extends it with the divider and numbering half._

## Guardrails

- G-1: No schema change. The order is written through the existing `puzzle_ids` list (Increment 15 "COMP-010 (order writes only)"; Rollback: "a revert leaves any order written meanwhile valid (it is still a permutation)"). Do not edit `migrations/**` or `src/nonogram/db/**`.
- G-2: Book assembly never re-grades or changes a puzzle. Tier is read (ADR-0033/R1).
- G-3: CARD-121's floor and override rule on `add_puzzles_to_book` holds unchanged. test: TestBookAddPuzzles_RefusesBelowFloorWithoutOverride, PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride.
- G-4: Removing a puzzle keeps the rest of the arrangement and its titles. test: `TestBookRemovePuzzle_KeepsRestOfArrangement` (asserted in CARD-131; do not regress it).
- G-5: Do not edit `src/nonogram/admin/templates/book_select_puzzles.html` or `src/nonogram/admin/templates/book_finalize.html`, which are owned by CARD-123 this wave, or `src/nonogram/admin/book_pdf_generator.py`, which is owned by CARD-117 this wave.

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
- ADR-0031/R1 — Tier has exactly three members — easy, medium, hard — and every one has a score band. classify takes the score alone; no module derives a tier from branch_nodes. (check: TestTiers_ThreeBandsAndNoFourthTier)
- ADR-0031/R2 — A solve that branched is reported as the `guess` strategy (solver.STRATEGY_GUESS) in FR-029's strategies list, never as a tier. (check: TestTiers_BranchingIsAStrategyNotATier)
- ADR-0031/R3 — A stored difficulty_tier of "guess" reads back as Tier.HARD and is never rewritten by this decision; no migration runs and no production database is touched. (check: TestTiers_LegacyGuessRowReadsAsHard)
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

- **FR:** FR-041
- **NFR:** —
- **ADR:** ADR-0037, ADR-0031, ADR-0033
- **Components:** COMP-009, COMP-010 (order writes only)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** ArrangeRow (reuse — disabled up/down at a level boundary; add that state to components.md), Flash / Alert (reuse — refusal), TierChip (reuse for level headings)
- **Screens:** /book/<id>/arrange-puzzles
- **Standards:** forge:engineering-standards §11

## Worktree notes

—

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

---
### Implementation agent notes (synced from worktree)

### Where the level order lives

`book_level_order` and the functions beside it went into
**`src/nonogram/admin/book_plan.py`** (the card's first option), not a new
module. The plan decides *what goes into* a book and the order decides *what
order it prints in*, and both speak the same tier vocabulary (`TIERS`,
`tier_of_record`) — one module, one vocabulary, no second tier table. The new
surface is pure (ids in, ids out; the caller supplies `tier_of`):

* `level_rank(tier)` — 0 easy, 1 medium, 2 hard, `UNGRADED_RANK` (3) for
  anything else;
* `book_level_order(ids, tier_of)` — **the one grouping**. A stable sort on
  the level alone, so it never reorders inside a level, and idempotent, which
  is what lets a legacy order be *read* grouped without being rewritten;
* `is_level_order` — INV-009's predicate, used by `reorder_puzzles`;
* `book_levels` — the grouped order cut into `[(Tier|None, [ids])]`, one entry
  per **non-empty** level (the shape CARD-128's one-divider-per-level needs);
* `place_in_level` — the add rule: insertion at the end of the id's own level,
  never a re-sort;
* `moved_within_level` — the move rule: `None` at the very top/bottom of the
  book (unchanged meaning of today's `False`), `LevelBoundary` when the
  neighbour is in another level.

`LevelBoundary` subclasses `ValueError`, so every caller that already handles
the book store's refusals handles this one; the arrange route catches it
separately and flashes the rule as a warning rather than as an error.

### Where a legacy order gets normalised

**Only in a move.** `_move_within_level` computes on the grouped view and
writes the grouped order back through `reorder_puzzles`, so the first move an
owner makes on a pre-CARD-126 book normalises it — visibly, on the page they
clicked. Everything else leaves the stored list alone:

* `puzzle_levels` (the arrange page) reads it grouped and writes nothing;
* `add_puzzles_to_book` *inserts* each new id after the last id of its own
  level and touches no other position;
* `reorder_puzzles` refuses an ungrouped submission outright rather than
  silently regrouping it — the aggregate enforces INV-009, the page is not
  trusted to.

Tier always comes from the stored word through `difficulty.tier_of_record`
(`BookManager._stored_tier`), never from a grid or a size (ADR-0033/R1,
ADR-0031); a legacy `guess` row reads as hard and is not rewritten
(ADR-0031/R3). An id with no readable tier — no store, no row, not a UUID —
ranks after every graded level rather than raising: an order has no
fail-closed case, it stays a permutation of the membership either way.

`move_puzzle_up`/`move_puzzle_down` are now one line each over
`_move_within_level`; the four near-identical storage branches they held are
gone, and the single write goes through `reorder_puzzles` (a fresh list in
both modes, CARD-101's lesson).

### Renders for the owner

`~/Documents/nonogram-reviews/CARD-126/` — `arrange-puzzles.html` / `.png`
(nine puzzles submitted hard-first, shown grouped easy → medium → hard with a
TierChip heading per level, numbering 1..9 unbroken, up/down disabled at each
level's own ends) and `arrange-puzzles-refused-move.html` / `.png` (the flash
after moving the first medium puzzle up: the order is unchanged and the banner
names the rule). Rendered through the Flask test client by a throwaway script
in the scratchpad; the PNGs are headless Chrome.

### SCOPE+

* SCOPE+ `tests/property/test_book_export_interior.py` — EC-034's parity
  property assumed the interior printed the puzzles in *submission* order. It
  now prints them grouped, which is this card's whole point, so the loop takes
  the same puzzles in level order (`_as_the_interior_prints_them`, with its own
  rank table, kept independent like every other expected value in that file).
  The parity assertion itself is untouched and still runs on every page.
* SCOPE+ `meta/design/components.md` — the card's Design context asks for the
  ArrangeRow level-boundary state; recorded there. Not committed (nothing under
  `meta/` is committed from the worktree).
* `BookManager._below_floor_for` gained an optional `tiers` out-dict. The add
  needs each submitted puzzle's tier and the floor's pass already holds each
  record; without this the add would read the store twice per submitted id and
  break EC-021's "one store read per distinct id" (CARD-121 review F-004).
* `BookManager.reorder_puzzles` gained an optional `tier_of` argument so a move
  does not read the same rows twice. It never changes the verdict.

### Tests

* `tests/test_book_level_order.py` — AC-257/258/259 through the real routes
  (Flask test client) plus the store-level rule in **both** storage modes, the
  pure helper on its own, the legacy-mixed postures, and the read-never-regrade
  guard.
* `tests/property/test_book_order.py` —
  `PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence`, 25 trials x 14
  steps per storage mode over a seeded corpus, with a minimum step count *and*
  a minimum per kind (add / remove / moved / refused / book_end) asserted
  inside the test. Checked against injected bugs: removing both INV-009 gates
  fails it, and making the grouping unstable fails it.

Full suite green apart from the known pre-existing
`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`,
which is deselected and not this card's.

---
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/book_plan.py, src/nonogram/admin/templates/book_arrange_puzzles.html, tests/property/test_book_export_interior.py, tests/property/test_book_order.py, tests/test_book_level_order.py
- [Build gate] PASSED (full, 193s; 4498 passed, 0 failed; deselected the known pre-existing tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied)
- [Golden tripwire] untouched — tests/test_export_a4_golden.py, tests/property/test_cli_exports_byte_identity.py and tests/fixtures/a4_golden/** are not in the diff, and green in the gate run
- [Scope gate] in_scope — 1 file outside Touches (tests/property/test_book_export_interior.py, declared SCOPE+: EC-034's parity property assumed submission order); 0 guardrail hits (G-1 migrations/**, src/nonogram/db/**; G-5 book_select_puzzles.html, book_finalize.html, book_pdf_generator.py all absent from the diff)
- [Visual] no Makefile run target / no browser harness — review runs static-only; the implementation agent rendered the arrange screen to ~/Documents/nonogram-reviews/CARD-126/ (arrange-puzzles.html/.png, arrange-puzzles-refused-move.html/.png) for the owner and for the reviewer's 8g check
- [Review 1/3] Score: 9.0 — crit: 0, imp: 0 (4 minor, 2 out-of-scope)
- [Review 1/3] Step 8h coverage: 47/47 card rules carry a verdict line (21 ✓ holds, 26 ⚠ unchecked no_eligible_fact, 0 ✗) — verified by id against the card's section
- [Review sync] 1 report(s) → meta/review/20260923T052417Z-CARD-126-cycle1.yml
- [Adversarial] not run — 0 critical / 0 important findings to verify
- [8h spot-check] 3/3 sampled holds reproduced (INV-009, INV-013, ADR-0033/R1) — each skeptic re-ran the named tests, re-derived the claim independently and injected+restored a mutant; working tree verified clean after each
  - INV-009: write-path enumeration re-done from scratch over all of src/ — the reviewer's list of 7 writers is complete, no route bypasses the aggregate; property-test oracle confirmed independent of book_level_order, MIN_STEPS/per-kind floors asserted in-test
  - INV-013: the SCOPE+ edit to tests/property/test_book_export_interior.py is +28/-1, the single deleted line being the loop's order source; CASES=28, SEED=135 and every minimum-count assertion unchanged; two mutants (level_rank collapsed, parity flipped) both make it fail
  - ADR-0033/R1: only puzzle-store call in the diff is the read get_puzzle; no tier derived from grid/size/score/solver; legacy `guess` reads as hard without rewrite
- [Fix 1] discretionary pass over the cycle-1 minors (0 crit / 0 imp — this pass did not gate): F-001 page-break indicator renumbered off the whole book, F-003 dead parametrization made live, F-004 reorder_puzzles' grouping gate moved below the book-exists and membership checks. F-002 (per-row store reads on the order paths) deliberately NOT fixed — see handover.
- [Fix 1] declarations: 1 updated (doc BookManager.reorder_puzzles — error classification and ordering), 2 none
- [Fix 1] pre-gate: 11/11 named tests green
- [Build gate] PASSED (full, 210s; 4504 passed, 0 failed; same single known pre-existing deselection)
- [Design] meta/design/components.md (ArrangeRow level-boundary state) copied worktree → main repo; it is not committed from the worktree and would otherwise die with it
- [AC/EC check] All criteria/constraints ✓ (evidence):
  - AC-257 ✓ demonstrated — TestBookArrange_MoveWithinLevelKeepsOwnerOrder, green (exit 0). Real Flask test client POSTing /book/<id>/arrange-puzzles action=move_up, plus a store-level assertion in both storage modes. E1,E2,M1 → move E2 up → [e2,e1,m1].
  - AC-258 ✓ demonstrated — TestBookArrange_MoveAcrossLevelBoundaryRefused, green. E1,E2,M1,M2 → move M1 up → order unchanged, refusal text "easy, then medium, then hard" rendered, "Moved puzzle up" absent; LevelBoundary raised at the store in both modes.
  - AC-259 ✓ demonstrated — TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, green. Via the real paste-IDs route; asserts order.index(e3) < order.index(m1).
  - EC-029 ✓ demonstrated — test_PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, green in both storage modes. No hypothesis; seeded stdlib random.Random, 25 trials x 14 steps = 350 steps/mode, MIN_STEPS=300 AND a per-kind floor MIN_OF_EACH_KIND=15 over add/remove/moved/refused/book_end asserted INSIDE the test body; oracle is a local RANK table, book_level_order is never called. Edit-sequence half only — the divider/numbering half is CARD-128's by the card's own text.
  - G-1 ✓ demonstrated — union of `git diff --name-only main...HEAD` and `git status --porcelain` (11 paths) contains no migrations/** and no src/nonogram/db/**.
  - G-2 ✓ demonstrated — TestBookLevelOrder_ReadsTheStoredTier green in both modes (stored tier byte-identical after a move); bounded grep of every added line under src/nonogram/admin/ for write/regrade calls matched only a comment. Independently re-derived by the 8h spot-check.
  - G-3 ✓ demonstrated — TestBookAddPuzzles_RefusesBelowFloorWithoutOverride + PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride green; both files absent from the committed and uncommitted diffs, so byte-identical to main — not retargeted or weakened.
  - G-4 ✓ demonstrated (evidence labelled honestly) — the card's named test TestBookRemovePuzzle_KeepsRestOfArrangement does NOT exist in this tree or on main; it is declared only in requirements.yml/trace.yml/CARD-131.md and is CARD-131's to create, so this card had nothing to regress and deleted nothing. Both halves of the behaviour are now directly evidenced: the ARRANGEMENT half by 108 existing removal tests plus EC-029's property (assert_levels_unchanged after 15+ removes per mode), and the TITLES half by a new mutation-checked test added here, TestBookRemovePuzzle_LeavesTheOtherTitlesAlone (both modes) — verified to FAIL when remove_puzzle_from_book is made to clear puzzle_titles wholesale.
  - G-5 ✓ demonstrated — the same 11-path check finds no book_select_puzzles.html, book_finalize.html or book_pdf_generator.py.
- [AC/EC check] ⚠ card defect for the decompose station (NOT blocking this card): G-4 names a `test:` that a LATER card (CARD-131, wave 26) creates. As written the guardrail is unverifiable by its own named test in every wave before CARD-131 lands. Worth rewording to name a test that exists at the time the guardrail is enforced.

---
### Fix pass (cycle 1 minors)

Review cycle 1 scored 9.0 with no critical and no important findings; three of
its four Minor ones are addressed here. F-002 (per-row store reads on the order
paths) is deliberately left alone and handed over.

* **F-001 — the page-break indicator.** The divider in
  `book_arrange_puzzles.html` counted off `loop.index`, which this card's nested
  per-level loop restarts at every heading: a two-level book printed "PAGE 2"
  twice and never "PAGE 3", and a level of three or fewer rows got no divider
  however deep in the book it sat. It now counts off `puzzle.order` — the
  route's 1..n numbering across the whole book — and stops at the book's last
  rendered row rather than at `loop.last`, which is only the last row of its own
  level. Pinned by
  `TestBookArrangeScreen_ShowsTheLevels::test_the_page_break_indicator_counts_the_whole_book_not_each_level`
  and `::test_no_page_break_indicator_follows_the_last_puzzle_of_the_book`.
* **F-003 — dead parametrization.** The unreadable-tier case was parametrized
  over five values and then collapsed every one of them to `None`, so
  `level_rank`'s non-`Tier` branch was never exercised. The value now goes
  through to `tier_of` and into the `level_rank` assertion as it stands.
* **F-004 — the order of `reorder_puzzles`' refusals.** The INV-009 grouping
  gate ran *before* the book lookup and the membership check, so
  `reorder_puzzles("does-not-exist", <ungrouped>)` raised `LevelBoundary` where
  the docstring promised `False`, and an order that was both ungrouped and not
  the book's membership reported the grouping complaint instead of the
  actionable one. The gate now runs last, after "no such book" (still `False`)
  and after the membership `ValueError`; it still runs outside either storage
  branch, because the tier lookup opens sessions of its own. The docstring's
  Returns/Raises now say so. `tests/test_book_manager.py::TestPuzzleReordering`
  gained a `graded_puzzles` helper and four store-backed cases — the previous
  ones used placeholder ids that resolve to no row, so every tier was `None` and
  the gate could never fire.

* **G-4, the titles half.** The gate found the arrangement half pinned (EC-029's
  property) but nothing asserting that removing one puzzle leaves the *others'*
  custom titles intact, so `tests/test_book_level_order.py` gained
  `TestBookRemovePuzzle_LeavesTheOtherTitlesAlone::test_removing_one_titled_puzzle_keeps_the_rest_and_their_titles`
  (both storage modes, real `set_puzzle_title`). Checked against an injected
  bug: making `remove_puzzle_from_book` clear `puzzle_titles` wholesale in each
  branch fails it in both modes (`assert [None, None, None] == ['First light',
  ...]`); the production file was restored unchanged. Noted while doing so and
  *not* fixed here: only the DB branch drops the removed id's own title entry —
  the in-memory branch never touches `puzzle_titles` — so a re-added puzzle
  silently regains its old title in legacy mode. Handed over, not pinned.

Renders regenerated in `~/Documents/nonogram-reviews/CARD-126/` on a nine-puzzle
book (four easy, three medium, two hard) so the corrected numbering is visible:
the dividers now read PAGE 2 after row 3 and PAGE 3 after row 6, with none after
row 9.

- [Commit] 00ad374 fix(admin): CARD-126 review round — page breaks count the whole book (4 files, 210+/14-); first commit 7c594c7 intact, no amend, no rebase; meta/ not committed
- [Handover] For CARD-128 (dividers + the printing half of AC-260): book_plan.book_levels returns [(Tier|None, [ids])] for NON-EMPTY levels only — that is the shape one-divider-per-level needs. The interior is now handed a GROUPED puzzle_ids, so any test assuming submission order through a book route needs the one-line adjustment EC-034's property already took (tests/property/test_book_export_interior.py::_as_the_interior_prints_them).
- [Handover] A re-grade of a puzzle already in a book reproduces the legacy-mixed posture: tier is read at read time (correct per ADR-0033/R1), so re-grading silently makes that book's stored order ungrouped until the next move normalises it. Not reachable today (nothing updates difficulty_tier after creation), but CARD-128 should know before it routes the PDF through book_levels.
- [Handover] Pre-existing, NOT this card's: remove_puzzle_from_book prunes puzzle_titles in the DB branch but not the in-memory branch (book_manager.py ~1058-1071 vs ~1101-1105), so in memory mode a removed-and-re-added puzzle silently regains an old title. Found by the G-4 titles test; left unfixed because it is a production behaviour change outside this card. Natural owner: CARD-131.
- [Handover] Review F-002, not fixed by choice: _tier_of resolves the whole membership one store read at a time on every order operation (a move on a default-plan book costs ~150 sessions where the old code did one UPDATE), and the arrange route reads every row twice. Harmless on local single-user SQLite; the fix is memoisation across three call paths.
- [Handover] tests/README.md documents 4 of 109 test files and is many waves stale — flagged by the docs step, worth its own card rather than per-card patching.


- [Done] rebased onto main 0684b34 (after CARD-123), full suite on the rebased tree with a private --basetemp: only the pre-existing e2e failure. Merged ea35a7f (--no-ff). Deferral scan: 0 hits. SCOPE+ tests/property/test_book_export_interior.py (verified not weakened) and meta/design/components.md. Handover pushed to CARD-128 and CARD-131.
