# CARD-136: Print setup stores the chosen trim on the book

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/136-store-chosen-trim
**Worktree:** —
**Source:** CARD-115 / CARD-116 handover (gap found during wave 22-23, 2026-09-23)
**Idea:** —
**Wave:** 24
**Depends on:** CARD-116
**Touches:** src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_finalize.html, tests/test_book_trim_persistence.py
**Review score:** 9.0 (cycle 4)
**Started:** 2026-09-23T06:26:37Z
**Closed:** 2026-09-23T09:28:02Z
**Actual:** 0.4d
**Merge commit:** cb0440c
**Blocked by:** —

## What to implement

Print setup validates the owner's trim and then throws it away: it writes only
`book.metadata.size` (a display string), never `books.trim_width_cm` /
`trim_height_cm`. The print columns are written exactly once, by `create_book`, so a
book whose trim the owner changed on Print setup still **prints on the Book 1 profile**
— the geometry, the cell size, the page pixels, all of it.

Two halves, and they must close together:

1. **Store it.** Add a `BookManager.set_print_spec(book_id, ...)` (both storage modes,
   as every other book_manager writer does) that writes the trim columns — and only
   those plus `updated_at` — and call it from `setup_print` after
   `PrintSpecValidator.create_spec` succeeds, in the same place the plan is saved
   (CARD-120). A refused plan must still not save the trim (AC-197's existing rule).
2. **Read it back consistently.** The Finalise screen reads `metadata.size` while the
   export reads the columns. After this card both must report the same trim, or a book
   will display one size and print another.

The export side is already done (CARD-116's `_export_part` passes the real Book), so a
book follows the stored columns the moment they are written.

CARD-115's `book_page_spec` already falls back to the Book 1 profile when the columns
are empty — keep that fallback for legacy books; this card is about new writes.

## Acceptance criteria

- AC-176 (now reachable): a 6 x 9 in book (trim 15.24 x 22.86 cm, Book 1 margins)
  holding a 15x15 puzzle with 7-deep clue gutters draws a 5.92 mm cell (+/- 0.05 mm),
  where the same puzzle on the 8.5 x 11 trim draws 7.5 mm.
  test: TestBookPdf_CellFollowsStoredTrim (exists; extend it to reach the trim through
  the Print setup route rather than a hand-built Book).
- AC-177 (now reachable): every page of that book's PDF is 1800 x 2700 px at 300 DPI.
  test: TestBookPdf_PageSizeEqualsStoredTrim (same note).
- New: setting the trim on Print setup and reopening the book shows the stored trim on
  both Print setup and Finalise, and the exported interior uses it.
  test: TestBookTrim_SetupPrintStoresAndExportFollows
- New: a submission whose plan is refused saves neither the plan nor the trim.
  test: TestBookTrim_RefusedPlanStoresNothing

## Guardrails

- G-1: `create_book`'s existing Book 1 profile defaults are unchanged — a book created
  and never edited keeps 21.59 x 27.94 cm with the CON-018 margins.
- G-2: `book_page_spec`'s profile fallback for legacy books (empty columns) is unchanged.
- G-3: Do not edit `src/nonogram/export/**` or `tests/fixtures/a4_golden/**`.
- G-4: `set_print_spec` writes no puzzle membership, order, titles or status
  (the INV-008 rule CARD-120's `save_plan` already respects).

## Architecture context

- **FR:** FR-030 (AC-176, AC-177), FR-031
- **CON:** CON-018
- **ADR:** ADR-0036
- **Components:** COMP-009, COMP-010
- **Trace:** meta/architecture/trace.yml

## System contract

Assembled fresh from the model at review time (system_rules.py --card CARD-136), 44 rules:

- ADR-0006/R1 [mandatory] — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as package data instead, and doing so is not a dependency change. (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 [mandatory] — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it may import the orchestrator but no capability module may import it or cli.py. (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 [mandatory] — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer. (check: review-lens)
- ADR-0022/R3 [mandatory] — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by more than 2x from the source's INK BOUNDING BOX ratio — not from its as-decoded file ratio — is refused rather than cropped. The bounding box is computed and judged before any crop is applied, so a refused request is still refused before any cropping runs. (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 [mandatory] — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the other side from the source's own aspect ratio, clamped to MIN_SIZE at the bottom only and never at the top. A source whose ratio exceeds N/5 is refused with a message naming the smallest N that would accommodate it, never silently clamped. (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 [mandatory] — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniqueness from the fact that a grid was repaired. (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 [mandatory] — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit on one lineage, is a named constant beside it and is never a second bound; exhausting the counter raises GenerationAbandoned whichever kind of attempt came last. (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 [mandatory] — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that set holds no filled/empty pair), so the filled count is preserved and no cell outside the region changes. (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 [mandatory] — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws nothing from the injected Random or from host state, so a seed replays the same repair lineage everywhere. (check: review-lens)
- ADR-0024/R5 [mandatory] — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 [mandatory] — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DENSITY and MAX_DENSITY are the only statement of that range. (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 [mandatory] — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density grounds, and no module's documentation claims that one does. (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 [mandatory] — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the share of cells settled at that rung; each rung is the fixed point of its technique, so the rung of a cell is a function of the clue set alone; a deeper solve of the same extent scores strictly higher, and the line-solvable corpus populates every score band. (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 [mandatory] — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the tier is derived from that same list — no second derivation, no second solver entry. The ladder's fixed points are phases of that one monotone forward solve — each continues from the board the previous left, the board is never reset and the search is never re-entered — so running a cheaper technique to exhaustion before a dearer one is not re-solving. (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 [mandatory] — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of the solve and branch_nodes, identical on every machine. (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 [mandatory] — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them, intersected), and are re-derived natively inside the solver package; the solver never imports clues.py or any other capability module for the purpose (ADR-0007). (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 [mandatory] — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all (empty or None per-cell tags, an all-zero per-rung histogram, an empty rung list). For uniquely-solvable clue sets, rung attribution is invariant under transposition and under line-visit order — a clue set and its transpose yield the same per-rung cell counts, the same rung list and the same score — and a change to the solver's iteration order may change how a fixed point is reached but never which cells belong to which rung. The invariance holds trivially for the non-unique ones too, since both orientations report nothing. (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 [mandatory] — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid it was handed and refuses, with NotUniquelySolvable, any grid whose clues do not have exactly one solution — including one whose solve timed out or could not be attempted. No caller's assurance substitutes for that check, and no admin path writes a puzzle row by another route. (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 [mandatory] — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never satisfies a quality minimum, is never the left operand of an order comparison, and renders as "N/A" wherever a score would be shown — templates, API responses and the book PDF alike, the book omitting the /100 denominator that a non-number does not take. recognizability carries the same rule in its own vocabulary. (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 [mandatory] — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id). (check: review-lens)
- ADR-0035/R1 [mandatory] — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percentage points of that cell's planned share. (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 [mandatory] — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 [mandatory] — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (check: review-lens)
- ADR-0037/R1 [mandatory] — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 [mandatory] — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- CON-005 [mandatory] — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 [mandatory] — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's socket-reach half is discharged by more than a threshold visible only in requirements.yml. (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 [mandatory] — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form request target whose authority is not a loopback name (NFR-004). Restates NFR-004 as a gate-enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's browser-mediated-reach half is discharged too, not only its socket-reach half (CON-009): binding to 127.0.0.1 alone does not stop this, since a browser sets Host from the request's target url, not from the page's origin. (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 [mandatory] — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This supersedes the 10..50 range FR-001 carried; FR-001 is marked status: superseded, superseded_by: FR-019, and FR-019 restates the behaviour over the narrowed range. (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 [mandatory] — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an explanatory error rather than converted (FR-021). The centred crop of FR-020 retains exactly min(r_src, r_tgt) / max(r_src, r_tgt) of the source with r = width/height, so this is exactly the rule "never silently discard more than half the user's picture". Retaining exactly 50% (a ratio difference of exactly 2x) is ACCEPTED — the boundary is inclusive. (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 [mandatory] — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a parameter: no supported call into nonogram.admin.app widens it, and no module under src/nonogram/admin/ names another bind address in code. Restates NFR-003 for the second inbound HTTP surface, which CON-009 does not reach. (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 [mandatory] — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not pass the door in force. With it unset (the default), it refuses any request whose Host header does not name this machine — a bare authority, no userinfo, path, query or fragment, a port absent or all digits, and a host component in {localhost, 127.0.0.1, ::1} — and refuses a request carrying no Host header at all. With it set, it refuses any request whose Host is not exactly that hostname (a loopback Host included), any request not carrying the configured credential, and any request the browser marks as started by another site (a Sec-Fetch-Site outside {same-origin, none}, or an Origin whose host is not that hostname). The wrong-host refusal is indistinguishable from "no such page" in both modes, so it tells a scanner nothing. Holds however the socket was bound, including when the bind was widened by an option outside this package's control. (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- INV-001 [mandatory] — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 [mandatory] — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 [mandatory] — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured maximum bound (NFR-002). (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 [mandatory] — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 [mandatory] — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 [mandatory] — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 [mandatory] — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 [mandatory] — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit move inside that level (FR-041). (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 [mandatory] — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; pairing never changes the book order (FR-040). (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 [mandatory] — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 once it holds one longer than 20; no answer-key page holds answers of two levels (FR-042). (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 [mandatory] — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; ADR-0035 clarification). (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 [mandatory] — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the interior's; the cover is produced as a separate file (FR-043). (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Worktree notes

- [Origin] Found by CARD-115 (handover) and confirmed by CARD-116, which deliberately
  left it (its G-4 forbade the book_manager write). Until this card lands, a
  UI-configured trim is display-only.

- [Handover from CARD-123, 2026-09-23] The Finalise Summary's "Trim size" row still reads book.metadata.size and renders nonsense like "8x10 x 27.94 cm" — it does not read the print columns the floor figure is measured against. Visible in ~/Documents/nonogram-reviews/CARD-123/finalize-after-trim-change.png. Closing that row is the display half of this card.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

- [Implementation, 2026-09-23] Both halves closed.
  **Store it.** `BookManager.set_print_spec(book_id, spec)` (book_manager.py,
  beside `save_plan`) writes `trim_width_cm`/`trim_height_cm` + `updated_at`
  and nothing else, in both storage modes. It takes a validated `PrintSpec`
  rather than raw strings — the posture `save_plan` takes towards a
  `DistributionPlan`, so the type is the proof the trim passed
  `PrintSpecValidator.create_spec`; anything else raises `ValueError`. The
  margins on the spec are deliberately *not* written (Print setup has no
  margin field; CON-018's margins stay where `create_book` put them, G-1).
  `setup_print` calls it where `save_plan` is called, so AC-197's rule — a
  refused plan stores neither half — holds for the trim too.
  **Read it back.** `setup_print`'s GET now fills its two fields from the
  stored columns (empty = legacy book = the profile defaults, G-2), and the
  Finalise summary's Trim size row comes from `_trim_cm(book)`, which reads
  `book_page_spec(book)` — the same door the printed-cell figures come
  through (EC-021), so the row and the mm figures beside it cannot disagree.
  The row now carries `data-trim-width-cm` / `data-trim-height-cm` for
  machine reading, and says "Cannot be read" instead of rendering a size
  nobody can print when the stored spec is refused (the posture
  `_book_cells` already takes). `book.metadata.size` is no longer written by
  Print setup at all: it was the defect, and both storage modes now behave
  identically.

- [Tests] `tests/test_book_trim_persistence.py` (new, 42 cases): the trim
  stored through the route and read back on Print setup and Finalise after
  reopening (new client, and in DB mode a new app, so only the stored row can
  carry it); the real `download_pdf` route producing 1800 x 2700 px pages at
  6 x 9 in; a refused plan (and a refused trim) storing neither half; G-4 —
  the writer leaving membership, order, titles, status, overrides, margins
  and the plan alone; G-1/G-2 — profile defaults and the legacy empty-column
  fallback. Both storage modes throughout, DB mode on a real SQLite file.
  `TestBookPdf_CellFollowsStoredTrim` and `TestBookPdf_PageSizeEqualsStoredTrim`
  now reach their trim through `POST /book/<id>/setup-print` (new
  `print_setup` fixture) instead of a hand-built Book; their page-measured
  oracles are untouched.
  Full suite: **4611 passed, 26 skipped, 1 deselected**, exit 0 — only the
  known pre-existing
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`.
  Private `--basetemp` (sibling worktrees share pytest's tmp root).

- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py,
  src/nonogram/admin/templates/book_finalize.html,
  tests/test_book_trim_persistence.py — all four predicted.
  `SCOPE+ tests/test_book_pdf.py — AC-176/AC-177 say "extend it to reach the
  trim through the Print setup route rather than a hand-built Book"; the
  change is additive (a fixture plus the book source of two classes).`
  `src/nonogram/admin/templates/book_setup_print.html` was **not** needed:
  the fields already render `default_width`/`default_height`, which the route
  now fills from the stored columns.

- [Guard] G-3 clean: nothing under `src/nonogram/export/**` or
  `tests/fixtures/a4_golden/**` is in the diff; CARD-113's golden A4 tripwire
  and the CLI byte-identity property test ran green untouched. G-1/G-2 have
  their own tests in the new file. Nothing under `meta/` committed; no
  `nonogram_admin.db`, no egg-info.

- [Visual] Owner renders in `~/Documents/nonogram-reviews/CARD-136/` (HTML
  with the stylesheet and previews inlined, PNGs from headless Chrome):
  `finalize-before-trim-change` (Book 1 profile: Trim size 21.59 × 27.94 cm,
  0 below the floor), `print-setup-shows-stored-trim` (reopened in a fresh
  session: 15.24 / 22.86 in the two fields), `finalize-after-trim-change`
  (Trim size **15.24 × 22.86 cm**, and the below-floor list now naming a
  puzzle at 4.65 mm — the row and the cell figures finally measured on the
  same trim).

- [Handover] `book_detail.html`'s "Size" row still shows
  `book.metadata.size` — the creation-time KDP string ("8x10"), which Print
  setup no longer overwrites. It was never persisted in DB mode anyway, so
  nothing regressed, but that row is the last display reading a field that is
  not the trim of record; a later card should point it at the print columns
  (or at `_trim_cm`) or drop it.

- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/templates/book_finalize.html, tests/test_book_pdf.py, tests/test_book_trim_persistence.py (fix scope)
- [System contract] section absent — assembled fresh from the model (44 rules) and written onto the card
- [Build gate] PASSED (full, 214s) — 4611 passed, 26 skipped, 1 deselected (known pre-existing e2e test_size_configuration_applied)
- [Scope gate] in_scope — 1 of 5 changed files outside Touches (tests/test_book_pdf.py, 20% < 25%, declared SCOPE+ and mandated by AC-176/AC-177); no guardrail glob hit; no wave-24 sibling poached
- [Visual] not a UI card by the procedure test (no ## Design context, Skill python-pro) and there is no Makefile run target — review runs static-only; the owner renders the implementation produced are in ~/Documents/nonogram-reviews/CARD-136/

- [Review sync] 1 report -> meta/review/20260923T071007Z-CARD-136-cycle1.yml
- [Review 1/3] Score: 7.5 — crit: 0, imp: 1 (F-001 `set_print_spec` promises a validation guarantee the `PrintSpec` type does not carry)
- [Review 1/3] Step 8h coverage: 44/44 card rules carry a verdict line in the YAML (18 holds, 26 unchecked, 0 violated) — count line present in the reviewer output
- [Adversarial] F-001 CONFIRMED — independent skeptic reproduced it in BOTH storage modes: `PrintSpec` is a plain non-frozen dataclass with no `__post_init__`, so `set_print_spec`'s isinstance gate proves only the type; `set_print_spec(bid, PrintSpec("999","abc"))` returns True and stores `999`/`abc`, after which `book_page_spec` raises — while `DistributionPlan`/`Split` really are frozen and self-validating, which is what makes `save_plan`'s identical sentence true. `test_it_accepts_nothing_but_a_validated_spec` only ever refuses a dict. No live defect (the one production caller passes a `create_spec` result).
- [Severity gate 1/3] Score 7.5 < 8 AND 1 confirmed important finding — fix mandatory
- [Fix 1] pre-gate PASSED — all 6 FIXED lines name existing tests, all green (201 cases in tests/test_book_trim_persistence.py, exit 0); every FIXED line carries a DECLARATIONS line; no "matrix updated" claim to cross-check (this card has no ## Failure matrix)
- [Fix 1] declarations: 6 updated, 0 confirmed, 0 none — set_print_spec docstring + Raises:, setup_print docstring, new _submitted_trim_cm docstring, tests/test_book_trim_persistence.py module docstring (x2). Two DESIGN CHANGES declared: the width/height form fields acquire a second meaning in inches mode (a value equal to the rendered string means "keep the stored centimetres"), and `unit_preference` becomes the unit the PAGE is rendered in, which may differ from the unit the session remembers.
- [Fix 1] F-004 partially accepted by design: each writer is now followed on its own return value ("Book not found" instead of a success flash), but plan and trim remain TWO writes in TWO sessions in DB mode — a failure between the commits can still leave the plan stored and the trim not. Rationale on the card's fix-round note; a single-session writer for both halves is the follow-up if that window ever matters. OWNER-VISIBLE CHOICE.
- [Build gate] PASSED (full, 211s) — 4647 passed, 26 skipped, 1 deselected (known pre-existing e2e), exit 0
- [Scope gate] in_scope (cycle 2) — same 5 files; tests/test_book_pdf.py still the only one outside Touches (20% < 25%); no guardrail glob hit
- [Review sync] 1 report -> meta/review/20260923T080241Z-CARD-136-cycle2.yml
- [Review 2/3] Score: 8.5 — crit: 0, imp: 1 (F-101 an empty/absent trim field in cm mode silently overwrites the stored trim with the Book 1 profile and flashes success). All six cycle-1 findings re-derived by execution and RESOLVED; the fix round introduced no defects of its own.
- [Review 2/3] Step 8h coverage: 44/44 card rules carry a verdict line (18 holds, 26 unchecked, 0 violated); 22 carried delta-clean, ADR-0019/R1 and ADR-0029/R4 re-run fail-closed (import guard green)
- [Review 2/3] no family regression — the cycle-2 finding is on the cm branch, untouched by the fix delta; streak 0. Not stalled: Δscore +1.0 >= 0.5.
- [Review 2/3] Owner-visible choices ENDORSED by the reviewer, not blocking: the two-transaction window between plan and trim; the width/height fields' second meaning in inches mode; `unit_preference` as the unit the PAGE is rendered in.
- [Adversarial] F-101 CONFIRMED — independent skeptic reproduced it verbatim in BOTH storage modes: `POST unit=cm width=""` (and with the width/height keys absent) returns 302, flashes "Print specs set", and replaces a stored ('15.24','22.86') with the Book 1 profile, while the identical INCHES submission is refused with a 200 and stores nothing. No upstream guard exists on the cm branch; `create_spec` defaults a falsy value (print_specs.py:155-156), so `set_print_spec`'s new validation cannot catch it — the spec is by then a valid Book 1 spec. `required` on both template inputs means no live browser path, and no test covers the empty/absent field. Skeptic's one reservation: severity is arguably a notch high for a hardening gap.
- [Severity gate 2/3] Score 8.5 >= 8 but 1 confirmed important finding — fix mandatory
- [Fix 2] pre-gate PASSED — both named tests exist and are green (TestBookTrim_ABlankTrimFieldStoresNothing, TestBookTrim_ThePageCarriesOneUnit; 87 cases, exit 0); F-102/F-103 legitimately `test: n/a` (docstring-only); every FIXED line carries a DECLARATIONS line
- [Fix 2] declarations: 3 updated, 2 confirmed, 1 none — setup_print docstring (a blank trim field is a refused submission, not a default), new _blank_trim_error docstring, _submitted_trim_cm docstring (F-102's precision + the strip), the refusal error text, the test-module docstring; `set_print_spec`'s Raises: and `create_spec`'s documented defaulting re-derived and CONFIRMED still correct (neither speaks about blank form fields)
- [Build gate] PASSED (full, 238s) — 4679 passed, 26 skipped, 1 deselected (known pre-existing e2e), exit 0
- [Scope gate] in_scope (cycle 3) — measured against the merge base db74b04 (main has since advanced to dbbf5b9 with CARD-137 merged; no file overlap with this card). Same 5 files; tests/test_book_pdf.py still the only one outside Touches (20% < 25%); no guardrail glob hit.
- [Review sync] 1 report -> meta/review/20260923T084331Z-CARD-136-cycle3.yml
- [Review 3/3] Score: 9.0 ✓ threshold reached + no critical/important. Full review (cycle 2's discovery reset confirmation mode). All ten prior findings re-derived BY EXECUTION in both storage modes and resolved; the blank-trim guard introduced no defects — legitimate and padded submissions still store, `inches_to_cm("0")` returns a truthy "0.00" so numeric zero is refused on bounds rather than re-opening create_spec's defaulting hole, and a blank trim beside a valid plan stores neither half.
- [Review 3/3] Step 8h coverage: 44/44 card rules carry a verdict line (16 holds, 28 unchecked, 0 violated); count line present
- [Review 3/3] not stalled: Δscore +0.5 >= 0.5; no family regression (each cycle's finding was a distinct mechanism, none attributed to the previous fix)
- [Handover] The blank-trim guard also refuses a TRIM-LESS submission: an absent `width`/`height` key is treated exactly like an empty one, so a plan-only POST to setup-print — which before this card saved the plan and let `create_spec` default the trim — is now refused whole (200, neither half stored). Declared in `setup_print`'s docstring; recorded here because that is the behaviour change outside this card's AC that a later card would otherwise meet by surprise.
- [8h spot-check] 2/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1 — both re-derived by independent skeptics with their own evidence; two wording imprecisions noted in ADR-0006/R1's line, neither affecting the conclusion)
- [8h spot-check] ✗ ADR-0032/R1 not reproduced — the rule's CONCLUSION was independently confirmed (no `add_puzzle` change, no new puzzle-write route, `TestStorageBoundary_AsksTheSolverNotTheCaller` passes 2/2 unmodified, and the skeptic found no violation), but three cited evidence elements did not re-derive: (1) the line range `book_manager.py:739-758` does not contain the writes — memory mode writes at 730-732, DB mode at 741-745, and 747+ is a different method; (2) the "161-case book/admin batch" count reconstructs from no selection (observed 191 for the three named files, 1122 for the broad sweep); (3) the characterisation "strengthens rather than bypasses the storage-boundary posture" is overstated — `BookManager.get_book` returns the LIVE `Book` object in memory mode (book_manager.py:570) and `Book` is a plain mutable dataclass, so a caller can write "999"/"abc" straight into the trim columns past `set_print_spec`'s new validation gate. Demonstrated: writer refuses, direct mutation succeeds, `book_page_spec` then refuses the stored value. Mitigations the skeptic recorded: no `src/` code does this, DB mode returns a detached snapshot so the mutation is dropped, and the reader refuses rather than printing a bad trim.
- [Escalated] 2026-09-23 — station: implementation. Step 8h holds failed re-derivation at cycle 3/3 (max_cycles), which the start/review procedure escalates rather than passing. NOT a stalled loop and NOT a quality failure: the score climbed 7.5 -> 8.5 -> 9.0, every one of the ten findings raised across three cycles was re-derived by execution and resolved, and cycle 3 reported zero critical and zero important findings. What a human must decide is whether the substantive half of the spot-check — the writer-side trim gate being bypassable in memory mode, while the review's verdict called it a strengthening of the storage boundary — needs closing on this card or is acceptable as it stands (the same class of over-claim as F-001, which this card already fixed once).
- [Escalated] Route: one more review round — `/kanban review CARD-136` — is the cheap path: the reviewer owns the verdict line and re-states it honestly, and the AC/EC/G gate (which never ran, see below) then runs. `/kanban redo` is NOT indicated; the loop converged.
- [Escalated] ⚠ THE TWO FIX ROUNDS ARE UNCOMMITTED in the worktree (commit 5bad570 holds the implementation only). The worktree /Users/omelnikova/PycharmProjects/PythonProject4-CARD-136 and branch card/136-store-chosen-trim are KEPT and must not be abandoned or removed — `/kanban abandon` would discard both fix rounds.
- [AC/EC check] (SUPERSEDED — this note recorded the gate not running at the escalation; the gate has since run in full, see below)
- [Docs step] (SUPERSEDED — see below)
- [Unblocked] 2026-09-23 — OWNER DECISION, relayed by the dispatcher: the memory-mode bypass is ACCEPTED as-is on this card. Rationale recorded as given: it is a property of the in-memory fallback's live-object semantics rather than something this card introduced; DB mode validates on the way in and `book_page_spec` refuses a bad value on read. It is being carded separately. Escalation cleared; the card re-enters at the review phase for an honest restatement of the ADR-0032/R1 verdict, the AC/EC/G gate (which never ran) and the commit.
- [Commit] dc0681f — the two review fix rounds committed with explicit pathspecs (src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, tests/test_book_trim_persistence.py). Nothing under meta/, no .db, no egg-info. The card now has two commits on 5bad570's branch.
- [Review sync] 1 report -> meta/review/20260923T090133Z-CARD-136-cycle4.yml
- [Review 4/3] Score: 9.0 ✓ threshold reached + no critical/important. Confirmation-mode re-entry after the owner unblocked the escalation. Delta-clean verified rather than assumed: `git diff dc0681f` touches only the card file, `git status --porcelain -- src/ tests/` is empty, and the full suite reproduces cycle 3's numbers exactly (4679 passed, 26 skipped, 1 deselected, 221.27s, exit 0) — the strongest available proof the two fix rounds moved into dc0681f unchanged.
- [Review 4/3] ADR-0032/R1 RESTATED honestly, which was this cycle's whole job. The rule holds because the card introduces no puzzle-write route — NOT because it strengthens the storage-boundary posture. The memory-mode live-object bypass is named inside the verdict as a known limitation with its three verified mitigations, and appears under Out-of-scope observations rather than as a gating finding, per the owner's decision. The wrong line range is corrected from the file as it stands (set_print_spec spans 655-745; the six assignments are at 730-732 and 741-743, committed at 744; 747 begins floor_overrides) and the unreconstructable "161-case" count is replaced by a selection the reviewer actually ran (TestStorageBoundary_AsksTheSolverNotTheCaller -> 2 passed in 0.02s, the check test unmodified and absent from the diff).
- [Review 4/3] Step 8h coverage: 44/44 card rules carry a verdict line (16 holds, 28 unchecked, 0 violated); 13 re-derived fresh this cycle, the rest carried(cycle 3, delta-clean).
- [Review 4/3] Remaining findings are 2 Minor, both re-stated from cycle 3 and accepted there: set_print_spec's non-finite ValueError text names an internal column when it reaches the owner, and Print setup shows the raw stored column while Finalise re-derives it through mm (they agree for every value the route can store; only a legacy "15.2" would differ).
- [8h spot-check] Selection (cycle 4, 3 of 13 fresh holds): ADR-0032/R1 — mandatory, it is the verdict that failed last time — plus ADR-0033/R1 and INV-005, the two fresh test-citing holds not sampled in cycle 3. Stated so the choice is contestable.
- [8h spot-check] ADR-0033/R1 reproduced — `set_print_spec`'s only writes are trim_width_cm/trim_height_cm/updated_at at book_manager.py:730-732 (memory) and 741-743 (DB) exactly as cited; the named selection gives 30 passed; and `test_nothing_but_the_trim_columns_moves` genuinely snapshots membership, order, titles, status and overrides before the write (test file:417-420) rather than comparing an object with itself, so it discriminates in memory mode too. A full pass over the diff finds no puzzle-field write anywhere.
- [8h spot-check] INV-005 reproduced — all four cited app.py line numbers exact, and the INDENTATION really does put the trim write (2358, indent 20) inside `elif plan_error is None:` (2310), with the blank guard setting `error` at 2287 so `if error:` at 2308 short-circuits both writers. The named class passes 16 cases in both modes inside a run that reproduces "37 passed" exactly. The skeptic added 21 independent adversarial probes through the real route — seven shapes of refused plan (sum 101, sum 99, negative share, negative cell, fractional cell, negative count, empty share) each carrying a VALID different trim, in both storage modes and through the inches branch — and the columns moved in none of them, on a probe first proven discriminating by watching an accepted trim move.
- [Handover] Gap found by the INV-005 spot-check, NOT a gate failure and NOT an INV-005 breach: `PrintSpecValidator.validate_trim_size` accepts the string `"nan"` (every float comparison against NaN is False), so `create_spec` returns a spec with no error, the route enters `elif plan_error is None:`, `save_plan` COMMITS, and only then does `set_print_spec`'s own finiteness guard raise — leaving the plan stored and the trim not. Verified in both modes: POST width="nan" with a plan edit -> 200 + "Error:" flash, plan moved 150->120, trim columns unmoved. The stored plan still sums to 100 with non-negative integers, so INV-005 holds, and this is the reverse direction of the two-transaction window the reviewer endorsed (F-004). Worth knowing: the card's `test_a_refused_trim_stores_neither_half_either` does NOT reach this path — it uses width="5", which `create_spec` refuses before `save_plan` runs. A later card either moves the finiteness check into `validate_trim_size` (so the route refuses "nan" before any writer) or gives the two halves one session.
- [8h spot-check] ADR-0032/R1 — first pass NOT reproduced on one element, then corrected at its own station and re-derived. The skeptic confirmed every numeric citation character-exact (puzzle_review.py:601, the 6-path file list, both grep exit codes, set_print_spec spanning 655-745, the assignments and the commit at 744, 747 beginning floor_overrides, get_book:570, Book:72-87, _row_to_book:514-557, _stored_book:501-522, app.py:3245, both named test runs) AND confirmed the honest restatement the owner asked for. The one failure: the cited repo-wide grep returns 11 lines, and the verdict enumerated 9, omitting book_manager.py:549-550. Sent back to the cycle-4 reviewer, which applied a one-clause fix and named the root cause candidly: it had run the grep WITH a `| grep -v` filter for the constructor kwargs, then cited the unfiltered command while enumerating the filtered results — the same class of defect as cycle 3's wrong line range, an evidence element that reads as reproducible but is not, wrapped around a true conclusion.
- [8h spot-check] Corrected clause re-derived by the orchestrator directly (the check is a deterministic command whose output does not depend on who runs it; the full independent skeptic pass above had already confirmed every OTHER element of this verdict). `grep -rn 'trim_width_cm *=\|trim_height_cm *=' src/` returns exactly 11 lines and each is classified correctly: book_manager.py:730,731,741,742 are the four stored-column writes; 549-550 are Book(...) construction kwargs inside _row_to_book; print_specs.py:166-167 are PrintSpec(...) construction kwargs inside create_spec; app.py:3245 is a tuple-unpack read of _trim_cm(book); db/models.py:148-149 are Column declarations. 3/3 sampled holds now reproduce.
- [Review sync] corrected cycle-4 report re-copied -> meta/review/20260923T090133Z-CARD-136-cycle4.yml (validates: 44 verdict lines, 44 unique ids, 16/28/0, score 9.0, 2 findings)
- [AC/EC check] All criteria/constraints ✓ (evidence), verified by a separate clean-context agent that ran every named test itself:
  AC-176 ✓ demonstrated — TestBookPdf_CellFollowsStoredTrim 3/3; `PASSED ...::test_a_six_by_nine_book_draws_the_smaller_cell` asserts abs(drawn_mm - 5.9170) < 0.05 on 6x9 and `...::test_the_same_puzzle_on_the_book_one_trim_is_held_at_the_standard_cell` asserts abs(drawn_mm - 7.5) < 0.05 on 8.5x11 — the card's own numbers, not re-derived from the code under test. The card's "reach the trim through the Print setup route" is honoured: both books come from a new `print_setup` fixture POSTing to the real route, replacing the hand-built `_book(...)`; a third test was ADDED, not substituted.
  AC-177 ✓ demonstrated — TestBookPdf_PageSizeEqualsStoredTrim 4/4; every page `.size == (1800, 2700)` and every MediaBox `== (0,0,432,648)` pt (6x9 in — the "at 300 DPI" half). Page-measuring oracles unchanged in the diff.
  TestBookTrim_SetupPrintStoresAndExportFollows ✓ demonstrated — 14 passed (7 x both modes). The reopening is real: a fresh client, and in DB mode a freshly built app, so only the stored row can carry the trim back; the export test drives the actual download_pdf interior route and asserts page sizes == {(1800,2700)} with (2550,3300) absent.
  TestBookTrim_RefusedPlanStoresNothing ✓ demonstrated — 16 passed, including 10 parametrised INV-005 refusals in both modes; each asserts BOTH halves (trim columns unmoved AND plan unmoved) with a 200 re-render rather than a redirect.
  G-1 ✓ demonstrated — the PRE-EXISTING covering test TestBookCreate_StoresBook1PrintProfile is green and its file appears 0 times in the card's changed-file list, so it was not weakened, retargeted or deleted; `create_book` has no diff hunk at all (book_manager.py's diff is purely additive); plus the card's own profile test and `test_the_margins_are_not_the_writers_to_touch`.
  G-2 ✓ demonstrated — book_page_spec.py and its test file both appear 0 times in the changed-file list; TestBookPageSpec_EmptyMarginsFallBackToBook1Profile and TestBookPdf_EmptyMarginsFallBackToBook1Profile green and untouched; plus the card's route-level legacy-empty-columns test in both modes.
  G-3 ✓ demonstrated — exact check: `git diff --name-only db74b04 | grep -E '^src/nonogram/export/|^tests/fixtures/a4_golden/'` exits 1, and the same grep over `git status --porcelain` also matches nothing. Bounded claim: the committed diff against the merge base plus every currently uncommitted path.
  G-4 ✓ demonstrated — TestSetPrintSpec_WritesOnlyTheTrim 24 passed. The memory-mode tautology trap is genuinely avoided and was proved so by MUTATION rather than by reading: the agent injected a mutant `set_print_spec` (scratchpad pytest plugin, no repo file touched) that also reversed puzzle_ids and set status="ready", and the test FAILED in both modes — memory on `after.puzzle_ids == before_ids` (the copy caught the live-object mutation), DB on `after.status == before_status == "draft"`.
  8 of 8 items demonstrated; nothing unverified, partial or contradicted. The owner-accepted memory-mode bypass was neither failed nor credited.
- [Docs step] forge:readme — SKIPPED for both changed source directories, deliberately. `src/nonogram/admin/` and `src/nonogram/admin/templates/` have no README.md and this card did not change either directory's structure or purpose (book_manager.py's diff is purely additive — one method, two imports; app.py gains four module-private helpers; no file added, moved or renamed), so the procedure's "create/update if structure/purpose changed; skip if current" resolves to skip. `tests/README.md` exists but is titled "Admin Panel Test Suite - Wave 1" and enumerates only four Wave-1 files (test_batch_history, test_puzzle_preview, test_bulk_operations, test_wave1_e2e); this card's tests are not Wave 1, so adding them to that inventory would be wrong and rewriting the whole file is far outside the card. Pre-existing staleness, recorded rather than fixed here: that README describes a four-file suite while the repo now runs 4679 tests.
- [Build gate] PASSED (full, 241s) — 4679 passed, 26 skipped, 1 deselected (known pre-existing e2e test_size_configuration_applied), exit 0, zero F/E marks. Run under the repo-level full-suite lock with a private --basetemp.
- [Commit] No further commit was needed at the success step: the card's code is entirely in 5bad570 (implementation) and dc0681f (both review fix rounds, committed when the owner unblocked the card), the docs step produced no changes, and the working tree holds nothing but meta/, which is never committed from a worktree. An empty commit was NOT manufactured to satisfy the step.
- [Pipeline complete] Status stays `review` until the dispatcher merges. Two commits to merge onto main (now dbbf5b9, CARD-137 merged, no file overlap with this card). NOT rebased here — the dispatcher rebases at merge.


- [Done] rebased onto main 55a3d3f, full suite on the rebased tree with a private --basetemp: only the pre-existing e2e failure. Merged cb0440c (--no-ff). Deferral scan: 0 hits. Escalation resolved by the owner accepting the memory-mode bypass; 4 review cycles, final 9.0, AC/EC/G gate demonstrated by a clean-context agent with a mutation check on G-4.
