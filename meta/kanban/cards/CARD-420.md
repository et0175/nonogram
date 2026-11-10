# CARD-420: A book's Christmas theme dresses its landing page and the puzzles opened from it

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- Basis: no migration (every book already stores a theme, BOOK_THEMES); one new served book field through the bundle and the assembler with its residual declared; one token block, the landing's themed rules, the tiles' link, and the play page's loader. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner request 2026-11-10 (project thread "Add a Christmas theme to the book page"): asked whether a book and its puzzles can have their own style, "e.g. Christmas for the first book"; "not needed for the printed book"; the co-author's mockup (green panels with gold edges, red buttons, cream background); solved tiles "of course not coloured", "maybe something greenish"; then "ok, do it please".
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-418
**Touches:** src/nonogram/admin/player_bundle.py, player/assemble.py, src/nonogram/admin/static/tokens.css, player/player.css, player/pages.js, tests/test_player_bundle.py, tests/test_public_player_pages.py, tests/test_book_landing_page.py
**Review score:** — (no review cycle; merged on the gates)
**Started:** 2026-11-10T16:35Z
**Closed:** 2026-11-10T17:15Z
**Actual:** one owner session (wall clock excluded, owner ruling)
**Merge commit:** ace5a29a
**Blocked by:** —

## Why this card exists

The first book is a Christmas book, and the owner wants its QR landing page, and the puzzles a reader opens from it, to look like one. Only the online pages change: the printed book is out of scope (owner, 2026-11-10).

## What to implement

1. **The served theme.** A book already stores a theme (`book_manager.BOOK_THEMES`: christmas, halloween, easter, valentine, generic), chosen on the General info step, so no migration is needed. The bundle's `book/<slug>.json` carries it as `theme`. The assembler serves it as `theme`, reduced to the themes the site draws (`SERVED_BOOK_THEMES = ("christmas",)`); any other value is served as `""`, the default look. Its residual (a closed choice: `log2(len(SERVED_BOOK_THEMES) + 1)` bits per book) is declared beside the tier label's.
2. **The Christmas look.** One token block in `tokens.css`, `:root[data-theme="christmas"]`, overrides the chrome tokens: a cream ground, pine-green surfaces and edges with gold, and red for the accent. The board's `--grid-*` tokens are not touched, so the cells stay black and white (colour-blind safety). The landing page adds a few themed rules in `player.css`: green section heads with a gold edge, a red Continue card, and solved tiles' pictures drawn in pine green instead of ink.
3. **The theme follows the book.** `pages.js` sets `data-theme` on the landing's root from the served field. Every link the landing makes to a puzzle (tiles, Continue, the number box) is `/play/<key>?book=<slug>`. The play page's loader reads `book`, fetches that book file, and applies its theme only when the book really holds this key. The same puzzle opened from the library, or with no or a wrong `book`, keeps the default look.

## Acceptance criteria

- **AC-1** *Given* a finalized book whose theme is christmas, *then* its `book/<slug>.json` in the bundle carries `"theme": "christmas"`, and the assembled site serves it; *given* any other theme, the served value is `""`. (test: `tests/test_player_bundle.py`, `tests/test_public_player_pages.py`)
- **AC-2** *Given* the served theme, *then* the assembler's listing partition accounts for `theme` and its residual is declared, and the capacity refusal still holds. (test: `tests/test_public_player_pages.py`)
- **AC-3** *Given* a christmas book's landing, *then* the page's root carries `data-theme="christmas"`, the themed tokens apply, a solved tile's picture is drawn in the theme's green, and every puzzle link carries `?book=<slug>`; a default book's landing has no `data-theme`. (test: `tests/test_book_landing_page.py`)
- **AC-4** *Given* `/play/<key>?book=<slug>` of a christmas book holding the key, *then* the play page's root carries `data-theme="christmas"` and the board's cells keep their black and white; *given* the same key with no `book`, a default book, or a book that does not hold the key, *then* there is no `data-theme`. (test: `tests/test_book_landing_page.py`)

## Worktree notes
- **[Implementation, 2026-11-10]** No migration: `books.theme` (required, `BOOK_THEMES`) already exists, so the owner sets the first book's theme to christmas on General info. The bundle exports it; the assembler serves `_book_theme` (only `SERVED_BOOK_THEMES` = christmas, else ""), declared as structure with `book_theme_residual_bits()` = 1.0 and printed by `--capacity`. `tokens.css` (both copies) gets `:root[data-theme="christmas"]` for chrome tokens only — no `--grid-*`, so the board stays ink on paper; accent stays green so the legend's "a green edge means started" stays true; contrast pairs computed (all >= 4.2:1 for decorative gold on pine, text >= 5.5:1). Links from a book are `/play/<key>?book=<slug>` written as template literals (the self-containment scan reads only literal targets). The play loader fetches the book file beside the puzzle and applies its theme only when the book holds the key.
- **[Tests]** Re-pointed: the bundle's criteria fields and source registry, the landing fixture (`BOOK_THEME = "generic"`), the empty-book payload, and five `/play/<key>` URL assertions (now `?book=<slug>`). New: `test_a_christmas_book_dresses_its_landing_and_the_puzzles_opened_from_it` (plant: the loader without the membership check -> `'christmas' is None` red). Gate (`make test-gate`): 8955 passed; 2 red — the shared-UI landing URL assertion (re-pointed, green after) and `test_book_pdf_memory`'s guard, which is red on main too (pre-existing). Also fixed on the way: `docs/deploy/player.md` backticked `--player-wave`, red on main for the assembler-flags test.
- **[Review]** No review cycle: merged on the gates (owner rule: merge on gates; renders sent to the owner before merge).
