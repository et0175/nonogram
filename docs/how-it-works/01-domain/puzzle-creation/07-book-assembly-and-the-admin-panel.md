# 07 — Book assembly (CAP-006 / COMP-009, AGG-002)

> Scope: `src/nonogram/admin/` — about 35,300 lines, 62% of the package
> (re-counted 2026-11-10). The storage
> guard, the Book aggregate and its lifecycle, the distribution plan, and the
> page-at-a-time PDF export.
>
> The admin panel's **door** (binding, credential, cross-site refusal) is in
> [09-the-three-inbound-adapters.md](09-the-three-inbound-adapters.md); its
> **database** is in
> [10-persistence-and-the-unmodelled-edges.md](10-persistence-and-the-unmodelled-edges.md).

## Why this is an adapter and not a capability

ADR-0033 kept Book in CTX-001 as its second aggregate rather than splitting out a
CTX-002. `contexts.yml` lists four signals *for* a split — Book has its own
lifecycle and its own invariants, TERM-018..TERM-029 are a print-production
vocabulary absent from the pipeline, CAP-006 lives only in a separately deployed
container, and CON-019 already imposes a one-way rule — and two against: one
owner, and the code already treating `admin/` as a **rank-0 inbound adapter** of
CTX-001.

That rank is what makes the panel's most important property legal. `admin/`
imports `clues`, `solver`, `difficulty`, `export` and `orchestrator` **directly**,
not through COMP-002, and the component diagram says this is drawn on purpose:
those arrows are ADR-0032/R1's storage guard, "which re-derives a puzzle's clues
and asks the solver for a verdict at the storage boundary itself rather than
trusting whoever called it. Routing them 'through the orchestrator' would erase
that guarantee."

All of its `nonogram.db` imports are **function-local**, deliberately
(`app.py:6230`): "importing it up top would make SQLAlchemy a hard requirement of
the admin panel — it is the optional `db` extra."

## The storage guard: what it cost to not have one

Three functions in `admin/puzzle_review.py`, in order.

**1. Shape.** `_refuse_unless_shaped_like_a_grid` (`:454`) refuses anything that is
not a non-empty rectangle **of booleans**. Its docstring carries the measurement
that makes a shape check necessary rather than paranoid:

> `[]` encodes to two empty clue sets, `[[]]` to `((0,),)`, and the string
> `"not a grid"` to ten rows of one filled cell — a 10×1 grid that is uniquely
> solvable, **so a guard that only asked the solver would have stored the string.**

**2. The question, asked in one place.** `_why_this_is_not_a_puzzle` (`:540`) is
the single place both the write path and the audit ask it, "so the write boundary
and the audit cannot drift into disagreeing about what 'a puzzle' means." It
`compute_clues(grid)` — **re-derived from the grid, never taken from the caller's
`clues_rows`/`clues_cols`** (`:567`):

> Those are the caller's claim about the grid, and a guard that trusts the
> caller's claim is not a guard.

Then `solve(..., deadline=time.monotonic() + deadline_seconds)`. A `SolverTimeout`
is an **objection, not a pass**: `"uniqueness could not be proven within {n}s —
unproven is not proven"` (`:588`). `errors.NotUniquelySolvable`'s own docstring
makes that collapse explicit (`errors.py:136`): "either because there are 0 or
>= 2, or because the solve passed its deadline without concluding. Both are the
same answer to the only question storage asks: *has this been proven to be a
puzzle?*"

The `solution_count == 0` arm carries its own honesty note: unreachable while the
clues are derived from the grid, "measured over 120 random derived clue sets: 97
unique, 23 ambiguous, none unsolvable. Kept because the solver's contract allows
the value, not because a caller can produce it."

**3. The write boundary.** `_refuse_unless_uniquely_solvable` (`:607`) runs the
shape check, looks up a SHA-256 `_grid_fingerprint` against a bounded proof cache,
then asks the question with `deadline_seconds=GENERATION_BUDGET_SECONDS` — 30.0 s
from `orchestrator.py:341`, **not** a caller's choice, "which is why this takes no
budget argument." Only **proofs** are cached, never timeouts (`:641`): "a timeout
is a fact about one run's clock", while a proof is sound to cache because the
verdict "is a function of the grid's cells alone".

### Why the guard exists

`puzzle_review.py:607` states it as a class-of-bug argument, with the price
attached:

> a store that accepts whatever its callers hand it has the property only as long
> as every caller does, and **the twenty rows deleted on 2026-09-14** are what
> that argument costs when it stops holding. They came from a third caller that
> derived a tier from the grid's *size* and never solved anything. Deleting that
> function closed the instance; this closes the class.

`meta/kanban/cards/CARD-080.md` records the deletion: 36 rows → 16; all 20 deleted
rows were **re-verified against the real solver at the moment of deletion** rather
than trusted from the earlier report, all 20 reporting `solution_count = 2`, and a
row that could not be proven either way would have been kept (none occurred).

### The read path is deliberately looser, and the asymmetry fixed a bug

`_as_readable_grid` (`:503`) checks shape as strictly but **coerces** cell type
(`bool(cell)`) where the write path refuses it, because "a row whose cells
round-tripped as `0`/`1` through some earlier writer is still a perfectly good
puzzle. Refusing it on the read path would be an audit lying about the data it
exists to describe: measured, `[[1, 1], [0, 1]]` is a uniquely solvable Easy puzzle
that the write-path check calls malformed."

The bug it closed is named: "The audit used to come through here too, which made
it report uniquely-solvable legacy rows as failures — the write path's strictness
applied to the read path's question (CARD-080 review cycle 1, F-001)."

It is a native reimplementation of `regrade._as_grid`, cross-checked from the test
tree by `tests/test_admin_uniqueness_boundary.py::TestTheTwoGridReaders_AgreeWithEachOther`
— **a third instance of the reimplement-and-cross-check pattern**, alongside
`solver.mask_runs` and `web/submission._EXTENT_SEPARATOR`.

### ADR-0032/R2: an unmeasured quality score is NULL, never 0

`db/models.py:70` — `quality_score = Column(Integer, nullable=True)  # 1-100`. The
scale starts at **1**, so 0 is not a legal measured value and NULL is the only
"unknown". The filter honours that: `puzzle_review.filter_puzzles` **excludes** a
NULL row from any `quality_min` filter "because SQL's `NULL >= n` is false"
(`models.py:99`), and `puzzle_review.py:1552` cites ADR-0032/R2 for not taking
`quality_min` straight off the query string. Random mode has stored NULL here since
CARD-050.

The score itself comes from `nonogram.analysis.quality_metric.measure_quality`
(`admin/app.py:138`, called at `:1942`) — a module **no component in the model
names**. See [10](10-persistence-and-the-unmodelled-edges.md).

A related decision worth keeping: **a hand edit deliberately leaves
`quality_score` alone** and records `manually_edited_at` instead (`models.py:90`,
CARD-245 / migration 016). Nulling it was the tempting alternative and would have
made a hand-improved puzzle *disappear* from the quality-filtered list the owner
picks book puzzles from.

## AGG-002 Book: five states, one transition method

```python
class BookStatus(Enum):          # admin/book_manager.py:50
    DRAFT = "draft"; READY_FOR_PDF = "ready_for_pdf"
    PDF_GENERATED = "pdf_generated"; READY_FOR_KDP = "ready_for_kdp"
    PUBLISHED = "published"
```

All five are real and stored in `books.status` (`db/models.py:142`,
`default='draft'`). Transitions are enforced in **one** method,
`BookManager.set_book_status` (`book_manager.py:2223`), identically in both
persistence modes:

- unknown status → `ValueError(f"Invalid status: {status}")`
- current status `published` → `ValueError("Cannot change status of published book")`
- empty selection and target ≠ draft → `ValueError("Must have puzzles before advancing status")`
- then `_refuse_unless_the_planned_book(...)` — **the readiness gate** (FR-037,
  ADR-0035)

See [diagrams/07-book-lifecycle.puml](diagrams/07-book-lifecycle.puml).

The gate runs **at the exit from draft, not continuously** (`:2237`). It is paid
for again by `_draft_after_membership_change` (`:488`), which returns a book to
draft when its membership changes after draft — INV-012 — "so it passes this gate
again before it can leave: a KDP upload is never built from a book that no longer
matches its plan." Editing the plan does the same via `save_plan` (`:773`).

### The readiness tolerance

`READY_TOLERANCE_POINTS = 3` (`book_manager.py:142`), **inclusive**: a cell exactly
3 points out passes (AC-219), one 4 points out does not (AC-220). The comparison is
integer-only to avoid float drift (`:229`):

```python
abs(actual[cell] - planned[cell]) * 100 > READY_TOLERANCE_POINTS * plan.count
```

`ready_refusal` (`:239`) names **every** offending cell at once (AC-221), and
`NO_PLAN_REFUSAL` (`:149`) is what a plan-less or undecodable-plan book is told.

### Invariant enforcement, located

| Invariant | Where it is enforced |
|---|---|
| INV-005 plan well-formed, never zero | `book_plan.InvalidPlan` (`book_plan.py:85`), cited at `book_manager.py:215, 755, 780` |
| INV-006 below-floor needs a stored override | `floor_overrides` (`:988`), `below_floor` (`:1000`), `_below_floor_for` (`:1087`), `floor_refusals` (`:1286`), `FloorRefusal` (`:289`) |
| INV-007 per-cell plan match at exit from draft | `book_manager.py:130`, `:2228`, `ready_refusal` (`:239`) |
| INV-008 published book's membership change needs confirmation | `AddOutcome` (`:349`) / `RemoveOutcome` (`:377`) `confirmed` flags; route → **409** (`app.py:2875`) |
| INV-009 a booked puzzle may not be re-graded into another tier | `RegradeInsideABook` (`puzzle_review.py:105`); route → 409 `regrade_in_a_book` (`app.py:2843`) |
| INV-010 two-up pairs equal tiers only | `book_pdf_generator.py`'s `_pairable_tier` (`:3583`) and `_level_runs` (`:3600`); deliberately **not** reimplemented in the routes |
| INV-011 answer-page capacity and order | `book_answer_key.py:24, 94, 173, 253, 299` |
| INV-012 membership change after draft returns to draft | `_draft_after_membership_change` (`book_manager.py:472`) |
| INV-013 the interior PDF carries no cover page | `book_pdf_generator.py:3`, `Interior.pages` (`:2555`), `export_book` (`:4672`) |

### A concurrency bound the code states about itself

`book_manager.py:2247` is worth quoting in full rather than paraphrasing, because
it is the honest version of a race:

> in DB mode the check and the write are **not atomic** … The single-session shape
> this replaced was no better — SQLAlchemy's pysqlite dialect runs the SELECT
> outside any transaction and only opens one at the first write, and a Postgres
> READ COMMITTED session behaves the same way — so the exposure is the whole DB
> layer's, not this method's. It is accepted here because the panel is a
> single-user loopback tool (CON-015): one owner, one browser, no concurrent
> writers.

## The distribution plan: 150 at 40/40/20, re-derived

```python
DEFAULT_PLAN: DistributionPlan = prefill(150, Split(40, 40, 20))   # book_plan.py:345
```

ADR-0034. Running that constant's own functions on this checkout's interpreter
(`book_plan` is pure — no DB, no I/O) yields the matrix it actually contains:

| Longest-side bucket | easy | medium | hard | row total |
|---|---|---|---|---|
| `<=15` | 20 | 7 | 0 | 27 |
| `16-20` | 30 | 27 | 6 | 63 |
| `21-25` | 10 | 20 | 12 | 42 |
| `26-30` | 0 | 6 | 12 | 18 |
| **column total** | **60** | **60** | **30** | **150** |

So 40/40/20 of 150 is `(60, 60, 30)` and the four buckets carry it as above.
The derivation, so the figures are citable with the function that produced them:

- `tier_counts` (`book_plan.py:278`) apportions the total over the split by
  **largest remainder with ties to the harder tier** —
  `_largest_remainder(..., ties_to_later=True)` (`:259`), EC-023, recorded as the
  owner's choice of 2026-09-22.
- `prefill` (`:291`) apportions each tier's count over the four buckets in
  proportion to that tier's **column** of `BOOK1_MATRIX` (`:195`, from
  `docs/research/book-format-research.md §8`, percent of book, `"–"` read as 0):
  `(10,5,0) (15,20,5) (5,15,10) (0,5,10)`.
- **Every column total equals its tier count exactly and the matrix sums to
  `count`. Row totals are not preserved** (FR-034's own note).

`LongestSideBucket` (`:89`) is `<=15`, `16-20`, `21-25`, `26-30`, and `_BOUNDS`
(`:118`) ties the outer ends to `nonogram.limits`, so **the four buckets partition
the supported size range exactly**. That is independent corroboration that the
range is 10..30 and not the 10×10..50×50 the component diagram claims: a 50-cell
side would have no bucket at all.

POL-007 re-derives an un-hand-edited bucket plan automatically when the split
changes (CMD-020 → EVT-021).

## The three millimetre constants

| Figure | Constant | Location |
|---|---|---|
| 4.75 mm book-cell **floor** (NFR-008, TERM-024) | `FLOOR_MM = 4.75` | `admin/book_page_spec.py:168` |
| 7.5 mm **standard cell**, the flat cap | `cell_cap_mm=7.5` on `BOOK1_PROFILE` | `admin/book_page_spec.py:320` |
| 7.0 mm two-up **shared cell** minimum | `TWO_UP_MIN_CELL_MM = 7.0` | **`export/layout.py:3554`** — not in `admin/` |

The floor's *placement* is itself an architectural statement
(`book_page_spec.py:139`): it is a module constant beside `BOOK1_PROFILE` rather
than a field on `PrintProfile`, because the floor and the cap "are the two ends of
NFR-008's band but are **not** the same kind of number. `PrintProfile.cell_cap_mm`
is an **input** to the sheet … The floor is a **verdict** the book store then makes
about the cell that came back, it is the same 4.75 mm for every trim, every margin
and every profile."

The 4.8 → 4.75 amendment (NFR-008 as amended 2026-10-17, CARD-222) carries its
measurement: "a 30-wide grid at clue depth 10 lands at 4.7625 mm, 0.012 mm
**above** this floor, where the retired 4.8 mm would have refused it (AC-370); a
30-wide grid first falls under this floor at clue depth 11 (4.6463 mm)."

`TWO_UP_MIN_CELL_MM` sits inside the band (`layout.py:3124`), "so a two-up page
never uses the 4.75 mm floor or its override; the spec's flat cap (the 7.5 mm
standard cell) still caps the shared cell. A named constant rather than a
`PageSpec` field: it is the owner's rule for every book, not a property of a trim."

**The footer band (FR-032, FR-040; CARD-392).** A puzzle page's footer is a
hairline and **one line** under it: the solution pointer ("Solution on p. N") on
the inner side, the folio at the centre, the pointer to the Play online page on the
outer side. The grid size moved out of the footer into the white corner between
the clues on 2026-11-10 (Anna's layout); see the puzzle page below. The band the
hairline opens is `INTERIOR_FOOTER_MM` in `export/layout.py`, "the footer line
plus its two gaps" -- a 10 pt line and 9 pt of white above and below it, 9.878 mm
(117 px at 300 DPI) -- where it was 29.878 mm while a 2 cm row at its foot was
held for the per-puzzle QR icon. The band is the unit the puzzle area is measured
against, so the 20 mm it gave back is the area's: on Book 1 the area between the
header rule and the footer rule is 233.1 mm (2753 px) deep, not 213.1 mm (2517),
and on the shortest trim `book_page_spec` admits (10.00 cm) 53.7 mm, not 33.7.
What it changes and what it does not: a single page's cell is fitted against the
usable height less the title band, never against the footer band, so the
one-cell-per-grid-size table does not move; where a drawing floats does (42% of a
larger spare), and so do FR-040's pair boundaries, because a pair's height is
fitted against what is left after two bands and the strip -- 31 cells of combined
drawing height on Book 1 (219.586 mm over 7.0 mm), 24 on 6 x 9 in, 20 on 5 x 8 in
(where no two puzzles pair at all). On a book of 120 easy 10 x 10 puzzles with
5-deep gutters that is 156 interior pages becoming 96, which crosses KDP's
150-page gutter band (0.5 in minimum to 0.375 in).

`BOOK1_PROFILE` in full (`book_page_spec.py:312`, CON-018): trim 8.5 × 11 in,
gutter 0.5 in, outside 0.5 in, top 0.55 in, bottom 0.47 in, `band_mm=12.0`,
`cell_cap_mm=7.5`, `min_thin_rule_mm=0.25` (ADR-0037/R2). Inches are `Decimal`
against `_MM_PER_INCH = Decimal("25.4")` (`:130`) — **not float**. Alongside it,
`MIN_SIDE_MARGIN_MM = 6.35` (`:175`) is KDP's 0.25 in minimum applied to both side
margins.

`book_page_spec.book_page_spec(book, page_number)` (`:578`) is "the one door onto
the book's sheet (CARD-115)", taking the page's **1-based position in the
interior** so parity follows FR-043: interior page 1 is the title and copyright
page and is right-hand/odd; the "How to Solve" guide is the facing spread on
pages 2 (a verso) and 3 (a recto), set in the puzzle pages' own frame (CARD-229).

### Ink mode — in the code, absent from the model

`InkMode` (`book_page_spec.py:266`) is `BLACK_AND_WHITE="bw"` / `COLOUR="colour"`,
default `BLACK_AND_WHITE` (`:308`), stored in `books.interior_ink_mode`
(`db/models.py:200`, nullable, `server_default='bw'`). It decides **exactly one
thing** — the Pillow bitmap mode, `"L"` or `"RGB"` — and the docstring argues it is
not geometry: "no page size, margin, cell, rule or count depends on it, and
ADR-0036/R1 is untouched."

The ADR-0037/R2 preservation argument is measured rather than assumed:
`Image.convert("L")`'s ITU-R 601-2 luma maps grey `(v,v,v)` to exactly `v` because
its three integer coefficients sum to 65536, "so 0 stays 0, 255 stays 255 and no
value between them is invented." No ADR or component description mentions ink mode
at all (CARD-147 / migration 013).

## The book PDF: what is on each page, and how it is written

`book_pdf_generator.py` (6,602 lines) builds the interior; `export_book` is the one
entry point every export route goes through and returns two files, the interior
PDF and the cover file (FR-043, INV-013). Its central claim (ADR-0036/R2) is still
a *negative* one: **this module fits no cell and places no grid line.** Every
number it uses is read off `nonogram.export.layout.compute_layout` called with the
book's own spec; it places only text the layout knows nothing about.

Every page is the book's own trim (2550 × 3300 px at 300 DPI on Book 1, i.e.
8.5 × 11 in; 1800 × 2700 px on a 6 × 9 in book), taken through
`book_page_spec(book, page_number)` so a page's parity, and therefore which side
its gutter is on, follows its position in the interior.

### Vector pages, two raster kinds

Since CARD-322 (2026-11-07) an interior page is **PDF operators, not a bitmap**
(ADR-0042/R1). `page_medium(kind)` is the one place the medium is decided: every
`PageKind` is vector unless `_RASTER_DECLARATIONS` names it, and it names exactly
two, each with its reason:

- `COVER` — a photograph the owner uploaded (ADR-0042/R2);
- `DIVIDER` — a picture the owner uploaded (owner decision 2026-11-06, CARD-311).

The vector writers live in their own modules (`book_puzzle_vector`,
`book_guide_vector`, `book_toc_vector`, `book_answer_vector`, `book_play_vector`,
with `book_sheet_vector` and `book_vector_draw` for the shared furniture and
strokes). Three of them import the generator, so the generator cannot import them
back; `book_interior_vector.interior_generator` is the one place that assembles a
generator with every writer, and `admin/app.py` is the only module that imports it.
`BookPDFGenerator(book)` on its own has no downstream writers and **refuses**,
rather than rasterises, a vector page it cannot draw.

### The page order

Measured on a rendered four-puzzle book (one easy pair, one medium, one hard),
the interior reads:

| Page | Kind | What is on it |
|---|---|---|
| 1 | `TITLE` | series name (if any), title, subtitle or "N picture puzzles", "by {authors}", and at the foot the copyright and reproduction lines; no folio (`vector_title_contents`, owner 2026-11-09 — it replaced the blank reserved page so KDP's "Look Inside" does not open on an empty page) |
| 2–3 | `GUIDE` | "How to Solve", a facing spread. Page 2 opens with a grey box holding the book's promise ("Each puzzle hides a picture and has just one solution, checked by computer…") and the sentence pointing at the Play online page by its real page number (`book_guide_spread._page_two`) |
| 4… | `TOC` | Table of Contents, see below; one page on Book 1, two on the smallest trim |
| | `DIVIDER` | one per non-empty level (Easy, Medium, Hard), when the book's divider pages option is on: the owner's uploaded picture, or the drawn one-word page for a slot with none |
| | `PUZZLE` | the puzzles in print order, easy then medium then hard; two equal-tier puzzles share a page when they fit (FR-040, INV-010) |
| | `BLANK` | only when needed to put the next page on a right-hand page |
| | `PLAY` | "Play Every Puzzle Online", the book's one QR code (CARD-390) |
| | `DIVIDER` | SOLUTIONS, when dividers are on |
| | `ANSWER` | the answer key, see below |

`interior_stream` decides every position before it draws a page: it runs the
section walk first, because how many pages the puzzles take is what puts each
divider, the Play page and every answer page where it goes.

### The puzzle page

- **Band** (ADR-0037/R1, FR-033): `"Puzzle N"` and the tier (`band_identity`),
  nothing else. The title is deliberately absent — "a titled puzzle page gives the
  picture away before the solver has drawn it" — and `_puzzle_payload` clears the
  picture's name so there is no title for the page to leave off.
- **Size** (`draw_corner_size_label`): the grid size ("15 x 15") is centred in the
  white corner where the column clues and the row clues meet, in grey
  (`CORNER_LABEL_GREY = 0.37`). When the corner is too small to hold it, the size
  goes back into the footer instead, before the pointer.
- **Footer**: a hairline and one line under it: the Play online pointer on the
  outer side ("Play puzzle 3 online · p. 11", or "Play 1 and 2 online · p. 11" on a
  shared page), the folio at the centre, and on the inner side the solution
  pointer (`footer_solution_text`): "Solution on p. 14", or "Solutions on p. 13"
  / "Solutions on p. A and B" for a shared page whose answers land on one or two
  pages. Every page number is the real one, read off the same plan that places
  the answer pages (`_answer_page_of_each_puzzle`).

### The table of contents

`structural_toc_entries` builds the rows: How to Solve Nonograms; each level's
heading with its puzzle range ("Puzzles 1–2") and first page; Play online; then
**Solutions** with one indented row per level (Easy, Medium, Hard) at the first
answer page of that level (`TocEntry.secondary`). Every number is the page it
points at in this same interior; the rows and the pages come out of one
`interior_stream` call (`InteriorStream.toc_entries`), so they cannot disagree.

### The Play online page

`book_play_vector._mockup_play_page` (Anna's design, 2026-11-10): a "BONUS" eyebrow
and a "FREE ONLINE ACCESS INCLUDED" badge, the title "Play Every Puzzle Online"
and an intro line, then a framed card with the QR code (32 mm, in a white box),
"Online Access to All N Puzzles", and the typed address under "OR TYPE THE
ADDRESS:". Below it three steps (Scan, Select, Solve) and a callout pointing at
the first solutions page. All type is 10 pt or larger (CON-020). The address is
made by `player_bundle` from the book's stored player domain and its puzzles, and
encoded by `book_qr` (the vendored encoder, error correction level Q); the tests
decode the printed code back to the address.

### The answer key

Packed by `book_answer_key` (FR-042, INV-011): up to four answers to a page in a
2 × 2 grid, for every grid up to 30 × 30; every level starts a new page, and the
first page of a level carries its heading ("SOLUTIONS · EASY"). Each answer is the
solved picture with its clues, under "Puzzle N" and captioned with the number and
the picture's title. **The answer key is the only place the book prints a
picture's title** (ADR-0037/R1, FR-033).

### Memory: one page at a time

The bound comes from CARD-145. The owner reported "render crashes when I try to
generate pdf" with **no traceback in the logs — "the signature of an OOM kill
rather than an exception"** — diagnosed by arithmetic: 2550 × 3300 × 3 bytes
(25.2 MB) per bitmap page times the page count, against a 512 MB instance.

`interior_stream` returns an `InteriorStream` whose `pages` is a **generator**,
single-use, drawn one page at a time, and whose counts come from the page plan's
own arithmetic, so an export can report what it is about to write without drawing
anything to count it. `export_book`:

```python
stream = self.interior_stream(puzzles)
interior = self._write_pdf(stream.pages, stream.page_count, mode=self.interior_bitmap_mode)
cover = self.export_cover(book_title, cover_image)
return BookExport(interior=..., cover=..., interior_page_count=stream.page_count, ...)
```

With the interior in operators, a typical page is now a few kilobytes; the 25.2 MB
figure applies only to the raster pages (dividers and the cover). What keeps the
cover page from being alive beside an interior page is not the order of the two
statements: `_write_pdf` keeps no page after writing it and returns a `BytesIO`.

**Nothing is written to disk.** The export route returns the two `BytesIO`s as
attachments named `book_{utcnow:%Y%m%dT%H%M%S}_{part}.pdf`. Uploaded **covers**,
**divider pictures** and source **pictures** *are* stored, which is what the
component diagram's `admin -> filesystem` arrow is. On export, any exception is
logged with its stack **before** it is flashed and redirected (CARD-171).

### How to see a change

`tests/test_book_vector_goldens.py` holds the operators of every page kind against
recorded goldens; after an intended layout change they are re-recorded with
`NONOGRAM_RECORD_VECTOR_GOLDENS=1 PYTHONPATH=src python -m tests.test_book_vector_goldens`.
To look at a whole book, download the interior from the book's page in the admin
panel.

### The three sibling modules

- **`book_answer_key.py`** (541 lines) — which answers share a page and what each
  says. Owns INV-011's capacity rule as "this module's, not the layout's".
  `plan_small_answer_pages` is the pure, sheet-free planner the book uses: two or
  four answers to a page, every grid up to 30 × 30, and no page holds two levels.
  The older six-up walk (`pack_answer_pages`, threshold `SIX_UP_LONGEST_SIDE = 20`)
  is still in the module.
- **`book_proof.py`** (784 lines) — "ADR-0037's proof pages: the book's own
  geometry, printed to be measured." A 30×30 at the smallest cell the book prints
  and a 15×15 at NFR-008's cap, "for the owner to print at 100% and measure with a
  ruler. The strokes ADR-0037 fixes are final only once that has happened"
  (`app.py:5535`). A GET that reads no membership, so a draft book downloads the
  same two pages a finished one does.
- **`book_kdp.py`** (662 lines) — Amazon KDP's gutter-margin table and the finalise
  check against it. `gutter_refusal(page_count, stored_cm)` refuses when the page
  count needs a larger gutter than the one stored. An inexact page count is worded
  "about N" to match the screen (CARD-153 AC-4), and a count above KDP's table
  raises `KdpPageCountNotModelled` rather than stating a sheet-free upper bound as
  a fact — "'runs to 350' would state a guess as a fact (review F-001)."

KDP is a **print specification the book PDF meets** (CON-018), not an integration.
`external_systems.yml` is `[]` and `c4/context.puml` says so explicitly.

## Batch generation, and the bounds the HTTP request imposed

`generate_batch` (`orchestrator.py:2234`) runs **synchronously inside the admin
request**, and three orchestrator constants exist only because of that:

| Constant | Value | Why |
|---|---|---|
| `MAX_CONSECUTIVE_ABANDONMENTS` | 3 | `:226` — skipping an abandoned candidate (CARD-083) removed the thing that used to stop a hopeless request. Without it, `generate_batch(count=50)` against impossible parameters would spend 50 × 30 = 1500 solves discovering that. Three because "three in a row is not bad luck at any rate this function can actually reach": measured over 200 draws per size at density 50, 0/200 abandoned at 10×10, 15×15 and 20×20, 4/200 at 25×25 — at p = 0.02 the chance of three consecutive is 8 in a million. |
| `BATCH_BUDGET_SECONDS` | 75.0 | `:289` — became a real question "the moment CARD-086 put gunicorn in front of the admin, because `generate_batch` runs synchronously inside the request and a worker killed mid-batch loses everything it had produced." Chosen against measurement: ~0.06 s/puzzle at 20×20, 0.55 s at 25×25, **3.90 s at 30×30**, so a 50-puzzle batch is 3 s at the small end and 195 s at the large one. 75 s "is what makes the *same* request safe at every extent, returning about 19 puzzles of a 50-puzzle 30×30 batch instead of dying at 120 s with nothing." |
| `MAX_BATCH_COUNT` | 50 | `:313` — down from 200 at the owner's proposal, because "200 was never reachable at the top of the supported range — a 200-puzzle 30×30 batch needs about 13 minutes and the server waits two — so the old ceiling described nothing real." A sanity bound, not the mechanism. |

`BATCH_BUDGET_SECONDS` is checked **before** each candidate, so one that starts
always finishes: the true ceiling is `75 + 30 = 105 s`, "which is what has to clear
the server's request timeout." `tests/test_admin_serving.py` reads `--timeout` out
of `start.sh` and asserts it, "the same way it does for the re-grade route — a
comment claiming the relationship is exactly what drifts."

## Bounds and honest gaps

- **`db/models.py:69`'s comment is stale against ADR-0031**:
  `difficulty_tier = Column(String, nullable=True)  # 'easy'/'medium'/'hard'/'guess'`.
  The tier was retired. Not determinable from code: whether any stored row still
  carries `'guess'`. The readers would treat it as "no recognisable tier" —
  `difficulty.tier_of_record` returns `None`, and `book_plan.selection_cells`
  (`:359`) drops such a record from every bucket, so a surviving row would silently
  belong to no plan cell.
- **`admin/pdf_generator.py` (349 lines) is reachable only from tests** and is the
  only `reportlab` user in the tree. `app.py:5799` records that the route "went
  through `admin/pdf_generator`" *until* CARD-135, and
  `tests/test_book_difficulty_dots.py:787` even carries
  `DINGBAT_EXEMPT_MODULES = frozenset({"nonogram.admin.pdf_generator"})`. So
  **reportlab is a declared extra of a code path nothing reaches.**
- **`admin/book_membership.py` (277 lines) is a one-off repair utility**
  (`backfill`, `release_orphans`, CARD-100), reachable only from tests and
  referenced in prose at `db/models.py:79`, `book_manager.py:1057`,
  `puzzle_review.py:2092`. Not wired to any route.
- Not determinable from code for either of the two above: whether they are retained
  deliberately or simply unremoved. No card states an intent for the modules
  themselves.
- `admin/app.py:390`'s `ALLOWED_HOSTS` is a **deliberate reimplementation** of
  `web/handler.py`'s identical frozenset (`:385` cites ADR-0007 and names
  `mask_runs` as the precedent): "Two short allowlists that agree is the intended
  shape; one importing the other is not." A **fourth** instance of the pattern.
- `admin/static/solver.js` (77 KB) and `solver_state.js` (43 KB) are substantial
  shipped browser code that no component in the model names. See
  [08-playing-a-stored-puzzle.md](08-playing-a-stored-puzzle.md).

## Related

- [06-exporting-a-finished-puzzle.md](06-exporting-a-finished-puzzle.md) — the `PageSpec` this is the only caller of
- [09-the-three-inbound-adapters.md](09-the-three-inbound-adapters.md) — the panel's door
- [10-persistence-and-the-unmodelled-edges.md](10-persistence-and-the-unmodelled-edges.md) — the database and the dual-mode doubling
- ADRs: [ADR-0030](../../../../meta/architecture/decisions/adr/0030-admin-remote-access-behind-a-credential.md) · [ADR-0032](../../../../meta/architecture/decisions/adr/0032-admin-storage-guarantees.md) · [ADR-0033](../../../../meta/architecture/decisions/adr/0033-book-assembly-stays-in-ctx-001.md) · [ADR-0034](../../../../meta/architecture/decisions/adr/0034-default-book-plan-150-at-40-40-20.md) · [ADR-0035](../../../../meta/architecture/decisions/adr/0035-book-readiness-gate-against-the-plan.md) · [ADR-0036](../../../../meta/architecture/decisions/adr/0036-book-page-geometry-via-page-spec.md) · [ADR-0037](../../../../meta/architecture/decisions/adr/0037-book-puzzle-page-band-and-strokes.md)
- Cards: `CARD-080` (the storage guard and the 20 deleted rows) · `CARD-145` (the OOM and the page-at-a-time export) · `CARD-101` (silent write loss in DB mode) · `CARD-139` (the duplicate module tree)
