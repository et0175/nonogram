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
**Touches:** src/nonogram/admin/templates/puzzle_edit.html, src/nonogram/admin/templates/puzzles.html, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/puzzle_edit.js, src/nonogram/admin/templates/_puzzle_table.html, src/nonogram/admin/static/admin.css, src/nonogram/admin/app.py, tests/test_puzzle_editor_ui.py, tests/test_admin_serving.py
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

### Implementation notes (CARD-246, 2026-10-18)

- **AC-6's rule: "the save is refused and names the undecided cells".** The
  brushes are *also* narrowed to Black and White in the editor's menu, but
  hiding them could not be the guarantee and the code says why:
  `solver_state.js clickedState` makes a repeat click's third step **blank**
  for Black and for White alike, and a confirmed Clear blanks every cell, so
  an undecided cell stays reachable with two brushes on offer. The refusal
  therefore lives in `static/puzzle_edit.js` (it names the cells, 1-based, up
  to six of them, and sends **no request**), resting on
  `solver_state.js answerOfBoard`, which returns `grid: null` whenever any
  cell is neither filled nor empty — there is no coerced grid for a caller to
  send. Both are asserted, and the mutant that puts all four brushes back
  kills only the narrowing test while the six refusal tests still pass, which
  is the evidence that the rule is the refusal.
- **The mode flag (G-2).** One grid renderer. `GET /puzzle/<id>/editor`
  serves the player's payload with `"mode": "edit"` added; `solver.js` reads
  that one flag (its `EDIT MODE` section is the contract) and it changes three
  things: the board starts on the stored grid (`boardOfGrid`), the browser
  save is off (the player's save is keyed by the puzzle id, so sharing it
  would overwrite the solve-in-progress of the puzzle being edited), and
  `showProgress` returns at once — no counters, no banner, no solved lock
  (the board opens *equal* to the solution, so the lock would fire before the
  first stroke) and no clue circles. The editor's page leaves out the elements
  that go with them; `actions.hint` became optional (`?.`) and nothing else in
  the player's code moved.
- **The page is at `/puzzle/<id>/editor`, not a GET of `/puzzle/<id>/edit`.**
  CARD-245 pinned a GET of the save path as a 405
  (`TestPuzzleEditRoutes_Refusals.test_a_get_is_not_allowed`), which is the
  canary that says a write can never be reached by a GET. Serving a page there
  would have retired that canary's spelling for nothing, so the editor took
  its own path and CARD-245's suite is untouched (G-6: no test retired).
- **An `EditNotVerified` (409) is reported as a step, not an error:** the
  message says nothing was stored, relays the store's own words and asks the
  owner to press Save again, which costs one re-verify and no work. An
  eviction of the memo is the same outcome and is tested by clearing the
  store's `_verifications`.
- **What AC-2 already had**, per the CARD-230 warning: the board, the four
  brushes, drag painting, undo/redo/reset, Region's `aria-pressed`, the
  `role="status"` announce line and zoom are all CARD-160..CARD-212's and were
  reused unchanged. What is new on the page is the two-brush menu, the save
  bar and the absence of the solution-relative controls.
- Out of scope, deliberately: no "hand-edited" filter on the list (CARD-245
  declared it too), no live re-derivation of the clue gutters as the owner
  paints (they are the stored puzzle's clues and the page says so; the clues
  that get *stored* are the ones the save re-encodes), and no change to
  `quality_score`/`recognizability`, which CARD-245 settled.

### Orchestrator: the scope gate, and the two judgments the agent made against its brief (2026-10-18)

`c7e2d7e` — 8 files, +1604/−6, of which **1033 lines are one new test file** (49 tests).

**[Touches drift]** Two files changed that the field does not name, three named that did not change:

| file | verdict |
|---|---|
| `src/nonogram/admin/static/puzzle_edit.js` | **new**, and genuinely missing from the field |
| `src/nonogram/admin/templates/_puzzle_table.html` | the field says `puzzles.html`; the list **row** lives in the partial, not the page |
| `templates/puzzle_solve.html` (named) | **not changed — that is G-1**, and the right outcome |
| `tests/test_admin_serving.py` (named) | not changed; nothing here affects deployment |

Zero new components (all COMP-009), so the scope gate's trigger is not met. The field is
amended above.

**One correction to the agent's own report:** it says the `Touches` list "misses
`static/solver_state.js`". It does not — `solver_state.js` is listed. `puzzle_edit.js` is the
only genuine omission. Recorded because an agent's account of a card is itself a claim.

#### It overruled the orchestrator's lean on AC-6, and the reason is better than the lean

I had leaned toward "hide the two brushes in edit mode" as the AC-6 rule. **The code disagrees
and the agent was right to say so:** `solver_state.js clickedState` makes a repeat click's third
step **blank** for Black *and* for White, and a confirmed Clear blanks every cell — so an
undecided cell stays reachable with only two brushes on offer, and "those brushes are
unavailable" **could never have been the guarantee.** It did both: the menu narrows to two
brushes (asserted separately, as a narrowing) and **the refusal is the guarantee**, resting on
`answerOfBoard` returning **`grid: null`** whenever any cell is neither filled nor empty — so
there is no coerced grid for any caller to send, rather than a grid a caller must remember not
to send. That is the ADR-0039/R2 shape (default-deny by construction) applied to a UI payload.

**Mutant M10 is the evidence the choice was right, and it is the cleanest single result in this
card:** putting all four brushes back **kills only the narrowing test while all six refusal tests
still pass.** So the refusal does not depend on the narrowing — which is exactly what "the
narrowing is a convenience, the refusal is the guarantee" has to mean to be true.

#### It protected a CARD-245 test instead of retiring its spelling

Its first cut served the editor page as a `GET` of `/puzzle/<id>/edit` — and that broke
CARD-245's `TestPuzzleEditRoutes_Refusals::test_a_get_is_not_allowed[/puzzle/{}/edit]`, which
pins a GET of the **save** path as 405. That assertion is a canary: **a write must never be
reachable by a GET** (prefetch, crawler, a pasted link). Rather than retire its spelling to make
room, the editor took its own path, `/puzzle/<id>/editor`. CARD-245's suite is untouched, G-6
holds with no test retired, and the route docstring records why. This is the first time on this
board that a card has **re-routed its own design to avoid weakening a sibling's guard**, and it
is the behaviour the G-6 rule exists to produce.

#### The flakes, and why they are not this card's

The agent reported three player tests failing in one loaded run and did the right thing rather
than the convenient thing: it **A/B-ed the implicated test by checking the three player-facing
files out at the parent commit `6184545` and back — 3 passed at the parent, 3 passed at its own
commit** — noted that the failing *parameter* moved between runs (`[phone]` then `[floor]` of the
same ring-geometry test), that a 19-second re-run took over ten minutes under load, and that all
three are load-sensitive measurements (a resize-debounce draw count and two pixel-fit
measurements on a 30×30). With the machine quiet the two files ran **89 passed**. The build gate
is where this is settled, and the lock note records the condition.

**G-3's proof is the one worth copying.** Structural assertions that "the editor decides no
uniqueness" are weak. Instead the verify route is **stubbed with a grade no local arithmetic
could produce** (`score 7`, tier `fiendish`) and the page is asserted to show it **while `easy`
is absent** — a page computing the difficulty itself would show 33/easy. That is a claim about
where a number came from, tested by making the server's answer impossible to guess.

### [Build gate] PASSED (full, 2026-10-18)

`EXIT=0` · **8300 passed, 1 skipped, 0 failed** · pytest's own figure **1091.59s** · commit
`c7e2d7e` · `DATABASE_URL` **SET** (this worktree's derived database) · under
`meta/kanban/.full-suite.lock`, released after. **First-attempt green.**

Collected 8252 → 8301 (**+49**), reconciling exactly with the new test file's 49 tests. The one
skip is the platform `setrlimit` one, unrelated to this card and the same skip every gate since
CARD-223 has reported.

**The gate settles the flake question, which is why it was the right place to settle it.** The
implementation agent reported three player tests failing in one loaded run and A/B-ed them clean
at the parent commit; this gate ran **the whole player family inside the full suite and all of
them passed**. So the A/B conclusion stands on gate evidence rather than on the agent's own
re-runs, and nothing is owed here. Had they gone red, this board's operating rule would have
applied — a single red test in a file the card does not touch is re-run before it is believed,
and the re-run recorded — but it did not need to be invoked.

Not written to `suite-timing.log`: that series is merge gates only, and this run shared the
machine with CARD-224's review cycle 2. The verdict is unaffected (separate derived databases
since CARD-244); the duration is not comparable.
