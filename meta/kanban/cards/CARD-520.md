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
- [Premise] Re-verified on the branch base before any change (scratch script /private/tmp/claude-501/card520/mutants.py, template mutated then restored by `git checkout`): mutant I1 (width `min="10"` only when `unit_preference == 'cm'`) leaves `TestPrintSetup_InchesTrimIsReachable` at '9 passed'; so does the height variant I1h (`min="12"` on height, cm only) and I1s (width `min="7"`, cm only, refuses 6 x 9 alone). The max-side variant I1m (height `max="10.99"`, cm only) was already red on the base, on the cm figure 27.94: any `max` that refuses 11 in also refuses 27.94 cm, so no max-side mutant of this shape can survive the old cm assert.
- [Browser or HTML] The unit radios' `updateUnits` only sets the two unit spans' text and writes no bound, so the bounds a browser applies after switching to inches are those rendered with the cm page; the server's HTML is enough and no Playwright test was added. That premise is itself asserted, not assumed: the test fails if any script on the page sets/removes/toggles `min`/`max`/`step` (via `.min =` etc. or `*Attribute('min'...)`), and fails if the `updateUnits` script is not among the scripts read (non-vacuity).
- [Change] `tests/test_book_workflow_steps.py`: `test_the_cm_form_admits_the_same_trim_in_cm` renamed `test_the_cm_form_admits_each_trim_in_either_unit` and extended: on a page opened in cm it judges 8.5 x 11, 8 x 10 and 6 x 9 in inches and their cm figures (`INCH_TRIMS`) against the rendered bounds with `_browser_admits`, after the script premise check. `_TrimInputs` now also collects `<script>` text. Old name referenced only in meta/profiling duration dumps; requirements/trace refs (main and CARD-519's branch) name the class, which is unchanged. No page or script change (G-1); requirements.yml untouched (G-2).
- [AC-1] I1 -> '1 failed, 8 passed': `test_the_cm_form_admits_each_trim_in_either_unit`, `AssertionError: ('inches', '8.5', {... 'id': 'width' ...})` / `where False = _browser_admits({... 'id': 'width' ...}, '8.5')`. Restored: '9 passed'.
- [AC-2] I1h -> '1 failed, 8 passed', same test, `AssertionError: ('inches', '11', {... 'id': 'height' ...})`. I1m -> '1 failed, 8 passed', same test, `AssertionError: ('inches', '11', {... 'id': 'height' ...})` (inches are judged before cm, so the red names the inch figure).
- [AC-3] All three trims are in the loop; I1s (refuses only 6 in) -> '1 failed, 8 passed', `AssertionError: ('inches', '6', {... 'id': 'width' ...})`, which the old 8.5 x 11-only checks missed.
- [Controls for the premise asserts] S1 (`updateUnits` sets `width.min`) and S2 (`updateUnits` calls `setAttribute('max', '30')` on height) -> each '1 failed, 8 passed' on the same test, the assert printing the `updateUnits` script. Renaming `updateUnits` to `relabelUnits` in the template -> '1 failed, 8 passed', `where False = any(...)` (the non-vacuity assert). Every mutant restored; `git diff --stat` afterwards shows only the test file.
- [AC-4] Collected count `--collect-only -q -o addopts= tests/`: 10692 before, 10692 after; net 0.
- [Gate] unarmed, `-o addopts= -rfs`: tests/test_book_workflow_steps.py tests/test_book_setup_print_mobile.py tests/test_book_trim_persistence.py -> '260 passed, 1 warning', 0 skipped. Not run armed (the card names no armed run; the changed test uses the in-memory `panel`).
