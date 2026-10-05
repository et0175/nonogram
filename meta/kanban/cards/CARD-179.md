# CARD-179: The wrapped proof note keeps each number with its unit and never starts a line with "×"

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/179-proof-note-keeps-units
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-05 (IDEA-099, WSJF 5.0; CARD-172 review F-004)
**Idea:** IDEA-099
**Wave:** 34
**Depends on:** —
**Touches:** src/nonogram/admin/book_proof.py, tests/test_book_proof_pages.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code and running it on main).**
The proof note has three placements (CARD-172). Only two of them wrap.

- **Foot** (`_annotate`, book_proof.py:573, `else:` branch). The two
  `annotation_lines` are printed whole, one per printed line, at a face
  `_fitted_note_font` (:420) shrinks until both fit the width. It never wraps.
  So the foot cannot split a number from its unit. All nine portrait trims,
  and the 15×15 page on 8.25×8.25, 8.5×8.5 and 11×8.5 in, take this path.
- **Outer side strip** and **blank clue corner** (`_fallback_note`, :551).
  The two lines are joined with `" · "` into one paragraph and passed to
  `_wrapped` (:523). `_wrapped` splits on every space, glues a `·` onto the
  word before it, and wraps greedily at 10 pt (42 px face), leading 1.2
  (`_FALLBACK_NOTE_LEADING`, :138, 50 px).

Because every space is a break point, the greedy wrap splits numbers from
units and starts lines with "×". What main prints today (Book 1 margins):

| Page | Spot width | Lines | Bad breaks |
|---|---|---|---|
| 8.25×8.25 p1 (corner) | 457 px | 9 | `cell 4.58` / `mm`, `rule 0.25` / `mm`, `rule 0.51` / `mm`, `grid 30 ×` / `30,` |
| 8.5×8.5 p1 (corner) | 474 px | 9 | same pattern |
| 8.25×6 p1, p2 (side) | 375 / 374 px | 12 | `152.4 mm (8.25` / `× 6.00 in)` (line starts with ×), `cell 3.11` / `mm` |
| 11×8.5 p1 (side) | 413 px | 10 | none today (`(11.00 × 8.50 in)` happens to fit a line); the rule must keep it that way |

**Target behaviour.** Change `_wrapped` only (and the leading rule below).
`annotation_lines` keeps its text (G-5). The foot path is not touched.

1. **A number and its unit are one unbreakable unit.** `<number> mm`,
   `<number> in)` and `<number> dpi` never split.
2. **An "N × M" group is unbreakable when it fits the spot's width.** The
   group includes a trailing unit and a leading `(` or trailing `,`:
   `209.6 × 209.6 mm`, `(8.25 × 6.00 in)`, `30 × 30,`.
3. **When an "N × M" group is wider than the spot, it may break only after
   the ×.** The × stays at the end of the line with N, and M keeps its unit.
   So **no line ever starts with ×**. The only case on the trims above:
   8.25×6, where `209.6 × 152.4 mm` is 398 px against a 375 px strip; it
   prints as `trim 209.6 ×` / `152.4 mm`.
4. The `·` glue stays as it is.

**The squares no longer fit at leading 1.2. This needs an owner decision.**
Measured by monkeypatching the rule above into `_wrapped` on main:

| Page | Lines now | Lines with the rule | Fits at 1.2 (50 px)? | Fits at 1.07 (45 px)? |
|---|---|---|---|---|
| 8.25×8.25 p1 corner (457 px tall) | 9 | 10 | no (500 px) → **refused** | yes (450 px) |
| 8.5×8.5 p1 corner (474 px tall) | 9 | 10 | no (500 px) → **refused** | yes (450 px) |
| 8.25×6 p1, p2 side | 12 | 12 | yes | yes |
| 11×8.5 p1 side | 10 | 10 | yes | yes |

Greedy wrapping already gives the fewest lines for a given set of break
points, so no smarter wrap gets the squares back to 9 lines. Any rule that
keeps `4.58 mm` together needs 10 lines in the corner. (Rule 1 alone, without
rule 2, also gives 10.) The spot width and the inset are CARD-172 guardrails,
and the 10 pt face is CON-020's floor, so the only free knob is the leading.

**Default this card builds (owner to confirm on the renders):** keep leading
1.2 wherever the wrapped note fits. When a spot cannot hold it at 1.2, try the
same spot at a tighter leading of **1.07** (`round(42 × 1.07)` = 45 px)
before moving to the next spot. New constant `_FALLBACK_NOTE_TIGHT_LEADING
= 1.07` beside `_FALLBACK_NOTE_LEADING`. Result: landscape pages keep 1.2;
the square corners print 10 lines at 45 px. DejaVu Sans at 42 px has cap
height ≈ 31 px and descender ≈ 9 px, so about 5 px (0.4 mm) of white stays
between a descender and the next line's caps. This is owner-visible (tighter
lines in the square corner).

Alternatives the owner may pick instead (each changes this card):
- (b) Use 1.07 for every fallback note, not only when 1.2 fails (one
  leading, simpler code; landscape renders tighten too).
- (c) Keep the units glued where they fit and accept the old wrap on squares
  only — this leaves the exact breaks F-004 named, so it does not meet the
  idea.

If no spot holds the note at either leading, keep today's `ValueError`
("no room for the proof note"). 15×15 cm and 20×20 cm still refuse
(measured).

**Portrait output does not move.** The portrait trims all take the foot path,
which never calls `_wrapped`, so CARD-172's AC-6 digests
(tests/fixtures/proof_baseline_card172.json) stay as they are. No new
baseline is recorded. If the implementer finds a portrait digest moving, that
is a bug in this change, not a new baseline.

Update the docstrings of `_wrapped`, `_fallback_note` and `_annotate` to say
what breaks are allowed and when the tight leading is used.

## Acceptance criteria

- **AC-1:** Given the four fallback trims (8.25×8.25, 8.5×8.5, 8.25×6, 11×8.5 in, Book 1 margins), when the note is wrapped for each fallback page, then no printed line ends with a bare number whose unit (`mm`, `in)`, `dpi`) starts the next line, and no printed line starts with `×`.
  *test: TestBookProof_WrappedNoteKeepsUnitsWithNumbers (in tests/test_book_proof_pages.py) — reads the lines `_fallback_note` returns for each of `FALLBACK_PAGES`; fails on main (8.25×8.25 p1 prints `cell 4.58` / `mm`; 8.25×6 starts a line with `× 6.00 in)`)*
- **AC-2:** Given those pages, when the note is wrapped, then every "N × M" group whose own width fits the spot sits on one line, and the one group that does not (8.25×6's `209.6 × 152.4 mm`) breaks only after the ×, with `152.4 mm` together on the next line.
  *test: TestBookProof_WrappedNoteKeepsUnitsWithNumbers (in tests/test_book_proof_pages.py) — fails on main (`grid 30 ×` / `30,` on the squares)*
- **AC-3:** Given seeded widths from 250 to 520 px and the notes of every `CORPUS_TRIMS_CM` and `FALLBACK_TRIMS_CM` trim, when `_wrapped` is called, then it returns `None` or lines that obey rules 1–3, rejoin (spaces normalised) to the input text, and each fit the width; at least 200 cases are checked, asserted inside the test.
  *test: test_PropertyTest_ProofNoteWrap_NeverSplitsAUnitOrStartsWithTimes (in tests/test_book_proof_pages.py)*
- **AC-4:** Given 8.25×8.25 and 8.5×8.5 in, when `proof_pages` runs, then both still return 2 pages and page 1's note still sits inside the blank clue corner, clear of every rule and digit by 1 mm (the existing AC-1 tests of CARD-172 stay green, unchanged); its printed line pitch is 45 px (the tight leading) and the 8.25×6 and 11×8.5 side-strip notes keep 50 px.
  *test: TestBookProof_SquareTrimsCarryTheNote (existing, unchanged) + TestBookProof_FallbackLeadingTightensOnlyWhenNeeded (in tests/test_book_proof_pages.py) — pitch read off the ink line bands*
- **AC-5:** Given 15×15 cm, when proof pages are requested, then `proof_pages` still raises "no room for the proof note" and the route still flashes it.
  *test: test_a_trim_with_no_room_for_the_note_is_refused_and_says_so + test_a_trim_with_no_room_for_the_note_is_reported_not_served (existing, unchanged)*
- **AC-6:** Given the nine portrait trims at the Book 1 margins, when both proof pages are rendered, then each page's digest equals the CARD-172 baseline.
  *test: TestBookProof_PortraitProofsAreByteIdentical (existing, unchanged; tests/fixtures/proof_baseline_card172.json not edited)*
- **AC-7:** The owner has looked at the square and landscape proofs and accepts the new breaks and the tighter square-corner leading (or picks alternative (b) or (c)).
  *test: review-lens (owner visual check of the renders)*

## Guardrails

- G-1: Portrait proofs are byte-identical (AC-6). The foot path, `_fitted_note_font`, `_NOTE_MM`, `_NOTE_FLOOR_MM`, `_NOTE_LEADING` and `_NOTE_GAP_MM` are not changed.
- G-2: `annotation_lines` text is unchanged (CARD-172 G-5); the rule lives in `_wrapped`, not in the note's wording.
- G-3: The fallback face stays 10 pt (CON-020 floor; `TestBookProof_FallbackNoteHoldsTheTenPointFloor`). Spot order (side strip, then corner), `_FALLBACK_INSET_MM` and the spot geometry in `_fallback_spots` are unchanged.
- G-4: The note never enters a margin and never overprints a rule or digit (`TestBookProof_SquareTrimsCarryTheNote`, `TestBookProof_LandscapeTrimsCarryTheNote`, the CARD-172 property test). Still exactly 2 proof pages.
- G-5: The note stays proof-only. `book_pdf_generator.py` and `src/nonogram/export/**` are not edited (`TestBookProof_AnnotationIsProofOnly`, CON-019 golden `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`). Book PDF pixel baselines (`tests/fixtures/book_baseline_*.json`) do not move.
- G-6: `test_no_wrapped_line_starts_with_a_separator_dot` stays green. No new dependency (ADR-0006/R1).

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-179` (52 rules). A projection — fix the source artifact, never this list._

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

- FR-033 (trace: final values confirmed by the owner on printed proof pages — an owner checkpoint). No FR AC names the proof note; AC-1..AC-7 are card-local.
- ADR-0037 (proof step), ADR-0036/R2 (geometry only from COMP-007 — this card places nothing new), ADR-0006/R1.
- CON-020 (10 pt floor, applied to the fallback note per CARD-172), CON-019 (A4 golden).
- COMP-009 (Admin Panel: `src/nonogram/admin/book_proof.py`). COMP-007 is read only.
- Trace: IDEA-099 ← CARD-172 review F-004 (meta/review/20261004T152453Z-CARD-172-cycle1.yml).

## Design context

- Output: the proof-pages PDF from Print setup's "Download proof pages" (`GET /book/<id>/proof-pages`). Not a book page.
- Owner-visible default: on square trims the corner note grows from 9 to 10 lines at a tighter 45 px line pitch; on 8.25×6 the trim line breaks as `trim 209.6 ×` / `152.4 mm`. Portrait proofs do not change.
- Renders: ~/Documents/nonogram-reviews/CARD-179/ (owner visual check) — `proof-pages-{8.25x8.25,8.5x8.5,8.25x6,11x8.5}.pdf`, a PNG of each fallback page, and a README.txt listing each page's printed lines before and after. Never beside the repo.

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-099 "Proof-note wrap splits '4.58 / mm' and starts lines with ×" (CARD-172 F-004; the owner accepted the CARD-172 renders as they are, so this is a readability improvement, not a defect fix).
- [Facts] book_proof.py on main: `_FALLBACK_NOTE_LEADING = 1.2` :138, `_NOTE_SEPARATOR` :150, `annotation_lines` :353, `_fitted_note_font` :420, `_fallback_spots` :474, `_wrapped` :523, `_fallback_note` :551, `_annotate` :573. Only tests/test_book_proof_pages.py imports `book_proof` among the tests.
- [Facts] The foot path prints `annotation_lines` whole (`block = list(lines)`), so the idea's "in any placement" reduces to the two fallback spots. Portrait digests cannot move; no new baseline commit is needed.
- [Measured] Spot widths: 8.25×8.25 corner 457 px, 8.5×8.5 corner 474 px, 8.25×6 side 375/374 px, 11×8.5 side 413 px. Heights: corner 457 / 474 px. Group widths at 42 px: `209.6 × 152.4 mm` 398, `279.4 × 215.9 mm` 398, `(8.25 × 6.00 in)` 333, `(11.00 × 8.50 in)` 360, `30 × 30,` 182, `4.58 mm` 189.
- [Measured] With rules 1–3: squares 10 lines (refused at 1.2, fit at 1.07 with 7 px / 24 px spare), 8.25×6 12 lines, 11×8.5 10 lines; 15×15 cm and 20×20 cm still refused. Gluing every "N × M mm" group unconditionally makes 8.25×6 refuse (398 > 375 px) — hence rule 3.
- [Pitfall] If gluing is done with a placeholder character (e.g. NUL or NBSP), measure the width with real spaces. In the probe, `font.getlength` on a NUL-glued token over-measured and wrongly refused 11×8.5.
- [Owner decision needed] Leading: default is "1.2, then 1.07 in the same spot" (alternatives (b) and (c) in What to implement). AC-4 and AC-7 follow the default; if the owner picks (b), AC-4's "side-strip notes keep 50 px" becomes 45 px.
- [Test] The new AC-1/AC-2 test reads `_fallback_note`'s returned lines (private seam, same module); AC-4's pitch check reads ink line bands with the existing `_runs` helper (tests/test_book_proof_pages.py:197). Existing test `test_no_wrapped_line_starts_with_a_separator_dot` (:1112) still applies.
- [AC cross-check] ACs re-read against What to implement: placement order (foot, side strip, corner) unchanged; tight leading tried per spot before the next spot — AC-4 matches. AC-2's exception names the only over-wide group measured.
