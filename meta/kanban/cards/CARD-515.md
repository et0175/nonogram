# CARD-515: A DATABASE_URL with surrounding whitespace connects to the database it names

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/515-database-url-whitespace
**Worktree:** ../PythonProject4-card-515
**Source:** roadmap wave 9, cut 2026-11-21 on the owner's "yes, start wave 9", which accepted the recommendation to trim rather than refuse. IDEA-224 (CARD-509 review F-001).
**Idea:** IDEA-224
**Wave:** 88
**Created wave:** 88
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/db/session.py, tests/conftest.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-21T20:01Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-509's review (F-001): `make_url` keeps a trailing space or newline in the database name ("db "), so a URL pasted with one connects to a database that does not exist and nothing says why. The "with trailing whitespace" wording appears only when the URL also fails to parse. Owner's ruling 2026-11-21: trim surrounding whitespace, do not refuse.

## What to implement

Re-verify the premise on main first (a URL ending in a space and one ending in a newline: what database name does `normalized_url` give?). Then trim leading and trailing whitespace from the URL text once, where every reader of DATABASE_URL goes through it. Find every reader of the variable by `ast` (src/, migrations/, scripts/, tests/conftest.py) and make sure each one sees the same trimmed value: in particular the test suite's per-worktree `*_test` name resolution and its production guard must agree with what the app connects to, or a padded URL could pass one check and connect elsewhere.

## Acceptance criteria

* **AC-1**: a URL ending in a space, a newline, or both, and one starting with a space, all give the same database name as the clean URL (control: main's code reds it, naming "db " or similar).
* **AC-2**: every DATABASE_URL reader found by `ast` sees the trimmed value; list them in the notes with how each is reached.
* **AC-3**: whitespace inside the URL (not at its ends) is left alone; the password is never echoed in any message (EC-1 unchanged).
* **AC-4**: net test count at most +1; change existing tests in preference to adding. Report it.

## Guardrails

* **G-1**: never connect to the production database; armed runs use the worktree's own `*_test` database on localhost.
* **G-2**: no other change to what a clean URL connects to.

## Worktree notes

**Premise, re-verified on main's code before any change** (recorded run of `normalized_url`): `…/db ` gave database `'db '`, `…/db\n` gave `'db\n'`, `…/db \n` gave `'db \n'`, and `' postgresql://…/db'` raised "not a URL SQLAlchemy can parse (scheme: 'postgresql, with leading whitespace')". Confirmed.

**What changed.**
- `nonogram.db.session.trimmed_url(value)`: new. It is the one trim rule. `None` stays `None`. Otherwise it returns `value.strip()`, or `None` when nothing is left, so a whitespace-only value counts as unset.
- `normalized_url`: strips a `str` argument before `_scheme_of` and `make_url`. Callers that pass raw text are covered too.
- `_scheme_of`: CARD-509's "with … whitespace" branch is removed, because `normalized_url` no longer hands it padded text. The docstring says so.
- `_engine_options`: strips before reading the scheme, so a leading space no longer drops the connect deadline.
- `_init_engine`: reads through `trimmed_url`. The trimmed text is the engine cache key.

**AC-2: every DATABASE_URL reader found by `ast`** (Constant `"DATABASE_URL"` under a read call or subscript, in src/, migrations/, scripts/, tests/conftest.py and the helpers it imports: database_guard, db_name, hang_guard, full_suite_lock, helpers/):
- `session._init_engine`: changed, reads through `trimmed_url`.
- `nonogram.db.__getattr__('DATABASE_URL')`: changed, returns `trimmed_url(...)`.
- `migrations/env.py` `run_migrations_online` / `run_migrations_offline`: changed to `trimmed_url(os.getenv(...))`. A blank value now falls back to alembic.ini as an unset one does. Both already reached `normalized_url`, which trims.
- `admin.app.create_app` and `admin.book_membership._services`: changed to `(os.getenv(...) or '').strip()`. They only decide set or unset, and the URL they then connect with goes through `_init_engine`. The strip is written inline because importing `session.py` needs SQLAlchemy, which an in-memory install (no `db` extra) lacks.
- `tests/conftest.py` `pytest_runtest_setup` and `_armed_database_plan`: changed to `trimmed_url(...)`, imported locally. (The module-level name `db_session` is the fixture, not the module.) A padded URL that names the resolved `*_test` database is now that database to the resolution and the refusal, as it is to the engine.
- `tests/database_guard.py` `current_verdict` and `report_line`: changed to `trimmed_url(...)`. Its `_database_name` already stripped the last path segment, so the change only affects a whitespace-only value: refused as `''` before, unset now.
- Not readers: `conftest.db_session` (setenv), `conftest._rebuild_public_schema` (passes `test_db_url` into a subprocess env), `tests/helpers/admin_scripts.run_script` (env store).
- scripts/*.py: no reader. Out of scope and unchanged: the shell scripts that read the variable (setup_admin_local.sh, start_admin_local.sh, run_admin_tests.sh, railway-deploy.sh, diagnose_postgres.sh), and `TEST_DATABASE_URL`, which `db_name.resolve_test_database_url` still returns verbatim.
- The reads stay direct `os.getenv`/`environ.get` calls wrapped in `trimmed_url`, so CARD-349's `ast` derivation (`_scopes_reading_the_variable`, `_production_readers`) still finds them.

**Tests changed (none added; one parametrised in two).**
- `test_every_part_but_the_driver_survives`: each corpus URL is also run padded (trailing space, `\n`, ` \n`, leading space). AC-1.
- `test_a_sqlite_url_is_returned_exactly_as_given`: each URL is also run padded. `with space.db` keeps its inner space. AC-3.
- `test_the_connect_deadline_still_reaches_a_normalised_url`: adds a `' postgresql'` row.
- `test_scheme_of_returns_a_grammatical_scheme_or_a_placeholder`: CARD-509's padded loop is removed (it tested the removed branch).
- `test_PropertyTest_DbUrl_MalformedUrlErrorNeverEchoesASecret`: each corpus URL is also run padded `"\t " + raw + " \n"`. It must fail with exactly the bare URL's message and no secret in the traceback, or parse to the same URL. CARD-509's literal now parses to database `db` with the password intact. AC-3 / EC-1.
- `test_the_online_branch_names_the_driver_and_keeps_the_password`: `DATABASE_URL` is padded and the migration config still names `nono`.
- `test_no_database_driver_is_in_sys_modules`: parametrised `absent` / `blank` (`" \n"`). This is the +1.
- `test_the_command_refuses_when_there_is_no_database`: a blank value is refused the same way.
- `test_the_prepare_branch_is_reachable_only_past_the_refusal`: a padded own URL gives `(trimmed url, prepare)`.
- `test_the_bare_variable_gate_and_the_resolution_gate_differ`: a blank value takes the bare gate.
- `test_no_database_at_all_is_the_ordinary_case`: with a blank value, `current_verdict()` equals the unset verdict and `report_line()` is `None`.

**Controls** (each mechanism reverted, the named tests run unarmed, the file restored; `git diff --stat` afterwards showed only the card's own changes):
- C1, `normalized_url` strip off: 3 red.
  - `test_every_part_but_the_driver_survives`: `{'sslmode': 'require '} != {'sslmode': 'require'}`. The padding lands in the last component, which is the database name when there is no query.
  - `test_a_sqlite_url_is_returned_exactly_as_given`: `RuntimeError … (scheme: '<malformed scheme>')`.
  - The property test: `'(scheme: 'POSTGRESQL')' != '(scheme: '<malformed scheme>')'`.
- C2, `_armed_database_plan` trim off: `test_the_prepare_branch…` red, `(' postgresql…_test \n', 'elsewhere') == ('postgresql…_test', 'prepare')`.
- C3, `pytest_runtest_setup` trim off: `test_the_bare_variable_gate…` red, `'…the per-worktree database said so' == '…DATABASE_URL is not set'`.
- C4, `current_verdict` trim off: `test_no_database_at_all…` red, `(False, 'Refu…') == (True, 'DATAB…')`.
- C5, `create_app` strip off: `test_no_database_driver_is_in_sys_modules[blank]` red, `AssertionError: not in-memory mode`.
- C6, `_services` strip off: `test_the_command_refuses…` red, `RuntimeError: DATABASE_URL not set. Database persistence disabled.` (not the SystemExit).
- C7, `_engine_options` strip off: `test_the_connect_deadline…` red, `KeyError: 'connect_args'`.
- C8, `trimmed_url` reduced to identity: 5 red across test_card_349 and test_card_109, the C2/C3/C4 lines plus the two subprocess guard tests that run the C4 test node.
- Not covered by any control: the `trimmed_url` call in `_init_engine` and the two in `migrations/env.py`. `normalized_url` trims behind them, so they change behaviour only for a whitespace-only value (`_init_engine`: "not set" instead of a parse error; env.py: alembic.ini fallback). No test pins that.

**Gate.** Files: test_db_url_driver, test_card_349_cold_database, test_card_109_database_guard, test_card_100_book_membership, and neighbours test_db_engine_lifecycle, test_db_isolation, test_db_connect_timeout, test_card_156_db_fixture, test_admin_binding, test_kill_matrix, test_db_e2e_smoke, test_card_102_foreign_keys_are_enforced, test_card_103_book_id_constraint, test_card_107_orphaned_book_ids, test_setup_admin_local, test_run_admin_tests, test_impact_set, test_collected_names.
- Unarmed (`-o addopts= -rfs`): 668 passed, 0 failed, 25 skipped, all "Database not reachable: DATABASE_URL is not set".
- Armed at this worktree's `nonogram_pythonproject4_card_515_2aef8ca9ee5c_test` on localhost: 693 passed, 0 failed, 0 skipped.
- Armed with that URL padded (`" <url> \n"`) over the four changed files: 160 passed, 0 skipped. The suite resolved, prepared and used the padded URL as its own database.

**Net test count:** 10690 before, 10691 after (+1, within AC-4).
