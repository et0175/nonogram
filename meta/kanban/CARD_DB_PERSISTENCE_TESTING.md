# Kanban Cards: Database Persistence Implementation Testing & Deployment

**Milestone:** Database Persistence for Admin Panel  
**Status:** Implementation Complete (Stages 1-5) → Ready for Verification & Deployment  
**Created:** 2026-09-09

---

## Increment 1: Local Verification (docker-compose)

### CARD-401: Set up local Postgres & verify migrations

**Type:** Testing  
**Effort:** 30 min  
**Priority:** P0 (blocker for all DB testing)

**Description:**
Verify that local docker-compose Postgres setup and migration `002` run cleanly.

**Checklist:**
- [ ] `docker compose up -d` — Postgres starts on localhost:5432
- [ ] `alembic upgrade head` — migrations apply without errors
- [ ] Verify tables exist: `\dt` shows `batches`, `puzzles`, `users`, `books`
- [ ] `psql nonogram_dev -c "SELECT COUNT(*) FROM batches"` — returns 0 (empty)
- [ ] Log files show no errors or warnings

**Checkpoint:** Postgres running locally with schema v002, no errors in alembic output

**Acceptance Criteria:**
- Postgres container healthy
- Both dev and test databases created
- All tables created (no dangling errors)
- Can connect and query

**Touches:** docker-compose.yml, migrations/versions/002_add_batches_and_puzzles.py

---

### CARD-402: Run full test suite (legacy mode)

**Type:** Testing  
**Effort:** 15 min  
**Priority:** P0 (verify no regressions)

**Description:**
Confirm that all existing tests pass with the new DB-backed app (legacy in-memory mode still works).

**Checklist:**
- [ ] `pytest tests/test_puzzle_review.py -v` — 21/21 pass
- [ ] `pytest tests/test_batch_generator.py -v` — 16/16 pass
- [ ] `pytest tests/test_cli.py -k "import_rule or adapter_allowlist" -v` — 10/10 pass (ADR-0007 guard)
- [ ] No new warnings or errors introduced
- [ ] All tests pass <5 min total

**Checkpoint:** All legacy tests green, no regressions

**Acceptance Criteria:**
- test_puzzle_review.py: 21 pass
- test_batch_generator.py: 16 pass
- ADR-0007 guard: 10 pass
- Total: ≥47 tests passing

**Touches:** tests/conftest.py, src/nonogram/admin/*.py

---

### CARD-403: Run DB smoke tests (local Postgres)

**Type:** Testing  
**Effort:** 15 min  
**Priority:** P0 (first DB test run)

**Description:**
Run the DB-dependent smoke tests now that Postgres is running locally. Tests will auto-skip if DB unavailable, so this verifies the skip logic and basic DB connectivity.

**Checklist:**
- [ ] `pytest tests/test_db_e2e_smoke.py -v` — at least 5 tests run (not skipped)
- [ ] At least 2 tests pass (app instantiation + db_session fixture)
- [ ] No database errors in output
- [ ] Table truncation works (fixtures clean up after each test)

**Checkpoint:** DB smoke tests execute against real Postgres, basic DB ops work

**Acceptance Criteria:**
- Smoke tests execute (not skipped)
- At least 2 tests pass
- No SQL errors
- Tables truncate correctly after each test

**Touches:** tests/test_db_e2e_smoke.py, tests/conftest.py

---

## Increment 2: Local End-to-End Workflow Testing

### CARD-404: Test batch creation → generation → approval workflow

**Type:** Testing / Validation  
**Effort:** 45 min  
**Priority:** P0 (critical path)

**Description:**
Walk through the complete batch workflow locally using the admin panel UI with Postgres persistence enabled. Verify that all state persists across steps and survives a server restart.

**Setup:**
- `docker compose up -d` (Postgres running)
- `export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nonogram_dev`
- `alembic upgrade head`
- `flask --app src.nonogram.admin.app run` (admin panel starts)

**Checklist:**
- [ ] Navigate to `/batch/create` — page loads
- [ ] Upload 3-5 test images (PNG/JPG)
- [ ] Set Quality Score to 80, Size to Medium
- [ ] Click "Next: Preview Images"
- [ ] Preview page shows cropped images
- [ ] Click "Next: Generate Puzzles"
- [ ] Generation proceeds to completion
- [ ] "Generated Puzzles" page shows:
  - [ ] List of generated puzzles
  - [ ] Quality filter explanation (count of filtered-out puzzles)
  - [ ] SVG download button works (file downloads)
  - [ ] PDF download button works (file downloads)
- [ ] Approve 2-3 puzzles, reject 1-2
- [ ] Restart Flask process (`Ctrl+C`, `flask run`)
- [ ] Check `/puzzles` page — all puzzles still there with correct statuses
- [ ] Check batch detail view — status/counts accurate
- [ ] Create another batch — uses new batch ID (Postgres sequence works)

**Checkpoint:** Full workflow executed, restart recovery confirmed, multiple batches coexist in DB

**Acceptance Criteria:**
- All workflow steps complete without 500 errors
- Images crop and preview successfully
- Batch generates at least 1 puzzle
- Quality filter explanation shows
- Download buttons work (files are valid)
- Approve/reject states persist to DB
- Server restart does NOT lose data
- Multiple batches queryable simultaneously

**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/*.py, templates/

---

### CARD-405: Test crash recovery (mid-batch restart)

**Type:** Testing / Validation  
**Effort:** 30 min  
**Priority:** P1 (important for robustness)

**Description:**
Verify that if the admin panel is killed mid-batch-generation, the batch state is left in `status="generating"` with an accurate `completed_count`, and the puzzles generated so far are queryable.

**Setup:**
- Docker Postgres running
- Fresh batch, e.g. with 10 images to generate

**Procedure:**
1. Start batch generation
2. Wait 5-10 seconds (let a few puzzles generate)
3. Kill the Flask process (Ctrl+C)
4. Query Postgres directly:
   - `SELECT * FROM batches WHERE status='generating'` — expect 1 row
   - Check `completed_count` — expect > 0 and < total_count
5. Restart Flask
6. Check `/puzzles` page — should show the puzzles that were generated before crash
7. Check batch status in UI — should show interrupted status (if UI supports it)

**Checkpoint:** Crash recovery confirmed — mid-batch state persists, puzzles queryable

**Acceptance Criteria:**
- Batch row has `status='generating'` after crash
- `completed_count` is accurate (matches number of Puzzle rows)
- Already-generated Puzzle rows are present and queryable
- Restart doesn't wipe the partial batch
- UI can display the interrupted batch

**Touches:** src/nonogram/admin/batch_generator.py (crash-recovery logic)

---

## Increment 3: User Acceptance Testing (Anna)

### CARD-406: UAT — Simple batch (1-2 images)

**Type:** Validation / UAT  
**Effort:** 20 min  
**Priority:** P1 (basic functionality)

**Assignee:** Anna (QA)  
**Reference:** docs/TEST_BATCH_GENERATION_UA.md (Сценарій 1)

**Description:**
Follow the Ukrainian testing guide (Сценарій 1: Мінімальний батч) to create and verify a single-image batch.

**Checklist:**
- [ ] Upload 1 PNG or JPG image
- [ ] Leave Quality Score at default (80)
- [ ] Leave Size at default (Medium)
- [ ] Complete workflow to Generated Puzzles page
- [ ] Verify 1 puzzle appears (or 0 if quality rejected it)
- [ ] Download SVG — file opens correctly
- [ ] Download PDF — file opens correctly, shows puzzle + solution

**Acceptance Criteria:**
- Batch processes without errors
- Files download and are valid
- User-facing messages are clear

**Touches:** Admin panel UI, download endpoints

---

### CARD-407: UAT — Batch with quality filtering

**Type:** Validation / UAT  
**Effort:** 25 min  
**Priority:** P1 (critical for filtering)

**Assignee:** Anna (QA)  
**Reference:** docs/TEST_BATCH_GENERATION_UA.md (Сценарій 2)

**Description:**
Verify that the quality filter works — upload 10+ images, set Quality Score to 80, and confirm the "filtered out" message appears with the correct count.

**Checklist:**
- [ ] Upload 10-15 images (variety of quality)
- [ ] Set Quality Score to 80
- [ ] Complete generation
- [ ] On "Generated Puzzles" page, verify:
  - [ ] Message shows: "Generated X puzzle(s) from 10 image(s)"
  - [ ] Message shows: "Y filtered out by quality threshold" (where Y > 0)
  - [ ] X + Y = 10 (or close to it)
- [ ] Lowering Quality Score to 0 generates more puzzles

**Acceptance Criteria:**
- Filter message appears and is accurate
- Count math is correct (generated + filtered = total)
- Lower threshold allows more puzzles

**Touches:** src/nonogram/admin/batch_generator.py, templates/generated_puzzles.html

---

### CARD-408: UAT — Size configuration persistence

**Type:** Validation / UAT  
**Effort:** 20 min  
**Priority:** P1 (critical for UX)

**Assignee:** Anna (QA)  
**Reference:** docs/TEST_BATCH_GENERATION_UA.md (Сценарій 3)

**Description:**
Verify that when the user changes puzzle sizes on the Preview page, those changes are saved and used during generation.

**Checklist:**
- [ ] Upload 3-5 images
- [ ] On Preview page, change sizes for individual images:
  - [ ] Image 1: Fixed Size = 15
  - [ ] Image 2: Minimum Size (auto)
  - [ ] Image 3: Maximum Size (auto)
- [ ] Complete generation
- [ ] On Generated Puzzles page, verify:
  - [ ] Image 1's puzzle is 15×15
  - [ ] Image 2's puzzle matches predicted min size
  - [ ] Image 3's puzzle is large

**Acceptance Criteria:**
- Size changes are stored and applied
- Predicted sizes match actual generated sizes
- No "size not saved" issues

**Touches:** src/nonogram/admin/image_preview.py, form submission logic

---

### CARD-409: UAT — Multiple batch operations

**Type:** Validation / UAT  
**Effort:** 30 min  
**Priority:** P2 (concurrent users)

**Assignee:** Anna (QA)

**Description:**
Create multiple batches in sequence (or simulated concurrency) and verify they don't interfere — each has its own ID, state, and puzzles.

**Checklist:**
- [ ] Create Batch 1 (3 images, Medium size)
- [ ] Generate and approve/reject puzzles
- [ ] Create Batch 2 (different images, Large size)
- [ ] Generate and approve/reject puzzles
- [ ] Navigate to `/puzzles` — both batches' puzzles visible
- [ ] Click batch detail view — filters by batch correctly
- [ ] Batch IDs are unique UUIDs (not sequential)

**Acceptance Criteria:**
- Multiple batches coexist without ID collisions
- Puzzle filtering by batch works
- No cross-batch contamination

**Touches:** Batch ID generation, batch filtering logic

---

## Increment 4: Render Production Deployment

### CARD-410: Deploy to Render & verify migration

**Type:** Deployment / Operations  
**Effort:** 15 min  
**Priority:** P0 (go-live)

**Description:**
Deploy the DB persistence code to Render and verify migration `002` runs successfully against the production Postgres.

**Procedure:**
1. Ensure all commits are pushed to main (commits 5d5eda8 through 7645ebc)
2. Trigger Render redeploy (or wait for auto-deploy)
3. Monitor build logs:
   - [ ] `pip install -r requirements.txt` succeeds
   - [ ] `alembic upgrade head` runs and completes
   - [ ] No migration errors
   - [ ] App starts successfully
4. Check Render app URL — admin panel loads
5. Check Render PostgreSQL add-on — database connection healthy

**Checkpoint:** Migration applied to production Postgres, app running with DB-backed services

**Acceptance Criteria:**
- Build succeeds
- Migration applies (no errors, no rollback)
- App health check passes
- Database connection verified

**Touches:** render.yaml, migrations/versions/002_add_batches_and_puzzles.py

---

### CARD-411: Production smoke test (Render)

**Type:** Testing / Validation  
**Effort:** 20 min  
**Priority:** P0 (go-live verification)

**Description:**
Test the live admin panel on Render to confirm DB persistence is working in production.

**Checklist:**
- [ ] Navigate to Render app URL `/batch/create`
- [ ] Upload 2-3 test images
- [ ] Create batch with default settings
- [ ] Complete workflow to approval stage
- [ ] Approve 1 puzzle, reject 1
- [ ] Download SVG/PDF — files download successfully
- [ ] Kill the dyno (via Render dashboard):
  - Render automatically restarts
  - Wait 30-60 seconds for restart
- [ ] Reload admin panel — batch still appears
- [ ] Verify puzzle counts and statuses match pre-crash state
- [ ] Create another batch — verify it has a different ID

**Checkpoint:** Production crash recovery confirmed, multiple batches persist, restart recovery works

**Acceptance Criteria:**
- Batch created and persisted to Postgres
- Files download without errors
- Dyno restart doesn't lose batch/puzzle data
- Multiple batches coexist correctly
- UI loads and functions normally

**Touches:** Production admin panel, Render PostgreSQL

---

### CARD-412: Document production metrics & monitoring

**Type:** Documentation / Operations  
**Effort:** 15 min  
**Priority:** P2 (post-deployment)

**Description:**
Document key metrics to monitor post-deployment and where to find them.

**Checklist:**
- [ ] Add to operations docs:
  - [ ] How to check Postgres disk usage (Render dashboard)
  - [ ] How to run alembic upgrade manually if needed
  - [ ] How to query batch/puzzle counts: `SELECT COUNT(*) FROM batches WHERE status='complete'`
  - [ ] How to identify slow batches: `SELECT * FROM batches WHERE status='generating' AND updated_at < NOW() - INTERVAL 1 hour`
  - [ ] Where to find alembic version info: `SELECT * FROM alembic_version`
- [ ] Create runbook for:
  - [ ] Recovering a stuck batch
  - [ ] Rolling back migration `002` (if needed)
  - [ ] Adding new migration

**Acceptance Criteria:**
- Ops team has clear procedures documented
- Key queries documented
- Troubleshooting guide complete

**Touches:** docs/DB_PERSISTENCE_IMPLEMENTATION.md (updated), ops runbooks

---

## Summary

| Card | Title | Type | Status | Effort | Increment |
|------|-------|------|--------|--------|-----------|
| 401 | Set up local Postgres | Testing | Ready | 30m | 1 |
| 402 | Full test suite (legacy) | Testing | Ready | 15m | 1 |
| 403 | DB smoke tests | Testing | Ready | 15m | 1 |
| 404 | E2E workflow test | Testing | Ready | 45m | 2 |
| 405 | Crash recovery test | Testing | Ready | 30m | 2 |
| 406 | UAT: Simple batch | Validation | Ready | 20m | 3 |
| 407 | UAT: Quality filtering | Validation | Ready | 25m | 3 |
| 408 | UAT: Size persistence | Validation | Ready | 20m | 3 |
| 409 | UAT: Multiple batches | Validation | Ready | 30m | 3 |
| 410 | Deploy to Render | Deployment | Ready | 15m | 4 |
| 411 | Production smoke test | Validation | Ready | 20m | 4 |
| 412 | Monitoring docs | Documentation | Ready | 15m | 4 |

**Total Effort:** ~5 hours  
**Recommended Timeline:** Stagger across 2-3 days  
**Blockers:** None (implementation complete)

---

## Definition of Done

**Increment 1 (Local Setup):** Docker Postgres running, all migrations applied, all existing tests pass  
**Increment 2 (Local E2E):** Full workflow tested, crash recovery verified locally  
**Increment 3 (UAT):** All user scenarios tested by Anna, no blockers  
**Increment 4 (Production):** Live on Render, smoke tested, monitoring documented  

---

**Ready for:** Execution by Anna (QA) and DevOps for testing and deployment.
