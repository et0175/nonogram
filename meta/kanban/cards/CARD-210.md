# CARD-210: Each puzzle's QR code becomes a real, scannable link to that puzzle's online solver

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- RESTATED in review cycles 2026-11-06 at queueing (the board counts Nc since ADR-0055). The day figure is the old estimate; the encoder choice below can move it. -->
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/210-real-puzzle-qr
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 ("I think about delivering some extra benefits with the book: 1. Qr code with each puzzle in the book to the puzzle online solver for this specific puzzle (this solver doesn't exist so far, so we need to think about its development)"); the slot it fills is CARD-204's placeholder glyph
**Idea:** —
**Wave:** —
**Depends on:** CARD-204, CARD-322
<!-- CARD-322 added 2026-11-06: after it the printed QR lives only in the vector writers (CARD-322 FLIPS the interior to operators; the deletion of the bitmap QR drawers moved to CARD-387 on 2026-11-07, so they may still exist in book_pdf_generator.py: this card changes the VECTOR writer's link and does not touch the dead bitmap drawers). The two must not run concurrently. -->
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/export/layout.py, pyproject.toml, tests/test_book_pdf.py, tests/test_book_qr.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** — (unblocked 2026-10-30; both preconditions now exist, see Worktree notes)

## [PREMISES RE-READ 2026-11-06] — what changed since this card was written, and the one open decision

Written by the orchestrator when the owner asked for this card to be queued ("doesn't matter what's first: 210 or dividers"). **The two blockers named under "Why this card exists and is blocked" are RESOLVED:** (1) a public solver to point at EXISTS: the public player is deployed at `https://nonogram.adverax.io` (docs/deploy/player.md), with `/play/<key>`, `/b/<slug>` and `/library`; (2) the URL namespace is DECIDED by ADR-0041/R1: the key is the grid's SHA-256 truncated to 10 hex characters, one-way, stable across re-seeds. Each book also stores its own **player domain** (CARD-332), so the printed link for a puzzle is `{the book's stored domain}/play/{key}` and a book with no stored domain must print no QR rather than one built from a base nobody chose (the rule docs/deploy/player.md records). **What is true today (measured by the CARD-322 re-cut author on main, 2026-11-06):** the QR printed on every puzzle page is NOT a link. The constant `QR_LINK_TEMPLATE = "nonogram.example/p/{number:03d}"` in `book_pdf_generator.py` is a placeholder (its own comment says "until the online solver" exists), so a book exported today cannot be scanned to reach the site, whatever the page medium. **The one decision that is still open and is the OWNER's:** the encoder (item 2 of "What it will do"): ADR-0006/R1 closes the runtime dependency set to stdlib + Pillow + NumPy, so a QR encoder is (A) a new pure-Python runtime dependency with a revision of that ADR, (B) a single vendored third-party file (with its licence) that adds code but no `pyproject.toml` dependency, or (C) about 400 lines of in-repo Reed-Solomon, mask selection and version fitting, correctness-critical (a printed code that looks right and does not scan). The AC below also wants a DECODED round trip, which needs a QR decoder on the test side (a dev-only dependency or a vendored test helper): the same decision. The card must carry the owner's choice, recorded as an ADR delta BEFORE implementation. The author of this card stops and asks if it is not recorded.

**[OWNER RULING 2026-11-06, after the above: "option 2, vendor one file"].** The QR ENCODER is a SINGLE vendored third-party source file, with its licence, in the repository: no new entry in `pyproject.toml`, ADR-0006/R1's dependency baseline (stdlib + Pillow + NumPy) is not widened. Consequences for the author: (1) choose the file and say why before writing code: the candidate the orchestrator had in mind is Project Nayuki's single-file Python QR Code generator (MIT licensed, no dependencies), but this is a recollection, NOT verified: read its actual licence text, version and size, and confirm its terms permit vendoring with attribution; if no single file with a permissive licence fits, STOP and report; (2) the vendored file carries its provenance in the repository: upstream URL, version or commit, the licence text beside it, and the sha256 of the vendored bytes, with a test that holds the bytes to that sha256 so an edit to vendored code is a deliberate act; (3) it lives where the layering guard and the closed-dependency check (tests/test_cli.py's import walk) accept it, and the card records the ADR delta BEFORE implementation: ADR-0006 gains a rule that third-party code may be vendored as a single provenance-stamped file under stated conditions (no network, no transitive dependency, a pinned hash), and what that does to R1's wording; (4) our wrapper stays thin and ours: the URL comes from the book's stored player domain and the puzzle key; the vendored file only turns bytes into a module matrix; the matrix is drawn into CARD-204's existing 2x2 cm slot by our code in both writers that remain after CARD-322 (the vector writers); (5) the DECODED round trip the AC asks for needs a QR decoder on the test side: survey the options (a pure-Python decoder vendored as a TEST helper under the same provenance rules, an installed decoder available to the dev extra, or a check against the encoder's published test vectors plus a render-and-sample reader of our own that is independent of the encoder code) and STOP and ask the owner if the only way is a new third-party dev dependency; (6) QR version and the longest URL it carries at a module size a phone camera resolves in 2x2 cm are stated in the card, as the original item 3 requires.

**[OWNER LINK DESIGN 2026-11-07, on the owner's proposal; recorded, not yet a requirement beyond item "the printed link"].** The printed QR link is `https://<book.player_domain>/<id>` (the owner's example host: `nonogram.adverax.io`), where `<id>` is the puzzle's public key (ADR-0041/R1: SHA-256 of the grid, 10 hex characters), NOT the puzzle's number in the book. Consequences this card must honour: (1) the printed link is the STABLE part and never encodes a book name, a path that could be reorganised, or a counter; the same puzzle has the same link in every book; (2) the player's route for that key must answer at the root path `/<id>` (the public player is deployed under a different path today: the author finds the current route and states the gap; adding the root route is the player's side, name the card if it is not this one); (3) the owner plans a separate LIBRARY page (`/library`, book pages such as `/Christmas`, then puzzle tiles) as a browsing layer over the same keys; it is NOT part of this card, but this card must not make it harder: no printed link may depend on it. Open points for that future card, recorded here so they are not lost: a book name must not collide with a 10-hex key (reserve the shape, or put books under `/b/<name>`); tiles must show no solution (ADR-0041/R2); and listing every puzzle lets a reader play a book without buying it, so the library should list only what the owner chooses (unlisted puzzles stay reachable by QR). The expected value in the printed-link test stays a literal string written in the test (CARD-322's AC-18 note), now of the shape `<player_domain>/<key>`.

## What to implement

**Why this card exists and is blocked.** CARD-204 reserves a 2×2 cm QR slot on
every book puzzle page and fills it with a deliberately-fake, non-scanning glyph
— the owner's own "draft the QR icon's layout slot now with a placeholder/TODO
link" decision of 2026-10-08. This card is the swap-in that CARD-204's
"What to implement" step 2 names as a follow-up. Two things it needs do not
exist yet, and neither can be decided in a worktree:

1. **A public solver to point at.** Today interactive play exists **only** as the
   admin panel's player behind the CON-015/CON-016 door (CON-021, ADR-0038/R6).
   The owner's own plan is explicit: "we'll need to set up an infrastructure for
   prod. But I propose to move it to the next phase — make for now solver under
   the admin panel". A QR printed into a book is permanent; pointing it at a
   URL that does not resolve, or at an admin URL nobody but the owner can
   reach, is worse than printing no QR.
2. **A URL namespace per puzzle** that survives the database being re-seeded —
   a printed code cannot be re-pointed. This is a design decision (opaque
   stable puzzle slug vs. row id vs. a content hash of the grid), not an
   implementation detail.

**What it will do once unblocked.**

1. Encode a real QR (the public per-puzzle URL) and draw it into CARD-204's
   existing slot — same position, same 2×2 cm extent, no new geometry
   (ADR-0036/R2: positions come from `export/layout.py`, which CARD-204 already
   taught to reserve the slot).
2. **The encoder is an ADR-0006 decision.** The runtime dependency set is
   exactly stdlib + Pillow + NumPy; a QR encoder is either a new dependency
   (revising ADR-0006/R1) or ~400 lines of in-repo Reed–Solomon, mask selection
   and version fitting — correctness-critical code whose failure mode is a
   printed code that looks right and does not scan. The card must carry the
   owner's choice, recorded as an ADR delta **before** implementation.
3. Quiet zone and module size are print constraints, not cosmetics: a 2×2 cm
   code must hold the URL at a module size a phone camera resolves. The card
   must state the chosen QR version and the longest URL it can carry, and the
   AC below must verify a **decoded** round trip, not merely that pixels were
   drawn.

## Acceptance criteria

(Written now so the card is ready to run the moment it is unblocked; all of them
presume the two blockers are resolved and the chosen URL scheme is recorded.)

- **AC-1** (happy): *Given* a puzzle printed as puzzle 37, *when* its book page
  is rendered, *then* the QR slot holds a code that decodes to exactly that
  puzzle's public solver URL. (test: `TestBookQr_DecodesToThePuzzlesOwnUrl`)
- **AC-2** (happy, every page): *Given* any book, *when* its interior is
  exported, *then* every puzzle page's QR decodes to the URL of the puzzle (or,
  on a two-up page, of each slot's own puzzle) printed on it. (test:
  `PropertyTest_BookQr_EveryPageCodesItsOwnPuzzle`)
- **AC-3** (happy, geometry): *Given* any book trim in CON-018's profile set,
  *when* a page is drawn, *then* the code occupies CARD-204's 2×2 cm slot
  exactly, with its full quiet zone inside that slot and no overlap with the
  grid, the band, the rule or the folio. (test: `TestBookQr_FitsTheReservedSlot`)
- **AC-4** (edge, print resolution): *Given* the book's export DPI, *when* a
  code is drawn, *then* every QR module is a whole number of device pixels (no
  resampling blur), and the module size is at or above the minimum the card
  records. (test: `TestBookQr_ModulesAreWholePixels`)
- **AC-5** (guard, dependency): *Given* the installed environment, *when* the
  dependency baseline test runs, *then* it reflects the ADR-0006 decision this
  card recorded — and fails if a dependency was added without it. (test:
  `TestDependencyBaseline_IsExactlyPillowAndNumpy`, updated only alongside the
  ADR delta)
- **AC-6** (guard, no solution leak): *Given* a printed QR, *when* it is
  decoded, *then* it carries a URL and nothing else — no grid, no solution, no
  admin path (ADR-0038/R6, CON-021). (test: `TestBookQr_CarriesOnlyAPublicUrl`)

## Guardrails

- G-1: The QR must never point at an admin-panel URL — CON-021/ADR-0038/R6 keep
  interactive play behind the admin door, and a printed admin link would publish
  it (test: `TestBookQr_CarriesOnlyAPublicUrl`).
- G-2: No new runtime dependency without an ADR-0006 revision recorded first
  (ADR-0006/R1; test: `TestDependencyBaseline_IsExactlyPillowAndNumpy`).
- G-3: The slot's geometry is CARD-204's — this card fills it, it does not move
  or resize it, and it computes no page geometry of its own (ADR-0036/R2).
- G-4: CLI and web-UI exports stay byte-identical (CON-019) — no QR on a
  single-puzzle export unless a separate card asks for one.
- G-5: Out of scope — the second QR from the same doc item ("generate your own
  puzzle from the picture") and the public solver itself; both are backlog
  entries pending the owner's "V1: only solver for book 1" decision.

## System contract

- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy; no
  third-party package joins without revising the ADR (check:
  `TestDependencyBaseline_IsExactlyPillowAndNumpy`)
- CON-021 — interactive play exists only as the admin panel's player, behind the
  admin door; no public or hosted page offers it (check: review-lens)
- ADR-0038/R6 — only the admin player may ship a solution to a browser; any
  public phase reopens the ADR (check: review-lens)
- CON-019 — book geometry never changes CLI/web exports (check:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)
- ADR-0036/R2 — only COMP-007's layout functions place things (check:
  review-lens)

## Architecture context

- **FR:** FR-032 (puzzle-page placement, as amended by CARD-204), FR-044 (the
  player — the thing the QR would link to, today admin-only).
- **ADR:** ADR-0006 (dependency baseline — **this card needs a delta**),
  ADR-0036/R2, ADR-0038/R6.
- **CON:** CON-015, CON-016, CON-019, CON-021.
- **Components:** COMP-009 (`book_pdf_generator.py`), COMP-007
  (`export/layout.py`, only if the slot needs anything CARD-204 did not add).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

**[Unblocked] 2026-10-30.** The two things this card waited on both exist now, and the
evidence is in the repository rather than in a claim:

1. **A public solver that is actually hosted.** COMP-011 is deployed — project
   `nonogram-studio` on Vercel, serving the owner's custom domain
   `https://nonogram.adverax.io`. Verified against production the same day: `/library`,
   `/play/<key>`, `/b/<slug>` and `puzzle/<key>.json` all 200; the served puzzle file
   carries exactly `clues`, `height`, `key`, `tier`, `width` (no solution, no puzzle
   title); the served `solver_state.js` is SHA-256 identical to the panel's. Recorded in
   `docs/deploy/player.md` ("What production is").
2. **A URL namespace stable enough to print.** ADR-0041/R1 (puzzle key) and R7 (book
   slug) are content hashes of the grid and of the ordered keys — recomputable from what
   a printed book preserves, and deliberately independent of any title. The base is
   recorded in that page's `qr-url-shapes` block, which
   `tests/test_public_player_pages.py::test_the_qr_url_shapes_here_are_the_shipped_routes`
   holds to `vercel.json`'s own rewrite sources.

**What this card still has to decide, and must not assume:** *where the base comes from
at print time.* Today it is a line in `docs/deploy/player.md`, which is repo-managed and
test-pinned. CARD-332 adds a domain field to book print setup, which would be a second
source. Whatever this card prints has to come from one of them by decision, and the
decision belongs with CARD-332 — see its "The one decision this card must not duck".
The owner's stated intent (2026-10-30) is the print-setup field, with the stored value
being what a book records as printed.

**Still true from 2026-10-13, and worth re-reading before starting:** a printed QR code
cannot be re-pointed. The slug moves if a book's puzzle membership or order changes
(INV-012 returns such a book to draft), so the set must be frozen before a run is
printed, and this card does not change that.

**Where the placeholder is now:** `book_pdf_generator.py:882` `QR_LINK_TEMPLATE =
"nonogram.example/p/{number:03d}"`, read only by `qr_link` (`:2125`), drawn as a
checkerboard by `_draw_qr_placeholder` (`:2085`). The slot is CARD-204's 2x2 cm reserve;
the caption line is `QR_CAPTION_TEXT = "Solve it online"` (`:864`). Note the template is
per-puzzle-NUMBER and the real link is per-KEY — a book's puzzle number is not a public
identifier, so this is a change of what the footer identifies, not just of the string.

**Dependency note:** `pyproject.toml` is in `Touches:` because a QR encoder is a new
runtime dependency, and ADR-0006/R1 closes that baseline at stdlib + Pillow + NumPy.
Adding `qrcode`/`segno` is an ADR revisit, not a `pyproject.toml` edit — or the card
draws the modules itself from the spec. That question is open and is the reason this
card is `architectural`.

## Amendment 2026-10-14 — the owner's "Puzzle page layout" artifact

The QR's **place** changes before its content does:

- **CARD-223** moves the QR out of the gutter-side strip into the footer's **outer** bottom
  corner, and adds the caption `Solve it online` plus a **typed link** beside it. So when this
  card unblocks, it changes the glyph *and* the link text in their new home — not CARD-204's
  gutter slot, which will no longer exist.
- The typed link is a placeholder from one named constant until this card
  (`nonogram.example/p/052` in the artifact's mockups, which the artifact itself labels a
  stand-in "until the online solver has a real address"). This card replaces that constant and
  the placeholder glyph together, so a reader with a camera and a reader without one are never
  pointed at different things.
- **Depends on:** CARD-223, in addition to the two infrastructure blockers (a hosted public
  solver and a stable per-puzzle URL namespace) the owner's 2026-10-13 decision set.
- Still blocked. The owner's decision stands: keep the placeholder until the infrastructure
  exists.
