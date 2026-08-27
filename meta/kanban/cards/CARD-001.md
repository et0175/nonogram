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

—
