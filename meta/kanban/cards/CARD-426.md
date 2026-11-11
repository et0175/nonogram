# CARD-426: The brush menu hangs: an outside tap neither closes it nor lets Escape close it, and it swallows taps on the board

**Status:** in_progress
**Priority:** P2
**Category:** bug
**Estimate:** 1c (0.5d)
<!-- The fix is one document-level dismissal, modelled on the one `wireExplainDismiss` already installs for the hint strip. The cost is getting the interaction right at the edges (a tap on the trigger itself must still toggle, not close-then-reopen) and the pointer-events half. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/426-brush-menu-dismiss
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-426
**Source:** owner play-test findings, Google Doc "Гра - тест", 2026-11-11, item 2. Reproduced on production (https://nonogram.adverax.io) before drafting; the measurements below are mine, the finding is the owner's.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_brush_menu.py
<!-- Derived 2026-11-11 by reading `solver.js`'s `openMenu`/`closeMenu` and every `closeMenu()` call site, and `admin.css`'s `.player-tool-menu`. Conflict edge: CARD-424 also edits `admin.css`'s compact block and the brush-menu test module — serialize, no dependency. -->
**Review score:** —
**Started:** 2026-11-11T18:05:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Measured on production at 390x844 (touch emulation), opening the menu from the trigger:

| action | `aria-expanded` | menu visible |
| --- | --- | --- |
| tap the trigger | true | yes |
| touch the board | **true** | **yes** |
| touch the header | **true** | **yes** |
| tap the trigger again | false | no |

And, separately measured: while the menu is open, Playwright refuses a tap on the stage for 30 s with `<div role="menu" ... id="puzzle-player-tool-menu"> ... intercepts pointer events`. The panel is 160 x 174 px at (16, 115) — over the top-left of the grid.

**Escape works, and the interaction between the two is the actual defect.** `openMenu()` focuses an item, and a keydown handler closes the menu on Escape — verified: `expanded=false` after Escape in both touch and mouse modes. But an outside tap does not close the menu *and* takes focus out of it, so after the tap the owner saw, Escape no longer reaches the handler either and the trigger is the only way out. The first reading of this card's own evidence said "not even Escape"; that was measured in a sequence where an outside tap had already moved focus, and is corrected here.

**The missing piece is named by its own neighbour.** `wireExplainDismiss` installs exactly the handler this menu lacks — `document.addEventListener("pointerdown", ..., true)` with an exemption for the control that is about to write the next message — for the hint strip, because CARD-409 decided the strip "is a glance, not a panel". The menu is a panel and has no such dismissal: every `closeMenu()` call site is a pick, the solved lock, or a key.

## What to implement

1. **An outside pointer-down closes the menu.** Follow `wireExplainDismiss`'s shape, including its exemption: a pointer-down on the trigger must reach the trigger's own toggle rather than being closed first and reopened by the click that follows. Wire it once, from the same place that wires the menu.
2. **An open menu must not swallow board taps.** Decide, and record which: the menu stays hit-testable but the outside pointer-down closes it and the tap is not re-dispatched (the usual menu behaviour — one tap to dismiss), or the first tap both closes and acts. The former is the smaller change and the one most UIs do; the AC pins whichever is chosen.
3. Keep the keyboard path exactly as it is: Escape with focus inside the menu closes it, and the roving focus of the items is untouched.

## Acceptance criteria

- **AC-1** (an outside tap closes it): at 390x844 and 1440x900, with the menu open, a pointer-down on the board and on the header each leave `aria-expanded="false"` and the menu hidden. (test: new cells in `tests/test_puzzle_solver_brush_menu.py`, or a changed existing menu-state cell; plant: remove the dismissal and the cell reds.)
- **AC-2** (the trigger still toggles): tapping the trigger while open closes it, and tapping it while closed opens it — no open-close-open flicker from the new handler. (test: the same cell, both directions.)
- **AC-3** (the board is reachable): with the menu open, a tap on a cell under the menu's box behaves as the decision in step 2 says — and in neither case does the tap do nothing. (test: the same module; evidence: the Playwright interception message above is what must stop happening.)
- **AC-4** (Escape is unchanged): opening by tap puts focus on a `.player-tool-item` and Escape closes the menu. (test: an existing keyboard cell, unchanged — it already passes.)

**Net test count: aim for 0 added** — the module already has menu-state cells; change one rather than adding four. State the net.

## Worktree notes

- **[Env]** forge version unresolved (no `.claude-plugin/plugin.json` at the executing path; this project has no `meta/.skills.yml`, so no `forge.min_version` comparison ran and no `models:` block exists — agents inherit the session model).
- **[Start gate]** `make_probe.py start-gate` → exit 0, `decision: gate`, `source: test_command`. **That command is exit 127 in a worktree** (no `.venv` there): use `/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`, or `make test-gate PY=<main>/.venv/bin/python`. Fork point `8ecb8758`, interactive mode.
- **[Impact scope]** Derive it with `scripts/impact_set.py --gate --against main`, never from a standing note — CARD-423 shipped two criticals past a hand-picked 10-module set that the script would have caught (it selects 141 files for an `admin.css` change).
- **[Conflict edges]** CARD-424 (brush-menu tap targets) and CARD-428 (landscape zoom) both edit `admin.css`, and CARD-424 also edits `tests/test_puzzle_solver_brush_menu.py`. Neither is started; serialize, no dependency.
