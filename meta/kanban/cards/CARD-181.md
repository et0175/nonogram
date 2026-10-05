# CARD-181: A batch remembers the tier it asked for, and its pages show it

**Status:** ready
**Priority:** P3
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/181-batch-requested-tier
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-05 (IDEA-073, WSJF 1.67; CARD-138 worktree note "For the owner / a later card")
**Idea:** IDEA-073
**Wave:** 34
**Depends on:** —
**Touches:** migrations/versions/014_batch_requested_tier.py, src/nonogram/db/models.py, src/nonogram/admin/batch_generator.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/batches_list.html, src/nonogram/admin/templates/batch_puzzles.html, src/nonogram/admin/templates/batch_status.html, tests/test_batch_requested_tier.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).** CARD-138 let a random batch ask
for a tier. The tier is used, then forgotten:

- `src/nonogram/admin/batch_generator.py:create_batch` (line 186) resolves the tier
  through `difficulty.parse_tier` into `requested_tier` (lines 260-264). It passes it
  as an argument to `_generate_random_batch` and stores it nowhere.
- Memory mode: the `BatchJob` built at lines 271-279 has no tier field
  (`BatchJob` dataclass, lines 82-98).
- DB mode: the `Batch` row built at lines 303-313 has no tier field.
  `src/nonogram/db/models.py:Batch` (line 25) has no column for it. The comment at
  lines 316-319 says so: "the row has no column for it".
- Readers: `get_batch_status` (BatchJob at lines 699-712) and `list_batches`
  (BatchJob at lines 768-781) copy row fields one by one. Neither has a tier.
- Pages: `batches_list.html`, `batch_puzzles.html` (`/batches/<id>`) and
  `batch_status.html` (`/batch/<id>`) show source, sizes and counts. None says what
  tier a batch aimed at. Only the shortfall note (in `error_message`) names the tier,
  and only when the batch fell short.

**Target behaviour.**

1. **Migration 014** — new file `migrations/versions/014_batch_requested_tier.py`,
   `revision = '014'`, `down_revision = '013'`. It adds one nullable string column,
   `batches.requested_tier`. No server default and no backfill: every existing row
   stays NULL. Use `op.batch_alter_table('batches')` like 004-013. `downgrade()` drops
   the column and touches nothing else. Follow 013's docstring style: say why a
   column, why NULL for old rows, and what rolling back costs (only the recorded tiers
   are lost; no puzzle changes).
2. **Model** — `Batch.requested_tier = Column(String, nullable=True)` in
   `src/nonogram/db/models.py`.
3. **Write at creation** — in `create_batch`, store the canonical value
   (`parse_tier(...).value`, i.e. the `requested_tier` variable that already exists)
   on both the memory-mode `BatchJob` and the DB-mode `Batch` row.
   - Untargeted batch (the form's "Any"): store `None`.
   - Image batch (`source="images"`): store `None`, even if a tier was passed.
     Image mode ignores the tier (CARD-138 out of scope), so recording one would be
     a claim the batch never acted on.
   - Rewrite the comment at lines 316-319: the tier is now also stored on the row.
     It still travels to `_generate_random_batch` as an argument — do not change that.
4. **Read back** — add `requested_tier: Optional[str] = None` to `BatchJob`, and
   copy `batch.requested_tier` in both DB readers (`get_batch_status`,
   `list_batches`).
5. **Show it** — register a Jinja filter in `src/nonogram/admin/app.py`, next to
   `strategy_label` (around line 1335), that turns a stored value into its display
   label: `difficulty.tier_of_record(value)`, then `.label`; `None` or an unknown value
   gives `None`. Templates use only this filter, so no template spells
   easy/medium/hard itself.
   - `batches_list.html`: a new column "Tier asked", right after "Source" (lines
     50 and 69). It shows the label, or `—` when nothing is stored.
   - `batch_puzzles.html` lede (line 16): append ", asked for Medium" after the
     sizes when a tier is stored. Say nothing when none is stored.
   - `batch_status.html` key/value list (lines 41-44): add a row "Tier asked" with
     the label, or `—`.
   - Plain text, not the `_tier.html` badge: the badge colours a puzzle's *graded*
     tier, and a request is not a grade.

**NULL means "no tier recorded".** A NULL row is either an untargeted batch or a batch
made before this migration. That includes targeted batches made since CARD-138, and
they cannot be told apart. So the pages show `—`, never "Any". "Any" would be false
for those older targeted batches.

Out of scope: retrying a batch with the same tier, filtering the batch list by tier,
and image-mode targeting.

## Acceptance criteria

- **AC-1:** Given memory mode (no session factory), when a random batch is created with `difficulty_tier="MEDIUM"`, then `get_batch_status(id).requested_tier == "medium"` and the same job in `list_batches()` carries `"medium"`.
  *test: TestBatchRequestedTier_MemoryModeRecordsTheTier (in tests/test_batch_requested_tier.py)*
- **AC-2:** Given DB mode over `tests/helpers/db.py:sqlite_session_scope`, when a random batch is created with `difficulty_tier="Hard"`, then the `batches` row read back in a new session holds `"hard"`, and both `get_batch_status` and `list_batches` return `requested_tier == "hard"`.
  *test: TestBatchRequestedTier_DbModeStoresAndReadsBackTheTier (in tests/test_batch_requested_tier.py)*
- **AC-3:** Given either mode, when a random batch is created with no tier, or an image batch is created with or without a tier, then `requested_tier` is `None` in the returned job and (DB mode) NULL in the row.
  *test: TestBatchRequestedTier_UntargetedAndImageBatchesStoreNull (in tests/test_batch_requested_tier.py)*
- **AC-4:** Given a tmp SQLite database built in today's shape, with `batches.requested_tier` dropped, one batch row inserted and the database stamped at 013, when `command.upgrade(..., "014")` runs, then the column exists, is nullable, and the old row reads NULL. When `command.downgrade(..., "013")` runs, the column is gone and the old row and its other columns are unchanged. A second upgrade to 014 succeeds (up, down, up).
  *test: TestBatchRequestedTier_Migration014IsReversible (in tests/test_batch_requested_tier.py)*
- **AC-5:** Given one batch stored with `"medium"` and one with NULL, when `/batches`, `/batches/<id>` and `/batch/<id>` are rendered, then the targeted batch shows "Medium" on all three pages. The NULL batch shows `—` in the list and on `/batch/<id>`, and `/batches/<id>` has no "asked for" phrase. No page shows "Any" for the NULL batch.
  *test: TestBatchRequestedTier_PagesShowWhatTheBatchAskedFor (in tests/test_batch_requested_tier.py)*
- **AC-6:** Migration 014 runs on Postgres `nonogram_test` only. The session fixture's `alembic upgrade head` (tests/conftest.py:_test_database_tables) reaches 014 there, and `tests/test_card_156_db_fixture.py`'s head check still passes. A manual round trip on `nonogram_test` (upgrade head, downgrade 013, upgrade head) is recorded in Worktree notes with its output. No command ever targets `nonogram_poc`, Render, or `nonogram_admin.db`.
  *test: review-lens (Worktree notes evidence + tests/test_card_156_db_fixture.py)*

## Guardrails

- G-1: CARD-138's generation behaviour is unchanged. The tier still reaches `_generate_random_batch` as an argument. Every batch note (shortfall, clock, refusal) stays byte-identical. `tests/test_batch_difficulty_target.py` passes unedited.
- G-2: Migrations 001-013 are not edited. The 011→013 chain test in `tests/test_book_floor.py` and `TestBookInk_Migration013BackfillsEveryExistingBook` in `tests/test_book_pdf_ink_mode.py` pass unedited.
- G-3: Never run alembic, or any SQL, against a database whose name lacks `_test`. That means no `nonogram_poc`, no Render URL, and no writes to `nonogram_admin.db`. `nonogram_admin.db` is already dirty in the main checkout; never stage it. The card ships the migration file only. The owner applies it (see Worktree notes).
- G-4: ADR-0031/R1 holds. The only tier vocabulary is COMP-006's (`parse_tier` on the way in, `tier_of_record`/`Tier.label` on the way out). No easy/medium/hard mapping is written in batch_generator, app.py or the templates. No score is compared to a cutoff (the AST guard in `tests/test_difficulty_tiers.py`).
- G-5: `_tier.html` and the tier hues stay unchanged (`tests/test_admin_tier_surfaces.py`).
- G-6: The image-batch flow (`/batch/generate-puzzles`, app.py around line 1774) does not change, beyond its batch now storing NULL.
- G-7: No new runtime dependency (ADR-0006/R1).

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-181` (55 rules). A projection — fix the source artifact, never this list._

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
- ADR-0031/R1 — Tier has exactly three members — easy, medium, hard — and every one has a score band. classify takes the score alone; no module derives a tier from branch_nodes. (check: test: TestTiers_ThreeBandsAndNoFourthTier)
- ADR-0031/R2 — A solve that branched is reported as the `guess` strategy (solver.STRATEGY_GUESS) in FR-029's strategies list, never as a tier. (check: test: TestTiers_BranchingIsAStrategyNotATier)
- ADR-0031/R3 — A stored difficulty_tier of "guess" reads back as Tier.HARD and is never rewritten by this decision; no migration runs and no production database is touched. (check: test: TestTiers_LegacyGuessRowReadsAsHard)
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

- **FR:** FR-008 (the requested tier). No FR covers the batch history pages. The column is a storage detail of CARD-138's feature.
- **ADR:** ADR-0031 (three tiers; R1 one vocabulary), ADR-0032 (admin storage guarantees; puzzle writes untouched here), ADR-0006 (dependency baseline)
- **Components:** COMP-009 (admin panel: batch_generator, app, templates), with its storage in src/nonogram/db/
- **Trace:** meta/architecture/trace.yml (COMP-009 rows; no new FR row)

## Design context

- **Screens:** `/batches` (new "Tier asked" column after Source), `/batches/<id>` (lede gains ", asked for <Tier>"), `/batch/<id>` (new "Tier asked" row in the Created/Updated list).
- **Owner-visible defaults chosen by this card:** the column header "Tier asked"; the lede wording "asked for Medium"; `—` for NULL (never "Any", because NULL also covers targeted batches made before 014); plain text rather than a tier badge.
- **Renders:** ~/Documents/nonogram-reviews/CARD-181/ (owner visual check before merge). Include screenshots of `/batches` with one targeted and one NULL batch, plus both detail pages for the targeted batch, rendered from the app on `nonogram_test` or memory mode, never `nonogram_poc`.

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-073 "Store a targeted batch's requested tier (column+migration)", from CARD-138's worktree note ("`batches` has no column and this card writes no migration … that is a column + migration decision, not an oversight here").
- [Facts] The migration tool is Alembic: `alembic.ini` at the repo root, `script_location = migrations`, revisions in `migrations/versions/` named `NNN_*.py` with string ids. The head on 2026-10-05 is `013` (`013_book_interior_ink_mode.py`, revises `012`). Before writing the file, run `alembic heads` in the worktree. If another wave-34 card has taken `014`, use the next free number and rebase `down_revision`. `migrations/**` and `src/nonogram/db/**` are conflict hotspots.
- [Facts] Test pattern to copy for AC-4: `tests/test_book_pdf_ink_mode.py:TestBookInk_Migration013BackfillsEveryExistingBook` (lines 642-770). It builds a tmp SQLite with `Base.metadata.create_all`, drops the new column, inserts a row, stamps the previous revision, and drives `alembic.command` with a `Config` whose `script_location` points at `migrations/`. Use `DROP COLUMN requested_tier` on `batches` and stamp `013`.
- [Facts] Batch rows reference no puzzles in the AC-4 fixture, so no FK work is needed. AC-2/AC-3 use `tests/helpers/db.py:sqlite_session_scope` (runs without a server). DB-mode `db_session` tests skip silently when `nonogram_test` is missing, so they do not count as evidence on their own.
- [Facts] AC-1 to AC-3 test recording, not generation. Monkeypatching `BatchGenerator._generate_random_batch` to a no-op is fine. `tests/test_batch_difficulty_target.py` shows the store-stub pattern if a real call is wanted.
- [Facts] Readers copy fields by hand: `get_batch_status` lines 699-712 and `list_batches` lines 768-781. Both need the new field. `_update_batch_status` (lines 146-184) whitelists the fields it writes and needs no change, because the tier is written once at creation.
- [Facts] Today's pages render `job.source`/`job.sizes` with no tier: batches_list.html lines 50 and 69, batch_puzzles.html line 16, batch_status.html lines 41-44. Display labels come from `difficulty.Tier.label` (difficulty.py:280) through `tier_of_record` (difficulty.py:516), which is total and never raises.
- [Order matters for the owner] The ORM model gains a column, so code from this card SELECTs `batches.requested_tier`. Running it against a database still at 013 returns a 500 on every batch page. **Apply the migration before running or deploying this code.**
- [For the owner: applying 014] Local panel (`nonogram_poc`): back up first with Postgres.app's pg_dump (Homebrew's v15 writes a 0-byte file against the v18 server):
  `PGPASSWORD=postgres /Applications/Postgres.app/Contents/Versions/18/bin/pg_dump -h localhost -p 5432 -U postgres -Fc -f ~/Documents/nonogram-reviews/nonogram_poc.bak.dump nonogram_poc`
  then `DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc" ./.venv/bin/alembic upgrade head`. Check with `alembic current`, which should print `014 (head)`.
  Render: `docs/deploy/render.md` marks "Migrations on deploy" as TODO(owner), because the service is dashboard-managed and `render.yaml` is ignored. After deploying, check read-only with `DATABASE_URL="<render external URL>" ./.venv/bin/alembic current`. If it is not at 014, run `alembic upgrade head` with that URL yourself.
  Rollback: `alembic downgrade 013` drops only the column. Recorded tiers are lost, and no puzzle or batch row is otherwise touched. Roll the code back first, or the pages 500 on the missing column.
- [AC cross-check] All ACs were re-read against the body. AC-3's image-batch-stores-NULL rule and AC-5's `—`-not-"Any" rule match target items 3 and 5. No change was needed.
