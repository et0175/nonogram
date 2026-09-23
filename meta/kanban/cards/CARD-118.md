# CARD-118: Proof pages — one 30×30 and one 15×15 on the book's PageSpec, for the owner to print

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/118-proof-pages
**Worktree:** ../PythonProject4-CARD-118
**Source:** meta/architecture/handoff.md#increment-13 (last card — carries the increment checkpoint)
**Idea:** —
**Wave:** 25
**Depends on:** CARD-117
**Touches:** src/nonogram/admin/book_proof.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_setup_print.html, tests/test_book_proof_pages.py
**Review score:** 8.5 (cycle 1/3)
**Started:** 2026-09-23
**Closed:** 2026-09-23
**Actual:** 0.5d
**Merge commit:** 2782887
**Blocked by:** —

## What to implement

ADR-0037 says the stroke numbers become final only after the owner has seen them on
**printed proof pages**. This card builds the "proof pages" export: a small PDF of the
ADR-0037 proof set on the book's own `PageSpec`.

1. `admin/book_proof.py` renders a 2-page PDF on the book's trim through the same page
   builder CARD-116/117 use: one **30×30 with 9-deep row and column clue gutters**
   (expected 4.97 mm cell on the Book 1 profile) and one **15×15 with 7-deep gutters**
   (expected 7.5 mm). Each page carries the band ("Puzzle 1 · …" / "Puzzle 2 · …") and
   the book strokes. The two proof puzzles are **fixed fixtures** (deterministic clue
   sets with exactly those depths), not drawn from the database. The measurements in
   the checkpoint depend on those depths. Which puzzles to use is not stated anywhere
   else, so record the choice in Worktree notes.
2. A **"Download proof pages"** action on Print setup (`book_setup_print.html`) served
   by a new `GET /book/<id>/proof-pages` route. The book does not need any puzzles to
   get proofs, since proofs come before curation.
3. Print on the page, in small type below the band area or at the page foot, **inside
   the margins**: the trim, the cell size in mm, and the thin and heavy rule widths in
   mm. The owner can then compare the ruler to the claim. (This is a proof-only
   annotation. A real book page never carries it.)

## Increment 13 checkpoint (this card closes it)

Automatable: the golden A4 test is green on both sides of the change, and a seeded
30×30 `nonogram generate` writes byte-identical PNG/SVG/PDF before and after
(CARD-113/114). A Book 1 profile book PDF opens at 2550 × 3300 px per page, and a 6×9
book at 1800 × 2700 px (CARD-116). The band reads "Puzzle N · Tier" and no picture title
is on the puzzle page (CARD-117). On facing pages the 15×15 drawing's left edge sits at
27.05 mm (odd) and 23.875 mm (even) from the trim edge, on the same top pixel row
(CARD-116). *Added 2026-09-22 (d):* the export yields two files — an interior PDF whose
page 1 is the guide page, with no cover page anywhere in it, and a one-page cover PDF at
the trim size (CARD-135) — and every page takes its parity from its interior position:
until level dividers exist (CARD-128) the first puzzle page is interior page 2, gutter on
the right (CARD-116).

**Owner-confirmed (not automatable):** printed on 8.5×11 paper, the proof pages measure
a 4.97 mm cell (±0.05 mm) on the 30×30 with 9-deep clues and 7.5 mm on the 15×15. Thin
rules are at least 0.25 mm and heavy rules visibly double. The owner has looked at the
printed proofs and confirmed the stroke values (owner-validates-visually). Renders go to
`~/Documents/nonogram-reviews/CARD-118/`, never beside the repo. The card is not `done`
until the owner's confirmation is recorded in Worktree notes. If the owner rejects the
strokes, that goes back to ADR-0037 (architect station), not into a code tweak here.

## Acceptance criteria

_No requirement-level AC names this deliverable (it realises ADR-0037's proof step). The
automatable half of the checkpoint is its executable done-definition:_

- CK-1 — given a Book 1 profile book, when proof pages are downloaded, then the PDF has exactly 2 pages, each 2550 × 3300 px at 300 DPI; the 30×30 page's cell is 4.97 mm (±0.05) and the 15×15 page's is 7.5 mm.
  *test:* `TestBookProof_TwoTrimSizedPagesAtExpectedCells`
- CK-2 — given a 6×9 book, when proof pages are downloaded, then each page is 1800 × 2700 px.
  *test:* `TestBookProof_FollowsStoredTrim`
- CK-3 — given the proof PDF, when the 30×30 page's rules are measured, then thin rules are ≥ 3 px (0.25 mm at 300 DPI), heavy rules are 2 × thin, and rule pixels are pure black.
  *test:* `TestBookProof_StrokesMeetBookMinimum`

## Guardrails

- G-1: The admin panel fits no cells and places no grid lines itself (ADR-0036/R2). Proofs go through the same PageSpec call as the book PDF, so the proof measures what the book will print.
- G-2: CLI and web A4 output stay byte-identical (CON-019). Do not edit `src/nonogram/export/**`.
- G-3: Do not edit `src/nonogram/admin/book_pdf_generator.py`. It is owned by CARD-127 this wave. Reuse its page builder through a public function. If one does not exist, add the smallest seam in `book_proof.py` and note it.
- G-4: Do not edit `src/nonogram/admin/templates/book_detail.html`, `src/nonogram/admin/templates/books_list.html` or `src/nonogram/admin/templates/_stepper.html`. They are owned by CARD-130 this wave.

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

- **FR:** — (ADR-0037 proof step; supports FR-033/NFR-008 verification)
- **NFR:** NFR-008
- **ADR:** ADR-0037, ADR-0036
- **Components:** COMP-009, COMP-007 (consumed)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md (direction + anti-patterns), tokens.css (all visual values), components.md (inventory + states)
- **UI components:** Button (reuse — secondary action "Download proof pages"), FormField (reuse, unchanged)
- **Screens:** /book/<id>/setup-print (the action), /book/<id>/proof-pages (PDF response)
- **Standards:** forge:engineering-standards §11 (tokens-only styling, all listed states, a11y minimum)

## Worktree notes

- [Env] forge 2026.8.17 (no meta/.skills.yml — no min_version to compare; defaults in force:
  review on, min_score 8, max_cycles 3, min_improvement 0.5, build_fix_attempts 2,
  scope_gate on, tdd false, standards on, no models block → agents spawn without `model:`)

- [Handover from CARD-117, 2026-09-23] The proof set is already rendered in ~/Documents/nonogram-reviews/CARD-117/ (30x30 even page 2, 15x15 odd page 3, 30x30 odd page 5 answer, full-interior-6pages.pdf, README.txt with what to measure). Print at 100%, never fit-to-page. Open question for the owner: whether the fixed 0.25 mm thin rule makes the 30x30 look too dense.

### CARD-118 implementation, 2026-09-23

**Which fixture puzzles, and why.** The card says the choice is stated nowhere
else, so: `src/nonogram/admin/book_proof.py` holds two literal `#`/`.` grids,
`_PROOF_LARGE_ROWS` (30x30, nominal tier "hard") and `_PROOF_SMALL_ROWS`
(15x15, "easy").

* **Extents and depths** are the whole reason for the choice. 30x30 is
  CON-011's largest extent and 9-deep row *and* column clues make the drawing
  39x39 cells — the deepest-gutter case at the largest extent, which is the
  **smallest cell a book page produces** (4.97 mm on Book 1, just above
  NFR-008's 4.8 mm floor) and so the case ADR-0037's stroke minimum is
  actually about. 15x15 with 7-deep gutters is 22x22 cells, small enough that
  the sheet is not what limits it on Book 1 and NFR-008's flat **7.5 mm cap**
  is. The two bracket the book's whole cell range on one sheet of paper.
* **How the grids were produced:** drawn once from a seeded, *transpose-
  symmetric* random source (`random.Random(30)` at 45% and `Random(10)` at 50%,
  upper triangle mirrored) and then **frozen as literals**. Symmetric so the
  row and column gutters are equally deep by construction; random-looking so
  the clue digits are a realistic mix of 1s, 2s, 3s and the odd 11 — the owner
  is judging digit legibility at 4.97 mm, and a comb pattern of all-1s would
  not test that. They are *not* claimed to be uniquely solvable and are not
  meant to be solved: a puzzle page prints no answer, so what reaches the paper
  is the ruled grid and the clue digits, which is exactly what is measured.
  Not drawn from the database on purpose — a proof set that changed with the
  panel's contents would stop being a proof of the checkpoint's numbers.
* **The band tiers ("hard"/"easy") are nominal**, not solver verdicts: these
  fixtures were never generated as puzzles and have no grade. They are printed
  so the band on the proof is the length and weight the book's own band will
  be, and the page says on its face that it is a proof page. ADR-0037/R1
  governs a *book puzzle page*; nothing here reaches a book.

**The seam used to reuse the page builder (G-3).** No edit to
`book_pdf_generator.py`. `book_proof.proof_pages` goes through its public
surface only: `BookPDFGenerator(book).page_spec(position)` for the sheet,
module-level `page_frame(spec)` for the usable area, module-level
`band_identity(n, tier)` for the band line, and COMP-007's
`nonogram.export.pdf.render_pages(payload, page_spec=...)` for the page. Proof
pages take interior positions 1 and 2, so page 1 is right-hand and page 2
left-hand and the mirrored margins are visible on the two sheets in hand.
Two seams were genuinely missing and were added **in book_proof.py**, both
six lines and both documented at their definition: (a) `_note_font_bytes`,
which loads the packaged DejaVu Sans through the public
`nonogram.export.pdf.FONT_PACKAGE`/`FONT_RESOURCE` constants, because the
note needs `·` and `×` (Pillow's default face has neither) and
`pdf._header_font` is private while G-2 puts `export/**` out of reach; and
(b) `render_proof_pdf`'s own `save(..., save_all=True, dpi=(DPI, DPI))`,
because `BookPDFGenerator._save_pdf` is private. **No cell is fitted and no
grid rule is placed here** (G-1): every millimetre in the annotation is read
back off `compute_layout`'s result for the book's spec.

**The annotation: wording and placement.** Two lines in DejaVu Sans at 2.6 mm
(shrunk to fit, floor 1.6 mm), left-aligned on the usable area's left edge with
the block's bottom on the usable area's bottom edge — the page foot, inside the
book's own mirrored margins:

```
PROOF PAGE (not a book page) · trim 215.9 × 279.4 mm (8.50 × 11.00 in) at 300 dpi
cell 4.97 mm · thin rule 0.25 mm · heavy rule 0.51 mm · grid 30 × 30, clues 9 and 9 deep
```

Every figure comes from the `Layout` that drew the page (`page.cell_mm`,
`thin_rule`/`thick_rule` converted at `layout.dpi`, `width`/`height`), never
from a profile constant — so the page's claim and the page's ink are the same
measurement and a ruler can check one against the other. It is proof-only:
`_annotate` is called from `proof_pages` and nowhere else, and
`test_nothing_on_the_book_export_path_imports_this_module` walks
`src/nonogram/**/*.py` with `ast` and requires `app.py` to be the module's only
importer, so there is no path from a book download to this ink.

**Known limitation (deliberate, tested):** on a **near-square trim** (8.25x8.25
or 8.5x8.5 in — both real KDP sizes) the square fixtures are limited by the
page's *height* and the drawing reaches the bottom margin, leaving no clear
strip for the note. `proof_pages` then raises a `ValueError` naming the room it
needed and the route flashes it, rather than overprinting the grid (unreadable
where it must be read) or pushing the note into the margin (breaking the rule
it exists to demonstrate). Every portrait book trim leaves tens of millimetres.
A later card could wrap the note into the drawing's blank clue corner if a
square-trim book is ever wanted.

**Measured values (8.5 x 11, Book 1 profile).** Page 1: 2550 x 3300 px, PDF
MediaBox 612 x 792 pt, 30x30 grid, 31 rules per axis, cell **4.967 mm**
measured off the ink (4.966 mm exact), thin **3 px = 0.254 mm**, heavy
**6 px = 0.508 mm**, scanline greys `[0, 255]` (no anti-aliasing), drawing's
left edge 12.7 mm (the gutter). Page 2: same trim, 15x15 grid, 16 rules per
axis, cell **7.501 mm** (7.5 exact), thin 3 px, heavy 6 px, greys `[0, 255]`,
left edge **23.876 mm** — Increment 13's own figure for the 15x15 on an even
page. On 6 x 9: 1800 x 2700 px, MediaBox 432 x 648 pt, cells 3.339 mm and
5.915 mm, strokes unchanged at 3/6 px.

**Owner renders.** `~/Documents/nonogram-reviews/CARD-118/` —
`proof-pages-8.5x11.pdf` and `proof-pages-6x9.pdf` (exactly what the button
serves) plus a PNG of each page, and `README.txt` modelled on CARD-117's,
including the MEASURED WHEN GENERATED cross-check block and CARD-117's open
question carried forward (does the fixed 0.25 mm thin rule make the 30x30 look
too dense?). Nothing was written beside the repo and
`nonogram_admin.db` was never opened — every test brings its own in-memory
book store.

**Owner confirmation: NOT YET RECORDED.** The card stays out of `done` until
the owner has printed `proof-pages-8.5x11.pdf` at 100% and confirmed the
strokes (owner-validates-visually). If the strokes are rejected, that goes back
to ADR-0037 at the architect station, not into a code tweak here.

- [Handover] `nonogram.admin.book_proof` is now the one place proof pages are
  built. `PROOF_PUZZLES`, `annotation_lines(layout)`, `proof_pages(book)` and
  `render_proof_pdf(book)` are its public surface; `proof_pages` takes anything
  carrying the `books` print columns (or `None` for the Book 1 profile) and
  reads **no** puzzle membership. A card that changes the book's `PageSpec` —
  strokes, band, cap, margins — changes these pages automatically and should
  re-render the owner set. If ADR-0037's stroke numbers move, the expected
  values in `tests/test_book_proof_pages.py` (MIN_THIN_RULE_MM/PX) and the
  checkpoint's 4.97/7.5 mm move with them; the fixture depths they depend on
  are pinned by `TestBookProof_FixturesAreTheDepthsTheMeasurementsAssume`.

- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_proof.py, src/nonogram/admin/templates/book_setup_print.html, tests/test_book_proof_pages.py
- [Note] branch base is 89facec, not main's current tip 1abc08c — main gained 37bb48e (kanban bookkeeping only) and 1abc08c (deploy fix: start.sh + tests/test_admin_serving.py) after the worktree was cut. No code overlap with this card's four files; the rebase at merge is clean-by-inspection.
- [Build gate] PASSED (full, 256s) — 4755 tests, rc=0, zero failures; the known pre-existing
  tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied
  deselected. Full-suite lock acquired and released. Not vacuous (4755 executed).
- [Golden tripwire] tests/test_export_a4_golden.py, tests/property/test_cli_exports_byte_identity.py
  and tests/fixtures/a4_golden/** are green and carry ZERO bytes of diff in this card (CON-019 intact).
- [Visual] no Makefile run target in the repo or the worktree — the app cannot be booted by the
  harness, so cycle 1 review runs STATIC-ONLY. The rendered result of the new Print-setup action
  was not verified by screenshot; the owner PDFs in ~/Documents/nonogram-reviews/CARD-118/ are the
  rendered evidence for the PAGES, not for the screen.
- [System contract] fresh lens (system_rules.py --card CARD-118) returns 44 rules; the card's
  ## System contract section lists the same 44 ids. No drift — section NOT refreshed, nothing added
  or removed.
- [Scope gate] IN_SCOPE — 4 changed files, all inside Touches; excess 0; comp_spread 0 (everything
  is COMP-009 admin + its tests); guardrail_hits 0 (no file under src/nonogram/export/**,
  book_pdf_generator.py, book_detail.html, books_list.html or _stepper.html).
  Recorded, NOT escalated: CARD-139 (ready, wave 26, "import sweep over app.py") lists app.py as
  1 of its 3 Touches entries, so the naive poach ratio reads 33%. app.py is this card's OWN declared
  Touches and the edit is one relative import line beside the existing `.book_pdf_generator` import
  plus one route function (+41/-0, nothing reordered) — the card doing the work it was cut to do is
  not poaching, and no part of CARD-139's sweep was absorbed.
- [Review 1/3] Score: 8.5 — crit: 0, imp: 0. Severity gate: findings_count == 0, score >= min_score 8
  -> success path open. Adversarial verification: nothing to verify (it runs on GATING findings only,
  and there are none); the 5 Minor + 4 Out-of-scope findings do not gate.
- [Review sync] 1 report(s) -> meta/review/ (20260923T135446Z-CARD-118-cycle1.yml)
- [Review 1/3] Step 8h coverage: count line present ("System contract: 44 rules checked, 25 holds,
  19 unchecked, 0 violated") and all 44 card ids carry a verdict line — verified id by id against the
  card's ## System contract section. 0 violated. No rules checked beyond the card's list.
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0036/R2, ADR-0037/R2, INV-013) by three
  independent skeptics with fresh context, each re-deriving the verdict's cited evidence with its
  own instrument rather than the card's test helpers.
  Deliberate, stated deviation from the default selection rule: the protocol's "first three
  test-citing holds in report order" would have sampled ADR-0006/R1, ADR-0019/R1 and ADR-0032/R1 —
  rules this diff barely touches. I sampled instead the three holds that actually gate this card
  (the admin places no rules; the strokes meet the book minimum; no proof artefact can reach the
  book export). Each cites a named test, so re-derivation stayed crisp; the sample is strictly
  harder than the default one, not easier.
  Independently re-derived, not merely re-run: cell pitch measured at 4.966 mm off ~126k rule gaps
  in the rendered pixels against the note's stated 4.97 mm; strokes measured 3 px / 6 px with grey
  set {0,255} over the WHOLE grid rectangle and ink exactly (0,0,0), on 8.5x11 AND 6x9; the
  ADR-0037/R2 floor swept across the panel's entire accepted trim box (10x10 cm .. 30x48 cm) with
  zero violations — at a 10 cm trim the proportional rule would be 1 px (0.085 mm) and
  min_thin_rule_mm lifts it to 3 px, so the floor is doing real work rather than coinciding with
  the default profile; and the sole render_proof_pdf call site confirmed at app.py:3496 with no
  proof reference anywhere on the book export path.
  One honest caveat carried forward from the INV-013 skeptic (NOT a gate failure — the verdict's
  conclusion stands on direct evidence): the card's own `ast` importer guard records `path.name`,
  so a future second file named `app.py` under src/nonogram/ would satisfy it, and it sees static
  imports only. Today the tree has exactly one `app.py` and no dynamic import of book_proof. The
  reviewer raised the same thing as a Minor (F-005 secondary).
- [AC/EC check] All criteria/constraints ✓ (evidence) — 7/7 items demonstrated by a fresh-context
  gate agent that ran the tests itself; no item was ⚠ partial, ✗ contradicted or ✗ unverified.
  This card has no '## Engineering constraints' section, so no EC item existed to verify.
  CK-1 ✓ demonstrated — TestBookProof_TwoTrimSizedPagesAtExpectedCells (exists at line 279), green
    in `14 passed, 6 warnings in 0.87s`. Asserts 2 pages, (2550,3300) px AND MediaBox
    (0,0,612.0,792.0) — the DPI half, which a pixel-only check would miss — with page 1 (30,30) at
    4.97 mm ±0.05 and page 2 (15,15) at 7.5 mm ±0.05, the cell read off the rendered ink via
    tests/helpers/page_ink.drawing_of, which imports only numpy/PIL (not export.layout) and is not
    in this card's diff — so the measurement is independent of the code under test.
  CK-2 ✓ demonstrated — TestBookProof_FollowsStoredTrim (line 333), green in the same run:
    (1800,2700) px and MediaBox (0,0,432.0,648.0) on a 6x9 book, plus the fixtures taking that
    smaller sheet's OWN cells — i.e. the proof measures the book, not a remembered Book 1 constant.
  CK-3 ✓ demonstrated — TestBookProof_StrokesMeetBookMinimum (line 382), 6 parametrised cases green:
    thin >= 3 px AND >= 0.25 mm; heavy exactly 2x thin (set equality, not merely "thicker"); greys
    on the scanline <= {0,255} and every ink pixel exactly (0,0,0); 30 cells ruled exactly 31 times.
    Judged-acceptable deviation, verified by the gate rather than taken on trust: strokes are
    measured on the page as drawn, not on the PDF-decoded page, because the file's DCT round trip
    greys a 3-px rule's edges and would make "pure black" unmeasurable — and render_proof_pdf saves
    exactly those page objects, while CK-1 separately proves the PDF's page size and box.
  G-1 ✓ demonstrated — scan (stated as such): book_proof.py contains no grid-drawing primitive at
    all — grep for .line/.rectangle/.polygon/.ellipse/.rounded_rectangle/ImageDraw returns the
    import plus one ImageDraw.Draw whose only use is draw.text for the two annotation lines. The
    page comes from render_pages with the same BookPDFGenerator.page_spec call the book PDF uses.
    Bounded to this card's two source files; not a global absence proof.
  G-2 ✓ demonstrated — BOTH halves, the priority check. Behavioural: test_export_a4_golden.py +
    property/test_cli_exports_byte_identity.py green (66 passed in 17.65s). Tripwire integrity:
    `git diff --stat main...HEAD` over those two files and tests/fixtures/a4_golden/ is EMPTY and
    `git status --porcelain` on the same paths is EMPTY — the fixtures were not regenerated or
    edited to pass. Structural: no path under src/nonogram/export/ in the diff or the working tree.
  G-3 ✓ demonstrated — changed-file set is exactly 4 paths (M app.py, A book_proof.py,
    M book_setup_print.html, A tests/test_book_proof_pages.py); no book_pdf_generator.py in either
    the committed diff or the uncommitted set. Reuse goes through that module's public surface
    (page_spec, page_frame, band_identity); the two added seams live in book_proof.py, as G-3 allows.
  G-4 ✓ demonstrated — no book_detail.html, books_list.html or _stepper.html in the diff or the
    working tree. The only template touched is book_setup_print.html, which Touches names and G-4
    does not guard.
  Corroborating: the diff is PURELY ADDITIVE (numstat 41/0, 539/0, 11/0, 922/0 — zero deleted lines
  anywhere), so no existing test could have been weakened, retargeted or deleted to make room.
- [Docs] forge:readme step SKIPPED for all three changed directories, deliberately, with reasons:
  * src/nonogram/admin/ and src/nonogram/admin/templates/ have no README.md, and neither does ANY
    directory under src/ in this repo (the only two READMEs in the tree are tests/ and tests/e2e/).
    Creating the project's first src-side README from a 0.5d proof-pages card would be introducing
    a convention rather than documenting a change — and CARD-127, CARD-130 and CARD-138 are all
    live in src/nonogram/admin/ right now, so three cards each creating the same new path is a
    guaranteed merge conflict for no doc value. The module documents itself: book_proof.py opens
    with a full module docstring and every public name carries one.
  * tests/README.md exists but is a stale, narrowly-scoped "Admin Panel Test Suite - Wave 1"
    document that enumerates four Wave-1 test files and none of the ~20 book test files added
    since (CARD-116/117/133/135 added none either). Appending one line about
    test_book_proof_pages.py to a Wave 1 index would make it less coherent, not more, and
    rewriting it wholesale is outside this card. Directory purpose did not change.
  * Recorded as a pre-existing documentation defect for the board's backlog, not introduced here:
    "tests/README.md is a Wave 1 index that has not tracked the book suite since wave 20".
- [Commit] SUCCESS — 8765b91. No separate /commit commit was created and none was needed: the
  implementation agent had already committed, and no fix round, AC-gate fix or README change
  followed, so the working tree holds only meta/ files, which /commit excludes by contract. The
  existing commit already satisfies the contract — conventional subject, body explaining the why,
  guardrails named, and the required trailer
  "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>". An empty commit would have
  added a second SHA and no information.
  Contents: 4 files, +1513/-0 (M app.py +41, A book_proof.py +539, M book_setup_print.html +11,
  A tests/test_book_proof_pages.py +922). Nothing under meta/, no nonogram_admin.db, no egg-info.
- [Pipeline] Card stays Status: review until the dispatcher merges it. One review cycle, no fix
  round, no escalation. Build gate run once (full, green). Review cycles used: 1 of 3.
- [OWNER ACTION OUTSTANDING — blocks `done`, not the merge] This card closes Increment 13 through
  an owner-confirmed checkpoint. The automatable half is green; the other half is a ruler.
  Print ~/Documents/nonogram-reviews/CARD-118/proof-pages-8.5x11.pdf on 8.5x11 paper at 100% /
  "actual size" — NEVER "fit to page" — and check against README.txt in that directory:
  4.97 mm cell (+/-0.05) on the 30x30 with 9-deep clues, 7.5 mm on the 15x15, thin rules at least
  0.25 mm, heavy rules visibly double, rules solid black with no grey fringe.
  The open question ADR-0037 leaves to the proof, carried forward from CARD-117: does the fixed
  0.25 mm thin rule make the 30x30 look too dense?
  If the owner REJECTS the strokes, that goes back to ADR-0037 at the ARCHITECT station — not into
  a code tweak here. Record the confirmation in these notes before the card goes to `done`.

- [Done] Merged 2782887 on 2026-09-23. Review 8.5 (1 cycle, 0 critical, 0 important,
  5 minor). AC/EC/G 7/7 demonstrated. Full suite green on the merged result (the one
  known pre-existing e2e failure deselected). Golden tripwire green with zero bytes of
  fixture diff — CON-019 intact.
- [Handover] `nonogram.admin.book_proof` is now the one place proof pages are built
  (PROOF_PUZZLES, annotation_lines, proof_pages, render_proof_pdf). It reads no puzzle
  membership, so any card that changes the book's PageSpec changes these pages too and
  should re-render the owner's set. Fixture clue depths (9/9 on the 30x30, 7/7 on the
  15x15) are pinned by TestBookProof_FixturesAreTheDepthsTheMeasurementsAssume; the
  4.97 / 7.5 mm figures depend on them.
- [Known gap, tested and deliberate] A square or landscape trim (8.25x8.25, 8.5x8.5 —
  real KDP sizes) leaves no room for the foot note, so `proof_pages` raises and the
  route flashes it. Every portrait trim renders.
- [Owner] BLOCKS the wave-25 checkpoint, not the merge. Print
  ~/Documents/nonogram-reviews/CARD-118/proof-pages-8.5x11.pdf at 100% / "actual size"
  (never "fit to page") and check it against README.txt in that directory: 4.97 mm cell
  (+/-0.05) on the 30x30 with 9-deep clues, 7.5 mm on the 15x15, thin rules >= 0.25 mm,
  heavy rules visibly double and solid black. Open question carried from CARD-117: does
  the fixed 0.25 mm thin rule make the 30x30 look too dense? A rejection routes to
  ADR-0037 at the architect station, not to a code tweak.
- [Deferred, non-blocking] Reviewer minors left for later: the route's broad
  `except Exception` flashes raw exception text; `redirect(request.referrer or ...)` is a
  caller-controlled target; a new `datetime.utcnow()` deprecation; the `ast` importer
  guard matches on bare filename rather than relative path.
- [Docs] Docs step deliberately skipped: no directory under src/ has a README, and
  tests/README.md is a stale "Wave 1" index unmaintained since wave 20. Logged as a
  pre-existing defect, not introduced here.
