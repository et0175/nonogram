# CARD-282: The admin panel exports the player bundle — static JSON the public solver reads

**Status:** in_progress
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/282-player-bundle-export
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-282
**Source:** ONLINE_GAME_SPECIFICATION.md#technical-architecture (owner decision 2026-10-23, commit 8b0ca0e2); backlog.md "A public online solver" / "A stable per-puzzle URL namespace" (both @enabler, both "Blocks CARD-210")
**Idea:** —
**Wave:** 58
**Depends on:** —
**Touches:** src/nonogram/admin/player_bundle.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_detail.html, tests/test_player_bundle.py
**Review score:** —
**Started:** 2026-10-24
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

## [DISPATCH 2026-10-24 — wave 58, orchestrator]

Fork point **`cef9f619`** (main). Worktree `../PythonProject4-card-282`, branch
`card/282-player-bundle-export`, `.venv` symlinked.

**No dependency, and the `Blocked by:` is genuinely resolved** — the URL-namespace
DEC landed 2026-10-23 as DEC-044/ADR-0041, and
`meta/architecture/decisions/adr/0041-public-player-static-bundle-and-hash-urls.md`
exists. Read the key recipe out of **ADR-0041/R1 itself**, not out of this card's
paraphrase of it: the card says "implement it exactly — any deviation is a
breaking change requiring a new ADR", and a paraphrase is exactly how a recipe
drifts.

### The moving floor is resolved: use today's paths

The card hedges — *"CARD-273 relocates book modules to `src/nonogram/book/` and
CARD-274 splits `app.py`. If those have merged by the time this card runs…"*.
**Checked at dispatch: CARD-273 and CARD-274 are both `ready` and
undispatched.** So the hedge resolves to **today's paths**, which is what
`Touches` already names: read books through `src/nonogram/admin/`'s existing
public API and register the route in `app.py` (53 route/blueprint sites today).
No conditional left for the round to guess at.

**And the obligation that creates, recorded now rather than discovered later:
CARD-274 splits `app.py`, so whichever of the two lands second carries the
other's work through.** If this card merges first, **CARD-274's brief must say
to carry the "Export player bundle" route into the split's route module** — I
will write that onto CARD-274 at this card's merge, not afterwards.

### Dispatched in parallel with CARD-276, and the graph agrees

`Touches` intersection with CARD-276 is **empty** (CARD-276 edits only
`tests/test_book_export_interior_cover.py`). No shared `conflict.hotspots`
entry. Genuinely concurrent.

**What is not free, and is the one thing the owner weighed before choosing
this:** `src/nonogram/admin/app.py` is in this card's `Touches`, and **75 test
files import the admin app — 563.58 s over 2,942 tests = 39.5 % of a 1426.16 s
suite.** Under `test_scope: impact` that is this card's per-cycle gate.
**344.29 s of it — 61 % — is `tests/test_book_export_interior_cover.py`**, a
file this card has nothing to do with, whose cost is CARD-287's subject and
which CARD-276 is editing right now. Expect ~5 gate runs across the card's
cycles, so **roughly 47 minutes of test time, ~29 of it in one unrelated file.**

**Do not narrow the impact set to make this cheaper.** That file is in the set
*because* it imports `app.py` more heavily than almost anything else, so
excluding it would remove precisely the coupling the impact scope exists to
catch. The owner was offered the alternative (run CARD-287 first and let this
card's cycles run cheap) and chose to pay the machine time instead, because this
chain unblocks **CARD-210**, which has been `blocked` since 2026-10-13 on
exactly this infrastructure: *"a public solver that is actually hosted, and a
per-puzzle URL namespace"*.

### Scope note the round should not have to infer

This card is the **data layer only** — the bundle writer, the keys, the trigger
and the output tree. `player/**` does not exist yet and is **CARD-283's**; this
card creates nothing under it. The chain is 282 → 283 → 284 → 285, strictly
serial, and only this first card touches `src/`.

### Correction, same day — I under-reported this card's gate by 16 %

The 39.5 % figure above came from **my grep** for admin-app importers (75 files,
563.58 s). The **committed tool** disagrees and is right: `scripts/impact_set.py
src/nonogram/admin/app.py` reports **98 files = 654.16 s over 5,739 tests =
45.9 %** of a 1426.16 s suite. Its own docstring says why — it prints "a
superset", and it includes unconditionally the ~22 tests that **scan the tracked
tree** (`git ls-files`, `git grep`, `rglob`) rather than importing what they
judge, which no import-graph grep can see.

So **five gate runs is ~55 minutes, of which ~29 is
`tests/test_book_export_interior_cover.py` alone** (344.29 s, **52.6 % of the
impact set**). The decision does not change; the number it was taken on was
light, and a figure is a claim whose control is recomputation — through the
project's own instrument, not a grep that approximates it.

**And the reason CARD-274 would not have helped, measured 2026-10-24 when the
owner asked whether to run it first:** the gate cost comes from tests importing
`nonogram.admin.app` **itself** — 82 `from nonogram.admin.app import`, 10
`import nonogram.admin.app`, 8 `from nonogram.admin import app`, and **zero
naming a route module**. After the blueprint split `app` still imports the
blueprints, so a change to `routes/book.py` keeps `app` in its
reverse-dependency closure and this set does not shrink. **The split moves code,
not the import graph the gate reads.**
## Worktree notes (CARD-282, 2026-10-24)

### The card's restatement of ADR-0041/R1 matches the ADR. Its slug sentence does not.

Read out of the ADR itself, not the card: R1 is *"the first 10 lowercase
hexadecimal characters of SHA-256 over the UTF-8 bytes of `"{width}x{height}:"`
followed by the solution grid's cells row-major, `'1'` for filled and `'0'` for
empty"*, with the worked example `"2x2:1000"` and "exactly one implementation
computes it". The card's paragraph 2 says the same thing in the same order, so
there is no deviation and nothing to stop for. `puzzle_key` implements it and
`tests/test_player_bundle.py::test_the_key_is_the_adrs_worked_example` asserts
the **hashed material** (`b"2x2:1000"` and, for a non-square grid, `b"3x1:100"`),
not just a digest computed the same way twice.

**But "Book slugs per the same ADR" points at something that is not there.**
ADR-0041 names `/b/<slug>`, "keyed by the book slug" and (in the owner spec)
"distinct per book/edition", and specifies **no slug recipe at all** — nor does
FR-045, TERM-040, TERM-041 or the glossary. So `book_slug` is **this card's
choice**, recorded as such in `player_bundle.py`'s docstring and here rather
than passed off as the ADR's:

> first 10 lowercase hex of SHA-256 over the UTF-8 bytes of `"book:{title}:"`
> followed by the book's puzzle keys in book order, concatenated.

Deliberately the *same* scheme as R1 applied to a book's own content (same
algorithm, truncation and case; a domain prefix then a fixed-width payload —
every key is exactly 10 characters, so no separator is needed) rather than a
second naming scheme, and content addressed for R1's own reason: a printed QR
code cannot be re-pointed, and the cover title plus the puzzles inside are what
survives a database re-seed. **This wants pinning by an ADR revision (an R7)
before any book is printed.** Nothing is printed yet — CARD-210 is still
blocked — so the window is open, and `book_slug` is the one function to change.

> **Superseded the same day.** The owner resolved this as **ADR-0041/R7** +
> DEC-044b (main `f32520a6`) and chose a **keys-only** recipe, explicitly
> against the `"book:{title}:"` variant above. See "## Worktree notes —
> revision to ADR-0041/R7" at the end of this file; the paragraph above is kept
> as the record of what was shipped in `58327b53` and why it was flagged, not
> as a description of the code.

### Two defects found in the brief, both measured

1. **"A new module under `src/nonogram/admin/` needs its row in
   `src/nonogram/__init__.py`'s docstring or the suite reds" is backwards.**
   The canonical map's row unit is the *top-level name under `nonogram`*:
   `tests/test_cli.py`'s `_component()` returns `module.split(".")[1]`, so
   `nonogram.admin.player_bundle` **is** the `admin` component, which already
   has its row (`admin/ COMP-009`). No row was added, and `tests/test_cli.py`
   is green (135 tests) without one. Measured the other way too: planting a
   `player_bundle    COMP-012 ...` row reds **5 cells** —
   `test_the_docstring_map_parses_into_rows`,
   `test_every_component_the_walk_finds_appears_exactly_once`,
   `test_the_maps_adapter_count_is_the_other_hole_that_stays_open`,
   `test_removing_the_planted_module_passes` and
   `test_the_two_row_readers_accept_exactly_the_same_lines` — because the row
   names no component the walk finds. The row was reverted and the file
   verified by sha256 (`ba2a58cd…`, 0 occurrences of the marker).
2. **The dispatch's impact figure needed recomputing again.** `scripts/impact_set.py`
   on this card's four changed paths reports **100 files**, not the 98 the
   dispatch quotes (the extra two are this card's own new test file and
   `tests/test_player_bundle.py`'s entry into the derived always-on scanning
   set — it uses `.rglob(`). The gate ran at **5840 passed, 15 skipped,
   661.64 s**, against the dispatch's predicted 654.16 s / 5739 tests.

### What is in the bundle, and the one thing that is not from the ADR's wording

`index.json` → `{"puzzles": [{key,width,height,tier,title}, …]}` sorted by key;
`puzzle/<key>.json` → the same entry plus `clues: {rows, columns}` from
`compute_clues` of the stored grid; `book/<slug>.json` →
`{slug,title,puzzle_keys}`. AC-380 writes "difficulty tier"; the field is named
`tier`, and `CRITERIA_FIELDS` in the test file is the literal pin for that
choice.

*Published* = carried by a finalized book; *finalized* = every `BookStatus`
except draft, derived from the enum (`FINALIZED_STATUSES`). A draft book's
puzzles never reach the bundle, and `test_bundle_is_clean_of_answers` asserts
their key and title are absent from the whole tree (M10 reds those two cells).

### EC-048's second clause — "data from which any solution cell is recoverable"

Two solution-derived values are written, both *required* by the ADR, and both
named in `SOLUTION_DERIVED_FIELDS` so the exemption is a declaration rather
than an omission (ADR-0039/R3): the clues (R5) and the one-way key (R1, in
three places). The scan behind AC-381 has two halves of different kinds:

* **derived forbidden material** — `forbidden_encodings(grid)` builds, from
  each grid at run time, 4 alphabets x 4 traversals x 4 separators plus the
  JSON forms, the hex and base-64 forms, and the **untruncated** digest (54
  more characters of the same material nothing has a reason to carry);
* **default-DENY on field names** — every JSON object key in the tree must be
  in `DECLARED_FIELDS`, derived from the exporter's own schema tuples. **An
  unrecognised field is a violation.** This is the half that catches a leak
  which is not a cell encoding at all: M3 adds `filled_cells` and is killed by
  it. And because that authority is code a mutant could widen alongside the
  writer, `test_the_declared_schema_is_the_field_set_the_criteria_name` holds
  the tuples to the literal field list the ACs name — V4 does exactly that
  widening and reds there.

The picture name is written nowhere: the title chain stops at `puzzle_name` and
falls back to `"Puzzle <key>"`, never to `source_image` the way `app.py`'s own
solve page does (M2 restores that fallback and reds 2 cells).

### EC-049 — proved by mechanism, over a real database

`test_export_is_readonly_and_deterministic` runs against SQLite through
`sqlite_session_scope`, so it **does not skip** (the suite's `db_required`
tests do, silently). Three kinds of evidence: an `Engine`-class statement log
whose verdict is taken on the *complement* of a read-only verb set (TRUNCATE,
MERGE, UPSERT, DROP, GRANT and an unparsable statement are all writes —
`test_the_statement_verdict_is_default_deny`, 15 cases); a row snapshot taken
from `Base.metadata.sorted_tables`; and a four-way byte comparison where two
runs are **subprocesses under different `PYTHONHASHSEED`** values, which is the
only way set iteration order reaching the output can be seen at all (M5 proves
it: `set(candidates)` reds the four-way comparison).

Determinism is built, not hoped for: explicit sorts everywhere, `sort_keys` /
`ensure_ascii` / fixed indent / explicit LF / `allow_nan=False`, **no floats at
all** (the writer refuses one), and `_settled` as a pure reduction for the
metadata of two rows that share one key by ADR-0041's design (M13 reds when
read order decides instead).

### Kill matrix — 17 mutants, 17 kills, 91 assertion nodes

Instrument: `tests/kill_matrix.py`, recording pass, child instrumentation off.
SHIPPED 0 FAIL of 91 reached, 53 collected tests.

| mutant (mechanism deleted) | cells red |
|---|---|
| M1 leak the solution grid into the puzzle file | 3 |
| M2 title falls back to `source_image` | 2 |
| M3 undeclared field carrying `filled_cells` | 2 |
| M4 export writes to the database (`rename_puzzle`) | 6 |
| M5 set iteration order into the output | 2 |
| M6 `sort_keys=False` | 1 |
| M7 `ensure_ascii=False` | 1 |
| M8 the owned tree is not reset | 2 |
| M9 the float refusal | 0 cells, **exit 1** (a `pytest.raises` mismatch — an error, not a cell) |
| M10 draft books exported too | 2 |
| M11 key material `{height}x{width}` | 2 |
| M12 truncation 10 -> 16 | 10 |
| M13 `_settled` reduction deleted | 1 |
| V1 the scan's deny-default deleted | 2 |
| V2 the forbidden-encoding derivation emptied | 1 |
| V3 the statement verdict always says clean | 3 |
| V4 schema widened together with the writer | 1 |

**Two of my own tests were weak and the instrument is how I know:**

* **M9 survived at first** (exit 0, 0 cells): `pytest.raises(TypeError,
  match="float")` passed with the float branch deleted, because the
  deny-default arm's message *prints the type name* and therefore contains the
  word "float". Now matched against the branch's own sentence.
* **M11 killed only 1 cell at first**, and not the one that should have caught
  it: the ADR's worked example is **square**, so `2x2` cannot tell
  `{width}x{height}` from `{height}x{width}`, and
  `test_the_key_separates_the_recipes_parts` compares two keys for inequality —
  both move together under the swap. A non-square material assertion
  (`b"3x1:100"`) was added and the blind spot is now written into that test's
  docstring instead of being implied away.

V1/V2/V3 are the ADR-0039/R1 readings for the three mechanisms: with the
mechanism present the leak is caught (M1/M3/M4), with it deleted the control
that depends on it reds — and V3 in particular shows AC-382's own
`forbidden_statements(...) == []` passing **vacuously** while
`test_the_statement_log_catches_a_write` reds, which is the whole reason that
control exists.

### Also pinned, because it is a trap a refactor would walk into

`PuzzleReviewService._grid_fingerprint` hashes a string of the *same shape* as
R1's — extent, colon, bits — with the extent **the other way round** and **no
truncation**. For any non-square grid it is a different value for the same
cells. `test_the_stores_internal_fingerprint_is_not_the_public_key` holds them
apart, so reusing the memo key as the public key is a red rather than a
breaking change to every printed book that looked like a refactor.

### Raised rather than fixed

* **ADR-0041 has no book-slug rule.** Proposed R7 above; needs the owner.
* **A book's slug moves if its title is edited or a member changes.** Both are
  frozen in practice for a printed book (INV-008, INV-012), and the ADR's own
  Negative already records that a finalized-but-unexported book has QR codes
  pointing at keys the site does not serve. Worth one sentence in
  `docs/deploy/player.md` (CARD-285) rather than code here.
* **CARD-274 carries this route forward.** `POST /book/<id>/export-player-bundle`
  is registered in `app.py`; the blueprint split must move it with the other
  book routes.

## Worktree notes — revision to ADR-0041/R7 (2026-10-24, second commit)

The slug gap this card raised was resolved by the owner as **DEC-044b +
ADR-0041/R7** (main `f32520a6`), and the recipe is **keys-only**:

> the first 10 lowercase hex characters of SHA-256 over the UTF-8 bytes of
> `"book:"` followed by the book's puzzle keys in book order, concatenated with
> no separator.

**The title is not an input.** That is the change from what `58327b53` shipped,
and R7's own text names the `"book:{title}:"` variant as the alternative
decided against, for the reason the first commit's docstring was circling: a
printed QR code cannot be re-pointed and a title is editorial, so a
one-character typo fix in the admin panel would otherwise break every code in
an already-printed run. The accepted remaining sensitivity is that the slug
*does* move on a membership change — content, not editorial, and already an
explicit confirmed act outside draft (INV-012).

### What changed in the code

* `book_slug(title, puzzle_keys)` → **`book_slug(puzzle_keys)`**. The title is
  gone from the *signature*, not merely from the hash: nothing else needed it
  (the book file's `title` comes straight off the book through `_book_title`),
  and a parameter accepted and ignored is a version of "not an input" a caller
  can get wrong.
* The module docstring no longer says "this card's recipe, not the ADR's" —
  that was true when written and is now false. It cites R7 and carries R7's
  breaking-change clause verbatim in substance: the prefix, the ordering, the
  absence of a separator, the algorithm, the truncation length, the case.
* **A consequence of the exclusion that needed handling, not a note.** With the
  title in the hash, two books could only share a slug by sharing a title, so
  the file content was the same either way. Keys-only means two finalized books
  with the same puzzles in the same order are **one** slug with **two**
  candidate titles. `export_bundle` now groups books by slug and `_book_file`
  reduces the title through `_settled` — a function of the titles, not of the
  store's row order. Writing "whichever book was read last" would have made the
  bundle's bytes depend on row order and quietly cost EC-049. Held by
  `test_two_books_with_the_same_puzzles_are_one_public_book`, and M16 reds it.

### R7's `check` control now exists (it named a test that did not)

`tests/test_player_bundle.py::test_the_slug_does_not_move_when_the_title_is_edited`
— export, edit the title through `BookManager.update_book_details` (which by
its own rule is not a membership change, so the book stays out of draft),
re-export, assert the slug file name is unchanged **and** that the file's
`title` field followed the edit. Then the paired direction: drop a member,
re-pass the readiness gate, re-export, assert the slug **did** move. A
stability-only test would pass just as well on a slug that is a constant.

**Applying this card's own M11 lesson to the fixture.** M11 showed the ADR's
*square* worked example could not distinguish `{width}x{height}` from
`{height}x{width}`. The same trap exists here: a book titled `""` would hash
`"book:" + keys` either way under a mutant that injects the title without a
separator, hiding it completely. So both titles in the control are non-empty,
differ from each other, and are **asserted** to be so before the export.

### Mutants for R7, cells red

| mutant | cells |
|---|---|
| **M14 title reintroduced into the slug material** | **4** — `test_the_slug_is_content_addressed_and_not_the_books_row_id` L1156 (the material assertion), **`test_the_slug_does_not_move_when_the_title_is_edited` L1214** (R7's own control: "an editorial title change moved the slug"), `test_two_books_with_the_same_puzzles_are_one_public_book` L1256, L1259 |
| M15 a `-` separator between the keys | 1 — L1156, the material assertion (R7's "absence of a separator") |
| M16 book-file title settled by read order | 1 — L1259 |

M14 is implemented as a three-edit mutant so the title really reaches the hash
on the production path (a module-level holder set in `export_bundle`), rather
than as a signature change the call site would not compile against.

### Everything re-run at this state

* **Full kill matrix re-run**: 20 mutants, **20 kills**, 107 assertion nodes,
  SHIPPED 0 FAIL of 107 reached, 55 collected tests. M9 is still the one
  error-kill (exit 1, 0 cells — a `pytest.raises` mismatch). M8 rose from 2
  cells to 4, because the new slug control also reds without `_reset`; three
  tuple-unpackings were turned into indexed reads with the count asserted, so
  those arms report cells instead of NOT-REACHED (the same lesson as M9/M11).
  M12 still carries 10 NOT-REACHED downstream of its own early errors.
* **AC-380 / AC-381 / AC-382 green**, `tests/test_player_bundle.py` 55 passed.
* **Impact set re-derived** with `scripts/impact_set.py` for the *new* changed
  set (`player_bundle.py`, `test_player_bundle.py`) — **still 100 files, byte
  identical to the first gate's selection**, because `app.py` imports
  `player_bundle`, so every test importing the admin app is in
  `player_bundle.py`'s reverse-dependency closure. There was no cheaper subset
  to run. Gate: **5842 passed, 15 skipped, 660.63 s**, 0 failures, 0 errors —
  the same 15 `db_required` skips at `tests/conftest.py:207`, two more passes
  than the first gate because this commit adds two tests.

## [FIX PRE-GATE on `3f6b57a0` — 2026-10-24, orchestrator] PASSED

Two commits on the branch: `58327b53` (the bundle) then `3f6b57a0` (the R7
revision). Diff across both is **exactly the four `Touches` paths, 2044 pure
insertions, no deletions**.

### R7 is implemented, and the rule is falsifiable by its own named control

The recipe, recomputed **independently** of the shipped helper — `sha256("book:"
+ "".join(keys))[:10]` written out by hand against `book_slug(keys)`:

```
independent : 773df54c6b
shipped     : 773df54c6b
agree       : True | KEY_LENGTH = 10
signature   : (puzzle_keys: 'Iterable[str]') -> 'str'
title-free  : True
```

**The title is gone from the signature, not merely from the hash** — which is
better than asked for. A parameter accepted and ignored is a version of "not an
input" a caller can get wrong; a removed parameter makes the old call site raise
`TypeError` instead, and the round confirmed that failure before fixing it. And
the docstring no longer claims the recipe: **zero occurrences** of "this card's
recipe, not the ADR's" remain, replaced by a citation of **ADR-0041/R7,
DEC-044b** carrying R7's breaking-change clause item by item.

**My own mutant, independent of the round's M14.** Its M14 was a three-edit
mutant using a module-level holder. Mine is a **single edit at the call site on
the production path** — `book_slug([_book_title(book)] + list(keys))` — so the
title genuinely reaches the hashed material with no signature change:

| | cells |
|---|---|
| **reds `test_the_slug_does_not_move_when_the_title_is_edited`** (R7's `check`) | ✅ |
| reds `test_bundle_tree_and_clues_match_the_encoder` (AC-380, R7's other check) | ✅ |
| reds `test_the_slug_is_content_addressed_and_not_the_books_row_id` | ✅ |
| reds `test_two_books_with_the_same_puzzles_are_one_public_book` | ✅ |
| **total** | **4 failed, 51 passed** |

So **R7 does not ship as a rule whose control does not exist** — which is the
`check_ref_missing` defect this board has now found **ten** times, twice today on
CARD-276's own ACs. I wrote R7's `check` field pointing at a test that did not
exist yet; it exists, it is two-directional (the title edit must *not* move the
slug; a membership change *must*), and it fails when the mechanism is broken.

### The consequence of the owner's decision that nobody foresaw — handled, not noted

**With the title in the hash, two books could only share a slug by sharing a
title, so the file's content was identical either way. Keys-only breaks that:**
two finalized books with the same puzzles in the same order are now **one** slug
with **two** candidate titles, and one file has to speak for both.

The round found this itself and did the right thing with it. Its first commit's
`for slug, title, keys in sorted(book_keys)` would have resolved it **by sort
order** — deterministic, but *by accident*, and silently dropping a title. It now
groups by slug and reduces the title through the existing `_settled`, a pure
function of the candidate titles rather than of the store's row order, held by
`test_two_books_with_the_same_puzzles_are_one_public_book` with **M16** (settle
by read order) redding it. Without that, EC-049's byte-diff guarantee would have
depended on row order and nobody would have known.

**And it raised the product half rather than inventing a second rule one commit
after being pulled up for inventing the first.** Which title gets published, or
whether such a pair should be refused at export or disambiguated, is an ADR-level
question. **Routed to CARD-284**, which owns `/b/<slug>` and `/library` — the
pages that actually render a book's title — and flagged to the owner. The current
behaviour is deterministic, tested, and defensible (the slug names content, and
two books with identical content resolve to identical content), so it is not a
blocker.

### The structural fact CARD-283's brief needs

**`app.py` imports `player_bundle`, so any future change confined to
`player_bundle.py` alone still derives the same 100-file impact set.** The round
re-derived it for the narrowed changed set as asked and got a **byte-identical
listing** — `diff` of the two is empty. That is the tool being right, not a
defect, but it kills the assumption that touching only the new module is cheap.
**CARD-283/284/285 must not be scoped on that assumption**, and I will put this
on CARD-283 at dispatch.

### Gate

| | |
|---|---|
| `tests/test_player_bundle.py` | **55 passed**, no skips (53 + the two new) |
| the three ACs + R7's control, by node id | **4 passed** |
| impact set, re-derived, **100 files, unnarrowed** | **5842 passed, 15 skipped, 0 failed**, 660.63 s |
| skips | the **same 15**, one reason (`conftest.py:207`, `DATABASE_URL is not set`), all `db_required`, none in this card's footprint |
| **G-1** seven forbidden paths | **0** files touched |
| **G-2** the three admin-player files | **0** lines changed across both commits |
| kill matrix | **20 mutants, 20 kills**, 107 assertion nodes, SHIPPED 0 FAIL of 107 reached |

Two matrix changes worth recording because they are the round applying its own
earlier lessons: **M8 rose 2 → 4 cells** (the new slug control also reds without
`_reset`), and **three tuple-unpackings became indexed reads with the count
asserted**, so those arms now report cells instead of NOT-REACHED — an unpacking
raises before the assert, and a never-reached assert is indistinguishable from a
surviving mutant. M9 remains the one **error-kill** (exit 1, 0 cells, a
`pytest.raises` mismatch), reported as such rather than as a failure cell.

## [CYCLE 1 ADJUDICATION — 2026-10-24, orchestrator] 7.0, NOT CERTIFIED — four gating findings, and the exporter is right while the guard is not

Report: `meta/review/20261024T115136Z-CARD-282-cycle1.yml` (synced; `yaml.safe_load`
OK; 8 findings — 4 gating; score 7, `certified: false`). **Aggregate round
counter: 3 of 6** (implementation including its R7 revision, pre-gate, cycle 1),
so one fix round, its pre-gate and a cycle 2 all fit.

**The shape of this review is the opposite of the usual one and worth naming: the
shipped artefact is clean and the thing that proves it clean is not.** EC-048
holds — the reviewer ran a provenance whitelist over the real 53-grid corpus (56
files) and every value in every file is accounted for as the R1 key, the extent,
a stored tier, a stored title, a R7 slug, or `compute_clues` of the stored grid:
**`UNACCOUNTED VALUES: none`**. No recoverable solution cell ships. Four of the
findings are about the guard that is supposed to keep it that way.

### F1 (high, gating) — the scan cannot fail for the leak class it names. Reproduced.

One edit on the production path in `_index_entry`, adding
`"clues": {"rows": <the grid as ints>, "columns": []}` — **no schema tuple
widened, no new field name** — puts the **entire 144-cell solution grid into
`index.json`**, exactly recoverable, with `answer_violations → []` and **55
passed**. Two independent causes, each isolated by the reviewer:

1. **`DECLARED_FIELDS` is a flat union** of the five per-file tuples (11 names),
   and **nothing asserts a written file's object equals its OWN tuple** — a
   puzzle file carrying `slug` and `puzzles` scans clean too. The derived set is
   real; the predicate underneath is default-ALLOW. **This is the CARD-245 shape
   exactly** — there the method *set* was derived while the write *predicate* was
   a four-shape allow-list, so eight of nine real write shapes were silently
   exempt.
2. **The scan looks for byte shapes the exporter cannot produce.** Verified
   independently here: `_dump` writes **`indent=2`** (`player_bundle.py:558`) and
   **every one of `forbidden_encodings`' forms is compact — 0 of 56 contain a
   newline** on a 2×3 grid. So the same leak, in the same field, in the same
   file, is **CAUGHT** when planted with compact `json.dumps` (which is what the
   leak-shape control at `:696` does) and **MISSED** when planted with
   `player_bundle._dump`.

**That second cause is the purest instance of ADR-0039/R1's violation this board
has produced: the control demonstrates the scan catching a shape the production
path never emits.** It is not that the control is weak — it is that the control
and the writer disagree about what a file looks like, and the control's version
is the one the scan was built for.

And the reach that remains is string values, where it is also incomplete: **7 of
7 recoverable encodings planted in `title` were missed** — base64 and base85 of
*packed* bits, a diagonal traversal, run-length, per-row hex, row-reversed, and
`-`-joined.

Rated **high rather than critical** because the shipped bundle is clean. **But it
is the contract CARD-283, CARD-284 and CARD-285 build on**, and EC-048's own
words are "for ANY puzzle, ANY book, ANY export path".

### F2 (medium, gating) — the corpus minimum is a tautology. Reproduced.

`MIN_CORPUS_GRIDS = 48` (`:86`) **both builds the corpus** —
`for index in range(MIN_CORPUS_GRIDS + 4)` at `:451` — **and is the bound it is
compared against** (`:620`, `:621`, `:622`). Lowered to 4: **corpus 9 grids, 55
passed.** EC-048's registry statement ends explicitly *"with the minimum corpus
size asserted in the test"*, and a bound that moves with the thing it bounds
asserts nothing. The corpus really is 53 at 48, as briefed — the count is right
and the guard on it is not.

### F3 (medium, gating) — `SOLUTION_DERIVED_FIELDS` is decorative

No scan and no production path reads it. Emptying it to `frozenset()` reds
**exactly one cell** — the test comparing it to its own literal — and changes
nothing about what is caught or written. Three docstrings
(`player_bundle.py:38`, `test_player_bundle.py:190-192`, and **this card at
`:332-334`**) claim it is how the scan "states the exemption instead of
absorbing it". ADR-0039/R3: an exemption is a claim and carries a control for
what it must NOT absorb. This one carries a control for its own spelling.

**F1 and F3 share one remedy**, and the reviewer has already built it as a probe:
**the provenance whitelist**. Instead of enumerating forbidden encodings —
default-allow underneath, by construction — assert that **every value in every
file is accounted for by a named good source**, with the exemption as the list of
those sources. That inverts the polarity, which is the only thing that closes a
default-allow guard.

### F4 (low, gating) — and it corrects ME

**`player_bundle.py:176` still ships `#: book slug is this card's recipe, not
ADR-0041's.`** on `_BOOK_PREFIX` — the very constant R7 pins.

My pre-gate reported *"zero occurrences of 'this card's recipe, not the ADR's'
remain"*, and this card repeats it at `:465`. **Both are false, and the way they
are false is the lesson: I verified a claim's absence by grepping for one
spelling of it.** The surviving text says "not **ADR-0041's**" where my pattern
said "not **the ADR's**", so the grep returned 0 and I read that as the claim
being gone. A looser `grep -niE "this card's recipe"` finds it at once.

**That is a measurement whose domain did not cover its claim — the exact defect
class I have spent this whole session finding in other people's work**, and it is
the fifth of my own that a round has caught today. Recorded here rather than
quietly fixed, because the pattern matters more than the line: **an absence
verified against one spelling is not an absence.**

### Non-gating, routed

* **F5** — `_settled` is not a pure function of its candidate set when two
  candidates share `str()`: `_settled(["1", 1])` returns `1` under
  `PYTHONHASHSEED` 0/1/12345 and `'1'` under 99999. Reachable only in in-memory
  mode. Small, real, and in the mechanism that exists *because* determinism must
  not depend on ordering — so it belongs in the fix round even though it is
  non-gating.
* **F6** — the only export path the owner can actually trigger (the POST route)
  is never run under the statement log. EC-049 is proven on the callable entry
  point and not on the route. Worth closing in the same round; it is cheap.
* **F7 — the reviewer corrects the ROUND, and me.** **M9 is not an error-kill.**
  Reproduced: it is `1 failed, 54 passed`, **an ordinary failure cell**. The "0
  cells" was `kill_matrix.py`'s *attribution*, not pytest's verdict. The round
  reported it as an error-kill and I repeated that on this card. **Correct the
  claim; the kill stands either way.** (M12 verified honest: 13 failed, and its
  NOT-REACHEDs genuinely downstream of its own `FileNotFoundError`s.)
* **F8** — a mid-write `_dump` failure leaves `index.json` advertising files that
  do not exist. **Routed to CARD-284**, which owns the pages that read the index.

### What checked out, and one of them answers a question I asked

* **Every `test:`/`check:` reference resolves** — the five named node ids collect,
  ADR-0039/R1–R3's controls exist, and R4/R6 point at CARD-283/285 files as
  expected. **No `check_ref_missing`** — notable, since this board has found that
  ten times and twice today on CARD-276's ACs.
* **No test can be green by skipping**: 55 passed with `-rs`, no SKIPPED section,
  no skip/xfail/importorskip/`db_required` marker, and `sqlite_session_scope`
  never skips. The round's choice to make AC-382 run against a real database was
  right and is now verified.
* **The statement log has no bypass** — `before_cursor_execute` on the Engine
  class sees flush-generated writes, its control proves it, and `src/nonogram/**`
  has zero `raw_connection`/`.cursor()`. `_SERIALISABLE` and the verb verdict are
  **genuinely default-deny**.
* **The `_grid_fingerprint` tripwire discriminates** — delegating `puzzle_key` to
  `_grid_fingerprint(grid)[:10]` reds 2 cells including the tripwire, and its
  grid is **3×2**, so it does not have the M11 square-example trap.
* **V4 verified** (9 cells including the schema pin). **G-2: 0 lines.**
* **Nothing besides `_settled` reaches the output that `PYTHONHASHSEED` cannot
  see** — no time or locale import, no filesystem iteration, `ensure_ascii=True`.
  That answers the question I put in the brief.

### What cycle 1 did not check, carried forward

The 100-file impact gate (it changed nothing that ships; **a fix round must
re-run it**, and CARD-276 is editing 52.6 % of it concurrently). The full suite
(mine). The kill matrix as a table — per the cost ladder it verified the weakest
mechanism and spot-checked V4/M9/M12/the tripwire/the exemption, leaving M1–M8,
M10–M11, M13–M16 and V1–V3 un-re-run. EC-049 over store states other than
AC-382's one fixture.
