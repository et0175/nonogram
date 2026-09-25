# CARD-148: The database driver is named, not inherited from a default

**Status:** in_progress
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
**Review score:** —
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
