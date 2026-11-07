# CARD-413: 'How to play' — the usage text becomes one collapsible line that opens to the owner's six tools

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- The text and a disclosure widget are small; the cost is reconciling the CARD-386 F-2 usage-paragraph hook in the assembler and the tests that read the old paragraph's words, which is why it comes last. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner player findings 2026-11-07, item 9: "The text below the puzzle: a single line, 'How to play ▸', that opens to this (approximately): Tap ... Brush ... Region ... Hint ... Probe ... Zoom: - / + or Fit."
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-406, CARD-409, CARD-411
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, player/assemble.py, tests/test_puzzle_solver_page.py, tests/test_puzzle_solver_brush_menu.py, tests/test_player_shared_ui_site.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. Depends on 406 (the text names Fit), 409 (where hint answers appear) and 411 (the probe button names) because the sentences must be true when it lands. It also edits `player/assemble.py` and `tests/test_player_shared_ui_site.py`, which CARD-394 edits: serialize with it, no dependency. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Today the usage text is a long paragraph (`#puzzle-player-hint`, class `.player-hint`, shown by solver.js once the board is drawn) with the Check clause and 'beside the puzzle's title' in it; the public page edits its tail at assembly time (`SHARED_UI_HINT_CLAUSE` / `SHARED_UI_HINT_REPLACEMENT`, CARD-386 F-2, owner ruling 2026-11-07: 'in the line at the top of the page'). The owner's replacement is a collapsed single line 'How to play ▸' that opens to six bullets (Tap, Brush, Region, Hint, Probe, Zoom). It does not mention Check (admin only) or the explain line.

Reconciling the F-2 ruling: the ruling's purpose was that the public page must not say something false (Check; 'beside the title'). With the owner's text there is no Check and no location sentence, so the replacement hook has nothing to replace: it is DELETED, together with its refusal and its tests, and a new assertion holds the purpose instead (the assembled public page's text is true: it names no control the page lacks). CARD-409 already changed the location sentence; this card deletes the whole paragraph.

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

## What to implement

1. **A disclosure** (`<details><summary>How to play</summary>` or an equivalent button with `aria-expanded`; the `▸` rotates when open), collapsed by default, one line when closed, shown only once the board is drawn like today's paragraph. The open state is a per-viewer convenience (remembered in localStorage is allowed; not required) and is never part of the saved game.
2. **The six bullets,** in the owner's words, edited only where a control has changed name or behaviour by the time this card runs: 'Zoom: - / + or Fit', 'Probe: ... press Wrong guess to undo it all' (the owner's words say 'Contradiction'; Q14 decides), Hint's 'press up to three times' ladder as the owner wrote it.
3. **Admin-only Check** (owner Q16): the owner's text omits Check. Recommended: one admin-only sentence in the admin page's open text, hidden in public mode by the same mechanism as the Check button (public mode removes the element), not by an assembly-time text edit.
4. **Retire the F-2 hook** in `player/assemble.py` (`SHARED_UI_HINT_CLAUSE`, `SHARED_UI_HINT_REPLACEMENT`) and the cells that pin it; the replaced text assertion becomes 'the assembled page names no control the page lacks'.
5. **Docs:** the template header paragraph about the usage text and the how-it-works player page.

## Acceptance criteria

* **AC-1** (collapsed by default): after the board draws the page shows exactly one visible line 'How to play' with a closed disclosure, at 390 x 844, 844 x 390 and 1280 x 720; the old paragraph is gone. (test: new browser cells; plant: leave it open)
* **AC-2** (opens, keyboard and touch): Enter/Space/tap opens it, `aria-expanded` follows, the six bullets are readable, nothing under the stage moves the board (the text is below the stage). (test: new cells)
* **AC-3** (every sentence is true): each control the text names exists on the page at that moment and the text names no control the page lacks, on the admin page and on the public-mode page. (test: new cell that extracts bold control names from the text and resolves them against the page; plant: name Check on the public page)
* **AC-4** (the hook is retired cleanly): `SHARED_UI_HINT_CLAUSE` and its replacement no longer exist, the assembler's refusal for it is gone, and the assembler still refuses a fragment lacking a hook it still uses. (test: `tests/test_player_shared_ui_site.py` re-pointed; the retired claim is named with the finding)
* **AC-5** (no other text moves): the page's other copy and the byte-identity table are unchanged. (test: `TestSharedUi_ByteIdentity` unchanged)
* **AC-6** (not saved): the open/closed state is not in `serializeState`. (test: new cell)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).

* **G-T** No test is deleted, renamed, skipped or weakened to fit. A test is changed ONLY if its claim is a CHANGED owner decision named in this card's Source: the old claim is retired in the test's docstring with the decision's date and the new claim is asserted in the same cell (a number is re-measured, not relaxed). The owner's rule applies: a test is kept only if its claim is a live decision. Node-id set difference against the merge-base is shown in Worktree notes, and every new cell has a plant that makes it red (an edge mutant, not only a happy path).

## System contract

* ADR-0041/R3 — the public player runs byte-identical copies of the admin files (check: `TestSharedUi_ByteIdentity`, unchanged table)
* ADR-0041/R2 — no solution in any public asset (check: `TestSharedUi_TheServedTreeCarriesNoAnswer`, unchanged)
* ADR-0038/R3, R4 — pure rules live in `solver_state.js`, clues come from the payload (check: the pure cells named in the ACs)


## Architecture context

FR-044 (the admin puzzle player, TERM-037) and FR-045 (public player, COMP-011) — the public player gets this behaviour by the shared-UI mode, not by its own code. The author reads the AC ids in `requirements.yml` FR-044 and amends exactly the ones whose claim changes (do not guess ids; AC-345..AC-347 are the circling ACs).

## How this reaches the public player

One source of truth (owner direction 2026-11-07; ADR-0041/R3): the change is made ONLY in the admin files (`src/nonogram/admin/static/solver.js`, `solver_state.js`, `admin.css`, `tokens.css` and the admin templates). Nothing in `player/play.js`, `player/player.css` or `player/play.html` is edited or tested by this card: CARD-399 retires them, and production serves `play.js` until the owner deploys the shared-UI mode, so this card reaches production only through the shared-UI rebuild and that deploy (the owner's timing; CARD-394 and CARD-399 are NOT dependencies of this card). What the card owes the public side:

* the shared-UI tree assembled from the changed files passes `tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity` with no edit to the table it holds (the copies stay byte-identical; no override layer, no public-only rule);
* the behaviour is verified ONCE, on the admin page (owner test-budget ruling, 2026-11-07): no duplicate public-mode cell is added; a public-mode cell exists only where the behaviour differs in public mode (for example Check and the error counter do not exist there); CARD-385's existing public-mode sweep and the byte-identity test cover the copy;
* the served-tree scan (`TestSharedUi_TheServedTreeCarriesNoAnswer`) still passes: a feature that needs the answer is not allowed to read it in public mode (ADR-0041/R2).

## Viewports the card must verify

Measured in a browser, not asserted from CSS, and recorded in Worktree notes with the numbers: **390 x 844** (phone portrait), **844 x 390** (phone landscape), **1280 x 720** and **1440 x 900** (desktop), each on a 15 x 15 board and on the owner's 30 x 29 class of board (use a 30 x 30 stored grid; the exact puzzle 1750b436-... is in the production database, which is off limits to this work). For each: no horizontal page scroll, no control clipped, the board does not move when the thing the card changes appears or disappears, and the card's own claim.

## Worktree notes

(none yet)
