// Puzzle player — board state (TERM-037, FR-044, ADR-0038/R4).
//
// The pure half of the player: no DOM, no globals, no I/O. Everything here is
// a function of its arguments, so CARD-161 (strokes, undo/redo) and CARD-162
// (error count, solved state) extend and test it without a page — from the
// browser test suite with `await import('/static/solver_state.js')`.
// Rendering lives in solver.js and only ever reads a board.
//
// A board is a frozen value:
//   { width: int >= 1, height: int >= 1,
//     cells: frozen array of width*height cell states, row-major
//            (the cell at row r, column c is cells[r * width + c]) }
// A cell state is one of UNKNOWN ("undecided"), FILLED or EMPTY ("marked
// empty"). Boards are never mutated: withCell returns a new one, so a history
// of boards (CARD-161's undo) is just an array of values. Boards are trusted
// in-page values: only this page's own code builds and passes them (CARD-160
// takes no input; CARD-161 routes clicks through withCell/setBoard). isBoard
// (below) says what a board is; solver.js setBoard asks it, then keeps and
// paints its own copy (copyBoard), never the value it was handed.

export const UNKNOWN = "unknown";
export const FILLED = "filled";
export const EMPTY = "empty";
export const CELL_STATES = Object.freeze([UNKNOWN, FILLED, EMPTY]);

function isSide(n) {
  return Number.isInteger(n) && n >= 1;
}

function indexOf(board, row, col) {
  if (!Number.isInteger(row) || !Number.isInteger(col)
      || row < 0 || row >= board.height || col < 0 || col >= board.width) {
    throw new RangeError(`cell (${row}, ${col}) is outside a ${board.width}x${board.height} board`);
  }
  return row * board.width + col;
}

// A width x height board with every cell undecided — how every puzzle starts.
export function createBoard(width, height) {
  if (!isSide(width) || !isSide(height)) {
    throw new RangeError(`a board needs positive integer sides, not ${width}x${height}`);
  }
  return Object.freeze({
    width,
    height,
    cells: Object.freeze(new Array(width * height).fill(UNKNOWN)),
  });
}

// The value of `object`'s own data property `key`, or undefined when `key`
// is absent, inherited, a hole, or an accessor (getter) — so a getter or a
// prototype can never stand in for a board's width, height, cells or cell.
function ownData(object, key) {
  return Object.getOwnPropertyDescriptor(object, key)?.value;
}

// Whether `value` is a board. What it checks:
//   1. `value` is a non-null object (typeof "object") and Object.isFrozen;
//   2. its own DATA properties `width` and `height` are integers >= 1
//      (typeof number, Number.isInteger: 0, negatives, 2.5, NaN, Infinity
//      and "20" are not sides);
//   3. its own data property `cells` is a genuine Array (Array.isArray — an
//      array-like {length, 0: ...} is not one), itself Object.isFrozen, whose
//      length is exactly width * height (so a cells array of the right length
//      on sides that do not multiply to it is refused, and the sides are
//      bounded by the maximum array length);
//   4. EVERY index 0..length-1 of `cells` is an own data element holding one
//      of CELL_STATES — checked index by index, because Array.prototype.every
//      skips holes; a hole, an accessor element or any other value
//      ("Filled", null, undefined, 1) is refused.
// Frozen with own data properties, a board never changes afterwards — what
// lets CARD-161 keep a history of boards and CARD-162 count errors over one.
// Nothing else is checked: other own properties of the board or of `cells`
// are not looked at, and copyBoard / withCell do not carry them over.
// createBoard, copyBoard and withCell only ever return values for which this
// is true.
export function isBoard(value) {
  if (value === null || typeof value !== "object" || !Object.isFrozen(value)) {
    return false;
  }
  const width = ownData(value, "width");
  const height = ownData(value, "height");
  const cells = ownData(value, "cells");
  if (!isSide(width) || !isSide(height) || !Array.isArray(cells)
      || !Object.isFrozen(cells) || cells.length !== width * height) {
    return false;
  }
  for (let index = 0; index < cells.length; index += 1) {
    if (!CELL_STATES.includes(ownData(cells, index))) {
      return false;
    }
  }
  return true;
}

// A fresh frozen board equal to `board`: width, height and every cell copied
// index by index through own-data reads into a new frozen Array. For a value
// isBoard accepted (it does not re-check); solver.js setBoard keeps this copy.
export function copyBoard(board) {
  const cells = ownData(board, "cells");
  return Object.freeze({
    width: ownData(board, "width"),
    height: ownData(board, "height"),
    cells: Object.freeze(Array.from({ length: cells.length }, (_, index) => ownData(cells, index))),
  });
}

export function cellAt(board, row, col) {
  return board.cells[indexOf(board, row, col)];
}

// The board with one cell set to `state`; `board` itself is left untouched.
// The new cells Array is built index by index (not board.cells.slice(), which
// would consult the cells array's constructor), so given a board it returns
// a board.
export function withCell(board, row, col, state) {
  if (!CELL_STATES.includes(state)) {
    throw new RangeError(`"${state}" is not a cell state (${CELL_STATES.join(", ")})`);
  }
  const target = indexOf(board, row, col);
  const cells = Array.from({ length: board.cells.length },
    (_, index) => (index === target ? state : board.cells[index]));
  return Object.freeze({ width: board.width, height: board.height, cells: Object.freeze(cells) });
}

// ---------------------------------------------------------------------------
// Strokes and history (CARD-161, FR-044 AC-303..AC-311, EC-035)
//
// A stroke is what one click or one drag does, as a frozen value
//   { cells: frozen array of frozen [row, col] pairs, state: a cell state }
// meaning "set every one of these cells to `state`". A stroke carries the
// state it sets, not the gesture that made it, so applying it again gives the
// same board: a click's stroke already holds the cycled state.
//
// A history is a frozen value
//   { board:  the current board,
//     done:   frozen array of frozen { stroke, before } — the undo stack,
//             oldest first; `before` is the board the stroke was applied to,
//     undone: frozen array of strokes — the redo stack, next to redo last }
// Undo goes back to the saved `before` board; it does not replay. EC-035 (the
// browser property test) checks that replaying done's strokes from the first
// board gives `board`, after every stroke, undo and redo of a random corpus.

// A click's next state: undecided -> filled -> marked empty -> undecided.
const CYCLE = Object.freeze({ [UNKNOWN]: FILLED, [FILLED]: EMPTY, [EMPTY]: UNKNOWN });

export function cycled(state) {
  if (!CELL_STATES.includes(state)) {
    throw new RangeError(`"${state}" is not a cell state (${CELL_STATES.join(", ")})`);
  }
  return CYCLE[state];
}

function makeStroke(cells, state) {
  return Object.freeze({ cells: Object.freeze(cells.map((cell) => Object.freeze([...cell]))), state });
}

// The stroke of one click on (row, col): that cell, cycled from its state on
// `board` (whatever tool is selected — the tool governs drags only).
export function clickStroke(board, row, col) {
  return makeStroke([[row, col]], cycled(cellAt(board, row, col)));
}

// The cells a drag covers, in the order first reached. `start` is the
// [row, col] the pointer went down on; `path` is every [row, col] the pointer
// was over afterwards, in order (repeats allowed). The drag keeps to the row
// or the column through `start`, decided by the first path cell that is not
// `start`: the row when it is at least as far from `start` in columns as in
// rows, the column otherwise. A path cell off that line adds nothing. Each
// path cell on the line adds every cell between it and the previous on-line
// position (`start` at first), so a pointer that moves fast enough to skip
// cells still covers the cells it passed. A path of only `start` covers
// `start` alone.
export function dragLine(start, path) {
  const [startRow, startCol] = start;
  const cells = [[startRow, startCol]];
  const seen = new Set([`${startRow},${startCol}`]);
  let alongRow = null;
  let last = null;
  for (const [row, col] of path) {
    if (alongRow === null) {
      if (row === startRow && col === startCol) continue;
      alongRow = Math.abs(col - startCol) >= Math.abs(row - startRow);
      last = alongRow ? startCol : startRow;
    }
    if (alongRow ? row !== startRow : col !== startCol) continue;
    const reached = alongRow ? col : row;
    const step = reached >= last ? 1 : -1;
    for (let k = last; k !== reached + step; k += step) {
      const cell = alongRow ? [startRow, k] : [k, startCol];
      const key = `${cell[0]},${cell[1]}`;
      if (!seen.has(key)) {
        seen.add(key);
        cells.push(cell);
      }
    }
    last = reached;
  }
  return cells;
}

// The stroke of one drag with `tool` (a cell state): dragLine's cells.
export function dragStroke(start, path, tool) {
  if (!CELL_STATES.includes(tool)) {
    throw new RangeError(`"${tool}" is not a tool (${CELL_STATES.join(", ")})`);
  }
  return makeStroke(dragLine(start, path), tool);
}

// The stroke that returns every cell of `board` to undecided.
export function resetStroke(board) {
  const cells = [];
  for (let row = 0; row < board.height; row += 1) {
    for (let col = 0; col < board.width; col += 1) cells.push([row, col]);
  }
  return makeStroke(cells, UNKNOWN);
}

// `board` with every cell of `stroke` set to its state; `board` is left
// untouched. A cell outside the board, or a state that is not a cell state,
// is refused with RangeError.
export function applyStroke(board, stroke) {
  if (!CELL_STATES.includes(stroke.state)) {
    throw new RangeError(`"${stroke.state}" is not a cell state (${CELL_STATES.join(", ")})`);
  }
  const cells = Array.from(board.cells);
  for (const [row, col] of stroke.cells) cells[indexOf(board, row, col)] = stroke.state;
  return Object.freeze({ width: board.width, height: board.height, cells: Object.freeze(cells) });
}

// `strokes` applied in order, starting from `board`.
export function replay(board, strokes) {
  return strokes.reduce(applyStroke, board);
}

function sameCells(a, b) {
  return a.cells.every((state, index) => state === b.cells[index]);
}

function historyOf(board, done, undone) {
  return Object.freeze({ board, done: Object.freeze(done), undone: Object.freeze(undone) });
}

// A history at `board` with nothing to undo or redo.
export function createHistory(board) {
  return historyOf(board, [], []);
}

// `history` after `stroke`: the stroke is applied to the current board,
// pushed onto the undo stack, and the redo stack is dropped. A stroke that
// changes no cell is not a step: `history` itself is returned, redo stack
// and all.
export function record(history, stroke) {
  const board = applyStroke(history.board, stroke);
  if (sameCells(board, history.board)) return history;
  const entry = Object.freeze({ stroke, before: history.board });
  return historyOf(board, [...history.done, entry], []);
}

// `history` with its last stroke undone (the board it was applied to comes
// back and the stroke moves onto the redo stack); `history` itself when there
// is nothing to undo.
export function undo(history) {
  if (history.done.length === 0) return history;
  const entry = history.done[history.done.length - 1];
  return historyOf(entry.before, history.done.slice(0, -1), [...history.undone, entry.stroke]);
}

// `history` with the last undone stroke applied again and back on the undo
// stack; `history` itself when there is nothing to redo.
export function redo(history) {
  if (history.undone.length === 0) return history;
  const stroke = history.undone[history.undone.length - 1];
  const entry = Object.freeze({ stroke, before: history.board });
  return historyOf(applyStroke(history.board, stroke), [...history.done, entry],
    history.undone.slice(0, -1));
}
