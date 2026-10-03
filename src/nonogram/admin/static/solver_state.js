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
