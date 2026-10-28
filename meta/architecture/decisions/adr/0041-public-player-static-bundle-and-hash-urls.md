# ADR-0041: The public player is a static site on Vercel, keyed by grid content hash, counted by GoatCounter

**Status:** Accepted
**Date:** 2026-10-23
**Deciders:** Olga (project owner)
**Revised:** —
**Migration:** on-touch
**Pattern:** —
**API-Posture:** —

## Context

The owner decided on 2026-10-23 (ONLINE_GAME_SPECIFICATION.md "Technical
Architecture", commit 8b0ca0e2) to build the public phase ADR-0038/R6 always
anticipated: a puzzle player that printed-book QR codes point at, plus online
browsing of the published puzzles — routes `/play/<key>`, `/b/<slug>`,
`/library`, one player app for both doors. Until now CON-021 confined
interactive play to the admin panel's player behind the CON-015 / CON-016
door, precisely because that player ships the puzzle's solution grid to the
browser for its error count; ADR-0038/R6 said in as many words that any
public phase reopens that ADR. This ADR is that reopening — it resolves the
three decisions the public phase cannot start without (DEC-044 the per-puzzle
URL namespace, DEC-045 the hosting, DEC-046 usage counting), decided together
because they are one coherent shape: what a printed QR code resolves to,
forever.

Three facts drive everything here. First, **a printed book is frozen**: a QR
code on paper cannot be re-pointed, so the URL under it must outlive any
database, host or re-seed — this is why CARD-282 was forbidden to pick a key
shape by default, and why the backlog's CARD-210 note says "a printed code
cannot be re-pointed". A hash whose domain is unstated has burned this
project before, so the key's exact recipe is a rule below, not prose. Second,
**the admin service must never carry customer traffic**: the deployed panel
is a free-tier Render service that spins down, so a QR scan through it would
wait 30–60 s on a cold start — the worst possible first contact with the
product — and every public request at the admin origin widens an attack
surface CON-015 / CON-016 exist to keep small. Third, **the public player
never has the answer**: ADR-0038/R6 stands unweakened. Completion is instead
detected as "every row and column clue satisfied", which for a uniquely
solvable puzzle — the generator's one mandatory property (CON-005) — is
exactly the solution. R6 is satisfied by construction, not relaxed.

The data the player reads is a **player bundle** (TERM-040): static JSON the
admin panel exports at publication time — `index.json` (the library),
`puzzle/<key>.json` (clues and metadata per puzzle, keyed by the grid hash),
`book/<slug>.json` (a book's ordered puzzle keys, keyed by the book slug).
The player itself is plain hand-written JS/CSS — the stack ADR-0038 chose —
in a top-level `player/` directory outside the Python package, reusing the
admin player's pure state module (`solver_state.js`, split out by CARD-160
for exactly this) by build-time copy, never by edit.

## Decision

**DEC-044 — the per-puzzle public URL namespace is a grid content hash.**
A puzzle's public key is the first 10 lowercase hexadecimal characters of
SHA-256 over the UTF-8 bytes of the string `"{width}x{height}:"` followed by
the solution grid's cells in row-major order, `'1'` for a filled cell and
`'0'` for an empty one. (Example: a 2x2 grid with only the top-left cell
filled hashes the bytes of `"2x2:1000"`.) The key is deterministic and
recomputable from the puzzle itself: a printed book preserves the grid
forever, so the key survives any database re-seed or loss. It is one-way, so
the URL reveals nothing about the solution. Identical grids share a key by
design — the key names the puzzle content, not the row. The recipe is pinned
as R1; any change to any part of it (the prefix, the separator, the cell
encoding, the algorithm, the truncation length or case) is a breaking change
to every printed book and requires a new ADR.

**DEC-044b — a finalized book's public slug is a content hash of its puzzle
keys, and deliberately not of its title.** A book's public slug is the first 10
lowercase hexadecimal characters of SHA-256 over the UTF-8 bytes of the string
`"book:"` followed by the book's puzzle keys in book order, concatenated. Every
key is exactly 10 characters by R1, so the concatenation needs no separator to
be unambiguous — the same prefix-then-fixed-width-payload shape R1 already uses.

**Why a content hash, and why the title is excluded.** The slug is printed in a
QR code (`/b/<book-slug>`), and *a printed QR code cannot be re-pointed*. So the
slug must be recomputable from what the printed artefact preserves and must not
move when anything editorial changes:

- **Not stored on the row.** This ADR already rejected a stored opaque slug for
  puzzles, under "Stored opaque slug per puzzle", for the reason that applies
  identically here: a stored slug "is stable only as long as the database and
  its backups are", and a re-seed loses it. A content hash survives a re-seed
  because the printed book preserves its puzzles.
- **Not derived from the title.** A title is editorial: typos get fixed,
  subtitles get added, a series gets renamed. Hashing the title would mean a
  one-character correction in the admin panel silently breaks every QR code in
  an already-printed run. **Owner decision 2026-10-24, taken explicitly against
  the alternative of hashing `"book:{title}:"` plus the keys, which CARD-282
  implemented before this rule existed.**
- **Not human-readable.** A readable slug (`/b/snowflakes-easy-vol-1`) is
  friendlier to type off a cover, but it needs a uniqueness registry — which
  puts the slug back in the database — and it moves when the title is edited.
  Both costs are the ones above.

The remaining sensitivity is deliberate and accepted: the slug **does** change if
the book's puzzle membership changes. That is a real change of content rather
than an editorial one, and INV-012 already makes it an explicit, confirmed act
on a book that has left draft. A reprint with different puzzles is a different
book and may have a different URL.

The recipe is pinned as **R7**, and as with R1 any change to any part of it — the
prefix, the ordering, the absence of a separator, the algorithm, the truncation
length or the case — is a breaking change to every printed book and requires a
new ADR.

**DEC-045 — the static host is Vercel.** The `player/` tree plus the exported
bundle deploy to Vercel as a static site: no cold starts, CDN delivery, free
tier sufficient. The admin panel's Render service stays untouched and never
serves public traffic.

**DEC-046 — usage counting is GoatCounter.** Cookieless, no consent banner,
free; counts visits, estimated uniques, country and device. The per-book slug
in the QR URL (`/b/<book-slug>`) is the primary per-book signal. Nothing we
ship stores a raw IP or any per-visitor identifier: an IP is personal data
under GDPR, and carrier NAT makes it a bad unique key anyway. The pages must
work with the analytics script blocked or absent.

**The public player's standing properties** (R2–R6 below): static files only,
same plain-JS stack as ADR-0038, no framework, no build toolchain, no npm; no
solution grid or solution-derived data in any public asset; play state in the
visitor's browser localStorage only, zero write requests, no accounts; the
bundle is exported by an explicit admin action, read-only against the
database, deterministic (same input, same bytes, so a bundle diff is
meaningful at deploy time). CON-021 is amended the same day to describe the
two players — admin and public — and keep forbidding everything else.

## Alternatives considered

### Stored opaque slug per puzzle (DEC-044)
A random short slug minted at publication and stored on the row. Friendlier
to the eye than a hash and free of the shared-key property. Rejected: the
slug is stable only as long as the database and its backups are. A re-seed,
a lost volume or a migration mistake orphans every QR code already printed —
and this project has already re-seeded its store once. The hash needs no
custody at all: the grid in the printed book IS the key material.

### Database row id (DEC-044)
Zero new code. Rejected outright: row ids change on re-seed, renumber on
re-import, and leak store ordering. Printed books outlive databases.

### Render static site (DEC-045)
The same dashboard as the admin service — one place to look, which was
genuinely tempting given the memory cost of a second dashboard. The owner
chose Vercel; capability-wise the two are close, and the deploy doc carries
the choice so it is documented rather than remembered.

### Cloudflare Pages (DEC-045)
Equally capable static hosting. Not chosen; nothing argued against it beyond
the owner picking Vercel — a swap later is a redeploy, not a rewrite, because
the artifact is one directory of static files.

### Serving the player from the admin Flask service (DEC-045)
One deploy, no new dashboard, and the bundle step disappears. Rejected on
both driving facts: the free-tier service spins down, so a QR scan pays a
30–60 s cold start at the exact moment a curious reader is deciding whether
the product is alive; and it puts anonymous public traffic on the origin
whose whole security story (CON-015 / CON-016) is that only the owner
reaches it.

### Plausible (DEC-046)
Equally fine on privacy, paid where GoatCounter is free. Rejected on cost
only; the integration is one script tag, so swapping later is trivial and
R6 names the service precisely so a swap is a conscious ADR touch, not drift.

### Homegrown IP logging (DEC-046)
Rejected outright: it stores personal data (GDPR) for a metric carrier NAT
makes unreliable anyway, and it would be the public phase's first server-side
write — the thing R4 exists to forbid.

## Consequences

### Positive
- A printed QR code's URL can always be regenerated from the book itself:
  the namespace survives database loss, re-seeds and host migrations.
- The one-way key means the URL leaks nothing about the solution, and R2
  keeps every public asset clean of it: the public surface never has the
  answer, so it cannot lose it.
- No cold start on a QR scan; customer traffic never touches the admin
  origin, so CON-015 / CON-016's surface is unchanged.
- No consent banner, no cookie, no stored IP: the analytics posture needs no
  GDPR machinery at all.
- Static files only: the deployable artifact is one directory, testable with
  a plain file server and the existing pytest-playwright extra, with no new
  runtime dependency (ADR-0006/R1 untouched).
- Deterministic export makes "did the bundle change?" a byte diff at deploy
  time.

### Negative
- Identical grids share a URL by design: two published puzzles with the same
  solution grid are one public page, and if that is ever wrong for a real
  pair the namespace cannot distinguish them without a new ADR.
- A hash URL is unreadable and unguessable: nobody types or remembers
  `/play/3fa9c04b1d`, so sharing relies on links and QR codes, not memory.
- Vercel is a second deployment dashboard to document and remember beside
  the admin panel's Render dashboard — the exact cost the rejected
  Render-static alternative avoided; docs/deploy/player.md carries it.
- Bundle re-export is a manual owner action that can be forgotten: a book
  finalized but never exported has QR codes pointing at keys the site does
  not serve. The soft not-found page (CARD-284) is the mitigation, not a
  fix.
- The clue-satisfaction solved check is correct only because every published
  puzzle is uniquely solvable; CON-005 and INV-002 are now also what keeps
  the public player honest.

### Neutral
- The admin player and its error count are unchanged; the public player has
  no error count because it has no solution, and adding one publicly is a
  new architecture question, not a worktree decision.
- GoatCounter is named in R6, so swapping analytics is a one-line ADR
  revision plus a script tag, never silent drift.
- `player/` is a top-level directory outside `src/nonogram/`, so the import
  guard's walk and the Python package are untouched; COMP-011 registers it
  in the component map's trace.

## References

- DEC-044, DEC-045, DEC-046 (resolved by this ADR)
- CTX-001; CAP-007 Puzzle play; COMP-009 (bundle export), COMP-011 (Public
  Player, registered with this delta)
- FR-045 (the public player and its bundle; AC-380..AC-392, EC-048..EC-050);
  FR-044 (the admin player the public one mirrors); FR-005 (`compute_clues`,
  the one encoder)
- CON-021 (amended 2026-10-23 to the two-player form); CON-015, CON-016,
  CON-017; CON-005 / INV-002 (uniqueness, which the clue-satisfaction solved
  check rests on)
- ADR-0038 (plain-JS stack, R6 the no-solution line — History notes this
  ADR as the public phase it anticipated), ADR-0006 (dependency baseline,
  untouched), ADR-0030 (the admin door that stays private)
- ONLINE_GAME_SPECIFICATION.md "Technical Architecture" (owner, 2026-10-23,
  commit 8b0ca0e2); meta/kanban/cards/CARD-282..285

## History

- 2026-10-24: **R7 added — the book-slug recipe, which this ADR named but never
  specified.** CARD-282's implementation round found that the Decision, the file
  layout (`book/<slug>.json`) and DEC-046's tracking paragraph all refer to "the
  book slug" while no recipe appears anywhere in this ADR, FR-045, TERM-040/041
  or the glossary. It implemented one, declared in its own docstring as the
  card's choice rather than this ADR's, and raised it — which is the correct
  shape for a gap of this kind: a recipe printed in a QR code is an
  architectural decision, not an implementation detail. **The owner resolved it
  2026-10-24 and chose to hash the puzzle keys ALONE**, against the shipped
  variant that also hashed the title, so that an editorial title edit cannot
  break an already-printed run. R7 and DEC-044b record it. CARD-282 is being
  revised to R7 before it merges, so no code cites a rule this ADR does not
  contain.

- 2026-10-28: **R2 gains its third exemption — a book's own display title —
  by owner decision, and the amendment exists because an FR cannot narrow a
  mandatory rule.** CARD-284 shipped the title on `/b/<slug>` with the
  justification that "EC-048's enumeration does not name it". That is true of
  EC-048's first three items (a solution grid, a filled-cells encoding, the
  picture name) and **false of its fourth clause** — "or data from which any
  solution cell is recoverable" — which is R2's own wording and is not an
  enumeration anything can fail to be named in. The card's own measurement
  settles it: a title can carry a `MIN_SIZE` grid's base-64 in 20 of its 120
  characters, and the round measured **100 of 100 cells** coming back. So the
  served title was outside R2 as written, while R2's check ref stayed live and
  green — the defect being that the next card's system-rules run would read a
  violated mandatory rule as mechanically checked. CARD-284's review cycle 2
  found it (F-001) with an addition mutant: changing the bundle fixture's
  hardcoded title to a leaky one makes R2's own served-half test fail, while
  another test in the same suite asserts that exactly that leak succeeds —
  two tests, opposite outcomes, one mandatory rule, discriminated only by a
  fixture constant. The owner was asked and chose to amend R2 rather than
  withdraw the title or derive a label from the slug. **What was NOT done:**
  the residual is not narrowed, no cap is claimed as protection, and the
  picture name is untouched. R2 is now weaker than it read on 2026-10-27 and
  says so in its own statement.

- 2026-10-23: Created. Resolves DEC-044 (grid content hash: first 10
  lowercase hex of SHA-256 over `"{width}x{height}:"` + row-major `'1'`/`'0'`
  cells), DEC-045 (Vercel static hosting; the admin Render service never
  serves public traffic) and DEC-046 (GoatCounter, cookieless, no stored
  IPs). ADR-0038/R6 is satisfied by construction (clue-satisfaction solved
  check), not weakened; CON-021 amended the same day to admit exactly the
  public player described here.

## Rules

```yaml
- id: ADR-0041/R1
  statement: >-
    A puzzle's public key is the first 10 lowercase hexadecimal characters of
    SHA-256 over the UTF-8 bytes of "{width}x{height}:" followed by the
    solution grid's cells row-major, '1' for filled and '0' for empty.
    Exactly one implementation computes it, and every public URL, bundle
    filename and index entry uses that key. Any change to the recipe — the
    prefix, the separator, the cell encoding, the algorithm, the truncation
    length or the case — is a breaking change to every printed book and
    requires a new ADR.
  scope: {code: ["src/nonogram/admin/**", "player/**", "tests/**"]}
  check: {kind: test, ref: "tests/test_player_bundle.py::test_bundle_tree_and_clues_match_the_encoder"}   # FR-045 AC-380 (planned, CARD-282); the key recipe itself also needs its own fixture cross-check in that suite
  severity: mandatory
- id: ADR-0041/R2
  statement: >-
    No public asset — nothing in player/, nothing in the exported bundle,
    nothing the assembled site serves — carries a solution grid or data from
    which any solution cell is recoverable, for any puzzle, on any export
    path. This restates ADR-0038/R6's clause for the public surface; the
    solved state is detected from clue satisfaction alone.
    EXEMPT, by owner decision 2026-10-28, and exempt by SCOPE rather than by
    safety: a book's own owner-authored display title, served verbatim on
    /b/<slug>, and carried in the bundle's own book/<slug>.json that the
    served file is built from — which it always has been, since
    player_bundle.BOOK_FILE_FIELDS is ("puzzle_keys", "slug", "title").
    AMENDED 2026-10-28 (b): the first wording said "and nowhere else", which
    was false of the bundle on the day it was written. Naming only the served
    file would have left FR-045's bundle sentence reading false for a field
    that predates this decision entirely. It is the third such exemption beside the
    clues and the answer key, and like them it is a named channel with a
    DECLARED residual rather than a bounded one — 120 code points at
    log2(1112064) bits each, 2410.18 bits, 24.1x this surface's 100-bit
    ceiling and 2.68x the 900 cells of the largest publishable grid. So the
    honest statement of what this exemption admits is: an owner who writes
    the base-64 of a solution into a book's title publishes it, measured at
    100 of 100 cells recovered, and no reachable character cap is a bound
    (one base-64 character already carries six bits). The exemption is
    bounded in WHERE it applies, not in WHAT it can carry. A puzzle's own
    title — the picture name — stays forbidden outright and is not covered
    here.
  scope: {code: ["player/**", "src/nonogram/admin/**", "tests/**"]}
  check: {kind: test, ref: "tests/test_player_bundle.py::test_bundle_is_clean_of_answers"}   # FR-045 AC-381/EC-048 (planned, CARD-282); the served tree's half is tests/test_public_player.py::test_served_tree_is_clean_of_answers (CARD-283). The 2026-10-28 exemption's OWN control is NOT named here on purpose: CARD-284 writes test_the_book_title_exemption_is_scoped_and_its_cost_is_measured and owes the flip at its merge. Naming it now would read as mechanically checked while it exists only on a branch.
  severity: mandatory
- id: ADR-0041/R3
  statement: >-
    The public player is static files only: plain hand-written JavaScript and
    CSS in the top-level player/ directory, no framework, no build toolchain,
    no npm, nothing added to the Python package. The board state module is
    reused from the admin player by byte-identical build-time copy of
    src/nonogram/admin/static/solver_state.js, never by editing it and never
    by a fork. ADR-0038/R1's "served by the admin panel" clause stays scoped
    to the admin player; this rule owns the public player's serving.
  scope: {code: ["player/**"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0041/R4
  statement: >-
    The public player keeps play state in the visitor's browser localStorage
    only. For every interaction sequence the page issues zero write requests;
    there are no accounts and no server-side state of any kind.
  scope: {code: ["player/**", "tests/**"]}
  check: {kind: test, ref: "tests/test_public_player.py::test_no_write_request_for_any_interaction"}   # FR-045 AC-385/EC-050 (planned, CARD-283)
  severity: mandatory
- id: ADR-0041/R5
  statement: >-
    The player bundle is exported by an explicit admin-panel action, is
    read-only against the database (no INSERT/UPDATE/DELETE on any export
    path), takes its clues from compute_clues of the stored grid (the one
    encoder), and is deterministic: the same input produces byte-identical
    files.
  scope: {code: ["src/nonogram/admin/**", "tests/**"]}
  check: {kind: test, ref: "tests/test_player_bundle.py::test_export_is_readonly_and_deterministic"}   # FR-045 AC-382/EC-049 (planned, CARD-282)
  severity: mandatory
- id: ADR-0041/R6
  statement: >-
    Nothing we ship stores, reads or transmits a visitor's IP address or any
    per-visitor identifier. Usage counting happens only through the
    cookieless hosted service this ADR names — GoatCounter — included as one
    script tag on the player pages, which must render and play correctly
    with it blocked or absent. Swapping the service is an ADR revision, not
    a code-only change.
  scope: {code: ["player/**", "scripts/**", "tests/**"]}
  check: {kind: test, ref: "tests/test_public_player_pages.py::test_no_homegrown_tracking"}   # FR-045 AC-392 (planned, CARD-285); the blocked-analytics half is test_pages_work_with_analytics_blocked
  severity: mandatory
- id: ADR-0041/R7
  statement: >-
    A finalized book's public slug is the first 10 lowercase hexadecimal
    characters of SHA-256 over the UTF-8 bytes of "book:" followed by the
    book's puzzle keys in book order, concatenated with no separator (each
    key is exactly 10 characters by R1). The book's title is NOT an input:
    the slug is printed in a QR code that cannot be re-pointed, so an
    editorial title change must not move it. Exactly one implementation
    computes it. Any change to the prefix, the ordering, the absence of a
    separator, the algorithm, the truncation length or the case is a
    breaking change to every printed book and requires a new ADR.
  scope: {code: ["src/nonogram/admin/**", "player/**", "tests/**"]}
  check: {kind: test, ref: "tests/test_player_bundle.py::test_bundle_tree_and_clues_match_the_encoder"}   # FR-045 AC-380 (CARD-282); the title-independence half is test_the_slug_does_not_move_when_the_title_is_edited
  severity: mandatory
```
