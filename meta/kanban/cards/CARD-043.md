# CARD-043: Clear error/success message when new image is uploaded

**Status:** ready
**Priority:** P2
**Category:** ux-polish
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/043-clear-message-on-upload
**Worktree:** —
**Source:** User feedback during wave 3 testing
**Idea:** —
**Wave:** 3
**Depends on:** CARD-038, CARD-041
**Touches:** src/nonogram/web/static/metadata.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

When a user uploads a new image, clear any previous error/success messages from the form. This prevents confusing the user with stale result messages from a previous generation attempt when they're about to try again with a new image.

**Flow:**
1. User generates puzzle → success/error message displays
2. User selects new image → message clears immediately (since they're starting fresh)
3. User adjusts settings + submits → new result displays

**Implementation:** In `metadata.js` file change listener, clear the result message container when new image selected.

## Acceptance criteria

- **AC-161** (clear on upload) — given a user who sees an error/success message, when they select a new image file, then the message is cleared.
  *test:* `TestWebUI_ClearsMessageOnNewImageUpload`

- **AC-162** (fresh start) — given a cleared message and new image, when the user adjusts settings + resubmits, then only the new result displays (no mixing).
  *test:* `TestWebUI_FreshMessageAfterNewUpload`

## Guardrails

- G-1: Only clear message when new image selected (not on form field changes)
- G-2: No JavaScript errors if result container missing
- G-3: Message clearing doesn't interfere with form persistence (CARD-037)

## Architecture context

- **FR:** FR-017
- **NFR:** NFR-003
- **ADR:** ADR-0020
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
