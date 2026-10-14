# CARD-211: Region leaves the brush menu and becomes its own control

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/211-region-own-control
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (item 2: "Solver please place "Region" select option separately from "Black\\White\\Maybe\\Undecided" dropdown")
**Idea:** —
**Wave:** 38
**Depends on:** —
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_brush_menu.py, tests/test_puzzle_solver_page.py, tests/test_admin_design_tokens.py
**Review score:** 9.0/10 (cycle 1/3) — 0 critical, 0 important, 3 minor; gate does not block
**Started:** 2026-10-14T05:31:26Z
**Closed:** 2026-10-14T09:16:08Z
**Actual:** 0.5d
**Merge commit:** 4790243
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
   **AMENDED 2026-10-14 (owner decision, decompose station):** one transition is now a
   DELIBERATE divergence — picking a brush no longer turns Region off. Everything else
   in this item still holds. The divergence is recorded in five places in the code,
   the template and the tests; this sentence was the one place still contradicting it,
   which the AC/EC gate caught.
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
- **AC-7** (happy, the other direction — **ADDED at the decompose station 2026-10-14**,
  owner decision): *Given* Region is pressed, *when* the player picks any brush from the
  menu — including re-picking the one already selected — *then* Region stays pressed
  (`aria-pressed="true"`), nothing is re-announced, and a drag afterwards marks with the
  newly picked brush before disarming. Added because the owner's 2026-10-14 decision made
  the two controls independent, and the AC/EC gate found that AC-5's closing clause ("the
  two controls do not overwrite each other") had come to assert more than its own *when*
  clause covered: AC-5 is the Region→brush direction, and this is the brush→Region one.
  *test: TestSolverBrushMenu_Region::test_picking_a_brush_leaves_region_armed,
  ::test_re_picking_the_same_brush_also_leaves_region_armed*

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
  (test: `test_the_stylesheet_uses_tokens_not_literals` (and, for a rule added by a card, a per-rule check like `test_the_region_toggles_pressed_look_comes_from_tokens`)).
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
  comes from a token, as `test_the_stylesheet_uses_tokens_not_literals` (and, for a rule added by a card, a per-rule check like `test_the_region_toggles_pressed_look_comes_from_tokens`) enforces.
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

- [Review] cycle 1/3 complete 2026-10-14 — **score 9.0**, risk LOW. **0 Critical, 0
  Important, 3 Minor.** Report synced: `meta/review/20261014T063601Z-CARD-211-cycle1.yml`.
  **The behaviour survived the move, and it was proven rather than asserted: 9 mutants,
  9 killed.** The two that matter most: (1) reinstating CARD-194's own drag-path code
  (`region = nextRegion(...); refresh()` instead of `setRegion(...)`) — the exact
  stale-`aria-pressed` regression a control-move invites — killed six tests including
  both AC-3 tests and the automatic-disarm announcement, so the IMPLICIT transition is
  covered, not just the explicit one; (2) swapping `setRegion` and `commit` in the
  pointerup branch killed exactly one test, which is the whole proof that the shared
  live region's third writer cannot clobber the solved banner. `solver_state.js` has
  zero DOM references (swept for `document`/`window`/`querySelector`/`localStorage`/
  `navigator`), so ADR-0038/R4 holds and the `stepZoom`/`zoom` analogy is exact.
  The four SCOPE+ files were verified **set-wise, not by reading the diff narrative**:
  exactly two tests disappeared and both have 1:1 stronger successors; nothing was
  weakened or retargeted. The one place this project's historical failure mode could
  have hidden — `maybe.py`'s reachability sweep, where `[False] * 6` stays 6 by
  coincidence (trigger + 5 items becomes trigger + 4 items + toggle) — is clean.
  The layout fix's reading of CARD-186 was confirmed by `git log -S`: CARD-194 added the
  `min-width`, and its own comment already attributed it to CARD-186's banner invariant.
  The new matrix has teeth in both axes — putting the min-width back on the trigger kills
  all 6 cells plus the pre-existing percent-row test, and restoring default padding on
  the toggle kills exactly the three Undecided cells and survives all three Black ones,
  so the brush axis is load-bearing rather than decoration.
  Guardrails G-1..G-5 all hold (and `TestSolverMarking_NoRequestPerMark` was confirmed
  LIVE at `marking.py:1188`, not a dead ref — this project has several of those).
  457 tests green in 4 targeted batches. System contract: 53 rules, 7 hold, 46 unchecked,
  0 violated. **Coverage gap stated plainly by the reviewer:** the visual dimension was
  not exercised (`review.visual: off`), so the pressed look, the trigger's new width and
  the 390 px toolbar are established geometrically and by token identity — never by eye.
- [Severity gate] 2026-10-14 — no Critical and no Important, so the gate does not block.
  The reviewer's approve condition is a human one: **F-003's measurements shown to the
  owner before merge** (done 2026-10-14). F-001/F-002 are one-line comment fixes and
  explicitly need not gate.
- [F-003, the one finding worth the owner's eye] The layout fix left the brush trigger
  **variable-width**: measured at 1280 px, 83.7 px with "Black" and 123.8 px with
  "Undecided", where it was a fixed 208 px before this card. `.player-tools` and
  `.player-slot` stay exactly 208 px — so the card's slot claim is right — but the
  group's INTERIOR is invisible to the new test, and because `.player-tools` left-packs,
  **the Region toggle's left edge slides ~40 px when the brush changes** — immediately
  after the interaction that precedes arming it. Breaks no AC, guardrail or rule, and
  the narrower trigger may be an improvement; the gap is in the evidence, and the card's
  own notes read as if nothing moved. Routed to the owner with both measurements.
- [Minor, RC-1 pair] Two stale comments, both one-liners: `solver.js:1003`'s Tab-case
  comment still says focus lands on "Undo" when it now lands on Region (the file's own
  header block WAS updated, so solver.js currently states both answers ~900 lines
  apart), and `tests/test_puzzle_solver_marking.py:742`'s docstring points at
  `TestSolverBrushMenu_Touch`, which this diff renamed.
- [For CARD-212 / CARD-216, from the review] The diff reflows large comment blocks in
  all three shared files, which is exactly where a clue-rendering or phone-mirror card
  will collide; one `admin.css` reflow left an over-long line that invites a second
  cosmetic re-wrap and a second conflict; `.player-tools` is now declared twice (lines
  591 and 633, harmless but one more place to look); and ~4 px of slack remains on the
  1280 px counters row, so anything either card adds to `.player-tools` lands red in
  `test_shares_the_buttons_row_at_1280`.
- [Out of scope, logged for later] Arming Region and then solving by a click leaves
  `.is-region` (and `touch-action: none`) on a locked board, so a touch user cannot pan
  the solved board until they undo. **Identical under CARD-194** via the menu item —
  pre-existing, not introduced here. Also: `--color-focus` is byte-identical to
  `--color-accent`, so the pressed toggle's focus ring reads as a thin page-coloured gap
  between two accent bands; a pre-existing token decision that already applies to every
  checked button in the panel.

- [Fix 1 complete] 2026-10-14 — committed `207831d` (`meta/` clean, verified).
  **Both owner decisions done, each with teeth proven by restoring the old behaviour.**
  (1) Independence: `nextRegion`'s `"brush"` event and `pick()`'s `setRegion` call are
  gone, and `"brush"` is now one of the REFUSED event names — stronger than silently
  dropping it, because a caller left behind fails loudly instead of disarming. The two
  tests that pinned the old coupling were **converted, not deleted**, and the conversion
  is better than the obvious one: it does not stop at `aria-pressed="true"` (which would
  pass over a cleared flag) but drags afterwards and asserts the cells take the newly
  picked brush, then disarm. Mutant B1 (restore the call + the event) fails exactly 3
  tests and nothing else.
  (2) The width pin: `.player-tool-trigger { flex: 1 0 auto }`. **It rejected the
  obvious implementation with measurements**, which is why there is no raw value and no
  new token: the `ch` route (`min-width: 9ch`, following `.player-zoom-readout`'s idiom)
  needs a value inside [8.60ch, 9.08ch] at `1ch = 9.508 px`, so `9ch` sits 0.7 px under
  the group's floor and a font substitution would push the group past 208 px and red the
  counters' row. `flex` cannot overflow — it only consumes free space. The
  design-tokens test is untouched and green.
  **The slide is now 0 px**, measured across all four brushes x three viewports: the
  trigger was 83.7 / 89.2 / 92.1 / 123.8 px and is now 128.3 px for every brush; the
  toggle's offset was 91.7 / 97.2 / 100.1 / 131.8 px and is now 136.3 px for every
  brush. `.player-slot` and `.player-tools` stay exactly 208.0 px in all twelve cells
  before and after. The review's requested assertion landed as a **12-cell matrix**
  (4 brushes x 3 viewports, up from 6), and cycle 1's M8 mutant now kills all 12 cells
  where it killed only 3 — the matrix got strictly stronger in both axes.
  The deliberate CARD-194 divergence is recorded in **five** places, each naming both
  cards and the date, including the template block that used to open "The semantics are
  CARD-194's, unchanged".
  Both stale one-liners fixed (RC-1).
- [Build gate] 2026-10-14 — branch suite **6915 passed, 9 skipped, 1 failed**. **The one
  failure is not this card's, and the agent proved that rather than asserting it:**
  `tests/test_web_upload.py::...::test_the_page_reports_success_and_names_the_written_file`
  compares `_uploaded_temp_files()` before and after, and that helper globs
  `nonogram-upload-*` in the **machine-wide** `tempfile.gettempdir()`. The extra entry
  belonged to CARD-205's concurrently-running suite (it located the foreign pytest PID).
  Re-run in isolation: the class is 2 passed, the file 9 passed. Counts reconcile
  exactly: 6915 + 1 = 6916 = this branch's 6910 baseline + the 6 new matrix cells.
  Nothing in this diff is reachable from the upload path. The merge gate will re-run the
  suite on the rebased tree with nothing else running, which is the real check.
- [Rebase hygiene, from the agent] It deliberately did NOT collapse the duplicate
  `.player-tools` declaration, and reflowed no existing comment line in any production
  file except the template paragraph it had to rewrite — so CARD-212/CARD-216 inherit
  the conflict surface the review warned about and nothing more.
- [Note for merge] The CHANGELOG entry must say that **picking a brush no longer turns
  Region off** — item (1) is a user-visible behaviour change, not just a control move,
  and CARD-194's own entry describes the dropdown world it replaces.
- [AC/EC check] 2026-10-14 — gate spawned. It has not run on this card yet (same gap as
  CARD-204 and CARD-214 had), so `done` would refuse without it.

- [Notes sync 2026-10-14, post-Fix-1] agent notes pulled one-way from the
  worktree copy, verbatim:

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

  ### [Fix 1] 2026-10-14 — the two owner decisions and the RC-1 comment pair

  Review cycle 1 scored 9.0 with no Critical and no Important findings, so the
  gate did not block; this cycle carries the two owner decisions recorded above
  plus F-001/F-002. Four production files and three test files changed. **Do
  NOT read this block as "CARD-211 kept CARD-194's semantics" — item 1 below
  deliberately breaks one of them, and that is the owner's decision, not drift.**

  #### 1. Owner decision — the brush and Region are now independent in BOTH directions

  `nextRegion`'s `"brush"` event and `pick()`'s `setRegion(nextRegion(region,
  "brush"))` call are gone. `REGION_EVENTS` is `["toggle", "drag"]`;
  `nextRegion`'s body (`event === "toggle" ? !armed : false`) is unchanged, and
  so are `RangeError` on an unknown event and `Object.isFrozen(REGION_EVENTS)`.
  `"brush"` is now one of the *refused* names, which is stronger than silently
  dropping it: a caller left behind fails loudly instead of disarming.

  **Two tests were CONVERTED, not deleted** (they were the two mutant M9 killed,
  and they pinned CARD-194's behaviour):

  | was | is | now asserts |
  | --- | --- | --- |
  | `TestSolverBrushMenu_Region::test_picking_a_brush_turns_region_off` | `::test_picking_a_brush_leaves_region_armed` | after `_region()` + `_tool("White")`: `aria-pressed="true"`, the live region still says "Region on: …" (nothing re-read, because `setRegion` is never called), **and the drag that follows marks the five cells WHITE and only then disarms** — the attribute alone would pass over a cleared flag, so the drag is what proves it is still armed |
  | `::test_re_picking_the_same_brush_also_turns_region_off` | `::test_re_picking_the_same_brush_also_leaves_region_armed` | re-picking the brush already chosen does not disarm either, and its drag still marks Black |

  `TestSolverRegion_DoesNotChangeTheBrush` (AC-5, the converse direction) is
  untouched and green — the two classes are now each other's mirror, which is
  what "independent in both directions" means in tests.

  `TestRegionRules_PureFunctions::test_next_region_covers_every_event_from_both_states`
  asserts the REAL domain, not a stale one: the four surviving combinations
  (`toggle`/`drag` × armed/disarmed), `REGION_EVENTS == ["toggle", "drag"]`,
  `Object.isFrozen`, and three refusals — `'press'`, `''` and now `'brush'`.
  The two `brushFrom*` rows are gone because the event is gone.

  **Where the deliberate divergence is recorded** (the point being that the next
  reader meets it wherever they enter):

  - `solver_state.js` — a `DELIBERATE DIVERGENCE from CARD-194, decided by the
    owner on 2026-10-14 (CARD-211)` paragraph in `nextRegion`'s own docstring,
    naming why CARD-194 was right at the time (Region was a fifth
    `role="menuitemradio"`, so the menu's radio exclusivity forced the disarm)
    and why CARD-211 is right now, and ending "anything still saying a brush
    pick disarms Region is stale".
  - `solver.js` — the header block's `region` entry, and `pick()`'s own comment
    beside the call that is no longer there.
  - `puzzle_solve.html` — the comment block's semantics paragraph, which used to
    open "The semantics are CARD-194's, unchanged" and now opens "CARD-194's
    with ONE deliberate divergence".
  - `tests/test_puzzle_solver_brush_menu.py` — the module docstring (which also
    said "nothing about what it does"), `TestSolverBrushMenu_Region`'s class
    docstring (including the fact that the two tests were converted rather than
    dropped), `TestSolverRegion_DoesNotChangeTheBrush`'s cross-reference and
    `TestRegionRules_PureFunctions`'s.

  **Teeth (mutant B1).** `setRegion(nextRegion(region, "brush"))` put back in
  `pick()` with `"brush"` back in `REGION_EVENTS`: `3 failed, 41 passed` —
  exactly the two converted tests and the pure truth table, nothing else.
  Restored by copying back pre-captured file copies, never `git checkout`.

  #### 2. Owner decision — the brush trigger's width is pinned, so the toggle stops moving (F-003)

  `admin.css`: `.player-tool-trigger { flex: 1 0 auto; … }`. The trigger is the
  group's only growable child (the menu is absolutely positioned out of flow),
  so it takes the whole of the 13rem `.player-tools` reserves less the toggle
  and the gap — **grow into the free space, never shrink below the label**. That
  states the fix as a relation rather than a measured number, which is why it
  needs no new token and cannot trip `test_admin_design_tokens.py` (its
  `.player-region` rule-body check and the file-wide hex sweep are both
  untouched, and both still pass): there is no raw value to express. The
  alternative considered was `min-width: 9ch` on `.player-tool-trigger-text`,
  following `.player-zoom-readout`'s `min-width: 4ch` idiom — rejected on
  measurement: `1ch` is 9.508 px and the usable window is [8.60ch, 9.08ch], so
  `9ch` sits 0.7 px under the group's floor and a font substitution would push
  the group past 208 px and red the counters' row. `flex` cannot overflow.

  **Measured before/after** (throwaway Playwright probe over all four labels ×
  390/1280/1440 px, written, run and deleted — the tree is clean; `regionΔ` is
  the toggle's left edge measured from `.player-tools`' own left edge, so it is
  viewport-independent):

  | brush | trigger BEFORE | trigger AFTER | regionΔ BEFORE | regionΔ AFTER |
  | --- | --- | --- | --- | --- |
  | Black | 83.7 px | **128.3 px** | 91.7 px | **136.3 px** |
  | White | 89.2 px | **128.3 px** | 97.2 px | **136.3 px** |
  | Maybe | 92.1 px | **128.3 px** | 100.1 px | **136.3 px** |
  | Undecided | 123.8 px | **128.3 px** | 131.8 px | **136.3 px** |

  Identical at 390, 1280 and 1440 px (only the group's page position differs:
  `.player-tools` left is 16 px at 390 px and 260 px at 1280/1440 px, so the
  toggle's absolute left edge was 107.7/113.2/116.1/147.8 px at 390 px and
  351.7/357.2/360.1/391.8 px at 1280 px, and is now 152.3 px and 396.3 px for
  every brush). **The 40.1 px slide between Black and Undecided is 0 px.**
  `.player-slot` and `.player-tools` are still exactly 208.0 px in all twelve
  cells, before and after, so the counters' row is untouched —
  `TestSolverPercent_SitsNextToTheCounters::test_shares_the_buttons_row_at_1280`
  and the one-row check in `test_puzzle_solver_maybe.py` are green unedited.

  **The assertion the review actually asked for.** F-003's gap was the evidence,
  not the CSS, so `test_adding_it_leaves_the_tools_slot_at_its_old_width` now
  pins the group's INTERIOR as well as its width: `round(trigger) == 128` and
  `round(regionΔ) == 136`, and its brush axis went from `["Black", "Undecided"]`
  to `MENU_ORDER` — **a 12-cell matrix (4 brushes × 3 viewports), up from 6**, so
  "it holds for all four labels" is asserted rather than argued.

  **Teeth (mutant W1).** `flex: 1 0 auto` deleted: **all 12 cells fail**, and the
  other four tests in the class still pass (the mutant is localised to the width
  claim). The pre-existing mutants still bite too — `min-width: 13rem` back on
  the trigger, or the toggle's default padding, fail as cycle 1's M7/M8 recorded,
  and M8's Black cells now fail on the trigger width as well as its Undecided
  cells on the group width, so the matrix got strictly stronger in both axes.

  #### 3. F-001 / F-002 — the stale one-liners

  - `solver.js` `case "Tab"`: `— Undo.` → `— Region (then Undo), since CARD-211
    put the toggle between the trigger and the history buttons`, matching the
    header block ~900 lines up that already said it.
  - `tests/test_puzzle_solver_marking.py` `test_a_touch_drag_marks_one_line`:
    the dangling `TestSolverBrushMenu_Touch` → `TestSolverRegion_UnarmedTouchDragStillScrolls`.

  #### Deliberately NOT done

  - **`.player-tools` stays declared twice** (`admin.css`, the flex/gap rule and
    the `min-width: 13rem` rule). Collapsing them would move the 20-line comment
    block that explains the 13rem, and CARD-212/CARD-216 are queued on this exact
    file with comment reflow already flagged as their likeliest conflict. The new
    `.player-tool-trigger` comment is a NEW block inserted between the two
    existing rules, so no existing comment line was reflowed in any of the four
    production files this cycle.
  - The two items cycle 1 logged as out of scope (the solved-board
    `.is-region`/`touch-action` lock, identical under CARD-194, and
    `--color-focus` being byte-identical to `--color-accent`). Neither is this
    card's.
  - Clue rendering and the phone mirror (G-5, CARD-212) and given cells
    (CARD-216).

  #### Test runs

  - `tests/test_puzzle_solver_brush_menu.py` + `test_admin_design_tokens.py`:
    **51 passed** (45 at cycle 1 — the +6 are the width matrix going from 6 to
    12 cells; no test was dropped).
  - The other player files (`_percent`, `_marking`, `_maybe`, `_zoom`, `_phone`,
    `_clues`, `_mirror`, `_page`): **262 passed**, unedited apart from
    `_marking`'s two docstring lines.
  - Full suite on this branch (NOT rebased, as instructed): **6915 passed,
    9 skipped, 1 failed in 19:38** — and the one failure is not this card's:
    `tests/test_web_upload.py::TestWebUpload_ConvertsUploadedImageThroughSamePipeline::test_the_page_reports_success_and_names_the_written_file`.
    Its last assertion compares `_uploaded_temp_files()` before and after, and
    that helper globs `nonogram-upload-*` in the MACHINE-WIDE
    `tempfile.gettempdir()`; the extra entry it found
    (`nonogram-upload-o_u51yn6`) belongs to another worktree's suite running
    concurrently on this host (CARD-205's full run was in flight; this run was
    queued behind it, and the CARD-214 watchers were still polling). Re-run in
    isolation: that class **2 passed**, the whole file **9 passed**. Nothing in
    this diff is reachable from the web upload path — it is four player files
    and two player test files. Pre-existing host-shared-state fragility in that
    test, worth a backlog line, not a defect introduced here.
  - Counts line up exactly: the branch baseline at `814854d` was 6910 passed /
    9 skipped; 6915 + 1 = 6916 = 6910 + the 6 new matrix cells. (Main has since
    moved to 6938 with CARD-204, but this branch is deliberately un-rebased.)

  Committed as `207831d` on `card/211-region-own-control` (explicit pathspecs;
  nothing under `meta/` staged).

- [AC/EC check] 2026-10-14 — **All criteria/constraints ✓.** 6 ACs, 5 guardrails, both
  owner decisions, CON-021 and ADR-0038/R1..R6 all evidenced. 412 targeted tests green
  across five batches; mutation checks run in a throwaway clone of the branch, never the
  worktree.
  The gate re-proved the teeth itself rather than citing the fix cycle: deleting the
  pointerup `setRegion` fails all three AC-3 tests plus two announcement tests; forcing
  `gesturePaints` to `return true` fails AC-4 and the truth table; swapping `setRegion`
  and `commit` fails **exactly** the solved-banner ordering test and nothing else;
  restoring the `"brush"` call fails exactly the two converted tests and the truth table;
  deleting `flex: 1 0 auto` fails **all 12** matrix cells and leaves the class's other
  four tests green. It also verified R4 by grep (`solver_state.js` contains no
  `document`/`window`/`querySelector`/`localStorage`/`navigator`), and CON-021 by
  construction rather than by sampling — `TestAdminAuth_EveryRouteIsBehindTheCredential`
  walks `app.url_map.iter_rules()`, so the solve route and every future route are
  covered.
  It settled the `1 failed` claim independently: `_uploaded_temp_files()` globs the
  machine-wide `tempfile.gettempdir()` unscoped to its own run, so a second worktree's
  suite is counted as this test's leak; isolated, the file is 9 passed; and the diff
  contains **zero Python production files**, so nothing in it is reachable from the
  upload path. Backlogged.
- [Decompose station] 2026-10-14 — three card-text defects the gate found, all mine,
  all fixed here: **AC-7 added** for the brush→Region direction (AC-5 was accurate but
  had come to cover a direction its own *when* clause did not); the "semantics are
  unchanged from CARD-194" sentence in `## What to implement` amended, since it was the
  one place still contradicting the five places in code that record the divergence; and
  **G-4's `TestAdminDesignTokens_NoRawValues` was a test I invented** — it exists
  nowhere at HEAD or on main. Corrected to the real checks here AND in CARD-212 and
  CARD-216, which carried the same fabricated name and would have handed it to their
  agents. Same class as the dead `check:` refs already logged against the architecture
  model in `backlog.md`: a plausible-looking test name that no gate can run.

- [Merge gate] 2026-10-14 — **PASSED** on the rebased tree: **6971 passed, 9 skipped,
  0 failed, `PYTEST_EXIT=0`**, read in its own command before the merge. The
  `test_web_upload.py` temp-dir test passed here, consistent with the fix cycle's
  diagnosis that its earlier failure was a concurrent worktree's suite and not this diff.
- [Merge guard] main had advanced since the branch took it in; verified
  `git diff 7ec9a77..HEAD -- src/ tests/ docs/ pyproject.toml` is EMPTY (the intervening
  commits are card notes under `meta/`), so the tested tree is the tree merged.
- [Done] 2026-10-14 — merged as `4790243` (`--no-ff`). Worktree removed, branch deleted,
  review report in `meta/review/`. Actual 0.5d against a 0.5d estimate — the move
  itself was small; the span is two owner decisions, a review cycle, a fix cycle and a
  verification gate.
  **Unblocked by this merge:** CARD-212 (clues on both sides) and CARD-216 (given cells
  in the player), both of which were queued on this card's template and statics. They
  inherit the rebase surface the review mapped: reflowed comment blocks in all three
  shared files, `.player-tools` declared twice, and ~4 px of slack on the 1280 px
  counters row — anything either card adds to that group reds
  `test_shares_the_buttons_row_at_1280`.
