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
