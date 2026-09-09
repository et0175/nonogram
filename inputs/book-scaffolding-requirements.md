# Book Scaffolding Requirements

**Status:** Draft  
**Last updated:** 2026-09-09  
**Scope:** Admin panel feature for assembling nonograms into printable books

---

## Overview

The admin panel needs a new "Book Scaffolding" workflow to let curators assemble approved puzzles into printable books. The workflow guides the user through: print setup → puzzle selection → arrangement → cover/guide → PDF export.

---

## Print Specifications (Constraints)

- **Trim size (default):** 15.24 × 22.86 cm (A5, Amazon KDP standard)
- **Support unit conversion:** cm ↔ inches (1 in = 2.54 cm)
- **Margins** (calculated per page count, implemented in Step 1.2):
  - Inside gutter margin
  - Outside margin
  - Outside margin with bleed
- **Source:** [Amazon KDP printing guide](https://kdp.amazon.com/en_US/help/topic/G202145400)

---

## User Stories & Acceptance Criteria

### Step 1: Print Parameter Setup

**US-BOOK-001:** As a curator, I can configure trim size and unit preference so the book matches print vendor specs.

**Acceptance Criteria:**
- [ ] Print setup form allows input of trim width/height in cm or inches
- [ ] Default trim size is 15.24 × 22.86 cm (A5)
- [ ] Unit preference (cm/inches) persists for the session
- [ ] Form validates that trim size is within printable bounds (min 10×10 cm, max 30×48 cm)

**Note:** Margin calculation (gutter, outside, bleed) deferred to implementation pending page count; surfaced in Step 4.

---

### Step 2: Puzzle Selection

**US-BOOK-002:** As a curator, I can filter and select approved puzzles to add to a book.

**Acceptance Criteria:**
- [ ] Selection panel reuses the puzzle filter UI from `/puzzles` (size, difficulty, theme, status)
- [ ] Filter excludes puzzles already in the current book
- [ ] Puzzles display as tiles: thumbnail/grid preview + size (e.g., "20×24") + difficulty tier + "Add to book" checkbox
- [ ] Checkboxes allow multi-select (can select 1..N puzzles)
- [ ] "Add selected" button at bottom commits selections and moves to arrangement view
- [ ] "Cancel" button discards selections and returns to book editor
- [ ] User can deselect individual puzzles before committing
- [ ] Empty selection is allowed (skip to arrangement with 0 puzzles)

**Non-goals (Step 2):**
- Drag/drop from selection panel (add in Step 3 if needed later)
- Puzzle preview modal (keep lightweight)

---

### Step 3: Puzzle Arrangement

**US-BOOK-003:** As a curator, I can order puzzles in the book and assign titles.

**Acceptance Criteria:**
- [ ] Puzzles display in a list showing: order number (#1, #2, …), puzzle grid preview (thumbnail), size, difficulty
- [ ] Each puzzle has:
  - Up/Down buttons to reorder (move 1 position; wraps around top/bottom disabled)
  - Inline text field: puzzle display title (e.g., "The Rain Deer" or "Cat #3")
  - Delete button to remove from book
- [ ] Order numbers auto-increment as puzzles are reordered
- [ ] Title field persists per puzzle in the book (not the original puzzle record)
- [ ] Page breaks shown as visual dividers (calculated from puzzle heights + trim height; updated live as user adds/removes puzzles)
- [ ] "Next" button advances to Step 4 (cover/guide)
- [ ] "Back" button returns to puzzle selection (with selections preserved)

**Non-goals (Step 3):**
- Drag/drop (up/down buttons sufficient for MVP)
- Multi-select reorder (one puzzle at a time)

---

### Step 4: Finalization & Export

**US-BOOK-004:** As a curator, I can add optional cover/guide pages and download the book as PDF.

**Acceptance Criteria (Cover Page):**
- [ ] Cover page section shows: placeholder "Cover (optional)" UI
- [ ] If no cover uploaded: message "Click to upload or skip"
- [ ] User can upload a pre-built cover image (PNG/JPG, max 10 MB, aspect ratio must match trim size)
- [ ] Uploaded cover displays as preview
- [ ] User can clear/replace cover without re-uploading entire book

**Acceptance Criteria (Guide Page):**
- [ ] Guide page section shows auto-generated summary: "This book contains [N] puzzles. Difficulty: [M] Easy, [K] Medium, [J] Hard"
- [ ] Guide text is non-editable in draft (customization deferred)
- [ ] Guide appears after cover (if any) but before first puzzle

**Acceptance Criteria (PDF Preview & Download):**
- [ ] "Preview" button shows lightweight mockup:
  - Cover page (if uploaded) or blank page with book title
  - First 3 puzzles with titles and grid layouts
  - Calculated total page count (shown as "Pages 1–N estimated")
  - Sample of arrangement accuracy
- [ ] Preview does NOT render full PDF (browser, not PDF lib)
- [ ] "Download PDF" button generates and serves the full PDF:
  - Includes cover (if uploaded)
  - Includes guide page summary
  - Includes all puzzles in order with titles, grids, and clues
  - Applies trim size and margin specs
  - Filename: `book_[timestamp].pdf` (e.g., `book_2026-09-09T143022.pdf`)
- [ ] PDF download completes within 10 seconds for typical books (≤100 puzzles)

**Acceptance Criteria (Workflow):**
- [ ] "Back" button returns to Step 3 (arrangement preserved)
- [ ] "Save Book" button finalizes the book and returns to book list
- [ ] Unsaved changes prompt user: "Discard changes?" on navigation away

---

## Non-Goals

- **Multi-language guide templates** — guide is English-only, auto-generated
- **Cover design editor** — users upload pre-built covers; no in-browser design tool
- **Print-on-demand integration** — no auto-upload to KDP (manual workflow)
- **Book versioning/history** — no undo; changes are live
- **Puzzle licensing/metadata in PDF** — no copyright statements or puzzle sources printed
- **Custom page layouts** — puzzles are full-page or half-page only (no grid layouts)

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Reuse puzzle filter UI** | Avoid duplicate filter logic; users already know the interface |
| **Up/Down buttons, not drag/drop** | Simpler, no JS library dependency, accessible |
| **Puzzle title (not PDF-global)** | Titles are book-local; original puzzle is unaffected |
| **Lightweight preview** | Full PDF render is slow; mockup shows layout without overhead |
| **Auto-generated guide page** | Minimal setup; customization is future work |
| **Optional cover upload** | Supports multi-step workflow: draft book first, cover later |

---

## Implementation Notes

- **Storage:** Books stored in DB as `Book` table with JSON column for puzzle list (order, title, cover_url)
- **PDF generation:** Use existing `export.pdf` module; add new `pdf.book_to_pdf()` function
- **UI:** Flask admin forms + HTML5 file input + client-side JS for up/down buttons
- **Testing:** Unit tests for arrangement logic; integration test for PDF export

---

## Acceptance Gate

Book scaffolding is complete when:
1. All Step 1–4 ACs are passing
2. End-to-end test creates a book and downloads valid PDF
3. PDF matches trim size and margin specs
4. Owner validates PDF on Amazon KDP preview tool or test print

