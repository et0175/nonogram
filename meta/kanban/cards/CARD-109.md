# CARD-109: The suite writes to whatever DATABASE_URL points at

**Status:** review
**Priority:** P1
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** red -> green; the guard is watched in a subprocess
**Branch:** card/109-suite-refuses-a-foreign-database
**Worktree:** ../PythonProject4-CARD-109
**Source:** observed twice on 2026-09-21 while working on CARD-107
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** tests/conftest.py (the guard), tests/e2e/test_admin_workflow.py, tests/test_admin_image_uniqueness.py, tests/test_admin_regrade.py, tests/test_card_050_quality_recognizability.py
**Review score:** —
**Started:** 2026-09-21
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

`create_app()` reads `DATABASE_URL` and goes to whatever it names. Most tests
clear it first; **four do not**, and they do not mean to use a database at all.

Measured on `main` at `20efa41`:

| | |
|---|---|
| test files calling `create_app()` | 28 |
| clear `DATABASE_URL` first | 25 |
| carry the `db_required` marker (opt-in, skips when unset) | 1 — `test_db_e2e_smoke.py` |
| **pick it up silently** | **4** |

The four: `tests/e2e/test_admin_workflow.py`,
`tests/test_admin_image_uniqueness.py`, `tests/test_admin_regrade.py`,
`tests/test_card_050_quality_recognizability.py`.

So a developer with `DATABASE_URL` exported — which is exactly the shell you
are in after running the membership backfill or an alembic upgrade — runs the
suite and those four tests read and write that database. Nothing warns.

**Both halves were seen on 2026-09-21**, neither of them hypothetical:

* A stray `books` row titled `c1` was left in the development database by a
  test run. Noticed only because CARD-107's cleanup counted what was left.
* Four e2e tests failed — `test_tc_006_download_svg_file` and three siblings —
  immediately after that database was emptied mid-session. They were reading
  it. A clean run passed all seventeen.

The second is the shape that matters: **the suite's result depended on the
contents of a database nobody told it about.** Green or red became a property
of the shell, not of the code.

`tests/test_admin_regrade.py` deserves its own sentence. CARD-077's regrade
rewrites every stored grade, and its guardrail G-1 is that it is never run
against live data. That guardrail is enforced by the card, not by the code —
and this is the path by which a test file about it could reach a real database.

## What to implement

1. **A guard in `tests/conftest.py`** that refuses to run against a
   `DATABASE_URL` the suite did not choose. The shape is the decision below.
2. **The four files clear it**, like the other twenty-five, because none of
   them wants a database — that is the local fix, and it should land whatever
   the guard turns out to be.
3. **`db_required` keeps working.** `test_db_e2e_smoke.py` opts in
   deliberately and skips when the variable is unset; the guard must not break
   the one case that is doing this on purpose.

## The decision this card needs (for the owner)

How strict should the guard be?

- **(a) Refuse anything but a known-test database.** A session-scoped
  autouse fixture aborts the run unless `DATABASE_URL` is unset, or names a
  database matching a test pattern (`…_test`, or `TEST_DATABASE_URL`'s value).
  Loudest and safest: it is impossible to run the suite against production by
  accident. Costs a deliberate opt-out for anyone who genuinely wants to point
  the suite at something else.
- **(b) Neutralise it instead of refusing.** An autouse fixture unsets
  `DATABASE_URL` for every test that has not asked for a database via
  `db_required`. Nothing to remember, no way to trip it, and the four files
  need no change at all. But it hides a real mistake rather than reporting it —
  a developer who *meant* to test against their database gets silence.
- **(c) Warn only.** Print a banner in `pytest_report_header` naming the
  database the run can reach. Cheapest, changes no behaviour, and would have
  made both of 2026-09-21's incidents obvious within a second of reading the
  output — but it does not stop anything.

**Recommendation: (a) with (c).** Refuse by default, and say in the header
which database the run considered and what it decided, so the refusal is never
mysterious. (b) is tempting and wrong for the same reason `except Exception:
pass` was wrong in CARD-104: silently absorbing a mistake is how it stays
invisible.

## Acceptance criteria

- **AC-1** — with `DATABASE_URL` naming a database that does not look like a
  test database, the suite refuses to start (or, under the chosen option,
  neutralises it) rather than reading it.
- **AC-2** — with `DATABASE_URL` unset, everything behaves exactly as it does
  today; the suite's count is unchanged.
- **AC-3** — `db_required` tests still run when a database is reachable and
  still skip when it is not.
- **AC-4** — the four files above no longer reach a database at all, shown by
  running the suite with `DATABASE_URL` set to a *reachable* database and
  observing that nothing is written to it.
- **AC-5** — the guard's own behaviour is tested, not just asserted — a test
  that sets a hostile `DATABASE_URL` and watches the guard act.

## Guardrails

- G-1: Do not weaken `db_required`. The one deliberate opt-in keeps working.
- G-2: No production code changes. `create_app` reading `DATABASE_URL` is
  correct; the problem is the suite, not the application.
- G-3: The guard must not itself connect to the database to decide. Reading
  the URL is enough, and a connection is what CARD-097 spent a card making
  safe.
- G-4: Commit only your own files — explicit pathspecs.

## Architecture context

- **FR:** — (test infrastructure)
- **Components:** the test suite
- **Trace:** none

### Correction, 2026-09-21 — this card overstated the scope fourfold

The Why above says **four** files pick up `DATABASE_URL` silently. **One does.**
The count came from grepping for `delenv("DATABASE_URL"` and treating its
absence as exposure, which is the same error this suite made about class names
twice today. Looked at properly:

| file | what it actually does |
|---|---|
| `tests/e2e/test_admin_workflow.py` | **nothing** — genuinely exposed |
| `tests/test_admin_image_uniqueness.py` | cleared it with `os.environ.pop` |
| `tests/test_card_050_quality_recognizability.py` | cleared it with `os.environ.pop` |
| `tests/test_admin_regrade.py` | **sets** its own SQLite URL via monkeypatch |

The evidence agreed all along and I did not read it: every one of the four
failures on 2026-09-21 was in `test_admin_workflow.py`. Had the other three
been exposed, the damage would have been wider.

The Why is left as written, with this correction beneath it, because a card
that quietly restates its own reasoning is worth less than one that shows where
it was wrong.

### Delivered

**The guard** — `tests/database_guard.py`, wired into `conftest.py`'s
`pytest_configure` so it stops the run before collection. It refuses unless
`DATABASE_URL` is unset, or names a database whose name contains `test`, or
`NONOGRAM_ALLOW_FOREIGN_DATABASE` is set. Option (a) with (c), as the card
recommended: it refuses, and the run header says what it decided when there is
anything to say.

It **never connects** (G-3) — the name is enough, and a connection is what
CARD-097 spent a card making safe to avoid. It **never echoes the credential**:
a refusal is printed and printed things get pasted, so only the database name
appears. A test asserts that with a distinctive username and password, after an
earlier version of it used "admin" and failed on the refusal's own prose.

**The one exposed fixture now clears the variable**, and the two that used
`os.environ.pop` use `monkeypatch` instead — popping cleared it for the rest of
the session rather than the test, so whether a later test saw a database
depended on whether an earlier one had run. That is order-dependence hiding
inside a fix, and it has its own test now.

**`pytest_report_header` is composed, not replaced.** The conftest imported
that name from the hang guard; defining another would have silently dropped it,
and the hang guard's line is how a killed run's stack dump is findable. Both
lines are emitted.

### Tests

`tests/test_card_109_database_guard.py`, 19 tests. The rule itself over
realistic URLs — including the Render-style host and the neighbouring
`mealplanner` database on the same server — and three that **run pytest in a
subprocess** and watch it refuse, succeed under the opt-out, and print the
header. AC-5 asked for the guard to be watched rather than asserted, and a
function returning `False` is not the same as a run stopping.

**Full suite: 3,691 passed, 0 failed.**
