# CARD-121: The 4.8 mm floor at the book store — below-floor puzzles join only with a stored override, on every add route

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/121-book-floor-override
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-14 (membership half of FR-031; tile and finalise count are CARD-123)
**Idea:** —
**Wave:** 23
**Depends on:** CARD-115, CARD-120
**Touches:** src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, src/nonogram/admin/book_page_spec.py, src/nonogram/db/models.py, migrations/versions/012_book_floor_overrides.py, tests/test_book_floor.py, tests/property/test_book_membership_floor.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-09-23T01:25:42Z
**Closed:** 2026-09-23T03:10:36Z
**Actual:** 0.2d
**Merge commit:** 9b2cfb7
**Blocked by:** —

## What to implement

INV-006 is enforced **where membership is written**, so no add route can bypass it.

1. **Migration `012_book_floor_overrides.py`** (COMP-010) adds per-book override
   storage: the set of puzzle ids admitted below the floor. Use a mutation-tracked JSON
   column on `books` (CARD-101 precedent) or a small table; record the choice. Include
   a `downgrade`. Use the next free revision at implementation time, after CARD-120's
   and CARD-115's.
2. **`BookManager.add_puzzles_to_book(book_id, puzzle_ids, overrides=())`** computes
   each puzzle's cell with **CARD-115's `book_cell_mm(book_page_spec(book), …)`**, the
   same call the PDF makes (EC-021). A puzzle below 4.8 mm (TERM-024) is:
   - refused, with a message naming its cell against the floor ("4.61 mm against the
     4.8 mm floor"), when its id is not in `overrides`;
   - admitted, with the override **persisted for that id**, when it is.
   Refusal is per puzzle: the other puzzles in the same submission are still added
   (record the choice if a whole-batch refusal turns out to be simpler and the AC still
   holds). Both storage modes.
3. **Both routes** end in that method: `POST /book/<id>/select-puzzles` (selection
   step) and `POST /book/<id>/add-puzzles` (paste-IDs form on the detail page). The
   selection route passes a per-puzzle override flag (the tile control itself is
   CARD-123; a form field `override_<puzzle_id>` is enough here). The paste-IDs route
   admits no override today, so it refuses below-floor ids and names them.
4. Removing a puzzle removes its override (no orphan override for a non-member).
5. **The 4.8 mm floor is a named constant beside the plan/book code**, not an inline
   literal (e.g. `book_page_spec.FLOOR_MM`).

## Acceptance criteria

- **AC-183** (INV-006) — given the same Book 1 profile book and the same 4.61 mm puzzle, with no override given, when the puzzle is submitted from the selection step, then the puzzle is not added — the book's puzzle list is unchanged and the response names 4.61 mm against the 4.8 mm floor.
  *test:* `TestBookAddPuzzles_RefusesBelowFloorWithoutOverride`
- **AC-184** (INV-006) — given the same book and puzzle, submitted with an explicit override for that puzzle id, when the add is processed, then the puzzle becomes a member and the override is persisted for that puzzle id.
  *test:* `TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt`
- **AC-185** (INV-006) — given the same book and puzzle, with no override, when its id is pasted into the book detail page's add-puzzles form (POST /book/<id>/add-puzzles), then the puzzle is not added — the floor holds on the paste-IDs route too.
  *test:* `TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride`
- **AC-186** — given a Book 1 profile book holding a 30-wide x 20-tall puzzle whose row-clue gutter is 10 entries deep and column-clue gutter 8 deep (40 cells across, 4.84 mm), when it is submitted without an override, then the puzzle is added with no flag — 4.84 mm is at or above the floor.
  *test:* `TestBookAddPuzzles_AcceptsCellJustAboveFloor`

_(AC-182 names "a Book 1 profile book and a 30-wide x 25-tall puzzle whose row-clue gutter is 12 entries deep and column-clue gutter 8 deep (42 cells across, 4.61 mm on the trim)" — the fixture AC-183..185 say "the same … puzzle" about.)_

## Engineering constraints

- **EC-021** (consistency, INV-006) — For any puzzle, any stored trim and margins and every add route (selection step, paste-IDs form, any future route ending in the book store), a puzzle whose book cell is below 4.8 mm becomes a member only together with a stored override for its id; and the tile's cell, the add refusal and the finalise count all come from the one computation FR-030's PDF uses, so no two of them can disagree about a puzzle.
  *test:* `PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride` — _membership half here (every route, every trim); the tile and finalise-count agreement is added by CARD-123._

## Guardrails

- G-1: The admin panel fits no cells itself. The floor check calls `book_cell_mm`, never a local estimate (ADR-0036/R2; EC-021 "one computation").
- G-2: Out of scope: one puzzle in several books (ADR-0033). The single-valued `puzzles.book_id` rule and the assigned-puzzle exclusion stay as they are.
- G-3: Book assembly never changes a puzzle's grid, clues, tier or strategies. The only puzzle field written is `book_id` (ADR-0033/R1).
- G-4: The published-book refusal in `add_puzzles_to_book` stays as it is here. Turning it into a confirmation is CARD-131 (FR-038).
- G-5: Do not edit `src/nonogram/admin/book_pdf_generator.py`. It is owned by CARD-116 this wave.

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

- **FR:** FR-031
- **NFR:** NFR-008
- **ADR:** ADR-0036, ADR-0033
- **Components:** COMP-009, COMP-010, COMP-007 (consumed via CARD-115)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

### Add routes covered

Enumerated from the code (`grep -rn "add_puzzles_to_book" src/`) and **held to
that enumeration by a test**: `TestBookFloor_EveryAddRouteEndsInTheGuardedStore`
walks `app.py` with `ast`, attributes every call to `BookManager.add_puzzles_to_book`
to its *innermost* enclosing function, and fails if the set is not exactly the
two below — so a third route added later is noticed rather than assumed away.

1. `POST /book/<id>/select-puzzles` — `app.select_puzzles_for_book`. Passes the
   per-puzzle overrides this submission carries (`override_<puzzle_id>`, read by
   the new `_submitted_overrides`); the tile that renders the control is CARD-123.
2. `POST /book/<id>/add-puzzles` — `app.add_puzzles_to_book`. Passes no
   override (the route has no control for one, AC-185). **Both** posting
   templates are covered: `book_detail.html`'s paste-IDs form and
   `_puzzle_table.html`'s review modal (which sends `return_to`) — one test each.

No third caller exists. The floor is enforced in `BookManager`, not in either
route, so a future route ending in the store is covered whether or not it
remembers to report the refusal (EC-021).

### Override storage: a JSON column, not a table

`books.floor_overrides`, a nullable JSON column added by migration **012**
(chains onto 011; confirmed 012 was the next free revision), a flat list of
puzzle-id strings, `MutableList.as_mutable(JSON)` per the CARD-101 precedent.
It has no nesting, so MutableList is enough where MutableDict was not enough for
`distribution_plan` — and `BookManager` assigns a freshly built list whole
anyway (`_merged_overrides`), the way CARD-100 rebuilt `puzzle_ids`.

Why not a table: the override set belongs to exactly one book, is read and
written in the same breath as `puzzle_ids`, is bounded by the book's own puzzle
count (~150), and is never queried across books. A join table would buy
referential integrity it cannot use (`puzzle_ids` beside it is already a JSON
list of the same ids) at the cost of a second write path per add. No backfill —
NULL reads as "no override was ever given", the fail-closed reading.

### Per-puzzle refusal (not whole-batch)

As the card asks. A submission of fifty tiles with one small picture in it is a
corrected selection, not a lost one; whole-batch refusal would make the owner
find the offender by bisection. The selection step keeps the refused tiles
ticked and stays on the step, so the remedy is one tick away.

### Postures on what cannot be measured (fail-closed line)

Stated at length in `BookManager.below_floor`'s docstring. Summary:

* record whose cell computes → the verdict (`< FLOOR_MM` refuses; **at** the
  floor passes, AC-186 reads "at or above");
* record whose clues cannot be read → **refused** (fail closed), and an
  override still admits it, because the refusal is the floor's;
* book whose stored trim/margins cannot be read → **the whole add refused**,
  with `book_page_spec`'s message naming the column (fail closed);
* an id no row matches → *not* refused. A phantom id is not a puzzle: no grid,
  no clues, nothing to print. Whether a book's list holds ids no row matches is
  referential integrity (CARD-103's FK, CARD-100's repair), not the printed-cell
  floor; it is the same verdict `_selection_records` makes, and ADR-0035's gate
  still refuses such a book at the exit from draft;
* manager with no puzzle store → nothing resolvable, nothing refused, an
  **error logged**. `create_app` wires a store on both branches, so this is a
  wiring error; CARD-100 deliberately kept `BookManager(session_factory=None)`
  working ("says so rather than pretending") and the readiness gate already
  fails closed for it. Covered by a named test that states the decision.

### SCOPE+ (edits outside the card's `Touches:`)

* `SCOPE+ tests/test_book_ready_gate.py` — its in-memory `Shelf` stub wrote
  puzzle records with **no clue fields at all** (its DB branch always wrote
  `clues_rows=[[1]]`). With the floor measuring stored records, a clue-less
  record is now refused, which broke 36 tests (incl. `tests/property/
  test_book_ready_gate.py`, which imports `Shelf`). Fixed by giving the
  in-memory stub the same one-cell clue pair the DB branch already had — a
  record with no clues is a stub the store could never write (`add_puzzle`
  always writes them), not a state to weaken the floor for.
* `SCOPE+ tests/test_book_plan_storage.py` (TestMigration010) and
  `SCOPE+ tests/test_book_page_spec.py` (TestMigration011) — both read the
  *current* ORM against a database stopped at their own revision, so any new
  column breaks them. Each now runs `command.upgrade(config, "head")` before the
  ORM read; the legacy un-backfilled row they are about is still the row read
  back, and 011's test now exercises 012's `downgrade` on its way down to 010.

No template was changed (the tile control is CARD-123; the selection route
needs only the `override_<puzzle_id>` field). `book_pdf_generator.py` was not
touched (G-5). The published-book refusal is unchanged (G-4) and has a test.

### Tests

* `tests/test_book_floor.py` — 48 tests: AC-183/184/185/186 driven through the
  real POST routes with the Flask test client (no browser harness in this
  project), plus both storage modes at the store, the postures above, the
  guardrails, and two structural checks (no second `4.8` literal anywhere the
  floor is applied, read off the AST; the add-route enumeration).
* `tests/property/test_book_membership_floor.py` — EC-021, spelled the way this
  suite spells a property test (`test_PropertyTest_<name>` module functions,
  per `tests/property/test_book_export_interior.py`): 24 hand-built puzzles x
  16 stored print specifications x every route (store in both modes, selection
  step, paste-IDs form, and the paste-IDs form *after* another route stored an
  override), stdlib `random.Random` on a fixed seed, no `hypothesis`. Minimum
  case count asserted inside — and asserted **per verdict**, so a corpus in
  which nothing ever fell below the floor cannot pass vacuously.
* Mutation-checked: neutering the `cell_mm < FLOOR_MM` comparison fails all 5
  property tests and 21 AC tests.
* Both new files' `admin_app` fixtures put `book_manager._book_manager` and
  `image_manager._image_manager` back to an empty singleton on teardown. The
  existing panel fixtures set them up but never tear them down, and these two
  files make many books: left behind, they made
  `test_admin_review_actions.py::test_delete_works_without_a_database` fail in
  the full-suite order (a fresh in-memory store reuses `puzzle_000001`, which
  one of these books still claimed, and the delete route refuses a puzzle that
  is in a book). Contained to the new files — the existing fixtures were left
  alone (CARD-116 is in `app.py` this wave).

Full suite green, minus the one known pre-existing failure
(`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::
test_size_configuration_applied`), which was deselected.

### Handover to CARD-123

`BookManager.below_floor(book_id, puzzle_ids)` is the tile's and the finalise
count's computation, already written: it returns a `FloorRefusal` per
below-floor puzzle carrying `cell_mm`. `floor_refusals(...)` is the same minus
the ids an override covers. The tile will also want the cell of an *above*-floor
puzzle, which is `book_cell_mm(book_page_spec(book), ...)` directly — the same
call, so the three figures cannot disagree.

One limitation left for CARD-123: an override ticked on tab A and committed from
tab B is not carried (`_submitted_overrides` reads the submitted form only, which
is what the card sanctions). It fails safe — the puzzle is refused by name.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

- [Scope] migrations/versions/012_book_floor_overrides.py, src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/book_page_spec.py, src/nonogram/db/models.py, tests/property/test_book_membership_floor.py, tests/test_book_floor.py, tests/test_book_page_spec.py, tests/test_book_plan_storage.py, tests/test_book_ready_gate.py
- [Scope gate] ⚠ grown: 3 files outside Touches (tests/test_book_page_spec.py, tests/test_book_plan_storage.py, tests/test_book_ready_gate.py) — all declared SCOPE+ by the implementer as forced test-fixture repairs. No guardrail hit: book_pdf_generator.py (G-5) untouched.
- [Build gate] PASSED (full, 164s) — 3 failures in the run (tests/test_card_037_upload_retry.py::test_a_success_releases_the_token_and_deletes_the_file and two in tests/test_web_upload.py) are NOT this card's: all three glob the SHARED system temp dir for `nonogram-upload-*` and assert the global set is unchanged, so CARD-116's concurrent suite run in its own worktree makes them fail. All 21 tests in both files pass in isolation on this branch. The known pre-existing failure (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied) was deselected.
- [Visual] no Makefile run target and no ## Design context section — no browser harness in this project; review runs static-only. User-facing ACs (AC-183/184/185) are covered by Flask test-client tests driving the real POST routes.
- [System contract] fresh lens (system_rules.py --card CARD-121) returns the same 44 rule ids as the card's ## System contract section — no refresh needed.
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h checked all 44 card rules: 14 ✓ holds, 30 ⚠ unchecked (23 no_eligible_fact, 6 check_ref_missing), 0 ✗ violated. Coverage guard: PASS.
- [Adversarial] F-001 (floor verdict + published refusal decided outside the writing transaction, DB mode) CONFIRMED — independent skeptic re-derived it: get_book returns a value snapshot from a closed session (book_manager.py:501-505), the verdict is taken off it (:777-784), and the write re-fetches the row in a new session (:820-842) that never re-checks book_row.status; on main the published check lived inside the writing session (main:526-532 + commit :546), so it is a regression, not a pre-existing property. Werkzeug's dev server is threaded (app.py:2278, which is why _pending_selections_lock exists), so the window is reachable from two tabs.
- [Severity gate 1/3] Score 8.5 >= threshold 8 but 0 critical / 1 important finding — fix mandatory
- [Fix 1] declarations: 5 updated, 4 confirmed, 3 none. FIXED F-001..F-007, each with a DECLARATIONS line; no "matrix ... updated" claim to cross-check (this card has no ## Failure matrix). Fix pre-gate: all 28 named tests run and green (TestBookAddPuzzles_VerdictAndWriteAreOneDecision, TestMigration012, TestBookFloor_ALargeBucketPuzzleNeedsAnOverride, TestBookAddPuzzles_ReportsTheMeasurementItEnforced, TestBookFloor_EveryAddRouteEndsInTheGuardedStore, TestBookFloor_TheStorelessPostureIsReachable, TestBookAddPuzzles_ARepeatedIdIsOneDecision, PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride x3).
- [Fix 1] F-001's fix is a design change, declared as such: the store's add gained a second job (reporting the verdict it enforced, not only applying it), carried by a NEW sibling method `add_puzzles_reporting_refusals` returning a new `AddOutcome` rather than by overloading `add_puzzles_to_book`'s bool. The guard is `_verdict_state(book_row)` re-read INSIDE the writing session and compared with the snapshot the verdict was made on (status + the four print columns + floor_overrides; puzzle_ids deliberately excluded). Verified by revert: neutering only the guard fails all three F-001 tests with the finding's own symptom, while the no-false-refusal test stays green.
- [Build gate] PASSED (full, 170s) — exit 0, no failures at all this run. The three upload tests that failed the cycle-1 gate pass here, confirming they were shared-temp-dir cross-talk from the concurrent card and never this card's.
- [Scope gate] cycle 2: unchanged — same 3 SCOPE+ test files outside Touches, no new excess, no guardrail hit (book_pdf_generator.py still absent from the diff).
- [Review 2/3] Score: 9.0 ✓ threshold reached + no critical/important — crit: 0, imp: 1->0. All seven cycle-1 findings verified resolved by the reviewer.
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h checked all 44 card rules: 17 ✓ holds, 27 ⚠ unchecked (21 no_eligible_fact, 6 check_ref_missing), 0 ✗ violated. Coverage guard: PASS. 8f mutation and 8g static certification RUN on this cycle, not deferred — the reviewer killed 3 mutants (F-001 guard, submission de-dup, newly_overridden filter) and restored the files byte-identically.
- [Notes correction] The implementer's ## Worktree notes above predate the cycle-1 fix pass and are stale in three places: the add now has a second store entry point `add_puzzles_reporting_refusals` returning `AddOutcome` (`add_puzzles_to_book` is a one-line delegation to it, its bool/False-means-not-found contract unchanged); the AST route-enumeration guard matches a two-name STORE_ENTRIES set, not `add_puzzles_to_book` alone; and tests/test_book_floor.py holds ~80 tests, not 48. The design change itself is recorded in the [Fix 1] lines above.
- [8h spot-check] 3/3 sampled holds reproduced by independent skeptics (INV-006, ADR-0036/R1, ADR-0033/R1). INV-006: the two cited line ranges are the real single write point (every other puzzle_ids writer refuses to add), the property test's >=300 / >=40-per-verdict assertions are live (proved by raising them to 99999 and watching them fail) and green, and the cell_mm < FLOOR_MM mutant was killed (34 failures). ADR-0036/R1: no tripwire path in the name-only diff, status, or untracked/ignored set; all tripwire blobs hash-identical to main; both suites green (66 passed); FLOOR_MM unreachable from export/. ADR-0033/R1: the test diffs the whole puzzle record minus book_id in both storage modes, and the only puzzle_store call the diff adds is a read.
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-183 ✓ demonstrated — TestBookAddPuzzles_RefusesBelowFloorWithoutOverride, 7 passed; real POST /book/<id>/select-puzzles via test_client with the template's own form fields, asserting "4.61 mm" and "4.8 mm floor" in the returned HTML and the book's list unchanged.
  AC-184 ✓ demonstrated — TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, 11 passed; real POST with override_<puzzle_id>=on; override persistence pinned in both storage modes, DB mode re-read through a fresh BookManager.
  AC-185 ✓ demonstrated — TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, 5 passed; real POST /book/<id>/add-puzzles with the comma string book_detail.html actually submits; the _puzzle_table.html review-modal variant covered too.
  AC-186 ✓ demonstrated — TestBookAddPuzzles_AcceptsCellJustAboveFloor, 6 passed; 4.84 mm joins with no flag and no floor mention; the two fixtures pinned either side as cells[below] < FLOOR_MM <= cells[above].
  EC-021 ✓ demonstrated — PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, 5 passed; 24 puzzle shapes x 16 stored print specs x every route (both store modes, selection step, paste-IDs, paste-IDs after another route stored an override, plus removal); MIN_DECISIONS>=300 and MIN_OF_EACH_VERDICT>=40 per verdict kind asserted inside, plus the converse — cannot pass vacuously. Seeded random.Random, no hypothesis.
  G-1 ✓ demonstrated — re-verified after the fix restructure: _below_floor_for holds the only floor comparison in the tree, on book_cell_mm(book_page_spec(book), ...); app.py computes nothing. AST scan finds no second 4.8 literal.
  G-2 ✓ demonstrated — the assigned-puzzle exclusion lives in puzzle_review.py, absent from the diff; Puzzle.book_id unchanged; 183 tests across the membership/constraint suites pass unmodified.
  G-3 ✓ demonstrated — whole-record diff minus book_id, both storage modes; _mirror_onto_puzzles unchanged.
  G-4 ✓ demonstrated — pytest.raises(match="Cannot add puzzles to published book") in both modes; the check was moved earlier, not reworded or turned into a confirmation.
  G-5 ✓ demonstrated (structural) — book_pdf_generator.py absent from the name-only diff and from status incl. untracked; byte-identical to main.
  Evidence class note: no browser harness in this project, so the three user-facing ACs are verified by Flask test-client tests that drive the real routes with the templates' own field names and assert on the real response body — checked, not assumed. Test-file edits are pure additions (0 deleted lines across tests/), so no covering test was weakened, retargeted or deleted.
- [Docs] forge:readme skipped, with reason. Of this card's changed directories, only tests/ has a README.md; migrations/versions/, src/nonogram/admin/, src/nonogram/db/ and tests/property/ have none, so this project does not keep per-directory developer READMEs and creating them for this card would be scope growth, not docs maintenance. tests/README.md is titled "Admin Panel Test Suite - Wave 1" and enumerates a fixed wave-1 file list; it names no book test file and has been stale for roughly twenty waves, so editing it for CARD-121 alone would be an opportunistic drive-by on a document whose staleness this card did not cause. Out-of-scope observation for a later card: tests/README.md needs a rewrite, not a patch.
- [Commit] SUCCESS 8d32a5f fix(admin): CARD-121 decide the floor verdict inside the transaction that writes it — the review-fix pass, staged with explicit pathspecs (4 files), on top of 3bd9d1f. Two commits on the branch, nothing under meta/ committed, attribution line present. Card stays Status: review until the dispatcher merges.

- [Done] main unchanged since branch base 6dd667a; the card's second full-suite gate ran clean on this tree. Merged 9b2cfb7 (--no-ff). Deferral scan: 0 hits. SCOPE+ on 3 test files (judged necessary; no covering test weakened). Handovers pushed to CARD-123 and CARD-131.
