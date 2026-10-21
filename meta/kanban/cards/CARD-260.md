# CARD-260: Commit the per-assertion kill instrument once, with all six of its known traps as controls

**Status:** review
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
**Review score:** 8.8 (round 5 — re-entry cycle 2/3)
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
- G-2: It never writes a lock, and refuses to start when `meta/kanban/.full-suite.lock` is held by
  **another** worktree — taking `full_suite_lock.current_verdict()` whole rather than re-deriving it, so
  an own-tree, a stale, or an announced-override lock does **not** refuse.
  **[Restated at the AC/EC/G gate, 2026-10-21.]** The original wording was "refuses to start if
  `meta/kanban/.full-suite.lock` exists", and the code does not do that — deliberately. A gate holds
  that file for its whole duration, so the literal rule made the instrument refuse inside the very gate
  certifying it: **23 `LockHeld` reds in build gate 3**, recorded under `### [Build-fix 1/2]`, closed by
  adopting CARD-255's identity rule (by **worktree**, not by existence). The guardrail's text was never
  updated to match that decision; this is that update, not a weakening. The foreign-holder refusal that
  remains **is** controlled — `allowed or 1` reds two arms, and re-deriving `board_lock_path` locally reds
  a third.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-4: No new runtime dependency (ADR-0006/R1) — `ast`, `pathlib`, `subprocess`, `tempfile` are stdlib.
  **[Corrected at the AC/EC/G gate, 2026-10-21.]** This line named `hashlib`, which the instrument does
  **not** import: the digest comes from the external `shasum` binary, which is exactly why
  `_verification_failures` carries a "shasum could not run" branch at all. The guardrail held; its
  prose named a module that is not there.
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
  figure and 5 from an independent **tokenise-and-count** route that never builds a tree (cycle 1, F-010:
  the control used to be `ast.walk` again, which is the same route rewritten and blind to a shared
  misconception about what an `ast.Assert` enumerates). The fixture has **5 assertion nodes and 2 collected tests
  on purpose** — on a file where the two agreed, the check could not fail.

### Both AC-7 anchors reproduced — cell for cell, including the pre-aggregation lists

**Anchor 1**, `tests/test_full_suite_lock.py` at `ddb1731b`: node count **130**, re-derived by the
independent tokenise-and-count route (agreeing with the AST on 130, 47 and 5); recording pass SHIPPED **130 of 130 PASS and reached, zero NOT-REACHED, zero FAIL**;
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
reproduce at 130/130** — and with it off the child is pristine and propagation across the boundary is
intact, so the arms that **read** a child's outcome are measured for real, which is the whole of what
default-off buys (cycle 1, F-004: the sentence used to say "those arms", and an arm that executes only
*inside* the child is not one of them — it writes no record and reads `NOT-REACHED` though it ran). Anchor
1 is honest rather than suppressed for a reason that is now stated instead of implied: that file selects
one of its **own** tests into the child, so its 7 child-dependent arms also execute in the parent and
record there — all 130 are PASS, none of them `NOT-REACHED`. See declared bound 2.

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

Since cycle 1 the restore itself cannot abandon its tail (F-008): **every** registered path is restored
before any verification failure is raised, and the failures are reported together — raising from inside
the loop skipped every path after the first, and the outer `finally`'s re-run failed at the same point, so
in this card's own second anchor the file left mutated would have been `src/nonogram/db/session.py`. A
`shasum` that could not run is one of those failures rather than a pass. Still outside the fix and worth
knowing: the `tempfile.mkdtemp` workdirs are never cleaned up, and the anchors mutate real tracked files
in the working tree for the length of a measurement, so an abnormal termination still leaves them edited.

And the children run with `PYTHONDONTWRITEBYTECODE=1` rather than the flake being declared as a bound: a
mutant edit is often byte-identical in length to the pristine file and can land in the same mtime second as
the reading before it, at which point that reading's `.pyc` still validates and the next child imports a
file no longer on disk. Seen once, as a single cell reading `PASS` where its re-run read `FAIL`. No reading
writes bytecode now, so no later reading can read one written in the same second, and a `.pyc` from before
the run predates every mutant's mtime and is invalidated normally.

### Two shapes the card did not name, added anyway

**A target with two asserts on one lineno is refused** — the matrix is keyed on a lineno and could only
merge them, which is a quieter trap 2. Since cycle 1 that refusal is **re-derived from the mutated file**
too (F-011): it was computed once on the pristine source, and a line-count-preserving mutant that merges
two asserts onto one line reintroduced the shape past it. And **the generated plugin's env-var names are interpolated from the
runner's constants**, with a test that reds if any name is hard-coded again.

### Declared bounds, eight, seven of them measured rather than asserted

Bounds 2 and 4 were **re-derived from the code after cycle 1's fixes**, not re-worded; 5 and 6 are new;
**7 is re-derived from build-fix 1's code** and replaces the strict reading cycle 1 shipped. After cycle 2:
**bound 2's justification is re-derived from an AST census of both anchors** (the clause it carried was
false on both at once, F-201), **bound 5 now says what exit `1` does *not* establish**, and **bound 8 is
new** — the domain bound that was the only one of this instrument's boundaries never written down, which
is why F-202's shape was findable at all.

1. `child_dependent_linenos` is **intra-function** and **over-marks** (measured: an arm after a spawn that
   reads nothing from it is still marked — the fail-closed direction), and does **not** see an arm reading
   a child's outcome through a helper's return (measured: returns the empty set). **A dataflow rule would
   be a silent PASS on a suppressed arm; this one is not.**
2. The `BLIND` overlay applies **only** when `child_instrumentation=True`. With it off the child is
   pristine and propagation is intact, so the arms that **read** a child's outcome are measured for real —
   and nothing more than that. An arm that executes only *inside* the child writes no record, so with the
   overlay off `NOT-REACHED` means "no execution recorded in the instrumented process", never "this arm
   did not run", and `0 BLIND` means the overlay never ran. **Now measured** rather than asserted: both
   figures carry the flag, and `test_ac3_the_flag_off_reading_on_a_child_spawning_target_is_the_bound`
   takes the flag-off reading on a child-spawning target beside the flag-on one — `:11` `NOT-REACHED` vs
   `FAIL`, `:20` `FAIL` vs `BLIND`, 0 BLIND vs 1 BLIND. Narrowed rather than reported as an explicit
   unmeasurable state because the in-child arm sits **above** the spawn and so is not in
   `child_dependent_linenos` at all, and the one fail-closed set that would contain it ("every
   `NOT-REACHED` arm in a file that spawns anything") is a **coarser position rule** — a targeted
   selection legitimately leaves most of a file's asserts `NOT-REACHED`, so that set relabels every arm
   the selection never ran, deciding a cell from position standing in for a cause the instrument cannot
   observe. **What that set would cost on the anchors is nothing, and the earlier wording here claimed
   otherwise (F-201).** Measured by AST census: anchor 2's target `tests/test_db_engine_lifecycle.py` has
   **no spawn-shaped call at all** (`child_dependent_linenos` → `frozenset()`; its single textual
   "subprocess" is a comment), so the set's precondition is unsatisfied there and it would relabel
   *nothing* in that file — the three `NAMES-BLIND` arms included; anchor 1's target does spawn (7
   child-dependent arms of 130 assertion nodes) but reproduces 130 of 130 reached, so it has no
   `NOT-REACHED` arm to relabel either. The anchors neither support nor refute the set; what rejects it is
   the position-for-cause substitution, which is the same move bound 8 refuses for `exit 1`. **The census
   is now a control, not a sentence:** `test_ac3_the_rejected_fail_closed_set_would_relabel_nothing_on_either_anchor`
   holds anchor 2 at zero spawn-shaped calls and `child_dependent_linenos() == frozenset()` and anchor 1
   at a non-empty one, and says "re-derive the bound rather than the expectation" if either moves.
3. One target file per run; a two-file selection is refused, so a matrix's domain is never ambiguous.
4. The database-guard refusal is a **path-and-text** refusal over the sites that carry the guard today, not
   an analysis of what an edit would do — stated as such in the module and the README. **The two halves
   have different reach, and that is now stated too:** the **path** half is by identity (`realpath`,
   `casefold`-ed parts, `samefile`) and is what refuses a guard-defeating edit, including one that names
   neither literal; the **text** half is two literals catching only an edit that *names* one of them, and
   its own reach is a copy of the guard elsewhere in a tree plus any edit re-introducing the live panel's
   database name. The set itself is unchanged: `tests/conftest.py` and `tests/database_guard.py` are both
   halves of the guard and there is no third site.
5. **A reading is a run.** Only pytest exit codes `{0, 1}` are published; 2/3/4/5 raise `UnmeasuredRun`,
   because the matrix they produce is all-`NOT-REACHED` and FAIL-free — the shape of a mutant every arm
   survived. `collected_tests` is **not** the precondition (it is regex-scraped from the `-q` summary and
   would read `None` on a good run the day that wording changes) and stays print-only. Measured both ways:
   a dead node id raises, and a killed mutant at exit 1 publishes. **What exit `1` does not establish is
   which cause it was** — see bound 8; the precondition is "pytest ran this selection", never "the cells
   account for what happened".
6. **The keys are re-derived from the file that runs.** Equal line counts are necessary and not sufficient,
   so after every `_apply` the target's assert **topology** (each node's `lineno` *and* what the assertion
   at it says) is compared with the pristine one; a moved, swapped or merged assert, and an unparsable
   target, are refused. A no-op for a mutant that edits anything but the target — measured, because the
   grid anchor 2 reproduces mutates `src/nonogram/db/session.py` while the target is a test file.
7. **The lock refusal is worktree identity, and the verdict is its owner's — whole.**
   `_refuse_if_lock_held` calls `full_suite_lock.current_verdict()` and raises `LockHeld` only on its
   refusal; it re-derives neither the path (that was F-001) nor the rule (that was build gate 3's 23
   reds). So: a **foreign** holder refuses the start; a lock the instrument's **own** tree holds does
   **not** — every full-suite gate holds exactly that file for its whole duration, so refusing on *any*
   lock means the instrument cannot run inside the gate that must certify it. **The staleness window
   (`STALE_SECONDS`) and the override arrive with the verdict, deliberately and not as leniency:** this
   code runs inside a pytest that same hook already admitted, so strictness beyond it reds a suite the
   board decided to run, and laxity below it would start a run whose child the hook kills — one function,
   one answer, agreement that is structural rather than two copies that happen to match. Neither
   relaxation is silent (the owner's terminal-summary hook announces both). The composition F-001 closed
   stays closed: a foreign lock still refuses the start, so no run can begin whose child the hook would
   kill, and an own-tree lock was never the hazard — that hazard is two *different* trees running heavy
   pytest at once, while a child spawned inside the instrument's own tree is already serialised by being
   one process tree and that child's own hook resolves the same tree. **Measured four ways rather than
   asserted:** foreign/own/stale-foreign/override, each compared against `current_verdict()`'s own answer
   (`test_g2_the_refusal_is_its_owners_verdict_and_not_a_second_opinion`), plus the own-tree case alone
   (`test_g2_a_lock_this_worktree_holds_does_not_refuse_the_start` — the control that reds if the strict
   rule returns) and the foreign-plus-decoy case
   (`test_g2_a_foreign_lock_refuses_the_start_and_repo_root_does_not_move_it`).

8. **The matrix's domain is `ast.Assert` nodes, so a kill expressed any other way is outside it.** A
   failure raised through `pytest.raises` or `pytest.fail`, a `unittest` assertion, an assert inside a
   helper the target calls, or an error before the first assert is a **real kill no cell can account
   for**, and its reading is `0 FAIL` at exit `1`. So `exit 1` with no `FAIL` cell means "pytest failed
   this selection for a reason outside the matrix's domain", **never** "every arm survived". Published
   rather than refused, deliberately: a refusal keyed on that *position* cannot tell an out-of-domain kill
   from a run that accounted for nothing, and `UnmeasuredRun` propagates out of `run()`, so one
   out-of-domain kill would destroy every other mutant's reading in the same run — refusing hardest
   exactly where the target is least assert-shaped. The distinction is **carried, not inferred**: every
   mutant's own `exit_code` and reached count are now in `KillMatrix.figure()` (and so in `table()`'s
   header), which before this fix carried **only SHIPPED's**, so the per-`Matrix` caveat never reached the
   consumer. The one refusal is on **SHIPPED**, where there is nothing to be wrong about: a baseline that
   reached no arm is not a baseline whatever its exit code — a third condition inside the gate that
   already owns that claim (`_refuse_unless_clean`), on the quantity its own aggregate figure already
   prints. **Measured both ways:**
   `test_g1_a_kill_outside_the_matrix_domain_is_attributable_in_the_figure` (two mutants whose cells are
   cell-for-cell identical, exit 0 against exit 1 — the figure is the only place they differ) and
   `test_g1_a_shipped_that_reached_nothing_is_not_a_baseline` (a fixture-errored SHIPPED published as
   `0 PASS, 0 FAIL, 2 NOT-REACHED` at exit 1, then refused).

### Sibling audit, and the card's premise verified rather than assumed

`grep` over `tests/ src/ scripts/` finds **no other** per-assertion or mutation instrument in the tree, **no**
`git checkout`/`git restore`/`git stash` anywhere, and the only `.full-suite.lock` writers are the existing
CARD-255/256 guard family. **This is the first instrument committed** — which was the card's entire premise.

Prose-to-mechanism, measured because CARD-257 made it a board concern: `kill_matrix.py` **0.48 : 1**,
`test_kill_matrix.py` **0.36 : 1** — both far under the 1.69 : 1 that card cut. (Both figures are **as
measured at `f9718739`**; cycle 3's fix adds prose to both files and mechanism to both, and is not
re-measured here because this record does not state the method that produced them.) Tree-wide census guards
re-run with the new files present (`test_guard_integrity`, `test_naming`, `test_suite_profile`,
`test_fixture_integrity`, `test_cli`, `test_full_suite_lock`, `test_run_admin_tests`,
`test_db_engine_lifecycle`): **754 passed.**

### Guardrails, each with a planted failure

G-1 empty selection / directory / non-file / two files, **plus a selection that resolves and whose node id
does not exist — a run pytest never made is refused, not published** · G-2 **both halves come from the lock's owner, path and
rule**: `tests/full_suite_lock.py` resolves the path (so a linked worktree watches the **main** checkout's
file) and `current_verdict()` gives the verdict, so a **foreign** holder refuses the start and a lock the
instrument's **own** tree holds does not — read as G-2 means (the hazard is contention between
*different* trees), never as G-2 weakened, because a gate holds that file for its whole duration and the
strict reading cannot run inside the gate that certifies it. Controls: the path compared against that
owner (the cycle-1 one planted a lock in a `tmp_path`, which cannot fail: a tmp tree has no `.git`, so the
broken and correct paths coincide there), a foreign lock planted on a tmp path through the guard's own
override with a **decoy** under `repo_root` that must *not* refuse, an own-tree lock that must *not*
refuse, and four lock states each asserted equal to `current_verdict()`'s own answer so a second opinion
written into the instrument reds. The board's real lock is never created, deleted or touched — the guard's
own path override, `monkeypatch`-ed for the length of one test, is what every control plants on instead —
and the instrument itself never writes a lock and sets no env switch · G-3 two text shapes and **seven spellings of the two guard files** —
mis-cased file, mis-cased directory, `..`, absolute — plus a guard-defeating edit that names neither
banned literal and is refused for where it lands · G-4 stdlib **plus one pinned sibling of this
directory** (`full_suite_lock`, the lock path's owner) by AST · G-5 argv
enumerated from the AST for every **spawn-shaped** callee (`_SPAWN`, so `os.system`/`Popen` are inside it,
and an import that would let a spawn be called under a bare name is refused): `cp`, `diff`, `shasum`,
`sys.executable`, plus every string constant matching `(\S*/)?git(\s|$)` so an absolute path is inside it
and prose about git is not — **an argv it cannot enumerate is a failure, not a skip**, and a command
assembled at run time out of pieces that are not themselves `git` is a declared bound **with its own
demonstration** since cycle 3 (both halves run over a source that assembles one and asserted to miss it,
in bound 1's shape, F-204) · the run's temp tree (backups, generated plugin, every `records-*`) is
removed when `run()` returns and kept only when a restore did not verify, with the directory named in
the exception (F-203) · G-6 no clock read, with `time`,
`timeit`, `datetime`, `resource`, `cProfile` and the names `perf_counter`/`monotonic`/`process_time`/
`elapsed` all forbidden by an import census; `subprocess`'s `timeout=` is declared as a bound on a hung
child, not a measurement.

**No AC is certified by the instrument's own report of success** — which was this card's declared trap.

---

## Orchestrator — review phase entry, 2026-10-21

- **[Env]** forge **2026.8.17**. No `meta/.skills.yml` in this project, so no `forge.min_version`
  comparison and no `models:` block — review / fix / AC-check agents inherit the session model with no
  `model:` override.
- **[Scope]** `tests/README.md`, `tests/kill_matrix.py`, `tests/test_kill_matrix.py` —
  `git diff --name-only main...HEAD` at `f9718739`, worktree clean. `forge:fix` may touch only these three.
- **[Scope gate]** **IN_SCOPE.** `excess` = 0 — the three files are the card's `Touches` exactly, no
  fourth path. `comp_spread` **skipped** (no `## Architecture context` section, so no declared component
  list). `poached` **empty**: **CARD-259** consumes this card's instrument and names none of these three
  files in its own `Touches`, and it sits in wave 52 regardless. `guardrail_hits` **skipped**: G-1…G-6
  are all behavioral — G-2 and G-5 name a lock path and `git` but as *things the instrument must not do*,
  not as areas the diff must not touch — so they belong to the AC/EC/G gate.
- **[System contract]** Freshness re-checked, not assumed: `system_rules.py --card CARD-260` projects
  **10** rules; the card's section carries **5**, which is exactly what `meta/kanban/curation.md`
  selects — the 2 `review-lens` rules (ADR-0038/R7, ADR-0038/R8) plus the 3 reach-limited `kind: test`
  rules (ADR-0039/R1–R3). The 5 dropped (CON-005, CON-009, CON-010, CON-011, CON-012) are plain
  `kind: test`. Ids added: none. Ids removed: none. Section left as written.
- **[Build gate 2 — PASSED]** `2026-10-20T18:56:46Z`, commit `f9718739`, solo: **8670 passed**, 1
  skipped, 0 failed, 1363s (22:43), EXIT=0. **This is this cycle's gate**, and it certifies the exact
  commit under review. Count reconciles against gate 1 exactly — gate 1 collected 8671 (8669 passed +
  1 failed + 1 skipped), gate 2 collects 8671 (8670 + 1 skipped) — so gate 1's single red
  (`test_puzzle_solver_progress.py::TestSolverProgress_LockedUntilReset::test_ac318_click_drag_undo_redo_change_nothing`,
  a playwright `wait_for_function` timeout) **passed on the identical commit with nothing fixed in
  between**. That is the flake attribution gate 1's control runs argued for, now confirmed rather than
  assumed. The one skip is the long-standing `setrlimit(RLIMIT_AS)` platform skip, unrelated to this card.
- **[Build gate — provenance, because it is not clean]** The session that ran gate 2 died before reaping
  it, so the result reached this card only on 2026-10-21, from the completed run's own output. Before
  that output arrived I had read the orphaned `meta/kanban/.full-suite.lock` (10.1h old, stale past the
  project's `STALE_SECONDS=21600`), broken it correctly, and started a **gate 3** on the same commit.
  Gate 3 was then **stopped at ~10%, zero failures** — redundant beside a green gate 2 on the identical
  commit, and compromised as evidence in its own right: when the harness reaped gate 2's wrapper it ran
  that wrapper's trailing `rm -f "$LOCK"`, deleting gate 3's lock mid-run, so gate 3 held no lock for
  part of its life. No timing comparison is drawn from either run — two full suites were reaped around
  each other on this machine, and G-6 forbids timing claims from this card anyway.

### [Review 1/3] Score: 4.0 — FAILS hard: 4 Critical, 3 Important

Report: `meta/review/20261021T051740Z-CARD-260-cycle1.yml` — 11 findings (4 critical / 3 high / 4 low),
5 system-contract verdicts. **[Review sync]** 1 report → `meta/review/`.

**Step 8h coverage: PASS** — count line present, all 5 curated rules carry a verdict. **2 ✓ holds
(ADR-0038/R7, R8), 3 ✗ violated (ADR-0039/R1, R2, R3).** All three reach-limit rules violated is the
signature this card was cut to avoid: an instrument whose job is measuring whether an assertion can fail,
making claims wider than its own reach.

**What the reviewer certified, and it matters that this is not a wholesale failure.** All 7 ACs pass.
Both AC-7 anchors reproduce — the reviewer ran the file: **42/42 pass**, including the 130/130 node count
and the 14-mutant grid. The card's declared trap **"no AC is certified by the instrument's own report of
success" HOLDS**: every AC's evidence is a refusal, a disagreeing control, a `raw_cells`-vs-`cells`
difference, or an externally-measured anchor. The **sibling audit's three bounds are all verified
accurate** by independent grep (no other `ast.Assert` instrument; no `git checkout/restore/stash`
anywhere — the three `restore` hits are HTTP action strings; `.full-suite.lock` writers are the
CARD-255/256 family only). **Declared bound #1 is called exemplary** — fail-closed *and* carrying a
control whose failure message tells the next agent to move the bound rather than the expectation. The
`bodies[False] == bodies[True].replace(...)` structural control and the AST-enumerated reporting surface
are named the two best mechanisms in the diff, unaffected by any finding, and **worth carrying into
CARD-259**.

**The score, and why the reviewer did not report the mechanical one.** Mechanical deduction gives
**1.0**; the reviewer reported **4.0** and said why: every defect is a *locally closable check* — one
topology re-derivation, one path canonicalization, one liveness precondition, one lock-path resolution —
while the transformer/two-pass architecture and its free structural control are sound. Recorded as the
reviewer's stated judgement, not as arithmetic. **The severity gate, not the number, is what blocks this
merge**, and it would block at 4.0 or at 9.0.

**The 4 Critical findings — all reproduced in sandboxed probes, not inferred:**

- **F-001 — `kill_matrix.py:677` — G-2's lock refusal checks a path no gate ever writes.**
  `_refuse_if_lock_held` tests `repo_root/meta/kanban/.full-suite.lock`, but
  `tests/full_suite_lock.py`'s `default_lock_path()` resolves through `main_repo_root()` to the **main**
  checkout. Derived live: km checks `…-card-260/meta/kanban/.full-suite.lock`, the real lock is
  `…/PythonProject4/meta/kanban/.full-suite.lock`, `SAME? False`. **Both AC-7 callers pass
  `repo_root=REPO` = the worktree**, so in the only shipped configuration **G-2 is inert** — a gate
  holding the board's real lock will not stop this tool mutating `src/nonogram/db/session.py` and
  spawning pytest, which is precisely the contention CARD-255 exists to prevent. `NONOGRAM_FULL_SUITE_LOCK`
  is ignored. And the control at `test_kill_matrix.py:864` plants its lock at `tmp_path/meta/kanban/`
  with `repo_root=tmp_path`, so it **can never fail for the real path**.
- **F-002 — `kill_matrix.py:344` — a mis-cased path defeats G-3 and clobbers the database guard.**
  `parts[-len(forbidden):] == forbidden` is a case-sensitive tuple compare. Reproduced in a sandbox tree:
  `tests/conftest.py` refused, but `tests/CONFTEST.py`, `tests/Conftest.py` and
  `tests/DATABASE_GUARD.py` were **ALLOWED** — and on this filesystem the mis-cased path reads the same
  file, so `apply_edit` + `write_text` through it changed that tree's `conftest.py` from `GUARD = 1` to
  `GUARD = 0`. The text refusal does not cover for it: a guard-defeating edit need not name
  `_refuse_unless_test_database` or `nonogram_poc` (e.g. `'.endswith("_test")'` → `'.endswith("")'`).
  `tests/conftest.py:224` is the one check standing between the fixture's `DROP SCHEMA public CASCADE`
  and the live panel's `nonogram_poc`.
- **F-003 — `kill_matrix.py:427` — an equal-line-count edit that moves an assert is accepted, and a real
  kill is reported `NOT-REACHED`.** `_refuse_line_shift` compares only `count("\n")` and
  `len(splitlines())` while cells stay keyed on pristine linenos. Reproduced: pristine `(6,)` → mutated
  `(5,)` **accepted**, `MUTANT km_move.py:6 NOT-REACHED`, `records {5: (False,)}` — the arm ran and
  **failed**, exit 0, no refusal. **This is the misattribution the card's own notes call the worse
  outcome**, and `_refuse_line_shift`'s docstring claims to prevent its consequence. The evidence is
  already in `records`.
- **F-005 — `kill_matrix.py:869` — a run in which nothing executed is reported as a complete, FAIL-free
  measurement.** `exit_code` and `collected_tests` are recorded but **no refusal consults either**;
  `_refuse_unless_clean` demands only "no FAIL" and "equals the baseline", both trivially true of an
  all-`NOT-REACHED` reading. Reproduced with a resolvable selection naming a non-existent node id:
  `0 PASS, 0 FAIL, 5 NOT-REACHED … (collected tests: None)`, `exit_code = 4`, every mutant cell
  `NOT-REACHED`, **no refusal** — and the baseline comparison passes because the baseline is equally
  blank. Any non-run takes this route: collection error, stale node id, import failure, **or this
  project's own `full_suite_lock` hook refusing the child pytest.**

**The 3 Important:** **F-004** (`:877`) — with `child_instrumentation` **off, which is the default**, an
arm that ran and failed in the child reads `NOT-REACHED`, and neither `figure()` nor `table()` carries
the flag, so `0 BLIND` cannot be distinguished from "the overlay never ran"; bound #2's justification is
true only for the parent's returncode arm, and the exempted state has **no control**. **F-006** (`:130`)
— the database-guard set is hand-written and never held to an equality against the sites carrying the
guard today; `tests/database_guard.py` is in the declared set and has **no control at all**.
**⚠ This summary was REFUTED at adversarial verification — see the verdict below. The parenthetical I
originally wrote here, inferring from `grep -c _refuse_unless_test_database tests/database_guard.py` = 0
that "the set is not derived from where the guard actually lives", was WRONG, and I had also fed that
inference to the skeptic as a leading hint. `database_guard.py` **is** the guard's other half; it simply
spells its logic differently. Only the missing control survives, as a Minor.** **F-011** (`:773`)
— the two-asserts-on-one-lineno refusal is computed on the pristine source only and is bypassed by a
same-line-count mutant that merges two asserts, yielding one cell for two nodes: "the quieter trap 2"
the card says it refuses.

**[Adversarial] F-001 CONFIRMED (Critical)** — six refutation lines tried, all failed, and the "caller
mistake" escape hatch died hardest. By execution from inside the worktree:
`default_lock_path()` and `lock_path()` both → `…/PythonProject4/meta/kanban/.full-suite.lock`, while
`_refuse_if_lock_held` (`kill_matrix.py:677-683`) builds
`…-card-260/meta/kanban/.full-suite.lock` — `SAME? False`. A grep for
`NONOGRAM|getenv|environ.get|rev-parse|gitdir|parent.parent|LOCK_PATH` finds **no** reach to the main
root: no env var, no `git rev-parse`, no `..` walk, no `main_repo_root` import.
- **Why it cannot be downgraded to a caller mistake.** `repo_root` is used in exactly three places:
  the lock path (`:678`), relative-selection resolution (`:701` `path = self.repo_root / path`), and the
  subprocess `cwd` (`:933`). `FOUR_ARM` is a *relative* selection, so it resolves through `:701` into
  `self.target` — **and `self.target` is the file the instrument reads, backs up and mutates** (`:771`,
  `:782`). Passing the main root to fix the lock check would **point the mutation edits at the main
  checkout.** The parameter is overloaded; the defect is structural.
- **The control provably cannot discriminate.** Run against a hypothetical correct implementation: a
  `tmp_path` has no `.git`, so `main_repo_root` returns itself and `default_lock_path(tmp)` equals where
  the control plants its lock — `control would ALSO pass under the correct impl: True`.
- **Aggravating, and the skeptic found it in this card's own sibling file:**
  `tests/test_full_suite_lock.py:764`, `test_every_worktree_resolves_the_one_lock_the_gates_write`,
  docstring: *"A per-worktree lock path would be a guard that cannot see contention."* **G-2 implements
  precisely that.** `tests/README.md:518` documents the behaviour as "under the given repo root", so the
  prose is faithful to the code and the docs do not catch it either.
- **Mitigating, and it narrows the blast radius without rescuing G-2:** the child pytest runs with
  `cwd=self.repo_root` inside the worktree, so it imports `tests/conftest.py`, whose `pytest_configure`
  calls `_full_suite_lock.pytest_configure` first (`conftest.py:96`) and reads the **real** main-root
  lock. A real lock would still stop the child with a `UsageError` — but only *after* G-2 let the run
  start and the instrument already edited the target and took backups. **A backstop in another component
  is not G-2 working.** Practical cost of a collision: a wasted edit-and-restore cycle rather than two
  colliding full suites. (Skeptic flagged this as inferred from reading, not executed.)

**[Adversarial] F-002 CONFIRMED — and the skeptic corrected the finding in three ways that change the
fix.** The mechanism is exactly as reported: `kill_matrix.py:343-349` compares raw `Path.parts`, and a
grep for `resolve|normcase|samefile|casefold|lower|realpath` across all 944 lines finds the only two
`resolve()` calls in the *generated child plugin* (`:582`) and in the instrument's own `sys.path` entry
(`:895`) — **neither in the refusal path**. Volume confirmed case-insensitive (`echo > a.txt; cat A.txt`
→ `hello`). Driven end-to-end through the **real `Runner.run`** in a sandbox, observing the sandbox's
real `tests/conftest.py` per pass: `SHIPPED → GUARD = 1`, `MISCASED-GUARD → GUARD = 0`,
`SHIPPED after → GUARD = 1`. `Edit.__post_init__` is the **only** gate — `Runner._apply:853-866` writes
straight to `edit.path` with no re-check.
- **Correction 1 — it is a bounded window, not permanent corruption.** The `cp -p` backup registry uses
  the same mis-cased path and therefore the same inode, so the file is restored after the run. **The
  window is the hazard** — it is open for the length of that mutant's pytest subprocess, which is
  precisely when the destructive fixtures could run. The card should say this; "clobbers the guard" alone
  overstates the persistence and understates the timing.
- **Correction 2 — a fourth bypass the finding did not list:** a mis-cased *directory*,
  `TESTS/conftest.py`, walks past too. A fix that only normalizes the filename misses it.
- **Correction 3 — the text half stays blind even after the casing fix, and the example is the LIVE
  guard.** `_FORBIDDEN_TEXT` is only two literals, and the skeptic verified `'.endswith("_test")'` →
  `'.endswith("")'` **passes the text gate**. That exact line is `tests/conftest.py:287`
  (`if not name.endswith("_test"):`), with `DROP SCHEMA public CASCADE` at `tests/conftest.py:505`. A
  line-count-preserving substitution there names neither banned string and passes `_refuse_line_shift`.
  **So this is two fixes, not one.** (Honest qualifier the skeptic volunteered: the guard checks
  `TEST_DATABASE_URL`, not `DATABASE_URL`, so the drop reaches `nonogram_poc` only if
  `TEST_DATABASE_URL` points there — which is the guard's own threat model, not an escape from it.)
- **Severity: the skeptic argues High/Important, not Critical, and I am recording its reasoning rather
  than overruling it.** There is no CLI and no directory walk in `kill_matrix.py` (`argparse`/`__main__`/
  `def main`: zero hits), and every `Edit` path at every call site is a hand-authored literal — so a
  mis-cased spelling requires a human typing it from memory or deliberately bypassing the gate, not a
  walk yielding a non-canonical spelling. Tab completion and copy-paste both yield canonical casing.
  **It gates identically either way** (Critical and Important both close the success path), so nothing
  about the loop changes; what changes is how the fix is framed — a default-deny belt with a hole a
  one-line canonicalization closes, plus a second, separate fix for the text half.

**[Adversarial] F-003 CONFIRMED (Critical) — and the skeptic found a strictly worse variant the
finding's own proposed fix would NOT catch.** All four links hold, reproduced on a throwaway target in a
temp root.
- **`_refuse_line_shift` is four lines and compares nothing else** (`:427-450`): `before = (count("\n"),
  len(splitlines()))` vs `after`, raise if unequal. It is called from `apply_edit:416` as the last step
  and is the **only** post-substitution check — no AST comparison, no post-mutation `assert_linenos`
  re-derivation, and no refusal anywhere keyed on `set(records) - set(linenos)`.
- **Keys come from pristine and nothing re-checks them.** `run()` derives keys once at `:772`, and after
  `_apply` calls `_measure(..., pristine)`, which re-derives from the **pristine** string at `:874`.
  Everything `run()` does after `_apply` is `_measure` → `_restore` → `_measure` → `_refuse_unless_clean`
  — and **`_refuse_unless_clean` is only ever applied to the SHIPPED matrices** (`:784`, `:803`), never
  to the mutant's own. Nothing inspects the mutant reading at all.
- **Reproduced.** Equal-line-count edit relocating an assert from line 7 to 6:
  `apply_edit: ACCEPTED`, `mutated assert linenos: (6, 8)`, and the published matrix read
  `km_throwaway_target.py:7 | NOT-REACHED` with `MUTANT records: {6: (False,)}` — **the assertion ran and
  failed** — `0 FAIL`, `exit_code: 0`, no refusal. `raw_cells` agrees with `cells`, so there is no
  internal disagreement to notice, and no `BLIND` (that overlay only fires under
  `child_instrumentation=True`, which is F-004's territory). A genuine kill published as "never reached".
- **Not contrived — the shape is *declared supported*.** `tests/test_kill_matrix.py:185-215`
  (`test_ac1_the_edge_of_the_claim_is_the_line_count_and_nothing_else`) **explicitly blesses**
  same-line-count multi-line substitutions: "The claim is *the line count*, not *the deletion*". Every
  mutant shipped today happens to be a single-token one-line swap, which is why nobody hit it — but the
  API takes arbitrary multi-line `old`/`new`, mutants here are hand-written by agents, and "inline this
  binding into the assert" or "move the assert above the guard" are ordinary things an agent writes.
- **The documentation actively misleads rather than caveats.** `tests/README.md:518` states the refusal
  as covering "a mutant that changes the **line count**", with the rationale that "every assert below the
  edit shifts its `lineno` and reports `NOT-REACHED`" — i.e. it offers line-count stability **as if it
  were sufficient for lineno stability**, which this repro falsifies.
- **⚠ THE WORSE VARIANT, and it is the reason this finding must not be fixed as written.** A mutant that
  merely **reorders two asserts** keeps the lineno tuple **identical**, so there is no off-key and the
  misattribution is **evidence-free**: `mutated assert linenos: (6, 7)` = pristine, `cells {6: 'FAIL',
  7: 'PASS'}`, `records {6: (False,), 7: (True,)}`, `off-keys: set()`. The arm whose source text actually
  reds is the one at pristine line 7, and the matrix pins the `FAIL` on line 6. **The proposed
  tuple-equality fix does not catch this case.** Closing it needs the stronger invariant — per lineno,
  the assert's own source text or AST shape is unchanged — or at minimum the tuple check *plus* a
  separate refusal on `set(records) - set(linenos)` for the off-key case.
- **False-positive cost of the fix, assessed:** re-deriving `assert_linenos` on the mutated source and
  requiring tuple equality has essentially **no** false-positive cost for a target-file mutant — a mutant
  meant to change behaviour never needs to move a target assert's line, and every substitution the
  campaign actually uses preserves the tuple. Two caveats the fix must honour: the check must be a no-op
  for edits to files **other than the target** (a production-file mutant passes it trivially), and it is
  **incomplete** on its own for the reorder variant above.
- `pytest tests/test_kill_matrix.py -k ac1 -q` → **6 passed**: the suite is green with this hole open,
  and the hole sits **inside** its own declared claim.

**[Adversarial] dropped false positive: F-006 "the database-guard set is hand-written and never held to
an equality"** — the finding is a conjunction with a **false headline**. "Hand-written" is true;
"described as derived" is **verbatim-refuted in four places**; "content wrong" is false.
- **Nothing anywhere claims derivation.** `kill_matrix.py:65-68` under "Safety discipline" prints all
  four members inline and types them: *"That is a path-and-text refusal, not an analysis of what an edit
  would do: it is the set of sites that carry the guard today."* `tests/README.md:519` enumerates the
  same four literals in the table row; the README's new "Declared bounds" section repeats the sentence;
  and the card's own **declared bound #4** (`CARD-260.md:247-248`) states it again, adding "stated as
  such in the module and the README." So the prose is a hand-written list over named sites, **labelled as
  such, filed under a bounds heading, and time-bounded with "today"**. There is no gap between claim and
  reach for ADR-0039/R2's honesty requirement to bite on — bound #4 discharges it.
- **The content is right, and more defensibly than the finding allowed.** ⚠ **This is where the skeptic
  refuted a leading inference I myself had put in its prompt, and which I had already written into the
  review summary above — I was wrong.** I offered `grep -c _refuse_unless_test_database
  tests/database_guard.py` = **0** and invited the conclusion that the set is not derived from where the
  guard lives. The answer: **`tests/database_guard.py` IS the guard's other half** — 125 lines, CARD-109,
  *"refuse to run the suite against a database nobody chose"* — carrying `verdict()`, `OPT_OUT`,
  `report_line()` and a `pytest_configure()` that raises `pytest.UsageError` (`:62, :99, :107, :119-125`),
  wired in at `tests/conftest.py:97,140`. **The guard has two independently-spelled halves and
  `_FORBIDDEN_PATHS` covers exactly both.** There is no third site: `pyproject.toml` has only
  `addopts = "-q"` with no `-p` wiring to subvert, and `tests/db_name.py` holds only name-derivation
  helpers with no `raise` and no `fail(`. My parenthetical in the summary above has been struck and
  corrected in place.
- **What survives, and it is carried forward as a Minor rather than discarded:** the claim is factually
  right that `test_kill_matrix.py:877-889` asserts exactly three refusals (two texts + `tests/conftest.py`)
  and that `grep -n database_guard tests/test_kill_matrix.py` returns **one** hit — the test's own *name*
  — never an `Edit(path=...)`. So **the second of the two forbidden paths has no control.** That is a
  one-line `pytest.raises` arm and a **Minor ADR-0039/R1 test-completeness nit** (every set member needs
  a control that can fail), *not* an Important R2 violation about a set misrepresented as derived.
- **And the skeptic closed the remedy trap I had asked it to weigh.** A "cheap equality control" that
  greps the tree for the guard's code sites **falls into the trap too**: the guard's two halves share no
  spelling, so any such grep is itself a hand-written pattern list and the fix reintroduces the defect one
  layer up. The honest cheap remedy is the single missing `Edit(path=Path("tests") / "database_guard.py")`
  arm at `:889`.
- **Incidental, and it is mild positive evidence for this card:** the skeptic's first `git status` in the
  CARD-260 worktree showed ` M tests/test_db_engine_lifecycle.py`, but `git diff --exit-code` returned
  **0** and the entry then cleared — mtime-only, content byte-identical. That is the fingerprint of the
  instrument's `cp -p` backup/restore on its anchor-2 target, i.e. independent evidence **the restore
  discipline holds**.

**[Adversarial] F-005 CONFIRMED (Critical) — and the skeptic showed F-001 and F-005 COMPOSE into a
single realistic failure, which neither finding states.**
- **`exit_code` is written and read by nothing.** Exhaustive grep of both names: `exit_code` is stored at
  `:890` and **never read anywhere in the module** — not in `figure()`, not in `table()`, not in
  `KillMatrix`. `collected_tests` is read exactly once, inside `Matrix.figure()`. Cross-checked against
  **every** `raise` in the file (20 sites): each is keyed on mutant text, selection paths, lineno
  collisions, backup digests or cell values. None touches either name. No `main`, no CLI, and `run()`
  calls only `_backup_registry`, `_measure`, `_refuse_unless_clean`, `_apply`, `_restore` — so there is
  no later consistency check either.
- **`_refuse_unless_clean` is vacuous on a blank reading.** It raises exactly twice: `if matrix.failed:`
  and on `moved` cells against a baseline. On an all-`NOT-REACHED` reading `matrix.failed == ()` and
  every cell equals an equally blank baseline. **Its own docstring explains why it cannot be stricter** —
  "a targeted selection legitimately leaves most of a file's asserts `NOT-REACHED`" — which is true, and
  is exactly the gap: **it has no way to tell "most" from "all".**
- **Reproduced**, with a control proving the selection was otherwise measurable. Dead node id:
  `0 PASS, 0 FAIL, 5 NOT-REACHED, 0 BLIND of 5 assertion nodes (collected tests: None)`, `exit_code: 4`,
  **no refusal**; with a real mutant added the whole grid stays blank and still passes the between-mutants
  baseline check. Control on `::test_add`, same target and mutant: `1 PASS, 2 FAIL, 2 NOT-REACHED`,
  `exit_code: 0`.
- **⚠ THE COMPOSITION — this is the finding that matters most on this card.** `full_suite_lock`'s
  `pytest_configure` raises `pytest.UsageError` on a foreign lock → pytest exits **4 before collection**,
  so no summary line and `collected_tests is None`. Meanwhile the instrument's own `_refuse_if_lock_held`
  reads `repo_root/meta/kanban/.full-suite.lock` while the hook reads `lock_path()` → the **main** repo
  root (**F-001**). **The two guards read different files**, so the instrument's door check passes and the
  child it spawns is refused. Demonstrated with `NONOGRAM_FULL_SUITE_LOCK` on a temp lock, using the
  selection the control had just proven yields `3 PASS`: `SHIPPED … 0 PASS, 0 FAIL, 5 NOT-REACHED …
  (collected tests: None)`, `exit_code: 4`, no refusal. **A legitimate selection, blanked by an external
  condition, published as `SHIPPED 0 FAIL`.** Not user error — and on this board a gate holding the real
  lock is an ordinary Tuesday.
- **"The printed caveat is enough" — judged insufficient, with the reason.** `(collected tests: None)`
  appears only on `Matrix.figure()`. The **aggregate headline a human quotes**, `KillMatrix.figure()`
  (`:552-558`) and the `table()` header built from it, reads: *"5 assertion nodes …; SHIPPED 0 FAIL"* —
  no exit code, no collected count. **`exit_code = 4` is printed by nothing at all**; the skeptic had to
  reach into the dataclass to see it.
- **The card's own README already names this hazard and guards the wrong half.**
  `tests/README.md:513`: *"a green run with a blank matrix is indistinguishable from a file that never
  ran"* — but only the *mutant* cause is guarded (`_refuse_shifting_mutant`), leaving the
  *pytest-never-ran* cause open. And `:518` claims "a selection it cannot resolve to one file is a
  failure, not a silent pass", which a resolvable file plus a dead node id defeats.
  `test_g1_an_empty_or_unresolvable_selection_is_refused:849` tests only `[]`, `"tests"` and `"."` —
  **file resolution, never node-id liveness.** No test in the 1216-line file covers a dead run.
- **Fix precondition, chosen with its false-positive cost measured — use `exit_code ∉ {0,1}`.** It is the
  only one of the three candidates that separates "pytest refused or could not run" (2 internal, 3 error,
  4 usage, 5 nothing collected) from "tests ran and some failed", and it has **no false-positive cost**:
  the recording pass always exits 0 (it suppresses `AssertionError`) and the reraising pass / a killed
  mutant legitimately exits 1 — both inside the allowed set. **`collected_tests` must stay print-only**:
  it is regex-scraped from pytest's `-q` summary (`_OUTCOME` at `:626`), so a pytest or plugin formatting
  change makes it `None` on a perfectly good run — a real false positive. **"SHIPPED recorded no execution
  at all" is the most honest but does have false positives**: a legitimately skipped test, asserts living
  in a helper, or (in the reraising pass) arms below a test that errors earlier all record nothing with
  nothing wrong. So: gate on the exit code, assert liveness as a secondary warning.
- `pytest tests/test_kill_matrix.py -q` → **42 passed**. The hole is open with a fully green suite.

**[Adversarial] F-004 CONFIRMED (Important, the skeptic argues "arguably Critical")** — six refutation
routes, all failed, with the load-bearing experiment run twice and repeated four more times.
- **The default is verbatim `child_instrumentation: bool = False`** (`:666`), and the overlay is gated on
  it at `:875-880` (`if pass_ is Pass.RECORDING and self.child_instrumentation:`) — exactly as the card
  declares.
- **Side by side on a throwaway child-spawning target, same mutant, recording pass:**

  | assert | flag=False | flag=True |
  |---|---|---|
  | `km_child_target.py:11` (executes only in the child) | **NOT-REACHED** | **FAIL** |
  | `km_child_target.py:20` (parent's returncode arm) | FAIL | BLIND |
  | BLIND count | 0 | 1 |

  `flag=False records: {20: (False,)}` vs `flag=True records: {20: (True,), 11: (False,)}`. Arm `:11` ran
  inside the child and its assertion was **false**; the default reports it `NOT-REACHED`. With the flag
  off the child is not instrumented, so no record is written for an in-child execution and
  `aggregate_any_red(())` returns `NOT_REACHED` (`:283-291`). **That is precisely the conflation the
  module's own docstring says the instrument exists to remove** — "a surviving mutant and a never-reached
  assert look identical".
- **No figure carries the flag.** `Matrix` does not even hold the field; `grep` finds 5 hits total — two
  docstrings, the field, and the two behavioural uses — and **zero inside any f-string**. `KillMatrix.table`
  appends `# domain: recording pass`, so the pass is carried unconditionally and **the overlay's domain is
  not**. So a recording-pass `0 BLIND` is ambiguous between "no blind arms" and "the overlay never ran" —
  which is the defect `Matrix.__post_init__` names in its **own refusal text** (`:486`): *"a figure that
  does not carry its domain is the defect this instrument exists to prevent."*
- **Route 6 is half true, and the half is the finding.** The bound's justification (`:652-663`, restated
  at `tests/README.md:559`) is *"With it off the child is pristine, propagation is intact, and those arms
  are measured for real."* True for the **parent's** returncode arm `:20`; for the arm executing **in the
  child** nothing is recorded at all.
- **⚠ Additional evidence the finding did not use — it reaches this card's flagship number.** AC-7's live
  anchor runs in **precisely the exempted state**: `test_kill_matrix.py:967` is
  `Runner(selection=[str(LOCK_GUARD_TEST)], repo_root=REPO)` with **no flag**, and
  `child_dependent_linenos` marks **7** of `tests/test_full_suite_lock.py`'s 130 arms. So the board's
  headline *"130 of 130 PASS and reached, zero NOT-REACHED"* is produced **with the overlay silently
  skipped over 7 marked arms, and nothing in the printed figure says so**. The number is **not corrupted
  today** — `test_full_suite_lock.py:925` selects one of its *own* tests into the child, so those arms
  also execute in the parent and record there — but that is **luck of the target, not a property the
  instrument guarantees**, and it is exactly the case the missing control would have pinned.
- **Severity reasoning, recorded as the skeptic gave it:** two things keep it from plainly Critical — the
  shipped anchors are not wrong today, and the flaw is confined to arms executing *only* in a child under
  RECORDING. Pushing toward Critical: a silently-wrong `NOT-REACHED` is the instrument's **core output**,
  it happens in the **default** configuration, and `tests/README.md:559` **positively advertises the
  flag-off mode as sound** rather than unsupported — so the "documented as unsupported → Minor" escape is
  unavailable; the documentation is itself the half-true claim.
- **Latent flake, flagged by the skeptic as an observation and not as evidence — worth a card bound.**
  One early run reported `:20 PASS` instead of `FAIL`, traced to **stale `__pycache__` in the child**: the
  mutant edit is byte-identical in length and can land in the same mtime second as the SHIPPED
  measurement. Not reproducible in 5 later attempts (and absent under `PYTHONDONTWRITEBYTECODE=1`). This
  is a real correctness hazard for an instrument whose output is a per-assertion verdict, and it is in
  this card's own files.

### [Severity gate 1/3] 4.0 < min_score 8 **and** 6 gating findings after verification — success path closed

critical: **3** (F-001, F-003, F-005) · important: **3** (F-002 — regraded from Critical by its skeptic;
F-004; F-011 **unverified**, beyond the 6-finding cap, gating anyway). **Dropped: 1 false positive
(F-006** → survives as a Minor one-line control). Adversarial verification changed the fix on **three** of
the five confirmations — F-002 needs two fixes not one, F-003's proposed fix is insufficient against the
reorder variant, and F-005 composes with F-001 — which is the whole reason this step runs even when the
score has already failed. → `forge:fix`, cycle 2 to follow.

### [Fix 1] FIX PRE-GATE: PASS — 11 of 11 findings addressed, every named test exists and passes

**Test half.** Ran **exactly** the 19 tests named across the `FIXED` lines: `25 passed, 35 deselected in
20.41s` (19 names → 25 node IDs). Whole file: **60 passed**, up from 42 at `f9718739` — **+18 new
controls**. Nothing bounces. Side evidence that the new G-3 controls are honest: after the run the real
`meta/kanban/.full-suite.lock` is **still absent** and `tests/conftest.py` is **byte-identical**, which is
what "the controls only *construct* an `Edit`, which raises before anything is written" looks like from
outside.
**Declarations half.** Every `FIXED` line carries a `DECLARATIONS` line. Spot-checked against the card
diff: bound **5** added (`UnmeasuredRun` / exit codes `{0,1}`), bound **6** added (keys re-derived from
the file that runs), bound **4** updated (`casefold`/`samefile` reach) and separately **confirmed**
unchanged for its set, bound **2** re-derived.
- **[Fix 1] declarations: 5 updated, 2 confirmed, 2 added, 0 none.**

**I verified the two load-bearing claims myself rather than taking them:**
- **F-001's fix closes the F-001×F-005 composition.** From inside the worktree,
  `km.board_lock_path()` and `full_suite_lock.lock_path()` both return
  `…/PythonProject4/meta/kanban/.full-suite.lock`, and the resolved path is **not** under this worktree.
  The door check and the child's `pytest_configure` hook now read the same file, so the instrument can no
  longer start and then spawn a child that gets refused. `repo_root` **lost a job** (3 → 2: relative
  selection and subprocess `cwd`), and the new control adds a **decoy** lock at
  `repo_root/meta/kanban/` that must *not* refuse — which is what reds if the jobs are ever conflated
  again. The old control provably could not fail; this one can.
- **F-002 used `casefold`, not the review's suggested `normcase` — and the agent was right to deviate.**
  `os.path.normcase` is the **identity on posix**, so the review's spelling would have fixed nothing on
  this volume. The comparison is now `realpath` → `casefold`-ed parts (so the mis-cased *directory*
  `TESTS/conftest.py` loses too) → `samefile` against the two guard files. **This is the second time in
  this cycle that a brief's suggested fix was wrong and the agent measured instead of complying.**

**⚠ FLAGGED FOR CYCLE 2's REVIEWER AND THE AC/EC/G GATE — G-4's control was widened, and it is not my
call to declare the guardrail satisfied.** Importing the lock's owner means the instrument is no longer
stdlib-only. Measured independently: `kill_matrix.py`'s non-stdlib import roots are now exactly
`{full_suite_lock, tests}` (two spellings of one sibling, because the suite imports the module as
`tests.kill_matrix` and the generated plugin imports it bare), and the control at
`test_kill_matrix.py:1433` holds them to an **equality** — `assert extra == {"tests", "full_suite_lock"}`
— so a third-party import still reds. What I can state: `pyproject.toml` is **untouched** in both the
branch diff and the working tree, so **G-4's binding claim — "No new runtime dependency (ADR-0006/R1)" —
still holds**; what changed is the *control's* reach, declared and pinned rather than silently widened.
What I am **not** stating: that this is therefore fine. G-4's parenthetical ("`ast`, `pathlib`,
`subprocess`, `hashlib` are stdlib") is now an incomplete description of the module, and the card's
`## Guardrails` section was — **correctly** — left untouched, because a guardrail is weakened only at the
decompose station and never from a worktree. The agent updated the guardrail *restatement* in the
worktree notes instead, which is the right surface. **Cycle 2 must judge whether a pinned sibling import
is inside G-4 as written, or whether G-4 needs a decompose-station amendment.**

**Two judgement calls the agent made and justified, both recorded because cycle 2 should test them, not
inherit them:**
- **F-004: it narrowed bound 2 rather than inventing a new cell state**, on the ground that the
  explicit-state route needs a set of "arms that may execute in the child", while
  `child_dependent_linenos` is a *position* rule for arms that **read** a spawn's result — and the
  fixture's in-child arm sits **above** the spawn, so it is not in that set (now asserted in the new
  control). It argues the only fail-closed superset — "every `NOT-REACHED` arm in a file that spawns
  anything" — would relabel the three arms AC-7's second anchor certifies, i.e. **break the card's own
  independent evidence**. Both figures now carry the flag, and the reporting-surface enumeration requires
  pass + denominator + exit code + flag in every `figure()`/`table()`.
- **F-003 runs the topology check unconditionally** rather than gated on `self.target in mutant.paths`,
  "because an edit reaching the target through another spelling is still an edit to it" — with the
  false-positive cost measured by a control where the mutant edits a different file and the reading
  publishes normally. The off-key refusal (`set(records) - set(linenos)`) is in `_measure` as a second
  net, and **F-011 was verified closed by that re-derivation rather than assumed** (the merge mutant is
  accepted by `apply_edit`, yields linenos `(8, 8)`, and the topology check refuses it).
- **The latent `__pycache__` flake was fixed, not declared:** `PYTHONDONTWRITEBYTECODE=1` in the child
  environment, with the mechanism written into the code comment, the README and the card.

**And the board's own guards caught the fix agent mid-work, which is worth recording as evidence the
anchors are live:** its first draft spelled `NONOGRAM_FULL_SUITE_LOCK` literally in `kill_matrix.py`'s
docstring, and **anchor 1 went red** at `tests/test_full_suite_lock.py:614`
(`test_nothing_in_the_tree_sets_either_of_the_guards_env_switches`, whose `OVERRIDE_NAMERS` is an
equality over three exact paths). Fixed by naming the constant `full_suite_lock.LOCK_PATH_VAR` instead of
copying its value. **The allowlist was not touched** — the guard was obeyed, not edited around.

**Noted, not fixed, correctly outside F-008's scope:** the `tempfile.mkdtemp` workdirs are never cleaned
up, and `test_kill_matrix.py`'s anchor mutates the real `src/nonogram/db/session.py` and
`tests/test_db_engine_lifecycle.py` in the working tree for the length of a measurement, so an abnormal
termination leaves them edited. Existing behaviour; recorded beside the F-008 note. **→ follow-up card.**

### [Build gate 3 — FAILED (attempt 1/2), post-fix] 23 reds, one cause, and the cause is F-001's own fix

Full suite, solo under the board lock: **23 failed, 8665 passed, 1 skipped, EXIT=1** in 947.40s (15:47).
Count reconciles: main 8629 + the card's **60** node IDs = 8689 = 23 + 8665 + 1, so nothing was lost.

**All 23 failures are in `tests/test_kill_matrix.py` and all 23 are the same error** — `LockHeld`, raised
from `kill_matrix.py:902`:

```
tests.kill_matrix.LockHeld: /Users/omelnikova/PycharmProjects/PythonProject4/meta/kanban/.full-suite.lock
exists: another worktree holds the board's full-suite lock. This instrument refuses to start and never
writes one
```

**This is not a flake and not an attribution puzzle — it is the direct, predictable consequence of the
F-001 fix, and the solo run could not have revealed it.** The same file passed **60/60** standing alone
twenty minutes earlier, because no lock was held then. Before the fix the instrument checked
`repo_root/meta/kanban/.full-suite.lock` — a per-worktree path **no gate ever writes** — so it never saw
a gate's lock and its tests always ran. After the fix it correctly resolves the board's one real lock
(verified: `km.board_lock_path() == full_suite_lock.lock_path()`). **And a full-suite gate run holds
exactly that lock for its whole duration.** So every test that actually drives the instrument now refuses
to start, inside the very gate that must certify it.

**The mechanism, from the code's own words.** `_refuse_if_lock_held`'s new docstring says it is
*"deliberately stricter than `full_suite_lock.verdict`, which the gates use: **any** lock refuses here,
with no staleness window and no [ownership check]."* `full_suite_lock` identifies a holder **by worktree**
and ignores a lock its own tree holds — that is CARD-255's whole design (`_same_tree`, "identity is the
worktree, not a pid"). The instrument discarded that half. "Stricter" turns out to mean **"cannot run
inside the gate that tests it"**, and the 23 tests that monkeypatch the override path pass while the 23
that use the real resolution fail.

**What this exposes about the contract, stated rather than quietly patched.** G-2 reads *"refuses to start
if `meta/kanban/.full-suite.lock` exists"* — and during any gate run it always exists. Taken literally, G-2
and "the instrument's own tests run inside the suite" cannot both hold. The honest reading is that G-2
means a **foreign** lock, which is what the board's own guard means by a lock and what the hazard is
(contention between *different* worktrees; a child pytest the instrument spawns inside its own worktree is
already serialised by being one process tree, and `full_suite_lock`'s hook in that child would resolve the
same tree and allow it).

**Routing: code defect, not a guardrail amendment.** → `/forge:fix` with the gate output, attempt **1 of
2** against `review.build_fix_attempts`, **not** counted as a review cycle. The fix is to apply the
owner's worktree-identity rule — refuse a foreign lock, ignore the instrument's own tree's — which
*preserves* F-001's intent (read the one file the gates write) instead of reverting it. Explicitly **not**
acceptable: making the 23 tests monkeypatch the lock path, which would return the real-path behaviour to
being untested and so recreate F-001's original sin, a control that cannot fail for the real path.

### [Build-fix 1/2] GATE-LOCKHELD closed — the owner's identity rule, not a weakened G-2

All 23 reds were one cause and the fix is one function call. `_refuse_if_lock_held` no longer asks "does a
lock exist at the path its owner resolves"; it asks the owner: `full_suite_lock.current_verdict()`, and
raises `LockHeld` only on a refusal. F-001's correction is **kept** — the path is still the one the gates
write, still resolved by `full_suite_lock` and still unmoved by `repo_root` — and what is dropped is the
half the fix had discarded with it, CARD-255's `_same_tree` ("identity is the worktree, not a pid";
"the guard must refuse a foreign lock and ignore its own").

**G-2 was read, not edited.** The card's `## Guardrails` section is byte-identical: G-2 says *"refuses to
start if `meta/kanban/.full-suite.lock` exists"*, and during any gate it always exists, so a literal
reading makes G-2 and "the instrument's own tests run in the suite" mutually exclusive. The reading taken
is that a lock means a **foreign** lock — which is what the board's own guard means by one and what the
hazard is. **No decompose-station amendment is needed and none was made**: the fix satisfies G-2 on the
only hazard G-2 names, rather than carving an exemption out of it.

**The staleness window and the override: a deliberate choice, stated.** Both arrive with
`current_verdict()` rather than being overruled locally. The instrument's refusal must be *the same
decision* that admitted the pytest process it is running inside — strictness beyond it reds a suite the
board decided to run (and a stale foreign lock would have reproduced these 23 reds in a second guise),
laxity below it would start a run whose child that same hook kills. One function, one answer, so the
agreement is structural and not two copies that happen to match. Neither relaxation is silent: the owner's
terminal-summary hook announces a stale lock walked past and an override used.

**Why own-tree is not a loophole.** The hazard G-2 guards is two *different* worktrees running heavy
pytest at once. A child pytest the instrument spawns inside its own tree is already serialised by being
one process tree, and `full_suite_lock`'s hook in that child resolves the same tree and allows it — so an
own-tree lock was never the hazard. The composition F-001 closed therefore stays closed: a **foreign**
lock still refuses the start, so the instrument can still never begin a run whose child the hook would
kill.

**Controls — the gate can catch a regression here.** The suggestion the brief explicitly ruled out
(monkeypatching the lock path in the 23 tests) was not taken; the real resolution stays under test.
- `test_g2_a_lock_this_worktree_holds_does_not_refuse_the_start` — **new**, and the one that reds if the
  strict rule is reinstated.
- `test_g2_the_refusal_is_its_owners_verdict_and_not_a_second_opinion` — **new**; four lock states
  (foreign / own / stale-foreign / override) with the instrument's answer asserted **equal to
  `current_verdict()`'s**, so a re-derived rule reds the way a re-derived path did as F-001.
- `test_g2_a_foreign_lock_refuses_the_start_and_repo_root_does_not_move_it` — the cycle-1 control,
  renamed and sharpened: the holder is now an **absolute** foreign path, so the refusal under test is the
  foreign-holder branch rather than the unanalysable-`worktree:` branch (which is kept as its own case).
  The **decoy** under `repo_root` still must not refuse, and the override is `delenv`-ed so the control
  cannot pass for the wrong reason.
- `test_g2_the_lock_it_watches_is_the_one_the_gates_write` — unchanged; `board_lock_path()` still
  asserted equal to `full_suite_lock.lock_path()`.

**Verified against the real condition, not a simulation of it.** The real lock was **absent**, so one was
planted at `/Users/…/PythonProject4/meta/kanban/.full-suite.lock` naming this worktree — what the gate
looks like from inside — and removed afterwards.
- `pytest tests/test_kill_matrix.py` with that lock held: **62 passed** (60 + 2 new controls). This is the
  exact configuration that produced 23 reds.
- Same file with no lock at all: **62 passed**.
- F-001's behaviour still live for the **real** path: with that same real file rewritten to name a foreign
  worktree, a direct `Runner(...)` **refuses** with `LockHeld` naming
  `…/PythonProject4/meta/kanban/.full-suite.lock`, and `km.board_lock_path() == lock_path()` is `True`
  while `this_worktree()` is the card worktree. The file was restored from a `cp -p` copy immediately.
- Guard neighbours re-run with the lock held, including anchor 1 and the tree-wide env-switch scan:
  `test_full_suite_lock` + `test_guard_integrity` + `test_naming` + `test_suite_profile` — **611 passed**.
- No timing measurement was taken anywhere (G-6); the new controls use a fixed past date and the lock
  file's own mtime instead of reading a clock.

### [Fix 2 / build-fix 1-of-2] FIX PRE-GATE: PASS — GATE-LOCKHELD closed by asking the owner, not by re-deriving it

**The fix is one function call.** `_refuse_if_lock_held` (`kill_matrix.py:906`) no longer asks "does a
lock exist at the path its owner resolves"; it asks the owner: `allowed, said =
full_suite_lock.current_verdict()`, refusing only when `allowed` is false and quoting the owner's own
`said`. **F-001 is preserved rather than reverted** — the path is still the one the gates write, still
resolved by `full_suite_lock`, still unmoved by `repo_root`; what was restored is the half the F-001 fix
had discarded along with the broken path, CARD-255's `_same_tree` identity rule. No test was made to
monkeypatch the lock path.

**I verified both directions myself, under the real condition, without touching the shared lock.** Using
`NONOGRAM_FULL_SUITE_LOCK` on a temp file (per-process, so CARD-258's live cycle-2 reviewer could not be
refused by a lock I planted — the hazard this card is about, avoided while testing this card):
- **Own-tree lock held — the exact configuration that produced the 23 reds:** the 4 named tests pass, and
  the **whole file is 62 passed** (60 + 2 new controls). Previously: 23 `LockHeld` failures.
- **No lock:** the 4 named tests pass.
- **Foreign lock (naming `…-card-999`):** `current_verdict()` → `allowed=False`, and a direct
  `Runner(...)` **raises `LockHeld`**. So **F-001 did not regress** — the inertness it fixed has not come
  back, and the F-001×F-005 composition stays closed, because a foreign lock still refuses the start and
  the instrument can still never begin a run whose child the hook would kill.
- CARD-256's own announcement fired correctly in every overridden run (*"reading the lock from … not the
  board's own … NONOGRAM_FULL_SUITE_LOCK is set"*), which is the loudness that card added — the override
  changed a verdict and said so.
- The shared `meta/kanban/.full-suite.lock` was **absent before and after** every probe.

**Declarations half.** `DECLARATIONS` line present; **bound 7 added** and confirmed real in the card diff
(`7. **The lock refusal is worktree identity, and the verdict is its owner's — whole.**`), with the
README's "Declared bounds" and refusal-table row updated and four docstrings re-derived.

**The staleness/override choice, which I asked for explicitly and got.** The agent took the owner's
verdict **whole**, staleness window and override included, rather than staying strict on a foreign lock
regardless of age — reasoning written into the code, the README and the card: this code runs *inside* a
pytest the owner's `pytest_configure` has already admitted, so strictness beyond that verdict would red a
suite the board deliberately decided to run (a foreign lock past `STALE_SECONDS`, whose holder the board
presumes gone, **would have reproduced these same 23 reds in a second guise**), while laxity below it
would start a run whose child that same hook kills. One function, one answer — so the agreement is
structural, not two copies that happen to match today.

**G-2: read, not weakened — and I checked rather than accepting the claim.** `git diff` on the card shows
**no `- G-N` row changed**: the `## Guardrails` section is byte-identical. G-2 is satisfied on the only
hazard it names, contention between *different* worktrees; an own-tree lock was never that hazard, since
a child pytest spawned inside the instrument's own tree is already serialised by being one process tree
and that child's hook resolves the same tree. **No decompose-station amendment is required**, so the
earlier flag on this point is resolved — but note this is the *second* guardrail-reading question this
card has raised (G-4's widened control is still open for cycle 2 to judge).

**Four controls, each able to fail:** a lock this worktree holds does **not** refuse (the control that
reds if the strict rule is reinstated); the instrument's answer asserted **equal to `current_verdict()`'s**
across four lock states (foreign / own / stale-foreign / override), so a re-derived *rule* reds the way a
re-derived *path* did as F-001; cycle-1's foreign-lock control sharpened to use an **absolute** foreign
path with the override `delenv`-ed so it cannot pass for the wrong reason, keeping the **decoy** under
`repo_root` that must not refuse; and `board_lock_path() == full_suite_lock.lock_path()` still asserted.

**Also worth recording:** the agent's guard-neighbour run with the lock held — `test_full_suite_lock` +
`test_guard_integrity` + `test_naming` + `test_suite_profile` + `test_kill_matrix` — was **673 passed**,
and it added no env-var literal to `kill_matrix.py`, so `OVERRIDE_NAMERS`' three-path equality (which
caught its first draft) stays green. Build gate 4 is **held until CARD-258's cycle-2 reviewer finishes**:
a full suite would take the board lock and refuse that reviewer's targeted runs, manufacturing exactly
the false red this card exists to diagnose.

### [Build gate 4 — PASSED, post-build-fix] The 23 LockHeld reds are gone, under the real condition

Full suite, solo under the board lock: **8690 passed, 1 skipped, 0 failed, EXIT=0** in 968.96s (16:08).
**Count reconciles exactly:** main 8629 + the card's **62** node IDs = 8691 = 8690 + 1 skipped, and 62 is
the figure the file reports standing alone — so the gate and the card agree. The one skip is the
long-standing `setrlimit(RLIMIT_AS)` platform skip.

**This is the gate that previously produced 23 `LockHeld` failures, and it is the first time the
worktree-identity fix has faced the real condition rather than a simulated one.** The gate wrapper holds
the board's actual lock at `meta/kanban/.full-suite.lock`, naming this worktree, for the entire run —
precisely the configuration that failed. The instrument now reads that lock through
`full_suite_lock.current_verdict()`, recognises the holder as its own tree, and proceeds; both AC-7
anchors, which spawn real child pytest runs, passed inside it. Nothing was simulated and no override was
set: `NONOGRAM_FULL_SUITE_LOCK` was **not** used for this gate. → review cycle 2.

### [Review 2/3] Score: 7.5 (4.0 → 7.5, Δ+3.5) — all 4 Criticals closed; 2 new Important

Report: `meta/review/20261021T085747Z-CARD-260-cycle2.yml` — 6 findings (2 high / 2 low / 2 info), 5
system-contract verdicts. **[Review sync]** 1 report → `meta/review/`. Score clears `min_improvement`
easily but not `min_score: 8`, and two Important close the severity gate either way.

**Step 8h: 5 rules checked — 2 ✓ holds, 1 ⚠ unchecked (`no_eligible_fact`: ADR-0038/R8, which would need
the browser tier this review was told not to run), 2 ✗ violated (ADR-0039/R1, R2).** **ADR-0039/R3 now
✓ holds**, having been violated in cycle 1: every exemption carries a both-sided control — G-4's sibling
held to an equality, G-2's own-tree exemption controlled by what it must **not** absorb (foreign lock plus
a `repo_root` decoy that must not refuse) and by four lock states each asserted equal to
`current_verdict()`'s own answer, G-3's set held to 7 spellings including a mis-cased directory, G-5's
`sys.executable` as the only non-literal argv[0], and bound 1's unseen region with its own failing control.

**All four Criticals and F-011 are genuinely closed, several corroborated by gate 4 under the real
condition.** F-001 ✓ both halves, and the agreement is **structural, not coincidental** — the control
drives foreign/own/stale-foreign/override and asserts `instrument_allowed is owner_allowed` each time.
F-002 ✓ with the directory case explicitly parametrised, and the reviewer confirms the agent was right to
use `casefold` over the review's own `normcase` suggestion, which is the identity on posix. F-003 ✓ with
the reorder case genuinely caught — and the swap test asserts `assert_linenos(swapped) ==
assert_linenos(pristine)` **before** expecting the refusal, so it certifies the stronger check rather than
the weaker one. F-005 ✓ with no legitimate run refused. **F-011 ✓ verified not assumed** — the merge test
asserts `apply_edit` *accepts* the mutant and yields `len(set(linenos))==1, len==2` before the topology
check refuses it, so the control can fail; this finding never got a skeptic in cycle 1 and has now been
properly closed.

**Both open questions I was carrying are ANSWERED, and neither needs a decompose escalation:**
- **G-4: a pinned sibling import is inside G-4 as written.** G-4's binding claim is ADR-0006/R1, which is
  about pyproject's declared runtime deps — untouched in both halves of the diff; `full_suite_lock` is
  in-repo dev-only test code; the allowance is pinned by equality so a third party reds. And the
  reviewer found the parenthetical was **already imprecise at decompose time**: it names `hashlib`, which
  the instrument deliberately does not import (cycle-1 F-009 removed that same false claim from the module
  docstring). It reads as illustration, not an allowlist. → **info F-205**, an optional one-line decompose
  wording refresh. **Not a code finding, not a blocker.** My earlier flag is resolved.
- **G-2 is read correctly in substance, not weakened in practice.** The verdict is not re-assembled, so the
  instrument is neither stricter nor laxer than the hook that admitted its own pytest; "never writes a
  lock" holds outright; and the strict reading is *measurably* unrunnable inside the gate that certifies it
  (23 reds, then 8690 passed with the real lock held). What remains is that the card's `## Guardrails` text
  now describes a stricter rule than the code, with the real rule carried in bound 7 → **info F-206**, a
  one-line decompose edit at the next touch.

**The two new Important findings — both land on boundaries the cycle-1 fix itself declared:**

- **F-201 — `tests/README.md:598` — bound 2's justification for declaring rather than mechanising the
  flag-off blind region is FALSE as measured.** This is **the exact argument I flagged for this cycle to
  test**, and it did not survive. The parenthetical claims the one fail-closed alternative would "relabel
  the three arms AC-7's second anchor reproduces". **I re-derived the core measurement myself before
  accepting it:** `child_dependent_linenos` returns **0 of 47** asserts for
  `tests/test_db_engine_lifecycle.py` (anchor 2's target) and **7 of 130** for
  `tests/test_full_suite_lock.py` (anchor 1). So anchor 2's target contains **no spawn-shaped call at
  all** — the rejected rule's precondition is false there and it would relabel **nothing** — while anchor
  1 has 7 child-dependent arms but **zero** NOT-REACHED arms, so there is nothing to relabel there either.
  The bound's *reading* is correctly measured and both figures do carry the flag; the defect is an
  unfalsified, false justification sitting inside a "Declared bounds" list that advertises five of seven
  as measured.
- **F-202 — `tests/kill_matrix.py:1222` — a mutant pytest killed outside any assert publishes a FAIL-free,
  all-`NOT-REACHED` matrix at exit 1, inside the admitted set.** F-005's fix gates `exit ∉ {0,1}` on the
  stated ground that such a run's matrix is "all-NOT-REACHED and FAIL-free, exactly the shape of a mutant
  every arm survived" — **and exit 1 produces that identical shape with no cross-check.** Measured:
  `0 PASS, 0 FAIL, 2 NOT-REACHED, 0 BLIND of 2 assertion nodes (collected tests: 1; pytest exit 1)`.
  A consumer counting kills as FAIL cells — **which is CARD-259, this card's own dependent** — reads
  "survivor", which is trap 1's recorded cost. Worse, the same shape is accepted **for SHIPPED**, where
  `_refuse_unless_clean` has no baseline on the first reading, so a fixture-errored SHIPPED becomes an
  all-`NOT-REACHED` baseline that `shipped_between` then compares against vacuously. The reviewer states
  the honest mitigation so the finding stays refutable — the figures do print `pytest exit 1` and the
  reached count — but notes F-005's fix **explicitly rejected that standard** ("`exit_code` was stored and
  read by nothing"). Proposed cross-check (`exit_code == 1` with no FAIL cell is always an unattributed
  failure) **fires nowhere in the 62-test suite nor on either anchor**, so its false-positive cost on this
  card's own evidence is zero.

**Mutation check correctly `deferred(cost)` again** — gating findings present, so the cost ladder holds it
for the stable cycle. No file under review was mutated by this review; digests unchanged start to finish.

**One Minor worth surfacing because it is measured and cumulative:** `Runner.workdir` leaks a machine-wide
temp directory per Runner with no cleanup — **519 `kill-matrix-*` directories** after gate 4 plus one file
run, oldest 2026-10-20 20:11. The reviewer checked and cleared the obvious interaction:
`test_web_upload.py`'s sweep globs only `nonogram-upload-*`, so this is housekeeping, not a flake risk.

**[Adversarial] F-201 CONFIRMED — verified inline by the orchestrator, because the decisive test is a
census I could run myself.** `[Inline fallback] F-201 verification`. Bound 2's justification reads,
verbatim (`tests/README.md`): *"The one fail-closed set that would contain it, 'every `NOT-REACHED` arm in
a file that spawns anything', would relabel the three arms AC-7's second anchor reproduces as
`NOT-REACHED` for a parent-side error, breaking the card's own independent evidence."*

My own AST census of anchor 2's target, `tests/test_db_engine_lifecycle.py`:
```
subprocess-shaped CALL nodes: []        child_dependent_linenos: []
textual occurrences of "subprocess": 1  (not a call node — i.e. a comment)
```
and for anchor 1, `tests/test_full_suite_lock.py`: **7 child-dependent arms of 130** asserts, with the
card's own figure recording **zero** NOT-REACHED arms there.

**So the justification is false in both anchors at once.** Anchor 2's target does not "spawn anything" —
the rejected rule's precondition is unsatisfied, so it would relabel **nothing**, including the three
NAMES-BLIND arms the justification names. Anchor 1 does spawn, but has no NOT-REACHED arm for the rule to
relabel. The only reading under which the sentence is true is "every run spawns, because the instrument
spawns the child" — under which the rejected rule is a straw man and the words "in a file" are doing no
work. Either way the claim does not hold as written.

**What this does and does not impugn.** Bound 2's *reading* is correctly measured and both figures do
carry the flag — F-004's mechanism half is sound and is not in question. The defect is a **false,
unfalsified justification inside a "Declared bounds" list that advertises five of its seven entries as
measured** — which is this card's own discipline turned on its own prose, and is why it gates despite
costing nothing at runtime. Note the asymmetry worth keeping: the fix the justification was rejecting
("carry 'target contains a spawn-shaped call', derived from the module's existing `_SPAWN`, beside the
flag in `figure()`") **relabels no cell**, so bound 2's own cost argument does not apply to it.

**[Adversarial] F-202 CONFIRMED — and the skeptic DISPROVED the proposed fix, which is the more valuable
half of this verdict.**

**The finding reproduces exactly.** An error-before-assert mutant (equal line count, target topology
untouched) published, unrefused and unflagged:
`0 PASS, 0 FAIL, 2 NOT-REACHED, 0 BLIND of 2 assertion nodes (collected tests: 1; pytest exit 1)`,
`exit_code: 1 · failed: () · records: {}`. The control in the same run proves the instrument was working
(`MARK-ROT` → `1 PASS, 1 FAIL`, `failed: (7,)`). The SHIPPED half reproduces too: a fixture-errored
pristine run passed `_refuse_unless_clean(shipped, None, …)` — which tests only `matrix.failed` and
returns before any cell comparison when `baseline is None` — and became a **blank baseline** against which
every mutant "survived" every arm. And nothing downstream cross-checks: across 1326 lines, `exit_code` is
read by the one gate at `:1222` and **two f-strings**; `matrix.failed` is read outside figures in exactly
one place, for SHIPPED only.
**Link 2 is worse than the finding said.** The per-`Matrix` figure does print `pytest exit 1`, but the
**aggregate** `KillMatrix.figure()`/`table()` that a consumer actually reads carries **only SHIPPED's**
exit code — so the caveat never reaches the reader, and the grid shows a column of `NOT-REACHED`
indistinguishable from the ones a targeted selection legitimately produces.

**⚠ THE PROPOSED FIX IS UNSAFE, and I re-derived the counter-example myself rather than taking it.**
The review's cross-check — *"`exit_code == 1` with no FAIL cell is always an unattributed failure"* — was
claimed to have zero false-positive cost. The skeptic instrumented `_measure` from an **external** plugin
(no edit to the file under review) across the whole 62-test suite: 68 published readings, exit histogram
`{0: 64, 1: 4}`, **0 would-flag** — so the claim is literally true *on this card's corpus*. Then it built
a target whose kill is expressed through `pytest.raises` instead of a bare assert. My own run of that
shape:

```
SHIPPED            exit=0  failed=()  passed=(9,)   WOULD-FLAG=False
RAISE-WRONG-TYPE   exit=1  failed=()  passed=(9,)   WOULD-FLAG=True     <-- a GENUINE, correctly-detected kill
```

`RAISE-WRONG-TYPE` (`ValueError` → `TypeError`) is a real kill the instrument detected correctly, and the
proposed predicate **refuses it** — note the cell reads **PASS**, not `NOT-REACHED`, on a run pytest
killed, so this shape *strengthens* link 2 while refuting the fix. The signature `exit 1 ∧ no FAIL`
conflates two different things that the recording/re-raising split does **not** separate: an
**unattributed failure** (the finding's case — nothing reached, the matrix accounts for nothing) and an
**out-of-domain kill** (a perfectly good reading whose kill was expressed by `pytest.raises`,
`pytest.fail`, a `unittest` assertion, or an assert in a helper). Had I sent the review's fix direction to
the fix agent, it would have shipped a refusal that breaks every target whose tests are not
assert-shaped — and `UnmeasuredRun` propagates out of `run()`, so **one** out-of-domain kill would destroy
the readings of every other mutant in the same run, refusing hardest exactly where the target needs the
instrument most. It also mislabels: `UnmeasuredRun`'s own docstring says "the run itself never happened",
and this run happened.

### [Family] streak 1 of 2 for CARD-260 — named, and it decided the fix shape

**The sentence: _each fix declares a boundary, and the next cycle finds a shape inside it._** Cycle 2's
two gating findings both land on boundaries the cycle-1 fix itself declared — F-201 on bound 2's narrowing,
F-202 on the exit-code precondition that fix introduced. Streak **1**; threshold is 2; **cycle 3 is the
last**, so another finding of this shape escalates.

**The skeptic connected that to the fix choice, which is the insight I most wanted and did not have:** a
refusal keyed on `exit 1 ∧ no FAIL` is *the same move* as the fail-closed set bound 2 already rejected — a
position/shape rule standing in for a cause it cannot observe. **A third such predicate is the likeliest
of all the options to produce the cycle-3 finding that escalates this card.**

### Cycle-3 fix shape for F-202: a SHRINKAGE of the proposed fix, in three parts

1. **SHIPPED needs no new gate — tighten the existing one.** Add `reached == 0` to
   `_refuse_unless_clean`, which already *is* the SHIPPED gate and already owns "SHIPPED must be
   trustworthy". A SHIPPED that reached nothing is not a baseline whatever its exit code, and that
   quantity is **already printed by its own aggregate figure** (`0 FAIL of 0 reached`). It cannot
   false-positive: a SHIPPED reaching no arm has no baseline to be.
2. **Carry each mutant's `exit_code` and reached count into `KillMatrix.figure()`/`table()`.** Not new
   mechanism — it is the module's own stated rule (*"a figure that does not carry its domain is the defect
   this instrument exists to prevent"*) applied to the one figure that currently does not. A reader then
   distinguishes `ERROR-BEFORE-ASSERT: 0 reached, exit 1` from `RAISE-WRONG-TYPE: 1 PASS, exit 1` from a
   true survivor, **with no predicate that can be wrong about which cause it was**.
3. **Declare the bound** in `tests/README.md`'s "Declared bounds": the matrix's domain is `ast.Assert`
   nodes, so a failure expressed any other way is a real kill **no cell can account for**, and `exit 1`
   with no `FAIL` cell means "pytest failed this selection for a reason outside the matrix's domain",
   never "every arm survived". **This was the only one of the instrument's boundaries not written down,
   which is why the shape was findable at all.** If only one part lands, it is this one: zero
   false-positive risk, and the only part that cannot itself become the next finding.

### [Fix 3] FIX PRE-GATE: PASS — all three F-202 parts landed, and F-201 took the route that adds nothing

**Test half.** The 5 named tests pass (5 node IDs, 61 deselected). Whole file **66 passed**, up from 62 —
**+4 new controls**. `## Guardrails` byte-identical again (`git diff` shows no `- G-N` row), and all the
orchestrator markers survive.
**Declarations half.** Every `FIXED` line carries a `DECLARATIONS` line; bound **2** re-derived, bound
**5** extended, bound **8** added, and the section heading's own count corrected **seven → eight** and
**"five" → "six measured"** — i.e. the fix updated the *count of its own measured claims*, which is the
discipline this card exists to enforce applied to itself.

**F-201 — it chose route (a) and gave the right reason, which is the reason I wrote the brief.** No new
mechanism: the false parenthetical is gone, replaced by what is measured. Its stated ground is that **(b)
would have added a second carried term to `figure()` in the same cycle as F-202 part 2 already adds one —
more surface for exactly the family's shape, for a term that decides nothing.** It re-derived my census
independently before writing it (anchor 2: 47 asserts, **0 spawn-shaped calls**, `child_dependent_linenos
== frozenset()`; anchor 1: 130 asserts, spawns at 4 sites, 7 child-dependent arms, 130/130 reached), and
it replaced the justification with an honest reason **derived from the code rather than from the
anchors**: the rejected set is a *coarser position rule*, and since a targeted selection legitimately
leaves most asserts `NOT-REACHED` — the premise `_refuse_unless_clean` already states — it would relabel
every arm the selection never ran. Position standing in for a cause, which is the same move bound 8 now
refuses for `exit 1`.
**And it noticed its own census was an uncontrolled claim.** It added
`test_ac3_the_rejected_fail_closed_set_would_relabel_nothing_on_either_anchor` in bound 1's shape, with
the message *"re-derive the bound rather than the expectation"* — because without it bound 2 would again
be an unfalsified sentence in a list advertising its entries as measured. **That is the family's lesson
applied to the fix for the family, unprompted.**

**F-202 — all three parts, in the priority order given, and nothing more.**
1. `_refuse_unless_clean` gained **one** condition, `reached == 0` (`denominator - len(not_reached)`), on
   both call sites. No new exception, no new outcome, no exit-code predicate — **and the refusal message
   states the exit code it deliberately did not key on.** Reproduced-then-refused by its own test.
2. `KillMatrix.figure()` now carries `per mutant: <NAME> exit <N> with <M> reached and <K> FAIL`, so
   `table()` carries it too (its header *is* that sentence). **Demonstrated by two mutants whose columns
   are cell-for-cell identical** — `MESSAGE-ROT` (true survivor, exit 0) and `RAISE-WRONG-TYPE` (a genuine
   `pytest.raises` kill, exit 1, no FAIL cell) — where the figure is the **only** place they differ.
   Neither is refused, which is the point.
3. The bound is written down in the README's "Declared bounds" and card bound 8, with bound 5 now stating
   what exit 1 does **not** establish. **No fifth cell outcome and nothing raises on `exit 1 ∧ no FAIL`.**

**F-203 measured to zero rather than asserted:** temp-dir growth across a whole file run is now **548
before, 548 after**, and it explicitly **did not delete the pre-existing 548** because another agent's
gate could own one — the restraint matters more than the cleanup. The tree is kept when a restore does not
verify, and the exception then names the directory, because the backup is the only intact copy there.

**Two more stale claims it found and handled differently, correctly:**
- The module docstring named `test_g4_the_instrument_imports_stdlib_only`, **a test renamed in cycle 1 that
  no longer exists** — corrected to the real name. (`shutil` was added for `rmtree` and declared; G-4's
  `extra == {"tests","full_suite_lock"}` census is unaffected.)
- The implementation record's prose-to-mechanism ratios (`0.48 : 1`, `0.36 : 1`) **it could not
  reproduce** — its own reconstruction gives 1.06 / 0.57, i.e. a different method, and the record never
  states the method. It **annotated them as "as measured at `f9718739`" and flagged the gap instead of
  inventing a number.** That is the right call: a figure whose method is unstated cannot be re-derived, and
  silently replacing it with a second unstated method would have been worse than leaving it labelled.

### [Build gate 5 — PASSED, post cycle-2 fix] and an interop check main's movement made necessary

Full suite, solo under the board lock: **8694 passed, 1 skipped, 0 failed, EXIT=0** in 1242.36s (20:42).
Count reconciles: main(old base) 8629 + the card's **66** node IDs = 8695 = 8694 + 1 skipped.

**⚠ But gate 5 certified a tree that is no longer what will ship, and I checked rather than assumed.**
CARD-258 merged as `4584caf4` while this card was in its fix round, so `main` moved to `50fdb165` while
this branch's merge-base stayed at `02e0f691`. What landed is **not** inert for this card:
`tests/conftest.py` **+15/−1** (registering a new always-on plugin), a new
`tests/helpers/undefined_table_report.py` (**735 lines**, loaded in *every* pytest session — including the
**child pytests this instrument spawns**), and `src/nonogram/db/session.py` **+69/−1** — which is
**AC-7 anchor 2's own mutation target**, whose 14 mutants are derived from that file's text.

**Rebasing now would be wrong** (two rounds of fixes are uncommitted; the procedure commits on a passing
cycle and `done` rebases the committed branch — my attempt aborted cleanly and the autostash restored
everything, verified). So I tested the interaction **without** disturbing the card: a throwaway detached
worktree at `main`, with this card's three in-flight files copied on top, `NONOGRAM_FULL_SUITE_LOCK`
pointed at a nonexistent scratch path and **no `DATABASE_URL`** so no database was created.

- `tests/test_kill_matrix.py` in the **both-cards** tree → **66 passed**.
- **Both AC-7 anchors reproduce**: `test_ac7_the_lock_guard_file_reproduces_130_of_130_pass_and_reached`
  and `test_ac7_the_four_arm_grid_of_card_257_reproduces` → **2 passed**. So anchor 2's 14 mutants still
  apply to the **changed** `session.py`, which was the one genuine risk.
- `git status` over `src/` and `tests/test_db_engine_lifecycle.py` in that tree afterwards: **empty** —
  the instrument restored both mutation targets byte-identically even on the new file content.
- Guard neighbours (`test_full_suite_lock`, `test_guard_integrity`, `test_suite_profile`, `test_naming`)
  → **611 passed**.
- Throwaway worktree removed; `PycharmProjects` holds only the repo and this card's worktree.

**So cycle 3's evidence will survive the rebase**, and that is now measured rather than hoped. The
merge gate at `done` remains the authority on the merged tree.

### [Scope gate] cycle 3: IN_SCOPE

`excess` = 0 — the three changed files are the card's `Touches` exactly, unchanged across three fix
rounds. `comp_spread` skipped (no `## Architecture context`). `poached` empty. `guardrail_hits` skipped
(G-1…G-6 are behavioral; none names a forbidden path). **[System contract]** re-checked at cycle entry:
the lens still projects 10 and the card still carries the 5 `meta/kanban/curation.md` selects — no ids
added, none removed.
**[Round counter]** 2 prior `[Review N/3]` entries; cycle 3 makes **3**, against a fatigue threshold of
2 × `max_cycles` = **6**. No fatigue escalation.

### [Review 3/3] Score: 8.5 (7.5 → 8.5, Δ+1.0) — one Important stands, and cycle 3 is the last

Report: `meta/review/20261021T131926Z-CARD-260-cycle3.yml` — 4 findings (1 high / 3 low), 5
system-contract verdicts. **[Review sync]** 1 report → `meta/review/`.

**Step 8h: 3 ✓ holds, 1 ⚠ unchecked, 1 ✗ violated.** ADR-0039/**R2 and R3 now ✓**, both having been
violated in cycle 1 — and R2 is closed *the way R2's own second clause prescribes*: the shape is
**analysed and carried** rather than silently passed, deny is applied at the one position that cannot be
wrong (`reached == 0`), and the residue is a named R3 exemption. ADR-0038/R8 repeats cycle 2's
`⚠ unchecked — no_eligible_fact` with the **same typed reason, deliberately not upgraded** without the
browser tier. **ADR-0039/R1 ✗ — but on a new and different ground**: cycle 2's R1 violation (bound 2's
false justification) is resolved; this is the off-key refusal.

**All of cycle 2's findings resolved, each re-derived.** F-201 ✓ — the reviewer re-ran both census halves
itself (anchor 2: 202 Call nodes, **0** matching `_SPAWN`) and confirmed the control **can fail** (M8 kills
it). F-202 ✓ all three parts — and it tested the thing I most wanted tested: it **constructed the two
candidate "legitimate" shapes** for part 1 (a node-id selection whose test owns no `ast.Assert`; a flag-off
target whose arms run only in the child) and found both are *precisely the useless baseline the gate
describes*, so **part 1 cannot false-positive**. Part 3's bound matches the code: exit 1 ∈
`_RAN_EXIT_CODES`, no predicate on `exit 1 ∧ no FAIL` anywhere, cell vocabulary unchanged. F-203 ✓
independently re-derived (**549 temp dirs before a clean run, 549 after**). F-204 ✓. F-205/F-206 not
re-raised. The prose-to-mechanism annotation judged **honest handling** — "labelling a figure whose method
is unstated beats substituting a second unstated method".

**Mutation check RAN at last** — deferred twice by the cost ladder, executed here on stable code:
**10 mutants, 8 killed, 1 survived-equivalent** (re-derived before being classified as equivalent, not
assumed), **1 survived → F-301**. Restore verified by `shasum` after **every** mutant, pre/post digest of
`kill_matrix.py` identical, `git diff --stat` byte-identical. *On a card whose entire subject is whether an
assertion can fail, this is the check that had to run — and it is what found the gating finding.*

**F-301 — Important — `tests/kill_matrix.py:1341` — the off-key refusal has no control that can fail.**
**I verified this myself rather than taking it.** Forcing `off_key = []` so the refusal can never fire
leaves **all 66 tests green** (restore verified byte-identical, `2a20d4f9…`). `tests/README.md:523`
publishes it to a consumer as a refusal the instrument performs.
**And the near-miss is what makes it sharp:** `test_ac1_the_planted_shifting_mutant_runs_green_and_reports_nothing`
constructs **exactly** the off-key condition (`assert not set(records) & set(linenos)`) and then **routes
around `_measure`**, calling `_pytest` and re-aggregating by hand — so R1's "missed WITHOUT" half exists
and the "caught WITH" half does not.
*One correction to the finding's wording, checked:* it says the message fragments "appear nowhere in the
test file", but `grep -c 'no cell for'` returns **1**. That occurrence is fixture **prose** —
`OUT_OF_DOMAIN_TARGET`'s own docstring — not a `pytest.raises(match=…)`. The substance holds; the phrasing
was loose, and the distinction is exactly the kind this card exists to police.

### [Family] streak STAYS 1 — the trigger does NOT fire, and the attribution is mechanical

**I re-derived the attribution myself:** `git show HEAD:tests/kill_matrix.py | grep -c off_key` → **0**;
working tree → **3**. So F-301's code is new in a fix round — but in the **cycle-1** fix (it was F-003's
"cheap second net", which my own cycle-1 brief asked for by name), **not** the cycle-2 fix. F-302 and
F-303 are present at HEAD (original implementation). F-304 **is** new in the cycle-2 fix — and it is
**Minor and non-gating**, so it is not "a gating finding attributable to the cycle-2 fix". The trigger
requires both.

**The reviewer's framing is better than mine and I am adopting it: this is _one cycle late, not one more
turn of the family_.** Cycle 3 found a shape inside a boundary the **cycle-1** fix declared, which **cycle
2 reviewed and endorsed without checking it had a control** — and so did I: my own `[Review 2/3]` note
records "the off-key refusal … is in `_measure` as a second net" approvingly, as an existence claim, which
is the precise error this family is about. That is a **review-coverage observation about cycle 2**, not a
new instance of the loop, and it would have been wrong to bank it as streak 2.

### [Review max/max] Score: 8.5 ⚠ max cycles reached — ESCALATED, changes NOT committed

Severity gate closed by one standing Important at cycle 3 of 3. Per the procedure the fixes stay
**uncommitted** and the worktree is **kept**; the owner decides.

**Routed to station: implementation** (code defect — the requirement, the card and the slice are all
sound; a control is missing). **Not** architect (no AC is unclear), **not** decompose (the scope held at
exactly three files across three fix rounds), **not** the family trigger.

**The remedy is one test, in a fixture that already exists, in a file the card already owns.** In
`test_ac1_the_planted_shifting_mutant_runs_green_and_reports_nothing`, after the existing `_pytest` block,
call `runner._measure("SHIFTED", Pass.RECORDING, len(linenos), pristine)` inside
`pytest.raises(MutantRefused, match="no cell for")` — the off-key condition is **already constructed
there**. The alternative is to delete the refusal and let the topology check own the claim. Either closes
F-301, and F-302 (two more uncontrolled refusals, both present at HEAD) folds into the same pass.

**[Escalated]** 2026-10-21 — station: **implementation** · max cycles reached (3/3), score 8.5, one
Important (F-301). Route: **add the one missing control, then `/forge:kanban review CARD-260`** — NOT
`redo`. A clean-slate redo would discard three fix rounds that closed four Criticals and brought the card
4.0 → 7.5 → 8.5, to replace one `pytest.raises` block in a fixture that already constructs the condition.

### [Fix 4 / escalation remedy] F-301 closed, owner chose "fix + re-review" — done inline by the orchestrator

The remedy was four small edits in files the card already owns, each one's correctness **mechanically
verifiable** (kill the mechanism, confirm the new control reds), so I made them inline rather than
spawning a fix agent. `[Inline fallback] cycle-3 remedy`.

```
FIXED F-301 — test: test_ac1_the_planted_shifting_mutant_runs_green_and_reports_nothing
FIXED F-302 — test: test_g1_the_two_construction_refusals_each_have_a_control
FIXED F-303 — test: test_ac7_the_lock_guard_file_reproduces_130_of_130_pass_and_reached
FIXED F-304 — test: n/a (docstring only — the sentence now claims what is demonstrated)
DECLARATIONS F-301 — none about the mechanism: a control was ADDED, the refusal is unchanged. The card's
  `### Declared bounds` heading re-derived six → seven measured.
DECLARATIONS F-302 — none about the mechanism: two controls added for refusals present at HEAD.
DECLARATIONS F-303 — a failure MESSAGE added (no mechanism change); the pin's value is unchanged at 130.
DECLARATIONS F-304 — a claim's reach NARROWED: `KillMatrix.figure()`'s docstring now separates case 1 by
  the reached count instead of asserting all three grids identical.
```

**Every new control was verified to fail without its mechanism — which is the entire point of the
finding, so asserting it would have repeated the defect:**

| kill | the control that must red | result |
|---|---|---|
| `off_key = []` (refusal can never fire) | `…planted_shifting_mutant…` | **1 failed** |
| `if not self.edits:` → `if False:` | `…two_construction_refusals…` | **1 failed** |
| `occurrence < 1` check → `if False:` | `…two_construction_refusals…` | **1 failed** |

Whole file: **67 passed** (66 + the one new node; F-301's control went *inside* the existing test, where
the off-key condition was already constructed). `tests/kill_matrix.py` restored byte-identical after all
three kills (`8dee3401…` before and after), `cp -p` backups only, no `git checkout`/`restore`/`stash`.

**F-301, precisely.** The test already built the off-key condition and then **routed around `_measure`**,
so the refusal was never reached. The control now calls
`runner._measure("SHIFTED", Pass.RECORDING, len(linenos), pristine)` inside
`pytest.raises(MutantRefused, match="no cell for")` **in the same `try` block**, while the shifted file is
still on disk — so the run records shifted linenos while the keys come from `pristine`, which is exactly
the trigger. The `finally` that restores the target is untouched. The refusal's published claim at
`tests/README.md:523` is now backed rather than asserted.

**F-303** keeps the pin at 130 and gives it the message every other cycle-3 control carries: a drift now
reads *"now has N assertion nodes, not 130 … re-derive the bound rather than the expectation"* instead of
`assert 131 == 130`. The finding was right that the pin is correct today and that the bare assert was the
defect.

**One thing I did NOT do, deliberately:** F-204's observation that the new G-5 control re-spells
`(\S*/)?git(\s|$)` as a fourth literal copy rather than sharing a constant. Sharing the constant would
make the demonstration depend on the thing it demonstrates — a control that cannot disagree with its
mechanism is the weaker shape, and this card has spent three cycles on exactly that class. Left as the
reviewer filed it: an out-of-scope observation, not a fix.

### [Review re-entry] round 4 — pre-flight done, reviewer HELD until build gate 6 is green

Owner chose "fix + re-review" at the cycle-3 escalation; `Status` returned to `review` and `Blocked by`
cleared (an escalated card returns to `review`, not `ready`). The cycle counter restarts at 1 for this
invocation, so the honest figure is tracked separately below.

- **[Scope gate] IN_SCOPE.** `excess` = 0 — still exactly the three files of `Touches`, unchanged across
  **four** fix rounds. `comp_spread` skipped (no `## Architecture context`), `poached` empty,
  `guardrail_hits` skipped (G-1…G-6 behavioral).
- **[System contract]** re-checked at re-entry: lens projects **10**, card carries **5** — the set
  `meta/kanban/curation.md` selects. No ids added, none removed.
- **[Round counter]** 3 prior `[Review N/3]` entries, so this is **round 4** against a fatigue threshold
  of 2 × `max_cycles` = **6**. Inside it, and stated rather than hidden by the counter reset: a re-entry
  is not a free reset, and if this round finds another uncontrolled claim the structural answer stops
  being "one more fix".
- **[Reviewer held, deliberately]** Build gate 6 took the board lock at `2026-10-21T13:40:26Z` for a
  ~20-minute full run. The test gate precedes the review cycle by procedure — **and spawning the reviewer
  now would be actively harmful**: it runs targeted pytest, `tests/full_suite_lock.py` would refuse every
  one of those runs as a foreign-lock `UsageError`, and it would read the refusals as reds. That is
  precisely the hazard CARD-258 was built to diagnose and CARD-260's own F-001×F-005 composition
  describes. Manufacturing it to start a reviewer four minutes earlier would be indefensible on this card
  of all cards.
- **What the diff under review now is:** `tests/README.md` +134/−17, `tests/kill_matrix.py` +541/−52,
  `tests/test_kill_matrix.py` +927/−26 — four rounds, still uncommitted, which is why `done` was refused.
- **The one claim this round must re-verify above all:** the refusal message `no cell for` now occurs
  **twice** in the test file — once as fixture prose (`OUT_OF_DOMAIN_TARGET`'s docstring, which was the
  misleading grep hit in cycle 3) and once as the new `pytest.raises(match=…)`. A reviewer that counts
  occurrences rather than reading them would conclude the control existed all along. It did not.

- **[Build gate 6 — PASSED, post escalation remedy]** Full suite, solo under the board lock:
  **8695 passed, 1 skipped, 0 failed, EXIT=0** in 1000.41s (16:40). **Count reconciles exactly against the
  pre-CARD-258 base this branch still sits on:** 8629 + the card's **67** node IDs = 8696 = 8695 + 1
  skipped, and 67 is what the file reports standing alone (66 + the one node F-302's control adds).
  *Note the base, deliberately:* this branch's merge-base is still `02e0f691`, so its 8629 is the old
  main — `main` itself is now 8669 after CARD-258 landed its 40. The rebase belongs to `done`, and the
  interop was already measured clean. Progression on this card: 8671 (gate 1, 1 red) → 8671 (gate 2
  green) → 23 reds (gate 3, F-001's own fix) → 8691 (gate 4) → 8695 (gate 5) → **8696 (gate 6)**.
  → review re-entry, round 4.

### [Review 4 — re-entry] Score: 8.5 (unchanged) — the remedy HOLDS; one Important on a different guard class

Report: `meta/review/20261021T141913Z-CARD-260-cycle4.yml` — 1 high / 2 low, 5 system-contract verdicts.
**[Review sync]** 1 report → `meta/review/`. **Step 8h: 3 ✓ holds, 1 ⚠ unchecked (ADR-0038/R8, same
typed reason a third time, deliberately not upgraded), 1 ✗ (ADR-0039/R1 — new ground).** **R2 and R3
re-verified ✓ position by position**, not inherited.

**The escalation remedy holds, and the reviewer took none of it on trust — which is what I asked for,
since the remedy was mine.** F-301's control is bound to the **real** off-key branch: **M1**
(`off_key = []`) reds it with `DID NOT RAISE MutantRefused`, and **M4** (that branch's message
`no cell for` → `no slot for`) reds it too, so `match=` is tied to that message and not to a sibling
refusal. `UnmeasuredRun`'s message cannot match. The `finally` still restores the target.
**And the trap did not catch it:** it **read** the two `no cell for` occurrences rather than counting
them — `:302` is the new `pytest.raises`, `:1421` is fixture prose — and confirmed the string occurs
**zero** times at HEAD, so the control is genuinely new. F-302 closed (M2, M3 each red it and nothing
else; the ordinary-path arm blocks refuse-always). F-303 closed, and **the message is measured, not
decorative**: that file's assert count went **64 → 102 → 111 → 129 → 130** across its five commits, so
"a live file that keeps gaining census-moving asserts" is accurate. F-304 closed and the narrowed sentence
verified true of the code. **Beyond the four, it swept all 26 refusal sites in `kill_matrix.py` and every
one maps to a `pytest.raises` asserting on its message — the refusal half of this card is now
exhaustively controlled.**

### ⚠ F-401 — and it refutes MY judgement call, measurably. I re-derived it and I was wrong.

At cycle 3 I declined to fix the G-5 four-copy regex, arguing that sharing the constant *"would make the
demonstration depend on the thing it demonstrates — a control that cannot disagree with its mechanism is
the weaker shape."* **That reasoning is inverted, and the measurement is one command.** I broke the
pattern **actually in use** at `:942` (`(\S*/)?git(\s|$)` → a never-matching pattern) and ran the file:

```
occurrences of the pattern literal: 4
mutated the FIRST occurrence (the one in use)
67 passed      <-- nothing red
```

With four copies, `:945`/`:949` assert over **their own** copies, so they cannot disagree with the one the
census uses — the census can be silently disabled. **With the constant shared, breaking it would red
`:945`: a control that CAN fail.** What I missed is that `:945`/`:949` do not demonstrate the census's
behaviour; they demonstrate the *regex's own semantics* — so coupling them to the census's constant
creates a coupling that **detects**, which is the opposite of the hazard I invoked. My cycle-3 note on
this is wrong and is superseded here rather than quietly dropped.

**F-401's full shape, and it is a class not a site:** three mutants survive, 67 passed each — **M5**
(`"git" in str(name)` → `"gxt"`), **M6** (the strings-half pattern), **M7** (G-6's clock-module
`isdisjoint` set → a non-existent module name). Each census asserts only the **absence** of a violation
over a source containing none, so an inert predicate is indistinguishable from a holding one: R1's
"caught WITH" half does not exist for any of them. Two more sites of the same shape are named and
unmutated: `:901` (`aliased == []`) and `:1843`.
**The guardrails themselves hold in substance** — the reviewer's own independent grep finds no git
invocation in `kill_matrix.py` (prose and a `.git` docstring pointer only) and zero clock names. This is
test-quality, not a product defect.

### [Family] streak STAYS 1 — and the attribution was bounded by evidence, not by my record

The reviewer did not trust the card's `[Fix N]` prose for attribution. It bounded fix 4's reach
**physically**: `tests/README.md`'s mtime is **older than the cycle-3 review**, so fix 4 never touched it;
and inside `kill_matrix.py` fix 4 is a single **+2-line** edit at line 795 — every cycle-3 line reference
below 795 shifted by exactly +2 (off_key 1341→1343, topology 1294→1296) and every one above is unmoved
(`_RAN_EXIT_CODES` :323, `_SPAWN` :440). That is F-304's docstring and nothing else. **F-401 is present
verbatim at HEAD** (`git show HEAD:tests/test_kill_matrix.py` :592, :599, :929–947).

So **the family trigger does not fire.** The honest reading, which I am adopting: **not "one more turn of
the loop" but "the R1 sweep was never exhaustive"** — rounds 1–3 swept the *refusals* (now 26/26
controlled) and never swept the *censuses*.

### [Stalled check] ⚠ the stall signature IS present, and it is the owner's call

Aggregate across rounds 3 → 4: **Δscore = 0** (8.5 → 8.5, below `min_improvement` 0.5) **and Δfindings = 0**
(1 → 1). Both of the stalled check's conditions are met, which by the letter escalates. The re-entry reset
the cycle counter to 1 and would have hidden this; the aggregate round counter is why it did not.
**The reviewer's score is unchanged *by design*** — it says so: "the code got strictly stronger, and a new
violation of the same mandatory rule replaced the one that closed."
**What distinguishes this from a true stall:** the remaining work is **enumerated, not discovered** —
five absence-assertion sites (`:901`, `:935`, `:942`, `:1840`, `:1843`), each closable by one planted
positive and each verifiable by killing its mechanism, plus hoisting one regex into a shared constant.
A stall is a loop that keeps finding unknowns; this is a finite list. **Round 4 of a 6-round fatigue
threshold** — so a round 5 is affordable, and a round 6 would not be.

### [Fix 5] FIX PRE-GATE: PASS — and the fix found a trap in my own brief

Scoped to F-401 by the owner's authorisation of a round 5. All **8** tests the fix named exist and pass.
`DECLARATIONS F-401 — doc ×3, doc `_spawn_argv_heads` (new), README, matrix none`. The `matrix none` is
**correct and I verified it**: CARD-260 has no `## Failure matrix` section (15 other cards on this board
do). `tests/kill_matrix.py` is byte-identical to fix 4 (`8dee3401…`) — the whole of round 5 is in
`tests/test_kill_matrix.py` (`c2113a33…` → `1468707b…`) and `tests/README.md` (`1686c5c2…` → `81dfaa8c…`).
**Those pre-edit digests are the three the cycle-4 report records as what it reviewed**, so round 5's
starting point is corroborated by the previous reviewer even though nothing on this card is committed and
no delta is diffable.

Shape: the seven inline census comprehensions became seven module-level callables
(`_aliased_spawn_imports`, `_spawn_argv_heads`, `_git_among`, `_git_command_strings`,
`_timing_module_imports`, `_clock_names_in`, `_hard_coded_env_names`), each called twice — on `INSTRUMENT`
asserting nothing is found, and on a planted source asserting the violation **is** found. One shared
`GIT_COMMAND = re.compile(r"(\S*/)?git(\s|$)")` replaced four copies. 67 → 72 tests.

**[The brief was wrong three ways, and the fix caught all three.]**
1. **The class is seven sites, not the five I enumerated.** The two I missed: the prose-side regex assert
   (my brief dismissed it as a pseudo-control; after the hoist it is a real one) and
   `"KILL_MATRIX" not in km._PLUGIN_SOURCE`, a census over the instrument's **generated** source.
2. **My proposed remedy reproduces the defect if the plant is derived from the set under test.** The fix's
   first implementation built each planted source *from* the set (`"".join(f"import {m}" for m in
   TIMING_MODULES)`) and compared the finding against that same set — delete a member and the plant and the
   expectation shrink together, agree, and nothing reds. **That is F-401's own inversion rebuilt inside
   F-401's fix.** It caught it pre-hand-back and measured it: three of its mutants are genuine member
   *deletions* and all three would have survived the generated shape. The distinction it handed back is the
   sharp one: *coupling to the predicate* detects; *deriving the expectation from the predicate's own data*
   does not. Shipped shape — plants as literal text, expectations as literals, and each hand-written set
   gets a **pair** of asserts (finding-vs-literal, set-vs-literal) so a member deleted **and** a member
   added both red.
3. **I pointed it at the card in the worktree**, which is the stale 134-line implementation snapshot; the
   1572-line record with every review note is on main. It reported "the card has no review notes" and was
   describing a different file than I was.

**[Orchestration gap, recorded because it cost the next station something.]** The fix's twelve-mutant
D-list existed only in its hand-back to me — nothing on disk carried it — so when I asked the reviewer to
re-derive D1–D12 it could not, and built its own eighteen-mutant set instead. Its conclusions stand on its
own measurements, but **the two reports' D-ids are not the same mutants and must not be read as such.**
The fix's list, persisted here so it is auditable: D1 `GIT_COMMAND`→never-matching; D2 `_git_among`'s
`"git"`→`"gxt"`; D3 `SPAWN_IMPORT_MODULES` member replaced; D4 `_spawn_argv_heads` default-deny
`isinstance(argv,(ast.List,ast.Tuple))`→`(ast.AST,ast.Tuple)`; D5 `TIMING_MODULES` member replaced;
D6 `CLOCK_NAMES` member replaced; D7 `ENV_NAME_SHAPE`→never-matching; D8 the `km._SPAWN` walk neutered;
D9 `GIT_COMMAND`→`.*git.*` (widened); D10/D11/D12 `SPAWN_IMPORT_MODULES`/`TIMING_MODULES`/`CLOCK_NAMES`
member **deleted** (as distinct from replaced). All twelve line-count-preserving, `cp -p`-backed, restored
byte-identical.

### [Review 5 — re-entry cycle 2/3] Score: 8.8 (8.5 → 8.8, Δ+0.3) — and its one gating finding was REFUTED

Report: `meta/review/20261021T165300Z-CARD-260-cycle5.yml`. **[Review sync]** 1 report → `meta/review/`.
**Step 8h: 3 ✓ holds, 1 ⚠ unchecked (ADR-0038/R8 — fourth cycle, same typed reason, deliberately not
upgraded), 1 ✗ (ADR-0039/R1 → F-501, now dismissed).** R2 and R3 re-verified position by position.

**F-401 is closed and mutation-confirmed.** The reviewer killed 17 of 18 mutants it chose itself; the
survivor disables an assertion rather than a mechanism and therefore certifies nothing. It confirmed
**no residue of the generated-plant shape anywhere**, including arms the fix did not flag — every plant is
literal triple-quoted text, every expectation a literal list — and confirmed the paired assert closes both
directions: member deleted (3 mutants), replaced (3), added (3), all killed, the added case by the literal
pin whose failure message is the instruction to plant the new member.

### [Adversarial verification] 1 finding → REFUTED; 1 positive verdict → REPRODUCED

**F-501 (the only gating finding) — REFUTED, and I re-measured it myself rather than taking the skeptic's
word.** The finding said the docstring at `:1032-1044` names arms that cannot fail, specifically that the
prose arm `:1064` never executes under a widened `GIT_COMMAND` because `:1059` reds first. My own run, one
mutation of line 74, plain propagating pytest, file restored byte-identical (`1468707b…` both sides):

| widening | `:1059` (`invoked == []`) | `:1064` (prose arm) |
|---|---|---|
| `r".*git(\s\|$)"` — the minimal pattern satisfying the docstring's own "matches prose" | **passes** | **FAILS**, own message |
| `r".*git.*"` — the reviewer's choice | **FAILS** | shadowed |

So the prose arm **does** have a control that can fail; it is shadowed only under the broader pattern the
reviewer happened to pick. `re.match` with a non-DOTALL `.*` cannot reach past line 1 of a multi-line
string constant, which is why the module's own "No git command anywhere" sentence is invisible to the
narrower widening. **R1 asks whether a control CAN fail, not whether it fails under every mutant** — the
filing does not hold. The skeptic also showed clause 1's count is right *measured the way the docstring
says it was measured*: under the **recording** pass, neutering `_SPAWN` reds exactly five arms
(`:1051 :1055 :1085 :1145 :1146`), and per-assertion measurement immune to short-circuit is that pass's
defining property (`kill_matrix.py:22-29`). The reviewer had counted under the re-raising pass.
**One residue is real and is not the filed violation:** "across three of these tests" is two tests, plus a
third red out of domain at the `pytest.raises` loop. Follow-up, not a gate.

**ADR-0039/R2 `✓ holds` — REPRODUCED** (re-derivation spot-check, not re-judgment). All three shapes the
verdict cites fail closed, verified by feeding the census freshly written sources: keyword `args=` → named
line-numbered `AssertionError`; starred argv → names the shape refused; empty argv literal → raises. The
structural argument is what makes it stick: once a call matches, every path either appends exactly one head
or raises, and the only `continue` is the match filter itself, so a **matched** call cannot be silently
omitted. 20 further argv shapes and 15 odd AST positions (f-string expression, decorator, `match` case,
except handler, comprehension, async def) all raised — zero silent omissions.

### [Figures] the fix's class-enumeration numbers do not reproduce — 189, not 172

The reviewer recounted and so did I, independently: **189** `ast.Assert` nodes in the shipped file (181 in
`test_*` functions, 8 in module-level helpers), against the fix's **172**. A grep-style count of
`assert ` line-starts gives **202** — a third domain. The absence-shaped count differs definitionally
(fix 30, reviewer 27) and the 32-vs-29 gap is whether the three default-deny asserts inside
`_spawn_argv_heads` are counted. **This is reporting hygiene, not a defect in the code, and I verified
that:** none of 172, 30, 189, 27 or 29 appears anywhere in `tests/test_kill_matrix.py`,
`tests/README.md` or `tests/kill_matrix.py`. The committed assert-count figures that *do* ship are
controlled — `130` is recomputed by `assert counted == 130` whose failure message instructs re-derivation,
and the fixture's `5 assertion nodes` is parsed back out of the instrument's own output at `:1466`.
**It is nonetheless this card's own trap 1** — an instrument has a domain, and the domain is part of every
figure it produces — committed in the hand-back prose rather than in the artifact. I repeated the `32` to
the owner before checking it; corrected here.

### [Scope gate] cycle 5: IN_SCOPE

`git status --short` in the worktree is the same three files as every prior round
(`tests/README.md`, `tests/kill_matrix.py`, `tests/test_kill_matrix.py`); round 5 touched two of them and
added no component. No ready sibling's `Touches` is covered.

### [Family] streak STAYS 1 — nothing to attribute

The family check needs a *gating* finding attributed to the previous fix. After adversarial verification
there is no gating finding, so there is nothing to attribute and the trigger cannot fire. Recorded rather
than skipped, because a cycle that ends with zero gating findings is exactly where this check gets quietly
dropped.

### [Stalled check] does NOT fire — the success path is open

Raw aggregate 4 → 5 would read Δscore +0.3 (below `min_improvement` 0.5) and Δfindings 1 → 1, which is the
stall signature that was present at round 4 and was the owner's reason to authorise this round. **After
verification it is Δfindings 1 → 0.** The stalled check governs whether to keep looping; the loop's
*success* condition — score ≥ `min_score` 8 **and** zero critical/important surviving verification — is
met at **8.8 with zero**. So the review loop exits successful at round 5 of a 6-round fatigue threshold,
and the next station is the AC/EC/G gate, which this card has never run.

**Remaining findings, none gating:** F-502 (minor — the `(\S*/)?git(\s|$)` literal is restated in prose at
`:1013` and in the README's G-5 paragraph with no control; one assert on `GIT_COMMAND.pattern` closes it),
F-402 and F-403 (low, carried from cycle 4 and re-derived here rather than taken on the predecessor's
word).

### [Follow-up observations] for the card owed after merge — all out of round-5 scope

1. ~~**An uncontrolled figure one layer further out.**~~ **STRUCK — the figure is correct and the error
   was mine.** I had recorded that `_scoped_edits`'s docstring at `:2275` — `setattr(` "occurs 6 times in
   one docstring and 32 times in the file around it" — did not reproduce, having counted **13 across five
   docstrings** in `tests/test_db_engine_lifecycle.py`. **I counted in the wrong file.** `_scoped_edits`
   is called on *two* texts, and the sentence names one clause for each: `setattr(` occurs **exactly 6
   times in `src/nonogram/db/session.py`, all six inside `reset_engine`'s docstring** (which is the span
   the anchor mutates), and **exactly 32 times in `tests/test_db_engine_lifecycle.py`**, the file around
   it. Both clauses reproduce exactly. Recorded rather than deleted: a false "does not reproduce" costs
   the same as a missed finding, and the mistake is this card's own trap 1 — I read a figure without its
   domain and then measured in a domain the author never claimed.
2. **The empty argv literal fails with a bare `IndexError`** — no message, no line number, no naming of the
   shape, unlike its three sibling asserts. R2's letter is satisfied (a failure, never a silent pass) but
   nothing *plants* that shape, so nothing pins it. `assert argv.elts, f"empty spawn argv at line
   {node.lineno}"` plus a fourth plant in `test_g5_the_argv_census_fails_rather_than_skips` closes it.
3. **Three alias routes are invisible to both spawn censuses** — `import subprocess as sp; sp.run(...)`,
   `run = subprocess.run`, and `functools.partial(subprocess.run, ...)`. The import census inspects only
   `ast.ImportFrom`, and the docstring names only the `from subprocess import run` route as refused. These
   are *not matched as spawn-shaped at all* — a different category from a matched-then-swallowed shape —
   and the complementary strings half catches all three. Only the run-time-assembled variant escapes both,
   and that is the bound the card already declares and demonstrates. Inside a named bound, not a quiet
   swallow; worth naming in the docstring anyway.
4. **`mkdtemp` workdir / in-tree mutation window** — carried from earlier rounds, still owed.

### [AC/EC/G gate — forward hazard] AC-7's anchors survive main's movement, verified by derivation

The gate flagged that main is 11 commits ahead and CARD-258 changed `src/nonogram/db/session.py`, from
which AC-7's second anchor derives its mutant grid — so the anchor could pass here and red after the
rebase. Checked before rebasing, against both blobs rather than by reading:

- `session.py` **did** move: `057ad2b4…` at `b441ba00` → `c37a2664…` at main.
- `_init_engine_globals()` returns **`('SessionLocal', '_engine_url', 'engine')` at both** revisions.
  CARD-258's `_reset_count` never enters it — not because of the `ast.Assign`-vs-`AugAssign` gap in that
  function (there is no `AugAssign` inside `_init_engine` at either revision), but because `_reset_count`
  is not declared global in `_init_engine` at all. It is declared in `reset_engine`, which the derivation
  does not read.
- The grid's one hard-coded figure, `count("global engine, SessionLocal, _engine_url") == 2`, **still
  holds on main** — main's second occurrence is `global engine, SessionLocal, _engine_url, _reset_count`,
  and the pin is a **substring** count, so the added name is invisible to it. That is what carries the
  anchor across the move; it is also a mild fragility worth naming, since a *reordered* declaration would
  red where an appended one does not.
- `reset_engine`'s docstring is unchanged in every respect the grid mutates: `engine` ×23,
  `SessionLocal` ×2, `_engine_url` ×2, `setattr(` ×6 at both revisions. `tests/test_db_engine_lifecycle.py`
  is not in main's diff at all.
- No collision: main changed none of the card's three files, so the rebase is clean for code.

Both AC-7 tests still get one run on the rebased tree before `done` — a derivation that holds is not a
substitute for the gate it feeds.

### [Fix 6 / AC-gate remedy] FIX PRE-GATE: PASS — G-5's second half now has a control per arm

Five named tests, all exist and pass. `tests/test_kill_matrix.py` `1468707b…` → `294a6422…` (2475 → 2701
lines), `tests/kill_matrix.py` `8dee3401…` → `4279dc5d…` (1433 → 1455), `tests/README.md` `81dfaa8c…` →
`5f2f9659…`. 72 → 76 tests. `DECLARATIONS G-5 — doc module docstring (re-derived), doc
`Runner._verification_failures` (re-derived), README G-5 paragraph (new per-arm paragraph), `:125`
confirmed, matrix none`. `DECLARATIONS AC-6 — doc none; module docstring's trap-1 sentence confirmed`.

**My own mutant, re-run against the fixed tree — the arms are isolated, which is the point:**

| mutant | reds |
|---|---|
| `diff -q` arm alone | `…_is_caught_by_diff_q`, `…_fails_the_run_from_its_finally` |
| `shasum` arm alone | `…_is_caught_by_shasum_256`, `…_fails_the_run_from_its_finally` |
| **both — the one that left 72 passed** | all three |

File restored byte-identical (`4279dc5d…`, 1455 lines) after each.

**The plant is in `cp` itself, and it has to be.** A successful `cp -p backup path` makes the two files
equal **by construction**, so no *input* can make `_verification_failures` see a mismatch. The control puts
a four-line `sh` shim first on `PATH` that, for restores only (recognised by which end the `backup.*` name
sits on), exits 0 and writes nothing. That is the actual hazard G-5 names — an exit code saying it worked
while the bytes on disk are not the backup's — rather than a re-spelling of the comparison, which is the
four-copy defect this card already gated on once.

**And it sharpened the finding rather than accepting it.** With both comparisons dead the suite looked calm
because a wrong-bytes restore *is* still caught one step later, by the between-mutants SHIPPED re-run. But
that backstop exists only **between** mutants: the outer `finally` has no re-run after it, so on the last
or only mutant of a run the file is left mutated and published as verified — with G-5 forbidding a git
restore. The hole is narrower than "nothing notices" and worse than it sounds: it is precisely the exit
path with no backstop.

The `shasum`-cannot-run branch is now controlled too, by narrowing `PATH` to a directory with `cp` and
`diff` and no `shasum` at all. Scope stated rather than implied: that plants the **absent binary** (the
`OSError` half), which is what the docstring's sentence claims; a `shasum` that exists and exits non-zero
takes the same `except` and the same `append`, so the *branch* is controlled and the two exception classes
are not controlled separately.

### [AC/EC check] All criteria/constraints ✓ (evidence)

Fresh re-run of the full gate after fix 6, on all 13 items, with the previous run's verdicts deliberately
**withheld from the verifier** so no conclusion could be inherited. 22 mutants, every one
line-count-preserving, `cp -p`-backed, and restored verified by **both** `shasum -a 256` and `diff -q`.
Baseline and post-gate both 76 passed, RC=0, digests identical at start and end.

```
AC-1 ✓ demonstrated — _refuse_line_shift neutered -> 4 red (DID NOT RAISE MutantRefused); topology
       re-check neutered -> 3 more
AC-2 ✓ demonstrated — aggregate_any_red -> last-write-wins -> 2 red ('PASS' == 'FAIL'), incl. the real-run arm
AC-3 ✓ demonstrated — Pass.reraise forced True; blind-spot set emptied; _Recorder always raising -> all red
AC-4 ✓ demonstrated — between-mutants check removed, and fed the STALE shipped -> red both ways
AC-5 ✓ demonstrated — found = source.count(old) -> edit.expect -> 6 red
AC-6 ✓ demonstrated — trap 1 exactly: figure prints {collected_tests} under "assertion nodes" -> red
AC-7 ✓ demonstrated — orelse=[] so no PASS is ever recorded -> both anchors red
G-1  ✓ demonstrated — both selection refusals off + _RAN_EXIT_CODES widened -> 3 red
G-2  ✓ demonstrated — read AS RESTATED, and controlled in BOTH directions (see below)
G-3  ✓ demonstrated — static + 28 passing guard tests, 0 skipped; refusals neutered -> 9 red
G-4  ✓ demonstrated — import equality; `import ast, numpy` -> red; a stdlib addition correctly does not
G-5  ✓ demonstrated — both restore comparisons dead -> 3 red; git censuses inert -> 4 red
G-6  ✓ demonstrated — set members dropped -> red; a real clock planted -> red
```

**G-2's restatement is itself controlled, which is the evidence I most wanted and did not ask for.** The
verifier added a third plant the card never claimed: putting the **old by-existence rule back** reds
`test_g2_a_lock_this_worktree_holds_does_not_refuse_the_start` and the four-state equality test. So the
own-tree / stale / override relaxations are **measured, not merely declared** — the restatement is not a
weakening, it is the only wording the code can hold, and the hold is controlled in both directions.

**Four honest bounds the gate recorded while still passing the items. None gates; all are follow-up.**
1. **"G-2 never writes a lock" has no behavioural control** — it rests on a structural enumeration of every
   write site in `kill_matrix.py` (three: the plugin's per-pid jsonl under its temp records dir, the
   mutated target in `_apply`, the generated plugin file), complete over the card's own code. The verifier
   deliberately did **not** plant a lock-writing mutant, and said why: `board_lock_path()` honours the env
   override, but one G-2 test does `monkeypatch.delenv`, so such a plant could reach the **main checkout's
   real lock file**. Declining that plant was the right call and the reason belongs on the record.
2. **AC-4's honest-path test is not a second control** — `test_ac4_two_sequential_mutants_each_see_a_clean_shipped`
   survived both AC-4 plants; it checks the between-matrices exist, are FAIL-free and equal SHIPPED's cells,
   so an implementation storing the initial `shipped` under each mutant's name would satisfy it. The leak
   test is the whole control.
3. **AC-3's structural arm does not route through `Pass`** — it calls `km._Recorder(reraise)` with literal
   booleans, so it is insensitive to a `Pass.reraise` mutation. It has its own control via the raise branch,
   so AC-3 is covered in two layers, but they are independent arms, not one chain.
4. **AC-7's anchors pin content, not commit identity** — `LOCK_GUARD_TEST`/`LIFECYCLE` read the working
   tree (there is no git call; G-5 forbids one). Content drift reds via `counted == 130` and the re-derived
   arms; a file replaced by different bytes that happened to yield 130 would not. Both anchor files are
   byte-identical to their named commits today, verified read-only — but that is an external check, not the
   test's.
