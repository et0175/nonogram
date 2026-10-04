# CARD-168: Ops housekeeping: say where Render's settings live, and point the test runner at the test database

**Status:** done
**Priority:** P2
**Category:** ops
**Estimate:** 0.5d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/168-ops-housekeeping
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (owner decisions on IDEA-003 and IDEA-036)
**Idea:** IDEA-003, IDEA-036
**Wave:** 32
**Depends on:** —
**Touches:** render.yaml, docs/deploy/render.md, scripts/run_admin_tests.sh, scripts/README.md, tests/test_run_admin_tests.py
**Review score:** 9.5 (cycle 1/3)
**Started:** 2026-10-04T07:04:41Z
**Closed:** 2026-10-04T07:55:48Z
**Actual:** 0.1d
**Merge commit:** cca9f0f
**Blocked by:** —

## What to implement

Two small ops items, both decided by the owner on 2026-10-04.

**1. Render (IDEA-003). Owner decision: the dashboard stays authoritative; document it.**
The deployed panel's Render service was created in the dashboard, so
`render.yaml` is ignored. Its build command, start command and env vars don't
apply. That cost four redeploys on 2026-09-23: production was running
`flask run` on python3.14 while `render.yaml` pins 3.11, bypassing CARD-086's
gunicorn decision.
- Put a header comment at the top of `render.yaml`. It should say the file is
  NOT authoritative: the service is dashboard-managed, so edits here change
  nothing in production. Point to `docs/deploy/render.md`.
- Write `docs/deploy/render.md`. It holds the settings production actually
  runs: service type, Python version, Build Command, Start Command, env var
  names (never values), and whether migrations run on deploy.
  - Include what is known (the evidence above).
  - Mark every value the repo can't know as `TODO(owner): copy from the Render
    dashboard`.
  - Add a short drift-check procedure: what to compare after any deploy-related
    change.
  - You can't see the dashboard, so never invent a setting.

**2. Test runner default database (IDEA-036). Owner decision: default to `nonogram_test`.**
`scripts/run_admin_tests.sh` defaults `DATABASE_URL` to `…/nonogram_poc`.
pytest's own guard (`tests/database_guard.py`, CARD-109) refuses any database
whose name lacks "test". So the default fails at start-up.
- Change the runner's default to `postgresql://postgres:postgres@localhost:5432/nonogram_test`.
- An exported `DATABASE_URL` still wins and is reported, as CARD-152 built.
- Update `scripts/README.md` to match. Don't change the other two scripts'
  defaults: they serve the panel, not the tests.

## Acceptance criteria

- **AC-1:** `render.yaml` opens with a comment stating it is not authoritative and naming `docs/deploy/render.md`; that doc exists and lists the production settings, with every value the repo can't know marked TODO(owner).
  *test: review-lens (doc change)*
- **AC-2:** With no `DATABASE_URL` exported, `run_admin_tests.sh` checks and uses `…/nonogram_test`. An exported URL still wins and is named as the source.
  *test: TestRunAdminTests_DefaultsToTheTestDatabase (in tests/test_run_admin_tests.py, using CARD-152's stubs)*

## Guardrails

- G-1: No production behaviour changes. This card changes no deploy setting; `render.yaml`'s content below the header stays as it is.
- G-2: Never write a secret or credential into the repo or the doc. Env var NAMES only.
- G-3: Never create, drop, seed or migrate any real database. Tests use CARD-151/152's psql model on PATH.
- G-4: `setup_admin_local.sh` and `start_admin_local.sh` keep their defaults, and CARD-152's pinned-identical URL logic stays identical across all three scripts.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-168` (7 rules). A projection — fix the source artifact, never this list._

- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

## Architecture context

- **FR:** — (ops; untraced like CARD-150..152)
- **ADR:** ADR-0030 (credentialed deployment), CON-016
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-003 and IDEA-036, owner decisions 2026-10-04. The Render facts come from the 2026-09-23 incident (access-log format, venv path).
- [Env] forge 2026.8.17
- [System contract] fresh assembly (system_rules.py) matches the card's 7 rules — no refresh
- [Impl] Commit edc3de8. render.yaml: 10-line header prepended (NOT AUTHORITATIVE, dashboard-managed, see docs/deploy/render.md); `tail -n +11 render.yaml | cmp - <original>` → identical (G-1). New docs/deploy/render.md: settings table where every current value is `TODO(owner): copy from the Render dashboard`; the evidence column holds only the 2026-09-23 observations (Werkzeug log format, `flask run` on `src.nonogram.admin.app`, venv `python3.14` vs render.yaml 3.11) and repo facts (Procfile holds that exact flask command, no claim the dashboard copied it); env var table = names the code reads (app.py, db/session.py, migrations/env.py, start.sh), dashboard presence TODO(owner); 4-step drift check. No values or secrets (G-2).
- [Impl] run_admin_tests.sh DEFAULT_DATABASE_URL → postgresql://postgres:postgres@localhost:5432/nonogram_test (+ comment why). setup/start scripts untouched (G-4). scripts/README.md: Prerequisites names both defaults; the run_admin_tests section and Day 1/Day 2 workflow comments updated. Left alone: the "Manual Commands" block still runs bare `pytest` after defaulting DATABASE_URL to nonogram_poc (pre-existing; not a run_admin_tests part — candidate backlog item).
- SCOPE+ tests/helpers/admin_scripts.py — the shared ExportedDatabaseUrlContract hard-coded `nonogram_poc` as every sibling's default; made it a class attribute `DEFAULT_DB` (default unchanged for setup_admin_local), _Runner overrides it with nonogram_test.
- SCOPE+ tests/test_setup_admin_local.py — CARD-152's identity check compared a block that INCLUDED the `DEFAULT_DATABASE_URL=` line, so any default change broke it. Now it compares everything after that line through the last `PSQL_URL=` (still ≥20 lines, still exact), and new `test_each_script_defaults_to_its_own_database` pins the three default lines exactly (poc, poc, test) — the excluded line is pinned rather than dropped, so no weakening.
- [Tests] New TestRunAdminTests_DefaultsToTheTestDatabase (3 tests): (a) a decoy DATABASE_URL set in the parent env via monkeypatch never reaches the script (harness strips it); only nonogram_test exists in the psql model; asserts "(project default)", psql model connected to dbname nonogram_test, pytest stub handed …/nonogram_test, no nonogram_poc anywhere; (a') only nonogram_poc exists → stops at the check, no pytest; (b) exported …/nonogram_mine_test wins, "(exported by the caller)", psql + pytest got it. Ran test_run_admin_tests, test_setup_admin_local, test_start_admin_local, test_admin_serving, test_admin_auth: 199 passed.
- [Mutation] default reverted to nonogram_poc → 5 failed (incl. DefaultsToTheTestDatabase ×2, contract default test, --help test, test_each_script_defaults_to_its_own_database). Restored.
- [Mutation] exported URL loses (`if false; then`) → test_an_exported_url_still_wins_and_is_named_as_the_source failed. Restored.
- [Mutation] exported source labelled "project default" → same test failed. Restored.
- [Mutation] setup_admin_local.sh default changed to nonogram_test → test_each_script_defaults_to_its_own_database + 2 contract tests failed. Restored.
- [Mutation] resolution-block body drift in run_admin_tests.sh → test_the_three_copies_of_the_url_resolution_are_identical failed. Restored.
- [Note] The dispatcher named skill python-pro; no such skill is in this session's skill list, so the work followed CLAUDE.md and the engineering-standards minimalism rule directly.
- [Scope] docs/deploy/render.md, render.yaml, scripts/README.md, scripts/run_admin_tests.sh, tests/helpers/admin_scripts.py, tests/test_run_admin_tests.py, tests/test_setup_admin_local.py
- [Scope gate] ⚠ grown: 2 files outside Touches (tests/helpers/admin_scripts.py, tests/test_setup_admin_local.py — both SCOPE+ declared; no COMP spread, no guardrail hit: setup_admin_local.sh/start_admin_local.sh untouched)
- [Build gate] impact underivable (test_scope: full) — full suite
- [Build gate] PASSED (full, 515s) — 6038 passed, 9 skipped, 2 failed = exactly the two wave-32 baseline failures (test_size_configuration_applied, test_batch_creation_form_renders; CARD-164 owns them)
- [Review 1/3] Score: 9.5 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: 7/7 card rules have a verdict line (all ⚠ unchecked — no_eligible_fact)
- [Review 1/3] Score: 9.5 ✓ threshold reached + no critical/important
- [8h spot-check] skipped — no fresh ✓ holds in cycle 1 (all 7 rules ⚠ unchecked, no_eligible_fact)
- [Mutation check] reviewer ran 3 mutants (runner default → nonogram_poc; exported URL relabelled project default; setup_admin_local default → nonogram_test): 3/3 killed
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — evidence: review-lens inspection: render.yaml:1 '# NOT AUTHORITATIVE. Production does not read this file.', :8 names docs/deploy/render.md; render.md Settings table (service type, Python version, Build/Start/Pre-Deploy Command, Auto-Deploy, Migrations on deploy) + env-var names table; every dashboard value TODO(owner); only dated 2026-09-23 observations filled
  AC-2 ✓ demonstrated — evidence: pytest tests/test_run_admin_tests.py::TestRunAdminTests_DefaultsToTheTestDatabase → 3 passed (nothing-exported → nonogram_test (project default); poc-only → stops at check; exported wins, '(exported by the caller)')
  G-1 ✓ demonstrated — evidence: tail -n +11 render.yaml | cmp - <(git show 7e57b1c:render.yaml) → byte-identical
  G-2 ✓ demonstrated — evidence: grep of added diff lines: SECRET_KEY/ADMIN_PASSWORD names only (TODO(owner)); only credential-shaped string is the pre-existing local-dev postgres:postgres@localhost pattern
  G-3 ✓ demonstrated — evidence: new tests use only run_script/connections from tests/helpers/admin_scripts.py (psql model stub on PATH, existing_dbs=[...]); 83 passed across the three admin-script test files
  G-4 ✓ demonstrated — evidence: git diff --quiet 7e57b1c HEAD -- scripts/setup_admin_local.sh scripts/start_admin_local.sh → unchanged; test_the_three_copies_of_the_url_resolution_are_identical + test_each_script_defaults_to_its_own_database pass; excluded default line pinned per script, ≥20-line floor kept
- [Docs] forge:readme on changed dirs: scripts/README.md updated by the implementation (run_admin_tests default + Prerequisites); docs/deploy/ is new with one doc — no per-directory README created (convention is an open owner decision, backlog line 10); tests/ and tests/helpers/ — no file added/removed, tests/README.md does not describe the admin-script tests — skipped, current
- [Commit] success commit edc3de8 (the implementation commit — review cycle 1 passed with no fix and no README change, so /commit had nothing further to stage; meta/ excluded). Open Minor: F-001 env table omits PYTHONUNBUFFERED; F-002 scripts/README Manual Commands still runs bare pytest against nonogram_poc (pre-existing); F-003 incident evidence has no in-repo source. Card stays review until done.
- [Merged] 2026-10-04 — cca9f0f into main (--no-ff). Merge gate: rebase was a no-op (main still at 7e57b1c = branch base); the merged tree is the one that passed the full suite (only the wave's 2 baseline failures, being fixed by CARD-164); not re-run. Deferral scan: 1 hit, incidental (the doc's own instruction to replace its TODO(owner) markers). F-001/F-002/F-003 captured to backlog; the TODO(owner) rows in docs/deploy/render.md are the owner's to fill from the Render dashboard.
