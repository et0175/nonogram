# Admin Panel Testing Workflow

Step-by-step guide for systematic testing of the Nonogram Admin Panel locally before production deployment.

## Overview

The workflow has 3 phases:

1. **Manual Testing** (Phase 1-2) - You test UI locally, document findings
2. **Investigation & Fix** - I investigate and fix issues you find
3. **Automated Testing** (Phase 3) - Run test suite to catch regressions

This creates a feedback loop: **Test → Find → Fix → Verify**.

---

## Phase 1: Set Up Local Environment

### Prerequisites

- Python 3.14+
- PostgreSQL running locally
- Virtual environment activated

### Setup Steps

```bash
# Navigate to project
cd /Users/omelnikova/PycharmProjects/PythonProject4

# Activate venv
source .venv/bin/activate

# Set environment
export FLASK_ENV=development
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"

# Run migrations (one-time)
alembic upgrade head

# Start Flask app
python -m flask --app src.nonogram.admin.app run

# In another terminal, run tests
pytest tests/test_admin_panel_e2e.py -v
```

The app will be available at **http://localhost:5000**

---

## Phase 2: Manual Testing & Finding Documentation

Follow this workflow for each test scenario:

### 1. Test a Feature

Pick a test case from **ADMIN_TESTING_PLAN.md** (e.g., "Generate small batch (50 puzzles)")

**Steps**:
1. Open http://localhost:5000
2. Navigate to the feature (e.g., Batch Generation)
3. Perform the test steps
4. Check if it behaves as expected

### 2. Document Any Issues

If something fails or behaves unexpectedly:

1. Open `/docs/ADMIN_FINDINGS.md`
2. Add a new issue using the template:

```markdown
## Issue: [Brief title]

**Status**: `new`

**Severity**: `high` (critical/high/medium/low)

**Description**: 
When I [did this], I expected [this], but got [this] instead.

**Steps to Reproduce**:
1. Go to Batch Generation
2. Click "Create Small Batch"
3. Wait for completion

**Environment**: Local

**Expected Behavior**: Status shows "100% Complete"

**Actual Behavior**: Status stuck at 50%

**Screenshots**: [Paste screenshot if helpful]
```

3. Commit to git (this signals to me)

```bash
git add docs/ADMIN_FINDINGS.md
git commit -m "test: document batch generation timeout issue"
```

### 3. Share the Finding

Send a message like:

> I found an issue - batch generation gets stuck at 50%. Added to ADMIN_FINDINGS.md with steps to reproduce.

Then I will:
1. Read ADMIN_FINDINGS.md
2. Investigate the code
3. Fix the issue
4. Update ADMIN_FINDINGS.md with the fix
5. Ask you to test the fix

### 4. Verify the Fix

After I fix an issue:

1. Pull latest changes: `git pull`
2. Restart Flask: Stop and restart `flask run`
3. Re-test the same scenario
4. If fixed → move issue to "Completed Issues" in ADMIN_FINDINGS.md
5. If still broken → add more details to the finding

---

## Recommended Test Order

Do NOT test everything at once. Follow this order to catch issues early:

### Day 1: Core Workflows (2-3 hours)

1. **Dashboard** (5 min)
   - [ ] Load http://localhost:5000
   - [ ] See dashboard with stats

2. **Batch Generation** (30 min)
   - [ ] Generate small batch (50 puzzles)
   - [ ] Watch status progress to 100%
   - [ ] See "Complete" status

3. **Puzzle Review** (30 min)
   - [ ] Go to Puzzle Review
   - [ ] See 50 puzzles listed
   - [ ] Try filters (size, difficulty, quality)
   - [ ] Approve 5 puzzles
   - [ ] Reject 3 puzzles

4. **Book Creation** (30 min)
   - [ ] Create a new book
   - [ ] Generate PDF
   - [ ] Download and open PDF
   - [ ] Verify PDF has puzzles

**Document any issues as you go.**

### Day 2: Edge Cases & Performance (2-3 hours)

1. **Large Batch** (30 min)
   - [ ] Generate 100 puzzles
   - [ ] Generate 200 puzzles
   - [ ] Measure time and watch for timeouts

2. **Empty States** (20 min)
   - [ ] Create book with 0 puzzles (should error)
   - [ ] Search with no results
   - [ ] Approve all puzzles, then filter by rejected (should be empty)

3. **Filters** (20 min)
   - [ ] Filter by different sizes
   - [ ] Combine multiple filters
   - [ ] Clear filters

4. **Performance** (30 min)
   - [ ] Open performance baseline table in ADMIN_FINDINGS.md
   - [ ] Time each operation and fill in measured times
   - [ ] Compare to targets

### Day 3+: Systematic Testing (1+ hours)

1. **Run automated tests**
   ```bash
   pytest tests/test_admin_panel_e2e.py -v
   ```

2. **Run smoke tests only** (quick)
   ```bash
   pytest tests/test_admin_panel_e2e.py -m smoke -v
   ```

3. **Run integration tests**
   ```bash
   pytest tests/test_admin_panel_e2e.py -m integration -v
   ```

4. **If any test fails**
   - Run with more details: `pytest tests/test_admin_panel_e2e.py::test_name -vv`
   - Add finding to ADMIN_FINDINGS.md
   - Include the test error output

---

## Example: Testing a Feature End-to-End

### Test: "Batch generation and puzzle storage"

**Environment**: Local, PostgreSQL running

**Setup**:
1. Flask running at http://localhost:5000
2. Dashboard shows "0 puzzles"

**Test Steps**:
1. Click "Batch Generation" menu
2. Click "Create Batch" button
3. Select "Small Batch" preset (50 puzzles)
4. Click "Start Generation"
5. Wait for status to reach 100%
6. See "COMPLETE" status
7. Click "Puzzle Review" menu
8. Verify 50 puzzles appear in list
9. See stats updated (50 total, 50 draft)

**Expected Result**: ✓ All steps complete without errors

**If Failed**: 
- Note which step failed
- Take screenshot
- Add to ADMIN_FINDINGS.md with step, expected vs actual
- Send message: "Generation fails at step X: [description]"

---

## How I Fix Issues

When you document an issue:

1. **Read** ADMIN_FINDINGS.md to get context
2. **Reproduce** locally following your steps
3. **Debug** the code (read logs, check database, etc.)
4. **Fix** the issue (edit code)
5. **Test** the fix locally (run your steps again)
6. **Verify** with automated tests (run pytest)
7. **Update** ADMIN_FINDINGS.md with fix details and commit
8. **Tell you** to pull and re-test

You don't need to understand the fix - just verify it works by re-testing.

---

## Communication Template

### When you find an issue:

> **Issue**: [Brief title]
> 
> **Reproduction**: On Local, I [steps to reproduce]
> 
> **Expected**: [What should happen]
> 
> **Actual**: [What actually happens]
> 
> **Details**: Added to ADMIN_FINDINGS.md at [time] for investigation

### When I report a fix:

> Fixed: [Issue title]
> 
> **Root cause**: [Brief explanation]
> 
> **What changed**: [File and what was fixed]
> 
> **To verify**: 
> 1. Pull latest
> 2. Restart Flask
> 3. Reproduce original steps
> 4. Should now work correctly

### How to structure a message with findings:

> I tested Phase 1 today:
> 
> ✓ Dashboard loads
> ✓ Small batch generates (took 4.2 seconds)
> ✓ Puzzles appear in review (50 total)
> ✓ Filters work (size, difficulty)
> ✓ Can approve/reject puzzles
> 
> ✗ Book creation (found 1 issue - added to ADMIN_FINDINGS.md)
> 
> Total issues: 1, Ready to fix?

---

## Checklist: Before Declaring "Ready for Production"

- [ ] All Phase 1 tests pass
- [ ] All Phase 2 edge cases pass
- [ ] All Phase 3 automated tests pass (pytest)
- [ ] Performance measurements within targets
- [ ] No critical or high-severity issues remain in ADMIN_FINDINGS.md
- [ ] Database migrations work on Render
- [ ] Documentation is up-to-date (ADMIN_SETUP.md)

---

## Files You'll Use

| File | Purpose |
|------|---------|
| `ADMIN_TESTING_PLAN.md` | Checklist of what to test |
| `ADMIN_FINDINGS.md` | Where you document issues |
| `TESTING_WORKFLOW.md` | This file - how to test |
| `tests/test_admin_panel_e2e.py` | Automated tests to run |
| `tests/conftest.py` | Test fixtures and setup |

---

## Common Issues & Solutions

**Flask won't start**
```bash
# Check port 5000 is free
lsof -i :5000

# If occupied, use different port
python -m flask --app src.nonogram.admin.app run --port 8000
```

**Database connection fails**
```bash
# Verify DATABASE_URL is set
echo $DATABASE_URL

# Test connection directly
psql $DATABASE_URL -c "SELECT 1;"
```

**Tests fail with import errors**
```bash
# Reinstall package in dev mode
pip install -e '.[dev]'
```

**Puzzles don't appear after generation**
```bash
# Check database directly
psql $DATABASE_URL -c "SELECT COUNT(*) FROM puzzles;"

# If 0, check Flask logs for errors
# Add more finding details and share with me
```

---

## Next Steps

1. **Set up local environment** (see Phase 1)
2. **Start Phase 1 manual testing** following test order above
3. **Document any issues** in ADMIN_FINDINGS.md
4. **Share findings** - I'll investigate and fix
5. **Iterate** until all tests pass
6. **Run automated test suite** to catch regressions

Let's build this systematically! 🚀

---

**Questions?** Let me know - this workflow can be adjusted based on what you find.
