# CARD-211: Region leaves the brush menu and becomes its own control

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/211-region-own-control
**Worktree:** ../PythonProject4-CARD-211
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (item 2: "Solver please place "Region" select option separately from "Black\\White\\Maybe\\Undecided" dropdown")
**Idea:** —
**Wave:** 37
**Depends on:** —
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_brush_menu.py, tests/test_puzzle_solver_page.py, tests/test_admin_design_tokens.py
**Review score:** —
**Started:** 2026-10-14T05:31:26Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- CARD-194 collapsed the brushes into **one** trigger button plus a
  `role="menu"` of **five** `role="menuitemradio"` items:
  `Black`, `White`, `Maybe`, `Undecided`, `Region`
  (`puzzle_solve.html:109-113`). Region is therefore a radio *among the
  brushes*, although it is not a brush: it is a modifier on how the next drag
  behaves.
- The trigger's label reflects both: its visible text is the chosen brush, or
  `Region · <brush>` with Region on; its `aria-label` is `Brush: <chosen>`
  (template comment, `puzzle_solve.html:21-24`).
- Behaviour today: with Region on, a drag (any pointer type) marks with the
  chosen brush and **Region turns itself off once that drag is recorded**; with
  Region off, a mouse drag still marks, while touch/pen drags scroll the page.
  `.player-board.is-region` switches the cells' `touch-action`
  (`admin.css:557`).

**What changes.** Region becomes a control of its own, outside the menu:

1. The brush menu holds exactly four items — `Black`, `White`, `Maybe`,
   `Undecided`. The trigger shows the chosen brush and its `aria-label` stays
   `Brush: <chosen>`.
2. A separate **Region** toggle button sits beside the brush trigger in the same
   `player-slot` row: `aria-pressed="true|false"` (a toggle, not a radio — it is
   a mode, and `aria-pressed` is what a screen reader announces as on/off),
   focusable in the same tab order, labelled `Region`.
3. The semantics are **unchanged** from CARD-194: turning Region on makes the
   next drag mark with the current brush on any pointer type, and Region turns
   itself off once that drag is recorded (the toggle's `aria-pressed` flips back
   with it). Do not take the opportunity to make it sticky — that is a separate
   owner decision, not this card's.
4. `.player-board.is-region` keeps driving `touch-action`; the toggle is now the
   single thing that sets it.
5. Keep the state logic in the pure module and the DOM wiring in `solver.js`
   (ADR-0038/R4): "is Region armed" is state, the button is rendering.

## Acceptance criteria

- **AC-1** (happy): *Given* the player page, *when* the brush menu is opened,
  *then* it holds exactly four `menuitemradio` items (Black, White, Maybe,
  Undecided) and no Region item. (test:
  `TestSolverBrushMenu_HoldsFourBrushesOnly`)
- **AC-2** (happy): *Given* the player page, *when* it loads, *then* a Region
  toggle button exists outside the menu, with `aria-pressed="false"`, reachable
  by keyboard in the toolbar's tab order. (test:
  `TestSolverBrushMenu_RegionIsItsOwnToggle`)
- **AC-3** (happy): *Given* Region is pressed, *when* the player drags along a
  row with the Black brush, *then* every cell of the drag is marked black, and
  afterwards the toggle reads `aria-pressed="false"` again. (test:
  `TestSolverRegion_ArmedDragMarksThenDisarms`)
- **AC-4** (happy): *Given* Region is not pressed, *when* a touch drag starts on
  a cell, *then* nothing is marked and the page scrolls (today's behaviour).
  (test: `TestSolverRegion_UnarmedTouchDragStillScrolls`)
- **AC-5** (happy, brush independence): *Given* any brush is selected, *when*
  Region is pressed and released, *then* the selected brush is unchanged — the
  two controls do not overwrite each other. (test:
  `TestSolverRegion_DoesNotChangeTheBrush`)
- **AC-6** (edge, announcements): *Given* a screen reader, *when* Region is
  pressed, *then* the state change is announced through the existing
  `#puzzle-player-announce` live region, not by a label the user must re-read.
  (test: `TestSolverRegion_AnnouncesItsState`)

## Guardrails

- G-1: Hand-written JS/CSS only — no framework, no build step, no vendored
  library (ADR-0038/R1).
- G-2: Marking, undo/redo, error count, percent, hints and resume keep working
  exactly as they do (tests: `test_puzzle_solver_marking.py`,
  `test_puzzle_solver_progress.py`, `test_puzzle_solver_resume.py`,
  `test_puzzle_solver_hint.py`).
- G-3: No request per mark — the board stays client-side (ADR-0038/R2; test:
  `TestSolverMarking_NoRequestPerMark`).
- G-4: Styling from the design tokens only, no hard-coded colours or sizes
  (test: `TestAdminDesignTokens_NoRawValues`).
- G-5: Do not change the clue rendering or the phone fit/mirror behaviour —
  CARD-212 owns those this wave.

## System contract

- ADR-0038/R1 — the player's client is hand-written JS/CSS served as static
  files; no framework, build step or vendored library (check: review-lens)
- ADR-0038/R4 — the player's state logic lives in a pure module with no DOM
  access, separate from rendering (check: review-lens)
- ADR-0038/R2 — no network request per mark (check:
  `TestSolverMarking_NoRequestPerMark`)
- CON-021 — interactive play exists only as the admin panel's player, behind the
  admin door (check: review-lens)

## Architecture context

- **FR:** FR-044 (the admin panel's puzzle player).
- **ADR:** ADR-0038 (the player's client architecture) — R1, R2, R4.
- **CON:** CON-015, CON-016 (the admin door), CON-021.
- **Components:** COMP-009 (admin panel: template, static JS/CSS).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** the admin panel's own `static/tokens.css` +
  `static/admin.css` (there is no `meta/design/` in this repo) — every value
  comes from a token, as `TestAdminDesignTokens_NoRawValues` enforces.
- **UI components:** the player toolbar (`.player-toolbar`, `.player-slot`,
  `.player-tools`) — the Region toggle is a new control in the existing row;
  reuse the `.btn.btn-outline-secondary` pattern the history buttons use.
- **Screens:** `/puzzles/<id>/solve` (`puzzle_solve.html`).
- **Standards:** the toggle must carry its state in `aria-pressed`, be
  keyboard-reachable, and keep the 44 px tap target CARD-182 established on a
  390 px phone.

## Worktree notes

- [Env] forge 2026.8.17 (project declares no `forge.min_version`; no `.skills.yml` here)
- [Dispatch] wave 37, started 2026-10-14T05:31:26Z. Slot freed by CARD-214's merge (`d49e73a`);
  CARD-204 still holds the other slot (owner's concurrency cap of 2). Conflict edges
  honoured: CARD-212 (solver.js, admin.css, puzzle_solve.html — overlap 0.50) and
  CARD-216 (same template and statics) stay queued while this runs.

- [Implementation complete] 2026-10-14 — committed `814854d` (10 files, +939/-236).
  Orchestrator-verified: `meta/` clean; full suite **6910 passed, 9 skipped, 0 failed,
  `PYTEST_EXIT=0`** (main was 6883/9, so +27 tests and none removed).
  Region is now `#puzzle-player-region`, a `.btn.btn-outline-secondary` toggle with
  `aria-pressed`, sibling to the brush trigger inside `.player-tools`; the menu holds
  exactly four `menuitemradio` items and CARD-194's `Region · <brush>` composite label
  is gone. Semantics unchanged, as the brief required. `solver_state.js` gained
  `nextRegion(armed, event)` — the flag's whole transition table, `RangeError` on
  anything else, following `stepZoom`'s precedent — and `gesturePaints(pointerType,
  armed)`, so the state lives in the pure module (ADR-0038/R4) while `solver.js` keeps
  the button.
- [Correction, mine] My brief told it to keep "CARD-182's 44 px tap target". **That
  rule does not exist in this repo** — verified: `tokens.css` sets `--control-h: 36px`
  and the player's own standard is `TestSolverZoom_TapTargetsAreAtLeast24px` (WCAG 2.2
  2.5.8). The agent flagged it instead of silently building to a number it could not
  reach, and asserted the toggle at >= 24 px square and exactly as tall as Undo.
  Reaching 44 px would be a panel-wide `--control-h` change, i.e. a token decision, not
  this card's.
- [Scope] four SCOPE+ test files beyond `Touches:`, all shared player-test
  infrastructure rather than new territory: `test_puzzle_solver_marking.py` (it owns the
  shared helpers — `MENU_ORDER` 5->4, new `_region*` helpers, `CONTROLS` gains
  "Region"), `_maybe.py` (asserted the five menu names; its reachability sweep counted
  trigger + five items), `_zoom.py` and `_phone.py` (two `_tool(page, "Region")` calls
  each). No production file outside `Touches:` changed.
- [Layout consequence, caught by an existing test] Adding an ~80 px control to
  `.player-tools` pushed "Progress: 0%" off the counters' row at 1280 px, observed red
  in `TestSolverPercent_SitsNextToTheCounters`. Fixed by moving `min-width: 13rem` from
  `.player-tool-trigger` to `.player-tools` — it was always the solved banner's slot
  constraint (CARD-186) — so `.player-slot` is exactly its old 208 px for every brush,
  now pinned by a new regression test at 1280/1440/390 px x Black/Undecided. Worth
  noting for CARD-212/216: that group now has ~4 px of slack on the 1280 px row.
- [Open owner question, raised by the agent and NOT decided in the worktree] Picking a
  brush still turns Region off (CARD-194's own behaviour #3). With Region now a separate
  control that is arguably surprising — two independent controls that still interact.
  Kept exactly as CARD-194 shipped it, because the brief said semantics stay and a
  change is the owner's call; it is now explicit (`nextRegion(armed, "brush")`) and
  tested rather than accidental. Making them fully independent is a one-line change
  (drop the `"brush"` event and `setRegion`'s call in `pick()`). Routed to the owner.
- [Review] cycle 1 starting 2026-10-14.

- [Notes sync 2026-10-14] agent notes pulled one-way from the worktree copy,
  verbatim:

  ### What shipped

  Region left the brush menu and became `#puzzle-player-region`
  (`[data-player-region]`), a `.btn.btn-outline-secondary` toggle carrying
  `aria-pressed`, placed as the brush trigger's sibling **inside**
  `.player-tools`, right after the `role="menu"` div. The menu now holds four
  `menuitemradio` items. **No semantics changed**: arming Region still makes the
  next drag mark with the current brush on any pointer type, Region still
  disarms itself the instant a drag is recorded (even one that changes no
  cell), a mouse drag with Region off still marks, a touch/pen drag with Region
  off still scrolls, a tap with Region on is still a click that leaves Region
  armed, and the brush click-cycling (CARD-189) is untouched.

  Placing the toggle inside `.player-tools` (rather than as a second child of
  `.player-slot`) was deliberate: `.player-slot > * { grid-area: 1/1 }` stacks
  its children, so a sibling there would have been drawn on top of the solved
  banner, and `.player-toolbar.is-solved .player-tools { visibility: hidden }`
  is what takes the toggle out of reach while the board is locked — where
  there is nothing left to mark.

  ### State vs. rendering (ADR-0038/R4)

  CARD-194 kept both the flag and its rules inline in `solver.js`. Now
  `solver_state.js` owns the rules as pure functions:

  - `nextRegion(armed, event)` — the whole transition table, `event` one of
    `REGION_EVENTS` = `("toggle", "drag", "brush")`, anything else `RangeError`
    (the `stepZoom` precedent).
  - `gesturePaints(pointerType, armed)` — "does a drag by this pointer type
    mark?"

  `solver.js` keeps the flag variable and the button (`setRegion`, which writes
  `aria-pressed`, the live-region line and `.is-region` via `refresh()`), the
  same split `zoom` the percent / `stepZoom` the arithmetic already follows.
  The flag is still never recorded, never in the history and never saved, so
  every load starts disarmed.

  ### Per-AC evidence

  All in `tests/test_puzzle_solver_brush_menu.py` unless noted.

  | AC | Test |
  |----|------|
  | AC-1 | `TestSolverBrushMenu_HoldsFourBrushesOnly` (`test_menu_lists_the_four_brushes_in_order`, `test_no_region_item_is_left_in_the_menu`) |
  | AC-2 | `TestSolverBrushMenu_RegionIsItsOwnToggle` (`test_it_is_a_pressed_state_button_outside_the_menu`, `test_tab_reaches_it_between_the_trigger_and_undo`, `test_space_and_enter_press_it`, `test_it_keeps_a_tap_target_and_the_toolbars_button_pattern_on_a_phone`) |
  | AC-3 | `TestSolverRegion_ArmedDragMarksThenDisarms` (mouse/Black, real CDP touch/White, and a drag that changes no cell) |
  | AC-4 | `TestSolverRegion_UnarmedTouchDragStillScrolls` (CARD-194 AC-6's CDP touch drag, moved here; nothing `defaultPrevented`, `pointercancel` fires, nothing marked) |
  | AC-5 | `TestSolverRegion_DoesNotChangeTheBrush` (parametrised over all four brushes: text, `aria-label` and the checked item all survive a press+release; plus "a region drag still paints the chosen brush") |
  | AC-6 | `TestSolverRegion_AnnouncesItsState` (press/unpress wording, it is the player's existing `#puzzle-player-announce` and not a second live region, the brush label never mentions Region, the automatic disarm is announced, and a solving drag lets the banner win the one live region) |

  Also added: `TestRegionRules_PureFunctions` — the two new `solver_state.js`
  exports exercised directly (truth table written out by hand, bad event →
  `RangeError`), modelled on `TestZoomArithmetic_PureFunctions`;
  `tests/test_admin_design_tokens.py::test_the_region_toggles_pressed_look_comes_from_tokens`
  (G-4: every value in the `.player-region` rules is a `var(--token)`).

  ### The one layout change the card needed

  Adding an ~80 px control to `.player-tools` broke
  `TestSolverPercent_SitsNextToTheCounters::test_shares_the_buttons_row_at_1280`
  (observed red: "Progress: 0%" dropped off the counters' row, `pt 186.8` vs
  `eb 185.4`). Fix, in `admin.css`:

  - `min-width: 13rem` moved from `.player-tool-trigger` to `.player-tools`.
    It was always a constraint on the *slot* width (what the solved banner
    takes over, CARD-186); on the trigger it only coincided with the group
    while the trigger was the group's only content. On the group, the slot
    keeps exactly its old 208 px.
  - `.player-region` takes the trigger's narrower side padding
    (`var(--space-2)`, like `.player-zoom .btn`), so the widest brush label
    ("Undecided", 124 px) + the toggle (72 px) + the gap = 204 px still fits
    under 13rem — i.e. the slot is 208 px for *every* brush, so picking a
    wider brush never nudges the board sideways either.

  Pinned by `TestSolverBrushMenu_RegionIsItsOwnToggle::test_adding_it_leaves_the_tools_slot_at_its_old_width`
  (1280/1440/390 px × Black/Undecided, slot == tools == 208 px).

  ### Template comment block

  The CARD-194 paragraph was replaced by three: the brush dropdown (now four
  items, trigger text is the brush alone), the Region control (where it lives,
  why `aria-pressed` and not `aria-checked`, the Tab order trigger → Region →
  Undo, the two `.player-tools > button` children, hidden-when-solved), and
  the unchanged semantics (one-shot disarm, `.is-region` → `touch-action`,
  brush-pick disarms, announcements through `#puzzle-player-announce`). The
  usage paragraph under the board (`#puzzle-player-hint`) was reworded to name
  the Region control instead of a fifth menu item. `solver.js`'s header got a
  new `region` entry beside `menu`, and `admin.css`'s two player comments were
  updated for the group's new shape.

  ### Judgement call, for the owner

  **Picking a brush still turns Region off** (CARD-194 target behaviour #3),
  kept as shipped. Before this card the menu's radio exclusivity forced it;
  with two independent controls it is arguably surprising — press Region, then
  change your brush, and Region silently disarms. AC-5 only asks for the other
  direction (pressing Region never changes the brush), which holds, and the
  brief says a behaviour change here is an owner decision. So the rule is now
  explicit (`nextRegion(armed, "brush")`) and tested
  (`TestSolverBrushMenu_Region::test_picking_a_brush_turns_region_off`,
  `test_re_picking_the_same_brush_also_turns_region_off`) rather than
  accidental. **If the owner wants the two fully independent, it is a one-line
  change**: drop the `"brush"` event from `nextRegion` and the `setRegion` call
  in `pick()`.

  Also noted: the brief asked for "CARD-182's 44 px tap target". No such
  threshold exists in this repo — `--control-h` is 36 px and the player's own
  tap-target test is `TestSolverZoom_TapTargetsAreAtLeast24px` (WCAG 2.2
  2.5.8's 24 px). The toggle is asserted ≥ 24 px square and exactly as tall as
  Undo, so it cannot drift from the toolbar's height; reaching 44 px would mean
  changing `--control-h` for every button in the panel, which is a design-token
  decision, not this card's.

  ### For CARD-212 and CARD-216

  - `.player-tools` now has **two** direct `<button>` children (trigger,
    Region) with the menu `<div>` between them. Selectors scoped to
    `.player-tools > button` (used in `test_puzzle_solver_percent.py` and
    `test_puzzle_solver_maybe.py`) see both — they were already written as set
    operations and needed no change, but new ones must not assume one.
  - The toolbar Tab order is now **Brush → Region → Undo → Redo → Reset →
    Hint**; `CONTROLS` in `tests/test_puzzle_solver_marking.py` lists it.
  - `MENU_ORDER` (same file) is four names. `_tool(page, "Region")` no longer
    works — use the new `_region(page)` / `_region_pressed(page)` /
    `_region_toggle(page)` helpers, also in that file.
  - `.player-slot` is still exactly 208 px (13rem), but the minimum now lives
    on `.player-tools`, not `.player-tool-trigger`. Anything added to that
    group eats into the 1280 px counters row — there were ~4 px of slack
    before this card and there are ~4 px now.
  - `#puzzle-player-announce` has a third writer (`setRegion`), alongside the
    solved banner and hints; `setRegion` writes before `commit`, so a stroke's
    own announcement wins.

  ### SCOPE+

  The card's `Touches:` lists four test files; these four more had to change
  because they import the shared player helpers or assert the five-item menu:

  - `SCOPE+ tests/test_puzzle_solver_marking.py` — owns the shared helpers:
    `MENU_ORDER` (5 → 4), new `_region*` helpers, `CONTROLS` (+ "Region"),
    the `[data-player-tool]` count, the reworded usage paragraph, and one
    `_tool(page, "Region")` call.
  - `SCOPE+ tests/test_puzzle_solver_maybe.py` — asserted the five menu names,
    and its solved-board reachability sweep counted "the trigger plus the five
    menu items"; now the trigger, four items and the toggle.
  - `SCOPE+ tests/test_puzzle_solver_zoom.py` — two `_tool(page, "Region")`
    calls.
  - `SCOPE+ tests/test_puzzle_solver_phone.py` — two `_tool(page, "Region")`
    calls (AC-13's `touch-action` check is one of them).

  No production file outside the card's `Touches:` was changed.

  ### Test runs

  - `tests/test_puzzle_solver_brush_menu.py` + `_percent.py` +
    `test_admin_design_tokens.py`: 67 passed.
  - The other player files (`_marking`, `_maybe`, `_progress`, `_hint`,
    `_resume`, `_zoom`, `_phone`, `_mirror`, `_clues`, `_page`): 323 passed.
  - Full suite: **6910 passed, 9 skipped, 0 failed**, `PYTEST_EXIT=0`
    (16:59). Main was 6883 passed / 9 skipped, so this card adds 27 tests and
    removes none.

  Committed as `814854d` on `card/211-region-own-control` (explicit
  pathspecs; nothing under `meta/` staged).

- [Owner decision 2026-10-14] **Make the two controls independent: picking a brush
  must NOT turn Region off.** This reverses CARD-194's behaviour #3, which made sense
  only while Region was one of five items in a single dropdown (selecting another item
  naturally replaced it); with Region a separate toggle, two independent-looking
  controls that silently interact is the wrong behaviour. The change is to drop the
  `"brush"` event from `nextRegion`'s transition table and the `setRegion` call in
  `pick()`, and to pin the new behaviour with a test (the existing
  `TestSolverRegion_DoesNotChangeTheBrush` covers the converse direction; this needs
  its mirror — picking a brush leaves `aria-pressed="true"` and the next drag still
  marks).
  Note for whoever implements it: this is now a DELIBERATE divergence from CARD-194's
  shipped semantics, so the brief's "semantics stay unchanged" rule no longer covers
  this one transition — update the transition table's own docstring and the template's
  comment block to say which card decided what, or the next reader will read it as
  drift. Folded into the fix cycle that follows review cycle 1 rather than run as a
  cycle of its own.
