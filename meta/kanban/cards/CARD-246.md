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

### [Review 1/3] Score: 7.0 — FAIL (threshold 8)

Report: `meta/review/20261018T170220Z-CARD-246-cycle1.yml`. **No criticals.** Five importants,
every one demonstrated **in Chromium** rather than argued from the source, and every one in a
single file (`static/puzzle_edit.js`). **None corrupts the store** — CARD-245's gate holds behind
all of them — so this is a fix, not a redesign.

**What held, and it is most of the card.** Every structural claim the review was told to attack
survived: the `mode` flag is a sound seam, the player's path through all four of its branches is
unchanged, its payload is still exactly CARD-160's six keys with `mode` not among them, and 161
player tests ran green **with none re-run for flakes**. AC-1, AC-2, AC-4, AC-6, AC-7 (all three
halves, separately pinned by three different mutants), G-1, G-3, G-5 and G-6 are **genuinely
covered**. G-2 is covered in substance. 12 of the reviewer's 15 mutants died.

**Two of the agent's own judgments were independently confirmed:**

- **The AC-6 argument is "plainly true".** `COLOUR_ORDER` steps `FILLED→EMPTY→UNKNOWN→FILLED`,
  so two White clicks on a filled cell land on `UNKNOWN` and a confirmed Clear blanks every cell
  — **a blank cell is reachable with Black and White alone**, so brush-hiding could never have
  been the guarantee and the agent was right to overrule the orchestrator's lean. The reviewer
  added what neither of us had: it is closed **server-side** too, since a crafted POST of
  non-booleans is a 422 at `_refuse_unless_shaped_like_a_grid`, covered by CARD-245's own suite.
- **M10 reproduced exactly.** Restoring all four brushes fails **only** the narrowing test while
  the other six AC-6 tests pass — so "the narrowing is a convenience, the refusal is the
  guarantee" is measured, not asserted.
- **G-3's proof was judged "as strong as it sounds"**: the verify route stubbed with `score 7`,
  tier `fiendish` — a grade no local arithmetic could produce — with the page asserted to show it
  while `easy` is absent. No uniqueness or difficulty decision leaks into the client.

#### The five importants: the flow is right and its edges state falsehoods

The common thread, and the reason this is briefed as **one invariant rather than five patches**:
*the page must never offer Approve for a grid other than the one whose grade is on screen, and
must never claim a store state it has not confirmed.* Three of the five **show the owner a false
statement about what happened**, which is worse than an error message.

- **F-001 — a refusal message standing beside a live Approve.** `onSave` withdraws a pending
  Approve only at the *top* of the call; the refusal branch returns without withdrawing, and
  nothing disables Save in flight. Demonstrated by racing two Saves: the valid response lands
  first (grade shown, Approve offered), the invalid one lands second, and the message becomes
  "This grid cannot be saved and nothing was stored…" **while Approve is still live and
  `verified` is still set.** Pressing it stores a grid the owner is being told cannot be saved.
- **F-002 — a stroke during the confirmation is silently dropped, and the page says the
  opposite.** Save → grade → one White click → Approve: the store holds the **pre**-stroke grid,
  the board shows the **post**-stroke grid, and the message reads "Saved. This grid is the stored
  puzzle now…". **The owner's last stroke exists in no store and gets no warning.** The most
  user-visible defect on the card, and the owner validates visually.
- **F-003 — a dropped connection leaves the page silent with an uncaught rejection.** `fetch` is
  unwrapped: the message stays "Checking this grid...", `Failed to fetch` reaches the console,
  Save stays enabled. The tell that this was *meant* to be handled is that `refusalText`'s own
  "The panel could not be reached" branch is **unreachable dead code**. On Approve it is worse —
  the owner cannot tell whether it committed.
- **F-004 — "Approve never re-reads the board" is pinned by nothing.** The mutant that makes
  Approve re-read the board passes **49/49**. So the card's stated guarantee is today a property
  of **CARD-245's** 409 and is asserted nowhere here. That is the same shape as CARD-245's own
  G-1 finding: a guarantee resting on a neighbour's behaviour rather than on its own control.
- **F-005 — the booked 409 is given the not-verified 409's advice**: "Cannot edit a puzzle that
  is in a book. **Press Save to check this grid again.**" — an instruction that can never
  succeed. The file's own comment records the conflation, and **CARD-245 distinguishes the two
  409s in `_edit_refusal` precisely so a caller can**, so the information is already on the wire.

#### Two findings about the card's own evidence, which are the ones worth learning from

- **F-006 — a vacuous control of the agent's own making.** `test_the_editor_writes_nothing_into_
  the_players_save` passes with `NO_SAVE` **removed entirely**, because `serializeState`
  independently refuses a non-blank start. The claim survives only through its end-to-end
  sibling. A control that cannot fail is the defect this board has paid for most often.
- **F-007 — the `player-cell` glob is a literal guard, not the completeness guard G-2 claims.**
  The reviewer added `static/editor_grid.js` with `createElement` and `class="editor-cell"` and
  **it passed**. This is the third time in wave 46 that a guard claimed completeness it did not
  have (after CARD-245's default-allow predicate and its alias hole), and the brief says the same
  thing it said there: derive the guard from something that cannot be renamed around, or narrow
  the claim to what it actually checks.

**Minors and nits routed into the fix:** F-008 (after Approve the header tier badge still reads
the **pre-edit** tier while the message says "with the difficulty shown above" — badge HARD,
stored tier easy), F-009 (the flag is branched on in **four** places, not the three the notes
claim; `nextHint` is a dead fourth), F-010 ("editable" is spelled three ways, so a falsy-but-
present `book_id` would show a control the route 409s), F-011 (Approve's double-click safety is
**accidental** — it works only because CARD-245 declines to consume a verification, recorded
nowhere and untested), F-012 (the stale-clue disclosure is the last clause of an eight-sentence
paragraph *below* the save bar, and the gutters themselves say nothing), F-013, F-014 (the 13th
browser-test file sits outside `test_puzzle_solver_*.py`, so CARD-235's PAGE_ISOLATION
declaration guard cannot see it), F-015.

**F-016 is wrong and was not briefed as a fix.** It reports the card as `Status: ready`,
`Started: —` — but it is reading the **worktree's** copy, which was branched from main *before*
the dispatch stamp commit. Main's copy is correctly `in_progress`, wave 46, with `Started` and
`Worktree` set. Verified both. Likewise its note that `Touches` "was never reconciled" is
already closed — the field was amended in main at dispatch review, and the agent's own claim that
`solver_state.js` was missing from it was recorded as wrong. **An agent reading a worktree's
`meta/` is reading a snapshot, not the board**, and that is worth remembering for every future
review brief.

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

### Review cycle 1 — fix notes (2026-10-18)

- **The invariant, rather than five symptoms.** The page may never offer
  Approve for a grid other than the one whose grade is on screen, and may
  never state a store state it has not been told. `static/puzzle_edit.js` now
  names the four mechanisms that carry it (THE INVARIANT) and each has a test
  that fails when that mechanism alone is taken out:
  1. **`tell(text, offer)` is the one writer** of the message line and of the
     Approve offer. The offer is an argument of the sentence that describes
     it, so "a refusal standing beside a live Approve" (F-001) is no longer a
     state this file can be in — there is no path that writes one without the
     other. It used to take two paired calls and the refusal branch made only
     one of them.
  2. **`turn`.** Every request is asked in a turn; the turn advances on each
     request and on every recorded board change, and an answer from a spent
     turn is dropped instead of told.
  3. **One request at a time** (and `aria-disabled` to say so), which closes
     F-001's root cause and makes F-011's double-click safety this page's own
     rather than a property of CARD-245 not consuming a verification.
  4. **The board announces its own changes.** `solver.js` dispatches
     `BOARD_CHANGE` in edit mode from `commit()` — the single place a change
     is RECORDED, so the editor needs no list of controls to watch — and the
     editor withdraws the offer and says so. Approve still sends the grid
     captured at Save and never re-reads the board (F-002, F-004).
- **The store's answer is the one thing never dropped**: it is the only report
  of what the store did. `fetch` is wrapped; no answer at all is `code: 0`,
  which on a save says that whether the grid was stored is not known here and
  to reload — never "Saved", never silence (F-003). `refusalText`'s
  "could not be reached" branch is reachable now and asserted.
- **The two 409s are told apart on the wire** (F-005): CARD-245's refusals
  carry `reason` (`not_unique` / `not_verified` / `in_a_book` / `not_found`,
  declared as `EDIT_REFUSAL_REASONS`) beside their words, so the booked case
  no longer gets "press Save again" — an instruction that can never succeed.
  Branching on the server's prose was the alternative and is not a wire
  contract.
- **The editor page claims no difficulty of its own** (F-008): the header tier
  badge was a fact about a stored grid on the one page where the stored grid
  is being rewritten. The grade is said where it is true — in the save bar,
  from the solve, then from the row that was stored.
- One spelling of "editable" (F-010, `puzzle_is_editable` over the store's
  `_holds_a_book`, read by the row, the card's payload and the route); one
  payload builder for the two board pages (F-015); the stale-gutter disclosure
  moved above the board (F-012); the G-2 guard derived from the page's script
  set and from "builds grid nodes" rather than from one class name (F-007);
  the vacuous localStorage control now seeds a real entry (F-006); this file's
  page isolation declared and checked locally, because CARD-235's glob cannot
  see it (F-014); the EDIT MODE contract counts its own branches (F-009).

### [Fix 1/3] the five importants closed as ONE invariant, made structural rather than remembered

Commits `a8b5442` (6 files, +1061/−147) and `7ad7bf8` (a test-synchronisation correction, kept
as its own commit rather than a bare `--amend`).

**The invariant:** *the page may never offer Approve for a grid other than the one whose grade is
on screen, and may never state a store state it has not been told.* Both are now properties of
the code's **shape**, not of paired calls remembered at five call sites.

**Verified by the orchestrator, because this is the claim the whole cycle rests on:**
`tell(text, offer)` really is the **single writer** of both the message line and the Approve
offer. I brace-matched the function and counted: `decide.hidden` is assigned **once, inside
`tell()`, and nowhere else**; the only assignment to `verified` outside it is its own
declaration (the two other apparent matches are `===` comparisons, which my first pattern caught
by accident — stated so the count is not read as a second writer). **So "a refusal standing
beside a live Approve" is not a state this page can represent**, rather than a state it avoids by
remembering to call a second function. That is the difference between a fix and a patch.

Four mechanisms, each with a test that fails when that mechanism alone is removed:

1. **`tell(text, offer)`** — the offer is an *argument of the sentence that describes it*, so
   every sentence states its own offer and none can leave the previous one's Approve standing.
2. **`turn`** — advanced on each request **and on every recorded board change**; an answer from
   a spent turn is dropped rather than told.
3. **One request at a time** — a guard at the top of each handler, announced with
   **`aria-disabled`, not `disabled`**.
4. **`BOARD_CHANGE`** — dispatched from `solver.js`'s `commit()` in edit mode only, i.e. **the
   single place a board change is recorded**, so clicks, drags, undo, redo, a confirmed Clear and
   `setBoard` are all covered *without the editor keeping a list of controls to watch*. The same
   reasoning as deriving a guard from an enumerable authority instead of hand-listing it
   (ADR-0039/R2) — applied to events.

**Plus one asymmetry that F-003 forced, and it is the right one:** the store's answer is the one
thing **never** dropped, because it is the only report of what the store did. `fetch` is wrapped
and "no answer at all" is `code: 0`, which on a save says the outcome **is not known here** and
to reload — **never "Saved", never silence**. A page that cannot know must not claim.

**All three of cycle 1's surviving mutants now die**, including the one that made Approve re-read
the board. 15 of 16 new mutants died.

#### It refused three of the review's four suggested mechanisms, and was right each time

- **"Disable Save" was the wrong instrument.** `disabled` removes the button from the tab order
  and **drops focus to the document mid-flow**, which fights G-4 — the flow is keyboard-driven
  and CARD-211's pattern is `aria-pressed`/`aria-disabled`. It used `aria-disabled` to *say* the
  state and a handler guard to *prevent* the request; the guard is what the mutants die on.
- **F-004's suggested fix is not implementable as written.** "Assert no POST carried the painted
  grid" needs a POST — and once the withdrawal exists, Approve with a moved board **posts
  nothing**. So the property is pinnable only by taking one of the two mechanisms out of the way,
  which is what its test does and documents: a capture-phase listener ahead of the editor's
  suppresses the announcement, a cell is painted, the offer is asserted still up (proving the
  suppression took), and then the POST body **and** the store are asserted to hold the *graded*
  grid. **That is the fourth suggested fix this wave that could not reach its own case** — the
  pattern is now firm enough to carry to the retrospective.
- **F-003's "unreachable dead code" was not quite right**: the fallback *was* reachable by any
  status outside 200/404/409/422 (a panel 500, a proxy 502). What was unreachable was the
  no-answer case it was written for. The defect was real; the description was not.
- **F-010 was three spellings of two different questions** — both page-side spellings also tested
  `status != 'in_book'`, so the drift risk was narrower than stated. Same fix, truer framing.

#### Its one honest disclosure, flagged to cycle 2 rather than accepted

Removing the single-flight guard from `onApprove` **alone** kills nothing, because
`tell("Storing this grid…")` already clears the offer synchronously so a second click returns at
the `verified === null` test. The fix says so plainly, shows the **combined** mutant does kill a
test, and keeps the guard "so a reader need not reason about `tell`'s side effect". **Whether
that is sound defence-in-depth or an unreachable disjunct presented as load-bearing is exactly
the shape cycle 2 flagged on CARD-224 (F2-006), so it is briefed to the reviewer as a question
rather than taken as an answer.** A redundant guard whose removal nothing notices is how a later
refactor deletes a mechanism silently.

**F-008's resolution is a product decision and is recorded as one:** the editor page now renders
**no tier badge at all**, on the reasoning that a badge is a fact about a *stored* grid displayed
on the one page where that grid is being rewritten — stale on the first stroke, never mind
Approve. The difficulty is said where it is true: the save bar, from the solve, then from the row
the store wrote. Flagged for the reviewer to judge as an improvement or a loss, because the owner
validates visually.

**F-012's deferral is accepted as reasoned:** the disclosure moved into `.editor-note` **above**
the board in bold, and the gutters were left undimmed deliberately — dimming is a visual change
on a **shared** renderer, so it belongs in a card that produces a render for the owner's eye, not
in a fix cycle. **F-014 was declared locally** rather than by widening CARD-235's
`_family_files()` glob, because that glob keys CARD-235's own collection-drift baseline and
allowlist and widening it would mean registering ~65 node ids — the right fix for *that* card,
not this cycle. Both deferrals name what they are not doing, which is the standard this board
asks for.

**Four server changes, each argued rather than assumed:** a machine-readable `reason` on
CARD-245's refusals (the alternative was matching the server's **prose** in JavaScript, which is
not a wire contract), `puzzle_is_editable` plus `editable` in the details payload (the only way
"one spelling" is true for a control the *client* draws), the shared `_board_page_payload` (the
duplication was server-side), and dropping `tier_label` from the editor route. All additive.

### [Review 2/3] Score: 8.5 — PASS (threshold 8, improvement +1.5 against a 0.5 floor)

Report: `meta/review/20261018T175800Z-CARD-246-cycle2.yml`. Both thresholds met, so the card is
**cleared to merge on score**. One new important, and a third cycle is being run anyway — the
same judgment taken on CARD-245 and CARD-224 this wave: a score that passes does not settle
whether something should merge.

**All five of cycle 1's importants closed, with each leg separately pinned**, and **both** of
cycle 1's surviving mutants now dead. 13 of 15 new mutants killed. The four server changes were
judged **all four earned**, with two details worth keeping: CARD-245's route tests are *genuinely*
untouched (the diff touches only this card's own test file on the test side, `reason` is additive,
and no test anywhere asserts an exact body shape — the reviewer grepped), and **the player's
payload is still exactly CARD-160's six keys *and in the same order*** — `mode` goes into a
separate dict literal before the update, so with `mode=None` the embedded JSON is byte-identical,
which is why 161 player tests never moved.

**The three structural claims were confirmed on their own terms, not accepted:**

- **`commit()` really is the single recording site.** `history` is assigned in exactly two places
  — `start()`'s initialiser and `player.commit` — and `setBoard` routes through it, as do clicks,
  drags, hint, undo, redo and the confirmed Clear. The reviewer probed Undo and Clear in Chromium
  with a grade on offer: **both withdraw the offer with the right words.**
- **`aria-disabled` plus a handler guard genuinely prevents a second request.** Both handlers run
  their guard synchronously and reach it before the first `await`, so every later activation in
  the same or a later task returns at the guard. Two mutants die on *two activations in one task*
  — the real double click. The attribute is the announcement, the guard is the mechanism, and the
  code says so.
- **F-008's badge removal was judged an improvement**, with one residual loss named: the
  *pre-edit* difficulty is now nowhere on the page, so a before/after comparison is gone. One
  line if the owner misses it, and it belongs in a card that produces a render.

#### ⚑ G-001 (important, new) — a save the page cannot read says "Nothing was stored" while the store HAS written

**I verified this statically myself.** In `refusalText`, `storing` is read **only** inside
`if (code === 0)`. Every other branch asserts "Nothing was stored" unconditionally — including
the catch-all `"The panel answered with ${code}, which this page does not know how to act on"`.
And **this card's own cycle-1 correction established that the catch-all is reachable** by any
status outside 200/404/409/422: a panel 500, a proxy 502.

Demonstrated end to end by the reviewer: it let the Approve reach the panel and replaced only the
**answer** with a 200 carrying `text/html`. The werkzeug log shows `POST /puzzle/<id>/edit 200`,
**the store holds the edited grid**, and the page reads *"Nothing was stored…"*. A 502 gives the
same sentence, and no `pageerror` either time.

**Why it is being fixed although the score passed.** The panel is deployed **behind a proxy**, so
this is reachable in the configuration production actually runs: a gateway that times out *after*
the app committed returns 502, the owner is told their edit was not stored, presses Save again,
and buys a second solve and a second `manually_edited_at` stamp for a grid that was already in.
And it is precisely what **THE INVARIANT in the card's own header forbids** — *may never state a
store state it has not been told*. **Cycle 1's F-003 was this defect one branch over**: the fix
threaded `{storing}` through and then read it in one place.

**The distinction briefed to the fix** is an allow-list rather than a patch per branch: the
knowable set is **CARD-245's own refusals** (`not_unique`, `not_verified`, `in_a_book`,
`not_found`, and bare 404/409/422), because those never write; everything else on a save is
unknowable and must not claim. That shape makes a **fifth** refusal reason added later fail safe
instead of lying — which is the same lesson as CARD-245's default-deny guard, and it ties to
G-007 below, since `EDIT_REFUSAL_REASONS` is currently read by no production code at all.

#### The disclosure was one-sided, and the reviewer found the other half

The fix had honestly disclosed that removing `onApprove`'s `inFlight` guard alone kills nothing.
The reviewer removed **the other half** — making the offer survive the "Storing this grid…"
sentence — and **that also passes 65/65**. So **neither mechanism is pinned alone and only the
pair is**, and the rationale given ("the guard stays so a reader need not reason about `tell`'s
side effect") leaves that side effect itself unasserted. Judged **sound defence-in-depth, not an
unreachable disjunct** — both branches are taken on every Approve, and the guard is what makes
the guarantee local to this file instead of borrowed from CARD-245, which was cycle 1's F-011
complaint. So both stay; the unasserted one gets its assertion. **An honest disclosure is still
only as good as its symmetry** — that is the transferable part.

**Minors and nits routed into the third cycle:** G-003 (`getBoard()` sees the drag preview while
`BOARD_CHANGE` fires from `commit()` — bounded by the gesture, and **it is also the window that
makes the F-004 test pin a reachable property rather than an unreachable path**, a point the
reviewer made in the card's favour), G-008 (`onCancel` is outside the turn discipline — not
owner-reachable today, the reviewer verified both controls are `display:none` mid-flight), G-004
(a div/`innerHTML` grid builder *inside* `puzzle_edit.js` survives the rebuilt G-2 guard, which is
wider than the declared limit — **the third guard in this wave to claim completeness it did not
have**), G-006 (F-012's relocation is unpinned, which is how it ended up below the save bar in
the first place), G-007, G-010 (a backlog line for CARD-235's glob — the local declaration was
judged **adequate** and the card does **not** owe the glob change, but nothing makes the *next*
out-of-glob browser file declare anything).

**G-009 is the worktree-snapshot artefact again** — the review reports the card as
`Status: ready` with uncommitted notes because it reads the worktree's copy of `meta/`, branched
before the dispatch stamp. Main's copy is correct. Second time this wave; the brief now says so
explicitly so a reviewer does not spend a finding on it.
