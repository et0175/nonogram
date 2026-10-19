# CARD-247: The player's toolbar says what it does — "Clear" instead of "Undecided", and three cells instead of the word "Region"

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/247-player-toolbar-labels
**Worktree:** ../PythonProject4-card-247
**Source:** owner's doc "Player", 2026-10-18 — items 1 and 2: rename "undesided" to "Clear"; the Region button should "display 3 cells (in black/dot/question mark/undecided), not word 'region'"
**Idea:** —
**Wave:** 48
**Depends on:** —
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_brush_menu.py, tests/test_puzzle_solver_tools.py, tests/test_admin_design_tokens.py
**Review score:** —
**Started:** 2026-10-19T15:41:00Z
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

_Assembled 2026-10-19 by `system_rules.py --card CARD-247 --root meta/architecture` (40 rules returned, `card_scope: touches`). A projection — fix the source artifact, never this list._

**Curated to 11 by rule; 29 dropped.** Curated under [`meta/kanban/curation.md`](../curation.md): keep every in-scope rule whose enforcement does not reach this card's new code, drop the rest. The kept ones are the rules **nothing executes**, plus `ADR-0039`, whose checks are tests but which declares they do not reach code written later.

⚑ **Tightened mid-flight, 2026-10-19: this contract was 16 rules an hour ago.** The model's `contexts: [CTX-001]` key was matching every card before any `code:` glob was consulted, so precisely-scoped rules behaved as package-wide. It was removed from 31 rule scopes and the authored globs became load-bearing. Only rules that do not apply to this card's files were removed — nothing that was relevant to work already done has gone.

- **ADR-0022/R1** — _nothing executes this_
  Grid extent crosses module boundaries as a (width, height) pair. No public function signature,
  request field, or export field reduces a grid's extent to a single scalar \"size\", and no
  source mode constructs a grid from one integer.
- **ADR-0036/R2** — _nothing executes this_
  Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the
  pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells
  or place grid lines itself.
- **ADR-0038/R1** — _nothing executes this_
  The puzzle player's client is hand-written JavaScript and CSS served as static files by the
  admin panel. There is no front-end framework, no build step, no npm toolchain and no vendored
  third-party JavaScript library. Adding any of these reopens this ADR (and ADR-0006/R1 for
  vendored code).
- **ADR-0038/R4** — _nothing executes this_
  The player's state logic (board, strokes, undo/redo history, error count, solved predicate)
  lives in a pure module with no DOM access, separate from rendering.
- **ADR-0038/R6** — _nothing executes this_
  Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution
  grid to the browser. A public or reader-facing player must not send the solution before the
  puzzle is solved, and any public phase reopens this ADR (CON-021).
- **ADR-0038/R7** — _nothing executes this_
  Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in
  pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — _nothing executes this_
  Browser tests run locally, against Chromium installed by `playwright install chromium`. When
  Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible
  in the run summary. They never pass silently. Once a CI pipeline exists, it installs Chromium
  (playwright install chromium) before running them; until then there is no CI, and that is a
  known gap, not a met clause.
- **ADR-0039/R1** — _declares its checks do not reach new code_
  A set a guard consults needs a completeness test written before the set, and any claim the
  guard makes about what it catches needs a control that can fail: caught WITH the set member
  present, missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and
  must be narrowed to what is measured or deleted.
- **ADR-0039/R2** — _declares its checks do not reach new code_
  A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where
  no such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE,
  never a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3.
- **ADR-0039/R3** — _declares its checks do not reach new code_
  An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT
  absorb — caught with the exemption removed, missed with it in place — is held to an equality
  against the sites that exist today, and records whatever it still cannot see as a measured
  bound with its own failing control.
- **CON-021** — _nothing executes this_
  Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served
  behind the door that guards every other admin page (CON-015, CON-016). No other surface — the
  CLI, the web UI, or any public or hosted page — offers an interactive or playable puzzle. Play
  state is never persisted on the server: no progress, marks, error count, score or solve time
  is written to a database, file or server, no network request is made per mark, and no user
  account exists for playing (CON-017). The one place play state may be kept is the browser's
  own localStorage, per puzzle, so that a puzzle reopened in that browser resumes where it was;
  it never leaves that browser. The admin player ships the puzzle's solution grid to the browser
  to compute the error count and the solved state; this is permitted for the admin panel only,
  and a public or reader-facing player must not send a puzzle's solution to the browser before
  the puzzle is solved.

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

---

### Implementation notes (agent, 2026-10-19)

- **[What shipped]** Two owner-visible changes and nothing else. (1) The fourth brush reads
  **"Clear"** in every place a human reads it — the menu item, the trigger's text, the trigger's
  `Brush: <label>` accessible name (`solver.js` `BRUSH_LABEL`), both sentences of the usage hint,
  and the reset confirmation ("Every mark is cleared. Undo brings them back."). (2) The Region
  toggle's face is **three `.player-swatch` cells in the active brush's mark** instead of the word
  "Region"; `syncTrigger` paints them from the same `tool` that writes the trigger, so the two can
  never disagree, and the button carries `aria-label="Region"` because its name used to be its text.
- **[The model name was not touched]** `UNKNOWN`, `data-player-tool="unknown"`, `data-state="unknown"`
  and `solver_state.js`'s own "undecided" wording are all unchanged — pinned by
  `TestSolverBrushMenu_RenameDidNotTouchTheStateName`, which reads the four exported constants out of
  the live module. **If the model name should change too, that is still a separate card.**
- **[AC-5, re-measured with provenance, not loosened]** Identical at 1280×720, 1440×900 and 390×844
  and for all four brushes: slot = group = **208 px** (13rem, untouched — nothing outside the group
  moved); Region toggle **64 px** (was 71.7); trigger **136 px** (was 128.3); the toggle's left edge
  **144 px** into the group (was 136), and it still does not move between brushes, which is the
  regression the block exists for. The group's content *shrank*: the widest trigger is now "Maybe" at
  92.1 px natural ("Clear" is the narrowest at 82.4, where "Undecided" was the widest at 124), so the
  content comes to 164.1 px inside the 208 px floor against CARD-211's 204. Both assertions are as
  tight as they were (two numbers, no tolerance); the toggle's own width is pinned by them as
  208 − 136 − 8.
- **[A defect the tests could not have found — caught in the render]** The first build drew the run
  with collapsed borders. `.player-swatch[data-state="filled"]` colours its border with the ink it
  fills with, so **three filled cells edge to edge are one solid black bar** — every `data-state`
  assertion was green and the owner's "3 cells" was not legible at all. Fixed by re-colouring the
  shared edge with the panel's own answer to the same question one block up in `admin.css`:
  `.guide-strip-cell`'s 28 % ink on paper. Pinned by the `seam != fill` assertion in
  `test_it_renders_three_cells_and_no_region_text` (mutant M10) — the only assertion in the file a
  correct `data-state` cannot satisfy. Renders for the owner, all four brushes plus Region armed and
  the menu open: `~/Documents/nonogram-reviews/CARD-247/`.
- **[Both pages verified — the editor is deliberately unchanged]** `static/solver.js` is shared with
  `puzzle_edit.html` (CARD-246), which offers **two** brushes and keeps its Region button as the word
  "Region" with no swatches. Nothing in this card assumes four brushes: `regionCells` is a
  `querySelectorAll` that is simply empty there, so `syncTrigger`'s loop does nothing, and
  `.player-brush-run` is a new class the editor's markup does not use, so the editor's layout is
  bit-for-bit what it was. Verified by running the whole of `tests/test_puzzle_editor_ui.py` (113
  passed) and by a render of the editor toolbar; a direct read of the editor's toggle gives
  `text="Region"`, `aria-label=None`, `swatches=0`, `aria-pressed="false"`. **Giving the editor the
  same icon is a deliberate non-decision**: it is outside this card's `Touches`, its toolbar is
  measured by CARD-246's own tests, and the owner's doc item is under "Player". If the owner wants
  the two toolbars identical, it is a cheap follow-up card.
- **[Out-of-`Touches` edits, and why each was unavoidable]** The label is a *locator* in five other
  test files, so the rename reaches them whether or not they are listed: `marking`, `maybe`, `hint`,
  `progress` and `test_puzzle_editor_ui.py`. The editor one is the important one —
  `test_the_editor_offers_only_the_two_brushes_an_answer_can_hold` asserted
  `_menu_item("Undecided").count() == 0`, which after this rename would hold for **every possible
  editor** (CARD-250's family of defect). It now asserts the label the player really shows. Also one
  Jinja comment in `puzzle_edit.html` that named the old label. **No test was retired and no test
  function was renamed** (G-6): a test method's name is part of a node id this repo guards, so
  `test_maybe_sits_between_white_and_undecided_in_the_menu` and
  `test_arrow_up_and_end_reach_undecided_the_last_item` keep their names with a note saying why.
- **[The node-id guard needed a new mechanism, and got its control]**
  `tests/test_browser_fixture_scope.py` derives the family's expected node ids from CARD-217's
  artefact plus `ADDED_SINCE_BEFORE`. That table can only ever **add**, and a label rename is not an
  addition: eight existing node ids carry the brush label in their *parameter*
  (`…[Undecided-Enter]`, `…[chromium-Undecided-1280-720]`, …), so the rename reads to the guard as
  eight removals and eight additions, and the removal half cannot be registered away. Added
  `RENAMED_SINCE_BEFORE` (`old id → (card, new id, reason)`), applied by `_recorded_node_ids` before
  anything is compared. It is a **move**, never a loss: a recorded rename whose old id is still
  collected is still red in both directions, an unrecorded one is red in both directions, and
  `_rename_problems` refuses an entry whose two sides name different test functions — which is the
  only way this table could have become a quiet way to delete coverage. Per **ADR-0039/R1 and /R3**
  the refusals are a function, not a loop inside its own test, and
  `test_the_rename_table_refuses_what_it_claims_to` drives all nine of them over tables broken on
  purpose, so none of them is a branch nothing executes. **This is the first rename on this board;
  the mechanism is general and the next one costs one entry.**
- **[System contract]** The worktree's card carried the **8-rule** curation; `main` at the time of
  writing carries the **16-rule** one re-derived under `meta/kanban/curation.md`. Judged against the
  16. In subject area and met: ADR-0006/R1 (no dependency added — three CSS lines and an HTML span),
  ADR-0038/R1 (hand-written CSS/JS, no framework, no build step, nothing vendored), /R2 (no network
  code touched; no request per mark), /R4 (the change is entirely rendering — `solver_state.js` was
  not edited at all, and the new tests read it rather than extend it), /R6 (no change to what the
  payload ships or who may see it), /R7-/R8 (new tests use the family's existing fixtures, which fail
  loudly with a named reason when Chromium is absent), CON-021 (nothing persisted, nothing served
  outside the panel's door). ADR-0039/R1–R3 were the ones that actually bit, on the rename table
  above. Out of subject area and left alone, as the card's declared residue allows: ADR-0022/R1,
  ADR-0024/R4-R5, ADR-0033/R1, ADR-0036/R2, ADR-0037/R1-R2 (grid extent, repair policy and book
  geometry — a toolbar label reaches none of them).
- **[Mutants — ten, all killed, tree restored byte-identical (sha256 compared each time)]**
  M1 `BRUSH_LABEL[UNKNOWN]` back to "Undecided" → both AC-1 tests. **M1 is the reason the sweep picks
  the fourth brush before reading the page**: with Black chosen that label is never rendered and the
  mutant survived the sweep on the first run — the claim was narrowed to what was measured and the
  test was given the one extra click that makes it true, rather than the docstring being left to
  overstate. M2 menu item text back → both AC-1 tests *and* AC-2's label/value pairs. M3 confirmation
  back → both AC-1 tests (not the sweep alone, as first claimed). M4 drop the `regionCells` loop →
  `test_the_three_cells_follow_the_active_brush`. M5 drop `aria-label="Region"` → the whole of AC-4.
  M6 two cells instead of three → the count *and* all 12 cells of the measured-layout case. M7 drop
  `.player-brush-run { display: inline-flex }` → the boxes (a `<span>` is inline, so width/height do
  not apply and the cells vanish) and again all 12 layout cells. M8 rename `UNKNOWN` to `"clear"` in
  `solver_state.js` → AC-2. M9 drop `flex: 1 0 auto` → all 12 layout cells, the CARD-211 regression.
  M10 drop the seam colour → the `seam != fill` assertion alone.
- **[Owner's parenthetical, recorded]** "in black/dot/question mark/undecided" was read as *the four
  states three cells can be in*, not one cell of each. If the owner meant one black, one dot and one
  "?", it is three `data-state` values in the template and one assertion — no layout change, since
  the toggle's width does not depend on which state each cell holds.

### [Scope] orchestrator, 2026-10-19 · `[Touches drift]` recorded

**11 files changed against 6 predicted.** Four of the six predicted were touched;
`tests/test_puzzle_solver_tools.py` and `tests/test_admin_design_tokens.py` were predicted and **not**
needed. Six files were changed outside the prediction:

- `tests/test_puzzle_solver_hint.py`, `…_marking.py`, `…_maybe.py`, `…_progress.py`,
  `tests/test_puzzle_editor_ui.py` — **the renamed label is a locator in each.** Unavoidable and
  correct: a rename that leaves its locators behind produces tests that pass against a page that no
  longer exists.
- `tests/test_browser_fixture_scope.py` — the 334-line `RENAMED_SINCE_BEFORE` table, the card's biggest
  diff. The label is a **parameter of eight node ids**, so the rename reads to CARD-217's coverage
  guard as eight removals.
- `src/nonogram/admin/templates/puzzle_edit.html` — **comment-only**, and the report's wording needs
  correcting: it says the editor is *"deliberately unchanged and verified so"*, which is true of its
  markup and behaviour but **not of the file**. The edit updates a Jinja comment that named the old
  label; leaving it would have left a comment describing a brush that no longer exists, which is this
  board's own defect family pointing the other way. The edit is right; the sentence about it was not.

`[Touches drift]` recorded for the retrospective's Step 4e rather than only for this card: five of the
six drifted files drifted for **one** reason — a user-facing string is a test locator — and `Touches`
derivation has no way to see that today.

### [Orchestrator] Three things verified rather than taken on report

**The render defect is real and the fix is legible.** The agent reports that its first build drew three
filled cells with collapsed borders, so they rendered as **one solid black bar** while every
`data-state` assertion stayed green. Checked the delivered render
(`~/Documents/nonogram-reviews/CARD-247/player-toolbar-black-region-on.png`): three distinct cells with
visible seams. The pin it added, `seam != fill`, is the only assertion in that file a correct
`data-state` cannot satisfy — which is the right shape for a defect that was invisible to state.

**A mutant survived first, and the agent widened the test rather than the claim — correctly.** M1
(`BRUSH_LABEL` back to "Undecided") initially **survived** the whole-page sweep, because with Black
selected the fourth label is never rendered. The sweep was asserting over a page that could not contain
the string. Rather than narrow the claim it gave the sweep the one click that makes the claim true, and
said so in the docstring. That is the correct call here: the claim ("no user-facing string says
Undecided") was the one worth keeping, and it was the *test* that was too weak.

**⚑ Owner-facing, and the card's own purpose makes it worth asking about: "Clear" now names two
different things on two pages that share one renderer.** In the **editor** `Clear` is the button that
**wipes the whole board** (CARD-246, `data-player-action="reset"`, confirm text *"Every cell goes back
to undecided"*). In the **player** `Clear` is now the fourth **brush**, which paints one cell undecided.
The card's purpose is *"the toolbar says what it does"*; a reader who learns the word on one page
learns the wrong thing on the other. Not a defect against any AC, and not blocking — recorded for the
owner's render check, since the alternative (a different word for the brush, or renaming the editor's
button) is a decision rather than a fix.
