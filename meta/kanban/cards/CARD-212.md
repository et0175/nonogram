# CARD-212: Big boards repeat their clues on both sides — left and right, top and bottom

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/212-clues-both-sides
**Worktree:** ../PythonProject4-CARD-212
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (item 3: "Solver - mobile mode - clues - show clues on both sides of the puzzle (on the right and on the left and on the top and on the bottom) for big puzzles, not just in the right or bottom")
**Idea:** —
**Wave:** 37
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_mirror.py, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_zoom.py
**Review score:** —
**Started:** 2026-10-14T14:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- The board is one `<table>`: `th.player-clue.is-col` boxes above the grid,
  `th.player-clue.is-row` boxes to the left, `td.player-cell` cells
  (`solver.js:293-350`, `drawBoard`).
- CARD-193 added a **mirror**, not a duplicate: when `payload.width > 15` *and*
  the viewport matches `(max-width: 820px)`, `drawBoard` appends each body row's
  row-clue box **after** its cells and the head row's corner after the last
  column clue, and `.player-board.is-mirrored` redraws the borders that the
  moved `:last-child` rules stop matching (`solver.js:303-347`,
  `admin.css:507-531`). So on a phone a wide board shows its row clues on the
  **right only** — the left gutter is gone, not doubled. Column clues are
  always top-only.
- `mirrorQuery.addEventListener("change", …)` redraws when the viewport crosses
  820 px; zoom (CARD-195) and the recorded board survive the redraw
  (`solver.js:404-476`).

**What changes.** For a big board, the clues appear on **both** sides of each
axis: row clues left *and* right, column clues above *and* below.

1. **Threshold.** Keep one rule, do not invent a second: the existing
   `payload.width > 15` is the "big" test for the row axis; add the symmetric
   `payload.height > 15` for the column axis. Each axis is doubled
   independently — a 30×12 board doubles its row clues and not its column clues.
   (Record the chosen constant once; `solver.js` already has it inline in two
   places, which is one too many.)
2. **Not phone-only.** The owner's framing is "mobile mode … for big puzzles",
   and the mirror was phone-only because a phone has no room for both gutters.
   Doubling needs *more* room, not less, so apply it when the viewport can
   afford it and fall back to CARD-193's single mirrored gutter when it cannot:
   the duplicate renders when the doubled gutters still leave the grid at or
   above the phone-fit cell minimum CARD-193/CARD-182 established; otherwise the
   board keeps exactly today's mirrored rendering. State the measured rule in
   the Worktree notes.
3. **Rendering.** `drawBoard` gains the second gutter per doubled axis: a
   trailing `th.player-clue.is-row` after each body row's cells, a trailing
   `<tr>` of `th.player-clue.is-col` boxes under the grid, and the two extra
   corners. The duplicate carries the **same numbers in the same order** as its
   twin (a bottom column-clue box reads top-to-bottom like the top one — this
   is a repetition, never a mirror of the sequence).
4. **Circles stay in sync.** `paintCircles` (`solver.js:559`) and
   `clueNumbersOf` (`:548`) collect `.player-clue-num` spans per axis and line;
   with two gutters there are two spans per number, and **both** must carry
   `.is-circled` (CARD-188's rule) and the `--player-clue-digits` custom
   property. A duplicate that does not circle is worse than no duplicate.
5. **Accessibility.** The duplicate is a visual repetition; a screen reader must
   not read every clue twice. Give the second gutter `aria-hidden="true"` and
   keep the first as the labelled one (the `aria-label` per box,
   `clueBox` at `solver.js:278`).
6. Borders: the heavy/thin rule pattern must still read correctly on all four
   sides — the `:last-child` border rules that CARD-193 already had to redraw
   for the mirrored case need the same treatment for the new trailing boxes
   (`admin.css:505-531`).

## Acceptance criteria

- **AC-1** (happy): *Given* a 30×25 puzzle on a viewport with room for both
  gutters, *when* the player page renders, *then* each row's clue appears both
  left of and right of the grid, and each column's clue appears both above and
  below it. (test: `TestSolverClues_BigBoardRepeatsBothAxes`)
- **AC-2** (happy, per-axis): *Given* a 30×12 puzzle, *when* it renders, *then*
  the row clues are doubled and the column clues are not. (test:
  `TestSolverClues_AxesDoubleIndependently`)
- **AC-3** (happy, same numbers): *Given* any doubled axis, *when* it renders,
  *then* the duplicate gutter's numbers equal its twin's, line by line and in
  the same order. (test: `TestSolverClues_DuplicateReadsTheSameSequence`)
- **AC-4** (happy, circles): *Given* a clue number CARD-188's rule circles,
  *when* the board is doubled, *then* both of its spans carry `.is-circled`,
  and both lose it when the marks change. (test:
  `TestSolverClues_CirclesPaintBothGutters`)
- **AC-5** (edge, small board): *Given* a 15×15 puzzle, *when* it renders,
  *then* the clues are exactly as they are today — one top gutter, one left
  gutter, no duplicates. (test: `TestSolverClues_SmallBoardUnchanged`)
- **AC-6** (edge, narrow viewport): *Given* a 390 px phone and a 30×30 puzzle,
  *when* it renders, *then* the board falls back to CARD-193's single mirrored
  row-clue gutter rather than shrinking the cells below the phone-fit minimum.
  (test: `TestSolverPhone_FallsBackToMirrorWhenDoublingWouldNotFit`)
- **AC-7** (edge, a11y): *Given* a doubled axis, *when* the accessibility tree
  is read, *then* each clue is exposed once — the duplicate gutter is
  `aria-hidden`. (test: `TestSolverClues_DuplicateIsAriaHidden`)
- **AC-8** (edge, zoom + viewport change): *Given* a doubled board at 150 %
  zoom, *when* the viewport crosses the breakpoint and the board redraws,
  *then* the marks, the zoom and the circles all survive. (test:
  `TestSolverZoom_SurvivesADoubledRedraw`)

## Guardrails

- G-1: Clues come from the embedded `compute_clues` JSON; the client never
  re-derives them from the solution (ADR-0038/R3; test:
  `TestSolverPage_ShowsTheClues`).
- G-2: Hand-written JS/CSS only — no framework, no build step, no vendored
  library (ADR-0038/R1).
- G-3: The pure state module stays DOM-free; doubling is a rendering concern
  (ADR-0038/R4).
- G-4: No request per mark (ADR-0038/R2; test:
  `TestSolverMarking_NoRequestPerMark`).
- G-5: Tap targets stay at CARD-182's minimum on a 390 px phone (test:
  `test_puzzle_solver_phone.py`).
- G-6: Do not change the brush/Region controls — CARD-211 owns those this wave.
- G-7: Styling from tokens only (test: `test_the_stylesheet_uses_tokens_not_literals` (and, for a rule added by a card, a per-rule check like `test_the_region_toggles_pressed_look_comes_from_tokens`)).

## System contract

- ADR-0038/R3 — the player's clues are the embedded JSON of `compute_clues` of
  the stored grid; the client never re-derives them (check:
  `TestSolverPage_ShowsTheClues`)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check:
  review-lens)
- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check:
  review-lens)
- ADR-0038/R2 — no network request per mark (check:
  `TestSolverMarking_NoRequestPerMark`)
- CON-021 — interactive play only in the admin panel's player (check:
  review-lens)

## Architecture context

- **FR:** FR-044 (the player), and CARD-193's phone-fit/mirror behaviour it
  extends.
- **ADR:** ADR-0038/R1–R4.
- **CON:** CON-011 (10–30 cell sides — the upper bound on how big "big" gets),
  CON-015/CON-016, CON-021.
- **Components:** COMP-009 (admin panel: static JS/CSS, template).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css` (no
  `meta/design/` in this repo); every value is a token.
- **UI components:** `.player-board` and its clue boxes — the new trailing
  gutters reuse `.player-clue.is-row` / `.is-col` and the mirrored-border rules
  CARD-193 added.
- **Screens:** `/puzzles/<id>/solve`.
- **Standards:** the duplicate is decorative (`aria-hidden`); the labelled
  gutter stays the single accessible source of each clue.

## Worktree notes

—
