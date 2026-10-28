# CARD-284: The QR landing and the library — /b/<slug> and /library around the player

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/284-book-landing-and-library
**Worktree:** —
**Source:** ONLINE_GAME_SPECIFICATION.md#technical-architecture (owner decision 2026-10-23, commit 8b0ca0e2) and §1.1 Puzzle Selection
**Idea:** —
**Wave:** 63
**Depends on:** CARD-282, CARD-283
**Touches:** player/**, tests/test_public_player_pages.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The two entry points into CARD-283's game — the spec's answer to "one player,
not two": a QR scan and an online visit land on the same app through different
doors.

1. **`/b/<slug>`** — the per-book landing the printed QR points at: the book's
   title, its puzzles from `book/<slug>.json` in book order (each tile: title,
   size, tier), tap one to `/play/<key>`. This page is a book customer's first
   contact with the product on a phone, seconds after scanning: it must render
   from the static JSON alone, instantly, with nothing else to load first.
   An unknown slug gets a friendly static not-found page, not a bare 404 —
   a misprinted or stale QR is exactly when the reader is most confused.
2. **`/library`** — all published puzzles from `index.json`, filterable by tier
   and size (spec §1.1), same tiles, same links. Client-side filtering over the
   one index file; no search backend.
3. Both pages are plain static HTML/JS in `player/`, same tokens and look as
   the board page, mobile-first.

The book slug in the URL doubles as the per-book usage signal — CARD-285 wires
the counting; this card only has to keep the slug the visible, bookmarkable
path (no fragment routing, no query-string indirection).

## Acceptance criteria

FR-045 (registry entries minted by the 2026-10-23 architect delta, ADR-0041).

- AC-387: Given a bundle with a finalized book, when `/b/<slug>` loads, then its
  puzzles are listed in book order and tapping one opens `/play/<key>` for that
  puzzle (test: tests/test_public_player_pages.py::test_book_landing_lists_and_links).
- AC-388: Given a slug not in the bundle, when `/b/<slug>` loads, then the
  not-found page renders with a way to the library, and no script error is
  thrown (test: tests/test_public_player_pages.py::test_unknown_slug_lands_softly).
- AC-389: Given the library page, when filtered by tier or size, then exactly the
  matching index entries remain and clearing the filter restores all (test:
  tests/test_public_player_pages.py::test_library_filters_the_index).

## Guardrails

- G-1: The admin player and panel are untouched: no edits under src/nonogram/**
  (same contract as CARD-283 G-1/G-2; this card's code is `player/` and tests).
- G-2: The bundle format is consumed as CARD-282 defined it — no new fields
  required of the exporter, no second index derived at page-load time.
- G-3: The runtime dependency baseline stays closed (ADR-0006/R1); no runtime
  dependency, no framework, no build tooling beyond the existing copy step
  (test: tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed).
- G-4: Out of scope — scores, daily puzzle, progress stats pages, any
  server-side write (deferred by the spec to the December write API).

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. (check: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). (check: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R5 — pyproject.toml package-data for nonogram.admin includes static/*.js alongside templates/*.html and static/*.css, so the player's script ships in every built wheel. (check: review-lens)
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

- **FR:** FR-045 (AC-387..389)
- **ADR:** ADR-0041, ADR-0038, ADR-0006
- **Components:** COMP-011 (Public Player)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** puzzle tile (new — register in components.md), reuse the
  tier badge look from the admin lists
- **Screens:** /b/<slug>, /library, the not-found page
- **Standards:** forge:engineering-standards §11

## Worktree notes

—

## Routed in from CARD-282's review cycle 1 (2026-10-24) — two items, one product question

CARD-282 builds the bundle this card's pages read. Two things surfaced there
belong here rather than on it, and are written down now rather than at that
card's merge.

### 1. F-8 — a half-written bundle advertises files that do not exist

A `_dump` failure part-way through an export leaves `index.json` listing puzzle
keys whose `puzzle/<key>.json` was never written. CARD-282's export is
**deterministic and read-only against the database**, and that is all it claims;
it does not claim **atomicity**, and cycle 1 did not ask it to.

**This card's pages are where that becomes visible**, because `/library` reads
`index.json` and `/b/<slug>` reads a book file, and either can name a file that
is absent. So decide it here, with the shapes stated so nobody re-derives them:
a 404 on a listed puzzle, a book page listing a puzzle that will 404, or a
library index that silently drops entries it cannot resolve. **Whatever is
chosen, the claim belongs in a test** — "the player degrades rather than
breaking on an incomplete bundle" is a claim like any other and needs a control
that fails.

Not CARD-282's to fix: making the export atomic is a change to the writer with
its own failure modes (a temp tree and a rename, which is not free on every
filesystem), and it would have landed in that card's last cycle with no review
left. Raised there, routed here.

### 2. The product question ADR-0041/R7 opened and does not answer

R7 excludes the book's **title** from the slug on purpose, so that an editorial
title edit cannot break a printed QR code (owner decision 2026-10-24, DEC-044b).
A consequence nobody foresaw: **two finalized books with identical puzzle
membership in identical order are now ONE slug with TWO candidate titles**, and
one `book/<slug>.json` has to speak for both.

CARD-282 made that **deterministic** — the title is reduced by a pure function of
the candidate values rather than of the store's read order, held by
`test_two_books_with_the_same_puzzles_are_one_public_book` with a mutant redding
a read-order settle. **The engineering is settled. The product answer is not**,
and CARD-282's round deliberately refused to invent a second rule one commit
after being pulled up for inventing the first.

**This card owns the pages that render a book's title**, so the decision is
here. The options, with what each costs:

* **Publish one title** (what ships today — the first in a stable order). Cheap,
  deterministic, and one book's title never appears publicly.
* **Refuse such a pair at export.** Arguably right if identical membership is a
  data error, but it makes a legitimate second edition unpublishable.
* **Disambiguate.** Needs a discriminator in the slug, which **re-opens R7** and
  is therefore an ADR touch, not a code change.

Worth knowing before choosing: a plausible real case is a reprint or second
edition with the same puzzles and a changed title — in which case one public
book with one title is arguably **correct**, since the slug names content and
the QR code resolves to the right puzzles. Only the displayed title is
ambiguous.
