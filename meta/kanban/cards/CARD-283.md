# CARD-283: The public player page — the admin game served static, with no answer in the browser

**Status:** blocked
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/283-public-player-page
**Worktree:** —
**Source:** ONLINE_GAME_SPECIFICATION.md#technical-architecture (owner decision 2026-10-23, commit 8b0ca0e2: one player app, routes /play/<key>, /b/<slug>, /library); backlog.md "A public online solver" @enabler
**Idea:** —
**Wave:** —
**Depends on:** CARD-282
**Touches:** player/**, tests/test_public_player.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** architect delta owed — CON-021 and ADR-0038/R6 confine interactive play to the admin door ("no public player"); the owner's 2026-10-23 direction reopens both, and that amendment happens at /forge:architect, not in a worktree. The same delta should register the new public-surface component and the static-export ADR. Unblock with `/forge:kanban unblock CARD-283` once CON-021 is amended.

## What to implement

The game itself, as a **static page** — the spec's key decision is ONE player
app serving both the book QR codes and online browsing, hosted statically so a
QR scan never waits on a cold start and customer traffic never touches the
admin service. This card builds the `/play/<key>` route; CARD-284 adds the two
entry pages around it.

1. **A new top-level static-site directory `player/`** (plain HTML/JS/CSS — the
   stack ADR-0038 already chose for the player; no framework, no build step
   beyond file copying, nothing added to the Python package). It is not a
   Python module and must not live under `src/nonogram/`.
2. **`/play/<key>`**: fetch `puzzle/<key>.json` from the CARD-282 bundle,
   render the board — clue boxes left and above, every fifth line heavier, the
   header with title and tier — and the marking behavior the admin player
   already has: three cell states, drag along the first-move line, undo/redo,
   reset, region marking. **Reuse, don't fork:** the board state lives in the
   admin player's pure module (`solver_state.js`, split out by CARD-160 for
   exactly this reuse); serve the same file via a build-time copy from
   `src/nonogram/admin/static/`, with a test asserting the served copy is
   byte-identical to the source. UI glue that assumes Flask templating is
   rewritten in `player/`, not shared.
3. **Completion without the answer.** The page never has the solution
   (ADR-0038/R6), so "solved" is detected as *every row and column clue
   satisfied* — for a uniquely-solvable puzzle that is exactly the solution.
   The admin player's error COUNT (CARD-162) needs the answer and is therefore
   **not** in this card's scope — if the owner wants it publicly, that is a new
   architecture question, not a worktree decision.
4. **Play state** is kept in this browser's localStorage only (the shape
   CON-021's 2026-10-06 amendment allows for the admin player): resume on
   reload, nothing sent to any server, no accounts.
5. **Mobile-first.** Nearly every QR scan is a phone: thumb-sized tap targets
   (backlog already tracks "~18 px at 390 px" as too small on the admin page),
   pinch-zoom, clues sticky while panning. Desktop keyboard controls match the
   admin player where they exist.

## Acceptance criteria

Spec-derived (owner doc 2026-10-23); registry FR/ACs owed by the blocking
architect delta.

- AC-1: Given a bundle puzzle JSON, when `/play/<key>` loads, then the board
  renders that puzzle's grid and clues and cells can be marked through the
  three states with undo/redo, with the same state transitions as the admin
  player's `solver_state.js` (test: tests/test_public_player.py::
  test_play_page_renders_and_marks — Playwright over a static file server).
- AC-2: Given a board where every row and column clue is satisfied, when the
  last mark lands, then the page shows the solved state; given one wrong cell,
  it does not (test: tests/test_public_player.py::
  test_solved_fires_on_clue_satisfaction_only).
- AC-3: Given a partially solved puzzle, when the page reloads, then the marks
  are restored from localStorage, and no network request was ever issued other
  than fetching the page's own static assets (test: tests/test_public_player.py::
  test_resume_is_local_and_the_page_writes_nowhere).
- AC-4: Given a 390 px-wide viewport and the largest supported grid
  (limits.MAX_SIZE per side), when the page renders, then the board is
  playable: cells reachable, clues legible, no horizontal page scroll (test:
  tests/test_public_player.py::test_phone_viewport_is_playable).

## Engineering constraints

- EC(ADR-0038/R6): no asset served by the public player — HTML, JS, JSON,
  anything in `player/` or the bundle — contains a solution grid or data from
  which one cell of it can be read, for any puzzle, not just AC-2's examples.
  test: tests/test_public_player.py::test_served_tree_is_clean_of_answers
- EC(CON-021/as-amended): play state persists in this browser's localStorage
  only — for every interaction sequence, zero write requests leave the page.
  test: tests/test_public_player.py::test_no_write_request_for_any_interaction

## Guardrails

- G-1: The admin player is behavior-unchanged: src/nonogram/admin/static/solver.js,
  solver_state.js, admin.css, templates/puzzle_solve.html are read (copied), never
  edited (test: existing tests/test_puzzle_solver_page.py suite green).
- G-2: Do not edit src/nonogram/** at all except nothing — this card's code is
  the `player/` tree and its tests; the bundle format is CARD-282's and is
  consumed as-is.
- G-3: The runtime dependency baseline stays closed (ADR-0006/R1) and
  pyproject.toml gains no runtime dependency; test tooling reuses the existing
  pytest-playwright dev extra (test: tests/test_export_pdf.py::
  test_the_dependency_baseline_is_still_closed).
- G-4: Out of scope — error count, hints, scores, accounts, any server-side
  write (ONLINE_GAME_SPECIFICATION.md defers the write API to the December
  features; CON-021 forbids it today).

## System contract

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

- **FR:** — (untraced: the public-player FR is owed by the blocking architect
  delta; FR-044 defines the admin player whose behavior this page mirrors)
- **ADR:** ADR-0038 (plain-JS player + Playwright; R6 shapes completion
  detection), ADR-0006
- **Components:** — (the public surface has no component id yet — registering
  it is part of the blocking delta)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** the player board as merged by CARD-160..162 (reuse its
  look: clue boxes, fifth-line rule, header badge); register the public page in
  components.md
- **Screens:** /play/<key>
- **Standards:** forge:engineering-standards §11 (tokens-only styling, states,
  a11y minimum)

## Worktree notes

—
