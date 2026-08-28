# Wave 4 — 2026-08-28   (tag: wave-4)

## Shipped
- CARD-005 (feature): Pipeline orchestrator (`Puzzle` aggregate, AGG-001) and the auto-regenerate retry loop — `nonogram generate` now runs source → clues → solve → mark-ready end to end for the first time, with a bounded (20-attempt, ADR-0002) regenerate-on-uniqueness-failure loop and the INV-002 export-readiness gate.   score 9.5 (cycle 1/3)   FR-007, NFR-002, INV-002, INV-003

## Milestone
This is the first wave where `nonogram generate` does not raise `NotImplementedError`.
Manually verified: `nonogram generate --size 12 --density 40 --seed 7 --export json` exits 0
and runs the real pipeline (no file is written yet — export renderers are CARD-007+).

## Requirements closed
- FR-007 (auto-regenerate on uniqueness failure), NFR-002/INV-003 (the retry bound), INV-002
  (export-readiness gate) — all three have named tests exercising the REAL solver and clue
  derivation (never a mocked verdict), and the review independently re-verified all three via
  mutation testing on a scratch copy (5/5 injected bugs caught by the existing suite).

## Review process note
Score 9.5/10, 0 critical/important findings, merged on cycle 1 — the fastest wave so far.
One scope question was raised and resolved during review, not silently: the card also edited
tests/test_cli.py (outside its predicted Touches) to extend CARD-001's ADR-0007 import-layering
guard from three special-case tests to one general `rank(imported) > rank(importer)` invariant.
The reviewer traced this back to a follow-up note CARD-001's own cycle-2 review had written on
this card *before implementation started*, explicitly offering that choice — ruled legitimate
scope growth (GROWN), not free-riding, and independently confirmed the rewritten guard is
strictly stronger than what it replaced (covers all 4 directional edges instead of 3).

## Convergence
- FR-007 ✓ (verified against the real pipeline, not just unit-level) — first user-facing
  generation capability, though still API-only: no export writer exists yet, so the feature
  is not yet usable end-to-end from a puzzle-in-hand perspective. UI gap tracked implicitly —
  CARD-007 (JSON export) is next.

## Known gaps / escalations
- none. Two forward notes left for later cards: CARD-006 must not conflate a future
  SolverTimeout with a uniqueness failure (already pinned by a test so this can't regress
  silently); CARD-010 should reuse the regenerate bound's constant rather than restating
  ADR-0002's "20" a second time, and should confirm the nested-loop budget semantics
  (the counter is not reset between calls to the retry primitive).

## Migrations
- none
