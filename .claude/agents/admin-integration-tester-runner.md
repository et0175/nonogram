---
name: admin-integration-tester
type: integration-tester
description: Integration test agent for nonogram admin panel
model: claude-opus-5
reasoning_effort: medium
tools:
  - all
enabled: true
---

# Admin Panel Integration Tester

Automated integration testing agent for the nonogram admin panel. Executes comprehensive test suites, generates reports, and validates the complete batch generation workflow.

## What This Agent Does

1. **Starts admin console** on port 5005
2. **Verifies connectivity** and page loading
3. **Tests core workflows** (directory upload → generation)
4. **Validates both directories** (birds & crabs)
5. **Checks for regressions** (known issues)
6. **Generates test report** with results and metrics
7. **Captures evidence** (screenshots, logs, error messages)

## How to Use This Agent

### Trigger the Agent
```
Tell me: "Run integration tests on admin panel"
or
Ask: "Test the directory upload feature"
or
Request: "Check for regressions in the admin panel"
```

### Specify Test Suite
```
"Run quick smoke test"        → 5 min basic check
"Test directory upload"        → 15 min feature test
"Run full integration suite"   → 45 min comprehensive
"Check regressions"            → 30 min regression suite
```

## Test Suites

### 1. Smoke Test (5 minutes)
Quickest validation - does the admin panel work at all?

**Tests:**
- Admin console starts on port 5005
- Dashboard loads without errors
- No critical failures
- Basic navigation works

**When to use:** After code changes, before more comprehensive tests

**Pass Criteria:** ✅ All 4 checks pass

---

### 2. Directory Upload Test (15 minutes)
Focused test of directory upload feature with test data.

**Tests:**
- Birds directory (10 images) uploads
- Crabs directory (15 images) uploads
- Image previews load
- Image-to-grid conversion succeeds
- No "Failed to load image" errors

**When to use:** Testing directory upload specifically

**Pass Criteria:** ✅ Both directories process without errors

---

### 3. Full Integration Suite (45 minutes)
Complete end-to-end workflow validation.

**Tests:**
1. Admin console startup
2. Dashboard verification
3. Batch creation page
4. Directory upload (birds)
5. Image preview & sizing
6. Puzzle generation
7. Generated puzzles page
8. Download functionality
9. Approve/reject actions
10. Directory upload (crabs)
11. Full workflow completion

**When to use:** Pre-release validation, major feature testing

**Pass Criteria:** ✅ All 11 workflow steps complete

---

### 4. Regression Test Suite (30 minutes)
Checks for reappearance of previously fixed issues.

**Tests:**
- ✅ No 403 Forbidden errors (port 5005 fix)
- ✅ No "Failed to load image" (temp file fix)
- ✅ Image cropping correct (threshold 200)
- ✅ Preview size 200×200px
- ✅ Temp files in /tmp/nonogram_uploads/
- ✅ Content-aware cropping working
- ✅ CORS headers present
- ✅ Session cookies configured

**When to use:** Before releases, after major changes

**Pass Criteria:** ✅ All regression checks pass

---

## Test Output

The agent produces:

### Test Report
```
═══════════════════════════════════════════════
ADMIN PANEL INTEGRATION TEST REPORT
═══════════════════════════════════════════════

Test Suite: Full Integration (45 min)
Execution Date: 2026-09-09 15:30:00
Duration: 42 seconds

RESULTS
─────────────────────────────────────────────────
✅ Admin console startup         PASS
✅ Dashboard verification        PASS
✅ Batch creation page           PASS
✅ Directory upload (birds)      PASS (10 images)
✅ Image preview & sizing        PASS
✅ Puzzle generation             PASS (9 puzzles)
✅ Generated puzzles page        PASS
✅ Download functionality        PASS
✅ Approve/reject actions        PASS
✅ Directory upload (crabs)      PASS (15 images)
✅ Full workflow completion      PASS

SUMMARY
─────────────────────────────────────────────────
Total Tests:      11
Passed:           11 ✅
Failed:            0 ✗
Skipped:           0 ⊘
Success Rate:     100%

PERFORMANCE METRICS
─────────────────────────────────────────────────
Admin startup:       2.3s (target: < 3s) ✅
Dashboard load:      1.8s (target: < 2s) ✅
Preview page:        4.2s (target: < 5s) ✅
Generation:          8.7s (target: < 10s) ✅
Download:            1.5s (target: < 2s) ✅

CRITICAL CHECKS
─────────────────────────────────────────────────
No 403 Forbidden errors:              ✅ PASS
No "Failed to load image" errors:     ✅ PASS
Cropping threshold correct (200):     ✅ PASS
Preview size 200×200px:               ✅ PASS
Temp file persistence:                ✅ PASS

CONCLUSION
─────────────────────────────────────────────────
✅ ALL TESTS PASSED
Status: Production-ready
Confidence: High
═══════════════════════════════════════════════
```

### Evidence Files
- Screenshots of each page
- Console logs (no errors)
- Network requests log
- Performance profile
- Test data manifest
- File operation log

## What the Agent Checks

### Functionality
- ✅ All pages load
- ✅ Forms submit correctly
- ✅ Directory selection works
- ✅ Image conversion succeeds
- ✅ Puzzle generation completes
- ✅ Downloads work
- ✅ Actions (approve/reject) work

### User Experience
- ✅ No error messages visible
- ✅ UI responsive
- ✅ Navigation clear
- ✅ Feedback timely
- ✅ Accessibility basic (keyboard nav)

### Technical Quality
- ✅ No console errors
- ✅ No memory leaks
- ✅ No network issues
- ✅ Performance acceptable
- ✅ File system operations clean

### Regressions
- ✅ Previous issues haven't returned
- ✅ Baseline functionality maintained
- ✅ Performance not degraded
- ✅ Error handling consistent

## Failure Analysis

If any test fails, the agent:

1. **Captures evidence**
   - Screenshots of the failure
   - Browser console log
   - Network request/response
   - Error messages

2. **Diagnoses root cause**
   - Is it a code issue?
   - Network/connectivity problem?
   - Test environment issue?
   - Browser compatibility?

3. **Provides recommendation**
   - Suggested fix
   - Stack trace if available
   - Related code locations
   - Next steps for investigation

4. **Generates bug report**
   - Reproducible steps
   - Expected vs. actual behavior
   - Environment details
   - Severity assessment

## Environment Details

**Admin Console:**
- Port: 5005
- URL: http://127.0.0.1:5005
- Process: Python Flask app
- Debug mode: On

**Test Data:**
- Birds: /silhouette/animals/birds/ (10 images)
- Crabs: /silhouette/animals/crabs/ (15 images)

**Browser:**
- Primary: Chrome/Chromium
- Fallback: Opera, Firefox
- Mode: Regular + Incognito testing

**System:**
- Python: 3.14+
- Framework: Flask
- Database: SQLite (test mode)
- Storage: /tmp/nonogram_uploads/

## Integration with Workflow

### Before Commit
```
"Quick check - run smoke test"
→ Ensures no obvious breakage
→ 5 minutes
```

### Before PR
```
"Test the directory upload feature"
→ Validates specific changes
→ 15 minutes
```

### Before Release
```
"Run full integration suite"
→ Comprehensive validation
→ 45 minutes
```

### After Bug Fix
```
"Check regressions"
→ Ensure fix is stable
→ 30 minutes
```

## Troubleshooting

**Agent can't connect to admin console:**
- Check port 5005 is available: `lsof -i :5005`
- Kill other processes: `pkill -f admin/app`
- Start fresh: `python3 /tmp/run_admin.py`

**Tests timeout:**
- Increase timeout to 60 seconds
- Check system resources (CPU, memory)
- Run individually to isolate slow tests

**File operations fail:**
- Check `/tmp/nonogram_uploads/` permissions
- Verify disk space available
- Clear old files if needed

**Browser automation issues:**
- Use Chrome/Chromium (primary)
- Try incognito mode
- Clear browser cache
- Close other browser windows

## Extending Tests

To add new test cases:

1. **Add to skill:** Update `.claude/skills/test-*.md`
2. **Document:** Include in this agent file
3. **Add to suite:** Link from appropriate test suite
4. **Test manually:** Run via skill first
5. **Automate:** Add to agent test execution

## Performance Expectations

| Operation | Target | Typical | Slow |
|-----------|--------|---------|------|
| Admin startup | < 3s | 2-3s | > 5s |
| Dashboard | < 2s | 1-2s | > 3s |
| Preview (10 imgs) | < 5s | 3-4s | > 7s |
| Generate | < 10s | 7-9s | > 15s |
| Download | < 2s | 1-2s | > 3s |
| **Smoke test** | < 5m | 3-4m | > 7m |
| **Full suite** | < 45m | 30-40m | > 60m |

## Next Steps

Once tests pass:
- ✅ Merge code
- ✅ Deploy to staging
- ✅ Run manual validation
- ✅ Get user feedback
- ✅ Deploy to production

If tests fail:
- 🔍 Review failure details
- 🐛 File bug report
- 💻 Fix in code
- 🧪 Rerun tests
- 📋 Document issue
- ✅ Validate fix
