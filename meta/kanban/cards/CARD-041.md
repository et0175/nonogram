# CARD-041: Add colored backgrounds to result messages (success/error visual distinction)

**Status:** in_progress
**Priority:** P2
**Category:** enhancement
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/041-result-message-colors
**Worktree:** ../PythonProject4-CARD-041
**Source:** User testing feedback (wave 3)
**Idea:** —
**Wave:** 3
**Depends on:** CARD-030
**Touches:** src/nonogram/web/pages.py, tests/test_web_server.py
**Review score:** —
**Started:** 2026-09-04T00:00:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Add CSS styling to distinguish success and error result messages with colored backgrounds:

- **Success message** — greenish background (e.g., `#d4edda` or `#c6f6d5`)
- **Error message** — pinkish/reddish background (e.g., `#f8d7da` or `#fed7d7`)

Both should use readable text color (dark gray or black) and maintain padding/spacing consistency with the current message layout.

## Acceptance criteria

- **AC-155** (success styling) — given a successful generation, when the form displays the result message, then it has a distinct greenish background that contrasts well with the text.
  *test:* `TestWebForm_SuccessMessageHasGreenBackground`

- **AC-156** (error styling) — given a generation error, when the form displays the error message, then it has a distinct pinkish/reddish background that contrasts well with the text.
  *test:* `TestWebForm_ErrorMessageHasPinkBackground`

- **AC-157** (accessibility) — both backgrounds meet WCAG AA contrast ratio requirements (≥4.5:1) with their text colors.
  *test:* `TestWebForm_ResultMessagesAccessible` (or manual axe scan)

## Guardrails

- G-1: CSS-only (no new HTML structure, no JavaScript)
- G-2: Colors match the form's existing dark mode + light mode themes
- G-3: Spacing/padding unchanged (only add background color)

## Architecture context

- **FR:** FR-017 (web UI)
- **NFR:** NFR-003 (UX polish)
- **ADR:** ADR-0019
- **Components:** COMP-008 (web UI)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
