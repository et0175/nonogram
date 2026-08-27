# Wave 3 — 2026-08-27   (tag: wave-3)

## Shipped
- CARD-004 (feature): Hand-rolled nonogram solver with fail-fast uniqueness check — constraint propagation to a fixed point + backtracking search over an int-bitmask internal representation (ADR-0012), stopping immediately after a 2nd distinct solution is found.   score 9.4 (cycle 2/3)   FR-006, NFR-001 (partial), CON-005 (mandatory), EC-001

## Requirements closed
- FR-006 (fail-fast solution counting), CON-005/EC-001 (the uniqueness check's no-false-positive property) — verified empirically: a mandatory property test (2400 adversarial/mutated cases, sizes 1x1..8x8) cross-checked against an independent ADR-0014 brute-force oracle, then independently re-verified by the reviewer with a THIRD from-scratch oracle sharing no code with either the solver or the in-repo oracles, over 3000 additional cases — 0 mismatches across both rounds.
- AC-017's fail-fast property confirmed across 22 orders of magnitude of solution-count growth (a 24x24 clue set with ~6.2e23 solutions returns "MANY" in 22ms).

## Architectural precedent set (worth reading before later cards)
This card's own text said "the solver consumes the clue API," which on a literal reading
implied importing `nonogram.clues` from `nonogram.solver`. That conflicts with ADR-0007's
capability-module boundary rule, mechanically enforced since CARD-001 by a disk-walking
test (`tests/test_cli.py`) that fails on any lateral import between capability modules.
The implementer resolved this in favor of the enforced ADR — consuming the clue *contract*
(the boundary types) without importing the clue *module*, reimplementing the one native
check needed and pinning it against `clues.encode_line` from the test tree, where the
cross-capability import is legal — and explicitly flagged the tension for review rather
than resolving it silently. The review ruled this correct: an ADR is the standing norm,
card prose is derived, and a norm with a merged enforcement test is not an open decomposition
question. **Precedent for future cards:** "consumes the X API" in a card's prose means the
X module's public *contract* (its types), never the X *module* — cross-capability imports
stay forbidden regardless of how a card's text is phrased.

## Convergence
- N/A — no wave-level goal-backward check configured yet (begins once user-facing cards land, wave 5+)

## Known gaps / escalations
- none. Performance characteristics measured and documented for downstream cards: line-solvable
  grids are trivial at every size, but random mid-density 40x40+ grids are the known-hard class
  where the search can take seconds without a deadline — CARD-006's ADR-0011 timeout is not
  optional at those sizes (hook points already in place), and CARD-005's retry loop should
  expect SolverTimeout as a normal outcome there, not exceptional.

## Migrations
- none
