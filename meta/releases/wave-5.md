# Wave 5 — 2026-08-28   (tag: wave-5)

## Shipped
- CARD-006 (feature): Cooperative generation deadline and SolverTimeout — a per-request wall-clock deadline (ADR-0001/ADR-0011), checked at every propagation sweep and every branch node, so generation never hangs (AC-038, independently reproduced at the real 30s budget: ~2ms overshoot).   score 9.2 (cycle 1/3)   FR-006, NFR-001, ADR-0011
- CARD-007 (feature): JSON export and the export-readiness gate — closes increment 1's walking skeleton: `nonogram generate ... --export json` writes a real file. Format registry derives the CLI's `--export` choices, so CARD-012/013/014 ship without touching the adapter.   score 9.4 (cycle 2/3)   FR-012 (partial), INV-002

## Requirements closed
- FR-006/NFR-001 (generation never hangs) — AC-038 established both structurally (every unbounded solver loop checked at its top) and empirically (reproduced against the real 30s budget by two independent reviewers).
- FR-012 partial/INV-002 (JSON export + the export-readiness gate) — verified against the real pipeline; manually confirmed a real file with correct shape.

## A genuine architectural finding, resolved mid-wave
CARD-006's own benchmark (AC-037: 20x20 generation p95 ≤5s) turned up a real gap, not a bug:
at 30-40% density the search's subtree-rejection isn't strong enough yet, and p95 is
unbounded (half the corpus hits the 30s hard cap) — while at ≥50% density the target is met
with large margin. ADR-0001 had explicitly named this exact scenario as grounds for revisiting
itself. Escalated to the user, who chose to **reaffirm the requirement rather than narrow it**:
ADR-0001 was revised (resolves DEC-019) on the strength of CARD-004's own finding that the
search's propagation is sound and the cost is specifically in how many wrong subtrees get
visited. The benchmark is now `xfail(strict=True)` — visible in every test run, not silently
green or permanently red — citing the revision and a new follow-up card, **CARD-018**
(strengthen the solver's search via lookahead/probing), which will remove the marker once the
gap closes.

## Review process notes
- CARD-005 and CARD-007's clean run (wave 4) was followed by a genuinely parallel pair this
  wave: CARD-006 and CARD-007 both predicted touching `orchestrator.py` (overlap 0.2, just
  under the 0.3 auto-serialize threshold). Run in parallel by choice — both rebases (CARD-006
  onto CARD-007's merge, then again onto the ADR-0001 revision commits) resolved cleanly with
  zero code conflicts; only the two-writers card-file pattern conflicted, as usual, and was
  resolved the same way each time.
- CARD-007 needed one fix cycle (an unhandled `OSError` on a bad `--out` path crashing with a
  raw traceback — first card to touch the filesystem, a real gap).
- CARD-006's review caught a genuine process gap (I-1: it was reviewed against a stale rebase,
  3 commits behind main, missing the very ADR revision its own xfail marker cited) — closed by
  re-rebasing before merge, not by a code fix.

## Convergence
- FR-006/NFR-001 ✓ converged for the timeout guarantee (AC-038). NFR-001's other half
  (AC-037, the p95 target) is a known, tracked, ⚑ NOT converged gap — see CARD-018.
- FR-012 partial ✓ (JSON only; CSV/PNG/SVG/PDF are increment-2 cards, waves 6-8).

## Known gaps / escalations
- AC-037 (NFR-001's p95 target at 20x20 mid/low density) — tracked via `xfail`, follow-up
  CARD-018 queued (unscheduled, depends on CARD-006, done).

## Migrations
- none
