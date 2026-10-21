# 06 — Exporting a finished puzzle (CAP-005 / COMP-007)

> Scope: `src/nonogram/export/` — 7,081 lines, of which `layout.py` alone is
> 4,838. Five renderers, one shared geometry module, one registry.

> **CLAUDE.md is stale here.** Its component map says `export/  COMP-007  not yet
> built`. All five formats ship: `_FORMATS` (`export/__init__.py:231`) registers
> `json`, `png`, `svg`, `csv`, `pdf`, and `tests/test_export*.py` plus
> `tests/property/test_export_roundtrip.py` and
> `tests/property/test_cli_exports_byte_identity.py` exercise them.

## Why the registry is trivial, and why that is the design

`export/__init__.py` is a lookup table plus the modules behind it:

```python
_FORMATS: dict[str, ExportFormat] = {
    JSON: ExportFormat(JSON, ".json", json_export.render),
    PNG:  ExportFormat(PNG,  ".png",  png.render),
    SVG:  ExportFormat(SVG,  ".svg",  svg.render),
    CSV:  ExportFormat(CSV,  ".csv",  csv_export.render),
    PDF:  ExportFormat(PDF,  ".pdf",  pdf.render),
}
FORMATS: tuple[str, ...] = tuple(_FORMATS)
```

**This registry is the only list of format names in the codebase.** `cli.py:348`
derives `--export`'s `choices` from `export.FORMATS` rather than repeating them,
which `export/__init__.py:9` names as the whole point of keeping the table
trivial: CARD-012/013/014 each added one row here and the CLI picked the new
format up — its flag, its help text, and its argparse rejection of a misspelling —
without being edited at all. The extension sits next to the renderer because "the
extension is part of 'what this format is', so a new row brings its own, and
nothing outside this file has to learn a per-format special case."

`sourcing.for_mode` is the same shape for the three grid sources but stops one
step short: the CLI still mirrors `--mode`'s strings by hand, because the three
sourcing modes do not share a parameter list whereas all five renderers take the
same `(payload, path)`.

`for_format` raises a bare `ValueError` for an unregistered name, deliberately not
a `NonogramError`, for the same reason `sourcing.for_mode` does: argparse's
`choices` — *which come from this very table* — already refused an unknown format,
so one arriving here is a wiring bug.

## Where the readiness gate is not

Nothing in `export/` asks whether a puzzle may be exported. `export/__init__.py:25`
is headed "Where the readiness gate is *not*", and the reason is ADR-0007's
single-enforcement-point rule: INV-002 is applied once, by
`orchestrator.export_puzzle` (`:2517`, `puzzle.require_ready_for_export()`),
before an `ExportPayload` is even built, "so that all five renderers inherit one
gate instead of carrying five copies of it that can drift apart."

`ExportPayload` is the structural half of that. It is a flat record of boundary
values rather than the `Puzzle` aggregate, and `:124` names both reasons: a
capability module may not import the aggregate (ADR-0007), but "more usefully, a
payload with no `ready_for_export` on it cannot tempt a renderer into re-checking
the gate COMP-002 already applied."

Note the one asymmetry: `export_puzzle` returns early when no format was
requested, **and the gate is not consulted either** (`:2487`) — "a run that asked
for no export cannot be 'refused' one."

## What crosses the boundary

```python
@dataclass(frozen=True, slots=True)
class ExportPayload:                       # export/__init__.py:123
    grid: list[list[bool]]
    row_clues: tuple[tuple[int, ...], ...]
    column_clues: tuple[tuple[int, ...], ...]
    seed: int
    mode: str
    width / height / density: int | None = None
    name: str | None = None
    difficulty: str | None = None          # the DISPLAY spelling, "Medium"
    strategies: tuple[str, ...] = ()
    binarisation: str | None = None
```

ADR-0012 boundary types throughout — never the solver's per-line bitmask.
`export/__init__.py:35` makes EC-002's round-trip fidelity a consequence of that
choice: "what is written is already a plain, JSON-native structure, so decoding it
back cannot depend on bit order or mask width."

The extent fields record **what was asked for**, not what was produced (ADR-0015,
ADR-0023) — "a request that named one and left the other to the default records
exactly that … the grid's actual extent is derivable from `grid`, and always was."

`difficulty` is a plain string and not a `difficulty.Tier`, because COMP-007 may
not import COMP-006 (ADR-0007). The tier's display spelling is resolved once by
the orchestrator through `Tier.label` and carried across as a value
(`orchestrator.py:2546`). The same reasoning carries `strategies` and
`binarisation`.

## Filenames: one name, one exception, and a collision policy

`export.write` (`:293`) is the shared plumbing: resolve a non-colliding path,
`mkdir(parents=True, exist_ok=True)`, hand the renderer a path, report where the
file landed. "A renderer therefore only ever serializes — it does not decide where
its output goes, which is what keeps the four later format cards down to one
registry row each."

`--out` is a *directory* and not a file path because `--export` is repeatable: one
run can ask for JSON and PDF at once, and the two files have to differ by extension
in one place the user chose.

**One base stem per run: the puzzle's FR-015 name, sanitised.** `_filename_stem`
(`orchestrator.py:2589`) reads the name off the aggregate rather than computing a
second convention, so "the name a user reads and the file they get cannot drift
apart". The sanitiser is deliberately an **allow-list**
(`_UNSAFE_STEM_CHARACTERS = re.compile(r"[^\w.-]+")`, `:2586`): "a name is user
input, and `--name "../../secrets"` must become a file in `--out` and not a write
outside it." `\w` on a `str` pattern is Unicode-aware, so Cyrillic, accented Latin
and CJK survive intact while `/`, `\`, `:`, NUL and lookalike separators such as
U+202E, U+2044 and U+FF0F are all excluded — none of those is ever matched by `\w`.

The stem is also resolved **once and passed down** rather than recomputed per
format (`:2556`), because the unnamed-aggregate fallback reads the clock
(`export.default_stem`) "and a run that straddled a minute boundary would otherwise
write `...-1429.json` next to `...-1430.png`."

ADR-0016 carves out exactly one exception, and `_stem_for_format`
(`orchestrator.py:2640`) is it: the PDF writes as `<name>-<difficulty>.pdf`, the
tier joined in its own **lowercase** `Tier.value` spelling (`cat-hard.pdf`) rather
than its display `label` — "the two being one string apart precisely so a filename
and a header can each take the form they need without a lookup table between
them." An untiered puzzle keeps the bare name, because "half of the convention is
not a filename, and a `cat-.pdf` or `cat-None.pdf` would be worse than a `cat.pdf`
that merely omits what nobody measured."

Collisions are auto-suffixed `-1`, `-2`, … rather than overwritten (ADR-0017,
`_free_path`, `:342`), "because the export path is computed, never dictated, so two
runs of the same mode in the same minute would otherwise silently destroy the first
run's artifact." ADR-0018 adopted the same counter shape for auto-generated *names*
so the pipeline's two collision points "read as one idea applied twice rather than
two different ones" (`orchestrator.py:460`).

Repeated formats (`--export json --export json`) are collapsed to the first
occurrence via `dict.fromkeys` (`:2513`): "the user asked for JSON, not for two
copies of it."

## The shared geometry: one `compute_layout`, three drawings

`layout.py` exists because three renderers draw the same picture — the PNG raster,
the SVG vector and the PDF — and "'the same picture' has to mean the same
*numbers*, so the numbers live here, once, and the renderers only choose how to
stroke them" (`layout.py:1`).

`compute_layout` is a pure function of the clues and the sheet: plain ints, floats
and tuples, no Pillow type, no SVG string, no filesystem in its signature — which
is what lets a third renderer consume it without inheriting the second one's
library. **The grid's size is not a parameter**, because it is not separate
information: `len(row_clues)` is the number of rows and `len(column_clues)` the
number of columns, and INV-001 makes the clue sets the encoding of the grid, "so a
size argument could only ever agree with them or be a bug."

That has a consequence worth stating plainly: **the layout is never handed the
grid**, so the blank puzzle page has no filled-cell coordinate in scope to draw
even by mistake. `png.py:1` and `svg.py:1` both call that out — the solution's
absence from the printable page is structural rather than a rule each renderer
remembers.

Default geometry, all A4 portrait at 300 DPI:

| Constant | Value | Source |
|---|---|---|
| `DPI` | 300 | `layout.py:299` — "at 150 a thin rule and a small clue digit both start to alias, and at 600 the 30×30 page is four times the bytes for detail no home printer resolves" |
| `PAGE_WIDTH_MM` / `PAGE_HEIGHT_MM` | 210.0 / 297.0 | `:307` |
| `PAGE_MARGIN_MM` | 12.0 | `:312` |
| `HEADER_BAND_MM` / `HEADER_FONT_MM` | 12.0 / 5.0 | `:377` — 5 mm is roughly 14 pt, larger than any clue digit at any cell size |
| `MAJOR_RULE_EVERY` | 5 | `:369` — the standard nonogram counting aid |
| `_CLUE_FONT_RATIO` | 0.62 | `:383` — leaves a visible gap on both sides of a two-digit clue, the widest that can occur since the longest possible run is 30 |
| `_THIN_RULE_RATIO` | 1/30 of the cell | `:389` — pinned to the cell so the drawing keeps its proportions at every size |

**NFR-005's comfort curve** is `CELL_COMFORT_MM` (`:321`), five decided points read
as piecewise-linear by `comfort_cap_mm`:

```
(10, 9.0) (15, 8.0) (20, 7.5) (25, 7.0) (30, 6.5)
```

"The points were decided, the line between them is interpolation." The curve must
stay non-increasing in cells (EC-008) — "which is the whole content of 'a bigger
grid gets a smaller cell'". `MAX_CELL_MM` is `CELL_COMFORT_MM[-1][1]` = **6.5 mm**,
the comfort value for the largest supported grid, and `:329` is careful that this
is "no longer *the* cap … only the bottom end of its curve".

The band's claim on the sheet is shared by every format even though only the PDF
draws a header (`layout.py:8`): the cell is sized so that drawing **plus** band
fits the page, "because a cell chosen without the band is a cell the PDF cannot
print."

### `MIN_CELL_MM` is live code for a case the domain can no longer reach

`MIN_CELL_MM = 2.0` (`:359`) is the floor, and unlike the comfort cap it **wins
over page fit**. The comment is the model entry for this kind of honesty:

> Measured over all 441 extents CON-011 supports at four clue patterns, each on
> the sheet NFR-006 turns it to: the smallest cell any of them gets is 48 px /
> 4.06 mm — three checkerboards, 30×28, 30×29 and 30×30 … against this floor's
> 24 px. Page fit has to fall under 24 px for the floor to engage at all, which
> needs 92 cells across or 129 down on a portrait sheet, and 135 across or 86 down
> on a landscape one — nearly twice CON-011's widest grid plus its deepest gutter.

So the guarantee "the floor still beats page fit" is certified against a
**synthetic** 120×60 clue set rather than a constructible puzzle, "because the
domain can no longer construct one. That is recorded rather than hidden: the clamp
is live code for a case only a future widening of CON-011, or a future format with
a much deeper gutter, would reach — and a later reader tempted to delete it as dead
should reach that conclusion on purpose."

### `PageSpec`: ADR-0036 retired the "no second paper size" rule

`layout.py` used to carry guardrail G-1, "A4 is the only sheet it knows". ADR-0036
retired it. COMP-007 now knows more than one sheet, **only through an explicit
`PageSpec`, never by guessing** (`:34`): "Nothing here infers a sheet from the
puzzle, the payload or the caller."

A caller that passes no spec — the CLI, the web UI, every existing export — gets
`DEFAULT_PAGE_SPEC` (`:649`), which is "today's A4 byte for byte (ADR-0036/R1,
CON-019, pinned by `tests/test_export_a4_golden.py`)". **The registry never passes
one**, so no CLI or web export can take the book path at all. The book (COMP-009)
is the only caller that builds a spec.

A spec lays a puzzle out one of two ways, decided by its `parity`:

- **no parity → a drawing-sized image.** The drawing plus one uniform margin on
  all four sides, the sheet may turn (NFR-006), and the cell is a whole number of
  device pixels. **This is the only path the default spec takes**, and every
  measurement quoted above describes the default spec only.
- **a parity (`ODD`/`EVEN`) → a placed page.** The image is the whole trim; the
  usable area is trim minus margins with the gutter margin on the binding side.
  Since CARD-224 **parity no longer moves the drawing sideways at all**: it moves
  the usable area, and the drawing is centred in whatever that is.

The two policy enums are narrow by design:

```python
class OrientationPolicy(StrEnum):   # layout.py:410
    LARGER_CELL_WINS = "larger_cell_wins"   # NFR-006, the default spec's
    PORTRAIT_ONLY    = "portrait_only"      # FR-032: a book puzzle prints upright

class CellCapPolicy(StrEnum):       # layout.py:421
    COMFORT_CURVE = "comfort_curve"         # NFR-005's comfort_cap_mm
```

`CellCapPolicy` has exactly one member, and its docstring says why: "The one named
cell cap. The other kind of cap is a flat number of mm" — a `PageSpec`'s `cell_cap`
is either `COMFORT_CURVE` or a finite positive float. NFR-008's 7.5 mm standard
cell for a book is the latter (`admin/book_page_spec.py:256`, `cell_cap_mm=7.5`).

`_exact_mm` (`layout.py:455`) is a small detail with a real consequence: a
measurement is converted with `Fraction(repr(value))`, not `Fraction(value)`,
because "9.525 mm is 0.375 in exactly, and the binary float nearest to it is not."
The placed path keeps the spec's numbers exact so its fit and parity arithmetic are
exact too.

`TWO_UP_MIN_CELL_MM = 7.0` (`:3130`) and `PairLayout` (`:3133`) serve FR-040's
two-up book page — a value object "valid by construction: `__post_init__` refuses
any pair that is not a two-up page, so a caller holding one never re-checks it."
Both are re-exported from `export/__init__.py` for the admin panel. See
[07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md).

## The five renderers

### PNG, and why `render_image` is the real entry point

`png.render_image` returns the Pillow `Image`; `write_png` saves one; `render` is
the `Renderer` the registry calls. `png.py:11` says that order is the point.
CON-006 settles FR-016's PDF as **a second sink on this raster path** — Pillow
saves a multi-page PDF from images already in memory — "so ADR-0006's dependency
baseline is not reopened for a PDF library." A module that only exposed "write a
PNG to this path" would have forced CARD-014 either to write a throwaway PNG and
read it back, or to re-implement the drawing against a second geometry that could
drift. "Handing back the `Image` costs nothing here and is the whole reason PDF is
one card instead of a dependency decision."

`write_png` stamps the DPI into the file's `pHYs` chunk, "so a print dialog
reproduces the intended physical size instead of assuming 72 DPI and scaling the
page to four times its size."

### SVG, assembled as text

`svg.py:9` argues the no-dependency case concretely: SVG is XML, and this document
is a few hundred elements of it with no namespacing beyond the root, no entities
and no user-supplied strings — "every value written below is an integer this
package computed. `svgwrite` or `cairosvg` would buy nothing here and would reopen
a dependency baseline ADR-0006 closed." `xml.sax.saxutils.escape` is nevertheless
applied to the one nominally-string field (the clue digits) "so that the 'these are
only ever integers' assumption is enforced by the code rather than trusted."

The root declares `width`/`height` in **inches** over a `viewBox` in the layout's
pixels. `svg.py:28` gives the failure that avoids: an SVG with a pixel `width` is
re-interpreted by every consumer at its own idea of a pixel (96/inch, usually) and
prints at a third of the intended size.

### PDF: two pages, no PDF library

One file, two pages (`pdf.py:1`). Page 1 is CARD-012's PNG raster **verbatim**, so
"the PDF and the PNG of one puzzle cannot drift apart: they are the same pixels."
Page 2 is that image *copied* and then filled with the solution. Both carry the
same `"<name> — <tier>"` header. This module therefore adds exactly the two things
a blank raster cannot do — reveal the solution and title the page — and re-derives
none of the geometry.

A consequence the file points out: a book page's `PuzzleFrame` appears on both
pages "without a line of code here", because the frame is stroked into the raster
by `png.render_image` and both pages *are* that raster. `_reveal` fills cells
inside the grid in the same pure black, so it cannot disturb the frame's rules.

**A font ships as package data.** `FONT_RESOURCE = "fonts/DejaVuSans.ttf"`
(`pdf.py:139`), with `fonts/LICENSE` beside it. ADR-0006's revision of 2026-09-01
(ADR-0006/R1) allows it precisely *because* it is data rather than a dependency —
and `pyproject.toml:79` is what makes that true:

```toml
[tool.setuptools.package-data]
"nonogram.export" = ["fonts/*.ttf", "fonts/LICENSE"]
```

That block carries its own measurement: without it the font is present in a source
checkout (where pytest's `pythonpath = ["src"]` reads it off disk) and **absent
from every built wheel** — "a wheel built from this tree carried 60 entries and
none of them a font, so `pdf._font_bytes()` raised on any real install while the
whole suite stayed green." The LICENSE is listed explicitly rather than left to a
glob "as an obligation of the DejaVu licence, not as a nicety".

DejaVu Sans covers Latin, Cyrillic and Greek — and the file is honest about what it
does not reach (`pdf.py:62`-`70`). That bound is what `errors.UnletterableTitle`
exists for on the book-cover path: a title the shipped face cannot letter is
refused by name rather than printed as a row of `.notdef` boxes
(`errors.py:178`). The header sets the title in DejaVu and the clue numbers in
Pillow's embedded default — two faces on one page, by necessity.

### JSON and CSV: FR-012, and the one asymmetric decision

JSON document shape, version 2 (`json_export.py:17`, `SCHEMA_VERSION = 2`):

```json
{"version": 2, "seed": 42,
 "request": {"mode": "random", "width": 4, "height": 4, "density": 50},
 "grid": [[true, true, false, false], ...],
 "clues": {"rows": [[2], [0], [4], [2]], "columns": [[1, 1], ...]}}
```

`request` is the provenance block: what was *asked for* (ADR-0015), not what was
produced, and each of `width`/`height`/`density` may be `null` — "'not asked' is a
real answer, distinct from zero." ADR-0023 replaced version 1's scalar `"size"`
with the pair, "because a single edge length cannot describe a rectangle."

CSV is four marker-delimited sections in fixed order — `#meta`, `#grid`,
`#row-clues`, `#column-clues` — because "a CSV file is an undifferentiated sequence
of rows, and this export has to hold four things of three different shapes: scalar
metadata, a rectangular 0/1 matrix, and two *ragged* lists of integer tuples"
(`csv_export.py:8`).

The asymmetry between them is a recorded owner decision, not an oversight.
`strategies` (FR-029) and `binarisation` (FR-027) were added at the **existing**
schema version, which ADR-0023's rule permits because no existing reader breaks on
them: JSON's decoder reads the fields it names and ignores the rest. **CSV could
not take them on those terms** — its `#meta` block has a closed key set and its
decoder refuses any version but its own — "so CSV carries neither, by decision
rather than by oversight (CARD-072, the owner's call: keep every file already
exported readable)" (`export/__init__.py:163`).

EC-002's round-trip property rests on the boundary types: "`json.loads` on this
document hands back the same nested lists of the same Python scalars, with no bit
order, mask width or sign convention to get wrong at the seam"
(`json_export.py:52`). Each renderer separates `document()`/`render()` so the
serialised shape can be asserted without touching a filesystem.

## Bounds and honest gaps

- `export.write` raises the stdlib's own `OSError`, **not** a `NonogramError`, when
  `--out` points at something unusable. `cli._run_generate` catches it around that
  one call and reports `ExitCode.EXPORT_REJECTED`, and `cli.py:428` records why the
  clause is narrow: it used to wrap the whole handler, which was safe only by
  accident of scope, and `--mode image` reading a user file would have made "a
  missing picture" report as "export rejected".
- `export.default_stem`'s docstring still describes FR-015 naming as unlanded —
  "That card has not landed" (`export/__init__.py:277`). It has;
  `orchestrator._filename_stem` is the caller that docstring anticipates, and says
  so at `orchestrator.py:2594`.
- `ExportPayload.difficulty`'s docstring (`export/__init__.py:187`) still describes
  a four-member value set including `"Guess"` and a `cat-guess.pdf` filename.
  ADR-0031 retired that tier; `difficulty.Tier` has three members. The code is
  correct, the prose is not.
- The default spec's measurements (the 441-extent sweeps, the orientation counts,
  the band's cost) **describe the default spec only** (`layout.py:49`). Nothing in
  this file's figures transfers to a book page.

## Related

- [01-the-layered-pipeline.md](01-the-layered-pipeline.md) — INV-002's gate · [05-difficulty-calibration.md](05-difficulty-calibration.md) — where the tier in the filename comes from
- [07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md) — the only caller that passes a `PageSpec`
- ADRs: [ADR-0006](../../../../meta/architecture/decisions/adr/0006-dependency-baseline.md) · [ADR-0016](../../../../meta/architecture/decisions/adr/0016-pdf-filename-convention.md) · [ADR-0017](../../../../meta/architecture/decisions/adr/0017-export-filename-collision-policy.md) · [ADR-0023](../../../../meta/architecture/decisions/adr/0023-export-metadata-grid-extent.md) · [ADR-0036](../../../../meta/architecture/decisions/adr/0036-book-page-geometry-via-page-spec.md) · [ADR-0037](../../../../meta/architecture/decisions/adr/0037-book-puzzle-page-band-and-strokes.md)
