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
:func:`~nonogram.export.pdf.render_pages`. The only thing positioned here is
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
guide page at interior page 1 and the "Easy" divider at 2, the first puzzle
page is interior page 3 — a right-hand page (AC-287).

Two-up pairing needs no level rule of its own: a page is shared only by two
puzzles of **equal** tier (INV-010), and a level *is* a tier's run, so no pair
can straddle a divider. The answer section follows the same book order — one
solved page per puzzle, in print-number order — so a level's answer pages sit
contiguously exactly as its puzzle pages do, with no further arranging here
(CARD-198).

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
import time
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from functools import lru_cache
from importlib import resources
from typing import Any, Dict, Iterable, Iterator, Optional, List, Sequence, Tuple, Union
from PIL import Image, ImageDraw, ImageFont, PdfParser
from io import BytesIO

from nonogram.admin.book_answer_key import answer_caption, answer_title
from nonogram.admin.book_page_spec import InkMode, book_ink_mode, book_page_spec
from nonogram.admin.book_plan import TIERS, book_level_order
from nonogram.difficulty import Tier, tier_of_record
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    ANSWER_TEXT_FONT_MM,
    DPI,
    HeaderBand,
    Layout,
    PageSpec,
    PairLayout,
    compute_layout,
    compute_pair_layout,
    header_band,
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
#: whatever size that is. It letters through :func:`_guide_face`, whose
#: fallback is sized, so a machine without Arial no longer prints the word at
#: Pillow's 10 px default (2.4 pt).
DIVIDER_PT = 14.4

#: The guide page's title (FR-041, AC-324, CARD-167). It was "How to Use This
#: Book" until the page started teaching how to solve.
GUIDE_TITLE = "How to Solve Nonograms"

#: The line the guide page's worked example solves (FR-041, AC-325): the clue
#: ``3 1`` on a row of six squares.
WORKED_EXAMPLE_CLUE: Tuple[int, ...] = (3, 1)
WORKED_EXAMPLE_LENGTH = 6

#: The guide page's opening paragraph, printed under the title on the page's
#: full form (CARD-167). A module constant since CARD-169 so the Finalise
#: screen's preview reads the same text.
GUIDE_INTRO = (
    "Each number beside a row or above a column is a run of "
    "filled squares in that line, in order, with at least one "
    "empty square between runs. Fill the squares you are sure "
    "of, and cross out the ones you are sure are empty."
)

#: The line that introduces the worked example on the page's full form,
#: built from the clue and the row length it names (CARD-169).
GUIDE_EXAMPLE_HEADING = (
    "Worked example: the clue "
    + " ".join(str(run) for run in WORKED_EXAMPLE_CLUE)
    + f" on a row of {WORKED_EXAMPLE_LENGTH} squares."
)

#: The guide page's closing sentence, printed on the page's full form
#: (CARD-167; a module constant since CARD-169).
GUIDE_CLOSING = (
    "Every puzzle in this book has exactly one solution. The "
    "answers are at the back of the book."
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


def _guide_face(size: int) -> Any:
    """The face the guide page and the divider pages letter in, at ``size`` px.

    Arial by path; on a machine without it, Pillow's own face asked for at the
    same size. A bare ``load_default()`` letters a page at a 10 px em whatever
    the page is, which is the defect CARD-149 fixed wearing a fallback's
    clothes. Pillow sizes its built-in face from 10.1 on; the declared floor
    is 10.0, which raises ``TypeError`` instead, and there the page keeps the
    unsized face it has always had.
    """
    try:
        return ImageFont.truetype("/System/Library/Fonts/Arial.ttf", size)
    except OSError:
        try:
            return ImageFont.load_default(size)
        except TypeError:  # pragma: no cover - Pillow < 10.1
            return ImageFont.load_default()


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
    or two sizes across every page it prints."""
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
    survives the overlap and stays continuous. ``slot.frame`` is ``None`` only
    on an unframed sheet, which a two-up slot never is — a pair is a placed page
    (:class:`~nonogram.export.layout.PairLayout` refuses anything else) and a
    placed page is framed — so the guard is a total function's, not a branch
    this module's callers can take.
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
    if frame is None:  # pragma: no cover - a two-up slot is a placed, framed page
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
    """

    puzzles: List[Any]
    ids: List[Any]
    printed: List[Any]
    payloads: List[ExportPayload]
    pages: List[SectionPage]


@dataclass(frozen=True)
class Interior:
    """The interior's pages, and what two-up pairing saved (FR-040).

    Attributes:
        pages: Every interior page in print order; ``pages[n - 1]`` is interior
            page ``n``. No cover page (FR-043, INV-013).
        unpaired_page_count: What the same interior would have taken with every
            puzzle on a page of its own — the "before pairing" count. Both are
            **interior** counts: the cover is a separate file and is never
            counted.

            It is the same interior before **pairing** and nothing else: the
            answer section is one page per puzzle on both sides of the
            subtraction (CARD-198 — there is no packing saving left to
            bundle in), which is what keeps :attr:`pages_saved` a measurement
            of two-up pairing alone.
        answer_page_count: How many of :attr:`pages` are answer pages, the
            SOLUTIONS divider **not** counted (FR-042) — the Increment 15
            checkpoint's own number.
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
    pairing walk and the drawable puzzle count (CARD-198: one answer page per
    puzzle, no packing), so an export can report what it is about to write
    without building 25.2 MB of bitmap per page to count them.

    Attributes:
        page_count: The interior's page count after pairing — the same number
            :attr:`Interior.page_count` reports, and the number of pages
            :attr:`pages` is contracted to produce.
        unpaired_page_count: What the same interior would have taken with
            every puzzle on a page of its own (:attr:`Interior.unpaired_page_count`).
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

    @property
    def pages_saved(self) -> int:
        """How many interior pages the two-up pages saved. Never negative."""
        return self.unpaired_page_count - self.page_count


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


def example_line_layout(spec: PageSpec) -> Layout:
    """The worked example's line, laid out by COMP-007 on the guide page's sheet.

    :func:`~nonogram.export.layout.compute_layout` is asked for a one-row
    puzzle whose row clue is :data:`WORKED_EXAMPLE_CLUE`, on ``spec`` — the
    book's own sheet — so the cell pitch, the thin and heavy rules, the frame
    and the clue size are the ones a puzzle on this book's page gets. The
    column clues are placeholders that only give the layout its six columns:
    the column gutter they occupy is not drawn (:func:`draw_example_line`).
    """
    columns = ((0,),) * WORKED_EXAMPLE_LENGTH
    layout = compute_layout((WORKED_EXAMPLE_CLUE,), columns, spec)
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


def draw_example_line(layout: Layout, step: ExampleStep) -> Image.Image:
    """One step of the worked example, cropped tight around its ink.

    Filled squares first, then crosses, then the rules and frame over them
    (:func:`_stroke_drawing`, the two-up page's stroking) and the clue numbers
    (:func:`_write_clues`) — the same order a puzzle's answer is drawn in, so a
    heavy rule stays continuous across a filled square. A cross is drawn
    corner to corner at the layout's thin rule.

    The image returned starts at the drawing's left edge (minus a heavy rule
    of white) and at the grid's top edge (minus a heavy rule of white).
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


def page_is_right_hand(page_number: int) -> bool:
    """Whether interior page ``page_number`` (1-based) is a right-hand page.

    Parity counts from the interior's page 1, the guide page, which is
    right-hand: odd pages are right-hand, even pages left-hand (FR-043).
    """
    if page_number < 1:
        raise ValueError(f"interior pages are numbered from 1, got {page_number}")
    return page_number % 2 == 1


def interior_page_count(
    puzzle_count: int,
    puzzle_pages: Optional[int] = None,
    answer_pages: Optional[int] = None,
    level_dividers: Optional[int] = None,
) -> int:
    """The interior's page count for ``puzzle_count`` rendered puzzles.

    The page plan :meth:`BookPDFGenerator.interior` builds — one guide page,
    one divider per non-empty level, the puzzle pages, then (only when there
    are puzzles) the SOLUTIONS divider and the answer pages; never the cover
    (FR-030 as amended by FR-043).
    ``interior`` checks its own output against this, so a change to the make-up
    of the pages that forgets this function fails loudly instead of shipping a
    book whose stated page count is not its page count.

    Two of the three terms are **measured by the passes that decide them**, and
    both default to the un-shortened plan:

    ``puzzle_pages`` is how many pages those puzzles actually take. It is
    ``puzzle_count`` — one page each — until two-up pairing shortens it
    (FR-040).

    ``answer_pages`` is how many pages the answer section actually takes.
    Since CARD-198 it is always ``puzzle_count`` — one full solved page per
    puzzle, no packing — so the parameter now carries its own default value
    rather than a shortened one; it exists at all only because
    :func:`~nonogram.admin.book_kdp.unpaired_interior_page_count` still passes
    it explicitly, and so that a caller built against the FR-042/CARD-134
    packed key (before CARD-198) is not silently misread. Before CARD-198
    this term was the *packed* key's page count
    (:func:`~nonogram.admin.book_answer_key.pack_answer_pages`, AC-270), which
    on the default 150-puzzle plan took 150 answer pages down to 30 — a
    saving this function no longer has anything to apply.

    So **called with the count alone this is the un-paired plan**: the number
    the Finalise screen has always shown, an upper bound on every book, and
    the "before pairing" half of the saving FR-040 asks the generator to
    report. ``app.py``'s Finalise screen still calls it that way and still
    labels the figure "~" (CARD-129 owns making that count exact, EC-034).
    Since CARD-198 the "before pairing" figure differs from the paired one by
    the two-up pairing term alone — there is no packing saving left to bundle
    into it.

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
    return 1 + dividers + pages + (answers + 1 if puzzle_count else 0)


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

    Used since CARD-198 for validation only — no packing reads this number any
    longer — but taken from the **grid** rather than from the row's
    ``width``/``height`` columns for the same reason it always was: the grid
    is what is actually drawn, and a row whose columns disagreed with its
    grid must be caught here rather than reaching a renderer that trusts the
    grid alone.

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

    Raises:
        ValueError: the grid is missing, empty, not a sequence of rows, or its
            rows are not all the same length — not a rectangle, so not a
            nonogram's solution. The message names the puzzle by its print
            number, which is the handle every other abort of
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
    return columns, rows


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

        Args:
            book_title: Title for the book
            cover_image: Optional pre-built cover image

        Returns:
            Cover page as PIL Image
        """
        if cover_image:
            # Use provided cover, resized to standard page size
            return cover_image.resize((self.page_width_px, self.page_height_px), Image.Resampling.LANCZOS)

        # Create blank cover with title
        cover = Image.new("RGB", (self.page_width_px, self.page_height_px), "white")
        draw = ImageDraw.Draw(cover)

        # Try to load a nice font, fall back to default
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 72)
        except OSError:
            # Fallback font
            title_font = ImageFont.load_default()

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
        """The guide page: "How to Solve Nonograms" and a worked example (FR-041).

        Args:
            puzzle_count: Total number of puzzles
            easy_count: Number of easy puzzles
            medium_count: Number of medium puzzles
            hard_count: Number of hard puzzles
            page_number: Its 1-based position in the interior. The guide page
                *is* interior page 1 (FR-043), so the default is the only
                value the export uses; it is a parameter because the page's
                margins are mirrored by that position like any other page's.

        Three counts, one per tier, since CARD-098 retired ADR-0025's fourth.

        **Its type is stated in points** — :data:`GUIDE_BODY_PT`,
        :data:`GUIDE_TITLE_PT`, :data:`GUIDE_LEADING_PT` — and converted to
        the page's pixels once, against :attr:`dpi`, by :func:`type_px`
        (CARD-149). The title is set smaller only when it is wider than the
        usable measure, and never below the body size.

        **The worked example (CARD-167).** :data:`WORKED_EXAMPLE_STEPS`, each
        step a caption over the line drawn by :func:`draw_example_line` from
        :func:`example_line_layout` — the book's own cell, rules and clue
        size. Text is wrapped to the usable measure. The page is set in the
        first of three forms whose last mark sits above the bottom margin: the
        full one (a short explanation, the puzzle counts, the example with
        full captions, a closing line); the example with full captions alone;
        or the example with short labels, which is drawn whatever happens. It
        is always one page.

        Returns:
            Guide page as PIL Image
        """
        spec = self.page_spec(page_number)
        frame = page_frame(spec)
        guide = Image.new("RGB", (frame.width, frame.height), "white")
        draw = ImageDraw.Draw(guide)

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
        # On a narrow trim the title is wider than the measure: set it a pixel
        # smaller at a time until it fits, never below the body size.
        while title_size > body_size and title_font.getlength(GUIDE_TITLE) > measure:
            title_size -= 1
            title_font = _guide_face(title_size)

        # Inside the usable area the layout reported, so the guide page keeps
        # the book's mirrored margins like every other interior page.
        draw.text((frame.left, frame.top), GUIDE_TITLE, fill="black", font=title_font)

        example = example_line_layout(spec)
        lines = [draw_example_line(example, step) for step in WORKED_EXAMPLE_STEPS]
        first = frame.top + type_px(GUIDE_TITLE_GAP_PT, self.dpi)
        ascent, descent = text_font.getmetrics()

        def set_page(full: bool, captions: bool) -> Tuple[List[Tuple[int, Any]], int]:
            """Every mark below the title as ``(y, text or image)``, and the
            lowest pixel they reach."""
            marks: List[Tuple[int, Any]] = []
            y = first
            bottom = y

            def paragraph(text: str) -> None:
                nonlocal y, bottom
                for line in wrap_words(text, text_font, measure):
                    marks.append((y, line))
                    bottom = y + ascent + descent
                    y += leading

            if full:
                paragraph(GUIDE_INTRO)
                y += leading
                paragraph(f"This book contains {puzzle_count} puzzles:")
                paragraph(f"Easy: {easy_count}")
                paragraph(f"Medium: {medium_count}")
                paragraph(f"Hard: {hard_count}")
                y += leading
                paragraph(GUIDE_EXAMPLE_HEADING)
            for step, image in zip(WORKED_EXAMPLE_STEPS, lines):
                paragraph(step.caption if captions else step.label)
                marks.append((y, image))
                bottom = y + image.height
                y = bottom + leading // 2
            if full:
                y += leading // 2
                paragraph(GUIDE_CLOSING)
            return marks, bottom

        for full, captions in ((True, True), (False, True), (False, False)):
            marks, bottom = set_page(full, captions)
            if bottom <= frame.bottom:
                break
        for y, mark in marks:
            if isinstance(mark, str):
                draw.text((frame.left, y), mark, fill="black", font=text_font)
            else:
                guide.paste(mark, (frame.left, y))

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
        """
        frame = page_frame(self.page_spec(page_number))
        divider = Image.new("RGB", (frame.width, frame.height), "white")
        draw = ImageDraw.Draw(divider)
        divider_font = _guide_face(type_px(DIVIDER_PT, self.dpi))

        bbox = draw.textbbox((0, 0), text, font=divider_font)
        x = (frame.width - (bbox[2] - bbox[0])) // 2
        y = (frame.height - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), text, fill="black", font=divider_font)
        return divider

    def export_book(
        self,
        puzzles: List[dict],
        book_title: str,
        cover_image: Optional[Image.Image] = None,
    ) -> BookExport:
        """Export a book as its two files: the interior PDF and the cover file.

        The one entry point every export route goes through (FR-043, INV-013).
        The interior holds no cover page — its page 1 is the guide page — and
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
        """
        blank, _ = render_pages(
            self._puzzle_payload(payload, puzzle_number),
            page_spec=self.page_spec(puzzle_page),
        )
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
        return page

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

        # Step 3: fill every solved cell, the same xs/ys-between-grid-lines
        # approach `pdf._reveal` uses — reimplemented rather than imported
        # (CLAUDE.md: capability modules reimplement rather than import
        # across; `_reveal` is private to `export.pdf` besides).
        grid = payload.grid
        xs = [line.position for line in layout.vertical_lines]
        ys = [line.position for line in layout.horizontal_lines]
        for row_index, row in enumerate(grid[: layout.rows]):
            for column_index, filled in enumerate(row[: layout.columns]):
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

        # Step 4: every thin/heavy rule and the frame, pure black, over the
        # fills — reused verbatim (G-2). ADR-0037/R2 stays literally true:
        # this call is not edited, so the book's own rules are still drawn
        # pure black everywhere, including over a filled run.
        _stroke_drawing(draw, layout)

        # Step 5 (this card's actual addition): re-stroke, in gray, the one
        # line segment between every pair of grid-adjacent cells that are
        # both filled — at that boundary's own already-computed width, so the
        # every-5th rhythm survives in gray across a filled run too. An outer
        # border (c == 0 or c == columns, r == 0 or r == rows) is never
        # reached by this loop, because it only ever indexes an *interior*
        # boundary — never "between two filled cells" since one side would be
        # outside the grid.
        for c in range(1, layout.columns):
            width = layout.vertical_lines[c].width
            x = xs[c]
            for r in range(layout.rows):
                if grid[r][c - 1] and grid[r][c]:
                    draw.line(
                        [(x, ys[r]), (x, ys[r + 1])],
                        fill=_SOLVED_GRID_GRAY,
                        width=width,
                    )
        for r in range(1, layout.rows):
            width = layout.horizontal_lines[r].width
            y = ys[r]
            for c in range(layout.columns):
                if grid[r - 1][c] and grid[r][c]:
                    draw.line(
                        [(xs[c], y), (xs[c + 1], y)],
                        fill=_SOLVED_GRID_GRAY,
                        width=width,
                    )

        # Step 6: clue digits — reused verbatim. Exempt from CON-020's 10 pt
        # floor (2026-10-06 amendment), exactly as on an unsolved page.
        _write_clues(draw, layout)

        placement = layout.page
        if placement is None:  # pragma: no cover - page_spec always carries a parity
            raise ValueError(f"page {page_number} is not a placed book page")

        # Step 7: the title band — reused verbatim, the same call an unsolved
        # page's own band is set from (:meth:`_puzzle_payload`'s band text,
        # via `render_pages`) and the same call a two-up slot's band is set
        # from, above.
        _set_band(
            draw,
            header_band(layout),
            band_identity(puzzle_number, payload.difficulty),
            placement.usable_right - placement.usable_left,
        )

        # Step 8: the caption, below the drawing, in the slack between
        # `drawing_bottom` and `usable_bottom` — never inside the trim
        # margin, never overlapping the grid. Font is the packaged DejaVu
        # face at `layout.ANSWER_TEXT_FONT_MM` in device pixels (exactly
        # 10 pt, the literal CON-020 floor, reused from `export.layout`,
        # never shrunk further) via this module's own `_band_font`. The mm
        # -> px conversion goes through this module's own `type_px` (its
        # docstring: "the one place this module turns a type size into
        # pixels") rather than reimplementing `round(mm / 25.4 * dpi)` inline
        # a second time — `type_px` is a sibling function in THIS same file,
        # not an import across a capability-module boundary, so CLAUDE.md's
        # reimplement-rather-than-import-across rule does not justify
        # duplicating it (forge:review F-002). `ANSWER_TEXT_FONT_MM` is
        # exactly 10pt expressed in mm (`export.layout.ANSWER_TEXT_FONT_MM
        # = 10 * 25.4 / 72`), converted back to points here so the single
        # source of truth for the size stays `export.layout`'s constant.
        #
        # If the slack is smaller than the caption's own line height (the
        # font's ascent + descent), the caption is omitted rather than
        # overlapping the drawing or spilling into the margin — a real limit
        # of a page-fit-bound puzzle (AC-6), not solved by this card.
        caption_font_points = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
        caption_font_size = type_px(caption_font_points, self.dpi)
        caption_font = _band_font(caption_font_size)
        ascent, descent = caption_font.getmetrics()
        line_height = ascent + descent
        slack = placement.usable_bottom - placement.drawing_bottom
        if slack >= line_height:
            caption = answer_caption(puzzle_number, title)
            draw.text(
                (
                    (placement.drawing_left + placement.drawing_right) / 2,
                    (placement.drawing_bottom + placement.usable_bottom) / 2,
                ),
                caption,
                font=caption_font,
                fill=INK,
                anchor="mm",
            )
        return page

    def puzzle_pages(
        self,
        payloads: List[ExportPayload],
        first_page: int = 2,
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

        Args:
            payloads: The drawable puzzles in print order. A payload's
                ``difficulty`` is the row's stored tier text, and its clue sets
                are what the pair is fitted from.
            first_page: The interior position of the first puzzle page. Page 1
                is the guide page, so the default is 2 — which is what it is
                for a book with no levels to divide; with CARD-128's dividers
                :meth:`puzzle_section` passes the page after each level's
                divider instead.
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
                try:
                    pair = compute_pair_layout(
                        (first.row_clues, first.column_clues),
                        (second.row_clues, second.column_clues),
                        self.page_spec(page_number),
                    )
                except Exception as e:
                    raise RuntimeError(
                        f"puzzle {_named_puzzles(ids, numbers, first_number)} "
                        f"could not be laid out: {e}"
                    ) from e
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
        first_page: int = 2,
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

        Args:
            payloads: The drawable puzzles in print order.
            first_page: The interior position of the section's first page,
                which is the first level's divider. Page 1 is the guide page,
                so the default is 2.
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
          (FR-040, INV-010).

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
            themselves and their ids, and the section's pages.

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
        return SectionPlan(
            puzzles=ordered,
            ids=ids,
            printed=printed,
            payloads=payloads,
            pages=self.puzzle_section(payloads, ids=ids),
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

        ``pages[n - 1]`` is interior page ``n``: page 1 is the guide page,
        a right-hand page (:func:`page_is_right_hand`), followed by the puzzle
        section — a divider page opening each non-empty level and that level's
        puzzle pages (:meth:`puzzle_section`, FR-041) — then the SOLUTIONS
        divider and the answer pages. The list's length is the book's page
        count (FR-030); the cover is never counted.

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

        *Drawn later, lazily, one page per :func:`next`.* The guide page, each
        level's divider and the puzzle pages the walk planned, the SOLUTIONS
        divider and one full solved page per puzzle (CARD-198), each on the
        spec of its own interior position (FR-043), each built when it is
        asked for and released when the next one is.
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

        # The validation half of the old packed key's walk, with nothing left
        # to pack (CARD-198): each answer's grid must still be a non-empty
        # rectangle, checked and named before any page is drawn, because
        # `app.py`'s `_is_an_unpackable_row` matches exactly this abort shape
        # (G-6) and a book with a malformed row must still fail here rather
        # than partway through the answer loop below.
        for index, (_, payload) in enumerate(payloads):
            number = index + 1
            try:
                _answer_extent(payload, number)
            except ValueError as e:
                raise RuntimeError(
                    f"puzzle {_named_puzzles(ids, (number,))} could not be "
                    f"laid out: {e}"
                ) from e

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
        # Every page of the section — dividers included — sits between the
        # guide page and the SOLUTIONS divider, so both of those positions
        # count the section's length and not its puzzle pages alone.
        first_answer_page = 3 + len(section)

        # Calculate difficulty counts for guide — over every member of the
        # book, drawable or not, because that is what the book holds. Read
        # here, with the custom titles, rather than inside the walk below:
        # everything that can fail without drawing fails before the caller has
        # a file open.
        counts = tier_breakdown(puzzles)
        titles = self.custom_titles()

        # The page plan is this function's own make-up; fail loudly rather
        # than let the two drift apart. It is taken over this call's *input* —
        # the puzzles that survived the payload pass — and over the walk's own
        # verdict on how many pages it takes, never over the pages the walk
        # below produces, so a change to the make-up of the pages (a divider
        # per level, say) that forgets `interior_page_count` is caught rather
        # than shipping a book whose stated page count is not its page count.
        # Since CARD-145 the two sides meet in `_as_planned`, as the pages go
        # past, instead of in a `len()` over a list nobody can afford to
        # build. `count` is the answer term since CARD-198: one page per
        # puzzle, no packing to measure.
        planned = interior_page_count(count, len(plan), count, dividers)

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
            yield self.create_guide_page(
                len(puzzles),
                counts[Tier.EASY],
                counts[Tier.MEDIUM],
                counts[Tier.HARD],
                page_number=1,
            )

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
            # (CARD-145's AC-3 pins that page for page).
            if not payloads:
                return
            yield self.create_divider_page(2 + len(section))
            for index, (puzzle_id, payload) in enumerate(payloads):
                number = index + 1
                try:
                    page = self.solved_puzzle_page(
                        payload,
                        number,
                        first_answer_page + index,
                        title=answer_title(
                            titles.get(str(puzzle_id)), payload.name
                        ),
                    )
                except Exception as e:
                    named = _named_puzzles(ids, (number,))
                    raise RuntimeError(
                        f"puzzle {named} could not be drawn: {e}"
                    ) from e
                yield page
                del page

        return InteriorStream(
            page_count=planned,
            # Before **pairing**, and only that (CARD-198: there is no
            # packing saving left to bundle in): the puzzle-page term alone is
            # unshortened here, so `pages_saved` measures the two-up pages and
            # nothing else.
            unpaired_page_count=interior_page_count(
                count, answer_pages=count, level_dividers=dividers
            ),
            answer_page_count=count,
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
