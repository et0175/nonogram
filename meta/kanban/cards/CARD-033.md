# CARD-033: Add output directory selector and improve form styling

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/033-output-dir-form-polish
**Worktree:** —
**Source:** User feedback post-CARD-021
**Idea:** —
**Wave:** —
**Depends on:** CARD-030, CARD-031, CARD-032
**Touches:** src/nonogram/web/pages.py, src/nonogram/web/submission.py, src/nonogram/web/handler.py, tests/test_web_server.py
**Review score:** —
**Started:** —
**Closed:** 2026-09-21
**Actual:** —
**Merge commit:** _(with CARD-104)_
**Blocked by:** —

## What to implement

1. **Output directory selector** — add an `<input type="text">` or native path picker (if available) allowing users to specify where generated files are written. Default to the working directory (current behavior). The handler maps this to the `out` field already declared in `GenerationRequest` but currently unused/hardcoded.

2. **Form styling polish** — improve visual hierarchy, spacing, and clarity:
   - Group related fields (image upload + metadata, export formats, etc.)
   - Use fieldsets or visual dividers
   - Improve button styling (primary action emphasis)
   - Consistent spacing and typography
   - Dark mode support (if `meta/design/tokens.css` exists; otherwise match the existing minimalist style)

This gives users control over file placement and makes the form feel more polished and intentional.

## Acceptance criteria

- **AC-131** (directory input) — given the form page, when it loads, then there is an "Output directory" input field with placeholder text explaining it defaults to the working directory.
  *test:* `TestWebUI_OutputDirectoryFieldAndStyling` in `tests/test_web_submission.py` (AC-131)

- **AC-132** (submission) — given a user who enters a directory path and submits, when the generation completes, then the output files are written to that directory (or an error is raised if the path is invalid/unwritable).
  *test:* `TestWebUI_OutputDirectoryFieldAndStyling` (AC-132)

- **AC-133** (UI polish) — given the refined form page, when it renders, it displays clear visual grouping of field categories (source/image, export options, output), consistent spacing, and a prominent Generate button.
  *test:* `TestWebUI_OutputDirectoryFieldAndStyling` (AC-133) — asserts the three `form-section` groups, which is the checkable part of "polish" (visual inspection or a11y tree check)

- **AC-134** (fallback) — given a user who leaves the output directory empty, when the form is submitted, the files are written to the working directory (same as before).
  *test:* `TestWebUI_OutputDirectoryFieldAndStyling` (AC-134)

## Guardrails

- G-1: No new runtime dependencies (use stdlib Path/pathlib only)
- G-2: Output directory validation happens in the handler, not as HTML validation (ADR-0019/R1 — domain only)
- G-3: The `GenerationRequest.out` field and orchestrator handling unchanged — web UI only
- G-4: Styling is CSS-only; no JavaScript frameworks or external style libraries

## Architecture context

- **FR:** FR-017 (web UI), FR-003 (generation)
- **NFR:** NFR-003
- **ADR:** ADR-0019 (adapter scope), ADR-0020 (no new deps)
- **Components:** COMP-008 (web UI), COMP-002 (orchestrator — unchanged)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

### Closed 2026-09-21 by CARD-104

Shipped, and **already tested** — `TestWebUI_OutputDirectoryFieldAndStyling` in
`tests/test_web_submission.py` carries a test per criterion and names AC-131,
AC-132, AC-133 and AC-134 in its docstring. The card's own `*test:*` lines
named four classes that never existed, which is the only reason this looked
untested; they now point at the real one.

AC-133's "polish" is the criterion that cannot be asserted as written. What the
existing test pins is the checkable part: the three `<div class="form-section">`
groups (Image, Puzzle Settings, Export). The rest of the criterion — "consistent
spacing", "prominent Generate button" — is left as the judgement it is, rather
than approximated by a test that asserts a `<div>` exists and calls it polish.
