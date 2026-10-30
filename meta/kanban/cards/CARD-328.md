# CARD-328: The public player's duplicated looks are held to the admin's — the dot and the solved reveal, declared after the fact

**Status:** review
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.75d <!-- The claim-card floor (owner, wave 50): a card whose subject is a CLAIM or a MEASUREMENT may not be estimated as trivial, whatever its diff size. This card's entire deliverable is the claim "two implementations agree", so the floor applies. It was first scoped at 0.5d in conversation before the rule was applied. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false <!-- Deliberately. TDD's red→green loop assumes production code to write; here the behaviour ALREADY SHIPPED (`2400501b`) and the deliverable is the guard over it. A guard written against working code is green on its first run by construction, so "watch it fail" is meaningless and MUTATION is the discipline that carries the weight instead — see the AC-5/AC-6 mutant pairs. -->
**Branch:** `card/328-player-looks-agree`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-328
**Source:** owner decision 2026-10-30, after the owner asked whether to revert `2400501b` and card it, or fold it into CARD-268's gate. Neither: the work is green and well evidenced, and CARD-268 cannot absorb it (disjoint footprint, and the commit is already CARD-268's rebase baseline — folding it in would attribute a public-player feature to an admin-player card's merge commit and make that card's record false). This card is the third option — **declare what shipped, review it, revert nothing** — and it owns the one debt the commit created.
**Idea:** —
**Wave:** 69 <!-- JOINS the wave in flight (precedent: CARD-291 joined wave 65 on 2026-10-28) rather than opening 70, because CARD-268 is still that wave's card and this is its second slot under the owner's cap of 2. Measured intersection with CARD-268's ACTUAL diff: EMPTY. Checked more sharply than a Touches comparison, because this card's guard READS two files CARD-268 writes: `admin.css` (+129) and `solver.js` (+196). Re-derived at dispatch -- CARD-268 adds only `.player-probe*` and `.player-cell[data-probe]` rules and touches NEITHER `.player-cell[data-state="empty"]::after` (the dot) NOR `player-solved-flash` / `player-solved-in` / `--player-wave` / `is-solved` (the sweep), and does not touch solver.js's `--player-wave` line. So this card's compared surface is untouched by the card it runs beside. -->
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_public_player_agreement.py, player/player.css, player/play.js
**Review score:** **8.0 (cycle 1/3) — does NOT certify.** Threshold met (`min_score: 8`) but **one open important finding**, and the rule is score >= 8 AND no open critical/important. IMP-1: each declared divergence exempts the WHOLE FACT, so real drift inside an exempted key is invisible — the reviewer fired four mutants into exempted content and **all four survived**, dumping the exempted fact's value under each to prove the guard had READ the change and stayed green. Independently re-fired by the orchestrator: changing the admin sweep to flash **empty** cells instead of filled ones left the guard at **23 passed in 0.10s**. Zero critical. MIN-1 (a tautological arm), MIN-2 (parse failures bundle attribution), NIT-1/2.
**Started:** 2026-10-30T14:36:59Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What already shipped, and is NOT this card's to rebuild

`2400501b` *"player: the white mark is a dot and solving is revealed, matching
the panel"* landed on `main` on 2026-10-30, outside the card pipeline, on two
owner calls. It is **green and measured** — `tests/test_public_player.py` plus
`tests/test_public_player_pages.py`, **67 passed, 0 skipped, exit 0**, re-run by
the orchestrator on 2026-10-30 (zero skips matters: every skip in this suite is
`DATABASE_URL`-gated and the browser fixtures refuse loudly when Chromium is
absent, so a green-with-skips could not be mistaken for this).

What it changed, from its own commit message and re-derived here:

1. **The empty mark became a dot.** It was a cross — two `linear-gradient`
   strokes painted into the cell's background — while the panel drew a centred
   dot, so one mark meant two things depending on which player you opened.
2. **Solving now plays a reveal.** The banner settles in (220 ms) and the
   filled cells flash the success colour in a diagonal sweep (440 ms each,
   12 ms a step) before ending in ink, keyed on `body[data-solved]` because
   `play.js` already writes that attribute on every render. Under
   `prefers-reduced-motion` the banner and frame still appear with no motion.
3. **`play.js:352` now sets `--player-wave` (row + col)** when it draws the
   board, *"exactly as solver.js sets it for admin.css"*.

**Its tests are good and are not to be rewritten.** Two calls in them are worth
preserving by name, because a later card could undo either by accident:

- The reveal is asserted through the computed `animation-*` properties and
  **not** through `getAnimations()` — a CSS animation leaves that list when it
  finishes, so a test reading it **races the 440 ms it is testing**.
- The dot is asserted through the `::after` box **and** through the cell's own
  `background-image` being `none`, so **the cross cannot come back as a
  background**. A two-direction assertion.

## Why this card exists: ADR-0041/R3 protects two files, and these looks are outside it

The commit reimplemented the admin's rules rather than sharing them, and
justified it correctly: ADR-0041/R3 copies `solver_state.js` and `tokens.css`
byte-identically **and nothing else**, so the admin's rule is *the look this
matches, not a file this one reads*.

**That reasoning is right, and it is also the whole problem.** R3 mandates
byte-identical copying **because copies drift**. These two behaviours now sit
outside that protection, parallel-maintained, with **nothing checking they stay
in agreement** — measured 2026-10-30:

**Identical today, declaration for declaration:**

| | admin | public |
|---|---|---|
| the dot | `admin.css:648` | `player.css:425-434` |
| selector | `.player-cell[data-state="empty"]::after` | the same |
| declarations | `content`, `display`, `width: 28%`, `height: 28%`, `margin: auto`, `border-radius: 50%`, `background: var(--color-text-secondary)` | the same seven, same values |
| `@keyframes player-solved-in` | `admin.css:1055` | `player.css:449` |
| `@keyframes player-solved-flash` | `admin.css:1056` | `player.css:450` |
| the sweep's shorthand | `player-solved-flash calc(2 * var(--duration-base)) var(--ease) calc(var(--player-wave) * 12ms)` | the same, with a `, 0` fallback |
| `--player-wave` | `solver.js:730`, `row + col` | `play.js:352`, `String(row + col)` |

**Legitimately divergent, and this is the half a naive guard would get wrong:**

- **The selector.** Admin keys the sweep on `.player-board.is-solved`; the
  public page keys it on `body[data-solved="true"]`. Different DOM hooks for a
  stated reason (`play.js` already writes the attribute on every render, so the
  reveal fires on the transition into solved and does not re-trigger while it
  stays solved). **Not a drift.**
- **The `, 0` fallback** in the public page's `var(--player-wave, 0)`.
- **The reduced-motion block's COVERAGE.** <!-- CORRECTED 2026-10-30 by the
  implementation round, and the error was the orchestrator's. This line read
  "admin has 4, the public sheet has 1", which is `grep -c 'prefers-reduced-motion'`
  — a STRING count read as a BLOCK count. Re-derived: `admin.css` has exactly ONE
  `@media (prefers-reduced-motion: reduce)` block, at :1061; its other three hits
  (:872, :1059, :1259) are prose comments mentioning the feature. Both sheets have
  ONE block, so the block count is NOT a divergence and declaring it would have been
  the stale exemption AC-4 forbids. The real divergence is what the one block covers.
  This is the board's own rule — a figure is counted from the rows, never from a
  narrative or a string match — failing in a card brief. -->
  Both sheets have exactly **one** `@media (prefers-reduced-motion: reduce)` block.
  What differs is its reach: admin's silences **5 selectors** with
  `animation: none !important; transition: none !important` (it has toolbar and stage
  chrome to quiet); the public sheet's silences **2** with `animation: none`. The
  **block count is compared separately and must agree at 1 = 1** — it is not declared,
  precisely because it is not a divergence.

So a guard asserting "the two sheets are the same" would be **false**, and one
asserting only the dot would miss the sweep entirely. The guard this card owes
asserts the **shared** parts and **declares** the divergences, so a change to
either kind is visible instead of silent.

## What to implement

1. **`tests/test_public_player_agreement.py`** — a new file, in the test tree,
   where reading both sheets is legal (the public page itself can never import
   from `src/`; the test tree can read both files, which is the precedent
   CLAUDE.md names for exactly this situation — `solver/propagate.py`'s
   `mask_runs`, cross-checked from the test tree rather than imported across).
2. **The dot: exact agreement.** Parse the `.player-cell[data-state="empty"]::after`
   rule out of each sheet and assert **declaration-set equality** — property
   names and values, insensitive to formatting and order, since one is
   single-line and the other multi-line. Not a string comparison of the rules.
3. **The sweep: shared parts asserted, divergences declared.** Assert the
   keyframe names and bodies match, the duration/easing/step formula matches,
   and **both** JS files set `--player-wave` to `row + col`. Then declare the
   three divergences above **as a frozen set with its reason**, so adding a
   fourth reds rather than passing. **State the pattern wherever a reader meets
   it**: an exemption with no shape constraint and no control is the defect
   CARD-255 shipped (two executable setters under its exempted prefixes left
   its test green).
4. **Do not change behaviour.** Nothing in this card alters a rendered pixel.
   If the guard finds a real disagreement, that is a **finding to raise** with
   the owner — the admin and the public page disagreeing about a mark is the
   defect `2400501b` existed to fix, and deciding which side is right is not a
   worktree call.
5. **Pointer comments** in `player/player.css` and `player/play.js` naming the
   guard, so the next person to edit either look finds the thing that will red.
   One line each, no more.

## Acceptance criteria

- **AC-1** (the dot's agreement is exact and mechanical): *Given* both
  stylesheets, *then* the `.player-cell[data-state="empty"]::after` rule's
  declaration set is **equal** in both — seven properties, same values — and the
  comparison is over parsed declarations, not over rule text. (test:
  `TestPlayerLooksAgree_TheDotIsDeclarationForDeclarationTheSame`)
- **AC-2** (the sweep's shared parts agree): *Given* both stylesheets, *then*
  `@keyframes player-solved-in` and `@keyframes player-solved-flash` have equal
  bodies in both, and the sweep's animation shorthand agrees on name, duration
  formula, easing and the `* 12ms` step. (test:
  `TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep`)
- **AC-3** (both players compute the same wave): *Given* `solver.js` and
  `play.js`, *then* each sets `--player-wave` to `row + col` — asserted over the
  source of both, so a change to either side's formula reds. (test:
  `TestPlayerLooksAgree_BothPlayersSetTheSameWave`)
- **AC-4** (the divergences are declared, not discovered): *Given* the guard,
  *then* the three known divergences (the sweep's selector, the `, 0` fallback,
  the reduced-motion block counts) are a **frozen declaration with a stated
  reason each**, and a fourth divergence in the compared surface **reds**.
  (test: `TestPlayerLooksAgree_ADivergenceMustBeDeclared`)
- **AC-5** (the dot guard can fail — two mutants): *Given* the guard, *then*
  changing `28%` to another value in **either** sheet reds AC-1, and so does
  changing `var(--color-text-secondary)` in either. **Four mutants, two per
  side**, because a guard that reads only one sheet would pass half of them.
  (evidence: the mutant table in `## Worktree notes`)
- **AC-6** (the sweep guard can fail at its edge — two mutants): *Given* the
  guard, *then* changing the `12ms` step in either sheet reds AC-2, and changing
  `row + col` to `row` in either JS file reds AC-3. (evidence: the mutant table)
- **AC-7** (nothing rendered changes): *Given* the branch, *then* no rendered
  pixel differs from `main` — `2400501b`'s own tests pass unedited, and the
  public player suite is green with **every skip attributed by name**. (test:
  the existing `tests/test_public_player.py` + `tests/test_public_player_pages.py`,
  run unmodified)

## Guardrails

- **G-1: do not touch `src/nonogram/admin/**`.** The guard **reads**
  `admin.css` and `solver.js` from the test tree; it changes neither.
  **CARD-268 is live in `admin.css`, `solver.js`, `solver_state.js`,
  `tokens.css` and `puzzle_solve.html`** — an edit there is a merge conflict
  with a card in flight.
- **G-2: do not edit `2400501b`'s tests.** `test_the_empty_mark_is_a_dot_and_solving_is_revealed`
  runs unmodified. In particular do **not** "simplify" its reveal assertion to
  `getAnimations()` — that races the animation it tests — and do not drop its
  `background-image: none` arm, which is what stops the cross returning as a
  background.
- **G-3: change no rendered pixel.** This card adds a guard and two pointer
  comments. A real disagreement found by the guard is a finding for the owner,
  not a look to silently pick.
- **G-4: do not weaken ADR-0041/R3 or widen `COPIED_FROM_ADMIN`.** Adding
  `admin.css` to the byte-identical copy table is a different and much larger
  decision (the two sheets are not interchangeable — the public page has no
  panel chrome), and it belongs to the architect station, not here.
- **G-5: an exemption gets a shape constraint and a control.** AC-4's frozen
  divergence set is the whole point; a bare path- or name-prefix exemption with
  no control is the CARD-255 defect.
- **G-6: no test deleted, renamed, skipped or merged**, `parametrize` ids
  included (gate: node-id set difference with `-o addopts=''`).
- **G-7: styling from tokens only**, if any CSS is touched at all (it should
  not be, beyond a comment).

## System contract

- ADR-0041/R3 — the board-state module and the design tokens are reused by byte-identical build-time copy, never edited; **everything else is reimplemented natively**, which is why this guard exists (check: `player/assemble.py`'s `COPIED_FROM_ADMIN`, plus its test-tree half)
- ADR-0041/R2 — no public asset carries a solution grid or recoverable solution data; this card adds no asset and reads no solution (check: CARD-282's and CARD-283's guards)
- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check: review-lens)
- ADR-0038/R6 — only the admin player ships the solution to a browser; the reveal changes only the board the player already made (check: review-lens)
- ADR-0038/R8 — a browser test refuses LOUDLY when Chromium is absent, never skips green (check: CARD-160's fixtures, and AC-7's skip attribution)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: AC-5, AC-6 — this card IS a claim, so the mutants are the deliverable)
- ADR-0039/R2 — a guard's set is derived and an unanalysable shape is a FAILURE (check: AC-4)

## Architecture context

- **FR:** FR-045 (the public player)
- **ADR:** ADR-0041/R2-R3, ADR-0038/R1, R6, R8, ADR-0039/R1-R2
- **Components:** COMP-011
- **Trace:** `meta/architecture/trace.yml` — not updated by this card (a guard over two existing implementations; no FR row's test moves)

## Design context

- **Design system:** `player/player.css` is the public player's own sheet; `tokens.css` is the byte-identical copy and the one definition of the colours. Both looks in scope already draw from tokens (`--color-text-secondary`, `--color-success`, `--duration-base`, `--ease`), which is what makes a declaration-level comparison meaningful rather than a pixel one.
- **UI components:** none added. `.player-cell[data-state="empty"]::after` and the solved sweep are the two surfaces compared.
- **Screens:** `/play/<key>` and `/puzzles/<id>/solve` — the card compares them, and renders neither differently.
- **Standards:** the reveal must keep working under `prefers-reduced-motion` exactly as `2400501b` shipped it (banner and frame, no motion).

## Worktree notes

- **[Env]** forge `2026.8.17`. No `meta/.skills.yml`, so no `forge.min_version` to
  compare against and no `models:` block — the implementation agent inherits the
  session model rather than resolving a class.
- **[Dispatched]** 2026-10-30T14:36:59Z, into wave 69 beside CARD-268, whose
  live agent had died leaving its implementation complete (two commits). The
  cap of 2 is honoured: this card and CARD-268 are the two slots.

- **[Declared, not rebuilt — the board's own idiom]** This is a declaration
  card in the sense CARD-262, CARD-276 and CARD-296 established: the state is
  recorded honestly rather than a scope being claimed closed. The owner was
  offered the two obvious options on 2026-10-30 and both were worse:
  - **revert `2400501b` and card it** — throws away green, measured,
    well-evidenced work to re-derive it through the pipeline; the most
    expensive path available, and the only thing it buys is the record;
  - **fold it into CARD-268's gate** — mechanically a no-op (the commit is
    already that card's rebase baseline, so its gate runs against it whatever
    anyone decides) and actively harmful to the record: CARD-268's ACs say
    nothing about public-player dot rendering, so attributing the feature to
    its merge commit would make that card false and mis-attribute the work in
    the retrospective. **Co-location is not ownership.**
- **[Serialization]** Shares `player/player.css` and `player/play.js` with
  CARD-323..327, so the conflict graph serializes it against any of them in one
  wave. Not a `Depends on` edge — it needs none of their output. Its *own*
  footprint is almost entirely the new test file, so it is the cheapest of the
  six to slot in.
- **[It absorbs CARD-325's AC-6]** CARD-325 (the crosshair) carried an AC
  requiring its two implementations to be shown to agree. That idea now has
  **one home**, here, and CARD-325 points at this card instead of carrying a
  third copy of the pattern. When the crosshair lands, its agreement check
  joins this file rather than starting a fourth.
- **[Where the mutant table goes]** AC-5 and AC-6 are evidenced by a table in
  this section, not by a test name: four mutants for the dot (two per sheet) and
  two for the sweep plus two for the wave formula. Both sides of every pair
  matter — **a guard that reads only one sheet passes half of them**, which is
  the exact shape of defect this card is built to catch.
