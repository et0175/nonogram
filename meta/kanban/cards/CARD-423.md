# CARD-423: Portrait phone tap targets are 44 x 36 px — the compact toolbar sets a width floor and no height floor

**Status:** in_progress
**Priority:** P2
**Category:** ux-polish
**Estimate:** 1c (0.5d)
<!-- The CSS is one declaration beside the `min-width: 44px` rules it joins. The cost is the three parts that are not CSS: widening `_LABEL_BOXES` to the four of the nine it cannot currently see, and re-measuring the four viewports because the toolbar gets taller and the board absorbs it. The owner ruled D1 below at drafting time, so no decision is outstanding. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/423-portrait-tap-targets
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-423
**Source:** my own measurement of the live site (https://nonogram.adverax.io) on 2026-11-11, at the owner's "check the live site on my phone", carded on their "card the 44px portrait touch targets". **Measured under Playwright device emulation (iPhone UA, touch, DPR 3), not on a physical phone** — the geometry is the page's, but no finger has tested it.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_phone.py
<!-- Derived 2026-11-11 by reading which file holds the measured behaviour: the compact block in admin.css ("Compact toolbar", CARD-401) and the one test that asserts the 44 px claim. `src/nonogram/admin/static/tokens.css` is read, not edited (`--control-h: 36px` stays: it is the whole panel's control height, not the player's). Nothing under `player/` changes — `admin.css` is in `COPIED_FROM_ADMIN`, so the public player gets this by the build-time copy and the byte-identity check carries it. Conflict edges: none open (CARD-400..422 are all `done`). -->
**Review score:** —
**Started:** 2026-11-11T13:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

On production at 390x844, 852x393 and 874x402 (portrait), **nine toolbar controls measure 44 x 36 px**: the brush trigger (Black), the Region toggle, Undo, Redo, Reset, Hint, `-`, `+` and Probe. 36 px is under the 44 px minimum this player adopted for itself.

The mechanism is in `admin.css`'s compact block (`@media (max-width: 600px), (max-height: 500px)`): `.player-tool-trigger`, `.player-history > .btn`, `.player-zoom .btn` and `.player-probe > .btn` each get `min-width: 44px` and **no height floor**, so the height falls through to `.player-toolbar .btn`'s `min-height: var(--control-h)`, which `tokens.css` sets to 36px.

Two things in the tree say 44 px was meant in both dimensions rather than in width alone. `.player-zoom-readout[role="button"]`, in that same compact block, already carries `min-height: 44px`. And CARD-402's landscape side-column block sets `height: 44px; min-height: 44px` on every `.btn` — which is exactly why the same measurement at 844x390 found **no** control under 44 px and portrait found nine. Portrait is the one path where the floor was written in one dimension.

**CARD-401 is not in breach.** Its AC-6 reads "at least 44 px wide and `--control-h` tall", so 36 px tall satisfied it as written, and its test asserts `box["button"] >= 44` on the width alone. The gap is in the rule, not in the implementation of it — which is why this is a new card and not a regression on a closed one.

The cost is not the declaration. Raising the floor makes the portrait toolbar taller: four rows at 44 px instead of 36 px is about **+32 px of chrome**. The board absorbs it rather than the page overflowing — `solver.js`'s `measureStageTop` writes the measured `--player-stage-top`, which both the stage's cap and the cell-height term read — so what actually gets smaller is the cell, and on the owner's 30x30 class of board that cell is already 9.1 px. That trade is a decision, not a measurement. Separately, `_LABEL_BOXES` only finds buttons that carry a `.player-btn-label`, so the brush trigger, Region, `-` and `+` — four of the nine — are outside the existing assertion entirely.

**[OWNER RULING 2026-11-11]** **D1: 44 px tall for all nine, and the board gives up the ~32 px in portrait.** Declined: keeping 36 px, and raising only the controls where a mis-tap is expensive (Reset, Probe). So the floor is ONE rule at every compact viewport — which is what the compact block's own comment and CARD-402's landscape block already state — and the author implements it without re-asking, recording what the cell size became (AC-2). If the 30x30's cell turns out to be unusable at the new size, that is CARD-406/407's Fit question, not a reason to lower this floor.

## What to implement

1. **A height floor in the compact block,** on the same selectors that already carry `min-width: 44px`, so one condition governs both dimensions. The comment's line "Every button is at least 44 px wide and `--control-h` tall" becomes "at least 44 x 44 px": that sentence *is* the rule, so it moves with it. `--control-h` itself does not change — it is the whole panel's control height, and the player is not the only thing that reads it.
2. **Re-measure and record** the portrait toolbar's rows and height, the stage's measured top and the resulting cell size, and that no horizontal page scroll appeared. Landscape should not move at all; if it does, CARD-402's block has been reached and that is a finding, not a re-pin.
3. **Nothing in `player/`.** No public-mode duplicate cell is added (owner test budget, 2026-11-07): the behaviour is verified once on the admin page and the copy's byte-identity check carries it to the public player.

## Acceptance criteria

- **AC-1** (the floor holds in both dimensions): at 390x844 and 844x390, every control inside `.player-toolbar` — the brush trigger, the Region toggle, Undo, Redo, Reset, Hint, Check (admin only), Probe, `-`, `+` and the zoom readout — has a border box at least 44 px wide **and** at least 44 px tall. (test: `tests/test_puzzle_solver_phone.py::TestSolverPhone_CompactToolbar::test_icons_only_when_compact`, **changed**: `_LABEL_BOXES` widens from `.player-btn-label` holders to every visible button in the toolbar and returns height beside width, and the docstring's "at least 44 px wide" is retired for the two-dimensional claim. **Plant:** drop the new `min-height` and the 390x844 cell reds while 844x390 stays green — one control, which also proves the two media blocks are independent.)
- **AC-2** (the board absorbs it, the page does not): at 390x844 on a 30x30 board there is no horizontal page scroll, and the cell size after the change is recorded in Worktree notes as the figure it became. (test: the existing `TestSolverPhone_BoardFitsThePhoneWidth` and `TestSolverPhone_FallsBackToMirrorWhenDoublingWouldNotFit` cells, which read the measured stage top, pass unchanged — a changed cell size that reds them is the signal that the fit formula, not the toolbar, needs the card.)
- **AC-3** (desktop and landscape unmoved): at 1280x720 and 1440x900 the toolbar geometry is unchanged, and at 844x390 CARD-402's side-column measurements are unchanged. (test: the existing brush-menu slot-geometry, percent and maybe cells, plus CARD-402's own cells.)

**Net test count: 0 added** — one existing parametrised cell gains a dimension; no new module, class or node id.

## Requirements

No AC in `meta/architecture/requirements.yml` pins a tap-target minimum — the word "compact" does not appear there, and the only 24 px figure is a *cell* floor in FR-044's deep-row-clue criterion. So this card **amends no requirement**: the rule stays where CARD-401 put it, in the compact block's comment and in the one test. If the owner wants it in the registry instead, that is a new line under FR-044 and the author asks for the id rather than inventing one (ADR check refs must be honest).

## Verification

Measured in a browser, not asserted from CSS, and recorded in Worktree notes with the numbers: **390x844**, **844x390**, **1280x720**, **1440x900**, each on a 15x15 board and on a 30x30 stored grid. For each: every toolbar control's two dimensions, the toolbar's height and row count, the stage's measured top, the cell size, and no horizontal page scroll.

## Worktree notes

- **[Env]** forge version unresolved: no `.claude-plugin/plugin.json` at the executing path, and this project has no `meta/.skills.yml`, so no `forge.min_version` comparison ran and no `models:` block exists (agents spawn without a `model:` override, inheriting the session model).
- **[Start gate]** `make_probe.py start-gate` → exit 0, `decision: gate`, `source: test_command`, command `./.venv/bin/python -m pytest`. **But that command is exit 127 in a worktree** — no card worktree has a `.venv` (the path is relative). The gate in this worktree runs as `make test-gate PY=/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`, or that absolute interpreter directly for a single module.
- **[Impact scope]** Player card: the gate is the player/solver test set (`tests/test_puzzle_solver_*.py`, `tests/test_player_*.py`), not the generator or book suites. The full suite runs at the merge gate; acquire `meta/kanban/.full-suite.lock` before any full run.
