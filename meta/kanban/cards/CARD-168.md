# CARD-168: Ops housekeeping: say where Render's settings live, and point the test runner at the test database

**Status:** ready
**Priority:** P2
**Category:** ops
**Estimate:** 0.5d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (owner decisions on IDEA-003 and IDEA-036)
**Idea:** IDEA-003, IDEA-036
**Wave:** 32
**Depends on:** —
**Touches:** render.yaml, docs/deploy/render.md, scripts/run_admin_tests.sh, scripts/README.md, tests/test_run_admin_tests.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
