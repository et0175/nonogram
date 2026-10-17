# CARD-244: Each worktree gets its own test database, so concurrent cards stop corrupting each other's runs

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/244-per-worktree-test-database
**Worktree:** ../PythonProject4-card-244
**Source:** measured on this board, wave 44 (2026-10-17) — CARD-222's build gate, and the owner's wave-45 decision to harden before resuming the interior chain
**Idea:** backlog, "The full-suite lock does not protect the shared `nonogram_test` database"
**Wave:** 45
**Depends on:** —
**Touches:** tests/conftest.py, tests/test_card_156_db_fixture.py, tests/test_db_e2e_smoke.py, tests/test_db_isolation.py, scripts/run_admin_tests.sh, scripts/setup_admin_local.sh
**Review score:** —
**Started:** 2026-10-18T00:00:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Every pytest process on this machine currently points at **one** database, `nonogram_test`, and
the session fixture rebuilds it destructively: `DROP SCHEMA public CASCADE`, `CREATE SCHEMA
public`, then `alembic upgrade head` (`tests/conftest.py`). There is also a per-test TRUNCATE.
So two cards running at the same time do not merely contend — **they destroy each other's
data.**

**This is measured, not theoretical.** Wave 44's evidence:

- A 7-file DB selection run beside a full suite produced **2 failures** in
  `test_book_trim_persistence` that are **200 passed in isolation**.
- CARD-222's build gate reported `57 skipped` against this suite's normal `9`. The 48-test
  "regression" **did not exist** — it was partial reachability of `nonogram_test` while a
  sibling card held it. Chasing it burned an entire fix-agent attempt.
- `conftest.py` **already knows**: its own comment says "several pipelines share
  nonogram_test, and a connection one of them holds open would make DROP SCHEMA wait on its
  lock". The present response is a 10-second `lock_timeout`, which converts a hang into an
  error. That is a better failure, not a fix.

**The approach: derive the database name from the repo root**, so a worktree can only ever
touch its own. `test_db_url` already reads `TEST_DATABASE_URL` and falls back to a hardcoded
`.../nonogram_test`; the fallback becomes `.../nonogram_test_<slug>` where `<slug>` is derived
from the resolved repo root. The session fixture creates that database if it is absent (via the
`postgres` maintenance database) and then runs the existing rebuild path unchanged.

**Alternatives considered and rejected, recorded so they are not re-proposed:**

- **A transaction-rollback fixture instead of TRUNCATE.** Faster and elegant, but it does not
  fix this: the code under test opens its *own* connections, so a test that writes through the
  fixture's transaction and reads through the app's connection would stop seeing its own data.
  It trades a concurrency bug for a correctness bug in the fixture.
- **Widen the full-suite lock to cover any DB-touching selection.** Simplest, and it would
  work — but it serialises all database work, which is precisely the parallelism the cap of 2
  exists to buy. It makes the symptom impossible by making concurrency impossible.
- **Keep one database and add advisory locking.** Still serialises, and adds a second locking
  protocol beside `meta/kanban/.full-suite.lock`.

**What this card does NOT do.** It does not remove or weaken `meta/kanban/.full-suite.lock`.
That lock exists for a second, independent reason — host load, since
`max_concurrent × full suite` saturates this machine — and that reason survives per-worktree
databases. This card removes the *data* collision only.

## Acceptance criteria

- **AC-1** (happy, the name is per-tree): *Given* two distinct resolved repo roots, *when* the
  default test-database URL is derived for each, *then* the database names differ, and each is a
  legal unquoted Postgres identifier. (test: `TestTestDbUrl_NameIsDerivedPerWorktree`)
- **AC-2** (happy, created when absent): *Given* a derived database that does not exist, *when*
  the session fixture runs, *then* it creates the database and migrates it to head, and the
  suite proceeds — it does not skip. (test: `TestTestDbSetup_CreatesTheDatabaseWhenAbsent`)
- **AC-3** (guard, an explicit override still wins): *Given* `TEST_DATABASE_URL` set
  explicitly, *then* it is used **unchanged** and no name is derived — CI, the owner's own runs
  and `scripts/run_admin_tests.sh` must keep working exactly as today.
  (test: `TestTestDbUrl_ExplicitOverrideIsUsedVerbatim`)
- **AC-4** (negative, the safety refusal still bites): *Given* a derived or overridden URL that
  names a non-test database, *then* `_refuse_unless_test_database` still refuses it. **Deriving
  a name must not open any path to `DROP SCHEMA` on `nonogram_poc` or `nonogram_dev`.** Assert
  the refusal, with those two names among the cases.
  (test: `TestTestDbSetup_StillRefusesANonTestDatabase`)
- **AC-5** (edge, the identifier limit): *Given* a repo root whose derived name would exceed
  Postgres's 63-byte identifier limit, *then* the name is truncated deterministically and two
  different long roots still derive different names. **State the measured length** of the name
  your scheme produces. (test: `TestTestDbUrl_LongPathsStayUniqueAndLegal`)
- **AC-6** (the property the card exists for): *Given* two pytest processes running DB tests
  from two different repo roots **concurrently**, *then* both pass, and neither observes the
  other's data. This must be **executed**, not reasoned about: run the two processes, and show
  that the same pair reds today. (test: `TestDbIsolation_TwoTreesDoNotCorruptEachOther`)

## Guardrails

- **G-1 (the one that matters): `nonogram_poc` and `nonogram_dev` are never created, dropped,
  connected to or truncated by the suite.** The live admin panel runs on `nonogram_poc`. A
  name-derivation bug here is the one defect on this card that could destroy the owner's real
  data, so assert the refusal rather than relying on the naming convention holding.
- **G-2: the skip behaviour is unchanged when Postgres is unreachable.** The suite's documented
  9 skips with the database up, and the `db_required`/`DATABASE_URL` skip path, must behave
  exactly as now. Do not convert a skip into a failure or a failure into a skip.
- **G-3: the full-suite lock stays.** See "What this card does NOT do".
- **G-4: no new runtime dependency.** The baseline is stdlib + Pillow + NumPy (ADR-0006/R1);
  database creation goes through the driver already present.
- **G-5: `alembic upgrade head` still runs in a subprocess**, for the reason `conftest.py`
  records — its `env.py` calls `logging.config.fileConfig`, which would disable every logger
  already created in-process and break later `caplog` assertions.
- **G-6: no test is retired without a named survivor** (CARD-220's rule).

## System contract

_Assembled 2026-10-18 by `system_rules.py --card CARD-244 --root meta/architecture` (10 rules, `card_scope: touches`). A projection — fix the source artifact, never this list._

**No rules were dropped.** The projection returned 10, inside the 6–14 band the owner approved on 2026-10-17, so this card carries its contract in full rather than curated. That is itself worth noting: the book cards project ~60 rules and have to be curated because 57 of them are scoped `src/nonogram/**`; this card touches `tests/` and `scripts/` and so lands a small, honest contract without help.

- **ADR-0038/R7** — Browser tests use pytest-playwright with Chromium, declared only in a dev-only
  extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check:
  review-lens)
- **ADR-0038/R8** — Browser tests run locally, against Chromium installed by `playwright install
  chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named skip
  reason visible in the run summary. They never pass silently. Once a CI pipeline exists, it
  installs Chromium (playwright install chromium) before running them; until then there is no CI,
  and that is a known gap, not a met cl… (check: review-lens)
- **ADR-0039/R1** — A set a guard consults needs a completeness test written before the set, and any
  claim the guard makes about what it catches needs a control that can fail: caught WITH the set
  member present, missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage,
  and must be narrowed to what is measured or deleted. (check: test:
  test_the_control_for_each_spelling_depends_on_the_set)
- **ADR-0039/R2** — A guard's set is derived from an authority the runtime can enumerate, not hand-
  written. Where no such authority exists, the guard defaults to deny: a shape it cannot analyse is
  a FAILURE, never a silent pass, and the unanalysable sites become named exemptions under
  ADR-0039/R3. (check: test: test_the_guard_sets_are_derived_and_not_hand_written)
- **ADR-0039/R3** — An exemption is a claim. Every exemption a guard grants carries a control for
  what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to
  an equality against the sites that exist today, and records whatever it still cannot see as a
  measured bound with its own failing control. (check: test:
  test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw)
- **CON-005** — The uniqueness check must never produce a false positive: a puzzle accepted as
  unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness
  property the whole tool depends on. (check: test:
  PropertyTest_Solver_NeverFalsePositiveUniqueness)
- **CON-009** — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only,
  and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-
  enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's
  socket-reach half is discharged by more than a threshold visible only in requirements.yml. (check:
  test: TestWebServer_BindsLoopbackOnlyByDefault)
- **CON-010** — The web UI's HTTP server refuses any request the browser itself marks as cross-site
  (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback
  host), and refuses any absolute-form request target whose authority is not a loopback name
  (NFR-004). Restates NFR-004 as a gate-enforced mandatory constraint — a `check:` the system
  contract actually collects — so BCO… (check: test:
  PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- **CON-011** — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide
  and applies to every source mode (random, built-in library, uploaded image) and to both inbound
  adapters (CLI and web UI). This supersedes the 10..50 range FR-001 carried; FR-001 is marked
  status: superseded, superseded_by: FR-019, and FR-019 restates the behaviour over the narrowed
  range. (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- **CON-012** — A generation request whose grid aspect ratio differs from the uploaded source
  image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file
  ratio) by more than 2x is refused with an explanatory error rather than converted (FR-021). The
  centred crop of FR-020 retains exactly min(r_src, r_tgt) / max(r_src, r_tgt) of the source with r
  = width/height, so this is ex… (check: test:
  PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **ADR-0039/R1 is the rule this card is most likely to breach, and it breaches it through AC-6.** "Two processes do not corrupt each other" is exactly the shape of claim whose control cannot fail unless someone writes the counterfactual — a pair that **reds** against a single shared database. The AC demands it be executed for that reason. Wave 43's retrospective found every gating finding on this board reduced to R1, and the wave-44 headline was that R1 "existed and did not bite" because its own `check:` is a point test in one file that cannot see a claim written elsewhere. Do not let that happen again here.
- **ADR-0039/R2 applies to the name derivation.** The set of databases the suite may touch must be derived from an authority the runtime can enumerate, and **default to deny**: a URL whose database name the code cannot classify is a FAILURE, never a silent pass. This is G-1's mechanism — it is what keeps `nonogram_poc` safe, rather than the naming convention holding.
- **ADR-0038/R8 is a live tension, not a formality.** It says browser tests must fail or skip *loudly* and never pass silently. This card is about a *different* silent pass — a DB test that skips because a sibling took its database — and the two should end up stating the same principle. If your change makes a DB skip quieter rather than louder, you have gone the wrong way.
- **ADR-0038/R7 bounds the fix.** `pytest-playwright` lives in a dev-only extra and must not reach `project.dependencies`; G-4 says the same for anything you reach for here. Database creation goes through the driver already present.
## Worktree notes

- **[Implemented `c4ac4d6`, and it overruled the card's own naming sketch — correctly.]** The card
  sketched `nonogram_test_<slug>`. Shipped: **`nonogram_<slug>_test`**. I verified the reason rather
  than accepting it: `conftest.py:271` is `if not name.endswith("_test")`, and
  `test_card_156_db_fixture.py` pins **`nonogram_test_backup`** among the names it refuses precisely
  because "starts with `nonogram_test`" is not good enough. So the prefix spelling would have required
  **widening the one guard standing between `DROP SCHEMA` and `nonogram_poc`** and retiring that case;
  the suffix spelling needs no change to that guard at all. My suggested `nonogram_test_card244` would
  itself have been *refused* by today's code. Good pushback on a brief — the card's wording is the
  sketch, the guard is the constraint.

- **[Verified independently before committing, not taken on report]** The suffix rule above; the three
  derived names (`…41B` for the repo, 50B for this worktree, 50B for CARD-223's — all distinct, all
  legal, all under 63); and **51 passed / 0 skipped in 34.75 s** against a live Postgres, matching the
  agent's own 51/32 s.

- **⚠ [The finding that matters beyond this card: THE MERGE GATE CANNOT EVIDENCE THIS CARD'S CENTRAL
  ACs.]** The board's documented gate condition is `nonogram_test` reachable with **`DATABASE_URL`
  unset**, which is what produces 8 of the suite's 9 normal skips. Measured here: with `DATABASE_URL`
  unset, `tests/test_db_isolation.py` runs **48 passed, 3 skipped** in 0.14 s — and the 3 skipped are
  **AC-2 (create-if-absent) and AC-6 (the concurrent-isolation proof with its counterfactual)**, i.e.
  the two criteria the card exists for. With `DATABASE_URL` set they are 51 passed in 34.75 s.
  **So the full-suite gate is not the evidence for AC-2 and AC-6; the separate run above is**, and the
  card's AC/EC/G gate records that run rather than pointing at the suite.
  **Generalised, because it is not about this card:** *any* acceptance criterion on this board whose
  named test is `db_required` is **never exercised by the merge gate**. That is a systemic evidence
  hole, it sits beside the 20 vacuous TODO-stub DB tests already in the backlog, and it is the reason
  "the gate is green" has to stop being treated as coverage for DB-dependent claims. Opened as a
  backlog item.

- **[Leftover databases to drop at merge]** `nonogram_card244_test` (created by hand for the agent's
  own isolation, on my instruction) and `nonogram_pythonproject4_card_244_d541cdce17d1_test` (this
  tree's derived database, created by a real run). Every database the tests themselves create is
  dropped in a `finally`, through a `_drop_database` that asserts the name's shape and refuses
  `nonogram_poc` / `nonogram_dev` / `nonogram_test` outright. **`nonogram_poc` was never connected to
  at any point** — the only live-database contact was `SELECT datname FROM pg_database` against the
  `postgres` maintenance database.

- **[Outside `Touches`, flagged by the agent rather than assumed — all four accepted]**
  `tests/db_name.py` (new; the derivation has to be importable without dragging in `nonogram.admin`,
  precedent `tests/database_guard.py` and `tests/hang_guard.py`), `tests/helpers/admin_scripts.py`
  (`TEST_DATABASE_URL` added to the stripped environment, for the same reason `DATABASE_URL` already
  is — otherwise the agent's own exported value decided the outcome), `tests/test_admin_local_cost.py`
  (its declared execution-set equality 63→66 and 69→72, for three tests added to
  `test_run_admin_tests.py`), and `tests/README.md` (its `db_session` description said "default
  `…/nonogram_test`", now false).
  **`scripts/setup_admin_local.sh` is in `Touches` and was deliberately NOT changed**: its default URL
  is `nonogram_poc` and no AC needs it, so editing the script that migrates the live panel's database
  was the highest-risk edit available on this card for no benefit. Correct call.

- **[A known limit, stated rather than hidden]** A bare `./scripts/run_admin_tests.sh` does **not** get
  per-tree isolation — its harness runs the script alone in a throwaway root where `tests/db_name.py`
  cannot exist, so deriving there would mean duplicating the derivation in bash. Not done, judged not
  worth the risk; that path stays the explicit-override path (export `DATABASE_URL` per tree, or run
  `pytest`). The script did gain one line of behaviour, `export TEST_DATABASE_URL="${TEST_DATABASE_URL:-$DATABASE_URL}"`,
  without which it would check and print one database and then watch the suite `DROP SCHEMA` on
  another — and if the derived one were unreachable, every DB test would skip while the script still
  said "Tests completed!", which is the green-for-nothing run CARD-152 added the check to prevent.

- **[Why this is P1 and why the owner put it ahead of the interior chain]** It does **not**
  unlock parallelism for CARD-223..CARD-233 — those collide on `export/layout.py` and
  `book_pdf_generator.py` and will serialise regardless. What it buys is **gate integrity**:
  without it, every concurrent run can produce failures and skip counts that are artefacts of a
  sibling card rather than of the code. This wave that cost one full fix-agent attempt and
  produced a false finding that reached the owner. A gate whose red can mean "the host" rather
  than "the code" is not a gate.

- **[Read `tests/conftest.py` before designing anything]** The rebuild is **session**-scoped,
  not per-test: `DROP SCHEMA public CASCADE` / `CREATE SCHEMA public` / `alembic upgrade head`,
  with a 10-second `lock_timeout` and the engine disposed through a `finally` on every exit
  path including a failed migration (CARD-156, and its Fix-1 F-003). There is a separate
  per-test TRUNCATE. Both are deliberate and documented; this card changes **which database**
  they act on, not what they do.

- **[A trap in AC-6]** "Two processes do not interfere" is trivially satisfiable by a test that
  never actually runs two processes. The AC says *executed* on purpose, and it asks you to show
  **the same pair reds today** — against a single shared database — because that counterfactual
  is the only thing that distinguishes a real isolation proof from a tautology. The method is
  already demonstrated on this board: wave 44 produced 2 failures in
  `test_book_trim_persistence` under contention that are 200 passed in isolation.

- **[House rules that bite here]** `hypothesis` is **not** in the dependency baseline — build
  corpora with seeded `random.Random` and assert a minimum case count inside the test. Prefer an
  independent second implementation over re-deriving a value with the function under test.
  Capability modules never import laterally (`tests/test_cli.py` has an `ast` guard).

- **[Do not measure timings on a loaded host]** If you want to show the TRUNCATE cost, note
  that this board has just learned twice over that a contended measurement is not a measurement:
  state the host condition with every figure, and prefer ratios to absolute seconds.
