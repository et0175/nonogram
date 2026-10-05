# CARD-184: One test holds every interior face to CON-020's 10 pt floor, and the two faces below it today are fixed

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/184-interior-type-floor
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-05 (IDEA-008, WSJF 7.0; folds in the divider half of IDEA-087)
**Idea:** IDEA-008
**Wave:** 34
**Depends on:** —
**Touches:** tests/test_book_interior_type_floor.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/export/layout.py, tests/helpers/book_corpus.py, tests/fixtures/book_baseline_card184.json, tests/test_book_pdf_ink_mode.py, tests/test_book_pdf_memory.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

CON-020 says no text the book's interior prints for the reader is below 10 pt
at the page's DPI. Its check is `review-lens` because no test walks every
interior face. CARD-149 and CARD-167 test the guide page only.

**Current behaviour (measured 2026-10-05 by spying on `ImageFont.truetype` /
`load_default` during `export_interior` of `book_corpus.baseline_puzzles()`,
300 DPI).** Every face the interior asks for:

| Face | Where | Book 1 (8.5×11 in) | 10×10 cm (min trim) |
|---|---|---|---|
| guide title | `create_guide_page` (`type_px(GUIDE_TITLE_PT)`) | 92 px = 22.08 pt | 87–92 px ≥ 20.9 pt |
| guide body + captions | `create_guide_page` | 46 px = 11.04 pt | same |
| worked-example clue digits | `draw_example_line` | 55 px = 13.20 pt | same |
| band "Puzzle N · Tier" | `_set_band` / `pdf._measure_header` (`HEADER_FONT_MM` 5 mm) | 59 px = 14.16 pt | same |
| level / SOLUTIONS divider | `create_divider_page` (bare `60` px) | 60 px = 14.40 pt | same |
| **answer heading + captions** | `png.render_answer_page` (`layout.ANSWER_TEXT_FONT_MM` 3.5 mm) | **41 px = 9.84 pt** | **41 px = 9.84 pt** |
| puzzle clue digits | `png._clue_font`, `_write_clues` (`pitch × 0.62`) | 36–55 px = 8.64–13.20 pt | 15–39 px = 3.60–9.36 pt |

Two faces break the floor today, and a third is out of its reach by nature:

1. **Answer key heading and captions: 9.84 pt.** `layout.py:2007`
   `ANSWER_TEXT_FONT_MM = 3.5`, commented "roughly 10 pt". 3.5 mm is 9.92 pt,
   and `_mm_to_px` rounds 41.34 px down to 41 px = 9.84 pt. Used at
   `layout.py:2414` (heading) and `layout.py:2579` (caption). CON-020's own
   2026-09-30 measurement list skipped the answer key. **This card fixes it:**
   state the size as 10 pt (in millimetres, `10 * 25.4 / 72`, so COMP-007
   still needs no import), which gives 42 px = 10.08 pt. The caption and
   heading lines stay 6 mm (71 px), so `min(…, line)` does not bind and no
   geometry moves. Answer pages' pixels change → new baseline (Touches rule).
2. **Dividers on a machine without Arial: 2.4 pt.** `create_divider_page`
   (`book_pdf_generator.py:1649-1652`) asks `truetype("/System/Library/Fonts/Arial.ttf", 60)`
   and on `OSError` falls back to **unsized** `ImageFont.load_default()`, a
   ~10 px em. The deployed panel runs on Render (Linux), where that path does
   not exist. `_guide_face` (`:529`) already fixed this for the guide page.
   Also, 60 is a bare pixel count: at 600 DPI it would print at 7.2 pt.
   **This card fixes it:** add a `DIVIDER_PT = 14.4` constant, size the face with
   `type_px(DIVIDER_PT, self.dpi)` (exactly 60 px at 300 DPI, so pixels do not
   change on a machine with Arial), and letter through `_guide_face` (or the
   same sized-fallback shape), so the fallback is sized too.
3. **Puzzle clue digits: 3.6–9.4 pt on small cells. Recorded, not fixed.** A
   clue digit has to fit its cell, so it scales with it (`_CLUE_FONT_RATIO = 0.62`,
   `layout.py:326`). It reaches 10 pt only at a 5.74 mm cell. INV-006's
   4.8 mm membership floor gives 2.98 mm = 8.4 pt. Book 1's own 30×30 prints at
   8.64 pt. No setting satisfies CON-020 here without breaking the cell floor.
   CON-020's 2026-09-30 face list leaves clue digits out. The test exempts
   them **by name** (see AC-3), and the architect decides whether CON-020's
   statement should say so (Worktree notes).

Out of scope:
- **The cover's 72 px title** (`create_cover_page:1500`). The cover is not part of
  the interior (INV-013), so CON-020 does not govern it. That half of IDEA-087
  stays in the backlog.
- **The band's shrink path** (`_set_band`, `_MIN_BAND_FONT_RATIO = 1/3` → 4.7 pt).
  The longest band, "Puzzle 120 · Medium", is about a tenth of the measure,
  so the shrink is never reached. Not changed. The test would catch it if a
  corpus ever reached it.
- The proof pages (`book_proof.py`). Owner decision on CARD-172: a proof page
  is not interior.

**The test (`tests/test_book_interior_type_floor.py`, new).** Use a spy that can
fail. Wrap `PIL.ImageDraw.ImageDraw.text` for the length of one export. Record,
for every call: the font's size in px (`font.size`), or "unsized" when the font
is not a `FreeTypeFont`; the calling function (from the stack); and the interior
page it was drawn on. Iterate `generator.interior_stream(...)`/`interior_pages(...)`
to get the page. Convert px to points as `size * 72 / generator.dpi` and assert ≥ 10.0 for
every call outside the named clue-digit exemption. An unsized face always
fails. Why `draw.text` rather than the font constructors: `_band_font`,
`png._lettering_font` and `pdf._header_font` are `lru_cache`d. A
constructor spy misses any size an earlier test already asked for. The
measurement above was skewed that way until the caches were cleared. Spying
on what is *drawn* also leaves out the guide title's fitting probes, which are
measured and never drawn.

Run it on `book_corpus.baseline_puzzles()` (all 11 page kinds) for two books:
`book_corpus.corpus_book()` (Book 1) and the same book at the 10.0 cm × 10.0 cm
minimum trim (`book_page_spec.MIN_TRIM_CM`, written out in the test as
`test_book_guide_page_type.py:264` does).

## Acceptance criteria

- **AC-1:** Given the baseline book on Book 1 and on the 10×10 cm minimum trim, when its interior is exported and every `draw.text` call is recorded, then every recorded face outside the clue-digit exemption is ≥ 10 pt at `generator.dpi`, and the recorded calls cover the guide page, a divider, a band, an answer heading and an answer caption. On main this fails on the answer heading and captions (41 px = 9.84 pt).
  *test: TestInteriorType_EveryFaceHoldsTheFloor (in tests/test_book_interior_type_floor.py)*
- **AC-2:** Given Arial is unavailable (`ImageFont.truetype` raises `OSError` for the `/System/Library/Fonts/Arial.ttf` path), when the same two books are exported, then no face is unsized and every face outside the exemption is still ≥ 10 pt. On main this fails on the dividers' unsized `load_default()`.
  *test: TestInteriorType_FloorHoldsWithoutArial (in tests/test_book_interior_type_floor.py)*
- **AC-3:** Given the exemption, when the recorded calls are filtered, then only calls from `png._draw_clues` and `book_pdf_generator._write_clues` (puzzle-page clue digits) are exempt. The exempt set is non-empty on both books, so the exemption is exercised. A worked-example clue digit (`draw_example_line`) is never exempt.
  *test: TestInteriorType_OnlyPuzzleClueDigitsAreExempt (in tests/test_book_interior_type_floor.py)*
- **AC-4:** Given generators at 300 and 600 DPI (monkeypatching `book_pdf_generator.DPI`, as `TestGuidePage_PointSizeIsIndependentOfDpi` does), when each draws a divider page, then the divider face's size in points is the same (14.4 pt) on both. On main it is 60 px at both, so 14.4 pt and 7.2 pt.
  *test: TestDividerPage_PointSizeIsIndependentOfDpi (in tests/test_book_interior_type_floor.py)*
- **AC-5:** Given the change, when the baseline book is exported on Book 1, then the only pages whose digests move are the three answer pages (9, 10, 11). The new baseline records `changed_pages: [9, 10, 11]` in its own commit, after the fix, and every predecessor fixture is byte-identical.
  *test: review-lens (fixture diff + `changed_pages`), plus the suite's existing baseline tests reading the new fixture*

## Guardrails

- G-1: Pages 1–8 of the baseline book are byte-identical, including the dividers on a machine with Arial (`type_px(14.4, 300) == 60`). `book_corpus.MACHINE_FACE_SIZES` stays `(92, 46, 60)` and `font_fingerprint` is unchanged.
- G-2: No baseline fixture is regenerated or edited. `book_baseline_card128..167.json` stay byte-identical; `book_baseline_card184.json` is new and names `book_baseline_card167.json` in `supersedes`.
- G-3: CON-019: CLI/web exports stay byte-identical. `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` stays green. The answer page is book-only, but `ANSWER_TEXT_FONT_MM` lives in `export/layout.py`.
- G-4: Answer-key geometry does not move: tile boxes, the 6 mm caption/heading lines, capacities (INV-011), `compute_answer_page_layout`'s output apart from `font_size`/`caption_font_size`. `tests/test_layout_answer_tiles.py` and `tests/test_book_answer_key.py` pass unchanged.
- G-5: Puzzle clue digits are unchanged (`_CLUE_FONT_RATIO`, INV-006 floor). The guide page (CARD-149/167 tests) is unchanged.
- G-6: No lateral import: `layout.py` gets no import from `admin/` (the `tests/test_cli.py` structural guard).
- G-7: No edit under `meta/`. CON-020's status/check stays as it is (the architect's job).

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-184` (55 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scala… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dimens… (check: review-lens)
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
- CON-019 — Adding book-specific page geometry (a trim, margins, a title band, a portrait-only rule, the 7.5 mm standard cell) never changes the CLI's or the web UI's exports: for… (check: test: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution. A type size is a physical measure - points or millimetres converted… (check: review-lens)
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

- **CON-020** (10 pt floor, `check: review-lens`, scope `book_pdf_generator.py`, `export/layout.py`): the rule this card gives a test.
- **FR-041** (guide page, AC-236..239, AC-324..326), **FR-042** (answer key: "small heading", 6 mm caption/heading line), **FR-043** / **INV-013** (interior has no cover; cover out of scope), **AC-254 / AC-292** (dividers, TERM-031), **INV-006** (4.8 mm cell floor, the reason for the clue exemption).
- **CON-019** (CLI exports byte-identical), **ADR-0036** (book geometry via COMP-007), **ADR-0006/R1** (packaged face for band/answer lettering).
- COMP-009 (book assembly, `admin/book_pdf_generator.py`), COMP-007 (`export/layout.py`, `export/png.py`).
- Trace: `trace.yml` `req: CON-020` → CAP-006, COMP-009, COMP-007, ADR-0036; tests today CARD-149's three guide-page tests only.

## Design context

- **Output:** interior PDF. The answer key pages' level heading and puzzle captions grow from 41 px (9.84 pt) to 42 px (10.08 pt). Every other interior page stays pixel-identical on a machine with Arial. On a machine without Arial (the Linux deploy), dividers change from Pillow's unsized ~10 px face to a 60 px face. This is an owner-visible change.
- **Renders:** ~/Documents/nonogram-reviews/CARD-184/ (owner visual check before merge): one answer page before/after at Book 1 trim, and a divider rendered with the Arial path forced to fail, before/after.

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-008 (CON-020 partial, no test walks every interior face). Folds in IDEA-087's divider half, because the floor test fails on it. IDEA-087's cover half is out of scope, since the cover is not interior (INV-013).
- [Measured 2026-10-05, drafting] Spy on `ImageFont.truetype`/`load_default` during `export_interior(baseline_puzzles())`, with the lru caches cold, gave the table in "What to implement". 10×10 cm trim with margins gutter 0.95 / outside 0.64 cm exported without error. Caution: running Book 1 first and the small trim second in one process hid the band and answer sizes on the second run, because of `lru_cache`. That is why the test spies on `ImageDraw.text`.
- [Facts] `ANSWER_TEXT_FONT_MM = 3.5` at `src/nonogram/export/layout.py:2007` (used `:2414`, `:2579`); `_mm_to_px` `:997` rounds to nearest. 10 pt = 41.67 px → 42 px. Divider font `book_pdf_generator.py:1650-1652`; `_guide_face` `:529`; `type_px` `:504`; `self.dpi = DPI` `:1447`. `_CLUE_FONT_RATIO = 0.62` `layout.py:326`.
- [Baselines] Answer pages are interior pages 9–11 of the baseline book. Expect these to go red and need re-pointing to `book_baseline_card184.json`: `tests/helpers/book_corpus.py` `BASELINE_FIXTURE` (`:117`), which feeds `tests/test_book_pdf_memory.py`; `tests/test_book_pdf_ink_mode.py` `TestBookInk_ColourInteriorIsUnchanged`, which compares pages 2–11 to CARD-146's file plus page 1 to CARD-167's, and the colour interior's length. Follow the CARD-167 pattern: overlay the moved pages from the new fixture and record the new `colour_interior_bytes`. `tests/test_book_pdf_memory.py` is in Touches in case its answer-page ink figures (`:225-228`) are bounds the larger type crosses. If they are not, leave it untouched. Record the baseline in its own commit, after the fix commit (CARD-149/167 precedent).
- [Architect] Flipping CON-020 to `check: test` (ref `TestInteriorType_EveryFaceHoldsTheFloor`), updating its trace tests, and deciding whether its statement should carve out cell-bound clue digits (or another rule should govern them) is the architect's job. Never edit `meta/` in this card.
- [AC cross-check] Re-read AC-1..AC-5 against the body. The exemption list (AC-3) matches item 3. The fixes in items 1–2 are what make AC-1/AC-2/AC-4 pass. AC-5's pages 9–11 match item 1. The cover and band shrink stay out of scope in both. No edit was needed.
