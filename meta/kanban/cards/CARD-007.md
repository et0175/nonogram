# CARD-007: JSON export and the export-readiness gate

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/007-json-export
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 5
**Depends on:** CARD-005
**Touches:** src/nonogram/export/__init__.py, src/nonogram/export/json_export.py, src/nonogram/orchestrator.py, src/nonogram/cli.py, tests/test_export_json.py, tests/test_cli.py
**Review score:** 9.4 (cycle 2/3)
**Started:** 2026-08-28T08:42:21Z
**Closed:** 2026-08-28T09:13:07Z
**Actual:** 0.1d
**Merge commit:** d4fa0c9
**Blocked by:** —

## What to implement

COMP-007 (Export Renderers), **JSON only** — the minimal export that closes the
increment-1 walking skeleton (`nonogram generate --mode random --size 10 --seed 42
--export json` end to end). The other four formats are Increment 2.

1. `export/__init__.py` — the format registry / dispatch table plus the shared "write to
   `--out`" plumbing. Keep it a thin table: CARD-012 (PNG/SVG), CARD-013 (CSV) and CARD-014
   (PDF) each add a row, so the table is the one shared file in this module and must stay
   trivial to extend. **Derive `--export`'s accepted values from this registry** rather than
   listing them in `cli.py` — that is what lets the four later format cards ship without
   editing the CLI adapter at all.
2. `export/json_export.py` — serialize the finalized puzzle: the full solution grid and the
   row/column clues, in the ADR-0012 boundary types (`list[list[bool]]` + clue tuples),
   never the solver's internal bitmask. Also record the seed (ADR-0015) so an exported
   puzzle can be traced back to the request that produced it.
3. **Wire the INV-002 gate.** Export is refused unless the orchestrator's
   `ready_for_export` flag is set (CARD-005 owns the flag; this card is its first consumer).
   The check is enforced in COMP-002, not inside the renderer — ADR-0007's
   single-enforcement-point rule, so all five formats inherit one gate rather than five.
4. CLI wiring: `--export json --out <path>` writes the file and reports the written path.

## Acceptance criteria

- **AC-031** (happy) — given a finalized, uniqueness-confirmed puzzle, when it is exported
  as JSON, then the JSON file contains the full solution grid and clues.
  *test:* `TestExport_WritesJSON`

_Note: FR-012's CSV output (AC-032), the exact round-trip (AC-033) and EC-002's round-trip
property test are CARD-013 — this card delivers FR-012's JSON half per the Increment 1
scope line ("minimal JSON export (FR-012, partial)")._

## Guardrails

- G-1: Do not edit `src/nonogram/solver/**`, `src/nonogram/errors.py` — `solver/**` and the
  error hierarchy's timeout additions are owned by CARD-006 this wave
- G-2: Do not edit `src/nonogram/sourcing/**`, `src/nonogram/clues.py`, `pyproject.toml` —
  outside this card's footprint. Serialization uses stdlib `json`; the ADR-0006 dependency
  baseline is closed
- G-3: The INV-002 readiness gate is enforced in COMP-002 (`orchestrator.py`), not inside
  the renderer (ADR-0007, trace.yml FR-011 note). Do not duplicate the check into
  `export/`
- G-4: The exported representation is the ADR-0012 boundary type. Do not export the solver's
  internal bitmask — EC-002's round-trip fidelity (CARD-013) depends on that choice
- G-5: Out of scope — no PNG, SVG, CSV or PDF renderer (Increment 2: CARD-012, CARD-013,
  CARD-014), and no interactive/playable output ever (CON-002)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-012 (partial — JSON half)
- **NFR:** —
- **INV:** INV-002
- **CON:** CON-002, CON-003
- **ADR:** ADR-0007, ADR-0012, ADR-0015
- **Components:** COMP-007 (Export Renderers), COMP-002 (readiness gate)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

### Summary

Increment 1's walking skeleton closes: `nonogram generate --mode random --size 10
--density 50 --seed 42 --export json --out DIR` now writes a real file and prints
its path. 617 tests pass (582 pre-existing, unchanged; 35 new in
`tests/test_export_json.py`). No blocker.

Files:

- `src/nonogram/export/__init__.py` (new) — COMP-007's format registry and the
  shared write-to-`--out` plumbing.
- `src/nonogram/export/json_export.py` (new) — the JSON renderer.
- `src/nonogram/orchestrator.py` — one additive function, `export_puzzle()`, plus
  one import and one `__all__` entry; `generate()` itself is untouched.
- `src/nonogram/cli.py` — `--export` choices derived from the registry; `_run_generate`
  reports the written paths and (ADR-0015) an auto-drawn seed.
- `tests/test_cli.py` — the `captured_requests` fixture now also stubs
  `orchestrator.export_puzzle`; see "Test-file edit outside Touches" below.

### Structure: why the registry derives the CLI's `--export` choices

`export/__init__.py` mirrors `sourcing/__init__.py`'s shape — a private `_FORMATS`
dict, a public `FORMATS` tuple, a `for_format()` lookup that raises `ValueError`
(not a `NonogramError`) because an unknown format is a wiring bug, not user input
argparse already rejected. Two deliberate differences from `sourcing`:

1. **A row is a record, not a bare callable.** `ExportFormat(name, extension, render)`.
   The three sourcing modes do not share a parameter list, so `for_mode` returns a
   callable and stops there. The five export formats *do* share one — render this
   puzzle to this path — so the table can also own the one other per-format fact
   there is, the file extension. CARD-012/013/014 then add exactly one line each and
   nothing outside this file learns a per-format special case.
2. **`cli.py` reads `FORMATS` instead of repeating it.** `sourcing`'s docstring says
   the CLI "mirrors these strings" for `--mode`; this card's item 1 explicitly
   overrides that for formats, and the reason is the four follow-on cards. With
   `choices=list(export.FORMATS)` and a help string built from the same tuple, adding
   a registry row makes the new format parse, appear in `--help`, and be rejected when
   misspelled — with the adapter untouched. `test_registering_a_format_reaches_the_cli_without_editing_the_adapter`
   pins that claim by monkeypatching a fake `"svg"` row in and parsing it; it is the
   test that fails if someone later re-hardcodes the list.

   Layering check: `cli -> export` skips the orchestrator, which ADR-0007's rule
   (`rank(imported) > rank(importer)`) permits and `tests/test_cli.py::test_every_import_in_the_package_points_inward`
   confirms. The alternative — re-exporting the tuple through the orchestrator — would
   put a capability's registry on COMP-002's surface to avoid an import that is already
   legal and inward.

### Structure: the gate, and why export is a second orchestrator call

`export_puzzle(puzzle)` is a separate function, **not** a tail of `generate()`.
Two reasons, one of which is a pre-existing test:

- `tests/test_orchestrator.py::test_a_run_writes_no_files` asserts `generate()` writes
  nothing even when the request carries `out=` and `export_formats=("json",)`. That is
  CON-003 stated as a property of the pure pipeline, and it still holds.
- The abandonment path (`test_an_abandoned_run_writes_nothing`) stays trivially true,
  and any non-CLI caller can generate without opting out of I/O.

INV-002 is enforced in exactly one place — `export_puzzle` calls the existing
`Puzzle.require_ready_for_export()` (CARD-005) before building anything (G-3). Nothing
in `export/` can re-check it, and that is structural rather than conventional:
`ExportPayload` has no readiness field, and `export/` cannot import the orchestrator
under ADR-0007 anyway. `test_the_renderer_does_not_re_check_readiness` asserts both.
The gate is skipped entirely when no format was requested — a run that asked for no
export cannot be "refused" one.

G-4: what crosses into `export/` is `list[list[bool]]` + `tuple[tuple[int, ...], ...]`
+ seed/mode/size/density (ADR-0012 boundary types, ADR-0015 provenance). The solver's
bitmask never leaves `solver/`. `json_export.document()` is split from `render()` so
the shape is assertable without a filesystem and CARD-013's round-trip (AC-033/EC-002)
has one function to invert. Document shape: `version`, `seed`, `request{mode,size,density}`,
`grid`, `clues{rows,columns}`.

### Decision: the default `--out` filename

Checked `meta/architecture/` first (as instructed) rather than inventing one. Three
existing sources, none of which cover the JSON case directly:

- **ADR-0016** fixes `<puzzle-name>-<difficulty>.pdf` — but scoped to FR-016, and both
  inputs are later cards (FR-015's name, FR-008's difficulty). Not available now.
- **FR-015 / AC-042** *does* fix the auto-generated **name**: `"random-2026-08-27-1430"`
  (mode + timestamp to the minute) for random-sourced puzzles.
- **ADR-0017** fixes the collision policy: auto-suffix `-1`, `-2`, never overwrite.

Decisions taken:

1. **`--out` is a directory, not a file path.** The flag's existing help text already
   said "Where exports are written (default: the working directory)", and `--export` is
   repeatable — one run can ask for several formats, which have to land as several files
   somewhere the user chose. So `--out` names that directory (created if missing) and the
   filename is always computed. Help/metavar updated to `DIR` to say so out loud.
2. **Stem = FR-015's own convention, computed now**: `export.default_stem(mode)` returns
   `f"{mode}-{now:%Y-%m-%d-%H%M}"` — literally AC-042's format. Deliberately *not* a new
   convention: when FR-015 lands and the aggregate carries a `name`, the caller reads
   `puzzle.name` instead and the filenames users already have keep their shape. Adding a
   `name` field to `Puzzle` now would be FR-015's card, so it was not done (`moment=` is
   injectable purely so the convention is testable without freezing the clock).
3. **Collisions auto-suffix (ADR-0017), applied here.** ADR-0017's letter is FR-016/PDF,
   but its reasoning is about a *computed* export path colliding, which is exactly this
   case — two runs of the same mode in the same minute. Since every path this plumbing
   produces is computed (see 1), the policy applies uniformly and lives in the one shared
   `write()` so all five formats inherit it, in the same spirit as the single gate.
   Applying the project's own accepted decision to the analogous case seemed better than
   silently overwriting, which ADR-0017 explicitly rejects as data loss.
4. **Repeated formats are collapsed** (`--export json --export json` writes one file):
   the user asked for JSON, not for two copies of it.

### Two small inclusions worth flagging at review

- **The seed echo.** ADR-0015 (in this card's ADR list) states as a standing consequence
  that when `--seed` is absent the drawn seed "must be printed to the user at run time",
  and `_run_generate`'s CARD-001 placeholder comment named it alongside the export paths
  as the reporting this card's area owns. It is one guarded `print` and its absence would
  leave an unseeded run's only record inside a file the user may not have asked for.
- **Test-file edit outside the predicted Touches.** `tests/test_cli.py`'s
  `captured_requests` fixture replaces the pipeline with a recorder; the adapter now makes
  two inward calls, so the fixture stubs `export_puzzle` too. Without it those argv tests
  would either hit the INV-002 gate on their fake unready puzzle (exit 5) or drop files in
  the working directory. The fixture's stated intent is unchanged; no assertion was
  touched. No guardrail covers `tests/**`, and `src/nonogram/solver/**`, `errors.py`,
  `sourcing/**`, `clues.py` and `pyproject.toml` were all left alone (G-1, G-2, G-5).

### Merge note (parallel CARD-006)

Kept the `orchestrator.py` footprint minimal for the expected rebase: one word added to
the existing `from nonogram import ...` line, one `__all__` entry, one two-line docstring
correction (the module header said the export file is "written by COMP-007 in a later
card"), and a new function appended at the end of the file. `generate()`, `run_bounded()`,
`RetryCounter` and `Puzzle` are byte-identical to main.

[Scope] Predicted Touches plus tests/test_cli.py (outside prediction — fixture updated to stub the new export_puzzle call so existing argv tests don't hit the gate or write files; no assertion changed). No file under solver/**, errors.py, sourcing/**, clues.py, pyproject.toml touched (G-1/G-2/G-5 held).
[Build gate] PASSED (full, independently re-run by orchestrator: 617 passed, 0 failed, no regressions vs the pre-CARD-007 582).
[Review 1/3] Score: 9.0 — crit: 0, imp: 1. Scope flag ruled justified GROWN (tests/test_cli.py diff verified +9/-0, fixture-only, no assertion changed). All 5 guardrails independently verified. Manual exercise confirmed a real JSON file with correct shape, ADR-0017 collision suffixing, and the ADR-0015 seed echo — all working as designed. Important finding: (I-1) `--out` pointing at an existing file (or an unwritable dir) crashes with a raw traceback (unhandled OSError/FileExistsError escapes cli.py's exception handling, which only catches NonogramError) — reproduced by the reviewer. This is the first card to touch the filesystem, so it's a newly-introduced user-facing gap, and likely: this card itself changed --out's metavar from PATH to DIR, so passing a filename is the obvious mistake. G-1 forbids adding a new NonogramError subclass this wave (errors.py is CARD-006's territory) — reviewer's suggested fix: catch OSError directly in cli.py (in scope) and map it to a clean message + exit code, without touching errors.py. 4 Minor findings, none gating: (M-1) cli->export is a real import edge the C4 diagram doesn't draw yet (permitted by the layering rule, just undocumented); (M-2) one shared filename stem will need to become per-format at CARD-014 (PDF's ADR-0016 naming) — noted there; (M-3) tests reach into a private _FORMATS dict (justified, no public API exists yet); (M-4) a TOCTOU race in collision-path selection, low severity for a single-process CLI. → routed to fix cycle.
[Fix 1] I-1 resolved: added `except OSError` in cli.py's main() (after the existing NonogramError clause), printing "nonogram: error: <message>" and returning ExitCode.EXPORT_REJECTED (5) — reused rather than adding a new code, since an OSError from export.write() can only surface during the export step, which already owns that code. errors.py untouched (CARD-006's territory this wave) per constraint. Added a test reproducing the exact reported scenario through the real CLI, asserting exit 5, a clean stderr message, no "Traceback" substring, and that the colliding file is untouched. 618/618 passed (617+1), independently re-verified by orchestrator. Manually reconfirmed: the reported repro command now exits cleanly instead of crashing.
[Review 2/3] Score: 9.4 ✓ — crit: 0, imp: 0. I-1 independently re-verified resolved: reviewer reproduced both the file-collision AND a permission-denied case manually (chmod 500), confirmed RuntimeError/non-domain exceptions still propagate uncaught, confirmed clause ordering is safe (NonogramError doesn't extend OSError), and independently verified the "OSError can only come from export today" premise by grepping sourcing/** and orchestrator.py for other file I/O (found none). errors.py confirmed untouched. 618/618, 0 regressions. 1 new forward-looking Nit (N-1, non-blocking): the except OSError wraps the whole args.handler call, not just the export step — harmless today but will misreport a future image-sourcing file-read error as "export rejected" (exit 5) once CARD-015/016 land; noted there. Final verdict: PASS — ready to merge.
