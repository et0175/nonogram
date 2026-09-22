# ADR-0032: What the admin panel guarantees about a stored puzzle

**Status:** Accepted
**Date:** 2026-09-22
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** on-touch
**Pattern:** —
**API-Posture:** —

## Context

The admin panel builds puzzles as plain dicts and writes them through
`PuzzleReviewService.add_puzzle`. It never instantiates `orchestrator.Puzzle`,
so INV-002 — the export gate the orchestrator enforces on its own aggregate —
does not reach it. For a long time nothing else did either: no ADR, no
constraint and no rule said anything about what the admin's storage path
guarantees.

Two defects grew in that gap, both of them shipped and both found by reading
rather than by any check:

- **Grids that were not puzzles.** Until CARD-080 the admin stored whatever it
  was handed. `MockGenerator` — then in `src/` — produced a random 50%-density
  grid, clue lists of random integers unrelated to it, and a random grade; 29
  tests stored that and called it a puzzle. The same shape of defect had
  already been deleted once, in the twenty rows `image_to_puzzle.create_puzzle_
  from_image` wrote on 2026-09-14.
- **A metric nobody had defined.** `quality_score` and `recognizability` have
  never appeared in any ADR or in `requirements.yml`. CARD-049/CARD-050 replaced
  a hardcoded `75` with a real measurement for image mode and an explicit
  `None` for random mode — the right decision, recorded only in a card. Three
  consumers then each decided separately what `None` meant: the in-memory
  filter compared it (`None < 50` raises `TypeError`, reachable from two
  routes), the DB filter dropped it silently via SQL `NULL`, and the book PDF
  printed `Quality: None/100` because its `.get("quality_score", 0)` default
  never fires on a key that exists and holds `None`. Five templates had
  meanwhile settled on `quality_score or 'N/A'` without anyone saying so.

CARD-080 fixed the first. This ADR records both guarantees so the next
consumer inherits a decision instead of making one.

## Decision

**A stored puzzle has been proved unique, and its quality is either a
measurement or explicitly absent.**

1. `PuzzleReviewService.add_puzzle` re-derives the clues from the grid it was
   given and asks the solver. A grid whose clues do not have exactly one
   solution is refused with `NotUniquelySolvable`, and a solve that cannot
   answer — a timeout — is also a refusal. Nothing is stored on the caller's
   word. The check is the storage boundary's own, not a precondition it
   documents and hopes for.

2. `quality_score` is an integer 1..100 when a conversion was measured
   (`analysis.quality_metric.measure_quality`, image mode) and `None` when
   there was nothing to measure (random and library mode). `None` means
   **unknown**, not zero and not an error: it never satisfies a minimum, it is
   never compared with `<`, and it renders as `N/A` on every surface —
   templates, the admin API and the printed book alike. `recognizability`
   follows the same rule with its own vocabulary.

## Consequences

- A caller that wants a puzzle stored has to give the boundary a real grid; the
  refusal is an exception, not a return code, because a caller offering an
  ambiguous grid has a bug rather than a condition to handle.
- Every quality filter has two outcomes to think about instead of one. A
  minimum excludes unmeasured puzzles, which is what the DB path already did,
  so nothing changes for the deployed Postgres store — the in-memory path stops
  raising and starts agreeing with it.
- A book containing random-mode puzzles prints `N/A` for their quality rather
  than `None/100`. No stored value changes.
- R1 covers the admin's storage path only. The orchestrator's own gate is
  INV-002 and is unchanged; the two now say the same thing about their own
  doors.

## Alternatives considered

### quality_score defaults to 0 when unmeasured

Rejected. It reads as a measurement — the worst score there is — and a book
would print `Quality: 0/100` for a puzzle nobody assessed. The distinction
between "measured badly" and "not measured" is exactly what CARD-050 bought by
retiring the hardcoded `75`; collapsing it again would spend that for the
convenience of one comparison.

### An unmeasured puzzle passes every minimum

Rejected as the default, though it is defensible: a user filtering by quality
is asking about measured quality, and answering with puzzles that have none is
answering a different question. It would also have made the in-memory and DB
paths disagree in a new way, since SQL `NULL` cannot be talked into passing a
`>=` without rewriting the predicate.

### Leave the guarantees in the cards that made them

Rejected — that is the arrangement this ADR exists to end. CARD-080's guard and
CARD-050's `None` were both real decisions, discoverable only by reading a card
nobody has a reason to open.

## References

- CARD-080 — the storage guard, the audit, and `MockGenerator` rewritten
- CARD-049 / CARD-050 — the real quality measurement and random mode's `None`
- CARD-055 — `MockGenerator` moved out of `src/` to the test tree
- CARD-056 — this ADR, and the two consumers that disagreed about `None`
- INV-002 — the orchestrator's own export gate, which this does not change
- CON-005 — the solver must never call a non-unique puzzle unique

## Rules
```yaml
- id: ADR-0032/R1
  statement: Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid it was handed and refuses, with NotUniquelySolvable, any grid whose clues do not have exactly one solution — including one whose solve timed out or could not be attempted. No caller's assurance substitutes for that check, and no admin path writes a puzzle row by another route.
  scope: {code: ["src/nonogram/admin/**"]}
  check: {kind: test, ref: TestStorageBoundary_AsksTheSolverNotTheCaller}
  severity: mandatory
- id: ADR-0032/R2
  statement: quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never satisfies a quality minimum, is never the left operand of an order comparison, and renders as "N/A" wherever a score would be shown — templates, API responses and the book PDF alike, the book omitting the /100 denominator that a non-number does not take. recognizability carries the same rule in its own vocabulary.
  scope: {code: ["src/nonogram/admin/**"]}
  check: {kind: test, ref: TestUnmeasuredQuality_SurvivesTheFilter}
  severity: mandatory
```

## History

- 2026-09-22: Created — Accepted. Records two guarantees that were already
  decided but never written down: CARD-080's uniqueness guard at the storage
  boundary, and CARD-050's definition of `quality_score`. R2 was written
  against three consumers that had each answered the `None` question
  differently, two of them wrongly; CARD-056 fixed both in the same change, so
  the rule and the behaviour land together rather than the rule describing an
  intention.
