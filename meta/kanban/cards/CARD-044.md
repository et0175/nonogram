# CARD-044: Fix image preview with persisted uploads (bridges CARD-037, 042, 043)

**Status:** ready
**Priority:** P1
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/044-preview-with-persistence
**Worktree:** —
**Source:** User testing feedback (wave 3 integration issue)
**Idea:** —
**Wave:** 3
**Depends on:** CARD-037, CARD-042
**Touches:** src/nonogram/web/static/metadata.js, src/nonogram/web/pages.py, tests/test_web_server.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The image preview (CARD-042) doesn't work with persisted uploads (CARD-037). When a user generates and gets an error, then selects a new image (or same image), the preview doesn't appear. 

**Root cause:** Preview display only triggers on file input change events. When form re-renders with persisted_image_path, no change event fires → preview hidden.

**Fix:** Refactor preview display logic to work on both file input change AND on page load when persisted image exists.

**Also fix:**
- Clear preview when form errors occur (prevent stale previews with error state)
- Integrate with CARD-043 (clear messages on new upload)

## Acceptance criteria

- **AC-163** (preview on page load) — given a persisted image in a form re-render, when the page loads, then the preview displays immediately (no file change needed).
  *test:* `TestWebUI_ShowsPreviewOnLoadWithPersistedImage`

- **AC-164** (preview on re-select) — given an error message and persisted image, when the user selects a new image, then the preview updates.
  *test:* `TestWebUI_UpdatesPreviewOnReselect`

- **AC-165** (clear on error) — given a previous preview, when generation fails and form re-renders with error, then the preview clears.
  *test:* `TestWebUI_ClearsPreviewOnGenerationError`

- **AC-166** (clear on new file) — given an error state, when user selects a new image, then both preview updates AND error message clears.
  *test:* `TestWebUI_ClearsErrorAndShowsNewPreview`

## Guardrails

- G-1: Preview works with persisted image path (file input hidden)
- G-2: No JavaScript errors if preview or persisted elements missing
- G-3: File input re-selection works (same file twice in a row)
- G-4: Doesn't break existing CARD-042 preview functionality

## Architecture context

- **FR:** FR-017
- **NFR:** NFR-003
- **ADR:** ADR-0020
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

**2026-09-10 — reverted from a false "done" state; this card is NOT actually
done on `main`.** The card previously claimed `Status: completed`,
`Merge commit: 1c6ed74`, `Closed: 2026-09-04T10:36:00Z` — all from a close-out
that happened on a git history with **no common ancestor with current `main`**
(`git merge-base main card/044-preview-with-persistence` returns nothing;
`git cat-file -t 1c6ed74` confirms the commit object exists but
`git log --oneline main | grep 1c6ed74` finds it on no branch reachable from
`main`). The implementation summary below is real work that happened — it is
kept as historical record — but it never reached the codebase that is
actually being developed on.

Checked directly: `main`'s current `src/nonogram/web/static/metadata.js` and
`pages.py` have **no** `persisted_image_path` field, no
`initializePersistedPreview()`, and no `TestWebUI_PreviewWithPersistence` test
class — none of this card's specific deliverable survived the `96da6ac` bulk
restore that brought its sibling cards' work back (CARD-038/039/040/041/042
were reconciled as done against that restore; this one's feature simply wasn't
in the backup being restored, or predates it).

Reverted to `ready`. Since CARD-037 (this card's other dependency) is also
confirmed not done on `main` (see its own notes), **this card cannot usefully
start until CARD-037 is re-implemented against current `main`** — the
persistence mechanism this card bridges into the preview doesn't exist yet
either.

A stray worktree exists on disk at `../PythonProject4-CARD-044` (pointing at
the orphaned `1c6ed74`/`2f40540`) — should be removed; left untouched pending
explicit confirmation.

### Implementation summary

Refactored metadata.js preview display logic:

1. **Extracted showImagePreview(metadata)** — reusable function that displays preview with given metadata (width, height, imageSrc)
2. **Added clearPreview()** — hides preview container when generation fails
3. **Added clearResultMessage()** — clears error/success messages when new image selected (CARD-043 integration)
4. **Added initializePersistedPreview()** — runs on page load to show preview if persisted image path exists
5. **Updated displayImagePreview()** — now calls showImagePreview() internally after FileReader completes
6. **Integrated with file change event** — now calls clearResultMessage() when new image selected

### Form updates

- Added `persisted_image_path` hidden field to both FORM_PAGE and form_with_result (CARD-037 integration)
- Added preview container elements to initial FORM_PAGE (AC-163)
- Updated test expectations for new form field

### Testing

- Added 7 new tests in TestWebUI_PreviewWithPersistence class verifying all ACs
- All 160 tests pass including new functionality
- Updated existing test to account for persisted_image_path field in form options