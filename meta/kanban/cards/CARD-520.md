# CARD-520: A page opened in centimetres admits an inches trim: a test that catches CARD-159's bug coming back

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/520-inches-trim-regression
**Worktree:** ../PythonProject4-card-520
**Source:** roadmap wave 11, cut 2026-11-22 on the owner's "yes, add a card for the CARD-159 regression test", after CARD-519 review 1 F-002.
**Idea:** —
**Wave:** 90
**Created wave:** 90
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_workflow_steps.py
**UI surface:** Print setup (test only)
**Review score:** —
**Started:** 2026-11-22T11:03Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-159 fixed Print setup refusing a valid inches trim: the size inputs carried centimetre bounds, and the unit switch only relabels the units, so a page opened in centimetres kept bounds that refused 8.5 x 11 in. CARD-519's review (F-002) showed that nothing catches that bug coming back: mutant I1, which puts `min="10"` on the width input only when the page opens in centimetres, leaves all 9 tests of `TestPrintSetup_InchesTrimIsReachable` green. `test_the_cm_form_admits_the_same_trim_in_cm` checks only the centimetre figures, and the reopened-page check covers only 8.5 x 11.

## What to implement

Re-verify on main first: reproduce mutant I1 and show the class stays green. Then change the existing tests in `TestPrintSetup_InchesTrimIsReachable` (no new test function if a parametrisation or an extra assert will do) so that a page opened in centimetres is shown to admit each common inches trim (8.5 x 11, 8 x 10, 6 x 9) once the unit is inches, judged by the bounds the page actually renders. If only a browser can judge it (the unit switch is script), use the project's existing browser-test helpers rather than a new harness, and say why.

## Acceptance criteria

* **AC-1**: with mutant I1 applied, a named test in `TestPrintSetup_InchesTrimIsReachable` reds, quoting its failing assertion; restored, it is green.
* **AC-2**: the same holds for a height-only and a max-side variant of the mutant (a bound on height, or a `max` that refuses 11 in), each shown red.
* **AC-3**: 8.5 x 11, 8 x 10 and 6 x 9 are each covered on a page opened in centimetres.
* **AC-4**: net test count at most +1 (prefer 0: parametrise or extend). Report it.

## Guardrails

* **G-1**: no change to the Print setup page or its script; this card adds verification only.
* **G-2**: requirements.yml is not edited here; CARD-519 owns AC-423's wording, and once this lands its claim can be widened in a later edit.

## Worktree notes
