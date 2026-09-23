# CARD-130: Books reopen into the step workflow — all five steps linked whatever the status, general info edits in place

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/130-book-step-workflow-reentry
**Worktree:** ../PythonProject4-CARD-130
**Source:** meta/architecture/handoff.md#increment-16 (FR-038 navigation half)
**Idea:** —
**Wave:** 25
**Depends on:** CARD-123, CARD-124
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_detail.html, src/nonogram/admin/templates/books_list.html, src/nonogram/admin/templates/book_create.html, src/nonogram/admin/templates/_stepper.html, tests/test_book_workflow_steps.py
**Review score:** 9.0 (cycle 3/3)
**Started:** 2026-09-23
**Closed:** 2026-09-23
**Actual:** 1d
**Merge commit:** a101db1
**Blocked by:** —

## What to implement

1. **Opening a book from `/books`** lands in the step workflow. The page reached carries
   the same `_stepper.html` navigation as creation.
2. **The detail page links to all five steps**: general info, Print setup, Puzzle
   selection, Arrangement, Finalise. These links appear **whatever the book's status**.
3. **General info edits an existing book.** A `GET/POST /book/<id>/edit` (or a reused
   `book_create.html` in edit mode) edits the New-book fields and stores them. Creation
   is unchanged.
4. **Every step renders for every status** (HTTP 200, no redirect or refusal just
   because of status). Remove any status guard on step GETs. What a *published* book may
   *change* is CARD-131's confirmation, not a refusal to render.
5. Stepper: the current step shows as "current". A book being revisited shows every
   step as reachable (components.md Stepper states: done · current · upcoming).

## Acceptance criteria

- **AC-222** — given a book in status pdf_generated, when its detail page is rendered, then the page carries a link to each of the five steps — general info, Print setup, Puzzle selection, Arrangement, Finalise.
  *test:* `TestBookDetail_LinksToEveryStep`
- **AC-223** — given a draft book listed on /books, when the owner opens it from the list, then the page reached carries the same step navigation as the creation workflow.
  *test:* `TestBooksList_OpensBookInStepWorkflow`
- **AC-224** — given an existing book titled "Winter Animals", when its general-info step is submitted with the title "Winter Birds", then the stored title is "Winter Birds".
  *test:* `TestBookGeneralInfo_EditsExistingBook`
- **AC-225** — given a book in status ready_for_kdp, when its puzzle-selection step is requested, then the step renders with HTTP 200 rather than a redirect or refusal.
  *test:* `TestBookSteps_ReachableWhateverStatus`

## Guardrails

- G-1: No schema change (Increment 16 Rollback: "Additive routes and template changes … No schema change"). Do not edit `src/nonogram/db/**` or `migrations/**`.
- G-2: Revisiting a step never discards selection, order or custom titles (EC-026). A GET changes nothing.
- G-3: The published-book membership rule is not changed here. That is CARD-131 (INV-008).
- G-4: Do not edit `src/nonogram/admin/book_pdf_generator.py` (owned by CARD-127 this wave) or `src/nonogram/admin/book_proof.py` / `src/nonogram/admin/templates/book_setup_print.html` (owned by CARD-118 this wave).

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

- **FR:** FR-038 (AC-222..AC-225)
- **NFR:** —
- **ADR:** ADR-0033
- **Components:** COMP-009, COMP-010 (reads only)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** Stepper (reuse — one macro, never hand-copied; linked for every step on revisit), PageHeader (reuse), FormField (reuse on general-info edit), DataTable (reuse — books list row link target)
- **Screens:** /books, /book/<id>, /book/<id>/edit (general info), every step page's stepper
- **Standards:** forge:engineering-standards §11

## Worktree notes

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

### What was built

The stepper macro carries the whole design. `book_steps(current=None, links=None)`
now matches `current` against a step **key** and prints the step's **position**
in the list. The keys are the four the list already had — Print setup is 1 here
as it was before general info joined — so every page that already called the
macro keeps its own call byte-for-byte while the list it renders grows to five
and the printed numbers run 1..5. That is what let `book_setup_print.html` stay
untouched under G-4: its `book_steps(1)` still names Print setup.

Left without `links`, the macro asks a new Jinja **global**, `book_step_links()`,
for the five URLs of the book in the request's own path (`request.view_args`).
A global rather than a context processor: every page imports `_stepper.html`
*without context*, which puts a context processor's names out of a macro's reach
and leaves a global's within it. So a step page links its four siblings without
its template being edited to pass anything — the mechanism that made G-4
satisfiable rather than conflicting.

`GET/POST /book/<id>/edit` is the general-info step: it renders
`book_create.html` in edit mode (`book` in the context) rather than a second
copy of the same form, and stores through the new
`BookManager.update_book_details`. Creation and revision now share one
statement of the rules — `_refuse_invalid_details`, extracted from
`create_book` — so the step cannot store what creation would have refused.
Nothing else about the book moves: not status, plan, membership, order, titles
or print columns. Naming a book is not a membership change, so INV-012's return
to draft is deliberately not triggered here.

`book_detail.html` carries the list with **no** step current (the page is the
book, not one of its steps), so all five render as links whatever the status —
AC-222 — and opening a book from /books lands in the workflow rather than beside
it — AC-223. The `{% if book.status == 'draft' %}` guard on "Continue
scaffolding" is gone for the same reason.

AC-225 needed no code change: no step GET was gated on status to begin with (the
only guard is "book not found"). The tests now hold that open across the whole
`BookStatus` enum × all five steps, so a future status guard fails the suite.

No CSS was added. `.stepper` already styles `is-done`/`is-current`, and the
`batch_steps` twin has rendered anchors inside it since the design system, so
the links inherit both the link styling and the global `a:focus-visible` ring
(§11 a11y). Ladder step 4 — reuse — not step 7.

### SCOPE+ (edits outside the card's Touches)

- `SCOPE+ src/nonogram/admin/book_manager.py` — the general-info step needs a
  domain setter for the four fields; none existed (only `set_cover_image`,
  `set_pdf_url`, `set_kdp_asin`). Putting the write in the route would have put
  domain rules in an inbound adapter (ADR-0019). Two changes only: the new
  `update_book_details`, and `create_book`'s four validation lines lifted into
  the module-level `_refuse_invalid_details` both now call.
- `SCOPE+ src/nonogram/admin/templates/book_select_puzzles.html` — this page has
  imported `_stepper.html` since it was written but never called the macro, so
  it was the one step of the flow with no way out of it. Added the same
  `Steps` card the sibling step pages carry, holding `stepper.book_steps(2)`.
  Nothing else in the file was touched.

The other three step templates (`book_setup_print.html`,
`book_arrange_puzzles.html`, `book_finalize.html`) needed **no** edit at all —
see the key/position split above — and were not touched. G-4 and G-1 hold:
`book_pdf_generator.py`, `book_proof.py`, `book_setup_print.html`,
`src/nonogram/db/**` and `migrations/**` are all untouched.

### Known stale copy (not fixed here — deliberately)

The four step pages' prose still reads "Step N **of 4**"
(`book_setup_print.html` L12, `book_select_puzzles.html` L24,
`book_arrange_puzzles.html` L13, `book_finalize.html` L12, plus their
`{% block section %}` "· step N" lines). With general info now a step they are
one out: Print setup is step 2 of 5. This is **not** an AC or a guardrail
conflict — every AC passes — it is copy that a fifth step made stale.
`book_setup_print.html` is owned by CARD-118 this wave (G-4) and cannot be
fixed here at all, and fixing the other three would have left one page
disagreeing with three instead of four agreeing with each other, so all four
were left alone. Whoever next owns those files should renumber them to "of 5";
it is a one-line change per page. Logged for the wave, not blocking.

### Verification

Full suite from the worktree root:
`4763 passed, 26 skipped, 1 deselected in 277s`. The one deselection is the
known pre-existing failure
`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`,
which is not this card's. `tests/test_book_workflow_steps.py` is 77 tests,
all green; the CARD-113 golden A4 tripwire was neither regenerated nor edited.

The rendered markup of all five step pages plus `/book/<id>` and `/book/create`
was read back (there is no browser harness in this repo): each step page marks
itself `is-current` with `aria-current="step"`, offers exactly the other four as
links, and `/book/create` — which has no book yet — still renders the plain,
unlinked list it always did.

Note for anyone running the panel by hand from a worktree: the venv's editable
install points at the **main** checkout, so an ad-hoc `python -c` imports the
main repo's `nonogram`. Use `PYTHONPATH=<worktree>/src`. pytest is unaffected
(`pythonpath = ["src"]` in `pyproject.toml`).

### Handover

- [Handover from CARD-130, 2026-09-23] **The stepper's contract**, for CARD-131
  (confirm-before-change) and CARD-132 (the books list).

  `{% import '_stepper.html' as stepper %}` then `stepper.book_steps(current,
  links)`. Both arguments are optional.

  * **`current`** — the step's **key**, an int, *not* the number printed on the
    screen. The keys are fixed: `0` general info, `1` Print setup, `2` puzzle
    selection, `3` arrangement, `4` finalise & export. The printed number is the
    step's position in the list (`loop.index`, 1..5), which is why Print setup
    is key `1` and shows as "2". Do not renumber the keys — four step templates
    pass them literally, and `TestBookStepper_KeysAreTheOnesTheStepPagesStillPass`
    reads those templates on disk and fails if a call and its step drift apart.
    `current=None` (the default) means "this page is beside the flow, not in
    it" — the book's detail page — and is the only way to render five links
    with nothing current.
  * **`links`** — a mapping `{step key: URL}`. A step is a link when
    `n != current and links.get(n)`; the current step is never a link. Passing
    `{}` renders every step as plain text (that is what `/book/create` gets,
    since there is no book to link to yet). **Omitted or `None`** — the normal
    case — the macro calls the Jinja global `book_step_links()` itself.

  `book_step_links(book_id=None)` is registered with `@app.template_global()` in
  `create_app`, next to the book routes. With no argument it reads `book_id`
  from `request.view_args`, so it follows the **page**, not the render call, and
  returns `{}` when the path carries no book. Pass `book_id` explicitly to get
  another book's links. The endpoints it maps are in `_BOOK_STEP_ENDPOINTS`
  (`edit_book`, `setup_print`, `select_puzzles_for_book`,
  `arrange_puzzles_in_book`, `finalize_book`) and the URLs come from `url_for`,
  so a route rename moves the links with it. It must stay a **global**: a
  `@app.context_processor` name is invisible inside a macro imported without
  context, which is how every page imports this one.

  **Status does not enter any of this.** A book's status maps to step
  availability not at all: every step of a book that exists is linked and
  renders 200 at every status, draft through published. That is deliberate and
  is AC-225 — what a published book may *change* is CARD-131's confirmation,
  applied to the change itself, never a refusal to render or to link the step.
  If CARD-131 needs the stepper to say something about a published book, add it
  as a marker beside the step, not as a removed link.

  **State rendering**, for CARD-132 if it reuses the list: `is-done` when
  `current is not none and n < current`, `is-current` when `n == current` (plus
  `aria-current="step"`), otherwise neither — the upcoming state. `current=None`
  therefore yields no done and no current at all.

  **For CARD-132 specifically**: `/books` rows link to `/book/<id>`, and that
  page now carries the step list, so the list already opens a book "in the
  workflow" (AC-223) without the list itself linking to a step. If CARD-132
  wants per-row step links it can call `book_step_links(book.book_id)` in the
  template — it takes an explicit id for exactly that.

  **For CARD-131 specifically**: `BookManager.update_book_details` is a
  general-info write, not a membership change, and deliberately does **not**
  return a non-draft book to draft (INV-012 is about membership). It is also the
  only book write that touches the four title/description/theme/target_audience
  fields — if a confirmation gate ever has to cover renames, that is the one
  seam.

- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/templates/_stepper.html, src/nonogram/admin/templates/book_create.html, src/nonogram/admin/templates/book_detail.html, src/nonogram/admin/templates/book_select_puzzles.html, tests/test_book_workflow_steps.py
- [Build gate] PASSED (full, 253s) — 4763 passed, 26 skipped, 0 failed; the known pre-existing tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied deselected. CARD-113 golden A4 tripwire untouched by the diff and green.
- [Scope gate] ⚠ grown: 2 files outside Touches (src/nonogram/admin/book_manager.py, src/nonogram/admin/templates/book_select_puzzles.html — both declared SCOPE+ by the implementation). No guardrail hit: src/nonogram/db/**, migrations/**, book_pdf_generator.py, book_proof.py and book_setup_print.html are all absent from the diff. No sibling poached (CARD-134's Touches do not intersect). comp_spread not measurable — trace.yml carries no components[].code mapping.

- [Visual] captured 16 screenshots (cycle 1) — all 8 screens x desktop 1440x900 + mobile 390x844, light only (tokens.css declares no dark block). Panel booted from the worktree against a throwaway SQLite DB (never nonogram_admin.db, never Postgres nonogram_poc); every one of the 8 screens returned HTTP 200 for a pdf_generated book. runtime.log: 0 console.error, 0 console.warning, 0 pageerror, 0 requestfailed, 0 sub-resource >= 400 across 16 loads; the Flask log served 173 requests with no traceback and no 4xx/5xx. a11y scan unavailable (@axe-core/playwright not installed — no node e2e scaffold in this repo); no meta/design/baselines/ yet, so no visual diff. Owner copy in ~/Documents/nonogram-reviews/CARD-130/.
- [Visual] ⚠ capture side effect: playwright + chromium were installed into the shared .venv to get a real runtime log. pyproject.toml was NOT touched and ADR-0006/R1's check reads the manifest, not the venv, so the declared baseline is intact — but the owner may want to `pip uninstall playwright` afterwards.

- [Review 1/3] Score: 7.0 — crit: 0, imp: 2. Step 8h covered all 44 card rules by id (7 ✓ holds, 37 ⚠ unchecked — 35 no_eligible_fact, INV-008 + INV-012 check_ref_missing because CARD-131 has not been built yet, 0 ✗ violated). All four ACs judged met, all four guardrails judged held (G-4: no guarded path in the diff).
- [Adversarial] F-001 "Step N of 4 beside a 1..5 stepper" CONFIRMED — the skeptic re-derived it from `git show main:_stepper.html` (the number printed was the key over a 4-list; it is now loop.index over a 5-list), so "of 4" was correct BEFORE this commit and this card made it wrong; both contradictions verified visible on one screen in the PNGs. Three of the four stale templates are unguarded; only book_setup_print.html is G-4.
- [Adversarial] F-002 "edit route's refusal path discards the owner's input" CONFIRMED — the skeptic could not refute it and proved it empirically against the worktree: POST /book/<id>/edit with a whitespace-only title plus description "KEEP-ME-1234" returns 200 with 'KEEP-ME-1234' in html = False and the stored values re-rendered. Branch is browser-reachable (three of four fields carry only `required`, which accepts "   ", while _refuse_invalid_details rejects it). Storage is correctly untouched — the defect is purely the lost input.
- [Severity gate 1/3] Score 7.0 below min_score 8 AND 2 confirmed important findings — fix mandatory.
- [Review sync] 1 report(s) → meta/review/20260923T135716Z-CARD-130-cycle1.yml

- [Fix 1] FIXED F-001 (test: TestBookStepPages_ProseAgreesWithTheStepper) · F-002 (test: test_a_refused_submission_carries_the_owner_s_entries_back) · F-003 (test: test_a_missing_theme_is_refused_not_defaulted) · F-004 (test: test_the_form_offers_exactly_the_domain_s_themes) · F-005 (test: n/a — design-system prose). Fix pre-gate: all four named tests exist and pass (14 tests, exit 0).
- [Fix 1] declarations: 4 updated, 3 confirmed, 1 none. Updated — the [Handover from CARD-130] contract re-derived for BOOK_STEPS + book_step_number/book_step_count/book_step_of, the `edit_book` docstring (its "the page comes back with the book as it still stands" claim WAS the defect), meta/design/components.md's Stepper entry (five steps, two state axes, status in neither) and its stale ArrangeRow "(step 3)". Confirmed still correct — the `links`/`book_step_links` paragraph, the status paragraph, and the CARD-131 `update_book_details` paragraph. None — F-004 (only the constant's fan-in changed). Verified on disk: the card's Handover now names the new macros; book_steps' signature and key->position mapping are unchanged, so CARD-131/132's contract still holds.
- [Build gate] PASSED (full, 240s) — 4777 passed, 26 skipped, 0 failed (14 new tests since cycle 1). Golden A4 tripwire untouched and green.
- [Visual] captured 18 screenshots (cycle 2) — the 8 screens plus a NEW refusal screen for F-002. runtime.log: 0 error-class lines, all 9 screens HTTP 200, Flask served 84x200 + 36x304 with no traceback. Renumbering verified in the rendered prose: general info "Step 1 of 5", puzzle selection "Step 3 of 5", arrangement "Step 4 of 5" (+ the two in-body cross-references now "step 3" / "step 5"), finalise "Step 5 of 5". A grep of all rendered HTML finds "of 4" on exactly ONE page — book_setup_print.html, the G-4 guarded exception. F-002 proven visually: the refusal renders 200 with "KEEP-ME-1234", the submitted audience AND the submitted (not stored) theme carried back, under a visible "Error: Title cannot be empty".
- [Visual] cycle-1 vs cycle-2 per-pixel diff: every screen the fix should NOT have touched diffs at exactly 0.000% (general info, print setup, book create — both viewports); every non-zero diff is either the renumbering itself or throwaway-seed UUID/timestamp data confirmed by crop. layout-probes.txt is byte-identical between cycles — no new overflow, no layout shift, no new breakage.
- [Scope gate] cycle 2 re-measured: 9 code files, 4 outside Touches (book_manager.py, book_select_puzzles.html, book_arrange_puzzles.html, book_finalize.html — all declared SCOPE+) = 44% -> still GROWN, no guardrail hit, no sibling poached. Confirmation mode therefore NOT eligible this cycle (it requires IN_SCOPE) — cycle 2 runs as a FULL review.

- [Review 2/3] Score: 8.5 — crit: 0, imp: 1. All five cycle-1 findings re-derived as ✓ resolved from evidence (F-001 proven by the rendered prose + the per-pixel diff, F-002 proven by the refusal screenshot carrying KEEP-ME-1234, the submitted audience and the submitted theme). Step 8h covered all 44 card rules (10 ✓ holds, 34 ⚠ unchecked — 32 no_eligible_fact + INV-008/INV-012 check_ref_missing, 0 ✗ violated). Scope excess judged NECESSARY — no scope finding. Reviewer independently verified the fix's two claims: book_steps' signature and key->position mapping are unchanged (so CARD-131/132's Handover contract holds), and book_setup_print.html is untouched.
- [Review 2/3] Step 8h checked the same 44 ids the card's section names — no surplus, no gap.
- [Review sync] 2 report(s) → meta/review/ (…-CARD-130-cycle1.yml, …-CARD-130-cycle2.yml)
- [Severity gate 2/3] Score 8.5 meets min_score 8, but 1 important finding remains — fix mandatory; the success path stays closed.
- [Family] not a family regression: the cycle-2 Important IS attributed to the cycle-1 F-002 fix (it added the refusal render path without the invalid-field marking), so the streak is 1 — escalation needs 2 consecutive cycles in one family. Watch it: if the next cycle raises another finding about the refusal form's own markup, that is the family and it escalates.
- [Merge note] the worktree branches from 89facec, which predates CARD-118's merge into main (8765b91 / 2782887). `git diff main` therefore also shows an unrelated CARD-118 reversion — an artifact of the branch point, not this card's work; the real diff is `git diff 89facec`. CARD-118 also edited src/nonogram/admin/app.py, so the dispatcher's rebase should be checked there; this card's app.py edits are confined to the book-routes region (the book_step_links/book_themes globals and the edit_book route).

- [Adversarial] F-006 "the refusal screen leaves the rejected field unmarked" CONFIRMED — the skeptic attacked it on all six axes and broke none. components.md:89-94 enumerates `invalid (danger border + hint)` as a FormField state and its `Used by:` line names book create explicitly; book_setup_print.html:104-106/113-116/140-144 already implements the pattern end-to-end via `_PlanFormError.fields` (machinery CARD-120's own review cycle paid for). The route is this card's new code (89facec has no edit_book), and the F-002 carry-back is what turns a latent gap into a visibly blank, unmarked box. One correction to the finding: base.html:42 does render the flash with role="alert" naming the field, so it is not "no cue at all" — it is no programmatic association and no visual marking. Fix cost ~40-60 lines; note that aria-describedby parity needs an in-page error region on book_create.html, since base.html's shared flash stack emits no stable id (do NOT widen to base.html).
- [Review 2/3] stalled check: Δscore +1.5 (7.0 → 8.5) ≥ min_improvement 0.5 — progressing, not stalled.

- [Fix 2] FIXED F-006 (tests: test_a_refused_edit_marks_exactly_the_offending_field, test_a_saved_submission_marks_nothing, test_the_create_screen_is_untouched_by_the_marking) · F-007 book_step_count fan-in · F-008 create lede derived · F-009 route docstrings now NAME their step · F-010 tautological theme assertion · F-011 corpus 302/theme literal · F-012 truthiness→is-not-none · plus F-105 (the Handover's breadcrumb sentence made true). Fix pre-gate: all 10 named tests exist and pass (21 tests, exit 0).
- [Fix 2] declarations: 5 updated, 2 confirmed, 4 none. The error-classification change is the substantive one — `_refuse_invalid_details` raised four bare ValueErrors and now raises `book_manager.InvalidBookDetails(message, field)`, a ValueError SUBCLASS carrying `fields: frozenset`, mirroring `_PlanFormError.fields`. Re-derived: the docstrings of `_refuse_invalid_details`, `create_book`, `update_book_details` and `edit_book`, the Handover note (a new cycle-2 block under "For CARD-131 specifically" recording how a refused general-info write is classified), and components.md's FormField + Stepper entries. Confirmed rather than changed: `create_book`'s existing `except ValueError` still catches the new type (proven live by test_the_create_screen_is_untouched_by_the_marking), and the three stepper macros' signatures are unchanged. A grep of src/tests/docs found no error or flash text still asserting the old shape.
- [Build gate] PASSED (full, 228s) — 4792 passed, 26 skipped, 0 failed. Golden A4 tripwire green, neither regenerated nor edited.
- [Scope] SCOPE+ src/nonogram/admin/static/admin.css — one rule inside the existing form block giving .form-control.is-invalid / .form-select.is-invalid `border-color: var(--color-danger)` so the marking paints the design system's red rather than Bootstrap's; the exclamation glyph is kept as the non-colour cue. Side effect worth knowing: this also corrects Print setup's own fields WITHOUT book_setup_print.html being touched — G-4 guards that template, not the shared stylesheet.
- [Review sync] 2 report(s) re-synced → meta/review/ (the cycle-2 YAML now carries status: fixed on its findings)

- [Visual] captured 20 screenshots (cycle 3) — 10 screens x 2 viewports, incl. two new probes (the general-info refusal and a /book/create refusal). runtime.log: 0 error-class lines across 20 loads, all 10 screens HTTP 200 on both viewports, Flask stderr free of tracebacks. F-006 proven directly: exactly ONE control carries is-invalid (#title), aria-invalid="true", aria-describedby="general-info-error" which RESOLVES in the DOM, computed border rgb(155,59,38) = --color-danger, Bootstrap's exclamation glyph kept as the non-colour cue, and #general-info-error present with role="alert". The submitted theme (halloween) is carried back, not the stored one (christmas). Creation is inert on BOTH the clean and the refused create screen: 0 marked controls, no error region. Focus ring survives the new border rule (outline 2px rgb(31,95,91)).
- [Visual] cycle-2 vs cycle-3 diff: of the six screens the fix should not have touched, print setup / arrangement / finalise are pixel-identical (0.000%) on both viewports and the other three differ only in throwaway-seed UUID text confirmed by crop. Nothing UNEXPECTED anywhere. layout-probes.txt is byte-for-byte identical across all three cycles — no new overflow, no layout shift. "of 4" now renders on exactly one page in the whole product: book_setup_print.html, the G-4 guarded page (its breadcrumb says "step 1" too).

- [Review 3/3] Score: 9.0 ✓ threshold reached + no critical/important. All eight cycle-2 findings re-derived as ✓ resolved from evidence, not from the fix agent's claim. Step 8h covered all 44 card rules (9 ✓ holds, 35 ⚠ unchecked — 33 no_eligible_fact + INV-008/INV-012 check_ref_missing, 0 ✗ violated). The reviewer independently swept all 32 `except ValueError` sites in src/nonogram/admin/ and confirmed none matches on message text or a narrower type, so the new InvalidBookDetails subclass cannot change any existing handler's behaviour; creation proven inert by both a test and the new book-create-refused probe. Certification on this stable cycle: 8g baseline-acceptance judged per screen (no unintended visual regression); 8f mutation check not run (review.mutation_check not enabled in this repo); automated a11y scan unavailable, static check done by hand and clean.
- [Review 3/3] Reviewer judged the shared admin.css SCOPE+ acceptable: G-4 guards book_setup_print.html the template, not the stylesheet, and the rule replaces Bootstrap's hardcoded #dc3545 with the --color-danger token, moving Print setup toward the design system rather than away from it.
- [Review sync] 3 report(s) → meta/review/ (…-cycle1.yml, …-cycle2.yml, …-cycle3.yml)

- [8h spot-check] ADR-0033/R1 reproduced — the skeptic re-derived update_book_details' field set in BOTH storage branches (five writes each, nothing on a puzzle and nothing on the book_id mirror), ran the cited test green (2 passed; corpus asserted at CORPUS_SIZE == 24) and swept the whole diff for puzzle-field writes, finding none. Two refinements worth carrying: (i) in memory mode the four fields live on `book.metadata.*`, not on the aggregate directly — same facts, different path; (ii) the verdict cited a GET-only, memory-mode-only test for a claim about both storage modes — the diff does contain the right one, `test_the_four_fields_are_stored_in_both_storage_modes`, parametrised over memory and db.
- [Handover addition, for CARD-131] The skeptic surfaced a write-surface consequence this card's own framing understates: because every step is now linked from every other whatever the status, a published / ready_for_kdp book can now REACH the select-puzzles and arrange-puzzles POST routes that were previously awkward to get to. Those routes write membership, order and the puzzles.book_id mirror. No rule is violated (ADR-0033/R1 permits the mirror, and AC-225 makes the reachability deliberate), but CARD-131's confirmation gate is now guarding a wider door than it was when it was cut. Size it against that.

- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-222 ✓ demonstrated — evidence: TestBookDetail_LinksToEveryStep::test_a_pdf_generated_book_links_to_every_step PASSED. Builds the book at BookStatus.PDF_GENERATED (the AC's own scenario, not a draft), GETs /book/<id>, parses the stepper and asserts all five labels AND all five step hrefs; a sibling test checks the premise that storage really reports "pdf_generated".
  AC-223 ✓ demonstrated — evidence: TestBooksList_OpensBookInStepWorkflow::test_the_page_the_list_opens_carries_the_step_navigation PASSED. The helper really GETs /books and regex-extracts the hrefs rather than hardcoding the URL; a sibling asserts the opened page's labels equal /book/create's.
  AC-224 ✓ demonstrated — evidence: TestBookGeneralInfo_EditsExistingBook::test_the_submitted_title_is_the_stored_title PASSED. Exactly the AC's scenario ("Winter Animals" -> "Winter Birds"), read back through storage; test_the_four_fields_are_stored_in_both_storage_modes repeats it in memory and against real SQLite.
  AC-225 ✓ demonstrated — evidence: TestBookSteps_ReachableWhateverStatus::test_puzzle_selection_of_a_ready_for_kdp_book_renders PASSED, asserting strictly 200; generalised to 5 steps x every status (25 cases), plus a test proving the not-found guard survived the status-guard removal.
  G-1 ✓ demonstrated — the changed-file union from base 89facec, filtered for ^src/nonogram/db/ or ^migrations/, returns nothing. Bounded: this shows the card touched no file under those globs, not that no schema statement exists elsewhere.
  G-2 ✓ demonstrated — TestBookSteps_RevisitingDiscardsNothing (both tests) PASSED. Genuinely multi-case: 24 books from a seeded random.Random(20260923), no hypothesis, `assert seen == CORPUS_SIZE` inside the test, a companion discrimination test, five step URLs + /book/<id> GETted twice in shuffled order, then membership/order/custom titles/details compared byte-equal. The diff STRENGTHENED it (302 no longer accepted); it was not renamed, retargeted or deselected.
  G-3 ✓ demonstrated — verified as a negative by four bounded checks: book_detail.html's diff contains only the stepper card and the removal of the draft-only guard (no add/remove control); app.py's add-puzzles/remove-puzzle/status routes (3649/3683/3698) lie beyond the last changed hunk (+3297); book_manager.py's add/remove membership methods lie outside every changed hunk; and update_book_details writes no status and no membership.
  G-4 ✓ demonstrated — none of book_pdf_generator.py, book_proof.py or book_setup_print.html appears in the changed-file union (book_setup_print.html: zero bytes changed). The shared admin.css rule does repaint Print setup's invalid fields, but G-4 names three files and the stylesheet is not one of them; the ownership collision the guardrail protects against cannot occur in a template nobody touched.

- [8h spot-check] CON-016 reproduced — and re-derived empirically rather than by reading. The skeptic confirmed `before_request_funcs == {None: [_refuse_what_this_panel_should_not_serve]}` (key None = app-wide) with `app.blueprints == {}`, then drove the NEW /book/<id>/edit route against five door configurations and got byte-identical refusals to the pre-existing /books: local-mode foreign Host 404/404, deployed no-credential 401/401, deployed loopback-Host-with-credential 404/404, deployed cross-site POST 403/403, deployed foreign-Origin POST 403/403, with 200/200 positive controls. A cross-site POST carrying title=hijacked did not reach the view. A full route-table diff against 89facec shows the change adds exactly ONE url rule and ZERO hooks or handlers; @app.template_global() was verified non-routable (neither book_step_links nor book_themes appears as a url_map endpoint). TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit: 9 passed.

- [8h spot-check] ADR-0035/R1 reproduced — the skeptic did not settle for reading the diff: it parsed both 89facec's app.py and the working tree with `ast`, stripped docstrings recursively and compared each of the four step routes' bodies, getting IDENTICAL(no-docstring) for all four, so "only docstrings changed" is literally true. update_book_details writes no status in either mode; TestBookStatus_EveryExitFromDraftIsGatedOnThePlan passes 30/30 and tests/test_book_ready_gate.py is not in the diff at all; `_refuse_unless_the_planned_book` appears 0 times in the diff and is still invoked from set_book_status in both modes. The only `.status =` write in the diff is the new TEST fixture helper `Shelf.force_status`, which arranges preconditions and bypasses nothing in production.
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0033/R1, CON-016, ADR-0035/R1).
- [Discoverability note, for CARD-131] The last skeptic pinned down precisely what the removed draft-only guard did and did not change: the step URLs were NEVER status-guarded server-side — only the LINK to setup-print was hidden on a non-draft book. So no POST path became reachable that could not already be reached by typing the URL; what changed is discoverability. Concretely, finalize_book's `save_and_finish` → set_book_status(READY_FOR_PDF) is now one click from a non-draft book's detail page. ADR-0035/R1 is unaffected (it governs exits FROM draft, which still run the gate; non-draft → non-draft was ungated by design), but it is the sharpest statement yet of the door CARD-131's confirmation has to cover.

- [Docs] forge:readme — no README written. src/nonogram/admin/, its templates/ and its static/ have never had one, and creating three from scratch mid-wave, in the two files three concurrent cards are editing, is a documentation project rather than this card's docs step; the package's canonical map is src/nonogram/__init__.py's docstring (CLAUDE.md), which this card does not change (no new module, no new directory — one route and three macros inside existing files). tests/README.md is a "Wave 1"-scoped document whose Test Files index already omits dozens of later test files including every test_book_*.py; adding this card's file to a stale Wave-1 index would neither make it current nor survive the siblings adding their own. Skipped as not-current-but-not-this-card's; worth a dedicated docs card.
- [Docs] meta/design/components.md carried by hand from the worktree into the main repo (meta/ is never committed from a worktree). Main's copy was unmodified since HEAD and identical to the worktree's base, so the carry-over clobbered no concurrent edit. Changes: FormField's Used-by now names the general-info step and its Notes state the three-part marking contract and the page-local error region; Stepper covers five steps plus the detail page and gains the second (reachability) axis with the explicit "status enters neither axis"; the macro note records that every printed number and count comes from _stepper.html; ArrangeRow corrected to "step 4 of 5".

- [Commit] bc11281 `fix(admin): CARD-130 review rounds on the book step workflow` — the two fix rounds, as a second commit on top of ff0c14d (the implementation). Branch tip bc11281 -> ff0c14d -> 89facec. 9 files, +645/-42, staged with explicit pathspecs; nothing under meta/, no .forge-screens/, no DB file, no egg-info, and no guarded path (book_setup_print.html, book_proof.py, book_pdf_generator.py, db/**, migrations/**) in either commit. ff0c14d was not amended.
- [Commit] a forge hook fired non-blockingly on commit: "source files changed — how-it-works docs may be stale. -> /forge:explain [aspect]". Left for the dispatcher's post-wave docs step; this card's per-directory docs decision is the [Docs] note above.
- [Review sync] fixed_in: bc11281 backfilled into the cycle-1 and cycle-2 report YAMLs in the main repo (forge:commit skipped it, correctly, because those files live under meta/ in the worktree where it was told to touch nothing).

- [Done] Merged a101db1 on 2026-09-23. Review 9.0 (3 cycles: 7.0 -> 8.5 -> 9.0), 0 critical /
  0 important at close; all three gating findings adversarially confirmed and fixed. Three
  full-suite runs, all green (4792 passed at close). Golden tripwire untouched and green.
  AC-222/223/224/225 and G-1..G-4 demonstrated. G-4 fully intact: zero bytes changed in
  book_setup_print.html.
- [SCOPE+] Five files beyond Touches, all judged necessary: book_manager.py (ADR-0019 — no
  domain write in the adapter), book_select_puzzles.html (imported the stepper but never
  called it), book_arrange_puzzles.html + book_finalize.html (forced by the renumbering
  fix), static/admin.css (one rule tokenizing the invalid border). books_list.html was in
  Touches but NOT needed — AC-223 holds because the list already links /book/<id>.
- [Handover -> CARD-131 / CARD-132] `book_steps(current=None, links=None)`: `current` is a
  step KEY (0 general info .. 4 finalise), the printed number is `loop.index`;
  `current=None` means "beside the flow" (detail page: five links, nothing current); links
  default from the `book_step_links()` Jinja global, which MUST stay a global — context
  processors are invisible in macros imported without context. Status maps to step
  availability NOT AT ALL, deliberately (AC-225).
- [Handover -> CARD-131, size against this] Every step is now linked from every other, so a
  published book can reach the select/arrange POST routes more easily. No rule is broken —
  those URLs were never status-guarded, only the link was hidden — but CARD-131's
  confirmation now guards a wider door, and finalize_book's save_and_finish ->
  set_book_status(READY_FOR_PDF) is one click from a non-draft detail page.
  `InvalidBookDetails` (a ValueError subclass carrying `fields`) is the seam if a
  confirmation ever has to cover renames.
- [Owner] ~/Documents/nonogram-reviews/CARD-130/ — 20 PNGs, 10 screens x desktop+mobile,
  including the refusal screen (field marked red with aria-describedby, typed description /
  audience / theme carried back) and a book-create-refused shot proving creation stayed
  inert. All 10 screens HTTP 200, runtime log clean over 20 loads.
- [Note] Playwright + Chromium were installed into the shared .venv for the runtime logs.
  pyproject.toml was NOT touched and ADR-0006/R1 reads the manifest, so the dependency
  baseline is intact; uninstall if unwanted.
