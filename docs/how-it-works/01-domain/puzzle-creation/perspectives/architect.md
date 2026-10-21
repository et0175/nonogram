# Puzzle Creation (CTX-001) — architect's perspective

## Why this matters to `architect`

CTX-001 is the **only** bounded context in this system, and its `context_map` is
empty. That is the single most consequential architectural fact here, and it was
reached by ruling out every boundary signal rather than by defaulting to a
monolith — `meta/architecture/domain/contexts.yml` carries the full elimination,
including the three technical seams that were considered and deliberately kept as
*module* seams. Everything an architect is accountable for in this repo therefore
reduces to two questions: does the dependency direction still hold, and is the one
mandatory constraint (CON-005) still proved rather than asserted.

You are also the person who will be asked to admit a fourth adapter, a second
paper size, a third aggregate or a new runtime dependency. Each of those has a
recorded, closed decision behind it, and each has a guard that fails the suite
rather than a convention that erodes.

## Description

Three containers, one context (`c4/containers.puml`):

| Container | What it is | State |
|---|---|---|
| Puzzle Creation Tool | the whole generation pipeline in one local process, with **two** first-class inbound adapters in it (CON-007) | none beyond the files it exports (CON-017) |
| Admin Panel | a separate process, its own entry point, deployed on Render | writes to the database |
| Admin Database | Postgres via SQLAlchemy + Alembic | the only persistent state in the system |

There is **deliberately no `Rel` between the admin panel and the generation
tool** — the containers diagram says so in a comment: "the admin panel imports the
same generation package into its OWN process; it never calls the other container.
An arrow here would claim an inter-process call that does not exist."

Inside, ADR-0007 fixes four ranks and one direction, and
[the layering narrative](../01-the-layered-pipeline.md) covers the mechanism. The
architecturally load-bearing part is the *absence* of arrows between capability
modules: there is no arrow between COMP-003..COMP-007 in the component diagram,
and the diagram's own header says "that absence is the architecture, not an
omission."

One consequence an architect should be able to state from memory: **the admin
panel's arrows straight into COMP-004 and COMP-005 are legal and are drawn on
purpose.** The panel is an *adapter* (rank 0), not a capability, and those arrows
are ADR-0032/R1's storage guard — it re-derives a puzzle's clues and asks the
solver for a verdict at the storage boundary itself rather than trusting whoever
called it. The component diagram is explicit: "routing them 'through the
orchestrator' would erase that guarantee."

## Examples

**The guard that makes layering an architectural property rather than a review
checklist.** `tests/test_cli.py` walks `src/nonogram/**/*.py` with `ast` and
applies one comparison (`:885`):

```python
and _rank(other) <= _rank(own)
```

with the ranks at `:762`-`765` and the one directed exemption at `:760`
(`_LAUNCH_EDGE = ("cli", "web")`). The capability set is **discovered from disk**
(`_discover_modules`, `:772`), so a module a later card adds is covered the moment
it lands. The guard is itself guarded: `test_the_import_walk_actually_sees_the_package`
fails a misrooted walk, and `test_the_import_rule_rejects_each_forbidden_edge` runs
the rule against a fabricated package so a degenerate rank table cannot pass
vacuously.

**What the lateral ban costs, in the code.** `solver/propagate.py:403`:

> `mask_runs` — "The bitmask twin of `clues.encode_line`, for the one case where
> the line is complete and the DP would be wasted work … `clues` is COMP-004's
> capability, not a shared kernel."

Pinned against `clues.encode_line` from the test tree, where the import is legal.
The same pattern appears twice more: `difficulty.py:230` spells the three rung
names out rather than importing `solver.RUNG_*`, and `web/submission.py:134`
duplicates `cli._EXTENT_SEPARATOR` byte for byte. **Three reimplement-and-cross-
check pairs is the architectural cost of ADR-0007**, and it is paid deliberately
each time with a docstring naming the precedent.

**A closed decision, and how it was reopened properly.** `layout.py` carried
guardrail G-1 — "A4 is the only sheet it knows" — until ADR-0036 retired it. The
reopening is narrow by construction (`layout.py:34`): COMP-007 now knows more than
one sheet "**only through an explicit `PageSpec`, never by guessing** … Nothing
here infers a sheet from the puzzle, the payload or the caller." The export
registry never passes one, so CON-019's "CLI and web exports stay byte-identical"
is structural, pinned by `tests/test_export_a4_golden.py`.

**A decision retired on measurement, not argument.** ADR-0025's fourth difficulty
tier (`Tier.GUESS`) was retired by ADR-0031 because its measured assignment rate
was zero in every population anyone looked at — 0 of 6,620, 0 of 462, 0 of 16
stored rows (`difficulty.py:255`) — and CARD-072 established *why*: no random draw
in the supported range branches after the solve's one-step lookahead phase, so the
tier was unreachable from generation. The fact it carried survives as the `guess`
**strategy**. That is the register to match when you retire something.

## High-level constraints and trade-offs

**CON-005 (mandatory) — ADR-0009, ADR-0014.** The uniqueness check must never
report a false positive. The trade-off ADR-0009 took knowingly: a hand-rolled
solver is where such a bug would hide. The mitigation is structural in two places —
every completed board is re-encoded and compared before it counts as a solution,
and a mismatch *raises* (`solver/search.py:100`); and EC-001 is property-tested
against an oracle that **must never import `nonogram.solver`**
(`tests/helpers/brute_force_oracle.py:6`), with the oracle's own two counters
cross-checking each other. If you change anything in `solver/`, the oracle's
independence is the invariant to protect, not the test's pass rate.

**ADR-0007 — inward-only dependencies.** The trade-off is explicit: duplication
over coupling. Accept it, and keep the cross-check in the test tree. Note the
asymmetry you inherit: `db/` ranks as a *capability* (`tests/test_cli.py:801`),
so no capability may import it and it may import no capability — the admin panel is
its only legal caller.

**ADR-0002 + ADR-0011 — two bounds that "operate together but independently."**
`MAX_RETRY_ATTEMPTS = 30` bounds attempts; `GENERATION_BUDGET_SECONDS = 30.0`
bounds wall clock, as **one** absolute instant per request shared by every solve
(`orchestrator.py:1793`). Conflating them is the failure mode the code guards
against by construction: `run_bounded` re-raises everything its attempt callable
raises, so a `SolverTimeout` ends the run instead of spending 30 more deadlines.
`orchestrator.py:332` records the arithmetic of the alternative: "30 attempts times
a per-solve 30s would be a fifteen-minute 'timeout'."

**ADR-0006 — the dependency baseline is closed.** `pyproject.toml:23` is exactly
`Pillow>=10.0` and `numpy>=1.24`. Everything else is an *extra*: `dev`
(pytest, pytest-playwright), `admin` (Flask, Werkzeug, reportlab, gunicorn), `db`
(SQLAlchemy, alembic, psycopg2-binary). `pyproject.toml:41` states the rule that
keeps that coherent: "ADR-0006/R1's baseline is `project.dependencies` above, which
stays exactly Pillow + NumPy — the extras have always been outside it." The visible
consequences in the architecture: no `hypothesis` (seeded corpora by hand instead),
no PDF library (CON-006 makes the PDF a second sink on the PNG raster), no SVG
library, no stdlib multipart parser after PEP 594 removed `cgi` (hence
`web/multipart.py`), and a font shipped as **package data** under ADR-0006/R1
rather than as a dependency.

**CON-004 — difficulty bands are heuristic, not a construction guarantee.** A tier
is a bucket a scored candidate fell into. POL-004 discards out-of-tier candidates;
it does **not** steer sourcing toward a tier (`orchestrator.py:26`,
`difficulty.py:272`). Do not let a future card invert that.

**CON-014 / NFR-007 / ADR-0029/R3 — no clock in a grade.** `elapsed_seconds`
exists and is telemetry only. A difficulty term that read it would make the same
seed grade differently on two machines.

**CON-017 (superseding CON-003) — the pipeline persists nothing.** Note the
precision required: the *generation pipeline* persists nothing, and
`orchestrator.generate()` genuinely writes nothing. But COMP-008's claim of "no
state beyond the export files" is **too strong as stated** — `web/uploads.py:59`
holds a process-lifetime `OrderedDict` of retention tokens bounded at
`MAX_RETAINED = 8`, and `web/multipart.py:104` writes uploads via
`tempfile.mkstemp`. See [09-the-three-inbound-adapters.md](../09-the-three-inbound-adapters.md).

**ADR-0033 — Book stays in CTX-001, and the split was costed.** `contexts.yml`
lists four signals *for* a separate CTX-002 (lifecycle mismatch, a print-production
vocabulary TERM-018..TERM-029 absent from the pipeline, a different
runtime/persistence, and CON-019's existing one-way rule — "the shape of an
upstream/downstream boundary") and two against (one owner, and the code already
treating `admin/` as a rank-0 adapter of CTX-001). It also names the obstacle to a
future split: a puzzle row's `book_id` mirrors membership (migration 009), so "a
split today would begin life as `shared_db` — the risky pattern — unless that
column is retired." That is your pre-work if the decision is revisited.

### Model-vs-code drift you own

The code wins; these are the deltas to carry back into the model.

1. **`c4/components-CTX-001.puml:87`** says COMP-003 sources "at a configured size
   10x10..50x50". `limits.py:16` is `MIN_SIZE = 10`, `MAX_SIZE = 30`, and ADR-0022
   narrowed the ceiling. `orchestrator.py:327` notes the same narrowing against
   its own constant.
2. **`c4/components-CTX-001.puml:95`** gives COMP-005 a four-rung ladder,
   `simple_overlap < line_dp < cross_line < probe_contradiction`.
   `propagate.py:148` has three; `:141` records `cross_line` as removed for good in
   the 2026-09-12 ADR-0029 revision, because it graded a puzzle differently from
   its own transpose. The string `cross_line` appears nowhere in `src/`.
3. **CAP-007 (Puzzle play) is in `capabilities.yml` and `contexts.yml` but absent
   from the component diagram's COMP inventory.** `trace.yml`'s 2026-10-03 (b)
   note confirms the player is a route, template and static assets of COMP-009 and
   that "the decision-surfacing note's 'COMP-008' was a mislabel" — but the COMP
   inventory comment block in the puml still lists CAP-001..CAP-006 only.
4. **`src/nonogram/analysis/` has no COMP id in `trace.yml` and no box in any C4
   diagram**, yet `analysis/quality_metric.py` is live admin-panel code
   (`admin/app.py:138`). Re-derived from `wc -l`: the unmapped surface is
   `errors.py` 190 + `limits.py` 17 + `analysis/` 483 + `__init__.py` 54 = **744 of
   46,127 lines, 1.6%**. `src/nonogram/__init__.py:32` records the `analysis/`
   omission as deliberate (CARD-053); the two shared modules are covered by
   `trace.yml`'s own prose but have no row.
5. **`capabilities.yml` CAP-001** says sourcing is "reachable through either
   inbound adapter … since both invoke the same CMD-001/CMD-002/CMD-003". The
   shipped web form offers **image mode only** since CARD-032
   (`pages.py:441`); CMD-001 and CMD-002 are reachable through `web` by a
   hand-written body, never from the rendered form.
6. **ADR-0020's Decision text does not cover `GET /static/<file>` or client-side
   JavaScript**, both of which ship (`handler.py:578`,
   `web/static/metadata.js`). This is *not* a CON-008 violation: CON-008 forbids an
   in-browser preview of the **generated puzzle**, while `metadata.js` previews the
   **uploaded source**. Different artifact — but the ADR is behind the code.

## Related docs

- Narrative: [01 — the layered pipeline](../01-the-layered-pipeline.md) · [04 — uniqueness and recovery](../04-uniqueness-and-recovery.md) · [09 — the three inbound adapters](../09-the-three-inbound-adapters.md) · [10 — persistence and the unmodelled edges](../10-persistence-and-the-unmodelled-edges.md)
- Siblings: [developer](developer.md) · [sre](sre.md) · [puzzle-creator (ACT-001)](puzzle-creator.md)
- Model: `meta/architecture/domain/contexts.yml` · `meta/architecture/c4/*.puml` · `meta/architecture/trace.yml` · `meta/architecture/requirements.yml`
- ADRs most often consulted from here: [ADR-0006](../../../../../meta/architecture/decisions/adr/0006-dependency-baseline.md) · [ADR-0007](../../../../../meta/architecture/decisions/adr/0007-internal-module-architecture.md) · [ADR-0009](../../../../../meta/architecture/decisions/adr/0009-solver-implementation.md) · [ADR-0019](../../../../../meta/architecture/decisions/adr/0019-web-ui-component-boundary.md) · [ADR-0032](../../../../../meta/architecture/decisions/adr/0032-admin-storage-guarantees.md) · [ADR-0033](../../../../../meta/architecture/decisions/adr/0033-book-assembly-stays-in-ctx-001.md) · [ADR-0036](../../../../../meta/architecture/decisions/adr/0036-book-page-geometry-via-page-spec.md)
