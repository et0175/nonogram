# Admin Panel Testing & Improvement Roadmap

Structured kanban approach: create cards → write tests → test locally → document findings → fix issues → iterate.

**Updated**: 2026-09-07  
**Status**: Planning Phase (Wave 1)

---

## Wave Overview

### Wave 1: Core Features & Testing Foundation (Current)
- Establish testing framework ✓ (conftest.py, test fixtures, ADMIN_FINDINGS.md)
- Fix critical UX issues (batch history, preview, bulk operations)
- Write comprehensive tests (unit, E2E, Playwright)
- User tests locally and documents findings

**Cards**: CARD-004h, 004i, 004j, 005a, 005b, 005d, 005e

### Wave 2: Async & Error Handling
- Implement async batch generation (prevent timeouts)
- Add error recovery (retry, cancel failed batches)
- Complete book management
- Improve PDF generation

**Cards**: CARD-004k, 004l, 004m, 004n

### Wave 3: Polish & Production
- Form validation & input constraints
- Additional browser testing
- Performance optimization
- Security/auth improvements

**Cards**: CARD-004o, 004g (security)

---

## Detailed Card List

### Wave 1: Core Features & Testing

| Card | Title | Size | Priority | Status |
|------|-------|------|----------|--------|
| CARD-004h | Batch History & Tracking | 8pt | High | Pending |
| CARD-004i | Puzzle Preview Modal | 8pt | High | Pending |
| CARD-004j | Bulk Puzzle Operations | 8pt | High | Pending |
| CARD-005b | Comprehensive Unit Tests | 13pt | High | Pending |
| CARD-005d | Comprehensive E2E Tests | 13pt | High | Pending |
| CARD-005e | Admin Testing Guide & Docs | 8pt | High | In Progress |

**Wave 1 Total**: ~58 points

**Testing Components**:
- Unit tests: service logic, validation, metrics
- E2E tests: workflows (batch→review→book→PDF)
- Playwright tests: UI interactions, form validation

### Wave 2: Async & Error Handling

| Card | Title | Size | Priority | Status |
|------|-------|------|----------|--------|
| CARD-004k | Async Batch Generation | 13pt | Critical | Pending |
| CARD-004l | Error Recovery & Retry | 5pt | High | Pending |
| CARD-004m | Book Management & Selection | 8pt | High | Pending |
| CARD-004n | PDF Generation & Download | 8pt | High | Pending |

**Wave 2 Total**: ~34 points

### Wave 3: Polish & Production

| Card | Title | Size | Priority | Status |
|------|-------|------|----------|--------|
| CARD-004o | Form Validation & Constraints | 5pt | Medium | Pending |
| CARD-004g | Admin Authentication & Access | TBD | High | Pending |

**Wave 3 Total**: ~5+ points

---

## Workflow: Test → Find → Fix → Verify

### Step 1: Create Cards for Wave

Review CARD-004h, 004i, 004j (Wave 1 feature cards)

### Step 2: Architect Writes Tests

For each card, I create:
- **Unit tests** (test_*.py files)
- **E2E tests** (test_admin_panel_e2e.py)
- **Playwright tests** (test_*.spec.ts or similar)
- Test fixtures and helpers

### Step 3: You Test Locally

Using TESTING_WORKFLOW.md:
1. Set up local environment
2. Follow ADMIN_TESTING_PLAN.md
3. Run automated tests: `pytest tests/test_admin_panel_e2e.py -v`
4. Manual testing (UI verification)

### Step 4: Document Findings

Add issues to ADMIN_FINDINGS.md with all details

### Step 5: Wave Review & Discussion

After testing phase (3-5 days), discuss:
- Which issues to fix first?
- Do we fix all Wave 1 issues before Wave 2?
- Any blockers for next wave?

### Step 6: Fix Issues

I investigate, fix, and test locally

### Step 7: Verify Fix

You pull, re-test, confirm fix works

### Step 8: Wave Complete

Merge all changes, run full test suite, move to next wave

---

## Success Criteria for Each Wave

### Wave 1 Success
- [ ] All CARD-004h, 004i, 004j implemented
- [ ] All unit tests passing (80%+ coverage)
- [ ] All E2E tests passing
- [ ] You tested locally, found issues
- [ ] All found issues fixed and verified
- [ ] Performance baseline established

### Wave 2 Success
- [ ] Async batch generation working (no timeouts)
- [ ] Error recovery working
- [ ] PDF generation reliable for all book sizes
- [ ] All tests passing

### Wave 3 Success
- [ ] Form validation comprehensive
- [ ] Authentication/access control implemented
- [ ] Admin panel production-ready

---

## Next Steps

1. **Review this roadmap** — any changes?
2. **Start Wave 1**:
   - I write tests for CARD-004h, 004i, 004j
   - You test locally, document findings
3. **First wave review** (estimated 1 week)
   - Discuss findings and priorities
   - Fix issues
   - Plan Wave 2

Ready to kick off Wave 1? 🚀
