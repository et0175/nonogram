# CARD-002: Clue derivation via run-length encoding

**Status:** review
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/002-clue-derivation
**Worktree:** ../PythonProject4-card-002
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 2
**Depends on:** CARD-001
**Touches:** src/nonogram/clues.py, tests/test_clues.py
**Review score:** 7.0 (cycle 1/3, awaiting cycle 2 confirmation)
**Started:** 2026-08-27T15:25:27Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-004 (Clue Derivation) — a pure function module, no state, no I/O.

Given a solution grid in the ADR-0012 boundary representation (`list[list[bool]]`), compute
the row clues and column clues by run-length encoding contiguous filled runs. A line with no
filled cells encodes to the empty-row marker `[0]` (AC-013) — not `[]`, so downstream
renderers and the solver see a uniform shape.

Also provide the inverse check used by INV-001 and by the solver's line logic: given a line
clue and a line, confirm the clue is exactly that line's run-length encoding. AC-014 is that
check applied to every row and column of an arbitrary grid.

This module is the first consumer of ADR-0012's boundary type. Keep the public signature in
that type (`list[list[bool]]` in, `tuple[tuple[int, ...], ...]` out) — the solver's internal
int-bitmask representation is CARD-004's business and must not leak into this API.

## Acceptance criteria

- **AC-012** (happy) — given a grid row with pattern `██·███··`, when clues are computed for
  that row, then the row clue equals `[2, 3]`.
  *test:* `TestComputeClues_EncodesRunLengths`
- **AC-013** (boundary) — given a grid row with no filled cells, when clues are computed for
  that row, then the row clue is the empty-row marker `[0]`.
  *test:* `TestComputeClues_HandlesEmptyRow`
- **AC-014** (boundary, INV-001) — given any solution grid, when clues are computed for every
  row and column, then decoding each clue against the grid confirms it exactly matches that
  line's run-length encoding.
  *test:* `TestComputeClues_MatchesGridExactly`

## Guardrails

- G-1: Do not edit `src/nonogram/sourcing/**` — owned by CARD-003 this wave
- G-2: Do not edit `src/nonogram/cli.py`, `src/nonogram/orchestrator.py`,
  `pyproject.toml` — CARD-001's deliverable; this card adds a module, it does not rewire
  the entry point
- G-3: The public clue API stays in the ADR-0012 boundary type (`list[list[bool]]` /
  int tuples). Out of scope — no solver-internal bitmask representation here; that is
  CARD-004's private concern

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-005
- **NFR:** —
- **INV:** INV-001
- **ADR:** ADR-0012
- **Components:** COMP-004 (Clue Derivation)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

Implemented on `card/002-clue-derivation`. Touches matched the prediction exactly:
`src/nonogram/clues.py`, `tests/test_clues.py` — nothing else changed (G-1/G-2 held;
`cli.py`, `orchestrator.py`, `pyproject.toml` and `sourcing/**` untouched).

**Public surface** (ADR-0012 boundary type only — no solver bitmask, G-3):

- `encode_line(line) -> tuple[int, ...]` — run-length encode one line; accepts any
  iterable of cells so the solver's line logic can pass a transposed column directly.
- `compute_clues(grid: list[list[bool]]) -> Clues` — `Clues` is a two-field NamedTuple
  (`rows`, `columns`), each a `tuple[tuple[int, ...], ...]`. Named rather than a bare
  pair to kill the `(rows, cols)` transposition bug at call sites; still unpacks as a
  plain tuple.
- `clue_matches_line(clue, line) -> bool` — the exact inverse check (INV-001), also
  the accept/reject predicate the solver's line logic needs. Compares by value, so a
  JSON-decoded `list` clue works without re-tupling.
- `EMPTY_LINE_CLUE = (0,)` — the AC-013 marker, named so downstream cards cite it
  rather than re-hardcoding it.

**Decisions worth carrying forward:**

- The empty-line marker is `(0,)`, never `()`, on columns as well as rows, so every
  clue is non-empty and the solver's "runs + gaps" arithmetic needs no special case.
  `clue_matches_line((), blank_line)` is `False` on purpose — a clue set that lost the
  marker is reported as a mismatch instead of passing vacuously.
- A ragged grid raises `ValueError` via `zip(*grid, strict=True)` — a programming
  error, not a domain condition, so no new type was added to `errors.py` (which is out
  of Touches anyway). Silent truncation to the shortest row was the alternative and it
  would have emitted clues that quietly disagree with the grid, breaking INV-001 with
  nothing failing.
- `compute_clues([])` returns `((), ())` — no rows means no clues, not a marker per
  missing line.

**AC → test mapping** (pytest-idiomatic names; each test's docstring cites its AC):

| AC | trace.yml test id | tests/test_clues.py |
| --- | --- | --- |
| AC-012 | `TestComputeClues_EncodesRunLengths` | `test_encodes_run_lengths*` (grid entry point, line primitive, 7 edge patterns, column ordering) |
| AC-013 | `TestComputeClues_HandlesEmptyRow` | `test_handles_empty_row*`, `test_clue_matches_line_rejects_the_bare_empty_tuple` |
| AC-014 (INV-001) | `TestComputeClues_MatchesGridExactly` | `test_matches_grid_exactly*` |

**AC-014 as a property, without hypothesis.** ADR-0006's dependency baseline is closed,
so INV-001 is swept over ~60 parametrized grids instead: hand-picked degenerate and
saturated shapes (1x1, single row/column, all-filled, all-empty, checkerboard, both
diagonals, frame, asymmetric) plus a seeded `random.Random(20260827)` sweep over sizes
1..50 (ADR-0012's line cap) and densities 0.0..1.0, including non-square grids so a
rows/columns mix-up cannot survive by symmetry. Fixed seed ⇒ reproducible; a failure is
replayable from the parametrize id alone. Two independent views of the invariant: the
per-line inverse check, and run sums conserving the filled-cell count on both axes
(catches an encoding that is self-consistent on one axis but lost cells on the other).
`test_matches_grid_exactly_rejects_a_wrong_clue` pins that the check can actually fail
(wrong order, extra/missing run, same total with the wrong split), so a green sweep
means something.

**Verification.** `./.venv/bin/python -m pytest -q` → **207 passed** (166 new + 41
pre-existing CLI tests, unbroken). Mutation-sanity checked by hand: dropping the
empty-line marker and aliasing column clues to row clues each fail the suite; both
reverted. `test_cli.py`'s disk-discovered ADR-0007 layering test picks up `clues.py`
automatically and passes — the module imports nothing from `nonogram`.

No blockers.

[Scope] src/nonogram/clues.py, tests/test_clues.py — matches predicted Touches exactly.
[Build gate] PASSED (full, independently re-run by orchestrator: 207 passed, 0 failed)
[Review 1/3] Score: 7.0 (below min_score 8) — crit: 2, imp: 3. Guardrails G-1..G-3 all ✓ holds; Touches exact; ADR-0012 conformance exemplary. CRITICAL (mutation-proven): AC-014/INV-001's named test `TestComputeClues_MatchesGridExactly` is a tautology — `clue_matches_line` re-derives via the same `encode_line` the diff is supposed to verify, so both sides of the equality share any defect in the encoder. A mutant reversing run order for lines >21 cells passes all 166 tests in the file (the 20-50 size range this tool targets). The sweep needs a decode-side oracle (reconstruct line from clue, or re-encode via a different algorithm e.g. itertools.groupby) to actually falsify the encoder — AC-014 is unmet as written. Important: (I-1) card notes overstate `clue_matches_line` as "the accept/reject predicate the solver's line logic needs" — ADR-0012 fixes the solver's state as three-valued/partial; this function silently mishandles partial lines (truthy-based, no type check). (I-2) the 72-grid sweep is a fixed corpus at import time (not a fresh generator per run) and under the engineering-standards' 100-1000 case band. (I-3) NFR-001 perf risk if CARD-004 calls this per-cell function inside its hot propagation loop — ADR-0012 exists specifically to avoid that; note for CARD-004. → routed to fix cycle.
[Fix 1] Critical resolved: added `_reference_encode_line` (itertools.groupby, zero shared code with clues.encode_line) as an independent oracle in both the property sweep and the hand-written examples. Fix agent reproduced the reviewer's exact mutation (reverse run order >21 cells) and confirmed the new oracle assertions fail immediately while clue_matches_line's own assertion still passes — the exact gap now closed. I-2 resolved: sweep widened 72→182 grids, non-square shapes now swept across all 9 densities (previously one fixed density). I-1 resolved: corrected clue_matches_line's docstring and this card's notes to scope it to complete lines only; CARD-004 already carries the corresponding hot-loop/partial-line caveat. 427/427 passed, independently re-verified by orchestrator.
