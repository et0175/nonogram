# Puzzle Creation (CTX-001) — developer's perspective

## Why this matters to `developer`

Four rules in this package will fail your build before a reviewer sees your
branch, and three of them are `ast` walks rather than linters. If you add a module,
share a helper between capabilities, write a second tier comparison, or touch the
web form's CSS, you need to know them first. Everything else here — the boundary
types, the error semantics, the extension points — is the contract you code
against rather than a thing that can bite you.

The register also matters. Constants in this package carry the measurement that
set them. If you change one, the comment above it is part of the change.

## Description

Five things to internalise, in the order they will stop you.

**1. Imports point strictly inward.** Four ranks
(`tests/test_cli.py:762`-`765`), one comparison (`:885`), capability set discovered
from disk. Two capability modules sharing rank 2 may **not** import each other.
Full mechanism: [01 — the layered pipeline](../01-the-layered-pipeline.md).

**2. When two capabilities need the same logic, reimplement it and cross-check
from the test tree.** There are four shipped instances to copy the shape from, each
naming its predecessor:

| Duplicate | Original | Cross-check |
|---|---|---|
| `solver/propagate.py:403` `mask_runs` | `clues.encode_line` | pinned from the test tree |
| `difficulty.py:230` `RUNG_*` names | `solver.RUNG_ORDER` | pinned from the test tree |
| `web/submission.py:134` `_EXTENT_SEPARATOR` | `cli._EXTENT_SEPARATOR` | pinned from the test tree |
| `admin/app.py:390` `ALLOWED_HOSTS` | `web/handler.py:107` | "Two short allowlists that agree is the intended shape; one importing the other is not" |
| `admin/puzzle_review.py:503` `_as_readable_grid` | `admin/regrade._as_grid` | `tests/test_admin_uniqueness_boundary.py::TestTheTwoGridReaders_AgreeWithEachOther` |

**3. Boundary types are deliberately dull (ADR-0012).** Grids cross as
`list[list[bool]]`, clues as `tuple[tuple[int, ...], ...]` with `(0,)` and never
`()`, a partial assignment as `list[list[bool | None]]`, rung tags as
`list[list[str | None]]`. The solver's int-bitmask-per-line state **never** crosses
a module boundary in either direction. `solver/search.py:228` gives the reason for
the `Givens` type specifically and it generalises: "a *type* at that boundary would
have to be imported from here, which ADR-0007 forbids … A structure made of
builtins needs no import at all."

The rung names are `str` and not a `StrEnum`, with a footgun named at
`propagate.py:111`: "A `StrEnum` would compare equal to its value but hash by its
*name*, so `counts["line_dp"]` on a dict keyed by members would raise."

**4. Validation lives inward of the adapter, as pure functions.** `argparse`
expresses syntax only. There is no `choices=` on `--difficulty` or `--library-key`
and no `type=` range check on `--size` or `--density`, because the ACs want domain
errors with exit code 3 rather than usage errors with exit code 2. See the table in
[09 — the three inbound adapters](../09-the-three-inbound-adapters.md).

**5. The aggregate owns the invariants, one enforcement point each.** Do not add a
second. `Puzzle.record_candidate` is the only writer of grid-and-clues,
`confirm_uniqueness` the only writer of `ready_for_export`,
`RetryCounter.record_attempt` the only advance of any counter, and
`difficulty.classify` the only band comparison in the package.

## Examples

**The structural guard you are most likely to trip.** A new module under
`src/nonogram/` is covered the moment it lands:

```python
# tests/test_cli.py:772
for path in sorted(_PACKAGE_DIR.rglob("*.py")):
    parts = path.relative_to(_PACKAGE_DIR).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    modules[".".join(("nonogram", *parts))] = path
```

**The second-classifier guard.** `difficulty.classify` is the only implementation
of the band rule, enforced by an `ast` walk in
`tests/test_difficulty_tiers.py`. `difficulty.py:171`: "A module that compared a
score against `EASY_MAX_SCORE` itself would be a second classifier that a retune
could silently leave behind."

**The escaping guard in the web pages.**
`TestWebPages_EscapingRuleIsTheOneTheDocstringStates`
(`tests/test_web_server.py:2416`) walks `pages.py`'s AST and fails on any unescaped
interpolation absent from `_UNESCAPED_PAGE_INTERPOLATIONS`. A second test (`:2518`)
regexes the docstring's own numbers and asserts they equal the walk, so "a docstring
reworded from memory fails here rather than at the next review."

**The hazard that has already cost 48 test failures once.**
`tests/test_web_server.py:1937` harvests form fields with
`re.findall(r'name="([^"]+)"', pages.FORM_PAGE)` — over the **whole rendered page**,
CSS and inline script included — and compares the result to
`cli.build_parser()`'s destinations as two **exact** set equalities. A
`[name="x"]` selector in `_STYLE` or a `querySelector('[name="x"]')` in the inline
script is harvested as a form field and breaks both at once, with no mention of CSS
in any message. As shipped there are zero `name="` matches in `_STYLE`. Grep before
and after editing it.

**How to add an export format.** One row, nothing else:

```python
# export/__init__.py:231
_FORMATS: dict[str, ExportFormat] = {
    JSON: ExportFormat(JSON, ".json", json_export.render),
    ...
}
```

`cli.py:348` builds `--export`'s `choices` from `export.FORMATS`, so the flag, its
help text and its rejection of a misspelling all follow without the CLI being
touched. The extension lives in the row because "the extension is part of 'what
this format is'."

**How to add a sourcing mode.** Two rows, in two tables —
`sourcing._SOURCES` and `sourcing._SHAPES` — **and** a branch in
`orchestrator._source_arguments`. The `else` there raises, and `:1416` records why
it must: until CARD-015 the random shape was an implicit fallback, and "the moment
`image` was registered, that fallback would have called
`image.generate(size, density, rng)` and bound a file path to an integer, turning a
one-line wiring omission into a confusing failure several frames away."

**How to add a library template.** Drop a module in `sourcing/templates/` with a
docstring and an `ART` string and nothing else (checked structurally by
`tests/test_sourcing_library.py`), then add one row to `library._TEMPLATES`.
Deliberately two edits: "the registry is a literal dict of explicit imports, which
is what makes the available keys knowable by reading the source rather than by
running it." Note `dolphin.py` and `dog_in_house.py` have only had the first edit
and are unreachable.

**How to add a domain error.** Add the class to `errors.py` (which has no imports
and no behaviour), then decide whether it needs a row in `cli._EXIT_CODES`. If it
subclasses a mapped error it does not: `exit_code_for`'s MRO walk finds the group,
and `SizeTooSmallForSource` and `GivenCellsCapExceeded` both took that path. If it
is a new group, add the row — `INTERNAL_ERROR` is reserved for a mapping gap, i.e.
for a bug.

**How to bound a new loop.** Use the existing primitive. A loop kind is a
`RetryCounter` with its own bound plus a callable that returns a candidate or
`None`:

```python
candidate = run_bounded(puzzle.some_counter, attempt_something, reason="...")
```

Per-request state goes in the **closure** the callable shares with the loop, not
in `run_bounded`, which is deliberately stateless — "the primitive counts, the
callable decides what to try next" (`orchestrator.py:1893`). Both POL-006's repair
lineage and POL-002's nudge cell list are written that way.

## Interface contracts, error semantics, extension points, enforced invariants

### Contracts

| Call | Signature | Notes |
|---|---|---|
| `clues.compute_clues(grid)` | → `Clues(rows, columns)` | raises `ValueError` on a ragged grid — a programming error, not a domain one |
| `solver.solve(row_clues, column_clues, *, givens=None, deadline=None)` | → `SolveResult` | pure for a given `deadline`; `solution_count ∈ {0, 1, MANY}` where `MANY == 2` means "≥ 2" |
| `solver.choose_givens(grid, rows, cols, *, cap, deadline=None)` | → `Givens` | raises `GivenCellsCapExceeded`; pure, no rng |
| `difficulty.score_difficulty(signals)` | → `float` in 0..100 | total; refuses no input; no clock, no solver re-entry |
| `difficulty.classify(score)` | → `Tier` | one argument since CARD-098; total on the whole real line |
| `difficulty.parse_tier(text)` | → `Tier` | **rejects** — the input rule (AC-021) |
| `difficulty.tier_of_record(value)` | → `Tier \| None` | total, never raises — the *reading* rule for stored or submitted text |
| `export.write(payload, name, *, directory, stem)` | → `Path` | raises `ValueError` (unknown format) or `OSError`; auto-suffixes on collision |
| `layout.compute_layout(row_clues, column_clues, spec=None)` | → `Layout` | no grid parameter, by design; `None` spec is A4, byte-identical |
| `orchestrator.generate(request, *, names=None)` | → `Puzzle` | see the `Raises:` block at `orchestrator.py:1714` — eight named errors |
| `orchestrator.export_puzzle(puzzle)` | → `tuple[Path, ...]` | INV-002's gate in the export direction; empty tuple when no format was asked for, and **the gate is not consulted then** |

### Error semantics

Every domain failure is a `NonogramError` subclass from `errors.py`. Two places
map them outward and they are deliberately different taxonomies:

- **CLI** — `cli.exit_code_for` groups them by remedy into six exit codes.
- **Web** — no table at all. `handler.py:886`: "Sorting domain outcomes into HTTP
  status families would be a second error taxonomy beside `cli.exit_code_for`'s
  exit-code table — the adapter drift ADR-0019 names as the accepted cost of two
  adapters." Every domain failure is **HTTP 200** with the error's own `str()`.
  400/404/413/501 are transport refusals only.
- **Admin** — Flask `abort`/status per route, with specific codes carrying meaning:
  **409** for INV-008's unconfirmed change to a published book and for INV-009's
  re-grade of a booked puzzle; **401** with `WWW-Authenticate` for a missing
  credential; **403** for a cross-site request; **404** for a `Host` the panel does
  not answer to.

Three errors are *not* `NonogramError` on purpose: `ValueError` for an
unregistered mode or format (a wiring bug, since argparse already refused the
user's spelling), `RuntimeError` from `RetryCounter.record_attempt` (a caller drove
a counter past its bound by hand), and `OSError`/`OverflowError` from a failed
bind ("'this port is taken' is not a fact about puzzles").

`errors.NotUniquelySolvable` deliberately collapses "disproven" and "unproven" into
one class, "because no caller has a different thing to do about them"
(`errors.py:143`).

### Invariants the code enforces, and where

| | Where |
|---|---|
| INV-001 clues == RLE of grid | `Puzzle.record_candidate` (`orchestrator.py:1174`) |
| INV-002 export gated on uniqueness | `confirm_uniqueness` (`:1214`) writes, `require_ready_for_export` (`:1307`) reads, `export_puzzle` (`:2517`) calls |
| INV-003 counter within bound | `RetryCounter.record_attempt` (`:605`) |
| CON-005 no false-positive uniqueness | re-encode-and-compare on every completed board, which **raises** on mismatch (`solver/search.py:100`) |
| INV-005..INV-013 (Book) | see the table in [07](../07-book-assembly-and-the-admin-panel.md) |
| the storage guard | `admin/puzzle_review.py:607` — re-derives clues, never trusts `clues_rows` |

### Test style, because it is a contract too

No `hypothesis`. "Property" tests build seeded corpora by hand with
`random.Random` and **assert the case count inside the test** so the corpus cannot
silently shrink — `REQUIRED_CASES = 1000` against `CASE_COUNT = 2400`, and
`REQUIRED_GIVEN_CASES = 500` against `GIVEN_CASE_COUNT = 1500`
(`tests/property/test_solver_uniqueness.py`). Seeds are pinned and separate so
re-pinning one does not reshuffle the other.

Prefer an independent second implementation over re-deriving a value with the
function under test. `tests/helpers/brute_force_oracle.py` **must never import
`nonogram.solver`** (`:6`), and its own two counters cross-check each other because
"an oracle nobody has verified is just a second guess."

Playwright tests are marked `browser` and need `playwright install chromium`;
without it they **fail with that instruction rather than skipping green**
(`pyproject.toml:30`).

## Related docs

- Narrative: [01](../01-the-layered-pipeline.md) · [03](../03-deriving-clues.md) · [04](../04-uniqueness-and-recovery.md) · [05](../05-difficulty-calibration.md) · [06](../06-exporting-a-finished-puzzle.md) · [09](../09-the-three-inbound-adapters.md)
- Siblings: [architect](architect.md) · [sre](sre.md) · [puzzle-creator (ACT-001)](puzzle-creator.md)
- ADRs: [ADR-0007](../../../../../meta/architecture/decisions/adr/0007-internal-module-architecture.md) · [ADR-0010](../../../../../meta/architecture/decisions/adr/0010-cli-argument-parsing.md) · [ADR-0012](../../../../../meta/architecture/decisions/adr/0012-grid-data-representation.md) · [ADR-0014](../../../../../meta/architecture/decisions/adr/0014-uniqueness-correctness-oracle.md)
- `CLAUDE.md` — the repo's own quickstart. **Several of its claims are behind the code**; the deltas are listed in [architect](architect.md) and in the root [README](../../../README.md).
