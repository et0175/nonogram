# CARD-349: `db_required` gates the create-if-missing path but not the reading of `DATABASE_URL`, so an unmarked test reds in a fresh worktree and self-heals

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Measured by CARD-278's merge gate, 2026-11-04, which went red at 5 cells on its first armed run in a file byte-identical to main's and belonging to a card whose entire footprint was `tests/test_timeout.py`. The gate measured the cause instead of re-running, which is the only reason this is a card rather than a shrug — the hazard self-heals, so the second run is green and the first reads as flakiness.
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/conftest.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, measured at a gate rather than theorised

`conftest.py`'s create-if-missing path for the per-worktree test database is gated on the
**`db_required` marker**. The *reading* of `DATABASE_URL` is not. So a test that reads
`DATABASE_URL` without carrying `db_required` enables DB persistence and **connects** before
any marked test has created the database.

Observed at CARD-278's gate, first armed full run:

```
FATAL: database "nonogram_pythonproject4_card_278_a6c1379e5711_test" does not exist
```

All five failures were one parametrized class,
`tests/test_admin_binding.py::TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine::test_a_request_addressed_to_this_machine_is_served[...]`,
in a file **byte-identical to main's**. Re-run after a marked test had created the database:
**14 passed**.

**Re-derive all of this before implementing.** The class name, the count and the marker's
gating are dated readings, and a different result is the finding.

## Why it needs a card and not a note: it is the self-healing signature again

**This is a sibling of the stale-schema hazard and demonstrably not that hazard.** The gate
distinguished them rather than assuming:

| | stale schema (CARD-338's gate) | this one (CARD-278's gate) |
|---|---|---|
| signature | missing **column** — `psycopg2 UndefinedColumn: books.player_domain` | missing **database** — `FATAL: database "…_test" does not exist` |
| cause | per-worktree DB predates a migration that landed that day | derived DB has never been created, and an unmarked test connects first |
| check that settles it | test DB's `alembic_version` against `head` | does the database exist at all |

A migration *had* landed recently (CARD-332, 2026-11-01), which is exactly when the
stale-schema hazard is live — so the obvious attribution was available and wrong. The gate
checked `information_schema` and found `books.player_domain` **already present**: the schema
was current and the database was simply absent.

**Both hazards red the first run and self-heal.** That is the worst signature a test suite can
have, because it trains a re-run instead of a look. Two of them now exist, one marker apart.

## What to implement

1. **Decide where the coupling belongs**, and say which you chose:
   - make the database's existence a **precondition of reading `DATABASE_URL`** rather than of
     the `db_required` marker, so the ordering cannot matter; or
   - make the create-if-missing path **eager** (session start) rather than lazy; or
   - **refuse loudly** when `DATABASE_URL` is armed and the derived database does not exist,
     turning a confusing red into a named one.
   The third is the cheapest and the weakest; the first removes the hazard. Measure before
   choosing — the lazy path exists for a reason and the card does not assume it is wrong.
2. **Derive the exposed set rather than listing it.** Which tests read `DATABASE_URL` without
   carrying `db_required`? Enumerate by `ast`/marker inspection, not by grep, and report the
   count. If it is one class, say so; if it is twenty, the fix's shape changes.
3. **Leave the two-gate structure intact.** The bare-`DATABASE_URL` check and the per-worktree
   `*_test` resolution are deliberately distinguishable; CARD-278's gate used that
   distinguishability to attribute its skips (1 skip armed, 0 from either DB gate). A fix that
   merges them loses a diagnostic the board relies on.
4. **Do not widen `_refuse_unless_test_database`.** It refuses by URL text, before connecting,
   any database not ending in `_test`. That is what keeps `nonogram_poc` out of reach.

## Acceptance criteria

- **AC-1** *Given* a worktree whose derived `*_test` database does not exist and
  `DATABASE_URL` armed, *then* the suite either creates it before any test reads
  `DATABASE_URL`, or **fails with a message that names the missing database and what to do** —
  not a bare `psycopg2` `FATAL`. Demonstrated by dropping the derived database and running.
  (test: named by the implementation; state it)
- **AC-2** *Given* the exposed set, *then* it is **derived** from the marker and the
  environment read rather than hand-listed (ADR-0039/R2), and its size is stated.
  (test: named by the implementation; state it)
- **AC-3** *Given* the fix, *then* the **second** run is not the first run's rescue: running
  twice from the same cold state gives the same result both times. The self-healing signature
  is the defect, so its absence is the acceptance.
  (test: named by the implementation; state it)
- **AC-4** *Given* the two DB gates, *then* they remain separately attributable — a skip or a
  red still says which one fired. CARD-278's gate's attribution (1 skip, `setrlimit`; 0 from
  the bare-`DATABASE_URL` check; 0 from per-worktree resolution) must still be derivable.
  (test: named by the implementation; state it)
- **AC-5** *Given* `_refuse_unless_test_database`, *then* it is neither widened nor bypassed,
  and a non-`_test` database name is still refused **by URL text before connecting**.
  (test: the existing refusal test; name it)

## Guardrails

- **G-1** — **Do not connect to the production database.** The live panel runs on
  `nonogram_poc`. Never create, drop, connect to or truncate it. This card edits the very
  machinery that protects it, so say explicitly what you verified.
- **G-2** — Do not make a red quieter by skipping it. ADR-0038/R8: tests fail or skip
  **loudly**. Turning this into a silent skip converts a self-healing red into a permanent
  false green, which is strictly worse.
- **G-3** — No new runtime dependency (ADR-0006/R1).
- **G-4** — Take no timing measurements and report no durations; other work shares the machine.
- **G-5** — A full suite needs the board's lock (`meta/kanban/.full-suite.lock`, structured,
  identity is the **worktree**, no pid). Never set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, and
  never redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard fires in `pytest_configure` for **any**
  selection, so a redirect blinds a file-scoped run to a gate that is holding the lock.

## System contract

- ADR-0038/R8 — tests fail or skip loudly, never silently (check: review-lens)
- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate
  (check: review-lens)
