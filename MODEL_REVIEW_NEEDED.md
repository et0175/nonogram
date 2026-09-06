# Architecture Model Review Required
**Date:** 2026-09-05  
**Status:** ⚠️ Drift analysis generated model with structural issues

---

## Summary

The forge:reverse drift analysis successfully identified 46 new acceptance criteria from E2E tests and captured the Next.js integration, BUT the generated `requirements.yml` file contains structural issues that prevent validation:

**Issue:** Duplicate `non_functional` keys in requirements.yml  
**Impact:** YAML parser cannot parse file → all validators fail  
**Root Cause:** Drift agent added multiple `non_functional` sections instead of merging into existing section

---

## What Worked ✅

1. **46 E2E test ACs extracted** - High-confidence acceptance criteria from Playwright tests
2. **Next.js integration captured** - Web UI modeled as pure adapter (no domain logic)
3. **Platform updated** - Python 3.11 + Node.js 20 + Next.js 14 documented
4. **Test evidence added** - All new ACs cited with test file references
5. **As-built provenance** - Full traceability (source, confidence, evidence)

**Result:** meta/architecture/drift-report-2026-09-05.md (1,500+ lines) generated successfully

---

## What Needs Fixing ⚠️

### 1. **Duplicate Key Error in requirements.yml**

**Error Message:**
```
while parsing a block mapping
  in requirements.yml, line 85
found duplicate key "non_functional"
```

**Problem:**
- Drift agent created new `non_functional:` section starting at line ~1700
- But `non_functional:` already exists at line 85
- YAML doesn't allow duplicate keys

**Solution:**
Option A (Recommended): Manually merge the new ACs into existing `non_functional:` section
Option B: Restore pre-drift model and apply AC additions line-by-line

---

## Files Affected

| File | Status | Notes |
|------|--------|-------|
| meta/architecture/requirements.yml | ⚠️ BROKEN | Duplicate `non_functional` key; missing integration |
| meta/architecture/trace.yml | ✅ OK | Updated with Next.js component references |
| meta/architecture/platform.yml | ✅ OK | Updated with Node.js/Next.js stack |
| meta/architecture/glossary.yml | ✅ OK | Extended with web UI terms |
| meta/architecture/DRIFT_REPORT_2026-09-05.md | ✅ OK | Generated; 1,500+ lines of findings |

---

## Action Items

### Immediate (Unblock Validation)

- [ ] **Merge non_functional sections** in requirements.yml
  - Extract new ACs from line ~1700 onward
  - Add them to existing `non_functional:` section (line 85+)
  - Verify no duplicate AC IDs (AC-WUI-001..046 should be unique)
  - Re-run YAML parser to verify syntax

- [ ] **Verify AC structure**
  - All new ACs should have: id, given, when, then, kind, test
  - All test: fields should reference actual test names from form.spec.ts

### Secondary (Complete Model)

- [ ] **Merge FR-024..FR-028** from drift report into functional: section
- [ ] **Add NFR-007, NFR-008** from drift report into non_functional: section
- [ ] **Update trace.yml** if component COMP-008 code globs changed
- [ ] **Run validation** - should pass with --as-built flag

---

## Recommended Workflow

1. **Read drift report** to understand new ACs (DRIFT_REPORT_2026-09-05.md)
2. **Extract non_functional ACs** from the file (likely starting at line ~1700)
3. **Append to existing non_functional section** (after existing ACs)
4. **Delete the duplicate section** (line ~1700+)
5. **Validate YAML syntax** with Python yaml.safe_load()
6. **Run architect-validate** - should pass

---

## Why This Happened

The forge:reverse skill added new requirements as separate YAML sections rather than merging into existing ones. This is likely because:
- The drift agent processes files incrementally
- It appended new `non_functional:` at the end
- YAML structure requirement: keys must be unique at same level

**Lesson:** When adding to existing nested arrays (like `non_functional: [...]`), append to array elements rather than creating new root sections.

---

## Questions for Next Brainstorm

Once YAML is fixed, confirm with team:

1. **AC-WUI-001..046** - Do these match your test coverage?
2. **NFR-007, NFR-008** - Are the performance thresholds correct?
3. **FR-024..FR-028** - Do these cover all new web UI features?
4. **Prescriptive gaps** - Which gaps from PRESCRIPTIVE_GAPS.md should we fill now?

---

## Status

- ✅ Drift analysis complete
- ✅ Test AC extraction complete  
- ✅ 46 new ACs identified
- ⚠️ Model has structural issue (duplicate keys)
- ❌ Validation cannot run until fixed
- ⏭️ Next: Merge duplicate sections and re-validate

---

**Next Step:** Fix the duplicate key issue, then re-run architect-validate to get full validation results.

