# CARD-057: ADR-0006/R1's dependency baseline is stale — reportlab was added without updating it

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/057-adr-0006-dependency-baseline-drift
**Worktree:** ../PythonProject4-CARD-057
**Source:** CARD-045 cycle 1 review, Step 8h spot-check (re-derivation) — meta/review/20260911T073855Z-CARD-045-cycle1.yml
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** meta/architecture/decisions/adr/0006-*.md, pyproject.toml
**Review score:** —
**Started:** 2026-09-11T14:25:00Z
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

## Worktree notes

**Investigated intent (step 1) before touching anything:** grepped the
whole repo for `reportlab` imports — exactly one file,
`src/nonogram/admin/pdf_generator.py` (`BookPDFGenerator`, added by
commit `838c407`, "CARD-008: Implement Book PDF Generation with
ReportLab", 2026-09-07), confirmed genuinely wired into a live route
(`app.py`'s `POST /book/<book_id>/generate-pdf`). Confirmed
`nonogram.export.pdf` (the core CLI/orchestrator pipeline's own PDF
exporter) does NOT import reportlab and its own docstring/tests
explicitly reject it (CARD-014's decision, unaffected). So reportlab is
a deliberate, real, live dependency — not a mistake to remove.

**Found a better resolution than the card's own step 2/3 options.**
`pyproject.toml`'s `admin` extras group already correctly holds
Flask/Werkzeug (also admin-only) separately from core `dependencies` —
but `reportlab` had been placed in core `dependencies` instead of that
same `admin` extra, meaning a bare `pip install nonogram` (CLI-only)
was silently pulled a third heavyweight dependency it has no use for.
Rather than widening ADR-0006/R1's "closed baseline" claim to
permanently include reportlab in the CLI's install footprint (step 2),
moved `reportlab>=4.0` into the `admin` extra where it belongs. This
restores ADR-0006/R1's ORIGINAL statement as literally true again —
**no ADR text revision was needed**, and `tests/test_export_pdf.py`
needed **zero changes** (its existing assertion,
`packages == {"pillow", "numpy"}`, is now true again). Documented the
finding as a packaging-fix History entry in the ADR (not a "Revised"
decision, since R1's content is unchanged) for traceability, so a
future reader understands why CARD-008's reportlab addition doesn't
appear as an ADR revision the way CARD-032's font addition did.

(First attempted the "revise ADR-0006/R1 to include reportlab in the
closed baseline" path per the card's literal step 2, including a
check.ref rename to avoid the same staleness recurring — fully
implemented, then discarded via `git checkout` once the misplaced-
dependency finding made the packaging fix the clearly better
resolution. No half-finished trace of that path remains.)

**AC-1 verified:** `./.venv/bin/python -m pytest
tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed -v`
passes, with the test file completely unmodified.

**AC-2 verified:** `system_rules.py --scope 'src/nonogram/**'
--verify-refs` shows `ADR-0006/R1`'s original, unmodified statement,
`check_refs_verified: true`, `dead_check_ref: []`.
`architect-validate/scripts/validate.py --phase all` — 0 errors, same 2
pre-existing warnings as before this card (ADR-0006's `Migration:`
field format, missing `trace.yml` — unrelated, confirmed identical to
the pre-card baseline).

**Regression check:** `test_export_pdf.py` + `test_pdf_generator.py` +
`test_book_scaffolding.py` + the structural import-boundary guard —
97/98 pass, 1 pre-existing unrelated failure
(`test_the_font_ships_as_package_data_and_not_as_a_dependency`, a
`KeyError: 'package-data'` confirmed present on `main` before this
card, unrelated to dependency grouping). Full suite: 41 failures, all
in the previously documented flaky/corpus-dependent classes (same set
seen across CARD-046/047/054's baseline runs, within the established
39-42 range), none touching `pyproject.toml`, `admin/pdf_generator.py`,
or dependency resolution.
