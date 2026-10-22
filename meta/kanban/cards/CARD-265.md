# CARD-265: The `_ADAPTER_COUNT` boundary, four one-line bounds, and the one sentence `tests/README.md` is missing

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/265-the-adapter-count-boundary
**Worktree:** —
**Source:** CARD-261's review cycle 3 (2026-10-22), which **passed** that card at 8.5 with seven bounds and recommended this as the follow-up. Every item below was measured there, not inferred.
**Idea:** —
**Wave:** —
**Depends on:** CARD-261 (it edits the controls that card shipped)
**Touches:** tests/test_cli.py, tests/README.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why — a card passed with bounds, and four of them are one line each

CARD-261 merged at 8.5 with seven accepted bounds. Five are cheap and were left only because the owner's
escalation route was `continue`, not `expand`, on a card already `LARGE_BUT_IN_SCOPE` at +1600 lines.
This card closes them. **Nothing here is speculative**: every figure was measured by CARD-261's cycle-3
reviewer with a plant that was executed.

### 1. `_ADAPTER_COUNT`'s boundary is a two-way regression (the Important from cycle 3)

Fix round 2 widened what counts as a quantity and **narrowed** the gap to the noun from two words to
one. The narrowing closed three false positives and opened a hole, proved by one plant run against both
revisions:

| plant in `CLAUDE.md` | at `feb3e6b5` | at `335c641e` |
|---|---|---|
| `"three distinct inbound adapters"` — a real count, two adjectives | **RED** | **GREEN exit 0** |
| `"Only the adapters import the orchestrator"` — states no count | **GREEN** | **RED**, *"CLAUDE.md states a count of adapters again"* |

A 44-form sweep at the new boundary found **eight** forms missed-or-falsely-caught that are in no
committed case and declared nowhere: a two-gap-word class of five, a parenthetical, a comma, a line
break, plus the new false positive. Two further facts, both of which are the real defect rather than the
pattern:

- the inline comment at `tests/test_cli.py:1119` declares the cost with a **three**-word example for a
  bound that shipped at **two**;
- the class docstring's *"every shape … is a committed case below"* is **false for all eight**.
- and the FP class the narrowing was *justified by closing* is narrowed, not closed —
  `"ADR-0019 section 2 adapters discussion"` still reds.

**Net reach is still better than `feb3e6b5`** (about eight new catch forms, including CARD-261's own
six-week defect, and three FPs closed), which is why this is a follow-up and not a revert. ~4 lines.

### 2. The pin list pins the wrong five (M-2 — one line)

Two of five known-miss slots are still padable, and the unpinned
`"sourcing covers CAP-001 and nothing else."` is the **only** corpus detector of the COMP/CAP widening.
Padded out, that widening still reds — but via a neighbour whose message **misattributes the cause to
`capabilities.yml`**. Exit 1 rather than exit 0, which is why cycle 3 scored it Minor rather than
gating. A misattributed failure message costs a future reader an hour.

### 3. Three figures in CARD-261's notes do not reproduce (M-3)

`:2194` is **not an assert lineno** — the cell is `:2191`; "five strings by value" on the adapter corpus
is **six**; "removes one line" is **twelve**. Correct them where they are *claimed*, and do not rewrite
the fix-round notes that recorded what that round believed — the same handling CARD-261 used for its own
non-reproducing figures.

### 4. The number bound is a live planter wrapped around two dead arms

`test_the_maps_adapter_count_is_the_other_hole_that_stays_open` genuinely reds when the lie stops being
planted — *"the lie was not planted … so this test has stopped measuring anything"*, verified. **But
cycle 3 defeated it**: closing the hole the way a later card actually would (a new test reading the count
out of the docstring and holding it to a walk-derived figure) left the test **GREEN at exit 0**, and a
third plant proved that closure genuine. The measured reason is exact: the planted lie touches **three
lines, all at indent 0**, and `_canonical_map(doc) == _canonical_map(lie)` is **True** — so the two
defect arms are *provably duplicates of live arms* and cannot fail for the stated reason.

**The contrast is the lesson and belongs in the fix.**
`test_a_wrong_description_is_the_one_hole_that_stays_open` uses a **fabricated** map and *is* a real
hole-assertion. A hole-assertion built on the real artefact can be satisfied by the artefact's live
arms; one built on a fabricated input cannot. That distinction is what CARD-261's cycle 3 produced that
no earlier cycle did.

### 5. `tests/README.md` is missing the sentence that would have saved three measurements

**Pytest's recording-pass exit code is not a kill signal.** Measured **three times independently across
two cards** in one afternoon: CARD-262's reviewer saw two mutants exit 0 while the matrix recorded FAIL;
CARD-261's fix round 2 saw **16 of 20 exit 0 with 15 of those carrying FAIL cells** — a test-level
reading would have published fifteen kills as survivors; CARD-261's cycle 3 saw both of its own.

The mechanism is in the instrument's own contract and is not a bug: `Pass.RECORDING`'s handler **does not
re-raise**, so a failing arm records FAIL and the test completes normally. The document explains the two
passes already (from line 453) and does not say this, which is why three separate agents had to rediscover
it. Draft wording is in `meta/review/20261022T111323Z-CARD-261-cycle3.yml`.

## Acceptance criteria

- **AC-1** *Given* `"three distinct inbound adapters"` planted in `CLAUDE.md`, *then* the count control
  reds; and *given* `"Only the adapters import the orchestrator"`, *then* it does **not**. Both states
  demonstrated against the shipped file, and the regression at two adjectives closed without reopening
  the three false positives fix round 2 closed. (test: `TestComponentMap_WhatTheAdapterCountReaderAbsorbs`)
- **AC-2** *Given* the eight forms cycle 3 measured at the boundary, *then* each is a **committed case**
  on the correct side, and the inline comment and class docstring state the shape **as shipped** — no
  three-word example for a two-word bound, and no *"every shape is a committed case"* claim that the
  case list does not support. (test: same class; the docstring is checked by the case table, not by eye)
- **AC-3** *Given* the known-miss corpus, *then* every case that is the **sole** detector of a widening
  is pinned by value, and a padding attack on any pinned slot reds with a message naming **the right
  cause** — not a neighbour's. Demonstrated by padding out `"sourcing covers CAP-001 and nothing else."`
  and reading the message. (test: `TestComponentMap_WhatTheClaudeMdReaderAbsorbs`, extended)
- **AC-4** *Given* the number bound, *then* it is either **closed** (held to the walk-derived figure, as
  cycle 3's own plant showed is possible) or asserted on a **fabricated** input so its arms cannot be
  duplicates of live arms. **State which shipped and why.** Demonstrated by re-running cycle 3's defeat:
  close the hole and show the bound test now reds. (test: `TestComponentMap_TheAdapterCountBoundIsReal`)
- **AC-5** *Given* `tests/README.md`'s two-pass section, *then* it states that the recording pass's
  pytest exit code is not a kill signal, names the mechanism (`Pass.RECORDING` does not re-raise), and
  says what to read instead. No test; this is prose, and the control is that the sentence is **there** —
  say so rather than inventing one.
- **AC-6** *Given* CARD-261's three non-reproducing figures, *then* each is corrected where it is
  claimed, and the fix-round notes that recorded what that round believed are **left intact**.

## Guardrails

- G-1: **Do not reopen the three false positives.** `"See section 3 about inbound adapters."` and
  `"the four tests cover adapters"` must stay clean; AC-1's second half plus committed cases are the
  control. Widening the gap back to two words is the obvious wrong fix and cycle 3 fired a mutant for it.
- G-2: **Do not weaken anything CARD-261 shipped.** The by-value pins, the per-side floors, the ten id
  defect kinds and the five `TestComponentMap_*` classes stay. This card extends and corrects; it
  removes no control.
- G-3: `CLAUDE.md` is **not** this card's to edit — CARD-264 owns its remaining prose and CARD-261 owns
  the layout block. Plant into it for a test and restore; do not ship an edit to it.
- G-4: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-5: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-6: ADR-0036/R4 — this card edits no `src/` file, so the rule should hold by construction; **verify
  rather than assume**.
- G-7: Take no timing measurements and report no durations.

## Architecture context

- **ADR:** ADR-0039/R1–R3 are the subject — a claim needs a control that can fail (AC-1/AC-4), a guard's
  set is derived rather than hand-written, and an exemption carries a control for what it must not
  absorb (AC-2/AC-3). ADR-0019 is the rule the adapter count describes.
- **Components:** none changed. Test files and one README only.
- **Trace:** `meta/architecture/trace.yml` — unchanged; no requirement's verifying test moves.

## Worktree notes

- **[Everything here was measured, not inferred]** Each figure above came from a plant that was executed
  by CARD-261's cycle-3 reviewer, with both states recorded. Re-derive before you rely on one — two
  figures of the orchestrator's were corrected by implementers on CARD-261 — but do not treat these as
  guesses to be re-litigated.
- **[The one-line items are one line each, and that is the point]** AC-3 and AC-6 are small. The card
  exists because five cheap bounds were left open by an escalation route that said `continue`, not
  `expand`, on a card already at +1600 lines. Keeping them together is cheaper than five drive-bys.
- **[Use the committed instrument]** `tests/kill_matrix.py`, documented in `tests/README.md` from line
  453, for any per-assertion figure. Do not write another. Keep deletion mutants
  **line-count-preserving**, aggregate **ANY-RED**, and **report the DOMAIN** of every figure —
  assert-node count versus collected-test count, selection, arms reached, SHIPPED result.
- **[And read AC-5 before you trust the instrument's exit code]** The sentence this card adds to the
  README is one you need while doing this card: the recording pass exits 0 on a killed mutant.
- **[A bound of CARD-261's certification worth knowing here]** M17 reaches only **2 of the 12** pin
  arms, and the padding attack is exactly the experiment artefact-mutation alone would never find. If
  you certify the arms you touch, mutate the **artefact** they pin and plant the attack separately.
- **[Gate figures]** This repo's `-q` output does not reliably print a pass-count line — it appeared at
  one gate and not at two later ones, and CARD-261's cycle 3 ruled out the `full_suite_lock` hook as the
  cause. Quote **pytest's exit code** plus a separate `--collect-only` pass, never a pass count.
