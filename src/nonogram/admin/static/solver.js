// Puzzle player — renderer (TERM-037, FR-044, CARD-160; ADR-0038).
//
// Not the uniqueness solver (COMP-005, src/nonogram/solver/): this draws the
// page a person solves a stored puzzle on. Plain JavaScript, no framework, no
// build step (ADR-0038/R1). Board state lives in the pure module
// solver_state.js (ADR-0038/R4); this file is the only one that touches the
// DOM, and it only ever *reads* a board to paint it — and, since CARD-162,
// reads payload.solution to show the error count and the solved state.
//
// THE PAYLOAD — the page's whole contract with the server. puzzle_solve.html
// embeds it as JSON in <script type="application/json" id="puzzle-player-data">,
// built by admin/app.py's puzzle_solve route:
//   {
//     "id":       string,             the stored puzzle's id
//     "width":    int >= 1,           W, columns (the stored grid's, not the row's column)
//     "height":   int >= 1,           H, rows
//     "rows":     [[int, ...]] * H,   row clues, top to bottom
//     "columns":  [[int, ...]] * W,   column clues, left to right
//     "solution": [[bool] * W] * H    the solution grid (admin only — ADR-0038/R6)
//     "mode":     "edit", optional      see EDIT MODE below
//   }
// "rows"/"columns" are compute_clues(stored grid) — the one encoder, never
// re-derived here (ADR-0038/R3). A line with no filled cell is [0] and is shown
// as the single number "0". A payload that is absent or not of this shape is
// refused: an alert replaces the board and window.puzzlePlayer stays unset.
//
// EDIT MODE (CARD-246). The manual editor (templates/puzzle_edit.html,
// static/puzzle_edit.js) is a SECOND CONSUMER of this board, not a second
// board: there is one grid renderer in the panel and this is it (CARD-246
// G-2, for the reason ADR-0036/R3 gives for round marks — two implementations
// of one picture drift). The editor's page serves exactly the payload above
// with "mode": "edit" added, and this file reads that one flag. Anything else
// in `mode`, the key being absent included, is the player, unchanged.
// What the flag changes — FIVE reads of `editing`, and nothing else
// (CARD-246 review cycle 1, F-009: the list said three and the code read it
// four times, which is how a contract stops being one):
//   * the board STARTS on payload.solution (solver_state.js boardOfGrid:
//     FILLED/EMPTY, never UNKNOWN) rather than blank — the owner opens the
//     stored picture and paints on it;
//   * the browser SAVE is off (no localStorage read, no write, nothing
//     removed). The player's save is keyed by the puzzle's id, so an editor
//     sharing it would overwrite the solve-in-progress of the very puzzle
//     being edited — the player is not regressed (G-1), and this is the seam
//     where it would have been;
//   * the counters, the solved banner, the solved LOCK and the clue circles
//     are off (showProgress returns at once). All four are statements about
//     a board measured AGAINST payload.solution, and in edit mode the
//     solution is the thing being changed: the board starts equal to it, so
//     the lock would fire before the first stroke and the error count would
//     count departures from the grid the owner is editing;
//   * nextHint answers null. A hint reveals payload.solution, and in edit
//     mode that is the grid being rewritten, so a "hint" would paint the
//     owner's edit back to the stored picture. The editor's page ships no
//     Hint button, so this guard is not reached today (`actions.hint?.`
//     short-circuits its own argument) — it stays because the rule belongs
//     to the MODE and not to which elements a template happens to carry: a
//     Hint button added to an edit page must not be able to undo an edit;
//   * the recorded board announces itself. In edit mode, and only there,
//     commit() dispatches BOARD_CHANGE on `document` — see BOARD CHANGE
//     below.
//
// BOARD CHANGE (CARD-246 review cycle 1, F-002/F-004). The editor's save bar
// offers Approve for ONE grid: the grid whose grade is on screen, captured
// when Save was pressed. The moment the board stops being that grid the
// offer is wrong, and static/puzzle_edit.js withdraws it — so it has to hear
// about a change rather than go looking for one. This event is that seam,
// and it is dispatched from commit(), the single place a change is RECORDED:
// a click, a drag, undo, redo, a confirmed reset and setBoard all pass
// through it, so the editor needs no list of controls to watch (a list is
// what goes stale when the next control is added). An uncommitted mid-drag
// preview (`show`) is deliberately not announced: nothing is recorded yet
// and the drag's own commit follows.
// What that silence costs, written down (CARD-246 review cycle 2, G-003):
// `getBoard()` returns the DISPLAYED board, preview and all, so between a
// drag's first move and its pointerup the board on screen is a board the
// editor has not been told about and so is not the grid whose grade is on
// offer. The window is bounded by the gesture — pointerup commits the
// preview (announced) and beginPinch/pointercancel reverts to
// `history.board` (announced) — and the editor spends its turn either way,
// so no grade can outlive it. Closing it would mean handing the editor the
// RECORDED board rather than the displayed one; it is a gap in the
// announcement, not a defect in it.
// The editor's page leaves out the elements that go with them (the counters,
// the banner and Hint); everything else — the brush menu, Region, undo, redo,
// reset, zoom, the announce line — is the player's own markup and its own
// code here. The grid still ships as `solution` under the same key: in edit
// mode it is the stored grid the editor opens on, which is why it is also
// still validated as a grid.
//
// THE LIVE PLAYER — window.puzzlePlayer, set once the board is drawn:
//   payload            the parsed payload above
//   getBoard()         the current board (a solver_state.js value) — the
//                      player's own copy, never an object passed to setBoard
//   setBoard(board)    replace the board and repaint; a value that is not a
//                      board (solver_state.js isBoard: frozen, own data
//                      integer sides >= 1, a frozen genuine Array of exactly
//                      width*height cells, every index an own element holding
//                      a known state — no holes) or a board of other
//                      dimensions is refused with RangeError before anything
//                      is painted, and the current board and DOM are kept;
//                      an accepted board is copied (copyBoard) and the copy
//                      is stored and painted; it also starts a new marking
//                      history at that board (nothing to undo or redo), the
//                      error count and solved state are re-derived from it,
//                      and an open reset confirmation is closed (see "reset")
// Boards are trusted in-page values (see solver_state.js).
//
// MARKING (CARD-161, FR-044 AC-303..AC-311; the "?" mark, CARD-186; a click
// follows the brush, CARD-189; one brush dropdown, CARD-194, with Region
// beside it as a toggle of its own, CARD-211). The
// strokes and the undo/redo history are solver_state.js values (clickStroke,
// dragStroke, resetStroke, record, undo, redo); this file only turns input into those calls and
// paints the resulting board. The marking code (wireMarking) does not read
// payload.solution — it only asks start() whether the board is locked and
// which cell a hint would reveal — and no mark or hint sends a request
// (ADR-0038/R2).
//   pointer   pointerdown on a cell, then pointerup without having been over
//             another cell = a click: clickStroke with the tool selected at
//             pointerdown and a `repeat` flag (solver_state.js clickedState:
//             a first click gives the cell the brush's state, a repeat click
//             moves it one step along the brush's sequence — see there).
//             A click is a repeat when the previous input was a recorded
//             click on the same cell with the same tool: wireMarking keeps
//             that one click as `lastClick` ({row, col, tool} or null). It
//             is UI state only — not on the board, not in the history, never
//             undone, redone or saved (SAVE; a load starts with it null).
//             Every commit clears it (a drag, even one that changes nothing,
//             undo, redo — button or key — a hint, a confirmed reset,
//             setBoard), and so does picking a brush from the menu (mouse or
//             key, the current brush too), pressing Reset when that opens the
//             confirmation (so a reset opened and then cancelled ends the
//             run too) and pointercancel; the click path sets it after its
//             own commit. Pressing Region does NOT clear it (Region is not a
//             brush pick — see "region" below).
//             Having been over another cell = a drag: dragStroke with the
//             tool selected at pointerdown, previewed on every move, recorded
//             on pointerup; pointercancel drops it. A mouse drag (main
//             button) always marks. A touch or pen drag marks only while
//             Region is on (`gesture.paints` below) — the board's cells set
//             touch-action accordingly (.player-board.is-region, admin.css),
//             and Region turns itself off once such a drag is recorded, even
//             one that changes no cell (CARD-194 target behaviour #7): a
//             region drag never lands as two tool picks in the undo history,
//             only as the one dragStroke. With Region off, a touch or pen
//             pointerdown does not call setPointerCapture or preventDefault,
//             so the browser is free to pan instead; a tap (no intervening
//             move) still reaches pointerup over its starting cell and is a
//             click, same as today. Whether the pointer left its starting
//             cell is tracked regardless of `paints` (only painting the
//             preview is gated on it): a real touch almost always has the
//             browser cancel the gesture (pointercancel) once it recognises
//             a pan, before pointerup — but a pen does not reliably do that
//             (observed: Chromium lets a pen gesture reach pointerup even
//             after real movement, with no cancel), and nothing here may
//             assume a pointerup it does reach is a tap just because
//             painting never ran. A gesture that moved and never painted
//             marks nothing on release either way.
//   menu      #puzzle-player-tool-trigger (a button, aria-haspopup="menu")
//             opens #puzzle-player-tool-menu (role="menu", initially hidden):
//             FOUR role="menuitemradio" [data-player-tool] items in the
//             owner's order — Black, White, Maybe, Clear (the four
//             brushes, filled/empty/maybe/unknown; the fourth reads "Clear"
//             since CARD-247 — a label change only, its data-player-tool is
//             still "unknown" and solver_state.js still calls the state
//             "undecided"). Region was a fifth item
//             until CARD-211 and is now a control of its own (see "region"
//             below), so the menu holds brushes only and exactly one item is
//             aria-checked="true": the chosen brush. The trigger's accessible
//             name is always "Brush: <brush>" and its visible text is
//             "<brush>" — CARD-194's "Region · <brush>" composite text is
//             gone with the menu item. Enter, Space or
//             ArrowDown on the trigger opens the menu with focus on the
//             checked item; inside it ArrowDown/ArrowUp move with wraparound,
//             Home/End jump to the first/last item, Escape closes with no
//             change and returns focus to the trigger, and Tab closes the
//             menu and lets focus continue to the next control (Region, since
//             CARD-211 put it between the trigger and Undo) —
//             picking an item (click, or Enter/Space on a native <button>)
//             closes the menu and returns focus to the trigger the same way.
//             The trigger and the Region toggle are the two direct <button>
//             children of .player-tools (the menu is a sibling <div> between
//             them), so a layout selector scoped to ".player-tools > button"
//             sees both.
//   region    [data-player-region] (#puzzle-player-region, CARD-211): the
//             Region toggle, a plain <button> carrying its state in
//             aria-pressed ("true"/"false") rather than aria-checked — it is
//             a mode, not one option among several, which is what a screen
//             reader should announce. Since CARD-247 its face is three
//             .player-swatch cells in the chosen brush's mark instead of the
//             word "Region" — syncTrigger writes their data-state from the
//             brush, the run is aria-hidden, and the button's name comes
//             from an aria-label the template carries (the text that used to
//             name it is gone). Pressing it arms Region; it disarms
//             again when pressed a second time and, one-shot, the instant a
//             drag is recorded (#7) — the flag's whole transition table is
//             solver_state.js nextRegion, so this file only says which event
//             happened. Picking a brush leaves Region exactly as it was: a
//             DELIBERATE divergence from CARD-194's target behaviour #3,
//             decided by the owner on 2026-10-14 (CARD-211) once Region
//             stopped being a fifth item in the brush menu — see
//             nextRegion's own note in solver_state.js. So the two controls
//             are independent in both directions; arming Region never
//             changes the brush either, and never clears
//             `lastClick` (#4). Every change — including the automatic
//             disarm — is written to #puzzle-player-announce, so a screen
//             reader hears "Region on"/"Region off" without re-reading a
//             label; an unchanged value is never rewritten (the live region
//             would announce it again). The flag is UI state like
//             `lastClick` and `zoom`: never a cell state, never recorded,
//             never saved, so every load starts with Region off. While it is
//             armed the board carries .is-region, which is how admin.css
//             drops .player-cell's touch-action to none; the toggle is the
//             only thing that sets that class.
//   history   [data-player-action] undo / redo / reset; aria-disabled="true"
//             while there is nothing to do — pressing one then leaves the
//             board as it is, because undo/redo with an empty stack and a
//             reset of a blank board return the history unchanged.
//             Ctrl/Cmd+Z undoes, Shift+Ctrl/Cmd+Z redoes.
//   hint      [data-player-action="hint"] (CARD-183, a LADDER since CARD-269
//             — see LADDER below) answers the same situation three ways, one
//             rung per press: rung 1 highlights the line to look at
//             (.is-hint-line on its cells and clue boxes) and records
//             nothing, rung 2 adds the checked reason and records nothing,
//             rung 3 is CARD-183's reveal — hintStroke for solver_state.js
//             hintCell (which start() computes from the recorded board and
//             the payload's clues and solution) through the same commit as
//             every stroke. Any recorded change, and Check, put the ladder
//             back on rung 1. aria-disabled="true", and pressing it does
//             nothing, while hintCell is null, the board is locked, or a
//             gesture is in progress. The hinted cell carries .is-hinted
//             until the next commit; #puzzle-player-announce says which line
//             to look at, then why, then which cell was revealed — and says
//             when that cell came from the solution rather than from one line.
//             Since the owner's decision of 2026-10-30 each of those
//             sentences is ALSO written to #puzzle-player-explain, the
//             visible line beside the puzzle's title, so every rung
//             changes something a sighted player can see (review F-2 had
//             measured rung 2's board and toolbar byte-identical to rung
//             1's). See showExplain below.
//   check     [data-player-action="check"] (CARD-269) answers "is one of my
//             marks wrong?": it highlights the ROW of the first wrong mark
//             (the same .is-hint-line) and names it, or says there are none —
//             and, since 2026-10-30, says it in the visible line too, which
//             is what makes "no wrong marks" on a clean board something other
//             than a dead press. It changes no cell, records no stroke and
//             moves no counter, so it is free; it resets the hint ladder.
//             aria-disabled="true"
//             while the board is locked OR a gesture is in progress — the
//             same two conditions Hint reports above (CARD-269 review F-10;
//             the handler always returned early mid-drag, only the attribute
//             did not say so). Like Hint it is absent from the manual
//             editor's page (CARD-246).
//
// PROGRESS (CARD-162, FR-044 AC-312..AC-321). After every recorded stroke,
// undo, redo, reset and setBoard, start() re-derives both from the current
// (recorded) board and payload.solution with solver_state.js errorCount and
// isSolved — nothing is accumulated, so the count is the live number of
// wrong marks. A drag's preview is not counted until it is recorded.
//   errors    [data-player-errors] in the toolbar (inside a role=status
//             region): errorCount of the current board.
//   progress  [data-player-progress] (CARD-187): solvedPercent of the
//             current board + "%". Deliberately NOT a live region (no role,
//             no aria-live, no live ancestor) and never written to
//             #puzzle-player-announce: it changes on almost every mark, so a
//             screen reader reads it on demand only.
//   hints     [data-player-hints] (its own role=status region): hintCount of
//             the current history — undo lowers it, reset leaves it, setBoard
//             (a new history) sets it to 0.
//   solved    while isSolved(current board) holds: the banner
//             #puzzle-player-solved (the picture's name, server-rendered) is
//             shown in place of the tools (the tools are hidden but keep
//             their box, admin.css .player-slot — the menu trigger and its
//             menu sit inside that hidden box too, so neither is reachable,
//             and the menu is closed if it was open) and its text is put into the live
//             region #puzzle-player-announce (cleared when unsolved), the board carries .is-solved (a
//             short CSS animation on the transition into solved; none under
//             prefers-reduced-motion, admin.css), and the board is LOCKED —
//             pointer input, undo and redo (buttons and keys) change nothing;
//             undo and redo say aria-disabled="true". Of the player's
//             controls only reset acts. The lock is a function of the
//             current board, not a separate flag: whatever makes the board
//             solved (a stroke, an undo, a redo, setBoard) locks it, and
//             whatever makes it unsolved unlocks it — once locked, that is
//             reset, or the setBoard seam, which replaces the board.
//   reset     pressing Reset opens the in-page confirmation
//             #puzzle-player-confirm (role=alertdialog; never window.confirm)
//             and moves focus to its "Keep marks" button. "Reset board"
//             records resetStroke through record — one undoable step, also
//             from the solved state; "Keep marks" or Escape changes nothing.
//             Any of these closes it and returns focus to Reset. So does
//             every recorded stroke, undo or redo (button or key — even one
//             that changes nothing) and setBoard while it is open: the board
//             it asked about is gone, so it closes as "Keep marks" does,
//             after that change is recorded. Undoing a reset
//             made from the solved state brings the solved board back, and
//             with it the lock (see "solved").
//
// DOM / CSS (admin.css, "Puzzle player"): table.player-board inside
// .player-stage; th.player-clue.is-col (one box per column, above) and
// th.player-clue.is-row (one box per row, left), each carrying its 0-based
// line in data-line and holding one span.player-clue-num per number;
// td.player-cell with data-row, data-col and data-state = the cell's state.
// Every fifth line on both axes is heavier: a cell or clue box after one
// carries .major-right / .major-below (never the last line, which is the
// board's frame).
//
// BOTH GUTTERS (CARD-212, owner's doc 2026-10-13). A big board repeats its
// clues on both sides of an axis: row clues left AND right, column clues
// above AND below, so a player scrolled to the far edge still has clues in
// view. "Big" is BIG_SIDE per axis and each axis is decided on its own; the
// repetition is drawn only while the cells it leaves are DOUBLE_MIN_CELL or
// more, and otherwise the board keeps exactly today's rendering, CARD-193's
// mirror included — see layoutLadder and drawSettledLayout in start(), which
// choose the rung by measuring the board they drew (today's rendering first,
// so a board that can afford no duplicate is built once and no more).
// Because that condition is a measurement and not a media query, the board
// is redrawn when the WINDOW changes too, not only when the 820 px
// breakpoint flips. The duplicate gutter carries the same numbers in the
// same order as its twin and is aria-hidden, so a screen reader reads each
// clue once (clueBox); its numbers circle with their twins (clueNumbersOf
// pairs them by data-line). Every board built leaves one
// performance.mark(DRAW_MARK), so what a layout choice cost is countable.
//
// STICKY GUTTERS (CARD-271, owner's bug report 2026-10-22: "clues sometimes
// are missed at the bottom and at the left for big puzzles"). CARD-212's
// duplicates deliver "a player scrolled to the far edge still has clues in
// view" only while they FIT, and the biggest boards are exactly the ones they
// do not fit: at 1280 x 720 every board from about 24 columns up is drawn
// plain (see drawSettledLayout). So EACH axis keeps ONE of its gutters in
// view by sticking it to .player-stage — the one scroll container over the
// board (measured: the table's every ancestor from .main up is
// overflow:visible, so sticky resolves against the stage's own scrollport).
// The gutter that sticks is the one that carries the labels: the head column
// gutter and the first (or, mirrored, the only) row gutter. The DUPLICATE
// never sticks, which is a measurement and not a preference — a 30 x 30 at
// 300% zoom has a 584 px row band in a 980 px stage, so sticking a gutter at
// each end of an axis would cover the cells between them outright. drawBoard
// marks each box with .is-stuck-col / .is-stuck-row for the axis (or, for a
// corner, the two axes) it keeps in view; admin.css ("Clue gutters that stay
// in view") does the sticking. Nothing here is a fit decision:
// DOUBLE_MIN_CELL, BIG_SIDE, the ladder's rung order and isMirrored are
// untouched by this card, and a doubled board draws exactly the boxes, in
// exactly the places, that CARD-212 left it drawing.
//   And a band sticks only while it has ROOM to: a stuck band floats over
//   the cells, so it spends the stage's space twice. keepCluesInView
//   measures what the drawn band could cover and sets .is-keeping-rows /
//   .is-keeping-cols on the table per axis (STICK_MAX_SHARE); it runs after
//   every draw and after every zoom, because the band's depth follows the
//   cell. Where there is no room the board keeps today's rendering and the
//   clues still scroll away — which is the bug, unfixed, in the two places
//   it cannot be fixed this way: a mirrored phone (the band is 76% of the
//   stage) and 300% zoom (the band is magnified with the cells, to 9 cells
//   deep in an 11-cell stage). Both are owner decisions about the BAND, not
//   about stickiness, and both are recorded on CARD-271.
//
// ZOOM (CARD-195, FR-044). A view setting that multiplies the fitted cell
// side (admin.css --player-zoom on table.player-board); it changes no board
// state, is never recorded, never in serializeState/the save, and starts at
// ZOOM_MIN (100%) on every load — wireMarking's local `zoom` variable is
// never read by anything outside this file. 100% to 300%, in ZOOM_STEP
// (25-point) steps on the zoom buttons ([data-player-zoom-action="in"/"out"]
// in .player-zoom) and continuously on a two-finger pinch; the readout
// ([data-player-zoom-readout]) is plain text, not a live region. The pure
// arithmetic (clamping, a button's next step, a pinch's ratio, and the
// anchor-preserving scroll formula) lives in solver_state.js (ADR-0038/R4);
// this file only reads the pointers, the DOM and .player-stage's scroll
// position and calls it.
//   buttons   applyZoom(stepZoom(zoom, "in"|"out"), cx, cy) with (cx, cy) the
//             centre of .player-stage's own visible box (its clientWidth/2,
//             clientHeight/2) as the anchor, so that point's board content
//             stays where it was (target behaviour #5). A press at either
//             end of the range is a no-op (stepZoom itself clamps), so no
//             extra aria-disabled guard is needed.
//   pinch     Two touch or pen pointers down, the first of them started on a
//             board cell, is the board's pinch (pinch rule a): it cancels
//             any single-pointer gesture in progress exactly as rule (b)
//             says (the preview is reverted through player.show of the
//             recorded board, `gesture` and `lastClick` are cleared, and the
//             first pointer's own later pointerup is ignored — tracked by
//             `pinch` itself: once set, every pointerup/pointercancel of
//             either of its two pointers ends it with no commit, whichever
//             of the two the browser releases first), then on every move of
//             either pointer recomputes the zoom from pinchZoom(starting
//             zoom, starting distance, current distance) (rule c) and
//             anchors on the pointers' current midpoint, in the stage's own
//             box — not the page's. Two pointers landing with the first NOT
//             on a board cell (a clue box, or off the board entirely) is
//             rule (d): solver.js does nothing — no preventDefault, no
//             pointer capture — so the browser's own page pinch runs
//             instead, which is why clue boxes keep touch-action: auto
//             (admin.css, unchanged by this card). A third touch/pen pointer
//             while one of the two is already tracked, or while a pinch is
//             already active, is ignored outright. Mouse pointers never
//             reach any of this (rule f — only "touch"/"pen" pointerTypes
//             are tracked in `touchPoints`/`touchStartCell` at all).
//
// CROSSHAIR (CARD-267, owner decision 2026-10-22, player-convenience session:
// "highlight row/column for selected cell so that the gaze don't slide
// away"). The row and the column of the cell the player's attention is on are
// tinted, and their clue boxes with them, so the eye can travel from a cell
// to its clues and back without sliding onto a neighbouring line.
//
// RENDERING ONLY, and less even than Zoom above — Zoom is at least a
// setting, this is not. One class, `.is-crossed`, on elements that are
// already on the page: no new element, no ARIA (it repeats where the pointer
// already is, so a live announcement would be noise and a screen reader must
// read each cell and clue exactly as before), no `data-state` touched,
// nothing in a stroke, in the undo history or in the save, and no
// solver_state.js involvement at all — `serializeState` cannot see it
// (ADR-0038/R4; CARD-267 G-5). No request is made for it either: nothing
// here fetches, and a pointer move is not an input (ADR-0038/R2).
//
// WHICH CELL carries it (wireCrosshair below):
//   mouse/pen  the cell under the pointer, from `pointermove` (and from
//              `pointerdown`, which the touch rule below needs and a mouse
//              press harmlessly shares — it names the cell already named by
//              the move that got the pointer there). It clears when
//              the pointer LEAVES the stage, and only then: a pointer that is
//              over the board but not over a cell — a clue box, the stage's
//              own padding, the gutter corner — keeps the crosshair where it
//              was, which is the point of the card. Looking from a cell to
//              its own clue must not put the line out. (Nor does it move the
//              line TO that clue's row: hovering a clue box lights nothing,
//              which the card records as out of scope.)
//   touch      the cell under the finger, from `pointerdown` and through
//              every move of the gesture, and it STAYS there after
//              `pointerup`. A phone has no hover, so a crosshair that left
//              with the finger would never be seen between taps. This is the
//              one place the pointer TYPE is read, and it is read in the
//              leave handler rather than the move handler: a touch pointer's
//              release fires `pointerleave` at once, so a leave that did not
//              exempt touch would undo every touch crosshair the instant it
//              was made.
//   load       nothing is crossed until a pointer arrives.
// WHERE: both pages that load this file — the player and CARD-246's manual
// editor, whose board is a .player-stage too. The editor's reach is a
// decision and not a side effect (owner, 2026-10-28), and it is asserted on
// that page by tests/test_puzzle_solver_crosshair.py
// TestSolverCrosshair_ReachesTheManualEditor.
// Exactly one row and one column carry it at a time, by construction: the
// old one is taken off before the new one goes on, and the position is held
// as a single [row, col] or null.
//
// WHAT IT COSTS per move: one hit test (cellUnder, as marking already pays
// per move of a gesture) and, only when that answers a DIFFERENT cell,
// crossedParts twice — the old line pair off, the new line pair on. A move
// inside one cell does nothing at all, and nothing here ever redraws the
// board.
//
// A REDRAW (a mirror breakpoint, a resize, a zoom rung — see redraw() in
// start()) replaces every cell and every clue box, so no painted class can
// survive one. What would survive is this closure's MEMORY of where the
// crosshair was, and a remembered position with nothing painted is exactly
// the half-painted crosshair the card refuses: the next move onto that same
// cell would take the "same cell, nothing to do" return and paint nothing.
// So redraw() calls forget(), and the next pointer event paints afresh.

import {
  EMPTY, FILLED, MAYBE, UNKNOWN, applyStroke, clickStroke, copyBoard, createBoard, createHistory,
  dragStroke, errorCount, hintCell, hintCount, hintStroke, isBoard, isSolved, record,
  redo, resetStroke, undo,
} from "./solver_state.js";
// The progress percent (CARD-187): see PROGRESS above.
import { solvedPercent } from "./solver_state.js";
// Clue circles (CARD-188): see paintCircles below.
import { circledClues } from "./solver_state.js";
// The save in this browser (CARD-185): see SAVE below.
import { deserializeState, saveKey, serializeState } from "./solver_state.js";
// Zoom (CARD-195): see ZOOM below.
import { ZOOM_MAX, ZOOM_MIN, anchoredScroll, pinchZoom, stepZoom } from "./solver_state.js";
// Region (CARD-194's modifier, its own toggle since CARD-211): see "region"
// above. The flag's transitions and the "does this drag paint?" rule are
// pure (ADR-0038/R4); the button that shows the flag is this file's.
import { gesturePaints, nextRegion } from "./solver_state.js";
// The hint ladder (CARD-269): see LADDER below. The rung transitions, the
// rung-1/2 line choice, the rung-2 classifier and Check's first-wrong-row
// scan are all pure (ADR-0038/R4); the three announcements, the line
// highlight and the two buttons are this file's.
import {
  HINT_REASONS, RUNG_EXPLAIN, RUNG_POINT, RUNG_REVEAL, firstWrongRow, hintLine, hintReason,
  nextRung,
} from "./solver_state.js";
// Edit mode (CARD-246): see EDIT MODE above. Both are pure board arithmetic
// (ADR-0038/R4); answerOfBoard is imported by static/puzzle_edit.js, not by
// this file, which never asks a board for its answer.
import { boardOfGrid } from "./solver_state.js";

const MAJOR_EVERY = 5;

// The one value of payload.mode that is not the player (CARD-246).
const EDIT_MODE = "edit";

// "The recorded board changed" — dispatched on `document` in edit mode only
// (see BOARD CHANGE above). Exported, and imported by static/puzzle_edit.js,
// so the two halves of the seam cannot drift to two spellings of one string.
export const BOARD_CHANGE = "puzzle-board-change";

// The save of a page that keeps nothing: edit mode's `save` (see EDIT MODE).
// A read of null is what start()'s restore branch already treats as "no
// saved board", so the flag needs no second test there.
const NO_SAVE = Object.freeze({
  read: () => null,
  write: () => {},
  forget: () => {},
});

// A board is "big" on an axis once that side is past BIG_SIDE. CARD-193 chose
// 15 for the row axis (W > 15 mirrors the row clues on a phone) and had the
// number inline in two places; CARD-212 names it once and reuses the same
// number for the column axis (H > 15 doubles the column clues), so the two
// axes are one rule read twice, not two rules that can drift apart.
const BIG_SIDE = 15;

// CARD-212: a second gutter is drawn only while the cells it leaves are at
// least this many CSS pixels on a side — CARD-182's phone-fit minimum (a
// WCAG 2.2 (2.5.8) 24 px target), the number CARD-193 then dropped as a
// *floor* because a floor forced a sideways scroll. As a *condition* it costs
// nothing: a board that cannot afford the duplicate keeps exactly today's
// rendering (see layoutLadder in start()). It is compared against the cell as
// actually drawn, never against a re-derivation of admin.css's clamp.
const DOUBLE_MIN_CELL = 24;

// CARD-271: the most of .player-stage's own visible box a clue gutter may
// cover before it stops being kept in view. A stuck gutter floats over the
// cells it used to scroll away from, so "keep the clues in view" and "keep
// the BOARD in view" are the same budget spent twice -- and where the band is
// big, the board loses. The share is taken against what a band can actually
// cover, min(this axis's overflow, the band's own size), so an axis that
// barely scrolls keeps its clues however deep its band is.
//
// Two fifths is a MEASURED bar between two sets of cases rather than a round
// number, and the gap between them is narrow enough to be worth stating:
//
//   * the cases this card has to fix top out at 0.364 -- the deepest being a
//     30 x 30 at 1280 x 600, whose whole 135.4 px column band would scroll
//     off a 372 px stage;
//   * the cases where a stuck band demonstrably took the board away from the
//     player start at 0.496: a 15 x 15 at 1024 x 768 and 200% zoom, where a
//     359.4 px row band over a 724 px stage swallowed the cells a recorded
//     touch drag was aimed at (tests/test_puzzle_solver_zoom.py
//     TestSolverZoom_OneFingerDragIsUnchangedByZoom, which reds on a bar of
//     0.5 and passes on this one). They run up to 0.76 -- a mirrored 30 x 30
//     on a 390 px phone, six columns of a thirty-column board left visible
//     and the cells under the band not tappable at all
//     (tests/test_puzzle_solver_phone.py
//     TestSolverPhone_TouchDragMarksOnAFittedBoard).
//
// Nothing was measured between 0.364 and 0.496, so where in that gap the bar
// belongs is the owner's to move; CARD-271 records it as such.
const STICK_MAX_SHARE = 0.4;

// The performance.mark drawBoard leaves behind, one per board built.
const DRAW_MARK = "nonogram-player-board-draw";

// How long after the last `resize` event the board is redrawn for the new
// window (CARD-212; see the listener in start()). Long enough that dragging
// a window edge redraws once at the end rather than on every event, short
// enough that letting go feels like it settled immediately.
const RESIZE_SETTLE = 150;

function majorAfter(index, length) {
  return (index + 1) % MAJOR_EVERY === 0 && index + 1 < length;
}

function isSide(n) {
  return Number.isInteger(n) && n >= 1;
}

function isClueSet(lines, count) {
  return Array.isArray(lines) && lines.length === count && lines.every(
    (clue) => Array.isArray(clue) && clue.length >= 1
      && clue.every((n) => Number.isInteger(n) && n >= 0));
}

function isSolution(grid, width, height) {
  return Array.isArray(grid) && grid.length === height && grid.every(
    (row) => Array.isArray(row) && row.length === width
      && row.every((cell) => typeof cell === "boolean"));
}

// The payload, or an Error saying why there is none worth drawing.
function readPayload() {
  const element = document.getElementById("puzzle-player-data");
  if (!element) throw new Error("the page carries no puzzle data");
  let payload;
  try {
    payload = JSON.parse(element.textContent);
  } catch (error) {
    throw new Error(`the puzzle data is not JSON (${error.message})`);
  }
  if (!payload || !isSide(payload.width) || !isSide(payload.height)
      || !isClueSet(payload.rows, payload.height)
      || !isClueSet(payload.columns, payload.width)
      || !isSolution(payload.solution, payload.width, payload.height)) {
    throw new Error("the puzzle data does not describe a width x height board with its clues");
  }
  return payload;
}

// One clue box for line `line` (0-based) of its axis. `data-line` is what
// pairs a duplicate with its twin (clueNumbersOf below), independently of
// where in the table either of them sits.
//   right      the box draws on the right of the grid instead of the left
//              (CARD-193's mirrored gutter, and CARD-212's second row gutter)
//   duplicate  CARD-212's repetition: aria-hidden and unlabelled, so a screen
//              reader still reads each clue exactly once — from the first
//              gutter, which keeps the aria-label. It is also the box that
//              does NOT stick (CARD-271): an axis's duplicate already sits at
//              the far end, so .is-stuck-row / .is-stuck-col goes on its twin.
function clueBox(tag, kind, line, label, clue, { right = false, duplicate = false } = {}) {
  const box = document.createElement(tag);
  box.className = `player-clue is-${kind}${right ? " is-right" : ""}${duplicate ? "" : ` is-stuck-${kind}`}`;
  box.scope = kind === "row" ? "row" : "col";
  box.dataset.line = String(line);
  if (duplicate) box.setAttribute("aria-hidden", "true");
  else box.setAttribute("aria-label", `${label}: ${clue.join(" ")}`);
  for (const n of clue) {
    const number = document.createElement("span");
    number.className = "player-clue-num";
    number.textContent = String(n);
    box.append(number);
  }
  return box;
}

// The blank box where a clue gutter crosses another. `right` puts it on the
// right of the column clues, where it carries the heavy rule the row clues'
// own side normally draws (admin.css .player-corner.is-right).
//
// `stuck` is CARD-271's two markers, and a corner is the one box that needs
// them stated rather than derived: it lies in a column band AND in a row
// band, and the two are kept in view independently. `col` is "my column band
// is the one that sticks" (the head one, never the <tfoot> duplicate) and
// `row` is "my row band is the one that sticks" (the left gutter normally,
// the right one when CARD-193's mirror made the right gutter the only one).
function cornerBox(right, stuck) {
  const corner = document.createElement("td");
  corner.className = `player-corner${right ? " is-right" : ""}`
    + `${stuck.col ? " is-stuck-col" : ""}${stuck.row ? " is-stuck-row" : ""}`;
  return corner;
}

// Draw the empty board for `payload` into `stage`; returns the cell elements,
// row-major, in the same order as a board's cells. The `cells` array is
// row-major whatever `layout` says — only the clue boxes around them move.
//
// `layout` is one rung of start()'s layoutLadder:
//   mirrored     CARD-193: the one row-clue gutter draws on the RIGHT (each
//                body row's box after its cells, the head row's corner after
//                the last column clue), for boards wider than BIG_SIDE on
//                phones only. The left gutter is gone, not doubled.
//   rowGutters   1, or 2 for CARD-212's repetition: a second row-clue box
//                after each body row's cells and a second corner after the
//                last column clue. Never 2 together with `mirrored` — two
//                gutters are what the mirror is the fallback for.
//   colGutters   1, or 2: a whole second gutter of column-clue boxes in a
//                <tfoot> under the grid, with its own corner(s). The
//                duplicate carries the same numbers in the same order as its
//                twin (a bottom box reads top to bottom like the top one);
//                it is a repetition, never a mirror of the sequence.
// Each axis is counted into admin.css's cell clamp through
// --player-row-gutters / --player-col-gutters, so a doubled axis is fitted
// with both of its bands rather than one.
// `zoomPercent` (CARD-195, 100..300) sets --player-zoom as the multiplier
// admin.css's cell clamp multiplies by (100 -> 1); every redraw (see redraw()
// in start()) passes the current zoom through, so neither re-mirroring nor
// re-doubling ever resets it.
function drawBoard(stage, payload, layout, zoomPercent) {
  // One performance mark per board built (CARD-212). Building a board is the
  // player's one expensive act — a 30 x 30 is ~900 cells plus its gutters —
  // and the layout ladder in start() can build more than one before it
  // settles, so how many it built is worth being able to count: see
  // DRAW_MARK's own test (tests/test_puzzle_solver_clues.py
  // TestSolverClues_TheLadderStopsAtTheFirstRungThatFits).
  performance.mark(DRAW_MARK);
  const { width, height, rows, columns } = payload;
  const { mirrored, rowGutters, colGutters } = layout;
  const table = document.createElement("table");
  table.className = mirrored ? "player-board is-mirrored" : "player-board";
  table.setAttribute("aria-label", `Puzzle board, ${width} columns by ${height} rows`);
  // The cell side is computed in CSS from these (admin.css, --player-cell).
  table.style.setProperty("--player-cols", width);
  table.style.setProperty("--player-rows", height);
  table.style.setProperty("--player-zoom", String(zoomPercent / 100));
  // The widest row band in ch: each row number takes its digits and a 1.45 ch
  // gap (admin.css .player-clue.is-row), and the row has 0.5 ch of padding.
  table.style.setProperty("--player-row-ch", Math.max(...rows.map((c) => c.reduce((sum, n) => sum + String(n).length + 1.45, 0.5))));
  table.style.setProperty("--player-col-depth", Math.max(...columns.map((c) => c.length)));
  table.style.setProperty("--player-col-digits", Math.max(...columns.flatMap((c) => c.map((n) => String(n).length))));
  table.style.setProperty("--player-row-gutters", rowGutters);
  table.style.setProperty("--player-col-gutters", colGutters);

  // The column-clue gutter: above the grid, or (duplicate) under it.
  const columnGutter = (duplicate) => {
    const line = (duplicate ? table.createTFoot() : table.createTHead()).insertRow();
    // CARD-271: a corner's column band sticks only in the head; its row band
    // sticks on the side the one-or-first row gutter is on — the left, unless
    // the mirror put the only row gutter on the right.
    if (!mirrored) line.append(cornerBox(false, { col: !duplicate, row: true }));
    columns.forEach((clue, col) => {
      const box = clueBox("th", "col", col, `Column ${col + 1}`, clue, { duplicate });
      if (majorAfter(col, width)) box.classList.add("major-right");
      line.append(box);
    });
    if (mirrored || rowGutters === 2) {
      line.append(cornerBox(true, { col: !duplicate, row: mirrored }));
    }
  };
  columnGutter(false);

  const body = table.createTBody();
  const cells = [];
  rows.forEach((clue, row) => {
    const line = body.insertRow();
    const rowClue = (duplicate) => {
      const box = clueBox("th", "row", row, `Row ${row + 1}`, clue,
        { right: duplicate || mirrored, duplicate });
      if (majorAfter(row, height)) box.classList.add("major-below");
      return box;
    };
    if (!mirrored) line.append(rowClue(false));
    for (let col = 0; col < width; col += 1) {
      const cell = line.insertCell();
      cell.className = "player-cell";
      cell.dataset.row = String(row);
      cell.dataset.col = String(col);
      if (majorAfter(col, width)) cell.classList.add("major-right");
      if (majorAfter(row, height)) cell.classList.add("major-below");
      // The solved animation's per-cell delay (a diagonal sweep, admin.css).
      cell.style.setProperty("--player-wave", row + col);
      cells.push(cell);
    }
    // Mirrored, the one labelled gutter moves here; doubled, a duplicate
    // follows the left gutter's labelled boxes.
    if (mirrored) line.append(rowClue(false));
    else if (rowGutters === 2) line.append(rowClue(true));
  });
  if (colGutters === 2) columnGutter(true);

  stage.replaceChildren(table);
  return cells;
}

function paint(cellElements, board) {
  cellElements.forEach((element, index) => {
    element.dataset.state = board.cells[index];
  });
}

function showError(stage, reason) {
  const alert = document.createElement("div");
  alert.className = "alert alert-danger player-error";
  alert.setAttribute("role", "alert");
  alert.textContent = `This puzzle's board cannot be drawn: ${reason}.`;
  stage.replaceChildren(alert);
}

function start() {
  const stage = document.getElementById("puzzle-player");
  let payload;
  try {
    payload = readPayload();
  } catch (error) {
    showError(stage, error.message);
    console.error(`puzzle player: ${error.message}`);
    return;
  }

  // CARD-246's one flag (see EDIT MODE above). Read once, here, so every
  // branch below names the same value.
  const editing = payload.mode === EDIT_MODE;
  const save = editing ? NO_SAVE : browserSave(saveKey(payload.id));
  let history = createHistory(
    editing ? boardOfGrid(payload.solution) : createBoard(payload.width, payload.height));
  const saved = save.read();
  if (saved !== null) {
    const restored = deserializeState(saved, payload);
    if (restored === null) save.forget();
    else history = restored;
  }
  let board = history.board;

  const toolbar = document.getElementById("puzzle-player-controls");
  const errorsOut = toolbar.querySelector("[data-player-errors]");
  const hintsOut = toolbar.querySelector("[data-player-hints]");
  const progressOut = toolbar.querySelector("[data-player-progress]");
  const banner = document.getElementById("puzzle-player-solved");
  const announce = document.getElementById("puzzle-player-announce");

  // Redrawn by redraw() below: the live table, its cells (row-major) and the
  // clue-number spans (CARD-188). `table`/`cellElements`/`clueNumbers` are
  // `let` so every closure that reads them (showProgress, the marking
  // callbacks) sees the current board after a mirror redraw (CARD-193).
  let table, cellElements, clueNumbers;
  let solved = false;
  // The cell the last hint revealed, as {row, col} and not as the element
  // showing it (CARD-212 review cycle 2, G-003): a redraw replaces every
  // element, and a hint is a CELL, not an element, so naming it this way is
  // what lets showHint put the highlight back on the redrawn table.
  let hintedAt = null;

  // Move the .is-hinted highlight to `next` ({row, col}), or take it off
  // (null). The element is looked up through the live cellElements each
  // time, so this is also how the highlight is re-applied after a redraw.
  function showHint(next) {
    const element = (cell) => cellElements[cell.row * payload.width + cell.col];
    if (hintedAt) element(hintedAt)?.classList.remove("is-hinted");
    hintedAt = next;
    if (hintedAt) element(hintedAt)?.classList.add("is-hinted");
  }

  // CARD-193: boards wider than BIG_SIDE columns mirror their row clues to
  // the right, but only on phones (owner decision, 2026-10-06) — the ≤ 820 px
  // shell breakpoint, the same one admin.css keys the phone cell floor to.
  const mirrorQuery = window.matchMedia("(max-width: 820px)");
  function isMirrored() {
    return payload.width > BIG_SIDE && mirrorQuery.matches;
  }

  // CARD-212: the layouts to try for this board, roomiest first. Each axis is
  // eligible for its duplicate on its own (a 30 x 12 board doubles its row
  // clues and not its column clues), and a rung is taken only if the cells it
  // leaves are still DOUBLE_MIN_CELL or more (redraw() below measures the
  // rung it drew). Doubling needs MORE room than the mirror, not less, so
  // when no doubled rung fits, the last rung — exactly today's rendering,
  // mirror included — is drawn whether it fits or not. The row axis is
  // preferred over the column axis when only one of the two can be afforded,
  // because the row gutter is the one the owner reported first and the only
  // one CARD-193 ever mirrored.
  function layoutLadder() {
    const bigRows = payload.width > BIG_SIDE;
    const bigColumns = payload.height > BIG_SIDE;
    const mirrored = isMirrored();
    const ladder = [];
    if (bigRows && bigColumns) ladder.push({ mirrored: false, rowGutters: 2, colGutters: 2 });
    if (bigRows) ladder.push({ mirrored: false, rowGutters: 2, colGutters: 1 });
    if (bigColumns) ladder.push({ mirrored, rowGutters: 1, colGutters: 2 });
    ladder.push({ mirrored, rowGutters: 1, colGutters: 1 });
    return ladder;
  }

  // The side of a cell of the board as just drawn, in unzoomed CSS pixels:
  // --player-zoom multiplies admin.css's fitted cell, so dividing it out
  // again makes this measurement — and with it the rung redraw() settles on —
  // the same at every zoom level (CARD-195), rather than letting zooming in
  // change the board's structure.
  function drawnCell(zoomPercent) {
    return stage.querySelector("td.player-cell").getBoundingClientRect().width / (zoomPercent / 100);
  }

  // Error count, hint count, progress percent and solved state of the recorded history (see
  // PROGRESS); `hint` is the hintCell value just recorded, or null.
  function showProgress(hint) {
    // CARD-246: in edit mode there is no solution to measure against — the
    // board IS the answer being written — so there are no counters, no
    // banner, no lock and no clue circles, and the page carries none of
    // their elements. `solved` therefore stays false and the board never
    // locks, which is what lets the owner keep painting.
    if (editing) return;
    const errors = String(errorCount(history.board, payload.solution));
    // Rewriting the same text would make the live region announce it again.
    if (errorsOut.textContent !== errors) errorsOut.textContent = errors;
    const hints = String(hintCount(history));
    if (hintsOut.textContent !== hints) hintsOut.textContent = hints;
    const percent = `${solvedPercent(history.board, payload.solution)}%`;
    if (progressOut.textContent !== percent) progressOut.textContent = percent;
    const now = isSolved(history.board, payload.solution);
    if (now !== solved) announce.textContent = now ? banner.textContent.trim() : "";
    else if (hint) {
      // Rung 3 (CARD-269 review F-2): the reveal's sentence goes to BOTH
      // channels, the same way say() writes rungs 1-2 and Check. commit()
      // cleared the visible line a moment ago, so this is what replaces
      // rung 2's explanation with the answer rather than leaving the
      // explanation standing over a cell that is now revealed.
      const said = hintText(hint);
      announce.textContent = said;
      showExplain(said);
    }
    solved = now;
    banner.hidden = !solved;
    toolbar.classList.toggle("is-solved", solved);
    table.classList.toggle("is-solved", solved);
    paintCircles(clueNumbers, circledClues(history.board, payload.rows, payload.columns));
  }

  // (Re)draws the board for the current viewport from the recorded history —
  // called once at load and again, from the same recorded board, whenever
  // mirrorQuery crosses 820 px (CARD-193: nothing recorded is lost — history,
  // undo/redo and the save are untouched by a redraw).
  // `marking` (below) always exists by the time this runs (the first call
  // is textually after `const marking = wireMarking(...)`) — CARD-195's
  // zoom (marking.getZoom()) survives a redraw the same way.
  // CARD-212: the gutter layout is chosen by measuring, not by predicting —
  // a rung is drawn and the cell it produced is measured. Only the rung that
  // settles is wired to the marking code; the discarded ones are replaced
  // within this same task, so no frame is ever produced from one.
  //
  // Today's rendering is drawn FIRST, and when it is already under the bar
  // nothing else is drawn at all. Doubling only ever takes room from the
  // cells — in admin.css's min() each extra gutter adds a subtrahend to both
  // width terms and a band to the height term — so a plain board below
  // DOUBLE_MIN_CELL cannot be rescued by a rung above it. That is the
  // commonest case by far — at 1280 x 720 it is every board from about 24
  // columns up — and it costs one draw where it used to cost four
  // (measured at review cycle 1 on a 30 x 30 there: ~125 ms to an
  // interactive board on one draw, ~810 ms on four). A board that CAN
  // afford a duplicate pays for the rungs it tries, and if none of them
  // fits, the plain board already drawn is put back rather than built
  // again. The counts are pinned by draw marks, not by timings:
  // tests/test_puzzle_solver_clues.py
  // TestSolverClues_TheLadderStopsAtTheFirstRungThatFits.
  function drawSettledLayout(zoom) {
    const ladder = layoutLadder();
    const plain = ladder[ladder.length - 1];
    const plainCells = drawBoard(stage, payload, plain, zoom);
    if (ladder.length === 1 || drawnCell(zoom) < DOUBLE_MIN_CELL) return plainCells;
    const plainTable = stage.firstElementChild;
    for (let rung = 0; rung < ladder.length - 1; rung += 1) {
      const cells = drawBoard(stage, payload, ladder[rung], zoom);
      if (drawnCell(zoom) >= DOUBLE_MIN_CELL) return cells;
    }
    stage.replaceChildren(plainTable);
    return plainCells;
  }

  // CARD-271: which axes can afford to keep their gutter in view, decided by
  // measuring the board that was drawn — the same discipline as the layout
  // ladder above, and for the same reason: the band's depth is admin.css's
  // clamp times the clue the puzzle happens to have, and predicting it here
  // would be re-deriving that clamp.
  //
  // A stuck band floats over cells, so what is measured is how much of the
  // stage it can cover: min(this axis's overflow, the band's own size). An
  // axis that does not scroll covers nothing however deep its band is (a
  // 15 x 15, and every doubled board at 100 %, are in that case), and an
  // axis past STICK_MAX_SHARE of the stage keeps today's rendering — the
  // clues scroll away, which is the bug, but a band over most of the board
  // is worse than the bug (see STICK_MAX_SHARE).
  //
  // Sticky takes no part in layout and, in Chromium, a stuck box adds
  // nothing to the scrollable overflow either, so neither term below is
  // changed by the classes this sets: the measurement cannot oscillate
  // (asserted in tests/test_puzzle_solver_clues.py
  // TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted).
  function keepCluesInView() {
    // The fallback fails CLOSED, toward not sticking (CARD-271 review cycle
    // 1, F-003). `Infinity` is the largest value `affords` can be handed, so
    // the only axis that still keeps with its band unmeasurable is one whose
    // own overflow is already inside the share — i.e. one where a band, of
    // whatever size, could cover no more than that overflow anyway. A 0 here
    // answered the opposite: a band of nothing always affords, so an axis
    // whose labelled gutter could not be found would STICK, which is the
    // board-eating direction STICK_MAX_SHARE exists to refuse (ADR-0039/R2).
    // No test can cover the branch, and that is measured rather than assumed:
    // the review's mutant R2 deleted the guard outright and all 158 tests of
    // the five-file selection stayed green, because every board drawBoard
    // produces marks one `is-stuck-row` box and one `is-stuck-col` box — the
    // branch is DEAD, not untested, so its direction is all there is to get
    // right. tests/test_puzzle_solver_clues.py's _ROOM reimplements this
    // expression and moves with it.
    const band = (selector, side) => {
      const box = table.querySelector(selector);
      return box === null ? Infinity : box.getBoundingClientRect()[side];
    };
    const affords = (overflow, bandSize, port) =>
      Math.min(overflow, bandSize) <= port * STICK_MAX_SHARE;
    table.classList.toggle("is-keeping-rows", affords(
      stage.scrollWidth - stage.clientWidth,
      band("th.player-clue.is-row.is-stuck-row", "width"), stage.clientWidth));
    table.classList.toggle("is-keeping-cols", affords(
      stage.scrollHeight - stage.clientHeight,
      band("th.player-clue.is-col.is-stuck-col", "height"), stage.clientHeight));
  }

  function redraw() {
    const zoom = marking.getZoom();
    cellElements = drawSettledLayout(zoom);
    table = stage.querySelector(".player-board");
    clueNumbers = clueNumbersOf(table);
    keepCluesInView();
    paint(cellElements, board);
    // The highlighted ELEMENT is gone with the old table; the hinted CELL is
    // not, so it is put back on the new one (CARD-212 review cycle 2,
    // G-003). Before this card a redraw meant crossing 820 px; it now also
    // means any window resize — a phone fires one when its URL bar
    // collapses, mid-solve — and "Hints: N" survives a redraw, so the
    // highlight the reader paid for has to survive it too.
    showHint(hintedAt);
    // CARD-267: and the crosshair is the other way round — the hinted CELL
    // outlives the elements that showed it, the crosshair does not. Every
    // cell and clue box it was painted on has just been replaced, so there
    // is nothing stale on screen; what has to go is the REMEMBERED position,
    // or the next pointer move onto that same cell would read "already
    // there" and paint nothing (see CROSSHAIR at the top of this file).
    crosshair.forget();
    showProgress(null);
    marking.refresh();
  }

  // Pointer, tool, history and keyboard input is wired once, to `stage`
  // (which survives a redraw) rather than to the table a redraw replaces —
  // see wireMarking.
  const marking = wireMarking(stage, {
    getHistory: () => history,
    locked: () => solved,
    // CARD-246: a hint reveals the solution, and in edit mode the solution
    // is what the owner is rewriting — "revealing" it would push the board
    // back to the stored grid. The editor's page ships no Hint button and
    // this answers null for the guards that ask anyway.
    nextHint: () => (editing ? null : hintCell(history.board, payload.rows, payload.columns, payload.solution)),
    // CARD-269: the line rungs 1 and 2 point at for a nextHint() result, and
    // the row Check names — both read the RECORDED board and the payload, so
    // they are asked here, beside nextHint, rather than from wireMarking.
    hintLine: (hint) => hintLine(history.board, payload.rows, payload.columns, payload.solution, hint),
    wrongRow: () => firstWrongRow(history.board, payload.solution),
    show(next) {
      board = next;
      paint(cellElements, board);
    },
    commit(next, hint) {
      history = next;
      board = history.board;
      paint(cellElements, board);
      showHint(hint ? { row: hint.row, col: hint.col } : null);
      showProgress(hint);
      save.write(serializeState(history, payload));
      // CARD-246 (see BOARD CHANGE above): the one announcement of a
      // recorded change, for the one consumer that needs it. Off in the
      // player, which has nobody listening and must stay byte-identical.
      if (editing) {
        document.dispatchEvent(new CustomEvent(BOARD_CHANGE, { bubbles: true }));
      }
    },
    forget: () => save.forget(),
    // CARD-271: zoom changes the band and the overflow without redrawing the
    // board (it is one custom property on the table), so the "can this axis
    // afford to keep its clues?" measurement has to be taken again after
    // one. It is the only thing zoom does beyond --player-zoom and the
    // anchored scroll, and it records nothing (CON-021).
    zoomed: () => keepCluesInView(),
  });
  // CARD-267: the crosshair's own pointer listeners, on the same stage and
  // wired once for the same reason. Constructed before the first redraw()
  // because redraw() calls forget() on it, exactly as it calls
  // marking.getZoom(); it takes no `player` callback at all, because a
  // crosshair reads no board (G-5).
  const crosshair = wireCrosshair(stage);
  redraw();
  // CARD-193: the mirror follows the viewport, not a redraw of its own
  // accord. CARD-212: the gutter layout follows it too — the room for a
  // duplicate is a property of the viewport — so a board big on EITHER side
  // redraws here, not only a mirrorable one; a board big on neither, which
  // can have no mirror and no duplicate, never redraws at all.
  //
  // CARD-271 (review cycle 1, F-001): and a board big on neither side still
  // has to RE-MEASURE. Before this card every viewport-dependent decision was
  // a LAYOUT one — CARD-193's mirror, CARD-212's ladder — and both need a
  // board big on one side, so that gate was the right gate. The room
  // condition is viewport-dependent for EVERY board, so what the two
  // listeners below reach is split: `keepCluesInView()` always, `redraw()`
  // only where the layout itself can change. Measured on a 15 x 15 at 200 %
  // zoom dragged from 1920 x 1500 to 1024 x 768 with the resize settled: the
  // classes set at load (both axes keeping, nothing scrolling there) survived
  // into a viewport whose own terms answer neither axis — a 376.3 px row band
  // and a 270.4 px column band over a 724 x 540 scrollport, shares 0.520 and
  // 0.501 against STICK_MAX_SHARE — and 105 of the 140 cells visible at the
  // bottom-right corner then hit-tested to a band instead of to themselves.
  // That is exactly the regression class STICK_MAX_SHARE was measured to
  // refuse, reinstated through the one path that did not re-measure. The
  // reverse was stale too: a board grown wider kept today's rendering where
  // the rule says there is room, so the clues scrolled away.
  //
  // Re-measuring is not redrawing, and the split is what keeps BOTH comments
  // above true: keepCluesInView() reads four numbers off boxes that are
  // already there and toggles two classes, leaving no DRAW_MARK behind, so a
  // small board still draws exactly once however often its window moves
  // (tests/test_puzzle_solver_zoom.py
  // ..._a_board_too_small_to_double_is_not_redrawn_by_a_resize counts that,
  // and ..._a_burst_of_resize_events_redraws_once still bounds the big
  // board's draws). Redrawing every board on every resize would have paid a
  // board build for a decision that needs two class toggles.
  const isBig = payload.width > BIG_SIDE || payload.height > BIG_SIDE;
  const viewportChanged = () => {
    // redraw() re-measures as part of drawing — see keepCluesInView() in it.
    if (isBig) redraw();
    else keepCluesInView();
  };
  mirrorQuery.addEventListener("change", viewportChanged);
  // CARD-212: and the window itself, not only the breakpoint. CARD-193's
  // mirror could never go stale, because its condition IS the media query
  // above — cross 820 px and it is re-evaluated, and it is false everywhere
  // else. This card's condition is a continuous one (does the board still
  // measure DOUBLE_MIN_CELL with the duplicate?), so behind that discrete
  // trigger alone a board loaded wide stayed doubled while the window
  // shrank: measured, a 30 x 25 loaded at 1920 x 1500 and dragged to
  // 900 x 800 kept its duplicates at 14.39 px cells — 9.6 px under its own
  // bar — with 376 px of sideways scroll inside the stage that the same
  // board reloaded at that size does not have.
  // Trailing debounce rather than a redraw per event: a drag fires `resize`
  // continuously, and a redraw of a 30 x 30 is tens of milliseconds of
  // layout even now that the ladder early-outs. RESIZE_SETTLE after the LAST
  // event the board is redrawn once — a burst of eight events costs at most
  // two draws, not eight (tests/test_puzzle_solver_zoom.py
  // ..._a_burst_of_resize_events_redraws_once) — from the recorded history,
  // exactly as a breakpoint crossing redraws it: marks, zoom, undo/redo, the
  // save, and since G-003 the hinted cell's highlight all survive.
  // Both boards are debounced, and the small one for the same reason the big
  // one is: a window drag fires `resize` continuously, and a re-measurement
  // per event would read the layout mid-drag and toggle the classes on
  // readings the player never sees settle.
  let resizeSettling = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeSettling);
    resizeSettling = setTimeout(viewportChanged, RESIZE_SETTLE);
  });

  window.puzzlePlayer = Object.freeze({
    payload,
    // The DISPLAYED board: mid-drag this is `show`'s preview and not the
    // recorded one, which is the window BOARD CHANGE above documents for the
    // editor that reads it (CARD-246 review cycle 2, G-003).
    getBoard: () => board,
    setBoard(next) {
      if (!isBoard(next)) {
        throw new RangeError("setBoard needs a board from solver_state.js (see isBoard: frozen, width*height known cell states, no holes)");
      }
      if (next.width !== payload.width || next.height !== payload.height) {
        throw new RangeError(
          `a ${next.width}x${next.height} board does not fit this ${payload.width}x${payload.height} puzzle`);
      }
      // Recorded like any other change (paint, progress, controls, and the
      // reset confirmation closed), as a fresh history.
      marking.commit(createHistory(copyBoard(next)));
    },
  });
}

// SAVE (CARD-185; FR-044 AC-360..AC-365, CON-021). This browser keeps one
// localStorage entry per puzzle, under solver_state.js saveKey(payload.id),
// holding serializeState of the recorded history; nothing is sent anywhere.
// At load, before the first showProgress, an entry that deserializeState
// trusts becomes the starting history (board, counts, undo and redo, and a
// solved board's banner and lock); one it does not trust is removed and the
// board starts blank. Every commit (stroke, hint, undo, redo, setBoard)
// writes the entry, a drag's preview does not, and a confirmed reset removes
// it (its in-page undo writes it again). A history serializeState cannot
// save (setBoard's non-blank start) removes it too. Each access to storage,
// window.localStorage itself included, is caught and silent: without
// storage the player works as before, and a failed write removes the entry
// so a reload never shows an older board than the one on screen.
function browserSave(key) {
  function forget() {
    try {
      window.localStorage.removeItem(key);
    } catch {
      // no storage: nothing to remove
    }
  }
  return {
    forget,
    read() {
      try {
        return window.localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    write(text) {
      if (text === null) {
        forget();
        return;
      }
      try {
        window.localStorage.setItem(key, text);
      } catch {
        forget();
      }
    },
  };
}

// CLUE CIRCLES (CARD-188). showProgress, run on every commit (stroke, undo,
// redo, reset, setBoard) and never for a drag's preview, sets
// .is-circled on each span.player-clue-num that solver_state.js circledClues
// circles for the recorded board, and clears it on the rest. The spans are
// collected once, here, at draw time: { rows: [...] per row, columns: [...]
// per column }, and each line holds one entry per clue NUMBER — the one or
// two spans that show it, one per gutter (CARD-212), paired by their box's
// data-line rather than by DOM order. So a duplicate is circled with its
// twin, by construction: paintCircles cannot reach one and miss the other.
// Each span is also given its digit count as --player-clue-digits. Text and
// aria-labels are left alone.
function clueNumbersOf(table) {
  const axis = (kind) => {
    const lines = [];
    for (const box of table.querySelectorAll(`th.player-clue.is-${kind}`)) {
      const line = Number(box.dataset.line);
      (lines[line] ??= []).push([...box.querySelectorAll(".player-clue-num")]);
    }
    return lines.map((gutters) => gutters[0].map((_, k) => gutters.map((spans) => spans[k])));
  };
  const numbers = { rows: axis("row"), columns: axis("col") };
  // The ring's pill width comes from the digit count (admin.css, --player-ring).
  for (const span of [...numbers.rows, ...numbers.columns].flat(2)) {
    span.style.setProperty("--player-clue-digits", span.textContent.length);
  }
  return numbers;
}

function paintCircles(clueNumbers, circled) {
  for (const axis of ["rows", "columns"]) {
    clueNumbers[axis].forEach((numbers, line) => {
      numbers.forEach((twins, k) => {
        for (const span of twins) span.classList.toggle("is-circled", circled[axis][line][k]);
      });
    });
  }
}

// What the live region says about a hint (1-based row and column).
function hintText({ row, col, state, deduced }) {
  const cell = `row ${row + 1}, column ${col + 1} is ${state === FILLED ? "black" : "white"}`;
  return deduced ? `Hint: ${cell}.`
    : `Hint: no cell follows from a single line yet; ${cell} (from the solution).`;
}

// ---------------------------------------------------------------------------
// LADDER (CARD-269) — the three things one Hint press can say, and Check
//
// The rung arithmetic is solver_state.js's (nextRung, hintLine, hintReason,
// firstWrongRow — see the ladder block there). What lives here is the four
// pieces of rendering: the SENTENCES below, the `.is-hint-line` highlight on
// a line's cells and clue boxes (wireMarking's setLadderLine), the rung's
// value beside Region's flag, and the two buttons.
//
// Rungs 1 and 2 record nothing: no stroke, no cell change, no counter move,
// no save. "Hints: N" therefore keeps meaning exactly what CARD-183 made it
// mean — cells the player did not deduce themselves — because hintCount
// still counts only `hint: true` strokes and only rung 3 records one.
//
// Every sentence is written through `say` below, into BOTH channels at once:
// #puzzle-player-announce, the one live region this page has (the solved
// banner and rung 3's hintText write it too; whichever wrote last wins), and
// #puzzle-player-explain, the visible answer line the owner's decision of
// 2026-10-30 added — see showExplain below for the measurement that forced
// it and for the accessibility-tree choice.
// A press that repeats its own answer REASSIGNS that sentence. CARD-269
// review F-9 measured this with a MutationObserver on the shipped page: the
// textContent setter runs the DOM's "string replace all", which removes the
// existing text node and inserts a new one, so an identical assignment still
// produces a mutation record. This file's earlier claim that it is "a no-op
// in the DOM" was simply false. Whether assistive technology re-reads the
// repeated sentence is therefore the AT's choice, not a platform rule, and
// nothing here suppresses the write: the live region always holds the answer
// to the last press, which is what a player returning to it needs. Nothing
// is skipped and there is no state to keep in step.

//: Rung 1: where to look, and nothing more. `axis` is a hintLine axis, so it
//: is already the word to say out loud ("row" / "column").
function ladderPointText(axis, index) {
  return `Hint: look at ${axis} ${index + 1}.`;
}

//: Rung 2's reason clause, one sentence per HINT_REASONS name. Each is
//: ALWAYS TRUE of the line hintReason just checked it on — "generic" by
//: lineForced's own definition of a forced cell, the other two because
//: hintReason verified their precondition and returns the name only then.
//: Keyed by the pure module's names so a reason and its sentence cannot
//: drift apart: a name with no sentence here is a RangeError at the press,
//: never an announcement reading "undefined".
//:
//: EXPORTED so that claim is a test and not a comment (ADR-0039/R2; CARD-269
//: review F-6, which measured that it was module-private and therefore that
//: no test could read these keys at all — a missing sentence was caught by
//: the RangeError at a driven press, but an EXTRA key was dead and
//: undetected). TestSolverHintLadder_ThePureModule now asserts
//: Object.keys(LADDER_REASON) IS HINT_REASONS, both directions.
export const LADDER_REASON = Object.freeze({
  "runs-complete": (axis) => `every run in this ${axis} is placed; the rest is white.`,
  overlap: (axis, run) => `the ${run}-run must overlap in the middle whatever its position.`,
  generic: (axis) => `every placement of this ${axis}'s clues agrees on at least one cell.`,
});

//: Rung 2: rung 1's sentence with the checked reason added.
function ladderExplainText(line) {
  const { reason, run } = hintReason(line.clue, line.cells, line.at);
  const sentence = LADDER_REASON[reason];
  if (sentence === undefined) {
    throw new RangeError(`"${reason}" is not a hint reason (${HINT_REASONS.join(", ")})`);
  }
  return `Hint: look at ${line.axis} ${line.index + 1} — ${sentence(line.axis, run)}`;
}

//: The exhausted state (card rule 6): undecided cells remain but no single
//: line decides one, so hintLine answers null. THIS SENTENCE IS THE CARD.
//: Rungs 1 and 2 highlight nothing and say what is actually the case, in
//: place of CARD-183's "no cell follows from a single line yet" arriving
//: fused to a revealed cell — which read as "you missed a line deduction"
//: when there was none to miss. Rung 3 is still that fallback reveal, with
//: its shipped "(from the solution)" wording (hintText above), so the
//: expensive answer is still available; it is no longer the only one, and
//: the two cheap rungs no longer teach a falsehood to get to it.
const LADDER_EXHAUSTED = "Hint: no single row or column decides a cell right now.";

//: Which sentence a press on each rung says about a line it DID find, keyed
//: by the rung the press was made ON. EXPORTED and keyed by HINT_RUNGS'
//: values, so the suite asserts these keys ARE the rungs that announce a
//: line — every rung in HINT_RUNGS except RUNG_REVEAL, which reveals instead
//: of announcing and is handled before the handler ever gets here.
//:
//: CARD-269 review F-6: the dispatch used to be a two-way ternary over a
//: three-valued rung, derived from no authority at all, so a fourth rung
//: added to HINT_RUNGS would have silently rendered rung 2's explain text.
//: A rung with no entry here is now a RangeError at the press, exactly as an
//: unknown event already is in nextRung and an unknown reason is in
//: ladderExplainText.
export const LADDER_SAY = Object.freeze({
  [RUNG_POINT]: (line) => ladderPointText(line.axis, line.index),
  [RUNG_EXPLAIN]: (line) => ladderExplainText(line),
});

//: Check (card rule 7): the ROW of the first wrong mark, never the cell —
//: Hint's rung 1 for a mistake. "no wrong marks" is the honest answer to the
//: question CARD-183's Hint silently danced around: hintCell ignores wrong
//: marks (AC-328) and never said so, so a player whose board was wrong got
//: hints that could not help and no word about why.
function checkText(row) {
  return row === null ? "Check: no wrong marks." : `Check: a mark in row ${row + 1} is wrong.`;
}

//: The SEEN half of every sentence above (CARD-269 review F-2, owner decision
//: 2026-10-30). #puzzle-player-announce is 1 x 1 and clipped, so until this
//: existed the ladder's whole output went only to a screen reader, and cycle 1
//: measured the consequence rather than argued it: rung 2's board and toolbar
//: were indistinguishable from rung 1's by SHA-256 of element screenshots with
//: getAnimations() settled. The rung whose job is "explain the deduction"
//: changed nothing a sighted player could see, and on an exhausted board rungs
//: 1 and 2 — and Check on a clean board — were presses indistinguishable from
//: a dead button. (The review said BYTE-identical. Fix round 2 re-measured:
//: the board reproduces as byte-identical, the toolbar does not once this line
//: exists — the announce write invalidates a tile and 6 pixels come back one
//: level apart in two button corners. The test's _pixel_delta carries that
//: correction and bounds the claim by LEVEL instead.)
//:
//: #puzzle-player-explain is a plain <p> in the page-head row, beside the
//: puzzle's title and directly above the toolbar — the only place on this page
//: that holds a line of text at zero vertical cost, which is why it is not in
//: the toolbar-to-board gap where it reads most naturally (admin.css has the
//: arithmetic, the two placements that were tried, and the residual). It
//: carries aria-hidden="true": the live region stays
//: THE assistive-technology channel and stays unchanged, so a screen reader
//: meets each sentence once as an announcement instead of twice.
//:
//: Optional, like the Hint button itself: puzzle_edit.html (CARD-246) loads
//: this same file with no Hint, no Check and no explain line, and there this
//: is a no-op rather than a mode flag of its own.
function showExplain(text) {
  const line = document.getElementById("puzzle-player-explain");
  if (line !== null) line.textContent = text;
}

// The elements `.is-hint-line` goes on for one line: every cell of it and
// every clue box of it. Keyed on the AXIS plus data-line exactly as
// crossedParts above is, and for the same reason — on a CARD-212 doubled
// axis BOTH clue twins carry data-line, and a selector that read DOM order
// would reach one twin and miss the other.
function linedParts(table, axis, index) {
  const cells = axis === "row" ? `td.player-cell[data-row="${index}"]`
    : `td.player-cell[data-col="${index}"]`;
  const clues = axis === "row" ? `th.player-clue.is-row[data-line="${index}"]`
    : `th.player-clue.is-col[data-line="${index}"]`;
  return [...table.querySelectorAll(cells), ...table.querySelectorAll(clues)];
}

// The [row, col] of the board cell under the viewport point (x, y), or null.
// `container` only needs to contain the live table — see wireMarking.
function cellUnder(container, x, y) {
  const cell = document.elementFromPoint(x, y)?.closest("td.player-cell");
  if (!cell || !container.contains(cell)) return null;
  return [Number(cell.dataset.row), Number(cell.dataset.col)];
}

function isAt(position, [row, col]) {
  return position[0] === row && position[1] === col;
}

// The elements the crosshair for board cell (row, col) marks (CARD-267; see
// CROSSHAIR above): that row's cells, that column's cells, and the clue
// boxes of row `row` and of column `col`. The clue boxes are selected by
// AXIS + data-line and never by DOM order, so on an axis a big board doubled
// (CARD-212) BOTH twins come back — the same rule, for the same reason, that
// clueNumbersOf follows for the circles: a selector keyed on data-line
// cannot reach one twin and miss the other.
//
// The cell at (row, col) itself is in both cell sweeps. classList.toggle
// with an explicit second argument is idempotent, so being listed twice
// costs one no-op and no correctness.
function crossedParts(table, row, col) {
  return [
    ...table.querySelectorAll(`td.player-cell[data-row="${row}"]`),
    ...table.querySelectorAll(`td.player-cell[data-col="${col}"]`),
    ...table.querySelectorAll(`th.player-clue.is-row[data-line="${row}"]`),
    ...table.querySelectorAll(`th.player-clue.is-col[data-line="${col}"]`),
  ];
}

// Attach the crosshair to `container` — the player's stage, for exactly
// wireMarking's reason: a redraw replaces the table, so the listeners go on
// the element that survives one and the live table is read fresh on every
// event. Returns { forget }, which redraw() calls (see CROSSHAIR above).
//
// Marking is not touched by any of this (CARD-267 G-6). These are listeners
// of their own on the same element: they call no `player` callback, they
// read no board, they never preventDefault and never stop propagation, so
// every handler wireMarking registered sees exactly the events it saw
// before, in the same order, with the same `defaultPrevented`.
function wireCrosshair(container) {
  // Where the crosshair is, as [row, col], or null. A CELL and not an
  // element, for showHint's reason: a redraw replaces every element.
  let crossed = null;

  function paintCrosshair([row, col], on) {
    const table = container.querySelector(".player-board");
    // No board to paint on. The branch is DEAD rather than untested, and that
    // is measured and not assumed (CARD-271's precedent for exactly this):
    // start() returns before wireCrosshair when readPayload refuses, so the
    // listeners are never attached to a stage that holds an alert, and a
    // redraw replaces the table inside one task, so no pointer event can land
    // between the removal and the insertion. The mutant that deletes this
    // line leaves all 15 tests of tests/test_puzzle_solver_crosshair.py green
    // (measured). So its DIRECTION is all there is to get right, and it fails
    // toward not painting — never toward a half-painted crosshair.
    if (table === null) return;
    for (const part of crossedParts(table, row, col)) part.classList.toggle("is-crossed", on);
  }

  // Move the crosshair to `position` ([row, col]). A move that lands on the
  // cell it is already on does nothing — no DOM write at all, which is what
  // makes a pointer wandering inside one cell free.
  function moveTo(position) {
    if (crossed !== null && isAt(position, crossed)) return;
    if (crossed !== null) paintCrosshair(crossed, false);
    crossed = position;
    paintCrosshair(crossed, true);
  }

  function clear() {
    if (crossed === null) return;
    paintCrosshair(crossed, false);
    crossed = null;
  }

  // `pointerdown` as well as `pointermove`, so a touch TAP — which can reach
  // pointerup without a single move — leaves the crosshair on the cell it
  // tapped, and so a gesture is crossed from the moment it starts.
  const follow = (event) => {
    const position = cellUnder(container, event.clientX, event.clientY);
    if (position !== null) moveTo(position);
  };
  container.addEventListener("pointerdown", follow);
  container.addEventListener("pointermove", follow);
  container.addEventListener("pointerleave", (event) => {
    // Touch is exempt, and that exemption is the whole of the touch rule
    // (see CROSSHAIR above): a released touch pointer leaves the stage
    // immediately, so without this the crosshair would be gone before the
    // finger was off the glass.
    if (event.pointerType === "touch") return;
    clear();
  });

  // Called by redraw(), which has just replaced every element the crosshair
  // was painted on; there is nothing to unpaint, only the position to
  // forget. See CROSSHAIR above for why forgetting it is the requirement.
  return { forget: () => { crossed = null; } };
}

// Attach pointer, tool, history and keyboard input to `container` (the
// player's stage, not the table itself — CARD-193: a mirror redraw replaces
// the table, and a listener bound to the table it replaced would stop
// receiving events; `container` survives a redraw, and the cell under a
// point is always read fresh from the live DOM, so these listeners need
// wiring only once, even though the table they act on can change). `player`
// gives the current history (getHistory), says whether the board is locked
// (locked — solved, see PROGRESS), gives the cell a hint would reveal
// (nextHint — a hintCell value or null), paints a board without recording it
// (show — a drag's preview) and records a new history (commit, with the hint
// it recorded, if any), and removes this puzzle's save (forget — after a
// confirmed reset, see SAVE). Returns { refresh,
// commit, getZoom }: refresh re-syncs the controls after the lock changed
// elsewhere; commit records a history from elsewhere (setBoard) exactly as
// an input does; getZoom (CARD-195) is the current zoom percent, read by
// redraw() in start() so a mirror redraw keeps it.
//: The brush each menu item paints, keyed by its data-player-tool (see
//: "menu" above). Region is deliberately absent — it is never a brush, has
//: no cell state, and since CARD-211 is not a menu item at all.
//: These are the labels a HUMAN reads, not the states: UNKNOWN reads "Clear"
//: (CARD-247, owner's doc 2026-10-18) while the state keeps the model's own
//: name, "undecided" (solver_state.js). Renaming a value here renames it in
//: the trigger's visible text and in its "Brush: <label>" accessible name,
//: and nowhere else.
const BRUSH_LABEL = { [FILLED]: "Black", [EMPTY]: "White", [MAYBE]: "Maybe", [UNKNOWN]: "Clear" };

//: What #puzzle-player-announce says about the Region toggle (CARD-211
//: AC-6). The "on" line names what Region will do, because that is the
//: state a screen-reader user cannot see; "off" needs no explanation.
const REGION_ANNOUNCEMENT = {
  true: "Region on: the next drag marks with the brush.",
  false: "Region off.",
};

function wireMarking(container, player) {
  const controls = document.getElementById("puzzle-player-controls");
  const trigger = document.getElementById("puzzle-player-tool-trigger");
  const triggerSwatch = trigger.querySelector(".player-swatch");
  const triggerText = trigger.querySelector("[data-player-trigger-text]");
  const menu = document.getElementById("puzzle-player-tool-menu");
  const items = [...menu.querySelectorAll("[data-player-tool]")];
  // The Region toggle (CARD-211, see "region" above) and the live region its
  // state is announced through (the same one the solved banner and a hint
  // use — start()'s showProgress writes it too, and whichever wrote last
  // wins, which is why only a genuine change is ever written).
  const regionToggle = document.getElementById("puzzle-player-region");
  // The three cells the toggle wears instead of the word "Region"
  // (CARD-247): syncTrigger paints them with the chosen brush. Read with
  // querySelectorAll and not asserted: puzzle_edit.html (CARD-246) loads this
  // same file with a Region toggle that still carries text, where this is
  // empty and syncTrigger's loop simply does nothing.
  const regionCells = [...regionToggle.querySelectorAll(".player-swatch")];
  const announce = document.getElementById("puzzle-player-announce");
  const actions = Object.fromEntries(
    [...controls.querySelectorAll("[data-player-action]")].map((b) => [b.dataset.playerAction, b]));
  // The reset confirmation (see PROGRESS "reset").
  const confirm = document.getElementById("puzzle-player-confirm");
  const keep = confirm.querySelector('[data-player-confirm="cancel"]');
  let tool = FILLED;
  let region = false; // armed? (see "region" above) — never a cell state, never saved
  // The hint ladder (CARD-269, see LADDER above). `rung` is the rung the
  // NEXT Hint press will show, 1..3, and `ladderLine` is the line currently
  // carrying `.is-hint-line` — a {axis, index} VALUE and not the elements
  // showing it, for showHint's and the crosshair's reason: a redraw replaces
  // every element, and refresh() (which redraw() calls last) paints the line
  // back onto the new table. Both are UI state of Region's kind: never a
  // cell state, never recorded, never saved, so a load starts on rung 1 with
  // nothing highlighted (AC-9).
  let rung = RUNG_POINT;
  let ladderLine = null;
  let gesture = null; // { pointerId, start, path, dragging, tool, paints }
  let lastClick = null; // the last recorded click, { row, col, tool } (see MARKING)

  // Zoom (CARD-195, see ZOOM above). `zoom` is a percent, 100..300, view
  // state only — never saved, never reset by anything but a fresh load.
  const zoomOut = controls.querySelector('[data-player-zoom-action="out"]');
  const zoomIn = controls.querySelector('[data-player-zoom-action="in"]');
  const zoomReadout = controls.querySelector("[data-player-zoom-readout]");
  let zoom = ZOOM_MIN;
  // Every active touch/pen pointer's current position ({x, y}, in viewport
  // coordinates) and the board cell it started on (a [row, col] from
  // cellUnder, or null when it started on a clue box or off the board) —
  // kept regardless of `gesture`/Region, purely to recognise and drive a
  // pinch (pinch rule a/d). Never touched for a mouse pointer (rule f).
  const touchPoints = new Map();
  const touchStartCell = new Map();
  // { firstId, secondId, startZoom, startDistance } of the active pinch, or
  // null. Set only by beginPinch; cleared the instant either pointer lifts
  // or cancels (pinch rule b: a pinch that ends with one finger still down
  // marks nothing — covered by `gesture` staying null throughout a pinch,
  // so that finger's own later pointerup falls through to the ordinary
  // "nothing to commit" path once pinch is cleared).
  let pinch = null;

  function distanceBetween(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  // The readout and the buttons' aria-disabled, from the current `zoom`.
  function syncZoom() {
    zoomReadout.textContent = `${Math.round(zoom)}%`;
    zoomOut.setAttribute("aria-disabled", String(zoom <= ZOOM_MIN));
    zoomIn.setAttribute("aria-disabled", String(zoom >= ZOOM_MAX));
  }

  // Moves to `nextPercent` (clamped by the caller's own arithmetic —
  // stepZoom or pinchZoom, never this function), keeping `(anchorX,
  // anchorY)` — a point's offset inside .player-stage's own visible box,
  // not the page's — over the same board point (target behaviour #5,
  // solver_state.js anchoredScroll). A no-op `nextPercent` (already at the
  // clamped end of the range) touches neither the table nor the scroll
  // position, only re-syncs the readout/buttons (idempotent either way).
  function applyZoom(nextPercent, anchorX, anchorY) {
    const old = zoom;
    zoom = nextPercent;
    if (zoom !== old) {
      const table = container.querySelector(".player-board");
      if (table) table.style.setProperty("--player-zoom", String(zoom / 100));
      container.scrollLeft = anchoredScroll(container.scrollLeft, anchorX, old, zoom);
      container.scrollTop = anchoredScroll(container.scrollTop, anchorY, old, zoom);
      // CARD-271: the clue band scales with the cell, so a zoom changes
      // whether either axis can still afford to keep its gutter in view.
      player.zoomed();
    }
    syncZoom();
  }

  // Pinch rule (a)/(b): `firstId` started on a board cell, `secondId` just
  // landed — ends whatever single-pointer gesture was in progress (its
  // preview is reverted, never committed) and starts tracking the pinch
  // from the two pointers' current positions.
  function beginPinch(firstId, secondId) {
    if (gesture) {
      player.show(player.getHistory().board); // revert the preview, commit nothing
      gesture = null;
    }
    lastClick = null;
    pinch = {
      firstId,
      secondId,
      startZoom: zoom,
      // Math.max(…, 1): pinchZoom (solver_state.js) refuses a non-positive
      // starting distance; two fingers reported at the exact same point
      // (not a real pinch, but not impossible from synthetic input) must
      // not throw here instead of simply not zooming yet.
      startDistance: Math.max(distanceBetween(touchPoints.get(firstId), touchPoints.get(secondId)), 1),
    };
    refresh();
  }

  // Pinch rule (c): the current zoom from the two pointers' current
  // positions, anchored on their midpoint (in the stage's own box).
  function pinchMove() {
    const p1 = touchPoints.get(pinch.firstId);
    const p2 = touchPoints.get(pinch.secondId);
    const stageBox = container.getBoundingClientRect();
    const midX = (p1.x + p2.x) / 2 - stageBox.left;
    const midY = (p1.y + p2.y) / 2 - stageBox.top;
    applyZoom(pinchZoom(pinch.startZoom, pinch.startDistance, distanceBetween(p1, p2)), midX, midY);
  }

  // The trigger's name/text and which menu item is checked, from `tool`
  // alone (see "menu" above): since CARD-211 the menu holds brushes only, so
  // Region no longer shows up in either the label or the checked item.
  // Since CARD-247 the Region toggle's three cells are painted from the same
  // `tool` in the same place, so the icon cannot drift from the trigger: one
  // function writes both, and every brush change goes through it (start() and
  // pick() are its only callers). The toggle's own NAME is not touched here —
  // it is a fixed aria-label on the button, because Region's name does not
  // change with the brush (CARD-211: the brush and Region are independent,
  // and the flip is announced through the live region, never by relabelling).
  function syncTrigger() {
    const label = BRUSH_LABEL[tool];
    trigger.setAttribute("aria-label", `Brush: ${label}`);
    triggerSwatch.dataset.state = tool;
    triggerText.textContent = label;
    for (const cell of regionCells) cell.dataset.state = tool;
    for (const item of items) {
      item.setAttribute("aria-checked", String(item.dataset.playerTool === tool));
    }
  }

  // Move Region to `armed` (CARD-211, see "region" above): the toggle's
  // aria-pressed, the board's .is-region class (through refresh(), which is
  // also what re-applies it after a mirror redraw) and one live-region line.
  // A no-op call writes nothing — rewriting the same announcement would make
  // it read out again. Every caller goes through solver_state.js nextRegion,
  // so this function never decides the transition itself.
  function setRegion(armed) {
    if (armed === region) return;
    region = armed;
    regionToggle.setAttribute("aria-pressed", String(region));
    announce.textContent = REGION_ANNOUNCEMENT[String(region)];
    refresh();
  }

  function closeMenu() {
    if (menu.hidden) return;
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
  }

  function openMenu() {
    menu.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    (items.find((item) => item.getAttribute("aria-checked") === "true") ?? items[0]).focus();
  }

  // A menu pick (mouse click, or Enter/Space on a focused item — items are
  // native <button>s, so those keys already fire "click"). Every item is a
  // brush since CARD-211, and picking one restarts the click sequence but
  // leaves Region alone: CARD-194's target behaviour #3 (a brush pick
  // disarms Region) was reversed by the owner on 2026-10-14, so there is no
  // setRegion call here and no "brush" event in nextRegion's table — see
  // nextRegion's divergence note in solver_state.js.
  function pick(name) {
    tool = name;
    lastClick = null;
    syncTrigger();
    closeMenu();
    trigger.focus();
    refresh();
  }

  // One line of the live region AND of the visible answer line — the two
  // channels of every ladder/Check sentence, written together here so the
  // seen one cannot drift from the spoken one (see LADDER above, and
  // showExplain there for what the visible one is and why it is hidden from
  // the accessibility tree). Written straight, with no same-string guard:
  // review F-9's measurement of what a repeated assignment does is in the
  // LADDER block.
  function say(text) {
    announce.textContent = text;
    showExplain(text);
  }

  // Put `.is-hint-line` on (or take it off) every cell and clue box of
  // `line`. The table is read fresh from the live DOM each time, exactly as
  // paintCrosshair does, so this also works right after a redraw. A missing
  // table means nothing to paint, and the direction fails toward NOT
  // painting rather than toward a half-painted line.
  function paintLadderLine(line, on) {
    const table = container.querySelector(".player-board");
    if (table === null) return;
    for (const part of linedParts(table, line.axis, line.index)) {
      part.classList.toggle("is-hint-line", on);
    }
  }

  // Move the highlight to `line` (a hintLine value, or {axis, index} for
  // Check's row), or clear it with null. The old line is unpainted first, so
  // one ladder never leaves two lines lit.
  function setLadderLine(line) {
    if (ladderLine !== null) paintLadderLine(ladderLine, false);
    ladderLine = line === null ? null : { axis: line.axis, index: line.index };
    if (ladderLine !== null) paintLadderLine(ladderLine, true);
  }

  function refresh() {
    const { board: current, done, undone } = player.getHistory();
    const locked = player.locked();
    if (locked) closeMenu(); // the tools' box is hidden while solved (admin.css)
    // Read fresh from the live DOM (not a `table` reference start() keeps):
    // a mirror redraw (CARD-193) replaces the table outright, and refresh()
    // runs again right after one (redraw() calls marking.refresh()), which
    // is what re-applies Region's touch-action class to the new table.
    container.querySelector(".player-board")?.classList.toggle("is-region", region);
    actions.undo.setAttribute("aria-disabled", String(locked || done.length === 0));
    actions.redo.setAttribute("aria-disabled", String(locked || undone.length === 0));
    actions.reset.setAttribute("aria-disabled", String(current.cells.every((s) => s === UNKNOWN)));
    // Optional since CARD-246: the editor's page has no Hint button (see
    // EDIT MODE). `?.` rather than a mode flag of its own — this function
    // reads the DOM it was given and nothing about why.
    actions.hint?.setAttribute("aria-disabled", String(locked || gesture !== null || player.nextHint() === null));
    // CARD-269 rule 9: Check is disabled by the LOCK alone. It reads the
    // board and never changes it, so "nothing to reveal" (which disables
    // Hint) is not a reason to disable it — on a board with no undecided
    // cell left, "is one of my marks wrong?" is exactly the question left to
    // ask. `?.` for Hint's reason: the manual editor's page ships neither
    // control (CARD-246 — there the solution IS what is being rewritten).
    // CARD-269 review F-10: the gesture is in the ATTRIBUTE and not only in
    // the handler. Check's handler has always returned early mid-drag (a
    // drag is one input; a Check in the middle of it would answer about a
    // board the player is still painting), but the attribute said
    // aria-disabled="false" while it did, which is the exact failure mode
    // aria-disabled exists to prevent and is reachable with a second pointer
    // on a touch device. Hint already includes `gesture !== null` above;
    // Check now matches it, and the card's rule 9 reads as the floor it is.
    actions.check?.setAttribute("aria-disabled", String(locked || gesture !== null));
    // The redraw that just replaced every element also took the line
    // highlight off the DOM while `ladderLine` still names it; redraw()
    // calls this function last, so painting it back here is what keeps a
    // rung the reader is standing on visible across a resize.
    if (ladderLine !== null) paintLadderLine(ladderLine, true);
  }

  function commit(next, hint = null) {
    lastClick = null; // anything recorded ends a run of repeat clicks
    // CARD-269: and anything recorded puts the ladder back on rung 1 with
    // nothing highlighted. THIS is the one choke point every recorded change
    // goes through — a click, a drag, undo, redo, a confirmed reset,
    // setBoard, and rung 3's own stroke — which is what makes rungs 1-3 of
    // one ladder always describe one situation (card rule 5). Done before
    // player.commit so rung 3's revealed cell is handed a board with no
    // stale line on it.
    rung = nextRung(rung, "change");
    setLadderLine(null);
    // And the visible answer line goes with the highlight: a sentence about
    // the board as it was is worse than no sentence (CARD-269 review F-2).
    // Cleared BEFORE player.commit, so rung 3's own reveal — which arrives
    // through showProgress's hint branch inside that call — writes its answer
    // over an empty line rather than racing the clear.
    showExplain("");
    player.commit(next, hint);
    if (!confirm.hidden) closeConfirm(); // see PROGRESS "reset"
    refresh();
  }

  container.addEventListener("pointerdown", (event) => {
    // Pinch bookkeeping (CARD-195) runs ahead of — and independently of —
    // the single-pointer gesture logic below, for touch/pen pointers only
    // (rule f): the very first check it would otherwise hit, `if (gesture)
    // return`, would swallow a second finger's pointerdown entirely.
    if (event.pointerType === "touch" || event.pointerType === "pen") {
      if (pinch) return; // a third pointer while a pinch is active: ignored
      const cell = cellUnder(container, event.clientX, event.clientY);
      if (touchPoints.size === 1) {
        // The second touch/pen pointer: pinch rule (a) when the first one
        // started on a board cell, rule (d) — leave it to the browser —
        // otherwise. Either way this pointer never starts its own gesture.
        const [firstId] = touchPoints.keys();
        touchPoints.set(event.pointerId, { x: event.clientX, y: event.clientY });
        touchStartCell.set(event.pointerId, cell);
        if (touchStartCell.get(firstId) !== null) {
          event.preventDefault();
          beginPinch(firstId, event.pointerId);
        }
        return;
      }
      touchPoints.set(event.pointerId, { x: event.clientX, y: event.clientY });
      touchStartCell.set(event.pointerId, cell);
    }
    if (gesture || player.locked() || (event.pointerType === "mouse" && event.button !== 0)) return;
    const start = cellUnder(container, event.clientX, event.clientY);
    if (!start) return;
    // A mouse drag always marks (G-1); a touch or pen drag marks only while
    // Region is on (CARD-194 target behaviour #8/#10, the rule itself in
    // solver_state.js gesturePaints) — captured here, at pointerdown, like
    // the tool itself, so toggling Region mid-gesture (not reachable today —
    // the toggle and the board are different elements) would not
    // retroactively change an in-progress gesture either.
    const paints = gesturePaints(event.pointerType, region);
    if (paints) {
      event.preventDefault();
      container.setPointerCapture(event.pointerId);
    }
    // The tool is taken here, at pointerdown: picking another brush mid-drag
    // applies to the next drag, not this one.
    gesture = { pointerId: event.pointerId, start, path: [], dragging: false, tool, paints };
    refresh(); // Hint is disabled while a gesture is in progress
  });

  container.addEventListener("pointermove", (event) => {
    if (touchPoints.has(event.pointerId)) touchPoints.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pinch && (event.pointerId === pinch.firstId || event.pointerId === pinch.secondId)) {
      event.preventDefault();
      pinchMove();
      return;
    }
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    const position = cellUnder(container, event.clientX, event.clientY);
    const previous = gesture.path.at(-1) ?? gesture.start;
    if (!position || isAt(position, previous)) return;
    // `dragging` is tracked even for a non-painting gesture (touch or pen
    // with Region off): a real device's own pan recognition drops almost
    // every such gesture via pointercancel before it gets this far (see
    // pointercancel below), but that is the browser's call, not a guarantee
    // — nothing here may assume it always fires. Painting the preview is
    // still gated on `paints`.
    gesture.path.push(position);
    gesture.dragging = gesture.dragging || !isAt(position, gesture.start);
    if (gesture.dragging && gesture.paints) {
      player.show(applyStroke(player.getHistory().board, dragStroke(gesture.start, gesture.path, gesture.tool)));
    }
  });

  container.addEventListener("pointerup", (event) => {
    if (touchPoints.has(event.pointerId)) {
      touchPoints.delete(event.pointerId);
      touchStartCell.delete(event.pointerId);
      // Pinch rule (b): the first pointer's later pointerup is ignored, and
      // a pinch that ends with one finger still down marks nothing —
      // either pointer lifting ends the pinch outright, with no commit; the
      // *other* finger, if still down, falls through below with `gesture`
      // still null (beginPinch cleared it), so its own eventual pointerup
      // is the ordinary "nothing to commit" no-op.
      if (pinch && (event.pointerId === pinch.firstId || event.pointerId === pinch.secondId)) {
        pinch = null;
        refresh();
        return;
      }
    }
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    const done = gesture;
    gesture = null;
    const history = player.getHistory();
    if (done.dragging) {
      if (!done.paints) {
        // A touch or pen gesture that left its starting cell but reached
        // pointerup without ever being cancelled (the browser chose not to
        // pan — e.g. nothing on the page can scroll): still not a tap, so
        // still not a click (CARD-194 target behaviour #8/#10 — "a touch
        // tap is still a click", which this is not). No mark either way.
        refresh();
        return;
      }
      // Region turns off the instant a drag is recorded — "a drag ended",
      // not "a cell changed" (CARD-194 target behaviour #7). The toggle's
      // aria-pressed flips back with it, and the disarm is announced, so a
      // screen-reader user is not left believing Region is still armed.
      // Announced BEFORE the commit on purpose: a drag that solves the board
      // lets showProgress overwrite this line with the solved banner, which
      // is the more important of the two.
      setRegion(nextRegion(region, "drag"));
      commit(record(history, dragStroke(done.start, done.path, done.tool)));
      return;
    }
    const [row, col] = done.start;
    const repeat = lastClick !== null && lastClick.row === row && lastClick.col === col
      && lastClick.tool === done.tool;
    commit(record(history, clickStroke(history.board, row, col, done.tool, repeat)));
    lastClick = { row, col, tool: done.tool };
  });

  container.addEventListener("pointercancel", (event) => {
    if (touchPoints.has(event.pointerId)) {
      touchPoints.delete(event.pointerId);
      touchStartCell.delete(event.pointerId);
      if (pinch && (event.pointerId === pinch.firstId || event.pointerId === pinch.secondId)) {
        pinch = null;
        refresh();
        return;
      }
    }
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    gesture = null;
    lastClick = null;
    player.show(player.getHistory().board);
    refresh();
  });

  zoomOut.addEventListener("click", () => {
    applyZoom(stepZoom(zoom, "out"), container.clientWidth / 2, container.clientHeight / 2);
  });
  zoomIn.addEventListener("click", () => {
    applyZoom(stepZoom(zoom, "in"), container.clientWidth / 2, container.clientHeight / 2);
  });

  trigger.addEventListener("click", () => {
    if (menu.hidden) openMenu();
    else closeMenu();
  });
  trigger.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowDown" || !menu.hidden) return;
    event.preventDefault();
    openMenu();
  });
  menu.addEventListener("keydown", (event) => {
    const at = items.indexOf(document.activeElement);
    if (at === -1) return;
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        items[(at + 1) % items.length].focus();
        break;
      case "ArrowUp":
        event.preventDefault();
        items[(at - 1 + items.length) % items.length].focus();
        break;
      case "Home":
        event.preventDefault();
        items[0].focus();
        break;
      case "End":
        event.preventDefault();
        items[items.length - 1].focus();
        break;
      case "Escape":
        event.preventDefault();
        closeMenu();
        trigger.focus();
        break;
      case "Tab":
        // Not prevented: the item closeMenu() hides is the current focus,
        // so the browser's own Tab handling lands on the next focusable
        // control after it in the (now updated) DOM — Region (then Undo),
        // since CARD-211 put the toggle between the trigger and the history
        // buttons.
        closeMenu();
        break;
      default:
        break;
    }
  });
  for (const item of items) {
    item.addEventListener("click", () => pick(item.dataset.playerTool));
  }

  // The Region toggle (CARD-211, see "region" above). A native <button>, so
  // Enter and Space already arrive as "click" — no keydown handler of its
  // own, and no focus move: pressing it leaves focus on it, the way a toggle
  // should. It never touches `tool` or `lastClick`.
  regionToggle.addEventListener("click", () => setRegion(nextRegion(region, "toggle")));

  // Undo and redo change nothing while the board is locked (solved).
  const step = {
    undo: () => (player.locked() ? player.getHistory() : undo(player.getHistory())),
    redo: () => (player.locked() ? player.getHistory() : redo(player.getHistory())),
  };
  for (const name of ["undo", "redo"]) {
    actions[name].addEventListener("click", () => {
      if (!gesture) commit(step[name]());
    });
  }

  // The hint ladder (CARD-269, see LADDER above). One button, three
  // answers to the same situation: rung 1 points at a line, rung 2 adds the
  // checked reason, rung 3 is CARD-183's reveal unchanged — the same
  // hintStroke, the same `.is-hinted`, the same hintText, the same counter,
  // the same one undo step, the same save (G-3). Only rung 3 calls commit,
  // which is also what puts the ladder back on rung 1.
  actions.hint?.addEventListener("click", () => {
    if (gesture || player.locked()) return;
    const hint = player.nextHint();
    if (hint === null) return;
    // A press is an INPUT, so it ends a run of repeat clicks even on rungs 1
    // and 2, which record nothing — the same rule the reset confirmation
    // follows ("opening the confirmation is an input", see MARKING). Without
    // this a click, a click, a nudge, a click would read as a third repeat
    // click on that cell, which is pinned by
    // tests/test_puzzle_solver_marking.py
    // TestSolverClickFollowsTheBrush::test_anything_between_two_clicks_makes_the_next_a_first_click
    // and is the behaviour CARD-183's reveal had for free, through commit.
    lastClick = null;
    if (rung === RUNG_REVEAL) {
      commit(record(player.getHistory(), hintStroke(hint.row, hint.col, hint.state)), hint);
      return;
    }
    const showing = rung;
    rung = nextRung(rung, "press");
    // null is the exhausted state: no line to point at, so nothing is
    // highlighted and the sentence says exactly that (see LADDER_EXHAUSTED).
    const line = player.hintLine(hint);
    setLadderLine(line);
    if (line === null) {
      say(LADDER_EXHAUSTED);
      return;
    }
    const sentence = LADDER_SAY[showing];
    if (sentence === undefined) {
      throw new RangeError(`rung ${showing} announces no line (${Object.keys(LADDER_SAY).join(", ")})`);
    }
    say(sentence(line));
  });

  // Check (CARD-269 rule 7): the row of the first wrong mark, or that there
  // is none. It changes no cell, records no stroke and moves no counter, so
  // it never calls commit — but it DOES reset the ladder, because it changes
  // what the player will look at next, and its highlight is rung 1's and
  // clears the same way (the next recorded change, or the next ladder press).
  actions.check?.addEventListener("click", () => {
    if (gesture || player.locked()) return;
    lastClick = null; // an input, like a ladder press (see the Hint handler)
    rung = nextRung(rung, "change");
    const row = player.wrongRow();
    setLadderLine(row === null ? null : { axis: "row", index: row });
    say(checkText(row));
  });

  // Reset asks first, in the page (see PROGRESS "reset").
  function closeConfirm() {
    confirm.hidden = true;
    actions.reset.setAttribute("aria-expanded", "false");
    actions.reset.focus();
  }
  actions.reset.addEventListener("click", () => {
    if (gesture || actions.reset.getAttribute("aria-disabled") === "true") return;
    lastClick = null; // opening the confirmation is an input (see MARKING)
    confirm.hidden = false;
    actions.reset.setAttribute("aria-expanded", "true");
    keep.focus();
  });
  // commit closes the confirmation (and returns focus to Reset).
  confirm.querySelector('[data-player-confirm="accept"]').addEventListener("click", () => {
    commit(record(player.getHistory(), resetStroke(player.getHistory().board)));
    player.forget(); // a confirmed reset clears the save (see SAVE)
  });
  keep.addEventListener("click", closeConfirm);
  confirm.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    closeConfirm();
  });

  // The Z key: event.key "z"/"Z", or — when the layout gives that key a
  // non-Latin character (e.g. Russian "я") — event.code "KeyZ". A layout that
  // puts another Latin letter on the KeyZ position (German "y") is matched by
  // its letter, so Ctrl+Y there does not undo.
  function isZ(event) {
    const key = event.key.toLowerCase();
    return key === "z" || (!/^[a-z]$/.test(key) && event.code === "KeyZ");
  }

  document.addEventListener("keydown", (event) => {
    if (gesture || !(event.ctrlKey || event.metaKey) || event.altKey || !isZ(event)) return;
    event.preventDefault();
    commit(event.shiftKey ? step.redo() : step.undo());
  });

  syncTrigger();
  refresh();
  syncZoom();
  controls.hidden = false;
  document.getElementById("puzzle-player-hint").hidden = false;
  // The visible answer line (CARD-269 review F-2) is shown with the toolbar
  // and for the toolbar's reason: it is one line box tall even while empty,
  // and a blank strip beside the title of a board that never got drawn would
  // be furniture promising a control that is not there. Optional for
  // puzzle_edit.html's sake, like the Hint and Check buttons.
  const explainLine = document.getElementById("puzzle-player-explain");
  if (explainLine !== null) explainLine.hidden = false;
  return { refresh, commit, getZoom: () => zoom };
}

start();
