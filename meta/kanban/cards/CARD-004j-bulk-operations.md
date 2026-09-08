# CARD-004j: Bulk Puzzle Operations (Approve/Reject Multiple)

**Status**: Pending  
**Priority**: High  
**Wave**: 1  
**Size**: Medium (8 points)

## Description

Currently, approving or rejecting puzzles requires one click per puzzle. With 200+ puzzles, this means 200+ clicks. Add bulk operations so users can select multiple puzzles and approve/reject them all at once.

## Acceptance Criteria

- [ ] AC-1: Checkbox appears next to each puzzle in list
- [ ] AC-2: "Select All" checkbox in header selects all puzzles on page
- [ ] AC-3: "Select All Filtered" option selects all matching current filters
- [ ] AC-4: Action bar appears when ≥1 puzzle selected
- [ ] AC-5: Action bar has "Approve Selected", "Reject Selected", "Clear" buttons
- [ ] AC-6: Bulk approve updates all selected puzzles to "approved" status
- [ ] AC-7: Bulk reject updates all selected puzzles to "rejected" status
- [ ] AC-8: Selected count shown in action bar ("3 selected")
- [ ] AC-9: Bulk operations work with current filters applied
- [ ] AC-10: Success message shows "Approved 50 puzzles"

## Test Requirements

**Unit Tests**:
- Bulk update logic in service
- Filter application to bulk operations

**E2E Tests**:
- Select puzzle, click approve → status changes
- Select multiple, bulk approve → all status change
- Select all filtered, bulk reject → all status change

**Playwright Tests**:
- Click checkbox → puzzle selected (visual)
- Click "Select All" → all on page selected
- Select 5 puzzles, click "Approve Selected" → all 5 approved
- Apply filter, "Select All Filtered" → all matching selected
- Bulk reject with selection → all rejected

## Dependencies

- Puzzle review page (CARD-004e)
- Filter functionality (existing)

## Worktree Notes

- Add checkbox UI to puzzle list
- Add action bar (sticky or float)
- Add JavaScript selection logic
- Add API endpoint `/api/puzzles/bulk-action` with payload {action: approve|reject, puzzle_ids: [...]}
- Add service method for bulk operations
