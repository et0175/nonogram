# CARD-203: The solved-page caption sits closer to the puzzle and right-aligns with its grid

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/203-solved-caption-position
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-CARD-203
**Source:** owner's Google Doc "Nonograms - Print layout1", 2026-10-08 (item 5: move the lower caption closer to the puzzle and right-align it)
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_solved_page.py, tests/helpers/book_corpus.py, tests/fixtures/book_baseline_card203.json
**Review score:** —
**Started:** 2026-10-10T04:04:25Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code in full).**

`BookPDFGenerator.solved_puzzle_page` (`src/nonogram/admin/book_pdf_generator.py:1972-2150`,
CARD-197's full-page solved-answer renderer, wired into the book's real answer key by
CARD-198 — this is the **only** place in the codebase that draws a puzzle caption today;
ADR-0037/R1 is explicit that a book's unsolved puzzle page never prints the picture's title,
only the answer/solution page does) draws its caption at step 8 (lines 2111-2150):

```python
caption_font_points = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
caption_font_size = type_px(caption_font_points, self.dpi)
caption_font = _band_font(caption_font_size)
ascent, descent = caption_font.getmetrics()
line_height = ascent + descent
slack = placement.usable_bottom - placement.drawing_bottom
if slack >= line_height:
    caption = answer_caption(puzzle_number, title)
    draw.text(
        (
            (placement.drawing_left + placement.drawing_right) / 2,
            (placement.drawing_bottom + placement.usable_bottom) / 2,
        ),
        caption,
        font=caption_font,
        fill=INK,
        anchor="mm",
    )
```

Today the caption is drawn with `anchor="mm"` (horizontal- and vertical-middle) at:

- **x** = the midpoint of `placement.drawing_left`/`placement.drawing_right` — horizontally
  **centred** under the grid.
- **y** = the midpoint of `placement.drawing_bottom`/`placement.usable_bottom` — vertically
  **centred in the whole slack** below the drawing, which can put real visual distance
  between the grid and its caption whenever the page has a lot of bottom slack (a small or
  fitted grid on a page sized for a bigger one — `book_page_spec.BOOK1_PROFILE`'s flat 7.5 mm
  cell cap means most puzzles are cap-bound, i.e. have slack, per CARD-197's own notes).

`export/layout.py`'s `Placement` dataclass (`src/nonogram/export/layout.py:608-624`)
confirms the field semantics directly from its own docstring: `drawing_right: The grid's
right edge.` (line 622) — this is the puzzle's own right edge, not `usable_right` (the
page's outer margin), so it is the correct anchor for "align it by the right side with the
puzzle."

**Target.** Two changes to step 8 only, both inside `solved_puzzle_page`:

1. **Right-align the caption with the grid's own right edge.** Change `anchor="mm"` to
   `anchor="rm"` (right, middle) and the x coordinate from the drawing-left/right midpoint to
   `placement.drawing_right` alone. `draw.text`'s `"rm"` anchor places the text's right edge
   at the given x and its vertical centre at the given y (Pillow anchor semantics: first
   letter = horizontal, second = vertical; `"r"` = right), so the caption's right edge lines
   up with the grid's right edge exactly as `answer_caption`'s own sibling, the title band,
   already does **not** (the band is still centred — this card does not touch the band, only
   the caption, per the owner's doc wording, which names only "the lower caption").
2. **Move the caption closer to the drawing, replacing "centred in the whole slack" with a
   small fixed gap above the caption's old position.** Reuse `export.layout.ANSWER_TILE_GAP_MM`
   (`src/nonogram/export/layout.py:1978`, literally `2.0` — already the project's own constant
   for "the gap around an answer caption area," used today in the OLD packed answer-key tile
   geometry's row/column spacing math, `book_answer_key.py`'s packing arithmetic) as the fixed
   gap, rather than inventing a new unnamed mm value — reuse over invention, the same
   discipline CARD-197's own caption text reused `answer_caption` instead of inventing a third
   wording. Convert it to device pixels the same way this method already converts a physical
   mm measurement that is **not** a type size — a plain `round(mm / 25.4 * self.dpi)`, the
   same formula this file used for the caption's own font size before CARD-197's review cycle
   2 replaced it with the already-existing `type_px()` call for a type size specifically
   (CARD-197's Worktree notes, [Fix 1], F-002) — `type_px()` itself takes **points**, not mm,
   so it is not the right call for a physical gap; a small local helper or an inline
   `round(ANSWER_TILE_GAP_MM / 25.4 * self.dpi)` is the honest equivalent. Name it clearly
   (e.g. `gap_px`) so the arithmetic below reads plainly.

   The new y coordinate (anchor `"rm"`'s vertical centre) is
   `placement.drawing_bottom + gap_px + line_height / 2` — i.e. the caption's own text band
   (height `line_height`) starts `gap_px` below the grid and ends `gap_px + line_height`
   below it, instead of being centred across however much slack a page happens to have.

3. **The omission arithmetic changes to match.** Today's guard is `slack >= line_height`
   (the caption fits if the whole slack is at least one line tall). With a fixed gap inserted
   before the line, the real requirement is `slack >= gap_px + line_height` — the caption
   needs room for the gap **and** the line, not the line alone. Get this right: a page whose
   slack is, say, exactly `line_height` (today's boundary case, AC-6's `_NO_SLACK_SHAPE` or
   near it) now has too little room once `gap_px` is added, and must omit the caption rather
   than draw it overlapping or past `usable_bottom` — this is a real, narrow widening of the
   omission case versus today, not a cosmetic rename of the same condition, and needs its own
   boundary test (see AC-4 below).

**What is explicitly unchanged:** the caption's own text (`answer_caption(puzzle_number,
title)`, CARD-197/198's existing wording, "Puzzle N — Title"), its font (`_band_font` at
`ANSWER_TEXT_FONT_MM`, exactly 10 pt, the CON-020 floor), the title band above the drawing
(`_set_band`, still centred — the doc's ask names only "the lower caption"), and every other
step of `solved_puzzle_page` (fill, `_stroke_drawing`, the gray boundary marks, `_write_clues`).
This card is scoped to steps 8's two draw-coordinate lines and the one guard condition beside
them — nothing else in the method changes.

## Acceptance criteria

- **AC-1** (happy, right alignment): *Given* a cap-bound puzzle's solved page with a resolved
  title, *when* the caption is rendered, *then* its rightmost ink column sits at
  `placement.drawing_right` (within normal antialiasing tolerance, the same tolerance the
  existing CARD-197 tests already use for ink-edge checks) and never past it — the caption's
  right edge lines up with the grid's right edge, not the page's centre.
  *test: TestBookSolvedPage_CaptionRightAlignedWithTheGrid (in tests/test_book_solved_page.py)*
- **AC-2** (happy, closer to the drawing): *Given* the same page, *when* the caption's
  vertical position is read, *then* it sits a small fixed gap (`ANSWER_TILE_GAP_MM` converted
  to this page's device pixels) below `placement.drawing_bottom`, not centred across the full
  slack to `placement.usable_bottom` — on a shape whose slack is much larger than one line's
  height plus the gap, the caption's ink stays near the top of the slack band, not its middle.
  *test: TestBookSolvedPage_CaptionMovedCloserToTheDrawing*
- **AC-3** (boundary, still inside the usable area): *Given* a cap-bound page, *when* the
  caption is rendered at its new position, *then* every caption pixel still sits strictly
  inside the usable area (never inside the trim margin, never overlapping the grid) — the
  same invariant the existing `test_the_caption_is_drawn_inside_the_usable_area_only` already
  asserts, re-verified at the new coordinates.
  *test: TestBookSolvedPage_CaptionMovedCloserToTheDrawing (same class as AC-2, or the existing test re-run unedited if it still holds at the new position — confirm which during implementation)*
- **AC-4** (boundary, the widened omission case): *Given* a puzzle whose slack is at least
  `line_height` but less than `gap_px + line_height` — too little room for the new gap plus
  the line, though enough for the line alone under the OLD guard — *when* the page is
  rendered, *then* the caption is omitted (no caption pixel anywhere), not drawn overlapping
  or clipped past `usable_bottom`.
  *test: TestBookSolvedPage_CaptionOmittedWhenNoSlack::test_the_narrow_gap_only_boundary_is_also_omitted (new case added to the existing AC-6 class, since it is the same declared behaviour — omit rather than overflow — at a boundary this card's own arithmetic change newly exposes)*
- **AC-5** (negative, existing AC-6 preserved): *Given* the existing `_NO_SLACK_SHAPE` fixture
  (zero or negative slack), *when* the page is rendered, *then* the caption is still omitted
  and the rendered page is still identical whatever the title — `TestBookSolvedPage_CaptionOmittedWhenNoSlack`'s
  three existing tests pass unedited (this card only widens the omission boundary, it does not
  narrow it — a shape that already omitted its caption before this card still omits it after).
  *test: TestBookSolvedPage_CaptionOmittedWhenNoSlack (existing, unedited)*
- **AC-6** (negative, everything else unchanged): *Given* any solved page, *when* every other
  mark is compared against the pre-card rendering — fill, `_stroke_drawing`'s rules, the gray
  boundary marks, clue digits, and the title band's own text/position — *then* none of it
  differs; only the caption's x/y coordinates and the omission boundary moved.
  *test: TestBookSolvedPage_SameGeometryAsTheUnsolvedPage, TestBookSolvedPage_GrayGridlinesBetweenFilledCells, TestBookSolvedPage_TitleBandMatchesBandIdentity (all existing, unedited — confirms no collateral drift)*

## Guardrails

- G-1: The caption's own text (`answer_caption`'s "Puzzle N — Title" wording) and font
  (`_band_font` at the `ANSWER_TEXT_FONT_MM` / CON-020 10 pt floor) are unchanged — this card
  moves the caption, it does not restyle or reword it.
- G-2: The title band (`_set_band`, "Puzzle N · Tier", still centred above the drawing) is
  untouched — the owner's doc names only "the lower caption"; the band is a separate piece of
  type this card does not move.
- G-3: `_stroke_drawing`, the gray-boundary marks (CARD-197), `_write_clues` and the solved-cell
  fill are byte-identical to before this card — `tests/test_book_solved_page.py`'s existing
  AC-1/AC-2/AC-3/AC-9 classes (clue placement, gray gridlines, same-geometry-as-unsolved) pass
  unedited.
- G-4: No change to `_two_up_page`, the unsolved `puzzle_pages` path, or any other caller of
  `_set_band`/`_write_clues`/`_stroke_drawing` — this card edits exactly one method's step 8.
- G-5: Page count and parity (FR-043/INV-013, `InteriorStream.answer_page_count`,
  `interior_page_count`) are unaffected — this card changes pixels on existing pages, not how
  many pages exist or what position each occupies.

## System contract

_Assembled 2026-10-08 by `system_rules.py --card CARD-203` (53 rules; identical rule-id set to CARD-197/198's own assembly — same Touches/Architecture-context scope). A projection — fix the source artifact, never this list._

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
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correc… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a n… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decode… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a paramet… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, whos… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)
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

- **FR:** none directly — the caption is CARD-197/198's own addition, itself not yet
  formalised into an FR (see CARD-197's own Architecture context: "none yet, by design"). This
  card is a refinement of that same not-yet-formalised layout, same footing.
- **ADR:** ADR-0037/R1 (title/caption only on the answer page — unaffected, this card only
  repositions the caption, it does not add it to a new page kind), ADR-0036/R2 (layout
  functions place, nothing else does — this card's new coordinates are still derived entirely
  from `Placement` fields the layout already computed; `ANSWER_TILE_GAP_MM` is a constant, not
  a new fitting computation).
- **CON:** CON-020 (10 pt floor — unaffected, same font/size).
- **Components:** COMP-007 (layout functions consumed, read-only), COMP-009 (the one edited
  method lives here, `src/nonogram/admin/book_pdf_generator.py`).
- **Trace:** meta/architecture/trace.yml — not updated by this card (no FR exists yet to trace
  against, same as CARD-197/198's own position).

## Design context

- **Output:** the solved answer page's caption (CARD-197/198), repositioned — right-aligned
  with the grid, closer to it.
- **Owner-visible default this card picks (needs confirmation before merge):** the exact size
  of the "closer" gap. This card reuses `export.layout.ANSWER_TILE_GAP_MM` (2.0 mm) — an
  existing project constant already meaning "the gap around an answer caption area" in the old
  packed-key geometry — rather than inventing a new, unconfirmed number. This is this card's
  own reading of "closer," not an owner-specified value (the same kind of unconfirmed-default
  flag CARD-198 raised for its own three open questions) — the owner should see the render and
  confirm the gap reads as "closer" without feeling cramped against the grid.
- **Renders:** ~/Documents/nonogram-reviews/CARD-203/ (owner visual check before merge) — the
  same cap-bound sample puzzle CARD-197's own render set used (a shape with real slack below
  the drawing), rendered both ways: today's centred caption and this card's right-aligned,
  closer caption, side by side, so the owner can confirm the gap size and the right-alignment
  read correctly before this ships.

## Worktree notes

- [Origin] Owner's Google Doc "Nonograms - Print layout1", 2026-10-08 (item 5): "Please move the
  lower caption (with the Puzzle name closer to the puzzle and align it by the right side with
  the puzzle." Scoped here to the one caption CARD-197/198 added to the solved answer page —
  confirmed by ADR-0037/R1 that no other page in the book carries a caption at all.
- [Verified facts the implementer must not re-derive]
  - `solved_puzzle_page` step 8 is `book_pdf_generator.py:2111-2150` exactly as quoted above —
    read in full, not excerpted.
  - `export/layout.py`'s `Placement` dataclass (`:608-624`) docstring confirms
    `drawing_right` is "the grid's right edge" (line 622) — the correct anchor for "align it by
    the right side with the puzzle," as opposed to `usable_right` (the page's own margin).
  - `ANSWER_TILE_GAP_MM = 2.0` already exists at `export/layout.py:1978`, today used only in the
    OLD packed answer-key tile geometry (`book_answer_key.py`'s packing math, left unedited by
    CARD-198 per its Guardrail G-5) — reusing it here for the new gap is a deliberate
    reuse-over-invention choice, not a coincidence of naming; it is not currently imported into
    `book_pdf_generator.py` and will need a new import line.
  - `tests/test_book_solved_page.py`'s existing caption tests
    (`TestBookSolvedPage_CaptionReadsThePictureName`, lines 387-443, and
    `TestBookSolvedPage_CaptionOmittedWhenNoSlack`, lines 451-505) assert the caption is
    *somewhere* inside the usable area and that changing the title only changes the slack band
    — neither hardcodes the old centred x/y formula directly, so most of their assertions
    should still hold at the new position; only `test_the_caption_is_drawn_inside_the_usable_area_only`'s
    "somewhere inside the usable area" check needs a companion assertion for "specifically at
    the right edge," which is what AC-1's new test adds.
  - `tests/test_book_pdf_band.py:1209`'s `test_the_search_finds_an_answer_caption_at_its_own_size`
    finds the caption by text and font size only (no x/y coordinate assertion) — grepped and
    confirmed unaffected by this card, left out of Touches.
  - The byte-identity baseline chain (`tests/test_book_pdf_memory.py:1205-1246`'s
    `TestBookPdfMemory_PagesAreUnchanged`, reading `tests/helpers/book_corpus.BASELINE_FIXTURE`,
    currently `tests/fixtures/book_baseline_card198.json` per `book_corpus.py:136`) is a sha256
    pixel digest per page of `tests/helpers/book_corpus.baseline_puzzles` — this card moves
    caption ink on every answer page whose caption is actually drawn (the cap-bound puzzles in
    that fixture book), so the baseline **must** be regenerated to a new
    `tests/fixtures/book_baseline_card203.json`, `BASELINE_FIXTURE` repointed, and the recording
    must name which pages moved (the chain's own established convention — see CARD-198's own
    entry in that same docstring's history for the expected shape of that note) — a page whose
    caption was already omitted (no slack) must be confirmed as one of the pages that did
    **not** move.
- [Design decision, not owner-confirmed] The exact 2.0 mm gap value (`ANSWER_TILE_GAP_MM`,
  reused) and the choice to keep the band uncentred-but-the-caption-right-aligned (i.e. the
  band and caption no longer share the same horizontal alignment) — flagged above in Design
  context, needs the owner's render sign-off before merge, same discipline CARD-197/198 both
  used for their own unconfirmed visual defaults.
- [Coordination note for a sibling card] CARD-202 (shrinking small solved answers to 2-or-4-up
  per page, drafted separately, not yet implemented at the time this card was drafted) is
  expected to reuse `solved_puzzle_page`'s drawing steps, including step 8's caption logic, at
  a shrunk size. Whichever of CARD-202/CARD-203 lands second should carry this card's final
  right-aligned/closer caption positioning into the shrunk-slot renderer too, rather than
  reintroducing the old centred behaviour in a new code path — no `Depends on` is set either
  way since they can ship in either order, but this is a real continuity the implementer of the
  second card should check for explicitly.
- [Not in this card] Formalising a requirements delta for the solved-page caption's position
  (it has no FR today, per CARD-197/198's own "none yet, by design") — architect-station
  follow-up, same pattern CARD-198 used for FR-042.

- [Implementation complete, 2026-10-10] Both target changes made, both guardrails confirmed.

  - **Where the code actually was.** By the time this card was implemented the step-8 code the
    card quotes (`solved_puzzle_page:2111-2150` in the card's own line numbers) had already moved:
    CARD-202 extracted `solved_puzzle_page`'s steps 3-8 into a new shared method,
    `BookPDFGenerator._draw_solved_slot`, called by **both** `solved_puzzle_page` (a full answer
    page) and `_packed_answer_page` (CARD-202's packed 2-/4-up slots). The caption code this card
    targets now lives at `_draw_solved_slot`'s own step 8. The two target edits were made there
    instead of at the stale line numbers, with identical semantics to what the card specifies.
  - **STRUCTURE: the CARD-202 coordination question resolves itself.** Investigated by reading
    `_packed_answer_page`, `_draw_solved_slot` and `book_answer_key.py` in full: CARD-202 did
    **not** duplicate caption-drawing logic for its packed slots — it extracted the single
    `_draw_solved_slot` method precisely so a full page and a packed slot "draw from the **one**
    implementation." So this card's one edit automatically reaches both page kinds — no second
    edit was needed. Confirmed empirically: the regenerated baseline's three answer pages (11
    Duck+Owl packed, 12 Tree packed alone, 13 Snowflake full page) **all three** moved.
  - **SCOPE+ (small, docs-only):** `tests/test_book_page_numbers.py`'s module docstring stated
    the caption anchor as `"mm"` (stale); corrected to `"rm"` with a CARD-203 pointer — no test
    behavior changed, only a stale documented fact.
  - **AC-4's boundary shape, found by sweep.** Swept every 10..30 checkerboard for a slack value
    inside `[line_height, gap_px+line_height)` = `[49, 73)` px: exactly one shape qualifies,
    29x23 (slack 58px) — `_NARROW_GAP_SHAPE`, proving the OLD guard would have drawn here while
    the NEW guard correctly omits it.
  - **Test evidence:** `tests/test_book_solved_page.py` 36 passed (26 pre-existing unedited + 6
    new/added across AC-1/AC-2/AC-3/AC-4); `tests/test_book_pdf_memory.py` green against the
    repointed baseline; `tests/test_book_solved_answer_key.py` (54), `tests/test_book_pdf_band.py`
    (34), `tests/test_book_page_numbers.py`, `tests/test_book_pdf_packed_degrade.py`,
    `tests/property/test_book_answer_tiles.py`, `tests/test_book_toc.py`,
    `tests/test_book_interior_type_floor.py`: all green. Full `pytest tests/ -k "book"`: green,
    exit 0, run twice to confirm.
  - **Baseline regeneration:** new `tests/fixtures/book_baseline_card203.json`, `BASELINE_FIXTURE`
    repointed. **Moved: pages 11, 12, 13** (the only pages where the caption actually draws ink).
    **Unmoved: pages 1-10**, confirmed byte-identical by direct digest comparison. `page_count`
    stays 13 (G-5 intact). `interior_bytes`: 3,420,073 → 3,421,901.
  - **Owner sign-off still needed before merge** (per Design context): the 2.0mm gap and the band
    staying centered while only the caption right-aligns are this card's own reading of
    "closer"/"align by the right side," not an owner-confirmed pixel value. No render was
    produced during implementation — needed before merge.
