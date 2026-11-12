# CARD-437: The book page does not notice what you just played — coming back from a puzzle leaves every tile as it was

**Status:** done
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
**Review score:** 9.0 (cycle 2)
**Started:** 2026-11-12T12:00:00Z
**Closed:** 2026-11-12T13:35:00Z
**Actual:** 2 review cycles + 1 fix round (wall clock excluded, owner ruling 2026-11-07: the clock measures the queue, not the work)
**Merge commit:** fefbcee5
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
- **AC-3** (the library too): ~~the same property on `/library`~~ — **PREMISE REFUTED, 2026-11-12, and amended here at close** so the registry stops carrying an AC that cannot be satisfied. `/library` reads no progress at all: `readProgress` is called only inside `load`'s `if (numbered)` branch, library tiles carry no `data-progress`, and `library.html` ships no progress legend. There was nothing stale there and no production change was made for it. What the cell asserts instead is that the library has no progress to go stale (`every(t => t.dataset.progress === undefined)`) and that a restore leaves its filter, its tiles and its request log untouched — a refutable claim, confirmed by both review cycles, which also guards against the wrong fix (re-running `load()` on `pageshow`). It does not red before the fix, which is stated rather than papered over. (test: `tests/test_public_player_pages.py::test_the_listing_pages_only_get_and_write_nothing`, changed.)
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
- [Review 1/3] Score: 8.5 — gated. Cleared min_score 8 and was blocked anyway, by SEVERITY: one Important finding, F-001. Risk MEDIUM, lane DEEP. Report `meta/review/20261112T131621Z-CARD-437-cycle1.yml`; `parse_review.py` verdict `accepted`, `security: applicable (0 findings)`. 0 Critical, 1 Important, 3 Minor, 4 out-of-scope. All four of the implementation's load-bearing claims were checked by the reviewer and held: claim 1 (the harness cannot restore) — `--disable-back-forward-cache` confirmed present in the installed driver bundle; claim 2 (red first) — re-verified by copying main's `player/pages.js` over the branch's and watching the cell time out; claim 3 (`/library` reads no progress) — independently confirmed, the substituted clause judged a real refutable assertion rather than a tautology; claim 4 (the hazard class is closed) — `decorate`'s side effects and the whole paint path enumerated, no third member. Two of four mutants reproduced byte-for-byte. Mutation check `deferred(cost)` per the cost ladder, gating findings present.
- **[Review sync]** 1 report(s) → `meta/review/` (found 1, copied 1, re-parsed in the main repo).
- **[Severity gate]** **BLOCKED** on F-001 (Important) despite 8.5 ≥ min_score 8 — the gate is severity, not score. F-001: the repaint discards the reader's hand-set section open/closed state. **Verified by the orchestrator independently of the reviewer, structurally, in three legs:** (i) `renderBook` recomputes `open` from `firstEasy`/`entries.length <= OPEN_ALL_UP_TO` and then `list.replaceChildren(...)`, while the hand-set state lives in exactly the `grid.hidden` / `aria-expanded` pair the section-head handler flips — so the repaint cannot preserve it; (ii) `OPEN_ALL_UP_TO` is 24 and the owner's real book serves **160** tiles (counted on production by this session earlier today), so sections are NOT all-open in production and this is the normal case, not an edge case; (iii) the only sectioned-book cell, `test_a_long_book_is_cut_into_level_sections_that_open_and_close`, is **untouched by this diff** — its one appearance in the diff is a git hunk HEADER (the enclosing-function annotation), every real change sitting in the progress and Christmas cells — and it never restores, so the suite is structurally blind to the regression. No adversarial pass was spawned: the finding was verified at the source instead, which is stronger than a second opinion about it.
- ~~**One behaviour change this card introduces, named rather than hidden.**~~ **Superseded by the
  cycle-1 fix below — the hand-set state is now preserved, so there is no behaviour change left to
  report here.** What this bullet said, and why it was wrong, is kept in the fix note: the open set
  was recomputed on every repaint, I called the whole of it a product question, and only the
  *default* is one. Discarding state the reader set by hand was a regression, not a decision.
### Fix round, review cycle 1 — F-001 (the only gating finding)
- **What the finding was.** The repaint discarded the reader's hand-set section open/closed state:
  `paint()` re-ran `renderBook`, which recomputed `open` from `firstEasy` / `OPEN_ALL_UP_TO` and then
  called `list.replaceChildren(...)` — and the state lives in exactly the `grid.hidden` +
  `aria-expanded` pair the section head's click handler flips, on the nodes `replaceChildren` throws
  away. `OPEN_ALL_UP_TO` is 24 and a real book is 100–160 tiles, so this is the normal case there,
  while every fixture in the changed cells has 4 puzzles and is therefore all-open in both readings.
  The worst case is the moment the card exists for: `continueTarget` is the highest *started* puzzle,
  so a reader who **solves** the one they were on came back to that section closed.
- **What I changed** (fix commit `c65850ef`, `git diff --numstat b72c5be3 c65850ef`: `player/pages.js`
  +35 −12, `tests/test_book_landing_page.py` +19 −1; no other file):
  - `sectionId(section)` — the `book-section-<from>` id, lifted out of `sectionFor` so the reader and
    the writer of that key are the same expression. It is derived from the section's first PRINT
    number, i.e. from `entries`, which a repaint does not change — so the key is stable across one.
  - `openSections(page)` — reads `!grid.hidden` per `.book-squares` into a `Map` keyed by that id,
    BEFORE the replace. Empty before the first paint.
  - `renderBook(page, entries, progress, slug, held = new Map())` — the computed default is now named
    `byDefault` and `held.get(sectionId(section)) ?? byDefault` is what reaches `sectionFor`, so the
    override is on top of today's default rather than instead of it.
  - `paint()` passes `openSections(page)`.
- **The default open set is untouched**, which is what the finding asked for: on a first load `held`
  is empty, every section falls through to `byDefault`, and the short-book clause of the long-book
  cell (all sections `true` on a 4-puzzle book) still passes unchanged. I cannot tell "untouched"
  from "hand-set to the same value as the default" — nothing on the page records which — so I took
  the conservative route the brief names: the observed state is carried over for every section, which
  is correct in both of those cases. The one thing it gives up is a default that would have *moved*
  on the repaint (e.g. `continueTarget` walking into another section): that section now stays as the
  reader last saw it instead of auto-opening. That is the right trade here — the auto-open it
  replaces is the very thing that was closing the section they had opened.
- **Red → green on the new assertion** (the existing cell
  `test_a_long_book_is_cut_into_level_sections_that_open_and_close`, which already builds the
  30-puzzle sectioned book and already clicks Medium open and Easy closed — so it is a CHANGED cell;
  **net test count stays 0 added**):
  - RED, with `git show HEAD:player/pages.js` copied over the fixed one:
    `AssertionError: assert ['true', 'false', 'false'] == ['false', 'true', 'false']` / `At index 0
    diff: 'true' != 'false'` — `1 failed in 1.93 s`. That is the reviewer's probe reading, reproduced
    from inside the suite.
  - GREEN with the fix: `tests/test_book_landing_page.py` → **7 passed in 4.54 s**, 0 skipped
    (`-o addopts= -rEfs`). The file was restored from `/tmp` and `git diff --stat -- player/pages.js`
    re-read afterwards.
  - The wait is on the repaint having happened, not on a sleep: the cell stamps
    `dataset.beforeRestore` on the current `.book-section` and waits for it to be gone, which only
    `replaceChildren` can do. So the assertion cannot pass by running before the repaint.
- **The three invariants on the restore path are unchanged by this fix**: nothing is fetched, nothing
  is written, and a storage or parse failure is still "not started" — `openSections` touches only
  the DOM it is handed, and the fix adds no `localStorage`, no `import` and no request.
- **DECLARATIONS F-001** — re-derived from the code just written: the stale "one behaviour change"
  bullet above is struck through and superseded (it stated the opposite of what the code now does);
  `paint()`'s own comment now says the open/closed state is the reader's and is read off the page
  rather than recomputed; `openSections` carries the why; `renderBook`'s default-open comment is
  still correct as written (the defaults did not move) and is confirmed, not reworded. No failure
  matrix row and no numeric bound changed. `renderBook`'s fifth parameter is a new input, not a
  second job for an existing one.
- **What the finding got wrong: nothing material.** Its measurement, its mechanism and its "normal
  case in production" reading all reproduced. Two small notes: the remedy came to 16 non-comment
  added lines rather than the sketch's "~6" — counted, not estimated (`git diff b72c5be3 c65850ef
  -- player/pages.js`, `+` lines less comments and blanks); the id helper, the named `byDefault` and
  re-indenting the `sections.map` arrow into a block are the extra. And it is the grid
  that carries the id (`aria-controls` on the head points at it), so `openSections` reads the grids
  and not the heads.
- **F-002 narrows but does not dissolve.** The repaint still rebuilds every square and still tears
  down and re-lays the decorations — I did not take the narrower in-place repaint, only the state
  carry-over, so the 3896-needle garland regeneration the reviewer measured is unchanged. Left as the
  reviewer filed it (Minor, not this round's scope).
- **Not fixed this round, by instruction**: F-002, F-003, F-004 and the four out-of-scope
  observations. `tests/test_public_player_pages.py` and `player/decor.js` were not touched.
- **[Fix 1] declarations** F-001 fixed in `c65850ef` (`player/pages.js` +35/−12, `tests/test_book_landing_page.py` +19/−1; nothing else touched, so the round's scope held). The remedy is an override, verified here rather than taken on trust: `renderBook`'s computed default is now named `byDefault` and the lookup is `held.get(sectionId(section)) ?? byDefault`, so an untouched section still takes today's default, and `held` is empty on a first load. The hinge that would have made the fix silently inert — whether the map's key and its lookup are the same string — is `grid.id = id` against `openSections`' `held.set(grid.id, …)`, both derived from `sectionId`; checked. Red-first reproduced from inside the suite (`assert ['true','false','false'] == ['false','true','false']`), which is the reviewer's probe reading, and the new assertion waits on the repaint having happened (a `dataset.beforeRestore` stamp that only `replaceChildren` can clear) rather than on a sleep. F-002 narrows but does not dissolve and was left as filed; F-003, F-004 and the four out-of-scope observations untouched.
- **[Fix 1] the trade the fix makes, named for cycle 2 to judge:** carrying the observed state means a default that would have MOVED on the repaint — `continueTarget` walking into a different section — no longer auto-opens that section. That is the right trade here, because that auto-open is the very mechanism that was closing the reader's section, but it is a product-visible consequence and not a pure bug fix. The reader's own closed section now stays closed even when their next puzzle is inside it.
- **[Provenance correction, orchestrator]** The fix round's spawn tag line read `forge.model=sonnet`, and `forge:commit` rendered that verbatim into `c65850ef`'s trailer. It is wrong: no `model` override was passed (this project has no `models:` block, so the procedure's instruction is to spawn without one and inherit), and the round ran on the session's own model, Opus 5. My error in assembling the tag, not the fix agent's — it reported the discrepancy rather than hiding it. The commit is left unamended (the standing rule here is never to amend), so this note is the correction of record.
- **[Build gate, fix round 1]** Impact-scoped, derived in the worktree after the last source edit (`scripts/impact_set.py --gate --against main`): **74 test files, 5226 of 10631 at this gate**. Run 1 `1 failed, 5203 passed, 15 skipped, 8 deselected, 1 xfailed` in 22:47; run 2 (the two lifted `wave_close_only` files) `6 passed, 176 deselected`. The single red was `tests/test_book_pdf_memory.py::TestMemoryGuard_StillFailsWhenTheExportItselfRegresses::test_an_export_that_retains_a_fraction_of_the_book_fails`, the pre-existing breakage recorded two notes above — fixed on main in `a10c5145` **after** this run started, so this gate's red is a stale copy of it in the worktree and not a finding about the card.
  **One harness failure of the orchestrator's own, recorded because of how it failed.** The first attempt at this gate died at `collected 0 items` / `ERROR: file or directory not found: after`: the file list was extracted with `sed '/^selection:/,$p'`, which swallowed the block's trailing prose line (`after those: nothing more is owed AT THIS GATE…`) and handed `after` to pytest as a path. It failed **loudly**, which is the only reason it cost nothing — had the stray token been a real path, pytest would have run a slightly wrong selection, reported a clean green, and that figure would have been recorded as the gate. The extraction is now anchored to `^  tests/.*\.py$` and prints its own file count (74, matching the block's own figure) so the run states what it ran.
- **[Rebase]** Rebased twice while in flight, cleanly both times, because another session kept landing on main: first onto `a10c5145` (to pick up the memory-guard fix), then onto `c4949d7a` (after CARD-439 and CARD-440 merged). The branch's diff against main is exactly its three files after each rebase, asserted with `git diff main --name-only`. The worktree's card copy was reverted before the first rebase, after confirming all 175 of its note lines had already reached main's copy — checked line by line rather than assumed, because `git rebase` with local changes to a file main also changed is the refusal this session has already been bitten by once.
- **[Review 2/3 dispatch]** Reviewer dispatched on the rebased branch (cycle 2, class heavy). Briefed to NOT re-derive what cycle 1 established by running, except where the fix round's diff disturbs it — the fix changed `renderBook`'s signature and added a DOM pre-read, so cycle 1's "the once-only hazard class has no third member" is the conclusion most worth re-testing. Four questions put to it: the `??` override's edges (a section absent from the map, the very first paint, a non-boolean in the map); whether the `book-section-<from>` key is stable across a restore in which the SECTIONS themselves move (a puzzle changing tier, the Continue target moving); the new cell's discrimination, to be re-verified by checking out the pre-fix file; and a ruling it must make rather than note — whether no longer auto-opening a section the default would have moved into is correct, Minor, or a defect of this diff.
- [Review 2/3] Score: 9.0 — passed. Risk MEDIUM, lane FAST, **0 Critical, 0 Important** — the severity gate that blocked cycle 1 is **clear**. Report `meta/review/20261112T150813Z-CARD-437-cycle2.yml`; `parse_review.py` verdict `accepted`, `security: applicable (0 findings)`. F-001's remedy was confirmed by measurement, not by reading: red-first re-derived byte-for-byte from the pre-fix file, the key proved stable (`sectionsOf` depends on `entries` ONLY, and the restore never re-fetches the book file, so no puzzle can change tier and no boundary can shift inside one document lifetime), and the once-only hazard class re-tested across four consecutive restores with every element count constant. The **deferred mutation check was paid on this stable cycle**: `?? → ||` KILLED (the undefined-vs-falsy edge is pinned by a test, not by a comment), `!grid.hidden → grid.hidden` KILLED by two cells, and `section.from → section.to` SURVIVED as a genuine equivalent mutant (both derive from the same immutable `entries`; the id's only jobs are uniqueness and stability). 5 Minor, 0 gating.
- **[Review sync]** 2 report(s) → `meta/review/` (cycles 1 and 2, both re-parsed in the main repo).
- **[Review 2/3 ruling]** The trade was RULED, not noted. Cycle 2 measured the suppression on the long-book fixture — with a save planted, Continue walked to puzzle 30 in Hard and Hard stayed closed — and ruled it **correct behaviour, not a finding**: a hand-set state is the reader's instruction and the default is a heuristic, overriding the first with the second on every return is exactly the regression F-001 named, and **nothing becomes unreachable** (the Continue card lives outside `[data-pages-list]`, survives `replaceChildren` and repaints with the new target; the closed section's own header still repaints its count, measured as `0 of 12`, `0 of 10`, `0 of 8 solved`). The orchestrator had called this the right trade; the reviewer was briefed to be free to disagree and reached the same answer from its own measurement.
- **[F-201, fixed before merge, by the orchestrator]** Cycle 2's first Minor **refuted a claim this card itself had recorded**. `openSections` writes an entry for EVERY rendered section — nothing on the page records which ones the reader *touched*, only what state they are in — so `?? byDefault` can never fall through on a repaint, and the carried state wins over the computed default **even when that default has moved**. Both the comment above `openSections` ("a section nobody has touched reads back AT its default") and this card's own `[Fix 1]` note ("the defaults did not move") said otherwise. Corrected in `6a2f77be`: prose only, `node --check` clean, both touched modules re-run green (40 passed). Committed by the orchestrator rather than a fix round because the subject is two sentences of comment whose falsity was already established — and because **this project treats a false comment as a defect in its own right**: CARD-432 exists because one in `admin.css` asserted that the page never scrolls. The provenance is recorded so the commit is not mistaken for a reviewed change.
- **[AC/EC check]** Run by node id, because this project's AC gate is unwired and a card-level invocation would prove nothing: `test_progress_comes_from_this_device_and_draws_the_readers_own_picture` (AC-1, AC-2, AC-4), `test_a_long_book_is_cut_into_level_sections_that_open_and_close` (F-001's guard), `test_a_christmas_book_dresses_its_landing_and_the_puzzles_opened_from_it` and `test_the_listing_pages_only_get_and_write_nothing` (AC-3 as amended). **4 passed, 0 skipped** — the skip count was read, not assumed, since a silent skip and a pass are indistinguishable without it.
- **[Note correction]** The `[Fix 1]` note above names fix commit `c65850ef`, which the two rebases replaced; the fix is now `2c204422` and its `--numstat` figures (+35/−12 and +19/−1) reproduce exactly on the rebased copy. Cycle 2 caught the stale sha.
- **[Merge gate]** Impact-scoped, derived from the final diff on the rebased branch (`head=6a2f77be`): **74 test files, 5226 of 10631**. Run 1 `2 failed, 5204 passed, 15 skipped, 8 deselected, 1 xfailed` in 21:49; run 2 `6 passed, 177 deselected`. **Both reds are foreign, and both were verified by the orchestrator in the MAIN checkout rather than argued away:** `tests/test_puzzle_solver_phone.py::TestSolverPhone_CompactToolbar::test_icons_only_when_compact` at `[390-844-True]` and `[844-390-True]`, failing `At index 3 diff: 'Line' != 'Probe'` — **CARD-439 added a `Line` control to the compact toolbar and did not update that census**. This branch never touches `tests/test_puzzle_solver_phone.py` (asserted with `git diff main --name-only`), and the two cells fail identically on main with no card branch involved. The memory guard that reddened the fix round's gate is fixed on this base and passes. Raised to the owner as its own subject, exactly as the memory guard was, because it reds every card's gate until someone owns it.
- **[Merged]** `fefbcee5`, `--no-ff`, three commits replayed. Both review reports were confirmed byte-identical in the main repo **before** the worktree was removed (`cmp` on each, not a count) — this session destroyed two review YAMLs earlier by removing a worktree first, and `meta/review/**` is gitignored, so there is no recovering them.
