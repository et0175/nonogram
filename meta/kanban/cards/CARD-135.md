# CARD-135: Interior PDF without the cover — the book starts at the guide page, the cover is its own file

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/135-interior-pdf-cover-separate
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-13 (FR-043 interior/cover split, added by the 2026-09-22 (d) delta; lands before CARD-116 so page parity is born counted from the guide page)
**Idea:** —
**Wave:** 20
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_finalize.html, tests/test_book_export_interior_cover.py, tests/property/test_book_export_interior.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Today `BookPDFGenerator.generate_book_pdf` appends the cover (`create_cover_page`: the
uploaded image resized to the page, or a generated title page) as **page 1 of the one
book PDF**, then the guide page, puzzles, the SOLUTIONS divider and the answers. KDP
does not accept that file as an interior (owner decision BK-9, book rule 15; FR-043).
This card splits the export into two files **before** CARD-116 introduces page parity,
so parity is counted from the right page from the start.

1. **Two outputs.** The book export returns an **interior PDF** and a **cover file**
   (a small result type, e.g. `BookExport(interior: BytesIO, cover: BytesIO,
   interior_page_count: int)`). The interior holds **no cover page**: its page 1 is
   the guide page. Every other page keeps today's content and order.
2. **Cover file.** One page, at the book's page size (today's hard-coded
   2550 × 3300 px letter page; CARD-116 moves every page, the cover file included, to
   the stored trim). It holds the uploaded cover image when one is set, otherwise
   today's generated title cover (`create_cover_page`, unchanged). Front cover only.
3. **Page numbering starts at the guide page.** Expose each interior page's 1-based
   position (page 1 = guide page = right-hand, odd) so CARD-116 can build
   `book_page_spec(book, page_number)` from it. The interior page count is the book's
   page count; the cover is never counted (FR-030 as amended; CARD-129 reads it).
4. **Every export route produces the same pair.** The Finalise step's
   `download_pdf` action, `POST /book/<id>/download-pdf` and
   `POST /book/<id>/generate-pdf`. Offer the two files as two downloads (e.g. an
   interior and a cover button on Finalise; `?part=interior|cover` on the routes).
   Note: `generate-pdf` today goes through `admin/pdf_generator.get_pdf_generator()`,
   a different generator from `BookPDFGenerator`, and the Finalise download does not
   pass the session's uploaded cover (`book_{id}_cover_path`) to the generator at all.
   Route both through `BookPDFGenerator` and pass the uploaded cover, and record what
   you found in Worktree notes.
5. **Out of scope:** a full KDP cover wrap (spine width from page count, back cover,
   bleed) — deferred by the owner (raw-requirements (d) line 3).

## Acceptance criteria

- **AC-283** (INV-013) — given a Book 1 profile book with an uploaded cover image and 3 easy 20x20 puzzles, when the book is exported, then the interior PDF's page 1 is the guide page.
  *test:* `TestBookExport_InteriorStartsAtGuidePage`
- **AC-284** (INV-013) — given the book of AC-283, when every page of its interior PDF is inspected, then no page holds the cover image or the generated title cover — the interior has no cover page.
  *test:* `TestBookExport_InteriorHoldsNoCoverPage`
- **AC-285** — given the book of AC-283, when the book is exported, then a separate cover file is produced — a 1-page PDF of 2550 x 3300 px (the 8.5 x 11 in trim at 300 DPI) holding the uploaded cover image.
  *test:* `TestBookExport_CoverIsSeparateSinglePageFile`
- **AC-286** (INV-013) — given a Book 1 profile book with no uploaded cover image, when the book is exported, then the cover file holds the generated title cover and the interior PDF's page 1 is still the guide page.
  *test:* `TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover`
- **AC-289** (INV-013) — given the book of AC-283 exported through each of the Finalise download, POST /book/<id>/download-pdf and POST /book/<id>/generate-pdf, when the three exports are compared, then each yields an interior PDF whose page 1 is the guide page plus a separate cover file.
  *test:* `TestBookExport_EveryRouteSeparatesInteriorAndCover`

## Engineering constraints

- **EC-034** (consistency, INV-013; interior/cover half — CARD-116 adds the parity half, CARD-128 asserts it with dividers in AC-287, CARD-129 adds the finalise page-count half, AC-288) — For any book (any members, levels, pairing, answer-key layout and cover or no cover) and every export route, the interior PDF holds no cover page, its page 1 is the guide page, each page's parity is its 1-based position in the interior (page 1 odd, right-hand), the page count finalise checks equals the interior's page count, and exactly one cover file of one trim-size page is produced beside it — for every book, not only the measured examples.
  *test:* `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` — _this card: no cover page in the interior, page 1 = guide page, exactly one 1-page cover file, reported interior page count == PDF page count, over a seeded corpus of books with and without covers and on every route._

## Guardrails

- G-1: Page content is unchanged apart from where the cover goes: guide, puzzle, SOLUTIONS divider and answer pages render exactly as today. The admin panel fits no cells (ADR-0036/R2). Do not edit `src/nonogram/export/**`.
- G-2: CLI and web A4 output stay byte-identical (CON-019). test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden, PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry (CARD-113, same wave — green at wave end).
- G-3: Do not edit `tests/test_export_a4_golden.py`, `tests/fixtures/a4_golden/**`, `tests/property/test_cli_exports_byte_identity.py` (CARD-113) or `src/nonogram/admin/book_plan.py` (CARD-119) — owned this wave.
- G-4: Out of scope: full KDP cover wrap — spine, back cover, bleed (deferred 2026-09-22 (d)).
- G-5: No schema change. Do not edit `src/nonogram/db/**` or `migrations/**`; the uploaded cover keeps its current (session) storage.

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

- **FR:** FR-043 (AC-283..AC-286, AC-289, EC-034 interior/cover half); FR-030 (page count is the interior's)
- **NFR:** —
- **CON:** CON-019
- **ADR:** ADR-0036
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** Button (reuse — two download actions: interior PDF, cover)
- **Screens:** /book/<id>/finalize
- **Standards:** forge:engineering-standards §11

## Worktree notes

—
