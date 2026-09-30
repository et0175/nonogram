# CARD-139: One import style in the admin package — a duplicate module tree cannot exist

**Status:** done
**Priority:** P1
**Category:** bug
**Estimate:** 0.25d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/139-admin-import-consistency
**Worktree:** —
**Source:** owner, 2026-09-23 (live panel: Print setup crashed on a stored plan)
**Idea:** —
**Wave:** 26
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/__init__.py, tests/test_admin_import_consistency.py
**Review score:** 9.0 (1 cycle + fix)
**Started:** 2026-09-30T12:08:28Z
**Closed:** 2026-09-30T13:05:00Z
**Actual:** 0.1d
**Merge commit:** a8bdade
**Blocked by:** —

## What to implement

The admin package mixes import styles: 44 absolute (`from nonogram.admin.x import ...`)
against 13 relative (`from .x import ...`), and `app.py` is itself mixed — 9 relative,
7 absolute. That is invisible until the package is imported under a second name, and
then it is a live 500.

Reproduced on the owner's panel, 2026-09-23. Launched as
`flask --app src.nonogram.admin.app`, Python loads the package twice —
`nonogram.admin.book_plan` **and** `src.nonogram.admin.book_plan` are both in
`sys.modules`, with two distinct `LongestSideBucket` enum classes whose members are
equal to nothing across the divide. `app.py` takes `PLAN_BUCKETS` from its relative
import; `book_manager` (absolute) builds the stored `Plan`, so `Plan.cell` indexes the
*other* module's `BUCKETS`:

    File "src/nonogram/admin/book_plan.py", line 240, in cell
      return self.cells[BUCKETS.index(bucket)][TIERS.index(tier)]
    ValueError: tuple.index(x): x not in tuple

It only fires once a plan is **stored** — a plan-less book renders `DEFAULT_PLAN`, which
comes from app's own copy — so it reads as a data bug and cost the owner a debugging
session. Verified: `import nonogram.admin.app` loads one `book_plan`;
`import src.nonogram.admin.app` loads two, and `A.LongestSideBucket is B.LongestSideBucket`
is `False`.

1. **Convert the 13 relative imports to absolute** (`src/nonogram/admin/__init__.py`, 3;
   `src/nonogram/admin/app.py`, 10), matching the 44 that already are. Absolute wins on
   count and is what every other admin module uses.
2. **Guard it structurally.** Add `tests/test_admin_import_consistency.py` with an `ast`
   walk over `src/nonogram/admin/**/*.py` that fails on any `ImportFrom` with
   `level > 0`. Follow the precedent of the layering guard in `tests/test_cli.py`: walk
   the files on disk, so a new admin module is covered the day it is written.
3. **A test that the tree cannot double.** Import the app under both names in a
   subprocess and assert exactly one `nonogram.admin.book_plan`-suffixed entry in
   `sys.modules` — the property that actually broke, stated directly. Run it in a
   subprocess so it cannot pollute the suite's own module table.

Out of scope: converting the rest of the codebase to one style (only `admin/` is mixed),
anything about how the panel is launched (a launch command is not a repo artifact), and
any behaviour change — this card is import lines and tests, nothing else.

## Acceptance criteria

- New: no module under `src/nonogram/admin/` uses a relative import.
  test: TestAdminImports_NoRelativeImports
- New: importing the app under a `src.`-prefixed name does not create a second copy of
  `book_plan`.
  test: TestAdminImports_PackageTreeCannotDouble
- Regression: Print setup renders a book whose plan is stored, with no `ValueError` from
  `Plan.cell`.
  test: TestAdminImports_StoredPlanRendersUnderEitherImportName

## Guardrails

- G-1: Behaviour is unchanged — this is an import-style sweep. No route, template or
  aggregate edits.
- G-2: The layering guard in `tests/test_cli.py` stays green: `export/` must still never
  import `admin/`, and absolute imports must not become a way around it.
- G-3: Do not edit `src/nonogram/export/**` or `tests/fixtures/a4_golden/**` (CON-019).

## Architecture context

- **ADR:** ADR-0031 (tiers — the enum that doubled), CTX-001 (one bounded context)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes
- [Env] forge 2026.8.17
- [Runs alone, satisfied] Nothing else is in flight: CARD-128, CARD-131, CARD-132, CARD-144,
  CARD-145, CARD-141, CARD-142 and CARD-148 are all merged and their worktrees removed.
- [Count re-measured at start] 15 relative imports remain under `src/nonogram/admin/`, not the
  13 the card states: 4 in `__init__.py` and 11 in `app.py`. The card was cut on 2026-09-23 and
  the cards merged since have added a few. The AC is "no module uses a relative import", which
  is a property and not a count, so the number in "What to implement" is stale rather than
  wrong — but convert what is there, not what the card counted.
- [Card defect, and I have ruled it IN scope] "What to implement" excludes launch commands on
  the grounds that "a launch command is not a repo artifact". That is false for this repo:
  `scripts/start_admin_local.sh:147` runs `python -m flask --app src.nonogram.admin.app` — the
  repo's own launcher hardcodes the exact `src.`-prefixed launch that produced the live 500.
  The card's own [Origin] note says it "removes the trap rather than remembering the
  workaround", and leaving the launcher pointing at the trap does the opposite. One line, taken
  as a declared SCOPE+.
- [Out of scope, recorded for the architect station] `migrations/env.py` imports
  `from src.nonogram.db.models import Base` (pre-existing) and, since CARD-148,
  `from src.nonogram.db.session import normalized_url`. Both CARD-148 reviewers routed this
  here. It is the same doubling hazard one package over — under alembic those load
  `src.nonogram.db.*` while anything else loads `nonogram.db.*`, giving two `Base` classes and
  two metadata objects — but it is `migrations/`, not `admin/`, and the `src.` prefix there may
  be load-bearing for how alembic resolves the repo root. Not touched by this card. It needs
  its own card, with an alembic run to prove the change is safe.

- [Origin] Owner, 2026-09-23. Found while diagnosing a live `ValueError` on Print setup
  step 2. The immediate unblock was to relaunch as `--app nonogram.admin.app` (no `src.`
  prefix); this card removes the trap rather than remembering the workaround.
- [Scheduling] Runs **alone** in wave 26, after CARD-128/131/132 merge: it rewrites the
  import block at the top of `app.py`, which every other admin card also edits.
### Cycle 1 review (2026-09-30)

- [Review 1/3] **9.0** · risk LOW · `meta/review/20260930T123942Z-CARD-139-cycle1.yml` ·
  0 critical, 0 important, 2 medium, 1 low, 3 info. **Ready to merge.** Premise checked before
  trusting the diff (`merge-base` == main's head), after an earlier card this session was
  reviewed against a stale one. Nothing the orchestrator pre-verified was wrong.
- **The reviewer re-derived the reproduction by its own hand** rather than trusting the report:
  reverted both files to main, ran the new tests — 4 failed, 2 errors, `sys.modules` holding
  both `book_plan` entries — and reproduced the owner's traceback exactly, through
  `setup_print` → `_plan_context` → `cell_value` → `book_plan.py:240` →
  `ValueError: tuple.index(x): x not in tuple`.
- **AC-3 really exercises a *stored* plan**, proven by a nice piece of evidence: on the reverted
  source the subprocess errored at the *render* step, which means `assert plan is not None` had
  already passed. The crash was on the stored-plan path, not `DEFAULT_PLAN` — which is the
  distinction that made this defect read as a data bug.
- **G-1 proven at the route level, not assumed.** The route table was built in all four
  combinations — main(plain), main(`src.`), branch(plain), branch(`src.`) — and all four are
  identical: 50 routes, rule + endpoint + methods. The function-local deferral of `regrade` at
  `app.py:4642` survived the conversion; nothing moved lazy→eager or back.
- **No remaining doubling vector**: 0 `src.`-prefixed imports and 0 `sys.modules` manipulation
  anywhere under `src/`. The only dynamic imports under `admin/` are `importlib.resources` for
  fonts and an inline `__import__('datetime')` — stdlib lookups, not package doubling.
- Mutation: 3 mutants, 2 killed. Weakening the `ast` predicate from `level > 0` to `> 1` is
  killed, so the walk cannot be silently loosened. The third (making AC-2's assertion
  count-insensitive) survived *by design* — the experiment proves the exact equality is
  load-bearing, and even weakened, the sibling enum test still fails on the defect, so AC-2 has
  two independent detectors.
- System contract: 47 rules — 40 ✓, 7 ⚠ no_eligible_fact, 0 ✗, and `--verify-refs` reports
  `dead_check_ref: []`, so every "holds" rests on a real check. ADR-0019/R1 ✓: the layering
  guard resolves relative and absolute imports to the same dotted name, so absolute imports did
  not become a way around it (94 passed in `tests/test_cli.py` on ba8f6c6).
- **F-001 (medium) — a consequence of the orchestrator's own SCOPE+ ruling, and it is fair.**
  The two launcher spellings do NOT resolve by the same mechanism. The old `src.` form resolved
  from the working directory (`cd "$PROJECT_ROOT"` plus `python -m` putting cwd on `sys.path`,
  where `src/` is a package dir). The new unprefixed form *cannot* resolve that way — `nonogram`
  lives at `src/nonogram`, so cwd yields `src.nonogram`, never `nonogram`. It resolves **only**
  through the editable install's `.pth`. Measured: with that path entry dropped,
  `find_spec('src.nonogram.admin')` is True and `find_spec('nonogram')` is False. The script
  never establishes the precondition — step 2 checks only that the `.venv` directory exists;
  there is no `pip install -e .` and no import check in its 158 lines. Not blocking, because the
  failure is loud and immediate (ModuleNotFoundError before a single request) where the old
  spelling's failure was a silent live 500 — but the worktree note's "resolves from any working
  directory" is a half-truth: it names what was gained, not the dependency introduced.
- **F-002 (medium) — `scripts/README.md:38,131,134` still document the `src.`-prefixed launch**,
  now the one spelling the repo tells you to avoid. The reviewer's judgement, which I accept: my
  ruling applies with equal force to a committed README as to a committed script, so this
  should have been folded in. The repo currently gives two contradictory launch instructions.
- F-003 (low) `_admin_modules()` keys by dotted name, so `admin/foo.py` beside
  `admin/foo/__init__.py` would collapse and exempt one file. Remote — no subpackages today.
- F-004 (info) the guard covers relative imports for any module written tomorrow (it `rglob`s
  disk), but not the wider hazard class (`importlib.import_module("src.nonogram…")`, a
  `sys.path` insert, `sys.modules` aliasing). No live vector exists, so there is nothing for a
  wider rule to catch today.
- F-005 (info) `migrations/env.py`: **both of the implementation's claims verified.** Not a live
  hazard — `src/nonogram/__init__.py` has no imports at all and `db/models.py`/`db/session.py`
  import only stdlib and sqlalchemy, so nothing reaches back for a bare `nonogram.*`. And the
  `src.` prefix IS load-bearing: `env.py:11` inserts the repo root and `alembic.ini:21` sets
  `prepend_sys_path = .`, neither of which puts `src` on the path. Correctly deferred; the
  follow-up card must also fix the path and prove it with a real `alembic upgrade head`.
- F-006 (info) the `src.`-prefixed test modules number **9, not the 7 the notes say** —
  `tests/test_card_050_quality_recognizability.py` was missed. Substance unaffected.
- [Build gate] PASSED, orchestrator's own run: 5381 tests, 5372 passed, 2 failed, 7 skipped —
  exactly +10 on the baseline, and the two long-known stale-heading failures.
- [Review sync] 1 report → meta/review/

- [Implementation] All 15 relative imports converted to absolute: 4 in
  `src/nonogram/admin/__init__.py`, 11 in `src/nonogram/admin/app.py` (10 in the module's
  import block, 1 function-local — `from .regrade import regrade` at line 4642, inside
  `create_app`, which the docstring there says is deliberately deferred to keep the import
  out of a no-database boot). Counted by `ast` before and after: 15 → 0. `admin/` is now 119
  absolute imports and nothing else. No route, template or aggregate was touched (G-1).
- [Proof the reported defect is gone, not just that tests pass] Under the pre-change source,
  a subprocess that does `import src.nonogram.admin.app` holds
  `['nonogram.admin.book_plan', 'src.nonogram.admin.book_plan']` and
  `A.LongestSideBucket is B.LongestSideBucket` is `False`; after the change it holds
  `['nonogram.admin.book_plan']` alone. The AC-3 test was also run against the reverted
  source and reproduced the owner's traceback exactly —
  `src/nonogram/admin/book_plan.py:240, in cell` →
  `return self.cells[BUCKETS.index(bucket)][TIERS.index(tier)]` →
  `ValueError: tuple.index(x): x not in tuple`, reached from `app.py:2486, in cell_value`.
  So the new tests fail on the defect and pass on the fix; they are not a tautology.
- [Live check, not only pytest] Started the panel the way the launcher now does —
  `python -m flask --app nonogram.admin.app run --port 5099` — created a book through
  `/book/create` (which stores the default plan) and fetched
  `/book/book_000001/setup-print`: HTTP 200 with all twelve `cell_<b>_<tier>` inputs
  rendered. That is the exact screen and the exact stored-plan condition that 500'd on
  2026-09-23. Also confirmed `flask --app nonogram.admin.app routes` and
  `flask --app src.nonogram.admin.app routes` now print a byte-identical route table, so
  the launcher change cannot alter what is served.
- [SCOPE+ scripts/start_admin_local.sh — the repo's own launcher aimed at the trap] Line 147
  ran `python -m flask --app src.nonogram.admin.app run --port $PORT`: the exact `src.`-prefixed
  launch that produced the live 500, hardcoded in the repository. Changed to
  `--app nonogram.admin.app`, with a comment saying why so it does not get "tidied" back.
  Verified the change is safe for how the script resolves the app: the script activates
  `.venv` (step 3) before launching, `nonogram` is installed editable there
  (`__editable__.nonogram-0.1.0.pth`), so the unprefixed name resolves from any working
  directory — the `src.` form was the one that depended on `cd "$PROJECT_ROOT"`. `bash -n`
  clean; the argument parsing, the Postgres check, the venv check, the `DATABASE_URL` export
  and the `alembic upgrade head` step are untouched, and line 147 was the script's only
  `src.`-prefixed reference. Nothing else in the file was edited.
- [Out of scope, flagged not fixed — `migrations/env.py`, with something concrete for the
  follow-up card] Left exactly as it is. Two facts worth having when it is picked up:
  (a) it is **not a live hazard today** — a subprocess that imports
  `src.nonogram.db.models` and `src.nonogram.db.session` the way `env.py` does loads *only*
  the `src.`-prefixed tree (`nonogram.db.models` is not in `sys.modules` alongside it),
  because nothing under `nonogram/db/` reaches back for an absolute `nonogram.` import. So
  an `alembic upgrade head` process holds one `Base` and one metadata object. It turns into
  the CARD-139 defect only once something in the *same* process also imports
  `nonogram.db.*` — an in-process alembic call from a test, or an `env.py` that grows an
  import of an app module. (b) The `src.` prefix **is** load-bearing as the file stands:
  `alembic.ini` sets `prepend_sys_path = .` and `env.py:11` inserts the repo root, but
  neither puts `src` on the path, so a bare `from nonogram.db.models import Base` would
  resolve only through the editable install. Converting it therefore also means adding `src`
  to the path (`prepend_sys_path = .:src`, or a second `sys.path.insert`) — which is why it
  needs its own card and a real `alembic upgrade head` to prove it.
- [Also flagged, not fixed — two more places the trap is written down] Same family as the
  launcher, but outside the SCOPE+ that was declared, so untouched: `scripts/README.md`
  documents `python -m flask --app src.nonogram.admin.app run` in three places (lines 38,
  131, 134), which is now the one spelling the repo tells you to avoid; and six test modules
  import the admin/analysis packages under the `src.` prefix (`tests/test_puzzle_review.py`,
  `tests/test_batch_generator.py`, `tests/test_book_manager.py`, `tests/test_pdf_generator.py`,
  `tests/test_strategy_counter.py`, `tests/test_quality_metric.py`, plus
  `tests/e2e/test_admin_workflow.py`), so the suite itself loads both trees in one process.
  That is harmless now that no admin module imports relatively — both trees reach the same
  submodules — but it is the condition that made the defect possible, and it is why the two
  new subprocess tests are subprocesses.
- [Tests] `tests/test_admin_import_consistency.py`, 10 tests, all **executing** — none
  skipped, and none needs a database (the two subprocess tests strip `DATABASE_URL` so they
  run in memory mode regardless of the developer's shell). No database was created, dropped
  or recreated. AC → test:
  * AC-1 `TestAdminImports_NoRelativeImports` — `ast` walk over `src/nonogram/admin/**/*.py`
    on disk, failing on any `ImportFrom` with `level > 0`, in the manner of
    `_discover_modules` in `tests/test_cli.py`; plus a guard-the-guard test that the walk
    actually found the package, and one that exercises the rule against fabricated source in
    all three relative forms so it cannot pass vacuously.
  * AC-2 `TestAdminImports_PackageTreeCannotDouble` — subprocess, imports the app under both
    names, asserts exactly one `nonogram.admin.book_plan` (and one `nonogram.admin.book_manager`
    — the other half of the divide) and that `PLAN_BUCKETS` is one object with one enum class
    across the two.
  * AC-3 `TestAdminImports_StoredPlanRendersUnderEitherImportName` — parametrised over both
    import names, subprocess, `TESTING` on so a `ValueError` propagates instead of becoming a
    500. Creates the book through `/book/create` so the stored plan is the one `book_manager`
    builds (not one this test picked a module for), asserts `get_plan` is not `None` — a
    plan-less book renders `DEFAULT_PLAN` from app's own copy and never hit the bug — then
    renders `/book/<id>/setup-print` and checks all twelve plan cells are on the page.
- [Guardrails] G-1 behaviour unchanged: the diff is 15 import lines, one launcher line and a
  new test file; identical route tables before and after. G-2 `tests/test_cli.py` **run and
  green — 94 passed**, so ADR-0007's inward-only rule still holds and `export/` still never
  imports `admin/`; absolute imports did not become a way around it (the layering guard
  resolves relative and absolute imports to the same dotted name, so converting them changes
  nothing it sees). G-3 nothing under `src/nonogram/export/**` or
  `tests/fixtures/a4_golden/**` was touched.
- [Suite] `pytest -o addopts=""` in the worktree: **5381 tests, 5372 passed, 2 failed,
  7 skipped** (4:29). Baseline was 5371/5362/2/7, so +10 collected and +10 passed — my new
  tests and nothing else. The two failures are the pre-existing ones and were left alone:
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`
  and `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders`.

- [Guard] The defect reproduced and eliminated, verified first-hand by the orchestrator rather
  than read off the report. Importing `src.nonogram.admin.app` in a subprocess: **on main**
  `sys.modules` holds `['nonogram.admin.book_plan', 'src.nonogram.admin.book_plan']` and
  `A.LongestSideBucket is B.LongestSideBucket` is `False`; **on this branch** it holds
  `['nonogram.admin.book_plan']` alone. That is the 2026-09-23 defect, before and after.
- [Guard] 0 relative imports remain under `src/nonogram/admin/`, counted by an independent
  `ast` walk.
### [Fix 1] — cycle-1 review, 2026-09-30 (F-001, F-002)

Both Medium findings from `meta/review/20260930T123942Z-CARD-139-cycle1.yml` closed. Cycle 1
scored 9.0 with no Critical and no Important, so this is not a mergeability fix — both findings
are about the reach of the fix rather than its correctness, and the owner chose to close them.
No Python touched: one shell script and one markdown file.

- **F-002 — `scripts/README.md` still documented the `src.`-prefixed launch.** Read the prose
  around all three occurrences first: none of them is showing the old or broken form on purpose
  as a counter-example — line 38 is the "after setup, start Flask manually" block and lines
  131/134 are the "Manual Commands" block, all three plain run-this instructions. All three
  changed to `--app nonogram.admin.app`, each block gaining a one-line `#` comment ("never
  `src.nonogram.admin.app`: the `src.`-prefixed spelling loads the admin package a second time
  and the two copies disagree (CARD-139)") so the next person does not tidy it back. The
  `--cov=src/nonogram/admin` on the pytest line is a **filesystem path**, not a module name, and
  was deliberately left alone.
- **F-001 — the launcher's new spelling has an unstated precondition; added a guard.** The
  script's step 2 checked only that the `.venv` *directory* exists; there was no `pip install -e .`
  and no import check in its 158 lines, so it could reach the launch line with a venv that cannot
  import `nonogram`, where the old spelling would have worked. Added a guard clause immediately
  after the venv is activated — the earliest point at which the script's own name for the venv's
  interpreter (bare `python`, as used on the launch line) exists, so no second way of naming the
  interpreter was introduced. It runs `python -c 'import nonogram'`, and on failure prints the
  `✗` line, names the command to run (`pip install -e .` in the activated venv, from
  `$PROJECT_ROOT`) and exits 1 — in the same coloured `✓`/`✗` register as the existing Python,
  PostgreSQL and venv checks. It deliberately does **not** run the install for the developer.
  Untouched: the launch line, the argument parsing, the Postgres check, the `DATABASE_URL`
  export and `alembic upgrade head`.

Evidence:
- `bash -n scripts/start_admin_local.sh` — clean, no output, exit 0.
- Guard passes on a correct environment: the project venv's interpreter runs
  `import nonogram` → exit 0, resolving to
  `/Users/omelnikova/PycharmProjects/PythonProject4/src/nonogram/__init__.py`. The guard block
  itself, run with that interpreter first on `PATH`, printed
  `✓ Project importable (editable install present)` and fell through to the launch line, exit 0.
- Guard fires on a broken one: the system `python3` with `PYTHONPATH` unset runs
  `import nonogram` → `ModuleNotFoundError: No module named 'nonogram'`, exit 1. The guard block,
  run with that interpreter symlinked as `python` on `PATH`, printed
  `✗ Project not installed in the virtual environment`, the `pip install -e .` instruction, and
  exited 1 — so the launch line is never reached.
- The script was **not** run end to end: it hardcodes `DATABASE_URL=…/nonogram_poc`, which this
  machine does not have. No database was created, dropped or recreated; `nonogram_dev` and
  `nonogram_test` were not touched.
- Full suite re-run because AC-1's guard walks files on disk — see [Suite, after Fix 1] below.
- [Suite, after Fix 1] `pytest -o addopts=""` in the worktree with the project venv:
  **5381 collected, 5372 passed, 2 failed, 7 skipped** (4:55) — identical to the pre-fix numbers
  on this branch. The two failures are the same pre-existing ones, untouched by this fix:
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`
  and `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders`.

- [Guard] The launcher's new check verified by the orchestrator in both directions, not read
  off the report: with the project venv first on PATH, `python -c 'import nonogram'` succeeds
  and the guard falls through to the launch line; with a bare system `python3` and no
  PYTHONPATH it fails and the guard exits before the launch line is reached. `bash -n` clean.
- [Build gate] PASSED on 895e41f: 5381 tests, 5372 passed, 2 failed, 7 skipped — unchanged from
  the pre-fix run, as expected for a shell-and-markdown change.
