# CARD-253: The player's reset confirmation names the button that opens it

**Status:** in_progress
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
**Review score:** —
**Started:** 2026-10-19T18:45:33Z
**Closed:** —
**Actual:** —
**Merge commit:** —
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
