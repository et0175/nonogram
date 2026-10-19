# CARD-250: The editor's two bars say what they do — Cancel leaves, "Back to edit" stays, and both exits land on a fresh list

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/250-editor-exits
**Worktree:** —
**Source:** owner's doc "Nonograms - Print layout" → "Puzzle editor", 2026-10-19 — items 1, 2, 3 and 4 (intake in `meta/architecture/inputs/raw-requirements.md`)
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/static/puzzle_edit.js, src/nonogram/admin/templates/puzzle_edit.html, src/nonogram/admin/templates/_puzzle_table.html, src/nonogram/admin/static/admin.css, src/nonogram/admin/app.py, tests/test_puzzle_editor_ui.py, tests/test_admin_design_tokens.py
**Review score:** —
**Started:** —
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
