# CARD-293 — vector interior vs raster interior, measured

**Spike. Ships nothing.** `git diff c0a6ac54..HEAD -- src/ tests/ pyproject.toml` is
empty (AC-6, G-1). The prototype is `scripts/card293_vector_probe.py`; the AC-4
demonstration is a scratchpad script quoted in full below. The question is
**should the book interior be emitted as vector PDF, with the cover left raster**,
and the answer is **yes on the measurements, and the decision is the owner's**
(G-7).

Everything numbered below was produced on one machine state, interleaved, and
**re-derived a second time before this document was written** (G-5). Each figure
names the door it came through.

---

## 0. The finding that reframes the question: the PDF writer is already hand-rolled

`book_pdf_generator._write_pdf` (`:7047`) and `_write_page` (`:7147`) do **not**
call `Image.save(save_all=True)`. Since CARD-145 they drive `PIL.PdfParser`
directly — allocating object ids, writing the header, the catalog, each page
object, each contents stream, the xref and the trailer by hand. Per page they
write three objects:

```
image_ref     : stream=<JPEG bytes>, Filter=/DCTDecode, ColorSpace=/DeviceGray
page_ref      : Resources={XObject:{image}}, MediaBox=[0 0 612 792]
contents_ref  : stream=b"q %f 0 0 %f 0 0 cm /image Do Q\n"
```

A vector interior replaces **only the third line** — the contents stream becomes
operators instead of a one-image draw — drops the first, and adds three objects
**once per file** for the font. The object-table pre-allocation, the one-page
streaming shape, the page count tripwire (`_as_planned`) and the whole
`BytesIO`/xref/trailer path are untouched.

**So this is not "adopt a PDF library". The PDF plumbing a vector interior needs
already ships, written by this project, inside the file that would change.** The
prototype proves it by writing its pages with the *same* `PdfParser` calls.

---

## 1. AC-5 — font embedding, priced first (the one genuinely hard part)

### It is not hard, and the reason is a number

`src/nonogram/export/fonts/DejaVuSans.ttf` is **757,076 B**. Deflated it is
**379,441 B**, and that cost is paid **once per PDF**, not per page.

| embedding option | bytes in the PDF | fidelity | verdict |
|---|---|---|---|
| **whole font, FlateDecode** | **379,441 once** | identical to today's pages | **recommended** |
| table-stripped sfnt (drop `GPOS`/`GSUB`/`MATH`/`kern`/`name`/`post`/`GDEF`/`FFTM`/`gasp`), Flate | 321,426 once | identical — none of those tables is consulted for a simple `/TrueType` font with `/WinAnsiEncoding` | available, −58,015 B, **not worth the 28 lines** |
| true glyph subset (`loca`/`glyf` rebuild + composite closure) | ~15,000 once | identical | **not needed — this is the expensive half and it buys 0.6 of one raster page** |
| PDF base-14 `/Helvetica` | **0** | **typeface changes**; every `type_px`/`_band_font`/`_guide_face` measurement in the tree is DejaVu's | rejected |
| digits drawn as paths | ~0 | identical shapes, no text layer, no copy/search | rejected (and header text would still need a face) |

Scale it against the thing it is competing with: a raster interior page costs
**~381,564 B each** (§2). **The whole font costs less than one raster page, once.**
On the 24-page book measured here the font is 93 % of the vector file; at 150
pages it is 68 %; at 450 it is 41 %. Subsetting is an optimisation for a later
card, if ever.

### What the job actually is, in lines

No stdlib module parses sfnt, so a PDF font dictionary's required fields come
from `struct` over five tables. Measured on the prototype, with docstrings and
comments excluded:

| piece | code lines |
|---|---|
| sfnt table directory + `head`/`hhea`/`maxp`/`OS/2`/`hmtx`/`cmap` (format 4) reader | **105** |
| the three PDF objects (`/Font`, `/FontDescriptor`, `/FontFile2`) | **33** |
| the centred-text operator (`BT /F1 s Tf x y Td (…) Tj ET` + advance-width centring) | **25** |
| table-stripper (optional, not recommended) | 28 |
| **total needed** | **163** |

**That is the estimate's basis: working code, not a guess.** It renders, and an
independent renderer agrees (§4).

### It is proved, not asserted

`~/Documents/nonogram-reviews/CARD-293/card293-font-whole.pdf` is a real 30×30
book page — frame, grey cell lines, heavy fifths, border, header band, folio and
**all 540 clue digits** — rendered by **poppler** (`pdftoppm -r 300`, an engine
that did not write the file) to 2550×3300 px with every digit in its own cell.
`card293-font-stripped.pdf` is the same page with the stripped font.

**AC-5 is answered: the job is ~163 lines and 379 KB per file, and it works.**
There is no blocker here, so the rest of the comparison stands.

---

## 2. AC-1 — the comparison table

### What each arm IS, printed before any result was read (G-4, CARD-292)

```
pages            24
grid_sizes       {"18x18": 10, "20x20": 14}
first_page       20x20 @ interior page 4
last_page        18x18 @ interior page 27
trim_px          [2550, 3300]      dpi 300
thin_thick_px    [3, 6]            (COMP-007's live rule widths on this book)
vector_sha256    d479a27f4cd16fbe  (first 16)
raster_sha256    4abf8240e0d6eaca  (first 16)
```

**The book.** `tests.helpers.book_corpus.corpus_puzzles()[:24]` on
`corpus_book()` — CON-018's Book 1 profile, 8.5 × 11 in at 300 DPI. Real
puzzles, the real `puzzle_page_plan`, the real `cell_sizes` map, the real
`compute_layout`. 24 rather than 150 so seven interleaved A/B rounds fit a sane
wall clock; all per-page figures scale linearly and the extrapolation is stated.

**What each arm draws.** Both arms draw *the same ink* from *the same*
`Layout`: grid rules, the every-fifth rules, the border, the `PuzzleFrame`, and
every clue digit. The raster arm is then JPEG-encoded and written by the
**production** `BookPDFGenerator._write_pdf` in its streaming (one-page-retained)
shape. **The raster arm is therefore a floor on the raster cost, not the
production page cost** — the shipped path additionally calls `render_pages`
(which draws a second, discarded solved page), the page frame, the QR glyph and
the footer. Both futures pay that composition cost; this compares the two output
technologies and nothing else.

### File size

| | vector | raster | ratio |
|---|---|---|---|
| 24-page interior, whole file | **407,976 B** | **9,157,535 B** | **22.4× smaller** |
| per page, as shipped | 16,999 B | 381,564 B | 22.4× |
| per page, **excluding the one-time font** | **1,189 B** | 381,564 B | **321× smaller** |
| one 30×30 page's content stream | 11,680 B raw / **1,339 B** deflated | 524,407 B | 392× |
| one 18×18 page's content stream | 5,913 B raw / **856 B** deflated | 360,603 B | 421× |

Extrapolated at 1,189 B/page + 379,441 B of font:

| interior | vector | raster (at 381.6 KB/page) |
|---|---|---|
| 24 pages | 0.41 MB | 9.2 MB |
| 150 pages | **0.56 MB** | 57.2 MB |
| 450 pages (the book the reviews came from) | **0.92 MB** | 171.7 MB |

Door: `scripts/card293_vector_probe.py page`, re-derived; both shas identical
across runs.

### Generation wall clock — interleaved A/B/A/B, seven rounds, twice (G-4, G-6)

Run 1 — load average `3.97 / 2.74 / 2.68` at **both** ends (identical, so the box
did not move under the arms):

```
order   V R V R V R V R V R V R V R
vector  0.0341 0.0328 0.0329 0.0329 0.0338 0.0333 0.0328
raster  0.3080 0.2806 0.2817 0.2801 0.2810 0.2872 0.2801
min     vector 0.0328   raster 0.2801
median  vector 0.0329   raster 0.2810
```

Run 2 (re-derivation, G-5) — load `3.71 / 3.06 / 2.82` at the start,
`3.49 / 3.03 / 2.81` at the end:

```
vector  0.0330 0.0334 0.0326 0.0331 0.0329 0.0328 0.0327
raster  0.3025 0.2816 0.2817 0.2805 0.2842 0.2810 0.2808
min     vector 0.0326   raster 0.2805
median  vector 0.0329   raster 0.2816
```

**Vector is 8.5× faster on medians (0.0329 s vs 0.2810/0.2816 s for 24 pages):
1.37 ms/page against 11.7 ms/page.** The vector median is identical to four
decimals across two runs; the raster median moves by 0.0006 s. The effect is
three orders of magnitude larger than the reproducibility, so CARD-218's trap
does not apply — but it is reported interleaved anyway, and never on one run.

### Memory — the weak instrument declared, and the exact figure given

**Peak RSS is the weak instrument** (CARD-218 measured its own fix *removing* a
192.6 MiB retention while the peak went **up**, because peak RSS is
allocation-order dependent). Reported anyway, interleaved, `/usr/bin/time -l`,
four separate processes alternating V R V R:

| arm | peak RSS run 1 | peak RSS run 2 |
|---|---|---|
| vector | 72,335,360 B (69.0 MiB) | 72,089,600 B (68.8 MiB) |
| raster | 128,696,320 B (122.7 MiB) | 128,483,328 B (122.5 MiB) |

**The exact figure is the retention, in this project's own unit**
(`PAGE_BITMAP_BYTES = 2550 × 3300 × 3 = 25,245,000`, `tests/test_book_pdf_memory.py:210`):

| arm | largest per-page artefact held | in page bitmaps |
|---|---|---|
| raster | 25,245,000 B (one page bitmap, by construction — CARD-145) | **1.00** |
| vector | 6,218 B (the largest content stream) | **0.000246** |

The raster figure is not measured, it is **structural**: CARD-145 pins the
retention at exactly 1.00 page bitmaps as an equality. The vector figure is
likewise structural: **no page bitmap is ever allocated**, so there is nothing to
retain and nothing to release. CARD-145's `del page` line, its 2.00-vs-1.00
equality test, and the whole 512 MB OOM story become **vacuous rather than
satisfied** on the interior. (The cover still allocates one; see §6.)

---

## 3. AC-2 — the printed proof, and the verdict on 0.3 / 0.8 / 1.3 pt

### What was produced, and where

`~/Documents/nonogram-reviews/CARD-293/`:

| file | what it is |
|---|---|
| **`card293-AC2-side-by-side.pdf`** / `.png` | **the sheet to print**: the same grid corner of the same 30×30 page, four ways at 1:1 300 DPI |
| `card293-proof-vector.pdf` | 2 full pages — owner's 0.3/0.8/1.3 pt, then CARD-227's 0.48/1.28/2.08 pt |
| `card293-proof-raster.pdf` | 3 full pages — owner's weights rasterised, CARD-227's rasterised, and **shipped today** |
| `card293-detail-raster-*.png` | the three raster details alone, 1:1 |
| `card293-font-whole.pdf`, `card293-font-stripped.pdf` | §1's font proof pages |
| `card293-arm-vector.pdf`, `card293-arm-raster.pdf` | §2's two arms, 24 pages each |
| `card293-vector-{owner,card227}-weights-at-{300,1200}dpi.png` | the four poppler renders §3's measurements were taken from |
| `card293-ac4-stream-assertion.py` | §4's replacement, runnable |

The four panels of the side-by-side are: **raster at the weights shipped today
(3 px / 6 px)**, **raster at the owner's weights (which round to 1 / 3 / 5 px)**,
**vector at the owner's weights rendered at 300 DPI**, and **vector at the
owner's weights rendered at 1200 DPI** (a press RIP) downsampled to 300 for the
sheet.

### What the weights become, re-derived

| design | cell line | → device px at 300 DPI | fifth | border |
|---|---|---|---|---|
| **shipped today** (COMP-007, `cell/30`) | 0.72 pt = 0.2540 mm | **3** | 1.44 pt → 6 | 1.44 pt → 6 |
| **CARD-227 / ADR-0037/R2 amended** | 0.48 pt = 0.1693 mm | **2** | 1.28 pt → 5 | 2.08 pt → 9 |
| **owner's artifact** | 0.30 pt = 0.1058 mm | **1** | 0.80 pt → 3 | 1.30 pt → 5 |

### Measured on the rendered vector file, by an engine that did not write it

Poppler, scanning one row through the middle of the first cell of the owner's
0.3 pt vector page (run lengths and darkest level, `< 200` threshold):

```
at  300 DPI : cell lines 2 px at grey 89 ; fifth line 4 px at grey 0
at 1200 DPI : cell lines 5 px at grey 89 ; fifth line 14 px at grey 0
```

and on the 0.48 pt page:

```
at  300 DPI : cell lines 2 px at grey 89 ; fifth line 6 px at grey 0
at 1200 DPI : cell lines 8 px at grey 89 ; fifth line 22 px at grey 0
```

Grey 89 is `round(255 × 0.35)` — **the declared tone, hit exactly, at both
resolutions**. The *width* scales with the device (×4 from 300 to 1200 DPI) while
the *tone* does not move. **That is what "there is no device floor in vector"
means, measured.** A raster interior has already made the 300 DPI choice,
irreversibly, and for the owner's design it makes it as **one pixel** — the
dropout ADR-0037/R2's amendment rejected.

### The verdict

**On the evidence I can produce: the owner's 0.3 / 0.8 / 1.3 pt design IS
printable in vector, and it is the best of the four panels.** The hierarchy the
design is after — a light grey cell grid, a clearly heavier every-fifth, a
clearly heavier border again — reads correctly at 300 DPI and better at 1200,
and the shipped 3 px / 6 px panel beside it reads as a heavy, dense grid in which
cell line and heavy rule are far closer in weight than the design intends.

**And the raster panel at the same weights is the control that shows why this
could not be had before**: at 1 / 3 / 5 px the cell grid is a one-pixel line that
the amendment refused on the evidence of 7 of 17 reviews.

**Two things I cannot settle, and they are the owner's to settle:**

1. **Dot gain on real stock.** A 0.1058 mm grey line on offset or toner on
   uncoated cream paper may spread, darken or break up. No screen render and no
   `pdftoppm` run knows that. This is exactly the question ADR-0037 itself says
   "becomes final only after the owner has seen them on printed proof pages".
2. **Whether grey cell lines are wanted at all at this tone.** The panels use the
   artifact's grey; whether 35 % reads as "light guidance" or "faded" on paper is
   a judgement about the printed object.

**So: print `card293-AC2-side-by-side.pdf` at 100 % and look at it.** My reading
of the renders is that the design is printable and better; the judgement on paper
is yours.

---

## 4. AC-4 — the test replacement, demonstrated with line counts

### The test chosen

`tests/test_book_proof_pages.py :: TestBookProof_StrokesMeetBookMinimum` — three
tests, each parametrised over both axes, making ADR-0037's claims about the
drawn page. It reads **several** `Drawing` fields (`grid_top`, `grid_left`,
`grid_right`, `grid_bottom`, `columns`, and `cell`, which is itself derived from
three of them), so the comparison is of a real reconstruction.

### The ink side, as it is today

```python
def _scan(page, axis, mode="L"):
    drawing = drawing_of(page)                       # reconstruct geometry from pixels
    pixels = np.asarray(page.convert(mode))
    past_last_rule = round(drawing.cell)             # cell = (grid_right - grid_left) / columns
    if axis == "vertical":
        row = drawing.grid_top + round(drawing.cell / 2)
        return pixels[row, drawing.grid_left : drawing.grid_right + past_last_rule]
    column = drawing.grid_left + round(drawing.cell / 2)
    return pixels[drawing.grid_top : drawing.grid_bottom + past_last_rule, column]

def _rule_widths(scan):
    return [len(run) for run in _runs(scan < INK_LEVEL)]   # INK_LEVEL = 128, a chosen threshold

def test_every_thin_rule_clears_the_quarter_millimetre_floor(book1_large_page, axis):
    widths = _rule_widths(_scan(book1_large_page, axis))
    assert len(widths) == MAX_SIZE + 1, "a 30-cell grid is ruled 31 times"
    thin = [w for i, w in enumerate(widths) if i not in self.HEAVY_INDICES]
    assert min(thin) >= MIN_THIN_RULE_PX
    assert min(thin) / PX_PER_MM >= MIN_THIN_RULE_MM
# ... + test_every_heavy_rule_is_twice_its_thin_rule, + test_the_rule_pixels_are_pure_black
```

Note what it is doing: it **counts consecutive dark pixels** to recover a width
the generator knew exactly, having first **counted rules** to recover a column
count the generator knew exactly, having first chosen a grey threshold to decide
what ink is. `drawing_of`'s own docstring says `columns` is *"counted from its
vertical rules"* and `grid_right` is *"measured at the same edge of the rule as
`grid_left`"*. Every one of those is a reconstruction.

### The content-stream side, written and run

The file is `~/Documents/nonogram-reviews/CARD-293/card293-ac4-stream-assertion.py` and is in the hand-back; it **passes** against the prototype's vector PDF,
and **fails on the right page** (see the mutant check below).

```python
def strokes(stream):
    """(width_pt, grey, axis) for every stroked line, in order."""
    width, grey, out = 1.0, 0.0, []
    for token in stream.splitlines():
        if m := re.fullmatch(rf"({N}) w", token):   width = float(m.group(1))
        elif m := re.fullmatch(rf"({N}) G", token): grey = float(m.group(1))
        elif m := re.fullmatch(rf"({N}) ({N}) m ({N}) ({N}) l S", token):
            x1, y1, x2, y2 = (float(g) for g in m.groups())
            out.append((width, grey, "vertical" if x1 == x2 else "horizontal"))
    return out

def test_a_thirty_cell_grid_is_ruled_thirty_one_times_on_each_axis(stream):
    drawn = strokes(stream)
    for axis in ("vertical", "horizontal"):
        cell  = [s for s in drawn if s[2] == axis and s[1] > 0]
        fifth = [s for s in drawn if s[2] == axis and s[1] == 0]
        assert len(cell) + len(fifth) + 2 == 31

def test_every_cell_line_clears_the_stroke_minimum(stream):
    assert min(s[0] for s in strokes(stream)) >= MIN_RULE_MM * PT_PER_MM

def test_the_three_weights_are_distinct_and_the_cell_line_is_the_declared_grey(stream):
    assert {(s[0], s[1]) for s in strokes(stream) if s[1] > 0}  == {(0.48, 0.35)}
    assert {(s[0], s[1]) for s in strokes(stream) if s[1] == 0} == {(1.28, 0.0)}
    assert re.search(r"\n2\.08 w\n", stream), "no outer border at 2.08 pt"
```

Reading the stream is three `PIL.PdfParser` calls — the same parser
`tests/helpers/pdf_pages.py` already opens a book PDF with:

```python
parser = PdfParser.PdfParser(buf=data)
page = parser.read_indirect(parser.pages[page_index])
return parser.read_indirect(page[b"Contents"]).decode().decode("ascii")
```

### The line counts (AC-4's gate)

Code lines only — blanks, comments and docstrings excluded, counted
mechanically:

| | test bodies | the reader they rest on | **total** |
|---|---|---|---|
| **ink (today)** | **38** (`TestBookProof_StrokesMeetBookMinimum`) | 21 in-file (`_runs` 10, `_scan` 9, `_rule_widths` 2) **+ 109** in `tests/helpers/page_ink.py` (380 lines of file) | **168** |
| **content stream** | **19** | **22** (`content_stream` 11, `strokes` 11) | **41** |

**4.1× smaller.** Taking only the per-test cost and leaving `page_ink.py`
amortised across its call sites in 21 files, it is 59 against 41 — **1.4× smaller**; and
the apparatus that is amortised is 109 lines of pixel archaeology against 22
lines of stream reading, **5× smaller**. Both readings are stated because both
are true and they answer different questions.

### Is it *more exact*, or merely different? — more exact, and it is shown

| | ink | stream |
|---|---|---|
| rule width | counted dark pixels, whole numbers only | **`0.48 w`** — the number used |
| colour | `< INK_LEVEL` (128), a chosen threshold | **`0.35 G`** — the tone declared |
| column count | counted rule groups, after dropping a frame identified heuristically | implicit in the stroke list, with no heuristic |
| cell size | `(grid_right − grid_left) / columns`, all three reconstructed | the layout's own number, stated |
| tolerance | `pytest.approx(abs=CELL_TOLERANCE_MM)`, `CELL_PITCH_SLACK_MM`, `_RULE_SHARE = 0.9` | **none** |
| what it reads | a **JPEG photograph** of the drawing, with DCT ringing (which is why `TestBookProof_StrokesMeetBookMinimum` has to read the in-memory page, *not* the shipped PDF — "the file's DCT round trip greys a 3-pixel rule's edges") | **the shipped file** |

That last row is the strongest single point: today the pure-black assertion
**cannot be made against the artefact that ships**, only against an in-memory
page upstream of it. A content stream assertion reads the file the printer gets.

### Mutant check — it discriminates

Run against `card293-proof-vector.pdf`:

```
page 1 (owner 0.3/0.8/1.3 pt):  test_every_cell_line_clears_the_stroke_minimum  FAILED (correct)
page 1                       :  test_the_three_weights_...                      FAILED (correct)
page 2 (0.48/1.28/2.08 pt)   :  both PASS
```

### Does `Sheet`'s independent-oracle role survive? — yes, intact

`tests/property/test_book_pdf_geometry.py`'s `Sheet` works **entirely in
millimetres** and imports no geometry (`"Nothing here imports compute_layout,
PageSpec or book_page_spec"`). Its outputs are compared against
`drawing_of(page)` — the measured artefact. The pairing is *independent
reimplementation ↔ artefact*, and a vector migration changes **only the right
half**: `Sheet` is untouched, and `sheet.drawing_left_mm(...)` is compared against
a coordinate the stream states rather than one `drawing_of` reconstructs.

CLAUDE.md's rule ("prefer an independent second implementation over re-deriving a
value with the same function you're testing") is preserved exactly, and the
comparison gets **stronger**, because today `Sheet`'s exact millimetres are
compared through `PX_PER_MM` rounding and explicit tolerances, and against a
stream they can be compared at full precision.

---

## 5. AC-3 — the dependency baseline stays shut

`pyproject.toml` is **unchanged** (AC-6's diff is empty). The prototype's imports
are `argparse`, `json`, `statistics`, `struct`, `sys`, `time`, `zlib`,
`dataclasses`, `io`, `pathlib`, `typing` — **stdlib** — plus `PIL`
(`Image`, `ImageDraw`, `ImageFont`, `PdfParser`) and `nonogram.export.layout`.
No NumPy is needed on the vector path at all.

**Nothing forced a library.** `reportlab`, `fpdf2`, `pypdf` and `fontTools` were
all unnecessary: `PIL.PdfParser` already writes the object structure, and the
163 lines of §1 cover the only thing it does not do. This continues
`export/svg.py`'s precedent exactly — *"`svgwrite` or `cairosvg` would buy
nothing here and would reopen a dependency baseline ADR-0006 closed"* — and
**ADR-0006/R1 does not need revisiting.**

One note for the phase: `PIL.PdfParser` is an *internal* Pillow module, so a
Pillow major bump could move it. That risk is **already taken** — CARD-145 took
it, and `_write_pdf`, `_write_page` and `tests/helpers/page_ink.pdf_page_boxes`
all depend on it today. A vector interior adds no new exposure.

---

## 6. The costs, stated honestly — two of them are smaller than the card claims

### What actually breaks

**The 21 `tests/fixtures/book_baseline_card*.json` recordings.** Each holds
`interior_bytes` and a per-page digest list for `baseline_puzzles()` on
`corpus_book()`; `book_baseline_card248.json` records 3,354,646 B over 13 pages.
A vector interior changes every one of those bytes.

**But this is not a fixture regeneration and not an owner decision.** The board's
own established move is to **record a NEW baseline beside the old one**, naming
what it supersedes and why — and it has done so **twenty times**: twenty of the
twenty-one files name the file they supersede and why (`card248` supersedes
`card223`, `card224` supersedes `card248`, `card206` supersedes `card224`, and so
back to `card145`, which supersedes nothing). One more link is the standing,
cheap, well-rehearsed procedure. `tests/fixtures/**` is still never regenerated.

### What does NOT break — and the card says it does

**CON-019 is not at risk.** Its statement is about *the CLI's and the web UI's*
exports: *"for any generation request the PNG, SVG and PDF files COMP-007
writes are byte-for-byte identical to those written before the book geometry
existed"*. A vector **book interior** lives in
`src/nonogram/admin/book_pdf_generator.py` and changes no COMP-007 renderer. The
prototype demonstrates this: it reads `Layout` and writes its own page objects,
touching neither `export/pdf.py` nor `export/png.py`.

**`tests/fixtures/a4_golden/` is not at risk either.** Its two files are
`compute_layout(row_clues, column_clues)` with **no PageSpec** (the default A4
path) and SHA-256 of the **CLI's** PNG/SVG/PDF. Neither is a book artefact.
`ADR-0036/R1`'s `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` is a claim
about the *default* `PageSpec`, which a book-interior change does not reach.

**So the byte-identity cost is one new baseline recording, not four tripwires
and a standing-rule conflict.**

### What stays raster, and what disappears

* **Pillow does not leave.** The **cover** (an uploaded photograph, `"RGB"`,
  `_write_pdf(mode="RGB")`), uploaded-image fitting, the PNG export, the CLI's
  own PDF, the cover title face — all still Pillow. This is not a dependency
  removal and `_write_pdf`/`_write_page` keep their image path for the cover
  file.
* **One or two smoke tests stay**, because a valid content stream can still be a
  broken PDF (a missing font resource, a bad `/Resources` dict). The honest check
  is the one this spike already ran: rasterise with an engine that did not write
  the file.
* **Some of it disappears rather than migrating.** The JPEG round trip has
  nothing to round-trip, so every "measure on the in-memory page because DCT
  greys the edges" workaround goes; the `"L"`-vs-`"RGB"` colour-space branch
  (CARD-147) becomes a `g`-vs-`rg` operator; and CARD-145's whole
  one-page-retained apparatus becomes vacuous for the interior.

### The 12 queued print-layout cards — which would be **rewritten** vs merely written

| card | | why |
|---|---|---|
| **CARD-227** — three rule weights | **rewrite** | It exists *because* of the floor. Its 0.48/1.28/2.08 pt is the owner's 0.3/0.8/1.3 scaled ×1.6 so the thinnest line is 2 px. In vector the owner's own numbers are available and the amendment's whole arithmetic is moot — the card's **decision** changes, not just its test. |
| **CARD-208** — clue numbers in ruled boxes | **rewrite** | Many thin rules at clue-box scale: exactly the sub-pixel case. |
| **CARD-215** — given cells (black cell, dot) | **rewrite** | Its own AC says *"the dot is at least **1 device pixel** across"* — a device-floor constraint with no meaning in vector. |
| **CARD-226** — two-up slots split by a **light** rule | **rewrite** | "Light rule" is the furniture-vs-grid problem ADR-0037/R2 says can no longer be solved by width. In vector it can. The card cites ADR-0037/R2 directly. |
| CARD-207, 209, 229, 230, 231, 232, 233 | **written, tests retargeted** | Page composition and type, not stroke weight. The design is unchanged; the ACs' *instrument* moves from ink to stream, and §4 says that is cheaper. |
| CARD-216 | unaffected | Storage and the web player; no print ink. |

**4 rewritten, 7 written with retargeted tests, 1 untouched.** The card's "several
exist *because* of the raster floor — CARD-227 most literally" is right, and the
count is four.

### Scope of the phase, if the owner says yes

Roughly **5–7 cards**:

1. **ADR** — vector interior, raster cover; the split, the font decision, and what
   CON-019/ADR-0036 do and do not reach. (Not a card; it gates the rest.)
2. The font module — the 163 lines of §1, with its own tests.
3. The content-stream page builder from a `Layout` — grid, frame, clues.
4. The non-puzzle pages — guide, TOC, dividers, answer tiles, QR glyph, difficulty
   dots. **This is the largest card and the one the spike deliberately did not
   price** (G-3): the prototype draws one puzzle page, not a page plan.
5. `_write_pdf` splitting its two page kinds, and the new baseline recording.
6. Test migration, 21 files, incremental.
7. Possibly: a `review-lens` → real test upgrade for ADR-0037/R2.

Item 4 is the real unknown. Everything in §1–§5 says the *mechanism* is cheap;
nobody has priced redrawing the guide's worked example, the pipeline diagram and
the difficulty legend as operators.

> **The one *primitive* of item 4 has since been priced, and not here.**
> CARD-294 built the interior's drawing vocabulary and measured the round
> shape: **24 code lines, 7 operators per mark, and a worst radial error of
> 2.7253e-4 of the radius — 1/44 of a device pixel at 1200 DPI on the largest
> dot the book prints.** The figures are in
> **`meta/profiling/card-294-curve-price.md`**, a sibling rather than an
> appendix to this file: this one is a spike report whose diff against `src/`
> is empty by its own AC-6, and CARD-294 ships code. Nothing measured above
> or below is changed by it. The rest of item 4 — the *page composition* of
> the guide, the TOC and the answer tiles — is still unpriced and is
> CARD-295/296/297's.

---

## 7. Recommendation

**Go vector for the interior, keep the cover raster — and do it before the 12
print-layout cards are dispatched.**

The numbers behind it, all re-derived:

* **22.4× smaller files** (321× per page excluding the one-time font); a 450-page
  interior falls from ~172 MB to **~0.9 MB**.
* **8.5× faster** page generation (1.37 ms vs 11.7 ms per page), interleaved,
  twice, under one recorded machine state.
* **Retention 1.00 → 0.000246 page bitmaps.** The 512 MB OOM story becomes vacuous
  for the interior.
* **Font embedding costs ~163 lines and 379 KB per file, once** — proved, not
  estimated — and **no new dependency**; ADR-0006/R1 stays shut.
* **The test apparatus gets 4.1× smaller and strictly more exact**, and for the
  first time can assert on the file that actually ships rather than on an
  in-memory page upstream of the JPEG.
* **The owner's own 0.3 / 0.8 / 1.3 pt design becomes available**, and on the
  renders it is the best of the four panels.
* **The byte-identity cost is one new baseline recording**, the board's own
  twenty-times-rehearsed move — not a CON-019 breach and not an a4-golden breach.

Against it: a phase of **5–7 cards**, of which **one** — redrawing the guide, TOC,
dividers and answer tiles as operators — is not priced here and could be large.
And **4 of the 12 queued cards would be rewritten rather than written** if they
are dispatched first, which is the cost of delay the owner named.

**Whether to spend that phase is the owner's decision, not this card's.** What
this card can say is that the mechanism is cheap, the dependency baseline holds,
the measurement is one-sided, and the design the ADR had to refuse is printable —
and that the proof of the last one is a sheet of paper at
`~/Documents/nonogram-reviews/CARD-293/card293-AC2-side-by-side.pdf`, which only
the owner's eyes can finish reading.
