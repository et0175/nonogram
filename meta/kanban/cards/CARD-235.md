# CARD-235: The browser tests stop paying for a page they throw away, 40% of the suite

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/235-browser-fixture-scope
**Worktree:** —
**Source:** CARD-217's profile, 2026-10-15 — `meta/profiling/suite-hotspots-20261015.md`
**Idea:** —
**Wave:** —
**Depends on:** CARD-217 (the measurement; do not start before it merges)
**Touches:** tests/conftest.py, tests/test_puzzle_solver_*.py (12 files), meta/profiling/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Measured, not supposed** (CARD-217, a solo 930.81 s run of 7082 timed tests):

- `tests/test_puzzle_solver_*.py` — 12 files driving Chromium through a shared `browser_page`
  fixture — is **366.19 s, 39.78% of the suite's wall-clock**.
- **A browser test costs 868 ms; every other test costs 83 ms. A 10.4x gap.**
- **96% of the suite's entire teardown time — 137.97 s of 144.37 s — is this family**, at about
  0.33 s per test, with no single test above 0.52 s. The cost is per-test page teardown, which
  is why it appears in no slowest-tests list and why nobody found it before.
- Wave 30 measured 68 ms/test overall; **the non-browser suite today is 83 ms/test**. All twelve
  of these files were first committed between 2026-10-03 and 2026-10-08, after that run, and
  they hold **69% of the +533 s of growth while being 34% of the +1224 new tests**.

So the suite did not get slow. One family arrived and it is expensive per test.

**What to do.** Reduce the number of page set-ups and tear-downs, **not** the number of tests
and not what any test asserts. The lever named by the profile is **fixture scope**: a
`browser_page` created per test pays Chromium's page lifecycle ~420 times. Candidate shapes, to
be chosen on measurement rather than taste:

1. A module- or class-scoped page with per-test state reset (navigate + clear storage), where
   the tests in that module do not mutate anything a reset cannot undo.
2. A shared browser/context with per-test pages only where a test genuinely needs isolation.
3. Leaving a file alone entirely where its tests depend on a fresh page in ways a reset cannot
   reproduce — and saying which files those are, with the reason.

**The risk is the whole card.** Shared browser state is how a suite acquires order-dependence:
tests that pass alone and fail together, or worse, pass together and fail alone. This project
already has one test (`test_web_upload.py`) whose host-shared state makes it fail when another
worktree runs, and it is in the backlog precisely because that class of defect is expensive.
Any scope change must be proved not to have introduced order-dependence, not merely observed to
be green once.

## Acceptance criteria

- **AC-1** (happy, the saving): *Given* the browser family, *when* the suite is profiled again
  by `meta/profiling/rank_durations.py` on a solo run, *then* the family's share is materially
  below 39.78% and the hotspots document records the before and after.
  (test: `TestBrowserFixtures_FamilyShareIsRecorded`)
- **AC-2** (guard, no test lost): *Given* the twelve files, *then* the collected test count and
  every test's node id are unchanged — this card changes fixtures, never coverage.
  (test: `TestBrowserFixtures_NoTestAddedOrRemoved`)
- **AC-3** (guard, no order-dependence): *Given* any file whose page scope changed, *when* its
  tests run in **reverse** order and again in a **shuffled** order with a recorded seed, *then*
  all pass. (test: `TestBrowserFixtures_OrderIndependent`)
- **AC-4** (guard, isolation where it is needed): *Given* a test that mutates page state a reset
  cannot undo, *then* it still gets its own page, and the fixture states which category each
  file is in. (test: `TestBrowserFixtures_IsolationIsDeclaredPerFile`)
- **AC-5** (happy, each test alone): *Given* each changed file, *when* any single test in it is
  run **alone**, *then* it passes — the failure mode where a test silently depends on a
  predecessor's navigation. (test: `TestBrowserFixtures_EveryTestPassesAlone`)
- **AC-6** (edge, a failing test does not poison its neighbours): *Given* a deliberately failed
  test on a shared page, *then* the tests after it in the same module still pass.
  (test: `TestBrowserFixtures_AFailureDoesNotCascade`)

## Guardrails

- G-1: No test's assertions change. This card may change set-up and teardown only; a diff that
  touches an `assert` is out of scope and must be reported instead.
- G-2: ADR-0038/R7 pins Chromium; this card does not change the browser or the runner.
- G-3: The saving is measured by the committed `rank_durations.py` on a **solo** run, by
  CARD-217's own method — not by a stopwatch and not on a shared host.
- G-4: No new dependency (ADR-0006/R1); `pytest-playwright` is already installed.
- G-5: Out of scope — the render-heavy files (CARD-218/219) and the admin-local script trio
  (CARD-236).

## System contract

- ADR-0038/R7 — the player's tests run under Chromium (check: review-lens)
- ADR-0038/R1 — the player is plain JS with no build step (check: review-lens)
- ADR-0006/R1 — no new runtime dependency (check:
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`)

## Architecture context

- **FR:** FR-044 (the player), whose tests these are.
- **ADR:** ADR-0038/R1, ADR-0038/R7.
- **Components:** COMP-008 (the admin panel's player surface) — tests only.
- **Trace:** not updated by this card.

## Worktree notes

- [Why this is P1 and ahead of the curation cards] It is 39.78% of the suite against the render
  family's 21.23%, and the gate runs once per card and once per wave. CARD-218/219/220 were cut
  on the render hypothesis before anyone had measured; CARD-217 measured, and this is where the
  time actually is.
