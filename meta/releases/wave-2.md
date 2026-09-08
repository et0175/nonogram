# Wave 2 — 2026-08-27   (tag: wave-2)

## Shipped
- CARD-002 (feature): Clue derivation via run-length encoding — `nonogram.clues`, the ADR-0012 boundary-type-only public surface for INV-001.   score 9.0 (cycle 2/3)   FR-005, INV-001
- CARD-003 (feature): Random grid sourcing with size/density validation — `nonogram.sourcing` package, random path, seeded/injected RNG (ADR-0015), exact-count density sampling proven within ADR-0003's ±3pp band at all 4141 size/density combinations.   score 9.5 (cycle 2/3)   FR-001, FR-004

## Requirements closed
- FR-005, INV-001 (clue derivation + its own invariant) — verified, not just asserted, after cycle-1 review caught and cycle-2 confirmed a fix for a tautological test
- FR-001, FR-004 (random grid sourcing) — verified

## Review process note
Both cards needed one fix cycle before merge, and both catches were substantive, not
stylistic:
- CARD-002: the AC-014/INV-001 test compared `encode_line()`'s output against itself
  (`clue_matches_line` re-derived via the same function), so it could not fail no
  matter how broken the encoder was. Proven by mutation (reversing run order on lines
  >21 cells passed all 166 tests). Fixed with an independent oracle (a from-scratch
  `itertools.groupby` encoder sharing no code with the module under test); the cycle-2
  reviewer independently re-derived the fix by reproducing the same mutation and a
  6-mutant battery, plus cross-checking the new oracle against a third encoder over
  20,000 random lines.
- CARD-003: the G-4 (no module-level `random` usage) structural guard's own self-test
  never called the real detector, so the detector could be silently broken without
  failing anything. Fixed by pointing the self-test at the real function against a
  real violating file, and tightening the detector's evasion coverage (aliased
  imports). ADR-0003's ±3pp density tolerance was independently proven to hold
  exhaustively across the full size/density space, not just the tested cases.

## Convergence
- N/A — no wave-level goal-backward check configured for this scaffolding-adjacent wave (full FR/NFR convergence checks begin once user-facing cards land, wave 5+)

## Known gaps / escalations
- none
- Minor follow-ups routed to downstream cards' Worktree notes rather than fixed here (out of each card's scope): CARD-004 carries two notes (do not call `clue_matches_line`/`encode_line` in the hot propagation loop — perf + partial-line hazard); CARD-008 carries one note (the G-4 test guard has two known evasion gaps to check against before assuming coverage).

## Migrations
- none
