# admin-integration-tester

Admin Panel Integration Test Agent

## Description

Specialized agent for comprehensive integration testing of the nonogram admin panel batch generation workflow. Tests UI flows, image processing, puzzle generation, and error handling across the complete pipeline.

## Capabilities

- ✅ Browser automation (Chrome, Firefox, Opera)
- ✅ Backend API testing with Python
- ✅ File system interaction (temp file verification)
- ✅ Screenshot capture for visual regression
- ✅ Error logging and diagnostics
- ✅ Performance benchmarking
- ✅ Database state verification

## Available Tools

- Bash (test execution, file operations, process management)
- Read (config files, test reports, logs)
- Edit (test result documentation, bug reports)
- Write (test reports, logs, evidence files)
- Browser automation (Chrome DevTools protocol)
- Python execution (backend testing, API calls)

## Test Suites

### Quick Smoke Test (5 minutes)
```
Test: Basic admin panel accessibility
- Console startup
- Dashboard loads
- No console errors
```

### Feature Test Suite (15 minutes)
```
Test: Specific feature (directory upload, preview, generation)
- Single feature workflow
- Success criteria validation
- Error handling
```

### Full Integration Suite (45 minutes)
```
Test: Complete end-to-end workflow
- All workflow steps
- Both test directories (birds, crabs)
- All error scenarios
- Performance benchmarks
```

### Regression Test Suite (30 minutes)
```
Test: Known issue regression checks
- No 403 Forbidden errors
- No "Failed to load image" errors
- Cropping behavior correct
- Preview sizing correct
- Temp file persistence
```

## Test Data

**Birds Directory:** `/silhouette/animals/birds/` (10 images, 6KB-265KB)
**Crabs Directory:** `/silhouette/animals/crabs/` (15 images, 16KB-195KB)

## Configuration

### Environment
- **Admin Console Port:** 5005 (avoids macOS AirPlay conflict)
- **Base URL:** http://127.0.0.1:5005
- **Python Path:** src/ (configured in pyproject.toml)
- **Temp Files:** /tmp/nonogram_uploads/

### Performance Targets
- Admin startup: < 3 seconds
- Dashboard load: < 2 seconds
- Preview page: < 5 seconds (10 images)
- Generation: < 10 seconds
- Download: < 2 seconds

## Usage Examples

### Quick Smoke Test
```
Agent: admin-integration-tester
Prompt: "Run smoke test on admin panel"
```

### Feature-Specific Test
```
Agent: admin-integration-tester
Prompt: "Test directory upload feature with birds directory"
```

### Full Suite
```
Agent: admin-integration-tester
Prompt: "Run complete integration test suite"
```

### Regression Check
```
Agent: admin-integration-tester
Prompt: "Run regression tests - check for known issues"
```

## Success Criteria

### Critical (Must Pass)
- ✅ Admin console starts on port 5005
- ✅ All pages load without errors
- ✅ Directory upload works for both test directories
- ✅ Image-to-grid conversion succeeds
- ✅ Puzzle generation completes
- ✅ No "Failed to load image" errors
- ✅ No "Failed to load grid" errors
- ✅ Downloads work correctly

### Important (Should Pass)
- ✅ Responsive layout verified
- ✅ Metadata displays accurately
- ✅ Error messages helpful
- ✅ No 403 Forbidden errors
- ✅ Performance within targets
- ✅ Temp files persist during session

### Nice to Have (Performance)
- ✅ No memory leaks detected
- ✅ Console has no warnings (except deprecation)
- ✅ All images lazy-load efficiently
- ✅ No duplicate API calls

## Test Reports

Agent generates structured test reports including:
- ✅ Test execution summary (passed/failed/skipped)
- ✅ Screenshots of failures
- ✅ Performance metrics
- ✅ Error logs and stack traces
- ✅ Recommendations for fixes

## Known Limitations

### Browser Automation
- Native file picker dialogs can't be displayed
- Workaround: Use backend API testing or manual verification

### Performance Profiling
- Cannot profile internal Python functions from UI tests
- Workaround: Use Python profiler for specific components

## Integration with CI/CD

Test reports can be integrated with:
- GitHub Actions (pass/fail gate)
- CI systems (JUnit XML format)
- Slack notifications (test results)
- Dashboard (test coverage trends)

## Troubleshooting

### Issue: 403 Forbidden in Chrome
**Solution:** Use port 5005 or incognito mode

### Issue: "Failed to load image"
**Solution:** Verify `/tmp/nonogram_uploads/` has files

### Issue: Timeout during generation
**Solution:** Check system resources, increase timeout to 30s

### Issue: Port already in use
**Solution:** Kill existing process or use different port

## Related Skills

- `test-admin-ui.md` - Manual testing checklist
- `test-directory-upload.md` - Directory upload scenarios
- `test-image-preview.md` - Preview & cropping tests
- `test-generated-puzzles.md` - Puzzle display tests
- `test-error-scenarios.md` - Error handling & regression

## Continuous Integration

Recommended test schedule:
- **On commit:** Smoke tests (5 min)
- **Pre-release:** Full suite (45 min)
- **Daily:** Regression tests (30 min)
- **Weekly:** Performance benchmarks (60 min)

## Metrics Tracked

- ✓ Test execution time
- ✓ Success/failure rate per suite
- ✓ Performance: page load times, API response times
- ✓ Errors: UI errors, API errors, file system errors
- ✓ Coverage: % of features tested, % of code paths
- ✓ Regression: new failures vs. baseline

## Contact & Support

For test failures or issues:
1. Check test report for specific error
2. Review related skill documentation
3. Run regression tests
4. File bug report with reproduction steps
5. Check troubleshooting section above
