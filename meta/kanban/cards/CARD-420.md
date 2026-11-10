# CARD-420: A book's Christmas theme dresses its landing page and the puzzles opened from it

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- Basis: no migration (every book already stores a theme, BOOK_THEMES); one new served book field through the bundle and the assembler with its residual declared; one token block, the landing's themed rules, the tiles' link, and the play page's loader. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/420-book-theme
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-420
**Source:** owner request 2026-11-10 (project thread "Add a Christmas theme to the book page"): asked whether a book and its puzzles can have their own style, "e.g. Christmas for the first book"; "not needed for the printed book"; the co-author's mockup (green panels with gold edges, red buttons, cream background); solved tiles "of course not coloured", "maybe something greenish"; then "ok, do it please".
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-418
**Touches:** src/nonogram/admin/player_bundle.py, player/assemble.py, src/nonogram/admin/static/tokens.css, player/player.css, player/pages.js, tests/test_player_bundle.py, tests/test_public_player_pages.py, tests/test_book_landing_page.py
**Review score:** —
**Started:** 2026-11-10T16:35Z
**Closed:** —
**Actual:** —
**Merge commit:** —
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
