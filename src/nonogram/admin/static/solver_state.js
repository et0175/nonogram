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
// errorCount, isSolved and solvedPercent ("Progress against the solution")
// compare a board with the payload's solution grid; solver.js shows all three.

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
// A board and the ANSWER it holds (CARD-246 — the manual editor)
//
// The editor (templates/puzzle_edit.html, static/puzzle_edit.js) paints the
// same board the player marks on, but the two mean different things by a
// cell. In the player a mark is the solver's guess and "?" is a note to
// self; in the editor a cell is either filled or empty IN THE ANSWER,
// because Puzzle.grid is list[list[bool]] (ADR-0012's boundary type). These
// two functions are that boundary, and they are here rather than in
// solver.js because they are arithmetic over a board and nothing else
// (ADR-0038/R4).
// ---------------------------------------------------------------------------

// The board a stored grid starts the editor on: FILLED where the grid is
// true, EMPTY where it is false — never UNKNOWN, so the board the owner
// opens is already a complete answer and every cell they leave alone stays
// the cell that was stored. `grid` is a height x width array of booleans
// (solver.js readPayload has already checked that much of the payload).
export function boardOfGrid(grid) {
  const height = grid.length;
  const width = height > 0 ? grid[0].length : 0;
  if (!isSide(width) || !isSide(height)) {
    throw new RangeError(`a board needs positive integer sides, not ${width}x${height}`);
  }
  const cells = new Array(width * height);
  for (let row = 0; row < height; row += 1) {
    for (let col = 0; col < width; col += 1) {
      cells[row * width + col] = grid[row][col] ? FILLED : EMPTY;
    }
  }
  return Object.freeze({ width, height, cells: Object.freeze(cells) });
}

// What `board` says the answer is:
//   { grid:      [[bool] * width] * height, or NULL,
//     undecided: frozen [[row, col], ...] of every cell that is neither
//                FILLED nor EMPTY, in row-major order }
//
// `grid` is null whenever `undecided` is non-empty, and that is the whole
// point (CARD-246 AC-6). An answer has no third state, so a board carrying
// UNKNOWN or MAYBE does not describe one — and the cheap thing to do with
// such a cell is to call it `false`, which stores a white cell the owner
// never chose and is the defect AC-6 exists to prevent. Returning no grid at
// all means there is nothing for a caller to coerce: puzzle_edit.js names
// the cells instead of sending anything, and a caller that ignored
// `undecided` would post `null` and be refused by the store's own gate
// rather than quietly storing a different picture.
//
// Hiding the Maybe and Undecided brushes (which puzzle_edit.html does) is
// NOT this guarantee and cannot be: `clickedState`'s third step is "blank"
// for both remaining brushes, and a confirmed Reset blanks every cell, so an
// undecided cell stays reachable in edit mode with two brushes on offer.
export function answerOfBoard(board) {
  const { width, height, cells } = board;
  const grid = [];
  const undecided = [];
  for (let row = 0; row < height; row += 1) {
    const line = [];
    for (let col = 0; col < width; col += 1) {
      const state = cells[row * width + col];
      if (state !== FILLED && state !== EMPTY) undecided.push(Object.freeze([row, col]));
      line.push(state === FILLED);
    }
    grid.push(Object.freeze(line));
  }
  return Object.freeze({
    grid: undecided.length === 0 ? Object.freeze(grid) : null,
    undecided: Object.freeze(undecided),
  });
}

// ---------------------------------------------------------------------------
// Strokes and history (CARD-161, FR-044 AC-303..AC-311, EC-035)
//
// A stroke is what one click or one drag does, as a frozen value
//   { cells: frozen array of frozen [row, col] pairs, state: a cell state }
// meaning "set every one of these cells to `state`". A stroke carries the
// state it sets, not the gesture that made it, so applying it again gives the
// same board: a click's stroke already holds the state the click gave.
//
// A history is a frozen value
//   { board:  the current board,
//     done:   frozen array of frozen { stroke, before } — the undo stack,
//             oldest first; `before` is the board the stroke was applied to,
//     undone: frozen array of strokes — the redo stack, next to redo last }
// Undo goes back to the saved `before` board; it does not replay. EC-035 (the
// browser property test) checks that replaying done's strokes from the first
// board gives `board`, after every stroke, undo and redo of a random corpus.

function makeStroke(cells, state) {
  return Object.freeze({ cells: Object.freeze(cells.map((cell) => Object.freeze([...cell]))), state });
}

// The brushes' click sequences (CARD-189, owner decision 2026-10-05): each
// brush's sequence as "state -> next state". The three colour brushes (Black
// = FILLED, White = EMPTY, Undecided = UNKNOWN) share one order, dark ->
// white -> blank -> dark, and differ only in where they start (their own
// state); Maybe's is "?" -> blank -> "?". A drag never reads these.
const COLOUR_ORDER = Object.freeze({ [FILLED]: EMPTY, [EMPTY]: UNKNOWN, [UNKNOWN]: FILLED });
const MAYBE_ORDER = Object.freeze({ [MAYBE]: UNKNOWN, [UNKNOWN]: MAYBE });

function checkState(state, what) {
  if (!CELL_STATES.includes(state)) {
    throw new RangeError(`"${state}" is not a ${what} (${CELL_STATES.join(", ")})`);
  }
}

// What one click with `tool` (a cell state: the brush) does to a cell in
// `state` — the only place that decides it. `repeat` (true only when it is
// exactly true) says the click repeats the previous input: a click on the
// same cell with the same tool, nothing in between; solver.js keeps that
// memory. A cell outside the brush's sequence takes the brush's state;
// otherwise, on a repeat click or when the cell already holds the brush's
// state, it moves one step along the sequence; otherwise it takes the
// brush's state. So the result always differs from `state`. A `state` or
// `tool` that is not a cell state is refused with RangeError.
export function clickedState(state, tool, repeat) {
  checkState(state, "cell state");
  checkState(tool, "tool");
  const order = tool === MAYBE ? MAYBE_ORDER : COLOUR_ORDER;
  if (!Object.hasOwn(order, state)) return tool;
  if (repeat === true || state === tool) return order[state];
  return tool;
}

// The stroke of one click on (row, col) with `tool`: that cell set to
// clickedState(its state on `board`, tool, repeat). The tool is required: a
// missing tool or one that is not a cell state is refused with RangeError
// (by clickedState), as dragStroke refuses it.
export function clickStroke(board, row, col, tool, repeat) {
  return makeStroke([[row, col]], clickedState(cellAt(board, row, col), tool, repeat));
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

// The progress percent (CARD-187; FR-044 AC-351..AC-354, EC-045): an integer
// 0..100. A cell is correct when it is FILLED on a solution-filled cell or
// EMPTY on a solution-empty one; UNKNOWN, a wrong mark and MAYBE ("?") never
// are. A solved board (isSolved) reads 100, even with undecided whites;
// otherwise floor(100 * correct / all cells) in integer maths. All cells
// correct implies solved, so an unsolved board reads at most 99.
export function solvedPercent(board, solution) {
  if (isSolved(board, solution)) return 100;
  let correct = 0;
  for (let row = 0; row < board.height; row += 1) {
    for (let col = 0; col < board.width; col += 1) {
      const state = board.cells[row * board.width + col];
      if (state === (solution[row][col] ? FILLED : EMPTY)) correct += 1;
    }
  }
  return Math.floor((100 * correct) / (board.width * board.height));
}

// ---------------------------------------------------------------------------
// Clue circles (CARD-188, owner's solver test doc 2026-10-05 item 4)
//
// Which clue numbers the player's MARKS settle — read from the board alone,
// never from the solution, with the payload's clues (ADR-0038/R3). In a line
// a cell is dark (FILLED), white (EMPTY) or undecided (any other state). A
// closed run is a maximal run of dark cells whose neighbour on each side is a
// white cell or the line's edge. A number is circled by rule A, B or C:
//   A  walk in from each edge: skip white cells; stop at the end or at an
//      undecided cell; at a dark run, stop unless it is closed and its length
//      is the next unassigned clue number from that edge — then circle that
//      number and walk on past the run. The two walks are independent.
//   B  every dark run of the line is closed and their lengths, left to
//      right, are exactly the clue: every number is circled.
//   C  (CARD-213, owner's print-layout doc 2026-10-13 item 4) a number whose
//      VALUE occurs exactly once in this line's clue, when the line holds
//      exactly one closed run of that length: no other number can own that
//      run, so it needs no edge anchoring — rule C reaches a number rules A
//      and B cannot. Uniqueness is per line and per value: in "1 2 3 2 1"
//      only the 3 can ever be circled by rule C. Two closed runs of the
//      unique length are contradictory marks, and rule C then circles
//      nothing rather than guessing one of them. Nothing else about the line
//      matters: undecided cells and other runs elsewhere are irrelevant, the
//      run's own two neighbours are what "closed" means.
// Nothing else circles a number (no matching by length alone — rule C matches
// a length only where the clue makes that length decisive). A "0" clue ([0])
// is circled only when every cell of the line is white; rule C does not apply
// to it. Wrong but self-consistent marks can circle a number; the error
// count, not the circle, says whether a mark is right.
//
// Rule C applies NO left-to-right ordering check, and that is deliberate
// rather than an oversight: it circles a number from the length of one closed
// run, so a line clued "1 2" marked "DDWDW....." circles BOTH numbers even
// though the 2-run sits left of the 1-run. Each run's length is still
// decisive given the clue, and such marks fit no placement at all, so a
// solver's brute force never sees them. This is the same family rules A and
// B already produce and at a smaller magnitude — measured over every line of
// length <= 7, marks that fit no placement already drew two or more circles
// in 941 cases before rule C existed, and rule C adds 226. Withholding the
// circle here needs an ordering check across the closed runs, which would
// belong to A and B as much as to C; that is a later card, not this rule.

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
  // Rules B and C read the line's dark runs: `runs` is every run's length,
  // left to right, and `closed` the lengths of the closed ones among them.
  const runs = [];
  const closed = [];
  let whole = true;
  for (let start = 0; start < length; start += 1) {
    if (cells[start] !== FILLED) continue;
    let end = start;
    while (end < length && cells[end] === FILLED) end += 1;
    const closedLeft = start === 0 || cells[start - 1] === EMPTY;
    const closedRight = end === length || cells[end] === EMPTY;
    if (!closedLeft || !closedRight) whole = false;
    else closed.push(end - start);
    runs.push(end - start);
    start = end;
  }
  // Rule B: every dark run closed, lengths exactly the clue.
  if (whole && runs.length === count && runs.every((run, k) => run === clue[k])) circled.fill(true);
  // Rule C: a value unique in the clue, matched by exactly one closed run.
  const times = (list, value) => list.reduce((n, item) => n + (item === value ? 1 : 0), 0);
  for (let number = 0; number < count; number += 1) {
    if (times(clue, clue[number]) === 1 && times(closed, clue[number]) === 1) circled[number] = true;
  }
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
//
// The projection to knowns is knownLine's (hoisted, defined in the ladder
// block below). CARD-269 review F-7: it used to be a five-line copy of it
// here, so hintLine's "the cell is forced on this axis" and this function's
// were PARALLEL-MAINTAINED duplicates, and a drift between them would have
// made rungs 1-2 announce the exhausted sentence on a board that is not
// exhausted. One helper makes "rungs 1-2 cannot drift from the cell rung 3
// reveals" (G-4, AC-328) structural instead of conventional, and gives the
// claim a control: breaking knownLine now breaks the cell hintCell picks,
// which the page-level AC-328 class sees.
export function hintCell(board, rows, columns, solution) {
  const truth = (row, col) => (solution[row][col] ? FILLED : EMPTY);
  const rowForced = rows.map((clue, row) =>
    lineForced(clue, knownLine(board, solution, "row", row)));
  const colForced = columns.map((clue, col) =>
    lineForced(clue, knownLine(board, solution, "column", col)));
  const { width, height } = board;
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

// ---------------------------------------------------------------------------
// The hint ladder (CARD-269, FR-044; supersedes the one-press reveal of
// AC-327, AC-329 and AC-334)
//
// CARD-183's Hint was an answer machine: one press revealed a cell. The
// gentlest useful hint — "look at row 7" — did not exist, so a player who
// needed a nudge paid the full answer; and the row-major fallback reveal
// (AC-329) taught a FALSEHOOD, because "no cell follows from a single line
// yet" arrived together with a revealed cell, and the player concluded they
// had missed a line deduction when in fact none existed.
//
// So one button now answers the same situation three ways, cheapest first:
//   rung 1  where to look   — the line, nothing else (nextRung, hintLine)
//   rung 2  what to see     — the same line plus a CHECKED reason (hintReason)
//   rung 3  the reveal      — exactly CARD-183's hint, unchanged (hintCell)
// and any recorded change — a mark, a drag, undo, redo, a reset, Check, and
// rung 3's own stroke — puts the ladder back on rung 1 (nextRung's "change").
// That reset is what makes one ladder describe ONE situation: the line of
// rungs 1-2 always contains the cell rung 3 reveals.
//
// The rung is player state of Region's kind: the transition rules are here,
// the value lives in solver.js (ADR-0038/R4), and it is never a cell state,
// never a stroke, never in the history and never saved — so every load
// starts on rung 1.
//
// G-4: nothing here changes hintCell, lineForced or hintStroke. The ladder
// WRAPS them: hintLine re-asks lineForced about the cell hintCell already
// picked, and hintReason reads the same CORRECT-marks-only line (knownLine),
// so AC-328's "wrong marks are ignored" holds at every rung by construction.

export const RUNG_POINT = 1;
export const RUNG_EXPLAIN = 2;
export const RUNG_REVEAL = 3;

//: Every rung, in order. The enumerable authority on what a rung can be:
//: solver.js's announce table and the test suite both derive their coverage
//: from this and from HINT_REASONS below, never from a hand-written list.
export const HINT_RUNGS = Object.freeze([RUNG_POINT, RUNG_EXPLAIN, RUNG_REVEAL]);

//: The event names nextRung understands — the two things that can move the
//: ladder, and nothing else can. A press climbs; ANY recorded change (and a
//: Check press, which changes what the player will look at) drops to rung 1.
export const RUNG_EVENTS = Object.freeze(["press", "change"]);

//: Where one press goes from each rung: the next rung in HINT_RUNGS, wrapping
//: at the end. DERIVED from HINT_RUNGS and not written out (ADR-0039/R2): a
//: rung added to the authority above gets a row here for free, where a
//: hand-written table would have left it with none and nextRung would have
//: refused a rung the authority declares.
//:
//: The wrap exists so nextRung is TOTAL, not because production climbs off
//: rung 3. It does not: solver.js's Hint handler branches to commit() while
//: `rung === RUNG_REVEAL` and never reaches nextRung on that press, and the
//: real 3 -> 1 step is commit()'s own nextRung(rung, "change") — rung 3's
//: stroke IS a recorded change, so it drops the ladder like any other.
//: `nextRung(RUNG_REVEAL, "press")` is therefore unreachable from the UI;
//: it is reached only by the derived-table test, which drives all six (rung,
//: event) pairs rather than the five that production can reach.
const RUNG_AFTER_PRESS = Object.freeze(Object.fromEntries(
  HINT_RUNGS.map((rung, i) => [rung, HINT_RUNGS[(i + 1) % HINT_RUNGS.length]])));

// Which rung the ladder stands on after `event`, given it stood on `rung`:
//   "press"   the Hint control was pressed — one rung up, wrapping 3 -> 1.
//   "change"  anything was recorded, or Check was pressed — rung 1.
// An unknown event or an unknown rung is a RangeError, like nextRegion's and
// stepZoom's: a typo must not silently read as "leave it as it was", which
// is the one answer that would let the ladder stick on a rung for ever.
export function nextRung(rung, event) {
  if (!RUNG_EVENTS.includes(event)) {
    throw new RangeError(`"${event}" is not a rung event (${RUNG_EVENTS.join(", ")})`);
  }
  if (event === "change") return RUNG_POINT;
  const next = RUNG_AFTER_PRESS[rung];
  if (next === undefined) {
    throw new RangeError(`${rung} is not a rung (${HINT_RUNGS.join(", ")})`);
  }
  return next;
}

//: The two axes a line can lie on. "column" and not "col": this is the word
//: the live region says out loud.
export const HINT_AXES = Object.freeze(["row", "column"]);

// One line of the board as the player's CORRECT marks alone describe it:
// every cell that agrees with the solution kept, every wrong mark read as
// UNKNOWN, every "?" read as UNKNOWN (it never agrees with FILLED/EMPTY).
// Exactly the knowns hintCell deduces from — hintCell CALLS this, so rungs 1
// and 2 cannot drift from the cell rung 3 reveals (G-4, AC-328) by
// construction rather than by parallel maintenance (CARD-269 review F-7).
export function knownLine(board, solution, axis, index) {
  if (!HINT_AXES.includes(axis)) {
    throw new RangeError(`"${axis}" is not an axis (${HINT_AXES.join(", ")})`);
  }
  const { width, height } = board;
  const known = (row, col) => {
    const state = board.cells[row * width + col];
    return state === (solution[row][col] ? FILLED : EMPTY) ? state : UNKNOWN;
  };
  return axis === "row"
    ? Array.from({ length: width }, (_, col) => known(index, col))
    : Array.from({ length: height }, (_, row) => known(row, index));
}

// The line rungs 1 and 2 point at for the hintCell result `hint`, as a frozen
//   { axis: "row" | "column", index, clue, cells, at }
// where `cells` is that line's knownLine and `at` the forced cell's index
// along it — everything hintReason needs, so the knowns are computed once.
// The axis is the one whose lineForced pass forces that cell, ROW FIRST when
// both do (the card's rule 2) — the same lineForced, over the same knowns
// (knownLine, which hintCell itself projects through), as the pass hintCell
// used to pick the cell, so an axis is claimed only where the deduction
// really is.
//
// THE NULL, WRITTEN OUT (CARD-269 review F-7). Behaviourally rungs 1 and 2
// treat one null one way, and the card's whole promise is that the null they
// meet means "the clues decide nothing more by themselves". Structurally
// there are three ways out of here, and they are NOT the same thing, so they
// are spelled apart below rather than collapsed into one `||`:
//
//   (a) `hint === null` — no undecided cell exists at all, so there is
//       nothing to hint. Unreachable from the UI: the Hint handler returns
//       on a null hint before calling this, and refresh() has already put
//       aria-disabled="true" on the button. Reached only by the pure-module
//       test's `noCell` case.
//   (b) `hint.deduced !== true` — hintCell fell back, so undecided cells
//       remain and no single line decides one. THIS is the exhausted state,
//       the null this card exists for: there is no line to look at, so rungs
//       1 and 2 point at NOTHING and say so, instead of handing over a cell
//       while claiming a line deduction was missed.
//   (c) a deduced cell that NEITHER axis forces — "I could not tell". It
//       would be indistinguishable from (b) to a player, which is the one
//       confusion this card must not ship, so it is not returned as a null
//       at all: it CANNOT OCCUR, and the code says so loudly instead of
//       quietly producing (b)'s sentence.
//
// (c) cannot occur because hintCell sets deduced: true only when
// lineForced(rows[row], knownLine(board, solution, "row", row)) or the
// column's equivalent leaves the cell decided — the same function over the
// same projection as `line` below, since CARD-269's F-7 fix made hintCell
// project through knownLine instead of through a copy of it. The RangeError
// is this module's standing answer to an impossible input (nextRung's, and
// knownLine's own axis check): a typo must not read as a quiet "exhausted".
export function hintLine(board, rows, columns, solution, hint) {
  if (hint === null) return null; // (a)
  if (hint.deduced !== true) return null; // (b) — the exhausted state
  const line = (axis, index, clue, at) => {
    const cells = knownLine(board, solution, axis, index);
    const forced = lineForced(clue, cells);
    if (forced === null || forced[at] === UNKNOWN) return null;
    return Object.freeze({ axis, index, clue, cells: Object.freeze(cells), at });
  };
  const found = line("row", hint.row, rows[hint.row], hint.col)
    ?? line("column", hint.col, columns[hint.col], hint.row);
  if (found === null) { // (c)
    throw new RangeError(
      `no axis forces the deduced cell (${hint.row}, ${hint.col}): `
      + "hintCell and hintLine have drifted");
  }
  return found;
}

//: Every reason rung 2 can give, as the names hintReason returns. The
//: enumerable authority — the one that does the real work in the announce
//: path (HINT_RUNGS keys nothing there; see solver.js's LADDER_SAY for the
//: rung dispatch). solver.js maps each name to one sentence in LADDER_REASON
//: and EXPORTS that map, and TestSolverHintLadder_ThePureModule asserts its
//: keys ARE this set — so a reason added here without a sentence, or a
//: sentence with no reason, is a failure and never a silent pass
//: (ADR-0039/R2). CARD-269 review F-6: LADDER_REASON used to be
//: module-private, which made this sentence a claim no test could perform.
export const HINT_REASONS = Object.freeze(["runs-complete", "overlap", "generic"]);

// The run of `clue` whose OVERLAP covers index `at` in a line of `length`
// cells with nothing known, or null when none does. Run j can start no
// earlier than `start` (every earlier run plus one gap each) and no later
// than `start + slack`, so it certainly covers `start + slack .. start +
// run - 1`; that window is non-empty exactly when the run is longer than the
// slack. Arithmetic over the clue alone — which is why it may only be
// claimed for a line with no known marks (hintReason checks that).
function overlappingRun(clue, length, at) {
  const runs = clue.filter((n) => n > 0);
  if (runs.length === 0) return null;
  const total = runs.reduce((sum, run) => sum + run, 0);
  const slack = length - (total + runs.length - 1);
  if (slack < 0) return null;
  let start = 0;
  for (const run of runs) {
    if (run > slack && at >= start + slack && at < start + run) return run;
    start += run + 1;
  }
  return null;
}

// WHY the cell at index `at` of the line (`clue`, `cells` — a knownLine)
// follows, as a frozen { reason, run }: one of HINT_REASONS, with `run` the
// run length the "overlap" reason names and null otherwise.
//
// This function is the card's centre of gravity, so read the rule twice: a
// named reason is returned ONLY where its own precondition has just been
// verified on this very line, and everything else gets "generic", whose
// sentence ("every placement of this line's clues agrees on at least one
// cell") is true of every forced cell by lineForced's definition. A reason
// that can lie is worse than no reason — it sends the player to look for
// something that is not there, which is the defect this whole card exists to
// remove.
//
//   runs-complete  the correct filled marks already total the clue AND every
//                  cell of the line is either one of those marks or forced
//                  EMPTY. The first half is what does the work; the second is
//                  the sentence's own second clause ("the rest is white")
//                  CHECKED rather than inferred, and it is honest to say it
//                  cannot fail on its own: once a placement exists and the
//                  marks total the clue, every placement fills exactly the
//                  marked cells, so every other cell is forced EMPTY. It
//                  therefore only ever differs where lineForced already
//                  answered null, which the line above has returned on. Kept
//                  because the sentence says it, and a sentence this card
//                  ships must be checked by the code that says it.
//   overlap        the line holds NO known mark at all (so the deduction is
//                  the clue's own arithmetic and nothing the player did) and
//                  `at` is forced FILLED and sits in some run's overlap
//                  window. The run named is the one that actually covers it.
//   generic        everything else, including a line lineForced finds no
//                  placement for and a cell it leaves undecided — the two
//                  cases where no claim about `at` would be safe at all.
export function hintReason(clue, cells, at) {
  const plain = (reason) => Object.freeze({ reason, run: null });
  const forced = lineForced(clue, cells);
  if (forced === null || forced[at] === UNKNOWN) return plain("generic");
  const total = clue.reduce((sum, run) => sum + run, 0);
  const marked = cells.filter((state) => state === FILLED).length;
  if (marked === total && cells.every((state, i) => state === FILLED || forced[i] === EMPTY)) {
    return plain("runs-complete");
  }
  if (cells.every((state) => state !== FILLED && state !== EMPTY) && forced[at] === FILLED) {
    const run = overlappingRun(clue, cells.length, at);
    if (run !== null) return Object.freeze({ reason: "overlap", run });
  }
  return plain("generic");
}

// The row of the first WRONG mark on `board`, row-major, or null when no
// mark is wrong (CARD-269 rule 7 — Check). A wrong mark is a FILLED or EMPTY
// cell the solution disagrees with; UNKNOWN is no mark at all and "?" is an
// assumption, never an error (CARD-186), so neither can ever be wrong.
//
// The ROW and never the cell, deliberately: Check answers "is one of my
// marks wrong?" with the cheapest true answer, leaving the player to find it
// — the same ladder discipline as rung 1. errorCount above says HOW MANY;
// this says WHERE to start looking.
export function firstWrongRow(board, solution) {
  const { width, height } = board;
  for (let row = 0; row < height; row += 1) {
    for (let col = 0; col < width; col += 1) {
      const state = board.cells[row * width + col];
      if (state !== FILLED && state !== EMPTY) continue;
      if (state !== (solution[row][col] ? FILLED : EMPTY)) return row;
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Zoom (CARD-195, FR-044). A view setting only: it changes no board state, is
// never recorded, serialized or saved (see SAVE in solver.js), and solver.js
// resets it to ZOOM_MIN on every page load. The percent (100..300) is the
// unit everywhere here and in solver.js's readout and CSS `--player-zoom`
// (which solver.js divides by 100 before setting it) — there is no separate
// "multiplier" representation.

export const ZOOM_MIN = 100;
export const ZOOM_MAX = 300;
export const ZOOM_STEP = 25;

// `value` folded into [ZOOM_MIN, ZOOM_MAX].
export function clampZoom(value) {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, value));
}

// The zoom one button press moves to: the next multiple of ZOOM_STEP from
// `current` in `direction` ("in" raises, "out" lowers), clamped to
// [ZOOM_MIN, ZOOM_MAX]. `current` need not itself be a multiple of
// ZOOM_STEP (a pinch leaves it at any value in range) — "in" finds the
// smallest multiple strictly above it, "out" the largest multiple strictly
// below it; a tiny (1e-6) tolerance treats a value already practically on a
// multiple as exactly there, so floating-point noise never skips a whole
// step. `direction` other than "in"/"out" is refused with RangeError.
export function stepZoom(current, direction) {
  if (direction !== "in" && direction !== "out") {
    throw new RangeError(`"${direction}" is not a zoom direction ("in" or "out")`);
  }
  const steps = current / ZOOM_STEP;
  const next = direction === "in"
    ? (Math.floor(steps + 1e-6) + 1) * ZOOM_STEP
    : (Math.ceil(steps - 1e-6) - 1) * ZOOM_STEP;
  return clampZoom(next);
}

// Pinch zoom rule (c): `startZoom` scaled by how much farther apart the
// pointers are now than when the pinch began, clamped to range. A
// `startDistance` that is not a positive number is refused with RangeError
// (a pinch's two starting points can never coincide in solver.js, but this
// stays a guarded boundary rather than dividing by zero or a negative).
export function pinchZoom(startZoom, startDistance, currentDistance) {
  if (!(startDistance > 0)) {
    throw new RangeError(`pinchZoom needs a positive starting distance, not ${startDistance}`);
  }
  return clampZoom(startZoom * (currentDistance / startDistance));
}

// The "keep the view" formula (target behaviour #5), one axis at a time:
// `scroll` is .player-stage's current scrollLeft or scrollTop, `anchor` is
// the point that must stay put — its offset from the stage's own visible
// box, not the page — and `oldZoom`/`newZoom` are percents (so the ratio is
// the same whether solver.js passes 100/300 or the equivalent 1/3
// multipliers). Returns the scroll position that keeps `anchor` over the
// same board point after the zoom changes from `oldZoom` to `newZoom`.
export function anchoredScroll(scroll, anchor, oldZoom, newZoom) {
  return (scroll + anchor) * (newZoom / oldZoom) - anchor;
}

// ---------------------------------------------------------------------------
// Region (CARD-194's modifier; its own control since CARD-211, FR-044).
//
// Region is not a brush and never a cell state: it is a one-shot mode saying
// "let the NEXT drag mark, whatever the pointer type". CARD-194 kept both the
// flag and its rules in solver.js, where it was a fifth radio in the brush
// menu; CARD-211 moves the control out of that menu into a toggle button of
// its own, so "is Region armed" is a genuine piece of player state and the
// two rules that read it belong in this pure module (ADR-0038/R4) — the
// button that shows the flag is rendering and stays in solver.js, exactly as
// `zoom` the percent lives there while the zoom arithmetic lives here.
//
// The flag itself is a plain boolean, not a board value: it is never
// recorded, never in the undo history and never saved (serializeState does
// not see it), so every load starts disarmed.

//: The event names nextRegion understands — the two things that can change
//: the flag, and nothing else can. There were three until CARD-211's owner
//: decision dropped "brush" (see the divergence note below).
export const REGION_EVENTS = Object.freeze(["toggle", "drag"]);

// Whether Region is armed after `event`, given it was `armed` before:
//   "toggle"  the Region control was pressed — it flips (the only way to arm
//             it; a press while armed disarms it again).
//   "drag"    a drag was just recorded — Region is one-shot and disarms
//             itself, even for a drag that changed no cell (CARD-194 target
//             behaviour #7). "A drag ended", not "a cell changed".
// DELIBERATE DIVERGENCE from CARD-194, decided by the owner on 2026-10-14
// (CARD-211): picking a brush does NOT disarm Region. CARD-194 shipped that
// disarm as its target behaviour #3, and it had a reason then — Region was a
// fifth role="menuitemradio" in the brush menu, so choosing any other item
// replaced it by the menu's own radio exclusivity. CARD-211 made Region a
// separate toggle, and two independent-looking controls that silently switch
// each other off is the wrong behaviour; so there is no "brush" event any
// more and picking a brush leaves Region exactly as the user left it. The
// two controls are now independent in BOTH directions. This is a decision,
// not drift: anything still saying a brush pick disarms Region is stale.
// Any other `event` is refused with RangeError (like stepZoom's direction):
// a typo must not silently read as "leave it as it was" — and "brush", the
// name CARD-194's rule went by, is deliberately one of the refused names, so
// a caller that still sends it fails loudly instead of disarming.
export function nextRegion(armed, event) {
  if (!REGION_EVENTS.includes(event)) {
    throw new RangeError(`"${event}" is not a Region event (${REGION_EVENTS.join(", ")})`);
  }
  return event === "toggle" ? !armed : false;
}

// Whether a drag by `pointerType` marks the board at all (CARD-194 target
// behaviour #8/#10): a mouse drag always does — the desktop default, and the
// reason Region exists only for the other pointer types — while a touch or
// pen drag marks only while Region is armed, so that with Region off the
// browser is free to pan the page instead. solver.js asks this once, at
// pointerdown, and keeps the answer for the whole gesture.
export function gesturePaints(pointerType, armed) {
  return pointerType === "mouse" || armed === true;
}

// ---------------------------------------------------------------------------
// Probe mode (CARD-268, owner decision 2026-10-22, FR-044)
//
// What a solver does when probing is make a GROUP of marks under one
// hypothesis and then either revert them all (a contradiction was found) or
// keep them all (the hypothesis held). So a probe is a TRANSACTION and never
// a fifth cell state: during one the player marks filled, empty AND "?"
// cells, so "this mark is a hypothesis" is a layer orthogonal to the mark —
// and CELL_STATES above keeps exactly its four members, because every
// selector, every save and every test on this page is keyed on those values.
//
// THE WHOLE VALUE IS ONE NUMBER. A probe is the CHECKPOINT it opened at —
// how many entries the undo stack held at that moment — or null when none is
// open. Membership follows from it (probeCells) rather than being stored per
// cell, and that is what makes undo and redo move the probe for free: a
// stroke popped off `done` takes its cells out of the set with it, and no
// second place can disagree with the history about what the probe holds.
//
// Like Region's flag and the hint ladder's rung, the probe is player state:
// the transitions are here (ADR-0038/R4) and the value itself lives in
// solver.js, where the buttons and the tint are. It is never a cell state,
// never a stroke, and never saved — a load always starts with no probe open
// (which is also rule 9: leaving the page abandons an open probe).

//: The event names nextProbe understands — everything that can move a probe,
//: and nothing else can. "keep", "abandon" and "change" are the three the
//: page raises by itself; "open" is the only one a control raises directly.
export const PROBE_EVENTS = Object.freeze(["open", "keep", "abandon", "change"]);

// The probe after `event`, given it was `probe` (null, or a checkpoint) and
// the history is now `history`:
//   "open"     a probe opens at the current position — the undo stack's
//              length (rule 2). DEPTH 1 (rule 1): an open probe is returned
//              unchanged, so pressing the control again cannot nest one.
//   "keep"     the marks become normal and the probe closes (rule 5). The
//              board is not touched: commit is a change of status, not of
//              cells. This is also the answer for the two closes the page
//              makes on the player's behalf — a board that reaches the
//              solved state was a correct hypothesis (rule 7), and a reset
//              clears the board the hypothesis was about (rule 10).
//   "abandon"  the probe closes after abandonProbe has undone it (rule 4).
//   "change"   something was recorded — the CLAMP of rule 6: the checkpoint
//              is never past the undo stack, so undoing past it shrinks the
//              probe instead of making strokes made BEFORE it members. A
//              probe can shrink to empty and stay open, and the next mark
//              belongs to it.
// The three closing events share one answer and are three names rather than
// one because the call sites name the rule they are invoking; nothing here
// can tell them apart, and no test pretends to. Any other `event` is a
// RangeError, like nextRegion's and stepZoom's: a typo must not read as a
// quiet "leave it as it was", which is the one answer that would strand a
// probe open for ever.
export function nextProbe(probe, history, event) {
  if (!PROBE_EVENTS.includes(event)) {
    throw new RangeError(`"${event}" is not a probe event (${PROBE_EVENTS.join(", ")})`);
  }
  if (event === "open") return probe === null ? history.done.length : probe;
  if (event === "change") return probe === null ? null : Math.min(probe, history.done.length);
  return null;
}

// The cells the open probe at `probe` holds: every cell of every stroke
// recorded since the checkpoint, each cell once, in the order first marked,
// as a frozen array of frozen [row, col] pairs. Empty when no probe is open,
// and empty while an open probe holds no stroke.
//
// A MARK MADE, not a cell changed (rule 3). A cell marked during the probe
// and then marked back to the state it had before it is still the probe's:
// the player touched it under the hypothesis, which is what the tint says.
// Reading membership off the strokes rather than off a before/after
// comparison of two boards is also what makes rule 6's clamp enough — there
// is no per-cell record to repair when the checkpoint moves.
export function probeCells(history, probe) {
  const cells = [];
  if (probe === null) return Object.freeze(cells);
  const seen = new Set();
  for (let index = probe; index < history.done.length; index += 1) {
    for (const [row, col] of history.done[index].stroke.cells) {
      const key = `${row},${col}`;
      if (seen.has(key)) continue;
      seen.add(key);
      cells.push(Object.freeze([row, col]));
    }
  }
  return Object.freeze(cells);
}

// `history` undone back to `probe`'s checkpoint (rule 4): the board is
// exactly the board the probe opened on, and the probe's strokes sit on the
// redo stack like any other undos — which is what makes "redo after an
// abandon follows the existing history rules" true by construction instead of
// by a rule of its own. `history` itself when no probe is open.
//
// The loop is total: `probe` is never negative, so done.length > probe means
// there is a stroke to undo and undo always steps. Nothing here is a new
// kind of move — an abandon IS a run of undos, which is why one undo after it
// goes on past the checkpoint as it always did.
export function abandonProbe(history, probe) {
  if (probe === null) return history;
  let at = history;
  while (at.done.length > probe) at = undo(at);
  return at;
}

// The history a save is written from while `probe` is open (rule 9): the
// history as of the checkpoint — the checkpoint board and the undo stack's
// checkpoint prefix. `history` itself when no probe is open.
//
// So a save never holds a probe stroke, deserializeState has nothing new to
// parse, and compatibility holds BOTH ways (G-5): a save written by today's
// player loads here unchanged, and a save written here loads in today's
// player. A reload resumes at the probe's start, which is "leaving the page
// abandons the open probe" — and the page says so beside the controls.
//
// DIVERGENCE FROM RULE 9, in the REDO STACK only, recorded here because the
// card's block is the contract and is not edited to match code: the prefix
// carries NO redo stack, where "the save as of the checkpoint" would have
// carried the one the player had then. The probe is one number, and from one
// number the undone strokes of an open probe cannot be told from pre-probe
// ones (undo a probe stroke and it sits on `undone` exactly as a pre-probe
// stroke would), so the only safe answer is to carry none — never a probe
// stroke the save must not hold. What it costs is bounded and reachable only
// one way: undo past the checkpoint while a probe is open, and a redo that
// was pending is not restorable after a reload (the live player's redo is
// untouched). In every other case the cost is zero, because `record` has
// already dropped the redo stack itself.
export function checkpointHistory(history, probe) {
  if (probe === null) return history;
  const keep = Math.min(probe, history.done.length);
  const board = keep === history.done.length ? history.board : history.done[keep].before;
  return historyOf(board, history.done.slice(0, keep), []);
}

// ---------------------------------------------------------------------------
// Saving a game in this browser (CARD-185; FR-044 AC-360..AC-365, EC-046/047)
//
// Pure: these functions build and read the TEXT of a save. Reading and
// writing it in the browser's storage is solver.js's job (ADR-0038/R4).
// A save is the JSON of
//   { v: SAVE_VERSION, id, width, height, rows, columns,
//     grid:   gridFingerprint of the payload's solution (never the solution),
//     done:   the undo stack's strokes, oldest first,
//     undone: the redo stack, in its stack order (next to redo last) }
// with each stroke as { cells: [[row, col], ...], state } plus hint: true
// only on a hint's stroke. The board, the error count, the solved state and
// the hint count all follow from those strokes replayed from a blank board.

export const SAVE_VERSION = 1;

// The storage key of puzzle `puzzleId`'s save. The version is in the value,
// not the key, so a later format replaces the same entry.
export function saveKey(puzzleId) {
  return "nonogram-player:" + puzzleId;
}

// 32-bit FNV-1a of the solution read row-major as "1" (filled) / "0", as
// eight lower-case hex digits.
export function gridFingerprint(solution) {
  let hash = 0x811c9dc5;
  for (const row of solution) {
    for (const filled of row) {
      hash = Math.imul(hash ^ (filled ? 0x31 : 0x30), 0x01000193) >>> 0;
    }
  }
  return hash.toString(16).padStart(8, "0");
}

function savedStroke(stroke) {
  const saved = { cells: stroke.cells.map(([row, col]) => [row, col]), state: stroke.state };
  if (stroke.hint === true) saved.hint = true;
  return saved;
}

// The save of `history` for `payload`, as JSON text — or null when the
// history does not start from a blank board (only solver.js setBoard makes
// such a history), because a save is replayed from a blank board.
export function serializeState(history, payload) {
  const first = history.done.length > 0 ? history.done[0].before : history.board;
  if (!first.cells.every((state) => state === UNKNOWN)) return null;
  return JSON.stringify({
    v: SAVE_VERSION,
    id: payload.id,
    width: payload.width,
    height: payload.height,
    rows: payload.rows,
    columns: payload.columns,
    grid: gridFingerprint(payload.solution),
    done: history.done.map((entry) => savedStroke(entry.stroke)),
    undone: history.undone.map(savedStroke),
  });
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

// The stroke a saved stroke stands for, or null when it is malformed: cells
// not an array of [int, int] on a width x height board, a state not in
// CELL_STATES, or a hint that is present and not true.
function strokeOf(saved, width, height) {
  if (!isRecord(saved) || !Array.isArray(saved.cells) || !CELL_STATES.includes(saved.state)) return null;
  const onBoard = (cell) => Array.isArray(cell) && cell.length === 2
    && Number.isInteger(cell[0]) && cell[0] >= 0 && cell[0] < height
    && Number.isInteger(cell[1]) && cell[1] >= 0 && cell[1] < width;
  if (!saved.cells.every(onBoard)) return null;
  if (Object.hasOwn(saved, "hint")) {
    return saved.hint === true ? Object.freeze({ ...makeStroke(saved.cells, saved.state), hint: true }) : null;
  }
  return makeStroke(saved.cells, saved.state);
}

// The history a save describes, rebuilt from a blank board with record and
// undo — or null when `text` cannot be trusted for `payload`: not JSON, not
// an object, another version, another id / size / clues / grid fingerprint,
// a malformed stroke, a `done` stroke that changes no cell, or an `undone`
// stroke that cannot be redone as a step. Never throws.
export function deserializeState(text, payload) {
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    return null;
  }
  if (!isRecord(data) || data.v !== SAVE_VERSION || data.id !== payload.id
      || data.width !== payload.width || data.height !== payload.height
      || JSON.stringify(data.rows) !== JSON.stringify(payload.rows)
      || JSON.stringify(data.columns) !== JSON.stringify(payload.columns)
      || data.grid !== gridFingerprint(payload.solution)
      || !Array.isArray(data.done) || !Array.isArray(data.undone)) {
    return null;
  }
  const done = data.done.map((saved) => strokeOf(saved, payload.width, payload.height));
  const undone = data.undone.map((saved) => strokeOf(saved, payload.width, payload.height));
  if (done.includes(null) || undone.includes(null)) return null;
  let history = createHistory(createBoard(payload.width, payload.height));
  // The redo stack is recorded from its top down, then undone as many times.
  for (const stroke of [...done, ...undone.slice().reverse()]) {
    const next = record(history, stroke);
    if (next === history) return null;
    history = next;
  }
  for (let k = 0; k < undone.length; k += 1) history = undo(history);
  return history;
}
