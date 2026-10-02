# Wave 28 — 2026-10-02   (tag: wave-28)

## Shipped
- CARD-150 (tech-debt): the local launcher refuses a database it cannot use   score 8.0   untraced
- CARD-151 (bug): the launcher's database check understands the URLs the panel builds   score 9.0 (3 cycles; escalated at cycle 2 on a test gap, owner-directed fix)   untraced
- CARD-152 (bug): the setup and test-runner scripts check the database they will use   score 9.5   untraced

## Requirements closed
- none — all three cards are untraced operational fixes (FR —); no goal-backward check applies

## Convergence
- ✅ converged — nothing traced to verify; wave smoke test green apart from the 2 known baseline failures

## Known gaps / escalations
- CARD-151 escalated once (review stalled at 8.0, one confirmed test gap F-006); resumed by owner decision and passed at 9.0
- Backlog: diagnose_postgres.sh still hardcodes nonogram_poc; Docker/Compose branches check by name only (CARD-150 F-005); run_admin_tests.sh default nonogram_poc is refused by pytest's database guard (owner decision)
- Owner to confirm: run_admin_tests.sh now requires a reachable database for every test type

## Migrations
- none
