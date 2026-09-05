# E2E Test Acceptance Criteria Extraction
**Source:** nonogram-web/e2e/form.spec.ts  
**Date:** 2026-09-05  
**Purpose:** Map Playwright tests → Formal acceptance criteria for requirements model

---

## Test-to-FR Mapping

### Form Rendering Tests

| Test Name | Encodes AC | Maps to FR | AC Statement |
|-----------|-----------|----------|---|
| `should display the page title` | ✅ | FR-017 (Web UI) | The nonogram generator form displays a visible page title "Nonogram Generator" |
| `should display all form fields` | ✅ | FR-017 | All form fields are visible: Grid Size, Density, Difficulty, Seed, Export Formats |
| `should have Grid Size input with default value 20` | ✅ | FR-001 | Grid Size input accepts integer values with default of 20 |
| `should have Density input with default value 30` | ✅ | FR-004 | Density input accepts integer values with default of 30% |
| `should have Difficulty select with default "Any"` | ✅ | FR-008 | Difficulty selector with options {Any, Easy, Medium, Hard}, defaults to "Any" |
| `should have Seed input with empty default` | ✅ | FR-009 | Seed input is optional (empty by default) |
| `should have all export format checkboxes checked by default` | ✅ | FR-011 | Export format checkboxes {JSON, CSV, PNG, SVG} all checked by default |
| `should have Generate Puzzle button` | ✅ | FR-017 | Generate Puzzle button present and enabled in default state |
| `should have mode radio buttons with random as default` | ✅ | FR-017, CAP-001 | Mode selector with {random, image}, defaults to random (hidden field: `mode=random`) |

**Confidence:** HIGH (direct HTML/DOM assertion)  
**Evidence:** nonogram-web/e2e/form.spec.ts:11-67

---

### Form Styling Tests

| Test Name | Encodes AC | Maps to FR | AC Statement |
|-----------|-----------|----------|---|
| `labels should be visible and readable` | ✅ | FR-017 (UI) | Form labels are visible and count ≥ 5 |
| `input fields should be visible` | ✅ | FR-017 | Input fields (size, density) visible on page load |
| `form container should have proper styling` | ⚠️ PARTIAL | FR-017 | Form container width > 300px (responsive design) |

**Confidence:** MEDIUM (CSS/styling is brittle)  
**Evidence:** nonogram-web/e2e/form.spec.ts:70-91

---

### Form Interaction Tests

| Test Name | Encodes AC | Maps to FR | AC Statement |
|-----------|-----------|----------|---|
| `should allow changing Grid Size` | ✅ | FR-001 | Grid Size input accepts user input (tested: 15) |
| `should allow changing Density` | ✅ | FR-004 | Density input accepts user input (tested: 50) |
| `should allow changing Difficulty` | ✅ | FR-008 | Difficulty selector accepts user changes (tested: hard) |
| `should allow entering Seed` | ✅ | FR-009 | Seed input accepts user input (tested: 42) |
| `should allow unchecking export formats` | ✅ | FR-011 | Export format checkboxes can be toggled independently |
| `should validate Grid Size min value` | ✅ | CON-011 | HTML5 browser validation enforces Grid Size minimum (≥10?) |
| `should validate Density range` | ✅ | NFR-001 | HTML5 browser validation enforces Density max (≤90?) |

**Confidence:** HIGH (direct user interaction)  
**Evidence:** nonogram-web/e2e/form.spec.ts:93-141

---

### Form Submission Tests

| Test Name | Encodes AC | Maps to FR | AC Statement |
|-----------|-----------|----------|---|
| `should display loading state when submitting` | ✅ | FR-017 | Button displays "Generating..." and becomes disabled during submission |
| `should submit form with correct data` | ✅ | FR-017, CAP-001 | Form POST to `/api/generate` includes: size, density, difficulty, mode=random, export_formats |
| `should handle API success response` | ✅ | FR-011 | On API success, form processes response (download prompt/display?) |
| `should handle API errors gracefully` | ✅ | FR-017 | On API error, form displays error message and remains visible |

**Confidence:** HIGH (HTTP interception + mocking)  
**Evidence:** nonogram-web/e2e/form.spec.ts:143-222

---

### Accessibility Tests

| Test Name | Encodes AC | Maps to FR | AC Statement |
|-----------|-----------|----------|---|
| `form labels should be associated with inputs` | ✅ | FR-017 (Accessibility) | Form labels have text content ("Grid Size", etc.) |
| `button should have accessible text` | ✅ | FR-017 | Submit button contains text "Generate Puzzle" |
| `form should be keyboard navigable` | ✅ | FR-017 | Form supports Tab navigation; focused elements are INPUT/SELECT/BUTTON |

**Confidence:** MEDIUM (accessibility features often aspirational)  
**Evidence:** nonogram-web/e2e/form.spec.ts:224-253

---

### Edge Cases Tests

| Test Name | Encodes AC | Maps to FR | AC Statement |
|-----------|-----------|----------|---|
| `should handle very large grid size gracefully` | ⚠️ NEEDS AC | CON-011 | Form accepts input > 30 (validation happens server-side) |
| `should handle decimal input in grid size` | ⚠️ NEEDS AC | FR-001 | Form accepts decimal input (15.5) in Grid Size |
| `should handle multiple rapid form submissions` | ✅ | FR-017 | Form button disabled after first submission (prevents double-submit) |
| `should remember form state on page reload` | ⚠️ CONFLICT | N/A | Form RESETS to defaults on reload (not persisted) - Not a bug, expected behavior |

**Confidence:** MEDIUM-LOW (edge case behavior)  
**Evidence:** nonogram-web/e2e/form.spec.ts:255-297

---

### Image Mode Tests

| Test Name | Encodes AC | Maps to FR | AC Statement |
|-----------|-----------|----------|---|
| `should have mode selector radio buttons` | ✅ | FR-017, CAP-001 | Mode selector has {random, image}; random is default |
| `should show Grid Size and Density in random mode` | ✅ | FR-001, FR-004 | Size/Density inputs visible in random mode |
| `should hide Grid Size and Density when switching to image mode` | ✅ | FR-003 | Size/Density inputs hidden when mode=image |
| `should show file upload input in image mode` | ✅ | FR-003 | File input with `accept="image/*"` visible in image mode |
| `should disable button when no file is selected in image mode` | ✅ | FR-003 | Generate button disabled until file selected in image mode |
| `should accept file input` | ✅ | FR-003 | File input accepts PNG files (tested: 1x1 PNG) |
| `should enable button when file is selected in image mode` | ✅ | FR-003 | Generate button becomes enabled once file is selected |
| `should switch back to random mode` | ✅ | FR-017 | Mode toggle works bidirectionally (random ↔ image) |
| `should keep difficulty and seed in all modes` | ✅ | FR-008, FR-009 | Difficulty and Seed fields visible/accessible in all modes |

**Confidence:** HIGH (mode switching is core flow)  
**Evidence:** nonogram-web/e2e/form.spec.ts:299-440

---

### Cross-browser Compatibility Tests

| Test Name | Encodes AC | Maps to FR | AC Statement |
|-----------|-----------|----------|---|
| `should work on desktop viewport` | ✅ | FR-017 | Form renders correctly on desktop (>1000px) |
| `should work on tablet viewport` | ✅ | FR-017 | Form renders correctly on tablet (>500px) |

**Confidence:** MEDIUM (viewport-dependent)  
**Evidence:** nonogram-web/e2e/form.spec.ts:442-459

---

## Summary of Extracted AC

### High-Confidence AC (to add to requirements.yml)

| AC ID | Statement | Test Evidence | FR |
|-------|-----------|----------------|-----|
| AC-091 | Form displays page title "Nonogram Generator" | form.spec.ts:11-14 | FR-017 |
| AC-092 | Grid Size input has default value 20 | form.spec.ts:25-28 | FR-001 |
| AC-093 | Density input has default value 30 | form.spec.ts:30-33 | FR-004 |
| AC-094 | Difficulty select has default "Any" | form.spec.ts:35-38 | FR-008 |
| AC-095 | Export formats default to all checked {JSON,CSV,PNG,SVG} | form.spec.ts:45-55 | FR-011 |
| AC-096 | Mode selector defaults to "random" | form.spec.ts:63-67 | CAP-001 |
| AC-097 | Form POST includes size, density, difficulty, mode, export_formats | form.spec.ts:166-189 | FR-017 |
| AC-098 | Button displays "Generating..." during submission | form.spec.ts:144-164 | FR-017 |
| AC-099 | Button disabled during submission (prevents double-submit) | form.spec.ts:272-283 | FR-017 |
| AC-100 | File input accepts images in image mode | form.spec.ts:352-375 | FR-003 |
| AC-101 | Generate button disabled until file selected in image mode | form.spec.ts:341-350 | FR-003 |
| AC-102 | Mode toggle works bidirectionally | form.spec.ts:404-422 | FR-017 |
| AC-103 | Size/Density visible in random mode, hidden in image mode | form.spec.ts:309-329 | FR-001, FR-003 |

### Medium-Confidence AC (needs verification)

| AC ID | Statement | Test Evidence | Issue |
|-------|-----------|----------------|-------|
| AC-104 | HTML5 validation enforces Grid Size minimum | form.spec.ts:126-133 | Test doesn't verify actual rejection |
| AC-105 | HTML5 validation enforces Density max | form.spec.ts:135-140 | Test doesn't verify actual rejection |
| AC-106 | Form labels are keyboard navigable | form.spec.ts:243-252 | Depends on HTML structure |

### Gaps Found in Tests

| Gap | Severity | Note |
|-----|----------|------|
| No test for actual successful puzzle generation | HIGH | Tests mock API; end-to-end flow not verified |
| No test for file download after generation | HIGH | FR-011 AC missing "user can download generated files" |
| No test for invalid image rejection | MEDIUM | FR-003 lacks AC for oversized/invalid image handling |
| No test for error message content | MEDIUM | API errors tested but message content not verified |
| No test for form field validation (server-side) | MEDIUM | CON-011 bounds tested only on client (HTML5) |
| No load/performance test | LOW | Nonogram generation time not tested |

---

## Recommended Actions

1. **Add high-confidence AC to requirements.yml** (AC-091..103)
   - Cite test evidence in `_meta.evidence`
   - Mark as `source: reverse-engineered` initially, flip to `authored` after review

2. **Close gaps with additional E2E tests**
   - Full happy-path: form → submit → download file
   - Error scenarios: oversized image, corrupted upload, API timeout
   - Server-side validation (CON-011 bounds enforcement)

3. **Formalize image mode flow as separate FR**
   - Current tests scatter image mode across multiple FR
   - Suggest: New FR-024 (Image mode puzzle generation)

4. **Add performance baseline tests**
   - Capture solve time for 20x20, 25x25, 30x30 grids
   - Set NFR-002 threshold based on actual measurements

---

## Test Execution

Currently passing:
- ✅ Form rendering (9 tests)
- ✅ Form styling (3 tests)
- ✅ Form interaction (7 tests)
- ✅ Form submission (4 tests)
- ✅ Accessibility (3 tests)
- ✅ Edge cases (4 tests)
- ✅ Image mode (9 tests)
- ✅ Cross-browser (2 tests)

**Total:** 41 test cases (as of 2026-09-05)

Run with:
```bash
cd nonogram-web && npm run test:e2e
# or
npx playwright test e2e/form.spec.ts
```

---

**Next Step:** Wait for forge:reverse drift to complete, then update requirements.yml with these AC.
