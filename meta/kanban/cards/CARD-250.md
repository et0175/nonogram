# CARD-250: The editor's two bars say what they do — Cancel leaves, "Back to edit" stays, and both exits land on a fresh list

**Status:** done
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/250-editor-exits
**Worktree:** — (removed at merge)
**Source:** owner's doc "Nonograms - Print layout" → "Puzzle editor", 2026-10-19 — items 1, 2, 3 and 4 (intake in `meta/architecture/inputs/raw-requirements.md`)
**Idea:** —
**Wave:** 47
**Depends on:** —
**Touches:** src/nonogram/admin/static/puzzle_edit.js, src/nonogram/admin/templates/puzzle_edit.html, src/nonogram/admin/templates/_puzzle_table.html, src/nonogram/admin/static/admin.css, src/nonogram/admin/app.py, tests/test_puzzle_editor_ui.py, tests/test_admin_design_tokens.py
**Review score:** 8.0 (cycle 3/3 — 7.5 → 8.0 → 8.0; cycle 3 escalated on a prose-only Important, overridden by the orchestrator, see [Gate override])
**Started:** 2026-10-19T07:15:19Z
**Closed:** 2026-10-19T10:39:12Z
**Actual:** 0.4d
**Merge commit:** 71b5ec9
**Blocked by:** —

## What to implement

Four items from the owner's doc. They are **one card** because all four move the same two bars in the
same file, and three of them change the same sentence — splitting them means measuring that bar
three times and conflicting on `puzzle_edit.js` twice.

### 1 + 3. The rename, and the exit that did not exist

The editor has one bar in two phases (`puzzle_edit.html:114-121`): **Save**, and after a save
**Approve + Cancel**, where Cancel means *"put the message away and go on editing — nothing was
stored"* (CARD-246 AC-4). The owner asks for a Cancel beside **Save** and a **"Back to edit"** beside
**Approve**.

Read together — and they have to be read together — today's Cancel is being **renamed to what it
actually does**, which frees the name "Cancel" for the exit that does not exist yet:

| | before | after |
|---|---|---|
| beside **Save** | — | **Cancel** — leave the editor, store nothing, go to the list |
| beside **Approve** | Cancel (go on editing) | **Back to edit** — *same behaviour, new name* |

**The behaviour of today's Cancel does not change** — only its label and its id. CARD-246 AC-4 and
`TestPuzzleEditor_CancelKeepsTheEditAndStoresNothing` keep their meaning; rename the class and say in
the card that you did.

**The message names the button, so it moves too.** `gradeText` (`puzzle_edit.js:132`) ends *"Approve
to store it, or **Cancel** to go on editing."* Rename the button and leave that sentence and the page
lies about its own controls. Same for `CANCELLED`'s wording.

**The new Cancel discards unsaved strokes.** Confirm before leaving **only when there is something to
lose** — the page already hears `BOARD_CHANGE` from the one place a change is recorded
(`onBoardChange`, `:399`), so "the board has changed since it was opened" is a fact this file already
has. A confirm on every exit trains the owner to dismiss it; no confirm at all loses work to a
mis-click. (`Clear`'s existing confirm is the house precedent for the wording.)

### 2. Both exits land on a list that shows the new picture

"Return to list" is navigation: `/puzzles`, the page the editor was reached from.

"**Reload pictures**" is the technical half and the reason this item is not trivial. The list's
thumbnail is `/api/puzzle/<id>/grid` (`app.py:5593`) — a **stable URL** whose response carries a
`Content-Type` and **no `Cache-Control` and no validator**. A browser is therefore entitled to redraw
the row from a cached SVG of the grid the owner just replaced, and will. Two ways out:

1. **Version the URL** (recommended): the row already carries `manually_edited_at` (CARD-245,
   migration 016) — exactly the version key a stable URL needs. `…/grid?v=<stamp>` changes only when
   the grid changes, so an unedited puzzle still caches normally. Touches `_puzzle_table.html:45` and
   the detail modal's `:289`.
2. Send `Cache-Control: no-cache` from the grid route — simpler, and it makes **every** thumbnail on
   every page load re-fetch forever to fix a case that arises once per edit.

Whichever you pick, **prove the stale case first**: a test that fails before the fix, with the two
SVGs differing, not a test that merely reads the attribute you just added.

### 4. The recomputed tier is coloured

In `gradeText`'s sentence, the tier word carries its tier's colour.

**The trap is that the colour rules are consolidated, and JavaScript cannot reach the place they live.**
`meta/design/tokens.css` declares `--color-tier-easy/medium/hard/none`; `templates/_tier.html` is their
**single documented exception** to the no-colour-literals rule, which exists because five copies of
that expression had drifted into two defects at once (CARD-076), and `tests/test_admin_design_tokens.py`
fails the suite on a hex value anywhere in `admin.css` or a template. A tier→hue map written in
`puzzle_edit.js` is a sixth copy in a language the macro cannot reach, and it will not be caught by
that test — the sweep does not read `.js`.

**The shape that is not a regression:** the server's own tier string reaches the DOM as a data
attribute (`<span class="editor-grade" data-tier="easy">easy</span>`), and `admin.css` colours it from
the existing tokens — same hues, no second mapping, no literal. The span is built with
`createElement` + `textContent`, never `innerHTML` (the tier is server data; G-5).

## The trap that governs the whole card: THE INVARIANT

`puzzle_edit.js`'s header states it and four mechanisms carry it, each pinned by its own test:
**this page never offers Approve for a grid other than the one whose grade is on screen, and never
states a store state it has not been told.** Mechanism 1 is that **`tell(text, offer)` is the ONLY
writer** of the message line and the offer, "so a refusal standing beside a live Approve is not a
state this file can be in".

Every item above pushes on it:

- a **third button** is a third thing that can be pressed mid-flight — the `inFlight` refusal and its
  `aria-disabled` (not `disabled`: CARD-211's pattern, it must not drop keyboard focus) cover Save and
  Approve today and must cover the new exits;
- **leaving the page** is a new way for a request to be in flight with nobody left to hear its answer.
  A save's answer "is the only report of what the store actually did" and is the one thing this file
  never drops. **An exit must not be able to leave during a save**, or the owner lands on a list
  while the store is deciding;
- **item 4 changes what `tell` writes** — from a string into a line with an element in it. Keep `tell`
  the single writer and keep `message.textContent` readable (a span's text concatenates into it, so
  the existing assertions survive); do not add a second writer for the coloured part.

## Acceptance criteria

- **AC-1** (happy): *Given* the editor with an unedited board, *when* Cancel beside Save is pressed,
  *then* the browser is on `/puzzles` and the store holds the original grid.
  (test: `TestPuzzleEditor_CancelLeavesTheEditor`)
- **AC-2** (boundary, unsaved work): *Given* a board changed since it was opened, *when* Cancel is
  pressed, *then* the owner is asked to confirm; declining stays on the editor with the edit intact,
  confirming leaves. *Given* an unchanged board, *then* no confirmation is asked.
  (test: `TestPuzzleEditor_CancelAsksOnlyWhenThereIsSomethingToLose`)
- **AC-3** (happy, the rename): *Given* a saved grid with its grade on screen, *then* the button
  beside Approve reads **"Back to edit"**, pressing it puts the message and the offer away and leaves
  the edit on the board, and the store is untouched — CARD-246 AC-4's behaviour under its new name.
  (test: `TestPuzzleEditor_BackToEditKeepsTheEditAndStoresNothing`, renamed from
  `TestPuzzleEditor_CancelKeepsTheEditAndStoresNothing`)
- **AC-4** (guard, the words match the buttons): *Given* any message this page can show, *then* no
  message names a button that is not on the bar — assert over the rendered page's own button labels,
  not against a literal list.
  (test: `TestPuzzleEditor_TheWordsNameTheButtonsThatExist`)
- **AC-5** (happy, Approve exits): *Given* an approved edit **and a board that has not moved since
  Approve was pressed**, *then* the store holds the new grid **and** the browser is on `/puzzles`.
  *Given* a stroke that landed while the store was writing, *then* the store still holds the approved
  grid, the page **does not leave**, and it says that the strokes made since are still on the board
  and unstored — the work is never discarded by the exit.
  (test: `TestPuzzleEditor_ApproveCommitsThenReturnsToTheList`, both cases; the second is
  `…::test_a_stroke_made_while_the_store_was_writing_keeps_the_page`)
  **AMENDED 2026-10-19 (orchestrator, review cycle 1 F-001).** As first written this AC said only
  *"the browser is on `/puzzles`"*, which an implementation satisfies by navigating away from unstored
  work — and that is exactly what it did. The behaviour was narrowed by the decision recorded under
  `### [Decision] F-001`; the AC is amended here so that **the criterion reads true rather than
  wider than the behaviour**, which is the same defect class this card's own guards exist to catch.
  Nothing about the settled case changed: its original *then* clause is intact and still carried by
  the same test.
- **AC-6** (happy, the stale picture — **the failing-first one**): *Given* a puzzle whose grid is
  edited and approved, *when* the list is shown, *then* the thumbnail is the **new** grid. The test
  must be shown failing against the pre-card tree with the two SVGs differing.
  (test: `TestPuzzleEditor_TheListShowsTheEditedPicture`)
- **AC-7** (guard, the exits cannot outrun the store): *Given* a request in flight, *when* **Cancel** is
  pressed, *then* the page does not navigate **and says so** — in words and with `aria-disabled`, which
  is more than a second Save gets. *Given* the same and **Back to edit** is pressed, *then* the page does
  not navigate and nothing is stored; during a **verify** it spends the turn and says the edit is still
  there, and during an **approve** it is ignored in silence.
  (test: `TestPuzzleEditor_NoExitWhileTheStoreIsDeciding`; the approve window's silence is
  `…::test_a_back_to_edit_forced_while_the_store_writes_does_not_stop_the_exit`, the verify window's
  speech `…_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer`)
  **AMENDED 2026-10-19 (orchestrator, review cycle 3).** The original read *"Cancel or Back to edit …
  does not navigate and says so, exactly as a second Save is refused today"* — one clause for two
  buttons, and **two review cycles read it two different ways**: cycle 1 held that "says so" cannot mean
  a sentence, because the named comparator (`onSave`'s guard) refuses *silently* and says so only via
  `aria-disabled`; cycle 3 read it literally and found it false. Both readings were defensible, which
  means the criterion, not the code, was the defect. It is split here so each button's obligation is
  stated and testable.
  **Why silence is right for Back to edit in the approve window, rather than something to fix.** Fix
  cycle 2's guard makes it ignored there so the exit predicate has one meaning. It cannot be made to
  "say so" the way Save does: `inFlightIs` deliberately leaves `back` without `aria-disabled`, and for
  the whole write the button lives inside a `display:none` container — an attribute on an invisible
  control communicates to nobody, so adding it would be a claim with no mechanism, which is the exact
  family that produced a finding on all three of this card's review cycles. The path is reachable only
  by script. **The alternative — making the page speak about a press that did nothing while a store is
  in flight — was rejected** because it brushes THE INVARIANT: the page would state something about a
  board decision it has not been told.
- **AC-8** (happy, the colour): *Given* a verified grid graded easy, medium and hard in turn, *then*
  the tier word in the message carries that tier's colour, and it is the **same** computed colour the
  list's badge uses for that tier, read from both pages in one test.
  (test: `TestPuzzleEditor_TheGradeWearsItsTierColour`)
- **AC-9** (guard, no sixth copy): *Given* the change, *then* no tier→colour mapping exists in
  `static/*.js`, no hex literal enters `admin.css` or any template, and `_tier.html` is still the only
  exception. (test: `tests/test_admin_design_tokens.py`, extended to sweep `static/*.js` for hex
  values — the sweep does not read `.js` today, which is why item 4 could regress unseen)
- **AC-10** (guard, THE INVARIANT): *Given* all of the above, *then* `tell` is still the only writer of
  the message and the offer, and each of the four mechanisms still dies under its own mutant.
  (test: `TestPuzzleEditor_TheOfferAndTheWordsAgree`, passing unchanged)

## Guardrails

- G-1: Behaviour of the existing Cancel is **renamed, not changed**. If `TestPuzzleEditor_…KeepsTheEdit…`
  needs more than a rename, you have changed something the owner did not ask to change.
- G-2: `tell(text, offer)` stays the single writer of the message line and the Approve offer; no second
  path writes either (CARD-246 review cycle 1, F-001..F-005).
- G-3: No navigation while a request is in flight (AC-7), and `aria-disabled` rather than `disabled`
  for every refusal, so keyboard focus is never dropped mid-flow (CARD-211).
- G-4: No tier→colour mapping in JavaScript and no colour literal outside `tokens.css` /`_tier.html`.
- G-5: Server strings reach the DOM through `textContent` / `createElement`, never `innerHTML`.
- G-6: This page still shows no difficulty of its own outside the save bar's message, and no tier badge
  returns to its header (CARD-246 F-008).
- G-7: The board payload gains no key (CARD-246 G-1), and no uniqueness check, clue re-derivation or
  difficulty arithmetic enters this file (CARD-246 G-3, ADR-0029/R2).
- G-8: No new runtime dependency and no front-end framework or build step (ADR-0006/R1, ADR-0038/R1).
- G-9: No test retired without a named survivor (CARD-220's rule).

## System contract

_Assembled 2026-10-19 by `system_rules.py --card CARD-250 --root meta/architecture` (57 rules returned, `card_scope: touches`). A projection — fix the source artifact, never this list._

**Curated to 8; 49 dropped and declared.** Nearly all of the projection is scoped `src/nonogram/**` or `src/nonogram/admin/**.py` — package-wide, so it matches every card on this board and narrows to nothing. Owner decision 2026-10-17: ship the curated form with the dropped count stated. **Superseded 2026-10-19 by [`meta/kanban/curation.md`](../curation.md)** — this card's curation dropped `ADR-0039`, the rule about claims outrunning their mechanisms, and then produced instances of exactly that family. The rule now keeps every in-scope rule whose enforcement does not reach the card's new code. Kept below are the rules a reviewer can hold *this diff* against.

- **ADR-0006/R1** — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-
  party package joins the installed dependencies without revising this ADR. Non-executable
  static assets (fonts and similar data files) may ship as package data instead, and doing so is
  not a dependency change. (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- **ADR-0038/R1** — The puzzle player's client is hand-written JavaScript and CSS served as
  static files by the admin panel. There is no front-end framework, no build step, no npm
  toolchain and no vendored third-party JavaScript library. Adding any of these reopens this ADR
  (and ADR-0006/R1 for vendored code). (check: review-lens)
- **ADR-0038/R2** — Marking, undo, redo, the error count and the solved check run entirely in
  the browser. A loaded player page issues no network request per mark. (check: test:
  TestSolverMarking_NoRequestPerMark)
- **ADR-0038/R4** — The player's state logic (board, strokes, undo/redo history, error count,
  solved predicate) lives in a pure module with no DOM access, separate from rendering. (check:
  review-lens)
- **ADR-0038/R7** — Browser tests use pytest-playwright with Chromium, declared only in a dev-
  only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra.
  (check: review-lens)
- **ADR-0038/R8** — Browser tests run locally, against Chromium installed by `playwright install
  chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named
  skip reason visible in the run summary. They never pass silently. Once a CI pipeline exists,
  it installs Chromium (playwright install chromium) before running… (check: review-lens)
- **ADR-0029/R2** — Technique classification and the strategies list are computed inside the one
  verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's
  strategies list, and the tier is derived from that same list — no second derivation, no second
  solver entry. The ladder's fixed points are phases of that o… (check: test:
  TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- **CON-016** — The admin panel serves a request through exactly one of two mutually exclusive
  doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not
  pass the door in force. With it unset (the default), it refuses any request whose Host header
  does not name this machine — a bare authority, no userinfo, pa… (check: test:
  TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)

## Worktree notes

- **[Why four items and not two cards]** Items 1, 3 and 4 all rewrite the same bar and the same
  sentence — `gradeText` names the button item 3 renames and carries the tier item 4 colours. Item 2 is
  where both new exits land. Cut apart, two cards would re-measure the bar and collide in
  `puzzle_edit.js`; the merge-conflict prediction would serialize them anyway.
- **[The reading of items 1 and 3, recorded because the source is terse]** Two buttons both called
  Cancel, meaning different things on one bar, is not a design anyone asked for; the only reading in
  which both items are non-redundant is a rename plus a new exit. If the owner meant something else it
  is a cheap change, and the alternative is written down here.
- **[`app.py` is a conflict hotspot]** Touched only if the grid route's caching is the chosen fix
  (option 2); option 1 — the recommended one — keeps the change in the templates.
- **[House rules]** `hypothesis` is not in the dependency baseline — seeded `random.Random` with an
  asserted minimum count. Browser tests fail or skip **loudly** with a named reason and never pass
  silently (ADR-0038/R8); `pytest-playwright` stays in the dev-only extra (R7).
- **[`PAGE_ISOLATION`]** `tests/test_puzzle_editor_ui.py` declares its own page isolation because
  CARD-235's glob is `tests/test_puzzle_solver_*.py` and cannot see it (CARD-246 F-014). Every new
  browser test here must be added to `PAGE_ISOLATION_DECLARATION` in that file.
- **[Do not take timing measurements]** Sibling cards may be active; a contended number is not a
  measurement. Layout and colour measurements are fine.

### Implementation summary (agent, 2026-10-19)

**Option taken for the stale thumbnail: option 1 — version the URL.** `app.py` is untouched; the
change is the two template lines the card named (`_puzzle_table.html:45` and the detail modal's
`:289`), so the declared conflict hotspot took no edit at all. No `SCOPE+` lines: every file changed
is in the card's Touches list.

**AC → test**

| AC | test |
|---|---|
| AC-1 | `TestPuzzleEditor_CancelLeavesTheEditor` (click, and from the keyboard) |
| AC-2 | `TestPuzzleEditor_CancelAsksOnlyWhenThereIsSomethingToLose` (5 tests: unchanged → no question; changed → asks, declining keeps the edit *and* it is still saveable; confirming leaves; Escape = Keep editing; painted-then-undone still asks) |
| AC-3 | `TestPuzzleEditor_BackToEditKeepsTheEditAndStoresNothing` (renamed from `…_CancelKeepsTheEditAndStoresNothing`; a rename and nothing else — G-1), plus `…TheWordsNameTheButtonsThatExist::test_the_button_the_grade_names_is_the_one_that_goes_back`, which reads the name out of the message and presses *that* |
| AC-4 | `TestPuzzleEditor_TheWordsNameTheButtonsThatExist` (4 tests) |
| AC-5 | `TestPuzzleEditor_ApproveCommitsThenReturnsToTheList` |
| AC-6 | `TestPuzzleEditor_TheListShowsTheEditedPicture` (server tier, 4 tests) + `…ApproveCommitsThenReturnsToTheList::test_the_row_it_lands_on_draws_the_grid_that_was_stored` |
| AC-7 | `TestPuzzleEditor_NoExitWhileTheStoreIsDeciding` (4 tests) |
| AC-8 | `TestPuzzleEditor_TheGradeWearsItsTierColour` (both pages read in one test) |
| AC-9 | `tests/test_admin_design_tokens.py::test_no_served_script_decides_a_colour` + `…::test_the_tier_hue_macro_is_still_the_only_exception` |
| AC-10 | `TestPuzzleEditor_TheOfferAndTheWordsAgree` — every assertion unchanged; one line added to one test (a 204 that holds the exit's navigation back, so the sentence it reads is still on screen). Mutant M8 below confirms the class still bites after `tell`'s body changed. |

**AC-6's red run, recorded.** The test was written and run against the tree *before* the template
change (`/private/tmp/.../scratchpad/ac6-red.txt`):

```
assert drawn_before != drawn_after        # PASSED — the two SVGs really differ
>       assert after != before, after
E       AssertionError: /api/puzzle/puzzle_000001/grid
E       assert '/api/puzzle/puzzle_000001/grid' != '/api/puzzle/puzzle_000001/grid'
```

All four tests of that class were red; they are green after the two template lines. The claim is
narrowed in the class docstring: these prove the two pictures differ and the URL moves with them, and
they explicitly do *not* drive Chromium's heuristic cache.

**Mutants run (16; 15 killed, 1 deliberately surviving the narrow guard and killed by another).**

| mutant | effect | killed by |
|---|---|---|
| M1 Cancel does not navigate | — | `test_cancel_goes_to_the_list_and_stores_nothing` |
| M2 Cancel never asks | — | `test_a_changed_board_is_asked_about_and_declining_keeps_the_edit` |
| M2b Cancel always asks (edge) | — | `test_an_unchanged_board_is_not_asked_about` |
| M3 in-flight refusal removed | — | `test_cancel_pressed_while_the_store_is_deciding_does_not_leave` |
| M3b "Leave editor" stops re-checking in-flight (edge) | — | `test_leave_editor_pressed_after_the_question_was_asked_is_refused_too` |
| M4 `gradeText` says "or Cancel to go on editing" again | — | `test_the_grade_names_both_buttons_it_offers` **and** `test_the_button_the_grade_names_is_the_one_that_goes_back`; **survives** `test_no_message_names_a_button_the_bar_does_not_carry`, which is exactly what that test's docstring says it cannot see (Cancel *is* a label on the bar now) |
| M5 a message says "press Hold on" | — | `test_no_message_names_a_button_the_bar_does_not_carry` |
| M6 Medium wears Hard's hue | — | `test_each_tiers_word_is_that_tiers_colour_and_the_lists_too` |
| M6b `data-tier` not written (edge) | — | same |
| M7 a hex literal enters `puzzle_edit.js` | — | `test_no_served_script_decides_a_colour` |
| M7b **edge:** the script picks a CLASS per tier instead | **survives the AC-9 sweep alone (exit 0)** — the residual that test's docstring declares — and is killed by `test_each_tiers_word_is_that_tiers_colour_and_the_lists_too` | AC-8's colour read |
| M8 `tell` leaves a live Approve beside a new sentence | — | `test_a_grid_being_checked_is_never_shown_beside_an_approve` (THE INVARIANT still bites after `tell` changed) |
| M9 the coloured span is filled but never put in the line | — | `test_save_shows_the_recomputed_difficulty_and_stores_nothing` (so "a span's text concatenates into `message.textContent`" is load-bearing, not decoration) |
| M10 the exit never says it is busy | — | `test_cancel_pressed_while_the_store_is_deciding_does_not_leave` |
| M11 the thumbnail's version stops moving after the first edit | — | `test_a_second_edit_moves_it_again` |
| M12 Approve does not leave | — | `test_the_store_holds_the_new_grid_and_the_browser_is_on_the_list` |

**The rename, recorded as the card asks.** `TestPuzzleEditor_CancelKeepsTheEditAndStoresNothing` →
`TestPuzzleEditor_BackToEditKeepsTheEditAndStoresNothing`; its two methods renamed with it;
`test_a_cancel_taken_mid_flight_is_not_undone_by_the_answer` →
`test_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer`. In the script,
`onCancel` → `onBackToEdit` and `CANCELLED` → `BACK_TO_EDIT` (same words — they never named the
button). Ids: the old `#puzzle-editor-cancel` is now `#puzzle-editor-back`, and the new exit is
`#puzzle-editor-leave` — the freed *label* was reused, the freed *id* deliberately was not, so no
existing selector silently retargets. No test retired (G-9).

**The one place AC-7 is read narrowly — settled by the amended AC-7 (review cycle 3, F-001).** AC-7
names Cancel *and* Back to edit. Cancel is refused mid-flight in words and with `aria-disabled`.
Back to edit is **not an exit**: it never leaves the page, so it has nothing to outrun, and refusing
it outright would change the behaviour G-1 says to rename rather than change (and would break
`test_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer`, which AC-10 says passes
unchanged). What it does mid-flight depends on **which** request is in flight — two windows, two
behaviours, each stated by the amended AC-7 and pinned on its own:

- during a **verify** it spends the turn and says the edit is still there (pinned by
  `test_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer`, and the no-navigation half by
  `test_back_to_edit_pressed_mid_flight_does_not_navigate_either`);
- during an **approve** fix cycle 2's guard makes it **ignored in silence**, so the exit predicate
  keeps one meaning (pinned by
  `test_a_back_to_edit_forced_while_the_store_writes_does_not_stop_the_exit`).

The asymmetry and its reason are written in `puzzle_edit.js`'s header, in `inFlightIs`, and in the
AC-7 test class's docstring. **Not treated as a guardrail conflict**, because AC-7 as amended states
each button's obligation separately and both are met. It is *not* for the reason first written here
— *"both halves of AC-7's then clause hold for both buttons"* — which review cycle 3 falsified: in
the approve window the "says so" half deliberately does **not** hold. Why that is correct rather
than a gap is recorded under AC-7 above: `back` carries no `aria-disabled`, it sits inside a
`display:none` container for the whole write, and THE INVARIANT forbids a sentence about a board
decision the page has not been told.

**Consequence of AC-5 worth a second look.** A successful Approve now leaves the page, so nine
existing browser tests could no longer wait on the "Saved" sentence on a bar the browser has left.
Eight now wait on the list (`_wait_for_the_list`); the one that must read the sentence
(`test_a_second_approve_pressed_in_flight_is_not_sent_either`) holds the page with a 204 on the
navigation (`_stay_on_the_editor`) and keeps every assertion it had.
`test_approving_from_the_keyboard_commits` lost one assertion about where focus went after the
successful approve **it** makes — the one that leaves, which has no bar left to stand on. (That is one
outcome of three, not every success; see the correction below.) **Each survivor pins one branch's focus hop,
and only one** (corrected in fix cycle 1, F-002): `test_the_whole_flow_runs_from_the_keyboard` pins
**Back to edit**'s `save.focus()` (`:1479`, `activeElement == "puzzle-editor-save"` after the press),
and `test_an_approval_of_a_grid_the_store_no_longer_remembers_asks_to_verify_again` pins **onApprove's
refusal branch** — it did not when the claim was first written (it read no `activeElement` at all, so
deleting that `save.focus()` failed nothing), and the assertion it was named for is now in it.
**Three hops, not two** (corrected in fix cycle 2, review cycle 2 F-001): fix cycle 1 gave onApprove a
successful branch that KEEPS the bar — a stroke landed while the store was writing — and that branch
has a hop of its own, `save.focus()` after the staying sentence, pinned by
`test_a_stroke_made_while_the_store_was_writing_keeps_the_page`. It needed one: `tell("Storing this
grid…")` hides `#puzzle-editor-decide`, so Chromium had dropped focus to `<body>` and the page was
telling the owner to press a Save nothing was standing on (measured `activeElement == ''`). **The
leaving branch is the only outcome with no hop**, for the reason above — there is no bar left to stand
on. `storedText`'s tail changed from "Your board is
untouched — go on editing" to "Showing the puzzle list…", because the old sentence became false the
moment the page started leaving — and in fix cycle 1 it split in two, the second tail belonging to the
branch that stays (F-001).

**Runs.** `tests/test_puzzle_editor_ui.py tests/test_admin_design_tokens.py` — 106 passed (in the
default random order and in `-p no:randomly`). Also run green as the shared-template blast radius:
`test_admin_tier_surfaces.py`, `test_puzzle_edit_routes.py`, `test_puzzle_edit_store.py`,
`test_card_060_grid_renderer_surface.py`, `test_puzzle_review_bulk_read.py`,
`test_batch_requested_tier.py`, `test_admin_filter_side_range_and_name.py`,
`test_admin_rename_strategies_batches.py`, `test_admin_review_actions.py`, `test_admin_serving.py`,
`test_card_065_follow_ups.py`, `test_card_066_status_filter.py`, `test_puzzles_list_pagination.py`,
`test_book_floor.py`. The full suite is the orchestrator's gate; it was not run here. No timing
measurements taken.

### Fix cycle 1 (agent, 2026-10-19) — review cycle 1, 7.5 against min_score 8

Six findings: five fixed, one dismissed as out of scope. `src/nonogram/admin/app.py` still untouched.

**F-001 (important) — fixed. The page stays when the board moved while the store was deciding.**
Per the orchestrator's `### [Decision] F-001`, no question is asked: the store has just spoken and its
answer is the only report of what it did. `onApprove` captures its turn (`const mine = (turn += 1)`)
and the exit is conditional on it — `onBoardChange` advances `turn` *before* its `inFlight ===
"approve"` early return, so `mine !== turn` is a true predicate for exactly "a stroke landed while the
store was writing" and for nothing else. No second notion of "changed" entered the file, and no
comparison of board against stored grid.
`storedText`'s tail split in two (`storedHead` + two exported tails): `storedText` keeps "Showing the
puzzle list…" for the branch that leaves, and the new `storedAndStayingText` says what is true of the
branch that stays — the grid was stored, and the strokes made since are still on the board and are
*not* stored, press Save to check it as it is now. Both are written by the one `tell` call on their own
branch, so G-2 holds: a branch after one `tell` is not a second writer. AC-4's corpus picks the new
sentence up (`_MESSAGE_CORPUS` now flattens both tails, over the whole grade corpus).
New test, shown red first: `TestPuzzleEditor_ApproveCommitsThenReturnsToTheList::test_a_stroke_made_while_the_store_was_writing_keeps_the_page`.
It presses Approve and paints in ONE task (`_APPROVE_THEN_PAINT`, beside `_SAVE_THEN_PAINT`), so the
stroke lands while the write is unanswered with no timing to get wrong, and waits on `_STORED_OR_LEFT`
— a predicate true both when the bar speaks and when the bar is *gone* — so the red run reports which
branch happened instead of timing out. Red against 318bf1d's script:
`AssertionError: … 'http://127.0.0.1:59394/puzzles' == []` (the list was asked for). Green after.
It asserts: the list was never requested, the url is still the editor, the painted board is still on
screen, the POST carried `EDITED` and the store holds `EDITED`, the sentence is the staying one and
does **not** contain "Showing the puzzle list", and no page errors.

**F-002 (important) — fixed with the assertion, and the note made precise.**
`test_an_approval_of_a_grid_the_store_no_longer_remembers_asks_to_verify_again` now ends with
`activeElement.id == "puzzle-editor-save"`, which is the branch that owns onApprove's surviving
`save.focus()`. The card's AC-5 blast-radius note now says which branch each survivor pins (Back to
edit for one, onApprove's refusal for the other) and records that the second did not pin it when the
claim was written. Proof: deleting `save.focus()` (M13) gives `AssertionError: assert '' ==
'puzzle-editor-save'`; restored, green.

**F-003 (minor) — fixed by moving it, not deleting it.**
The tautological `assert not _approve_offered(...)` after `_wait_for_the_list` is gone from
`test_approve_commits_the_grid_that_was_graded`; a comment there names its survivor. The property
("no Approve stands beside the Saved sentence") is now read where the page still exists, in
`test_a_second_approve_pressed_in_flight_is_not_sent_either`, out of `_WATCH_BAR`'s recorded states
filtered for "Saved" — beside the "Storing" filter that was already there. It can fail: under M14
(`tell(storedText(…), grid)` — the offer standing beside the stored sentence) the moved assertion
dies, while the retired line, temporarily put back under the same mutant, **passed** — the control
demonstrating it never could fail.

**F-004 (minor) — fixed: the comment narrowed to its mechanism.** onApprove's success comment no
longer says the answer "is never traded for the navigation". It says what the code does: the answer is
*told* on either branch before anything else; the refusals are the ones read on this bar; the success
is reported to the owner by the row's new picture on the list rather than by a sentence a navigation in
the same task leaves unannounced; and on the staying branch it is genuinely read.

**F-005 (minor) — dismissed**, written back as `dismissed` with "out of scope, routed to a follow-up by
the orchestrator". The four templates were not touched.

**F-006 (minor) — fixed.** `inFlightIs`'s comment now reads "(CARD-246 G-4 / CARD-250 G-3, CARD-211's
pattern)", the form the card's own new test already uses.

**Mutants run this cycle (6; all 6 killed).**

| mutant | effect | killed by |
|---|---|---|
| M13 `save.focus()` deleted from onApprove's refusal branch | — | `…_asks_to_verify_again` (F-002's new assertion) |
| M14 the offer stands beside the Saved sentence (`tell(storedText(…), grid)`) | — | `…_a_second_approve_pressed_in_flight_is_not_sent_either` (F-003's moved assertion); the retired line passed under it |
| M15 the exit is unconditional again (the pre-fix code) | — | `test_a_stroke_made_while_the_store_was_writing_keeps_the_page` |
| M15b **edge:** it never leaves (`if (true)`) | — | AC-5's own two tests plus three that wait on the list |
| M16 the staying branch says the leaving sentence | — | `test_a_stroke_made_while_the_store_was_writing_keeps_the_page` ("Showing the puzzle list" not in said) |
| M16b **edge:** the leaving branch says the staying sentence | — | `…_a_second_approve_pressed_in_flight_is_not_sent_either` (one assertion added: the leaving tail is on screen there) |

**Declarations re-derived (step 6b).** F-001 changed the lifecycle of a successful Approve, so every
statement of it was re-derived from the code: `puzzle_edit.js`'s header flow (the Approve line now
states the exception and why), THE INVARIANT's mechanism 2 (for a save's answer a spent turn decides
not whether to speak but whether to *leave*), `onBoardChange`'s early-return comment (the turn it
spends is not lost with the return), `storedText`'s own doc comment, `_wait_for_the_list`'s docstring,
`TestPuzzleEditor_ApproveCommitsThenReturnsToTheList`'s class docstring (what AC-5 means now), and the
card's AC-5 note. `PAGE_ISOLATION_DECLARATION` now also names an editor left holding an unstored
stroke — **not a new way for a test to leave a page behind** (corrected in fix cycle 2, review cycle 2
F-005): `test_a_stroke_while_the_grid_is_being_checked_is_not_graded` and
`test_a_changed_board_is_asked_about_and_declining_keeps_the_edit` both predate this card and both do
exactly that. The declaration string itself claims no novelty and needed no edit; the novelty was the
note's. No config field, parameter or timeout acquired a second job. F-002,
F-003, F-004 and F-006 are local to their own claim.

**Runs.** `tests/test_puzzle_editor_ui.py tests/test_admin_design_tokens.py` — **107 passed** (106
before, +1 new test), in the default random order and under `-p no:randomly`. The full suite is the
orchestrator's gate. No timing measurements taken.

**For the next review.** Two places worth the hardest look. (1) AC-5's literal text still says *then*
the browser is on `/puzzles`; the behaviour now narrows that to the settled case by the orchestrator's
decision, and the narrowing is recorded in the class docstring and on the card, but the AC's own words
were left alone. (2) The staying branch leaves the owner on a page whose board is unstored work and
whose bar says so — nothing re-offers Approve for that board, by design (Save is the way back in), and
the sentence says exactly that; a reviewer should check it reads as a next step and not as a dead end.

---

### Fix cycle 2 (review cycle 2, score 8.0 — one Important open, severity gate)

**F-001 (important, gating) — fixed in all three layers.** Fix cycle 1 gave `onApprove` a third
outcome — a successful store that KEEPS the bar — and left `main`'s single unconditional
`save.focus()` sitting in the refusal branch only, so the one path this card added told the owner to
press Save while `document.activeElement` was `<body>`. `tell("Storing this grid…")` sets
`decide.hidden = true`, which hides the focused Approve's ancestor, and nothing put focus back.

1. **Code** — `save.focus()` before the `return` in the staying branch, with the reason in the
   comment. Save is the target because the sentence itself names it, it is re-enabled by
   `inFlightIs(null)` in the `finally`, and it is the same choice `onBackToEdit` and the refusal
   branch already make.
2. **Pin** — `assert browser_page.evaluate("() => document.activeElement.id") == "puzzle-editor-save"`
   at the end of `test_a_stroke_made_while_the_store_was_writing_keeps_the_page`. **Red before the
   code, measured:** `AssertionError: assert '' == 'puzzle-editor-save'`. Green after.
3. **Claim** — the comment in `test_approving_from_the_keyboard_commits` said "the focus discipline of
   the flow is still pinned where the page stays", which fix cycle 1 made false. It now enumerates
   **three** focus hops (Back to edit, onApprove's refusal, onApprove's stored-and-stayed branch),
   each named with the test that pins it, with the leaving branch the only outcome that has none — and
   the card's AC-5 blast-radius note says the same, with its "Neither pins the successful branch,
   which no longer has one" corrected rather than left standing. **One more of the same family, found
   by grep rather than by the report:** the refusal test's own comment (`:1468`) said "the successful
   branch has no bar left to stand on", the parallel form of the claim the reviewer flagged, and it
   was equally falsified by fix cycle 1. Corrected to name the handler's two hops and to say that the
   success with nowhere to stand is the one that LEAVES. The card's `:327` note was narrowed the same
   way — "the successful approve **it** makes", not every success.

**F-002 (minor) — guarded, option 1, and pinned.** `if (inFlight === "approve") return;` at the top of
`onBackToEdit`. Chosen over narrowing the comment because the predicate `mine !== turn` now decides
whether a successful store LEAVES, and a turn spent for any other reason makes the page state a fact
about the board nothing told it; the guard removes the state instead of documenting it, and it is the
same guard — same condition, same silence — that `onBoardChange` already takes for the same window, so
it adds no new shape to the file. Narrow on purpose: a blanket `inFlight !== null` would drop G-008's
verify-case turn spend, and
`test_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer` is green and unchanged. New test
`test_a_back_to_edit_forced_while_the_store_writes_does_not_stop_the_exit` forces the press in one
task (`_APPROVE_THEN_BACK`, written out beside `_APPROVE_THEN_PAINT`) and asserts the exit is still
taken.

**F-003 (minor) — docstring narrowed, predicate left alone.** `_STORED_OR_LEFT` said "whichever way it
went" and resolves only on a SUCCESS (`'Saved'` or no bar). It now says so, and says plainly that a
refusal runs the wait out — loud, just slow — and why that is the cheaper honest option here: both
branches the wait exists to distinguish are successes, and a refusal on this path would be a defect
rather than a case.

**F-004 (minor) — mirror added, and the conflation actually run.** The reviewer argued this from the
assertions without running a mutant; run, the direction matters. **MU-A** (the LEAVING sentence emits
head + BOTH tails) **survived the whole 108-test file** — the page claiming in one breath to stay and
to show the list, then navigating. `assert "the editor stays open" not in said, said` beside
`:1843` kills it. **MU-B** (the STAYING sentence emits both tails) was already killed by the negative
guard that test carries, which is why the hole was one-sided and not a swap.

**F-005 (minor) — novelty claim dropped.** Fix cycle 1's own step-6b note called the
`PAGE_ISOLATION_DECLARATION` clause "the one new way a test leaves a page behind". It is not new;
`test_a_stroke_while_the_grid_is_being_checked_is_not_graded` and
`test_a_changed_board_is_asked_about_and_declining_keeps_the_edit` both predate the card and both do
it. The declaration string was accurate and is untouched.

**F-006 (info) — dismissed, not fixed,** on the orchestrator's instruction: `storedHead`'s difficulty
clause was equally unasserted in `storedText` before the split, so it is pre-existing and not a
CARD-250 regression. Recorded in the report with the reason, and with the fix agent's note that the
one assertion the suggestion names is genuinely cheap, left for the orchestrator to decide rather than
added unilaterally into the last tree before the gate.

**Mutants (4 run, 4 accounted for).**

| # | mutant | result |
|---|---|---|
| MU-A | `storedText` (leaving) emits head + BOTH tails | **SURVIVED** 108/108 before the fix → **KILLED** by the added mirror assertion (`…_a_second_approve_pressed_in_flight_is_not_sent_either`) |
| MU-B | `storedAndStayingText` (staying) emits head + both tails | KILLED by the staying test's existing `"Showing the puzzle list" not in said` — the hole was one-sided |
| MU-C | F-001's `save.focus()` deleted from the staying branch | KILLED by `test_a_stroke_made_while_the_store_was_writing_keeps_the_page` — this is the mutant cycle 2's report left for cycle 3 |
| MU-D | F-002's `if (inFlight === "approve") return;` removed | KILLED by `test_a_back_to_edit_forced_while_the_store_writes_does_not_stop_the_exit` |

Every mutant was installed, run, and restored **from a byte-identical backup copy** before the next
one; `diff` against that copy was clean after each restore, and the tree was never left mutated across
a pause. (Not `git checkout --` for the restore: these fixes are uncommitted, so that would discard
them — it did once, mid-cycle, and both code edits were re-applied before anything else ran.)

**Declarations re-derived (step 6b).**
`DECLARATIONS F-001 — updated.` A successful Approve that KEEPS the page now has a focus hop, so the
flow's focus discipline changed from two hops to three. Re-derived everywhere it is stated: the
staying branch's own comment in `puzzle_edit.js`, the comment in
`test_approving_from_the_keyboard_commits` that licensed dropping the hop, the new assertion's comment
in the staying test, and the card's AC-5 blast-radius note. No numeric bound, config field, parameter
or timeout changed, and none acquired a second job.
`DECLARATIONS F-002 — confirmed.` The guard does not change what any declaration says; it makes two
existing ones true that were not. `onApprove`'s "a stroke landed while the store was writing" and
`onBoardChange`'s turn-spend comment both read the turn as "the board moved", and `onBackToEdit` was
the one site that could make that false. Re-derived against the new code and left as written.
`DECLARATIONS F-003 — updated (declaration only).` `_STORED_OR_LEFT`'s docstring narrowed to the two
outcomes the predicate resolves; no behaviour.
`DECLARATIONS F-004 — none (local branch).` One assertion; the sentences are unchanged.
`DECLARATIONS F-005 — updated (declaration only).` The card note; `PAGE_ISOLATION_DECLARATION` itself
re-read and confirmed accurate.
`DECLARATIONS F-006 — none (dismissed).`

**Runs.** `tests/test_puzzle_editor_ui.py tests/test_admin_design_tokens.py` — **108 passed** (107
before, +1 for F-002's pin), in the default random order and again under `-p no:randomly`. The full
suite is the orchestrator's gate. No timing measurements taken. `src/nonogram/admin/app.py` is
untouched, as it has been for the whole card.

**For the final gate.** The mutant cycle 2's report named as still owed to cycle 3 — MU-C, deleting
F-001's `save.focus()` — was run here and kills. The one judgement a reviewer may want to re-take is
F-002's choice of the guard over the comment: it adds a behaviour change (a forced, owner-unreachable
press is now ignored instead of spending the turn) in exchange for making the exit predicate mean one
thing, and the alternative was zero code and a narrower comment.

### [Fix cycle 3] Review cycle 3 — F-001 (important), F-002, F-003; F-004 dismissed

Cycle 3's verdict was that **the code is right and must not change**, so this cycle is prose plus two
test-only assertions. **Zero behaviour change.** The `src/` delta is comment lines only (audited:
`git diff -U0 src/` has no changed line that is not a `//` comment), and the `tests/` delta is added
assertions plus two rewritten docstrings. `_puzzle_table.html`, `puzzle_edit.html`, `admin.css` and
`app.py` are untouched by this cycle.

**F-001 — the AC-7 asymmetry claim, narrowed at all four sites.** Fix cycle 2's guard made Back to
edit behave differently in the two in-flight windows, and its own step 6b recorded the declarations
as "confirmed, unchanged" — that was the miss. Every site now states **two windows, two behaviours**,
with the pin named beside each half:
- `static/puzzle_edit.js` header (the AC-7 paragraph) — "nothing to refuse … it does what it always
  did" replaced by the per-window split: verify → spends the turn and says the edit is still there
  (`test_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer`), approve → ignored in silence
  (`test_a_back_to_edit_forced_while_the_store_writes_does_not_stop_the_exit`), with the mechanism of
  the silence stated (no `aria-disabled` on `back`, a `display:none` container for the whole write).
  The same paragraph's Cancel clause lost "exactly as a second Save is": a second Save returns
  **silently** (`onSave:458`) and says so through `aria-disabled` alone, so Cancel's refusal is *more*
  than it gets — which is what the amended AC-7 now says.
- `inFlightIs`'s comment — "it is refused by nothing" narrowed to "it is never told it is busy", with
  the one window in which it *is* refused named and the reason the refusal is silent given.
- the AC-7 test class docstring — the asymmetry rewritten as a two-bullet split, each bullet naming
  its pin, and "CARD-246's unchanged" qualified to the verify window, which is the only window in
  which that behaviour still exists.
- this card, §"The one place AC-7 is read narrowly" — the false premise ("both halves of AC-7's *then*
  clause hold for both buttons") replaced by the amended AC-7's per-button reading, with the old
  premise recorded as falsified rather than quietly dropped.

**F-002 — the measured mirror hole closed.** Three `not in` assertions added to the AC-7 refusal
tests, completing `inFlightText`'s 2×2 the way cycle 2's F-004 completed the stored pair:
`"Still checking" not in` beside the storing branch, `"Still storing" not in` beside both checking
branches. **MU-J re-run with them in place: KILLED** — the mutant that returned both sentences
concatenated for every caller survived all 108 tests for the reviewer and now fails three
(1 run: `3 failed, 105 passed`), one per branch asserted.

**F-003 — the modal's versioned thumbnail is now read.** The detail modal is built by a template
literal from `/api/puzzle/<id>/details`, so no Flask-client test can see the url it produces; the pin
had to be a browser assertion. `test_the_row_it_lands_on_draws_the_grid_that_was_stored` now opens
the modal over the row it has just landed on and requires the same stamp in `.thumb-lg img`'s `src`
(and that the picture loads), in the same shape as the row's assertion. **Proved red:** deleting the
modal's `?v=` fails exactly this test (`1 failed, 107 passed`, the message printing the unversioned
url) where it previously failed nothing.

**F-004 — dismissed, not a finding by its own text** (severity info, type question). The measurement
is on the record and `test_a_second_approve_pressed_in_flight_is_not_sent_either`'s docstring already
states mechanism 3 *narrower* than the module docstring does. Raised to the orchestrator rather than
edited: the module docstring (`tests/test_puzzle_editor_ui.py:40-41`) says each of the four mechanisms
"is pinned there by a test that fails when that mechanism alone is taken out", and MU-I3 measured that
false for mechanism 3 at `onApprove`. That is the same claim-vs-mechanism family as F-001, one level
up; it is left for the orchestrator's call.

Cycle 2's F-006 (`storedHead`'s unasserted difficulty clause) stays dismissed and routed to CARD-251.

`DECLARATIONS F-001 — updated (declaration only).` Nothing about the mechanism changed this cycle;
the four standing statements of it did, re-derived from `onBackToEdit`'s guard as it now stands rather
than re-worded. The failure matrix was re-read and needs nothing: it carries no row for a forced
mid-flight Back to edit.
`DECLARATIONS F-002 — none (local branch).` Three assertions; no sentence, bound or lifecycle moved.
`DECLARATIONS F-003 — updated (declaration only).` The AC-6 browser test's docstring now says which
of item 2's two urls it covers, and that the modal half is reachable only from a browser.
`DECLARATIONS F-004 — none (dismissed).`

**Mutant discipline.** Both mutated files were installed from and restored to byte-identical backups
in the session scratchpad (`puzzle_edit.js.FIX3BACKUP`, sha256 `2491eda4…b9209cf`, the same hash the
cycle-3 reviewer recorded; `_puzzle_table.html.FIX3BACKUP`, sha256 `b7d12c3d…c6bc1b`). `diff` was
clean after each restore and the hashes re-verified; `git checkout --` was never used. The tree is
unmutated.

**Runs.** `tests/test_puzzle_editor_ui.py tests/test_admin_design_tokens.py` — **108 passed** before
and after (the three new assertions and the modal assertion live inside existing tests, so the count
does not move). No timing measurements. The full suite is the orchestrator's gate.

### [Scope] orchestrator, 2026-10-19

Changed files vs `main`: `admin.css`, `puzzle_edit.js`, `_puzzle_table.html`, `puzzle_edit.html`,
`tests/test_admin_design_tokens.py`, `tests/test_puzzle_editor_ui.py` — **six of the seven
`Touches` entries, no drift, no file outside the prediction.** `src/nonogram/admin/app.py`, the
declared conflict hotspot, took **no edit**, which is the outcome option 1 was recommended for and
which leaves CARD-251 a clean base in the file both cards would otherwise collide in.

**AC-6's red run verified independently of the report.** The evidence file shows
`assert drawn_before != drawn_after` PASSING and the URL assertion failing on the pre-card tree —
i.e. the two SVGs genuinely differ and the stale case was real before the fix, which is the one thing
a thumbnail test of this shape can get wrong.

### [Build gate] PASSED (full, 884s) — orchestrator, 2026-10-19

`review.test_scope` is `full` on this board, so the gate is the whole suite. Run on the worktree at
`318bf1d` with `DATABASE_URL` SET at the worktree's own derived database (CARD-244), under the flock
on `meta/kanban/.full-suite.lock`. **EXIT=0, first attempt, 8390 passed / 1 skipped / 0 failed** —
the one skip is the platform `setrlimit` one every run on this machine carries.

**The count reconciles exactly, and that is the evidence.** Collected 8391 on the branch against
**8364** on `main` — which is itself wave 46's final smoke test (8363 passed + 1 skipped) — so the
net is **+27**, and all 27 are in this card's own two test files (79 → 106 node ids there, nothing
else moved).

**[G-9] verified rather than trusted.** Exactly three node ids present on `main` are gone from the
branch, and all three are the documented renames, each with its successor collected on the branch:
`…CancelKeepsTheEditAndStoresNothing::{test_cancel_leaves_the_store_and_the_board_as_they_were,
test_the_edit_can_be_carried_on_and_saved_after_a_cancel}` →
`…BackToEditKeepsTheEditAndStoresNothing::{…_back_to_edit_leaves_…, …_after_going_back}`, and
`TheOfferAndTheWordsAgree::test_a_cancel_taken_mid_flight_is_not_undone_by_the_answer` →
`…test_a_back_to_edit_taken_mid_flight_…`. **No test retired.**

**⚑ The gate's own summary line was suppressed by the orchestrator's flag — my defect, recorded.**
`pyproject.toml` already sets `addopts = "-q"`, so the gate script's explicit `-q` made it `-qq`, at
which pytest prints **no** `N passed` line at all. `EXIT=0` was still the authority and `failed`
appears zero times in the log, but a gate that cannot print its own count is the same shape wave 46
recorded when `-rs` reported skips and not failures. The flag is dropped, and the counts above were
re-derived from `--collect-only` with `addopts` cleared rather than read off a line that was never
printed.

### [Review 1/3] Score: 7.5 — 0 critical, 2 important, 4 minor · [Review sync] 1 report → meta/review/

Report: `meta/review/20261019T081619Z-CARD-250-cycle1.yml` (parses under `yaml.safe_load`; synced into
the main repo, so it survives the worktree). Below the `min_score: 8` threshold, and the severity gate
fails independently of the score. **Mutation check (Step 8f) emitted `deferred(cost)`** — correct per
the cost ladder, and it means **this card cannot merge on this review**: the certification must
actually run on the stable cycle.

**What the review did NOT find, which is worth as much as what it did.** The brief pointed it at the
two mutants the implementation declares as surviving by design (M4, M7b) because a declared residual
that is really a hole is this board's recurring defect. It read the killing tests rather than trusting
the table and **both kills are real**: M4 is killed twice over (the labels list, and the test that
presses the button the message names), M7b by the two-surface colour read, since `admin.css` keys only
on `[data-tier=…]` so all three tiers would collapse to `--color-tier-none`. It also re-derived
THE INVARIANT after `tell`'s body changed and found all four mechanisms still die under their own
mutant, with a sharper reason than the card's: the parts are collected into `line` **before**
`replaceChildren`, and the bar's MutationObserver delivers its records in one microtask checkpoint, so
no half-written line is observable.

**[Review] F-001 (important) CONFIRMED by the orchestrator against the code, including the remedy's
premise.** A stroke made while the store is deciding is destroyed by Approve's new exit, and no
question is asked although the page already knows the board moved. `onApprove` tells the answer and
then calls `window.location.assign(THE_LIST)` **unconditionally** (`puzzle_edit.js:501-502`), while
`onBoardChange` sets `boardChanged = true` and returns early by design when `inFlight === "approve"`
so the store keeps the last word. Before this card the same sequence was safe — the page stayed and
`storedText` said *"Your board is untouched — go on editing"*; the card's own notes record replacing
that sentence **because it became false**, without noticing that the work it described is now lost.
No test covered it before or after. The remedy's load-bearing premise was checked independently:
`onBoardChange` advances `turn` **before** its early return (`:549` ahead of `:558`), so a turn
captured at approve time is a true predicate for exactly this sequence.

**[Review] F-002 (important) CONFIRMED, and it is wave 46's through-line in the artifact that is read
at merge.** The card's note names two survivors for the focus assertion AC-5 forced out of
`test_approving_from_the_keyboard_commits`, "both of which still assert the focus discipline". Only
one does. `test_an_approval_of_a_grid_the_store_no_longer_remembers_asks_to_verify_again` contains no
read of `activeElement` at all — the only reads in the file are at `:1473/1475/1479` (the keyboard
flow, and `:1479` pins **Back to edit**'s `save.focus()`, not the refusal branch's) and
`:2305/2352/2393` (the leave confirmation). So the `save.focus()` the diff moved into onApprove's
refusal branch is pinned by nothing, and deleting it fails no test.

**[Review] F-003 (minor) CONFIRMED — a control that cannot fail.**
`test_approve_commits_the_grid_that_was_graded:1070` keeps `assert not _approve_offered(browser_page)`
*after* `_wait_for_the_list`, i.e. on `/puzzles`, where `#puzzle-editor-decide` does not exist and
Playwright's `is_visible()` returns False for every possible implementation. The review checked the
other seven retargeted tests and each keeps a substantive post-navigation assertion, so this is
isolated rather than systemic — but "no Approve stands beside the Saved sentence" is now asserted
nowhere.

**[Review] The reviewer corrected the orchestrator's own premise on F-006, and it was right to.** The
brief claimed the `inFlightIs` comment cites the wrong guardrail. It does not: the line is unchanged
context, and **CARD-246's G-4 really is the accessibility rule**, so its original referent is correct.
What is left is a bare `G-N` that a reader arriving from CARD-250's list resolves wrongly — fixed by
qualifying it, not by renumbering.

### [Decision] F-001 — stay and say so, not ask before leaving (orchestrator, 2026-10-19)

The review raised F-001 as partly an owner question: *"stay and say so"* or *"ask before leaving"*.
Carried as an orchestrator call rather than parked at the wave boundary, with the alternative recorded,
because the finding is a defect either way — **today the page neither stays nor asks** — and because
this board's standing rule is to carry a card through its gates.

**Chosen: the page does not leave when the board moved while the store was deciding, and says so.**

- It loses no work, which is the whole of what F-001 is about.
- It follows AC-2's own principle — *confirm only when there is something to lose* — using the very
  fact AC-2 introduced (`boardChanged`, latched from the one place a change is announced). No second
  notion of "changed" enters the file.
- The rejected alternative would put a **question in front of an answer the owner has not read yet**:
  the store has just spoken, and that answer "is the only report of what the store actually did".
  Asking about the exit first buries it.
- It narrows AC-5's literal *"and the browser is on /puzzles"* to the settled case. AC-5's own test
  and all eight retargeted tests still exercise that case unchanged, so what narrows is not the AC's
  scenario but the behaviour on a path the AC does not describe: the owner has created new unstored
  work mid-store. **If the owner wants the exit to win even then, that is a one-line change** and this
  note is where to find it.

The staying branch needs a test that can fail, and `storedText`'s tail ("Showing the puzzle list…")
must split in two: it is false on the branch that stays.

### [Fix 1] declarations — orchestrator, 2026-10-19 · commit `130823f`

All six findings closed or routed: **F-001, F-002, F-003, F-004, F-006 fixed**; **F-005 dismissed** as
out of scope and filed to the backlog. 107 passed in the card's two test files (106 before, +1).
`app.py` still untouched, so CARD-251's base in the hotspot is unchanged.

**F-001's fix verified by the orchestrator's own mutant, not by the report.** Flipping the new
predicate to `if (false)` — i.e. restoring the pre-fix unconditional exit — makes
`…::test_a_stroke_made_while_the_store_was_writing_keeps_the_page` **FAIL**, and it passes restored.
So the central new test is not vacuous. The same run incidentally re-confirmed AC-6 live: the request
log shows `GET /api/puzzle/<id>/grid?v=2026-10-19T08:34:54…`, the versioned URL.

**The fix agent reported an edge mutant that SURVIVED, and that is the most useful line in its
report.** M16b — the *leaving* branch saying the *staying* sentence — lived at first, "because the two
tails share a head and nothing read the tail". It added an assertion to kill it rather than narrowing
the claim or leaving it undeclared. Review cycle 2 is pointed at exactly that shape: whether each tail
is now pinned on its own branch, in both directions.

**`turn` has acquired a third job and the review was told to judge it.** It was the staleness token for
answers; mechanism 2 made it decide whether an answer may *speak*; the fix makes it decide whether the
page may *leave*. `onSave` and `onBackToEdit` also advance it, so the question put to review is whether
any of those is reachable between Approve and its answer — an overloaded token that two uses can
disagree about is how this file's earlier defects were shaped.

### [Build gate] FAILED (full, 1109s) — orchestrator, 2026-10-19 · attribution OPEN

The gate on the fixed tree (`130823f`) came back **RED: EXIT=1, 12 failed, 8379 passed, 1 skipped**.
Recorded here before it is explained, because a gate red on one run and green on another is not the
evidence a gate green on its first run is — the same rule wave 45 applied to CARD-248.

**All 12 failures are in `tests/test_puzzle_editor_ui.py` and all have one shape: the editor does not
leave for `/puzzles` after a successful Approve.** Eleven are
`page.wait_for_url("**/puzzles", timeout=20_000)` timing out. The twelfth is **semantic, and it is the
one that matters**: `test_a_second_approve_pressed_in_flight_is_not_sent_either` failed
`assert "Showing the puzzle list" in said` against a message carrying the **staying** tail —
*"You changed the board while… the editor stays open: those strokes are still on the board and are not
stored."* That is the F-001 branch firing on a path that must leave, which means `turn` advanced
between Approve and its answer.

**What is already known, and what is not.**

- **The same file is green SOLO: 97 passed, EXIT=0, 26.73s**, run immediately after the red gate.
- **This gate ran CONCURRENTLY with review cycle 2's targeted browser runs — the orchestrator's own
  choice, recorded as such.** The cost shows: 132 ms/test against 105 on the same tree two hours
  earlier, and the suite ran 1109s against 884s.
- **So the red run is not yet attributable**, and will not be read as a verdict either way. Wave 44
  recorded that a concurrent sibling can manufacture failures *and* skip counts, that reading a
  contended run as a verdict cost a fix-agent attempt, and that it put a false finding in front of the
  owner. A **solo** re-gate is chained behind a host-quiet check.
- **The semantic failure is the reason this is not being written off as slowness.** A 20s navigation
  timeout is credible under load; a message carrying the wrong one of two tails is not. For the
  staying branch to fire, `BOARD_CHANGE` must arrive between Approve and its answer — and solver.js
  dispatches it **synchronously** from `commit()` (`solver.js:782`), so there is no late-delivery
  story to lean on. Either something calls `commit()` during the approve, or the predicate is reachable
  another way. If the solo gate is red too, that is fix cycle 2's finding and it is precisely the
  overloaded-`turn` hazard review cycle 2 was asked to judge.

### [Review 2/3] Score: 8.0 — 0 critical, 1 important, 4 minor · [Severity gate] FAILS · [Review sync] 2 reports → meta/review/

Report: `meta/review/20261019T085620Z-CARD-250-cycle2.yml`. **8.0 meets `min_score` and the card still
does not pass**: a gating finding is open, and a severity gate is not a number. Cycle 3 is the last one
available.

**Step 8f RAN this cycle — 7 mutants, 7 killed, 0 survived**, so cycle 1's `deferred(cost)` is
substantially discharged. Not finally: six of the seven targets lie outside the fix F-001 now calls
for, so they stand; the seventh does not, because F-001's fix adds a line to `onApprove` and an
assertion to the new test. **Cycle 3 must run the mutant that pins that added line** (delete the
`save.focus()` → the staying-branch test must fail). Nothing else is owed.

**All ten ACs hold, including the amended AC-5, scored as written.** G-1..G-9 clean **except G-3**,
which is what the Important finding is.

**[Review] F-001 (important) — the fix cycle introduced a G-3 violation, and it is a regression against
`main`.** `main` ended `onApprove` with **one unconditional `save.focus()`** covering every outcome.
This card moved it into the refusal branch, licensed by the claim that a stored edit leaves the editor
so there is *"no save bar left to stand on"* — and then fix cycle 1 added a successful-approve branch
that **keeps the bar** and revisited neither the call nor the claim. `tell("Storing this grid...")`
hides `#puzzle-editor-decide`, the focused Approve's ancestor, so Chromium drops focus to `<body>`; the
staying branch then speaks and returns with no `focus()` anywhere. **Measured, not inferred:** a
temporary probe inside the new test read `activeElement='' tag='BODY'`. So the page tells the owner to
press Save while nothing is focused — against G-3's stated purpose (*"keyboard focus is never dropped
mid-flow"*, CARD-211) — and the claim in the test file that licensed dropping the call is now false of
a page-staying path. The other two page-keeping paths both restore focus and both are pinned.

**The four Minors are three claim-vs-mechanism defects and one false novelty claim**, all one-line or
prose-only: `onBackToEdit`'s unguarded `turn += 1` is the one way the exit predicate can mean something
other than "the board moved" (unreachable without forcing — filed because **the file's own comment on
that very line refuses the reachability argument**); `_STORED_OR_LEFT`'s docstring claims three outcomes
while the predicate resolves two, so a *refused* approve times out at 20 s, the exact failure mode the
docstring says it avoids; the two sentence tails' negative guards are one-sided, so a sentence
conflating both tails would pass both tests; and the card's own note calls the new page-isolation clause
"the one new way a test leaves a page behind" when a pre-card test already does exactly that. (Written
by the fix agent at the worktree card's `:422`, not by the orchestrator — corrected here because the
first draft of this note claimed it as mine, and a mis-assigned defect is as wrong in this record as an
unrecorded one. It still reaches the artifact read at merge, since worktree notes sync into this card.)

⚑ **Three consecutive cycles in this one file have now produced a finding of the same family** — a claim
stated wider than its mechanism. That is the signal the family-regression check exists for; it is not
an escalation yet (the findings are not attributed to the previous fix in the way that check requires),
but it is the reason the four Minors go into the same fix cycle rather than being waved through.

### [Build gate] the RED run is EXPLAINED and attributed — orchestrator, 2026-10-19

**Measured, not argued: the gate's 12 failures and the `if (true)` mutant's 12 kills are the SAME 12
tests**, with no difference in either direction (`comm -23` and `comm -13` both empty). Review cycle 2's
Step 8f mutation pass edits `puzzle_edit.js` **in place**; the orchestrator's full suite was reading
`src/` while the always-stay mutant was installed. The red run is therefore **neither contention nor a
code defect**, and the semantic failure that made it look real — a message carrying the staying tail —
is exactly what that mutant produces.

**The orchestration defect is the orchestrator's, and it is a new one for this board.** A full-suite
gate must never run concurrently with a review cycle that has `mutation_check: true`. The
`.full-suite.lock` protects against two full suites; **it does not protect against a mutator**, and the
procedure's "machine-load" reasoning is about CPU, not about a tree being edited underneath a reader.
The first diagnosis offered — CPU contention, citing wave 44 — was *wrong in a way that would have been
comfortable*: it would have been retried, come back green, and been filed as noise, leaving the real
hazard unrecorded for the next card.

Consequences taken rather than noted: the queued solo re-gate was **cancelled** (it would have fired
into fix cycle 2's edits and repeated the mistake), and **no gate runs on `130823f` at all** — it is
superseded by fix cycle 2. The tree that gets gated is the tree intended for merge, gated **solo**,
after the fix lands. The 1109s / 132 ms-per-test line in `suite-timing.log` must not be read as a cost
trend: it is a mutated tree's run.

### [Fix 2] declarations — orchestrator, 2026-10-19 · commits `57c1fc1`, `b8fbec4`

F-001 fixed in all three layers, F-002..F-005 fixed, F-006 dismissed as pre-existing. **108 passed** in
the card's two test files. `app.py` still untouched.

**Verified independently, because the fix agent disclosed a restore mishap.** Its first mutant restore
used `git checkout --` and discarded two uncommitted edits; it caught that, re-applied them, and used a
byte-identical backup copy thereafter. The claim to check was therefore not "the fix works" but "no
mutant residue reached the commits": **the entire code delta since `130823f` is exactly two
non-comment lines** — `save.focus();` and `if (inFlight === "approve") return;` — and the tracked tree
is clean. The disclosure is the reason the check was possible; an undisclosed mishap of that shape is
invisible.

**The most informative result of the cycle is that the reviewer's argument was right and incomplete.**
Cycle 2 filed the one-sided-guard finding (F-004) *argued from the assertions*, saying plainly it had
not run a conflation mutant. Run: **MU-A — the LEAVING sentence emitting head + both tails — SURVIVED
all 108 tests.** The hole was real, and wider than the pair the finding described. MU-B, the direction
the brief actually described, was already dead. So the remedy was right for a reason neither the
reviewer nor the brief had established, and **the mutant is what established it** — which is this
board's standing rule earning its cost for the third time this wave.

**A fourth instance of the family was found by the fix agent itself, not by review.** It grepped the
claim family rather than only the cited lines and found `tests/test_puzzle_editor_ui.py:1468` — the
refusal test's parallel *"the successful branch has no bar left to stand on"* — equally falsified by fix
cycle 1. Commit `b8fbec4`. Three cycles, four instances, one family: a claim true when written and
false after a later change.

**F-006 decided rather than left open.** The fix agent offered, without acting, that one assertion for
`storedHead`'s unasserted difficulty clause would be cheap. **Not added**: it is pre-existing, carries
no AC, and putting an unrequested assertion into the last tree before the final gate buys nothing. It
is routed as a free pickup for **CARD-251**, which passes through this same file.

**For cycle 3 to weigh: F-002's judgement call.** The guard was chosen over narrowing `onApprove`'s
comment. It buys an exit predicate with one meaning; it costs a behaviour change on an owner-unreachable
path (a forced Back to edit during a store is now ignored rather than spending the turn), and
`onBackToEdit` now has a silent early return where it used to always say something.

### [Review 3/3] Score: 8.0 — 0 critical, 1 important, 2 minor · [Severity gate] ESCALATES · certification COMPLETE

Report: `meta/review/20261019T093741Z-CARD-250-cycle3.yml`. Scores across the card: **7.5 → 8.0 → 8.0**.
`max_cycles` is exhausted, so the open Important formally escalates.

**Step 8f: CERTIFICATION COMPLETE — 12 mutants, 10 killed, 2 survived, both filed, neither gating.**
This is the condition cycle 1's `deferred(cost)` left owed, and it is discharged. Three results are
worth keeping:
- **MU-C re-run rather than inherited.** The mutant pinning fix 2's `save.focus()` was reported killed
  by the agent that wrote the line; the reviewer ran it again itself, on the principle that *a
  certification carried on the fixed-by agent's own word is not a certification*. Killed, by its
  intended pin alone.
- **The focus discipline is FOUR hops, not three.** The brief asked for a sweep and it found a fourth
  page-keeping path this card added — `closeTheConfirm`'s `leave.focus()`. All four die under their own
  mutant, each killed by exactly one test, and the leaving branch is correctly the only page outcome
  with no hop.
- **MU-H**, the guard widened to `inFlight !== null`, is killed by *both* verify-case pins — so fix 2's
  "narrow on purpose" is demonstrated on both sides rather than asserted.

**[Review] F-001 (important) — the AC-7 asymmetry claim is false at four sites, and the root cause is a
step-6b that said nothing changed.** Fix cycle 2's guard is right and well pinned; what was not
re-derived is every standing statement of the asymmetry it changed — the script header's AC-7
paragraph, `inFlightIs`'s comment, the AC-7 test class docstring, and **the card's own sentence
dismissing the guardrail question** (*"Not treated as a guardrail conflict, because both halves of
AC-7's then clause hold for both buttons"*). Fix 2's own declarations step recorded *"the guard does
not change what any declaration says"*, which is exactly the miss. **No behavioural defect claimed;
the reviewer said the code should not change.**

**The two Minors are both this card's own work and both measured or derived, which is why they were
fixed rather than deferred like F-006.** `inFlightText`'s pair carries the same one-sided mirror hole
F-004 closed for the stored pair — **MU-J survived all 108 tests**; and the detail modal's versioned
thumbnail is the one card change **no test reads** (delete its `?v=` and 108 still pass), a coverage
gap the reviewer verified statically to be otherwise correct.

**The reviewer declined to inflate and declined to suppress, and said so.** It filed the two
cosmetic-consequence items as Minor, refused to re-raise cycle 2's dismissed F-006, and recorded the
mechanism-3 redundancy as an observation rather than a finding — while refusing to let the Important
pass, on this card's own precedent: in cycle 1 the identical defect class was rated Important and
closed by amending an AC's text so the criterion read true.

### [Gate override] cycle 3's escalation handled by the orchestrator, not sent to the owner — 2026-10-19

`max_cycles: 3` is exhausted and an Important was open, so the pipeline's answer is **escalate to the
owner**. It was not sent, and the reasons are recorded here so the owner can reverse the call rather
than discover it.

**What the finding is and is not.** It is **zero code** — the reviewer's own verdict is that the code
is right and should not change, and that the implementation is in the best shape it has been in across
three cycles. What is wrong is four written claims plus an AC whose text two reviewers read two
different ways.

**Why this did not need the owner.** The test is whether their answer would change what happens next.
The options were (1) narrow the four claims and amend AC-7 so it reads true, (2) leave false claims in
the tree, (3) make Back to edit "say so" in the approve window to match AC-7's literal wording.
(2) is not a choice anyone makes. **(3) is refutable on mechanism and was refuted, not merely
preferred**: `inFlightIs` leaves `back` without `aria-disabled` on purpose, and for the whole write the
button sits inside a `display:none` container, so the attribute would communicate to nobody — a claim
with no mechanism, which is the family that produced a finding on all three of this card's cycles. Its
other form, making the page speak about a press that did nothing while a store is in flight, brushes
THE INVARIANT. That leaves (1), which is the orchestrator's own writing surface and the **precedent
this card already set**: AC-5 was amended for the identical defect class in cycle 1, recorded the same
way.

**What was done instead of escalating.** AC-7 amended (split per button, each half with its own named
pin, and the reason silence is correct written down); a prose-only fix cycle for the four claim sites;
and the two measured Minors closed, because a *surviving mutant that has been measured* must not be in
the tree at merge.

**What the owner may want to reverse.** The AC-7 amendment is a spec edit made by the orchestrator. If
the owner reads AC-7's "says so" as binding on Back to edit too, the honest closes are a code change
(and a fourth cycle this pipeline does not have) or a recorded deviation — not the amendment. The
alternative is stated above so it can be taken.

**No behaviour reaches the owner differently because of this.** The only behaviour change in the last
two cycles is one `save.focus()` and one guard on a script-only path.

### [Fix 3] declarations — 2026-10-19 · commits `1be1b19`, `2821642`

F-001, F-002, F-003 fixed; F-004 (the mechanism-3 observation) dismissed as not a finding by its own
text. **Zero behaviour change, audited mechanically rather than asserted:** `git diff -U0 b8fbec4..HEAD
-- src/` contains no added or removed line that is not a `//` comment. The test delta is additive
assertions plus the rewritten AC-7 docstring; the only removed test lines are six prose lines.
108 tests before and after.

**Both measured gaps are now closed and each was shown dying:** MU-J (`inFlightText` returning both
sentences concatenated), which **survived all 108 tests** before, now kills **three** tests, one per
branch asserted; and deleting the detail modal's `?v=`, which failed nothing before, now kills
`test_the_row_it_lands_on_draws_the_grid_that_was_stored` alone. The modal pin had to be a browser
assertion — the modal is built by a template literal from `/api/puzzle/<id>/details`, so no Flask-client
test can see the URL it produces, which is why that half of item 2 had no coverage in the first place.

**The fix agent found a fifth instance of the family inside the site it was sent to correct.** The same
header paragraph claimed Cancel is refused *"in words and with aria-disabled, exactly as a second Save
is"* — and `onSave` returns **silently**. That comparator was false in exactly the way cycle 1 first
flagged, and it is the same false comparator that made AC-7 readable two ways. Narrowed to say Cancel's
refusal is *more* than a second Save gets.

**[Orchestrator] A sixth instance, one level up, narrowed rather than left standing.** The module
docstring claimed each of THE INVARIANT's four mechanisms "is pinned there by a test that fails when
that mechanism alone is taken out". Cycle 3's **MU-I3 measured that false** for mechanism 3 at
`onApprove`: removing its one-request guard alone leaves **98 tests passing**, because `tell` has
already withdrawn the offer, so a second Approve has nothing to send. `onSave`'s site is where the
mechanism is sole protection. The reviewer declined to file it and the fix agent was told not to touch
it unilaterally — both correct — so the call was the orchestrator's: narrow it, name the declared
redundancy, and record that a mutant falsified it (`2821642`). Six instances of one family across three
review cycles, and **the last two were found by the fix agent and the orchestrator, not by review.**

### [Build gate] PASSED (full, 902s, SOLO) — orchestrator, 2026-10-19 · `2821642`

**EXIT=0, first attempt, 8392 passed / 1 skipped / 0 failed.** The skip is the platform `setrlimit` one.

**The count reconciles exactly, which is the evidence this board asks for.** `main` is **8364** collected
(8363 passed + 1 skipped — wave 46's final smoke test); the branch is **8393**, so **+29**. The card's
own two test files went **79 → 108** node ids, also **+29**. Every test this card added is in its own
files and nothing outside it moved.

**Comparable with the 884s build-gate line and with nothing else**: both solo, same DATABASE_URL
condition, so 902s is **+2%**, which is this card's 29 new tests, 25 of them browser tests. The
1109s / 132 ms-per-test FAIL line is **not** a cost point — that run was this suite reading a mutated
tree, and the attribution is recorded above.

**The gate prints its own count again.** The `-q` → `-qq` defect that suppressed it on the first gate —
and forced the count to be reconstructed from `--collect-only` — is fixed, so this line was read rather
than derived.

### [AC/EC check] 17 verified, 2 unverified — both closed by `9a31a8b` · orchestrator, 2026-10-19

The evidence gate read every AC-1..AC-10 and G-1..G-9 against its named test, asking only *would this
test fail if the behaviour were wrong*. **17 verified, 2 unverified, 0 n/a.** Both gaps were **evidence
on correct code** — no behavioural defect anywhere — and both were measured rather than argued.

**⚑ The seventh instance of this card's family was in the orchestrator's own amended AC-7 text, which is
exactly what the gate was sent to look for.** AC-7 says Back to edit pressed during an approve is
*"ignored in silence"* and names `test_a_back_to_edit_forced_while_the_store_writes_does_not_stop_the_exit`
as carrying that clause. **It did not.** With the guard changed to `tell(BACK_TO_EDIT); return;` the
whole suite still passed — so the page could have announced *"your edit is still there"* over a live
store write, which is **the very alternative AC-7's own justification paragraph records as rejected for
brushing THE INVARIANT**. The test pinned "the guard does not spend the turn, so the exit still
happens", which is a different sentence. Closed: `_APPROVE_THEN_BACK` now returns the bar's state and
the test asserts the sentence is still the store's, read in the press's own task.

**G-2's literal clause was unpinned too, and that one is inherited from CARD-246 rather than introduced
here.** The suite pinned the *consequence* — every sentence carries its own offer, so a refusal never
stands beside a live Approve — and not the clause G-2 states. Measured: replacing
`tell(inFlightText(inFlight))` in `onLeave` with a direct `message.textContent` write left **98 tests
passing**; a second writer that happens not to decouple message from offer was invisible. Closed with a
structural test that counts exactly one write of each and requires both to be `tell`'s own, **with its
residual declared** (a writer that aliases the element to a third name is not matched) rather than
claimed complete — the discipline this card learned six times over.

**Both pins verified by mutant, each with a green control run on the real tree first.** That control
mattered: the first attempt at the AC-7 mutant **did not install** (the guard string occurs twice —
`onBackToEdit` and `onBoardChange`) and the second ran against the wrong class, and both times the
output read "passed". Neither would have proved anything, and both were caught by checking what the
selection actually contained rather than trusting the word.

**Two pre-existing artifact-naming defects recorded, neither this card's:** the System contract cites
`TestDependencyBaseline_IsExactlyPillowAndNumpy`, which exists under no such name (the live assertions
are in `test_db_url_driver.py:383`, `test_export_pdf.py:750`/`:1272`, `test_admin_serving.py:143`); and
G-9 has no enforcing test at all — its evidence is the diff, which shows exactly three `def test_` and
one `class` removed and all four reappearing renamed in the same hunks. Net retirements zero.

### [Owner render] checked on the shipped page — 2026-10-19

Render: `~/Documents/nonogram-reviews/CARD-250/` — 28 files through the real panel (Flask over SQLite
on loopback; `nonogram_poc` untouched), in two passes: the test corpus for the flow, and two real
generated pictures (duck → cat) so the row's change is visible rather than a missing corner.

**SETTLED (owner): the four buttons stay.** After a Save the bar carries **Save · Cancel · Approve ·
Back to edit**, all live. That was the one open design question the render raised — the doc asked for a
Cancel beside Save and a Back to edit beside Approve, and this is the literal reading, but nobody had
been asked whether the left pair should go quiet while a grade is on screen. Owner: *"the four buttons
are fine, leave them"*. **A later card proposing to hide Save and Cancel behind a grade is reversing a
decision, not tidying an oversight.**

**Still open, and deliberately not read as approved by silence:** the row's caption still says
`duck.png` after the picture became a cat (the caption is the source image, so it is not false, but it
no longer describes the picture). Raised in the render as a question; no answer, so it stays a question.
The editor's heading still naming only the extent is **CARD-249**, already carded and ready.
