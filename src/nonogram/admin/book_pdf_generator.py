"""PDF generation service for book scaffolding.

Exports a book as two files (FR-043, INV-013): the interior PDF — guide page,
puzzles, SOLUTIONS divider and answers, with no cover page — and the cover
file, a single front-cover page.

Every page is the book's own trim at 300 DPI (CARD-116, FR-030/FR-032)
--------------------------------------------------------------------
The generator used to hard-code a 2550 x 3300 px letter page and print each
puzzle through the A4 layout, so a book puzzle was sized for A4 and then laid
on a sheet it had never been measured against. It now builds **one page spec
per page** through :func:`~nonogram.admin.book_page_spec.book_page_spec` — the
one door onto the book's sheet (CARD-115) — and every page of the interior
(guide, puzzles, SOLUTIONS divider, answers) and the cover file's single page
is that trim: 2550 x 3300 px on the Book 1 profile, 1800 x 2700 px on a 6 x 9
in book.

``book_page_spec`` takes the page's **1-based position in the interior**, and
that position is where the page's parity comes from (FR-043): interior page 1
is the guide page and is right-hand (odd), so the gutter margin is on its
left; page 2 is left-hand, and so on for every page kind alike. Parity moves
the drawing sideways only — its top edge is top margin + band on every puzzle
page (FR-032) — which is COMP-007's arithmetic, not this module's.

**This module fits no cell and places no grid line** (ADR-0036/R2). Every
number it uses is read off :func:`~nonogram.export.layout.compute_layout`
called with the book's spec: the trim and the usable area through
:func:`page_frame`, the placed drawing through
:func:`~nonogram.export.pdf.render_pages`, and — since CARD-222 — a puzzle
page's **frame** through :func:`~nonogram.export.layout.interior_frame`: the
two rules' rows and weights, the puzzle area between them, the inner side the
grid-size label is set against and the centre the folio is set at. This module
strokes those and places nothing (:func:`_draw_page_frame`, :func:`_draw_rule`,
:func:`grid_size_label`). The only thing positioned here is
text the layout knows nothing about — the guide page's lines and the divider's
word — and it is positioned against the usable area the layout reported. The
guide page's worked example (CARD-167) is laid out by ``compute_layout`` on the
page's own spec — cell pitch, rule positions and widths, frame and clue size.
This module trims that layout to a single row (the vertical rules and the
frame start at the grid's top; no column clue is written), draws each step's
filled and crossed squares in its cells, and chooses where on the page the
drawing is pasted.

What the band says (ADR-0037/R1, CARD-117)
------------------------------------------
A book puzzle page's 12 mm band (TERM-028) reads **"Puzzle N · Tier"** — the
puzzle's 1-based position in the print order and the solver's tier, nothing
else. The picture's title is not on it (FR-033): a titled puzzle page gives
the picture away before the solver has drawn it. The title appears once, in
the **answer key**, as the caption over that puzzle's answer — "Puzzle N —
Title" (FR-042, CARD-134) — so the answer can be found by the number printed
on the puzzle and recognised by the name once it is found.

The band is the export's own header, set by COMP-007 inside the band the
`PageSpec` reserves; this module chooses only the *text*, by what it puts in
the two header fields of each page's :class:`~nonogram.export.ExportPayload`
(:func:`~nonogram.export.pdf.header_parts` is the non-empty members of
``(name, difficulty)``, em rule between them) — see
:meth:`BookPDFGenerator._puzzle_payload`, which clears the picture's name so
that there is no title for the page to leave off. Drawing lettering is the
admin's to decide (ADR-0036/R2 forbids fitting cells and placing rules, not
wording), and it is set in the packaged DejaVu Sans the export already uses
(ADR-0006/DEC-027), which covers the middle dot.

One full solved page per puzzle (FR-042, CARD-134, CARD-198)
--------------------------------------------------------------
The answer section was a **packed** key — six answers to a page (2 x 3) or
four (2 x 2) — from CARD-134 until CARD-198 replaced it: a "SOLUTIONS" divider
immediately after the last puzzle page (AC-292, unchanged), and then one full
solved page per puzzle, in book order, each captioned with its number and the
picture's title. :meth:`BookPDFGenerator.solved_puzzle_page` (CARD-197) is the
rendering primitive this card reuses verbatim: clues top and left, light-gray
gridlines between filled cells, the same layout call an unsolved puzzle page
at that position would make. ``interior_stream``'s answer loop calls it once
per drawable puzzle with that page's own :class:`PageSpec`, so an answer
page's margins are mirrored by its interior position like every other page's.

**The level heading is gone, on purpose.** The old packed key gave only the
first page of a level's run a small "Easy"/"Medium"/"Hard" heading; every
other page in the run carried no level text at all. Since every per-puzzle
page already carries its tier in its own band ("Puzzle N · Tier",
:func:`band_identity`), carrying that same information a second time as a
once-per-run heading would be redundant on most pages and absent on the rest —
so there is no heading and no level-divider page inside the answer section
(CARD-198's own reading of the owner's confirmed format change; flagged for
confirmation, not an owner instruction in its own right).

``book_answer_key.py``'s packing machinery (:func:`~nonogram.admin.book_answer_key.pack_answer_pages`,
:class:`~nonogram.admin.book_answer_key.Answer`, :class:`~nonogram.admin.book_answer_key.AnswerPage`)
is left in that module, unedited, though nothing in this module calls it any
longer — deleting it is a decision for later, not this card's (CARD-198
Guardrail G-5).  :func:`~nonogram.admin.book_answer_key.answer_caption` and
:func:`~nonogram.admin.book_answer_key.answer_title` remain in use: they are
the only two functions this module's answer-page loop still calls.

Levels, and the page that opens one (FR-041, INV-009, CARD-128)
----------------------------------------------------------------
A book prints **easy, then medium, then hard**, and the grouping is decided
here, at PDF time: :func:`print_order` runs the book's rows through
``book_plan.book_level_order`` — the one grouping the arrange screen, the
moves and the adds already use (FR-041) — so a legacy mixed arrangement
*prints* grouped without its stored list being rewritten (AC-260, G-1). The
sort is stable and keyed on the level alone, so the owner's arrangement
inside a level is untouched, and it is idempotent, so a book that is already
grouped is not reordered at all.

Each non-empty level opens with a **divider page** (TERM-031): one trim-sized
page carrying the level's name and nothing else — no band, no number, no
grid (G-3). An empty level has no divider, because the cut
(:meth:`BookPDFGenerator.puzzle_section`) walks the levels that are there.
The **ungraded tail** — rows whose ``difficulty_tier`` no reader can turn into
one of ADR-0031's three tiers — is not a level and opens no divider: its name
is the one thing a divider carries, and there is none to print. A blank sheet
would be a page the reader cannot account for, so those puzzles simply follow
the last named level, exactly as their band prints "Puzzle 12" and stops
(:func:`band_identity`) and their answer run starts an unheaded page
(:func:`~nonogram.admin.book_answer_key.level_heading`).

**Dividers consume no puzzle numbers.** ``N`` in "Puzzle N · Tier" is the
puzzle's 1-based position among the *puzzles* in print order, unbroken across
the levels (AC-255), while a divider is a page like any other and takes its
parity from its interior position like any other (FR-043, CARD-116). With the
guide at interior pages 1-2 (CARD-201) and the "Easy" divider at 3, the first
puzzle page is interior page 4 — a left-hand page (CARD-201 moved this
example's own numbers by one; the relationship it illustrates — a divider's
parity like any other page's — is unchanged, AC-287).

Two-up pairing needs no level rule of its own: a page is shared only by two
puzzles of **equal** tier (INV-010), and a level *is* a tier's run, so no pair
can straddle a divider. The answer section follows the same book order — one
solved page per puzzle, in print-number order — so a level's answer pages sit
contiguously exactly as its puzzle pages do, with no further arranging here
(CARD-198).

What the table of contents lists (FR-043, CARD-200, CARD-205)
--------------------------------------------------------------
The TOC sits between the guide and the puzzle section, and since CARD-205 it
lists **sections, never puzzles**: one "How to Solve Nonograms" row, then —
for each non-empty level — a heading row carrying the level's name and a
``Puzzles N–M`` row carrying that level's own divider page number, and finally
one "Solutions" row against the SOLUTIONS divider. Leader dots carry the eye
from each label across to its page number
(:meth:`BookPDFGenerator.create_toc_page`).

CARD-200 shipped it as one row per drawable puzzle, captioned "37. Ice skate"
— on a 150-puzzle book, four pages of rows. The owner's decision (Google Doc
"Nonograms - Print layout", 2026-10-13) replaced it: a puzzle is found by the
number printed in its own band, so a reader needs the TOC to say where a
*level* starts, not where each puzzle does. The amendment is to FR-043's TOC
half, whose own acceptance criteria still describe the per-puzzle listing;
flagged for the architect station in CARD-205's Worktree notes, since a kanban
card does not edit ``meta/architecture/**``.

**Its length is a term in every later page's number**, which is what makes
this more than a cosmetic change: the structural list is about six rows where
the per-puzzle one was up to several pages, so a book's puzzle pages, its
SOLUTIONS divider and its answer pages all moved earlier by the difference.
That length is decided once, from :func:`structural_toc_entry_count`, and read
by three places that must never disagree — :meth:`BookPDFGenerator.section_plan`
(the real export), :func:`interior_page_count`'s own sheet-free default, and
:func:`~nonogram.admin.book_kdp.unpaired_interior_page_count` (whose page count
chooses KDP's gutter margin). :meth:`BookPDFGenerator.interior_stream` closes
the loop with a tripwire in two halves: the rows it actually hands the drawing
must be as many as :func:`structural_toc_entry_count` says that book lists,
*and* must re-measure to the page count the plan was laid out on. Both halves,
because a page count is 1 for anything from one row up to a page's capacity
and so cannot see a row-count divergence on its own.

Two puzzles to a page (FR-040, INV-010, CARD-127)
--------------------------------------------------
:meth:`BookPDFGenerator.puzzle_pages` walks the book order from the first
puzzle and offers puzzle *i* and puzzle *i+1* to COMP-007's
:func:`~nonogram.export.layout.compute_pair_layout` **only when their tiers are
equal**. A :class:`~nonogram.export.layout.PairLayout` back means both print on
one page and the walk moves to *i+2*; ``None`` — a verdict, not an error: the
pair's largest shared cell is under 7.0 mm — means *i* prints alone and the
walk moves to *i+1*. An *exception* from that call is not a verdict and is not
read as one: it is re-raised naming the two puzzles offered, so that a member
too malformed to measure is named whether or not it happened to have a
same-tier neighbour. The last puzzle of an odd run prints alone. **The walk
never reorders**, never looks past the immediate successor for a better
partner, and never skips a puzzle to keep a later pair intact, so
concatenating the pages front to back yields the book order exactly (EC-027).

**Since CARD-248 the walk makes a second check, and it is still a verdict
about the pair's page and not about the book.** A two-up page carries one
footer strip holding **both** puzzles' QR groups (the owner's decision of
2026-10-18 — a puzzle's scannable link must not be lost), so the walk tells
``compute_pair_layout`` to reserve that strip out of the pair's height
(:attr:`~nonogram.export.layout.InteriorFrame.footer_depth`) and then asks
:func:`~nonogram.export.layout.qr_group_insets` whether the strip is wide
enough for two groups. Either refusal means the same thing the 7.0 mm floor
means: the two puzzles print on two single pages, each with its own footer
and its own link, which is one more interior page and never a two-up page with
a link missing. Both figures are constants of the sheet and the face —
:func:`_qr_group_line_px`, like :func:`_folio_reserve_px`, is measured from the
font and the DPI alone — so neither lets a page number or a book's own scale
decide whether two puzzles pair (INV-010).

What the panel decides is *which neighbours to offer* and nothing else (G-1,
ADR-0036/R2): the shared cell, both slot positions, every ruled line and every
clue centre are read off the ``PairLayout``. What it composes is the page,
because COMP-007 exposes no call that draws a *given*
:class:`~nonogram.export.layout.Layout` — :func:`~nonogram.export.png.render_image`
and :func:`~nonogram.export.pdf.render_pages` each fit their own layout from a
payload and a spec, so neither can draw a two-up slot. :func:`_stroke_drawing`,
:func:`_write_clues` and :func:`_set_band` therefore stroke what the pair
already measured, natively here rather than through the renderers' private
helpers — the precedent ``solver/propagate.py``'s ``mask_runs`` sets, and the
only shape the import layering allows. They place nothing: every coordinate
they are given came from COMP-007. That includes each slot's **frame**
(CARD-144's rectangle around clues and grid): ``compute_pair_layout`` measures
one per slot, and :func:`_stroke_drawing` strokes it last of all, on its own
four boundaries at the heavy rule (CARD-146) — so a printed pair is two framed
puzzles, not two bare grids.

Each slot carries **its own band**, "Puzzle N · Tier", measured by
:func:`~nonogram.export.layout.header_band` on that slot and set with the same
type, the same centring and the same measure-and-shrink fitting the export's
header uses (:func:`_set_band`, whose docstring records the one step of the
export's three it does not reproduce and why that step cannot be reached), so
a slot's band and a single page's band are the same ink. The upper
slot is the earlier puzzle and its drawing's top edge is the fixed row every
single puzzle page uses — top margin plus band (FR-032, EC-022).

Pairing is decided here, at PDF time, and nothing about it is stored
(Increment 15's rollback story). It shortens the interior, so **every later
page's parity flips** — which is why each page is still built on the spec of
its own position and never on a position assumed in advance. Both page counts,
before and after pairing, come back on :class:`Interior` and
:class:`BookExport`.

One page plan, asked twice (CARD-140)
--------------------------------------
:meth:`BookPDFGenerator.section_plan` is the whole of the decision above with
no drawing in it: the print order, the payload pass, and the pairing and level
walk, returned as a :class:`SectionPlan`. :meth:`BookPDFGenerator.interior_stream`
walks it to draw the interior, and the Arrangement screen calls the **same**
method to say where each puzzle will print — which is what makes the screen's
page breaks the book's pages rather than a second opinion on them. The screen
had shown a break every three puzzles, a rule no book this project prints has
ever followed.

It stays a *call*, not a stored plan (G-4): the answer depends on the book's
trim and on every row's clues, so it is re-asked whenever it is needed and the
two surfaces cannot drift. And it is asked of **this** module rather than
reimplemented in the panel's routes: a second implementation of INV-010 is
exactly what ADR-0036/R2 forbids the panel.

One page at a time (CARD-145, the 512 MB envelope)
---------------------------------------------------
A page of the Book 1 profile is 2550 x 3300 px RGB — **25.2 MB of bitmap**,
every page, whatever is drawn on it. The export used to build the whole
interior as a list and hand it to Pillow's ``save_all``, so peak memory was
25.2 MB **x the page count**: 0.5 GB at 20 pages, 3.8 GB at a 150-page Book 1.
The deployed panel has 512 MB, so the worker was OOM-killed with no traceback
— which is what the owner saw as "render crashes when I try to generate pdf".
No instance size fixes that shape; releasing a page before the next is built
does.

**How a page is built, written and released.** :meth:`BookPDFGenerator.interior_stream`
does every decision that does *not* draw — the payload pass, the pairing walk,
the packed key, the tier counts, the custom titles, and both plan tripwires —
and returns an :class:`InteriorStream`: the three page counts, known before a
single pixel exists, and a **one-shot generator** of the pages. :meth:`_write_pdf`
pre-allocates one image, page and contents object id per page from that count
(which is why the count has to be known first), writes the header and the
catalog, and then pulls one page at a time: it JPEG-encodes that page into the
output buffer and drops it before asking for the next. Nothing on the export
path holds a list of pages, and **no page survives the call that builds the
next one**: neither the producer nor the writer keeps its page bound across
it, so the number of pages this module *retains* is one, whatever the book's
length. That is asserted as an **equality** rather than as a bound —
``tests/test_book_pdf_memory.py`` measures a retained peak of exactly one page
bitmap on an 8-page and on a 179-page book, and on
:meth:`BookPDFGenerator.export_book`, which writes both files — because every
one of those ``del``\\ s is the difference between a retained peak of 1.00 and
2.00 page bitmaps, and a test that allowed 2.00 would not notice one going
missing.

**One page retained is not one page alive, and the difference is a measured
constant.** Inside a single puzzle-page build the process holds **two**
full-size bitmaps: :meth:`BookPDFGenerator._blank_page` calls COMP-007's
:func:`~nonogram.export.pdf.render_pages`, which draws a blank page *and* a
solved page from one payload, and binds ``blank, _ = render_pages(...)`` — so
the solved page, which has had no use since FR-042, is alive until that frame
returns. Registering both pages it returns measures a peak of **50,490,000 B =
2.00 page bitmaps**, and measures the *same* 50,490,000 B on the 179-page book
as on the 8-page one: it is a constant every puzzle page pays and none of them
accumulates, not a term that grows. It is also the merge-base's code untouched
— CARD-145 changed when a page is released, not what draws one (G-1) — so
reducing it belongs to whatever card revisits ``render_pages``' second page.

**The memory envelope, with its numbers.** Peak is those two page bitmaps
(50.5 MB on Book 1) plus a page's JPEG buffer, plus — and this term is real,
not rounded away — the written PDF itself, which accumulates in the returned
``BytesIO`` at a measured ~0.46 MB per page. A 179-page interior therefore
peaks near 50.5 + 81.9 = **~132 MB** instead of the old shape's 4.5 GB, about
a quarter of the 512 MB instance, and a book fits the envelope with room for
the request around it. Measured end to end, a child process exporting that
book peaks at 150.8-169.9 MB resident, interpreter and imports included. Peak
is **O(one retained page) + O(a transient constant) + O(the compressed
file)**, not O(one page x the page count); it is not a constant, and the tests
say so rather than claiming one the code does not have.

**Why Pillow rather than ReportLab.** ReportLab is an installed dependency of
the panel (ADR-0006, 2026-09-11) and can write a page and move on, but it
writes an unconditional comment line inside the PDF trailer dictionary, and
Pillow's own ``PdfParser`` — which ``tests/helpers/pdf_pages.py`` reads every
book PDF with — refuses such a trailer. Reaching for it would have meant
editing a shared test helper to accommodate a self-inflicted format change.
Pillow's ``PdfParser`` is already a writer as well as a reader:
``PdfImagePlugin`` needs the whole page list only to pre-allocate those object
ids, and the page count here is known without drawing anything. :meth:`_write_pdf`
therefore mirrors ``PdfImagePlugin._save``'s ``mode == "RGB"`` path object for
object — same ``DCTDecode`` stream, same ``MediaBox``, same contents operator,
same ``Info`` dates — so the file is byte-identical to the old one but for its
two timestamps, and every reader of a book PDF keeps working unedited.

Black-and-white or colour (CARD-147)
------------------------------------
The interior's **content** has always been pure black and white: COMP-007 draws
``INK = (0, 0, 0)`` on ``BACKGROUND = (255, 255, 255)`` and nothing else, and no
divider, guide, band, frame or answer page introduces a colour. But the **file**
declared colour — every page was composed ``"RGB"``, JPEG-encoded in RGB and
written with ``ColorSpace /DeviceRGB`` — and a print-on-demand interior that
declares colour invites the colour price for a book that has none in it.

So the book now says what it is. :class:`~nonogram.admin.book_page_spec.InkMode`
is stored on the book beside its trim (``books.interior_ink_mode``, migration
013), :attr:`BookPDFGenerator.ink_mode` reads it once in ``__init__``, and
:meth:`_write_pdf` takes the bitmap mode of the file it is writing as an
argument — ``"L"`` for a black-and-white interior, ``"RGB"`` for a colour one,
and ``"RGB"`` always for the **cover**, which is a separate file holding an
uploaded image that may be anything (CARD-135, out of this card's scope). It is
an argument and not an attribute read inside the writer precisely because the
two files of one export do not agree about it.

**The mode changes the colour space and nothing else.** ``Image.convert("L")``
applies ITU-R 601-2 luma with three integer coefficients that sum to 65536, so a
grey ``(v, v, v)`` becomes exactly ``v``: 0 stays 0, 255 stays 255, no value
between them is invented, and the set of inked pixel positions is identical
(ADR-0037/R2 — a rule is not softened, and no anti-aliasing is introduced).
Cell size, origin, gutter, rules, frame and page count are all COMP-007's and
are computed from the :class:`PageSpec`, which does not carry the mode at all.
Measured end to end on the baseline book, the eleven pages decoded back out of
a grayscale interior are **byte-identical** to the eleven decoded out of the RGB
one — JPEG keeps the luma plane and the constant chroma planes decode back to
it exactly — so the mode moves the file's size, not its ink.

**It is converted per page** (G-3, CARD-145). :meth:`_write_page` converts the
page it was handed and drops the conversion when it returns, so a grayscale
interior holds one extra one-channel bitmap (8.4 MB on the Book 1 profile,
a third of a page) inside a single page's write and never between two pages.
Nothing collects pages to convert them, and the number of pages the module
retains is still one, whatever the book's length.

**Nothing half-written escapes.** The output buffer is a local of
:meth:`_write_pdf` and is returned only after the cross-reference table and
trailer are written, so a page that will not draw at page *k* of *N* raises
through the caller and the partial bytes are released unreferenced — a route
can serve a whole PDF or an error, never a truncated one. And because the
object ids are pre-allocated, a producer that yielded the wrong number of
pages would leave dangling page references: :func:`_as_planned` counts what
the producer yields against the count the plan declared and raises
``RuntimeError`` — before the extra page is written, or before the trailer is
— so a structurally corrupt PDF is unreachable by construction.
"""

import logging
import math
import time
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from functools import lru_cache
from importlib import resources
from typing import Any, Dict, Iterable, Iterator, Optional, List, Sequence, Tuple, Union
from PIL import Image, ImageDraw, ImageFont, PdfParser
from io import BytesIO

from nonogram.admin.book_answer_key import (
    PACKED_TWO_UP,
    Answer,
    PackedAnswerPage,
    answer_caption,
    answer_title,
    plan_small_answer_pages,
)
from nonogram.admin.book_page_spec import InkMode, book_ink_mode, book_page_spec
from nonogram.admin.book_plan import TIERS, book_level_order
from nonogram.difficulty import Tier, tier_of_record
from nonogram.errors import UnletterableTitle
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    ANSWER_TEXT_FONT_MM,
    ANSWER_TILE_GAP_MM,
    DPI,
    INTERIOR_FOOTER_LINE_PT,
    DifficultyDots,
    HeaderBand,
    InteriorFrame,
    Layout,
    PageParity,
    PageRule,
    PageSpec,
    PairLayout,
    QrCaption,
    QrSlot,
    caption_slot,
    compute_layout,
    compute_packed_solved_layout,
    compute_pair_layout,
    difficulty_dots,
    header_band,
    interior_frame,
    qr_caption,
    qr_group_insets,
    qr_slot,
)
from nonogram.export.pdf import FONT_PACKAGE, FONT_RESOURCE, render_pages
from nonogram.export.png import BACKGROUND, INK

#: The panel's own logger, like the rest of ``admin/``: a dropped puzzle is
#: the only trace the export leaves of a member that did not reach the file,
#: and a ``print`` of it lands nowhere in a served request.
logger = logging.getLogger(__name__)

#: ``PdfImagePlugin._write_image``'s two branches, transcribed: the PDF colour
#: space and the procset Pillow's own writer gives a page of each image mode.
#:
#: ``{bitmap mode: (ColorSpace, ProcSet)}``. One table rather than a branch in
#: :meth:`BookPDFGenerator._write_page`, so that "what this module writes" and
#: "what the plugin would have written" can be read side by side and checked —
#: which is the claim ``_write_pdf`` makes and the reason the file stays
#: readable by every existing reader of a book PDF (CARD-145's F-7, CARD-147).
#: The plugin's own words for the two: ``"ImageB"  # grayscale`` and
#: ``"ImageC"  # color images``.
#:
#: It holds exactly the two modes a book page can be composed in (CARD-147).
#: ``"1"``, ``"P"``, ``"CMYK"`` and the alpha modes the plugin also handles are
#: deliberately absent: no page of a book is drawn in them, and a writer that
#: silently accepted one would be choosing a colour space the book never asked
#: for. :meth:`BookPDFGenerator._write_pdf` refuses anything not keyed here.
_PDF_COLOUR_SPACE = {
    "L": ("DeviceGray", "ImageB"),
    "RGB": ("DeviceRGB", "ImageC"),
}

#: What stands between a puzzle's number and its tier in the band: a middle dot
#: (U+00B7) with a space either side, exactly as ADR-0037 writes it
#: ("Puzzle 12 · Easy").
#:
#: It is part of one header piece, set as a glyph in the packaged DejaVu Sans,
#: which covers U+00B7 — unlike the em rule the export *strokes* between two
#: pieces (``pdf.HEADER_SEPARATOR``). The two marks are deliberately different:
#: the dot joins the number to its tier inside one line, the rule joins that
#: line to the picture's title on the answer page.
BAND_SEPARATOR = " · "

#: Points per inch — the one conversion between the unit type is specified in
#: and the device pixels a page is drawn in.
#:
#: A point is 1/72 in by definition, so at the 300 DPI COMP-007 measures every
#: page at (:data:`~nonogram.export.layout.DPI`) one point is 4.167 px. It is
#: written here because the pages this module draws itself — the guide page —
#: are the only ones that set type in pixels, and a pixel is not a size a
#: reader of a printed page can judge.
POINTS_PER_INCH = 72.0

#: The guide page's type, in **points** (CARD-149, AC-236).
#:
#: Interior page 1 is the one page of the book that explains how to play it,
#: and it is set for a reader who may need reading glasses to hold it (EV-0003,
#: a 2★ review of a competitor: "Very tiny squares. Not good for older
#: people."). 11 pt is ordinary book body size; 22 pt reads as a title rather
#: than as body.
#:
#: They are points and not pixels **on purpose**. Until CARD-149 the method
#: asked Pillow for Arial at 28 px and 48 px on a 300 DPI surface, which is
#: 6.7 pt of body under an 11.5 pt "title" — smaller than a legal footnote,
#: and set at body size at that. Nothing in those two numbers said what page
#: they were for, so a book profile rendered at another resolution would have
#: silently changed the apparent size of the type; sizes stated in points and
#: converted once, at :func:`type_px`, cannot.
GUIDE_TITLE_PT = 22.0
GUIDE_BODY_PT = 11.0

#: The guide page's leading: the distance from one body line's baseline to the
#: next, in points (CARD-149, AC-239).
#:
#: ~1.5x the body size, the ordinary setting for a page of unjustified text.
#: It has to be stated with the type it leads: the method's previous 50 px
#: advance is 12 pt, which sets 11 pt type on 12 pt leading and would have put
#: 46 px of glyph into a 50 px line the moment the body grew to book size.
GUIDE_LEADING_PT = 17.0

#: The space between the guide page's title and its first body line, in points
#: — the 150 px the method reserved before CARD-149, restated at 300 DPI in
#: the unit the rest of the page's type is stated in.
GUIDE_TITLE_GAP_PT = 36.0

#: A divider page's one word, in points (TERM-031, CARD-184).
#:
#: The 60 px the divider has always been lettered at on a 300 DPI page, stated
#: in the unit a reader can judge: ``type_px(14.4, 300) == 60``, so a book
#: drawn at 300 DPI prints its dividers exactly as before, and a page at
#: another resolution prints them at the same 14.4 pt instead of 60 px of
#: whatever size that is. It letters through :func:`_guide_face`, which since
#: CARD-221 is the packaged face at that exact size on every host — before
#: CARD-149 a machine without Arial printed the word at Pillow's 10 px default
#: (2.4 pt), and before CARD-221 it printed it in Pillow's own face at the
#: right size but another face's widths.
DIVIDER_PT = 14.4

#: The guide page's title (FR-041, AC-324, CARD-167). It was "How to Use This
#: Book" until the page started teaching how to solve.
#:
#: **Kept unchanged by CARD-201** (an owner-decision flag resolved in that
#: card's Worktree notes): the source PDF's own heading is "HOW TO SOLVE A
#: NONOGRAM" (all caps, singular), but this title is already an
#: owner-approved, shipped one from CARD-167, and the source document's own
#: capitalisation is its own design, not a wording instruction.
GUIDE_TITLE = "How to Solve Nonograms"

#: How many interior pages the guide occupies (FR-041, CARD-201): the
#: leading term of :func:`interior_page_count`'s formula, named rather than
#: a bare ``2`` in that function's return statement. ``1`` until CARD-201's
#: "full 1-2 page tutorial" (FR-041's own deferred clause) landed as 2 pages.
GUIDE_PAGE_COUNT = 2

#: The footer folio's own type, in points (CARD-200, G-4): CON-020's 10 pt
#: floor exactly, the same size the answer caption is set in
#: (:data:`~nonogram.export.layout.ANSWER_TEXT_FONT_MM`'s own point
#: equivalent) — a page number needs no more emphasis than the caption it
#: shares a corner with, and no setting below the floor is ever added.
FOLIO_PT = 10.0

#: The grid-size label's own type, in points (CARD-222) — CON-020's floor, the
#: same size and the same reasoning as :data:`FOLIO_PT`, which it shares the
#: footer line with: a page's two smallest marks are set alike so the line
#: reads as one line. Read from COMP-007's
#: :data:`~nonogram.export.layout.INTERIOR_FOOTER_LINE_PT` rather than
#: restated, because that is the figure the footer band's own depth is
#: measured from: a label set larger than the band was built for would print
#: into the QR icon's row (G-1).
SIZE_LABEL_PT = INTERIOR_FOOTER_LINE_PT

#: What stands between a puzzle's width and its height in the footer's
#: grid-size label (CARD-222): a lower-case ``x`` with a space either side,
#: ``"20 x 20"``, exactly as this card's AC-3 spells it.
#:
#: **ASCII, deliberately.** The owner's artifact draws a multiplication sign
#: (U+00D7) and DejaVu Sans covers it, but the interior's whole character
#: repertoire is recorded and asserted glyph by glyph
#: (``tests/test_book_interior_face.py``), and an extra glyph in it is a
#: standing commitment for every future face. The AC spells the ASCII form, so
#: no glyph is added for a mark the AC does not ask for.
SIZE_LABEL_SEPARATOR = " x "

#: The invitation set on the first of the QR icon's two footer lines
#: (CARD-223, the owner's artifact of 2026-10-14). Plain ASCII, for the reason
#: :data:`SIZE_LABEL_SEPARATOR` is: the interior's character repertoire is
#: asserted glyph by glyph (``tests/test_book_interior_face.py``) and no glyph
#: is added for a mark the artifact does not ask for.
QR_CAPTION_TEXT = "Solve it online"

#: The typed link set on the second line — **the one line CARD-210 edits.**
#:
#: Still a placeholder, and deliberately: the owner's artifact writes
#: ``nonogram.example/p/052`` and calls it a stand-in "until the online solver
#: has a real address", and CON-021 refuses a printed link that points at a
#: dead or admin-only URL. ``.example`` is one of the names RFC 2606 reserves
#: precisely so that it can never resolve, so this text cannot become a live
#: address by accident — the same inertness
#: :func:`_draw_qr_placeholder`'s checkerboard has, stated for the words
#: instead of for the glyph.
#:
#: Per **puzzle**, not per page: the number interpolated is the puzzle's own
#: position in the book, so a two-up page's two slots print two different
#: links, and the three-digit padding is the artifact's own (``052``). One
#: template in one module, read only by :func:`qr_link`, so the whole of
#: CARD-210's edit to the printed link is this string.
QR_LINK_TEMPLATE = "nonogram.example/p/{number:03d}"

#: How many digits of a page number :func:`_folio_reserve_px` plans room for
#: on a two-up page's lower slot (CARD-204 Fix 4, owner decision 2026-10-12,
#: "fixed universal reserve") — a fixed ceiling, never this book's own
#: largest page number or this page's own number. Four digits is far beyond
#: anything a physical print book this software produces reaches in
#: practice (the project's own Amazon market snapshot puts the median
#: competitor book at ~120 pages, and no trim CON-018 stocks is bound
#: anywhere near 1000 pages) — a generous, constant ceiling, not a
#: measurement of any specific book. A hypothetical book past 9999 pages
#: would not break: its own five-digit folios simply would not clear
#: :func:`_draw_folio`'s own width check at this corner and would be
#: omitted, exactly as every page kind with too little room already is.
#: **What this room costs the owner** (measured in CARD-204's cycle-4 review
#: and reproduced twice from independent sweeps, see
#: :func:`~nonogram.export.layout.compute_pair_layout`'s own docstring): the
#: reserve takes part in the pairing verdict, so ~5% of adversarial pairs
#: that would pair unreserved at >= 7.0 mm are refused and ~9% more commit a
#: slightly smaller cell — and every refused pair is one more interior page,
#: i.e. a longer interior and, on KDP, a higher print cost per copy.
#: Accepted knowingly (owner decision 2026-10-12, reaffirmed 2026-10-13 with
#: that measurement in hand), against the alternative of losing the folio
#: from every two-up page.
FOLIO_RESERVE_DIGITS = 4

#: The table of contents page's title (CARD-200) — plain and descriptive,
#: the same register as the divider's own one-word pages rather than a
#: styled heading; every TOC page repeats it (see :func:`create_toc_page`),
#: so a multi-page TOC reads as one list continuing, not several unlabelled
#: ones.
TOC_TITLE = "Table of Contents"

#: One TOC entry's own type, in points (CARD-200, G-4): CON-020's floor, the
#: same reasoning as :data:`FOLIO_PT` — a listing row needs to be read, not
#: to draw the eye the way the guide page's body text does, so it is set at
#: the floor rather than at :data:`GUIDE_BODY_PT`.
TOC_ENTRY_PT = 10.0

#: The gap below one TOC entry's own line, in points (CARD-200) — a fixed,
#: small fraction of the entry's own size rather than a second invented
#: leading constant, so rows read as a list and not as run-on body text.
#:
#: Since CARD-205 it is also the **horizontal** clearance a row's leader-dot
#: run keeps from the label on its left and from the page number on its
#: right (:meth:`BookPDFGenerator.create_toc_page`) — the same single gap
#: constant on both axes rather than a second invented one, for exactly the
#: reason this one exists at all.
TOC_ENTRY_GAP_PT = 4.0

#: The **extra** gap set above a row that opens a group, in points
#: (CARD-205 Fix 1, owner decisions 2026-10-14) — what separates one group
#: of the structural list from the group above it, so the list reads as
#: sections rather than as eight evenly spaced rows.
#:
#: Set above every row whose :attr:`TocEntry.starts_group` is true: the
#: three level headings **and** the :data:`TOC_SOLUTIONS_LABEL` row, which
#: is a numbered row rather than a heading but opens the last group all the
#: same (the owner's second decision, 2026-10-14 — before it, ``Solutions``
#: sat one ordinary line under the Hard range and read as the tail of that
#: group). Four gaps on a three-level book, not three.
#:
#: The owner's own sample (Google Doc "Nonograms - Print layout",
#: 2026-10-13) sets a blank line between the groups. This is that
#: separation, and deliberately **not** a blank :class:`TocEntry` row: a
#: spacer row would be counted (AC-1 asserts the structural list's row
#: count exactly — two rows plus two per level and nothing else), and
#: giving one row a different height would make
#: :func:`_toc_entries_per_page`'s uniform-row division a second
#: text-layout primitive (G-2). A fixed point figure added to the pen's own
#: ``y`` before such a row is drawn is neither: the rows are still set with
#: :func:`_guide_face`/:func:`type_px` on the same :func:`page_frame`, and
#: the entries list, the row count and :func:`structural_toc_entry_count`
#: are all exactly what they were.
#:
#: **8.0 pt is the largest separation that leaves every storable trim its
#: own page number with the owner's own margin over the folio** — the figure
#: is measured, and that is the whole reason it is not a rounder number. On
#: the **shortest** trim a book can store and
#: :func:`~nonogram.admin.book_page_spec.book_page_spec` lays out (10.00 cm,
#: :data:`~nonogram.admin.book_page_spec.MIN_TRIM_CM`), a three-level book's
#: eight rows leave 187 px under the last one, of which the folio's own line
#: needs 49 (:func:`_draw_folio`, which omits the folio outright when its
#: caller's ``content_bottom`` leaves it less). Four gaps at 300 dpi must
#: therefore fit in 138 px:
#:
#: ===========  ======  ==================  =============================
#: constant     px      headroom (4 gaps)   folio (needs 49 px)
#: ===========  ======  ==================  =============================
#: 10.0 pt      42      19                  **dropped**
#: 9.0 pt       38      35                  **dropped**
#: 8.5 pt       35      47                  **dropped**, by 2 px
#: 8.2 pt       34      51                  ok — the largest that fits
#: **8.0 pt**   **33**  **55**              **ok, with 6 px to spare**
#: ===========  ======  ==================  =============================
#:
#: 8.0 rather than the maximal 8.2 by the owner's own choice: a margin over
#: the folio's line is worth more than the 0.2 pt of extra white, because
#: the next change that adds a row or a gap should fail on its own
#: arithmetic rather than silently un-number a page.
#:
#: **Both the table and the constant were read on Arial until CARD-221**,
#: which letters the interior in the packaged face on every host. On Arial
#: these same eight rows left 199 px and the owner chose **8.5 pt** (35 px,
#: 59 px of headroom, 10 px over the folio) against a maximum of 8.9; on
#: Pillow's own fallback face, which is what the deployed Linux image
#: printed, they left 27 px and the page went out unnumbered. The packaged
#: face sets a row 49 px tall against Arial's 48 and the title's line 258 px
#: against 254, which costs 12 px and left 8.5 pt exactly 2 px short at this
#: one trim — measured in CARD-221, where it was the one height of 381 that
#: failed. **8.0 pt is the owner's own rule re-measured on the face the book
#: is actually printed in** (owner decision, 2026-10-14, CARD-221 fix cycle
#: 1), not a new figure: the largest gap that fits, less a margin, which
#: comes to 6 px here where it came to 10 px there. The figure is
#: face-independent now, so the sweep asserts it unconditionally and there
#: is no gate and no expected failure left under it.
#:
#: This constant was **10 pt through Fix 1**, when only the three headings
#: were set off and three gaps of 42 px left 73 px — the fourth gap the
#: ``Solutions`` decision adds is what spent the margin. The superseded
#: rationale ("one :data:`TOC_ENTRY_PT`, a row's worth of white") is
#: recorded here only so it is not re-derived: the separation is now set by
#: the folio's reservation, not by an entry's set size. See
#: :func:`_toc_entries_per_page` for why the gaps are *proved* to fit
#: rather than charged to every row, and
#: ``tests/test_book_toc.py``'s
#: ``TestBookToc_GroupsAreSetOffFromWhatPrecedesThem`` for the sweep that
#: asserts the 55 px, and that no height fails, over all 381 heights KDP
#: admits.
TOC_GROUP_GAP_PT = 8.0

#: The label of the TOC's own last row (CARD-205): the SOLUTIONS divider that
#: opens the answer section, as the **table of contents** names it.
#:
#: Sentence case, and therefore deliberately *not*
#: :meth:`BookPDFGenerator.create_divider_page`'s own ``"SOLUTIONS"``
#: default. That string is the all-caps word printed on the divider page
#: itself — a display decision of that page, the same register its one-word
#: level dividers are set in — whereas a TOC row sits in a list beside
#: :data:`GUIDE_TITLE` ("How to Solve Nonograms") and the
#: :class:`~nonogram.difficulty.Tier` labels ("Easy"), every one of which is
#: sentence case. This is the owner's own sample wording (Google Doc
#: "Nonograms - Print layout", 2026-10-13: ``Solutions ............ 86``),
#: not a second name for that page: nothing reads this constant to draw the
#: divider, and the divider's own text is untouched by this card (G-3/G-5).
TOC_SOLUTIONS_LABEL = "Solutions"

#: The en dash a ``Puzzles N–M`` row's range is set with (CARD-205) — the
#: typographic dash for a span of numbers, and the same character the
#: owner's own sample uses. Named rather than inlined because
#: :func:`toc_range_label` and the tests that pin its output must agree on
#: the exact code point, which a literal in two places cannot guarantee by
#: eye (U+2013; the module already letters the wider em dash through
#: :func:`~nonogram.admin.book_answer_key.answer_caption`, so the one face
#: :func:`_guide_face` returns is known to carry this range — asserted glyph
#: by glyph since CARD-221 by ``tests/test_book_interior_face.py``'s
#: ``TestInteriorFace_ThePackagedFaceCoversWhatTheInteriorPrints``).
TOC_RANGE_DASH = "–"

#: The line the guide page's worked example solves (FR-041, AC-325): the clue
#: ``3 1`` on a row of six squares.
WORKED_EXAMPLE_CLUE: Tuple[int, ...] = (3, 1)
WORKED_EXAMPLE_LENGTH = 6

#: Page 1's opening line, printed under the title on the page's full form
#: (CARD-167; reworded verbatim from the owner's reference guide by
#: CARD-201). A module constant since CARD-169 so the Finalise screen's
#: preview reads the same text.
#:
#: **CARD-201 replaced this constant's text.** Until this card it explained
#: the clue-to-run rule in prose ("Each number beside a row..."); that
#: explanation did not disappear, it moved into :data:`GUIDE_BASIC_RULE_TEXT`
#: beside its own worked diagram. This constant is now the tutorial's single
#: opening sentence, read off
#: ``docs/guides/how_to_solve_nonograms_v2.pdf`` page 1 verbatim.
GUIDE_INTRO = "Read the clues. Fill what must be black. Mark what must be empty."

#: The line that introduces the worked example on the page's full form,
#: built from the clue and the row length it names (CARD-169).
GUIDE_EXAMPLE_HEADING = (
    "Worked example: the clue "
    + " ".join(str(run) for run in WORKED_EXAMPLE_CLUE)
    + f" on a row of {WORKED_EXAMPLE_LENGTH} squares."
)

#: Page 2's closing heading and sentence, printed on the page's full form
#: (CARD-167; a module constant since CARD-169).
#:
#: **CARD-201 replaced this constant's text.** The owner's reference guide's
#: own closing is CON-005's uniqueness guarantee stated for a reader rather
#: than for a requirements document — "Every puzzle in this book is checked
#: by the solver before publication. There is exactly one solution, and no
#: puzzle that requires guessing is included." — carried verbatim; "The
#: answers are at the back of the book." is this book's own practical
#: addition (CARD-167), kept because it is still true and still useful, and
#: not part of what the source document asks to be verbatim.
GUIDE_CLOSING_HEADING = "One solution. No guessing."
GUIDE_CLOSING = (
    "Every puzzle in this book is checked by the solver before publication. "
    "There is exactly one solution, and no puzzle that requires guessing is "
    "included. The answers are at the back of the book."
)


@dataclass(frozen=True)
class ExampleStep:
    """One step of the guide page's worked example (CARD-167).

    Attributes:
        caption: The sentence printed above the step's line when the page has
            room for the full text.
        label: The short caption printed instead when it does not.
        filled: The 0-based squares drawn filled at this step.
        crossed: The 0-based squares drawn crossed out (known empty).
    """

    caption: str
    label: str
    filled: frozenset
    crossed: frozenset


#: The worked example, from the bare clue to the finished line. Step 2 is the
#: overlap of the clue's two extreme placements; step 3 takes one fact from
#: the crossing column (square 1 is empty), after which the line has exactly
#: one arrangement.
WORKED_EXAMPLE_STEPS: Tuple[ExampleStep, ...] = (
    ExampleStep(
        "1. The clue 3 1 means a run of 3 filled squares, then at least one "
        "empty square, then a run of 1.",
        "1. The clue",
        frozenset(),
        frozenset(),
    ),
    ExampleStep(
        "2. Overlap: pushed left, the 3 covers squares 1-3; pushed right, "
        "2-4. Squares 2 and 3 are filled either way.",
        "2. Overlap",
        frozenset({1, 2}),
        frozenset(),
    ),
    ExampleStep(
        "3. Gap: the column crossing square 1 shows it is empty, so the 3 "
        "covers squares 2-4 and square 5 is the gap. Cross out 1 and 5.",
        "3. Gap",
        frozenset({1, 2, 3}),
        frozenset({0, 4}),
    ),
    ExampleStep(
        "4. Solved: the 1 fills square 6.",
        "4. Solved",
        frozenset({1, 2, 3, 5}),
        frozenset({0, 4}),
    ),
)


# ---------------------------------------------------------------------------
# The 2-page tutorial's new content (CARD-201)
# ---------------------------------------------------------------------------
#
# FR-041's own deferred clause ("the full 1-2 page tutorial") — content
# hand-transcribed from ``docs/guides/how_to_solve_nonograms_v2.pdf`` (2
# pages, committed alongside this card as a read-only provenance record; no
# code reads the PDF file itself at runtime, same pattern as every other
# hard-coded guide-page string). Every line diagram below is drawn through
# the generalised :func:`example_line_layout`/:func:`draw_example_line` pair
# (point 1 of this card's "Target"); the three cell-state icons, the
# 4-step assume/follow/breaks/proved pipeline and the difficulty box are the
# genuinely new drawing shapes the card's own analysis named — see
# :func:`guide_icon_layout`, :func:`_draw_pipeline_diagram` and
# :func:`_draw_difficulty_legend` (a bordered box until CARD-221 fix 1).


@dataclass(frozen=True)
class GuideCellState:
    """One of the three cell states the guide page teaches (CARD-201).

    Attributes:
        heading: "Unknown" / "Filled" / "Empty".
        caption: Its one-line gloss ("not decided yet", ...).
        filled: Whether the icon's bare cell is drawn filled.
        crossed: Whether it is drawn crossed. Never both.
    """

    heading: str
    caption: str
    filled: bool
    crossed: bool


#: "Use three cell states" (page 1, item 3): Unknown, Filled, Empty, each a
#: bare cell through :func:`guide_icon_layout` (CARD-201).
GUIDE_CELL_STATES_HEADING = "Use three cell states"
GUIDE_CELL_STATES: Tuple[GuideCellState, ...] = (
    GuideCellState("Unknown", "not decided yet", filled=False, crossed=False),
    GuideCellState("Filled", "definitely black", filled=True, crossed=False),
    GuideCellState("Empty", "definitely white", filled=False, crossed=True),
)

#: "The basic rule" (page 1, item 2): a clue is a run of consecutive filled
#: cells, in order, with at least one empty cell between runs — worked with
#: "3 2 1" on the minimal 8-cell line that forces a unique arrangement
#: (3 + 1 + 2 + 1 + 1 = 8), a different clue/length pair from the original
#: worked example's "3 1" on 6 (G-1: that example is unchanged, not reused
#: here).
GUIDE_BASIC_RULE_HEADING = "The basic rule"
GUIDE_BASIC_RULE_TEXT = (
    "Each clue describes a run of consecutive filled cells. If a line has "
    "more than one number, the runs appear in that order, with at least one "
    "empty cell between them."
)
GUIDE_BASIC_RULE_CLUE: Tuple[int, ...] = (3, 2, 1)
GUIDE_BASIC_RULE_LENGTH = 8
GUIDE_BASIC_RULE_FILLED: frozenset = frozenset({0, 1, 2, 4, 5, 7})
GUIDE_BASIC_RULE_CROSSED: frozenset = frozenset({3, 6})
GUIDE_BASIC_RULE_CAPTION = "3 2 1 means 3 filled, gap, 2 filled, gap, 1 filled."


@dataclass(frozen=True)
class GuideRow:
    """One drawn line inside a :class:`GuideTechnique`'s diagram (CARD-201).

    Attributes:
        filled: The 0-based squares drawn filled.
        crossed: The 0-based squares drawn crossed out.
        note: A short label printed beside this row alone ("certain",
            "Compare"), or ``""`` for none.
    """

    filled: frozenset
    crossed: frozenset
    note: str = ""


@dataclass(frozen=True)
class GuideTechnique:
    """One numbered technique on the guide's 2-page tutorial (CARD-201).

    Every row of :attr:`rows` is drawn on the same ``(clue, length)`` line
    through :func:`example_line_layout`/:func:`draw_example_line`, stacked top
    to bottom — one row for a technique with a single diagram (CARD-201's
    "complete lines"), several for one that compares positions ("squeeze
    from both ends", "keep what every arrangement agrees on").

    Attributes:
        heading: The numbered heading, e.g. "1. Complete lines" — also the
            short label printed in the page's labels-only fallback form,
            since every heading here already is one line.
        caption: The explanation paragraph, full form only.
        clue: The row clue every one of ``rows`` is drawn with.
        length: The row's length in cells.
        rows: One or more :class:`GuideRow`, drawn stacked.
    """

    heading: str
    caption: str
    clue: Tuple[int, ...]
    length: int
    rows: Tuple[GuideRow, ...]


#: "Start with certainty" (page 1, item 4): three techniques, each with one
#: worked diagram (CARD-201).
GUIDE_CERTAINTY_HEADING = "Start with certainty"
GUIDE_TECHNIQUES_1: Tuple[GuideTechnique, ...] = (
    GuideTechnique(
        heading="1. Complete lines",
        caption="If the clue fills the whole line, every cell is known immediately.",
        clue=(10,),
        length=10,
        rows=(GuideRow(frozenset(range(10)), frozenset()),),
    ),
    GuideTechnique(
        heading="2. Squeeze from both ends",
        caption=(
            "For a long run, place it as far left as possible and then as "
            "far right as possible. Cells covered both times must be filled."
        ),
        clue=(8,),
        length=10,
        rows=(
            GuideRow(frozenset(range(8)), frozenset()),
            GuideRow(frozenset(range(2, 10)), frozenset()),
            GuideRow(frozenset(range(2, 8)), frozenset(), note="certain"),
        ),
    ),
    GuideTechnique(
        heading="3. Mark spaces around a completed block",
        caption=(
            "Once a run is complete, cells immediately beside it must be "
            "empty. Marking empties often unlocks the next deduction."
        ),
        clue=(3,),
        length=8,
        rows=(GuideRow(frozenset({2, 3, 4}), frozenset({1, 5})),),
    ),
)

#: Page 1's closing callout (item 5): text only, no diagram (CARD-201).
GUIDE_SWITCHING_HEADING = "Keep switching between rows and columns"
GUIDE_SWITCHING_TEXT = (
    "Every confirmed black or empty cell gives new information in the "
    "crossing line. Recheck both directions after every discovery."
)

#: Page 2's title (CARD-201) — title-cased like the shipped :data:`GUIDE_TITLE`
#: rather than the source PDF's all-caps heading (see the matching owner-
#: decision note on :data:`GUIDE_TITLE` in the card's Worktree notes).
GUIDE2_TITLE = "When the Puzzle Gets Harder"
GUIDE2_INTRO = "Use stronger deductions only when the simpler ones stop producing new cells."

#: Page 2's first two numbered techniques (item 2): each with one worked
#: diagram, the same :class:`GuideTechnique` shape as page 1's (CARD-201).
#: The third technique, "Assume, and watch it break", is not a line diagram
#: (see :data:`GUIDE_ASSUME_STEPS` below) and so is not one of these.
GUIDE_TECHNIQUES_2: Tuple[GuideTechnique, ...] = (
    GuideTechnique(
        heading="1. Use what you already know",
        caption=(
            "Known empty cells split a line into smaller regions. If a "
            "remaining run cannot fit inside a region, those cells can be "
            "ruled out."
        ),
        clue=(2, 3),
        length=10,
        rows=(
            GuideRow(frozenset(), frozenset({3, 5})),
            GuideRow(
                frozenset(),
                frozenset({3, 4, 5}),
                note="The one-cell region cannot hold 2 or 3.",
            ),
        ),
    ),
    GuideTechnique(
        heading="2. Keep what every arrangement agrees on",
        caption=(
            "Consider the legal ways the clue can still fit the line. A "
            "cell that is filled in every surviving arrangement is certain; "
            "a cell empty in every arrangement is certainly empty."
        ),
        clue=(3,),
        length=5,
        # Review cycle 1, F-1 (gating): the previous version of this example
        # used length=10 and showed only 3 of its 8 legal placements (starts
        # 0, 1, 5), concluding cell 4 was "certainly empty in every
        # arrangement" — false, since starts 2, 3 and 4 (not shown) all cover
        # cell 4. A run of 3 on a 10-cell line has NO invariant cell at all:
        # every index 0..9 is reachable by some start, and no index is
        # covered by all 8 starts (each cell is covered by at most 3 of the
        # 8). Fixed by shrinking the line to 5 cells, where a run of 3 has
        # exactly `length - clue + 1 = 3` legal placements — so the three
        # rows below are literally ALL of them, not a chosen subset:
        #   start 0 -> {0, 1, 2}
        #   start 1 -> {1, 2, 3}
        #   start 2 -> {2, 3, 4}
        # Cell 2 is the only index covered by every one of the 3 starts (0
        # only by start 0; 1 by starts 0-1; 3 by starts 1-2; 4 only by start
        # 2) — filled in every surviving arrangement, so it is genuinely
        # "certain". Verified against literally all legal placements (not
        # just the three shown) by
        # tests/test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyBox::test_the_arrangement_comparison_is_verified_against_every_legal_placement,
        # which brute-forces every start for this clue/length independently
        # of this constant.
        #
        # "Compare" (not "compare"): an x-height-only word has no capital or
        # ascender for the cap-height-to-baseline measurement CON-020's
        # floor is checked by (this suite's own convention since CARD-149),
        # which undercounts its size by nearly a quarter even though it is
        # drawn at the same 11 pt as every other line here — the same class
        # of defect CARD-167 fixed by rewording its own copy. Measured while
        # building CARD-201; unrelated to the F-1 content fix above.
        rows=(
            GuideRow(frozenset({0, 1, 2}), frozenset()),
            GuideRow(frozenset({1, 2, 3}), frozenset()),
            GuideRow(frozenset({2, 3, 4}), frozenset()),
            GuideRow(frozenset({2}), frozenset(), note="Compare"),
        ),
    ),
)


#: The four icon kinds :func:`_draw_pipeline_diagram` knows how to draw —
#: see :class:`GuidePipelineStep`.
PIPELINE_ICON_SQUARE = "square"
PIPELINE_ICON_DOTS = "dots"
PIPELINE_ICON_BANG = "bang"
PIPELINE_ICON_CROSS = "cross"


@dataclass(frozen=True)
class GuidePipelineStep:
    """One box of the "assume, and watch it break" pipeline (CARD-201).

    Attributes:
        label: The box's word ("ASSUME", "FOLLOW", "BREAKS", "PROVED").
        icon: One of the ``PIPELINE_ICON_*`` kinds, drawn under the word by
            :func:`_draw_pipeline_diagram`. A **kind**, not a glyph: the
            source PDF draws ASSUME as a filled square and PROVED as a cross,
            the same filled-square and crossed-square ink this page already
            draws for the "Filled"/"Empty" cell states
            (:data:`GUIDE_CELL_STATES`), so those two are drawn with
            :class:`ImageDraw`'s own rectangle/line primitives rather than a
            Unicode glyph a fallback face might not carry; FOLLOW's "..." and
            BREAKS's "!" are plain ASCII, safe on any face including the
            no-Arial fallback (``without_arial`` in
            ``tests/test_book_interior_type_floor.py``). "No new iconography
            invented beyond what the source PDF already shows" (this card's
            own "Target") — these are the same four marks, drawn in the
            page's established visual language instead of its font's.
    """

    label: str
    icon: str


#: Page 2's third technique (item 2c): not a puzzle-line diagram — a simple
#: 4-box sequence with an arrow between each (CARD-201). Drawn by
#: :func:`_draw_pipeline_diagram`.
GUIDE_ASSUME_HEADING = "3. Assume, and watch it break"
GUIDE_ASSUME_TEXT = (
    "If everything stalls, temporarily treat one unsettled cell as filled "
    "and follow the consequences through its row and column. If a clue "
    "becomes impossible, the assumption was wrong."
)
GUIDE_ASSUME_STEPS: Tuple[GuidePipelineStep, ...] = (
    GuidePipelineStep("ASSUME", PIPELINE_ICON_SQUARE),
    GuidePipelineStep("FOLLOW", PIPELINE_ICON_DOTS),
    GuidePipelineStep("BREAKS", PIPELINE_ICON_BANG),
    GuidePipelineStep("PROVED", PIPELINE_ICON_CROSS),
)
GUIDE_ASSUME_CLOSING = (
    "This is not guessing: erase the temporary trial and keep only what the "
    "contradiction proves."
)


@dataclass(frozen=True)
class DifficultyLabel:
    """One column of the difficulty legend (CARD-201).

    Attributes:
        name: "EASY" / "MEDIUM" / "HARD" — ADR-0031's three tiers. The whole
            of what the **printed** guide page says about the labels since
            CARD-221 fix 1.
        text: Its one-sentence gloss, carried verbatim from the source PDF
            (CARD-201's "Target" point 3: "this box alone is the doc's
            entire description of what our difficulty levels are about").
            **No longer printed on the guide page** — see
            :data:`GUIDE_DIFFICULTY_LABELS`. Still shown by the Finalise
            screen's own preview of the page
            (``templates/book_finalize.html``), and still carried here as
            the text CARD-229 places in the guide's key strip, which is the
            owner's reason for choosing this block over any other on the
            page.
    """

    name: str
    text: str


#: Page 2, item 3: the difficulty legend, drawn by
#: :func:`_draw_difficulty_legend` (CARD-201).
#:
#: **Its three sentences stopped being printed in CARD-221 fix 1** (owner
#: decision, 2026-10-14). Lettering the interior in the packaged face made
#: page 2's captions form 4 px too tall for the Book 1 sheet, which dropped
#: the page a whole fallback level and cost the reader the worked example's
#: four step explanations and both technique notes as well. Dropping these
#: three sentences buys 234 px against that 4 px deficit, so everything else
#: on the page stays — and they are the one block with a successor already
#: carded: CARD-229 moves the difficulty legend into the guide's key strip.
#: The :attr:`DifficultyLabel.name`\ s still print, and the ruled box that
#: held the sentences went with them (see :func:`_draw_difficulty_legend`).
#:
#: ``text`` is therefore data this module keeps and no longer prints. The
#: Finalise screen's preview still shows it, which is a divergence between
#: that screen and the page it previews: flagged for the owner and for
#: CARD-229 in CARD-221's Worktree notes rather than fixed here, because
#: that screen is out of this card's scope (G-6) and CARD-229 rebuilds the
#: block on both surfaces.
GUIDE_DIFFICULTY_HEADING = "What the difficulty labels mean"
GUIDE_DIFFICULTY_LABELS: Tuple[DifficultyLabel, ...] = (
    DifficultyLabel(
        "EASY",
        "Squeezing and direct deductions are enough from start to finish.",
    ),
    DifficultyLabel(
        "MEDIUM",
        "Needs deeper line logic and may need contradiction for part of "
        "the grid.",
    ),
    DifficultyLabel(
        "HARD",
        "Contradiction reasoning is needed through much of the grid.",
    ),
)


def type_px(points: float, dpi: int) -> int:
    """``points`` of type as the whole device pixels a page at ``dpi`` needs.

    The one place this module turns a type size into pixels. Pillow's
    ``ImageFont.truetype`` takes its size in pixels — it is the em square in
    device pixels, not a point size — so every size this module states in
    points passes through here on its way to a font.

    Args:
        points: A type size or a leading, in points (1/72 in).
        dpi: The resolution of the surface the type is drawn on, which for
            every page of a book is
            :attr:`BookPDFGenerator.dpi`.

    Raises:
        ValueError: ``dpi`` is not positive, so the conversion has no meaning,
            or ``points`` is negative.
    """
    if dpi <= 0:
        raise ValueError(f"a page's resolution is positive, got {dpi}")
    if points < 0:
        raise ValueError(f"type has a non-negative size, got {points}")
    return round(points * dpi / POINTS_PER_INCH)


def _guide_face(size: int) -> ImageFont.FreeTypeFont:
    """The face every reader-facing interior page letters in, at ``size`` px.

    The packaged DejaVu Sans — :func:`_band_font_bytes`, the one font this
    project ships (ADR-0006/R1, package data rather than a dependency) and the
    face the band and the folio were already set in. The guide pages, the
    dividers and the table of contents letter through here, so **every
    measurement the interior makes is a function of this repository's own
    font data and of the installed Pillow/FreeType, and of nothing the host's
    font configuration offers** (CARD-221).

    That second clause is the honest limit of what the swap bought, and it
    is deliberate wording (review cycle 1, F-005). The face is now the
    repository's; the rasteriser is not. ``pyproject.toml`` floors Pillow at
    ``>=10.0`` with no ceiling, the metrics this module reads come straight
    off ``getmetrics()``, and one pixel of ascent is exactly the lever that
    separated 42 TOC rows from 41 when the face was the host's. So a
    FreeType bump can still move a page count where a missing Arial no
    longer can. What would catch it is the baseline: every interior page is
    compared digest-for-digest against ``book_baseline_card221.json`` with
    no face gate left to skip it
    (``tests/test_book_pdf_memory.py``'s ``TestBookPdfMemory_PagesAreUnchanged``),
    so a rasteriser that redraws a glyph reds the suite on the machine that
    bumped it rather than reaching a printed book. Bounding Pillow, or
    recording the metrics themselves, is an ADR-0006/R1 question and not
    this function's to answer.

    **It asked the host for Arial by path until CARD-221**, with Pillow's own
    built-in face as a sized fallback. That made the interior's row geometry
    host-dependent while the folio's own reservation (:func:`_band_font`) was
    not, so the same book could be finalised here and generated on the
    deployed Linux image and disagree about its page count — and therefore
    about the printed KDP gutter band the count selects. Measured on
    2026-10-14 at Book 1's trim: a TOC page held 42 rows on Arial and 40 on
    the fallback, and ``main``'s own suite showed it as 10 off-host failures
    in ``tests/test_book_finalise_gutter.py``, every one a page count off by
    exactly one.

    **No escapes, and none needed** (the card's step 1): the interior's whole
    character repertoire is ASCII plus ``·`` (U+00B7, :data:`BAND_SEPARATOR`),
    ``—`` (U+2014, the answer caption's dash), ``–`` (U+2013,
    :data:`TOC_RANGE_DASH`) and ``…`` (U+2026, :func:`_clipped_to`'s
    ellipsis), and DejaVu Sans covers every one of them — asserted glyph by
    glyph, against this file's own strings, by
    ``tests/test_book_interior_face.py``'s
    ``TestInteriorFace_ThePackagedFaceCoversWhatTheInteriorPrints``. A silent
    ``try`` here would be a second face waiting to be selected by accident,
    which is the defect this function was changed to remove.

    Uncached deliberately, unlike :func:`_band_font`: the guide page's title
    is fitted by asking for one pixel less at a time, so a page probes many
    sizes and a small LRU would thrash on exactly the call that needs it. The
    font *bytes* are cached (:func:`_band_font_bytes`), which is where the
    cost is; every call returns a fresh :class:`ImageFont.FreeTypeFont`, as
    the Arial-by-path call it replaces also did.
    """
    return ImageFont.truetype(BytesIO(_band_font_bytes()), size=size)


def band_identity(puzzle_number: int, stored_tier: object) -> str:
    """The band line of one book puzzle: ``"Puzzle 12 · Easy"`` (ADR-0037/R1).

    The whole of what a puzzle page's band says. ``N`` is the puzzle's 1-based
    position in the **print** order, which is the number its answer-key entry
    carries too, so the two can be matched by eye; ``Tier`` is the solver's
    own grade, never anything derived from the grid's size (FR-009).

    ``stored_tier`` is whatever the puzzle's row holds, in any of the spellings
    that reach it — the enum value a generated row stores (``"easy"``), the
    display label an older or hand-entered row carries (``"Easy"``), or
    ADR-0031/R3's retired ``"guess"``, which reads back as Hard without being
    rewritten. It is normalised through
    :func:`nonogram.difficulty.tier_of_record`, the one reader of stored tier
    text, rather than printed as it is stored: a band reading "Puzzle 12 ·
    easy" would be the same counting bug that function exists to prevent,
    wearing a typography bug's clothes.

    **A row with no tier of record prints "Puzzle 12" and stops.** ``None`` out
    of ``tier_of_record`` means the text on the row is not a tier at all — a
    missing column, a blank, a word from some retired vocabulary — and there
    is nothing true to print after the dot. The three honest options are to
    print the raw text (which would put an unvetted string from the database on
    a printed page and spell it however it happens to be spelled), to invent a
    label such as "Unrated" (a fourth tier on the page, which ADR-0031 has
    exactly three of), or to say only what is known. This says only what is
    known: the number still identifies the puzzle and still matches the answer
    key, and the missing grade is visible as an absence to whoever proofs the
    book rather than dressed up as one.

    Raises:
        ValueError: ``puzzle_number`` is not a print position (below 1).
    """
    if puzzle_number < 1:
        raise ValueError(f"puzzles are numbered from 1, got {puzzle_number}")
    tier = tier_of_record(stored_tier)
    if tier is None:
        return f"Puzzle {puzzle_number}"
    return f"Puzzle {puzzle_number}{BAND_SEPARATOR}{tier.label}"


def tier_breakdown(puzzles: List[Dict[str, Any]]) -> "Counter[Tier]":
    """Count a book's puzzles by tier, however their rows spell it.

    One implementation for both places a book's difficulty breakdown is built —
    the PDF guide page here and the finalize screen in ``app.py`` — because two
    copies of it is how the defect below survived in both at once.

    Every count goes through :func:`nonogram.difficulty.tier_of_record` rather
    than comparing against a display label. A row written by the generation
    pipeline stores the enum *value* (``"easy"``), so the previous
    ``== "Easy"`` matched none of them: every generated book reported a 0/0/0
    breakdown, which reads as an empty book rather than as a broken reader
    (CARD-076 review F-002). Rows whose tier is missing or unrecognised are
    counted in no tier at all, so the totals never exceed the puzzle count.

    Returns a :class:`collections.Counter`, so every member of :class:`Tier`
    can be indexed without a ``get`` and reads
    0 when the book has none.
    """
    return Counter(
        tier
        for tier in (
            tier_of_record(puzzle.get("difficulty_tier")) for puzzle in puzzles
        )
        if tier is not None
    )


def _stored_tier(puzzle: Any) -> Optional[Tier]:
    """One book row's level, however it spells its tier — ``None`` when it states none.

    :func:`~nonogram.difficulty.tier_of_record` is the one reader of stored
    tier text everywhere in this module (the band, the pairing walk, the answer
    key), so ``"easy"``, ``"Easy"`` and ADR-0031/R3's retired ``"guess"`` are
    the tiers they mean. The row is read defensively — a member so malformed it
    is not even a mapping has no tier, and is dropped a few lines later by the
    payload pass rather than raising here, where the export is still deciding
    what order to print in.
    """
    if not hasattr(puzzle, "get"):
        return None
    return tier_of_record(puzzle.get("difficulty_tier"))


def print_order(puzzles: List[Any]) -> List[Any]:
    """``puzzles`` in the order the book prints them: easy, medium, hard (INV-009).

    The grouping half of FR-041, decided **here, at PDF time**, over whatever
    order the book's rows arrive in. Nothing is stored and nothing is rewritten
    (G-1, Increment 15's rollback story): a book whose stored arrangement
    predates INV-009 — medium, easy, hard, easy — prints E1, E2, M1, H1 and
    still reads back mixed from the database (AC-260). Only a move writes a
    grouped order back, and that is ``book_manager``'s (CARD-126).

    It is ``book_plan.book_level_order`` — **the one grouping** the arrange
    screen, the adds and the moves all use — applied to the rows' positions
    rather than to their ids, so it holds for a list whose members share an id,
    carry none, or are not rows at all. Two consequences come with that
    function and are the reason it is reused rather than rewritten here: the
    sort is **stable** and keyed on the level alone, so the owner's arrangement
    inside a level is never re-sorted, and it is **idempotent**, so a book that
    is already grouped comes back in exactly the order it went in.

    Rows with no readable tier (:func:`_stored_tier`) rank after all three
    levels, in their own relative order. They are never dropped: the print
    order is a permutation of the book's membership, always.
    """
    ranked = list(puzzles)
    return [
        ranked[index]
        for index in book_level_order(
            range(len(ranked)), lambda index: _stored_tier(ranked[index])
        )
    ]


# ---------------------------------------------------------------------------
# Drawing a page COMP-007 measured but draws no call for (FR-040, ADR-0036/R2)
# ---------------------------------------------------------------------------

#: How much of a slot's usable width a band's line may occupy, and how far the
#: type may shrink to fit it — COMP-007's own header numbers
#: (``pdf._HEADER_WIDTH_RATIO``, ``pdf._MIN_HEADER_FONT_RATIO``), restated here
#: because they are private to that module. They never bite on a band this
#: module writes: "Puzzle 120 · Medium" is about a tenth of a book page's
#: usable width at the 5 mm the band is set in. They are kept so that a band is
#: fitted by the same rule wherever it is drawn, rather than running off the
#: page in the one case nobody measured — and they are pinned equal to
#: COMP-007's pair by
#: ``test_a_two_up_band_is_fitted_by_the_exports_own_header_ratios``
#: (``tests/test_book_pdf_two_up.py``, where importing those private names is
#: legal), so a retuning on that side cannot leave this side silently behind.
_BAND_WIDTH_RATIO = 0.9
_MIN_BAND_FONT_RATIO = 1 / 3

#: CARD-197's light-gray gridline tone, for the full-page solved layout's
#: mark between two grid-adjacent filled cells (owner's Google Doc, "Nonograms
#: - Print layout1", 2026-10-07). A literal ``(v, v, v)`` RGB tuple, never a
#: named colour (G-5): grepped the whole ``export/`` and ``admin/`` print path
#: and the CSS tokens for an existing gray convention first — there is none to
#: reuse. ``(160, 160, 160)`` is roughly equidistant from black (0) and white
#: (255) in printed density, survives the book's own ``(v, v, v) -> v``
#: RGB-to-``"L"`` conversion (CARD-147's B&W interior mode) as an exact
#: grayscale value by construction, and is distinguishable from both ends by
#: an exact pixel comparison. The owner confirms this specific tone on the
#: render before CARD-198 wires it into the real answer key (see Worktree
#: notes).
_SOLVED_GRID_GRAY = (160, 160, 160)


@lru_cache(maxsize=1)
def _band_font_bytes() -> bytes:
    """The packaged DejaVu Sans, read once (ADR-0006/R1, ADR-0006/DEC-027).

    The same face, addressed the same way as :mod:`nonogram.export.pdf`
    addresses it for its own header — package *data*, named by that module's
    public :data:`~nonogram.export.pdf.FONT_PACKAGE` and
    :data:`~nonogram.export.pdf.FONT_RESOURCE` and read through
    :mod:`importlib.resources`, not a filesystem path and not a system font.
    A band reads "Puzzle 12 · Easy", and U+00B7 is not in Pillow's embedded
    ASCII default face — a band set in that would print a ``.notdef`` box
    between the number and the tier.
    """
    return resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()


@lru_cache(maxsize=8)
def _band_font(size: int) -> ImageFont.FreeTypeFont:
    """The packaged face at ``size`` device pixels. Cached: a book asks for one
    or two sizes across every page it prints — plus the generated title
    cover's own :data:`COVER_TITLE_PX`, which letters through here too since
    CARD-234 (:func:`_cover_title_face`)."""
    return ImageFont.truetype(BytesIO(_band_font_bytes()), size=size)


def _stroke_drawing(draw: ImageDraw.ImageDraw, slot: Layout) -> None:
    """Stroke every ruled line of ``slot``, thin ones first, then its frame (FR-040).

    Every number here — each line's axis position, its two ends and its width,
    and the frame's four boundaries — is COMP-007's, read off the
    :class:`~nonogram.export.layout.Layout` the pair-aware call placed. Nothing
    is measured, rounded or offset.

    Thin rules first and the every-5th and border rules last, so that where a
    heavy line crosses a thin one the heavy line survives the overlap and stays
    visually continuous — the same order, and the same reason, as the PNG
    renderer's. It is reimplemented rather than imported: ``png._draw_grid`` is
    private, and ``export/`` exposes no call that draws a layout it is handed.

    **The frame, last of all (CARD-146).** A two-up page used to stop at the
    grid: this function was written before CARD-144 gave a book page's drawing
    its frame, and a slot's :attr:`~nonogram.export.layout.Layout.frame` — which
    :func:`~nonogram.export.layout.compute_pair_layout` computes for *both*
    slots, exactly as it does for the single page each would otherwise have been
    — was simply never stroked. Interior page 3 of the baseline book, the two-up
    page, was byte-identical to its pre-frame recording while the single-puzzle
    pages moved; that was the gap, and this is where it closes. A pair now reads
    as two framed puzzles rather than two bare grids.

    The four sides are stroked exactly as
    :func:`~nonogram.export.png._draw_frame` strokes a single page's — the same
    pure :data:`INK`, the same :attr:`~nonogram.export.layout.PuzzleFrame.width`
    (:attr:`Layout.thick_rule`, the heavy rule, no new weight — ADR-0037/R2),
    each side **on** its boundary coordinate so Pillow centres it there and half
    a heavy rule hangs outside the box, as the grid's own outer border already
    does. Nothing is re-derived: this card consumes ``slot.frame`` and places
    nothing (ADR-0036/R2, G-3). Two of the four sides — right and bottom — land
    on the grid's outer border the loop above has already stroked at the same
    width on the same coordinates, so re-stroking them puts identical black in
    identical pixels; the ink a frame *adds* is its left and top sides, the
    outer edges of the two clue gutters.

    Drawn after the grid, and for the same reason the grid draws its heavy rules
    last: where the frame crosses a thin rule, the heavy line is the one that
    survives the overlap and stays continuous. ``slot.frame`` is ``None`` on an
    unframed sheet — which a two-up slot never is, since a pair is a placed
    page (:class:`~nonogram.export.layout.PairLayout` refuses anything else)
    and a placed page is framed, so from *that* caller the guard was a total
    function's, not a branch it could take.

    **No longer true of every caller (CARD-201).** :func:`guide_icon_layout`
    deliberately drops its frame (a bare cell icon, no clue gutter to frame)
    and still draws through :func:`draw_example_line`, which calls this
    function unconditionally — so the guard below is live, taken every time
    the guide page's three cell-state icons are drawn, not dead code.
    """
    oriented: List[Tuple[Any, bool]] = [
        *((line, True) for line in slot.vertical_lines),
        *((line, False) for line in slot.horizontal_lines),
    ]
    for line, vertical in sorted(oriented, key=lambda pair: pair[0].major):
        if vertical:
            ends = [(line.position, line.start), (line.position, line.end)]
        else:
            ends = [(line.start, line.position), (line.end, line.position)]
        draw.line(ends, fill=INK, width=line.width)

    frame = slot.frame
    if frame is None:  # guide_icon_layout's bare cell icon (CARD-201) — live, not dead
        return
    left, top, right, bottom = frame.left, frame.top, frame.right, frame.bottom
    for side in (
        ((left, top), (right, top)),
        ((left, bottom), (right, bottom)),
        ((left, top), (left, bottom)),
        ((right, top), (right, bottom)),
    ):
        draw.line(list(side), fill=INK, width=frame.width)


def _write_clues(draw: ImageDraw.ImageDraw, slot: Layout) -> None:
    """Write ``slot``'s clue numbers, each centred on the point COMP-007 placed it.

    ``anchor="mm"`` centres the glyph box on that point in both axes — the one
    placement rule that does not depend on a face's ascent or digit width — and
    the size is :attr:`Layout.clue_font_size`, which the layout derived from the
    shared cell. Pillow's embedded default face, at an explicit size, exactly as
    a single puzzle page's clues are set: they are ASCII decimal digits, so the
    coverage that forces the band onto the packaged face does not arise.
    """
    font = ImageFont.load_default(size=slot.clue_font_size)
    for entry in slot.clue_entries:
        draw.text(
            (entry.center_x, entry.center_y),
            str(entry.value),
            font=font,
            fill=INK,
            anchor="mm",
        )


def _set_band(draw: ImageDraw.ImageDraw, band: HeaderBand, text: str, room: int) -> None:
    """Set ``text`` centred in ``band``, shrunk if it would not fit ``room``.

    The band's strip, its centre and its type size are
    :func:`~nonogram.export.layout.header_band`'s answer for the slot; ``room``
    is the slot's usable width, the same measurement the export fits a header
    against. One piece, so there is no separator to stroke: a puzzle page's
    header is the identity line alone (:meth:`BookPDFGenerator._banded` clears
    the picture's name), and a two-up slot is a puzzle page.

    Drawn from the line's left edge with ``anchor="lm"`` at
    ``center_x - width / 2`` rather than with a centred anchor, because that is
    what :func:`~nonogram.export.pdf.render_pages` does for a one-piece header:
    the two must put the same ink in the same pixels, or the upper slot's band
    and the band of the same puzzle printed alone would differ.

    **Two of the export's three fitting steps, not three.** ``pdf._draw_header``
    measures, shrinks once to :data:`_MIN_BAND_FONT_RATIO` of the band's type
    size, and then — if the line is *still* too wide at that floor — elides its
    first piece. The first two steps are above; the third is deliberately not
    reproduced, and cannot be reached from here: the export elides the first of
    several pieces because only a picture's name is long enough to need it
    (:meth:`BookPDFGenerator._banded`), while a band is the one piece
    :func:`band_identity` composes — "Puzzle 120 · Medium", about a tenth of a
    book page's usable width at the 5 mm the band is set in, with the number
    bounded by the book's membership and the tier by ADR-0031's three labels.
    There is nothing here that could grow into the case the third step exists
    for, and eliding the only piece would cut the number the answer key is
    looked up by. Were a band ever to carry a second, unbounded piece, that
    step would have to come with it.
    """
    if band.height <= 0 or not text:
        return
    size = band.font_size
    font = _band_font(size)
    width = font.getlength(text)
    usable = room * _BAND_WIDTH_RATIO
    if width > usable:
        size = max(round(band.font_size * _MIN_BAND_FONT_RATIO), int(size * usable / width))
        font = _band_font(size)
        width = font.getlength(text)
    draw.text(
        (band.center_x - width / 2, band.center_y),
        text,
        font=font,
        fill=INK,
        anchor="lm",
    )


def _draw_difficulty_dots(
    draw: ImageDraw.ImageDraw,
    stored_tier: object,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> Optional[DifficultyDots]:
    """Draw ``stored_tier`` as a row of dots inside a box (CARD-228).

    **The only place in this package that puts a circle on a page**, and the
    one call every difficulty glyph the book prints goes through: the puzzle
    page's band (CARD-207), the guide's key strip (CARD-229), a section opener
    (CARD-231) and a solution tile's header (CARD-233). That is asserted
    structurally rather than promised — ``tests/test_book_difficulty_dots.py``
    walks ``src/nonogram/**/*.py`` with ``ast`` and fails on a second call to
    any Pillow method whose geometry is an ellipse, the way
    ``tests/test_cli.py`` walks the same tree for a lateral import. Four cards
    drawing four slightly different dots is the defect this function exists to
    make impossible, so "readers learn them here once" can be true.

    One stroke for the row, filled or outlined (:attr:`DifficultyDots.stroke`),
    so the solid dots and the outlined ones share a silhouette and the glyph
    reads as *n of three* rather than as two kinds of mark.

    The count and the order are :data:`~nonogram.admin.book_plan.TIERS` and
    nothing else — ``len(TIERS)`` dots, the tier's own index in it as the rank.
    There is deliberately no second ladder, not even a ``3``: a tuple of tier
    names on its own literals is exactly how ``strategy_counter.py`` grew a
    second classifier (CARD-155), and a glyph whose rank disagreed with the
    panel's own tier order would be wrong on paper, where it cannot be fixed.

    The tier is **read, never written** (ADR-0033/R1): ``stored_tier`` is
    whatever the puzzle's row holds, normalised through
    :func:`nonogram.difficulty.tier_of_record` — the one reader of stored tier
    text — exactly as :func:`band_identity` reads it for the word beside these
    dots. Nothing here assigns, defaults or re-grades a tier.

    **A row with no tier of record draws nothing at all.** Not three outlined
    dots: an empty three-dot frame is the same mark an "easiest of three
    tiers" glyph would be if the first dot failed to ink, and a reader has no
    way to tell "we do not know" from "the easy one" on a printed page. The
    absence is visible as an absence to whoever proofs the book, which is the
    same call :func:`band_identity` makes for the missing word.

    The dots are **not text**, so CON-020's 10 pt floor does not reach them
    (guardrail G-2) — and cannot be evaded through them either: this function
    makes no ``draw.text`` call, which
    ``tests/test_book_interior_type_floor.py`` pins. The *word* beside them is
    text and is held to the floor by its own caller.

    Args:
        draw: The page's own draw object — the existing drawing primitive
            (guardrail G-1); no new surface, image or canvas is made here.
        stored_tier: The puzzle's tier as its row spells it, in any of the
            spellings :func:`~nonogram.difficulty.tier_of_record` reads.
        left: The box the glyph may use, left edge inclusive.
        top: Its top edge, inclusive.
        right: Its right edge, inclusive.
        bottom: Its bottom edge, inclusive.

    Returns:
        The geometry actually drawn — so a caller can set its word beside the
        ink rather than beside the box — or ``None`` when nothing was drawn,
        either because the row carries no tier or because
        :func:`~nonogram.export.layout.difficulty_dots` declined the box as
        too small for a legible dot.
    """
    tier = tier_of_record(stored_tier)
    if tier is None or tier not in TIERS:
        return None
    dots = difficulty_dots(
        left,
        top,
        right,
        bottom,
        filled=TIERS.index(tier) + 1,
        total=len(TIERS),
    )
    if dots is None:
        return None
    for index, dot in enumerate(dots.dots):
        draw.ellipse(
            dot,
            fill=INK if dots.is_filled(index) else BACKGROUND,
            outline=INK,
            width=dots.stroke,
        )
    return dots


#: CARD-204's placeholder QR icon: a plain alternating checkerboard, never a
#: real QR module pattern — see :func:`_draw_qr_placeholder`'s own docstring.
#: Reimplemented from :mod:`nonogram.export.png`'s identical helper rather
#: than imported (the native-reimplementation convention this module already
#: follows for :func:`_stroke_drawing`/:func:`_write_clues`: ``export/``
#: exposes no call that draws onto a page it is handed, CARD-146).
_QR_PLACEHOLDER_MODULES = 5


def _draw_qr_placeholder(draw: ImageDraw.ImageDraw, icon: QrSlot) -> None:
    """Draw CARD-204's placeholder QR icon inside ``icon``'s box.

    **Deliberately not a real QR code (owner's confirmed option 2(b)).** A
    bordered square around a plain alternating checkerboard — no finder
    squares, no real module data, "a generic grid-of-squares glyph, never
    claiming to scan". No URL, admin or otherwise, appears anywhere in this
    function (CON-021, G-3): there is nothing here to point anywhere, which
    is what keeps it inert. See
    :func:`nonogram.export.png._draw_qr_placeholder`'s own docstring for the
    full reasoning — identical here, for a two-up slot rather than a single
    page.
    """
    draw.rectangle((icon.left, icon.top, icon.right, icon.bottom), outline=INK, width=2)
    side = icon.right - icon.left
    step = side / _QR_PLACEHOLDER_MODULES
    for row in range(_QR_PLACEHOLDER_MODULES):
        for column in range(_QR_PLACEHOLDER_MODULES):
            if (row + column) % 2 == 0:
                continue
            draw.rectangle(
                (
                    icon.left + round(column * step),
                    icon.top + round(row * step),
                    icon.left + round((column + 1) * step),
                    icon.top + round((row + 1) * step),
                ),
                fill=INK,
            )


def qr_link(puzzle_number: int) -> str:
    """The typed link the footer prints for puzzle ``puzzle_number`` (CARD-223).

    The one reader of :data:`QR_LINK_TEMPLATE`, so "the link comes from one
    constant" (AC-3) is a property of this module rather than of each page
    kind that prints it, exactly as :func:`grid_size_label` is for the footer's
    other label. Still a placeholder address until CARD-210 — see that
    constant for why it cannot resolve.
    """
    return QR_LINK_TEMPLATE.format(number=puzzle_number)


def qr_group_caption(puzzle_number: int) -> str:
    """The invitation line of one footer QR group, with its puzzle named (CARD-248).

    ``"Puzzle 12 · Solve it online"``: the same *shape* :func:`band_identity`
    prints — the word, the number, :data:`BAND_SEPARATOR` — with
    :data:`QR_CAPTION_TEXT` where the band puts the tier.

    **This function re-spells ``f"Puzzle {n}"``; it does not read
    :func:`band_identity`'s form, and it is the fifth place in the package
    that spells those seven characters** (:func:`band_identity`'s band,
    ``book_answer_key.answer_caption``'s answer-key caption,
    :func:`_puzzle_range_label`'s single-puzzle table-of-contents row, the
    review PDF's own page header in ``admin.pdf_generator``, and this). Said
    outright because an earlier draft of this docstring claimed the form was
    *taken from* :func:`band_identity`, which it never was, and a docstring
    that claims a coupling the code does not have is worse than the fifth
    spelling it was covering for.

    **Why it is not worth removing.** The only way to actually read that form
    is ``band_identity(number, None)``, which leans on the "a row with no
    tier of record prints 'Puzzle 12' and stops" branch — a branch that
    exists to report a **missing grade**, not to compose a prefix. That
    function's own docstring weighs printing "Unrated" there and rejects it;
    were it ever re-decided, this caption would change with it, and a
    baseline fixture pins this caption's rendered string. One real coupling
    traded for one false one is no bargain, so the word stays spelled here
    and the claim is corrected instead.

    **What G-1 pins is the two strings, and those are reused rather than
    retyped**: :data:`QR_CAPTION_TEXT`, the owner's own words, which exist
    once in ``src/nonogram/**`` and are carried through unchanged, and
    :data:`QR_LINK_TEMPLATE`, read only by :func:`qr_link` so that CARD-210
    stays a one-line change — plus :data:`BAND_SEPARATOR` for the mark that
    joins a number to what follows it.
    ``TestTwoUpFooter_EachGroupNamesItsPuzzleNumber``'s
    ``test_the_invitations_words_are_still_one_constant`` is the guard that
    holds those, by reading this function's own source.

    **Why a two-up page's groups name their puzzle and a single page's does
    not.** A single puzzle page has one group, and the page's own band already
    says which puzzle it belongs to. A two-up page stacks its puzzles
    vertically and sets their two links **side by side**, so "which link is the
    upper puzzle's" is a question the reader cannot answer by position alone,
    however the two groups are ordered. The number answers it outright. The
    measurement that makes this free rather than a trade: the group's width is
    set by its widest line, and the typed link (549 px on Book 1's footer face)
    already runs wider than the bare invitation (300 px); naming the puzzle
    takes the invitation to 567 px, so two groups measure 140.0 mm of a
    190.5 mm usable width where two unnamed ones measured 137.0 mm.

    Args:
        puzzle_number: The puzzle's 1-based position in the print order — the
            same number its band, its answer-key entry and its own
            :func:`qr_link` carry.

    Returns:
        The line, ready to set.

    Raises:
        ValueError: ``puzzle_number`` is not a print position (below 1), the
            same refusal :func:`band_identity` makes on the same quantity.
    """
    if puzzle_number < 1:
        raise ValueError(f"puzzles are numbered from 1, got {puzzle_number}")
    return f"Puzzle {puzzle_number}{BAND_SEPARATOR}{QR_CAPTION_TEXT}"


def _qr_group_line_px(dpi: int) -> int:
    """How wide one footer QR group's widest line can **ever** be, in pixels.

    The horizontal twin of :func:`_folio_reserve_px`, and a constant for
    exactly the same reason (CARD-204 Fix 4's own argument, which CARD-248
    inherits rather than re-litigates): this figure takes part in the pairing
    **verdict** — a page whose footer could not hold both groups must not be a
    two-up page at all (:meth:`BookPDFGenerator.puzzle_pages`) — so it may not
    be read off a page's own numbers, or the identical pair would pair on page
    9 and refuse on page 1009. It is therefore the widest line this face can
    set for *any* puzzle number up to :data:`FOLIO_RESERVE_DIGITS` digits,
    from the font and the DPI alone.

    ``slack`` covers the one thing ``9999`` does not: were some other digit of
    this face wider than ``9``, a four-digit number could measure that much
    more. It is ``0`` on the packaged DejaVu Sans, whose digits are tabular
    (measured), and it is kept so that the bound is a bound rather than a
    property of one face.

    The **drawing** uses the real measure instead
    (:meth:`BookPDFGenerator._two_up_page`), which is never wider than this,
    so a page the verdict admitted always has room for the groups it draws.
    """
    font = _band_font(type_px(INTERIOR_FOOTER_LINE_PT, dpi))
    number = 10**FOLIO_RESERVE_DIGITS - 1
    slack = FOLIO_RESERVE_DIGITS * (
        max(font.getlength(digit) for digit in "0123456789") - font.getlength("9")
    )
    return math.ceil(
        max(font.getlength(qr_group_caption(number)), font.getlength(qr_link(number))) + slack
    )


def _draw_qr_caption(
    draw: ImageDraw.ImageDraw,
    caption: QrCaption,
    puzzle_number: int,
    dpi: int,
    *,
    name_the_puzzle: bool = False,
) -> None:
    """Set the QR icon's two footer lines beside it (CARD-223).

    The invitation over the typed link, both at
    :data:`~nonogram.export.layout.INTERIOR_FOOTER_LINE_PT` — CON-020's 10 pt
    floor, the same size and the same face the footer's grid-size label and
    folio are set in, because the three are one line of small print and a
    reader should not be told which of them matters more.

    Every coordinate comes off ``caption``
    (:func:`~nonogram.export.layout.qr_caption`) and nothing is measured
    here (ADR-0036/R2); the only choice this function makes is the Pillow
    anchor that turns ``right_aligned`` into a direction, the same
    translation :func:`_draw_page_frame` makes for the grid-size label. The
    bottom-of-bbox anchors (``rb``/``lb``) keep both glyph boxes above their
    own baselines, so neither line can descend past the icon's row.

    ``name_the_puzzle`` sets :func:`qr_group_caption`'s named form on the
    first line instead of the bare :data:`QR_CAPTION_TEXT` — what a two-up
    page's two side-by-side groups need and a single page's one group does
    not (see that function). The default keeps every single page's footer
    byte-for-byte what CARD-223 drew (G-3).
    """
    font = _band_font(type_px(INTERIOR_FOOTER_LINE_PT, dpi))
    anchor = "rb" if caption.right_aligned else "lb"
    invitation = qr_group_caption(puzzle_number) if name_the_puzzle else QR_CAPTION_TEXT
    for text, baseline in (
        (invitation, caption.caption_baseline),
        (qr_link(puzzle_number), caption.link_baseline),
    ):
        draw.text((caption.x, baseline), text, font=font, fill=INK, anchor=anchor)


def _folio_reserve_px(dpi: int) -> int:
    """The fixed pixel reserve CARD-200's folio gets on a two-up page's lower slot.

    **Owner decision, 2026-10-12, "fixed universal reserve" (CARD-204
    Fix 4).** Review cycles 1 and 2 (F-1, F-5) rejected Fix 1's and Fix 2's
    own versions of this function for taking ``page_number``/
    ``max_page_number`` and so letting a specific page's or a specific
    book's own scale flip :func:`~nonogram.export.layout.compute_pair_layout`'s
    accept/refuse verdict (INV-010). This version takes **only** ``dpi`` — a
    value fixed at compile time (every :class:`BookPDFGenerator` is
    constructed with :data:`~nonogram.export.layout.DPI`, never a
    caller-chosen or book-specific resolution) — so it returns the exact
    same number of pixels for every call this codebase will ever make,
    structurally incapable of depending on ``payloads``, a page number or a
    book's own page count.

    Measures the widest single decimal digit this font actually draws (all
    ten, not assumed — a narrow font could draw "1" tighter than "0") at
    :data:`FOLIO_PT`, the same font/size :func:`_draw_folio` itself measures
    its own clearance from, times :data:`FOLIO_RESERVE_DIGITS` — a fixed
    ceiling sized for any book this software could realistically produce,
    never this book's own largest page number. ``math.ceil``'d to a whole
    pixel, the same rounding :func:`_draw_folio`'s own text-width check
    already uses by comparing a float ``font.getlength`` against whole-pixel
    geometry.
    """
    font = _band_font(type_px(FOLIO_PT, dpi))
    widest_digit_px = max(font.getlength(str(digit)) for digit in range(10))
    return math.ceil(widest_digit_px * FOLIO_RESERVE_DIGITS)


def _draw_folio(
    draw: ImageDraw.ImageDraw,
    left: int,
    top: int,
    right: int,
    bottom: int,
    page_number: int,
    dpi: int,
    content_bottom: Optional[int] = None,
    content_right: Optional[int] = None,
    content_left: Optional[int] = None,
    centred_x: Optional[int] = None,
) -> None:
    """Draw ``page_number``'s plain-decimal folio at the bottom-outer corner (CARD-200).

    **Or at the bottom centre, when the caller passes ``centred_x``**
    (CARD-222). The frame the owner's artifact asks for puts the QR icon in
    the footer's outer corner (CARD-223), which is where this folio has sat
    since CARD-200, so on a page that carries the frame the page number moves
    to the footer line's centre —
    :attr:`~nonogram.export.layout.InteriorFrame.folio_x`, the trim's own
    centre, so it lands in the same place on every page of the book whichever
    side of the spread it is on. The room check below is **not** made in that
    case and no argument of it is read: a caller passing ``centred_x`` has
    already established that the footer strip is clear of its own content
    (:func:`_draw_page_frame` is the one caller that does, and it omits the
    whole footer group together rather than this mark alone). One
    ``draw.text`` call either way, so there is still exactly one place in this
    module that draws a folio.

    ``left``/``top``/``right``/``bottom`` are one page's usable area in
    device pixels — read off a :class:`PageFrame` (guide, divider, TOC) or a
    grid page's own :class:`~nonogram.export.layout.PagePlacement`
    (``usable_left``/``usable_top``/``usable_right``/``usable_bottom`` — one-
    up, two-up, solved, packed). **They cross as four plain ints, not as the
    frame object itself** — a correction to this card's own draft, which
    claimed the two classes "already expose the same four ``usable_*``
    fields by name": read in full, :class:`PageFrame` actually names them
    ``left``/``top``/``right``/``bottom`` (no ``usable_`` prefix), so a
    caller duck-typing on that premise would have raised ``AttributeError``
    the first time this function tried ``frame.usable_bottom`` on a guide
    page's :class:`PageFrame`. Normalising to four ints at each call site
    keeps this function itself ignorant of which class its caller holds
    (G-1: no field is added to either class to make the names agree).

    ``content_bottom`` is the lowest pixel this page's own content already
    reaches, when the caller has a real figure to offer — the same
    measurement the answer caption's own slack check already makes
    (``placement.usable_bottom - placement.drawing_bottom``). Left at
    ``top`` (the full usable height counts as available) when omitted, which
    is correct only for a page kind nothing ever competes with this corner
    for (CARD-197's "omit rather than collide" rule for the answer caption,
    generalised to every page kind that actually needs it — AC-1's own final
    clause — rather than reinvented per kind).

    **Review cycle 2, F-1 (gating):** a vertical-only check is not enough for
    every caller. A two-up page's *lower* slot reports zero vertical slack
    **by construction** (:class:`PairLayout`'s own docstring: "the lower
    slot['s]... drawing's bottom edge is the bottom margin") on *every*
    two-up page, not just a tight one — so a caller that always fed the
    lower slot's own ``drawing_bottom`` back as ``content_bottom`` would
    silently omit the folio from every two-up page in the book, which is
    worse than the collision it would be avoiding. What actually decides
    whether the lower slot's own ink can reach the folio's exact corner is
    *horizontal* room at that same row.

    **Since CARD-204 that room is a fixed reserve, not a pair-dependent
    leftover.** This paragraph previously read "the lower slot is centred
    across the page's shared usable width and only touches the left/right
    margin when that centring leaves no spare, which is the common case's
    opposite, not its rule" — false on both counts since this card, and the
    canonical statement of exactly the belief cycle-3's review (F-7) traced
    Fix 3's folio-loss regression to; corrected here per cycle-4's F-12. No
    slot is centred any more: CARD-204's reading (b) places each slot flush
    with the usable area's *outer* margin, mirrored by parity (an ODD,
    right-hand page lands ``drawing_right`` on ``usable_right``; an EVEN,
    left-hand one lands ``drawing_left`` on ``usable_left``), and
    :func:`~nonogram.export.layout._slot_layout`'s own docstring proves that
    an algebraic identity for *every* slot, however large its own spare — so
    "when centring leaves no spare" is not the rare case, it is not a case at
    all. What the lower slot does instead, on **every** two-up page and
    regardless of either puzzle's extent, is reach to within exactly
    :func:`_folio_reserve_px` pixels of that outer margin, because
    :func:`~nonogram.export.layout.compute_pair_layout` keeps that many
    pixels of the slot's own spare out of the parity shift and, when the
    natural spare is smaller, re-fits the shared cell until it is not (owner
    decision 2026-10-12, "fixed universal reserve"; the reserve is sized for
    :data:`FOLIO_RESERVE_DIGITS` digits of this same face at
    :data:`FOLIO_PT`, which is why the check below clears by exactly that
    reserve). The horizontal test is therefore a verification that the
    reserved room really arrived — not a gamble on leftover slack, and not a
    check that only tight pairs can fail.

    **CARD-224 corrects the paragraph above twice over, and the mechanism
    survives both corrections.** (a) Slots *are* centred again — that card
    restores FR-032's own clause, so each slot leaves ``max(spare, 0) / 2``
    on **both** of its sides and the reserve no longer shifts either slot's
    placement; it is still taken out of the shared cell's own fit, so the
    room at the corner is now half the lower slot's spare, which is at least
    half the reserve and usually several times it. (b) Since CARD-248 a
    two-up page reserves a whole footer strip, so its folio is set **centred
    on the footer line** and never reaches this corner at all: the corner
    path is the documented fallback for a pair laid out without that strip,
    which nothing in production builds. So this check is still the one that
    decides, it still cannot fire on a page with room, and the one geometry
    it could now refuse — a four-digit page number on a cornered two-up page
    whose lower slot has little spare — is recorded in
    ``tests/property/test_book_two_up.py`` rather than left to be
    discovered.

    ``content_right``/
    ``content_left`` (the content's own rightmost/leftmost pixel — e.g.
    ``placement.drawing_right``/``drawing_left``) are read **only** when
    ``content_bottom`` already shows no vertical room: the folio is then
    omitted only if the relevant one (``content_right`` on a right-hand
    page, ``content_left`` on a left-hand one — :func:`page_is_right_hand`
    picks which) *also* leaves no room for the folio's own measured text
    width at that corner, i.e. only when the content's own bounding box
    would actually overlap the folio's. A caller with no horizontal figure
    to offer (``content_right``/``content_left`` left ``None``) keeps the
    old, more conservative "no vertical room is already enough to omit"
    rule — which is what :meth:`BookPDFGenerator.solved_puzzle_page` and
    :meth:`BookPDFGenerator._blank_page` still want, since neither has a
    structural reason its own vertical slack would ever read zero on every
    call the way a two-up page's lower slot does.

    The anchor is chosen so the folio's own glyph box never crosses
    ``bottom``, ``left`` or ``right`` (G-5 is read, not changed: this is a
    new decision about the folio's own position, not a change to where a
    drawing already placed sits) — Pillow's ``"rb"`` anchor (right,
    bottom-of-bbox) at ``(right, bottom)`` on a right-hand page,
    ``"lb"`` at ``(left, bottom)`` on a left-hand one, by
    :func:`page_is_right_hand` (FR-043).
    """
    size = type_px(FOLIO_PT, dpi)
    font = _band_font(size)
    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    text = str(page_number)
    if centred_x is not None:
        draw.text((centred_x, bottom), text, font=font, fill=INK, anchor="mb")
        return
    right_hand = page_is_right_hand(page_number)
    if content_bottom is not None and bottom - content_bottom < line_height:
        text_width = font.getlength(text)
        if right_hand:
            clear_horizontally = (
                content_right is not None and content_right <= right - text_width
            )
        else:
            clear_horizontally = (
                content_left is not None and content_left >= left + text_width
            )
        if not clear_horizontally:
            return
    x = right if right_hand else left
    anchor = "rb" if right_hand else "lb"
    draw.text((x, bottom), text, font=font, fill=INK, anchor=anchor)


def grid_size_label(columns: int, rows: int) -> str:
    """One puzzle's grid size as the footer prints it: ``"20 x 25"`` (CARD-222).

    Width first, then height, which is how every other surface in this
    project names an extent (the panel's filters, the export filename,
    ``book_arrange``'s size column) and how the owner's artifact draws it.
    """
    return f"{columns}{SIZE_LABEL_SEPARATOR}{rows}"


def _draw_rule(draw: ImageDraw.ImageDraw, rule: PageRule) -> None:
    """Stroke one of the frame's ruled lines (CARD-222).

    The one place a frame rule is stroked, so "the header rule and the footer
    rule are the weights COMP-007 measured" is a property of this function
    rather than of each caller (ADR-0036/R2: the renderer strokes the line and
    does not pick it). Pure black, like every other rule on a book page
    (ADR-0037/R2's colour clause), and centred on its own row the way the
    drawing's rules are (:class:`~nonogram.export.layout.PuzzleFrame`).
    """
    draw.line(
        [(rule.left, rule.y), (rule.right, rule.y)], fill=INK, width=rule.width
    )


def _draw_page_frame(
    draw: ImageDraw.ImageDraw,
    frame: InteriorFrame,
    page_number: int,
    dpi: int,
    *,
    size_label: Optional[str] = None,
    content_bottom: Optional[int] = None,
    content_right: Optional[int] = None,
    content_left: Optional[int] = None,
) -> bool:
    """Draw one puzzle page's frame: the two rules, the size label, the folio.

    The owner's artifact of 2026-10-14, "The rules behind it" (CARD-222): the
    header rule runs the full text width under the header, the footer's
    hairline runs it again above a line that carries the puzzle's grid size on
    the **inner** side and the page number at its centre. Every coordinate and
    both weights come from ``frame``
    (:func:`~nonogram.export.layout.interior_frame`); nothing is measured here.

    **The header rule is unconditional. The footer group is all-or-nothing.**
    A drawing fitted flush to the bottom margin — which a two-up page's lower
    slot was by construction until CARD-248 reserved it a footer strip
    (:class:`~nonogram.export.layout.PairLayout`), and which a page-fit-bound
    single puzzle can be — would be crossed by the hairline and overprinted by
    a centred folio.

    **Since CARD-224 this condition and the layout's own verdict are the same
    question.** A single page's drawing floats at 42% of the puzzle area's
    spare height, so it reaches below the footer rule on exactly the pages
    whose area cannot hold it at all — the pages
    :attr:`~nonogram.export.layout.PagePlacement.vertical_bound` reports as
    ``"footer"``, where that card's own rule degrades to "as low as it fits"
    and holds the drawing at the band's foot or lower. The two are not wired
    together (this function is handed a pixel, not a verdict, and keeps
    deciding from the pixel), and **they do not agree by construction** — the
    placement reaches its verdict from a clearance in pixels and this function
    reaches its own from ``content_bottom``, so what makes "no drawing ink
    crosses a rule that is drawn" true of every page is an inequality the
    placement maintains, not the shape of the code.

    The inequality, since CARD-224's review cycle 2 (F2-001): a degraded
    placement takes the band's foot only while the gap it leaves below pays
    the drawing's own clearance, and otherwise goes to
    ``area_bottom + 1 - drawing_height`` — one pixel of drawing past the
    footer rule, which makes the test below false and omits the group. So
    either the drawing clears the hairline or the hairline is not stroked, at
    **every** band depth and rule weight. Until that cycle the degraded
    placement relied on the band's own lift (``band_mm / 8``) outrunning the
    clearance threshold, which is true of Book 1's 12 mm band (17.72 px
    against 14.29 px) and false below about 10.4 mm, where a shallower title
    band put ink three rows past a stroked hairline. Pinned by
    ``tests/test_book_puzzle_frame.py``'s
    ``test_a_positive_spare_too_small_to_clear_the_rule_also_reports_footer``
    and ``test_a_shallow_band_cannot_leave_ink_on_a_drawn_footer_rule``, and
    swept on a 9 mm band by that module's ``"shallow band"`` sheet.
    The one row both sides read is
    :func:`~nonogram.export.layout._puzzle_area_px`'s footer row: it is
    ``frame.footer_rule.y`` here and the placement's own ``area_bottom``, so
    there is one definition and not two that can drift.

    Where ``content_bottom`` reaches below the footer rule, the rule, the label
    and the centred folio are therefore **all** omitted and the page keeps
    CARD-200's bottom-outer-corner folio instead, which is the corner
    :func:`_folio_reserve_px` already reserves room in. One condition,
    one place, all three marks: a half-drawn footer (a rule with no number
    under it, or a number sitting on a grid) is worse than the corner this card
    inherited.

    **The footer's other two marks are drawn by this function's callers**
    (CARD-223: the QR icon and its two lines, at the footer's outer corner),
    and they are gated by the *same* condition rather than by this function's
    return value — :func:`~nonogram.export.layout.qr_slot` makes the identical
    test on the identical figure, which ``tests/test_book_qr_slot.py`` pins as
    an equivalence over a seeded corpus. They are not drawn here because the
    icon is a **per-drawing** mark and this frame is a property of the
    *sheet*: a two-up page has one footer and two icons, so a frame-level
    drawer would have to be handed the slots it refuses to know about.

    Args:
        draw: The page's draw object.
        frame: The page's frame, from ``interior_frame(page_spec)``.
        page_number: The page's 1-based interior position (FR-043).
        dpi: The page's resolution, for the two type sizes.
        size_label: The grid size the footer prints
            (:func:`grid_size_label`), or ``None`` for a page that has no one
            grid size to name — a two-up page, whose two slots carry two
            (CARD-226 gives each slot its own).
        content_bottom: The lowest pixel this page's own content reaches, or
            ``None`` for a page nothing competes with the footer for. Read
            exactly as :func:`_draw_folio` reads it.
        content_right: Passed to :func:`_draw_folio` for the corner fallback.
        content_left: Passed to :func:`_draw_folio` for the corner fallback.

    Returns:
        Whether the footer group was drawn. ``False`` means this page fell
        back to the corner folio — the verdict is returned rather than
        re-derived by a caller that wants to assert it.
    """
    _draw_rule(draw, frame.header_rule)
    footer_is_clear = content_bottom is None or content_bottom <= frame.footer_rule.y
    if not footer_is_clear:
        # CARD-200's corner, untouched: on the bottom margin
        # (``page_bottom``), which is the row ``_folio_reserve_px`` keeps
        # horizontal room in on a two-up page's lower slot — never the footer
        # line, which this page's own content is standing on.
        _draw_folio(
            draw,
            frame.header_rule.left,
            frame.header_rule.y,
            frame.header_rule.right,
            frame.page_bottom,
            page_number,
            dpi,
            content_bottom=content_bottom,
            content_right=content_right,
            content_left=content_left,
        )
        return False
    _draw_rule(draw, frame.footer_rule)
    if size_label is not None:
        draw.text(
            (frame.label_x, frame.baseline),
            size_label,
            font=_band_font(type_px(SIZE_LABEL_PT, dpi)),
            fill=INK,
            anchor="rb" if frame.label_right_aligned else "lb",
        )
    _draw_folio(
        draw,
        frame.header_rule.left,
        frame.header_rule.y,
        frame.header_rule.right,
        frame.baseline,
        page_number,
        dpi,
        centred_x=frame.folio_x,
    )
    return True


def _guide_rule_width(spec: PageSpec) -> int:
    """This page's thin rule width, in pixels (CARD-201).

    Borrowed from a puzzle probe layout (:data:`_PROBE_CLUES`, the same probe
    :func:`page_frame` reads) so the pipeline diagram's and the difficulty
    box's borders are drawn at the same weight as every ruled line on this
    book's pages (ADR-0037/R2), through ``compute_layout`` rather than an
    invented stroke width (ADR-0036/R2, G-3).
    """
    return compute_layout(_PROBE_CLUES, _PROBE_CLUES, spec).thin_rule


def _draw_pipeline_diagram(
    spec: PageSpec, steps: Tuple[GuidePipelineStep, ...], label_font: Any, label_size: int
) -> Image.Image:
    """"Assume, and watch it break": four bordered boxes joined by arrows (CARD-201).

    Not a puzzle-line diagram (this card's own "Target" point 2) — there is
    no clue, no grid, nothing for :func:`example_line_layout` to lay out — so
    this draws directly: each box bordered at :func:`_guide_rule_width`,
    lettered with the step's word and, under it, its icon (a filled or
    crossed square for ASSUME/PROVED, drawn with the same primitives
    :func:`draw_example_line` fills and crosses a cell with; plain ASCII
    ``"..."``/``"!"`` for FOLLOW/BREAKS — see :class:`GuidePipelineStep`), an
    arrowhead-tipped line joining each box to the next. Pure black ink, no
    fill but the icon's own (G-5).

    ``label_size`` is the pixel size ``label_font`` was asked for from
    :func:`_guide_face`, passed explicitly rather than read back off
    ``label_font.size`` (review cycle 1, F-2, gating). The reason it was
    introduced is **gone**: ``_guide_face`` could return an "unsized" face
    with no ``.size`` attribute at all — a sizeless
    ``ImageFont.load_default()``, on any non-macOS host with a Pillow older
    than 10.1, a combination ``pyproject.toml``'s unbounded ``Pillow>=10.0``
    floor still allows — and since CARD-221 it returns the packaged face at
    the asked-for size and nothing else, on every host. The parameter stays
    because the habit it encodes is sound on its own terms: every caller of a
    ``_guide_face`` font in this file measures through the font's own API
    (``create_guide_page``'s title/body fonts with
    ``getlength``/``getmetrics``, ``create_divider_page``'s with
    ``draw.textbbox``) rather than reading a number off the object, and
    taking the size as a parameter is the same discipline. Its own
    robustness test still stands, against a stand-in face rather than
    against a face ``_guide_face`` can return
    (``tests/test_book_guide_page.py``'s
    ``test_the_new_drawing_routines_tolerate_a_sizeless_fallback_face``).
    """
    rule = _guide_rule_width(spec)
    border = max(rule, 1)
    pad = label_size
    icon = label_size * 2
    bbox = label_font.getbbox("Mg")
    label_h = bbox[3] - bbox[1]
    box_w = int(max(label_font.getlength(step.label) for step in steps) + pad * 2)
    box_h = int(pad * 3 + label_h + icon)
    arrow_w = pad * 3
    width = len(steps) * box_w + (len(steps) - 1) * arrow_w
    canvas = Image.new("RGB", (width, box_h), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    icon_top = pad * 2 + label_h
    x = 0
    for index, step in enumerate(steps):
        # Review cycle 1, F-3 (gating): ``x + box_w`` is one pixel past this
        # box's own right edge — for the last box that is the canvas's exact
        # pixel width, one past the last valid pixel, so Pillow clipped it
        # and "PROVED" shipped with no visible right border; for every
        # earlier box it drew 1px into the arrow gutter instead of the box.
        # ``x + box_w - 1`` is the box's own last column (confirmed by
        # rendering the fix and pixel-checking every box, the last included,
        # for a complete, un-clipped 4-sided border that stays clear of the
        # arrows — see test_the_last_pipeline_box_has_a_complete_unclipped_border).
        draw.rectangle((x, 0, x + box_w - 1, box_h - 1), outline=INK, width=border)
        draw.text(
            (x + box_w / 2, pad), step.label, font=label_font, fill=INK, anchor="ma"
        )
        cx, cy = x + box_w / 2, icon_top + icon / 2
        half = icon * 0.3
        if step.icon == PIPELINE_ICON_SQUARE:
            draw.rectangle((cx - half, cy - half, cx + half, cy + half), fill=INK)
        elif step.icon == PIPELINE_ICON_CROSS:
            draw.line([(cx - half, cy - half), (cx + half, cy + half)], fill=INK, width=border)
            draw.line([(cx - half, cy + half), (cx + half, cy - half)], fill=INK, width=border)
        elif step.icon == PIPELINE_ICON_DOTS:
            draw.text((cx, cy), "...", font=label_font, fill=INK, anchor="mm")
        elif step.icon == PIPELINE_ICON_BANG:
            draw.text((cx, cy), "!", font=label_font, fill=INK, anchor="mm")
        else:  # pragma: no cover - defensive; every kind above is handled
            raise ValueError(f"unknown pipeline icon kind: {step.icon!r}")
        x += box_w
        if index < len(steps) - 1:
            mid_y = box_h // 2
            tip_x = x + arrow_w - border
            draw.line([(x + border, mid_y), (tip_x, mid_y)], fill=INK, width=border)
            head = max(border * 3, pad // 2)
            draw.polygon(
                [(tip_x, mid_y), (tip_x - head, mid_y - head), (tip_x - head, mid_y + head)],
                fill=INK,
            )
            x += arrow_w
    return canvas


def _draw_difficulty_legend(
    labels: Tuple[DifficultyLabel, ...],
    measure: int,
    text_font: Any,
    text_size: int,
) -> Image.Image:
    """"What the difficulty labels mean": the three tier names, in a row.

    A ``measure``-wide strip, one column per entry of ``labels``, each
    holding its tier's :attr:`~DifficultyLabel.name` and nothing else.

    **It was a bordered box holding a sentence per column until CARD-221 fix
    1** (``_draw_difficulty_box``, CARD-201; the source PDF's grey-filled
    highlight became a plain bordered box in the book's own ink and paper).
    The owner's decision to stop printing the three sentences
    (:data:`GUIDE_DIFFICULTY_LABELS`) took the rule with them, and that was
    this card's call to make on the render rather than the owner's: a
    ``measure``-wide rectangle holding three words — about a seventh of its
    own area, under a heading that promises an explanation — reads as a
    table whose contents failed to draw, which is worse than no rule at all.
    Nothing else on either guide page borders anything it does not enclose:
    the pipeline's four boxes each hold a word and an icon, and every line
    diagram's frame holds a grid. Three names in a row, set under their own
    heading with the page's own leading above and below them, read as the
    legend they are — which is also the shape CARD-229 moves into the
    guide's key strip.

    With the rule gone this draws no ruled line at all, so it no longer
    needs the page's own :class:`PageSpec` (it took one only for
    :func:`_guide_rule_width`), nor the ``leading`` that set a column's
    wrapped sentences, nor the ``with_text`` flag that chose between the two
    forms: the labels-only form is the only form.

    ``text_size`` is ``text_font``'s own pixel size, passed explicitly rather
    than read off ``text_font.size`` — see :func:`_draw_pipeline_diagram`'s
    docstring (review cycle 1, F-2, gating) for why ``.size`` is never read
    off a ``_guide_face`` font.
    """
    pad = text_size
    gutter = pad
    # Flush at both ends of the measure, where the box's own border used to
    # be: with the rule gone its ``pad`` of inner margin would have left the
    # first label indented from a left edge nothing draws any more, out of
    # line with every other line of type on the page — the heading directly
    # above it included. The columns keep their pitch (one ``gutter``
    # between them) and simply start at the measure's own left edge.
    column_w = (measure - gutter * (len(labels) - 1)) // len(labels)
    bbox = text_font.getbbox("Mg")
    name_h = bbox[3] - bbox[1]
    # ``pad`` of white above and below the row: the one piece of the box's
    # geometry that still does a job now that there is no rule to do it —
    # it is what sets the legend apart from the heading above and the
    # paragraph below, exactly as it separated them from the border before.
    height = pad * 2 + name_h
    canvas = Image.new("RGB", (measure, height), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    x = 0
    for label in labels:
        draw.text((x, pad), label.name, font=text_font, fill=INK)
        x += column_w + gutter
    return canvas


@dataclass(frozen=True)
class TocEntry:
    """One row of the table of contents: a label, and the page it sends a
    reader to (CARD-205).

    The boundary type between the two halves of the TOC — the pass that
    decides *what* is listed (:func:`structural_toc_entries`, from the page
    plan) and the one that draws it
    (:meth:`BookPDFGenerator.create_toc_page`) — and a type of its own
    rather than the ``(label, page_number)`` tuple CARD-200 passed, for the
    reason this card introduces a row that has **no** page number: a bare
    ``(str, Optional[int])`` tuple makes every reader of a row decide for
    itself whether the second slot is a page or a sentinel, where this
    makes the two kinds of row name themselves (:attr:`is_heading`).

    Attributes:
        label: The row's text, exactly as it prints. Already resolved —
            :data:`GUIDE_TITLE`, a :class:`~nonogram.difficulty.Tier`'s own
            label, :func:`toc_range_label`'s range or
            :data:`TOC_SOLUTIONS_LABEL` — never a template the drawing
            fills in.
        page: The 1-based interior page the row names, or ``None`` for a
            level **heading**, which groups the row under it and points at
            no page of its own (the page number belongs to the
            ``Puzzles N–M`` row beneath it, which is the page a reader
            actually turns to). A heading therefore gets no leader dots
            either: there is nothing on the right for them to lead to.
        starts_group: Whether this row **opens a group** of the list, and is
            therefore set :data:`TOC_GROUP_GAP_PT` of extra white below
            whatever precedes it (CARD-205 Fix 2, owner decision
            2026-10-14). True on each level heading and on the
            :data:`TOC_SOLUTIONS_LABEL` row.

            A flag of its own rather than anything
            :meth:`BookPDFGenerator.create_toc_page` could infer, and the
            one reason this type grew a third field. The two inferences
            available are both wrong about what is meant:
            :attr:`is_heading` separates the three headings but not
            ``Solutions``, which is a *numbered* row that nonetheless opens
            the last group — that is exactly the gap this field was added
            to close; and "the last row" reads the same today only by
            accident, and would silently mis-set the moment anything is
            appended after the solutions (an appendix, an index, a second
            answer section), separating the new tail instead of the row
            that actually means it.

            It is a flag and **not** a row: the row count AC-1 pins and
            :func:`structural_toc_entry_count`'s ``2 + 2 * levels`` are
            untouched by it, and every row is still one line of
            :data:`TOC_ENTRY_PT` high, so
            :func:`_toc_entries_per_page` stays a uniform division (G-2).
    """

    label: str
    page: Optional[int] = None
    starts_group: bool = False

    def __post_init__(self) -> None:
        if self.page is not None and self.page < 1:
            raise ValueError(
                f"a TOC row names interior page 1 or later, got {self.page}"
            )

    @property
    def is_heading(self) -> bool:
        """Whether this row is a level heading — a label with no page number."""
        return self.page is None


@dataclass(frozen=True)
class PuzzlePagePlan:
    """One page of the interior's puzzle section: one puzzle, or two (FR-040).

    What :meth:`BookPDFGenerator.puzzle_pages`'s walk decided, before any page
    is drawn: where the page sits, which puzzles it holds, and — for a two-up
    page — the geometry COMP-007 measured for the pair.

    Attributes:
        page_number: The page's 1-based position in the interior, which is
            where its parity comes from (FR-043).
        numbers: The 1-based print numbers of the puzzles on it, in print
            order: one number, or two with the upper slot's first.
        pair: ``None`` for a single-puzzle page. Otherwise the
            :class:`~nonogram.export.layout.PairLayout` whose ``upper`` slot is
            ``numbers[0]`` and whose ``lower`` slot is ``numbers[1]``.
    """

    page_number: int
    numbers: Tuple[int, ...]
    pair: Optional[PairLayout] = None

    @property
    def is_two_up(self) -> bool:
        """Whether this page holds two puzzles (TERM-030)."""
        return self.pair is not None


@dataclass(frozen=True)
class DividerPagePlan:
    """One page of the interior's puzzle section that opens a level (TERM-031).

    The other kind of page :meth:`BookPDFGenerator.puzzle_section` plans, and
    deliberately a type of its own rather than a :class:`PuzzlePagePlan`
    holding no puzzle: a divider carries no band, no number and no drawing
    (G-3), so every caller that walks the section is made to say which of the
    two it is looking at instead of discovering it from an empty tuple.

    Attributes:
        page_number: Its 1-based position in the interior, which is where its
            parity comes from like any other page's (FR-043).
        level: The level it opens. A :class:`~nonogram.difficulty.Tier` and
            never ``None`` — the name is the whole of what a divider carries,
            and a run of rows with no readable tier has none to print, so it
            opens no divider at all (see the module docstring).
    """

    page_number: int
    level: Tier

    def __post_init__(self) -> None:
        if not isinstance(self.level, Tier):
            raise ValueError(
                f"a divider page opens one of ADR-0031's tiers, not {self.level!r}"
            )

    @property
    def text(self) -> str:
        """The only thing printed on it: "Easy", "Medium" or "Hard" (AC-254)."""
        return self.level.label


#: One planned page of the interior's puzzle section: a level's divider, or a
#: page of one or two puzzles.
SectionPage = Union[DividerPagePlan, PuzzlePagePlan]


@dataclass(frozen=True)
class SectionPlan:
    """The book's puzzle section decided from its rows, before anything draws.

    What :meth:`BookPDFGenerator.section_plan` settles: the print order, which
    rows can be printed at all, and the pages they take
    (:meth:`BookPDFGenerator.puzzle_section`). It is the **one** seam through
    which a book's pages are decided (CARD-140) — the export path walks it to
    draw, and the Arrangement screen walks the same call to say where each
    puzzle will print, so the screen cannot report a page the book does not
    have.

    Attributes:
        puzzles: Every row the book holds, in print order
            (:func:`print_order`) — the undrawable ones included, because that
            is the book's membership and what the guide page counts.
        ids: The ids of the rows that built an export payload, in print order
            and parallel to :attr:`payloads`. ``ids[n - 1]`` is the id of the
            row printed as puzzle ``n``, which is what the export's failure
            messages name.
        printed: Those same rows **themselves**, in print order and parallel to
            :attr:`ids`. ``printed[n - 1]`` is the row printed as puzzle ``n``,
            which is what turns a page's :attr:`PuzzlePagePlan.numbers` back
            into rows a screen can point at. It carries the rows and not just
            their ids because an id need not identify a row: two rows with no
            id, or with ids that stringify alike, are one key in any map built
            from :attr:`ids` and the later one wins, whereas the rows the
            caller handed over are distinct objects by construction
            (CARD-140 F-003).
        payloads: Those rows as the export's boundary type, parallel to
            :attr:`ids`.
        pages: The section's pages in print order: a
            :class:`DividerPagePlan` opening each named non-empty level, each
            immediately before that level's :class:`PuzzlePagePlan`\\ s.
        toc_page_count: How many table-of-contents pages precede this
            section (CARD-200) — the term already baked into every page in
            :attr:`pages` own :attr:`PuzzlePagePlan.page_number`/
            :attr:`DividerPagePlan.page_number`, carried here too so a caller
            that needs the interior's *own* ``first_answer_page`` arithmetic
            (:meth:`BookPDFGenerator.interior_stream`) does not re-derive it
            from the entry count a second time.
    """

    puzzles: List[Any]
    ids: List[Any]
    printed: List[Any]
    payloads: List[ExportPayload]
    pages: List[SectionPage]
    toc_page_count: int = 0


@dataclass(frozen=True)
class Interior:
    """The interior's pages, and what two-up pairing (and, since CARD-202,
    small-answer packing) saved (FR-040, FR-042).

    Attributes:
        pages: Every interior page in print order; ``pages[n - 1]`` is interior
            page ``n``. No cover page (FR-043, INV-013).
        unpaired_page_count: What the same interior would have taken with every
            puzzle on a page of its own **and** its answer unpacked — the
            baseline before any space-saving technique. Both are **interior**
            counts: the cover is a separate file and is never counted.

            It is deliberately left at one answer page per puzzle
            (CARD-198's own shape) rather than recomputed with CARD-202's
            packing walk, so :attr:`pages_saved` now measures two-up pairing
            *and* small-answer packing together — not pairing alone, as this
            attribute's own name once implied before CARD-202 (see that
            card's Worktree notes for the reasoning:
            ``book_kdp.unpaired_interior_page_count`` keeps the matching
            baseline for the same reason, an EC-034 cross-check between the
            two).
        answer_page_count: How many of :attr:`pages` are answer pages, the
            SOLUTIONS divider **not** counted (FR-042) — the Increment 15
            checkpoint's own number, now CARD-202's packed-or-full count.
    """

    pages: List[Image.Image]
    unpaired_page_count: int
    answer_page_count: int = 0

    @property
    def page_count(self) -> int:
        """The interior's real page count, after pairing."""
        return len(self.pages)

    @property
    def pages_saved(self) -> int:
        """How many interior pages the two-up pages saved. Never negative."""
        return self.unpaired_page_count - self.page_count


@dataclass(frozen=True)
class InteriorStream:
    """The interior decided but not yet drawn (CARD-145).

    Everything :class:`Interior` states about a book, **before** a page of it
    exists: the three counts are the page plan's own arithmetic over the
    pairing walk and CARD-202's own packing walk
    (:func:`~nonogram.admin.book_answer_key.plan_small_answer_pages`, pure and
    sheet-free), so an export can report what it is about to write without
    building 25.2 MB of bitmap per page to count them.

    Attributes:
        page_count: The interior's page count after pairing and packing — the
            same number :attr:`Interior.page_count` reports, and the number
            of pages :attr:`pages` is contracted to produce.
        unpaired_page_count: What the same interior would have taken with
            every puzzle on a page of its own and its answer unpacked
            (:attr:`Interior.unpaired_page_count`).
        paired_only_page_count: What the same interior would have taken with
            two-up pairing applied but CARD-202's packing **not** — pairing's
            own baseline, between :attr:`unpaired_page_count` and
            :attr:`page_count`. This is what lets :attr:`pages_saved_by_pairing`
            and :attr:`pages_saved_by_packing` attribute the saving between
            :attr:`unpaired_page_count` and :attr:`page_count` to the
            technique that actually made it (review F-2: the Finalise screen
            used to show the *whole* delta as "pairing", which misattributed
            whatever a small answer's packing saved).
        answer_page_count: How many of the pages are answer pages, the
            SOLUTIONS divider not counted (:attr:`Interior.answer_page_count`).
        pages: The interior's pages in print order, drawn **one at a time, on
            demand**. A generator, and therefore single-use: walking it a
            second time yields nothing. It is the export path's only source of
            pages, and it holds none of them — a page is built when it is
            asked for and released when the next one is. Its length is checked
            against :attr:`page_count` as it goes (:func:`_as_planned`).
    """

    page_count: int
    unpaired_page_count: int
    answer_page_count: int
    pages: Iterator[Image.Image]
    paired_only_page_count: int = 0

    @property
    def pages_saved(self) -> int:
        """How many interior pages pairing *and* packing together saved. Never negative."""
        return self.unpaired_page_count - self.page_count

    @property
    def pages_saved_by_pairing(self) -> int:
        """How many interior pages two-up pairing alone saved (review F-2).

        Measured against :attr:`paired_only_page_count`, not
        :attr:`page_count`, so a book whose packing did the saving reports
        zero here rather than claiming pairing's credit.
        """
        return self.unpaired_page_count - self.paired_only_page_count

    @property
    def pages_saved_by_packing(self) -> int:
        """How many interior pages CARD-202's packing alone saved (review F-2).

        Measured from :attr:`paired_only_page_count` (pairing already
        applied) to :attr:`page_count`, so :attr:`pages_saved_by_pairing` +
        this always equals :attr:`pages_saved`.
        """
        return self.paired_only_page_count - self.page_count


def _as_planned(
    pages: Iterable[Image.Image], page_count: int
) -> Iterator[Image.Image]:
    """``pages``, refused the moment they stop being ``page_count`` of them.

    The streaming replacement for the list-length check the export used to
    make after building every page. It cannot be made on a list any more —
    there is no list — so it is made *as the pages go past*, which is strictly
    earlier: the extra page is refused before it is written rather than after.

    Both directions are structural failures, not cosmetic ones. The PDF writer
    pre-allocates one image, page and contents object id per planned page
    before anything is drawn (:meth:`BookPDFGenerator._write_pdf`), so a
    producer that yielded **more** pages than planned would write objects
    nothing references, and one that yielded **fewer** would leave the page
    tree pointing at object ids that were never written — a file whose page
    count is a lie and whose reader hits a dangling reference. Neither is
    allowed to reach the trailer: the over-count raises in place of the
    surplus page, and the under-count raises at the end of the walk, before
    the caller writes the cross-reference table.

    The under-count's message is the wording the list-length check used, so
    the guard reads the same in a traceback as it always has.

    Raises:
        RuntimeError: the producer's page count is not ``page_count``.
    """
    produced = 0
    for page in pages:
        produced += 1
        if produced > page_count:
            raise RuntimeError(
                f"interior has at least {produced} pages, its page plan says "
                f"{page_count}"
            )
        yield page
        # The page is the writer's alone from here: this frame must not be
        # what keeps a 25.2 MB bitmap alive while the next one is built.
        del page
    if produced != page_count:
        raise RuntimeError(
            f"interior has {produced} pages, its page plan says {page_count}"
        )


@dataclass(frozen=True)
class BookExport:
    """A book's export: the interior PDF and, beside it, the cover file.

    ``interior_page_count`` is the book's page count (FR-030 as amended by
    FR-043) — the interior's pages only; the cover file is never counted.
    ``unpaired_interior_page_count`` is the same count before two-up pairing
    (FR-040), so the two together are the saving the owner's "big books"
    research asks for. ``answer_page_count`` is how many of those pages are
    answer pages, the SOLUTIONS divider not counted (FR-042). All three are
    interior counts.
    """

    interior: BytesIO
    cover: BytesIO
    interior_page_count: int
    unpaired_interior_page_count: int
    answer_page_count: int = 0

    @property
    def pages_saved(self) -> int:
        """Interior pages saved by printing two puzzles to a page (FR-040)."""
        return self.unpaired_interior_page_count - self.interior_page_count


@dataclass(frozen=True)
class PageFrame:
    """One book page's trim and usable area in device pixels (ADR-0036/R2).

    Not measured here: it is :func:`~nonogram.export.layout.compute_layout`'s
    own answer for the page's :class:`~nonogram.export.layout.PageSpec`, read
    off a :class:`~nonogram.export.layout.PagePlacement`. That is what lets
    the pages this module draws itself — the guide, the divider, the cover —
    sit on the same trim, inside the same mirrored margins, as the puzzle
    pages COMP-007 places, without the admin panel converting a millimetre to
    a pixel anywhere.

    Attributes:
        width: The trim's width; ``height`` its height.
        left: The usable area's left edge — the gutter margin on an odd
            (right-hand) page, the outside margin on an even one.
        top: The usable area's top edge (the title band starts here).
        right: Its right edge; ``bottom`` its bottom edge.
    """

    width: int
    height: int
    left: int
    top: int
    right: int
    bottom: int


#: The smallest clue set that still describes a puzzle: one 1-cell row and one
#: 1-cell column. :func:`page_frame` lays it out purely to read the sheet's own
#: numbers back, so the probe's extent never reaches any output.
_PROBE_CLUES: Tuple[Tuple[int, ...], ...] = ((1,),)


def page_frame(spec: PageSpec) -> PageFrame:
    """The trim and usable area of a page laid out on ``spec``.

    Raises:
        ValueError: ``spec`` carries no parity, so it lays out a drawing-sized
            image rather than a book page — build it with ``book_page_spec``.
    """
    layout = compute_layout(_PROBE_CLUES, _PROBE_CLUES, spec)
    placement = layout.page
    if placement is None:
        raise ValueError(
            "a book page needs a PageSpec with a parity: build it with book_page_spec"
        )
    return PageFrame(
        width=layout.width,
        height=layout.height,
        left=placement.usable_left,
        top=placement.usable_top,
        right=placement.usable_right,
        bottom=placement.usable_bottom,
    )


def example_line_layout(spec: PageSpec, clue: Tuple[int, ...], length: int) -> Layout:
    """One guide-page line, laid out by COMP-007 on the guide page's sheet.

    :func:`~nonogram.export.layout.compute_layout` is asked for a one-row
    puzzle whose row clue is ``clue`` on a line of ``length`` cells, on
    ``spec`` — the book's own sheet — so the cell pitch, the thin and heavy
    rules, the frame and the clue size are the ones a puzzle on this book's
    page gets. The column clues are placeholders that only give the layout
    its ``length`` columns: the column gutter they occupy is not drawn
    (:func:`draw_example_line`).

    **Generalised by CARD-201** (AC-8): until this card ``clue`` and
    ``length`` were always :data:`WORKED_EXAMPLE_CLUE` and
    :data:`WORKED_EXAMPLE_LENGTH`, read off the module rather than taken as
    arguments — the one worked example the guide page drew. The 2-page
    tutorial draws several different lines (a 10-cell complete line, an
    8-on-10 squeeze, a 3-on-8 mark-spaces line, and more), each its own
    ``(clue, length)`` pair through this same call, so the pair became
    parameters instead of a second hard-wired constant per new diagram. The
    four original worked-example steps pass :data:`WORKED_EXAMPLE_CLUE`/
    :data:`WORKED_EXAMPLE_LENGTH` explicitly now; the signature changed, not
    what that call draws (AC-8 pins the output pixel-identical).

    **CARD-204 note.** This call's only use for ``compute_layout``'s
    placed-page branch is borrowed cell/rule consistency (ADR-0036/R2) —
    :func:`draw_example_line` crops the result tight to its own ink and the
    guide page pastes that crop at a fixed, card-independent position
    (``frame.left``), never at this layout's own ``left``. CARD-204's
    right-alignment change nonetheless moves the guide page's own pixels by
    a small, sub-pixel rounding scatter: ``_boundaries`` rounds each grid
    boundary independently, and that rounding depends on the *absolute*
    anchor's fractional part, which CARD-204's formula changed even though
    nothing about where this diagram ends up on the page did. See
    ``tests/test_book_pdf_memory.py``'s
    ``TestBookPdfMemory_NonDrawingPagesAreByteIdentical`` for the measured
    extent of it (pages 1-2 only, ~15000 px of a 2550x3300 page) and
    CARD-204's own Worktree notes for why it is flagged rather than
    eliminated here (doing so would give this function its own placement
    arithmetic, which G-3 forbids).
    """
    columns = ((0,),) * length
    layout = compute_layout((clue,), columns, spec)
    # A single row: the vertical rules and the frame start at the grid's top
    # instead of running up through the column gutter, and no column clue is
    # written.
    top = layout.grid_top
    return replace(
        layout,
        vertical_lines=tuple(replace(line, start=top) for line in layout.vertical_lines),
        column_clues=(),
        frame=None if layout.frame is None else replace(layout.frame, top=top),
    )


def guide_icon_layout(spec: PageSpec) -> Layout:
    """A single bare cell at the book's own pitch — no clue, no frame (CARD-201).

    :func:`example_line_layout` trims :func:`~nonogram.export.layout.compute_layout`'s
    output to one row with its row clue kept (the worked example always names
    its line's clue). The three cell-state icons (Unknown / Filled / Empty)
    are not a line of a puzzle at all — a bare square, captioned in prose
    beside it rather than numbered — so this trims further: the column clue
    is cleared exactly as :func:`example_line_layout` does, the row clue is
    cleared too, and the frame is dropped so :func:`draw_example_line`'s crop
    starts at the grid's own left edge (``xs[0]``) instead of the row-clue
    gutter's. What is left is the grid's own 1x1 box and nothing else — still
    sized and ruled at this page's cell pitch and rule widths, still reached
    only through ``compute_layout`` (ADR-0036/R2, G-3): no new placement
    arithmetic, only a narrower slice of what it already returns.
    """
    layout = compute_layout(((0,),), ((0,),), spec)
    top = layout.grid_top
    return replace(
        layout,
        vertical_lines=tuple(replace(line, start=top) for line in layout.vertical_lines),
        row_clues=(),
        column_clues=(),
        frame=None,
    )


def draw_example_line(layout: Layout, step: ExampleStep) -> Image.Image:
    """One step of a guide-page line, cropped tight around its ink.

    Filled squares first, then crosses, then the rules and frame over them
    (:func:`_stroke_drawing`, the two-up page's stroking) and the clue numbers
    (:func:`_write_clues`) — the same order a puzzle's answer is drawn in, so a
    heavy rule stays continuous across a filled square. A cross is drawn
    corner to corner at the layout's thin rule.

    The image returned starts at the drawing's left edge (minus a heavy rule
    of white) and at the grid's top edge (minus a heavy rule of white).

    **Already general (CARD-201).** This function reads nothing module-level:
    ``layout``'s own extent (``layout.vertical_lines``/``horizontal_lines``)
    bounds the loops below, so the one-row six-column worked example, a
    10-cell complete line, an 8-on-10 squeeze and a bare 1x1 cell icon
    (:func:`guide_icon_layout`) all draw through this same call — only
    :func:`example_line_layout`'s signature needed generalising (AC-8).
    """
    pad = layout.thick_rule
    xs = [line.position for line in layout.vertical_lines]
    ys = [line.position for line in layout.horizontal_lines]
    left = (layout.frame.left if layout.frame is not None else xs[0]) - pad
    top = layout.grid_top - pad
    canvas = Image.new("RGB", (layout.width, layout.grid_bottom + pad + 1), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    for column in step.filled:
        draw.rectangle((xs[column], ys[0], xs[column + 1], ys[1]), fill=INK)
    for column in step.crossed:
        inset = (xs[column + 1] - xs[column]) // 4
        x0, x1 = xs[column] + inset, xs[column + 1] - inset
        y0, y1 = ys[0] + inset, ys[1] - inset
        draw.line([(x0, y0), (x1, y1)], fill=INK, width=layout.thin_rule)
        draw.line([(x0, y1), (x1, y0)], fill=INK, width=layout.thin_rule)
    _stroke_drawing(draw, layout)
    _write_clues(draw, layout)
    return canvas.crop((left, top, layout.grid_right + pad + 1, layout.grid_bottom + pad + 1))


def wrap_words(text: str, font: Any, measure: int) -> List[str]:
    """``text`` broken greedily at spaces into lines no wider than ``measure``.

    A single word wider than ``measure`` stays on a line of its own.
    """
    lines: List[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}" if current else word
        if current and font.getlength(candidate) > measure:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _clipped_to(text: str, font: Any, measure: int) -> str:
    """``text`` shortened with a trailing ellipsis until it fits ``measure``.

    One line, clipped rather than wrapped — :func:`wrap_words` is for a
    paragraph of several lines, and the two places this is used (a TOC row
    beside its page number, and a solved page's caption line) are each one
    line by definition.

    Extracted for CARD-204 Fix 7, which needs the same clip for a caption
    too wide for its page's usable area at all: the loop below is the one
    :meth:`BookPDFGenerator.create_toc_page` already ran inline since
    CARD-200, moved here unchanged (two characters off, one ellipsis on,
    stopping at a single character so no text can be clipped away entirely),
    so the TOC draws the identical bytes it drew before. A caption cannot be
    *shrunk* to fit instead: ``ANSWER_TEXT_FONT_MM`` already is CON-020's
    10 pt floor for reader-facing interior text.
    """
    clipped = text
    while len(clipped) > 1 and font.getlength(clipped) > measure:
        clipped = clipped[:-2] + "…"
    return clipped


def page_is_right_hand(page_number: int) -> bool:
    """Whether interior page ``page_number`` (1-based) is a right-hand page.

    Parity counts from the interior's page 1, the guide page, which is
    right-hand: odd pages are right-hand, even pages left-hand (FR-043).
    """
    if page_number < 1:
        raise ValueError(f"interior pages are numbered from 1, got {page_number}")
    return page_number % 2 == 1


@lru_cache(maxsize=1)
def default_toc_frame() -> "PageFrame":
    """The TOC's usable area on CON-018's Book 1 profile (CARD-200).

    Used only as the basis for :func:`interior_page_count`'s own
    ``toc_pages`` default — the "called with the count alone" bound its
    docstring already promises for every other optional term
    (:data:`GUIDE_PAGE_COUNT`'s sibling terms). ``page_frame`` on
    ``page_number=1`` is a safe stand-in for *any* interior page's usable
    area here, for the same reason the module's own "early"
    ``first_answer_page`` probe (``interior_stream``) relies on a
    representative spec for a feasibility check: :func:`book_page_spec`'s
    own docstring states that parity moves only the left/right margins, and
    reading its body confirms ``top_mm``/``bottom_mm``/``height_mm`` never
    depend on ``page_number`` at all — so this frame's ``top``/``bottom`` are
    exactly any other page's, not only its width (the premise CARD-200's own
    draft stops short of — it is extended here to height because the TOC's
    split needs it, and verified against the real function body rather than
    assumed).

    A caller that knows the *book's own* trim (:meth:`BookPDFGenerator.section_plan`)
    builds its own frame off ``self.page_spec`` and passes the real
    ``toc_pages`` in instead of relying on this; this default is only ever
    read when nothing else is known — a bare call, or (review cycle 2, F-2)
    :func:`~nonogram.admin.book_kdp.unpaired_interior_page_count`'s own
    genuinely-last-resort fallback, for a book whose trim cannot be read at
    all — not its general path, which measures the book's own stored height
    instead (see that function's own docstring). Public (no longer
    underscore-prefixed) since review cycle 2, F-2, for exactly that cross-
    module reuse: ``book_kdp`` needs this same Book 1 fallback frame, and
    reimplementing it natively there would duplicate :func:`book_page_spec`'s
    own profile-fallback logic rather than reuse it.
    """
    return page_frame(book_page_spec(None, 1))


def _toc_entries_per_page(frame: "PageFrame", dpi: int) -> int:
    """How many :func:`BookPDFGenerator.create_toc_page` rows fit one TOC page.

    Every TOC page repeats :data:`TOC_TITLE` (:func:`BookPDFGenerator.create_toc_page`'s
    own docstring), so one page's entry budget is the frame's usable height
    minus the title's own line and gap, minus one more folio-sized line at
    the bottom, divided by one entry's line height (:data:`TOC_ENTRY_PT` set,
    :data:`TOC_ENTRY_GAP_PT` under it) — a pure division, not a second
    text-layout primitive (G-1): the same :func:`_band_font`/:func:`_guide_face`
    metrics every other page's own fitting already reads, never a value this
    function invents.

    **The folio-sized reservation is load-bearing, not a safety margin.**
    Every TOC page but a short final one is packed to exactly this many
    rows (:func:`BookPDFGenerator.create_toc_page` draws whatever slice it
    is given, never fewer) — unlike a grid page, where the drawing's own
    natural height usually leaves slack below it by chance, a TOC page with
    no such reservation would end with its *own* last entry sitting exactly
    at the bottom margin on every page but the last, which is precisely the
    "slack too small to fit one line" case :func:`_draw_folio` then omits
    the folio for (found by this card's own ``tests/test_book_toc.py``
    while drafting it, not assumed away). Reserving one folio line here
    instead keeps every TOC page's own folio printed, the normal case
    AC-1 asks for, rather than making the TOC the one page kind whose folio
    is routinely missing.

    At least one entry always fits, by floor, the same shape
    :func:`interior_page_count`'s own ``level_dividers`` default already
    uses for its own worst case.

    **The group gaps are deliberately not charged here** (CARD-205).
    :meth:`BookPDFGenerator.create_toc_page` sets :data:`TOC_GROUP_GAP_PT`
    of extra white above each row that opens a group, which is vertical
    space this figure does not know about — so this function stays what its
    name says, a uniform division by one row's height, and does **not**
    become group-dependent (which would make one page's capacity a function
    of its own content, i.e. the second layout primitive G-2 forbids). That
    is sound rather than merely convenient, because the structural list
    cannot reach the split this figure governs:
    :func:`structural_toc_entry_count` is ``2 + 2 * levels`` with at most
    ``len(TIERS)`` levels, i.e. **eight rows with four gaps** (three
    headings and the solutions row — Fix 2), and the shortest trim
    :func:`~nonogram.admin.book_page_spec.book_page_spec` lays out at all
    holds nine rows (ten until CARD-221 lettered the rows in the packaged
    face, which sets them a pixel taller than Arial did) — so the real list is one page on every trim KDP admits,
    with its four gaps and the folio's own reserved line inside the one
    page's own frame (measured, over every tenth of a centimetre from 10 to
    48 cm, by ``tests/test_book_toc.py``'s
    ``TestBookToc_GroupsAreSetOffFromWhatPrecedesThem`` and
    ``tests/test_book_finalise_gutter.py``'s
    ``test_the_structural_toc_is_one_page_on_every_trim_kdp_admits``).

    **The margin that proof leaves is thin and was once spent.** The
    fourth gap put the worst case 18 px *inside* the folio's reserved line
    at Fix 1's 10 pt constant, which is why :data:`TOC_GROUP_GAP_PT` is
    8.5: a fifth gap, or a ninth row, has to be measured here again rather
    than assumed. The sweep asserts the figure, not merely the inequality,
    so it cannot be reintroduced quietly.

    The alternative — folding the worst case in by dividing by
    ``entry_height + group_gap`` — would charge *every* row a gap only a
    group's first row gets, cutting Book 1's own capacity from 41 rows to
    27 and moving :func:`measured_toc_page_count` for all three of its callers
    (the export's own plan, ``book_kdp``'s gutter-band figure,
    :func:`interior_page_count`'s sheet-free bound) to pay for a split the
    structural list never takes. Should a future card list something long
    enough to spill — a per-puzzle appendix, say — that is the decision to
    revisit *then*, with the rows that actually spill in hand.
    """
    title_font = _guide_face(type_px(GUIDE_TITLE_PT, dpi))
    title_ascent, title_descent = title_font.getmetrics()
    title_space = title_ascent + title_descent + type_px(GUIDE_TITLE_GAP_PT, dpi)
    entry_font = _guide_face(type_px(TOC_ENTRY_PT, dpi))
    entry_ascent, entry_descent = entry_font.getmetrics()
    entry_height = entry_ascent + entry_descent + type_px(TOC_ENTRY_GAP_PT, dpi)
    folio_font = _band_font(type_px(FOLIO_PT, dpi))
    folio_ascent, folio_descent = folio_font.getmetrics()
    folio_space = folio_ascent + folio_descent
    available = (frame.bottom - frame.top) - title_space - folio_space
    return max(1, available // entry_height)


def measured_toc_page_count(entry_count: int, frame: "PageFrame", dpi: int) -> int:
    """How many TOC pages ``entry_count`` listing rows need on ``frame``.

    Zero when there is nothing to list (CARD-200) — the same "only when
    there are puzzles" guard the SOLUTIONS divider and the answer section
    already apply, extended to the table of contents that now precedes them:
    a book with no drawable puzzle gets no TOC page at all, rather than one
    page carrying a title and no rows.

    Named ``measured_*`` rather than the bare ``toc_page_count`` every
    caller's own local variable/field already uses (:class:`SectionPlan.toc_page_count`,
    :meth:`BookPDFGenerator.section_plan`'s own local of the same name) —
    a module-level function sharing that exact name would make
    ``toc_page_count = toc_page_count(...)`` raise ``UnboundLocalError``
    inside any method that also assigns a same-named local, Python's normal
    scoping rule for a name a function body assigns anywhere. Public (no
    longer underscore-prefixed) since review cycle 2, F-2:
    :func:`~nonogram.admin.book_kdp.unpaired_interior_page_count` now calls
    this directly on the book's own stored trim, rather than only ever
    through this module's own :func:`interior_page_count` default.

    Raises:
        ValueError: ``entry_count`` is negative.
    """
    if entry_count < 0:
        raise ValueError(f"a table of contents lists 0 or more entries, got {entry_count}")
    if entry_count == 0:
        return 0
    per_page = _toc_entries_per_page(frame, dpi)
    return -(-entry_count // per_page)


def toc_range_label(first: int, last: int) -> str:
    """A level's ``Puzzles N–M`` row label (CARD-205).

    The row that carries the level's own divider page number, under the
    heading that names the level. ``first``/``last`` are 1-based **puzzle
    numbers** (not page numbers): INV-009 groups a book by tier, which is
    the only reason a level's puzzle numbers are a contiguous range at all
    — on an ungrouped order this label would name a span holding other
    levels' puzzles, so this function is only ever fed the runs
    :func:`_level_runs` cut out of :func:`print_order`'s own output.

    A level holding exactly one puzzle reads ``Puzzle 7``, not
    ``Puzzles 7–7``. The owner's sample (Google Doc "Nonograms - Print
    layout", 2026-10-13) only shows the plural case, and nothing in the
    card forces the singular — but a printed book is read, not parsed, and
    ``Puzzles 7–7`` is the kind of thing an owner proof-reading a render
    files as a defect. Handled here, once, rather than left to the caller:
    this is the one place a range becomes words.

    Raises:
        ValueError: the range runs backwards or starts below 1 — a level with
            no puzzle has no row at all (:func:`structural_toc_entries`), so
            an empty range reaching here means the walk that built it is
            wrong, not that the label should be blank.
    """
    if first < 1 or last < first:
        raise ValueError(
            f"a level's puzzle range runs 1 <= first <= last, got {first}..{last}"
        )
    if first == last:
        return f"Puzzle {first}"
    return f"Puzzles {first}{TOC_RANGE_DASH}{last}"


def structural_toc_entry_count(level_count: int, puzzle_count: int) -> int:
    """How many rows the structural table of contents holds (CARD-205).

    The TOC lists **sections, never puzzles** (the owner's decision, Google
    Doc "Nonograms - Print layout", 2026-10-13): one
    :data:`GUIDE_TITLE` row, a heading row plus a ``Puzzles N–M`` row for
    each named non-empty level, and one :data:`TOC_SOLUTIONS_LABEL` row —
    ``2 + 2 * level_count`` rows, independent of how many puzzles the book
    holds. Zero when the book has no drawable puzzle, which is what makes
    :func:`measured_toc_page_count` return no TOC page for it at all
    (CARD-200's own "only when there are puzzles" guard, unchanged).

    **Why a count function and not just ``len(structural_toc_entries(...))``.**
    The entries themselves need the page numbers of the pages they name, and
    those page numbers are not known until the TOC's own length has been
    decided — the TOC sits between the guide and the puzzle section, so its
    page count is a term in every later page's number
    (:meth:`BookPDFGenerator.section_plan`). The count, unlike the entries,
    depends on nothing but the level runs, which are readable from the
    payloads alone; so the split is what breaks that circle rather than a
    convenience. :meth:`BookPDFGenerator.interior_stream` closes the loop
    with a tripwire: the entries it finally builds must re-measure to the
    same page count the plan was laid out on.

    **Both callers of :func:`measured_toc_page_count` are fed by this
    function**, and that is load-bearing rather than tidy:
    :meth:`BookPDFGenerator.section_plan` (the real export, which decides
    where every later page sits) and
    :func:`~nonogram.admin.book_kdp.unpaired_interior_page_count` (whose
    page count feeds KDP's own gutter-margin band). A change to the entry
    rule applied to one and not the other prints a gutter margin for a book
    of a different length than the one actually written — a defect that
    appears in no render, which is why CARD-205's AC-5 cross-checks the two
    directly. :func:`interior_page_count`'s own sheet-free ``toc_pages``
    default is the third reader, through ``level_dividers``' own
    ``min(len(TIERS), puzzle_count)`` bound.

    ``level_count`` is the number of **named** levels with at least one
    printable puzzle — a run of rows stating no readable tier opens no
    divider (:meth:`BookPDFGenerator.puzzle_section`) and so has no page to
    point a row at, exactly as it gets no divider page.

    Raises:
        ValueError: either count is negative.
    """
    if level_count < 0 or puzzle_count < 0:
        raise ValueError(
            f"a book holds 0 or more levels and 0 or more puzzles, got "
            f"{level_count} level(s) and {puzzle_count} puzzle(s)"
        )
    if puzzle_count == 0:
        return 0
    return 2 + 2 * level_count


def structural_toc_entries(
    section: Sequence["SectionPage"],
    payloads: Sequence[ExportPayload],
    solutions_page: int,
) -> List["TocEntry"]:
    """The structural TOC's own rows, read off the page plan (CARD-205).

    Built from the **one** page plan the interior is drawn from
    (:meth:`BookPDFGenerator.puzzle_section`'s own output, carried on
    :attr:`SectionPlan.pages`) rather than from a second walk over the
    puzzles: a level's heading comes from its :class:`DividerPagePlan`'s own
    :attr:`~DividerPagePlan.level` and its row's page number from that same
    divider's :attr:`~DividerPagePlan.page_number`. So a row cannot name a
    page the book does not have, and a level with no divider — an empty one,
    or a run with no readable tier — contributes no row by construction
    rather than by a second "only when there are puzzles" guard written
    here.

    **The puzzle *range* cannot come from "the ``PuzzlePagePlan``\\ s that
    follow the divider" alone, and this is a finding rather than a style
    choice.** :func:`print_order` ranks rows with no readable tier *after*
    all three levels, and such a run opens no divider
    (:meth:`BookPDFGenerator.puzzle_section`) — so in a book that holds one,
    its puzzle pages sit in ``section`` immediately behind the last named
    level's own pages, structurally indistinguishable from them. Collecting
    "every puzzle page until the next divider" would therefore print
    ``Puzzles 121–150`` under *Hard* for a book whose hard run ends at 140
    and whose last ten rows state no tier: a wrong range, in ink, on a page
    no test of the dividers themselves would notice. The ranges are taken
    from :func:`_level_runs` over ``payloads`` instead — the same cut
    :meth:`BookPDFGenerator.puzzle_section` itself planned the dividers from
    — and the two readings are cross-checked against each other below
    (same number of named runs, same levels, same order) rather than
    assumed to agree.

    The rows, in order:

    * :data:`GUIDE_TITLE` against interior page ``1``. The guide opens the
      interior (INV-013: no cover page, the guide is right-hand page 1) and
      runs :data:`GUIDE_PAGE_COUNT` pages, so its *first* page is the one a
      reader is sent to.
    * per named non-empty level, a heading row carrying the level's own
      :attr:`~nonogram.difficulty.Tier.label` and **no page number** — the
      same string :attr:`DividerPagePlan.text` prints on the divider itself
      — followed by a :func:`toc_range_label` row carrying that divider's
      own page number.
    * :data:`TOC_SOLUTIONS_LABEL` against ``solutions_page``.

    ``payloads`` is the book's drawable puzzles in print order, parallel to
    the 1-based puzzle numbers (:attr:`SectionPlan.payloads`) — the same
    list ``section`` was planned from.

    ``solutions_page`` is the SOLUTIONS divider's own interior position
    (``first_answer_page - 1`` in :meth:`BookPDFGenerator.interior_stream`):
    the page that *opens* the answer section is what the reader turns to,
    which is why it and not the first answer page is listed (CARD-205 AC-2).

    Returns the empty list for a book with no printable puzzle — it gets no
    TOC page at all (AC-7, CARD-200's behaviour unchanged). ``len()`` of the
    result equals :func:`structural_toc_entry_count` of the same book;
    :meth:`BookPDFGenerator.interior_stream` asserts **that equality itself**,
    row count against row count, before it lays a page out — and separately
    re-measures the pages those rows take. The row half is the one that
    cannot be inferred from the other: a page count is 1 for anything from
    one row up to the frame's capacity, so the two passes can differ by rows
    and still agree on pages (review cycle 1, F-001: the page comparison
    alone did not notice this function's own count function losing a row).

    Raises:
        RuntimeError: ``section``'s dividers and ``payloads``' own level runs
            disagree on how many named levels the book has, which of them, or
            in what order. Both are derived from the same grouped print order
            by the same call, so this can only fire on a change that broke
            one of the two — and it must fire loudly here rather than print a
            heading against another level's page range.
    """
    if not payloads:
        return []
    dividers = [entry for entry in section if isinstance(entry, DividerPagePlan)]
    runs = [run for run in _level_runs(payloads) if run[0] is not None]
    if [divider.level for divider in dividers] != [level for level, _, _ in runs]:
        raise RuntimeError(
            "the page plan's level dividers "
            f"{[divider.level.value for divider in dividers]} do not match the "
            f"book's own level runs {[level.value for level, _, _ in runs]}"
        )
    # Interior page 1 is the guide's own first page (INV-013: the interior
    # holds no cover page and opens on the guide). A literal, deliberately:
    # the day something is printed *before* the guide, this is the one term
    # here that has to move, and a constant folded into `GUIDE_PAGE_COUNT`
    # would hide that — `interior_stream`'s own `GUIDE_PAGE_COUNT + 1 + index`
    # for the TOC pages and `section_plan`'s `first_page` are its siblings.
    entries: List[TocEntry] = [TocEntry(GUIDE_TITLE, 1)]
    for divider, (level, start, end) in zip(dividers, runs):
        # `_level_runs` cuts half-open slices of `payloads`, and puzzle
        # numbers are 1-based positions in that same list (`interior_stream`'s
        # own `enumerate(payloads, start=1)`), so the run `[start, end)` is
        # puzzles `start + 1 .. end`. A run is never empty by construction.
        entries.append(TocEntry(level.label, None, starts_group=True))
        entries.append(TocEntry(toc_range_label(start + 1, end), divider.page_number))
    # The solutions open the last group, so they are set off like a heading
    # even though they are a numbered row (owner decision 2026-10-14) — see
    # :attr:`TocEntry.starts_group`.
    entries.append(TocEntry(TOC_SOLUTIONS_LABEL, solutions_page, starts_group=True))
    return entries


def interior_page_count(
    puzzle_count: int,
    puzzle_pages: Optional[int] = None,
    answer_pages: Optional[int] = None,
    level_dividers: Optional[int] = None,
    toc_pages: Optional[int] = None,
) -> int:
    """The interior's page count for ``puzzle_count`` rendered puzzles.

    The page plan :meth:`BookPDFGenerator.interior` builds — :data:`GUIDE_PAGE_COUNT`
    guide pages (CARD-201: the 2-page "how to solve" tutorial, FR-041's own
    deferred clause), the table of contents (CARD-200, only when there are
    puzzles to list), one divider per non-empty level, the puzzle pages, then
    (only when there are puzzles) the SOLUTIONS divider and the answer pages;
    never the cover (FR-030 as amended by FR-043).
    ``interior`` checks its own output against this, so a change to the make-up
    of the pages that forgets this function fails loudly instead of shipping a
    book whose stated page count is not its page count.

    Three of the four terms are **measured by the passes that decide them**,
    and each defaults to the un-shortened plan:

    ``puzzle_pages`` is how many pages those puzzles actually take. It is
    ``puzzle_count`` — one page each — until two-up pairing shortens it
    (FR-040).

    ``answer_pages`` is how many pages the answer section actually takes.
    From CARD-198 until CARD-202 it was always ``puzzle_count`` (one full
    solved page per puzzle, no packing); since CARD-202
    :meth:`BookPDFGenerator.interior_stream` passes
    ``len(answer_plan)`` — CARD-202's own packing walk's page count, which
    can be less than ``puzzle_count`` whenever a small answer qualifies to
    pack. The parameter still carries ``puzzle_count`` as its own default
    (an un-shortened upper bound, called with nothing else) rather than
    computing a packing walk itself, which is also why
    :func:`~nonogram.admin.book_kdp.unpaired_interior_page_count` still
    passes it explicitly, deliberately left at the unpacked baseline (see
    that function's own docstring and CARD-202's Worktree notes for why).
    Before CARD-198 this term was the *old* packed key's page count
    (:func:`~nonogram.admin.book_answer_key.pack_answer_pages`, AC-270), which
    on the default 150-puzzle plan took 150 answer pages down to 30 —
    CARD-202's own packing is a narrower, differently-shaped saving (small
    answers only, 2-or-4 to a page, never the old six-up).

    So **called with the count alone this is the un-paired, un-packed plan**:
    the number the Finalise screen has always shown, an upper bound on every
    book, and the "before pairing" half of the saving FR-040 asks the
    generator to report. ``app.py``'s Finalise screen still calls it that way
    and still labels the figure "~" (CARD-129 owns making that count exact,
    EC-034). From CARD-198 until CARD-202 the "before pairing" figure
    differed from the paired one by the two-up pairing term alone; since
    CARD-202 it differs by pairing *and* packing together.

    ``level_dividers`` is how many level divider pages the book opens
    (CARD-128) — one per non-empty named level, measured by the pass that
    decides it (:meth:`BookPDFGenerator.puzzle_section`). It **cannot** be
    derived from ``puzzle_count``: it takes the book's stored tiers, which a
    caller holding only a member count does not have. So left out it is the
    most a book of that many puzzles could open — ``min(3, puzzle_count)``,
    since ADR-0031 has three tiers and a level needs a puzzle in it — which
    keeps "called with the count alone this is an upper bound on every book"
    true of the dividers as it already is of pairing and packing. That bound
    is what the Finalise screen shows as "~"; CARD-129 owns making it exact
    (EC-034).

    ``puzzle_count`` counts puzzles that *render*: :meth:`interior` skips a
    puzzle it cannot build an export payload for, so a count taken from the
    book's members is an upper bound when one of them is broken. That skip is
    the only way the two can differ — a puzzle that builds a payload and then
    will not draw aborts the export with a :class:`RuntimeError` naming it,
    rather than quietly making the file one page shorter than this number.

    ``toc_pages`` (CARD-200, amended by CARD-205) is how many pages the table
    of contents takes — **one row per section** since CARD-205 (the guide,
    each non-empty level's heading and ``Puzzles N–M`` range, the solutions:
    :func:`structural_toc_entry_count`), not one per drawable puzzle, however
    many of them fit a page
    (:func:`measured_toc_page_count`/:func:`_toc_entries_per_page`). Unlike
    ``level_dividers``'s own count-only default, the TOC's split genuinely
    needs a usable height to divide by — a page's own real geometry, which a
    caller holding only ``puzzle_count`` does not have either. Left out, it
    is :func:`measured_toc_page_count` measured on :func:`default_toc_frame` — CON-018's
    Book 1 profile, the same default :class:`BookPDFGenerator` falls back to
    for ``book=None`` — rather than a count-only guess, because a guess could
    as easily under-state the real split as over it (an actual page holds
    anywhere from a handful of rows to several dozen, depending on type size
    and trim, so no single multiplier of ``puzzle_count`` bounds every book
    the way ``min(3, puzzle_count)`` bounds the dividers). This keeps "called
    with the count alone this is an upper bound on every book whose own trim
    is Book 1 or larger" true of the TOC too; a caller that knows the book's
    *own*, possibly smaller, trim (:meth:`BookPDFGenerator.section_plan`)
    always passes its own measured ``toc_pages`` instead of relying on this.
    """
    if puzzle_count < 0:
        raise ValueError(f"puzzle count cannot be negative, got {puzzle_count}")
    pages = puzzle_count if puzzle_pages is None else puzzle_pages
    if pages < 0:
        raise ValueError(f"puzzle page count cannot be negative, got {pages}")
    answers = puzzle_count if answer_pages is None else answer_pages
    if answers < 0:
        raise ValueError(f"answer page count cannot be negative, got {answers}")
    dividers = (
        min(len(TIERS), puzzle_count) if level_dividers is None else level_dividers
    )
    if dividers < 0:
        raise ValueError(f"divider page count cannot be negative, got {dividers}")
    toc = (
        measured_toc_page_count(
            # CARD-205: the structural list's row count, bounded by the same
            # `min(len(TIERS), puzzle_count)` `dividers` is bounded by above —
            # one heading + one range row per level that could have a divider.
            # `dividers` itself is not reused: a caller may pass its own
            # (correct, possibly smaller) divider count, and the TOC's own
            # default must stay an upper bound over every book, not shrink to
            # one caller's book.
            structural_toc_entry_count(min(len(TIERS), puzzle_count), puzzle_count),
            default_toc_frame(),
            DPI,
        )
        if toc_pages is None
        else toc_pages
    )
    if toc < 0:
        raise ValueError(f"TOC page count cannot be negative, got {toc}")
    return (
        GUIDE_PAGE_COUNT + toc + dividers + pages + (answers + 1 if puzzle_count else 0)
    )


def _named_puzzles(
    ids: Optional[List[Any]], numbers: Tuple[int, ...], first_number: int = 1
) -> str:
    """The puzzles of one page, as an aborted export names them.

    One naming rule for every abort :meth:`BookPDFGenerator.interior` can raise
    — a pair that will not lay out, a page that will not draw — because the
    owner searches a 120-puzzle book by the id in the message and nothing else
    (:meth:`BookPDFGenerator.interior`'s ``Raises``).

    ``ids`` is the puzzle ids, parallel to the payloads, so ``numbers`` (1-based
    print numbers) index into it. Without them — :meth:`puzzle_pages` called on
    its own, as a test or a future caller may — the print numbers are named
    instead, which is still the only handle such a caller has.

    ``first_number`` is the print number of ``ids[0]``. It is 1 for the whole
    book and the level's first puzzle when the walk is run over one level at a
    time (:meth:`BookPDFGenerator.puzzle_section`), where the numbers keep
    running 1..n across the levels while ``ids`` is only that level's slice —
    naming the wrong row is worse than naming none, so the offset travels with
    the ids rather than being assumed away.
    """
    if ids is None:
        return ", ".join(f"#{number}" for number in numbers)
    return ", ".join(repr(ids[number - first_number]) for number in numbers)


def _pairable_tier(payload: ExportPayload) -> Optional[Tier]:
    """The tier a payload pairs on, or ``None`` when its row states none.

    :func:`~nonogram.difficulty.tier_of_record` is the one reader of stored
    tier text, so ``"easy"``, ``"Easy"`` and ADR-0031/R3's retired ``"guess"``
    are the tiers they mean rather than three different strings.

    A row whose tier cannot be read has no tier, and **never pairs** — not even
    with another unreadable one. INV-010 lets two puzzles share a page only
    when *their tiers are equal*, and two absences are not an equality: the
    band of such a puzzle already prints "Puzzle 12" and stops
    (:func:`band_identity`), and putting two ungraded puzzles on one page would
    state a sameness the book cannot show the reader.
    """
    return tier_of_record(payload.difficulty)


def _level_runs(
    payloads: Sequence[ExportPayload],
) -> List[Tuple[Optional[Tier], int, int]]:
    """``payloads`` cut into its levels: ``(level, start, end)`` half-open slices.

    A level is a maximal run of consecutive payloads whose tier of record is
    the same (:func:`_pairable_tier`), so on the grouped print order
    (:func:`print_order`) there is one run per non-empty level and none for an
    empty one. ``None`` is a level here as it is everywhere else in this
    module — a run of rows stating no readable tier — and it is the caller that
    decides such a run opens no divider
    (:meth:`BookPDFGenerator.puzzle_section`).
    """
    runs: List[Tuple[Optional[Tier], int, int]] = []
    for index, payload in enumerate(payloads):
        level = _pairable_tier(payload)
        if runs and runs[-1][0] is level:
            runs[-1] = (level, runs[-1][1], index + 1)
        else:
            runs.append((level, index, index + 1))
    return runs


def _answer_extent(payload: ExportPayload, puzzle_number: int) -> Tuple[int, int]:
    """One answer's ``(width, height)`` in cells, read off its solved grid.

    Used since CARD-198 for validation (a row whose columns disagreed with
    its grid must be caught here rather than reaching a renderer that trusts
    the grid alone) **and**, since CARD-202, for packing: this return value
    feeds the ``Answer(width=..., height=...)`` the generator builds for
    :func:`~nonogram.admin.book_answer_key.plan_small_answer_pages`, which is
    what :func:`~nonogram.admin.book_answer_key.qualifies_for_packing` reads.
    Taken from the **grid** rather than from the row's ``width``/``height``
    columns for the same reason it always was: the grid is what is actually
    drawn.

    Reimplemented here rather than imported: ``png._answer_extent`` is private
    to that module and ``export/`` exposes no public call that measures a grid
    on its own — the precedent ``solver/propagate.py``'s ``mask_runs`` sets.
    The two are pinned equal in ``tests/test_book_answer_key.py`` by
    ``TestBookAnswerKey_TheExtentReaderAgreesWithTheRenderer``, which runs both
    readers over the same grids: each measures a well-formed grid the same way,
    and a grid one refuses for its shape the other refuses too. The type check
    below is this module's own and has no counterpart in ``png``: a payload's
    grid comes off a database row, and such a row must be named and refused
    here rather than reaching the renderer as a ``TypeError``.

    **CARD-202 Fix 2** added the clue-agreement check below. The grid check
    above only ever read ``payload.grid`` — a stored row's ``clues_rows``/
    ``clues_cols`` are a *separate* pair of columns (``_payload`` builds
    ``row_clues``/``column_clues`` straight from them, never re-deriving them
    from the grid), so a row with a well-formed square grid but a corrupted
    (e.g. emptied) ``clues_cols`` sailed straight through this function and
    was only ever caught three layers deeper, inside
    :func:`~nonogram.export.layout.compute_packed_solved_layout`'s
    ``_pair_member`` (the build-gate regression this fix closes) — a check
    this function now makes itself, at the same early point CARD-198's own
    eager validation pass already runs, mirroring exactly the check
    :func:`~nonogram.export.layout.compute_layout` and ``_pair_member`` make
    of the same two clue sets (``bool(rows) != bool(columns)``: a grid has
    either both or neither). It can never fire for a well-formed grid — every
    row and every column of a non-empty rectangle encodes to a non-empty clue
    set (a line with no filled cells is ``(0,)``, never ``()``, per the
    project's own boundary-type rule) — so this is strictly a widening of what
    was already validated here, not a behaviour change for any valid puzzle.

    Raises:
        ValueError: the grid is missing, empty, not a sequence of rows, or its
            rows are not all the same length — not a rectangle, so not a
            nonogram's solution; or the stored row and column clue sets
            disagree about whether the grid has any cells at all (one is
            empty while the other is not). The message names the puzzle by
            its print number, which is the handle every other abort of
            :meth:`BookPDFGenerator.interior` is searched by.
    """
    grid = payload.grid
    if not isinstance(grid, (list, tuple)) or not all(
        isinstance(row, (list, tuple)) for row in grid
    ):
        raise ValueError(
            f"puzzle {puzzle_number}'s answer must be rows of cells, not "
            f"{type(grid).__name__}"
        )
    rows = len(grid)
    columns = len(grid[0]) if rows else 0
    if not rows or not columns or any(len(row) != columns for row in grid):
        raise ValueError(
            f"puzzle {puzzle_number}'s answer must be a non-empty rectangular "
            f"grid, not {rows} row(s) of "
            f"{sorted({len(row) for row in grid})} cell(s)"
        )
    row_clue_count = len(payload.row_clues)
    column_clue_count = len(payload.column_clues)
    if bool(row_clue_count) != bool(column_clue_count):
        raise ValueError(
            f"puzzle {puzzle_number}'s clue sets disagree about the grid: "
            f"{row_clue_count} row clue(s) but {column_clue_count} column "
            f"clue(s); a grid has either both or neither"
        )
    return columns, rows


def _packed_page_is_feasible(
    plan: PackedAnswerPage,
    payloads: Sequence[Tuple[Any, ExportPayload]],
    page_spec: PageSpec,
) -> bool:
    """Whether COMP-007 can actually lay ``plan`` out at its own capacity (review F-1).

    :func:`~nonogram.export.layout.compute_packed_solved_layout` returns
    ``None`` exactly when ``plan``'s real clue depths cannot share
    :attr:`~nonogram.admin.book_answer_key.PackedAnswerPage.capacity` slots
    without the shared cell falling below
    :data:`~nonogram.export.layout.MIN_CELL_MM` — the one case that function's
    own docstring says to read as "print these some other way", never as an
    error. ``page_spec``'s parity does not matter here (``book_page_spec``'s
    own docstring: parity moves the margins sideways, never the usable size),
    so one representative spec answers this for whichever interior page
    position ``plan`` ends up printed at.
    """
    members = [payloads[number - 1] for number in plan.numbers]
    clue_pairs = [(payload.row_clues, payload.column_clues) for _, payload in members]
    try:
        layout = compute_packed_solved_layout(clue_pairs, plan.capacity, page_spec)
    except Exception as e:
        # A malformed member (clue sets that disagree about the grid, say) is
        # a different thing from "declines to pack": `compute_packed_solved_layout`
        # answers "no" to a genuine question by returning `None`, never by
        # raising — so an exception here means this page could never be laid
        # out at all, at any capacity, and must abort named rather than be
        # read as "try a lower density" (the same split `puzzle_pages` already
        # keeps between `compute_pair_layout` returning `None` and raising).
        ids = [puzzle_id for puzzle_id, _ in payloads]
        raise RuntimeError(
            f"puzzle {_named_puzzles(ids, plan.numbers)} could not be laid out: {e}"
        ) from e
    return layout is not None


def _degrade_infeasible_packed_pages(
    answer_plan: Sequence[Union[Answer, PackedAnswerPage]],
    payloads: Sequence[Tuple[Any, ExportPayload]],
    page_spec: PageSpec,
) -> List[Union[Answer, PackedAnswerPage]]:
    """Replace a packed page COMP-007 cannot lay out with one it can (review F-1).

    :func:`~nonogram.admin.book_answer_key.plan_small_answer_pages` groups
    answers from their extents alone — it is pure and measures no tile (its
    own module docstring) — so it cannot see that a run's *real* clue depth
    (only the actual grids carry that) will make
    :func:`~nonogram.export.layout.compute_packed_solved_layout` decline a
    packed page: the :data:`~nonogram.export.layout.MIN_CELL_MM` floor would
    otherwise force a slot's drawing to spill into a *neighbouring* answer's
    tile, which is never acceptable (unlike a single puzzle's own ink running
    past its own margin — see that function's docstring, "review F-1").

    This degrades such a page the same way :func:`~nonogram.export.layout.compute_pair_layout`'s
    own "decline, then the caller falls back" contract already works for a
    pair: first the next lower density in the same run (4-up -> two 2-ups),
    and if even a 2-up pair cannot fit without overlap, all the way down to
    CARD-198's original guarantee — each answer on a full page of its own,
    which :func:`~nonogram.export.layout.compute_layout` always builds for
    any puzzle in the supported size range (it has no "decline" verdict at
    all; the single-page tolerance it does keep only ever lets *that*
    puzzle's own ink run past *its own* margin, never another's). A page
    that already fits at its planned capacity is returned unchanged.

    Every answer in ``answer_plan`` reaches the result exactly once, in the
    same order — this only ever splits a page into more, smaller ones; it
    never drops, duplicates or reorders one (checked by the caller's own
    tripwire, the same shape as the one that checks this module's puzzle-page
    walk).

    Args:
        answer_plan: :func:`~nonogram.admin.book_answer_key.plan_small_answer_pages`'s
            own, extent-only plan.
        payloads: Every drawable puzzle's ``(id, ExportPayload)``, indexed by
            1-based print number minus one, the real clue sets this check
            needs and the pure planner never sees.
        page_spec: Any placed book page spec for this book — parity does not
            change the usable size (see :func:`_packed_page_is_feasible`), so
            one spec checks every page position the plan could still use.

    Returns:
        A plan with the same answers, in the same order, where every
        remaining :class:`~nonogram.admin.book_answer_key.PackedAnswerPage`
        is one COMP-007 can actually draw without any two slots' ink
        overlapping.
    """
    degraded: List[Union[Answer, PackedAnswerPage]] = []
    for entry in answer_plan:
        if not isinstance(entry, PackedAnswerPage):
            degraded.append(entry)
            continue
        if _packed_page_is_feasible(entry, payloads, page_spec):
            degraded.append(entry)
            continue
        if entry.capacity == PACKED_TWO_UP:
            # No lower packed density exists: every answer on it prints alone.
            degraded.extend(entry.answers)
            continue
        # A 4-up that cannot pack: try the next lower density, two 2-ups,
        # each checked (and allowed to fail) independently — one half
        # binding tighter than the other is exactly the case this exists for.
        for half in (entry.answers[:2], entry.answers[2:]):
            if not half:
                continue
            if len(half) == 1:
                degraded.append(half[0])
                continue
            pair_page = PackedAnswerPage(half)
            if _packed_page_is_feasible(pair_page, payloads, page_spec):
                degraded.append(pair_page)
            else:
                degraded.extend(half)
    return degraded


# ---------------------------------------------------------------------------
# The generated title cover's lettering (CARD-234, FR-043)
# ---------------------------------------------------------------------------

#: The em square, in device pixels, the generated title cover sets its title
#: in. The number :meth:`BookPDFGenerator.create_cover_page` has always asked
#: for, kept verbatim: how large a cover's title should be is the cover's
#: visual design, which CARD-234 leaves exactly as it found it (G-5). At the
#: 300 DPI every book page is drawn at it is 17.3 pt, and in the packaged face
#: it sets a cap height of 52 px. That cap height is what AC-2 measures off
#: the ink, because until this card the size was silently dropped on any host
#: without Arial and the title came out at 8 px — about a seventh.
COVER_TITLE_PX = 72

#: The first Private Use codepoint. No real face assigns it, so whatever the
#: packaged face draws for it *is* that face's ``.notdef`` box, which is the
#: instrument :func:`_cover_title_face` measures a title against. Verified
#: against the shipped font rather than assumed:
#: ``tests/test_book_cover.py``'s
#: ``test_the_glyph_probe_can_tell_a_missing_glyph_from_a_blank_one``.
_UNASSIGNED_CODEPOINT = "\ue000"


def _cover_title_face(book_title: str) -> ImageFont.FreeTypeFont:
    """The face the generated title cover letters ``book_title`` in.

    The packaged DejaVu Sans at :data:`COVER_TITLE_PX` — :func:`_band_font`,
    the one font this project ships (ADR-0006/R1, package data and not a
    dependency), reused rather than wrapped in a lookup of its own. So the
    cover file, like the interior since CARD-221, is lettered from this
    repository's own font data and from nothing the host's font configuration
    offers.

    **What it replaced** (CARD-234). ``create_cover_page`` asked the host for
    ``/System/Library/Fonts/Arial.ttf`` at 72 px and, on the ``OSError``,
    called ``ImageFont.load_default()`` **with no size**. Two defects that
    compounded: the path exists only on macOS, so the deployed Linux panel
    took the fallback every time; and a sizeless ``load_default()`` drops the
    72 px it was asked for, leaving Pillow's small bitmap face. Measured at
    CARD-221's review (2026-10-14, F-009) and again here: a cap height of 8 px
    where the packaged face sets 52. The title was still centred by its own
    measured bbox, so nothing overflowed and nothing was logged — the one page
    a buyer sees first simply came out at about a seventh of its size.

    **A title the face cannot letter is refused, not substituted** (AC-4, the
    decision this card was asked to make and state). The interior's repertoire
    is bounded and known to be covered glyph by glyph (:func:`_guide_face`); a
    book title is typed by the owner, so its repertoire is not. The packaged
    face covers printable ASCII, Latin-1, Latin Extended, Cyrillic, Greek,
    Hebrew, Arabic and the punctuation a title plausibly carries — measured
    against the shipped file, not assumed. It does not cover CJK, kana,
    hangul, Thai, most emoji or an unassigned codepoint, and for any of those
    FreeType draws ``.notdef`` — an empty rectangle. Printing that is the same silent defect in a new
    costume: the cover is the file KDP prints, bills for and sells, and a row
    of empty boxes is only discovered by a buyer. So the characters are named
    in a :class:`~nonogram.errors.UnletterableTitle` and the owner retypes
    them. Substituting (``?``, ``U+FFFD``, transliteration) was rejected for
    the same reason: it ships a title that is not the title, quietly.

    Whether a glyph exists is asked of the face by **drawing** the character
    and comparing it with the face's own ``.notdef``
    (:data:`_UNASSIGNED_CODEPOINT`), because Pillow exposes no character map.
    A character the face sets as blank — a space, U+200B — renders blank,
    which is not ``.notdef``, so it is letterable and passes; a tab is not,
    and does not (U+0009 has no glyph at all and FreeType boxes it). The
    probe is ``3 x COVER_TITLE_PX`` square with the pen one em in from the
    corner, which no glyph of this face at this size comes close to filling.

    Args:
        book_title: The title to be lettered. Callers pass a title with
            something in it: a blank or all-whitespace title never reaches
            here, because :meth:`BookPDFGenerator.create_cover_page` returns
            the blank page before asking for a face (AC-5).

    Raises:
        ~nonogram.errors.UnletterableTitle: some character of ``book_title``
            has no glyph in the packaged face. The message names each one and
            its codepoint.
    """
    face = _band_font(COVER_TITLE_PX)

    def sample(character: str) -> bytes:
        box = 3 * COVER_TITLE_PX
        probe = Image.new("L", (box, box), 0)
        ImageDraw.Draw(probe).text(
            (COVER_TITLE_PX, COVER_TITLE_PX), character, fill=255, font=face
        )
        return probe.tobytes()

    notdef = sample(_UNASSIGNED_CODEPOINT)
    missing = [
        character
        for character in dict.fromkeys(book_title)
        if sample(character) == notdef
    ]
    if missing:
        named = ", ".join(
            f"{character!r} (U+{ord(character):04X})" for character in missing
        )
        raise UnletterableTitle(
            f"the book title {book_title!r} cannot be set on a cover: the "
            f"packaged face has no glyph for {named}. Retype or remove "
            "those characters."
        )
    return face


class BookPDFGenerator:
    """Generates a book's interior PDF (guide, puzzles, answers) and cover file.

    Args:
        book: The book being exported — anything carrying the ``books`` print
            columns (a :class:`~nonogram.admin.book_manager.Book` or a row).
            ``None`` is a book with no stored print specification, which is
            CON-018's Book 1 profile, exactly as an empty column is
            (:func:`~nonogram.admin.book_page_spec.book_page_spec`).

    Raises:
        ValueError: the book's stored print specification cannot be laid out
            (a trim outside KDP's bounds, a margin below the minimum, a
            non-numeric column) — the message names the column at fault.
    """

    def __init__(self, book: Any = None):
        self.book = book
        self.dpi = DPI  # 300, the resolution COMP-007 measures every page at
        # CARD-147: how this book's interior is printed, read once from the
        # stored column. It decides the interior's colour space and nothing
        # else; the cover file is RGB whatever it says (AC-5, G-4).
        self.ink_mode = book_ink_mode(self.book)
        # The trim, as the layout reports it for this book's sheet. Parity
        # never changes a page's size, so page 1's frame gives it for all.
        frame = page_frame(self.page_spec(1))
        self.page_width_px = frame.width
        self.page_height_px = frame.height

    @property
    def interior_bitmap_mode(self) -> str:
        """The Pillow image mode this book's **interior** pages are written in.

        ``"L"`` for a black-and-white interior, ``"RGB"`` for a colour one
        (CARD-147). The cover file is not an interior page and is always
        ``"RGB"`` (AC-5): :meth:`export_cover` says so at its own call.
        """
        return self.ink_mode.bitmap_mode

    def page_spec(self, page_number: int = 1) -> PageSpec:
        """The book's sheet for interior page ``page_number`` (1-based).

        The one door onto the book's geometry (CARD-115). Page 1 is the guide
        page and is right-hand; each page's parity is its position (FR-043).
        """
        return book_page_spec(self.book, page_number)

    def create_cover_page(self, book_title: str, cover_image: Optional[Image.Image] = None) -> Image.Image:
        """Create cover page image, one trim-size page.

        The cover file is never numbered (FR-043), so it has no parity of its
        own; its page is the trim, and the generated title cover is centred on
        it, which a mirrored margin would not move anyway.

        **The generated title cover is lettered from packaged data**
        (CARD-234): :func:`_cover_title_face` at :data:`COVER_TITLE_PX`, the
        face the interior has used since CARD-221 and the band since CARD-197.
        Until this card the title was set in the host's Arial by path with a
        **sizeless** ``ImageFont.load_default()`` behind a bare ``except
        OSError`` — so off a Mac the cover's title came out at an 8 px cap
        height instead of 52, silently. There is no fallback here now: the one
        face is this repository's, and a title it cannot letter is refused by
        name (see that function, AC-4).

        An uploaded ``cover_image`` is resized and returned untouched by any
        of this: nothing about that path changed (AC-6).

        Args:
            book_title: Title for the book. A blank or all-whitespace title
                is a title with nothing to letter, and its cover is the blank
                page (AC-5) — never a centred ``.notdef`` box, which is what
                a lone tab used to draw.
            cover_image: Optional pre-built cover image

        Returns:
            Cover page as PIL Image

        Raises:
            ~nonogram.errors.UnletterableTitle: the title holds a character
                the packaged face has no glyph for (AC-4). Only the generated
                cover can raise it; an uploaded ``cover_image`` is returned
                before the title is looked at.
        """
        if cover_image:
            # Use provided cover, resized to standard page size
            return cover_image.resize((self.page_width_px, self.page_height_px), Image.Resampling.LANCZOS)

        # Create blank cover with title
        cover = Image.new("RGB", (self.page_width_px, self.page_height_px), "white")
        if not book_title.strip():
            # Nothing to letter, so nothing is drawn (AC-5). Without this, a
            # title of one tab reached the face as a character with no glyph
            # and printed a .notdef box in the middle of an otherwise empty
            # cover; a title of spaces drew nothing but was still measured.
            return cover

        draw = ImageDraw.Draw(cover)
        title_font = _cover_title_face(book_title)

        # Draw title centered on page
        title_bbox = draw.textbbox((0, 0), book_title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.page_width_px - title_width) // 2
        title_y = (self.page_height_px - (title_bbox[3] - title_bbox[1])) // 2

        draw.text((title_x, title_y), book_title, fill="black", font=title_font)

        return cover

    def create_guide_page(
        self,
        puzzle_count: int,
        easy_count: int,
        medium_count: int,
        hard_count: int,
        page_number: int = 1,
    ) -> Image.Image:
        """One page of the 2-page "how to solve" tutorial (FR-041, CARD-201).

        Args:
            puzzle_count: Total number of puzzles
            easy_count: Number of easy puzzles
            medium_count: Number of medium puzzles
            hard_count: Number of hard puzzles
            page_number: Its 1-based position in the interior, **and** which
                half of the tutorial it draws: odd (1) draws page 1 (the
                title :data:`GUIDE_TITLE`, the basic rule, the three cell
                states, "start with certainty" and the original worked
                example); even (2) draws page 2 (:data:`GUIDE2_TITLE`, the
                harder techniques, the difficulty-label box and the closing).
                The two always coincide — the guide is always interior pages
                1 and 2 — so this one parameter carries both meanings rather
                than adding a second that could disagree with it (a STRUCTURE
                decision recorded in this card's Worktree notes). The page's
                margins are mirrored by this same position like any other
                page's (FR-043).

        Three counts, one per tier, since CARD-098 retired ADR-0025's fourth;
        printed on page 2, beside the difficulty-label box they give meaning
        to (CARD-201 moved them off page 1, which is now the basic-technique
        half of the tutorial and has no room left for them).

        **Its type is stated in points** — :data:`GUIDE_BODY_PT`,
        :data:`GUIDE_TITLE_PT`, :data:`GUIDE_LEADING_PT` — and converted to
        the page's pixels once, against :attr:`dpi`, by :func:`type_px`
        (CARD-149). The title is set smaller only when it is wider than the
        usable measure, and never below the body size.

        **Every diagram is one of two shapes.** A line diagram (the basic
        rule's "3 2 1", every :class:`GuideTechnique`'s rows, the original
        worked example) is drawn by :func:`draw_example_line` over a layout
        :func:`example_line_layout` built for that diagram's own clue and
        length (CARD-201 generalised both to take them as arguments, AC-8);
        a bare cell icon (:data:`GUIDE_CELL_STATES`) the same way over
        :func:`guide_icon_layout`. The pipeline and the difficulty legend
        are not puzzle-line diagrams and are drawn by
        :func:`_draw_pipeline_diagram`/:func:`_draw_difficulty_legend`.

        **Five fallback forms, per page — the original three, plus two more
        CARD-201 adds for the 10 cm minimum trim alone:** the full one
        (every heading, every explanation paragraph, every diagram, the
        closing); the captions form (drops the explanation paragraphs and
        the puzzle-count/closing text, keeps every heading, diagram and
        short note); the labels form (headings and diagrams alone, every
        note dropped too); and two more, strictly more aggressive, that drop
        specific diagrams rather than any text below CON-020's floor — see
        :func:`set_page`'s own ``bare_level`` parameter inside this method.
        Whichever is the first whose last mark sits above the bottom margin
        is drawn. A 2-page tutorial is more text than the one page it
        replaces, so the smallest stored trims need this fallback at least
        as much as the original page did (AC-4) — measured (not assumed) to
        need it: the 10 cm minimum trim does not fit even the labels form
        without the two extra levels; every other stored trim (Book 1, 6 x 9
        in) fits one of the original three. See this card's Worktree notes.

        Returns:
            Guide page as PIL Image
        """
        spec = self.page_spec(page_number)
        frame = page_frame(spec)
        guide = Image.new("RGB", (frame.width, frame.height), "white")
        draw = ImageDraw.Draw(guide)
        page_one = page_number % 2 == 1

        # The page's type, stated in points and converted once against the
        # resolution this page is drawn at (CARD-149, AC-236/AC-238). Pillow
        # sizes a face in pixels, so the conversion is the only thing between
        # "11 pt" and the font: at another resolution the pixels change and
        # the printed size does not.
        title_size = type_px(GUIDE_TITLE_PT, self.dpi)
        body_size = type_px(GUIDE_BODY_PT, self.dpi)
        leading = type_px(GUIDE_LEADING_PT, self.dpi)
        measure = frame.right - frame.left
        title_font = _guide_face(title_size)
        text_font = _guide_face(body_size)
        title_text = GUIDE_TITLE if page_one else GUIDE2_TITLE
        # On a narrow trim the title is wider than the measure: set it a pixel
        # smaller at a time until it fits, never below the body size.
        while title_size > body_size and title_font.getlength(title_text) > measure:
            title_size -= 1
            title_font = _guide_face(title_size)

        # Inside the usable area the layout reported, so the guide page keeps
        # the book's mirrored margins like every other interior page.
        draw.text((frame.left, frame.top), title_text, fill="black", font=title_font)

        first = frame.top + type_px(GUIDE_TITLE_GAP_PT, self.dpi)
        ascent, descent = text_font.getmetrics()

        # Every line diagram this page draws, built once regardless of which
        # fallback form is chosen: one `example_line_layout` call per
        # distinct (clue, length) pair, cached so a technique whose rows
        # share a line (the squeeze, the comparison) lays it out once.
        line_layouts: Dict[Tuple[Tuple[int, ...], int], Layout] = {}

        def line_image(clue: Tuple[int, ...], length: int, filled: frozenset, crossed: frozenset) -> Image.Image:
            key = (clue, length)
            layout = line_layouts.get(key)
            if layout is None:
                layout = example_line_layout(spec, clue, length)
                line_layouts[key] = layout
            return draw_example_line(layout, ExampleStep("", "", filled, crossed))

        def technique_rows(technique: GuideTechnique) -> List[Image.Image]:
            return [
                line_image(technique.clue, technique.length, row.filled, row.crossed)
                for row in technique.rows
            ]

        icon_layout = guide_icon_layout(spec)
        # Hoisted above the fallback loop (review cycle 3, F-20): the fit
        # check the loop now runs needs it per attempt, and the final paste
        # loop below needed the same value anyway (F-11) — one computation,
        # not two.
        pad = icon_layout.thick_rule
        cell_state_images = [
            draw_example_line(
                icon_layout,
                ExampleStep(
                    "",
                    "",
                    frozenset({0}) if state.filled else frozenset(),
                    frozenset({0}) if state.crossed else frozenset(),
                ),
            )
            for state in GUIDE_CELL_STATES
        ]
        basic_rule_image = line_image(
            GUIDE_BASIC_RULE_CLUE,
            GUIDE_BASIC_RULE_LENGTH,
            GUIDE_BASIC_RULE_FILLED,
            GUIDE_BASIC_RULE_CROSSED,
        )
        worked_example_layout = line_layouts.setdefault(
            (WORKED_EXAMPLE_CLUE, WORKED_EXAMPLE_LENGTH),
            example_line_layout(spec, WORKED_EXAMPLE_CLUE, WORKED_EXAMPLE_LENGTH),
        )
        worked_example_images = [
            draw_example_line(worked_example_layout, step) for step in WORKED_EXAMPLE_STEPS
        ]
        pipeline_image = _draw_pipeline_diagram(spec, GUIDE_ASSUME_STEPS, text_font, body_size)

        def set_page(
            full: bool, captions: bool, bare_level: int = 0
        ) -> Tuple[List[Tuple[int, Any, bool]], int]:
            """Every mark below the title as ``(y, text or image)``, and the
            lowest pixel they reach.

            ``bare_level`` extends the original three fallback forms
            (CARD-201) with two more, each strictly more aggressive than the
            last, so a page that misses the labels-only form by a handful of
            pixels does not jump straight to the most stripped-down one —
            every stored trim this project ships fits one of these five
            (measured, not assumed — see this card's Worktree notes), the 10
            cm minimum trim needing the last:

            * ``0`` (labels-only, unchanged): every heading, every diagram in
              full, the worked-example recap and the pipeline on page 2.
            * ``1``: a technique with more than one row (the squeeze, the
              region split, the arrangement comparison) draws only its last
              row — the one that states the conclusion, not the reasoning
              that reaches it — and page 2 drops the pipeline diagram and the
              worked-example recap (a restatement of a technique page 1
              already taught in full, not new material).
            * ``2``: also drops page 1's purely illustrative cell-state
              pictures (the heading alone still names "Unknown"/"Filled"/
              "Empty") and page 1's "mark spaces" diagram (heading only), and
              tightens the gaps between sections — never any text below
              CON-020's floor, which no level here touches: only which
              diagrams and gaps are drawn change, never a font size.
            """
            # Each mark carries its own ``needs_pad`` flag (review cycle 2,
            # F-11, gating): only an image built via
            # ``draw_example_line``/``example_line_layout`` bakes in a left
            # bleed-margin of one heavy rule (see that function's own
            # docstring), so only those images may be pasted ``pad`` to the
            # left of their logical position. ``_draw_pipeline_diagram`` and
            # ``_draw_difficulty_legend`` set their own ink flush at column
            # 0 with no such margin — pasting them with the same correction
            # shifted both one heavy-rule-width too far left. A text mark's
            # flag is unused (text is always drawn straight at ``frame.left``)
            # but kept so every mark has the same shape.
            marks: List[Tuple[int, Any, bool]] = []
            state = {"y": first, "bottom": first}

            def paragraph(text: str) -> None:
                for line in wrap_words(text, text_font, measure):
                    marks.append((state["y"], line, False))
                    state["bottom"] = state["y"] + ascent + descent
                    state["y"] += leading

            def picture(img: Image.Image, gap: int, *, needs_pad: bool = True) -> None:
                marks.append((state["y"], img, needs_pad))
                state["bottom"] = state["y"] + img.height
                state["y"] = state["bottom"] + gap

            def space(amount: Optional[int] = None) -> None:
                if amount is None:
                    amount = leading // 6 if bare_level >= 2 else leading // 2
                state["y"] += amount

            def technique(
                entry: GuideTechnique,
                rows: List[Image.Image],
                *,
                draw_diagram: bool = True,
            ) -> None:
                paragraph(entry.heading)
                if full:
                    paragraph(entry.caption)
                if draw_diagram:
                    # Level >= 1 on a technique with more than one row: the
                    # final row is the one that states the technique's
                    # conclusion ("certain" on the squeeze, the ruled-out
                    # cells on the region split) — the intermediate rows are
                    # the reasoning that gets there, droppable before the
                    # conclusion itself is.
                    last_row_only = bare_level >= 1
                    drawn = list(zip(entry.rows, rows))[-1:] if last_row_only else zip(entry.rows, rows)
                    for row, row_image in drawn:
                        picture(row_image, gap=0)
                        if row.note and captions:
                            paragraph(row.note)
                space(0 if bare_level >= 2 else leading // 4)

            if page_one:
                if full:
                    paragraph(GUIDE_INTRO)
                    space()

                paragraph(GUIDE_BASIC_RULE_HEADING)
                if full:
                    paragraph(GUIDE_BASIC_RULE_TEXT)
                picture(basic_rule_image, gap=0)
                if captions:
                    paragraph(GUIDE_BASIC_RULE_CAPTION)
                space()

                paragraph(GUIDE_CELL_STATES_HEADING)
                # Review cycle 3, F-21 (gating): this used to be an
                # all-or-nothing `if bare_level >= 2: pass else: <heading +
                # picture>`, dropping the heading paragraph along with the
                # picture — contradicting this method's own docstring
                # ("the heading alone still names Unknown/Filled/Empty" at
                # this level) and this card's own Fix-1 Worktree notes.
                # `technique()` above gets this right for its own diagrams:
                # the heading is unconditional, and only the diagram is
                # gated (there, by `draw_diagram`). Same shape here: the
                # heading (and, independently, the caption under the
                # existing `captions` flag) always prints; only the picture
                # drops at `bare_level 2`.
                for cell_state, cell_image in zip(GUIDE_CELL_STATES, cell_state_images):
                    paragraph(cell_state.heading)
                    if captions:
                        paragraph(cell_state.caption)
                    if bare_level < 2:
                        picture(cell_image, gap=leading // 4)
                space()

                paragraph(GUIDE_CERTAINTY_HEADING)
                for index, entry in enumerate(GUIDE_TECHNIQUES_1):
                    last = index == len(GUIDE_TECHNIQUES_1) - 1
                    technique(
                        entry, technique_rows(entry),
                        draw_diagram=not (bare_level >= 2 and last),
                    )

                paragraph(GUIDE_SWITCHING_HEADING)
                if full:
                    paragraph(GUIDE_SWITCHING_TEXT)
            else:
                if full:
                    paragraph(GUIDE2_INTRO)
                    space()

                for entry in GUIDE_TECHNIQUES_2:
                    technique(entry, technique_rows(entry))

                paragraph(GUIDE_ASSUME_HEADING)
                if full:
                    paragraph(GUIDE_ASSUME_TEXT)
                if bare_level < 1:
                    # No left bleed margin (``_draw_pipeline_diagram`` draws
                    # its own border flush at column 0) — paste unadjusted.
                    picture(pipeline_image, gap=leading // 4, needs_pad=False)
                if full:
                    paragraph(GUIDE_ASSUME_CLOSING)
                space()

                paragraph(GUIDE_DIFFICULTY_HEADING)
                legend_image = _draw_difficulty_legend(
                    GUIDE_DIFFICULTY_LABELS, measure, text_font, body_size
                )
                # No left bleed margin (``_draw_difficulty_legend`` sets its
                # first column flush at column 0, spanning the full
                # ``measure``) — paste unadjusted. It no longer varies with
                # ``captions``: since CARD-221 fix 1 there is one form of it,
                # the three names, on every fallback level.
                picture(legend_image, gap=leading // 2, needs_pad=False)

                if full:
                    paragraph(f"This book contains {puzzle_count} puzzles:")
                    paragraph(f"Easy: {easy_count}")
                    paragraph(f"Medium: {medium_count}")
                    paragraph(f"Hard: {hard_count}")
                    space()

                # CARD-167's original worked example (G-1: unchanged content,
                # wording and pixel output) — "one of several worked examples
                # on the 2-page tutorial now, not replaced" (G-1's own
                # wording). Placed here, at the close of page 2, rather than
                # among page 1's new content: measured (not assumed) to be
                # the fit that lets page 1's own, newly-added material (the
                # basic rule, the three cell states and three "start with
                # certainty" techniques) reach its own best fallback form on
                # every stored trim, Book 1 included — see this card's
                # Worktree notes, STRUCTURE. Dropped first at ``bare_level``
                # 1: it is a recap of a technique page 1 already taught in
                # full, not new material.
                if bare_level < 1:
                    if captions:
                        paragraph(GUIDE_EXAMPLE_HEADING)
                    for step, step_image in zip(WORKED_EXAMPLE_STEPS, worked_example_images):
                        paragraph(step.caption if captions else step.label)
                        picture(step_image, gap=leading // 2)
                    space()

                paragraph(GUIDE_CLOSING_HEADING)
                if full:
                    paragraph(GUIDE_CLOSING)

            return marks, state["bottom"]

        def fits_width(marks: List[Tuple[int, Any, bool]]) -> bool:
            """Whether every image ``marks`` holds stays inside ``frame.right``.

            Review cycle 3, F-20 (gating): this loop used to accept the
            first fallback level whose last mark cleared the bottom margin
            without ever checking any mark against the RIGHT margin —
            ``_draw_pipeline_diagram`` sizes its own canvas purely from
            label widths and fixed padding/arrow constants, with nothing
            clamping or wrapping that width against this page's usable
            ``measure``, so on a trim narrow enough to overflow but tall
            enough to still pass the only check that existed (10 cm wide x
            25 cm tall: frame.right=1031 on a measure of 918, the pipeline's
            own ink reaching column 1180 of an 1181 px canvas), the
            oversized diagram was never dropped.

            Rather than teach ``_draw_pipeline_diagram`` to clamp or wrap
            its own layout, this extends the loop's existing accept/retry
            mechanism — the one that already handles the vertical case — to
            the horizontal one: a mark that doesn't fit at one level fails
            this check, the loop tries the next, strictly more aggressive
            level, and the pipeline diagram (the one mark wide enough to
            ever trigger this) is dropped outright from ``bare_level 1``
            onward (``set_page``'s own ``bare_level < 1`` gate), which is
            always narrow enough to fit — the same way the vertical check
            already relies on more aggressive levels drawing less.

            A text mark is skipped: :func:`wrap_words` already wraps every
            paragraph to ``measure`` before it is ever added to ``marks``,
            so a text mark cannot overflow by construction and checking it
            here would only re-verify that function, not this loop.

            A ``needs_pad`` (line-diagram) mark is allowed to cross
            ``frame.right`` by up to half a heavy rule: :func:`_stroke_drawing`
            centres a frame's border *on* its boundary coordinate "so Pillow
            centres it there and half a heavy rule hangs outside the box, as
            the grid's own outer border already does" (that function's own
            docstring) — the same by-design sideways bleed every puzzle
            page's own grid already has, not a defect this finding is about.
            ``_draw_pipeline_diagram``/``_draw_difficulty_legend``
            (``needs_pad`` ``False``) draw flush at column 0 with no such
            bleed and get none of this tolerance.
            """
            for _y, mark, needs_pad in marks:
                if isinstance(mark, str):
                    continue
                x = frame.left - pad if needs_pad else frame.left
                bleed = (pad + 1) // 2 if needs_pad else 0
                if x + mark.width > frame.right + bleed:
                    return False
            return True

        for full, captions, bare_level in (
            (True, True, 0),
            (False, True, 0),
            (False, False, 0),
            (False, False, 1),
            (False, False, 2),
        ):
            marks, bottom = set_page(full, captions, bare_level)
            if bottom <= frame.bottom and fits_width(marks):
                break
        # A line diagram's own image starts a heavy rule's width (``pad``)
        # before its logical left edge (:func:`draw_example_line`'s own
        # docstring: "starts at the drawing's left edge... minus a heavy
        # rule of white"), so it must be pasted that same distance left of
        # ``frame.left`` for its logical content — not its own blank
        # bleed-margin — to land where the text above and below it does.
        # Text has no such margin and is drawn straight at ``frame.left``.
        # Measured while building this card: pasting every diagram at
        # ``frame.left`` unadjusted (as the single-diagram original page
        # did, where it never reached any stored trim's right edge) shifts
        # a wide diagram's ink a heavy rule further right than its own
        # caption text — invisible until a 10-cell line with a 3-digit
        # clue, at the 10 cm minimum trim, crossed the usable area's own
        # right edge because of it.
        #
        # Review cycle 2, F-11 (gating): that correction belongs ONLY to
        # images with this bleed margin. ``_draw_pipeline_diagram`` and
        # ``_draw_difficulty_legend`` draw their own ink flush at column 0
        # (no bleed at all) and set their own mark's ``needs_pad=False`` at
        # the ``picture()`` call site above — applying the same ``pad``
        # shift to them landed both one heavy-rule-width too far left,
        # into the inner gutter margin on Book 1's right-hand page and
        # further into the already-tight 10 cm minimum trim's margin.
        # ``pad`` itself is computed above, before the fallback loop (review
        # cycle 3, F-20 needed it there too, for ``fits_width``).
        for y, mark, needs_pad in marks:
            if isinstance(mark, str):
                draw.text((frame.left, y), mark, fill="black", font=text_font)
            else:
                x = frame.left - pad if needs_pad else frame.left
                guide.paste(mark, (x, y))

        # CARD-200: the folio, after every mark above — `bottom` is the
        # chosen fallback form's own lowest mark (the loop above that picked
        # it), never re-measured, so a tight fallback on a small trim omits
        # the folio exactly when it would otherwise collide with this page's
        # own last line (AC-1's "too small a slack" clause), the same
        # omit-rather-than-collide discipline CARD-197 set for the answer
        # caption, without re-selecting which of the five fallback forms
        # above was drawn (G-3: the content above the footer band is
        # unedited by this card).
        _draw_folio(
            draw, frame.left, frame.top, frame.right, frame.bottom, page_number, self.dpi,
            content_bottom=bottom,
        )
        return guide

    def create_divider_page(self, page_number: int, text: str = "SOLUTIONS") -> Image.Image:
        """A divider page: one word on the book's trim, one page (TERM-031).

        Both dividers the interior holds, because they are the same page: the
        "SOLUTIONS" page that opens the answer key (AC-292, the default) and
        the "Easy" / "Medium" / "Hard" page that opens a level (AC-254,
        CARD-128). Its ``text`` is **the only thing on it** — no band, no page
        number, no drawing, nothing fitted (G-3, ADR-0036/R2).

        Its word is centred on the trim, so ``page_number`` decides its size
        and nothing else — but it is taken, not assumed, because the divider
        is an interior page like any other and its position is where a page's
        parity comes from (FR-043).

        **Since CARD-200, one more mark: the folio.** "No band, no page
        number... nothing fitted" above is G-3's statement about the divider
        word itself, unedited by this card; the folio is drawn from outside
        that one word's own geometry, at the frame's own bottom-outer corner
        (:func:`_draw_folio`), after it, never adjusting where the centred
        word sits.
        """
        frame = page_frame(self.page_spec(page_number))
        divider = Image.new("RGB", (frame.width, frame.height), "white")
        draw = ImageDraw.Draw(divider)
        divider_font = _guide_face(type_px(DIVIDER_PT, self.dpi))

        bbox = draw.textbbox((0, 0), text, font=divider_font)
        x = (frame.width - (bbox[2] - bbox[0])) // 2
        y = (frame.height - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), text, fill="black", font=divider_font)
        _draw_folio(
            draw,
            frame.left,
            frame.top,
            frame.right,
            frame.bottom,
            page_number,
            self.dpi,
            content_bottom=y + bbox[3],
        )
        return divider

    def create_toc_page(
        self, entries: List["TocEntry"], page_number: int
    ) -> Image.Image:
        """One page of the table of contents: each row against its own interior page (CARD-200, CARD-205).

        ``entries`` is **this page's own slice** — :class:`TocEntry` rows in
        book order — already split by :meth:`interior_stream`'s own planning
        pass (:func:`measured_toc_page_count`/:func:`_toc_entries_per_page`,
        read off the same frame this method itself builds), so this method
        draws whatever it is handed and never re-decides how many rows share
        a page: one source of truth for the split, not two.

        **Since CARD-205 the rows are sections, not puzzles**
        (:func:`structural_toc_entries`): the guide, each non-empty level's
        heading and ``Puzzles N–M`` range, and the solutions. This method
        does not know that — it draws a label, optionally a page number, and
        the leaders between them — but two consequences of it are visible
        here: a row whose :attr:`TocEntry.page` is ``None``
        (:attr:`TocEntry.is_heading`) prints its label alone, with no number
        and no leaders, and no title lookup happens anywhere on this path
        any more (CARD-200 captioned each row through
        :func:`~nonogram.admin.book_answer_key.answer_caption`; the
        structural list names no puzzle at all, which is why that function
        and ``answer_title`` are now read only by the answer pages — G-3).

        **A row that opens a group is set a group's gap below the row above
        it** (:data:`TOC_GROUP_GAP_PT`, owner decisions 2026-10-14): the
        extra white the owner's sample shows between its groups, drawn as a
        fixed figure added to this method's own pen position rather than as
        a blank row — the entries this method is handed are exactly the rows
        :func:`structural_toc_entries` built, and every one of them is one
        line of :data:`TOC_ENTRY_PT` high, so neither the row count nor
        :func:`_toc_entries_per_page`'s uniform division changes (G-2).
        The page's first row never gets it (there is no group above it to
        separate from), so the list still starts exactly where CARD-200's
        did, one :data:`GUIDE_TITLE_GAP_PT` under the title.

        Which rows those are is read off :attr:`TocEntry.starts_group`, a
        flag the entries arrive carrying, and deliberately **not** off
        :attr:`TocEntry.is_heading`: the ``Solutions`` row is numbered and
        still opens a group (Fix 2). This method therefore does not decide
        what a group is — it draws the separation the list already declares,
        which is also why a future section can open a group without this
        method learning its name.

        **Leader dots** fill the gap between a label and its page number, so
        the eye carries across a short label to a number at the far margin —
        which a six-row list on a 13 cm wide page needs far more than
        CARD-200's dense per-puzzle listing did. The run is a repeated
        ``.`` measured in :func:`~PIL.ImageFont.FreeTypeFont.getlength` and
        **clipped to the measured gap**, keeping :data:`TOC_ENTRY_GAP_PT` of
        clearance from the label on its left and from the number on its
        right, so the dots touch neither side (AC-6); a row whose label
        leaves no room for even one dot simply gets none. No new text-layout
        primitive: this is the same font-metric measuring every other page's
        own fitting already does (ADR-0036/R2, G-2).

        Drawn the same way :meth:`create_guide_page`/:meth:`create_divider_page`
        are: :func:`page_frame` for the usable area, :func:`_guide_face`/
        :func:`type_px` for its type. Every TOC page repeats
        :data:`TOC_TITLE` (unchanged by CARD-205 — G-5 keeps the title, the
        type sizes and the TOC's position out of scope), so a multi-page TOC
        reads as one list continuing rather than several unlabelled pages,
        and so that :func:`_toc_entries_per_page`'s own entries-per-page
        figure — measured once, off the title's own height, for *every* TOC
        page — stays true of this one too.

        A label too wide to sit beside its own page number on one line is
        clipped, with a trailing ellipsis (:func:`_clipped_to` — this
        method's own inline loop until CARD-204 Fix 7 extracted it for the
        solved caption's own over-wide case, unchanged), rather than wrapped
        (:func:`wrap_words` is for a paragraph of several lines; a listing
        row is one line by definition) or left to overlap the number it
        would otherwise share the row with. It cannot fire for any row
        :func:`structural_toc_entries` builds on any trim CON-018 stocks —
        the longest is :data:`GUIDE_TITLE`, about a fifth of the usable
        width — and is kept because this method draws what it is handed and
        a future section's name is not this card's to bound.

        Ends with the same bottom-outer-corner folio every interior page
        carries (:func:`_draw_folio`) — the TOC is front matter inside the
        interior, not an exception to FR-043's "cover never numbered" rule
        (only the cover itself is exempt). It still prints on the now
        single-page TOC for the reason it printed on CARD-200's packed
        multi-page one: :func:`_toc_entries_per_page` reserves a folio-sized
        line at the bottom of *every* TOC page, a reservation this card's
        much shorter list makes no less load-bearing (G-1).
        """
        spec = self.page_spec(page_number)
        frame = page_frame(spec)
        page = Image.new("RGB", (frame.width, frame.height), "white")
        draw = ImageDraw.Draw(page)
        measure = frame.right - frame.left

        title_font = _guide_face(type_px(GUIDE_TITLE_PT, self.dpi))
        draw.text((frame.left, frame.top), TOC_TITLE, fill="black", font=title_font)
        title_ascent, title_descent = title_font.getmetrics()
        y = frame.top + title_ascent + title_descent + type_px(GUIDE_TITLE_GAP_PT, self.dpi)

        entry_font = _guide_face(type_px(TOC_ENTRY_PT, self.dpi))
        entry_ascent, entry_descent = entry_font.getmetrics()
        # One gap constant, read once, used on both axes: under a row
        # (`line_height`, exactly as CARD-200 set it — `_toc_entries_per_page`
        # divides by this same figure, so the two must not drift) and beside
        # a row's leader dots (see :data:`TOC_ENTRY_GAP_PT`).
        gap = type_px(TOC_ENTRY_GAP_PT, self.dpi)
        line_height = entry_ascent + entry_descent + gap
        # The separation between two groups of the list (CARD-205): white
        # above a row that opens one, never a row of its own and never a
        # second row height — see :data:`TOC_GROUP_GAP_PT`.
        group_gap = type_px(TOC_GROUP_GAP_PT, self.dpi)
        dot_width = entry_font.getlength(".")

        bottom = y
        for index, entry in enumerate(entries):
            if entry.starts_group and index > 0:
                # This row opens a group, so it is set a group's gap below
                # whatever the group above it ended with — `starts_group`,
                # not `is_heading`: `Solutions` is a numbered row that opens
                # the last group (Fix 2). Suppressed for the page's
                # **first** row, where there is no group above to separate
                # from: the gap would then only push the list away from the
                # title this page already set its own `GUIDE_TITLE_GAP_PT`
                # under — and would spend, on padding, room the folio's own
                # reserved line is counting on (`_toc_entries_per_page`,
                # G-1). The structural list never opens a page with such a
                # row (its first row is the guide), but this method draws
                # what it is handed.
                y += group_gap
            if entry.is_heading:
                # A level heading: its own row, label only. No number to
                # right-align and therefore nothing for leaders to lead to.
                clipped = _clipped_to(entry.label, entry_font, measure)
                draw.text((frame.left, y), clipped, fill="black", font=entry_font)
            else:
                number_text = str(entry.page)
                number_width = entry_font.getlength(number_text)
                # Two gaps, not CARD-200's one: the label must clear the
                # number by the leaders' own clearance at both ends, so that
                # a label long enough to be clipped is still clipped short of
                # where a dot could sit rather than up against the number.
                label_measure = measure - number_width - 2 * gap
                clipped = _clipped_to(entry.label, entry_font, label_measure)
                draw.text((frame.left, y), clipped, fill="black", font=entry_font)
                draw.text(
                    (frame.right, y), number_text, fill="black", font=entry_font, anchor="ra"
                )
                # The gap the dots may occupy, measured off what was actually
                # drawn (the *clipped* label) rather than off the label as it
                # arrived — an ellipsised label is narrower, and leaders that
                # started where the full label would have ended would leave a
                # hole in the row.
                dot_left = frame.left + entry_font.getlength(clipped) + gap
                dot_right = frame.right - number_width - gap
                run = dot_right - dot_left
                # The division is a **first estimate, corrected both ways**,
                # never the verdict. A repeated glyph's measured run need not
                # be its own advance times its count — a face with a kerning
                # pair for ".." (or plain floating-point drift at this size)
                # makes it slightly narrower or wider — so the string itself
                # is measured: trimmed while it overruns the gap, grown while
                # another dot would still fit. Correcting only downwards (the
                # obvious half) would silently drop a dot on any face whose
                # kerning is negative. That used to differ between Arial and
                # `_guide_face`'s own fallback, and so between one machine's
                # render and another's; since CARD-221 there is one face, and
                # the correction stays because it is a property of a face's
                # kerning rather than of which face was found.
                dots = "." * max(0, int(run // dot_width)) if dot_width > 0 else ""
                while dots and entry_font.getlength(dots) > run:
                    dots = dots[:-1]
                while dot_width > 0 and entry_font.getlength(dots + ".") <= run:
                    dots += "."
                if dots:
                    draw.text((dot_left, y), dots, fill="black", font=entry_font)
            bottom = y + entry_ascent + entry_descent
            y += line_height

        _draw_folio(
            draw, frame.left, frame.top, frame.right, frame.bottom, page_number, self.dpi,
            content_bottom=bottom,
        )
        return page

    def export_book(
        self,
        puzzles: List[dict],
        book_title: str,
        cover_image: Optional[Image.Image] = None,
    ) -> BookExport:
        """Export a book as its two files: the interior PDF and the cover file.

        The one entry point every export route goes through (FR-043, INV-013).
        The interior holds no cover page — its pages 1-2 are the guide
        (CARD-201's 2-page tutorial, ``GUIDE_PAGE_COUNT``) — and
        the cover file is a single page at the book's page size holding the
        uploaded ``cover_image`` when one is given, otherwise the generated
        title cover. Front cover only: the KDP cover wrap (spine, back cover,
        bleed) is deferred.

        Args:
            puzzles: List of puzzle dicts (from puzzle_review service), in
                book order
            book_title: Title for the book (the generated cover's text)
            cover_image: The uploaded front-cover image, if one is set

        The trim is the ``book`` this generator was built for (CARD-116), not
        a pair of loose strings: the two ``trim_*_cm`` arguments this method
        used to take were informational only, and a second way to state the
        sheet is a second sheet waiting to disagree with the one every page is
        laid out on.

        Returns:
            :class:`BookExport` — both files, the interior's page count, what
            it would have been without two-up pairing (FR-040), and how many
            of its pages are answer pages (FR-042).

        The three counts come off the **page plan**, not off a list of built
        pages: :meth:`interior_stream` knows all three before a page is drawn,
        so reporting them costs nothing and the interior is never materialised
        to be counted (CARD-145).

        The interior is finished **before** the cover page is built, and the
        two are written as two statements rather than as two arguments of one
        ``BookExport(...)`` call — that reads better, and nothing more should
        be read into it. **The order is not what keeps a cover page from being
        alive beside an interior page** (card item 3, failure matrix F-6), and
        neither is :meth:`_cover_page` being a generator. What keeps them
        apart is that no page escapes the :meth:`export_cover` call at all:
        :meth:`_write_pdf` retains no page after writing one and hands back a
        ``BytesIO``, and :attr:`BookExport.cover` is that ``BytesIO``, not an
        :class:`~PIL.Image.Image`. Mutation-measured, each of — swapping the
        two statements, folding them back into one ``BookExport(...)`` call
        with ``cover=`` evaluated first, and making :meth:`_cover_page` eager
        with the cover built first — still peaks at one page bitmap. What
        would double the peak is *this* method binding a page itself: a
        ``cover_page = self.create_cover_page(...)`` held across the interior
        write measures 2.00 page bitmaps and fails
        ``test_the_whole_book_holds_one_page_bitmap_at_a_time``. The four
        ``del page`` sites this card added pin the **interior** half of the
        bound (F-1) — consecutive pages of a multi-page walk — not this one.
        """
        stream = self.interior_stream(puzzles)
        interior = self._write_pdf(
            stream.pages, stream.page_count, mode=self.interior_bitmap_mode
        )
        cover = self.export_cover(book_title, cover_image)
        return BookExport(
            interior=interior,
            cover=cover,
            interior_page_count=stream.page_count,
            unpaired_interior_page_count=stream.unpaired_page_count,
            answer_page_count=stream.answer_page_count,
        )

    def export_interior(self, puzzles: List[dict]) -> BytesIO:
        """The interior PDF alone — :meth:`export_book`'s ``interior``.

        For a route that serves only the interior: it renders no cover page.
        One page of it is alive at a time (CARD-145) — this goes through
        :meth:`interior_stream`, never through :meth:`interior_pages`, whose
        list is exactly what a book cannot afford.
        """
        stream = self.interior_stream(puzzles)
        return self._write_pdf(
            stream.pages, stream.page_count, mode=self.interior_bitmap_mode
        )

    def export_cover(
        self, book_title: str, cover_image: Optional[Image.Image] = None
    ) -> BytesIO:
        """The cover file alone — :meth:`export_book`'s ``cover``.

        One page: ``cover_image`` when given, else the generated title cover.
        It renders no interior page, so a cover download costs one page.

        One page is not the memory problem CARD-145 is about, but it takes the
        same path as the interior all the same, and the page it draws does not
        escape this call: :meth:`_write_pdf` retains no page after writing one
        and returns a ``BytesIO``. That, and not the order :meth:`export_book`
        calls it in, is why a cover file never holds a page beside the
        interior's (failure matrix F-6). For a one-page file the ``del page``
        in the writer's loop does nothing at all — it only matters between
        consecutive pages of a multi-page walk, which is the interior's half
        of the bound (F-1).
        """
        # ``mode="RGB"``, stated here and not read off the book: the cover is
        # a separate file (FR-043, CARD-135) holding an uploaded image that
        # may be anything, so a black-and-white **interior** leaves a colour
        # cover in colour (CARD-147 AC-5, G-4).
        return self._write_pdf(
            self._cover_page(book_title, cover_image), 1, mode="RGB"
        )

    def _cover_page(
        self, book_title: str, cover_image: Optional[Image.Image] = None
    ) -> Iterator[Image.Image]:
        """The cover file's one page, as the iterable :meth:`_write_pdf` takes.

        A generator, so the page is built when the writer asks for it — but
        nothing in the memory bound rests on that: an eager version returning
        ``[self.create_cover_page(...)]`` measures the same one page bitmap
        (failure matrix F-6).
        """
        yield self.create_cover_page(book_title, cover_image)

    def generate_book_pdf(
        self,
        puzzles: List[dict],
        book_title: str,
    ) -> BytesIO:
        """The book's interior PDF alone — :meth:`export_book`'s ``interior``.

        Kept for callers that want only the interior. It carries no cover
        page, so there is no way left to produce the old single file whose
        page 1 was the cover (FR-043).
        """
        return self.export_interior(puzzles)

    @staticmethod
    def _payload(puzzle: dict) -> ExportPayload:
        """One book puzzle as the export's boundary type — the row, as it is.

        The *record* payload: it carries the puzzle's own name and its stored
        tier text, in the spelling the row holds them. Neither reaches a page
        in that form. :meth:`_banded` turns this into the two payloads a page
        is actually drawn from, once the puzzle's print position is known, and
        that position is handed out only after a row has proved it can build a
        payload at all (:meth:`interior_pages`) — which is why the band text is
        not composed here.
        """
        clues_rows = puzzle.get("clues_rows", [])
        clues_cols = puzzle.get("clues_cols", [])
        return ExportPayload(
            grid=puzzle.get("grid", [[]]),
            row_clues=tuple(tuple(row) for row in clues_rows) if clues_rows else (),
            column_clues=tuple(tuple(col) for col in clues_cols) if clues_cols else (),
            seed=0,  # Seed for reproducibility (not available from book puzzles)
            mode="random",  # Mode (not available from book puzzles)
            width=puzzle.get("width"),
            height=puzzle.get("height"),
            name=puzzle.get("puzzle_name"),
            difficulty=puzzle.get("difficulty_tier"),  # Display name, not score
        )

    @staticmethod
    def _puzzle_payload(payload: ExportPayload, puzzle_number: int) -> ExportPayload:
        """``payload`` as its puzzle page is drawn from (ADR-0037/R1).

        Two changes to the record payload: the band becomes
        :func:`band_identity`'s line for ``puzzle_number``, and the picture's
        name is **cleared**. The clearing is the whole mechanism by which no
        title is drawn on a puzzle page — the export sets the non-empty header
        fields and nothing else
        (:func:`~nonogram.export.pdf.header_parts`), so a page whose payload
        has no name has no title to leave off.

        The title still has nowhere else to go on *this* page: it reaches the
        reader once, as the caption under the puzzle's own full solved answer
        page (:func:`~nonogram.admin.book_answer_key.answer_caption`,
        :meth:`solved_puzzle_page`, CARD-198) — never as a header here.
        """
        return replace(
            payload,
            name=None,
            difficulty=band_identity(puzzle_number, payload.difficulty),
        )

    def _blank_page(
        self, payload: ExportPayload, puzzle_number: int, puzzle_page: int
    ) -> Image.Image:
        """One puzzle's blank page, alone on the sheet of *its own* position.

        ``render_pages`` draws a blank page and a solved page from one
        payload; the solved one is dropped here. The puzzle's own full solved
        page is drawn separately, by :meth:`solved_puzzle_page`, at the
        answer section's own interior position — never by keeping *this*
        call's solved half, whose layout is the puzzle page's position, not
        the answer page's (CARD-198). Dropped here rather than in the caller
        so that every page this method returns is a page the interior really
        holds.

        **Since CARD-200, one more mark: the folio.** No caption or any
        other text is ever drawn on this page, but the grid itself can be —
        review cycle 2, F-1 (gating): a blank puzzle page's own cell fitting
        (:func:`~nonogram.export.layout.compute_layout`) can leave **zero**
        vertical slack below the grid when the puzzle is page-fit-bound (a
        30-wide/30-tall grid, row-clue depth 1, column-clue depth 10, on
        Book 1's own trim reproduces it exactly — confirmed by direct
        measurement before this fix, not assumed), in which case drawing the
        folio unconditionally prints it directly over the grid's own bottom
        row. The real ``content_bottom`` therefore has to come from the same
        :class:`~nonogram.export.layout.Layout` ``render_pages`` itself
        computed for this puzzle's clues on this page's spec — recomputed
        here independently (:func:`~nonogram.export.layout.compute_layout`
        is pure and total, so the second call is the same answer, not a
        second implementation) rather than threaded out of ``render_pages``,
        which returns only the two rendered images.
        :func:`~nonogram.export.layout.interior_frame` gives every coordinate
        the furniture sits on (unaffected by which puzzle's clues are drawn,
        since the frame is the spec's own margins and band, not the grid), the
        same reuse :meth:`create_guide_page`/:meth:`create_divider_page`
        already rely on for :func:`page_frame` (G-1); only the vertical-room
        check is new. No horizontal check is needed here (unlike
        :meth:`_two_up_page`'s lower slot): nothing about a single puzzle
        page's own cell fitting makes its vertical slack read zero on *every*
        call the way a two-up page's lower slot does, so the simple
        vertical-only check :meth:`solved_puzzle_page` already uses is
        enough — see :func:`_draw_folio`'s own docstring.

        **Since CARD-222 the page carries the whole frame**, not the folio
        alone: :func:`_draw_page_frame` strokes the header rule, the footer's
        hairline, the grid-size label on the inner side and the folio at the
        footer line's centre. The same ``content_bottom`` the folio's own room
        check was added for now decides the *footer group* — a page-fit-bound
        grid (the 30-wide, column-clue-depth-10 case named above) keeps
        CARD-200's corner folio and gets no footer rule, because a hairline
        across its bottom row is the collision this check exists to avoid.

        **Since CARD-223 the footer also carries the QR icon's two lines.**
        The glyph itself is drawn by ``render_pages`` above, which reads the
        same :func:`~nonogram.export.layout.qr_slot` this method's
        :func:`~nonogram.export.layout.qr_caption` call reads — one pure
        function, so the words are set beside an icon that is really there
        and are omitted on exactly the pages that have no icon (AC-5). The
        link needs the **puzzle's** number, not the page's: a reader typing
        it is after this puzzle, and the two differ on every page of the
        book.
        """
        page_spec = self.page_spec(puzzle_page)
        blank, _ = render_pages(
            self._puzzle_payload(payload, puzzle_number),
            page_spec=page_spec,
        )
        layout = compute_layout(payload.row_clues, payload.column_clues, page_spec)
        placement = layout.page
        draw = ImageDraw.Draw(blank)
        _draw_page_frame(
            draw,
            interior_frame(page_spec),
            puzzle_page,
            self.dpi,
            size_label=grid_size_label(layout.columns, layout.rows),
            content_bottom=None if placement is None else placement.drawing_bottom,
        )
        caption = qr_caption(layout)
        if caption is not None:
            _draw_qr_caption(draw, caption, puzzle_number, self.dpi)
        return blank

    def custom_titles(self) -> Dict[str, str]:
        """The per-book titles the Arrangement step set, ``{puzzle_id: title}``.

        ``books.puzzle_titles`` on whatever object this generator was built
        for, read **defensively and without importing ``book_manager``**: the
        book may be a :class:`~nonogram.admin.book_manager.Book`, a SQLAlchemy
        row, a plain mapping from a route, or ``None``, and a column that is
        empty, ``NULL`` or holding something that is not a mapping is simply a
        book with no custom titles. Keys are stringified, because a puzzle id
        reaches this module as whatever the row holds and the column is keyed
        by its string form (``book_manager.set_puzzle_title``).

        No exception is swallowed to achieve that: the two shapes are told
        apart by :class:`~collections.abc.Mapping` rather than by trying one
        and catching the failure.
        """
        book = self.book
        if book is None:
            return {}
        raw = (
            book.get("puzzle_titles")
            if isinstance(book, Mapping)
            else getattr(book, "puzzle_titles", None)
        )
        if not isinstance(raw, Mapping):
            return {}
        return {str(key): value for key, value in raw.items() if isinstance(value, str)}

    def _two_up_page(
        self, plan: PuzzlePagePlan, payloads: List[ExportPayload]
    ) -> Image.Image:
        """The page two puzzles share, composed from what COMP-007 measured.

        The panel strokes; it does not place (ADR-0036/R2, G-1). Every
        coordinate comes off ``plan.pair``: the two slot
        :class:`~nonogram.export.layout.Layout`\\ s carry the shared cell's
        ruled lines and clue centres, and
        :func:`~nonogram.export.layout.header_band` measures each slot's own
        band from its placement. What this method chooses is the *text* of the
        two bands — "Puzzle N · Tier" for each, in print order, the upper slot
        holding the earlier puzzle — exactly as a single page's band text is
        chosen (:meth:`_banded`).

        The page is drawn rather than rendered because ``export/`` offers no
        call that draws a :class:`~nonogram.export.layout.Layout` it is handed;
        see the module docstring.

        **Since CARD-200, one more mark: the folio, once per page.** Read off
        ``pair.lower.page`` rather than ``pair.upper.page`` — a correction to
        this card's own draft, which suggested the upper slot: reading
        :class:`~nonogram.export.layout.PairLayout`'s own docstring and the
        arithmetic :func:`~nonogram.export.layout.compute_pair_layout` builds
        each slot from shows ``upper.page.usable_bottom`` is the *midline*
        between the two slots, not the page's own bottom margin — it is
        ``lower.page.usable_bottom`` that is the true bottom margin (and,
        algebraically, ``lower.page.drawing_bottom`` always equals it too:
        "whatever height the pair leaves spare falls between the two slots",
        never below the lower one). ``usable_left``/``usable_right`` do not
        differ between the two slots either way (both are placed against
        the page's one shared usable width — **centred** across it since
        CARD-224, which restores FR-032's own clause and ends the flush-outer
        anchor CARD-204 had introduced; each slot's own ``usable_*`` fields
        are identical either way, and since centring the folio reserve no
        longer pulls the lower slot's drawing in at all), so reading all four
        off ``lower.page``
        alone is both correct and sufficient — one call, not a slot-by-slot
        one as the loop above intentionally avoids already.

        **Review cycle 2, F-1 (gating), correcting this card's own first-pass
        reasoning**: "nothing else is drawn in this corner" was wrong — the
        lower slot's own grid *can* reach the usable area's outer (left or
        right) edge at exactly the row the folio sits on, when the pair's
        shared cell is fitted tight enough that the lower slot's drawing has
        no horizontal spare either (confirmed by direct measurement: a
        25-26-column, row-clue-depth-1 pair on Book 1's own trim lands the
        lower slot's drawing flush with both margins, not just the bottom
        one). But the lower slot's *vertical* slack reads zero on **every**
        two-up page, not just a tight one (the algebraic identity above), so
        feeding ``lower.page.drawing_bottom`` back as a plain
        ``content_bottom`` the way :meth:`solved_puzzle_page` does would
        omit the folio from every two-up page in the book — the exact
        over-correction :func:`_draw_folio`'s own docstring warns against.
        ``content_right``/``content_left`` (``lower.page.drawing_right``/
        ``drawing_left``) are passed alongside ``content_bottom`` so
        :func:`_draw_folio` can tell a real corner collision (the drawing
        also has no horizontal room at that exact edge) from the lower
        slot's always-zero vertical slack alone: see that function's own
        docstring for the exact rule.

        **CARD-224: both halves of that corner story are now historical.**
        Centring every slot again leaves the lower slot half its own spare on
        each side, so its drawing is not flat against either margin; and
        CARD-248's footer strip means this page's folio is centred on the
        footer line rather than placed in a corner. ``content_right``/
        ``content_left`` are still passed — the fallback is still reachable
        for a pair built without the strip, and a caller that stopped passing
        them would silently widen the omission rule — but on every page this
        panel actually prints they decide nothing.

        **History (CARD-204 Fix 1/Fix 2, reverted by Fix 3, restored as a
        fixed constant by Fix 4 — owner decision, 2026-10-12, "fixed
        universal reserve"; and CARD-224, which ends the alignment the whole
        mechanism answered).** Under reading (b)'s flush alignment with no
        reserve, ``lower.page.drawing_right``/``drawing_left`` lands
        *exactly* on ``usable_right``/``usable_left`` on **every** two-up
        page, not just when the lower slot happens to be the pair's
        width-binding member — an algebraic identity of the anchor formula
        itself (:func:`~nonogram.export.layout._slot_layout`'s own
        docstring), confirmed directly, not merely observed in one case —
        so this horizontal check would fail, and the folio be omitted, on
        every two-up page in every book. Fix 1 and Fix 2 had
        ``compute_pair_layout`` reserve horizontal room at the lower slot's
        own outer corner (first per-page, then book-level) so the check
        always cleared — but that reserve let a *page/book-specific*
        quantity flip whether two puzzles paired at all (INV-010, cycle-1
        F-1, cycle-2 F-5). Fix 3 removed the reserve entirely, restoring
        INV-010 purity but reintroducing the universal folio loss it was
        meant to fix (cycle-3 F-7) — this method's own prior docstring
        wrongly described the loss as occasional ("whatever natural slack
        the pair's own geometry happens to leave"), the exact
        mischaracterisation that review caught. **Fix 4 passes a fixed,
        page/book-independent pixel reserve into every pairing decision**
        (:meth:`puzzle_pages`'s own docstring), so
        ``lower.page.drawing_right``/``drawing_left`` now carries that
        reserve's worth of real clearance on every two-up page by
        construction, and this method's own call below needs no edit at
        all: it already read the slot's *actual* (not assumed) geometry,
        which now simply has room in it.

        **CARD-222: the frame, and what a two-up page gets of it.** The call
        below goes through :func:`_draw_page_frame`, so this page carries the
        header rule on the same baseline as every other puzzle page (AC-2).
        ``size_label=None`` remains: two slots carry two grid sizes, and
        CARD-226 gives each slot its own.

        **CARD-248: and now the footer group too, which is the whole card.**
        Until this card the page carried **none** of it, and not by an
        exception made for it: the lower slot's drawing bottom *was* the bottom
        margin on every two-up page (the algebraic identity above), so the
        frame's own all-or-nothing footer condition refused the strip and the
        page kept CARD-200's corner folio. The owner's decision of 2026-10-18
        is that the lower puzzle's scannable link "definitely should not be
        lost", so
        :func:`~nonogram.export.layout.compute_pair_layout` is now told to
        reserve one footer strip out of the pair's height
        (``footer_reserve_px``, from :attr:`InteriorFrame.footer_depth`) before
        it fits anything. Three things follow, none of them decided here:
        ``content_bottom`` clears ``footer_rule.y`` so the hairline and the
        **centred folio** are drawn; the strip carries one QR group per puzzle
        (:meth:`_draw_two_up_qr_groups`); and the corner folio and the
        horizontal reserve Fix 4 built for it are untouched, still the
        fallback for a pair laid out without the strip. CARD-226 AC-5's
        requirement that the reserve be unchanged is met: the card adds a
        reservation on the other axis rather than touching that one.
        """
        pair = plan.pair
        if pair is None:  # pragma: no cover - the walk only sends two-up plans here
            raise ValueError(f"page {plan.page_number} is not a two-up page")
        page = Image.new("RGB", (pair.upper.width, pair.upper.height), BACKGROUND)
        draw = ImageDraw.Draw(page)
        # ``strict``: a plan whose numbers and payloads disagree with its two
        # slots is a bug in the walk, and a silently half-drawn page is the
        # one way a book could ship a puzzle nobody printed.
        for slot, number, payload in zip(
            (pair.upper, pair.lower), plan.numbers, payloads, strict=True
        ):
            placement = slot.page
            if placement is None:  # pragma: no cover - PairLayout refuses one
                raise ValueError("a two-up slot must be a placed page")
            _stroke_drawing(draw, slot)
            _write_clues(draw, slot)
            _set_band(
                draw,
                header_band(slot),
                band_identity(number, payload.difficulty),
                placement.usable_right - placement.usable_left,
            )
        footer_area = pair.lower.page
        frame = interior_frame(self.page_spec(plan.page_number))
        _draw_page_frame(
            draw,
            frame,
            plan.page_number,
            self.dpi,
            size_label=None,
            content_bottom=footer_area.drawing_bottom,
            content_right=footer_area.drawing_right,
            content_left=footer_area.drawing_left,
        )
        self._draw_two_up_qr_groups(draw, pair, plan.numbers)
        return page

    def _draw_two_up_qr_groups(
        self,
        draw: ImageDraw.ImageDraw,
        pair: PairLayout,
        numbers: Tuple[int, ...],
    ) -> None:
        """The two QR groups a two-up page's one footer strip carries (CARD-248).

        One group per puzzle — the placeholder icon, the named invitation
        (:func:`qr_group_caption`) and the typed link
        (:func:`qr_link`) — set side by side in the strip
        :func:`~nonogram.export.layout.compute_pair_layout` reserved for them.
        Both are measured on the **lower** slot's extent, because that is the
        one whose ``usable_bottom`` is the sheet's own bottom margin: the
        footer belongs to the page, not to a slot, and the lower slot's box is
        the page's (:class:`~nonogram.export.layout.PairLayout`). The upper
        slot is not asked — CARD-223 asked it, and got a box at the *midline*
        between the two drawings while the lower slot got none at all, which
        is the 3-links-for-4-puzzles defect this card exists to fix.

        **Which side the upper puzzle's group takes, and why: the left, at
        both parities.** A stacked pair of puzzles maps onto a side-by-side
        pair of links, so the two orders have to be reconciled by a rule the
        reader already has; the one they have is reading order. The upper
        puzzle is therefore the group met **first reading left to right** —
        the inner group on an ``ODD`` (right-hand) page, where the row packs
        rightward from the outer margin, and the outer group on an ``EVEN``
        one. The *positions* mirror by parity exactly as every other mark on
        a book page does (FR-030); what does not mirror is which puzzle is
        named first, because a reader does not read a left-hand page
        backwards. Neither group relies on that: each names its own puzzle
        number outright (AC-3), and the order is the redundant second cue.

        **The measure is the real one, the verdict's was a constant.** The
        pitch comes from the widest of the four lines this page actually
        sets, so the row is as far from the spine as these two puzzles'
        numbers allow; the pairing walk's own gate used
        :func:`_qr_group_line_px`'s page-independent ceiling instead, which
        is never narrower, so a page the walk admitted always fits the row
        drawn here (see that function and :meth:`puzzle_pages`).

        **No strip, no groups — the frame's own verdict, read and not
        re-derived.** A pair laid out with no ``footer_reserve_px`` (nothing
        production builds, but what a test or a future caller may hand in)
        leaves its lower slot's drawing on the bottom margin, so
        :func:`~nonogram.export.layout.qr_slot` answers ``None`` and
        :func:`_draw_page_frame` has already fallen back to CARD-200's corner
        folio. This method then draws nothing, which is the same
        omit-rather-than-overlap discipline and the same single verdict
        CARD-223 established. A strip that exists but cannot hold the groups
        is the other case and is a **failure**: the pairing walk refuses such
        a pair before it becomes a page, so reaching here means the two
        disagree.

        Raises:
            ValueError: the footer strip is there but cannot hold this many
                groups. Unreachable from :meth:`puzzle_pages`, which refuses
                such a pair before it becomes a page; raised rather than
                passed over because a two-up page with one link is the defect
                this card exists to remove, not a degradation to accept.
        """
        if qr_slot(pair.lower) is None:
            return
        font = _band_font(type_px(INTERIOR_FOOTER_LINE_PT, self.dpi))
        widest = max(
            math.ceil(font.getlength(text))
            for number in numbers
            for text in (qr_group_caption(number), qr_link(number))
        )
        insets = qr_group_insets(pair.lower, widest, len(numbers))
        if insets is None:
            raise ValueError(
                f"this page's footer cannot carry {len(numbers)} QR groups "
                f"{widest} px wide"
            )
        placement = pair.lower.page
        if placement.parity is PageParity.ODD:
            # The row packs rightward from the outer (right) margin, so the
            # outermost group is the *last* one a reader meets.
            insets = tuple(reversed(insets))
        for number, inset in zip(numbers, insets, strict=True):
            icon = qr_slot(pair.lower, inset_px=inset)
            caption = qr_caption(pair.lower, inset_px=inset)
            if icon is None or caption is None:  # pragma: no cover - insets imply both
                raise ValueError("a reserved footer strip must carry its own QR group")
            _draw_qr_placeholder(draw, icon)
            _draw_qr_caption(draw, caption, number, self.dpi, name_the_puzzle=True)

    def _draw_solved_slot(
        self,
        draw: ImageDraw.ImageDraw,
        slot: Layout,
        grid: Any,
        puzzle_number: int,
        difficulty: Any,
        title: Optional[str],
    ) -> Optional[Tuple[int, int]]:
        """Draw one solved answer's whole content onto an already-placed slot.

        CARD-197/198's full solved-page drawing (steps 3-8 of
        :meth:`solved_puzzle_page`, before CARD-202), extracted so a packed
        slot (:meth:`_packed_answer_page`) and a full answer page
        (:meth:`solved_puzzle_page`) draw from the **one** implementation —
        the same precedent :meth:`_two_up_page` set for
        :func:`_stroke_drawing`/:func:`_write_clues`/:func:`_set_band`, now
        extended to this card's own drawing steps. Nothing is reordered and
        nothing added or removed: a full page calling this on its own
        full-page ``Layout`` draws byte-for-byte what it always did (AC-7),
        because every line below is the same line that used to sit directly
        in :meth:`solved_puzzle_page`'s body.

        ``slot`` is whatever COMP-007 measured for this answer's position — a
        full page's :class:`~nonogram.export.layout.Layout`, or one tile of a
        :class:`~nonogram.export.layout.PackedSolvedLayout` — and nothing
        here fits a cell or places a line itself (ADR-0036/R2).

        **Review cycle 1, F-001 (gating).** Returns the caption's own occupied
        box — ``(caption_bottom, caption_right)`` in device pixels, read off
        the mark this method actually drew — or ``None`` when the omission
        guard (``slack < gap_px + line_height``) left the caption undrawn.
        Callers thread this into :func:`_draw_folio`'s own
        ``content_bottom``/``content_right`` collision check (the same
        mechanism CARD-200 built for a two-up/packed page's *grid* vs. the
        folio, now reused for the *caption* vs. the folio): the caption's
        right-aligned anchor (CARD-203) can share the folio's own bottom-outer
        corner on a right-hand page, which a caller with no figure for the
        caption's box cannot detect. The folio — never the caption — yields
        when both would want the same corner, the same "folio omits, content
        wins" precedent CARD-200 already set; this card does not touch the
        caption's own placement or omission guard above.

        **CARD-204 Fix 7 (merge gate), as corrected by Fix 8 (review cycle
        5, F-2).** The caption's right edge is now the one
        :func:`~nonogram.export.layout.caption_slot` reports for this slot
        and this text's measured width, not ``placement.drawing_right``
        unconditionally. CARD-203's right-alignment is preserved exactly
        where the *drawing itself* fits inside its own usable area
        (:attr:`~nonogram.export.layout.PagePlacement.fits`) and the caption
        fits beside it — the two are then the same pixel. Two cases depart
        from it, both deliberately and both toward the margin the ink would
        otherwise cross: a caption wider than its grid is held off the
        usable area's left edge instead of printing into the trim margin
        (which it did on an ``EVEN`` page from the moment CARD-204 placed the
        drawing flush with that edge, and still does for a long enough name
        now that CARD-224 has centred it again — half a page's spare is a
        wider allowance, not an unbounded one); and on a page too small for its
        puzzle, where the ``MIN_CELL_MM`` floor puts ``drawing_right``
        *past* ``usable_right`` (``fits`` False — AC-3's own regime), the
        caption stops at ``usable_right`` rather than following the drawing
        out into the gutter margin, so it sits up to that overflow further
        left than CARD-203 alone would have put it (measured: 32 px / 2.7 mm
        for a 30x30 on a 10.0 cm trim at KDP-minimum margins). COMP-007's
        own comment on that stop, and
        ``tests/test_layout_page_spec.py::TestCaptionSlot_NoWidthEverLeavesTheUsableArea::test_an_overflowing_layout_stops_the_caption_at_the_margin``,
        are where that case is stated and pinned. The width is measured here
        because only this module knows the face; where that width is allowed
        to sit is COMP-007's (ADR-0036/R2). A caption too wide for the
        usable area at any x is clipped to
        :attr:`~nonogram.export.layout.CaptionSlot.measure` first
        (:func:`_clipped_to`), since its type is already at CON-020's floor
        and cannot shrink. The box returned to the caller reports the clamped
        right edge, so the folio's own collision check above sees where the
        caption actually is.

        Raises:
            ValueError: ``slot`` is not a placed page (:meth:`page_spec`
                always carries a parity, so this cannot happen through the
                public door — the same total-function guard
                :meth:`_two_up_page` keeps for the same reason).
        """
        xs = [line.position for line in slot.vertical_lines]
        ys = [line.position for line in slot.horizontal_lines]
        for row_index, row in enumerate(grid[: slot.rows]):
            for column_index, filled in enumerate(row[: slot.columns]):
                if not filled:
                    continue
                draw.rectangle(
                    (
                        xs[column_index],
                        ys[row_index],
                        xs[column_index + 1],
                        ys[row_index + 1],
                    ),
                    fill=INK,
                )

        _stroke_drawing(draw, slot)

        for c in range(1, slot.columns):
            width = slot.vertical_lines[c].width
            x = xs[c]
            for r in range(slot.rows):
                if grid[r][c - 1] and grid[r][c]:
                    draw.line(
                        [(x, ys[r]), (x, ys[r + 1])],
                        fill=_SOLVED_GRID_GRAY,
                        width=width,
                    )
        for r in range(1, slot.rows):
            width = slot.horizontal_lines[r].width
            y = ys[r]
            for c in range(slot.columns):
                if grid[r - 1][c] and grid[r][c]:
                    draw.line(
                        [(xs[c], y), (xs[c + 1], y)],
                        fill=_SOLVED_GRID_GRAY,
                        width=width,
                    )

        _write_clues(draw, slot)

        placement = slot.page
        if placement is None:  # pragma: no cover - page_spec always carries a parity
            raise ValueError("a solved slot must be a placed book page")

        _set_band(
            draw,
            header_band(slot),
            band_identity(puzzle_number, difficulty),
            placement.usable_right - placement.usable_left,
        )

        caption_font_points = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
        caption_font_size = type_px(caption_font_points, self.dpi)
        caption_font = _band_font(caption_font_size)
        ascent, descent = caption_font.getmetrics()
        line_height = ascent + descent
        # A physical mm gap, not a type size, so this converts straight to
        # device pixels rather than through `type_px` (CARD-203; that
        # helper's own docstring takes points, not mm).
        gap_px = round(ANSWER_TILE_GAP_MM / 25.4 * self.dpi)
        slack = placement.usable_bottom - placement.drawing_bottom
        if slack >= gap_px + line_height:
            caption = answer_caption(puzzle_number, title)
            # CARD-204 Fix 7: where the caption's right edge goes is COMP-007's
            # to say, not this renderer's (ADR-0036/R2) — a caption wider than
            # its own grid would otherwise overhang `drawing_left`. CARD-204
            # made that overhang land in the trim margin by placing the
            # drawing flush with it; CARD-224 centres the drawing again, so
            # half the page's spare is back on that side and the clamp binds
            # later — but it still binds, because a picture's name is
            # unbounded and a grid is not (that card's AC-5/G-3).
            # What stays here is what only this module knows:
            # the face, and therefore the text's own width. A caption too wide
            # for the usable area at all is clipped to the measure COMP-007
            # reports, the same way `create_toc_page` clips a long label
            # (`_clipped_to`) — the type cannot shrink instead, since
            # ANSWER_TEXT_FONT_MM already *is* CON-020's 10 pt floor.
            caption_width = math.ceil(caption_font.getlength(caption))
            box = caption_slot(slot, caption_width)
            if box is None:  # pragma: no cover - `placement` above is not None
                raise ValueError("a solved slot must be a placed book page")
            if caption_width > box.measure:
                caption = _clipped_to(caption, caption_font, box.measure)
                box = caption_slot(slot, math.ceil(caption_font.getlength(caption)))
            draw.text(
                (
                    box.right,
                    placement.drawing_bottom + gap_px + line_height / 2,
                ),
                caption,
                font=caption_font,
                fill=INK,
                anchor="rm",
            )
            # Review cycle 1, F-001: hand the caption's own occupied box back
            # to the caller so it can fold it into _draw_folio's own
            # collision check (right-aligned caption can now share a
            # right-hand page's folio corner — see this method's own
            # docstring). The caption's right edge sits at `box.right`
            # (anchor "rm"), which is `drawing_right` for every caption that
            # fits beside its own grid and further right only for one clamped
            # off the margin; its bottom edge is gap_px + line_height below
            # drawing_bottom, the same arithmetic as the guard above.
            return (
                round(placement.drawing_bottom + gap_px + line_height),
                box.right,
            )
        return None

    def solved_puzzle_page(
        self,
        payload: ExportPayload,
        puzzle_number: int,
        page_number: int,
        title: Optional[str] = None,
    ) -> Image.Image:
        """One puzzle's full-page solved layout: clues top and left, light-gray
        gridlines between filled cells (owner's Google Doc "Nonograms - Print
        layout1", 2026-10-07).

        A rendering primitive added by CARD-197 beside :meth:`_two_up_page`
        (same layer, same pattern), and the one this method draws every
        answer page with since CARD-198 wired it into
        :meth:`interior_stream`'s answer-section loop, replacing the former
        packed 6-up/4-up key (FR-042, ADR-0036/R2).

        ``compute_layout`` is called with ``payload``'s own clue sets and
        :meth:`page_spec`'s spec for ``page_number`` — the **same** call an
        unsolved puzzle page at that position would make, so the cell, the
        gutters, every grid-line position and the frame are identical to an
        unsolved page's (AC-9). Nothing here fits a cell or places a line
        itself (ADR-0036/R2): every mark below sits at a coordinate that call
        already measured.

        The caller resolves the caption's title through
        :func:`~nonogram.admin.book_answer_key.answer_title` /
        :meth:`custom_titles` before calling
        :func:`~nonogram.admin.book_answer_key.answer_caption` — this method
        never reads ``payload.name``.

        Args:
            payload: The puzzle's solved grid and clue sets (ADR-0012
                boundary types) and its stored tier (``payload.difficulty``),
                read for the band exactly as :meth:`_puzzle_payload` reads it
                for an unsolved page's.
            puzzle_number: The puzzle's 1-based print position — the same
                number the band's "Puzzle N" and the caption's "Puzzle N"
                both show (:func:`band_identity`,
                :func:`~nonogram.admin.book_answer_key.answer_caption`).
            page_number: The interior position this page is laid out for
                (FR-043), whose parity :meth:`page_spec` reads.
            title: The caption's resolved title
                (:func:`~nonogram.admin.book_answer_key.answer_title`'s
                return), or ``None`` for a puzzle with neither a custom title
                nor a name — the caption then reads "Puzzle N" and stops,
                exactly as :func:`~nonogram.admin.book_answer_key.answer_caption`
                already does.

        **Since CARD-200, one more mark after the caption: the folio.**
        Drawn here, not inside :meth:`_draw_solved_slot` (G-3: the caption's
        own drawing/omission logic there is unedited by this fix), from the
        same ``layout.page`` placement the caption's own slack check already
        reads — recomputed independently rather than threaded out of that
        method, so the two checks cannot be made to disagree by a future edit
        to one alone.

        **Review cycle 1, F-001 (gating), correcting this docstring's own
        earlier claim.** Before CARD-203 the caption was horizontally
        centred, so it always sat in the opposite corner from the folio
        (caption centred, folio at the usable area's outer corner) and
        neither mark's placement needed to know about the other. CARD-203's
        right-aligned caption (anchor ``"rm"`` at ``placement.drawing_right``)
        removed that separation: on a right-hand page the caption now targets
        the **same** bottom-outer corner the folio does, and a puzzle whose
        slack falls in the narrow window where both marks' own "is there
        room" guards pass independently used to produce overlapping ink
        (reported against this exact method; the two guards' thresholds
        differ — the caption's own ``gap_px + line_height`` is wider than the
        folio's plain ``line_height`` — so a slack value could clear the
        caption's bar without the folio's placement ever learning the
        caption was there).

        The fix follows CARD-200's own precedent for the grid-vs-folio case
        ("the folio yields, the content wins," never the other way round):
        :meth:`_draw_solved_slot` now reports the caption's own occupied box
        back to this method, which — only on a right-hand page, where the
        caption's box can actually reach the folio's corner — folds it into
        the ``content_bottom``/``content_right`` figures passed to
        :func:`_draw_folio`, so the folio omits itself rather than drawing
        into the caption's own ink. A left-hand page is unaffected (the
        caption sits at the opposite corner there, exactly as before); on a
        right-hand page the two marks either both draw with daylight between
        them, or the folio alone yields — they never again draw overlapping.

        Returns:
            The rendered page.

        Raises:
            ValueError: ``page_number`` did not produce a placed book page
                (:meth:`page_spec` always carries a parity, so this cannot
                happen through the public door — the same total-function
                guard :meth:`_two_up_page` keeps for the same reason).
        """
        layout = compute_layout(
            payload.row_clues, payload.column_clues, self.page_spec(page_number)
        )
        page = Image.new("RGB", (layout.width, layout.height), BACKGROUND)
        draw = ImageDraw.Draw(page)
        caption_box = self._draw_solved_slot(
            draw, layout, payload.grid, puzzle_number, payload.difficulty, title
        )
        placement = layout.page
        if placement is not None:  # pragma: no cover - page_spec always carries a parity
            # Review cycle 1, F-001: on a right-hand page the right-aligned
            # caption (CARD-203) can reach the same bottom-outer corner the
            # folio does. Fold the caption's own box (if drawn) into the
            # folio's collision check there — "the folio yields, the content
            # wins," CARD-200's own precedent for the grid-vs-folio case. A
            # left-hand page's caption sits at the opposite corner, so it
            # cannot compete with the folio and this method's pre-CARD-203
            # behaviour is left exactly as it was.
            content_bottom = placement.drawing_bottom
            content_right = None
            if caption_box is not None and page_is_right_hand(page_number):
                caption_bottom, caption_right = caption_box
                content_bottom = max(content_bottom, caption_bottom)
                content_right = caption_right
            _draw_folio(
                draw,
                placement.usable_left,
                placement.usable_top,
                placement.usable_right,
                placement.usable_bottom,
                page_number,
                self.dpi,
                content_bottom=content_bottom,
                content_right=content_right,
            )
        return page

    def _packed_answer_page(
        self,
        plan: PackedAnswerPage,
        payloads: List[Tuple[Any, ExportPayload]],
        page_number: int,
        titles: Dict[str, str],
    ) -> Image.Image:
        """The page 2 or 4 small answers share, each with its own clues (CARD-202).

        What :meth:`_two_up_page` is to :meth:`puzzle_pages`' pairing walk,
        this is to :func:`~nonogram.admin.book_answer_key.plan_small_answer_pages`:
        a page composed from what COMP-007 measured
        (:func:`~nonogram.export.layout.compute_packed_solved_layout`), one
        shared cell for every slot. What this method chooses is each slot's
        drawing — :meth:`_draw_solved_slot`, the **same** call
        :meth:`solved_puzzle_page` draws a full answer page with — never a
        cell, a line or a band position (ADR-0036/R2, G-1).

        Args:
            plan: Which small answers land on this page, in fill order
                (:attr:`~nonogram.admin.book_answer_key.PackedAnswerPage.numbers`),
                and at what capacity (2 or 4).
            payloads: Every drawable puzzle's ``(id, ExportPayload)``, indexed
                by 1-based print number minus one — the same list
                :meth:`interior_stream` already holds.
            page_number: The interior position this page is laid out for
                (FR-043), whose parity :meth:`page_spec` reads.
            titles: The book's custom puzzle titles (:meth:`custom_titles`),
                read the same way :meth:`interior_stream`'s own answer loop
                already reads them for a full answer page.

        **SCOPE+ (CARD-200), not named by this card's own "What to
        implement": a packed answer page is still an interior page AC-1
        asks a folio of, and this card's own Touches list predates
        CARD-202's packed key existing at all.** Drawn off :func:`page_frame`
        rather than ``layout`` itself: unlike :meth:`solved_puzzle_page`'s
        full-page :class:`~nonogram.export.layout.Layout`,
        :class:`~nonogram.export.layout.PackedSolvedLayout` carries no
        page-level ``usable_*`` at all (G-3's "no page-level title band"
        extends to no page-level margin reader either — only each slot's own
        tile does) — exactly the gap :func:`page_frame` exists to fill for
        any ``PageSpec``, drawn content or not, the same reuse
        :meth:`create_guide_page`/:meth:`create_divider_page`/
        :meth:`_blank_page` already rely on.

        **Review cycle 2, F-1 (gating), correcting this card's own first-pass
        reasoning**: "tiles sit inset from the trim's own margins... never
        reaching the page's bottom-outer corner" was wrong —
        :func:`~nonogram.export.layout.compute_packed_solved_layout`'s own
        tile gap (``SOLVED_TILE_GAP_MM``) sits only *between* adjacent
        tiles; the outer tiles (the bottom row, the first/last column) are
        bounded by the page's own usable area with no extra inset at all,
        so the **tile** reaches the trim's own margin on every packed page,
        by construction, on its outer edges. Whether that outer tile's own
        *drawing* also reaches that edge (the real collision risk) depends
        on the shared cell's own fit — confirmed by direct measurement: a
        30-wide/23-tall, row-clue-depth-1/column-clue-depth-15 member at
        capacity 4 lands its bottom-right tile's drawing flush with both the
        tile's own bottom and right edges, i.e. the page's own usable
        corner. Only the tile at the folio's own physical corner (the last
        tile row, crossed with the last tile column on a right-hand page or
        the first on a left-hand one) can ever compete with it — a tile
        elsewhere on the page never reaches that corner regardless of its
        own fit — and only when the plan actually filled that position
        (:attr:`~nonogram.admin.book_answer_key.PackedAnswerPage.numbers`
        may leave a page's last slot or two empty). When that corner slot
        exists, its own :class:`~nonogram.export.layout.PagePlacement` is
        passed to :func:`_draw_folio` as ``content_bottom``/
        ``content_right``/``content_left`` exactly as :meth:`_two_up_page`
        passes its own lower slot's; when the corner is unfilled there is
        nothing there to collide with, so the folio is drawn with no
        content figures at all, the same as before this fix.

        **Review cycle 1, F-001 (gating).** The corner tile's own caption
        (CARD-203, right-aligned at that tile's ``drawing_right``) can reach
        the exact same corner as its ``content_right``/``content_left``
        above already do — so when :meth:`_draw_solved_slot` reports that
        tile's caption as actually drawn, its own lower edge (not just the
        tile's ``drawing_bottom``) is folded into ``content_bottom`` before
        calling :func:`_draw_folio`.

        **CARD-203 review cycle 2, F-101 (gating, correcting the previous
        paragraph's own overstated parity claim).** The fold-in above is
        **only ever correct on a right-hand page**, exactly like
        :meth:`solved_puzzle_page`'s own gate (``page_is_right_hand`` at line
        ~3754) — and the first-pass fix above omitted that gate entirely,
        applying it on both page sides. The caption is always right-aligned
        at *that tile's own* ``drawing_right``, regardless of which column
        the corner tile occupies: on a right-hand page the corner tile is
        the last column, so its ``drawing_right`` coincides with the page's
        own right-outer margin — the folio's actual corner — and the fold-in
        is a real collision check. On a left-hand page the corner tile is
        the *first* column instead (``corner_column`` above), whose
        ``drawing_right`` sits at that tile's own right edge, nowhere near
        the page's left-outer margin the folio actually anchors to there
        (``content_left``, fed from that same tile's ``drawing_left``) —
        folding the caption's bottom into ``content_bottom`` unconditionally
        made the folio disappear from left-hand packed pages with genuine,
        ample slack, reversing the very defect this fix was meant to close
        (reproduced and fixed under F-101; regression-tested by
        ``TestBookSolvedAnswerKey_PackedCaptionDoesNotCollideWithTheFolio``
        in ``tests/test_book_solved_answer_key.py``). ``right_hand`` (already
        computed above for ``corner_column``) is reused as the gate, so the
        two methods' fixes are now actually parallel, not just claimed to be.

        **CARD-204 Fix 8 (review cycle 5, F-1, gating).** "Right-aligned at
        that tile's own ``drawing_right``" above stopped being the whole
        truth at Fix 7: a caption wider than its own grid is clamped out to
        the tile's ``usable_right`` instead
        (:func:`~nonogram.export.layout.caption_slot`). ``content_right`` is
        therefore read off the caption's own reported box when the corner
        tile drew one on a right-hand page — the same figure
        :meth:`solved_puzzle_page` already passes — not off
        ``drawing_right``, which under-reports a clamped caption and let the
        folio draw into its glyphs. See the comment at the call site for the
        reproduction and for why the left-parity mirror is left latent.

        Returns:
            The rendered page.
        """
        members = [payloads[number - 1] for number in plan.numbers]
        layout = compute_packed_solved_layout(
            [(payload.row_clues, payload.column_clues) for _, payload in members],
            plan.capacity,
            self.page_spec(page_number),
        )
        if layout is None:
            # pragma: no cover - `interior_stream`'s
            # `_degrade_infeasible_packed_pages` pass (review F-1) already
            # proved this exact plan, at this capacity, lays out on a
            # parity-equivalent spec before it ever reaches here; a `None`
            # here means that guarantee broke, not that this page is a normal
            # case to recover from.
            raise ValueError(
                f"packed answer page {page_number} ({plan.numbers}) cannot be "
                f"laid out at capacity {plan.capacity} after the packing walk "
                "already found it feasible"
            )
        page = Image.new("RGB", (layout.width, layout.height), BACKGROUND)
        draw = ImageDraw.Draw(page)
        caption_boxes: List[Optional[Tuple[int, int]]] = []
        for slot, number, (puzzle_id, payload) in zip(
            layout.slots, plan.numbers, members, strict=True
        ):
            title = answer_title(titles.get(str(puzzle_id)), payload.name)
            caption_boxes.append(
                self._draw_solved_slot(
                    draw, slot, payload.grid, number, payload.difficulty, title
                )
            )
        frame = page_frame(self.page_spec(page_number))
        right_hand = page_is_right_hand(page_number)
        corner_column = layout.tile_columns - 1 if right_hand else 0
        corner_index = (layout.tile_rows - 1) * layout.tile_columns + corner_column
        corner_placement = (
            layout.slots[corner_index].page if corner_index < len(layout.slots) else None
        )
        # Review cycle 1, F-001: the corner tile's own caption (CARD-203,
        # right-aligned at that tile's drawing_right) can reach exactly the
        # same physical corner this folio targets, so content_bottom has to
        # widen to the caption's own lower edge when one was actually drawn
        # there — same "folio yields" precedent as solved_puzzle_page's own
        # fix, applied to the corner tile instead of a full page's single
        # placement.
        #
        # CARD-204 Fix 8 (review cycle 5, F-1): content_right has to widen
        # with it. This comment used to claim that "content_right /
        # content_left already carry that tile's own drawing_right /
        # drawing_left (the caption's right edge coincides with it)" — true
        # until Fix 7, false since. A caption wider than its own grid is now
        # clamped out to the tile's `usable_right` (`caption_slot`), and a
        # packed tile's drawing is CENTRED inside its tile, so the tile has
        # right-hand spare for the clamp to spend; on the corner column of a
        # right-hand page that tile's usable_right IS the page's own folio
        # corner. So `drawing_right` under-reported the caption's real edge,
        # the clearance test below passed on a figure that no longer
        # described the ink, and the folio drew into glyphs the caption had
        # already set. Reproduced at trim 21.59x22.86 cm, KDP-minimum
        # margins, capacity 4, 11x11, page 9, a 64-character picture name:
        # drawing_right 2383 against the caption's real right edge 2462,
        # the folio's own glyph box starting at 2447, 20 px of caption ink
        # inside it. The caption's own reported right edge is what goes in
        # now, exactly as solved_puzzle_page already passes `caption_right`.
        #
        # The left-parity mirror (`content_left` from the caption's own left
        # edge) is deliberately NOT taken here: `_draw_solved_slot` reports
        # `(bottom, right)` and nothing else, so the caption's left edge
        # would need a third element on that return tuple — a contract
        # change this fix cycle is scoped out of (owner decision, cycle 5).
        # It is latent, not live: `content_left` is read only on a left-hand
        # page, where F-101's own fix gates the `content_bottom` fold-in on
        # `right_hand`, so the vertical half of the predicate does not fire.
        content_bottom = None if corner_placement is None else corner_placement.drawing_bottom
        corner_caption = (
            caption_boxes[corner_index] if corner_index < len(caption_boxes) else None
        )
        content_right = None if corner_placement is None else corner_placement.drawing_right
        if right_hand and content_bottom is not None and corner_caption is not None:
            content_bottom = max(content_bottom, corner_caption[0])
            content_right = corner_caption[1]
        _draw_folio(
            draw,
            frame.left,
            frame.top,
            frame.right,
            frame.bottom,
            page_number,
            self.dpi,
            content_bottom=content_bottom,
            content_right=content_right,
            content_left=None if corner_placement is None else corner_placement.drawing_left,
        )
        return page

    def puzzle_pages(
        self,
        payloads: List[ExportPayload],
        first_page: int = 1 + GUIDE_PAGE_COUNT,
        ids: Optional[List[Any]] = None,
        first_number: int = 1,
    ) -> List[PuzzlePagePlan]:
        """The pairing walk over the book order (FR-040, INV-010, EC-027).

        Walks ``payloads`` — the book order, as CARD-126 leaves it — from the
        first puzzle. Puzzle *i* and puzzle *i+1* are offered to COMP-007's
        :func:`~nonogram.export.layout.compute_pair_layout` **only when their
        tiers are equal** (:func:`_pairable_tier`). A ``PairLayout`` back means
        both go on one page and the walk moves to *i+2*; ``None`` means *i*
        prints alone and the walk moves to *i+1*. The last puzzle of an odd run
        prints alone.

        **Greedy, forward, and deliberately so.** The walk offers only the
        immediate successor, never looks further for a better partner, and
        never leaves a puzzle alone that its successor would have paired with.
        Concatenating the pages' puzzles front to back therefore yields the
        book order exactly: pairing is an arrangement of the order, never a
        change to it (EC-027). The owner arranged that order (INV-009, FR-041)
        and a PDF that re-sorted it to save paper would be silently overruling
        them.

        Each pair is measured on the spec of **its own page** — the page number
        the walk has reached, whose parity is its position (FR-043) — so a page
        saved earlier in the book moves every later page to the other side of
        the spread, and each one is laid out for the side it actually lands on.
        (Parity moves the usable area, never its size, so it cannot change a
        verdict; measuring on the real page is what keeps that true by
        construction rather than by assumption.)

        ``None`` back from :func:`~nonogram.export.layout.compute_pair_layout`
        is the only verdict it has; an **exception** from it is a malformed
        member (clue sets that disagree about the grid) or a page spec that is
        not a book page, and is re-raised as a :class:`RuntimeError` naming the
        two puzzles the walk offered. It is not turned into "this pair does not
        pair": ``None`` means *measured and too small*, and a walk that answered
        it for a member it could not measure would print that member alone and
        leave the export to fail — or not — somewhere else, under a different
        name. The failure is named here, where it happened, so that every abort
        of :meth:`interior` names a puzzle whatever stage it came from.

        **CARD-200's folio always gets its fixed, universal reserve (CARD-204
        Fix 4, owner decision 2026-10-12).** Every call here passes
        :func:`_folio_reserve_px`'s own value — a constant derived only from
        the font and ``self.dpi``, never from ``page_number``, ``payloads``
        or anything about this specific book — into
        :func:`~nonogram.export.layout.compute_pair_layout`'s
        ``folio_reserve_px``. The same number reaches every pair this walk
        ever offers, so the walk's own accept/refuse verdicts and cell sizes
        stay exactly as page/book-independent as they were when Fix 3
        removed the reserve mechanism (INV-010) — the difference is that
        every two-up page's lower slot now keeps room for its folio instead
        of losing it (see :func:`~nonogram.export.layout.compute_pair_layout`'s
        own docstring for why a fixed constant cannot reintroduce the
        cycle-1/cycle-2 coupling).

        Args:
            payloads: The drawable puzzles in print order. A payload's
                ``difficulty`` is the row's stored tier text, and its clue sets
                are what the pair is fitted from.
            first_page: The interior position of the first puzzle page. Pages
                1..:data:`GUIDE_PAGE_COUNT` are the guide (CARD-201's 2-page
                tutorial), so the default is one past it — which is what it
                is for a book with no levels to divide; with CARD-128's
                dividers :meth:`puzzle_section` passes the page after each
                level's divider instead.
            ids: The puzzle ids, parallel to ``payloads``, for the message of
                the raise below. Optional: without them a failure names the
                print numbers instead.
            first_number: The print number of ``payloads[0]``. 1 for the whole
                book; for one level's slice it is the number that level's first
                puzzle carries, so the bands and the answer key still run 1..n
                unbroken across the levels (AC-255) and a divider consumes
                none of them.

        Returns:
            One :class:`PuzzlePagePlan` per page, in print order.

        Raises:
            ValueError: ``ids`` was given and is not parallel to ``payloads``
                — naming the wrong puzzle is worse than naming none.
            RuntimeError: a pair the walk offered could not be laid out. The
                message names both members (``_named_puzzles``) and keeps the
                original failure as its ``__cause__``.
        """
        if ids is not None and len(ids) != len(payloads):
            raise ValueError(
                f"ids must be parallel to payloads: {len(ids)} id(s) for "
                f"{len(payloads)} payload(s)"
            )
        plan: List[PuzzlePagePlan] = []
        page_number = first_page
        index = 0
        while index < len(payloads):
            first, second = payloads[index], None
            if index + 1 < len(payloads):
                tier = _pairable_tier(first)
                if tier is not None and tier is _pairable_tier(payloads[index + 1]):
                    second = payloads[index + 1]
            number = index + first_number
            if second is None:
                pair = None
            else:
                numbers = (number, number + 1)
                page_spec = self.page_spec(page_number)
                try:
                    pair = compute_pair_layout(
                        (first.row_clues, first.column_clues),
                        (second.row_clues, second.column_clues),
                        page_spec,
                        folio_reserve_px=_folio_reserve_px(self.dpi),
                        footer_reserve_px=interior_frame(page_spec).footer_depth,
                    )
                except Exception as e:
                    raise RuntimeError(
                        f"puzzle {_named_puzzles(ids, numbers, first_number)} "
                        f"could not be laid out: {e}"
                    ) from e
                if pair is not None and (
                    qr_group_insets(pair.lower, _qr_group_line_px(self.dpi), len(numbers))
                    is None
                ):
                    # The strip fits the sheet's height but not two groups
                    # across it (a 10 cm trim at the narrowest margins
                    # ``book_page_spec`` admits, measured). Unpaired, not
                    # half-linked: the two puzzles print on two single pages,
                    # each with its own footer and its own link.
                    pair = None
            if pair is None:
                plan.append(PuzzlePagePlan(page_number, (number,)))
                index += 1
            else:
                plan.append(PuzzlePagePlan(page_number, (number, number + 1), pair))
                index += 2
            page_number += 1
        return plan

    def puzzle_section(
        self,
        payloads: List[ExportPayload],
        first_page: int = 1 + GUIDE_PAGE_COUNT,
        ids: Optional[List[Any]] = None,
    ) -> List[SectionPage]:
        """The interior's puzzle section: a divider per level, then its pages.

        The whole of the interior between the guide page and the SOLUTIONS
        divider (FR-041, INV-009, CARD-128), planned before anything is drawn.
        ``payloads`` is the book in **print order** — grouped easy, then
        medium, then hard by :func:`print_order`, which is where the ordering
        decision is made and the only place it is made.

        This method cuts that order into its levels and, for each one, plans a
        :class:`DividerPagePlan` followed by :meth:`puzzle_pages`' walk over
        that level's puzzles alone. A level is a **maximal run of consecutive
        payloads sharing a tier**, read through :func:`_pairable_tier`, which
        on a grouped order is exactly "one run per non-empty level" — an empty
        level is not in the list at all, so it gets no divider (AC-256). A run
        whose tier is ``None`` gets no divider either: there is no name to
        print on one (see the module docstring).

        Reading runs rather than sorting again is deliberate: it is what keeps
        this cut and the answer section's own book order agreeing by
        construction, with no separate pass re-deriving the levels a second
        time.

        Splitting the pairing walk at a level boundary changes no verdict:
        INV-010 already lets only two puzzles of **equal** tier share a page,
        so no pair the single walk would have made could straddle a boundary
        anyway. What the split adds is the page numbers — each level's walk
        starts on the page after its own divider — while the **puzzle**
        numbers run on unbroken through ``first_number``, so a divider costs a
        page and no number (AC-255).

        **History (CARD-204 Fix 1/Fix 2, reverted by Fix 3, restored as a
        fixed constant by Fix 4 — owner decision, 2026-10-12, "fixed
        universal reserve").** Fix 1 and Fix 2 reserved horizontal room at
        each two-up page's lower slot for CARD-200's folio, first per-page
        (Fix 1) and then as one book-level bound shared across every level's
        walk (Fix 2) — but both let a *non-geometric, page/book-specific*
        quantity (a page number's or a book's own digit count) flip whether
        two puzzles pair and at what cell, which cycle-1 and cycle-2 review
        each reproduced as an INV-010 violation. Fix 3 removed the reserve
        mechanism entirely, which restored INV-010 purity but silently
        reintroduced the folio-loss bug on *every* two-up page (cycle-3
        review F-7). **This method needs no edit for Fix 4**: each level's
        own :meth:`puzzle_pages` call now reserves
        :func:`_folio_reserve_px`'s own fixed, dpi-only pixel amount
        internally — identical for every level of every book, since neither
        this method nor :meth:`puzzle_pages` ever passes it a page number or
        a count of anything. Splitting the pairing walk at a level boundary
        therefore still changes no verdict: the reserve a puzzle sees does
        not depend on which level's slice it is offered in, any more than
        :data:`~nonogram.export.layout.TWO_UP_MIN_CELL_MM` does.

        Args:
            payloads: The drawable puzzles in print order.
            first_page: The interior position of the section's first page,
                which is the first level's divider. Pages
                1..:data:`GUIDE_PAGE_COUNT` are the guide (CARD-201), so the
                default is one past it.
            ids: The puzzle ids, parallel to ``payloads``, for the messages
                :meth:`puzzle_pages` raises. Each level's walk is handed its
                own slice, so a failure still names the row it happened to.

        Returns:
            The section's pages in print order: one :class:`DividerPagePlan`
            per named non-empty level, each immediately before that level's
            :class:`PuzzlePagePlan`\\ s.

        Raises:
            ValueError: ``ids`` was given and is not parallel to ``payloads``.
            RuntimeError: as :meth:`puzzle_pages`.

        Note:
            The print-order premise above is a **precondition, not a guard**.
            It is what makes "one divider per non-empty level" — and therefore
            :func:`interior_page_count`'s ``min(len(TIERS), puzzle_count)``
            default — true: ``_level_runs`` cuts maximal runs, so an ungrouped
            list of *n* tier changes yields *n* named runs and *n* dividers,
            above that bound. Today the premise holds by construction, because
            :meth:`interior_stream` calls :func:`print_order` before it calls
            this and is the only production caller. It is left unguarded here
            deliberately, and CARD-129 — which must make the interior's page
            count exact and is the expected next direct caller — is the card
            that decides whether the ordering moves inside this method or
            becomes a checked precondition.
        """
        if ids is not None and len(ids) != len(payloads):
            raise ValueError(
                f"ids must be parallel to payloads: {len(ids)} id(s) for "
                f"{len(payloads)} payload(s)"
            )
        section: List[SectionPage] = []
        page_number = first_page
        for level, start, end in _level_runs(payloads):
            if level is not None:
                section.append(DividerPagePlan(page_number, level))
                page_number += 1
            pages = self.puzzle_pages(
                payloads[start:end],
                first_page=page_number,
                ids=None if ids is None else ids[start:end],
                first_number=start + 1,
            )
            section.extend(pages)
            page_number += len(pages)
        return section

    def section_plan(self, puzzles: List[dict]) -> SectionPlan:
        """Where this book's puzzles print, decided from its rows alone (CARD-140).

        The **pure** half of :meth:`interior_stream`, extracted so that a
        caller who only wants to know *where* a puzzle lands does not have to
        draw a page to find out — and, more importantly, so that there is one
        implementation of that question. The Arrangement screen's page breaks
        and the exported book's pages come out of this one call (FR-036,
        FR-041): the screen asks and renders, and decides no geometry of its
        own (G-1, ADR-0036/R2). It draws nothing, opens no file and stores
        nothing — pages are decided at PDF time and remain so (G-4).

        Three decisions, in the order the export makes them:

        * the **print order** (:func:`print_order`): grouped easy, then medium,
          then hard, stably and idempotently, so a caller that already holds
          the book grouped — as the arrange screen does, through the store's
          own grouping — gets the same list back;
        * the **payload pass**: a row that cannot even build an
          :class:`~nonogram.export.ExportPayload` is dropped with a warning,
          before a puzzle number or a page position is handed out, exactly as
          the export drops it;
        * the **section walk** (:meth:`puzzle_section`): a divider page per
          named non-empty level (CARD-128) and that level's pages, one puzzle
          each or two of equal tier that COMP-007 measured onto one page
          (FR-040, INV-010) — starting the page after the table of contents
          (CARD-200), whose own length this method measures first from the
          payload pass's own count, so every page number in the walk's
          output already carries the TOC's own offset.

        **What the pairing verdict is read from, and what it is not.** The walk
        offers each same-tier neighbour pair to
        :func:`~nonogram.export.layout.compute_pair_layout`, which fits the
        shared cell from both puzzles' *real clue depths* (TERM-021) — so a
        pair's verdict is not a function of the two extents alone, and a
        planner that took ``(width, height)`` and nothing else would answer
        differently from the book it is supposed to describe. The rows' own
        stored clues are therefore what travels here, and they are on the
        puzzle record beside the extent and the tier, so the screen loads
        nothing extra to ask this question.

        *How* differently is measured rather than asserted, and re-measured on
        every run, by
        ``tests/test_book_arrange_page_breaks.py``'s
        ``test_extent_alone_would_disagree_with_the_book_on_this_corpus``: over
        that file's seeded 24-book corpus, 10 of the 93 same-tier neighbour
        verdicts the walk offers come out differently when both puzzles' clues
        are flattened to one run per line at the same extent.

        Args:
            puzzles: The book's rows, in any order — the same list the export
                is given.

        Returns:
            The :class:`SectionPlan`: the ordered rows, the printable ones
            themselves and their ids, the section's pages, and the TOC's own
            page count (CARD-200).

        Raises:
            RuntimeError: a pair the walk offered could not be laid out
                (:meth:`puzzle_pages`).
        """
        ordered = print_order(puzzles)
        ids: List[Any] = []
        printed: List[Any] = []
        payloads: List[ExportPayload] = []
        for puzzle in ordered:
            # Read outside the try: a row so malformed it is not even a
            # mapping must still be logged, not raise again inside the
            # handler that is reporting it.
            puzzle_id = puzzle.get("id") if hasattr(puzzle, "get") else None
            try:
                payload = self._payload(puzzle)
            except Exception as e:
                logger.warning(
                    "Dropping book puzzle %s from the interior: no export "
                    "payload could be built for it (%s)",
                    puzzle_id,
                    e,
                )
                continue
            ids.append(puzzle_id)
            printed.append(puzzle)
            payloads.append(payload)
        # CARD-200: the table of contents sits between the guide and the
        # puzzle section, so every page this walk hands out moves by its own
        # length. Measured here, off this book's own trim
        # (:func:`page_frame`/:func:`measured_toc_page_count`), rather than deferred
        # to :meth:`interior_stream` — this is the *only* place the puzzle
        # section's own ``first_page`` is decided, and the Arrangement
        # screen's own call (``app.py``'s ``_printed_places``) goes through
        # here too, so a screen asking "where will puzzle 12 print" and the
        # export that actually prints it cannot disagree about the TOC's
        # own length (G-4, the same "decided once, read twice" discipline
        # this method's own docstring already states for the pairing walk).
        #
        # CARD-205: the entry count is the **structural** list's, not the
        # puzzle count — the TOC lists sections (guide, each non-empty level's
        # heading and range, solutions), so `structural_toc_entry_count` is
        # what `measured_toc_page_count` is fed here. The level runs it needs
        # are readable from the payloads alone, which is what lets this figure
        # be settled before any page number exists; `_level_runs` is called
        # again by `puzzle_section` below, over the same list, and the two
        # readings are cross-checked in `interior_stream` (its own TOC
        # tripwire) rather than assumed equal. The measured split is kept
        # exactly as it was: this is the same arithmetic on a different count,
        # never a hardcoded "the TOC is one page".
        toc_entry_count = structural_toc_entry_count(
            len([run for run in _level_runs(payloads) if run[0] is not None]),
            len(payloads),
        )
        toc_page_count = measured_toc_page_count(
            toc_entry_count, page_frame(self.page_spec(1)), self.dpi
        )
        first_page = 1 + GUIDE_PAGE_COUNT + toc_page_count
        return SectionPlan(
            puzzles=ordered,
            ids=ids,
            printed=printed,
            payloads=payloads,
            pages=self.puzzle_section(payloads, first_page=first_page, ids=ids),
            toc_page_count=toc_page_count,
        )

    def interior_pages(self, puzzles: List[dict]) -> List[Image.Image]:
        """Every page of the interior, in print order; no cover page.

        :attr:`Interior.pages` of :meth:`interior`, for the callers that want
        the pages and not the page-count saving beside them.

        **A list of pages, and therefore not what an export uses.** Since
        CARD-145 the export path walks :meth:`interior_stream` instead, one
        page alive at a time; this method and :meth:`interior` are the
        materialising convenience over the same walk, for a caller that really
        does want every page at once — a test measuring ink on page 4, a
        future proof sheet. On a book of any size that list is 25.2 MB a page,
        so calling it *is* the shape the deployed panel was OOM-killed by.
        """
        return self.interior(puzzles).pages

    def interior(self, puzzles: List[dict]) -> Interior:
        """Every page of the interior, in print order, and what pairing saved.

        ``pages[n - 1]`` is interior page ``n``: pages 1..:data:`GUIDE_PAGE_COUNT`
        are the guide, the 2-page "how to solve" tutorial (CARD-201), page 1
        a right-hand page (:func:`page_is_right_hand`), followed by the
        puzzle section — a divider page opening each non-empty level and
        that level's puzzle pages (:meth:`puzzle_section`, FR-041) — then the
        SOLUTIONS divider and the answer pages. The list's length is the
        book's page count (FR-030); the cover is never counted.

        The puzzles print grouped easy, then medium, then hard whatever order
        the book's rows arrive in (:func:`print_order`, INV-009), and the
        numbers their bands carry run 1..n over the puzzles in that order: a
        divider takes a page and no number.

        A puzzle page holds one puzzle, or two of equal tier that the walk
        paired (:meth:`puzzle_pages`, FR-040). The answer section is one full
        solved page per puzzle (:meth:`solved_puzzle_page`, FR-042, CARD-198),
        in book order, each page's own band carrying its tier — there is no
        separate level heading inside the answer section.

        Every page is built on ``book_page_spec(book, its own position)``, so
        each one is the book's trim and takes its parity from where it lands
        (FR-043). That is why the payloads are built first: a puzzle that
        cannot even be turned into an export payload is dropped *before* any
        position is handed out, so no later page is numbered as though a page
        that does not exist were there — every surviving page still sits where
        its **own** 1-based position puts it. The drop is logged, at warning,
        and is the only trace of a member that did not reach the file.

        The same pass decides the **puzzle numbers** ADR-0037/R1 prints. A
        puzzle's ``N`` is its 1-based position among the payloads that
        survived, not among ``puzzles``, so the numbers a reader sees run
        1, 2, 3 with no gap where a dropped member was — and its answer page
        carries that same number, whichever page its puzzle was printed on.
        Numbering follows the print order, whatever put the puzzles in it:
        CARD-128's grouping by level reorders ``puzzles`` and the numbers
        follow.

        Returns:
            The :class:`Interior`: the pages, and the count the same interior
            would have taken with every puzzle on a page of its own (FR-040).

        Raises:
            RuntimeError: one puzzle built a payload and then would not print.
                That failure is **not** swallowed — the page plan
                :func:`interior_page_count` states would no longer describe the
                file, and a book that is quietly one page short is worse than
                an export that says so — so it aborts the whole export. The
                message names the puzzle's ``id``, which is the only thing in
                the raised text a 120-puzzle book can be searched by: the
                position in ``puzzles`` no longer matches the interior once a
                puzzle has been dropped, and the interior page number does not
                point back at a row at all.

                A puzzle can fail at either of two stages, and **both name it**:
                "puzzle <id> could not be laid out" when the pairing walk
                offered it to COMP-007 and the measurement itself failed
                (:meth:`puzzle_pages`; a pair names both members, since the
                measurement is of the two together), and "puzzle <id> could not
                be drawn" when its page would not render. Which stage a given
                malformed row reaches depends on whether it has a same-tier
                neighbour, so a failure that named the row in one book and not
                in the other would be the contract holding by luck.

                It is also raised when the page plan and the pages built
                disagree, and when the walk's plan does not print every puzzle
                exactly once, in order.

        Since CARD-145 this is :meth:`interior_stream` with its pages
        collected — the same walk, the same order, the same tripwires, the
        same failures, and every page held at once at the end of it.
        """
        stream = self.interior_stream(puzzles)
        return Interior(
            pages=list(stream.pages),
            unpaired_page_count=stream.unpaired_page_count,
            answer_page_count=stream.answer_page_count,
        )

    def interior_stream(self, puzzles: List[dict]) -> InteriorStream:
        """The interior's page plan, and its pages one at a time (CARD-145).

        The export path's entry point, and the lazy core :meth:`interior` is
        the materialising convenience over. It splits the interior into the
        part that **decides** and the part that **draws**, and does all of the
        first before any of the second:

        *Decided here, eagerly, before this method returns.* The print order
        (:func:`print_order`), the payload pass (and the drop of any member
        that cannot build one), the level cut and the pairing walk
        (:meth:`puzzle_section`) — those three through :meth:`section_plan`,
        which is the same call the Arrangement screen asks where a puzzle
        prints (CARD-140) — then an eager validation pass over every answer
        (CARD-198: the same rectangle check the old packed key made, kept
        because the abort contract is load-bearing — see
        :func:`_is_an_unpackable_row` in ``app.py`` — though its result is no
        longer used to pack anything), the page-plan tripwire, the guide
        page's tier counts, the Arrangement step's custom titles, and all
        three page counts. None of it draws a pixel, and all of it can fail —
        so an export that is going to be refused is refused before its file
        has a first byte.

        *Drawn later, lazily, one page per :func:`next`.* The guide page, the
        table of contents (CARD-200, :meth:`create_toc_page`), each level's
        divider and the puzzle pages the walk planned, the SOLUTIONS divider
        and one full solved page per puzzle (CARD-198), each on the spec of
        its own interior position (FR-043), each built when it is asked for
        and released when the next one is.
        The returned generator is single-use and holds no page: see
        :class:`InteriorStream`.

        Returns:
            The :class:`InteriorStream`: three counts known without drawing,
            and the pages.

        Raises:
            RuntimeError: as :meth:`interior` documents — but note *when*. The
                page-plan tripwire ("the page plan prints ...") and a
                malformed answer's "could not be laid out" both raise from
                this call, before the caller has opened a file. "puzzle <id>
                could not be drawn" and the page-count guard
                (:func:`_as_planned`) raise from the generator instead, while
                the caller is walking it; a caller that is writing a PDF must
                therefore treat its output buffer as worthless until the walk
                has finished, which is exactly what :meth:`_write_pdf` does.
        """
        # The print order, the payload pass and the section walk, all through
        # the one seam the Arrangement screen asks the same question of
        # (:meth:`section_plan`, CARD-140): the rows are grouped easy, then
        # medium, then hard and a row that cannot build a payload is dropped
        # before a number or a page position is handed out, so everything below
        # — the bands and the answer section's own numbers — follows one order
        # that was settled once, and the screen's page breaks are this same
        # book's pages rather than a second opinion on them.
        #
        # The positions every page is built on: 1 the guide page, then the
        # puzzle section — a divider per non-empty level and the puzzle pages
        # the walk planned — then the SOLUTIONS divider and one answer page
        # per puzzle. The section walk runs before a single page is drawn,
        # because how many pages it takes is what puts the divider and every
        # answer page where it goes.
        decided = self.section_plan(puzzles)
        puzzles = decided.puzzles
        # The puzzle's own id travels with its payload: it is what the raises
        # below name, and once a member has been dropped nothing else left in
        # the walk identifies the row the failure came from.
        payloads: List[Tuple[Any, ExportPayload]] = list(
            zip(decided.ids, decided.payloads)
        )
        count = len(payloads)
        ids = decided.ids
        section = decided.pages
        plan = [entry for entry in section if isinstance(entry, PuzzlePagePlan)]
        dividers = len(section) - len(plan)
        toc_page_count = decided.toc_page_count
        titles = self.custom_titles()

        # The validation half of the old packed key's walk (CARD-198): each
        # answer's grid must still be a non-empty rectangle, checked and named
        # before any page is drawn, because `app.py`'s `_is_an_unpackable_row`
        # matches exactly this abort shape (G-2) and a book with a malformed
        # row must still fail here rather than partway through the answer
        # loop below. CARD-202 also *uses* the measured extent, below, to
        # decide which answers pack — the same reader, read once.
        answers: List[Answer] = []
        for index, (_, payload) in enumerate(payloads):
            number = index + 1
            try:
                width, height = _answer_extent(payload, number)
            except ValueError as e:
                raise RuntimeError(
                    f"puzzle {_named_puzzles(ids, (number,))} could not be "
                    f"laid out: {e}"
                ) from e
            answers.append(
                Answer(
                    number=number,
                    width=width,
                    height=height,
                    level=_pairable_tier(payload),
                )
            )

        # CARD-202's packing walk: pure, over extents and levels alone, no
        # sheet involved (ADR-0036/R2 — the geometry it implies is only
        # measured later, per page, by `compute_packed_solved_layout`). A
        # large answer (anything over width<=15/height<=20) still plans as
        # itself, one page, unconditionally (G-1); a run of small answers of
        # one level packs 4-or-2 (G-6).
        answer_plan = plan_small_answer_pages(answers)

        # Every page of the section — dividers included — sits between the
        # guide page and the SOLUTIONS divider, so both of those positions
        # count the section's length and not its puzzle pages alone. Computed
        # here (rather than after the degrade pass below) because it depends
        # only on `section`, never on `answer_plan` — any page_spec built from
        # it measures the *same* usable size any other interior page position
        # would (`book_page_spec`'s own docstring: parity moves the margins,
        # never the usable size), which is exactly what lets one representative
        # spec answer the degrade pass's feasibility check for every page
        # position the plan could still land on.
        first_answer_page = 3 + len(section)

        # Review F-1 (CARD-202, fix cycle 1): `plan_small_answer_pages` above
        # is pure and extent-only (its own module docstring: no tile measured,
        # no PageSpec) — it cannot know that a run's *real* clue depth will
        # make COMP-007's `compute_packed_solved_layout` decline a packed page
        # the MIN_CELL_MM floor would otherwise force to overlap a neighbour's
        # tile. This degrades any such page — 4-up to two 2-ups, then down to
        # one full page per answer — into a plan every page of which COMP-007
        # can actually lay out, *before* `len(answer_plan)` is read for the
        # page count below and baked into the PDF's pre-allocated object
        # table (`_write_pdf`). `payloads` carries the real grids and clue
        # sets this check needs; `plan_small_answer_pages` never sees them.
        answer_plan = _degrade_infeasible_packed_pages(
            answer_plan, payloads, self.page_spec(first_answer_page)
        )

        # The walk's own half of the page-plan tripwire below, and the one the
        # tripwire cannot make: `interior_page_count(count, len(plan))` takes
        # the puzzle-page term from the walk's output, so a walk that dropped a
        # puzzle (or printed one twice) would agree with itself and ship a book
        # missing a puzzle whose answer page is printed all the same. Checked
        # against this call's own input instead, before a page is drawn.
        printed = [number for entry in plan for number in entry.numbers]
        if printed != list(range(1, count + 1)):
            raise RuntimeError(
                f"the page plan prints {printed}, not puzzles 1..{count}"
            )

        # The degrade pass above only ever splits a page into more, smaller
        # ones in place — it must never drop, duplicate or reorder an answer.
        # Checked directly, the same tripwire shape as `printed` above, rather
        # than trusted because the implementation "only ever splits": a change
        # to that function that broke the invariant must fail loudly here
        # instead of shipping an answer section that silently prints twice or
        # not at all.
        answer_numbers = [
            number
            for entry in answer_plan
            for number in (
                entry.numbers if isinstance(entry, PackedAnswerPage) else (entry.number,)
            )
        ]
        if answer_numbers != list(range(1, count + 1)):
            raise RuntimeError(
                f"the answer-section plan prints {answer_numbers}, not puzzles 1..{count}"
            )
        # Every page of the section — dividers included — sits between the
        # TOC (CARD-200: `toc_page_count` pages, after the guide) and the
        # SOLUTIONS divider, so both of those positions count the section's
        # length and not its puzzle pages alone.
        first_answer_page = 1 + GUIDE_PAGE_COUNT + toc_page_count + len(section) + 1

        # CARD-200/CARD-205: the TOC's own rows, decided here (not inside
        # `produce()` below) for the same reason every other page-count-bearing
        # pass in this method runs before a pixel is drawn — anything that can
        # fail must fail before the caller has a file open, not partway through
        # the walk. **After** the two plan tripwires above, deliberately: this
        # reads `section`'s own dividers and page numbers, and those tripwires
        # are what guarantee the plan it reads prints puzzles 1..count exactly
        # once (the same ordering CARD-200's own review finding established for
        # the per-puzzle dict this replaces, kept for the same reason).
        #
        # CARD-205: one row per **section**, never per puzzle — the guide, each
        # non-empty level's heading and `Puzzles N–M` range, and the solutions
        # — built from this same page plan rather than from a second source of
        # truth. The row that names the answer section points at the SOLUTIONS
        # divider, `first_answer_page - 1`: the page that opens the section is
        # what a reader turns to, and it is one page before the first answer
        # by construction (the same arithmetic `produce()` below yields it on).
        toc_entries = structural_toc_entries(
            section, decided.payloads, first_answer_page - 1
        )
        # The plan/draw tripwire for the TOC, in two halves — the ROWS first,
        # then the pages they take.
        #
        # `section_plan` measured `toc_page_count` from
        # `structural_toc_entry_count` — the row count predicted from the level
        # runs alone, before any page number existed (that function's own
        # docstring explains why the split is necessary) — and every page
        # number in `section`, `first_answer_page` and the folio of every page
        # after the guide is laid out on that figure. The rows just built are
        # the ones that will actually be drawn.
        #
        # The first half is the equality `structural_toc_entries`' own
        # docstring states: the builder's row count is the count function's.
        # It is checked here and NOT left to the page comparison below,
        # because a page count hides a row count: both figures are 1 for
        # anything from one row up to the frame's own capacity (ten rows on
        # the shortest storable trim, several dozen on Book 1), so the two
        # passes could disagree by rows — a heading without its range, a
        # level listed twice — and still agree on pages. Review cycle 1,
        # F-001, demonstrated exactly that: `structural_toc_entry_count`
        # mutated to `1 + 2 * level_count` left the page comparison silent.
        # `dividers` is the section walk's own count of level divider pages,
        # which `structural_toc_entries` has just proved to be the same levels
        # in the same order as `payloads`' own runs (its RuntimeError above).
        predicted_toc_rows = structural_toc_entry_count(dividers, count)
        if len(toc_entries) != predicted_toc_rows:
            raise RuntimeError(
                f"the table of contents built {len(toc_entries)} row(s), but "
                f"a book of {dividers} level(s) and {count} puzzle(s) lists "
                f"{predicted_toc_rows} — the page plan was laid out on the "
                "second figure"
            )
        # The second half, on the pages. If the two ever disagree the book's
        # whole back half is numbered for a TOC of the wrong length, which no
        # render of the TOC page itself would reveal: so they are re-measured
        # against each other here rather than trusted to have been derived the
        # same way.
        drawn_toc_pages = measured_toc_page_count(
            len(toc_entries), page_frame(self.page_spec(1)), self.dpi
        )
        if drawn_toc_pages != toc_page_count:
            raise RuntimeError(
                f"the table of contents' {len(toc_entries)} row(s) need "
                f"{drawn_toc_pages} page(s), but the page plan was laid out on "
                f"{toc_page_count}"
            )

        # Calculate difficulty counts for guide — over every member of the
        # book, drawable or not, because that is what the book holds. Read
        # here rather than inside the walk below: everything that can fail
        # without drawing fails before the caller has a file open.
        counts = tier_breakdown(puzzles)

        # The page plan is this function's own make-up; fail loudly rather
        # than let the two drift apart. It is taken over this call's *input* —
        # the puzzles that survived the payload pass — and over the walk's own
        # verdict on how many pages it takes, never over the pages the walk
        # below produces, so a change to the make-up of the pages (a divider
        # per level, say) that forgets `interior_page_count` is caught rather
        # than shipping a book whose stated page count is not its page count.
        # Since CARD-145 the two sides meet in `_as_planned`, as the pages go
        # past, instead of in a `len()` over a list nobody can afford to
        # build. The answer term is `len(answer_plan)` since CARD-202: the
        # packing walk's own page count, <= `count` and strictly less
        # whenever at least one small answer packs. `toc_pages` is
        # `decided.toc_page_count` (CARD-200): the same length already baked
        # into `section`'s own page numbers above, passed explicitly rather
        # than left to this function's own sheet-free default, which assumes
        # Book 1's profile and would silently disagree with a book stored on
        # a smaller trim.
        planned = interior_page_count(
            count, len(plan), len(answer_plan), dividers, toc_pages=toc_page_count
        )

        # CARD-200: measured once here, off this book's own trim, and reused
        # verbatim by `produce()`'s own TOC loop below — the same split
        # `decided.toc_page_count` (`section_plan`) was already measured
        # with, so the plan and the draw can never disagree about how a long
        # TOC breaks across pages.
        toc_entries_per_page = _toc_entries_per_page(page_frame(self.page_spec(1)), self.dpi)

        def produce() -> Iterator[Image.Image]:
            """The interior's pages in print order, one per :func:`next`.

            Two rules hold throughout, and both are load-bearing rather than
            stylistic — every page kind keeps them, the level dividers
            CARD-128 added included:

            **No page outlives the yield that hands it on.** A page is either
            yielded as an expression or bound, yielded and immediately
            ``del``\\ eted, because a 25.2 MB bitmap still bound when the walk
            resumes is a bitmap alive while the next one is built, which is
            exactly the shape this card removes.

            **No ``yield`` sits inside the ``except Exception`` that names an
            undrawable puzzle.** A page is built inside the ``try`` and handed
            on outside it, so the handler can only ever see a failure of the
            drawing it wrapped — never something a consumer threw back in
            while the walk was suspended at that yield.
            """
            # CARD-201: the guide is GUIDE_PAGE_COUNT pages, not one — two
            # calls to the same method (page_number selects which half, see
            # create_guide_page's own docstring), each yielded and released
            # exactly as every other page is (CARD-145/CARD-198's "no page
            # outlives the yield that hands it on", restated above).
            for guide_page_number in range(1, GUIDE_PAGE_COUNT + 1):
                page = self.create_guide_page(
                    len(puzzles),
                    counts[Tier.EASY],
                    counts[Tier.MEDIUM],
                    counts[Tier.HARD],
                    page_number=guide_page_number,
                )
                yield page
                del page

            # CARD-200: the table of contents, immediately after the guide
            # and before the puzzle section — every later page's own number
            # already accounts for `toc_page_count` (the `first_page` passed
            # into `puzzle_section` above, via `section_plan`). Every TOC
            # page repeats `TOC_TITLE` (`create_toc_page`'s own docstring),
            # so `toc_entries_per_page`, measured once above, is the same
            # split on every page rather than a per-page re-decision.
            for index in range(toc_page_count):
                start = index * toc_entries_per_page
                page = self.create_toc_page(
                    toc_entries[start : start + toc_entries_per_page],
                    GUIDE_PAGE_COUNT + 1 + index,
                )
                yield page
                del page

            for page_plan in section:
                if isinstance(page_plan, DividerPagePlan):
                    # A level's divider: its name on the book's trim and
                    # nothing else (AC-254, G-3). Yielded as an expression, so
                    # this frame never holds it while the next page is built.
                    yield self.create_divider_page(
                        page_plan.page_number, page_plan.text
                    )
                    continue
                members = [payloads[number - 1] for number in page_plan.numbers]
                try:
                    if page_plan.pair is None:
                        ((_, payload),) = members
                        page = self._blank_page(
                            payload, page_plan.numbers[0], page_plan.page_number
                        )
                    else:
                        page = self._two_up_page(page_plan, [p for _, p in members])
                except Exception as e:
                    named = _named_puzzles(ids, page_plan.numbers)
                    raise RuntimeError(
                        f"puzzle {named} could not be drawn: {e}"
                    ) from e
                yield page
                del page

            # The divider opens the answer section, so it is yielded before
            # the pages it opens — the order the interior holds them in. Each
            # answer page is drawn from its own interior position and nothing
            # else, so building them in book order changes no page's ink
            # (CARD-145's AC-3 pins that page for page). Since CARD-202 an
            # entry is either a lone `Answer` (unchanged: one full solved page,
            # CARD-198) or a `PackedAnswerPage` (2 or 4 small answers sharing
            # one page, CARD-202) — the walk above is what decided which.
            if not payloads:
                return
            # CARD-201: the guide grew by GUIDE_PAGE_COUNT pages, not one, so
            # the SOLUTIONS divider (immediately before the answer section)
            # moved with it — one page before `first_answer_page`, by
            # construction, which already accounts for GUIDE_PAGE_COUNT
            # above.
            yield self.create_divider_page(first_answer_page - 1)
            for index, entry in enumerate(answer_plan):
                page_number = first_answer_page + index
                try:
                    if isinstance(entry, PackedAnswerPage):
                        page = self._packed_answer_page(
                            entry, payloads, page_number, titles
                        )
                    else:
                        puzzle_id, payload = payloads[entry.number - 1]
                        page = self.solved_puzzle_page(
                            payload,
                            entry.number,
                            page_number,
                            title=answer_title(
                                titles.get(str(puzzle_id)), payload.name
                            ),
                        )
                except Exception as e:
                    numbers = (
                        entry.numbers
                        if isinstance(entry, PackedAnswerPage)
                        else (entry.number,)
                    )
                    named = _named_puzzles(ids, numbers)
                    raise RuntimeError(
                        f"puzzle {named} could not be drawn: {e}"
                    ) from e
                yield page
                del page

        return InteriorStream(
            page_count=planned,
            # The baseline before *any* space-saving technique: one puzzle
            # page each (no two-up pairing) and one answer page each (no
            # CARD-202 packing) — deliberately left at `answer_pages=count`
            # rather than `len(answer_plan)`. `pages_saved` therefore now
            # measures two-up pairing *and* CARD-202 packing together, not
            # pairing alone as CARD-198's own comment here used to say — see
            # this card's Worktree notes for why that comment, not this
            # number, is what changed (the KDP sheet-free estimate decision
            # turns on the same point). `paired_only_page_count` below is
            # the number that lets a caller split the two apart again
            # (review F-2).
            # `toc_pages=toc_page_count` on both calls below (CARD-200): the
            # TOC's own length does not change with pairing or packing, so it
            # is the one term every one of this method's three
            # `interior_page_count` calls shares, passed explicitly rather
            # than left to the sheet-free default for the same reason
            # `planned` above does.
            unpaired_page_count=interior_page_count(
                count, answer_pages=count, level_dividers=dividers, toc_pages=toc_page_count
            ),
            # Pairing's own baseline (review F-2): the puzzle section at its
            # actual, paired length, but the answer section still at one full
            # page per puzzle (no CARD-202 packing) — so
            # `pages_saved_by_pairing`/`pages_saved_by_packing` can attribute
            # the saving between `unpaired_page_count` and `page_count` to
            # the technique that actually made it, instead of the Finalise
            # screen crediting it all to pairing.
            paired_only_page_count=interior_page_count(
                count,
                len(plan),
                answer_pages=count,
                level_dividers=dividers,
                toc_pages=toc_page_count,
            ),
            answer_page_count=len(answer_plan),
            pages=_as_planned(produce(), planned),
        )

    def _write_pdf(
        self, pages: Iterable[Image.Image], page_count: int, *, mode: str
    ) -> BytesIO:
        """Write ``pages`` as one PDF, one image per page, rewound to 0.

        ``page_count`` is how many pages ``pages`` will produce, known from
        the page plan before any of them exists. It is not a hint: the PDF's
        object table is laid out from it — one image, one page and one
        contents object id per page, all allocated before the catalog is
        written — which is what lets the pages themselves arrive one at a time
        rather than as a list (CARD-145). ``pages`` is consumed exactly once
        and no page is held after it is written; a caller that wants the pages
        afterwards must keep them itself.

        ``mode`` is the Pillow image mode this **file**'s pages are written
        in — one of :data:`_PDF_COLOUR_SPACE`'s keys — and it is a required
        keyword argument rather than something read off the book inside here
        (CARD-147). The two files of one export disagree about it: a
        black-and-white interior is written ``"L"``, and the cover file beside
        it is written ``"RGB"`` whatever the book's mode says, because it holds
        an uploaded image that may be anything (AC-5, G-4). Naming it at every
        call is what makes that disagreement visible at the call rather than
        hidden in a default.

        What is written is ``PdfImagePlugin._save``'s path for that mode,
        object for object: a ``DCTDecode`` (JPEG) image stream at the book's
        DPI, a page whose ``MediaBox`` is the trim in points, a contents
        stream drawing that one image over the whole page, and an ``Info``
        dictionary with the two dates Pillow writes. For ``"RGB"`` that is the
        same file this module has always written — the only difference from
        the one the old list-at-once call produced is those two timestamps, the
        same language CON-019 uses for the CLI's own PDFs — so
        ``tests/helpers/pdf_pages.py`` and every other reader of a book PDF
        works on it unedited, in either colour space.

        Returns:
            The finished PDF, rewound to 0. **Only** a finished one: the
            buffer is a local of this method until the cross-reference table
            and trailer are written, so a page that will not draw at page *k*
            of *N* raises through this call and takes its partial bytes with
            it. No caller, and no route, can be handed a truncated PDF.

        Raises:
            RuntimeError: ``pages`` produced a number of pages other than
                ``page_count`` — see :func:`_as_planned`, which is what the
                interior's producer is already wrapped in. Checked again here,
                over whatever iterable this method was actually given, because
                it is this method's object table that a miscount corrupts.
            Exception: whatever a page raised while being drawn, unchanged.
            ValueError: ``mode`` is not a colour space this writer knows —
                raised before the buffer exists, so no partial file is built.
        """
        if mode not in _PDF_COLOUR_SPACE:
            known = ", ".join(sorted(_PDF_COLOUR_SPACE))
            raise ValueError(
                f"a book PDF is written in one of {known}, not {mode!r}"
            )
        written = BytesIO()
        pdf = PdfParser.PdfParser(f=written, filename="", mode="w+b")
        # The two dates Pillow's own writer stamps a new file with, so the
        # Info dictionary reads the same as it always has.
        pdf.info["CreationDate"] = time.gmtime()
        pdf.info["ModDate"] = time.gmtime()

        # One image, page and contents object per planned page, allocated
        # before anything is drawn. This is the whole reason the page count
        # has to be known in advance — and the reason a producer that yields
        # the wrong number of pages is a corrupt file rather than a short one.
        image_refs: List[Any] = []
        page_refs: List[Any] = []
        contents_refs: List[Any] = []
        for _ in range(page_count):
            image_refs.append(pdf.next_object_id(0))
            page_refs.append(pdf.next_object_id(0))
            contents_refs.append(pdf.next_object_id(0))
            pdf.pages.append(page_refs[-1])

        pdf.start_writing()
        pdf.write_header()
        pdf.write_comment("created by Pillow PDF driver")
        pdf.write_catalog()

        index = 0
        for page in _as_planned(pages, page_count):
            self._write_page(pdf, page, image_refs[index], page_refs[index],
                             contents_refs[index], mode)
            index += 1
            # Nothing in this frame may outlive the page it wrote: the next
            # one is built by the `next()` at the top of this loop, and this
            # loop variable is the one reference every other frame's own `del`
            # cannot drop for it. Without this line the measured peak is
            # exactly 2.00 page bitmaps instead of 1.00, which is what
            # `test_neither_book_holds_more_than_one_page_bitmap` pins.
            del page

        pdf.write_xref_and_trailer()
        pdf.close()
        written.seek(0)
        return written

    def _write_page(
        self,
        pdf: PdfParser.PdfParser,
        page: Image.Image,
        image_ref: Any,
        page_ref: Any,
        contents_ref: Any,
        mode: str = "RGB",
    ) -> None:
        """Write one page's three objects into ``pdf``, at its own object ids.

        ``PdfImagePlugin._write_image`` and the body of its ``_save`` loop for
        an image of this ``mode``, side by side here because the plugin only
        offers them behind a call that wants every page at once. Nothing is
        chosen: the filter, the colour space, the procset, the ``MediaBox``
        arithmetic and the contents operator are all taken from it verbatim —
        see :data:`_PDF_COLOUR_SPACE`, which is the plugin's own two branches
        transcribed — which is what keeps an RGB file byte-identical to the one
        the old call wrote and a grayscale one exactly what the plugin would
        have written for an ``"L"`` page.

        **The conversion happens here, per page** (CARD-147, G-3). The page
        this method was handed is COMP-007's, drawn ``"RGB"``; a
        black-and-white interior converts it to ``"L"`` and drops the
        conversion when this frame returns, so the extra bitmap is one
        one-channel page (8.4 MB on the Book 1 profile) inside a single page's
        write and never a term that grows with the book. Nothing collects
        pages in order to convert them, and the number of pages the module
        retains across a page boundary is still one.

        The conversion itself loses no ink: ITU-R 601-2 luma's three integer
        coefficients sum to 65536, so a grey ``(v, v, v)`` becomes exactly
        ``v`` — 0 stays 0, 255 stays 255, and nothing between them is invented
        (ADR-0037/R2).

        ``mode`` defaults to ``"RGB"``, the one colour space every book PDF was
        written in before this card, so a caller that names none gets the old
        behaviour; :meth:`_write_pdf` always names it.
        """
        colour_space, procset = _PDF_COLOUR_SPACE[mode]
        if page.mode != mode:
            page = page.convert(mode)
        encoded = BytesIO()
        page.save(encoded, format="JPEG", dpi=(self.dpi, self.dpi))
        pdf.write_obj(
            image_ref,
            stream=encoded.getvalue(),
            Type=PdfParser.PdfName("XObject"),
            Subtype=PdfParser.PdfName("Image"),
            Width=page.width,
            Height=page.height,
            Filter=PdfParser.PdfName("DCTDecode"),
            BitsPerComponent=8,
            ColorSpace=PdfParser.PdfName(colour_space),
        )
        width = page.width * 72.0 / self.dpi
        height = page.height * 72.0 / self.dpi
        pdf.write_page(
            page_ref,
            Resources=PdfParser.PdfDict(
                ProcSet=[PdfParser.PdfName("PDF"), PdfParser.PdfName(procset)],
                XObject=PdfParser.PdfDict(image=image_ref),
            ),
            MediaBox=[0, 0, width, height],
            Contents=contents_ref,
        )
        pdf.write_obj(
            contents_ref,
            stream=b"q %f 0 0 %f 0 0 cm /image Do Q\n" % (width, height),
        )
