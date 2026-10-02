# CARD-153: Finalise doesn't hide a broken page plan behind "About N"

**Status:** done
**Priority:** P1
**Category:** bug
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/153-finalise-broken-page-plan
**Worktree:** —
**Source:** CARD-129 review findings F-001, F-002, F-004, F-005 (2026-09-30); code re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 29
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_finalize.html, tests/test_book_finalise_gutter.py, tests/test_book_export_interior_cover.py
**Review score:** 9.5 (cycle 3/3)
**Started:** 2026-10-02T11:56:43Z
**Closed:** 2026-10-02T14:04:40Z
**Actual:** 0.3d
**Merge commit:** 11bea97
**Blocked by:** —

## What to implement

`_interior_counts` (`src/nonogram/admin/app.py:866`) asks the export's page plan
for the interior's page counts. It wraps that call in a bare `except Exception`
(:887). Three problems share that one root cause:

1. **A correctness failure looks like an estimate.** `interior_stream` raises
   `RuntimeError` from two deliberate plan tripwires ("the page plan prints …",
   "the answer key holds …", documented in `book_pdf_generator.py` around
   :2234). Those mean the exporter is wrong. The bare `except` catches them the
   same way it catches an unreadable print spec, and the screen shows "About N"
   with no log line and no message.
2. **The reason is recorded and then dropped.** `InteriorCounts.unreadable` is
   written at :901 and nothing ever reads it. The owner never learns why the
   count is approximate.
3. **A book can leave draft when its pages can't be counted.** When
   `_interior_counts` returns `None`, `_kdp_gutter_refusal` returns `None` (:926),
   which the `save_and_finish` branch (:4096) treats as "no objection". The book
   moves to `READY_FOR_PDF` while the same screen says its pages cannot be counted.

Also from the same review:

4. **Wording mismatch (F-005):** the refusal says the book "runs to N pages" where
   the screen says "About N" for the same inexact count.
5. **A vacuous assertion (F-004):** `tests/test_book_export_interior_cover.py:374`,
   `"~" not in body.split('data-interior-page-count')[1][:40]`, can never fail,
   because the first split segment after the attribute name never contains the
   display text.

## What to do

1. Only catch what means "this book's print spec can't be laid out". Let the
   plan tripwires (and any other unexpected exception) propagate as the
   errors they are, logged with a traceback. Find out the exact exception type(s)
   the "unlayable spec" case raises, and catch only those.
2. Show `unreadable` on the Finalise screen next to the approximate count, with
   the remedy (Print setup).
3. A book whose interior can't be counted at all must not leave draft. Refuse in
   `save_and_finish` with a message saying why.
4. Make the refusal text and the screen agree on whether the count is exact.
5. Replace the vacuous assertion with one that can fail.

## Acceptance criteria

- **AC-1:** When `interior_stream` raises one of its plan tripwires, Finalise
  does not show an "About N" count, and the error is logged with its traceback.
  *test: TestFinaliseCounts_PlanTripwireIsNotAnEstimate*
- **AC-2:** When the stored print spec can't be laid out, Finalise shows the
  approximate count together with the reason and points to Print setup.
  *test: TestFinaliseCounts_ShowsWhyTheCountIsApproximate*
- **AC-3:** A book whose interior cannot be counted stays in draft on
  "Save and finish", and the screen says why.
  *test: TestFinalise_UncountableBookStaysInDraft*
- **AC-4:** The refusal for an inexact count uses the same "about" wording as
  the screen.
  *test: TestFinaliseGutter_InexactRefusalSaysAbout*
- **AC-5:** The exactness assertion in `test_book_export_interior_cover.py` fails
  when the screen shows "~N" (checked by temporarily breaking it).
  *test: the existing test, rewritten*

## Guardrails

- G-1: The stored gutter is never raised or rewritten, and the book is never laid
  out a second time at another gutter (CARD-129's G-1/G-2 stand).
- G-2: No change to the PDF bytes of any export. The CON-019 golden A4 tripwire
  stays green.
- G-3: ADR-0035/R1's plan gate is unchanged; this card adds a refusal and
  doesn't relax one.

## Architecture context

- **FR:** FR-030, FR-040, FR-042 (page counts on Finalise); EC-034 (the count
  checked is the count printed)
- **ADR:** ADR-0035/R1, ADR-0036 (gutter clarification)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## System contract

_Assembled 2026-10-02 by system_rules.py --card CARD-153 (card scope: touches), 44 rules._

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

## Worktree notes

- [Origin] CARD-129's review: F-001/F-002/F-005 share one root cause and were
  left open when CARD-129 merged. Cut from the backlog sweep on 2026-10-02.
- [Why P1] This is the one place a real exporter bug would surface before the
  owner uploads to KDP, and right now it surfaces as a plausible number.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +44 ids (section was absent) / −0
### Implementation (2026-10-02, commit ff781b1)
- [What changed] `src/nonogram/admin/app.py` (Finalise path only: `_interior_counts`,
  `_kdp_gutter_refusal`, new `UNCOUNTABLE_INTERIOR_REFUSAL`, the `save_and_finish` branch, one new
  context key `page_count_unreadable`; plus `import logging`), `book_finalize.html` (an
  "Approximate" note beside the inexact count with the builder's reason and a Print setup link;
  the "cannot be counted" line links Print setup too), the two test files. No SCOPE+:
  `book_pdf_generator.py` and `book_kdp.py` are untouched (G-2: no PDF byte change).
- [Exception types, and how established] The unlayable spec raises **`ValueError` from
  `BookPDFGenerator.__init__`** (`page_frame(self.page_spec(1))` → `book_page_spec`; the ink-mode
  column read beside it raises ValueError too). Established by (a) the constructor's documented
  `Raises: ValueError: the book's stored print specification cannot be laid out`, (b)
  `book_page_spec`'s Raises section (all four checks raise ValueError, parity never changes
  validity), and (c) a probe: gutter 0.60, trim 5 cm, trim 200 cm, gutter "abc" all raised
  `ValueError` from the constructor, never from `interior_stream`. So the narrow catch is
  `except ValueError` **around the constructor only** — no generator change needed. Plan tripwires
  are `RuntimeError` from `interior_stream`.
- [The one other pre-existing case, preserved] A row whose answer grid is malformed makes
  `interior_stream` raise `RuntimeError("puzzle <id> could not be laid out ...")` even on a valid
  sheet. Before, that ended as `None` ("Cannot be counted"); several existing tests
  (`test_book_workflow_steps.py`, `property/test_book_workflow.py`, `test_book_ready_gate.py`)
  render Finalise for such placeholder rows. It is told apart from a tripwire by asking
  `unpaired_interior_page_count` (an independent sheet-free check that raises ValueError on exactly
  such a row): if the rows fail it → `None`, logged at WARNING with exc_info; otherwise the
  exception is logged with `logger.exception` and re-raised. Logger is
  `logging.getLogger(__name__)` = `app.logger`'s own name ("nonogram.admin.app").
- [Tripwire on screen] GET Finalise → the panel's 500 page (no count, no "About"). Note: the
  global `@app.errorhandler(500)` prints `str(e)` of Flask's InternalServerError wrapper, so the
  page does not name the tripwire — the traceback is in the log. Making the 500 page show
  `e.original_exception` is outside this card's scope (global handler); possible follow-up.
  On "Save and finish" the route's existing outer `except Exception` flashes it and the re-render
  500s; the book stays in draft.
- [G-3 precedence] The uncountable refusal would have pre-empted the plan gate's refusal
  (`test_book_ready_gate.py::test_the_finalize_route_flashes_it` went red). Fixed by asking the
  gate first, read-only, via `book_mgr._refuse_unless_the_planned_book(...)` — the exact check
  `set_book_status` makes — so its ValueError reaches the same handler with the same text. It is
  a private-method call across modules; making it public would be a book_manager.py edit, out of
  scope.
- [AC-4 wording] `gutter_refusal`'s text lives in `book_kdp.py` (out of scope), so
  `_kdp_gutter_refusal` rewrites "runs to N pages" → "runs to about N pages" when `exact` is
  false; the unreadable-gutter refusal says "its about N interior pages". The AC-4 test pins the
  phrase, so a rewording in book_kdp would fail it rather than silently drop "about".
- [Tests] All four AC classes in `tests/test_book_finalise_gutter.py` (17 new tests). AC-5 is the
  rewritten `TestBookFinalise_OffersBothDownloads` assertion (regex reads the `<dd>`'s displayed
  text; plus "About N interior pages" absent). Run: gutter + interior_cover files 122 passed;
  with golden A4 (CON-019), layout page spec, puzzle frame, CLI byte identity, ready gate,
  workflow steps/property, ink mode, floor tiles, trim persistence, pdf memory, tier surfaces,
  export-interior property, membership floor: 812 passed, 1 skipped.
- [Revert checks — each made the named tests fail, then restored]
  R0 AC-5: template forced to `~{{ page_count }}` → `assert '~7' == '7'` fails.
  R1 old bare `except Exception` around constructor+stream → all 7 PlanTripwire tests fail.
  R2 log call replaced by a no-op → the helper-level log test fails (2 params). (First version
  of the log test was satisfied by Flask's own 500 log line; rewritten to call the helper
  outside a request.)
  R3 `except ValueError` widened to cover `interior_stream` → `..._not_read_as_an_unlayable_spec`
  fails. R4 approximate note removed from the template → AC-2 screen tests fail.
  R5 uncountable refusal set to None → AC-3 refusal test fails. R6 "about" rewrite disabled →
  AC-4 inexact test fails. R7 unreadable-gutter "about" removed → its test fails.
  R8 (incidental) without the gate-first call, the ready-gate finalize test fails.
- [Renders] ~/Documents/nonogram-reviews/CARD-153/ — `.html` + `.png` for:
  1-approximate-count-with-reason, 2-approximate-refusal-says-about, 3-uncountable-book-refused,
  4-exact-count-unchanged, 5-plan-tripwire-500.
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/templates/book_finalize.html, tests/test_book_export_interior_cover.py, tests/test_book_finalise_gutter.py
- [Build gate] impact underivable (test_scope: full) — full suite
- [Build gate] PASSED (full, 303s; baseline: the 2 known pre-existing failures on main dc26103 — tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders — and no other failure/error)
- [Scope gate] cycle 1: in_scope (4/4 files within Touches; COMP-009 only; CARD-154 overlap 1/5 = 20%; no structural guardrails)
- [Review sync] 1 report(s) → meta/review/ (20261002T121938Z-CARD-153-cycle1.yml)
- [Review 1/3] Step 8h: 44 rules checked (11 ✓, 33 ⚠ no_eligible_fact, 0 ✗) — every card rule id has a verdict line
- [Adversarial] F-001 CONFIRMED — reproduced: _kdp_gutter_refusal(InteriorCounts(350, exact=False)) at gutter 0.6 returns book_kdp's "this interior runs to 350." while the screen says "About 350"; reachable from save_and_finish, no puzzle cap keeps the bound ≤300
- [Review 1/3] Score: 8.0 — crit: 0, imp: 1
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Fix 1] pre-gate: 6 named tests (9 cases) green; FIXED F-001, F-002, F-004, F-005; SKIPPED F-003 (needs public gate query in book_manager.py — out of scope; dismissed/deferred in YAML); F-006 out-of-scope untouched
- [Fix 1] declarations: 4 updated (docstrings/comments of _kdp_gutter_refusal, _about, _interior_counts, _is_an_unpackable_row, UNCOUNTABLE_INTERIOR_REFUSAL, finalize_book route), 0 confirmed, 0 none
### [Fix 1] review cycle 1 (score 8.0), 2026-10-02 — uncommitted
- F-001 (AC-4): new `_about(refusal, n)` rewrites "runs to N" → "runs to about N" for an inexact
  count in **both** book_kdp refusals (band minimum and `KdpPageCountNotModelled`); if book_kdp
  ever stops saying "runs to N", it appends "(This book's interior page count is about N, not
  exact.)" instead of silently no-opping. Tests:
  `TestFinaliseGutter_InexactRefusalSaysAbout::test_above_the_table_an_inexact_count_says_about`
  (350 pages, exact/inexact) and `::test_a_reworded_refusal_still_says_about`.
- F-002: malformed-row vs tripwire is decided by `_is_an_unpackable_row(error, puzzles)`: the
  exception must be a `RuntimeError` whose `__cause__` is a `ValueError` (the generator's
  documented "could not be laid out" shape; the two tripwires are raised bare, no cause) **and**
  the rows must fail the sheet-free count. The sheet-free check alone was a correlated neighbour:
  a row whose payload cannot be built is dropped from the plan, so a real tripwire can fire in a
  book whose rows also fail the sheet-free count. Message text is not read. Test:
  `TestFinaliseCounts_PlanTripwireIsNotAnEstimate::test_a_tripwire_in_a_book_with_a_malformed_row_is_not_read_as_uncountable`.
- F-004: `UNCOUNTABLE_INTERIOR_REFUSAL` is now status-neutral ("...and the book's status is not
  changed"). Test: `TestFinalise_UncountableBookStaysInDraft::test_a_book_past_draft_is_not_told_it_stays_in_draft`;
  the AC-3 refusal test now asserts the new wording.
- F-005: corrects the Implementation note above ("the outer except flashes it and the re-render
  500s"). Save and finish now catches the helper's re-raise and renders `500.html` itself, naming
  the tripwire, with the status untouched; it is logged once (by the helper). Test:
  `TestFinaliseCounts_PlanTripwireIsNotAnEstimate::test_save_and_finish_names_the_tripwire_on_its_error_page_and_logs_it_once`.
  The GET screen is unchanged (still the global 500; F-006 is out of scope).
- F-003: dismissed as deferred (needs a public gate query in book_manager.py, outside this card's
  scope); the call site now has a comment documenting the coupling.
- Revert checks: each new test failed with the finding's own symptom on the old code (F-001
  "runs to 350."; F-002 DID NOT RAISE (None); F-004 "stays in draft"; F-005 generic 500 text and
  two log records), then the code was restored.
- Renders refreshed in ~/Documents/nonogram-reviews/CARD-153/: 2-approximate-refusal-says-about,
  3-uncountable-book-refused; new 6-save-and-finish-tripwire-500.
- [Build gate] PASSED (full, 284s; baseline: the same 2 known pre-existing failures, no other failure/error)
- [Scope gate] cycle 2: in_scope (fix delta: src/nonogram/admin/app.py, tests/test_book_finalise_gutter.py)
- [Review sync] 2 report(s) → meta/review/ (cycle1 with fix statuses, 20261002T124028Z-CARD-153-cycle2.yml)
- [Review 2/3] Step 8h: 44 rules checked (11 ✓, 33 ⚠ no_eligible_fact — 23 carried(cycle 1, delta-clean), 0 ✗); cycle-1 F-001/F-002/F-004/F-005 verified resolved, F-003 deferred; 8f-mutation ran early: 10 mutants, 9 killed, M5 survived (F-008 Minor)
- [Adversarial] F-007 CONFIRMED — reproduced: get_puzzle_title raising KeyError on POST save_and_finish → returned 500.html blaming "page plan could not be built", book stays draft, zero log records on any logger (the returned 500 bypasses Flask's exception log and @app.errorhandler(500))
- [Review 2/3] Score: 8.0 — crit: 0, imp: 1
- [Severity gate 2/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Review 2/3] family check: F-007 is attributed to the F-005 fix (its declared boundary: the save_and_finish route) — streak 1, below the escalation threshold of 2
- [Review 2/3] ⚠ improvement stalled — Δscore: 0.0, Δcrit+imp: 0
- [Escalated] 2026-10-02 — review stalled at 8.0, cycle 2/3: cycle 1's one Important finding (F-001, AC-4 wording) was fixed and verified, but the cycle-1 fix of Minor F-005 brought in a new Important finding, F-007: Save and finish's new `except Exception` around `_interior_counts(book, members_in_order())` (app.py ~4249-4263) turns any non-plan error (a DB error in members_in_order, a non-ValueError from the generator constructor) into an unlogged 500 that blames the page plan, against objective 1 ("any other unexpected exception … logged with a traceback"). Both cycles had 1 Important finding at 8.0, so the mechanical stalled check fired. NOT a regenerating loop: the remaining fix is small and well specified. · station: implementation (code defect; requirement and card are sound) · route: one targeted fix + `/kanban review CARD-153` (preferred: move members_in_order() out of the try, and catch only the helper's own re-raise or log whatever the helper didn't, plus a test that a non-plan error on Save and finish is logged with its traceback; optionally close Minor F-008 with a test for `_is_an_unpackable_row`'s second condition, i.e. surviving mutant M5). `/kanban redo` is NOT indicated. State: ff781b1 committed on the branch; the cycle-1 fix edits (app.py, tests/test_book_finalise_gutter.py) are UNCOMMITTED in the worktree, kept as the procedure requires. Reports: meta/review/20261002T121938Z-CARD-153-cycle1.yml, meta/review/20261002T124028Z-CARD-153-cycle2.yml
- [Unblocked] 2026-10-02 — owner chose targeted fix of F-007 + final review cycle (dispatcher)
### [Fix 2] review cycle 2 (score 8.0), 2026-10-02 — uncommitted
- F-007 (introduced by the F-005 fix): Save and finish no longer turns every exception into the
  "page plan could not be built" page.
  - Invariant: that page (status 500, status untouched) is shown for exactly the page-plan
    failure `_interior_counts` has already logged with its traceback; every other exception takes
    the route's ordinary path and is logged with its traceback, never blamed on the plan.
  - Discriminator: the helper's own stamp. Right after its one `log.exception` for an
    `interior_stream` failure, `_interior_counts` sets `_PLAN_FAILURE_LOGGED` on that very
    exception and re-raises it unchanged (type, message, traceback). The route reads the rows
    (`members_in_order()`) **before** the `try`, and its `except` re-raises anything
    `_is_a_logged_plan_failure()` does not recognise. Why not the class: a tripwire is a
    `RuntimeError`, but so are DB-driver and constructor errors (correlated neighbour), and the
    plan can also fail with a `ValueError`; only the stamp says both "this is the plan's failure"
    and "already logged". Marking rather than wrapping keeps the error the error it is, so the
    AC-1 helper tests (`exc_info[1] is raised.value`, `pytest.raises(RuntimeError|ValueError)`)
    are unchanged and not weakened; GET Finalise is unchanged.
  - A non-plan error now reaches the route's pre-existing outer `except Exception` (flash) and
    the re-render, whose failure Flask logs ("Exception on /book/<id>/finalize [POST]", with
    traceback) and 500s — the behaviour before the F-005 fix. Residual, pre-existing and outside
    this card: an error that clears by the re-render would be flashed only, not logged (the outer
    handler covers every POST action).
  - Tests: `TestSaveAndFinish_OnlyThePlanFailureIsBlamedOnThePlan::test_a_non_plan_error_is_logged_and_not_called_a_page_plan_failure`
    [row-read: `get_puzzle_title` raises KeyError('db went away'); generator-constructor:
    TypeError]. PROPAGATE_EXCEPTIONS=False.
- F-008: `TestFinaliseCounts_PlanTripwireIsNotAnEstimate::test_a_layout_abort_on_clean_rows_is_the_exporters_error`
  — two `pairs_up` rows (sheet-free count accepts them), `compute_pair_layout` patched to raise
  ValueError; the pairing walk's real "could not be laid out" RuntimeError-from-ValueError must be
  re-raised and logged at ERROR with traceback.
- Revert checks: cycle-1 app.py restored from a captured copy → both F-007 params fail with the
  finding's symptom (body contains "page plan could not be built ... 'db went away'"); mutant M5
  (drop the sheet-free check) → only the F-008 test fails; stamp removed → the F-005
  logged-once test fails (2 params). Fix restored, sha 17e92dd verified before the final
  docstring touch.
- Docstrings corrected: `_interior_counts` (stamp, Raises), new `_is_a_logged_plan_failure`,
  `_is_an_unpackable_row` (pairing-walk shape), the route's save_and_finish comment.
  500-page text unchanged (now only shown for the stamped failure).
- Run: finalise gutter, export interior/cover, ready gate, workflow steps, workflow property, CLI:
  421 passed.
- Renders (worktree src verified via nonogram.__file__): refreshed 6-save-and-finish-tripwire-500
  (unchanged text); new 7-save-and-finish-non-plan-error (flash "Error: 'db went away'" + the
  global 500 page, no "page plan" wording).
- [Fix 2] pre-gate: 2 named tests (3 cases) green; FIXED F-007, F-008; declarations: 2 updated (doc _interior_counts, _is_a_logged_plan_failure (new), _is_an_unpackable_row, finalize_book save_and_finish comment), 0 confirmed, 0 none
- [Commit] cycle-1 + cycle-2 fixes committed on the card branch (owner-approved resume); nothing under meta/
- [Build gate] PASSED (full, 311s; baseline: the same 2 known pre-existing failures, no other failure/error)
- [Scope gate] cycle 3: in_scope (4/4 files within Touches)
- [Review sync] 3 report(s) → meta/review/ (incl. 20261002T132240Z-CARD-153-cycle3.yml)
- [Review 3/3] Score: 9.5 — crit: 0, imp: 0 (FULL review; F-007, F-008 verified resolved; Minor F-009 GET tripwire logged twice; out-of-scope F-010 pre-existing outer except only flashes, F-003 deferred, F-006)
- [Review 3/3] Step 8h: 44 rules checked, fresh (12 ✓, 32 ⚠ no_eligible_fact, 0 ✗); 8f-mutation re-certified this cycle: 12 mutants, 12 killed
- [Review 3/3] Score: 9.5 ✓ threshold reached + no critical/important
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0035/R1) — note: the named check TestDependencyBaseline_IsExactlyPillowAndNumpy is a label in tests/test_export_pdf.py (tests test_the_dependency_baseline_is_still_closed + font-as-package-data, 2 passed), not a class; M9 independently re-run and killed
- [AC/EC check] Failed: G-1 ⚠ partial — "stored gutter is never raised or rewritten" demonstrated (TestKdpGutterTable never-rounded-up/writes-nothing, TestBookFinalise_RefusesGutterBelowKdpMinimumForPageCount::test_the_stored_gutter_is_not_changed, AC-3 test asserts gutter unchanged); "never laid out a second time at another gutter" has no test (code reading only). AC-1..AC-5, G-2, G-3 ✓ demonstrated
### [Fix 3] AC/EC/G verification — G-1 second half, 2026-10-02 — uncommitted
- G-1 "never laid out a second time at another gutter" had no test. Added
  `TestFinaliseGutter_NeverLaidOutAgainAtAnotherGutter` (tests/test_book_finalise_gutter.py): spies
  `nonogram.admin.app.BookPDFGenerator` (+ wraps `_interior_counts`) and asserts, for GET Finalise and
  refused POST save_and_finish (exact refusal at 0.70 cm and 151 pages at 0.95 cm, no-sheet 0.60 cm,
  uncountable row), that every generator/layout reads the stored gutter, at most one layout per count,
  and the gutter column is unchanged. Test-only; no production change.
- Revert check: injecting a second layout at 1.27 cm in `_interior_counts` (4 fail) and in
  `_kdp_gutter_refusal` (3 fail) both turned the new tests red; app.py restored by copy, `cmp` clean.
- Run: finalise gutter + ready gate: 171 passed.
- [Fix 3] (AC/EC/G gate) pre-gate: TestFinaliseGutter_NeverLaidOutAgainAtAnotherGutter 3 tests / 7 cases green; FIXED G-1 (test-only); declarations: 0 updated, 0 confirmed, 1 none
- [Build gate] PASSED (full, 292s; baseline: the same 2 known pre-existing failures, no other failure/error)
- [Scope gate] cycle 3 (re-entry after AC/EC/G fix): in_scope (delta: tests/test_book_finalise_gutter.py only)
- [Review sync] 4 report(s) → meta/review/ (incl. 20261002T134252Z-CARD-153-cycle3.yml, the cycle-3 re-entry)
- [Review 3/3] re-entry (confirmation mode, test-only delta) Score: 9.5 — crit: 0, imp: 0; G-1 ✓ re-verified with 2 independent revert checks; new Minor F-011 (layout spy sees only BookPDFGenerator layouts); 8h 44 rules (INV-011 fresh, rest carried delta-clean); 8f carried (src unchanged since 12/12)
- [Review 3/3] Score: 9.5 ✓ threshold reached + no critical/important
- [8h spot-check] re-entry: 1/1 sampled fresh hold reproduced (INV-011; the other 11 holds are carried and excluded from the pool)
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — evidence: TestFinaliseCounts_PlanTripwireIsNotAnEstimate 11/11 PASSED (incl. test_the_screen_shows_no_count_and_the_error_is_logged_with_its_traceback[page-plan|answer-key])
  AC-2 ✓ demonstrated — evidence: TestFinaliseCounts_ShowsWhyTheCountIsApproximate 4/4 PASSED (gutter 0.60 and trim 5 cases)
  AC-3 ✓ demonstrated — evidence: TestFinalise_UncountableBookStaysInDraft 6/6 PASSED (no-sheet and sheet)
  AC-4 ✓ demonstrated — evidence: TestFinaliseGutter_InexactRefusalSaysAbout 6/6 PASSED
  AC-5 ✓ demonstrated — evidence: TestBookFinalise_OffersBothDownloads::test_the_screen_renders_an_interior_and_a_cover_download PASSED; with the template forced to "~{{ page_count }}" it FAILED (assert '~7' == '7'); template restored, cmp identical
  G-1 ✓ demonstrated — evidence: TestKdpGutterTable + TestBookFinalise_RefusesGutterBelowKdpMinimumForPageCount PASSED (stored gutter never rewritten); TestFinaliseGutter_NeverLaidOutAgainAtAnotherGutter 7/7 PASSED and fails on an injected second layout at a raised gutter (5 sheet-path / 2 no-sheet failures), app.py restored, cmp identical
  G-2 ✓ demonstrated — evidence: tests/test_export_a4_golden.py (CON-019) all PASSED (61 layout cases + CLI golden png/svg/pdf); no src/nonogram/export/ or book_pdf_generator.py in the diff
  G-3 ✓ demonstrated — evidence: tests/test_book_ready_gate.py all PASSED incl. TestBookStatus_EveryExitFromDraftIsGatedOnThePlan (26 cases, memory and db); gate code not in the diff; no test lines removed
- [Docs] forge:readme — current: changed dirs src/nonogram/admin/, src/nonogram/admin/templates/, tests/ gain no new file/module and no responsibility change (admin/ and templates/ have no README; the per-directory README convention is an open owner decision on the board backlog); tests/README.md unaffected
- [Commit] success — card branch: ff781b1 (implementation), 0773bed (cycle-1/2 review fixes), 8a9f7a0 (G-1 evidence test; success commit). 4 files, +885/−19 vs merge-base dc26103; nothing under meta/ committed. Card stays `review` until done.
- [Merged] 2026-10-02 — 11bea97 into main (--no-ff). Rebased onto 5037625 cleanly (main had not touched the card's 4 files) and the full suite ran on that tree under the lock (waited 258s, ran 384s; only the 2 baseline failures). Main then moved by 92fb9b4 (meta/releases/wave-28.md only); re-rebased, tree otherwise identical, not re-run. Deferral scan: 0 hits. Trace write-back: CARD-153's evidence tests appended to FR-030 (5), FR-040 (3), FR-042 (3); statuses stay `partial` (FR-030 is still listed by open CARD-154/158/159; FR-040/FR-042 wait on the wave-27 owner checkpoint). Follow-ups F-003, F-006, F-009, F-010, F-011 captured to backlog.
