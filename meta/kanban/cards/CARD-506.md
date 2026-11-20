# CARD-506: Player and admin-CSS minors: two local values to tokens, Redo's aria-disabled, the ? centring, the Reset Escape path, stale comments, a scale-1 render

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/506-player-css-minors
**Worktree:** —
**Source:** roadmap wave 6 (cut 2026-11-20 on the owner's "please start the next wave"). IDEA-053, 060, 095, 147, 151, 157, 161, 166 (WSJF 2.31 each, about 0.125 d each). Several are marked unverified in the backlog: the player was reworked through the November cards, so expect some to be closed already.
**Idea:** IDEA-053, IDEA-060, IDEA-095, IDEA-147, IDEA-151, IDEA-157, IDEA-161, IDEA-166
**Wave:** 85
**Created wave:** 85
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_*.py, tests/test_admin_design_tokens.py
**UI surface:** puzzle player (admin, and the public player built from the same files), guide strip
**Review score:** —
**Started:** —
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
