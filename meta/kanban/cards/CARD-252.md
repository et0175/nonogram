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

### [Review 1/3] Score 7.0 — FAILED on the severity gate (2 open Important)

Report: `meta/review/20261019T202638Z-CARD-252-cycle1.yml` (copied to main; `yaml.safe_load` ok).
Every one of the six findings is a **claim-versus-mechanism correction, not a defect** — the fix
itself was judged correct, AC-1 is a genuine failing-first control, and AC-3's withdrawal was found
better pinned than most ACs on this board.

- **F-001 (important, `session.py:219`)** — the docstring's "Without it …" paragraph attributes four
  waves of irreproducible gate failures to the mechanism AC-3 was withdrawn for. The card's own
  measurement went further than *undemonstrated*: 24/24 post-DROP queries correct,
  `pg_prepared_statements` 0, `type_code=2950` every time — the recorded signature measured
  **unreachable on psycopg2**. The narrowed wording already exists in the test module and in
  `conftest.py`; `session.py` is the one artifact of the three that still reads as established, and
  it is the file a maintainer of the production module opens.
- **F-002 (important, `test_db_engine_lifecycle.py:157`)** — AC-5's private-globals guard
  over-claims, with **three surviving mutants**: a tenth hand-set site inside an already-exempt
  (file, name) **pair** (the exemption is an equality over pairs, so nine sites collapse to six —
  the comment claiming a tenth site fails the guard is false), monkeypatch's **string-target**
  spelling, and `import … as X` + `X.engine = None`, which the completeness test's own docstring
  promises to deny and does not, because it enumerates only `ast.ImportFrom`.
- **F-003/F-004/F-005 (minor)** — the `db_required` count measures the *run's selection* rather than
  the module (so selecting the test alone reds with "expected 2": a red that means nothing, on the
  card whose subject is that a red must mean the code); both ordering docstrings give the
  unreachable hazard as the *reason* for the ordering, which is right as behaviour and wrong as
  rationale; AC-1's three-part claim has two independent pins, because the only realistic
  backend-alive mutant dies on the preceding pool assertion.
- **What the reviewer certified, so a later cycle does not churn it**: the *other* derived set
  (`_global_names_assigned_by`) is sound — it raises on a missing function, biases unanalysable
  shapes to red, and a fourth global added to `_init_engine` killed the test with the promised
  message. That is the edge control the claim was missing. `_engine_url = None` is defensible as the
  documented cache key. G-1, G-2, G-3 (as behaviour), G-4 (verified by diff), G-5, G-6 all hold.
- **Not checkable and recorded as such**: AC-4's suite-wide half (needs the full suite, which a
  review may not run), the backend third of AC-1, and whether the four waves' failures are this
  mechanism at all. The reviewer also recorded, and declined to use as evidence, that CARD-253's
  intermittent red carries the same signature — and named the alternative that fits the same
  evidence shape: two runs sharing one test database, which is the hazard CARD-244 fixed and whose
  comment this diff removes.

### Review cycle 1, findings closed, 2026-10-19 (`meta/review/20261019T202638Z-CARD-252-cycle1.yml`)

Score 7.0 / `min_score: 8`, two open Importants. Every finding was a claim-versus-mechanism
correction, so nothing about the fix changed: `src/nonogram/db/session.py` and
`tests/conftest.py` are **docstring-only** edits this cycle (verified by comparing both files'
ASTs with every docstring stripped — executable code identical, so G-1 and the G-3 ordering are
untouched).

| finding | verdict | where | the mutant that proves it |
|---|---|---|---|
| **F-001** (Important) | closed | `session.py:208-262` (`reset_engine`'s docstring) | n/a — a narrowing; nothing is claimed that was not already pinned |
| **F-002** (Important) | closed | `tests/test_db_engine_lifecycle.py` — guard rewritten at `:133-300`, four controls at `:723-815` | R1/R2/R3 all now **RED**; G1–G4 (below) kill the four new controls one at a time |
| **F-003** | closed | `:105-150` (`_test_functions_in`) + `:578-589` | F3a, F3b |
| **F-004** | closed | `conftest.py:453-463` and `session.py:218-226` | R7's measurement is now quoted as the reason the ordering is *not* load-bearing |
| **F-005** | closed | AC-1 class docstring `:300-316` (bound declared) + the AC-4 class renamed | M1/R5 are the two pins named; R6 is named as the measurement that the third is implied |
| **F-006** | closed | `:434-442` (comment above the real rebuild) | n/a — a one-line attribution note, as the reviewer asked |

**F-001.** `reset_engine()`'s docstring now splits into "What is pinned" and "**Not** pinned".
Kept: the cache-plus-pool mechanism sentence (AC-1 forces it; M1 and R5 make it red). Changed: the
four waves of gate failures are stated as the **motive** for the function, with AC-3's withdrawal,
its three measurements (24/24 correct, `pg_prepared_statements` 0, OID 2950) and the sentence *the
gate failures remain unexplained* — plus a pointer to the test module's docstring and to
`TestEngineLifecycle_WhyTheHazardCannotBeForced`. `session.py` was the one artifact of the three
that presented the hazard as established; it no longer does.

**F-002, the shape wave 46 requires.** The exemption stays derived and machine-checked; the
analysis got the three spellings it claimed and a deny default:

- counts **sites**, not `(file, name)` pairs — `_EXEMPT_PRIVATE_GLOBAL_SITES` is now a
  `{(file, name): count}` equality (nine sites, six pairs), so R1's tenth site in an exempt pair
  is a decision;
- recognises `monkeypatch.setattr("nonogram.db.session.engine", …)` (R2's string target) and any
  dotted assignment chain, not only `Name.attr = …`;
- collects aliases from `ast.Import` as well as `ast.ImportFrom` (`_session_aliases_in`), and the
  site scan unions the aliases of the file it is reading on top of the `_SESSION_ALIASES` floor —
  so R3 reds the site guard *and* the completeness test;
- `_names_the_session_module` returns `True`/`False`/**`None`**, and `None` (a spelling it cannot
  resolve — `import nonogram.db as pkg; pkg.session.engine = …`, or a string naming some other
  package's `session`) is a **failure**, never a silent pass (ADR-0039/R2).

The two false claims are corrected: the comment on the exemption set now says a tenth site, a new
name or a new file each fail it (and names its controls), and the AC-5 class docstring says
"nine **sites**, six pairs", lists the four things the guard reaches, and **declares the bound** —
the recognition is syntactic, so a reach through a fixture-bound name, `importlib`, or a
`globals()` write is outside it.

One extra fix this cycle forced: narrowing conftest's docstring for F-004 put the literal
`reset_engine()` into conftest's *prose*, which would have satisfied the old substring check in
`test_conftest_names_the_seam_at_its_call_site` with the call deleted. That test now reads
conftest's AST for an actual call on something that names the session module, with its own bound
stated (a bare imported `reset_engine()` would red it). M1 — the call deleted, the prose kept — and
M1b — the call turned into an attribute read — are its two controls.

**F-003.** The count comes from the module's own AST (`_test_functions_in`, which applies a
class-level `db_required` to the tests it contains, as pytest does) instead of from
`request.session.items`. The selection that the reviewer reported red
(`…::test_exactly_the_expected_number_of_tests_here_need_the_database` alone) is **1 passed**. The
second count (zero skip reasons, bare `psycopg2.connect`) is untouched.

**F-005.** AC-1's class docstring now declares the bound in writing: the engine identity (M1) and
the pool (R5) are independently falsifiable; the **backend** third is an implied consequence of the
pool assertion, because any mutation that leaves a pre-rebuild backend alive leaves its connection
in that pool — measured, R6 (`engine.dispose(close=False)`) died on the pool assertion. The poll
stays as the belt-and-braces reading and for the failure message, not as a third control.
**Rename, with the survivor named:** `TestEngineLifecycle_TheSkipProfileIsUnchanged` →
`TestEngineLifecycle_TheDbCoverageDoesNotQuietlyVanish`. Nothing is retired — the same two tests
carry on under the new name, which is what the class actually asserts; the old name is recorded in
the new class's docstring so a grep for it lands. AC-4's "(test: …)" line above is updated to the
new name.

**F-006.** A comment above the real `_rebuild_public_schema` call says that this test drives a live
`DROP SCHEMA` mid-run, so a lock-timeout red there is an earlier test's leaked transaction rather
than this card, and that `pg_stat_activity` names the holder.

#### Cycle-2 mutants (all applied one at a time, restored from byte-identical backups, `diff` clean after each)

| # | mutant | result |
|---|---|---|
| **G1** | the string-target branch deleted from `_private_global_sites_in` (R2's shape) | **RED.** `test_the_string_target_spelling_is_a_site` (`the string-target spelling … is invisible to the guard`) and `test_a_spelling_the_guard_cannot_resolve_is_a_failure`. `2 failed, 7 passed` |
| **G2** | the `ast.Import` branch deleted from `_session_aliases_in` (R3's shape) | **RED.** `test_a_plain_import_alias_is_a_site` (`the alias-completeness collection does not see the plain-import spelling`). `1 failed, 8 passed` |
| **G3** | sites counted per pair again (`sites[...] = 1`) | **RED** twice: the guard equality (`('test_db_connect_timeout.py','engine'), 1` vs `2`) and `test_a_tenth_site_in_an_already_exempt_pair_is_counted`. `2 failed, 7 passed` |
| **G4** | `None` → `False` in `_names_the_session_module` (deny default removed) | **RED.** `test_a_spelling_the_guard_cannot_resolve_is_a_failure` (`a reach the guard cannot classify must come back as a failure, not as nothing to see: []`). `1 failed, 8 passed` |
| **R1** | the reviewer's verbatim mutant — a **tenth** site in an already-exempt pair (`monkeypatch.setattr(db_session, "engine", None)` appended to `test_db_url_driver.py`) | **RED** (it SURVIVED in cycle 1). The guard equality (`('test_db_url_driver.py','engine'): 2` vs `1`) and the R1 control. `2 failed, 7 passed` |
| **R2** | the reviewer's verbatim mutant — `monkeypatch.setattr("nonogram.db.session.engine", None)` in a non-exempt file | **RED** (SURVIVED in cycle 1). `new site ('test_db_isolation.py','engine')`. `1 failed, 8 passed` |
| **R3** | the reviewer's verbatim mutant — `import nonogram.db.session as _review_probe_session`, then `… .engine = None` | **RED** (SURVIVED in cycle 1), twice: the completeness test (`tests/ names the session module as ['_review_probe_session']`) and the site guard. `2 failed, 7 passed` |
| **F3a** | `@pytest.mark.db_required` removed from the prepared-statement test (M4's shape, against the AST count) | **RED.** `1 test(s) in this module carry db_required, expected 2`. `1 failed, 1 passed` |
| **F3b** | the count's other edge — a **third** `db_required` marker added to `test_a_reachable_postgres_yields_no_db_mode_skip_reasons` | **RED.** `3 test(s) in this module carry db_required, expected 2`, naming all three. `1 failed, 1 passed` |
| **M1** | re-run: `app_session.reset_engine()` deleted from `conftest` — **with the narrowed docstring's `reset_engine()` prose kept** | **RED.** AC-1 (`the app's global engine survived the schema rebuild`) and the rewritten `test_conftest_names_the_seam_at_its_call_site` (`a mention in a docstring is not a call site`). `2 failed, 12 passed` |
| **M1b** | the call turned into an attribute read (`app_session.reset_engine`, no parens) — the call-site claim's edge | **RED.** `test_conftest_names_the_seam_at_its_call_site`. `1 failed, 8 passed` |
| **M2** | re-run: `_engine_url = None` deleted from `reset_engine()` | **RED**, still only on `test_it_resets_exactly_the_globals_the_builder_creates`. Unchanged verdict: the line is the documented cache key, defensible, and the derived guard is what catches it. `1 failed, 8 passed` |
| **M3** | re-run: `app_session.engine = None` added to `conftest` ahead of the seam | **RED** twice: AC-1's pool assertion and the guard (`found … ('conftest.py','engine'), 1`). `2 failed, 12 passed` |

#### Cycle-2 test selections (lock checked before each; no timings taken)

- `tests/test_db_engine_lifecycle.py`: **14 passed, 0 skipped** (10 + the four new controls).
- `…::TestEngineLifecycle_TheDbCoverageDoesNotQuietlyVanish::test_exactly_the_expected_number_of_tests_here_need_the_database` alone: **1 passed** — the red F-003 reported is gone.
- Touched-adjacent (`test_db_engine_lifecycle`, `test_card_156_db_fixture`, `test_db_isolation`, `test_db_url_driver`, `test_db_connect_timeout`, `test_db_e2e_smoke`, `test_card_109_database_guard`, `test_cli`): **260 passed, 0 skipped, 0 failed** (256 before + the four controls).

G-4 again held throughout: every run used `nonogram_pythonproject4_card_252_5ddd9defbd0a_test` as
both `DATABASE_URL` and `TEST_DATABASE_URL`; `nonogram_poc` was never named, connected to or
touched, and `_refuse_unless_test_database` was neither widened nor bypassed. The residual the
reviewer recorded (AC-1 builds the app engine from `os.environ["DATABASE_URL"]`, safe only because
it requests `db_session` first) is unchanged — that setup was not touched, so the ordering still
holds. G-6: nothing retired; the one rename names its survivor above. G-5: no new dependency
(`Counter` is stdlib).

- **[Orchestrator] the stale-docs hook fired and there is nothing to refresh.** The post-commit hook
  prints "source files changed — how-it-works docs may be stale" for **any** `.py` in the commit; it
  reads extensions, not content. Checked: no file under `docs/` or `meta/architecture/` names
  `reset_engine`, `_engine_url` or the global engine at all, and
  `docs/DB_PERSISTENCE_IMPLEMENTATION.md` mentions `session.py` only as "session_scope() context
  manager", which this card does not touch. Nothing regenerated, and the reason is recorded so the
  next person who sees the warning on a docstring-only commit does not go looking.

### [Review 2/3] Score 8.0 — FAILED on the severity gate (1 open Important) · ⚠ family regression

Report: `meta/review/20261019T205927Z-CARD-252-cycle2.yml` (copied to main). `min_score: 8` is met;
the open Important fails the card regardless, which is what the severity gate is for.

- **G-1 re-derived by the certifier, not taken on assurance**: both files parsed at `fc5508e` and
  `214b629`, every docstring stripped, `ast.dump` compared — `session.py` **identical**,
  `conftest.py` **identical**. **Zero executable production delta across the whole fix cycle**, so
  cycle 1's M1/R5/R6 measurements carry forward legitimately.
- **All six of cycle 1's findings certified closed**, each with a one-line verdict. F-001 closed
  **without smuggling in a new claim** — every sentence under "What is pinned" has a nameable
  control. F-005's declared bound was judged **accurate**, and found to *under*-claim (refutable
  only by a contrived mutation that checks the connection out first) — the safe direction. The
  rename is clean under G-6: same two tests, old name recorded, card AC-4 line and AC-status row
  both updated.
- **The self-flagged side effect was real.** The pre-fix test was literally
  `assert "reset_engine()" in source`, and the narrowed conftest docstring now contains that string
  at `:457` — so the old check *would* have passed with the call deleted. The AST rewrite's M1 (call
  deleted, prose kept) and M1b (call → attribute read) are both red, re-derived.
- **⚠ C2-F-001 (important, `test_db_engine_lifecycle.py:285`), family = cycle-1 F-002.** The next
  three `setattr` spellings out: a non-literal attribute name (`args[1]` not an `ast.Constant`), the
  **bare builtin** `setattr(app_session, "engine", None)` (the code requires `node.func` to be an
  `ast.Attribute` while the claim names exactly this spelling), and a computed string target. All
  three are idioms already in this test tree. ADR-0039/R1 and R2 both recorded violated.
- **C2-F-002 (minor), family = cycle-1 F-003.** The AST count fails **open** in one direction: a
  class renamed off pytest's `Test*` prefix counts 2 in the AST and collects 0 in pytest — coverage
  vanishes, guard stays green. Five other directions bias to red, correctly.

**[Family regression] The loop is regenerating defects in one artifact rather than converging on it**
— both findings land in families filed in cycle 1, and the gating one is the same file, guard, rules
and defect class. Two qualifications the certifier made and I keep: it is **not** the same mutant
surviving twice (cycle 1's three shapes are genuinely fixed and stay fixed — it is the next three
out), and the recurrence is confined to one guard in one test file while the card's product
behaviour has never been in question. The mechanism of the regression is the finding: **each fix
widens the mechanism shape by shape and then writes a reach claim slightly wider than the new
mechanism**, and a fourth shape exists for any finite list.

- **[Orchestrator] the escalation the family-regression rule asks for, answered rather than queued.**
  `review.family_regression: on` means escalate and let a human pick the source (design / undefined
  term / bad slice). The source is already diagnosed, by measurement, in the finding itself: the
  guard is being widened by enumeration, and its claim keeps running one shape ahead of it. So the
  decision available to a human is available now, and it is **not** "polish the same guard a third
  time". Fix cycle 2 is dispatched with a **structural** mandate — make the deny default total, on
  every axis, so the claim becomes *"these spellings, and it FAILS on anything setattr-shaped whose
  target or name it cannot read"*, which has no outside to probe. The discrimination that makes
  totality affordable is already in the guard: a target that is not the session module is none of
  its business. The explicitly sanctioned alternative is to **retreat the claim** to what the guard
  reads and claim nothing beyond it, with the measurement that forced the retreat. Both outcomes
  close the Important; a third enumeration does not, and the agent is told so.
- **[Orchestrator] what this card is allowed to cost.** `max_cycles: 3`, so cycle 3 is the last
  review. The thing being argued over is a test-tree guard on a card whose production delta is
  measured at zero in both cycles. If cycle 3 does not certify, the card does not get a fourth
  attempt at the guard — it gets its claim cut back to what is demonstrable and merges on that.

### Review cycle 2, findings closed, 2026-10-20 (`meta/review/20261019T205927Z-CARD-252-cycle2.yml`)

Score 8.0 (meets `min_score: 8`), failed the severity gate on one Important. Both findings were
again claim-versus-mechanism, and again nothing about the card's product behaviour changed:
`src/nonogram/db/session.py` is a **docstring-only** edit this cycle (verified by comparing the
file's AST with every docstring stripped against `214b629` — executable code identical, so G-1 and
the G-3 ordering are untouched). All work is in `tests/test_db_engine_lifecycle.py`.

| finding | verdict | where | the mutant that proves it |
|---|---|---|---|
| **C2-F-001** (Important) | **closed structurally** — the deny default is now total, not a fourth shape | guard at `:309-485`, claim at `:836-884`, five controls at `:1037-1197` | X1/X2/X3 all **RED** as real-file mutants; branch mutants B1–B7 each red a named control |
| **C2-F-002** (Minor) | closed by narrowing + a one-line filter | `_test_functions_in` `:106-172`, control at `:740` | B8 (filter deleted) reds `test_a_class_renamed_off_pytests_prefix_is_not_counted` |

**C2-F-001 — the structural exit, not a third widening.** The guard no longer enumerates spellings.
`_private_global_sites_in` now analyses **every** `setattr`-shaped call — `anything.setattr(...)`
*and* the bare builtin, via `_is_setattr_call` — and tells the two argument shapes apart by
**arity** (3+ positional = `setattr(obj, name, value)`, 2 = monkeypatch's string target; the builtin
cannot take two), which is what distinguishes them in Python rather than a guess. The rule is then:

- a **readable** attribute name that is not one of `session.py`'s engine globals ends the analysis;
- a target the guard resolves to some **other** module or object ends it too — this is the
  discrimination that makes totality affordable, and it has its own control;
- **everything left is a FAILURE**: a target it cannot rule out, and an attribute name it cannot
  read while the target is or might be the session module.

For the string-target form, `_string_target_tail` reads the *trailing literal segment* even of a
computed target (`f"{MOD}.engine"` → `engine`), so the guard can tell "names one of my globals on a
module I cannot read" (**failure**) from "names someone else's attribute" (not my business — this is
what keeps the tree's real `monkeypatch.setattr(f"{__name__}._WEB_SOURCES", [])` green).

The claim at `:836-884` is now *"it recognises these three spellings, and it fails on anything
setattr-shaped whose target or name it cannot read"* — a claim with no outside — plus the measured
numbers: over all of `tests/` the total guard finds **nine sites, six pairs, zero unanalysable**, so
`_EXEMPT_PRIVATE_GLOBAL_SITES` is an equality over the *entire* set the guard sees.

**Triage of what the total guard found across the test tree.** No site needed adding to the
exemption map: nothing outside the nine known sites sets a session global.
- **0** unanalysable spellings (the guard's failure list is empty on this head).
- **13** sites skipped by the other-target discrimination (a non-literal attribute name on something
  that is plainly not the session module — the six the reviewer named at
  `test_book_finalise_gutter.py:1907`, `test_book_plan.py:287`, `test_book_trim_persistence.py:891`,
  `test_web_submission.py:989`, `test_admin_error_text.py:102`, `property/test_image_fit.py:714`,
  plus the bare-builtin-on-a-class sites). **Correctly not flagged** — the guard must not flag them,
  so the discrimination is narrowed rather than the claim.
- **315** sites skipped because the attribute name is readable and simply is not one of the engine
  globals.
- **2** sites fall in the one declared residual (below).

**The one residual, declared with its measurement.** The guard follows **names, not values**. A call
whose target is a computed value *and* whose attribute name is also non-literal gives it nothing on
either axis, so it skips. Measured: exactly two such sites exist in this tree —
`tests/property/test_book_membership_floor.py:190` and `tests/test_book_finalise_gutter.py:1511`,
both `setattr(<a book row>, column, value)` — and failing on them is a red that cannot be
discriminated without guessing. The **edge** of that bound is pinned too: as soon as the attribute
name *is* readable, how the target was computed stops mattering, so
`setattr(sys.modules["nonogram.db.session"], "engine", None)` is a **failure**. That is one corner
wide, not "computed targets are outside the guard", and it is the same bound already declared and
accepted in cycle 2 (a fixture-bound name, `importlib` into a local, a `globals()`/`vars()` write).

**C2-F-002.** `_test_functions_in` now filters `ClassDef`s by pytest's `Test` prefix and returns the
set of classes that passed the filter, so the caller asserts the filter cannot silently empty the
walk. The docstring's "the way pytest applies it" is gone: it now declares exactly what the walk
sees (AST-visible `@pytest.mark.db_required` on `Test*` classes and their direct `test*` methods),
names the five fail-closed divergences, and names the one fail-open direction as the reason the
filter exists.

**Out-of-scope pointer (the certifier's optional item).** `session.py:249-254` now says which of the
three AC-3 numbers is a standing control — only `pg_prepared_statements == 0` after 40 executions
(`test_no_server_side_prepared_statement_is_ever_created`) — and that the 24/24 and the OID 2950 are
recorded on this card's `## Worktree notes`, not asserted in
`TestEngineLifecycle_WhyTheHazardCannotBeForced`.

#### Cycle-3 mutants (each applied alone, restored from a byte-identical backup, `diff` clean after each)

Branch mutants — one per new mechanism branch, deleting the branch:

| # | branch deleted | control that reds |
|---|---|---|
| **B1** | the bare-builtin arm of `_is_setattr_call` | `test_the_bare_builtin_setattr_spelling_is_a_site` (+ the bound control's edge). `2 failed, 18 passed` |
| **B2** | the non-literal-attribute-name deny | `test_a_non_literal_attribute_name_is_a_failure`. `1 failed, 19 passed` |
| **B3a** | the unreadable-module-part deny (string target) | `test_a_computed_string_target_is_a_failure`. `1 failed, 19 passed` |
| **B3b** | the unreadable-target deny (string target) | `test_a_computed_string_target_is_a_failure`. `1 failed, 19 passed` |
| **B4** | the other-target discrimination (`verdict is False → continue`) | `test_a_setattr_on_another_module_is_not_this_guards_business` **and** the tree-wide guard. `2 failed, 18 passed` |
| **B5** | the declared-bound skip (computed target + unreadable name) | `test_a_computed_target_with_an_unreadable_name_is_the_declared_bound` **and** the tree-wide guard. `2 failed, 18 passed` |
| **B6** | the JoinedStr/BinOp arms of `_string_target_tail` | `test_a_setattr_on_another_module_is_not_this_guards_business` **and** the tree-wide guard. `2 failed, 18 passed` |
| **B7** | the readable-name-outside-`names` arm | `test_a_setattr_on_another_module_is_not_this_guards_business` **and** the tree-wide guard. `2 failed, 18 passed` |
| **B8** | the `Test` prefix filter in `_test_functions_in` | `test_a_class_renamed_off_pytests_prefix_is_not_counted`. `1 failed, 19 passed` |

Real-file mutants, appended to a real non-exempt test file (the reviewer's verbatim shapes), run
against `TestEngineLifecycle_TheResetIsAPublishedSeam`:

| # | mutant | result |
|---|---|---|
| **X1** | `monkeypatch.setattr(app_session, name, None)` parametrised over the three globals, in `test_db_isolation.py` | **RED** (SURVIVED cycle 2). `test_db_isolation.py:1020: setattr(app_session, name, ...) — the attribute name is not a literal this guard can read`. `1 failed, 13 passed` |
| **X2** | the bare builtin `setattr(app_session, "engine", None)` | **RED** (SURVIVED cycle 2). Counted as a site: `Left contains 1 more item: {('test_db_isolation.py','engine'): 1}`. `1 failed, 13 passed` |
| **X3** | `monkeypatch.setattr(f"{_M}.engine", None)` — a computed string target | **RED** (SURVIVED cycle 2). `1 failed, 13 passed` |
| **R1** | cycle-1's tenth site in an already-exempt pair | **RED**, twice (the guard equality and its own control). `2 failed, 12 passed` |
| **R2** | cycle-1's string-target `setattr` in a non-exempt file | **RED**. `1 failed, 13 passed` |
| **R3** | cycle-1's `import nonogram.db.session as X` then `X.engine = None` | **RED**, twice (completeness + the site guard). `2 failed, 12 passed` |

#### Cycle-3 test selections (lock checked before each; no timings taken)

- `tests/test_db_engine_lifecycle.py`: **20 passed, 0 skipped** (14 + six new controls: five on the
  AC-5 guard, one on the AC-4 count).
- Touched-adjacent (`test_db_engine_lifecycle`, `test_card_156_db_fixture`, `test_db_isolation`,
  `test_db_url_driver`, `test_db_connect_timeout`, `test_db_e2e_smoke`, `test_card_109_database_guard`):
  **170 passed, 0 skipped, 0 failed** (164 before + the six controls).
- The same plus `test_cli` (the structural import guard): **266 passed, 0 skipped, 0 failed**
  (260 in cycle 2 + the six controls).

G-4 held throughout: every run used `nonogram_pythonproject4_card_252_5ddd9defbd0a_test` as both
`DATABASE_URL` and `TEST_DATABASE_URL`, passed as literals; `nonogram_poc` was never named,
created, dropped, connected to or truncated, and `_refuse_unless_test_database` was neither widened
nor bypassed. G-6: nothing retired or renamed this cycle — cycle 1's one rename stands. G-5: no new
dependency. G-1: zero executable production delta (docstring-stripped ASTs of `session.py`
identical to `214b629`).

**Is there a fourth shape?** Not inside the claim. The claim is now a deny default over every
`setattr`-shaped call plus the dotted assignment, with two stated exits (a readable name outside the
globals; a target resolved to something else) and one stated residual (both axes unreadable,
measured at two sites). A fourth *spelling* of a reach still exists outside the guard — anything
that reaches the globals through a value rather than a name, e.g. `globals()["engine"] = None` via a
fixture-bound module object — but that is the bound the guard declares in writing and does not claim
to catch, and the AST cannot follow it without executing the test tree.

- **[Orchestrator] what the structural mandate bought, and what it did not.** The guard stopped
  enumerating spellings: it now analyses every `setattr`-shaped call, tells the two argument shapes
  apart **by arity** (3+ positional is `setattr(obj, name, value)`; 2 is monkeypatch's string target,
  and the builtin cannot take two), and fails on anything left after two stated exits. X1, X2 and X3
  — the three shapes that survived cycle 2 — are all red, and cycle 1's R1/R2/R3 stayed red. Eight
  branch mutants, one per new branch, with B4/B6/B7 also reddening the tree-wide guard, which is what
  shows the other-target discrimination is load-bearing rather than decorative.
  What it did **not** buy is a guard with no limit. The limit is now a **measured** one: the walk
  follows names, not values, so a call whose target *and* name are both non-literal gives it nothing,
  and exactly two such sites exist in the tree. The edge is pinned in the direction that matters —
  `setattr(sys.modules["nonogram.db.session"], "engine", None)` fails, because a readable name makes
  the computed target irrelevant. That is the difference this card kept failing on: a residual
  declared with its measurement and its edge, instead of a claim one shape wider than the mechanism.
- **[Orchestrator] the tree-wide triage is now the claim, which makes it falsifiable by arithmetic.**
  0 unanalysable, 9 sites over six pairs (so the exemption map is an equality over the **entire** set
  the guard sees, not a subset), 13 skipped as another module or object — including all six
  non-literal-name sites the certifier named — 315 skipped as a readable name outside the globals,
  and 2 as the declared residual. No site was added to the exemption map, which is the part worth
  noticing: the total guard found nothing outside the nine known sites reaching a session global.
  Cycle 3 is asked to re-derive all five numbers rather than read them.
- **[Orchestrator] three cycles have gone into the guard and none into the fix.** `session.py` is
  docstring-identical by AST for the third cycle running. Cycle 3 is the last review, and it is asked
  for one of certify / merge-with-the-claim-cut-back / split — and, directly, whether this guard is
  worth keeping at all, or whether a smaller guard (or a declared convention and no guard) would
  serve the board better than an AST deny-default with a declared residual.

### [Review 3/3] Score 8.0 — one open Important · verdict: **merge with the claim cut back**

Report: `meta/review/20261019T213532Z-CARD-252-cycle3.yml` (copied to main). Last review the card
gets; there is no cycle 4.

- **Every mechanical claim verified, independently.** All five tree-wide numbers re-derived by a
  separate script replaying the guard's branch decisions rather than reading its output: 0
  unanalysable, 9 sites in 6 pairs (dict **byte-equal** to `_EXEMPT_PRIVATE_GLOBAL_SITES`), 13
  other-target skips, 315 readable-name-outside skips, 2 residual. The two residual sites are exactly
  the two named and no others; the residual's edge mutant reds; the residual's own skip **can fail**
  (B5 kills). X1 and X2 re-derived as real-file mutants, both red. B4 and B5 spot-checked, both
  killed, each also reddening the tree-wide guard. All six guardrails hold by measurement, including
  G-1 re-derived: `session.py` docstring-stripped AST **identical** `214b629`↔`ddd5a18`, so the
  production delta is zero for the third cycle running.
- **C3-F-001 (important) — the fourth axis is argument *binding*, not spelling.** The dispatch is
  three conditions (Assign + `ast.Attribute`; arity ≥ 3; arity == 2) and nothing catches what falls
  between them: `monkeypatch.setattr(app_session, name="engine", value=None)`, the same with
  `target=`, `setattr(*TRIPLE)`, and `app_session.engine, app_session.SessionLocal = None, None` (and
  the same target nested in a list/annotated/`for`/`with`) **reach a session global and pass
  silently** — confirmed executing, not merely parsed. In every one of them the target *and* the name
  are readable literals, so they are inside the claim and outside the mechanism: a hidden limit, not
  a declared one. `:840-845`'s "no outside … deny on every axis it can observe" is literally false.
- **Why the remedy is prose and not a fourth branch**, and the reviewer did the arithmetic that
  earns it: **zero** `setattr`-shaped calls in the tree take fewer than two positional arguments, and
  **zero** tuple/list/annotated attribute targets name an engine global. Cycle 2's survivors were
  live idioms at 17 real sites; these have **no traffic at all**. What is defective is a universally
  quantified sentence, and ADR-0039/R1's own remedy is "narrowed to what is measured or deleted".
- **C3-F-002 (minor)** — a second fail-open direction in the prefix filter: a `Test*` class carrying
  an `__init__` collects 0 in pytest (with a warning) and counts 1 in the walk. The sentence claiming
  "the one direction" is the defect; no filter change is wanted.
- **[Family regression] Third generation, both findings, and the certifier named what actually
  recurs.** The spelling axis genuinely closed and the mechanism genuinely became a deny default
  rather than a list — this is not the same defect in a wider shape. What regenerates is one **claim
  habit**: each fix widens the mechanism, then describes it with a universal quantifier. That is the
  finding to carry to the retrospective, not a fourth card.

- **[Orchestrator] the remedy is dispatched exactly as prescribed, and deliberately as prose plus one
  control.** Four sentences narrowed (`:840-845`, `:847`, `:374-375`, `:133-134`) and ~8 lines added:
  a tree-wide assertion that no `setattr`-shaped call has fewer than two positional arguments and no
  tuple/list/annotated attribute target names an engine global — both 0 today, so the new bound is a
  **control that can fail** instead of a sentence that cannot. It carries the two mutants this board
  requires: the keyword-bound reach appended to a non-exempt file must red it, and the same shape on
  another module must stay green. The agent is told that a fourth widening of the mechanism is
  forbidden, and that if any of the four sentences turns out to be true as written it should keep it
  and say so.
- **[Orchestrator] the guard's own size is now a separate card, not this card's residue.** The final
  reviewer answered the question directly: **no, not at this size** — three cycles, nine helpers,
  ~180 lines of AST machinery, ~220 lines of docstring claims, eleven controls, and **zero real
  violations caught**; the nine sites it reports are the nine it was written around. What it would
  keep is about a fifth: `_global_names_assigned_by` plus its test (the one genuinely *derived*
  authority here, so a fourth global added to `_init_engine` is inside the check the same day), the
  AST call-site and public-seam tests, and the exemption **equality** reduced to a per-file textual
  count — which still reds on a new file, a new name or a tenth site while claiming nothing about
  reach, so there is nothing left to probe. Its reasoning is worth keeping verbatim: *a convention
  enforced at review is honest about being a convention; an AST deny-default is a proof claim, and a
  proof claim in a dynamic language always has one more axis.* Carded as **CARD-254**, to land after
  this merge — never before, because shrinking a guard while its card is mid-merge is how a guard
  disappears with nothing in its place.
