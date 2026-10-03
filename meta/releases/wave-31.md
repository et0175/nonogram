# Wave 31 — 2026-10-03   (tag: wave-31)

## Shipped
- CARD-160 (feature): the admin panel opens any puzzle in the puzzle player with its clues   score 8.5 (4 cycles; escalated at cycle 3, owner-directed fix)   FR-044
- CARD-161 (feature): marking — tools, click cycle, line drags, undo and redo   score 9.0   FR-044, EC-035
- CARD-162 (feature): live error count, solved state with name reveal, confirmed reset   score 9.5 (3 cycles; stalled at cycle 2, owner-directed test)   FR-044, EC-036, EC-037
- CARD-163 (feature): the player hides the picture name until solved   score 9.3   FR-044 AC-322/323

## Requirements closed
- FR-044 ≈ — every AC (AC-296..AC-323) and EC (EC-035..037) holds on main, verified goal-backward by browser probe; CON-021 ✓; ADR-0038 R1–R7 ✓, R8 ≈ (the repo has no CI config, so its "CI installs Chromium" clause cannot be checked)
- Architect delta of 2026-10-03: CON-002 superseded by CON-021; FR-044, US-028, CAP-007, ADR-0038 (DEC-040/041)

## Convergence
- ✅ converged — FR-044 satisfied with a UI surface (Solve in the puzzle detail modal → /puzzle/<id>/solve) · ≈ ADR-0038/R8 CI clause unverifiable (no CI)

## Known gaps / escalations
- CARD-160 escalated at cycle 3 (family regression: "what makes a value a board" — fix prompts drew declarations into hostile-value territory); CARD-162 stalled at cycle 2 on an untested header claim. Both resolved by owner-directed targeted fixes.
- Backlog: tier shown upper-case ("MEDIUM") only in the player; picture name present in the page source before solve (not visible); drag-axis rule and pointer-only cell marking unstated in FR-044; "25x15" vs "×" (owner call); no CI config to carry ADR-0038/R8's Chromium step.
- Owner visual checks: ~/Documents/nonogram-reviews/CARD-160/ … CARD-163/

## Migrations
- none
