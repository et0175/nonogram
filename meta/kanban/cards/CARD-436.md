# CARD-436: A puzzle opened from a book offers the way back to it — today the play page has no links at all

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.25d)
<!-- Basis: the slug and the book's title are already in hand on the page (CARD-420 fetches /book/<slug>.json for the theme), so the work is markup, a string and one test. The cost is deciding where it is shown, and keeping a public-only addition from drifting the shared player. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/436-way-back-to-the-book
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-436
**Source:** owner's play-test doc "Гра - тест", 2026-11-12, item 5: *"When we have 'solved' puzzle - have get back to book"*.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/assemble.py, tests/test_public_player.py
<!-- Derived 2026-11-12. The public play page is RENDERED by player/assemble.py (puzzle_solve.html plus the wrapper script that reads ?book= and fetches the book file). The owning test module must be resolved before the brief is acted on: tests/test_public_player.py, tests/test_public_player_pages.py and tests/test_player_bundle.py all drive the public play page and the first is a guess, not a derivation. Run scripts/impact_set.py --gate. -->
**Review score:** —
**Started:** 2026-11-13T09:30:00Z
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
- **[Env]** forge 2026.10.29; no `meta/.skills.yml`, so no `min_version` comparison exists. Start gate `decision: gate`; fork point interactive/target tip `199a2671`. Pin, drift and state-table gates not applicable; no dependencies.
- **[Premise re-verified before dispatch]** The card's measurement is from 2026-11-12 and five cards have shipped since, so it was re-run on production today: `/play/33fa80994c?book=0a958d036e` still has **`document.querySelectorAll('a').length === 0`** — no links at all — and still carries `?book=0a958d036e`. The premise holds exactly.
- **[Owner ruling, 2026-11-13] ALWAYS VISIBLE.** The card asked, as its one open question, whether the way back should appear only on solve (the owner's original words, "when we have 'solved' puzzle") or the whole time. Put to them with the re-verified measurement — zero links, so an unsolved reader is equally stranded and a QR arrival from a printed book has no Back entry at all — and the ruling is **always visible**: a quiet link from the moment the puzzle opens, plus a prominent one in the solved state. They declined "only when solved" and the narrower "always, but only from a book". **AC-1 therefore widens** from the solved state to the whole session, and the card's `## The question to put to the owner before merging` section is answered rather than still open.
- **[Owning test module — RESOLVED, and the card's `Touches:` guess was wrong]** `Touches:` named `tests/test_public_player.py`, and the derivation note already flagged it as a guess. It is not that module, nor either of the other two the note listed. The public `/play/<key>` PAGE — the generated shell, its hooks, its solved banner and a fixture that holds BOTH a book and puzzles outside it — is owned by **`tests/test_player_shared_ui_site.py`** (`TestSharedUi_ThePageRuns`). Derived two ways rather than by co-location: (a) `#puzzle-player-solved` is asserted against the assembled public tree in exactly one module, that one; (b) its `bundle` fixture is the pages corpus (one book, `BOOK_ORDER`) *plus* `sweep`/`stall`, which no other player module has, and it already imports `solve_to_the_end`. The nearest neighbour, and worth naming because a reviewer will find it: `tests/test_book_landing_page.py::test_a_christmas_book_dresses_its_landing_and_the_puzzles_opened_from_it` already walks the four addresses this card needs (valid book, no book, malformed slug, book that does not hold the key) — but it reaches the play page by clicking a tile and cannot reach the SOLVED state, so it could carry AC-2 and not AC-1. It is unchanged and green, which is AC-3's "nothing else moved".
- **[Net test count: +1]** One cell, `tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_a_puzzle_opened_from_a_book_offers_the_way_back_and_no_other_page_does`, plus one case added to the existing `test_a_fragment_missing_a_hook_is_refused` parametrize (not a new cell). The card's rule was "0 added if the solved-state cell exists; otherwise 1" — the solved-state cell DOES exist (`test_a_real_puzzle_plays_to_the_solved_banner`), and +1 is still the answer, stated rather than silently taken: that cell is AC-383's registry-verifying ref, drives a BOOKLESS puzzle at the default viewport, and asserts an exact seven-URL request set for that page. Widening it would have changed a referenced node's subject and put two subjects in one cell; the owner's budget is "change existing cells", not "change the one cell a registry points at".
- **[AC-1 widened by the owner's ruling]** The card's AC-1 speaks only of the solved state. The ruling of 2026-11-13 (recorded above) is **always visible plus a prominent solved state**, and that is what was built and tested. AC-2's three negatives and AC-3 are as written.
- **[ONE element, promoted — decided by a render, not by taste]** Requirement 2 asked which. It was built FIRST as a second element, a child of the solved banner, and that version was measured and rendered before being dropped: the banner's box is `contain: inline-size`, so it is only as wide as the hidden `.player-tools` — **208 px at 1280x720, 101 px at 390x844** — and a link in it overflowed onto the History buttons (seen in the render) and, at 1280, wrapped the banner's own "Solved!" and pushed the board **down 12.8 px** (2 px at 390). The `.page-head.player-head` row is the only place on this page that can hold a line of text for free — `admin.css`'s own comment says so and measured it — so the way back lives there and the solve promotes it in place: quiet grey underline while playing, the banner's own success edge and tint in a pill once solved. What tells it the board is solved is the banner's `hidden`, observed; no second copy of the predicate.
- **[Stage-height cost at 390x844: ZERO, before and after, playing and solved]** With the book and without, `.player-stage` **341.45 px high**, its top **192 px**, `.player-head` **28 px**, `.player-toolbar` **125 px** — all four identical in all four states (bookless playing / bookless solved / book playing / book solved). Also measured at 844x390 (stage 329.89, top 28, head 47.98, toolbar 296.23) and 1280x720 (stage 373.64, top 165.58, head 52, toolbar 62.58): identical there too. The equality is in the test, not just here (`_ROOM`), and the SOLVED arm of it is not ceremony — it is the arm that caught the 12.8 px above, which the unsolved-only comparison passed straight through.
- **[Declared residual: landscape]** At 844x390 the head row is a 96 px column (`admin.css`'s CARD-402 strip), so the link is **47.67 px wide** — present, tappable and ellipsised to about "← W…". Declared rather than fixed: narrowing it is a stylesheet change, and this page has no stylesheet of its own to make it in (see below).
- **[Why inline styles, and the one rule this bends]** The link is drawn by the public wrapper in `player/assemble.py`, which the card is explicit about as a deliberate exception to "the admin solver is the source" (CARD-386/399) — the admin player has no book, no `?book=` and no `/b/<slug>`. The reason is stated in the implementation's own comment, as the brief required. Its styling is inline because the page links no stylesheet but the admin's three and has no override layer by design; a fourth sheet would be the extra request AC-3 forbids, and `admin.css` is a byte-identical copy that must not be edited. Every value is a `tokens.css` custom property.
- **[SCOPE+ none]** Both changed files are the card's `Touches:` set by path (`player/assemble.py`) or its resolved correction (`tests/test_player_shared_ui_site.py` in place of `tests/test_public_player.py`). Nothing under `src/nonogram/admin/**` was touched.
- **[Hardening beyond the ACs, one line]** `id="puzzle-player-solved"` was added to `_SHARED_UI_HOOKS`. The loader now reads that element, and a template that renamed it while keeping `data-player-solved-name` would have left the loader throwing *before* it appends the payload — a page with no board at all. The hook list exists for exactly that, and the new refusal case in `test_a_fragment_missing_a_hook_is_refused` is its control.
- **[Gate]** Impact selection derived from this diff by `scripts/impact_set.py --gate --against main`: **53 test files, 4278 of 10652 tests (40.2%)** for the two COMMITTED files; **54 files, 4293 of 10653** as actually run, because the unstaged card edit is in the working tree the script reads (both figures given rather than the convenient one). Final run, against the final diff: run 1 (`-m "not wave_close_only"`) **4269 passed, 15 skipped, 8 deselected, 1 xfailed**, 920 s; run 2 (`-m wave_close_only tests/test_book_export_interior_cover.py`, the file lifted by rule S via `tests/test_player_shared_ui_site.py`) **4 passed, 146 deselected**, 30 s. Both exit 0. Skips read off `-rEfs`, never recalled: **14** x "Database not reachable: DATABASE_URL is not set" + **1** x the setrlimit platform skip — that 14 is this selection's count, not the full suite's 29, and was derived here. 9 marked tests stay owed at the wave close. (An earlier run of the pre-hardening diff was 4254 passed on 53 files; the delta is this card's own new cell plus the refusal case and the card-edit selection.)
- **[AC evidence]** AC-1: `test_a_puzzle_opened_from_a_book_offers_the_way_back_and_no_other_page_does` red (`assert back.is_visible()` -> False, the element did not exist) -> green. AC-2: the same cell, three negatives, each asserted as `document.querySelectorAll('a').length === 0` — the card's own production instrument, which is stronger than "no link of mine". AC-3: `tests/test_book_landing_page.py`'s CARD-420 theme cell unchanged and green, plus the request count in the new cell (the book page asks for exactly the bookless page's URLs plus `/book/<slug>.json`).
- **[Net test count, measured rather than taken from the report]** The round reports "+1 (one cell), plus one case added to an existing parametrize (not a cell)". Collected both sides: `tests/test_player_shared_ui_site.py` gives **47 on main and 49 on the branch — +2 node ids**. Both framings are honest about the same change, but the checkable number is 2, because a parametrize case *is* a collected node id, and the owner's budget is counted in tests. Recorded as **+2** here so a later reader comparing counts does not find a discrepancy and assume something was hidden. Against the card's own rule ("0 if the solved-state cell exists; otherwise 1") the round's reason for not widening the existing cell is sound and worth keeping: that cell is **AC-383's registry-verifying ref**, so widening it would have changed the subject of a node another artefact points at.
- **[Census: not owed, checked rather than assumed]** A new node id usually reds `tests/test_browser_fixture_scope.py`'s family census, as it did on CARD-433. It did not here, and the reason is mechanical: that census's `FAMILY_PREFIX` is **`tests/test_puzzle_solver`**, and this card's module is `tests/test_player_shared_ui_site.py` — outside the family by name. Verified by reading the constant and by running the census on the branch: **33 passed**. So no `ADDED_SINCE_BEFORE` entry was owed, rather than one being skipped.
- **[The design decision was made by a render, not by preference]** Requirement 2 asked whether the solved state gets the same element promoted or a second one. The round **built the second element first**, measured it, rendered it, and then dropped it: `#puzzle-player-solved`'s box is `contain: inline-size`, so it is only as wide as the hidden `.player-tools` — **208 px at 1280x720, 101 px at 390x844** — and a link inside it overflowed onto the History buttons and, at 1280, wrapped the banner's own "Solved!" and pushed the board **down 12.8 px**. So one element, promoted in place. That is the right way round: the cheaper answer was reached by discarding a measured one, not by choosing it in advance.
- **[Requirement 5 — zero cost, and the assertion that caught the defect]** `.player-stage` is **341.45 px** high with top **192 px** at 390x844, identical across all four states (bookless playing, bookless solved, book playing, book solved); zero cost at 844x390 and 1280x720 too. The equality is asserted in the test — and **its solved arm is what caught the 12.8 px**: the unsolved-only comparison the round wrote first passed straight through the defect. A declared residual stands: at 844x390 the head row is CARD-402's 96 px landscape column, so the link renders 47.67 px wide and ellipsises to about "← W…" — present and tappable, not fixed, because narrowing it needs a stylesheet this page does not have.
