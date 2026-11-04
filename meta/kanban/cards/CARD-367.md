# CARD-367: This board estimates in review cycles and has no ADR saying so — the decision is recorded only in the tool that reads it

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Found by CARD-363's implementation round, 2026-11-04, which pinned the absence with a test rather than reporting it: `ADR-0055` is cited by five of this board's artefacts and the local ADR series tops out at **0042**. Traced at the station to a cross-repository category error of the orchestrator's — see below.
**Idea:** —
**Wave:** —
**Created wave:** 76
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/decisions/adr/, meta/architecture/decisions/open.yml, meta/kanban/board.md, meta/kanban/retro.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What happened, and it is a category error rather than a typo

This board switched its estimate unit from **days** to **review cycles** at wave 74's open. That
decision is load-bearing: it is the single act that made a calibration signal possible —
wave 73 could export nothing at 0-of-3 coverage, wave 74 exported 3-of-3 at exactly 1.000 — and
every card since carries an `Nc (Md)` double entry because of it.

**It has no ADR on this board.** Measured: the local series is `0001` … **`0042`**.

**And ADR-0055 is a real, accepted ADR — upstream.** Measured 2026-11-04 by CARD-363's cycle-2 review and confirmed read-only: `/Users/omelnikova/MyProjects/forge_1/forge/meta/architecture/decisions/adr/0055-estimate-in-review-cycles.md` exists, 11833 bytes, status **accepted**, titled *«Единица оценки карточки — ожидаемые циклы ревью, не дни»*. So the decision **is** formally recorded — in the tool's own architecture, not in this board's. That makes this card's remit **narrower and clearer** than the title suggests: the gap is not "nobody wrote it down" but "this board adopted an upstream decision without recording the adoption". Any guard that promises to red "the day someone writes the ADR" is already void — it is written, and the pin will stay green forever.

**Where the citation came from.** `forge_1`'s retrospective skill documents its own estimate-unit
change as *"since ADR-0055 (switch_to_review_cycles, DEC-058)"*, and `switch_to_review_cycles`
appears in **forge_1's own** test suite and CI baseline. So **ADR-0055 is the TOOL's architecture
decision.** The orchestrator read it in the skill and cited it as if it were this project's — in
**five** artefacts (`board.md`, `dispatcher.state`, `retro.md`, CARD-363, CARD-366), all written
the same day. All five are now annotated as upstream and pointing here.

**So the defect is not the missing file. It is that this board adopted an upstream convention and
recorded the adoption nowhere** — the decision lives only in the tool that consumes it, which
means nothing here states *why* this project estimates in cycles, what the unit means, or what
happens to the pre-switch cards.

**Re-derive the series maximum and the five citing artefacts** before implementing; both are
dated readings and CARD-363's `test_the_estimate_unit_decision_still_has_no_adr_file` will **red
the moment the ADR lands**, which is deliberate — it sends its author to the forward-scope
constant that currently stands in for the decision.

## What the ADR has to settle, because the convention is already in force

1. **The unit and its spelling.** `Nc (Md)` — cycles primary, days as the rollback path. Why both,
   and when the parenthetical may be dropped.
2. **What a cycle *is*.** A completed review cycle, counted by the `[Review N/M] Score:` marker —
   except the marker is absent on **128** of the board's scored cards and the `Review score` text
   carries the count on **228 of 231**. **The ADR should say which field is authoritative**,
   because CARD-363 guards the agreement between them and the tool reads the one with worse
   coverage.
3. **The pre-switch population.** **244** cards carry a numeric `Wave` and no `Nc` estimate, and
   `max(wave)` over them is **< 74** — so wave 74 is the convention's measured start rather than
   an arbitrary cut. The ADR should declare that boundary, since every guard scopes forward from
   it.
4. **That `accuracy_ratio` over a days-estimated card is NULL, never 0.0.** A retro folding it in
   as zero reads "overestimated" for a card nobody estimated in cycles. This is the consequence
   most likely to be got wrong by a later reader.
5. **The wall-clock exclusion**, which is the owner's standing ruling and belongs beside the unit:
   wall-clock actuals are unusable for calibration because the clock measures the queue, not the
   work. Every card since has substituted a derived size datum with the exclusion stated in its
   own field.

**Figures in this card are CARD-363's measurements, not the orchestrator's** — four of five of the
orchestrator's own figures for that card did not reproduce, so take them from the module's own
asserted bounds and not from here.

## What to implement

1. **Write the ADR** in Nygard format through the normal flow — Context, Decision, Consequences —
   at the next free local number. **Do not reuse 0055**: it is the tool's number, and taking it
   would make a cross-repository collision permanent.
2. **Record it in `open.yml`/`resolved.yml`** as the registries expect, so the decision is
   discoverable by the same walk as every other.
3. **Re-point the five annotated citations** at the new local ADR, and drop the "see CARD-367"
   pointer once it exists.
4. **Expect CARD-363's absence test to red**, and update that constant rather than deleting the
   test — it exists so the ADR's author is sent to the code the decision governs.

## Acceptance criteria

- **AC-1** *Given* the local ADR series, *then* a Nygard-format ADR records the estimate-unit
  decision at a **free local number**, and `0055` is not reused.
  (test: named by the implementation; state it)
- **AC-2** *Given* the ADR, *then* it settles all five points above, and each of (2), (3) and (4)
  states its figure as **derived from the card tree** rather than quoted from this card.
  (check: review-lens)
- **AC-3** *Given* the five annotated citations, *then* each points at the new local ADR and none
  still reads as if `ADR-0055` were this board's.
  (test: named by the implementation; state it — a text search over the five is sufficient and
  should be asserted)
- **AC-4** *Given* CARD-363's `test_the_estimate_unit_decision_still_has_no_adr_file`, *then* it is
  **updated, not deleted**, and still able to fail — its job becomes pinning that the decision
  *has* an ADR and that the constant matches it.
  (test: that test, by name)
- **AC-5** *Given* the decision registries, *then* the new ADR is discoverable by the same walk as
  every other, and the validator reports no new dead reference.
  (test: the validator of record, 0 errors)

## Guardrails

- **G-1** — **`/Users/omelnikova/MyProjects/forge_1` is READ-ONLY.** ADR-0055 is its decision; do
  not edit it, do not renumber it, and do not "fix" its skill text.
- **G-2** — **Do not reuse the number 0055.** A local ADR at that number makes the collision
  permanent and un-greppable.
- **G-3** — Do not delete CARD-363's absence test to make the tree quiet. AC-4 is the guard.
- **G-4** — Do not restate the figures from this card as measurements. Four of five of the
  orchestrator's figures for CARD-363 did not reproduce; derive them.
- **G-5** — No `src/` change; no new runtime dependency (ADR-0006/R1).
- **G-6** — Take no timing measurements and report no durations.
- **G-7** — When comparing validator output, match `^[[:space:]]*\[WARN` (the validator indents two
  spaces) and assert both sides non-empty before comparing.

## System contract

- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate
  (check: review-lens)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written
  (check: review-lens)
