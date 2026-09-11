# CARD-041: Add colored backgrounds to result messages (success/error visual distinction)

**Status:** done
**Priority:** P2
**Category:** enhancement
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/041-result-message-colors
**Worktree:** —
**Source:** User testing feedback (wave 3)
**Idea:** —
**Wave:** 3
**Depends on:** CARD-030
**Touches:** src/nonogram/web/pages.py, tests/test_web_server.py
**Review score:** —
**Started:** 2026-09-04T00:00:00Z
**Closed:** 2026-09-08T10:59:21+03:00
**Actual:** n/a — reconciled, see Worktree notes
**Merge commit:** 96da6ac
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

**2026-09-10 — reconciled against `main`, not merged normally.** Same
disconnected-history situation as CARD-038/039. Unlike those two, this card's
own branch (`card/041-result-message-colors`) DOES carry a genuine, complete
implementation commit (`fff246f "feat(CARD-041): Add colored backgrounds to
success/error messages"` — full diff, tests, AC-155/156/157 addressed,
WCAG AA contrast documented) — it was simply never taken through review/`done`
before the history split, and the branch it lives on has no path back to
current `main`.

`main`'s `src/nonogram/web/pages.py:385-393` already carries the exact colors
this commit introduced (`#d4edda`/`#f8d7da`/`#155724`), via the same `96da6ac`
bulk restore, later refined by `2d86180 "fix: use CSS classes instead of
attribute selectors for data-outcome styling"`. Verified present on current
`main`; closing as done with `96da6ac` as the merge commit (the commit that
actually landed it there).

The orphaned worktree at `../PythonProject4-CARD-041` still exists on disk and
should be removed — left untouched pending explicit confirmation.
