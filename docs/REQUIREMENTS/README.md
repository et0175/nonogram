# Requirements Documentation Framework

**Purpose**: Central index for all requirements, user stories, and test cases  
**Last Updated**: 2026-09-22  
**Status**: Reorganization abandoned — this framework was never populated

> **Status (2026-09-22, CARD-071): this is not the project's requirements
> system.** The live registry is
> [`meta/architecture/requirements.yml`](../../meta/architecture/requirements.yml)
> — FR/NFR/CON entries, each with acceptance criteria that name the test
> verifying them — with traceability in
> [`meta/architecture/trace.yml`](../../meta/architecture/trace.yml) and the
> generation pipeline described as implemented in
> [`docs/GENERATION_ALGORITHM.md`](../GENERATION_ALGORITHM.md). The `REQ-xxx` /
> `AS-xxx` / `GS-xxx` / `TC-xxx` scheme below belongs to a 2026-09-08 plan for
> a parallel framework that was never built: of the ~20 files its tree listed,
> three existed. The tree now shows what is actually on disk; the conventions,
> checklists and metrics further down are kept as the plan they were, not
> deleted, and describe nothing that ships.

## 📋 Document Organization

What is actually here (verified 2026-09-22):

```
REQUIREMENTS/
├─ README.md (this file)
├─ REQUIREMENTS_OVERVIEW.md            (2026-09-08 overview; parts stale — see its banner)
├─ SUMMARY.md                          (2026-09-08 summary of the same)
├─ ADMIN_CONSOLE_REQUIREMENTS.md       (admin panel REQ-x.y.z, partly stale)
├─ NONOGRAM_GENERATION_REQUIREMENTS.md (superseded for algorithm questions)
├─ DIFFICULTY_ENGINE.md                (superseded — the shipped formula is ADR-0013's)
├─ USER_STORIES/
│  └─ ADMIN_PANEL_STORIES.md           (AS-001 onwards)
├─ TEST_CASES/
│  └─ ADMIN_PANEL_TC.md                (TC-101 onwards)
└─ TRACEABILITY/
   └─ TRACEABILITY_MATRIX.md           (REQ → story → test case, for the above)
```

The live equivalents of the directories this tree used to promise:

| Planned here | What actually holds it |
|---|---|
| `FEATURES/` | `meta/architecture/requirements.yml` (FR/NFR/CON) |
| `ACCEPTANCE_CRITERIA/` | the `acceptance:` block on each entry in that file |
| `TEST_CASES/` | the suite under `tests/`, named by each AC's `test:` field |
| `TRACEABILITY/COVERAGE_REPORT.md` | `meta/architecture/trace.yml` + the forge validator |
| `NON_FUNCTIONAL/` | the `NFR-*` entries in `requirements.yml` |
| `FINDINGS/` | `meta/review/*.yml` (per-card review cycles) |
| `TESTING/` | `tests/`, plus each card's `## Worktree notes` |

## 📑 Key Documents

### Requirements Phase
1. **Feature Requirements** (FEATURES/)
   - What the system must do (functional requirements)
   - How the system must perform (non-functional requirements)
   - Examples: "User can upload images", "Generation completes in <10s"

2. **User Stories** (USER_STORIES/)
   - Development units derived from requirements
   - Format: "As a [role], I want [capability] so that [benefit]"
   - Includes acceptance criteria and story IDs

3. **Acceptance Criteria** (ACCEPTANCE_CRITERIA/)
   - Testable conditions that must be met
   - Format: "Given [context], When [action], Then [result]"
   - Separate from stories for cross-reference

### Testing Phase
4. **Test Cases** (TEST_CASES/)
   - Concrete test scenarios derived from stories
   - Format: "Test ID, Steps, Expected Result, Status"
   - Mapped to acceptance criteria

5. **Test Plans** (TESTING/TEST_PLANS/)
   - Strategy for testing each feature
   - Coverage goals and test schedule
   - Resource allocation

6. **Test Reports** (TESTING/TEST_REPORTS/)
   - Execution results and metrics
   - Pass/fail counts, coverage percentages
   - Issues found and their status

### Analysis & Findings
7. **Traceability Matrix** (TRACEABILITY/)
   - Maps requirement → user story → test case
   - Ensures nothing is missed or orphaned

8. **Audit Report** (FINDINGS/)
   - Gap analysis (coverage holes)
   - Inconsistencies (contradictions)
   - Recommendations (how to fix)

## 🎯 Naming Conventions

### Requirement IDs
- `REQ-001` to `REQ-999` (general requirements)
- `NFREQ-001` to `NFREQ-999` (non-functional)

### User Story IDs
- `AS-001` to `AS-999` (admin system stories)
- `GS-001` to `GS-999` (generation system stories)

### Acceptance Criteria IDs
- `AC-101` to `AC-199` (admin panel AC)
- `AC-201` to `AC-299` (generation AC)

### Test Case IDs
- `TC-101` to `TC-199` (admin panel tests)
- `TC-201` to `TC-299` (generation tests)

### Test Plan/Report IDs
- `TP-001` to `TP-999` (test plans)
- `TR-001` to `TR-999` (test reports)

## 📊 Traceability Example

```
REQ-2.1 (Image Upload)
  ├─ AS-001: User uploads single image
  │   ├─ AC-101: File type validation
  │   │   └─ TC-101: Test PNG upload
  │   │   └─ TC-102: Test invalid format
  │   └─ AC-102: File size validation
  │       └─ TC-103: Test max size
  └─ AS-002: User uploads batch (5+ images)
      ├─ AC-103: Batch handling
      │   └─ TC-104: Test 5-image batch
      └─ AC-104: Progress tracking
          └─ TC-105: Test progress indicator
```

## ✅ Document Checklist

### For Each Requirement
- [ ] Has requirement ID (REQ-xxx)
- [ ] Clearly written and unambiguous
- [ ] Has 1+ user stories mapped to it
- [ ] Non-functional requirements separate (NFREQ-xxx)
- [ ] Related to at least one test case

### For Each User Story
- [ ] Has story ID (AS-xxx or GS-xxx)
- [ ] Follows INVEST principles (Independent, Negotiable, Valuable, Estimable, Small, Testable)
- [ ] Has 2-5 acceptance criteria
- [ ] Acceptance criteria are testable
- [ ] Has traceability to requirement
- [ ] Has traceability to test cases

### For Each Acceptance Criterion
- [ ] Has AC ID (AC-xxx)
- [ ] Is testable (pass/fail)
- [ ] No vague language ("correctly", "properly")
- [ ] Covers happy path, edge cases, error conditions
- [ ] Has 1+ test cases mapped

### For Each Test Case
- [ ] Has TC ID (TC-xxx)
- [ ] Clear steps to reproduce
- [ ] Expected result defined
- [ ] Mapped to acceptance criterion
- [ ] Includes setup/teardown
- [ ] Includes edge cases/error scenarios

## 🔍 Document Review Checklist

### Requirements Quality
- [ ] No duplicate requirements
- [ ] No empty/placeholder requirements
- [ ] All requirements have clear acceptance criteria
- [ ] No contradictory requirements
- [ ] Requirements are prioritized (MVP vs. nice-to-have)

### User Story Quality
- [ ] All stories follow "As a... I want... So that..." format
- [ ] All stories are INVEST-compliant
- [ ] No overlapping stories
- [ ] Clear dependency chains
- [ ] Proper complexity estimation

### Test Case Quality
- [ ] All acceptance criteria have test cases
- [ ] No orphaned test cases
- [ ] Tests are independent (no dependencies)
- [ ] Tests are repeatable
- [ ] Expected results are clear and objective

### Traceability
- [ ] All requirements → user stories (1:many)
- [ ] All user stories → requirements (many:1)
- [ ] All user stories → test cases (1:many)
- [ ] All acceptance criteria → test cases (1:many)
- [ ] No orphaned documents

## 📈 Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Requirements defined | 100% | TBD | 🔄 |
| User stories written | 100% | TBD | 🔄 |
| Acceptance criteria | 2-5 per story | TBD | 🔄 |
| Test case coverage | 100% | TBD | 🔄 |
| Traceability matrix complete | 100% | TBD | 🔄 |

## 🚀 Next Steps

1. **Audit Phase** (in progress)
   - Review all existing requirements documents
   - Identify gaps, duplicates, inconsistencies
   - Create audit report

2. **Reorganization Phase** (next)
   - Separate requirements from test plans/findings/reports
   - Create FEATURES/ and USER_STORIES/ documents
   - Extract acceptance criteria into separate file

3. **User Story Phase** (next)
   - Write user stories for each requirement
   - Ensure INVEST compliance
   - Map to requirements

4. **Test Case Phase** (next)
   - Write test cases for each acceptance criterion
   - Ensure test coverage
   - Create test plans

5. **Traceability Phase** (next)
   - Build traceability matrix
   - Verify all mappings
   - Document coverage gaps

6. **Review Phase** (final)
   - Review with team
   - Approve final versions
   - Archive old documents

## 📚 Related Documents

- `TESTING_AND_REQUIREMENTS_INDEX.md` — Overview of all requirements
- `tests/e2e/` — E2E test implementation
- `ADMIN_CONSOLE_REQUIREMENTS.md` — Original admin console spec
- `NONOGRAM_GENERATION_REQUIREMENTS.md` — Original algorithm spec

---

**Status**: Framework created, reorganization in progress ✅  
**Last Updated**: 2026-09-08
