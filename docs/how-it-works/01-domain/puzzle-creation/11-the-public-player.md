# 11 — The public player (CAP-007 / FR-045)

> Scope: the top-level `player/` tree — `play.js` (579 lines), `pages.js` (364),
> `player.css` (461), three hand-written documents (`play.html`, `library.html`,
> `book.html`, ~100 lines each), `vercel.json`, and `assemble.py` (1,642) which
> writes the deployable site — plus the exporter that feeds it,
> `admin/player_bundle.py` (631, COMP-009). Component **COMP-011**, governed by
> ADR-0041.

## Why there are two players

[08](08-playing-a-stored-puzzle.md) describes the admin panel's puzzle player and
quotes CON-021 as it stood on 2026-10-03: interactive play "only as this
admin-panel page — no public player". That clause is gone. CON-021's current
statement (`trace.yml:631`) reads:

> Interactive play in exactly two forms — the admin panel's puzzle player (behind
> CON-015/CON-016, may ship the solution) and the public player per ADR-0041
> (static, read-only, no accounts, localStorage-only, never ships a solution);
> everything else forbidden, no server-persisted play state anywhere.

FR-045 (2026-10-23) is that second form. Its reason is printed: a book carries a QR
code beside each puzzle, and a QR code needs something to point at that is not
behind the panel's credentialed door. Both players are CAP-007 — the capability
gained a second requirement rather than a sibling (`capabilities.yml:212`,
`requirements: [FR-044, FR-045]`).

**COMP-011 is the first component whose code lives outside `src/nonogram/`**
(`trace.yml:2624`), and that has one consequence worth stating: ADR-0007's import
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
| `/play/<key>` | first 10 hex characters of SHA-256 over `"{width}x{height}:"` + the solution grid row-major, `1`/`0` | R1, `player_bundle.puzzle_key` (`:215`) |
| `/b/<slug>` | first 10 hex of SHA-256 over `"book:"` + the book's puzzle keys in book order, concatenated | R7, `player_bundle.book_slug` (`:257`) |

Both are *content* addresses, chosen over a stored opaque slug for a stated
reason: a stored slug "is stable only as long as the database and its backups
are", while a printed book preserves its puzzles forever, so a hash of the content
survives a re-seed. Keys are 10 characters each (`KEY_LENGTH`, `:203`), which is
why the slug concatenates them with no separator and is still unambiguous.

The slug takes **no title**, and `book_slug`'s signature does not accept one —
"the only version of 'not an input' a caller cannot get wrong" (`:270`). A title is
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
than asserted about it (`play.js:21`-`45`):

- **Solved is clue satisfaction.** `isClueSolved` (`play.js:174`) asks whether
  every row and column clue is satisfied by the filled cells. For a uniquely
  solvable puzzle that is exactly the solution — CON-005/INV-002 make every
  published puzzle uniquely solvable, which is what the check rests on.
- **Four functions of the shared state module are unreachable here.**
  `solver_state.js`'s `isSolved`, `errorCount`, `solvedPercent` and `hintCell` all
  take a `solution` argument, so the public page cannot call them. That is why it
  has no error count, no progress percent and no hint button, and why adding any
  of them is a new architecture question rather than a feature.
- **The save is this file's own.** `serializeState`/`deserializeState` fingerprint
  `payload.solution` into the save and refuse one whose fingerprint does not
  match, so they cannot be called from a page that has no solution. `play.js`
  reimplements the save natively and is cross-checked against the module's stroke
  values from the test tree — the reimplement-rather-than-import precedent
  CLAUDE.md names.

## Reuse by byte-identical copy, not by import

ADR-0041/R3 requires the board-state module to be *copied*, never edited and never
imported across. `assemble.py`'s `COPIED_FROM_ADMIN` (`:381`) is the table: today
`solver_state.js` and the design tokens `tokens.css`, each copied byte for byte
from `src/nonogram/admin/static/`. The equality is checked at assembly time *and*
from the test tree, so the two copies cannot drift.

The practical effect is that "the public player makes the same state transitions as
the admin player" is true by construction. `play.js` turns input into
`clickStroke` / `dragStroke` / `resetStroke` / `record` / `undo` / `redo` calls and
paints what comes back; the admin's `solver.js` keeps the same division of labour
against the same module.

What is *not* shared is the UI glue, and the reason is in `play.js:16`: `solver.js`
is built around a Flask-rendered page with an embedded payload, a brush menu, zoom,
an error count, a hint button and a progress percent. This page fetches its puzzle,
has three brushes and no counters.

## Marking: three brushes, and the mark that had drifted

The public page offers `TOOLS = [FILLED, EMPTY, UNKNOWN]` (`play.js:83`) — the
`MAYBE` ("?") brush is the admin player's fourth and is not offered here.

An empty cell is drawn as a **centred dot**, 28% of the cell, as an `::after`
(`player.css:425`) — the mark `admin.css` draws for the same state. It was two
`linear-gradient` strokes here (a cross) until 2026-10-30, so the same mark meant
one thing in the panel and another on the public page; the owner chose the dot and
the divergence is closed. Like everything else shared between the two players, it
is reimplemented rather than imported: R3's byte-identical copy covers
`solver_state.js` and `tokens.css`, and nothing else, so `admin.css`'s rule is the
*look* this matches, not a file it reads.

## Solving is revealed, and the reveal is keyed on an attribute the page already writes

On the transition into solved, the banner settles in and the filled cells flash the
success colour in a diagonal sweep before ending in ink — about 0.8 s in all
(`player.css:440`-`456`). The sweep's per-cell delay reads `--player-wave`, which
`play.js:352` sets to `row + col` when it draws each cell, exactly as `solver.js`
sets it for `admin.css`'s copy of the same animation.

It is keyed on `body[data-solved="true"]` rather than on a class of its own,
because `play.js` already writes that attribute on every render (`:422`): the
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

One `localStorage` entry per puzzle key, under `nonogram-public:<key>`
(`play.js:191`). The save carries the clues it was made against and is refused on
replay if they do not match the fetched puzzle (`deserialize`, `:235`), so marks
cannot be replayed onto a different puzzle that happens to share a key.

There is no account, no server-side state, and **no write request of any kind** —
the only request the page issues is the `GET` of its own puzzle file, which is
asserted in a browser rather than argued:
`tests/test_public_player.py::test_no_write_request_for_any_interaction`.

## What the site is, and what is rebuilt rather than copied

See [diagrams/11-bundle-to-site.puml](diagrams/11-bundle-to-site.puml) for the
whole path, database to visitor, and where the solution stops on it.

`assemble.py` writes the deployable tree: the three pages, the two copies from the
panel, `vercel.json`, a `.player-site` marker (`:487`) that is how the script
recognises its own output before deleting it, and — rebuilt from the bundle — one
`puzzle/<key>.json` per puzzle, `index.json`, and one `book/<slug>.json` per book.

The rebuild is the point, and it is load-bearing for R2. CARD-282 shipped the
exporter and then measured a path straight through it: an owner renames a puzzle to
the base-64 of its own packed grid, the exporter writes that string into the
bundle's declared `title`, every guard passes, and the published JSON decodes back
to all 144 cells of a 12×12 answer. A scan cannot fix that — the set of encodings
of a grid is not enumerable, and CARD-282's denylist missed 7 of 7 planted
encodings. So the assembler does not filter free text; it **removes the channel**:
every served puzzle file is rebuilt from `SERVED_SCHEMA` (`:733`), which is
`("clues", "height", "key", "tier", "width")`, and a puzzle's `title` is in no
served schema at all. A field the schema does not name is dropped, named in the
report, and never written — the run prints `dropped (not in the served schema):
title`.

What is left is held to EC-048 by two statements that do different work:

- `clues` and `key` are **exempt**, not safe-by-measurement
  (`EXEMPT_SERVED_FIELDS`, `:541`): ADR-0041/R2 grants the exemption and R5 — the
  exporter taking every clue from `compute_clues` of the stored grid, upstream —
  is where their integrity actually lives;
- every other served value is drawn from a domain the module enumerates
  (`SERVED_VALUE_SPACE`, `:547`), with `width`/`height` recomputable from the
  clues, and `check_capacity` (`:572`) refuses to assemble unless the total free
  capacity is strictly below `MIN_SIZE * MIN_SIZE` bits.

A **book's** `title` is a different field and is *not* removed: the owner granted it
R2's third exemption on 2026-10-28 (`EXEMPT_LISTING_FIELDS`, `:902`), scoped to
`/b/<slug>`, with its residual declared rather than bounded — R2's own text
measures it at 100 of 100 cells recoverable if an owner writes a base-64 grid into
a book title. "This script removes the free-text channel" is therefore false as a
sentence about the whole site, and `assemble.py` says so about itself.

## Three doors, one document each

`vercel.json`'s rewrites are the host's whole routing table, and the fixtures route
by reading that file:

| URL | Serves | Why a rewrite |
|---|---|---|
| `/play/<key>` | `play/index.html` | one document plays every puzzle; `play.js` reads the key out of the path and fetches `puzzle/<key>.json` |
| `/b/<slug>` | `b/index.html` | the QR landing for one book |
| `/library` | `library/index.html` | the extensionless path needs the rule |

## Bounds and honest gaps

- **COMP-011 is in the registries and not in the C4 diagram.** `trace.yml:2632`
  carries the component with `code: ["player/**"]`; `c4/components-CTX-001.puml`
  does not mention it at all. This is the same drift [08](08-playing-a-stored-puzzle.md)
  records for CAP-007, one component wider.
- **Nothing is deployed yet.** `docs/deploy/player.md` records the host decision
  (DEC-045, Vercel) and the publish commands, and every value only the dashboard
  can supply — the production domain included — is still marked
  `TODO(owner)`. The QR base in that page is Vercel's default shape for a project
  of that name and has **not** been observed; CARD-210, which would print real
  scannable codes, is blocked on it and on the hosted solver.
- **Counting is opt-in and off by default.** The one script tag lives in
  `assemble.py`'s `ANALYTICS_SNIPPET` (`:413`) and is injected only when the
  endpoints are passed, so a local run and every test fixture assemble an
  uncounted tree.
- **EC-048's literal text is not satisfiable by any implementation of ADR-0041**,
  and `assemble.py`'s own docstring is where that is argued rather than here: R2
  carries three exemptions (the clues, the answer key, the book title) and four
  declared residuals.
- The bundle is exported by an **explicit** owner action and never as a side
  effect of finalising a book or generating a PDF (R5, `export_bundle`, `:336`).
  Only books out of draft reach it (`FINALIZED_STATUSES`, `:302`) — the route says
  so when the book you pressed it from is still a draft.

## Related

- [08-playing-a-stored-puzzle.md](08-playing-a-stored-puzzle.md) — the admin
  player, the shared state module, and why that one may ship the solution
- [07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md) — AGG-002, whose finalised books become `/b/<slug>`
- [09-the-three-inbound-adapters.md](09-the-three-inbound-adapters.md) — the door
  the public player is deliberately outside of
- `docs/deploy/player.md` — what is deployed where, the publish commands, and the
  owner steps still open
- ADR: [ADR-0041](../../../../meta/architecture/decisions/adr/0041-public-player-static-bundle-and-hash-urls.md) ·
  [ADR-0038](../../../../meta/architecture/decisions/adr/0038-puzzle-player-plain-js-and-playwright.md)
