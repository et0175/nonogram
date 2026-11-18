# CARD-475: The five hollow upload e2e tests post the field the route reads

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false <!-- test-only card -->
**Branch:** —
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-082, WSJF 5.38); premise re-read against main on 2026-11-18. Origin: CARD-164 review, finding F-002.
**Idea:** IDEA-082
**Wave:** —
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/e2e/test_admin_workflow.py
**UI surface:** none
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-164 found `test_size_configuration_applied` posting the file as `images`, a field `/batch/from-images` never reads, so it only ever saw the "No images selected" redirect and passed. It fixed that one test. Five siblings in the same file still do the same thing and still pass on the redirect: `test_tc_001_single_image_upload`, `test_preview_page_displays_original_image`, `test_metadata_shown_on_preview`, `test_tc_002_multiple_image_batch`, `test_tc_003_svg_generation_display`.

## What to implement

Apply CARD-164's repair to the five: post the field the route reads, and assert on what a real upload produces (the preview page, its image, its metadata) instead of on a location that the refusal redirect also satisfies. Where a test's remaining assertion would still hold for the refusal path, tighten it or fold the test into the sibling that already makes the claim.

## Acceptance criteria

* **AC-1**: each of the five reds when the route's upload handling is stubbed to refuse (run once, pasted in the notes) — today all five stay green.
* **AC-2**: no test in the file posts a field name the route does not read (derived from the route's own `request.files` reads, not from a list in the test).
* **AC-3**: net test count reported; a merge of two tests that make one claim is allowed, a deletion without a surviving claim is not.

## Guardrails

* **G-1**: `src/` is not touched. If a repaired test goes red on main, that is a product finding: stop and report it, do not bend the test.
* **G-2**: the e2e file needs the database; read `-rfs` and confirm zero skips among the five before claiming green.

## Worktree notes

—
