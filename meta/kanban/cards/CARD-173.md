# CARD-173: An unreadable stored print setup says so once, names the remedy, and offers no override that cannot work

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/173-unreadable-print-spec-remedy
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (IDEA-072, WSJF 2.33)
**Idea:** IDEA-072
**Wave:** 33
**Depends on:** —
**Touches:** src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_select_puzzles.html, src/nonogram/admin/templates/book_finalize.html, tests/test_book_select_floor_tiles.py, tests/test_book_floor.py
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-10-05T03:04:22Z
**Closed:** 2026-10-05T04:09:45Z
**Actual:** 0.1d
**Merge commit:** da0283f
**Blocked by:** —

## What to implement

A book's stored print setup (trim and margin columns) is read in one place:
`book_page_spec(book)` in `src/nonogram/admin/book_page_spec.py`. It raises
`ValueError` when a column is not a finite number, a trim is outside KDP's
bounds, a side margin is below the minimum, or the margins leave no width.
`print_specs.py` is NOT on this path: it only validates the Print setup form
before a save. The remedy for an unreadable stored setup is one save on
Print setup (`/book/<id>/setup-print`, endpoint `setup_print`), which writes
fresh, validated columns.

**Current behaviour (verified by reading the code):**

1. **Selection step, GET** (`app.py: select_puzzles_for_book`, line 3667).
   `_book_cells` (app.py ~3517) catches the `book_page_spec` error, logs one
   warning, and maps every tile's id to `None`. `_misses_the_floor(None)` is
   true, so every tile is in `below_floor_ids`. The template
   (`book_select_puzzles.html` ~229-238) then renders, on every tile,
   "Cell cannot be measured on this book." plus an "Include below floor"
   override checkbox. N tiles, N identical messages. Nothing names Print setup.
2. **Selection step, POST, and the paste-IDs form** (`app.py:
   add_puzzles_to_book`, line 4852). Both call
   `BookManager.add_puzzles_reporting_refusals`, which calls `_below_floor_for`
   (book_manager.py ~1009). It calls `book_page_spec(book)` at line 1047 with
   no catch, so the whole add raises `ValueError`. The routes flash
   `"Error: " + str(e)` (app.py 3814 and ~4892), i.e. the raw column message,
   for example "Error: book trim_width_cm must be a number of cm, not 'abc'".
   Ticking the override changes nothing: the raise comes before any override
   is read. So the override on every tile can never succeed. This fails
   closed (nothing is added), which is correct and must stay.
3. **Finalise** (`app.py` ~4434, `book_finalize.html` ~161-169). The trim row
   already says "Cannot be read — set it again on Print setup". But the
   below-floor alert also lists every member as "cell cannot be measured",
   one line per puzzle.

**Target behaviour:**

- One wording for this case, stated once in `book_manager.py` next to
  `NO_PLAN_REFUSAL` (a constant or a small function taking the reason). It
  says the book's print setup cannot be read, gives `book_page_spec`'s reason,
  says no puzzle's printed cell can be measured so nothing was added, and
  names the remedy: save the print settings again on Print setup.
- `_below_floor_for` catches the `book_page_spec` `ValueError` and re-raises a
  `ValueError` carrying that wording (`from` the original). Still fails closed:
  nothing is written. Both add routes keep their existing `except ValueError`
  and so flash it once.
- Selection step GET: when the book's print setup cannot be read, the route
  passes the reason to the template. The template shows ONE book-level alert
  with the wording and a link to Print setup (`url_for('setup_print', ...)`,
  as `book_detail.html:52` already does). Tiles show no per-tile flag note
  and no override checkbox in this case. The tile's "Book cell: not
  measurable" info row may stay.
- Finalise: when the print setup cannot be read, the below-floor alert shows
  one sentence (the same wording, or "cell sizes cannot be measured until the
  print setup is saved again on Print setup") instead of N per-member lines.
  The below-floor COUNT stays what it is today (every member counts as
  missing the floor). That is the fail-closed verdict.
- A puzzle whose own clues are unreadable (spec fine) keeps today's per-tile
  flag and per-puzzle refusal. That is a per-puzzle fault, not a book-level one.

## Acceptance criteria

- **AC-1:** Given a book whose stored `trim_width_cm` is "not a number" and a tab with 3 tiles, when the selection step renders, then the page holds exactly one print-setup alert that links to `/book/<id>/setup-print`, and no tile carries a flag note or an `override_<id>` checkbox.
  *test: TestBookSelect_UnreadablePrintSetupIsOneBookLevelMessage (in tests/test_book_select_floor_tiles.py)*
- **AC-2:** Given the same book, when 2 puzzles are submitted from the selection step (with and without an override ticked), then nothing is added, the book's puzzle list is unchanged, and exactly one error flash is shown that names Print setup.
  *test: TestBookAddPuzzles_UnreadablePrintSetupRefusesOnceAndNamesTheRemedy (in tests/test_book_floor.py)*
- **AC-3:** Given the same book, when ids are pasted into the detail page's add form, then nothing is added and the one flash names Print setup.
  *test: TestBookAddPuzzlesByIds_UnreadablePrintSetupNamesTheRemedy (in tests/test_book_floor.py)*
- **AC-4:** Given the same book, when `BookManager.add_puzzles_reporting_refusals` is called directly, then it raises `ValueError` whose message names Print setup and still contains `book_page_spec`'s reason (asserted by the column name only, not the full text), and nothing is written.
  *test: TestBookAddPuzzles_UnreadablePrintSetupRefusesOnceAndNamesTheRemedy (in tests/test_book_floor.py)*
- **AC-5:** Given a book holding 3 members whose print setup cannot be read, when Finalise renders, then the below-floor count is still 3 and the alert carries one print-setup sentence, not 3 "cell cannot be measured" lines.
  *test: TestBookFinalize_UnreadablePrintSetupCollapsesTheBelowFloorList (in tests/test_book_select_floor_tiles.py)*
- **AC-6:** Given the AC-1 book, when the trim is saved again with valid values (via `retrim`), then the selection step shows each tile's cell in mm and no print-setup alert (the remedy the message names really works).
  *test: TestBookSelect_UnreadablePrintSetupIsOneBookLevelMessage (in tests/test_book_select_floor_tiles.py)*

## Guardrails

- G-1: Still fails closed. An unreadable print setup never lets a puzzle join a book, on any route (INV-006, EC-021). `PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride` stays green.
- G-2: `_misses_the_floor` stays the only place on the admin side that compares a cell against `FLOOR_MM`. No template compares a number (CARD-123 G-1).
- G-3: The unreadable-clues posture is unchanged: `test_an_unreadable_clue_set_is_flagged_rather_than_shown_as_a_number`, `test_the_finalise_count_holds_the_same_posture` and `test_a_stored_puzzle_with_unreadable_clues_is_refused` stay green as they are.
- G-4: Do not change `book_page_spec.py`'s or `print_specs.py`'s refusal messages. CARD-174 owns trim-refusal wording. Tests here must not pin the reason text, only the remedy and the column name.
- G-5: No change to book PDF output, layout, or the Finalise page counts (CARD-153 counts, CARD-129 KDP gutter check). ADR-0036/R1's A4 golden stays green.
- G-6: The no-store posture of `_below_floor_for` (logs, refuses nothing, never raises; review cycle 1 F-005) is unchanged: the store check still precedes the sheet.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-173` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-031 (AC-182..AC-188; tile flag, add refusal, finalise count), EC-021 (one computation, every add route), NFR-008 (4.8 mm floor)
- **Invariant:** INV-006 (below floor only with a stored override)
- **ADR:** ADR-0036/R2 (book geometry only through COMP-007's layout via `book_page_spec`), ADR-0019/R1 (adapter holds HTTP concerns only)
- **Components:** COMP-009 (Admin Panel)
- **Trace:** meta/architecture/trace.yml (FR-031 rows); no new FR or AC id, card-local ACs only

## Design context

- **Screens:** book selection step (`/book/<id>/select-puzzles`), book detail paste-IDs flash, Finalise below-floor alert. Admin UI only; no print output changes, so no renders.
- Reuse the existing alert style and Print setup link wording ("set it again on Print setup", as `book_finalize.html:138` and `book_detail.html:52` do).

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-072 "Unreadable stored print spec: name the remedy" (WSJF 2.33).
- [Fact] The stored spec is read by `book_page_spec` (book_page_spec.py:346), not by print_specs.py. The idea's text names print_specs.py; that file only validates form input.
- [Fact] Store raise point: book_manager.py:1047 (`spec = book_page_spec(book)` in `_below_floor_for`). `add_puzzles_reporting_refusals` docstring (~1238) already documents the raise; update it to the new wording.
- [Fact] Screen degrade: app.py `_book_cells` ~3517-3550 maps every id to `None`; `_trim_cm` (~3552) uses the same try and can be the model for a small "reason or None" helper.
- [Fact] Existing test `test_a_book_whose_trim_cannot_be_read_shows_no_cell_at_all` (tests/test_book_select_floor_tiles.py ~506) asserts "not measurable" in the tile. It stays green if the info row is kept. `retrim(...)` in that file sets stored columns.
- [Overlap] CARD-174 edits trim-refusal wording (print_specs.py `validate_trim_size`, possibly book_page_spec.py's "outside KDP's" message). This card touches neither file; it only wraps `book_page_spec`'s message. If CARD-174 merges first, no conflict; AC tests pin the column name, not the text.
- [Env] forge 2026.8.17
- [System contract] fresh assembly (system_rules.py --card CARD-173) matches the card section: 52 rules, no change.
- [Implemented] `book_manager.py`: `unreadable_print_setup_refusal(reason)` next to `NO_PLAN_REFUSAL` — one sentence carrying `book_page_spec`'s reason and naming Print setup. `_below_floor_for` catches exactly `ValueError` from `book_page_spec(book)` and re-raises `ValueError(unreadable_print_setup_refusal(...)) from` it; still before any store read/write, still after the no-store posture (G-6). `below_floor` / `add_puzzles_reporting_refusals` docstrings updated to the new wording.
- [Implemented] `app.py`: `_unreadable_print_setup(book)` ("reason or None", modelled on `_trim_cm`). Selection step passes `print_setup_unreadable` (the wording, or None) into the context; Finalise passes a boolean `print_setup_unreadable`. `_book_cells`, `_below_floor_ids`, `_misses_the_floor` and the below-floor count are unchanged (G-1, G-2, fail-closed count).
- [Implemented] `book_select_puzzles.html`: one `alert-warning` marked `data-print-setup-unreadable` with the wording and a `url_for('setup_print', ...)` link; the tile flag block is now `{% if below_floor and not print_setup_unreadable %}` (the "Book cell: not measurable" info row and `data-below-floor` stay). `book_finalize.html`: inside the existing below-floor alert, one sentence ("Cell sizes cannot be measured until the print setup is saved again on Print setup", linked) replaces the per-member list when the setup is unreadable.
- [Wording] The sentence says "nothing can be added to it" rather than "nothing was added", so the one wording reads true both as the add refusal (flash) and as the selection step's GET alert, which is shown before anything is submitted.
- [AC→test] AC-1, AC-6 → `TestBookSelect_UnreadablePrintSetupIsOneBookLevelMessage` (tests/test_book_select_floor_tiles.py; also checks an unreadable-clues puzzle on a readable book keeps its per-tile flag and override). AC-5 → `TestBookFinalize_UnreadablePrintSetupCollapsesTheBelowFloorList` (same file). AC-2, AC-4 → `TestBookAddPuzzles_UnreadablePrintSetupRefusesOnceAndNamesTheRemedy` (tests/test_book_floor.py; selection POST with/without overrides; store call parametrised memory + sqlite db, with/without overrides; asserts `__cause__` is the original ValueError, membership and overrides unchanged). AC-3 → `TestBookAddPuzzlesByIds_UnreadablePrintSetupNamesTheRemedy` (same file). Tests assert only the column name `trim_width_cm` and "Print setup", never `book_page_spec`'s reason text (G-4).
- [Mutants] (scratchpad card173_mutants.py; all KILLED, all reverted): M1 store re-raises raw error → AddPuzzles (selection + store) and AddPuzzlesByIds; M2 `from` dropped → AddPuzzles store test (`__cause__`); M3 helper always None → SelectBookLevel (3 tests) + Finalize alert; M4 select alert context always None → SelectBookLevel (3); M5 finalize flag inverted → Finalize alert; M6 finalize flag False → Finalize alert; M7 tile guard dropped → SelectBookLevel no-flag test; M8 select alert unconditional → SelectBookLevel per-puzzle + remedy tests; M9 alert link removed → SelectBookLevel one-alert test; M10 finalize collapse condition false → Finalize alert. Every new class is killed by at least one mutant.
- [Tests run] tests/test_book_select_floor_tiles.py + tests/test_book_floor.py: 118 passed. Related set (22 files incl. property/test_book_membership_floor.py [INV-006 property], test_export_a4_golden.py, test_layout_page_spec.py [ADR-0036/R1], test_book_finalise_*.py, test_book_select_tabs.py, test_book_detail_page.py, test_book_page_spec.py, test_cli.py import guard): 1341 passed. G-3's three named tests unchanged and green.
- [Scope] No SCOPE+; only the six Touches files changed. book_page_spec.py / print_specs.py untouched (G-4); no PDF code touched (G-5).
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/templates/book_finalize.html, src/nonogram/admin/templates/book_select_puzzles.html, tests/test_book_floor.py, tests/test_book_select_floor_tiles.py
- [Build gate] impact underivable (test_scope: full, no pytest-testmon) — full suite
- [Build gate] PASSED (full, 608s; 6190 passed, 9 skipped)
- [Scope gate] in_scope — 6 changed files, all inside Touches; no guarded-path hits
- [Visual] review.visual off — Step 8g static check only
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1 (pre-adversarial; F-001 test cannot tell card wording from raw reason, mutant R1 survived)
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h covered all 52 card rules (9 ✓, 43 ⚠ no_eligible_fact, 0 ✗)
- [Adversarial] F-001 CONFIRMED — skeptic re-ran mutant (raw reason in place of unreadable_print_setup_refusal at app.py:3906): 118 passed; contract gap vs objective + docstring
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Fix cycle 1, F-001] Test-only: `test_the_page_holds_exactly_one_alert_linking_print_setup` now also asserts the alert text contains `unreadable_print_setup_refusal(str(e))`, `e` being the ValueError `book_page_spec` raises for that book — the card's wording around the reason, with the reason taken from `book_page_spec` itself, so its text is still never pinned (G-4). No production code changed; no declaration changed (the `unreadable_print_setup_refusal` docstring claim is now demonstrated, not altered).
- [Fix cycle 1, revert check] Mutant R1 (app.py select context passes raw `unreadable` instead of `unreadable_print_setup_refusal(unreadable)`) applied: the strengthened test FAILED. app.py restored byte-for-byte from a scratchpad copy; `git diff src/` empty. Both card test files green afterwards.
- [Fix cycle 1, F-002 accepted] Refused selection POST shows the sentence twice (error flash + book-level alert on the re-rendered page): accepted — the flash reports the refused submission, the alert describes the book's state; AC-2's one-flash holds; changing it would add an untested branch.
- [Fix 1] pre-gate: FIXED F-001 named test passed (1 passed); SKIPPED F-002 (orchestrator-accepted, no behaviour change)
- [Fix 1] declarations: 0 updated, 0 confirmed, 1 none
- [Build gate] PASSED (full, 592s; 6190 passed, 9 skipped) after fix 1
- [Scope gate] cycle 2 in_scope — fix delta: tests/test_book_select_floor_tiles.py only
- [Review 2/3] Score: 9.5 — crit: 0, imp: 0 (confirmation mode; F-001 resolved, R1 now killed; F-002 dismissal upheld)
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h covered all 52 card rules (all carried, delta-clean)
- [Review 2/3] Score: 9.5 ✓ threshold reached + no critical/important
- [8h spot-check] skipped — pool empty: every cycle-2 holds line is carried(cycle 1, delta-clean)
- [Mutation] cycle 2: 10 killed, 0 survived (cycle 1: 9/10, R1 survivor fixed by F-001)
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-1 ✓ demonstrated (one alert + setup-print href + card wording; no flag-note/override on 3 tiles) · AC-2 ✓ demonstrated (selection POST no-override/override: membership unchanged, 0 overrides, 1 flash) · AC-3 ✓ demonstrated (paste-ids: nothing added, 1 flash naming Print setup) · AC-4 ✓ demonstrated (store raises, memory+db x override 4/4, column name only, __cause__ set, nothing written) · AC-5 ✓ demonstrated (count 3, one linked sentence, no per-member lines) · AC-6 ✓ demonstrated (retrim → mm cells, alert gone) · G-1 ✓ demonstrated (PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride 7/7, test untouched) · G-2 ✓ demonstrated (bounded grep: no new FLOOR_MM comparison in src/templates) · G-3 ✓ demonstrated (3 named tests green, unchanged) · G-4 ✓ demonstrated (book_page_spec.py/print_specs.py untouched; no reason text pinned) · G-5 ✓ demonstrated (A4 golden 63 + layout + finalise gutter/guide 110 green) · G-6 ✓ demonstrated (no-store posture tests green, store check precedes sheet)
- [Docs] forge:readme skipped — src/nonogram/admin/ and templates/ carry no per-directory README (owner decision pending in backlog); tests/README.md current (no new test file)
- [Commit] success commit 6257093 (on top of implementation 2988199); branch diff vs merge-base cf119ca: 6 files, +266/−7
- DESIGN-REGISTER: PuzzleTile — state: book print setup unreadable (no flag-note, no override; one book-level alert-warning above the tabs, linking Print setup) (CARD-173)
- [Out-of-scope] card objective says "nothing was added"; the shipped wording says "nothing can be added to it" so one sentence reads true on both the GET alert and the POST flash (reviewer cycle 1 accepted, no finding)
- [Merge gate] rebased onto ae2529f; full suite 6199 passed, 9 skipped, exit 0 (600s, under the lock). Merged da0283f.
- [Design] DESIGN-REGISTER applied to meta/design/components.md (PuzzleTile state).
