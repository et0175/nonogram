# CARD-057: ADR-0006/R1's dependency baseline is stale — reportlab was added without updating it

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/057-adr-0006-dependency-baseline-drift
**Worktree:** —
**Source:** CARD-045 cycle 1 review, Step 8h spot-check (re-derivation) — meta/review/20260911T073855Z-CARD-045-cycle1.yml
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** meta/architecture/decisions/adr/0006-*.md, pyproject.toml, tests/test_export_pdf.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`ADR-0006/R1` states: "The runtime dependency set is exactly stdlib + Pillow +
NumPy. No third-party package joins the installed dependencies without
revising this ADR", with a declared mechanical check
(`check: {kind: test, ref: TestDependencyBaseline_IsExactlyPillowAndNumpy}`,
in `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`).

That test currently **fails on `main`**:
`AssertionError: assert {'numpy', 'pillow', 'reportlab'} == {'numpy', 'pillow'}`
— `reportlab>=4.0` is already listed in `pyproject.toml` (commit `5d5eda8`),
presumably for PDF export, but `ADR-0006/R1` was never revised to say so, and
the test was never updated either. This means the ADR's own declared
mechanical check has been silently broken since `5d5eda8` landed — any
system-contract review scoped to `src/nonogram/**` (which is essentially
every review) reports `ADR-0006/R1 ✓ holds` on the strength of a check that
does not actually pass, because reviewers correctly note "not touched by
this diff" without re-running the check itself, and the review's own re-
derivation spot-check (forge:review's Step 8h holds check, when it runs)
would flag every future card's review the same way this one did.

Discovered during CARD-045's cycle-1 review spot-check re-derivation —
unrelated to CARD-045's own diff (`image_manager.py`/
`test_image_batch_size_fix.py`), which does not touch dependencies.

1. Decide the actual intent: does this project deliberately depend on
   `reportlab` now (for PDF export, most likely — check `src/nonogram/export/pdf.py`
   and `src/nonogram/admin/book_pdf_generator.py`/`pdf_generator.py` for usage),
   or was it added by mistake / should it be replaced with something already
   in the baseline?
2. If `reportlab` is a deliberate, real dependency: revise `ADR-0006/R1`'s
   statement to name the actual current baseline (stdlib + Pillow + NumPy +
   reportlab, or whatever the true set is — check `pyproject.toml` directly
   rather than assuming), and update
   `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`
   (and the `TestDependencyBaseline_IsExactlyPillowAndNumpy` reference in the
   ADR's `check:` block) to match.
3. If `reportlab` was NOT a deliberate baseline change: remove it and whatever
   depends on it, or replace it with an existing baseline library, restoring
   the ADR's original claim.
4. Either way, re-run
   `python3 <forge-plugin-path>/skills/architect-validate/scripts/system_rules.py --root meta/architecture --scope 'src/nonogram/**'`
   and confirm `ADR-0006/R1`'s `check:` ref now actually passes.

## Acceptance criteria

- **AC-1** — given the ADR/dependency reconciliation is complete, when
  `./.venv/bin/python -m pytest tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed -v`
  is run, then it passes.
- **AC-2** — `ADR-0006/R1`'s statement in
  `meta/architecture/decisions/adr/0006-*.md` accurately describes the
  runtime dependency set as it actually is in `pyproject.toml` after this
  card (no more silent drift between the two).

## Engineering constraints

None — this is a documentation/test reconciliation, or a dependency removal;
no new production behavior.
