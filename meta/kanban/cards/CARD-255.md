# CARD-255: A pytest run refuses to start while another worktree holds the full-suite lock

**Status:** ready
**Priority:** P1
**Category:** ops
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** wave 48 retrospective, owner decision 2026-10-20 — "the full-suite lock gets enforced in conftest.py", after CARD-225's build gate 2 shared its window with a browser suite and reported two failures that were not the tree.
**Idea:** —
**Wave:** 49 (queued)
**Depends on:** —
**Touches:** tests/conftest.py, meta/kanban/.full-suite.lock (format only), tests/test_full_suite_lock.py (new)
**Review score:** —
**Started:** — · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why

The gate script writes `meta/kanban/.full-suite.lock` naming its holder, commit and reason — and
**nobody reads it**. Its own guard refuses to *start* beside another pytest, which is a check at the
door that cannot stop someone entering afterwards. Measured cost this wave: CARD-225's build gate 2
ran 15:19 while a 288-test Chromium suite ran in another worktree, and came back 2-failed on tests
unrelated to the card (a UUID sentinel handed a float, a loopback server nothing answered on). Both
are in build gate 3's green count. One gate re-run, one attribution written down and then withdrawn.

A control that only the controlled party consults is this board's own claim-family shape
(ADR-0039/R1) living in the procedure instead of the code.

## What to implement

In `tests/conftest.py`, at session start: if `meta/kanban/.full-suite.lock` exists **and was not
written by this process**, abort the run with a message naming the holder, its commit and the age of
the lock. Requirements that make it a control rather than an irritation:

- **It must name the holder.** "Another run is in progress" sends someone hunting; the lock file
  already carries `holder`, `at`, `worktree`, `commit`, `why` — print them.
- **A stale lock must not wedge the board.** A holder process that died leaves the file behind.
  Decide and state the rule: either the lock carries the holder's pid and a dead pid is ignored with
  a warning, or an age threshold applies. Whichever is chosen, **its control is a test**, not a
  comment.
- **The gate itself must not be blocked by its own lock**, and a targeted selection by an agent
  while a gate runs is exactly what must be refused.
- **An override must exist and must be loud** (an env var the gate scripts do not set), because the
  one thing worse than a contended gate is a board that cannot run tests at all.

## Acceptance criteria

- **AC-1** *Given* a lock file written by another worktree, *when* pytest starts, *then* it exits
  non-zero before collecting, printing the holder, commit and lock age.
- **AC-2** (the control) *Given* the abort removed, *then* AC-1's test fails. A guard whose removal
  fails nothing is this board's recurring defect, not a guard.
- **AC-3** *Given* a stale lock under the chosen rule (dead pid, or past the age threshold), *then*
  the run proceeds and says why it ignored the lock.
- **AC-4** *Given* the override set, *then* the run proceeds and says so on stdout; *given* it unset,
  *then* it does not.
- **AC-5** (guard) *Given* this change, *then* the suite's skip profile is unchanged and no test
  that passed before now skips — the abort must not become a silent skip.

## Guardrails

- G-1: The abort fires **before** any fixture touches a database.
- G-2: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-3: No new runtime dependency (ADR-0006/R1); `os`/`pathlib`/`time` only.
- G-4: The lock's **format** may be extended (a pid line) but every field the gate scripts already
  write must keep its meaning — the scripts are not in this card's Touches and must keep working
  unchanged.
- G-5: No test retired without a named survivor.

## Worktree notes

- **[Do not take timing measurements]** other cards share this machine.
- **[The trap, and it is this card's whole subject]** The obvious test asserts "the lock file causes
  an abort" by creating a lock and catching `SystemExit` **in the same process that wrote it**. That
  test passes with a guard that only ever refuses *itself*, which is the opposite of what is wanted.
  The guard must refuse a lock written by **another** holder and ignore its own — so the test needs
  two distinct holder identities, and the mutant that proves it is "treat every lock as foreign"
  (which must red the gate's own self-run case).
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`.
