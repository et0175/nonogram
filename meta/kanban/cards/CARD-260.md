# CARD-260: Commit the per-assertion kill instrument once, with all six of its known traps as controls

**Status:** in_progress
**Priority:** P1
**Category:** enabler
**Complexity:** standard
**Estimate:** 0.75d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/260-commit-the-kill-instrument
**Worktree:** ../PythonProject4-card-260
**Source:** Wave 50 retrospective, owner decision — five agents built this instrument from scratch in one wave and each hit a different trap first
**Idea:** —
**Wave:** 51
**Depends on:** —
**Touches:** tests/kill_matrix.py, tests/test_kill_matrix.py, tests/README.md
**Review score:** —
**Started:** 2026-10-20T16:52:59Z · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why — the traps are known, and nothing in the tree remembers them

Wave 49 promoted *per-assertion measurement with a line-count-preserving instrument*, because a test
short-circuits at its first failing assert, so one `FAILED` line says nothing about the arms that never
ran — **a surviving mutant and a never-reached assert look identical**.

Wave 50 then found **five more ways the instrument itself lies**, each discovered by a different agent,
none of them by reading another's code:

| # | the lie | cost when it bit |
|---|---|---|
| 1 | a **test count** reported as an assertion count | a *killed* mutant recorded as a **survivor**; the matrix measured over an undeclared subset |
| 2 | **last-write-wins** aggregation loses a RED from an assert inside a `for` loop | would have lost **3 of 6** kills |
| 3 | **suppressed propagation** — the recording wrapper swallows `AssertionError`, so a child pytest reports `1 passed` with rc 0 | four real kills recorded as **PASS**, inflating "unkilled" 80 → 84 |
| 4 | a **leaked patch** — two of three mutated attributes restored | a leaked patch and a real kill look identical |
| 5 | a **no-op mutant** — deleting a literal the text does not contain (it writes a placeholder the arm substitutes first) | returned 2 of 4 cells; a no-op mutant and a surviving mutant look identical |
| 6 | **line-count-shifting** deletion mutants (wave 49's original) | the numbering shifts and **every** assert reports NOT-REACHED |

Six traps, three independent instruments on CARD-257 alone, and **each found a defect the others' shape
would have hidden**. That is the argument for committing one: not that writing it is expensive, but that
the knowledge evaporates with the scratchpad every time.

## What to implement

1. **One instrument at `tests/kill_matrix.py`**, importable by a test or runnable as a script, that
   rewrites **every** `ast.Assert` at any depth into a recording `try/except AssertionError`/`else` keyed
   on the node's **own** `lineno`, and reports each assertion as `PASS` / `FAIL` / **`NOT-REACHED`**.
2. **Two passes, because they do not see the same things.** A **recording** pass (records and continues:
   per-arm attribution, suppressed propagation) and a **re-raising** pass (records and re-raises: true
   propagation and true cross-process semantics). The API must make the caller name which pass a figure
   came from — **a figure that does not carry its domain is the defect this card exists to prevent.**
3. **Each trap is a control that can fail**, not a comment. See the ACs.
4. **Safety discipline, inherited from the wave's own probes and not negotiable:** refuse to start if
   the board's real lock exists; `cp -p` backups with all later content read from the backups; assert each
   substitution occurs **exactly once** with equal newline counts and equal `splitlines()` length;
   restore in a `finally` verified with `diff -q` **and** `shasum -a 256`; **no git command anywhere**.

## Acceptance criteria

- **AC-1** (trap 6) *Given* a deletion mutant that removes a line, *then* the instrument **refuses** it,
  naming the line-count change. (test: a shifting mutant is rejected, not silently measured)
- **AC-2** (trap 2) *Given* an assertion inside a `for` loop that reds on one iteration and passes on
  another, *then* the aggregate is **RED**. (test: a two-iteration arm, and its control is the same arm
  under last-write-wins, which must disagree)
- **AC-3** (trap 3) *Given* an assertion whose truth depends on a child process's outcome, *then* the
  **recording** pass reports it as a declared **blind spot** rather than PASS, and the **re-raising**
  pass reports the kill. (test: both passes over one child-spawning arm; the two must differ, and the
  difference must be what the instrument reports)
- **AC-4** (trap 4) *Given* two mutants applied in sequence, *then* SHIPPED is re-run and asserted
  all-PASS **between** them, and a deliberately leaked patch **fails** that check. (test: the leak is
  planted and caught)
- **AC-5** (trap 5) *Given* a mutant whose `old` string is absent from the target, *then* it is
  **refused**; *given* one present but not the occurrence intended, *then* the caller must target it
  explicitly. (test: a no-op mutant is rejected, and the five-occurrence case from
  `test_db_engine_lifecycle.py` is the fixture)
- **AC-6** (trap 1) *Given* any reported figure, *then* it carries its **domain and its denominator** —
  assertion node count, never a collected test count. (test: the reported denominator equals an
  independent `ast.walk` count, and a mutant that substitutes the collected test count reds)
- **AC-7** (guard) *Given* this instrument, *then* running it over `tests/test_full_suite_lock.py` at
  `ddb1731b` reproduces **130 of 130 PASS and reached**, and over `tests/test_db_engine_lifecycle.py` at
  `b441ba00` reproduces the four-arm AC-2 grid of CARD-257 — the two matrices the board already measured
  three independent ways.

## Guardrails

- G-1: The instrument never runs the full suite. It takes a targeted selection and refuses an empty one.
- G-2: It never writes a lock, and refuses to start if `meta/kanban/.full-suite.lock` exists.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-4: No new runtime dependency (ADR-0006/R1) — `ast`, `pathlib`, `subprocess`, `hashlib` are stdlib.
- G-5: It never restores a file with git. `cp -p` backups only, verified two ways.
- G-6: It takes **no timing measurements** and reports none.

## Worktree notes

- **[Do not take timing measurements]** other cards may share this machine.
- **[The trap of this card is the obvious one]** an instrument that certifies itself is exactly the defect
  CARD-256 gated on three times. **Every AC above must be certified against a planted failure**, not
  against the instrument's own report of success. AC-7's two reproductions are the independent anchors:
  both matrices were measured three separate ways in wave 50 and the figures are in the cards.
- **[The claim rule applies to this card hardest of all]** it is an instrument for measuring claims. Any
  sentence it prints is a claim, and `--help` text is not exempt.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR files
  **case-insensitively** for the reach-limit idiom. This card is about ADR-0039/R1.

## System contract

Curated to **5 of 10** in-scope rules under `meta/kanban/curation.md`: every rule whose
enforcement does not reach this card's new code is kept; the rest are dropped because the suite runs them
on every gate. **5 dropped.** ADR-0039 present, as the sanity check requires for a card
touching `tests/**`.

- **ADR-0038/R7** — _review-lens — nothing executes it_
  Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in
  pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — _review-lens — nothing executes it_
  Browser tests run locally, against Chromium installed by `playwright install chromium`. When
  Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible
  in the run summary. They never pass silently.
- **ADR-0039/R1** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  A set a guard consults needs a completeness test written before the set, and any claim the guard
  makes about what it catches needs a control that can fail: caught WITH the set member present,
  missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and must be
  narrowed to what is measured or deleted.
- **ADR-0039/R2** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no
  such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE, never
  a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3.
- **ADR-0039/R3** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT
  absorb — caught with the exemption removed, missed with it in place — is held to an equality
  against the sites that exist today, and records whatever it still cannot see as a measured bound
  with its own failing control.
