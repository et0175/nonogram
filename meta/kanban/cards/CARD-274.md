# CARD-274: admin/app.py splits into route modules — the blueprint refactor

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/274-app-py-route-split
**Worktree:** —
**Source:** the 2026-10-22 architecture review (same session as ADR-0040). Deliberately NOT an ADR: a pure refactor inside the adapter — no rank, boundary or contract changes. ADR-0040's Neutral section records that it proceeds independently and is sensibly sequenced after the move.
**Idea:** —
**Wave:** —
**Created wave:** 54
**Deferred waves:** 0
**Depends on:** CARD-273
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/routes/**, src/nonogram/admin/__init__.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`src/nonogram/admin/app.py` is 6,330 lines (counted 2026-10-22 — re-derive)
and, once CARD-273 has moved book production out, it is the largest file left
in the adapter: route handlers for puzzles, batches, review, books, images, the
player and exports all in one module, which is also a declared conflict hotspot
(`conflict.hotspots`) precisely because every admin card has to edit it.

Split the request handlers into cohesive route modules under
`src/nonogram/admin/routes/` (by resource: puzzles, batches, review, books,
images, player — follow the natural seams in the file, not this list, if they
disagree). `app.py` keeps only app creation, configuration and registration.
The mechanism — Flask blueprints vs plain registration functions — is the
implementer's choice **under G-1**: whatever is chosen, endpoint names and URL
rules must not change, because templates resolve `url_for()` against today's
endpoint names and blueprints prefix endpoint names by default.

This card runs after CARD-273 so it splits actual adapter code rather than
re-shuffling 13k lines of book logic that is about to move.

## Acceptance criteria

- **AC-1** *Given* the app before and after the split, *then* the URL map is
  identical — the full set of (rule, endpoint name, methods) triples compares
  equal, held by a committed parity test that snapshots the map, so a future
  rename reds instead of breaking templates silently.
  (test: `test_admin_url_map_parity` — new, in the admin test tree)
- **AC-2** *Given* `app.py` after the split, *then* no request-handler body
  remains in it — it creates, configures and registers only. (evidence on
  card: the post-split `app.py` size and an enumeration of what stayed, each
  line justified as creation/config/registration; review verifies)
- **AC-3** *Given* the admin test suite, *then* it passes with no edits to test
  assertions — at most import-line changes if a test imported a handler
  directly. (test: the suite; evidence: diff stat)

## Guardrails

- G-1: **Endpoint names and URL rules unchanged.** Every `url_for()` target in
  `templates/**` resolves exactly as before; AC-1's parity test is the control.
- G-2: `src/nonogram/admin/templates/**` and `src/nonogram/admin/static/**`
  untouched.
- G-3: **Pure relocation** — no handler's behavior, wording, status codes or
  response shapes change; moving code is the whole card.
- G-4: `src/nonogram/book/**` untouched (the move is done and certified;
  re-opening it here is scope growth), and `migrations/**`,
  `src/nonogram/db/**` untouched beyond import lines.
- G-5: `CLAUDE.md` not edited; `nonogram_poc` never touched; no new runtime
  dependency (ADR-0006/R1); no timing measurements.

## System contract

<!-- PROJECTION assembled by system_rules.py --card CARD-274 (scope: touches), 37 rules, 2026-10-22. Regenerated on every decompose; fix a wrong rule in its source artifact, never here. -->

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. (check: review-lens)
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

- **FR:** — (every admin FR's behavior is held by the existing suite; this card
  moves handlers, not behavior)
- **ADR:** ADR-0040 (Neutral: this refactor proceeds independently, sequenced
  after the move), ADR-0019/ADR-0030 (the admin panel remains one adapter, one
  deployment — this card changes neither)
- **Components:** COMP-009 (admin) — internal layout only; no component
  boundary moves
- **Trace:** meta/architecture/trace.yml — unchanged (COMP-009's code glob
  covers the new routes/ subpackage)

## Worktree notes

- **[The hotspot is the point]** `app.py` is in `conflict.hotspots` because
  five cards once serialized on it by accident. After this card, route cards
  touch their own module and the hotspot entry should be revisited (narrowed to
  the registration core or retired) — say so at done, don't edit config here.
- **[Blueprint endpoint names]** Flask blueprints namespace endpoints
  (`books.list` vs `list_books`). If blueprints are chosen, register them so
  the public endpoint names stay identical, or don't choose blueprints. AC-1
  reds either way — that is what it is for.
