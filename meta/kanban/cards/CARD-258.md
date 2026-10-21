# CARD-258: Make the next `relation "puzzles" does not exist` red say what it was talking to

**Status:** done
**Priority:** P1
**Category:** ops
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/258-the-ops-red-says-what-it-talked-to
**Worktree:** —
**Source:** CARD-256's build gates 1 and 2 (2026-10-20) — red then green on the same commit, on a tree carrying CARD-252's `reset_engine()`. The hazard survives the fix that was expected to remove it.
**Idea:** —
**Wave:** 51
**Depends on:** —
**Touches:** tests/conftest.py, tests/test_admin_binding.py, tests/helpers/ (a new diagnostic helper), src/nonogram/db/session.py — only if a read-only accessor is needed
**Review score:** 9.0 (cycle 3/3)
**Started:** 2026-10-20T16:52:59Z · **Closed:** 2026-10-21T10:05:00Z · **Actual:** 2.2d · **Merge commit:** `4584caf4`
**Blocked by:** —

## Why — four waves, one signature, no data

The same red has now appeared on build gates in waves 47, 48 and 50: **five failures in
`tests/test_admin_binding.py::TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine`, with
`relation "puzzles" does not exist` raised inside the server thread**, and a sixth variant where the
page times out because the request died server-side on `uuid.UUID(hex=<float>)` inside SQLAlchemy's
UUID processor. Every occurrence has been solo, guard-enforced, and **green on a re-run of the same
commit**.

Two explanations have been offered and both are dead:

- *psycopg2's prepared statements* — refuted in wave 45: psycopg2 has no `prepare_threshold`.
- *a module-global engine surviving the schema rebuild* — CARD-252 published `reset_engine()` and
  wired it into `_rebuild_public_schema`. **CARD-256's gates ran red then green on a tree carrying
  it.** That card's AC-3 was withdrawn rather than claimed, and its docstring says the failures
  remain unexplained; this is that sentence being right.

So the next step is not a third hypothesis. **It is to make the next occurrence diagnostic.** The
cost of staying blind is measurable: ~16 minutes per re-run, three waves running, plus one
attribution written down and withdrawn.

## What to implement

A failure hook that fires **only** on this error class and records what no traceback currently shows:

1. **Which database the failing connection is attached to** — `SELECT current_database()`,
   `current_schema()`, `current_setting('search_path')`, and the backend pid (`pg_backend_pid()`).
   The derived name (CARD-244) means a connection to the *wrong* database is a one-line proof.
2. **Which engine object served it** — `id(engine)`, its URL, pool status
   (`engine.pool.status()`), and whether `reset_engine()` has been called since process start (a
   counter it already could expose read-only).
3. **Which process and thread** — pid, thread name, and whether the frame is inside a werkzeug server
   thread. These five tests are the only ones in the suite that serve real HTTP from a thread while
   the fixture owns the schema; that is a fact worth confirming rather than assuming.
4. **What the schema actually holds at that moment** — `to_regclass('public.puzzles')` and the row
   from `pg_tables`. "The table is missing" and "we are looking in the wrong place" are different
   failures with the same message.

Write it where it cannot distort the thing it measures: a `pytest_exception_interact` hook or an
`except` path that captures through a **separate connection**, never the failing one, and that is
silent when the error is anything else.

## Acceptance criteria

- **AC-1** *Given* a test that raises `UndefinedTable` for `puzzles`, *then* the report carries the
  four groups above, and the test still fails with its original traceback intact.
  (test: a test that provokes the error against a schema it has dropped itself)
- **AC-2** (the control) *Given* the hook removed, *then* AC-1's test fails. A diagnostic that cannot
  be shown absent is not wired in.
- **AC-3** *Given* any other failure, *then* the hook adds nothing — measured on a selection with an
  ordinary assertion failure, byte-compared against the same run without the hook.
- **AC-4** (guard) *Given* the hook, *then* a passing run is byte-identical to one without it, and
  the suite's skip profile is unchanged.
- **AC-5** *Given* the capture path itself fails (no connection, server gone), *then* the test's own
  failure is still reported and the capture's failure is named, not swallowed. A diagnostic that
  masks the defect it was built for is worse than none.

## Guardrails

- G-1: **No production code changes behaviour.** If `session.py` needs a read-only accessor (a reset
  counter, the engine's id), it is additive and nothing in `src/` calls it.
- G-2: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed. The capture connection derives its
  URL the same way every other test does.
- G-3: No new runtime dependency.
- G-4: The hook must not run per-test on the happy path — it fires on the exception class only.
- G-5: No test retired without a named survivor; `test_admin_binding.py`'s five parametrisations stay
  exactly as they are. **This card does not try to fix the hazard.**

## Worktree notes

- **[Do not take timing measurements]** other cards may share this machine.
- **[The trap]** The obvious implementation captures through the connection that just failed — which
  is in a broken transaction, so the capture raises `InFailedSqlTransaction` and the report says
  nothing, on exactly the run it was built for. Use a separate connection, and make AC-5 the control
  for that.
- **[The second trap]** This card is worth doing *only* if it is silent and free on the 8627 runs
  that pass. A diagnostic that costs a per-test query is a tax levied forever to catch something that
  happens once a wave.
- **[What success looks like]** the next occurrence produces a line that names a database, a schema,
  an engine and a pid — and that line either proves the connection was attached to the wrong
  database, or proves it was attached to the right one and the table genuinely was not there. Either
  is the first real datum this class has produced.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR
  files case-insensitively for the reach-limit idiom.

## System contract

Curated to **10 of 29** in-scope rules under `meta/kanban/curation.md`: every rule whose
enforcement does not reach this card's new code is kept; the rest are dropped because the suite runs them
on every gate. **19 dropped.** ADR-0039 present, as the sanity check requires for a card
touching `tests/**`.

- **ADR-0022/R1** — _review-lens — nothing executes it_
  Grid extent crosses module boundaries as a (width, height) pair. No public function signature,
  request field, or export field reduces a grid's extent to a single scalar "size", and no source
  mode constructs a grid from one integer.
- **ADR-0036/R3** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect
  whatever Pillow call it is written with.
- **ADR-0036/R4** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in
  U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed.
- **ADR-0038/R6** — _review-lens — nothing executes it_
  Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution
  grid to the browser. A public or reader-facing player must not send the solution before the
  puzzle is solved, and any public phase reopens this ADR (CON-021).
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
- **CON-021** — _review-lens — nothing executes it_
  Interactive play exists only as the admin panel's puzzle player, behind the door that guards
  every other admin page (CON-015, CON-016). Play state is never persisted on the server; the one
  place it may be kept is the browser's own localStorage, per puzzle.

## Implementation record — `8e40c0c0`

Commit `8e40c0c0` on `card/258-the-ops-red-says-what-it-talked-to`, pathspecs `tests/conftest.py`
`tests/test_admin_binding.py` `tests/helpers/undefined_table_report.py` (new) `src/nonogram/db/session.py`
— the card's `Touches`, exactly. Nothing under `meta/` in it.

`tests/helpers/undefined_table_report.py` is a pytest plugin with **exactly one hook**,
`pytest_exception_interact`, registered by name (`undefined-table-report`) from conftest's existing
`pytest_configure` rather than imported as a hook — which keeps it off the four hook names conftest
already owns **and** makes `-p no:undefined-table-report` a real control. At `8e40c0c0`: 15 test
functions / 21 node IDs / **48 assertion nodes**; selection green at 21 passed, the reachable
neighbourhood at 201 passed. **After the cycle-1 fixes** (re-derived from the tree, not re-worded):
**25 test functions / 39 node IDs / 88 assertion nodes** (**26 / 40 / 93** after the cycle-2 fixes —
one new assertion for bound 10's counted-sites control, and one new test with four for bound 14), of
which 13 node IDs are now
`@pytest.mark.slow` (every subprocess-driving one) and 9 are `db_required` (was 7). Selection green at
39 passed; `tests/test_admin_binding.py` whole-file green at 72 passed;
`tests/test_db_engine_lifecycle.py` + `tests/test_admin_auth.py` — the two files that read this
module's and `session.py`'s text structurally — green at 93 passed.

### TDD red, and then a better red

The first red was a bare `ImportError` on a helper that did not exist. The agent then wired a **no-op
stub** so each AC would red on its own assertion rather than on collection — **10 failed, 9 passed**, and
the 9 passes were the correct ones: both byte comparisons (a no-op hook *is* byte-identical), the four
negative detector arms, the registration check, the one-hook AST check, the G-1 sweep. That is the right
instinct: a collection error tells you nothing about which claim is unmet.

### 22 mutants, every one red — and three of them changed the work

- **M13 survived and was a DEAD MECHANISM**: a `warnings.catch_warnings()` suppression around the
  capture's lazy imports, whose comment called it load-bearing. **Removed rather than narrowed**, with
  the reasoning recorded: all it could ever do is hide the one thing the byte comparisons exist to catch —
  a warning from the diagnostic's own import *is* the diagnostic changing something besides the section,
  so a red comparison there is the **correct** outcome. Now a declared open bound.
- **M16, M18 and M20 initially survived** → three claims being made without controls. Each got one. The
  best of them: the verdict's **MISMATCH** arm now has a probe where the failing connection is on
  PostgreSQL's maintenance database while the capture resolves to the derived `_test` one — **the card's
  headline "wrong database is a one-line proof", which nothing had ever actually taken.** And G-2's
  refusal consult got a probe with `TEST_DATABASE_URL` naming an invented non-`_test` database behind a
  dead port, so `NOT OPENED` (refusal fired) and `FAILED` (it tried) are distinguishable.
- **Two of its own first-draft mutants were NO-OPS reporting as survivors** (`None or connection.execute(…)`,
  `[] or sorted(…)`). Caught and rewritten as real deletions. **That is wave 50's trap 5 recurring in a
  fresh context** — a no-op mutant and a genuine survivor look identical — and it is now CARD-260's AC-5.

### AC-3 / AC-4 proved byte-identical, by SHA-256 over the whole output

Each probe is a throwaway test file in a temp directory, which is its own rootdir — so the repo conftest
(and with it CARD-255's lock guard) is **not loaded**, the plugin arrives only via `-p`, and "not passed"
is the control. Same file, same directory, run twice:

```
AC-3 ordinary assertion failure: with=0e253e3e23429968 without=0e253e3e23429968 bytes=914/914 identical=True
AC-4 one pass + one skip       : with=1726b62ab40a0b8b without=1726b62ab40a0b8b bytes=375/375 identical=True
```

The only normalisation is a duration token — **which is also how the agent avoided recording a timing**.
AC-1's "traceback intact" needed one further normalisation, hex object addresses, because two processes
print different `id()` values in a default traceback's `self = <…>` lines; it is used **only** there and
is documented at the function. AC-2's real-suite half: `-p no:undefined-table-report` reds
`test_the_diagnostic_is_registered_in_this_very_run`.

### The broken-transaction trap — split, not avoided

Groups 1 and 2 read **libpq attributes only** (`get_dsn_parameters()`, `get_backend_pid()`, `status`,
`get_transaction_status()` via `error.cursor.connection`) — these answer from the client's own handle and
issue **no SQL**. Every question needing SQL goes to a **separate** connection whose URL comes from
`tests.db_name.resolve_test_database_url` and is screened by `conftest._refusal_reason` before anything
opens. Measured rather than reasoned: a query through the failing connection raises
`InFailedSqlTransaction`, while `get_dsn_parameters()`/`get_backend_pid()` answer fine on that same
handle. **M2** (rebuild the capture on the failing DBAPI connection) is the control. Both transaction
states are now on record — the AC-1 probe's connection is `INERROR`, the real instance below was already
rolled back at `IDLE` — **and the libpq-only approach reads both.**

### What it prints, from a provoked real instance — the card's "what success looks like", first try

```
group-1 failing-connection: dbname=…card_258_07a8a3b5229b_test host=localhost port=5432 backend_pid=64079
                            libpq_status=READY txn_status=IDLE [libpq attributes, no SQL]
group-1 error: class=psycopg2.errors.UndefinedTable sqlstate=42P01 message=relation "puzzles" does not exist
group-2 app-engine: id=0x10a2a3770 pool=Pool size: 5 … reset_engine_calls=0
group-2 failing-dbapi-connection: dbname_matches_app_engine=yes [a comparison, not a provenance]
group-3 process: pid=64053 hook_thread=MainThread alive_threads=['MainThread']
group-3 traceback: werkzeug_frames=['werkzeug/test.py:1162:get', …] frames=51
group-4 capture-connection: current_database=… current_schema=public search_path="$user", public backend_pid=64081
group-4 schema-now: to_regclass('public.puzzles')=None to_regclass('puzzles')=None pg_tables(puzzles)=[]
group-4 failing-backend-from-server: pid=64079 datname=… state=idle query=ROLLBACK [the server's own view]
group-4 verdict: failing-dbname=…card_258_07a8a3b5229b_test app-engine-dbname=…card_258_07a8a3b5229b_test
                 capture-dbname=…card_258_07a8a3b5229b_test vs-app-engine=MATCH vs-capture=MATCH
                 [vs-app-engine is the binding verdict … vs-capture only says whether schema-now … ]
```

Right database (`vs-app-engine=MATCH`), table genuinely absent — **not** a wrong-place lookup.
The verdict line above is the **cycle-1** format: at `8e40c0c0` it printed one unlabelled
`MATCH`/`MISMATCH` over `failing-dbname` vs `capture-dbname`, which F-003 showed reads as a binding
verdict while comparing a pair that is legitimately unequal whenever `DATABASE_URL` and
`TEST_DATABASE_URL` disagree. Re-captured from a provoked instance after the fix, not re-worded.

### ⚑ A premise of this card is REFUTED, which is why it asked

Point 3 said these five "are the only ones in the suite that serve real HTTP **from a thread**… a fact
worth confirming rather than assuming." **It does not hold.** `alive_threads=['MainThread']` and the
werkzeug frames are `werkzeug/test.py` — Flask's **in-process test client on the main thread**, not
`werkzeug/serving.py`. (The helper reports the werkzeug *module path*, not the basename, precisely because
a bare `test.py` reads as ours.) One provoked instance is what that rests on.

### ⚑ And a hypothesis offered with evidence — which the orchestrator then REFUTED for the gate scenario

The agent proposed, from provoking the error rather than from looking for a cause: the five fail
deterministically when `DATABASE_URL` names an **existing but unmigrated** database; the table is
genuinely absent from the right database at `reset_engine_calls=0`; after one schema build the file is
52/52 green; and — by grep over `tests/test_*.py` in sort order — nothing before `test_admin_binding.py`
builds the schema. It named its own gap: *that the gates' actual collection order matches file sort
order*, which it could not test without a full-suite run.

**I tested that gap with `--collect-only`, which runs no tests, and the gap is where it fails.**

- **Collection order is not file sort order.** Subdirectories come first: of 211 collected files,
  `tests/e2e/…` and `tests/property/…` occupy positions 1–31 and **`test_admin_binding.py` is position 32.**
- **The very first file collected builds the schema.** `tests/e2e/test_admin_workflow.py` has **18 test
  functions taking `client` as a parameter** — verified by AST, not by grep, because a word-boundary grep
  over the other four candidates matched prose and the AST check cleared them.
- **And `client` → `app` → `db_session` → `request.getfixturevalue("_test_database_tables")` → `alembic
  upgrade head`**, session-scoped. So in a full-suite gate run the schema **is** built, by position 1,
  long before position 32.

So the mechanical account is **correct for the agent's reproduction and wrong for the gate**: it
reproduced the signature in a scenario the gate does not have (one file, in isolation, against an
unmigrated database). The agent was right to call it a hypothesis and right not to act on it (G-5).

**What this leaves is sharper than what we had.** In a gate run the schema *was* built before those five,
so the next occurrence is either (a) a schema built and then lost, (b) a connection that cannot see it —
wrong database or wrong `search_path` — or (c) a session-scoped fixture torn down and rebuilt mid-run.
**Those three are exactly what `to_regclass` + `current_database` + `pg_stat_activity` + the verdict line
now distinguish, on the first occurrence, for free.** The card did its job and did not need the
hypothesis to be right.

### `src/nonogram/db/session.py` — needed, and G-1 proved mechanically

An engine's `id()` cannot distinguish *fresh because `reset_engine()` ran* from *never built*, so the
counter is the datum. Added `_reset_count`, incremented in `reset_engine()`, plus read-only
`reset_count()`, documented as counting **calls** not disposals. G-1 is not asserted but walked:
`test_nothing_in_src_calls_the_reset_counter` parses every `*.py` under `src/` by AST for a `Call` whose
callee is `reset_count` and asserts the list empty. **M11** (a caller added inside `session.py`) reds it;
**M10** (the increment removed) reds the engine-group test. `tests/test_db_engine_lifecycle.py` —
including CARD-257's convention-text and globals-counting tests, which read this module's AST — is green.

### Declared bounds, not closed

1. **It does not name the engine the failing connection came from** — the exception carries a DBAPI
   connection and nothing naming an engine. Group 2 prints `dbname_matches_app_engine=yes/no`, labelled a
   comparison, not a provenance. *Re-derived at cycle 1 (F-003):* group 4's verdict now prints the same
   comparison a second time as `vs-app-engine=MATCH/MISMATCH`, beside the separately labelled
   `vs-capture` pair. Still a comparison of database **names** and still not a provenance of
   connections — a failing connection from a different engine on the same database reads `MATCH`.
2. **It does not report the failing connection's own `search_path`** — that needs a query and only the
   unusable connection could answer. `pg_stat_activity` is asked about the failing *backend* instead,
   which gives its database from the server's side.
3. **The detector's sqlstate arm has no real reach today** — no psycopg2 error takes it without also
   matching the class arm. Exercised only by a fabrication; it exists for a non-psycopg2 driver. Declared
   in the docstring, not claimed as coverage.
4. **A lazy-import warning would break the byte comparisons** — left open deliberately (M13).
5. **The sixth gate variant is out of reach** — `uuid.UUID(hex=<float>)` is a different class and the hook
   is silent for it, by design.
6. **An error dying inside a werkzeug server thread without propagating is invisible** — the hook only
   sees what reaches pytest.
7. **AC-4's skip-profile half is measured on the AC-4 selection only**, plus the structural argument that
   the plugin implements one hook and it is not a collection or setup hook (M1 reds it). *Re-derived at
   cycle 1 (F-002):* that structural argument no longer rests on one syntactic shape. The hook set is
   read from `dir(diagnostic)` filtered on callable `pytest_*` attributes — the authority pluggy itself
   consults, so an **assigned** hook (`pytest_runtest_setup = _spy`, measured live as firing once per
   test) is seen — with the AST arm kept as a second reading that also covers `def`, `async def`,
   assignment and annotated assignment and **reds on any module-level binding target it cannot name**.
   Measured: old arm `{}` / new arm `{'pytest_runtest_setup'}` on the assignment shape, held by
   `test_the_one_hook_guard_reds_on_a_hook_that_is_assigned_not_defined`. What remains open is the
   nested `def` — which is not a live hook unless it is also bound to a module global, at which point it
   is the assignment shape and is seen. *Re-derived at cycle 2 (F-015):* the byte comparisons hold
   **output identity** and nothing about cost. Under the same `pytest_runtest_setup = _spy` mutant,
   `test_an_ordinary_assertion_failure_is_byte_identical` and
   `test_a_passing_run_with_a_skip_is_byte_identical` both stayed **green** while the one-hook guard red
   — a hook that prints nothing is byte-identical by construction. So the per-test-cost half of this
   bound is held by the one-hook guard **alone**, and the byte comparisons contribute nothing to it;
   that division of labour is now stated at the guard's own docstring rather than only in the cycle-1
   `[Adversarial]` narrative, which is where this card's discipline puts a residual.
8. **The matrix is ANY-RED per test node, not per assertion** — **93** assertion nodes is the
   denominator after the cycle-2 fixes (88 after cycle 1, 48 at `8e40c0c0`), and it does **not** claim
   all 93 are reached. Re-derived by `ast` over the card's own test class, not re-worded: **26** test
   functions / **40** node IDs (was 25 / 39). The cycle-2 delta is +5: one assertion for the
   counted-sites control at bound 10, and four in the new
   `test_registering_a_second_time_returns_none_instead_of_ending_the_run` (bound 14). The F-011
   deletion removed code but no assertion.
   *Exactly the domain discipline wave 50 promoted, applied unprompted.*

### Declared bounds added at review cycle 1

9. **The new global is spelled with `+=`** — an `ast.AugAssign`, and so outside the `ast.Assign` sweep
   CARD-252's `test_it_resets_exactly_the_globals_the_builder_creates` derives its globals from. That
   test's agreement between builder and reset is **silent** about `_reset_count` rather than covering it;
   its green is not evidence about this name (F-004). Declared at `_reset_count` in `session.py`. The
   honest repair — teaching `_global_names_assigned_by` about `AugAssign`/`AnnAssign` and restating the
   equality as a subset relation — lands in `tests/test_db_engine_lifecycle.py`, outside this card's
   four-file scope, and is left for a follow-up card.
10. **G-1's sweep is a bound, not a proof.** It reds on four shapes, each with a control
   (`test_the_src_sweep_reds_on_every_shape_it_claims`): a call whose callee it can name, a bare
   name/attribute reference (the alias shape), a string literal equal to or ending in the accessor's
   name (the `getattr` / `globals()[…]` / `vars(…)[…]` / dotted-path shapes), and — by deny-default,
   ADR-0039/R2 — **any call site whose callee it cannot name at all**, held to an equality against the
   three such sites under `src` today, each a named exemption with its reason (ADR-0039/R3:
   `nonogram/admin/app.py` ×2 `_regrade_batch`, `nonogram/orchestrator.py` `shape_for_mode`; keyed by
   file and inner callee, not by line number, so a reformat does not red it). What it still cannot see:
   a name assembled at runtime (`"reset_" + "count"`), or reached through a `sys.modules` entry under a
   computed attribute name — spelled nowhere a parse can find it, and narrowed by the deny-default to
   shapes that also call nothing the sweep can name. Measured at cycle 1: the guard as first written
   caught **0 of 4** indirect shapes; the sweep now catches 4 of 4 and still catches the direct one.

   *Re-derived at cycle 2 (F-011) — the `strings` arm now has **no carve-out at all**.* The cycle-1 fix
   had excluded every leading string expression under `src` from that arm and called it "docstrings
   excluded"; the exclusion is **deleted**, not controlled. Two reasons, both measured on this tree, not
   argued: (i) no control could fail on it — disabling the clause, returning `set()` from the collector,
   and narrowing it to real docstring holders each left `tests/test_admin_binding.py` at **72 passed**,
   which is what ADR-0039/R3 forbids; (ii) the mechanism was dead against real input — of the **5501**
   string constants under `src/`, **1073** were being excluded as leading strings and **none of the 5501**
   can satisfy the arm's predicate (`== "reset_count"` or `.endswith(".reset_count")`), because prose
   ends in a period. Deleting it also removes a fourth claim site: `session.py`'s and
   `undefined_table_report.py`'s docstrings already stated the arm **unqualified**, and now say exactly
   what it does. The accepted cost is ADR-0039/R2's preferred direction and not a defect: a future `src/`
   docstring whose text literally **is** `reset_count`, or ends in `.reset_count`, reds the sweep — and
   earns a named exemption with a real control at that point, rather than being pre-absorbed by a blanket
   one. Verified after deletion: whole file still **72 passed**, and the arm still bound — making the
   `strings` arm match nothing still reds exactly the four controls `[dotted]`, `[getattr]`, `[globals]`,
   `[vars]`, so the deletion loosened nothing a control was holding.

   *Re-derived at cycle 2 (F-013) — the deny-default's exemption is an equality over **counted sites**.*
   Each key now declares how many `f(...)(...)` sites it accounts for (`app.py` `_regrade_batch` → 2,
   `orchestrator.py` `shape_for_mode` → 1) and the assertion is
   `dict(Counter(sites)) == {key: count}`, following `_EXEMPT_HAND_SET_SITES` in
   `tests/test_db_engine_lifecycle.py` ("an equality over counted sites, not a floor"). Measured in the
   direction the pair-set equality was blind to: appending a third `_regrade_batch()()` to
   `src/nonogram/admin/app.py` now reds the sweep (`found 3 / expect 2`) where before it stayed **green**;
   the multiplicity the count depends on has its own control, a probe with two same-key sites asserted to
   report two entries rather than one key. **Residual, declared rather than implied:** the key is still
   `(file, inner callee)`, so a third site that *replaces* one of the two counted ones — same file, same
   inner callee, different line — is indistinguishable from it. Line numbers are deliberately not in the
   key (a reformat would red it), and such a site would still have to trip the `references` or `strings`
   arm to be a reach at all.
11. **A failure inside `_attach` cannot be named, only contained.** `_attach` is the hook's only channel,
   so the hook now wraps it too (F-009) and swallows a non-control-flow failure there rather than
   letting it escape into pytest's reporting and mask the failure AC-5 protects. The consequence is
   declared: a report whose `longrepr` rejects both spellings carries no section and says nothing about
   why. `KeyboardInterrupt`/`SystemExit` still pass through, there and at the two other
   `except BaseException` handlers (F-005), which
   `test_no_guard_in_the_diagnostic_absorbs_control_flow` holds over the module's own AST so a handler
   added later is covered rather than assumed.
12. **The verdict's two pairs answer two different questions, and only one is about binding.**
   `vs-app-engine` compares the failing connection's dbname against the app engine's own
   (`engine.url.database`, built from `DATABASE_URL`) — the binding verdict. `vs-capture` compares it
   against the capture connection, which resolves `TEST_DATABASE_URL` or the derived per-worktree name
   and **never reads `DATABASE_URL`**, so it answers only whether `schema-now` describes the same
   database. The two are legitimately different in any run where those variables disagree — a
   configuration `tests/database_guard.py` admits, `scripts/README.md` documents, and only
   `scripts/run_admin_tests.sh:83` equalises. Before cycle 1 the second pair alone was printed as a bare
   `MISMATCH`, i.e. the card's headline proof of a *wrong* database printed over a correctly bound one
   (F-003); both arms now have a probe
   (`test_a_connection_on_the_wrong_database_is_a_one_line_proof`,
   `test_the_verdict_does_not_call_a_correctly_bound_connection_a_mismatch`), and with no capture
   connection at all the verdict line still says only that (unchanged).
13. **Bound 3 re-derived and confirmed unchanged.** The detector's sqlstate arm still has no reach
   beyond the `_WithSqlstate` fabrication: the cycle-1 work added `_chain` and `_one_line` boundary tests
   and a cyclic-chain test, none of which gives that arm a real psycopg2 error, and the detector's seven
   parametrisations are untouched. Bound 4 (the lazy-import warning left open) and bounds 2, 5, 6 are
   likewise untouched by the cycle-1 fixes.

### Declared bounds added at review cycle 2

14. **`register()` returns `None` in two cases now, and the second one restores the run, not the
   registration.** Added at cycle 2 (F-012): the module refuses to register itself a second time
   (`config.pluginmanager.is_registered(sys.modules[__name__])`), because pluggy refuses one plugin
   object under a second name and a run that loads this module by its import path
   (`-p tests.helpers.undefined_table_report`) *and* lets the conftest register it died at configure
   time with `INTERNALERROR> ValueError: Plugin already registered under a different name` —
   reproduced on this tree before the fix. What the guard does **not** restore, declared rather than
   implied: under that invocation pytest has already registered the module under *its* name, so
   `hasplugin(PLUGIN_NAME)` is false and `test_the_diagnostic_is_registered_in_this_very_run` reds —
   one informative failure (72 passed, 1 failed) instead of an aborted session. No documented invocation takes
   that path (`addopts` is `-q`; the probes run under their own rootdir, where this conftest is not
   loaded), and `-p no:undefined-table-report` is unchanged. The guard has a control that fails:
   `test_registering_a_second_time_returns_none_instead_of_ending_the_run` builds a throwaway
   `PluginManager` (the class taken off the live `pytestconfig.pluginmanager`, not imported — `pluggy`
   is not in this project's declared baseline), registers the module under another name, and asserts
   `register()` returns `None`; measured with the guard deleted, that arm reds with the exact
   `ValueError` above, and a third arm provokes the same `ValueError` from pluggy directly so the
   refusal is shown real rather than hypothetical, while a fourth holds the ordinary path so the guard
   cannot be satisfied by refusing always.

### Orchestrator note — my own `-qq` slip, for the record

My first collection-order command passed `-q` on top of `pyproject.toml`'s `addopts = "-q"`, making `-qq`,
which collapsed the listing to 227 lines and returned **zero** matches — so my first reading was that
nothing collected at all. That is the trap recorded on CARD-250 and restated in four briefs this wave, and
I walked into it while verifying someone else's claim. Cost: one command.

---

## Orchestrator — review phase entry, 2026-10-21

- **[Env]** forge **2026.8.17**. This project has no `meta/.skills.yml`, so there is no
  `forge.min_version` to compare against (no skew verdict either way — the note exists so a later
  diagnosis is possible at all) and no `models:` block: the review / fix / AC-check agents are spawned
  **without** a `model:` override and inherit the session model.
- **[Scope]** `src/nonogram/db/session.py`, `tests/conftest.py`, `tests/helpers/undefined_table_report.py`,
  `tests/test_admin_binding.py` — `git diff --name-only main...HEAD` at `8e40c0c0`, worktree clean
  (`git status --porcelain` empty). `forge:fix` may touch only these four.
- **[Scope gate]** **IN_SCOPE.** `excess` = 0 — all four files fall under the card's `Touches`, and
  `src/nonogram/db/session.py` is the conditional entry (`only if a read-only accessor is needed`),
  which the implementation record shows was needed and taken additively. `comp_spread` **skipped**:
  this card has no `## Architecture context` section, so there is no declared component list to measure
  spread against. `poached` **empty**: the only `ready` sibling whose `Touches` intersect
  (**CARD-259** — `tests/conftest.py`, `src/nonogram/db/session.py`, 2 of its 3 paths) is in **wave 52**,
  not this wave, and was deliberately moved there at wave-51 dispatch; the poach metric is same-wave by
  definition. `guardrail_hits` **skipped**: G-1…G-5 are all behavioral (no entry names a forbidden
  path or glob), so they are the AC/EC/G gate's job, not this gate's.
- **[System contract]** Freshness re-checked at review entry, not assumed:
  `system_rules.py --card CARD-258` projects **29** rules; the card's section carries **10**. That is
  not drift — it is exactly the set `meta/kanban/curation.md` selects: all **5** `review-lens` rules
  (ADR-0022/R1, ADR-0038/R6, ADR-0038/R7, ADR-0038/R8, CON-021) plus the **5** reach-limited
  `kind: test` rules (ADR-0039/R1–R3, ADR-0036/R3–R4). The 19 dropped are plain `kind: test` rules the
  suite executes on every gate. Ids added: none. Ids removed: none. Section left as written, and it is
  what the reviewer is being judged against.
- **[Build gate 1 — PASSED, carried from the wave-51 dispatch session]** The run exists and is on the
  record in `meta/kanban/suite-timing.log`; what was missing is this note. Verbatim:
  `2026-10-20T18:12:00Z wave-51 card-258-build-gate-1-SOLO 1108s PASS (8649 passed, 1 skipped, 0 failed;
  EXIT=0) [128ms/test] — commit 8e40c0c0`. **Re-validated before being accepted as this cycle's gate,
  rather than trusted:** `git rev-parse HEAD` = `8e40c0c037761b0d194bbe42386f1020fccb1c5b` and
  `git status --porcelain` is empty, so the tree under review is **byte-identical** to the tree that
  passed — the one condition under which a carried gate is evidence and not a guess. Count reconciles:
  main 8628 + the card's 21 new node IDs = 8649. Scope `full` (`review.test_scope: full`), 1108s.
  Not vacuous: 8649 tests executed.
- **[Bookkeeping defect, source station: orchestrator]** Both wave-51 cards ran their build gates on
  2026-10-20 and **neither gate reached its card** — no `[Env]`, `[Scope]`, `[Build gate]` or
  `[Review sync]` note existed on either, and both cards still read `Status: in_progress` while their
  implementations sat committed in their worktrees. The runs were logged in `suite-timing.log` only.
  Per the CARD SYNC PROTOCOL the card file is the only durable copy, so a gate that lives in the timing
  log and not on the card is a gate nobody downstream can read. Recorded here rather than silently
  backfilled.

### [Review 1/3] Score: 7.5 — FAILS the gate twice over (7.5 < min_score 8, and 3 open Important)

Report: `meta/review/20261021T051223Z-CARD-258-cycle1.yml` — 10 findings, 10 system-contract verdicts,
parses under `yaml.safe_load`. **[Review sync]** 1 report → `meta/review/` (the worktree copy is
uncommitted and dies with the worktree; this is the durable one).

**Step 8h coverage: PASS.** Count line present and all 10 of the card's curated rules carry a verdict
line — 7 ✓ holds, 1 ⚠ unchecked (ADR-0039/R3, typed `no_eligible_fact`), 2 ✗ violated (ADR-0039/R1 and
R2, both tied to F-001/F-002). The reviewer also checked G-1, G-3, G-4, G-5 and CLAUDE.md's
import-direction rule beyond the card's list, which is legal and is logged rather than penalised.

**No AC fails, and the reviewer re-derived the one that could not be measured directly.** AC-4's
suite-level half (declared bound 7) was verified against *pytest 9.1.1's own source* rather than
accepted: `_pytest.runner.check_interactive_exception` returns `False` for `Skipped`,
`unittest.SkipTest`, `BdbQuit` and `wasxfail`, so `pytest_exception_interact` cannot fire on a pass, a
skip or an xfail — the skip profile genuinely cannot move. M13's bound was also confirmed **real rather
than engineered away**: removing `warnings.catch_warnings()` left AC-3's byte comparison falsifiable.
Declared bound 3 (the sqlstate arm) is honestly declared and **not** dead code dressed as coverage — its
`_WithSqlstate` fabrication is not an `UndefinedTable`, so deleting the arm reds that parametrisation.

**The three gating findings, all of them about reach rather than correctness:**

- **F-001 — Important — `tests/test_admin_binding.py:1074` — G-1's AST sweep claims more than it
  catches.** The callee is resolved as `func.attr` for an `ast.Attribute`, else `getattr(func, "id",
  None)`; every other shape yields `None` and is **skipped with no record**. Measured by execution, not
  argued: `getattr(session,"reset_count")()`, an alias, `globals()[...]()` and `vars(session)[...]()` —
  **0 of 4 caught**. The exhaustive claim is made twice (`test_admin_binding.py:1060-1061` and
  `session.py:353-355`). G-1 itself holds today by direct grep; this is about the guard that must keep
  holding it. Violates **ADR-0039/R2** (an unanalysable shape must be a failure, never a silent pass).
- **F-002 — Important — `tests/test_admin_binding.py:1023` — the one-hook guard cannot see an assigned
  hook, and G-4 *and* AC-4's bound 7 both rest on it.** The set is built from `tree.body`
  FunctionDef/AsyncFunctionDef only. Demonstrated under pytest 9.1.1: a plugin containing
  `pytest_runtest_setup = _tax` fired **once per test** (pluggy resolves hookimpls by `getattr` over
  `dir(module)`) while the guard's own expression reported only `{'pytest_exception_interact'}`. So
  `:1015-1021`'s claim that an added `pytest_runtest_setup` "would red this" is false for exactly that
  shape — and the byte comparisons cannot substitute, because a per-test hook that prints nothing is
  byte-identical. Violates **ADR-0039/R2**.
- **F-003 — Important — `tests/helpers/undefined_table_report.py:482` — MATCH/MISMATCH may compare the
  wrong pair.** The capture resolves its expectation through `resolve_test_database_url`, which reads
  `TEST_DATABASE_URL` or derives the per-worktree name and **never reads `DATABASE_URL`** — while the
  engine the failure came out of is built from `DATABASE_URL` (`session.py:199`). The suite explicitly
  supports the two differing (`conftest.py:222` branches on exactly that equality, and the five target
  parametrisations are not `db_required`). In such a run the verdict prints MISMATCH on every occurrence
  while the connection sat exactly where it was told — **the inverse of the card's headline proof**, and
  one of the three accounts the card claims the verdict distinguishes.

**[Adversarial] F-001 CONFIRMED** — four refutation routes tried, all failed. The skeptic did not read the
reviewer's reasoning; it re-ran the guard's own callee-resolution expression itself. Evidence:
`test_admin_binding.py:1077-1081` resolves `func.attr if isinstance(func, ast.Attribute) else
getattr(func, "id", None)` with **no `ast.Subscript` branch, no unresolved-callee collection and no
deny-default** — `name is None` falls through with no record. Over a scratch file: `getattr(...)()` →
`None`, `globals()[...]()` → `None`, `vars(...)[...]()` → `None`, the alias → `'f'`; the direct shape
→ `'reset_count'`, **caught**. Then end-to-end against a **copy** of the real 60-file `src` tree with
all four indirect reaches injected: `files swept: 60 · callers found: [] · GUARD VERDICT: GREEN`, and
the control (same replica plus `session.reset_count()`) → **RED**. So the replica discriminates and the
gap is reachable end-to-end, not theoretical. The wider claim is textually real:
`test_admin_binding.py:1060-1061` says "a call added anywhere under it reds this" with "a call"
unqualified, and `session.py:353-355` asserts the property is *held by* the mechanism.
- **The verdict strengthens the finding in two ways the report did not state.** (1) It is a
  **mandatory-rule violation by the mechanism itself**, not only by the prose: ADR-0039/R2 says a shape
  the guard cannot analyse is a FAILURE, never a silent pass, and the `None` fall-through is exactly
  that — so R2 is violated however charitably the docstrings are read. The skeptic also found that
  ADR-0039's 2026-10-19 scope revision added `src/nonogram/**` *specifically because* source docstrings
  claiming what a test catches were the costliest instances of this family (19 gating findings, 2
  escalations across CARD-238/228/239). (2) **There is a third claim site the finding does not cite** —
  `tests/helpers/undefined_table_report.py:334-336` repeats the unnarrowed G-1 claim. A fix touching
  only the two cited sites would leave this one overclaiming. **This goes into the fix prompt.**
- **Severity holds at Important, and the skeptic said why rather than deferring to the reviewer:** G-1's
  underlying property is **true today** (`grep -rn reset_count src/` finds only the definition, its
  docstring and the `global` statement), so this is a guard-discipline/ADR-conformance defect with no
  production bug behind it.
- **Precedent for the fix, found by the skeptic:** the pre-existing `reset_engine` docstring at
  `session.py:~295-339` already models the required discipline — it enumerates its own blind spellings,
  explicitly including "a `globals()` or `vars()` write", and states it is **not** a proof, adding that
  "an AST deny-default was tried for exactly that claim and withdrawn." The new accessor's docstring
  makes precisely the unqualified claim its immediate neighbour refuses to make.

**[Adversarial] F-002 CONFIRMED** — all four refutation routes failed, three of them closed by execution
rather than reading. The skeptic worked from the claim and the code only.
- **Link 1 — the guard reads only top-level `def`s.** `test_admin_binding.py:1023-1031` builds `hooks`
  from `tree.body` filtered on `(ast.FunctionDef, ast.AsyncFunctionDef)`. No tree walk, no `ast.Assign`
  collection, **and no cross-check against `dir()` of the module it has already imported** — `diagnostic`
  is in scope on that very line, and `test_the_diagnostic_is_registered_in_this_very_run:999` checks only
  `hasplugin`/identity, never the hookimpl set.
- **Link 2 — pluggy really does register an assigned hook.** pytest 9.1.1 / pluggy 1.6.0 / Python 3.14.3,
  fresh temp rootdir with this repo's conftest never loaded. Probe A (`-p` load, plugin containing no
  `def pytest_runtest_setup` at all, only `pytest_runtest_setup = _spy`): fired **once per test**,
  `calls=2`. Probe B through **this repo's own registration path** —
  `config.pluginmanager.register(sys.modules[__name__], PLUGIN_NAME)`, as `tests/conftest.py:104` calls
  it — also `calls=2`, with `pluggy-visible pytest_* attrs on plugin: ['pytest_exception_interact',
  'pytest_runtest_setup']`. Against the same mutant the guard's own expression reports
  `GUARD SEES: {'pytest_exception_interact'} · GUARD PASSES: True`.
- **Link 4 — the byte comparisons provably cannot substitute.** The skeptic replicated AC-4's
  `test_a_passing_run_with_a_skip_is_byte_identical:939` against a plugin that is guard-clean *and*
  carries a silent assigned per-test hook (counts, queries nothing, prints nothing). The raw outputs
  differed only in the timing line — which `_probe_run`'s own `_without_durations:670`
  (`re.sub(r"\d+\.\d+s", "<duration>s", output)`) erases. After that substitution:
  `with_hook == without_hook -> True` **and** `guard PASSES: True` simultaneously. AC-3's comparison uses
  the same helper, so it behaves identically. **The card's two byte-comparison controls are blind to
  exactly the hook shape its one-hook guard is blind to.**
- **Link 3 — nothing else backs G-4 or bound 7.** A grep for `get_hookcallers|hook_impls|_hookimpls|
  parse_hookimpl|dir(diagnostic)|dir(module)` across all three test files in the diff returns **no hits**:
  no runtime hookimpl enumeration, no per-test counter, anywhere. And bound 7 names the AST guard as its
  own backing in so many words (card line 304-305: "plus the structural argument that the plugin
  implements one hook"). The reviewer's `check_interactive_exception` re-derivation establishes G-4 for
  **the code as written today**, but it is an argument rather than an executing control and speaks only
  to `pytest_exception_interact`'s own firing conditions — it says nothing about a *second* hook being
  added, which is the one job this guard claims.
- **The skeptic's own two qualifications, recorded because they narrow the finding honestly:** (1) the
  *nested-`def`* half of the claim is weaker than written — a nested `pytest_*` is invisible to the guard
  but is not a live hook unless also bound to a module global, at which point it is the assignment shape
  again; **the assignment shape is the load-bearing one and it is fully live**. (2) **G-4 is not violated
  today** — the module really does define exactly one hook. The defect is the guard's reach, i.e. what
  keeps G-4 holding after this card, not current behaviour.
- **The rule this card itself put in scope.** ADR-0039/R2 requires a guard's set to be derived from an
  authority the runtime can enumerate, defaulting to deny on an unanalysable shape. The skeptic's point
  is that **the authority R2 asks for exists here and is one call away** — `dir(diagnostic)` on the
  already-imported module, which is precisely what pluggy itself uses.

**[Adversarial] F-003 CONFIRMED** — five refutation angles tried, all failed, and the inversion was
**reproduced live** rather than argued.
- **Links 1 and 2 are code facts.** `undefined_table_report.py:481-487` resolves the expectation via
  `db_name.resolve_test_database_url(os.environ, db_name.REPO_ROOT)`, and the verdict at `:553-578`
  compares `failing_dbname` against `here[0]` — `current_database()` **on the capture connection**, i.e.
  on the engine built from that resolution. `tests/db_name.py`'s entire resolution is three lines
  (`TEST_DATABASE_URL` if exported, else the derived per-worktree name) and the string `DATABASE_URL`
  **appears nowhere in the file**.
- **Link 3 — the divergence is reachable, and the skeptic reached it.** The suite's only `DATABASE_URL`
  write is `conftest.py:621`, inside the *function-scoped* `db_session` fixture; no session-scoped or
  autouse hook aligns the two. The five target parametrisations use a **local** `client` fixture
  (`test_admin_binding.py:290-295`) that calls `admin_app.create_app()` directly and carry no
  `db_required` marker, so they run against the ambient `DATABASE_URL`. `scripts/run_admin_tests.sh:83`
  equalises the two — **but a bare `pytest`, the run command CLAUDE.md documents, does not**, and
  `scripts/README.md:112-131` explicitly tells the owner to `export DATABASE_URL=".../my_other_test"`.
  Live run with `DATABASE_URL` on a fresh `nonogram_f003_app_test` and `TEST_DATABASE_URL` unset — a
  configuration `tests/database_guard.py`'s `TEST_MARKERS = ("test",)` **admits without refusal** — gave
  `5 failed`, each an `UndefinedTable` on `puzzles` from `puzzle_review.py:2329`, and printed:
  `group-4 verdict: failing-dbname=nonogram_f003_app_test
  capture-dbname=nonogram_pythonproject4_card_258_07a8a3b5229b_test MISMATCH` while
  `group-2 … dbname_matches_app_engine=yes`. **MISMATCH on all five occurrences, with the connection
  sitting exactly where `DATABASE_URL` sent it.**
- **Link 4 — the one real mitigation, stated precisely.** The *whole* section does disambiguate: group 2
  prints the app engine's URL plus an explicit `dbname_matches_app_engine=yes/no`, and the verdict line
  labels its second term `capture-dbname=` rather than `expected=`, which is honest. But the card's claim
  at its own line 49 is a **one-line** proof — "a connection to the *wrong* database is a one-line
  proof" — and that one line, read alone, asserts the wrong conclusion in this configuration. The
  finding survives as written; its severity rests on the one-line reading, not on the report being
  unreadable.
- **Link 5 — no test separates the two causes, by construction.** `_PROBE_UNDEFINED_TABLE:572-577` sets
  `os.environ["DATABASE_URL"] = resolve_test_database_url(...)`, so its MATCH arm **can only match**;
  `_PROBE_FAILING_CONNECTION_ELSEWHERE:612-634` builds the failing engine from `resolved` and flips only
  the failing side. No test anywhere sets `DATABASE_URL` divergent from the resolved URL and asserts the
  verdict's meaning.
- **Hygiene, checked:** repo and both worktrees unmodified; `nonogram_poc` untouched;
  `_refuse_unless_test_database` untouched; the scratch database created and dropped; only the 5 target
  node ids run (1.89s).

### [Severity gate 1/3] 7.5 < min_score 8 **and** 3 confirmed Important — the success path is closed

critical: 0 · important: **3** (F-001, F-002, F-003 — all CONFIRMED, none refuted, none dropped).
Either condition alone would close it. Adversarial verification was run unconditionally even though the
score already failed, because an unverified false positive sent to the fix agent costs a fix *plus* a
re-review cycle — and in this case it earned its keep three times over: it found an uncited third claim
site for F-001, proved F-002's blind spot is **shared by the card's two byte-comparison controls**, and
reproduced F-003's inversion on a real database. → `forge:fix`, cycle 2 to follow.

### [Fix 1] FIX PRE-GATE: PASS — 9 fixed, 1 skipped, every named test exists and passes

**Test half.** Ran **exactly** the 14 tests named across the `FIXED` lines (no more, no less):
`22 passed, 50 deselected in 4.83s` — 14 names resolving to 22 node IDs through parametrisation, with
`DATABASE_URL` on the worktree's derived `…card_258_…_test` database so the `db_required` arms executed
rather than skipped. No `FIXED` line names a test that is missing or red, so nothing bounces.
**Declarations half.** Every `FIXED` line carries a matching `DECLARATIONS` line, and the "updated"
claims are real in the diff rather than asserted: bound 8 reads **88** assertion nodes against the old
**48** (`git diff` shows both the bound row and the implementation record's count line changing), bounds
**9–13 added**, bounds **1 and 7 re-derived**. Bound 13 is a **"re-derived and confirmed unchanged"**
outcome for bound 3 — the legitimate third answer the contract allows, taken rather than avoided.
**Scope.** Worktree diff is `+845/−46` across exactly three of the four in-scope files;
`tests/conftest.py` was in scope and needed no change, which the agent said instead of touching it.

- **[Fix 1] declarations: 4 updated, 1 confirmed, 5 added, 0 none.**
- **⚠ MY OWN BRIEF WAS WRONG, and the fix agent caught it rather than following it.** I told it to hold
  the deny-default "to an equality against today's sites (**which is zero**)". I had inferred that from
  the F-001 skeptic's `grep -rn reset_count src/` result — but that grep is about *calls to
  `reset_count`*, not about *callee shapes the guard cannot analyse*, and I conflated the two. Measured
  over the real 60-file `src` tree, there are **3**: `src/nonogram/admin/app.py:6271` and `:6291`
  (`_regrade_batch()()`) and `src/nonogram/orchestrator.py:1385`
  (`sourcing.shape_for_mode(request.mode)()`) — all the `f(...)(...)` shape. **I re-derived this
  independently with my own AST sweep before accepting it, and got the same three sites.** Had the agent
  obeyed the brief, the new guard would have shipped with an equality against an empty set and **red on
  the first run**. They are now named ADR-0039/R3 exemptions with reasons, keyed by *(file, inner callee
  name)* rather than line number so a reformat cannot red them, and held to an equality in **both**
  directions — a new unanalysable shape reds, and a stale exemption reds too.
- **F-001 — the agent took the deny-default (R2) over narrowing, and justified why the withdrawal
  precedent does not bind.** The `reset_engine` docstring's withdrawn deny-default covered a far wider
  claim ("no test hand-sets these three globals", across the whole `tests/` tree, with `setattr`,
  `sys.modules`, unpacking); here the surface is one name under `src/`. Measured both halves: old guard
  **0 of 4** indirect shapes caught, new sweep **4 of 4** plus the direct control. The sweep now reports
  four kinds — nameable calls, bare name/attribute references (the alias shape), string spellings
  (`getattr`/`globals()`/`vars()`/dotted path, docstrings excluded), and the deny-default.
- **F-002 — runtime arm primary, as ADR-0039/R2 asks.** Hook set is now `dir(diagnostic)` filtered on
  callable `pytest_*` — what pluggy itself does — with the AST arm **kept** and extended to
  `Assign`/`AnnAssign` plus a deny-default on module-level targets it cannot name. Measured: old AST-body
  expression `{}` vs new runtime arm `{'pytest_runtest_setup'}` on `pytest_runtest_setup = _spy`. Both
  skeptic qualifications were respected rather than overclaimed: the assignment shape is load-bearing,
  the nested `def` is only live once bound to a module global (which *is* the assignment shape), and G-4
  is not violated today.
- **F-003 — verified by revert, which is the part that matters.** Invariant: *the binding verdict compares
  the failing connection's dbname against the database the app engine is bound to.* Discriminator:
  `engine.url.database` on `nonogram.db.session.engine`, built from `DATABASE_URL` (`session.py:199`) —
  explicitly **not** the capture connection's database, because `resolve_test_database_url` never reads
  `DATABASE_URL`. The line now prints both pairs, each named: `vs-app-engine` (the binding verdict) and
  `vs-capture` (does `schema-now` describe the same database). **Two probes now separate the two causes**
  — failing connection elsewhere → `vs-app-engine=MISMATCH`; `DATABASE_URL` divergent from the resolved
  URL → `vs-app-engine=MATCH, vs-capture=MISMATCH`. **With the old verdict restored, the new test fails
  printing the finding's own symptom** (`MISMATCH` over a connection sitting exactly where `DATABASE_URL`
  sent it), then green again after. Database hygiene held: nothing created, dropped or truncated;
  `nonogram_poc` never touched; `_refuse_unless_test_database` untouched.
- **[Protocol deviation, recorded not hidden]** The fix agent wrote to the **main-repo** card copy
  (bounds 1/7/8 re-derived, 9–13 added, the counts line and the "What it prints" sample re-captured).
  Under the CARD SYNC PROTOCOL the main copy is the orchestrator's and a worktree agent writes only the
  worktree copy. The DECLARATION contract simultaneously *requires* the card's bounds be corrected in the
  same fix, so the two rules collide for any card whose declarations live on the card. **I verified my own
  orchestrator notes all survived** — `[Env]`, `[Build gate 1]`, `[Review 1/3]`, all three `[Adversarial]`
  verdicts and `[Severity gate 1/3]` are intact, and `Review score:` still reads `7.5 (cycle 1/3)` — and
  I am keeping the content because it is correct and independently checked. The worktree copy still
  predates the implementation record; `done` 5b's one-way merge is append-only, so that is harmless.
- **Noted, not fixed, correctly outside scope:** `tests/test_db_engine_lifecycle.py`'s
  `_global_names_assigned_by` collects only `ast.Assign` targets, so its docstring claim that "a shape
  this function cannot analyse biases it to red" is **false** for `AugAssign`/`AnnAssign`. The honest
  repair is to collect both and restate the equality as a subset relation. **→ follow-up card.**

- **[Build gate 2 — PASSED, post-fix]** Full suite, solo under the board lock:
  **8667 passed, 1 skipped, 0 failed, EXIT=0** in 900.58s (15:00). Scope `full`
  (`review.test_scope: full`). Not vacuous: 8667 tests executed.
  **Count reconciles exactly and confirms the fix's own arithmetic:** main 8628 + the card's **39** node
  IDs = 8667, against gate 1's 8649 = 8628 + 21. The +18 is the cycle-1 fixes' new controls, and 39 is
  the number bound 8 now declares — so the bound and the gate agree rather than merely coexisting.
  The one skip is the long-standing `setrlimit(RLIMIT_AS)` platform skip, unrelated to this card.
  → review cycle 2.

### [Review 2/3] Score: 8.5 (7.5 → 8.5, Δ+1.0) — all three cycle-1 findings ✓ resolved, ONE new Important

Report: `meta/review/20261021T074734Z-CARD-258-cycle2.yml` — 8 findings (4 high / 4 low), 10
system-contract verdicts. **[Review sync]** 1 report → `meta/review/`. Full review, not confirmation mode
(cycle 1 discovered gating findings, and discovery resets the mode). Score clears `min_score: 8` and
`min_improvement: 0.5` — **and the severity gate still closes the success path, because one Important
stands.** That is the gate working as designed: a rising score is not a merge condition.

**Step 8h coverage: PASS** — count line present, all 10 rules carry a verdict: **9 ✓ holds, 0 ⚠,
1 ✗ violated (ADR-0039/R3)**. Cycle 1's two violations (ADR-0039/R1, R2) are both now ✓, each
re-derived by mutation rather than read: R1's claims measured by killing M2/M3/M4/M5; R2 confirmed
because both guard sets now come from authorities the runtime can enumerate (`dir(module)`; psycopg2's
own `extensions` names).

**All three cycle-1 findings resolved, and the reviewer re-derived each instead of accepting it:**
- **F-001 ✓** — an *independent* AST sweep that does not import the guard reproduces the three
  unanalysable sites exactly, and on real-tree replicas **4 of 4** previously-missed indirect shapes are
  now caught. **Both questions I asked were answered by execution:** the equality is genuinely
  **two-directional** (a new unanalysable key reds; a stale exemption reds three ways — renaming the inner
  callee, removing the sites, renaming `shape_for_mode`), and a rename **cannot** defeat the key. One real
  residual found: a *second* `f(...)(...)` in the same file with the *same* inner callee is absorbed
  silently → Minor F-013. Bonus datum: the "runtime-assembled name" shape bound 10 declares blind
  (`getattr(s, "reset_" + "count")()`) is in fact **caught** — the bound is conservative, not wrong.
- **F-002 ✓, and my specific worry was answered honestly.** The runtime arm is the guard's *first*
  assertion and is demonstrably live — verified by mutating the **production module**, not a synthetic
  one. On the byte-comparison blind spot: **it is confirmed still real but no longer load-bearing.** Under
  that same mutant both `*_byte_identical` tests stayed **green** while the guard red — so the guard, not
  the byte comparison, is now what backs G-4 and bound 7. **The problem moved to the right place rather
  than being closed**, which is the honest outcome and is what I asked to be distinguished. The residual
  is recorded only in the cycle-1 `[Adversarial]` narrative and not at bound 7 → Minor F-015.
- **F-003 ✓ and the revert claim reproduces.** Discriminator verified as the app engine's binding, not a
  neighbour: `_app_engine_dbname()` → `session.engine.url.database`, `_init_engine` reads
  `os.getenv('DATABASE_URL')` (`session.py:193`), and `tests/db_name.py` contains **no occurrence of
  `DATABASE_URL` at all**, so the two resolutions are provably independent. Revert re-derived as mutant
  M6: restoring the old capture-based comparison reds exactly
  `test_the_verdict_does_not_call_a_correctly_bound_connection_a_mismatch` **and nothing else**.

**The mutation check ran and it is what found the gating finding.** `review.mutation_check: true` and this
entered as the candidate passing cycle, so Step 8f executed instead of deferring: **8 mutants, 7 killed,
1 survived.** The survivor is M1 — the docstring exemption — and it is F-011. **Deferring would have
hidden it**, so it is reported as run. Restore verified byte-for-byte: all three files' SHA-256 match the
pre-mutation capture and `git diff --stat` is unchanged at `+845/−46`.

**F-011 — Important — `tests/test_admin_binding.py:873` — the exemption the F-001 fix added has no
control that can fail.** `_docstring_constants` grants the sweep's `strings` arm an exemption ("Docstrings
excluded" / "Prose is not a reach") and `_RESET_COUNTER_INNOCENT` is positioned as its control. That
control **cannot fail**: disabling the clause leaves the file green (**72 passed**), and deleting the
mechanism outright also leaves **72 passed**. ADR-0039/R3 requires "caught with the exemption removed,
missed with it in place" — neither holds. The stated justification is also measurably not the reason it is
needed: the arm matches only a string equal to `reset_count` or ending in `.reset_count`, which no
docstring under `src` does. Weight stated plainly by the reviewer: a guard-discipline/ADR-conformance
defect with **no reach consequence** — the function only ever collects a bare string expression statement
in first position, i.e. dead prose — exactly as F-001 was.

### ⚠ [Family] FAMILY REGRESSION, streak 1 of 2 — recorded now so cycle 3 is judged against it

**The one sentence the fixes keep getting wrong: _a guard's exemption is not established by the guard
staying green; it needs a control that fails when the exemption is removed._** — F-001/F-002 (cycle 1) →
F-011/F-013 (cycle 2), files: `tests/test_admin_binding.py`, `src/nonogram/db/session.py`,
`tests/helpers/undefined_table_report.py`.

**Attribution is mechanical, not inferred.** `git show HEAD:tests/test_admin_binding.py | grep -c
_docstring_constants` → **0**; working tree → **3**. F-011 is in the cycle-1 fix's **own new code**, in
the **same guard** it was fixing, under the **same ADR-0039 family**. Minor F-013 (same-key absorption)
and F-015 (undeclared byte-comparison residual) fall in that family too.

**This is the exact signature `review.family_regression` exists to catch** — the documented failure mode
is "a card ran six cycles with the score RISING the whole way while each fix created the next cycle's
finding in the same mechanism", and here the score rose **7.5 → 8.5** while the fix for three
reach-claim findings introduced a fourth. The stalled check is structurally blind to this shape: Δscore
+1.0 and Δfindings −2 both look like progress.

**Streak is 1, so the threshold of 2 is not met and I am NOT escalating** — the procedure continues into
the fix loop. But the consequence must be stated before cycle 3, not after: **cycle 3 is the last
(`max_cycles: 3`), and if it raises another finding in this family attributed to the cycle-2 fix, that is
streak 2 and the card escalates** with the family and three routes (design / undefined term / slice) for
the owner to choose between. **So the cycle-3 fix must be chosen to shrink this family's surface, not
add to it.** The reviewer offers two routes and they are not equivalent under this signal: adding yet
another control to the exemption *adds* mechanism to the family, while **deleting the exemption** (72
passed either way) *removes* the claim entirely and follows this card's own `warnings.catch_warnings()`
precedent. Deletion is the route that cannot regenerate the family.

**[Adversarial] F-011 CONFIRMED** — five refutation routes, all failed, and the mechanism turns out to be
not merely uncontrolled but **dead**.
- **Both measurements reproduce, and a third removal shape too.** Baseline `72 passed`. Mutation 1
  (exclusion clause can never exclude) → `72 passed`. Mutation 2 (`_docstring_constants` returns `set()`)
  → `72 passed`. Mutation 4, the skeptic's **own** attempt to find a red by narrowing the exemption to
  real docstring holders (`Module`/`ClassDef`/`FunctionDef`/`AsyncFunctionDef`) → `72 passed`. **Every
  removal-direction mutation is green.**
- **The one mutation that reds goes the wrong way.** Mutation 3 (over-exclude — treat *every* string
  constant as prose) reds 4 of the shape controls (`[dotted]`, `[getattr]`, `[globals]`, `[vars]`). That
  binds the `strings` **arm**; ADR-0039/R3 asks for "caught with the exemption removed, missed with it in
  place", and removal is green in every form the skeptic could write. **The arm has a control; the
  exemption does not.**
- **⚠ The mechanism is dead against real input, which is stronger than the finding claimed.** An
  independent enumeration of every string constant under `src/`: **1073** constants are excluded as
  docstrings, and **zero of them — and zero string constants of any kind under `src/` — can satisfy the
  arm's equality-or-dotted-suffix predicate.** A real docstring is prose and ends in a period or newline,
  so it cannot equal `reset_count` or end in `.reset_count`. The named control's own fixture proves it:
  `_RESET_COUNTER_INNOCENT`'s docstring is *"A docstring may say reset_count without being a reach."* —
  it passes with the exemption **and** without it.
- **A third claim site, which decides the route:** `src/nonogram/db/session.py:372-374` **already states
  the arm unqualified** — "the string `"reset_count"`, or any string ending in `.reset_count`" — with **no
  docstring carve-out. Under deletion that sentence becomes exactly true as written.**
- Restoration verified: `c1555f06…a67e` before and after all four mutations, byte-identical, no
  `git checkout/restore/stash`, worktree showing exactly the three expected modified files.

### Cycle-3 fix route chosen: DELETE the exemption (route b), on the skeptic's evidence, not on tidiness

I asked the skeptic to judge which route is less likely to regenerate the family, and it argued **(b)**
with three grounds I am adopting:
1. **(a) would make a third claim site false, and that site is production code.** Keeping the exemption
   means `session.py:372-374` and `undefined_table_report.py:369-372` must *also* be amended to declare
   it — **(a) adds a fourth claim to keep synchronised across three files; (b) removes one and leaves the
   other two accurate untouched.** The family's sentence is precisely "prose claims more than the test
   establishes".
2. **(a)'s control would be a fixture manufactured to rescue a dead mechanism.** A probe docstring
   `"""reset_count"""` satisfies R3 *in letter* — but the mechanism's **stated** reason ("this file's own
   docstrings write the accessor's name out") is measurably not the reason, since none of those 1073
   docstrings was ever a candidate. That is the same defect one level up: a control proving the mechanism
   does *something* while its justification still says something else. On a guard that has produced
   F-001/F-002 → F-011/F-013 in two cycles, **a claim whose only evidence is a synthetic input is the
   highest-probability way to produce the cycle-3 finding that escalates this card.**
3. **The project's own precedents point at (b), one of them in the file being changed.**
   `session.py:306-311` — the `reset_engine` backstop this card already cites as the model — says its
   count includes "an occurrence in a docstring, a comment or a string literal. **It over-reds; that is
   the safe direction for a backstop.**" ADR-0036/R4 is stated as "No string literal anywhere in
   `src/nonogram/**` — **docstrings included**". And ADR-0039's 2026-10-19 scope revision reached into
   `src/nonogram/**` *because source docstrings claiming what a test catches were this family's costliest
   instances*. **A docstring exemption inside a guard written under ADR-0039 points against the ADR's
   reason for reaching into `src/` at all.**

**(b)'s only cost is the ADR's intended behaviour, not a defect.** If someone ever writes a `src/`
docstring literally equal to `reset_count`, the sweep reds — and ADR-0039/R2 explicitly prefers that:
such a site then earns a **real** named exemption with a **real** control. The arm stays bound after
deletion (mutation 3 proves over-exclusion still reds 4 shape controls), so nothing the shape controls
held is loosened.

**And the risk of (b) is mechanical, so it is enumerated rather than trusted — delete ALL of it or the
family regenerates with the sign flipped:** the clause, `_docstring_constants` itself, the "Docstrings
excluded, see `_docstring_constants`" sentence in `_reset_counter_sites`'s docstring (`:911-912`), the
"prose" clause in `_RESET_COUNTER_INNOCENT`'s comment (`:975-976`) if it still implies an exemption is
working, **and the mention at the card's bound 10**. Leaving the prose anywhere after removing the
mechanism is the identical defect inverted. The `_RESET_COUNTER_INNOCENT` fixture itself **stays** — it is
honest as a neighbouring-accessor control, as long as nothing claims it controls a docstring exemption.

### [Fix 2] FIX PRE-GATE: PASS — the exemption is gone, and the family SHRANK rather than grew

**Test half.** The three named tests pass (9 node IDs). Whole file **73 passed** (72 before; the one new
test is F-012's own control). Both verifications I asked for came back, on the final tree: the file is
green, **and the `strings` arm is still bound** — making it match nothing still reds exactly `[dotted]`,
`[getattr]`, `[globals]`, `[vars]` (4 failed, 3 passed), so deleting the clause loosened nothing those
controls were holding.
**Declarations half.** All five `FIXED` lines carry `DECLARATIONS` lines; bound **10** re-derived, bound
**14** added, bounds **7** and **8** updated (8 re-derived to 93 assertion nodes / 26 test functions / 40
node IDs, from 88/25/39).
**I verified the deletion is complete rather than taking the claim:** `grep -c _docstring_constants` → **0**,
and the one surviving `docstring`-adjacent sentence is the **inverted** one —
*"**No carve-out for prose:** a docstring or comment whose text happens to BE the name, or to end in
`.<name>`, lands here like any other literal"* (`:901`). That is the claim now matching the code instead
of excusing it.
**Orchestrator markers all survived** (`[Env]`, both build gates, both `[Review N/3]`, `[Severity gate]`,
`[Fix 1]`, `⚠ [Family]`, all four `[Adversarial]` verdicts), and `git diff` shows **no `- G-N` row
changed** — the `## Guardrails` section is byte-identical again.

**The agent re-measured my brief's evidence instead of trusting it**, and went further than the number I
gave it: under `src/` there are **5501** string constants, **1073** of them the leading strings the old
mechanism excluded, and **0 of the 5501** can satisfy the arm's predicate. The mechanism was dead against
every string in the tree, not just against docstrings.

**F-013 was measured in both directions on the REAL tree, not a replica:** appending a third
`_regrade_batch()()` to `src/nonogram/admin/app.py` now reds with `found 3 / expect 2`, where the old
pair-set equality left it green. So the exemption is now an equality over **counted** sites, following
`test_db_engine_lifecycle.py`'s precedent ("an equality over counted sites, not a floor"), and the
`(file, inner callee)` key residual is **declared at bound 10** rather than implied.
`src/nonogram/admin/app.py` restored byte-for-byte (`shasum` `f68883ae…` unchanged).

**One addition beyond the brief, and it is the right instinct on a card with this family.** F-012's
one-line guard is itself a new mechanism, and the agent judged that shipping it without a control would
re-commit the family's error at a new site — so it built one:
`test_registering_a_second_time_returns_none_instead_of_ending_the_run`, measured to red with the exact
`ValueError: Plugin already registered under a different name` when the guard is deleted, plus a third arm
provoking that error from pluggy directly (so the refusal is shown real) and a fourth holding the ordinary
path (so the guard cannot be satisfied by refusing always). **`pluggy` is not imported** — outside the
declared baseline — the class is taken off the live `pytestconfig.pluginmanager` by an MRO walk that
**raises rather than defaulting to a pass**.

**F-012's residual, declared not hidden:** `pytest -p tests.helpers.undefined_table_report` no longer
`INTERNALERROR`s (**72 passed, 1 failed** — figure corrected at cycle 3; I had repeated the fix agent's
stale 71, which predated its own new control test), but pytest has registered the module under its own
import-path name, so
`test_the_diagnostic_is_registered_in_this_very_run` reds — **one informative failure instead of an
aborted session**, which is the honest improvement rather than a claim of full support. At bound 14 and in
`register()`'s docstring.

### [Family] streak assessment after the cycle-2 fix: the family SHRANK — 2 → 1 exemptions, 3 → 0 carve-out claims

Counted, not asserted: exemptions in the G-1 guard **2 → 1** (the survivor is the unanalysable-call
exemption, which already had a failing control in both directions and now also holds multiplicity), and
claims asserting a docstring carve-out **3 → 0**. The one mechanism added (F-012's guard) arrived with a
control measured to fail. **This is the first fix in this card's three cycles that removed more claim
surface than it added**, which is what route (b) was chosen for. The streak stays at **1** — cycle 3's
review decides whether it clears or reaches 2.

- **[Build gate 5 — PASSED, post-cycle-2-fix]** Full suite, solo under the board lock:
  **8668 passed, 1 skipped, 0 failed, EXIT=0** in 883.86s (14:43). **Count reconciles exactly against the
  bound the fix re-derived:** main 8628 + the card's **40** node IDs = 8668, and bound 8 now declares 40
  node IDs — the gate and the bound were derived independently and agree. Progression across the card:
  8649 (gate 1, +21) → 8667 (gate 2, +39) → 8668 (gate 5, +40). Not vacuous. → review cycle 3, the last.

### [Review 3/3] Score: 9.0 (8.5 → 9.0, Δ+0.5) — ZERO Critical, ZERO Important. Severity gate OPEN.

Report: `meta/review/20261021T085955Z-CARD-258-cycle3.yml` — 2 findings, both Minor, 10 system-contract
verdicts. **[Review sync]** 1 report → `meta/review/`. Full review (cycle 2 discovered a gating finding,
so the mode reset). **Step 8h: 10 rules checked, 10 ✓ holds, 0 ⚠, 0 ✗** — cycle 2's ADR-0039/R3 violation
is resolved, so all three ADR-0039 rules now hold after being violated in cycle 1 (R1, R2) and cycle 2
(R3). **Mutation check RAN: 7 mutants, 7 killed, 0 survived**, with restore verified byte-for-byte by
SHA-256 on all three files and `git diff --stat` unchanged at `+966/−48`.

**All five cycle-2 findings resolved, each re-derived rather than accepted.** F-011's deletion is complete
(`grep -c _docstring_constants` → 0 across all three files; the surviving sentence is the inverted one;
`_RESET_COUNTER_INNOCENT`'s comment likewise inverted to "No exemption is involved in either miss"), and
M2 proves **the deletion loosened nothing** — making the `strings` arm match nothing still reds exactly
`[dotted]`, `[getattr]`, `[globals]`, `[vars]`. F-012's MRO walk verified sound by M5 (walk matches
nothing → reds with "this guard cannot default to a pass"). F-013's control verified two-directional by
M3/M4. F-014 and F-015 confirmed by re-measurement, F-015 by re-running the mutant: the one-hook guard
reds while **both** byte-comparison tests stay green, exactly as bound 7 now declares.

### ⚑ [Family] THE FAMILY DID NOT REGENERATE — streak CLEARS at 1, no escalation

The reviewer counted and attributed mechanically rather than inferring, and **it says it looked hard for a
family finding and declined to manufacture one** — which is the answer I asked for in both directions.
Exemptions in the G-1 guard: **1**. Claims asserting a docstring carve-out: **0**. The two Minors raised
are **stale quoted numbers, not uncontrolled claims**, and the one in test code is **cycle-1 code the
cycle-2 fix never touched** — verified by `git show HEAD:… | grep -c "Four of these"` → 0 and
`_RESET_COUNTER_SHAPES` absent from HEAD. **Neither is in the family and neither is attributed to the
cycle-2 fix.** The route chosen for cycle 3 (delete the dead exemption rather than control it) is what
cleared this, and it is now on the record as having worked.

### [8h spot-check] 3/3 sampled holds reproduced — and my first probe was invalid, which I am recording

Run **inline** by the orchestrator rather than by three subagents: the three selected verdicts all cite a
named test or a repeatable scan, so re-derivation is objective command output rather than judgement, and
the cheaper route buys the same evidence. `[Inline fallback] 8h spot-check`.
- **ADR-0036/R3** — ran the named test it cites: `test_the_package_draws_a_round_mark_in_exactly_one_function`
  → **1 passed**. Reproduced.
- **ADR-0036/R4** — repeated the scan with **my own** independent AST sweep for U+25A0–U+25FF / U+2022 /
  U+2219 over every string constant under `src/`: hits at `src/nonogram/admin/pdf_generator.py:321` only —
  pre-existing, outside this diff, and already a named exemption in the enforcing guard. Reproduced.
- **ADR-0039/R3** — re-derived the two-directional control by mutation. **My first attempt was a no-op and
  I nearly recorded a false negative:** the declared counts sit on their own lines (`2,` at `:858`), so
  neither of my regexes matched and the file was rewritten unchanged — the test passed because nothing had
  been mutated, not because the control is weak. Redone precisely: **M4** (count `2` → `3` at `:858`) →
  **1 failed**; **M3** (delete the `shape_for_mode` exemption entry, lines 862–866) → **1 failed**. Both
  directions red. Reproduced. Restore verified byte-identical (`744372b3384d3d47` before and after).
  *Recorded because a botched probe that looks like a failed re-derivation would have cost this card a
  cycle it did not owe.*

**The two Minors, neither blocking:** **F-016** — `_RESET_COUNTER_SHAPES` holds **seven** entries while
`:949` says "Four of these five" and `:1588` says "Four of these six"; the substantive half reproduces and
coverage is unaffected because the parametrisation derives from the dict. **F-017** — bound 14's "(71
passed)" does not reproduce; it is **72 passed, 1 failed**, because the figure was taken before the fix
added its own control test (the file is 73 now). Both are prose-accuracy edits in exactly the class this
card's own discipline polices, which is why they are worth fixing at commit time rather than waiving.

### [Fix 3] Both cycle-3 Minors closed inline by the orchestrator (prose only, no mechanism touched)

Neither gates, but both are stale-number claims in exactly the class this card spent three cycles on, so
shipping them would be the family's own defect surviving in the record.
- **F-016 closed.** Verified the premise with my own AST read first — `_RESET_COUNTER_SHAPES` holds **7**
  entries while `:949` said "Four of these **five**" and `:1588` said "Four of these **six**", so neither
  denominator was ever right. Both denominators **dropped** rather than corrected to 7, because the
  parametrisation is derived from the dict and a hard-coded count would just go stale again — the file's
  own idiom. `tests/test_admin_binding.py` re-run after the edit: **73 passed**, unchanged.
- **F-017 closed, and I corrected my own copy of the same error.** Measured the real figure myself:
  `pytest tests/test_admin_binding.py -p tests.helpers.undefined_table_report` → **1 failed, 72 passed**,
  the single red being `test_the_diagnostic_is_registered_in_this_very_run`, exactly as the residual
  describes. Bound 14's "(71 passed)" was taken before the fix added its own control test. **The same
  stale 71 appeared in my own `[Fix 2]` note above, because I repeated the fix agent's report figure
  without re-deriving it** — both are now corrected, and mine says so.
  *And a third instance, caught while writing this bullet:* my first draft closed with
  "`grep -c '71 passed'` → 0", which was **false the moment it was written**, because the sentence above
  it quotes the old figure while explaining it. A count over a file that includes the prose discussing the
  count is not a check. The honest statement is the one that names where the string survives: the stale
  figure is gone from **bound 14** and from the **[Fix 2]** note, and the only remaining occurrences in
  this card are the two inside this bullet, quoting it as the error it was.

### [AC/EC check] All criteria/constraints ✓ (evidence)

**5/5 acceptance criteria and 5/5 guardrails `demonstrated`. 0 EC items** — the card has no
`## Engineering constraints` section, which the gate confirmed by enumerating the card's headings rather
than assuming. Every verdict is backed by a command in the gate's evidence appendix.

```
AC-1 ✓ demonstrated — 6 tests green, plus a freshly PROVOKED instance printing all four group labels with
       concrete values (dbname/backend_pid/libpq_status/txn_status, engine id+pool+reset_engine_calls=1,
       pid/thread/alive_threads, current_database/schema/search_path, verdict vs-app-engine=MATCH
       vs-capture=MATCH) and still ending "1 failed" with the original ProgrammingError traceback above it
AC-2 ✓ demonstrated — the hook actually disabled, TWO ways: (a) `-p no:undefined-table-report` reds the
       registration test; (b) the probe fixture mutated to with_hook=False → 5 failed, 1 passed
AC-3 ✓ demonstrated — named test green, plus an independent real-suite comparison: 72 passed both ways,
       normalised sha256 `3a128c7c…c6246f` identical, 72 real PASSED lines (non-vacuous)
AC-4 ✓ demonstrated — named test green; suite-wide half re-derived from pytest 9.1.1's own source
       (`check_interactive_exception` returns False for no-raise, wasxfail, Skipped/SkipTest/BdbQuit, and
       those are its only two call sites), so the hook cannot fire on a pass, skip or xfail
AC-5 ✓ demonstrated — capture failure NAMED not swallowed (`group-4 … FAILED`, test's own failure intact),
       and KeyboardInterrupt/SystemExit pass through both guards
G-1  ✓ demonstrated — guard + all 7 reach controls green; independent AST sweep of 60 files: named calls
       to `reset_count` = []; `session.py` additive (+69/−1, the deletion being a `global` line extended)
G-2  ✓ demonstrated — refusal fires BEFORE anything opens (`NOT OPENED` present, `FAILED` absent); and
       `_refuse_unless_test_database` + `_refusal_reason` AST-extracted from merge-base and worktree are
       byte-identical (`e2f96ed5…`/2031 B and `a9601ea1…`/1872 B) — neither widened nor bypassed;
       `nonogram_poc` appears in the entire card diff on exactly one line, a comment saying never
G-3  ✓ demonstrated — `pyproject.toml` diff EMPTY against the merge-base; every added import is stdlib or
       an already-declared package (`psycopg2`, `sqlalchemy`, both in the pre-existing `db` extra)
G-4  ✓ demonstrated — one-hook guard + its assigned-hook control green; and enumerated the way pluggy
       does, independently of the card's helper: pluggy-visible `pytest_*` callables = ['pytest_exception_interact']
G-5  ✓ demonstrated MECHANICALLY, as demanded — the five-parametrisation class AST-extracted from `main`
       and from the worktree: 4244 bytes and sha256 `b16dd8b0…fdd0` on BOTH, identical=True; the file's
       diff is `1411 insertions, 0 deletions` with no hunk inside lines 290–394; and `git diff` contains
       no `-…def test_` line anywhere, so no test was retired
```

**Three caveats the gate recorded rather than smoothed over, which is why I trust the rest of it:**
- **It caught its own vacuous run.** Its first AC-3/AC-4 real-suite comparison had an unquoted
  `--deselect` that collapsed into one argument, so **both runs collected 0 items and reported identical
  hashes** — a false pass. It noticed via output length, re-ran correctly, and cites only the non-vacuous
  run (72 real PASSED lines). *That is the second vacuous-probe near-miss in this card's verification
  today; mine was the ADR-0039/R3 no-op mutation.*
- **AC-2's mutation control left one of AC-1's six tests green**, for a stated structural reason (that test
  compares two now-identically-hookless runs and is trivially true in the mutant). Reported as observed,
  with the registration half (a) named as what covers the gap — not glossed.
- **Every check is bounded and says so.** The skip-profile measurement covers the 72-test selection, not
  8668; the suite-wide claim rests on pytest's own gate plus build gate 5's `1 skipped`.

### [Docs step] SKIPPED deliberately, and the reason is an open owner decision — not an omission

`docs.enabled` defaults on, and the changed directories are `src/nonogram/db/`, `tests/` and
`tests/helpers/`. I am **not** creating per-directory READMEs here, for two reasons that are specific
rather than general: (1) **no directory under `src/` has one**, and whether that becomes the convention is
a **standing owner decision already in `meta/kanban/backlog.md`** ("Either make 'no per-directory READMEs'
the convention and drop the step, or create them once and rewrite `tests/README.md`") — creating them from
this card would preempt that decision across the repo; (2) `tests/README.md` is **being modified by
CARD-260 in the same wave**, so editing it from here would manufacture a merge conflict between two
active cards. Recorded so the skip is a decision with a route, not a gate that silently did nothing.

### [Commit] `2488b779` — review cycle complete, card awaits `done`

`ops(CARD-258): the diagnostic's guards claim only what they catch` — 3 files, **+966 / −48**, staged with
**explicit pathspecs** (`src/nonogram/db/session.py`, `tests/helpers/undefined_table_report.py`,
`tests/test_admin_binding.py`) so none of this repo's standing untracked set could be swept in. The three
review YAMLs correctly stayed **untracked**: `meta/` must never enter the branch it reviewed.
Status stays `review` until `done` merges it, per the protocol.

**A hook fired on commit and is passed on rather than swallowed:** *"forge: source files changed —
how-it-works docs may be stale. → /forge:explain [aspect]"*. The only `src/` change on this card is an
**additive read-only counter with no callers under `src/`** (G-1, independently verified), so no
behaviour a how-it-works page describes has moved — but the notice is the owner's call, not mine to
dismiss, so it is recorded here and surfaced in the report.

### [Done] merged `4584caf4` into `main` — 2026-10-21

**Merge gate (the once-per-card full run, on the REBASED tree): PASSED** — `8668 passed, 1 skipped,
0 failed, EXIT=0` in 1027.52s at `c4ebba6c`. Rebase onto `main` was clean: main had moved three commits,
all `meta/kanban/` bookkeeping with **zero** overlap with this card's files.

**I nearly carried build gate 5 instead of running this, and was wrong to consider it.** The rebased
code tree hashes **identically** to the gated one (`da96dd26…` before and after), which is exactly the
"byte-identical to the gated commit" carry this board used on CARD-248. But the suite **reads `meta/`**:
`tests/full_suite_lock.py` defines `OVERRIDE_PROSE = ("meta/kanban/cards/", "meta/review/")`, and
`test_nothing_in_the_tree_sets_either_of_the_guards_env_switches` scans the **whole tracked tree** for
in-tree setters of the guard's env switches with those two prefixes exempted under a shape clause — the
very test that caught CARD-260's fix agent mid-work today. The rebase replaced the worktree's tracked
`meta/` with main's, so **the tree the suite sees did change and code identity was not sufficient.**
The gate was run. It passed. *Recorded because the shortcut was plausible, precedented, and wrong.*

**Merge commit type `fix`**, from `Category: ops` (forge:commit's mapping), `--no-ff`: 4 files,
**+2230 / −2**.

- **[Deferral scan]** 0 mechanical hits — **and one real deferral captured anyway.** The obligation lives
  in the card's **declared bound 9**, not in a code comment, so the grep could not see it: 
  `_global_names_assigned_by` collects only `ast.Assign`, so `_reset_count` (declared `global`, assigned
  `+=`) is dropped by the intersection and CARD-252's globals equality **passes by silence, not by
  cover** — while that function's docstring claims the opposite bias. Captured to
  `meta/kanban/backlog.md` under a new `## Deferred during implementation` heading with the honest repair
  (collect `AugAssign`/`AnnAssign`, restate the equality as a subset relation) and the site. Under-capture
  is the failure mode that scan exists to fix, so a declared-but-ungrepped deferral is still a deferral.
- **[Sync 5b]** Review reports: 3 → `meta/review/`, each verified **byte-identical** in the main repo
  before the worktree was destroyed (cycle 1 7.5 / 10 findings, cycle 2 8.5 / 8, cycle 3 9.0 / 2).
  Card notes: **no-op, deliberately.** The worktree copy (315 lines) was the *pre-fix* version — its
  only lines absent from the main copy (1099 lines) are **superseded field values** (`Status:
  in_progress`, `Review score: —`, the old 48-assertion-node counts). The protocol copies notes missing
  from main; appending stale values would have corrupted the card, so the one-way sync correctly moved
  nothing.
- **[Sync 5c]** Visual baselines: skipped — no `.forge-screens/`, not a UI card.
- **[Worktree]** Removed with `--force` only after confirming the discarded set was **exactly** the three
  review YAMLs (all three `cmp`-identical in the main repo) plus `__pycache__`/`.pytest_cache`. Branch
  `card/258-the-ops-red-says-what-it-talked-to` deleted by safe `-d` (fully merged). `PycharmProjects`
  is tidy: only the repo and CARD-260's live worktree remain.
- **[Changelog]** `docs(changelog): CARD-258` → `fc2e02bb`, under a new `## 2026-10-21` heading.
- **[Trace write-back]** Skipped: this card has **no `## Architecture context`** section, so there is no
  FR/NFR link entry to append evidence to. Stated rather than silent — it is the untraced-enabler path,
  not a missed step.
- **[Dependents]** None: no card's `Depends on` names CARD-258, so no dependent worktree needed rebasing.
- **[Hooks, passed on not swallowed]** `/commit` printed *"source files changed — how-it-works docs may be
  stale → /forge:explain"*, and the merge printed *"pulled external changes — drift detection unavailable
  (python3 or .claude/hooks/forge/post-pull.py missing; run /forge:init hooks)"*. The first is likely
  moot (the only `src/` change is an additive counter with no callers); the second is a missing hook
  install, unrelated to this card. Both are the owner's call.
