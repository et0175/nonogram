# ADR-0031: Retire the Guess tier — a difficulty is a score band again

**Status:** Accepted
**Date:** 2026-09-18
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** on-touch
**Pattern:** —
**API-Posture:** —

**Supersedes:** ADR-0025 ("Requires guessing" is a fourth difficulty tier, not a flag)

## Context

ADR-0025 (2026-09-12) added a fourth tier, `guess`, keyed on the verifying
solve's `branch_nodes` rather than on a score band. The argument was that
"needs a real guess" is a fact about the solve and can never be a threshold on
a number, and that Easy/Medium/Hard should therefore be able to promise
line-solvability.

The tier has never been assigned. Every measurement since has returned zero:

| measurement | branching puzzles |
|---|---|
| ADR-0029's sweep | 0 of 6,620 |
| CARD-076's | 0 of 462 |
| `tests/test_difficulty.py`'s AC-118 corpus | 0 of ~290 |
| this project's admin database | 0 of 16 rows |

CARD-072 then established *why*, which the rate alone had not: no random draw
in the supported extent range branches at all after the solver's own one-step
lookahead phase. The tier was not rare, it was unreachable from generation —
found by a mutation test, where a mutant that never appended `guess` survived
the whole suite because no test could pose a case that reached it.

ADR-0025's History anticipated the zero rate and kept the tier anyway, calling
it "the product promise stated as a fact, and a safety net for a future source
or extent that does produce a branching grid". That argument is real: image
mode, the library source, or a future extent might yet produce one.

## Decision

**Retire the tier.** `Tier` has three members, each a score band; `classify`
takes the score alone.

**Keep the fact.** A solve that branched still reports `guess` — as a
*strategy* (FR-029), named by `solver.STRATEGY_GUESS` and appended wherever
the strategies list is built. "This puzzle needs a guess" remains printable
beside a puzzle; it is no longer a claim about its difficulty.

**Read the old rows, migrate nothing.** `difficulty.tier_of_record("guess")`
answers `Tier.HARD`. Commit `bb1d5f6` records a real row in the production
database whose stored tier was `guess`, so this path is live, not defensive.
`None` would have been worse than wrong: it means "not a tier at all", and
such a row would drop out of every count and filter silently. Nothing rewrites
stored data; a re-grade (CARD-077) reassigns such a row on its own terms.

## Consequences

### Positive

- A tier is a bucket on the 0..100 scale again — no member without a band, no
  classifier that takes a second argument, no "three of the four" caveat in
  four docstrings.
- ADR-0025/R2 concentrated the branch-count comparison in one place because it
  decided a *tier*; it now decides a *strategy*, so the three call sites that
  had to ask `classify` read the count directly. The `ast` guard that enforced
  the old rule loses its second half rather than gaining three exemptions.
- One of the suite's two standing failures — the fourth tier's admin badge —
  is deleted rather than deselected.

### Negative

- **The safety net is gone.** If a future source does produce a branching
  grid, it will be filed in whatever band its score falls in, and only the
  `guess` strategy will say otherwise. `tests/property/test_difficulty_ladder.py`
  `::test_no_generated_puzzle_needs_a_branch` is the tripwire: it asserts the
  measurement this decision rests on, so a source that starts branching fails
  it and brings this ADR back for review.
- Rows written while the tier existed no longer say what they said. They read
  as Hard, which is a true statement about the puzzle but a lossy one about
  the grade it was given.

### Neutral

- No export schema version moves: neither format serializes `difficulty`
  (ADR-0023/R2 — the tier reaches a file only through the ADR-0016 filename
  and the FR-016 page header, both in-process).
- `--difficulty guess` becomes an ordinary unknown-tier refusal (AC-021).

## Alternatives considered

- **Keep the tier as a safety net** (ADR-0025's own position). Rejected by the
  owner: a tier that has never been assigned in ~7,400 measured puzzles is a
  cost paid on every consumer — four bands to handle, a two-argument
  classifier, a fourth badge, a filter option — against a case nobody has
  seen. The fact it protects is kept as a strategy at none of that cost.
- **Keep it but hide it from the UI.** Rejected: the shapes it forces
  (`band` returning `None`, the second classifier argument) are in the domain,
  not the interface, so hiding it would pay the cost and lose the promise.
- **Fold branching into Hard explicitly** — classify a branching solve as Hard
  regardless of score. Rejected: that *is* a second rule keyed on
  `branch_nodes`, which is what this decision removes; and it would overstate
  the difficulty of a branching puzzle whose score is low.

## References

- ADR-0025 (superseded), ADR-0029 (the ladder, unchanged), ADR-0005 (the bands)
- FR-029 (strategies), FR-008 (tier selection), EC-015 (retired with ADR-0025)
- CARD-072 (found the unreachability), CARD-098 (this change)

## Rules
```yaml
- id: ADR-0031/R1
  statement: Tier has exactly three members — easy, medium, hard — and every one has a score band. classify takes the score alone; no module derives a tier from branch_nodes.
  scope: {code: ["src/nonogram/difficulty.py"]}
  check: {kind: test, ref: TestTiers_ThreeBandsAndNoFourthTier}
  severity: mandatory
- id: ADR-0031/R2
  statement: A solve that branched is reported as the `guess` strategy (solver.STRATEGY_GUESS) in FR-029's strategies list, never as a tier.
  scope: {code: ["src/nonogram/orchestrator.py", "src/nonogram/admin/regrade.py", "src/nonogram/admin/puzzle_review.py"]}
  check: {kind: test, ref: TestTiers_BranchingIsAStrategyNotATier}
  severity: mandatory
- id: ADR-0031/R3
  statement: A stored difficulty_tier of "guess" reads back as Tier.HARD and is never rewritten by this decision; no migration runs and no production database is touched.
  scope: {code: ["src/nonogram/difficulty.py"]}
  check: {kind: test, ref: TestTiers_LegacyGuessRowReadsAsHard}
  severity: mandatory
```

## History

- 2026-09-18: Created — Accepted. Supersedes ADR-0025 on the owner's decision
  after CARD-072 established that the tier is unreachable from generation.
  The fact it carried survives as FR-029's `guess` strategy; the rows that
  carry its value are read, not migrated.
