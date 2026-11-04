# CARD-362: Retire the 396 tracked review YAMLs — the owner action CARD-335 bounded but could not take

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** The residual CARD-335 measured, bounded and explicitly could not repair from a card branch. Its review cycle 1 priced the consequence exactly and confirmed all three blocking reasons, reproducing two of them independently. This card exists because the work is an owner action on `main`, not because CARD-335 fell short.
**Idea:** —
**Wave:** —
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** CARD-335
**Touches:** meta/review/, .gitignore
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What is left, and it is priced

**9 of the 10 actively-revived refs are kept alive solely by `meta/review/*.yml`** — five files
(`…CARD-139-cycle1` revives 6, `…CARD-134-cycle3` 2, `…CARD-117-cycle1` 1, `…CARD-305-cycle1/2`
2). CARD-335 shut the **cause-side** door (those paths are now gitignored, so a new one needs
`git add -f` and reds a census cell) and bounded the population by count, digest and members in
the pre-existing bookkeeping-only gate. **It did not un-revive the nine.**

**The consequence is measured, which is what makes this a priced card rather than an open
question.** CARD-335's reviewer patched `CodeSearch.exists` to report the 10 dead and ran the
validator:

> **0 errors / 89 warnings → 0 errors / 94 warnings.** The +5 are 3 `DEAD check ref` **WARNs**
> (`requirements.yml` FR-040/AC-252, FR-042/AC-291, FR-042/AC-292) and 2 partly-checked WARNs
> (`domain/aggregates.yml` INV-011, INV-013). **Zero ERRORs appear**, because 8 of the 10 are
> declared on a `status: partial` trace entry and `trace.py` never asks the resolver about those
> — see **CARD-361**, which owns that blind spot.

**So expect 89 → 94 and 0 errors. Re-derive it; a different number is the finding.**

## The three reasons a card branch cannot do this, all reproduced

1. **INV-023.** `cmd-done` step 2d diffs `<merge-into>...HEAD -- meta/kanban meta/review` and
   **refuses** on any path. A card branch cannot commit under `meta/review/` at all.
2. **Untracking is DELETION for everyone but the branch.** Reproduced twice in a throwaway repo
   (by the round and independently by its reviewer): branch does `git rm -r --cached meta/review`
   plus a gitignore, merge into main, and **the files are gone from main's working tree**. This
   is the mechanism by which "gitignoring is fine, emptying is not" could be violated without
   anyone writing an `rm`.
3. **The suite reads these directories off disk.** `test_suite_profile.py` asserts the
   `suite-durations-*.txt` glob is non-empty; two more modules read `meta/profiling/` by name.
   That is the sibling population, but it is the same hazard class and the same lesson.

## What to implement — and the first step is not a git command

1. **COPY `meta/review/` OUT OF THE REPOSITORY FIRST**, to a location nothing in this repo can
   reach, and **verify the copy is readable** before touching the index. These are the only
   record of the review cycles this board's retrospective reads — wave 74 had to reconstruct
   **four** of them from reviewers' reports because none had been written, and wave 75 a fifth.
   **State where the copy is and how you verified it.**
2. **Then untrack the 396** with `git rm -r --cached meta/review` on `main` — not on a branch,
   for reason 2 above. The directory is already gitignored by CARD-335, so nothing re-adds them.
3. **Measure the validator before and after**, comparing WARN **sets** with both sides asserted
   non-empty. Expect 89 → 94, 0 errors, and **every one of the +5 accounted for by name**. A
   drop instead of a rise means something else moved and is a finding.
4. **Verify the files are still on disk and readable afterwards.** 413 `.yml` were present when
   CARD-335 measured (396 tracked + 17 untracked); the count after must be the same, with zero
   read failures.

## Acceptance criteria

- **AC-1** *Given* the untracking, *then* every `meta/review/*.yml` is **still present on disk
  and readable**, the count is stated before and after and is unchanged, and an out-of-repo copy
  exists and was verified **before** the index was touched.
  (test: named by the implementation; state it)
- **AC-2** *Given* the validator, *then* the warning count **rises** to the measured figure with
  0 errors, the WARN sets are compared with both sides asserted non-empty, and **every appearing
  warning is named**. A fall is a finding.
  (test: named by the implementation; state it)
- **AC-3** *Given* the nine refs, *then* each now resolves **loose-dead as well as strict-dead**
  — the revival is gone, not merely the file untracked — derived with the resolver's own
  instrument.
  (test: `tests/test_check_ref_resolution.py`)
- **AC-4** *Given* CARD-335's guards, *then* the census cell and the bookkeeping-only gate are
  both still green and both still **able to fail** — demonstrated, not read.
  (test: `tests/test_check_ref_resolution.py`)
- **AC-5** *Given* the suite, *then* nothing that reads these directories off disk breaks:
  `test_suite_profile.py`'s glob is still non-empty and the by-name readers still resolve.
  (gate: the full suite)

## Guardrails

- **G-1** — **Do not delete, move or empty `meta/review/`.** Untracking only. The out-of-repo
  copy exists so that a mistake is recoverable, not so the originals become expendable.
- **G-2** — **Do this on `main`, not on a card branch.** Reason 2 above; a branch's untracking
  becomes main's deletion at merge.
- **G-3** — Do not widen `.gitignore` beyond what CARD-335 landed. Its scoping was deliberate:
  `meta/review/*.yml` and not `meta/review/**`, so the `.md` records a live test reads stay
  tracked.
- **G-4** — Do not raise a severity or suppress a warning to make the after-count tidy. The
  point of this card is that the number **goes up** and that this is correct.
- **G-5** — Take no timing measurements and report no durations.
- **G-6** — A full suite needs the board's lock (structured, worktree identity, no pid). Never
  set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, never redirect `NONOGRAM_FULL_SUITE_LOCK`.
- **G-7** — When comparing WARN sets, match `^[[:space:]]*\[WARN` and assert both sides
  non-empty before comparing.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: `tests/test_check_ref_resolution.py`)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written
  (check: review-lens)
- ADR-0038/R8 — findings are reported loudly (check: review-lens)
