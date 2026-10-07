# CARD-199: Extend KDP's gutter table past 300 pages so larger books still finalise

**Status:** done
**Priority:** P2
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/199-kdp-gutter-table-extend
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-CARD-199
**Source:** CARD-198's own finding (a book that finalised fine before CARD-198 can cross 300 pages once it ships); card drafter's research into KDP's published gutter/page-count tables, 2026-10-07
**Idea:** —
**Wave:** 37
**Depends on:** —
**Touches:** src/nonogram/admin/book_kdp.py, tests/test_book_finalise_gutter.py
**Review score:** 9.5 (cycle 1/3)
**Started:** 2026-10-07T12:00:00Z
**Closed:** 2026-10-07T13:50:28Z
**Actual:** 0.1d
**Merge commit:** 7d4bcf8
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading `book_kdp.py` in full).** `KDP_GUTTER_BANDS`
(`book_kdp.py:88-91`) holds exactly two entries — `(150, 0.375in)`, `(300, 0.5in)` —
and `MAX_MODELLED_PAGE_COUNT = KDP_GUTTER_BANDS[-1][0]` (`:95`) is therefore `300`.
`kdp_page_band` (`:167-188`) and `kdp_min_gutter_cm` (`:191-208`) both raise
`KdpPageCountNotModelled` (`:102-123`) for any page count above 300, and the
module's own docstring (`:27-38`) already says why: KDP's real table continues
past 300, but "which numbers those are is a business fact this project has not
recorded," and the fix is "to record the rest of KDP's table, not to widen this
one by hand." `gutter_refusal` (`:253-290`), `kdp_min_gutter_inches` (`:211-217`),
`stored_gutter_cm` (`:220-250`) and `_rounded`/`_floored` (`:131-154`) are all
generic over whatever `KDP_GUTTER_BANDS` holds — none of them hardcodes 150 or
300 in logic, only in docstring prose and the one parametrize/`KDP_BAND_TEXT`
constant the test file uses for the *existing* two bands.

**Why this matters now.** CARD-198 turns the book's answer key into one full
page per puzzle. Its own "What to implement" section measured the consequence:
the 150-puzzle corpus book goes from a 182-page interior to roughly 305 pages —
over today's 300-page ceiling, where Finalise now refuses outright with
`KdpPageCountNotModelled`, for a book shape that finalised fine before CARD-198.
This card is the "record the rest of KDP's table" fix the module's own
docstring calls for, so that regression doesn't ship with CARD-198.

**Research done for this card (so the implementer does not have to re-derive
it) — two separate numbers, and they do not agree.**

1. **KDP's gutter-margin table, by page count (trim-independent, as the
   module already treats it).** Fetched directly from KDP's own help topic
   ("Set Trim Size, Bleed, and Margins",
   `https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6`, retrieved
   2026-10-07) and cross-checked against three independent secondary guides
   (scribecount.com, vappingo.com, kdpbuilder.com) that all state the same
   five bands:
   - 24-150 pages — 0.375 in (today's first band, unchanged)
   - 151-300 pages — 0.5 in (today's second band, unchanged)
   - 301-500 pages — 0.625 in
   - 501-700 pages — 0.75 in
   - 701-828 pages — 0.875 in
2. **KDP's absolute maximum page count for a black-ink, white-paper
   paperback — and it is trim-dependent.** The 828-page ceiling above is
   what KDP states for its 5"x8", 5.5"x8.5" and 6"x9" trims. For **8.5"x11"
   — CON-018's Book 1 profile, the only trim this project's real books use**
   — the same help topic (and the independently-fetched "Paperback
   Submission Guidelines" topic, `G201857950`) states a *lower* ceiling:
   **590 pages** (550 on cream paper, which this project does not model —
   `grep`"ed the whole of `src/nonogram`for "cream"/"paper_type"/"paper_color"`
   and found nothing, so there is no column to tell the two apart; treat
   every book as white paper, the more permissive case).

   590 falls **inside** the general table's 501-700 band, not at a band
   boundary — so the physically real ceiling for this project's one trim is
   not 828, it is 590, and the 701-828 band is unreachable for an 8.5"x11"
   book regardless of its gutter margin. Modelling a gutter minimum for
   601-700 pages would be worse than the current silence: it would let such
   a book pass *this* check and still be rejected at upload for exceeding
   KDP's absolute page-count cap on that trim — the exact "looked finished,
   rejected at upload" failure CON-018/ADR-0036 exist to prevent, just moved
   from the 150-page boundary to a new one.

**What to implement, following from that research.** Extend
`KDP_GUTTER_BANDS` with **two** new entries, stopping the table at this
project's real, trim-accurate ceiling rather than the general 828:

```python
KDP_GUTTER_BANDS: Tuple[Tuple[int, Decimal], ...] = (
    (150, Decimal("0.375")),
    (300, Decimal("0.5")),
    (500, Decimal("0.625")),
    (590, Decimal("0.75")),
)
```

`MAX_MODELLED_PAGE_COUNT` becomes `590` automatically (it is computed as
`KDP_GUTTER_BANDS[-1][0]`, `book_kdp.py:95` — no change needed there). The
last band's upper bound is `590`, not the general table's `700`, precisely
because this module has no trim parameter and the project's one real trim
caps out there; a comment at the new entries must say so and cite the two
help-topic URLs above, the way the module docstring already cites "how KDP
states it" for the first two bands.

**Caller check (per the brief — confirmed by reading each one, not
assumed).**
- `kdp_page_band`, `kdp_min_gutter_cm`, `kdp_min_gutter_inches`,
  `gutter_refusal`: all generic loops over `KDP_GUTTER_BANDS` / compare
  against `kdp_page_band`'s result. No code change — they automatically
  pick up the new bands and the new ceiling.
- `unpaired_interior_page_count` (`book_kdp.py:298-357`): reads
  `interior_page_count`, `print_order`, `tier_of_record` and
  `pack_answer_pages` — it never references `KDP_GUTTER_BANDS` or
  `MAX_MODELLED_PAGE_COUNT` today, and must not gain that dependency. No
  change.
- `app.py`'s `_kdp_gutter_refusal` (`app.py:1101-1140`, CARD-153's Finalise
  gate): already catches `KdpPageCountNotModelled` and relays
  `gutter_refusal`'s text generically, naming whatever page count and band
  the exception carries. No change.
- `CON-018` (`meta/architecture/requirements.yml:5262-5281`): its statement
  is about Book 1's *fixed default* gutter (0.5 in) and the two bands that
  default straddles; it never claimed the table was exhaustive above 300
  pages, so this card amends nothing under `meta/`.

**Documentation that does need rewriting (prose, not logic).** The module
docstring's "Two bands" framing (`:21`), the "up to 150... / 151 to 300..."
list (`:24-25`), the "Above 300 pages... silent" paragraph (`:27-38`), and
the illustrative `(1, 150)` / `(151, 300)` pairs in `kdp_page_band`'s and
`kdp_min_gutter_cm`'s docstrings (`:170`, `:194`) all need updating to
describe four bands and the new 590-page ceiling, with the research above
(both URLs, the three corroborating guides, and the 590-vs-828 trim
distinction) recorded in the module docstring the same way the existing one
explains its own two bands.

## Acceptance criteria

- **AC-1** (happy, new 301-500 band): *Given* page counts 301, 400 and 500,
  *when* `kdp_page_band`/`kdp_min_gutter_cm` are called, *then* the band is
  `(301, 500)` and the minimum is 1.59 cm (0.625 in).
  *test: TestKdpGutterTable::test_the_minimum_for_each_band (extended) (in tests/test_book_finalise_gutter.py)*
- **AC-2** (happy, new 501-590 band): *Given* page counts 501, 550 and 590,
  *when* `kdp_page_band`/`kdp_min_gutter_cm` are called, *then* the band is
  `(501, 590)` and the minimum is 1.91 cm (0.75 in).
  *test: TestKdpGutterTable::test_the_minimum_for_each_band (extended) (in tests/test_book_finalise_gutter.py)*
- **AC-3** (boundary, the real ceiling still has a modelled gutter): *Given*
  `page_count == MAX_MODELLED_PAGE_COUNT` (590), *when* `kdp_min_gutter_cm`
  is called, *then* it returns 1.91 cm rather than raising
  `KdpPageCountNotModelled` — the real KDP ceiling for this project's trim
  is inside the modelled table, not past it.
  *test: TestKdpGutterTable::test_the_real_kdp_ceiling_still_has_a_modelled_gutter (new) (in tests/test_book_finalise_gutter.py)*
- **AC-4** (negative, refuses above the new ceiling): *Given* page counts
  591, 700 and 10,000, *when* `kdp_page_band`/`kdp_min_gutter_cm` are called,
  *then* `KdpPageCountNotModelled` is raised naming "not modelled above 590
  pages" — the same refusal shape as today, moved to the new ceiling.
  *test: TestKdpGutterTable::test_above_the_real_ceiling_it_refuses_rather_than_guessing (renamed/reparametrized from test_above_three_hundred_pages_it_refuses_rather_than_guessing) (in tests/test_book_finalise_gutter.py)*
- **AC-5** (happy, Finalise refuses correctly inside a new band): *Given* a
  book whose interior runs to about 350 pages (inside the new 301-500 band)
  storing only a 0.5 in gutter, *when* the book is finalised, *then* it is
  refused naming the 301-500 band and its 1.59 cm (0.625 in) minimum — not
  the old "not modelled" wording, and not a silent accept.
  *test: TestBookFinalise_RefusesGutterInANewBandBeyondThreeHundredPages (new) (in tests/test_book_finalise_gutter.py)*
- **AC-6** (happy, CARD-198's own regression scenario): *Given* a book whose
  interior runs to about 305 pages (CARD-198's 150-puzzle-corpus figure,
  previously refused outright because it sat above the old 300-page
  ceiling) storing a gutter that meets the new 301-500 band's minimum,
  *when* the book is finalised, *then* it finalises — no
  `KdpPageCountNotModelled` refusal.
  *test: TestBookFinalise_ABookJustOverTheOldThreeHundredPageCeilingNowFinalises (new) (in tests/test_book_finalise_gutter.py)*
- **AC-7** (guardrail made testable, 150-300 unchanged): *Given* page counts
  1, 150, 151 and 300, *when* `kdp_page_band`/`kdp_min_gutter_cm` are called,
  *then* they return exactly today's bands and minima (0.9525 cm/150,
  1.27 cm/300) — the two existing bands are not renumbered or re-valued by
  this card.
  *test: TestKdpGutterTable::test_the_band_is_named_as_a_page_range, test_the_bands_are_the_two_the_requirements_state (renamed to reflect four bands) (in tests/test_book_finalise_gutter.py)*

## Guardrails

- G-1: CON-018's existing rounding tests stay green, **unedited**:
  `TestKdpGutterTable::test_the_stored_two_decimal_form_of_a_band_is_that_band`,
  `test_the_projects_own_spelling_of_each_minimum_still_passes`,
  `test_a_stored_gutter_is_never_rounded_up_into_compliance`,
  `test_the_refusal_reads_the_stored_column_and_writes_nothing`,
  `test_an_empty_column_is_the_profiles_own_gutter` (all in
  `tests/test_book_finalise_gutter.py`). None of them reads a page count
  above 300, so none of them needs a code or assertion change.
- G-2: The two existing bands' boundaries and values — `(150, 0.375in)` and
  `(300, 0.5in)` — and the `KDP_BAND_TEXT` constant
  ("1.27 cm (0.5 in) for 151-300 pages", `tests/test_book_finalise_gutter.py:72`)
  are unchanged. New entries are appended after them, same tuple shape,
  ascending by page count.
- G-3: `unpaired_interior_page_count`'s signature, arithmetic and exception
  shape are unchanged — it does not read `KDP_GUTTER_BANDS` or
  `MAX_MODELLED_PAGE_COUNT` today and must not gain that dependency.
  Exercised unedited by `TestBookFinalise_RefusesGutterBelowKdpMinimumForPageCount`
  and `TestFinaliseCounts_PlanTripwireIsNotAnEstimate` (both in
  `tests/test_book_finalise_gutter.py`).
- G-4: `app.py`'s `_kdp_gutter_refusal`/Finalise gate (CARD-153) is not
  edited. `TestFinaliseGet_NamesThePagePlanFailure`,
  `TestFinaliseGet_OtherErrorsStayGeneric`,
  `TestFinalisePost_PlanGateRefusalIsNotAnError` (all in
  `tests/test_book_finalise_gutter.py`) pass unedited.
- G-5: The rounding-direction rules — half-up for a band minimum
  (`_rounded`), floor for a stored gutter (`_floored`) — apply identically
  to the two new bands; no new rounding behaviour is introduced.
- G-6: `KdpPageCountNotModelled` stays a plain `ValueError`, not a
  `nonogram.errors.NonogramError` subclass — unaffected by this card;
  `tests/test_web_submission.py::test_the_walked_corpus_is_the_whole_hierarchy`
  is untouched.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-199` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-030/CON-018 — the gutter rule this table models; CON-018's own
  statement describes Book 1's fixed default and the two bands it
  straddles, and never claimed the table was exhaustive above 300 pages, so
  no `meta/` edit is needed.
- **ADR:** ADR-0036's clarification ("Gutter margin and page count") — this
  card is exactly the "record the rest of KDP's table" remedy its own
  `book_kdp.py` docstring names; the refuse-rather-than-iterate design
  (G-2 of that ADR) is unaffected, only the table it refuses against grows.
- **CON:** CON-018 (unaffected, see above).
- **Components:** COMP-009 (`book_kdp.py` lives here, same as CARD-153 and
  CARD-198).
- **Trace:** meta/architecture/trace.yml — not updated by this card (no
  edit under `meta/`).

## Worktree notes

- [Origin] CARD-198's "What to implement" section names the regression this
  card exists to prevent: its 150-puzzle corpus book goes from 182 to
  roughly 305 interior pages, crossing the then-300-page ceiling. This card
  was drafted to land before or alongside CARD-198 so Finalise does not
  regress when CARD-198 ships. **Recommend CARD-198 record a `Depends on:
  CARD-199` (or the two land in the same merge window) — this card does not
  edit CARD-198's files and can be implemented and merged independently,
  but CARD-198's own 305-page example needs this card's 301-500 band to
  finalise.**
- [Research, 2026-10-07] Fetched `https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6`
  ("Set Trim Size, Bleed, and Margins") and
  `https://kdp.amazon.com/en_US/help/topic/G201857950` ("Paperback
  Submission Guidelines") directly, and cross-checked against three
  independent secondary guides (scribecount.com, vappingo.com,
  kdpbuilder.com) via web search the same day. All agree on the general
  five-band gutter table (150/0.375, 300/0.5, 500/0.625, 700/0.75,
  828/0.875 — in page-count/inches pairs). Independently, both the KDP
  help fetch and multiple secondary sources state the 8.5"x11" trim's
  absolute page-count ceiling as **590** pages (black ink, white paper),
  not 828 — 828 is what KDP states for 5"x8"/5.5"x8.5"/6"x9". This card
  recommends stopping `KDP_GUTTER_BANDS` at 590 (the trim this project
  actually ships, CON-018's Book 1 profile) rather than the general 828,
  because modelling a minimum for the unreachable 591-700/701-828 range
  would silently accept a book that KDP would reject at upload purely for
  exceeding its page-count cap, regardless of gutter — the same class of
  late failure CON-018/ADR-0036 already guard against. **This is a
  business fact about an external platform, not re-derivable from this
  repo; get a one-line owner nod on the 590-vs-828 choice before merging,
  the way CARD-198 flagged its own un-confirmed reading** — it should not
  block starting the implementation.
- [Verified facts the implementer must not re-derive] `KDP_GUTTER_BANDS`
  `book_kdp.py:88-91`; `MAX_MODELLED_PAGE_COUNT` `:95` (computed, no code
  change); `KdpPageCountNotModelled` `:102-123`; `kdp_page_band` `:167-188`;
  `kdp_min_gutter_cm` `:191-208`; `kdp_min_gutter_inches` `:211-217`
  (not in `__all__`, used internally by `gutter_refusal`); `stored_gutter_cm`
  `:220-250`; `gutter_refusal` `:253-290`; `_rounded`/`_floored` `:131-154`;
  `unpaired_interior_page_count` `:298-357` (no `KDP_GUTTER_BANDS`
  reference today); `_grid_extent` `:360-383` (unrelated, untouched).
  `app.py`'s `_kdp_gutter_refusal` `:1101-1140`, called at `:4494`.
  `tests/test_book_finalise_gutter.py`'s `TestKdpGutterTable` class
  (`:322-455`) is the whole of the existing unit coverage for the table
  itself; `KDP_BAND_TEXT` constant at `:72`. Grepped the whole of
  `src/nonogram` for "cream"/"paper_type"/"paper_color": no hits — the
  project does not model paper stock at all, so there is no column to
  distinguish the 590-page white-paper ceiling from cream paper's lower
  one; treat every book as the more permissive white-paper case, as the
  module already implicitly does for every other KDP figure it models.
- [Not in this card] Trim-aware modelling (a different `MAX_MODELLED_PAGE_COUNT`
  per stored trim, since `book_page_spec.py` already lets a book store a
  non-Book-1 trim) is a bigger change than "extend the table in the same
  shape" and is out of scope. If the owner later wants other trims
  supported at their own real page-count ceilings, that is a follow-up
  card, not this one.
- [AC cross-check] Re-read AC-1..AC-7 against "What to implement": AC-1/AC-2
  map to the two new table entries, AC-3/AC-4 to the new ceiling and its
  refusal, AC-5/AC-6 to the Finalise-level consequence (the second being
  CARD-198's own motivating scenario), AC-7 pins the two bands this card
  must not change. No AC asks for a band or page count the body doesn't
  also name.
- [Estimate] 0.5d. The research (the harder, less certain part) is done and
  recorded above; what remains is a two-entry table extension, a module
  docstring rewrite, and rewriting/adding roughly seven test cases in one
  existing file — no new production module, no pixel/render work (this is
  a pure data/logic card; see Design context note below).
- **Design context omitted.** This card changes no print layout and no
  owner-visible page geometry — only the gutter table's data and the
  Finalise refusal text's wording for page counts above 300. No render is
  needed for the owner (per the brief's own instruction for this card).
- [Owner decision] 2026-10-07 — use 590 (trim-accurate for Book 1s 8.5×11 in profile), not KDPs general 828-page table.
- [Env] forge 2026.8.17

- [Implementation, 2026-10-07] Both files touched exactly as scoped
  (`src/nonogram/admin/book_kdp.py`, `tests/test_book_finalise_gutter.py`),
  nothing under `meta/` committed.
  - `KDP_GUTTER_BANDS` extended to the four-entry tuple the card specifies —
    `(150, 0.375)`, `(300, 0.5)` byte-identical to before, `(500, 0.625)` and
    `(590, 0.75)` appended. `MAX_MODELLED_PAGE_COUNT` is `590` automatically
    (no code change). Verified none of `kdp_page_band`, `kdp_min_gutter_cm`,
    `kdp_min_gutter_inches`, `stored_gutter_cm`, `gutter_refusal`, `_rounded`,
    `_floored`, `unpaired_interior_page_count`, `_grid_extent` hardcode
    150/300 — confirmed by reading each (they loop/compare generically) — so
    none needed a logic change, only the table and three docstrings
    (module-level "The table, and where it stops" section, the new comment
    block above `KDP_GUTTER_BANDS`, and the illustrative examples in
    `kdp_page_band`/`kdp_min_gutter_cm`). Both URLs
    (`GVBQ3CMEQW3W2VL6`, `G201857950`), the three secondary guides
    (scribecount.com, vappingo.com, kdpbuilder.com) and the 590-vs-828 trim
    distinction are cited in both the comment above the table and the module
    docstring, following the existing citation style (inline prose + plain
    URLs, same as CON-018's own citation pattern already in the file).
  - Test file: added `KDP_BAND_TEXT_301_500` / `KDP_BAND_TEXT_501_590`
    constants (mirroring `KDP_BAND_TEXT`, left untouched per G-2) and two new
    corpora, `AC199_NEW_BAND_CORPUS` (277 medium `alone`s -> 350 pages) and
    `AC199_CARD198_CORPUS` (241 medium `alone`s -> 305 pages, CARD-198's own
    figure), both verified against the real export page plan in a
    `test_the_scenario_really_has_that_many_pages` test, not assumed.

  **AC-by-AC test names:**
  - AC-1 -> `TestKdpGutterTable::test_the_minimum_for_each_band` (extended
    with 301/400/500 rows) and `TestKdpGutterTable::test_the_band_is_named_as_a_page_range`
    (extended with a `(301, (301, 500))` etc. row).
  - AC-2 -> same two tests, extended with 501/550/590 rows.
  - AC-3 -> `TestKdpGutterTable::test_the_real_kdp_ceiling_still_has_a_modelled_gutter`
    (new).
  - AC-4 -> `TestKdpGutterTable::test_above_the_real_ceiling_it_refuses_rather_than_guessing`
    (renamed/reparametrized from `test_above_three_hundred_pages_it_refuses_rather_than_guessing`,
    now `[591, 700, 10_000]`, asserting "not modelled above 590 pages").
  - AC-5 -> `TestBookFinalise_RefusesGutterInANewBandBeyondThreeHundredPages`
    (new class, 4 tests).
  - AC-6 -> `TestBookFinalise_ABookJustOverTheOldThreeHundredPageCeilingNowFinalises`
    (new class, 2 tests).
  - AC-7 -> `TestKdpGutterTable::test_the_band_is_named_as_a_page_range` (the
    four rows for 1/150/151/300 are byte-unchanged in outcome) and
    `TestKdpGutterTable::test_the_bands_are_the_four_the_requirements_state`
    (renamed from `test_the_bands_are_the_two_the_requirements_state`,
    asserting all four bands and `MAX_MODELLED_PAGE_COUNT == 590`).

  **Guardrails:**
  - G-1: `test_the_stored_two_decimal_form_of_a_band_is_that_band`,
    `test_the_projects_own_spelling_of_each_minimum_still_passes`,
    `test_a_stored_gutter_is_never_rounded_up_into_compliance`,
    `test_the_refusal_reads_the_stored_column_and_writes_nothing`,
    `test_an_empty_column_is_the_profiles_own_gutter` — all present, byte-
    unedited (`git diff` confirms no hunk touches them), all green.
  - G-2: `(150, Decimal("0.375"))` and `(300, Decimal("0.5"))` are the first
    two tuple entries, unchanged; `KDP_BAND_TEXT = "1.27 cm (0.5 in) for
    151-300 pages"` is untouched; new entries appended after, ascending.
  - G-3: `unpaired_interior_page_count` not edited (confirmed by diff — zero
    hunks in that function); `TestBookFinalise_RefusesGutterBelowKdpMinimumForPageCount`
    and `TestFinaliseCounts_PlanTripwireIsNotAnEstimate` are present, byte-
    unedited, green.
  - G-4: `app.py` not touched at all (not in the diff);
    `TestFinaliseGet_NamesThePagePlanFailure`,
    `TestFinaliseGet_OtherErrorsStayGeneric`,
    `TestFinalisePost_PlanGateRefusalIsNotAnError` present, byte-unedited,
    green.
  - G-5: no new rounding code — `_rounded`/`_floored` are unedited (confirmed
    by diff, zero hunks there); the new bands flow through the same two
    functions, verified by `gutter_refusal(400, 1.59)`/`(550, 1.91)` ->
    `None` and the "stores N cm" floored-not-rounded wording appearing in
    AC-5's refusal test, same mechanism as the pre-existing bands.
  - G-6: `KdpPageCountNotModelled` class definition not touched (still
    `class KdpPageCountNotModelled(ValueError):`, confirmed by diff — the
    hunk only edits its docstring's prose, not its base class or body);
    `tests/test_web_submission.py::test_the_walked_corpus_is_the_whole_hierarchy`
    untouched and not part of this diff.

  **Mutants run (both reverted after confirming the failure, `git diff`
  clean before final commit):**
  - `[Mutant] (590, Decimal("0.75")) -> (591, Decimal("0.75")) (the new
    ceiling, 590->591) -> caught by test_the_real_kdp_ceiling_still_has_a_modelled_gutter
    (kdp_page_band(590) returned (501, 591) instead of (501, 590)), also by
    test_the_bands_are_the_four_the_requirements_state, three
    test_the_band_is_named_as_a_page_range[501/550/590] cases, and all three
    test_above_the_real_ceiling_it_refuses_rather_than_guessing[591/700/10000]
    cases (message said "not modelled above 591 pages", the assertion
    expects "590").`
  - `[Mutant] (500, Decimal("0.625")) -> (500, Decimal("0.65")) (the new
    301-500 band's minimum value) -> caught by
    test_the_minimum_for_each_band[301-1.5875]/[400-1.5875]/[500-1.5875]
    (kdp_min_gutter_cm returned 1.651 instead of 1.5875), and by all three
    tests in TestBookFinalise_RefusesGutterInANewBandBeyondThreeHundredPages
    plus both tests in
    TestBookFinalise_ABookJustOverTheOldThreeHundredPageCeilingNowFinalises
    (the 1.59cm-gutter book that should finalise was instead refused, since
    1.59 < the mutated 1.65cm minimum).`

  **Full suite:** `./.venv/bin/python -m pytest` (run from the worktree root
  using the main repo's `.venv`) — 6647 passed, 9 skipped, 0 failed (853s),
  per the implementation agent's own run; the orchestrator's independent
  test-gate run is recorded separately below.
- [Scope] src/nonogram/admin/book_kdp.py, tests/test_book_finalise_gutter.py
- [Build gate] broke stale full-suite lock (CARD-193, 2026-10-07T13:08:48Z) —
  the break was a bug in this orchestrator's own lock script (a `date -j -f`
  parse without `-u`, which read the owner timestamp as local time against a
  UTC "now", inflating the apparent age by the ~3h zone offset); the lock was
  in fact only ~6 minutes old, not stale. CARD-193's own board/dispatcher
  entries show no distress afterward and its full-suite lock use is
  cooperative (a broken lock cannot kill an in-flight pytest process, only
  let a second one start), but this may have run two full suites
  concurrently for a few minutes. No corruption observed: this run's own
  result (6647 passed, 9 skipped, 0 failed) matches the implementation
  agent's independently-run full suite on the same commit exactly.
- [Build gate] PASSED (full, 865s) — orchestrator's own independent run,
  ./.venv/bin/python -m pytest from the worktree root: 6647 passed, 9
  skipped, 0 failed. Matches the implementation agent's own full-suite run
  on the same commit (2eb950b).
- [System contract] fresh `system_rules.py --card CARD-199` assembly (52
  rules) matches the card's existing "## System contract" section exactly —
  no refresh needed.
- [Review 1/3] Score: 9.5 — crit: 0, imp: 0. Scope gate: IN_SCOPE (actual
  diff files == Touches exactly, no guardrail-glob hits, no comp spread).
  8h: 52 rules checked, 2 ✓ holds (ADR-0006/R1, ADR-0019/R1), 50 ⚠ unchecked
  (no_eligible_fact), 0 ✗ violated. 8f mutation check: 3/3 targeted mutants
  killed (590→591 ceiling, 0.625→0.65 and 500→499 band-boundary/value on the
  new 301-500 band), no survivors, clean restore verified. AC-5/AC-6's
  350/305-page fixtures independently confirmed against the real
  BookPDFGenerator export, not assumed.
- [Review sync] 1 report(s) → meta/review/ (20261007T133651Z-CARD-199-cycle1.yml,
  validated parsable YAML via yaml.safe_load: overall_score 9.5, findings: []).
- [Adversarial] no Critical/Important findings this cycle — nothing to verify
  (adversarial verification loop is vacuous by construction).
- [8h spot-check] 2/2 sampled holds reproduced (ADR-0006/R1 via independent
  skeptic: re-ran test_the_dependency_baseline_is_still_closed, "1 passed, 58
  deselected"; ADR-0019/R1 via independent skeptic: re-ran
  test_every_import_in_the_package_points_inward, "1 passed, 93 deselected,
  1 warning" — both confirmed no new/boundary-crossing import, diff stat
  limited to the two scoped files).
- [Review N/max] Score: 9.5 ✓ threshold reached + no critical/important
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-1..AC-7 and G-1..G-6
  all verdict "✓ demonstrated" by an independent AC-check agent (fresh
  context), via `./.venv/bin/python -m pytest` runs in the worktree —
  targeted run "68 passed, 44 deselected" covering every named AC/G test,
  plus G-6's cross-file `tests/test_web_submission.py::test_the_walked_corpus_is_the_whole_hierarchy`
  run directly ("1 passed"), plus a full-file sanity run of
  `tests/test_book_finalise_gutter.py` ("112 passed"). AC-5/AC-6's claimed
  350/305-page fixtures confirmed to assert against the real
  `BookPDFGenerator(book).interior_stream(rows)` export (not mocked/hardcoded).
  G-1/G-3/G-4's named tests confirmed byte-unedited by diff inspection; G-2's
  two existing band tuples and `KDP_BAND_TEXT` confirmed unchanged; G-5's
  `_rounded`/`_floored` confirmed to have zero diff hunks; G-6's
  `KdpPageCountNotModelled(ValueError)` class line confirmed unchanged.
  13/13 items demonstrated, 0 unverified, 0 contradicted.
- [Docs] No README update needed: `src/nonogram/admin/` has no README.md;
  `tests/README.md` makes no reference to the gutter table or its page-count
  ceiling. Structure/purpose of both touched directories is unchanged by this
  card (no files added/removed/renamed). Skipped, current.
- [Success] Commit `2eb950b` (made by the implementation agent, verified
  independently by the orchestrator's own full-suite run, the review agent,
  two holds-skeptics, and the AC/EC check agent — all against this same
  commit) stands as this card's success commit; no fix cycle ran, so there
  is nothing to add to it. Only `meta/` artefacts (this card's own notes,
  the review YAML report) remain uncommitted in the worktree, per the
  wave-37 brief's "nothing under meta/ from the worktree" rule — both are
  synced into the main repo by this orchestrator instead of being committed.
