# CARD-017: Nudge-count reporting in CLI output

**Status:** review
**Priority:** P3
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/017-nudge-count-reporting
**Worktree:** ../PythonProject4-card-017
**Source:** meta/architecture/handoff.md#increment-3
**Idea:** —
**Wave:** 11
**Depends on:** CARD-016
**Touches:** src/nonogram/cli.py, src/nonogram/orchestrator.py, tests/test_nudge_reporting.py
**Review score:** 8.5 (cycle 1/3)
**Started:** 2026-08-29T10:40:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The last card of the plan, and deliberately the smallest: make the nudges visible.

FR-014 exists because ADR-0004 resolved DEC-004 — a tool that quietly alters the user's
picture and says nothing is not acceptable, but a diff view or a per-pixel report is more
than the CLI needs. The decision is a single count line at export time.

1. `nudge_count` is already carried on the `Puzzle` aggregate by COMP-002 (CARD-016). At
   export time COMP-001 prints one line stating how many cells were nudged.
2. **Zero nudges → no line at all** (AC-041). Not "0 cells nudged" — the absence of the line
   is the signal that the image came through untouched.
3. COMP-007 writes **no** nudge metadata into the image exports — the report is a CLI output
   line only (trace.yml FR-014 note).

## Acceptance criteria

- **AC-040** (happy) — given an exported puzzle whose image conversion required 2 pixel
  nudges to reach uniqueness, when the puzzle is exported, then the CLI output includes a
  line stating that 2 cells were nudged.
  *test:* `TestExport_ReportsNudgeCount`
- **AC-041** (boundary) — given an exported puzzle whose image conversion reached uniqueness
  with zero nudges, when the puzzle is exported, then no nudge-count line is printed.
  *test:* `TestExport_OmitsNudgeCountWhenZero`

## Guardrails

- G-1: Do not edit `src/nonogram/export/**` — COMP-007 writes no nudge metadata into the
  image exports; the report is a CLI output line only (trace.yml FR-014 note)
  (test: TestExport_WritesPNG, TestExport_WritesPDFPageOneBlankWithHeader)
- G-2: Do not edit `src/nonogram/sourcing/**`, `src/nonogram/solver/**`,
  `src/nonogram/clues.py`, `src/nonogram/difficulty.py` — reporting is additive and must
  revert without touching random/library modes, the solver, or export (handoff Increment 3
  Rollback)
- G-3: Zero nudges prints nothing — do not "improve" this into a `0 cells nudged` line
  (AC-041 is the decision, ADR-0004)
- G-4: Out of scope — no per-pixel diff, no before/after image, no nudge coordinates.
  ADR-0004 chose the count over the diff deliberately
- G-5: The nudge count is read from the aggregate, not recomputed — do not re-derive it by
  comparing grids in `cli.py`

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-014
- **NFR:** —
- **ADR:** ADR-0004
- **Components:** COMP-001 (prints), COMP-002 (carries the count)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

**Correction confirmed against code first.** The card's own text says
`nudge_count` is carried on `Puzzle`; the actual field (from CARD-016) is
`puzzle.nudge`, a `RetryCounter` (same type as `regenerate`/`resample`), and
the count to print is `puzzle.nudge.attempts` (an `int`, default `0` via
`RetryCounter`'s dataclass default). Read `orchestrator.py`'s `Puzzle` and
`RetryCounter` classes before writing anything, per the task's instruction —
confirmed the field name and that CARD-016 already left a comment on it
("CARD-017 reports this number to the user; this card only carries it
(guardrail G-5)").

**What was built.** One change, in `src/nonogram/cli.py`'s `_run_generate`:
after the existing `for path in written: print(f"wrote {path}")` loop, four
new lines read `puzzle.nudge.attempts` and, only when it is greater than
zero, print a line of the form `"2 cells were nudged to reach a unique
solution"` (with `cell`/`was` for the singular case, though the nudge cap is
5 so the count is always in `1..5` when nonzero). Nothing is printed when the
count is zero — no `if/else`, just the single `if nudged > 0:` guard, so
there is no "0 cells nudged" branch to accidentally add later (G-3).

**Placement decision (documented per the task's instruction to use judgment
and record the choice).** Placed the line *after* the `"wrote {path}"` loop,
not right after `puzzle = orchestrator.generate(request)`. Reasoning:

- AC-040 and AC-041 are both phrased as "when the puzzle is exported" — the
  count is framed as an export-time report, not a generation-time one, even
  though the underlying number is fixed the moment `generate()` returns.
- Placing it after the export loop means nothing prints if export fails
  with an `OSError` (the `except` branch returns before reaching this code),
  which matches "the report is a CLI output line only ... at export time"
  more literally than printing it unconditionally right after generation,
  before it's known whether export will even happen.
- It reads naturally alongside the other export-time report (`wrote
  {path}`), keeping the two "what happened during this run" lines adjacent
  in stdout, with the reproducibility line (`seed: ...`) staying where it
  was, printed right after generation since that one really is about
  generation, not export.

**Guardrail compliance.**
- G-1: `src/nonogram/export/**` untouched; no nudge metadata added to any
  export format. Verified via `git diff --stat` — only `cli.py` changed.
- G-2: `sourcing/**`, `solver/**`, `clues.py`, `difficulty.py` untouched.
- G-3: zero nudges prints nothing (`test_export_omits_nudge_count_when_zero`
  asserts `"nudged" not in out`, not merely that a specific string is
  absent).
- G-4: count only — no diff, no image, no coordinates.
- G-5: `puzzle.nudge.attempts` is read directly; no grid comparison of any
  kind appears in `cli.py`.

**Touches vs. prediction.** Matches the predicted list except
`orchestrator.py`, which needed *no* change at all — `puzzle.nudge.attempts`
already existed from CARD-016 exactly as needed, so this card is CLI-only
plus its test file:
- `src/nonogram/cli.py` (the print statement + docstring update)
- `tests/test_nudge_reporting.py` (new — AC-040/AC-041)

No other files touched; nothing outside the predicted `Touches:` scope.

**Tests added.**
- `test_export_reports_nudge_count` (AC-040) — drives the real CLI
  (`cli.main`) end to end in `--mode image` against the pre-existing pinned
  fixture `tests/fixtures/bands.png` at size 10, seed 1, which
  `tests/test_nudge.py::test_nudge_attempts_bounded_recovery_on_a_real_image`
  already pins at `puzzle.nudge.attempts == 2` — reused rather than
  re-deriving a new nudging fixture. Asserts `"2 cells were nudged"` appears
  in stdout.
- `test_export_omits_nudge_count_when_zero` (AC-041) — an ordinary
  `--mode random` run (which never enters the nudge loop, so the counter
  stays at its `0` default) asserts `"nudged"` does not appear anywhere in
  stdout at all.

Both run the real pipeline (real solver, real image conversion) rather than
scripting `puzzle.nudge` by hand, consistent with this codebase's stated
preference for exercising the real path over faking aggregate state.

**Test run result.** Fresh venv built in the worktree
(`python3.14 -m venv .venv && ./.venv/bin/pip install -e '.[dev]'`). Full
suite: `1155 passed, 1 xfailed` (baseline before this card: `1153 passed, 1
xfailed`; the +2 accounts exactly for the two new tests — no regressions).
The pre-existing xfail is unchanged: `tests/bench_generate.py::test_20x20_p95_is_under_5s`,
same AC-037/CARD-018 reason string as before this card, confirmed via
`pytest -rx`.

### Orchestrator notes

- **[Scope]** Touches match predicted minus `orchestrator.py` (needed no
  change — `puzzle.nudge.attempts` already existed from CARD-016). No
  deviation, no silent creep. G-1/G-2 confirmed clean (empty diff on
  `export/**`, `sourcing/**`, `solver/**`, `clues.py`, `difficulty.py`).
- **[Build gate]** PASSED (full, independently re-run by orchestrator using
  the implementer's own worktree venv: 1155 passed, 1 xfailed, exit 0;
  AC-037 xfail unchanged in status and reason).
- **[Review 1/3] 8.5/10 — FAIL (severity gate).** Report:
  `meta/review/20260829T104500Z-CARD-017-cycle1.yml`. Production code
  ruled correct — including an explicit ruling on the placement decision
  (printing after the export loop rather than right after `generate()`):
  the reviewer found the implementer's own rationale understated (the line
  actually still prints on a no-`--export` run; the *only* case it
  suppresses is an export `OSError`), and ruled the placement is not just
  defensible but the *better* choice — no artifact reached disk on that
  path, so there's nothing to disclose, and the count is deterministic and
  recoverable via re-run regardless. Two Important findings block merge
  regardless of score, both test-only:
  - F-001: the singular/boundary case (exactly 1 nudge) is completely
    untested — two of the four new production lines (`"cell"`, `"was"`)
    never execute in the suite, and the mutant `if nudged > 1:` survives.
    Fix: add a test reusing `test_nudge.py`'s existing single-nudge
    scripted source.
  - F-002: AC-041's test substitutes a random-mode run for the AC's stated
    "image conversion reached uniqueness with zero nudges" scenario —
    structurally can't reach the nudge branch, so it verifies the counter
    default rather than the AC's own given. A stronger pinned zero-nudge
    *image* fixture already exists (`wide.png`@20/seed 1) whose own
    docstring says it exists for exactly this card. Fix: point the test at
    it instead.
  One Minor (a rationale comment overstates the implemented condition —
  fix the comment, not the placement) deferred to the fix cycle alongside
  the two Important findings.
