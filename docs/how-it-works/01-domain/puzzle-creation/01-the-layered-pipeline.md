# 01 — The layered pipeline, and the guard that keeps it layered

> Scope: COMP-002 (`src/nonogram/orchestrator.py`), the ADR-0007 dependency rule,
> and the `ast` walk in `tests/test_cli.py` that enforces it.
> Read this first: every later file in this aspect assumes the direction of the
> arrows described here.

## Why it is this way

CTX-001 has one aggregate that spans its whole lifecycle. `meta/architecture/domain/contexts.yml`
records the reasoning: AGG-001 (Puzzle) is sourced, encoded, verified, scored and
exported as one object, and its three invariants are deliberately cross-cutting —
INV-001 ties sourcing to clue derivation, INV-002 ties uniqueness to export,
INV-003 is **one** counter shared by three different recovery reactions. Splitting
capabilities across contexts would have meant splitting the aggregate, which
`domain/aggregates.yml` had already refused.

That single-aggregate shape is the reason the code is a layered pipeline rather
than a set of collaborating services. If any capability module could call another,
each of those three invariants would acquire a second enforcement point, and the
model's one mandatory constraint (CON-005, the solver must never report a
false-positive uniqueness verdict) would become a property of a call graph instead
of a property of one function.

So ADR-0007 fixes four ranks and one direction:

```
rank 0   adapters          cli.py · web/ · admin/
rank 1   orchestrator      orchestrator.py  (and nonogram/__init__.py)
rank 2   capabilities      sourcing/ · clues.py · solver/ · difficulty.py · export/ · db/ · analysis/
rank 3   shared            errors.py · limits.py
```

An import is legal only when it reaches a **strictly deeper** rank.
See [diagrams/01-dependency-ranks.puml](diagrams/01-dependency-ranks.puml).

## How the rule is enforced

It is not a convention and it is not a linter. `tests/test_cli.py:772` walks
`src/nonogram/**/*.py` on disk, parses each file with `ast`, collects the names it
imports from inside the `nonogram` package, and applies one comparison
(`tests/test_cli.py:885`):

```python
and _rank(other) <= _rank(own)
```

Three things follow from that single `<=` that are easy to miss:

- **Lateral imports between capabilities are violations, not merely discouraged.**
  Two capability modules share rank 2, so `2 <= 2` fails the test. `solver/`
  importing `clues.py` would red the suite.
- **`db/` is a capability, not a layer of its own.** It is absent from both
  `_ADAPTERS` and `_SHARED` (`tests/test_cli.py:747`, `:749`), so `_rank`
  falls through to `_CAPABILITY_RANK`. The admin panel (rank 0) may import it; the
  solver may not, and `db/` may not import the solver either.
- **Modules a later card adds are covered the moment they land**, because the
  capability set is discovered from disk rather than listed
  (`tests/test_cli.py:772`, `_discover_modules`).

There is exactly **one** exemption with a direction to it: `_LAUNCH_EDGE =
("cli", "web")` (`tests/test_cli.py:760`). `cli.py` may import `web/` because
ADR-0008 keeps a single `[project.scripts]` console entry point and
`nonogram serve` lives in `cli.py`'s argparse tree. The reversed pair stays
forbidden and is pinned as such by
`test_the_import_rule_rejects_each_forbidden_edge`.

The guard is itself guarded: `test_the_import_walk_actually_sees_the_package`
fails a misrooted walk, and `test_the_import_rule_rejects_each_forbidden_edge`
runs the rule against a fabricated package so a rank table that had degenerated
to "everything is rank 0" could not pass vacuously.

### What the lateral ban costs, and what the project pays instead

The ban has a real consequence: shared logic gets **reimplemented**, not
imported. `solver/propagate.py:403` holds `mask_runs`, a run-length encoder over
the solver's int bitmasks that duplicates what `clues.encode_line` already does:

> "The bitmask twin of `clues.encode_line` … ADR-0007 forbids lateral imports
> between capability modules, and `clues` is COMP-004's capability, not a shared
> kernel" — `solver/search.py:110`

The project does not then hope the two agree. `mask_runs` is pinned against
`clues.encode_line` **from the test tree**, where the import is legal. This is the
house pattern: an independent second implementation plus a cross-check from
outside, rather than one implementation checking itself.

The same pattern is why `difficulty.py` spells the three rung names out
(`difficulty.py:230`) instead of importing `solver.RUNG_*`, and pins them against
`solver.RUNG_ORDER` from a test.

It is also why nothing in this package depends on `hypothesis`. ADR-0006's
dependency baseline is closed — `pyproject.toml:23` declares exactly
`Pillow>=10.0` and `numpy>=1.24` as runtime dependencies — so "property" tests
build seeded corpora by hand with stdlib `random.Random` and **assert the case
count inside the test** so the corpus cannot silently shrink
(`tests/property/test_solver_uniqueness.py:215`).

## What the orchestrator actually does

ADR-0007 gives COMP-002 three jobs (`orchestrator.py:3`) and nothing else: own
AGG-001 for one run, be the single enforcement point for INV-002 and INV-003, and
drive POL-001..POL-006 by composing capability modules that never call each other.

One `generate()` call is:

```
resolve name  →  resolve tier  →  resolve extent  →  draw seed  →  build Puzzle
   →  fix the ADR-0011 deadline  →  resolve the source callable
   →  [ source → clues → solve → score ]  under two nested bounded loops
```

The first four steps happen **before the aggregate exists**
(`orchestrator.py:1760`-`1788`), because an unusable name (AC-045), an unsupported
tier (AC-021) or an unresolvable extent (AC-098) must leave nothing behind. All
three are then fixed for the run: a retry replaces the *candidate*, never the
puzzle.

### The aggregate holds the invariants, one enforcement point each

`Puzzle` (`orchestrator.py:927`) is created once per call and mutated in place.
Its docstring states the mapping, and the code matches it:

| Invariant | Enforcement point | Mechanism |
|---|---|---|
| INV-001 clues == RLE of grid | `Puzzle.record_candidate` (`:1174`) | grid and clues are written in one operation; the method returns the fresh clues so the caller never reads them back |
| INV-002 export gated on uniqueness | `Puzzle.confirm_uniqueness` (`:1214`) writes it, `require_ready_for_export` (`:1307`) reads it | `ready_for_export = solution_count == UNIQUE_SOLUTION_COUNT`, and nothing else assigns that field |
| INV-003 retry counter within bound | `RetryCounter.record_attempt` (`:605`) | refuses to advance past `bound` with a `RuntimeError`, so a caller cannot overshoot even by ignoring `exhausted` |

`record_candidate` also *clears* the previous candidate's whole verdict —
`solution_count`, `difficulty_score`, `branch_nodes`, `undecided_mask`,
`witnesses`, `rung_tags`, `givens`, `strategies`, `ready_for_export`
(`:1187`-`1211`). That is what keeps INV-002 true in the gap between discarding a
candidate and judging its replacement, and what makes AC-026 ("the new candidate
is re-scored automatically") structural rather than a step to remember.

### One counting primitive, three loop kinds

Three bounded loops exist in the model and INV-003 constrains all three with one
sentence, so the counting lives in one place. `RetryCounter` holds the count;
`run_bounded` (`:624`) is the loop:

```python
while not counter.exhausted:
    counter.record_attempt()
    candidate = attempt()
    if candidate is not None:
        return candidate
raise GenerationAbandoned(...)
```

`attempt` returns the accepted candidate or `None` for "try another". Anything it
**raises** propagates unchanged — which is the load-bearing detail. Only a
candidate the uniqueness check answered about can be retried
(`orchestrator.py:44`). A `SolverTimeout`, a `SizeOutOfRange` or a wiring bug ends
the run immediately, because conflating a timeout with a non-unique verdict would
let one infeasible request spend `MAX_RETRY_ATTEMPTS` full solver deadlines —
exactly the worst case ADR-0002's attempt bound and ADR-0001's time budget exist
to prevent "together but independently".

The three counters, with the bounds as the code states them:

| Counter | Policy | Bound | Constant |
|---|---|---|---|
| `regenerate` | POL-001 redraw + POL-006 repair | 30 | `MAX_REGENERATE_ATTEMPTS` → `MAX_RETRY_ATTEMPTS` (`:192`) |
| `resample` | POL-004 difficulty resample | 30 | `MAX_RESAMPLE_ATTEMPTS` → same constant |
| `nudge` | POL-002 pixel nudge | 5 | `MAX_NUDGE_ATTEMPTS` (`:261`) |

`MAX_RETRY_ATTEMPTS` and `MAX_NUDGE_ATTEMPTS` are deliberately **not** chained.
They answer different questions — how many fresh candidates are worth drawing,
versus how much of the user's own picture it is acceptable to alter behind their
back — and the module says so at `:249`: "a retune of the retry bound must not
silently license twenty edits to an uploaded photograph."

`MAX_CONSECUTIVE_REPAIRS = 5` (`:224`) is a fourth number of a different kind. It
bounds nothing: every repair and every redraw advances the one `regenerate`
counter, and K only decides how that single budget is **split** between the two
reactions. Setting it to `0` restores the pure-redraw loop exactly, down to the
rng draws — ADR-0024's rollback switch, and a property of how the branch in
`generate` is written rather than a flag anything consults.

### The bounds are measured, and the measurements are in the source

This is worth reading as the project's register. `MAX_RETRY_ATTEMPTS` moved from
ADR-0002's original 20 to 30 in CARD-090 on a sweep recorded at
`orchestrator.py:178`: at 30×30 density 50 over 100 seeded requests, bound 20
abandoned 14, bound 30 abandons 4, bound 40 abandons 3, bound 60 abandons 1. Ten
of the fourteen were false negatives. 30 is where the curve knees. The
counter-intuitive finding is recorded with it: raising the bound *lowered* total
wall clock, because an abandonment spends the whole budget and returns nothing
while a success usually lands early.

`MAX_CONSECUTIVE_REPAIRS` moved from ADR-0024's guessed 3 to 5 in CARD-091 on the
same shape of sweep (`:208`): K=0 38%, K=3 95%, K=5 99%, K=8 98%, K=12 98%
success over 100 seeded requests — and the tell was that at K=3, 45 of the 95
accepted puzzles were found on the *last* repair K allowed.

### The two nested loops, and one shared budget

POL-004's resample loop **wraps** POL-001's regenerate loop (`:1624`). One
resample round runs the whole regenerate loop to get a uniquely-solvable
candidate, then keeps it only if its score is in tier. Neither counter is reset
between rounds, so across a whole request **at most 30 grids are ever sourced**,
however the two rejection causes divide them up. A resample round does not get a
fresh budget to find a unique candidate in — which is what stops scoring inside
the loop from multiplying the work NFR-001 budgets.

### The deadline: computed once, shared by every solve

ADR-0011's cooperative deadline is **enforced**, not stubbed. `generate` turns
`GENERATION_BUDGET_SECONDS = 30.0` into one absolute `time.monotonic` instant
before the first attempt (`orchestrator.py:1793`) and threads that same instant
into the module's single `solver.solve` call (`:1859`). The solver checks it at
every propagation fixed point (`solver/propagate.py:983`, `:1129`) and at every
branch node (`solver/search.py:1180`, `:1259`), raising `SolverTimeout` rather
than returning a verdict.

Per-request and not per-solve, deliberately: 30 attempts times a 30 s per-solve
budget would be a fifteen-minute "timeout" (`:332`). The retry loop therefore
cannot extend the budget by taking another turn.

ADR-0001's *other* number — the 5 s p95 for grids up to 20×20 — is deliberately
not a constant here. It is a benchmark gate (`tests/bench_generate.py`), not a
failure boundary, and `orchestrator.py:337` records that the asymmetry is meant to
stay explicit.

### There is exactly one `solver.solve` call in the module

`judge_candidate` (`orchestrator.py:1819`) is the tail of the pipeline, shared by
every loop in the function. Where a candidate came from — a fresh draw, a library
re-rendering, an uploaded image, a nudged image, a repaired grid, an unaltered
grid with cells revealed — cannot change how it is judged. That is CON-005 made
structural: a nudged grid is genuinely re-solved and can no more be assumed unique
than a random one.

### Errors travel out as domain errors; only the CLI knows about exit codes

`errors.py` is import-free and behaviour-free: every class is a marker the raiser
fills with a message. The exit-code table lives in `cli.py:72`, grouped by what
the user must do rather than one code per class, and `exit_code_for` (`cli.py:112`)
walks the error's MRO so a future subclass inherits its group. `SizeTooSmallForSource`
and `GivenCellsCapExceeded` were both added later and needed no new row — that is
the extension path the table was built for (`errors.py:49`, `:114`).

An unmapped `NonogramError` reports `INTERNAL_ERROR`, because a mapping gap is a
bug, not a user error.

## Bounds and honest gaps

- **No persistence on this path.** CON-017 (superseding CON-003): the aggregate
  lives in memory for one call. `generate()` writes nothing; `export_puzzle()` is
  the only function in the pipeline that touches the filesystem
  (`orchestrator.py:2473`). A run that is abandoned leaves no trace on disk.
- **`src/nonogram/analysis/` belongs to no component.** It is not in
  `trace.yml`'s `components:` block and not in the C4 component diagram.
  `src/nonogram/__init__.py:32` records that as deliberate (CARD-053) rather than
  as an omission. See [10-persistence-and-the-unmodelled-edges.md](10-persistence-and-the-unmodelled-edges.md).
- **`MAX_CONSECUTIVE_ABANDONMENTS = 3`** (`:247`) and
  **`BATCH_BUDGET_SECONDS = 75.0`** / **`MAX_BATCH_COUNT = 50`** (`:312`, `:323`)
  bound a *batch*, not a puzzle, and exist because the admin panel calls
  `generate_batch` synchronously inside an HTTP request. They are covered in
  [07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md).

## Related

- [02-sourcing-a-solution-grid.md](02-sourcing-a-solution-grid.md) · [04-uniqueness-and-recovery.md](04-uniqueness-and-recovery.md) · [06-exporting-a-finished-puzzle.md](06-exporting-a-finished-puzzle.md)
- ADRs: [ADR-0007](../../../../meta/architecture/decisions/adr/0007-internal-module-architecture.md) · [ADR-0002](../../../../meta/architecture/decisions/adr/0002-retry-and-nudge-bounds.md) · [ADR-0011](../../../../meta/architecture/decisions/adr/0011-generation-timeout-mechanism.md) · [ADR-0024](../../../../meta/architecture/decisions/adr/0024-random-mode-repair-then-redraw.md)
- `docs/GENERATION_ALGORITHM.md` — the pipeline as prose, maintained alongside the code
