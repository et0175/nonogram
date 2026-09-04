# CARD-037: Persist uploaded image for retry without re-upload

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/037-persist-upload-retry
**Worktree:** ../PythonProject4-CARD-037
**Source:** User feedback during wave 0–2 testing
**Idea:** —
**Wave:** 3
**Depends on:** CARD-031
**Touches:** src/nonogram/web/handler.py, src/nonogram/web/submission.py, src/nonogram/web/pages.py, tests/test_web_server.py
**Review score:** —
**Started:** 2026-09-04T00:00:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

When a user uploads an image and encounters an error (invalid ratio, too many retry attempts, etc.) or wants to regenerate with different settings (size, difficulty, name), they currently must re-upload the image. This creates friction and a poor UX.

Instead, keep the uploaded temp file available across retry attempts, allowing the user to:
1. Upload image once
2. Adjust size/difficulty/name/output-directory
3. Resubmit form without re-uploading
4. If error, repeat steps 2–3

**Technical approach:**
- Store temp file path in session/form state (hidden field or cookie)
- Check if resubmission references an existing temp file
- Reuse temp file for subsequent generation attempts
- Clean up after success OR after max retry attempts exceeded
- Validate temp file still exists before reuse

## Acceptance criteria

- **AC-143** (persist) — given an uploaded image and a generation error, when the form is re-rendered with inline error, then the temp file is retained and available for retry.
  *test:* `TestWebUpload_PersistsImageAcrossRetries`

- **AC-144** (reuse) — given a persisted temp file and a form resubmission with different size/difficulty, when the form is submitted, then the same image file is used for generation without requiring a new upload.
  *test:* `TestWebUpload_ReusesPersistedImageOnRetry`

- **AC-145** (cleanup) — given a successful generation or max retry attempts exceeded, when the session ends, then the temp file is deleted (no orphaned files).
  *test:* `TestWebUpload_CleansUpAfterSuccess`

- **AC-146** (validation) — given a persisted temp file reference, when the form is submitted, then the system validates the file still exists and is readable before reuse (handles race conditions).
  *test:* `TestWebUpload_ValidatesPersistedFileStillExists`

## Guardrails

- G-1: No new runtime dependencies
- G-2: Temp file cleanup happens even on errors or aborted requests
- G-3: Persisted file reference validated before reuse (security)
- G-4: Max file persistence time enforced (prevent disk space issues)

## Architecture context

- **FR:** FR-017 (web UI)
- **NFR:** NFR-003
- **ADR:** ADR-0019, ADR-0020, ADR-0021
- **Components:** COMP-008 (web UI)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
