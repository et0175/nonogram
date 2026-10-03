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
// of boards (CARD-161's undo) is just an array of values.

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

export function cellAt(board, row, col) {
  return board.cells[indexOf(board, row, col)];
}

// The board with one cell set to `state`; `board` itself is left untouched.
export function withCell(board, row, col, state) {
  if (!CELL_STATES.includes(state)) {
    throw new RangeError(`"${state}" is not a cell state (${CELL_STATES.join(", ")})`);
  }
  const cells = board.cells.slice();
  cells[indexOf(board, row, col)] = state;
  return Object.freeze({ width: board.width, height: board.height, cells: Object.freeze(cells) });
}
