# CARD-421: The Christmas book's landing gets its decorations: a pine garland and snow on the panels

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: two drawings made in pages.js as inline SVG (no served file), their placement in player.css, and the existing Christmas cell extended. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner request 2026-11-11 (project thread "Add a Christmas theme to the book page"): "then please make the pictures for the decor" — the co-author's mockup's garland and snow caps, after CARD-420's colours.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-420
**Touches:** player/pages.js, player/player.css, tests/test_book_landing_page.py
**Review score:** — (no review cycle; merged on the gates)
**Started:** 2026-11-11T08:05Z
**Closed:** 2026-11-11T08:34Z
**Actual:** one owner session (wall clock excluded, owner ruling)
**Merge commit:** 6f06f8a3
**Blocked by:** —

## Why this card exists

CARD-420 gave the first book's landing its Christmas colours; the co-author's mockup also has a pine garland with baubles across the top and snow lying on the panels. The owner asked me to draw them rather than wait for artwork.

## What to implement

1. **The drawings.** `pages.js` draws a garland tile (a seeded spray of pine needles along one swag, red berries, one red and two gold baubles) and a snow drift (a lumpy edge with drips), as inline SVG the way the squares' pictures are drawn. No file is served: an SVG file's namespace and attributes read as foreign targets to the site's self-containment scan, which stays as it is. Every colour is a `player.css` class painted from the theme's tokens.
2. **The placement.** On a book whose theme is christmas only: the garland repeats across the top of the page (72 px tall), and snow sits on the top edge of the number box, the Continue card and each section head. Both are `aria-hidden` and `pointer-events: none`, so they cover no control. The play page is not decorated.

## Acceptance criteria

- **AC-1** *Given* a christmas book's landing, *then* there is one garland and every panel carries snow, all `aria-hidden` and not hit-testable; *given* a default book or a puzzle's play page, *then* there are none. (test: `tests/test_book_landing_page.py::test_a_christmas_book_dresses_its_landing_and_the_puzzles_opened_from_it`)

## Worktree notes

- **[Implementation, 2026-11-11]** First drawn as two `player/decor-*.svg` files: the site's self-containment scan (`tests/test_public_player_pages.py`'s `scan_site`) read their `xmlns` as a foreign host and their `"/>` as rooted literals. Rather than loosen that guard, the drawings moved into `pages.js` as HTML-parsed inline SVG with explicit closing tags (no `"/>`), and their colours into `player.css` classes over the theme's tokens (no colour literal in a served script). The garland is 8 cloned 240x64 tiles, about 1000 needle lines each pair of layers; the snow is one path stretched to each panel. Plant: `decorate()` for every book -> the default book's arm red (`7 == 0`).
- **[Gate]** `make test-gate`: 5331 passed; 1 red, `test_book_pdf_memory`'s guard, red on main too (pre-existing).
