# CARD-125: The pair-aware layout call — two puzzles, one shared cell in [7.0, 7.5] mm, or no pairing

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/125-pair-aware-layout
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-15 (COMP-007 half of FR-040)
**Idea:** —
**Wave:** 22
**Depends on:** CARD-114
**Touches:** src/nonogram/export/layout.py, src/nonogram/export/__init__.py, tests/test_layout_two_up.py, tests/property/test_book_two_up.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-09-22T17:35:05Z
**Closed:** 2026-09-22T19:16:59Z
**Actual:** 0.2d
**Merge commit:** b106796
**Blocked by:** —

## What to implement

This card is the first implementation of ADR-0036's 2026-09-22 clarification ("Two-up
pages"). FR-040's `_meta` left the API shape open, and this card settles it.

1. **`compute_pair_layout(first, second, page_spec) -> PairLayout | None`** in
   `export/layout.py`. `first` and `second` are each `(row_clues, column_clues)`.
   - The shared cell is the **largest** cell, capped at the spec's flat cap (7.5 mm),
     at which (a) the combined drawing height of both puzzles (grid rows plus
     column-clue rows of each) × cell, plus **one band per puzzle**, fits the usable
     height (trim − top − bottom), and (b) **each** puzzle's drawing width (grid columns
     plus row-clue columns) × cell fits the usable width. Clue depths are the real
     depths (TERM-021).
   - It returns `None` (no pairing) when that cell is below the **7.0 mm two-up
     minimum** (a named constant).
   - Otherwise it returns both slot `Layout`s at that one cell, with their page
     positions: the **earlier puzzle in the upper slot**, the upper slot's drawing top
     edge at top margin + band (the same fixed row as a single page, EC-022), and the
     lower slot below its own band. The slots must not overlap.
   - It is only valid for a portrait-only, flat-cap spec. Any other spec raises
     `ValueError`: the default A4 spec never pairs.
2. The single-puzzle `compute_layout` is **unchanged**. A single puzzle keeps using it
   (ADR-0036 clarification).
3. It reuses the existing private helpers (`_gutter_depth`, `_axis_lines`,
   `_rule_widths`, clue placement) so strokes and every-5th rules match the single-page
   book path. Do not add a second implementation of cell fitting.
4. Pin the arithmetic of AC-242..AC-247 at layout level here: 7.5, 7.39, 7.16 mm,
   `None` at 6.95 and 6.57 mm, and `None` on the width failure. CARD-127 re-asserts
   them on the PDF.

If writing this reveals that ADR-0036's clarification cannot be met as worded (for
example, the fixed top edge conflicts with the combined-height rule), stop and escalate
to the architect station. Do not reshape the rule here.

## Acceptance criteria

_Layout-level halves of FR-040's criteria (the PDF-level tests are CARD-127):_

- **AC-242** (INV-010) — given a Book 1 profile book whose order starts with two easy 10x10 puzzles, each with 4-deep row- and column-clue gutters (combined drawing height 28 cells), when the book PDF is generated, then both puzzles print on one page at a 7.5 mm shared cell (the page fit of 8.44 mm capped at the standard cell).
  *test:* `TestPairLayout_TwoTenByTensShareAtStandardCell`
- **AC-243** (INV-010) — given a Book 1 profile book whose order starts with two easy 12x12 puzzles, each with 4-deep row- and column-clue gutters (combined drawing height 32 cells), when the book PDF is generated, then both puzzles print on one page at a 7.39 mm shared cell (+/- 0.05 mm; 236.35 mm over 32 cells).
  *test:* `TestPairLayout_TwelvePairAtSevenThirtyNine`
- **AC-244** (INV-010) — given a Book 1 profile book whose order has an easy 15x15 puzzle with a 5-deep column-clue gutter followed by an easy 10x10 puzzle with a 3-deep column-clue gutter (combined drawing height 33 cells), when the book PDF is generated, then both puzzles print on one page at a 7.16 mm shared cell (+/- 0.05 mm) — at or above the 7.0 mm two-up minimum.
  *test:* `TestPairLayout_JustAboveTwoUpMinimum`
- **AC-245** (INV-010) — given the same book but the 15x15 puzzle's column-clue gutter is 6 deep (combined drawing height 34 cells, 6.95 mm shared cell), when the book PDF is generated, then the two puzzles print on two separate pages.
  *test:* `TestPairLayout_JustBelowTwoUpMinimumIsNone`
- **AC-246** (INV-010) — given a Book 1 profile book whose order has an easy 15x15 puzzle with a 5-deep column-clue gutter followed by an easy 12x12 puzzle with a 4-deep one (combined 36 cells, 6.57 mm), when the book PDF is generated, then the two puzzles print on two separate pages.
  *test:* `TestPairLayout_FifteenPlusTwelveIsNone`
- **AC-247** (INV-010) — given a Book 1 profile book whose order has an easy 22-wide x 10-tall puzzle with a 6-deep row-clue gutter (28 cells across, at most 6.92 mm on the 193.7 mm usable width) followed by an easy 10x10 puzzle with 3-deep gutters, when the book PDF is generated, then the two puzzles print on two separate pages — the pair fits the height but the wide puzzle's drawing does not fit the width at 7.0 mm.
  *test:* `TestPairLayout_WidthFailureAtTwoUpMinimumIsNone`

## Engineering constraints

- **EC-028** (consistency, NFR-008) — For any two puzzles of 10..30 cells per side, any clue depths and any stored trim and margins, a two-up page's shared cell lies in [7.0, 7.5] mm, both puzzles print at that one cell, and both drawings with their two 12 mm bands lie inside the usable area without overlapping — and a pair whose largest fitting cell is below 7.0 mm is never put on one page.
  *test:* `PropertyTest_BookTwoUp_SharedCellInRangeAndDrawingsFitUsableArea`
- EC(ADR-0036/R1): adding the pair-aware call leaves `compute_layout`'s default path byte-identical.
  *test:* `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` (CARD-113) stays green
- EC(ADR-0037/R2): both slots use the book strokes (thin ≥ 0.25 mm, heavy = 2 × thin, black) at the shared cell.
  *test:* `PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin` (CARD-114 — add two-up cases)

## Guardrails

- G-1: CLI and web A4 output stay byte-identical (CON-019, ADR-0036/R1). test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden, PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry.
- G-2: `compute_layout`'s signature and single-puzzle behaviour are unchanged. The pair call is additive (Increment 15 Rollback: "nothing is stored, so reverting restores one puzzle per page").
- G-3: Do not edit `src/nonogram/admin/**`, `src/nonogram/db/**` or `migrations/**`. The walk that decides which neighbours to offer is CARD-127 (ADR-0036/R2), and nothing is stored.
- G-4: Do not edit `tests/fixtures/a4_golden/**`. It is CARD-113's tripwire.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as … (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it … (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from … (check: review-lens)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dimensions from one. (check: review-lens)
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
- CON-019 — Adding book-specific page geometry (a trim, margins, a title band, a portrait-only rule, the 7.5 mm standard cell) never changes the CLI's or the web UI's exports: for any generation request the PNG, SVG and PDF files … (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
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

- **FR:** FR-040
- **NFR:** NFR-008
- **CON:** CON-019
- **ADR:** ADR-0036, ADR-0037
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Failure matrix

No failure-bearing boundaries: `compute_pair_layout` is a pure, total geometry
function (no I/O, no clock, no concurrency, no retries, no shared state), so
there is no dependency to time out, retry or degrade. The poison-input rows
that do apply, with their declared behaviour:

| Input | Behaviour |
|---|---|
| `page_spec` not a `PageSpec` | `TypeError` (same as `compute_layout`) |
| `page_spec` without a parity (a drawing-sized spec, e.g. `DEFAULT_PAGE_SPEC`), or with the comfort-curve cap | `ValueError` — the default A4 spec never pairs; a spec with parity is portrait-only by `PageSpec`'s own invariant |
| `first`/`second` not a `(row_clues, column_clues)` pair | `ValueError` |
| a clue set pair with rows but no columns (or the reverse) | `ValueError`, the same rule and message shape as `compute_layout` |
| valid inputs, largest fitting cell < 7.0 mm (height or width) | `None` — no pairing; never an exception |
| valid inputs, the spec's usable height cannot hold even the two bands | `None` — no cell fits at all, so no pairing |
| valid inputs, cell in [7.0, cap] | a `PairLayout` whose own `__post_init__` re-checks one shared cell, both slots placed, slots disjoint and each drawing inside its slot |

Contract: `None` is a *verdict* about a valid pair (they do not fit two-up);
an exception is a *caller bug* (wrong spec kind or malformed clues). CARD-127's
walk treats `None` as "print alone" and never catches the exceptions.

## Worktree notes

—

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)
**Summary (2026-09-22).** `compute_pair_layout(first, second, page_spec) -> PairLayout | None`
added to `export/layout.py` as one contiguous block appended after `compute_layout`
(plus three `__all__` entries and `replace` added to the `dataclasses` import);
`PairLayout` and `TWO_UP_MIN_CELL_MM` re-exported from `export/__init__.py`.
`compute_layout` is byte-for-byte untouched (G-1/G-2; golden and CLI-identity tests green).
Commit f9ace15 on card/125-pair-aware-layout. The ADR clarification was met as worded,
with no blocker: the fixed top edge (upper drawing at top + band) and the combined-height
rule are consistent, because (rows1 + rows2) × cell + 2 × band ≤ trim − top − bottom
leaves the lower slot room above the bottom margin.
Measured at layout level on Book 1 (odd and even give the same values):
AC-242 7.5 mm (fit 8.44), AC-243 7.3859 mm, AC-244 7.1621 mm, AC-245 None (6.95),
AC-246 None (6.57), AC-247 None (width: 193.675 / 28 = 6.917; height alone 9.09).
- STRUCTURE: `PairLayout(upper: Layout, lower: Layout, cell_mm: float)`, a frozen value
  object whose `__post_init__` refuses a pair unless both slots are placed pages at one
  shared cell, on the same trim and parity, with cell ≥ 7.0, slots disjoint
  (`upper.page.usable_bottom <= lower.page.usable_top`) and each `page.fits`. Why: the
  caller never re-checks EC-028, and a hand-built invalid pair can't exist.
- STRUCTURE: slot positions are expressed through each slot's own `PagePlacement`, and no
  new placement type was added. Across, it is the page's usable width (each drawing is
  centred on it, FR-032). Down, `usable_top` is where the slot's band starts and
  `usable_bottom` is where the slot ends. Why: the renderers draw each slot exactly like
  a single placed page, and `header_band(slot)` returns each slot's own 12 mm band
  unchanged, so CARD-127 places neither bands nor lines itself (ADR-0036/R2).
- STRUCTURE: the upper slot's band starts at the top margin, so its drawing sits on the
  single page's fixed row (EC-022, AC-252). The lower drawing ends at the bottom margin,
  so the spare height falls between the slots. Why: if the slots were stacked flush, the
  lower band's text would sit midway between two drawings and read as belonging to either
  one. With the spare between the slots, each band hugs its own puzzle. For the tight
  pairs (7.39 / 7.16) the spare is about 0 anyway. [Owner eyeball: see the proofs.]
- STRUCTURE: the pair is fitted with no second fitting implementation. The shared cell is
  `_placed_cell_mm(max(across1, across2), down1 + down2, page_spec=replace(spec,
  band_mm=2 × band))`: the single page's exact fit of one combined drawing on the same
  spec with a second band reserved. Slots are built by `_slot_layout` from
  `_gutter_depth`, `_boundaries`, `_rule_widths`, `_axis_lines` and
  `_place_row_clues`/`_place_column_clues`. At the same cell, the upper slot's lines,
  clues and strokes equal `compute_layout`'s (pinned by a test).
- STRUCTURE: the 7.0 mm constant is `TWO_UP_MIN_CELL_MM = 7.0`. It is a module constant,
  not a `PageSpec` field, because it is the owner's rule for every book and not a property
  of a trim. It is compared exactly (as a Fraction).
- STRUCTURE: the flat-cap / portrait-only validation is phrased as "a placed page (parity
  set, which `PageSpec` already forces to be PORTRAIT_ONLY) with a flat cap". Any other
  spec raises ValueError ("... never pairs"), and a non-PageSpec raises TypeError. The
  default A4 spec raises. A portrait-only spec with no parity also raises, because a pair
  has page positions and so needs a placed page.
- STRUCTURE: `None` means valid inputs that don't fit two-up (cell < 7.0 mm, or the usable
  height can't hold two bands). An exception means a caller bug. See the Failure matrix.
- SCOPE: `tests/property/test_book_layout.py` was not edited. The ADR-0037/R2 two-up
  cases are a sibling test,
  `test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_two_up`
  in `tests/property/test_book_two_up.py`.
- Tests: `tests/test_layout_two_up.py` (29 tests) and `tests/property/test_book_two_up.py`
  (3 property tests: EC-028 over 3000 seeded pairs with ≥500 paired, ≥500 declined and
  ≥100 at the cap; a swap-symmetry verdict test; the two-up strokes test). The full suite
  (4086 collected) is green except the known deselect.
- Proofs (not committed): `~/Documents/nonogram-reviews/CARD-125/`, with
  `two-up_{10x10+10x10,12x12+12x12,15x15+10x10}_p{3-odd,4-even}_*.png` and all six pages
  in `two-up_proofs.pdf`. They are drawn with `png._draw_grid`/`_draw_clues` per slot,
  with the band text from `header_band(slot)`. The faint blue frame is the usable area, a
  proof guide only. Script:
  `/private/tmp/claude-501/.../scratchpad/card125_proofs.py`.
- [Handover] CARD-127: call `layout.compute_pair_layout((rows_a, cols_a), (rows_b,
  cols_b), book_spec_for_this_page_parity)`, with the earlier puzzle first. `None` means
  print them on separate pages (use `compute_layout` for each). A `PairLayout` gives you
  `.upper` / `.lower` as full-trim `Layout`s. Draw both onto one trim-sized page exactly
  as a single placed page is drawn (grid and clues), and draw each band from
  `header_band(slot)` ("Puzzle N · Tier"). The call does NOT decide: tier equality,
  adjacency, the in-order walk (EC-027/INV-010), puzzle numbers, band text, the page's
  parity (pass the spec for the page's actual parity), or any PDF composition. It never
  reorders. The current `png.render_image` draws only one layout, so the two-slot page
  composition is yours.
- [Handover] CARD-133: added in `layout.py` `"TWO_UP_MIN_CELL_MM"`, `"PairLayout"`,
  `"compute_pair_layout"` to `__all__`, `replace` to the `from dataclasses import` line,
  and one block at the end of the file (after `compute_layout`) headed "# Two-up pages
  (FR-040 ...)": `TWO_UP_MIN_CELL_MM`, `PairLayout`, `compute_pair_layout`,
  `_pair_member`, `_slot_layout`. No existing line was reordered or reformatted. Put
  the answer-tile block after it, or reuse `_slot_layout`'s pattern for placing a
  Layout at a given cell and origin.
- [Scope] src/nonogram/export/__init__.py, src/nonogram/export/layout.py, tests/property/test_book_two_up.py, tests/test_layout_two_up.py
- [Build gate] impact underivable (python-pro without pytest-testmon) — full suite
- [Build gate] PASSED (full, 146s) — 4059 passed, 26 skipped, 1 deselected (known pre-existing e2e TestFlow2BatchImageUpload::test_size_configuration_applied)
- [Visual] not a UI card (no Design context, Skill python-pro); no Makefile run target — review static-only
- [Scope gate] in_scope — 4/4 changed files within Touches; no guarded-glob hits (G-3 admin/db/migrations, G-4 a4_golden)
- [Review 1/3] Score: 9.0 — crit: 0, imp: 0
- [Review 1/3] Score: 9.0 ✓ threshold reached + no critical/important (Minor: F-001 _slot_layout duplicates compute_layout placed-branch assembly; F-002 lower slot anchored to bottom margin — unspecified by FR-040/ADR-0036, heavy bottom rule half-stroke into margin; OOS F-003)
- [Review sync] 1 report(s) → meta/review/
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0036/R1, ADR-0037/R2, CON-019)
- [AC/EC check] Failed: EC(ADR-0037/R2) ⚠ partial — widths hold on both slots (102-case sibling test) but 'black' not observed for two-up slots and height-fit cells not checked against the 0.25 mm floor; AC-242..247, EC-028, EC(ADR-0036/R1), G-1..G-4 ✓ demonstrated
- [Fix 1] FIXED F-EC037 (two-up stroke width at height-fit cells + black measured off rendered pixels), FIXED F-001 (upper slot == compute_layout at the shared cell); pre-gate: 3/3 named tests pass
- [Fix 1] declarations: 0 updated, 1 confirmed (Failure matrix re-read against compute_pair_layout), 2 doc (card EC test pointer + Worktree notes tests inventory)
- [Build gate] PASSED (full, 146s) — 4062 passed, 26 skipped, 1 deselected (post-fix)
  cases are sibling tests in `tests/property/test_book_two_up.py`:
  `..._StrokesAtLeastQuarterMillimetreHeavyTwiceThin_two_up` (the cap sets the cell),
  `..._two_up_fitted` (the height fit sets it: cells strictly below the cap, varied
  shapes, margins, bands and both parities, ≥350 fitted and ≥100 at-cap cases) and
  `..._two_up_pixels` (the "black" clause: both slots of 8 pairs drawn on a trim-sized
  canvas with `png._draw_grid`/`_draw_clues` — `render_image`'s own body, which cannot be
  called for a slot because it re-fits its layout from clues + spec — then probed for runs
  of ink exactly as CARD-114's `..._pixels` probes a single page).
  (6 property tests: EC-028 over 3000 seeded pairs with ≥500 paired, ≥500 declined and
  ≥100 at the cap; a swap-symmetry verdict test; the three two-up strokes tests above;
  and `PropertyTest_BookTwoUp_UpperSlotIsTheSinglePageAtTheSharedCell`, which holds
  `_slot_layout`'s upper slot against `compute_layout(*first, spec with cap = the shared
  cell)` — lines, clues, strokes and drawing edges — over ≥400 seeded pairs, exactly when
  the cell is the cap and within one pixel when the height fit set it, since only then is
  the re-fitted pitch a `float` round-trip of the pair's exact fraction). The full suite
- [Review 2/3] Score: 9.0 — crit: 0, imp: 0 (confirmation mode; F-001 resolved & mutation-confirmed, F-EC037 resolved; F-002/F-003 carried non-gating; new Minor F-004 clue_font_size uncompared, F-005 pixel probe can index past canvas on a near-zero bottom margin)
- [Review 2/3] Score: 9.0 ✓ threshold reached + no critical/important
- [Review sync] 2 report(s) → meta/review/
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, CON-011, ADR-0037/R2 — the last re-derived at full depth with killed INK and heavy-factor mutants)
- [8h spot-check] noted: the 0.25 mm thin floor is never the binding term at a >= 7.0 mm cell, so two-up cases cannot distinguish floor from ratio; CARD-114's 4.0 mm-cap case pins that mechanism
- [Fix 2] FIXED F-004 (clue_font_size now compared upper-vs-single; mutant killed), FIXED F-005 (fitted-corpus bottom margin floored at 2.0 mm + canvas-bounds assertions); pre-gate: 2/2 named tests pass
- [Fix 2] declarations: 0 updated, 0 confirmed, 2 doc (test docstrings re-derived from the code); src/ untouched
- [Build gate] PASSED (full, 145s) — 4062 passed, 26 skipped, 1 deselected (post-minor-fix)
- [AC/EC check] All criteria/constraints ✓ (evidence):
- AC-242 ✓ demonstrated — TestPairLayout_TwoTenByTensShareAtStandardCell::test_the_shared_cell_is_the_standard_cell PASSED; cell_mm == 7.5 on both slots (8.44 page fit capped)
- AC-243 ✓ demonstrated — TestPairLayout_TwelvePairAtSevenThirtyNine PASSED; == 236.35/32 (7.39 ±0.05)
- AC-244 ✓ demonstrated — TestPairLayout_JustAboveTwoUpMinimum PASSED; == 236.35/33 (7.16), >= TWO_UP_MIN_CELL_MM
- AC-245 ✓ demonstrated — TestPairLayout_JustBelowTwoUpMinimumIsNone PASSED; None on both parities (236.35/34 ≈ 6.95)
- AC-246 ✓ demonstrated — TestPairLayout_FifteenPlusTwelveIsNone PASSED; None (236.35/36 ≈ 6.57)
- AC-247 ✓ demonstrated — TestPairLayout_WidthFailureAtTwoUpMinimumIsNone PASSED; None in both orders on width (193.675/28 ≈ 6.92) with a passing control case
- EC-028 ✓ demonstrated — PropertyTest_BookTwoUp_SharedCellInRangeAndDrawingsFitUsableArea PASSED; 3000 seeded cases, in-test minimums paired>=500 / declined>=500 / at_cap>=100, independent mm oracle
- EC(ADR-0036/R1) ✓ demonstrated — TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden + a4_golden suite PASSED (130); tripwire files unmodified
- EC(ADR-0037/R2) ✓ demonstrated — ..._two_up (102 cap-bound) + ..._two_up_fitted (600 cases, 444 below cap, both parities) + ..._two_up_pixels (16 slot probes, black asserted against literal (0,0,0)) + CARD-114's original PASSED. Stated limitation: at a cell >= 7.0 mm the 1/30 ratio already yields 3 px, so the 0.25 mm floor is never the binding term in two-up cases; its mechanism stays pinned by CARD-114's small-cap cases
- G-1 ✓ demonstrated — golden + CLI/web byte-identity tests green; neither test file in the diff
- G-2 ✓ demonstrated — compute_layout AST source sha256 identical between main and worktree (644fc010...); layout.py diff purely additive after it
- G-3 ✓ demonstrated — changed non-meta files (4) grep clean against admin/, db/, migrations/
- G-4 ✓ demonstrated — same set grep clean against tests/fixtures/a4_golden/
- [Docs] src/nonogram/export has no README — its package docstring is the directory doc and the implementation updated it (PageSpec/PairLayout paragraph); tests/README.md is a wave-1 document that indexes neither layout nor property tests, so nothing there went stale. No README change needed.
- [Commit] 5a8d0f6 test(export): property-test the two-up stroke gate on both slots (CARD-125) — 1 file, tests/property/test_book_two_up.py; parent f9ace15 (implementation). Nothing under meta/ committed.

- [Done] rebased onto main 2dd96af (after CARD-115), full suite on the rebased tree: only the pre-existing e2e failure. Merged b106796 (--no-ff). Deferral scan: 0 hits. Handover notes pushed to CARD-127 and CARD-133; F-002 (bottom-anchored lower slot, unrecorded in FR-040/ADR-0036) queued to raw-requirements for the architect.
