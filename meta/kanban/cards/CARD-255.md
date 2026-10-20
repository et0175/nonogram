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
