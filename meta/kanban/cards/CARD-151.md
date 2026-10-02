# CARD-151: The launcher's database check understands the URLs the panel accepts

**Status:** done
**Priority:** P2
**Category:** bug
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/151-launcher-database-check-urls
**Worktree:** —
**Source:** CARD-150 cycle-1 review, F-006 (2026-10-01); mechanisms re-measured by the orchestrator before cutting this card
**Idea:** —
**Wave:** 28
**Depends on:** —
**Touches:** scripts/start_admin_local.sh, tests/test_start_admin_local.py
**Review score:** 9.0 (cycle 3/3)
**Started:** 2026-10-02T09:42:31Z
**Closed:** 2026-10-02T12:18:02Z
**Actual:** 0.3d
**Merge commit:** 4fc5821
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

## System contract

_Assembled fresh 2026-10-02 by system_rules.py --card CARD-151 (card_scope: touches), plus CON-015, which the card cites but the lens scopes out (its scope is src/nonogram/admin/**)._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy; no third-party package joins without revising the ADR. (check: test TestDependencyBaseline_IsExactlyPillowAndNumpy)
- CON-005 — The uniqueness check must never produce a false positive. (check: test PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds 127.0.0.1 only. (check: test TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI refuses cross-site / foreign-authority requests. (check: test PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. (check: test PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A request whose aspect ratio differs from the source's ink box by more than 2x is refused. (check: test PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's entry point binds 127.0.0.1 only, debugger off; the bind address is a constant. (check: test TestAdminPanel_BindsLoopbackOnlyByDefault) — card-cited

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
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +ADR-0006/R1, CON-005, CON-009, CON-010, CON-011, CON-012 (+CON-015 card-cited) / −none (the card had no section)
- [Implementation, commit 04116bc] Smallest change: `PSQL_URL` = DATABASE_URL with
  `+driver` dropped from the scheme (bash parameter expansion), passed as one
  argument, so host/port/credentials/query survive; the panel still gets
  DATABASE_URL untouched (G-4). DB_NAME is now the path after the host up to
  any `?query` (the old `${DATABASE_URL##*/}` returned `user@host:port` for a URL
  with no path — a second form of the empty-name defect). Empty DB_NAME is
  refused in step [1/6] before the Docker branches and before any psql, with
  "✗ DATABASE_URL names no database", the URL + source (same echo the existing
  refusal already prints — no new password exposure), and "This script does not
  create a database." Docker branches' `-d "$DB_NAME"` untouched (F-005).
- [Harness] The psql stub is now an independent Python model (urllib.parse) of
  real psql's measured behaviour: only postgresql:// / postgres:// are URIs; a
  `+driver` string without `=` is taken whole as a database name, with `=` is
  rejected as conninfo; an empty dbname falls back to the user ($PGUSER, else
  $USER — harness pins USER/LOGNAME). It logs a `connect user= password= host=
  port= dbname=` line that AC-3 and the corpus assert on. Existing 19 tests stay
  green unmodified in their assertions.
- AC-1: TestStartAdminLocal_AcceptsADriverQualifiedUrl (4 tests) red→green.
- AC-2: TestStartAdminLocal_RefusesAUrlThatNamesNoDatabase (4 tests, both
  "user-named database exists" and "absent") red→green.
- AC-3: TestStartAdminLocal_StillChecksTheTargetDatabase::
  test_the_check_carries_the_urls_host_port_and_credentials red→green (covers
  the driver-qualified URL); ::test_it_still_fails_when_the_database_is_absent
  green before and after — a regression guard for what CARD-150 won, by design.
- Corpus test_the_decision_over_an_enumerated_corpus_of_url_shapes (180 cases,
  min-count asserted): 156/180 wrong against the old script → 0 wrong.
- Tests: tests/test_start_admin_local.py 30 passed (~97s; corpus ~67s). Full
  suite: 5560 passed, 7 skipped, 2 failed — tests/e2e/test_admin_workflow.py::
  TestFlow2BatchImageUpload::test_size_configuration_applied and
  tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders,
  both failing in isolation on admin page content; pre-existing, unrelated to
  scripts/ (neither touches the launcher).
- No SCOPE+: scripts/README.md makes no statement this change falsifies.
- [Scope] scripts/start_admin_local.sh, tests/test_start_admin_local.py
- [Build gate] impact underivable (test_scope: full) — full suite
- [Build gate] PASSED (full, 374s; baseline: 2 failures pre-existing on main dc26103 and reproduced there in isolation — tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders (backlog "Tests" item); no new failure. Lock: meta/kanban/.full-suite.lock via fcntl.flock — no flock(1) on this machine)
- [Scope gate 1/3] IN_SCOPE — 2 files, both in Touches; guardrail hits: none (no src/ path)
- [Adversarial] F-001 CONFIRMED — query-dropping mutant (PSQL_URL rebuilt from DB_PATH) survives all 30 tests; libpq parse_dsn confirms URI query params (host/port/dbname/sslmode) override the URI parts. Skeptic's correction: the contract hook is "What to do" item 1 + the script's own comment, not AC-3's text.
- [Review 1/3] Score: 8.0 — crit: 0, imp: 1
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: 7/7 card rules have a verdict line (2 ✓, 5 ⚠, 0 ✗)
- [Review 1/3] 8f mutation: ran — 8 mutants, 6 killed, M7 survived (equivalent on well-formed URLs → Minor F-003), M8 survived (→ F-001)
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Fix 1] Cycle-1 findings. Invariant enforced: the check's psql target ≡ the
  panel's DATABASE_URL minus only the +driver, and the database the script names
  ≡ the one psql connects to. F-001: the psql model now applies libpq query
  semantics (parse_qsl; query keywords override URI parts; unknown key = error;
  query keys logged on `connect`); the script now honours `?dbname=` (last wins,
  as libpq and the panel's driver do) when naming the database — pre-fix it
  named the path's database while psql checked the query's. New class
  TestStartAdminLocal_CarriesTheUrlsQuery (5 tests). F-004: a value with no
  `://` is refused first with "✗ DATABASE_URL is not a URL" + URL/source + "does
  not create a database" (TestStartAdminLocal_RefusesAValueThatIsNotAUrl).
  F-002: corpus is now a greedy pairwise covering array (20 cases, floor
  asserted, pair coverage self-checked) with query values that set host/port
  and dbname/user; it also asserts the named database per case. F-003
  dismissed (raw `?`/`/` in userinfo is invalid; refused fail-safe); its
  libpq-valid `?dbname=`-only sub-case is now accepted via F-001. Mutants: M5,
  M6, M8, M9 (drop ?dbname override), M10 (drop not-a-URL guard) killed; M7
  survives (near-equivalent). Pre-fix script fails 4 new tests with the
  finding's own symptoms. File: 36 passed in ~47s (was ~97s). README: no
  statement falsified.
- [Fix 1] pre-gate PASSED — 7/7 named tests green; FIXED F-001, F-002, F-004 · SKIPPED/dismissed F-003 (raw ?// in userinfo is invalid RFC 3986; all refused, none green)
- [Fix 1] declarations: 3 updated (script DB_NAME comment + "names no database" hint; _PSQL_MODEL doc; corpus docstring/MIN_CORPUS_CASES; step [1/6] refusal comment), 4 confirmed (PSQL_URL comment, --help, scripts/README.md ×2), 0 none · design note: DB_NAME now also honours ?dbname= and so feeds the out-of-scope Docker -d "$DB_NAME" branches too (F-005 otherwise untouched)
- [Build gate] PASSED (full, 328s; baseline: the same 2 pre-existing failures, no new failure)
- [Scope gate 2/3] IN_SCOPE — 2 files, both in Touches; guardrail hits: none
- [Review 2/3] full mode (not confirmation): the fix delta adds behaviour (?dbname= override, not-a-URL refusal), so discovery-depth review on both files
- [Adversarial] F-006 CONFIRMED — mutant ME (`[^&]*`→`[^&]+` in the ?dbname= extraction) survives all 36 tests; under ME the suite's own run_script prints "✓ … database 'nonogram_dev' reachable" for `postgresql://someone@localhost:5432/nonogram_dev?dbname=` while psql connected to `someone` (AC-2 shape); libpq parse_dsn confirms an empty query dbname overrides the path. Script itself correct — test-coverage gap only.
- [Review 2/3] Score: 8.0 — crit: 0, imp: 1
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h coverage: 7/7 card rules have a verdict line (2 ✓, 5 ⚠, 0 ✗)
- [Review 2/3] cycle-1 findings: F-001 ✓ resolved, F-002 ✓ resolved, F-003 dismissal sound, F-004 ✓ resolved
- [Review 2/3] 8f mutation: ran — 7 mutants, 4 killed (MA not-a-URL guard, MB empty-name guard, MH ?dbname= override, M8 query in psql target), 3 survived: ME (→ F-006), MC first-vs-last ?dbname= (→ Minor F-008), MD `&` anchor (equivalent for safety)
- [Severity gate 2/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Review 2/3] family regression check: F-006 attributed to fix 1 (the F-001 fix's ?dbname= handling, named in its DECLARATIONS) — streak 1 of 2, no escalation from this check
- [Review 2/3] ⚠ improvement stalled — Δscore: 0.0, Δcrit+imp: 0
- [Escalated] 2026-10-02 — review loop stalled at cycle 2/3 (score 8.0 → 8.0, gating findings 1 → 1: cycle-1 F-001 resolved, cycle-2 F-006 raised by its fix) · station: implementation · route: manual fix + /kanban review CARD-151 — NOT /kanban redo: the loop converged on everything but one test case. The code is correct (reviewer and skeptic both verified the script refuses the URL); what is missing is a test pinning it: extend tests/test_start_admin_local.py::TestStartAdminLocal_CarriesTheUrlsQuery::test_an_empty_dbname_in_the_query_still_names_no_database to also use `postgresql://someone@localhost:5432/nonogram_dev?dbname=` with nonogram_dev absent and `someone` present, and confirm it kills mutant ME. Optional in the same pass: Minor F-008 (a repeated-?dbname= test kills MC). Changes are UNCOMMITTED in the worktree (fix 1 on top of 04116bc) — worktree and branch kept. Evidence: meta/review/20261002T110413Z-CARD-151-cycle2.yml.
- [Unblocked] 2026-10-02 — owner chose manual fix of F-006 + /kanban review (dispatcher)
- [Fix 2] (orchestrator, owner-authorised manual fix) FIXED F-006 — test: tests/test_start_admin_local.py::TestStartAdminLocal_CarriesTheUrlsQuery::test_an_empty_dbname_in_the_query_still_names_no_database (now also `postgresql://someone@localhost:5432/nonogram_dev?dbname=`, nonogram_dev absent, `someone` present; asserts refusal, no green tick, no psql call) · FIXED F-008 — test: ::test_the_last_dbname_in_the_query_wins · F-007 left (owner). Mutants: ME `[^&]*`→`[^&]+` KILLED (returncode 0 where refusal expected), MC first-?dbname=-wins KILLED; script restored byte-exact after each (cp + cmp). Test file 37 passed (46.8s), bash -n clean.
- [Fix 2] declarations: 0 updated, 0 confirmed, 2 none (test-only: no bound, lifecycle, error class or config meaning changed)
- [Commit] ce2574b — fix 1 + fix 2 (scripts/start_admin_local.sh, tests/test_start_admin_local.py; explicit pathspecs)
- [Build gate] PASSED (full, 342s; pre-existing baseline: the same 2 failures red on main dc26103 — test_size_configuration_applied, test_wave3_e2e::test_batch_creation_form_renders; no new failure)
- [Scope gate 3/3] IN_SCOPE — 2 files, both in Touches; guardrail hits: none
- [Review 3/3] confirmation mode: fix delta since the cycle-2 reviewed state = tests/test_start_admin_local.py only (F-006 + F-008 tests); scripts/start_admin_local.sh byte-identical to the cycle-2 state; deferred/final certification (mutation check) required this cycle
- [Review 3/3] Score: 9.0 — crit: 0, imp: 0
- [Review sync] 3 report(s) → meta/review/
- [Review 3/3] Step 8h coverage: 7/7 card rules have a verdict line (2 ✓ fresh, 5 ⚠ carried(cycle 2, delta-clean), 0 ✗)
- [Review 3/3] previous findings: F-006 ✓ resolved, F-008 ✓ resolved, F-007 left by owner
- [Review 3/3] 8f mutation (deferred certification, stable cycle): ran — 8 mutants, 8 killed (ME, MC, MA not-a-URL guard, MB empty-name guard, MF +driver strip, MG psql arg, M8 query in psql target, MH ?dbname= override)
- [Review 3/3] Score: 9.0 ✓ threshold reached + no critical/important
- [8h spot-check] 2/2 sampled holds reproduced (CON-015, ADR-0006/R1) — CON-015: launch line content byte-identical to main (moved :239→:289), grep empty, tests/test_admin_binding.py 33 passed; ADR-0006/R1: no pyproject/src path, stdlib-only imports incl. the psql-model string, baseline test green
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — TestStartAdminLocal_AcceptsADriverQualifiedUrl (4 tests) PASSED (rc 0, "database 'nonogram_dev' reachable", panel still gets the URL as exported, other drivers accepted)
  AC-2 ✓ demonstrated — TestStartAdminLocal_RefusesAUrlThatNamesNoDatabase (4 tests) PASSED, both "user-named database exists" and "absent" cases; refusal text checked, no ✓, no psql run
  AC-3 ✓ demonstrated — TestStartAdminLocal_StillChecksTheTargetDatabase PASSED: dbname=nonogram_dev in every psql call (plain + driver URL); absent database → non-zero, "Database 'nonogram_dev' is not reachable", stops before [2/6]
  G-1 ✓ demonstrated — bash -n clean; main vs HEAD counts unchanged for ✓ 13/13, [2/6]..[6/6], --port, --no-migrate, --check-only, --help (✗ 6→8 and [1/6] 3→4 additions only)
  G-2 ✓ demonstrated — no createdb/dropdb/create|drop database/alembic downgrade|stamp/INSERT/seed in script or tests; stubs only
  G-3 ✓ demonstrated — nonogram.admin.app 4/4, editable-install probe 2/2, launch/probe lines outside the diff
  G-4 ✓ demonstrated — diff = scripts/start_admin_local.sh, tests/test_start_admin_local.py only; nothing under src/ (normalized_url untouched)
  G-5 ✓ demonstrated — no skipif/importorskip/pytest.mark; stdlib-only test imports; tools stubbed on PATH with DATABASE_URL/PG* stripped; CARD-150 test bodies unchanged (only the old always-succeeding _PSQL_STUB replaced by the stricter psql model)
  (no Engineering constraints section on this card; 10/10 named tests passed, 11.1s)
- [Docs] forge:readme on scripts/, tests/ — both READMEs current: no file added/removed/renamed, no responsibility shift; scripts/README.md re-checked by 3 reviews + fix agent, nothing it states is made false — skipped
- [Commit] success commit: ce2574b (already on the branch, made at the owner-authorised fix step with explicit pathspecs + Co-Authored-By; the final gates found nothing to change, so the worktree had no code diff left to commit and no empty commit was made). Branch = 04116bc + ce2574b.
- [Merged] 2026-10-02 — 4fc5821 into main (--no-ff). Merge gate: rebase was a no-op (main still at dc26103 = branch base), so the merged tree is exactly ce2574b, the tree that passed the cycle-3 full suite under the lock (342s; baseline = the 2 failures red on dc26103). Not re-run. Deferral scan: 0 real deferrals (hits are the test's psql `stub` fixture). No trace write-back: untraced card (FR —).
