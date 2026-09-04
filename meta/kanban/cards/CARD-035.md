# CARD-035: Include source image filename in export (traceability)

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/035-export-filename-traceability
**Worktree:** —
**Source:** User feedback during wave 0 testing
**Idea:** —
**Wave:** 2
**Depends on:** CARD-031
**Touches:** src/nonogram/web/handler.py, src/nonogram/orchestrator.py, src/nonogram/export/**, tests/**
**Review score:** 9.2
**Started:** 2026-09-03T00:00:00Z
**Closed:** 2026-09-04T06:00:00Z
**Actual:** 1.0d
**Merge commit:** e3ec635
**Blocked by:** —

## What to implement

Currently, exported files are named based on the generated puzzle name (e.g., `puzzle_20260903_abc123.svg`), which loses the connection to the original uploaded image file.

Enhance traceability by incorporating the source image filename into the export filenames when available. For example:
- Upload: `cat.jpg`
- Generated puzzle: "cat"
- Export: `cat_20260903_abc123.svg` or `cat.svg`

**Technical approach:**
1. Capture the original uploaded image filename from the file input
2. Pass filename through the request pipeline (add to `GenerationRequest` or pass separately)
3. Use it in puzzle name generation (FR-015) as a hint/prefix
4. Fallback to current behavior if no image source or filename unavailable

## Acceptance criteria

- **AC-139** (capture filename) — given an uploaded image file, when the form is submitted, then the original filename is captured and passed through to the puzzle generation.
  *test:* `TestWebUI_CapturesUploadedImageFilename`

- **AC-140** (export naming) — given a puzzle generated from an uploaded image named "cat.jpg", when files are exported, then the exported filenames include "cat" in their name (e.g., "cat_puzzle.svg" or "cat_<seed>.pdf").
  *test:* `TestWebUI_ExportFilenamesIncludeSourceImageName`

- **AC-141** (fallback) — given a puzzle generated without an image source (non-image mode), when files are exported, then naming follows the current scheme (no regression).
  *test:* `TestWebUI_NonImageModeUsesCurrent Naming`

- **AC-142** (sanitization) — given an uploaded image with special characters in filename (e.g., "cat (1).jpg", "puzzle-#1.png"), when exported, then the filename is sanitized to be filesystem-safe while retaining recognizability.
  *test:* `TestWebUI_ExportFilenameSanitization`

## Guardrails

- G-1: No new runtime dependencies
- G-2: Non-image mode behavior unchanged (fallback to current naming)
- G-3: Sanitization prevents path traversal or invalid characters
- G-4: Puzzle name generation logic (FR-015) can accept optional source hint but continues to work as before

## Architecture context

- **FR:** FR-015 (puzzle naming), FR-017 (web UI)
- **NFR:** NFR-003
- **ADR:** ADR-0019, ADR-0020
- **Components:** COMP-002 (orchestrator — puzzle naming), COMP-008 (web UI)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

**Review cycle 1 (Score: 9.2/10)** ✓ PASSED

**AC/EC/G Verification:**
- AC-139 ✓: Filename captured from multipart Content-Disposition header, passed through pipeline to GenerationRequest
- AC-140 ✓: Export filenames include source image name (e.g., "cat_puzzle.svg") via puzzle.name derived from image_filename
- AC-141 ✓: Non-image modes (random/library) use current naming scheme, image_filename ignored
- AC-142 ✓: Filename sanitization via _sanitized_component prevents path traversal and filesystem-unsafe characters

**Guardrail Compliance:**
- G-1 ✓: No new runtime dependencies — only stdlib + existing Pillow/NumPy
- G-2 ✓: Non-image mode behavior fully unchanged — random/library naming logic intact
- G-3 ✓: Sanitization prevents path traversal via regex `[^\w.-]+` → prevents `../`, `//`, `\`, null bytes, special chars
- G-4 ✓: Puzzle naming logic (FR-015) accepts optional image_filename but operates as before

**Test Results:**
- 18 new unit tests in test_card_035_image_filename_traceability.py: 18/18 passing
- Full test suite: 2370/2370 passing ✓
- Coverage: multipart parsing, filename extraction, naming hints, sanitization edge cases, unicode handling, fallbacks

**Implementation Notes:**
- multipart.py: Extracts filename from Content-Disposition header via part.get_filename()
- submission.py: Passes image_filename through from_fields() to GenerationRequest
- orchestrator.py: NameContext._auto_name() uses image_filename as puzzle name hint for image mode (priority: filename → path stem → timestamp)
- orchestrator.py: _sanitized_component() applies filesystem safety via _UNSAFE_STEM_CHARACTERS regex
- handler.py: Correctly manages multipart submission and cleanup of uploaded temp files

**Architecture Alignment:**
- ADR-0010 ✓: Filename is unvalidated at CLI boundary (GenerationRequest)
- ADR-0016 ✓: Sanitization applied at export-time filename stage (not on puzzle name itself)
- ADR-0018 ✓: No collision with naming context — image_filename is not disambiguated (same as library key)
- ADR-0020 ✓: Multipart parsing via email.parser.BytesParser for RFC 2046 compliance

**Ready to merge:** All criteria met, review score 9.2 (threshold 8.0) ✓
