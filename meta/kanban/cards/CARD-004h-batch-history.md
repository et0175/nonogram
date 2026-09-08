# CARD-004h: Batch History & Tracking

**Status**: Pending  
**Priority**: High  
**Wave**: 1  
**Size**: Medium (8 points)

## Description

Currently, batch generation records don't persist. Users can't see what batches were generated in previous sessions or check historical metrics. This makes it hard to track progress and reproduce batches.

Add batch history so users can:
- View all past batches (list with pagination)
- See batch details (date, count, sizes, theme, completion time)
- Filter by status (pending, complete, error)
- Re-generate similar batches

## Acceptance Criteria

- [ ] AC-1: Batches table in database stores: batch_id, status, count, sizes, theme, created_at, completed_at, puzzle_count, error_message
- [ ] AC-2: Batch list page shows all batches with date, status, puzzle count, completion time
- [ ] AC-3: Batch detail page shows full metadata and list of puzzles in batch
- [ ] AC-4: Filter by status (pending/complete/error) works on batch list
- [ ] AC-5: Sorting by date (newest first) works
- [ ] AC-6: API endpoint `/api/batches` returns list with pagination
- [ ] AC-7: Error batches show error_message and "Retry" button

## Test Requirements

**Unit Tests**:
- Batch model serialization
- Filter by status logic

**E2E Tests**:
- Generate batch, verify it appears in history
- Filter history by status
- View batch details

**Playwright Tests**:
- Click "Batch History" menu
- See list of past batches
- Filter by status
- Click batch to view details

## Dependencies

- Database migration for batches table
- API endpoints implemented (CARD-004b)

## Worktree Notes

- Add `created_at`, `completed_at`, `error_message` fields to batch job model
- Create migration file
- Add batch list and detail routes in Flask
- Update templates
