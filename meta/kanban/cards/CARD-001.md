# CARD-001: Package scaffolding and CLI entry point

**Status:** ready
**Priority:** P1
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/001-package-scaffolding-cli
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** pyproject.toml, src/nonogram/__init__.py, src/nonogram/cli.py, src/nonogram/errors.py, src/nonogram/orchestrator.py, tests/test_cli.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The greenfield skeleton every later card builds inside. Nothing in this card generates,
solves, scores or exports anything — it establishes the package, the entry point, and the
argument surface.

1. **Installable src-layout package (ADR-0008).** `pyproject.toml` with PEP 621 metadata,
   `requires-python = ">=3.14"`, `src/` layout, and a `[project.scripts]` console entry
   point `nonogram = "nonogram.cli:main"`. Declare the **complete** ADR-0006 dependency
   baseline here (`Pillow`, `numpy`) so no later card has to reopen `pyproject.toml` —
   NumPy lands in the solver (ADR-0012), Pillow in the export renderers (ADR-0006/CON-006).
2. **Module skeleton (ADR-0007, layered pipeline package).** Create the module layout the
   platform decision fixes, with stubs where a later card owns the body:
   - `src/nonogram/__init__.py`
   - `src/nonogram/cli.py` — the only inbound adapter (COMP-001)
   - `src/nonogram/errors.py` — the error hierarchy the CLI maps to exit codes:
     `SizeOutOfRange`, `InvalidDensity`, `UnknownLibraryImage`, `GenerationAbandoned`,
     `SolverTimeout`, `ExportRejected`, `InvalidPuzzleName`
   - `src/nonogram/orchestrator.py` — the `generate(request) -> Puzzle` signature plus the
     `Puzzle` aggregate placeholder, raising `NotImplementedError` (body: CARD-005)
   Dependencies point inward only: `cli.py` imports `orchestrator`, never the reverse.
3. **argparse adapter (ADR-0010).** A `generate` subcommand carrying the increment-1 flag
   surface: `--mode {random}`, `--size`, `--density`, `--seed`, `--export {json}`, `--out`.
   Later cards extend this same parser (`--difficulty`, `--name`, `--image`, more export
   formats). argparse does **parsing only** — no domain validation. Size range, density
   range and name validity are domain rules enforced inward of COMP-001; the CLI's job is
   to convert a raised domain error into a clear message and a non-zero exit code.
4. A `tests/` tree with `tests/test_cli.py` asserting the parser wiring and the
   error→exit-code mapping, plus whatever `pytest` configuration the project needs
   (`[tool.pytest.ini_options]` in `pyproject.toml`).

## Acceptance criteria

_(none — this card is traced to no FR; it is the enabler the increment-1 FR cards land on.
Its done-definition is the guardrails below plus a green `python -m pytest` and a working
`nonogram --help`.)_

## Guardrails

- G-1: CLI-only surface — no web server, GUI, HTTP endpoint or interactive/playable output
  (CON-001, CON-002; both are v1 constraints, not preferences)
- G-2: Runtime dependencies are exactly stdlib + Pillow + NumPy (ADR-0006). Do not add any
  other third-party runtime dependency to `pyproject.toml` — this baseline is closed and
  every later card inherits it
- G-3: `cli.py` performs argument **parsing** only; size-range, density-range and name
  validation stay inward of COMP-001 (ADR-0010, trace.yml FR-001/FR-015 notes). Do not
  encode AC-003/AC-004/AC-045 as argparse `type=`/`choices=` checks
- G-4: Out of scope — no generation, solving, clue derivation, scoring or export logic.
  `orchestrator.generate` stays a signature with `NotImplementedError`; its body is CARD-005
- G-5: No persistence beyond local file export — no database, no cache, no state directory
  (CON-003)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** —
- **NFR:** —
- **CON:** CON-001, CON-002, CON-003
- **ADR:** ADR-0006, ADR-0007, ADR-0008, ADR-0010
- **Components:** COMP-001 (CLI Adapter), COMP-002 (Pipeline Orchestrator — stub only)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

Laid the greenfield skeleton: a PEP 621 `pyproject.toml` (src-layout, `requires-python =
">=3.14"`, the closed ADR-0006 runtime baseline of Pillow + NumPy, a `nonogram =
"nonogram.cli:main"` console script and `[tool.pytest.ini_options]`), plus the four modules
ADR-0007 fixes as this card's share of the layout — `src/nonogram/__init__.py` (version only,
imports nothing), `errors.py` (the seven-error domain hierarchy under a `NonogramError` base),
`orchestrator.py` (COMP-002: the `GenerationRequest` boundary record, the `Puzzle` (AGG-001)
placeholder, and `generate(request) -> Puzzle` raising `NotImplementedError`), and `cli.py`
(COMP-001: an argparse `generate` subcommand carrying `--mode {random} --size --density --seed
--export {json} --out`, an `ExitCode` enum, and the domain-error → exit-code translation).
`tests/test_cli.py` covers parser wiring, the increment-1 flag surface, usage errors, the
argv → `GenerationRequest` hand-off, every error's exit code, and the ADR-0007 import
direction. `python -m pytest`: 38 passed, 0 failed. `pip install -e '.[dev]'` succeeds and
`nonogram --help` / `nonogram generate --help` work; no guardrail waivers were needed. Two
things deliberately NOT done: the dependency lockfile ADR-0008 mentions (needs a `uv`/`pip
compile` toolchain choice this card has no basis to make — pick it when CI first installs the
package), and the `import-linter` contract ADR-0007's negative consequence suggests (it would
be a fourth dependency; a source-parsing test guards the rule instead, see STRUCTURE-10).

STRUCTURE-1: setuptools>=77 as the build backend with `[tool.setuptools.packages.find] where
= ["src"]` — ADR-0008 fixes src-layout + PEP 621 but not the backend; setuptools ships in
every venv, so `pip install -e .` needs no extra build-time download, and no bespoke build
tooling is introduced (ADR-0008's "zero-novelty" criterion).

STRUCTURE-2: only the four modules this card owns exist; `sourcing/`, `clues.py`, `solver/`,
`difficulty.py` and `export/` are documented in the package docstring but NOT created as empty
stubs — an empty package would show up as an as-built component in trace.yml before its card
runs, and G-4 puts their content out of scope. The card that implements a capability creates
its module.

STRUCTURE-3: `errors.py` is a flat hierarchy — `NonogramError` plus the seven concrete errors,
no intermediate grouping classes (`InvalidInput`, `ExportFailure`, …). Grouping classes would
be abstraction with one implementation each and no boundary reason; the semantic grouping the
CLI actually needs lives in the exit-code table instead.

STRUCTURE-4: the exit-code table and `ExitCode` enum live in `cli.py`, not in `errors.py`. A
process exit code is an adapter concern; putting it on the exception classes would leak COMP-001
outward-facing knowledge inward, against ADR-0007's direction rule. `exit_code_for` walks the
error MRO, so a future error subclassing a mapped one inherits its code, and an unmapped
`NonogramError` reports `INTERNAL_ERROR` (1) rather than masquerading as a user error.

STRUCTURE-5: exit codes are grouped by what the user must do, not one per exception class —
0 OK, 1 internal, 2 usage (argparse's own), 3 invalid input, 4 generation failed, 5 export
rejected. Later cards can add errors to an existing group without changing the tool's
observable exit-code contract.

STRUCTURE-6: `GenerationRequest` is defined in `orchestrator.py`, not in `cli.py` and not in a
new `requests.py`. The inward module owns its own inbound boundary type, so the dependency
arrow stays cli → orchestrator; a separate module would be a third file for one dataclass.

STRUCTURE-7: `--size` and `--density` are optional (`default=None`) and carry no argparse
range, and every field of `GenerationRequest` except `mode` defaults to unset. This is G-3
literally: the parser accepts `--size 200` and `--density 9999` and hands them inward unchanged
(there is a parametrized test asserting exactly that, so re-adding a range check at the CLI
breaks the suite). It also keeps the domain free to resolve defaults per mode later — library
mode may imply its own size, which a `required=True` at the parser would have foreclosed.

STRUCTURE-8: `--export` is a repeatable `action="append"` flag with no default, normalized to a
tuple by the adapter. FR-011/FR-012 allow several formats per run, so repetition is the shape
later formats extend without a flag rename; choosing a default export format is a product
decision this card has no FR for, so an empty request means "the domain decides".

STRUCTURE-9: subcommand dispatch via `set_defaults(handler=...)` rather than an `if
args.command == …` ladder — later subcommands register themselves next to their own parser, and
`main` stays a three-line translate-and-map function.

STRUCTURE-10: ADR-0007's inward-only rule is guarded by tests that parse module source with
`ast` and assert no module inward of the adapter imports anything named `cli` (and that
`__init__.py` imports no submodule at all). This keeps the rule enforced without adding
`import-linter`, which G-2 would make a judgement call and which cannot run in the test
process anyway.

STRUCTURE-11: `Puzzle` is an intentionally field-less placeholder class. Its state is what
INV-001..INV-003 constrain, and inventing fields here would pre-empt CARD-005 and risk
committing the aggregate to a shape ADR-0012's grid representation contradicts; the docstring
records what must land there instead.
