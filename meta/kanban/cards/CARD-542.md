# CARD-542: The test-database rebuild's ownership and grants note, verified against today's code

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/542-schema-grants
**Worktree:** —
**Source:** roadmap wave 18, cut 2026-11-24 on the owner's pick of "a small Wave 18" from the backlog's remaining no-decision items. IDEA-033.
**Idea:** IDEA-033
**Wave:** 97
**Created wave:** 97
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/README.md, src/nonogram/db/session.py (only if a finding cannot be closed in the README)
**UI surface:** —
**Review score:** 10.0 (cycle 3/3 - CERTIFIED)
**Started:** 2026-11-24T11:23Z
**Closed:** 2026-11-24T16:30Z
**Actual:** 1c — ratio 1/1 = 1.0
**Merge commit:** bfde900c
**Blocked by:** —

## Why this card exists

CARD-156's review (F-007) noted that `DROP SCHEMA public CASCADE` needs the test role to own `public`, and that the recreated schema loses its default grants; it was documented in `tests/README.md`, not handled in code. Re-checked on main at the cut: the rebuild now lives in `src/nonogram/db/session.py` (its docstring describes the drop and `alembic upgrade head`), and `tests/README.md` says the armed run needs a "`public` schema your role owns". Whether the grants half is still true, still documented, or matters to any test is not known.

## What to implement

1. Verify first, on your worktree's OWN `*_test` database on localhost only (never `nonogram_poc`, never production; the suite resolves the name per worktree). Record: who owns `public` before and after one armed rebuild, and the schema's grants (`\dn+ public`) before and after.
2. If the README already says what the run shows, record moot. If it is missing or wrong, correct `tests/README.md`.
3. Do not change `tests/conftest.py`, `tests/database_guard.py` or any guard: they are protected, and widening a guard is out of scope. Change `session.py` only if a lost grant breaks something a test or the owner's local run needs; otherwise stop and report.

## Acceptance criteria

- AC-1: each in-scope item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a computed figure), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and a fix to a test or to code has one control that fails when the fix is reverted. A comment-only fix records the computed figure instead.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes

### Verification (2026-11-24, PostgreSQL 15.19 on localhost, role `postgres`, superuser)

Premise correction: the rebuild lives in `tests/conftest.py`'s `_rebuild_public_schema` (`DROP SCHEMA public CASCADE`, `CREATE SCHEMA public`, alembic subprocess); `src/nonogram/db/session.py` holds only `reset_engine`, whose docstring describes it. CARD-156 F-007 (cycle 2 review, still `status: open`) names both halves: ownership needed, default grants lost.

Database: `nonogram_pythonproject4_card_542_9abdf51bcc36_test` (`db_name.resolve_test_database_url({}, REPO_ROOT)`, checked equal to the armed URL). It did not exist; created through the suite's own `_ensure_test_database` (no rebuild), so the pristine state could be probed.

Before (fresh database), `\dn+ public`:

    public | pg_database_owner | pg_database_owner=UC/pg_database_owner+ | standard public schema
           |                   | =U/pg_database_owner
    has_schema_privilege('public','public','USAGE') = t

One armed rebuild: `DATABASE_URL=<that URL> pytest -o addopts= -rfs -k test_no_server_side_prepared_statement_is_ever_created tests/test_db_engine_lifecycle.py` -> `1 passed, 19 deselected`.

After, `\dn+ public`:

    public | postgres |  |
    has_schema_privilege('public','public','USAGE') = f   (8 tables in public)

Ownership half, probed on the after-state in a rolled-back transaction: `SET LOCAL ROLE pg_read_all_data` (non-superuser, not owner); `DROP SCHEMA public CASCADE` -> `ERROR:  must be owner of schema public`.

Verdicts:
- Ownership requirement: LIVE as a fact, already documented (troubleshooting bullet under "Refusing to set up the test database"), but filed under a refusal that is about the name guard, not the error a non-owner sees. Added a troubleshooting bullet for `must be owner of schema public`.
- Lost grants: LIVE and undocumented (tests/README.md said nothing about grants). Documented under the `db_session` fixture with the before/after above. Not a code defect: the armed run passed after the rebuild, and fixtures and app connect through the one URL that rebuilt the schema; only a second non-superuser role on the same database is affected. `src/nonogram/db/session.py` unchanged; `tests/conftest.py` untouched (protected).
- AC-2: comment-only fix, the computed figures are the psql outputs above.

Gate (unarmed, `-o addopts= -rfs`): tests/test_kill_matrix.py, tests/test_full_suite_lock.py, tests/test_cli.py, tests/test_guard_integrity.py (the tests that read or scan tests/README.md, found by an `ast` scan for README literals) -> 449 passed, 0 skipped.

Net test count: 10714 before, 10714 after (`--collect-only -q -o addopts= tests/`), net 0.

[Review 1/3] Score: 9.5, certified, no high or medium findings. Before connecting, I checked that `db_name.resolve_test_database_url({}, REPO_ROOT)` resolves to `nonogram_pythonproject4_card_542_9abdf51bcc36_test` on localhost; I ran only read-only catalog queries against it, on PostgreSQL 15.19. They match the notes' after-state: `\dn+ public` shows owner `postgres` and an empty access list, `nspacl` is null, `has_schema_privilege('public','public','USAGE')` is false, and there are 8 tables in `public`. No armed run (the after-state was already on disk). The before-state (`pg_database_owner` with `=U/pg_database_owner`) was not reproduced, but matches PostgreSQL 15's documented default for `public`. `_rebuild_public_schema` in `tests/conftest.py` runs `DROP SCHEMA public CASCADE` and `CREATE SCHEMA public` with no GRANT, then alembic through the same URL. The conclusion that `session.py` needs no change holds: the fixtures, the alembic subprocess and the app all connect through the one URL that rebuilt the schema; no tracked file issues GRANT, SET ROLE, ALTER DEFAULT PRIVILEGES or CREATE ROLE, and `pg_default_acl` is empty. Both README edits are in the right places. Figures: README-reading set (`test_kill_matrix`, `test_full_suite_lock`, `test_cli`, `test_guard_integrity`) 449 passed, 0 skipped (a first run gave 9 failed / 440 passed because CARD-541's gate took the full-suite lock mid-run; re-run after it cleared); `test_kanban_review_record` and `test_check_ref_resolution` 97 passed; 10714 collected, net 0. F-001 (low): the troubleshooting bullet says to connect "as the role `\dn+ public` names as owner"; before any rebuild that is `pg_database_owner`, which cannot log in; the role that can drop `public` there is the database's owner. F-002 (low): "lose `USAGE` on `public`, and with it its tables" overstates: the 8 recreated tables grant SELECT to no other role, so the rebuild costs a second role only the schema's USAGE. F-003 (info): the implementer's three read-only queries on the `postgres` maintenance database do not matter for the card; no figure depends on them, and `_ensure_test_database` connects there on every armed run anyway.

**Fix round 1 (orchestrator).** F-001: the troubleshooting bullet now says to connect as a superuser or the database's owner (`\l` names it), that the `\dn+ public` owner works after a rebuild, and that before one it reads `pg_database_owner`, which is not a login role; the `db_session` entry says the database's owner qualifies on a never-rebuilt database. F-002: "and with it its tables" replaced by "It had no table privileges to lose: the migration grants none to any other role." README prose only; the database-owner statement follows PostgreSQL 15's documented `pg_database_owner` membership and was not run here (both local roles are superusers).

[Review 2/3] Score: 9.5, certified, no high or medium findings. Before connecting, I checked that `db_name.resolve_test_database_url({}, REPO_ROOT)` resolves to `nonogram_pythonproject4_card_542_9abdf51bcc36_test` on localhost, and ran only read-only catalog queries against it. Every sentence of fix round 1 was checked against the code, the PostgreSQL 15 docs and that catalog. The `public` schema is owned by `postgres` with a null `nspacl`. All 22 relations in `public` (8 tables, 14 indexes) are owned by `postgres` with a null `relacl`. `pg_database_owner` has `rolcanlogin = f` and `rolinherit = t`. No migration issues a GRANT; the only `op.execute` calls, in 013 and 017, are UPDATE backfills. So "It had no table privileges to lose: the migration grants none to any other role" is true, and the troubleshooting bullet is right that `pg_database_owner` is not a login role. The unrun claim that the database's owner can drop `public` follows from the PostgreSQL 15 docs (Predefined Roles, Privileges, DROP SCHEMA), and its PostgreSQL 15 scope is hedge enough. Figures: README-reading set (`test_kill_matrix`, `test_full_suite_lock`, `test_cli`, `test_guard_integrity`) 449 passed, 0 skipped; `test_kanban_review_record` and `test_check_ref_resolution` 97 passed; 10714 collected, net 0. F-001 (low): the troubleshooting bullet's "works too" implies the database's owner can still drop `public` after a rebuild, but `CREATE SCHEMA public` gives the schema to the connecting role, so that holds only when the database's owner did the rebuild. F-002 (low): "owned by that role" in the `db_session` entry now points at the database's owner; it should say the connecting role.

**Fix round 2 (orchestrator).** F-002: the `db_session` entry says the recreated schema is owned by "the connecting role". F-001: the troubleshooting bullet now separates the two states, in the reviewer's suggested order: before any rebuild, connect as the database's owner (`\l` names it; `\dn+ public` says `pg_database_owner`, not a login role); after one, as the role `\dn+ public` names, because the rebuild gives `public` to whichever role ran it; a superuser works either way. README prose only.

[Review 3/3] Score: 10.0, certified, no findings above info. I read both reworded README passages in full against `_rebuild_public_schema` in `tests/conftest.py` and the catalog facts measured in cycles 1 and 2. The `db_session` entry's "owned by the connecting role" matches `CREATE SCHEMA public` with no AUTHORIZATION clause (owner `postgres`, the URL's role). The `must be owner of schema public` bullet now separates three cases correctly: the database's owner before any rebuild (`\dn+ public` shows the NOLOGIN `pg_database_owner`), the role `\dn+ public` names after one, and a superuser either way. The `[Review 2/3]` paragraph matches the cycle 2 report and the Fix round 2 note matches commit 386429a6. Figures: one run of `test_kill_matrix`, `test_full_suite_lock`, `test_cli`, `test_guard_integrity` and `test_kanban_review_record` gave 520 passed, 0 skipped; the four README-reading files gave 449 in cycles 1 and 2 and no `.py` file has changed since. 10714 collected, net 0. F-001 (info): the bullet's `pg_database_owner` statement is PostgreSQL 15+ behaviour and does not repeat the version scope the `db_session` entry gives; optional, not taken.

**Merge gate (orchestrator).** `make test-gate BASE=main` on `f39195a9` (main 084230e0 merged in) answered SELECTION: 2 failed / 4857 passed / 20 skipped (unarmed) / 8 deselected / 1 xfailed in 21 min 31 s, then the marked run 8 passed. 5 marked tests are owed at the wave close. Both reds are `tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant` (`[a-network-call-is-added]`, `[probe-auto-commit-decided-by-filled-count]`), each "sweep aborted: TimeoutError: Locator.click: Timeout 10000ms exceeded" on the real files: the same browser timeout under load recorded at CARD-535. This card changes only `tests/README.md` and the card. Re-run alone, the whole test (27 parameters) twice: 27 passed, 27 passed. Recorded as a flake; the wave close runs the bare full suite.
