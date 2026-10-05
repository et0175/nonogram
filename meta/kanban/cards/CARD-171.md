# CARD-171: Finalise names a page-plan error on screen, and logs every other error it flashes

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/171-finalise-errors-named-and-logged
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (CARD-153 review findings F-006, F-010; F-009 closes with F-006)
**Idea:** IDEA-041, IDEA-040
**Wave:** 33
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, tests/test_book_finalise_gutter.py
**Review score:** 10.0 (cycle 2/3)
**Started:** 2026-10-04T16:19:11Z
**Closed:** 2026-10-05T03:04:10Z
**Actual:** 1.3d
**Merge commit:** 7713c65
**Blocked by:** —

## What to implement

Two gaps in the Finalise route, `finalize_book` (`src/nonogram/admin/app.py:4247`).
Both were left open by CARD-153 as out of scope.

**1. GET Finalise does not name a page-plan error (IDEA-041, CARD-153 F-006).**

Current behaviour (read on main 2e071b4):
- The GET half calls `_interior_counts(book, puzzles_in_book)` (~:4405) with no `try`.
- When the page plan fails (a plan tripwire from `interior_stream`), `_interior_counts`
  (:867) logs it with `log.exception`, stamps it (`_PLAN_FAILURE_LOGGED`, :978) and re-raises.
- Nothing on GET answers it. Flask turns it into a 500, and the global handler
  `server_error` (:5473) renders `500.html` with `error=str(e)`. `e` is Flask's
  `InternalServerError` wrapper, so the screen shows Flask's generic text, not the tripwire.
- Flask also logs it a second time ("Exception on /book/<id>/finalize [GET]"):
  two ERROR records for one failure (CARD-153 F-009).
- POST `save_and_finish` already does it right (~:4318-4336): it checks
  `_is_a_logged_plan_failure`, renders `500.html` itself naming the error, and
  re-raises anything not stamped.

Target behaviour:
- GET answers the stamped plan failure the same way POST does: status 500, `500.html`,
  the message says the page plan could not be built and includes the exception's text.
- It is logged once (by the helper only).
- Any exception that is NOT stamped is re-raised unchanged, so it takes the global
  handler and Flask's own log, as today.
- Keep the wording in one place, so GET and POST cannot drift. A small shared helper
  that builds the error page is fine. GET's text must not say "its status is not
  changed" unless that is true on GET (it is: GET changes nothing).
- **Do not change the global 500 handler.** F-006's suggestion
  (`getattr(e, "original_exception", e)` in `server_error`) would put the text of
  every unhandled exception, on every route, on screen. The panel is deployed at a
  public hostname behind a credential (ADR-0030, CON-016). A database driver's
  error can name hosts, users and connection details. The page-plan failure is
  the exporter's own text (tripwire wording, puzzle ids), so naming only that one
  is safe.

**2. The outer `except Exception` on POST only flashes (IDEA-040, CARD-153 F-010).**

Current behaviour:
- The POST block's outer handler (`except Exception as e: flash(f"Error: {str(e)}", "error")`,
  ~:4357) writes no log line.
- A transient error (it clears before the page re-renders) on any POST action
  (`clear_cover`, `save_and_finish`, `download_pdf`) ends as a flash only: 200,
  zero log records. CARD-153's cycle-3 probe confirmed it (constructor `TypeError`
  raised once → flash "Error: transient", status draft, no log).
- An error that persists is logged today only by accident: the re-render hits it
  again and Flask logs that.

Target behaviour:
- **Keep the outer handler** (owner rule: the outer try/except is intentional;
  add logging, don't remove it). Keep the flash text as it is.
- Before flashing, log the exception with its traceback on the panel's logger
  (`logging.getLogger(__name__)`, which is `app.logger`'s name, "nonogram.admin.app").
- The plan gate's refusal is NOT an error and must not be logged at ERROR. It is a
  `ValueError` raised by `book_mgr._refuse_unless_the_planned_book(...)` (~:4346)
  or `book_mgr.set_book_status(...)` inside `save_and_finish`, and its message is
  the refusal the owner reads (`test_book_ready_gate.py::test_the_finalize_route_flashes_it`).
  Tell it apart without reading message text, e.g. catch the gate's `ValueError`
  at those two calls and flash it there, or mark it. Implementer's choice.
- The stamped plan failure already returns before the outer handler. It must stay
  logged once, not twice.
- `download_pdf` goes through `generate_book_pdf_download` (:4653), whose own
  `except Exception` (:4669) also flashes only. Add the same log line there
  (it serves `/book/<id>/download-pdf` too). Keep its flash and redirect.

## Acceptance criteria

- **AC-1:** *Given* a book whose page plan trips (either tripwire), *when* GET Finalise renders, *then* the response is 500, the body names the page-plan failure and contains the tripwire's own text, and shows no page count.
  *test: TestFinaliseGet_NamesThePagePlanFailure (in tests/test_book_finalise_gutter.py)*
- **AC-2:** *Given* the AC-1 book, *when* GET Finalise renders, *then* exactly one ERROR record with that exception's traceback is on the panel logger (today: two).
  *test: TestFinaliseGet_NamesThePagePlanFailure::logs_it_once (in tests/test_book_finalise_gutter.py; tighten the existing `test_the_screen_shows_no_count_and_the_error_is_logged_with_its_traceback` to `len(logged) == 1`)*
- **AC-3:** *Given* GET Finalise where something other than the page plan fails (e.g. the generator constructor raises `TypeError` with a marker string), *when* it renders, *then* the response is 500, the body does NOT say "page plan could not be built", and does NOT contain the marker string (the global handler stays generic).
  *test: TestFinaliseGet_OtherErrorsStayGeneric (in tests/test_book_finalise_gutter.py)*
- **AC-4:** *Given* an error that is raised once and then clears, on each Finalise POST action (`clear_cover`, `save_and_finish`, `download_pdf`), *when* the action is posted, *then* the flash is shown as today and one ERROR record with that exception and its traceback is on the panel logger.
  *test: TestFinalisePost_TransientErrorIsLogged (in tests/test_book_finalise_gutter.py, parametrised per action)*
- **AC-5:** *Given* a book the plan gate refuses (ADR-0035/R1), *when* Save and finish is posted, *then* the refusal is still flashed, the book stays in draft, and no ERROR record is written.
  *test: TestFinalisePost_PlanGateRefusalIsNotAnError (in tests/test_book_finalise_gutter.py)*
- **AC-6:** No error page or log line added by this card prints a secret: the global handler's output is unchanged, and the only exception text newly put on screen is the stamped page-plan failure.
  *test: review-lens (diff of `server_error` is empty; the new GET page is reached only through `_is_a_logged_plan_failure`)*

Each new test must fail on main 2e071b4 (AC-1: generic text; AC-2: two records; AC-4: zero records). Show it with a revert check.

## Guardrails

- G-1: The outer `except Exception` in `finalize_book` stays, and so does its flash text. Same for `generate_book_pdf_download`'s.
- G-2: The global `@app.errorhandler(500)` (`server_error`) and `500.html` are unchanged. No route other than Finalise shows exception text it does not show today.
- G-3: CARD-153's behaviour holds: all of `TestFinaliseCounts_PlanTripwireIsNotAnEstimate`, `TestSaveAndFinish_OnlyThePlanFailureIsBlamedOnThePlan`, `TestFinalise_UncountableBookStaysInDraft`, `TestFinaliseCounts_ShowsWhyTheCountIsApproximate` and `TestFinaliseGutter_InexactRefusalSaysAbout` stay green, and Finalise's page counts don't move.
- G-4: The plan gate keeps its precedence and its flash (`tests/test_book_ready_gate.py::test_the_finalize_route_flashes_it`). ADR-0035/R1 is not relaxed.
- G-5: No change to any PDF byte. The CON-019 golden A4 tripwire stays green.
- G-6: Never log or display secrets or credentials (passwords, `SECRET_KEY`, `DATABASE_URL`). The new log lines carry the exception and the book id only.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-171` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-030, FR-040, FR-042 (the page counts Finalise shows); EC-034 (the count checked is the count printed)
- **ADR:** ADR-0035/R1 (plan gate at the exit from draft), ADR-0030 (panel deployed behind a credential: why the global handler stays generic)
- **CON:** CON-016 (credentialed hostname mode), CON-019 (A4 golden, untouched)
- **Components:** COMP-009 (admin panel)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Screen:** GET `/book/<id>/finalize` when the page plan fails: the panel's `500.html` page, now naming the error, as POST Save and finish already does (CARD-153 render 6).
- **Renders:** ~/Documents/nonogram-reviews/CARD-171/ (GET plan-failure page; GET non-plan failure, still generic; a POST transient-error flash). Owner visual check.

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-041 (CARD-153 F-006, WSJF 2.5) + IDEA-040 (CARD-153 F-010, WSJF 6.0), combined because both live in `finalize_book`. Also closes CARD-153 F-009 (GET logs the tripwire twice).
- [Verified on main 2e071b4] `finalize_book` :4247; POST stamped-failure page ~:4318-4336; outer handler ~:4357; GET `_interior_counts` call ~:4405; `_interior_counts` :867; `_PLAN_FAILURE_LOGGED` :978; `_is_a_logged_plan_failure` :981; `generate_book_pdf_download` :4653 (its except :4669); `server_error` :5473. `500.html` already renders `error` in an alert; it needs no change.
- [Existing tests to reuse] `tests/test_book_finalise_gutter.py`: `PANEL_LOGGER` (:730), `_drop_last_planned_page` (:733) and the `TRIPWIRES` parametrisation, `_generator_cannot_start` / `_db_went_away` fixtures (~:950-967), `PROPAGATE_EXCEPTIONS=False` pattern. `test_the_screen_shows_no_count_and_the_error_is_logged_with_its_traceback` (:807) pins GET today (500, no count, logged) and gets the one-record assertion.
- [Why not the global handler] F-006 suggested `original_exception` in `server_error`. Rejected here: it echoes every route's raw exception text on a publicly reachable panel (G-2, G-6).
- [Pre-existing, not this card] The outer flash already shows `str(e)` on screen, so a DB error's text can appear in a flash today. Unchanged here (G-1); a follow-up could narrow it.
- [Precedent] `download_book_proof_pages` (~:4706) already logs with `app.logger.exception` before flashing: same shape as part 2.
- [Env] forge 2026.8.17
- [Impl] Commit 6fb9bc1 (src/nonogram/admin/app.py, tests/test_book_finalise_gutter.py only; no SCOPE+). New module-level `_page_plan_failure_page(error)` holds the one wording; POST Save and finish and GET both call it. GET wraps `_interior_counts` and re-raises anything `_is_a_logged_plan_failure` rejects. The wording is POST's existing text ("...and its status is not changed"), which also holds on GET (GET changes nothing).
- [Impl] POST outer `except Exception` keeps its flash; adds `app.logger.exception("A Finalise action on book %s failed", book_id)` first. `generate_book_pdf_download` keeps flash + redirect; adds `app.logger.exception("The PDF of book %s could not be generated", book.book_id)`. G-6: book id and the exception only.
- [Impl] Plan gate (AC-5): `except ValueError` at the two call sites (`_refuse_unless_the_planned_book` on the uncountable path, `set_book_status` on the normal path), flashed as `f"Error: {e}"`, the text the outer handler gave it before, so `test_the_finalize_route_flashes_it` and the gate's precedence are unchanged. Note: `set_book_status`'s other ValueError refusals (published, no puzzles, invalid status) take this path too and are not logged either; its docstring says each of its ValueErrors is an owner-facing refusal.
- [Impl] `server_error` and 500.html: diff empty (AC-6, G-2). No generator change (G-5).
- [Impl] Tests: TestFinaliseGet_NamesThePagePlanFailure (test_the_page_names_the_failure_and_shows_no_count, test_logs_it_once; both x TRIPWIRES), TestFinaliseGet_OtherErrorsStayGeneric, TestFinalisePost_TransientErrorIsLogged (clear_cover / save_and_finish / download_pdf; `_raise_once` helper: Path.unlink once for clear_cover with a stored cover in tmp BOOK_COVER_DIR, BookPDFGenerator.__init__ once for the other two), TestFinalisePost_PlanGateRefusalIsNotAnError (countable / uncountable book, a plan for 3 medium vs a selection of 3 easy). Existing `test_the_screen_shows_no_count_and_the_error_is_logged_with_its_traceback` tightened to `len(logged) == 1`. The panel fixture is in-memory only, so the neighbouring tests have no DB-mode variant, and neither do these.
- [Impl] Targeted runs: tests/test_book_finalise_gutter.py, test_book_ready_gate.py, test_book_export_interior_cover.py, test_book_finalise_guide_preview.py, test_book_detail_page.py, test_book_workflow_steps.py, test_book_pdf_ink_mode.py, test_book_trim_persistence.py, test_book_select_floor_tiles.py, test_admin_tier_surfaces.py, property/test_book_workflow.py: 633 passed.
- [Impl] Revert check (app.py back to main, new tests kept): 9 failed. The tightened existing test fails x2 (2 records: the helper's line plus Flask's "Exception on /book/.../finalize [GET]"); test_the_page_names... fails x2 (generic 500 text); test_logs_it_once fails x2 (2 records); TransientErrorIsLogged fails x3 (0 records). AC-3 and AC-5 pass on main, as the card expects (they pin behaviour that has to stay).
- [Impl] Mutation self-check (tests/test_book_finalise_gutter.py + test_book_ready_gate.py, each reverted afterwards): M1 GET drops the stamp guard -> TestFinaliseGet_OtherErrorsStayGeneric (and the existing generator-constructor case) fail; M2 GET re-raises the stamped failure instead of answering it -> both NamesThePagePlanFailure tests x2 + the tightened test x2 fail; M3 outer-handler log line deleted -> TransientErrorIsLogged[clear_cover], [save_and_finish] fail; M4 generate_book_pdf_download log line deleted -> TransientErrorIsLogged[download_pdf] fails; M5 gate catch on the uncountable path disabled (except KeyError) -> PlanGateRefusalIsNotAnError[uncountable] fails; M6 gate catch around set_book_status disabled -> PlanGateRefusalIsNotAnError[countable] fails; M7 helper wording changed -> test_the_page_names_the_failure_and_shows_no_count x2 fail. Every new test class failed on at least one mutant.
- [Owner default] none named in the card.
- [Scope] src/nonogram/admin/app.py, tests/test_book_finalise_gutter.py
- [Build gate] impact underivable (python-pro without pytest-testmon; config test_scope FULL) — full suite
- [Build gate] PASSED (full, 588s; 6128 passed, 9 skipped; lock wait 668s)
- [Scope gate] cycle 1: IN_SCOPE (2 files, both in Touches; no guarded file in diff)
- [Review 1/3] Score: 9.5 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/ (20261004T165109Z-CARD-171-cycle1.yml, yaml.safe_load OK)
- [Review 1/3] Step 8h coverage: 52/52 card rule ids have a verdict line (7 ✓, 45 ⚠ no_eligible_fact, 0 ✗)
- [Review 1/3] Mutation check (reviewer): 7/7 mutants killed (M-a..M-g)
- [Review 1/3] Step 8g: static only (visual off; no template/CSS/token change; 500.html unchanged) — rendered result not verified by review
- [Review 1/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Orchestrator] F-001 (Minor) narrowed in place, doc-only: `_page_plan_failure_page` docstring now says the stamp marks the page plan's own failure, already logged by `_interior_counts` (no longer "the exporter's own tripwire message"). Lands in the success commit.
- [8h spot-check] ✗ ADR-0006/R1 not reproduced — rule holds in substance, but the verdict's evidence "the diff adds no import line" is false: the card adds `from pathlib import Path` (stdlib) in tests/test_book_finalise_gutter.py; test green, pyproject untouched
- [8h spot-check] ADR-0035/R1 reproduced — gate-call args identical to main (app.py:4369, :4389); both named tests green (32 passed); no bypass path (line cite off by one: 4369 not 4370)
- [8h spot-check] ADR-0036/R1 reproduced — merge-base diff touches only admin/app.py + the test file; TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden green (125 passed). Result: 2/3 sampled holds reproduced; ADR-0006/R1 not → cycle 2 (spot-check failure costs a cycle)
- [AC/EC check] (cycle 1, run alongside the spot-check; not the gate of record because the spot-check failed) 12/12 ✓ demonstrated (AC-1..AC-6, G-1..G-6; no EC section) — 220 targeted tests passed; revert check re-confirmed AC-1/2/4 fail on base
- [Scope gate] cycle 2: IN_SCOPE (merge-base diff: app.py + test file; uncommitted docstring edit in app.py)
- [Review 2/3] Score: 10.0 — crit: 0, imp: 0 (confirmation mode; F-001 ✓ resolved; ADR-0006/R1 re-derived fresh with corrected evidence)
- [Review sync] 2 report(s) → meta/review/ (cycle2: 20261004T165859Z-CARD-171-cycle2.yml, yaml.safe_load OK)
- [Review 2/3] Step 8h coverage: 52/52 ids (7 ✓, 45 ⚠ incl. 2 carried(cycle 1, delta-clean): ADR-0038/R7, ADR-0038/R8; 0 ✗)
- [Review 2/3] Score: 10.0 ✓ threshold reached + no critical/important
- [Docs] forge:readme: no directory structure/purpose change (no new files; src/nonogram/admin has no README — per-directory README convention is an open owner decision; tests/README.md current) — skipped
- [8h spot-check] cycle 2: 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0035/R1, ADR-0036/R1)
- [AC/EC check] All criteria/constraints ✓ (evidence): AC/EC/G agent ran on the same working tree that cycle 2 reviewed (source diff hash d29fe9f unchanged since; no EC section); orchestrator re-ran the named test file + G-4 test fresh after the spot-check: 95 passed.
  AC-1 ✓ demonstrated — TestFinaliseGet_NamesThePagePlanFailure::test_the_page_names_the_failure_and_shows_no_count[page-plan|answer-key] PASSED (fail on base)
  AC-2 ✓ demonstrated — ::test_logs_it_once[page-plan|answer-key] + tightened test_the_screen_shows_no_count_and_the_error_is_logged_with_its_traceback (len(logged) == 1) PASSED (fail on base: 2 records)
  AC-3 ✓ demonstrated — TestFinaliseGet_OtherErrorsStayGeneric::test_a_non_plan_error_is_not_named_on_screen PASSED
  AC-4 ✓ demonstrated — TestFinalisePost_TransientErrorIsLogged[clear_cover|save_and_finish|download_pdf] PASSED (fail on base: 0 records)
  AC-5 ✓ demonstrated — TestFinalisePost_PlanGateRefusalIsNotAnError (countable, uncountable) PASSED
  AC-6 ✓ demonstrated — server_error identical to main; templates/ diff empty; _page_plan_failure_page called only at app.py:4357 and :4484, each right after `if not _is_a_logged_plan_failure(...): raise`
  G-1 ✓ demonstrated — both outer `except Exception` blocks and flash texts unchanged; only a logger.exception line added
  G-2 ✓ demonstrated — server_error/500.html unchanged; no other route shows new exception text
  G-3 ✓ demonstrated — the five CARD-153 classes PASSED (11+2+6+4+6); only test-line removal is `assert logged` → `assert len(logged) == 1`
  G-4 ✓ demonstrated — test_book_ready_gate.py::TestBookReady_RefusalNamesOffendingCell::test_the_finalize_route_flashes_it PASSED; that file unchanged
  G-5 ✓ demonstrated — both TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden classes PASSED (63+62); no export/layout file in diff
  G-6 ✓ demonstrated — new log calls carry a fixed format string + book id; exception via exc_info only
- [Renders] owner visual check: ~/Documents/nonogram-reviews/CARD-171/ — 1-get-plan-failure.{html,png} (500 page naming the plan failure + tripwire text), 2-get-other-error-generic.{html,png} (Flask's generic text, unchanged), 3-post-transient-flash.{html,png} (flash "Error: transient", Finalise re-rendered). Rendered from the worktree via the test panel fixture + headless Chrome.
- [Commit] success commit 5faa9db (on 6fb9bc1); card in review, awaiting done. Branch base 594cd7b — main has since moved (CARD-172 merged, edd61be); rebase at merge.
- [Merge gate] rebased onto 99154ea; full suite 6177 passed, 9 skipped, exit 0 (576s, under the lock). Merged 7713c65.
