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
// follows the brush, CARD-189). The
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
//             setBoard), and so do pressing any tool button (mouse or key,
//             the pressed one too), pressing Reset when that opens the
//             confirmation (so a reset opened and then cancelled ends the
//             run too) and pointercancel; the click path sets it after its
//             own commit.
//             Having been over another cell = a drag: dragStroke with the
//             tool selected at pointerdown, previewed on every move, recorded
//             on pointerup; pointercancel drops it. Mouse (main button), pen
//             and touch alike; the board's cells set touch-action: none
//             (admin.css).
//   tools     #puzzle-player-controls [data-player-tool] — toggle buttons
//             (filled, empty, unknown, maybe), aria-pressed, exactly one
//             pressed; FILLED at load.
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
//             their box, admin.css .player-slot) and its text is put into the live
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

import {
  FILLED, UNKNOWN, applyStroke, clickStroke, copyBoard, createBoard, createHistory,
  dragStroke, errorCount, hintCell, hintCount, hintStroke, isBoard, isSolved, record,
  redo, resetStroke, undo,
} from "./solver_state.js";
// The progress percent (CARD-187): see PROGRESS above.
import { solvedPercent } from "./solver_state.js";
// Clue circles (CARD-188): see paintCircles below.
import { circledClues } from "./solver_state.js";
// The save in this browser (CARD-185): see SAVE below.
import { deserializeState, saveKey, serializeState } from "./solver_state.js";

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
// row-major, in the same order as a board's cells.
function drawBoard(stage, payload) {
  const { width, height, rows, columns } = payload;
  const table = document.createElement("table");
  table.className = "player-board";
  table.setAttribute("aria-label", `Puzzle board, ${width} columns by ${height} rows`);
  // The cell side is computed in CSS from these (admin.css, --player-cell).
  table.style.setProperty("--player-cols", width);
  table.style.setProperty("--player-rows", height);
  // The widest row band in ch: each row number takes its digits and a 1.45 ch
  // gap (admin.css .player-clue.is-row), and the row has 0.5 ch of padding.
  table.style.setProperty("--player-row-ch", Math.max(...rows.map((c) => c.reduce((sum, n) => sum + String(n).length + 1.45, 0.5))));
  table.style.setProperty("--player-col-depth", Math.max(...columns.map((c) => c.length)));
  table.style.setProperty("--player-col-digits", Math.max(...columns.flatMap((c) => c.map((n) => String(n).length))));

  const head = table.createTHead().insertRow();
  const corner = document.createElement("td");
  corner.className = "player-corner";
  head.append(corner);
  columns.forEach((clue, col) => {
    const box = clueBox("th", "col", `Column ${col + 1}`, clue);
    if (majorAfter(col, width)) box.classList.add("major-right");
    head.append(box);
  });

  const body = table.createTBody();
  const cells = [];
  rows.forEach((clue, row) => {
    const line = body.insertRow();
    const box = clueBox("th", "row", `Row ${row + 1}`, clue);
    if (majorAfter(row, height)) box.classList.add("major-below");
    line.append(box);
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

  const cellElements = drawBoard(stage, payload);
  const save = browserSave(saveKey(payload.id));
  let history = createHistory(createBoard(payload.width, payload.height));
  const saved = save.read();
  if (saved !== null) {
    const restored = deserializeState(saved, payload);
    if (restored === null) save.forget();
    else history = restored;
  }
  let board = history.board;
  paint(cellElements, board);

  const table = stage.querySelector(".player-board");
  const toolbar = document.getElementById("puzzle-player-controls");
  const errorsOut = toolbar.querySelector("[data-player-errors]");
  const hintsOut = toolbar.querySelector("[data-player-hints]");
  const progressOut = toolbar.querySelector("[data-player-progress]");
  const banner = document.getElementById("puzzle-player-solved");
  const announce = document.getElementById("puzzle-player-announce");
  const clueNumbers = clueNumbersOf(table);
  let solved = false;
  let hinted = null; // the cell element carrying .is-hinted

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

  const marking = wireMarking(table, {
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
  showProgress(null);
  marking.refresh();

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
function cellUnder(table, x, y) {
  const cell = document.elementFromPoint(x, y)?.closest("td.player-cell");
  if (!cell || !table.contains(cell)) return null;
  return [Number(cell.dataset.row), Number(cell.dataset.col)];
}

function isAt(position, [row, col]) {
  return position[0] === row && position[1] === col;
}

// Attach pointer, tool, history and keyboard input to `table`. `player` gives
// the current history (getHistory), says whether the board is locked (locked
// — solved, see PROGRESS), gives the cell a hint would reveal (nextHint — a
// hintCell value or null), paints a board without recording it (show — a
// drag's preview) and records a new history (commit, with the hint it
// recorded, if any), and removes this puzzle's save (forget — after a
// confirmed reset, see SAVE). Returns { refresh,
// commit }: refresh re-syncs the controls after the lock changed elsewhere;
// commit records a history from elsewhere (setBoard) exactly as an input does.
function wireMarking(table, player) {
  const controls = document.getElementById("puzzle-player-controls");
  const tools = [...controls.querySelectorAll("[data-player-tool]")];
  const actions = Object.fromEntries(
    [...controls.querySelectorAll("[data-player-action]")].map((b) => [b.dataset.playerAction, b]));
  // The reset confirmation (see PROGRESS "reset").
  const confirm = document.getElementById("puzzle-player-confirm");
  const keep = confirm.querySelector('[data-player-confirm="cancel"]');
  let tool = FILLED;
  let gesture = null; // { pointerId, start, path, dragging, tool }
  let lastClick = null; // the last recorded click, { row, col, tool } (see MARKING)

  function refresh() {
    const { board, done, undone } = player.getHistory();
    for (const button of tools) {
      button.setAttribute("aria-pressed", String(button.dataset.playerTool === tool));
    }
    const locked = player.locked();
    actions.undo.setAttribute("aria-disabled", String(locked || done.length === 0));
    actions.redo.setAttribute("aria-disabled", String(locked || undone.length === 0));
    actions.reset.setAttribute("aria-disabled", String(board.cells.every((s) => s === UNKNOWN)));
    actions.hint.setAttribute("aria-disabled", String(locked || gesture !== null || player.nextHint() === null));
  }

  function commit(next, hint = null) {
    lastClick = null; // anything recorded ends a run of repeat clicks
    player.commit(next, hint);
    if (!confirm.hidden) closeConfirm(); // see PROGRESS "reset"
    refresh();
  }

  table.addEventListener("pointerdown", (event) => {
    if (gesture || player.locked() || (event.pointerType === "mouse" && event.button !== 0)) return;
    const start = cellUnder(table, event.clientX, event.clientY);
    if (!start) return;
    event.preventDefault();
    table.setPointerCapture(event.pointerId);
    // The tool is taken here, at pointerdown: picking another tool mid-drag
    // applies to the next drag, not this one.
    gesture = { pointerId: event.pointerId, start, path: [], dragging: false, tool };
    refresh(); // Hint is disabled while a gesture is in progress
  });

  table.addEventListener("pointermove", (event) => {
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    const position = cellUnder(table, event.clientX, event.clientY);
    const previous = gesture.path.at(-1) ?? gesture.start;
    if (!position || isAt(position, previous)) return;
    gesture.path.push(position);
    gesture.dragging = gesture.dragging || !isAt(position, gesture.start);
    if (gesture.dragging) {
      player.show(applyStroke(player.getHistory().board, dragStroke(gesture.start, gesture.path, gesture.tool)));
    }
  });

  table.addEventListener("pointerup", (event) => {
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    const done = gesture;
    gesture = null;
    const history = player.getHistory();
    if (done.dragging) {
      commit(record(history, dragStroke(done.start, done.path, done.tool)));
      return;
    }
    const [row, col] = done.start;
    const repeat = lastClick !== null && lastClick.row === row && lastClick.col === col
      && lastClick.tool === done.tool;
    commit(record(history, clickStroke(history.board, row, col, done.tool, repeat)));
    lastClick = { row, col, tool: done.tool };
  });

  table.addEventListener("pointercancel", (event) => {
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    gesture = null;
    lastClick = null;
    player.show(player.getHistory().board);
    refresh();
  });

  for (const button of tools) {
    button.addEventListener("click", () => {
      tool = button.dataset.playerTool;
      lastClick = null; // a tool press, even of the pressed tool, restarts the sequence
      refresh();
    });
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

  refresh();
  controls.hidden = false;
  document.getElementById("puzzle-player-hint").hidden = false;
  return { refresh, commit };
}

start();
