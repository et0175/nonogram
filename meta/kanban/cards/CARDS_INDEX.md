# Admin Panel Kanban Cards Index

All card details are defined in the ADMIN_PANEL_ROADMAP.md. Individual cards below:

## Wave 1: Core Features & Testing (58 points)

### CARD-004h: Batch History & Tracking
- **Size**: 8pt | **Priority**: High
- **What**: View past batches with metadata, retry similar batches
- **Why**: Users can't see what was generated before, hard to track progress
- **AC**: Batches table stores batch_id, status, count, sizes, theme, dates; API `/api/batches`; list page with filtering
- **Tests**: Unit (model), E2E (generate batch, verify in history), Playwright (click history menu, filter by status)

### CARD-004i: Puzzle Preview Modal  
- **Size**: 8pt | **Priority**: High
- **What**: Modal showing puzzle grid, clues, and metrics before approval
- **Why**: Users can't judge quality without seeing the puzzle
- **AC**: Click puzzle → modal opens; grid displays; row/col clues shown; approve/reject from modal; ESC closes
- **Tests**: Unit (grid rendering), E2E (preview opens), Playwright (modal interactions, approve from modal)

### CARD-004j: Bulk Puzzle Operations
- **Size**: 8pt | **Priority**: High
- **What**: Select multiple puzzles, approve/reject all at once
- **Why**: Approving 200 puzzles is 200 clicks; need bulk operations
- **AC**: Checkboxes, "Select All", action bar, "Approve/Reject Selected", works with filters
- **Tests**: Unit (bulk update service), E2E (select and bulk update), Playwright (checkbox UI, bulk buttons)

### CARD-005b: Comprehensive Unit Tests
- **Size**: 13pt | **Priority**: High
- **What**: Unit tests for all admin services (batch, puzzle review, book, validators)
- **Why**: 80%+ coverage ensures correctness of business logic
- **AC**: >80% coverage; all service methods tested; edge cases covered
- **Tests**: Write test_batch_service.py, test_puzzle_review_service.py, test_book_manager.py, test_validators.py

### CARD-005d: Comprehensive E2E Tests
- **Size**: 13pt | **Priority**: High
- **What**: E2E tests for complete workflows (batch→review→book→PDF)
- **Why**: Verify workflows work end-to-end, not just individual components
- **AC**: 30+ tests; all workflows covered; performance benchmarks; marked with @pytest.mark
- **Tests**: Expand test_admin_panel_e2e.py with workflow tests, performance tests, concurrency tests

### CARD-005e: Admin Testing Guide & Docs
- **Size**: 8pt | **Priority**: High
- **What**: Documentation for testing (ADMIN_TESTING_PLAN.md, ADMIN_FINDINGS.md, TESTING_WORKFLOW.md)
- **Status**: ✓ In Progress (created: ADMIN_TESTING_PLAN.md, ADMIN_FINDINGS.md, TESTING_WORKFLOW.md)
- **Still Needed**: pytest.ini, tests/README.md, CI/CD integration

---

## Wave 2: Async & Error Handling (34 points)

### CARD-004k: Async Batch Generation with Job Queue
- **Size**: 13pt | **Priority**: Critical
- **What**: Batch generation runs in background, returns immediately with job ID
- **Why**: Large batches timeout on Render; need async + job queue
- **AC**: POST /batch returns immediately; job runs in background; progress polling; completion/error handling

### CARD-004l: Error Recovery & Batch Retry
- **Size**: 5pt | **Priority**: High
- **What**: Failed batches show error message and "Retry" button
- **Why**: Failed batches stuck in ERROR state with no recovery
- **AC**: Error message shown; "Retry" button retries with same params; "Cancel" available

### CARD-004m: Book Management & Selection UI
- **Size**: 8pt | **Priority**: High
- **What**: Better book creation with manual/auto-balanced puzzle selection
- **Why**: Current UI minimal; users need better controls
- **AC**: Create book form; two selection modes (auto, manual); preview selection; edit metadata

### CARD-004n: PDF Generation & Download
- **Size**: 8pt | **Priority**: High
- **What**: Robust PDF generation that works for large books
- **Why**: PDF may fail or timeout for 100+ puzzles
- **AC**: PDF downloads with correct filename; works for 200+ puzzles; metadata set; error handling

---

## Wave 3: Polish & Production (5+ points)

### CARD-004o: Form Validation & Input Constraints
- **Size**: 5pt | **Priority**: Medium
- **What**: Form validation with clear error messages
- **Why**: Invalid inputs cause silent failures
- **AC**: Client + server validation; error messages shown; submit disabled until valid

### CARD-004g: Admin Authentication & Access Control
- **Size**: TBD | **Priority**: High
- **What**: Restrict admin panel to authorized users
- **Why**: Currently no auth; anyone can access
- **AC**: Login required; role-based access; sessions

---

## How to Use This

1. Pick a card (e.g., CARD-004h)
2. Read the details above
3. Reference full AC in ADMIN_PANEL_ROADMAP.md
4. I write tests for the card
5. You test locally and document findings
6. We iterate until card complete

All card descriptions are summaries. Full details (Test Requirements, Dependencies, Worktree Notes) are in ADMIN_PANEL_ROADMAP.md.

---

See: `/meta/kanban/ADMIN_PANEL_ROADMAP.md` for complete roadmap with all AC, test requirements, dependencies
