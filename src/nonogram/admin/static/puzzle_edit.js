// The manual puzzle editor — Save, Cancel, the difficulty message, Approve,
// Back to edit (CARD-246; the server half it talks to is CARD-245; the two
// exits, the rename and the coloured tier are CARD-250).
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
//   Save         answerOfBoard(the board) -> POST /puzzle/<id>/edit/verify
//                with {"grid": ...}. Nothing is stored by that route; what
//                comes back is one solve's grade, and it goes on screen with
//                Approve and Back to edit beside it.
//   Approve      POST /puzzle/<id>/edit with THE SAME GRID. The store commits
//                only the grid whose grade was shown for this puzzle, and the
//                grade it shows is the one that proof carries, so an approval
//                can never store a difficulty nobody saw. The store's answer
//                is told — it is never dropped — and then the editor is LEFT
//                for the puzzle list, where the row's picture is the grid
//                just stored (CARD-250 AC-5/AC-6). It is NOT left when a
//                stroke landed while the store was writing: that stroke is
//                unstored work which lives only on this board, so the page
//                stays and says so, by the same rule Cancel follows — only
//                leave when there is nothing to lose (review cycle 1, F-001).
//   Back to edit puts the message and the two buttons away and changes
//                nothing — not on the server, and not on the board: the edit
//                is still there to go on with (CARD-246 AC-4). This button was
//                labelled Cancel until CARD-250 renamed it to what it does;
//                the behaviour is unchanged, which is why CARD-246's test for
//                it needed only a rename.
//   Cancel       leaves the editor for the puzzle list and stores nothing. It
//                asks first ONLY when there is something to lose — a board
//                that has changed since it was opened, which this file hears
//                from solver.js's BOARD_CHANGE and from nowhere else. A
//                confirm on every exit trains the owner to dismiss it; no
//                confirm at all loses work to a mis-click. It asks in the
//                page (role="alertdialog", never window.confirm), as Clear
//                does.
//
// NEITHER EXIT CAN OUTRUN THE STORE (CARD-250 AC-7). Cancel is refused while
// a request is in flight, for the same reason a second Save is: landing on
// the list while the store is still deciding would leave the save's answer —
// the only report of what the store did — with nobody left to hear it. It is
// refused in words AND with aria-disabled, which is MORE than a second Save
// gets (that one returns silently and says so through aria-disabled alone),
// because an exit is the press whose refusal is most likely to read as a dead
// button.
//
// Back to edit is not an exit from the page, so it has nothing to OUTRUN —
// but since review cycle 2's F-002 it is not "refused by nothing" either, and
// what it does mid-flight (which only a script can do, the pair being hidden)
// depends on WHICH request is in flight. Two windows, two behaviours:
//   during a verify   it does what it always did, spending the turn and
//                     saying the edit is still there — CARD-246's behaviour,
//                     and the verify window is now the only window in which
//                     that behaviour exists. Asserted unchanged by
//                     test_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer,
//                     so this file does not get to quietly change it either.
//   during an approve it is IGNORED IN SILENCE: the guard at the top of
//                     onBackToEdit returns before the turn is spent, so the
//                     exit predicate keeps one meaning ("the board moved")
//                     and the page states no fact it was not told. Pinned by
//                     test_a_back_to_edit_forced_while_the_store_writes_does_not_stop_the_exit.
// The silence is the mechanism, not an omission. `back` deliberately carries
// no aria-disabled (see inFlightIs) and for the whole write it sits inside a
// display:none container, so an attribute there would speak to nobody; and a
// sentence about a press that did nothing would speak OVER the store's
// answer, the one sentence the owner must read. AC-7 is written per button on
// the card for exactly this reason (amended, review cycle 3).
//
// THE TIER WORD WEARS ITS TIER'S COLOUR (CARD-250 item 4), and the colour
// rules are NOT here. meta/design/tokens.css declares --color-tier-*, and
// templates/_tier.html is their single documented exception to the
// no-colour-literals rule — an exception that exists because five copies of
// one badge expression drifted into two defects at once (CARD-076). A
// tier->hue map in this file would be a sixth copy, in a language that macro
// cannot reach. So the server's own tier string reaches the DOM as a data
// attribute and static/admin.css colours it from those tokens: this file
// names no colour and maps no tier to one. The span that carries it is the
// TEMPLATE'S (#puzzle-editor-grade) — tell() fills it and puts it in the
// line — so nothing here creates an element, which is what keeps CARD-246
// G-2's "the editor ships no second grid renderer" the flat assertion it is
// (tests/test_puzzle_editor_ui.py's _BUILDS_A_GRID reads this file for any
// node-building at all).
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
//      made only one of them.) CARD-250 made its `text` either a string or
//      the PARTS of a sentence, one of which may be the tier word that wears
//      a colour; the parts are still written in that one call, so the
//      coloured word is not a second writer of the line.
//   2. `turn`. Every request is asked in a turn, and the turn advances on
//      each new request AND on every recorded board change. An answer from a
//      spent turn is DROPPED rather than told, so a grade can never appear
//      for a grid that is no longer on the board. A SAVE's answer is the one
//      exception — it is always told, being the only report of what the
//      store did — so for it the spent turn decides not whether to speak but
//      whether to LEAVE: a board that moved keeps the page (F-001).
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
// report of what the store actually did. And what that answer licenses the
// page to CLAIM is an allow-list, not a default (review cycle 2, G-001). On
// a save this page may say "nothing was stored" only for the answers
// CARD-245 gives WITHOUT writing: its four declared reasons, and the bare
// 404/409/422 those refusals arrive as. Every other answer to a save — no
// answer at all, a 2xx whose body will not parse, a 5xx from the panel or
// from the proxy in front of it, a reason this page has never been taught —
// leaves the store's state unknown here, and the page says exactly that and
// asks for a reload. The default used to run the other way, and the cost of
// that is not theoretical for a panel behind a gateway: a proxy that gives
// up AFTER the app committed answers 502, the owner read "Nothing was
// stored", and the owner's next act on that sentence is a second Save —
// another solve and another manually_edited_at stamp for a grid that was
// already in. Inverting the default also means the FIFTH refusal reason,
// whenever it is added, fails safe instead of lying.
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

// The grade's sentence, as the PARTS tell() writes in one go. The tier word
// is a part of its own, marked `{ tier }`, because it is the one word that
// wears a colour (item 4) — and it is marked rather than coloured here: what
// the colour IS lives in admin.css, from the tier tokens. Everything else is
// prose. The sentence names "Back to edit", which is the label the bar
// carries since CARD-250's rename; a message that named a button the bar does
// not have is what TestPuzzleEditor_TheWordsNameTheButtonsThatExist refuses.
export function gradeText(grade, book = null) {
  return [
    "This grid is a puzzle. Difficulty: ",
    { tier: grade.difficulty_tier },
    `, score ${grade.difficulty_score} of 100. `
      + bookNote(book)
      + "Approve to store it, or Back to edit to go on editing.",
  ];
}

// THE BOOK'S CLAUSE of the grade's sentence (CARD-251). A puzzle a book holds
// is editable now, so the grade's sentence has two more things to say and the
// verify is where both belong — the owner's own principle for the tier was
// "learn it at verify, with the grade".
//
//   1. WHICH BOOK, named. The confirmation that follows Approve is about this
//      book, and "Are you sure?" with no object is a dialog to click through.
//      The title comes off the wire; a book whose title could not be read is
//      named by its id AND SAID TO BE (`namedBook`), because the title is
//      presentation and the guard is the flag the server requires.
//   2. HOW MANY PAGES THE BOOK WOULD GAIN, and which puzzle this one shares
//      its page with (AC-9). A book page holds two puzzles only when both fit
//      at one shared cell (INV-010), and that fit is measured FROM THE CLUES
//      — so a repaint that keeps the tier and the extent can still deepen a
//      gutter past the point where the pair fits, split the page in two and
//      move every folio after it. It is a WARNING and not a refusal (owner,
//      2026-10-19): Approve stays beside it and an approved edit stores,
//      because refusing would block any repaint that deepens a paired
//      puzzle's clues, which is most real edits.
//
// The regrade is the one thing this clause never has to word, because it
// never arrives as a grade: it is refused at the verify (AC-4), so what the
// page gets for it is a refusal and `refusalText` words it.
//
// `null` for a puzzle no book holds, and the empty string then adds nothing
// to the sentence — which is also what the corpus that calls `gradeText`
// with one argument gets.
export function bookNote(book) {
  if (!book) return "";
  const named = namedBook(book);
  const pages = book.pages || {};
  if (pages.known !== true) {
    return `This puzzle is in ${named}, and whether this grid would change `
      + "that book's page count could not be measured here. ";
  }
  if (pages.changes !== true) {
    return `This puzzle is in ${named}. `;
  }
  const shared = pages.partner
    ? `, which it shares with ${pages.partner},`
    : "";
  return `This puzzle is in ${named}, and this grid would make that book `
    + `${pageCountChange(pages.added)}: how deep its clues are decides `
    + `whether the page it is on${shared} holds two puzzles or one. The book `
    + "stays valid. ";
}

// THE BOOK, AS A SENTENCE NAMES IT. A title when there is one; otherwise the
// id, said to BE an id and said to be standing in for a title that could not
// be read (review cycle 1, F-002, and failure matrix F-4, which declares
// exactly that and was half-refuted by a page that printed the bare uuid
// where the title goes — the owner read "This puzzle is in the book
// 3f2a1b0c-…" and had no way to tell a missing title from a book literally
// called that).
//
// A book with no readable title is still a book the edit must be confirmed
// for: the title is presentation and the guard is the server's flag
// (`_book_holding` in app.py sends `title: null` for a `book_id` that
// resolves to no book, and the store refuses the unconfirmed save either
// way). The id is printed in full rather than shortened — it is what the
// owner would have to quote to find the row.
function namedBook(book) {
  if (book.title) return `the book ${book.title}`;
  return `a book whose title could not be read (id ${book.id})`;
}

// HOW MUCH LONGER, in the words the measured number supports and no wider
// (review cycle 1, F-001/F-004). The server answers `added`, a count of
// pages, which may be more than one and may be NEGATIVE — a replacement
// whose clues are shallower can let a pair fit that does not fit today, and
// the book then gets SHORTER. The old sentence quoted the delta's two
// absolute figures and then asserted "gets one page longer" beside them,
// neither of which the measurement constrained.
function pageCountChange(added) {
  const count = Math.abs(added);
  const pages = count === 1 ? "one page" : `${count} pages`;
  return `${pages} ${added < 0 ? "shorter" : "longer"}`;
}

// THE QUESTION, when the store has answered `needs_confirmation` (AC-2/G-1).
// The server refused an unconfirmed save, wrote nothing and sent back the
// book, so this is the sentence that turns that answer into a question — and
// it is `tell` that writes it, like every other sentence on this bar (G-7).
// The in-page alertdialog beside it carries only its two answers.
//
// A PUBLISHED book is said to be published. The flag is the same one either
// way; what differs is that for a published book this is INV-008's own
// confirmation — the one the panel has required for a published book's
// membership since CARD-131 — and an owner deciding whether to repaint a
// puzzle that is already on sale needs to know which case they are in
// (Trap 1: `in_a_book()` cannot tell the two apart, so the question has to).
export function needsConfirmationText(book) {
  const named = book ? namedBook(book) : "a book";
  const published = book && book.published
    ? ", and that book is published"
    : "";
  return `Nothing is stored yet. This puzzle is in ${named}`
    + `${published}: the grid you verified would replace the grid that book `
    + "prints. Answer the question below to store it or to leave the stored "
    + "grid as it is.";
}

// What the page says when the owner answers "no". Nothing was stored, and
// nothing on the board was lost either — the same promise Back to edit makes,
// which is why it reads like its sentence.
export const BOOK_KEPT =
  "Not stored: the book keeps the grid it had, and your edit is still on the "
  + "board. Press Save when you want it checked again.";

// What the store says it stored, in the store's own numbers (the row it
// wrote, out of the save's response). The page shows no difficulty of its
// own any more: the header badge it used to point at ("the difficulty shown
// above") was the PRE-EDIT tier and stayed that way (F-008).
//
// The head is the store's answer and is the same on both branches; the TAIL
// says what the page does next, and that is two different things (review
// cycle 1, F-001). Approve leaves for the list — unless a stroke landed
// while the store was writing, in which case the page stays, because leaving
// would take that stroke with it. One sentence per branch, so neither claims
// the other's act; both are still written by the one `tell`.
function storedHead(stored) {
  const graded = stored && stored.difficulty_tier
    ? ` Difficulty: ${stored.difficulty_tier}, score ${stored.difficulty_score} of 100.`
    : "";
  return `Saved: the grid you verified is the stored puzzle now.${graded} `;
}

export function storedText(stored) {
  return storedHead(stored)
    + "Showing the puzzle list, where this puzzle's picture is the grid that "
    + "was just stored.";
}

// The same store, and a board that moved while it was being written. The
// editor stays open and says so: the strokes made since are unstored work,
// and the page that holds them is the only place they exist.
export function storedAndStayingText(stored) {
  return storedHead(stored)
    + "You changed the board while it was being stored, so the editor stays "
    + "open: those strokes are still on the board and are not stored. Press "
    + "Save to check the board as it is now.";
}

// The board stopped being the grid whose grade is on screen (or the grid
// that was being checked), so there is nothing to approve and nothing was
// stored. Said as soon as the stroke lands, rather than left for the owner
// to discover after an Approve that did not include it.
export const BOARD_MOVED =
  "The board has changed, so there is nothing checked to approve and "
  + "nothing was stored. Press Save to check the grid that is on the board now.";

// What Back to edit says. Called CANCELLED until CARD-250, when the button
// it belongs to stopped being called Cancel: the words are unchanged (they
// never named the button), the name is, so that the constant and the control
// go on meaning the same thing.
export const BACK_TO_EDIT =
  "Not saved, and nothing on the board was lost: your edit is still there. "
  + "Press Save when you want it checked again.";

// Why an exit was refused (AC-7). Said rather than left to the aria-disabled
// alone, because a press that does nothing and says nothing reads as a dead
// button. Neither sentence names a control.
export function inFlightText(what) {
  return what === "approve"
    ? "Still storing this grid, so the editor stays open: the store's answer "
      + "is the only report of what it did, and it is about to be shown here."
    : "Still checking this grid, so the editor stays open. The answer is "
      + "about to be shown here.";
}

// THE REFUSALS THAT NEVER WRITE — the allow-list THE INVARIANT's last
// paragraph rests on. Each of these is a decision CARD-245's two routes take
// before they touch the store, which is what makes "nothing was stored" a
// fact about them rather than a guess. The vocabulary is the server's own
// (app.py EDIT_REFUSAL_REASONS) and a test reads both sides off the source
// and holds them to that tuple, so the two cannot drift; a fifth reason
// added to the routes has to be looked at here, and until it is, the page
// does not know what the store did and says so.
// CARD-251 adds the fifth, sixth and seventh, and each is a CLAIM that that
// answer never writes. The claim is made true at the route — the store
// decides all three before it touches a row, the confirmation before it even
// solves — and it is proved by driving each one through the real route and
// reading the row back afterwards
// (`TestBookedEdit_TheFifthReasonIsTrueNotListed`), rather than by adding a
// string here and trusting it. That is the whole of what this inversion was
// for.
const REFUSALS_THAT_NEVER_WRITE = [
  "not_unique",
  "not_verified",
  "in_a_book",
  "not_found",
  "needs_confirmation",
  "regrade_in_a_book",
  "extent_changed",
  // CARD-291: a branching replacement onto an approved or in-book puzzle.
  // The store raises before it writes, so nothing was stored.
  "needs_guessing",
];
// The same refusals arriving with no reason on them — the codes CARD-245
// gives them. `code: 0` (this page's own value for "no answer at all", see
// post()) is deliberately not among them: no answer is no knowledge.
const CODES_THAT_NEVER_WRITE = [404, 409, 422];

// Can this page say what the store did? A reason it recognises answers for
// itself; a bare code falls back to the codes those refusals use; anything
// else — a code with a foreign reason, a 5xx, an answer that would not parse
// — is unknown. The default is "no", which is the whole of the fix.
export function storeStateIsKnown(code, reason) {
  return reason
    ? REFUSALS_THAT_NEVER_WRITE.includes(reason)
    : CODES_THAT_NEVER_WRITE.includes(code);
}

// A refusal the owner can act on, from the server's own message and its
// `reason` (AC-5: words, never an exception). CARD-245's reasons are
// "not_unique" (422), "not_verified" and "in_a_book" (both 409) and
// "not_found" (404); the codes are kept as the fallback so an answer without
// a reason still reads as words.
//
// `storing` says whose answer this is. On a VERIFY nothing is stored whatever
// comes back — that route writes nothing at all — so the definite sentence is
// always true there. On a SAVE it is true only for the answers above, and
// every other one gets the sentence that claims nothing.
export function refusalText(code, message, reason, { storing = false } = {}) {
  const said = message ? ` ${message}.` : "";
  if (storing && !storeStateIsKnown(code, reason)) {
    const how = code === 0
      ? "The panel could not be reached while this grid was being stored, so "
        + "whether it was stored is not known here."
      : `The panel answered the save with ${code}, which this page does not `
        + "know how to act on, so whether the grid was stored is not known "
        + "here.";
    return `${how}${said} Reload the page to see the stored puzzle, and press `
      + "Save again if your edit is not in it.";
  }
  if (code === 0) {
    return "Nothing was checked and nothing was stored: the panel could not be "
      + "reached. Press Save to try again.";
  }
  if (reason === "in_a_book") {
    return `This edit cannot be stored.${said} A puzzle in a book keeps the `
      + "grid the book was made from, so take it out of the book if its grid "
      + "has to change. Nothing was stored.";
  }
  if (reason === "needs_confirmation") {
    // Reached when this answer arrives outside the approve that asked for it
    // — the handler there turns it into the page's own question instead. It
    // claims "nothing was stored" because nothing was: the store decides the
    // confirmation before it solves, let alone writes.
    return `Nothing was stored.${said} Press Save to check this grid again `
      + "and answer the question about the book.";
  }
  if (reason === "regrade_in_a_book") {
    return `This edit cannot be stored.${said} A book's order is grouped by `
      + "difficulty level, so a puzzle in a book keeps its level: paint a grid "
      + "of the same difficulty, or take the puzzle out of the book. Nothing "
      + "was stored.";
  }
  if (reason === "extent_changed") {
    return `This grid is not the size of the stored puzzle, so nothing was `
      + `stored.${said} An edit repaints a puzzle; it never resizes one.`;
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

async function post(path, grid, confirmed = false) {
  let response;
  try {
    // `confirmed` travels in the body of the save, which is the request the
    // server refuses without it (CARD-251 G-1). It is sent only when it is
    // true, so an ordinary save's body is byte-for-byte the one CARD-245
    // documented, and the server reads it as `is True` — a confirmation is an
    // answer, not a truthy value.
    const body = confirmed ? { grid, confirmed: true } : { grid };
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
  const back = document.getElementById("puzzle-editor-back");
  const leave = document.getElementById("puzzle-editor-leave");
  const message = document.getElementById("puzzle-editor-message");
  // The one element the message line ever holds, carried by the template so
  // that nothing here builds a node (see THE TIER WORD above).
  const gradeWord = document.getElementById("puzzle-editor-grade");
  const confirmLeave = document.getElementById("puzzle-editor-leave-confirm");
  const leaveAnyway = document.getElementById("puzzle-editor-leave-accept");
  const keepEditing = document.getElementById("puzzle-editor-leave-keep");
  // The book's question (CARD-251): an alertdialog in the page, never
  // window.confirm — the rule Clear's and Cancel's questions already follow.
  const bookQuestion = document.getElementById("puzzle-editor-book-question");
  const editAnyway = document.getElementById("puzzle-editor-book-accept");
  const keepTheBook = document.getElementById("puzzle-editor-book-keep");

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
  // The grid the book's question is about: the verified grid an Approve
  // already sent once and the server refused for want of the confirmation.
  // Held apart from `verified` because `tell` takes the Approve offer away
  // with the question's own sentence — there is nothing to approve while a
  // question is open, and the answer to the question is what sends this.
  let awaitingTheBook = null;

  // Has the board changed since this page opened it? The board announces its
  // own changes from the ONE place a change is recorded (solver.js
  // BOARD_CHANGE), so this is a fact and not a guess — and it is the whole of
  // what decides whether Cancel asks first.
  let boardChanged = false;

  // THE ONE WRITER of the message line and of the Approve offer (invariant
  // 1). `offer` is the grid Approve would send, or null for "nothing to
  // approve": every sentence this page shows states its own offer, so no
  // sentence can leave the previous one's Approve standing beside it.
  //
  // `text` is a string, or the parts of one sentence — strings, and at most
  // one `{ tier }` marker for the word that wears its tier's colour. The
  // marker is filled into the template's own span and placed in the line
  // here, in this one call: the colour is never a second write. The server's
  // tier reaches the DOM through textContent and a data attribute, never
  // innerHTML (G-5), and what colour that attribute means is admin.css's.
  function tell(text, offer = null) {
    verified = offer;
    decide.hidden = offer === null;
    const line = [];
    for (const part of Array.isArray(text) ? text : [text]) {
      if (typeof part === "string") {
        line.push(document.createTextNode(part));
        continue;
      }
      gradeWord.textContent = part.tier;
      gradeWord.dataset.tier = String(part.tier).toLowerCase();
      line.push(gradeWord);
    }
    // One call, so the line is never half-written; message.textContent still
    // reads as the whole sentence, span and all.
    message.replaceChildren(...line);
  }

  // aria-disabled, not `disabled`: the owner may be standing on the button
  // from the keyboard, and `disabled` drops the focus to the document
  // mid-flow (CARD-246 G-4 / CARD-250 G-3, CARD-211's pattern). What PREVENTS a second request is
  // the guard at the top of each handler; this is how the state is said.
  //
  // Cancel joins Save and Approve here, because it is refused for the same
  // reason they are (AC-7). Back to edit does NOT: it is never told it is
  // busy. It is refused in exactly ONE window — the approve window, by
  // onBackToEdit's guard — and that refusal is silent on purpose: for the
  // whole write the button sits inside a display:none container, so an
  // attribute set here would say "busy" to nobody while making this file
  // claim a mechanism it has not got. In the verify window it is not refused
  // at all, so "busy" would be plainly false there (review cycle 3, F-001).
  function inFlightIs(what) {
    inFlight = what;
    const busy = String(what !== null);
    save.setAttribute("aria-disabled", busy);
    approve.setAttribute("aria-disabled", busy);
    leave.setAttribute("aria-disabled", busy);
  }

  // Both exits land here: the list the editor was reached from, redrawn by
  // the server, with this puzzle's row carrying the picture of the grid that
  // is stored now (CARD-250 item 2 — _puzzle_table.html versions the
  // thumbnail's URL by manually_edited_at, so a cache cannot answer with the
  // grid that was replaced).
  const THE_LIST = "/puzzles";

  function closeTheConfirm() {
    confirmLeave.hidden = true;
    leave.setAttribute("aria-expanded", "false");
    leave.focus();
  }

  // Put the book's question away and forget the grid it was about. The grid
  // is forgotten on purpose: the question is the only thing that can send it,
  // so a grid left behind a closed question would be an unapprovable offer
  // this page was still holding.
  function closeTheBookQuestion() {
    bookQuestion.hidden = true;
    awaitingTheBook = null;
  }

  async function onSave() {
    if (inFlight !== null) return; // one request at a time; the button says so
    // The board AS DISPLAYED, which during an uncommitted drag is that
    // drag's preview rather than a recorded board (review cycle 2, G-003;
    // solver.js BOARD CHANGE announces commit(), not show()). So a Save
    // taken mid-gesture — two pointers on a touch device — checks a grid the
    // editor was never told about. It is harmless as this file stands:
    // whatever is read here is the grid Approve sends, and the gesture's own
    // pointerup/cancel either commits the preview or reverts it, both of
    // which announce and so spend this turn and drop this answer. It is
    // written down because it is the one gap in "the board announces its own
    // changes", and the close, if it is ever wanted, is to read the recorded
    // board here instead of the displayed one.
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
    // `body.book` is absent for a puzzle no book holds, and the grade's
    // sentence then says nothing about books (CARD-251).
    tell(gradeText(body.grade, body.book), answer.grid);
    approve.focus();
  }

  async function onApprove() {
    if (inFlight !== null || verified === null) return;
    // The grid that was graded, captured when Save was pressed. The board is
    // NOT read here; see invariant 4. It is sent WITHOUT the book's
    // confirmation: that question is the server's, and this is the request it
    // answers (CARD-251 G-1).
    await store(verified, false);
  }

  // Send one grid to the store, with or without the book's confirmation.
  //
  // `onApprove` sends it the first time unconfirmed, because the question is
  // the SERVER's: for a puzzle a book holds the answer comes back
  // `needs_confirmation`, with nothing written and nothing even solved, and
  // the page turns that answer into its own question. "Edit it anyway" calls
  // this again with the same grid and the flag — a second request, which is
  // the point: a dialog that then posted an identical request would be no
  // implementation of this card.
  async function store(grid, confirmed) {
    // The turn is captured, not merely spent: a stroke that lands while the
    // store is writing advances it (onBoardChange, before its early return),
    // and that is how this handler learns there is unstored work on the
    // board by the time the answer comes back (review cycle 1, F-001).
    const mine = (turn += 1);
    inFlightIs("approve");
    // The offer goes away with this sentence: the store is being written, so
    // there is nothing left to approve, and a second Approve cannot be sent.
    tell("Storing this grid...");
    let answered;
    try {
      answered = await post(
        `/puzzle/${encodeURIComponent(puzzleId)}/edit`, grid, confirmed);
    } finally {
      inFlightIs(null);
    }
    // Never dropped, whatever turn it comes back into: this answer is the
    // only report of what the store did, and the page may not go quiet about
    // it. It speaks of "the grid you verified" and not of "this grid",
    // because the board is free to have moved since.
    const { code, body } = answered;
    if (body && body.ok !== true && body.reason === "needs_confirmation") {
      // The server asked the question. Nothing was stored — that is what this
      // reason's place on the allow-list claims and what the route makes true
      // — so the page keeps the grid, says which book the question is about,
      // and puts the question's two answers up. The Approve offer goes away
      // with that sentence: while a question is open the way on is its own
      // "Edit it anyway", not a second Approve that would only ask again.
      awaitingTheBook = grid;
      tell(needsConfirmationText(body.book));
      bookQuestion.hidden = false;
      editAnyway.focus();
      return;
    }
    if (code !== 200 || !body || body.ok !== true) {
      awaitingTheBook = null;
      tell(refusalText(code, body && body.message, body && body.reason, { storing: true }));
      save.focus();
      return;
    }
    awaitingTheBook = null;
    // The store said yes, and what the page does next depends on the board.
    //
    // The answer is TOLD on either branch, before anything else is done with
    // it: the refusals above are the ones read on this bar, and this success
    // is reported to the owner by the list they land on — the row's new
    // picture (AC-6) — rather than by a sentence a navigation in the same
    // task leaves unannounced. The sentence is still written, because it is
    // the only report of what the store did and the page may not go quiet
    // about it, and on the branch below that stays it is genuinely read.
    //
    // A stroke landed while the store was writing (AC-2's own fact, reached
    // through mechanism 2 rather than a second notion of "changed"): that
    // work is unstored and lives only on this board, so the page does not
    // leave with it, and says that they are still on the board and unstored
    // (F-001).
    if (mine !== turn) {
      tell(storedAndStayingText(body.puzzle));
      // The bar is still here, so focus has somewhere to stand -- and it has
      // to be put there: `tell("Storing this grid...")` above hid `decide`,
      // the focused Approve's ancestor, so the browser dropped focus to the
      // document (G-3 / CARD-211: focus is never dropped mid-flow). Save is
      // the target because it is the button this very sentence tells the
      // owner to press, which is the choice onBackToEdit and the refusal
      // branch above already make, and it is enabled again (`inFlightIs(null)`
      // ran in the `finally`). Review cycle 2, F-001.
      save.focus();
      return;
    }
    tell(storedText(body.puzzle));
    window.location.assign(THE_LIST);
  }

  // Back to edit (CARD-246's Cancel, renamed; the behaviour below is that
  // card's, unchanged).
  function onBackToEdit() {
    // Not while the store is writing. This is the one press that could spend
    // the turn for a reason other than "the board moved", and onApprove READS
    // that turn to decide whether a successful store LEAVES: forced here
    // mid-write it would both suppress the exit and make the page state a
    // fact about the board that is not true ("You changed the board while it
    // was being stored"). An owner cannot reach it -- the pair is `hidden` --
    // but that is exactly the argument the comment below refuses, and
    // `_SAVE_THEN_BACK` already forces such a press for the verify case.
    //
    // Narrow on purpose: a blanket `inFlight !== null` would drop the
    // verify-case turn spend the next line exists for (G-008). Silent, like
    // onBoardChange's identical guard, and for the same reason: the bar is
    // mid-"Storing this grid...", and the store's answer is the sentence the
    // owner must read -- a press that cannot stop the store does not get to
    // speak over it. Review cycle 2, F-002.
    if (inFlight === "approve") return;
    // It is a turn of its own (review cycle 2, G-008). An owner cannot reach
    // this mid-flight — the pair is `hidden`, which is `display: none` — but
    // safety that rests on another element's visibility is not safety:
    // without this line a press forced during a verify was silently undone
    // by the grade that landed after it, offer and all. Spending the turn
    // drops that grade. A SAVE's answer is still never dropped, because it
    // is the only report of what the store did, so the store keeps the last
    // word over a press that cannot stop it.
    turn += 1;
    tell(BACK_TO_EDIT);
    save.focus();
  }

  // Cancel: leave the editor, store nothing (AC-1/AC-2).
  function onLeave() {
    // An exit may not outrun the store (AC-7): refused while a request is in
    // flight, for the same reason a second Save is, and said rather than
    // merely not done.
    if (inFlight !== null) {
      tell(inFlightText(inFlight));
      return;
    }
    // Ask only when there is something to lose. An unedited board has
    // nothing unstored on it, so an exit from it is not a question.
    if (!boardChanged) {
      window.location.assign(THE_LIST);
      return;
    }
    // Unlike Clear's confirmation, this one is NOT closed by a stroke that
    // lands while it is open: Clear asks about one particular board, which a
    // stroke makes a different board, whereas "leave the editor?" is as true
    // of the board after the stroke as of the board before it — and truer.
    confirmLeave.hidden = false;
    leave.setAttribute("aria-expanded", "true");
    keepEditing.focus();
  }

  // The board stopped being the grid this page has been talking about
  // (solver.js dispatches this from the one place a change is recorded).
  function onBoardChange() {
    // Whatever is in flight is now about an old grid.
    turn += 1;
    // There is now unstored work on this board, so Cancel has something to
    // ask about. Recorded here because this is the one place a change is
    // announced — the same fact invariant 4 rests on, not a second notion of
    // "changed".
    boardChanged = true;
    // An approval is already on its way with the grid it captured, and its
    // answer is what the owner must read — a stroke does not get to speak
    // over the store. The turn spent above is not lost with this return:
    // onApprove compares it and, finding the board moved, keeps the page
    // rather than leaving with this stroke (F-001).
    if (inFlight === "approve") return;
    // The book's question is about ONE grid — the one the owner verified and
    // approved — so a stroke makes it a question about a grid that is not on
    // the board any more. Unlike "leave the editor?", which is as true after
    // a stroke as before it, this one is withdrawn: Clear's confirmation
    // follows the same rule for the same reason.
    if (!bookQuestion.hidden) {
      closeTheBookQuestion();
      tell(BOARD_MOVED);
      save.focus();
      return;
    }
    // Nothing was claimed, so there is nothing to correct: ordinary painting
    // does not write to the live region.
    if (verified === null && inFlight === null) return;
    tell(BOARD_MOVED);
  }

  save.addEventListener("click", onSave);
  approve.addEventListener("click", onApprove);
  back.addEventListener("click", onBackToEdit);
  leave.addEventListener("click", onLeave);
  // The confirmation's own two answers. "Leave editor" re-reads inFlight:
  // the dialog may have been open when a request started, and AC-7's refusal
  // is about the moment of leaving, not the moment of asking.
  leaveAnyway.addEventListener("click", () => {
    if (inFlight !== null) {
      closeTheConfirm();
      tell(inFlightText(inFlight));
      return;
    }
    window.location.assign(THE_LIST);
  });
  keepEditing.addEventListener("click", closeTheConfirm);
  // The book's question, answered. "Edit it anyway" is the owner's
  // confirmation, and it reaches the server as the save's own `confirmed`
  // field — the same grid, a different request.
  editAnyway.addEventListener("click", () => {
    const grid = awaitingTheBook;
    closeTheBookQuestion();
    if (inFlight !== null) {
      // A request started while the question stood open; the answer in flight
      // is the one the owner must read.
      tell(inFlightText(inFlight));
      return;
    }
    if (grid === null) return;
    void store(grid, true);
  });
  keepTheBook.addEventListener("click", () => {
    closeTheBookQuestion();
    tell(BOOK_KEPT);
    save.focus();
  });
  // Escape answers it the way "Keep the stored grid" does, as the other two
  // questions on this page do.
  bookQuestion.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    closeTheBookQuestion();
    tell(BOOK_KEPT);
    save.focus();
  });
  // Escape answers it the way "Keep editing" does, as Clear's does.
  confirmLeave.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    closeTheConfirm();
  });
  document.addEventListener(BOARD_CHANGE, onBoardChange);
  box.hidden = false;
}

start();
