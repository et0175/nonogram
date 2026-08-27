# ADR-0008: Packaging and runtime

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

CON-001 fixes the target interface as a CLI tool with no web/GUI in v1, run as a
single local process with local file I/O only. FR-011 and FR-012 require the tool
to export a finalized puzzle in several formats (PNG and/or SVG for print, JSON
and/or CSV for exact reconstruction of the solution grid and clues), which means
the packaged tool must run reliably as an installed command that a user invokes
repeatedly against different inputs, not as a one-shot script. The repository
currently holds only the bare `main.py` boilerplate left over from project
scaffolding — the CLI that docs/requirements.md Section 2 describes has not yet
been given a package shape, an entry point, or a declared dependency mechanism.

The module boundaries this package must expose internally — image conversion,
solver/scorer, and export renderers as seams within the single bounded context
(CTX-001) — are the subject of a related decision (DEC-007) and are not settled
here. Separately, the tool's runtime dependency baseline (whether it needs only
Pillow, or Pillow plus NumPy) is the subject of DEC-006 and is likewise not
settled here; at least one compiled-wheel dependency for raster image work is
expected regardless of that outcome. This decision is scoped narrowly to how the
tool is packaged, distributed, and executed, and how its dependencies — whatever
DEC-006 decides them to be — are declared and pinned, independent of both of
those outcomes.

## Decision

We will package the tool as an **installable Python package using a src-layout
and `pyproject.toml`** (PEP 621), exposing a `[project.scripts]` console entry
point (e.g. `nonogram`), with dependencies declared with lower bounds and pinned
via a lockfile, installed into a virtual environment via `pip` or `uv`. The tool
runs as a single local process and writes exports to the working directory or a
user-supplied `--out` path.

This is the alternative labeled **installable_package_pyproject** in DEC-008 and
is also this DEC's stated default. A console entry point is the conventional
shape CON-001's "CLI tool" implies, and `pyproject.toml` becomes the single
source of truth that `forge:harness` and `forge:kanban` read for the toolchain
(test runner, linters, the Python 3.14 pin). It also makes the module boundaries
that DEC-007 will define enforceable and importable by the test suite, which a
single script or a vendored bundle cannot offer. The two alternatives considered
below were rejected primarily because they trade this structural clarity for a
distribution convenience — zero-install or single-file copying — that does not
matter for this tool's actual usage pattern: a single local user installing once
and invoking the command repeatedly.

## Alternatives considered

### single_file_pep723_script

A single self-contained script declaring its dependencies via PEP 723 inline
script metadata, run with `uv run nonogram.py` or a pipx-style invocation with no
install step. This was rejected because it directly contradicts DEC-007's module
boundaries — a single file cannot cleanly hold five internal modules (image
conversion, solver/scorer, export renderers, orchestration, CLI) — and because
the test suite would not be able to import parts of it cleanly, making property
tests for EC-001/EC-002 awkward to write and run. It also requires a PEP
723-aware runner, a stronger and less universal assumption than "pip install."

### zipapp_bundle

A `.pyz` zipapp bundling the package with its dependencies vendored in, shipped
as one double-clickable or one-command artifact. This keeps the multi-module
package structure intact but was rejected because vendoring a compiled wheel
(Pillow, expected from DEC-006 under either of its outcomes) into a zipapp is
platform-specific and fragile, and because the build step it requires has no
real consumer to justify it — the tool's single actor (ACT-001) is also its
developer, running it on the same machine it was built on.

## Consequences

### Positive

- The package gets a conventional, discoverable shape: `pip install .` (or
  `uv pip install .`) followed by running `nonogram` from anywhere, matching
  what CON-001's "CLI tool" framing implies to any user or contributor.
- `pyproject.toml` becomes the single authoritative file for dependencies, the
  test runner, linters, and the Python 3.14 pin, which `forge:harness` and
  `forge:kanban` can read directly instead of inferring the toolchain from
  scattered config files.
- The src-layout enforces the module boundaries DEC-007 will define as real
  importable package boundaries, so the test suite (including the property
  tests required for EC-001/EC-002) can exercise internal modules directly
  without import hacks.
- The choice is standard and zero-novelty: the cost is a small (roughly 15-line)
  `pyproject.toml`, with no bespoke build tooling or packaging format to
  maintain.

### Negative

- An install step is now required before first run — a bare script or a zipapp
  could be executed with zero setup; this package must be installed into a
  venv first.
- A lockfile now exists as an artifact that needs to be regenerated and
  reviewed whenever dependencies change, adding a small amount of ongoing
  maintenance that a single unversioned script would not carry.

### Neutral

- Introduces `pyproject.toml` and a lockfile as new repository artifacts,
  replacing the bare `main.py` boilerplate entirely; `main.py` is retired by
  this decision rather than kept alongside the package.
- The actual dependency set and pin strategy are still governed by DEC-006 —
  this decision only fixes *how* dependencies are declared and installed, not
  *which* ones are required.
- The internal module layout this package boundary encloses is still governed
  by DEC-007 — this decision fixes the packaging mechanism the eventual module
  split will live inside, not the split itself.

## References

- DEC-008 (resolved by this ADR)
- CON-001, FR-011, FR-012 (criteria this decision satisfies)
- DEC-006, DEC-007 (related, separately-decided: dependency baseline and
  internal module boundaries)
- CTX-001 (Puzzle Creation, the single bounded context this package implements)

## History

- 2026-08-27: Created — adopted an installable src-layout package with
  `pyproject.toml` and a console entry point as the packaging, distribution,
  and execution model for the CLI, replacing the repository's bare `main.py`
  boilerplate.
