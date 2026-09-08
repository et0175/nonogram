# CARD-004m: Book Management & Selection UI

**Status**: Pending  
**Priority**: High  
**Wave**: 2  
**Size**: Medium (8 points)

## Description

Book creation is minimal. Users need better controls to select puzzles for a book and manage book metadata before PDF generation.

## Acceptance Criteria

- [ ] AC-1: Book list shows all books with status, puzzle count, creation date
- [ ] AC-2: Create book page has fields: title, author, description, theme, target_audience
- [ ] AC-3: Puzzle selection shows two modes: "Auto-balanced" and "Manual" selection
- [ ] AC-4: Auto-balanced mode filters and selects N puzzles matching difficulty %
- [ ] AC-5: Manual mode shows puzzles with checkboxes, "Select" and "Clear" options
- [ ] AC-6: Book detail page shows metadata, puzzle list, difficulty breakdown chart
- [ ] AC-7: Can edit book metadata before PDF generation
- [ ] AC-8: Book status progression: draft → ready_for_pdf → published

## Test Requirements

**Unit Tests**:
- Book creation validation
- Puzzle selection logic (auto-balanced)
- Difficulty distribution calculation

**E2E Tests**:
- Create book with auto-balanced selection → correct puzzle count by difficulty
- Create book with manual selection → correct puzzles added
- Edit book metadata → changes persisted

**Playwright Tests**:
- Create book → form loads with fields
- Select "Auto-balanced", enter distribution → correct selection
- Manual selection → checkboxes work, count updates
- Edit book title → updates on detail page

## Dependencies

- Puzzle review (CARD-004e)
- Book manager service

## Worktree Notes

- Update book model with metadata fields
- Add book creation form with two selection modes
- Add auto-balanced selection algorithm
- Add book detail page with charts
- Add edit book endpoint and form
