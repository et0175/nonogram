# CARD-013: CSV export and exact round-trip fidelity

**Status:** review
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/013-csv-export-roundtrip
**Worktree:** ../PythonProject4-card-013
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 6
**Depends on:** CARD-006, CARD-007
**Touches:** src/nonogram/export/csv_export.py, src/nonogram/export/json_export.py, src/nonogram/export/__init__.py, tests/test_export_csv.py, tests/property/test_export_roundtrip.py
**Review score:** 9.0 (cycle 1/3, awaiting cycle 2 confirmation)
**Started:** 2026-08-28T10:17:03Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Completes FR-012: CARD-007 delivered the JSON writer; this card adds CSV and proves the
round-trip property that makes both formats trustworthy as an interchange representation.

1. `export/csv_export.py` — write the full solution grid and the row/column clues. CSV is
   flat, so pick a layout that survives decoding unambiguously (e.g. a grid block and a
   clue block with explicit section markers, or a header row naming each block) and document
   it in the module docstring. Ragged clue rows must round-trip exactly, including the
   empty-row marker `[0]`.
2. A **decoder** for both JSON and CSV (the JSON decoder lands alongside CARD-007's writer in
   `export/json_export.py` — that file is this card's to extend, the CSV half is new). The
   round-trip is not testable without one, and EC-002 asserts a property of the pair, not of
   the writer alone.
3. Register `csv` in `export/__init__.py`'s dispatch table. `--export`'s accepted values are
   derived from that registry (CARD-007), so this card needs **no** `cli.py` edit.
4. EC-002's property test: for any finalized puzzle, decode → compare. Round-trip fidelity
   holds because ADR-0012 exports the boundary type (`list[list[bool]]` + clue tuples), never
   the solver's internal bitmask — if a change here makes the property fail, the fix is the
   representation, not the tolerance.

## Acceptance criteria

- **AC-032** (happy) — given a finalized, uniqueness-confirmed puzzle, when it is exported as
  CSV, then the CSV file contains the full solution grid and clues.
  *test:* `TestExport_WritesCSV`
- **AC-033** (boundary) — given a puzzle exported as JSON, when that JSON is decoded back,
  then the resulting grid and clues are exactly identical to the original puzzle's.
  *test:* `TestExport_JSONRoundTripsExactly`

## Engineering constraints

- **EC-002** (consistency, instances: AC-033) — For any finalized puzzle, decoding its
  exported JSON or CSV representation reproduces the exact original solution grid and clues.
  *test:* `PropertyTest_Export_RoundTripsExactlyForAnyPuzzle`
  A genuinely multi-case property test: generate puzzles across the supported size range and
  a spread of densities (including all-empty and all-filled lines), export, decode, and
  assert exact equality of both grid and clues — for **both** formats, not just JSON.

## Guardrails

- G-1: Do not edit `src/nonogram/export/png.py`, `src/nonogram/export/svg.py`,
  `src/nonogram/export/layout.py` — owned by CARD-012 this wave. `export/__init__.py` is
  shared with CARD-012 (both register a format): keep the edit to adding a row to the
  dispatch table, never restructuring it
- G-2: Do not edit `src/nonogram/sourcing/**` (CARD-008), `src/nonogram/difficulty.py`
  (CARD-009), `src/nonogram/orchestrator.py` and `src/nonogram/cli.py` (CARD-008/CARD-011
  this wave)
- G-3: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py` — export is additive on
  top of Increment 1 and must revert without touching the solver or the orchestrator's core
  generation logic (handoff Increment 2 Rollback)
- G-4: Serialize the ADR-0012 boundary type only — never the solver's internal bitmask.
  EC-002's fidelity is a consequence of that decision (trace.yml FR-012 note)
- G-5: No new dependency — stdlib `json` and `csv` (ADR-0006)
- G-6: Out of scope — no PDF (CARD-014), no interactive/playable output (CON-002)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-012 (completion — CSV + round-trip)
- **NFR:** —
- **EC:** EC-002
- **CON:** CON-002
- **ADR:** ADR-0012, ADR-0015
- **Components:** COMP-007 (Export Renderers)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

### Summary

FR-012 completed: CSV export, decoders for both formats, and EC-002's property test.

- **`export/csv_export.py`** (new) — `document(payload) -> str`, `render(payload, path)`,
  `decode(text) -> ExportPayload`, `read(path) -> ExportPayload`. Stdlib `csv` only (G-5).
- **`export/json_export.py`** — CARD-007's `document`/`render` untouched; added the inverse
  half, `parse(document)` / `decode(text)` / `read(path)`, in the same style (the
  `document`↔`parse` pair mirrors the existing `document`→`render` split, so the shape is
  still assertable without a filesystem).
- **`export/__init__.py`** — one added row, `CSV: ExportFormat(CSV, ".csv", csv_export.render)`,
  plus the `CSV = "csv"` constant and the `csv_export` import (G-1: additive, the table was
  not restructured). `cli.py` and `orchestrator.py` untouched — `--export csv` works because
  argparse's choices come from the registry (verified end to end by
  `test_the_cli_accepts_csv_without_the_adapter_being_edited` and a manual CLI run).
- Both decoders return an `ExportPayload`, so the decode is the exact inverse of the render
  including ADR-0015's provenance. `ExportPayload` is imported *inside* the two functions:
  `export/__init__.py` imports these modules to build its registry, so the boundary type is
  only bound after that import finishes — which it always has by call time.
- G-4 held: only ADR-0012's boundary type is serialized (`list[list[bool]]` cell by cell,
  clues as integer tuples). Both decoders reject the numeric/bitmask spellings outright, so
  the internal representation cannot leak back in through the reader either.

Two pre-existing tests in `tests/test_export_json.py` had to move (not in the predicted
Touches, but they asserted the registry's *former* contents):
`test_the_registry_knows_the_json_format` pinned `FORMATS == (export.JSON,)` — now asserts
membership plus no duplicate names, so CARD-012/CARD-014's rows will not break it; and
`test_an_unregistered_format_is_rejected_by_the_cli` used `"csv"` as its stand-in for an
unknown format — now `"pdf"` (CARD-014's, still unregistered). The JSON decoder's rejection
cases were added to that file too, next to CARD-007's writer tests.

### The CSV layout (the design decision of this card)

CSV is flat and this export holds three different shapes — scalar metadata, a rectangular
0/1 matrix, and two *ragged* integer-tuple lists. The layout says in the file itself where
each block starts. Four sections, each opened by a one-cell marker row, in this fixed order:

```
#meta
version,1
seed,42
mode,random
size,4
density,50
#grid
1,1,0,0
0,0,0,0
1,1,1,1
0,1,1,0
#row-clues
2
0
4
2
#column-clues
1,1
1,2
2
1
```

Decisions and why:

- **`#`-prefixed marker rows.** Every data row in every section is a row of bare integers,
  so no data row can be read as a marker and no marker as data. Alternative considered and
  rejected: header rows naming the columns — they cannot delimit a *ragged* block, since a
  clue row and a header row are both "some cells".
- **Fixed order, each section exactly once.** The decoder checks that the markers seen, in
  the order seen, are exactly `SECTIONS`. Accepting any order would also accept a file whose
  two clue blocks were swapped — a silent transposition, which is a fidelity bug, not an
  error a user would notice.
- **`#meta` is `key,value` rows**, all five keys required, no others accepted. `size`/`density`
  are `int | None` in the payload (ADR-0015 records them *as asked for*, and "not asked" is a
  real answer), so `None` is an empty value — `size,` — and decodes back to `None`, never `0`
  or `""`.
- **Grid cells are `1`/`0` and nothing else.** Cell by cell, not one integer per line: a
  bitmask would make the file's fidelity depend on bit order and mask width (G-4). The
  decoder rejects `true`, `2` or an empty cell, so two different files can never decode to
  the same grid.
- **Clue rows are written ragged, never padded.** CSV's raggedness is the feature here:
  padding to the longest clue would put cells in the file that a decoder has to guess were
  not really runs.
- **The `(0,)` empty-line marker round-trips as a `0` cell**, so it comes back as `(0,)` and
  never as `()`. Note this module does *not* need to know `clues.EMPTY_LINE_CLUE` — it
  serializes whatever tuples it is handed. What it does instead is close the one hole: an
  empty clue tuple `()` would serialize to a blank line, indistinguishable from a stray one,
  so **`decode` rejects a blank row anywhere**, including a trailing blank line at the end of
  the file (which would otherwise be one more `#column-clues` entry). The single input that
  could not survive the round trip therefore fails loudly instead of coming back altered.
- The decoder is strict throughout — 18 documented rejection cases in
  `tests/test_export_csv.py`, 15 more for JSON in `tests/test_export_json.py`. Deliberate:
  EC-002 is a *fidelity* property, and a decoder that repaired what it read would still
  "round-trip" a file it had quietly altered while the property passed.
- Line terminator is `\n` (not `csv`'s default `\r\n`) to match the JSON renderer; the reader
  accepts either, so a file that made a round trip through a Windows tool still decodes.

### The property test's corpus (EC-002)

`tests/property/test_export_roundtrip.py`, house style: one module-level `SEED = 20260828`,
a seeded `random.Random`, no `hypothesis` (ADR-0006's baseline is closed), and the case count
asserted *inside* the tests so the corpus cannot quietly shrink below the bar.

- **2030 cases** = 2000 drawn + 30 hand-picked. `REQUIRED_CASES = 500` is the asserted floor.
- **Sizes 1..50, cycled not sampled** — every edge length is drawn exactly 40 times, and
  `test_the_corpus_covers_what_ec_002_asks_for` asserts `{sizes} == set(range(1, 51))`. A
  uniform sample would leave some size uncovered on some seeds.
- **Densities** `(0.0, 0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95, 1.0)`, cycled — both extremes in
  deliberately: 0.0 gives the all-empty lines the `(0,)` marker exists for, 1.0 the all-filled
  ones. Asserted: >= 100 cases contain an all-empty line, >= 100 an all-filled line.
- **Hand-picked degenerate shapes** the draw would essentially never produce: fully empty,
  fully filled, a single filled cell, alternating stripes and a checkerboard (the most runs a
  line can hold), each at sizes 1, 2, 3, 10, 49, 50.
- **Provenance varies too** — modes cycle through `random`/`library`/`image`, seeds are drawn,
  and every 7th/11th case leaves `size`/`density` unrequested (`None`). >= 100 such cases
  asserted. Per ADR-0015's warning, the grid/clue equality and the provenance equality are
  asserted as two *separately worded* claims, so neither stands in for the other.
- **Clues are derived** with `compute_clues` (INV-001), so the corpus is a corpus of puzzles
  rather than of arbitrary integer tuples.
- **Where the files are.** The two per-format property tests run the serializer pair in
  memory (full corpus, ~0.4 s each); `test_a_slice_of_the_corpus_round_trips_through_real_files`
  puts every 19th case (107 of them, spanning all 50 sizes — the stride is coprime with both
  the size cycle of 50 and the density cycle of 9) through `render` → `read` on disk, so the
  file layer is covered without paying 4000 temp files for it. AC-033 and its CSV twin are
  end-to-end on top: `generate` at the pinned seed 0 / 10x10 / 50%, `export_puzzle`, decode,
  compare — the property tied to an actually uniqueness-confirmed puzzle.
- **Mutation-checked.** Four injected bugs were each caught by the property test at case 0:
  an empty meta cell decoding to `0` instead of `None`; `(0,)` collapsing to `()`; clues
  decoding to lists instead of tuples; grid cells decoding to ints instead of bools.

### Results

`./.venv/bin/python -m pytest -q` → **700 passed, 1 xfailed** in ~17 s (the xfail is the
pre-existing, already-tracked AC-037 benchmark gate — not this card's). Baseline before the
card was 637 passed + 1 xfailed, so +63 tests and no regressions.

No blockers.

[Scope] Predicted Touches matched, plus tests/test_export_json.py (outside prediction — 2 pre-existing "registry has exactly one row" assertions updated to membership checks, same pattern as CARD-007/012's scope notes). cli.py, orchestrator.py untouched (registry-driven, no wiring needed). export/png.py, svg.py, layout.py untouched (G-1). sourcing/**, difficulty.py, solver/**, clues.py untouched (G-2/G-3).
[Build gate] PASSED (full, independently re-run by orchestrator: 701 collected, 700 passed, 1 xfailed, 0 failed, exit 0).
[Review 1/3] Score: 9.0 — crit: 0, imp: 1. CSV layout design independently verified sound via adversarial probing beyond the property test's own corpus (mode="#grid", embedded newlines/quotes/commas, empty string — all round-trip correctly). EC-002 property test independently verified rigorous: reviewer reproduced all 4 claimed mutation catches by injection, confirmed 2030-case corpus with 500-case floor asserted in-test, confirmed both formats covered, confirmed all-empty/all-filled line coverage floors. Guardrails G-1..G-6 all ✓ holds (import-audited: no solver representation reachable from either serializer). Important finding: (I-1) neither decoder cross-checks clue counts against grid dimensions — demonstrated: dropping the last line of a valid CSV/JSON export decodes silently into a wrong-shaped puzzle instead of raising. Not a round-trip-property violation (document() never emits such a file, so EC-002's own corpus can't reach this branch) but a real gap in the "decoder is strict throughout" claim, and a realistic failure mode (truncated download, partial write, hand-edited file). 2 Minor findings: (M-1) JSON tolerates unknown fields while CSV rejects them — asymmetric strictness, contradicts JSON's own docstring claim; (M-2) the property test's type-fidelity guard doesn't cover clue *element* types (a runs-decoded-as-bool mutation escapes undetected in 0/2030 cases) — production code is safe (json_export explicitly rejects bool for int fields), so this is a test-coverage gap, not a code defect. Reviewer's own verdict was PASS treating I-1 as a "decoder-hardening gap not a contract violation," but per the severity gate an Important finding routes to a fix cycle regardless of score/framing. → routed to fix cycle.
[Rebase] Rebased onto main (CARD-008/009/012 merged first) before the fix cycle — resolved the expected export/__init__.py conflict (kept both CARD-012's png/svg rows and this card's csv row) plus tests/test_export_json.py's registry-membership test (merged both cards' independent fixes into one assertion covering membership + render identity + no-duplicate-names). Independently re-verified: 884 collected, 884 passed, exit 0, clean rebase.
[Fix 1] I-1 resolved: added `_check_clue_counts` to both csv_export.decode and json_export.parse, checking len(row_clues)==len(grid) and len(column_clues)==len(grid[0]) (0 if grid empty, matching clues.compute_clues's own convention) — raises ValueError in the same style as existing rejection cases. New tests reproduce the reviewer's literal example plus a genuine truncation (dropped last CSV line / popped last JSON clues.columns entry) plus a confirming test that the legitimate empty-grid/no-clues case still decodes. 893/894 passed (1 pre-existing xfail), independently re-verified by orchestrator. EC-002's property test confirmed unchanged — the new check only rejects shapes the encoder never emits.
