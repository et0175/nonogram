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
// an error count, a hint button and a progress percent. This page fetches its
// puzzle, has the same four brushes and no counters.
//
// ZOOM IS THE MODULE'S ARITHMETIC AND THIS FILE'S RENDERING (CARD-324,
// ADR-0038/R4, ADR-0041/R3)
// ---------------------------------------------------------------------
// Until CARD-324 this page SERVED the zoom arithmetic and called none of it:
// solver_state.js exports ZOOM_MIN, ZOOM_MAX, ZOOM_STEP, clampZoom,
// stepZoom, pinchZoom and anchoredScroll, the served copy carries all seven,
// and the only mention of zoom in this file was the sentence above. That is
// duplication-shaped debt waiting to happen rather than a missing feature,
// and the whole of the fix is the glue below.
//
// Nothing about the zoom is derived here. There is no bound, no step and no
// clamp expression in this file: the percent starts at ZOOM_MIN, the buttons
// ask stepZoom what the next one is, a pinch asks pinchZoom, and the scroll
// position that keeps the anchored cell still comes from anchoredScroll.
// Both of those functions clamp their own return, which is why applyZoom
// below does not (solver.js's own applyZoom says the same in as many words),
// and it is why clampZoom and ZOOM_STEP are NOT imported: this file has no
// use for either that is not already inside stepZoom/pinchZoom, and an
// unused import is a second place to look for a rule that lives in one. The
// five names imported are exactly the five solver.js's own glue imports, and
// tests/test_public_player_zoom.py derives that set from solver.js rather
// than listing it, so the two pages' consumed surface cannot drift apart.
//
// Zoom is a VIEW: it changes no board state, records no stroke, never enters
// the history or the save, and resets to ZOOM_MIN on every load — the same
// three properties the admin's zoom has.
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
//   getZoom()      the zoom percent, ZOOM_MIN..ZOOM_MAX (view only)
//   saveKey        the localStorage key this puzzle's save lives under

import {
  UNKNOWN, FILLED, EMPTY, MAYBE, CELL_STATES,
  createBoard, createHistory, record, undo, redo,
  applyStroke, clickStroke, dragStroke, resetStroke,
  gesturePaints, nextRegion,
  ZOOM_MIN, ZOOM_MAX, stepZoom, pinchZoom, anchoredScroll,
} from "/solver_state.js";

// Every fifth line carries the heavier rule, as on the printed sheet and in
// the admin player (CARD-160). The last line never does: it is the board's
// own edge.
const MAJOR_EVERY = 5;

// The save's format version. In the value, never in the key, so a later
// format replaces the same entry — solver_state.js's SAVE_VERSION makes the
// same choice for the admin player's save and gives the reason.
const SAVE_VERSION = 1;

// The four brushes this page offers: solver_state.js's four cell states, all
// of them. MAYBE ("?") was withheld until CARD-323 — not because the page
// could not reach it (every transition it needs is in the module this page
// already shares, and player.css already carried the mark's look) but as a
// scope choice, which the owner reversed on 2026-10-30. What stays out is the
// three features that take `solution`, named in the header above; a brush is
// not one of them, so a cell reachable from this page is any of the four.
//
// The order is the DOM's, and it is the ADMIN player's menu order —
// filled, empty, maybe, unknown (templates/puzzle_solve.html's
// .player-tool-menu). Matching it is the point of the card, and
// tests/test_public_player_maybe.py reads that template rather than a list
// spelled twice, so a reorder on either side reds.
const TOOLS = [FILLED, EMPTY, MAYBE, UNKNOWN];

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
// FILLED (EMPTY, UNKNOWN and MAYBE, the "?" — since CARD-323 this page's own
// brush leaves it, and before that only a save from the admin player could)
// breaks a run, so this reads the marks exactly as a printed line reads.
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
      // CARD-328: tests/test_public_player_agreement.py holds this expression to solver.js's own — change it here and that guard reds.
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

// --------------------------------------------------------------------------
// The crosshair (CARD-325, FR-045)
// --------------------------------------------------------------------------
//
// Hovering a cell tints its row, its column and their two clue boxes, so the
// eye can travel from a cell to its clues and back without sliding onto a
// neighbouring line. The admin player has the same control (CARD-267,
// `wireCrosshair` in solver.js); it is written natively here, not imported,
// and tests/test_public_player_agreement.py holds the two to the same
// decisions (TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions).
//
// IT READS THE DOM AND NOTHING ELSE. One class, `.is-crossed`, on elements
// that are already on the page: no cell state, no history, no clue data, no
// payload field, no storage and no request (ADR-0038/R2, ADR-0041/R2). That
// is asserted over this source, default-deny, by
// tests/test_public_player_crosshair.py TestPublicCrosshair_ItReadsNoBoard:
// the functions below may use `document`, `Number`, `Set` and each other, and
// nothing else. It adds no toolbar control and touches no pointer event's
// default: the listeners call no callback, never preventDefault and never
// stop propagation, so every handler start() registered sees exactly the
// events it saw before (G-5).
//
// The four decisions CARD-267 paid for, followed rather than rediscovered:
//
//   1. THE GUTTER CORNER. A pointer over the stage but not over a cell — a
//      clue box, the corner, the stage's padding — keeps the crosshair where
//      it was. Only LEAVING the stage clears it, so looking from a cell to its
//      clue does not put the line out.
//   2. THE NO-HOVER PHONE. A touch crosshair follows the finger from
//      pointerdown (a tap may never move) through every move, and STAYS after
//      the finger lifts, so it is seen between taps.
//   3. WHY AN EXEMPT TOUCH. A released touch pointer fires pointerleave at
//      once, so a leave that did not exempt touch would undo every touch
//      crosshair the moment it was made. The pointer TYPE is read in the
//      leave handler, and only there (and in the pinch count below).
//   4. A REMEMBERED POSITION WITH NOTHING PAINTED IS THE HALF-PAINTED
//      CROSSHAIR. The admin calls forget() from redraw(). This page draws its
//      table once, so there is no redraw to hook; the refusal is kept by
//      construction instead: the "already there" shortcut is taken only when
//      the DOM still shows the cross painted, so a stale memory can never
//      suppress a repaint.
//
// WHAT THE ADMIN CARD DID NOT HAVE TO DECIDE (zoom, CARD-324):
//
//   * WHICH CELL. The cell under the pointer comes from the browser's hit
//     test (cellUnder, the call marking uses), never from geometry computed
//     here. A hit test is right at every zoom and every scroll offset of the
//     stage and of the page; arithmetic over scrollLeft and the cell pitch is
//     how a crosshair lands one cell off at 300%.
//   * A PINCH HAS NO CROSSHAIR. Two or more touch/pen pointers down is a
//     pinch. The first finger's pointerdown had already painted one, so the
//     second takes it off; nothing follows the spread; nothing is left when
//     the fingers lift. Crossing resumes with the next single pointer. This
//     is the crosshair's own count of pointers and reads none of start()'s
//     pinch state, so it also covers two fingers that began on a clue box,
//     which start() leaves to the browser.
//   * touch-action stays `auto` (owner, 2026-11-05); nothing here depends on
//     it, and no zoom control or toolbar button is involved.

// The elements the crosshair for (row, col) marks: that row's cells, that
// column's cells, and the clue boxes of that row and that column. Clue boxes
// are selected by AXIS and data-line, never by DOM order.
function crossedParts(table, row, col) {
  return [
    ...table.querySelectorAll(`td.player-cell[data-row="${row}"]`),
    ...table.querySelectorAll(`td.player-cell[data-col="${col}"]`),
    ...table.querySelectorAll(`th.player-clue.is-row[data-line="${row}"]`),
    ...table.querySelectorAll(`th.player-clue.is-col[data-line="${col}"]`),
  ];
}

function wireCrosshair(stage) {
  // Where the crosshair is, as [row, col], or null: a CELL and not an element.
  let crossed = null;
  // The touch/pen pointers currently down, id -> pointer type; and whether two
  // of them make this a pinch (cleared when the last one is up).
  const down = new Map();
  let pinching = false;

  function paint([row, col], on) {
    const table = stage.querySelector(".player-board");
    if (table === null) return;
    for (const part of crossedParts(table, row, col)) part.classList.toggle("is-crossed", on);
  }

  // Whether the cross for `position` is on the page right now.
  function isPainted([row, col]) {
    return stage.querySelector(`td.player-cell.is-crossed[data-row="${row}"][data-col="${col}"]`) !== null;
  }

  function clear() {
    if (crossed === null) return;
    paint(crossed, false);
    crossed = null;
  }

  function moveTo(position) {
    // Decision 4: the shortcut needs the cross to be SEEN, not remembered.
    if (crossed !== null && isAt(position, crossed) && isPainted(crossed)) return;
    if (crossed !== null) paint(crossed, false);
    crossed = position;
    paint(crossed, true);
  }

  const follow = (event) => {
    if (pinching) return;
    const position = cellUnder(event.clientX, event.clientY);
    if (position !== null) moveTo(position);
  };

  const isFinger = (event) => event.pointerType === "touch" || event.pointerType === "pen";

  stage.addEventListener("pointerdown", (event) => {
    if (isFinger(event)) {
      // A primary pointer starts a fresh session FOR ITS OWN TYPE: isPrimary is
      // per pointer type, so a pen's primary must not wipe a finger that is
      // still down (play.js counts touch and pen together as a pinch), and a
      // pointerup that never reached the stage cannot leave a stale entry of
      // the same type counting as a second pointer. (Found by review mutant E09.)
      if (event.isPrimary) {
        for (const [id, type] of down) if (type === event.pointerType) down.delete(id);
        pinching = down.size >= 2;
      }
      down.set(event.pointerId, event.pointerType);
      if (down.size >= 2) {
        pinching = true;
        clear();
        return;
      }
    }
    follow(event);
  });
  stage.addEventListener("pointermove", follow);

  const lift = (event) => {
    if (!down.delete(event.pointerId)) return;
    if (down.size === 0) pinching = false;
  };
  stage.addEventListener("pointerup", lift);
  stage.addEventListener("pointercancel", lift);

  stage.addEventListener("pointerleave", (event) => {
    // Decision 3: touch is exempt, and that exemption is the whole touch rule.
    if (event.pointerType === "touch") return;
    clear();
  });
}

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

  // ------------------------------------------------------------------ zoom
  // `zoom` is a percent in [ZOOM_MIN, ZOOM_MAX]. It is view state and
  // nothing else: `commit`, `serialize` and `refresh` never read it, so no
  // zoom change can reach the history, the save or a cell's data-state.
  const zoomOut = document.querySelector('[data-player-zoom-action="out"]');
  const zoomIn = document.querySelector('[data-player-zoom-action="in"]');
  const zoomReadout = document.querySelector("[data-player-zoom-readout]");
  let zoom = ZOOM_MIN;

  // Every live touch/pen pointer's viewport position, and the board cell it
  // went down on (a [row, col] or null). Kept regardless of `gesture` and of
  // Region, purely so a second finger can be recognised as a pinch; a mouse
  // pointer never enters either map.
  const touchPoints = new Map();
  const touchStartCell = new Map();
  // { firstId, secondId, startZoom, startDistance } while a pinch is running,
  // else null. See beginPinch for what a pinch does to a stroke in progress.
  let pinch = null;

  const distanceBetween = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

  // The readout and the two buttons' aria-disabled, from `zoom` alone. The
  // percent and both bounds are the module's; nothing here is a literal.
  function syncZoom() {
    zoomReadout.textContent = `${Math.round(zoom)}%`;
    zoomOut.setAttribute("aria-disabled", String(zoom <= ZOOM_MIN));
    zoomIn.setAttribute("aria-disabled", String(zoom >= ZOOM_MAX));
  }

  // Move to `nextPercent` — already clamped by whichever of stepZoom /
  // pinchZoom produced it — keeping the board point under `(anchorX,
  // anchorY)` where it was. The anchor is an offset inside .player-stage's
  // own visible box, not the page's, because the stage is the scroll
  // container both axes belong to. A no-op percent (a press at either end of
  // the range) touches neither the table nor the scroll position.
  function applyZoom(nextPercent, anchorX, anchorY) {
    const old = zoom;
    zoom = nextPercent;
    if (zoom !== old) {
      // --player-zoom multiplies player.css's fitted cell, exactly as
      // admin.css's own --player-zoom multiplies the panel's.
      stage.querySelector(".player-board")?.style.setProperty("--player-zoom", String(zoom / 100));
      // The gutters scale with the cell, so a zoom changes whether either
      // axis can still afford to keep its own in view. Before the scroll is
      // moved: the anchored positions below are read against the stage's own
      // box, which this does not change, but the gutter's width is what the
      // player is looking past.
      keepCluesInView();
      stage.scrollLeft = anchoredScroll(stage.scrollLeft, anchorX, old, zoom);
      stage.scrollTop = anchoredScroll(stage.scrollTop, anchorY, old, zoom);
    }
    syncZoom();
  }

  // THE PINCH/DRAG COLLISION, decided rather than left to listener order
  // (the card's item 4). Two pointers down on the stage is a pinch — and by
  // the time the second lands, the first has ALREADY begun a single-pointer
  // gesture, because `gesture` is set at pointerdown. What happens to that
  // gesture is the decision, and it is: the stroke is ABANDONED.
  //
  //   * its preview reverts to the recorded board (`shown = history.board`),
  //     so nothing a drag had painted stays on screen;
  //   * `gesture` is cleared, so the first finger's own later pointerup
  //     commits nothing — not the drag, and not even the single-cell CLICK
  //     it would otherwise have been. That last one is the sharp half: with
  //     Region off a touch gesture paints nothing anyway (gesturePaints),
  //     but it still ends as a tap, so a pinch that did not clear `gesture`
  //     would mark the cell the first finger went down on. That is exactly
  //     the cell AC-5 names;
  //   * `lastClick` is cleared, so the pinch also breaks a run of repeat
  //     taps rather than letting the next tap continue one across it;
  //   * `pinch` then swallows the pointerup/pointercancel of BOTH its
  //     pointers, whichever the browser releases first, so a pinch that ends
  //     with one finger still down marks nothing either.
  //
  // This is the same ruling solver.js took for the admin stage, reached the
  // same way; it is written natively here because the public page's pointer
  // handling is its own code and only the arithmetic is shared.
  function beginPinch(firstId, secondId) {
    if (gesture) {
      shown = history.board;
      gesture = null;
      refresh();
    }
    lastClick = null;
    pinch = {
      firstId,
      secondId,
      startZoom: zoom,
      // Math.max(…, 1): pinchZoom refuses a non-positive starting distance.
      // Two pointers reported at one point is not a real pinch but is not
      // impossible from synthetic input, and it must simply not zoom yet
      // rather than throw out of a listener.
      startDistance: Math.max(distanceBetween(touchPoints.get(firstId), touchPoints.get(secondId)), 1),
    };
  }

  // CARD-271's question, asked for this page — and the one thing the zoom
  // needed beyond the transform itself.
  //
  // The clue gutters are sticky so a panned board keeps its clues readable;
  // player.css's own header states that as a promise. They are sized from
  // --player-cell, so the zoom grows them with everything else — and on a
  // 390 px phone at 300% the ROW gutter alone is then wider than the whole
  // stage. Pinned, it covers every column and the board becomes unreachable:
  // measured on the 30-cell board, which is the case this card exists for,
  // and visible in the renders CARD-324 was reviewed from.
  //
  // So a gutter is pinned only while there is still room beside it for TWO
  // whole cells. Two, and derived rather than chosen: a window of width w
  // laid over cells of pitch c holds a whole cell at EVERY scroll offset
  // exactly when w >= 2c (at w < 2c some offset straddles the only cell
  // there is, and at w = c that is every offset but the aligned one). One
  // cell was this rule's first spelling, and cycle 1's render of the 175%
  // rung shows what it allowed: 60 px of band beside a 299 px gutter, a
  // 50 px cell, and at the scroll the zoom itself lands on, zero whole cells
  // in view. The threshold is a property of the board's own cell and the
  // argument above — no share, no tuned constant — and it is deliberately
  // NARROWER than the admin's own rule
  // (solver.js's keepCluesInView, STICK_MAX_SHARE = 0.4): that rule applied
  // at this width would unpin this page's row gutter at 100% as well, which
  // contradicts player.css's promise and the reading
  // tests/test_public_player.py::test_phone_viewport_is_playable makes of it.
  // Which of the two rules the public page should take is an owner decision
  // and is NOT taken here. This one changes nothing below the zoom at which
  // the board stops being reachable at all.
  //
  // The column axis is measured against the VISIBLE height of the stage, not
  // its clientHeight. The stage's cap is derived from where the stage really
  // starts (the first lines of the function below), so in the ordinary case
  // its bottom edge is on screen and the two are the same number; the min
  // stays for the cases where the cap is not what bounds the stage (the
  // moment before the first measurement, the dynamic toolbar of a phone
  // browser moving `innerHeight` under a cap computed for `svh`), because
  // the part that counts is the part visible with the page at its top, and
  // the page scrolling further down only shows more of the stage, so this is
  // conservative, never wrong. (That last claim has a premise, and the premise
  // is an inequality: the space below the stage must be smaller than the
  // stage's own top offset, else scrolling the page could hide the band from
  // a reading taken at the top. tests/test_public_player_zoom.py asserts it.)
  //
  // It is recomputed on resize, because the geometry it reads is the
  // viewport's: a rotation changes the stage's width, its visible height and
  // the toolbar's wrapping with no zoom press to re-run it. (Zoomed to 250%
  // on a portrait phone, then rotated, the classes were left holding the
  // PORTRAIT answer — both wrong — and no cell was reachable until a zoom
  // button was pressed.) `resize` alone is bound: orientationchange can fire
  // before the new dimensions are laid out, and a rotation always resizes.
  //
  // Both classes are opt-IN, so the default is unpinned (ADR-0039/R2): a
  // gutter whose room cannot be measured must not be left covering the
  // board. The page draws its board from script, so there is no state in
  // which the classes are absent and a board is on screen.
  const CELLS_BESIDE = 2;
  function keepCluesInView() {
    // The stage's cap follows the REAL toolbar. Where the stage starts, in
    // page coordinates, is the whole chrome above it -- heading, however many
    // rows the toolbar wrapped to, margins -- so it is measured, not allowed
    // for. Written first, because every figure below is read off the stage
    // this resizes.
    stage.style.setProperty(
      "--player-above-h",
      `${stage.getBoundingClientRect().top + window.scrollY}px`,
    );
    const board = stage.querySelector(".player-board");
    const rowClue = stage.querySelector("th.player-clue.is-row");
    const colClue = stage.querySelector("th.player-clue.is-col");
    const cell = stage.querySelector("td.player-cell");
    if (!board || !rowClue || !colClue || !cell) return;
    const { width, height } = cell.getBoundingClientRect();
    // A comparison and not Math.min on purpose: this is a viewport clip, not
    // a zoom bound, and tests/test_public_player_zoom.py keeps Math.min out of
    // this file wholesale so that a clamp can never be spelled here.
    const onScreen =
      window.innerHeight - (stage.getBoundingClientRect().top + stage.clientTop + window.scrollY);
    const visibleHeight = onScreen < stage.clientHeight ? onScreen : stage.clientHeight;
    board.classList.toggle(
      "keeps-rows",
      stage.clientWidth - rowClue.getBoundingClientRect().width >= CELLS_BESIDE * width,
    );
    board.classList.toggle(
      "keeps-cols",
      visibleHeight - colClue.getBoundingClientRect().height >= CELLS_BESIDE * height,
    );
  }

  // The zoom the two pointers' current separation asks for, anchored on their
  // midpoint in the stage's own box.
  function pinchMove() {
    const first = touchPoints.get(pinch.firstId);
    const second = touchPoints.get(pinch.secondId);
    const box = stage.getBoundingClientRect();
    applyZoom(
      pinchZoom(pinch.startZoom, pinch.startDistance, distanceBetween(first, second)),
      (first.x + second.x) / 2 - box.left,
      (first.y + second.y) / 2 - box.top,
    );
  }

  // Whether `event` is one of the running pinch's two pointers.
  const inPinch = (event) =>
    pinch !== null && (event.pointerId === pinch.firstId || event.pointerId === pinch.secondId);

  // A touch/pen pointer leaving the page, by lift or by cancel: forget it,
  // and end the pinch it belonged to with nothing committed. Returns whether
  // the caller should stop — the pinch's pointers never fall through to the
  // single-pointer paths below.
  function releaseTouch(event) {
    if (!touchPoints.has(event.pointerId)) return false;
    touchPoints.delete(event.pointerId);
    touchStartCell.delete(event.pointerId);
    if (!inPinch(event)) return false;
    pinch = null;
    return true;
  }

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
    // The pinch bookkeeping runs AHEAD of the single-pointer logic below and
    // independently of it, for touch and pen pointers only — a mouse never
    // reaches it. It has to come first: `if (gesture) return` on the next
    // line would otherwise swallow a second finger's pointerdown whole, and
    // the pinch would never be recognised.
    if (event.pointerType === "touch" || event.pointerType === "pen") {
      if (pinch) return; // a third pointer while a pinch runs: ignored
      const cell = cellUnder(event.clientX, event.clientY);
      touchPoints.set(event.pointerId, { x: event.clientX, y: event.clientY });
      touchStartCell.set(event.pointerId, cell);
      if (touchPoints.size === 2) {
        // The second finger. It is the BOARD's pinch only when the first one
        // went down on a board cell; two fingers starting on a clue box or
        // off the board are left to the browser entirely — no
        // preventDefault, no capture — exactly as the admin leaves them.
        // Either way this pointer never starts a gesture of its own.
        const [firstId] = touchPoints.keys();
        if (touchStartCell.get(firstId) !== null) {
          event.preventDefault();
          beginPinch(firstId, event.pointerId);
        }
        return;
      }
    }
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
    if (touchPoints.has(event.pointerId)) {
      touchPoints.set(event.pointerId, { x: event.clientX, y: event.clientY });
    }
    if (inPinch(event)) {
      event.preventDefault();
      pinchMove();
      return;
    }
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
    if (releaseTouch(event)) return;
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
    if (releaseTouch(event)) return;
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

  // The anchor for a button press is the centre of the stage's own visible
  // box, so the cell the player is looking at stays under their eye. A press
  // at either end of the range is a no-op, because stepZoom clamps — no
  // separate guard is needed beyond the aria-disabled the readout syncs.
  zoomOut.addEventListener("click", () => {
    applyZoom(stepZoom(zoom, "out"), stage.clientWidth / 2, stage.clientHeight / 2);
  });
  zoomIn.addEventListener("click", () => {
    applyZoom(stepZoom(zoom, "in"), stage.clientWidth / 2, stage.clientHeight / 2);
  });

  document.addEventListener("keydown", (event) => {
    if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "z") return;
    event.preventDefault();
    commit(event.shiftKey ? redo(history) : undo(history));
  });

  window.addEventListener("resize", keepCluesInView);
  // The toolbar can change height with no resize: the Solved banner wrapping
  // onto a new row, a late font changing a label's width. The stage's cap
  // follows the toolbar, so the toolbar's own size is observed as well.
  new ResizeObserver(keepCluesInView).observe(controls, { box: "border-box" });

  // The crosshair (CARD-325): DOM only, on the stage; see wireCrosshair.
  wireCrosshair(stage);

  controls.hidden = false;
  hint.hidden = false;
  syncZoom();
  // After the toolbar is revealed, because the stage's own box is what the
  // gutters are measured against and the toolbar is above it.
  keepCluesInView();
  refresh();

  window.publicPlayer = Object.freeze({
    payload,
    getBoard: () => shown,
    getHistory: () => history,
    isSolved: () => isClueSolved(history.board, payload.rows, payload.columns),
    getTool: () => tool,
    isRegion: () => region,
    getZoom: () => zoom,
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
