# Wave 35 — 2026-10-06   (tag: wave-35)

_Solver test-doc items 1, 3, 5 (CARD-185, 187, 189) and the owner's admin-panel amendments (CARD-190..192)._

## Shipped
- CARD-185 (feature): the puzzle player reopens a puzzle in the state you left it, in this browser only   score 9.5   FR-044 (CON-021 amended)
- CARD-187 (feature): "Progress: N%" next to the error counter — correct cells over all cells, 100 only when solved   score 9.0   FR-044
- CARD-189 (feature): a click follows the selected brush; repeat clicks go on along the brush's sequence   score 9.0   FR-044 (AC-303/304 superseded)
- CARD-190 (feature): puzzle review's size filter goes by the longest side (API too)   score 9.5
- CARD-191 (feature): book arrangement — "Sort by size" orders each level smallest first and saves it   score 9.5
- CARD-192 (feature): arrangement shows one plan band at a time, with what's left or over   score 9.2

## Requirements closed
- Goal-backward per card: card-local ACs ✓ on main (owner render sign-offs recorded as pending: 185, 187, 189, 190, 191, 192)
- FR-044 model caught up in the 2026-10-06 architect delta (24a1e63): AC-327..365, EC-042..047; CON-020/021; ADR-0038/R8

## Convergence
- ✅ code converged; model converged for the wave-35 player and admin changes
- Smoke: full suite on main 6618 passed, 9 skipped, exit 0 (770 s)

## Known gaps / escalations
- CARD-187 ran through a fix round and a confirmation review (cycle 1 score 8 → 9); CARD-187 merge gate needed its AC/EC note written first
- CARD-192 and CARD-187 were interrupted by the Sonnet 5 weekly / spend limit; resumed after the reset from their committed state
- Owner items: renders for 185, 187, 189, 190, 191, 192 (~/Documents/nonogram-reviews/CARD-NNN/)
- Follow-ups in backlog: CARD-185 setBoard-history wording (AC-365); CARD-189 help line vs first-click rule; CARD-190 _side_bounds edge tests; CARD-191 INV-009 "move" → "reorder"; CARD-192 commit trailer (Sonnet 5 on the implementation commit, not rewritten)
- Retro for wave 35 still to run

## Migrations
- none
