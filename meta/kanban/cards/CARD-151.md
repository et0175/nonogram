# CARD-151: The launcher's database check understands the URLs the panel accepts

**Status:** ready
**Priority:** P2
**Category:** bug
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** CARD-150 cycle-1 review, F-006 (2026-10-01); mechanisms re-measured by the orchestrator before cutting this card
**Idea:** —
**Wave:** 28
**Depends on:** —
**Touches:** scripts/start_admin_local.sh, tests/test_start_admin_local.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

CARD-150 made `scripts/start_admin_local.sh` check the database it is about to
use. The check itself is `psql "$DATABASE_URL" -c "SELECT 1"`, and it hands
`psql` a URL that is not always a libpq URL. Two measured consequences — both
reproduced on this machine 2026-10-01, neither inferred from the review:

### 1. A driver-qualified URL is refused, though the panel accepts it

    $ psql "postgresql+psycopg://omelnikova@localhost:5432/nonogram_dev" -c "SELECT 1"
    psql: error: FATAL: database "postgresql+psycopg://omelnikova@localhost:5432/nonogram_dev"
          does not exist

`psql` does not parse that as a URI at all — it takes the **whole string as a
database name**. The same database over a plain `postgresql://` URL answers
`SELECT 1` immediately.

This matters because `postgresql+psycopg2://` is a URL this project
*deliberately produces and preserves*. `normalized_url` in
`src/nonogram/db/session.py` exists to put the driver into the URL (CARD-148,
the 2026-09-25 outage), and it leaves an explicitly named driver alone on
purpose — "the defect this closes is inheriting a default, and an explicit
`postgresql+psycopg://` is somebody's decision, not an accident". So an owner
who exports the URL the panel itself would build is told their database is
unreachable.

Note `DB_NAME` is **not** the problem: `${DATABASE_URL##*/}` extracts
`nonogram_dev` from a driver-qualified URL correctly. Only the string passed to
`psql` is wrong.

### 2. A URL with no database name falls through to a different database

    $ psql "postgresql://omelnikova@localhost:5432/" -c "SELECT 1"
    FATAL: database "omelnikova" does not exist

With a trailing slash, `DB_NAME` is empty and `psql` falls back to connecting
to a database named after the **user**. On this machine no such database
exists, so it fails — but on a machine where one does, the check passes and the
script prints `✓ PostgreSQL is running, database '' reachable`, a green tick
naming no database at all, and then starts the panel against a `DATABASE_URL`
the panel cannot use either. That is the unsafe direction, and it is the exact
shape of the defect CARD-150 was cut to remove.

## What to do

1. **Give `psql` something it understands.** Either strip the `+driver` from the
   URL before the check, or build the connection from its parts
   (`-h`/`-p`/`-U`/`-d`), or set `PG*` variables. Judge which keeps the script
   simplest — but whatever you choose must preserve what CARD-150 gained: the
   check still names the database it is about to use, and still carries the
   URL's host, port and credentials rather than matching on the name alone.
2. **Refuse an empty database name** rather than letting `psql` substitute one.
   A `DATABASE_URL` with no database is a configuration error the owner should
   be told about, named as such; it must never reach a green tick.
3. Keep the refusal message's shape: it names the database, prints the URL and
   its source, and says the script does not create a database.

Out of scope: the two Docker branches' `-d "$DB_NAME"` (they discard the URL's
host, port and credentials — a separate finding, F-005, still open on the
backlog); the sibling scripts `setup_admin_local.sh` and `run_admin_tests.sh`
(their own backlog card); anything about the panel itself.

## Acceptance criteria

- **AC-1:** With `DATABASE_URL` carrying an explicit driver
  (`postgresql+psycopg2://…`), the script's check succeeds against a reachable
  database rather than refusing it.
  *test: TestStartAdminLocal_AcceptsADriverQualifiedUrl*
- **AC-2:** With `DATABASE_URL` naming no database (a trailing slash), the
  script refuses, says the URL names no database, and never prints a green tick
  — whether or not a database named after the user exists.
  *test: TestStartAdminLocal_RefusesAUrlThatNamesNoDatabase*
- **AC-3:** What CARD-150 won is unchanged: the check still names the database
  it is about to use, and still fails when that database is absent.
  *test: TestStartAdminLocal_StillChecksTheTargetDatabase*

## Guardrails

- G-1: `bash -n` clean; the script keeps its coloured `✓`/`✗` register, the
  `[n/6]` steps, and `--port`, `--no-migrate`, `--check-only`, `--help`.
- G-2: **Do not create, drop, seed or migrate any database**, in the script or
  in the tests. `nonogram_dev` and `nonogram_test` are the owner's;
  `nonogram_test` sits at revision 013 with empty tables; `nonogram_poc`
  deliberately does not exist.
- G-3: Do not change the launch target. `--app nonogram.admin.app` is CARD-139's
  fix for a live 500, and CARD-139's editable-install check stays.
- G-4: No Python under `src/`. In particular **do not change
  `normalized_url`** — the panel's handling of driver-qualified URLs is correct
  and is CARD-148's whole point; it is the script that must learn.
- G-5: All tests keep executing with no `skipif`, `importorskip` or marker, and
  none may require PostgreSQL to be running. CARD-150's suite achieved this with
  logging stubs on `PATH`; follow it.

## Architecture context

- **FR:** — (untraced: operational defect, follows CARD-150's review)
- **ADR:** ADR-0006/R1 (the dependency baseline — no shell-testing library)
- **CON:** CON-015 (the panel binds loopback only)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

**No FR on purpose**, like CARD-150 and CARD-147. Do not cite one to look
traced — CARD-144's review found that defect and it cost a finding.

## Worktree notes

- [Origin] CARD-150's cycle-1 review, F-006, left open by the owner's decision
  to merge with the Minors on the backlog. Cut as its own card on 2026-10-01 at
  the owner's request.
- [The review's mechanism was half right, and this card states the measured one]
  F-006 attributed both symptoms to `DB_NAME` being string-sliced. The slicing
  is fine — it extracts `nonogram_dev` from a driver-qualified URL correctly.
  The real mechanism is what is handed to `psql`: the whole URL, which `psql`
  treats as a database name when it cannot parse it. Worth knowing before
  reaching for the slicing.
- [Why the driver case is the one that will actually bite] `postgresql+psycopg2://`
  is not an exotic spelling — it is what `normalized_url` builds on every
  connection the panel makes, and what CARD-148 was written to guarantee. An
  owner who copies the URL the panel uses gets told it is unreachable.
