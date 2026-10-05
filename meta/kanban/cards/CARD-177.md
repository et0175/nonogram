# CARD-177: Finalise and the book PDF downloads flash a generic error, not the exception's text

**Status:** done
**Priority:** P1
**Category:** compliance
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/177-generic-error-flash-on-finalise-and-pdf
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-05 (CARD-171 Worktree notes, "Pre-existing, not this card"; CARD-171 G-1 kept `str(e)`)
**Idea:** IDEA-091
**Wave:** 34
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, tests/test_book_finalise_gutter.py, tests/test_admin_error_text.py
**Review score:** 9.0 (1 cycle)
**Started:** 2026-10-05T07:46:37Z
**Closed:** 2026-10-05T09:52:40Z
**Actual:** 0.3d
**Merge commit:** d1995fd
**Blocked by:** —

## What to implement

The admin panel is deployed at a public hostname behind a credential (ADR-0030, CON-016).
Three broad `except Exception` handlers on the book export path put the raw exception
text on screen. A database driver's error can name hosts, users and connection
details. The fix: flash a fixed, generic message, and keep the detail in the log only.

**Current behaviour (read on main 1ebf337):**

1. `finalize_book` (`src/nonogram/admin/app.py:4299`), POST outer handler (:4436-4440):
   `app.logger.exception("A Finalise action on book %s failed", book_id)` (CARD-171), then
   `flash(f"Error: {str(e)}", "error")`. It catches whatever the `clear_cover` and
   `save_and_finish` actions raise, including a database error reading the rows
   (`members_in_order`, :4307) and any error `_interior_counts` re-raises unstamped.
2. `generate_book_pdf_download` (:4736), its `except Exception` (:4752-4756):
   `app.logger.exception("The PDF of book %s could not be generated", ...)` (CARD-171), then
   `flash(f"Failed to generate PDF: {str(e)}", "error")` and a redirect. It serves
   Finalise's `download_pdf` action and `POST /book/<id>/download-pdf`.
3. `generate_book_pdf` (:5034, `POST /book/<id>/generate-pdf`), its `except Exception`
   (:5080-5082): `flash(f"Error generating PDF: {str(e)}", "error")` and a redirect.
   It writes **no log line**. It is the third route of the same export (FR-043), so it
   is in scope with the other two.

**Target behaviour:**

- Each of the three handlers flashes a fixed message that contains no part of the
  exception. Suggested wording (owner-visible, see Design context):
  - Finalise outer handler: `Error: that action could not be completed. The details are in the panel's log.`
  - Both PDF handlers (one shared constant): `Failed to generate PDF. The details are in the panel's log.`
- Put each wording in one module-level constant, so tests import it rather than copy it.
- Each handler logs the exception once, with its traceback, on the panel logger
  (`nonogram.admin.app`), before it flashes. Handlers 1 and 2 already do; keep those
  lines as they are. Add the same shape to handler 3:
  `app.logger.exception("The PDF of book %s could not be generated", book_id)`.
- Every handler keeps its status code and destination: Finalise POST re-renders (200);
  the PDF handlers redirect (302) to where they redirect today.
- The generic message applies to every exception class that reaches these three
  handlers, `ValueError` included. The owner refusals never reach them: they are
  caught or returned earlier, and keep their text (see G-2).

**Out of scope (this card):** the other routes that echo `str(e)` from a broad handler.
They are listed in Worktree notes as a scope question for the owner.

## Acceptance criteria

- **AC-1:** *Given* a Finalise POST action (`clear_cover`, `save_and_finish`) that raises once an exception whose message carries a marker, *when* the action is posted, *then* the response is 200, the flash shown is the Finalise generic constant, the marker is nowhere in the body, and exactly one ERROR record with that exception and its traceback and the book id is on the panel logger.
  *test: TestFinalisePost_TransientErrorIsLogged (in tests/test_book_finalise_gutter.py; update the expected flash for `clear_cover` and `save_and_finish` from `f"Error: {error}"` to the constant, and assert the marker is absent)*
- **AC-2:** *Given* a book export that raises once an exception with a marker, *when* it is requested through each of the three routes (Finalise `download_pdf`, `/download-pdf`, `/generate-pdf`), *then* the response is a 302 to today's destination, the only error flash is the PDF generic constant, the marker is in no flash and not in the `Location` header, and exactly one ERROR record with that exception, its traceback and the book id is on the panel logger.
  *test: TestBookPdfDownload_ErrorIsGenericAndLogged (in tests/test_admin_error_text.py, parametrised over the three routes; the Finalise `download_pdf` row in TestFinalisePost_TransientErrorIsLogged gets the same constant)*
- **AC-3:** *Given* a seeded corpus of at least 60 cases (fixed `random.Random` seed; asserted count), each an exception whose message holds a fake credential (a DSN like `postgresql://nonogram:<fake-password>@db.internal:5432/nonogram_poc`, `password=<fake>`, a `SECRET_KEY`-like token; some with HTML-special characters and newlines) of a varied class (`RuntimeError`, `OSError`, `TypeError`, `KeyError`, `ValueError`, a stand-in `OperationalError(Exception)`), raised once at one of five seams (clear_cover's unlink, save_and_finish's row read, and the export generator on each of the three PDF routes), *when* the request is made, *then* the fake password appears in none of: the body (raw and `html.unescape`d), the flashed messages, the response headers; and the exception is logged exactly once.
  *test: PropertyTest_AdminErrors_RawExceptionTextNeverReachesTheScreen (in tests/test_admin_error_text.py)*
- **AC-4:** *Given* each owner refusal on these paths (the plan gate's refusal on Save and finish, the KDP gutter refusal, the uncountable-interior refusal, the lost-cover refusal, the unknown-part refusal, the stamped page-plan failure page), *when* it fires, *then* its text is shown exactly as before.
  *test: existing tests stay green unmodified — test_the_finalize_route_flashes_it (tests/test_book_ready_gate.py), TestFinalisePost_PlanGateRefusalIsNotAnError, TestFinaliseGet_NamesThePagePlanFailure, TestFinaliseGutter_InexactRefusalSaysAbout (tests/test_book_finalise_gutter.py), test_a_cover_download_is_refused_not_silently_swapped (tests/test_book_export_interior_cover.py)*
- **AC-5:** The only flash text changed is in the three handlers named above; no new log line carries anything but the book id and the exception; `server_error` and `500.html` are unchanged.
  *test: review-lens (diff of app.py touches only :4436-4440, :4752-4756, :5080-5082 and the new constants; `git diff` of `server_error` and templates/500.html is empty)*

AC-1, AC-2 and AC-3 must each fail on main 1ebf337 (the flash carries `str(e)`; `/generate-pdf` also writes no log record). Show it with a revert check.

## Guardrails

- G-1: All three outer `except Exception` handlers stay (owner rule: the outer try/except is intentional). CARD-171's two log lines keep their text. No exception is logged twice.
- G-2: Owner refusals keep their text and their place: the plan gate's `ValueError` caught at the two call sites in `save_and_finish` (:4404, :4421), `UNCOUNTABLE_INTERIOR_REFUSAL`, `_kdp_gutter_refusal`, `_LOST_COVER_MESSAGE`, the unknown-part flashes, and `_page_plan_failure_page` (the exporter's own text, CARD-171 AC-1/AC-6). ADR-0035/R1 is not relaxed.
- G-3: `server_error` (:5559) and `500.html` are unchanged. GET Finalise's non-plan failure stays generic (TestFinaliseGet_OtherErrorsStayGeneric).
- G-4: No other route's flash or response changes. In particular the batch error strings pinned by tests/test_card_062_abandon_retry.py ("Error processing wide.png: ...") stay as they are.
- G-5: No PDF byte changes. The CON-019 A4 golden (TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden) and the book pixel baselines stay green.
- G-6: Never put a secret or credential on screen or in new log text (passwords, `SECRET_KEY`, `DATABASE_URL`). The test corpus uses invented values only.
- G-7: CARD-153/CARD-171 behaviour holds: TestFinaliseCounts_PlanTripwireIsNotAnEstimate, TestSaveAndFinish_OnlyThePlanFailureIsBlamedOnThePlan, TestFinalise_UncountableBookStaysInDraft stay green; the book stays in draft after a failed Save and finish.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-177` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-043 (the book export's three routes produce one export); FR-030 (Finalise / Save and finish gate)
- **ADR:** ADR-0030 (panel reachable at a public hostname behind a credential: why exception text must stay off screen); ADR-0035/R1 (plan gate refusal, unchanged)
- **CON:** CON-016 (credentialed hostname mode), CON-019 (A4 golden, untouched)
- **Components:** COMP-009 (admin panel)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Screens:** the Finalise page after a failed `clear_cover` / `save_and_finish` (flash), and the page a failed PDF download redirects to (Finalise or book detail).
- **Owner-visible default:** the new flash wording replaces the exception text. The owner no longer sees *why* a PDF failed on screen; the reason is in the panel log (Render's log stream when deployed). For an unreadable print setup the Finalise screen already names the reason (CARD-173 sentence and the "Approximate" note), so that case is still visible there.
- **Renders:** ~/Documents/nonogram-reviews/CARD-177/ (Finalise with the generic flash after a failed action; book detail after a failed `/generate-pdf`). Owner visual check of the wording before merge.

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-091 (compliance, P1, WSJF 13). Follows CARD-171, which added the log lines and deliberately kept `str(e)` (its G-1 and "Pre-existing" note).
- [Verified on main 1ebf337] `finalize_book` :4299; `members_in_order` :4307; plan gate catches :4404 and :4421; outer handler :4436-4440; cover-upload handler :4453-4454; `_export_part` :4689; `generate_book_pdf_download` :4736 (except :4752-4756); `generate_book_pdf` :5034 (except :5080-5082, no log); `server_error` :5559; `_page_plan_failure_page` :996.
- [Tests that pin today's text] tests/test_book_finalise_gutter.py `_clear_cover_fails_once` (:1431), `_save_and_finish_fails_once` (:1437), `_download_pdf_fails_once` (:1443) return the old expected flashes (`f"Error: {error}"`, `f"Failed to generate PDF: {error}"`); update them to the constants. No test asserts the `/generate-pdf` error text today.
- [Reuse] `_raise_once` (:1406), `PANEL_LOGGER` (:730), `_panel_errors`, the `panel` fixture (:194) in tests/test_book_finalise_gutter.py; `ROUTES`, `admin_app` and `_flashes` in tests/test_book_export_interior_cover.py. The new file may copy small helpers rather than import across test modules. Inject the save_and_finish error at `panel.books.get_puzzle_title` (as `_db_went_away` does, :949), raise-once so the re-render succeeds. Do NOT inject a `ValueError` at `BookPDFGenerator.__init__` on the save_and_finish seam: `_interior_counts` (:928) treats that as an unreadable print setup and shows its text by design.
- [Log text] The log record carries the exception object, as CARD-171's lines do. This card adds no text of its own to it and does not scrub driver messages in the log (server log only).
- [Scope question for the owner] Other broad handlers that echo `str(e)` on screen, NOT changed here (G-4). Candidates for a follow-up card:
  - `delete_book` :4834-4835 `Failed to delete book: {e}` — a pure DB call, the closest match to this card's risk; recommended next.
  - `finalize_book` cover upload :4453-4454 `Failed to load image: {e}` — Pillow/OS text (may name file paths); no log line.
  - `download_book_proof_pages` :4791-4797 `Failed to generate proof pages: {e}` — logged; mixes one owner refusal (trim with no room for the proof note) with bugs, so it needs the refusal split out first.
  - `batch_from_images` per file :1575-1576 and outer :1602-1603; `generate_batch_puzzles` per image :1958-1959 (into the flashed `errors` list) and outer :2042-2043 `Unexpected error: {e}` — none logged. The per-image `NonogramError` branch (:1951-1957) is an owner message and must keep its text (tests/test_card_062_abandon_retry.py).
  - Plain-text 500 bodies: `api_get_image` :5149-5150, `api_get_cropped_image` :5220-5221, `api_puzzle_grid_from_puzzle` :5251-5252, `api_puzzle_grid_download_from_puzzle` :5280-5281, `api_puzzle_grid_download_pdf` :5341-5343 (only the last is logged).
- [Scope decision] `/generate-pdf` is included although the idea names only Finalise: it is the third route of the same export (FR-043), and leaving it would keep the leak on one of three buttons.
- [AC cross-check] Re-read AC-1..AC-5 against the body: placement (log before flash), the three handlers, ValueError treated as generic inside them, and refusals untouched all agree. No change was needed.
- [Env] forge 2026.8.17
- [Implementation 2026-10-05] app.py: two module constants after `UNCOUNTABLE_INTERIOR_REFUSAL` — `FINALISE_ACTION_FAILED`, `PDF_EXPORT_FAILED`. Finalise outer handler and `generate_book_pdf_download` now flash the constants (`except Exception:` without `as e`; CARD-171 log lines unchanged). `generate_book_pdf` gains `app.logger.exception("The PDF of book %s could not be generated", book_id)` before its flash of `PDF_EXPORT_FAILED`. All three outer handlers kept (G-1); statuses/destinations unchanged. No other app.py hunk; `server_error` and templates/500.html untouched.
- [Owner default] flash wording — implemented as drafted.
- [Tests] tests/test_book_finalise_gutter.py: `_clear_cover_fails_once`/`_save_and_finish_fails_once`/`_download_pdf_fails_once` return the constants; TestFinalisePost_TransientErrorIsLogged uses a distinct marker and asserts it is absent from the body (200) or from every flash and the Location header (302). Nothing else in that file changed. New tests/test_admin_error_text.py: TestBookPdfDownload_ErrorIsGenericAndLogged (AC-2, 3 routes; raise-once at `BookPDFGenerator.__init__`; no Referer, so 302 to `/book/<id>`) and `test_PropertyTest_AdminErrors_RawExceptionTextNeverReachesTheScreen` (AC-3; function form, the repo's naming for property tests; seed 177, 60 cases, count asserted; covers all 6 classes and all 5 seams, asserted; save_and_finish seam is raise-once at `panel.books.get_puzzle_title` per [Reuse]). Order of log vs flash is NOT asserted by any test.
- [Mutants] (scratchpad card177_mutants.py; app.py restored after each) — M1 finalise flash `f"Error: {str(e)}"`: killed by TransientErrorIsLogged[clear_cover], [save_and_finish], PropertyTest. M2 download flash `f"Failed to generate PDF: {str(e)}"`: killed by AC-2[finalise], AC-2[download-pdf], TransientErrorIsLogged[download_pdf], PropertyTest. M3 generate-pdf flash `f"Error generating PDF: {str(e)}"`: AC-2[generate-pdf], PropertyTest. M4 drop the new generate-pdf log line: AC-2[generate-pdf], PropertyTest. M5 generate-pdf logs twice: AC-2[generate-pdf], PropertyTest. M6 (edge) finalise leaks only for ValueError: PropertyTest. M7 (edge) download appends html.escape(str(e)): AC-2[finalise], AC-2[download-pdf], TransientErrorIsLogged[download_pdf], PropertyTest. M8 (edge) download leaks only for a class named OperationalError: PropertyTest.
- [Revert check] 2e40c96's app.py put in place (plus the two constants appended so the imports resolve): 7 failed — AC-2 x3, PropertyTest (AC-3), TransientErrorIsLogged x3 (AC-1 incl. download_pdf row). Restored afterwards.
- [Tests run] tests/test_admin_error_text.py, test_book_finalise_gutter.py, test_book_ready_gate.py, test_book_export_interior_cover.py, test_card_062_abandon_retry.py, test_book_trim_persistence.py, test_book_workflow_steps.py, test_print_specs.py: 659 passed (under the shared lock). tests/test_export_a4_golden.py + test_layout_page_spec.py (G-5): 168 passed. AC-4/G-3/G-7 named tests are in those files, unmodified, green. Grep for the old strings in tests/ found only the three helpers above (the other `f"Error: ` hits are print-setup refusals on other routes, green).
- [Scope] src/nonogram/admin/app.py, tests/test_admin_error_text.py, tests/test_book_finalise_gutter.py
- [Build gate] impact underivable (test_scope: full) — full suite
- [Build gate] PASSED (full, 700s) — 6274 passed, 9 skipped
- [System contract] fresh assembly (system_rules.py --card CARD-177) matches the card's 52 rules — no refresh
- [Scope gate 1] IN_SCOPE — 3 files, all inside Touches; components: COMP-009 only; no structural guardrail hit (templates/500.html untouched)
- [Visual] review.visual off — owner renders before/after in ~/Documents/nonogram-reviews/CARD-177/ (8 PNG + HTML; fake password on screen: before 4/4, after 0/4)
- [Orchestrator] 2026-10-05T08:40:36Z handed back before completion (harness forced hand-back): review cycle 1 agent still running, no cycle-1 report yet; no success commit beyond implementation cb05439
- [Review 1/3] Score: 9.0 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/
- [Adversarial] no Critical/Important findings in cycle 1 — nothing to verify
- [Review 1/3] Step 8h coverage: 52/52 card rules named (10 ✓, 42 ⚠ no_eligible_fact, 0 ✗); no extra ids
- [Review 1/3] Score: 9.0 ✓ threshold reached + no critical/important
- [Review 1/3] 8f mutation check ran (5 reviewer mutants MA–ME, all killed; app.py restored byte-exact); revert check independently confirmed (7 failures on 2e40c96 app.py)
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0035/R1, INV-007, INV-013)
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-1 ✓ demonstrated — TestFinalisePost_TransientErrorIsLogged[clear_cover|save_and_finish|download_pdf] 3 passed (fail on main); AC-2 ✓ demonstrated — TestBookPdfDownload_ErrorIsGenericAndLogged[finalise|download-pdf|generate-pdf] 3 passed (fail on main); AC-3 ✓ demonstrated — test_PropertyTest_AdminErrors_RawExceptionTextNeverReachesTheScreen passed, 60 cases asserted (fails on main); AC-4 ✓ demonstrated — 16 named refusal tests passed, files unmodified vs main; AC-5 ✓ demonstrated — app.py hunks only constants + the three handlers, 500.html diff empty, server_error in no hunk; G-1 ✓ three except blocks kept, CARD-171 log lines unchanged, logged-once asserted; G-2 ✓ refusal tests green, no refusal text in diff; G-3 ✓ 500.html/server_error untouched, OtherErrorsStayGeneric green; G-4 ✓ test_card_062_abandon_retry 14 passed, no other route hunk; G-5 ✓ A4 golden + book pixel baselines 252 passed 1 platform skip; G-6 ✓ invented credentials only, no credential in new log text; G-7 ✓ PlanTripwire/OnlyThePlanFailure/UncountableBookStaysInDraft green (no EC section on this card)
- [Docs] no README change: src/nonogram/admin/ has no README (per-directory README convention is an open owner decision), tests/README.md is a Wave-1 listing that enumerates no book test files — structure/purpose of both dirs unchanged
- [Commit] the passing cycle left no uncommitted code: cb05439 (implementation commit, 3 files, +329/−13 vs main 2e40c96) is the success commit; nothing under meta/ committed. Open Minor: F-001 log-before-flash order not asserted by a test; F-002 AC-2 destination checked only without a Referer. Out-of-scope: OOS-1 owner no longer sees exporter text (e.g. unreadable print setup ValueError) on the PDF routes — confirm log reachability on Render; OOS-2 other routes echoing str(e) (delete_book next); OOS-3 /generate-pdf can show success+failure flashes if sending fails (pre-existing). Card stays review until done.
- [Merge gate] rebased onto a5df2a0; full suite 6327 passed, 9 skipped, exit 0 (596s, under the lock). Owner: "merge now, check later" (wording renders in ~/Documents/nonogram-reviews/CARD-177/). Merged d1995fd.
