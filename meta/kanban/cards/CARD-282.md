# CARD-282: The admin panel exports the player bundle — static JSON the public solver reads

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/282-player-bundle-export
**Worktree:** —
**Source:** ONLINE_GAME_SPECIFICATION.md#technical-architecture (owner decision 2026-10-23, commit 8b0ca0e2); backlog.md "A public online solver" / "A stable per-puzzle URL namespace" (both @enabler, both "Blocks CARD-210")
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/player_bundle.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_detail.html, tests/test_player_bundle.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** — (was: the URL-namespace DEC — resolved 2026-10-23 as DEC-044/ADR-0041, unblocked the same day)

## What to implement

The data layer of the public player phase (ONLINE_GAME_SPECIFICATION.md
"Technical Architecture", agreed 2026-10-23): a printed book is frozen, so the
player reads **static JSON exported at publication time** — no live database in
the customer path, and the admin panel/Postgres stay private.

1. **Bundle writer.** A new admin-side module `player_bundle.py` that, given the
   stored puzzles and books, writes a directory tree:
   - `index.json` — the library index: one entry per published puzzle (key,
     width, height, difficulty tier, title) for the player's `/library` page;
   - `puzzle/<key>.json` — one file per puzzle: row clues and column clues plus
     the same metadata. Clues come from the stored grid through the one encoder
     (`compute_clues`, the same call the storage boundary makes) — never
     re-derive them another way. **No solution grid and no field derived from
     it** (ADR-0038/R6; see EC-1). The picture name must not appear either —
     backlog "Wave-31 goal-check" already flags that the admin page leaks it in
     the hidden solved banner, and this bundle is the public surface where that
     would matter;
   - `book/<slug>.json` — one file per finalized book: its slug, display title,
     and the ordered list of its puzzle keys (for `/b/<slug>`, the QR landing).
2. **Keys and slugs** per ADR-0041/R1 (DEC-044, resolved 2026-10-23): a
   puzzle's public key is the first 10 lowercase hex characters of SHA-256
   over the UTF-8 bytes of `"{width}x{height}:"` followed by the solution
   grid's cells row-major, `'1'` filled / `'0'` empty. Implement it exactly —
   any deviation is a breaking change requiring a new ADR. Book slugs per the
   same ADR. Do not invent a second naming scheme anywhere in the tree.
3. **Trigger.** An explicit owner action, not a side effect: a "Export player
   bundle" action on the book detail page (route lands in whatever module owns
   book routes after CARD-274's blueprint split), plus a callable entry point
   tests can drive. Export is **read-only** with respect to the database.
4. **Output** goes to a directory outside the package (default under `build/`),
   gitignored. Re-export of unchanged data is deterministic: same input, same
   bytes (that is what makes "did the bundle change?" diffable at deploy time).

Note the moving floor: CARD-273 relocates book modules to `src/nonogram/book/`
and CARD-274 splits `app.py`. If those have merged by the time this card runs,
read books through the moved modules' public API and register the route in the
split's route module — the Touches list above names today's paths.

## Acceptance criteria

FR-045 (registry entries minted by the 2026-10-23 architect delta, ADR-0041).

- AC-380: Given a finalized book, when the owner exports the player bundle, then
  the output tree contains `index.json`, `book/<slug>.json`, and one
  `puzzle/<key>.json` per published puzzle, and each puzzle file's clues equal
  `compute_clues` of the stored grid (test: tests/test_player_bundle.py::
  test_bundle_tree_and_clues_match_the_encoder).
- AC-381: Given any exported bundle, when every file in it is scanned, then no
  file contains a solution grid, a filled-cells encoding, or the picture name
  (test: tests/test_player_bundle.py::test_bundle_is_clean_of_answers — a
  property test over a seeded corpus of grids, not one example).
- AC-382: Given an export run, when it completes, then the database is unchanged
  (read-only — no INSERT/UPDATE/DELETE issued) and a second run over the same
  data produces byte-identical files (test: tests/test_player_bundle.py::
  test_export_is_readonly_and_deterministic).

## Engineering constraints

- EC-048 (ADR-0038/R6, ADR-0041/R2): no artifact this card produces may carry a
  puzzle's solution grid to a public surface, for any puzzle, any book, any
  export path — not just the AC-381 examples.
  test: tests/test_player_bundle.py::test_bundle_is_clean_of_answers
- EC-049 (ADR-0041/R5): the export is read-only against the database and
  deterministic — same input, byte-identical output — for every input, not just
  AC-382's example run.
  test: tests/test_player_bundle.py::test_export_is_readonly_and_deterministic

## Guardrails

- G-1: Do not edit migrations/**, src/nonogram/db/**, src/nonogram/export/layout.py,
  src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_manager.py,
  tests/helpers/book_corpus.py — shared hotspots outside this card's footprint
  (books are read through their public API, never modified).
- G-2: The admin player is untouched: src/nonogram/admin/static/solver.js,
  solver_state.js, templates/puzzle_solve.html and their behavior stay as merged
  by CARD-160..162 (test: existing tests/test_puzzle_solver_page.py suite green).
- G-3: The runtime dependency baseline stays closed (ADR-0006/R1: stdlib +
  Pillow + NumPy; test: tests/test_export_pdf.py::
  test_the_dependency_baseline_is_still_closed). JSON export is stdlib `json`.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. (check: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. (check: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. (check: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. (check: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. (check: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. (check: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. (check: test_no_module_types_a_round_mark_as_a_character)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. (check: review-lens)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). (check: TestSolverPage_ShowsTheClues)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. (check: review-lens)
- ADR-0039/R1 — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH the set member present, missed WITHOUT it. (check: test_the_control_for_each_spelling_depends_on_the_set)
- ADR-0039/R2 — A guard's set is derived from an authority the runtime can enumerate, not hand-written. (check: test_the_guard_sets_are_derived_and_not_hand_written)
- ADR-0039/R3 — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to an equality against the sites that exist ... (check: test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw)
- ADR-0041/R1 — A puzzle's public key is the first 10 lowercase hexadecimal characters of SHA-256 over the UTF-8 bytes of "{width}x{height}:" followed by the solution grid's cells row-major, '1' for filled and '0' for empty. (check: tests/test_player_bundle.py::test_bundle_tree_and_clues_match_the_encoder)
- ADR-0041/R2 — No public asset — nothing in player/, nothing in the exported bundle, nothing the assembled site serves — carries a solution grid or data from which any solution cell is recoverable, for any puzzle, on any export path. (check: tests/test_player_bundle.py::test_bundle_is_clean_of_answers)
- ADR-0041/R3 — The public player is static files only: plain hand-written JavaScript and CSS in the top-level player/ directory, no framework, no build toolchain, no npm, nothing added to the Python package. (check: review-lens)
- ADR-0041/R4 — The public player keeps play state in the visitor's browser localStorage only. (check: tests/test_public_player.py::test_no_write_request_for_any_interaction)
- ADR-0041/R5 — The player bundle is exported by an explicit admin-panel action, is read-only against the database (no INSERT/UPDATE/DELETE on any export path), takes its clues from compute_clues of the stored grid (the one encoder),... (check: tests/test_player_bundle.py::test_export_is_readonly_and_deterministic)
- ADR-0041/R6 — Nothing we ship stores, reads or transmits a visitor's IP address or any per-visitor identifier. (check: tests/test_public_player_pages.py::test_no_homegrown_tracking)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form r... (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an e... (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. (check: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not pass the door in force. (check: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-021 — Interactive play exists in exactly two forms. (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: TestExport_RejectsUnverifiedPuzzle, ...)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured maximum bound (NFR-002). (check: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, ...)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, ...)
- INV-006 — A puzzle whose cell on the book's trim is below the cell floor (TERM-024, 4.75 mm since 2026-10-17) is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (check: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, ...)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, ...)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: TestBookPublished_ConfirmedPuzzleChangeApplied, ...)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit move inside that leve... (check: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, ...)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; pairing never changes ... (check: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, ...)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4... (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, ...)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038;... (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, ...)
- INV-013 — The book's interior PDF holds no cover page and starts at the book's title / copyright page as a right-hand page 1 — no folio, no ink — with the guide following as a facing spread on pages 2 (verso) and 3 (recto); eac... (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, ...)

## Architecture context

- **FR:** FR-045 (AC-380..382; FR-044/ADR-0038 cover the admin player it
  exports for)
- **ADR:** ADR-0041 (R1 key recipe, R2 no-solution, R5 read-only deterministic
  export), ADR-0038 (R6), ADR-0006
- **Components:** COMP-009 (Admin Panel — the exporter lives behind its door),
  COMP-011 (Public Player — the bundle is its data)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
