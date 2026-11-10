# CARD-418: The book's QR landing page is redesigned: jump to a number, continue, three level sections of picture squares

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 2c (1d)
<!-- Basis: one page source (player/book.html), its renderer (player/pages.js, the `numbered` branch), its styles (player/player.css) and their tests; no server, no new served field. The cost is the local-progress reader (replaying a save against its own clues) and the tests that pin "no answer ever comes from the site". -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner request 2026-11-10 (project thread "Design the book QR landing page"): owner chose mockup A, then "remove Book 1 from the title", "make squares more interesting", "I like pictures for the solved ones", "make cards for new landing page design and a how to solve page".
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-284, CARD-339, CARD-419
<!-- CARD-284 (done) built /b/<slug>; CARD-339 (done) gave the public player its "?" mark. CARD-419 is the How to solve page this page links to: the link can land first and point at it once it exists, or this card waits for it. -->
**Touches:** player/book.html, player/pages.js, player/player.css, player/assemble.py, tests/test_public_player_pages.py, tests/test_book_landing_address.py, meta/architecture/requirements.yml, docs/how-it-works/01-domain/puzzle-creation/11-the-public-player.md
<!-- A starting point, not the boundary: grep the WHOLE tests tree for `data-pages-`, `pages-list`, `tile-number`, `numbered` and `readTitle` before starting. -->
**Review score:** — (no review cycle; merged on the owner's request)
**Started:** 2026-11-10T10:30Z
**Closed:** 2026-11-10T11:41Z
**Actual:** about 30 min of one owner session, after CARD-419
**Merge commit:** 871ec258
**Blocked by:** —

## Why this card exists

`/b/<slug>` is the page a book's QR code opens, so it is the reader's first contact with the product, seconds after scanning and on a phone. Today (`player/book.html`, rendered by `pages.js`) it is the book's title, "160 puzzles", one hint line and 160 large tiles, two to a row. Each tile shows only a number, a size and a tier. A reader holding the book on page 120 has to scroll past about 60 rows to find it. The page does not name the series or the authors, and it does not show what the reader has already played, although the player keeps that on the device.

The owner reviewed two mockups and chose **A**. The design of record is the canvas "Book QR landing page" (https://claude.ai/artifact/7nXaVdkyQ8raJNZ2bPV1fk), board "A · Book landing (chosen)". A screenshot of today's page is in the project files at `landing/current-390.png`.

## What to implement

1. **Header.** Above the title, a small line naming the series ("Anna & Olga's Ultimate Puzzle Selection"; no "Book 1"). Under it, the book title as the h1 (still the served display title, written with textContent, as now), then "by <authors> · N puzzles to play on your phone".
   * The series and authors are owner-authored editorial text about the BOOK, the same class as the display title already served under `EXEMPT_LISTING_FIELDS` (owner decision 2026-10-28). Serve them the same way: two optional fields in `book/<slug>.json`, each with the same exemption, the same whitespace normalisation and length cap as `readTitle`. A book without them shows no series line and no "by" clause. **Never a puzzle title** (EC-048); the slug stays the hash of the keys alone (ADR-0041/R7), so these fields must not enter it.
2. **"Which puzzle are you on?"** A labelled numeric input and a Play button. A number in range opens `/play/<key>` for that printed number; the hint line under it names the level ("Opens puzzle 47 (Medium).") or says the range ("This book has puzzles 1 to 160."). The number is the PRINT number, the same mapping the tiles use (tile i is the puzzle the interior prints as number i, CARD-389 AC-2).
3. **"Continue where you stopped."** A card shown only when this device holds a save for one of this book's puzzles that is started and not solved: the most recently changed one, "Puzzle 12 · 15×13 · Easy". Hidden otherwise. If the save has no timestamp to decide "most recent", the card says so in the worktree notes and uses the highest started print number instead; do not add a timestamp to the save format in this card without asking.
4. **Three level sections.** Easy, Medium and Hard each get a header button ("Easy · puzzles 1–68", "3 of 68 solved", a level dot in the tier colour, +/−) that opens and closes a grid of squares. Easy is open by default; the others start closed. A level with no puzzles is not shown. 6 squares per row at 390 px, more on wider screens; each square is a link to `/play/<key>`, at least 44 px.
5. **The squares.**
   * **Not started:** a blank mini grid (faint 5×5 lines) with the print number in the middle.
   * **Started:** the same, a 2 px accent edge, and a few of the reader's own black cells in light accent behind the number.
   * **Solved:** the picture the reader uncovered, drawn small from THEIR OWN saved board (black cells only), with the print number in a small corner badge.
   * Each square's accessible name says the number and the state ("Puzzle 12, started").
6. **Reading progress, on the device only.** The player's save is `localStorage["nonogram-player:" + <id>]` (`solver_state.js` `saveKey`, `serializeState`). A public save carries the puzzle's own `rows` and `columns` clues and its strokes, so this page can replay the strokes into a board and decide "solved" with the player's own clue check (`isClueSolved` or whatever `solver_state.js` exports for "solved without the solution", ADR-0041/R2), with no fetch. Import from the copy of `solver_state.js` the site already serves; do not reimplement the replay. Verify that a public save's `id` is the puzzle key that the book file lists, and state it.
   * Every read is wrapped so a blocked or empty storage just shows every square as not started.
   * **The page never writes storage**, as now.
7. **Footer.** Two links: "New to nonograms? How to solve one" to CARD-419's page, and "More puzzles in the library".
8. **Unknown slug and empty book** keep today's friendly panels (AC-388 and CARD-282's F-8).

## Acceptance criteria

(The ids below are local labels; the registry ids are assigned at dispatch.)

- **AC-A** (happy, jump): *Given* the Book 1 file, *when* the reader enters 47 and presses Play, *then* the page goes to `/play/<key of print number 47>`; 0, 161 and empty do not navigate and show the range line. (control: an off-by-one mapping to stored order reds it on a mixed-stored book, CARD-389 AC-2's fixture.)
- **AC-B** (happy, sections): the three sections show the right print ranges and counts for a level-grouped book, Easy opens by default, and a book with no Hard puzzles shows no Hard section.
- **AC-C** (progress from the device): with saves planted in localStorage for print numbers 1 (solved), 2 (started) and none else, square 1 renders the planted board's black cells, square 2 is "started", the rest are "not started", the Easy header reads "1 of 68 solved", and the Continue card names puzzle 2. With storage throwing on access, the page renders with every square "not started" and no Continue card.
- **AC-D** (guard, no answer from the site): no served file gains a solution grid, a picture, or a puzzle title; the solved picture comes only from the device's own save. The existing `test_bundle_is_clean_of_answers` family stays green and is extended to `book/<slug>.json`'s new fields.
- **AC-E** (guard, the code on paper still works): the slug of an existing book is unchanged (CARD-389 AC-3's literal), so a printed QR still resolves.
- **AC-F** (layout): at 390 px wide no horizontal scroll, squares at least 44 px, focus visible on every control. (check: a Playwright screenshot at 390 and 1280 for the owner's eye.)

## Guardrails

- **G-1** No new runtime dependency, no network call beyond today's single `book/<slug>.json` fetch.
- **G-2** Nothing from a save leaves the device; the page reads storage and never writes it.
- **G-3** The player itself (`/play/<key>`, the admin's `puzzle_solve.html` shared UI) is not changed by this card. If "solved" turns out to need a field in the save, stop and ask: that is the player thread's change, not this card's.
- **G-4** Change existing tests where they pin today's tile markup; add one control per AC that can fail; report the net test count.

## Architecture context

- **FR:** FR-045 (the public player and its book landing). **Components:** COMP-011 (the public player site), `player/assemble.py` (what is served and the exemption for book fields).
- **Decisions this follows:** ADR-0041 (slug, landing, R2 solved-by-clues, R7 slug from keys only), EC-048 (no puzzle title anywhere served), CARD-284 (the landing), CARD-389 (print numbers).

## Worktree notes

- Built in the cloud thread "Design the book QR landing page" on branch book-landing-how-to-solve (commit 614c7b5b), merged to main as 871ec258 on the owner's "merge please".
- The book file gained `series` and `authors` beside `title` (player_bundle.BOOK_FILE_FIELDS; assemble.SERVED_BOOK_SCHEMA); all three are EXEMPT_LISTING_FIELDS, settled by the same `_book_title` whitespace collapse, and `book_exempt_residual_bits()` counts them.
- Progress is read only from this device: pages.js imports /solver_state.js, replays each `nonogram-player:<key>` save against the served clues, and calls a puzzle solved only when isClueSolved says so; the solved picture is the reader's own board, never site data.
- Sections: all open when the book has 24 or fewer puzzles (OPEN_ALL_UP_TO), otherwise the first Easy section plus the Continue puzzle's section.
- Tests: tests/test_book_landing_page.py (6, browser) plus updated fixtures in test_public_player_pages, test_public_player, test_player_bundle, test_book_landing_address.
- Left open (not done here): FR-045 AC registry rows in meta/architecture/requirements.yml and their trace rows; an ADR-0041/R2 amendment naming series and authors as exempt like the title; the how-it-works page for the public player.
