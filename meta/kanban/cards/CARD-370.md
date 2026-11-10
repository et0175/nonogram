# CARD-370: The full-suite lock is mandatory on refusal and purely advisory on acquisition — nothing writes it, so two full suites ran in parallel and one lost 37 tests

**Status:** done
**Priority:** P1
**Category:** enabler
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** Wave 76, 2026-11-04. Both reviewers reported half of it and neither reported the mechanism; the orchestrator's first reading ("neither agent at fault") was an inference and is retracted below. Mechanism measured in `tests/full_suite_lock.py` directly.
**Idea:** —
**Wave:** —
**Created wave:** 76
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/full_suite_lock.py, meta/kanban/config.yml
**Review score:** n/a — closed on the owner's 2026-11-10 enabler triage; no review of its own.
**Started:** 2026-11-10
**Closed:** 2026-11-10
**Actual:** about two hours, with CARD-377
**Merge commit:** —
**Blocked by:** —

## The asymmetry, measured in the module

`tests/full_suite_lock.py` enforces the lock in exactly one direction:

- **Refusal is mandatory and total.** `pytest_configure` runs first in `conftest.py`, before the
  database guard and before any fixture exists, and `raise`s `pytest.UsageError` when a *foreign*
  worktree holds the lock. This refuses **every** pytest from that worktree, not just full suites.
- **Acquisition is not enforced at all.** `verdict()` returns `(True, None)` the moment
  `lock_text is None` — no lock, run freely, say nothing. And **no function in the module writes
  the lock.** Acquisition is entirely by convention: an agent writes the file by hand, or doesn't.

So a run that never acquires is indistinguishable from a run that has no need to, and the mutual
exclusion the lock exists to provide **simply never engages**.

## What it cost, wave 76

Two reviews reached their full suites at roughly the same time.

1. CARD-363's reviewer checked for the lock, found it absent, and **ran a full suite without
   writing one** — visible in its own shell history, and consistent with the module: nothing asked
   it to.
2. CARD-348's reviewer then saw no lock, **correctly acquired it** (`at: 2026-11-04T15:21:24Z`), and
   ran.
3. Every child pytest CARD-363's run spawned after that instant was refused. Its result:
   **10292 passed, 37 failed, 27 skipped** — the refusal text appearing **71** times, all 37
   failures in the four subprocess-spawning modules (30 kill-matrix, 3 database-guard, 3 browser
   pass-alone, 1 suite-profile collect-only). The module under review contributed none.
4. CARD-348's own suite stayed green — **10280 passed / 0 failed / 27 skipped** — so nothing needed
   re-attributing. That is luck, not design.

**Had step 1 acquired the lock, step 2 would have been refused up front and waited.** The collision
is therefore attributable, and the structural point is that **nothing in the tree could have
prevented it** — which is why this is P1 and not a note.

> **Retracted (ADR-0039/R4).** The orchestrator first wrote this card as "two reviews share one
> lock, neither agent at fault". That was an inference from CARD-363's reviewer saying only that the
> lock *"was absent immediately before I started"* — a true statement that does not claim
> acquisition. CARD-348's reviewer measured the other half. Neither report was wrong; the roll-up
> was. Logged because it is the same subclass as the premise failures this board keeps finding:
> a conclusion assembled from two correct partial accounts.

## Why no re-run was needed, and why that is not reassurance

CARD-363's reviewer did not re-run, correctly: the lock was still held, and it neither set
`NONOGRAM_IGNORE_FULL_SUITE_LOCK` nor redirected `NONOGRAM_FULL_SUITE_LOCK`. Both remain forbidden
and no fix here may involve either.

The dangerous property is that **the failure is silent in the direction that matters.** A run that
holds no lock reports nothing — `verdict()` returns `said = None`, and `pytest_terminal_summary`
prints only when there is an announcement. The *refused* side is loud; the *un-acquired* side is
invisible. `tests/full_suite_lock.py`'s own docstring was written for the two-suites-in-parallel
attribution hazard (CARD-225's build gate 2), and that is exactly what happened.

## Acceptance criteria

- **AC-1** — A full suite that holds no lock is **detected**, and the detection is derived, not a
  list of gate names (ADR-0039/R2, defaulting to deny). State how "this run is a full suite" is
  decided and why that decision cannot be evaded by the shape of an invocation.
- **AC-2** — The un-acquired case **announces itself** through the same path the refusal and the
  stale-lock walk-past already use, so it survives `addopts = "-q"` — `pytest_terminal_summary`
  exists precisely because `-q` prints no header.
- **AC-3** — A subprocess refused for lock contention is distinguishable from a genuine failure
  **at the point of failure**, not by grepping 71 occurrences out of a 23-minute run's output. A
  refused child must never pass vacuously; the suite-profile module's own vacuity guard firing
  rather than passing is the model, and is why the 37 were visible at all.
- **AC-4** — A plant proves each new arm can fail: run a full suite without acquiring and assert the
  announcement; hold the lock from a second worktree mid-run and assert the distinct outcome. Plant
  by text with the occurrence count asserted `== 1`, SHA-256 both ends, restore from captured
  content, and keep a matched control green in the same run.
- **AC-5** — Say whether the right answer is instead **"reviews serialise within a wave"** as a
  scheduling rule in `config.yml`, with the measured cost of each option. Do not assume the
  technical fix wins — the owner's standing concurrency cap is 2, and this is the first measured
  cost of that cap. **This is the orchestrator's call to make with the owner, not the round's.**
- **AC-6** — No change to `src/`. Run with `-rEfs`; state the skip count **as a function of whether
  `DATABASE_URL` is armed**, never as a bare number.

## Guardrails

- **G-1** — `NONOGRAM_IGNORE_FULL_SUITE_LOCK` must never be set and `NONOGRAM_FULL_SUITE_LOCK` must
  never be redirected, by this card's implementation or its tests.
- **G-2** — The refusal path is load-bearing and correct. Do not weaken it to make acquisition
  symmetric; add the missing half.
- **G-3** — A holder that dies must still leave a walk-past-able stale lock. The module's docstring
  says a board that cannot run tests is worse than one that mis-attributes; preserve that.

## Worktree notes

(none yet)

## Closed 2026-11-10 — owner's enabler triage, done together with CARD-377

- **AC-1.** A run is a full suite when every test module on disk under `tests/` produced a collection report, nothing was deselected, and no argument named a single node (`is_full_suite`). It is read from the collection, so `pytest`, `pytest tests`, `pytest .` and a list of every file are the same full suite, and `-k`, `-m`, `--deselect`, `--ignore` or one missing file are not. A tree the rule cannot see answers *full*. Such a run takes the lock itself before the first test (`O_EXCL`), writes `pid`, `host`, `token` and a heartbeat, hands the token to its child pytests, and removes the lock when it ends.
- **AC-2.** Taking the lock, or failing to, is announced in the terminal summary, which survives `-q`.
- **AC-3.** A test that fails while another worktree holds the lock gets a `full-suite lock` section in its own failure report, and the summary counts them.
- **AC-4.** Held by a throwaway tree in `tests/test_full_suite_lock.py` (the module copied beside a two-file suite, so its real lock path is used without OVERRIDE or LOCK_PATH_VAR). Five mutants were each killed by one of the new tests: deselection ignored, the same-worktree token check removed, a dead pid ignored, release skipped, the failure section skipped.
- **AC-5.** Not built: with the suite taking the lock itself, serialising reviews by a `config.yml` rule is not needed for correctness. It stays the owner's call if the wait between two reviews proves too costly.
- **AC-6.** No change to `src/`.
- Since the board's full suites are now held automatically, a hand-written lock is no longer needed before a full run.
