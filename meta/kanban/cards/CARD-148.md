# CARD-148: The database driver is named, not inherited from a default

**Status:** review
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/148-name-the-db-driver
**Worktree:** ../PythonProject4-CARD-148
**Source:** production outage, 2026-09-25 (Render deploy failed: `ModuleNotFoundError: No module named 'psycopg'`)
**Idea:** —
**Wave:** 27
**Depends on:** —
**Touches:** src/nonogram/db/session.py, requirements.txt, pyproject.toml, tests/test_db_url_driver.py
**Review score:** 7.5 (cycle 1/3)
**Started:** 2026-09-25T10:30:09Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

On 2026-09-25 the deployed panel stopped booting with
`ModuleNotFoundError: No module named 'psycopg'`. **Nothing in this repository
changed.** SQLAlchemy released 2.1.0, `requirements.txt` asked for
`sqlalchemy>=2.0`, the next Render build resolved to it, and 2.1.0 changed the
default DBAPI for a bare `postgresql://` URL from `psycopg2` to `psycopg` (v3),
which is not installed.

Verified in isolation, not inferred:
`make_url("postgresql://…").get_dialect().driver` is `psycopg` on 2.1.0 and
`psycopg2` on 2.0.x.

The immediate stopgap is already in place — `sqlalchemy>=2.0,<2.1` in both
`requirements.txt` and `pyproject.toml`'s `db` extra. **This card is the
lasting fix, and the cap comes off as part of it.**

Two independent problems to close:

1. **The driver is inherited, not chosen.** `session.py` passes `DATABASE_URL`
   to `create_engine` exactly as the environment gives it, so which DBAPI the
   panel uses is decided by whatever SQLAlchemy's default happens to be on the
   day of the build. Name it: normalise a bare `postgresql://` (and Render's
   legacy `postgres://`) to an explicit `postgresql+psycopg2://` before
   `create_engine` sees it — or move to psycopg 3 deliberately and name that.
   Either is fine; inheriting a default is not.

2. **Local and production resolve differently, and nothing notices.** The venv
   here is pinned by history to SQLAlchemy 2.0.52, so the whole suite passed
   while production could not boot. There is no lock file. A test that asserts
   the resolved driver would have failed here the moment the cap came off —
   that is the test this card owes.

## Acceptance criteria

- **AC-1:** Whatever scheme `DATABASE_URL` carries (`postgres://`,
  `postgresql://`, or an explicit `postgresql+psycopg2://`), the engine is
  built on the driver this project ships, and the URL handed to `create_engine`
  names it explicitly. *test: TestDbUrl_DriverIsNamedNotInherited*
- **AC-2:** A test fails if the installed SQLAlchemy would resolve a bare
  `postgresql://` to a driver that is not installed — so the next default
  change is caught here rather than on a deploy.
  *test: TestDbUrl_TheResolvedDriverIsInstalled*
- **AC-3:** With AC-1 and AC-2 in place, the `<2.1` cap is removed from both
  `requirements.txt` and `pyproject.toml`, and the suite passes against the
  uncapped resolution. *test: TestDependencyBaseline_SqlalchemyIsNotCapped*
- **AC-4:** In-memory mode (no `DATABASE_URL`) is unaffected — no import of any
  database driver happens when the panel runs without one.
  *test: TestDbUrl_InMemoryModeImportsNoDriver*

## Engineering constraints

- **EC-1:** The normalisation must not alter any other part of the URL — host,
  port, database, query parameters and credentials survive untouched, and the
  password never reaches a log or an exception message. Verify over a seeded
  corpus of URL shapes, not one example.

## Guardrails

- G-1: ADR-0006/R1 — `project.dependencies` stays exactly Pillow + NumPy. The
  database packages live in the `db` extra and this card does not move them.
- G-2: Do not change what database the panel talks to, or any schema. This is
  about how the connection is constructed, nothing else.
- G-3: CON-015 — no bind address, host or debug-flag change.

## Architecture context

- **FR:** — (operational defect; no FR)
- **ADR:** ADR-0006/R1 (dependency baseline)
- **Components:** COMP-009, COMP-010
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Env] forge 2026.8.17
- [Parallel] Run alongside CARD-140 (wave 26, in review). No file overlap: CARD-140 is
  admin/app.py + book_pdf_generator.py + templates; this card is db/session.py +
  requirements.txt + pyproject.toml. The one shared resource is the repo's `.venv`, which
  CARD-140's review is using — see the venv constraint below.

[Why P1] The stopgap cap restores service but freezes a dependency on a
deadline nobody chose: 2.0.x stops getting fixes eventually, and the cap is the
kind of line that survives for two years because removing it is scary. The card
exists so the removal is a planned step with a test behind it.

[Architect station] This is the third item this week whose real home is the
model rather than a card: the dependency baseline (ADR-0006/R1) says what may
be installed but says nothing about pinning discipline or about who chooses a
driver. Worth a CON or an ADR amendment rather than a comment in
`requirements.txt`.

- [Scope] src/nonogram/db/session.py, migrations/env.py, tests/conftest.py, requirements.txt,
  pyproject.toml, tests/test_db_url_driver.py — one commit, a776d53. Two of those are SCOPE+
  beyond the card's Touches (migrations/env.py, tests/conftest.py); both are justified below
  and both are on the deploy or the gate path, not opportunistic.
- [Build gate] PASSED twice, re-run by the orchestrator rather than taken on the agent's
  word. Under the shared venv (SQLAlchemy 2.0.52) and under the throwaway venv at
  `<scratchpad>/venv-sa21` (SQLAlchemy **2.1.0**, psycopg2-binary 2.9.13, **psycopg v3
  absent** — production's exact resolution, which I verified before trusting it: a bare
  `postgresql://` resolves to `psycopg` there). Both runs: the two pre-existing failures and
  nothing else.
- [Guard] The outage reproduced and the fix verified by hand under 2.1, not inferred:
  `create_engine("postgresql://u:p@h:5432/db")` raises `ModuleNotFoundError: No module named
  'psycopg'`; `normalized_url(...)` yields `Engine(postgresql+psycopg2://u:***@h:5432/db)`
  with `url.password` intact; `postgres://` normalises to `postgresql+psycopg2`; an explicit
  `postgresql+psycopg://` keeps psycopg; `sqlite:///` passes through untouched. Cap absent
  from both requirements.txt and pyproject's `db` extra.
- [Requirement defect, for the architect station — NOT hand-patched here] AC-2 and AC-3 are
  mutually exclusive as written: on 2.1.x with only psycopg2 installed, SQLAlchemy's bare
  default IS an uninstalled driver, so a test demanding that default be importable would
  make a healthy uncapped install permanently red over a driver this project deliberately
  does not ship. The implementation resolved it by asserting the DBAPI **the panel's engine
  resolves to** is importable, plus a third test pinning that the panel's answer is invariant
  to SQLAlchemy's default — which is the right reading of the intent, and is verified by
  mutation (7 tests fail on 2.0.52 and 9 on 2.1.0 with the normalisation removed). The card's
  AC-2 text should be corrected where it was written rather than reworded to match the code:
  route via /forge:architect (requirements delta), then decompose.
- [Rebase needed before merge] The branch was cut at 25b54f5, before CARD-140 merged
  (5d54019). `git diff main..HEAD` is therefore misleading — it shows CARD-140's files as
  deletions. The card's real diff is 6 files / +849 / -20 against the merge base. Rebase onto
  main and re-run the gate before merging.
- [Not verified, and it is the thing that matters] There is no live Postgres here, so this is
  proven at engine-construction and dialect-import level only. The panel's actual boot on
  Render is unproven by anyone. Given that the live panel runs on Postgres and that the
  Render service ignores render.yaml, the deploy is the real test.
- [Hook] A `forge: source files changed — how-it-works docs may be stale` hook fired on the
  agent's commit; /forge:explain was not run.

- [Review 1/3] 7.5 · risk MEDIUM · lane DEEP ·
  `meta/review/20260925T121330Z-CARD-148-cycle1.yml` · 0 critical, 3 important, 3 minor.
  Below `min_score: 8`, so a fix cycle is required. The normalisation itself is
  mutation-clean; every gating finding is about the coverage of the two SCOPE+ files and one
  error-taxonomy edge. System contract: 38 rules — 2 ✓ (ADR-0006/R1, ADR-0019/R1), 36 ⚠
  no_eligible_fact, 0 ✗. G-1, G-2 ✓; CON-015 fell outside the assembled scope and was
  verified directly. Nothing the orchestrator pre-verified was wrong.
  - **Would the suite have caught the outage before deploy? Yes, demonstrated.** Mutant M1
    (`normalized_url` → `return url`, i.e. pre-card behaviour): 7 tests fail on 2.0.52 and 9
    on 2.1.0, the extra two being AC-2's, one of them failing with the deploy's own
    `ModuleNotFoundError: No module named 'psycopg'`. AC-1's five fail even on 2.0.52, where
    the old suite was green — so the defect is caught on this machine, before a 2.1.x build
    exists.
  - F-001 (important) `tests/conftest.py:71` — the probe's driver naming is UNTESTED, and the
    test the card names as covering it does not discriminate it: it counts probes and compares
    verdicts, both of which hold whichever argument is passed. **Mutant M4 survived on both
    versions.** This is the guard against this repo's known "DB tests skip silently" mode, and
    it is unpinned. One assertion fixes it.
  - F-002 (important) `migrations/env.py:78` — the deploy path (render.yaml buildCommand →
    `alembic upgrade head`) has zero covering tests, and is the only place the
    "never through text" rule is necessarily broken (`engine_from_config` takes a
    string-keyed dict). The reviewer verified the round-trip is lossless over all 260 corpus
    URLs on both versions — 0 field mismatches — so it is correct today, pinned by nothing.
  - F-003 (important) `session.py:97` — `except ArgumentError` MISSES `ValueError`. `make_url`
    raises a bare `ValueError` from `int(port)` for an unbracketed IPv6 host
    (`postgresql://u:p@2001:db8::1:5432/db` — the commonest DATABASE_URL typo), and for
    `@h:notaport/` and `@h:/`. So the docstring's "Raises RuntimeError if not a URL SQLAlchemy
    can parse" is false, and the `from None` / `_scheme_of` shield never runs on that path.
    No password leaks there (verified absent from message, traceback and chain), so EC-1's
    outcome holds — but its *guarantee* does not. The corpus contains an IPv6 host only in its
    always-bracketed `URL.create` form, which is why it was missed.
  - F-004 (minor) `_scheme_of` runs INSIDE the except block, so a raise there re-exposes
    SQLAlchemy's `ArgumentError` — which echoes the whole URL including the password — as an
    unsuppressed `__context__`. Demonstrated on both versions; the exact mechanism `from None`
    exists to block. Minor only because no current caller can pass a non-`str`.
  - F-005 (minor) `POSTGRES_DRIVER` is cross-checked against pyproject's `db` extra only.
    `requirements.txt` — the manifest the Render build actually installs — has its DBAPI line
    unchecked.
  - F-006 (minor) `scripts/diagnose_postgres.sh:108` tells the operator to set `DATABASE_URL`
    to `postgresql+psycopg://…`, an uninstalled driver that `normalized_url` deliberately
    preserves — so following the repo's own diagnostic reproduces the outage's error message.
  - Card overstates one thing: the SCOPE+ note implies both `migrations/env.py` branches were
    broken. Only the online one was — `URL.get_dialect()` loads the dialect class without
    importing the DBAPI. Offline was verified working end to end under 2.1.0 (`alembic upgrade
    head --sql` emits full DDL, exit 0, secret count 0).
  - There is **no third place** a bare `DATABASE_URL` reaches SQLAlchemy: swept
    `create_engine|engine_from_config|create_async_engine` across every .py/.ini/.yaml/.sh/
    .toml/.cfg — only session.py, migrations/env.py and conftest.py. Coverage of the reach is
    complete.
  - Reviewer agrees with routing the AC-2/AC-3 contradiction to the architect station as a
    requirement defect rather than rewording the card to match the code.
  - Model note: ADR-0006/R1's declared check ref `TestDependencyBaseline_IsExactlyPillowAndNumpy`
    is not a collectible node id — only a docstring binding. The live test is
    `test_the_dependency_baseline_is_still_closed` (tests/test_export_pdf.py:1249). The rule
    should be re-pointed at the architect station.
- [Review sync] 1 report → meta/review/

- [Build gate] PASSED after Fix 1 (f36c4ed), re-run by the orchestrator under BOTH versions.
- [Guard] The three fixes I care most about, verified by hand rather than read off the
  report. F-003: an unbracketed IPv6 URL carrying a password
  (`postgresql://u:s3cr3t-p@ss@2001:db8::1:5432/db`), a non-numeric port and an empty port
  all now raise `RuntimeError` with the secret absent from the message AND from the
  formatted traceback, `__cause__ is None`, `__suppress_context__ is True`. F-004: bytes,
  `None` and an int input are all handled totally, with no "During handling of the above
  exception" in the traceback. F-001, the mutant that SURVIVED cycle 1 (29 passed, exit 0):
  re-applied it myself — reverted conftest's probe to the raw URL — and it now FAILS on both
  2.0.52 and 2.1.0, on the `legacy-postgres-alias` and `uppercase-scheme` ids. conftest.py
  restored and the tree verified clean afterwards.

### Cycle 2 — NOT performed independently (2026-09-29)

- [Escalated] The cycle-2 reviewer subagent terminated on an account spend limit (HTTP 429,
  `req_011CfQDdMfZurywEAGQZ1cSc`) before producing any finding. Cycle 2 has therefore NOT been
  run by an independent circuit, and the card stays at `Review score: 7.5 (cycle 1/3)` — below
  `min_score: 8`. It must not merge on cycle 1's score.
- [Self-approval refused] The orchestrator re-ran cycle 2's checks inline (the documented
  degradation when subagents cannot be spawned) and then attempted to write a scored cycle-2
  report. That write was refused as self-approval, and the refusal is right: the same actor
  wrote the fix brief, so an inline score is not the second circuit the gate is asking for.
  The measurements below stand as facts; they are not a review verdict.

FACTS MEASURED FIRST-HAND ON f36c4ed (no score attached):

- Full suite, **SQLAlchemy 2.1.1** (uncapped resolution; the 2.1.0 venv died with the session
  and was rebuilt, psycopg v3 absent, bare `postgresql://` still resolves to `psycopg`):
  5325 tests, 5297 passed, 1 failed, 27 skipped.
- Full suite, **SQLAlchemy 2.0.52**: identical — 5325 / 5297 / 1 / 27.
- The single failure is the known pre-existing
  `test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`.
- **This gate is WEAKER than the 2026-09-25 run on the same commit, and not because of this
  card.** That run recorded 5316 passed / 2 failed / 7 skipped. The local Postgres role
  `postgres` no longer exists ("FATAL: role \"postgres\" does not exist"), so ~20 DB-backed
  tests now skip instead of executing — among them
  `test_wave3_e2e::test_batch_creation_form_renders`, which is why only one of the two known
  pre-existing failures appears. **It is skipping, not passing.** This is the repo's known
  "DB tests skip silently" hazard surfacing in the gate itself — the very thing F-001's fix
  exists to stop happening invisibly inside the harness.
- The card's own `tests/test_db_url_driver.py`: 37 tests, **37 executed, 0 skipped** under
  2.1.1 — so the card's own evidence does not depend on the unreachable Postgres.
- F-001's mutant, re-applied by the orchestrator (conftest's probe reverted to the raw URL):
  now FAILS on both versions (`legacy-postgres-alias`, `uppercase-scheme`) where it SURVIVED
  in cycle 1 with 29 passed / exit 0. conftest.py restored, tree verified clean.
- The widened `except (ArgumentError, ValueError)` rejects nothing legitimate: 16 URL shapes
  probed under 2.1.1 (every corpus family plus a `mysql+pymysql` URL) — 0 now take the error
  path.
- `scripts/diagnose_postgres.sh` passes `bash -n`; its advice is now `postgresql+psycopg2://`.
- Observation for CARD-139's sweep, not fixed here: `migrations/env.py:19` imports the seam as
  `from src.nonogram.db.session import normalized_url` — the `src.`-prefixed double-import
  shape. Harmless here (a pure string function, no enum identity), but it widens the precedent
  env.py's existing `src.`-prefixed models import set.

WHAT IS STILL OWED BEFORE MERGE: an independent cycle-2 review, and a rebase onto main (the
branch was cut at 25c54f5, before CARD-140 merged at 5d54019) with the gate re-run on the
rebased result.

## Implementation (CARD-148)

### AC → test mapping

All in `tests/test_db_url_driver.py`; 28 tests, all of which **execute** (none
needs a live database, so none of them can skip green).

| AC | Class | Tests |
|----|-------|-------|
| AC-1 | `TestDbUrl_DriverIsNamedNotInherited` | 9 (4 parametrised schemes + explicit-driver, sqlite pass-through, the `create_engine` capture, the shipped-driver cross-check, the CARD-097 deadline regression) |
| AC-2 | `TestDbUrl_TheResolvedDriverIsInstalled` | 3 |
| AC-3 | `TestDependencyBaseline_SqlalchemyIsNotCapped` | 4 (both files, their agreement, and G-1's Pillow+NumPy baseline) |
| AC-4 | `TestDbUrl_InMemoryModeImportsNoDriver` | 2 (the assertion, and the same probe shown detecting a driver that *was* imported) |
| EC-1 | `TestDbUrl_NormalisationChangesNothingElse` | 10 (7 tests, one of them 4-way parametrised) |

### AC-1 design choice: normalise to `postgresql+psycopg2://`

Chosen over moving to psycopg 3, because it is the option that changes
*nothing else*. This project ships `psycopg2-binary` today and G-1 forbids
moving the database packages, so naming psycopg 3 would have meant swapping a
dependency inside a defect fix — a decision, not a repair. `POSTGRES_DRIVER` in
`session.py` is the single place that name lives, and a test cross-checks it
against the `db` extra so the two cannot drift; upgrading later is that one
constant plus the extra, together.

Three details worth the reviewer's eye:

* **Consistent with what already knew about both schemes.** The check reuses
  `_TIMEOUT_SCHEMES = ("postgresql", "postgres")` rather than introducing a
  second notion of "is this postgres". The backend is *canonicalised* to
  `postgresql`, not merely given a driver: `make_url("postgres://…")` parses
  happily and then `get_dialect()` raises `NoSuchModuleError`, so Render's
  legacy alias was never inheriting a default — it was broken outright.
* **An explicitly named driver is left alone** (`postgresql+psycopg://` stays
  psycopg). The defect is inheriting a default; overriding an operator's stated
  choice would be the same defect with our name on it.
* **A `URL` object is passed to `create_engine`, never a string.** `str(url)`
  renders the password as `***`, so normalising through text would produce a
  URL that looks right in a log and cannot authenticate.
  `test_create_engine_receives_the_named_url_with_its_password_intact` captures
  the actual argument and asserts both `isinstance(…, URL)` and that the secret
  survived.

### EC-1 corpus

260 URLs (floor asserted at 200 inside the test), `random.Random(148)`; no
hypothesis — ADR-0006/R1's baseline is closed. Exhaustive over 5 schemes ×
13 passwords, with username / host / port / database / query cycled by the
seeded generator, and the shapes the design called out asserted present:
absent and empty password; `@ : / ? #` and percent-encodings and a literal `%`
and unicode and 64 chars in the password; `@` and `:` in the *username*; IPv6
literal host; no port; absent and empty database; one and two query parameters
and one with a space in its value; already-`+psycopg2`; a different explicit
driver; uppercase scheme; sqlite pass-through.

Built as `URL` objects and rendered with `render_as_string(hide_password=False)`
rather than assembled as text, so the expected value of every field is the
object's own field — independent of the function under test — and so the test
does not reimplement percent-encoding and thereby agree with a bug. Compared
**field by field**, not by rendered string: `render_as_string` sorts query
parameters, and on 2.1 it percent-encodes the colons in `:memory:` where 2.0
does not. That last one actually bit — the first version of the sqlite
pass-through test failed on 2.1 for a change this code did not make. It is now
compared against `make_url(raw)`, and the docstring says why, because the
tempting "fix" was to start doing string surgery in production.

Password containment has two halves: nothing is logged (asserted with `caplog`
at DEBUG over the whole corpus, and that the record list is *empty*), and an
unparseable URL raises our own `RuntimeError` naming only the scheme, with
`raise … from None` so SQLAlchemy's `ArgumentError` — which has echoed the
offending string back before now — cannot reach the traceback. The test asserts
`__cause__ is None` **and** `__suppress_context__ is True`, since the latter is
the one that actually suppresses printing and is easy to drop.

### AC-2, and why it does not contradict AC-3

Read literally, "a test fails if the installed SQLAlchemy would resolve a bare
`postgresql://` to a driver that is not installed" and "the suite passes
uncapped" cannot both hold: on 2.1.x with only psycopg2 installed, SQLAlchemy's
bare default *is* an uninstalled driver, and demanding it be importable would
make a healthy 2.1.x install red over a driver this project deliberately does
not ship. So the test asserts the thing that was actually false on 2026-09-25:
**the DBAPI the panel's engine would be built on is importable**, resolved
through the production path and then actually imported via `import_dbapi()`.
A third test records what SQLAlchemy *would* have chosen and asserts the
panel's answer is invariant to it — that invariance is the fix, and it is the
assertion a future default change cannot quietly satisfy.

Verified by mutation rather than argued: with `normalized_url` reduced to
`return url` (pre-card behaviour), **7 tests fail on 2.0.52 and 9 on 2.1.0**,
the extra two on 2.1.0 being AC-2's — i.e. the outage reproduces as a red test
on production's resolution, and AC-1 catches the defect even here, where the
default happens to be right and the old suite was green. Implementation
restored afterwards.

### AC-3 — which venv produced which result

* **Shared venv, read-only** (`…/PythonProject4/.venv`, SQLAlchemy 2.0.52 +
  psycopg2 2.9.12): full suite **5307 passed, 7 skipped**, 2 failures, both
  pre-existing and unrelated (`test_admin_workflow.py::…::test_size_configuration_applied`,
  `test_wave3_e2e.py::…::test_batch_creation_form_renders` — stale heading
  assertions on the batch-create form). Nothing was installed, upgraded or
  removed in it.
* **Throwaway venv built for this card**, in the session scratchpad rather than
  the worktree (SQLAlchemy **2.1.0** + psycopg2-binary 2.9.13 + pytest, Pillow,
  NumPy, Flask, Werkzeug, reportlab, alembic; **psycopg v3 deliberately absent**,
  so this is exactly production's resolution): full suite **5307 passed, 7
  skipped**, the same 2 pre-existing failures and nothing else. The cap is
  genuinely safe to remove.

The outage was also reproduced in that venv before trusting the fix:
`create_engine("postgresql://…")` → `ModuleNotFoundError: No module named
'psycopg'`; `normalized_url(...)` → `Engine(postgresql+psycopg2://u:***@h:5432/db)`.

The 7 skips are `test_db_e2e_smoke.py` and friends, which want a live Postgres
that is not configured here — the known "DB tests skip silently" shape. None of
this card's tests is among them.

### SCOPE+

* `SCOPE+ migrations/env.py` — the second place a bare `DATABASE_URL` reaches
  SQLAlchemy, and it is on the deploy path (`render.yaml`'s build command runs
  `alembic upgrade head`). Removing the cap while leaving this alone would have
  fixed the panel's boot and left the migration step to die of the same
  `ModuleNotFoundError` on the next default change — the outage half-closed.
  Both the online and offline branches now go through `normalized_url`.
* `SCOPE+ tests/conftest.py` — `_unreachable_reason` probes the database
  through "the same engine options production uses", which stopped being true
  the moment production also named a driver. On a SQLAlchemy whose default is
  not installed, the probe would have failed to load psycopg and every database
  test would have reported "unreachable" and skipped **green** against a
  database that was in fact right there — the exact failure mode this card
  exists to stop, relocated into the harness. One argument changed; covered by
  the existing `test_the_reachability_verdict_is_taken_once_per_url`.

Nothing was added to the worktree that is not source (`git status` shows five
modified files plus the new test); the throwaway venv lives in the session
scratchpad, so `.git/info/exclude` needed no entry.

### Architect station — the gap is sharper now, and still not mine to close

Noted, not acted on. Implementing this made the missing rule concrete rather
than abstract: `POSTGRES_DRIVER` in `session.py` is now a load-bearing
architectural fact — *which* DBAPI this system connects through — and it lives
in a capability module's constant with a test holding it against
`pyproject.toml`. That is a fine mechanism and the wrong owner. ADR-0006/R1
says what may be installed; nothing says who chooses a driver, or that a
version ceiling is a dated decision needing a review trigger rather than a
comment. Both cost a production outage this week. No ADR written and no model
amended, per instruction.

### [Fix 1] — cycle-1 review findings (score 7.5 / min 8)

Every gating finding was about *coverage* of the two SCOPE+ files plus one
error-taxonomy edge; the normalisation itself was mutation-clean and is
unchanged.

- **F-001 (important) fixed** — `TestHarness_TheReachabilityProbeUsesTheSameNaming`
  (3 parametrised schemes) captures what `sqlalchemy.create_engine` actually
  receives inside conftest's probe and asserts it is a `URL` with
  `drivername == "postgresql+psycopg2"` and the password intact. Mutant M4
  (`tests/conftest.py:71` reverted to the raw `database_url`) now **fails 3
  tests on 2.0.52 and 3 on 2.1.0**; it survived both before. Re-mutated,
  observed red, restored.
- **F-002 (important) fixed** — `TestMigrations_TheDeployPathNamesTheDriver`
  drives `migrations/env.py`'s **online** branch for real (a subprocess that
  replaces `sqlalchemy.engine_from_config` before alembic loads env.py, then
  runs `alembic upgrade head`) and asserts the config dict's `sqlalchemy.url`
  names psycopg2 with username/host/port/database/password all intact. Plus
  `test_the_text_round_trip_that_alembic_forces_is_lossless` over all 260
  corpus URLs + `:memory:` + a spaced path, field by field. Reverting env.py's
  online branch to the raw URL fails the first on both versions.
  `render_as_string(hide_password=False)` there is correct, not a defect —
  `engine_from_config` takes a string-keyed dict — and env.py is otherwise
  unrestructured.
- **F-003 (important) fixed** — `except (ArgumentError, ValueError)`;
  `make_url` raises a bare `ValueError` out of `int(port)` on both versions.
  Three new parametrise ids: `ipv6-host-without-brackets`, `non-numeric-port`,
  `empty-port`. Docstring corrected — it promised a `RuntimeError` it did not
  deliver for those. **Why the corpus missed it:** it builds its IPv6 host
  through `URL.create`, which always renders the brackets, so the malformed
  *spelling* cannot exist in it. Decision: leave the corpus as URL objects —
  its independence from the function under test is exactly what makes EC-1's
  field-by-field comparison worth anything, and raw text would have to be
  hand-encoded (the way a test ends up agreeing with a bug). Raw-text shapes
  belong where they now are: the unparseable parametrisation, which is the
  only place a shape SQLAlchemy *cannot* parse can live at all.
- **F-004 (minor) fixed** — the scheme is computed **before** the `try` and
  `_scheme_of` is total for any input, so the handler's body cannot raise and
  cannot resurface SQLAlchemy's URL-echoing `ArgumentError` as an unsuppressed
  `__context__`. `test_a_non_string_cannot_resurface_sqlalchemys_url_echoing_message`
  asserts it over `bytes`/`None`/`int`/`object` against the *formatted
  traceback*. Reverting either half fails it on both versions.
- **F-005 (minor) fixed** — `test_the_shipped_driver_is_the_one_the_project_installs`
  now checks **both** manifests (requirements.txt is what the Render build
  installs) and is bidirectional in each: the set of PostgreSQL DBAPIs a
  manifest names must be non-empty and contain nothing but the shipped driver.
  Swapping requirements.txt's `psycopg2-binary` for `psycopg` now fails it.
- **F-006 (minor) fixed** — `SCOPE+ scripts/diagnose_postgres.sh` — line 108
  told the operator to set `DATABASE_URL` to `postgresql+psycopg://`, a driver
  this project does not install and which `normalized_url` deliberately
  preserves, so following the repo's own diagnostic reproduced the outage's
  exact error. Now `postgresql+psycopg2://`, with a comment saying why. One
  line plus its comment; nothing else in that script was touched.
- **F-007, F-008 (info)** — no code change, by the reviewer's own routing:
  env.py's `src.`-prefixed import belongs to CARD-139's sweep, and AC-2/AC-3's
  literal mutual exclusivity is a requirement defect for the architect station.

Suite, both versions, worktree as cwd: **2 failed, 5316 passed, 7 skipped**
(the two failures are the known pre-existing ones). `tests/test_db_url_driver.py`
is now **37 tests, all executing, 0 skipped** on both — 9 more than before, and
none of them needs a live database.

---
