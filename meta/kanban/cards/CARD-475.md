# CARD-475: The five hollow upload e2e tests post the field the route reads

**Status:** review
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false <!-- test-only card -->
**Branch:** card/475-hollow-upload-e2e-tests
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-475
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-082, WSJF 5.38); premise re-read against main on 2026-11-18. Origin: CARD-164 review, finding F-002.
**Idea:** IDEA-082
**Wave:** 80
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/e2e/test_admin_workflow.py
**UI surface:** none
**Review score:** 9.0 (cycle 3/3 - NOT CERTIFIED, ⚠ max cycles reached; two gating findings fixed after the last cycle)
**Started:** 2026-11-18T09:15Z
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

[Start] Implemented by the orchestrating session itself; reviewed by one independent agent across all three cycles. One file, `tests/e2e/test_admin_workflow.py`; four commits on the branch.
[G-2 withdrawn] The guardrail says the file needs the database. It does not: `admin_app` removes `DATABASE_URL` and runs in memory. 19 passed, 0 skipped.
[AC-1, measured] Before the card, with the route stubbed to refuse every upload, all five tests stayed green. After it, the same stub reds six: `test_tc_001_single_image_upload`, `test_preview_page_displays_original_image`, `test_metadata_shown_on_preview`, `test_tc_002_multiple_image_batch`, `test_tc_003_svg_generation_display`, and `test_size_configuration_applied` (CARD-164's, already real). Reviewer-re-fired in cycles 1 and 2.
[Review 1/3] Score: 7.0 (four gating findings, all hollowness in the NEW assertions). F-001 any "N×M px" accepted; F-002 the drawn image never fetched; F-003 an empty SVG accepted; F-004 the field check recognised call shapes instead of denying by reference. All fixed.
[Review 2/3] Score: 9.0 (two new gating findings, both in fix 1's additions). F-008 the field check exempted any function NAMED `_upload`; F-009 a comment claimed the grid was "this picture's". Both fixed.
[Review 3/3] Score: 9.0, NOT certified: two gating findings. F-012, introduced by fix 2: a module-level class named `_upload` became an allowed reader. F-011, first-commit code missed in cycles 1 and 2: `test_tc_002_multiple_image_batch`'s comment claimed more than its assertions hold. The reviewer wrote: with those two edits applied and the file re-run, "I would merge without another review pass".
[Last edit, uncertified] Both were applied after cycle 3, so no review cycle saw the final commit. The F-012 edit is the reviewer's own, verified on its tree; here it was fired again (a class named `_upload` and one named like the check each red the field check; with the two lines removed the first passes). F-011 is a comment-only change. What the merge gate establishes about this commit: that the file and the gate's selection pass, nothing about the claims.
[Declared bound of the field check] It cannot see an address not spelled whole in the file (concatenation, `url_for`) or the constants reached without naming them (`globals()`, `sys.modules`); a value exported from inside `_upload` itself is also unseen and is NOT named in the docstring (reviewer F-013, minor, open).
[Beyond the card] `admin_app` now redirects the temp root per test: measured +7 files per run in the machine upload directory without it, +0 with it; no test asserts that.
[Not carded] Thirteen other test modules post to the upload route with no redirect and leave files in the machine temp directory (reviewer F-007; one measured at 4 files per run, twelve unmeasured).
[Estimate] 1c estimated, 3 cycles used.
