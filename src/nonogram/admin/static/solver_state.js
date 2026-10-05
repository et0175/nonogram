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
// A cell state is one of UNKNOWN ("undecided"), FILLED, EMPTY ("marked
// empty") or MAYBE (CARD-186: the player's "?" — an assumption, neither dark
// nor white; never an error, and no board holding one is solved). Boards are never mutated: withCell (the single-cell primitive) and
// applyStroke return a new one. Boards are trusted in-page values: only this
// page's own code builds and passes them. In solver.js a click, a drag or a
// reset becomes a stroke, recorded into a history value with record (which
// applies it with applyStroke); undo and redo move along that history. A
// history is {board, done: [{stroke, before}], undone: [stroke]} — see
// "Strokes and history" below. isBoard (below) says what a board is;
// solver.js setBoard asks it, then keeps and paints its own copy (copyBoard),
// never the value it was handed, and starts a new history at that copy.
// errorCount and isSolved ("Progress against the solution", at the end)
// compare a board with the payload's solution grid; solver.js shows both.

export const UNKNOWN = "unknown";
export const FILLED = "filled";
export const EMPTY = "empty";
export const MAYBE = "maybe";
export const CELL_STATES = Object.freeze([UNKNOWN, FILLED, EMPTY, MAYBE]);

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
// lets a history keep each stroke's `before` board and CARD-162 count errors
// over one.
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

// A click's next state: undecided -> filled -> marked empty -> undecided. A
// "?" (MAYBE) is read as undecided, so it goes to filled (CARD-186).
const CYCLE = Object.freeze({ [UNKNOWN]: FILLED, [FILLED]: EMPTY, [EMPTY]: UNKNOWN, [MAYBE]: FILLED });

export function cycled(state) {
  if (!CELL_STATES.includes(state)) {
    throw new RangeError(`"${state}" is not a cell state (${CELL_STATES.join(", ")})`);
  }
  return CYCLE[state];
}

function makeStroke(cells, state) {
  return Object.freeze({ cells: Object.freeze(cells.map((cell) => Object.freeze([...cell]))), state });
}

// What one click does to a cell in `state` with `tool` selected — the only
// place that decides it (CARD-186; CARD-189 extends it). With the MAYBE tool
// a cell that is not "?" becomes "?" and a "?" becomes undecided. With any
// other tool, or none (undefined), the cell cycles (see CYCLE).
export function clickedState(state, tool) {
  if (tool === MAYBE) {
    if (!CELL_STATES.includes(state)) {
      throw new RangeError(`"${state}" is not a cell state (${CELL_STATES.join(", ")})`);
    }
    return state === MAYBE ? UNKNOWN : MAYBE;
  }
  return cycled(state);
}

// The stroke of one click on (row, col) with `tool` selected: that cell set
// to clickedState of its state on `board`. With `tool` omitted the cell
// cycles, as with Black, White or Undecided.
export function clickStroke(board, row, col, tool) {
  return makeStroke([[row, col]], clickedState(cellAt(board, row, col), tool));
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

// ---------------------------------------------------------------------------
// Progress against the solution (CARD-162, FR-044 AC-312..AC-317, EC-036/037)
//
// `solution` is the payload's grid: `height` rows of `width` booleans, true =
// the cell is filled in the answer. Both functions read only the board's
// current cells, so they are functions of the current board, not of how it
// was reached: an undone or corrected mark stops counting at once. Like
// boards, the solution is a trusted in-page value; its sides are taken to
// match the board's (solver.js checks the payload's shape at load).

// The number of wrong marks: cells marked FILLED whose solution is empty,
// plus cells marked EMPTY whose solution is filled. UNKNOWN and MAYBE ("?")
// never count.
export function errorCount(board, solution) {
  let errors = 0;
  for (let row = 0; row < board.height; row += 1) {
    for (let col = 0; col < board.width; col += 1) {
      const state = board.cells[row * board.width + col];
      const filled = solution[row][col];
      if ((state === FILLED && !filled) || (state === EMPTY && filled)) errors += 1;
    }
  }
  return errors;
}

// Whether the board solves the puzzle: no cell is MAYBE ("?", CARD-186),
// every solution-filled cell is marked FILLED and no solution-empty cell is.
// EMPTY marks are optional, as on paper: a solution-empty cell may be EMPTY
// or UNKNOWN.
export function isSolved(board, solution) {
  if (board.cells.includes(MAYBE)) return false;
  for (let row = 0; row < board.height; row += 1) {
    for (let col = 0; col < board.width; col += 1) {
      if ((board.cells[row * board.width + col] === FILLED) !== solution[row][col]) return false;
    }
  }
  return true;
}

// ---------------------------------------------------------------------------
// Clue circles (CARD-188, owner's solver test doc 2026-10-05 item 4)
//
// Which clue numbers the player's MARKS settle — read from the board alone,
// never from the solution, with the payload's clues (ADR-0038/R3). In a line
// a cell is dark (FILLED), white (EMPTY) or undecided (any other state). A
// closed run is a maximal run of dark cells whose neighbour on each side is a
// white cell or the line's edge. A number is circled by rule A or rule B:
//   A  walk in from each edge: skip white cells; stop at the end or at an
//      undecided cell; at a dark run, stop unless it is closed and its length
//      is the next unassigned clue number from that edge — then circle that
//      number and walk on past the run. The two walks are independent.
//   B  every dark run of the line is closed and their lengths, left to
//      right, are exactly the clue: every number is circled.
// Nothing else circles a number (no matching by length alone). A "0" clue
// ([0]) is circled only when every cell of the line is white. Wrong but
// self-consistent marks can circle a number; the error count, not the
// circle, says whether a mark is right.

// The indices of the clue numbers one walk of rule A circles. `at(step)` is
// the walk's step-th cell from its edge; `numberAt(step)` is the walk's
// step-th clue number from that edge, as an index into the clue.
function walkIn(length, count, at, numberAt, clue) {
  const circled = [];
  let step = 0;
  while (step < length && circled.length < count) {
    if (at(step) === EMPTY) {
      step += 1;
      continue;
    }
    if (at(step) !== FILLED) break;
    let end = step;
    while (end < length && at(end) === FILLED) end += 1;
    if (end < length && at(end) !== EMPTY) break; // the run is not closed
    const number = numberAt(circled.length);
    if (end - step !== clue[number]) break;
    circled.push(number);
    step = end;
  }
  return circled;
}

// One boolean per number of `clue` (an array of ints, [0] for an empty line):
// whether the marks in `cells` (one line of cell states) circle it. Frozen.
export function circledNumbers(clue, cells) {
  const length = cells.length;
  if (clue.length === 1 && clue[0] === 0) {
    return Object.freeze([cells.every((state) => state === EMPTY)]);
  }
  const count = clue.length;
  const circled = new Array(count).fill(false);
  const fromLeft = walkIn(length, count, (step) => cells[step], (k) => k, clue);
  const fromRight = walkIn(length, count, (step) => cells[length - 1 - step], (k) => count - 1 - k, clue);
  for (const number of [...fromLeft, ...fromRight]) circled[number] = true;
  // Rule B: every dark run closed, lengths exactly the clue.
  const runs = [];
  let whole = true;
  for (let start = 0; start < length; start += 1) {
    if (cells[start] !== FILLED) continue;
    let end = start;
    while (end < length && cells[end] === FILLED) end += 1;
    const closedLeft = start === 0 || cells[start - 1] === EMPTY;
    const closedRight = end === length || cells[end] === EMPTY;
    if (!closedLeft || !closedRight) whole = false;
    runs.push(end - start);
    start = end;
  }
  if (whole && runs.length === count && runs.every((run, k) => run === clue[k])) circled.fill(true);
  return Object.freeze(circled);
}

// circledNumbers of every line of `board`: { rows: one array per row, top to
// bottom, columns: one per column, left to right }, all frozen. `rows` and
// `columns` are the payload's clues; the solution is not an argument.
export function circledClues(board, rows, columns) {
  const { width, height, cells } = board;
  const row = (r) => Array.from({ length: width }, (_, c) => cells[r * width + c]);
  const column = (c) => Array.from({ length: height }, (_, r) => cells[r * width + c]);
  return Object.freeze({
    rows: Object.freeze(rows.map((clue, r) => circledNumbers(clue, row(r)))),
    columns: Object.freeze(columns.map((clue, c) => circledNumbers(clue, column(c)))),
  });
}

// ---------------------------------------------------------------------------
// Hints (CARD-183, IDEA-074; FR-044 extension, no AC id yet)
//
// A hint reveals one undecided (UNKNOWN or "?") cell, set to its solution
// state, as one stroke: hintStroke carries `hint: true`, which applyStroke,
// record, undo and redo ignore, so a hint is one undo step and replay still
// holds.
// hintCount reads the undo stack, so undo takes a hint back and redo puts it
// back. The clues are the payload's rows / columns (ADR-0038/R3).

// One line of cell states with every cell that all placements of `clue`
// consistent with `cells` agree on set to FILLED or EMPTY; null when no
// placement fits. `clue` is a payload clue ([0] = no filled cell). The same
// idea as nonogram.solver.propagate.line_intersection, written natively: a
// forward and a backward reachability table over (position, runs placed).
// A run placed at `start` takes its cells and the one cell after it (unless
// it ends the line), which must not be FILLED.
export function lineForced(clue, cells) {
  const runs = clue.filter((n) => n > 0);
  const n = cells.length;
  const k = runs.length;
  const fits = (start, length) => start + length <= n
    && cells.slice(start, start + length).every((s) => s !== EMPTY)
    && (start + length === n || cells[start + length] !== FILLED);
  const after = (start, length) => Math.min(start + length + 1, n);
  const table = () => Array.from({ length: n + 1 }, () => new Array(k + 1).fill(false));
  // back[i][j]: cells i.. can hold runs j.. exactly.
  const back = table();
  back[n][k] = true;
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = k; j >= 0; j -= 1) {
      back[i][j] = (cells[i] !== FILLED && back[i + 1][j])
        || (j < k && fits(i, runs[j]) && back[after(i, runs[j])][j + 1]);
    }
  }
  if (!back[0][0]) return null;
  // front[i][j]: cells ..i-1 can hold runs ..j-1 exactly, the next run free
  // to start at i. Every move from a state on a full path is a placement.
  const front = table();
  front[0][0] = true;
  const canFill = new Array(n).fill(false);
  const canEmpty = new Array(n).fill(false);
  for (let i = 0; i < n; i += 1) {
    for (let j = 0; j <= k; j += 1) {
      if (!front[i][j]) continue;
      if (cells[i] !== FILLED && back[i + 1][j]) {
        front[i + 1][j] = true;
        canEmpty[i] = true;
      }
      if (j < k && fits(i, runs[j]) && back[after(i, runs[j])][j + 1]) {
        const end = i + runs[j];
        front[after(i, runs[j])][j + 1] = true;
        for (let c = i; c < end; c += 1) canFill[c] = true;
        if (end < n) canEmpty[end] = true;
      }
    }
  }
  return cells.map((_, i) => {
    if (canFill[i] && !canEmpty[i]) return FILLED;
    if (canEmpty[i] && !canFill[i]) return EMPTY;
    return UNKNOWN;
  });
}

// Whether a hint may reveal a cell in `state`: UNKNOWN or MAYBE ("?" is read
// as undecided, CARD-186).
function isUndecided(state) {
  return state === UNKNOWN || state === MAYBE;
}

// The cell a hint reveals on `board`, as {row, col, state, deduced}, or null
// when no cell is UNKNOWN or MAYBE. The knowns are the board's correct marks
// (a wrong mark counts as undecided; a "?" is never a known). The first
// UNKNOWN or MAYBE cell, row-major, that lineForced of its row or of its
// column forces from the knowns (one pass, not to a fixed point) is returned
// with deduced: true; when there is none, the first UNKNOWN or MAYBE cell
// with deduced: false. `state` is always the
// solution's. A line lineForced finds no placement for deduces nothing.
export function hintCell(board, rows, columns, solution) {
  const { width, height } = board;
  const truth = (row, col) => (solution[row][col] ? FILLED : EMPTY);
  const known = (row, col) => {
    const state = board.cells[row * width + col];
    return state === truth(row, col) ? state : UNKNOWN;
  };
  const rowForced = rows.map((clue, row) =>
    lineForced(clue, Array.from({ length: width }, (_, col) => known(row, col))));
  const colForced = columns.map((clue, col) =>
    lineForced(clue, Array.from({ length: height }, (_, row) => known(row, col))));
  let fallback = null;
  for (let row = 0; row < height; row += 1) {
    for (let col = 0; col < width; col += 1) {
      if (!isUndecided(board.cells[row * width + col])) continue;
      if ((rowForced[row] !== null && rowForced[row][col] !== UNKNOWN)
          || (colForced[col] !== null && colForced[col][row] !== UNKNOWN)) {
        return { row, col, state: truth(row, col), deduced: true };
      }
      if (fallback === null) fallback = { row, col, state: truth(row, col), deduced: false };
    }
  }
  return fallback;
}

// The stroke of one hint: (row, col) set to `state`, marked hint: true.
export function hintStroke(row, col, state) {
  return Object.freeze({ ...makeStroke([[row, col]], state), hint: true });
}

// The number of hints on the undo stack.
export function hintCount(history) {
  return history.done.filter((entry) => entry.stroke.hint === true).length;
}
