# Wave 29 — 2026-10-02   (tag: wave-29)

## Shipped
- CARD-153 (bug): Finalise doesn't hide a broken page plan behind "About N"   score 9.5 (3 cycles; escalated at cycle 2, owner-directed fix)   FR-030, FR-040, FR-042, EC-034
- CARD-154 (bug): Print setup saves the plan and the trim together, and refuses "nan"   score 9.5   FR-030, FR-031, CON-018
- CARD-155 (tech-debt): one difficulty classifier — retire the prototype's 30/70 tiers   score 9.5   ADR-0031/R1
- CARD-156 (tech-debt): the db_session fixture stops dropping tables other tests are using   score 9.0   test infrastructure

## Requirements closed
- FR-031 ✓ (goal-backward, every AC/EC)
- FR-030 ≈, FR-040 ≈, FR-042 ≈ — every AC/EC holds in code; criteria measured on printed paper await the owner's wave-25 / wave-27 checkpoints
- Trace: evidence tests appended to FR-030, FR-031, FR-040, FR-042; all stay `partial` (open cards still list FR-030; owner checkpoints pending)

## Convergence
- ✅ converged — no unmet requirement, no UI gap (Finalise and Print setup are the shipped screens) · ≈ owner-measured print criteria (wave-25: 4.97 mm / 7.5 mm proof cells, strokes; wave-27: 7.39 mm pair, 5.0 mm answer, real-book pages)

## Known gaps / escalations
- CARD-153 escalated once (review stalled at 8.0 on F-007, a defect its own cycle-1 fix introduced); resumed by owner decision and passed at 9.5
- Goal-check observation: `validate_margins` does not enforce the 0.635 cm minimum (unreachable today — no margin field on Print setup); captured to backlog
- Follow-ups captured to backlog: CARD-153 F-003/F-006/F-009/F-010/F-011, CARD-155 stale enum note, CARD-156 F-005/F-006/F-007
- Owner visual checks: ~/Documents/nonogram-reviews/CARD-153/ (renders 3 and 7), CARD-154/ (nan before/after)

## Migrations
- none (the test fixture now builds nonogram_test's schema from alembic head once per session)
