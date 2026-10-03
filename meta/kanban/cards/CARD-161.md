# CARD-161: Mark cells in the solver: tools, click cycle, drag, undo and redo

**Status:** blocked
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** owner design doc "Nonograms - Print layout" (Google Doc 1pJKF2qX6mC9qw4Cf9Nv3hblTDmtoHwP5Tb8wzK1_WqM), section "Online solver"
**Idea:** —
**Wave:** 31
**Depends on:** CARD-160
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_marking.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** architect delta — same as CARD-160 (CON-002 amendment, solver FR, client/testing ADR), plus CARD-160 itself

## What to implement

The marking controls the owner's document lists, kept "as simple as
possible, similar to puzzle-nonograms.com". The document says no more
options than these for now.

1. **Tool picker:** three tools: **black** (filled), **white** (marked
   empty, drawn as a dot or a small cross), and **undecided** (clears a
   cell). Exactly one tool is active. Pick it by button and by keyboard.
2. **Click cycle in the grid:** clicking a cell cycles it: 1st click
   black, 2nd click white, 3rd click clear. This is independent of the
   active tool, as the document describes.
   **Open question, record your call in the card:** does a click cycle, or
   apply the active tool? The document describes both. One reading: tools
   govern drags, and a single click cycles. Another: a click applies the
   tool and the cycle exists only when no tool is chosen. Pick one, make it
   obvious on screen, and note the reasoning.
3. **Drag to mark a region:** press on a cell and drag, and every cell
   passed over takes the active tool's state. Constrain a drag to the row
   or column it started in, as the reference site does; that's the usual
   nonogram behaviour and avoids smearing diagonals. One drag is one
   history step.
4. **Undo and redo:** buttons plus Ctrl/Cmd+Z and Shift+Ctrl/Cmd+Z. Undo
   reverts a whole stroke (one click, or one drag). A new mark after an
   undo drops the redo stack.
5. **Touch:** tap and drag must work on a tablet-sized touch screen. This
   is the cheapest moment to get it right, since phones are where printed
   QR codes will land later.

State changes go through CARD-160's pure state module (apply stroke,
undo, redo), so the logic is testable without a browser. Rendering only
reflects state.

## Acceptance criteria

- **AC-1:** Clicking one cell three times takes it unknown → filled →
  empty → unknown, and the board shows black, then a dot or cross, then
  blank.
  *test: TestSolverMarking_ClickCycles*
- **AC-2:** Dragging across five cells of a row with the black tool fills
  exactly those five. A drag that wanders off the row still marks only
  its starting row.
  *test: TestSolverMarking_DragMarksOneLine*
- **AC-3:** After a drag and two clicks, three undos restore the empty
  board, three redos restore all marks, and a new mark after one undo
  empties the redo stack.
  *test: TestSolverMarking_UndoRedoByStroke*
- **AC-4:** The state module's apply/undo/redo keeps the history
  consistent over a seeded random sequence of at least 500 strokes:
  replaying the history from blank always reproduces the current board.
  *test: PropertyTest_SolverHistory_ReplayReproducesTheBoard*
- **AC-5:** Every control (tools, undo, redo) is reachable and works from
  the keyboard and has an accessible name.
  *test: TestSolverMarking_KeyboardAndLabels*

## Guardrails

- G-1: No new runtime dependency (ADR-0006/R1); plain JS as decided in
  CARD-160's ADR.
- G-2: The board does not reveal correctness while marking. Errors and
  the solved state are CARD-162's, so this card must not leak whether a
  mark is right.
- G-3: No server round-trip per mark; marking is entirely client-side.

## Architecture context

- **FR:** — (pending the architect delta; see Blocked by)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ (tokens only; register the tool picker in components.md)
- **Screens:** /puzzle/<id>/solve
- **Reference:** puzzle-nonograms.com; the doc's screenshots were not readable through the Drive text export

## Worktree notes

- [Origin] Cut 2026-10-03 from the owner's design doc at the owner's request.
- [Estimate] 1d is the card-size ceiling. If the click-cycle/tool question
  and touch support push it over, split touch support into its own card
  instead of growing this one.
