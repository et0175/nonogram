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
**Wave:** 73
<!-- STAMPED 2026-10-31 at dispatch, opening wave 73. Wave 73's owner-named card, scheduled 2026-10-31 on "ok schedule it" and carried as NEXT TO START since. Premise re-checked at dispatch. Conflict profile measured EMPTY against CARD-338 and CARD-323. Declares the app.py hotspot, so any future card touching it serializes behind. OWES A RENDER: it changes owner-facing UI. -->
**Depends on:** —
**Touches:** docs/deploy/player.md, migrations/versions/018_book_player_domain.py, src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/player_bundle.py, src/nonogram/admin/print_specs.py, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/templates/book_setup_print.html, src/nonogram/db/models.py, tests/test_book_arrange_play_link.py, tests/test_book_page_spec.py, tests/test_book_player_domain.py, tests/test_player_bundle.py, tests/test_public_player.py
<!-- DERIVED 2026-11-03 in fix round 1 from `git diff --name-only main...HEAD` plus the working tree's own adds, minus this card file and the review YAML. Hand-editing is what left it wrong twice: the round widened it once (models.py, migrations/, and dropping tests/test_book_setup_print_mobile.py, which this card really does not touch and leaves passing as a G-3 control), and cycle 1 then measured two files still missing from it (tests/test_book_page_spec.py, tests/test_public_player.py). THE ONE OUT-OF-SCOPE ENTRY IS tests/test_public_player.py: this card repairs the guard that mechanically enforces ADR-0041/R3 there (see the fix-round note below), which is a shared file, so it belongs in any conflict graph measured over this wave. tests/test_book_arrange_play_link.py is new in fix round 1 (F-003). Three of the four ACs require the domain to be STORED with the book (AC-1 "stored with the book's print setup", AC-2 "a book with a stored domain", AC-3 "a book with no stored domain"), so a column — models.py, book_manager.py and a migration — was always what the ACs asked for, and player_bundle.py is where the one key recipe lives that the link must be built through. -->
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
Cycle 1 then measured the widened field **still** missing two files it had
changed, so it is no longer edited by hand at all: it is derived from
`git diff --name-only main...HEAD` plus the working tree's own adds (see the
field's own note).

Migration **018** deliberately departs from 013 and 017: **no server default and
no backfill**. Those two columns have a value every existing book already *is*
(every book printed black-and-white; every book printed its dividers), so a
default states the truth. Nobody has ever chosen a domain for any book — the
public player's first deploy was 2026-10-30 — so NULL means exactly "no base was
ever chosen", and the screen says so rather than printing a guess.

### ADR-0041/R2 applies to this diff, and holds

**Corrected in fix round 1 (cycle 1, F-006): the verdict was right and the
reasoning was not.** This section used to argue that R2 "governs public assets;
the arrangement screen is behind the panel's CON-015/CON-016 door and is not
one" — i.e. that R2 does not reach here. It does. R2 declares
`scope: {code: ["player/**", "src/nonogram/admin/**", "tests/**"]}`, so
`src/nonogram/admin/**` is inside its own stated scope, and for a reason: that
is where the exporter producing the public bundle lives. A reader who took the
old wording literally would conclude R2 never reaches `admin/`, which would
exempt the exporter itself — exactly the inference a later card would reuse.

**R2 applies, and it holds.** The link is `{base}` + `/play/` + the R1 key and
nothing else; the only solution-derived value this card adds anywhere is that
key, which R1 sanctions by name as a public projection ("one-way, so the URL
reveals nothing about the solution"); and nothing added reaches `player/`, the
exported bundle or the served site. The panel door (CON-015/CON-016) is why
this screen is not itself a public asset — a true and separate fact, and not
the reason R2 is satisfied.

AC-4 is held by a **whitelist on what the rendered fragment carries**, not a
scan for leak shapes — CARD-282's own lesson — and its ability to fail is
measured by two planted leaks (a title in an attribute, the grid's cells in a
query string), not assumed.

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

**And nothing held those two lines until fix round 1.** Cycle 1 measured it as a
surviving mutant: with both declarations deleted — the whole render-found fix
reverted — 159 tests across six modules still passed, because the markup is
byte-identical with the CSS gone and only the geometry regresses. A defect found
by a render and guarded by nothing is a defect found once.
`tests/test_book_arrange_play_link.py` now measures it in Chromium, on the
harness `tests/test_book_setup_print_mobile.py` established, and each
declaration is independently killed: deleting `.play-link`'s placement reds two
cells (the link leaves the title column), deleting `.play-url`'s wrapping reds
two more (the URL's 316 px line ends 149 px outside the card at 390 px), and the
reviewer's both-at-once mutant reds four.

### Fix round 1 (cycle 1 at 7.5): what changed, and the two things it is honest about

* **F-001 — the repaired R3 guard was incomplete.** This card replaced
  `tests/test_public_player.py`'s substring guard (which red on *prose*: a
  comment in `book_manager.py` tripped it) with an `ast` walk. The walk read
  only `node.module` for an `ImportFrom`, so `from scripts import
  assemble_player_site` — the most idiomatic spelling of the thing R3 forbids,
  and one `scripts/`'s PEP 420 namespace package really resolves — passed it,
  though the old guard had caught it. The repair removed a false positive and
  narrowed the true-positive surface at the same time; that is now closed (each
  alias is read qualified by its module), and all four plants red. A name
  assembled at run time from string pieces still survives, deliberately, and
  the guard's comment says so instead of claiming "both are checked".
* **F-003 — the render-found CSS fix is guarded** (see the section above).
* **F-007 — Copy now says what happened where it can be heard.** The outcome
  lived in `button.title` alone: not announced by a screen reader, invisible
  without a pointer, and on the no-`navigator.clipboard` branch nothing a user
  could perceive happened at all — the button looked inert. It is written to a
  `role="status" aria-live="polite"` region beside the button as well, and the
  AC-4 whitelist states the new region's vocabulary (`role`, `aria-live`,
  `status`, `polite`, the class) rather than tolerating it. Two Chromium cells
  hold both branches, and the pre-fix behaviour (title only) reds both.
* **F-004/F-005/F-008 — test-side.** AC-4's page-wide cell no longer excuses an
  href because it contains the base (the base is removed from the haystack
  instead); `play_links`' docstring states the one constraint its non-greedy
  regex has; and the port corpus now carries `:1`, `:65535` and `:65536`, which
  kills both one-character boundary mutants (`< _MAX_PORT`, `2 <= port`) that
  the 599-case corpus had let through.
* **F-009 — the registry entry is deliberately deferred, and CARD-210 owes it.**
  All four ACs here come from the owner, not from `requirements.yml`: FR-037
  (book print setup) gained no AC for the player-domain field and FR-045 covers
  the public player rather than the panel's authoring of it. Nothing is added to
  the registry from this card — a requirement written to match code just landed
  is not a requirement — but this card is deleted at `done`, and **CARD-210 is
  the card that owes FR-037 (or FR-045) the delta**, because it is the next
  reader of `print_specs.stored_player_domain` and `player_bundle.play_url` and
  will want something to trace to.

### Estimate: 0.5d, under by about 3x — a datum against the estimator, not against the round

Recorded here because a retro reads cards, not review YAMLs. Cycle 1 priced the
+1721 lines: 892 of them (52 %) are one test file, and genuine executable
production Python is **about 130 lines** plus a ~12-line migration, two templates
and two CSS declarations. The verdict was that 0.5d is **under-estimated by
roughly 3x and not because the work over-reached** — the card's own text mandated
every expensive part, and three of its four ACs say "stored", which is a column,
a migration and two storage modes to test. The calibration signal belongs to
whoever prices the next card of this shape: *a card whose ACs say "stored" is
never 0.5d.*

### Carried forward for CARD-210

The base it prints is `print_specs.stored_player_domain(book)`; the URL it encodes
is `player_bundle.play_url(base, key)`. Neither needs re-deciding, and a book with
no stored base must print no QR code rather than a guessed one — the same posture
this screen takes.

### [Merge gate 2026-11-03] cycle 2's two low findings closed, and three recorded

**Its own `Touches:` carried the parsed-field defect CARD-341 names, and so did
`Wave:`.** Found by running `card_lint.parse_card_fields` over this file rather
than reading it: an inline `<!-- -->` is stripped by no parser, and
`extract_touches` splits on commas, so the comment's prose became **28 "globs"
where 15 were declared** — and `tests/test_public_player.py`, the last real
entry, arrived concatenated with the comment's opening and **no longer matched
itself**, which is how `compute_excess` reports a declared file as excess.
`Wave:` parsed as the whole comment instead of `73`, and
`find_runtime_field_format_issues` reported it malformed. Both comments now sit
on their own line; re-measured, `Wave` is `'73'` and `Touches` is 15 globs with
no fragment. The one remaining malformed field is `Branch`, whose backticks are
**board-wide convention** (CARD-316, 323, 329 and 338 all carry them) and not
this card's to change.

**F-203 — bounded, not reset.** The live region was a fourth item on
`.play-url`'s flex line, and the squeeze it caused is reproduced here exactly as
cycle 2 measured it: **98.984375 px -> 30.5 px** at 390 px. The choice was
between resetting the two failure branches and bounding the region, and
**bounding won on the text's own purpose**: `copyPlayUrl` clears only `Copied`,
which is transient by design, while both failure branches end in *"select the
link and copy it"* — an instruction to act on. A timer that erased it would undo
what F-007 added for exactly the user who cannot see the button's `title`. So
the region moved off that line instead: `.play-link` is now a block holding a
`.play-link-row` flex line (URL + button) and the region beneath it as
`d-block`. The squeeze cannot now *occur* in any branch, which is stronger than
cannot *persist*, and the message stays readable. An empty block adds no height,
so a silent row measures as it did before. `copyPlayUrl` had to move from
`button.parentElement` to `button.closest('.play-link')`, since the button's
parent is now the inner row.

Measured both ways. `test_what_the_region_says_takes_no_width_from_the_url` is
new and is the geometry cell the round did not have — at **390 px**, on the
longest message, on the branch that never clears (the existing cell reads text,
at 1024 px only). Edge mutant: putting the region back on the flex line reds
**that cell and only that cell**, with `[(98.984375, 30.5)]`.

**F-204 — the click is bounded at 2 s, the module's own precedent.**
`_CLICK_TIMEOUT_MS`, beside `_SAID_TIMEOUT_MS`, on both existing clicks and the
new one. Re-measured after: deleting `.play-url`'s declaration now reds **6**
cells (the five cycle 2 measured, plus the new one, which fails the same way) in
**10.31 s** against a **9.95 s** clean baseline — where the round measured
**66.91 s** against 7.53 s. The cause is unchanged and now arrives at once:
*"`card-body` ... subtree intercepts pointer events"*. The 57 retries bought no
information; only the first message ever had any.

**Recorded, not fixed.** F-201: the round's "25 modules / 1744 passed" named no
modules and so was not re-derivable from the card; cycle 2's own figures and
module list are in `meta/review/CARD-332-cycle2.yml`. F-202: the DB arming is
load-bearing for **6 cells in four other modules**, not for this card's own
module, whose `[db]` cells run on a shared SQLite fixture. F-207:
`_PLAYER_ORIGIN` bounds the port but neither the host label nor the host length,
so a 300-character host would be stored and printed. F-205 is closed on main —
`meta/impact/` is gitignored there (`.gitignore:77`); it still showed untracked
in this worktree only because the branch forked before that commit, and the
merge carries it.

**Not a finding of cycle 2's and not fixed here:** this card adds
`tests/test_book_arrange_play_link.py` and appends **no row** to
`tests/README.md`, which `meta/kanban/config.yml` names as a hotspot on the
grounds that "every card with tests appends a line". Nothing enforces it
mechanically, so the suite is green either way, and adding it would widen a
`Touches:` this round has already had wrong twice. Left to the board.

### [Merge gate 2026-11-03] the first gate was RED, by my own hand, and AC-4's inventory is what caught it

Recorded because a gate that reds and is then made green silently is worse than
one that never red. Full suite on the merged tree, run 1: **4 failed / 10229
passed / 1 skipped / 1 xfailed**, exit 1, 1568 s. All four in this card's own
new module, both parametrisations of two cells in
`TestPlayerDomain_NothingButTheKeyReachesTheLink`.

The cause was **F-203's template restructure**, three commits earlier in this
same gate. `inventory()` is AC-4's exhaustive allow-list of the link markup's
vocabulary — tag names, attribute names, attribute **values** and text — and its
own docstring promises the consequence: *"A stylesheet change that renames a
class reds the test using this, and the fix is to state the new name."* Moving
the live region off the flex line renamed all three class attributes
(`play-link d-flex align-items-center gap-2 small` -> `play-link small`, a new
`play-link-row d-flex align-items-center gap-2`, and `d-block` onto the region),
so the check fired exactly as designed. The fix is the three names, stated.

Verified exact rather than merely green: an `ast` read of the literal against
the class attributes the template emits shows **6 of 6 allowed and no stale
class-shaped entry** — an allow-list keeping a name the markup no longer emits
would permit a shape nobody renders.

**The process lesson is mine.** Before merging I ran the module I had edited
(`tests/test_book_arrange_play_link.py`, 9 green) and not the card's impact
scope. The leakage inventory lives in a *different* module from the template it
describes, so the one module I chose could not see the break. Run 2 covered the
five `Touches` test modules together — **300 passed** — before the full suite was
re-run.
