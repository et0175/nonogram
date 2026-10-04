# CARD-164: Main goes green: fix the two tests that have been red for weeks

**Status:** done
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/164-main-goes-green
**Worktree:** —
**Source:** roadmap wave 1 (meta/kanban/roadmap.md), 2026-10-04
**Idea:** IDEA-066, IDEA-067
**Wave:** 32
**Depends on:** —
**Touches:** tests/test_wave3_e2e.py, tests/e2e/test_admin_workflow.py, src/nonogram/admin/templates/batch_create.html, src/nonogram/admin/app.py
**Review score:** 9.5 (cycle 1/3)
**Started:** 2026-10-04T07:04:24Z
**Closed:** 2026-10-04T08:13:03Z
**Actual:** 0.1d
**Merge commit:** 4f3226e
**Blocked by:** —

## What to implement

Every full-suite run since wave 20 has failed the same two tests, and every gate
since has had to exclude them by hand. So no gate could demand a clean exit, and
a new failure could hide behind the two known ones. Make the full suite exit 0.

1. **`tests/test_wave3_e2e.py:366`** (IDEA-067) expects the heading "Create Batch
   from Images". f773015 (2026-09-14, Pressroom) renamed that page's heading
   "New batch". The page is right and the test is stale. CARD-156 fixed the same
   stale check in `test_db_e2e_smoke.py`; follow it.
2. **`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`**
   (IDEA-066) has been red since 89ed292 / wave 20. Nobody has diagnosed it.
   **Diagnose first.** Is it a stale expectation (the form or size fields changed
   on purpose, e.g. the (width, height) work or the batch-create redesign) or a
   real regression in how a batch applies its size configuration? Record the
   evidence (the commit that broke it, and what the test expects versus what
   the app does) in Worktree notes.
   - Stale → update the test to the current intended behaviour, keeping what it
     was there to protect.
   - Regression → fix the code, and keep the test as written.

## Acceptance criteria

- **AC-1:** `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders` passes and asserts the page's current heading ("New batch").
  *test: tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders*
- **AC-2:** `test_size_configuration_applied` passes. Worktree notes record whether the cause was a stale test or a code regression, with the commit that introduced it.
  *test: tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied*
- **AC-3:** The full suite exits 0, with no failures and no new skips or xfails.
  *test: full suite (`./.venv/bin/python -m pytest`)*

## Guardrails

- G-1: Neither test may be deleted, skipped, xfailed or loosened to pass. Each
  must still fail if the behaviour it protects breaks. Show that with a mutant
  for each.
- G-2: If IDEA-066 turns out to be a code regression, fix only that. Don't
  redesign the batch flow.
- G-3: No change to the image pipeline's conversion behaviour (`sourcing/`).

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-164` (52 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit… (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when… (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn;… (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on… (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp <… (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the… (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a… (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no… (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the… (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle… (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the… (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin… (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm… (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No… (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode)… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031,… (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's… (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5… (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is… (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns… (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the… (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** — (test hygiene; the batch flow's own FRs are unchanged)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Roadmap wave 1, the two highest-scored ideas (WSJF 24 each). Once this merges, the kanban test-gate baseline is "no failures", and every later card's gate gets stricter.
- [Env] forge 2026.8.17
- [Diagnosis IDEA-066] Stale test, not a code regression. Introducing commit: f773015 "feat(admin): adopt the Pressroom design system and fix the panel's broken flows" (2026-09-14). Evidence: the test at f773015~1 passes, at f773015 fails (`git worktree add --detach <scratch> f773015~1|f773015` + `env -u DATABASE_URL pytest tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied` → "1 passed" / "1 failed"). `git log -i -G fixed` on the step-1 templates names only f773015 (and the 96da6ac creation); its diff removes `<small class="text-muted">Adjust puzzle sizes (Fixed/Min/Max)</small>`. "Red since 89ed292 / wave 20" is when the gate first recorded it, not the cause.
- [Diagnosis IDEA-066] What the test expected vs what the app does: the test POSTed its file as `images`; `/batch/from-images` (app.py batch_from_images) reads only `image_files` and `directory` — since the test was written (c57deb5, 2026-09-08). So no upload ever happened: the route flashed "No images selected" and redirected to step 1, and the test's `b'fixed' in data.lower()` matched that page's help text. It never exercised size application. The route's size handling (`default_size` → SIZE_PRESETS → update_image_size) works and has its own coverage (tests/test_image_batch_size_fix.py).
- [Change] tests/e2e/test_admin_workflow.py::test_size_configuration_applied now uploads via `image_files` with `default_size=large` and asserts it lands on /batch/preview-images with `<option value="fixed" selected>` and `extent=30x30`. "large" (30, fixed) differs from the route's "medium" (20, fixed) fallback, so 30x30 can only come from the submitted choice. No app code changed (G-2/G-3 untouched; nothing under sourcing/).
- [Change] tests/test_wave3_e2e.py::test_batch_creation_form_renders asserts `b'<h1>New batch</h1>'`, same literal as CARD-156's fix in tests/test_db_e2e_smoke.py (9390d40).
- [Mutant] batch_create.html `<h1>New batch</h1>` → `<h1>Create batch</h1>`: test_batch_creation_form_renders FAILED — `E assert b'<h1>New batch</h1>' in b'<!DOCTYPE html>...'` (tests/test_wave3_e2e.py:368). Reverted, passes.
- [Mutant] app.py batch_from_images `default_size = request.form.get("default_size", "medium")` → `default_size = "medium"` (route ignores the submitted size): test_size_configuration_applied FAILED — `E assert b'extent=30x30' in b'<!DOCTYPE html>...'` (tests/e2e/test_admin_workflow.py:158). Reverted, passes.
- [Commit] 1dea73e test(CARD-164): bring the two weeks-red admin tests up to the current pages.
- [Handback] orchestrator handed back by harness enforcement while the implementation agent's locked full-suite run was still in progress; review cycle not started.
- [Full suite] Locked full run on 1dea73e: exit 0 — "6036 passed, 9 skipped, 15060 warnings in 555.50s (0:09:15)". No xfails; this card adds no skip/xfail markers (the 9 skips are environment-gated, pre-existing).
- [Resume] dispatcher resumed the pipeline at step 8 after the interim hand-back.
- [Build gate] PASSED (full, 555s) — implementation agent's locked run on 1dea73e: 6036 passed, 9 skipped, 0 failed, 0 xfailed. Baseline wave-31 smoke: 2 failed, 6034 passed, 9 skipped → the two targets turned green, skip count unchanged (9→9), diff adds no skip/xfail marker.
- [Scope] tests/e2e/test_admin_workflow.py, tests/test_wave3_e2e.py
- [Scope gate] in_scope — both files inside Touches; no G-3 hit (nothing under src/nonogram/sourcing/); comp_spread 0 (test files only).
- [Review 1/3] Score: 9.5 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/ (20261004T072902Z-CARD-164-cycle1.yml, yaml.safe_load OK)
- [Adversarial] no gating findings in cycle 1 — nothing to verify (F-001 Minor, F-002 out-of-scope)
- [Review 1/3] Step 8h coverage: 52/52 card rules have a verdict line (2 ✓, 0 ✗, 50 ⚠ no_eligible_fact)
- [Review 1/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Mutation check] cycle 1 (passing cycle): 8 mutants, 7 killed, 1 survived — M8 (batch_create.html select renamed default_size→size_preset) survives: the test posts field names directly to the route, nothing pins the step-1 form's names (F-001, Minor).
- [Retro] IDEA-066 test was hollow from birth: since c57deb5 (2026-09-08) it posted the dead field `images`, so it only ever saw the 'No images selected' redirect and passed on help text; f773015 removing that text merely exposed it. Five sibling tests in tests/e2e/test_admin_workflow.py (lines 86/100/112/130/170) still post `images` and pass on the redirect (F-002, out of scope → backlog candidate).
- [8h spot-check] 2/2 sampled holds reproduced (ADR-0006/R1 — diff --stat 2 test files, pyproject unchanged, tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed 1 passed; ADR-0022/R1 — no src/ change, extent=30x30 is the WxH pair from _size_fit_box.html)
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — evidence: PASSED tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders; asserts b'<h1>New batch</h1>'
  AC-2 ✓ demonstrated — evidence: PASSED tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied; stale-test diagnosis reproduced (old tests: 2 passed at 97597b1 = f773015~1, 2 failed at f773015; new test passes at both)
  AC-3 ✓ demonstrated — evidence: locked full run exit 0, "6036 passed, 9 skipped, 15060 warnings in 524.13s"; 0 failed/xfail/xpass; skips 9 = baseline 9 (1 setrlimit, 8 DATABASE_URL unset); diff adds no skip/xfail
  G-1 ✓ demonstrated — evidence: independent mutants killed (h1 → "New Batch": heading test 1 failed; default_size forced "medium": size test failed on extent=30x30; `if False and default_size in size_mapping`: failed); new assertions strictly stronger than old
  G-2 ✓ demonstrated — evidence: no app code changed; stale test confirmed by bisect pair at f773015
  G-3 ✓ demonstrated — evidence: git diff --name-only 7e57b1c...HEAD = 2 test files; nothing under src/nonogram/sourcing/
- [Docs] forge:readme on tests/ and tests/e2e/: no structure/purpose change (no file added/removed/renamed; neither README names the changed tests) — skipped as current.
- [Commit] no uncommitted code after review (cycle 1 passed with no fix); success commit = 1dea73e "test(CARD-164): bring the two weeks-red admin tests up to the current pages". Diff stat vs 7e57b1c: 2 files changed, 17 insertions(+), 6 deletions(-).
- [Merged] 2026-10-04 — 4f3226e into main (--no-ff). Rebased onto 14eb2b7 (CARD-168) cleanly → 7357658; merge gate: full suite under the lock, EXIT 0 — 6040 passed, 9 skipped, 0 failed (first clean full suite since wave 20). From now on the kanban test-gate baseline is NO failures. Deferral scan: 0 hits. F-001 (M8) and F-002 (five sibling tests post the dead `images` field) captured to backlog.
