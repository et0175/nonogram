# CARD-332: The panel learns the player's domain — a print-setup field, and the real per-puzzle link beside each arranged puzzle

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** `card/332-the-panel-learns-the-players-domain`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-332
**Source:** owner, 2026-10-30, after the public player's first deploy ("I'd add an input field for a domain string there also (on print setup) and then on arrangement page add a link (read-only) next to a puzzle (e.g. https://nonogram.adverax.io/play/073280edd0)"). The deploy that makes a real link possible is recorded in `docs/deploy/player.md` ("What production is").
**Idea:** —
**Wave:** 73 <!-- STAMPED 2026-10-31 at dispatch, opening wave 73. Wave 73's owner-named card, scheduled 2026-10-31 on "ok schedule it" and carried as NEXT TO START since. Premise re-checked at dispatch. Conflict profile measured EMPTY against CARD-338 and CARD-323. Declares the app.py hotspot, so any future card touching it serializes behind. OWES A RENDER: it changes owner-facing UI. -->
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/print_specs.py, src/nonogram/admin/book_manager.py, src/nonogram/db/models.py, migrations/versions/018_book_player_domain.py, src/nonogram/admin/player_bundle.py, src/nonogram/admin/templates/book_setup_print.html, src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/static/admin.css, docs/deploy/player.md, tests/test_book_player_domain.py, tests/test_player_bundle.py <!-- WIDENED 2026-11-01 in the round: the decompose-time Touches was under-specified, not the work. Three of the four ACs require the domain to be STORED with the book (AC-1 "stored with the book's print setup", AC-2 "a book with a stored domain", AC-3 "a book with no stored domain"), so a column — models.py, book_manager.py and a migration — was always what the ACs asked for, and player_bundle.py is where the one key recipe lives that the link must be built through. -->
**Review score:** —
**Started:** 2026-10-31T12:18:26+00:00
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## [Scheduled 2026-10-31] — premise verified at the queue, every anchor exact

**Scheduled on the owner's instruction while wave 72's two slots were full**, so it is
next to start when one frees. Its premise was checked before scheduling, per the rule
four cards of the vector family produced: a card whose premise rests on cited code
should have that code resolved before it is queued, not in its first hour.

**All seven anchors this card cites hold exactly**, measured 2026-10-31:

| the card cites | measured |
|---|---|
| `app.py:3593`, the setup-print route | **exact** |
| `app.py:4839`, the arrange-puzzles route | **exact** |
| `app.py:3329`, the `is-invalid`/`aria-invalid` refusal pattern | **exact** |
| `print_specs.py`'s validator family | all three present — `validate_trim_size`, `validate_margins`, `validate_interior_ink_mode` |
| `player_bundle.puzzle_key` | `src/nonogram/admin/player_bundle.py:215` |
| `templates/book_setup_print.html`, `book_arrange_puzzles.html` | both exist |
| `tests/test_book_setup_print_mobile.py`, `tests/test_player_bundle.py` | both exist |

**Why the line numbers are not stale, unlike the sibling cards':** nothing in waves 70
or 71 touched `src/nonogram/admin/app.py`. Those waves were test-side and registry-side
(CARD-317/318 in `requirements.yml`, CARD-330/331 in `tests/`), which is also why
CARD-316 arrived with 7 of 7 of its `requirements.yml` lines stale while this card
arrived with none. **That is a fact about what moved, not a guarantee** — re-derive any
anchor at the start of the round rather than trusting this table, which is a dated
reading like every other figure on this board.

**Conflict profile, measured rather than assumed.** Intersection is **EMPTY** against
every card that could contend: CARD-329 and CARD-316 (both in flight), the tails
CARD-278 and CARD-320, the destination CARD-322, and CARD-210. So it can start the
moment a slot frees, beside anything.

**But it declares a hotspot: `src/nonogram/admin/app.py`.** Nothing currently active
declares it, so there is no edge today — and any future card that declares it must
serialize against this one. Say so at dispatch rather than discovering it.

**Priority note, stated because it inverts the queue.** This is **P2** and it is being
placed ahead of **CARD-320 (P1)**, on the owner's instruction after the public player's
first deploy. The reasons are its own: 0.5d, owner-facing, free of every other card, and
it closes a gap the owner hit in use rather than one the board inferred. CARD-320's P1
stands on a real defect (a float reaching `uuid.UUID` through `add_puzzle`, visible only
under the full suite) and it keeps its place immediately behind.

**One thing this card owes that the test-side cards did not.** It changes owner-facing
UI — a form field and a per-puzzle link — so a green suite is not the whole gate. The
round should produce a **rendered check of both pages** for the owner (the print-setup
form with the field, including its refusal state, and the arrangement page showing a
real `{base}/play/{key}` beside an arranged puzzle), filed under
`~/Documents/nonogram-reviews/CARD-332/`. The link's own value is derivable:
`puzzle_key` is ADR-0041/R1's ten hex characters computed from the stored grid, so the
render can be checked against a key derived independently rather than eyeballed.

## What to implement

Two owner-facing pieces, and one decision that has to be made before either is written.

**1. A player-domain field on book print setup** (`GET/POST
/book/<book_id>/setup-print`, `app.py:3593`, template `book_setup_print.html`). One text
input holding the base of the public player, e.g. `https://nonogram.adverax.io`. It
joins the existing posted fields (`width`, `height`, `unit`, `interior_ink_mode`,
`interior_divider_pages`, `interior_divider_pages_present`, `plan_count`), is validated
inward of the route as a pure function — `print_specs.py` is where that family of
validators lives (`validate_trim_size`, `validate_margins`,
`validate_interior_ink_mode`) — and re-renders with the field marked
`is-invalid`/`aria-invalid` on refusal, the pattern `setup_print` already establishes
(`app.py:3329`).

**2. A read-only per-puzzle player link on the arrangement page**
(`GET/POST /book/<book_id>/arrange-puzzles`, `app.py:4839`, template
`book_arrange_puzzles.html`). Beside each arranged puzzle, the URL a reader would open:
`{base}/play/{key}`, where `key` is `player_bundle.puzzle_key(grid)` — ADR-0041/R1's
ten hex characters, computed from the stored grid. Read-only: displayed and copyable,
never an input. The owner's example is
`https://nonogram.adverax.io/play/073280edd0`.

### The one decision this card must not duck

**Where the base comes from, and therefore how many places can disagree about it.**

Today there is exactly one: the `qr-url-shapes` block in `docs/deploy/player.md`, which
`scripts/assemble_player_site.py` parses and
`tests/test_public_player_pages.py::test_the_qr_url_shapes_here_are_the_shipped_routes`
holds to `vercel.json`'s own rewrite sources. Adding a form field creates a second. This
project has repeatedly paid for a second copy of a fact (see `CLAUDE.md`'s account of the
retired component map, and `render.yaml`'s "NOT AUTHORITATIVE" header), so the card picks
one of these deliberately and writes the reason down:

- **(a) The page is the default, the field overrides per book, and the stored value is
  what a printed book records.** The owner's stated intent. It has a real argument
  behind it: a printed run must preserve *what was printed*, and a book printed before a
  domain change cannot be fixed, so the value belongs with the book, not only with the
  deploy page. Cost: two sources, and the page is no longer the single authority — which
  means the card owes a stated rule for which one wins where, and a test that holds it.
- **(b) The page stays the only source and the field is removed from scope.** Cheapest
  and keeps one authority, but it makes the per-book record impossible and leaves the
  owner editing a markdown file to change a domain.

**Do not resolve this in the worktree by picking whichever is easier to code.** If (a),
the stored base is a *book* attribute (it travels with the book's print setup, like the
trim size) and the arrangement page shows the link built from the book's own value — and
CARD-210 then prints from the stored value, which is what makes a printed book
self-describing. Say so in the card's notes and add the control.

### Bounds

- **No QR pixels here.** Drawing real scannable codes into the PDF is CARD-210, which
  was unblocked the same day. This card is the panel's side only: a field and a readable
  link. Keep the two separable — CARD-210 should be able to read the base this card
  settles without re-deciding it.
- **`puzzle_key` has exactly one implementation** (ADR-0041/R1, `player_bundle.py:215`).
  Import it; do not spell the hash again in a template or a route. R1 makes any change to
  the recipe a breaking change to every printed book.
- **The arrangement page must not become an export path for answers.** It runs behind the
  panel's door, so showing a key is fine (the key is one-way and ADR-0041/R1 sanctions it
  as a public projection) — but the link is built from the key and nothing else. No
  title, no grid, no solution in a URL, on a page or in a copy button.
- **A book with no stored base.** Decide and state what the arrangement page shows then —
  the page's base, a relative path, or an explicit "no domain set" with a link to print
  setup. Silently rendering `None/play/<key>` is the failure this bullet exists to
  prevent.

## Acceptance criteria

Derived from the owner's request, not from `requirements.yml` — FR-045 covers the public
player, not the panel's authoring of it. **Confirm these before starting; they are what
the AC gate will hold the work to.**

- **AC-1** — *Given* a book at print setup, *when* the owner submits a player domain,
  *then* it is stored with the book's print setup and shown on return to that page;
  *and when* the owner submits a value that is not an absolute `https://` origin, *then*
  the form re-renders with that field marked invalid and nothing is stored.
- **AC-2** — *Given* a book with arranged puzzles and a stored domain, *when* the owner
  opens the arrangement page, *then* each puzzle shows the read-only URL
  `{base}/play/{key}` whose `key` equals `player_bundle.puzzle_key` of that puzzle's
  stored grid.
- **AC-3** — *Given* a book with **no** stored domain, *when* the owner opens the
  arrangement page, *then* it says so plainly and links to print setup, and renders no
  URL built from a missing base.
- **AC-4** — *Given* any book, *when* the arrangement page renders, *then* no puzzle
  title, grid or solution cell appears in any link, attribute or copy target on it.

## Engineering constraints

- **EC** — the key on the page is computed from the stored grid through the one
  implementation (`player_bundle.puzzle_key`), for every puzzle, on every render; a
  second spelling of the recipe anywhere in `admin/` or in a template is a defect
  regardless of whether it agrees today (ADR-0041/R1).

## Guardrails

- G-1: The public player (`player/**`) and the bundle exporter's served schemas are not
  touched. This card changes what the *panel* shows, not what the site serves.
- G-2: `docs/deploy/player.md`'s `qr-url-shapes` block and the tests that read it keep
  working. If decision (a) above makes the page no longer the single authority, the page
  must say so in its own words — do not leave it asserting something the code has
  stopped honouring.
- G-3: Print setup's existing fields and their validation behaviour are unchanged
  (test: the existing `tests/test_book_setup_print_mobile.py` cases).
- G-4: No new runtime dependency. A QR encoder is CARD-210's problem and
  ADR-0006/R1's baseline question; nothing here needs one.

## Architecture context

- **FR:** FR-045 (the public player and its bundle — this card authors the base that
  phase's URLs are read with), FR-037 (book print setup, the form this field joins)
- **ADR:** ADR-0041 (R1 the key recipe, R7 the slug, R2 what a public asset may carry),
  ADR-0035 (the book's plan and its readiness gate, which this form belongs to)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml
- **Related cards:** CARD-210 (real QR pixels in the PDF — unblocked 2026-10-30, reads
  whatever base this card settles), CARD-204 (the 2x2 cm slot and the placeholder glyph),
  CARD-285 (the deploy page this base is recorded in)

## Worktree notes

### The decision: (a), and the rule that keeps two sources from being two authorities

**(a) was taken** — the base is a **book attribute**, stored beside the trim by the
same Print setup submission, and the arrangement page builds each link from the
**book's own** value and from nothing else. The owner's reason is the one that
decided it: a printed run records *what was printed*, and a book printed before a
domain change cannot be fixed. A base read from the deploy page at print time
would be right for the deploy and wrong for the book.

The card demanded a stated rule for which source wins where, and a test that
holds it. The rule, written into `docs/deploy/player.md` itself (G-2) so the page
no longer asserts something the code has stopped honouring:

* **For a book** — the book's stored `player_domain` wins, always. Nothing else
  is consulted, not even as a fallback.
* **For the deploy** — `docs/deploy/player.md`'s `qr-url-shapes` block wins, and
  keeps the meaning it always had: the shapes production serves and the base it
  serves them at **today**. It is what the owner copies into Print setup; no code
  reads it.
* The two **may** disagree once a domain moves, and that is the intended state:
  books printed before the move keep the base they were printed with.

What holds it: `tests/test_book_player_domain.py::TestPlayerDomain_ABookWithNoDomainSaysSo`
is the test that the page is **not** a fallback — a book with no stored base shows
no URL at all, and `test_no_url_is_rendered_from_a_missing_base` names both
spellings of the failure (`None/play/<key>` and `/play/None`) so a future reader
sees they were checked. `tests/test_public_player_pages.py`'s existing block test
still passes unchanged, so G-2's mechanism is intact.

### Three states, and why there is no hidden companion field

CARD-305's divider checkbox needed `interior_divider_pages_present` because an
unticked box posts **nothing**, so "off" and "this form has no such control"
arrive identically. A **text input always posts its name**, so the field is its
own marker and three states arrive distinguishably:

| the submission | the column |
|---|---|
| no `player_domain` field at all | unchanged (a client built before this control) |
| `player_domain=` (blank) | cleared — no domain stored |
| `player_domain=https://...` | the owner's base, normalised |

The discriminating cell is
`test_a_submission_without_the_field_leaves_the_stored_base_alone`, **driven from
a base that is SET** — from "no base" it could not fail, because absent and
cleared both leave NULL. Measured: deleting the route's marker guard
(`if "player_domain" in request.form:` -> `if True:`) and deleting
`book_manager._apply_print_spec`'s `if spec.player_domain is not None:` guard each
red exactly that cell, in both storage modes.

### Touches was under-specified; the migration is not scope creep

The decompose-time Touches named no `models.py` and no `migrations/`, and the
round was briefly flagged for writing one. Three of the four ACs require the
value to be **stored** ("stored with the book's print setup", "a book with a
stored domain", "a book with no stored domain"), so a column was always what
they asked for. Touches was widened in the round rather than the work narrowed.

Migration **018** deliberately departs from 013 and 017: **no server default and
no backfill**. Those two columns have a value every existing book already *is*
(every book printed black-and-white; every book printed its dividers), so a
default states the truth. Nobody has ever chosen a domain for any book — the
public player's first deploy was 2026-10-30 — so NULL means exactly "no base was
ever chosen", and the screen says so rather than printing a guess.

### ADR-0041/R2, checked rather than assumed

The link is `{base}` + `/play/` + the R1 key and nothing else. R2 governs
**public assets**; the arrangement screen is behind the panel's CON-015/CON-016
door and is not one, and the only solution-derived value this card adds anywhere
is the key, which R1 sanctions by name as a public projection ("one-way, so the
URL reveals nothing about the solution"). AC-4 is held by a **whitelist on what
the rendered fragment carries**, not a scan for leak shapes — CARD-282's own
lesson — and its ability to fail is measured by two planted leaks (a title in an
attribute, the grid's cells in a query string), not assumed.

### The key: one recipe, one caller

`player_bundle.puzzle_key_of_record` was added so the panel's screens, which hold
*records* rather than grids, reach R1's one implementation through the module
that owns it instead of respelling the hash in a route or a template. It reuses
the exporter's `_grid_of`, which is also what refuses a stored value that is not
a grid — a string is sliceable and would otherwise hash as a column of cells.
`play_url` joins the base to `docs/deploy/player.md`'s `play` shape and refuses a
blank base, which is the `None/play/<key>` failure the card's own bounds named.
`TestPlayerDomain_OneRecipe` holds `sha256`/`hexdigest` in `admin/` to
`player_bundle.py` and `puzzle_review.py` (whose `_grid_fingerprint` is a
different value for the same cells and is named rather than tolerated).

### One thing the first render caught that no test would have

The link went into `.item-info`, a flex row — and a 43-character URL widened that
column until the title box and the row's buttons were pushed out of the card. The
suite was green through it. It is now a third grid row (`.play-link`), which cost
two lines of `admin.css`, and the re-render is clean. Renders are in
`~/Documents/nonogram-reviews/CARD-332/`.

### Carried forward for CARD-210

The base it prints is `print_specs.stored_player_domain(book)`; the URL it encodes
is `player_bundle.play_url(base, key)`. Neither needs re-deciding, and a book with
no stored base must print no QR code rather than a guessed one — the same posture
this screen takes.
