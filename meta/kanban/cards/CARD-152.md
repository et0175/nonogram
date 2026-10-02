# CARD-152: The setup and test-runner scripts check the database they will use

**Status:** done
**Priority:** P2
**Category:** bug
**Estimate:** 0.5d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/152-sibling-scripts-check-database
**Worktree:** —
**Source:** CARD-150 cycle-1 review (2026-10-01), backlog sweep 2026-10-02; defects re-read on main beaecdd before cutting this card
**Idea:** —
**Wave:** 28
**Depends on:** CARD-151
**Touches:** scripts/setup_admin_local.sh, scripts/run_admin_tests.sh, scripts/README.md, tests/test_setup_admin_local.py (new), tests/test_run_admin_tests.py (new)
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-10-02T12:19:53Z
**Closed:** 2026-10-02T13:49:47Z
**Actual:** 0.2d
**Merge commit:** 02ea77a
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

## System contract

_Assembled fresh 2026-10-02 by system_rules.py --card CARD-152 (card_scope: touches)._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy; no third-party package joins without revising the ADR. (check: test TestDependencyBaseline_IsExactlyPillowAndNumpy)
- CON-005 — The uniqueness check must never produce a false positive. (check: test PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds 127.0.0.1 only. (check: test TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI refuses cross-site / foreign-authority requests. (check: test PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. (check: test PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A request whose aspect ratio differs from the source's ink box by more than 2x is refused. (check: test PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

## Architecture context

- **FR:** — (untraced: operational defect, same as CARD-150 and CARD-151)
- **ADR:** ADR-0006/R1 (no shell-testing library)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] CARD-150's review found these as out-of-scope siblings; the owner asked
  for them as one card on 2026-10-02.
- [Order] Runs after CARD-151, so the URL handling it reuses is settled first.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +ADR-0006/R1, CON-005, CON-009, CON-010, CON-011, CON-012 / −none (the card had no section)
- [Impl 2026-10-02] Copy, not a shared helper: `tests/test_start_admin_local.py` copies ONLY `start_admin_local.sh` into its throwaway root, so a sourced helper would not exist there and that suite (which must stay unmodified) would break. The resolution block (exported wins / DATABASE_URL_SOURCE / DB_NAME from path + last `?dbname=` incl. empty / `+driver` strip into PSQL_URL) is copied byte-identical into both siblings, with a comment saying why and to keep the three copies identical. No SCOPE+: `start_admin_local.sh` and its tests are untouched.
- [Impl] setup_admin_local.sh: resolution before the banner; the check (not-a-URL refusal, names-no-database refusal, Docker/Compose with `-d "$DB_NAME"`, Homebrew `psql "$PSQL_URL"`) sits where the old one was; env step does `export DATABASE_URL` and prints `DATABASE_URL=... (<source>)`; a failed `alembic upgrade head` prints ✗, quotes alembic's output indented, exits 1 and never reaches "Setup complete!". No arguments before, none added.
- [Decision] run_admin_tests.sh now CHECKS reachability and refuses (same check and messages as the other two), placed after argument parsing so `--help` / an unknown option answer without a database, and before pytest. Why: the card asks for the same behaviour in both scripts, and without a check an unreachable DB is worse than a failure here — conftest skips DB-backed tests, so the run came back green having tested nothing DB-related. It prints `DATABASE_URL=... (<source>)` under "Checking the database...". `--help` gained an Environment section naming the default; all args (all/wave1/wave2/e2e/unit/smoke/integration, -v/--verbose, --coverage, --help, unknown-option exit 1) unchanged and pinned.
- [Observed, not fixed] With the project default `nonogram_poc`, `run_admin_tests.sh` passes its own check but pytest then stops at start-up: `tests/database_guard.py` (CARD-109) refuses a DB whose name lacks "test" unless NONOGRAM_ALLOW_FOREIGN_DATABASE=1. Pre-existing; README now says so and its workflow examples export a `nonogram_test` URL. Changing the runner's default is a product decision — candidate follow-up card.
- [Tests] Shared harness `tests/helpers/admin_scripts.py` (new): imports CARD-151's psql model, docker stub, `_all_pairs`, `_plain` from `tests/test_start_admin_local.py` (one model judges all three scripts; nothing there modified); own alembic/pytest stubs that also log the DATABASE_URL they were handed. Two contract mixins (ExportedDatabaseUrlContract, DatabaseCheckContract) applied to both scripts. AC-1: `TestSiblingScripts_ExportedDatabaseUrlWins` (in BOTH tests/test_setup_admin_local.py and tests/test_run_admin_tests.py). AC-2: `TestSetupAdminLocal_ChecksTheTargetDatabase` (+ same contract as `TestRunAdminTests_ChecksTheTargetDatabase`). AC-3: `TestSetupAdminLocal_StopsOnAFailedMigration`. Plus `TestRunAdminTests_KeepsItsArguments`, harness guards, README caveat check. Branches pinned per script: exported vs default source, +driver strip (3 drivers), path name, `?dbname=` override, query-only name, EMPTY `?dbname=` with path (nonogram_dev absent, `someone` present → refused, no psql), repeated `?dbname=` (last wins), trailing slash / no path → refused with no psql/docker, no `://` → "not a URL", host/port/credentials/query carried, target absent while default answers → refused, Docker branches carry `-d <db>`, plus a pairwise corpus (≥20 cases asserted) per script.
- [Mutants] Hand mutation check (copy, mutate, run file with -x, restore with cp + filecmp byte-exact): 14 common mutants × 2 scripts + 4 setup-only = 32, ALL KILLED — `-n`→`-z` on the exported test; no +driver strip; `[^&]*`→`[^&]+`; drop `.*` (first dbname wins); bare `psql -c`; not-a-URL test disabled; empty-name refusal disabled; Docker and Compose `-d nonogram_poc`; `export DATABASE_URL="$DEFAULT_DATABASE_URL"`; query left in name; query dropped from psql URL; path ignored; source labels swapped; migration failure without exit; alembic `2>/dev/null`; quote not indented; green tick on failure. Known unpinned: the runner's (and setup's pre-existing) "psql not found" branch — needs a PATH without the developer's real psql; not worth the brittleness.
- [Results] tests/test_setup_admin_local.py + tests/test_run_admin_tests.py: 40 tests; with tests/test_start_admin_local.py (unmodified, green): 77 passed in ~100s on a loaded machine (the two corpora ~7s each). `bash -n` clean on all three scripts.
- [Scope] scripts/README.md, scripts/run_admin_tests.sh, scripts/setup_admin_local.sh, tests/helpers/admin_scripts.py, tests/test_run_admin_tests.py, tests/test_setup_admin_local.py
- [Build gate] impact underivable (test_scope: full) — full suite
- [Build gate] PASSED (full, 405s; 5607 passed, 7 skipped, 2 failed = the pre-existing baseline red on main dc26103 — tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders; no new failure. Lock: meta/kanban/.full-suite.lock via fcntl.flock, waited 369s)
- [Scope gate 1/3] IN_SCOPE — 6 files: 5 in Touches + 1 new file near scope (tests/helpers/admin_scripts.py, shared harness; SCOPE DISCIPLINE allows new files); comp_spread none (COMP-009 only); poached none; guardrail hits: none (no src/ or pyproject path)
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: 6/6 card rules have a verdict line (1 ✓, 5 ⚠ no_eligible_fact, 0 ✗)
- [Review 1/3] 8f mutation: deferred(cost) — gating findings present; certify on the stable cycle
- [Adversarial] F-001 CONFIRMED — README:15-18 (new in this diff) claims all three checks verify host, port, credentials and name; the Docker/Compose branches run first (setup :104/:106, runner :181/:183) with only -d "$DB_NAME" and -U postgres, so a same-named database in a local container passes a URL aimed at another server. Skeptic: Important defensible (false statement in a named deliverable); Docker-first order inherited from start_admin_local.sh (CARD-151 F-005), only the overstating wording is new.
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Fix 1] Invariant: every README/--help claim about the three admin scripts is true of the code, and the three DATABASE_URL resolution copies stay identical. Changed: F-001 README Prerequisites now says only the local `psql` branch checks host/port/credentials, the Docker/Compose branches check only that a database of that name exists in the container (behaviour unchanged, CARD-151 F-005 still open); Troubleshooting adds wrong host/port/credentials as a cause. F-002 the "After setup" and "Manual Commands" snippets use `${DATABASE_URL:-…nonogram_poc}` so an exported URL survives. F-003 behaviour kept (owner decision); `--help` Environment and README say every test type, unit/smoke included, needs psql and a reachable DB; the psql-not-found branch is now pinned (`without_psql=True` in the harness: PATH = stub dir + links to dirname/python3 only). F-004 `test_the_three_copies_of_the_url_resolution_are_identical` (comment lines dropped). F-005 dismissed (would edit tests/test_start_admin_local.py); dependency named in a comment at the import. Revert checks: drifting one copy's regex, removing the runner's psql guard, and the pre-fix --help each fail their new test. Results: scoped 3 files 79 passed; `bash -n` clean on both touched scripts.
- [Fix 1] pre-gate PASSED — 3/3 named tests green (test_help_answers_without_a_database, test_without_psql_it_stops_before_any_test, test_the_three_copies_of_the_url_resolution_are_identical), bash -n clean; FIXED F-001 (README, doc-only), F-002 (README snippets, doc-only), F-003 (--help + README; psql-not-found branch now pinned), F-004 (structural copies-identical test) · SKIPPED/dismissed F-005 (would edit tests/test_start_admin_local.py, which must stay unmodified; comment added at the import)
- [Fix 1] declarations: 3 updated (README Prerequisites + Troubleshooting; README snippets; run_admin_tests.sh --help Environment + README runner section), 1 confirmed (PSQL_URL comment), 1 none (F-004 structural test)
- [Build gate] PASSED (full, 419s; 5609 passed, 7 skipped, 2 failed = the same pre-existing baseline — test_size_configuration_applied, test_wave3_e2e::test_batch_creation_form_renders; no new failure)
- [Scope gate 2/3] IN_SCOPE — same 6 files (5 in Touches + new tests/helpers/admin_scripts.py); guardrail hits: none
- [Review 2/3] confirmation mode: fix delta since the cycle-1 reviewed state (8e6fb93) = uncommitted fix 1 on scripts/README.md, scripts/run_admin_tests.sh, tests/helpers/admin_scripts.py, tests/test_run_admin_tests.py, tests/test_setup_admin_local.py (setup_admin_local.sh untouched); deferred certification (8f mutation) required this cycle
- [Review 2/3] Score: 9.5 — crit: 0, imp: 0
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h coverage: 6/6 card rules have a verdict line (1 ✓, 5 ⚠, 0 ✗ — all carried(cycle 1, delta-clean): fix delta touches no src/, pyproject or imports)
- [Review 2/3] cycle-1 findings: F-001 ✓ resolved, F-002 ✓ resolved, F-003 ✓ resolved, F-004 ✓ resolved, F-005 dismissal sound
- [Review 2/3] 8f mutation (deferred certification, stable cycle): ran — 10 mutants, 10 killed by behaviour tests alone (M1 setup not-a-URL guard, M2 runner empty-name guard, M3 setup empty ?dbname= [^&]+, M4 runner first-?dbname=-wins, M5 setup no +driver strip, M6 runner psql -d $DB_NAME, M7 setup migration failure no exit, M8 runner psql-not-found guard, M9 runner unreachable no exit, M10 setup -n→-z); files restored, cmp + hashes verified
- [Review 2/3] new: Minor F-006 (unreachable message names 2 causes, README 3 — wording inherited from start_admin_local.sh), out-of-scope F-007 (README Python 3.11+ vs pyproject)
- [Review 2/3] Score: 9.5 ✓ threshold reached + no critical/important
- [8h spot-check] skipped — pool empty: every ✓ holds this cycle is carried(cycle 1, delta-clean) (ADR-0006/R1 was fresh in cycle 1)
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — tests/test_setup_admin_local.py::TestSiblingScripts_ExportedDatabaseUrlWins (3) + tests/test_run_admin_tests.py::TestSiblingScripts_ExportedDatabaseUrlWins (3), both scripts: consumer stub (alembic / pytest) receives the exported URL, stdout "(exported by the caller)", no nonogram_poc, psql connects only to nonogram_dev — PASSED
  AC-2 ✓ demonstrated — tests/test_setup_admin_local.py::TestSetupAdminLocal_ChecksTheTargetDatabase incl. test_an_absent_database_is_refused_while_the_servers_default_answers, test_the_old_bare_check_would_have_passed_here — PASSED
  AC-3 ✓ demonstrated — tests/test_setup_admin_local.py::TestSetupAdminLocal_StopsOnAFailedMigration (4): non-zero exit, alembic stderr quoted indented on stdout, "Setup complete!" absent, silent failure prints "(no output)" and stops — PASSED
  G-1 ✓ demonstrated — bash -n OK both scripts; runner case options unchanged (only --help text added), case $TEST_TYPE identical; setup takes no args before/after; colour definitions kept (runner adds RED)
  G-2 ✓ demonstrated — no createdb/dropdb/CREATE|DROP DATABASE/alembic downgrade|stamp/INSERT/seed in scripts or tests (one docstring hit denying it); psql/docker/docker-compose/alembic/pytest stubbed first on PATH
  G-3 ✓ demonstrated — git diff main...HEAD -- src/ and git diff HEAD -- src/ empty; normalized_url 0 hits in diffs; tests/test_db_url_driver.py green
  G-4 ✓ demonstrated — no skipif/importorskip/pytest.skip/mark/create_engine/sqlalchemy/socket in new test files; -rs no skips; tests/test_start_admin_local.py unmodified vs main and green
  (no Engineering constraints section; 22 AC-named tests passed in 30.5s; 116 passed across the 3 script suites + test_db_url_driver.py in 128.5s)
- [Docs] forge:readme on scripts/, tests/, tests/helpers/ — scripts/README.md is itself a card deliverable, updated and verified by 2 reviews (every claim true); tests/README.md is the legacy Wave-1 page that lists neither helpers/ nor the script suites (same as CARD-151); tests/helpers/ has no README (per-directory READMEs convention is an open owner decision on the backlog) — skipped
- [Commit] success commit: 65656c3 (fix 1, explicit pathspecs + Co-Authored-By) on top of 8e6fb93 (implementation). Branch = 8e6fb93 + 65656c3; worktree clean apart from meta/.
- [Merged] 2026-10-02 — 02ea77a into main (--no-ff). Rebased onto 494cebd cleanly (main had not touched scripts/ or the test files since the branch base) → tip 756f5ed. Merge gate: full suite on the rebased tree under the lock (waited 257s, ran 397s); only the 2 baseline failures. Deferral scan: 0 hits. No trace write-back: untraced card. Out-of-scope items captured to backlog. Owner to confirm: run_admin_tests.sh now requires a reachable database for every test type (unit/smoke included).
