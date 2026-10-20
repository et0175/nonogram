# CARD-255: A pytest run refuses to start while another worktree holds the full-suite lock

**Status:** in_progress
**Priority:** P1
**Category:** ops
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/255-full-suite-lock-is-enforced
**Worktree:** ../PythonProject4-card-255
**Source:** wave 48 retrospective, owner decision 2026-10-20 — "the full-suite lock gets enforced in conftest.py", after CARD-225's build gate 2 shared its window with a browser suite and reported two failures that were not the tree.
**Idea:** —
**Wave:** 49
**Depends on:** —
**Touches:** tests/conftest.py, meta/kanban/.full-suite.lock (format only), tests/test_full_suite_lock.py (new)
**Review score:** —
**Started:** 2026-10-20T05:15:11Z · **Closed:** — · **Actual:** — · **Merge commit:** —
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

## System contract

Curated to **5 of 10** in-scope rules under `meta/kanban/curation.md`: every rule whose
enforcement does not reach this card's new code is kept; the rest are dropped because the suite runs them
on every gate. **5 dropped.**

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

### Implementation (2026-10-20)

**Where it lives.** `tests/full_suite_lock.py` (new), with `tests/conftest.py` calling its
`pytest_configure` **first** in its own — before the CARD-109 database guard and before any fixture
exists, let alone one that connects (G-1) — and importing its `pytest_terminal_summary` under its own
name so the hook registers. A deviation from Touches, which named only the conftest: it follows
`tests/hang_guard.py` and `tests/database_guard.py`, the two guards already registered from there for
exactly this reason — the decision stays a pure function that every case can be put in front of
without starting a process, and its own tests start real runs and watch it refuse them.

**Holder identity is the worktree, never a pid.** The gate writes the lock and then launches pytest as
a **child**, so no pid the file could carry is ever the pid of the process the guard runs in; a
pid-identity guard would refuse every gate on the board. What every gate does do is run pytest in the
worktree it names, so the comparison is the lock's `worktree:` against the tree the guard module was
imported from (`Path(__file__).parents[1]`, not the cwd). A lock that names **no** worktree is refused
rather than assumed ours (ADR-0039/R2: a shape the guard cannot analyse is a refusal, never a silent
pass) — which is why `tests/README.md`'s profiling protocol, whose documented snippet wrote a
free-text lock naming nobody, is updated in the same commit to write the field format.

**The lock's location.** Every gate script writes the **main** checkout's
`meta/kanban/.full-suite.lock` whichever worktree it runs in, so a linked worktree follows its `.git`
file (`gitdir: <main>/.git/worktrees/<name>`) back to the main root. A per-worktree path would have
been a guard that cannot see the only contention there is. `NONOGRAM_FULL_SUITE_LOCK` points the
reader elsewhere and exists for this guard's own tests — the real lock is never created or deleted by
a test, because a gate may be holding it. Unset, which is every real run, the path is the real file
(`test_the_production_default_is_the_boards_own_lock`).

**Stale rule: age, not pid — and why.** The gate scripts write `at:` and no pid, and G-4 forbids
editing them to make this guard work, so a pid rule would never fire on a single real lock: a claim
with no reach (ADR-0039/R1). `STALE_SECONDS = 21600` (6h). The number is bounded from below by the
longest hold this board has recorded — CARD-245's gate wrapper at **4126s** — because a threshold near
that figure would hand a *running* gate's window to a second pytest, which is the defect being
removed; `test_the_threshold_clears_the_longest_gate_this_board_has_recorded` is that bound as a test,
not a comment. The cost of being generous is bounded by the override, which needs no wait. `at:` is
preferred and the file's mtime stands in when it is missing or malformed; an age that cannot be
determined is **not** treated as old.

**Override: `NONOGRAM_IGNORE_FULL_SUITE_LOCK`.** No gate script sets it, and
`test_nothing_in_the_tree_sets_the_override_for_a_run` holds the tree to that (the guard, its test and
the README may name it; `src/` and `pyproject.toml` may not). It announces itself through
`pytest_terminal_summary`, **not** the run header: `addopts = "-q"`, and at that verbosity pytest
prints no header at all — measured before choosing, so an announcement that only reached
`pytest_report_header` would be invisible in every gate and every agent selection, which are the only
runs there are. The same channel carries the stale-lock line. Both are silent when there is no lock
and when the lock is this run's own.

**G-4, both directions.** The reader parses `key: value` lines and reports whatever it finds, so both
shapes in use (`why:` as its own field in `gate-247.sh`/`gate-250.sh`, folded into `holder:` in
`gate.sh`) are understood, an unknown field such as a future `pid:` is printed rather than dropped,
and a lock written **without** it gets the same verdict. No gate script is touched.

**Mutants** (each file restored from a byte-identical backup, verified with `diff`, never
`git checkout --`), selection `tests/test_full_suite_lock.py`, 24 tests green at base:

| mutant (mechanism deleted) | result |
| --- | --- |
| M1 `verdict`'s own-worktree branch — *treat every lock as foreign* | 3 failed / 21 passed — the two refusal tests stayed **green** and the three self-run cases went red. This is the trap's control: the suite can tell "refuses a foreign lock" from "refuses everything". |
| M2 `raise pytest.UsageError` in `pytest_configure` (**AC-2**) | 1 failed — `test_a_foreign_lock_aborts_a_real_run_before_collection` |
| M3 the stale-age branch | 2 failed — both AC-3 tests |
| M4 the override branch | 2 failed — both AC-4 tests |
| M5 `terminalreporter.write_line` | 2 failed — the AC-3 and AC-4 *real-run* tests (the pure-function pair stays green, which is why both layers exist) |
| M6 the `age:` line in the refusal | 1 failed — AC-1's "does not say how old the lock is" |
| M7 the holder/commit/why block in the refusal | 4 failed |
| M8 the conftest wiring line | 3 failed — every real-run case |
| M9 `main_repo_root`'s `gitdir:` resolution | 1 failed — `test_every_worktree_resolves_the_one_lock_the_gates_write` |
| M10 the mtime fallback in `lock_age_seconds` | 1 failed |
| M11 the `held_by and` guard (unnamed worktree treated as ours) | 1 failed |

**AC-5, measured rather than asserted.** Same selection (5 files, `db_required` tests with no
`DATABASE_URL`, so the skip machinery actually runs) under the pristine conftest and under this one:
`184 passed, 2 skipped` both times, same two tests, same reason — only the conftest **line number** in
the skip line moves (177 → 193), because the change adds lines above it. The guard also names no skip
API at all (`test_the_guard_cannot_turn_a_refusal_into_a_skip`), and each allowed case asserts
`1 passed` with `skipped` nowhere in the output.

**One collateral fix.** `tests/test_db_isolation.py`'s `_ROOT_CONTENTS` is a hand-written list of what
a copied repo root needs; it already carried the other two guard modules, and without the third every
copied root failed to import its own conftest (both arms of that card's AC-6 red for a reason with
nothing to do with databases). One entry added, with the reason. Each copied root is its own main root
(no `.git`), resolves a lock path of its own, finds nothing there, and runs exactly as before —
`tests/test_db_isolation.py` 51 passed.

**What a gate sees now.** The refusal (exit 4, before collection):

```
ERROR: Refusing to start: another worktree holds the full-suite lock.

  holder:   CARD-254 gate (wave 49)
  why:      build gate 2, solo
  worktree: /Users/omelnikova/PycharmProjects/PythonProject4-card-254
  commit:   a60d375
  at:       2026-10-20T05:18:18Z
  age:      413s (stale after 21600s)
  lock:     .../meta/kanban/.full-suite.lock
  ... Wait for the file to disappear — it is deleted when that run ends.
  If the holder is gone and the file is not: NONOGRAM_IGNORE_FULL_SUITE_LOCK=1 pytest ...
```

and, at `-q`, the two allowed-but-notable cases:

```
full-suite lock: held by CARD-254 gate (wave 49) (/Users/.../PythonProject4-card-254) — running anyway because NONOGRAM_IGNORE_FULL_SUITE_LOCK is set
full-suite lock: ignoring a stale lock — CARD-250 RE-GATE, solo (wave 47) (...) took it 188723s ago, past the 21600s threshold, and is presumed gone. Delete ... if it is.
```

**Not claimed.** The gate scripts themselves are unchanged and still refuse to *start* beside another
pytest; this card adds the other half of that check and nothing else. No timing figure was taken (a
sibling card was live on this host), and the full suite was not run here — the gates run it.

- **[Orchestrator] the identity decision is the card, and the agent got it right for a reason I had
  not seen.** The card said "the lock carries the holder's pid **or** an age threshold applies". A pid
  rule is unimplementable here and would have been worse than nothing: **the gate writes the lock and
  then launches pytest as a child**, so no pid the file could carry is ever the pid of the process the
  guard runs in — a pid-identity guard would have refused **every gate on this board**. Identity is
  the lock's `worktree:` against the guard module's own tree, and a lock naming *no* worktree is
  refused rather than assumed ours (ADR-0039/R2).
- **[Orchestrator] M1 is the mutant this card existed to need.** Deleting the own-worktree branch —
  "treat every lock as foreign" — left both refusal tests **green** and reddened the three self-run
  cases. That is the card's trap closed by measurement: the suite can tell *"refuses a foreign lock"*
  from *"refuses everything"*, which the obvious single-process test cannot.
- **[Orchestrator] the stale threshold is bounded from below by evidence, not taste.** 6h, against
  the longest hold this board has on record — CARD-245's gate wrapper at **4126s**. A threshold near
  that figure would hand a running gate's window to a second pytest. The bound is a test, not a
  comment, and "an age that cannot be determined" is **not** treated as old.
- **[Orchestrator] the announcement channel was measured before it was chosen.** `pyproject.toml`
  sets `addopts = "-q"`, at which pytest prints **no header at all** — so a header-only announcement
  would have been invisible in every gate and every agent selection. It goes through
  `pytest_terminal_summary` instead. This is the same `-q` that cost a gate its count line in wave 47.
- **[Touches drift]** three files beyond the card's `Touches`, all flagged by the agent:
  `tests/full_suite_lock.py` (new — the guard is its own module, following `hang_guard.py` and
  `database_guard.py`, the two guards already registered from conftest for exactly this reason),
  `tests/test_db_isolation.py` (one entry in `_ROOT_CONTENTS`, the hand-written list of what a copied
  repo root needs — without it every copied root failed to import its own conftest, reddening both
  arms of an unrelated card's AC-6) and `tests/README.md` (its profiling-lock snippet wrote a lock
  naming no worktree, which the new guard correctly refuses).
- **[Build gate 1 — PASSED]** `3711af2b`, solo: **8619 passed**, 1 skipped, 17:20, EXIT=0. The count
  reconciles exactly: main 8595 + the card's **24** new tests = 8619.
- **[The gate was also this guard's first live self-run case]** The gate script writes
  `meta/kanban/.full-suite.lock` naming this card's own worktree, and the tree under test carries the
  guard that reads it. Had identity been got wrong — a pid rule, or "every lock is foreign" (the M1
  mutant) — **this gate would have refused itself** and exited 4 before collecting. It ran. That is
  the self-run case certified in production conditions rather than in a test's temp directory, and it
  is why the card was gated before being reviewed rather than after.

### [Review 1/3] Score 7.5 — FAILED on the severity gate (2 open Important)

Report: `meta/review/20261020T062654Z-CARD-255-cycle1.yml` (copied to main). Ten findings, two
gating; both are one-clause fixes in files this card already owns.

- **The identity design is certified, including the premise.** The reviewer **read all three gate
  scripts** rather than taking the pid argument on trust: each writes the lock and *then* runs pytest
  as a child, so a pid rule would have refused every gate. Five of six identity probes come back
  correct — prefix sharing is exact equality (`…-card-25` vs `…-card-255` → False), trailing slash
  and `~` normalise, symlinks resolve on both sides, a linked worktree resolves to the main root.
- **M1 re-derived exactly**: "treat every lock as foreign" reds the three self-run cases and leaves
  **both refusal tests green**. The suite genuinely distinguishes *refuses a foreign lock* from
  *refuses everything* — the card's trap, closed and now independently confirmed.
- **The stale rule holds and its riskiest claim is controlled.** `Z` is not read as local time —
  numerically (1792473498 vs `time.mktime`'s 1792462698, 10800s out) **and** by a mutant that reds in
  either hemisphere's sign. Undeterminable age is genuinely not treated as old; `STALE_SECONDS` ≥ 4×
  the longest hold on record is a test, not a comment.
- **F-001 (important) — the silent direction.** `os.path.realpath` resolves a **relative** value
  against the *reading* process's cwd, and gates run pytest from the worktree root. A foreign lock
  reading `worktree: .` therefore resolves, inside every other worktree, to that worktree: the run
  proceeds and **prints nothing**. Probed live. What makes it gating is the asymmetry with the card's
  own principle — the module adopts ADR-0039/R2 verbatim and refuses a lock naming **no** worktree,
  while a value that cannot be resolved to a tree is the same shape and gets the opposite verdict.
  And `tests/README.md`, changed by this card, now tells a human to hand-write a lock.
- **RC-1 — `_same_tree` is the function this card reduces to and it has no direct test.** Three
  mutants survived at 24 passed: `startswith` for exactness, raw string equality for normalisation,
  and `return None` for the `""` distinction. Every identity assertion reaches that function through
  `verdict()` with two already-resolved, exactly-equal absolute paths — so three documented claims
  have no control that can fail. One fix (the `isabs` clause plus a direct table test) closes all
  four findings.
- **F-004 (important) — a test whose claim is wider than its own pathspec.**
  `test_nothing_in_the_tree_sets_the_override_for_a_run` says "nothing **in the tree**" and then greps
  `-- tests src pyproject.toml`. Measured: whole-tree grep returns 3 files, the scanned set 2 — the
  pathspec buys nothing and costs the claim its reach. `scripts/run_admin_tests.sh` is an in-tree
  pytest runner that already exports env for the suite, and is the strongest co-change peer of
  `conftest.py` absent from this diff: an export there would disable the guard for every run through
  it and leave the test green.
- **The collateral fix is the whole fix, proven.** The reviewer rebuilt a copied root both ways:
  without the `_ROOT_CONTENTS` entry → `exit 4, ImportError` at `conftest.py:148`; with it → exit 0.
  It also enumerated conftest's complete `tests.*` import set and confirmed no other such list exists.
- **F-009 recorded and deliberately not "fixed"**: a lock naming a worktree that no longer exists
  refuses every run until it goes stale. A filesystem-existence check would hand a live gate's window
  away whenever a path is briefly unreadable; the override is the documented escape.

### Review cycle 1 — the fix (score 7.5, two open Important)

Report: `meta/review/20261020T062654Z-CARD-255-cycle1.yml`. Selection throughout:
`tests/test_full_suite_lock.py`, **24 passed before / 30 passed after**. No timing taken (a fix
cycle was live on CARD-254); the board's real lock was never created, modified or deleted — every
lock in this work lived in the session scratchpad behind `NONOGRAM_FULL_SUITE_LOCK`.

**RC-1 — `_same_tree` was the card's whole claim with no direct test.** Four findings, one cause.

- **F-001 (Important, ADR-0039/R2) — a relative `worktree:` was a silent pass.** `os.path.realpath`
  resolves a relative value against the *reading* process's cwd, and gates run pytest from the
  worktree root, so a foreign holder's `worktree: .` resolved, inside every other worktree, to that
  worktree: `verdict()` returned `(True, None)` and the run proceeded printing nothing. Probed live
  before the fix: exit 0, `1 passed`, no "full-suite lock" line anywhere.
  Fixed with one clause, not a second vocabulary: `_names_a_tree` (`tests/full_suite_lock.py:226`)
  requires `os.path.isabs(expanduser(...))` before the exemption is even considered
  (`tests/full_suite_lock.py:322`), so a relative value folds into the *same* branch as a lock that
  names no worktree at all — the shape ADR-0039/R2 already refused — and the explanation says which
  of the two it was (`tests/full_suite_lock.py:341-354`).
  Probed live after the fix, same lock: **exit 4**, `ERROR: Refusing to start`, and
  `its worktree: value '.' is not an absolute path, so it would resolve to whichever tree happened
  to read it`.
  **The clause changes the verdict for no lock any gate script writes.** All five scripts in the
  orchestrator's scratchpad (`gate.sh`, `gate-225/247/250/251.sh`) write `worktree: $WT` with `$WT`
  absolute. Measured rather than asserted: the pre-fix and post-fix modules were loaded side by side
  and each script's exact lock text put to both, read by its own holder, by another worktree and by
  the main checkout — 15 pairs, **0 verdicts changed**.
- **F-002 / F-003 / F-005 — three survivors, now three reds.** Re-run as real mutants against the
  fixed tree, each restored from a byte-identical backup (`diff -q`, never `git checkout --`):

  | mutant | before | after |
  |---|---|---|
  | NA-prefix (`_same_tree` → `startswith`) | survived, 24 passed | **1 failed, 29 passed** — `…-card-25 read as …-card-255` |
  | NB-realpath (`_same_tree` → raw string equality) | survived, 24 passed | **1 failed, 29 passed** — `a trailing slash made a tree foreign` |
  | ND-readlock (`except OSError: return ""` → `return None`) | survived, 24 passed | **1 failed, 29 passed** — `a lock that cannot be read read as no lock` |

  The controls: `test_same_tree_is_exact_identity_not_a_prefix_or_a_spelling`
  (`tests/test_full_suite_lock.py:230`) is a direct table over the board's *real* neighbours — the
  main checkout and `…-card-25` are prefixes of `…-card-255`, so exactness is the live case, not a
  hypothetical — plus trailing slash, `/.`, a `tmp_path` symlink and `~`;
  `test_a_lock_that_cannot_be_read_is_not_the_same_as_no_lock` (`:284`) uses a *directory* at the
  lock path rather than `chmod 0o000`, which does not stop the file's owner on every host.
  Two further mutants on the new clause and on the exemption pair, to keep each new claim owned:
  **NC-isabs** (`_names_a_tree` → `bool(value)`) → 3 failed; **M1-no-exemption** → 3 failed, the
  three self-run cases only, both refusal tests still green; **M2-no-abort** → 2 failed.

**F-004 (Important, ADR-0039/R1) — a claim wider than its own pathspec.**
`test_nothing_in_the_tree_sets_the_override_for_a_run` claimed the tree and scanned
`-- tests src pyproject.toml`. The pathspec is gone (`tests/test_full_suite_lock.py:420-464`); the
allowlist is now `OVERRIDE_NAMERS` (the guard, this file, `tests/README.md`) plus the prose prefixes
`meta/kanban/cards/` and `meta/review/` — the latter needed because review reports quote the
variable and `meta/review/` is tracked in main. Both bounds are now stated in the docstring rather
than left to be discovered: `git grep` reads **tracked** files only, and the gate scripts live
outside the repo so they cannot be held by this test at all.
Control (mutant **NE-runner**): `export NONOGRAM_IGNORE_FULL_SUITE_LOCK=1` appended to
`scripts/run_admin_tests.sh` — the in-tree pytest runner that already exports env for the suite, and
the strongest co-change peer of `tests/conftest.py` absent from the diff. Widened test: **1 failed**
(`assert not ['scripts/run_admin_tests.sh']`). The old pathspec'd scan, run against the same mutated
tree, returned exactly the three allowlisted files — it would have stayed green. Runner restored
byte-identical.

**The small ones.**

- **F-007** — a lock stamped ahead of this clock printed `age: -3600s`. `_describe` now prints
  `stamped 3600s in the future (clock skew?)` (`tests/full_suite_lock.py:279-289`); the verdict is
  untouched (a negative age is below the threshold, so the refusal stands), which the control asserts
  both ways (`test_a_lock_stamped_in_the_future_refuses_and_says_so_in_words`).
- **F-010** — `tests/README.md`'s snippet gained `trap 'rm -f "$LOCK"' EXIT`. Said in the same place:
  the gate scripts have the same `rm -f` shape with no trap of their own, they live outside this repo
  and are not this card's to edit, so an aborted *gate* still leaves its lock and the override is the
  way past it.
- **F-006** — left as the project's convention (`tests/database_guard.py:103` reads its opt-out the
  same way) and now said out loud where it is defined (`tests/full_suite_lock.py:89-93`): any
  non-empty value turns it on, `=0` included, and the run announces it either way, so the surprising
  spelling cannot become a quiet suppression.
- **F-008** — AC-5's structural guard keeps its text rule and says in its own docstring that it is a
  text rule over prose as well as code, failing in the safe direction. It now also reads the claim
  off the module's syntax: no `ast.Call` in `tests/full_suite_lock.py` resolves to
  `skip/skipif/importorskip/xfail/add_marker/exit`.
- **F-009 — recorded, not fixed, on purpose.** A lock naming a worktree that no longer exists
  refuses every run on the host until it goes stale. Adding a filesystem-existence check would hand
  a live gate's window away whenever its path is briefly unreadable — the defect this card removes.
  The override is the documented escape, it is named on the line below every refusal, and merge
  discipline removes a worktree *at* merge, which is also when its gate has deleted its lock.

**AC-5 and the ordinary run, re-proved after the change.** The abort is still an abort, never a
skip: the guard names no skip API (text rule **and** AST rule), and the three allowed real-run cases
each assert `1 passed` with `skipped` nowhere. The skip profile was re-derived on its own selection —
five db-bearing files (`test_card_156_db_fixture`, `test_db_url_driver`, `test_db_isolation`,
`test_card_109_database_guard`, `test_db_engine_lifecycle`), no `DATABASE_URL` — against the fixed
guard and then against the pre-fix one restored for the comparison: **153 passed, 7 skipped** both
times, one named reason (`Database not reachable: DATABASE_URL is not set`), and the two outputs are
**byte-identical**. A tree with no lock says nothing about a lock: no `full-suite lock` line and no
mention of the override in that run's output, and
`test_a_tree_with_no_lock_runs_exactly_as_it_did_before` asserts it.
Neighbours that read the guard or the README: `test_guard_integrity.py`, `test_suite_profile.py`,
`test_full_suite_lock.py`, `test_db_url_driver.py`, `test_cli.py` — **712 passed**.

**Declarations re-derived.** The identity rule changed, so every statement of it was corrected in
the same pass: the module docstring now names *both* members of the unanalysable shape and why a
relative value is one (`tests/full_suite_lock.py:23-37`); `_same_tree`'s own docstring states the
exactness claim, the normalisation claim and its new precondition (`:203-224`); `tests/README.md`
told a human to hand-write a lock and now says the `worktree:` line must be **absolute**, with
`worktree: .` named as a refusal; the override's doc comment records its spelling. The age display
changed, so its comment explains why the verdict did not. No config field, parameter or timeout
acquired a second job.

### [Review 2/3] Score 8.5 — FAILED on the severity gate (1 open Important) · ⚠ second generation

Report: `meta/review/20261020T065828Z-CARD-255-cycle2.yml` (copied to main).

- **The measurement that licensed the `isabs` clause was re-derived and came back *stronger* than the
  fix reported**: 15 pairs, 0 verdicts changed — **and all 15 messages byte-identical**, not merely
  the booleans. With the structural reason attached, which turns the sample into an argument: for any
  **absolute** `worktree:` value, `_names_a_tree(held_by) ≡ bool(held_by)`, so both branches take
  exactly the pre-fix path and behaviour can only differ where the value is non-empty and
  non-absolute.
- **18 adversarial path shapes probed, all unchanged** pre-vs-post: `~`, `~` alone,
  `~nonexistentuser`, trailing spaces/tab/**CR** (a CRLF-written lock), leading spaces, trailing and
  double and triple slashes, a symlinked parent on each side, an absolute path containing `..`, and
  `$WT` unset. `expanduser` inside `isabs` saves the `~` family; `realpath` normalises the rest.
- **Cycle 1's three survivors are all dead, and the table is tight**: each assertion is live for a
  *distinct* mutant — prefix in each direction (M-B/M-B2), trailing slash (M-C/M-C2), `~` (M-C3/M-J),
  and the symlink case reds **only** under `realpath → normpath` (M-I). AC-5 re-proved byte-identical
  against **both** the pre-fix guard and the no-guard baseline, on a five-file selection of the
  certifier's own choosing.
- **⚠ F-101 (important, `test_full_suite_lock.py:414`) — the second generation of cycle 1's family.**
  The F-004 fix widened the scan correctly and **paid for it with a new exemption**: two whole
  directories exempted by path **prefix**, with no constraint on file shape and no control. Probed
  live: two executable `export NONOGRAM_IGNORE_FULL_SUITE_LOCK=1` scripts placed under the
  allowlisted prefixes, both visible to `git grep` — **the test stayed green with two live in-tree
  setters.** That is cycle 1's own evidentiary standard, and it is verbatim the shape ADR-0039/R3's
  comment names as its reason for existing. Said plainly: **the fix for a claim wider than its
  mechanism was itself a claim wider than its mechanism, one directory over.**
- **Minors**: the documented `=0`-enables-the-override semantics has no control (M-K survived); the
  documented exit code 4 is asserted only as `!= 0`, which is why a `pytest.exit` mutant (code 2)
  passed every real-run test; the new AST rule reaches exactly **one** name past the text rule it
  sits behind; and the `trap … EXIT` added in cycle 1 stays armed for the profiler's whole shell, so
  a later Ctrl-C could delete a **live gate's** lock — narrower than what it replaced, but worse in
  kind.

### [Standing requirement for the orchestrator] `gate.sh` must be passed an absolute worktree

The certifier found exactly one real-producer shape whose verdict changes: `gate.sh <worktree>`
invoked with a **relative** path now makes the gate refuse **itself** at exit 4. That is the right
trade — pre-fix, the same lock resolved to every *other* worktree's own path and disabled the guard
board-wide in silence — but it is a requirement on whoever drives the gates. The four dedicated gate
scripts hardcode absolute paths; `gate.sh` takes `$1` and lives outside the repo, where no test can
hold it. **Every gate invocation in this session passes an absolute path, and must keep doing so.**

### Review cycle 2 — the fix (score 8.5, one open Important; the last fix cycle, `max_cycles: 3`)

Report: `meta/review/20261020T065828Z-CARD-255-cycle2.yml`. Fix commit: `9ef39c54`.
Selection throughout:
`tests/test_full_suite_lock.py`, **30 passed before / 36 passed after**; the neighbours that read
the guard or the README together with it — `test_suite_profile.py`, `test_guard_integrity.py`,
`test_db_isolation.py`, `test_full_suite_lock.py` — **617 passed**. No timing taken (a certification
cycle was live on CARD-254). The board's real lock was never created, modified or deleted; every
lock in this work lived under `tmp_path` behind `NONOGRAM_FULL_SUITE_LOCK`, and the new control
builds a throwaway git repo under `tmp_path` rather than adding anything under the real `meta/`.
`git status` carries only this card's three files and this note.

**Say it plainly: this was the second generation of the family both of cycle 1's gating findings
belonged to.** F-001 and F-004 were each *a claim wider than its mechanism*. The fix for F-004 —
widening the override scan from a hand-written pathspec to the whole tracked tree, which was the
right move and is proved by a mutant — paid for that reach with a new exemption, two bare directory
prefixes, and that exemption was itself a claim wider than its mechanism, one directory over. The
scan's controls tested what the exemption *exempted* and never what it must not absorb. That is
verbatim the counter-example ADR-0039/R3 records as its own reason for existing. The lesson the card
leaves behind is the one R3 already states: widening a predicate and adding an exemption are the
same edit, and the exemption needs its own failing control in the same commit.

- **F-101 (Important, ADR-0039/R3) — the prose exemption now has a shape bound and a control.**
  `OVERRIDE_PROSE = ("meta/kanban/cards/", "meta/review/")` matched by `path.startswith(...)`
  carried no constraint on file *shape*. The certifier probed it live: two executable
  `export NONOGRAM_IGNORE_FULL_SUITE_LOCK=1` scripts at `meta/kanban/cards/run-the-suite.sh` and
  `meta/review/run-the-suite.sh`, both visible to `git grep`, and the scan test stayed **green with
  two live in-tree setters**.
  Fixed with one clause and one control. `PROSE_SHAPES = (".md", ".yml")`
  (`tests/test_full_suite_lock.py:481`) and the predicate lifted into `_override_offenders`
  (`:484`), which exempts a prefix hit only when the file is also prose:
  `path.startswith(OVERRIDE_PROSE) and path.endswith(PROSE_SHAPES)`. The trailing slashes are kept —
  they are what stops `meta/review-archive/` and `meta/reviews/` matching — and both prefixes are
  kept: they are load-bearing in both checkouts today.
  The control is the probe, promoted:
  `test_an_executable_setter_under_an_allowlisted_prefix_is_still_caught`
  (`tests/test_full_suite_lock.py:540`) builds a throwaway repo holding a card `.md`, a review
  `.yml` and the two executable `run-the-suite.sh` setters, runs the same `git grep -l` and the same
  predicate, and asserts the offender list is **exactly the two setters** while the prose stays
  exempt. Two mutants on the new clause, each restored from a byte-identical backup:
  **M-L** (the `endswith` clause deleted — the exact pre-fix predicate) → **1 failed**, and the
  scan test above stayed green, which is the finding reproduced as a red; **M-M**
  (`PROSE_SHAPES` narrowed to `(".md",)`) → **1 failed**. The exemption is now bounded on both
  axes and fails in both directions.
  **The shape constraint excludes no file that legitimately names the override today** — measured,
  not assumed: `git grep -l NONOGRAM_IGNORE_FULL_SUITE_LOCK` is `meta/kanban/cards/CARD-255.md`,
  `tests/README.md`, `tests/full_suite_lock.py`, `tests/test_full_suite_lock.py` in this worktree
  and `meta/kanban/cards/CARD-255.md` plus the two `meta/review/*.yml` reports in the main checkout;
  every one is either an exact `OVERRIDE_NAMERS` member or `.md`/`.yml`. And the shape set equals
  the directories' whole population rather than guessing at it:
  `git ls-files meta/kanban/cards meta/review` is 256 `.md` and 286 `.yml` files and nothing else.
- **F-102 (Minor, ADR-0039/R1) — the `=0` spelling has a control; M-K is dead.**
  `test_any_non_empty_value_turns_the_override_on_including_zero`
  (`tests/test_full_suite_lock.py:402`) drives `current_verdict()` against a foreign lock with the
  variable set to `"1"`, `"0"`, `"false"`, `"no"` and `""`, asserting the first four turn the
  override on *and announce it* and the empty one leaves the lock standing. Mutant **M-K**
  (`bool(os.getenv(OVERRIDE))` → `in {"1","true","yes","on"}`), which survived cycle 2 at 30 passed:
  **3 failed, 33 passed** (`[0-True]`, `[false-True]`, `[no-True]`). The doc comment at
  `tests/full_suite_lock.py:89-96` now names that test, so the sentence points at its mechanism.
- **F-103 (Minor, ADR-0039/R1) — the documented exit code is asserted; M-G is dead twice over.**
  `test_a_foreign_lock_aborts_a_real_run_before_collection` asserted `returncode != 0`, which is why
  **M-G** (`raise pytest.UsageError(said)` → `pytest.exit(said)`, exit 2) passed every real-run
  test. It now asserts `result.returncode == 4` with the reason in a comment
  (`tests/test_full_suite_lock.py:708-714`): `UsageError` is pytest's `USAGE_ERROR` and the only
  outcome this abort has, so another code means the abort moved to another mechanism. M-G re-run:
  **2 failed, 34 passed** — `assert 2 == 4` in the real run, plus the AST rule.
- **F-104 (Minor) — the AST rule's reach is stated as what it is.** The docstring of
  `test_the_guard_cannot_turn_a_refusal_into_a_skip` (`tests/test_full_suite_lock.py:721`) no longer
  implies the syntax rule is the broader check: it says the text rule runs first and forbids five of
  the six names as substrings, so the syntax rule's independent reach is the non-result *exit* APIs,
  and that one name is demonstrably live (M-G). `Exit` added to `forbidden_apis` beside `exit`, so
  the stated reach and the measured reach are the same set.
- **F-105 (Minor) — the profiling trap is scoped to the run.** `tests/README.md:310-318` writes the
  lock first, then arms `trap 'rm -f "$LOCK"' EXIT`, then disarms it in the same breath as the
  documented delete: `rm -f "$LOCK"; trap - EXIT`. The prose says why it is scoped — an `EXIT` trap
  at top level lives until the *shell* exits, so one left armed in an open terminal deletes whatever
  is at that path when the window is later closed, and by then it may be a live gate's lock: `rm -f`
  on a path the shell no longer owns is the silent direction this card exists to close, reached
  through the handling for the loud one. A `( ... )` subshell is offered as the equivalent.
- **F-106 (Info) — recorded, no code change.** Also narrowed the one unverifiable justification it
  names: `test_a_lock_that_cannot_be_read_is_not_the_same_as_no_lock`'s docstring no longer claims
  something about `chmod 0o000` that does not reproduce on this host (where it raises for its own
  owner); it states the directory route's determinism, which is the actual reason.

**STANDING REQUIREMENT — `gate.sh` must be passed an ABSOLUTE worktree path.** `gate.sh <worktree>
<out> <why>` writes `worktree: $1` verbatim into the lock. Invoked with a *relative* worktree
(`gate.sh ../PythonProject4-card-255 ...`) the lock now makes the gate **refuse itself at exit 4**,
naming `'../PythonProject4-card-255' is not an absolute path`. This is the one real-producer shape
whose verdict the `isabs` clause changes, and it is not a defect: pre-fix that same lock resolved to
every *other* worktree's own path and disabled the guard board-wide in silence. Loud self-refusal is
the better of the two. The four dedicated gate scripts (`gate-225/247/250/251.sh`) hardcode absolute
paths; `gate.sh` is the only one that could be called otherwise and it lives outside the repo, where
no test in this tree can hold it — so this requirement is on the orchestrator, written here to
survive the session.

**AC-5 re-checked: the abort is still never a silent skip.** The module names no skip API and calls
none (text rule + syntax rule, both in `test_the_guard_cannot_turn_a_refusal_into_a_skip`), and
every allowed real run asserts `1 passed` with `skipped` absent from the output. The skip *profile*
re-derived after this fix on a db-bearing selection with `DATABASE_URL` unset
(`test_card_156_db_fixture.py`, `test_card_109_database_guard.py`, `test_db_connect_timeout.py`):
**35 passed, 2 skipped**, one named reason — `Database not reachable: DATABASE_URL is not set` — and
the output is **identical to the same selection under the pre-card pristine conftest**
(`git show a60d53a4:tests/conftest.py`, swapped in and restored byte-identically) except the
conftest line number the guard's import shifts (177 → 193) and the elapsed-time line, which is
incidental and not a measurement.

**A tree with no lock still behaves exactly as before.** Re-proved after the change: the comparison
above is that proof at the suite level, and
`test_a_tree_with_no_lock_runs_exactly_as_it_did_before` asserts it at the run level — exit 0,
`1 passed`, no `full-suite lock` line, no mention of the override. Nothing in this fix touches the
guard's runtime behaviour at all: the only edit to `tests/full_suite_lock.py` is a doc comment
naming F-102's new test.

**DECLARATIONS.**

- `DECLARATIONS F-101 — updated.` The exemption's own doc comment is the declaration that changed:
  `OVERRIDE_PROSE`/`PROSE_SHAPES` (`tests/test_full_suite_lock.py:460-481`) now state what the
  prefixes are exempted *for*, that the shape set equals the measured population of those
  directories, and that the trailing slashes are load-bearing; `_override_offenders`' docstring
  states which exemption is bounded by equality and which by shape, and why neither can be bounded
  the other way. The scan test's claim is unchanged and still true.
- `DECLARATIONS F-102 — updated.` `tests/full_suite_lock.py:89-96` keeps the documented spelling and
  now names the test that holds it, so the claim and its control are one edit apart.
- `DECLARATIONS F-103 — confirmed.` The card's "What a gate sees now" block already says *exit 4,
  before collection*; re-derived against the code and left standing, now with a test behind it.
- `DECLARATIONS F-104 — updated.` The docstring was the defect: it claimed a reach the rule does not
  have. Narrowed to the one-name (now two-name) gain it actually buys.
- `DECLARATIONS F-105 — updated.` `tests/README.md`'s own prose about what the trap is for, since
  the snippet is what people paste. No other document describes it.
- `DECLARATIONS F-106 — updated.` One docstring sentence narrowed to what reproduces on this host;
  the standing requirement written into these notes.

No config field, parameter or timeout acquired a second job in this cycle. No failure-matrix row
changes: the guard's verdicts are unchanged by this fix except where no verdict existed before (the
offender predicate is test-side).

- **[Orchestrator] the shape set is a census, not a guess, and that is what makes it an enumerable
  exemption rather than another prefix.** `git ls-files meta/kanban/cards meta/review` is **256 `.md`
  + 286 `.yml` and nothing else** — recorded in the `PROSE_SHAPES` comment, so a prose file in a third
  format is a deliberate one-word edit rather than a silent widening. ADR-0039/R3 asks for an
  exemption set that is derived and machine-checked; a measured census with a control is that.
- **[Orchestrator] M-L is the right control because it is the pre-fix predicate exactly.** Deleting
  the `endswith` clause reproduces cycle 2's finding **as a red in the new control and nowhere else**
  — the old test stays green, which is the whole point: the probe catches what the old scan could
  not. M-M (narrowing the shapes to `.md` alone) reds it from the other side, so the set is bounded
  in both directions.
- **[Orchestrator] two claims that were documented-only are now measured.** M-K (the `=0`-enables
  semantics) went from surviving at 30 passed to **3 failed**, and M-G (the `pytest.exit`
  substitution) from being caught by the AST rule alone to failing the exit-code assertion as well.
  Both were Minors; both were the "documented claim with no control" shape this wave keeps finding.
