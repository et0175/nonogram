# CARD-246: A generated puzzle can be edited by hand, from its card or the list, and approved on its new difficulty

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/246-manual-puzzle-editor
**Worktree:** ../PythonProject4-card-246
**Source:** owner's doc "Admin panel", 2026-10-18 — "start from a puzzle card or the list of puzzles, add a button - edit… Then show a message with difficulty and cancel/approve buttons"
**Idea:** —
**Wave:** 46
**Depends on:** CARD-245 (the verify-and-grade path this UI calls; without it there is nothing to approve)
**Touches:** src/nonogram/admin/templates/puzzle_edit.html, src/nonogram/admin/templates/puzzles.html, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/app.py, tests/test_puzzle_editor_ui.py, tests/test_admin_serving.py
**Review score:** —
**Started:** 2026-10-18T08:31:25Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The owner's flow, end to end:

1. An **Edit** button, reachable from **both** entry points the owner named — a puzzle's own
   card and the puzzle list (`/puzzles`).
2. An editor: the puzzle's grid, paintable by hand.
3. **Save** hands the edited grid to CARD-245's verify path.
4. A message showing the **recomputed difficulty**, with **Cancel** and **Approve**.
5. Approve commits. A grid without a unique solution is never storable, and the message says so
   rather than failing silently.

**Reuse the player's board; do not build a second one.** `static/solver.js` and
`solver_state.js` already render a grid, carry four brushes (Black / White / Maybe / Undecided),
paint on click and drag, and keep an undo history. `app.py:5571`'s `/puzzle/<id>/solve` route
already reads one puzzle and hands it to `solver.js` — and its docstring is explicit that it is
**not** the uniqueness solver, it only reads and renders. That is exactly the shape this editor
needs. A second grid renderer in this panel would be the kind of duplicate ADR-0036/R3 forbids
elsewhere for round marks, for the same reason: two implementations of one picture drift.

**But an editor is not a solver, and the difference is load-bearing.** In the player, a mark is
the *solver's guess* and `Maybe` is a note to self. In the editor, a cell is either **filled or
empty in the answer** — there is no third state, because `Puzzle.grid` is `list[list[bool]]`
(ADR-0012's boundary type). So the editor must map its marks down to booleans before saving, and
decide what `Maybe` and `Undecided` mean on the way out. **Do not silently coerce them.** Either
hide those two brushes in edit mode, or refuse to save while any cell is still undecided and say
which cells — but say which, in the notes and to the user.

## Acceptance criteria

- **AC-1** (happy, both entry points): *Given* the puzzle list and a single puzzle's card,
  *then* each offers an Edit control that reaches the editor for that puzzle.
  (test: `TestPuzzleEditor_ReachableFromListAndCard`)
- **AC-2** (happy, the editor shows the real grid): *Given* a stored puzzle, *when* the editor
  opens, *then* it renders that puzzle's own grid — the filled cells are the stored filled cells,
  at the stored width and height. (test: `TestPuzzleEditor_OpensOnTheStoredGrid`)
- **AC-3** (happy, the confirm step): *Given* an edit whose grid is uniquely solvable, *when*
  Save is pressed, *then* a message shows the **recomputed difficulty** — score and tier — with
  Cancel and Approve, and **nothing is stored until Approve**.
  (test: `TestPuzzleEditor_SaveShowsDifficultyThenApproveCommits`)
- **AC-4** (negative, Cancel changes nothing): *Given* that message, *when* Cancel is pressed,
  *then* the stored puzzle is unchanged and the owner is returned to the editor with their edit
  intact — cancelling must not also discard the work.
  (test: `TestPuzzleEditor_CancelKeepsTheEditAndStoresNothing`)
- **AC-5** (negative, a non-unique edit): *Given* an edit with zero or several solutions, *when*
  Save is pressed, *then* the message says the puzzle cannot be saved and **offers no Approve**,
  and the stored puzzle is unchanged. The refusal is stated in words the owner can act on, not an
  exception. (test: `TestPuzzleEditor_NonUniqueEditCannotBeApproved`)
- **AC-6** (edge, no third state reaches the store): *Given* an edit where some cell is left
  `Maybe` or `Undecided`, *then* the chosen rule is applied and **asserted** — whichever of
  "those brushes are unavailable in edit mode" or "the save is refused and names the cells" you
  implement, the test states which. A cell silently becoming `false` is the defect.
  (test: `TestPuzzleEditor_NoUndecidedCellReachesTheStore`)
- **AC-7** (guard, a booked puzzle offers no Edit): *Given* a puzzle `in_a_book`, *then* the
  Edit control is absent or disabled **and** the route refuses it. A disabled button alone is not
  a guard. (test: `TestPuzzleEditor_BookedPuzzleIsNotEditable`)

## Guardrails

- G-1: **The player is not regressed.** `/puzzle/<id>/solve` keeps its current behaviour exactly;
  the editor is a second consumer of the shared board, not a change of the first. The player's
  own tests must pass untouched.
- G-2: No second grid renderer. If the shared board needs a mode flag, add one; do not fork
  `solver.js`.
- G-3: The uniqueness verdict and the difficulty are **never computed client-side** and never
  trusted from the client — they come from CARD-245's server path. This card ships no JS that
  decides whether a puzzle is valid.
- G-4: Accessibility is not optional here: the Edit control and the Cancel/Approve message are
  keyboard-reachable and announce their state, following the pattern CARD-211 set for the Region
  toggle (`aria-pressed`, and `role="status"` for the announce line in `puzzle_solve.html:152`).
- G-5: No new runtime dependency (ADR-0006/R1).
- G-6: No test retired without a named survivor (CARD-220's rule).

## System contract

_Assembled 2026-10-18 by `system_rules.py --card CARD-246 --root meta/architecture` (57 rules returned, `card_scope: touches`). A projection — fix the source artifact, never this list._

**Curated to 12; 45 dropped and declared.** The projection returned **57**, of which **45** are scoped `src/nonogram/**` — package-wide, so they match every card in the project and narrow to nothing. Owner decision 2026-10-17: ship the curated form (6–14 rules, kept where the rule's scope names a file this card touches or the card names the rule's artifact) with the dropped count stated. This is not a judgement that the dropped rules do not apply — it is that a ~57-rule contract measurably produces **fake** coverage on this board: reviews emitted a count line claiming all rules checked while marking 45–48 of 53 `⚠ unchecked` and writing 6–12 verdict lines, where 10- and 13-rule contracts produced full coverage. The root cause is the package-wide scoping and is tracked in `meta/kanban/backlog.md`.

- **ADR-0006/R1** — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party
  package joins the installed dependencies without revising this ADR. Non-executable static assets
  (fonts and similar data files) may ship as package data instead, and doing so is not a dependency
  change. (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- **ADR-0036/R1** — compute_layout called without a PageSpec produces exactly today's A4 geometry;
  CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test:
  TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- **ADR-0036/R2** — Book page geometry is computed only by COMP-007's layout functions
  (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin
  panel does not fit cells or place grid lines itself. (check: review-lens)
- **ADR-0036/R3** — Exactly one function in src/nonogram/** puts a round mark on a page. A second
  one is a defect whatever Pillow call it is written with: four cards print the same difficulty
  glyph, and four slightly different dots cannot be fixed once a book is on paper. (check: test:
  test_the_books_own_pages_carry_no_undeclared_round_mark)
- **ADR-0036/R4** — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a
  codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: the cheapest
  way to print a difficulty dot is to append a bullet to a header string, and that route bypasses
  the one drawing site and CON-020's type floor… (check: test:
  test_no_module_types_a_round_mark_as_a_character)
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

- **[Depends on CARD-245 for a reason that is not just ordering]** The whole value of this card
  is that the owner cannot store a broken puzzle. If this UI ships against a route that does not
  yet gate, it ships the opposite of its purpose. Do not stub the verify call to get the UI
  moving — if CARD-245 is not merged, say so and stop.
- **[The CARD-230 lesson, which this card is well placed to repeat]** That card's ACs described
  behaviour that already shipped, because it was written from a sibling card's *title* rather
  than from the code. Before writing a test here, open `solver.js` and
  `templates/puzzle_solve.html` and establish what the board **already** does — four brushes,
  drag painting, undo, the Region mode, the `aria-pressed` toggle, the `role="status"` announce
  line. Some of AC-2's work may already exist; say so rather than claiming it.
- **[`quality_score` is an open question on CARD-245, and it surfaces here]** Whatever is decided
  there — keep, null, or re-measure — this editor is where a hand-edited puzzle becomes
  distinguishable from a generated one, so the list and the card may need to show it. Read
  CARD-245's "Open question" section before designing the confirm message.
- **[House rules]** `hypothesis` is **not** in the dependency baseline. Prefer an independent
  second implementation over re-deriving a value with the function under test. Capability modules
  never import laterally (`tests/test_cli.py` has an `ast` guard). Baselines are re-recorded with
  provenance; no earlier fixture is regenerated or deleted.
- **[Browser tests]** ADR-0038/R8: browser tests fail or skip **loudly** with a named reason and
  never pass silently, and `pytest-playwright` stays in the dev-only extra (ADR-0038/R7). If this
  card's UI claims need a browser, respect both.
