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
**Wave:** —
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

Spec-derived (owner doc 2026-10-23); registry FR/ACs owed by the architect
delta blocking CARD-283.

- AC-1: Given a bundle with a finalized book, when `/b/<slug>` loads, then its
  puzzles are listed in book order and tapping one opens `/play/<key>` for that
  puzzle (test: tests/test_public_player_pages.py::test_book_landing_lists_and_links).
- AC-2: Given a slug not in the bundle, when `/b/<slug>` loads, then the
  not-found page renders with a way to the library, and no script error is
  thrown (test: tests/test_public_player_pages.py::test_unknown_slug_lands_softly).
- AC-3: Given the library page, when filtered by tier or size, then exactly the
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
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form r... (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an e... (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

## Architecture context

- **FR:** — (untraced: owed by the architect delta blocking CARD-283)
- **ADR:** ADR-0038, ADR-0006
- **Components:** — (public surface component registered by the same delta)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** puzzle tile (new — register in components.md), reuse the
  tier badge look from the admin lists
- **Screens:** /b/<slug>, /library, the not-found page
- **Standards:** forge:engineering-standards §11

## Worktree notes

—
