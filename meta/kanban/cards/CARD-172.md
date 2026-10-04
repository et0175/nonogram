# CARD-172: Proof pages render on square and landscape trims, with the note in a clear spot inside the frame

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/172-proof-pages-square-landscape
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (IDEA-070, WSJF 3.0; CARD-118 known gap)
**Idea:** IDEA-070
**Wave:** 33
**Depends on:** —
**Touches:** src/nonogram/admin/book_proof.py, tests/test_book_proof_pages.py, tests/fixtures/proof_baseline_card172.json (new)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code and running it).**
`book_proof.proof_pages` lays out the two fixed proof puzzles (30×30 with
9-deep clues, 15×15 with 7-deep clues) on the book's PageSpec. Then
`_annotate` puts a two-line note at the page foot. `_fitted_note_font` sizes
it at 2.6 mm (shrinks to a 1.6 mm floor) into the strip between the drawing's
bottom and the bottom margin, less a 2 mm gap. If the strip is too shallow it
raises `ValueError("this trim leaves no room for the proof note ...")`, and the
route `download_book_proof_pages` (app.py ~4704) flashes it.

On a square or landscape trim the drawing is limited by the page's *height*.
It reaches the bottom margin, so the foot strip is 0 mm. Measured on page 1
(30×30) with the Book 1 margins:

| Trim (in) | Foot strip | Side strip (each side) | Blank clue corner |
|---|---|---|---|
| 8.25×8.25 | 0 mm | 4.4 mm | 41.2 mm square |
| 8.5×8.5 | 0 mm | 4.5 mm | 42.7 mm square |
| 8.25×6 (KDP landscape) | 0 mm | 32.9 mm | 26 mm square |
| 11×8.5 | 0 mm | 36.2 mm | 42.7 mm square |

So `proof_pages` raises for all four. On 8.25×6 both pages raise; on the
squares only page 1 does (page 2 has 13.5–19.9 mm of foot).

**Target behaviour.** Keep the foot placement exactly as it is wherever it
fits today. When the foot strip cannot hold the note, place it in the first
clear spot that can, in this order:

1. **Foot strip** — unchanged code path, unchanged size rule (2.6 mm, floor 1.6 mm).
2. **Outer side strip** — the clear column between the drawing and the outer
   margin (right on an odd page, left on an even page; the drawing is centred,
   so both are equal). Used by landscape trims.
3. **Blank clue corner** — the empty boxed square at the drawing's top-left,
   where the row and column clue gutters meet. Inset 1 mm from its rules.
   Used by square trims.

In spots 2 and 3 the note is the same text (`annotation_lines`, unchanged),
word-wrapped to the spot's width, set at a fixed **10 pt** (CON-020's floor,
42 px at 300 dpi) with leading 1.2. It never shrinks below 10 pt. If no spot
holds it, keep today's `ValueError` with the same "no room for the proof note"
wording.

Probe results for this rule (10 pt, leading 1.2): 8.25×8.25 page 1 → corner,
9 lines, 38.1 mm tall in 39.2 mm. 8.5×8.5 page 1 → corner (38.1 in 40.6 mm).
8.25×6 → side on both pages (14 and 10 lines). 11×8.5 → side. Small squares
still refuse: 15×15 cm and 20×20 cm fit no spot.

The placement is **owner-visible** (a note inside the puzzle's clue corner is
new on the page). Render the set for the owner (see Design context).

Replace the pinned raise test. Do not delete it silently:
- `TestBookProof_BandAndAnnotation.test_a_trim_with_no_room_for_the_note_is_refused_and_says_so`
  (tests/test_book_proof_pages.py:614) uses 8.5×8.5 → re-point it to a 15×15 cm
  square, which still refuses. Its docstring changes to say why.
- `TestBookProof_ProofPagesRoute.test_a_trim_with_no_room_for_the_note_is_reported_not_served`
  (:756) uses `"21.59", "21.59"` → re-point to `"15.00", "15.00"`.
- The 8.5×8.5 case moves to the new AC-1 test. Update the `CORPUS_TRIMS_CM`
  comment (:795) that names the old test.
- Update the module docstring and the `_annotate` docstring. Both describe the
  square-trim refusal as the end state.

## Acceptance criteria

- **AC-1:** Given books at 8.25×8.25 and 8.5×8.5 in (Book 1 margins), when `proof_pages` runs, then it returns 2 trim-sized pages, and on each page the note's ink lies inside the frame and touches no grid rule or clue digit (page 1's note sits inside the blank clue corner's interior).
  *test: TestBookProof_SquareTrimsCarryTheNote (in tests/test_book_proof_pages.py)*
- **AC-2:** Given books at 8.25×6 in and 11×8.5 in, when `proof_pages` runs, then both pages render and each note lies in the outer side strip, inside the outer margin, clear of the drawing's bounding box on both parities.
  *test: TestBookProof_LandscapeTrimsCarryTheNote (in tests/test_book_proof_pages.py)*
- **AC-3:** Given any note placed in the side strip or clue corner, when its first line's capital-letter ink height is measured, then it is at least 10 pt × DejaVu Sans's cap-height ratio at 300 dpi (fails if the fallback reuses the 2.6 mm / 1.6 mm sizing).
  *test: TestBookProof_FallbackNoteHoldsTheTenPointFloor (in tests/test_book_proof_pages.py)*
- **AC-4:** Given the EC corpus extended with 20.96×20.96, 21.59×21.59, 20.96×15.24 and 27.94×21.59 cm, when every page is checked, then each page is its stored trim, inside its own mirrored margins, ruled at ADR-0037/R2 weights, and its note's stated cell equals the drawn cell.
  *test: test_PropertyTest_BookProof_EveryStoredPrintSpecPrintsItsOwnSheet (in tests/test_book_proof_pages.py, extended; floors raised to match)*
- **AC-5:** Given a 15×15 cm square, where no spot holds the note at 10 pt, when proof pages are requested, then `proof_pages` raises `ValueError` matching "no room for the proof note", and the route redirects to Print setup with that flash.
  *test: test_a_trim_with_no_room_for_the_note_is_refused_and_says_so + test_a_trim_with_no_room_for_the_note_is_reported_not_served (in tests/test_book_proof_pages.py, re-pointed, replacing the 8.5×8.5 cases)*
- **AC-6:** Given the nine portrait trims of `CORPUS_TRIMS_CM` at the Book 1 margins, when both proof pages are rendered, then each page's pixel digest (SHA-256 of `page.tobytes()`) equals the digest recorded from main before this card.
  *test: TestBookProof_PortraitProofsAreByteIdentical (in tests/test_book_proof_pages.py, digests in tests/fixtures/proof_baseline_card172.json — record them from main first)*
- **AC-7:** The owner has looked at the square and landscape proofs and accepts where the note sits.
  *test: review-lens (owner visual check of the renders)*

## Guardrails

- G-1: Portrait proofs are byte-identical (AC-6). The foot path, `_NOTE_MM`, `_NOTE_FLOOR_MM`, `_NOTE_LEADING` and `_NOTE_GAP_MM` keep their values.
- G-2: The drawing never moves. No cell is fitted and no rule is placed in `book_proof.py` (ADR-0036/R2). `compute_layout` and `src/nonogram/export/**` are not edited; the CON-019 golden (`TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`) stays green.
- G-3: Still exactly 2 proof pages (`test_the_proof_is_exactly_two_pages`). The note never enters a margin and never overprints a rule or clue digit.
- G-4: The note stays proof-only. `book_pdf_generator.py` is not edited and does not import `book_proof` (`TestBookProof_AnnotationIsProofOnly`). Book PDF pixel baselines (`tests/fixtures/book_baseline_*.json`) do not move; this card changes no book page.
- G-5: The note's text (`annotation_lines`) is unchanged, so every figure is still read off the layout.
- G-6: No new dependency (ADR-0006/R1). The note uses the bundled DejaVu Sans via `_note_font`.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-172` (52 rules). A projection — fix the source artifact, never this list._

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

- FR-033 (trace: "final values confirmed by the owner on printed proof pages (30x30, 15x15) — an owner checkpoint"). No AC names the proof deliverable; AC-1..AC-7 are card-local.
- ADR-0037 (proof step, R2 stroke weights), ADR-0036/R2 (geometry only from COMP-007), ADR-0006/R1.
- CON-018 (Book 1 profile margins), CON-019 (A4 golden), CON-020 (10 pt floor — see Worktree notes on scope).
- COMP-009 (Admin Panel: `admin/book_proof.py`, route in `admin/app.py`), COMP-007 (layout, read only).
- ADR-0036's "portrait only" is the page's orientation policy (no rotation for a bigger cell). A landscape trim is stored and laid out as-is today; this card does not change that.

## Design context

- Screen/page: the proof-pages PDF from Print setup's "Download proof pages" (`GET /book/<id>/proof-pages`). Not a book page.
- Owner-visible choice: on square trims the note goes in the 30×30's blank clue corner; on landscape trims in the outer side strip; portrait unchanged at the foot.
- Renders: ~/Documents/nonogram-reviews/CARD-172/ (owner visual check) — `proof-pages-8.25x8.25.pdf`, `proof-pages-8.5x8.5.pdf`, `proof-pages-8.25x6.pdf` (KDP's landscape trim), a PNG of each page, and a README.txt saying where the note sits on each and what to check. Never beside the repo.

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-070 "Square/landscape trims: no room for proof foot note" (CARD-118 known gap, WSJF 3.0, roadmap estimate 0.375 d).
- [Facts] `_fitted_note_font` is book_proof.py:395 (raise at :428), `_annotate` :438, `proof_pages` :493. `PagePlacement` gives `drawing_left/top/right/bottom` and `cell_mm`; the corner is `row_gutter_cells × cell` wide by `column_gutter_cells × cell` tall from the drawing's top-left. `page_frame(spec)` gives the usable area.
- [Facts] Tests that pin today's refusal and must be re-pointed, not dropped: tests/test_book_proof_pages.py:614 (8.5×8.5) and :756 (route, "21.59"/"21.59"). The comment at :795 names the first.
- [Facts] 10 pt at 300 dpi = 41.67 px → 42 px face. At leading 1.35 the corner needs 43.4 mm on 8.25×8.25 and does not fit (39.2 mm); leading 1.2 needs 38.1 mm and fits. Re-measure if the wrap rule differs.
- [Owner decision] CON-020 governs "text the book's interior prints for the reader"; a proof page is not interior. The existing portrait foot note is 2.6 mm ≈ 7.4 pt (floor 1.6 mm ≈ 4.5 pt), below 10 pt, and G-1 keeps it so. This card holds the new placements at 10 pt as asked. Lifting the portrait note to 10 pt would break byte-identity and is a separate decision.
- [Baseline] Record AC-6's digests from main **before** changing `book_proof.py`.
