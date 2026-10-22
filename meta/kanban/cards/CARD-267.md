# CARD-267: Crosshair — the player highlights the hovered cell's row, column and their clues

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/267-player-crosshair
**Worktree:** —
**Source:** quick — owner decision 2026-10-22 (player-convenience session, option 1: "highlight row/column for selected cell so that the gaze don't slide away"); no handoff increment
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_crosshair.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- The board is one `<table>`: `th.player-clue.is-col` boxes above (and, on big
  boards, below) the grid, `th.player-clue.is-row` to the left (and right),
  `td.player-cell` cells with `data-row`, `data-col` and `data-state`
  (`solver.js`, `drawBoard`). Each clue box carries its 0-based line in
  `data-line`, which is what pairs a duplicate gutter's box with its twin
  (CARD-212) — `clueNumbersOf` collects spans by axis + `data-line`, never by
  DOM order, and `paintCircles` (CARD-188) paints **both** twins.
- Pointer handling lives in `solver.js` (pointerdown/move/up with a drag
  preview; clue boxes keep `touch-action: auto` and are not markable). Nothing
  reacts to a pointer that is merely *over* a cell.
- The precedent for a pure view behaviour is Zoom (CARD-195, template comment):
  "It is a view setting only: it changes no board state, is never saved" — the
  crosshair is the same class of thing, and even less: it is not a setting, it
  has no toggle and no persistence at all.

**What changes.** When the player's attention is on a cell, the board shows a
crosshair: that cell's whole row and whole column are lightly tinted, and the
row's and column's clue boxes are highlighted — so the eye can travel from a
cell to its clues and back without sliding onto a neighbouring line.

1. **Which cell has the crosshair.** On a pointer that can hover (mouse, pen in
   range): the cell under the pointer; leaving the board clears it. During any
   marking gesture: the cell the gesture is currently over. On touch (no
   hover): the crosshair appears with the gesture and **stays on the last
   touched cell** after pointerup — a phone player keeps their place between
   taps. A fresh page load shows no crosshair.
2. **What gets marked.** A class (suggested: `.is-crossed`) on every
   `td.player-cell` of the row and of the column, and on every clue box whose
   axis + `data-line` matches — on a doubled axis that is **both** twins, the
   same rule as circles. Exactly one row and one column carry it at a time.
3. **Rendering only.** No change to `solver_state.js` — the crosshair is not
   player state (ADR-0038/R4): never in a stroke, never in the undo history,
   never in the save, invisible to `serializeState`. It changes no
   `data-state`.
4. **Pointer-move cost.** A move within the same cell does nothing; a move to a
   new cell toggles the old row/column/clues off and the new on — never a
   board redraw, and no work per move beyond the two line sweeps.
5. **Colors from tokens.** The tint must keep all four `data-state` looks
   (unknown / filled / empty / maybe) plainly distinguishable, and must not be
   confusable with CARD-188's clue circles. New values go in `tokens.css`.
6. **Redraws.** After a mirror-breakpoint or zoom redraw (`drawBoard` reruns),
   no stale `.is-crossed` survives — cleared or recomputed, either is fine, a
   half-painted crosshair is not.
7. **Accessibility.** The crosshair is decorative and redundant by nature (it
   repeats where the pointer already is): it adds **no** ARIA attributes, no
   live announcements, and must not change what a screen reader reads per cell
   or clue.

Out of scope, recorded so the review does not invent it: hovering a *clue box*
does not light its line (a candidate follow-up, not this card), and the
crosshair gets no on/off setting unless the owner asks for one after seeing it.

## Acceptance criteria

- **AC-1** (happy): *Given* a rendered puzzle, *when* the pointer hovers cell
  (r, c), *then* every cell of row r, every cell of column c, and the clue
  boxes with `data-line` r (row axis) and c (column axis) carry the crosshair
  marker, and no other cell or clue box does. (test:
  `TestSolverCrosshair_RowColumnAndCluesLight`)
- **AC-2** (happy, move): *Given* a crosshair on (r, c), *when* the pointer
  moves to (r2, c2), *then* the old row/column/clues are cleared and exactly
  the new ones are marked. (test: `TestSolverCrosshair_FollowsThePointer`)
- **AC-3** (happy, doubled board): *Given* a board big enough for CARD-212's
  duplicate gutters, *when* a cell is hovered, *then* **both** twins of its
  row clue and **both** twins of its column clue carry the marker. (test:
  `TestSolverCrosshair_LightsBothTwinsOnADoubledBoard`)
- **AC-4** (happy, touch): *Given* a touch drag across cells, *then* the
  crosshair follows the cell under the finger during the drag, the drag still
  marks exactly as today, and after pointerup the crosshair remains on the
  last touched cell. (test: `TestSolverCrosshair_TouchKeepsTheLastCell`)
- **AC-5** (edge, leave): *Given* a hover crosshair, *when* the mouse leaves
  the board, *then* the crosshair clears. (test:
  `TestSolverCrosshair_ClearsWhenThePointerLeaves`)
- **AC-6** (edge, view-only): *Given* any sequence of hovers, *then* no cell's
  `data-state` changed, the undo history is exactly as without them, and no
  save was written — and `solver_state.js` is not edited by this card at all.
  (test: `TestSolverCrosshair_IsPureView`; the no-edit clause is G-5,
  structural)
- **AC-7** (edge, redraw): *Given* a crosshair, *when* the board redraws
  (viewport crosses the mirror breakpoint, or zoom), *then* no stale marker
  survives the redraw. (test: `TestSolverCrosshair_NoStaleMarkerAfterRedraw`)
- **AC-8** (edge, a11y + tokens): *Given* the shipped page, *then* hovering
  adds no ARIA attribute anywhere, and the new CSS rules take every color from
  tokens — with a per-rule check in the token test file, CARD-212 G-7 style.
  (tests: `TestSolverCrosshair_AddsNoAria`,
  `test_the_crosshair_tint_comes_from_tokens`)

## Guardrails

- G-1: Clues come from the embedded `compute_clues` JSON; the client never
  re-derives them (ADR-0038/R3; test: `TestSolverPage_ShowsTheClues`).
- G-2: Hand-written JS/CSS only — no framework, no build step, no vendored
  library (ADR-0038/R1).
- G-3: No request per mark — and none per hover either (ADR-0038/R2; test:
  `TestSolverMarking_NoRequestPerMark`).
- G-4: Styling from tokens only (test:
  `test_the_stylesheet_uses_tokens_not_literals`, plus the per-rule check in
  AC-8).
- G-5: `src/nonogram/admin/static/solver_state.js` is not edited — the
  crosshair is rendering, and a crosshair that needs the state module has been
  designed wrong (ADR-0038/R4).
- G-6: Marking behaviour is untouched: click sequence, drag preview/commit,
  Region, hint, circles, counters and the save all behave exactly as today
  (the existing `tests/test_puzzle_solver_*.py` files run unedited).

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check:
  review-lens)
- ADR-0038/R2 — no network request per mark (check:
  `TestSolverMarking_NoRequestPerMark`)
- ADR-0038/R3 — clues are the embedded JSON of `compute_clues`; the client
  never re-derives them (check: `TestSolverPage_ShowsTheClues`)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check:
  review-lens)
- CON-021 — interactive play only in the admin panel's player; nothing
  persisted server-side (check: review-lens)

## Architecture context

- **FR:** FR-044 (the player). This is a view convenience inside the already
  decided player; the owner decided it 2026-10-22. FR-044's statement is not
  amended by this card — if the architect pipeline wants it recorded, the
  owner decision goes through `inputs/raw-requirements.md` as usual.
- **ADR:** ADR-0038/R1–R4.
- **CON:** CON-015/CON-016 (the admin door), CON-021.
- **Components:** COMP-009 (admin panel: static JS/CSS, template).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css`; every value is
  a token (G-4).
- **UI components:** `.player-board`, its `td.player-cell` and
  `th.player-clue` boxes — the crosshair is a class on existing elements, no
  new elements.
- **Screens:** `/puzzles/<id>/solve`.
- **Standards:** decorative highlight, no ARIA; all four cell states stay
  distinguishable under the tint; owner validates the look on a real puzzle
  render before merge (standing practice for player visuals).

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** (run them, do not rewrite them):

| name | resolves to |
|------|-------------|
| `TestSolverPage_ShowsTheClues` | `tests/test_puzzle_solver_page.py:206` |
| `TestSolverMarking_NoRequestPerMark` | `tests/test_puzzle_solver_marking.py:1377` |
| `test_the_stylesheet_uses_tokens_not_literals` | `tests/test_admin_design_tokens.py:219` |

**To be written by this card** (in `tests/test_puzzle_solver_crosshair.py`,
except the token check, which joins `tests/test_admin_design_tokens.py`) —
none exists yet; report them as written, never as passing before they exist:
`TestSolverCrosshair_RowColumnAndCluesLight`,
`TestSolverCrosshair_FollowsThePointer`,
`TestSolverCrosshair_LightsBothTwinsOnADoubledBoard`,
`TestSolverCrosshair_TouchKeepsTheLastCell`,
`TestSolverCrosshair_ClearsWhenThePointerLeaves`,
`TestSolverCrosshair_IsPureView`,
`TestSolverCrosshair_NoStaleMarkerAfterRedraw`,
`TestSolverCrosshair_AddsNoAria`,
`test_the_crosshair_tint_comes_from_tokens`.

## Worktree notes

—
