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
// EDIT NOT VERIFIED (409). The store remembers a bounded number of recent
// verifications, so "the grid moved since you verified it" — and "it was
// verified so long ago the proof is gone" — are the same, ordinary answer:
// the save is refused, nothing is stored, and the owner is asked to press
// Save again, which costs one solve and no work. It is reported as the
// normal step it is, not as an error.

import { answerOfBoard } from "./solver_state.js";

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

// A refusal the owner can act on, from the status code and the server's own
// message (AC-5: words, never an exception). The codes are CARD-245's:
// 422 a grid that may not be stored, 409 a conflict (not verified, or a book
// holds the puzzle), 404 the puzzle is gone.
export function refusalText(code, message) {
  const said = message ? ` ${message}.` : "";
  if (code === 422) {
    return `This grid cannot be saved and nothing was stored.${said} `
      + "A stored puzzle has exactly one solution: change the grid and press Save again.";
  }
  if (code === 409) {
    return `Nothing was stored.${said} `
      + "Press Save to check this grid again.";
  }
  if (code === 404) {
    return `Nothing was stored.${said} This puzzle is no longer in the panel.`;
  }
  return `Nothing was stored.${said} The panel could not be reached — try Save again.`;
}

async function post(path, grid) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ grid }),
  });
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
  // that was graded is the grid that gets stored, and if the owner painted
  // on in between, the store refuses it (409) rather than storing a grade
  // nobody saw.
  let verified = null;

  function say(text) {
    message.textContent = text;
  }

  // Put the two buttons away. Always paired with a new message, so the
  // reader is never left with "Approve" gone and no word about why.
  function withdraw() {
    verified = null;
    decide.hidden = true;
  }

  async function onSave() {
    withdraw();
    const answer = answerOfBoard(player.getBoard());
    if (answer.grid === null) {
      // Nothing is sent: an undecided cell has no boolean to send, and
      // picking one for the owner is the defect (see THE ONE THING above).
      say(undecidedText(answer.undecided));
      return;
    }
    say("Checking this grid...");
    const { code, body } = await post(
      `/puzzle/${encodeURIComponent(puzzleId)}/edit/verify`, answer.grid);
    if (code !== 200 || !body || body.ok !== true) {
      say(refusalText(code, body && body.message));
      return;
    }
    verified = answer.grid;
    say(gradeText(body.grade));
    decide.hidden = false;
    approve.focus();
  }

  async function onApprove() {
    if (verified === null) return;
    const grid = verified;
    const { code, body } = await post(`/puzzle/${encodeURIComponent(puzzleId)}/edit`, grid);
    withdraw();
    if (code !== 200 || !body || body.ok !== true) {
      say(refusalText(code, body && body.message));
    } else {
      say("Saved. This grid is the stored puzzle now, with the difficulty shown above. "
        + "Go on editing and press Save again to change it further.");
    }
    save.focus();
  }

  function onCancel() {
    withdraw();
    say("Not saved, and nothing on the board was lost: your edit is still there. "
      + "Press Save when you want it checked again.");
    save.focus();
  }

  save.addEventListener("click", onSave);
  approve.addEventListener("click", onApprove);
  cancel.addEventListener("click", onCancel);
  box.hidden = false;
}

start();
