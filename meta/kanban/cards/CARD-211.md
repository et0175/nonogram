# CARD-211: Region leaves the brush menu and becomes its own control

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/211-region-own-control
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (item 2: "Solver please place "Region" select option separately from "Black\\White\\Maybe\\Undecided" dropdown")
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_brush_menu.py, tests/test_puzzle_solver_page.py, tests/test_admin_design_tokens.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- CARD-194 collapsed the brushes into **one** trigger button plus a
  `role="menu"` of **five** `role="menuitemradio"` items:
  `Black`, `White`, `Maybe`, `Undecided`, `Region`
  (`puzzle_solve.html:109-113`). Region is therefore a radio *among the
  brushes*, although it is not a brush: it is a modifier on how the next drag
  behaves.
- The trigger's label reflects both: its visible text is the chosen brush, or
  `Region · <brush>` with Region on; its `aria-label` is `Brush: <chosen>`
  (template comment, `puzzle_solve.html:21-24`).
- Behaviour today: with Region on, a drag (any pointer type) marks with the
  chosen brush and **Region turns itself off once that drag is recorded**; with
  Region off, a mouse drag still marks, while touch/pen drags scroll the page.
  `.player-board.is-region` switches the cells' `touch-action`
  (`admin.css:557`).

**What changes.** Region becomes a control of its own, outside the menu:

1. The brush menu holds exactly four items — `Black`, `White`, `Maybe`,
   `Undecided`. The trigger shows the chosen brush and its `aria-label` stays
   `Brush: <chosen>`.
2. A separate **Region** toggle button sits beside the brush trigger in the same
   `player-slot` row: `aria-pressed="true|false"` (a toggle, not a radio — it is
   a mode, and `aria-pressed` is what a screen reader announces as on/off),
   focusable in the same tab order, labelled `Region`.
3. The semantics are **unchanged** from CARD-194: turning Region on makes the
   next drag mark with the current brush on any pointer type, and Region turns
   itself off once that drag is recorded (the toggle's `aria-pressed` flips back
   with it). Do not take the opportunity to make it sticky — that is a separate
   owner decision, not this card's.
4. `.player-board.is-region` keeps driving `touch-action`; the toggle is now the
   single thing that sets it.
5. Keep the state logic in the pure module and the DOM wiring in `solver.js`
   (ADR-0038/R4): "is Region armed" is state, the button is rendering.

## Acceptance criteria

- **AC-1** (happy): *Given* the player page, *when* the brush menu is opened,
  *then* it holds exactly four `menuitemradio` items (Black, White, Maybe,
  Undecided) and no Region item. (test:
  `TestSolverBrushMenu_HoldsFourBrushesOnly`)
- **AC-2** (happy): *Given* the player page, *when* it loads, *then* a Region
  toggle button exists outside the menu, with `aria-pressed="false"`, reachable
  by keyboard in the toolbar's tab order. (test:
  `TestSolverBrushMenu_RegionIsItsOwnToggle`)
- **AC-3** (happy): *Given* Region is pressed, *when* the player drags along a
  row with the Black brush, *then* every cell of the drag is marked black, and
  afterwards the toggle reads `aria-pressed="false"` again. (test:
  `TestSolverRegion_ArmedDragMarksThenDisarms`)
- **AC-4** (happy): *Given* Region is not pressed, *when* a touch drag starts on
  a cell, *then* nothing is marked and the page scrolls (today's behaviour).
  (test: `TestSolverRegion_UnarmedTouchDragStillScrolls`)
- **AC-5** (happy, brush independence): *Given* any brush is selected, *when*
  Region is pressed and released, *then* the selected brush is unchanged — the
  two controls do not overwrite each other. (test:
  `TestSolverRegion_DoesNotChangeTheBrush`)
- **AC-6** (edge, announcements): *Given* a screen reader, *when* Region is
  pressed, *then* the state change is announced through the existing
  `#puzzle-player-announce` live region, not by a label the user must re-read.
  (test: `TestSolverRegion_AnnouncesItsState`)

## Guardrails

- G-1: Hand-written JS/CSS only — no framework, no build step, no vendored
  library (ADR-0038/R1).
- G-2: Marking, undo/redo, error count, percent, hints and resume keep working
  exactly as they do (tests: `test_puzzle_solver_marking.py`,
  `test_puzzle_solver_progress.py`, `test_puzzle_solver_resume.py`,
  `test_puzzle_solver_hint.py`).
- G-3: No request per mark — the board stays client-side (ADR-0038/R2; test:
  `TestSolverMarking_NoRequestPerMark`).
- G-4: Styling from the design tokens only, no hard-coded colours or sizes
  (test: `TestAdminDesignTokens_NoRawValues`).
- G-5: Do not change the clue rendering or the phone fit/mirror behaviour —
  CARD-212 owns those this wave.

## System contract

- ADR-0038/R1 — the player's client is hand-written JS/CSS served as static
  files; no framework, build step or vendored library (check: review-lens)
- ADR-0038/R4 — the player's state logic lives in a pure module with no DOM
  access, separate from rendering (check: review-lens)
- ADR-0038/R2 — no network request per mark (check:
  `TestSolverMarking_NoRequestPerMark`)
- CON-021 — interactive play exists only as the admin panel's player, behind the
  admin door (check: review-lens)

## Architecture context

- **FR:** FR-044 (the admin panel's puzzle player).
- **ADR:** ADR-0038 (the player's client architecture) — R1, R2, R4.
- **CON:** CON-015, CON-016 (the admin door), CON-021.
- **Components:** COMP-009 (admin panel: template, static JS/CSS).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** the admin panel's own `static/tokens.css` +
  `static/admin.css` (there is no `meta/design/` in this repo) — every value
  comes from a token, as `TestAdminDesignTokens_NoRawValues` enforces.
- **UI components:** the player toolbar (`.player-toolbar`, `.player-slot`,
  `.player-tools`) — the Region toggle is a new control in the existing row;
  reuse the `.btn.btn-outline-secondary` pattern the history buttons use.
- **Screens:** `/puzzles/<id>/solve` (`puzzle_solve.html`).
- **Standards:** the toggle must carry its state in `aria-pressed`, be
  keyboard-reachable, and keep the 44 px tap target CARD-182 established on a
  390 px phone.

## Worktree notes

—
