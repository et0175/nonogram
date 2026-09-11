# CARD-037: Persist uploaded image for retry without re-upload

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/037-persist-upload-retry
**Worktree:** —
**Source:** User feedback during wave 0–2 testing
**Idea:** —
**Wave:** —
**Depends on:** CARD-031
**Touches:** src/nonogram/web/handler.py, src/nonogram/web/submission.py, src/nonogram/web/pages.py, tests/test_web_server.py
**Review score:** —
**Started:** —
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

**2026-09-10 — investigated as part of reconciling CARD-038/039/040/041/042/044
against `main`.** Unlike its siblings, this card is genuinely **not done** —
staying `ready`, not being closed.

Its branch (`card/037-persist-upload-retry`) exists but never received an
actual `feat(CARD-037)` implementation commit (`git log --all` finds none
anywhere in the repository) — the branch tip (`5c5ae5e`) turned out to be
CARD-039's commit, landed here by an apparent worktree/checkout mixup at
implementation time (see CARD-039's own notes), not this card's own work.

`main`'s current `src/nonogram/web/*.py` has no `persisted_image_path` field,
no session/hidden-field temp-file reuse across retries, and no test for it —
confirmed by grep, none of the `96da6ac` bulk restore's files carried this
feature in either. `CARD-044`'s branch (a different, later card) did add a
`persisted_image_path` hidden field and `initializePersistedPreview()` as part
of *bridging* this card with the preview feature — but that specific piece
also did not survive into `main` (see CARD-044's notes) — so there is nothing
to reconcile here; this is real, outstanding work.

A stray worktree exists on disk at `../PythonProject4-CARD-037` (pointing at
the orphaned `5c5ae5e`, i.e., CARD-039's commit, not this card's) — it should
be removed before starting fresh, since a normal `start CARD-037` would create
a new worktree off current `main` anyway.

**2026-09-11 — update: the worktree is NOT clean, and removal was correctly
refused.** `git worktree remove` on this path fails (`fatal: ... contains
modified or untracked files`) because it holds **real, substantive, never-
committed implementation work** for this exact card:
`src/nonogram/web/handler.py` (persisted-path reuse + conditional cleanup on
success/error), `src/nonogram/web/pages.py` (the `persisted_image_path` hidden
field), and `tests/test_web_server.py` (4 new tests, `TestWebForm_ImagePersistence`,
covering AC-143/144/145/146). This is meaningfully further along than "never
implemented" — it was implemented and simply never committed before the
history split.

**Preserved** at
`/private/tmp/claude-501/-Users-omelnikova-PycharmProjects-PythonProject4/7153fc65-6545-4f37-8efc-99569009eea7/scratchpad/CARD-037-uncommitted-work.patch`
(124 lines) before any further action, so it survives regardless of what
happens to this worktree.

**Not applied to `main` as-is** — it's written against the old lineage's
`handler.py` structure (variable names `image_path`/`media_type`/`fields` at
specific call sites); `main`'s current `handler.py` should be diffed against
this patch before reuse to confirm it still applies cleanly or needs
adaptation. Treat this as a strong starting draft for CARD-037's real
implementation, not a drop-in patch.

The worktree itself (still holding this uncommitted diff) is left in place —
removing it now would require `--force` and would discard this work with no
recovery beyond the preserved patch file. Do not force-remove until the patch
has been reviewed/reapplied against current `main`.
