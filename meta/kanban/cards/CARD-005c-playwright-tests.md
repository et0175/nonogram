# CARD-005c: Playwright Browser Automation Tests

**Status**: Pending  
**Priority**: High  
**Wave**: 2-3  
**Size**: Large (13 points)

## Description

Browser UI tests using Playwright to verify user workflows, form interactions, and visual state changes that unit/E2E tests miss.

## Acceptance Criteria

- [ ] AC-1: Playwright setup with fixture for Flask app
- [ ] AC-2: Dashboard page loads and shows correct UI elements
- [ ] AC-3: Batch creation form: fill, submit, redirect to status page
- [ ] AC-4: Batch status page: progress bar updates, completion shows message
- [ ] AC-5: Puzzle review list: filters work, puzzles render, approve/reject buttons clickable
- [ ] AC-6: Puzzle preview modal: opens on click, closes on ESC or close button
- [ ] AC-7: Bulk operations: checkboxes work, select all works, bulk buttons clickable
- [ ] AC-8: Book creation: form fills, puzzle selection modal works, PDF download starts
- [ ] AC-9: Form validation: error messages appear for invalid input
- [ ] AC-10: Mobile responsiveness: layout works on 375px width

## Test Requirements

**Playwright Tests** (to write):
- test_admin_dashboard.spec.ts (3+ tests)
- test_batch_creation.spec.ts (4+ tests)
- test_puzzle_review.spec.ts (6+ tests)
- test_book_management.spec.ts (4+ tests)
- test_form_validation.spec.ts (4+ tests)
- test_responsive.spec.ts (2+ tests)

## Dependencies

- Admin panel frontend (all CARD-004 tasks)
- Playwright library

## Worktree Notes

- Add `@playwright/test` to devDependencies
- Create tests/ui/ for Playwright tests
- Use `playwright.config.ts` for configuration
- Run with: `npx playwright test`
