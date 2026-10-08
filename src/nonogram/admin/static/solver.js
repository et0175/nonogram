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
//   }
// "rows"/"columns" are compute_clues(stored grid) — the one encoder, never
// re-derived here (ADR-0038/R3). A line with no filled cell is [0] and is shown
// as the single number "0". A payload that is absent or not of this shape is
// refused: an alert replaces the board and window.puzzlePlayer stays unset.
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
// follows the brush, CARD-189; one brush dropdown with a Region option,
// CARD-194). The
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
//             own commit. Picking Region does NOT clear it (Region is not a
//             brush pick — see "menu" below).
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
//             five role="menuitemradio" [data-player-tool] items in the
//             owner's order — Black, White, Maybe, Undecided (the four
//             brushes, filled/empty/maybe/unknown) then Region. Exactly one
//             item is aria-checked="true": a brush when Region is off, or
//             Region itself when it is on (picking a brush always turns
//             Region off; picking Region keeps whichever brush was active —
//             CARD-194 target behaviour #3/#4). The trigger's accessible
//             name is always "Brush: <brush>"; its visible text is "<brush>",
//             or "Region · <brush>" while Region is on. Enter, Space or
//             ArrowDown on the trigger opens the menu with focus on the
//             checked item; inside it ArrowDown/ArrowUp move with wraparound,
//             Home/End jump to the first/last item, Escape closes with no
//             change and returns focus to the trigger, and Tab closes the
//             menu and lets focus continue to the next control (Undo) —
//             picking an item (click, or Enter/Space on a native <button>)
//             closes the menu and returns focus to the trigger the same way.
//             The trigger is the only direct <button> child of .player-tools
//             (the menu is a sibling <div>), so a layout selector scoped to
//             ".player-tools > button" still sees one control.
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
// th.player-clue.is-row (one box per row, left), each holding one
// span.player-clue-num per number; td.player-cell with data-row, data-col and
// data-state = the cell's state. Every fifth line on both axes is heavier:
// a cell or clue box after one carries .major-right / .major-below (never the
// last line, which is the board's frame).
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

const MAJOR_EVERY = 5;

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

function clueBox(tag, kind, label, clue) {
  const box = document.createElement(tag);
  box.className = `player-clue is-${kind}`;
  box.scope = kind === "row" ? "row" : "col";
  box.setAttribute("aria-label", `${label}: ${clue.join(" ")}`);
  for (const n of clue) {
    const number = document.createElement("span");
    number.className = "player-clue-num";
    number.textContent = String(n);
    box.append(number);
  }
  return box;
}

// Draw the empty board for `payload` into `stage`; returns the cell elements,
// row-major, in the same order as a board's cells. `mirrored` (CARD-193:
// boards wider than 15 columns, on phones only — see isMirrored in start())
// moves each body row's row-clue box after its cells and the head row's
// corner after the last column clue, so the row-clue gutter draws on the
// right (admin.css .player-board.is-mirrored); the `cells` array stays
// row-major regardless — only DOM placement within each row changes.
// `zoomPercent` (CARD-195, 100..300) sets --player-zoom as the multiplier
// admin.css's cell clamp multiplies by (100 -> 1); a mirror redraw (the only
// other caller of drawBoard, see redraw() in start()) passes the current
// zoom through too, so re-mirroring never resets it.
function drawBoard(stage, payload, mirrored, zoomPercent) {
  const { width, height, rows, columns } = payload;
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

  const head = table.createTHead().insertRow();
  const corner = document.createElement("td");
  corner.className = "player-corner";
  if (!mirrored) head.append(corner);
  columns.forEach((clue, col) => {
    const box = clueBox("th", "col", `Column ${col + 1}`, clue);
    if (majorAfter(col, width)) box.classList.add("major-right");
    head.append(box);
  });
  if (mirrored) head.append(corner);

  const body = table.createTBody();
  const cells = [];
  rows.forEach((clue, row) => {
    const line = body.insertRow();
    const box = clueBox("th", "row", `Row ${row + 1}`, clue);
    if (majorAfter(row, height)) box.classList.add("major-below");
    if (!mirrored) line.append(box);
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
    if (mirrored) line.append(box);
  });

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

  const save = browserSave(saveKey(payload.id));
  let history = createHistory(createBoard(payload.width, payload.height));
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
  let hinted = null; // the cell element carrying .is-hinted

  // CARD-193: boards wider than 15 columns mirror their row clues to the
  // right, but only on phones (owner decision, 2026-10-06) — the ≤ 820 px
  // shell breakpoint, the same one admin.css keys the phone cell floor to.
  const mirrorQuery = window.matchMedia("(max-width: 820px)");
  function isMirrored() {
    return payload.width > 15 && mirrorQuery.matches;
  }

  // Error count, hint count, progress percent and solved state of the recorded history (see
  // PROGRESS); `hint` is the hintCell value just recorded, or null.
  function showProgress(hint) {
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

  // (Re)draws the board for the current mirror state from the recorded
  // history — called once at load and again, from the same recorded board,
  // whenever mirrorQuery crosses 820 px (CARD-193: nothing recorded is
  // lost — history, undo/redo and the save are untouched by a redraw).
  // `marking` (below) always exists by the time this runs (the first call
  // is textually after `const marking = wireMarking(...)`) — CARD-195's
  // zoom (marking.getZoom()) survives a mirror redraw the same way.
  function redraw() {
    cellElements = drawBoard(stage, payload, isMirrored(), marking.getZoom());
    table = stage.querySelector(".player-board");
    clueNumbers = clueNumbersOf(table);
    paint(cellElements, board);
    hinted = null; // the old highlighted element no longer exists
    showProgress(null);
    marking.refresh();
  }

  // Pointer, tool, history and keyboard input is wired once, to `stage`
  // (which survives a redraw) rather than to the table a redraw replaces —
  // see wireMarking.
  const marking = wireMarking(stage, {
    getHistory: () => history,
    locked: () => solved,
    nextHint: () => hintCell(history.board, payload.rows, payload.columns, payload.solution),
    show(next) {
      board = next;
      paint(cellElements, board);
    },
    commit(next, hint) {
      history = next;
      board = history.board;
      paint(cellElements, board);
      hinted?.classList.remove("is-hinted");
      hinted = hint ? cellElements[hint.row * payload.width + hint.col] : null;
      hinted?.classList.add("is-hinted");
      showProgress(hint);
      save.write(serializeState(history, payload));
    },
    forget: () => save.forget(),
  });
  redraw();
  // CARD-193: the mirror follows the viewport, not a redraw of its own
  // accord — a board that never mirrors (width <= 15) never redraws here.
  mirrorQuery.addEventListener("change", () => {
    if (payload.width > 15) redraw();
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
// collected once, here, at draw time: { rows: [[span...]] per row,
// columns: [[span...]] per column }, each span also given its digit count
// as --player-clue-digits. Text and aria-labels are left alone.
function clueNumbersOf(table) {
  const spans = (kind) => [...table.querySelectorAll(`th.player-clue.is-${kind}`)]
    .map((box) => [...box.querySelectorAll(".player-clue-num")]);
  const numbers = { rows: spans("row"), columns: spans("col") };
  // The ring's pill width comes from the digit count (admin.css, --player-ring).
  for (const span of [...numbers.rows, ...numbers.columns].flat()) {
    span.style.setProperty("--player-clue-digits", span.textContent.length);
  }
  return numbers;
}

function paintCircles(clueNumbers, circled) {
  for (const axis of ["rows", "columns"]) {
    clueNumbers[axis].forEach((spans, line) => {
      spans.forEach((span, k) => span.classList.toggle("is-circled", circled[axis][line][k]));
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
//: "menu" above) — "region" is deliberately absent: it is never a brush and
//: never reaches solver_state.js.
const BRUSH_LABEL = { [FILLED]: "Black", [EMPTY]: "White", [MAYBE]: "Maybe", [UNKNOWN]: "Undecided" };

function wireMarking(container, player) {
  const controls = document.getElementById("puzzle-player-controls");
  const trigger = document.getElementById("puzzle-player-tool-trigger");
  const triggerSwatch = trigger.querySelector(".player-swatch");
  const triggerText = trigger.querySelector("[data-player-trigger-text]");
  const menu = document.getElementById("puzzle-player-tool-menu");
  const items = [...menu.querySelectorAll("[data-player-tool]")];
  const actions = Object.fromEntries(
    [...controls.querySelectorAll("[data-player-action]")].map((b) => [b.dataset.playerAction, b]));
  // The reset confirmation (see PROGRESS "reset").
  const confirm = document.getElementById("puzzle-player-confirm");
  const keep = confirm.querySelector('[data-player-confirm="cancel"]');
  let tool = FILLED;
  let region = false; // the Region option (see "menu" above) — never a cell state
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

  // The trigger's name/text and which menu item is checked, from `tool` and
  // `region` (see "menu" above).
  function syncTrigger() {
    const label = BRUSH_LABEL[tool];
    trigger.setAttribute("aria-label", `Brush: ${label}`);
    triggerSwatch.dataset.state = tool;
    triggerText.textContent = region ? `Region · ${label}` : label;
    for (const item of items) {
      const checked = region ? item.dataset.playerTool === "region" : item.dataset.playerTool === tool;
      item.setAttribute("aria-checked", String(checked));
    }
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
  // native <button>s, so those keys already fire "click"). Picking a brush
  // turns Region off and restarts the click sequence (CARD-194 target
  // behaviour #3); picking Region keeps the current brush and leaves
  // `lastClick` alone (#4).
  function pick(name) {
    if (name === "region") {
      region = true;
    } else {
      tool = name;
      region = false;
      lastClick = null;
    }
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
    actions.hint.setAttribute("aria-disabled", String(locked || gesture !== null || player.nextHint() === null));
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
    // Region is on (CARD-194 target behaviour #8/#10) — captured here, at
    // pointerdown, like the tool itself, so toggling Region mid-gesture (not
    // reachable today — the menu and the board are different elements)
    // would not retroactively change an in-progress gesture either.
    const paints = event.pointerType === "mouse" || region;
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
      // not "a cell changed" (CARD-194 target behaviour #7).
      if (region) {
        region = false;
        syncTrigger();
      }
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
        // control after it in the (now updated) DOM — Undo.
        closeMenu();
        break;
      default:
        break;
    }
  });
  for (const item of items) {
    item.addEventListener("click", () => pick(item.dataset.playerTool));
  }

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
  actions.hint.addEventListener("click", () => {
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
