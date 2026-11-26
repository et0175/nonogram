# 11 — The public player (CAP-007 / FR-045)

> **Rewritten whole on 2026-11-26** against the code as shipped that day. The page
> it replaces described `player/play.js`, a second implementation of the player
> that CARD-399 deleted on 2026-11-08; since then `/play/<key>` is the admin
> player's own `solver.js` running in public mode. This page cites code **by
> name** (a constant, a function, a test) and never by line number or line count:
> both went stale within a week the last time they were written down.

> Scope: the top-level `player/` tree — `assemble.py` (which writes the deployable
> site and generates the play page), `pages.js` and `player.css` (the library and
> the book landing), `how-to-solve.html` / `how-to-solve.js` (the lesson),
> `decor.js` / `decor.css` (a themed book's decorations), `library.html`,
> `book.html`, `vercel.json` — plus the five files copied byte for byte from
> `src/nonogram/admin/static/` and the exporter that feeds it all,
> `admin/player_bundle.py` (COMP-009). Component **COMP-011**, governed by
> ADR-0041.

## Why there are two players

[08](08-playing-a-stored-puzzle.md) describes the admin panel's puzzle player.
CON-021 allows interactive play in exactly two forms:

> Interactive play in exactly two forms — the admin panel's puzzle player (behind
> CON-015/CON-016, may ship the solution) and the public player per ADR-0041
> (static, read-only, no accounts, localStorage-only, never ships a solution);
> everything else forbidden, no server-persisted play state anywhere.

FR-045 is the second form. Its reason is printed: a book carries a QR code, and a
QR code needs something to point at that is not behind the panel's credentialed
door. Both players are CAP-007.

"Two players" is two **pages**, not two implementations. The owner ruled on
2026-11-06 that the public page runs the admin's player rather than a copy of it,
and since CARD-399 there is one board, one toolbar and one set of rules: the
admin's `solver.js`, `solver_state.js` and `admin.css`. What differs is the
**mode** the page starts in, and that is the subject of the next two sections.

**COMP-011 is the first component whose code lives outside `src/nonogram/`**, so
ADR-0007's import guard, which walks `src/nonogram/**/*.py`, does not see it. The
dependency direction is kept here by the tree having no Python at all except an
assembler that imports nothing from the package by name.

## The two URLs are content hashes, and one of them deliberately ignores the title

A printed QR code cannot be re-pointed. Everything in ADR-0041's URL design falls
out of that sentence.

| URL | Derived from | Rule |
|---|---|---|
| `/play/<key>` | first 10 hex characters of SHA-256 over `"{width}x{height}:"` + the solution grid row-major, `1`/`0` | R1, `player_bundle.puzzle_key` |
| `/b/<slug>` | first 10 hex of SHA-256 over `"book:"` + the book's puzzle keys in book order, concatenated | R7, `player_bundle.book_slug` |

Both are *content* addresses, chosen over a stored opaque slug for a stated
reason: a stored slug "is stable only as long as the database and its backups
are", while a printed book preserves its puzzles forever, so a hash of the content
survives a re-seed. Keys are 10 characters each (`KEY_LENGTH`), which is
why the slug concatenates them with no separator and is still unambiguous.

The slug takes **no title**, and `book_slug`'s signature does not accept one —
"the only version of 'not an input' a caller cannot get wrong". A title is
editorial; hashing it would mean a typo fix in the panel silently breaking every QR
code in a printed run. Owner decision of 2026-10-24, taken explicitly against the
`"book:{title}:"` form CARD-282 had already implemented.

What the slug *does* move with is membership: a book whose puzzle set or order
changes is a different content and gets a different URL. INV-012 already makes a
membership change on a book that has left draft an explicit act (it returns the
book to draft — see [07](07-book-assembly-and-the-admin-panel.md)), so the
sensitivity is bounded by a gate that already existed.

## The page never has the answer

ADR-0038/R6 lets the panel ship the solution grid because it sits behind the
door; ADR-0041/R2 forbids it for anything public. The public page's payload is
`{ id, width, height, rows, columns, mode: "public", tier }` and has **no
`solution` key**.

Public mode is mechanical, not a convention (`solver.js`, "PUBLIC MODE"):

- **A payload that carries a solution is refused** (`readPayload`), and at start
  `payload.solution` is replaced with a getter that throws. A reader of the answer
  that is not gated by the mode is a page error on the first gesture that reaches
  it, never a tolerated `null`. `tests/test_player_public_mode.py` sweeps every
  control to hold that.
- **Solved is clue satisfaction.** `isClueSolved` asks whether every row and
  column clue is satisfied by the black cells. Every published puzzle has exactly
  one solution (CON-005/INV-002), so that is the same fact as "equals the
  solution". The solved banner, the lock and a probe's auto-commit all ask it.
- **Errors, Progress and Check are absent, not inert.** Each is a statement about
  the answer, so `start()` removes their elements before anything is wired
  (owner, 2026-10-30). The template stays the admin's one file.
- **The hint is derived, never revealed** — see [the hint](#the-hint-is-derived-from-the-clues-and-never-reveals-the-answer).
- **The save carries a constant stamp** where the admin's carries the solution's
  fingerprint — see [play state](#play-state-is-this-browsers-and-nothing-elses).

## One player, copied byte for byte

ADR-0041/R3 requires the shared files to be **copied**, never edited for the
public site and never imported across. `assemble.py`'s `COPIED_FROM_ADMIN` is the
table: `solver.js`, `solver_state.js`, `admin.css`, `tokens.css` and
`favicon.png`, each written to the site exactly as it is in
`src/nonogram/admin/static/`. The equality is checked when the copy is made and
again from the test tree (`tests/test_player_shared_ui_site.py`,
`TestSharedUi_ByteIdentity`), so the two cannot drift: a change to the player is
made once, in the admin's files, and reaches the public site at the next
assembly.

The play page itself is **generated**. `assemble.py`'s `shared_ui_play_page`
renders the admin's own `puzzle_solve.html` fragment into a static shell
(`play/index.html`) with a small inline loader. The loader reads the key from the
path, fetches `puzzle/<key>.json`, writes the payload element, and imports
`/solver.js`. Opened from a book (`?book=<slug>`) it also fetches
`book/<slug>.json` and adds what only a book gives a puzzle:

- the heading **Puzzle N** (its print number in the book) with the size beside it,
  and the book's title in the browser tab;
- the way back, "← <book>" beside the title ("← Book" on a compact screen). When
  the puzzle was opened from the book page it is the browser's own Back to that
  entry (`returnsToBook`), so the book reopens as the reader left it;
- after a solve, **Next puzzle** and **Back to the book** (`wayOn`);
- the book's theme, and for a decorated theme its garland (`decor.js`);
- the link to the lesson, on the How to play line and at the end of its list.

`base.css` (from `player/shared-ui-base.css`) stands in for the Bootstrap file the
panel loads; `tests/test_player_base_css.py` holds the page's computed styles to a
measurement taken against the real file.

## What the public page offers

Everything on this list is the admin player's own control, behaving as
[08](08-playing-a-stored-puzzle.md) describes. Only the differences are noted.

| Control | On the public page |
|---|---|
| **Tap / click** | The brush's cycle: with Black, black → white (dot) → blank. |
| **Brush** | Black, White, Maybe (`?`), Clear. |
| **Region** | A touch or pen drag marks only while Region is on; a mouse drag always marks. On while the whole board is in view; once the board is zoomed past the stage, a drag pans and Region is armed by its button for one drag. Press and hold a cell, then tap another on its row or column, to paint the stretch between. |
| **Undo / Redo / Reset** | One drag is one step. Reset asks first, and Undo brings the board back. |
| **Line** | On a compact screen: one row or column in big squares (below). |
| **Hint** | Three presses: where to look, why, then the cell. Derived from the clues (below). |
| **Probe** | A guess that can be kept or taken back whole. **Not offered on an Easy puzzle** (below). |
| **Zoom** | − / readout / +, one pill. 100% to 300% in 25-point steps, plus **Fit** when the board does not fit at 100%. |
| **Crosshair** | The row and column of the cell under the pointer or the last touch are tinted, with their clues. |
| **Circles** | A clue number the marks settle is circled (below). |
| **Counters** | Only "Revealed", the number of hint cells. No error count and no progress percent. |
| **Show grid** | After a solve, shows the finished picture with or without the grid. |
| **How to play** | A closed list under the board, the same words the lesson's buttons step uses. |

The keyboard works as in the panel: the arrow keys move a cursor, Space marks,
and on a computer the right mouse button puts White whatever the brush.

### Sizing and zoom

A cell is sized to fit the stage, between a floor and a cap. The cap is 28 px in
the panel, 36 px on a phone and **64 px on the public desktop page**, where the
window's height is what bounds the board: a small puzzle fills the window instead
of sitting in its corner (owner, 2026-11-23). Clue numerals stop at 14 px, so
past that only the cells grow.

Zoom multiplies the fitted cell (`--player-zoom`). It is a view: it changes no
board state, is never saved, and starts at 100% on every load — or at **Fit** for
a board that does not fit a compact screen. The arithmetic is `solver_state.js`'s
(`stepZoom`, `pinchZoom`, `fitZoom`, `anchoredScroll`); the page only reads the
pointers and the scroll position.

- **Pinch.** Two fingers anywhere on the stage, cells or clue boxes, are the
  board's pinch. Below 100% a pinch has the buttons' two stops and nothing between
  them: 100%, then Fit.
- **The browser's own zoom is off on the board.** The play page declares
  `user-scalable=no`, the stage takes `touch-action: pan-x pan-y`, and WebKit's
  `gesturestart`/`gesturechange` are cancelled there, because iOS Safari ignores
  the first of those and its pinch-in opens the tab overview.
- **A pan keeps to its axis.** Safari pans a scroller diagonally; the first few
  pixels of a one-finger pan pick an axis and the other is held until the scroll
  ends. Chrome does this itself.
- A double tap never zooms the page.

Not observed on a real iPhone: there is no iOS simulator on the machine the
Safari-specific parts were written on, so they are checked by script in Chromium
and by the owner's phone after each publish.

### Line view

On a compact screen (600 px wide or 500 px tall, or less) the **Line** button
opens one row or column as one or two strips of big squares, with its clue and a
small map of the whole board. Tapping the map or the arrows picks a line;
**Rows / Cols** switches direction; a long press on a square jumps to the line
that crosses it there. Marks are ordinary recorded strokes, so Undo, the save,
Hint and Probe all see them. The view reopens on the direction it was last on,
through the last cell touched. **Board** (an arrow alone under 375 px) goes back.

## Circled clue numbers: the readout that needs no answer

> The table at the end of this section is executed: `tests/test_puzzle_solver_clues.py`'s
> `test_the_documented_circle_cases_are_what_the_player_does` reads every row out
> of this file and holds the player's `circledNumbers`, and the test tree's own
> second implementation of the rules, to it.

A clue number is circled when the player's **marks** settle it. Which numbers is
decided by `solver_state.js`'s `circledNumbers` (one line) and `circledClues` (the
whole board): they take the board and the clues, never a solution, so the public
page can run them, and the admin player calls the very same functions. `solver.js`
only carries the answer to the page: after every recorded change it sets or
removes `.is-circled` on each number.

### The words

In one row or column a cell is **black**, **white** (the dot), or **undecided**.
A blank cell and a Maybe (`?`) are both undecided: a `?` never closes a run.

A **run** is a stretch of black cells with no gap. A run is **closed** when the
cell on each side of it is a white dot or the edge of the board. A run beside a
blank or a `?` is **open**, and an open run never circles anything.

### When a number is circled

A number is circled when any one of these holds. Each line is read by itself.

- **A. Counted in from an edge.** Start at one end of the line and walk inward.
  White dots are skipped. The first closed run met is the first clue number from
  that end if its length matches; circle it and walk on to the next run and the
  next number. The walk stops at the first undecided cell, the first open run, or
  the first run of the wrong length. Both ends are walked, separately.
- **B. The whole line is there.** Every run on the line is closed, and their
  lengths, in order, are exactly the clue. Every number is circled, even when
  undecided cells remain between the runs.
- **C. The only number of that size.** The number's value occurs once in this
  line's clue, and the line holds exactly one closed run of that length. No other
  number could own that run, so it is circled wherever it stands.
- **E. The only number with room there.** The run's length occurs more than once
  in the clue, but only one of those numbers leaves room for the numbers before it
  (each with a gap) to its left and the numbers after it to its right. That one is
  circled. In `2 2 2` on ten cells, a closed pair on cells 6 and 7 can only be the
  middle 2.
- **The clue `0`.** Circled only when every cell of the line is a white dot.

(There is no rule D. It circled numbers pinned by the marks without a closed run;
the owner withdrew it on 2026-11-12: a circle appears only beside dots or the
edge.)

### When the circle goes away

The circles are worked out again from scratch after every recorded change, so a
number loses its circle the moment none of the rules above holds for it any more.
In practice:

- a dot beside the run is cleared or turned into `?`, so the run is open again;
- the run grows or shrinks by a cell, so its length no longer matches;
- a second closed run of the same length appears where rule C needed exactly one;
- a mark elsewhere stops rule A's walk earlier, or breaks rule B's "exactly the
  clue", and no other rule still covers the number;
- **Undo** takes back the mark that completed it; **Redo** brings it back;
- **Reset** clears the board, so every circle goes (a `0` clue included);
- **Wrong guess** removes a probe's marks, and the circles they made go with them.
  Probe marks count like any other mark while the probe is open, and **Keep**
  leaves the circles as they are.

A drag does not circle anything until the finger or the button is lifted: circles
follow recorded marks, never a preview.

### Circled is not "correct"

The rules read the player's marks, not the answer. Marks that are wrong but
agree with each other can circle a number (rows X2 and X3 below), and a line with
every number circled can still be wrong. Whether the board is solved is decided
separately, by an exact check of every line against its clue.

### The cases

`D` is black, `W` a white dot, `.` blank, `?` Maybe. Every line has ten cells.
In the last-but-one column the circled numbers are in brackets.

| Case | Clue | Marks | Circled | Why |
|---|---|---|---|---|
| A1 | 3 2 | `DDDW......` | `[3] 2` | The first run is closed by the edge and a dot: rule A from the left. |
| A2 | 3 2 | `DDD.......` | `3 2` | The dot is gone: the run is open, the circle goes. |
| A3 | 3 2 | `DDD?......` | `3 2` | A `?` is not a dot. |
| A4 | 3 2 | `.DDDW.....` | `3 2` | A blank before the run: the walk cannot pass it and the run is open. |
| A5 | 3 2 | `WDDDW.....` | `[3] 2` | Dots before the run are skipped. |
| A6 | 3 2 | `......WDDW` | `3 [2]` | The same walk from the right end. |
| A7 | 3 2 | `DDDW...WDD` | `[3] [2]` | Both walks, each from its own end. |
| A8 | 1 1 3 | `DWDW......` | `[1] [1] 3` | The walk goes on past one closed run to the next. |
| A9 | 1 1 3 | `DW.DW.....` | `[1] 1 3` | It stops at the blank; the second 1 is open on its left. |
| A10 | 3 2 | `DDDDW.....` | `3 2` | One cell too many: a closed 4 is neither number. |
| B1 | 1 1 | `.WDW.WDW..` | `[1] [1]` | Every run closed and the runs are exactly the clue: rule B. |
| B2 | 1 1 | `.WD..WDW..` | `1 1` | One dot cleared: a run is open, so rule B no longer holds. |
| B3 | 1 1 | `.WDW.WDW.D` | `1 1` | A third, open run: the line is not exactly the clue. |
| C1 | 1 4 2 | `...WDDDDW.` | `1 [4] 2` | The only 4 in the clue, the only closed 4 on the line: rule C. |
| C2 | 1 4 2 | `...WDDDD..` | `1 4 2` | The same run, open on one side. |
| C3 | 1 4 2 | `DDDDWDDDDW` | `1 4 2` | Two closed 4s contradict each other: neither is circled. |
| C4 | 1 1 | `...WDW....` | `1 1` | A repeated value, and either 1 has room there: nothing to choose by. |
| E1 | 2 2 2 | `.D..WDDW.D` | `2 [2] 2` | Only the middle 2 has room on both sides: rule E. |
| E2 | 2 2 2 | `.D..WDD..D` | `2 2 2` | The dot after it cleared: open, the circle goes. |
| E3 | 2 2 2 | `WDDWWDDWDD` | `[2] [2] [2]` | The outer runs closed too: the walks circle all three. |
| E4 | 2 3 2 | `....WDDW..` | `2 3 2` | Neither 2 has room there, so the marks fit no number. |
| Z1 | 0 | `WWWWWWWWWW` | `[0]` | A `0` line, every cell dotted. |
| Z2 | 0 | `WWWW.WWWWW` | `0` | One cell still blank. |
| Z3 | 0 | `WWWWDWWWWW` | `0` | A black cell on a `0` line. |
| X1 | 3 2 | `DDDWWWWWDD` | `[3] [2]` | The finished line. |
| X2 | 3 2 | `DDWWWWWDDD` | `[3] [2]` | Wrong order, yet each run is the only one of its size (rule C): circled is not correct. |
| X3 | 3 2 | `DDW.......` | `3 [2]` | A closed 2 at the wrong end is still the only closed 2: rule C circles it. |
| X4 | 3 2 | `..........` | `3 2` | Nothing marked, nothing circled. |

What the page does with the answer (the events, not the rules) is held on a real
board by `TestSolverClues_CirclesFollowEveryCommit` in
`tests/test_puzzle_solver_clues.py` (drag, click, Undo, Redo, Reset, and no circle
before release) and by the probe tests in `tests/test_puzzle_solver_probe.py`.

The ring is a **border** drawn around the number, not a background, so the
crosshair's tint on the clue box cannot hide it. On a board wide or tall enough to
repeat its clues on both sides, both copies of a number circle together.

## The hint is derived from the clues, and never reveals the answer

`hintCell` and `hintLine` are called with a `null` solution. The deduction they
rest on, `lineForced`, takes a clue and a line and nothing else: it returns the
cells every placement of the clue that fits the marks agrees on. The hint is the
first undecided cell that some row or column forces, read from the board **as the
player has it**.

The ladder is three presses on one situation: the line is pointed at and lit, then
the reason is said, then **one** hint stroke is recorded — one undo step, counted
in "Revealed" off the undo stack. Any recorded change puts the ladder back on its
first rung.

Three things differ from the panel, all because there is no answer to consult:

- **No fallback.** When no line forces a cell, the panel reveals one from the
  solution. The public page says, at every press, that the clues decide nothing
  more by themselves (`PUBLIC_EXHAUSTED`), records nothing and counts nothing.
  Hint stays enabled while any cell is undecided, so that sentence can be reached.
  This is where **Probe** is the way on.
- **Wrong marks are not ignored.** The page cannot tell a wrong mark from a right
  one, so a hint may follow from a wrong mark.
- **A broken line is named first.** If the marks already make some row or column
  impossible, Hint says which (`brokenLine`) before pointing anywhere else. That
  is solution-free: it is a statement about the marks and the clue.

**Why this is not an ADR-0041/R2 problem**: R2 is read as a rule about what an
*asset carries*, not about what a browser can compute from clues it already has
(owner ruling, 2026-11-06). `puzzle/<key>.json` is unchanged by any number of
hints, and every published puzzle is uniquely solvable, which is why the clues
already determine every cell.

## Probe: a guess that is kept or taken back whole

A solver who cannot deduce further makes a group of marks under one hypothesis
and then keeps them all or reverts them all. That is a transaction over the
history, not a cell state: `CELL_STATES` stays four members, and which marks
belong to the probe is derived from the history's strokes (`probeCells`), never
stored per cell. The whole transaction is in the shared module and takes no
solution (`nextProbe`, `abandonProbe`, `checkpointHistory`, `brokenLines`).

On the page: **Probe** becomes **✓ Keep** and **✗ Wrong guess** while a probe is
open. Marks made inside it carry a dashed edge, a dashed frame is drawn round the
board's visible part, and a one-line note says "Probing · ✓ Keep · ✗ Wrong
guess". After **Wrong guess** on a probe that began with one cell, the page offers
to mark that cell the other colour.

| | Rule |
|---|---|
| 1 | **Depth 1** — at most one probe open |
| 2 | Probe opens at the current history position |
| 3 | While open, every mark made belongs to it and takes the dashed look |
| 4 | **Wrong guess** undoes back to the checkpoint: the board is exactly as at probe start, and the probe closes |
| 5 | **Keep** drops the look and closes the probe; it touches no cell |
| 6 | Undo/redo stay LIFO; undoing past the open position empties the probe and leaves it open, and a redo of a pre-probe stroke stays outside it |
| 7 | A probe whose marks reach the solved state **commits** |
| 8 | The circles read the board as it is, probe marks included |
| 9 | The save never contains probe strokes, so leaving the page abandons an open probe |
| 10 | Reset clears the board, the history and any open probe |

Two public-page specifics:

- **Hint inside a probe reveals no cell** (CARD-435). It names the rows and
  columns the guess has already broken, turns their clues red and flags Wrong
  guess. A line is never called broken until the reader asks.
- **An Easy puzzle has no Probe** (owner, 2026-11-24). Easy means the simplest
  overlap rule finishes the puzzle (`simple_overlap` in
  `docs/GENERATION_ALGORITHM.md`), so a probe is never needed there. The payload's
  `tier` is what tells the page; `probeOffered` hides the button and How to play's
  Probe line. The panel's payload names no tier and keeps Probe everywhere.

Rule 7 is the one place the panel consults the answer; here "solved" is
`isClueSolved`, the same fact for a uniquely solvable puzzle. Without the
auto-commit a reader who finished the picture inside a probe would lose the
finishing marks on a reload (rule 9).

## Solving

When the last cell falls into place the board locks, the solved banner appears,
the filled cells sweep through the success colour once, and the toolbar offers
**Show grid**. Under `prefers-reduced-motion` the sweep is off and the banner
still appears. In a book, **Next puzzle** and **Back to the book** follow the
board.

## Play state is this browser's and nothing else's

One `localStorage` entry per puzzle, under `nonogram-player:<key>`
(`solver_state.js` `saveKey`) — the panel's own key and format, with the constant
`PUBLIC_GRID` stamp where the panel's save fingerprints the solution. The save is
the undo history; it carries hint strokes (so "Revealed" survives a reload) and
never probe strokes. Zoom, the brush, Region and the line view's direction are
not saved. Saves written by the retired `play.js` under `nonogram-public:<key>`
are left alone and not read.

The listing pages read the same entries, read-only, to draw progress.

There is no account, no server-side state and **no write request of any kind**:
the play page fetches its puzzle file, and its book file when opened from a book,
and nothing else. The player's files contain no network call at all, which
`tests/test_player_public_mode.py`'s `TestPublicMode_NoNetworkInAnyMode` and
`tests/test_player_shared_ui_site.py` hold over the source and over the copied
files.

## The pages around the player

- **`/b/<slug>` — the book landing**, the page a printed QR code opens. It renders
  from `book/<slug>.json` alone: the series, title and authors, a link to the
  lesson, a **Continue** card, a "Which puzzle are you on?" box that jumps to a
  print number, and the puzzles as numbered squares. A book of more than
  `OPEN_ALL_UP_TO` puzzles is cut into level sections that open and close; only
  the section holding the Continue puzzle starts open (the first Easy section
  when nothing is started). **Continue** is the started, unsolved puzzle with the
  highest print number: a save carries no time, so "most recent" is not knowable.
  Each square shows its size and the reader's progress, a thumbnail of the marks
  included.

  The reader's view — which sections are open, and the scroll — is kept in the
  page's own history entry (`history.replaceState`, `VIEW_STATE`), so a Back onto
  it, restored from the back/forward cache or loaded afresh, finds it as it was.
  A new visit gets the defaults. One gap is known and left: a reader who went on
  with **Next puzzle** returns by a new entry and gets the defaults. Closing it
  needs browser storage, which the served-tree scan forbids on these pages.
- **`/library`** lists every published puzzle with level and size filters.
- **`/how-to-solve`** is the lesson, one page for every book, seven steps: the
  rules with a board to try; the squeeze, with an exercise and a way out for the
  reader who came for the Easy puzzles; finding what is certain, with an exercise;
  the buttons; a guided probe; Line mode; the levels. Its figures are computed
  from the lesson's own `arrangements`, so a picture cannot disagree with the
  clue it shows. Opened from a book it wears that book's theme, and its way back
  is that book.
- **Themes.** `SERVED_BOOK_THEMES` is the closed set (`christmas` today). A theme
  dresses the book landing, the puzzles opened from it and the lesson opened from
  it; it is online only and changes nothing in print.

## What the site is, and what is rebuilt rather than copied

See [diagrams/11-bundle-to-site.puml](diagrams/11-bundle-to-site.puml) for the
whole path, database to visitor, and where the solution stops on it.

`assemble.py` writes the deployable tree: the hand-written pages and their
scripts and styles (`PLAYER_FILES`), the generated play page, the five copies
from the panel (`COPIED_FROM_ADMIN`), `vercel.json`, a `.player-site` marker
(`SITE_MARKER_FILE`) that is how the script recognises its own output before
deleting it, and — rebuilt from the bundle — one `puzzle/<key>.json` per puzzle,
`index.json`, and one `book/<slug>.json` per book.

The rebuild is the point, and it is load-bearing for R2. CARD-282 shipped the
exporter and then measured a path straight through it: an owner renames a puzzle to
the base-64 of its own packed grid, the exporter writes that string into the
bundle's declared `title`, every guard passes, and the published JSON decodes back
to all 144 cells of a 12×12 answer. A scan cannot fix that — the set of encodings
of a grid is not enumerable, and CARD-282's denylist missed 7 of 7 planted
encodings. So the assembler does not filter free text; it **removes the channel**:
every served puzzle file is rebuilt from `SERVED_SCHEMA`, which is
`("clues", "height", "key", "tier", "width")`, and a puzzle's `title` is in no
served schema at all. A field the schema does not name is dropped, named in the
report, and never written — the run prints `dropped (not in the served schema):
title`.

What is left is held to EC-048 by two statements that do different work:

- `clues` and `key` are **exempt**, not safe-by-measurement
  (`EXEMPT_SERVED_FIELDS`): ADR-0041/R2 grants the exemption and R5 — the
  exporter taking every clue from `compute_clues` of the stored grid, upstream —
  is where their integrity actually lives;
- every other served value is drawn from a domain the module enumerates
  (`SERVED_VALUE_SPACE`), with `width`/`height` recomputable from the
  clues, and `check_capacity` refuses to assemble unless the total free
  capacity is strictly below `MIN_SIZE * MIN_SIZE` bits.

A **book's** `title` is a different field and is *not* removed: the owner granted it
R2's third exemption on 2026-10-28, since widened to its `series` and `authors`
(`EXEMPT_LISTING_FIELDS`), scoped to the served `book/<slug>.json` schema
(`SERVED_BOOK_SCHEMA`) and to no other, with its residual declared rather than
bounded — R2's own text measures it at 100 of 100 cells recoverable if an owner
writes a base-64 grid into a book title. "This script removes the free-text channel"
is therefore false as a sentence about the whole site, and `assemble.py` says so
about itself.

The scope is that **schema**, not the set of pages the string is shown on: R2's
2026-10-28(b) amendment struck its own "and nowhere else" clause. The title is shown
on `/b/<slug>`'s `h1` and, since CARD-436, in the header of a `/play/<key>` opened
from that book, where it names the way back, and in both pages' browser tab. That
page already fetches `book/<slug>.json` for the theme, so this adds no served
field, no request and no character — the declared residual above is unchanged.

## Four doors, one document each

`vercel.json`'s rewrites are the host's whole routing table, and the test
fixtures and `scripts/preview_player_site.py` route by reading that file:

| URL | Serves | Why a rewrite |
|---|---|---|
| `/play/<key>` | `play/index.html` | one document plays every puzzle; its loader reads the key out of the path |
| `/b/<slug>` | `b/index.html` | the QR landing for one book |
| `/library` | `library/index.html` | the extensionless path needs the rule |
| `/how-to-solve` | `how-to-solve/index.html` | the same |

## Bounds and honest gaps

- **The published site lags `main` on purpose.** Nothing publishes by itself: a
  publish is an explicit owner "publish", recorded in `docs/deploy/player.md`
  with the commit, the files that changed and the rollback target. Production is
  `https://nonogram.adverax.io`.
- **Real phones are observed by people, not by the suite.** The suite drives
  Chromium, including phone-sized and touch contexts. Safari-only behaviour (its
  gesture events, diagonal panning, double-tap zoom) is written from WebKit's
  documented behaviour and confirmed by the owner's and the co-author's phones.
- **No error count, no progress percent, no Check** on the public page: recorded
  exclusions (owner, 2026-10-30), not gaps.
- **Counting is opt-in and off by default.** The one script tag is injected only
  when the endpoints are passed to the assembler, so a local run and every test
  fixture assemble an uncounted tree.
- **EC-048's literal text is not satisfiable by any implementation of ADR-0041**;
  `assemble.py`'s docstring argues it. R2 carries its exemptions (the clues, the
  key, a book's title, series and authors) and declares their residuals.
- The bundle is exported by an **explicit** owner action, never as a side effect
  of finalising a book or exporting a PDF (R5), and only books out of draft reach
  it.
- **COMP-011 is in the registries and not in the C4 component diagram**, the same
  drift [08](08-playing-a-stored-puzzle.md) records for CAP-007.

## Related

- [08-playing-a-stored-puzzle.md](08-playing-a-stored-puzzle.md) — the admin
  player, the shared state module, and why that one may ship the solution
- [07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md) — AGG-002, whose finalised books become `/b/<slug>`
- [09-the-three-inbound-adapters.md](09-the-three-inbound-adapters.md) — the door
  the public player is deliberately outside of
- `docs/deploy/player.md` — what is deployed where, the publish commands and every
  publish since the first
- [`docs/qa/public-player-test-cases.md`](../../../qa/public-player-test-cases.md) — the
  manual cases, each naming the automated test that is the actual gate
- ADR: [ADR-0041](../../../../meta/architecture/decisions/adr/0041-public-player-static-bundle-and-hash-urls.md) ·
  [ADR-0038](../../../../meta/architecture/decisions/adr/0038-puzzle-player-plain-js-and-playwright.md)
