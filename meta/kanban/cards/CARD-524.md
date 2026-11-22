# CARD-524: A long first word in the solved name starts on line 1, breaking mid-word

**Status:** ready
**Priority:** P3
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap wave 12, cut 2026-11-22 on the owner's "let's take your suggestions for first 4 ideas". IDEA-221 (CARD-507 review F-003/F-005).
**Idea:** IDEA-221
**Wave:** 91
**Created wave:** 91
**Deferred waves:** 0
**Depends on:** CARD-523 (same stylesheet and test file)
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_maybe.py
**UI surface:** admin solver page solved banner (desktop)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
