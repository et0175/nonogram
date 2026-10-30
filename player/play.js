// The public player's glue for /play/<key> (COMP-011, FR-045, ADR-0041).
//
// What this file is, and what it is deliberately not
// --------------------------------------------------
// The board STATE is not here. Every cell transition, every stroke and the
// whole undo/redo history come from solver_state.js — the admin player's pure
// module, which CARD-160 split out for exactly this reuse and ADR-0041/R3
// requires to be a byte-identical build-time copy (player/assemble.py makes
// it; tests/test_public_player.py fails if the served copy differs from
// src/nonogram/admin/static/solver_state.js by one byte). So "the same state
// transitions as the admin player" is true by construction here rather than
// by imitation: this file turns input into clickStroke / dragStroke /
// resetStroke / record / undo / redo calls and paints what comes back, which
// is the same division of labour solver.js keeps.
//
// What IS here is the UI glue, rewritten rather than shared: solver.js is
// built around a Flask-rendered page with an embedded payload, a brush menu,
// zoom controls, an error count, a hint button and a progress percent. This
// page fetches its puzzle, has three brushes and no counters.
//
// THE PAGE NEVER HAS THE ANSWER (ADR-0038/R6, ADR-0041/R2)
// -------------------------------------------------------
// puzzle/<key>.json carries clues and extent, and no solution grid — nothing
// the site serves does. Three consequences, all of them visible in the code
// below:
//
//   * `isClueSolved` is the solved check: every row and column clue satisfied
//     by the FILLED cells. For a uniquely solvable puzzle that is exactly the
//     solution (CON-005 / INV-002 make every published puzzle uniquely
//     solvable, which is what the check rests on — ADR-0041's Consequences
//     say so in as many words). It is written here, natively, and NOT built
//     out of solver_state.js's circledNumbers: that function circles a number
//     under three rules, two of which fire on marks that satisfy no clue, so
//     "every number circled" is not "every clue satisfied";
//   * solver_state.js's isSolved, errorCount, solvedPercent and hintCell all
//     take `solution` and are therefore unreachable from this page. No error
//     count, no progress percent, no hints (CARD-283 G-4). Adding any of them
//     publicly needs the answer, which is a new architecture question;
//   * the save below is this file's own, not serializeState /
//     deserializeState. Those two fingerprint `payload.solution` into the
//     save and refuse a save whose fingerprint does not match, so they cannot
//     be called here at all. Reimplemented natively rather than imported
//     around — the precedent CLAUDE.md names for exactly this situation — and
//     cross-checked against the module's stroke values in the test tree.
//
// PLAY STATE IS THIS BROWSER'S, AND NOTHING ELSE'S (ADR-0041/R4, EC-050,
// CON-021 as amended). The save is one localStorage entry per puzzle key.
// There is no account, no server-side state and no write request of any kind:
// the only request this page issues is the GET of its own puzzle file.
//
// window.publicPlayer, set once the board is drawn (and left unset when the
// payload is refused, so a test cannot mistake a failed load for an empty
// board):
//   payload        the fetched puzzle file, frozen
//   getBoard()     the DISPLAYED board (mid-drag, the preview)
//   getHistory()   the recorded history
//   isSolved()     whether every clue is satisfied on the recorded board
//   getTool()      the chosen brush
//   isRegion()     whether Region is armed
//   saveKey        the localStorage key this puzzle's save lives under

import {
  UNKNOWN, FILLED, EMPTY, CELL_STATES,
  createBoard, createHistory, record, undo, redo,
  applyStroke, clickStroke, dragStroke, resetStroke,
  gesturePaints, nextRegion,
} from "/solver_state.js";

// Every fifth line carries the heavier rule, as on the printed sheet and in
// the admin player (CARD-160). The last line never does: it is the board's
// own edge.
const MAJOR_EVERY = 5;

// The save's format version. In the value, never in the key, so a later
// format replaces the same entry — solver_state.js's SAVE_VERSION makes the
// same choice for the admin player's save and gives the reason.
const SAVE_VERSION = 1;

// The three brushes this page offers. solver_state.js knows four cell states;
// MAYBE ("?") is the admin player's fourth and is not offered here, so a cell
// reachable from this page is one of these three (CARD-283, "three cell
// states"). The order is the DOM's.
const TOOLS = [FILLED, EMPTY, UNKNOWN];

const majorAfter = (index, count) => (index + 1) % MAJOR_EVERY === 0 && index + 1 !== count;

// --------------------------------------------------------------------------
// The key, from the URL
// --------------------------------------------------------------------------

// A public puzzle key: the first 10 lowercase hex characters of a SHA-256
// digest (ADR-0041/R1). Checked before anything is fetched, so a hand-typed
// path cannot turn into a request for an arbitrary file.
const KEY = /^[0-9a-f]{10}$/;

// The key `path` names, or null. The last non-empty segment of /play/<key>,
// so a trailing slash is accepted and /play/ alone is not a key.
export function keyOf(path) {
  const segments = String(path).split("/").filter((segment) => segment !== "");
  const last = segments.at(-1);
  return last !== undefined && KEY.test(last) ? last : null;
}

// --------------------------------------------------------------------------
// The payload, checked rather than trusted
// --------------------------------------------------------------------------

// Whether `clue` is a run-length encoding a line of `length` cells could
// have: [0] for an empty line (the AC-013 convention, never []), otherwise
// positive runs that fit with one gap between each pair. The same rule
// player/assemble.py applies when it writes the file — deliberately twice,
// once on each side of the wire, because a page that trusts its input is a
// page whose input decides what it does.
function isClue(clue, length) {
  if (!Array.isArray(clue) || clue.length === 0) return false;
  if (!clue.every((n) => Number.isInteger(n) && n >= 0)) return false;
  if (clue.includes(0)) return clue.length === 1;
  return clue.reduce((a, b) => a + b, 0) + clue.length - 1 <= length;
}

// The puzzle `data` describes, frozen — or null when it is not one. Shape:
//   { key, width, height, tier, clues: { rows, columns } }
// A tier is a display label and may be empty; nothing else may be missing.
export function readPayload(data, key) {
  if (data === null || typeof data !== "object" || Array.isArray(data)) return null;
  const { width, height, clues } = data;
  if (data.key !== key || !Number.isInteger(width) || !Number.isInteger(height)) return null;
  if (width < 1 || height < 1 || typeof data.tier !== "string") return null;
  if (clues === null || typeof clues !== "object") return null;
  const { rows, columns } = clues;
  if (!Array.isArray(rows) || rows.length !== height) return null;
  if (!Array.isArray(columns) || columns.length !== width) return null;
  if (!rows.every((clue) => isClue(clue, width))) return null;
  if (!columns.every((clue) => isClue(clue, height))) return null;
  return Object.freeze({
    key,
    width,
    height,
    tier: data.tier,
    rows: Object.freeze(rows.map((clue) => Object.freeze([...clue]))),
    columns: Object.freeze(columns.map((clue) => Object.freeze([...clue]))),
  });
}

// --------------------------------------------------------------------------
// Solved, without the answer (ADR-0038/R6; AC-384)
// --------------------------------------------------------------------------

// The lengths of `cells`'s runs of FILLED cells, left to right — [0] when
// there are none, the same convention a clue uses. Every state that is not
// FILLED (EMPTY, UNKNOWN and the "?" the admin player can leave behind in a
// save) breaks a run, so this reads the marks exactly as a printed line reads.
export function runsOf(cells) {
  const runs = [];
  let run = 0;
  for (const state of cells) {
    if (state === FILLED) {
      run += 1;
    } else if (run > 0) {
      runs.push(run);
      run = 0;
    }
  }
  if (run > 0) runs.push(run);
  return runs.length > 0 ? runs : [0];
}

const sameNumbers = (a, b) => a.length === b.length && a.every((n, i) => n === b[i]);

// Whether every row and column clue of `board` is satisfied by its FILLED
// cells. This is the whole of the public player's completion rule: a board
// satisfying every clue of a uniquely solvable puzzle IS its solution, and
// the page has nothing else to compare against.
export function isClueSolved(board, rows, columns) {
  const { width, height, cells } = board;
  for (let row = 0; row < height; row += 1) {
    const line = Array.from({ length: width }, (_, col) => cells[row * width + col]);
    if (!sameNumbers(runsOf(line), rows[row])) return false;
  }
  for (let col = 0; col < width; col += 1) {
    const line = Array.from({ length: height }, (_, row) => cells[row * width + col]);
    if (!sameNumbers(runsOf(line), columns[col])) return false;
  }
  return true;
}

// --------------------------------------------------------------------------
// The save (ADR-0041/R4, EC-050): this browser's localStorage, nothing else
// --------------------------------------------------------------------------

export const saveKey = (key) => `nonogram-public:${key}`;

const savedStroke = (stroke) => ({
  cells: stroke.cells.map(([row, col]) => [row, col]),
  state: stroke.state,
});

// The save of `history` as JSON text, or null when the history does not start
// from a blank board (a save is replayed from one). The clues are in the save
// and are compared on the way back in, so a re-export that changed a puzzle's
// clues under the same key cannot replay marks onto a different puzzle.
export function serialize(history, payload) {
  const first = history.done.length > 0 ? history.done[0].before : history.board;
  if (!first.cells.every((state) => state === UNKNOWN)) return null;
  return JSON.stringify({
    v: SAVE_VERSION,
    key: payload.key,
    width: payload.width,
    height: payload.height,
    rows: payload.rows,
    columns: payload.columns,
    done: history.done.map((entry) => savedStroke(entry.stroke)),
    undone: history.undone.map(savedStroke),
  });
}

function strokeOf(saved, width, height) {
  if (saved === null || typeof saved !== "object" || Array.isArray(saved)) return null;
  if (!Array.isArray(saved.cells) || !CELL_STATES.includes(saved.state)) return null;
  const onBoard = (cell) => Array.isArray(cell) && cell.length === 2
    && Number.isInteger(cell[0]) && cell[0] >= 0 && cell[0] < height
    && Number.isInteger(cell[1]) && cell[1] >= 0 && cell[1] < width;
  if (!saved.cells.every(onBoard)) return null;
  return Object.freeze({
    cells: Object.freeze(saved.cells.map(([row, col]) => Object.freeze([row, col]))),
    state: saved.state,
  });
}

// The history `text` describes, rebuilt from a blank board with record and
// undo — or null when it cannot be trusted for `payload`: not JSON, another
// version, another key, size or clues, a malformed stroke, a `done` stroke
// that changes no cell, or an `undone` stroke that cannot be redone as a
// step. Never throws.
export function deserialize(text, payload) {
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    return null;
  }
  if (data === null || typeof data !== "object" || Array.isArray(data)) return null;
  if (data.v !== SAVE_VERSION || data.key !== payload.key) return null;
  if (data.width !== payload.width || data.height !== payload.height) return null;
  if (JSON.stringify(data.rows) !== JSON.stringify(payload.rows)) return null;
  if (JSON.stringify(data.columns) !== JSON.stringify(payload.columns)) return null;
  if (!Array.isArray(data.done) || !Array.isArray(data.undone)) return null;
  const done = data.done.map((saved) => strokeOf(saved, payload.width, payload.height));
  const undone = data.undone.map((saved) => strokeOf(saved, payload.width, payload.height));
  if (done.includes(null) || undone.includes(null)) return null;
  let history = createHistory(createBoard(payload.width, payload.height));
  for (const stroke of [...done, ...undone.slice().reverse()]) {
    const next = record(history, stroke);
    if (next === history) return null;
    history = next;
  }
  for (let k = 0; k < undone.length; k += 1) history = undo(history);
  return history;
}

// Reading and writing it. Every access is caught and silent, window.
// localStorage itself included: a browser with storage blocked plays exactly
// as one without, and a failed write removes the entry so a reload never
// shows an older board than the one on screen (solver.js's browserSave makes
// the same two choices, for the same reasons).
function storage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function readSave(key) {
  try {
    return storage()?.getItem(saveKey(key)) ?? null;
  } catch {
    return null;
  }
}

function writeSave(key, text) {
  const store = storage();
  if (store === null) return;
  try {
    if (text === null) store.removeItem(saveKey(key));
    else store.setItem(saveKey(key), text);
  } catch {
    try {
      store.removeItem(saveKey(key));
    } catch {
      /* nothing left to try; the page plays on without a save */
    }
  }
}

// --------------------------------------------------------------------------
// Drawing
// --------------------------------------------------------------------------

function clueBox(clue, line, axis, count) {
  const box = document.createElement("th");
  box.className = `player-clue is-${axis}`;
  box.scope = axis === "row" ? "row" : "col";
  box.dataset.line = String(line);
  if (axis === "col" && majorAfter(line, count)) box.classList.add("major-right");
  if (axis === "row" && majorAfter(line, count)) box.classList.add("major-below");
  for (const number of clue) {
    const span = document.createElement("span");
    span.className = "player-clue-num";
    span.textContent = String(number);
    box.append(span);
  }
  return box;
}

// The board's table, and the cell elements in row-major order. The DOM
// contract is the admin player's (solver.js's header documents it): th.player
// -clue.is-col above with its 0-based line in data-line, th.player-clue.is-row
// to the left, td.player-cell with data-row, data-col and data-state.
function drawBoard(stage, payload) {
  const { width, height, rows, columns } = payload;
  stage.replaceChildren();
  const table = document.createElement("table");
  table.className = "player-board";
  table.style.setProperty("--player-width", String(width));
  table.style.setProperty("--player-height", String(height));

  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  const corner = document.createElement("th");
  corner.className = "player-clue is-corner";
  headRow.append(corner);
  for (let col = 0; col < width; col += 1) headRow.append(clueBox(columns[col], col, "col", width));
  head.append(headRow);

  const body = document.createElement("tbody");
  const cells = [];
  for (let row = 0; row < height; row += 1) {
    const tr = document.createElement("tr");
    tr.append(clueBox(rows[row], row, "row", height));
    for (let col = 0; col < width; col += 1) {
      const cell = document.createElement("td");
      cell.className = "player-cell";
      cell.dataset.row = String(row);
      cell.dataset.col = String(col);
      cell.dataset.state = UNKNOWN;
      if (majorAfter(col, width)) cell.classList.add("major-right");
      if (majorAfter(row, height)) cell.classList.add("major-below");
      // The solved sweep's per-cell delay (player.css), as solver.js sets it
      // for the admin player: a diagonal, so the flash crosses the picture.
      cell.style.setProperty("--player-wave", String(row + col));
      tr.append(cell);
      cells.push(cell);
    }
    body.append(tr);
  }
  table.append(head, body);
  stage.append(table);
  return cells;
}

const paint = (cells, board) => {
  for (let index = 0; index < cells.length; index += 1) cells[index].dataset.state = board.cells[index];
};

// --------------------------------------------------------------------------
// The page
// --------------------------------------------------------------------------

function fail(stage, message) {
  const paragraph = stage.querySelector("[data-player-fallback]") ?? document.createElement("p");
  paragraph.className = "player-fallback";
  paragraph.textContent = message;
  stage.replaceChildren(paragraph);
}

function cellUnder(x, y) {
  const cell = document.elementFromPoint(x, y)?.closest("td.player-cell");
  return cell ? [Number(cell.dataset.row), Number(cell.dataset.col)] : null;
}

const isAt = (a, b) => a[0] === b[0] && a[1] === b[1];

function start(payload) {
  const stage = document.querySelector("[data-player-stage]");
  const controls = document.querySelector("[data-player-controls]");
  const solved = document.querySelector("[data-player-solved]");
  const announce = document.querySelector("[data-player-announce]");
  const hint = document.querySelector("[data-player-hint]");
  const regionToggle = document.querySelector("[data-player-region]");
  const actions = {};
  for (const button of document.querySelectorAll("[data-player-action]")) {
    actions[button.dataset.playerAction] = button;
  }

  document.querySelector("[data-player-title]").textContent =
    `Puzzle ${payload.width}×${payload.height}`;
  document.title = `Puzzle ${payload.width}×${payload.height} · Nonogram`;
  const tierChip = document.querySelector("[data-player-tier]");
  if (payload.tier !== "") {
    tierChip.textContent = payload.tier.toUpperCase();
    tierChip.hidden = false;
  }

  const cells = drawBoard(stage, payload);
  const board = createBoard(payload.width, payload.height);
  let history = deserialize(readSave(payload.key), payload) ?? createHistory(board);
  let shown = history.board;
  let tool = FILLED;
  let region = false;
  let lastClick = null;
  let gesture = null;

  const setDisabled = (button, disabled) => {
    if (button) button.setAttribute("aria-disabled", disabled ? "true" : "false");
  };

  function refresh() {
    paint(cells, shown);
    setDisabled(actions.undo, history.done.length === 0);
    setDisabled(actions.redo, history.undone.length === 0);
    setDisabled(actions.reset, history.board.cells.every((state) => state === UNKNOWN));
    const done = isClueSolved(history.board, payload.rows, payload.columns);
    solved.hidden = !done;
    document.body.dataset.solved = done ? "true" : "false";
    regionToggle.setAttribute("aria-pressed", region ? "true" : "false");
    for (const button of document.querySelectorAll("[data-player-tool]")) {
      button.setAttribute("aria-checked", button.dataset.playerTool === tool ? "true" : "false");
    }
    for (const swatch of regionToggle.querySelectorAll(".player-swatch")) swatch.dataset.state = tool;
    stage.querySelector(".player-board")?.classList.toggle("is-region", region);
  }

  // Everything that changes the recorded history goes through here: the board
  // is repainted, the save is rewritten and a run of repeat clicks ends.
  function commit(next) {
    history = next;
    shown = next.board;
    lastClick = null;
    writeSave(payload.key, serialize(history, payload));
    refresh();
  }

  function setRegion(armed) {
    region = armed;
    refresh();
  }

  stage.addEventListener("pointerdown", (event) => {
    if (gesture || (event.pointerType === "mouse" && event.button !== 0)) return;
    const from = cellUnder(event.clientX, event.clientY);
    if (!from) return;
    // A mouse drag always marks; a touch or pen drag marks only while Region
    // is armed, so with Region off the browser is free to pan the page
    // instead (solver_state.js gesturePaints — the rule, not a copy of it).
    // Read once, at pointerdown, like the brush: arming Region mid-gesture
    // does not retroactively change this one.
    const paints = gesturePaints(event.pointerType, region);
    if (paints) {
      event.preventDefault();
      stage.setPointerCapture(event.pointerId);
    }
    gesture = { pointerId: event.pointerId, start: from, path: [], dragging: false, tool, paints };
  });

  stage.addEventListener("pointermove", (event) => {
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    const at = cellUnder(event.clientX, event.clientY);
    const previous = gesture.path.at(-1) ?? gesture.start;
    if (!at || isAt(at, previous)) return;
    gesture.path.push(at);
    gesture.dragging = gesture.dragging || !isAt(at, gesture.start);
    if (gesture.dragging && gesture.paints) {
      shown = applyStroke(history.board, dragStroke(gesture.start, gesture.path, gesture.tool));
      refresh();
    }
  });

  stage.addEventListener("pointerup", (event) => {
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    const done = gesture;
    gesture = null;
    if (done.dragging) {
      if (!done.paints) {
        // A touch or pen gesture that left its starting cell: not a tap, so
        // not a click, and it marks nothing either way.
        shown = history.board;
        refresh();
        return;
      }
      // Region is one-shot and disarms itself the instant a drag is recorded
      // — "a drag ended", not "a cell changed" (solver_state.js nextRegion).
      setRegion(nextRegion(region, "drag"));
      commit(record(history, dragStroke(done.start, done.path, done.tool)));
      return;
    }
    const [row, col] = done.start;
    const repeat = lastClick !== null && lastClick.row === row
      && lastClick.col === col && lastClick.tool === done.tool;
    commit(record(history, clickStroke(history.board, row, col, done.tool, repeat)));
    lastClick = { row, col, tool: done.tool };
  });

  stage.addEventListener("pointercancel", (event) => {
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    gesture = null;
    shown = history.board;
    refresh();
  });

  for (const button of document.querySelectorAll("[data-player-tool]")) {
    button.addEventListener("click", () => {
      const chosen = button.dataset.playerTool;
      if (!TOOLS.includes(chosen)) return;
      tool = chosen;
      lastClick = null;
      refresh();
    });
  }

  // Region and the brush are independent in both directions: pressing Region
  // never changes the brush and picking a brush never disarms Region
  // (solver_state.js nextRegion's divergence note, owner 2026-10-14).
  regionToggle.addEventListener("click", () => setRegion(nextRegion(region, "toggle")));

  actions.undo?.addEventListener("click", () => commit(undo(history)));
  actions.redo?.addEventListener("click", () => commit(redo(history)));
  actions.reset?.addEventListener("click", () => {
    commit(record(history, resetStroke(history.board)));
    announce.textContent = "Board reset. Undo brings the marks back.";
  });

  document.addEventListener("keydown", (event) => {
    if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "z") return;
    event.preventDefault();
    commit(event.shiftKey ? redo(history) : undo(history));
  });

  controls.hidden = false;
  hint.hidden = false;
  refresh();

  window.publicPlayer = Object.freeze({
    payload,
    getBoard: () => shown,
    getHistory: () => history,
    isSolved: () => isClueSolved(history.board, payload.rows, payload.columns),
    getTool: () => tool,
    isRegion: () => region,
    saveKey: saveKey(payload.key),
  });
}

async function load() {
  const stage = document.querySelector("[data-player-stage]");
  const key = keyOf(window.location.pathname);
  if (key === null) {
    fail(stage, "This address names no puzzle. A puzzle link looks like /play/ followed by ten letters and digits.");
    return;
  }
  let data;
  try {
    const response = await fetch(`/puzzle/${key}.json`, { cache: "no-store" });
    if (!response.ok) throw new Error(String(response.status));
    data = await response.json();
  } catch {
    fail(stage, "This puzzle is not on the site. It may not have been published yet.");
    return;
  }
  const payload = readPayload(data, key);
  if (payload === null) {
    fail(stage, "This puzzle's file could not be read, so the board was not drawn.");
    return;
  }
  start(payload);
}

if (typeof document !== "undefined") load();
