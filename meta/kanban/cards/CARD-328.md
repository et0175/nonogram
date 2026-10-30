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
**Review score:** cycle 1 **8.0 — did NOT certify** (1 open important, 0 critical) → **fix round 1 complete**, awaiting cycle 2 of 3. IMP-1 closed by constraining the **residue** rather than the key: `DECLARED_DIVERGENCES` became `{key: Divergence(reason, difference, residue)}`, the declared difference is normalised away and what is left is held to equality on both sheets, under a floor that rejects an unreadable residue on **either** side — because two absences are equal, and both sheets dropping the sweep would otherwise pass. **Verified by the orchestrator re-firing its own cycle-1 probe**: the admin sweep flashing *empty* cells went from `23 passed in 0.10s` to **5 failed / 30 passed**, on named arms whose parametrize ids read as the product consequence. 28 mutants at expectation (23 kill, 5 survive), the four cycle-1 survivors all dying, the original eight still dying, a **fifth drift found while fixing** (N5: the hook renamed in the sweep rule only, leaving the reduced-motion block quieting a selector that no longer exists). Gate **115 passed / 0 skipped**; node ids **23 → 35**, removals empty. MIN-1 closed, NIT-2 closed, MIN-2 improved with the trade it declined recorded, NIT-1 declined as merge-time bookkeeping.
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

### Implementation round 1 (2026-10-30, worktree `PythonProject4-card-328`)

**What shipped:** `tests/test_public_player_agreement.py` (new, 23 tests in the
four classes the ACs name), plus one pointer comment in `player/player.css`
and one in `player/play.js`. **Nothing under `src/` is changed** — see the SHA
check at the end of this round.

#### The guard's design

The compared surface is **derived, not written down**. `compared_surface()`
takes the two sheets' text and the two scripts' extracted wave expressions and
returns `{fact: (admin value, public value)}` — **12 facts**, counted from the
dict it returns, not from this sentence:

`dot.declarations`, `keyframes.player-solved-in`,
`keyframes.player-solved-flash`, `sweep.selector`,
`sweep.animation.{name,duration,easing,delay,step}`,
`reduced-motion.block-count`, `reduced-motion.coverage`, `wave.expression`.

`disagreements()` is **total over those keys**, so a fact that starts to differ
can only be *declared* or *reported* — never overlooked. Three things make the
parse honest rather than convenient:

- **Parsed declarations, never rule text** (AC-1). One sheet writes the dot on
  a single line, the other over nine, so a text comparison would compare code
  style. `test_the_comparison_is_over_declarations_and_not_over_rule_text`
  asserts the texts *differ* and the declarations *agree*, which is what stops
  a later "simplification" into `admin_rule == public_rule`.
- **The sweep rule is found by what it does**, not by its selector: the one
  rule whose `animation` value names `player-solved-flash`, with reduced-motion
  blocks excluded first. Looking it up by the admin's selector would simply not
  find the public one, and "not found" has to be a failure here.
- **Anti-vacuity arms throughout.** Declaration-set equality is vacuously true
  on two empty parses, so each side is *also* held to an independently written
  expectation: `DOT_PROPERTIES` (the seven names), `WAVE_EXPRESSION`
  (`row + col`), a non-empty keyframes body, `rule_count(...) == 1` per sheet,
  `len(surface) >= 12`. A regex that stopped matching tomorrow reds instead of
  reporting perfect agreement about nothing.

No CSS parser is in the dependency baseline, so this is `re` plus two brace
walks, following `tests/test_admin_design_tokens.py`'s idiom for reading these
sheets rather than inventing a second one. No `hypothesis`. The animation
shorthand is split by an independent paren-depth tokeniser rather than matched
against the formula we expect, because the expected formula is the thing under
comparison.

#### The shared / declared split (AC-4), re-derived 2026-10-30

Measured: **9 of the 12 facts agree, 3 disagree, and the 3 that disagree are
exactly `DECLARED_DIVERGENCES`.**

| Declared divergence | admin | public | why it is not drift |
|---|---|---|---|
| `sweep.selector` | `.player-board.is-solved .player-cell[data-state="filled"]` | `body[data-solved="true"] .player-cell[data-state="filled"]` | different DOM hooks: `play.js` already writes the attribute on every render, so the reveal fires on the transition into solved and does not re-trigger while it stays solved — the same once-only reveal the class gives the panel. The look agrees; the hook is each page's own. |
| `sweep.animation.delay` | `calc(var(--player-wave) * 12ms)` | `calc(var(--player-wave, 0) * 12ms)` | a fallback, not a different delay. The step is compared **separately** as `sweep.animation.step` and must agree, so this exemption cannot hide a changed step (M5/M6 prove it). |
| `reduced-motion.coverage` | 5 selectors (`.player-toolbar`, `.player-toolbar *`, `.player-stage`, `.player-stage *`, the sweep) with `animation: none !important; transition: none !important` | 2 selectors (the banner, the sweep) with `animation: none` | the panel has toolbar/stage chrome that animates and the public page has none of it. Both switch the same reveal off; the surface each has to switch off differs. The block **count** is compared separately as `reduced-motion.block-count` and must agree. |

> **[Superseded by fix round 1]** The three rows above describe the table as it
> shipped in round 1, where each exemption was a key and a reason. Review cycle
> 1's IMP-1 showed that shape absorbs real drift — four mutants fired inside
> these three facts survived at `23 passed` — so each exemption now also names
> the **difference** it exempts and leaves a **residue** that must agree. The
> current shape, the residues and the controls are in *Fix round 1* below; the
> "why it is not drift" column here is still accurate as far as it goes, but it
> is no longer the whole of what holds these three exemptions.

**G-5 / the CARD-255 shape.** The declaration is not a bare list. It carries
three constraints and two controls, each its own node id:
- `test_every_declared_divergence_is_a_fact_the_guard_measures` — a declared
  key outside the compared surface exempts nothing and hides everything;
- `test_every_declared_divergence_carries_a_reason` — a reason floor
  (120 chars), because the key says *what* differs and only the sentence says
  whether anyone *decided* it;
- `test_the_disagreements_are_exactly_the_declared_ones` — set **equality**, so
  an undeclared disagreement reds *and* a declared key that no longer diverges
  reds as a stale exemption;
- `test_a_fourth_divergence_in_the_compared_surface_is_reported` — the positive
  control for "a fourth divergence reds": the real public sheet text with
  `width: 28%` → `31%` planted as a string substitution, asserted to surface as
  `dot.declarations` and to be **outside** the exemption table;
- `test_a_declared_divergence_that_stops_diverging_is_reported` — the other
  direction, the public selector rewritten to the panel's own.

#### [FINDING — this card's own brief, corrected] the third divergence was a mention count, not a block count

The card body and the dispatch brief both state *"reduced-motion blocks: admin
has 4, the public sheet has 1."* **Re-derived on 2026-10-30: both sheets have
exactly ONE `@media (prefers-reduced-motion: reduce)` block.**

`grep -c 'prefers-reduced-motion' admin.css` = 4 and `player.css` = 1 — but in
`admin.css` only line 1061 opens a block; lines 872, 1059 and 1259 are *prose
comments* that mention the feature. The figure came from a string count and
reads as a block count. The board's own rule applies to the brief as much as to
the work: **a figure summarising rows is counted from the rows.**

So the guard declares the honest divergence — `reduced-motion.coverage`, the
block's selector set and declarations — and *additionally* compares
`reduced-motion.block-count`, which **agrees at 1 = 1** and is therefore
deliberately **not** in `DECLARED_DIVERGENCES`. Declaring a divergence that
isn't one would have been the stale exemption the same AC forbids. The card
asked for three declared divergences with a reason each and it has three; the
third one's *shape* is the corrected one.

#### The mutant table (AC-5, AC-6) — 8 mutants, 8 KILLED, 0 survived

Harness: `scratchpad/card328/mutate_card328.py` (not at the shared scratchpad
root — CARD-284's root-level harness was re-executed after its own run and its
first kill reading was untrustworthy). Per mutant: assert the file is at HEAD
by SHA-256 against `git show HEAD:<path>` → sweep `*.pyc`/`__pycache__` →
substitute (asserting it applied exactly once) → run with
`PYTHONDONTWRITEBYTECODE=1` and `-o addopts=''  -v` → restore from the
pre-mutant bytes → re-assert the SHA → sweep again. A crashed instrument is
recorded `CRASHED`, never as a survivor; an empty verdict map raises. Raw
verdicts: `scratchpad/card328/mutants.json`.

The admin dot mutants are applied **to the line carrying
`.player-cell[data-state="empty"]::after`**, because `.player-swatch[data-state="empty"]::after`
(admin.css:781) shares `width: 28%` and `var(--color-text-secondary)` — a
whole-file substitution would have mutated two rules and the kill would not
have been attributable.

| # | File | Change | AC | Status | Arms red (node id, class prefix `TestPlayerLooksAgree_`) |
|---|---|---|---|---|---|
| M1 | `src/nonogram/admin/static/admin.css` | dot `width: 28%` → `31%` | AC-5 | **KILLED** | `TheDot…::test_the_two_declaration_sets_are_equal`, `TheDot…::test_the_comparison_is_over_declarations_and_not_over_rule_text`, `ADivergence…::test_the_disagreements_are_exactly_the_declared_ones`, `ADivergence…::test_a_fourth_divergence_in_the_compared_surface_is_reported` |
| M2 | `player/player.css` | dot `width: 28%` → `31%` | AC-5 | **KILLED** | the same four |
| M3 | `src/nonogram/admin/static/admin.css` | dot `background: var(--color-text-secondary)` → `var(--color-text)` | AC-5 | **KILLED** | `TheDot…::test_the_two_declaration_sets_are_equal`, `TheDot…::test_the_comparison_is_over_declarations_and_not_over_rule_text`, `ADivergence…::test_the_disagreements_are_exactly_the_declared_ones` |
| M4 | `player/player.css` | dot `background: var(--color-text-secondary)` → `var(--color-text)` | AC-5 | **KILLED** | the same three |
| M5 | `src/nonogram/admin/static/admin.css` | sweep step `* 12ms` → `* 13ms` | AC-6 | **KILLED** | `TheSweep…::test_the_per_cell_step_agrees`, `ADivergence…::test_the_disagreements_are_exactly_the_declared_ones`, `ADivergence…::test_a_fourth_divergence_in_the_compared_surface_is_reported` |
| M6 | `player/player.css` | sweep step `* 12ms` → `* 13ms` | AC-6 | **KILLED** | the same three |
| M7 | `src/nonogram/admin/static/solver.js` | `setProperty("--player-wave", row + col)` → `row` | AC-6 | **KILLED** | `BothPlayers…::test_both_players_set_the_wave_to_the_same_expression`, `BothPlayers…::test_the_wave_is_the_cells_row_plus_its_column`, `ADivergence…::test_the_disagreements_are_exactly_the_declared_ones`, `ADivergence…::test_a_fourth_divergence_in_the_compared_surface_is_reported` |
| M8 | `player/play.js` | `setProperty("--player-wave", String(row + col))` → `String(row)` | AC-6 | **KILLED** | the same four |

Counted from the rows: **8 mutants, 8 killed, 0 survived, 0 crashed/not-reached.**
Four of them are admin-side (M1, M3, M5, M7) — **a guard that read
`player.css`/`play.js` on both sides of every comparison would have survived
all four**, which is why both sides of every pair are in the table rather than
one of each. `test_the_guard_reads_both_trees_and_not_one_of_them_twice`
asserts that property about the guard itself.

Note M3/M4 red three arms rather than four: with the dot already disagreeing on
colour, the planted-fourth-divergence control's precision assertion
(`disagreements - declared == {"dot.declarations"}`) still holds. That is
correct behaviour of the control, not a missed arm.

#### AC-by-AC evidence

- **AC-1** — `TestPlayerLooksAgree_TheDotIsDeclarationForDeclarationTheSame`,
  5 node ids: `test_the_rule_is_declared_once_in_each_sheet`,
  `test_the_admin_sheet_declares_the_seven_properties`,
  `test_the_public_sheet_declares_the_seven_properties`,
  `test_the_two_declaration_sets_are_equal`,
  `test_the_comparison_is_over_declarations_and_not_over_rule_text`. Split one
  arm per claim deliberately — a test short-circuits at its first failing
  assert, so a bundled method's single `FAILED` line would say nothing about
  which arm a mutant reached. Reds under M1–M4.
- **AC-2** — `TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep`,
  8 node ids (banner keyframes, flash keyframes, non-empty bodies, rule found
  once per sheet, name, duration, easing, step). Reds under M5/M6 at
  `test_the_per_cell_step_agrees`.
- **AC-3** — `TestPlayerLooksAgree_BothPlayersSetTheSameWave`, 3 node ids.
  `test_each_player_sets_the_wave_exactly_once` is the shape constraint: a
  second setter is a second decision, and the CARD-255 lesson is that the
  thing nobody counted is where the extra executable copy lives. Reds under
  M7/M8.
- **AC-4** — `TestPlayerLooksAgree_ADivergenceMustBeDeclared`, 7 node ids; see
  the split table and the G-5 list above. Its two planted controls make the
  claim falsifiable without touching a file, which matters because the live
  tree agrees and a set equality over an agreeing tree proves nothing on its
  own.
- **AC-5 / AC-6** — the mutant table above.
- **AC-7** — see the next block.

#### AC-7: nothing rendered changes, and the skip attribution

`tests/test_public_player.py` + `tests/test_public_player_pages.py` +
`tests/test_admin_design_tokens.py` + the new file, run with
`-o addopts='' -rs -p no:randomly`:

**103 passed, 0 skipped, 0 failed, exit 0** (15.91s). Split: 34 + 33 + 13 + 23.
The two shipped files' **67** reproduces the card's declared figure exactly.

**Skip attribution: the set of skips is EMPTY, and that is a measurement, not
an absence of one.** `-rs` reports a reason line per skip and printed no skip
section; the count line carries no `skipped` term. So there is no skip to
attribute by name — which is what ADR-0038/R8 wants here: every skip in this
suite would be `DATABASE_URL`-gated, and the browser fixtures refuse loudly
when Chromium is absent rather than skipping green. Chromium *is* present in
this worktree — the `browser`-marked tests ran and passed, including
`2400501b`'s own `test_the_empty_mark_is_a_dot_and_solving_is_revealed`
(re-run alone by node id: 1 passed).

**G-2 is intact and re-derived, not assumed.** `git diff --name-only HEAD --
tests/` is **empty**: no existing test file is touched. The two protected calls
still read as shipped — `getAnimations` occurs exactly once in
`tests/test_public_player.py` and that occurrence is the docstring explaining
why the reveal is *not* asserted through it, and the `background-image`/
`cellBackgroundImage` arm is still there (lines 2085, 2097).

Also run, because a new file in `tests/` can red a tree-scanning guard by its
own text: `tests/test_collected_names.py`, `tests/test_guard_integrity.py`,
`tests/test_suite_profile.py`, `tests/test_impact_set.py` — **664 passed, 0
skipped**. The new file matches neither `RENDER_API_PATTERN` (so
`RENDER_HEAVY_SNAPSHOT` does not move) nor `scripts/impact_set.py`'s
`SCAN_IDIOMS`, and it declares no `PropertyTest_*` class. It uses no `skipif`
and no module-scope silencer, so it registers no new host-state silence. **The
full suite was not run — the merge gate is the only full run.**

#### G-6: no test deleted, renamed, skipped or merged

`git diff --name-only HEAD -- tests/` is empty, so no existing node id can have
moved; the node-id set difference is therefore **additions only**. Enumerated
by AST and cross-checked against `--collect-only -q -o addopts=''`: **23
declared, 23 collected, both differences empty** — no silently-uncollected
class (the CARD-294 defect shape), and no helper named `test*`.

#### Guardrails

- **G-1 `src/nonogram/admin/**` untouched.** `admin.css` and `solver.js` were
  mutated and restored during the mutation run; both are byte-identical to
  HEAD afterwards:
  `03a7de8d1f5f1066f4c9e3400d65393144cafffb5d2609e35734b5cc527a381d  admin.css`
  and `7a3b4aeb59fbc91ae146f2d523716b77c13c00be9b8f9687e1a673ed37d2fbe5  solver.js`,
  equal to `git show HEAD:<path>`. `git status` shows only `player/play.js`,
  `player/player.css`, `tests/test_public_player_agreement.py`, this card and
  `scratchpad/`.
- **G-3 no rendered pixel changed.** The two edits to `player/` are comments.
  The guard found **no real disagreement** outside the three declared ones, so
  there is nothing to raise with the owner on that front.
- **G-4** — `COPIED_FROM_ADMIN` is not touched and ADR-0041/R3 is not
  weakened. The guard reads `admin.css`/`solver.js`; it copies neither.
- **G-7** — no CSS value added, only a comment.

#### [FINDING — belongs to CARD-268, not to this card] its edit misses this card's surface, re-derived

Re-derived in the sibling worktree at `9c88b723` rather than taken on trust:
`git diff ef04286a` there is `admin.css +129`, `solver.js +196`, and **not one
added or removed line touches this card's compared surface.** The dot rule
(`admin.css:648`), both `@keyframes player-solved-*` (1055, 1056), the sweep
rule (1058) and the reduced-motion block (1061-1062) are byte-identical in both
trees, and `solver.js`'s `--player-wave` setter is unchanged (it has only moved
730 → 778). Its only hit anywhere near the surface is `.player-probe-note`,
which reaches for `--color-text-secondary` as a text colour and is not a
compared fact. **No merge conflict is expected, and the guard is line-number-free
by construction** — every fact is found by selector, keyframes name or what the
rule does, never by a line number, precisely so a +129 above it cannot move it.

### Fix round 1 (2026-10-30, review cycle 1 — score 8, IMP-1 open)

Cycle 1 scored 8 and did **not** certify: the threshold was met but one
important finding was open. Five findings, all closed or declined with a
reason. **Nothing under `src/` changed** (SHA check at the end), `player/` is
untouched this round, and the only tracked file edited is
`tests/test_public_player_agreement.py`.

#### IMP-1 (important, gating) — an exemption is now over a stated DIFFERENCE, not over a fact

The table exempted three facts **by key**, and nothing constrained what could
differ *inside* an exempted key. The reviewer fired four mutants into the
exempted content and all four survived at `23 passed`, each proved to have
been *read* by the guard. **Closed by constraining the residue, not the key.**

`DECLARED_DIVERGENCES` is now `{key: Divergence(reason, difference, residue)}`:

- `reason` — the sentence, floor unchanged at 120 chars;
- `difference` — what is normalised away, in a phrase;
- `residue` — `(this side's value, this side's own sweep selector) -> what is
  left`, held to **equality across the two sheets** by
  `residue_disagreements()`.

Per exemption, re-derived from the files (not quoted — printed from
`residues()` on the live tree):

| Declared divergence | what the exemption exempts | residue, both sides |
|---|---|---|
| `sweep.selector` | the leading page-state hook (and **only one hook's worth**: a selector that is not `<hook> <target>` is unreadable) | `.player-cell[data-state="filled"]` |
| `sweep.animation.delay` | the `, 0` inside `var(--player-wave, 0)`; a delay that no longer reads `--player-wave` is unreadable | `calc(var(--player-wave) * 12ms)` |
| `reduced-motion.coverage` | the selector **lists** (5 vs 2) and `!important`; the block is searched for that sheet's own sweep selector **exactly, hook included** | `.player-cell[data-state="filled"] { animation: none }` |

Three things make that a shape rather than three special cases:

- **the residue arms are total over the table** —
  `test_every_declared_divergence_agrees_on_the_residue_it_leaves` and
  `test_every_declared_divergence_names_the_difference_it_normalises_away`
  iterate `DECLARED_DIVERGENCES`, so a fourth entry is held the moment it is
  added;
- **a floor under the equality** —
  `test_no_declared_divergence_has_an_unreadable_residue`, because two
  *absences* are equal: if **both** sheets stopped quieting the sweep the
  residues would agree at `!! …` and the equality alone would pass. This is
  the same vacuity `DOT_PROPERTIES` and `WAVE_EXPRESSION` guard for the facts
  that agree outright;
- **`RESIDUE_CONTROLS` held to the table by set equality** —
  `test_every_declared_divergence_carries_a_control_of_its_own`. Six plants
  (one per exemption **per sheet**, because a residue computed from one tree
  twice would pass half of them), each planting real drift inside one
  exemption on the real sheet text and asserting, **in order**, that (1) the
  key-level table still absorbs it — which is *why* the matching cycle-1 probe
  survived — and (2) the residue reports it anyway.

#### MIN-1 — the sub-assertion that could not fail

`test_the_comparison_is_over_declarations_and_not_over_rule_text` squeezed the
admin operand and left the public one raw, so the two could essentially never
be equal. **Both operands are now raw** (like against like) and the docstring
claims only what the arm holds: that the two texts differ *today*, with a
message telling the next reader to restate the premise rather than leave the
arm asserting it. The claim the arm could not carry — "the comparison is over
declarations, not text" — moved to a new arm that **can** fail on its own,
`test_reformatting_a_dot_rule_moves_no_declaration`: collapsing the public
rule onto one line moves no pixel and must move no compared fact.
Controls: **P1** (the reviewer's own experiment — the public dot collapsed
byte-identical to the admin's) now **KILLS**; **P2** (the claim's edge — a
whitespace-only reindent that leaves the texts different) **SURVIVES**, so the
arm is not formatting police.

#### MIN-2 — parse-failure attribution, improved, with what was NOT traded stated

`compared_surface()` now reads every fact through `_measured(fact, read)`,
which re-raises a collapsed parse with the **fact's name** (`sweep.selector
(admin.css) did not parse: …`) instead of the bare helper message, and a new
fixture-free arm `test_the_compared_surface_parses_fact_by_fact` turns any
collapse into **one named FAILED cell** carrying that name.

**What was deliberately not done:** the fixture-scoped ERRORs remain (V1/V3/V4
still show 5 errors each). Removing them means handing the arms a surface with
sentinels where a fact should be, which would make "not found" something other
than a failure — a weaker control, which the brief says to decline and say so.
So: attribution improved, not completed, and the reason is recorded.

#### NIT-2 — the reduced-motion opener, tightened

`REDUCED_MOTION = "@media (prefers-reduced-motion: reduce"`, used by
`reduced_motion_blocks()`, `sweep_rule()` and the coverage plant. Controls:
**Q1** (the reduce query renamed to `: no-preference`) now **KILLS** on the
block count; **Q2** (the claim's edge — an unrelated `: no-preference` block
added to the public sheet, which the old loose opener *would* have counted)
**SURVIVES**.

#### NIT-1 — declined, with a reason

Bookkeeping, and not this round's. The branch is 4 commits behind `main` and
the only contested path is this card file; the fix brief forbids a rebase or
merge and the orchestrator resolves it at merge time.

#### The mutant table — 28 mutants, 28 at expectation, 0 crashed

Harness: `scratchpad/fix328/mutate.py` (scoped to `scratchpad/fix328/`, never
the shared scratchpad root). Per mutant: snapshot the pre-mutant bytes and
their SHA-256 → for every file outside `tests/`, assert that SHA equals
`git show HEAD:<path>` → sweep `*.pyc`/`__pycache__` → substitute, asserting
each edit applied exactly the expected number of times → run with
`PYTHONDONTWRITEBYTECODE=1 -o addopts='' -q -rfE -p no:randomly` → restore
from the snapshot → re-assert the SHA → sweep again. A crashed instrument is
recorded `CRASHED`, never as a survivor; an empty verdict map raises. Raw
verdicts: `scratchpad/fix328/mutants.json`. **All verdicts and failing-cell
sets reproduced identically across two independent runs with cache sweeps
between them.**

Class prefix below is `TestPlayerLooksAgree_`; `ADiv…` is
`ADivergenceMustBeDeclared`, `TheDot…` is
`TheDotIsDeclarationForDeclarationTheSame`, `TheSweep…` is
`TheSweepSharesItsKeyframesAndItsStep`, `BothPlayers…` is
`BothPlayersSetTheSameWave`.

**The four cycle-1 survivors — all four now DIE.**

| # | File | Change | Cycle 1 | Now | Count line | Cells that red |
|---|---|---|---|---|---|---|
| N1 | `admin.css` | sweep selector `[data-state="filled"]` → `"empty"` (the panel flashes the wrong cells) | **SURVIVED** `23 passed` | **KILLED** | `5 failed, 30 passed` | `ADiv…::test_every_declared_divergence_agrees_on_the_residue_it_leaves`, `ADiv…::test_no_declared_divergence_has_an_unreadable_residue`, `ADiv…::test_real_drift…[sweep.selector::the panel flashes the empty cells]`, `…[sweep.selector::the public page flashes the empty cells]`, `…[reduced-motion.coverage::the panel stops quieting its sweep]` |
| N2 | `admin.css` | delay → `calc(3 * var(--player-wave) * 12ms)` (3× slower panel sweep) | **SURVIVED** `23 passed` | **KILLED** | `2 failed, 33 passed` | `ADiv…::test_every_declared_divergence_agrees_on_the_residue_it_leaves`, `ADiv…::test_real_drift…[sweep.animation.delay::the public sweep is three times slower]` |
| N3 | `admin.css` | the reduced-motion block no longer names the sweep | **SURVIVED** `23 passed` | **KILLED** | `3 failed, 32 passed` | `…agrees_on_the_residue_it_leaves`, `…no_declared_divergence_has_an_unreadable_residue`, `…test_real_drift…[reduced-motion.coverage::the panel stops quieting its sweep]` |
| N4 | `player.css` | the reduced-motion block no longer names the sweep | **SURVIVED** `23 passed` | **KILLED** | `3 failed, 32 passed` | `…agrees_on_the_residue_it_leaves`, `…has_an_unreadable_residue`, `…test_real_drift…[reduced-motion.coverage::the public page stops quieting its sweep]` |

**Why N2 reds the *public* delay control and not the panel one.** With the
panel's delay already 3× under the mutant, the public-side plant makes the
public delay 3× too, the two residues become equal, and the control's second
assert — "the residue reports it" — fails because the plant accidentally
restored agreement. The panel-side plant stacks to 9× and stays green. Both
readings are correct for a drifted tree; the kill is attributable either way.

**Found while fixing — a fifth real drift inside the same exemption.**

| # | File | Change | Status | Count line | Cells that red |
|---|---|---|---|---|---|
| N5 | `admin.css` | the sweep's **hook** renamed `.is-solved` → `.is-done` in the sweep rule **only**, leaving the reduced-motion block quieting a selector that no longer exists | **KILLED** | `3 failed, 32 passed` | `…agrees_on_the_residue_it_leaves`, `…has_an_unreadable_residue`, `…test_real_drift…[reduced-motion.coverage::the panel stops quieting its sweep]` |

This is why the coverage residue matches the sheet's own sweep selector
**exactly, hook included** rather than by its tail: a block that quiets
`.player-board.is-solved .player-cell[…]` while the sweep hangs on another
hook quiets nothing. E1 below is the same rename done **consistently** and it
SURVIVES, which is the pair that separates the exempted difference from the
drift.

**The card's own eight — all eight still DIE.**

| # | File | Change | AC | Status | Count line | Cells that red (beyond the six residue controls, see the note) |
|---|---|---|---|---|---|---|
| M1 | `admin.css` | dot `width: 28%` → `31%` (line-scoped to the `.player-cell` rule) | AC-5 | **KILLED** | `10 failed, 25 passed` | `TheDot…::test_the_two_declaration_sets_are_equal`, `TheDot…::test_the_comparison_is_over_declarations_and_not_over_rule_text`, `ADiv…::test_the_disagreements_are_exactly_the_declared_ones`, `ADiv…::test_a_fourth_divergence_in_the_compared_surface_is_reported` |
| M2 | `player.css` | dot `width: 28%` → `31%` | AC-5 | **KILLED** | `10 failed, 25 passed` | the same four |
| M3 | `admin.css` | dot `background` → `var(--color-text)` | AC-5 | **KILLED** | `9 failed, 26 passed` | the same, less `…a_fourth_divergence…` (see the cycle-1 note: that control's precision assertion still holds) |
| M4 | `player.css` | dot `background` → `var(--color-text)` | AC-5 | **KILLED** | `9 failed, 26 passed` | the same three |
| M5 | `admin.css` | sweep step `* 12ms` → `* 13ms` | AC-6 | **KILLED** | `10 failed, 25 passed` | `TheSweep…::test_the_per_cell_step_agrees`, `ADiv…::test_the_disagreements_are_exactly_the_declared_ones`, `ADiv…::test_a_fourth_divergence…`, `ADiv…::test_every_declared_divergence_agrees_on_the_residue_it_leaves` |
| M6 | `player.css` | sweep step `* 12ms` → `* 13ms` | AC-6 | **KILLED** | `10 failed, 25 passed` | the same four |
| M7 | `solver.js` | `--player-wave` `row + col` → `row` | AC-6 | **KILLED** | `10 failed, 25 passed` | `BothPlayers…::test_both_players_set_the_wave_to_the_same_expression`, `BothPlayers…::test_the_wave_is_the_cells_row_plus_its_column`, `ADiv…::test_the_disagreements_are_exactly_the_declared_ones`, `ADiv…::test_a_fourth_divergence…` |
| M8 | `play.js` | `String(row + col)` → `String(row)` | AC-6 | **KILLED** | `10 failed, 25 passed` | the same four |

**Note on M1–M8's larger failure counts.** They were 3–4 cells in cycle 1 and
are 9–10 now. The extra cells are the six new `test_real_drift…` controls,
redding on their **first** assert — the one that says the key-level table must
still absorb the plant. Under M1–M8 the live tree *itself* disagrees outside
the exemption table, so that premise is false and the controls say so; the
message names the surplus key and points at
`test_the_disagreements_are_exactly_the_declared_ones`. That is a premise
assert doing its job, not a mis-attributed kill — and it is why the message
was rewritten this round to name both directions of the set difference.

**The claims' edges — what the exemptions and the new arms still allow.**

| # | File | Change | Expected | Status | Count line |
|---|---|---|---|---|---|
| E1 | `admin.css` | the sweep's hook renamed `.is-solved` → `.is-done` **consistently** in the sweep rule *and* the reduced-motion block | SURVIVES (the hook is the declared difference) | **SURVIVED** | `35 passed` |
| E2 | `player.css` | the delay's fallback `var(--player-wave, 0)` → `, 1` | SURVIVES (the fallback is the declared difference) | **SURVIVED** | `35 passed` |
| E3 | `admin.css` | the reduced-motion block drops a chrome selector (`.player-stage *`) | SURVIVES (the lists are the declared difference) | **SURVIVED** | `35 passed` |
| P1 | `player.css` | the dot rule collapsed onto one line, byte-identical to the admin's — a pure reformat, zero pixels moved | KILLS (MIN-1: it SURVIVED in cycle 1) | **KILLED** | `1 failed, 34 passed` — `TheDot…::test_the_comparison_is_over_declarations_and_not_over_rule_text` |
| P2 | `player.css` | the dot rule reindented but still not the admin's text | SURVIVES (the arm is not formatting police) | **SURVIVED** | `35 passed` |
| Q1 | `admin.css` | the reduce query renamed `: no-preference` | KILLS | **KILLED** | `10 failed, 25 passed` |
| Q2 | `player.css` | an unrelated `: no-preference` block added (the old loose opener would have counted it) | SURVIVES | **SURVIVED** | `35 passed` |

**Anti-vacuity, re-fired — the guard is still not hollow.**

| # | Change | Status | Count line | First cell |
|---|---|---|---|---|
| V1 | `_RULE` never matches | **KILLED** | `20 failed, 10 passed, 5 errors` | `TheDot…::test_the_rule_is_declared_once_in_each_sheet` |
| V2 | `_WAVE_SETTER` never matches | **KILLED** | `2 failed, 33 passed` | `BothPlayers…::test_each_player_sets_the_wave_exactly_once` |
| V3 | `_blocks_at_depth_one` returns nothing | **KILLED** | `12 failed, 18 passed, 5 errors` | `TheSweep…::test_the_banner_keyframes_agree` |
| V4 | `declarations()` always `{}` | **KILLED** | `17 failed, 13 passed, 5 errors` | `TheDot…::test_the_admin_sheet_declares_the_seven_properties` |
| V5 | `compared_surface()` returns `{}` | **KILLED** | `13 failed, 22 passed` | `ADiv…::test_the_compared_surface_is_not_empty_and_names_both_looks` |
| V6 | the step regex never matches | **KILLED** | `1 failed, 34 passed` | `TheSweep…::test_the_per_cell_step_agrees` |

**The shape itself — a FOURTH exemption cannot slip through.**

| # | Change to the guard | Status | Count line | The cell that makes the point |
|---|---|---|---|---|
| S1 | one exemption declared as a bare reason string again, as all three were in cycle 1 | **KILLED** | `10 failed, 25 passed` | `ADiv…::test_every_declared_divergence_names_the_difference_it_normalises_away` (with `…carries_a_reason` and both residue arms) |
| S2 | a fourth exemption added **with** a difference and a residue but **no control** | **KILLED** | `9 failed, 26 passed` | `ADiv…::test_every_declared_divergence_carries_a_control_of_its_own` |

Counted from the rows: **28 mutants — 23 expected to kill and 23 KILLED, 5
expected to survive and 5 SURVIVED, 0 crashed, 0 off expectation.** Admin-side
mutants: 15 of the 28 (N1, N2, N3, N5, M1, M3, M5, M7, E1, E3, Q1 and, on the
admin half of their plants, the three residue controls) — a guard reading
`player.css`/`play.js` on both sides of every comparison would survive them.

#### Does a fourth exemption inherit the constraint?

**Yes, structurally, and it was measured rather than asserted (S1, S2).** A
fourth entry:

- **cannot be declared without a difference and a residue** — the table's
  value type is `Divergence`, and
  `test_every_declared_divergence_names_the_difference_it_normalises_away`
  reds on a bare string (S1);
- **is held to residue equality and to the unreadable-residue floor for free**
  — both arms iterate the table;
- **cannot ship without its own control** —
  `test_every_declared_divergence_carries_a_control_of_its_own` compares
  `RESIDUE_CONTROLS` to `DECLARED_DIVERGENCES` by set **equality**, so a
  fourth exemption reds until it brings a plant (S2), and a control left
  behind by a removed exemption reds too.

What it does **not** inherit is the *content* of its residue: the function that
normalises its particular difference away has to be written, and that is the
irreducible part — a residue nobody wrote is a difference nobody stated. This
matters for CARD-325, whose crosshair agreement check is scheduled to join
this file: it will meet the constrained pattern rather than the licence.

#### The gate

`tests/test_public_player.py` + `tests/test_public_player_pages.py` +
`tests/test_admin_design_tokens.py` + this file, with
`-o addopts='' -rs -p no:randomly`: **115 passed, 0 skipped, 0 failed, exit
0** (13.57s). Split 34 + 33 + 13 + **35**; the two shipped files' **67** still
reproduces the card's declared figure.

**Skip attribution: the set of skips is EMPTY, and that is a measurement.**
`-rs` printed no skip section and the count line carries no `skipped` term, so
there is no skip to attribute by name — which is what ADR-0038/R8 wants here.
Chromium is present in this worktree and the `browser`-marked tests ran.

Also re-run, because a test file can red a tree-scanner by its own text:
`tests/test_collected_names.py`, `tests/test_guard_integrity.py`,
`tests/test_suite_profile.py`, `tests/test_impact_set.py` — **664 passed, 0
skipped**. **The full suite was not run:** CARD-268 is live in a parallel
worktree in its own fix round, the flock on `meta/kanban/.full-suite.lock` was
not taken, and the merge gate is the only full run.

#### G-6: no test deleted, renamed, skipped or merged

Node-id set difference under `-o addopts=''`, before vs after:
**23 → 35, removals EMPTY, 12 additions** (`scratchpad/fix328/nodeids.{before,after}.txt`).
Cross-checked against the AST: 30 declared methods, one of them carrying 6
`parametrize` ids → 35 collected, and 35 collected. Class split, counted from
the node ids: `TheDot…` 6, `TheSweep…` 8, `BothPlayers…` 3, `ADiv…` 18 — 35.
No arm was deleted; `test_the_comparison_is_over_declarations_and_not_over_rule_text`
was **re-expressed**, which G-6 allows, and P1/P2 are its control pair.

#### Per-assertion measurement, for the multi-arm controls

The new `test_real_drift_inside_a_declared_divergence_is_reported` carries two
asserts in a fixed order, and a test short-circuits at the first, so each was
measured separately:

- **assert 1** (the key-level table still absorbs the plant) is the one that
  reds under M1–M8 and Q1 — i.e. under pre-existing drift — and it is green
  under N1–N5, which is exactly the statement "the cycle-1 probe survived";
- **assert 2** (the residue reports it) is the one that reds under N1–N5 and
  under S1/S2, and it is **reached** there because assert 1 passed. Verified
  from the failing-cell sets, not inferred: N1 reds
  `[sweep.selector::…]` and `[reduced-motion.coverage::the panel…]` while the
  other four cases stay green, which is only possible if assert 1 passed in
  all six.

`test_every_declared_divergence_names_the_difference_it_normalises_away` has
three asserts inside one loop (type, difference, residue); S1 reds it on the
`isinstance` arm. `test_every_declared_divergence_carries_a_control_of_its_own`
has two (set equality, no empty tuple); S2 reds it on the set equality.
`test_no_declared_divergence_has_an_unreadable_residue` is a single
dict-comprehension assert and names every offending `(key, sheet)` pair in its
message rather than stopping at the first.

#### Guardrails

- **G-1 nothing under `src/`.** `admin.css` and `solver.js` were mutated and
  restored under the harness's SHA discipline; after the final run both are
  byte-identical to HEAD —
  `03a7de8d1f5f1066f4c9e3400d65393144cafffb5d2609e35734b5cc527a381d  admin.css`,
  `7a3b4aeb59fbc91ae146f2d523716b77c13c00be9b8f9687e1a673ed37d2fbe5  solver.js`
  — equal to `git show HEAD:<path>`.
- **G-2 `2400501b`'s tests unmodified.** `git diff --name-only HEAD -- tests/`
  is exactly `tests/test_public_player_agreement.py`; no other test file is
  touched, so `getAnimations` is still only the docstring and the
  `background-image: none` arm is intact.
- **G-3 no rendered pixel changes.** `player/player.css` and `player/play.js`
  are byte-identical to HEAD (`db675981…5ebc`, `5c21e097…a526`): this round's
  diff is `tests/` only, so the `player/` diff is still comments only.
- **G-4** `COPIED_FROM_ADMIN` untouched, ADR-0041/R3 not weakened.
- **G-5** this is the finding closed above, now holding **per exemption** and
  not just at the table.
- **G-6** additions only, measured above.
- **G-7** no CSS value added — no CSS file is in this round's diff at all.
- **Not rebased, not merged.** The branch is still 4 commits behind `main`.
