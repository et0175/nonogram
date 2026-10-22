# CARD-263: The error count becomes the first hint, not a free one — and the player stops being told

**Status:** blocked
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/263-errors-are-the-first-hint
**Worktree:** —
**Source:** owner, 2026-10-22, in conversation: *"I think it'll also make sense to not show the number of errors, or rather to show it on demand. In this case first hint may be number of errors (if any)"* — proposed while reviewing whether the player's hints could be made more sophisticated.
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_hints.py, tests/test_puzzle_solver_page.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** FR-044 **AC-354** pins the error counter's DOM presence and order, and **AC-312..315**'s verifying browser test asserts the counter `is_visible()` before reading it. The requirement must change before the code — `/forge:architect` delta on `requirements.yml`, then `decompose`. A drafted delta is in `## Proposed FR-044 delta` below. **EC-037 needs no change.**

## Why — a visible error count is a free hint, and it is the strongest one

The player shows `Errors: N` as a **live counter** in the toolbar (`solver.js:690-692`, rendered at
`puzzle_solve.html:208`), inside a `role=status` region with `aria-atomic="true"`, recomputed on every
stroke. A hint, by contrast, must be asked for and is counted (`hintCount`, `solver_state.js:664`).

So the design gives away the most valuable signal in the game — *"you have gone wrong"*, delivered the
instant it happens, unasked — and charges for cell reveals. **The cost structure is inverted.** Making
the count on-demand, and making it the first rung of the hint ladder, is the owner's proposal and it
makes the economy coherent for the first time.

**It also repairs a defect that is visible in the current code.** `hintCell`'s `known()`
(`solver_state.js:636-640`) treats a **wrong** mark as `UNKNOWN`:

```js
const known = (row, col) => {
  const state = board.cells[row * width + col];
  return state === truth(row, col) ? state : UNKNOWN;
};
```

So the hint reasons *around* the player's mistake and can hand back a correct cell while a contradiction
sits on the board. **Deducing from a poisoned board is worse than useless** — the player spends a hint
and advances a position that cannot be completed. Errors-first is therefore not merely cheaper, it is
the correct **rung 0**: there is no point offering a deduction on a board that admits none.

Third argument, secondary but real: on paper nobody tells you. Hiding the count is more faithful to the
game, not just stingier.

## What to implement

1. **The counter becomes on-demand.** `Errors: N` is no longer rendered continuously. The DOM keeps a
   place for it and the ARIA contract is preserved — see G-2, which is the part most likely to be got
   wrong.
2. **The hint ladder gains rung 0: errors.** One button. When the board has errors, the first press
   reports them; when it has none, the press behaves as today (a deduction hint).
3. **Rung 0 itself escalates, because a bare count is not help on a large grid.** Three errors on a
   30×30 sends the player hunting 900 cells. The ladder is: **count** → **locality** (the row or column,
   or a named region, holding at least one error) → **the cell**. Each press advances one step.
   *Decide and declare where locality lands between "a row" and "a quadrant"; the right answer probably
   depends on grid size, and a size-dependent rule must be stated, not inferred.*
4. **Non-revealing hints need their own accounting.** `hintCount` counts strokes on the undo stack
   carrying `hint: true` (`solver_state.js:664-666`). **An error hint changes no cell, so it is not a
   stroke, so the existing ledger would silently under-report it.** Decide whether a non-revealing hint
   is counted, and make the counter measure what is decided. Whatever is chosen, the replay contract
   (`solver_state.js:795-860`) must still reconstruct the hint count from the saved strokes — or the
   saved shape must grow to carry it, which is a storage-format change and must be said out loud.

## Acceptance criteria

- **AC-1** (happy) *Given* a freshly loaded board, *then* no error count is displayed anywhere until it
  is asked for. (test: `TestPlayerErrors_TheCountIsNotShownUntilAsked`)
- **AC-2** (happy) *Given* a board with at least one error, *when* the hint control is used, *then* the
  response is the error report — not a cell reveal — and no cell changes state.
  (test: `TestPlayerHints_RungZeroIsTheErrorReport`)
- **AC-3** (happy) *Given* a board with **zero** errors, *when* the hint control is used, *then* the
  behaviour is today's deduction hint, unchanged, and the existing hint ACs still hold.
  (test: `TestPlayerHints_WithNoErrorsTheLadderStartsAtTheDeduction`)
- **AC-4** (escalation) *Given* a board with errors, *when* the hint control is used repeatedly, *then*
  the report advances count → locality → cell, and each step is reachable and distinct. The locality
  step **names a region that provably contains an error** — asserted against the board, not against the
  step's own description. (test: `TestPlayerHints_TheErrorRungEscalates`)
- **AC-5** (boundary) *Given* a board whose last error is corrected while the ladder is part-way through
  rung 0, *then* the next press is a deduction hint and the ladder's position does not survive the board
  becoming error-free. (test: `TestPlayerHints_CorrectingTheLastErrorResetsTheRung`)
- **AC-6** (accounting) *Given* any sequence of hints, *then* the hint count the player sees equals the
  count the replay reconstructs from the saved strokes — **with at least one non-revealing hint in the
  sequence**, which is the case the current ledger cannot represent.
  (test: `TestPlayerHints_TheLedgerSurvivesANonRevealingHint`)

## Guardrails

- G-1: **The deduction hint's own behaviour is unchanged** when the board is error-free. CARD-183's
  hint ACs stay green and are not weakened, retargeted or deleted to make room.
- G-2: **The ARIA contract is preserved.** The error counter today lives in a `role=status`
  `aria-atomic="true"` region, and `puzzle_solve.html:148-150` documents a deliberate split between DOM
  order (Errors, Hints, Progress) and visual order (Progress, Errors, Hints), with a further FR-044 AC
  pinning *"'Progress: 0%' follows the error counter, then the hint counter, in DOM order"*. An
  on-demand count must not silently drop a live region or reorder the three — and a screen-reader user
  must not be *worse* served than today, which an unannounced on-demand value easily does.
- G-3: **No new information reaches the client.** The solution grid already ships to this player for
  CARD-162's count, behind the panel's door (ADR-0038/R6, CON-021). This card ships **nothing new** —
  it changes what is shown, not what is known. A public player must still never receive the solution.
- G-4: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-5: No new runtime dependency (ADR-0006/R1); stdlib + Pillow + NumPy only, and the player's browser
  code stays dependency-free.
- G-6: **No lateral import.** The player reimplements line logic natively in JS and must continue to —
  the project's precedent is `solver/propagate.py`'s `mask_runs` reimplementing a clue check rather than
  importing `clues.py`.
- G-7: Take no timing measurements and report no durations.

## Architecture context

- **FR:** FR-044 (the admin panel's puzzle player). **AC-312..315 and EC-037** define the error counter
  and are what this card changes — see `Blocked by`.
- **Components:** COMP-009 (the admin panel and its player assets). No solver or export change.
- **ADR:** ADR-0038/R6 and CON-021 (the solution reaches only this player, behind the door);
  ADR-0039/R1–R3 (a claim needs a control that can fail — live for AC-4's locality claim and AC-6's
  ledger).
- **Trace:** `meta/architecture/trace.yml` — FR-044's rows change if AC-312..315 do.

## Worktree notes

- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR files
  **case-insensitively** for the reach-limit idiom. Sanity check: `Touches` includes `tests/**` and
  `src/nonogram/**`, so ADR-0039 must be in the kept set.
- **[Do not take timing measurements]** other cards may share this machine.
- **[The sharpest trap: AC-4's locality claim is exactly the shape this board keeps failing]** *"one of
  your errors is in row 7"* is a claim about the board. It must be **asserted against the board** — that
  the named region contains at least one error — and not against the message the step generated. A
  message that describes its own input is the uncontrolled claim ADR-0039/R1 exists for, and three cards
  this week (CARD-206, CARD-259, CARD-262) were gated on precisely that shape.
- **[AC-6 is the one that will be got wrong quietly]** The replay contract rebuilds the board, the error
  count, the solved state **and the hint count** from the saved strokes alone
  (`solver_state.js:795-797`). A non-revealing hint has no stroke. So either the saved shape grows a
  field — a **storage-format change**, which needs saying out loud and a migration thought, since
  CARD-186 and CARD-246 already read saved games — or the count is defined so that non-revealing hints
  are not counted, which is a product decision and belongs on the card before the code.
- **[What this card deliberately does NOT take]** The richer deduction hints discussed with the owner on
  2026-10-22 are a **separate card**: ordering the deduction hint by the solver's per-cell rung tag
  (`SolveResult.rung_tags`, a `list[list[str | None]]` of `simple_overlap` / `line_dp` /
  `probe_contradiction`, already computed for the difficulty score and **never sent to the player**),
  naming the technique in the hint text, and hinting a **line** rather than a cell. Those need the rung
  grid added to the player's payload — a server change — whereas this card needs **no new data at all**.
  Kept apart for that reason, and because the line-level hint is the only option that would also work
  for a future *public* player, which is a requirement decision rather than an implementation one.
- **[Why `blocked` and not `ready`]** The error counter's continuous display is a shipped acceptance
  criterion with tests behind it. A card that implements against a contradicted AC fails its own AC/EC
  gate, and that gate is right to fail it. The unblock is one small architect delta on FR-044
  AC-312..315 and EC-037 — restating the counter as available on demand, and deciding whether the hint
  ladder's rung 0 belongs in FR-044 or in a new FR for hints, which currently have **no AC id at all**
  (`solver_state.js:556` says so: *"CARD-183, IDEA-074; FR-044 extension, no AC id yet"*). That gap is
  worth closing in the same delta: hints have been shipping since CARD-183 without a requirement behind
  them.

---

## Proposed FR-044 delta (drafted 2026-10-22, for `/forge:architect`)

**Read first, because it narrows the change:** the coupling is **not** where the card first said it was.
`AC-312..315` state the count's **arithmetic** — *"the error count reads 1"*, *"it reads 0 — undecided
cells never count"* — and AC-315 is already phrased *"when the error count **is read**"*. None of them
asserts continuous display. What breaks when the counter is hidden is their **verifying test**:
`TestSolverProgress_LiveErrorCount` is a browser test whose helper does

```python
counter = page.locator("[data-player-errors]")
assert counter.is_visible()          # tests/test_puzzle_solver_progress.py:143
return int(counter.text_content())
```

so the value is verified *through the visible DOM*. And the AC that actually pins presence is **AC-354**,
not AC-312..315. **EC-037 is pure arithmetic over any board and any matching solution, verified by
`PropertyTest_SolverProgress_ErrorCountMatchesTheDefinition` — it is unaffected and must not be
touched.**

### 1. AC-312..315 — `then` gains the request; statements otherwise unchanged

The arithmetic is right and should not move. Only make the read explicit, so the AC is satisfiable by a
count that exists on request:

```yaml
# .functional[43].acceptance[16]  (AC-312)  -- then:
then: the error count, when requested, reads 1
# likewise acceptance[17] (AC-313): ... when requested, reads 1
# likewise acceptance[18] (AC-314): the error count, when requested, reads 0 — the count is the
#          current number of wrong marks, not a running total
# acceptance[19] (AC-315) needs NO text change: it already says "when the error count is read"
```

And re-point all four `test:` fields from `TestSolverProgress_LiveErrorCount` to
`TestSolverProgress_ErrorCountOnRequest` — **renaming the class rather than keeping a name whose word
"Live" would then be false.** (This board has twice shipped a test name describing a retired statement:
EC-034's name on CARD-206, and CARD-221's `TestBookGuidePageType_*`, which named nothing at all.)

### 2. AC-354 — splits in two, because it currently conflates the row with the counter

Today: *"'Progress: 0%' follows the error counter, then the hint counter, in DOM order, on the error
counter's row at desktop width; the page has no horizontal scroll at 390 px."*

```yaml
# AC-354 (amended) -- the row without the error counter
given: the player page at desktop width and at 390 px
when: the counter row is read
then: '"Progress: N%" precedes the hint counter in DOM order on one row at desktop width, and the
  page has no horizontal scroll at 390 px'
kind: happy
test: TestSolverPercent_SitsNextToTheCounters

# AC-3NN (NEW) -- the requested count's placement and announcement
given: the player page with at least one wrong mark
when: the error count is requested
then: the count appears in the counter row and is announced once to assistive technology; it is
  absent from the DOM until requested, and requesting it does not move the progress or hint counters
kind: happy
test: TestSolverProgress_TheRequestedCountIsPlacedAndAnnounced
```

**The announcement half is the part that is easy to lose.** The counter today sits in a `role=status`
`aria-atomic="true"` region updated on every stroke, and `puzzle_solve.html:148-150` records a
*deliberate* split between DOM order (Errors, Hints, Progress) and visual order (Progress, Errors,
Hints). An on-demand value that silently drops the live region leaves a screen-reader user **worse
served than today** — so the new AC must assert the announcement, not only the placement.

### 3. Hints need a requirement at all — the real gap

`src/nonogram/admin/static/solver_state.js:556` says it outright: *"Hints (CARD-183, IDEA-074; FR-044
extension, **no AC id yet**)"*. Hints have shipped since CARD-183 with **nothing in the registry behind
them**, which is why this card has nowhere to attach a rung. Close that in the same delta — four ACs for
the shipped behaviour plus two for the new rung, so the new work extends a specified feature rather than
an unspecified one:

```yaml
# Shipped since CARD-183, specified here for the first time:
- id: AC-3NN   # a hint reveals one cell
  given: a board with at least one undecided cell
  when: a hint is taken
  then: exactly one undecided cell is set to its solution state and no other cell changes
  kind: happy
  test: TestPlayerHints_RevealsExactlyOneCell
- id: AC-3NN   # a hint is one undo step
  given: a board on which a hint has just been taken
  when: undo is used once
  then: the revealed cell returns to undecided and the hint count falls by one
  kind: boundary
  test: TestPlayerHints_IsOneUndoStep
- id: AC-3NN   # a hint prefers a deducible cell
  given: a board on which at least one undecided cell is forced by its row's or column's clue from
    the marks already correct on the board
  when: a hint is taken
  then: the revealed cell is one of those, not an arbitrary undecided cell
  kind: happy
  test: TestPlayerHints_PrefersADeducibleCell
- id: AC-3NN   # the ledger survives a reload
  given: a saved game carrying hints
  when: it is replayed
  then: the hint count reconstructed from the saved strokes equals the count before the reload
  kind: boundary
  test: TestPlayerHints_TheLedgerSurvivesAReplay

# New, this card's subject:
- id: AC-3NN   # rung 0 is the error report
  given: a board with at least one wrong mark
  when: a hint is taken
  then: the response reports the errors and no cell changes state
  kind: happy
  test: TestPlayerHints_RungZeroIsTheErrorReport
- id: AC-3NN   # rung 0 escalates and its locality claim is true of the board
  given: a board with at least one wrong mark
  when: hints are taken repeatedly
  then: the report advances from a count to a named region to a cell, and the named region provably
    contains at least one wrong mark
  kind: happy
  test: TestPlayerHints_TheErrorRungEscalates
```

**The last `then` is worded the way it is on purpose.** *"The named region provably contains at least one
wrong mark"* makes the claim checkable **against the board** rather than against the message the step
produced. A message that merely describes its own input is the uncontrolled claim ADR-0039/R1 exists
for, and three cards this week — CARD-206, CARD-259 and CARD-262 — were gated on exactly that shape.

### 4. One EC worth adding, because the accounting has no invariant

```yaml
- id: EC-0NN
  statement: For any sequence of player actions, the hint count displayed equals the number of hints
    reconstructable from the saved strokes — including hints that reveal no cell
  kind: consistency
  instances: [the four shipped hint ACs and the two new ones]
  test: PropertyTest_PlayerHints_TheLedgerMatchesTheReplay
```

This is the invariant the current design cannot satisfy: `hintCount` counts strokes marked `hint: true`
(`solver_state.js:664`), and an error report **is not a stroke**, so it would be silently uncounted. The
EC forces the choice to be made — either the saved shape grows a field, which is a storage-format change
with CARD-186 and CARD-246 already reading saved games, or non-revealing hints are defined as uncounted
and the displayed count says so.

### What is NOT in this delta

Nothing about the richer deduction hints (rung-ordered, technique-named, line-level). Those need the
solver's per-cell `rung_tags` in the player's payload, and the line-level variant raises a question this
delta should not answer by accident: whether a future **public** player gets hints at all, given
ADR-0038/R6 and CON-021 confine the solution to the admin player. That is a separate decision, and it is
in `meta/kanban/backlog.md`.
