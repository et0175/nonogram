# CARD-048: Widen ADR-0022/R3 and R4 scope.code to include the admin panel

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/048-adr-0022-scope-admin
**Worktree:** —
**Source:** meta/review/20260910T164426Z.yml#F-006
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** meta/architecture/decisions/adr/0022-grid-extent-and-size-range.md
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-09-11T13:25:00Z
**Closed:** 2026-09-11T13:55:00Z
**Actual:** 0.05d
**Merge commit:** b154886
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

## System contract

_(no rule's scope.code covers meta/architecture/** — this is a documentation-only diff outside any code-scoped rule; confirmed by running system_rules.py --scope 'meta/architecture/**' → rules: [].)_

[Review 1/3] Score: 8.5 — crit: 0, imp: 1
[Review sync] 1 report(s) → meta/review/ (20260911T111738Z-CARD-048-cycle1.yml)
[Adversarial] 1 gating finding — verified independently before fix (not
just trusted from the review): read image_manager.py's predict_size()
directly and confirmed its SizeTooSmallForSource except-branch silently
substitutes a workable N via a range() search instead of refusing with
a named-smallest-N message — the opposite of R4's refusal-and-message
clause. The reviewer's finding (F-001: the new ADR text overclaimed
that R4's checks "genuinely reach admin's behaviour" for both of R4's
clauses, when only the arithmetic clause actually transfers) is
CONFIRMED, not a false positive.
Cycle 1 summary (forge:review): AC-1/AC-2 independently re-verified and
held cleanly (system_rules.py before/after, validate.py on both
main and this branch — identical diagnostics). R2's exclusion rationale
verified factually correct by reading predict_size()/validate_extent
directly. R3's widening verified fully justified (image_to_puzzle.py
genuinely delegates to sourcing.image.generate, propagating
NonogramError as expected). The one Important finding was about R4's
justification text overclaiming, not about AC-1/AC-2 or the scope
widening decision itself — the reviewer's own read: "everything else
... independently re-derived and confirmed correct." Zero Critical, 1
Important, zero Minor. Risk: LOW, lane: FAST. Score 8.5 ≥ min_score 8
but gate requires zero Critical/Important — cycle 1 does NOT clear.

[Fix round 1] Narrowed the Negative-consequence bullet and History
entry to state precisely that R4's widening is justified for its
derivation-arithmetic clause (admin calls derive_extent directly) but
NOT for its refusal-and-message clause (admin's predict_size() silently
substitutes a workable N on SizeTooSmallForSource rather than refusing
with a message, per its own docstring comment). Named a follow-up
(surface an explicit substitution message in the admin UI) as a
candidate future card, out of this scope-only card's Touches — not
created here per protocol (implementer doesn't unilaterally spawn new
kanban cards; flagged for the user/orchestrator instead). Re-verified
AC-1 (R3/R4 still appear, check_refs_verified: true) and AC-2 (0
errors, same 2 pre-existing warnings) fresh after the fix. Commit
3732d60.

CYCLE 1 — 1 Important finding, fixed same-day. Proceeding to cycle 2
(confirmation mode: fix delta only, everything else carried forward as
delta-clean per the review's own "independently re-derived and
confirmed correct" verdicts on AC-1/AC-2/R2/R3).

[Review 2/3] Score: 9.5 — crit: 0, imp: 0 (CONFIRMATION MODE)
[Review sync] 1 report(s) → meta/review/ (20260911T112249Z-CARD-048-cycle2.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 2 summary (forge:review, CONFIRMATION MODE): fix-delta (3732d60)
reviewed at full depth — the overclaim phrase confirmed removed (grep,
not relocated elsewhere), new R4 text independently re-verified against
image_manager.py:108-119 line-for-line. F-001 explicitly verdicted
CLOSED, not just "no longer flagged." R2 exclusion rationale, R3
widening justification, and the meta/architecture/** system-contract
N/A all carried forward as delta-clean (fix-delta's touched lines
mechanically confirmed not to intersect their scope). AC-1/AC-2
independently re-derived fresh on this cycle too (not reused from
cycle 1's report) — both hold, byte-identical validator diagnostics
to main. Zero Critical/Important. Risk: LOW, lane: FAST. Score 9.5 ≥
min_score 8, zero Critical/Important — severity gate OPEN. This is the
passing cycle (2 of 3).

[8h spot-check] 3/3 sampled holds reproduced — independently re-ran
both AC-1 (system_rules.py) and AC-2 (validate.py) fresh, and
independently re-grepped for the overclaim phrase (zero hits).

[AC/EC check] Both criteria ✓ (evidence):
AC-1 ✓ demonstrated — evidence: system_rules.py --scope 'src/nonogram/admin/**' --verify-refs shows ADR-0022/R3 and R4 in rules:, check_refs_verified: true; absent on main.
AC-2 ✓ demonstrated — evidence: validate.py --phase all reports 0 errors on both this branch and main, with byte-identical warning sets (2 pre-existing, unrelated to this ADR).

Both items independently re-verified across two review cycles and one
final gate pass. Gate passes. No engineering constraints beyond
documentation-only (per the card itself); none violated.

[Docs] This IS the documentation change (the card's whole Touches is
one ADR file); no other README/doc needs updating.

[Commit] Final state is 2 commits on the branch: 60406d3
(implementation) and 3732d60 (fix round 1, addressing cycle 1's sole
Important finding). Nothing further needed — cycle 2 cleared cleanly.

CYCLE 2 COMPLETE — SUCCESS. Ready for `/kanban done CARD-048`.

Note for follow-up (not created here, per protocol — implementer/review
agents flagged it twice but did not unilaterally spawn a card): admin's
`predict_size()` silently substitutes a workable N instead of refusing
with a message on `SizeTooSmallForSource` — a real, live divergence
from ADR-0022/R4's refusal-and-message clause, now documented and
auditable but not yet fixed. A small follow-up card to surface an
explicit substitution message in the admin UI would close this gap.
