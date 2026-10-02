# CARD-158: The book list and book page show what the book actually holds

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/158-book-pages-show-contents
**Worktree:** —
**Source:** CARD-135 follow-up, CARD-130 handover, CARD-136 handover (backlog); templates re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 30
**Depends on:** —
**Touches:** src/nonogram/admin/templates/books_list.html, src/nonogram/admin/templates/book_detail.html, src/nonogram/admin/app.py, src/nonogram/admin/static/admin.css, tests/test_book_detail_page.py (new)
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-10-02T17:01:36Z
**Closed:** 2026-10-02T18:45:05Z
**Actual:** 0.2d
**Merge commit:** 66214c1
**Blocked by:** —

## What to implement

Four display gaps on `/books` and `/book/<id>`:

1. **Cover download is missing.** Since CARD-135 the export is two files, interior
   and cover, but `books_list.html:115` and `book_detail.html:73` only offer the
   interior. The route already serves the cover: `POST /book/<id>/download-pdf`
   with `part=cover` (`app.py:4407`). Only the buttons are missing.
2. **Puzzles appear as raw UUIDs.** `book_detail.html:117-120` renders
   `<code>{{ puzzle_id }}</code>` for each member, although every puzzle has a
   title (`custom_title`, falling back to `puzzle_name`, as Finalise does).
3. **The "Size" row is stale.** `book_detail.html:42` reads `book.metadata.size`,
   which Print setup no longer writes (CARD-136). It should show the stored trim
   from the book's print spec, or "not set" with a link to Print setup.
4. **The books table overflows at 390 px** (CARD-130 handover; not re-measured).

## What to do

1. Add a cover download next to the interior one on both pages. It follows the
   same lost-upload rule the route already applies (`_cover_upload_lost`).
2. Show each member puzzle's title (and tier, if it's cheap) instead of its id.
   Keep the id available, for example in a `title` attribute or a muted column,
   because the "Add puzzles by ID" form still uses ids. Read titles in one pass;
   if CARD-157 has landed, use `get_puzzles`.
3. Replace the Size row with the stored trim.
4. Make the books table fit a 390 px viewport (horizontal scroll inside the
   table wrapper is fine). Render it at 390 px and put the screenshot in
   `~/Documents/nonogram-reviews/CARD-158/` for the owner.

## Acceptance criteria

- **AC-1:** Both pages offer an interior download and a cover download, and the
  cover button submits `part=cover`.
  *test: TestBookPages_OfferBothExportFiles*
- **AC-2:** The book page lists member puzzles by title, not by id.
  *test: TestBookDetail_ListsPuzzlesByTitle*
- **AC-3:** The book page's size row shows the trim stored by Print setup, and
  "not set" for a book with no print spec.
  *test: TestBookDetail_ShowsTheStoredTrim*

## Guardrails

- G-1: No route, export or PDF behaviour changes; this card only changes templates
  and their view data.
- G-2: Use existing tokens and components only (no inline colours or sizes).
- G-3: The owner checks the rendered pages (see owner-validates-visually).

## System contract

_Assembled 2026-10-02 by system_rules.py --card CARD-158 (scope: Touches); 44 mandatory rules._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as package data instead, and doing so is not a dependency change. (test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it may import the orchestrator but no capability module may import it or cli.py. (test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer. (review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by more than 2x from the source's INK BOUNDING BOX ratio — not from its as-decoded file ratio — is refused rather than cropped. The bounding box is computed and judged before any crop is applied, so a refused request is still refused before any cropping runs. (test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the other side from the source's own aspect ratio, clamped to MIN_SIZE at the bottom only and never at the top. A source whose ratio exceeds N/5 is refused with a message naming the smallest N that would accommodate it, never silently clamped. (test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniqueness from the fact that a grid was repaired. (test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit on one lineage, is a named constant beside it and is never a second bound; exhausting the counter raises GenerationAbandoned whichever kind of attempt came last. (test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that set holds no filled/empty pair), so the filled count is preserved and no cell outside the region changes. (test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws nothing from the injected Random or from host state, so a seed replays the same repair lineage everywhere. (review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DENSITY and MAX_DENSITY are the only statement of that range. (test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density grounds, and no module's documentation claims that one does. (test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the share of cells settled at that rung; each rung is the fixed point of its technique, so the rung of a cell is a function of the clue set alone; a deeper solve of the same extent scores strictly higher, and the line-solvable corpus populates every score band. (test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the tier is derived from that same list — no second derivation, no second solver entry. The ladder's fixed points are phases of that one monotone forward solve — each continues from the board the previous left, the board is never reset and the search is never re-entered — so running a cheaper technique to exhaustion before a dearer one is not re-solving. (test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of the solve and branch_nodes, identical on every machine. (test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them, intersected), and are re-derived natively inside the solver package; the solver never imports clues.py or any other capability module for the purpose (ADR-0007). (test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all (empty or None per-cell tags, an all-zero per-rung histogram, an empty rung list). For uniquely-solvable clue sets, rung attribution is invariant under transposition and under line-visit order — a clue set and its transpose yield the same per-rung cell counts, the same rung list and the same score — and a change to the solver's iteration order may change how a fixed point is reached but never which cells belong to which rung. The invariance holds trivially for the non-unique ones too, since both orientations report nothing. (test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid it was handed and refuses, with NotUniquelySolvable, any grid whose clues do not have exactly one solution — including one whose solve timed out or could not be attempted. No caller's assurance substitutes for that check, and no admin path writes a puzzle row by another route. (test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never satisfies a quality minimum, is never the left operand of an order comparison, and renders as "N/A" wherever a score would be shown — templates, API responses and the book PDF alike, the book omitting the /100 denominator that a non-number does not take. recognizability carries the same rule in its own vocabulary. (test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id). (review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percentage points of that cell's planned share. (test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's socket-reach half is discharged by more than a threshold visible only in requirements.yml. (test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form request target whose authority is not a loopback name (NFR-004). Restates NFR-004 as a gate-enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's browser-mediated-reach half is discharged too, not only its socket-reach half (CON-009): binding to 127.0.0.1 alone does not stop this, since a browser sets Host from the request's target url, not from the page's origin. (test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This supersedes the 10..50 range FR-001 carried; FR-001 is marked status: superseded, superseded_by: FR-019, and FR-019 restates the behaviour over the narrowed range. (test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an explanatory error rather than converted (FR-021). The centred crop of FR-020 retains exactly min(r_src, r_tgt) / max(r_src, r_tgt) of the source with r = width/height, so this is exactly the rule "never silently discard more than half the user's picture". Retaining exactly 50% (a ratio difference of exactly 2x) is ACCEPTED — the boundary is inclusive. (test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a parameter: no supported call into nonogram.admin.app widens it, and no module under src/nonogram/admin/ names another bind address in code. Restates NFR-003 for the second inbound HTTP surface, which CON-009 does not reach. (test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not pass the door in force. With it unset (the default), it refuses any request whose Host header does not name this machine — a bare authority, no userinfo, path, query or fragment, a port absent or all digits, and a host component in {localhost, 127.0.0.1, ::1} — and refuses a request carrying no Host header at all. With it set, it refuses any request whose Host is not exactly that hostname (a loopback Host included), any request not carrying the configured credential, and any request the browser marks as started by another site (a Sec-Fetch-Site outside {same-origin, none}, or an Origin whose host is not that hostname). The wrong-host refusal is indistinguishable from "no such page" in both modes, so it tells a scanner nothing. Holds however the socket was bound, including when the bind was widened by an option outside this package's control. (test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured maximum bound (NFR-002). (test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit move inside that level (FR-041). (test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; pairing never changes the book order (FR-040). (test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 once it holds one longer than 20; no answer-key page holds answers of two levels (FR-042). (test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; ADR-0035 clarification). (test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the interior's; the cover is produced as a separate file (FR-043). (test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-043 (two-file export), FR-030 (print setup)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Four small display leftovers from CARD-130, CARD-135 and CARD-136,
  grouped by the two screens they share. Cut on 2026-10-02.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +44 rules (card had no section) / −none
- [Impl] Commit bc1281b. Changed: `app.py` (`book_detail` passes `members`
  [id/title/tier from one `get_puzzles(book.puzzle_ids)` pass; title =
  `book.puzzle_titles` custom title → `puzzle_name` → id, Finalise's fallback],
  `trim_set`/`trim_width_cm`/`trim_height_cm` via `_trim_cm`, and
  `cover_upload_lost`; `books_list` passes `lost_covers`). No route, form
  handling or PDF code changed (G-1).
- [AC-1] Cover button on both pages posts `part=cover` to
  `/book/<id>/download-pdf` (the route the card names; book_detail's interior
  button still posts to `/generate-pdf`, now with an explicit `part=interior`,
  which is that route's default). Lost-upload rule: when `_cover_upload_lost`
  is true the cover button is rendered disabled, outside any form (book page
  adds a note linking to Finalise; list carries title/aria-label). The cover
  is offered on a book with no puzzles (title cover); only the interior waits.
- [AC-2] Members show title (`.name`), tier badge, and the id muted beneath
  (`.subtle`) for the "Add puzzles by ID" form. Membership read from the
  book's own list, never `puzzles.book_id` (ADR-0033/R1).
- [AC-3] "Size" row → "Trim size": stored trim (e.g. `15.24 × 22.86 cm`);
  "Not set — set it in Print setup" when both trim columns are empty; "Cannot
  be read — set it again in Print setup" for an unreadable stored trim
  (Finalise's posture). Note: `create_book` stores the CON-018 profile, so
  only legacy books show "Not set".
- [390 px] Measured with Playwright (in-memory app on 127.0.0.1, seeded).
  Before: `/books` scrollWidth=450 vs clientWidth=390 (60 px page overflow);
  cause was NOT the table width (it already sat in Bootstrap's
  `.table-responsive`) but `.visually-hidden` spans (", sorted descending",
  "Off plan:") — position:absolute, so they escaped the scroll wrapper.
  Fix: `.table-responsive { position: relative; }` in admin.css (no size or
  colour, G-2). After: `/books` 390/390, overflow 0; `/book/<id>` 390/390 both
  before and after; all pages 1440/1440.
- [Renders] ~/Documents/nonogram-reviews/CARD-158/: before-*.png (baseline),
  after-books-1440.png, after-books-390.png,
  after-books-390-scrolled-to-actions.png, after-book-detail-{1440,390}.png
  (titles, both downloads, stored trim), after-book-detail-not-set-{1440,390}.png,
  after-books-lost-cover-{1440,390}.png, after-book-detail-lost-cover-{1440,390}.png.
- [Tests] tests/test_book_detail_page.py — 22 tests, the three AC classes;
  in-memory mode, runs without Postgres. Hand mutants of every new branch
  (fallback order, trim_set, unreadable branch, lost-cover on detail, list
  all/none lost, missing/wrong part, tier) each fail at least one test.
  Related files (property/test_book_export_interior, property/test_book_workflow,
  test_admin_design_tokens, test_book_arrange_page_breaks,
  test_book_export_interior_cover, test_book_guide_page_type,
  test_book_pdf_ink_mode, test_book_proof_pages, test_book_puzzle_frame,
  test_book_trim_persistence, test_book_workflow_steps,
  test_books_list_plan_stats, test_book_published_confirm, test_cli): 690 passed.
- SCOPE+ tests/test_books_list_plan_stats.py — `TestBooksList_NoHintWhenOnPlan`
  asserted the substring "over" absent from the whole row text, which the new
  "Cover" button label contains; changed to whole-word matches (`\bover\b`,
  `\bshort\b`), which still catch a real "… over 2" hint.
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/book_detail.html, src/nonogram/admin/templates/books_list.html, tests/test_book_detail_page.py, tests/test_books_list_plan_stats.py
- [Build gate] PASSED (full, 404s) — 5831 passed, 9 skipped, 2 failed = exactly the main baseline (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders), pre-existing on main
- [Scope gate] in_scope — comp_spread 0 (COMP-009 only); excess 1/6 (tests/test_books_list_plan_stats.py, SCOPE+ recorded) = 17% < 25%; CARD-159 overlap 1/5 (app.py) < 30%; no structural guardrails
- [Adversarial] F-001 CONFIRMED — deleting `or str(puzzle_id)` leaves tests/test_book_detail_page.py 22/22 green; blank rename stores puzzle_name=None (puzzle_review.py:1202/1216), template renders literal "None"
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1
- [Review sync] 1 report(s) → meta/review/ (20261002T172339Z-CARD-158-cycle1.yml)
- [Review 1/3] Step 8h coverage: 44/44 card rules have a verdict line (19 ✓, 25 ⚠ no_eligible_fact, 0 ✗); mutation check 8/9 killed (M9 survived = F-001)
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Fix 1] FIXED F-001 (2 tests, revert-verified), FIXED F-002 (visible lost-cover hint on /books inside the existing lost-cover branch; test + 2 mutants killed), SKIPPED F-003 (legacy-only state, would add an untested branch; dismissed in YAML); F-004/F-005 out of scope. Pre-gate: 3/3 named tests passed
- [Fix 1] declarations: 1 updated (books_list template comment + app.py books_list doc comment, F-002), 0 confirmed, 1 none (F-001 tests only)
- [Build gate] PASSED (full, 377s) — 5834 passed, 9 skipped, 2 failed = exactly the main baseline (test_size_configuration_applied, test_batch_creation_form_renders)
- [Scope gate] cycle 2: in_scope (no new files since cycle 1)
- [Review 2/3] Score: 9.5 — crit: 0, imp: 0 (confirmation mode; F-001 ✓ resolved, F-002 ✓ resolved, F-003 dismissed Minor; new Minor F-006: lost-cover renders predate the F-002 hint)
- [Review sync] 1 report(s) → meta/review/ (20261002T173722Z-CARD-158-cycle2.yml)
- [Review 2/3] Step 8h coverage: 44/44 card rules have a verdict line (19 ✓, 25 ⚠ no_eligible_fact, 0 ✗; delta-clean rules carried from cycle 1); mutation check 9/9 killed
- [Review 2/3] Score: 9.5 ✓ threshold reached + no critical/important
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0019/R1, ADR-0032/R1, ADR-0032/R2) — note: ADR-0019/R1's 'delta adds only import re' is true of the fix delta; the whole card adds imports only under tests/
- [Renders] re-rendered all after-*.png at 20:39 on bc1281b + fix 1 (F-006): lost-cover rows now show the visible hint; /books 390/390, book pages 390/390 and 1440/1440 → ~/Documents/nonogram-reviews/CARD-158/
- [Docs] forge:readme over changed dirs (src/nonogram/admin, admin/static, admin/templates, tests): no structural or purpose change — admin dirs carry no README; tests/README.md is a Wave-1 guide that does not catalogue per-feature files; nothing to update
- [AC/EC check] All criteria/constraints ✓ (evidence) — with one ruling, stated: G-3 returned ⚠ partial because its second half (the owner looks at the pages) is a human act at done that no worktree change can produce; its in-pipeline half (current renders for the owner, card 'What to do' step 4 and the dispatcher's run facts) is demonstrated. G-3 is handed to the dispatcher as a pre-merge owner check, not counted as verified. No fix loop run for it (it cannot converge).
  AC-1 ✓ demonstrated — evidence: TestBookPages_OfferBothExportFiles 13 passed (test_offers_a_cover_download_that_submits_part_cover[detail]/[list], test_offers_an_interior_download[detail]/[list]); cover hidden fields == {part: cover}; Flask test-client rendering is the accepted evidence class (no e2e harness)
  AC-2 ✓ demonstrated — evidence: TestBookDetail_ListsPuzzlesByTitle 8 passed (test_each_member_is_labelled_by_its_puzzle_name, test_the_raw_id_is_not_the_visible_label)
  AC-3 ✓ demonstrated — evidence: TestBookDetail_ShowsTheStoredTrim 4 passed (test_shows_the_trim_print_setup_stored, test_a_book_with_no_print_spec_says_not_set_and_links_to_print_setup)
  G-1 ✓ demonstrated — no @app.route line, _export_part or PDF/export module in the diff; app.py changes are view data only; -k TestBookExport 31 passed; interior_cover + export_pdf + a4_golden 177 passed
  G-2 ✓ demonstrated — 0 hits for style=/hex/rgb(/hsl(/px|rem|em in added template/CSS lines; only new CSS .table-responsive{position:relative}; test_admin_design_tokens.py 6 passed
  G-3 ⚠ partial — 11 after-*.png renders (20:39:43–49) newer than the last source edit (20:36:10), both pages at 1440/390 incl. not-set and lost-cover; the owner's own check happens at done and is not verified here
- [Commit] success — card branch card/158-book-pages-show-contents: bc1281b (implementation), d0aa9ce (cycle-1 fixes; success commit). Explicit pathspecs; nothing under meta/ committed. vs 96bf6e8: 6 files +700/−16 (app.py +44/−1, admin.css +4/−0, book_detail.html +54/−12, books_list.html +17/−1, tests/test_book_detail_page.py +578 new, tests/test_books_list_plan_stats.py +3/−2 SCOPE+). Card stays review until done.
- [G-3] 2026-10-02 — ✓ owner confirmed: the owner reviewed the renders in ~/Documents/nonogram-reviews/CARD-158/ and approved the merge (answered to the dispatcher). Closes the gate's `G-3 ⚠ partial`, which the pipeline could not demonstrate itself.
- [Merged] 2026-10-02 — 66214c1 into main (--no-ff). Merge gate: rebase was a no-op (main still at 96bf6e8 = branch base), so the merged tree is the one that passed the post-fix full suite (only the 2 baseline failures); not re-run — the wave-30 smoke test runs the full suite on main at wave end. Deferral scan: 0 hits. Trace write-back: evidence tests appended to FR-043 (2) and FR-030 (1); statuses stay `partial` (CARD-159 still lists FR-030). F-004/F-005 captured to backlog.
