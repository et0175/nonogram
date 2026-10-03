// Puzzle player — renderer (TERM-037, FR-044, CARD-160; ADR-0038).
//
// Not the uniqueness solver (COMP-005, src/nonogram/solver/): this draws the
// page a person solves a stored puzzle on. Plain JavaScript, no framework, no
// build step (ADR-0038/R1). Board state lives in the pure module
// solver_state.js (ADR-0038/R4); this file is the only one that touches the
// DOM, and it only ever *reads* a board to paint it.
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
//                      is stored and painted
// Boards are trusted in-page values (see solver_state.js).
// CARD-160 has no input handling: setBoard is the one way the board changes,
// and CARD-161's click/drag/undo will go through it.
//
// DOM / CSS (admin.css, "Puzzle player"): table.player-board inside
// .player-stage; th.player-clue.is-col (one box per column, above) and
// th.player-clue.is-row (one box per row, left), each holding one
// span.player-clue-num per number; td.player-cell with data-row, data-col and
// data-state = the cell's state. Every fifth line on both axes is heavier:
// a cell or clue box after one carries .major-right / .major-below (never the
// last line, which is the board's frame).

import { copyBoard, createBoard, isBoard } from "./solver_state.js";

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
  table.style.setProperty("--player-row-depth", Math.max(...rows.map((c) => c.length)));
  table.style.setProperty("--player-col-depth", Math.max(...columns.map((c) => c.length)));

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
  let board = createBoard(payload.width, payload.height);
  paint(cellElements, board);

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
      board = copyBoard(next);
      paint(cellElements, board);
    },
  });
}

start();
