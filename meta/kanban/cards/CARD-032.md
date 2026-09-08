# CARD-032: Restrict web form to image-only mode

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/032-image-only-mode
**Worktree:** —
**Source:** User feedback post-CARD-021
**Idea:** —
**Wave:** —
**Depends on:** CARD-021
**Touches:** src/nonogram/web/pages.py, tests/test_web_server.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The web UI form currently offers three sourcing modes: random, library, and image. However, the image upload feature (CARD-021) is the unique value proposition of the web UI — the CLI already covers random and library. Simplify the form to offer **image mode only**, removing the random and library options.

This reduces cognitive load and signals to users what the web UI is for. The CLI remains the way to generate via random or library sourcing.

## Acceptance criteria

- **AC-128** (scope) — given the form page, when it loads, then the "Source" dropdown is gone and the form assumes image mode implicitly (file upload required, image metadata displayed, no size/density/library-key fields relevant to random/library).
  *test:* `TestWebForm_OnlyOffersImageMode`

- **AC-129** (validation) — given a form submission with no file uploaded, when the form is submitted, then the handler returns an error (missing image file) with the same path as if mode validation had failed in the domain.
  *test:* `TestWebForm_RequiresImageForSubmission`

- **AC-130** (parity) — given the web form in image-only mode, when a valid image and size are submitted, the generation pipeline behaves identically to the multi-mode version (same sourcing, same clue derivation, same solver — only the UI offering changed).
  *test:* `TestWebForm_GeneratesIdenticallyToMultiMode`

## Guardrails

- G-1: No changes to the domain (orchestrator, sourcing, handler logic) — UI-only
- G-2: The urlencoded submission path (used by tests) must still work unchanged
- G-3: All three modes remain equally supported at the CLI level (no regression)

## Architecture context

- **FR:** FR-017 (web UI)
- **NFR:** NFR-003
- **ADR:** ADR-0019 (adapter scope), ADR-0020 (no new deps)
- **Components:** COMP-008 (web UI only)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
