# CARD-271: Big boards lose their bottom and left clues — keep clues in view whatever the fit ladder decides

**Status:** in_progress
**Priority:** P2
**Category:** ops
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/271-clues-stay-in-view
**Worktree:** ../PythonProject4-card-271
**Source:** quick — owner bug report 2026-10-22: "clues sometimes are missed at the bottom and at the left for big puzzles"; no handoff increment
**Idea:** —
**Wave:** 55
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_zoom.py
**Review score:** —
**Started:** 2026-10-23T15:05Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, with its mechanism verified in the code

**Symptom (owner).** On big puzzles the clues are sometimes missing at the
bottom and at the left.

**Mechanism — three converging causes, all by design, which is why "sometimes":**

1. **The plain-first bar.** `drawSettledLayout` (`solver.js:735`) draws
   today's single-gutter board first and tries no duplicate at all when its
   cells are already under `DOUBLE_MIN_CELL` (24 unzoomed px,
   `solver.js:395`). The code's own comment measures the consequence: at
   1280×720 that is *every board from about 24 columns up*. So the biggest
   puzzles — the ones CARD-212's duplicates were built for — are exactly the
   ones that render without bottom (and right) clues.
2. **The ladder prefers the row axis.** When both axes are big but only one
   duplicate fits, `layoutLadder` (`solver.js:660`) tries
   `{rowGutters: 2, colGutters: 1}` before `{colGutters: 2}` — the bottom
   clues are the first to be sacrificed.
3. **The mirror removes the left gutter on phones.** At ≤ 820 px with
   width > 15, CARD-193 draws the one row-clue gutter on the *right*
   (`isMirrored`, `solver.js:646`) — by owner decision, so on a phone a big
   board can lack both the left clues (mirror) and the bottom clues (cause 1).

And across all three: the gutters are ordinary table rows/columns, so once the
board overflows `.player-stage` (big board, or any board zoomed to 300%),
whatever gutter scrolls out of the viewport is simply gone — nothing keeps a
clue in view while the player works at the far corner. CARD-212's own stated
intent was *"a player scrolled to the far edge still has clues in view"*; the
duplicates deliver that only when they fit, and causes 1–3 are precisely the
cases where they don't.

## What to implement

**Keep clues in view on both axes, at every board size, scroll position and
zoom — without undoing any CARD-212/CARD-193 decision.** Recommended
mechanism: **sticky gutters as the fallback.**

1. When an axis renders with a single gutter (duplicate didn't fit, or the
   mirror holds), that gutter's clue boxes become `position: sticky` against
   the board's scroll container — column clues stick to the top (or the
   bottom, for a tfoot gutter), row clues to the left (or the right when
   mirrored) — so the clues stay in view wherever the player scrolls or
   zooms. Sticky boxes need an opaque background (`.player-clue` already has
   `var(--color-surface)`) and a z-index above cells; the corner boxes stick
   on both axes.
2. When a duplicate *does* fit, CARD-212's behaviour is untouched: same
   ladder, same rungs, same draw counts — the duplicates may also be sticky,
   but nothing about which layout is chosen changes.
3. Verify at implementation that `.player-stage` is the scroll container
   sticky resolves against (Chromium supports `position: sticky` on `th`/`td`
   in a scrolling block; if the overflow actually lives on an ancestor, say
   so and move it or stick against that — a finding, not a silent fix).
4. The heavy-rule pattern, circles (both twins), `.is-hinted`, the crosshair
   (CARD-267, if merged first) and the solved outline must all render
   correctly on and under sticky boxes — cells scroll *under* the gutter, so
   the gutter's own borders must fully cover its edge.
5. No layout decision moves into the state module: this is rendering
   (ADR-0038/R4), `solver_state.js` is not edited.

Out of scope, recorded: changing `DOUBLE_MIN_CELL`, the ladder order, or the
mirror decision. If the owner would rather lower the bar or re-order the
ladder instead of (or beside) sticky, that is an owner decision to surface at
the render, not a choice the implementation makes.

## Acceptance criteria

- **AC-1** (happy, the reported case): *Given* a 30×30 board at 1280×720 —
  today a plain board, cells under the doubling bar — *when* the stage is
  scrolled to the bottom-right cells, *then* that row's row clues and that
  column's column clues are inside the viewport (bounding-rect assertion),
  and the cells scrolled past are under, not over, the gutters. (test:
  `TestSolverClues_StayInViewOnAPlainBigBoard`)
- **AC-2** (happy, phone + mirror): *Given* a 30×30 board at 390 px (mirrored:
  row clues on the right only), *when* the board is scrolled in both axes,
  *then* the right row-clue gutter and the column-clue gutter remain in view.
  (test: `TestSolverPhone_MirroredGutterSticks`)
- **AC-3** (happy, zoom): *Given* any big board at 300 % zoom, *when* the
  stage is panned to each corner, *then* at least one clue box of the current
  row and of the current column is in view at every position. (test:
  `TestSolverZoom_CluesStayInViewWhileZoomed`)
- **AC-4** (edge, CARD-212 untouched): *Given* boards where the duplicates
  fit, *then* the ladder settles on exactly the rungs it settles on today —
  `TestSolverClues_TheLadderStopsAtTheFirstRungThatFits` and the whole
  existing clue/phone/zoom suites pass with their assertions unedited (new
  tests are added; existing ones only gain nothing). (gate: the named class,
  unedited)
- **AC-5** (edge, small board): *Given* a 15×15 board that fits its stage,
  *then* nothing observable changes: no scrolling, gutters where they are
  today, all existing small-board assertions green. (test:
  `TestSolverClues_SmallBoardsUnaffectedByStickiness`)
- **AC-6** (edge, visual integrity): *Given* a sticky gutter with the board
  scrolled behind it, *then* the gutter's background is opaque, its heavy
  rule edge is drawn, and circled clue numbers (CARD-188) render on it
  exactly as on a static gutter. (test:
  `TestSolverClues_StickyGutterRendersCleanly`)

## Guardrails

- G-1: `DOUBLE_MIN_CELL`, `BIG_SIDE`, `layoutLadder`'s rung order and
  `isMirrored` are not changed — this card adds visibility, it does not
  re-litigate fit (the owner may re-open those separately after seeing the
  render).
- G-2: Hand-written JS/CSS, tokens only (ADR-0038/R1; tests:
  `test_the_stylesheet_uses_tokens_not_literals`, plus a per-rule check if
  the fix adds colored values).
- G-3: `solver_state.js` is not edited (ADR-0038/R4); no request per mark or
  per scroll (ADR-0038/R2; test: `TestSolverMarking_NoRequestPerMark`).
- G-4: Marks, history, save, hint, circles and progress are untouched by
  scrolling — a scroll or a sticky repaint records nothing and saves nothing
  (CON-021).
- G-5: The redraw path keeps its draw-count pins: the ladder tests that count
  draws by draw marks run unedited (AC-4).
- G-6: The three renders — big board at desktop, phone width, 300 % zoom — are
  **produced and handed to the owner**, written to
  `~/Documents/nonogram-reviews/CARD-271/`. <!-- AMENDED 2026-10-23 by owner
  decision: "да, мержи по гейтам". As written this guardrail said *before
  merge*, which contradicts the owner's standing instruction that merges go on
  gates and renders are reviewed AFTER landing. The renders are still mandatory;
  what is not mandatory is waiting on an eyeball to merge. A reviewer must not
  file this as unsatisfied when the renders exist and the gates passed. -->

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check:
  review-lens)
- ADR-0038/R2 — no network request per mark (check:
  `TestSolverMarking_NoRequestPerMark`)
- ADR-0038/R3 — clues are the embedded JSON of `compute_clues`; the client
  never re-derives them (check: `TestSolverPage_ShowsTheClues`)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check:
  review-lens)
- CON-021 — play state persists only in this browser's localStorage; nothing
  per scroll (check: review-lens)

## Architecture context

- **FR:** FR-044 — this completes CARD-212's stated intent ("a player
  scrolled to the far edge still has clues in view") for the cases its
  duplicates cannot cover, and preserves CARD-193's mirror decision.
- **ADR:** ADR-0038/R1–R4.
- **CON:** CON-011 (30×30 is the biggest board — the worst case is bounded),
  CON-015/CON-016, CON-021.
- **Components:** COMP-009 (admin panel: static JS/CSS).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css`; sticky needs
  no new colors — background and rules already exist on `.player-clue`.
- **UI components:** `.player-clue` boxes and corners gain stickiness; no new
  elements.
- **Screens:** `/puzzles/<id>/solve` (and the editor's board, which shares
  the stylesheet — confirm no editor regression on the render).
- **Standards:** gutters opaque over scrolled cells; no animation on stick;
  the accessibility tree is unchanged (sticky is visual only).

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** (run them, do not rewrite them):

| name | resolves to |
|------|-------------|
| `TestSolverClues_TheLadderStopsAtTheFirstRungThatFits` | `tests/test_puzzle_solver_clues.py:2114` |
| `TestSolverMarking_NoRequestPerMark` | `tests/test_puzzle_solver_marking.py:1377` |
| `TestSolverPage_ShowsTheClues` | `tests/test_puzzle_solver_page.py:206` |
| `test_the_stylesheet_uses_tokens_not_literals` | `tests/test_admin_design_tokens.py:219` |

**To be written by this card** (across `tests/test_puzzle_solver_clues.py`,
`tests/test_puzzle_solver_phone.py`, `tests/test_puzzle_solver_zoom.py`) —
none exists yet; report them as written, never as passing before they exist:
`TestSolverClues_StayInViewOnAPlainBigBoard`,
`TestSolverPhone_MirroredGutterSticks`,
`TestSolverZoom_CluesStayInViewWhileZoomed`,
`TestSolverClues_SmallBoardsUnaffectedByStickiness`,
`TestSolverClues_StickyGutterRendersCleanly`.

## Worktree notes

- **[The "sometimes" is now enumerable]** The three causes above predict
  exactly when clues go missing; AC-1..AC-3 pin one representative of each.
  If reproduction finds a *fourth* way (e.g. a resize race in `redraw()`),
  that is a finding to record here, not to fold silently into the fix.
- **[Sticky-in-table risk]** `position: sticky` on table cells has
  per-browser quirks; the suite runs Chromium only (ADR-0038/R8), so assert
  what Chromium does and record the bound — other browsers are untested, and
  that is the project's standing browser-test boundary, not this card's gap.
- **[Conflict note]** Touches overlap CARD-267 (crosshair: `solver.js`, CSS)
  and CARD-269 (hint ladder: same files) and CARD-270 (`admin.css`,
  `tokens.css`); the dispatcher serializes same-wave overlaps. If CARD-267
  merges first, AC-6's "renders cleanly" check includes the crosshair tint on
  a sticky gutter.

## [Dispatch note 2026-10-23] Two prerequisites measured before the brief, because both could have made this card unverifiable

**1. Every one of AC-1..AC-6 is a browser test, and ADR-0038/R8 says they fail or skip *loudly*.** If
Chromium were absent they would all **skip green** and the card would "pass" having verified nothing —
the green-with-skips shape this board has already carded (a skipped run reports the same collected count
and the same exit 0 as a verified one; only the **passed** count separates them). Measured before
dispatch: `playwright` imports, five Chromium builds are in `~/Library/Caches/ms-playwright/`, and the
card's three test files run **105 passed, 0 skipped**. So this card's evidence is real, and **any skip in
those files during this card is a signal, not normal**.

**2. The inner loop does not need the full suite.** `scripts/impact_set.py` over this card's six
`Touches` returns a real **26-file selection**, not `FULL` — unlike CARD-264, whose `CLAUDE.md` tripped
the fail-closed branch and forced six full gates in one day. The selection is pinned in the brief, so the
per-round cost is ~2 minutes of tests instead of ~24, and the full suite runs **once**, at the merge gate.

**Conflict note for the dispatcher, not an action for this card.** `src/nonogram/admin/static/solver.js`
and `admin.css` are the board's busiest hotspot: CARD-280 (solved reveal), CARD-267 and CARD-277 all land
there. This card holds them for its duration; the other three must not run concurrently with it.
