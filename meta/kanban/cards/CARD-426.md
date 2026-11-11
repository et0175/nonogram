# CARD-426: The brush menu hangs: an outside tap neither closes it nor lets Escape close it, and it swallows taps on the board

**Status:** done
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
**Review score:** 9.0 (cycle 2)
**Started:** 2026-11-11T18:05:00Z
**Closed:** 2026-11-11T20:15:00Z
**Actual:** 2 review cycles + 3 rounds (fix, owner ruling, ruling resolution), wall clock excluded per the owner's ruling
**Merge commit:** 1fbec7b3
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
- **AC-3** (the chrome swallows the tap) — **REWRITTEN 2026-11-11 by the owner's ruling**, which withdrew the claim this criterion used to make. It read: *"with the menu open, a tap on a cell under the menu's box behaves as the decision in step 2 says — and in neither case does the tap do nothing"*, with the Playwright interception message named as what must stop happening. The owner ruled the box keeps the pointer, so that message is now **correct behaviour** and the old criterion is retired. The claim is: with the menu open, a pointer-down on the menu's own chrome (its padding ring or an inter-item gap) closes the menu, leaves the brush unchanged and marks nothing; a pointer-down on an item picks that brush; a pointer-down clear of the box closes the menu and marks. (test: `tests/test_puzzle_solver_brush_menu.py::TestSolverBrushMenu_AnOutsidePointerDownDismissesIt::test_an_outside_pointer_down_closes_it_and_the_board_stays_reachable`, the chrome-tap block at 1440x900, with the points handed over by the hit-test snippet so taps and assertions cannot drift; plant: widen the exemption back to `#puzzle-player-tool-menu` and that block reds first and alone. Desktop-only, and the reason is measured not convenient: at 390x844 Chromium's touch adjustment retargets two of the three chrome points onto the nearest option, so "the brush is unchanged" is unprovable on touch — marks were unchanged at every touch point.)
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

### [Fix round] review cycle 1 (score 6.5: 1 critical, 1 important, 3 minor)

The dismissal mechanism, the ACs and decision (b) were not revisited — the
reviewer verified each on every question asked, decision (b)'s safety against
the pinch and stroke paths included. Commit `d6e47fc9`, three explicit
pathspecs (`solver.js`, `tests/test_browser_fixture_scope.py`,
`tests/test_puzzle_solver_maybe.py`), message through `-F`. Nothing under
`meta/` staged (INV-023).

**F-001 (critical) — the new node id is now recorded.** One
`ADDED_SINCE_BEFORE` entry in `tests/test_browser_fixture_scope.py`, in the
dict's existing shape, attributed to CARD-426 and naming AC-1..AC-3, with the
`[chromium]` suffix as part of the id. `ADDED_SINCE_BEFORE` is the right table
because this node is genuinely new: nothing was renamed, so
`RENAMED_SINCE_BEFORE` and the board's G-T rule ("no test deleted, renamed,
skipped or weakened to fit") are not in play. Before the entry the reviewer
measured `1 failed in 1.76s`; after it, both the control and the attribution
cell pass together:

```
pytest "tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured" \
       "tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_every_allowlist_entry_is_attributed_and_not_already_recorded" \
       -o addopts= -rEfs
-> 2 passed in 1.45s
```

The second node is the one the reviewer warned a *rename* in `ADDED` would
trip; a genuine addition does not trip it, measured above.

**F-002 (important) — `test_menu_left_open_closes_on_solve` discriminates
again.** It is the only cell pinning CARD-194 target behaviour #12, and it
reached the solve through `_solve_and_measure`, whose last step is
`_cell(page, *LAST).click()` — a pointer-down this card's own new cell asserts
closes the menu by itself. It now drives the solve with no pointer event at
all: `_set(browser_page, _solution_cells(GRID, U))` (`setBoard` commits and
refreshes, so `refresh()`'s `if (locked) closeMenu()` runs), then
`_is_solved_shown`, then the two closing assertions it already carried.
`_solve_and_measure` is untouched — its two other callers measure boxes and
need the real click.

The repair is proved discriminating, not asserted to be: with
`if (locked) closeMenu()` commented out of `refresh()` in `solver.js` (one
plant, restored afterwards), the SAME node was run in both forms —

| form of the cell | with the solved lock removed |
| --- | --- |
| repaired (`_set` + `_solution_cells`) | **1 failed** — `assert False is True`, `menu.hidden` is False |
| as shipped at `fd2e94fe` (`_solve_and_measure`) | **1 passed** — vacuous, exactly as F-002 says |

**F-004 (minor, taken).** `solver.js`'s header `menu` entry enumerated only
Escape, Tab and a pick as the ways out; it now names the fourth (a
pointer-down outside the trigger and the menu, not consumed, so the same tap
acts on what it hit) and points at the listener for the reasoning. The added
lines are all `//` comments carrying neither `editing` nor `publicMode`, so
`test_puzzle_editor_ui.py`'s two mode censuses — which strip `//` lines before
counting — are unmoved.

**F-005 (minor) — attempted, then dropped, and the measurement is why.** The
suggested arm was built: inside the existing cell's 1440x900 arm, a 10x10
`live.store` (`_unique_grid(10, 10, seed=426)`), the overlapping cell found by
intersecting the live rects rather than written down, then one tap asserting
both halves. It reds, and not on the geometry: the overlap is real
(`under=(0, 0)`, box at x 260, y 185.78, 160 x 174) and the menu does close,
but `_marked(_states(page)) == {}` — nothing is marked. Probed at that exact
point, `document.elementFromPoint` answers
`['BUTTON', 'player-tool-item', 'unknown']`: the cell's centre lies under the
*Clear* item, so that tap is a menu PICK, which closes the menu and marks
nothing. The composite F-005 asks for is therefore reachable only where the
cell's centre falls on the box's own chrome — its padding ring or an
inter-item gap — which is precisely the behaviour F-003 reports and which is
with the owner for a ruling. Asserting it now would pin behaviour that may be
reverted, so the arm was reverted instead (the module is byte-identical to
`fd2e94fe`) and no node id was added. F-003's `pointer-events` pair, the
card's decision note and the chrome itself were left exactly as they were.

### SCOPE+ (fix round)

`SCOPE+ tests/test_browser_fixture_scope.py` — the browser family's census,
and a gate red without it: the new node sits inside
`FAMILY_PREFIX = "tests/test_puzzle_solver"`, `impact_set.py --against main`
selects the module, and `wave_close_marker.py` lists
`TestBrowserFixtures_NoTestAddedOrRemoved::*` under `controls` rather than
`marked`, so the merge gate runs it. Same class as the
`tests/test_player_base_css.py` entry above: a frozen registry the card's own
`Touches:` does not reach.

`SCOPE+ tests/test_puzzle_solver_maybe.py` — F-002's repair; the module owns
CARD-194 target behaviour #12 and this diff changed that cell's premise.

### Verification (fix round; narrowed, never the gate)

All runs `-o addopts= -rEfs` against the main checkout's venv (a card worktree
has none). The full suite, `make test-gate` and every impact-scoped substitute
were NOT run: the orchestrator owns the gate and its 146-file selection, and
the full-suite lock was not taken (two other worktrees have agents in them).

| set | result |
| --- | --- |
| the two `test_browser_fixture_scope.py` control nodes | **2 passed** (1.45 s) |
| `…maybe.py` `…brush_menu.py` `test_browser_fixture_scope.py` | **118 passed**, 0 failed, **0 skipped** (169 s) |
| `node --check src/nonogram/admin/static/solver.js`, `py_compile` on both edited test modules | clean |

### Net test count (fix round)

**Still +1 collected node id — now a *recorded* +1.** No node id was added or
removed this round: `ADDED_SINCE_BEFORE` gains a registry row for the node
already shipped at `fd2e94fe`, F-002 rewrites the body of an existing cell
without touching its name or its class, F-004 is a comment, and F-005's
candidate arm (which would have cost no node id either) was reverted whole.

### [Orchestrator] the chrome ruling's scope, narrowed by measurement

The fix round attempted cycle 1's optional minor (assert AC-3's two halves together on a geometry where a cell lies under the box) and **dropped it with a measurement rather than skipping it** — which changes what the owner's chrome ruling actually touches.

Built at 1440x900 on a 10x10 grid, the overlap is real (`under=(0,0)`, box at x 260, y 185.78, 160x174) and the menu closes, but no cell is marked. Probed at that exact point, `document.elementFromPoint` answers `['BUTTON', 'player-tool-item', 'unknown']`: **the overlapping cell's centre lies under the Clear item, so the tap is a menu PICK** — it closes the menu and marks nothing.

So decision (b)'s pass-through is **not** the whole 160 x 174 panel. Most of the box's area is items, which take `pointer-events: auto` and swallow the tap into a brush pick. The pass-through is confined to the box's own **8 px padding ring and the 4 px gaps between options** — a thin frame. The card's decision note implies something broader, and that is now corrected here.

**What this means for the owner's ruling ("chrome should swallow the tap"), which stands:** it lands precisely on the surface that misbehaves and nothing else, and the implementation is still the one recorded above — revert the CSS half, keep the JS half. Two consequences to state rather than discover:

- With the box back to `pointer-events: auto`, a tap landing on the **ring or a gap** closes the menu and marks nothing (the ruling). A tap landing on an **item** picks that brush and closes the menu (unchanged either way). A tap **clear of the box** closes the menu and marks (unchanged).
- The only behaviour that changes is the ring and the gaps, so the three `_MENU_HIT_TEST` points — all of which are deliberately on the chrome, not on items — are exactly the assertions that reverse. That is a tidy coincidence: cycle 1's reviewer chose those points to prove the box was transparent, and they are the same points that now prove it is opaque.

The round also left cycle 1's F-005 `open` rather than closing it, correctly: its composite is reachable only on the chrome, which is the surface the ruling changes, so pinning it now would pin behaviour about to be reverted.

### [Owner ruling round] 2026-11-11, "chrome should swallow the tap"

Implemented. The round was **raised as a `[BLOCKER]` first and finished after
the orchestrator authorized the one change its brief had forbidden**; both
halves are recorded below, because the false premise came from the brief and
the record should not be silent about where the error originated.

#### The blocker, as raised

**The CSS revert alone does not deliver the ruling: a tap on the menu's own
chrome does NOT close the menu.** The round's brief rested on
"the document capture-phase `pointerdown` dismissal still fires on any
pointer-down outside the trigger and the menu — including one that lands *on*
the box". That is false by the listener's own selector and by measurement:
the dismissal in `solver.js` exempts the menu as well as the trigger
(`event.target.closest("#puzzle-player-tool-trigger, #puzzle-player-tool-menu")`),
and the comment beside it says why the menu is exempt — "their click is the
pick, and closing here would hide the button before it arrives". Once the box
keeps the pointer, `event.target` for a chrome point IS the menu, so the
exemption matches and `closeMenu()` is never reached.

Measured in this worktree with the CSS revert applied, admin solve page, the
family's 15x15 `GRID`, recording the real `pointerdown` target on a capture
listener rather than inferring it:

| viewport | chrome point | `pointerdown` target | after the tap |
| --- | --- | --- | --- |
| 1440x900 (mouse) | left padding | `div.player-tool-menu` | **expanded=true, menu open**, brush Black, nothing marked |
| 1440x900 (mouse) | bottom padding | `div.player-tool-menu` | **expanded=true, menu open**, brush Black, nothing marked |
| 1440x900 (mouse) | gap items 0/1 | `div.player-tool-menu` | **expanded=true, menu open**, brush Black, nothing marked |
| 390x844 (touch) | left padding | `div.player-tool-menu` | **expanded=true, menu open**, brush Black, nothing marked |
| 390x844 (touch) | bottom padding | `button.player-tool-item` | closed, **brush Black -> Clear**, nothing marked |
| 390x844 (touch) | gap items 0/1 | `button.player-tool-item` | closed, **brush Clear -> Black**, nothing marked |

So on the desktop all three chrome points re-open this card's own defect on
the chrome — the menu hangs, with Escape out of reach because the tap moved
focus — and on the phone two of the three are retargeted by Chromium's touch
adjustment onto the nearest option, which closes the menu by *picking a
different brush*. Neither is "closes the menu and does nothing else".

The touch retargeting is not new and not this round's: the items have always
been hit-testable, and cycle 1's F-005 measured the same snap (a cell centre
under the box answering `['BUTTON', 'player-tool-item', ...]`). The desktop
hang IS new to the revert.

#### The resolution (authorized by the orchestrator, which verified the
#### selector itself before answering rather than taking the report's word)

**`solver.js`'s dismissal exemption narrowed from the box to its options:**
`closest("#puzzle-player-tool-trigger, .player-tool-item")`. An item's
pointer-down stays exempt, so the pick still survives to its click; a chrome
pointer-down now reaches `closeMenu()`, and because the BOX was the event's
own target the board never sees the tap — so it closes the menu and does
nothing else, which is the ruling. One selector, no `preventDefault`, no
`stopPropagation`: not decision (a), and the stage's own `pointerdown` (pinch
bookkeeping, the crosshair) and the click behind a tap are reached exactly as
before. `solver.js` was in scope for this change only; the header `menu`
entry cycle 1's F-004 corrected described the fourth way out as "a
pointer-down anywhere outside the trigger and the menu", which the narrowing
makes imprecise, so that phrase names the four options and the chrome now —
the same correction, in the one other place the card's story is told.

**The behaviour is now asserted, not only the hit test.** The defect above
was one the whole suite was green over, because the cell asserted what
`elementFromPoint` answers and never what a tap does. The same cell now taps
each of the three chrome points at 1440x900 — the points handed over by the
hit-test snippet itself, so the two cannot drift — and asserts the menu
closed, `aria-expanded="false"`, `aria-label` (the brush) unchanged and the
marks unchanged. Desktop only, by the measurement in the table above.

**Planted.** With the exemption widened back to `#puzzle-player-tool-menu`
(one plant, restored; `node --check` clean after), the new block reds on the
first chrome point and nothing else does:

```
AssertionError: ('1440x900', [262, 212.78125])
assert False
 +  where False = is_hidden()   # <Locator selector='#puzzle-player-tool-menu'>
```

**The ruling's stated limit on a phone, recorded as information (the
orchestrator is reporting it to the owner, not asking).** At 390x844 two of
the three chrome points are retargeted by Chromium's touch adjustment onto
the nearest option, so in the padding ring and the gaps a thumb gets the
NEAREST BRUSH rather than nothing (measured: bottom padding Black -> Clear,
gap 0/1 Clear -> Black; the left padding point is not snapped and behaves as
on the desktop). The snap predates this round — cycle 1's F-005 measured the
same thing against a cell centre — it is the browser's and not this code's,
and what it produces is a menu action rather than a board action, which is
the half the owner objected to. Not fixed, not asserted; the cell says so
where it limits the new block to the desktop.

**Chrome vs items, re-derived at both viewports (the measurement that says
how narrow the ruling's surface is).** The box is 160 x 174 px at both — 390x844:
box at (16, 256.08), four items at x 25, w 142, h 36, tops 265.08/305.08/345.08/385.08;
1440x900: box at (260, 185.78), items at x 269, w 142, h 36, tops 194.78/234.78/274.78/314.78.
Box 27 840 px2, the four items 20 448 px2 = **73.4 %**, leaving **26.6 %
(7 392 px2)** of chrome — the 8 px padding ring and the three 4 px gaps —
identical at both viewports. The pass-through the ruling removes was never
the whole panel: most of it was already a pick.

**The three reversed hit-test points.** `_MENU_HIT_TEST`'s `dead` list is
renamed `chrome` (a dict key inside the JS snippet, not a node id) and its
three points — `box.x+2` at item 0's vertical centre, `box.bottom-3`, the
midpoint of `items[0].bottom..items[1].y` — now assert **`[True, True, True]`**:
`document.elementFromPoint` answers `div.player-tool-menu` at each, i.e. the
box answers for itself and never names a cell. Measured at both viewports
(table above). The four item-centre points keep asserting `[True, True, True, True]`
(each option answers for itself). The old claim is retired in the cell's
docstring and beside the constant, in the board's form (`RETIRED CLAIM,
2026-11-11 (CARD-426, the owner's ruling "chrome should swallow the tap")`),
with the new claim asserted in the same cell; the class and the method keep
their names (G-T, and a rename would move the id CARD-217's census records).

**CSS.** `.player-tool-menu`'s `pointer-events: none` and
`.player-tool-item`'s paired `pointer-events: auto` are both gone — the
second only ever undid the first, and the item rows already carried `auto` in
the frozen census, so removing it moves nothing (certified below). The long
CARD-426 `pointer-events` comment block, which explained a rule that no
longer exists, is replaced by a short note recording that the box keeps the
pointer by the owner's 2026-11-11 ruling and why.

**The prose beside the dismissal.** Two lines described the deleted CSS rule
("the box takes the pointer nowhere, so the tap reaches the cell at all");
they now say what is true — a tap clear of the box closes and marks, a tap ON
the box is the box's own event, so the board never sees it and all it does is
close the menu — naming the owner's ruling and pointing at
`.player-tool-menu`'s comment in `admin.css` for it. The exemption's own
paragraph says which elements are exempt and why the box deliberately is not.

**The frozen census goes back, and is certified.**
`tests/test_player_base_css.py`'s `FROZEN` carries `pointer-events` for
`04 div puzzle-player-tool-menu` at both widths; `none` -> `auto`, edited by
the property's index in `PROPS` (field 30 of 34, derived from the module's own
tuple — never by counting pipes). Both rows are now byte-identical to their
pre-CARD-426 form (`diff` against `fd2e94fe^`). `PROVENANCE["recorded"]` now
records what CARD-426 finally left — the table as it found it — rather than
what it set in passing. Certified against the real Bootstrap (sha256
`7f1d37f0…96c2a`, verified with `shasum -a 256`, matching `PROVENANCE`), so
the fidelity cell takes its sha-matched branch and asserts
`differences(FROZEN[width], live) == []` at 390 and at 1280:

```
NONOGRAM_REAL_BOOTSTRAP=…/bootstrap-423/bootstrap.min.css \
  pytest tests/test_player_base_css.py -o addopts= -rEfs
-> 3 passed in 26.11s      (re-run on the final tree; 25.95s on the first)
```

**The census control, and the net node-id change.** No id was added or
removed: the flip edits one cell's body and docstring, the rename is a JS
dict key, and no test was added, renamed, skipped or weakened.

```
pytest "…brush_menu.py::TestSolverBrushMenu_AnOutsidePointerDownDismissesIt::test_an_outside_pointer_down_closes_it_and_the_board_stays_reachable" \
       "…test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured" \
       "…::test_every_allowlist_entry_is_attributed_and_not_already_recorded" -o addopts= -rEfs
-> 3 passed in 3.09s
```

**Still +1 collected node id**, as recorded in `ADDED_SINCE_BEFORE` — the
control above is the measurement.

**Verification (narrowed, never the gate).** All runs `-o addopts= -rEfs`
against the main checkout's venv (a card worktree has none).

| set | result |
| --- | --- |
| `…brush_menu.py` `…maybe.py` `test_player_base_css.py` `test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved` | **96 passed**, 0 failed, **0 skipped** (133.89 s) |
| the same census module under `NONOGRAM_REAL_BOOTSTRAP` (certification) | **3 passed** (26.11 s) |
| the cell alone, with the exemption widened back (plant) | **1 failed**, on the chrome-tap block |
| `tests/test_kanban_review_record.py`, alone, after each card edit | 68 passed |
| `node --check` on `solver.js`, `py_compile` on both edited test modules | clean |

`…maybe.py` is in the set because `solver.js` changed again: F-002's repaired
`test_menu_left_open_closes_on_solve` is the one cell outside this module
that reads the menu's open/closed state, and it is green. A static check
rather than a broad run for the rest: no test anywhere clicks
`#puzzle-player-tool-menu` itself (the editor's menu cells click items, which
stay exempt), and the lines added to `solver.js` are `//` comments carrying
neither `editing` nor `publicMode`, so `test_puzzle_editor_ui.py`'s two mode
censuses — which strip `//` lines before counting — are unmoved.

The full suite, `make test-gate` and every impact-scoped substitute were NOT
run (the orchestrator owns the gate and its 146-file selection), and the
full-suite lock was not taken — two peers are reviewing other cards.

**Commit.** `398bb7f9` on `card/426-brush-menu-dismiss`, four explicit
pathspecs (`admin.css`, `solver.js`,
`tests/test_puzzle_solver_brush_menu.py`, `tests/test_player_base_css.py`),
message through `-F`. Nothing under `meta/` is staged (INV-023): these notes
stay uncommitted for the orchestrator to sync. Nothing under `player/` was
touched — both changed source files are copied into the public site
byte-identically (`player/assemble.py`'s `COPIED_FROM_ADMIN`), so it
inherits the ruling with no edit of its own.

**Net test count: unchanged, still the recorded +1 collected node id.** No id
was added or removed this round: the flip and the new chrome-tap block are
assertions inside the existing cell, `_MENU_HIT_TEST`'s `dead` -> `chrome`
is a dict key in a JS snippet, and the census control
(`test_the_family_collects_exactly_what_card_217_measured`) passes, which is
the measurement rather than the claim.

Cycle 1's report is untouched: F-003 is this ruling's origin and F-005 stays
open and unbuilt. The ruling supersedes F-003.

### [Orchestrator] the ruling round's blocker was my error, and what it exposed

The first attempt at the owner's chrome ruling stopped with a `[BLOCKER]` because **my brief's central premise was false**. I wrote that the document dismissal "fires on any pointer-down outside the trigger and the menu — including one that lands on the box". It does not: the listener reads `closest("#puzzle-player-tool-trigger, #puzzle-player-tool-menu")`, so once the box keeps the pointer, a chrome point's `event.target` IS the menu, the exemption matches, and `closeMenu()` is unreachable. I verified that in the source before authorizing anything rather than taking the report's word. Measured consequence of the CSS revert alone: all three chrome points at 1440x900 left `aria-expanded="true"` and the menu hanging — **this card's own defect, reinstated on the chrome**.

The remedy was one selector: narrow the exemption to `closest("#puzzle-player-tool-trigger, .player-tool-item")`. Items stay exempt so a pick survives to its click; a chrome pointer-down reaches `closeMenu()`, and because the box was the event's own target the board never sees the tap. No `preventDefault`, no `stopPropagation`, not decision (a). Authorized with `solver.js` put back in scope for that one change.

**What the blocker exposed is worth more than the fix:** the defect was invisible to the entire suite. The cell asserted what `elementFromPoint` ANSWERS, never what a tap DOES, so a hanging menu passed every gate. The round added the behavioural assertion inside the existing cell at 1440x900 — real pointer-down/up on each of the three chrome points, asserting menu closed, `aria-expanded="false"`, the brush unchanged and the marks unchanged — with the points handed over by the hit-test snippet itself so taps and assertions cannot drift. Planted: widening the exemption back reds the new block first and alone.

**Three prose homes were stale, not the two I named.** Beyond the dismissal's two lines and its exemption paragraph, the round found the header `menu` entry — the one cycle 1's F-004 had just corrected — still saying the fourth way out is a pointer-down "outside the trigger and the menu", which the narrowing makes imprecise. It corrected it and flagged that it was outside my list. Fourth instance today of prose going stale one step behind the code.

**The ruling's limit on a phone, recorded as information:** at 390x844 Chromium's touch adjustment retargets two of the three chrome points onto the nearest option, so a thumb in the ring or a gap gets the nearest brush (bottom padding Black→Clear, gap 0/1 Clear→Black) rather than nothing; the left-padding point is not snapped and behaves as on the desktop. Not fixed and not asserted — the new block is desktop-only and its comment says why. It predates this round (cycle 1's F-005 measured the same snap) and the outcome is a menu action rather than a board action, which is the half the owner objected to.

- **[Next]** CARD-426's cycle 1 scored 6.5, below `min_score: 8`, so it owes a cycle-2 re-score before it can close — the two fix rounds and this ruling round are all unreviewed. Order: gate and merge CARD-425 and CARD-428 first (both passed at 9.0), then rebase this branch, run its cycle 2, then its gate. The reviewer and the gate cannot share the host: a gate takes the full-suite lock and the guard then refuses every pytest from a worktree.

- [Review 2/3] Score: 9.0 — forge:review, all three verdicts `pass` (57 rules: 10 ✓, 47 ⚠, **0 ✗** — cycle 1's single `ADR-0039/R1` violation repaired and plant-confirmed). **0 critical, 0 important**, 3 minor, 5 out-of-scope. Report `meta/review/20261111T183317Z-CARD-426-cycle2.yml`. **[Severity gate]** PASS, `min_score: 8` met.
- **[Review 2/3] the rebase interaction I flagged is CLEAN.** CARD-428 merged into `admin.css` while this card was in flight, and its landscape block makes the brush menu `position: fixed` and lifts it. Driven on the rebased head at 844x390, 874x402 **and 740x320** — the viewport that actually takes `openMenu()`'s lift branch (`menu.style.top = 138px`) — touch and mouse, identical in all: `chrome == [True, True, True]`, `items == [True, True, True, True]`, each chrome point closes with the brush unchanged and nothing marked, an item tap still picks, the trigger toggles, a tap clear of the box closes and marks. The lift moves the box, not who answers the hit test.
- **[Review 2/3] the headline, and it is the owner's ruling that produced it:** the whole production delta is **five lines of JavaScript**. Against the rebased merge base `admin.css` is 14 added / 0 removed and `solver.js` 48 added / 0 removed, of which 57 of 62 lines are comment — the CSS half is fully reverted, so the effective stylesheet is byte-identical to main's. The only behaviour this card ships is the document capture-phase listener with `closest("#puzzle-player-tool-trigger, .player-tool-item")`.
- **[Review 2/3] mutation check RUN** (owed on this stable cycle, deferred in cycle 1): five mutants, all killed, no survivors. The FROZEN certification came back stronger than asked — the whole of `tests/test_player_base_css.py` is **1 added / 1 removed line** against the merge base, and that line is the `PROVENANCE` comment, so both rows are byte-identical rather than merely equal in the one field.
- **[AC-3 rewritten by the orchestrator]** Cycle 2's first minor: the ruling section said "the card's AC-3 is rewritten to the ruling" and nothing had done it, in either copy — the code and the test implemented the ruling while the card's own contract text still demanded the behaviour the ruling withdrew. Rewritten above in main's copy (the worktree's is frozen by INV-023).
- **[Two minors routed to CARD-424, not fixed here]** (1) a chrome dismissal **drops focus to `<body>`** — measured at 1440x900: `closeMenu()` hides the menu around the focused item, and unlike `pick()` and Escape nothing calls `trigger.focus()`. Any fix must be scoped to the in-box case: a blanket `trigger.focus()` in `closeMenu()` would yank focus back on an ordinary board tap. (2) the exemption selector `.player-tool-item` is **globally scoped** — harmless today (six elements, all inside the menu, across both templates) but a future control reusing that class outside the box would silently stop dismissing the menu; `#puzzle-player-tool-menu .player-tool-item` is the scoped form. CARD-424 is the natural home: it already owns that class and that block.
- **[Out of scope, worth the owner's eye]** The ruling's one stated cost — on the **public** shell cells really do lie under the box, so a reader taps once to dismiss and again to mark — is reasoned from the admin geometry plus the certified census. **Nobody has seen it on the live site.** It is the first thing to look at after the next deploy.

- **[Build gate] run three times, and the third is the one that counts.** Derived selection: 149 files / 7656 tests.
  - **Run 1** (rebased onto `c902fae0`): 7654 passed, 30 skipped, **2 failed** in 34:06 — the known pre-existing `test_book_pdf_memory` red, plus `tests/test_puzzle_solver_clues.py::TestPlayerNumerals_ColumnFloorIsTheWidestColumnNumeral::test_one_digit_column_numbers_keep_the_fit`, which had appeared in no gate today.
  - **Run 2**, identical head and selection: **7655 passed**, 1 failed, 26:17 — the clues test passed, the +1 being exactly it.
  - **Run 3**, after rebasing onto the new main `e8c7b2d1`: **7655 passed, 30 skipped, 1 failed**, 26:33; run 2 of the lifted marked files 6 passed.
- **[Flaky gate member, recorded not waved through]** Before accepting run 1's extra red as transient it was chased: the test passes on main, alone on this branch, across its whole module (85 passed), and across **847 tests of the solver/player family under the lock** (14:21). Only the 149-file run ever reddened it, and the timing agrees with load — the failing run took **34:06** against the two passing runs' 26:17 and 26:33 on the same work. It measures CARD-196's column-numeral floor, a fit figure, which is the class that drifts on a busy machine. Worth a card if it recurs; one observation is not yet a pattern.
- **[Harness flaw, fixed]** Run 1's assertion numbers were lost because the gate script printed only the last 30 lines of pytest's output. It now prints every failure's full context. A red reported without its numbers is a red nobody can act on.
- **[Main moved mid-gate, and my first two merge attempts failed for a DIFFERENT reason]** Another session merged `claude/solution-one-path` into main at 19:38 (`src/nonogram/admin/book_answer_vector.py` and a vector golden fixture — disjoint from this card). I reported that as the cause of a failed merge; **it was not**. Both attempts were refused by my own uncommitted staged `meta/kanban/cards/CARD-429.md` — `error: Your local changes to the following files would be overwritten by merge` — and a `grep` filter on the merge output hid the message from me. The lesson is the filter, not the merge: never pipe a command through a pattern that can swallow its error. The rebase onto the new main was still right, and run 3 is the gate that measured what actually merged.
- **[Done]** Merged `1fbec7b3` on the gates. Estimate 1c against 2 review cycles and 3 rounds — the overrun is the owner's ruling arriving mid-card and reversing one half of the fix, which is not an estimation error but a decision that could not have been made earlier: it took the first implementation existing before the question could be asked.
