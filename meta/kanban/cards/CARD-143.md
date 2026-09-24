# CARD-143: Type a puzzle's position in the arrange step, not only up and down

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/143-arrange-type-a-position
**Worktree:** —
**Source:** owner, 2026-09-23 ("sort puzzles inside the difficulty group after adding new puzzles, and manually change ordinal numbers, not only moving up-down")
**Idea:** —
**Wave:** 27
**Depends on:** CARD-140
**Touches:** src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/app.py, tests/test_book_arrange_position.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The arrange step moves a puzzle one place at a time (`move_up` / `move_down`,
app.py:3241-3248). After adding a batch of new puzzles — which land at the end of their own
level (CARD-126) — putting one near the front of a 50-puzzle level takes dozens of clicks.
The owner asked to type the position instead.

The ordering rule already supports it. `moved_within_level(puzzle_ids, puzzle_id, offset,
tier_of)` (book_plan.py:511) takes **any** integer offset, works on the grouped view, and
returns `None` when the move would leave the puzzle's level. So a typed position is the
existing operation with a computed offset — no new ordering logic, and INV-009 is enforced by
the same function that enforces it today.

1. **A position box per row.** Each puzzle shows its number within its level and accepts a
   new one. Submitting computes `offset = target - current` **inside the level** and calls
   `moved_within_level`; the up/down buttons stay exactly as they are.
2. **Number within the level, not the book.** The owner is sorting inside a difficulty group,
   and a book-wide ordinal would invite exactly the cross-level move INV-009 forbids. Label
   it so this is unambiguous on screen — position 1 means first among that level's puzzles.
3. **Refuse clearly, never silently clamp.** A position below 1 or above that level's count,
   a non-number, or an empty box is refused with a message naming the valid range, and the
   order is unchanged. Do not clamp to the nearest legal value: a typo that silently moves a
   puzzle somewhere else is worse than a refusal.
4. **A position that changes nothing is not an error.** Typing a puzzle's current position
   succeeds and leaves the order untouched.

Out of scope: drag-and-drop, sorting a level by any key (size, title, date), moving puzzles
between levels (INV-009 forbids it and CARD-126 settled it), and any change to where newly
added puzzles land.

## Acceptance criteria

- New: typing 1 against the last puzzle of a level moves it to the front of that level and
  leaves every other level untouched.
  test: TestArrangePosition_TypedPositionMovesWithinTheLevel
- New: a position above the level's count, below 1, or not a number is refused with the
  valid range named, and the stored order is unchanged.
  test: TestArrangePosition_OutOfRangeIsRefusedNotClamped
- New: typing a puzzle's current position succeeds and changes nothing.
  test: TestArrangePosition_NoOpPositionIsAccepted
- New: for any book and any legal position, the result is a permutation of the same ids,
  still grouped by tier.
  test: PropertyTest_ArrangePosition_AlwaysAPermutationGroupedByTier

## Guardrails

- G-1: INV-009 holds — the order stays grouped by tier and no typed position moves a puzzle
  across a level boundary. The move goes through `moved_within_level`; the route must not
  reorder ids itself.
- G-2: The up/down buttons and their tests are unchanged.
- G-3: Do not edit `src/nonogram/export/**` or `tests/fixtures/a4_golden/**` (CON-019).
- G-4: No schema change — the stored order is still a list of ids, not positions.

## Architecture context

- **FR:** FR-036 (arrangement)
- **INV:** INV-009 (grouped by tier, level-confined moves)
- **ADR:** ADR-0033, ADR-0019 (the adapter holds no domain logic)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner, 2026-09-23, after the first real arranging session on the deployed panel.
- [Why it waits for CARD-140] Both rewrite `book_arrange_puzzles.html` — CARD-140 replaces
  the page-break indicators, this card adds a control to every row. Running them together
  buys a conflict in one template for no gain.
- [Seam] `moved_within_level`'s docstring already says "Any integer works" for the offset, so
  this card should add no arithmetic beyond `target - current` within the level.
