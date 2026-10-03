# Wave 30 — 2026-10-03   (tag: wave-30)

## Shipped
- CARD-157 (tech-debt): read a book's puzzles in one query, not one session per puzzle   score 9.5   untraced (ADR-0033/R1) — 60-puzzle book: selection 123 → 4 sessions, status change 62 → 3, arrange click 245 → 9
- CARD-158 (feature): the book list and book page show what the book actually holds   score 9.5   FR-043, FR-030 — G-3 owner-confirmed
- CARD-159 (bug): book forms keep what you typed and say the right step   score 9.4   FR-038, FR-030 — G-3 owner check PENDING (merged on pipeline evidence by owner choice)

## Requirements closed
- FR-043 ✓ for the wave-30 surface (both files offered on /books and /book/<id>; lost-cover handling)
- FR-030 ≈, FR-038 ≈ — wave-30 parts hold in code; CARD-159's owner visual check pending
- Trace: evidence tests appended to FR-030, FR-038, FR-043; statuses stay `partial`

## Convergence
- ✅ converged — no unmet requirement, UI surface present for every user-facing FR · ≈ CARD-159 owner check pending
- Goal-check note (lean b): the behaviours wave 30 shipped (inches trims reachable, stored trim on the book page, prose/stepper agreement, create keeps input, lost-cover handling) live only in card ACs, not in requirements.yml — routed to the backlog for /forge:architect

## Known gaps / escalations
- No escalations this wave
- Owner check pending: ~/Documents/nonogram-reviews/CARD-159/
- Backlog: empty-book interior download inconsistent between /books and /book/<id>; Limits box "18.90 in" exceeds the 48 cm maximum (CARD-159 F-001); remaining N+1 loops in /books and the floor check (CARD-157 F-004)

## Migrations
- none
