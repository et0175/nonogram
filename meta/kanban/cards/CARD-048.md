# CARD-048: Widen ADR-0022/R3 and R4 scope.code to include the admin panel

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/048-adr-0022-scope-admin
**Worktree:** ../PythonProject4-CARD-048
**Source:** meta/review/20260910T164426Z.yml#F-006
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** meta/architecture/decisions/adr/0022-grid-extent-and-size-range.md
**Review score:** —
**Started:** 2026-09-11T13:25:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`system_rules.py --scope 'src/nonogram/admin/**'` matches only `ADR-0006/R1`
and `ADR-0022/R1`. `ADR-0022/R2`'s `scope.code` is
`["src/nonogram/sourcing/**", "src/nonogram/cli.py"]`, `R3`'s is
`["src/nonogram/sourcing/image.py"]`, and `R4`'s is
`["src/nonogram/cli.py", "src/nonogram/orchestrator.py", "src/nonogram/sourcing/**"]`
— none include `src/nonogram/admin/**`.

`ec18fb4` made `admin/image_manager.py` a real, direct consumer of R4's "N on
the longer axis, never capped at the top" rule (it now calls `derive_extent`
directly) and of R3's crop policy indirectly (via `image_to_puzzle.py` calling
`sourcing.image.generate`). Functionally this is safe today — admin calls the
shared functions rather than reimplementing their arithmetic, so behavior stays
in sync automatically with any future change to `derive_extent`/`generate`
themselves. But an automated system-contract audit of R3/R4 compliance
(`system_rules.py --scope ...`) does not see `admin/` as in-scope territory to
check at all — so a *future* admin-side change that bypassed `derive_extent` or
`sourcing.image.generate` (reintroducing the exact bug `ec18fb4` fixed) would
not be caught by any mechanical or review-lens check tied to these rules.

1. Add `"src/nonogram/admin/**"` to `scope.code` for `ADR-0022/R3` and `R4` in
   `meta/architecture/decisions/adr/0022-grid-extent-and-size-range.md`'s
   `## Rules` YAML block.
2. Consider whether `R2` (the 10..30 range validation) should also be widened —
   `admin`'s `predict_size()` re-derives its own `stated` value and clamps it
   independently rather than calling `validate_extent` directly, so R2's
   `check: {kind: test, ref: TestValidateExtent_RejectsSideAboveThirty}` would
   still not exercise admin's clamp even with a widened scope; note this as a
   known gap in the ADR's `## Consequences` rather than silently widening a rule
   whose `check:` wouldn't actually cover the new territory.
3. Re-run `system_rules.py --scope 'src/nonogram/admin/**' --verify-refs` after
   the edit and confirm R3/R4 now appear in the matched set.

## Acceptance criteria

- **AC-1** — given the scope edit is applied, when
  `system_rules.py --root meta/architecture --scope 'src/nonogram/admin/**'` is
  run, then `ADR-0022/R3` and `ADR-0022/R4` appear in the `rules:` output.
- **AC-2** — the ADR's own consistency is preserved: no existing accepted
  clause is contradicted by the scope widening (this is a scope-declaration
  change, not a decision change).

## Engineering constraints

None — documentation-only change to the architecture model, no production code
touched.

## Worktree notes

**Implementation:** widened `ADR-0022/R3` and `R4`'s `scope.code` in the
`## Rules` YAML block to include `"src/nonogram/admin/**"`. Step 2
(consider widening R2) was resolved as: deliberately **not** widened,
documented as a known/accepted gap in a new Negative consequence bullet
— `admin/predict_size()` clamps its own `stated` value independently
rather than calling `validate_extent` directly, so R2's `check`
(`TestValidateExtent_RejectsSideAboveThirty`, which exercises
`validate_extent` alone) would not actually reach admin's clamp; a
scope claiming coverage a rule's check can't reach is worse than an
honestly absent one. Added a `## History` entry (2026-09-11, "Scope
widened, no decision change") for traceability, consistent with the
ADR's own convention, without bumping `Status`/`Revised` — AC-2
requires this be a scope declaration, not a decision revision, and no
existing accepted clause is contradicted.

**AC-1 verified:** `system_rules.py --root meta/architecture --scope
'src/nonogram/admin/**' --verify-refs` — before the edit, only
`ADR-0006/R1` and `ADR-0022/R1` appeared; after, `ADR-0022/R3` and `R4`
both appear, with `check_refs_verified: true` (their check refs,
`TestFitImage_RefusesRatioMismatchBeyondTwice` and
`PropertyTest_BareSize_DerivesShorterSideFromSourceShape`, still exist
and were not touched).

**AC-2 verified:** `architect-validate/scripts/validate.py --root
meta/architecture --phase all` — 0 errors both before and after the
edit; the 2 pre-existing warnings (ADR-0006's `Migration:` field format,
missing `trace.yml`) are identical on `main` and this branch — confirmed
unrelated to this change, not newly introduced.

**Regression check:** documentation-only change (Engineering
constraints: none, no production code touched) — no test reads the ADR
markdown file's content directly (grepped `tests/*.py` for
`scope.code`/the ADR's filename, zero hits). `tests/test_cli.py`
(includes the ADR-0007 structural import-boundary guard) — 86/86 pass,
unaffected as expected.
