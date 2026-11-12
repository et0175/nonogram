# CARD-437: The book page does not notice what you just played — coming back from a puzzle leaves every tile as it was

**Status:** in_progress
**Priority:** P1
**Category:** bug
**Estimate:** 1c (0.25d)
<!-- Basis: one listener and a re-run of a function the page already has. The cost is proving the fix on a real back-navigation rather than on a reload, which is what hid the bug. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/437-book-progress-refresh
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-437
**Source:** owner's play-test doc "Гра - тест", 2026-11-12, item 6: *"Refresh solved puzzles on the book even"*. Reproduced on production the same day; the measurement is below.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/pages.js, tests/test_book_landing_page.py
<!-- Derived 2026-11-12. readProgress, progressOf and SAVE_PREFIX are all in player/pages.js, which serves both /b/<slug> and /library — the library's tiles read the same saves and are in scope. tests/test_book_landing_page.py holds test_progress_comes_from_this_device_and_draws_the_readers_own_picture; tests/test_public_player_pages.py drives the library. Re-derive with scripts/impact_set.py --gate. -->
**Review score:** —
**Started:** 2026-11-12T12:00:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists — the reproduction, run on production

`https://nonogram.adverax.io/b/0a958d036e`, 2026-11-12, one tile followed end to end:

```
tile 33fa80994c on the book page        data-progress = "new"
open it, record ONE stroke              localStorage nonogram-player:33fa80994c written
browser Back to the book page           data-progress = "new"      <- stale
                                        the save is still there (read back: true)
explicit reload of the same page        data-progress = "started"  <- correct
```

So the reader's progress is read **once per fresh load**. Return to the book by the only route the product offers — the browser's Back button, since the play page has no links at all (CARD-436) — and the book shows the state it had before you played. Solve a puzzle and the book still calls it new until you think to reload.

`performance.getEntriesByType('navigation')[0].type` read `"navigate"` after the Back, not `"back_forward"`, which is what Chrome reports for a page restored from the back/forward cache: the original entry's type is kept. That is consistent with a bfcache restore, and `player/pages.js` registers **no `pageshow` listener** — progress is computed at module load and never again. *(The cause is read from the code and from that one reading; the restore itself was not independently confirmed, e.g. with a `pageshow.persisted` probe. Confirm it before fixing, because the fix differs: a bfcache restore needs `pageshow`, while a genuinely fresh load that still shows stale tiles would mean something else is wrong.)*

## Why it matters more than it looks

The book page is where a reader sees what they have done — "Solved puzzles show the picture you uncovered". The one moment they most want that to be true is the moment they have just solved one. That is exactly the moment it lies.

## What to implement

1. Recompute progress when the page is shown again, not only when it is first loaded: a `pageshow` listener that re-runs the existing read when the page was restored, and repaints the tiles.
2. The same applies to `/library`, which is served by the same module and reads the same saves.
3. Keep every property the current read has: nothing is fetched, nothing is written, any storage or parse failure is "not started" and never an error.
4. Do not re-read on every `visibilitychange` — the cost is one `deserializeState` per entry over a 160-tile book, and a tab switch is not a play.

## Acceptance criteria

- **AC-1** (a return shows what you did): on the book page, with a save written for one of its puzzles after the page was first shown, a restore repaints that tile from `new` to `started`. (test: a changed cell in `tests/test_book_landing_page.py::test_progress_comes_from_this_device_and_draws_the_readers_own_picture` — it must exercise a **restore**, not a reload; a reload already passes today, which is why this bug survived.)
- **AC-2** (solved too): the same with a save that satisfies `isClueSolved` — the tile becomes `solved` and draws the reader's own picture. (test: the same cell.)
- **AC-3** (the library too): the same property on `/library`. (test: the library's progress cell in `tests/test_public_player_pages.py`, changed.)
- **AC-4** (still reads nothing from the site): the restore issues no network request and writes no storage key. (test: the same cell as AC-1; evidence: the request count.)

**Net test count: 0 added** — the cells exist; they assert the reload path and must assert the restore path instead, since the reload path is the one that never broke.

## Worktree notes
- **[Env]** forge 2026.10.29; no `meta/.skills.yml`, so no `min_version` comparison was made. Start gate: `decision: gate`, command `./.venv/bin/python -m pytest` from `review.test_command`. Fork point: `e11c0af2` (interactive mode, target tip).
