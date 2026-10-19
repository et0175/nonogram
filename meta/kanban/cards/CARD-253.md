# CARD-253: The player's reset confirmation names the button that opens it

**Status:** done
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 0.25d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/253-player-reset-confirmation
**Worktree:** ../PythonProject4-card-253
**Source:** owner, 2026-10-19 — "fix the player's confirmation wording too", after CARD-247 raised it and the owner first chose to leave it.
**Idea:** —
**Wave:** 48 (started on owner instruction)
**Depends on:** —
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_marking.py, tests/test_puzzle_solver_maybe.py, tests/test_puzzle_solver_hint.py, tests/test_puzzle_solver_percent.py, tests/test_puzzle_solver_progress.py, tests/test_puzzle_solver_resume.py
**Review score:** 9.5 (cycle 2/3 — certified, zero findings at every severity)
**Started:** 2026-10-19T18:45:33Z
**Closed:** 2026-10-19T23:36:28Z
**Actual:** 0.61d (4.8h wall clock: 1 review + 1 fix + 1 certification, 3 build gates, 1 merge gate)
**Merge commit:** 12e2c01
**Blocked by:** —

## What to implement

The player's reset **button** is called **Reset**. The confirmation it opens says **"Clear the board?"**
with an accept button **"Clear board"** — and since CARD-247 the player also has a **brush** called
**Clear**, two controls away. So the sentence names neither the button that opened it nor anything it
does, and the one word it does use belongs to a different control on the same toolbar.

Two strings in `src/nonogram/admin/templates/puzzle_solve.html`:

- `#puzzle-player-confirm-title`: `Clear the board?` → **`Reset the board?`**
- `[data-player-confirm="accept"]`: `Clear board` → **`Reset board`**

Then **23 locator sites across 7 test files** follow. Measured before carding: none of them is a
`parametrize` value, so **no node id carries the string** and no rename table is owed — this is the
cheap half of CARD-247's rename without the expensive half.

The editor's equivalent was already renamed under CARD-247 AC-7 (`Reset` / `Reset the board?` /
`Reset board`), so after this card the two pages agree.

## The trap: the editor's guard shape is WRONG here

CARD-247's AC-7 guards the editor with *"no control on this page carries the word Clear"*. **That
assertion would be false on the player and must not be copied** — on the player "Clear" correctly names
the fourth brush, which is the owner's decision (2026-10-19) and the whole reason this card renames the
confirmation instead of the brush.

The guard this page needs is the **relation**, not the absence: *the reset confirmation names the
control that opens it*. Build it that way, and make it fail for the right reason.

## Acceptance criteria

- **AC-1** (happy): *Given* the player page, *then* the reset confirmation's title and its accept button
  both read **Reset**, and neither says *Clear*.
  (test: `TestSolverReset_TheConfirmationNamesTheButtonThatOpensIt`)
- **AC-2** (guard, the relation — **and the one that must not be copied from the editor**): *Given* the
  player page, *then* the word in the reset button, in the confirmation title and on the accept button
  is **the same word**, and it is **not** the fourth brush's label. Assert the relation by reading all
  three off the rendered page, **not** by asserting a literal absence of "Clear" — the brush legitimately
  carries that word here. (test: same class)
- **AC-3** (guard, the brush is untouched): *Given* the change, *then* the fourth brush still reads
  **Clear** in the menu, in the trigger and in its accessible name — this card renames a confirmation,
  not a brush. (test: `TestSolverReset_TheBrushKeepsItsName`)
- **AC-4** (guard, no locator left behind): *Given* the 23 updated sites, *then* every one still drives
  or asserts the control it named before — a stale locator must fail loudly, never match nothing and
  pass. Show at least one updated site failing under a mutant that reverts the template string.
  (test: the updated files, plus the mutant recorded on the card)

## Guardrails

- G-1: **The fourth brush keeps the name `Clear`** (owner, 2026-10-19). This card moves the
  confirmation's words, nothing else.
- G-2: The editor's wording, renamed under CARD-247, is not touched again.
- G-3: `data-player-confirm="accept"`, the element ids and `role="alertdialog"` are unchanged — this is
  a wording change, not a markup change, so no behaviour, focus order or aria contract moves
  (CARD-211, ADR-0038/R4).
- G-4: No test retired, renamed or weakened; a locator update is not a rename (G-9's rule).
- G-5: No new runtime dependency (ADR-0006/R1), no colour literal (CARD-211 G-4).

## System contract

_Assembled 2026-10-19 by `system_rules.py --card CARD-253 --root meta/architecture` (38 rules returned)._

**Curated to 10 by rule; 28 dropped** under [`meta/kanban/curation.md`](../curation.md): keep every in-scope rule whose enforcement does not reach this card's new code.

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

- **[Do not take timing measurements]** Two sibling cards are live.
- **[Why this is a card and not a two-line commit]** 23 sites across 7 files, and the guard's shape is
  the opposite of the editor's. Both are cheap to get wrong and neither is visible in a diff.

### Implementation, 2026-10-19 (commit `2ba64a5`)

**The two strings** (`src/nonogram/admin/templates/puzzle_solve.html`, lines 181 and 184):
`Clear the board?` → `Reset the board?`, `Clear board` → `Reset board`. Nothing else in that
element moved: `data-player-confirm="accept"`, every id, `role="alertdialog"`,
`aria-labelledby`/`aria-describedby` and the Keep marks button are byte-identical (G-3), and the
diff is 4 lines.

**23 sites, as measured before carding** — the replacement found exactly 23 and the breakdown is
19 locators + 4 comments/docstrings: clues 1, hint 1, percent 1, maybe 2 (1 locator + 1
docstring), resume 5, marking 6 (3 locators + 3 comments), progress 7 (6 accept + 1
`get_by_role("alertdialog", name=…)`). No node id carried the string, confirmed by the family's
own collection guard, which reports no rename.

**Two files beyond Touches, both for a claim this rename made false.** `static/solver.js` quoted
`"Clear board"` in the reset paragraph of its header and called the wipe "a confirmed Clear" in
the BOARD CHANGE note; `puzzle_solve.html`'s own header listed "the reset confirmation" among the
four places a human reads the brush's name "Clear", which is now three. Comments only — no
executable line in either file changed.

**One file beyond Touches that the ACs made unavoidable:**
`tests/test_browser_fixture_scope.py`. Adding a browser test means recording its node id in
`ADDED_SINCE_BEFORE` with a card and a reason, or
`TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured`
reds with "tests added". The four new ids are registered; mutant M9 (below) is the control.

**The guard (AC-2), and why its shape is the opposite of the editor's.** CARD-247 AC-7 guards
`puzzle_edit.html` with "no control on this page carries the word Clear". Copied here it would be
false by design, because Clear is the correct name of the fourth brush. So
`TestSolverReset_TheConfirmationNamesTheButtonThatOpensIt` reads FOUR labels off the rendered page
through structural locators (`[data-player-action="reset"]`, `#puzzle-player-confirm-title`,
`[data-player-confirm="accept"]`, `[data-player-tool="unknown"]` — never by the label under test,
which would assume the answer) and asserts: the reset button is named by exactly one word; that
word is in the title and on the accept button; the brush's word is a different word and is in
neither. The setup is structural too — it reads `aria-disabled` off the reset locator instead of
`_is_disabled(page, "Reset")`, so the test fails on the relation rather than on a label.
`_control_label` asserts `count() == 1` and a non-empty label: a locator matching nothing returns
`""`, and an assertion about `""` is true for every possible implementation (CARD-250).

**Mutants — all nine run, 8 killed, 1 survivor recorded.** Each applied with `sed`, restored from
a byte-identical `cp -p` backup and `diff`-confirmed; never `git checkout --`.

| # | Mutant | Observed |
|---|--------|----------|
| M1 | accept button back to `Clear board` | **AC-4's evidence.** Red: AC-1, AC-2, and `TestSolverProgress_ResetAfterConfirm::test_ac320_thirty_marks_cleared_after_accepting` (an updated pre-existing site) |
| M2 | title back to `Clear the board?` | Red: the same three |
| M3 | fourth brush renamed `Reset` | Red: AC-2, AC-3. **The editor's guard shape would pass this** — a page with no "Clear" on it at all, one word again naming a brush and a board-wipe |
| M4 | reset BUTTON renamed `Clear` | Red: AC-2 and the progress site. The inverse collision, also invisible to an absence guard |
| M5 | `data-player-confirm="accept"` renamed | Red: all five. Loud, but it also unwires solver.js, so it shows loudness, not isolation |
| M8 | accept button emptied of its text | Red: AC-1, AC-2, the progress site — `count() == 1` plus the non-empty check, so a label locator matching nothing cannot pass |
| M7 | dialog loses `aria-labelledby` | Red: the announce test and the progress site |
| M6 | stale `aria-label="Clear the board?"` added beside `aria-labelledby` | **SURVIVED.** The accname algorithm prefers `aria-labelledby`, so the announced name is still the title. The test's docstring is narrowed to what this measures — the labelledby TARGET, not the absence of other labels — and M7 is what shows it can fail at all |
| M9 | the four new ids struck from `ADDED_SINCE_BEFORE` | Red: the family's collection guard, naming all four ids |

**Tests run** (never the full suite; the gate runs it solo): the 7 touched files +
`TestBrowserFixtures_NoTestAddedOrRemoved` → **288 passed**. Also, because they are coupled to
the template this card edits: `test_puzzle_solver_brush_menu.py` + `test_puzzle_solver_page.py`
(117 passed) and, after the header-comment change, brush_menu + marking (126 passed). The
editor's AC-7 guard was run and is untouched and green (G-2). No timing test was run and no
timing measurement taken.

**For the reviewer, hardest first.** (1) M6's survival is the one claim narrowed rather than
proven — read `test_the_dialog_announces_the_sentence_it_shows` and decide whether a test that no
wording mutant can red earns its place beside AC-2 (M7 reds it; the pre-existing progress site
covers the literal). (2) AC-2 compares casefolded word SETS, so it states "the reset button's one
word" and nothing about word order or punctuation — the title's wording freedom is deliberate and
only AC-1 pins the sentence. (3) The three files outside **Touches** (`solver.js` comments, the
template header, the `ADDED_SINCE_BEFORE` registry).

- **[Touches drift]** Three files beyond the card's **Touches**, all flagged by the agent, none
  silent: `tests/test_browser_fixture_scope.py` (+30 — a new browser test MUST register its node
  id in `ADDED_SINCE_BEFORE` or CARD-217's collection guard reds with "tests added"; the card's
  note that "no rename table is owed" was right about `RENAMED_SINCE_BEFORE` and wrong to imply
  the *added* registry was free), `src/nonogram/admin/static/solver.js` (comments only — its reset
  paragraph quoted the old string) and `puzzle_solve.html`'s own `{# #}` header (it listed the
  reset confirmation among the four places a human reads the brush's name — now three). No
  executable line changed in either of the last two.
- **[Gate]** Queued third in wave 48's serialized gate chain, behind CARD-225's solo re-measure
  and CARD-252's first build gate. Reason in CARD-225's notes: gates are solo, and this card's
  own 288-test browser run is what made that rule's gap visible.
- **[Build gate 1 — FAILED, and not this card's]** `2ba64a5`, solo: 5 failed, 8503 passed, 14:49.
  All five in `tests/test_admin_binding.py::TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine`,
  all `psycopg2.errors.UndefinedTable: relation "puzzles" does not exist` — raised inside the
  request the test asserts is served, i.e. in the server thread's query, not in the test's body.
  This card changed two template strings, four test files' locators and three comments. The file
  passes solo (33 passed, 5.4s).
- **[Build gate 2 — PASSED, same commit]** `2ba64a5`, solo: **8508 passed**, 1 skipped, 15:58,
  EXIT=0. 8503 + 5 = 8508, so gate 1's five failures are gate 2's five passes. Collection order is
  deterministic in this suite (no `pytest-randomly`), so a second run of the same commit that
  reproduces nothing rules out both "real" and "order-dependent" and leaves a **nondeterministic**
  cause. That is the signature `reset_engine()`'s docstring names (CARD-252): "failures that
  reproduced on no second run".
- **[What this costs the re-gate]** The owner's sequence is merge CARD-252, then re-gate this card.
  Worth saying plainly: a green re-gate on top of CARD-252 is **not** evidence the fix works,
  because this commit is already green on its second run without it. An intermittent failure that
  stops appearing is the one thing a single green run cannot distinguish from luck. The re-gate is
  owed as this card's own gate — it must pass on the tree it will merge into — and the question of
  whether CARD-252 actually stops the hazard needs the next several waves' gates, which is where
  wave 45 already left it.
- **[Build gate 3 / re-gate — PASSED]** `9a3cc21` (this card's work merged with `main`, so the tree
  now carries CARD-252's `reset_engine()` and CARD-247's merged work), solo: **8529 passed**, 1
  skipped, 15:42, EXIT=0. Third full suite on this card's code, second green one.
- **[What the re-gate does and does not establish]** It establishes what a gate is for: this card
  passes the full suite on the tree it will merge into. It establishes **nothing** about whether
  CARD-252 fixed the intermittent `relation "puzzles" does not exist` class, because build gate 2
  was already green on this card's own commit *without* that fix. Three runs of this card's suite:
  red, green, green — one fix landed between the second and third. That sequence cannot distinguish
  a fix from a failure that stopped appearing, and it is recorded that way rather than counted as
  evidence.

### [Review 1/3] Score 7.5 — FAILED on the severity gate (1 open Important)

Report: `meta/review/20261019T223846Z-CARD-253-cycle1.yml` (copied to main).

- **The card's three hardest claims were re-derived by mutation and all three hold.** The relation
  guard's shape: M3 (brush renamed "Reset") and M4 (reset button renamed "Clear") both red, and both
  are mutants **a copied CARD-247 absence guard would pass** — M3 leaves no "Clear" on the page at
  all. Not copying the editor's shape was the right call, and now it is measured rather than argued.
  `_control_label`'s `count() == 1`: the reviewer added its own **M10** (rename the title's id) to
  exercise the zero-match path without unwiring solver.js the way M5 does — it reds all three new
  tests, so CARD-250's failure mode is shut, not merely described. AC-4: M1 reds a pre-existing
  updated site **loudly**, on a `Locator.click` timeout against a zero-match locator, because
  `_button` uses `get_by_role(..., exact=True)` — and that same `exact=True` is what stops the new
  "Reset board" colliding with `_button(page, "Reset")` under Playwright's default substring
  matching, which would have been a real hazard of this particular rename.
- **F-001 (important, `tests/test_puzzle_solver_brush_menu.py:53/:227-230/:248/:285`) — the fourth
  site of the claim this card corrected three times.** CARD-247's "the brush's label appears in four
  places, including the reset confirmation" is false now, and this card is what falsified it. The card
  fixed that claim deliberately in `puzzle_solve.html`'s header and twice in `solver.js`, and missed
  the third file — which its own notes say it opened and ran. The suite therefore now asserts both
  things about one page, and a later reader has no reason to prefer the newer one. That half of the
  claim is also no longer coverage: no mutant on the brush's label can red it, because the
  confirmation no longer carries the label. It stays green only because the one confirmation element
  it reads is `#puzzle-player-confirm-text`, which this card did not touch.
- **Minors**: `meta/design/components.md:296` still quotes the old strings (weighted down — nothing
  pins that file to the templates, and CARD-247 set the same precedent); AC-3's new test duplicates
  `TestSolverBrushMenu_FourthBrushIsCalledClear` assertion-for-assertion and **kills no mutant that
  test does not already kill**, adding one genuinely new structural read; and
  `marking.py:1225`'s `assert "Clear" not in title…` sits after the two literal equalities, so it can
  never be the line that reds.
- **One correction to this card's own record, from the reviewer**: M7 is **not** the only mutant that
  reds the announce test — M10 reds it too, and M7 also reds the pre-existing progress site, so the
  literal is independently pinned there as the card claimed. The card's mutant table is what a later
  reader trusts, so the fix cycle carries that correction.
- **M6's survival re-confirmed, three runs**, and the narrowed docstring judged true as written: the
  accname algorithm does prefer `aria-labelledby`. The test earns its place because M7 and M10 are
  controls that can fail, and because it asserts a relation that survives the next rename where the
  progress site pins only today's literal.

### [Fix cycle 1] All four findings closed; F-001's name half decided and recorded

Report updated in place: `meta/review/20261019T223846Z-CARD-253-cycle1.yml` (all four
`status: fixed`). Comment- and docstring-only work plus one deleted assertion, one reduced test
and one register line; no executable source line changed.

- **F-001 (Important) — closed. The docstrings corrected; the test NAME kept, deliberately.**
  `tests/test_puzzle_solver_brush_menu.py`: the module docstring no longer lists the reset
  confirmation among the places the brush's label is read (three, not four), and a new paragraph
  says what this file still pins there — the confirmation's BODY line, "Every mark is cleared.
  Undo brings them back." — and points at `test_puzzle_solver_marking.py`'s
  `TestSolverReset_TheConfirmationNamesTheButtonThatOpensIt` for the title and accept button. The
  class docstring (`…FourthBrushIsCalledClear`) and the sweep test's docstring say the same, and
  the class's mutant paragraph now distinguishes the body line from the title/accept wording.
  `ADDED_SINCE_BEFORE`'s own CARD-247 reason carried the same false claim (a fifth site the review
  did not list) and is corrected with it.
- **F-001's name half: the name at `:248` is KEPT, with the measurement.** A
  `RENAMED_SINCE_BEFORE` entry for this rename is **refused by the registry's own guard on three
  independent grounds** — measured by driving `_rename_problems` over the entry that would be
  written: (1) the id is "not in CARD-217's record, so there is nothing here to move"; (2) "a move
  may rename a PARAMETER, not a test — … names a different test function, which is a coverage
  change and **belongs in neither table**"; (3) "also in `ADDED_SINCE_BEFORE`, so the derived
  baseline counts it twice". So "rename it with a proper rename-table entry" is not an available
  option for this id: the registry says a test-function rename is not a move. The only remaining
  route is to strike CARD-247's `ADDED_SINCE_BEFORE` entry and add a new one, which would record
  CARD-247's test as removed and CARD-253 as having added a test it did not write — a false entry
  in the register a later reader trusts, to fix a name. Against that, the name's cost is bounded
  and now documented: the test does still read the confirmation and does still assert a sentence
  on it ("Every mark **is cleared**"), so "the confirmation … say[s] clear" is not false of what
  the test asserts — only narrower than it used to mean, which the docstring right above it now
  states. The class docstring says the name is kept for that reason and points here.
- **F-002 (Minor) — closed.** `meta/design/components.md:296` (ResetConfirm) now reads
  "Reset the board?" / "Reset board", attributed `(CARD-253)` with the old strings and why they
  changed. Not generated — a hand-maintained register; updating it is one line. **Uncommitted**,
  like these notes: nothing under `meta/` is committed from a worktree.
- **F-003 (Minor) — closed by reducing, and renamed because the old name then over-claimed.**
  `TestSolverReset_TheBrushKeepsItsName` keeps only the structural read
  `_control_label('[data-player-tool="unknown"]') == "Clear"` — the one assertion
  `TestSolverBrushMenu_FourthBrushIsCalledClear` does not make. **G-6 survivor named**, in the
  class docstring and in the registry entry: that CARD-247 test covers the menu item's text, the
  trigger's text and the trigger's `Brush: …` name, and reds on the same mutant (M3). The node id
  changed (`…still_reads_clear_in_all_three_places` →
  `…_read_structurally_still_reads_clear`), so its `ADDED_SINCE_BEFORE` entry was rewritten —
  still CARD-253's own entry, so unlike F-001's name this rename records nothing false: no entry
  of another card is struck and the family's collection guard is green. Three places asserted in
  one place is not a claim the name can keep, which is why the reduction took the name with it.
- **F-004 (Minor) — closed by deleting the line.** `assert "Clear" not in title and "Clear" not in
  accept` is gone; the two literal equalities above it already imply it, and the reviewer's
  suggested casefolded replacement would have been dead in exactly the same way. AC-1's docstring
  now says there are two assertions and no third, names the CARD-250 family, and points at AC-2
  where the brush's word being absent **is** a relation a mutant can fail.

**Mutants for the changed claims — four, each applied with `sed`, restored from a byte-identical
`cp -p` backup and `diff`-confirmed (`RESTORED-IDENTICAL` after every run); never
`git checkout --`.** Two per changed claim, one inside the claimed region and one at its edge.

| # | Mutant | Observed |
|---|--------|----------|
| MA | confirmation body line → `Every mark is removed. Undo brings them back.` (inside brush_menu's narrowed claim) | Red: `…FourthBrushIsCalledClear::test_the_item_the_trigger_the_hint_and_the_confirmation_all_say_clear` **and nothing else** — so the body line really is what that file pins on the confirmation |
| MB | title back to `Clear the board?` (the EDGE of that claim) | **Both** brush_menu tests stay **green**; red: AC-1 and AC-2 in `marking.py`. The title's wording is no longer brush_menu's claim and is pinned where the docstring now points. Also re-proves AC-1 can red after F-004's deletion |
| MC | fourth brush renamed `Reset` (inside the reduced AC-3's claim; = M3) | Red: the reduced `test_the_fourth_brush_read_structurally_still_reads_clear`, both brush_menu tests and AC-2. The mutant AC-3 exists for still reds the reduced test |
| MD | `solver.js` `BRUSH_LABEL[UNKNOWN]` → `Cleared` (the EDGE: the trigger's text and name, nothing in the DOM menu) | Red: **only** the named survivor, brush_menu's first test. The reduced test stays green, which is exactly the division of labour its docstring claims |
| M10 | the title element's `id` renamed (the reviewer's, re-run here) | Red: all three tests of `…TheConfirmationNamesTheButtonThatOpensIt`, the announce test included — the correction to the M7 row above, measured rather than taken on report |

**Tests run in the fix cycle** (never the full suite; `meta/kanban/.full-suite.lock` checked absent
before each run; no timing measurement taken, another review was running):
`…FourthBrushIsCalledClear` + the two CARD-253 classes in `marking.py` +
`TestBrowserFixtures_NoTestAddedOrRemoved` + `TestSolverProgress_ResetAfterConfirm` → **27 passed**
on the fixed tree; then the five mutant runs above over the first three of those selections, each
followed by a `diff`-verified restore; then, after the last restore, the whole of
`tests/test_browser_fixture_scope.py` (the registry's own controls, M9's guard included),
`tests/test_puzzle_solver_brush_menu.py` (the file whose docstrings changed),
`tests/test_puzzle_solver_marking.py` and `TestSolverProgress_ResetAfterConfirm` →
**168 passed, exit 0**. `git diff --stat HEAD -- src/` is empty: every mutant was restored and no
source line changed in this cycle.

- **[Orchestrator] the name was kept because the registry refused the rename, and that refusal is
  the interesting part.** I gave the fix agent two priced options: rename with a
  `RENAMED_SINCE_BEFORE` entry, or keep the name and record why. It found a third fact instead —
  it drove `_rename_problems` over the entry that would have been written, and the registry's own
  guard refuses it on **three independent grounds**: the id is not in CARD-217's record so there is
  nothing to move; a move may rename a *parameter*, not a test, because a different test function is
  a coverage change that belongs in neither table; and the id is already in `ADDED_SINCE_BEFORE`, so
  the derived baseline would count it twice. So "rename it properly" was not an available option,
  and the only route left — strike CARD-247's entry, add a new one — would have recorded CARD-247's
  test as removed and this card as having added a test it did not write. A false entry in the
  register a later reader trusts, traded for a better name. Keeping the name is the right call, and
  it is now measured rather than asserted.
- **[Orchestrator] a fifth site, found by the fix and not by the review.** CARD-247's own
  `ADDED_SINCE_BEFORE` *reason* in `tests/test_browser_fixture_scope.py:813` ended "…and the reset
  confirmation" — the same stale claim, in the registry itself. Corrected in place with CARD-247's
  attribution left intact.
- **[Orchestrator] the card's mutant table was corrected against a re-measurement, not against the
  report.** The fix agent re-ran M10 itself rather than take the reviewer's word: it reds all three
  tests of the confirmation class, the announce test included. So this card's M6 row now says M7
  **and M10** are what show that test can fail at all, and `marking.py`'s own docstring — which named
  only M7 — says both. The table is what a later reader trusts; it is worth more than the time it
  cost to re-run.
- **[Orchestrator] `meta/design/components.md`'s ResetConfirm entry is updated on main.** The review
  weighted that Minor down because nothing pins the register to the templates and CARD-247 set the
  same precedent. It is fixed anyway: it was simply false, and a register nobody updates stops being
  one. The entry now carries the old strings and why they changed.

### [Review 2/3] Score 9.5 — **CERTIFIED**, zero findings at every severity

Report: `meta/review/20261019T230941Z-CARD-253-cycle2.yml` (copied to main). Zero Critical, zero
Important, zero Minor; the 0.5 below 10 is two recorded residuals, not a finding.

- **The cheap bound first**: `git diff --stat 9a3cc21 35298ca -- src/` is **empty**, so every
  src-side guardrail is delta-clean by construction and the whole mutation budget went on the
  evidence layer. The fix cycle's full delta is three test files, +78/−32.
- **F-001's closure is certified in both directions, measured.** **MA** (the confirmation's body line
  reworded) reds that one `brush_menu` test **and nothing else** across 75 — and the static half
  agrees: exactly one assertion of that line exists in `tests/`. **MB** (title reverted) leaves both
  `brush_menu` tests **green** and reds `marking.py`'s AC-1, AC-2 and the pre-existing progress site.
  That is the division of labour the new docstrings claim, and it is now a measurement.
- **The certifier measured the half nobody had.** The class docstring claims the title **or the
  accept button**; both cycles had only ever measured the title. Its own **ME** (accept button
  reverted to "Clear board") leaves both `brush_menu` tests green and reds AC-1 and AC-2 — so both
  halves of that sentence are true, and the sentence is no longer wider than its evidence.
- **The registry refusal re-derived a second time, independently.** All three refusals reproduce
  verbatim: the id is not in CARD-217's record, the id *is* in `ADDED_SINCE_BEFORE`, and a test-
  function rename is not a move. The certifier's judgement on keeping the name is worth keeping:
  *the register is machine-consulted and carries its own failing controls, so a false entry degrades
  the guard whose job is making a browser test's disappearance visible — buying a nicer identifier
  with a false record is the wrong direction of trade.* The name is narrower-than-it-reads, not false.
- **Sixth-site sweep: the set is closed.** `requirements.yml` has zero hits, `solver.js` is clean
  apart from the four-brushes list and `BRUSH_LABEL` itself, `components.md` is fixed on main, and
  CARD-247's attribution in the registry is intact (the fix is in the reason prose only). The
  remaining old-literal hits are per-card historical records and an unrelated game-spec checklist.
- **ADR-0039/R1 — the rule cycle 1 found violated — now holds and is measured.** No family
  attribution to make: cycle 2 raises no claim-family finding anywhere, so there is no third
  generation.
- **One bookkeeping catch, applied**: cycle 1's F-002 `fixed_in` said the edit was "in the worktree,
  uncommitted" when it was already landed on main in `5b501e9`. Corrected on main's copy of the
  cycle-1 report — a report that misstates where a fix lives is a report the retrospective reads
  wrong.

### Merged — `12e2c01`

- **[Merge gate — PASSED]** `3570982` (branch merged with `main`), solo: **8529 passed**, 1 skipped,
  14:18, EXIT=0.
- **[Actual against estimate]** 0.25d estimated. The two strings and the 19 locators were the 0.25d;
  everything past that was evidence — one review, one fix, one certification, and the fourth site of
  a claim this card falsified in three other files. Worth the retrospective's attention beside
  CARD-252's identical shape: **both cards were sized by their code change and spent their time on
  claims.**
- **[What the next person needs to know]** The player's fourth brush is still called **Clear**, and
  that is deliberate (owner, 2026-10-19). The editor's guard shape — *no control on this page carries
  the word Clear* — is **false on the player** and must never be copied there; the relation guard in
  `tests/test_puzzle_solver_marking.py` is the player's equivalent. `brush_menu.py` pins the
  confirmation's **body line** only; its title and accept button are pinned in `marking.py`. And the
  test name at `brush_menu.py:248` reads wider than what it asserts, on purpose: the registry refuses
  the rename, and a false register entry is a worse trade than a narrow name with the correction
  three lines above it.
