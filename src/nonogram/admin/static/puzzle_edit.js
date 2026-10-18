// The manual puzzle editor — Save, the difficulty message, Cancel, Approve
// (CARD-246; the server half it talks to is CARD-245).
//
// NOT a renderer. There is exactly one grid renderer in this panel,
// static/solver.js, and this file never draws a cell: it reads the board
// through window.puzzlePlayer (which solver.js sets, in edit mode, from the
// stored grid — see EDIT MODE in solver.js), turns it into an answer with
// solver_state.js answerOfBoard, and talks to the two routes CARD-245 added.
// Plain JavaScript, no framework, no build step (ADR-0038/R1).
//
// THE OWNER'S FLOW, which is two phases because they asked to SEE the
// difficulty before committing:
//   Save      answerOfBoard(the board) -> POST /puzzle/<id>/edit/verify
//             with {"grid": ...}. Nothing is stored by that route; what comes
//             back is one solve's grade, and it goes on screen with Approve
//             and Cancel beside it.
//   Approve   POST /puzzle/<id>/edit with THE SAME GRID. The store commits
//             only the grid whose grade was shown for this puzzle, and the
//             grade it shows is the one that proof carries, so an approval
//             can never store a difficulty nobody saw.
//   Cancel    puts the message and the two buttons away and changes nothing
//             — not on the server, and not on the board: the edit is still
//             there to go on with (AC-4).
//
// THE INVARIANT, and what it rests on (review cycle 1, F-001..F-005). This
// page must never offer Approve for a grid other than the one whose grade is
// on screen, and must never state a store state it has not been told. Four
// mechanisms carry that, and each is pinned by a test of its own in
// tests/test_puzzle_editor_ui.py:
//   1. tell(text, offer) is the ONLY writer of the message line and of the
//      Approve offer. The offer is an argument of the sentence that
//      describes it, so "a refusal standing beside a live Approve" is not a
//      state this file can be in — there is no path that writes one without
//      the other. (It used to take two paired calls, and the refusal branch
//      made only one of them.)
//   2. `turn`. Every request is asked in a turn, and the turn advances on
//      each new request AND on every recorded board change. An answer from a
//      spent turn is DROPPED rather than told, so a grade can never appear
//      for a grid that is no longer on the board.
//   3. One request at a time: each handler refuses to start a second while
//      one is in flight, and both buttons say so (aria-disabled). Two
//      answers can therefore never race to write the message, and a double
//      click is one request — rather than two that only happen to be
//      harmless because CARD-245 does not consume a verification.
//   4. The board announces its own changes (solver.js BOARD_CHANGE, from the
//      one place a change is recorded). Approve sends the grid captured when
//      Save was pressed and never re-reads the board; a stroke in between
//      therefore withdraws the offer and says so, instead of being quietly
//      left out of a store the page then calls saved.
// The store's answer is the one thing that is never dropped: it is the only
// report of what the store actually did. When it cannot be had at all, the
// page says that whether the grid was stored is not known here — never that
// it was saved, and never nothing.
//
// WHAT THIS FILE NEVER DECIDES (G-3). Whether a grid is a puzzle, and how
// hard it is, are the server's answers from one solve (ADR-0029/R2), and
// every refusal shown below is the server's own message relayed with a
// sentence about what to do next. There is no uniqueness check, no clue
// re-derivation and no difficulty arithmetic here, and the score and tier on
// screen are read out of the response — fabricate a grade in a route stub
// and this page shows the fabrication, which is the test that says so
// (tests/test_puzzle_editor_ui.py, G-3).
//
// THE ONE THING IT DOES DECIDE is whether the board describes an answer at
// all, which is not a question about the puzzle but about this page's own
// board: an answer is list[list[bool]] (ADR-0012), so a cell left undecided
// or "?" has no value to send. answerOfBoard hands back no grid for such a
// board (solver_state.js), and Save then NAMES the cells and sends nothing
// — CARD-246 AC-6's chosen rule. The two brushes that paint those states are
// also left out of the editor's menu, but that is a narrowing of the tools,
// never the guarantee: a repeat click's third step is "blank" for both
// remaining brushes and a confirmed Reset blanks the whole board, so an
// undecided cell is still reachable with Black and White alone.
//
// WHY A REFUSAL WAS A REFUSAL comes off the wire as a `reason`, not out of
// the server's prose (F-005). The two 409s look alike and need opposite
// words: a verification the store has forgotten costs one re-verify and no
// work ("press Save again"), while a book built on the puzzle means this
// edit cannot be stored at all — and telling that owner to press Save again
// is an instruction that can never succeed. The sentence the server sends is
// still shown; the reason only chooses what this page adds to it.
//
// EDIT NOT VERIFIED (409, reason "not_verified"). The store remembers a
// bounded number of recent verifications, so "the grid moved since you
// verified it" — and "it was verified so long ago the proof is gone" — are
// the same, ordinary answer: the save is refused, nothing is stored, and the
// owner is asked to press Save again. It is reported as the normal step it
// is, not as an error.

import { answerOfBoard } from "./solver_state.js";
// One spelling of the event name, shared with the renderer that dispatches
// it (solver.js BOARD CHANGE). An import rather than a second string
// literal: two halves of a seam written out twice is how the seam breaks.
import { BOARD_CHANGE } from "./solver.js";

// How many undecided cells are named one by one before the message says
// "and N more". Long enough to be actionable on a board the owner can still
// see, short enough that the live region stays readable.
const MAX_NAMED_CELLS = 6;

// Rows and columns are 1-based on screen: the owner is counting cells on a
// board, not indexing an array.
function cellName(cell) {
  return `row ${cell[0] + 1}, column ${cell[1] + 1}`;
}

function namedCells(cells) {
  const named = cells.slice(0, MAX_NAMED_CELLS).map(cellName).join("; ");
  const rest = cells.length - MAX_NAMED_CELLS;
  return rest > 0 ? `${named}; and ${rest} more` : named;
}

export function undecidedText(cells) {
  const count = cells.length === 1 ? "1 cell is" : `${cells.length} cells are`;
  return `Not saved: ${count} still undecided (${namedCells(cells)}). `
    + "Every cell of a stored puzzle is black or white, so give those cells "
    + "one or the other and press Save again.";
}

export function gradeText(grade) {
  return `This grid is a puzzle. Difficulty: ${grade.difficulty_tier}, `
    + `score ${grade.difficulty_score} of 100. `
    + "Approve to store it, or Cancel to go on editing.";
}

// What the store says it stored, in the store's own numbers (the row it
// wrote, out of the save's response). The page shows no difficulty of its
// own any more: the header badge it used to point at ("the difficulty shown
// above") was the PRE-EDIT tier and stayed that way (F-008).
export function storedText(stored) {
  const graded = stored && stored.difficulty_tier
    ? ` Difficulty: ${stored.difficulty_tier}, score ${stored.difficulty_score} of 100.`
    : "";
  return `Saved: the grid you verified is the stored puzzle now.${graded} `
    + "Your board is untouched — go on editing and press Save again to "
    + "change it further.";
}

// The board stopped being the grid whose grade is on screen (or the grid
// that was being checked), so there is nothing to approve and nothing was
// stored. Said as soon as the stroke lands, rather than left for the owner
// to discover after an Approve that did not include it.
export const BOARD_MOVED =
  "The board has changed, so there is nothing checked to approve and "
  + "nothing was stored. Press Save to check the grid that is on the board now.";

export const CANCELLED =
  "Not saved, and nothing on the board was lost: your edit is still there. "
  + "Press Save when you want it checked again.";

// A refusal the owner can act on, from the server's own message and its
// `reason` (AC-5: words, never an exception). CARD-245's reasons are
// "not_unique" (422), "not_verified" and "in_a_book" (both 409) and
// "not_found" (404); the codes are kept as the fallback so an answer without
// a reason still reads as words. `code: 0` is this page's own value for "no
// answer at all" — see post() — and on a save it is the one outcome where
// the store's state is NOT known here.
export function refusalText(code, message, reason, { storing = false } = {}) {
  const said = message ? ` ${message}.` : "";
  if (code === 0) {
    return storing
      ? "The panel could not be reached while this grid was being stored, so "
        + "whether it was stored is not known here. Reload the page to see the "
        + "stored puzzle, and press Save again if your edit is not in it."
      : "Nothing was checked and nothing was stored: the panel could not be "
        + "reached. Press Save to try again.";
  }
  if (reason === "in_a_book") {
    return `This edit cannot be stored.${said} A puzzle in a book keeps the `
      + "grid the book was made from, so take it out of the book if its grid "
      + "has to change. Nothing was stored.";
  }
  if (reason === "not_verified") {
    return `Nothing was stored.${said} Press Save to check this grid again.`;
  }
  if (reason === "not_unique" || code === 422) {
    return `This grid cannot be saved and nothing was stored.${said} `
      + "A stored puzzle has exactly one solution: change the grid and press Save again.";
  }
  if (reason === "not_found" || code === 404) {
    return `Nothing was stored.${said} This puzzle is no longer in the panel.`;
  }
  if (code === 409) {
    // A conflict with no reason on it: the advice that is right for the
    // common one, and no claim about which conflict it was.
    return `Nothing was stored.${said} Press Save to check this grid again.`;
  }
  return `Nothing was stored.${said} The panel answered with ${code}, which `
    + "this page does not know how to act on — press Save to try again.";
}

async function post(path, grid) {
  let response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ grid }),
    });
  } catch {
    // No answer at all: a dropped connection, a panel that stopped, a
    // network that went away. Unwrapped, this rejected out of the handler
    // and left "Checking this grid..." on screen with an uncaught error in
    // the console and no word to the owner (F-003). `code: 0` is not a
    // refusal — on a save it means nobody here knows what the store did.
    return { code: 0, body: null };
  }
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null; // a response that is not JSON says nothing beyond its code
  }
  return { code: response.status, body };
}

function start() {
  const box = document.getElementById("puzzle-editor");
  // No board, no Save: solver.js sets window.puzzlePlayer only once it has
  // drawn one, so a page whose payload it refused shows no editor controls
  // rather than a Save button over an alert — the discipline the toolbar
  // and the usage hint already follow.
  if (!box || !window.puzzlePlayer) return;
  const player = window.puzzlePlayer;
  const puzzleId = box.dataset.editorPuzzle;
  const save = document.getElementById("puzzle-editor-save");
  const decide = document.getElementById("puzzle-editor-decide");
  const approve = document.getElementById("puzzle-editor-approve");
  const cancel = document.getElementById("puzzle-editor-cancel");
  const message = document.getElementById("puzzle-editor-message");

  // The grid whose grade is on screen, or null when there is nothing to
  // approve. Approve sends THIS value and never re-reads the board: the grid
  // that was graded is the grid that gets stored, and a board that moves in
  // between takes the offer away (onBoardChange) rather than quietly
  // sending one grid while the owner reads about another.
  let verified = null;
  // Which turn the page is in (invariant 2 above). Advanced by every request
  // and by every recorded board change; an answer that comes back into a
  // later turn is about a grid that is no longer on the board.
  let turn = 0;
  // "verify", "approve", or null — what is in flight (invariant 3).
  let inFlight = null;

  // THE ONE WRITER of the message line and of the Approve offer (invariant
  // 1). `offer` is the grid Approve would send, or null for "nothing to
  // approve": every sentence this page shows states its own offer, so no
  // sentence can leave the previous one's Approve standing beside it.
  function tell(text, offer = null) {
    verified = offer;
    decide.hidden = offer === null;
    message.textContent = text;
  }

  // aria-disabled, not `disabled`: the owner may be standing on the button
  // from the keyboard, and `disabled` drops the focus to the document
  // mid-flow (G-4, CARD-211's pattern). What PREVENTS a second request is
  // the guard at the top of each handler; this is how the state is said.
  function inFlightIs(what) {
    inFlight = what;
    const busy = String(what !== null);
    save.setAttribute("aria-disabled", busy);
    approve.setAttribute("aria-disabled", busy);
  }

  async function onSave() {
    if (inFlight !== null) return; // one request at a time; the button says so
    const answer = answerOfBoard(player.getBoard());
    if (answer.grid === null) {
      // Nothing is sent: an undecided cell has no boolean to send, and
      // picking one for the owner is the defect (see THE ONE THING above).
      tell(undecidedText(answer.undecided));
      return;
    }
    const mine = (turn += 1);
    inFlightIs("verify");
    tell("Checking this grid...");
    let answered;
    try {
      answered = await post(
        `/puzzle/${encodeURIComponent(puzzleId)}/edit/verify`, answer.grid);
    } finally {
      inFlightIs(null);
    }
    // The board moved while this grid was being checked: this grade is about
    // a grid that is not on the board, so it is dropped. onBoardChange has
    // already told the owner what happened.
    if (mine !== turn) return;
    const { code, body } = answered;
    if (code !== 200 || !body || body.ok !== true) {
      tell(refusalText(code, body && body.message, body && body.reason));
      return;
    }
    tell(gradeText(body.grade), answer.grid);
    approve.focus();
  }

  async function onApprove() {
    if (inFlight !== null || verified === null) return;
    // The grid that was graded, captured when Save was pressed. The board is
    // NOT read here; see invariant 4.
    const grid = verified;
    turn += 1;
    inFlightIs("approve");
    // The offer goes away with this sentence: the store is being written, so
    // there is nothing left to approve, and a second Approve cannot be sent.
    tell("Storing this grid...");
    let answered;
    try {
      answered = await post(`/puzzle/${encodeURIComponent(puzzleId)}/edit`, grid);
    } finally {
      inFlightIs(null);
    }
    // Never dropped, whatever turn it comes back into: this answer is the
    // only report of what the store did, and the page may not go quiet about
    // it. It speaks of "the grid you verified" and not of "this grid",
    // because the board is free to have moved since.
    const { code, body } = answered;
    if (code !== 200 || !body || body.ok !== true) {
      tell(refusalText(code, body && body.message, body && body.reason, { storing: true }));
    } else {
      tell(storedText(body.puzzle));
    }
    save.focus();
  }

  function onCancel() {
    tell(CANCELLED);
    save.focus();
  }

  // The board stopped being the grid this page has been talking about
  // (solver.js dispatches this from the one place a change is recorded).
  function onBoardChange() {
    // Whatever is in flight is now about an old grid.
    turn += 1;
    // An approval is already on its way with the grid it captured, and its
    // answer is what the owner must read — a stroke does not get to speak
    // over the store.
    if (inFlight === "approve") return;
    // Nothing was claimed, so there is nothing to correct: ordinary painting
    // does not write to the live region.
    if (verified === null && inFlight === null) return;
    tell(BOARD_MOVED);
  }

  save.addEventListener("click", onSave);
  approve.addEventListener("click", onApprove);
  cancel.addEventListener("click", onCancel);
  document.addEventListener(BOARD_CHANGE, onBoardChange);
  box.hidden = false;
}

start();
