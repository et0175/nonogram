# CARD-004l: Error Recovery & Batch Retry

**Status**: Pending  
**Priority**: High  
**Wave**: 2  
**Size**: Small (5 points)

## Description

When batch generation fails (database error, timeout, etc.), the batch stays in ERROR state with no recovery option. Users must manually start over. Add error recovery so users can see what went wrong and retry.

## Acceptance Criteria

- [ ] AC-1: Failed batch shows error_message in database
- [ ] AC-2: Error message displayed on status page (red alert)
- [ ] AC-3: "Retry" button available on error batch (uses same count/sizes/theme)
- [ ] AC-4: "Cancel" button available (marks batch as cancelled, clears queued job)
- [ ] AC-5: Retry creates new batch_id (not reusing old one)
- [ ] AC-6: Cancelled batch shown in history with status="cancelled"
- [ ] AC-7: Error type categorized (timeout, db_error, generation_error) for better UX

## Test Requirements

**Unit Tests**:
- Error handling in batch service
- Error message storage and retrieval

**E2E Tests**:
- Simulate batch failure → error shown
- Retry button → new batch created
- Cancel button → batch marked cancelled

**Playwright Tests**:
- Generate batch that fails → error message visible
- Click "Retry" → new batch starts
- Click "Cancel" → batch cancelled

## Dependencies

- Batch history (CARD-004h)
- Async batch generation (CARD-004k) - recommended but not required

## Worktree Notes

- Add error_message field to batch table
- Add error handling in batch generator
- Add retry and cancel routes
- Update batch status page template with error UI
- Add error classification logic
