# Reports Directory

Test execution results, deployment status, and quality metrics.

## Subdirectories

### test-reports/
All test execution reports and summaries.

**Contents:**
- E2E_TEST_REPORT.md - Comprehensive end-to-end test results
- E2E_TEST_SUMMARY.md - Summary statistics and overview
- NONOGRAM_WEB_TEST_REPORT.md - Web UI test results
- E2E_TESTS_README.md - Test documentation and setup

**Purpose:** Track test execution, coverage, and quality metrics

### deployment-reports/
Deployment status and operational reports.

**Contents:**
- Deployment status updates
- Fix summaries and hotpatch documentation
- Incident reports and resolutions

**Purpose:** Track deployment activities and infrastructure status

## Report Organization

Reports are organized by:
- **Type** - Test reports, deployment reports, performance reports
- **Date** - Latest reports are most current
- **Component** - E2E tests, UI tests, API tests, etc.

## Reading Test Reports

### Report Contents
Each test report typically includes:
- Test execution summary (pass/fail counts)
- Test results by component/feature
- Failure details and logs
- Coverage metrics
- Performance metrics (if applicable)
- Recommendations

### Test Report Naming
- Date-based: `2026-09-05_test_report.md`
- Component-based: `e2e_test_report.md`, `ui_test_report.md`
- Status-based: Latest results always in `current_*` files

## Reading Deployment Reports

### Deployment Report Contents
- Deployment date and time
- Services deployed
- Configuration changes
- Validation results
- Any issues encountered
- Rollback information (if applicable)

### Deployment Status Tracking
- Current deployment status
- Recent changes
- Known issues in current deployment
- Next scheduled deployment

## Usage Guidelines

### For Review/Approval
1. Check latest test reports in test-reports/
2. Review coverage and pass rate
3. Check deployment-reports/ for production status
4. Verify no critical failures before approval

### For Debugging Failures
1. Find relevant test report
2. Look for failure details and stack traces
3. Cross-reference with ../development/troubleshooting/
4. Check application logs

### For Metrics/Analytics
1. Review test reports for trends
2. Track deployment history in deployment-reports/
3. Monitor performance over time
4. Identify patterns and areas for improvement

## Report Lifecycle

1. **Generated** - During CI/CD pipeline or manual test runs
2. **Archived** - Old reports moved to archive/ subdirectory after 90 days
3. **Analyzed** - Critical findings escalated to team
4. **Resolved** - Issues fixed and documented

## Archiving Old Reports

To keep this directory manageable:
- Move reports older than 3 months to archive/
- Keep latest 10 reports of each type
- Maintain quarterly summaries

```bash
mkdir -p archive/
mv reports/2026-06-*.md archive/
```

## Accessing Report History

- **Current status** - Latest file in each subdirectory
- **Recent history** - Last 10 files
- **Archived** - archive/ subdirectory (organized by date)
- **Trending** - Monthly/quarterly summary reports

---
Last updated: 2026-09-05
