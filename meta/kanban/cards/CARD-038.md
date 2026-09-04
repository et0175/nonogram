# CARD-038: Clear previous result message when submitting new generation

**Status:** ready
**Priority:** P2
**Category:** bugfix
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/038-clear-result-on-resubmit
**Worktree:** —
**Source:** User feedback during wave 0–2 testing
**Idea:** —
**Wave:** —
**Depends on:** CARD-030
**Touches:** src/nonogram/web/pages.py, src/nonogram/web/handler.py, tests/test_web_server.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

When a user generates a puzzle, the result (success or error) is displayed inline (CARD-030). However, if they then select a new image and submit again, the *previous* result message still shows instead of clearing and showing the new one.

The form should clear the previous result message when a new submission is processed, ensuring the user always sees the current state.

**Fix:** Before rendering form_with_result() on a new submission, pass `outcome=""` or similar to clear the previous result display, showing only the fresh result.

## Acceptance criteria

- **AC-147** (clear on new submit) — given a user who previously generated a puzzle and sees a result message, when they select a new image and submit, then the previous result message is cleared before the new one displays.
  *test:* `TestWebForm_ClearsPreviousResultOnNewSubmit`

- **AC-148** (no stale state) — given multiple sequential form submissions, then each submission displays only its own result (no mixing of old and new messages).
  *test:* `TestWebForm_NoStaleResultAcrossSubmissions`

## Guardrails

- G-1: No breaking changes to CARD-030's result display logic
- G-2: Error and success messages both clear properly
- G-3: Form fields preserved across submission (CARD-030 behavior unchanged)

## Architecture context

- **FR:** FR-017
- **NFR:** NFR-003
- **ADR:** ADR-0019
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
