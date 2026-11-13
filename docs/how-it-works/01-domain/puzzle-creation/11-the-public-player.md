# 11 — The public player (CAP-007 / FR-045)

> **STALE AS OF 2026-11-08, AND IT WAS STALE WHEN IT WAS COMMITTED.** Everything
> below describes `player/play.js`, the public player's own implementation.
> **CARD-399 deleted that file on 2026-11-08** and `/play/<key>` is now the admin
> player's `solver.js` rendered at build time in public mode (CARD-385's
> `mode: "public"`), with `admin.css` and CARD-394's `base.css`; `player.css` and
> `pages.js` now style and drive only `/library` and `/b/<slug>`. That player went
> to production on 2026-11-09 — see `docs/deploy/player.md`'s "shared-UI publish".
>
> This page was written from a working-tree read of 2026-11-06 and committed on
> 2026-11-09 without re-checking that its subject still existed, which is the
> failure its own scope note warns about one paragraph down. What is still true of
> the shipped page: the two hash URLs, the no-answer rule and how it is kept, the
> byte-identical copy rule (now four files, not two), the localStorage save, the
> three doors, and the rebuild-not-filter argument. What is now wrong: every
> sentence about `play.js`, its brush buttons, its own hint and crosshair code, and
> `body[data-solved]`. The six control sections describe behaviour the shared UI
> mostly keeps, but not the code that implements it. A rewrite is owed.

> Scope: the top-level `player/` tree — `play.js`, `pages.js`, `player.css`, three
> hand-written documents (`play.html`, `library.html`, `book.html`), `vercel.json`,
> and `assemble.py`, which writes the deployable site — plus the exporter that
> feeds it, `admin/player_bundle.py` (COMP-009). Component **COMP-011**, governed
> by ADR-0041.
>
> The per-file **line counts this block used to carry are retired, not updated**.
> They were measured once and nothing redded when they rotted: by 2026-11-06 the
> block said 579 lines of `play.js` against 1,426 and 461 of `player.css` against
> 884, after five cards landed in a week. CARD-347 holds the same retirement for
> the aspect README's column and for the figures in a card body, a module
> docstring and a stylesheet comment; this is its first half arriving early,
> because the block had to be rewritten anyway. For the same reason the prose
> below cites code **by name** — a constant, a function, a test class — and not by
> `path:line`: a line number in a document nobody re-measures is a claim that goes
> false on the next edit.

## Why there are two players

[08](08-playing-a-stored-puzzle.md) describes the admin panel's puzzle player and
quotes CON-021 as it stood on 2026-10-03: interactive play "only as this
admin-panel page — no public player". That clause is gone. CON-021's current
statement (CON-021's row in `trace.yml`) reads:

> Interactive play in exactly two forms — the admin panel's puzzle player (behind
> CON-015/CON-016, may ship the solution) and the public player per ADR-0041
> (static, read-only, no accounts, localStorage-only, never ships a solution);
> everything else forbidden, no server-persisted play state anywhere.

FR-045 (2026-10-23) is that second form. Its reason is printed: a book carries a QR
code beside each puzzle, and a QR code needs something to point at that is not
behind the panel's credentialed door. Both players are CAP-007 — the capability
gained a second requirement rather than a sibling (CAP-007 in
`domain/capabilities.yml` carries `requirements: [FR-044, FR-045]`).

**COMP-011 is the first component whose code lives outside `src/nonogram/`**
(COMP-011's row in `trace.yml`), and that has one consequence worth stating: ADR-0007's import
guard walks `src/nonogram/**/*.py`, so a tree of hand-written JS and CSS is
untouched by it. The dependency direction this aspect is built on
([01](01-the-layered-pipeline.md)) is not enforced here by an `ast` walk; it is
enforced by the tree having no Python in it at all except an assembler that
imports nothing from the package by name.

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

This is the same rule as the admin player's, inverted. ADR-0038/R6 permits the
panel to ship the solution grid *because* it sits behind the door; ADR-0041/R2
forbids it for anything public. The consequences are visible in the code rather
than asserted about it (`play.js`'s header says all three):

- **Solved is clue satisfaction.** `isClueSolved` asks whether every row and
  column clue is satisfied by the filled cells. For a uniquely solvable puzzle
  that is exactly the solution — CON-005/INV-002 make every published puzzle
  uniquely solvable, which is what the check rests on.
- **Four functions of the shared state module are unreachable here.**
  `solver_state.js`'s `isSolved`, `errorCount`, `solvedPercent` and `firstWrongRow`
  all take a `solution` argument as the thing they compare the board *against*, so
  the public page cannot call them. That is why it has **no error count, no
  progress percent and no Check** — and those three stay out by the owner's
  decision of 2026-10-30, not merely by inability.
  **`hintCell` was on this list and should not have been** (CARD-327). It takes a
  solution for exactly two things — spelling the state it returns, and reading the
  player's wrong marks as undecided — and the deduction between them, `lineForced`,
  takes a clue and a line and no solution at all. "A hint needs the answer" was a
  sentence this document and `play.js`'s own header both carried, and it was false;
  see [the hint](#the-hint-derives-the-next-cell-and-never-reveals-one) below.
- **The save is this file's own.** `serializeState`/`deserializeState` fingerprint
  `payload.solution` into the save and refuse one whose fingerprint does not
  match, so they cannot be called from a page that has no solution. `play.js`
  reimplements the save natively and is cross-checked against the module's stroke
  values from the test tree — the reimplement-rather-than-import precedent
  CLAUDE.md names.

## Reuse by byte-identical copy, not by import

ADR-0041/R3 requires the board-state module to be *copied*, never edited and never
imported across. `assemble.py`'s `COPIED_FROM_ADMIN` is the table: today
`solver_state.js` and the design tokens `tokens.css`, each copied byte for byte
from `src/nonogram/admin/static/`. The equality is checked at assembly time *and*
from the test tree, so the two copies cannot drift.

The practical effect is that "the public player makes the same state transitions as
the admin player" is true by construction. `play.js` turns input into
`clickStroke` / `dragStroke` / `resetStroke` / `record` / `undo` / `redo` calls and
paints what comes back; the admin's `solver.js` keeps the same division of labour
against the same module.

What is *not* shared is the UI glue, and `play.js`'s header says why: `solver.js`
is built around a Flask-rendered page with an embedded payload. This page fetches
its puzzle instead, and then rebuilds the glue — the brush menu, Region, the
crosshair, zoom, the clue circles and the hint are each written natively here
against the same module, which is the subject of the six sections below. The
counters are the one group that is not rebuilt: no error count, no progress
percent, no Check.

## Marking: four brushes, and the mark that drifted

The public page offers `TOOLS = [FILLED, EMPTY, MAYBE, UNKNOWN]` — all four of
`solver_state.js`'s cell states, in the admin brush menu's own order (locate the
constant by name: `play.js`'s `TOOLS`). `MAYBE` ("?") was withheld until CARD-323,
and the reason was never that the page could not reach it: every transition it
needs is in the shared module and `player.css` already carried the mark's cell
background. It was a scope choice, which the owner reversed on 2026-10-30. What
stays out is the three features that take `solution` — the error count, the
progress percent and Check — because those the page genuinely cannot reach. The
hint used to be named in that list and does not belong in it.

**The click cycle is the module's, including the repeat.** A tap is
`clickStroke(board, row, col, tool, repeat)`, where `repeat` is true only when the
previous tap was the same cell *with the same brush*; `lastClick` is what remembers
that, and anything that could make the next tap mean something else — a brush
change, a commit, a pinch — clears it. So Black cycles black → white → blank on one
cell, Maybe marks "?" and clears it on the second tap, and picking a different
brush restarts the cycle instead of continuing someone else's. A drag along a row
or column is one `dragStroke`, and therefore one undo step.

The two players did **not** agree on what a "?" looks like, and the story of that
disagreement is the clearest example in this document of how a drift is actually
caught here. `admin.css` drew a "?" glyph in the accent token on the cell and on
the swatch; `player.css` drew a tint one step off the paper and no glyph, and the
tint measures 1.169:1 against a blank cell — invisible. CARD-328's agreement guard
exists to stop these two sheets drifting, and it did not report this, because the
Maybe mark was never in the surface it compares: the mark did not diverge *past* a
guard, it diverged where no guard was looking, so it reached a render before it
reached a test. CARD-323 measured it and routed it to the owner rather than
deciding a rendered mark in a worktree; the owner chose the admin's glyph on
2026-11-03; CARD-339 added it to both hooks and **widened the compared surface**,
which is the half of that card that was not one line of CSS.

Two things are worth carrying away from it. The glyph is matched to the admin's by
*derivation* rather than by copy — `tests/test_public_player_agreement.py` reads
both sheets and holds the two declaration sets to each other, which is also why
`player.css` now declares `--player-numeral-min`: the admin's `font-size` reads
that token, it lives in `admin.css` rather than in the byte-identically copied
`tokens.css`, and a declaration this page could not resolve would render the glyph
at the body size. And the marks are no longer *assumed* to agree: the same module
censuses every state `solver_state.js` declares against both hooks and both
sheets, and every fact of it has to be compared, agreeing, or routed to the owner
with a figure. Of the sixteen facts, three are compared, seven agree and **six
are routed**; the two Maybe *papers* are among the six, because the admin's Maybe
cell has no background rule at all and draws the glyph on the board's paper at
7.258:1 where this page draws it on the tint at 6.207:1. Nobody has decided that,
so it is routed rather than exempted — which means the census holds it to **keep
diverging**, and (for these two, by written-out values) to keep the values it
has. **"These two" is two facts but only three of their four sides**, and the
difference matters if you are relying on the word "pinned": the written-out
values are the *cell*'s, both sides of it; the *swatch*'s public side comes
along transitively, because the guard also claims this page's swatch paper
equals its cell paper (the button previews the cell). The swatch's **admin**
side is held only to *differing from this page's* — `admin.css` declares no
background on its Maybe swatch, so a background planted there moves the census
with every arm green. That was measured by plant in this card's cycle 2, and
the fourth side is CARD-346's too. The other four routed facts are held to
diverging and no further; the derived residue that would close both gaps, the
counterpart of the one `DECLARED_DIVERGENCES` already carries, is CARD-346's.

An empty cell is drawn as a **centred dot**, 28% of the cell, as an `::after`
(`player.css`'s `.player-cell[data-state="empty"]::after`) — the mark
`admin.css` draws for the same state. It was two
`linear-gradient` strokes here (a cross) until 2026-10-30, so the same mark meant
one thing in the panel and another on the public page; the owner chose the dot and
the divergence is closed. Like everything else shared between the two players, it
is reimplemented rather than imported: R3's byte-identical copy covers
`solver_state.js` and `tokens.css`, and nothing else, so `admin.css`'s rule is the
*look* this matches, not a file it reads.

## Region: the one-shot arm that lets a touch drag mark

A mouse drag always marks. A **touch or pen** drag marks only while Region is
armed, and that is not a preference: with Region off the browser must stay free to
pan the page, because the board of a 30-cell puzzle on a 390 px screen is read by
scrolling and zooming. The rule itself is the shared module's — `gesturePaints`
takes the pointer type and the armed flag and answers whether this gesture paints —
and `play.js` reads it **once, at `pointerdown`**, like the brush, so arming Region
mid-gesture cannot retroactively turn a pan into a stroke.

Three decisions worth knowing, all of them the admin's, followed rather than
re-taken:

- **It is one-shot.** `nextRegion(region, "drag")` disarms it the instant a drag is
  *recorded* — "a drag ended", not "a cell changed", so a drag that marked nothing
  still spends the arm.
- **Region and the brush are independent in both directions** (owner, 2026-10-14):
  pressing Region never changes the brush, and picking a brush never disarms
  Region. The toggle's three swatches preview the *current* brush, which is how the
  button says what the next drag will paint.
- **It is the only thing on this page that takes `touch-action` away from the
  browser.** `player.css` sets `touch-action: auto` on a cell and overrides it to
  `none` only under `.player-board.is-region` — `admin.css` keys its own rule the
  same way. The page-wide `touch-action` stays `auto`, which the owner
  play-tested and confirmed on 2026-11-05; there is no `pan-x pan-y` anywhere, and
  `play.html` deliberately keeps the browser's own pinch-zoom (no
  `user-scalable=no`, no `maximum-scale`).

## The crosshair reads the DOM and nothing else

Hovering a cell tints its row, its column and their two clue boxes, so the eye can
travel from a cell to its clues and back without sliding onto a neighbouring line
(CARD-325; the admin's own control is CARD-267's `wireCrosshair`, and this is
written natively against the same decisions).

Its whole mechanism is **one class, `.is-crossed`, on elements that are already on
the page**: no cell state, no history, no clue data, no payload field, no storage
and no request. That is asserted over the source, default-deny, by
`tests/test_public_player_crosshair.py`'s `TestPublicCrosshair_ItReadsNoBoard` —
the crosshair's functions may use `document`, `Number`, `Set` and each other, and
nothing else. It adds no toolbar control, calls no callback, never calls
`preventDefault` and never stops propagation, so every other handler on the stage
sees exactly the events it saw before. In `player.css` the tint is a *background*
(`--player-cross`, and `--player-cross-ink` under a filled cell) precisely so it
stays out of the way of everything else drawn on a cell: the white dot and the
Maybe "?" are `::after`, and the clue circle is a border.

Four decisions CARD-267 paid for are followed here rather than rediscovered:

1. **The gutter corner.** A pointer over the stage but not over a cell — a clue
   box, the corner, the padding — *keeps* the crosshair where it was. Only leaving
   the stage clears it, so looking from a cell to its clue does not put the line
   out.
2. **The no-hover phone.** A touch crosshair follows the finger from `pointerdown`
   (a tap may never move) and **stays after the finger lifts**, so it is seen
   between taps.
3. **Why touch is exempt from the leave handler.** A released touch pointer fires
   `pointerleave` at once, so a leave that did not exempt touch would undo every
   touch crosshair the moment it was made.
4. **A remembered position with nothing painted is a half-painted crosshair.** The
   admin clears its memory from `redraw()`; this page draws its table once, so the
   refusal is kept by construction instead — the "already there, do nothing"
   shortcut is taken only when the DOM still shows the cross painted.

And two the admin never had to make, because the admin had zoom first and this page
gained both in the same week:

- **Which cell comes from the browser's hit test** (`cellUnder`, the same call
  marking uses), never from geometry computed here. A hit test is right at every
  zoom and every scroll offset; arithmetic over `scrollLeft` and the cell pitch is
  how a crosshair lands one cell off at 300%.
- **A pinch has no crosshair.** Two or more touch/pen pointers down is a pinch: the
  first finger's `pointerdown` had already painted a cross, so the second takes it
  off, nothing follows the spread, and nothing is left when the fingers lift. This
  is the crosshair's *own* count of pointers and reads none of the marking code's
  pinch state, so it also covers two fingers that began on a clue box — the case
  the marking code deliberately leaves to the browser.

The two players are held to the same decisions, not to the same code, by
`tests/test_public_player_agreement.py`'s
`TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions`.

## Zoom: the module's arithmetic, this file's rendering

Until CARD-324 this page **served** the zoom arithmetic and called none of it:
ADR-0041/R3's byte-identical copy of `solver_state.js` has always carried
`ZOOM_MIN`, `ZOOM_MAX`, `ZOOM_STEP`, `clampZoom`, `stepZoom`, `pinchZoom` and
`anchoredScroll`, and the only mention of zoom in `play.js` was a comment saying
the admin had one. That is duplication-shaped debt rather than a missing feature,
and the fix is glue and nothing else.

**Nothing about the zoom is derived here.** There is no bound, no step and no clamp
expression in `play.js`: the percent starts at `ZOOM_MIN`, the buttons ask
`stepZoom` for the next one, a pinch asks `pinchZoom`, and the scroll position that
keeps the anchored cell still comes from `anchoredScroll`. Both of those clamp
their own return, which is why `clampZoom` and `ZOOM_STEP` are **not** imported —
an unused import is a second place to look for a rule that lives in one. The five
names the page does import are exactly the five `solver.js`'s glue imports, and
`tests/test_public_player_zoom.py` *derives* that set from `solver.js` rather than
listing it, so the two pages' consumed surface cannot drift apart. The readout in
`play.html` starts **empty** for the same reason: a literal `100%` in the markup
would be a second source for a number whose only source is the module.

**Zoom is a view.** It changes no board state, records no stroke, never enters the
history or the save, and resets to `ZOOM_MIN` on every load — the same three
properties the admin's zoom has. In the stylesheet it is one custom property,
`--player-zoom`, multiplying the fitted cell, as `admin.css`'s own `--player-zoom`
multiplies the panel's; the cell's `min-width`/`min-height` floor is tied to
`--player-cell` rather than to a measured 28 px, because with `table-layout: fixed`
Chromium sizes a column to the largest minimum in it, and a fixed floor gave the
board *wider gutters and no bigger cells* at 125% — the one thing a zoom must not
do.

Two interactions had to be decided rather than left to listener order:

- **The anchor.** A button press anchors on the centre of the stage's own visible
  box, so the cell under the player's eye stays there; a pinch anchors between the
  fingers. `keepCluesInView` runs before the scroll is moved, because a bigger cell
  changes whether an axis can still afford to keep its gutter on screen.
- **The pinch/drag collision: the stroke is abandoned.** By the time a second
  finger lands, the first has already begun a gesture. Its preview reverts to the
  recorded board, the gesture is cleared so the first finger's own `pointerup`
  commits nothing — not the drag, and not even the single-cell tap it would
  otherwise have been — `lastClick` is cleared so the pinch breaks a run of repeat
  taps, and the pinch then swallows the `pointerup`/`pointercancel` of both its
  pointers, whichever the browser releases first.

**The honest residue, and it is why later controls are not in the toolbar.** The
toolbar's zoom group is a third `role="group"` after the history buttons, matching
the admin's DOM order and attribute names. Swept at 390 px tall during CARD-324:
`main` kept the toolbar one row from about 780 px to 932 px wide, and the zoom
build wraps it to two rows from 780 px to 880 px, so **the group needs about 889 px
to stay one row** — iPhone landscape at 844, 852 and 874 px is affected. Three
layouts that would fit at 844 were measured and deliberately not shipped (they are
layout choices, and one of them shrinks the 44 px touch target the round chose), so
this is an **open residue the owner holds**, not a closed question. The practical
consequence is structural: `tests/test_public_player_zoom.py` pins that one-row
bound and therefore reds by design on *any* new toolbar button, which is why the
Hint control — and, per CARD-380, the probe controls — live outside
`.player-toolbar` rather than in it.

## Circled clue numbers: the readout that needs no answer

A clue number is circled once the player's marks account for it. **Which** numbers
is `solver_state.js`'s `circledClues` and nothing in `play.js`: it takes the board
and the payload's clues, never a solution, and it is the very function the admin
player calls, so the two pages cannot disagree about when a number is circled
(CARD-326). This page only carries the answer to the DOM, and carries it without
deciding anything — the value handed to `classList.toggle` is a bare member of
`circledClues`'s return value, which `tests/test_public_player_circles.py` holds
both structurally (the painter has no operator, no comparison and no property it
was not given) and by corpus (the page's set equals the module's across seeded
boards). The circles are painted from the **recorded** board, never from a drag's
preview: a number is not circled by marks that are not yet made.

**Circled is not satisfied**, and the solved check is deliberately not built from
this set. A board can circle every number and still be wrong — the module's own
example is a line clued `1 2` marked with its 2-run to the left of its 1-run, which
circles both — so `isClueSolved` stays an exact clue-satisfaction check and
CARD-326's AC-4 holds it with a board that does exactly this.

The ring is a **border** on the number's `::before`, not a background, so the
crosshair's tint on the clue box cannot hide it. This page has one gutter per axis
— the admin's doubled gutters (CARD-212) are a layout it does not have — so each
number is one span and there are no twins to keep in step.

## The hint derives the next cell, and never reveals one

CARD-327's starting point was a false sentence in this page's own code: `play.js`'s
header listed hints among the things the page cannot have "because they need the
answer". `hintCell` does take a solution, but only to spell the state it returns
and to discard the player's wrong marks; the deduction in between, `lineForced`,
takes a clue and a line and nothing else. So the hint is reachable, and it is the
one admin feature on the parity list that had to be *re-derived* rather than wired.

- `forcedLine(clue, cells)` is that deduction written natively — reachability over
  (cell, runs placed), backward then forward — returning the cells every placement
  of the clue consistent with the knowns agrees on, or `null` when no placement
  fits. It is the reimplement-rather-than-import precedent CLAUDE.md names, and it
  is cross-checked against the module's own `lineForced` and `hintCell` **from the
  test tree**, where the import is legal (`tests/test_public_player_hint.py`).
- `derivedHint(board, rows, columns)` is the `hintCell` equivalent: it runs
  `forcedLine` over every row clue and every column clue against the board *as the
  player has it* and returns the first undecided cell (`UNKNOWN` or `MAYBE`),
  row-major, that some line forces — its row first, then its column — with the
  state that line gave it. There is nowhere else that state could come from.

**The ladder is the module's** — `nextRung`, `RUNG_POINT`/`RUNG_EXPLAIN`/
`RUNG_REVEAL`, `hintReason`, `hintStroke` and `hintCount` are imported, not rebuilt;
this page adds the sentences (the admin's own words, so the two pages say the same
thing about the same line, held by the agreement test) and the rendering. Rung 1
points at the line and lights it, rung 2 explains why that line decides a cell,
and rung 3 records **one** `hintStroke` — so a hint is one undo step, and the
counter reads the hint count off the undo stack rather than keeping a tally. The
stroke keeps `hint: true` in the save, so a reload does not demote a derived cell
to a plain mark and drop it from the count. Any recorded change puts the ladder
back on rung 1 with nothing lit, which is what makes rungs 1–3 of one ladder always
describe one situation.

**Two things `hintCell` did with the answer, and what replaces them:**

- **No fallback.** Finding no line that forces an undecided cell, `hintCell`
  reveals an arbitrary one. That branch is the one that reads the answer and has no
  solution-free form, so this page does not have it: when no line forces a cell,
  every rung says the same sentence — *the clues decide nothing more by themselves*
  — and **nothing is revealed at any rung**. The admin says that sentence too
  (CARD-269 designed it) and then follows it with a rung-3 reveal; that is the part
  this page leaves out. The control is disabled only when no cell is undecided at
  all, because the exhausted state has to be sayable out loud.
- **Wrong marks are not discarded.** The page cannot tell a wrong mark from a right
  one, so it deduces from the board as the player has it (only filled and empty are
  knowns; a "?" is undecided). A wrong mark can contradict a line's clue, and
  `forcedLine` then answers `null` for that line — **the line is skipped** and the
  hint deduces from the others, so a hint may follow from a wrong mark. That is what
  "the board as the player has it" means, and it is why the hint says which line it
  read. Surfacing the contradiction ("this line cannot be right") *is*
  solution-free and would be the nearest honest thing to the error count the owner
  declined — which is exactly why it is not shipped as a bug fix.

**Why this is not an ADR-0041/R2 problem**, declared rather than assumed: R2 is read
as a rule about what an *asset carries*, not about what a browser can compute from
clues it already has (owner ruling, 2026-11-06). `puzzle/<key>.json` is unchanged,
no variable in `play.js` is a solution grid before or after any number of hints, and
CON-005/INV-002 — every published puzzle is uniquely solvable — are why the clues
already determine every cell. The mechanical half is
`tests/test_public_player_hint.py`'s `TestPublicHint_TheAssetGainsNothing`.

The control is **not** a child of `.player-toolbar` (owner ruling, 2026-11-06): it
sits in its own bar under the board, beside the usage paragraph, for the toolbar
reason measured under [zoom](#zoom-the-modules-arithmetic-this-files-rendering)
above. The sentence a press says goes in a `role="status"` region that is
*visible* — rungs 1 and 2 exist to be read, and the page's own announcer is clipped
to 1×1 — and it is emptied on the next recorded change, because it describes the
board as it was.

## Probe mode: decided, specified, and not here yet

**Status, 2026-11-06: not on `main`.** `player/play.js`, `play.html` and
`player.css` contain no probe code; CARD-380 is `in_progress` on
`card/380-public-probe-mode`, queued behind the hint, which is a real dependency
rather than a serialisation one — rule 3 below puts hint strokes inside an open
probe, so the interaction could not be built or tested before CARD-327 landed. This
section is the design as decided, so that reading it is not the same as reading the
shipped page.

**What a probe is.** A solver who cannot deduce further makes a *group* of marks
under one hypothesis and then either keeps them all or reverts them all. That is a
transaction over the history, not a colour: probing places filled, empty and "?"
marks, so one extra cell state could not carry it, and `CELL_STATES` stays exactly
four members. Membership lives beside `data-state` (the admin uses `data-probe` on
the cell) and is **derived from the history's strokes**, never stored per cell.

**The whole transaction is already in the shared module and already solution-free**
— `PROBE_EVENTS`, `nextProbe`, `probeStart`, `probeCells`, `abandonProbe` and
`checkpointHistory` take a history and a probe state and no solution — which is why
this is wiring, as zoom was. Measured from those signatures on 2026-11-06.
CARD-268's eleven rules carry over unchanged:

| | Rule |
|---|---|
| 1 | **Depth 1** — at most one probe open; pressing Probe again cannot nest one |
| 2 | A Probe control opens a probe at the current history position |
| 3 | While open, **every** mark made belongs to it and renders in the probe look — hint strokes included |
| 4 | **Contradiction** undoes back to the checkpoint: the board is exactly as at probe start, and the probe closes |
| 5 | **Keep** drops the look and closes the probe; it touches no cell |
| 6 | Undo/redo stay LIFO; undoing past the open position shrinks the probe to empty and leaves it open, and a redo of a pre-probe stroke stays outside it |
| 7 | A probe whose marks reach the solved state **commits** |
| 8 | The circles read the board as it is, probe marks included |
| 9 | The save never contains probe strokes, so leaving the page abandons an open probe |
| 10 | Reset clears the board, the history and any open probe |
| 11 | Open/closed is player state: the transitions are the pure module's, the value lives in the page |

Rule 6 is worth one more sentence, because CARD-268's review found it: the
checkpoint cannot be a single number. It is the frozen set of strokes the history
held **on both stacks** when the probe opened — a stroke sitting on the redo stack
is one the player made *before* the probe, and redoing it must not join one. That
is already in the module (`nextProbe`'s "open"), and because the probe names the
strokes it is *not* about, the clamp of rule 6 stops being a rule of its own.

**Rule 7 is the one place the admin touches the answer, and it is the one rule that
differs here.** The admin decides "solved" with `isSolved`, against the solution.
This page's check is `isClueSolved`, which is the same fact for a uniquely solvable
puzzle, and the owner confirmed the auto-commit on 2026-11-06: a hypothesis that
reaches the whole picture *was* correct, because every published puzzle has exactly
one solution, so there is nothing left to abandon. Without it a player who finished
the picture inside an open probe would lose the finishing marks on a reload (rule 9)
and would still be shown a Contradiction button that one press would use to undo the
finished picture.

**The look is decided and is not open for redesign** (owner, 2026-11-06): the
admin's **dashed outline**, never a ground tint. The admin's own measurement is the
evidence and does not need re-taking — its probe tint sat dE76 2.55 from the
crosshair's tint, which is two small cells in what reads as one colour. What
CARD-380 must settle is the part the admin never faced: this page now draws a
crosshair tint, a circle ring and a hint highlight, and a probed cell may be under
any of them, so the marks have to coexist **by pixels, from tokens only**. A
collision that cannot be resolved without changing the probe's look, the crosshair,
the circles or the hint is a stop-and-report to the owner, not a redesign — and the
controls must land outside the toolbar, for the measured reason under zoom above.

## Solving is revealed, and the reveal is keyed on an attribute the page already writes

On the transition into solved, the banner settles in and the filled cells flash the
success colour in a diagonal sweep before ending in ink — about 0.8 s in all
(`player.css`'s `@keyframes player-solved-in` and `player-solved-flash`, and the
`body[data-solved="true"] .player-cell[data-state="filled"]` rule that plays
them). The sweep's per-cell delay reads `--player-wave`, which `drawBoard` sets to
`row + col` on each cell, exactly as `solver.js` sets it for `admin.css`'s copy of
the same animation.

It is keyed on `body[data-solved="true"]` rather than on a class of its own,
because `play.js`'s `refresh` already writes that attribute on every render: the
animation therefore plays on the transition into solved and does not re-trigger
while the board stays solved. Under `prefers-reduced-motion` both animations are
off and the banner and success frame still appear.

Held by `tests/test_public_player.py::test_the_empty_mark_is_a_dot_and_solving_is
_revealed`, which asserts the dot through the `::after` box *and* through the
cell's own `background-image` being `none` (so the cross cannot return as a
background), and the reveal through the *computed* `animation-*` properties rather
than `getAnimations()` — a CSS animation leaves that list when it finishes, so a
test reading it races the 440 ms it is testing.

## Play state is this browser's and nothing else's

One `localStorage` entry per puzzle key, under `nonogram-public:<key>` (`saveKey`).
The save carries the clues it was made against and is refused on replay if they do
not match the fetched puzzle (`deserialize`), so marks cannot be replayed onto a
different puzzle that happens to share a key. It also carries the format version in
the *value* and not in the key, so a later format replaces the same entry — the
choice `solver_state.js`'s `SAVE_VERSION` makes for the admin's save, and its
reason.

There is no account, no server-side state, and **no write request of any kind** —
the only request the page issues is the `GET` of its own puzzle file, which is
asserted in a browser rather than argued:
`tests/test_public_player.py::test_no_write_request_for_any_interaction`.

## What the site is, and what is rebuilt rather than copied

See [diagrams/11-bundle-to-site.puml](diagrams/11-bundle-to-site.puml) for the
whole path, database to visitor, and where the solution stops on it.

`assemble.py` writes the deployable tree: the three pages, the two copies from the
panel, `vercel.json`, a `.player-site` marker (`SITE_MARKER_FILE`) that is how the script
recognises its own output before deleting it, and — rebuilt from the bundle — one
`puzzle/<key>.json` per puzzle, `index.json`, and one `book/<slug>.json` per book.

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
R2's third exemption on 2026-10-28 (`EXEMPT_LISTING_FIELDS`), scoped to the served
`book/<slug>.json` schema and to no other, with its residual declared rather than
bounded — R2's own text measures it at 100 of 100 cells recoverable if an owner
writes a base-64 grid into a book title. "This script removes the free-text channel"
is therefore false as a sentence about the whole site, and `assemble.py` says so
about itself.

The scope is that **schema**, not the set of pages the string is shown on: R2's
2026-10-28(b) amendment struck its own "and nowhere else" clause. The title is shown
on `/b/<slug>`'s `h1` and, since CARD-436, in the header of a `/play/<key>` opened
from that book, where it names the way back. That page already fetches
`book/<slug>.json` for CARD-420's theme, so this adds no served field, no request and
no character — the declared residual above is unchanged.

## Three doors, one document each

`vercel.json`'s rewrites are the host's whole routing table, and the fixtures route
by reading that file:

| URL | Serves | Why a rewrite |
|---|---|---|
| `/play/<key>` | `play/index.html` | one document plays every puzzle; `play.js` reads the key out of the path and fetches `puzzle/<key>.json` |
| `/b/<slug>` | `b/index.html` | the QR landing for one book |
| `/library` | `library/index.html` | the extensionless path needs the rule |

## Bounds and honest gaps

- **COMP-011 is in the registries and not in the C4 diagram.** `trace.yml`
  carries the component with `code: ["player/**"]`; `c4/components-CTX-001.puml`
  does not mention it at all (re-measured 2026-11-06: the file contains the
  string "player" nowhere). This is the same drift [08](08-playing-a-stored-puzzle.md)
  records for CAP-007, one component wider.
- **It is deployed, and this page is not where that is recorded.** The sentence
  here used to be "nothing is deployed yet" and went false on 2026-10-30, when the
  site first published to Vercel (project `nonogram-studio`) and the owner's
  `https://nonogram.adverax.io` was observed serving it. It has been republished
  as each of this week's cards landed, the latest recorded publish being the hint's
  on 2026-11-06. `docs/deploy/player.md` is the record — the observed facts, the
  commands, and the `TODO(owner)` values only the dashboard can supply — and it is
  the only place that should carry them, so this bullet deliberately restates
  nothing but the date. The QR base is therefore an **observed** URL rather than
  Vercel's default shape for a project of that name, which is what unblocked
  CARD-210 (real scannable codes, still `ready`) and CARD-332 (the panel's domain
  field and the read-only per-puzzle link, landed 2026-11-03).
- **Probe mode is the one parity gap still open**, and it is a gap rather than an
  exclusion: see its section above for the design and for what CARD-380 is doing
  with it. The error count, the progress percent and Check are the recorded
  *exclusions* (owner, 2026-10-30), and they stay out.
- **Counting is opt-in and off by default.** The one script tag lives in
  `assemble.py`'s `ANALYTICS_SNIPPET` and is injected only when the
  endpoints are passed, so a local run and every test fixture assemble an
  uncounted tree.
- **EC-048's literal text is not satisfiable by any implementation of ADR-0041**,
  and `assemble.py`'s own docstring is where that is argued rather than here: R2
  carries three exemptions (the clues, the answer key, the book title) and four
  declared residuals.
- The bundle is exported by an **explicit** owner action and never as a side
  effect of finalising a book or generating a PDF (R5, `export_bundle`).
  Only books out of draft reach it (`FINALIZED_STATUSES`) — the route says
  so when the book you pressed it from is still a draft.

## Related

- [08-playing-a-stored-puzzle.md](08-playing-a-stored-puzzle.md) — the admin
  player, the shared state module, and why that one may ship the solution
- [07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md) — AGG-002, whose finalised books become `/b/<slug>`
- [09-the-three-inbound-adapters.md](09-the-three-inbound-adapters.md) — the door
  the public player is deliberately outside of
- `docs/deploy/player.md` — what is deployed where, the publish commands, and the
  owner steps still open
- [`docs/qa/public-player-test-cases.md`](../../../qa/public-player-test-cases.md) — the
  manual cases for everything above, each naming the automated test that is the
  actual gate, plus the after-publish smoke run
- ADR: [ADR-0041](../../../../meta/architecture/decisions/adr/0041-public-player-static-bundle-and-hash-urls.md) ·
  [ADR-0038](../../../../meta/architecture/decisions/adr/0038-puzzle-player-plain-js-and-playwright.md)
