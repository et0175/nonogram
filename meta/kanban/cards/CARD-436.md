# CARD-436: A puzzle opened from a book offers the way back to it — today the play page has no links at all

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.25d)
<!-- Basis: the slug and the book's title are already in hand on the page (CARD-420 fetches /book/<slug>.json for the theme), so the work is markup, a string and one test. The cost is deciding where it is shown, and keeping a public-only addition from drifting the shared player. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner's play-test doc "Гра - тест", 2026-11-12, item 5: *"When we have 'solved' puzzle - have get back to book"*.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/assemble.py, tests/test_public_player.py
<!-- Derived 2026-11-12. The public play page is RENDERED by player/assemble.py (puzzle_solve.html plus the wrapper script that reads ?book= and fetches the book file). The owning test module must be resolved before the brief is acted on: tests/test_public_player.py, tests/test_public_player_pages.py and tests/test_player_bundle.py all drive the public play page and the first is a guess, not a derivation. Run scripts/impact_set.py --gate. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists — measured, not inferred

On production, 2026-11-12, `/play/bac44c19a9?book=0a958d036e`:

```
document.querySelectorAll('a').length   ->  0
```

**The play page contains no links whatsoever.** Not back to the book, not back to the library, not to How to solve. A reader who opens a puzzle from their book and finishes it has the browser's Back button and nothing else; a reader who arrived by QR code from a printed book has no Back entry at all.

The owner asked for this at the moment of solving. The measurement says the gap is wider than that, which is noted below as a question, not quietly built.

## What makes this cheap

CARD-420 already put the book's identity on the page: a puzzle opened from a book is `/play/<key>?book=<slug>`, and the page already fetches `/book/<slug>.json` beside the puzzle, "so it costs no extra round trip". That file carries the book's **display title** — the one editorial string the residual-bits exemption lets the public site serve (`player/assemble.py`'s module docstring, the `/b/<slug>` exemption). So the slug, the title and the fetch all exist. Nothing new is fetched and no new residual is served: the title is already on this page's network path.

## Why this one lives in the public tree

The standing rule is that the admin solver is the source and the public page is a build-time copy (CARD-386/399, owner 2026-11-07). This card is a **deliberate exception**: the admin player has no concept of a book, no `?book=` parameter and no `/b/<slug>` to return to. The link belongs to the public wrapper in `player/assemble.py`, beside the theme code that reads the same parameter.

State that in the implementation's comment. A future reader comparing the two trees must find the reason there, not conclude the copies have drifted.

## What to implement

1. When the play page was opened with a `?book=<slug>` that really holds this key — the same validity test CARD-420 already applies for the theme — the solved state offers a link back to `/b/<slug>`, naming the book by its display title.
2. No book, a malformed slug, or a book that does not hold this key: no link, exactly as today. A puzzle opened from the library is unchanged.
3. The link is a real `<a href>`, so it works without JavaScript having to navigate and a reader can open it in a new tab.

## The question to put to the owner before merging

Should the way back be there **the whole time**, not only once solved? The owner asked for it on solve, so that is what AC-1 requires and what this card builds. But the measurement above says an unsolved reader is equally stranded, and a book reader who wants the next puzzle has to solve this one first. Ask; do not widen the scope on your own reading. If the answer is yes, it is a one-line change to this card's own work and belongs here rather than in a second card.

## Acceptance criteria

- **AC-1** (the way back exists on solve): a public play page opened with a valid `?book=<slug>`, solved, shows a link whose `href` is `/b/<slug>` and whose text names the book's display title. (test: a changed cell in the module that owns the public play page's solved state — derive it; plant: drop the slug from the URL and the link must be absent.)
- **AC-2** (no book, no link): the same page opened without `?book=`, with a malformed slug, and with a valid slug for a book that does not hold this key, shows no link in all three cases. (test: the same cell.)
- **AC-3** (nothing else moved): the theme CARD-420 applies from the same parameter still applies, and the page still issues no extra request beyond the two it makes today. (test: the existing CARD-420 theme cell, unchanged; evidence: the request count.)

**Net test count: 0 added if the solved-state cell exists; otherwise 1, reported at the gate.** Resolve which before writing — the owner's budget of 2026-11-07 is to change existing cells, not add.

## Worktree notes
