# CARD-507: A long solved-puzzle name no longer moves the desktop board: the banner text takes the compact two-line --text-xs clamp

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/507-solved-name-clamp
**Worktree:** ../PythonProject4-card-507
**Source:** roadmap wave 7 (cut 2026-11-20 on the owner's "go with option 2, start wave 7"). IDEA-218, owner decision 2026-11-20: option 2 of five (ellipsis, two-line --text-xs clamp, reserved line, wider tools box, leave it).
**Idea:** IDEA-218
**Wave:** 86
**Created wave:** 86
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_*.py
**UI surface:** puzzle player (admin, and the public player built from the same files): the solved banner at desktop widths
**Review score:** —
**Started:** 2026-11-20T21:24Z
**Blocked by:** —

## Why this card exists

Measured by CARD-506 and its review (2026-11-20): the solved banner wraps inside the 13rem tools box and pushes the board down at desktop widths. 10-12 characters 0 px; 14-24 characters +12.8 px; 26 without spaces +62.4 px; 50-60 +62.4 px; 100 +136.8 px; at 390 px wide, 0 for every length. The compact (phone) rule already sets the banner's text span to `--text-xs`, `--leading-tight`, clamped to two lines (`.player-solved > span` inside the compact media block of admin.css). The owner chose to apply that same treatment at desktop widths.

## What to implement

1. Re-measure the shift on this branch's base first (the lengths above, at 1440x900 and 1100x700, 15x15 and 30x30 boards), in a browser run.
2. Apply the compact rule's text treatment (`--text-xs`, `--leading-tight`, two-line `-webkit-line-clamp`, overflow hidden) to the banner text at every width. Prefer moving the declaration out of the media block over duplicating it. Keep the phone layout exactly as it is.
3. The full name stays in the DOM (the clamp is visual only), so the banner's accessible name and the text a screen reader announces are unchanged.

## Acceptance criteria

* **AC-1**: at 1440x900 and 1100x700, for solved names of 10, 24, 26 (no spaces), 60 and 100 characters, the board's top edge moves 0 px between the unsolved and solved states (or by no more than the box's existing short-name height, stated with its measured figure).
* **AC-2**: the banner text never shows more than two lines at any width; a long name is cut, not wrapped further.
* **AC-3**: at 390x844 every computed value of the banner and the board is unchanged against the base (a before/after measurement).
* **AC-4**: the banner's accessible text still contains the full name.
* **AC-5**: the board-shift assertion is folded into an existing solved-banner test (net test count 0, or +1 at most if no existing test can carry it; report it). Its control: remove the new rule and the test reds with the measured shift.

## Guardrails

* **G-1**: the player files are the public player's source: the public player test set (tests/test_player_*.py, tests/test_public_*.py) runs green. The orchestrator publishes after merge only on the owner's say.
* **G-2**: no other visible change. Short names (that fit on one line today) render at the new text size; state that change and its measured size in the notes, because the owner sees it.

## Worktree notes

### Implementation (2026-11-21)

**Change.** admin.css: the rule `.player-solved > span { font-size: var(--text-xs); line-height: var(--leading-tight); display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; }` moved out of the compact media block (`@media (max-width: 600px), (max-height: 500px)`) to the base rules, after `.player-solved-name`. It was moved, not copied. The compact block keeps `.player-solved { gap; padding }`. The CARD-186 comment above `.player-slot` now says the banner no longer makes the row taller, and names the new widths.

**Test (AC-5, net 0).** `TestSolverMaybe_LongNameBannerWrapsInsideTheToolsWidth::test_wraps` in tests/test_puzzle_solver_maybe.py now carries three new checks: the board's (x, y) is the same before and after the solving click; the text span is at most two lines tall (`height <= 2 * line-height + 0.5`); and the banner's textContent contains the whole name, next to the existing `inner_text == long_name`. Its viewport `(1200, 900)` became `(1100, 700)` to match AC-1, so it still has 6 cases (3 viewports x 2 names of 120 characters). The docstring no longer says a long name moves the board.

**Measurement method.** A throwaway Playwright probe under /private/tmp/claude-501/card507/ used the suite's `live`, `_open`, `_set` and `_cell` helpers. It asserted at import that `nonogram` and `tests` resolve to this worktree. A first pair of runs had imported the main checkout's editable install, so they measured main's CSS twice; those runs were thrown away. Base = HEAD's admin.css swapped into the worktree. After = this branch. Boards were 15x15 (GRID) and 30x30 (BIG), and both gave the same figures. Names: 10, 12, 14, 24, 60 and 100 characters with spaces, 26 and 120 characters with no spaces.

**Re-measured premise (step 1): board dy on solve, base.**
- 1440x900: 10 and 12 give 0; 14 gives +12.797; 24 and 26 (no spaces) give +37.594; 60 gives +87.188; 100 gives +136.781; 120 (no spaces) gives +161.578 px.
- 1100x700: 0, 0, +12.812, +37.609, +37.609, +87.203, +136.797, +161.594 px.
- 390x844: 0 for every length.
- The premise holds. Where my 24- and 60-character figures differ from the card's (+12.8, +62.4), the cause is where the words break: these are different strings.

**After (AC-1, AC-2).**
- 1440x900 and 1100x700, both boards, every name: dy 0 and dx 0.
- Text lines: names of 14 characters or fewer take 1 line, longer names 2, and no name takes more than 2.
- Sweep at height 900 (700, 800, 960, 1000, 1200, 1280, 1480 and 1920 px wide, all eight names): dy 0, at most 2 lines.

**AC-3 (390x844).** The probe saved computed values (font-size, line-height, display, overflow, -webkit-line-clamp, width, height, padding, gap, margin-top, font-weight, white-space) and the rectangle of each of these: the banner, its text span, the label, the name, the icon, the board, the tools and the solved box. Comparing base and after over 2 boards x 8 names x 9 snapshots gave 144 compared and 0 differences. Board dy is 0 in both.

**AC-4.** In the probe, the name element's textContent equals the stored name for all 48 cases (2 boards x 3 viewports x 8 names). `test_wraps` asserts the same for 120-character names at all three viewports.

**G-2: the visible change for short names (owner, please note).** At desktop widths a short name now renders smaller. Measured on a 10-character name at 1440x900 and 1100x700:
- the text: 16px / 24.8px line-height became 12.48px / 14.976px (`--text-xs` / `--leading-tight`, the phone's size);
- the text span's width: 136.23 to 106.28 px;
- the banner's width: 188.23 to 158.28 px;
- the banner's height stays 36 px and its left/top are unchanged.

The board does not move for any name. A 14-character name that used to wrap to 2 lines now fits on 1.

**Seen, not fixed (out of scope).** At 600x900 (inside the compact block, portrait) the board moves on solve by dy +27.203 px and dx +12.656 px for every name length, the 10-character one included (dx added in fix round 1, review F-004; re-measured in base2/after2). Base and after are identical, so this card did not cause it and does not change it. It is recorded here only. It is not the banner text: a 1-line name moves it too.

**Controls.**
1. With the new rule deleted from admin.css, `test_wraps` reds 6 of 6 on the two-line assert: `AssertionError: [198.375, 24.8]` at 1440 and 1100 (both names), and `[446.34375, 24.8]` and `[396.75, 24.8]` at 390.
2. With the rule deleted and the two-line assert also removed (so the board-shift assert is reached), it reds 6 of 6 on the shift: `AssertionError: (0, 161.578125)` at 1440, `(0, 161.59375)` at 1100, and `(0, 404.34375)` / `(0, 354.75)` at 390. At 390 the rule is gone everywhere in this control, so the phone loses its clamp too.

Both files were restored after each control: `git diff --stat` shows the same 2 files, 31 insertions and 11 deletions, and admin.css is byte-identical (`cmp`) to the saved branch copy. There is no separate control for the textContent check: the clamp is CSS-only, so there is no mechanism to revert that would take text out of the DOM.

**Gate (unarmed, `-o addopts= -rfs`).** Files: tests/test_puzzle_solver_maybe.py (touched), tests/test_puzzle_solver_progress.py, test_puzzle_solver_phone.py and test_puzzle_solver_solved_reveal.py (its neighbours), and the public player set: test_player_base_css.py, test_player_bundle.py, test_player_public_mode.py, test_player_shared_ui_site.py, test_player_viewport_matrix.py, test_public_player.py and test_public_player_pages.py. Result: 414 passed, 0 failed, 0 skipped. tests/test_kanban_review_record.py: 71 passed.

**Net test count.** 10689 collected before and 10689 after, so net 0.

[Review 1/3] Score: 8.5, one gating finding, not certified. F-001 (high) removing `overflow: hidden` from the moved rule leaves `test_wraps` green while lines 3+ paint over the Probe/Show grid buttons: AC-2's "cut, not wrapped further" has no control. F-002 (medium) `--text-xs` -> `--text-sm` survives `test_wraps` (two --text-sm lines still fit the tools' box): the owner's chosen size is unheld. F-003 (low, owner's eye) a name without spaces breaks after the label on desktop, so line 1 shows only "Solved!" and the name gets one cut line. F-004 (low) the 600x900 pre-existing shift note omits dx +12.656. Measured: AC-1 0/0 in 24 cases; AC-3 0 differences over 73,344 values at 390x844 and 844x390; AC-4 full name in the accessibility snapshot; control re-fired 6/6 red; 414 passed.

### Fix round 1 (review cycle 1, 8.5; F-001..F-004)

**F-001 (gating): the cut is now held where it is painted.** `test_wraps` gets a module constant, `_BANNER_TEXT`, that returns the text span's measurements. The test now also asserts:
- `scrollHeight > clientHeight`, so the name runs past the two lines;
- a third line is laid out: the first client rect of a Range over `[data-player-solved-name]` whose centre lies below the span's box;
- no element of `#puzzle-player-solved` is in `document.elementsFromPoint` at the middle of that line.

It reads the whole hit stack on purpose. Under the no-overflow mutant, the third line paints beneath the Show grid button there, so `elementFromPoint` returns the button either way, and only the stack lists `STRONG.player-solved-name`. Measured at 1440x900 with a 120-character name:
- mutant stack: `SPAN.player-btn-label`, `BUTTON...player-show-grid`, `DIV.player-probe`, `STRONG.player-solved-name`, ...
- with the rule: `SPAN.player-btn-label`, `BUTTON...player-show-grid`, `DIV.player-probe`, `DIV.player-toolbar is-solved`, `MAIN.main`.

My first version took the first line whose top was below the box, which skipped line 3: its content area starts above the box edge. It switched to the line's centre.

**F-002: the size is held.** `test_wraps` asserts the span's computed font-size equals `--text-xs` as the page resolves it: a temporary element is given `font-size: var(--text-xs)` and its computed size is read. No px value is written in the test.

**F-003 (owner-visible): fixed with one CSS-local rule.** I tried three candidates by injecting a style tag, and listed each line's characters at 1440x900, 1100x700, 390x844 and 844x390 for names of 10, 24, 60 and 120 characters with spaces, and 26, 60 and 120 without:
- `word-break: break-all` on the name: starts a name with no spaces on line 1, but also breaks names with spaces mid-word at every view.
- `line-break: anywhere` on the name: the same.
- `.player-solved-label { white-space: nowrap; }`: starts a name with no spaces beside "Solved!" and fills both lines at 1440 and 1100 (for example `Solved! The_lighthouse_k` / `eepers_cottage_on_the_n`, where it was `Solved! ` / `The_lighthouse_keepers_`). Names with spaces have identical line content, name rectangle and shift at all four views, and every name is identical at 390x844 and 844x390.

The third was adopted. The compact block's visually-hidden rule already gives that label `white-space: nowrap`, so nothing new applies on the phone. Screenshots of the toolbar at 1440 with a 60-character no-space name: /private/tmp/claude-501/card507/f003/none-t60-1440.png (before) and /private/tmp/claude-501/card507/f003/label-nowrap-t60-1440.png (after). `test_wraps` holds it: where the label is visible, the name's first line starts on the label's line; at 390 the check is null.

**F-004:** the 600x900 note above now gives dx +12.656 too. Re-measured, not pasted: base2 and after2 both give dy +27.203 and dx +12.656 for all eight names.

**Re-measurement with the F-003 rule** (base2 = fc3f33e2's admin.css swapped into the worktree; after2 = this round):
- AC-1: board shift 0 (dx and dy) for all eight names at 1440x900 and 1100x700, on both boards.
- AC-2: at most 2 lines everywhere; the height-900 sweep from 700 to 1920 px gives 0 for every name.
- AC-3: 390x844 and 844x390, 2 boards x 8 names x 9 snapshots each: 288 compared, 0 differences, shift 0.
- G-2: the short-name figures are unchanged from the first round.

**Controls (mutants of admin.css; after each one admin.css was copied back and `cmp`-checked against the branch copy).**
1. No-overflow mutant (` overflow: hidden;` removed from `.player-solved > span`): `test_wraps` fails 6 of 6 on the `inBanner` assert with `assert True is False`.
2. `--text-sm` mutant: 6 of 6 fail on the font-size assert with `assert '14.4px' == '12.48px'`.
3. Label-nowrap rule removed: 2 of 6 fail, the one-token name at 1440 and at 1100, on the beside-label assert with `assert False is True`. The words cases and 390 stay green, as designed.

**Gate, fix round 1 (unarmed, `-o addopts= -rfs`, same files as the first round).** 414 passed, 0 failed, 0 skipped. tests/test_kanban_review_record.py: 71 passed.

**Net test count.** 10689 tests collected in 3.84s; that equals the 10689 before this card, so net 0. No test was added: the new asserts are folded into `test_wraps`.
