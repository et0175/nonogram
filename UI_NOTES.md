# UI/UX Issues and Observations

## Date: 2026-09-05

### Issue: Image Name and Open Button

**User Report:** "Image name and open button don't work for generated image"

**Investigation Findings:**

#### API Testing Results
- ✅ Puzzle name parameter works correctly
- ✅ File generation returns proper file paths  
- ✅ Open file endpoint (`/api/open-file`) is implemented
- ✅ All export formats work (JSON, PDF, PNG, SVG, CSV)

**Test Examples:**
```bash
# Custom name works
curl -X POST /api/generate \
  -F "name=TestPuzzle" \
  -F "export_formats=pdf"
  
# Response
{
  "name": "TestPuzzle",
  "files": {
    "pdf": "/app/nonogram-web/TestPuzzle-easy.pdf"
  }
}
```

#### Form Component Analysis
**File:** `nonogram-web/app/components/GeneratorForm.tsx`

Name Input (lines 273-279):
- ✅ Properly connected to `customName` state
- ✅ onChange handler updates state
- ✅ Placeholder shows filename automatically
- ✅ Helper text shows when no custom name provided

```typescript
<input
  type="text"
  name="name"
  value={customName}
  onChange={(e) => setCustomName(e.target.value)}
  placeholder={selectedFile ? selectedFile.name.replace(/\.[^.]+$/, '') : 'puzzle'}
/>
```

#### Result Display Component
**File:** `nonogram-web/app/components/ResultDisplay.tsx`

Display Elements (lines 60-61, 82-96):
- ✅ Name displays correctly: `<code>{name}</code>`
- ✅ Open button implemented with `/api/open-file` call
- ✅ Copy path button with visual feedback
- ✅ File list shows all generated formats

#### Potential Issues
1. **Visual Clarity:** The name input might not be obvious to users
2. **Form Submission:** May need to verify name field is being included in FormData for all export format combinations
3. **Image Mode Specific:** Issue might only occur with image uploads (not random mode)
4. **Platform Specific:** The "Open" button behavior depends on platform (macOS/Linux/Windows)

### Recommendations
1. Test image upload + PDF-only export combination specifically
2. Ensure form validation shows if name is empty
3. Add visual indicator for active form field
4. Verify FormData includes all fields before submission

### Status
- ✅ Core functionality working
- ⚠️ Minor UX polish needed
- 🔍 Requires user testing with actual form submission to identify exact issue
