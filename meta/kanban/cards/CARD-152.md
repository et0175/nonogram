# CARD-152: The setup and test-runner scripts check the database they will use

**Status:** ready
**Priority:** P2
**Category:** bug
**Estimate:** 0.5d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** CARD-150 cycle-1 review (2026-10-01), backlog sweep 2026-10-02; defects re-read on main beaecdd before cutting this card
**Idea:** —
**Wave:** 28
**Depends on:** CARD-151
**Touches:** scripts/setup_admin_local.sh, scripts/run_admin_tests.sh, scripts/README.md, tests/test_setup_admin_local.py (new), tests/test_run_admin_tests.py (new)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

CARD-150 fixed three defects in `scripts/start_admin_local.sh`. Its two sibling
scripts still have them, verbatim (re-read on main beaecdd, 2026-10-02):

| Defect | `setup_admin_local.sh` | `run_admin_tests.sh` |
|---|---|---|
| The Homebrew branch checks the **default** database with a bare `psql -c "SELECT 1"`, not the one the script will use | :40 | — |
| `DATABASE_URL` is hardcoded to `…/nonogram_poc` and **overwrites** whatever the caller exported | :64 | :24 |
| A failed `alembic upgrade head` prints a yellow "⚠ Migrations may have issues", discards alembic's output to `/dev/null`, and the script reports "Setup complete!" | :70-74 | — |

`nonogram_poc` deliberately does not exist on the owner's machine, so out of the
box `setup_admin_local.sh` checks a database it does not use, sets a URL that
points nowhere, swallows the migration failure and says it worked.
`scripts/README.md:13` currently says these two scripts "do not yet honour" an
exported `DATABASE_URL`. That caveat should go once this card lands.

## What to do

1. Give both scripts the same behaviour `start_admin_local.sh` has after CARD-150
   and CARD-151: an exported `DATABASE_URL` wins, the script says which source it
   used, the reachability check targets that database (host, port, credentials
   and name), and an empty database name is refused.
   **Reuse CARD-151's approach to turning the URL into something `psql`
   understands**, so all three scripts handle `postgresql+psycopg2://` the same
   way. If the cleanest route is a small shared shell helper sourced by all
   three, that's fine. Don't copy the logic three times if a helper is simpler.
2. `setup_admin_local.sh`: a failed migration stops the script with alembic's own
   message, as in CARD-150.
3. Update `scripts/README.md` so it no longer carries the "do not yet honour"
   caveat, and make sure every claim it makes about the three scripts is true.

## Acceptance criteria

- **AC-1:** With `DATABASE_URL` exported, neither script overwrites it, and each
  says it took the URL from the environment.
  *test: TestSiblingScripts_ExportedDatabaseUrlWins*
- **AC-2:** `setup_admin_local.sh` refuses when the database the URL names is
  unreachable, even when the server's default database answers.
  *test: TestSetupAdminLocal_ChecksTheTargetDatabase*
- **AC-3:** A failing `alembic upgrade head` makes `setup_admin_local.sh` exit
  non-zero, quote alembic's message and never print "Setup complete!".
  *test: TestSetupAdminLocal_StopsOnAFailedMigration*

## Guardrails

- G-1: `bash -n` clean. Keep each script's existing arguments and coloured output.
- G-2: **Do not create, drop, seed or migrate any real database**, in the scripts
  or in the tests. Use logging stubs on `PATH` the way CARD-150's suite does.
- G-3: No Python under `src/`, and `normalized_url` stays untouched (CARD-148).
- G-4: No test may need PostgreSQL to be running, and none may `skipif` or
  `importorskip`.

## Architecture context

- **FR:** — (untraced: operational defect, same as CARD-150 and CARD-151)
- **ADR:** ADR-0006/R1 (no shell-testing library)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] CARD-150's review found these as out-of-scope siblings; the owner asked
  for them as one card on 2026-10-02.
- [Order] Runs after CARD-151, so the URL handling it reuses is settled first.
