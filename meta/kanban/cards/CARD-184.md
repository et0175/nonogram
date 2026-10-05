# CARD-184: One test holds every interior face to CON-020's 10 pt floor, and the two faces below it today are fixed

**Status:** done
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
**Review score:** 9.5 (cycle 1/3)
**Started:** 2026-10-05T07:46:41Z
**Closed:** 2026-10-05T09:42:16Z
**Actual:** 0.2d
**Merge commit:** 9117567
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
- [Env] forge 2026.8.17
- [System contract] fresh assembly (system_rules.py --card CARD-184) = card section, 55 rules — no refresh needed
- [Renders] before: ~/Documents/nonogram-reviews/CARD-184/{answer-page9-book1,divider-with-arial,divider-no-arial}-before.png (main 2e40c96); divider without Arial letters SOLUTIONS at Pillow's unsized ~10 px face
- [Implemented 2026-10-05] Commits on card/184-interior-type-floor: `2b1ef03` fix (code + new test), `52c4da6` baseline (own commit), `0333288` test-only follow-up (removed an untested spy branch; see the T6 note below). Files: `src/nonogram/export/layout.py` (`ANSWER_TEXT_FONT_MM = 10 * 25.4 / 72`, no import), `src/nonogram/admin/book_pdf_generator.py` (`DIVIDER_PT = 14.4`; `create_divider_page` letters through `_guide_face(type_px(DIVIDER_PT, self.dpi))`), `tests/test_book_interior_type_floor.py` (new), `tests/fixtures/book_baseline_card184.json` (new), `tests/helpers/book_corpus.py` (`BASELINE_FIXTURE` now card184), `tests/test_book_pdf_ink_mode.py` (overlays pages 9-11 from card184 and reads `colour_interior_bytes` from it, following the CARD-167 pattern). No SCOPE+.
- [Measured] Answer heading/caption: 41 px = 9.84 pt before, 42 px = 10.08 pt after (300 DPI, both books). Divider with Arial: 60 px = 14.40 pt before and after. Divider without Arial: before, a sizeless `load_default()` (Pillow 12.3 returns a FreeTypeFont at a 10 px em) = 2.40 pt; after, `load_default(60)` = 14.40 pt. Divider at 600 DPI: 60 px = 7.2 pt before, 120 px = 14.4 pt after.
- [Spy shape, real names] The exempt functions exist as named: `nonogram.export.png._draw_clues` and `nonogram.admin.book_pdf_generator._write_clues`. **But `draw_example_line` also calls `_write_clues`**, so a rule based only on the immediate caller would exempt the worked-example digits. The rule is: the immediate caller is one of the two, AND `draw_example_line` is nowhere in the call chain. The chain is the `nonogram.*` frames only. Two more facts: (1) the min-trim book prints its single puzzles through COMP-007's `pdf._draw_header`, not `_set_band`, so both count as "band" for the coverage assertion; (2) the 10x10 cm book exports 12 interior pages, not 11, because its answer key packs onto one more page. The test asserts 11 and 12 per book. "Unsized" means either the face is not a FreeTypeFont, or it is the object a sizeless `ImageFont.load_default()` returned during the walk. On Pillow ≥ 10.1 that object is a FreeTypeFont at 10 px, so `isinstance` alone cannot tell it apart (see T1m).
- [Test on main] With main's src, the new file has 7 failed / 14 passed. AC-1's two floor tests fail on page 9-11 answer heading/captions at 41 px = 9.84 pt. AC-2's `test_no_face_is_unsized` (x2) and its floor tests (x2) fail on the dividers' sizeless `load_default()`. AC-4 fails at [7.2] pt vs 14.4.
- [Mutants] All were run against the new test file. S* mutate src; T* mutate the test. "(main)" means the test mutant was run with main's two defects restored.
  - S1 `ANSWER_TEXT_FONT_MM = 3.5`: killed (AC-1 + AC-2 floor tests, both books).
  - S2 divider back to main: killed (AC-2 unsized + floor, AC-4).
  - S3 divider sized by `type_px` but unsized fallback: killed (AC-2 unsized + floor). AC-4 survives, as expected.
  - S4 sized fallback but bare `60`: killed (AC-4 only).
  - S5 `_write_clues` halves its size: killed (AC-1/AC-2 floor). This proves worked-example digits are held to the floor.
  - S6 `png._clue_font` quarters puzzle-clue size: survives. This is the exemption's edge: puzzle-page digits really are exempt.
  - S7 `_set_band` starts at its 1/3 shrink floor: killed on book1 only (only book1 has a two-up band).
  - S10 `pdf._draw_header` starts at its 1/3 floor: killed on both books.
  - S8 answer face 3.505 mm (41.4 px → 41): killed.
  - S9 answer face 3.5137 mm (41.5 px → 42): survives. The floor boundary is between 41 and 42 px, as claimed.
  - T1 spy drops the sizeless-`load_default` detection: survives on fixed code. T1m (main): `test_no_face_is_unsized` no longer fails, but the floor tests still catch the 10 px divider. So the detection is what makes AC-2's "no face is unsized" able to fail.
  - T2 exemption widened to include `draw_example_line`: killed (`test_worked_example_digits_are_drawn_and_never_exempt` x2, `test_exempt_calls_are_puzzle_page_digits` x2, `test_the_exemption_rule_by_name`).
  - T3 floor comparison flipped: killed.
  - T4 exemption widened to `png.render_answer_page`: killed (`exempt_calls_are_puzzle_page_digits`, `exemption_rule_by_name`). T4m (main): AC-1's floor tests then pass on main's 9.84 pt answers, but `exempt_calls_are_puzzle_page_digits` still fails. So that test is what stops the exemption from hiding a real face.
  - T5 (main) `without_arial` patches nothing: `test_arial_really_is_unavailable` fails. So does the AC-1/AC-2 floor test (answers), and AC-2's unsized tests stop failing. The control works.
  - T6 the spy drops its "skip PIL-internal multiline re-entry" filter: survived (no interior text is multiline). The filter was removed in `0333288` instead of being claimed. `_call_chain` already skips PIL frames.
- [Baseline] Font fingerprint reproduced first (= card167's `cfa57e76…`). Pages 1-8 have the same sha256 as `book_baseline_card167.json`, dividers included. Only pages 9, 10 and 11 moved (`changed_pages: [9, 10, 11]`). Interior bytes went 2,436,675 → 2,437,097, and the colour interior 2,845,318 → 2,845,507. The colour-export page digests equal the black-and-white ones (checked). `git diff 2e40c96 --stat` shows no predecessor fixture touched. `MACHINE_FACE_SIZES` stays `(92, 46, 60)` and `font_fingerprint` is unchanged.
- [book_pdf_memory] `tests/test_book_pdf_memory.py` was not touched. Its answer-page ink checks still pass with the larger type. It reads the new fixture through `book_corpus.BASELINE_FIXTURE`. One existing docstring (`:1163`) still says "currently book_baseline_card147.json"; it was already stale before this card and was left alone.
- [Tests run] On the final tree, the new file passed 21/21. A wider run of `tests/test_book*.py`, `test_answer_page_layout.py`, `test_export*.py`, `test_layout*.py`, `test_pdf_generator.py`, `tests/property/` and `tests/test_cli.py` gave 2450 passed and 1 skipped. That skip is the pre-existing platform skip of `setrlimit(RLIMIT_AS)` on macOS. The full suite was not run here (orchestrator gate).
- [Architect] As drafted: CON-020's check/trace flip, and whether to carve out cell-bound clue digits, are left to the architect. Nothing under meta/ was edited apart from these notes.
- [Scope] src/nonogram/admin/book_pdf_generator.py, src/nonogram/export/layout.py, tests/fixtures/book_baseline_card184.json, tests/helpers/book_corpus.py, tests/test_book_interior_type_floor.py, tests/test_book_pdf_ink_mode.py
- [Build gate] impact underivable (test_scope: full) — full suite
- [Renders] after: ~/Documents/nonogram-reviews/CARD-184/*-after.png + answer-page9-top-before-over-after.png, divider-no-arial-before-over-after.png. Pixel diff: answer page 9 changes only in the heading/caption band (bbox 546,132–2029,257); divider with Arial identical; divider without Arial 10 px → 60 px face. Owner look is a pre-merge check.
- [Build gate] PASSED (full, 711s; 6291 passed, 9 skipped — baseline 6270 + 21 new)
- [Scope gate 1] IN_SCOPE — 6 files, all within Touches; no guardrail hits (no meta/, no predecessor fixture, no new import in layout.py)
- [Review 1/3] Score: 9.5 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/ (20261005T084958Z-CARD-184-cycle1.yml)
- [Adversarial] no Critical/Important findings in cycle 1 — nothing to verify
- [Review 1/3] Step 8h coverage: 55/55 card rules have a verdict line (10 ✓, 45 ⚠ no_eligible_fact, 0 ✗)
- [Review 1/3] Score: 9.5 ✓ threshold reached + no critical/important
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0036/R1)
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-1 ✓ demonstrated — TestInteriorType_EveryFaceHoldsTheFloor 4/4 PASSED (book1 + min-trim, coverage of guide/divider/band/answer heading/caption); fails on main src · AC-2 ✓ demonstrated — TestInteriorType_FloorHoldsWithoutArial 7/7 PASSED; test_no_face_is_unsized fails on main · AC-3 ✓ demonstrated — TestInteriorType_OnlyPuzzleClueDigitsAreExempt 9/9 PASSED (exempt set non-empty on both books, worked-example digits never exempt) · AC-4 ✓ demonstrated — TestDividerPage_PointSizeIsIndependentOfDpi PASSED (14.4 pt at 300 and 600 DPI); fails on main · AC-5 ✓ demonstrated — card184 fixture changed_pages [9,10,11], supersedes card167, pages 1-8 sha256 = card167, no predecessor fixture in diff, baseline commit 52c4da6 after fix 2b1ef03, test_book_pdf_memory + test_book_pdf_ink_mode green · G-1 ✓ (digests 1-8 = card167; MACHINE_FACE_SIZES (92,46,60), font_fingerprint unchanged) · G-2 ✓ (no card128..167 fixture in diff) · G-3 ✓ (tests/property/test_cli_exports_byte_identity.py 3 passed; a4 golden + page spec 171 green) · G-4 ✓ (test_layout_answer_tiles 48, test_book_answer_key 56 PASSED, files untouched) · G-5 ✓ (_CLUE_FONT_RATIO untouched; guide page tests 17+11 PASSED) · G-6 ✓ (test_every_import_in_the_package_points_inward PASSED; no import line in src diff) · G-7 ✓ (git diff main...HEAD -- meta empty)
- [Docs] forge:readme: no README in src/nonogram/admin, src/nonogram/export, tests/fixtures, tests/helpers; tests/README.md is the Wave-1 admin-suite README and lists no book tests — no structure/purpose change, nothing to update
- [Commit] success commit d69d6e2 (empty marker; change in 2b1ef03 fix + 52c4da6 baseline + 0333288 test-only follow-up, which changes no pixels) — diff vs main: 6 files, +570/−18; nothing under meta/ committed. Open: Minor F-001 (test_only_the_two_clue_writers_are_exempt passes by construction — redundant with test_the_exemption_rule_by_name); out-of-scope: clue digits 3.6–9.4 pt (architect: CON-020 carve-out + flip check to TestInteriorType_EveryFaceHoldsTheFloor), stale docstring test_book_pdf_memory.py:1163. Owner look at ~/Documents/nonogram-reviews/CARD-184/ is a pre-merge check.
- [Merge gate] rebased onto cb53412; full suite 6323 passed, 9 skipped, exit 0 (590s, under the lock). Owner: "merge now, check later" (renders in ~/Documents/nonogram-reviews/CARD-184/). Merged 9117567.
