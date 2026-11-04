# CARD-346: `SIBLING_FINDINGS` pins that a fact diverges, not what it is — the same lesson `DECLARED_DIVERGENCES` already learned

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Raised as F-3 by CARD-339's review cycle 1 (2026-11-04), which falsified the round's own claim with two plants rather than reading the code. Carded rather than folded in because mechanising it is in-pattern but out of CARD-339's scope; what CARD-339 owes is the retraction of the overclaim, which its fix round takes.
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** CARD-339
**Touches:** tests/test_public_player_agreement.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, falsified rather than argued

CARD-339 added a `SIBLING_FINDINGS` registry of facts that **do** differ between the two
player stylesheets, that nobody has decided, and that the guard claims to pin. `RoutedFinding`'s
docstring says it is "a fact outside [the compared surface] that *does* differ … and that this
guard **pins so neither sheet can change it unremarked**."

**For four of its six entries, it does not.** CARD-339's reviewer planted twice:

| plant | effect | census test |
|---|---|---|
| admin `.player-swatch[data-state="filled"]` `border-color: var(--grid-ink)` → `var(--color-danger)` | the fact's value changes | **still passes** |
| public `.player-swatch[data-state="unknown"]` `background` → `var(--color-danger)` | **a rendered pixel the owner would see** changes | **still passes** |

What *is* mechanised — and it is real and worth keeping — is that each fact keeps **diverging**:
`diverging == set(SIBLING_FINDINGS)` reds in both directions. Value-pinning exists only for the
**two Maybe papers**, through hand-written literals in
`test_the_paper_under_the_maybe_mark_is_a_routed_finding_and_not_an_exemption`. No equivalent
protects the other four.

**Re-derive all of this before implementing** — the plants, the four-of-six split and the
registry's size are dated readings, and a different result is the finding.

## Why it is the same lesson twice

`DECLARED_DIVERGENCES` already has the counterpart: **`RESIDUE_CONTROLS`**, holding what may
differ *inside* an exempted key. That mechanism exists because **CARD-328's cycle-1 review
raised it as IMP-1** — this exact lesson, one registry over. `SIBLING_FINDINGS` was built
without it.

So routing currently permits something a declared divergence does not, which is the one
asymmetry that makes "routed" weaker than it reads. It is **not** an exemption table —
`test_no_mark_is_both_compared_and_routed` holds the two disjoint and nothing inside the
compared surface is excused — it is an **overclaimed queue**.

## What to implement

1. **Give `SIBLING_FINDINGS` a residue control**, derived the way `RESIDUE_CONTROLS` is rather
   than reinvented: each routed fact's **current value on both sides** is held, so a change in
   either sheet reds. Read CARD-328's mechanism first and say what you reused.
2. **Decide what a residue is for a fact whose two sides are cascaded**, and state it — the
   paper facts are read against the hook's base rule so "declares nothing" and "declares the
   base's background" are not a false divergence. A residue control that compares pre-cascade
   values would red on a no-op refactor.
3. **Do not widen the compared surface.** A routed fact that becomes compared is a decision for
   the board owner, not this card. If a fact turns out to need no routing at all, that is a
   finding to report, not a move to make.

## Also owed here — MIN-3: the census has no committed plant on a glyph fact

**Measured by CARD-339's review cycle 2.** Both `CENSUS_PLANTS` entries target `.paper` facts,
so the census's **glyph reader has no committed control** — which matters most for the four
facts CARD-339 newly labelled as *agreeing because neither sheet draws a glyph there*.

**It is a missing control, not a live hole, and that distinction was established by hand:** the
reviewer planted a real `::after { content: "Z" }` on each of the four absent facts on each
sheet and got **8 of 8** unilateral directions moving the census and reding the classification
arm; a total glyph-reader death is separately caught by the anti-vacuity floor (`drawn` 12 → 8
against a floor of ≥ 10). So the reader is not blind — nothing *committed* proves it.

**Add a third `CENSUS_PLANTS` entry on a glyph fact**, and re-derive the 8-of-8 rather than
trusting it.

## Acceptance criteria

- **AC-1** *Given* each of the routed facts, *then* changing its value in **either** sheet
  **reds** — demonstrated by one plant per sheet per fact, or by a derivation that covers all
  of them with two plants and says why that is total.
  (test: named by the implementation; state it)
- **AC-2** *Given* the **one** fact that has literal pinning — `.player-cell.maybe.paper`, and
  **only** that one — *then* it still reds, and the hand-written literals are **replaced by the
  derived mechanism** rather than left beside it; two mechanisms for one claim is how a stale
  exemption survives.
  **An earlier wording here said "the two facts that already had literal pinning", which
  inherits the very overclaim CARD-339's gate narrowed** (its IMP-2): the *cell* fact is pinned
  by literals, the *swatch's public side* only transitively through its equality with the cell,
  and **the swatch's admin side is held to nothing but diverging**. AC-1 above — "changing its
  value in **either** sheet reds" — is what genuinely closes that fourth side, so this card's
  scope was always right and only this sentence was wrong.
  (test: `test_the_paper_under_the_maybe_mark_is_a_routed_finding_and_not_an_exemption`)
- **AC-3** *Given* `DECLARED_DIVERGENCES`, *then* it is unchanged (3 entries, CARD-328's) and
  `test_no_mark_is_both_compared_and_routed` still holds the tables disjoint.
  (test: `test_no_mark_is_both_compared_and_routed`)
- **AC-4** *Given* a no-op refactor of either sheet that changes no rendered value, *then*
  nothing reds — the control must not fire on cascade-equivalent rewrites (per item 2).
  (test: named by the implementation; state it)
- **AC-5** *Given* the docstring of `RoutedFinding`, *then* its claim matches what the code
  does, and if any gap remains it is stated rather than implied.
  (check: review-lens)
- **AC-6** *Given* `CENSUS_PLANTS`, *then* it carries at least one entry on a **glyph** fact,
  and planting it reds the classification arm — so the glyph reader has a committed control and
  not only a hand-measured one (MIN-3).
  (test: named by the implementation; state it)

## Guardrails

- **G-1** — No `src/` change. Plants into `src/nonogram/admin/static/admin.css` are
  measurements and must be **restored from captured content** with SHA-256 both ends; leaving
  an edit there is the violation.
- **G-2** — Do not add an entry to `DECLARED_DIVERGENCES`. An exemption added to make this card
  green is the defect one level up.
- **G-3** — No new runtime dependency (ADR-0006/R1).
- **G-4** — Take no timing measurements and report no durations; other work shares the machine.
- **G-5** — ADR-0041/R2: no public asset may carry a solution grid or data from which any
  solution cell is recoverable. Say what you verified.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate
  (check: `test_every_census_fact_is_compared_routed_or_agreeing`)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written
  (check: review-lens)
