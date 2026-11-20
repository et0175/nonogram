# CARD-506: Player and admin-CSS minors: two local values to tokens, Redo's aria-disabled, the ? centring, the Reset Escape path, stale comments, a scale-1 render

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/506-player-css-minors
**Worktree:** ../PythonProject4-card-506
**Source:** roadmap wave 6 (cut 2026-11-20 on the owner's "please start the next wave"). IDEA-053, 060, 095, 147, 151, 157, 161, 166 (WSJF 2.31 each, about 0.125 d each). Several are marked unverified in the backlog: the player was reworked through the November cards, so expect some to be closed already.
**Idea:** IDEA-053, IDEA-060, IDEA-095, IDEA-147, IDEA-151, IDEA-157, IDEA-161, IDEA-166
**Wave:** 85
**Created wave:** 85
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_*.py, tests/test_admin_design_tokens.py
**UI surface:** puzzle player (admin, and the public player built from the same files), guide strip
**Review score:** —
**Started:** 2026-11-20T17:17Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-053 (CARD-160 F-004).** The player's cell bounds (`--player-cell-min: 14px`, `--player-cell-max: 28px`) and the thin-rule colour-mix are local custom properties in admin.css; promote to tokens.css. Re-read 2026-11-20: still local.
2. **IDEA-095 (CARD-169 F-002).** The guide strip's `--strip-cell: 1.5rem` is local in admin.css; promote to a token or record it as a deliberate local value. Still local 2026-11-20.
3. **IDEA-060 (CARD-163).** puzzle_solve.html's header comment "Its text is announced…" no longer clearly refers to the banner; the redo-noop test does not assert Redo is aria-disabled before the click.
4. **IDEA-147 (CARD-188 F-008).** No render at device scale 1 for the 14 px floor.
5. **IDEA-151 (CARD-186).** The "?" glyph's centring is untested (only containment); a solved name of about 40+ characters moves the board about 13 px at desktop widths.
6. **IDEA-157 (CARD-189).** Only Reset's "Keep marks" cancel path is tested for ending a repeat run (Escape untested); the solver.js / puzzle_solve.html summaries omit the "first click on a cell already in the brush's state moves on" rule.
7. **IDEA-161 (CARD-187).** A template comment's rationale covers focus only, not WCAG 1.3.2; an admin.css comment cites a test that does not assert it.
8. **IDEA-166 (CARD-196).** Four stale comments: two-digit column clearance in admin.css, a row-gutter class comment in test_puzzle_solver_phone.py, a docstring overclaiming OWNER_ROW, a mixed digit-count row pair comment.

## What to implement

Re-verify each against main first, in a browser run where the item is behavioural (5, 6, 4); drop any already closed with one line. Move values to tokens with no computed-style change (measure before/after). Fix the board shift in 5 only if it is still there and the fix is CSS-local; otherwise record it. Fold every new assertion into an existing test.

## Acceptance criteria

* **AC-1**: each item fixed, or dropped/recorded with its evidence.
* **AC-2**: the token moves change no computed value (a before/after measurement of the player and the guide strip at 390 and 1440 px); the design-token census test stays green.
* **AC-3**: each new assertion has a control that reds it.
* **AC-4**: net test count 0; report it.

## Guardrails

* **G-1**: the player files are the public player's source: the public player test set (tests/test_player_*.py, test_public_*.py where present) runs green; the orchestrator publishes after merge only on the owner's say.
* **G-2**: no visual change the owner would see, except removing the board shift in item 5.

## Worktree notes
- [Built] 2026-11-20. Each item re-verified on this branch's base first; browser measurements by throwaway Playwright probes using the suite's own fixtures (`live`, `_open`, `_glyph_box`, `_solve_and_measure`), kept out of the repo.
- IDEA-053 / IDEA-095 (tokens): `--player-cell-min: 14px`, `--player-cell-max: 28px`, `--player-thin` (28% ink on paper) and `--strip-cell: 1.5rem` moved from admin.css (`.player-stage`, `.guide-strip`) to `:root` in meta/design/tokens.css, mirrored byte-identically to static/tokens.css. Names kept, so the per-width overrides on `.player-stage` (the 0px floor at <= 820px, the 36px caps) still apply. meta/design/components.md's two "candidate token" lines updated; player/player.css's CARD-445 comment now names tokens.css for `--player-thin`.
- AC-2 measurement: every computed property (all standard properties plus the moved and dependent custom properties) of every element under `.player-toolbar`/`.player-stage-wrap`, with its `::before`/`::after`, and its bounding box — 15x15 and 30x30 boards with filled/empty/maybe/unknown cells at 390x844, 1440x900 and 1100x700 — and of every `.guide-strip` element on /book/<id>/finalize at 390x844 and 1440x900; before vs after the move. 11,180,302 values compared: 0 standard-property, pseudo-element or box differences; 0 values that were set changed. The only differences are the four moved custom properties now inherited from `:root` on elements outside their old declaring scope (empty -> the same value; 25,692 entries), which no rule there reads.
- Census: tests/test_admin_design_tokens.py (mirror test included) green. The how-to page's equality test (test_how_to_solve_page.py test_the_lesson_uses_tokens_and_the_players_probe_colours) read `--player-thin` from admin.css only; it now reads tokens.css + admin.css. No census counts tokens exactly (test_public_player_pages.py's is a `>= 40` floor; the how-to test unions the sets).
- IDEA-060: the template's "Its text is announced" now names the solved banner, and "the confirmation under it" says it is the element right after Reset. test_a_board_change_while_asking_closes_the_confirmation[redo-key-noop|redo-button-noop] now asserts Redo is aria-disabled BEFORE the press.
- IDEA-147: still open on base (no scale-1 render existed). The 14 px floor only binds on a board with single-digit columns (the suite's 30x30 BIG binds the 14.39 px numeral floor instead); measured on a 30x30 with single-digit columns at 1100x700: cell 14.0 px at DPR 1 and 2, 1px thin rules, the board scrolls vertically inside the stage. Renders (DPR 1 and 2, page and stage crop) in ~/Documents/nonogram-reviews/CARD-506/; looked at the DPR-1 crop: rules and every clue numeral legible (row clue "1 22 2" checked against the computed clue (1, 22, 2)). No test added (a render is the item).
- IDEA-151 centring: measured "?" glyph-box centre vs cell centre: |dx| <= 0.66 px, |dy| <= 1.70 px over 30x30@390, 15x15@1440 and 30x30@1100x700 at DPR 1 and 2. Folded into TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell::test_glyph: centre within 2 px on both axes.
- IDEA-151 board shift: STILL THERE and larger than the backlog says. Measured (15x15, solving click, board y after minus before): names of 10-12 characters move nothing; 14-24 characters move the board +12.8 px at 960/1024/1200/1440/1480 (0 at 1280); a 26-character name +37.6 px; 50-60 +62.4; 100 +136.8; 390 px 0 at every length (the compact rule clamps the banner to two lines). Cause: the banner shares the 13rem tools' box and wraps from about 14 characters. NOT FIXED: every CSS-local fix changes something the owner sees beyond removing the shift (clamp/ellipsis hides part of the name; a smaller desktop banner font changes the banner; reserving a second line moves the board before solve; a wider tools' box changes the toolbar). Owner decision — the compact rule's two-line `--text-xs` clamp on desktop is the smallest candidate.
- IDEA-157: Escape path added as one more entry of test_anything_between_two_clicks_makes_the_next_a_first_click's `between` dict (row 13, column 10). The click-rule summaries in solver.js (MARKING "pointer") and puzzle_solve.html now include "a first click on a cell already holding the brush's state moves one step on (Clear always clears)", which is solver_state.js clickedState's rule.
- IDEA-161: puzzle_solve.html's Progress paragraph now names WCAG 1.3.2 and records the owner's acceptance as its answer. admin.css's `.player-counters` comment now cites test_puzzle_solver_hint.py TestSolverHint_PlacesTheButtonAndTheCounter for Hints' right end (its test_dom_order_and_boxes asserts it); the 74.80/38.80 px heights are now called measurements, with the two asserted layouts named.
- IDEA-166: admin.css ring comment: row-number line-height is `normal`, and the 0.5 px pill clearance now excepts the two-digit column pill (F-002); the F-006 paragraph now says what the close-pairs check pins and that a single-digit/two-digit ROW pair is in no gap assertion (its fixture has no single-digit row number) (F-008). test_puzzle_solver_clues.py: "the only adjacent single-digit row ring pair" corrected and "check below" names its class (F-007); the same docstrings' "floor and desktop viewports ... under _RING_GAP" corrected to desktop only, as the test asserts since CARD-411. test_puzzle_solver_phone.py: F-003's "row gutter wider than the 358 px stage" sentence was already gone; the swipe class's "nothing pans the board on a phone" and the module docstring's "``auto`` with Region off" / "off by default" (stale since CARD-195/CARD-433) corrected.
- Controls (mutant applied, node run, file restored byte-for-byte; `git diff --stat` unchanged after): C1 Redo's aria-disabled forced "false" -> both redo-noop cases red at the new precondition (`assert False ... _is_disabled(..., 'Redo')`). C2 the review's mutant C4 (lastClick clear moved from Reset-open into Keep-marks) -> `{'reset opened and cancelled (Escape)': 'unknown'} != {...: 'filled'}`. C3h `text-align: left` on the "?" -> `assert 8.828125 <= 2`. C3v `margin-top: -6px` on the "?" -> `assert 4.703125 <= 2`. C4 tokens.css `--player-thin` at 30% -> test_the_lesson_uses_tokens_and_the_players_probe_colours red on the mix.
- Process: one of my control runs expanded a zsh `$N1[...]` subscript to no node ids and started the whole suite (pid 14887, holding the lock from 18:11:39Z); killed on the orchestrator's message. Its lock file stays (I do not delete locks); the guard's dead-pid rule (tests/full_suite_lock.py holder_alive) walks past it.
- Gate (unarmed, `-o addopts= -rfs`): tests/test_admin_design_tokens.py, test_how_to_solve_page.py, test_puzzle_solver_{clues,marking,maybe,phone,progress,page,percent,hint}.py, test_book_finalise_guide_preview.py, test_kanban_review_record.py, and the public player set test_player_*.py + test_public_*.py: 846 passed, 0 failed, 0 skipped. Net test count: 10689 collected before and after (0 net; every new assertion folded into an existing test).
