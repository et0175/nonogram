# CARD-474: The upload test counts only its own temp directories, so a second worktree cannot red it

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** false <!-- the card changes a test helper, not product code -->
**Branch:** card/474-upload-test-own-temp-dirs
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-474
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-108, WSJF 10.0); premise re-read against main on 2026-11-18. Origin: wave 37 retrospective (cost CARD-211 a failed run); the same defect is logged a second time as IDEA-069.
**Idea:** IDEA-108
**Wave:** 80
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_web_upload.py
**UI surface:** none
**Review score:** —
**Started:** 2026-11-18T08:35Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/test_web_upload.py` proves the upload's `finally` cleans up by listing `nonogram-upload-*` under `tempfile.gettempdir()` before and after. That directory is machine-wide: an upload test running in another worktree at the same moment adds or removes an entry between the two readings and the test goes red on a correct tree. The board runs two worktrees at once, so this is the ordinary case.

## What to implement

Make the before/after listing see only directories this test process can have created: point the process's temp root at the test's own `tmp_path` for the duration (`monkeypatch` of `tempfile.tempdir`, or the equivalent the helper's callers already allow), and list that. Keep the helper's meaning — "the upload leaves nothing behind" — unchanged.

## Acceptance criteria

* **AC-1**: with a foreign `nonogram-upload-*` directory created and removed in the machine temp dir while the test runs, the cleanup tests still pass (one planted control in the existing module).
* **AC-2**: the control that proves the check can fail survives: an upload path with its cleanup removed still reds the same test.
* **AC-3**: net test count for the card: +1 at most (the plant in AC-1); no test deleted.

## Guardrails

* **G-1**: `src/` is not touched — the upload code already cleans up; only the measurement was wrong.
* **G-2**: IDEA-069 is the same defect; the closing commit names both so neither is carded again.

## Worktree notes

—
