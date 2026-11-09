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

**Since CARD-248 the walk reserves the footer strip, and that is still a
verdict about the pair's page and not about the book.** A two-up page carries
one footer, so the walk tells ``compute_pair_layout`` to reserve that strip out
of the pair's height
(:attr:`~nonogram.export.layout.InteriorFrame.footer_depth`); a pair that cannot
reach the 7.0 mm floor with it reserved prints on two single pages, each with
its own footer, which is one more interior page. **Until CARD-391 the walk
also refused a pair whose footer could not hold both puzzles' QR groups side
by side; that clause (c) is gone with the groups** (ADR-0041/R8), so a narrow
trim now pairs on the height and width rules alone. The folio reserve is a
constant of the sheet and the face — :func:`_folio_reserve_px` is measured from
the font and the DPI alone — so neither lets a page number or a book's own
scale decide whether two puzzles pair (INV-010).

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

import enum
import logging
import math
import time
import unicodedata
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from functools import lru_cache
from importlib import resources
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional, List, Sequence, Tuple, Union
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
from nonogram.admin.book_dividers import (
    SOLUTIONS_SLOT,
    fit_to_page,
    require_slot,
    slot_for_level,
)
from nonogram.admin.book_page_spec import (
    GridSize,
    InkMode,
    book_cell_sizes,
    book_cell_spec,
    book_divider_pages,
    book_ink_mode,
    book_page_spec,
)
from nonogram.admin.book_plan import TIERS, book_level_order
from nonogram.admin.print_specs import printable_player_domain
from nonogram.admin.book_puzzle_vector import puzzle_page_stream, two_up_page_stream
from nonogram.admin.book_sheet_vector import (
    SheetFurniture,
    draw_sheet_furniture,
)
from nonogram.admin.book_vector import (
    ContentStream,
    FontMetrics,
    UnrepresentableText,
    encode_text,
    interior_face_bytes,
    interior_face_metrics,
    write_face_objects,
    write_vector_page,
)
from nonogram.difficulty import Tier, tier_of_record
from nonogram.errors import UnletterableTitle, UnsettablePuzzleTitle
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    ANSWER_TEXT_FONT_MM,
    DPI,
    INTERIOR_FOOTER_LINE_PT,
    DifficultyDots,
    HeaderBand,
    Layout,
    PageSpec,
    PairLayout,
    compute_layout,
    compute_packed_solved_layout,
    compute_pair_layout,
    difficulty_dots,
    header_band,
    interior_frame,
)
from nonogram.export.pdf import FONT_PACKAGE, FONT_RESOURCE
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


class PageKind(enum.Enum):
    """Every kind of page this module writes, as the medium decision sees it.

    ADR-0042/R2 (CARD-298). A *kind* is not a page count and not a method
    name: it is the one axis the choice of medium is made on, so the members
    below are exactly the distinctions ADR-0042 draws and no finer. The ADR
    names four interior kinds — "puzzle pages, answer pages, the table of
    contents and the guide" — plus the cover, and the owner's 2026-10-25
    decision names the section divider; :data:`TITLE_PAGE_COUNT`'s blank
    title/copyright page is the sixth, which the ADR does not mention because
    it carries no ink of any kind (:meth:`BookPDFGenerator.create_title_page`).

    An enumeration rather than strings, so :func:`page_medium` can be
    default-DENY on something that is not a kind at all instead of returning
    a medium for a typo.
    """

    COVER = "cover"
    TITLE = "title"
    GUIDE = "guide"
    TOC = "toc"
    DIVIDER = "divider"
    PUZZLE = "puzzle"
    #: The page that carries the book's one QR code, after the last puzzle
    #: (CARD-390). A vector page with no raster declaration, like every
    #: interior kind that is not a picture.
    PLAY = "play"
    #: A page that exists only to put the next one on a right-hand page
    #: (CARD-390): no ink and no folio, the blank title page's own shape.
    BLANK = "blank"
    ANSWER = "answer"


class PageMedium(enum.Enum):
    """How one page is written: as operators, or as a bitmap.

    ``VECTOR`` is ADR-0042/R1's page — two PDF objects, a page and a
    FlateDecoded content stream, no image XObject. ``RASTER`` is the page
    Pillow's own plugin writes — three objects, the extra one a DCTDecode
    image — and is reached only through a live :class:`RasterDeclaration`
    (ADR-0042/R2).
    """

    RASTER = "raster"
    VECTOR = "vector"


@dataclass(frozen=True)
class RasterDeclaration:
    """One page kind's declared exception to ADR-0042/R1, with its reason.

    ADR-0042/R2's "declared, with its reason", as data rather than as prose:
    the registry below is what :func:`page_medium` reads, and it is also what
    ``tests/test_book_pdf.py``'s R2 guard reads, so the declaration a reader
    sees and the declaration the writer obeys cannot be two different things.

    Attributes:
        reason: Why this kind is a bitmap. One sentence, and a *reason* —
            "it is a photograph", not "it has not been converted".
        authority: The decision that permits it, by name: an ADR rule, or an
            owner decision with its date. A declaration with no authority is
            somebody's preference.
        expires_with: The card ids that between them remove this exception, or
            ``()`` for an exception with no end — the cover's. **A declaration
            that names a card is a temporary one**, and it can go stale in
            **two** directions, which two different tests notice:

            * the page is converted and this entry is left behind —
              ``test_a_declaration_whose_reason_expired_is_a_defect``;
            * the last card named here reaches ``done`` and this entry is
              still present — ``test_a_declaration_outliving_its_done_card``
              ``_is_a_defect``, which reads each card's ``**Status:**`` off
              ``meta/kanban/cards/``.

            Neither direction implies the other, which is why both exist: a
            card can close without converting its page (measured — CARD-298's
            review cycle 1 found all five interior entries naming CARD-299,
            which converts no page), and a page can convert while the card
            that owns it is still open. It is a tuple because a kind can be
            held raster by more than one unlanded piece of work, and a
            declaration that named only the first of them would read as
            nearly clear when it is not; **the expiry is the day the LAST of
            them is done**, so an entry still present then is the defect.
    """

    reason: str
    authority: str
    expires_with: Tuple[str, ...] = ()


#: The **whole** of ADR-0042/R2's declared set, keyed by page kind: the two
#: pages that are still a bitmap, and nothing else.
#:
#: **Both are permanent.** The cover is "a photograph and raster is the right
#: representation for it", and since CARD-311 the section divider is the same
#: thing: a picture the owner uploads (``book_dividers``), which is a bitmap by
#: nature and has no vector form to be converted to. The divider's old
#: exception was scheduling (CARD-231 was to redesign the page "born vector");
#: that card is parked, because uploaded dividers replace it.
#:
#: **CARD-322 removed five entries**, the title, guide, TOC, answer and puzzle
#: kinds, when it flipped ADR-0042/R1: every interior page of those kinds is
#: written as PDF content-stream operators on every export path, through
#: ``nonogram.admin.book_interior_vector``. The reasons those entries carried
#: (a reader conversion still owed, a placed-edge convention still undecided)
#: were cleared by the slice cards and by CARD-322 itself, and are in git and
#: in those cards' notes, not here: a declaration that names a blocker which
#: has been cleared reads as further from done than it is.
#:
#: No count of the live mapping is written here. A number in a comment nobody
#: re-reads is what goes stale when the mapping changes again (CARD-261 found
#: it twice), so the live shape is pinned where it can be checked: by
#: ``tests/test_book_pdf.py``'s
#: ``TestRasterDeclarations_TheCommentAgreesWithTheRegistry``, which holds
#: these lines to the mapping in both directions.
#:
#: **An entry that names cards is a temporary one, and the shrink is guarded in
#: two directions** (the two permanent entries name none).
#: ``test_a_declaration_whose_reason_expired_is_a_defect`` reds the day a kind
#: goes vector and its entry stays (the CONVERSION direction);
#: ``test_a_declaration_outliving_its_done_card_is_a_defect`` reds the day the
#: last card named in an ``expires_with`` reaches ``done`` and the entry is
#: still here (the LANDING direction). Reading a card file tells you the card
#: is *done*; it does not tell you the conversion happened, which is why there
#: are two.
#:
#: **Nothing else may be a bitmap.** :func:`page_medium` returns ``VECTOR``
#: for every kind absent from this mapping, so a new page kind is vector by
#: default and a kind that wants to be a bitmap has to say why here -- which is
#: the direction ADR-0042/R2 asks for and the opposite of a vector allow-list.
_RASTER_DECLARATIONS: Dict[PageKind, RasterDeclaration] = {
    PageKind.COVER: RasterDeclaration(
        reason=(
            "a cover is a photograph the owner uploaded, and raster is the "
            "right representation for a photograph"
        ),
        authority="ADR-0042/R2",
        expires_with=(),
    ),
    PageKind.DIVIDER: RasterDeclaration(
        reason=(
            "a divider is a picture the owner uploaded, and a picture is a "
            "bitmap by nature; its lettering is the owner's, so CON-020's "
            "10 pt floor, which is checked on text this module sets, is "
            "not claimed for it (book_dividers)"
        ),
        authority="owner decision 2026-11-06 (dividers are uploaded), CARD-311",
        expires_with=(),
    ),
}


def page_medium(kind: PageKind) -> PageMedium:
    """How a page of ``kind`` is written — **the one place this is decided**.

    AC-4. Every medium in every book file this module writes comes from this
    call: :meth:`BookPDFGenerator._write_pdf` is handed page *kinds* and asks
    here, so neither the interior's page loop nor the cover's chooses a medium
    of its own. ``TestWritePdf_TheMediumIsChosenInOnePlace`` derives that from
    the module's AST and fails on a second site — and on a site whose shape it
    cannot classify, which is ADR-0039/R2.

    **Default-DENY, in both directions.** A ``kind`` that is not a
    :class:`PageKind` raises rather than falling through to a medium; and a
    kind that *is* one is vector unless :data:`_RASTER_DECLARATIONS` says
    otherwise, so forgetting to declare a new bitmap page kind makes the
    writer refuse the page object it is handed rather than quietly ship a
    DCTDecode interior.

    Raises:
        TypeError: ``kind`` is not a :class:`PageKind`.
    """
    if not isinstance(kind, PageKind):
        raise TypeError(
            f"a page medium is chosen per page kind, not for {kind!r}"
        )
    return PageMedium.RASTER if kind in _RASTER_DECLARATIONS else PageMedium.VECTOR


@dataclass(frozen=True)
class InteriorPageWriters:
    """The interior page writers that live **downstream of this module**.

    CARD-309, ADR-0042/R1's assembly point, as a parameter rather than as an
    import. Three of the four vector interior writers —
    :mod:`nonogram.admin.book_guide_vector`,
    :mod:`nonogram.admin.book_toc_vector` and
    :mod:`nonogram.admin.book_answer_vector` — import **this** module at module
    level, for the constants, the type sizes and the frame helpers the pages
    are composed from. So the interior's page walk
    (:meth:`BookPDFGenerator.interior_stream`) cannot import them back: it
    would be a cycle, and a lazy import inside the walk would be the same
    cycle with the direction hidden in a function body.

    What this class does instead is **state the shape the walk needs and
    nothing else**. The walk calls through an instance; the only module that
    can *build* one is :mod:`nonogram.admin.book_interior_vector`, which is
    downstream of all five writers and which nothing in ``src/`` imports. The
    puzzle page needs no entry here: :mod:`nonogram.admin.book_puzzle_vector`
    imports no generator, so this module already imports it directly and
    :meth:`BookPDFGenerator.vector_puzzle_page` composes the page here
    (CARD-295/CARD-306).

    **Default-DENY.** A field left ``None`` is not a fallback to the bitmap:
    :func:`page_medium` is the only thing that decides a medium, and a kind it
    calls ``VECTOR`` with no writer here is a **refusal** naming the assembly
    point (:func:`_drawn_downstream`). A generator built with no writers at
    all therefore keeps writing exactly the book it wrote before this card, and
    stops dead the moment a declaration is lifted underneath it rather than
    shipping a bitmap under a vector declaration.

    Attributes:
        guide: ``(spec, dpi, page_number, *, puzzle_count, easy_count,
            medium_count, hard_count, play_page) -> ContentStream`` — one page
            of the 2-page tutorial, the twin of
            :meth:`BookPDFGenerator.create_guide_page`. ``play_page`` is the
            Play online page's interior page number, ``None`` for a book that
            prints none (CARD-229).
        toc: ``(rows, frame, dpi, page_number) -> ContentStream`` — one page of
            the table of contents over **its own slice** of the entries, the
            twin of :meth:`BookPDFGenerator.create_toc_page`.
        answer: ``(spec, dpi, payload, puzzle_number, page_number, title) ->
            ContentStream`` — one full solved page, the twin of
            :meth:`BookPDFGenerator.solved_puzzle_page`.
        packed_answer: ``(spec, dpi, plan, payloads, page_number, titles) ->
            ContentStream`` — one page of 2 or 4 small answers (CARD-202), the
            twin of :meth:`BookPDFGenerator._packed_answer_page`.
        play: ``(spec, dpi, page_number, rows, player_domain) ->
            ContentStream`` — the Play online page (CARD-390). It has no
            raster twin. ``rows`` is the book's rows in print order and
            ``player_domain`` its stored domain: the landing address is made
            downstream, where :mod:`nonogram.admin.player_bundle` (which
            imports this module) can be reached, so the walk holds no second
            way to spell the address.

    Each signature is the downstream writer's **own**, in its own order, so
    the assembly point binds rather than adapts: a shape stated here that the
    writer does not have would be a second opinion about how a page is drawn.
    """

    guide: Optional[Any] = None
    toc: Optional[Any] = None
    answer: Optional[Any] = None
    packed_answer: Optional[Any] = None
    play: Optional[Any] = None


#: An interior with no downstream writers at all — the generator every route
#: builds today, and the one whose interior is byte-for-byte what it was
#: before CARD-309 for every kind this module can draw itself.
NO_DOWNSTREAM_WRITERS = InteriorPageWriters()


def _drawn_downstream(
    writer: Optional[Any], kind: PageKind, *args: Any, **keywords: Any
) -> "ContentStream":
    """One page of ``kind``, drawn by a writer that lives downstream of here.

    **The one place this module calls an injected callable**, and the reason
    it is one place is not tidiness. ``tests/test_book_export_interior_cover.py``'s
    door-axis walk over this module is **default-DENY over every**
    ``ast.Call``: it refuses a callee it cannot anchor to a definition this
    module's own text shows, and a refusal there is a failure and not a pass
    (ADR-0039/R2). An injected writer is by construction such a callee — a
    value, not a definition — so a gate that called ``self.pages.guide(...)``
    in place, or bound it to a local first, put a refusal in that walk for
    **every** gate (measured: four). Here the callee is this function's own
    ``writer`` **parameter**, which is one of that guard's declared and
    controlled blind spots (*"the CALL-GRAPH axis: a parameter used as a
    callee"*), so the whole of this card's indirection costs that walk
    nothing it had not already declared — and the four gates above call a
    module-level definition, which it anchors.

    The arguments are forwarded as they arrive: each writer's signature is its
    own (:class:`InteriorPageWriters` states them), and a per-kind wrapper
    here would be four more places for a signature to drift from the writer
    it names.

    **Default-DENY.** Reached only when :func:`page_medium` has already said
    ``VECTOR`` for ``kind``, so there is no bitmap left to fall back to and
    falling back is exactly what must not happen: ``_write_pdf``'s own
    representation refusal would catch a bitmap arriving under a vector
    declaration (G-6), and this says the same thing one step earlier, where
    the message can name the assembly point instead of a type.

    Raises:
        ValueError: ``kind`` is declared vector and this generator was built
            with no writer for it.
    """
    if writer is None:
        raise ValueError(
            f"a {kind.value} page is written as operators (ADR-0042/R1) and "
            "this generator was built with no downstream writer for it: "
            "compose the interior through "
            "nonogram.admin.book_interior_vector, the one module that may "
            "import both this one and the page writers that import it"
        )
    return writer(*args, **keywords)


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

#: Whether a level's divider with no uploaded picture is drawn in the
#: Solutions opener's style -- rule, "PUZZLES a–b", the level's name large,
#: its dots (:meth:`BookPDFGenerator.create_level_divider`, owner decision
#: 2026-11-09) -- rather than as the one centred word
#: (:meth:`BookPDFGenerator.create_divider_page`, AC-254).
LEVEL_DIVIDER_OPENER = True

#: How many interior pages the book's title / copyright page occupies
#: (FR-043, INV-013 as amended 2026-10-17, AC-283, CARD-206): one, and it is
#: interior page 1 — a right-hand page carrying **no folio and no ink at
#: all**. The page is *reserved* by the page plan rather than populated
#: (owner decision 2026-10-13: "leave it blank (template page) — reserve the
#: page in the page plan so counts and parity are right, print nothing on
#: it"), so the copyright text is set into the exported PDF afterwards.
#:
#: The front-matter positions after it count from here rather than from a
#: literal, which is the whole reason it is a named constant and not a bare
#: ``1`` in :meth:`BookPDFGenerator.interior_stream`: the guide's own two
#: pages, the TOC's, :meth:`BookPDFGenerator.section_plan`'s ``first_page``,
#: the SOLUTIONS divider, :func:`interior_page_count`'s formula and —
#: through that same formula —
#: :func:`~nonogram.admin.book_kdp.unpaired_interior_page_count`, which is
#: the figure KDP's gutter band is read at.
#:
#: **That sentence is a claim, and this is the control it is held to**
#: (CARD-206 review F-102): ``TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage``
#: derives this module's page positions from the one geometry door they all
#: reach — :meth:`BookPDFGenerator.page_spec` — and fails on any integer
#: literal other than ``0`` or ``1`` in one of them. What that reaches, and
#: what it still cannot see, is the test's own to state; before the fix it
#: reached only the expressions that load :data:`GUIDE_PAGE_COUNT`, and a
#: bare ``3 + len(section)`` sat nine statements from the position it was
#: supposed to be a duplicate of.
TITLE_PAGE_COUNT = 1

#: How many interior pages the guide occupies (FR-041, CARD-201): a term of
#: :func:`interior_page_count`'s formula, named rather than a bare ``2`` in
#: that function's return statement. ``1`` until CARD-201's
#: "full 1-2 page tutorial" (FR-041's own deferred clause) landed as 2 pages.
#:
#: It is no longer the formula's *leading* term: since CARD-206 the guide
#: follows :data:`TITLE_PAGE_COUNT`, on interior pages 2 (a verso) and 3
#: (a recto), which is what lets the two pages face each other.
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
#: into the band's reserved foot row (G-1).
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

#: The promise under the intro (owner, 2026-11-09): what every puzzle in the
#: book is, so a reader knows a stuck grid is not a broken one.
GUIDE_PROMISE = (
    "Each puzzle hides a picture and has just one solution, checked by computer."
)

#: The line that introduces the worked example on the page's full form,
#: built from the clue and the row length it names (CARD-169).
GUIDE_EXAMPLE_HEADING = (
    "Worked example: the clue "
    + " ".join(str(run) for run in WORKED_EXAMPLE_CLUE)
    + f" on a row of {WORKED_EXAMPLE_LENGTH} squares."
)

#: The line under the guide's intro that names the Play online page (CARD-229,
#: folded in from CARD-393; the owner's wording, ADR-0041/R8). ``{page}`` is the
#: Play page's interior page number, a described variable: the guide prints the
#: sentence only for a book whose plan prints that page, so the number it names
#: is always a page that exists (:func:`guide_play_sentence`). Reworded by the
#: owner on 2026-11-09 so it no longer opens like the promise above it.
GUIDE_PLAY_SENTENCE = (
    "You can also play them all online: scan the code on page {page}."
)


def guide_play_sentence(page: int) -> str:
    """:data:`GUIDE_PLAY_SENTENCE` for a Play online page at interior ``page``."""
    return GUIDE_PLAY_SENTENCE.format(page=page)


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
            data that nothing prints or reads (owner, 2026-11-08: the legend
            carries :data:`GUIDE_DIFFICULTY_LINE`, one line for the whole
            ladder, and the :attr:`name` beside CARD-228's dots, not one
            sentence per tier); both surfaces show the same heading and line.
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
#: ``text`` is therefore data this module keeps and no longer prints. (The
#: Finalise screen's preview showed it for a while, which was a divergence
#: between that screen and the page it previews; CARD-221 fix 1 cut the
#: preview to the names, and CARD-229's key strip, which moved the legend to the
#: first guide page and drew CARD-228's dots beside each name, keeps the two
#: agreeing. Printing the sentences is a wording question left to the owner.)
GUIDE_DIFFICULTY_HEADING = "Difficulty"

#: The one line under the legend's heading (owner approved 2026-11-08, the short
#: form only): what the two ends of the ladder ask of a reader. The legend is
#: this line, the heading and the three entries (CARD-228's dots beside each
#: tier's name); the per-tier sentences of :class:`DifficultyLabel` are not
#: printed.
GUIDE_DIFFICULTY_LINE = (
    "Easy puzzles need only direct deductions; Hard ones need contradiction "
    "through much of the grid."
)
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
    # BASIC, not Pillow's default RAQM when libraqm is installed: RAQM measures
    # differently (a soft hyphen as zero, kerned pairs), so the same book
    # would print different pixels on different machines.
    return ImageFont.truetype(BytesIO(_band_font_bytes()), size=size, layout_engine=ImageFont.Layout.BASIC)


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


def numbered_rows(
    puzzles: List[Any],
) -> Tuple[List[Any], List[Any], List[Any], List[ExportPayload]]:
    """The rows the interior numbers, decided once (INV-009, CARD-389).

    Returns ``(ordered, ids, printed, payloads)``: ``ordered`` is every row in
    print order (:func:`print_order`), undrawable ones included; ``ids``,
    ``printed`` and ``payloads`` are the rows that built an export payload, in
    print order and parallel, so ``printed[n - 1]`` is the row the interior
    prints as puzzle ``n``. A row whose payload cannot be built (malformed
    clues, say) is dropped here with a logged warning and takes no number.

    This is the one filter: :meth:`BookPDFGenerator.section_plan` calls it,
    and so does the player bundle when it names a book's puzzles, so the
    printed numbering and the landing page's cannot be decided twice.
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
            payload = BookPDFGenerator._payload(puzzle)
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
    return ordered, ids, printed, payloads


def puzzle_page_plan(book: Any, puzzles: List[Any]) -> List["PuzzlePagePlan"]:
    """The pages ``puzzles`` would print on in ``book``, and nothing drawn.

    The pairing walk alone (:meth:`BookPDFGenerator.puzzle_pages`), over
    puzzles **already in print order** (:func:`print_order`): no bitmap is
    made and no page is rendered, so the answer costs the geometry only. Its
    length is the book's puzzle-page count, which is the one thing CARD-251's
    editor needs — it asks this twice for one edit, once over the book's
    stored clues and once with a replacement's swapped in, and tells the owner
    when the two disagree (AC-9).

    One walk, and it is the real one. Pairing is decided by
    :func:`~nonogram.export.layout.compute_pair_layout` from the clue sets, so
    a question about "would this edit split a page" has to be asked of that
    function or it is asking about a model of it; INV-010 stays the layout's
    and a change there moves this answer with it.

    Args:
        book: The book, as :class:`BookPDFGenerator` takes it.
        puzzles: Its members as stored rows, in print order.

    Returns:
        One :class:`PuzzlePagePlan` per puzzle page, in print order. A plan's
        ``numbers`` are 1-based positions in ``puzzles``, so a page that holds
        two names both of them.

    Raises:
        ValueError: the book's stored print specification cannot be laid out.
            The failure is the **book's** and names no member: the sheet is
            laid out by :meth:`BookPDFGenerator.__init__` when the generator
            is built, before any member is measured, exactly as it was before
            CARD-225 put a cell map in front of the walk (review cycle 1,
            F-006; review cycle 2, F-001 for where the refusal really sits).
        RuntimeError: a **member** could not be measured — one whose clue sets
            disagree about its grid. The message names it (:func:`_named_puzzles`
            on the rows' own ids), and the original failure is its
            ``__cause__``.

            Since CARD-225 this is raised for such a member whether or not the
            pairing walk would have offered it to a pair: the book's cell map
            measures every member, so the member with no same-tier neighbour —
            which reached neither stage before and so aborted this entry
            nowhere — aborts it here too, named (review cycle 1, F-002; the
            card's failure matrix, row F-3).
    """
    generator = BookPDFGenerator(book)
    payloads = [generator._payload(puzzle) for puzzle in puzzles]
    ids = [puzzle.get("id") if hasattr(puzzle, "get") else None for puzzle in puzzles]
    # No sheet read of its own here, and none is needed. An unreadable stored
    # print specification is the book's failure and belongs to no member, and
    # what keeps it the bare ValueError it has always been is
    # `BookPDFGenerator.__init__`'s own `page_frame(self.page_spec(1))`: the
    # `BookPDFGenerator(book)` line above lays this book's sheet out before
    # this function has a payload to measure, so a book-level fault cannot
    # reach the cell map's handler below. This entry held a second
    # `generator.page_spec(1)` for one cycle, introduced as that mechanism; it
    # was dead — deleting it failed no test — and it is gone (review cycle 2,
    # F-001). The mechanism's own mutant lives in `__init__`.
    # CARD-225: the same whole-book cell map `section_plan` settles, so the
    # editor's "would this edit split a page" answer is asked of the pages the
    # book really prints — a pairing verdict now depends on the grid sizes'
    # own book cells (F-8), so a walk run without the map would be a model of
    # the export rather than the export.
    #
    # Routed through the same `_unmeasurable_members` helper `section_plan`
    # uses, for the same reason (review cycle 1, F-002): the map fails closed
    # for the whole book and says *that* a member will not lay out, not
    # *which*, and this entry's whole contract is that every abort names a
    # puzzle. Without this the map's ValueError reached the editor bare —
    # no name, no position, no cause — and widened this entry's abort surface
    # to a member the walk never offered anyone.
    try:
        cell_sizes = generator.cell_sizes(payloads)
    except ValueError as unmeasurable:
        raise RuntimeError(
            f"puzzle {generator._unmeasurable_members(payloads, ids)} could not "
            f"be laid out: {unmeasurable}"
        ) from unmeasurable
    # `ids` to the walk as well, for parity with `section_plan`'s own call:
    # should the walk's *other* abort ever be reached — a pair COMP-007
    # refused to measure — it would name these rows rather than the bare
    # "#1, #2" the walk falls back to. **Nothing holds this, and nothing can
    # today**: a payload `cell_sizes` measures but `compute_pair_layout`
    # refuses is not constructible through this entry, so dropping `ids`
    # here fails no test (review cycle 2, F-002). Stated as parity, not as a
    # mechanism with a control.
    return generator.puzzle_pages(payloads, ids=ids, cell_sizes=cell_sizes)


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
    # BASIC, not Pillow's default RAQM when libraqm is installed: RAQM measures
    # differently (a soft hyphen as zero, kerned pairs), so the same book
    # would print different pixels on different machines.
    return ImageFont.truetype(BytesIO(_band_font_bytes()), size=size, layout_engine=ImageFont.Layout.BASIC)


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
    (CARD-222). The frame the owner's artifact asks for gave the footer's
    outer corner to a QR icon (CARD-223, retired by CARD-391), which is where
    this folio has sat since CARD-200, so on a page that carries the frame the
    page number moves to the footer line's centre —
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


def footer_pointer_text(numbers: Sequence[int], play_page: int) -> str:
    """The footer line that points at the Play online page (CARD-391).

    ``Play puzzle 53 online · p. 167`` on a page that carries one puzzle,
    ``Play 9 and 10 online · p. 167`` on a two-up page, which shares
    ONE footer line between its two puzzles (owner rulings of 2026-11-07; the
    word "puzzles" was dropped from the shared line by the owner on 2026-11-08,
    so that it fits beside the folio on a 6 x 9 in page).
    ``numbers`` are the page's print numbers, the ones its bands and the
    answer key carry, and ``play_page`` is the Play page's interior page number
    **read from the plan** (:attr:`SectionPlan.play_page`): this function
    computes no page number, so a pointer cannot name a page the plan did not
    lay (ADR-0041/R8, G-2/G-3). The ``" · "`` is :data:`BAND_SEPARATOR`.

    Raises:
        ValueError: ``numbers`` is not one or two print positions (below 1),
            or ``play_page`` is not a page number: a line pointing at nothing
            is refused, not printed.
    """
    if play_page < 1:
        raise ValueError(f"a pointer names a page from 1, got {play_page}")
    if len(numbers) not in (1, 2) or min(numbers) < 1:
        raise ValueError(f"a page carries one or two puzzles numbered from 1, got {tuple(numbers)}")
    names = (
        f"puzzle {numbers[0]}"
        if len(numbers) == 1
        else f"{numbers[0]} and {numbers[1]}"
    )
    return f"Play {names} online{BAND_SEPARATOR}p. {play_page}"


def _guide_rule_width(spec: PageSpec) -> int:
    """This page's thin rule width, in pixels (CARD-201).

    Borrowed from a puzzle probe layout (:data:`_PROBE_CLUES`, the same probe
    :func:`page_frame` reads) so the pipeline diagram's and the difficulty
    box's borders are drawn at the same weight as every ruled line on this
    book's pages (ADR-0037/R2), through ``compute_layout`` rather than an
    invented stroke width (ADR-0036/R2, G-3).
    """
    return compute_layout(_PROBE_CLUES, _PROBE_CLUES, spec).thin_rule


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
        cell_sizes: The cell each grid size in this book prints at, in mm
            (CARD-225, NFR-008 as amended) — :meth:`BookPDFGenerator.cell_sizes`
            over :attr:`payloads`. The pages in :attr:`pages` were already
            planned with it, and it is carried here because the **single**
            puzzle pages are drawn later, by
            :meth:`BookPDFGenerator.interior_stream`, which must size them by
            the same map rather than compute a second one.
        play_page: The interior page number of the Play online page
            (CARD-390), or ``None`` when the book prints none — it has no
            stored player domain, or no puzzle to point at. A right-hand page
            by construction (:func:`recto_blank_pages`). The page numbers the
            footer pointers (CARD-391) and the guide's line (CARD-393) name are
            read from here; they compute nothing.
        play_blank_page: The interior page number of the blank page that sits
            immediately before it so it is right-hand, or ``None`` when the last
            puzzle page is a verso already (and whenever :attr:`play_page` is
            ``None``).
    """

    puzzles: List[Any]
    ids: List[Any]
    printed: List[Any]
    payloads: List[ExportPayload]
    pages: List[SectionPage]
    toc_page_count: int = 0
    cell_sizes: Dict[GridSize, float] = field(default_factory=dict)
    play_page: Optional[int] = None
    play_blank_page: Optional[int] = None

    @property
    def play_page_count(self) -> int:
        """How many pages the Play online block adds: its blank, if any, and itself."""
        return (self.play_page is not None) + (self.play_blank_page is not None)


@dataclass(frozen=True)
class Interior:
    """The interior's pages, and what two-up pairing (and, since CARD-202,
    small-answer packing) saved (FR-040, FR-042).

    Attributes:
        pages: Every interior page in print order; ``pages[n - 1]`` is interior
            page ``n``. No cover page (FR-043, INV-013).

            **Each page is in the medium its kind declares** (CARD-309,
            :func:`page_medium`): an :class:`~PIL.Image.Image` for a declared
            raster kind and a
            :class:`~nonogram.admin.book_vector.ContentStream` for a vector
            one, so a book whose puzzle pages are operators hands back a list
            that is not all bitmaps. A caller that wants to *look* at a page
            has to ask which medium it is in, which is what ADR-0042/R6 asks
            of a reader anyway — the element type widened rather than the walk
            rasterising a stream to keep it narrow.
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

    pages: List[Union[Image.Image, ContentStream]]
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
        page_kinds: One :class:`PageKind` per planned page, in print order
            (CARD-298) — the same length as :attr:`page_count` and decided by
            the same walk that decided the count, before a page exists. It is
            what :meth:`BookPDFGenerator._write_pdf` lays its object table out
            from, because the medium of a page follows from its kind
            (:func:`page_medium`) and a mixed file's object table has to be
            allocated before the catalog is written.
    """

    page_count: int
    unpaired_page_count: int
    answer_page_count: int
    pages: Iterator[Union[Image.Image, ContentStream]]
    paired_only_page_count: int = 0
    page_kinds: Tuple[PageKind, ...] = ()
    #: ``(puzzle id, title)`` for every puzzle, in print order: the title each
    #: answer caption prints (CARD-383). Read by the doors that draw, through
    #: :func:`_refuse_unsettable_titles`; the plan-only readers ignore it.
    answer_titles: Tuple[Tuple[Any, Optional[str]], ...] = ()
    #: The interior page number of the Play online page (CARD-390), or
    #: ``None`` when the book prints none: :attr:`SectionPlan.play_page`, read
    #: from the same plan the page count is, so Finalise can say where it is.
    play_page: Optional[int] = None
    #: How many pages the Play online block adds to :attr:`page_count`: 0, 1
    #: (the page) or 2 (a blank before it), so a refusal made at that count can
    #: say the block is part of it.
    play_block_pages: int = 0

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
    pages: Iterable[Union[Image.Image, ContentStream]], page_count: int
) -> Iterator[Union[Image.Image, ContentStream]]:
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


#: The strip an answer page keeps above its tiles for the running head (the
#: approved mockup's "SOLUTIONS · EASY" / "PUZZLES 1–4" line and its rule).
RUNNING_HEAD_MM = 9.0


def answer_section_spec(spec: PageSpec) -> PageSpec:
    """``spec`` with the running head's strip taken off the top of its usable area.

    Every answer page is planned and laid out on this spec, so the packing
    walk's feasibility check and the page that is finally drawn agree about
    how much room the tiles have.
    """
    return replace(spec, top_mm=spec.top_mm + RUNNING_HEAD_MM)


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
    # The guide's lines keep their clue box even though the book's puzzle
    # pages dropped the frame (owner, 2026-11-09): a diagram's clue is
    # closed off from the prose beside it.
    if spec.parity is not None:
        spec = replace(spec, frame=True)
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


def page_is_right_hand(page_number: int) -> bool:
    """Whether interior page ``page_number`` (1-based) is a right-hand page.

    Parity counts from the interior's page 1 — since CARD-206 the blank
    title page (:data:`TITLE_PAGE_COUNT`), which is right-hand: odd pages are
    right-hand, even pages left-hand (FR-043).
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


def structural_toc_entry_count(
    level_count: int, puzzle_count: int, *, play_row: bool = False
) -> int:
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
    # The Play online row (owner, 2026-11-09), between the levels and the
    # solutions, when the book prints that page.
    return 2 + 2 * level_count + (1 if play_row else 0)


def structural_toc_entries(
    section: Sequence["SectionPage"],
    payloads: Sequence[ExportPayload],
    solutions_page: int,
    *,
    level_rows: bool = True,
    play_page: Optional[int] = None,
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

    * :data:`GUIDE_TITLE` against interior page ``1 + TITLE_PAGE_COUNT``.
      The blank title page opens the interior (INV-013 as amended: no cover
      page, page 1 is the title page) and the guide follows it for
      :data:`GUIDE_PAGE_COUNT` pages, so its *first* page — a verso — is the
      one a reader is sent to.
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
    if not level_rows:
        # CARD-305: this book prints no divider pages, so there is no page for
        # a level row to point at and the TOC carries the guide row and the
        # solutions row alone. The tripwire does not go away, it **inverts**:
        # a section that still holds a divider while the caller says the book
        # has none is the same kind of plan/draw disagreement the matching
        # check below catches, and it must fail just as loudly rather than
        # print a TOC that silently omits pages the book really has.
        if dividers:
            raise RuntimeError(
                "the page plan holds level dividers "
                f"{[divider.level.value for divider in dividers]} for a book "
                "whose interior prints none"
            )
        return [
            TocEntry(GUIDE_TITLE, 1 + TITLE_PAGE_COUNT),
            *_play_rows(play_page),
            TocEntry(TOC_SOLUTIONS_LABEL, solutions_page, starts_group=True),
        ]
    if [divider.level for divider in dividers] != [level for level, _, _ in runs]:
        raise RuntimeError(
            "the page plan's level dividers "
            f"{[divider.level.value for divider in dividers]} do not match the "
            f"book's own level runs {[level.value for level, _, _ in runs]}"
        )
    # The guide's own first page, counted from the front matter before it
    # (INV-013 as amended: the interior holds no cover page and opens on the
    # blank title page, `TITLE_PAGE_COUNT`). CARD-206 is the day the comment
    # that used to stand here anticipated — something is now printed *before*
    # the guide — so the term is derived from the constant rather than left a
    # literal; `interior_stream`'s own `TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT +
    # 1 + index` for the TOC pages and `section_plan`'s `first_page` are its
    # siblings and count from the same two constants.
    entries: List[TocEntry] = [TocEntry(GUIDE_TITLE, 1 + TITLE_PAGE_COUNT)]
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
    entries.extend(_play_rows(play_page))
    entries.append(TocEntry(TOC_SOLUTIONS_LABEL, solutions_page, starts_group=True))
    return entries


#: The contents row naming the Play online page (owner, 2026-11-09).
TOC_PLAY_LABEL = "Play online"


def _play_rows(play_page: Optional[int]) -> List["TocEntry"]:
    """The Play online row, set off as its own group, or nothing."""
    return [] if play_page is None else [TocEntry(TOC_PLAY_LABEL, play_page, starts_group=True)]


def recto_blank_pages(pages_before: int) -> int:
    """How many blank pages put the next page on the right (FR-043, CARD-390).

    ``pages_before`` pages have been laid down. If the last of them is
    right-hand (:func:`page_is_right_hand`) the next is a verso and one blank
    page goes first; if it is a verso the next is already a recto. The one
    rule the Play online page's placement is made from, in the plan and in
    :func:`interior_page_count` alike; a section opener that must start
    right-hand (CARD-231, parked) would ask the same question.

    ``pages_before`` is at least 1 in every caller (the blank title page is
    interior page 1); :func:`page_is_right_hand` refuses a position under 1.
    """
    return 1 if page_is_right_hand(pages_before) else 0


def interior_page_count(
    puzzle_count: int,
    puzzle_pages: Optional[int] = None,
    answer_pages: Optional[int] = None,
    level_dividers: Optional[int] = None,
    toc_pages: Optional[int] = None,
    solutions_divider: bool = True,
    play_online: bool = False,
) -> int:
    """The interior's page count for ``puzzle_count`` rendered puzzles.

    The page plan :meth:`BookPDFGenerator.interior` builds —
    :data:`TITLE_PAGE_COUNT` blank title page (CARD-206: interior page 1,
    reserved and unprinted), :data:`GUIDE_PAGE_COUNT`
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

    ``solutions_divider`` (CARD-305) is whether the book prints the SOLUTIONS
    page that opens its answer key — ``False`` for a book whose divider-pages
    setting is off, which prints neither that page nor any level divider.

    **It does not reach the ``toc_pages=None`` default**, and the two must not
    be read as consistent: left out, ``toc_pages`` is derived from
    ``structural_toc_entry_count(min(len(TIERS), puzzle_count), puzzle_count)``,
    which still budgets TOC rows for level dividers under
    ``solutions_divider=False``. That is deliberate — the default is an upper
    bound over *every* book of that many puzzles and never one caller's book,
    the same posture ``level_dividers`` takes — but it means
    ``interior_page_count(n, solutions_divider=False)`` called without
    ``toc_pages`` is an over-estimate for a book that prints no dividers
    rather than its real length. Every production caller passes ``toc_pages``
    explicitly (:func:`~nonogram.admin.book_kdp.unpaired_interior_page_count`
    and :meth:`BookPDFGenerator.interior_stream`), so nothing ships on the
    default; said here because a future caller could (CARD-305 cycle 1,
    F-006 — latent, and left latent on purpose: making the default follow
    this parameter would turn it into one book's figure).

    ``play_online`` (CARD-390) is whether the book prints the Play online page
    that follows the last puzzle page. It adds that page and, when the last
    puzzle page is itself right-hand, the one blank page in front of it
    (:func:`recto_blank_pages`) — so the term depends on the pages before it
    and is counted here, from the same figures every caller already passes,
    rather than in a caller. Like the SOLUTIONS page it needs a puzzle to point
    at, and is not counted for a book with none.
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
            structural_toc_entry_count(
                min(len(TIERS), puzzle_count), puzzle_count, play_row=True
            ),
            default_toc_frame(),
            DPI,
        )
        if toc_pages is None
        else toc_pages
    )
    if toc < 0:
        raise ValueError(f"TOC page count cannot be negative, got {toc}")
    before_play = TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc + dividers + pages
    return (
        before_play
        # CARD-390: the Play online page and its blank, after the last puzzle
        # page and before the SOLUTIONS divider.
        + (recto_blank_pages(before_play) + 1 if play_online and puzzle_count else 0)
        # CARD-305: the `+ 1` here has always been the SOLUTIONS divider, and
        # it is now the one term `level_dividers` could not express — that
        # parameter counts the *level* dividers, which a book without
        # dividers reports as 0 of its own accord, while this page is not a
        # level's and had nowhere to be said. A book that prints no dividers
        # passes `solutions_divider=False` and loses both.
        + (answers + (1 if solutions_divider else 0) if puzzle_count else 0)
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


#: How much of a title the refusal's message quotes, and how many distinct
#: characters it lists, so a pasted paragraph does not become a wall of text on
#: the owner's screen. The exception's own ``title`` and ``characters`` carry
#: the whole of both.
_REFUSAL_TITLE_CHARS = 60
_REFUSAL_LISTED_CHARACTERS = 6


def _refuse_unsettable_titles(
    answer_titles: Sequence[Tuple[Any, Optional[str]]],
) -> None:
    """Refuse, before any page, an answer caption the interior cannot set.

    CARD-383 (the owner's ruling D4: refuse loudly, transliterate nothing, no
    wider face). A page written as operators shows text through
    :func:`~nonogram.admin.book_vector.encode_text`, which raises for anything
    outside the interior's encoding. Left to the walk, that raise would be
    re-wrapped in a ``RuntimeError`` naming no character, so the one check is
    made here, **eagerly and outside the walk's per-page ``try``**, and says
    what the owner has to do.

    The answer page is always operators (the raster answer writers were
    deleted on 2026-11-09), so the check always runs.

    ``answer_titles`` is :attr:`InteriorStream.answer_titles`: ``(puzzle id,
    title)`` in print order, the title being the very value of the same
    :func:`~nonogram.admin.book_answer_key.answer_title` call the walk makes
    (the per-book custom title when set, otherwise the name), and
    :func:`~nonogram.admin.book_answer_key.answer_caption` composes the line,
    so the number and the separator are judged with it. ``encode_text`` is the
    only authority; there is no second character table here. The first
    puzzle in print order that fails is named.

    **Called by the doors that draw** (:meth:`export_book`,
    :meth:`export_interior`, :meth:`interior`, which :meth:`interior_pages`
    reads), after :meth:`interior_stream` has decided the plan and before the
    first page is asked for -- and **not by :meth:`interior_stream` itself**,
    which is also the plan the Finalise counts read (``app._interior_counts``)
    and must keep counting a book the export will refuse (CARD-383, AC-8).

    Raises:
        UnsettablePuzzleTitle: the first caption ``encode_text`` rejects.
    """
    for number, (puzzle_id, title) in enumerate(answer_titles, start=1):
        try:
            encode_text(answer_caption(number, title))
        except UnrepresentableText:
            pass
        else:
            continue
        refused: List[str] = []
        for character in title or "":
            if character in refused:
                continue
            try:
                encode_text(character)
            except UnrepresentableText:
                refused.append(character)
        shown = (title or "")[:_REFUSAL_TITLE_CHARS]
        if shown != title:
            shown += "..."
        listed = ", ".join(
            f"{character!r} (U+{ord(character):04X})"
            for character in refused[:_REFUSAL_LISTED_CHARACTERS]
        )
        if len(refused) > _REFUSAL_LISTED_CHARACTERS:
            listed += f" and {len(refused) - _REFUSAL_LISTED_CHARACTERS} more"
        raise UnsettablePuzzleTitle(
            f"Puzzle {number} \u201c{shown}\u201d cannot be exported: its "
            f"title holds {listed}, which the book's interior cannot print. "
            "The interior sets Latin letters with their accents and the "
            "common punctuation, and nothing else. Rename the puzzle, or "
            "give it another title on the Arrangement step.",
            puzzle_id=puzzle_id,
            puzzle_number=number,
            title=title,
            characters=tuple(refused),
        )



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


#: Close WinAnsi stand-ins for characters an owner may type into a title
#: page line that the embedded face's encoding cannot carry (owner,
#: 2026-11-09). "—", "–", "’", "&" and "©" are all WinAnsi and need none;
#: these are for what is *not*, so a pasted glyph degrades to its plain
#: spelling instead of refusing the whole book (:class:`UnrepresentableText`).
_TITLE_PAGE_STAND_INS = {
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2015": "\u2014",
    "\u2212": "-", "\u2032": "'", "\u2033": '"', "\u00a0": " ",
    "\u2009": " ", "\u202f": " ", "\u2002": " ", "\u2003": " ",
    "\u2117": "(P)",
}


def _settable(value: str) -> str:
    """``value`` with every character the embedded face cannot set replaced.

    Each character is tried against :func:`encode_text`, the one judge of
    what the interior's face carries. One it refuses becomes its
    :data:`_TITLE_PAGE_STAND_INS` entry if that is itself settable, else its
    compatibility decomposition stripped of combining marks (``é`` stays —
    it is WinAnsi — but ``ő`` becomes ``o``), else ``?``. Never raises.
    """
    def ok(text: str) -> bool:
        try:
            encode_text(text)
        except UnrepresentableText:
            return False
        return True

    out = []
    for character in value:
        if ok(character):
            out.append(character)
            continue
        stand_in = _TITLE_PAGE_STAND_INS.get(character)
        if stand_in is not None and ok(stand_in):
            out.append(stand_in)
            continue
        plain = "".join(
            c for c in unicodedata.normalize("NFKD", character)
            if not unicodedata.combining(c)
        )
        out.append(plain if plain and ok(plain) else "?")
    return "".join(out)


class BookPDFGenerator:
    """Generates a book's interior PDF (guide, puzzles, answers) and cover file.

    Args:
        book: The book being exported — anything carrying the ``books`` print
            columns (a :class:`~nonogram.admin.book_manager.Book` or a row).
            ``None`` is a book with no stored print specification, which is
            CON-018's Book 1 profile, exactly as an empty column is
            (:func:`~nonogram.admin.book_page_spec.book_page_spec`).
        pages: The interior page writers that live downstream of this module
            (CARD-309) — :class:`InteriorPageWriters`. ``None`` is
            :data:`NO_DOWNSTREAM_WRITERS`, a generator that can draw every
            kind it owns itself and **refuses** a kind
            :func:`page_medium` calls vector that it does not: see
            :class:`InteriorPageWriters` for why the direction is a parameter
            and :mod:`nonogram.admin.book_interior_vector` for the one module
            that builds a full set.
        dividers: The owner's uploaded divider pictures, ``{slot: PNG
            bytes}`` over :data:`~nonogram.admin.book_dividers.DIVIDER_SLOTS`
            (CARD-311). A divider page whose slot is present prints the
            picture, fitted to the page; the others are drawn. They change what
            a divider page shows and never the page plan.

    Raises:
        ValueError: the book's stored print specification cannot be laid out
            (a trim outside KDP's bounds, a margin below the minimum, a
            non-numeric column) — the message names the column at fault.
    """

    def __init__(
        self,
        book: Any = None,
        pages: Optional[InteriorPageWriters] = None,
        dividers: Optional[Mapping[str, bytes]] = None,
    ):
        self.book = book
        # CARD-311: the owner's uploaded divider pictures, ``{slot: PNG}``,
        # handed in by the caller that read them from the store -- this class
        # holds no database. A slot with no picture prints the drawn page, and
        # a slot for a page the book does not have prints nothing: this is read
        # only when the walk reaches a divider the page plan already contains,
        # so it can change what a page shows and never how many there are.
        self.divider_images: Dict[str, bytes] = {
            require_slot(slot): bytes(png) for slot, png in (dividers or {}).items()
        }
        # CARD-309: read once, here, for the same reason `ink_mode` and
        # `divider_pages` are — the walk below asks it per page and two page
        # walks of one export must not be able to disagree about which writer
        # drew a kind. It is a constructor argument rather than a keyword on
        # each of `export_book`/`export_interior`/`interior_stream` because
        # those three are one walk behind three doors, and forwarding a
        # parameter through all of them would be three signatures carrying a
        # fact that belongs to the generator.
        self.pages = NO_DOWNSTREAM_WRITERS if pages is None else pages
        self.dpi = DPI  # 300, the resolution COMP-007 measures every page at
        # CARD-147: how this book's interior is printed, read once from the
        # stored column. It decides the interior's colour space and nothing
        # else; the cover file is RGB whatever it says (AC-5, G-4).
        self.ink_mode = book_ink_mode(self.book)
        # CARD-305: whether this book's interior prints its four divider
        # pages — the level dividers (AC-254) and SOLUTIONS (AC-292) — read
        # once from the stored column, beside the ink mode and for the same
        # reason: one read, so no two page walks can disagree about it.
        # Unlike the ink mode it moves the page COUNT, which is why every
        # `interior_page_count` call in this module is passed it rather than
        # left to a default.
        self.divider_pages = book_divider_pages(self.book)
        # CARD-390: the book's stored player domain, read once beside the
        # other stored columns for the same reason. Whether the interior
        # prints the Play online page is this and nothing else (ADR-0041/R8:
        # no domain, no page); it moves the page COUNT, so every
        # `interior_page_count` call here is told.
        self.player_domain = printable_player_domain(self.book)
        # The trim, as the layout reports it for this book's sheet. Parity
        # never changes a page's size, so page 1's frame gives it for all.
        #
        # **This line is also what makes an unreadable stored print
        # specification the book's own bare ValueError** rather than a
        # per-puzzle abort naming every member of it: it lays the sheet out
        # before the generator has a payload, so no caller of `section_plan`
        # or `puzzle_page_plan` can reach their cell-map handlers with a sheet
        # that will not lay out (CARD-225 review cycle 2, F-001 — the two
        # statements those entries carried for that purpose were dead, and
        # this one had been doing the work since before the card). Pinned by
        # `tests/test_book_pdf.py`'s
        # `test_an_unreadable_print_specification_is_the_books_own_failure`,
        # which reds when this read is made to fall back to a default sheet
        # instead of raising.
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

        The one door onto the book's geometry (CARD-115). Page 1 is the blank
        title page (:data:`TITLE_PAGE_COUNT`) and is right-hand; each page's
        parity is its position (FR-043).
        """
        return book_page_spec(self.book, page_number)

    def cell_sizes(self, payloads: Sequence[ExportPayload]) -> Dict[GridSize, float]:
        """The cell each grid size in this book prints at, in mm (NFR-008, CARD-225).

        :func:`~nonogram.admin.book_page_spec.book_cell_sizes` over
        ``payloads``' clue sets on this book's own sheet — the one door, as
        every other book figure comes through (EC-021, ADR-0036/R2). The
        panel selects among ``compute_layout``'s own cells and measures
        nothing itself.

        **It takes the whole book, never a slice of it.** A grid size's cell
        is fitted to the deepest-clued member *in the book*, so a map built
        over one level's puzzles would print that level's 20x20s larger than
        another level's. Both production callers hand it the full payload
        list: :meth:`section_plan` (the export and the Arrangement screen)
        and :func:`puzzle_page_plan` (CARD-251's editor).

        Args:
            payloads: Every drawable member of the book, in any order.

        Returns:
            ``{(columns, rows): cell in mm}``, covering exactly the grid
            sizes ``payloads`` holds.

        Raises:
            ValueError: the book's stored print specification cannot be laid
                out, or a payload's clue sets cannot be (fail closed — see
                ``book_cell_sizes``).
        """
        return book_cell_sizes(
            self.page_spec(1),
            [(payload.row_clues, payload.column_clues) for payload in payloads],
        )

    def _puzzle_page_spec(
        self,
        page_number: int,
        cell_mm: Optional[float],
    ) -> PageSpec:
        """The sheet one puzzle page is drawn on, capped at its grid size's cell.

        :meth:`page_spec` for ``page_number``, with its flat cap lowered to
        ``cell_mm`` (:func:`~nonogram.admin.book_page_spec.book_cell_spec`) —
        which is how the book-wide figure reaches the page without a second
        placement. ``None`` is the sheet unchanged, which is the per-puzzle
        fit this card replaces: it is what a caller that was handed no
        ``cell_sizes`` map gets (F-14), and what every **non-puzzle** page
        (guide, TOC, divider, answer key) is drawn on, since none of them
        prints a puzzle at a book cell (F-15, F-16).
        """
        spec = self.page_spec(page_number)
        return spec if cell_mm is None else book_cell_spec(spec, cell_mm)

    @staticmethod
    def _grid_size(payload: ExportPayload) -> GridSize:
        """``payload``'s grid size, read off its clue sets exactly as the map keys it."""
        return (len(payload.column_clues), len(payload.row_clues))

    def _unmeasurable_members(
        self, payloads: List[ExportPayload], ids: Optional[List[Any]]
    ) -> str:
        """Which members :meth:`cell_sizes` could not measure, named (CARD-225).

        The **failure path only**. ``cell_sizes`` fails closed for the whole
        book (:func:`~nonogram.admin.book_page_spec.book_cell_sizes`), which
        says *that* a member will not lay out and not *which*; this walks the
        payloads once more and names every one that refuses, through
        :func:`_named_puzzles`, so the message is the one the owner can act on.

        A second pass is affordable precisely because it runs only when the
        export is already aborting, and it cannot disagree with the first:
        ``book_cell_mm`` is pure, so a member that refused there refuses here.

        **The book's own sheet is not re-judged here.** This helper carried a
        ``spec_is_readable`` pre-check for a book whose stored print
        specification is itself unreadable; that branch was unreachable from
        both production entries, because
        :meth:`BookPDFGenerator.__init__` lays the sheet out when the
        generator is built and raises there, so no production caller gets as
        far as a payload holding an unreadable sheet (review cycle 2, F-001).
        Scoped to production callers deliberately: a specification mutated to
        an unreadable value after construction can reach a payload, and review
        cycle 3's probe found no caller that does it. It is deleted rather
        than documented as live.

        Should none of the payloads refuse alone, every member is still
        named — a fail-safe for a ``cell_sizes`` that refuses a set no single
        member of it refuses, which ``book_cell_mm``'s per-member purity says
        cannot happen. **No test pins that branch and none is claimed for
        it.**
        """
        refused: List[int] = []
        for index, payload in enumerate(payloads):
            try:
                self.cell_sizes([payload])
            except ValueError:
                refused.append(index + 1)
        numbers = tuple(refused) if refused else tuple(range(1, len(payloads) + 1))
        return _named_puzzles(ids, numbers)

    def _pair_cell_mm(
        self,
        first: ExportPayload,
        second: ExportPayload,
        cell_sizes: Optional[Dict[GridSize, float]],
    ) -> Optional[float]:
        """The cap a two-up page takes: the **smaller** of its two book cells.

        The owner's rule for a shared page, recorded on CARD-225 ("two
        puzzles sharing a page use the smaller of their two sizes — this is
        what makes their grids line up"). Two puzzles of the *same* grid size
        share one entry, so the rule degenerates to that entry for them.

        ``None`` (no map, or a member whose grid size the map does not cover)
        leaves the sheet uncapped, which is the pair-only fit that preceded
        this card (F-14).
        """
        if cell_sizes is None:
            return None
        cells = [
            cell_sizes.get(self._grid_size(payload)) for payload in (first, second)
        ]
        known = [cell for cell in cells if cell is not None]
        return min(known) if len(known) == len(cells) else None

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

    def vector_title_contents(self, puzzle_count: int, page_number: int = 1) -> ContentStream:
        """Interior page 1 with the book's title and copyright (owner, 2026-11-09).

        Replaces the blank reserved page the owner chose on 2026-10-13: a
        blank first page is what KDP's "Look Inside" would open on. Centred
        on the usable width, top to bottom:

        * the **series name** (migration 020), uppercase in grey at 10.5 pt,
          above the title — only if the book has one;
        * the **title**, 32 pt emboldened, wrapped at 80 % of the width, its
          first baseline a third of the way down;
        * the **subtitle** in grey at 14 pt — or, for a book with none, the
          "N picture puzzles" line in its place;
        * "by {authors}" at 13 pt, if the book names its authors;
        * at the foot of the usable area, the copyright notice — naming the
          authors when there are any — and the reproduction line, grey 10 pt.

        No folio, as on any title page. Every string is passed through
        :func:`_settable` first, so a character the embedded face's
        WinAnsi encoding cannot carry is set as its nearest equivalent
        instead of refusing the whole book.
        """
        frame = page_frame(self.page_spec(page_number))
        stream = ContentStream(width_px=frame.width, height_px=frame.height, dpi=self.dpi)
        face = interior_face_metrics()
        pt = self.dpi / 72.0
        left, right = frame.left, frame.right
        middle = (left + right) / 2
        secondary = 0.37

        def centred(value: str, baseline: float, size_pt: float, grey: float, bold: bool = False) -> None:
            width = face.advance(value) * size_pt * pt
            stream.text(
                value, middle - width / 2, baseline, size_pt, grey=grey,
                embolden_pt=size_pt * 0.04 if bold else 0.0,
            )

        def wrapped(value: str, size_pt: float, share: float) -> List[str]:
            """``value``'s words, filled into lines no wider than ``share`` of the width."""
            lines: List[str] = []
            for word in value.split():
                candidate = f"{lines[-1]} {word}" if lines else word
                if lines and face.advance(candidate) * size_pt * pt <= (right - left) * share:
                    lines[-1] = candidate
                else:
                    lines.append(word)
            return lines

        def own(name: str) -> Optional[str]:
            value = getattr(self.book, name, None)
            value = _settable(str(value).strip()) if value is not None else ""
            return value or None

        metadata = getattr(self.book, "metadata", None)
        title = _settable(str(getattr(metadata, "title", "") or ""))
        series_name, subtitle, authors = own("series_name"), own("subtitle"), own("authors")

        title_pt, series_pt, subtitle_pt, authors_pt = 32.0, 10.5, 14.0, 13.0
        title_top = frame.height * 0.34

        if series_name:
            series_lines = wrapped(series_name.upper(), series_pt, 0.8)
            # The last series line sits a clear gap above the title's first
            # baseline; any line before it stacks upwards from there.
            last = title_top - (title_pt + 12.0) * pt
            for index, line in enumerate(series_lines):
                offset = len(series_lines) - 1 - index
                centred(line, last - offset * series_pt * 1.4 * pt, series_pt, secondary)

        y = title_top
        for line in wrapped(title, title_pt, 0.8):
            centred(line, y, title_pt, 0.0, bold=True)
            y += title_pt * 1.2 * pt

        y += 14 * pt  # the first line under the title: where the count always sat
        if subtitle:
            for line in wrapped(subtitle, subtitle_pt, 0.8):
                centred(line, y, subtitle_pt, secondary)
                y += subtitle_pt * 1.35 * pt
        elif puzzle_count:
            noun = "picture puzzle" if puzzle_count == 1 else "picture puzzles"
            centred(f"{puzzle_count} {noun}", y, subtitle_pt, secondary)
            y += subtitle_pt * 1.35 * pt

        if authors:
            y += 18 * pt
            for line in wrapped(f"by {authors}", authors_pt, 0.8):
                centred(line, y, authors_pt, 0.0)
                y += authors_pt * 1.35 * pt

        year = getattr(self.book, "created_at", None)
        holder = authors.rstrip(".") if authors else None
        if year is not None and holder:
            notice = f"Copyright © {year.year} {holder}. All rights reserved."
        elif year is not None:
            notice = f"Copyright © {year.year}. All rights reserved."
        elif holder:
            notice = f"Copyright © {holder}. All rights reserved."
        else:
            notice = "All rights reserved."
        notice = _settable(notice)
        base = frame.bottom - 16 * pt
        notice_lines = wrapped(notice, 10.0, 1.0)
        for index, line in enumerate(notice_lines):
            offset = len(notice_lines) - 1 - index
            centred(line, base - offset * 14 * pt, 10.0, secondary)
        centred(
            "No part of this book may be reproduced without written permission.",
            base + 14 * pt, 10.0, secondary,
        )
        return stream

    def vector_title_page(self, page_number: int = 1) -> ContentStream:
        """:meth:`create_title_page`'s vector twin: the trim, and no operator.

        CARD-298, ADR-0042/R1. The one page kind whose two media are the same
        page by construction rather than by measurement: the raster twin is
        ``Image.new("RGB", ..., "white")`` and prints no ink at all, so the
        operator stream that reproduces it exactly is the **empty** one. There
        is nothing here to get wrong, which is why this is the one interior
        kind this card can convert without a page writer behind it.

        Its sheet is taken from its own position for the reason the raster
        twin's is (:meth:`page_spec`, FR-043) — the page has no ink for a
        parity to mirror, but it is the book's trim and it decides whether the
        page after it is a verso.
        """
        frame = page_frame(self.page_spec(page_number))
        # Bound to ``stream`` rather than returned straight out of the call:
        # ``tests/test_book_difficulty_dots.py``'s
        # ``test_every_content_stream_in_the_package_is_spelled_stream`` holds
        # every ``ContentStream`` in the package to that one name, and allows
        # exactly one unbound ``return ContentStream(...)`` —
        # ``book_vector_draw.page_stream``, the factory. A second would be
        # "a failure to look at rather than a pattern to absorb" in that
        # guard's own words, and it is right: this is a page's stream, not a
        # second factory for one.
        stream = ContentStream(
            width_px=frame.width, height_px=frame.height, dpi=self.dpi
        )
        return stream

    def divider_page(
        self,
        slot: str,
        page_number: int,
        text: str,
        *,
        puzzle_count: Optional[int] = None,
        puzzle_range: Optional[Tuple[int, int]] = None,
    ) -> Image.Image:
        """The divider page for ``slot``: the owner's picture if one is stored, else the drawn word.

        CARD-311. The picture is fitted to this page's own frame
        (:func:`~nonogram.admin.book_dividers.fit_to_page`), derived from
        :meth:`page_spec` and not from a constant, and **no folio is drawn over
        it**: it is the owner's artwork, and the blank title page already
        establishes that an interior page may carry none. Parity and the page
        number are the plan's and are untouched either way (FR-043, G-1).

        Raises:
            DividerRefused: the stored picture no longer suits the page (the
                trim was changed after the upload). Raised, never stretched.
        """
        stored = self.divider_images.get(require_slot(slot))
        if stored is None and slot == SOLUTIONS_SLOT and puzzle_count:
            return self.create_solutions_opener(page_number, puzzle_count)
        if (
            stored is None
            and slot != SOLUTIONS_SLOT
            and puzzle_range is not None
            and LEVEL_DIVIDER_OPENER
        ):
            return self.create_level_divider(page_number, Tier(slot), puzzle_range)
        if stored is None:
            return self.create_divider_page(page_number, text)
        frame = page_frame(self.page_spec(page_number))
        return fit_to_page(stored, slot, frame.width, frame.height, self.dpi)

    def create_solutions_opener(self, page_number: int, puzzle_count: int) -> Image.Image:
        """The approved mockup's Solutions opener, for a book with no uploaded picture.

        Set on the page's usable left edge, a little above the middle: a short
        rule, the eyebrow "PUZZLES 1–N" in grey, the title "Solutions" large
        and heavy, and one grey line saying how the key runs. Every size is at
        or above CON-020's 10 pt floor.
        """
        frame = page_frame(self.page_spec(page_number))
        page = Image.new("RGB", (frame.width, frame.height), "white")
        draw = ImageDraw.Draw(page)
        grey = (96, 96, 96)
        left = frame.left
        top = round(frame.height * 0.28)
        rule_w = type_px(60, self.dpi)
        draw.rectangle(
            (left, top, left + rule_w, top + max(1, type_px(2.4, self.dpi))), fill="black"
        )
        eyebrow_font = _guide_face(type_px(10, self.dpi))
        eyebrow = "PUZZLES 1" if puzzle_count == 1 else f"PUZZLES 1–{puzzle_count}"
        y = top + type_px(14, self.dpi)
        draw.text((left, y), eyebrow, fill=grey, font=eyebrow_font)
        title_font = _guide_face(type_px(48, self.dpi))
        y += type_px(18, self.dpi)
        draw.text(
            (left, y), "Solutions", fill="black", font=title_font,
            stroke_width=max(1, type_px(1.2, self.dpi)), stroke_fill="black",
        )
        bbox = draw.textbbox((left, y), "Solutions", font=title_font)
        blurb_font = _guide_face(type_px(11, self.dpi))
        y = bbox[3] + type_px(30, self.dpi)
        draw.text(
            (left, y), "Check your finished picture. Solutions run in puzzle order.",
            fill=grey, font=blurb_font,
        )
        blurb_box = draw.textbbox(
            (left, y), "Check your finished picture. Solutions run in puzzle order.",
            font=blurb_font,
        )
        _draw_folio(
            draw,
            frame.left,
            frame.top,
            frame.right,
            frame.bottom,
            page_number,
            self.dpi,
            content_bottom=blurb_box[3],
        )
        return page

    def create_level_divider(
        self, page_number: int, level: Tier, puzzle_range: Tuple[int, int]
    ) -> Image.Image:
        """A level's divider in the Solutions opener's style (owner, 2026-11-09).

        The same placement as :meth:`create_solutions_opener`: a short rule,
        the eyebrow "PUZZLES a–b" in grey, the level's name large and heavy,
        and under it the level's difficulty dots -- filled for its rank among
        the tiers, open for the rest, as the puzzle headers draw them.
        """
        frame = page_frame(self.page_spec(page_number))
        page = Image.new("RGB", (frame.width, frame.height), "white")
        draw = ImageDraw.Draw(page)
        grey = (96, 96, 96)
        left = frame.left
        top = round(frame.height * 0.28)
        draw.rectangle(
            (left, top, left + type_px(60, self.dpi), top + max(1, type_px(2.4, self.dpi))),
            fill="black",
        )
        first, last = puzzle_range
        eyebrow = f"PUZZLE {first}" if first == last else f"PUZZLES {first}–{last}"
        y = top + type_px(14, self.dpi)
        draw.text((left, y), eyebrow, fill=grey, font=_guide_face(type_px(10, self.dpi)))
        title_font = _guide_face(type_px(48, self.dpi))
        y += type_px(18, self.dpi)
        draw.text(
            (left, y), level.label, fill="black", font=title_font,
            stroke_width=max(1, type_px(1.2, self.dpi)), stroke_fill="black",
        )
        bbox = draw.textbbox((left, y), level.label, font=title_font)
        # The level's dots through the one round-mark site (CARD-228), in a
        # box the size of three of the guide's own.
        height = type_px(12, self.dpi)
        dot_top = bbox[3] + type_px(26, self.dpi)
        drawn = _draw_difficulty_dots(
            draw, level, left, dot_top, left + 4 * height, dot_top + height
        )
        dots_bottom = dot_top + height if drawn is not None else bbox[3]
        _draw_folio(
            draw,
            frame.left,
            frame.top,
            frame.right,
            frame.bottom,
            page_number,
            self.dpi,
            content_bottom=dots_bottom,
        )
        return page

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

    def export_book(
        self,
        puzzles: List[dict],
        book_title: str,
        cover_image: Optional[Image.Image] = None,
    ) -> BookExport:
        """Export a book as its two files: the interior PDF and the cover file.

        The one entry point every export route goes through (FR-043, INV-013).
        The interior holds no cover page — its page 1 is the blank title
        page (``TITLE_PAGE_COUNT``, CARD-206) and its pages 2-3 are the guide
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
        _refuse_unsettable_titles(stream.answer_titles)
        interior = self._write_pdf(
            stream.pages,
            stream.page_count,
            mode=self.interior_bitmap_mode,
            kinds=stream.page_kinds,
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
        _refuse_unsettable_titles(stream.answer_titles)
        return self._write_pdf(
            stream.pages,
            stream.page_count,
            mode=self.interior_bitmap_mode,
            kinds=stream.page_kinds,
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
            self._cover_page(book_title, cover_image),
            1,
            mode="RGB",
            kinds=(PageKind.COVER,),
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

    def vector_puzzle_page(
        self,
        payload: ExportPayload,
        puzzle_number: int,
        puzzle_page: int,
        cell_sizes: Optional[Dict[GridSize, float]] = None,
        play_page: Optional[int] = None,
    ) -> ContentStream:
        """:meth:`_blank_page`'s vector twin: the same page as operators (CARD-295).

        ADR-0042/R1. The sheet, the cell and the band identity are taken
        exactly as :meth:`_blank_page` takes them — the same
        :meth:`_puzzle_page_spec` call on the same ``cell_sizes`` map, the same
        :func:`~nonogram.export.layout.compute_layout`, the same
        :func:`band_identity` — so the two media differ in the medium and in
        nothing else. ADR-0037/R1 holds for the same reason it holds there:
        the band is composed by :func:`band_identity` and the picture's name
        reaches no call here at all.

        ``header_band(layout)`` is called without a spec, as
        :meth:`_two_up_page` calls it: on a **placed** page the band is read
        off ``layout.page`` and the spec argument is not consulted
        (:func:`~nonogram.export.layout.header_band`), so passing it would
        suggest a dependency that does not exist.

        **And since CARD-306 it carries the sheet's furniture too** — the
        interior frame's two rules, the footer's grid-size label, the folio
        and (CARD-391) the pointer to the Play online page, which
        :meth:`_blank_page` added after ``render_pages`` returned (the QR
        group, until CARD-391) and which this page went without for as long
        as nothing could call it. It is **not** drawn by
        :mod:`nonogram.admin.book_puzzle_vector`, which still draws only what
        makes a page a puzzle page: every interior page kind carries the same
        furniture off the same
        :func:`~nonogram.export.layout.interior_frame`, so it is drawn once,
        in :mod:`nonogram.admin.book_sheet_vector`, and composed here —
        which is where the words and the type sizes live.

        The figures handed to it are :meth:`_blank_page`'s own, read from the
        same objects on the same ``Layout``: the frame from
        :func:`~nonogram.export.layout.interior_frame`, the label from
        :func:`grid_size_label`, the footer's verdict from
        ``placement.drawing_bottom``. So the two media differ in the medium
        and in nothing else here — except the pointer, which only this twin
        draws (:meth:`_blank_page`).

        ``play_page`` is the interior page number of the Play online page,
        read from the plan (:attr:`SectionPlan.play_page`) by the caller; a
        book that prints no Play page passes ``None`` and the footer carries
        the grid size and the folio only (G-2).
        """
        page_spec = self._puzzle_page_spec(
            puzzle_page,
            None if cell_sizes is None else cell_sizes.get(self._grid_size(payload)),
        )
        layout = compute_layout(payload.row_clues, payload.column_clues, page_spec)
        stream = puzzle_page_stream(
            layout,
            header_band(layout),
            band_identity(puzzle_number, payload.difficulty),
        )
        placement = layout.page
        draw_sheet_furniture(
            stream,
            self._sheet_furniture(
                page_spec,
                puzzle_page,
                size_label=grid_size_label(layout.columns, layout.rows),
                content_bottom=None if placement is None else placement.drawing_bottom,
                pointer=self._pointer(play_page, (puzzle_number,)),
            ),
            interior_face_metrics(),
        )
        return stream

    def _sheet_furniture(
        self,
        page_spec: PageSpec,
        page_number: int,
        *,
        size_label: Optional[str] = None,
        content_bottom: Optional[int] = None,
        content_right: Optional[int] = None,
        content_left: Optional[int] = None,
        pointer: Optional[str] = None,
    ) -> SheetFurniture:
        """One vector interior page's furniture, composed from this module's own figures.

        The **only** place a :class:`~nonogram.admin.book_sheet_vector.SheetFurniture`
        is built, so the three type sizes, the folio's spelling and the
        folio's reserved width have one reader each (CARD-306, AC-3):
        :data:`FOLIO_PT`, :data:`SIZE_LABEL_PT` and
        :data:`~nonogram.export.layout.INTERIOR_FOOTER_LINE_PT` through
        :func:`type_px` — the same conversion the raster footer's fonts are
        asked for — :func:`_folio_reserve_px`, and
        :func:`page_is_right_hand` for the fallback corner's parity (FR-043).

        Every *position* comes from :func:`~nonogram.export.layout.interior_frame`
        and nothing is measured here or there (ADR-0042/R3).
        """
        return SheetFurniture(
            frame=interior_frame(page_spec),
            folio=str(page_number),
            folio_size_px=type_px(FOLIO_PT, self.dpi),
            size_label=size_label,
            label_size_px=type_px(SIZE_LABEL_PT, self.dpi),
            pointer=pointer,
            pointer_size_px=type_px(INTERIOR_FOOTER_LINE_PT, self.dpi),
            folio_reserve_px=_folio_reserve_px(self.dpi),
            content_bottom=content_bottom,
            content_right=content_right,
            content_left=content_left,
            right_hand=page_is_right_hand(page_number),
        )

    def _pointer(
        self, play_page: Optional[int], numbers: Tuple[int, ...]
    ) -> Optional[str]:
        """The footer pointer for a page of ``numbers``, or ``None`` with no Play page.

        The one place the "pointer and Play page exist together or not at
        all" rule is applied (ADR-0041/R8, G-2): the page number is the
        plan's, and a book whose plan laid no Play page has none to name.
        """
        return None if play_page is None else footer_pointer_text(numbers, play_page)

    def vector_two_up_page(
        self,
        plan: "PuzzlePagePlan",
        payloads: Sequence[ExportPayload],
        play_page: Optional[int] = None,
    ) -> ContentStream:
        """:meth:`_two_up_page`'s vector twin: two puzzles, one sheet (CARD-295).

        A two-up slot *is* a puzzle page (TERM-030): the pair's geometry is
        two :class:`~nonogram.export.layout.Layout`\\ s on one trim, and each
        gets the same drawing and the same band a single page's does. ``strict``
        on the zip for the same reason :meth:`_two_up_page` passes it — a plan
        whose numbers and payloads disagree with its two slots is a bug in the
        walk, and a half-drawn page is the one way a book could ship a puzzle
        nobody printed.

        The page carries ONE footer line for its two puzzles, naming both
        (:func:`footer_pointer_text`), and no grid-size label: two slots carry
        two sizes. ``play_page`` is as :meth:`vector_puzzle_page` takes it.

        Raises:
            ValueError: ``plan`` is not a two-up page.
        """
        pair = plan.pair
        if pair is None:
            raise ValueError(f"page {plan.page_number} is not a two-up page")
        stream = two_up_page_stream(
            [
                (slot, header_band(slot), band_identity(number, payload.difficulty))
                for slot, number, payload in zip(
                    (pair.upper, pair.lower), plan.numbers, payloads, strict=True
                )
            ]
        )
        footer_area = pair.lower.page
        draw_sheet_furniture(
            stream,
            self._sheet_furniture(
                self.page_spec(plan.page_number),
                plan.page_number,
                size_label=None,
                content_bottom=footer_area.drawing_bottom,
                content_right=footer_area.drawing_right,
                content_left=footer_area.drawing_left,
                pointer=self._pointer(play_page, plan.numbers),
            ),
            interior_face_metrics(),
        )
        return stream

    def vector_puzzle_pages(
        self,
        payloads: List[ExportPayload],
        first_page: int = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT,
        cell_sizes: Optional[Dict[GridSize, float]] = None,
        play_page: Optional[int] = None,
    ) -> Iterator[ContentStream]:
        """Every puzzle page of ``payloads``, in print order, as content streams.

        The vector arm of the interior's puzzle section: :meth:`puzzle_pages`'
        own walk decides the pages — one puzzle or two, at which interior
        position — and each page is then drawn by
        :meth:`vector_puzzle_page` or :meth:`vector_two_up_page`. The plan is
        the real one, so a pairing verdict here is the export's verdict and not
        a model of it.

        One page at a time, by ``yield``: a content stream is three or four
        orders of magnitude smaller than the 25.2 MB bitmap CARD-145's
        ``interior_stream`` was built around, but holding a list of them would
        still be the shape that card removed.

        Args:
            payloads: **The whole book**, in print order
                (:func:`print_order`). Not a level's slice: ``cell_sizes``
                below is fitted over what it is handed, and a grid size's cell
                is the book's (NFR-008/CARD-225) — a map built over one level
                would print that level's 20x20s at another size.
            first_page: The interior position of the first puzzle page, as
                :meth:`puzzle_pages` takes it.
            cell_sizes: The book's cell map; measured over ``payloads`` when
                not given.
            play_page: The Play online page's interior page number, from the
                plan, for the footer's pointer; ``None`` for no pointer.
        """
        measured = self.cell_sizes(payloads) if cell_sizes is None else cell_sizes
        for entry in self.puzzle_pages(payloads, first_page, cell_sizes=measured):
            members = [payloads[number - 1] for number in entry.numbers]
            if entry.pair is None:
                yield self.vector_puzzle_page(
                    members[0], entry.numbers[0], entry.page_number, measured, play_page
                )
            else:
                yield self.vector_two_up_page(entry, members, play_page)

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

    def puzzle_pages(
        self,
        payloads: List[ExportPayload],
        first_page: int = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT,
        ids: Optional[List[Any]] = None,
        first_number: int = 1,
        cell_sizes: Optional[Dict[GridSize, float]] = None,
    ) -> List[PuzzlePagePlan]:
        """The pairing walk over the book order (FR-040, INV-010, EC-027).

        **Since CARD-225 a pair is offered a capped sheet** (``cell_sizes``,
        :meth:`cell_sizes`' whole-book map): the pair's spec is capped at the
        **smaller** of the two members' grid-size cells, which is the owner's
        own rule for a shared page and what makes the two grids line up. The
        cap is a ceiling, not a floor — the pair's own two-up fit still wins
        when it is the smaller (F-9) — and a pair whose smaller book cell is
        itself below :data:`~nonogram.export.layout.TWO_UP_MIN_CELL_MM` is
        **refused**, so its two puzzles print on separate pages (F-8). The
        map is the **book's**, never this walk's own slice: each level's walk
        is handed the same one by :meth:`puzzle_section`, so a 20x20 does not
        change size between levels (F-14).

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
            first_page: The interior position of the first puzzle page. Page
                1 is the blank title page (:data:`TITLE_PAGE_COUNT`,
                CARD-206) and the :data:`GUIDE_PAGE_COUNT` pages after it are
                the guide (CARD-201's 2-page
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
                page_spec = self._puzzle_page_spec(
                    page_number, self._pair_cell_mm(first, second, cell_sizes)
                )
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
        first_page: int = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT,
        ids: Optional[List[Any]] = None,
        cell_sizes: Optional[Dict[GridSize, float]] = None,
    ) -> List[SectionPage]:
        """The interior's puzzle section: a divider per level, then its pages.

        ``cell_sizes`` (CARD-225) is the **book's** per-grid-size cell map and
        is passed through to every level's :meth:`puzzle_pages` walk
        unchanged. Splitting the walk at a level boundary therefore still
        changes no verdict and now no cell either: the map a puzzle is sized
        by does not depend on which level's slice it was offered in, exactly
        as :data:`~nonogram.export.layout.TWO_UP_MIN_CELL_MM` does not.

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
                which is the first level's divider. Page 1 is the blank title
                page (:data:`TITLE_PAGE_COUNT`, CARD-206) and the
                :data:`GUIDE_PAGE_COUNT` pages after it are the guide
                (CARD-201), so the default is one past it.
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
            # CARD-305: a level opens with a divider only when this book
            # prints them. The page number is advanced inside the same branch
            # that appends the page, so a book without dividers simply has a
            # shorter section and every later page number follows from
            # `len(section)` exactly as before — there is no second place
            # that has to be told the dividers are gone.
            if level is not None and self.divider_pages:
                section.append(DividerPagePlan(page_number, level))
                page_number += 1
            pages = self.puzzle_pages(
                payloads[start:end],
                first_page=page_number,
                ids=None if ids is None else ids[start:end],
                first_number=start + 1,
                cell_sizes=cell_sizes,
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
            ValueError: the book's stored print specification cannot be laid
                out. A book-level failure, named for the book and for no
                member (review cycle 1, F-006).
            RuntimeError: a member could not be measured — the whole-book cell
                map's own failure (:meth:`cell_sizes`, since CARD-225) or a
                pair the walk offered (:meth:`puzzle_pages`). Either way the
                message names the puzzle (:meth:`_unmeasurable_members`).
        """
        ordered, ids, printed, payloads = numbered_rows(puzzles)
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
        #
        # CARD-305: a book that prints no dividers has no level rows in its
        # TOC either — the rows name the dividers' pages, so without them
        # there is nothing for a level row to point at. The level term is
        # therefore 0, leaving the guide row and the solutions row, and
        # `structural_toc_entries` reaches the same shape from the other side
        # (it reads `section`'s dividers, of which there are none). The TOC
        # tripwire in `interior_stream` is what holds the two readings equal.
        toc_entry_count = structural_toc_entry_count(
            (
                len([run for run in _level_runs(payloads) if run[0] is not None])
                if self.divider_pages
                else 0
            ),
            len(payloads),
            play_row=self.player_domain is not None,
        )
        # Read once here and fed to the TOC measurement below, which saves
        # `page_frame(self.page_spec(1))` a second call on the same sheet.
        #
        # **Its position makes no claim.** No production caller reaches this
        # method holding a book whose stored print specification cannot be
        # laid out: `__init__` laid the same sheet out when the generator was
        # built and raised there, which is what keeps a book-level fault out
        # of the cell map's handler below (review cycle 2, F-001). Said that
        # way on purpose — a specification mutated to an unreadable value
        # *after* construction does arrive here, and this read then refuses it
        # with the bare `ValueError` row F-3b asks for; review cycle 3 drove
        # exactly that probe, and found no caller that does it. Moving this
        # read under that try fails no test, so nothing here is stated as a
        # mechanism — the mechanism, and its mutant, are in `__init__`.
        spec = self.page_spec(1)
        toc_page_count = measured_toc_page_count(
            toc_entry_count, page_frame(spec), self.dpi
        )
        first_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc_page_count
        # CARD-225 (NFR-008 as amended): the cell each grid size prints at,
        # settled here, once, over the **whole** book — this is the only place
        # that knows every printable member at once, and the figure has to be
        # the book's rather than a level's or a page's (see `cell_sizes`). The
        # pairing walk below is handed it, and so is `interior_stream`, which
        # draws the single pages from the same map.
        try:
            cell_sizes = self.cell_sizes(payloads)
        except ValueError as unmeasurable:
            # One bad member stops the whole book — fail closed (F-3) — but the
            # owner searches a 120-puzzle book by the id in the message and
            # nothing else, so the abort names it, exactly as the pairing walk's
            # and the draw loop's do. The culprit is found on the **failure**
            # path only: the happy path asks `cell_sizes` once (EC-021's one
            # computation) and never re-measures a member to label it.
            raise RuntimeError(
                f"puzzle {self._unmeasurable_members(payloads, ids)} could not be "
                f"laid out: {unmeasurable}"
            ) from unmeasurable
        section = self.puzzle_section(
            payloads, first_page=first_page, ids=ids, cell_sizes=cell_sizes
        )
        # CARD-390: the Play online page follows the last page of the puzzle
        # section, on a right-hand page, and only when the book has a stored
        # player domain and a puzzle for the code to open. The blank before it
        # is the question `recto_blank_pages` answers about the pages laid
        # down so far.
        play_page = None
        play_blank_page = None
        if self.player_domain is not None and payloads:
            pages_before = TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc_page_count + len(section)
            play_page = pages_before + 1
            if recto_blank_pages(pages_before):
                play_blank_page = play_page
                play_page += 1
        return SectionPlan(
            puzzles=ordered,
            ids=ids,
            printed=printed,
            payloads=payloads,
            pages=section,
            toc_page_count=toc_page_count,
            cell_sizes=cell_sizes,
            play_page=play_page,
            play_blank_page=play_blank_page,
        )

    def interior_pages(
        self, puzzles: List[dict]
    ) -> List[Union[Image.Image, ContentStream]]:
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

        ``pages[n - 1]`` is interior page ``n``: page 1 is the blank title
        page (:data:`TITLE_PAGE_COUNT`, CARD-206), a right-hand page
        (:func:`page_is_right_hand`), the :data:`GUIDE_PAGE_COUNT` pages
        after it are the guide, the 2-page "how to solve" tutorial
        (CARD-201), followed by the
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
        _refuse_unsettable_titles(stream.answer_titles)
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
        # TOC (CARD-200: `toc_page_count` pages, after the blank title page and
        # the guide) and the SOLUTIONS divider, so both of those positions
        # count the section's length and not its puzzle pages alone. Computed
        # here (rather than after the degrade pass below) because it depends
        # only on `section` and `toc_page_count`, never on `answer_plan` — any
        # page_spec built from it measures the *same* usable size any other
        # interior page position would (`book_page_spec`'s own docstring:
        # parity moves the margins, never the usable size), which is exactly
        # what lets one representative spec answer the degrade pass's
        # feasibility check for every page position the plan could still land
        # on.
        #
        # CARD-206 review F-102: ONE assignment, read twice. This method used
        # to compute `first_answer_page` twice, nine statements apart, and the
        # first of the two was `3 + len(section)` — a front-matter page count
        # spelled as a bare literal and left behind by CARD-200's TOC and this
        # card's own title page, so that the two assignments disagreed (3
        # against 6 at today's constants). It was inert, because the degrade
        # pass reads only the spec's usable size and never its position, and
        # it was still the literal this card's plan named as the bug it was
        # most likely to ship.
        # CARD-305: the trailing term is the SOLUTIONS divider, which only a
        # book that prints dividers has. `len(section)` already carries the
        # level dividers or not, because `puzzle_section` is the one place
        # that decides whether to append them.
        #
        # **Three lines, and the conditional inline — both deliberate.** This
        # statement is `tests/test_book_export_interior_cover.py`'s
        # `DERIVED_POSITION` anchor: the door-axis walk replaces this exact
        # block, *line-count-preservingly*, with each of its planted shapes,
        # and asserts it occurs exactly once. Reflowing it over eight lines
        # reds 44 of that file's cells — the guard working, not a flake — and
        # hoisting the conditional into a local would put a term of a page
        # position behind a name, which is the laundering that walk exists to
        # catch. Hence the long middle line; that file's own anchor is
        # updated in the same commit, which is the edit this guard is built
        # to force.
        first_answer_page = (
            1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc_page_count + len(section) + decided.play_page_count + (1 if self.divider_pages else 0)
        )

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
            answer_plan, payloads, answer_section_spec(self.page_spec(first_answer_page))
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
        #
        # CARD-305: when the book prints no dividers there is no page one
        # before the first answer, so the row points at the first answer page
        # itself — still "the page a reader turns to for the solutions",
        # which is what the row means. The level rows disappear on their own,
        # because `structural_toc_entries` reads them off `section`'s
        # dividers and there are none.
        toc_entries = structural_toc_entries(
            section,
            decided.payloads,
            first_answer_page - (1 if self.divider_pages else 0),
            level_rows=self.divider_pages,
            play_page=decided.play_page,
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
        predicted_toc_rows = structural_toc_entry_count(
            dividers, count, play_row=decided.play_page is not None
        )
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
            count,
            len(plan),
            len(answer_plan),
            dividers,
            toc_pages=toc_page_count,
            # CARD-305: `dividers` above is `len(section) - len(plan)`, so it
            # is already 0 for a book that prints none; the SOLUTIONS page is
            # the term that has to be said out loud.
            solutions_divider=self.divider_pages,
            play_online=decided.play_page is not None,
        )

        # CARD-200: measured once here, off this book's own trim, and reused
        # verbatim by `produce()`'s own TOC loop below — the same split
        # `decided.toc_page_count` (`section_plan`) was already measured
        # with, so the plan and the draw can never disagree about how a long
        # TOC breaks across pages.
        toc_entries_per_page = _toc_entries_per_page(page_frame(self.page_spec(1)), self.dpi)

        # CARD-298: the interior's page *kinds*, in print order, decided here
        # beside the page count and off the same walk — never read back off
        # the pages, which do not exist yet. `_write_pdf` lays its object
        # table out from these, because a page's medium follows from its kind
        # (`page_medium`) and a mixed file's table has to be allocated before
        # the catalog is written.
        #
        # This list and `produce()` below walk the same five sections in the
        # same order, and `_write_pdf` is what holds them together: it refuses
        # a `kinds` whose length is not the page count, so a kind list that
        # drifted from the walk is a refused export rather than a page whose
        # medium nobody decided. The check is **there** and not here on
        # purpose — `_as_planned` is this method's own liveness guard for the
        # plan/draw disagreement (`TestBookPdf_PagePlanGuardIsLive`), and a
        # second count check here would fire first and retire it.
        # The two front-matter ranges are `produce()`'s own, spelled the same
        # way here — `range(1, TITLE_PAGE_COUNT + 1)` and
        # `range(1 + TITLE_PAGE_COUNT, TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + 1)`
        # — rather than as bare repeat counts, so the two walks read as one
        # walk and every expression that counts the guide counts the title
        # page with it (`tests/test_book_export_interior_cover.py`'s
        # `test_every_guide_counting_expression_counts_the_title_page`).
        page_kinds: List[PageKind] = []
        page_kinds.extend(
            PageKind.TITLE for _ in range(1, TITLE_PAGE_COUNT + 1)
        )
        page_kinds.extend(
            PageKind.GUIDE
            for _ in range(
                1 + TITLE_PAGE_COUNT, TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + 1
            )
        )
        page_kinds.extend(PageKind.TOC for _ in range(toc_page_count))
        page_kinds.extend(
            PageKind.DIVIDER if isinstance(entry, DividerPagePlan) else PageKind.PUZZLE
            for entry in section
        )
        # `produce()` returns before the answer section on a book with no
        # drawable member, so the kinds stop where the pages do.
        if payloads:
            # CARD-390: the Play online page, and the blank that puts it on a
            # right-hand page, sit between the puzzle section and SOLUTIONS.
            if decided.play_page is not None:
                if decided.play_blank_page is not None:
                    page_kinds.append(PageKind.BLANK)
                page_kinds.append(PageKind.PLAY)
            if self.divider_pages:
                page_kinds.append(PageKind.DIVIDER)
            page_kinds.extend(PageKind.ANSWER for _ in answer_plan)

        def produce() -> Iterator[Union[Image.Image, ContentStream]]:
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
            # CARD-206: the blank title / copyright page opens the interior
            # (TITLE_PAGE_COUNT, AC-283). Yielded as an expression, so this
            # frame never holds it while the next page is built — the same
            # rule every page kind below keeps.
            # Since 2026-11-09 it carries the book's title and copyright.
            for title_page_number in range(1, TITLE_PAGE_COUNT + 1):
                yield self.vector_title_contents(len(payloads), title_page_number)

            # CARD-201: the guide is GUIDE_PAGE_COUNT pages, not one — two
            # calls to the same method (page_number selects which half, see
            # create_guide_page's own docstring), each yielded and released
            # exactly as every other page is (CARD-145/CARD-198's "no page
            # outlives the yield that hands it on", restated above).
            # CARD-206: it starts one page later, after the title page, so
            # its first page is a verso (interior page 2) and the two halves
            # face each other.
            for guide_page_number in range(
                1 + TITLE_PAGE_COUNT, TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + 1
            ):
                # CARD-309: the walk cannot reach the guide writer by import
                # (`InteriorPageWriters`), so it goes through the writer set
                # this generator was built with and refuses when there is none.
                page = _drawn_downstream(
                    self.pages.guide,
                    PageKind.GUIDE,
                    self.page_spec(guide_page_number),
                    self.dpi,
                    guide_page_number,
                    puzzle_count=len(puzzles),
                    easy_count=counts[Tier.EASY],
                    medium_count=counts[Tier.MEDIUM],
                    hard_count=counts[Tier.HARD],
                    play_page=decided.play_page,
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
                rows = toc_entries[start : start + toc_entries_per_page]
                # CARD-309, as the guide above: the split is still this walk's
                # own (`toc_entries_per_page`, measured once), so the two media
                # are handed the same slice and cannot re-decide it.
                #
                # The position is bound to `toc_page_number` rather than
                # spelled in each arm, and the choice was measured rather than
                # taken on taste: the vector arm needs it twice (its sheet, and
                # the folio the writer sets), so spelling it inline puts three
                # copies of one expression in this loop and takes
                # `tests/test_book_export_interior_cover.py`'s guide-counting
                # census from 9 sites to 11 for no gain. Bound, that census is
                # unmoved and the cost is one new name in that file's position
                # vocabulary — which is the honest statement of what happened:
                # this walk now holds a name that carries the TOC's page
                # number.
                toc_page_number = TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + 1 + index
                page = _drawn_downstream(
                    self.pages.toc,
                    PageKind.TOC,
                    rows,
                    page_frame(self.page_spec(toc_page_number)),
                    self.dpi,
                    toc_page_number,
                )
                yield page
                del page

            # Each divider's own puzzle span, for its eyebrow (owner,
            # 2026-11-09): the numbers on the pages up to the next divider.
            divider_ranges: Dict[int, Tuple[int, int]] = {}
            opened: Optional[int] = None
            for page_plan in section:
                if isinstance(page_plan, DividerPagePlan):
                    opened = page_plan.page_number
                elif opened is not None and page_plan.numbers:
                    low, high = divider_ranges.get(
                        opened, (min(page_plan.numbers), max(page_plan.numbers))
                    )
                    divider_ranges[opened] = (
                        min(low, *page_plan.numbers), max(high, *page_plan.numbers)
                    )
            for page_plan in section:
                if isinstance(page_plan, DividerPagePlan):
                    # A level's divider (AC-254). Yielded as an expression, so
                    # this frame never holds it while the next page is built.
                    yield self.divider_page(
                        slot_for_level(page_plan.level),
                        page_plan.page_number,
                        page_plan.text,
                        puzzle_range=divider_ranges.get(page_plan.page_number),
                    )
                    continue
                members = [payloads[number - 1] for number in page_plan.numbers]
                # `book_puzzle_vector` imports no generator, so the walk
                # reaches the puzzle writer by import (CARD-309).
                try:
                    if page_plan.pair is None:
                        ((_, payload),) = members
                        page = self.vector_puzzle_page(
                            payload,
                            page_plan.numbers[0],
                            page_plan.page_number,
                            decided.cell_sizes,
                            decided.play_page,
                        )
                    else:
                        page = self.vector_two_up_page(
                            page_plan, [p for _, p in members], decided.play_page
                        )
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
            # CARD-390: the Play online page, immediately after the last
            # puzzle page and before the SOLUTIONS divider. Its blank, when
            # the last puzzle page is right-hand, is the title page's own
            # empty stream: no ink and no folio, the page's position the
            # plan's. Both are vector by `page_medium`'s default; the page
            # itself is drawn downstream, which can reach the landing address.
            if decided.play_page is not None:
                if decided.play_blank_page is not None:
                    yield self.vector_title_page(decided.play_blank_page)
                yield _drawn_downstream(
                    self.pages.play,
                    PageKind.PLAY,
                    self.page_spec(decided.play_page),
                    self.dpi,
                    decided.play_page,
                    puzzles,
                    self.player_domain,
                )
            # CARD-201: the guide grew by GUIDE_PAGE_COUNT pages, not one,
            # and CARD-206 put TITLE_PAGE_COUNT page(s) in front of it, so
            # the SOLUTIONS divider (immediately before the answer section)
            # moved with both — one page before `first_answer_page`, by
            # construction, which already accounts for both constants above.
            #
            # CARD-305: and only when this book prints dividers at all. The
            # answer pages below are unaffected — their numbers come from
            # `first_answer_page`, which has already accounted for this page
            # being absent, so the answer key simply starts one page earlier.
            if self.divider_pages:
                yield self.divider_page(
                    SOLUTIONS_SLOT, first_answer_page - 1, "SOLUTIONS",
                    puzzle_count=len(payloads),
                )
            for index, entry in enumerate(answer_plan):
                page_number = first_answer_page + index
                # CARD-309: the plan (which answers are packed and at what
                # capacity) is this walk's, handed to the answer writers.
                try:
                    if isinstance(entry, PackedAnswerPage):
                        page = _drawn_downstream(
                            self.pages.packed_answer,
                            PageKind.ANSWER,
                            self.page_spec(page_number),
                            self.dpi,
                            entry,
                            payloads,
                            page_number,
                            titles,
                        )
                    else:
                        puzzle_id, payload = payloads[entry.number - 1]
                        title = answer_title(
                            titles.get(str(puzzle_id)), payload.name
                        )
                        page = _drawn_downstream(
                            self.pages.answer,
                            PageKind.ANSWER,
                            self.page_spec(page_number),
                            self.dpi,
                            payload,
                            entry.number,
                            page_number,
                            title,
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
            answer_titles=tuple(
                (puzzle_id, answer_title(titles.get(str(puzzle_id)), payload.name))
                for puzzle_id, payload in payloads
            ),
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
                count,
                answer_pages=count,
                level_dividers=dividers,
                toc_pages=toc_page_count,
                solutions_divider=self.divider_pages,
                play_online=decided.play_page is not None,
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
                solutions_divider=self.divider_pages,
                play_online=decided.play_page is not None,
            ),
            answer_page_count=len(answer_plan),
            pages=_as_planned(produce(), planned),
            page_kinds=tuple(page_kinds),
            play_page=decided.play_page,
            play_block_pages=decided.play_page_count,
        )

    def _write_pdf(
        self,
        pages: Iterable[Union[Image.Image, ContentStream]],
        page_count: int,
        *,
        mode: str,
        kinds: Sequence[PageKind],
    ) -> BytesIO:
        """Write ``pages`` as one PDF, **a medium per page**, rewound to 0.

        ``page_count`` is how many pages ``pages`` will produce, known from
        the page plan before any of them exists. It is not a hint: the PDF's
        object table is laid out from it — one page and one contents object id
        per page, plus an image object for each page that is a bitmap and the
        face's three for the file if any page is not, all allocated before the
        catalog is written — which is what lets the pages themselves arrive one
        at a time rather than as a list (CARD-145). ``pages`` is consumed
        exactly once and no page is held after it is written; a caller that
        wants the pages afterwards must keep them itself.

        ``kinds`` is one :class:`PageKind` per planned page, in page order,
        and it is how this writer learns each page's medium — it asks
        :func:`page_medium`, the module's one decision point, and decides
        nothing itself (CARD-298, AC-4). It is a required keyword for the same
        reason ``mode`` is: a default would be a medium chosen in a signature.
        Each PDF page is its own content stream, so a file may mix the two
        media freely; **that is a sanctioned end state and not a migration
        artefact** (ADR-0042/R2's own words), because the cover is a
        photograph and the section divider is a picture the owner uploads (CARD-311).

        **The medium and the page object must agree, and disagreement is a
        refusal.** A page kind whose medium is ``VECTOR`` must arrive as a
        :class:`~nonogram.admin.book_vector.ContentStream` and a ``RASTER``
        one as an :class:`~PIL.Image.Image`; anything else raises before it is
        written. That is the runtime half of default-DENY: a page kind added
        to the plan and forgotten in :data:`_RASTER_DECLARATIONS` cannot
        quietly ship a DCTDecode page under a vector declaration, and a
        bitmap handed in where operators were declared cannot pass for one.

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
            ValueError: ``mode`` is not a colour space this writer knows, or
                ``kinds`` is not one kind per planned page — both raised
                before the buffer exists, so no partial file is built.
            TypeError: a page arrived in the other medium's representation
                from the one its kind declares.
        """
        if mode not in _PDF_COLOUR_SPACE:
            known = ", ".join(sorted(_PDF_COLOUR_SPACE))
            raise ValueError(
                f"a book PDF is written in one of {known}, not {mode!r}"
            )
        if len(kinds) != page_count:
            raise ValueError(
                f"a {page_count}-page PDF needs {page_count} page kind(s), "
                f"not {len(kinds)}"
            )
        # The media, decided once, before a page exists — through the module's
        # one decision point, so this loop reads a medium and never picks one.
        media = [page_medium(kind) for kind in kinds]
        any_vector = PageMedium.VECTOR in media

        written = BytesIO()
        pdf = PdfParser.PdfParser(f=written, filename="", mode="w+b")
        # The two dates Pillow's own writer stamps a new file with, so the
        # Info dictionary reads the same as it always has.
        pdf.info["CreationDate"] = time.gmtime()
        pdf.info["ModDate"] = time.gmtime()

        # The face's three objects, **first and only when some page is
        # vector** (ADR-0042/R5: once per file, however many pages set text).
        # A raster-only file allocates none of them, which is what keeps the
        # cover file — and any all-raster interior — the object table it has
        # always had rather than one with three unused objects in it.
        font_ref = descriptor_ref = file_ref = None
        if any_vector:
            font_ref = pdf.next_object_id(0)
            descriptor_ref = pdf.next_object_id(0)
            file_ref = pdf.next_object_id(0)

        # A page and a contents object per planned page, plus an image object
        # for each page that is a bitmap, allocated before anything is drawn.
        # This is the whole reason the page count has to be known in advance —
        # and the reason a producer that yields the wrong number of pages is a
        # corrupt file rather than a short one. The image ids are keyed by
        # page index rather than counted, so a mixed file's object table has
        # no hole in it and no page borrows another's id.
        image_refs: Dict[int, Any] = {}
        page_refs: List[Any] = []
        contents_refs: List[Any] = []
        for index in range(page_count):
            if media[index] is PageMedium.RASTER:
                image_refs[index] = pdf.next_object_id(0)
            page_refs.append(pdf.next_object_id(0))
            contents_refs.append(pdf.next_object_id(0))
            pdf.pages.append(page_refs[-1])

        pdf.start_writing()
        pdf.write_header()
        pdf.write_comment("created by Pillow PDF driver")
        pdf.write_catalog()

        if any_vector:
            write_face_objects(
                pdf,
                interior_face_bytes(),
                interior_face_metrics(),
                font_ref,
                descriptor_ref,
                file_ref,
            )

        index = 0
        for page in _as_planned(pages, page_count):
            if media[index] is PageMedium.RASTER:
                if not isinstance(page, Image.Image):
                    raise TypeError(
                        f"page {index + 1} is a declared {kinds[index].value} "
                        f"bitmap, but arrived as {type(page).__name__}"
                    )
                self._write_page(pdf, page, image_refs[index], page_refs[index],
                                 contents_refs[index], mode)
            else:
                if not isinstance(page, ContentStream):
                    raise TypeError(
                        f"page {index + 1} is a vector {kinds[index].value} "
                        f"page, but arrived as {type(page).__name__}"
                    )
                write_vector_page(
                    pdf, page, page_refs[index], contents_refs[index], font_ref
                )
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
