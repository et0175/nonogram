# CARD-425: The “book not found” page should not offer “Browse the library”

**Status:** ready
**Priority:** P3
**Category:** ux-polish
**Estimate:** 1c (0.25d)
<!-- One element and one test claim. The cost is deciding what, if anything, replaces it — see the decision. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner play-test findings, Google Doc "Гра - тест", 2026-11-11, item 1. Reproduced on production (https://nonogram.adverax.io) before drafting; the measurements below are mine, the finding is the owner's.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/book.html, tests/test_public_player_pages.py
<!-- Derived 2026-11-11 by reading where the panel lives: the not-found block in `player/book.html`, and the one test that asserts its link (`test_unknown_slug_lands_softly`, which both asserts `a.pages-library-link` inside `[data-pages-notfound]` AND follows it). Nothing under `src/`: this page is the assembler's, not the admin's. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Measured on production at `/b/deadbeef99` (an unknown slug):

```
Your book
We could not find this book
This link does not match a book on the site. The code may have been mistyped,
or the book may not be published online yet.
[Browse the library]        -> /library
New to nonograms? How to solve one -> /how-to-solve
```

The owner's finding is the first control: a reader who scanned a QR code from **their own printed book** and landed here does not want someone else's library — they want their book, and the page cannot give it to them. Offering the library turns a dead end into a detour, and on a page whose whole job is to say "this is not it", a prominent `btn` is the most clickable thing on the screen.

The second link (`/how-to-solve`) was not objected to and stays unless the owner says otherwise: it is an offer of help, not a redirection.

## Decision owed before implementation (owner)

**D1:** does the panel keep **nothing** but the explanation; keep the how-to-solve link only; or say something actionable instead (for example "check the code on the back of your book")? **Default if unanswered:** remove the library button, keep the how-to-solve line, change no wording — the smallest change that satisfies the finding.

## What to implement

1. Remove the `<a class="btn pages-library-link" href="/library">Browse the library</a>` paragraph from the not-found block in `player/book.html`. The same class is used elsewhere on the listing pages; remove the element, not the class.
2. `tests/test_public_player_pages.py::test_unknown_slug_lands_softly` asserts that link exists **and** follows it to `/library`. That claim is retired by this card: replace it in the same place with the new claim (the panel is visible, explains itself, and offers no library link), per the owner's test budget — change the existing test, do not add one.

## Acceptance criteria

- **AC-1** *Given* `/b/<unknown>` and `/b/not-a-slug`, *then* `[data-pages-notfound]` is visible and contains no `a.pages-library-link`; *and* the page still explains itself in words. (test: `tests/test_public_player_pages.py::test_unknown_slug_lands_softly`, changed; plant: re-add the anchor and the test reds.)
- **AC-2** (nothing else loses its library link): the `/library` link on the book landing proper and on the listing pages is unchanged. (test: the existing landing cells.)

**Net test count: 0 added.**

## Worktree notes

—
