# CARD-363: The retrospective's two inputs are unguarded — the cycle marker is absent on 152 of 279 closed cards, and nothing requires a wave's estimate to be in the unit the ratio needs

**Status:** ready
**Priority:** P1
**Category:** enabler
**Estimate:** 2c (0.5d)
**Complexity:** standard
**Skill:** python-pro
**Revision pending:** false
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Measured at the station 2026-11-04 after five review artefacts in two waves had to be reconstructed from agents' hand-back messages. The measurement found the gap is not five cards but systemic, and that the orchestrator's own diagnosis of it was half wrong — see "What the measurement changed".
**Idea:** —
**Wave:** —
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_kanban_review_record.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The measurement

Over all **279** `done` cards carrying a `Review score`:

| | count |
|---|---|
| marker count disagrees with the cycle the card's own score names | **136** |
| **zero** `[Review N/M] Score:` markers at all | **152** |
| no review YAML on disk | **81** |
| the score text states its cycle (`cycle N of M`) | **279 of 279** |

**Re-derive all four.** They are a dated reading and the sets matter more than the counts.

## What the measurement changed, including about my own diagnosis

The retrospective derives `cycles_used` by counting exactly `[Review N/max] Score:`. I had
diagnosed the absence of that marker as the reason wave 73 could export no calibration signal,
and wrote markers onto wave 74's three cards to fix it.

**The marker was never where the information lived.** The `Review score` field already states
the cycle — *"8.4 (cycle 2 of 3 — CERTIFIED)"* — on **279 of 279** scored cards, while the
marker is present on **127**. So the numerator was available for the whole of the board's
history, in a field the extractor does not read.

**And the thing that actually blocked wave 73 was the DENOMINATOR, not the numerator.** Measured
per wave:

| wave | estimates in cycles? | ratio computable |
|---|---|---|
| 71 | no — `0.5d`, `0.75d` | **0 of 2** |
| 72 | no — `0.25d`, `2d` | **0 of 2** |
| 73 | no — `0.25d`, `0.5d`, `0.5d` | **0 of 3** |
| 74 | **yes** — `1c`, `1c`, `2c` | **3 of 3** |

Waves 71–73 had the cycle count all along and no **cycle estimate** to divide it by. So wave 73's
retrospective reached the right conclusion ("no signal exportable") for a reason that was only
half the cause, and wave 74's signal exists because the estimates were **restated in review
cycles at the wave open** — a decision made before any work happened — and not because markers
were written.

**That is what this card protects: the unit of the estimate, which is the scarce input.**

## What to implement

A new module, `tests/test_kanban_review_record.py`, holding two guards. Both read **tracked**
files only — card bodies — so neither depends on the untracked review YAMLs and neither reds on
a fresh clone.

1. **The marker agrees with the score.** For each card whose `Review score` names a cycle,
   assert the `[Review N/M] Score:` marker count equals that cycle number. **Scope it forward**
   from a stated card id or date and **declare the historical population as a measured bound**
   (ADR-0039/R3) — do not demand 152 cards of fabricated history, and do not silently exclude
   them either. Name the count in the bound so it cannot grow unremarked.
2. **A card that ran in a wave carries a cycle estimate.** For each card with a `Wave:` that is a
   number, assert its `Estimate` states an `Nc` term. Same forward scoping and the same declared
   bound for the pre-ADR-0055 population.

**Derive both populations from the card files** (ADR-0039/R2), never from a list. A card the walk
cannot classify — a `Review score` whose text states no cycle, say — is a **FAILURE**, not a
skip: that is the shape this whole family keeps producing.

## Acceptance criteria

- **AC-1** *Given* the card tree, *then* a card whose score names cycle N and carries ≠ N markers
  **reds by name**, demonstrated by planting one — and the unplanted tree is green.
  (test: named by the implementation; state it)
- **AC-2** *Given* a card stamped with a numeric `Wave` whose `Estimate` carries no `Nc` term,
  *then* it **reds by name**, demonstrated by planting one.
  (test: named by the implementation; state it)
- **AC-3** *Given* the historical populations, *then* each is **declared with its measured count**
  and the declaration is asserted, so neither can grow silently. State both counts as measured,
  not as the figures in this card.
  (test: named by the implementation; state it)
- **AC-4** *Given* a card the walk cannot classify, *then* it is a **FAILURE and not a skip**
  (ADR-0039/R2), demonstrated.
  (test: named by the implementation; state it)
- **AC-5** *Given* both guards, *then* they read **only tracked files** — no dependence on
  `meta/review/*.yml`, which is untracked by convention and absent in a fresh clone. State how
  you verified it.
  (test: named by the implementation; state it)

## Guardrails

- **G-1** — No `src/` change; this is board hygiene expressed as a test.
- **G-2** — **Do not fabricate history.** Writing markers onto 152 closed cards would invent
  intermediate scores nobody recorded. Declare the bound instead.
- **G-3** — **`/Users/omelnikova/MyProjects/forge_1` is READ-ONLY.** The extractor that reads the
  marker lives there. If the real fix is "read the score field instead", that is a finding handed
  upstream with its measurement — not an edit.
- **G-4** — Do not loosen either guard to accommodate the historical population. AC-3 is the
  mechanism for that, and a bound without an asserted count is not a bound.
- **G-5** — No new runtime dependency (ADR-0006/R1); stdlib only.
- **G-6** — Take no timing measurements and report no durations.
- **G-7** — A full suite needs the board's lock (structured, worktree identity, **no pid**). Never
  set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, never redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard
  fires in `pytest_configure` for **any** selection.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none
  exists it defaults to **deny** (check: review-lens)
- ADR-0039/R3 — a declaration carries a reason and a measured residue (check: review-lens)
- ADR-0055 — review cycles are the estimate unit (check: review-lens)
