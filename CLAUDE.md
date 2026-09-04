# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Setup (Python >=3.14, src-layout package):

```bash
python3.14 -m venv .venv
./.venv/bin/pip install -e '.[dev]'
```

Run the whole suite:

```bash
./.venv/bin/python -m pytest        # or: pytest, once the venv is active
```

Run a single test / file / pattern:

```bash
./.venv/bin/python -m pytest tests/test_solver.py::test_reports_unique_solution -v
./.venv/bin/python -m pytest tests/property/test_solver_uniqueness.py -v   # the mandatory EC-001 property test
./.venv/bin/python -m pytest -k density
```

`pyproject.toml` sets `pythonpath = ["src"]`, so the suite also runs against a bare checkout without the editable install (but the `nonogram` console script and Pillow/NumPy still require it).

Run the CLI:

```bash
nonogram generate --size 20 --density 30 --seed 42 --export json
```

There is no lint/format/type-check tooling configured yet (no ruff/mypy in `pyproject.toml` or the venv).

## Architecture

This is a CLI tool that generates uniquely-solvable black-and-white nonogram puzzles. The full spec lives in `docs/requirements.md`; the formal architecture (ADRs, domain model, requirements with acceptance criteria, C4 diagrams) lives under `meta/architecture/`, and delivery is tracked as kanban cards under `meta/kanban/cards/` — a card's `## Worktree notes` section is often the best source of *why* a piece of code looks the way it does.

**Layered pipeline, one bounded context (CTX-001), one dependency direction.** Package layout (`src/nonogram/__init__.py` docstring is the canonical map):

```
cli.py           COMP-001  the only inbound adapter (argparse) — parsing only, no domain validation
orchestrator.py  COMP-002  owns the Puzzle aggregate; drives the capability modules below
sourcing/         COMP-003  sources a solution grid (random, library templates, user-uploaded images)
clues.py          COMP-004  pure run-length-encoding of a grid into row/column clues
solver/           COMP-005  hand-rolled constraint-propagation + backtracking uniqueness solver
difficulty.py     COMP-006  heuristic difficulty scoring (Easy/Medium/Hard tiers via solver signals)
export/           COMP-007  exports puzzles as PNG/SVG/JSON/CSV/PDF formats
web/              COMP-008  web UI adapter (HTTP request handler, form rendering, HTML generation)
```

`cli` imports `orchestrator`; `orchestrator` imports the capability modules; **capability modules never import `cli`, the orchestrator, or each other laterally** — their only shared dependency is `errors.py` (a flat, import-free exception hierarchy). This is not just convention: `tests/test_cli.py` contains a structural guard that walks `src/nonogram/**/*.py` on disk with `ast` and fails the suite on any lateral or inward-pointing import, so it automatically covers new capability modules as they're added. When two capabilities need to share logic, reimplement it natively in each rather than importing across — see `solver/propagate.py`'s `mask_runs` for the precedent (it deliberately reimplements one clue-encoding check rather than importing `clues.py`, and is cross-checked against `clues.encode_line` from the test tree instead, where the import is legal).

**Boundary types vs. internal representation.** Public APIs between modules pass grids as `list[list[bool]]` and clues as `tuple[tuple[int, ...], ...]` (a line with no filled cells encodes to `(0,)`, never `()`). The solver's internal per-line state is a pair of int bitmasks (filled/empty) for performance; those bitmasks never cross a module boundary in either direction. `orchestrator.GenerationRequest` is the CLI/domain boundary type — unvalidated, syntactically typed only; range/format validation happens inward of the CLI as pure domain functions (e.g. `sourcing/random_grid.py`'s `validate_size`/`validate_density`), never as argparse `choices=`/`type=` constraints, so a request can carry an out-of-range value all the way to where a `nonogram.errors.NonogramError` subclass rejects it. All such domain errors funnel through `NonogramError`; `cli.py` is the only place that maps them to a process exit code (grouped by what the user must do, not one code per exception class, via `exit_code_for`'s MRO walk).

**The dependency baseline is closed.** `pyproject.toml` declares exactly stdlib + Pillow + NumPy as runtime dependencies (plus `pytest` as a dev-only extra); adding a third-party runtime dependency requires revisiting that decision, not just editing `pyproject.toml`.

**The solver (`solver/`) is the correctness-critical component.** It must never report a puzzle as uniquely solvable when it actually has 0 or ≥2 solutions (the one mandatory property, verified by `tests/property/test_solver_uniqueness.py` against an independent brute-force oracle in `tests/helpers/brute_force_oracle.py` — that oracle must never import `nonogram.solver`, or the cross-check becomes circular). It fails fast: search stops the instant a second distinct solution is found rather than enumerating further, which is what makes it affordable to call on every candidate grid a future retry loop generates. Performance is asymmetric by design: line-logic alone solves easy/dense grids in milliseconds, but random mid-density grids at 40×40+ are a known-hard class where the search can take seconds — a cooperative timeout (hook points already present in `propagate.py`/`search.py`, not yet enforced) is expected to be needed once a retry loop calls this repeatedly.

**Test style.** No `hypothesis` (it isn't in the dependency baseline) — "property" tests instead build large seeded corpora by hand with stdlib `random.Random`, asserting a minimum case count inside the test itself so the corpus can't silently shrink. Prefer an independent second implementation over re-deriving a value with the same function you're testing (see the solver's two independent brute-force counters in `brute_force_oracle.py`, which cross-check each other).
