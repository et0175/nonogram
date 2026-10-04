# CARD-176: A malformed DATABASE_URL's error never echoes text that could hold the password

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/176-scheme-of-never-echoes-a-secret
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (IDEA-016, WSJF 8.0; CARD-148 review finding F-001)
**Idea:** IDEA-016
**Wave:** 33
**Depends on:** —
**Touches:** src/nonogram/db/session.py, tests/test_db_url_driver.py
**Review score:** 9.5 (1 cycle)
**Started:** 2026-10-04T14:28:25Z
**Closed:** 2026-10-04T14:52:39Z
**Actual:** 0.1d
**Merge commit:** 62ea1eb
**Blocked by:** —

## What to implement

`normalized_url` (`src/nonogram/db/session.py:69`) turns any parse failure into
a `RuntimeError` whose message names the scheme, taken from
`_scheme_of` (`session.py:133`). `_scheme_of`'s docstring promises the value
is "a scheme or nothing at all — never a password".

**Current behaviour (verified by reading and running the code).**
`_scheme_of` returns everything before the first `://`. So text placed before
the separator comes back verbatim and lands in the error message:

- `"postgresql:hunter2://h/db"` → `'postgresql:hunter2'`
- `"hunter2@h://x/db"` → `'hunter2@h'`
- `"u:hunter2@h://x"` → `'u:hunter2@h'`

**Target behaviour.** `_scheme_of` returns text only when it is a real URL
scheme. Otherwise it returns a placeholder.

- Take the text before the first `://`, then the part of that before its first
  `:`.
- Return it only if it matches RFC 3986 scheme grammar,
  `[A-Za-z][A-Za-z0-9+.-]*` (this also admits `postgresql+psycopg2`).
- Otherwise return a fixed placeholder such as `"<malformed scheme>"`. Keep
  `"<no scheme>"` for "no `://` at all" and `"<not a string>"` for non-strings.
- Keep it total: it must not raise for any input (its docstring says why).
- Update the docstring so it is true again.

The idea text proposes only `scheme.partition(':')[0]`. That fixes the named
example but **not** `"hunter2@h://x/db"`, where no `:` precedes the secret.
The grammar check closes both. AC-1's corpus must include that shape so the
weaker fix fails.

## Acceptance criteria

- **AC-1:** Given a seeded corpus (stdlib `random.Random`, fixed seed, ≥ 500 cases, the minimum asserted inside the test) of malformed `DATABASE_URL` strings, each built from a scheme drawn from a fixed list plus a random secret inserted at a random position after the first character — between the scheme and `://` (with and without a `:` before it), in userinfo, host, port, path, query, and before `://` behind an `@` with no `:` — when `normalized_url` raises, then the secret appears in neither `str(error)` nor the rendered traceback, and the echoed scheme is exactly one of the corpus's scheme list or a placeholder. The test also asserts that every insertion position actually occurs in the corpus.
  *test: PropertyTest_DbUrl_MalformedUrlErrorNeverEchoesASecret (in tests/test_db_url_driver.py)*
- **AC-2:** Given `"postgresql:hunter2://h/db"` and `"hunter2@h://x/db"`, when `normalized_url` raises, then `hunter2` is not in the message, and the message still says `DATABASE_URL`.
  *test: TestDbUrl_SchemeOfEchoesOnlyARealScheme (in tests/test_db_url_driver.py)*
- **AC-3:** Given a well-formed scheme with a broken rest (e.g. `"postgresql://panel:pw@db:notaport/nono"`), when `normalized_url` raises, then the message still names `'postgresql'`, so the error stays actionable.
  *test: TestDbUrl_SchemeOfEchoesOnlyARealScheme (in tests/test_db_url_driver.py)*

## Guardrails

- G-1: Valid URLs normalise exactly as today. CARD-148's `TestDbUrl_NormalisationChangesNothingElse` and `TestDbUrl_DriverIsNamedNotInherited` pass unchanged.
- G-2: The handler stays incapable of raising. `_scheme_of` is still computed before the `try`, stays total, and the error is still raised `from None`. `test_an_unparseable_url_is_rejected_without_quoting_the_password` and `test_a_non_string_cannot_resurface_sqlalchemys_url_echoing_message` pass unchanged.
- G-3: Only `_scheme_of` and its docstring change in `session.py`. No change to `_init_engine`, engine options, the driver normalisation, or any database.
- G-4: ADR-0006/R1. No new runtime dependency; the test uses stdlib `random`, not hypothesis.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-176` (46 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scala… (check: review-lens)
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

- **FR:** — (operational defect; no FR, as for CARD-148)
- **EC:** CARD-148 EC-1 (the password never reaches a log or an exception message)
- **ADR:** ADR-0006/R1 (dependency baseline)
- **Components:** COMP-009, COMP-010
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-016 (tech-debt, WSJF 8.0), from CARD-148 review finding F-001 (`meta/kanban/cards/CARD-148.md`, Worktree notes, "Minor findings").
- [Fact] `_scheme_of` is at `src/nonogram/db/session.py:133-149`; its only caller is `normalized_url` at `session.py:115`, computed before the `try` on purpose (G-2).
- [Fact] Existing parametrised test `test_an_unparseable_url_is_rejected_without_quoting_the_password` (`tests/test_db_url_driver.py:772-830`) puts the secret only after `://`, which is why F-001 survived. Its `no-scheme` case (`"://panel:…"`) currently echoes `''`; under the grammar check it becomes the placeholder. That test asserts only `"DATABASE_URL" in message`, so it needs no edit.
- [Fact] Checked with the current code: the one-line `partition(':')[0]` fix still returns `'hunter2@h'` for `"hunter2@h://x/db"`. Use the grammar check.
- [Limit] A secret that IS the leading token (`"hunter2://…"`, `"hunter2:x://…"`) is indistinguishable from a scheme and is out of scope. AC-1's corpus never puts the secret at position 0. For `"panel:pw@h://x"` the echo is the username `panel`, which EC-1 does not treat as secret.
- [Env] forge 2026.8.17
- [Impl] `_scheme_of` (src/nonogram/db/session.py) now cuts the pre-`://` text at its first `:` and returns it only if it matches RFC 3986 `[A-Za-z][A-Za-z0-9+.-]*` (checked with inline ASCII character sets, no new import or module constant — G-3); otherwise `"<malformed scheme>"`. `"<no scheme>"` / `"<not a string>"` kept; still total and still computed before the `try` (G-2). Docstring rewritten to state the [Limit] honestly (leading-token secret, scheme-chars-only secret glued to the scheme, and a username before `:` are echoed) — each claim pinned by a case in the unit test below.
- [Impl] Tests per AC (tests/test_db_url_driver.py): AC-1 → `test_PropertyTest_DbUrl_MalformedUrlErrorNeverEchoesASecret` (module-level function, following the repo's `test_PropertyTest_*` convention because pytest does not collect a `PropertyTest_` class); seed 176, 8 insertion positions × 90 = 720 cases, all raising; asserts ≥ 500 *raising* cases, every position present among them, the secret absent from `str(error)` and `traceback.format_exception(error)`, echoed scheme ∈ corpus schemes ∪ placeholders, and that the `@`-shape is reached with both an alphanumeric and a punctuated secret. Secrets carry the marker `QXSECRET`, never sit at position 0, and in the `scheme-glued` position always carry a non-scheme character (else they are the [Limit] case). AC-2 → `TestDbUrl_SchemeOfEchoesOnlyARealScheme::test_text_before_the_separator_that_holds_a_secret_is_not_echoed`; AC-3 → `TestDbUrl_SchemeOfEchoesOnlyARealScheme::test_a_well_formed_scheme_with_a_broken_rest_is_still_named`; plus `TestDbUrl_SchemeOfEchoesOnlyARealScheme::test_scheme_of_returns_a_grammatical_scheme_or_a_placeholder` (grammar edges + documented limit). Existing CARD-148 tests untouched (G-1, G-2). File: 56 passed.
- [Impl] Mutation: M1 `partition(':')[0]` with no grammar → caught by AC-2 test [secret-behind-an-at], AC-1 property, unit test. M2 return raw pre-`://` text → caught by AC-2 (both), AC-1 property, unit test. M3 grammar admits `@` → caught by AC-2 [secret-behind-an-at], AC-1 property (alnum secret in the `@` position), unit test. M4 drop leading-letter check → caught by unit test [1postgres]. M5 no `:` cut → caught by unit test [postgresql:hunter2, u:hunter2]. M6 always placeholder → caught by AC-3 test (both) and unit test. M7 drop emptiness guard → caught by unit test [://panel] and CARD-148's [no-scheme] case (IndexError). Every new test fails on at least one mutant; all reverted.
- [Scope] src/nonogram/db/session.py, tests/test_db_url_driver.py
- [Build gate] impact underivable (test_scope: full) — full suite
- [Build gate] PASSED (full, 597s) — 6102 passed, 9 skipped
- [Scope gate] IN_SCOPE cycle 1 — 2 files, both in Touches; no guardrail hits; no comp spread
- [System contract] fresh lens == card section (46 rules) — no refresh
- [Review 1/3] Score: 9.5 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: 46/46 card rules named (1 ✓, 45 ⚠ no_eligible_fact); count line present
- [Review 1/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Review 1/3] mutation check: 6/6 mutants killed (reviewer, passing cycle)
- [8h spot-check] 1/1 sampled holds reproduced (ADR-0006/R1 — diff touches no manifest, only new import stdlib ast, test_the_dependency_baseline_is_still_closed 2 passed)
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — evidence: PASSED tests/test_db_url_driver.py::test_PropertyTest_DbUrl_MalformedUrlErrorNeverEchoesASecret (seed 176, 720 cases all raising, ≥500 asserted in-test, all 8 positions asserted, secret absent from str(error) and format_exception, echo ∈ schemes ∪ placeholders)
  AC-2 ✓ demonstrated — evidence: PASSED TestDbUrl_SchemeOfEchoesOnlyARealScheme::test_text_before_the_separator_that_holds_a_secret_is_not_echoed[secret-behind-a-colon] and [secret-behind-an-at]
  AC-3 ✓ demonstrated — evidence: PASSED TestDbUrl_SchemeOfEchoesOnlyARealScheme::test_a_well_formed_scheme_with_a_broken_rest_is_still_named[bare-scheme] and [scheme-with-driver]
  G-1 ✓ demonstrated — evidence: TestDbUrl_DriverIsNamedNotInherited + TestDbUrl_NormalisationChangesNothingElse PASSED; git diff main...HEAD -- tests/ has no '-' lines
  G-2 ✓ demonstrated — evidence: test_an_unparseable_url_is_rejected_without_quoting_the_password (7 params) + test_a_non_string_cannot_resurface_sqlalchemys_url_echoing_message PASSED; _scheme_of still before try, raise … from None unchanged
  G-3 ✓ demonstrated — evidence: diff --name-only = session.py + test file; session.py 2 hunks, both inside _scheme_of (docstring + body)
  G-4 ✓ demonstrated — evidence: pyproject.toml not in diff; only new import stdlib ast (test); corpus uses random.Random; no hypothesis
- [Docs] forge:readme on changed dirs: src/nonogram/db/ — no file added/removed, no purpose change, no README exists (per-directory README convention is an open owner decision) — skipped; tests/ — no file added/removed, tests/README.md current — skipped
- [Commit] success commit cdc3ade (the implementation commit — review cycle 1 passed with no fix and no README change, so /commit had nothing further to stage; meta/ excluded). Open Minor: F-001 bare leading-token limit (hunter2://) has no pinning case; F-002 AC-1 echo check accepts any corpus scheme, not the case's own. Out-of-scope F-003: leading whitespace now reports <malformed scheme> (less operator hint). Card stays review until done.
