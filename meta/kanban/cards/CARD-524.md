# CARD-524: A long first word in the solved name starts on line 1, breaking mid-word

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/524-long-first-word
**Worktree:** —
**Source:** roadmap wave 12, cut 2026-11-22 on the owner's "let's take your suggestions for first 4 ideas". IDEA-221 (CARD-507 review F-003/F-005).
**Idea:** IDEA-221
**Wave:** 91
**Created wave:** 91
**Deferred waves:** 0
**Depends on:** CARD-523 (same stylesheet and test file)
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_maybe.py
**UI surface:** admin solver page solved banner (desktop)
**Review score:** 9.0 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-22T15:36Z
**Closed:** 2026-11-22T16:46Z
**Actual:** 1c — ratio 1/1 = 1.0
**Merge commit:** 9ad3fd2c399db70e736fd2971ce76df8c2b66f3b
**Blocked by:** —

## Why this card exists

With CARD-507's two-line clamp on the solved banner, a name whose first word does not fit beside "Solved! " starts on the second line, so only one line of the name shows ("Solved!" / "The_lighthouse_keepers_…"). CARD-507's fix round 1 had a version that fills line 1 by letting such a word break mid-word, and reverted it because whether mid-word breaks were acceptable was the owner's call. Owner's ruling 2026-11-22: yes, let a long first word break across lines.

## What to implement

Read CARD-507's card and notes first (the reverted attempt and why). Re-verify on main: a no-space name and a long-first-word name at the desktop widths CARD-507 measured start on line 2. Then let the name start on line 1 beside "Solved! ", breaking a word only when it cannot fit (ordinary names keep breaking between words).

## Acceptance criteria

* **AC-1**: a no-space name and a long-first-word name each start on line 1 beside "Solved!" and use both clamped lines (control: main's code starts them on line 2).
* **AC-2**: an ordinary multi-word name breaks only between words, as before; a short name is unchanged.
* **AC-3**: the board does not move on solve at the widths CARD-511 and CARD-523 hold to 0, and the banner's two-line clamp and text size (CARD-507) are unchanged.
* **AC-4**: net test count 0; extend CARD-507's banner tests. Report it.

## Guardrails

* **G-1**: no publish; the public banner reads "Solved!" without a name, so it should be unaffected: show that.
* **G-2**: renders go to ~/Documents/nonogram-reviews/CARD-524/, never into the repo.

## Worktree notes

### Implementation (2026-11-22)

**Change.** admin.css: one rule after CARD-507's clamp rule (`.player-solved > span`): `.player-solved-label { white-space: nowrap; }`, with a comment. It removes the line break after "Solved! ", so the name starts on line 1. A first word that does not fit there breaks mid-word through `.player-solved-box .player-solved`'s existing `overflow-wrap: anywhere`. This is the rule CARD-507 fix round 1 tried and reverted. Its review F-005 case ("Solved! Northumberlands" / "hire lighthouse at dawn") is the behaviour the owner ruled for on 2026-11-22.

**Test (AC-4, net 0).** `TestSolverMaybe_LongNameBannerWrapsInsideTheToolsWidth::test_wraps` is extended. No test was added and no node id changed. A new module constant `_BANNER_LINES` returns the text of each line inside the clamped box, read from each character's rect. A line counts as inside when its centre is above the box's bottom. With an argument it first replaces the name's text, so the same element and rules lay it out. Another new constant, `_LONG_FIRST_WORD`, is "Northumberlandshire lighthouse at dawn over the harbour wall". These checks run at 1100x700 only, the one viewport in `test_wraps` that shows the label. They cover the stored name, plus `_LONG_FIRST_WORD` swapped in for the words case:
- exactly 2 visible lines, and line 1 starts with "Solved! ";
- both lines carry name text, and together they are the name's prefix;
- each line ends at a space or inside the name's first word;
- `_LONG_FIRST_WORD`'s line 1 does not end at a space, so it breaks mid-word;
- the ordinary words name's line 1 ends at a space.

**Premise re-verified (main's admin.css, Playwright probe under /private/tmp/claude-501/card524/).** The probe asserted that `nonogram` and `tests` import from this worktree. At 1440x900, 1100x700 and 1280x720 the visible lines were:
- no-space names (26, 60 and 120 characters): `Solved! ` / `lighthouse_keepers_cotta`;
- long-first-word names: `Solved! ` / `Northumberlandshire `, and `Solved! ` / `Northumberlandshire_lig`.

So the premise holds: these names start on line 2.

**After (AC-1, AC-2).** Same probe, same three desktop views:
- nospace26: `Solved! lighthouse_keeper` / `s_cottage`.
- nospace60 and nospace120: `Solved! lighthouse_keeper` / `s_cottage_on_the_norther`.
- longfirst38: `Solved! Northumberlands` / `hire lighthouse at dawn`.
- longfirst60: `Solved! Northumberlands` / `hire_lighthouse at dawn `.
- Unchanged from before: short10 (`Solved! Lighthouse`, 1 line), ordinary24 (`Solved! The lighthouse at ` / `dawn x`), and ordinary60 and words120 (`Solved! The lighthouse ` / `keeper's cottage on the `).

**AC-3.**
- The board's dx and dy on solve are 0 for all 9 names at the 3 desktop views, before and after.
- At 390x844 and 600x900, the probe's output (board dx/dy, line contents, line count, label position) is identical before and after. On the compact layout the label is visually hidden and already nowrap.
- `test_sweep` (CARD-511/523's 57 viewports) passes in the gate below.
- The clamp rule and its text size are untouched. `test_wraps` still asserts at most 2 lines and font-size equal to `--text-xs` at all 3 viewports.

**G-1 (public player, not published).** A scratch site was assembled with `scripts/assemble_player_site.py --bundle .../build/player-bundle --out /private/tmp/claude-501/card524/site`, without `--analytics`. Its admin.css is byte-identical to this branch's. It was served locally, and the smallest puzzle was solved with `solve_to_the_end` at 1440x900, 1100x700 and 390x844, once with main's admin.css swapped in and once with this branch's. The label's white-space is `normal` before and `nowrap` after at desktop, so the rule does apply. Every other measured value is identical: banner text "Solved!", banner and span rects, label position, board position, and 0 name elements. The banner screenshots are byte-identical at all 3 views.

**Renders (G-2).** In ~/Documents/nonogram-reviews/CARD-524/:
- `before-*` and `after-*`: toolbar shots at 1440x900, 1280x720 and 1100x700 for 9 names (short, ordinary, no-space, long-first-word);
- `compare-1440x900.png` and `compare-1100x700.png`: side-by-side sheets;
- `public-{before,after}-*.png`: the public banner.

**Controls (admin.css restored after each; `cmp` against the saved branch copy matched).**
1. With main's admin.css (the rule absent), `test_wraps` fails 2 of 6, the two 1100-700 cases:
   - words: `AssertionError: ['Solved! ', 'Northumberlandshire ']` on the name-on-line-1 assert;
   - one-token: `AssertionError: ['Solved! ', 'lighthouse_keepers_cotta']`.
2. With `.player-solved-name { word-break: break-all; }` added (every word breaks), 1 of 6 fails: 1100-700-words, `AssertionError: (17, ['Solved! The lighthouse ke', "eper's cottage on the nort"])`, `assert ('e' == ' '`. This means an ordinary name broken mid-word reds.

**Gate (unarmed, `-o addopts= -rfs`).** Files run:
- touched: tests/test_puzzle_solver_maybe.py;
- neighbours: test_puzzle_solver_progress.py, test_puzzle_solver_phone.py, test_puzzle_solver_solved_reveal.py;
- the public player set: test_player_base_css.py, test_player_bundle.py, test_player_public_mode.py, test_player_shared_ui_site.py, test_player_viewport_matrix.py, test_public_player.py, test_public_player_pages.py;
- tests/test_browser_fixture_scope.py, because `test_wraps` node ids are recorded there and none changed.

Result: 447 passed, 0 failed, 0 skipped.

**Net test count.** `--collect-only` over tests/ gives 10694 collected before and 10694 after, so net 0.

[Review 1/3] Score: 9.0, nothing gating, certified. At seven desktop views (960-1480 px) every name gives the same lines: ordinary names break only between words; a no-space name and a long first word fill both lines from "Solved! "; a long second word moves whole to line 2 and breaks there (as since CARD-507). Board dx 0 / dy 0 at all 9 views; clamp two lines at 12.48 px; compact label still visually hidden; textContent still "Solved! <name>". Control 1 red (2 failed, 4 passed), restored. Gate subset 105 passed. Renders read well. F-001 (low): `_BANNER_LINES` measures character boxes, which the visually-hidden clip does not change, so a hidden label on desktop still reads as "Solved! " (control: hiding it on desktop left the one-token case green); asserting the label is wider than 1 px would close it. F-002 (low): the test's rule "a word is broken only when it is the name's first word" is too broad; a long later word is also broken, correctly. F-003 (info, owner's call): a long second word still leaves line 1 as "Solved! The ".

**Merge gate (orchestrator).** `make test-gate BASE=main` on `370afb69` (main had not moved since the merge into the branch) answered SELECTION: 7565 passed / 30 skipped (unarmed) / 12 deselected / 1 xfailed / 0 failed in 29 min 21 s, then the marked run 6 passed. 7 marked tests are owed at the wave close.
