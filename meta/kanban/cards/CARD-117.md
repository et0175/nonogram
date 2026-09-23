# CARD-117: "Puzzle N · Tier" in the band, picture title only in the answer key, print-weight rules on the page

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/117-book-band-and-strokes
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-13
**Idea:** —
**Wave:** 24
**Depends on:** CARD-116
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf_band.py
**Review score:** 9.0 (cycle 1/3)
**Started:** 2026-09-23T03:55:53Z
**Closed:** 2026-09-23T05:23:21Z
**Actual:** 0.2d
**Merge commit:** 837a6f3
**Blocked by:** —

## What to implement

This card implements ADR-0037 on the book pages CARD-116 produces.

1. **The band.** Each puzzle page's 12 mm band (TERM-028) reads **"Puzzle N · Tier"**,
   for example "Puzzle 12 · Easy". N is the puzzle's 1-based position in the printed
   order, and the answer-key entry uses the same number. Tier is the solver's tier
   display name (Easy / Medium / Hard; ADR-0031), never derived from grid size (FR-009).
   Nothing else goes in the band: no picture title, size or quality. The band text is
   drawn inside the band rectangle the `PageSpec` reserves. Drawing text is allowed in
   the admin (ADR-0036/R2 forbids fitting cells and placing grid lines, not lettering).
   Use the packaged font the export uses (ADR-0006/DEC-027), not `/System/Library/...`.
2. **The picture title** appears on the puzzle's **answer-key page only** (FR-033).
   Build the puzzle-page payload so `render_pages` draws no title on it. The answer page
   carries the title together with the same "Puzzle N · Tier" identity.
3. **Line weights.** Under the book `PageSpec`, CARD-114 already applies thin ≥ 0.25 mm,
   heavy = 2 × thin, pure black. This card proves it on the rendered page: every 5th
   rule and both borders are wider than every rule between them (AC-195). Also check
   that the pixels are `#000`, not anti-aliased grey.
4. Numbering stays in the current stored order in this increment. CARD-128 later
   reorders by level, and the numbering follows print order then.

Out of scope: solution hints ("Hint for 12: row 7 has cells 4–11 filled") are deferred
(handoff "Not in scope").

## Acceptance criteria

- **AC-193** — given a book holding a puzzle named "Snowflake", when the book PDF is generated, then the puzzle's puzzle page carries no "Snowflake" text.
  *test:* `TestBookPdf_PuzzlePageCarriesNoPictureTitle`
- **AC-194** — given the same book holding the puzzle named "Snowflake", when the book PDF is generated, then the puzzle's answer-key page shows "Snowflake".
  *test:* `TestBookPdf_AnswerKeyCarriesPictureTitle`
- **AC-195** — given a Book 1 profile book holding a 30x30 puzzle printed at 4.97 mm, when its puzzle page's grid rules are measured, then the rules at line indices 0, 5, 10, 15, 20, 25 and 30 are each wider in pixels than every rule between them.
  *test:* `TestBookPdf_EveryFifthGridLineWider`

## Engineering constraints

- EC(ADR-0037/R1): for every puzzle in a book, whatever its name and tier, the puzzle page's band text is exactly "Puzzle N · Tier" with N its 1-based print position and Tier its solver tier display name, and the page carries no picture title.
  *test:* `PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle`

## Guardrails

- G-1: The admin panel fits no cells and places no grid lines itself (ADR-0036/R2). Strokes come from the book `PageSpec`, not from redrawing rules in the admin.
- G-2: CLI and web A4 output stay byte-identical (CON-019). Do not edit `src/nonogram/export/**`. If `render_pages` cannot suppress the title without an export change, escalate.
- G-3: Out of scope: solution hints (deferred, handoff "Not in scope").
- G-4: Do not edit `src/nonogram/admin/app.py`, `src/nonogram/admin/book_manager.py` or `src/nonogram/admin/templates/**`. They are owned by CARD-123 / CARD-126 this wave.

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

- **FR:** FR-033
- **NFR:** NFR-008
- **ADR:** ADR-0037, ADR-0036, ADR-0031
- **Components:** COMP-009, COMP-007 (consumed)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

- [Handover from CARD-114, 2026-09-22] F-004: the book-path `render_pages` currently prints "<name> — <tier>" in the band. ADR-0037/R1 forbids the picture name on a book puzzle page — replace it with "Puzzle N · Tier"; do not rely on the current band text.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

- [Implemented, 2026-09-23] Done inside the card's Touches only —
  `src/nonogram/admin/book_pdf_generator.py` and the new
  `tests/test_book_pdf_band.py`. Nothing under `src/nonogram/export/**` was
  touched (G-2): the band's content is decided entirely by what the admin puts
  in each page's `ExportPayload`, since `pdf.header_parts` is just the
  non-empty members of `(name, difficulty)`.

  **What changed.** New module-level `band_identity(puzzle_number, stored_tier)`
  composes `"Puzzle 12 · Easy"` (`BAND_SEPARATOR` is `" · "`, U+00B7, set as a
  glyph in the packaged DejaVu Sans — no `/System/Library/...` anywhere).
  `_payload` still reads the row as it is; the new `_banded(payload, number)`
  turns it into the two payloads the pages are drawn from — puzzle page
  `name=None, difficulty=identity`, answer page `name=<picture title>,
  difficulty=identity`. `_puzzle_and_answer` now takes the puzzle's print
  number and makes **two** `render_pages` calls always (the two pages no longer
  share a header, so the old "one call when the parities agree" shortcut is
  gone). `interior_pages` passes `index + 1`: N is the 1-based position among
  the payloads that *survived* the drop pass, so numbers never leave a gap
  where a broken member was, and the answer page built in the same iteration
  carries the same N.

  **Tier source.** Always `difficulty.tier_of_record` on the row's stored text
  (FR-009, ADR-0031) — never grid size, never the raw stored spelling, so
  `"easy"`, `"Easy"` and `"EASY"` all print `Easy`, and ADR-0031/R3's `"guess"`
  prints `Hard` without anything being rewritten.

  **Decision for a missing/unrecognised tier:** the band prints **`"Puzzle 12"`
  alone** — number, no dot, nothing after it. Rejected: printing the raw stored
  text (an unvetted database string on a printed page, spelled however it
  happens to be spelled) and inventing a label such as "Unrated" (a fourth tier
  on the page, where ADR-0031 has exactly three). The number still identifies
  the puzzle and still matches the answer key; the missing grade shows up as an
  absence to whoever proofs the book. Covered by
  `TestBookPdf_UngradedPuzzlePrintsItsNumberAlone` and by the property corpus,
  which includes `None`, `""`, `"extreme"` and a non-string tier.

  **Answer page carries both,** as `"Snowflake — Puzzle 1 · Hard"` — the title
  first, deliberately: the export fits an over-wide header by setting it smaller
  and then eliding **the first piece**, which is safe only while the first piece
  is the long one. A 200-character picture name in the second slot would be the
  piece that does not fit and the piece that is never cut, so putting the name
  first keeps the number and tier — what the answer key is *used* by — whole.

  **Tests** (`tests/test_book_pdf_band.py`, 25 passing): AC-193
  `TestBookPdf_PuzzlePageCarriesNoPictureTitle`, AC-194
  `TestBookPdf_AnswerKeyCarriesPictureTitle`, AC-195
  `TestBookPdf_EveryFifthGridLineWider`, EC
  `test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle`
  (28 seeded books, 80+ puzzles, 13 names incl. Cyrillic/Greek/Hebrew, a
  200-character one and a decoy name that *is* a band line, x 13 stored tier
  spellings x varied print positions; minimum case counts asserted inside the
  test). Bands are read back by rendering the expected line through COMP-007
  and comparing pages byte for byte, with ink checks and rename controls so a
  blank band can never pass. AC-195 measures the printed page: `page_ink`
  supplies the grid box by its own route, then a scanline through the middle of
  the first cell counts 31 runs of ink per axis — thin 3 px (0.254 mm ≥ the
  0.25 mm floor), heavy 6 px at lines 0/5/…/30, only greys {0, 255} and only
  `(0,0,0)` ink, i.e. no anti-aliasing. Mutation-checked: clearing the elision,
  keeping the name on the puzzle page, an off-by-one N, dropping the title from
  the answer page and lowering `min_thin_rule_mm` each fail these tests.
  Full suite green (only the known pre-existing
  `TestFlow2BatchImageUpload::test_size_configuration_applied` deselected);
  CARD-113's A4 golden tripwire untouched and green.

  **Owner proof renders:** `/Users/omelnikova/Documents/nonogram-reviews/CARD-117/`
  — `30x30-even-page2-puzzle.pdf/.png` (even/left-hand page, 4.97 mm cell),
  `15x15-odd-page3-puzzle.pdf/.png` (odd/right-hand, 7.50 mm cell),
  `30x30-odd-page5-answer.pdf/.png` (the title's one page),
  `full-interior-6pages.pdf`, and `README.txt` listing what to measure on each
  and the expected value. All at real Book 1 geometry, 300 DPI, correct DPI
  metadata; built from in-memory puzzle dicts, `nonogram_admin.db` never
  opened. The render script was a scratchpad throwaway and is not in the repo.

- [Handover] CARD-118: print the four PDFs above at 100% ("actual size", not
  "fit to page") and measure against `README.txt` — band wording, thin rule
  ≥ 0.25 mm, every 5th rule exactly 2x thin, pure black, cell 4.97 / 7.50 mm.
  The open question ADR-0037 leaves to the proof is whether the fixed 0.25 mm
  rule makes the 30x30 look too dense.
- [Handover] CARD-128 (order by level): numbering is positional, not stored —
  `interior_pages` numbers puzzles by their place in the list it is handed, so
  reordering `puzzles` renumbers the bands and the answer key together with no
  change here. If a divider page per level is inserted, only the *page*
  positions move (`2 + index`, `first_answer_page + index`); the puzzle number
  stays `index + 1` and must keep counting puzzles, not pages.
- [Handover] CARD-134 (two-up pages): a paired page carries two bands, one per
  puzzle, and `_banded` already produces exactly one payload per page. The
  pairing code needs its own way to set two headers on one sheet — the export
  draws one band per `render_pages` call — so that is a COMP-007 conversation,
  not a payload trick.

- [Scope] src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf_band.py

- [Build gate] PASSED (full, 210s; 4535 passed, 26 skipped, 1 deselected — the known pre-existing TestFlow2BatchImageUpload::test_size_configuration_applied)
- [Scope gate] IN_SCOPE (2 files, both inside Touches; no hits under G-2 src/nonogram/export/** or G-4 app.py/book_manager.py/templates/**)
- [Review 1/3] first attempt aborted mid-review by a session rate limit (no report written, no score) — re-run, not counted as a cycle
- [Review 1/3] Score: 9.0 — crit: 0, imp: 0; 4 Minor, 4 out-of-scope. Verdict LOW risk, no approve conditions.
- [Review 1/3] Step 8h: 47/47 card rules carry a verdict line (14 ✓ holds, 33 ⚠ unchecked, 0 ✗). INV-009/INV-010/INV-011 read ⚠ check_ref_missing — six named tests do not exist in tests/ (per-level dividers, two-up pairing, 6-up answer key are not built yet). Pre-existing model gap, not this card's.
- [Review sync] 1 report(s) → meta/review/20260923T051146Z-CARD-117-cycle1.yml
- [Review 1/3] Score: 9.0 ✓ threshold reached + no critical/important
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-193 ✓ demonstrated — TestBookPdf_PuzzlePageCarriesNoPictureTitle: PASSED test_the_puzzle_page_is_the_page_of_a_nameless_payload; PASSED test_renaming_the_picture_leaves_the_puzzle_page_identical
  AC-194 ✓ demonstrated — TestBookPdf_AnswerKeyCarriesPictureTitle: PASSED test_the_answer_page_carries_the_title_and_the_same_identity; PASSED test_the_title_is_ink_the_answer_band_would_not_have_without_it; PASSED test_the_answer_number_is_the_number_printed_on_the_puzzle
  AC-195 ✓ demonstrated — TestBookPdf_EveryFifthGridLineWider: PASSED test_the_grid_is_the_thirty_by_thirty_at_the_stated_cell; PASSED test_every_fifth_rule_is_wider_than_every_rule_between_them[vertical|horizontal]; PASSED test_the_rules_are_pure_black_and_not_anti_aliased[vertical|horizontal]
  EC(ADR-0037/R1) ✓ demonstrated — PASSED test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle; genuinely multi-case: 28 seeded books (random.Random(20260923)), 13 names x 13 stored tier spellings x varying print position, minimum counts asserted inside the test (>=24 books, >=60 puzzles, position >=4, all three labels, >=8 names); expected band comes from the test's own second implementation, not from band_identity/tier_of_record
  G-1 ✓ demonstrated — diff adds no drawing primitive and no cell-fitting arithmetic in the admin; TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden green
  G-2 ✓ demonstrated — no path under src/nonogram/export/ in the diff; tests/test_export_a4_golden.py (63 passed) and tests/property/test_cli_exports_byte_identity.py (3 passed) green, untouched, fixtures not regenerated
  G-3 ✓ demonstrated — no hint machinery added anywhere in the diff
  G-4 ✓ demonstrated — changed-file set is exactly the two Touches files; app.py / book_manager.py / templates/** unedited (the new test imports book_manager's types, an import not an edit)
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0031/R1) by an independent skeptic re-running the named checks on 06b158f. Two citation nits, neither a miss: the card's checker names TestDependencyBaseline_IsExactlyPillowAndNumpy and TestTiers_ThreeBandsAndNoFourthTier are trace.yml contract names, not pytest node ids (mapped in the modules' own docstrings to test_the_dependency_baseline_is_still_closed / test_tiers_three_bands_and_no_fourth_tier); and ADR-0031/R1's cited range 118-121 is two lines short of the None-return it describes (the body is 118-123).
- [Docs step] No README written: src/nonogram/admin/ has no per-directory README, and tests/README.md is a stale "Wave 1" document no later card maintains — editing it would be a drive-by change on a shared file while CARD-123/CARD-126 run. Structure and purpose of the touched directories are unchanged by this card.
- [Commit] Success commit is 06b158f (the implementation commit): conventional message with the card's context and rationale, exactly the two Touches files, nothing under meta/, attribution line present. The review produced no critical/important findings to fold in and the docs step produced no changes, so no follow-up commit was made.


- [Done] main unchanged since branch base 17c647b; the card's full-suite gate (4535 passed) ran on this tree. Merged 837a6f3 (--no-ff). Deferral scan: 0 hits, no SCOPE+. Proof PDFs for CARD-118 in ~/Documents/nonogram-reviews/CARD-117/.
