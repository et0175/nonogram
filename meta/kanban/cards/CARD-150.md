# CARD-150: The local launcher refuses a database it cannot use, instead of starting anyway

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/150-launcher-honest-database
**Worktree:** —
**Source:** owner, 2026-10-01 ("нагадай ще раз, як запустити локально" — the answer turned out to be "not with this script")
**Idea:** —
**Wave:** 28
**Depends on:** —
**Touches:** scripts/start_admin_local.sh, scripts/README.md, tests/test_start_admin_local.py
**Review score:** 8.0 (1 cycle + fix)
**Started:** 2026-10-01T10:15:00Z
**Closed:** 2026-10-01T17:05:00Z
**Actual:** 0.3d
**Merge commit:** 0aab707
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
- [Env] forge 2026.8.17
- [Runs alone] Nothing else is in flight; waves 26 and 27 are both complete and every worktree
  from them removed.
- [Testing a shell script is the novel part of this card] The repo has no precedent for it —
  `tests/` holds Python only, and CARD-139's review noted this file had no test and correctly
  left that out of scope. So the first real decision is **how** to test it, not what to assert.
  Driving the script end to end is not possible here: it ends in `flask run`, which does not
  return. Prefer testing the decisions in isolation — the database check, the `DATABASE_URL`
  precedence, the migration's failure path — over trying to run the whole thing.
- [The one database fact that makes AC-1 testable without touching anything] Connecting to a
  database that does not exist **fails**; it does not create one. So AC-1 can be exercised
  against a name that is certainly absent, with no risk to `nonogram_dev`, `nonogram_test` or
  `nonogram_poc`.
- [Measured today, so the agent need not re-derive] `nonogram_dev` and `nonogram_test` exist on
  this machine; **`nonogram_poc` does not**, which is why the defect is visible here at all.

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

### Cycle 1 review (2026-10-01)

- [Review 1/3] **8.0** · risk LOW · lane FAST ·
  `meta/review/20261001T155452Z-CARD-150-cycle1.yml` · 0 critical, **2 important**, 5 minor.
  Not merging this cycle; both gating findings are one-line fixes. The shipped script is
  correct — the reviewer verified its three decisions live.
- **F-001 (important) — the card's own fix is unverified, and the mutant proving it survives
  all 18 tests.** Dropping `2>&1` from `MIGRATION_OUTPUT="$(alembic upgrade head 2>&1)"`
  reintroduces exactly the defect this card removes (alembic's message discarded, printed as
  `(no output)`) and **18 passed**. Reproduced independently by the orchestrator. The mechanism
  is the harness's own: the alembic stub writes to stderr and the test's `Run.output` is
  `stdout + stderr`, so the message is in `run.output` whether the script quoted it or it merely
  leaked past. This is the sole test for that clause.
- **F-002 (important) — AC-4's own fix added a false sentence, and it is this card's defect
  class reintroduced one section above where it was removed.** The new Prerequisites bullet
  says unqualified that "a `DATABASE_URL` you exported yourself wins over it". `## Prerequisites`
  governs `## Scripts`, which documents **three** scripts; it is true of one.
  `setup_admin_local.sh:64` and `run_admin_tests.sh:24` both still overwrite the caller — and
  **`setup_admin_local.sh` still carries all three original defects verbatim**: the bare
  `psql -c "SELECT 1"` (:40) and the swallowed migration (:70-74). AC-4's suite cannot see it,
  because every README test drives only `start_admin_local.sh`.
- **[Correction to the orchestrator's own reporting] The "14 of 18 fail against the original"
  figure is an artifact.** The reviewer confirmed the number and then explained it: the original
  script has no `--check-only`, so it exits at argument parsing — `Unknown option: --check-only`
  appears 22 times — and **13 of the 14 fail for that reason, not the defect's**. Only
  `test_refuses_before_starting_anything`, the one flag-free test, fails for the real reason.
  The targeted mutants are the honest measure: 3 of 4 killed.
- The harness itself was judged sound and **not** a simulation: it copies the real file and runs
  it with `bash`, and the hazard of a `docker` stub silently taking the Docker path is
  *deliberately inverted* — the stub exits 1 for both `docker` and `docker-compose`, so every
  run falls through to the Homebrew branch the defect lived in. Confirmed by the call log and by
  M1 killing 5 tests.
- AC-1's guard is honest but a **proxy**: it asserts on recorded argv, so
  `PGDATABASE=nonogram_poc psql -c "SELECT 1"` — correct — would fail it, while
  `psql -U postgres -d nonogram_poc` passes while discarding the URL's host, port and
  credentials, which is what the two Docker branches do. Errors run in the safe direction.
- The migration change's reasoning was accepted: `--no-migrate` pre-exists, is documented, is
  named in the refusal and is tested, so no new "continue anyway" flag was needed — a
  migrate-then-ignore mode *is* the default this card removes. The capture is correct shell
  (an assignment's status is the substitution's; a command in an `if` is exempt from `set -e`).
  One caveat worth knowing: capturing means a long migration now prints nothing until it ends.
- `--check-only` judged a genuine operator affordance rather than test-only scaffolding, and it
  does run all six steps. But the implementation's claim that "the tests do not depend on it" is
  **false for the committed suite** — 16 of 18 pass the flag, and the flag-free before/after
  harness it cited is not in the diff.
- G-2 ✓ measured after the work: only `nonogram_dev` and `nonogram_test` exist, `nonogram_poc`
  still absent, `nonogram_test` at revision 013 with every table at 0 rows. G-3 ✓ the launch
  target is unchanged and CARD-139's editable-install check survives. 18 tests, **0 skipped, no
  `skipif`/`importorskip` anywhere** — the "DB tests skip silently" hazard did not reappear.
- [Model defect, sharper than previously recorded] `--verify-refs` reported
  `dead_check_ref: []` with `check_refs_verified: true` while **4 of the 5 assembled refs** do
  not exist as declarations. The reviewer also found *why*: the convention is that the model's
  ref name lives in a test file's **docstring**, mapping to a differently-named declaration
  (`tests/test_clues.py:8`). So the properties are covered and **the refs are what is dead** —
  which makes the backlog card's job clearer than it was.
- [Review sync] 1 report → meta/review/

### Orchestrator gates (2026-10-01)

- [Build gate] PASSED on 8af5d0f: **5557 collected, 5548 passed, 2 failed, 7 skipped** — the
  5539 baseline plus exactly the card's 18, and the two long-known stale-heading failures.
- [Guard] The defect reproduced and the fix verified by the orchestrator, running **both**
  scripts against a genuinely absent `nonogram_poc` (only `nonogram_dev` and `nonogram_test`
  exist here), with `PGDATABASE=postgres` to expose the bare check:
  - **old** → `✓ PostgreSQL is running (Homebrew)` — a green tick for a database that is not
    there. It stopped later only because this worktree has no `.venv`; on a machine with one it
    would have gone on to serve a panel whose every database read fails.
  - **new** → `✗ Database 'nonogram_poc' is not reachable`, naming the URL, its source, and
    "This script does not create a database.", exit 1, before the venv step.
- [Guard] G-2 verified after the work rather than taken on trust: the only databases present are
  still `nonogram_dev` and `nonogram_test`, `nonogram_poc` was **not** created, and
  `nonogram_test` is still at revision **013** with **0** rows. Nothing was created, dropped,
  seeded or migrated.
- [Note] 18 tests, all executing, **none needing PostgreSQL** — which matters here more than
  usual: a test that silently skipped without a database would have been this project's known
  "DB tests skip silently" hazard reappearing inside the very card about a database check.
### [Fix 1] — review cycle 1, the two Important findings (score 8.0)

- [F-001, the mutant that survived] The reviewer's M3a — dropping `2>&1` from
  `MIGRATION_OUTPUT="$(alembic upgrade head 2>&1)"` — passed all 18 tests, so
  AC-3's message clause was unverified. Reproduced, and the cause is the
  harness, not the script: `_ALEMBIC_STUB` writes its message with
  `printf … >&2` and `Run.output` was `stdout + stderr` concatenated, so
  alembic's message is in `run.output` whether the script *quoted* it or it
  merely *leaked past* the script to the terminal — which is the entire
  distinction AC-3 is about. `Run` now also carries `stdout` and `stderr`
  separately (`output` is unchanged, so every existing assertion stands), and
  `test_alembics_own_message_reaches_the_output` keeps its old assertions and
  adds two the leak cannot satisfy: each line of alembic's message in the
  **four-space-indented** form only the script's own `sed 's/^/    /'` can
  produce, asserted against the script's **stdout**, and `"(no output)" not in
  run.output`. Measured: mutant applied → `1 failed, 18 passed`
  (`assert "    FAILED: …" in run.stdout` fails, with stdout showing
  `    (no output)` and the message in stderr); script restored (sha1
  `ba6aeb47c164f083ed529f4f0aa3e5a8df8e395d`, byte-identical, `git diff` empty)
  → `19 passed`. The script was not changed: it was already correct.
- [F-002, the false sentence] The new Prerequisites bullet claimed,
  unqualified, that "a `DATABASE_URL` you exported yourself wins over it".
  `## Prerequisites` governs `## Scripts`, which documents three scripts, and
  it was true of one. Read all three: `start_admin_local.sh` resolves the URL
  above the banner and honours an exported value (`DATABASE_URL_SOURCE`);
  `setup_admin_local.sh:64` and `run_admin_tests.sh:24` both still
  `export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"`,
  overwriting the caller. The sentence is now scoped to the script it holds
  for and says plainly that the other two do not honour it. Fixing them is a
  separate card, deliberately not widened into this one. The companion claim
  "**The scripts never create a database**" is true of all three (no
  `createdb`/`CREATE DATABASE` anywhere in `scripts/`) and is untouched.
- [An assertion for the scripts the suite never runs] The reviewer's note that
  AC-4's suite cannot see this class of error — every README assertion is
  driven from a run of `start_admin_local.sh` only — was cheap to answer:
  `test_a_claim_about_the_scripts_names_the_script_it_holds_for` reads the
  *source* of every script the README documents under a `###` heading, and for
  each one that `export DATABASE_URL=`s over the caller requires Prerequisites
  to name it. Mutation-proved both ways: the old unqualified sentence restored
  → that test fails; the scoped sentence → passes. It relaxes by itself as the
  siblings get fixed, and it does not run them (G-2 untouched).
- [What was not touched] F-003 through F-007 are left open on purpose, as are
  `setup_admin_local.sh`, `run_admin_tests.sh` and the four dead check refs in
  the model. The diff is `scripts/README.md` and
  `tests/test_start_admin_local.py` only. `bash -n scripts/start_admin_local.sh`
  clean; 19 tests in the file, all executing, none skipped; `nonogram_poc` still
  absent and `nonogram_test` still at 013 with 0 rows.

- [Guard] F-001's repair verified by the orchestrator with the same mutant: dropping `2>&1`
  from the alembic capture **survived all 18 tests** before, and now fails exactly
  `test_alembics_own_message_reaches_the_output`. The script is **byte-identical** across the
  fix commit — the defect was in the test's evidence channel, which is where it was repaired.
- [Guard] The fix did not widen: rather than making `output` stdout-only (which would have
  retargeted the other 17 assertions), it added `stdout`/`stderr` as separate fields and
  asserted the four-space-indented form only the script's own `sed` can produce, against
  **stdout** — so a stub writing to stderr can never satisfy it.
- [Build gate] PASSED on dfe07db: **5558 collected, 5549 passed, 2 failed, 7 skipped** — the
  5557 baseline plus the one new test, and the two long-known stale-heading failures.
- [Guard] G-2 re-checked after the work: only `nonogram_dev` and `nonogram_test` exist,
  `nonogram_poc` still absent, `nonogram_test` still at revision 013.
