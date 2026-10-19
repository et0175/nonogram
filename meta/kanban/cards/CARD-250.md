# CARD-250: The editor's two bars say what they do — Cancel leaves, "Back to edit" stays, and both exits land on a fresh list

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/250-editor-exits
**Worktree:** ../PythonProject4-card-250
**Source:** owner's doc "Nonograms - Print layout" → "Puzzle editor", 2026-10-19 — items 1, 2, 3 and 4 (intake in `meta/architecture/inputs/raw-requirements.md`)
**Idea:** —
**Wave:** 47
**Depends on:** —
**Touches:** src/nonogram/admin/static/puzzle_edit.js, src/nonogram/admin/templates/puzzle_edit.html, src/nonogram/admin/templates/_puzzle_table.html, src/nonogram/admin/static/admin.css, src/nonogram/admin/app.py, tests/test_puzzle_editor_ui.py, tests/test_admin_design_tokens.py
**Review score:** 7.5 (cycle 1/3 — below the 8 threshold; two Important)
**Started:** 2026-10-19T07:15:19Z
**Closed:** —
**Actual:** —
**Merge commit:** —
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
- **AC-5** (happy, Approve exits): *Given* an approved edit, *then* the store holds the new grid
  **and** the browser is on `/puzzles`.
  (test: `TestPuzzleEditor_ApproveCommitsThenReturnsToTheList`)
- **AC-6** (happy, the stale picture — **the failing-first one**): *Given* a puzzle whose grid is
  edited and approved, *when* the list is shown, *then* the thumbnail is the **new** grid. The test
  must be shown failing against the pre-card tree with the two SVGs differing.
  (test: `TestPuzzleEditor_TheListShowsTheEditedPicture`)
- **AC-7** (guard, the exits cannot outrun the store): *Given* a save in flight, *when* Cancel or Back
  to edit is pressed, *then* the page does not navigate and says so, exactly as a second Save is
  refused today.
  (test: `TestPuzzleEditor_NoExitWhileTheStoreIsDeciding`)
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

**Curated to 8; 49 dropped and declared.** Nearly all of the projection is scoped `src/nonogram/**` or `src/nonogram/admin/**.py` — package-wide, so it matches every card on this board and narrows to nothing. Owner decision 2026-10-17: ship the curated form with the dropped count stated. Kept below are the rules a reviewer can hold *this diff* against.

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

**The one place AC-7 is read narrowly, flagged for the reviewer.** AC-7 names Cancel *and* Back to
edit. Cancel is refused mid-flight in words and with `aria-disabled`. Back to edit is **not**
refused: it never leaves the page, so it has nothing to outrun, and refusing it would change the
behaviour G-1 says to rename rather than change (and would break
`test_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer`, which AC-10 says passes
unchanged). What AC-7 asks of it — the page does not navigate, and it says what it did — is asserted
by `test_back_to_edit_pressed_mid_flight_does_not_navigate_either`. The asymmetry and its reason are
written in `puzzle_edit.js`'s header, in `inFlightIs`, and in both tests' docstrings. **Not treated
as a guardrail conflict**, because both halves of AC-7's *then* clause hold for both buttons.

**Consequence of AC-5 worth a second look.** A successful Approve now leaves the page, so nine
existing browser tests could no longer wait on the "Saved" sentence on a bar the browser has left.
Eight now wait on the list (`_wait_for_the_list`); the one that must read the sentence
(`test_a_second_approve_pressed_in_flight_is_not_sent_either`) holds the page with a 204 on the
navigation (`_stay_on_the_editor`) and keeps every assertion it had.
`test_approving_from_the_keyboard_commits` lost one assertion about where focus went after a
successful approve — there is no bar left to stand on; the named survivors are
`test_the_whole_flow_runs_from_the_keyboard` (Back to edit) and
`test_an_approval_of_a_grid_the_store_no_longer_remembers_asks_to_verify_again` (a refusal keeps the
page), both of which still assert the focus discipline. `storedText`'s tail changed from "Your board
is untouched — go on editing" to "Showing the puzzle list…", because the old sentence became false
the moment the page started leaving.

**Runs.** `tests/test_puzzle_editor_ui.py tests/test_admin_design_tokens.py` — 106 passed (in the
default random order and in `-p no:randomly`). Also run green as the shared-template blast radius:
`test_admin_tier_surfaces.py`, `test_puzzle_edit_routes.py`, `test_puzzle_edit_store.py`,
`test_card_060_grid_renderer_surface.py`, `test_puzzle_review_bulk_read.py`,
`test_batch_requested_tier.py`, `test_admin_filter_side_range_and_name.py`,
`test_admin_rename_strategies_batches.py`, `test_admin_review_actions.py`, `test_admin_serving.py`,
`test_card_065_follow_ups.py`, `test_card_066_status_filter.py`, `test_puzzles_list_pagination.py`,
`test_book_floor.py`. The full suite is the orchestrator's gate; it was not run here. No timing
measurements taken.

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
