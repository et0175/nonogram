# CARD-004i: Puzzle Preview Modal

**Status**: Pending  
**Priority**: High  
**Wave**: 1  
**Size**: Medium (8 points)

## Description

When reviewing puzzles, users can't see what a puzzle looks like before approving/rejecting it. They only see metrics (difficulty, quality score). Add a preview modal so users can see the puzzle grid and clues before making decisions.

## Acceptance Criteria

- [ ] AC-1: Clicking on a puzzle in review list opens modal with preview
- [ ] AC-2: Modal displays puzzle grid (filled/empty cells)
- [ ] AC-3: Row clues and column clues displayed clearly
- [ ] AC-4: Grid size and difficulty metrics shown in modal
- [ ] AC-5: Modal has "Approve", "Reject", "Close" buttons
- [ ] AC-6: Approve/Reject from modal updates puzzle status immediately
- [ ] AC-7: Modal closes without action when "Close" or ESC is pressed
- [ ] AC-8: Preview works for all grid sizes (10×10 to 30×30)

## Test Requirements

**Unit Tests**:
- Grid rendering logic (convert grid to display format)
- Clue formatting for display

**E2E Tests**:
- Generate puzzle, open preview, verify grid displays
- Approve puzzle from modal
- Reject puzzle from modal

**Playwright Tests**:
- Click puzzle in list → modal opens
- Verify grid and clues visible
- Click "Approve" in modal → status changes
- Click "Reject" in modal → status changes
- Click close → modal closes
- Press ESC → modal closes

## Dependencies

- Puzzle data model must include grid and clues
- Puzzle review page exists (CARD-004e)

## Worktree Notes

- Add grid rendering function (SVG or Canvas)
- Create modal template with preview
- Add JavaScript event handlers for modal
- Add CSS for responsive grid display
