# CARD-030: Display inline success/error messages on form page

**Status:** done
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
**Closed:** 2026-09-21
**Actual:** —
**Merge commit:** _(with CARD-104)_
**Blocked by:** —

## What to implement

Currently, after a form submission, users are redirected to either a success page or a failure page. This UX forces the user to navigate back to the form to submit again. Instead, display both success and failure outcomes inline on the same form page.

The POST handler (`handler._generate`) already computes success and failure payloads; the change is purely UI — render them inline as collapsible sections on the form page itself, preserving form inputs so users can modify and resubmit.

> **These AC numbers are local to this card (CARD-106).** The requirements
> registry uses the same numbers for entirely different criteria, and the
> registry's are authoritative — they carry given/when/then/test and trace to
> an FR, while these are prose. Neither set is renumbered; both are cited by
> tests and by closed cards.
>
> | number | means, in `requirements.yml` | owned by |
> |---|---|---|
> | `AC-122` | two solver signal records identical in every field except elapse… | FR-029 |
> | `AC-123` | a random-mode request with seed 42, 20x20, density 40 and --diff… | FR-029 |
> | `AC-124` | a resized cell whose ink coverage is 80% (grey value 51 of 255 a… | FR-027 |

## Acceptance criteria

- **AC-122** (happy) — given a successful puzzle generation, when the user submits the form, then the page displays the result (name, seed, written files) in a collapsible "Success" section on the same page, form remains visible and editable.
  *test:* `tests/test_web_submission.py` — the AC-122 assertions at the success arm ("form remains visible", fields re-populated)

- **AC-123** (error) — given a failed generation, when the form is submitted, then the page displays error summary and details in a collapsible "Error" section, form retains inputs, user can adjust and retry.
  *test:* `tests/test_web_submission.py` — the AC-123 assertions at the failure arm ("form retains inputs")

- **AC-124** (UX) — given a user who has submitted successfully, when they clear the form, the result section collapses and focus returns to form inputs.
  *test:* `TestWebForm_ResultClearing` in `tests/test_web_server.py` (CARD-038's AC-147/148 cover the same script)

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

### Closed 2026-09-21 by CARD-104

The feature shipped long before this card was looked at again: `POST /generate`
answers 200 with the form and the result on one page (`pages.form_with_result`),
and every failure goes through `handler._fail_inline` rather than a redirect.

**AC-122 and AC-123 were already tested** — in `tests/test_web_submission.py`,
asserting the criteria's own words ("form remains visible", "form retains
inputs"). They were not found for eighteen days because this card's `*test:*`
lines named classes that never existed, so nothing led from the criterion to
its test. Those lines now point at the real ones.

**AC-124's second clause is retired.** It asks that "focus returns to form
inputs". Nothing moves focus, and nothing should: the listener fires on
`input`, which cannot happen unless focus is already in a form control, so
calling `.focus()` would take focus somewhere the user did not put it. The
clause is satisfied by construction. The script's comment claimed to "manage
focus" and was doing no such thing; CARD-104 rewrote it to say what the code
does and why.
