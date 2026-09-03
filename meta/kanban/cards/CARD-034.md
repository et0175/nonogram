# CARD-034: Calculate image metadata on file upload (client-side)

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/034-client-metadata
**Worktree:** —
**Source:** User feedback during wave 0 testing
**Idea:** —
**Wave:** —
**Depends on:** CARD-031
**Touches:** src/nonogram/web/pages.py, tests/test_web_server.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Calculate image metadata and suggestions **client-side** on file selection (not after submission). Shows aspect ratio and 2-3 suggestions instantly, allows clicking suggestions without re-uploading.

**Uses File API to:**
- Read uploaded image dimensions asynchronously
- Calculate aspect ratio (fraction simplification)
- Run deterministic suggestion algorithm (must match server)
- Update form UI in real time

**Benefits:**
- Instant preview (no server round-trip for preview phase)
- Suggestions are actionable (file stays selected)
- Better UX flow (one form submission, not two)

## Acceptance criteria

- **AC-135** (instant preview) — metadata and suggestions appear instantly when file is selected (within 1s), without form submission.
  *test:* `TestWebUI_InstantMetadataOnFileSelect`

- **AC-136** (suggestion click) — clicking suggestion populates size field, file input retains selection, user can submit immediately.
  *test:* `TestWebUI_ClickSuggestionPreserveFile`

- **AC-137** (algorithm parity) — client-side and server-side metadata calculations are identical for same image.
  *test:* `TestWebUI_ClientServerMetadataMatch`

- **AC-138** (fallback) — no error if File API unavailable; suggestions shown after submission as before (CARD-031 fallback).
  *test:* `TestWebUI_FileAPIFallback`

## Guardrails

- G-1: No new runtime dependencies
- G-2: File API optional (graceful degradation)
- G-3: Server-side suggestion algorithm unchanged
- G-4: Vanilla JavaScript only (no frameworks)

## Architecture context

- **FR:** FR-017
- **NFR:** NFR-003
- **ADR:** ADR-0019, ADR-0020
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
