# CARD-437: The book page does not notice what you just played — coming back from a puzzle leaves every tile as it was

**Status:** review
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
- **The bfcache question, settled before any production code was written.** Three probes, all in
  `scratchpad/card437/` (gitignored), all against this project's own `browser_page` fixture unless
  said otherwise:
  - *This harness cannot produce a restore.* After `page.goto` away and `page.go_back()`, a
    `pageshow` listener registered before leaving is **gone** — the `window` property holding its
    log reads `None` — and `performance.getEntriesByType('navigation')[0].type` reads
    `"back_forward"`. That is a document **re-created** from the history entry, i.e. a fresh load.
    `notRestoredReasons` on that entry reads `null` (not populated here).
  - *It is not just the flag.* Playwright hardcodes `--disable-back-forward-cache` in its Chromium
    switches (`playwright/driver/package/lib/coreBundle.js`, `chromiumSwitches`). Launching
    Chromium with `ignore_default_args=["--disable-back-forward-cache"]` gave the **same two
    readings**, so no fixture here can produce the real thing.
  - *The card's production reading is confirmed, and its cause analysis is right.* Production read
    `"navigate"` after Back, which the card called "consistent with a bfcache restore" while
    flagging it as unconfirmed. I confirmed it **by hand in real Chrome** against the assembled
    fixture site (served through the test fixture's own host, so the shipped `vercel.json` rewrites
    applied): opened `/b/<slug>` with all four tiles `new`, registered a `pageshow` probe, tapped a
    tile, recorded **one real stroke** with the mouse (`localStorage nonogram-player:e719e5770a`
    written, one cell `filled`), then went Back. The probe read **`persisted: true`** — the same
    document handed back, listener and all — with `navigation[0].type` still `"navigate"`. So the
    restore is real and `pageshow` is the right hook.
  - **Consequence, stated plainly: the real restore path is NOT covered by the suite.** The cells
    pin the handler instead, by dispatching `PageTransitionEvent('pageshow', {persisted: true})`.
    All of the above is written into `_restore`'s docstring in `tests/test_public_player_pages.py`
    so the next reader does not re-derive it.
- **The fix.** `player/pages.js`, book branch of `load()`: the paint is named (`paint`), `progress`
  and `shown` became `let`, and a `pageshow` listener re-runs the existing `readProgress` and
  repaints when `event.persisted`. Nothing new reads storage — `progressOf`/`readProgress` are
  reused unchanged, so "nothing fetched, nothing written, any failure is not started" holds because
  it is literally the same read.
- **AC-1: test `test_progress_comes_from_this_device_and_draws_the_readers_own_picture` red→green.**
  Red first, for the right reason: with the plant done and the page never re-opened, the restore
  never repainted and the wait for `data-progress == "started"` timed out at `PAGES_SETTLE_MS`.
  Green after the listener landed. The cell no longer re-opens the page at all — that was the line
  that let the defect through CARD-418's review.
- **AC-2: same test, same cell, red→green** — the solved square (`data-progress == "solved"`, the
  reader's own picture: one `M` per black cell, the board's own `viewBox`) is reached across the
  same restore, in the same timed-out red.
- **AC-4: same cell, green** — `asked[quiet:] == []` (no request at all after the restore began;
  the player's reader is already in the document's module map, so the dynamic import costs nothing)
  and `{...localStorage}` identical before and after. Also on the restore path now: the damaged-save
  arm (`'{not json'` → `new`, `pageerror` list empty, the damaged bytes still exactly there).
- **AC-3: `tests/test_public_player_pages.py::test_the_listing_pages_only_get_and_write_nothing`,
  green — and it REFUTES the card's premise.** The card says "the library … reads the same saves".
  It does not. `readProgress` is called only inside `load`'s `if (numbered)` branch; the library's
  tiles are `tileFor`'s (extent and tier, no `data-progress`), `library.html` has no progress legend,
  and `grep` for `data-progress` across the tree finds it only in `squareFor`, `player.css` and the
  book landing's tests. So **there is nothing stale on `/library` to refresh**, and no production
  change was made for it. The clause asserts what is true instead: every library tile's
  `dataset.progress` is `undefined`, and a restore there leaves the tiles, the reader's chosen
  filter and the request log untouched. **This clause does not red before the fix** (there was no
  listener to get wrong) — it is a guard against the wrong fix, and it earns its place: see the
  mutant below.
- **Mutants run, to show each new claim is live** (each applied to `player/pages.js`, measured, then
  reverted):
  - `pageshow` handler ignores `persisted` → the progress cell reds (`'solved' == 'new'`), so the
    "do not re-read on every show" requirement (card item 4) is actually held.
  - the restore implemented as "re-run `load()`" and registered on both pages → the library clause
    reds (6 tiles where 2 were shown: the reader's filter was thrown away, and `index.json` was
    re-fetched). This is the mutant AC-3 exists for.
  - decorations not removed before a repaint → the Christmas cell reds with `garlands: 2`,
    `snowed: 8` (6 expected), `needles: 7792` (3896 expected).
  - the jump box re-wired on every paint → the progress cell reds with `__wired == 2`.
- **Two hazards the repaint created, both found by reading the code the repaint re-runs, both fixed
  and both now measured** (this is the part of the card that grew, and it is all inside
  `player/pages.js`):
  - *`decorate` prepends and is documented "called once".* A repaint that called it again hung a
    second garland on the body and a second drift on the jump box and the Continue card. Fixed by
    removing `.decor-garland, .decor-snow` before redrawing; the bough is seeded from a constant, so
    the redraw is the same bough. (The section heads are new elements each paint, so they do need
    re-snowing — which is why the decoration cannot simply be left out of the repaint.)
  - *The jump box's listeners accumulated.* It lives outside the list `renderBook` replaces, so
    re-running `renderBook` added a second `input` and a second `submit` listener on every return.
    Fixed by lifting that block out of `renderBook` into `wireJump`, called once: nothing in it
    reads progress, so it never belonged in the per-paint path.
- **One behaviour change this card introduces, named rather than hidden.** The repaint re-runs
  `renderBook`, which recomputes which sections are open (first Easy + the one holding the Continue
  puzzle). So a section the reader opened or closed by hand is reset on a return. Usually this is
  what they want — the section holding the puzzle they just played is the Continue section and
  opens — but a reader who **solves** the puzzle they were on can come back to that section closed.
  Keeping the hand-set state would mean a second notion of "open" passed into `renderBook`; whether
  it should survive a return is a product question, so it is reported here rather than decided. No
  card raised (below the cut bar until the owner wants it).
- **Net test count: 0 added**, as the card asked. Three cells changed, no cell added, no cell
  removed. Two module-scope helpers added (`_restore` in `tests/test_public_player_pages.py`,
  `_restored` in `tests/test_book_landing_page.py`) and one constant each (`PAGES_INERT_MS`,
  `_DECOR` — the latter is the Christmas cell's own expression, lifted so it can be read twice).
- **SCOPE+ `tests/test_public_player_pages.py` — AC-3, the library shares the module.** No other
  file outside the card's `Touches:` was edited.
- **Impact set, derived in this worktree from my own diff** (`scripts/impact_set.py --gate
  --against main`, re-derived after the last source edit): `changed (3)` →
  **73 test files, 5214 of 10631 tests collected, 5212 at this gate**; 2 marked files lifted
  (`tests/test_book_export_interior_cover.py` by the two test files, `tests/test_browser_fixture_scope.py`
  by `player/pages.js`), 7 marked tests still owed at the wave close. Both printed commands were
  run. (The 73 happens to equal the card's predicted figure; it was printed here, not carried.)
- **Gate result: `1 failed, 5189 passed, 15 skipped, 8 deselected, 1 xfailed` in 1384.54 s (run 1)
  and `6 passed, 176 deselected` in 75.85 s (run 2).** The 15 skips are 14 × "Database not reachable:
  DATABASE_URL is not set" (UNARMED) and 1 × the `setrlimit(RLIMIT_AS)` platform skip — both read
  off `-rEfs`, not recalled.
- **The one red is NOT this card's, and it is red on `main`.**
  `tests/test_book_pdf_memory.py::TestMemoryGuard_StillFailsWhenTheExportItselfRegresses::test_an_export_that_retains_a_fraction_of_the_book_fails`.
  Its assertion is `smallest_caught < retained < CORPUS_PAGE_COUNT / 10`; the left clause passes
  (`15.3 < 20`) and the right one is `20 < 19.8`, a comparison of two constants that cannot pass at
  any load. `tests/test_book_pdf_memory.py`, `tests/helpers/` and all of `src/` are byte-identical
  to `main` in this worktree (`git diff main --quiet`), and the same cell run **in the main checkout**
  fails identically. Cause, from the file itself: `CORPUS_PAGE_COUNT` is derived from the fixture
  corpus and now reads 198, so its tenth fell under the test's hard-coded `retained = 20` — the
  closing thank-you page (owner 2026-11-10) is the last commit to touch the file, and the corpus was
  already under the line before it. Left alone: different file, different subject, and what
  `retained` should now be — or whether it should be derived rather than written — is a judgement
  for whoever owns that guard. **It reds every card's merge gate until someone fixes it**, so it is
  raised here rather than absorbed.
- **[Blocker check]** No `[BLOCKER` line in the worktree copy (prefix match, not the exact token).
- **[Scope]** Diff touches `player/pages.js`, `tests/test_book_landing_page.py`, `tests/test_public_player_pages.py`. The third is one module beyond `Touches:` and is DECLARED (`SCOPE+`, AC-3's library cell) — not a growth escalation (the gate's bar is 2+ components beyond the slice, or covering a ready sibling's `Touches:`; neither holds). The card carries no `## Guardrails` section, so there is no structural contract to breach. `git diff main` also lists `meta/kanban/cards/CARD-437.md`, which is MAIN's own stamp commit moving under a branch cut before it — the branch's three committed files are the three above, so INV-023 holds (asserted with `git diff <fork-point> HEAD --name-only`).
- **[Build gate]** The agent's impact-scoped run: 73 test files, 5212 at the gate, `1 failed, 5189 passed, 15 skipped, 8 deselected, 1 xfailed` + `6 passed, 176 deselected`. Figures are the agent's, not re-run here; the merge gate re-runs cold. **The one red is not attributable to this card and was verified independently by the orchestrator in the MAIN checkout**: `tests/test_book_pdf_memory.py::TestMemoryGuard_StillFailsWhenTheExportItselfRegresses::test_an_export_that_retains_a_fraction_of_the_book_fails` asserts `smallest_caught < retained < CORPUS_PAGE_COUNT / 10` and reduces to `assert 20 < (198 / 10)` — two constants, unpassable at any load, because `CORPUS_PAGE_COUNT` is derived from the fixture corpus and now reads 198 while `retained` is hard-coded 20. `src/`, `tests/helpers/` and that module are byte-identical to main on this branch. Classified as a pre-existing breakage of the gate itself, not a build failure of this card, so the review cycle proceeds; it is raised to the owner as a separate subject because it reds EVERY card's merge gate until it is fixed.
- - **[Review 1/3]** Reviewer dispatched (cycle 1, min_score 8, severity gate on; `review.parallel: false`, one reviewer, class heavy).
