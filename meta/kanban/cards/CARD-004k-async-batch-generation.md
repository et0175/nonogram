# CARD-004k: Async Batch Generation with Job Queue

**Status**: Pending  
**Priority**: Critical  
**Wave**: 2  
**Size**: Large (13 points)

## Description

Currently, batch generation is synchronous and blocks the HTTP request. Generating 200 puzzles takes 20-30 seconds locally, which times out on Render's free tier. Implement async job queue so batch generation runs in the background while the user sees immediate feedback.

## Acceptance Criteria

- [ ] AC-1: POST /batch/create returns immediately with {batch_id, status: "queued"}
- [ ] AC-2: Batch job runs in background (Python Queue or similar)
- [ ] AC-3: Job status page polls `/api/batch/<id>/status` and updates progress bar
- [ ] AC-4: Progress updates show current count and percentage
- [ ] AC-5: Batch completion shows total puzzles generated and database stored count
- [ ] AC-6: If job fails, error message and "Retry" button shown
- [ ] AC-7: Can generate multiple batches in parallel
- [ ] AC-8: Job metadata persists (start_time, end_time, error_message)

## Test Requirements

**Unit Tests**:
- Job queue enqueue/dequeue logic
- Job status tracking
- Error handling in job worker

**E2E Tests**:
- Create batch → returns batch_id immediately
- Poll batch status → progress increases
- Batch completes → puzzles in database
- Multiple batches → both process correctly

**Playwright Tests**:
- Create batch → status page loads immediately
- Progress bar updates as generation proceeds
- Completed batch shows "100% Complete"
- Can create new batch while first is generating

## Dependencies

- Batch model updated with job queue status
- Redis or Python Queue for job management

## Worktree Notes

- Implement job queue (consider: Redis/RQ, Celery, or simple threading)
- Create job worker process
- Add polling mechanism to status page
- Update batch_generator to queue jobs instead of running synchronously
- Add error recovery (retry mechanism)
