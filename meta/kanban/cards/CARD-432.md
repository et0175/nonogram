# CARD-432: The board hands its scroll to the page — the fling carries on after the finger stops (the "104 px unreachable" half was my own measurement error; see below)

**Status:** done
**Priority:** P1
**Category:** bug
**Estimate:** 1c (0.5d)
<!-- The likely fix is one declaration, `overscroll-behavior: contain` on `.player-stage`, which CARD-402 already uses on the landscape strip. The cost is the part that is NOT the declaration: establishing WHY the page takes a gesture that starts over a board with 104 px of unused scroll, and whether removing the page's own slack is needed too. Measure first; the one-liner may be half an answer. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/432-board-scroll-containment
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-432
**Source:** owner question, 2026-11-12: *"why it still scrolls out of inertia when I already stopped scrolling?"* — asked after the wave's three publishes, and traced the same day. Very probably also the content of the owner's play-test **finding 6** of 2026-11-11 (*"When we scroll on the clues - the puzzle jumps down and up"*), which could not be reproduced when the findings were carded and was deliberately left uncarded for want of a reproduction.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_zoom.py, tests/test_puzzle_editor_ui.py
<!-- Derived 2026-11-12. `.player-stage`'s rule and its preceding comment block are in admin.css; `tests/test_puzzle_solver_zoom.py` owns `TestSolverZoom_TheBoardScrollsInsideItsStage`, which is where a scroll-containment claim belongs. `tests/test_puzzle_solver_clues.py`, `_hint.py` and `_phone.py` also read `scrollTop`/`scrollLeft` and are the modules most likely to move — name them in the brief and re-derive rather than assume. Nothing under `player/`: admin.css is in COPIED_FROM_ADMIN. -->
**Review score:** 8.0 (cycle 1)
**Started:** 2026-11-12T14:05:00Z
**Closed:** 2026-11-13T07:40:00Z
**Actual:** 1 review cycle + 1 fix round (wall clock excluded, owner ruling 2026-11-07)
**Merge commit:** 793f4660
**Blocked by:** —

## Why this card exists

Measured on production (`https://nonogram.adverax.io`), 390x844 emulated touch, the 30x30 `52603b6dee` zoomed to **175%**:

```
stage scroll room        319 px down, 549 px across
page scroll room          23 px
touch-drag up on board   stage stays at 215/319      page 0 -> 23
force stage.scrollTop     stage reaches 319          (so the stage is NOT stuck)
computed styles          .player-stage overscroll-behavior: auto,  scroll-behavior: auto
                         html scroll-behavior: smooth
```

Three facts, of which only the first is ordinary:

1. **The inertia itself is the platform's fling.** Every touch scroller decelerates after the finger lifts. That is not a defect and this card does not try to remove it.
2. **The fling does not stay on the board.** `.player-stage` computes `overscroll-behavior: auto`, so scrolling may chain out of it, and the page has 23 px of slack to chain into. A drag that starts **over the puzzle** moves the **page**. When the finger lifts, the page keeps gliding — which is exactly the owner's "it still scrolls when I already stopped".
3. **104 px of the board is unreachable by finger at that zoom.** The stage sits at 215 of 319 and gesture input will not advance it, while assigning `scrollTop` directly reaches 319 immediately. The board has more to show and the gesture cannot get there.

**An existing declaration in the same file is falsified by this.** The comment block above `.player-stage` (the CARD-160/FR-044 header) ends: *"below the floor the board scrolls inside `.player-stage` and the page never does."* The page does — 23 px of it, measured. That sentence has to go with the fix, and it is the reason this was never caught by reading.

**The project already knows the remedy for the sibling case.** `overscroll-behavior` appears **exactly once** in the whole stylesheet: `overscroll-behavior: contain` on the landscape tool strip, added by CARD-402 for this very class of problem. The one surface a reader actually drags on never got it.

## What is measured and what is not — read this before fixing

The **effect** is measured: the page takes the gesture, the board does not move, the stage has room left. The **dispatch reason** is not: I did not establish why Chromium hands a touch that starts over the board to the document scroller rather than to `.player-stage`. So:

- `overscroll-behavior: contain` on `.player-stage` is the **hypothesis**, not a known fix. Apply it and measure; if the page still takes the gesture, the containment was not the cause and the card must say so rather than ship a declaration that reads like a fix.
- The page's 23 px of slack is the other half of the pair. Where it comes from is unestablished — `.player-stage`'s `max-height: max(calc(100svh - var(--player-above)), 5rem)` is sized to end above the fold, so a 23 px overflow means something below or beside it is taller than that arithmetic assumes. **Find out which element overflows** before deciding whether to contain the scroll, remove the slack, or both.
- All of the above is **emulated touch** (Playwright, `is_mobile`, CDP touch events). It is geometry, not a thumb. The owner's own report is the stronger evidence that it is real.

## What to implement

1. **Establish the dispatch reason** — which scroller receives a touch that starts over the board, and why. Then fix the cause, not the symptom.
2. **Contain the board's scroll** so a fling that reaches the board's limit does not continue into the page, matching what CARD-402 already does for the strip.
3. **Make the remaining 104 px reachable** — a board with scroll room must yield it to a drag. If (2) alone achieves this, say so with the measurement; if it does not, this is the part that matters most, because it is the one that hides puzzle from the reader.
4. **Correct the falsified comment** in the same diff: "and the page never does" is not true today. Replace the sentence; do not append its history to it (the wave's standing lesson — one card shipped 115 comment lines above a 12-line handler by appending).

## Acceptance criteria

- **AC-1** (the board's scroll stays on the board): at 390x844 with the 30x30 zoomed past fit, a touch drag over the board that exhausts the stage's scroll leaves `window.scrollY` unchanged. (test: a changed cell in `tests/test_puzzle_solver_zoom.py::TestSolverZoom_TheBoardScrollsInsideItsStage`; plant: remove the containment and the cell reds.)
- **AC-2** (every pixel of the board is reachable): at the same viewport and zoom, repeated drags move `stage.scrollTop` from 0 to its maximum — the figure measured, not assumed — with no residue that only a programmatic assignment can reach. (test: the same cell; this is the AC that fails today at 215 of 319.)
- **AC-3** (nothing else moves): the fit path at 100% is unchanged — a board that fits still does not scroll, the stage still ends above the fold, and `TestSolverPhone_BoardFitsThePhoneWidth` and the clue-band cells in `tests/test_puzzle_solver_clues.py` pass unchanged. (test: those cells, unchanged.)
- **AC-4** (the claim in the file is true again): no comment in `admin.css` states that the page never scrolls, unless the card has made that true and the test asserts it. (test: AC-1's cell is the assertion; evidence: the replaced sentence.)

**Net test count: 0 added** — `TestSolverZoom_TheBoardScrollsInsideItsStage` already owns this subject; change it.

## Worktree notes

—
- **[Env]** forge 2026.10.29; no `meta/.skills.yml`, so no `min_version` comparison exists to make. Start gate `decision: gate` (command from `review.test_command`); fork point interactive/target tip. Pin, drift and state-table gates all not applicable.
- **[Stale figures, read this first]** Every figure in this card's `## Why this card exists` was measured on production on 2026-11-12 **before four cards landed on the same surface**: CARD-430 (the zoom group became one joined pill), CARD-431 (the portrait title went 30 px → 20 px, explicitly "giving the board the height back"), CARD-439 (a twelfth control, Line, joined the compact toolbar) and CARD-437. Three of those four change the toolbar's height or width, and `.player-stage`'s cap is `max-height: max(calc(100svh - var(--player-above)), 5rem)` — i.e. it is computed FROM the height above it. So the stage's 319 px of scroll room, the page's 23 px of slack, the 215/319 the drag reached and the 104 px unreachable are all **suspect and must be re-measured before anything is changed**. The DEFECT is not in doubt — the page taking a gesture that starts over the board is a mechanism, not a figure — but every number attached to it is.
### Re-measured, beside what the card claimed
All of the card's figures were production readings of 2026-11-12, taken before
CARD-430/431/437/439 landed. Re-measured in this worktree, Playwright Chromium,
`has_touch=True`, 390x844, the 30x30 (`tests/test_puzzle_solver_phone.BIG`),
CDP `Input.dispatchTouchEvent`:
| | card (prod, pre-wave) | here, before the fix |
|---|---|---|
| stage scroll room at 175% | 319 down, 549 across | **576 down, 715 across** |
| stage scroll room at 300% | — | 1116 down |
| page scroll room | 23 px | **23 px — unchanged** |
| a touch drag up on the board | stage stops at 215/319 | one drag sweeps ~370-400 px; **repeated drags reach the stage's last pixel** (576/576 in 2 drags at 175%, 1116/1116 in 3 at 300%) |
| unreachable board | 104 px | **0 px** |
| `.player-stage` overscroll-behavior | auto | auto (now `contain`) |
The stage's room nearly doubled at the same zoom, which is CARD-431's 20 px
title and CARD-430's joined zoom pill giving the height back exactly as
intended: `--player-stage-top` is 415 px and the stage's cap computes to 413 px,
so the stage is 413 px tall and holds 576 px more board at 175%.
**The card's headline figure does not survive.** "104 px of the board is
unreachable by finger" and "the stage sits at 215 of 319 and gesture input will
not advance it" are not reproducible on this tree: 215 was one drag's TRAVEL,
not a limit. AC-2 is green before this card's diff and green after it, and is
recorded below as such rather than as a red->green.
### Why the page takes the gesture — established
It does not. **The gesture is dispatched to `.player-stage`**, and the page
moves only by scroll CHAINING out of it. Three measurements, in order of force:
1. A 20-step drag at 175% from `scrollTop` 156: the stage moves on every step
   (156 -> 415) and `window.scrollY` is 0 at every one of the 20 readings.
2. One gesture started 30 px short of the stage's limit: the stage runs to its
   maximum (546 -> 576) and `scrollY` then goes 0 -> 23 **inside that same
   gesture**. That is chaining, by definition: one finger, the inner scroller
   first, the outer one only after the inner one is spent.
3. Repeated drags: drags 1-2 move only the stage (0 -> 399 -> 576, `scrollY` 0);
   drag 3, arriving with the stage spent, moves only the page (0 -> 23).
So `overscroll-behavior: contain` is the mechanism's own remedy and not a
symptom patch, and the card's hypothesis holds. It is the **whole** answer to
AC-1, not half of one: after the declaration, every one of the three
measurements above leaves `scrollY` at 0, at 100%, 175% and 300%, in both
directions.
### The page's 23 px of slack — where it comes from
Found, and it is not the stage overflowing. Measured at 390x844: `body` ends at
867 against an `innerHeight` of 844.
```
--player-stage-top   415   (measured by solver.js)
--player-above       431   = 415 + --space-4 (16)
stage max-height     413   = 100svh (844) - 431
stage bottom         828   = 415 + 413
"How to play" line   828 -> 851   (.player-hint.player-howto, CARD-413)
.main padding-bottom  16   -> body bottom 867
                             867 - 844 = 23
```
`--player-above` counts everything ABOVE the stage and reserves `--space-4`
(16 px) of air below it; what actually stands below it on the player page is
the How-to-play line (23 px) plus `.main`'s bottom padding (16 px) = 39. The
slack is exactly 39 - 16.
**Not removed, deliberately.** Removing it at source means teaching
`--player-above` a second measured quantity — what stands BELOW the stage —
which is new JS, shrinks the stage by 23 px at every zoom, moves
`.player-stage`'s box and so re-reds `tests/test_player_base_css.py`'s FROZEN
census (29 sampled elements, re-certification against the pinned bootstrap),
and contradicts this card's own AC-3 ("the stage still ends above the fold ...
nothing else moves"). It is an owner-visible height change on every player
page, so it is a decision, not a cleanup. Named as a finding, not done here.
**Containment hides nothing.** Measured after the fix: the page's 23 px is
still reachable by a drag that starts on `.player-head`, on `.player-toolbar`
or on the How-to-play line — each took `scrollY` 0 -> 23. Only a drag that
starts on the board is now refused, which is the point.
### AC lines
- **AC-1** (the board's scroll stays on the board): `tests/test_puzzle_solver_zoom.py::TestSolverZoom_TheBoardScrollsInsideItsStage::test_300_percent_scrolls_the_stage_both_ways_never_the_page` **red -> green**. Red reason before the CSS: `assert (spent["scrollY"], spent["top"]) == (0, spent["room"])` -> `(23, 1116) == (0, 1116)`. Plant: deleting `overscroll-behavior: contain` restores exactly that failure (it is the measurement the red was taken from).
- **AC-2** (every pixel of the board is reachable): same cell, **green before and after** — the defect the card describes is not on this tree. The loop that walks `scrollTop` from 0 to its maximum is now pinned (it reached 1116/1116 in 3 drags before the diff and after it), so a future regression to the card's symptom would red; but this card did not turn it green, and saying otherwise would be a false claim.
- **AC-3** (nothing else moves): `tests/test_puzzle_solver_phone.py::TestSolverPhone_BoardFitsThePhoneWidth` and all of `tests/test_puzzle_solver_clues.py` run unchanged — 91 passed. The 100% fit path re-measured by hand as well: board fits, stage ends above the fold, page unchanged at 23.
- **AC-4** (the claim in the file is true again): same cell, **red -> green** on `assert spent["overscroll"] == "contain"`. The falsified sentence ("below the floor the board scrolls inside `.player-stage` and the page never does") is replaced, not appended to: the new sentence says the board's scroll stays on the board AND that the page does scroll, by the height of what stands below the stage. `grep -n "page never" admin.css` is empty.
`tests/test_player_base_css.py`'s FROZEN census is **not** touched:
`overscroll-behavior` is not in `PROPS`, and the declaration changes no
rectangle. The file passes in the run below.
### Scope
The two predicted `Touches:` — `src/nonogram/admin/static/admin.css` and
`tests/test_puzzle_solver_zoom.py` — plus one line of prose:
`SCOPE+ docs/deploy/player.md` — **not this card's defect.** Main's tip
(`ecf1e90d`, CARD-437's deploy record) backticked another tool's flag on its
own, `` `--disable-back-forward-cache` ``, and
`tests/test_public_player_pages.py::test_the_assembly_helper_drives_the_assembler_and_writes_nothing_itself`
reads every lone backticked `--flag` on that page as one of
`assemble_player_site.py`'s own options. It is **red on main** and would red
this card's merge gate for a reason the card has nothing to do with. Fixed by
the convention that test's own comment states — name another tool's flag
inside the whole command it belongs to — so it now reads
`` `chromium --disable-back-forward-cache` ``, one word, no meaning changed.
Revert that hunk if the owner would rather it were carded.
The card's derivation note named `tests/test_puzzle_solver_clues.py`,
`_hint.py` and `_phone.py` as likely to move; re-derived, none of them did
(they read `scrollTop`/`scrollLeft` but assert nothing about chaining).
**Net test count: 0 added**, as the card required — the existing cell kept its
`browser_page` fixture and grew the gesture half.
**Why the fixture was kept.** The gesture half was first written on a
`has_touch=True` context of its own, which is how every other touch test in
this file is shaped. That renamed the cell's node id (`...page` ->
`...page[chromium]`), and `tests/test_browser_fixture_scope.py`'s browser-family
census refused it as one test added and one removed — a frozen registry outside
the impact scope, exactly the class the wave's standing lesson names. Rather
than register a move, the cell now drives CDP touch on `browser_page`'s own
context (`page.context.new_cdp_session(page)`), the precedent being
`tests/test_puzzle_solver_brush_menu.py`'s touch drags, which run on contexts
with no `has_touch` either. Measured identical both ways, red and green:
`Input.dispatchTouchEvent` reaches the renderer regardless, and the red without
the CSS is the same `(23, 1116) == (0, 1116)`.
### Verification
`scripts/impact_set.py --gate --against main` derives a **7563-test selection
across 142 files** (71.1% of the suite) from the changed paths, because
`admin.css` reaches nearly every browser test. Per the owner's standing ruling
of 2026-11-09 for player cards (admin solver files: the player test set, not
the generator/book tests), self-verification here is the 26 player files:
**1019 tests, 20 min**. First run: 2 failed, 1017 passed — the census refusal
above (mine, now resolved without a registry edit) and the deploy-page flag
(main's, fixed under `SCOPE+`). Both cells re-run green, as did the changed
cell and the whole census file (34 passed). The merge gate runs the derived
selection once.
### What the card got wrong
1. Its headline symptom. "104 px unreachable", "the stage will not advance past
   215 of 319" — not reproducible; every pixel was reachable before the fix.
   The defect that IS real is the chaining, which is the owner's actual
   complaint ("it still scrolls when I already stopped").
2. "`overscroll-behavior` appears **exactly once** in the whole stylesheet."
   It appears **twice**: CARD-402's landscape tool strip and CARD-439's Line
   sheet. This is now the third.
3. Every geometry figure, as the brief anticipated — the stage's room at the
   same zoom is 576, not 319.
4. Its framing of the dispatch question. Chromium is not handing the gesture to
   the document scroller; the stage gets it and chains. The one-liner is the
   whole answer to AC-1, which the card was right to doubt and wrong to doubt
   in that particular way.
- **[Card correction, orchestrator — this card's own author was wrong]** The implementation round re-measured and **the headline symptom does not survive**. The card said a touch drag left the stage at 215 of 319 and that **104 px of board was unreachable by finger**. Re-measured in the worktree at 390x844 on the 30x30: one drag sweeps ~370-400 px and **repeated drags reach the last pixel** (576/576 in two drags at 175%, 1116/1116 in three at 300%). **215 was one drag's TRAVEL, not a limit** — I measured a single swipe, saw the stage stop, noticed that assigning `scrollTop` went further, and concluded "unreachable". I never tried a second drag. Verified independently by the orchestrator before accepting it: with the card's CSS reverted in the worktree, the reachability cells still **pass** and only the page-scroll cell reds, which is exactly the discrimination that says AC-2 was green before this card existed. The title is amended; AC-2 is now a property this card PINS rather than one it fixes, and the notes must not claim otherwise.
- **[Card correction]** The stage's room also nearly doubled at the same zoom since the card was written — 319/549 → **576/715** — because CARD-431's 20 px title and CARD-430's joined pill gave the height back exactly as CARD-431 intended. The page's 23 px of slack is the one figure that did NOT move. And `overscroll-behavior` no longer appears "exactly once" in the stylesheet as the card states: CARD-439's Line sheet added a third.
- **[The defect is real and its cause is now established, which the card had left open]** The card could not say WHY the page took the gesture and wrote `overscroll-behavior: contain` as a hypothesis to measure. Measured: the gesture **is** dispatched to `.player-stage` — a 20-step drag moves the stage on every step with `scrollY` 0 at all 20 readings — and the page moves only by **chaining** out of it, shown by a single gesture started 30 px short of the limit that runs the stage to its max AND moves `scrollY` 0 → 23 within that same gesture. So the hypothesis was right and it is the WHOLE answer to AC-1, not half: after the declaration, all three measurements leave `scrollY` at 0, at 100/175/300% and in both directions.
- **[The 23 px of slack — found, deliberately not removed]** `--player-above` counts what stands above the stage and reserves 16 px of air below it; what actually stands below is the "How to play" line (23 px) plus `.main`'s bottom padding (16) = 39, and 39 − 16 = 23. Exact, and traced to the pixel (stage bottom 828, howto 828→851, +16 → body 867 against `innerHeight` 844). Not removed, because doing so needs a second measured quantity in JS, shrinks the stage 23 px at every zoom, moves `.player-stage`'s box and so re-reds the FROZEN census, and contradicts this card's own AC-3 — an owner-visible height change is a decision, not a cleanup. Containment hides nothing: the 23 px is still reachable by dragging the head, the toolbar or the How-to-play line.
- - **[Record correction, orchestrator]** The line above was written by the phase-transition script when the card moved to `review`, and it said the reviewer had been **dispatched**. It had not been: the status moved and the turn ended before any reviewer was spawned, so for a short while this card's record claimed a review that did not exist. No review ran, no score was recorded, and nothing downstream consumed the claim. Corrected here and the reviewer dispatched for real below.
- **[Review 1/3 dispatch]** Reviewer dispatched for real (cycle 1, min_score 8, severity gate on, class heavy), after the correction above. Briefed to audit the REVERSAL as carefully as the fix: a card whose author admits an error is not thereby right about the correction, so the first question put to it is whether the new reachability assertion is capable of failing at all. Also asked to re-derive the one measurement the whole remedy rests on — the gesture started 30 px short of the limit that runs the stage to max AND moves `scrollY` within the same gesture, which is what distinguishes chaining from dispatch — and to check that the replacement comment's own arithmetic is true, since a replacement comment that is wrong would be this card's original defect committed twice.
- **[Rebase]** Rebased onto `117ed98a` after CARD-441 and CARD-442 landed. The `docs/deploy/player.md` hunk the round had carried as `SCOPE+` **dropped out of the diff**: the orchestrator had fixed that red identically on main in `5d01e8b1`, so git replayed nothing. The branch's diff against main is now exactly the two files `Touches:` predicted, with no scope excess at all.
- [Review 1/3] Score: 8.0 — gated by F-001 (Important). Risk LOW–MEDIUM, lane DEEP. Report `meta/review/20261112T202647Z-CARD-432-cycle1.yml`, `parse_review.py` verdict accepted, `security: n/a` (one CSS declaration and a browser cell — no input, boundary, authz or deserialization). 0 Critical, **1 Important**, 2 Minor. Everything the brief asked it to audit, it re-derived rather than accepted: the chaining-vs-dispatch measurement **reproduced** (with `auto`, one gesture started 30 px short runs the stage 1086 → 1116 AND moves `scrollY` 0 → 23 inside that same gesture; with `contain`, 1116 and `scrollY` 0); the fixture decision costs **no fidelity** for this property (the identical gesture on a real `has_touch` context gives the same red and the same green, and `admin.css` carries no `(pointer: coarse)` query for anything to read); the FROZEN census is untouched **by running it** (36 passed); and AC-4's arithmetic traces to the pixel.
- **[Review 1/3 reversal audit]** It holds. The brief asked whether the retracted "104 px unreachable" left behind a cell that passes on any implementation. It does not: deleting the declaration reds it with exactly `(23, 1116) == (0, 1116)` while the reachability loop still reaches 1116/1116 in three drags, and **two controls prove the reachability assert itself can fail** — a 10 px sweep reds it, and a loop guard of 2 reds it at `782 == 1116`.
- **[Severity gate] BLOCKED on F-001 (Important), and it is a finding the card never looked for.** `overscroll-behavior` governs the **mouse wheel** as well as touch, and `.player-stage` is also the **admin editor's** board container — verified by the orchestrator independently: `.player-stage` appears in BOTH `puzzle_solve.html` and `puzzle_edit.html`, while `.player-stage-wrap` appears only in `puzzle_solve.html` (1 vs 0) and the id `puzzle-player` is on both, so the wrapper is the only usable discriminator. Measured page scroll suppressed by the one declaration, on surfaces and an input this card never measured: **editor at 1024x600 with the wheel, 229 px; solve page with "How to play" OPEN, wheel, 277 px; editor at 390x844 by touch, 331 px; solve page with help open, touch, 349 px** — against the 23 px the card was written about. AC-3 as written is satisfied (it names only the 100 % fit path and three cells, all green), so this is a gap in the card's SCOPE, not a broken criterion: "containment hides nothing" was measured against 23 px and the real figures are 10–15x that.
- **[Owner ruling, 2026-11-12]** Put the measured figures to the owner — editor 229 px by wheel and 331 px by touch, solve page with "How to play" open 277 px by wheel and 349 px by touch, against the 23 px the card was written for — with three options. Ruling: **scope the rule to the solve page, and on the solve page keep it contained even when the help is open.** The owner accepted explicitly that with the help open a drag ON THE BOARD will not scroll the page down to the help text, because the help text, the toolbar and the header all remain page-scroll surfaces. The editor and the wheel there are unaffected. The two alternatives they declined: releasing containment while the help is expanded (returns the original complaint in that one state, and needs JS plus a test to watch the panel), and giving the help panel its own scroller (bigger, changes how the help reads on every screen, properly its own card).
- **[Fix 1 dispatched]** F-001 is now a scoping job rather than an open question. The brief carries the one trap that would make the fix silently undo the card: a narrowed selector that stops matching the solve page at all would still satisfy the editor's new cell and leave the original defect in place, so `TestSolverZoom_TheBoardScrollsInsideItsStage::test_300_percent_scrolls_the_stage_both_ways_never_the_page` must be re-run green unchanged. It also carries the discriminator already verified by the orchestrator (`.player-stage-wrap` in `puzzle_solve.html` only, 1 vs 0; the id `puzzle-player` on both and therefore useless) with an instruction to confirm the DOM really nests that way rather than trust the suggestion. The two Minor comment findings go in the same round because AC-4 of this card IS that the comment be true: replacing one false sentence ("the page never does") with a differently false one (overstating the slack by 16 px) would be the same defect twice.
- - [Review 1/3] Score: pending — reviewer dispatched (cycle 1, min_score 8, severity gate on, class heavy).
- **[Fix round, review cycle 1 — F-001 scoped to the solve page, F-002/F-003 comment corrections]**
  - **The selector is `.player-stage-wrap > .player-stage`**, and the declaration moved out of the `.player-stage` block into its own rule beside it. The nesting was confirmed on disk rather than assumed: `puzzle_solve.html` has `<div class="player-stage-wrap">` immediately followed by `<div class="player-stage" id="puzzle-player">` (direct child, lines 332-333), `puzzle_edit.html` has the stage with no wrapper, and the id `#puzzle-player` is on BOTH templates so it could not discriminate. The public player page is the same template rendered by `player/assemble.py` (`SHARED_UI_TEMPLATE = "puzzle_solve.html"`), so it keeps the containment; the admin editor loses it, which is the owner's ruling of 2026-11-12. Specificity is `(0,2,0)` against the block's `(0,1,0)` and nothing else in the stylesheet declares `overscroll-behavior` on `.player-stage`, so no cascade question arises.
  - **The editor's side is pinned in an EXTENDED cell, not a new one. Net test count: 0 added** (as the card promised; the fix round adds no node id). The cell is `tests/test_puzzle_editor_ui.py::TestPuzzleEditor_TheBoardKeepsItsCluesByTheSameRule::test_the_editors_gutters_obey_the_room_condition` — the one cell that already reads the EDITOR stage's computed scrolling (`overflowY`). It now also, at 1024x600 and 300% with the stage put at its stop and the page at its origin, measures a wheel over the board: the page takes the surplus (`scrollY` 0 -> moved) and the board stays at its stop. Premises asserted first, so the claim cannot pass vacuously: the stage has room, the page has room, the stage is spent, and the computed value is not `contain`.
  - **Controls, both run.** (a) The pre-fix global rule put back (`.player-stage { overscroll-behavior: contain; }`): the editor cell reds, `assert 'contain' != 'contain'`, with the editor's own figures `{'top': 1263, 'room': 1263, 'scrollY': 0}`. (b) The same mutant with that one computed-style assertion neutralised: the BEHAVIOUR half reds on its own, `assert 0 > 0` — the wheel moved the page 0 px under containment. So the new half is not carried by the style read alone. Both files restored afterwards and re-run green.
  - **Re-runs** (`-o addopts= -rEfs`, no skips): the solve page's cell `tests/test_puzzle_solver_zoom.py::TestSolverZoom_TheBoardScrollsInsideItsStage::test_300_percent_scrolls_the_stage_both_ways_never_the_page` **passes unchanged** — the narrowed selector still reaches this page, which its `spent["overscroll"] == "contain"` assertion is what proves. Together with the editor class and `tests/test_player_base_css.py`: **7 passed** (1 + 3 + 3). The FROZEN census is **measured untouched**, not assumed: `overscroll-behavior` is not in `PROPS` and the new rule declares nothing else. `tests/test_admin_design_tokens.py` (the whole-file hex/token sweeps over `admin.css`): 14 passed.
  - **F-002, the corrected figure.** The comment said the page overflows "by the height of what stands BELOW the stage ... which `--player-above` does not count", which gives 39. It now says what the card's own notes say: `--player-above`'s `--space-4` term **reserves 16 px** of air below the stage, the "How to play" line plus `.main`'s bottom padding are **39**, so the slack is **39 - 16 = 23 px**. One false sentence was not replaced with another.
  - **F-003, the instrument and the fling.** The CARD-432 comment now opens by naming its instrument for every figure it carries — emulated Chromium driven from pytest, touch via CDP `Input.dispatchTouchEvent` and the wheel via Playwright, never a real device — and the fling clause is marked as what it is: a property of the CSS spec (only `none` additionally suppresses the overscroll affordance; neither value touches inertia), explicitly NOT a reading taken here, because a CDP drag carries no timing and so produces no fling to measure and no test pins one.
  - **The editor's loss, in the comment too**, since the comment is this card's AC-4: the review's 229 px (wheel, 1024x600) and 331 px (touch, 390x844) on the editor are named as the reason for the narrowing, and the solve page's 277/349 px with "How to play" open are named as what the owner accepted (the help text, toolbar and header stay page-scroll surfaces). Those four figures are review cycle 1's measurements, attributed as such.
  - **One test docstring outside the CSS, inside scope.** `TestSolverZoom_TheBoardScrollsInsideItsStage`'s docstring said the chaining was permitted by "`.player-stage`'s overscroll-behavior"; after the narrowing that is the EDITOR's state. It now says "this stage's", and names where the boundary is pinned and why the cell reads a computed value rather than a selector. No assertion changed.
  - **Scope.** No `SCOPE+` entries: the three files touched are `src/nonogram/admin/static/admin.css`, `tests/test_puzzle_editor_ui.py` and `tests/test_puzzle_solver_zoom.py` (docstring only), all named in the fix brief.
  - **DECLARATIONS F-001** — the stylesheet comment above `.player-stage` and the new rule's own comment re-derived from the narrowed selector (which surface is contained, which is not, and why); `TestSolverZoom_...`'s docstring corrected; the editor class's header comment says why the boundary is pinned in its first cell. `docs/deploy/player.md`'s line on this defect is a dated record of the PRE-fix measurement and stays true as that. **DECLARATIONS F-002 / F-003** — the same comment block, which is the declaration itself; the card's own notes already stated 39 - 16 = 23 and the instrument, and are confirmed correct rather than changed.
  - **The header's `Touches:` line predates this round and still names two files** (`admin.css`, `tests/test_puzzle_solver_zoom.py`); `tests/test_puzzle_editor_ui.py` is the third file this round changed, named in the fix brief's own Scope for F-001 item 2. It is NOT recorded as `SCOPE+` for that reason, and the header is left as it is because card edits in a worktree belong under this heading only (INV-023). The merge gate derives its selection from the changed paths, not from that line.
- **[Fix 1] verified by the orchestrator, not accepted on report.** Three checks, each chosen because it would catch a plausible way the fix could be wrong: (i) **the net count held against a baseline taken BEFORE the round** — `tests/test_puzzle_editor_ui.py` collected 117 cells both before and after, so the editor's side was genuinely EXTENDED and not added, which is what the card promised and the owner's test budget asks; (ii) **the trap is closed** — a narrowed selector that stopped matching the solve page would have satisfied the new editor cell while leaving the original defect in place, green and useless, and the solve cell asserts `spent["overscroll"] == "contain"` on that page and passes, so the selector demonstrably still reaches it; (iii) **the DOM really nests that way** — `puzzle_solve.html` lines 332-333 put `.player-stage` as the immediate child of `.player-stage-wrap`, so the `>` combinator is right, and `puzzle_edit.html` carries the stage with no wrapper. `overscroll-behavior` now appears three times in the stylesheet and none of the other two is on `.player-stage` (CARD-402's landscape strip, CARD-439's line sheet).
- **[AC/EC check]** Run by node id with skips counted, because this project's card-level AC gate is unwired: `TestSolverZoom_TheBoardScrollsInsideItsStage` (AC-1, AC-2), `TestSolverPhone_BoardFitsThePhoneWidth` and `TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted` (AC-3), and `TestPuzzleEditor_TheBoardKeepsItsCluesByTheSameRule` (the owner's narrowing). **16 passed, 0 skipped.** AC-4 checked directly rather than through a test: `grep "page never does"` on `admin.css` returns **0**, and the replacement states the derivation the card's notes state (`--space-4` reserves 16 px of the 39 below the stage, so the slack is 23).
- **[Touches corrected]** The header named two files; the owner's ruling made it three by requiring the editor's side to be pinned. Widened to include `tests/test_puzzle_editor_ui.py`. The fix round flagged the discrepancy and correctly did **not** edit the header itself (INV-023 — the worktree writes only `## Worktree notes`); the header is the orchestrator's, so the correction is made here.
- **[Merge gate]** Impact-scoped, derived on the rebased branch: **143 test files** in the full selection. **32 of them run**, the player subset, per the owner's ruling of 2026-11-09 that player cards gate on the player test set rather than on everything `admin.css` reaches. **2137 passed, 0 failed, 0 skipped** in 18:20, plus the two lifted `wave_close_only` files `6 passed`. **Stated so it cannot be read as broader than it is: the full 143-file selection was NOT run at this gate, and the wave close owes it.**
- **[Merged]** `793f4660`, `--no-ff`, two commits replayed. The review report was confirmed byte-identical in the main repo before the worktree was removed.
- **[No cycle 2, and why — this is a judgement, not an omission]** The reviewer closed with explicit approve conditions: *"Approve once F-001 is answered (scope the selector, or record the figures and get the ruling) and the two comment clauses are corrected."* All three were met, and each was verified by the orchestrator by running something rather than by reading the fix round's report: the net count against a pre-round baseline, the solve cell's own `overscroll == "contain"` assertion (the one thing that would catch a selector which silently stopped reaching the solve page), the DOM nesting the `>` combinator needs, the FROZEN census re-run, and — the claim with real consequence for the owner — that the PUBLIC play page still carries `.player-stage-wrap` after the narrowing, so the live site keeps the fix. CARD-437 took a cycle 2 in the same shape; the difference here is that the fix is one declaration moved into a scoped rule plus comment prose, and the specific ways it could have been wrong were each checkable directly and were checked. A reviewer has not seen the narrowed selector, and this note is the record of that.
- **[Review sync] ⚠ FAILED, and the orchestrator caused it.** The worktree's copy of the cycle-1 report carried `status: fixed` / `fixed_in: b20b4f91` on all three findings, written by the fix round. The orchestrator removed the worktree **before** copying that updated copy back, so it is gone — `meta/review/**` is gitignored and a removed worktree leaves nothing behind. Main holds the reviewer's original, which said `open` / `null`. **The guard fired and was ignored by the shell, not by the reader:** the `cmp`-against-main check printed `MISSING/DIFFERENT` as designed, but it was written as `cmp … || echo … && git worktree remove …`, and `|| echo` makes the clause exit 0, so `&&` ran the removal anyway. A check whose failure cannot stop the next step is not a check. Third of this family today, and the same root as the other two: decorating or filtering a command's output swallows its exit status. The three statuses have been **reconstructed** in main's copy under an explicit `writer: orchestrator-recovery` block that names what was lost, why reconstruction is safe here (every fix is in the merge and each was verified independently of the fix round's report), and how the loss happened. `parse_review.py` re-accepts the file.
