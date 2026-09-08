# CARD-030: Display inline success/error messages on form page

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/030-inline-messages
**Worktree:** —
**Source:** User feedback during CARD-021 testing
**Idea:** —
**Wave:** —
**Depends on:** CARD-021
**Touches:** src/nonogram/web/pages.py, src/nonogram/web/handler.py, tests/test_web_server.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Currently, after a form submission, users are redirected to either a success page or a failure page. This UX forces the user to navigate back to the form to submit again. Instead, display both success and failure outcomes inline on the same form page.

The POST handler (`handler._generate`) already computes success and failure payloads; the change is purely UI — render them inline as collapsible sections on the form page itself, preserving form inputs so users can modify and resubmit.

## Acceptance criteria

- **AC-122** (happy) — given a successful puzzle generation, when the user submits the form, then the page displays the result (name, seed, written files) in a collapsible "Success" section on the same page, form remains visible and editable.
  *test:* `TestWebForm_DisplaysSuccessInline`

- **AC-123** (error) — given a failed generation, when the form is submitted, then the page displays error summary and details in a collapsible "Error" section, form retains inputs, user can adjust and retry.
  *test:* `TestWebForm_DisplaysErrorInline`

- **AC-124** (UX) — given a user who has submitted successfully, when they clear the form, the result section collapses and focus returns to form inputs.
  *test:* `TestWebForm_ClearsResultOnNewSubmit`

## Guardrails

- G-1: No new runtime dependencies
- G-2: HTTP response codes unchanged (200 for both outcomes)
- G-3: All form field names and orchestrator integration unchanged
- G-4: Accessibility: result sections must have clear ARIA labels

## Architecture context

- **FR:** FR-017, FR-003
- **NFR:** NFR-003
- **ADR:** ADR-0019, ADR-0020
- **Components:** COMP-008, COMP-002 (unchanged)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
