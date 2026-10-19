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
