# CARD-273: Book production moves to src/nonogram/book/ — the ADR-0040 rewrite

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard  <!-- large but mechanical: a relocation whose correctness is "only import lines changed and the suite is green" -->
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/273-book-package-move
**Worktree:** —
**Source:** meta/architecture/decisions/adr/0040-book-production-composite-capability-rank.md (DEC-043, 2026-10-22; Migration: rewrite). Delta carded directly, no handoff increment.
**Idea:** —
**Wave:** —
**Created wave:** 54
**Deferred waves:** 0
**Depends on:** CARD-276, CARD-287, CARD-288, CARD-289, CARD-272, CARD-207, CARD-208, CARD-209, CARD-216, CARD-218, CARD-219, CARD-220, CARD-226, CARD-227, CARD-229, CARD-230, CARD-231, CARD-232, CARD-233, CARD-249, CARD-262
**Touches:** src/nonogram/book/**, src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_kdp.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/book_membership.py, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_plan.py, src/nonogram/admin/book_proof.py, src/nonogram/admin/print_specs.py, src/nonogram/admin/__init__.py, src/nonogram/admin/app.py, src/nonogram/admin/puzzle_review.py, src/nonogram/__init__.py, src/nonogram/errors.py, src/nonogram/export/layout.py, src/nonogram/export/png.py, src/nonogram/db/models.py, tests/test_cli.py, meta/architecture/c4/components-CTX-001.puml, meta/architecture/trace.yml, tests/**  <!-- tests/**: the import lines of the 83 test files that import nonogram.admin.book_* (measured 2026-10-22 by grep; re-derive) — one-line changes each, listed as the glob because naming 83 files hides more than it shows -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Execute ADR-0040's **Migration: rewrite**: relocate book production (CAP-006)
from the admin adapter into its own composite-capability package. CARD-272 has
already taught the guard the rank and the deny pin; this card gives the rank
its resident.

1. **Move nine modules** (13,840 lines, counted 2026-10-22 — re-derive) from
   `src/nonogram/admin/` to `src/nonogram/book/`, with `git mv` so history
   follows: `book_answer_key.py`, `book_kdp.py`, `book_manager.py`,
   `book_membership.py`, `book_page_spec.py`, `book_pdf_generator.py`,
   `book_plan.py`, `book_proof.py`, **and `print_specs.py`** — not a `book_*`
   name, but `book_manager` and `book_page_spec` import it and it imports
   `book_page_spec` back, so leaving it behind would make the moved package
   import the adapter, which CARD-272's guard now reds. `app.py` keeps using it
   from the new location (adapter → composite is legal).
2. **Update the importers.** In-src, exactly three files import the moved
   modules (verified 2026-10-22): `src/nonogram/admin/__init__.py`,
   `src/nonogram/admin/app.py`, `src/nonogram/admin/puzzle_review.py` — plus
   the moved modules' imports of each other. In tests, 83 files import
   `nonogram.admin.book_*` (measured by grep 2026-10-22; **re-derive the list
   mechanically — by grep or AST, not from this card**) and get one-line import
   changes only.
3. **Component map, C4, trace.** Add the `book/` row to the canonical map
   (`src/nonogram/__init__.py` docstring) with the next free component id
   (**COMP-011** as of this writing — verify against the map and puml) carrying
   CAP-006; add the same component to
   `meta/architecture/c4/components-CTX-001.puml` and a `components[]` entry
   with code glob `src/nonogram/book/**` to `meta/architecture/trace.yml`. The
   `TestComponentMap_*` classes hold all three to each other and to disk, so a
   partial update fails the suite. Re-pointing every book FR's component rows
   from COMP-009 is the trace-only synthesis pass that follows the merge — not
   this card.
4. **Stale path claims.** Comments and docstrings in `src/nonogram/errors.py`,
   `src/nonogram/export/layout.py`, `src/nonogram/export/png.py` and
   `src/nonogram/db/models.py` name `admin.book_*` paths (cross-references,
   not imports — verified 2026-10-22). A path in prose is a claim; update those
   lines, and sweep `src/**` and `tests/**` for any other
   `nonogram.admin.book_` / `admin/book_` reference left behind.
5. **Per-directory READMEs** for `src/nonogram/book/` per the pipeline's README
   step; `src/nonogram/admin/`'s description shrinks accordingly.

## Acceptance criteria

- **AC-1** *Given* the move, *then* `src/nonogram/admin/` contains no
  `book_*.py` and no `print_specs.py`, `src/nonogram/book/` contains all nine,
  and the full suite is green — including the guard walk now seeing a populated
  composite package on disk. (test: the full suite;
  `test_every_import_in_the_package_points_inward`)
- **AC-2** *Given* the canonical map, *then* the docstring row, the puml
  component and the trace `components[]` entry exist with one agreed id
  carrying CAP-006, and `TestComponentMap_*` passes in both directions — no row
  without a module, no module without a row, no id the model does not
  enumerate. (test: `TestComponentMap_*`)
- **AC-3** *Given* any moved module, *then* its body is unchanged except import
  statements and path-naming docstring/comment lines — demonstrated by a diff
  summary on the card enumerating every non-import changed line (expected:
  none). (evidence on card; review verifies)
- **AC-4** *Given* the test tree, *then* only import lines change in test files
  — no assertion, fixture-logic or expectation edits. (evidence: diff stat on
  card)
- **AC-5** *Given* `src/**` and `tests/**` after the move, *then* no reference
  to `nonogram.admin.book_` or `admin/book_` remains (grep control committed as
  the sweep's record on the card). References inside `meta/**` and `docs/**`
  are out of scope: `meta/` records history, and `docs/` re-pointing is named
  in the decompose report as follow-up, not silently absorbed here.

## Engineering constraints

- EC(ADR-0040/R1): every moved module's imports satisfy the composite law on
  disk — only capability-rank and shared-rank targets, nothing shallower.
  test: `test_every_import_in_the_package_points_inward`
- EC(ADR-0040/R2): no pipeline module imports `book/` after the move — the walk
  plus CARD-272's pinned deny case hold it.
  test: `test_every_import_in_the_package_points_inward`

## Guardrails

- G-1: **Pure relocation.** No behavior change in any moved module: no
  executable line changes anywhere except import statements. AC-3's diff
  discipline is the control; a "small improvement while we're here" is scope
  growth, not a favor.
- G-2: Outside `src/nonogram/admin/` and `src/nonogram/book/`, only
  comment/docstring lines may change (`errors.py`, `export/layout.py`,
  `export/png.py`, `db/models.py` cross-references) — no executable line in
  `export/`, `db/` or `errors.py` moves.
- G-3: `CLAUDE.md` is not this card's to edit — the canonical map is the
  `src/nonogram/__init__.py` docstring, and CLAUDE.md's prose is held by
  CARD-261/CARD-264's controls.
- G-4: `migrations/**` untouched — a relocation changes no schema.
- G-5: ADR-0033/R1 holds across the move — book code writes no puzzle field but
  `puzzles.book_id`; the rule's scope glob already covers both locations.
- G-6: `nonogram_poc` never touched; no new runtime dependency (ADR-0006/R1);
  no timing measurements.

## System contract

<!-- PROJECTION assembled by system_rules.py --card CARD-273 (scope: touches), 48 rules, 2026-10-22. Regenerated on every decompose; fix a wrong rule in its source artifact, never here. -->

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. (check: review-lens)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0031/R2 — A solve that branched is reported as the `guess` strategy (solver.STRATEGY_GUESS) in FR-029's strategies list, never as a tier. (check: test: TestTiers_BranchingIsAStrategyNotATier)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/... (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec the puzzle grid has exactly three rule weights -- 0.48 pt ordinary cell lines in grey, 1.28 pt every fifth line on both axes, 2.08 pt... (check: review-lens)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. (check: review-lens)
- ADR-0039/R1 — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: c... (check: test: test_the_control_for_each_spelling_depends_on_the_set)
- ADR-0039/R2 — A guard's set is derived from an authority the runtime can enumerate, not hand-written. (check: test: test_the_guard_sets_are_derived_and_not_hand_written)
- ADR-0039/R3 — An exemption is a claim. (check: test: test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw)
- ADR-0040/R1 — src/nonogram/book/ sits at the composite-capability rank: it imports only capability-rank modules (clues, difficulty, export, db, ...) and shared modules (er... (check: test: test_every_import_in_the_package_points_inward)
- ADR-0040/R2 — The generation pipeline never depends on book production: neither orchestrator.py nor any capability module imports src/nonogram/book/ (CON-019's one-way rul... (check: test: test_the_import_rule_rejects_each_forbidden_edge)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header ... (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its... (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request ... (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-019 — Adding book-specific page geometry (a trim, margins, a title band, a portrait-only rule, the 7.5 mm standard cell) never changes the CLI's or the web UI's ex... (check: test: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue c... (check: test: TestInteriorType_EveryFaceHoldsTheFloor)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image... (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan)
- INV-006 — A puzzle whose cell on the book's trim is below the cell floor (TERM-024, 4.75 mm since 2026-10-17) is a member of the book only together with an explicit ov... (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped... (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft... (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists)
- INV-013 — The book's interior PDF holds no cover page and starts at the book's title / copyright page as a right-hand page 1 — no folio, no ink — with the guide follow... (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage)

## Architecture context

- **FR:** — (the FRs CAP-006 serves — FR-030..FR-039, FR-041..FR-043 — are
  delivered and unchanged; this card moves their home, so their ACs are not
  this card's to re-verify beyond the suite staying green)
- **ADR:** ADR-0040 (the subject; Migration: rewrite), ADR-0007 (revised rank
  table), ADR-0033 (context boundary unchanged; R1 scope covers both globs),
  ADR-0036 (shared geometry stays in export/ — this move does not dissolve that
  direction)
- **Components:** COMP-009 (admin, shrinks), new book/ component (id assigned
  here, see AC-2), COMP-010 (db, import target only)
- **Trace:** meta/architecture/trace.yml — gains the book/ component entry;
  full re-point of CAP-006/FR rows is the post-merge trace-only synthesis

## Worktree notes

- **[Why the long dependency list]** Every listed card edits
  `admin/book_*.py`, the book tests, `app.py` or `tests/**`. Moving the files
  under an open sibling diff would conflict catastrophically, so this card runs
  after the book wave drains. CARD-210 and CARD-263 also overlap but are
  indefinitely blocked (owner decisions) and are deliberately NOT dependencies;
  if either unblocks after this merge, its `Touches:` must be re-pointed to
  `src/nonogram/book/` — recorded in the decompose report.
- **[Figures are claims]** 9 modules / 13,840 lines / 3 in-src importers / 83
  test files were all measured 2026-10-22 by grep and `wc`. Re-derive each by
  AST or grep before relying on it; correct here if it moved.
- **[Mechanics]** `git mv` preserves history. Run the guard first after the
  move — it is the fastest honest signal that an import edge is wrong. The
  suite's full runs take the flock on `meta/kanban/.full-suite.lock`.

## Dependency list extended 2026-10-24 — it predated four cards that edit what this card relocates

The list was written 2026-10-22 and is stale. Added, with the overlap each one
has against this card's own `Touches`:

- **CARD-276** (in flight, wave 58) — edits `tests/test_book_export_interior_cover.py`, inside this card's `tests/**`.
- **CARD-287** — the same file, and it is sized against the class CARD-276 is measuring.
- **CARD-288** — `tests/property/test_book_pdf_geometry.py`, inside `tests/**`.
- **CARD-289** — `src/nonogram/admin/book_pdf_generator.py`, named **explicitly** in this card's `Touches`.

Found while answering the owner's question "maybe we need 273–274 first?" on
2026-10-24. The answer was no — this card depends on seventeen others and
CARD-274 depends on this one, so the pair is **terminal** to the book phase
rather than an alternative ordering for it — and checking that turned up the
staleness. **A relocation card's dependency list is not documentation; it is the
thing that stops the relocation landing under a card that is mid-flight.** It
needs re-deriving at dispatch, not trusting: every card whose `Touches` meets
this one's belongs in it.
