// Puzzle player — renderer (TERM-037, FR-044, CARD-160; ADR-0038).
//
// Not the uniqueness solver (COMP-005, src/nonogram/solver/): this draws the
// page a person solves a stored puzzle on. Plain JavaScript, no framework, no
// build step (ADR-0038/R1). Board state lives in the pure module
// solver_state.js (ADR-0038/R4); this file is the only one that touches the
// DOM, and it only ever *reads* a board to paint it — and, since CARD-162,
// reads payload.solution to show the error count and the solved state.
//
// THE PAYLOAD — the page's whole contract with the server. puzzle_solve.html
// embeds it as JSON in <script type="application/json" id="puzzle-player-data">,
// built by admin/app.py's puzzle_solve route:
//   {
//     "id":       string,             the stored puzzle's id
//     "width":    int >= 1,           W, columns (the stored grid's, not the row's column)
//     "height":   int >= 1,           H, rows
//     "rows":     [[int, ...]] * H,   row clues, top to bottom
//     "columns":  [[int, ...]] * W,   column clues, left to right
//     "solution": [[bool] * W] * H    the solution grid (admin only — ADR-0038/R6)
//     "mode":     "edit", optional      see EDIT MODE below
//   }
// "rows"/"columns" are compute_clues(stored grid) — the one encoder, never
// re-derived here (ADR-0038/R3). A line with no filled cell is [0] and is shown
// as the single number "0". A payload that is absent or not of this shape is
// refused: an alert replaces the board and window.puzzlePlayer stays unset.
//
// EDIT MODE (CARD-246). The manual editor (templates/puzzle_edit.html,
// static/puzzle_edit.js) is a SECOND CONSUMER of this board, not a second
// board: there is one grid renderer in the panel and this is it (CARD-246
// G-2, for the reason ADR-0036/R3 gives for round marks — two implementations
// of one picture drift). The editor's page serves exactly the payload above
// with "mode": "edit" added, and this file reads that one flag. Anything else
// in `mode`, the key being absent included, is the player, unchanged.
// What the flag changes — FIVE reads of `editing`, and nothing else
// (CARD-246 review cycle 1, F-009: the list said three and the code read it
// four times, which is how a contract stops being one):
//   * the board STARTS on payload.solution (solver_state.js boardOfGrid:
//     FILLED/EMPTY, never UNKNOWN) rather than blank — the owner opens the
//     stored picture and paints on it;
//   * the browser SAVE is off (no localStorage read, no write, nothing
//     removed). The player's save is keyed by the puzzle's id, so an editor
//     sharing it would overwrite the solve-in-progress of the very puzzle
//     being edited — the player is not regressed (G-1), and this is the seam
//     where it would have been;
//   * the counters, the solved banner, the solved LOCK and the clue circles
//     are off (showProgress returns at once). All four are statements about
//     a board measured AGAINST payload.solution, and in edit mode the
//     solution is the thing being changed: the board starts equal to it, so
//     the lock would fire before the first stroke and the error count would
//     count departures from the grid the owner is editing;
//   * nextHint answers null. A hint reveals payload.solution, and in edit
//     mode that is the grid being rewritten, so a "hint" would paint the
//     owner's edit back to the stored picture. The editor's page ships no
//     Hint button, so this guard is not reached today (`actions.hint?.`
//     short-circuits its own argument) — it stays because the rule belongs
//     to the MODE and not to which elements a template happens to carry: a
//     Hint button added to an edit page must not be able to undo an edit;
//   * the recorded board announces itself. In edit mode, and only there,
//     commit() dispatches BOARD_CHANGE on `document` — see BOARD CHANGE
//     below.
//
// BOARD CHANGE (CARD-246 review cycle 1, F-002/F-004). The editor's save bar
// offers Approve for ONE grid: the grid whose grade is on screen, captured
// when Save was pressed. The moment the board stops being that grid the
// offer is wrong, and static/puzzle_edit.js withdraws it — so it has to hear
// about a change rather than go looking for one. This event is that seam,
// and it is dispatched from commit(), the single place a change is RECORDED:
// a click, a drag, undo, redo, a confirmed Clear and setBoard all pass
// through it, so the editor needs no list of controls to watch (a list is
// what goes stale when the next control is added). An uncommitted mid-drag
// preview (`show`) is deliberately not announced: nothing is recorded yet
// and the drag's own commit follows.
// The editor's page leaves out the elements that go with them (the counters,
// the banner and Hint); everything else — the brush menu, Region, undo, redo,
// reset, zoom, the announce line — is the player's own markup and its own
// code here. The grid still ships as `solution` under the same key: in edit
// mode it is the stored grid the editor opens on, which is why it is also
// still validated as a grid.
//
// THE LIVE PLAYER — window.puzzlePlayer, set once the board is drawn:
//   payload            the parsed payload above
//   getBoard()         the current board (a solver_state.js value) — the
//                      player's own copy, never an object passed to setBoard
//   setBoard(board)    replace the board and repaint; a value that is not a
//                      board (solver_state.js isBoard: frozen, own data
//                      integer sides >= 1, a frozen genuine Array of exactly
//                      width*height cells, every index an own element holding
//                      a known state — no holes) or a board of other
//                      dimensions is refused with RangeError before anything
//                      is painted, and the current board and DOM are kept;
//                      an accepted board is copied (copyBoard) and the copy
//                      is stored and painted; it also starts a new marking
//                      history at that board (nothing to undo or redo), the
//                      error count and solved state are re-derived from it,
//                      and an open reset confirmation is closed (see "reset")
// Boards are trusted in-page values (see solver_state.js).
//
// MARKING (CARD-161, FR-044 AC-303..AC-311; the "?" mark, CARD-186; a click
// follows the brush, CARD-189; one brush dropdown, CARD-194, with Region
// beside it as a toggle of its own, CARD-211). The
// strokes and the undo/redo history are solver_state.js values (clickStroke,
// dragStroke, resetStroke, record, undo, redo); this file only turns input into those calls and
// paints the resulting board. The marking code (wireMarking) does not read
// payload.solution — it only asks start() whether the board is locked and
// which cell a hint would reveal — and no mark or hint sends a request
// (ADR-0038/R2).
//   pointer   pointerdown on a cell, then pointerup without having been over
//             another cell = a click: clickStroke with the tool selected at
//             pointerdown and a `repeat` flag (solver_state.js clickedState:
//             a first click gives the cell the brush's state, a repeat click
//             moves it one step along the brush's sequence — see there).
//             A click is a repeat when the previous input was a recorded
//             click on the same cell with the same tool: wireMarking keeps
//             that one click as `lastClick` ({row, col, tool} or null). It
//             is UI state only — not on the board, not in the history, never
//             undone, redone or saved (SAVE; a load starts with it null).
//             Every commit clears it (a drag, even one that changes nothing,
//             undo, redo — button or key — a hint, a confirmed reset,
//             setBoard), and so does picking a brush from the menu (mouse or
//             key, the current brush too), pressing Reset when that opens the
//             confirmation (so a reset opened and then cancelled ends the
//             run too) and pointercancel; the click path sets it after its
//             own commit. Pressing Region does NOT clear it (Region is not a
//             brush pick — see "region" below).
//             Having been over another cell = a drag: dragStroke with the
//             tool selected at pointerdown, previewed on every move, recorded
//             on pointerup; pointercancel drops it. A mouse drag (main
//             button) always marks. A touch or pen drag marks only while
//             Region is on (`gesture.paints` below) — the board's cells set
//             touch-action accordingly (.player-board.is-region, admin.css),
//             and Region turns itself off once such a drag is recorded, even
//             one that changes no cell (CARD-194 target behaviour #7): a
//             region drag never lands as two tool picks in the undo history,
//             only as the one dragStroke. With Region off, a touch or pen
//             pointerdown does not call setPointerCapture or preventDefault,
//             so the browser is free to pan instead; a tap (no intervening
//             move) still reaches pointerup over its starting cell and is a
//             click, same as today. Whether the pointer left its starting
//             cell is tracked regardless of `paints` (only painting the
//             preview is gated on it): a real touch almost always has the
//             browser cancel the gesture (pointercancel) once it recognises
//             a pan, before pointerup — but a pen does not reliably do that
//             (observed: Chromium lets a pen gesture reach pointerup even
//             after real movement, with no cancel), and nothing here may
//             assume a pointerup it does reach is a tap just because
//             painting never ran. A gesture that moved and never painted
//             marks nothing on release either way.
//   menu      #puzzle-player-tool-trigger (a button, aria-haspopup="menu")
//             opens #puzzle-player-tool-menu (role="menu", initially hidden):
//             FOUR role="menuitemradio" [data-player-tool] items in the
//             owner's order — Black, White, Maybe, Undecided (the four
//             brushes, filled/empty/maybe/unknown). Region was a fifth item
//             until CARD-211 and is now a control of its own (see "region"
//             below), so the menu holds brushes only and exactly one item is
//             aria-checked="true": the chosen brush. The trigger's accessible
//             name is always "Brush: <brush>" and its visible text is
//             "<brush>" — CARD-194's "Region · <brush>" composite text is
//             gone with the menu item. Enter, Space or
//             ArrowDown on the trigger opens the menu with focus on the
//             checked item; inside it ArrowDown/ArrowUp move with wraparound,
//             Home/End jump to the first/last item, Escape closes with no
//             change and returns focus to the trigger, and Tab closes the
//             menu and lets focus continue to the next control (Region, since
//             CARD-211 put it between the trigger and Undo) —
//             picking an item (click, or Enter/Space on a native <button>)
//             closes the menu and returns focus to the trigger the same way.
//             The trigger and the Region toggle are the two direct <button>
//             children of .player-tools (the menu is a sibling <div> between
//             them), so a layout selector scoped to ".player-tools > button"
//             sees both.
//   region    [data-player-region] (#puzzle-player-region, CARD-211): the
//             Region toggle, a plain <button> carrying its state in
//             aria-pressed ("true"/"false") rather than aria-checked — it is
//             a mode, not one option among several, which is what a screen
//             reader should announce. Pressing it arms Region; it disarms
//             again when pressed a second time and, one-shot, the instant a
//             drag is recorded (#7) — the flag's whole transition table is
//             solver_state.js nextRegion, so this file only says which event
//             happened. Picking a brush leaves Region exactly as it was: a
//             DELIBERATE divergence from CARD-194's target behaviour #3,
//             decided by the owner on 2026-10-14 (CARD-211) once Region
//             stopped being a fifth item in the brush menu — see
//             nextRegion's own note in solver_state.js. So the two controls
//             are independent in both directions; arming Region never
//             changes the brush either, and never clears
//             `lastClick` (#4). Every change — including the automatic
//             disarm — is written to #puzzle-player-announce, so a screen
//             reader hears "Region on"/"Region off" without re-reading a
//             label; an unchanged value is never rewritten (the live region
//             would announce it again). The flag is UI state like
//             `lastClick` and `zoom`: never a cell state, never recorded,
//             never saved, so every load starts with Region off. While it is
//             armed the board carries .is-region, which is how admin.css
//             drops .player-cell's touch-action to none; the toggle is the
//             only thing that sets that class.
//   history   [data-player-action] undo / redo / reset; aria-disabled="true"
//             while there is nothing to do — pressing one then leaves the
//             board as it is, because undo/redo with an empty stack and a
//             reset of a blank board return the history unchanged.
//             Ctrl/Cmd+Z undoes, Shift+Ctrl/Cmd+Z redoes.
//   hint      [data-player-action="hint"] (CARD-183) records hintStroke for
//             solver_state.js hintCell (which start() computes from the
//             recorded board and the payload's clues and solution) through
//             the same commit as every stroke. aria-disabled="true", and
//             pressing it does nothing, while hintCell is null, the board is
//             locked, or a gesture is in progress. The hinted cell carries
//             .is-hinted until the next commit; #puzzle-player-announce says
//             which cell it revealed, and says when it came from the
//             solution rather than from one line.
//
// PROGRESS (CARD-162, FR-044 AC-312..AC-321). After every recorded stroke,
// undo, redo, reset and setBoard, start() re-derives both from the current
// (recorded) board and payload.solution with solver_state.js errorCount and
// isSolved — nothing is accumulated, so the count is the live number of
// wrong marks. A drag's preview is not counted until it is recorded.
//   errors    [data-player-errors] in the toolbar (inside a role=status
//             region): errorCount of the current board.
//   progress  [data-player-progress] (CARD-187): solvedPercent of the
//             current board + "%". Deliberately NOT a live region (no role,
//             no aria-live, no live ancestor) and never written to
//             #puzzle-player-announce: it changes on almost every mark, so a
//             screen reader reads it on demand only.
//   hints     [data-player-hints] (its own role=status region): hintCount of
//             the current history — undo lowers it, reset leaves it, setBoard
//             (a new history) sets it to 0.
//   solved    while isSolved(current board) holds: the banner
//             #puzzle-player-solved (the picture's name, server-rendered) is
//             shown in place of the tools (the tools are hidden but keep
//             their box, admin.css .player-slot — the menu trigger and its
//             menu sit inside that hidden box too, so neither is reachable,
//             and the menu is closed if it was open) and its text is put into the live
//             region #puzzle-player-announce (cleared when unsolved), the board carries .is-solved (a
//             short CSS animation on the transition into solved; none under
//             prefers-reduced-motion, admin.css), and the board is LOCKED —
//             pointer input, undo and redo (buttons and keys) change nothing;
//             undo and redo say aria-disabled="true". Of the player's
//             controls only reset acts. The lock is a function of the
//             current board, not a separate flag: whatever makes the board
//             solved (a stroke, an undo, a redo, setBoard) locks it, and
//             whatever makes it unsolved unlocks it — once locked, that is
//             reset, or the setBoard seam, which replaces the board.
//   reset     pressing Reset opens the in-page confirmation
//             #puzzle-player-confirm (role=alertdialog; never window.confirm)
//             and moves focus to its "Keep marks" button. "Clear board"
//             records resetStroke through record — one undoable step, also
//             from the solved state; "Keep marks" or Escape changes nothing.
//             Any of these closes it and returns focus to Reset. So does
//             every recorded stroke, undo or redo (button or key — even one
//             that changes nothing) and setBoard while it is open: the board
//             it asked about is gone, so it closes as "Keep marks" does,
//             after that change is recorded. Undoing a reset
//             made from the solved state brings the solved board back, and
//             with it the lock (see "solved").
//
// DOM / CSS (admin.css, "Puzzle player"): table.player-board inside
// .player-stage; th.player-clue.is-col (one box per column, above) and
// th.player-clue.is-row (one box per row, left), each carrying its 0-based
// line in data-line and holding one span.player-clue-num per number;
// td.player-cell with data-row, data-col and data-state = the cell's state.
// Every fifth line on both axes is heavier: a cell or clue box after one
// carries .major-right / .major-below (never the last line, which is the
// board's frame).
//
// BOTH GUTTERS (CARD-212, owner's doc 2026-10-13). A big board repeats its
// clues on both sides of an axis: row clues left AND right, column clues
// above AND below, so a player scrolled to the far edge still has clues in
// view. "Big" is BIG_SIDE per axis and each axis is decided on its own; the
// repetition is drawn only while the cells it leaves are DOUBLE_MIN_CELL or
// more, and otherwise the board keeps exactly today's rendering, CARD-193's
// mirror included — see layoutLadder and drawSettledLayout in start(), which
// choose the rung by measuring the board they drew (today's rendering first,
// so a board that can afford no duplicate is built once and no more).
// Because that condition is a measurement and not a media query, the board
// is redrawn when the WINDOW changes too, not only when the 820 px
// breakpoint flips. The duplicate gutter carries the same numbers in the
// same order as its twin and is aria-hidden, so a screen reader reads each
// clue once (clueBox); its numbers circle with their twins (clueNumbersOf
// pairs them by data-line). Every board built leaves one
// performance.mark(DRAW_MARK), so what a layout choice cost is countable.
//
// ZOOM (CARD-195, FR-044). A view setting that multiplies the fitted cell
// side (admin.css --player-zoom on table.player-board); it changes no board
// state, is never recorded, never in serializeState/the save, and starts at
// ZOOM_MIN (100%) on every load — wireMarking's local `zoom` variable is
// never read by anything outside this file. 100% to 300%, in ZOOM_STEP
// (25-point) steps on the zoom buttons ([data-player-zoom-action="in"/"out"]
// in .player-zoom) and continuously on a two-finger pinch; the readout
// ([data-player-zoom-readout]) is plain text, not a live region. The pure
// arithmetic (clamping, a button's next step, a pinch's ratio, and the
// anchor-preserving scroll formula) lives in solver_state.js (ADR-0038/R4);
// this file only reads the pointers, the DOM and .player-stage's scroll
// position and calls it.
//   buttons   applyZoom(stepZoom(zoom, "in"|"out"), cx, cy) with (cx, cy) the
//             centre of .player-stage's own visible box (its clientWidth/2,
//             clientHeight/2) as the anchor, so that point's board content
//             stays where it was (target behaviour #5). A press at either
//             end of the range is a no-op (stepZoom itself clamps), so no
//             extra aria-disabled guard is needed.
//   pinch     Two touch or pen pointers down, the first of them started on a
//             board cell, is the board's pinch (pinch rule a): it cancels
//             any single-pointer gesture in progress exactly as rule (b)
//             says (the preview is reverted through player.show of the
//             recorded board, `gesture` and `lastClick` are cleared, and the
//             first pointer's own later pointerup is ignored — tracked by
//             `pinch` itself: once set, every pointerup/pointercancel of
//             either of its two pointers ends it with no commit, whichever
//             of the two the browser releases first), then on every move of
//             either pointer recomputes the zoom from pinchZoom(starting
//             zoom, starting distance, current distance) (rule c) and
//             anchors on the pointers' current midpoint, in the stage's own
//             box — not the page's. Two pointers landing with the first NOT
//             on a board cell (a clue box, or off the board entirely) is
//             rule (d): solver.js does nothing — no preventDefault, no
//             pointer capture — so the browser's own page pinch runs
//             instead, which is why clue boxes keep touch-action: auto
//             (admin.css, unchanged by this card). A third touch/pen pointer
//             while one of the two is already tracked, or while a pinch is
//             already active, is ignored outright. Mouse pointers never
//             reach any of this (rule f — only "touch"/"pen" pointerTypes
//             are tracked in `touchPoints`/`touchStartCell` at all).

import {
  EMPTY, FILLED, MAYBE, UNKNOWN, applyStroke, clickStroke, copyBoard, createBoard, createHistory,
  dragStroke, errorCount, hintCell, hintCount, hintStroke, isBoard, isSolved, record,
  redo, resetStroke, undo,
} from "./solver_state.js";
// The progress percent (CARD-187): see PROGRESS above.
import { solvedPercent } from "./solver_state.js";
// Clue circles (CARD-188): see paintCircles below.
import { circledClues } from "./solver_state.js";
// The save in this browser (CARD-185): see SAVE below.
import { deserializeState, saveKey, serializeState } from "./solver_state.js";
// Zoom (CARD-195): see ZOOM below.
import { ZOOM_MAX, ZOOM_MIN, anchoredScroll, pinchZoom, stepZoom } from "./solver_state.js";
// Region (CARD-194's modifier, its own toggle since CARD-211): see "region"
// above. The flag's transitions and the "does this drag paint?" rule are
// pure (ADR-0038/R4); the button that shows the flag is this file's.
import { gesturePaints, nextRegion } from "./solver_state.js";
// Edit mode (CARD-246): see EDIT MODE above. Both are pure board arithmetic
// (ADR-0038/R4); answerOfBoard is imported by static/puzzle_edit.js, not by
// this file, which never asks a board for its answer.
import { boardOfGrid } from "./solver_state.js";

const MAJOR_EVERY = 5;

// The one value of payload.mode that is not the player (CARD-246).
const EDIT_MODE = "edit";

// "The recorded board changed" — dispatched on `document` in edit mode only
// (see BOARD CHANGE above). Exported, and imported by static/puzzle_edit.js,
// so the two halves of the seam cannot drift to two spellings of one string.
export const BOARD_CHANGE = "puzzle-board-change";

// The save of a page that keeps nothing: edit mode's `save` (see EDIT MODE).
// A read of null is what start()'s restore branch already treats as "no
// saved board", so the flag needs no second test there.
const NO_SAVE = Object.freeze({
  read: () => null,
  write: () => {},
  forget: () => {},
});

// A board is "big" on an axis once that side is past BIG_SIDE. CARD-193 chose
// 15 for the row axis (W > 15 mirrors the row clues on a phone) and had the
// number inline in two places; CARD-212 names it once and reuses the same
// number for the column axis (H > 15 doubles the column clues), so the two
// axes are one rule read twice, not two rules that can drift apart.
const BIG_SIDE = 15;

// CARD-212: a second gutter is drawn only while the cells it leaves are at
// least this many CSS pixels on a side — CARD-182's phone-fit minimum (a
// WCAG 2.2 (2.5.8) 24 px target), the number CARD-193 then dropped as a
// *floor* because a floor forced a sideways scroll. As a *condition* it costs
// nothing: a board that cannot afford the duplicate keeps exactly today's
// rendering (see layoutLadder in start()). It is compared against the cell as
// actually drawn, never against a re-derivation of admin.css's clamp.
const DOUBLE_MIN_CELL = 24;

// The performance.mark drawBoard leaves behind, one per board built.
const DRAW_MARK = "nonogram-player-board-draw";

// How long after the last `resize` event the board is redrawn for the new
// window (CARD-212; see the listener in start()). Long enough that dragging
// a window edge redraws once at the end rather than on every event, short
// enough that letting go feels like it settled immediately.
const RESIZE_SETTLE = 150;

function majorAfter(index, length) {
  return (index + 1) % MAJOR_EVERY === 0 && index + 1 < length;
}

function isSide(n) {
  return Number.isInteger(n) && n >= 1;
}

function isClueSet(lines, count) {
  return Array.isArray(lines) && lines.length === count && lines.every(
    (clue) => Array.isArray(clue) && clue.length >= 1
      && clue.every((n) => Number.isInteger(n) && n >= 0));
}

function isSolution(grid, width, height) {
  return Array.isArray(grid) && grid.length === height && grid.every(
    (row) => Array.isArray(row) && row.length === width
      && row.every((cell) => typeof cell === "boolean"));
}

// The payload, or an Error saying why there is none worth drawing.
function readPayload() {
  const element = document.getElementById("puzzle-player-data");
  if (!element) throw new Error("the page carries no puzzle data");
  let payload;
  try {
    payload = JSON.parse(element.textContent);
  } catch (error) {
    throw new Error(`the puzzle data is not JSON (${error.message})`);
  }
  if (!payload || !isSide(payload.width) || !isSide(payload.height)
      || !isClueSet(payload.rows, payload.height)
      || !isClueSet(payload.columns, payload.width)
      || !isSolution(payload.solution, payload.width, payload.height)) {
    throw new Error("the puzzle data does not describe a width x height board with its clues");
  }
  return payload;
}

// One clue box for line `line` (0-based) of its axis. `data-line` is what
// pairs a duplicate with its twin (clueNumbersOf below), independently of
// where in the table either of them sits.
//   right      the box draws on the right of the grid instead of the left
//              (CARD-193's mirrored gutter, and CARD-212's second row gutter)
//   duplicate  CARD-212's repetition: aria-hidden and unlabelled, so a screen
//              reader still reads each clue exactly once — from the first
//              gutter, which keeps the aria-label
function clueBox(tag, kind, line, label, clue, { right = false, duplicate = false } = {}) {
  const box = document.createElement(tag);
  box.className = `player-clue is-${kind}${right ? " is-right" : ""}`;
  box.scope = kind === "row" ? "row" : "col";
  box.dataset.line = String(line);
  if (duplicate) box.setAttribute("aria-hidden", "true");
  else box.setAttribute("aria-label", `${label}: ${clue.join(" ")}`);
  for (const n of clue) {
    const number = document.createElement("span");
    number.className = "player-clue-num";
    number.textContent = String(n);
    box.append(number);
  }
  return box;
}

// The blank box where a clue gutter crosses another. `right` puts it on the
// right of the column clues, where it carries the heavy rule the row clues'
// own side normally draws (admin.css .player-corner.is-right).
function cornerBox(right) {
  const corner = document.createElement("td");
  corner.className = right ? "player-corner is-right" : "player-corner";
  return corner;
}

// Draw the empty board for `payload` into `stage`; returns the cell elements,
// row-major, in the same order as a board's cells. The `cells` array is
// row-major whatever `layout` says — only the clue boxes around them move.
//
// `layout` is one rung of start()'s layoutLadder:
//   mirrored     CARD-193: the one row-clue gutter draws on the RIGHT (each
//                body row's box after its cells, the head row's corner after
//                the last column clue), for boards wider than BIG_SIDE on
//                phones only. The left gutter is gone, not doubled.
//   rowGutters   1, or 2 for CARD-212's repetition: a second row-clue box
//                after each body row's cells and a second corner after the
//                last column clue. Never 2 together with `mirrored` — two
//                gutters are what the mirror is the fallback for.
//   colGutters   1, or 2: a whole second gutter of column-clue boxes in a
//                <tfoot> under the grid, with its own corner(s). The
//                duplicate carries the same numbers in the same order as its
//                twin (a bottom box reads top to bottom like the top one);
//                it is a repetition, never a mirror of the sequence.
// Each axis is counted into admin.css's cell clamp through
// --player-row-gutters / --player-col-gutters, so a doubled axis is fitted
// with both of its bands rather than one.
// `zoomPercent` (CARD-195, 100..300) sets --player-zoom as the multiplier
// admin.css's cell clamp multiplies by (100 -> 1); every redraw (see redraw()
// in start()) passes the current zoom through, so neither re-mirroring nor
// re-doubling ever resets it.
function drawBoard(stage, payload, layout, zoomPercent) {
  // One performance mark per board built (CARD-212). Building a board is the
  // player's one expensive act — a 30 x 30 is ~900 cells plus its gutters —
  // and the layout ladder in start() can build more than one before it
  // settles, so how many it built is worth being able to count: see
  // DRAW_MARK's own test (tests/test_puzzle_solver_clues.py
  // TestSolverClues_TheLadderStopsAtTheFirstRungThatFits).
  performance.mark(DRAW_MARK);
  const { width, height, rows, columns } = payload;
  const { mirrored, rowGutters, colGutters } = layout;
  const table = document.createElement("table");
  table.className = mirrored ? "player-board is-mirrored" : "player-board";
  table.setAttribute("aria-label", `Puzzle board, ${width} columns by ${height} rows`);
  // The cell side is computed in CSS from these (admin.css, --player-cell).
  table.style.setProperty("--player-cols", width);
  table.style.setProperty("--player-rows", height);
  table.style.setProperty("--player-zoom", String(zoomPercent / 100));
  // The widest row band in ch: each row number takes its digits and a 1.45 ch
  // gap (admin.css .player-clue.is-row), and the row has 0.5 ch of padding.
  table.style.setProperty("--player-row-ch", Math.max(...rows.map((c) => c.reduce((sum, n) => sum + String(n).length + 1.45, 0.5))));
  table.style.setProperty("--player-col-depth", Math.max(...columns.map((c) => c.length)));
  table.style.setProperty("--player-col-digits", Math.max(...columns.flatMap((c) => c.map((n) => String(n).length))));
  table.style.setProperty("--player-row-gutters", rowGutters);
  table.style.setProperty("--player-col-gutters", colGutters);

  // The column-clue gutter: above the grid, or (duplicate) under it.
  const columnGutter = (duplicate) => {
    const line = (duplicate ? table.createTFoot() : table.createTHead()).insertRow();
    if (!mirrored) line.append(cornerBox(false));
    columns.forEach((clue, col) => {
      const box = clueBox("th", "col", col, `Column ${col + 1}`, clue, { duplicate });
      if (majorAfter(col, width)) box.classList.add("major-right");
      line.append(box);
    });
    if (mirrored || rowGutters === 2) line.append(cornerBox(true));
  };
  columnGutter(false);

  const body = table.createTBody();
  const cells = [];
  rows.forEach((clue, row) => {
    const line = body.insertRow();
    const rowClue = (duplicate) => {
      const box = clueBox("th", "row", row, `Row ${row + 1}`, clue,
        { right: duplicate || mirrored, duplicate });
      if (majorAfter(row, height)) box.classList.add("major-below");
      return box;
    };
    if (!mirrored) line.append(rowClue(false));
    for (let col = 0; col < width; col += 1) {
      const cell = line.insertCell();
      cell.className = "player-cell";
      cell.dataset.row = String(row);
      cell.dataset.col = String(col);
      if (majorAfter(col, width)) cell.classList.add("major-right");
      if (majorAfter(row, height)) cell.classList.add("major-below");
      // The solved animation's per-cell delay (a diagonal sweep, admin.css).
      cell.style.setProperty("--player-wave", row + col);
      cells.push(cell);
    }
    // Mirrored, the one labelled gutter moves here; doubled, a duplicate
    // follows the left gutter's labelled boxes.
    if (mirrored) line.append(rowClue(false));
    else if (rowGutters === 2) line.append(rowClue(true));
  });
  if (colGutters === 2) columnGutter(true);

  stage.replaceChildren(table);
  return cells;
}

function paint(cellElements, board) {
  cellElements.forEach((element, index) => {
    element.dataset.state = board.cells[index];
  });
}

function showError(stage, reason) {
  const alert = document.createElement("div");
  alert.className = "alert alert-danger player-error";
  alert.setAttribute("role", "alert");
  alert.textContent = `This puzzle's board cannot be drawn: ${reason}.`;
  stage.replaceChildren(alert);
}

function start() {
  const stage = document.getElementById("puzzle-player");
  let payload;
  try {
    payload = readPayload();
  } catch (error) {
    showError(stage, error.message);
    console.error(`puzzle player: ${error.message}`);
    return;
  }

  // CARD-246's one flag (see EDIT MODE above). Read once, here, so every
  // branch below names the same value.
  const editing = payload.mode === EDIT_MODE;
  const save = editing ? NO_SAVE : browserSave(saveKey(payload.id));
  let history = createHistory(
    editing ? boardOfGrid(payload.solution) : createBoard(payload.width, payload.height));
  const saved = save.read();
  if (saved !== null) {
    const restored = deserializeState(saved, payload);
    if (restored === null) save.forget();
    else history = restored;
  }
  let board = history.board;

  const toolbar = document.getElementById("puzzle-player-controls");
  const errorsOut = toolbar.querySelector("[data-player-errors]");
  const hintsOut = toolbar.querySelector("[data-player-hints]");
  const progressOut = toolbar.querySelector("[data-player-progress]");
  const banner = document.getElementById("puzzle-player-solved");
  const announce = document.getElementById("puzzle-player-announce");

  // Redrawn by redraw() below: the live table, its cells (row-major) and the
  // clue-number spans (CARD-188). `table`/`cellElements`/`clueNumbers` are
  // `let` so every closure that reads them (showProgress, the marking
  // callbacks) sees the current board after a mirror redraw (CARD-193).
  let table, cellElements, clueNumbers;
  let solved = false;
  // The cell the last hint revealed, as {row, col} and not as the element
  // showing it (CARD-212 review cycle 2, G-003): a redraw replaces every
  // element, and a hint is a CELL, not an element, so naming it this way is
  // what lets showHint put the highlight back on the redrawn table.
  let hintedAt = null;

  // Move the .is-hinted highlight to `next` ({row, col}), or take it off
  // (null). The element is looked up through the live cellElements each
  // time, so this is also how the highlight is re-applied after a redraw.
  function showHint(next) {
    const element = (cell) => cellElements[cell.row * payload.width + cell.col];
    if (hintedAt) element(hintedAt)?.classList.remove("is-hinted");
    hintedAt = next;
    if (hintedAt) element(hintedAt)?.classList.add("is-hinted");
  }

  // CARD-193: boards wider than BIG_SIDE columns mirror their row clues to
  // the right, but only on phones (owner decision, 2026-10-06) — the ≤ 820 px
  // shell breakpoint, the same one admin.css keys the phone cell floor to.
  const mirrorQuery = window.matchMedia("(max-width: 820px)");
  function isMirrored() {
    return payload.width > BIG_SIDE && mirrorQuery.matches;
  }

  // CARD-212: the layouts to try for this board, roomiest first. Each axis is
  // eligible for its duplicate on its own (a 30 x 12 board doubles its row
  // clues and not its column clues), and a rung is taken only if the cells it
  // leaves are still DOUBLE_MIN_CELL or more (redraw() below measures the
  // rung it drew). Doubling needs MORE room than the mirror, not less, so
  // when no doubled rung fits, the last rung — exactly today's rendering,
  // mirror included — is drawn whether it fits or not. The row axis is
  // preferred over the column axis when only one of the two can be afforded,
  // because the row gutter is the one the owner reported first and the only
  // one CARD-193 ever mirrored.
  function layoutLadder() {
    const bigRows = payload.width > BIG_SIDE;
    const bigColumns = payload.height > BIG_SIDE;
    const mirrored = isMirrored();
    const ladder = [];
    if (bigRows && bigColumns) ladder.push({ mirrored: false, rowGutters: 2, colGutters: 2 });
    if (bigRows) ladder.push({ mirrored: false, rowGutters: 2, colGutters: 1 });
    if (bigColumns) ladder.push({ mirrored, rowGutters: 1, colGutters: 2 });
    ladder.push({ mirrored, rowGutters: 1, colGutters: 1 });
    return ladder;
  }

  // The side of a cell of the board as just drawn, in unzoomed CSS pixels:
  // --player-zoom multiplies admin.css's fitted cell, so dividing it out
  // again makes this measurement — and with it the rung redraw() settles on —
  // the same at every zoom level (CARD-195), rather than letting zooming in
  // change the board's structure.
  function drawnCell(zoomPercent) {
    return stage.querySelector("td.player-cell").getBoundingClientRect().width / (zoomPercent / 100);
  }

  // Error count, hint count, progress percent and solved state of the recorded history (see
  // PROGRESS); `hint` is the hintCell value just recorded, or null.
  function showProgress(hint) {
    // CARD-246: in edit mode there is no solution to measure against — the
    // board IS the answer being written — so there are no counters, no
    // banner, no lock and no clue circles, and the page carries none of
    // their elements. `solved` therefore stays false and the board never
    // locks, which is what lets the owner keep painting.
    if (editing) return;
    const errors = String(errorCount(history.board, payload.solution));
    // Rewriting the same text would make the live region announce it again.
    if (errorsOut.textContent !== errors) errorsOut.textContent = errors;
    const hints = String(hintCount(history));
    if (hintsOut.textContent !== hints) hintsOut.textContent = hints;
    const percent = `${solvedPercent(history.board, payload.solution)}%`;
    if (progressOut.textContent !== percent) progressOut.textContent = percent;
    const now = isSolved(history.board, payload.solution);
    if (now !== solved) announce.textContent = now ? banner.textContent.trim() : "";
    else if (hint) announce.textContent = hintText(hint);
    solved = now;
    banner.hidden = !solved;
    toolbar.classList.toggle("is-solved", solved);
    table.classList.toggle("is-solved", solved);
    paintCircles(clueNumbers, circledClues(history.board, payload.rows, payload.columns));
  }

  // (Re)draws the board for the current viewport from the recorded history —
  // called once at load and again, from the same recorded board, whenever
  // mirrorQuery crosses 820 px (CARD-193: nothing recorded is lost — history,
  // undo/redo and the save are untouched by a redraw).
  // `marking` (below) always exists by the time this runs (the first call
  // is textually after `const marking = wireMarking(...)`) — CARD-195's
  // zoom (marking.getZoom()) survives a redraw the same way.
  // CARD-212: the gutter layout is chosen by measuring, not by predicting —
  // a rung is drawn and the cell it produced is measured. Only the rung that
  // settles is wired to the marking code; the discarded ones are replaced
  // within this same task, so no frame is ever produced from one.
  //
  // Today's rendering is drawn FIRST, and when it is already under the bar
  // nothing else is drawn at all. Doubling only ever takes room from the
  // cells — in admin.css's min() each extra gutter adds a subtrahend to both
  // width terms and a band to the height term — so a plain board below
  // DOUBLE_MIN_CELL cannot be rescued by a rung above it. That is the
  // commonest case by far — at 1280 x 720 it is every board from about 24
  // columns up — and it costs one draw where it used to cost four
  // (measured at review cycle 1 on a 30 x 30 there: ~125 ms to an
  // interactive board on one draw, ~810 ms on four). A board that CAN
  // afford a duplicate pays for the rungs it tries, and if none of them
  // fits, the plain board already drawn is put back rather than built
  // again. The counts are pinned by draw marks, not by timings:
  // tests/test_puzzle_solver_clues.py
  // TestSolverClues_TheLadderStopsAtTheFirstRungThatFits.
  function drawSettledLayout(zoom) {
    const ladder = layoutLadder();
    const plain = ladder[ladder.length - 1];
    const plainCells = drawBoard(stage, payload, plain, zoom);
    if (ladder.length === 1 || drawnCell(zoom) < DOUBLE_MIN_CELL) return plainCells;
    const plainTable = stage.firstElementChild;
    for (let rung = 0; rung < ladder.length - 1; rung += 1) {
      const cells = drawBoard(stage, payload, ladder[rung], zoom);
      if (drawnCell(zoom) >= DOUBLE_MIN_CELL) return cells;
    }
    stage.replaceChildren(plainTable);
    return plainCells;
  }

  function redraw() {
    const zoom = marking.getZoom();
    cellElements = drawSettledLayout(zoom);
    table = stage.querySelector(".player-board");
    clueNumbers = clueNumbersOf(table);
    paint(cellElements, board);
    // The highlighted ELEMENT is gone with the old table; the hinted CELL is
    // not, so it is put back on the new one (CARD-212 review cycle 2,
    // G-003). Before this card a redraw meant crossing 820 px; it now also
    // means any window resize — a phone fires one when its URL bar
    // collapses, mid-solve — and "Hints: N" survives a redraw, so the
    // highlight the reader paid for has to survive it too.
    showHint(hintedAt);
    showProgress(null);
    marking.refresh();
  }

  // Pointer, tool, history and keyboard input is wired once, to `stage`
  // (which survives a redraw) rather than to the table a redraw replaces —
  // see wireMarking.
  const marking = wireMarking(stage, {
    getHistory: () => history,
    locked: () => solved,
    // CARD-246: a hint reveals the solution, and in edit mode the solution
    // is what the owner is rewriting — "revealing" it would push the board
    // back to the stored grid. The editor's page ships no Hint button and
    // this answers null for the guards that ask anyway.
    nextHint: () => (editing ? null : hintCell(history.board, payload.rows, payload.columns, payload.solution)),
    show(next) {
      board = next;
      paint(cellElements, board);
    },
    commit(next, hint) {
      history = next;
      board = history.board;
      paint(cellElements, board);
      showHint(hint ? { row: hint.row, col: hint.col } : null);
      showProgress(hint);
      save.write(serializeState(history, payload));
      // CARD-246 (see BOARD CHANGE above): the one announcement of a
      // recorded change, for the one consumer that needs it. Off in the
      // player, which has nobody listening and must stay byte-identical.
      if (editing) {
        document.dispatchEvent(new CustomEvent(BOARD_CHANGE, { bubbles: true }));
      }
    },
    forget: () => save.forget(),
  });
  redraw();
  // CARD-193: the mirror follows the viewport, not a redraw of its own
  // accord. CARD-212: the gutter layout follows it too — the room for a
  // duplicate is a property of the viewport — so a board big on EITHER side
  // redraws here, not only a mirrorable one; a board big on neither, which
  // can have no mirror and no duplicate, never redraws at all.
  const isBig = payload.width > BIG_SIDE || payload.height > BIG_SIDE;
  mirrorQuery.addEventListener("change", () => {
    if (isBig) redraw();
  });
  // CARD-212: and the window itself, not only the breakpoint. CARD-193's
  // mirror could never go stale, because its condition IS the media query
  // above — cross 820 px and it is re-evaluated, and it is false everywhere
  // else. This card's condition is a continuous one (does the board still
  // measure DOUBLE_MIN_CELL with the duplicate?), so behind that discrete
  // trigger alone a board loaded wide stayed doubled while the window
  // shrank: measured, a 30 x 25 loaded at 1920 x 1500 and dragged to
  // 900 x 800 kept its duplicates at 14.39 px cells — 9.6 px under its own
  // bar — with 376 px of sideways scroll inside the stage that the same
  // board reloaded at that size does not have.
  // Trailing debounce rather than a redraw per event: a drag fires `resize`
  // continuously, and a redraw of a 30 x 30 is tens of milliseconds of
  // layout even now that the ladder early-outs. RESIZE_SETTLE after the LAST
  // event the board is redrawn once — a burst of eight events costs at most
  // two draws, not eight (tests/test_puzzle_solver_zoom.py
  // ..._a_burst_of_resize_events_redraws_once) — from the recorded history,
  // exactly as a breakpoint crossing redraws it: marks, zoom, undo/redo, the
  // save, and since G-003 the hinted cell's highlight all survive.
  let resizeSettling = 0;
  window.addEventListener("resize", () => {
    if (!isBig) return;
    clearTimeout(resizeSettling);
    resizeSettling = setTimeout(redraw, RESIZE_SETTLE);
  });

  window.puzzlePlayer = Object.freeze({
    payload,
    getBoard: () => board,
    setBoard(next) {
      if (!isBoard(next)) {
        throw new RangeError("setBoard needs a board from solver_state.js (see isBoard: frozen, width*height known cell states, no holes)");
      }
      if (next.width !== payload.width || next.height !== payload.height) {
        throw new RangeError(
          `a ${next.width}x${next.height} board does not fit this ${payload.width}x${payload.height} puzzle`);
      }
      // Recorded like any other change (paint, progress, controls, and the
      // reset confirmation closed), as a fresh history.
      marking.commit(createHistory(copyBoard(next)));
    },
  });
}

// SAVE (CARD-185; FR-044 AC-360..AC-365, CON-021). This browser keeps one
// localStorage entry per puzzle, under solver_state.js saveKey(payload.id),
// holding serializeState of the recorded history; nothing is sent anywhere.
// At load, before the first showProgress, an entry that deserializeState
// trusts becomes the starting history (board, counts, undo and redo, and a
// solved board's banner and lock); one it does not trust is removed and the
// board starts blank. Every commit (stroke, hint, undo, redo, setBoard)
// writes the entry, a drag's preview does not, and a confirmed reset removes
// it (its in-page undo writes it again). A history serializeState cannot
// save (setBoard's non-blank start) removes it too. Each access to storage,
// window.localStorage itself included, is caught and silent: without
// storage the player works as before, and a failed write removes the entry
// so a reload never shows an older board than the one on screen.
function browserSave(key) {
  function forget() {
    try {
      window.localStorage.removeItem(key);
    } catch {
      // no storage: nothing to remove
    }
  }
  return {
    forget,
    read() {
      try {
        return window.localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    write(text) {
      if (text === null) {
        forget();
        return;
      }
      try {
        window.localStorage.setItem(key, text);
      } catch {
        forget();
      }
    },
  };
}

// CLUE CIRCLES (CARD-188). showProgress, run on every commit (stroke, undo,
// redo, reset, setBoard) and never for a drag's preview, sets
// .is-circled on each span.player-clue-num that solver_state.js circledClues
// circles for the recorded board, and clears it on the rest. The spans are
// collected once, here, at draw time: { rows: [...] per row, columns: [...]
// per column }, and each line holds one entry per clue NUMBER — the one or
// two spans that show it, one per gutter (CARD-212), paired by their box's
// data-line rather than by DOM order. So a duplicate is circled with its
// twin, by construction: paintCircles cannot reach one and miss the other.
// Each span is also given its digit count as --player-clue-digits. Text and
// aria-labels are left alone.
function clueNumbersOf(table) {
  const axis = (kind) => {
    const lines = [];
    for (const box of table.querySelectorAll(`th.player-clue.is-${kind}`)) {
      const line = Number(box.dataset.line);
      (lines[line] ??= []).push([...box.querySelectorAll(".player-clue-num")]);
    }
    return lines.map((gutters) => gutters[0].map((_, k) => gutters.map((spans) => spans[k])));
  };
  const numbers = { rows: axis("row"), columns: axis("col") };
  // The ring's pill width comes from the digit count (admin.css, --player-ring).
  for (const span of [...numbers.rows, ...numbers.columns].flat(2)) {
    span.style.setProperty("--player-clue-digits", span.textContent.length);
  }
  return numbers;
}

function paintCircles(clueNumbers, circled) {
  for (const axis of ["rows", "columns"]) {
    clueNumbers[axis].forEach((numbers, line) => {
      numbers.forEach((twins, k) => {
        for (const span of twins) span.classList.toggle("is-circled", circled[axis][line][k]);
      });
    });
  }
}

// What the live region says about a hint (1-based row and column).
function hintText({ row, col, state, deduced }) {
  const cell = `row ${row + 1}, column ${col + 1} is ${state === FILLED ? "black" : "white"}`;
  return deduced ? `Hint: ${cell}.`
    : `Hint: no cell follows from a single line yet; ${cell} (from the solution).`;
}

// The [row, col] of the board cell under the viewport point (x, y), or null.
// `container` only needs to contain the live table — see wireMarking.
function cellUnder(container, x, y) {
  const cell = document.elementFromPoint(x, y)?.closest("td.player-cell");
  if (!cell || !container.contains(cell)) return null;
  return [Number(cell.dataset.row), Number(cell.dataset.col)];
}

function isAt(position, [row, col]) {
  return position[0] === row && position[1] === col;
}

// Attach pointer, tool, history and keyboard input to `container` (the
// player's stage, not the table itself — CARD-193: a mirror redraw replaces
// the table, and a listener bound to the table it replaced would stop
// receiving events; `container` survives a redraw, and the cell under a
// point is always read fresh from the live DOM, so these listeners need
// wiring only once, even though the table they act on can change). `player`
// gives the current history (getHistory), says whether the board is locked
// (locked — solved, see PROGRESS), gives the cell a hint would reveal
// (nextHint — a hintCell value or null), paints a board without recording it
// (show — a drag's preview) and records a new history (commit, with the hint
// it recorded, if any), and removes this puzzle's save (forget — after a
// confirmed reset, see SAVE). Returns { refresh,
// commit, getZoom }: refresh re-syncs the controls after the lock changed
// elsewhere; commit records a history from elsewhere (setBoard) exactly as
// an input does; getZoom (CARD-195) is the current zoom percent, read by
// redraw() in start() so a mirror redraw keeps it.
//: The brush each menu item paints, keyed by its data-player-tool (see
//: "menu" above). Region is deliberately absent — it is never a brush, has
//: no cell state, and since CARD-211 is not a menu item at all.
const BRUSH_LABEL = { [FILLED]: "Black", [EMPTY]: "White", [MAYBE]: "Maybe", [UNKNOWN]: "Undecided" };

//: What #puzzle-player-announce says about the Region toggle (CARD-211
//: AC-6). The "on" line names what Region will do, because that is the
//: state a screen-reader user cannot see; "off" needs no explanation.
const REGION_ANNOUNCEMENT = {
  true: "Region on: the next drag marks with the brush.",
  false: "Region off.",
};

function wireMarking(container, player) {
  const controls = document.getElementById("puzzle-player-controls");
  const trigger = document.getElementById("puzzle-player-tool-trigger");
  const triggerSwatch = trigger.querySelector(".player-swatch");
  const triggerText = trigger.querySelector("[data-player-trigger-text]");
  const menu = document.getElementById("puzzle-player-tool-menu");
  const items = [...menu.querySelectorAll("[data-player-tool]")];
  // The Region toggle (CARD-211, see "region" above) and the live region its
  // state is announced through (the same one the solved banner and a hint
  // use — start()'s showProgress writes it too, and whichever wrote last
  // wins, which is why only a genuine change is ever written).
  const regionToggle = document.getElementById("puzzle-player-region");
  const announce = document.getElementById("puzzle-player-announce");
  const actions = Object.fromEntries(
    [...controls.querySelectorAll("[data-player-action]")].map((b) => [b.dataset.playerAction, b]));
  // The reset confirmation (see PROGRESS "reset").
  const confirm = document.getElementById("puzzle-player-confirm");
  const keep = confirm.querySelector('[data-player-confirm="cancel"]');
  let tool = FILLED;
  let region = false; // armed? (see "region" above) — never a cell state, never saved
  let gesture = null; // { pointerId, start, path, dragging, tool, paints }
  let lastClick = null; // the last recorded click, { row, col, tool } (see MARKING)

  // Zoom (CARD-195, see ZOOM above). `zoom` is a percent, 100..300, view
  // state only — never saved, never reset by anything but a fresh load.
  const zoomOut = controls.querySelector('[data-player-zoom-action="out"]');
  const zoomIn = controls.querySelector('[data-player-zoom-action="in"]');
  const zoomReadout = controls.querySelector("[data-player-zoom-readout]");
  let zoom = ZOOM_MIN;
  // Every active touch/pen pointer's current position ({x, y}, in viewport
  // coordinates) and the board cell it started on (a [row, col] from
  // cellUnder, or null when it started on a clue box or off the board) —
  // kept regardless of `gesture`/Region, purely to recognise and drive a
  // pinch (pinch rule a/d). Never touched for a mouse pointer (rule f).
  const touchPoints = new Map();
  const touchStartCell = new Map();
  // { firstId, secondId, startZoom, startDistance } of the active pinch, or
  // null. Set only by beginPinch; cleared the instant either pointer lifts
  // or cancels (pinch rule b: a pinch that ends with one finger still down
  // marks nothing — covered by `gesture` staying null throughout a pinch,
  // so that finger's own later pointerup falls through to the ordinary
  // "nothing to commit" path once pinch is cleared).
  let pinch = null;

  function distanceBetween(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  // The readout and the buttons' aria-disabled, from the current `zoom`.
  function syncZoom() {
    zoomReadout.textContent = `${Math.round(zoom)}%`;
    zoomOut.setAttribute("aria-disabled", String(zoom <= ZOOM_MIN));
    zoomIn.setAttribute("aria-disabled", String(zoom >= ZOOM_MAX));
  }

  // Moves to `nextPercent` (clamped by the caller's own arithmetic —
  // stepZoom or pinchZoom, never this function), keeping `(anchorX,
  // anchorY)` — a point's offset inside .player-stage's own visible box,
  // not the page's — over the same board point (target behaviour #5,
  // solver_state.js anchoredScroll). A no-op `nextPercent` (already at the
  // clamped end of the range) touches neither the table nor the scroll
  // position, only re-syncs the readout/buttons (idempotent either way).
  function applyZoom(nextPercent, anchorX, anchorY) {
    const old = zoom;
    zoom = nextPercent;
    if (zoom !== old) {
      const table = container.querySelector(".player-board");
      if (table) table.style.setProperty("--player-zoom", String(zoom / 100));
      container.scrollLeft = anchoredScroll(container.scrollLeft, anchorX, old, zoom);
      container.scrollTop = anchoredScroll(container.scrollTop, anchorY, old, zoom);
    }
    syncZoom();
  }

  // Pinch rule (a)/(b): `firstId` started on a board cell, `secondId` just
  // landed — ends whatever single-pointer gesture was in progress (its
  // preview is reverted, never committed) and starts tracking the pinch
  // from the two pointers' current positions.
  function beginPinch(firstId, secondId) {
    if (gesture) {
      player.show(player.getHistory().board); // revert the preview, commit nothing
      gesture = null;
    }
    lastClick = null;
    pinch = {
      firstId,
      secondId,
      startZoom: zoom,
      // Math.max(…, 1): pinchZoom (solver_state.js) refuses a non-positive
      // starting distance; two fingers reported at the exact same point
      // (not a real pinch, but not impossible from synthetic input) must
      // not throw here instead of simply not zooming yet.
      startDistance: Math.max(distanceBetween(touchPoints.get(firstId), touchPoints.get(secondId)), 1),
    };
    refresh();
  }

  // Pinch rule (c): the current zoom from the two pointers' current
  // positions, anchored on their midpoint (in the stage's own box).
  function pinchMove() {
    const p1 = touchPoints.get(pinch.firstId);
    const p2 = touchPoints.get(pinch.secondId);
    const stageBox = container.getBoundingClientRect();
    const midX = (p1.x + p2.x) / 2 - stageBox.left;
    const midY = (p1.y + p2.y) / 2 - stageBox.top;
    applyZoom(pinchZoom(pinch.startZoom, pinch.startDistance, distanceBetween(p1, p2)), midX, midY);
  }

  // The trigger's name/text and which menu item is checked, from `tool`
  // alone (see "menu" above): since CARD-211 the menu holds brushes only, so
  // Region no longer shows up in either the label or the checked item.
  function syncTrigger() {
    const label = BRUSH_LABEL[tool];
    trigger.setAttribute("aria-label", `Brush: ${label}`);
    triggerSwatch.dataset.state = tool;
    triggerText.textContent = label;
    for (const item of items) {
      item.setAttribute("aria-checked", String(item.dataset.playerTool === tool));
    }
  }

  // Move Region to `armed` (CARD-211, see "region" above): the toggle's
  // aria-pressed, the board's .is-region class (through refresh(), which is
  // also what re-applies it after a mirror redraw) and one live-region line.
  // A no-op call writes nothing — rewriting the same announcement would make
  // it read out again. Every caller goes through solver_state.js nextRegion,
  // so this function never decides the transition itself.
  function setRegion(armed) {
    if (armed === region) return;
    region = armed;
    regionToggle.setAttribute("aria-pressed", String(region));
    announce.textContent = REGION_ANNOUNCEMENT[String(region)];
    refresh();
  }

  function closeMenu() {
    if (menu.hidden) return;
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
  }

  function openMenu() {
    menu.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    (items.find((item) => item.getAttribute("aria-checked") === "true") ?? items[0]).focus();
  }

  // A menu pick (mouse click, or Enter/Space on a focused item — items are
  // native <button>s, so those keys already fire "click"). Every item is a
  // brush since CARD-211, and picking one restarts the click sequence but
  // leaves Region alone: CARD-194's target behaviour #3 (a brush pick
  // disarms Region) was reversed by the owner on 2026-10-14, so there is no
  // setRegion call here and no "brush" event in nextRegion's table — see
  // nextRegion's divergence note in solver_state.js.
  function pick(name) {
    tool = name;
    lastClick = null;
    syncTrigger();
    closeMenu();
    trigger.focus();
    refresh();
  }

  function refresh() {
    const { board: current, done, undone } = player.getHistory();
    const locked = player.locked();
    if (locked) closeMenu(); // the tools' box is hidden while solved (admin.css)
    // Read fresh from the live DOM (not a `table` reference start() keeps):
    // a mirror redraw (CARD-193) replaces the table outright, and refresh()
    // runs again right after one (redraw() calls marking.refresh()), which
    // is what re-applies Region's touch-action class to the new table.
    container.querySelector(".player-board")?.classList.toggle("is-region", region);
    actions.undo.setAttribute("aria-disabled", String(locked || done.length === 0));
    actions.redo.setAttribute("aria-disabled", String(locked || undone.length === 0));
    actions.reset.setAttribute("aria-disabled", String(current.cells.every((s) => s === UNKNOWN)));
    // Optional since CARD-246: the editor's page has no Hint button (see
    // EDIT MODE). `?.` rather than a mode flag of its own — this function
    // reads the DOM it was given and nothing about why.
    actions.hint?.setAttribute("aria-disabled", String(locked || gesture !== null || player.nextHint() === null));
  }

  function commit(next, hint = null) {
    lastClick = null; // anything recorded ends a run of repeat clicks
    player.commit(next, hint);
    if (!confirm.hidden) closeConfirm(); // see PROGRESS "reset"
    refresh();
  }

  container.addEventListener("pointerdown", (event) => {
    // Pinch bookkeeping (CARD-195) runs ahead of — and independently of —
    // the single-pointer gesture logic below, for touch/pen pointers only
    // (rule f): the very first check it would otherwise hit, `if (gesture)
    // return`, would swallow a second finger's pointerdown entirely.
    if (event.pointerType === "touch" || event.pointerType === "pen") {
      if (pinch) return; // a third pointer while a pinch is active: ignored
      const cell = cellUnder(container, event.clientX, event.clientY);
      if (touchPoints.size === 1) {
        // The second touch/pen pointer: pinch rule (a) when the first one
        // started on a board cell, rule (d) — leave it to the browser —
        // otherwise. Either way this pointer never starts its own gesture.
        const [firstId] = touchPoints.keys();
        touchPoints.set(event.pointerId, { x: event.clientX, y: event.clientY });
        touchStartCell.set(event.pointerId, cell);
        if (touchStartCell.get(firstId) !== null) {
          event.preventDefault();
          beginPinch(firstId, event.pointerId);
        }
        return;
      }
      touchPoints.set(event.pointerId, { x: event.clientX, y: event.clientY });
      touchStartCell.set(event.pointerId, cell);
    }
    if (gesture || player.locked() || (event.pointerType === "mouse" && event.button !== 0)) return;
    const start = cellUnder(container, event.clientX, event.clientY);
    if (!start) return;
    // A mouse drag always marks (G-1); a touch or pen drag marks only while
    // Region is on (CARD-194 target behaviour #8/#10, the rule itself in
    // solver_state.js gesturePaints) — captured here, at pointerdown, like
    // the tool itself, so toggling Region mid-gesture (not reachable today —
    // the toggle and the board are different elements) would not
    // retroactively change an in-progress gesture either.
    const paints = gesturePaints(event.pointerType, region);
    if (paints) {
      event.preventDefault();
      container.setPointerCapture(event.pointerId);
    }
    // The tool is taken here, at pointerdown: picking another brush mid-drag
    // applies to the next drag, not this one.
    gesture = { pointerId: event.pointerId, start, path: [], dragging: false, tool, paints };
    refresh(); // Hint is disabled while a gesture is in progress
  });

  container.addEventListener("pointermove", (event) => {
    if (touchPoints.has(event.pointerId)) touchPoints.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pinch && (event.pointerId === pinch.firstId || event.pointerId === pinch.secondId)) {
      event.preventDefault();
      pinchMove();
      return;
    }
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    const position = cellUnder(container, event.clientX, event.clientY);
    const previous = gesture.path.at(-1) ?? gesture.start;
    if (!position || isAt(position, previous)) return;
    // `dragging` is tracked even for a non-painting gesture (touch or pen
    // with Region off): a real device's own pan recognition drops almost
    // every such gesture via pointercancel before it gets this far (see
    // pointercancel below), but that is the browser's call, not a guarantee
    // — nothing here may assume it always fires. Painting the preview is
    // still gated on `paints`.
    gesture.path.push(position);
    gesture.dragging = gesture.dragging || !isAt(position, gesture.start);
    if (gesture.dragging && gesture.paints) {
      player.show(applyStroke(player.getHistory().board, dragStroke(gesture.start, gesture.path, gesture.tool)));
    }
  });

  container.addEventListener("pointerup", (event) => {
    if (touchPoints.has(event.pointerId)) {
      touchPoints.delete(event.pointerId);
      touchStartCell.delete(event.pointerId);
      // Pinch rule (b): the first pointer's later pointerup is ignored, and
      // a pinch that ends with one finger still down marks nothing —
      // either pointer lifting ends the pinch outright, with no commit; the
      // *other* finger, if still down, falls through below with `gesture`
      // still null (beginPinch cleared it), so its own eventual pointerup
      // is the ordinary "nothing to commit" no-op.
      if (pinch && (event.pointerId === pinch.firstId || event.pointerId === pinch.secondId)) {
        pinch = null;
        refresh();
        return;
      }
    }
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    const done = gesture;
    gesture = null;
    const history = player.getHistory();
    if (done.dragging) {
      if (!done.paints) {
        // A touch or pen gesture that left its starting cell but reached
        // pointerup without ever being cancelled (the browser chose not to
        // pan — e.g. nothing on the page can scroll): still not a tap, so
        // still not a click (CARD-194 target behaviour #8/#10 — "a touch
        // tap is still a click", which this is not). No mark either way.
        refresh();
        return;
      }
      // Region turns off the instant a drag is recorded — "a drag ended",
      // not "a cell changed" (CARD-194 target behaviour #7). The toggle's
      // aria-pressed flips back with it, and the disarm is announced, so a
      // screen-reader user is not left believing Region is still armed.
      // Announced BEFORE the commit on purpose: a drag that solves the board
      // lets showProgress overwrite this line with the solved banner, which
      // is the more important of the two.
      setRegion(nextRegion(region, "drag"));
      commit(record(history, dragStroke(done.start, done.path, done.tool)));
      return;
    }
    const [row, col] = done.start;
    const repeat = lastClick !== null && lastClick.row === row && lastClick.col === col
      && lastClick.tool === done.tool;
    commit(record(history, clickStroke(history.board, row, col, done.tool, repeat)));
    lastClick = { row, col, tool: done.tool };
  });

  container.addEventListener("pointercancel", (event) => {
    if (touchPoints.has(event.pointerId)) {
      touchPoints.delete(event.pointerId);
      touchStartCell.delete(event.pointerId);
      if (pinch && (event.pointerId === pinch.firstId || event.pointerId === pinch.secondId)) {
        pinch = null;
        refresh();
        return;
      }
    }
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    gesture = null;
    lastClick = null;
    player.show(player.getHistory().board);
    refresh();
  });

  zoomOut.addEventListener("click", () => {
    applyZoom(stepZoom(zoom, "out"), container.clientWidth / 2, container.clientHeight / 2);
  });
  zoomIn.addEventListener("click", () => {
    applyZoom(stepZoom(zoom, "in"), container.clientWidth / 2, container.clientHeight / 2);
  });

  trigger.addEventListener("click", () => {
    if (menu.hidden) openMenu();
    else closeMenu();
  });
  trigger.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowDown" || !menu.hidden) return;
    event.preventDefault();
    openMenu();
  });
  menu.addEventListener("keydown", (event) => {
    const at = items.indexOf(document.activeElement);
    if (at === -1) return;
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        items[(at + 1) % items.length].focus();
        break;
      case "ArrowUp":
        event.preventDefault();
        items[(at - 1 + items.length) % items.length].focus();
        break;
      case "Home":
        event.preventDefault();
        items[0].focus();
        break;
      case "End":
        event.preventDefault();
        items[items.length - 1].focus();
        break;
      case "Escape":
        event.preventDefault();
        closeMenu();
        trigger.focus();
        break;
      case "Tab":
        // Not prevented: the item closeMenu() hides is the current focus,
        // so the browser's own Tab handling lands on the next focusable
        // control after it in the (now updated) DOM — Region (then Undo),
        // since CARD-211 put the toggle between the trigger and the history
        // buttons.
        closeMenu();
        break;
      default:
        break;
    }
  });
  for (const item of items) {
    item.addEventListener("click", () => pick(item.dataset.playerTool));
  }

  // The Region toggle (CARD-211, see "region" above). A native <button>, so
  // Enter and Space already arrive as "click" — no keydown handler of its
  // own, and no focus move: pressing it leaves focus on it, the way a toggle
  // should. It never touches `tool` or `lastClick`.
  regionToggle.addEventListener("click", () => setRegion(nextRegion(region, "toggle")));

  // Undo and redo change nothing while the board is locked (solved).
  const step = {
    undo: () => (player.locked() ? player.getHistory() : undo(player.getHistory())),
    redo: () => (player.locked() ? player.getHistory() : redo(player.getHistory())),
  };
  for (const name of ["undo", "redo"]) {
    actions[name].addEventListener("click", () => {
      if (!gesture) commit(step[name]());
    });
  }

  // A hint is one recorded stroke (see MARKING "hint").
  actions.hint?.addEventListener("click", () => {
    if (gesture || player.locked()) return;
    const hint = player.nextHint();
    if (hint === null) return;
    commit(record(player.getHistory(), hintStroke(hint.row, hint.col, hint.state)), hint);
  });

  // Reset asks first, in the page (see PROGRESS "reset").
  function closeConfirm() {
    confirm.hidden = true;
    actions.reset.setAttribute("aria-expanded", "false");
    actions.reset.focus();
  }
  actions.reset.addEventListener("click", () => {
    if (gesture || actions.reset.getAttribute("aria-disabled") === "true") return;
    lastClick = null; // opening the confirmation is an input (see MARKING)
    confirm.hidden = false;
    actions.reset.setAttribute("aria-expanded", "true");
    keep.focus();
  });
  // commit closes the confirmation (and returns focus to Reset).
  confirm.querySelector('[data-player-confirm="accept"]').addEventListener("click", () => {
    commit(record(player.getHistory(), resetStroke(player.getHistory().board)));
    player.forget(); // a confirmed reset clears the save (see SAVE)
  });
  keep.addEventListener("click", closeConfirm);
  confirm.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    closeConfirm();
  });

  // The Z key: event.key "z"/"Z", or — when the layout gives that key a
  // non-Latin character (e.g. Russian "я") — event.code "KeyZ". A layout that
  // puts another Latin letter on the KeyZ position (German "y") is matched by
  // its letter, so Ctrl+Y there does not undo.
  function isZ(event) {
    const key = event.key.toLowerCase();
    return key === "z" || (!/^[a-z]$/.test(key) && event.code === "KeyZ");
  }

  document.addEventListener("keydown", (event) => {
    if (gesture || !(event.ctrlKey || event.metaKey) || event.altKey || !isZ(event)) return;
    event.preventDefault();
    commit(event.shiftKey ? step.redo() : step.undo());
  });

  syncTrigger();
  refresh();
  syncZoom();
  controls.hidden = false;
  document.getElementById("puzzle-player-hint").hidden = false;
  return { refresh, commit, getZoom: () => zoom };
}

start();
