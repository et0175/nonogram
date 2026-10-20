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

## Implementation record — `f9718739`

Commit `f9718739` on `card/260-commit-the-kill-instrument`, pathspecs `tests/kill_matrix.py` (new, 944
lines) `tests/test_kill_matrix.py` (new, 1216 lines) `tests/README.md` (+113) — the card's `Touches`,
exactly, no fourth path. Nothing under `meta/` in it. **42 tests, all passing.**

### TDD done the hard way, and the right way

Rather than redding on `ImportError`, the agent built the core and then **staged a naive baseline with all
six trap mechanisms removed**, re-adding them one at a time — so **every red is the trap biting**, not a
missing import. Naive baseline: **12 failed, 23 passed**. Each AC's red is recorded verbatim on the card's
worktree notes; the two worth quoting:

- **trap 2** red carries its own attribution: the assertion *above* the failing one —
  `matrix.records[loop_arm] == (False, True)` — **passed**, so the records were right and only the
  aggregation was wrong. A red that tells you which layer failed.
- **trap 1** red is `assert 2 == 5`, where 2 came from parsing `of 2 assertion nodes` back out of the
  figure and 5 from an independent `ast.walk`. The fixture has **5 assertion nodes and 2 collected tests
  on purpose** — on a file where the two agreed, the check could not fail.

### Both AC-7 anchors reproduced — cell for cell, including the pre-aggregation lists

**Anchor 1**, `tests/test_full_suite_lock.py` at `ddb1731b`: node count **130**, re-derived by independent
`ast.walk`; recording pass SHIPPED **130 of 130 PASS and reached, zero NOT-REACHED, zero FAIL**;
`collected_tests == 41` asserted **as the collected count and never as the denominator.**

**Anchor 2**, `tests/test_db_engine_lifecycle.py` at `b441ba00`: 14 mutants, all derived from `session.py`'s
own AST, every edit occurrence-scoped to a docstring span. Six `DOC-NAME-DEL` FAIL at `:878`, four
`DOC-HEAD-DEL` FAIL at `:889`, `NAMES-BLIND` FAIL at `:859` **with the three arms below it NOT-REACHED**,
`POINTER-ROT` and `POINTER-DEL-WORD` FAIL at `:897`, **`CONTROLS-RENAME-ONLY` PASS**, SHIPPED all-PASS.

And the part that settles it: **CARD-257's pre-aggregation lists came back too** —
`DOC-NAME-DEL[SessionLocal@prod] :878 (False, True)` and `[…@guard] :878 (True, False)`, exactly its
`['RED','PASS']` / `['PASS','RED']`. **ANY-RED is doing real work on a real anchor, not only in a fixture.**

Occurrence-scoping was load-bearing here — trap 5 in the wild a second time: `setattr(` occurs **6** times
in the prod docstring and **32** in the file around it, and `global engine, SessionLocal, _engine_url`
occurs **twice** in `session.py`. Every edit names its 1-based occurrence, emitted in **descending** order
so an earlier replacement cannot renumber a later one.

### One transformer, and its failing state is on disk

`_Recorder(reraise: bool)` is the only transformer; `Pass.RECORDING` is `reraise=False`, `Pass.RERAISING`
is `reraise=True`. **The recording pass IS the handler-that-forgot-the-`raise`**, observed two ways:
**structurally** — a test asserts `bodies[False] == bodies[True].replace("\n        raise", "")`, so the
two are literally one `raise` apart and the control stays free — and **behaviourally**, on the
child-spawning arm: recording reports `exit_code == 0` and `BLIND`, re-raising reports non-zero and
`FAIL`. Wave 50 got this control by accident; this card got it by design and then measured it.

The transformer's node list is checked against an independent enumeration over a target with asserts nested
in `with` / `for` / `try` / `except` / `else`. The tree goes straight to `compile()` and is never
re-unparsed, so no line can shift.

### The domain is locked four ways, three of which raise

1. `run(pass_, …)` — `pass_` is **positional with no default**; omitting it is a `TypeError`.
2. `Matrix.__post_init__` raises `TypeError("pass_ must be a Pass member: a figure that does not carry its
   domain is the defect this instrument exists to prevent")` for anything that is not a `Pass`.
3. **The denominator is not caller-supplied** — the Runner computes it from `assert_linenos`, so a caller
   *cannot* hand in a test count; and `__post_init__` raises unless `len(cells) == denominator`, so the
   matrix must report every node.
4. The only reporting surface is `figure()`/`table()`, each interpolating pass and denominator
   unconditionally, with no `__str__`/`__repr__` shortcut — **and the reporting surface is enumerated from
   the module's own AST**, every method called, each output required to contain the pass name, the string
   `assertion node` and the denominator. **A reporting method added tomorrow is inside the check on the day
   it is added, and one the enumeration cannot call is a failure rather than a silent pass.** That is
   ADR-0039/R2's deny-default applied to the instrument's own output.

### ⚑ Why wave 50's child instrumentation mattered — found, measured, and deliberately departed from

Wave 50's instrument perturbed the child **unconditionally**. This one defaults `child_instrumentation` to
**off**, and the agent found the reason rather than guessing it: `_run_pytest` in `test_full_suite_lock.py`
**overwrites `PYTHONPATH`**, so an inherited `-p` flag cannot load and the child dies with a usage error.
**Measured: with inheritance forced on, SHIPPED showed 20 spurious FAILs** at `:974–:978, :1067–:1068,
:1092–:1093, :1104–:1107, :1115–:1118, :1136–:1141, :1167–:1168`. **Default-off is what makes anchor 1
reproduce at 130/130** — and with it off the child is pristine, propagation across the boundary is intact,
and those arms are measured for real, so the anchor is honest rather than a suppressed reading.

### Two findings in its own work, both the same rule biting the author

- **The first AC-1 plant deleted ONE line**, shifting asserts from `{9,10,11,18,19}` to `{8,9,10,17,18}` —
  **overlapping** the pristine numbering, so the matrix was silently **misattributed** rather than blank,
  and the "all NOT-REACHED" assertion was simply false. Fixed by deleting three lines. **A seventh shape,
  now recorded on CARD-259: a small line shift misattributes; only a large one reads NOT-REACHED — and
  misattribution is the worse of the two, because a misattributed cell looks like a measurement.**
- **The first AC-4 plant leaked into a module nothing in the selection imported**, so SHIPPED came back
  clean and `LeakedPatch` never raised — **the plant could not fail.** Fixed by having the target import
  the leaked module. A leak SHIPPED cannot see is not the trap.

### AC-4's plant is the shape the real leak took

Not a toy: an **incomplete backup registry**, so the path sits outside the bookkeeping and every
`diff -q`/`shasum` verification that ran was satisfied. **Only the between-mutants SHIPPED re-run can see
it** — and that re-run compares **cell for cell against SHIPPED's own first reading**, not merely
"FAIL-free", because a targeted selection legitimately leaves most asserts NOT-REACHED and a leak that
*removes* coverage would pass a FAIL-free check.

### Two shapes the card did not name, added anyway

**A target with two asserts on one lineno is refused** — the matrix is keyed on a lineno and could only
merge them, which is a quieter trap 2. And **the generated plugin's env-var names are interpolated from the
runner's constants**, with a test that reds if any name is hard-coded again.

### Declared bounds, four, two of them measured rather than asserted

1. `child_dependent_linenos` is **intra-function** and **over-marks** (measured: an arm after a spawn that
   reads nothing from it is still marked — the fail-closed direction), and does **not** see an arm reading
   a child's outcome through a helper's return (measured: returns the empty set). **A dataflow rule would
   be a silent PASS on a suppressed arm; this one is not.**
2. The `BLIND` overlay applies **only** when `child_instrumentation=True` (see above).
3. One target file per run; a two-file selection is refused, so a matrix's domain is never ambiguous.
4. The database-guard refusal is a **path-and-text** refusal over the sites that carry the guard today, not
   an analysis of what an edit would do — stated as such in the module and the README.

### Sibling audit, and the card's premise verified rather than assumed

`grep` over `tests/ src/ scripts/` finds **no other** per-assertion or mutation instrument in the tree, **no**
`git checkout`/`git restore`/`git stash` anywhere, and the only `.full-suite.lock` writers are the existing
CARD-255/256 guard family. **This is the first instrument committed** — which was the card's entire premise.

Prose-to-mechanism, measured because CARD-257 made it a board concern: `kill_matrix.py` **0.48 : 1**,
`test_kill_matrix.py` **0.36 : 1** — both far under the 1.69 : 1 that card cut. Tree-wide census guards
re-run with the new files present (`test_guard_integrity`, `test_naming`, `test_suite_profile`,
`test_fixture_integrity`, `test_cli`, `test_full_suite_lock`, `test_run_admin_tests`,
`test_db_engine_lifecycle`): **754 passed.**

### Guardrails, each with a planted failure

G-1 empty selection / directory / non-file / two files · G-2 a lock planted in a **tmp** tree, never the
board's; the instrument never writes a lock and never sets `NONOGRAM_FULL_SUITE_LOCK` · G-3 three refusal
shapes, and the instrument **refuses any edit naming `nonogram_poc` or `_refuse_unless_test_database`, or
any edit to `tests/conftest.py` or `tests/database_guard.py`** · G-4 stdlib-only by AST · G-5 argv
enumerated from the AST (`cp`, `diff`, `shasum`, `sys.executable`) plus every string constant matching
`git(\s|$)` — **an argv it cannot enumerate is a failure, not a skip** · G-6 no clock read, with `time`,
`timeit`, `datetime`, `resource`, `cProfile` and the names `perf_counter`/`monotonic`/`process_time`/
`elapsed` all forbidden by an import census; `subprocess`'s `timeout=` is declared as a bound on a hung
child, not a measurement.

**No AC is certified by the instrument's own report of success** — which was this card's declared trap.
