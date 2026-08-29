# Wave 10 — 2026-08-29   (tag: wave-10)

Single-card wave: CARD-016 gives image mode its recovery path. Zero fix cycles —
cleared cycle 1 at 9.5/10, the review's deepest quantitative verification yet (mutation
tests, a 24,000-case property brute-force, an independent effectiveness sweep).

## Shipped
- CARD-016 (feature): Bounded pixel-nudge recovery loop for image mode — when an
  uploaded image's converted grid fails the uniqueness check, up to 5 pixel nudges
  are applied and re-checked before the run reports failure. A clean two-component
  split: the policy (when/how many times) lives in `orchestrator.py` as a third,
  independent `RetryCounter` bound to its own constant (`MAX_NUDGE_ATTEMPTS = 5`,
  deliberately never chained to the 20-attempt regenerate/resample family); the
  mechanism (which cell to flip) lives in `sourcing/image.py` as a stateless function
  that takes only the grid and an attempt number.   score 9.5 (cycle 1/3)   FR-013,
  INV-003, CON-005, POL-002, POL-003, ADR-0002, ADR-0004, ADR-0007

## Requirements closed
- FR-013 (bounded pixel-nudge recovery) — closes the second-to-last card of
  Increment 3. Only CARD-017 (nudge-count reporting) remains.

## Design decision worth recording, and independently stress-tested by the reviewer
Each nudge attempt flips the best-ranked N cells of the **original** converted grid,
never built incrementally on the previous attempt's result. The implementer argued
two benefits: no oscillation (nudging a nudged grid could undo an earlier flip), and
`puzzle.nudge.attempts` doubles as the exact cell-diff count CARD-017 will want to
report, with no second quantity to keep in sync. The reviewer treated the
non-monotonic-flip risk this claims to avoid as a real question rather than taking
the argument on faith: proved structurally that the ranking is independent of the
attempt count (so each attempt's flip set is a strict superset of the previous one's
by construction, not by luck), then verified it empirically with a 24,000-case
property brute-force across grid sizes 2×2 to 14×14 and attempt counts 1–7 — zero
violations. A mutation test confirmed the design is load-bearing: switching to the
incremental alternative broke 11 tests (and, worth recording honestly, incidentally
recovered one fixture the cumulative design doesn't — the argument for cumulative is
the bounded-drift guarantee and the free diff count, not raw recovery rate).

## Review process notes
- Cleared cycle 1 outright (9.5, zero Critical/Important findings) with unusually
  heavy independent verification for a LOW-risk/FAST-lane card: 5 mutation tests (all
  killed, working tree restored and re-verified byte-for-byte afterward), the
  24,000-case property check above, and an independent re-run of the implementer's
  claimed heuristic-effectiveness sweep (4 of 6 previously-failing fixture/size
  combinations now recover — reproduced exactly).
- G-4 (every nudged grid must be genuinely re-solved, never assumed unique because a
  nudge was applied) was verified mechanically rather than by trusting test names: a
  refactor left exactly one `solver.solve` call site in the entire package, shared
  unbranched by every mode including nudged candidates — grep-confirmed, not merely
  read.
- One flagged scope deviation (four pre-existing CARD-015 tests updated to reflect
  the intentional behavior change from "fail immediately" to "nudge, then fail at
  cap") was judged legitimate — no coverage was weakened, a moved assertion was
  traced to its new home, and one re-pinned real-image test was found to exactly
  duplicate a `test_nudge.py` case (harmless, flagged as a Minor rather than treated
  as a defect).

## Convergence
- FR-013 ✓ converged.

## Known gaps / escalations
- AC-037 — still tracked via `xfail`, CARD-018 unchanged, untouched this wave.
- Backlogged, not blocking: a large/hard image can now spend up to 6 solves against
  the shared 30s deadline instead of 1 (budget not breached, but could surface a
  generic timeout instead of this card's own retry advice on an unlucky input); a
  successful nudged run silently alters the user's picture with no visible signal
  until CARD-017 ships nudge-count reporting (correct per this card's own guardrail,
  but a real gap while the pair is half-landed — keep CARD-017 close behind); a
  duplicate test case and a docstring that overclaims exact-vs-"up to" flip counts.
- Two previously-backlogged items resolved this wave: the EXIF-orientation fix
  (landed directly on main between Wave 9 and Wave 10) and a forward-referenced test
  name in CARD-015's System contract (`TestNudge_ReportsFailureAtCap`), both now
  checked off.

## Migrations
- none
