# CARD-349: `db_required` gates the create-if-missing path but not the reading of `DATABASE_URL`, so an unmarked test reds in a fresh worktree and self-heals

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/349-db-required-misses-the-url-read`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-349
**Source:** Measured by CARD-278's merge gate, 2026-11-04, which went red at 5 cells on its first armed run in a file byte-identical to main's and belonging to a card whose entire footprint was `tests/test_timeout.py`. The gate measured the cause instead of re-running, which is the only reason this is a card rather than a shrug — the hazard self-heals, so the second run is green and the first reads as flakiness.
**Idea:** —
**Wave:** 78 <!-- DISPATCHED 2026-11-04T20:25Z as wave 78's ONLY card. SOLO on the owner's confirmed order ("wait for 363 then open 78 on 349 solo", recorded in dispatcher.state), and the reason is measured rather than preferred: Touches is tests/conftest.py, the highest blast-radius file in the tree, so this card serializes against CARD-320 (which also touches it) AND against any card whose gate runs a suite. Was: no wave. The queue comment read "wave 76" and that attribution is withdrawn -- the card was never dispatched into 76, which closed on CARD-348 alone. Estimate was ALREADY 1c (0.5d), restated in review cycles before this open rather than at it, so wave 78's ratio is computable from the outset -- the scarce input CARD-363 merged to protect. -->
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/conftest.py
**Review score:** —
**Started:** 2026-11-04T20:25Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, measured at a gate rather than theorised

> **PREMISE VERIFIED AT THE STATION, 2026-11-04 — and it is SHARPER than this card states.**
>
> Measured in `tests/conftest.py` by name, not by line number: the whole create-and-migrate path
> sits inside `if 'db_required' in markers:` in the skip hook, and the `os.getenv("DATABASE_URL")`
> read plus its `pytest.skip` are **inside that same block**. So the card's wording — "gates the
> create-if-missing path but not the reading of `DATABASE_URL`" — is right about the asymmetry but
> wrong about where it lives: **conftest does not read the env var for an unmarked test at all.**
>
> The real asymmetry is between conftest and the test tree. Creation happens **only** for marked
> tests, while an **unmarked** test is free to read `DATABASE_URL` in its own code and connect — and
> many do. **⚠ THAT MECHANISM IS REFUTED — see the round's record below** (ADR-0039/R4). Measured by
> the round and re-derived independently by the orchestrator: **zero** collected test modules read
> `DATABASE_URL` in their own code, and `test_admin_binding.py` — the module that actually reds —
> carries **nine** `db_required` declarations. The exposure is **indirect**, through production
> readers (`create_app`, `_init_engine`, …) reached transitively. **A reference-based census, grep or
> `ast`, cannot find the real exposed set.** The family attribution was right; the mechanism was not.
> The superseded wording follows.
>
> [SUPERSEDED] Measured: of the test modules referencing `DATABASE_URL`, a large set carry **no**
> `db_required` marker anywhere, the `test_admin_*` family prominent among them. **Re-derive that set
> rather than carrying this sentence**; it is the population the fix has to speak about, and a
> census counts references, not declaration sites.
>
> **Two live confirmations, both from gates rather than theory.** CARD-336's gate met this hazard
> and pre-empted it by running the 26 `db_required` tests first to take the create path. CARD-348's
> gate met the **twin** — a per-worktree database at `alembic_version` 017 against a head of 018 —
> in `test_admin_binding.py`, a module that sorts early, never requests `db_session`, and therefore
> read the previous session's schema. Distinguish the two by signature: **missing database** is this
> card; **missing column** is the stale-schema twin. Both self-heal, which is why each reds a first
> run and reads as flakiness.
>
> **Serialization, measured.** `tests/conftest.py` is the highest-blast-radius file in the tree and
> **CARD-320 also touches it**, which is why the owner scheduled both solo and this one first. Do not
> pair this card with anything.

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

## Worktree notes

[Review 1/3] Score: **9.0**, `overall_verdict: fail` — **BACK TO THE ROUND.** Above `min_score: 8`,
but one Important finding and a failing circuit, and certification was `deferred(cost)` with
`mutation_check: true` live, so the card cannot merge on it. Artefact:
`meta/review/CARD-349-cycle1.yml`, **deliberately left uncommitted** — see below. Task contract
**pass** (AC-1..AC-5, G-1..G-5). System contract **fail**: 2 of 3 rules hold, 1 violated.

[Review 1/3] **The Important, and it is grounded by a SURVIVING mutant.** `_armed_database_is_ready`
catches `pytest.skip`/`pytest.fail` from `_test_database_tables` — correctly, since letting either out
of a session-autouse fixture would skip or error the whole suite. The entire safety of that catch
rests on the docstring's claim that the reason *"is recorded and announced instead"*, **and that claim
has no control that can fail**: replacing `_ARMED_SETUP["reason"] = str(stopped)` with `pass` — a
preparation failure swallowed in total silence, which is what G-2 forbids — **survives at 57 passed /
2 skipped / 0 failed.** Violates **ADR-0039/R1**.

[Review 1/3] **The root cause explains why the existing control misses it, and it is a shape worth
naming.** Every note test **splits the mechanism at `_ARMED_SETUP`**: it calls the pure planner for an
`action`, then *hand-injects* `_ARMED_SETUP` by monkeypatch, then asserts on `armed_database_note()`.
Planner tested, formatter tested — and **the fixture body that connects them, the only thing that
writes `_ARMED_SETUP` in a real run, is driven by no test at all.** Its sole appearance in the module
is as a **string** in a name-isolation list. One test closes it: drive the fixture with
`_test_database_tables` raising `pytest.skip.Exception` and assert both the recording and the note.

[Review 1/3] **MY REVIEW ASK IS REFUTED, and it was a text-search reading** (ADR-0039/R4). I recorded
in `3c834922` that *"nothing asserts that conftest's newly-composed `pytest_terminal_summary` still
calls the lock guard's"*. Removing the delegation line is **killed** by two pre-existing tests —
`test_the_override_lets_a_contended_run_through_and_announces_itself` and
`test_a_redirected_real_run_announces_it_in_the_terminal_summary` — which drive **real pytest
subprocesses** and therefore route through conftest's composition. The ask was pointed one line away
from the line that *is* uncovered. The reviewer disclosed that it was its own grep-based reading
first, refuted by its own mutant before it could gate anything. **This is a mutant result the
orchestrator did not re-derive.** What the orchestrator did verify: the branch defines the composed
hook (`tests/conftest.py`, the `pytest_terminal_summary` definition calling
`_full_suite_lock_terminal_summary`) while **main** carries only the bare re-export — so the
orchestrator's own confirming grep had been run against the **wrong tree**, and the round's
description of the change was correct.

[Review 1/3] **The round's self-raised item is VERIFIED rather than accepted, and its fix was better
than restating the figure: it DELETED it.** The fixture docstring now gives no suite count and says
why — `-rEfs` answers it per run — which removes the carried figure instead of refreshing one. And the
derived "29 expected" unarmed now has a **measured input**: the module runs **16 passed / 2 skipped**
unarmed, so 27 + 2 = 29.

[Review 1/3] **System contract, 3 rules.** **ADR-0038/R8 ✓ holds** — nothing is made silent, verified
by reading rather than assumed: `db_session` calls `request.getfixturevalue("_test_database_tables")`,
so pytest re-raises that fixture's cached exception to the later requester, and the announcement
channel is real (its mutant was killed). **ADR-0039/R2 ✓ holds** — default-to-deny explicit and
reachable in `_armed_database_plan`, AC-2's set derived by `ast` with a matched non-vacuity control.
**ADR-0039/R1 ✗ violated** — the finding above. All three carry `check: review-lens`, so no dead-ref
hazard.

[Review 1/3] **AC-3 passes AS RESTATED**, and the reviewer credited the round for naming the defect
rather than silently reinterpreting it: the AC *as written* is satisfied by the defect (two cold runs
red identically), and the round replaced it with a cold run plus the run after it. **G-1 verified
rather than trusted**, as the only code here that destroys anything: `_drop_if_present` asserts four
conditions before `DROP DATABASE` — `_test` suffix, `_refusal_reason` allows it, not this worktree's
own derived name, creatable-name shape — and `nonogram_poc` fails the first two.

[Review 1/3] **Minors.** `_drop_if_present`'s docstring claims the target is "not any database a live
worktree or the live panel owns" while the code checks only **this** repo's derived name — not
exploitable, but an overclaimed safety comment on the one destructive operation. And `Touches` names
`tests/conftest.py` alone while the diff adds an **851-line** test module with `scope_gate: on`;
raised so it stops being decided per card.

[Review 1/3] **Why the artefact is UNCOMMITTED, and it is the measured hazard rather than caution.**
`meta/review/*.yml` is gitignored yet tracked, so committing needs `-f` — and two test names the
report cites (`test_the_suites_own_infrastructure_is_where_the_reads_live`,
`test_the_eager_setup_hides_nothing_from_the_marked_path`) **do not exist on main**, because the card
is unmerged. Committing now would put them into tracked text where the word-bounded search over
tracked files resolves them as **alive** while no such test exists there — precisely the
"review YAMLs revive dead check refs" mechanism. It stays at the conventional path to be committed at
the card's `done` step, after the merge makes the names real.

[Review 1/3] **A declared conflict of interest, and a second reader is already running.** The
reviewer wrote the implementation brief this round worked from, disclosed that its review is therefore
not independent of it, and asked for a second reader anchored elsewhere. The orchestrator had
separately dispatched one, which is running an **armed** full suite under the lock and will write to
`meta/review/CARD-349-cycle1-second-reader.yml`. It was told that a prior reading exists and its
verdict withheld, so it forms its own first. **Coverage the first reviewer disclosed rather than
papered over:** it did not reach `src/`'s production readers, so the round's transitive figures
(4 readers / 10 names / 78 scopes / 19 modules) are **not** independently re-derived by it; it did not
re-run the armed full suite, so the round's 10392 remains the round's own figure and the gate's to
confirm; and it recorded Step 8c as N/A on the measured basis that the impact set reports empty
components and contexts.

[Review 1/3] **Two instrument notes from the reviewer worth keeping.** `mutation_check` was read by
**parsing** `config.yml`, not grepping — the live key sits under a long comment block, and both a
`sed` range over the first part of the `review:` block and a grep would have found it inside commented
history instead. And `reverse_deps` came back **underivable** (`manifest_changed`; the import graph
does not model `tests/conftest.py`), recorded as `no_eligible_fact` rather than letting an empty set
read as a small blast radius — the honest reach is **every collected test**, which is why this card
scheduled itself solo.

[Round, commit `8c108047`] Implemented: two files, `tests/conftest.py` (+223/−1) and the new
`tests/test_card_349_cold_database.py`. INV-023 clean, worktree clean, not merged. **Remedy chosen:
the card's first and second together, with the third as a backstop** — an autouse **session-scoped**
`_armed_database_is_ready` that requests the existing `_test_database_tables` when `DATABASE_URL` is
armed at the URL this worktree resolved. pytest sets up widest scopes first, so it runs before any
test *body*. **It adds no DDL of its own and is not extra work**: `_test_database_tables` is
session-scoped, so this *moves* the one setup rather than adding a second. The third remedy survives
as a `database setup:` terminal-summary note for the three cases eager preparation must not act on —
and it goes to `pytest_terminal_summary` because `addopts = "-q"` hides the header, which is the lock
guard's own reasoning.

[Round] **THE HEADLINE: the card's remedy 2 is a FALSE FIX, measured rather than argued.** With the
database created but **no schema in it**, the same five cells red again with
`psycopg2.errors.UndefinedTable: relation "puzzles" does not exist`, self-healing identically. So
"make the create-if-missing path eager" converts hazard A into hazard B, and the next gate would
misattribute the result to the stale-schema twin's card. Planted as mutant **M2** and killed by two
tests. **Consequence for this card's own two-hazard discriminator table:** it presents the two as
siblings with different causes; measured, hazard B is the **immediate successor** of hazard A under
this card's own proposed remedy. They are two stages of one defect — the derived database not being
brought to a *usable* state before the first unmarked reader. This also explains CARD-258's waves
47/48/50 reds, which carried the `relation "puzzles" does not exist` signature. The table remains a
correct discriminator for **attribution**; its "cause" column for hazard B was incomplete.

[Round] **AC-3 as written is satisfied by the defect.** "Running twice from the same cold state gives
the same result both times" — drop the database before each of two runs and the defect gives
`5 failed, 9 passed` **both times**. Measured, not reasoned: under mutant M1 the original cold/cold
equality assertion **passed**, and only the return-code assertion caught it. The self-healing
signature is cold-red then **warm**-green, so the pair carrying the acceptance is a cold run and the
run *after* it. Rewritten accordingly, with the refutation in the test's docstring.

[Round] **The exposed set, derived rather than listed — and it is 19 modules, not one class.** Direct
runtime reads in collected test modules: **0** (re-derived independently by the orchestrator: 0). The
only readers under `tests/` are three scopes in two files pytest collects no tests from. The
orchestrator's grep calibration reproduced exactly (79 of 215 mention `DATABASE_URL`, 11 mention
`db_required`) and **nearly every one of the 79 is a `monkeypatch.delenv`** — a test taking the
variable away. The real exposure is indirect: **4** direct production readers under `src/`, a
name-keyed transitive closure of **10** reaching names, and **78 scopes across 19 modules** that
reference them without clearing the variable; restricted to `create_app` alone, **18 scopes across 4
modules**. **The derivation is a name-keyed over-approximation, not a proof of reachability** — which
is exactly why the fix does not take the set as input.

[Round] **Marker authority is pytest's own, not text.** `-m db_required --collect-only` collects **0**
items for the exposed class and ≥1 for the whole module as a matched control — and that control
matters, because `test_admin_binding.py` *mentions* `db_required` **nine** times in classes that sit
**below** the exposed class in the same file. **A module-level text census would have called that
module "marked" and missed the defect entirely.**

[Round] **A sharpening that kills the workaround CARD-336's gate used.** The exposed class and the
nine `db_required` tests are in **the same file**, the marked ones below it — so the fix cannot be
"run the marked tests first". That workaround is order-dependent and would not survive
`pytest-randomly`, which is installed in this venv.

[Round] **Full suite with `DATABASE_URL` ARMED, under the lock: 10392 passed / 1 skipped /
1 xfailed**, exit 0. The single skip is the `setrlimit` platform gate; **zero** from the bare-
`DATABASE_URL` check and **zero** from per-worktree resolution. That is the armed prediction exactly
(1 skip, the 26 at zero) — and it **confirms** that CARD-363's two suites were unarmed, which was the
gap that card's gate disclosed. Lock: absence confirmed with `find -maxdepth 1 -name`, written with
all five fields and no pid, released by an `EXIT` trap and verified gone; neither override env var
touched.

[Round] **Eight mutants, one dead and replaced.** M1 (eager preparation removed) killed; **M2** (the
card's remedy 2 literally — created, never migrated) killed; M3 (failure note drops the database
name) killed; **M4 SURVIVED and was reported as semantically equivalent, not a gap** — the
fall-through returns `None` either way — and was replaced by **M4b** (the plan reads a different
variable so every run looks unarmed), killed by five tests; M5 (`_refusal_reason` bypassed) killed;
M6 (resolved-URL precondition dropped, so a foreign `*_test` database gets prepared) killed; **M7
planted in a *test* module** (a collected module gains a direct read) killed, so AC-2's emptiness
claim is **failable rather than vacuous**. All by text with the occurrence asserted `== 1`, SHA-256
matched both ends, restored from captured content.

[Round] **G-1 / `nonogram_poc`: never created, dropped, connected to or truncated.** The only
existence check was issued from the **`postgres` maintenance database**, and the round deliberately
did not count its rows because that would require connecting. The refusal is neither widened nor
bypassed — `git diff -U0` carries no line touching `_refuse_unless_test_database`, `_refusal_reason`,
`_CREATABLE_NAME` or `endswith`, and a test asserts **structurally** that the decision goes through
`_refusal_reason` rather than a re-implemented suffix rule, because a widened guard most likely
arrives as a re-implementation. Every drop was proved safe first on four separate properties, with no
wildcard or pattern-matched drop anywhere. It also used the **Postgres.app** client per the
orchestrator's correction and never `psql -lqt`.

[Round] **Self-raised and NOT settled — for the gate to verify, not to accept.** After the full suite
the round corrected two carried figures in its own conftest docstring (a "26 database skips" count its
own change invalidates, and a line-distance phrase replaced by a class name), then re-ran the ten
modules that read source text at runtime (**498 passed / 0 skipped**) rather than a second 25-minute
suite. **So the full-suite figure is two docstring phrases behind the committed tree.** The round
raised and fixed this itself; the gate must verify it rather than take it as settled. Likewise its
**unarmed** figure is **derived, not measured**: +2 `db_required` tests means an unarmed suite should
report 2 more bare-`DATABASE_URL` skips than main's prior 27, i.e. **29**. Measured on the module
only: unarmed 2 skips, armed 0.

[Round] **Residues, carded rather than absorbed:** one `*_test` database per worktree is created and
**nothing removes them** — the round re-derived 66 and the orchestrator measured **67** afterwards,
the difference being the round's own run, exactly as it disclosed. Now **CARD-375**. And
`dog_in_house.py` emits a `SyntaxWarning: "\," is an invalid escape sequence` on any `ast` walk of
`src/` — pre-existing, harmless today, an error in a future Python. Now **CARD-376**. Left as a
**review ask** rather than a card: nothing asserts that conftest's newly-composed
`pytest_terminal_summary` still calls the lock guard's, so a future edit could drop it silently.
