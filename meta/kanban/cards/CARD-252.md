# CARD-252: The test session's schema rebuild disposes the app's engine, so a gate's red means the code

**Status:** in_progress
**Priority:** P1
**Category:** ops
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/252-dispose-the-global-engine
**Worktree:** ../PythonProject4-card-252
**Source:** backlog `@ops` item "The app's module-global SQLAlchemy engine survives the test session's `DROP SCHEMA`…", first observed 2026-10-18 on CARD-248's gate; carded on the owner's instruction 2026-10-19 after it cost a fourth gate run.
**Idea:** —
**Wave:** 48 (started mid-wave on owner instruction)
**Depends on:** —
**Touches:** tests/conftest.py, tests/test_db_engine_lifecycle.py, src/nonogram/db/session.py
**Review score:** —
**Started:** 2026-10-19T17:32:53Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this is P1 when it changes no product behaviour

It does not break the panel. It breaks **the board's ability to believe its own gates**, which is the
one instrument every card depends on.

Measured cost, four consecutive waves, each a full ~16-minute suite re-run plus a fresh diagnosis:

| wave | run | how it presented |
|---|---|---|
| 45 | CARD-248 build gate | `EXIT=1`, 1 failed, then green on the same commit |
| 46 | the wave smoke test, first run | 5 failed, `FATAL: database … does not exist` |
| 47 | CARD-251 build gate | 5 failed, `relation "puzzles" does not exist` |
| 48 | CARD-247 build gate | 6 failed, incl. `uuid.UUID(hex=<float>)` → `AttributeError: 'float' object has no attribute 'replace'` |

**It also costs trust, which is worse than the minutes.** On wave 47 the orchestrator attributed a red
gate to its own scheduling, committed that attribution, and had to withdraw it after measuring
properly. A defect whose signature changes shape between runs makes every red gate a research project,
and makes a wrong diagnosis cheap to reach.

## The mechanism, read from the code

- `src/nonogram/db/session.py:10-12` keeps **module-global** `engine`, `SessionLocal` and `_engine_url`.
  The builder at `:183` rebuilds only when `engine is None or database_url != _engine_url` — so a
  process that has already built an engine for this URL keeps it, pool and all.
- `tests/conftest.py:486-508` empties and rebuilds the schema on **its own** engine
  (`DROP SCHEMA public CASCADE` → `CREATE SCHEMA public` → `alembic upgrade head`) and disposes **that**
  engine in its `finally`. The app's global engine is never touched.
- So pooled connections created before the DROP are handed out after it. Their cached per-table
  metadata — column type OIDs — belongs to tables that no longer exist, which is how a `UUID` column
  comes back as the float `inf` and `uuid.UUID(hex=inf)` calls `.replace` on it. The `puzzles` table has
  **no float column at all**, so misalignment *within* the table cannot explain the observed value.

## What to implement

**The fix itself is small and is not the work.** After the rebuild and migration, and before the
fixture yields, dispose the app's global engine and reset its cache key, so no connection predating the
new schema can be handed out:

```python
from nonogram.db import session as app_session
if app_session.engine is not None:
    app_session.engine.dispose()
app_session.engine = None
app_session.SessionLocal = None
app_session._engine_url = None
```

Reaching into another module's globals is ugly. **Prefer giving `session.py` a named function to do it**
(`reset_engine()` or similar, with a docstring saying who calls it and why) so the test tree depends on
a published seam rather than on three private names — and so a later reader of `session.py` sees that
something resets it. That is the one design decision in this card; record it as a `STRUCTURE:` note
either way.

## The real work: a control that can fail

**This is the whole card, and it is genuinely hard, because the defect is non-deterministic.** A test
that asserts "the dispose happened" pins the *mechanism* and proves nothing about the *hazard* — and
shipping that while calling it a fix would be a control that cannot fail, inside the card whose subject
is a defect that makes evidence unreliable. Do not do that quietly.

Attempt them in this order:

1. **Deterministic reproduction (what the card wants).** Force the global engine to exist and to have
   executed against `puzzles` so its connection caches that table's OIDs; rebuild the schema underneath
   it; query again through the global engine. **Shown RED before the fix** — with the failure being one
   of the recorded signatures, not merely "an error" — and green after. The one real risk is that the
   stale-metadata path needs a condition the test cannot force (connection returned to the pool and
   handed back out, a statement past psycopg's auto-prepare threshold); if so, say which condition and
   move to 2.
2. **If 1 cannot be made deterministic, say so in the test's own docstring and pin what you can:** that
   the fixture leaves no engine predating the rebuild (so the hazard's *precondition* is gone), with a
   mutant removing the dispose that turns the assertion red. Then **state plainly, in the card and in
   the docstring, that this pins the precondition and not the absence of the race** — and say what
   would be needed to pin the race itself.

**Either way the claim must match the mechanism.** This card is allowed to ship (2); it is not allowed
to ship (2) described as (1).

**And one way of "fixing" this that must not happen.** The hazard only bites `db_required` tests. A
change that makes those tests skip — by narrowing the fixture, by failing to set `DATABASE_URL`, by
any route — removes the red without removing the defect, and this board's DB tests already *skip
green* when the database is absent, so the suite would not complain. The skip profile is therefore
part of the deliverable: this machine's run has **exactly one** skip (the platform `setrlimit` one),
and it must still have exactly one afterwards (AC-4).

## Acceptance criteria

- **AC-1** (the fix, happy): *Given* a session fixture that has rebuilt the schema, *then* the app's
  global engine is not one built before the rebuild — it is disposed and its cache key cleared, so the
  next session request builds a new one against the new schema.
  (test: `TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema`)
- **AC-2** (the control — **the failing-first one**): *Given* the fix removed, *then* AC-1's test fails.
  The mutant and its output are recorded on the card. A fix whose removal fails nothing is not pinned.
  (test: the same, under a named mutant)
- **AC-3** (the hazard, **if and only if it can be made deterministic**): *Given* a global engine that
  has queried `puzzles`, *when* the schema is rebuilt underneath it and the same query runs again,
  *then* without the fix the recorded signature appears and with the fix the query succeeds.
  **If this cannot be made deterministic, AC-3 is withdrawn in writing** — the card records which
  condition could not be forced, and AC-1/AC-2 carry the card.
  (test: `TestEngineLifecycle_AStaleEngineReadsTheOldSchema`)
- **AC-4** (guard, nothing else changes): *Given* the change, *then* the suite's skip profile is
  unchanged — the same 1 skip on this machine — and no test that passed before now skips. A fix that
  quietly turns DB tests into skips would remove the symptom by removing the coverage.
  (test: `TestEngineLifecycle_TheSkipProfileIsUnchanged`, asserting the count rather than reading it)
- **AC-5** (guard, the seam is published if one is added): *Given* a `reset_engine()`-style function on
  `session.py`, *then* it is documented, named in `conftest.py`'s call site, and no test reaches into
  `session.py`'s private globals directly. If the decision goes the other way, this AC is withdrawn in
  writing with the reason.
  (test: `TestEngineLifecycle_TheResetIsAPublishedSeam`)

## Guardrails

- G-1: **No production behaviour changes.** The panel's own engine lifecycle outside tests is untouched;
  `get_session`'s contract is unchanged.
- G-2: **No test is made to skip** to make a failure go away (AC-4).
- G-3: The fix runs **after** `alembic upgrade head` and **before** the fixture yields — disposing
  before the migration would leave a fresh engine pointing at a half-built schema.
- G-4: `nonogram_poc` is never created, dropped, connected to or truncated, and
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-5: No new runtime dependency (ADR-0006/R1).
- G-6: No test retired without a named survivor.

## System contract

_Assembled 2026-10-19 by `system_rules.py --card CARD-252 --root meta/architecture` (29 rules returned, `card_scope: touches`). A projection — fix the source artifact, never this list._

**Curated to 8 by rule; 21 dropped**, under [`meta/kanban/curation.md`](../curation.md): keep every in-scope rule whose enforcement does not reach this card's new code, drop the rest. The dropped all carry a `kind: test` check the suite executes every gate. Kept are the rules **nothing executes**, plus `ADR-0039`, whose checks are tests but which declares they do not reach code written later — **which is exactly this card's situation**, since its subject is a test-tree guard.

- **ADR-0022/R1** — _nothing executes this_
  Grid extent crosses module boundaries as a (width, height) pair. No public function signature,
  request field, or export field reduces a grid's extent to a single scalar \"size\", and no
  source mode constructs a grid from one integer.
- **ADR-0038/R6** — _nothing executes this_
  Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution
  grid to the browser. A public or reader-facing player must not send the solution before the
  puzzle is solved, and any public phase reopens this ADR (CON-021).
- **ADR-0038/R7** — _nothing executes this_
  Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in
  pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — _nothing executes this_
  Browser tests run locally, against Chromium installed by `playwright install chromium`. When
  Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible
  in the run summary. They never pass silently. Once a CI pipeline exists, it installs Chromium
  (playwright install chromium) before running them; until then there is no CI, and that is a
  known gap, not a met clause.
- **ADR-0039/R1** — _declares its checks do not reach new code_
  A set a guard consults needs a completeness test written before the set, and any claim the
  guard makes about what it catches needs a control that can fail: caught WITH the set member
  present, missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and
  must be narrowed to what is measured or deleted.
- **ADR-0039/R2** — _declares its checks do not reach new code_
  A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where
  no such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE,
  never a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3.
- **ADR-0039/R3** — _declares its checks do not reach new code_
  An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT
  absorb — caught with the exemption removed, missed with it in place — is held to an equality
  against the sites that exist today, and records whatever it still cannot see as a measured
  bound with its own failing control.
- **CON-021** — _nothing executes this_
  Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served
  behind the door that guards every other admin page (CON-015, CON-016). No other surface — the
  CLI, the web UI, or any public or hosted page — offers an interactive or playable puzzle. Play
  state is never persisted on the server: no progress, marks, error count, score or solve time
  is written to a database, file or server, no network request is made per mark, and no user
  account exists for playing (CON-017). The one place play state may be kept is the browser's
  own localStorage, per puzzle, so that a puzzle reopened in that browser resumes where it was;
  it never leaves that browser. The admin player ships the puzzle's solution grid to the browser
  to compute the error count and the solved state; this is permitted for the admin panel only,
  and a public or reader-facing player must not send a puzzle's solution to the browser before
  the puzzle is solved.

## Worktree notes

- **[Do not take timing measurements]** Sibling cards may be running; a contended number is not a
  measurement.
- **[The suite's own evidence is the acceptance test]** The honest end state is that the next four
  waves' gates stop producing unattributable reds. That cannot be asserted in a test, so it is not an
  AC — but it is what the card is for, and the retrospective should check it.
- **[Prior art on the board for a test that must fail first]** CARD-250's AC-6 required the stale
  thumbnail be demonstrated failing before the fix, and the evidence was a transcript showing the two
  SVGs genuinely differing. Same standard here.

### Implementation, 2026-10-19 (branch `card/252-dispose-the-global-engine`)

**STRUCTURE: the reset is a published seam.** `src/nonogram/db/session.py` gains
`reset_engine()` — public, documented, naming its one caller and the reason the order
matters. The card's alternative (three assignments to `engine` / `SessionLocal` /
`_engine_url` from `conftest.py`) was rejected: it is the same four lines but leaves
`session.py` silent about the fact that anything retires its engine, and silent is how the
module got here. AC-5 is therefore **kept**, not withdrawn.

**STRUCTURE: the destructive half of the fixture is now a named function.**
`tests/conftest.py` grows `_rebuild_public_schema(engine, database_url)` — DROP/CREATE,
`alembic upgrade head`, read the truncate list, then `reset_engine()` — and
`_test_database_tables` calls it. Not cosmetic: it is what makes AC-2's mutant land in the
code the fixture actually runs instead of in a copy of it. Without it, a test could only
inspect the global engine *after* the session fixture had already run, and whether an engine
existed at that moment is a property of test ordering — so the control would have passed
with the fix removed on most orderings. See the "control that cannot fail" risk this card
is about.

#### AC status

| AC | verdict | test |
|---|---|---|
| AC-1 | pass | `TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema::test_no_engine_pool_or_backend_predating_the_rebuild_survives_it` |
| AC-2 | pass (mutant M1, red) | the same test, under M1 below |
| AC-3 | **WITHDRAWN** (see below) | survivor: `TestEngineLifecycle_WhyTheHazardCannotBeForced` (2 tests) |
| AC-4 | pass | `TestEngineLifecycle_TheSkipProfileIsUnchanged` (2 tests) — with one part moved to the gate, stated below |
| AC-5 | pass | `TestEngineLifecycle_TheResetIsAPublishedSeam` (5 tests) |

`tests/test_db_engine_lifecycle.py` — 10 tests, `10 passed` with
`DATABASE_URL` pointed at this worktree's derived database
(`nonogram_pythonproject4_card_252_5ddd9defbd0a_test`). Touched-adjacent selection
(`test_db_engine_lifecycle`, `test_card_156_db_fixture`, `test_db_isolation`,
`test_db_url_driver`, `test_db_connect_timeout`, `test_db_e2e_smoke`,
`test_card_109_database_guard`, `test_cli`): **256 passed, 0 skipped, 0 failed**.
Plus `test_puzzle_edit_routes` + the new module: **87 passed**.

#### AC-3 is withdrawn, and this is the condition that could not be forced

**A cached, schema-dependent, per-connection statement does not exist on this code path.**

Attempted, directly and deliberately, before any fix was written: build the app's global
engine against this worktree's test database; insert into and read `puzzles` twelve times
through `SessionLocal` (ORM and Core, so both the pool and SQLAlchemy's compiled-statement
cache are warm); close each session so the connection goes back into the pool; then
`DROP SCHEMA public CASCADE` / `CREATE SCHEMA public` / `alembic upgrade head` on a second
engine; then query again through the surviving pooled connection, four query shapes
(`ORM .all()`, `SELECT id`, `SELECT *`, `ORM Puzzle.id`) × six attempts each.

Result: **24/24 succeeded with correct values. No error of any kind.** psycopg2 sends every
statement for parse on every execution and typecasts each result from the OIDs in *that
result's own* `RowDescription`, so a connection that outlives a `DROP SCHEMA` carries
nothing about the old tables to be wrong about.

Three further measurements, which are what the two survivor tests pin:

- `pg_prepared_statements` holds **0** rows after 40 identical parameterised executions on
  one pooled connection. psycopg2 2.9.12 has no auto-prepare threshold to pass — the
  attribute does not exist, so the card's suggested condition ("a statement past psycopg's
  auto-prepare threshold") is not a high knob, it is **no knob**. That condition is
  reachable on psycopg 3 and this project names psycopg2 (`session.POSTGRES_DRIVER`,
  CARD-148).
- Even a hand-written `PREPARE p252 AS SELECT id FROM puzzles` **survives** the rebuild:
  PostgreSQL re-analyses the stored parse tree, so the recreated table is found by name and
  `EXECUTE` returns the new rows. So forcing the prepared statement would not have produced
  the signature either.
- `cursor.description` for `puzzles.id` is `type_code=2950` (`uuid`) on every execution,
  freshly, so the recorded `uuid.UUID(hex=<float>)` signature cannot be reached by handing
  a surviving connection a stale OID through this driver.

`TestEngineLifecycle_WhyTheHazardCannotBeForced` exists so the withdrawal is not a sentence
in a card nobody re-reads: it goes **red** if `POSTGRES_DRIVER` changes, if psycopg2 gains a
`prepare_threshold`, or if a server-side prepared statement ever appears — which is the day
AC-3 becomes reachable again (G-6: named survivor for a withdrawn AC).

#### What is pinned instead, and what it is NOT

AC-1's test pins the hazard's **precondition**: after `_rebuild_public_schema` returns, no
engine object, no connection pool and no PostgreSQL backend process from before the rebuild
survives it. The precondition is **forced**, not hoped for — the test builds the global
engine itself, queries `puzzles` through it, records `pg_backend_pid()`, asserts the pool
holds that connection and that the backend is live *before* the rebuild, and only then
drives the rebuild. Both forcing assertions carry their own failure messages saying the test
would otherwise be vacuous.

**It does not demonstrate that a surviving connection would have corrupted a query.** It
cannot, for the reason above. This is case (2) of the card's ladder and it is labelled as
case (2) in the module docstring, in the test class docstring and here. To pin the race
itself one would need psycopg 3 with `prepare_threshold` reached, a server-side cursor held
open across the DROP, or a connection left idle-in-transaction so the DROP takes the
`lock_timeout` path — none of which exist on this code path today, and manufacturing one
would test the manufactured thing rather than the suite.

**One claim deliberately not made:** the test pins the *outcome* (no survivor), not the
*position* of the call (G-3). Measured: moving `reset_engine()` to before the migration does
**not** turn it red, because `reset_engine()` clears the globals without building anything,
so there is no engine to point at a half-built schema. G-3's hazard is real for the card's
sketch-with-an-eager-rebuild and is handled by the ordering plus the docstring that explains
it, not by an assertion. Widening the test to pin line order would have been a claim about
something that cannot go wrong in this shape.

**AC-4, split honestly.** Two things are asserted as counts: this module keeps exactly
`EXPECTED_DB_REQUIRED_TESTS = 2` tests that need the live database (so the coverage pinning
the fix cannot quietly go to zero), and — given a PostgreSQL that answers, probed by a bare
`psycopg2.connect` rather than by `conftest`'s own cached verdict — the `db_required` gate
yields exactly **zero** skip reasons for this worktree's derived database. The *suite's*
skip profile (exactly 1 on this machine: the platform `setrlimit` skip in
`tests/test_book_pdf_memory.py`) **cannot** be asserted from inside the run without
depending on collection order, and pytest knows the number only after the last test. It is a
gate observation; the docstring says so rather than implying the test covers it. The new
module contributes **0** skips on a machine with Postgres, and adds no new skip path other
than "Postgres does not answer at all", which is already the board's condition for every DB
test.

#### Mutants (all restored from byte-identical backups; `diff` clean after each)

| # | mutant | result |
|---|---|---|
| **M1** | `app_session.reset_engine()` deleted from `conftest._rebuild_public_schema` (the fix removed — **AC-2**) | **RED.** `AssertionError: the app's global engine survived the schema rebuild…` plus `test_conftest_names_the_seam_at_its_call_site`. `2 failed, 8 passed` |
| **M2** | `_engine_url = None` deleted from `reset_engine()` | **RED**, but only on `test_it_resets_exactly_the_globals_the_builder_creates` (`resets ['SessionLocal','engine'] but _init_engine builds ['SessionLocal','_engine_url','engine']`). AC-1 stayed green — honest finding: that line is defensive, not load-bearing, because `_init_engine` rebuilds on `engine is None` alone. The structural guard is the only thing that catches it, which is the reason it is derived from `session.py`'s own AST rather than hand-written. `1 failed, 9 passed` |
| **M3** | `app_session.engine = None` added to `conftest` ahead of the seam (the card's rejected sketch, done wrong) | **RED** twice: the AC-5 guard (`new: [('conftest.py','engine')]`) and AC-1 (`the pre-rebuild pool still holds a connection (… Connections in pool: 1): it was not disposed`). Worth noting — AC-1 pins the **dispose**, not just the cleared global. `2 failed, 8 passed` |
| **M4** | `@pytest.mark.db_required` removed from the prepared-statement test (AC-4's coverage-removal shape) | **RED.** `1 test(s) here carry db_required, expected 2`. `1 failed, 9 passed` |
| **M5** | env-only, no file touched: `TEST_DATABASE_URL=…/nonogram_notatest` (a gate that would skip) | **RED.** `PostgreSQL answers, yet the db_required gate would skip this worktree's test database for 2 reason(s)` |

G-4 held throughout: every DROP/CREATE/migration in this card ran against
`nonogram_pythonproject4_card_252_5ddd9defbd0a_test`, derived for this worktree by
`tests/db_name.py` and created by this card's own run. `nonogram_poc` was never named,
connected to or touched, and `_refuse_unless_test_database` was neither widened nor bypassed
(M5's refused URL was rejected on its text, with no connection to it).
G-1: nothing in `src/` calls `reset_engine()`; `get_session`, `get_db` and `session_scope`
are byte-identical. G-5: no new dependency.

### [Scope] clean · [Orchestrator] two corrections, one of them to the card itself

**3 files, all inside `Touches`, no drift, no `SCOPE+`.** `reset_engine()` is the **last** statement
before `_rebuild_public_schema` returns (G-3), verified in the tree.

**⚑ AC-3 is WITHDRAWN, and the reason reaches past this card: the mechanism this board has recorded
since wave 45 is refuted.** The backlog item said the hazard came from "a connection whose statement had
crossed psycopg's auto-prepare threshold". Measured, and re-verified independently by the orchestrator:
**psycopg2 2.9.12 has no `prepare_threshold` on its cursor or its connection at all.** Three supporting
measurements point the same way — `pg_prepared_statements` is **0** after 40 identical parameterised
executions on one pooled connection; a hand-written `PREPARE` **survives** the rebuild, because
PostgreSQL re-analyses the stored parse tree; and `cursor.description` reports `type_code=2950` freshly
on every execution. 24 of 24 deliberate reproduction attempts succeeded with correct values.

**So the symptom is real — four occurrences — and the causal chain is now unknown.** This card removes
a *plausible* cause and says so: it pins that **no engine, pool or backend process predating the
rebuild survives it**, with the precondition **forced** rather than assumed, and it explicitly does not
claim a survivor would have corrupted a query. **It ships as case (2) and is labelled case (2)** in the
module docstring, the class docstring and the card — which is exactly what the card demanded and the
thing it would have been easiest to fudge. Backlog corrected to match.

**⚑ The second correction is to my own card text.** CARD-252's **G-3** said disposing before the
migration "would leave a fresh engine pointing at a half-built schema". The agent measured it: moving
`reset_engine()` earlier does **not** turn the test red, because it clears the globals without building
anything, so there is no engine to point anywhere. **G-3's hazard is real only for the sketch I wrote
in the card, not for the shape that was built** — and the agent declined to widen the test to cover a
failure that cannot occur, which is the correct call and the opposite of the easy one.

**One honest residue the agent surfaced rather than buried (M2):** `_engine_url = None` is **not
load-bearing** — AC-1 stays green without it, because `_init_engine` rebuilds on `engine is None`
alone. The line was kept (clearing the cache key alongside the engine is the coherent thing) and its
only control is the AST-derived structural guard. Flagged for review to judge whether that is enough.

**AC-4 was split honestly rather than asserted whole.** A test inside the run cannot count the run's own
skips without depending on collection order. What is asserted: this module keeps exactly two DB-mode
tests, and — probed by a bare `psycopg2.connect` rather than conftest's cached verdict, an independent
second implementation — the `db_required` gate yields **zero** skip reasons for this worktree's
database. The suite-level skip profile stays a **gate** observation, and is stated as such.

- **[Build gate 1 — PASSED]** `fc5508e`, **solo** (second in wave 48's serialized chain): 8504
  passed, 1 skipped, 14:38, EXIT=0. First full suite this card has ever had.
- **[The hazard showed up next door, on a tree without this fix]** CARD-253's gate ran third in the
  same chain, equally solo, and failed 5 tests in `tests/test_admin_binding.py` with
  `psycopg2.errors.UndefinedTable: relation "puzzles" does not exist` — this function's docstring's
  own signature ("connections opened *before* the `DROP SCHEMA` are handed back out *after* it …
  failures that reproduced on no second run"). CARD-253 is based on `b2b2491` and therefore does
  **not** carry `reset_engine()`. That is a coincidence of timing, not evidence: it is one
  observation, this card's gate is one observation, and neither is a controlled comparison. It is
  recorded because it is the reason this card merges **before** CARD-253 re-gates, and because the
  reviewer should know the hazard is live on this board right now rather than historical.
