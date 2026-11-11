# CARD-426: The brush menu hangs: an outside tap neither closes it nor lets Escape close it, and it swallows taps on the board

**Status:** review
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
**Review score:** 6.5 (cycle 1)
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

### Implementation (wave 79)

**The interaction decision, step 2: (b) — the dismissing tap also acts.** A
pointer-down outside the menu closes it and is not consumed, so it goes on to
whatever it was aimed at: a tap on a cell closes the menu *and* marks the
cell. Reason, in one sentence: it is the shape both of this file's existing
dismissals already have (`wireExplainDismiss` and the wrong-guess offer's
`closeOffer` listener each close and consume nothing — and `admin.css`
already pairs `pointer-events: none` on `.player-explain` with `auto` on
`.player-offer` for the other box that lies over the board), and it is the only
reading under which "the board is reachable" is true of a panel that lies
over the board. (a) would have needed `preventDefault` + `stopPropagation` on
a document-level capture listener, a bigger footprint than the card's own
description of the fix ("one document-level dismissal"): a capture-phase
`stopPropagation` at `document` also stops the stage's own `pointerdown`
handler — the pinch bookkeeping and the crosshair — and by the spec a
prevented `pointerdown` suppresses the compatibility mouse events, so the
click behind it would die for touch and survive for mouse. **Reasoned, not
measured: (a) was not built.** What the choice rests on measurably is that
both existing dismissals in this file consume nothing.

**What was measured, before anything was changed.** Escape works, exactly as
the card says: `TestSolverBrushMenu_Keyboard` (3 cells, including
`test_escape_closes_and_tab_leaves`) was green on the fork point. The defect
reproduced at both viewports on the admin solve page: after a pointer-down on
a board cell with the menu open, `aria-expanded` stayed `"true"` and the menu
stayed visible.

**Geometry, measured in this worktree (admin solve page, 100 % zoom).** The
menu's box is 160 x 174 px at every viewport measured. 390x844: box at
(16, 256), stage top at y 427.9 — the box ends 2.2 px into the stage.
1440x900: box at (260, 186), x 260..420, while the first column of cells
starts at x 432 (the sticky row-clue band holds 260..432) — the box ends
12 px short of a cell, and stays there at any scroll, the band being sticky.
844x390 (the CARD-402 landscape strip, where the menu is `position: fixed`):
box at (260, 188), cells from x 516. **So on the ADMIN page no cell centre is
under the box at any pinned viewport** — the box overlaps the clue band, not
the grid. The owner's (16, 115) measurement is the PUBLIC page, whose shorter
shell puts the stage under the toolbar; `solver.js` and `admin.css` are
copied into it byte-identically (`player/assemble.py`'s `COPIED_FROM_ADMIN`),
so it inherits both halves. AC-3 is therefore pinned as the *mechanism*: the
box answers the hit test with whatever lies under it (three no-item points,
computed from the live rects), each item answers for itself, and the marking
half on an ordinary cell tap. With a 10x10 grid at 1440x900 the overlap is
real on admin too (cells (0,0) and (0,1) fall under the box), and that is the
case the fix was first sighted against; the shipped cell uses the family's
15x15 `GRID` and does not depend on it.

### AC red->green

- **AC-1** (an outside tap closes it — board and header, 390x844 and
  1440x900): test
  `TestSolverBrushMenu_AnOutsidePointerDownDismissesIt::test_an_outside_pointer_down_closes_it_and_the_board_stays_reachable`
  red->green. First red was the right one: `menu.is_hidden()` False at
  390x844 after a CDP touch tap on cell (4,4) — an open menu after an outside
  pointer-down, not a selector or fixture error.
- **AC-2** (the trigger still toggles, no flicker): same test, red->green
  (its toggle block is what the dropped-exemption plant reds).
- **AC-3** (the board is reachable; decision (b)): same test, red->green —
  the cell is marked by the dismissing tap, and the box's three no-item
  points answer the hit test with what lies under them.
- **AC-4** (Escape unchanged): `TestSolverBrushMenu_Keyboard` green before
  and after, unedited; the new cell also asserts focus is on a
  `.player-tool-item` after a tap-open and that Escape closes it.

### Plants run (one at a time, each restored)

| plant | reds |
| --- | --- |
| the `document` pointer-down dismissal removed | the cell-tap block (`menu.is_hidden()` False) — i.e. the production defect |
| its trigger exemption dropped | the AC-2 toggle block: the pointer-down closes and the click behind it reopens, so a second click never shuts the menu |
| `.player-tool-menu`'s `pointer-events: none` dropped | `dead == [True, True, True]` — all three no-item points answer "the menu" |
| `.player-tool-item`'s `pointer-events: auto` dropped | `items == [False, False, False, False]` — nothing in the menu is clickable |

An earlier form of the hit test probed the box's bottom-right corner 1 px in;
the third plant showed that point was `False` either way (the box is
`--radius-container` rounded, so the corner is outside it). It was replaced by
the bottom padding strip, and all three points are now load-bearing.

### SCOPE+

`SCOPE+ tests/test_player_base_css.py` — unavoidable, and it would have been
a gate red. That module's FROZEN computed-style census includes
`pointer-events`, measured on the public player, which serves this same
`admin.css`. The run before the edit named **exactly one** difference at each
of its two widths and no other, rectangles included:
`04 div puzzle-player-tool-menu: pointer-events 'auto' != 'none'`. That one
field was updated in both tables (programmatically, by the property's index in
`PROPS`, not by hand-counting pipes), and `PROVENANCE["recorded"]` now says
CARD-426 edited one field rather than re-recording. The module is green
(3 passed). Nothing else in the census moved, which is also the measurement
that the rule changes no layout.

### Verification (narrowed, never the gate)

All runs `-o addopts= -rEfs` (the project's `addopts = "-q"` would make a
second `-q` print no summary at all), against the main checkout's venv — a
card worktree has none.

| set | result |
| --- | --- |
| the card's four files: `…brush_menu` `…marking` `…phone` `…zoom` | **188 passed**, 0 failed, **0 skipped** (215 s) |
| `…marking` `…phone` `…zoom` `tests/test_player_public_mode.py` (re-run after the final edits; the public-mode page added because `solver.js` drives it too) | **216 passed**, 0 failed, 0 skipped (430 s) |
| `…brush_menu` + `tests/test_player_base_css.py` (the SCOPE+ census) | **54 passed** |
| `tests/test_admin_design_tokens.py` (it reads `admin.css`) | 14 passed |
| `tests/test_kanban_review_record.py`, alone, after each card edit | 68 passed |

The full suite and `make test-gate` were NOT run: the orchestrator owns the
gate and its impact selection. Two files it will want in scope beyond the
card's `Touches:` are `tests/test_player_base_css.py` (edited here, see
SCOPE+) and `tests/test_puzzle_editor_ui.py` (`puzzle_edit.html` loads this
same `solver.js` and opens this same menu; its menu cells only open it and
read the items, and none drives an outside pointer-down, so no change was
needed — read, not run).

### Commit

`fd2e94fe` on `card/426-brush-menu-dismiss`, four explicit pathspecs
(`solver.js`, `admin.css`, `tests/test_puzzle_solver_brush_menu.py`,
`tests/test_player_base_css.py`), message through `-F`. Nothing under
`meta/` is staged (INV-023): these notes stay uncommitted for the
orchestrator to sync. Nothing under `player/` was touched — both changed
files are copied into the public site byte-identically, so it inherits the
fix with no edit of its own.

### Net test count

**+1 collected node id.** Two test files changed: this card's module went
50 -> 51 (both counted with `--collect-only -q`, the fork-point number from
`git show HEAD:…` collected under a temporary name and then deleted), and
`tests/test_player_base_css.py` gained none — only two of its FROZEN data
fields changed. One cell carries AC-1, AC-2 and AC-3 at both viewports, and re-asserts
AC-4's focus along the tap path; no existing cell was weakened or deleted. The
card's target was 0 — no existing cell owns "the menu's open/closed state
under pointer input", and folding a dismissal into
`test_one_button_with_a_menu` (the group's shape) or
`test_menu_lists_the_four_brushes_in_order` (the menu's contents) would have
misnamed both.

### [Orchestrator] notes on the implementation

- **[Card defect, mine] AC-3 was written from a public-page measurement and assigned to an admin-page test.** The implementer measured that on the admin solve page **no cell centre lies under the menu's 160 x 174 box at any viewport** — at 1440x900 the box spans x 260..420 while the first column starts at x 432, and the *sticky* row-clue band holds 260..432 so neither scrolling nor zooming changes it; at 844x390 cells start at x 516; at 390x844 the box ends 2.2 px into the stage. The owner's (16, 115) overlap is the **public** page, whose shorter shell puts the stage under the toolbar. So the literal Playwright interception message cannot be made to stop on admin with this grid. AC-3 is instead pinned as the mechanism — the box answers the hit test with whatever lies under it (three no-item points computed from live rects, not written down), each item answers for itself, plus the marking half on an ordinary cell tap. That substitution is sound and is the implementer's, not mine; the defective wording was mine.
- **[Decision (b)] recorded and justified from the tree, not from taste.** The dismissing pointer-down closes the menu and consumes nothing, so the tap also acts. The reason given: both existing dismissals in `solver.js` (`wireExplainDismiss`, and the wrong-guess offer's `closeOffer`) close and consume nothing, and `admin.css` already pairs `pointer-events: none` on `.player-explain` with `auto` on `.player-offer` for the other box that lies over the board. (a) would have needed `preventDefault` + `stopPropagation` on a document capture listener, which also stops the stage's own `pointerdown` (pinch bookkeeping, crosshair) and would kill the following click for touch but not mouse. So (b) is the house pattern in both files.
- **[SCOPE+ `tests/test_player_base_css.py`]** Unavoidable and it would have been a gate red: that module's FROZEN census includes `pointer-events` and is measured on the public player, which serves this same `admin.css`. **One field of one row at each width** was edited (`04 div puzzle-player-tool-menu`, `auto` -> `none`), by the property's index in `PROPS` rather than by counting pipes, and `PROVENANCE` now records that CARD-426 edited one field rather than re-recording. The run before the edit named exactly that one difference at both widths and no other, rectangles included — which is also the measurement that the rule moves no layout. **Open for the reviewer:** CARD-423 established that this table can be *certified* against the pinned Bootstrap (sha256 `7f1d37f0…`, the file `src/nonogram/admin/templates/base.html` pins, fetchable any time) by running with `NONOGRAM_REAL_BOOTSTRAP` so the module's own sha-matched assert proves the table equals the real file's live measurement. A one-field edit is cheaper and plausibly equivalent — `admin.css` is in both compared trees — but "plausibly equivalent" is not the same as certified, and this board has a standing preference for the measurement over the argument.
- **[Net tests] +1 node id against a target of 0**, with a stated reason: no existing cell owns "the menu's open/closed state under pointer input", and folding it into `test_one_button_with_a_menu` (the group's shape) or `test_menu_lists_the_four_brushes_in_order` (the menu's contents) would have misnamed both. A reviewer may disagree; it is the owner's budget, so the disagreement belongs in the review rather than in a silent fold.
- **[Read, not run]** `tests/test_puzzle_editor_ui.py` — `puzzle_edit.html` loads the same `solver.js` and opens the same menu; its menu cells only open and read items, none drives an outside pointer-down. Named here so the gate's selection is checked against it rather than trusting the read.
- **[Build gate] DEFERRED, with the reason.** The derived selection for a `solver.js` + `admin.css` change takes the full-suite lock, and CARD-425 still has an agent working in its own worktree — the lock's guard refuses every pytest from a worktree while a foreign worktree holds it, so running the gate now would break that agent's runs at `pytest_configure` rather than merely contend. The gate runs once the other worktrees are idle, and this card does not close without it.

- [Review 1/3] Score: 6.5 — forge:review, `overall_verdict: fail`, `task_contract_verdict: pass`, `system_contract_verdict: fail` (57 rules: 7 ✓, 49 ⚠ — 46 `no_eligible_fact` and 3 `stale_check` — and **1 ✗, ADR-0039/R1**). **1 critical, 1 important**, 3 minor, 2 out-of-scope. Report `meta/review/20261111T164551Z-CARD-426-cycle1.yml`.
- **[Severity gate]** FAIL.
- **[Review 1/3] the critical is the same frozen-census class CARD-428 hit, from the other direction.** This card's genuinely NEW node id (`TestSolverBrushMenu_AnOutsidePointerDownDismissesIt::test_an_outside_pointer_down_closes_it_and_the_board_stays_reachable[chromium]`) is unrecorded in `ADDED_SINCE_BEFORE`, so `tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured` fails — measured, `1 failed in 1.76s`. `impact_set.py` selects that module (1 of this diff's 146 files) and `wave_close_marker.py` lists the class under `controls`, so the merge gate runs it. **Here `ADDED_SINCE_BEFORE` is the right table** (CARD-428's was a rename, which belongs in `RENAMED_SINCE_BEFORE` and was instead undone). The card's Verification table could not see it because the guard deliberately lives in the one module not named `test_puzzle_solver_*`. Briefing this was mine to do and I did not.
- **[Review 1/3] the important finding is the best of the day: an existing cell's only control was silently disarmed.** `tests/test_puzzle_solver_maybe.py::test_menu_left_open_closes_on_solve` is the only cell pinning CARD-194 target behaviour #12 (the solved lock closes the menu). It opens the menu and reaches the solve through `_solve_and_measure`'s `_cell(page, *LAST).click()` — and that click's pointerdown now fires the new dismissal, so the cell's closing assertions hold whether or not `refresh()`'s `if (locked) closeMenu()` exists. The premise is not inferred: **this diff's own new cell asserts that a mouse press-and-release on a board cell at 1440x900 closes the menu with the board unsolved** — exactly the event `_solve_and_measure` sends. Ran green (2 passed), i.e. green and non-discriminating, and the module is in the derived selection so the gate reports it green too. `violates: ADR-0039/R1` — a claim whose control cannot fail is narrative, not coverage. It is also a co-change peer absent from the diff (10 of the last 120 commits touching the two production files).
- **[Review 1/3] the FROZEN question is answered: CERTIFY, it costs 26 seconds.** `NONOGRAM_REAL_BOOTSTRAP=<sha-verified copy> pytest tests/test_player_base_css.py` → 3 passed in 25.4 s, the sha-matched branch taken and `differences(FROZEN[width], live) == []` asserted at both 390 and 1280 against a second tree serving the real Bootstrap. So the one-field edit is measured, not argued, and no re-record is owed. The reviewer also checked the field is the right one by position in `PROPS` (5th from the end), and that the four `player-tool-item` rows already carried `auto`, which is why the explicit `auto` moves nothing. **Adopted as the standing answer: any one-field FROZEN edit gets this certification.**
- **[Review 1/3] decision (b) verified safe on both halves I asked about.** `closeMenu()` writes only `menu.hidden` and the trigger's `aria-expanded` — no `gesture`, `pinch`, `zoom`, `lastClick` or history state — and the menu is out of flow, so `cellUnder()` sees unchanged geometry and no stroke starts in a leftover state. A pinch whose first touch lands on the transparent box does not mark: the first touch is recorded with its start cell, the second finger takes the `touchPoints.size === 1` branch, `beginPinch()` reverts the preview and nulls `gesture`. **Pre-diff was worse**: the box ate the first touch, so the second finger became a lone marking gesture.
- **[Review 1/3] net +1 is right, and the reviewer found the only home a fold could have had** — not either cell the implementer considered, but `TestSolverBrushMenu_Keyboard::test_escape_closes_and_tab_leaves`, the cell that owns "the ways out of the menu". It does not work: that class is keyboard-only on the single 1280x720 fixture, cannot host two viewports or a touch context, and AC-4 requires it unchanged. +1 stands.

### [OWNER RULING 2026-11-11] the menu's own chrome swallows the tap

Asked how a near-miss on the menu's own chrome (its 8 px padding ring, the 4 px gaps between options) should behave now that the box is transparent, the owner chose: **"Chrome should swallow the tap."** A tap on the menu's own chrome closes the menu and does nothing else; only a tap clear of the box marks.

**This is NOT a reversal to decision (a), and the option text I offered overstated the cost.** (a) would have made *every* outside tap non-acting, needing `preventDefault` + `stopPropagation` on a document capture listener — which also stops the stage's own `pointerdown` (pinch bookkeeping, crosshair) and kills the following click for touch but not mouse. That is not what the ruling asks for. The ruling separates the two halves of this card's fix, and the resolution is to **keep the JS half and revert the CSS half**:

- `admin.css`: drop `pointer-events: none` from `.player-tool-menu` (and the paired `auto` on `.player-tool-item`, which only existed to undo it). The box is hit-testable again, so a tap on its chrome lands on the menu and never reaches the board.
- `solver.js`: keep the document capture-phase `pointerdown` dismissal exactly as it is. It fires on any pointer-down outside the trigger and the menu — including one that lands *on* the box — so the menu still closes.

The resulting behaviour, which is what the owner described: a tap on the chrome **closes the menu, marks nothing**; a tap clear of the box **closes the menu and marks**; the trigger still toggles; Escape unchanged.

**The one consequence to state rather than discover:** with the box opaque again, a tap on a cell that lies *under* the box closes the menu without marking that cell — the reader taps again to mark it. On the admin page this is moot (measured: no cell centre is under the box at any viewport). On the **public** page cells genuinely are under it, so there a first tap closes and a second marks. That is the cost of the ruling and it is the ordinary behaviour of a menu, which is what the owner asked for.

**What this costs in tests, honestly:** the claim reverses, so `TestSolverBrushMenu_AnOutsidePointerDownDismissesIt`'s three `_MENU_HIT_TEST` points — which currently assert the box answers the hit test with what lies under it — must assert the opposite (the box answers for itself, the items answer for themselves), and the card's AC-3 is rewritten to the ruling. The dismissal half (AC-1, AC-2) and the Escape half (AC-4) are untouched. `tests/test_player_base_css.py`'s FROZEN field goes back to `auto`, which is a second one-field edit and gets the 26-second real-Bootstrap certification the cycle-1 reviewer established as routine.

**Queued, not dispatched:** a fix round for cycle 1's findings was already in flight when this ruling arrived, and it was explicitly told not to touch `pointer-events`. This ruling is dispatched as its own round once that one lands, so the two do not collide in the same files.
