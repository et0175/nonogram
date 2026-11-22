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
**Review score:** 9.0 (cycle 3/3 - CERTIFIED)
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

[Review 1/3] Score: 8.5, one gating finding, not certified. All four ACs and both guardrails hold: I1 reds with `('inches', '8.5', ... width ...)`, I1h and I1m with `('inches', '11', ... height ...)`, I1s with `('inches', '6', ... width ...)`, S1 and S2 red, unmutated 9 passed; judging from the HTML is sound for today's page; net count 0. F-001 (Important, violates ADR-0039/R2): the "no script writes a bound" check matches two hand-picked spellings in inline scripts only, so `Object.assign(width, {min: …})`, `width['min'] = …` and `setAttribute(k, v)` with the name in a variable (B1-B3) each leave the class green, and an external `<script src>` is never read; the test docstring claims more than that. F-002 (low, pre-existing): `_browser_admits` takes the step base as `min` else 0, where the HTML rule is `min`, else the `value` attribute, else 0; no verdict differs today because stored trims sit on the 0.01 grid.

- [Fix round 1, 2026-11-22] F-001: the script check in `test_the_cm_form_admits_each_trim_in_either_unit` now refuses by default. (a) Every `<script src>` must be in the class's `EXEMPT_SCRIPT_SRCS`, held EQUAL to the rendered srcs (today only Bootstrap's pinned 5.3.0 bundle, which is exempted unread). (b) No inline script may name `min`/`max`/`step` as a word, `Math.min`/`Math.max` aside. (c) No inline script may use `set/remove/toggleAttribute`, `attributes`, `Object.assign`, `Reflect`, `defineProperty`, `eval`, `Function(` or a bracket assignment `] =`. The `updateUnits` presence assert is kept. `_TrimInputs` records `script_srcs`. The docstring now lists exactly these checks and names the gap: a name assembled at run time and written through a path not in (c). Each mutant gave '1 failed, 8 passed' on that test, and the assert that fired is named:
  - B1 `Object.assign(width, {min: ...})`: token rule (b).
  - B2 `width['min'] = ...`: token rule (b).
  - B2f `width['mi' + 'n'] = '10'`: dynamic rule (c).
  - B3 `['mi' + 'n'].forEach(k => width.setAttribute(k, '10'))`: dynamic rule (c).
  - B4 `width.min = '10'`: token rule (b).
  - S1, S2: token rule (b).
  - X `<script src="/static/print_units.js">` added: `assert set(read.script_srcs) == self.EXEMPT_SCRIPT_SRCS` -> `AssertionError: ['/static/print_units.js', 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js']`.
  - I1, I1h, I1m, I1s re-run: red on the same lines as before.
  - M0 (`Math.max(1, Math.min(2, 3))` added to `updateUnits`): '9 passed', so the Math exclusion does not over-refuse.
  - All template mutants restored by `git checkout`; `git status` afterwards shows only the test file modified.
- [Fix round 1] F-002: `_browser_admits` takes the step base as `min`, else the `value` attribute when it parses as a finite number, else 0. The control is inside `test_a_page_reopened_on_an_inches_trim_admits_its_own_values` and needed no new test: an off-grid prefill (`value` 21.005) must put 8.5 off the grid. Control H1 (helper base reverted to min-else-0) -> '1 failed, 8 passed', `assert not _browser_admits(off_grid, "8.5")` / `where True = _browser_admits(..., '8.5')`. Test file restored from a byte copy (`cmp` equal).
- [Fix round 1] Gate, unarmed, `-o addopts= -rfs`: tests/test_book_workflow_steps.py tests/test_book_setup_print_mobile.py tests/test_book_trim_persistence.py -> '260 passed, 1 warning', 0 skipped. Collected count `--collect-only -q -o addopts= tests/`: 10692 (re-derived); net 0 against the 10692 base.

[Review 2/3] Score: 8.5, one gating finding, not certified. Holds: today's page green (130 passed); I1, I1h, I1m, I1s red; cycle-1 bypasses B1-B3, S1 and X red; a template literal, `attributes.setNamedItem` and a `<template><script>` red; F-002's step base is right per the HTML spec (control H1 reds); the exemption list is one pinned Bootstrap URL held equal to the rendered srcs; net 0. F-001 (Important, ADR-0039/R2): script outside `<script>` text and `<script src>` is never read, and each of these leaves 9 passed: an inline `onchange` handler writing `width.min` (the page already uses three inline handlers), `<script type="module">import …`, a dynamic `import()`, `createElement('script')`, and an `<iframe srcdoc>`. F-002 (low): honest edits such as a comment containing "max" or "step" red with no message saying why or what to do. F-003 (low): the docstring's declared gap has no failing control (`setAttribute` via an alias, `setAttributeNS`, `setAttributeNode` each 9 passed).

**Orchestrator, before cycle 3.** Two rounds of pattern-matching have each found new carriers, so the static script check cannot be made complete. Cycle 3 replaces it with a measurement: the existing browser fixtures open the page in centimetres, switch the unit to inches as a user does, and ask the browser itself whether each trim is admitted.

- [Fix round 2, 2026-11-22] Review 2 F-001: the approach changed from pattern-matching to measuring in a browser. Added `TestPrintSetup_InchesTrimIsReachable.test_a_browser_admits_each_inches_trim_after_switching_a_cm_page`, marked `@pytest.mark.browser`.
  - Fixtures are reused, not built: `browser_page`/`browser_type` are imported from tests/test_puzzle_solver_page.py and `live_book` from tests/test_book_setup_print_mobile.py, the existing Print setup browser file. Neither file is edited.
  - What the test does: it opens Print setup in a fresh session, which opens in cm (asserts `#unit_cm` is checked). It clicks `label[for=unit_inches]` as a user does, then asserts `#unit_inches` is checked and `#width_unit` reads "in". For 8.5 x 11, 8 x 10 and 6 x 9 it fills `#width`/`#height` and asks Chromium: each input's `validity.valid` and `checkValidity()`, then `form.checkValidity()`. Each assert message names the trim, the field and the validity flags. The test also asserts no `pageerror`.
  - The static script guard, `EXEMPT_SCRIPT_SRCS` and `_TrimInputs`' script collection are removed. `test_the_cm_form_admits_each_trim_in_either_unit` keeps the HTML check of both units, and its docstring now says it sees only the rendered bounds, not the script. The F-002 step base and its control are kept.
  - Chromium was available; the test ran, it did not skip.
- [Fix round 2] Controls, each against the browser test (script /private/tmp/claude-501/card520/mutants3.py):
  - Today's page: '1 passed'; whole class '10 passed'.
  - I1 -> '1 failed': `AssertionError: ('8.5 x 11 in', 'width', {'value': '8.5', 'valid': False, 'checkValidity': False, 'rangeUnderflow': True, ...})`.
  - I1h -> `('8.5 x 11 in', 'height', {'value': '11', 'valid': False, ..., 'rangeUnderflow': True, ...})`.
  - I1m -> `('8.5 x 11 in', 'height', {'value': '11', 'valid': False, 'checkValidity': False, 'rangeUnderflow': False, ...})` (an overflow).
  - I1s -> `('6 x 9 in', 'width', {'value': '6', 'valid': False, ..., 'rangeUnderflow': True, ...})`.
  - EH (the Inches radio's inline `onchange` also writes `width.min = '10'`) -> `('8.5 x 11 in', 'width', {... 'rangeUnderflow': True ...})`; the HTML test stays green under it ('1 failed, 9 passed' for the class).
  - DI (`updateUnits` runs `import('/static/card520_bound.js')`, a file created for the run that writes `width.min = '10'`) -> the same width line; class '1 failed, 9 passed'.
  - FV, for the form-level assert alone (`player_domain` made `required`, so both trim inputs stay valid) -> `('8.5 x 11 in', 'form', {... 'form': False})`.
  - H1 (F-002 helper base reverted) -> `test_a_page_reopened_on_an_inches_trim_admits_its_own_values` red at `assert not _browser_admits(off_grid, "8.5")`.
  - Restores: the template by `git checkout` (template diff clean), the static file deleted (checked absent), and the test file from a byte copy (`cmp` equal). Afterwards `git status` showed only the test file modified.
- [Fix round 2] Gate, unarmed, `-o addopts= -rfs`: tests/test_book_workflow_steps.py tests/test_book_setup_print_mobile.py tests/test_book_trim_persistence.py tests/test_impact_set.py -> '461 passed, 1 warning', 0 skipped. test_impact_set.py was added because this file now imports a test module's fixture.
- [Fix round 2] Net count, `--collect-only -q -o addopts= tests/`: 10693 now, against 10692 at HEAD without this round (the change stashed, re-derived). tests/test_book_workflow_steps.py: 131 against 130. Net +1, the browser test, as AC-4 allows.
- [Fix round 2] Not established: DI's red depends on the dynamic import resolving before the fills are read. It did resolve in time on this run, but the test does not wait for it.

[Review 3/3] Score: 9.0, nothing gating, certified. `test_a_browser_admits_each_inches_trim_after_switching_a_cm_page` is not vacuous: a failed load times out on `#unit_cm`, the switch is proven by `#unit_inches` checked and `#width_unit` reading "in", all three trims fill both fields, and the input's own form is read. I1 reds both tests; EH, CE and DI red the browser test. Stable: the class 5 times and the browser test 5 times, all green. Fixture imports collect nothing twice; Chromium absent fails loudly per ADR-0038/R8; ADR-0039/R2 now holds. Net +1. F-001 (low): the field's final value is not asserted, so an `oninput` that rewrites 8.5 to 10 passes. F-002 (low): validity is read without waiting for asynchronous work; a `setTimeout` bound write passes, and DI/CE red by timing; today's page has none.
