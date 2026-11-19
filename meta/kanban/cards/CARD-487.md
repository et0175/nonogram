# CARD-487: ADR-0029/R4's check tests its own rule, not the import graph

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/487-r4-check
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 3 (IDEA-006, WSJF 3.85); premise re-read against main on 2026-11-19.
**Idea:** IDEA-006
**Wave:** 82
**Created wave:** 82
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/decisions/adr/0029-difficulty-by-strategy-ladder.md, tests/test_solver*.py, tests/property/*, tests/test_check_ref_resolution.py
**UI surface:** —
**Review score:** 9.5 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-19T19:53Z
**Closed:** 2026-11-19T20:35Z
**Actual:** 2c — ratio 2/1 = 2.0
**Merge commit:** f6af67a622a4a00f9122ff88057f4804816daed3
**Blocked by:** —

## Why this card exists

ADR-0029/R4 (mandatory) has two halves: the overlap masks behind the `simple_overlap` rung are computed **relative to the line's already-known cells** (the leftmost and rightmost placements consistent with them, intersected), and they are re-derived natively inside `solver/` without importing `clues.py`. Its `check:` is `test_every_import_in_the_package_points_inward` (tests/test_cli.py), which covers only the import half. Re-read 2026-11-19: the ref is unchanged. A dead-ref sweep cannot catch this, because the ref is alive; it just cannot fail when the rule is broken.

## What to implement

1. Find whether a test already pins the first half (masks relative to known cells). If one exists, add it to R4's `check:` ref; if not, write the narrowest one, preferably by extending an existing solver test, against an independent oracle (the project's brute-force or line-enumeration helpers), never by re-deriving with the function under test.
2. Keep the import-graph test on the ref for the second half.

## Acceptance criteria

* **AC-1**: R4's `check:` names a test that reds when the masks are computed ignoring the known cells (control: plant the from-scratch overlap, it reds), and still names the import-graph test.
* **AC-2**: tests/test_check_ref_resolution.py stays green; any frozen class it holds is re-derived, not pasted.
* **AC-3**: net test count at most +1; report it.

## Guardrails

* **G-1**: no solver behaviour change; if the control finds the rule actually broken in code, stop and report: that is a correctness finding, not this card's fix.
* **G-2**: the brute-force oracle never imports `nonogram.solver` (CLAUDE.md).

## Worktree notes

**Finding: half (a) was already pinned; no test written.** Two existing tests in
`tests/test_solver_witnesses_and_rungs.py` check the overlap rule against an
independent placement enumeration (`_feasible_placements`, which never calls the
solver): `test_overlap_deduction_matches_the_textbook_rule` and
`test_the_overlap_greedy_finds_the_true_extreme_start_of_every_run`. Both
confirmed as `def` lines by an `ast` walk over tests/ (one each), not by text search.

**Controls** (each on a scratch `git archive` copy under /private/tmp/claude-501/,
never in the worktree; `nonogram.__file__` confirmed to resolve to the copy):
* Plant A, `overlap_extremes` ignores the known cells: 4 red in the overlap
  selection -- the textbook-rule test (its known-filled case), the
  true-extreme-start test, and two cases of
  `test_overlap_deduction_reports_an_impossible_line`.
* Plant B, `overlap_deduction` reads the extremes of a blank line and ORs the
  known cells back in: 3 red -- the textbook-rule test and the two
  impossible-line cases. `test_overlap_deduction_never_claims_more_than_every_placement_agrees_on`
  stays green, as it must: a from-scratch overlap is sound, only weaker, so a
  soundness test cannot pin (a).
* Plant C, `propagate_overlap`'s two call sites pass blank knowledge (known cells
  ORed back): 6 red across the rung-level tests, including
  `test_a_line_solvable_set_tags_every_cell_without_probe_contradiction` and
  `test_every_corpus_puzzle_that_never_left_overlap_scores_the_same_point`.
  Not put on the ref: these red for downstream reasons, not on the rule itself.
* Unplanted base: same overlap selection 11 passed. G-1: the rule is not broken
  in production code; no solver change.

**Ref change.** ADR-0029/R4's `check:` now names the two tests above plus
`test_every_import_in_the_package_points_inward` (kept for the native-derivation
half), quoted as a multi-name ref. No yaml mirrors R4's ref: requirements.yml
has no R4 entry, and trace.yml mentions R4 only in prose.

**Frozen counts moved** (tests/test_check_ref_resolution.py, base 26 passed in
the worktree, 2 red after the ref edit, re-derived, then green): `CENSUS`
596 -> 598 and `DEFINED` 471 -> 473, OUT 0 / IN 2 each. Diffed as sets via the
module's own `_declared_refs` / `_verdicts` with the edit reverted and then
reapplied. The base fingerprints matched the stored baselines, and base plus the
two names predicted the new fingerprints exactly. Neither name was declared
under meta/architecture/ at the base (`git grep -w` at HEAD).

**Gate** (`-o addopts= -rfs`): tests/test_solver*.py, tests/property/test_solver*.py,
tests/property/test_solve_strategies.py, tests/test_strategies.py,
tests/test_difficulty*.py, tests/test_check_ref_resolution.py, tests/test_cli.py,
tests/test_kanban_review_record.py, and the ADR/registry readers
tests/test_approval_guess_gate.py, tests/test_grid_bound_agreement.py,
tests/test_nfr001_generation_time.py, tests/test_book_page_packing_doc.py,
tests/test_impact_set.py: **708 passed, 1 xfailed, 0 skipped, 0 failed**.

**Net test count: 0** (`--collect-only -q -o addopts=` over tests/: 10704 base,
10704 branch).

**Fix round 1 (review cycle 1, F-1..F-3).** The round-0 finding above was
only partly right: the existing tests pinned (a) at the extremes level and on
one hand-picked mask case only. A mask plant that ignored just the known-empty
cells stayed green on every test the ref named.
* F-1: `test_overlap_deduction_never_claims_more_than_every_placement_agrees_on`
  now also asserts `(filled, empty)` EQUALS the masks built from the
  enumeration's per-run start range (min/max start over every feasible
  placement), never from solver code; docstring updated. No new test.
  Plants on a scratch `git archive` copy (overlap selection, `-o addopts=`):
  unplanted 11 passed; A (extremes ignore known) 5 failed; B (deduction from
  blank extremes) 4 failed; C1 (feasibility kept, masks blank) 2 failed; C2
  (masks from known-empty only) 2 failed; C3 (masks from known-filled only)
  1 failed. That test reds under all five, each time on its new exactness
  assertion ("not the overlap relative to the known cells"). Under C3 it is the
  only test that reds.
* R4's `check:` now names four: that test, the textbook-rule test, the
  extreme-start test, and `test_every_import_in_the_package_points_inward`.
* F-2: the ADR ref comment and the CENSUS comment now say which plants each
  test reds under, instead of "each reds".
* Frozen counts: `CENSUS` 596 -> 599 and `DEFINED` 471 -> 474 against the base
  (598 -> 599 and 473 -> 474 against round 0). OUT is 0 each. IN is the three
  overlap test names against the base; against round 0 it is only the
  never-claims-more test.
  Derived as sets with the module's own `_declared_refs` / `_verdicts`, the ADR
  swapped to its base and round-0 versions. Those fingerprints reproduced the
  stored baselines. The new name has one `ast`-found def and was undeclared
  under meta/architecture/ at the base.
* F-3: `test_the_two_directions_of_disagreement_are_exactly_the_measured_ones`
  warns "the 'honest-dead' class lost 12 member(s)" in the worktree with the
  card's three changed files set back to the base commit's contents. It still
  warns with the synced review YAML (meta/review/, cycle 1) moved aside. So it
  predates this branch and is not caused by the review YAML. Fresh-repo archive
  copies fail this test outright, base and branch alike, so they could not
  serve as the comparison. Not fixed here.
* Gate (`-o addopts= -rfs`: tests/test_solver*.py, tests/property/test_solver*.py,
  tests/property/test_solve_strategies.py, tests/test_check_ref_resolution.py,
  tests/test_cli.py): 266 passed, 0 skipped, 0 failed. Net test count 0
  (10704 collected).

[Review 1/3] Score: 8.5, one gating finding, not certified. F-1 the re-pointed ref did not hold R4's half (a) at the deduction level: a plant building the masks from known-filled cells only (ignoring known-empty) left every test on the ref green, and three other from-scratch plants were caught by one hand-picked case; F-2 two comments claimed "each reds under a from-scratch plant"; F-3 (info) a pre-existing "honest-dead lost 12" warning. Fixed in `43f867f9`: `test_overlap_deduction_never_claims_more_than_every_placement_agrees_on` now also asserts the masks equal those built from the independent enumeration's start range, and reds under all five plants; it joins R4's ref; CENSUS/DEFINED re-derived to 599/474. F-3 measured pre-existing on the base, not this branch.

[Review 2/3] Score: 9.5, nothing gating, certified. F-1 closed: the extended test reds on its exactness assertion under all five plants; its expected masks come only from `_feasible_placements`; the corpus has 222 feasible lines, 30 carrying both kinds of known cell, and dropping either known mask changes the masks on 21-24 of them; R4's ref names it; CENSUS 599 / DEFINED 474 re-derived independently. F-2 closed. F-3 confirmed pre-existing on main. F-4 (low) fixed inline by the orchestrator: the test now asserts at least 25 feasible lines carry both known kinds (measured 30; a bound of 31 reds it). 261 passed, 0 skipped; net test count 0.

**Merge gate (orchestrator).** `make test-gate BASE=main` (a selection): 4319 passed / 15 skipped / 1 xfailed / 0 failed, plus 4 passed marked. The 15 skips are the selection's 14 `db_required` tests (DATABASE_URL unset; counted by collecting the same files with `-m db_required`) plus the setrlimit platform skip.
