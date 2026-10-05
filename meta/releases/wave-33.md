# Wave 33 — 2026-10-05   (tag: wave-33)

_Roadmap wave 1 of the 2026-10-04 re-plan (meta/kanban/roadmap.md), carded as CARD-169..CARD-176._

## Shipped
- CARD-169 (feature): the Finalise guide preview shows "How to Solve Nonograms" and its worked example, read from the printing code   score 9.5   FR-041
- CARD-170 (tech-debt): confirmed — each "Puzzle N · Tier" band prints once; the extra draw lands on a discarded scratch page. Pixel + recorder tests added   score 9.5   FR-033/FR-040
- CARD-171 (feature): GET Finalise names a page-plan failure; every flashed Finalise/PDF-download error is logged with its traceback   score 10.0
- CARD-172 (feature): proof pages render on square and landscape trims (8.25×8.25, 8.5×8.5, 8.25×6, 11×8.5); portrait proofs byte-identical   score 9.2   FR-033
- CARD-173 (feature): an unreadable stored print setup is said once, names Print setup, and offers no override that cannot work   score 9.5   FR-031
- CARD-174 (feature): inch trim refusals speak inches; the Limits box reads the same source (18.89 in)   score 9.5   FR-038
- CARD-175 (feature): /books rows fold off-plan hints behind a one-line summary on phones (668 → 169 px)   score 9.6   FR-039
- CARD-176 (tech-debt): a malformed DATABASE_URL's error never echoes text that could hold the password   score 9.5   CARD-148 EC-1

## Requirements closed
- Goal-backward on main: FR-041, FR-043, FR-030, FR-033, FR-040, FR-042, FR-031, FR-038, FR-039, NFR-008, CON-009/016/018/019, CARD-148 EC-1 ✓, and every card-local AC ✓ (CARD-172 AC-7 and CARD-170 AC-5 are recorded owner/review acts)
- CON-020 ≈ review-lens only (the proof note's 10 pt floor is test-backed by CARD-172 AC-3)
- Requirement deltas this wave: none (card-local ACs; CARD-172 AC-2 amended by the owner — foot first wherever it fits)

## Convergence
- ✅ converged — every target holds on main, UI surfaces present
- Wave smoke: full suite on main 6270 passed, 9 skipped, exit 0 (596 s)

## Known gaps / escalations
- CARD-172 escalated (decompose: AC-2 contradicted the card's own placement order) → owner route (a), no code change
- CARD-170 escalated (review stalled at 8.5 on test-comment wording) → owner-chosen targeted fix + 1 review → 9.5
- Owner items: look at ~/Documents/nonogram-reviews/CARD-169/finalise-guide-preview.png (merged "check later"); CARD-174's inch minimum says "on both sides" vs cm's "in both dimensions"; IDEA-088 (?status=all) still undecided; IDEA-080 Render dashboard rows
- Known limit (CARD-176): a password of plain letters/digits glued to the scheme (`postgresqlhunter2://`) is still echoed as the scheme — documented and tested as a limit
- Follow-ups captured to backlog: Finalise flash echoes str(e); lone puzzles render a discarded solved page; CARD-174 F-003 (48.0 cm reopens as 18.90 in); minor review findings per card

## Migrations
- none
