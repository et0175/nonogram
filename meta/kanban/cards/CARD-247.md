# CARD-247: The player's toolbar says what it does — "Clear" instead of "Undecided", and three cells instead of the word "Region"

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/247-player-toolbar-labels
**Worktree:** —
**Source:** owner's doc "Player", 2026-10-18 — items 1 and 2: rename "undesided" to "Clear"; the Region button should "display 3 cells (in black/dot/question mark/undecided), not word 'region'"
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_brush_menu.py, tests/test_puzzle_solver_tools.py, tests/test_admin_design_tokens.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Two toolbar changes from the owner's doc. They are one card because they share three files and
**both move the same measured, test-pinned layout** — doing them separately would mean measuring
it twice and conflicting on the way.

**1. The fourth brush is called "Clear", not "Undecided".** Today the label appears in more
places than the button, and all of them are the same claim:

- `templates/puzzle_solve.html:146` — the menu item's own text
- `templates/puzzle_solve.html:188` — the hint: "…(Black: black, white, blank; White: white,
  blank, black; **Undecided**: blank, black, white)" and "choose Black, White, Maybe or
  **Undecided**"
- `templates/puzzle_solve.html:159` — the confirm text "Every mark goes back to **undecided**"
- `static/solver.js:855` — `BRUSH_LABEL = { … [UNKNOWN]: "Undecided" }`
- the template's own header comments at `:24` and `:58`, and `admin.css`'s width notes

**Rename the user-facing label; do not rename the state.** `UNKNOWN` in `solver_state.js` is the
*model's* name for a cell with no mark, documented as "undecided" at `solver_state.js:13`, and
it is shared with the grid model and the brush ordering. This card changes what the human reads,
not what the code calls it — and `data-player-tool="unknown"` / `data-state="unknown"` stay, so
every selector and test keyed on them keeps working. If you think the model name should change
too, that is a separate card; say so, don't do it here.

**2. The Region button shows three cells instead of the word.** The owner's parenthetical —
"in black/dot/question mark/undecided" — lists the **four brush states for three cells**, so the
reading is: *three cells rendered in whatever the active brush marks with*, not one cell of each.
Region makes the next drag mark with the current brush, so a three-cell run in that brush's mark
is a picture of exactly what the control does. Implement that reading; if the owner meant
something else, it is a cheap change and the alternative is recorded here.

**Reuse `.player-swatch` — the art already exists.** `admin.css` already renders all four states:
`filled` is an ink fill, `empty` is a 28 % dot via `::after`, `maybe` is a "?" glyph, and the
default (unknown) is paper with a border. Three `.player-swatch` spans driven by the active
brush's `data-state` gives the whole icon with no new CSS art.

## Two traps, both already documented in the code

**Trap 1 — the layout is pinned by measurement and by a test, because it broke once before.**
`admin.css:676-693` records it: CARD-194's trigger was a fixed 208 px, and when that floor moved
to the group, the trigger became content-width — "measured 83.7 px for 'Black' and 123.8 px for
'Undecided', so **the Region toggle's left edge slid 40 px whenever the brush changed, right
before the hand reaches for it**." The fix was `flex: 1 0 auto`, stating the rule as a relation
instead of a number. The result is pinned by
`tests/test_puzzle_solver_brush_menu.py::TestSolverBrushMenu_RegionIsItsOwnToggle::test_adding_it_leaves_the_tools_slot_at_its_old_width`,
which asserts **the trigger's width, the toggle's offset inside the group, and the group's own
width**.

Changing the Region button from text (measured 72 px) to three swatches changes the toggle's
width, and because the trigger grows into the remaining space, it moves the trigger's width too.
So that test **will** need re-measuring. **Re-measure it with provenance; do not loosen it.**
The assertion exists because of a real regression, and a tolerance widened to make a card pass is
how that regression comes back.

**Trap 2 — replacing the Region button's text removes its accessible name.** The button's name
comes from its own text today (`puzzle_solve.html:148`). Three decorative swatches marked
`aria-hidden="true"` would leave it with **no name at all**, which a screen reader announces as
an unlabelled button — a straight accessibility regression on a control CARD-211 deliberately
gave `aria-pressed` so it would announce as on/off. Give it an explicit accessible name
(`aria-label`, or a visually-hidden span) and assert that name in a test.

## Acceptance criteria

- **AC-1** (happy, the label): *Given* the brush menu, *then* the fourth brush reads **"Clear"**,
  and no user-facing string in the player says "Undecided" or "undecided" any more — the menu
  item, the hint and the confirm text all agree. Assert over the rendered page, not one literal.
  (test: `TestSolverBrushMenu_FourthBrushIsCalledClear`)
- **AC-2** (guard, the model name is untouched): *Given* the rename, *then* `UNKNOWN`,
  `data-player-tool="unknown"` and `data-state="unknown"` are unchanged, and the brush ordering
  is still Black, White, Maybe, Clear.
  (test: `TestSolverBrushMenu_RenameDidNotTouchTheStateName`)
- **AC-3** (happy, three cells): *Given* the Region control, *then* it renders **three** cells and
  no "Region" text, and the cells carry the **active brush's** state — switching the brush to
  Black, White, Maybe and Clear changes all three accordingly.
  (test: `TestSolverRegion_ShowsThreeCellsInTheActiveBrush`)
- **AC-4** (guard, it still has a name): *Given* the Region control with its text replaced,
  *then* it has a non-empty accessible name and still carries `aria-pressed="true|false"`.
  (test: `TestSolverRegion_KeepsItsAccessibleNameAndPressedState`)
- **AC-5** (boundary, the slot does not move): *Given* each of the four brushes in turn, *then*
  the tools group is still its 13rem floor and the Region toggle's left edge **does not move
  between brushes** — the regression `admin.css` records. **State the re-measured figures** for
  the trigger, the toggle and the group.
  (test: `TestSolverBrushMenu_RegionIsItsOwnToggle::test_adding_it_leaves_the_tools_slot_at_its_old_width`)
- **AC-6** (guard, behaviour unchanged): *Given* the new label and icon, *then* Region still
  makes the next row-or-column drag mark with the brush and still turns itself off once such a
  drag is recorded, and pressing it still does **not** change the brush.
  (test: the existing Region behaviour tests, named in the notes, passing unchanged)

## Guardrails

- G-1: **Appearance only.** No change to what any brush does, to the undo history, to the
  `UNKNOWN`/`FILLED`/`EMPTY`/`MAYBE` model, or to Region's mode semantics. If a behaviour test
  changes, you have gone too far.
- G-2: The measured layout assertions are **re-measured, never loosened** (see Trap 1).
- G-3: `.player-swatch` is reused rather than reimplemented — one definition of what a cell in
  each state looks like.
- G-4: Accessibility does not regress (see Trap 2); `aria-pressed` stays.
- G-5: No new runtime dependency (ADR-0006/R1).
- G-6: No test retired without a named survivor (CARD-220's rule).

## System contract

_Assembled 2026-10-18 by `system_rules.py --card CARD-247 --root meta/architecture` (57 rules returned, `card_scope: touches`). A projection — fix the source artifact, never this list._

**Curated to 8; 49 dropped and declared.** The projection returned **57**, of which **49** are scoped `src/nonogram/**` — package-wide, so they match every card in the project and narrow to nothing. Owner decision 2026-10-17: ship the curated form (6–14 rules, kept where the rule's scope names a file this card touches or the card names the rule's artifact) with the dropped count stated. This is not a judgement that the dropped rules do not apply — it is that a ~57-rule contract measurably produces **fake** coverage on this board: reviews emitted a count line claiming all rules checked while marking 45–48 of 53 `⚠ unchecked` and writing 6–12 verdict lines, where 10- and 13-rule contracts produced full coverage. The root cause is the package-wide scoping and is tracked in `meta/kanban/backlog.md`.

- **ADR-0006/R1** — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party
  package joins the installed dependencies without revising this ADR. Non-executable static assets
  (fonts and similar data files) may ship as package data instead, and doing so is not a dependency
  change. (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- **ADR-0038/R1** — The puzzle player's client is hand-written JavaScript and CSS served as static
  files by the admin panel. There is no front-end framework, no build step, no npm toolchain and no
  vendored third-party JavaScript library. Adding any of these reopens this ADR (and ADR-0006/R1 for
  vendored code). (check: review-lens)
- **ADR-0038/R2** — Marking, undo, redo, the error count and the solved check run entirely in the
  browser. A loaded player page issues no network request per mark. (check: test:
  TestSolverMarking_NoRequestPerMark)
- **ADR-0038/R3** — The player page's clues are embedded as JSON from compute_clues of the stored
  grid (the one encoder). The client never re-derives clues from the solution. (check: test:
  TestSolverPage_ShowsTheClues)
- **ADR-0038/R4** — The player's state logic (board, strokes, undo/redo history, error count, solved
  predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-
  lens)
- **ADR-0038/R6** — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a
  puzzle's solution grid to the browser. A public or reader-facing player must not send the solution
  before the puzzle is solved, and any public phase reopens this ADR (CON-021). (check: review-lens)
- **ADR-0038/R7** — Browser tests use pytest-playwright with Chromium, declared only in a dev-only
  extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check:
  review-lens)
- **ADR-0038/R8** — Browser tests run locally, against Chromium installed by `playwright install
  chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named skip
  reason visible in the run summary. They never pass silently. Once a CI pipeline exists, it
  installs Chromium (playwright install chromium) befor… (check: review-lens)
## Worktree notes

- **[The owner's doc had a third Player item and it was empty.]** "3." is a bare number with
  nothing after it. Nothing has been invented to fill it; if the owner meant a third change, it
  needs a line and will be its own card.
- **[The owner wrote "undesided"]** in the source doc — a typo for "undecided", which is what the
  code says. The target spelling is **"Clear"**, so this only matters for grepping: search the
  code for `Undecided`/`undecided`, not for the doc's spelling.
- **[Why 0.5d and not smaller]** The two edits themselves are small. The cost is AC-5: a pinned,
  measured layout with a documented past regression has to be re-measured across four brushes,
  and that measurement is the deliverable as much as the markup is.
- **[House rules]** `hypothesis` is not in the dependency baseline. Capability modules never
  import laterally (`tests/test_cli.py` has an `ast` guard). ADR-0038/R8: browser tests fail or
  skip **loudly** with a named reason and never pass silently; ADR-0038/R7 keeps
  `pytest-playwright` in the dev-only extra.
- **[Do not take timing measurements]** Sibling cards are active; a contended number is not a
  measurement. Layout measurements are fine — they do not depend on host load.
