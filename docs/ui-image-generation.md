# Nonogram Web UI — Image-Based Generation Requirements (CLI `serve` Interface)

## 1. Overview

This document specifies the web UI for **image-based nonogram puzzle generation**, as implemented by the CLI's `nonogram serve` command. The interface is server-side rendered HTML with minimal JavaScript for client-side metadata calculation (aspect ratio, dimension suggestions).

**Scope:** Image-only generation (supports only `--mode image` from CLI). All output formats match CLI behavior exactly.

**Architecture:**
- Server-rendered HTML form (no SPA, no Next.js)
- Python Flask/CLI backend handling form submission
- Client-side JavaScript (`metadata.js`) for instant metadata + suggestions (no server round-trip)
- Direct integration with nonogram CLI generation pipeline

**Key constraint:** UI behavior and form fields **must match the CLI's `--mode image` argument set exactly**, to ensure web submission produces identical results to CLI invocation.

## 2. Form Layout & Fields

### 2.1 Image Upload Section

**UI-IG-001: File Input**
- Label: "Image"
- Helper: "select the picture to convert"
- Type: `<input type="file" name="image">`
- Accepts: PNG, JPEG, GIF, WebP, BMP, TIFF (raster only, no SVG)
- No file size limit enforced on client (server validates)
- Behavior: On file select, trigger `metadata.js` to calculate dimensions and suggestions

**UI-IG-002: Image Preview Container**
- Display area: `#image-preview-container` (hidden by default, visible when image selected)
- Shows: `<img id="image-preview">` (max 200×200px) + dimensions label
- Dimensions label: `#image-dimensions` — displays "W × H" format
- Updated: When user selects file (instant via FileReader)
- Persisted: On error/retry, image stays shown if validation succeeded

### 2.2 Image Metadata & Suggestions (Client-Side, CARD-034)

**UI-IG-003: Aspect Ratio Display**
- Element: `#metadata-suggestions-area` (dynamically populated)
- Shows: "Image aspect ratio: W:H (decimal)"
  - Example: "Image aspect ratio: 16:9 (1.78)"
  - Format: simplified ratio + decimal (2 places)
- Calculated: `simplifyRatio(width, height)` via GCD algorithm
- Updated: Instantly when image selected (no server call)

**UI-IG-004: Dimension Suggestions (2-3 buttons)**
- Heading: "Suggested dimensions (click to set):"
- Shows: Top 2–3 grid sizes matching the image's aspect ratio
- Algorithm (matches server exactly, AC-137):
  1. Enumerate all (w, h) pairs where 10 ≤ w, h ≤ 30
  2. Compute `ratioError = |gridRatio - imageRatio| / imageRatio` for each
  3. Sort by error (lowest first)
  4. Return top 2–3 candidates
- Button styling: `.suggestion-button` (light gray, inline-block, small font)
- Behavior on click:
  - Populate `input[name="size"]` with value like "20x30"
  - No form submission
  - Focus remains on page

**UI-IG-005: Size Input Field**
- Label: "Size"
- Input: `<input type="text" name="size">`
- Helper: "optional. One number for the grid's longer side (the other side follows the image's own shape), or WxH for exact width and height, e.g. 20x30"
- Format: "20" (square) or "20x30" (exact W×H)
- Placeholder: "e.g., 20 or 20x30"
- Validation: Server-side (not client-validated to match CLI flexibility)
- Populated by: Suggestion buttons (AC-136) OR user manual entry
- Cleared on: New image selection (AC-149, prevents stale size from previous image)

### 2.3 Export Configuration

**UI-IG-006: Export Formats (Checkboxes)**
- Label: "Export" section, "Formats" fieldset
- Options: JSON, PNG, SVG, CSV, PDF
- Defaults: PDF checked, others unchecked
- Layout: Inline labels with checkboxes (one per line or inline)
- At least one required: Server validates; form rejects if none checked
- Example form:
  ```html
  <fieldset>
    <legend>Formats</legend>
    <label><input type="checkbox" name="export_formats" value="json"> json</label>
    <label><input type="checkbox" name="export_formats" value="png"> png</label>
    <label><input type="checkbox" name="export_formats" value="svg"> svg</label>
    <label><input type="checkbox" name="export_formats" value="csv"> csv</label>
    <label><input type="checkbox" name="export_formats" value="pdf" checked> pdf</label>
  </fieldset>
  ```

**UI-IG-007: Output Directory (Optional)**
- Label: "Output directory"
- Input: `<input type="text" name="out">`
- Placeholder: "."
- Helper: "defaults to the working directory"
- Default: "." (current directory)
- Validation: Server trusts user input (path is user-controlled, no sanitization)
- Example values: "." (cwd), "/tmp/puzzles", "~/Desktop"

### 2.4 Puzzle Settings

**UI-IG-008: Difficulty**
- Label: "Difficulty"
- Input: `<select name="difficulty">`
- Options: "(any)" [selected], "easy", "medium", "hard"
- Default: "(any)" (empty string or special "any" value)
- Behavior: Passed to orchestrator; filters/regenerates until difficulty matches

**UI-IG-009: Puzzle Name (Optional)**
- Label: "Name"
- Input: `<input type="text" name="name">`
- Placeholder: "(auto-generated if empty)"
- Helper: "shown on the printed page"
- Default: Empty (server generates from image filename or timestamp)
- Example: "my_puzzle" (no spaces, sanitized)

**UI-IG-010: Seed (Optional, Numeric)**
- Label: "Seed"
- Input: `<input type="text" name="seed" inputmode="numeric">`
- Placeholder: "(random if empty)"
- Helper: "for a reproducible puzzle"
- Default: Empty (random seed generated by server)
- Validation: Server accepts any integer; Python `random.Random()` handles it

## 3. Form Structure (Grid Layout)

```
┌─────────────────────────────────────┐
│ Image Preview (left column)         │
│ Metadata & Suggestions (right col)  │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Form Grid (2 columns, desktop)      │
├──────────────┬──────────────────────┤
│ Image field  │ Size field           │ (row 1)
├──────────────┼──────────────────────┤
│ Export       │ Puzzle Settings      │ (row 2)
│ Formats      │ (Difficulty, Name,   │
│ Out Dir      │  Seed)               │
└──────────────┴──────────────────────┘
```

**Responsive:** On mobile (≤768px), form grid becomes single column.

## 4. Form Submission

**UI-IG-011: Submit Button**
- Label: "Generate"
- Type: `<button type="submit">`
- Action: POST to `/generate` with `enctype="multipart/form-data"`
- Disabled: Never (form always submittable)
- Loading: Form cleared, button shows "Generating..." (optional, server-controlled)

**UI-IG-012: Hidden Fields**
- `<input type="hidden" name="persisted_image_path" value="">`
- `<input type="hidden" name="persisted_image_filename" value="">`
- Purpose: Store image path/filename on retry for image persistence (AC-163, CARD-037)

**UI-IG-013: Form Data Serialization**
- Enctype: `multipart/form-data`
- Fields submitted:
  - `image`: File (binary)
  - `size`: String ("20" or "20x30", optional)
  - `export_formats`: Array (checked values: json, png, svg, csv, pdf)
  - `out`: String (optional, default ".")
  - `difficulty`: String ("" / "any" / "easy" / "medium" / "hard")
  - `name`: String (optional)
  - `seed`: String (numeric, optional)
  - `persisted_image_path`: String (retry scenario)
  - `persisted_image_filename`: String (retry scenario)

## 5. Result Display & Error Handling

**UI-IG-014: Result Container**
- Element: `<div data-result-container="true"></div>` (cleared on new form submit)
- Populated by: Server response (HTML snippet injected by server or JavaScript)

**UI-IG-015: Success Message**
- Background: Green (#28a745, #51cf66 in dark mode)
- Border: Left 3px green bar
- Class: `.outcome-success`
- Content:
  - Heading: "Success" or checkmark icon
  - Message: "Puzzle generated successfully"
  - Details: Name, seed, files generated
  - Links: Download each file (href depends on server implementation)
  - Call-to-action: "Generate another puzzle or upload a new image"

**UI-IG-016: Error Message**
- Background: Red (#dc3545, #ff6b6b in dark mode)
- Border: Left 3px red bar
- Class: `.outcome-failure`
- Content:
  - Heading: "Error" or error icon
  - Message: Error text from server
  - Common errors:
    - "Image does not yield a unique solution. Try a different size or image."
    - "Grid size must be between 10×10 and 30×30."
    - "File could not be processed."
    - "No export formats selected."
  - Recovery: "Try adjusting settings and re-submit." (form stays enabled)

**UI-IG-017: Image Persistence on Error (AC-163, CARD-037)**
- On error, if image upload was valid:
  - Server saves image to temp location (disk or memory)
  - Returns `persisted_image_path` and `persisted_image_filename` in response
  - Client stores values in hidden form fields
  - On page reload/retry, image preview is restored (via `initializePersistedPreview()`)
  - Suggestion buttons are recalculated and displayed
- Benefit: User can retry with different size/settings without re-uploading image
- Lifetime: Single session; cleared on successful generation or explicit "upload new image"

## 6. Client-Side JavaScript (metadata.js)

### 6.1 Image Metadata Extraction (AC-135)

**Function: `extractImageMetadata(file) → Promise`**
- Input: File object from `<input type="file">`
- Process:
  1. FileReader.readAsDataURL() → data URL
  2. Create Image element, load from data URL
  3. Extract `width` and `height` from Image.naturalWidth/Height
  4. Calculate simplified aspect ratio via GCD algorithm
  5. Calculate decimal representation (e.g., 1.78)
- Output: `{width, height, aspectRatio: {width, height, decimal}}`
- Error: Reject with message ("Could not read image dimensions")
- Performance: < 100ms on typical laptop

### 6.2 Dimension Suggestions (AC-137)

**Function: `suggestDimensions(metadata, minSize=10, maxSize=30) → Array`**
- Algorithm (exact match to `metadata.py` server-side, AC-137):
  ```
  1. For w from 10 to 30:
       For h from 10 to 30:
         gridRatio = w / h
         ratioError = |gridRatio - imageRatio| / imageRatio
         suggestions.push([ratioError, [w, h]])
  2. Sort by ratioError (ascending)
  3. Return top 2-3 candidates
  ```
- Output: Array of [w, h] pairs, e.g., `[[20, 25], [18, 24]]`
- Test: Cross-checked against server in test harness; deviation ≥ 1 cell → test fails

### 6.3 Form Update (AC-135, AC-136)

**Function: `updateFormWithMetadata(metadata, suggestions)`**
- Updates `#metadata-suggestions-area` with:
  - Metadata block: Aspect ratio display
  - Suggestion buttons: One button per suggested size
- Attaches click handlers to buttons:
  - On click: Set `input[name="size"]` to "WxH" format
  - No form submission
  - No page reload

### 6.4 Image Preview (AC-158, AC-159, AC-160)

**Function: `displayImagePreview(metadata)`**
- Reads file via FileReader.readAsDataURL()
- Sets `img#image-preview.src` to data URL
- Sets `div#image-dimensions.textContent` to "W × H" format
- Shows `#image-preview-container` (adds `.visible` class)
- Max dimensions: 200×200px (CSS `max-width`, `max-height`)

### 6.5 Event Handlers

**File Input Change Handler:**
- Triggered: When user selects new image
- Actions:
  1. Call `clearResultMessage()` (AC-166, CARD-043: clear old errors)
  2. Call `clearSizeField()` (AC-149: prevent stale size)
  3. Verify file is image (check `file.type.startsWith("image/")`)
  4. Call `extractImageMetadata(file)` asynchronously
  5. Call `suggestDimensions(metadata)` (if extraction succeeds)
  6. Call `updateFormWithMetadata(metadata, suggestions)` (populate form)
  7. On error: Clear metadata, log to console, do not block submission

**Form Submit Handler:**
- Triggered: When form submitted
- Actions:
  1. Clear `[data-result-container]` contents
  2. Submit form normally to `/generate`
  3. Server handles form processing and renders response

**Persisted Image Initialization (AC-163):**
- Triggered: On page load, if `input[name="persisted_image_path"]` is non-empty
- Actions:
  1. Read metadata from `<script data-image-metadata>` tag (if present)
  2. Call `showImagePreview()` with persisted metadata
  3. Calculate suggestions from persisted image dimensions
  4. Populate `#metadata-suggestions-area` with suggestions
  5. Attach click handlers to suggestion buttons
- Benefit: On error/retry, image and suggestions visible without server round-trip

## 7. Non-Functional Requirements

**NFR-UI-1: Responsiveness**
- Desktop (≥768px): 2-column form grid
- Mobile (<768px): Single-column layout (stacked form fields)
- Preview section: 2-column on desktop, 1-column on mobile
- Touch-friendly: Buttons ≥44px height, adequate spacing

**NFR-UI-2: Accessibility**
- All labels properly associated with inputs via `<label>` tag
- Color contrast: WCAG AA (4.5:1 text/background)
- Keyboard navigation: Tab through inputs, Enter to submit
- Screen reader: Form labels announced, error messages available
- No required visual-only cues (icons used with text labels)

**NFR-UI-3: Performance**
- Metadata extraction: < 100ms (JavaScript, client-side)
- Dimension suggestions: Instant (< 50ms, 441 pairs evaluated, 10-30 range)
- Form submission: No client-side blocking, POST direct to server
- Image preview: Max 200×200px displayed (low bandwidth)
- No external dependencies (pure HTML/CSS/JS, no framework)

**NFR-UI-4: Browser Compatibility**
- Requires: FileReader API, Image element, ES5+ JavaScript
- Supports: Chrome 90+, Firefox 88+, Safari 15+, Edge 90+
- Mobile: iOS Safari 15+, Chrome Android 90+
- Fallback: If File API unavailable, clear metadata but allow form submission

**NFR-UI-5: Security**
- XSS protection: HTML escape user input via `.textContent` (not `.innerHTML` except server-generated)
- CSRF: Form submission is POST to `/generate`; server validates CSRF token if required
- File upload: Server validates file type, size, magic number (client-side check for UX only)

**NFR-UI-6: Styling (CSS Variables)**
- Light mode (default):
  - `--text-primary: #000`
  - `--bg-primary: #fff`
  - `--border-color: #ccc`
  - `--button-bg: #007bff`
  - Success: `#28a745`, Error: `#dc3545`
- Dark mode (prefers-color-scheme):
  - `--text-primary: #e0e0e0`
  - `--bg-primary: #1a1a1a`
  - `--border-color: #444`
  - `--button-bg: #0d6efd`
  - Success: `#51cf66`, Error: `#ff8a8a`

## 8. Acceptance Criteria (AC-UI-IG-001 through AC-UI-IG-032)

### Image Upload & Metadata (AC-UI-IG-001 to AC-UI-IG-010)

| AC ID | Requirement | Test Scenario | Expected Result |
|-------|-------------|---------------|-----------------|
| AC-UI-IG-001 | File input accepts raster formats | Upload PNG/JPEG/GIF/WebP/BMP | Image accepted, preview shown |
| AC-UI-IG-002 | Invalid format rejected | Upload SVG or PDF | Error displayed, no preview |
| AC-UI-IG-003 | Image dimensions extracted | Upload 1600×800 image | Shown in preview: "1600 × 800" |
| AC-UI-IG-004 | Aspect ratio calculated | 1600×800 image uploaded | Display "2:1 (2.00)" |
| AC-UI-IG-005 | GCD simplification works | 1024×768 image | Display "4:3 (1.33)" (simplified) |
| AC-UI-IG-006 | Suggestions match algorithm | 16:9 image | Top 3 include sizes with ~1.78 ratio |
| AC-UI-IG-007 | Suggestions are clickable | Click "20×25" suggestion | Size field populated with "20x25" |
| AC-UI-IG-008 | Size field cleared on new upload | Select image, change size, upload new image | Size field becomes empty |
| AC-UI-IG-009 | Image preview displays | Upload image | Preview visible, max 200×200px |
| AC-UI-IG-010 | Metadata instant (no server call) | Select image | Preview + suggestions appear < 100ms |

### Size & Configuration (AC-UI-IG-011 to AC-UI-IG-020)

| AC ID | Requirement | Test Scenario | Expected Result |
|-------|-------------|---------------|-----------------|
| AC-UI-IG-011 | Size field accepts "20" format | Enter "20" | Submitted as-is to server |
| AC-UI-IG-012 | Size field accepts "20x30" format | Enter "20x30" | Submitted as-is to server |
| AC-UI-IG-013 | Placeholder shown when empty | Size field empty | Placeholder "e.g., 20 or 20x30" visible |
| AC-UI-IG-014 | Export formats: PDF default | Form load | PDF checkbox checked, others unchecked |
| AC-UI-IG-015 | Export formats multi-select | Check JSON, PNG, PDF | All three values in form data array |
| AC-UI-IG-016 | Difficulty dropdown functional | Select "easy" | Value "easy" submitted |
| AC-UI-IG-017 | Name field optional | Leave empty | Server uses auto-generated name |
| AC-UI-IG-018 | Seed field numeric | Enter "12345" | Submitted to server |
| AC-UI-IG-019 | Output directory optional | Leave empty (or ".") | Server uses CWD |
| AC-UI-IG-020 | Output directory accepts paths | Enter "./puzzles" | Path passed to CLI unchanged |

### Form Submission & Results (AC-UI-IG-021 to AC-UI-IG-032)

| AC ID | Requirement | Test Scenario | Expected Result |
|-------|-------------|---------------|-----------------|
| AC-UI-IG-021 | Form submits via POST | Click "Generate" | POST to `/generate` with FormData |
| AC-UI-IG-022 | Success message displayed | Generation succeeds | Green success card shown |
| AC-UI-IG-023 | Success shows name & seed | Generation succeeds | Displays name, seed value |
| AC-UI-IG-024 | Download links provided | Success response | Links to PNG, JSON, etc. visible |
| AC-UI-IG-025 | Error message displayed | Generation fails | Red error card shown |
| AC-UI-IG-026 | Error shows reason | Invalid size (50x50) | Error: "Grid size must be..." |
| AC-UI-IG-027 | Error card clearable | Errors shown, new file selected | Error card removed (AC-166) |
| AC-UI-IG-028 | Form reusable after error | Generation fails | Form fields still enabled, can re-submit |
| AC-UI-IG-029 | Image persisted on error | Error on first try | Image cached in hidden fields |
| AC-UI-IG-030 | Preview restored on retry | Page reloaded with persisted image | Image preview visible, suggestions shown |
| AC-UI-IG-031 | Suggestions match persisted image | Retry with persisted image | Suggestion buttons match image ratio |
| AC-UI-IG-032 | Results container cleared on submit | Old success, new generation | Old result cleared before new submit |

## 9. Implementation Status

### ✅ Already Implemented (from `nonogram serve`)

- Server-rendered HTML form with all fields
- CSS styling (dark/light mode support)
- `metadata.js`: Image extraction, aspect ratio, dimension suggestions
- File input and preview container
- Export format checkboxes (PDF default)
- Form submission to `/generate`
- Success/error result display (colored cards)
- Image persistence on error (hidden fields)
- Persisted preview restoration on load

### 🔧 Potential Enhancements (v1.1+)

- Add image drag-and-drop upload
- Show spinner during generation
- Live image crop preview (show exact region that will be converted)
- Difficulty indicator (e.g., slider or "complexity: medium")
- Batch generation (multiple sizes from one image)
- Save puzzle to library (with tags/search)

## 10. Testing Strategy

### Unit Tests (JavaScript)
- `metadata.js`: Image extraction, GCD ratio simplification, suggestion algorithm
- Cross-check: Client suggestions match Python `metadata.py` exactly
- Test corpus: Known aspect ratios (16:9, 4:3, 1:1, extreme 30:1)

### Integration Tests (Form Submission)
- Form + server: Upload image → suggestions → modify size → submit → success/error
- Error recovery: Fail → retry with different size → succeed
- Image persistence: Error → page reload → suggestions visible → retry

### E2E Tests (Browser Automation)
- Full workflow: Upload image → see preview + suggestions → click suggestion → submit → download file
- Mobile responsiveness: Verify form layout on mobile screen sizes
- Accessibility: Keyboard navigation, screen reader announcements

### Manual Testing
- Real image uploads (photographs, drawings, document scans)
- Edge cases: Very small images, extreme aspect ratios, large images
- Dark mode rendering and color contrast

## 11. References & Related

- **CLI command:** `nonogram serve --port 8765`
- **Generated output:** Matches `nonogram generate --mode image` exactly
- **Kanban cards:** CARD-034 (metadata), CARD-037 (image persistence), CARD-043 (result clearing)
- **Python modules:** `nonogram.web.pages`, `nonogram.sourcing.metadata`
- **Acceptance criteria:** AC-135 through AC-166, cross-referenced in kanban cards

---

**Document Version:** 2.0 (revised, reverse-engineered from `nonogram serve`)  
**Last Updated:** 2026-09-05  
**Scope:** CLI web interface (`nonogram serve`), image generation only  
**Status:** Ready for test harness implementation
