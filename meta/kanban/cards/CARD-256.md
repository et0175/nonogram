# CARD-256: The lock guard's path-redirect variable gets the same control and the same loudness as its override

**Status:** in_progress
**Priority:** P1
**Category:** ops
**Complexity:** trivial
**Estimate:** 0.25d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/256-the-lock-path-var-gets-a-control
**Worktree:** ../PythonProject4-card-256
**Source:** CARD-255 review cycle 3, F-203 — the certifier's answer to "is there any failure mode that would be *silent*?"
**Idea:** —
**Wave:** 50
**Depends on:** CARD-255 (merged)
**Touches:** tests/test_full_suite_lock.py, tests/full_suite_lock.py, tests/README.md
**Review score:** —
**Started:** 2026-10-20T08:41:42Z · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why — one measured hole, and it is the silent kind

CARD-255's guard has **two** environment switches. `NONOGRAM_IGNORE_FULL_SUITE_LOCK` walks past a
lock **loudly**, by design, and an in-tree setter of it is caught by a tree-wide scan with its own
control. `NONOGRAM_FULL_SUITE_LOCK` redirects the guard at a different path — and does it in silence.

Probed by the certifier, not reasoned about: pointed at a path holding no lock, `386 passed`,
`current_verdict() == (True, None)`, `report_line() == None`. **A run allowed that should have been
refused, printing nothing at all.** And the scan greps the override variable only, so an in-tree
setter of the path variable sits outside the control that exists for the other one.

The route is concrete, and it is the same file the whole family keeps circling:
`scripts/run_admin_tests.sh` is a pytest wrapper with a block of `export`s. CARD-255 cycle 2's M-H
proved the scan reds when the **override** is exported there. Append
`export NONOGRAM_FULL_SUITE_LOCK=/tmp/none` instead and the scan stays **green**. The guard's own
docstring asserts the condition that makes it safe — *"Unset — which is every real run, gate or
agent"* — and **nothing holds it**.

This card exists because that sentence should be a test, not a hope, in a guard that now runs in
front of every pytest invocation on this board.

## What to implement

1. **Give the path variable the same scan control.** The remedy is two tokens —
   `["git","grep","-l","-e",guard.OVERRIDE,"-e",guard.LOCK_PATH_VAR]` — and the certifier verified it
   adds no hit outside the four files already exempted. Extend the existing control rather than
   writing a second one; the exemption set and its shape constraint stay as CARD-255 left them.
2. **Make the redirection announce itself.** The guard already has `_ANNOUNCEMENT` and
   `pytest_terminal_summary`. A run reading its lock from somewhere other than the board's own path
   should say so, for the same reason the override does: a switch that changes the guard's verdict in
   silence is indistinguishable from the guard not working.
3. **Close F-202's surviving mutant.** `M-M` (the `startswith` half of the prose exemption deleted)
   **survived 36/36** — under it the exemption becomes "any `.md`/`.yml` anywhere", which would absorb
   `ci/forge-ci.yml` and `.github/workflows/*.yml`. It cannot alter the guard's runtime verdict (it
   widens a *test's* exemption), which is why it is not CARD-255's problem — but one assertion closes
   it.
4. **Narrow four sentences CARD-255 left owed** (ADR-0039/R1's own remedy, carried forward):
   `test_full_suite_lock.py:464` *"prose, never anything a shell can run"* and `:555` *"an executable
   under an exempted prefix is still an offender"* — both false as written, because the clause bounds
   the **extension**, and an executable `.md`/`.yml` gets through (probed live at mode 100755);
   `full_suite_lock.py:104-106` *"Unset — which is every real run, gate or agent"* — unverified until
   item 1 lands; and `:735` *"five of the **six** names below"* — the set now holds **seven**, so the
   independent reach is two, which the same docstring already says.

**Optional, if it is cheap:** the mode-bit axis can be closed outright — `git ls-files -s` over both
prefixes returns 542 entries, all `100644`, so an equality on the mode is available and would make
"nothing a shell can run" true rather than narrowed.

## Acceptance criteria

- **AC-1** *Given* an in-tree file exporting `NONOGRAM_FULL_SUITE_LOCK`, *when* the tree scan runs,
  *then* it is reported as an offender, naming the file. (test: the extended scan control)
- **AC-2** (the control) *Given* the second `-e` removed, *then* AC-1's test fails. A scan that cannot
  red on the variable it claims to cover is this board's recurring defect.
- **AC-3** *Given* a run whose lock path is redirected, *then* the run says so in its terminal
  summary; *given* an ordinary run, *then* it says nothing. (test: both halves, since "says nothing"
  is the half that rots)
- **AC-4** *Given* the `startswith` half of the prose exemption deleted, *then* a test reds — M-M
  must no longer survive.
- **AC-5** (guard) *Given* this change, *then* the skip profile is unchanged and a tree with no lock
  behaves exactly as before, both re-proved as CARD-255 proved them.

## Guardrails

- G-1: The guard's **verdict** logic is not touched beyond the announcement — a run that was refused
  before is refused after, and a run that was allowed is allowed. Prove it the way CARD-255's cycle 3
  did: the module's code objects compile to byte-identical `co_code` apart from the announcement path.
- G-2: The abort never becomes a skip; the guard names no skip API.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-4: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-5: **Never create, modify or delete the board's real lock.** Every lock the tests make lives in a
  temp path behind the very variable this card is about.

## Worktree notes

- **[Do not take timing measurements]** other cards may share this machine.
- **[The trap]** This card's own subject is a switch that is silent. The obvious test redirects the
  path, finds no lock, and asserts the run proceeds — which is the *current* behaviour and would pass
  before and after. The test that matters asserts the run **says** it was redirected, and the mutant
  is deleting the announcement, not the redirection.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`. Note the known
  trap: read the ADR files **case-insensitively** for the reach-limit idiom, or ADR-0039 silently
  drops out of the contract — and this card is entirely about ADR-0039/R1 and R3.

## System contract

Curated to **5 of 10** in-scope rules under `meta/kanban/curation.md`: every rule whose
enforcement does not reach this card's new code is kept; the rest are dropped because the suite runs them on
every gate. **5 dropped.** ADR-0039 present, as the sanity check requires for a card
touching `tests/**`.

- **ADR-0038/R7** — _review-lens — nothing executes it_
  Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in
  pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — _review-lens — nothing executes it_
  Browser tests run locally, against Chromium installed by `playwright install chromium`. When
  Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible
  in the run summary. They never pass silently. Once a CI pipeline exists, it installs Chromium
  (playwright install chromium) before running them; until then there is no CI, and that is a
  known gap, not a met clause.
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


## Implementation record (worktree, uncommitted)

**Commit:** `28de78d9` on `card/256-the-lock-path-var-gets-a-control`, pathspecs
`tests/full_suite_lock.py tests/test_full_suite_lock.py tests/README.md` (the card's Touches, exactly).
Nothing under `meta/` committed. The board's real lock was checked absent before every pytest and
was never created, modified or deleted; every lock these tests make lives under `tmp_path` behind
`NONOGRAM_FULL_SUITE_LOCK` (G-5).

### TDD — the test failed first

`tests/test_full_suite_lock.py` 36 -> 41 tests. The red run, before any guard change:

```
FAILED test_an_executable_setter_under_an_allowlisted_prefix_is_still_caught
   the scan saw ['ci/forge-ci.yml', 'meta/kanban/cards/CARD-999.md',
   'meta/kanban/cards/run-the-suite.sh', 'meta/review/...cycle1.yml',
   'meta/review/run-the-suite.sh']            # the three path-var setters invisible
FAILED test_a_redirected_run_says_which_lock_it_read
   AttributeError: module 'tests.full_suite_lock' has no attribute 'redirect_note'
FAILED test_an_ordinary_run_says_nothing_about_where_its_lock_came_from      (same)
FAILED test_a_redirected_real_run_announces_it_in_the_terminal_summary
   assert '<tmp>/there-is-no-lock-here.lock' in '. [100%]\n1 passed in 0.03s\n'
4 failed, 1 passed
```

That last line is F-203 itself: a redirected run, `1 passed`, nothing said.

### What the announcement says

```
full-suite lock: reading the lock from /private/tmp/.../there-is-no-lock-here, not the
board's own /Users/omelnikova/.../meta/kanban/.full-suite.lock — NONOGRAM_FULL_SUITE_LOCK is set
```

Printed in the terminal summary (where `-q` cannot hide it) and in the run header. The certifier's
probe re-run: `NONOGRAM_FULL_SUITE_LOCK=<no lock there> pytest tests/test_clues.py` -> `386 passed`
**plus that line**; the same selection with the variable unset -> `386 passed` and nothing added.
No file was created at the probe path.

### G-1 — the verdict did not move

`co_code`/`co_consts` of every code object, baseline vs HEAD (compiled from source, walked
recursively):

| differs | identical |
| --- | --- |
| `<module>` (the new `def` + `__all__` gains `redirect_note`; `dis` diff is those four instructions and line shifts, no statement changed), `pytest_configure` (the announcement path) | `verdict`, `current_verdict`, `lock_path`, `default_lock_path`, `read_lock`, `parse_fields`, `_same_tree`, `_names_a_tree`, `_epoch`, `lock_age_seconds`, `_describe`, `_one_line`, `this_worktree`, `main_repo_root`, `report_line`, `pytest_terminal_summary` — byte-identical in both |

Behaviourally re-proved too (mutant **M-F**, `names_a_tree and _same_tree(...)` -> `False and ...`,
i.e. treat every lock as foreign): reds the self-run case (3 assertions) and leaves the refusal
case green — CARD-255's pair, unchanged.

### Per-assertion kill matrix

Instrument: every `ast.Assert` **at any depth** (the two `for`-loop asserts included) rewritten into
a recording try/except keyed on the node's own `lineno`, so a short-circuit cannot hide an arm —
`BASELINE` shows all 41 assertions **PASS and reached**, and no assertion reports NOT-REACHED under
any mutant. All 21 mutants are line-count preserving (deletions become never-matching values).

| test | assert | killed by |
| --- | --- | --- |
| `…sets_either_of_the_guards_env_switches` | `not offenders` | M-N, M-X, M-Y, M-K, M-K2 |
| | `OVERRIDE not in conftest` | M-K2 |
| | `LOCK_PATH_VAR not in conftest` | M-K |
| `…setter_under_an_allowlisted_prefix_is_still_caught` | `hits == prose+setters+elsewhere` | **M-1** |
| | `all setters under the prefixes` | M-X |
| | `elsewhere is prose-shaped and outside` | M-Y |
| | `offenders == setters+elsewhere` | M-1, **M-M**, M-E, M-X, M-Y |
| | `offenders(elsewhere) == elsewhere` | **M-M** |
| | `offenders(prose) == []` | M-X, M-Y |
| | `100755 in _tracked_modes(repo)` | M-X, M-T, M-S |
| `…exempted_prefixes_hold_nothing_a_shell_can_run` | `len(modes) >= 500` | M-X, M-S |
| | `set(modes) == {100644}` | M-X, M-S |
| `…redirected_run_says_which_lock_it_read` | `note is not None` | **M-A** |
| | `the path is in it` | M-A, M-D |
| | `the variable is in it` | M-A, M-V |
| | `the default path is in it` | M-A, M-P |
| `…ordinary_run_says_nothing_about_where_its_lock_came_from` | unset -> `None` | M-C |
| | `''` -> `None` | M-C |
| `…summary_hook_says_nothing_when_there_is_nothing_to_say` | `quiet.lines == []` | M-R |
| | `loud.lines == [the line]` | M-R2 |
| `…gate_running_under_its_own_lock_is_not_refused` | rc == 0 / `1 passed` / no verdict phrase | M-F (3 of 4) |
| `…redirected_real_run_announces_it…` | the path is in the output | M-A, **M-B**, M-D, M-R2 |
| | the variable is in the output | M-A, M-B, M-V, M-R2 |
| `…tree_with_no_lock_runs_exactly_as_it_did_before` | no verdict phrase | M-Q2 |

Mutants: **M-1** second `-e` dropped from `_scan` (AC-2); **M-M** `startswith` half of the prose
exemption -> `True` (AC-4); **M-E** `endswith` half -> `True`; **M-N** `not in OVERRIDE_NAMERS` ->
`True`; **M-X** `OVERRIDE_PROSE` -> prefixes nothing is under; **M-Y** `PROSE_SHAPES` ->
`(".txt",".ini")`; **M-T** `_tracked_modes` reports `100644` for everything; **M-S** its pathspec
lists nothing; **M-K/M-K2** `tests/conftest.py` names the path var / the override (in a comment,
line-preserving); **M-A** `redirect_note` always `None` (the announcement deleted); **M-B** the hook
drops `redirect_note()` from `_ANNOUNCEMENT` (the announcement deleted at the wiring); **M-C** the
note becomes unconditional; **M-D/M-V/M-P** the path / the variable / the default path removed from
the sentence; **M-R** `if _ANNOUNCEMENT` widened; **M-R2** `write_line` deleted; **M-Q/M-Q2**
`verdict` / `current_verdict`'s no-lock branch returns a verdict; **M-F** every lock foreign.

**Measured bounds, stated rather than left to be found.**
- `M-Q` (the `verdict` no-lock branch) **survives**: `current_verdict` returns before calling
  `verdict` when there is no lock, so that branch is unreachable from a real run. `M-Q2`, the same
  edit in `current_verdict`, is killed. Not fixed — the surviving edit changes nothing observable.
- `_ANNOUNCEMENT = "\n".join(lines) or None` -> without the `or None`: an **equivalent** mutant
  (`""` and `None` are both falsy at both report hooks), so no control can tell them apart.
- A mutant deleting the *redirection* (`lock_path()` ignoring the variable) is deliberately **not**
  in the set: under it every real-process case here reads the board's own lock, which G-5 forbids.
- Unkilled by this set, and why: the four `rc == 0` / `1 passed` premises in the two redirected
  real-run cases (they establish that the run happened, not what it said — the claims beside them
  are killed four ways each); the two `"skipped" not in combined` assertions (CARD-255's, untouched,
  measured there); and `test_a_foreign_lock_aborts_a_real_run_before_collection` in full (CARD-255's,
  included only to show M-F leaves it green).
- Every mutant was restored from a byte-identical backup, `diff`-verified in the harness itself
  (`assert d.returncode == 0`); no `git checkout --`. `tests/conftest.py` ends the work unmodified
  (`git status` clean).

### The four sentences, narrowed

1. `test_full_suite_lock.py` `PROSE_SHAPES` — was *"prose, never anything a shell can run"*. Now
   states that the clause bounds the **extension** and nothing else, that an executable `.md`/`.yml`
   under a prefix is exempted by it (probed live at 100755), and that the mode axis is closed by a
   separate equality, named.
2. `_scan_offenders` docstring — was *"an executable under an exempted prefix is still an offender"*.
   Now *"prose exempts prose by extension, so a `.sh` under an exempted prefix is still an offender —
   an executable `.md` is not"*, plus what each half of the clause must not absorb.
3. `full_suite_lock.py` `LOCK_PATH_VAR` — was *"Unset — which is every real run, gate or agent"*.
   Now: that it is unset is held only as far as it is measured — no **tracked** file in this tree
   names it (the widened scan, named); untracked files and the out-of-repo gate scripts are outside
   `git grep`'s reach and are read, not held; and what closes the rest is that a run which does set
   it says so.
4. `test_the_guard_cannot_turn_a_refusal_into_a_skip` — *"five of the **six** names below"* ->
   **seven** (the set holds `skip`, `skipif`, `importorskip`, `xfail`, `add_marker`, `exit`, `Exit`;
   the text rule reaches five, so the syntax rule's independent reach is two, which the same
   docstring already said).

**Optional item taken:** the mode axis is closed outright, not just narrowed —
`test_the_exempted_prefixes_hold_nothing_a_shell_can_run` is an equality over `git ls-files -s` for
both prefixes (546 tracked files, all `100644`, with a `>= 500` population floor so the corpus
cannot silently shrink), and its own failing control is one assertion inside the exemption's control
test, where a `0755` file under an exempted prefix exists and must be seen (`M-T`/`M-S` kill it).

### Renames (nothing retired)

- `test_nothing_in_the_tree_sets_the_override_for_a_run` ->
  `test_nothing_in_the_tree_sets_either_of_the_guards_env_switches`; same assertions, widened, and
  the old name is recorded in the new docstring so CARD-255's record still resolves.
- `_override_offenders` -> `_scan_offenders` (it now filters hits for both switches). `OVERRIDE_NAMERS`,
  `OVERRIDE_PROSE` and `PROSE_SHAPES` are untouched, as the card required.
- New `_scan(cwd)`: one definition of the scan for the tree and for its control, so AC-2's mutant is
  a single edit that reds the control.

### Test selections

| selection | result |
| --- | --- |
| `tests/test_full_suite_lock.py` | 41 passed |
| `tests/test_full_suite_lock.py tests/test_guard_integrity.py` | 172 passed |
| `tests/test_clues.py` (an ordinary selection, variable unset) | 386 passed, nothing added to the output |
| `tests/test_card_109_database_guard.py` (the conftest wiring) | 19 passed |
| the same four, 22 times, under the mutation harness | the matrix above |

`DATABASE_URL`/`TEST_DATABASE_URL` both set to the derived
`nonogram_pythonproject4_card_256_c360f3e725e2_test`; DB-mode tests skip because it does not exist
on this host. No timing measurements taken (CARD-257 live on this machine). `nonogram_poc` never
touched.

- **[Orchestrator] wave 49's three new rules were applied at the *implementation* station and they
  worked on the first card to carry them.** The per-assertion instrument was built as specified —
  every `ast.Assert` at any depth, keyed on its own `lineno`, **21 mutants all line-count-preserving**
  — and it reports something no per-test run can: **baseline all 41 assertions PASS and are reached,
  and no assertion reports NOT-REACHED under any mutant.** That sentence is the whole point of the
  rule: without it, "this control is green" and "this control never ran" are the same observation.
- **[Orchestrator] the card's optional item was taken, and it is the better half of the result.** The
  mode axis is **closed rather than exempted**: an equality over `git ls-files -s` for both prefixes
  (546 tracked files, all `100644`, with a ≥500 population floor), and its *own* failing control is
  an assertion inside the exemption's control test, where a `0755` file under an exempted prefix must
  be seen. So *"prose, never anything a shell can run"* is now **true with a control** instead of
  narrowed into a disclaimer — the opposite of how this family has usually ended.
- **[Orchestrator] no new exemption was added, which was the card's second trap.**
  `OVERRIDE_NAMERS`, `OVERRIDE_PROSE` and `PROSE_SHAPES` are exactly as CARD-255 left them, and the
  union scan adds no hit outside the eight already-exempted files. The widening and the control share
  **one** `_scan` definition, so AC-2's mutant is a single edit that reds the control — rather than a
  widened predicate paid for with an exemption, which is precisely what CARD-255 cycle 2 gated on.
- **[Orchestrator] M-M is killed two ways now**, and the second is the interesting one: the
  exemption's control plants prose-shaped setters **outside** both prefixes (`ci/forge-ci.yml`,
  `.github/workflows/suite.yml`, `docs/running-the-suite.md`) and asserts they are offenders. Under
  M-M the exemption becomes "any `.md`/`.yml` anywhere" and both the union assertion and the
  dedicated one red. CARD-255's own F-202 survivor is dead.
- **[Orchestrator] the residuals are stated, including one that survives.** **M-Q survives** —
  `current_verdict` returns before calling `verdict` when there is no lock, so that branch is
  unreachable from a real run, and the same edit one level up (M-Q2) is killed. It is recorded as a
  surviving mutant that changes nothing observable, not as a hole and not as a kill. Likewise
  `"\n".join(lines) or None` is named an **equivalent** mutant. A report that names its equivalent
  mutants is one I can read.
- **[Build gate 1 — FAILED, and it is the `@ops` hazard, on a tree that carries the fix]** `28de78d9`,
  solo: 5 failed, 8622 passed, 16:32. All five in
  `tests/test_admin_binding.py::TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine`, with
  **10 occurrences of `relation "puzzles" does not exist`** — the signature verbatim, and the same
  five parametrisations CARD-253's build gate 1 failed on in wave 48. The count reconciles (8622 + the
  5 tests this card adds = 8627), so nothing was lost; these are failures, not absences.
- **[Why this one matters beyond this card]** `src/nonogram/db/session.py:201` defines
  `reset_engine()` and `tests/conftest.py:528` calls it — **CARD-252's fix is present and wired in
  this tree.** When that card merged I recorded, deliberately, that merging it did **not** establish
  that it stops the hazard, because CARD-253 had gone red then green on the same commit *without* the
  fix, and "a single green gate cannot distinguish a fix working from a failure not appearing". The
  answer was owed to the next several waves' gates. **This is the first one, and it is a red.**
- **[The measurement that decides what it means]** a re-run on the **same commit**, solo, is running.
  Green ⇒ the class is still intermittent *with* the fix in place, which means `reset_engine()` did
  not remove it and CARD-252's own docstring — already careful to say the four waves of failures
  "remain unexplained" — stays exactly as honest as it was. Red again ⇒ something in this card's tree
  reproduces it deterministically, which would be the first reproducible instance this board has ever
  had and worth far more than this card.
- **[Build gate 2 — PASSED, same commit]** `28de78d9`, solo: **8627 passed**, 1 skipped, 16:08,
  EXIT=0. 8622 + 5 = 8627, so gate 1's five failures are gate 2's five passes. **The card's own code
  is clear**; the gate passes on this run.

### The answer owed since CARD-252 merged: `reset_engine()` did not stop the hazard

Red, then green, on **the same commit**, on a tree where `reset_engine()` is defined
(`session.py:201`) and called (`conftest.py:528`). That is the same red-then-green shape CARD-253
produced in wave 48 **without** the fix. So:

- **The `@ops` class survives CARD-252.** Four waves of gate reds were attributed to a hazard that
  card was expected to remove, and the first gate to hit it afterwards behaves identically.
- **CARD-252 was never wrong, and this is why its wording matters.** Its AC-3 was **withdrawn** with
  a measuring survivor, and its docstring says the four waves of irreproducible failures **remain
  unexplained**. Every cycle's instinct was to let that card claim the cure; the claim rule stopped
  it three times. Had it shipped the cure claim, this gate would now be evidence of a regression in
  a fix that never fixed anything — instead it is evidence about the hazard, which is what it is.
- **What stops now**: attributing a red to "the known `@ops` hazard, which CARD-252 addresses". The
  honest attribution is "the known `@ops` hazard, cause unknown, unaffected by the engine disposal".
- **What starts**: CARD-258, which does not guess at a cause — it makes the **next** occurrence say
  which database, which engine and which process the failing connection was attached to. Four waves
  of this class have produced one signature and no data.

### [Review 1/3] Score: 8.5 — FAILS the severity gate (one open Important)

Report: `meta/review/CARD-256-cycle1.yml` (6 findings, all `status: open`). Score 8.5 ≥ min_score 8, but
**one open Important fails the card regardless of score.**

- **F-001 — Important, gating — ADR-0039/R1.** The record states **M-Q as a measured survivor**. It is
  not: `verdict` is unit-tested directly (`test_full_suite_lock.py:103`, `guard.verdict(None, …)`
  asserting `allowed is True` and `said is None`), so mutating the no-lock branch **reds 6 of 41
  tests**. The *unreachability-from-a-real-run* half of the claim is true and stands; the *survival*
  half is false.
  Root cause is the matrix's scope, not the mutant. The record claims "every `ast.Assert` at any
  depth" and "all **41** assertions PASS and reached" — but **41 is the collected test count**
  (36 → 41). The file holds **129** `ast.Assert` nodes at HEAD (111 on main, +18 from this card), and
  the ten tests the matrix names hold 38. So the matrix was measured against an **undeclared subset**
  which excludes exactly the arm that kills M-Q — and the instrument is in neither the diff nor the
  tree, so the figure cannot be re-derived at all.
- **F-002** (Minor) the absent redirection mutant is justified by a premise G-5 does not state (G-5
  forbids create/modify/delete, not reading), and the redirection *is* controlled in-process by
  `test_the_lock_path_is_injectable_so_a_test_never_touches_the_real_one:742` — the record understates
  its own coverage.
- **F-003** (Minor) the `PROSE_SHAPES` comment census "256 `.md` and 286 `.yml`" is stale (258/288) and
  has no recomputing control; this card rewrote that block and updated the neighbouring 546 but not the pair.
- **F-004** (Minor) "8622 + the 5 tests this card adds = 8627" conflates the 5 added tests (already
  inside the 8622 passes) with gate 1's 5 *failures*; gate 1's line also omits the skip gate 2 reports.
- **F-005** (Minor) the two `conftest` substring assertions cannot fail while `assert not offenders`
  above them passes; their one genuine independent reach — an **untracked** conftest — is undeclared.
- **F-006** (Minor) the two real-process silence assertions were narrowed to a hand-enumerated
  three-phrase list; the enumeration is now the bound and is not declared as one, and each loop is one
  `ast.Assert` over three phrases, so it short-circuits.

**Nine figures recomputed and held**, which is worth recording beside the one that did not: 546 tracked
files under both prefixes all `100644` (main 547); the `>= 500` floor; 41 **tests**; 21 mutants as a
count; the **seven**-name skip set with independent reach two; the `co_code` identity table **exactly**
(only `<module>` and `pytest_configure` differ, `redirect_note` is new, **17** shared code objects
byte-identical — the card lists 16, omitting compiler-generated `__annotate__`); "no new exemption, the
three sets as CARD-255 left them" verified **against the diff, not the prose**; and "the union scan adds
no hit outside the eight exempted files" (8 hits, 3 namers + 5 prose, 0 offenders).

**Residues judged:** the `"\n".join(lines) or None` equivalent mutant **accepted** (both consumers filter
falsy; nothing asserts `report_line() is None`). The absent-redirection-mutant *reasoning* **rejected**,
conclusion harmless. The declared trap **avoided** — the shipped tests assert the run *says* it was
redirected, and the reviewer killed the announcement two ways (M-A, M-B) rather than reading it.

**Five adversarial false positives dropped** before filing. System contract: ADR-0039/R2 and R3 hold
(both derived sets recomputed, both default to DENY; mode axis closed by an equality over today's 546
sites with its own failing control); ADR-0039/R1 violated by F-001; ADR-0038/R7 and R8 `no_eligible_fact`.

**[The rule that caught it, and the direction it failed in]** Wave 49 promoted per-assertion measurement
with a line-count-preserving instrument. This is the first card to carry it at the *implementation*
station, and it failed in the mirror image of last wave's failure: not a never-reached assert read as a
kill, but a **never-measured assert read as a survivor**. The claimed scope ("every `ast.Assert` at any
depth") was the right scope; the number beside it was a different quantity. Both waves' defects are the
same shape — *a measurement whose domain is not the domain it is reported over*.

### [Fix 1] `f2236045` — the full-set instrument moved FIVE of the card's 21 rows, not one

Commit `f2236045` on `card/256-the-lock-path-var-gets-a-control`, pathspec
`tests/test_full_suite_lock.py` only — 1 file, **+85/−11**. `tests/full_suite_lock.py` and
`tests/README.md` needed no change and are not in it (a subset of `Touches`, no drift; the README was
checked and names no census figure and no renamed helper). Nothing under `meta/` in the commit.

**Node counts — the figure that recomputes, replacing the one that did not.**

| tree | `ast.Assert` nodes in `tests/test_full_suite_lock.py` |
| --- | --- |
| main `c1d65cd2` | **111** |
| `28de78d9` (implementation) | **129** — the card adds **18** |
| `f2236045` (this fix) | **130** (+1, the new shape equality) |

The card's **41 is the collected test count** (36 → 41), re-confirmed as 41 collected / 41 passed. It is
not an assertion count and is no longer stated as one.

**Baseline over all 130 nodes: 130 PASS and reached, zero NOT-REACHED.** 23 mutants (the card's 21, plus
**M-TP** for this fix's own addition and **M-RD** for F-002(a)), each run **twice** — instrumented for
per-assertion attribution, and plain, because the recording wrapper suppresses `AssertionError` and would
let a child pytest report `1 passed` and hide real-process propagation.

**F-001 — closed, and the correction is larger than the finding. Five rows moved:**

1. **M-Q is killed, not surviving** — **recording pass** `:105`, `:106`; **plain pass** `:105`, `:1067`,
   `:1104`, `:1115`, `:1136`, `:1167`, one per failing test; **union** `:105 :106 :1067 :1104 :1115 :1136
   :1167` (corrected at fix 2 — the original row gave only the recording pass's two). **M-Q is the only
   mutant of the 23 whose kill reaches the child process** (`child_fails` is `[105]` for M-Q and `[]` for all
   22 others), which is why its was the only row *under*-attributed rather than merely short-attributed. In
   `test_no_lock_file_is_the_ordinary_case`, and
   **6 of 41 tests** red in a plain run, reproduced solo twice. Both linenos sit above every edit in this
   fix, so they hold for `28de78d9` too. The *unreachability-from-a-real-run* observation about
   `current_verdict` stands on its own and needed no survivor to be true.
2. **M-Q2's row was wrong, and the mutant is bigger than a row.** The card said it kills the no-verdict
   phrase. Measured: **no assertion runs at all.** `current_verdict()` refuses on *every* pytest, so the
   measuring run aborts in `pytest_configure` — `ERROR: Refusing to start`, **exit 4, 0 collected, all 130
   asserts NOT-REACHED**. The mutant is detected maximally loudly, and by **nothing in the matrix**.
3. **M-A kills one arm of that unit test, not four.** Only `:820` (`note is not None`) — and, added at fix
   2 for scope: M-A also reds `:1138` in **both** domains and `:1141` in the recording pass.
   `:821`/`:822`/`:825` are
   **NOT-REACHED**, because with `note is None` the next line raises `TypeError` rather than
   `AssertionError`, so the test errors and the remaining arms never run. Test-level coverage is intact;
   the attribution was wrong. **This is the instrument's own hazard appearing inside its own output** —
   and only a per-assertion run with NOT-REACHED reporting can see it.
4. **M-F reds 6 arms in the recording pass across 3 tests, not 3** (`:133`, `:134`, `:152`, `:1067`,
   `:1068`, `:1071`; a plain run gives `:133 :152 :1067` — the same 3 tests red). The
   refusal case stays green, so CARD-255's pair holds as recorded.
5. **M-R2 has two kills the undeclared subset could not see** — `:1107` (`"stale" in combined.lower()`) and
   `:1118` (`guard.OVERRIDE in combined`), 4 tests red in a plain run: the widest real reach in the set.

**14 of the card's 21 rows reproduce exactly.** And **`:1174` is killed by nothing in the 23-mutant set**,
and its control is **not** dead — but the reason first given for that was exactly backwards, and is
corrected at fix 2. **M-1174** (new row) makes `current_verdict`'s no-lock branch return one of the three
*enumerated* phrases and reds `:1174` **alone**: 1 failed, 40 passed, the failure reading
`a run with no lock in sight reports a verdict: 'stale'`. What `:1174` **cannot** see is a **fourth**
phrase — which is F-006's bound (a), measured here too: **M-4B**, the same branch returning a phrase in no
list, leaves all **41 green** while printing that phrase twice in the measuring run's own output. *The
original sentence named as the killer the one thing the assertion provably cannot notice.*

Two rows follow from that, and the second repairs an implementation-matrix row fix 1 only half-corrected —
the original matrix attributed `…tree_with_no_lock…` / *no verdict phrase* to **M-Q2**, which collects
nothing at all, so that row was **empty**, not merely wrong:

| test | assert | killed by |
| --- | --- | --- |
| `…tree_with_no_lock_runs_exactly_as_it_did_before` | no verdict phrase (`:1174`) | **M-1174** — *not* M-Q2, which aborts before collection and reds nothing |
| (deliberately green, the measured form of F-006's bound (a)) | the same assert | **M-4B** — a *fourth* phrase, in no list: 41 passed |

Both are one-line, line-count-preserving substitutions on the same `if text is None: return True, None`
that M-Q2 targets.

**Two measurement domains, named — and the bound stated in each.** *(This paragraph replaced an earlier one
that said "84 of 130 assertions are killed by no mutant in this set"; that was the recording pass's number
stated as if it were the mutant set's. Corrected at fix 2, measured by two new passes over the same 23
mutants, neither of them the recording pass, agreeing with each other on all 26 rows.)*

Every per-assertion figure in this record comes from one of two passes, and they do not see the same things.

- **The recording pass** (the instrument): each `ast.Assert` is wrapped in a `try/except AssertionError` that
  **records and continues**, so within a test every arm is measured independently and no short-circuit can
  hide one — which is what it was built for. The price is suppressed propagation: **an assertion whose truth
  depends on a child pytest's outcome cannot record FAIL at all.** The real-process cases run `SELECTION` —
  one test out of *this same instrumented file* — in a child process, so under **M-Q** the child's `:105`
  fails, the wrapper swallows it, the child reports `1 passed` with rc 0, and the parent's `returncode == 0`
  premises record **PASS by construction**. Declared as **a bound on the instrument**: in the recording pass
  *reached* means reachability-under-suppressed-`AssertionError`, strictly wider than a plain run's, and
  **PASS is not evidence of a surviving assertion for any arm that reads a child's outcome** — there, PASS is
  an observation that pass cannot fail to make.
- **The plain pass** (no instrumentation, `--tb=line`): true propagation and true cross-process semantics, at
  the price of exactly one failing lineno per failed test — every arm after the first failure in that test is
  never reached, so it attributes nothing to them.

Neither pass alone is the kill set; the **union** is.

| domain | assertions with a FAIL | killed by no mutant |
| --- | --- | --- |
| recording pass | **46** | **84** |
| plain pass (`--tb=line`) | **33** | 97 |
| **union of both** | **50** | **80** |

**17 linenos are kills only the recording pass can see** — `:106 :134 :620 :621 :689 :694 :742 :854 :975
:976 :977 :978 :1068 :1071 :1091 :1092 :1093`: the test had already aborted on an earlier arm, so the
assertion *is* controlled and only its **attribution** needs the instrument. **Four are kills only a plain
run can see** — `:1104 :1115 :1136 :1167`, all M-Q, and all four exactly the `rc == 0` premises the old
record dismissed as *"they establish that the run happened"*. Those four are the ones that matter, because
for them the recording pass did not report NOT-REACHED — it reported **PASS**.

**So: 84 of 130 record no FAIL in the recording pass; 80 of 130 are killed by no mutant in this set in
either domain.** The reason stands, re-checked by mapping all 80 to their enclosing tests: overwhelmingly
CARD-255's pure-function arms — 10 in `test_same_tree_is_exact_identity…`, 10 in `test_a_value_that_is_not_
an_absolute_path…`, 5 and 5 in the foreign-lock and relative-worktree refusals, the stale/threshold/
future-stamp rules, the two age fallbacks, the skip-API pair — which these 23 mutants were never aimed at.
Four of the 80 are the `"1 passed" in combined` companions of the arms just recovered (`:1105 :1116 :1137
:1168`): unkilled in **both** domains — suppressed in the recording pass, never reached in the plain one —
and their only control is the test-level signal, 6 of 41 tests red under M-Q.

**The distinction in one sentence, which is the whole of F-007:** *an instrumented-only kill is an
attribution the plain run cannot make; a plain-only kill is an observation the instrument cannot make — and
only the second kind corrupts a figure.*

**F-003 — the census is DELETED, not corrected.** A number in a comment has no control, and this population
moves faster than a card does: the comment said **542** when this card was drafted. The figure on main was
read **three** times inside this one wave and was different every time — 550, 551, 552 — so **no live main
figure is quoted here any more**; the claim is held by the equality at `:750`. The one census figure left in
the record is **546, the tracked population under both prefixes at `f2236045`** (suffixes exactly
`{.md, .yml}`), stated as the population the equality was measured over, with the `>= 500` floor as its
control. *A tree-pinned figure is the only kind worth keeping.* What the figure claimed is now held by an equality at **`:750`**: the suffixes
git tracks under both prefixes are exactly `PROSE_SHAPES`, measured **out of the same `git ls-files` call**
as the mode equality (`_tracked_modes` → `_tracked_index(cwd)`, returning `(mode, path)`), so the two
equalities can never be measured over different populations. No new uncontrolled number replaced it. The
`>= 500` floor and its "(546)" were recomputed and left alone — 546 is stated as the population the
equality was measured over, with the floor as its control.

Mutants over the fix's own additions: `:750` red by **M-TP** (deletes the path half of the one `ls-files`
call the claim names) and **M-Y**, plus M-X and M-S **in the recording pass** (in a plain run those tests
abort earlier, at `:736`); **M-T** (the mode half) leaves it green **in both domains** — so M-T and
M-TP **isolate the two halves of that one return** rather than certifying the addition. `:698` (changed
call site), `:736`, `:742` keep their rows unchanged: the rename weakened nothing.
**`OVERRIDE_NAMERS`, `OVERRIDE_PROSE` and `PROSE_SHAPES` keep exactly CARD-255's values**, verified by diff
— no `+`/`-` line touches any of the three assignments; the change above `PROSE_SHAPES` is comment-only,
stated explicitly as F-003 requires. No exemption added, none widened.

**F-005 — declared as a measurement, not an argument.** `tests/conftest.py` is tracked and unexempted, so a
conftest naming either switch would already be in `offenders` and `:614` would fail first — and the
instrument agrees: every mutant reddening either arm (**M-K** → `:621`, **M-K2** → `:620`, both
**recording-pass** attributions — a plain run reds `:614` **alone**, with both arms NOT-REACHED, which is
precisely the subsumption the new docstring declares) reds `:614` too,
and **no mutant in the set reds an arm on its own**. The one independent reach — an **untracked** conftest,
which `git grep` cannot see and `read_text` can — is declared as a bound **the test cannot create** (it
would have to untrack a file in the live tree), not claimed as coverage.

**F-006 — both bounds declared, and the declaration now makes a falsifiable prediction.** (a) The three
phrases are a **closed enumeration** of what `verdict()` returns today — `"Refusing to start"`,
`"running anyway"`, `"stale"` — so a fourth message would be printed on a self-run or a no-lock run and
**neither test would notice**; the old `"full-suite lock" not in combined` form could not drift that way but
is unusable here, because every real-process case now carries the redirect note, which opens with that
phrase. (b) Each loop is a single `ast.Assert`, so a plain run stops at the first phrase that fails.
Backed rather than asserted: `:1071` is red by M-F, and `:1174` by nothing in the set.

**F-002(a) — confirmed by measurement.** **M-RD** (deletes the redirection so `lock_path()` ignores
`LOCK_PATH_VAR`, line-preserving) reds `test_the_lock_path_is_injectable_so_a_test_never_touches_the_real_one`
at **`:795`** and **10 of 41 tests**. The record understated its own coverage, and no real-process mutant is
needed. **G-5 is not implicated either way**: under M-RD the probes *read* the board's lock path (checked
absent) and never create, modify or delete anything there — so the record's premise "which G-5 forbids" is
not what G-5 says.

**F-004(b) — confirmed by arithmetic rather than a run.** Collection is deterministic for the same commit,
host and invocation. Gate 2: 8627 passed + 1 skipped = **8628 collected**. Gate 1 as recorded: 8622 passed
+ 5 failed = 8627 = 8628 − 1 — so gate 1 **also had 1 skipped and its line omits it**. With the skip
restored the two reconcile exactly: 8628 collected both times, gate 1's five failures are gate 2's five
passes, and the card separately adds 5 tests (36 → 41). Declared bound: the absolute totals could not be
re-derived (a full suite is forbidden outside a gate) and the skipping test was not identified.

**[A pre-existing red, with its control, not attributed to this card]** `tests/test_db_isolation.py` reds 3
tests in a targeted selection (`…never_existed_is_created_and_migrated`, `…absent_database_skips_rather_
than_fails_with_no_server`, `…two_trees_pass_concurrently_and_the_same_pair_reds_when_they_share`). **The
identical 3 fail on unmodified main at `c1d65cd2` with the same env**, so they are this host's Postgres
environment, not this tree and not this fix. Cause not investigated. Worth noting that main's gates are
green at full-suite scope, so this is selection-dependent — and worth noting too that the control was run
*before* the attribution, which is the part the `@ops` class never got for four waves.

**[Touches-drift note, nothing to commit]** the matrix above referenced `_tracked_modes`; the helper is now
`_tracked_index`. Corrected here.

**[The instrument, and why it is not committed]**
`/private/tmp/claude-501/-Users-omelnikova-PycharmProjects-PythonProject4/e6396d39-0b74-4498-9018-df045632a00c/scratchpad/c256fix/kill_matrix.py`,
with `report.py`, `matrix.txt`, `results-sweep.json`, `results-rerun.json`, `sweep.log`,
`runs/<MUTANT>-{instr,plain}/pytest.out` and `apply_fixes.py` beside it. It refuses to start if the board's
real lock exists; takes `cp -p` backups and reads all later content from them, never from git; applies one
mutant as an exact substitution asserting it occurs **exactly once** and that the file's line count is
**unchanged**; applies it to the **pristine** source *before* instrumenting, so the linenos keyed on
afterwards are the committed file's; rewrites **every** `ast.Assert` at any depth into a recording
`try/except/else`, verified by asserting the transformer's node list equals an independent `ast.walk`
enumeration; records **per-pid**, because the real-process cases start child pytest processes running one
test from this same file; and restores every file verified with `diff -q` **and** `shasum -a 256`.
**A new file is outside the card's three `Touches` paths, so committing it would be touches drift.** The
figure is reproducible from that path for as long as the directory lives, and **not from the tree** — a
declared bound, not a hidden one. *Commit the instrument once, as its own card* goes to the retrospective:
three agents have now built it independently and each hit a different trap first.

### [Review 2/3] Score: 8.0 — FAILS the gate on TWO new Importants, both made by the fix's record, not its code

Report: `meta/review/CARD-256-cycle2.yml`. **All six of cycle 1's findings carried forward as `fixed`,
`fixed_in: f2236045`** — F-001 is genuinely closed on substance. **F-007 and F-008 are new, Important,
both ADR-0039/R1.** Both are **record-only**: no code moves, no test changes, so cycle 3 is cheap — but it
is needed, and cycle 3 is the last.

**The fix's code survived every kill attempt**, which is what makes the diagnosis precise. `M-TP` reds the
new `:750` assertion **alone** — not subsumed, not a control that cannot fail. `M-T` reds `:698` alone and
leaves `:750` green, so the two halves of the one `ls-files` call really are isolated. And the reviewer's
own **M-WIDE** (widen `PROSE_SHAPES` by one shape) reds `:750` **and** `:685` — so the shape exemption now
carries ADR-0039/R3's must-not-absorb control, **which it did not have before the fix.** A genuine
strengthening. One equivalent mutant noted and correctly not filed: the tab-split in `_tracked_index` is
indistinguishable from `split()[3]` in today's tree (0 tracked paths under either prefix contain a space),
and the docstring states it as a *reason for the choice*, not as something a test catches.

**Verdict on the instrument: all five of its numbered claims hold** — and not on its own word. Every
`ast.Assert` at any depth is reached (the missing `generic_visit` inside the visitor loses nothing, since
an `Assert` statement cannot contain an `Assert`), cross-checked against an independent `ast.walk`, and
**corroborated twice independently: the reviewer's own `ast.walk` count is 130, and a `sys.monitoring`
LINE tracer — a wholly different mechanism — reached all 130 linenos.** Pristine-first with three real
guards (`count(old)==1`, equal newline counts, equal `splitlines()` length), verified by applying 11
mutants by hand under the same guards. Per-pid holds and the rationale is real. Plain runs too, and they
were decisive. `cp -p` + `diff -q` + `shasum -a 256`, with **no git command anywhere in the file**.

**But it has one undeclared limit, and that limit is the finding.**

---

**F-007 — Important, gating — ADR-0039/R1.** The recording wrapper catches `AssertionError`, so under a
mutant the **child** pytest runs the *instrumented* file: the child's assert fails, the wrapper swallows
it, the child reports **`1 passed` with rc 0**, and the parent's real-process premises therefore record
**PASS**. The fix named this mechanism for *test-level* results — it is exactly why it added the plain
passes — and **never drew the consequence for its own per-assertion figures.**

Measured cost: at least **four** of the 84 (`:1104`, `:1115`, `:1136`, `:1167`) are reddened by **M-Q in a
plain run** and recorded **PASS** by the instrument. So **84 is an upper bound** — at most 80 — and the
four counterexamples are precisely the premises the record dismissed as *"they establish that the run
happened"*. The matrix also under-attributes every real-process arm: it gives M-Q `:105/:106`, where a
plain run gives M-Q `:105, :1067, :1104, :1115, :1136, :1167`.

The number itself recomputes **in the domain it was measured in** (46 FAIL / 84 no-FAIL of 130, derived
independently from `results-sweep.json`), and the *reason* is largely right — all 84 mapped to their
enclosing tests, the great majority CARD-255's pure-function arms, and of the 26 assertion entries this
card added or reshaped only three sit in the 84. **None of the 84 is a genuinely uncontrolled claim of this
card.** So the honest statement is **the number, the reason, AND the domain** — plus the plain-domain
kills, which cost one flag to recover (`--tb=line` on the existing plain pass).

**F-008 — Important, gating — ADR-0039/R1.** The record says `:1174` is unkilled because *"only a new
verdict phrase would red it, which is precisely the enumeration bound F-006 declares"*. That is **false,
and self-contradictory in the same commit**: a fourth phrase **cannot** red it — that *is* F-006's bound —
while what does red it is an **enumerated** phrase reaching a run that should have none. The reviewer's
**M-1174** reds `:1174` **alone**. So "unkilled by this set" is true, "not a dead control" is true, and
the reason given for both was the wrong mechanism.

---

**F-006's prediction was TESTED and CONFIRMED**, which is the part of the fix that earned its keep. Fourth
phrase on `verdict()`'s self-run branch → `test_a_gate_running_under_its_own_lock_is_not_refused` **green**
(the only red is the *unit* test at `:133/:134`, which the declaration does not speak for). Fourth phrase
on `current_verdict()`'s no-lock branch → **41 passed**, with the new phrase printed in the measuring run's
own output and **nothing in the file noticing** — wider than declared, but consistent with it. Bound (b) is
visible in the AST (one `Assert` node each at `:1071`/`:1174`) and in every plain run.

**Eleven independent probes, nine plain-run rows re-run and matching exactly.** M-Q (6 of 41, the exact
six), M-Q2 (rc 4, nothing collected, one ERROR line), M-A (2 tests red, only failing arm `:820`), M-R2 (4
red, `:1107` and `:1118` among the failing arms), M-RD (10 of 41, arm `:795`), M-TP, M-T, M-K — all agree.
**Two disagreements**, both now findings: every real-process arm is under-attributed, and the `:1174`
reason.

**Node counts and baseline, re-derived not carried:** **111 / 129 (+18) / 130 (+1)**. `41` is the collected
test count — 36 on main, 41 at HEAD by `--collect-only` — and **the fix states it nowhere as an assertion
count.** Baseline **130 of 130 PASS and reached, zero NOT-REACHED**, taken from the `sys.monitoring` tracer
rather than from the instrument.

**G-1 verified rather than assumed:** `tests/full_suite_lock.py` is **byte-identical** at `28de78d9` and
`f2236045` — same blob sha `7b90cad0` at both, matching the worktree — so **G-1 needs no re-derivation**.
`OVERRIDE_NAMERS`, `OVERRIDE_PROSE` and `PROSE_SHAPES` read verbatim and identical at **all three**
commits; no `+`/`-` line touches any of the three assignments; the change above `PROSE_SHAPES` is
comment-only. **No new exemption, none widened.**

**The `test_db_isolation.py` attribution is CONFIRMED.** The identical 3 fail in the worktree **and** in
the unmodified main checkout, same env, 48 passed in both, same three names — and `tests/`, `src/` and
`pyproject.toml` are byte-identical between `c1d65cd2` and main HEAD, so the control is clean.
Pre-existing, environmental, selection-dependent; **not a regression this card introduced.** Cause not
investigated.

**Noted, not filed: main's population today is 551, not the 550 the fix's narrative states.** It drifted
*within this wave*. That is the fix's own argument about uncontrolled numbers turning on the fix — and
precisely why the controlled form is the `:750` equality. Recomputed and held: 546 in the worktree, all
mode `100644`, suffixes exactly `{.md, .yml}`, the `>= 500` floor intact, 8 scan hits all exempted, 0
offenders. **Seven more adversarial false positives dropped**; the ledger is not extended by anything
unreproduced.

**System contract:** ADR-0039/R2 ✓, ADR-0039/R3 ✓ (**strengthened**), ADR-0039/R1 ✗ (F-007, F-008),
ADR-0038/R7 and R8 ⚠ `no_eligible_fact`.

**[The family, and the decision not to escalate]** Three gating findings on this card, and **all three are
one shape: a measurement reported over a domain that is not the domain it was measured in.** Cycle 1: `41`
was a collected test count stated as an assertion count. F-007: `84` is an instrumented-domain figure
stated as a property of the mutant set. F-008: a stated *reason* that a run refutes. By
`review.family_regression: on` **both preconditions are met this time** — cycle 2's new gating findings
*are* attributed to the previous fix, and they fall in one family (the card's record claims about its own
measurements). I am **recording the family and not escalating to the decompose station**, because nothing
about this card's slice, design or terms is wrong: the code is sound and certified, the remedy is two
one-paragraph corrections whose exact content the reviewer has already measured, and cycle 3 certifies
them. Escalating would buy a human decision about a question that is already answered. **Surfaced at the
wave boundary rather than buried here**, because the owner should see that a fix station can produce two
gating findings while its code survives every mutant aimed at it.

**[What this says about the instrument rule, one wave after promoting it]** Wave 49 promoted *per-assertion
measurement with a line-count-preserving instrument*. Wave 50 has now found **four distinct ways the
instrument lies**, each discovered by a different agent: the line-numbering shift (wave 49), reporting a
**test count** as an assertion count (cycle 1), **last-write-wins aggregation** losing a RED from an assert
inside a `for` loop (CARD-257 cycle 1), and now **the recording wrapper suppressing propagation so a child
process reports `1 passed`** (F-007). The rule needs its own clause: *an instrument has a domain, and the
domain is part of every figure it produces.*

### [Fix 2] no commit — both findings were record claims, and the record is `main`'s file

**Nothing committed; no repo file created, modified or deleted.** `git status` in the worktree shows `tests/`
clean. F-007 and F-008 were claims *about* measurements, so the fix is the corrected text, applied in place
in the `[Fix 1]` section above. HEAD stays `f2236045`.

**The method is the deliverable.** Rather than re-run the recording pass, fix 2 ran **two new passes over the
same 23 mutants, neither of them the recording pass**, and they agree with each other on all 26 rows:

- a **plain pass** with `--tb=line` — true propagation, one failing lineno per failed test;
- a **re-raising pass** — the handler records **and re-raises**, so the semantics are plain semantics while
  reachability is still reported.

That matters because of what CARD-257 found this same wave: **reproducing a figure with the original method
only confirms the method.** Two new domains is the answer to that, not a third run of the first one.

**What the re-raising pass bought, beyond agreement:**
- a **third independent baseline** — 130 of 130 PASS, **0 NOT-REACHED**, under true propagation (cycle 2
  corroborated the baseline with `sys.monitoring`; this is a third mechanism);
- **its own control, which can fail**: a handler that forgot the `raise` would show M-Q's outer row as
  `{105}` with the four premises PASS — that is, the recording pass's row. It did not;
- **plain-domain reachability**, which `--tb=line` cannot report: under M-Q, 6 FAIL / 107 PASS / **17
  NOT-REACHED**, and the NOT-REACHED set contains `:106`, `:1105`, `:1116`, `:1137`, `:1168` — the arms the
  recording pass measures as kills or as PASS. The complementarity as a measurement rather than an argument;
- **child-process attribution** — the child pid's `FAIL` at `:105` under M-Q: the F-007 mechanism caught in
  the act.

**The sibling audit.** Every other per-assertion figure in `[Fix 1]` was checked against both domains.
**Naming the domain is all any of them needs**, with one wanting a scope word (M-A). All are now labelled
above: M-Q both domains plus union; M-Q2 holds in both; M-A scoped to its unit test, with `:1138` in both
domains and `:1141` recording-only; M-F recording-pass arms vs 3 plain tests; M-R2's `:1107`/`:1118` in both
domains; F-003's `M-TP`/`M-T` in **both** domains (the load-bearing half) with `M-X`/`M-S` recording-only;
F-005's arms recording-only, a plain run redding `:614` alone — which *strengthens* the subsumption the
docstring declares.

**22 of 26 rows lose attribution in the plain domain** (M-X 8→3, M-RD 14→7, M-F 6→3, M-S 4→2, M-A 3→2,
M-Y 5→3, M-R2 5→4, M-K/M-K2/M-1/M-M/M-C 2→1). That is **short-circuit, not suppression** — and the whole
basis for calling those figures under-labelled rather than wrong. **M-Q was the only one actually wrong,
because its missing kills were suppressed (reported PASS), not short-circuited (reported NOT-REACHED).**

**Safety discipline, stated because 52 runs of file mutation deserve it:** board-lock check **before and
after every run**; `cp -p` backups of all three mutated files with all later content read from the backups;
the three substitution guards (occurs exactly once / equal newline counts / equal `splitlines()` length);
restore in a `finally` verified with `diff -q` **and** `shasum -a 256`; **52/52 runs reporting a verified
restore**; post-sweep sha256 byte-identical to pre-sweep; `git status -- tests/` clean; and **no git command
anywhere in the probe** — the only git used was read-only.

**The `_tracked_index` tab-split equivalent mutant was left alone, as briefed, with no control invented for
it.** Probe: `/private/tmp/claude-501/-Users-omelnikova-PycharmProjects-PythonProject4/e6396d39-0b74-4498-9018-df045632a00c/scratchpad/c256fix3/plain_lines.py`
with `results-plain-reraise.json` and `runs/<MUTANT>-{plain,reraise}/pytest.out`.

**[What this card is actually about, in the end]** It was carded as *the lock path var gets a control* — a
0.25d trivial. Its code shipped sound at `28de78d9` and has not changed since except one comment-and-assertion
commit. All three gating findings were about **how the card described its own measurements**, and the wave's
durable output is a rule the board did not have: **an instrument has a domain, and the domain is part of
every figure it produces.** Four distinct ways a per-assertion instrument lies were found in this one wave,
each by a different agent: the line-numbering shift (wave 49), a **test count** reported as an assertion
count (cycle 1), **last-write-wins** aggregation losing a loop-interior RED (CARD-257 cycle 1), and
**suppressed propagation** making a child report `1 passed` (F-007) — with a fifth on CARD-257, a **leaked
patch** that looks identical to a real kill.
