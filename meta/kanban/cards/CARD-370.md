# CARD-370: Two concurrent reviews share one full-suite lock, and the second one silently reds the first — 37 failures, neither agent at fault

**Status:** ready
**Priority:** P2
**Category:** ops
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** Measured during CARD-363's cycle-1 review, 2026-11-04 — item 4 of its new-work list. The cost was paid in that cycle: a 23-minute full suite whose 37 failures were all lock contention.
**Idea:** —
**Wave:** —
**Created wave:** 76
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/kanban/config.yml, tests/conftest.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What happened, measured

Wave 76 ran two cards concurrently, which is the owner's standing cap. Both reached review at
roughly the same time. CARD-363's reviewer started a full suite with the lock **free**; CARD-348's
reviewer then **took the lock mid-run**:

```
holder: CARD-348 review cycle 1
worktree: /Users/omelnikova/PycharmProjects/PythonProject4-card-348
at: 2026-11-04T15:21:24Z
```

Every child pytest CARD-363's run spawned after that moment was refused — the refusal text appears
**71 times** — and the run reported **10292 passed, 37 failed, 27 skipped**. All **37** failures sit
in the four subprocess-spawning modules (30 kill-matrix, 3 database-guard, 3 browser pass-alone,
1 suite-profile collect-only). **The module under review contributed no failure.**

## Why it is worth a card rather than a convention note

Three properties make this expensive:

1. **It is invisible at the point of failure.** The 37 reds name the tests, not the lock. A reviewer
   without the presence of mind to grep for the refusal text diagnoses 37 unrelated failures.
2. **It strikes mid-run**, so a pre-run lock check — which both reviewers did correctly — cannot
   prevent it.
3. **It wastes the most expensive thing in the pipeline**, a full suite, and it does so at exactly
   the moment two cards are closest to landing.

One mitigation is *not* available and should be ruled out explicitly: the lock must not be
overridden or redirected. `NONOGRAM_IGNORE_FULL_SUITE_LOCK` and redirecting
`NONOGRAM_FULL_SUITE_LOCK` are both forbidden, and CARD-363's reviewer correctly did neither.

## Acceptance criteria

- **AC-1** — A subprocess refused for lock contention is distinguishable from a genuine failure
  **at the point of failure**, without grepping the whole run's output.
- **AC-2** — The mechanism that makes a mid-run acquisition safe is named and justified: either the
  suite declares its intent up front so a rival blocks instead of interleaving, or a refused child
  is reported as a distinct outcome that cannot be read as a pass **or** as an ordinary red.
  **A refused child must never pass vacuously** — the suite-profile module's own vacuity guard
  firing is why the 37 were visible at all, and that behaviour is the model.
- **AC-3** — A plant proves it: hold the lock from a second worktree mid-run and assert the named
  distinct outcome, not a bare red. Restore from captured content.
- **AC-4** — State whether the convention should instead be "reviews serialise within a wave", with
  the measured cost of each option. Do not assume the technical fix is the right one — the cheap
  answer may be a scheduling rule in `config.yml`, and that is the orchestrator's call to make with
  the owner.
- **AC-5** — Run with `-rEfs`; state the skip count **as a function of whether `DATABASE_URL` is
  armed**, never as a bare number.

## Worktree notes

(none yet)
