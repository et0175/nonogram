# CARD-474: The upload test counts only its own temp directories, so a second worktree cannot red it

**Status:** review
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
**Touches:** tests/test_web_upload.py, tests/test_card_037_upload_retry.py
**UI surface:** none
**Review score:** 9.0 (cycle 3/3 - CERTIFIED)
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

[Start] Implemented by the orchestrating session itself, not a spawned agent (a 46-line test-only change); reviewed by one independent agent across all three cycles. Branch tip `6ec23678`, three commits.
[Review 1/3] Score: 7.5 (below 8.0; one gating finding). F-001: `tests/test_card_037_upload_retry.py` imports the reading without the fixture, so two of its tests still redden under a foreign file. Fixed by importing `_own_temp_root` there (Touches grew by that file; the reviewer ruled it in scope, since IDEA-069 names both modules). Minors F-003 (control now uses `multipart._write_temp_file`) and F-004 (helper docstring) fixed in the same commit.
[Review 2/3] Score: 8.0 (one NEW gating finding, introduced by fix 1). F-005: the redirect directory sat under `tmp_path`, so `test_resubmitting_with_the_token_re_uses_the_picture`'s listing of `tmp_path` could no longer fail. Fixed: the directory comes from `tmp_path_factory`.
[Review 3/3] Score: 9.0, no gating findings, certified. Reviewer-reported; the merge gate has not run yet. Open minor F-002, by design: the control puts one upload-shaped file in the machine temp dir for an instant, which AC-1 asks for.
[AC-2, as measured] The two cleanup tests red only with BOTH deletion sites neutralised (the store's and the handler's `finally`); either alone survives in this module, before the card as after. The reviewer ruled it legitimate redundancy: the store's deletion is killed by the retry module's tests.
[Not carded] `tests/test_card_043_clear_message_on_new_image.py` leaves two upload temp files in the machine temp dir per run (reviewer-measured). Not run under pytest-xdist; the project does not use it.
[Estimate] 1c estimated, 3 cycles used.
