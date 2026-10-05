# CARD-170: Prove from the PDF's pixels that a puzzle's band prints once ("Puzzle 5 · Hard" drawn twice?)

**Status:** done
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/170-band-prints-once
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (wave-32 goal-check observation; IDEA-090, WSJF 16)
**Idea:** IDEA-090
**Wave:** 33
**Depends on:** —
**Touches:** tests/test_book_pdf_band.py, src/nonogram/admin/book_pdf_generator.py, tests/helpers/book_corpus.py, tests/fixtures/book_baseline_card170.json (new)
**Review score:** 9.5 (3 cycles)
**Started:** 2026-10-04T16:19:19Z
**Closed:** 2026-10-05T03:33:47Z
**Actual:** 1.4d
**Merge commit:** a5a2b99
**Blocked by:** —

## What to implement

The wave-32 goal-check hooked text drawing during a book export. It saw the
band "Puzzle 5 · Hard" drawn twice. Nobody checked whether the printed PDF
shows it twice. This card settles that with evidence first. It fixes only if
the duplicate is real.

**What the code does today (read, not yet proven by a test).**

- "Puzzle 5 · Hard" is a **puzzle-page band**, not an answer-key band. Answer
  tiles are captioned "Puzzle N — Title" with an em dash
  (`book_pdf_generator.py:BookPDFGenerator._answer_page`, lines 1936-1968, via
  `book_answer_key.answer_caption`). Answer pages carry no band. The idea's
  wording ("answer-key band", "fitting loop") does not match the code.
- A puzzle that prints **alone** goes through `BookPDFGenerator._blank_page`
  (lines 1827-1842). It calls COMP-007's `export/pdf.py:render_pages`, which
  draws **two** pages from one payload, the blank page and the solved page.
  It sets the header on both (`export/pdf.py` lines 465-467:
  `for page in (blank, answer): _draw_header(...)`). `_blank_page` keeps the
  blank page and drops the solved one (`blank, _ = render_pages(...)`).
- So the second draw most likely lands on the **dropped solved page**, a
  scratch bitmap that never reaches `_write_page`. That explains "twice"
  without any printed duplicate. It also explains "highest tier": in a
  5-puzzle book with Easy and Medium pairs, the single Hard puzzle is the only
  one printed alone. Paired puzzles go through `_two_up_page`
  (lines 1970-2011), which calls `_set_band` once per slot. `_set_band`
  (lines 773-820) only measures with `font.getlength`; it calls `draw.text`
  once. `_draw_header` in `export/pdf.py` also measures with `getlength` and
  calls `draw.text` once per part. So "measuring before drawing" is not the
  cause: measuring draws nothing.
- The module docstring already records the dropped solved page as a known,
  constant memory cost (`book_pdf_generator.py` lines 213-224).

**Steps.**

1. **Establish the fact from the exported PDF.** Build a small book whose
   last puzzle is the only Hard one and prints alone (for example 2 Easy,
   2 Medium, 1 Hard, sized so the Easy and Medium pairs pair). Export the
   interior through the generator's normal path. Read the bytes back with
   `tests/helpers/pdf_pages.py:pdf_pages`. Assert from pixels:
   - exactly one page of the whole PDF carries the "Puzzle 5 · Hard" band;
   - on that page the band strip holds one copy of the line: its ink extent
     matches the width of one line set at the band's size (with a JPEG
     tolerance), so a second, offset copy fails;
   - no divider or answer page carries that band's ink.
   Also cover a two-up page: each slot's band appears once.
2. **Name where the second draw lands.** Record `ImageDraw.text` calls during
   the export (monkeypatch). Assert that every draw of the band text that
   lands on a page reaching `_write_page` happens once per written page. Do
   not assert "exactly two draws": that would pin the wasted solved-page
   render.
3. **Render for the owner.** Write the Hard puzzle's page, a two-up page and
   one answer page as PNGs (decoded from the exported PDF, not re-rendered)
   to `~/Documents/nonogram-reviews/CARD-170/`. Never write them beside the
   repo.
4. **Decide.** If steps 1-2 pass, record "not a defect" in Worktree notes with
   the evidence: the test names and the recorder's result. Change no
   production code. If they fail, fix the generator so the band prints once,
   and rebaseline under the book pixel-baseline rule (see Touches).

## Acceptance criteria

- **AC-1:** Given a book whose only Hard puzzle prints alone as Puzzle 5, when its interior PDF is exported and its pages are decoded, then exactly one page carries the "Puzzle 5 · Hard" band, and its band strip holds one copy of the line, not two.
  *test: TestBookPdf_BandPrintsOnceInTheExportedPdf (in tests/test_book_pdf_band.py) — fails if `_set_band` or `_draw_header` draws a second offset copy, or if any other page gets the band*
- **AC-2:** Given a two-up page in the same export, when its pages are decoded, then each slot's band ("Puzzle 1 · Easy", "Puzzle 2 · Easy") appears exactly once on that page and on no other page.
  *test: TestBookPdf_BandPrintsOnceInTheExportedPdf (in tests/test_book_pdf_band.py)*
- **AC-3:** Given the same export with `ImageDraw.text` recorded, when the band text's draws are matched to the images written to the PDF, then each written page received the band exactly once, and any other draw landed on an image that was never written.
  *test: TestBookPdf_ExtraBandDrawNeverReachesAWrittenPage (in tests/test_book_pdf_band.py)*
- **AC-4:** Given the export above, when the owner opens `~/Documents/nonogram-reviews/CARD-170/`, then it holds the Hard puzzle's page, a two-up page and an answer page decoded from the exported PDF, and the Worktree notes record the verdict (defect or not) with its evidence.
  *test: review-lens (renders exist; verdict recorded)*
- **AC-5:** Mutation check: a second offset `draw.text` added in `_set_band`, and an answer caption that reuses `band_identity`, each make AC-1/AC-2 fail.
  *test: review-lens (mutants run and reverted, recorded in Worktree notes)*

## Guardrails

- G-1: If no duplicate prints, no production file changes. `git diff main -- src/` is empty.
- G-2: Book PDF pixels do not change unless a printed duplicate is found. The existing baselines (`tests/fixtures/book_baseline_card167.json` and earlier) still pass unchanged.
- G-3: Do not change `export/pdf.py:render_pages`. Its two-page contract and CON-019's A4/CLI golden are COMP-007's. Removing the dropped solved page is a separate decision (see Worktree notes).
- G-4: The band's wording stays ADR-0037/R1's "Puzzle N · Tier"; `test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle`, `TestBookPdf_PuzzlePageCarriesNoPictureTitle` and `TestBookPdf_AnswerKeyCarriesPictureTitle` stay green unedited.
- G-5: The one-page-retained memory equality in `tests/test_book_pdf_memory.py` stays green.
- G-6: The new tests read the PDF bytes, not the generator's in-memory pages. The pixel test must not call `_blank_page` or `render_pages` to get the page it checks.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-170` (53 rules; refreshed at start from the 7-rule decompose projection). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static as… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no do… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the ot… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniquen… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit on … (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that … (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws noth… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DE… (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density… (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) a… (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle'… (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure f… (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them,… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution … (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid … (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never s… (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership … (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percentage… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel do… (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm toolchain … (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the sol… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium (pl… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctne… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a ga… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to bot… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded f… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a parameter:… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution. A type size is a physical measure - points or millimetres converted aga… (check: review-lens)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No other… (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never … (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-00… (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, ch… (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), … (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at m… (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it t… (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book'… (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **Requirements:** FR-033 (AC-193 / AC-194: the title only on the answer key; the puzzle page band is "Puzzle N · Tier"), FR-040 (two-up pages, one band per slot), FR-042 (packed answer key: captions, no band).
- **ADRs:** ADR-0037/R1 (band wording), ADR-0036/R2 (COMP-007 lays out; the panel strokes).
- **Constraints:** CON-019 (CLI/A4 PDF golden; untouched).
- **Components:** COMP-009 (`src/nonogram/admin/book_pdf_generator.py`) is the subject. COMP-007 (`src/nonogram/export/pdf.py:render_pages`) is the likely site of the second draw, read-only here.
- **Trace:** FR-033 → COMP-009 `_blank_page` / `_two_up_page` → COMP-007 `render_pages` / `_draw_header` → tests/test_book_pdf_band.py.
- **See also:** meta/releases/wave-32.md, "Known gaps": "To check: the goal-check's PDF recorder saw the highest-tier answer-key band drawn twice …". Nothing in meta/kanban/retro.md.

## Design context

- **Output:** interior PDF: the Hard puzzle's page (printed alone), one two-up page, one answer page.
- **Renders:** ~/Documents/nonogram-reviews/CARD-170/ (owner visual check: one band per puzzle, nothing doubled or shadowed).

## Worktree notes

- [Touches] The last three Touches apply only if the duplicate proves real; otherwise the card commits tests/test_book_pdf_band.py alone (tests/helpers/pdf_pages.py is read, not changed). Listed in full so the dispatcher serializes this card with CARD-169 (shared book_pdf_generator.py).

- [Origin] Roadmap wave 1: IDEA-090 (tech-debt, P1, WSJF 16), "answer-key band drawn twice in an export (printed duplicate?)", from the wave-32 goal-check.
- [Verified 2026-10-04, read only] Likely cause: `render_pages` (`src/nonogram/export/pdf.py:423-468`) sets the header on the blank page **and** the solved page (lines 465-467). `BookPDFGenerator._blank_page` (`book_pdf_generator.py:1827-1842`) drops the solved page. So every puzzle printed alone has its band drawn twice, once on a bitmap that is never written. Paired puzzles (`_two_up_page`, 1970-2011) draw each band once. Callers: lines 2559 (`_blank_page`), 2563 (`_two_up_page`), 2584 (`_answer_page`).
- [Verified] "Measure then draw" is not the mechanism. `_set_band` (773-820) and `export/pdf.py:_draw_header` (322-405) measure with `font.getlength` and call `draw.text` once per piece.
- [Verified] The PDF has no text objects. Each page is one DCT image (`_write_page`, 2707-2776). So "printed twice" can only mean ink in the image. Two draws at the same spot would give the same pixels. The pixel test therefore looks for a second **copy** (another page, or an offset in the strip), and the recorder test (AC-3) separates written from unwritten images.
- [Reuse] `tests/test_book_pdf_band.py` already has `_book`, `_puzzle`, `print_plan`, `puzzle_page_number`, `answer_page_number` and `_band_strip`. `tests/helpers/pdf_pages.py:pdf_pages` decodes the exported bytes.
- [Owner decision, out of scope] Stop rendering `render_pages`' unused solved page for book puzzle pages? It costs one full-size bitmap and a full render per puzzle printed alone (docstring lines 213-224 already record this). It would mean a COMP-007 API change (a blank-only render), so it needs its own card. Suggest a backlog line rather than doing it here.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +ADR-0006/R1, ADR-0019/R1, ADR-0022/R1, ADR-0022/R3, ADR-0022/R4, ADR-0024/R1, ADR-0024/R2, ADR-0024/R3, ADR-0024/R4, ADR-0024/R5, ADR-0027/R1, ADR-0027/R2, ADR-0029/R1, ADR-0029/R2, ADR-0029/R3, ADR-0029/R4, ADR-0029/R5, ADR-0032/R1, ADR-0032/R2, ADR-0033/R1, ADR-0035/R1, ADR-0036/R1, ADR-0036/R2, ADR-0037/R1, ADR-0037/R2, ADR-0038/R1, ADR-0038/R2, ADR-0038/R3, ADR-0038/R4, ADR-0038/R6, CON-015, CON-016, CON-020, CON-021, INV-001, INV-002, INV-003, INV-005, INV-006, INV-007, INV-008, INV-009, INV-010, INV-011, INV-012, INV-013 / −none (fresh assembly 53 rules, card_scope touches — the card's Touches name src/nonogram/admin/book_pdf_generator.py, which pulls in every admin/** rule)
- [Verdict 2026-10-04] NOT A DEFECT. Production code unchanged: `git diff main -- src/` is empty (G-1). The card commits only tests/test_book_pdf_band.py, so no rebaseline (G-2). book_corpus.py and the card170 baseline are not touched.
- [Evidence, pixels] TestBookPdf_BandPrintsOnceInTheExportedPdf (9 tests, tests/test_book_pdf_band.py). The book is 2 Easy, 2 Medium and 1 Hard, all 10x10. It is exported through `export_book`, and its 11 pages are decoded from the interior PDF's bytes with `pdf_pages`. No `_blank_page`, `render_pages` or `interior_pages` call is used to obtain a checked page (G-6). Results: every band line ("Puzzle 1 · Easy" … "Puzzle 5 · Hard") is found exactly once in the whole PDF, on its own page (3, 3, 5, 5, 7), at the 5 mm band size. The search tries every type size from 10 to 120 px. On page 7 (Hard, alone) and on the upper slots of pages 3 and 5, the top band strip, rules aside, holds one run of rows. That run's ink box and ink match the line set once. On page 3 the bands read "Puzzle 1 · Easy" above "Puzzle 2 · Easy". Control: the same search finds the answer caption "Puzzle 5 — Snowflake" once, on page 11, at a smaller size than the band.
- [Evidence, recorder] TestBookPdf_ExtraBandDrawNeverReachesAWrittenPage (2 tests). It records `ImageDraw.text` and `_write_page` during `export_book`. Recorded result: written pages {3: P1 ×1, P2 ×1; 5: P3 ×1, P4 ×1; 7: P5 ×1}. Exactly one further band draw was recorded, 'Puzzle 5 · Hard', on an image never passed to `_write_page`. No band draw happened on a page after it was written. That the unwritten image is `render_pages`' solved page is from reading the code (`_blank_page` drops it). The recorder only shows that the image was never written.
- [Tolerance] Measured on this export: each of the five decoded bands' ink box equals the box of the text set once at 59 px, to 0 px in both axes. Their ink mismatch is 0.4-0.7 %. Compared against the line for a different puzzle number (same box), the mismatch is 8.8-10.6 %. Limits set: BOX_TOLERANCE_PX = 2 and INK_MISMATCH_LIMIT = 3 %. A row counts as a rule when its run is longer than 118 px (2 × the type size): the frame rule's rows measured 1153 px, and the longest run in any band line measured 30-33 px.
- [Mutants] All were reverted, and `git diff main -- src/` is empty afterwards. Results are against the CARD-170 tests (-k "PrintsOnce or ExtraBandDraw"):
- (AC-5a) `_set_band` second `draw.text` at x+40: FAILED found-once, strip[two-up-easy-upper], strip[two-up-medium-upper], two-up-upper-first and recorder per-page. Also run at x+3, at y+3 (same 5 failures) and at y+80 (copy runs into the frame's rows: the strip[two-up-*] tests and the recorder failed).
- (AC-5b) answer caption = `band_identity(answer.number, payload.difficulty)`: FAILED found-once (bands found on the answer pages at caption size), the caption control, and recorder per-page.
- `export/pdf.py:_draw_header` drawn a second time, offset, as a runtime monkeypatch plugin in the scratchpad (the file itself was never edited, G-3): at x+40, x+3 and y+3, FAILED found-once, strip[hard-alone] and recorder per-page. At y+80, FAILED strip[hard-alone] and recorder per-page.
- (AC-3) an invisible extra band draw (white, at the corner) on the written blank page in `_blank_page`: only the recorder per-page test FAILED. The pixels cannot see it, as expected.
- (AC-3) `_set_band` called twice per slot at the same spot: FAILED the recorder per-page test, plus found-once, both two-up strips and upper-first (the anti-aliasing darkens).
- (AC-3) band drawn on page 7 after `_write_page` (in `_write_pdf`): FAILED recorder per-page and recorder late-draw.
- `_blank_page` returns the solved page instead of the blank: the CARD-170 tests stay green, because which of the two pages is written is not their claim. The existing band tests catch it: 6 failures, including TestBookPdf_PuzzlePageCarriesNoPictureTitle and the PropertyTest.
- [Tests] tests/test_book_pdf_band.py, tests/test_book_pdf_memory.py, tests/test_book_pdf_ink_mode.py: 102 passed, 1 skipped. The skip is pre-existing (setrlimit RLIMIT_AS is refused on macOS). tests/test_book_guide_page.py also passes. The G-4 named tests are green and unedited. The G-5 memory test is green.
- [Renders] Decoded from the exported interior PDF bytes by the scratchpad script card170_render.py: ~/Documents/nonogram-reviews/CARD-170/page07-hard-puzzle-5-alone.png, page03-two-up-puzzles-1-2.png and page11-answer-page-hard.png. Eyeballed: one band per puzzle, with nothing doubled or shadowed.
- [Suggested backlog] "Stop rendering `render_pages`' unused solved page for book puzzles printed alone. Needs a COMP-007 blank-only render API, so it is its own card. Saves one full-size bitmap and render per puzzle printed alone. The extra 'Puzzle N · Tier' draw the CARD-170 recorder records lands on that unwritten page." Not implemented here (owner decision, out of scope).
- [Scope] No SCOPE+. The only changed file is tests/test_book_pdf_band.py: new imports, two docstring lines and an appended CARD-170 section.
- [Scope] tests/test_book_pdf_band.py
- [Build gate] impact underivable (python-pro, no pytest-testmon; test_scope full) — full suite
- [Build gate] PASSED (full, 571s; 6127 passed, 9 skipped; waited 754s for the full-suite lock)
- [Scope gate] cycle 1: IN_SCOPE — 1 file (tests/test_book_pdf_band.py), inside Touches; no guarded path (G-3 src/nonogram/export/pdf.py) touched
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1 (F-001, pending adversarial verification)
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: 53/53 card rules carry a verdict (7 ✓, 46 ⚠ no_eligible_fact, 0 ✗)
- [Adversarial] F-001 CONFIRMED — skeptic reproduced: _set_band second copy at y+300 (over column clues) leaves all 7 collected pixel tests green; only the recorder per-page test fails; src reverted
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Fix cycle 1, F-001 correction] The [Evidence, pixels] line and the [Verified] line ("looks for a second copy (another page, or an offset in the strip)") are narrower than the test comments first stated. The pixel class catches a second copy only in clear space (the band strip, the margins, the gap between slots) or touching the band line. A copy that lands on other ink (clues, grid, captions) merges with that ink into a line that matches no reference, and the pixel tests miss it, just as they miss a copy at the same spot. Only the recorder (AC-3) catches those. Mutants, rerun in this fix and reverted: a second `_set_band` copy at y+300 (over the column clues) and at y+700 (inside the grid) left every pixel test green, and only `test_each_written_page_received_each_of_its_bands_exactly_once` failed. "Found nowhere else" in [Evidence, pixels] means as a line of its own, in clear space. The section comment, the TestBookPdf_BandPrintsOnceInTheExportedPdf docstring and two test docstrings are narrowed to match.
- [Fix cycle 1, F-002] `_BandDraws.late` (the late-draw test) watches only pages that had received a band before `_write_page`. A late band draw on any other written page (a divider) lands in `unwritten`, which no test asserts. The comment and the test docstring are narrowed. The check itself is not broadened: holding every written image would keep the whole book's bitmaps alive.
- [Fix cycle 1, F-003] `test_the_interior_is_the_page_sequence_this_module_reads` is renamed `test_the_interior_has_the_page_count_this_module_reads`, because it asserts only the count. Mutant (`_pairable_tier` returns None, so there is no pairing and no dividers): it FAILED, 8 == 11. Reverted.
- [Fix cycle 1, AC-5 rerun] After the edits, (AC-5a) the second `_set_band` draw.text at x+40 FAILED found-once, both two-up strips, upper-first and recorder per-page. (AC-5b) the answer caption = band_identity FAILED found-once, the caption control and recorder per-page. Both were reverted. `git diff HEAD -- src/` is empty.
- [Fix 1] declarations: 0 updated, 0 confirmed, 0 none — 3 doc/notes declaration sets narrowed (F-001 section comment + 3 docstrings + card notes; F-002 _BandDraws.late + test docstring; F-003 rename); pre-gate: named tests green
- [Build gate] PASSED (full, 572s; 6127 passed, 9 skipped)
- [Scope gate] cycle 2: IN_SCOPE — tests/test_book_pdf_band.py only; G-3 path untouched; src/ clean
- [Review 2/3] Score: 8.5 — crit: 0, imp: 1 (F-005, introduced by the F-001 fix's wording; pending adversarial verification). F-001 ✗ in new form, F-002 ✓, F-003 ✓
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h coverage: 53/53 card rules carry a verdict (7 ✓, 46 ⚠ no_eligible_fact carried(cycle 1, delta-clean), 0 ✗)
- [Adversarial] F-005 CONFIRMED — skeptic reproduced: _set_band copy at (x−900, y+600) lands in page 3's left margin (cols 180-611, 105 px from nearest ink); _lines merges it into the 1158 px-tall drawing line; all 7 pixel tests green, only recorder per-page fails; src restored
- [Review 2/3] family attribution: F-005 attributed to the F-001 fix (reviewer: 'the fix fixed one over-claim and introduced another') — family streak 1 (<2, no family escalation). Family sentence: which band copies the pixel search can see (only rows with no other ink within a line's height sideways)
- [Review 2/3] ⚠ improvement stalled — Δscore: 0.0, Δcrit+imp: 0
- [Escalated] 2026-10-04T17:22:47Z — review stalled at 8.5 (cycle 2/3; Δscore 0, Δcrit+imp 0): F-005 (Important, skeptic-CONFIRMED): the cycle-1 fix's narrowed wording over-claims again — tests/test_book_pdf_band.py:920-924, 1131-1136, 1147-1148 and the card's [Fix cycle 1, F-001 correction] note say a second band copy 'in the margins' fails the pixel tests; a copy in the side margin beside the drawing (x−900, y+600, clear of ink) passes all 7 pixel tests, only the recorder catches it. Verdict 'not a defect' stands (recorder catches every case); src/ unchanged; implementation commit 5a31d3f; cycle-1 fix edits to tests/test_book_pdf_band.py left UNCOMMITTED in the worktree · station: implementation (code defect — test-comment wording; card and requirement sound) · route: manual fix — state the real rule (a copy is found only on rows with no other ink within about a line's height sideways: band strip, gap between slots, top/bottom margins; a copy beside the drawing or over ink is caught only by the recorder, AC-3) at lines 920-924, 1131-1136, 1147-1148 + correcting card note, optionally F-006 (same-spot double draw is caught by pixels today, by accident) — then /kanban review CARD-170
- [Owner decision] 2026-10-05 — "Targeted fix + 1 review": narrow the test comments/notes to the real detection rule (F-005; F-006 optional), then one confirmation review. Unblocked → review.
- [Rebase] 2026-10-05 owner decision 'Targeted fix + 1 review': branch rebased onto main cf119ca (implementation commit now 854de35); uncommitted cycle-1 fix edits carried over; tests/test_book_pdf_band.py green after rebase
- [Fix cycle 2, F-005 correction] The "[Fix cycle 1, F-001 correction]" note above over-claims: "the margins" is wrong for the side margins. `_lines` groups every run of page rows that holds any ink, then splits a group sideways only at gaps at least as wide as the group is tall. Beside the drawing that group is the whole ~1158 px grid. The real rule: the pixel class finds a second band only on rows with no other ink within about a line's height sideways of it (the band strip, the gap between the two slots, the top and bottom margins). A copy beside the drawing (a side margin) or over other ink is caught only by the recorder (AC-3). The section comment, the TestBookPdf_BandPrintsOnceInTheExportedPdf docstring and the found-once docstring now state this rule.
- [Fix cycle 2, F-006] A second draw at exactly the same spot IS caught by the pixel tests today, but only incidentally: the second antialiased pass darkens the edge pixels past the 3 % ink-mismatch limit. The pixel tests do not guarantee it. The recorder does. The section comment and the class docstring say so.
- [Fix cycle 2, other narrowing] `_lines` docstring: the "clue numbers a cell apart do not [stay one line]" claim is dropped. On pages 3 and 7, each drawing with its clues decodes as one 1158x1158 line. The side-by-side caption claim is kept, because pages 9 and 10 each decode two caption lines at row 226. The band-strip test docstring: "as a second run of rows" is widened to "or a taller first one", backed by M11/M12 below. The caption control docstring: "clear of other ink" is narrowed to "on rows clear of other ink sideways". The Hard-alone page (COMP-007 header) was not mutated, because pdf.py is off-limits. Its claims rest on the same `_lines`/strip reading that the two-up mutants exercise.
- [Fix cycle 2, mutants] Each mutant adds a second `draw.text` in `_set_band` at (x+dx, y+dy), on the upper slot only unless noted, and runs `-k "PrintsOnce or ExtraBandDraw"`. The generator was restored from a saved copy after each run, `cmp` matched, and `git diff HEAD -- src/` is empty. Key: F1 = found-once, S = both two-up band-strip params, U = upper-first, R = recorder per-page test. M1 side margin (-900,+600): R only. M10 side margin (+900,+600): R only. M2 top margin (0,-110): F1, U, R. M3 slot gap (0,+1450): F1, U, R. M4 bottom margin (lower slot, 0,+1280): F1, U, R. M5 band strip beside the band (-900,0): F1, S, U, R. M6 touching the band (+40,0): F1, S, U, R. M7 over the column clues (both slots, 0,+300): R only. M8 inside the grid (both slots, 0,+700): R only. M9 same spot (both slots, 0,0): F1, S, U, R. M11 (0,+60): S, R. M12 (0,+80): S, R. Tests after the edits: tests/test_book_pdf_band.py 34 passed.
- [Fix 2] declarations: wording-only (F-005: section comment + 5 docstrings + 3 card notes; F-006: section comment + class doc + card note); pre-gate n/a lines (doc-only, backed by mutants M1-M12); src/ clean
- [Build gate] PASSED (full, 622s; 6186 passed, 9 skipped; post-rebase)
- [Scope gate] cycle 3: IN_SCOPE — tests/test_book_pdf_band.py only; G-3 path untouched; src/ clean
- [Review 3/3] Score: 9.5 — crit: 0, imp: 0 (F-005 ✓, F-006 ✓, F-004 ✓ rebased; F-007 Minor open)
- [Review sync] 3 report(s) → meta/review/
- [Review 3/3] Step 8h coverage: 53/53 card rules carry a verdict (7 ✓, 46 ⚠ no_eligible_fact, 0 ✗)
- [Review 3/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Mutation check] cycle 3 (passing cycle): AC-5a x+40 killed; AC-5b caption=band_identity killed; same-spot double draw killed; side-margin M1/M10 recorder-only (as documented); top-margin/slot-gap killed; y+60 strip+recorder; _draw_header H1-H4 (runtime patch) killed; src restored (filecmp)
- [8h spot-check] 3/3 sampled holds reproduced (INV-009, INV-010, INV-011) — rule checks test_book_order/pairing/answer_key + pdf_levels/two_up: 144 passed; independent decode: bands p3,3,5,5,7 at 59 px, captions 1-5 once each in order p9-11
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — test_every_band_is_found_once_on_its_own_page_and_nowhere_else, test_the_band_strip_holds_one_line_at_the_band_size[hard-alone] PASSED (class 7/7)
  AC-2 ✓ demonstrated — test_the_two_up_page_carries_each_slots_band_once_upper_first, strip[two-up-easy-upper], strip[two-up-medium-upper] PASSED
  AC-3 ✓ demonstrated — TestBookPdf_ExtraBandDrawNeverReachesAWrittenPage 2/2 PASSED
  AC-4 ✓ demonstrated — 3 PNGs in ~/Documents/nonogram-reviews/CARD-170/ opened (one band per puzzle, nothing doubled); verdict NOT A DEFECT with evidence in notes
  AC-5 ✓ demonstrated — mutants re-run by the gate: (a) x+40 second draw → 4 fail; (b) caption=band_identity → 2 fail; restored (cmp), src diff 0 lines
  G-1 ✓ demonstrated — git diff main -- src/ 0 lines; only tests/test_book_pdf_band.py changed
  G-2 ✓ demonstrated — test_book_pdf_memory.py (card167 baseline, pages pixel-identical) + ink-mode baseline classes green
  G-3 ✓ demonstrated — export/pdf.py diff 0 lines
  G-4 ✓ demonstrated — the 3 named tests PASSED; diff hunks do not touch them
  G-5 ✓ demonstrated — memory peak tests PASSED
  G-6 ✓ demonstrated — once_pages = pdf_pages(export.interior.getvalue()); no _blank_page/render_pages calls in new code
- [Docs] tests/README.md unchanged — no file added/renamed; structure and purpose of tests/ unchanged
- [Commit] success commit e344f3f (on 854de35); diff vs main: tests/test_book_pdf_band.py +431/−2; src/ empty
- [Merge gate] branch rebased onto cf119ca (= main at merge); post-rebase full suite 6186 passed, 9 skipped (pipeline gate, same tree — main had not moved; not re-run). Merged a5a2b99.
