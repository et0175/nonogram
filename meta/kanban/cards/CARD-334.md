# CARD-334: Seven requirements say a decision is expected — one has provably been made, and nobody knows about the other six

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** business-analyst
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-316's review cycle 1, 2026-10-31, which found two stale `_meta.dec_expected` flags inside its own set and derived the family as seven. Re-measured at the decompose station, where the premise changed — see below.
**Idea:** —
**Wave:** —
**Created wave:** 72
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, meta/architecture/decisions/resolved.yml, meta/architecture/decisions/open.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists — and why it is NOT the card the review described

CARD-316's round found `FR-028._meta.dec_expected` and `FR-035._meta.dec_expected`
still reading `true` although DEC-034 and DEC-036 are resolved. Its review then derived
the family as **seven** and recommended one card for all of them, on the reading that
**every** one has a resolved DEC behind it.

**That reading is not confirmed, and the orchestrator's own check at the decompose
station points the other way for four of the seven.** Both readings are recorded here
because the card's first job is to settle which is right — not to act on either.

### Measured 2026-10-31 by the orchestrator

`_meta.dec_expected: true` appears on exactly **seven** requirements — that much agrees:
**FR-025, FR-026, FR-027, FR-028, FR-030, FR-035, FR-044.**

But they are **not one situation**:

| requirement | what its own `_meta` records | reading |
|---|---|---|
| **FR-027** | `decided: 2026-09-17`, `decided_by: owner, after the visual gate (CARD-079)`, `chosen_alternative: ink_coverage_threshold_50pct`, `gate_discharged`, `gaps: []` | **provably stale** — it records its own decision *and* keeps the flag |
| **FR-028** | `dec_question` + `dec_alternatives`, no `decided` | stale **per CARD-316's round**, which found DEC-034 → ADR-0027 `refuse_degenerate_density` (2026-09-12) |
| **FR-035** | `dec_question` + `dec_alternatives`, no `decided` | stale **per CARD-316's round**, which found DEC-036 → ADR-0034 `fixed_150_at_40_40_20` (2026-09-22) |
| **FR-025** | `dec_question` on random-mode recovery (pure redraw / repair / redraw-then-repair), `criteria_by_alternative`, no `decided` | **looks genuinely open** |
| **FR-026** | `dec_question` on guessing-as-flag vs fourth tier, `supersedes_pending`, no `decided` | **looks genuinely open** |
| **FR-030** | `dec_question` on **where the book's page geometry lives** — extend COMP-007's `compute_layout` or a book-owned geometry in COMP-009 — no `decided` | **looks genuinely open, and is live to the vector phase** |
| **FR-044** | `dec_question` on the player's client approach, many `amended_*` entries, no `decided` | **looks genuinely open** |

And on the decision side: `open.yml` holds exactly **one** open decision, **DEC-026**, about
the PDF export filename, and it names none of the seven. So four requirements expect a
decision that exists in **no** DEC record at all — neither open nor resolved by any
mapping the orchestrator could find from the requirement side.

**A caution this card must not repeat.** The orchestrator's first attempt asked "is this
requirement id *named* in `open.yml`?" and got four hits — all **mentions in prose**, not
open decisions. That is the mention-is-not-a-definition hazard, in the check written to
look for it, three cards after the family that exists to stamp it out. **Derive from the
DEC records' own structure, not from a text search.**

## What to implement

1. **Establish, per requirement, whether a decision has actually been made**, and by what
   authority: a resolved DEC, an ADR, an owner decision recorded in `_meta` (FR-027's
   shape), or nothing. **Derive it; do not grep for the requirement id.**
2. **Clear the flag only where the decision is made**, and record *what* was decided and
   where, in the form FR-027 already uses (`decided`, `decided_by`, `chosen_alternative`,
   and `gate_discharged` where a gate existed). FR-027 is the worked example: it is
   complete except for the flag.
3. **Leave the flag set where the decision is genuinely outstanding** — that is the flag
   working, not a defect. For each one left set, say in one line *what the open question
   is* and whether a DEC record should exist for it, because four of the seven currently
   expect a decision that no DEC record mentions.
4. **Surface, do not decide.** None of these questions is this card's to answer, and two
   are consequential: **FR-030** asks where the book's page geometry lives, which the
   vector phase (CARD-322 and its dependencies) is actively building against, and
   **FR-044** is the player's client approach, already shipped one way. If a requirement's
   question was settled *in practice* without a record, that is the finding — report it,
   with the evidence, and let the owner decide whether to record it retroactively.

## Acceptance criteria

- **AC-1** (the family is derived, not listed): *Given* the registry, *then* the set of
  requirements carrying `_meta.dec_expected: true` is derived by parsing, with its count
  asserted, and **every** member classified — nothing unclassified (ADR-0039/R2). The
  expected figure is **7**; a different number is a finding.
- **AC-2** (each flag's truth is established by authority): *Given* that set, *then* each
  member is resolved to *decided* or *outstanding* **by a DEC/ADR record or a recorded
  owner decision**, never by a text search for the requirement's id, and the authority is
  named per member.
- **AC-3** (only the settled ones are cleared): *Given* the classification, *then* the
  flag is cleared exactly on the members shown decided, each carrying what was decided and
  where; the others keep it, each with its open question stated in one line.
- **AC-4** (the four without a DEC record are reported): *Given* that `open.yml` holds one
  decision naming none of the seven, *then* the card reports which members expect a
  decision that no DEC record mentions, and says whether one should be opened — **without
  opening or answering it**.
- **AC-5** (the change can fail): **Two mutants** — one clearing a flag whose decision is
  outstanding, one leaving set a flag whose decision is recorded — both killed.

## Guardrails

- **G-1: decide nothing.** Not FR-030's geometry question, not FR-044's client approach,
  not any other. This card establishes the *state of the record*, and a card that answers
  an architectural question by side effect is the failure mode this board has paid for.
- **G-2: do not open or close a DEC.** If a decision record should exist, say so.
- **G-3: `dec_expected` appears to gate no validator behaviour** — the review found none,
  and the orchestrator did not re-check. **Verify that before treating the warning count
  as the measure of this card**, and expect the count not to move. This is a
  record-honesty card, not a warning-count one.
- **G-4: no criterion's `test:`, `then`, `given` or `when` is touched.** Those are
  CARD-316's and CARD-317's subject and the owner settled their shape on 2026-10-31.
- **G-5: no test deleted, renamed, skipped or merged**; node-id set difference as the gate.

## Notes

- **Do not inherit the "all seven are stale" framing.** It is one of the two readings on
  the table and the orchestrator's measurement contradicts it for four members. The card's
  value is the classification, and if the review's reading turns out right, that is the
  finding and it is cheaply stated.
- **FR-027 is the worked example of the destination**, not of the defect: it carries
  `decided`, `decided_by`, `chosen_alternative`, `gate_discharged` and an empty `gaps` —
  everything except a cleared flag.
