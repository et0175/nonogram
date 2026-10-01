# CARD-150: The local launcher refuses a database it cannot use, instead of starting anyway

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** owner, 2026-10-01 ("нагадай ще раз, як запустити локально" — the answer turned out to be "not with this script")
**Idea:** —
**Wave:** 28
**Depends on:** —
**Touches:** scripts/start_admin_local.sh, scripts/README.md, tests/test_start_admin_local.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`scripts/start_admin_local.sh` starts the panel against a database that does not
exist, reports success along the way, and leaves the owner on a broken panel.
Measured on this machine 2026-10-01, not inferred:

1. **The Homebrew branch of the PostgreSQL check does not check the database.**
   Lines 75–80: the two Docker branches run
   `psql -U postgres -d nonogram_poc -c "SELECT 1"` — they verify `nonogram_poc`
   is reachable. The Homebrew branch is a bare `psql -c "SELECT 1"`, which
   connects to the *default* database (`$USER`) and says nothing about
   `nonogram_poc`. It prints `✓ PostgreSQL is running (Homebrew)` and continues.
2. **The database it then uses is hardcoded** (line 125):
   `export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"`.
   It overwrites whatever the caller exported, so there is no way to point the
   script at another database without editing it.
3. **A failed migration is swallowed** (lines 134–137): `alembic upgrade head`
   runs with `> /dev/null 2>&1`, and on failure prints
   `⚠ Migrations may have issues (but continuing)` and carries on. The error
   text is discarded, so the one message that would explain the problem is the
   one thing thrown away.

Together: on a machine without `nonogram_poc` — which is this machine, where
only `nonogram_dev` and `nonogram_test` exist — the script prints two green
ticks and one yellow warning, then serves a panel whose every database read
fails. The owner asked how to run locally and the honest answer was "not with
this script".

**This is not a request to create the database.** Which database the owner
wants is their call; the script's job is to be honest about the one it was
given.

1. **Check the database the script will actually use**, on every branch, not
   only the Docker ones. The Homebrew branch must make the same assertion the
   Docker branches make.
2. **Respect a `DATABASE_URL` the caller already exported**, and fall back to
   the current value when there is none. A hardcoded export that overwrites the
   caller is what makes the script unusable rather than merely opinionated.
3. **Refuse on a failed migration** rather than continuing, and **print what
   alembic said**. If there is a reason to continue, it must be an explicit
   flag the owner passes, not the default.
4. **Correct `scripts/README.md`**, which states `nonogram_poc` as a
   prerequisite (line 9) and repeats the hardcoded URL at lines 37 and 127. If
   the script learns to respect `DATABASE_URL`, the README must say so.

Out of scope: creating or seeding any database; changing which database the
project uses by default; the Docker and docker-compose paths beyond making
their check and the Homebrew check agree; anything about the panel itself.

## Acceptance criteria

- **AC-1:** Run on a machine where the target database does not exist, the
  script exits non-zero naming that database, before starting the panel.
  *test: TestStartAdminLocal_RefusesAMissingDatabase*
- **AC-2:** With `DATABASE_URL` already exported, the script uses it and says
  so; with none exported, it uses the project default.
  *test: TestStartAdminLocal_RespectsAnExportedDatabaseUrl*
- **AC-3:** When `alembic upgrade head` fails, the script exits non-zero and
  alembic's own message appears in the output.
  *test: TestStartAdminLocal_RefusesAndReportsAFailedMigration*
- **AC-4:** `scripts/README.md` describes what the script actually does — the
  database it defaults to, that an exported `DATABASE_URL` wins, and that a
  missing database or failed migration stops it.
  *test: TestStartAdminLocal_ReadmeMatchesTheScript*

## Guardrails

- G-1: `bash -n` clean, and the script keeps its existing shape — the coloured
  `✓`/`✗` register, the numbered `[n/6]` steps, `--port`, `--no-migrate`,
  `--help`. This is a correctness fix, not a rewrite.
- G-2: Do not create, drop, seed or migrate any database as part of the script's
  normal path, and do not do so while testing this card. `nonogram_dev`,
  `nonogram_test` and `nonogram_poc` are the owner's.
- G-3: Do not change the launch target. `--app nonogram.admin.app` is CARD-139's
  fix for a live 500 and the `src.`-prefixed form must not come back; the
  editable-install check added in that card stays.
- G-4: No Python under `src/` changes. This card is a shell script, a README and
  its test.

## Architecture context

- **FR:** — (untraced: operational defect, owner intake 2026-10-01)
- **CON:** CON-015 (the panel binds loopback only — the script must not widen it)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

**No FR on purpose.** Like CARD-144's frame and CARD-147's ink mode, this is
owner intake the architect station has not formalised. Do not cite an existing
FR to make it look traced — CARD-144's review found exactly that defect and it
cost a finding.

## Worktree notes

- [Origin] The owner asked how to run the panel locally on 2026-10-01. Working
  out the honest answer surfaced all three defects above. The script was last
  touched by CARD-139, which fixed its launch target and added the
  editable-install check — that card's SCOPE+ was deliberately narrow and did
  not look at the database path.
- [Why it survived] Nothing tests this script. CARD-139's review noted the file
  had no test and treated that as out of scope, correctly. The failure is also
  invisible on a machine that happens to have `nonogram_poc`: the owner's live
  panel does, which is why it has worked until now.
- [The class of defect] This is the third instance this week of a stated thing
  that was true once: CARD-139's README documented the launch spelling it had
  just removed, CARD-143's Ukrainian guide said the order could only be changed
  with buttons, and here the script's own green tick asserts a database it never
  checked. Worth noticing that all three were *descriptions*, and all three
  passed every test the project had.
