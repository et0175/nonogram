# CARD-004o: Form Validation & Input Constraints

**Status**: Pending  
**Priority**: Medium  
**Wave**: 3  
**Size**: Small (5 points)

## Description

Forms lack proper validation. Users can submit invalid inputs which cause silent failures. Add comprehensive form validation with clear error messages.

## Acceptance Criteria

- [ ] AC-1: Batch count must be 50-200 (validation before submit)
- [ ] AC-2: Grid sizes must be 10-30 (validation before submit)
- [ ] AC-3: No duplicate sizes in batch (e.g., "10,10,20" rejected)
- [ ] AC-4: Difficulty percentages sum to 100% (if percentages used)
- [ ] AC-5: All required fields must be filled
- [ ] AC-6: Clear error messages shown in red near field
- [ ] AC-7: Submit button disabled until form valid
- [ ] AC-8: Client-side validation (before submit) + server-side validation (for security)

## Test Requirements

**Unit Tests**:
- Validation functions for each field type
- Range checking, sum checking, required field checking

**E2E Tests**:
- Submit form with out-of-range values → validation error
- Submit incomplete form → error message

**Playwright Tests**:
- Fill in invalid batch count → error message appears
- Fix error → error disappears
- Fill in all fields correctly → submit enabled

## Dependencies

- Forms (batch create, book create)

## Worktree Notes

- Add validation functions to form handlers
- Add JavaScript validation (client-side)
- Display error messages in templates
- Add server-side validation for security
