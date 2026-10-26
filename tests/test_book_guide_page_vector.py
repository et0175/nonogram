"""The guide page drawn as PDF content-stream operators (CARD-296, ADR-0042).

CARD-293's spike refused to price this page and CARD-294 shipped the
vocabulary; :mod:`nonogram.admin.book_guide_vector` is the first drawing of
it, and this file is where its claims are held.

**Everything here reads the written file**, which is ADR-0042/R6: a claim about
an interior page's geometry, rule widths or tone is asserted against the
content stream of the PDF, not against a rendered bitmap. The one place an
engine that did not write the file is asked anything is AC-5's clue digits,
and what it is asked for is **text** — ``pdftotext``'s extraction, which
exercises the embedded face's ``/Widths``, its ``/Encoding`` and the ``Tj``
operand together. No test below recovers a number by counting pixels.

Why the floor is checked here at all, when CON-020 already has a verifier
---------------------------------------------------------------------------

CON-020's verifier (``tests/test_book_interior_type_floor.py``'s
``TestInteriorType_EveryFaceHoldsTheFloor``) works by spying on
``ImageDraw.ImageDraw.text`` and tagging each call with the enclosing
function's name. **A vector page makes no such call**, so that instrument is
blind to this one — and its floor assertion is ``below_floor(...) == []``,
which is *vacuously true of an empty recording*. What saves it there is the
sibling that requires a set of covered kinds to be present.

:class:`TestGuidePage_EveryFaceHoldsTheFloorInTheStream` carries both halves
of that pairing into the new medium, and the registry-level rewrite of
CON-020's own check stays CARD-299's (CARD-296 G-5):

* the floor is read off the ``Tf`` operands of the written stream — the
  operand a reader's viewer obeys, not a number this project remembers;
* the writer's own record of what it set
  (:class:`~nonogram.admin.book_guide_vector.DrawnFace`) is held **against**
  that stream, string for string and size for size, so the record cannot
  drift from the file. It drifted once while this card was being written: the
  page's title was recorded and not drawn, and this is the assertion that
  would have caught it;
* and the kinds the record covers are required to be
  :data:`~nonogram.admin.book_guide_vector.FACE_KINDS`, so the check cannot
  pass on nothing.
"""

from __future__ import annotations

import ast
import dataclasses
import random
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from nonogram.admin import book_guide_vector as guide_vector
from nonogram.admin import book_pdf_generator
from nonogram.admin.book_guide_vector import (
    BODY_TEXT,
    CLUE_DIGIT,
    EXEMPT_KINDS,
    FACE_KINDS,
    GUIDE_PAGE_NUMBERS,
    LEGEND_NAME,
    TITLE,
    GuidePage,
    guide_pages,
    write_guide_pdf,
)
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_vector import ContentStream
from nonogram.admin.book_pdf_generator import (
    FOLIO_PT,
    GUIDE_ASSUME_STEPS,
    GUIDE_BASIC_RULE_CLUE,
    GUIDE_BASIC_RULE_LENGTH,
    GUIDE_BODY_PT,
    GUIDE_DIFFICULTY_LABELS,
    GUIDE_TECHNIQUES_1,
    GUIDE_TECHNIQUES_2,
    GUIDE_TITLE_PT,
    WORKED_EXAMPLE_CLUE,
    WORKED_EXAMPLE_LENGTH,
    WORKED_EXAMPLE_STEPS,
    BookPDFGenerator,
    ExampleStep,
    example_line_layout,
    guide_icon_layout,
)
from nonogram.export.layout import Layout, compute_layout
from tests.helpers import pdf_vector
from tests.helpers.book_corpus import corpus_book

#: Why a test may be skipped. A host with no poppler has no independent
#: engine, so the honest state is "not checked here", never "checked and
#: fine" — the same wording ``tests/test_book_pdf_vector_primitives.py`` uses.
NO_POPPLER = "poppler (pdftotext) is not installed: the independent engine is absent"

needs_poppler = pytest.mark.skipif(pdf_vector.PDFTOTEXT is None, reason=NO_POPPLER)

#: The 10x10 cm minimum trim's stored margins — the same book
#: ``tests/test_book_interior_type_floor.py`` measures the floor on, written
#: out there too rather than shared, so each file's statement of the sheet it
#: measured stays its own.
#: CON-020's floor, in points. Written out here rather than imported — the
#: writer deliberately declares no such constant (see the comment beside
#: :data:`~nonogram.admin.book_guide_vector.EXEMPT_KINDS`), and this file's
#: statement of what it is holding the page to stays its own, exactly as
#: ``tests/test_book_interior_type_floor.py`` writes the same figure out.
FLOOR_PT = 10.0

#: The only tone this page may ink, as a ``g``/``G`` operand: pure black.
#: Written here for the same reason :data:`FLOOR_PT` is — the control states
#: what it holds the page to, and the writer's own ``_BLACK`` is the thing
#: being checked rather than the authority for it.
_BLACK_TONE = 0.0

MIN_TRIM_CM = 10.0
MIN_TRIM_GUTTER_CM = "0.95"
MIN_TRIM_OUTSIDE_CM = "0.64"


def min_trim_book() -> Book:
    """The baseline book's print specification at the 10x10 cm minimum trim."""
    return Book(
        book_id="card-296-min-trim",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="The book CARD-296's vector guide is drawn on.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=f"{MIN_TRIM_CM:.2f}",
        trim_height_cm=f"{MIN_TRIM_CM:.2f}",
        gutter_margin_cm=MIN_TRIM_GUTTER_CM,
        outside_margin_cm=MIN_TRIM_OUTSIDE_CM,
    )


BOOKS = {"book1": corpus_book, "min-trim": min_trim_book}

#: The tier counts the page prints on its full form. Arbitrary — the page
#: letters whatever it is handed — but fixed so the drawn strings are stable.
COUNTS = dict(puzzle_count=24, easy_count=8, medium_count=8, hard_count=8)

#: Which kinds of face each profile's guide really sets, and why the second is
#: a subset rather than the whole of :data:`FACE_KINDS`.
#:
#: ``book1`` sets every kind there is, across its two pages: page 1 the title,
#: the body, its diagrams' clue digits and the folio; page 2 the pipeline's
#: labels and the legend's names as well.
#:
#: ``min-trim`` sets four, and both absences are today's page behaving as
#: designed rather than this writer omitting something:
#:
#: * no ``pipeline label`` — the 10 cm trim drives the page to the most
#:   stripped-down of the five fallback forms (``bare_level`` 2), and the
#:   pipeline diagram is dropped from ``bare_level`` 1 onward (CARD-201);
#: * no ``folio`` — CARD-200's omit-rather-than-collide rule: the page's own
#:   content already reaches the bottom margin, so the page number is omitted
#:   rather than set on top of the last line.
REQUIRED_KINDS = {
    "book1": FACE_KINDS,
    "min-trim": frozenset({TITLE, BODY_TEXT, CLUE_DIGIT, LEGEND_NAME}),
}

#: The fewest faces each profile's guide may set, asserted so a page that
#: silently stopped drawing most of itself could not pass the floor check by
#: setting almost nothing. Measured, and deliberately well under the real
#: figures (``book1`` sets 66 across its two pages, ``min-trim`` 29) so an
#: ordinary content change does not red it and a collapse does.
MINIMUM_FACES = {"book1": 50, "min-trim": 20}

_PAGES: Dict[str, List[GuidePage]] = {}
_PDFS: Dict[str, bytes] = {}


def drawn(profile: str) -> List[GuidePage]:
    """Both halves of ``profile``'s guide, drawn once per session."""
    if profile not in _PAGES:
        generator = BookPDFGenerator(BOOKS[profile]())
        _PAGES[profile] = guide_pages(generator.page_spec, generator.dpi, **COUNTS)
    return _PAGES[profile]


def written(profile: str) -> bytes:
    """``profile``'s guide as the bytes of a PDF, written once per session."""
    if profile not in _PDFS:
        pages = drawn(profile)
        _PDFS[profile] = write_guide_pdf(pages, len(pages)).getvalue()
    return _PDFS[profile]


@pytest.fixture(params=sorted(BOOKS))
def profile(request) -> str:
    """Book 1, and the same book at the 10x10 cm minimum trim."""
    return request.param


#: One text object as the stream spells it: ``/F1 <size> Tf <x> <y> Td
#: (<text>) Tj``. Its own expression rather than
#: ``pdf_vector.type_sizes``, because this one has to recover the *string*
#: beside the size — the pairing is what makes the writer's record checkable
#: against the file rather than merely plausible beside it.
_SHOWN = re.compile(
    r"/\w+\s+(-?\d+(?:\.\d+)?)\s+Tf\s+"
    r"-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s+Td\s+"
    r"\((?P<text>(?:\\.|[^()\\])*)\)\s+Tj"
)


def shown(stream: str) -> List[Tuple[float, str]]:
    """Every ``(point size, string)`` the stream sets, in order.

    The escapes are undone in the reverse order
    ``book_vector._escape`` applies them, so a string carrying a backslash or
    a bracket comes back as the caller's own.
    """
    out: List[Tuple[float, str]] = []
    for match in _SHOWN.finditer(stream):
        text = match.group("text")
        for escaped, plain in ((r"\r", "\r"), (r"\n", "\n"), (r"\)", ")"), (r"\(", "(")):
            text = text.replace(escaped, plain)
        out.append((float(match.group(1)), text.replace("\\\\", "\\")))
    return out


# --------------------------------------------------------------------------
# AC-1 — the guide carries no bitmap
# --------------------------------------------------------------------------


class TestGuidePage_CarriesNoImageXObject:
    """AC-1 / ADR-0042/R1 — no guide page references an image XObject.

    The page-local control that fails first. ADR-0042/R1's own derived test,
    over *every* interior page kind at once, is CARD-298's.
    """

    def test_no_page_resource_dictionary_offers_an_xobject(self):
        keys = pdf_vector.page_resource_keys(written("book1"))

        assert len(keys) == len(GUIDE_PAGE_NUMBERS)
        for page in keys:
            assert "XObject" not in page, page
            assert "Font" in page, page

    def test_the_file_holds_no_image_object_and_no_jpeg_stream(self):
        data = written("book1")

        assert b"/Image" not in data
        assert b"DCTDecode" not in data

    def test_both_profiles_carry_no_bitmap_not_only_book_one(self, profile):
        """AC-1 at the minimum trim as well (review cycle 1, F-7).

        The two assertions above run on ``book1`` only, and the minimum trim
        got just the non-vacuity test — yet it is the profile that drives the
        page to its most stripped-down fallback form, which is where a writer
        would be most tempted to fall back on a bitmap.

        Written as its own cell rather than by adding ``profile`` to those two,
        because **G-6's gate is a node-id set difference and a ``parametrize``
        id is a node id**: parameterizing them would delete
        ``…::test_no_page_resource_dictionary_offers_an_xobject`` and report as
        a removed test. (CARD-298 owns ADR-0042/R1's derived check over every
        page kind, which is where these three stop being page-local.)
        """
        data = written(profile)
        keys = pdf_vector.page_resource_keys(data)

        assert len(keys) == len(GUIDE_PAGE_NUMBERS)
        for page in keys:
            assert "XObject" not in page, page
            assert "Font" in page, page
        assert b"/Image" not in data
        assert b"DCTDecode" not in data

    def test_the_pages_are_not_empty_which_is_what_makes_the_two_above_mean_anything(
        self, profile
    ):
        """The non-vacuity floor: a file with no pages would pass both above.

        Every page carries operators, and enough of them that "the guide was
        drawn" is a statement about a page rather than about a blank sheet.
        """
        pages = drawn(profile)

        assert len(pages) == len(GUIDE_PAGE_NUMBERS)
        for page in pages:
            assert len(page.stream.operators) > 50, (page.page_number, page.fallback_level)
            assert page.stream.render(), page.page_number


# --------------------------------------------------------------------------
# AC-2 — every face holds the 10 pt floor, and the check can see it
# --------------------------------------------------------------------------


class TestGuidePage_EveryFaceHoldsTheFloorInTheStream:
    """AC-2 and EC(CON-020) — at the Book 1 profile and at the minimum trim.

    Three assertions, and the first alone would be worth little: a stream with
    no text in it holds every floor there is. See this module's docstring for
    why the pairing is what the claim rests on.
    """

    def test_every_type_size_in_the_stream_is_at_least_ten_points(self, profile):
        under = [
            (page.page_number, size)
            for page in drawn(profile)
            for size in pdf_vector.type_sizes("\n".join(page.stream.operators))
            if size < FLOOR_PT
        ]

        assert under == []

    def test_the_writers_record_is_exactly_what_the_stream_shows(self, profile):
        """The record cannot drift from the file, which is AC-2's "can see it".

        Caught a real defect while this card was being written: the page's
        title was appended to the record and never written to the stream, so
        a floor check reading the record alone would have reported a size no
        reader would ever see.
        """
        for page in drawn(profile):
            from_stream = shown("\n".join(page.stream.operators))
            from_record = [(face.size_pt, face.text) for face in page.faces]

            assert sorted(from_stream) == sorted(from_record), page.page_number

    def test_the_record_covers_every_kind_of_face_the_page_sets(self, profile):
        """The non-vacuity floor, carried over from CON-020's own sibling.

        ``TestInteriorType_EveryFaceHoldsTheFloor``'s floor assertion is
        vacuously true on an empty recording; what makes it bite is the
        sibling requiring a set of kinds. This is that sibling.
        """
        covered = frozenset().union(*(page.kinds for page in drawn(profile)))

        assert REQUIRED_KINDS[profile] <= covered, sorted(covered)
        assert covered <= FACE_KINDS, sorted(covered - FACE_KINDS)

    def test_the_page_sets_enough_faces_for_the_floor_check_to_be_about_a_page(
        self, profile
    ):
        total = sum(len(page.faces) for page in drawn(profile))

        assert total >= MINIMUM_FACES[profile], total

    def test_no_kind_on_this_page_is_exempt_from_the_floor(self):
        """CON-020's exemption is two named functions and reaches neither page.

        Stated as an assertion rather than as a comment, because "there is no
        exemption here" is a claim AC-5 rests on and a comment cannot fail.
        """
        assert EXEMPT_KINDS == frozenset()


# --------------------------------------------------------------------------
# AC-4 — one grid routine, and the worked example goes through it
# --------------------------------------------------------------------------


class TestGuidePage_WorkedExampleReusesTheGridRoutine:
    """AC-4 — derived from the module's AST, default-DENY (ADR-0039/R2).

    **A drawing path this cannot classify is a FAILURE, not a pass.** The set
    of functions it inspects is every function in the module; the set it
    permits to touch a ``Layout``'s grid is named below with a role each, and
    a function that reaches one of those attributes without a role reds this
    class rather than being skipped.

    CARD-296's AC-4 asks for "CARD-295's grid routine". **CARD-295 runs after
    this card** — wave 61 is ordered guide-first, as the routing note on
    CARD-294's N-2 records — so there is no such routine to call, and
    ``draw_line_diagram`` is it: it takes a ``Layout`` and a set of
    filled/crossed cells, knows nothing about a guide page, and is what
    CARD-295 is meant to consume.
    """

    #: The names a ``Layout`` carries that this guard does **not** treat as
    #: grid ink, each with the reason that earns it. :attr:`GRID_ATTRIBUTES` is
    #: everything else, so the guarded set is derived from the dataclass
    #: itself (ADR-0039/R2) and a field or property added to ``Layout`` is
    #: guarded the day it lands.
    #:
    #: **This replaces a hand-written set of seven whose stated derivation was
    #: false** (review cycle 1, F-2). It claimed to be what
    #: ``book_pdf_generator._stroke_drawing``/``_write_clues``/
    #: ``draw_example_line`` read between them; those three also read ``frame``,
    #: ``thick_rule`` and ``thin_rule``, all omitted, so the set was exactly the
    #: subset that kept the module green — and worse, every guarded name had an
    #: **unguarded synonym** one level down (``Layout.grid_lines`` =
    #: ``vertical_lines + horizontal_lines``, ``clue_entries`` = ``row_clues +
    #: column_clues``). A complete second grid implementation spelled around it
    #: — ruled lines through ``grid_lines``, the frame through ``frame``, the
    #: digits through ``row_clues``/``column_clues`` — passed this class 4/4.
    #:
    #: Two reason classes, each with an assertion of its own below rather than
    #: a word here:
    #:
    #: * ``"not ink"`` — a count or the sheet's metadata: it is neither a
    #:   coordinate, a stroke weight, nor a placed number, so no second grid
    #:   can be drawn out of it. Held by
    #:   :meth:`test_every_name_the_raster_grid_routines_read_is_guarded`.
    #: * ``"shared name"`` — a name the guard cannot attribute, because objects
    #:   in *this* module carry it too and the walk matches attribute names.
    #:   Guarding ``width`` would report a ``PageFrame``'s width and a
    #:   ``_Mark``'s. These are the only two names that escape the name walk,
    #:   and what closes the escape is the second assertion in this class:
    #:   a receiver spelled as a ``Layout`` may not be read for them either.
    ALLOWED = {
        "rows": "not ink",
        "columns": "not ink",
        "row_gutter_cells": "not ink",
        "column_gutter_cells": "not ink",
        "orientation": "not ink",
        "dpi": "not ink",
        "page": "not ink",
        "width_inches": "not ink",
        "height_inches": "not ink",
        "width": "shared name",
        "height": "shared name",
    }

    #: Every field and property of a ``Layout`` that is grid ink — derived, as
    #: the complement of :attr:`ALLOWED` over the dataclass's own surface. It
    #: holds ``grid_lines``, ``clue_entries``, ``row_clues``, ``column_clues``,
    #: ``cell`` and ``margin`` by construction, which is the whole point.
    GRID_ATTRIBUTES = frozenset(
        {field.name for field in dataclasses.fields(Layout)}
        | {name for name, member in vars(Layout).items() if isinstance(member, property)}
    ) - frozenset(ALLOWED)

    #: Every function allowed to read one of :attr:`GRID_ATTRIBUTES`, the role
    #: that earns it, and **exactly which names that role covers**. A function
    #: here that stops touching the grid is as much a finding as one that
    #: starts, and a function that starts reading a *further* grid name is a
    #: finding too: both halves are asserted, so a second grid appended inside
    #: a function that already has a role cannot inherit it.
    ROLES = {
        "draw_line_diagram": (
            frozenset({"vertical_lines", "horizontal_lines", "thin_rule"}),
            "the one composition: marks, rules, clue digits",
        ),
        "_stroke_layout": (
            frozenset({"vertical_lines", "horizontal_lines", "frame"}),
            "strokes the ruled lines and the frame",
        ),
        "_write_clue_digits": (
            frozenset({"clue_entries", "clue_font_size"}),
            "sets the clue digits",
        ),
        "diagram_left": (
            frozenset({"frame", "vertical_lines"}),
            "reads where the ink starts",
        ),
        "diagram_box": (
            frozenset({"grid_top", "grid_right", "grid_bottom", "thick_rule"}),
            "reads the box the raster routine crops out of its canvas",
        ),
        "translation": (
            frozenset({"grid_top"}),
            "lands a diagram's bleed corner where the page put it",
        ),
        "pad": (
            frozenset({"thick_rule"}),
            "the paste pad: one heavy rule of bleed around a diagram",
        ),
        "guide_page": (
            frozenset({"thick_rule"}),
            "hoists that same paste pad once, off the icon layout — exactly "
            "what the raster page reads at book_pdf_generator.py:4361, and the "
            "only grid number the page itself reads",
        ),
    }

    #: How this module spells a ``Layout``-valued expression. An equality
    #: against what it really writes (asserted non-vacuous below), and the
    #: subject of the second assertion: a receiver spelled this way may be read
    #: only for a guarded name, which is what stops ``layout.width`` or
    #: ``layout.cell`` from being a way around :attr:`ALLOWED`.
    LAYOUT_SPELLINGS = frozenset({"layout", "self.layout", "icon_layout"})

    @staticmethod
    def _module_source() -> str:
        return Path(guide_vector.__file__).read_text(encoding="utf-8")

    @classmethod
    def _functions(cls) -> Dict[str, ast.AST]:
        """Every function and method defined in the module, by name."""
        tree = ast.parse(cls._module_source())
        found: Dict[str, ast.AST] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[node.name] = node
        return found

    @classmethod
    def _grid_reads(cls) -> Dict[str, frozenset]:
        """``{function: the grid names it reads}``, for every function that does."""
        found: Dict[str, frozenset] = {}
        for name, node in cls._functions().items():
            read = {
                child.attr
                for child in ast.walk(node)
                if isinstance(child, ast.Attribute) and child.attr in cls.GRID_ATTRIBUTES
            }
            if read:
                found[name] = frozenset(read)
        return found

    def test_only_the_named_routines_touch_a_layouts_grid(self):
        """Default-DENY: an unclassified function reaching the grid is a failure."""
        touching = self._grid_reads()

        assert set(touching) == set(self.ROLES), {
            "unclassified": sorted(set(touching) - set(self.ROLES)),
            "classified but no longer touching": sorted(set(self.ROLES) - set(touching)),
        }

    def test_each_routine_reads_exactly_the_grid_names_its_role_declares(self):
        """And no more: a second grid inside a classified function is a failure too.

        The function-level equality above says *who* may read the grid; this
        says *what*, so ``guide_page``'s role (one paste pad) cannot quietly
        become "draws the grid".
        """
        touching = self._grid_reads()
        declared = {name: names for name, (names, _why) in self.ROLES.items()}

        assert touching == declared, {
            name: {
                "reads": sorted(touching.get(name, ())),
                "role declares": sorted(declared.get(name, ())),
            }
            for name in set(touching) | set(declared)
            if touching.get(name) != declared.get(name)
        }

    def test_a_layout_is_never_read_for_a_name_the_guard_lets_through(self):
        """The escape the name walk has to leave open, closed from the receiver end.

        :attr:`ALLOWED` has to let ``width`` and ``height`` through, because
        other classes in this module carry those names too — ``PageFrame``,
        ``_Mark`` and ``_Diagram`` carry both and ``_PipelineGeometry`` carries
        ``width``, which the test below asserts rather than asks a reader to
        take on trust. So a ``Layout``'s
        own ``width``, ``height``, ``cell`` or ``rows`` would be invisible to
        the walk — except that a ``Layout`` in this module is spelled one of
        :attr:`LAYOUT_SPELLINGS`, and a receiver spelled that way may be read
        only for a guarded name.

        **The named limit, stated rather than implied**: a ``Layout`` rebound
        to a name this set does not hold (``lay = self.layout``) escapes this
        assertion, and the only names it would gain are ``width`` and
        ``height`` — the sheet's own size, which no grid can be drawn out of
        once ``cell``, ``margin`` and every line, clue and bound are guarded by
        name. Everything else lands in the assertions above whatever the
        receiver is called.
        """
        tree = ast.parse(self._module_source())
        reads = sorted(
            {
                (ast.unparse(node.value), node.attr)
                for node in ast.walk(tree)
                if isinstance(node, ast.Attribute)
                and ast.unparse(node.value) in self.LAYOUT_SPELLINGS
            }
        )

        assert reads, "no Layout-spelled receiver in the module: this guard is vacuous"
        for spelling in sorted(self.LAYOUT_SPELLINGS):
            assert any(
                receiver == spelling for receiver, _attr in reads
            ), f"{spelling} is in LAYOUT_SPELLINGS and is not written in the module"
        unguarded = [
            (receiver, attr) for receiver, attr in reads if attr not in self.GRID_ATTRIBUTES
        ]

        assert unguarded == [], unguarded

    def test_every_name_the_raster_grid_routines_read_is_guarded(self):
        """The derivation claim, as an assertion instead of a sentence.

        The shape of the thing being guarded is what the raster routines this
        module replaces read off a ``Layout``:
        ``book_pdf_generator._stroke_drawing``, ``_write_clues`` and
        ``draw_example_line``. Every one of those names must be in
        :attr:`GRID_ATTRIBUTES`, so :attr:`ALLOWED` cannot drop one of them to
        stay green — which is exactly what the previous hand-written set did
        with ``frame``, ``thick_rule`` and ``thin_rule``.

        **One exception, named and reasoned**: ``draw_example_line`` reads
        ``layout.width`` — the width of the full-page canvas it draws into
        *before cropping*. This medium has nothing to crop and never needs it
        (:func:`~nonogram.admin.book_guide_vector.diagram_box` is the crop), and
        ``width`` is a ``"shared name"`` the walk cannot attribute, so it is
        allowed here and refused on a ``Layout`` receiver by
        :meth:`test_a_layout_is_never_read_for_a_name_the_guard_lets_through`.
        """
        raster = ast.parse(
            Path(book_pdf_generator.__file__).read_text(encoding="utf-8")
        )
        universe = self.GRID_ATTRIBUTES | frozenset(self.ALLOWED)
        read: set = set()
        for node in ast.walk(raster):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name not in ("_stroke_drawing", "_write_clues", "draw_example_line"):
                continue
            read |= {
                child.attr
                for child in ast.walk(node)
                if isinstance(child, ast.Attribute) and child.attr in universe
            }

        assert read, "the raster routines were not found: this derivation is vacuous"
        assert read - self.GRID_ATTRIBUTES == {"width"}, sorted(
            read - self.GRID_ATTRIBUTES
        )

    def test_every_allowed_name_is_a_layout_name_with_a_live_reason(self):
        """The allow-list cannot hold a stale name or an unjustified one.

        Each key must still be a field or property of ``Layout`` — a name that
        has gone is a licence for whatever takes it next (ADR-0039/R3) — and
        each ``"shared name"`` must still be carried by another class in this
        module, because that ambiguity is the whole reason it is allowed. The
        day nothing else carries ``width``, the name is guardable and this test
        says so.
        """
        # Read off ``Layout`` again rather than as ``GRID_ATTRIBUTES |
        # ALLOWED``, which is the expression the set is built from and could
        # not fail.
        surface = frozenset(
            {field.name for field in dataclasses.fields(Layout)}
            | {
                name
                for name, member in vars(Layout).items()
                if isinstance(member, property)
            }
        )

        assert frozenset(self.ALLOWED) <= surface, sorted(
            frozenset(self.ALLOWED) - surface
        )
        assert set(self.ALLOWED.values()) == {"not ink", "shared name"}
        for name, reason in sorted(self.ALLOWED.items()):
            if reason != "shared name":
                continue
            carriers = sorted(
                value.__name__
                for value in vars(guide_vector).values()
                if isinstance(value, type)
                and value is not Layout
                and name
                in set(getattr(value, "__annotations__", {}))
                | {
                    key
                    for key, member in vars(value).items()
                    if isinstance(member, property)
                }
            )

            assert carriers, name

    def test_exactly_one_routine_strokes_the_ruled_lines(self):
        """``_stroke_layout`` is called from one place, and it is the composition."""
        callers = {
            name
            for name, node in self._functions().items()
            if any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == "_stroke_layout"
                for child in ast.walk(node)
            )
        }

        assert callers == {"draw_line_diagram"}, callers

    def test_exactly_one_routine_writes_the_clue_digits(self):
        callers = {
            name
            for name, node in self._functions().items()
            if any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == "_write_clue_digits"
                for child in ast.walk(node)
            )
        }

        assert callers == {"draw_line_diagram"}, callers

    def test_the_page_draws_every_diagram_through_that_one_routine(self, monkeypatch):
        """Behavioural, not structural: the page really goes through it.

        The worked example's own ``(clue, length)`` has to appear among the
        layouts handed to ``draw_line_diagram``, and so has every technique's
        and the basic rule's. A second grid implementation would show up here
        as a diagram that never arrived.
        """
        seen: List[Tuple[int, int]] = []
        real = guide_vector.draw_line_diagram

        def spy(stream, layout, step, **kwargs):
            # The diagram's own shape: how many cells its line has, and how
            # many clue digits sit beside it. That pair identifies each of
            # the page's ``(clue, length)`` diagrams without reading anything
            # the writer chose.
            seen.append((len(layout.vertical_lines) - 1, len(layout.clue_entries)))
            return real(stream, layout, step, **kwargs)

        monkeypatch.setattr(guide_vector, "draw_line_diagram", spy)
        generator = BookPDFGenerator(corpus_book())
        pages = guide_pages(generator.page_spec, generator.dpi, **COUNTS)

        assert sum(len(page.faces) for page in pages) > 0
        # The worked example is a 6-cell line with one row clue, drawn once
        # per step of WORKED_EXAMPLE_STEPS.
        worked = (WORKED_EXAMPLE_LENGTH, len(WORKED_EXAMPLE_CLUE))
        assert seen.count(worked) == len(WORKED_EXAMPLE_STEPS), seen
        # And the basic rule's line, a different (clue, length) pair.
        assert (GUIDE_BASIC_RULE_LENGTH, len(GUIDE_BASIC_RULE_CLUE)) in seen, seen


class TestGuidePage_EveryDiagramStaysInsideItsOwnBox:
    """The control the first draft of this module did not have, and needed.

    The raster routine draws a line diagram into a **full-page canvas** and
    then crops a box out of it, so ink outside the box is simply discarded —
    and some is drawn: ``guide_icon_layout`` drops the layout's frame but
    keeps the horizontal rules, which run the whole width of the sheet,
    through the row-clue gutter the bare cell icon does not use. A content
    stream has nothing to crop.

    The first draft of
    :func:`~nonogram.admin.book_guide_vector.draw_line_diagram` translated the
    layout and drew everything, so each of page 1's three cell-state icons
    grew an extra empty cell to its left, out in the page's margin. **Every
    assertion in this file passed.** It was caught by looking at a render,
    which is the kind of catching a board does not get to rely on, so the
    claim now has a control: a diagram inks nothing outside the box it tells
    the page it occupies.

    Path operators only (``m``, ``l``, ``re``). A text object's own glyph box
    is not a path, and where a clue digit sits is
    :class:`TestGuidePage_WorkedExampleClueDigitsAreNotExempt`'s business with
    poppler's extraction beside it.
    """

    _NUMBER = r"-?\d+(?:\.\d+)?"
    _PATHS = re.compile(
        rf"({_NUMBER}) ({_NUMBER}) m(?: ({_NUMBER}) ({_NUMBER}) l)?"
        rf"|({_NUMBER}) ({_NUMBER}) ({_NUMBER}) ({_NUMBER}) re"
    )

    @classmethod
    def _inked_pixels(cls, stream) -> List[Tuple[float, float]]:
        """Every path point the stream carries, back in device pixels.

        The inverse of the stream's own conversion — points to pixels, and the
        PDF's bottom-left origin back to the layout's top-left — written here
        rather than asked of the writer, so the two are not one piece of
        arithmetic read twice.
        """
        scale = stream.dpi / 72.0
        found: List[Tuple[float, float]] = []
        for match in cls._PATHS.finditer("\n".join(stream.operators)):
            move_x, move_y, line_x, line_y, box_x, box_y, box_w, box_h = match.groups()
            if box_x is not None:
                x, y = float(box_x), float(box_y)
                found += [(x, y), (x + float(box_w), y + float(box_h))]
            else:
                found.append((float(move_x), float(move_y)))
                if line_x is not None:
                    found.append((float(line_x), float(line_y)))
        return [(x * scale, stream.height_px - y * scale) for x, y in found]

    def _layouts(self, spec):
        yield "icon", guide_icon_layout(spec)
        for clue, length in (
            (GUIDE_BASIC_RULE_CLUE, GUIDE_BASIC_RULE_LENGTH),
            (WORKED_EXAMPLE_CLUE, WORKED_EXAMPLE_LENGTH),
        ):
            yield f"{clue} on {length}", example_line_layout(spec, clue, length)

    def test_a_diagram_inks_nothing_outside_the_box_it_declares(self, profile):
        generator = BookPDFGenerator(BOOKS[profile]())
        spec = generator.page_spec(GUIDE_PAGE_NUMBERS[0])
        checked = 0
        for name, layout in self._layouts(spec):
            cells = len(layout.vertical_lines) - 1
            stream = ContentStream(width_px=4000, height_px=4000, dpi=generator.dpi)
            guide_vector.draw_line_diagram(
                stream,
                layout,
                ExampleStep("", "", frozenset(range(cells)), frozenset({0})),
            )
            left, top, right, bottom = guide_vector.diagram_box(layout)
            # A frame's border is centred ON its boundary coordinate, so half
            # a heavy rule hangs outside the box by design — the same sideways
            # bleed every puzzle page's own grid has. One pixel on top of that
            # for the stream's 0.001 pt coordinate rounding.
            slack = layout.thick_rule / 2 + 1
            outside = [
                (x, y)
                for x, y in self._inked_pixels(stream)
                if not (left - slack <= x <= right + slack)
                or not (top - slack <= y <= bottom + slack)
            ]

            assert outside == [], (name, (left, top, right, bottom), outside[:4])
            checked += 1

        assert checked == 3

    def test_the_pipeline_inks_nothing_outside_the_extent_it_declares(self, profile):
        """The second declared box, which nothing held any ink to (cycle 1, F-8).

        :func:`~nonogram.admin.book_guide_vector.pipeline_extent` is what
        ``guide_page``'s fit loop and ``fits_width`` consume — a content stream
        cannot be measured by rendering it, so the diagram states its own size
        and the page believes it. Nothing checked that the drawing then stays
        inside it. Measured at review: it does (no live overflow), which is
        what makes this a control rather than a fix.

        Path ink only, as everywhere in this class; the labels are text and are
        :class:`TestGuidePage_EveryFaceHoldsTheFloorInTheStream`'s business.
        """
        generator = BookPDFGenerator(BOOKS[profile]())
        spec = generator.page_spec(GUIDE_PAGE_NUMBERS[0])
        body_px = GUIDE_BODY_PT * generator.dpi / 72.0
        width, height = guide_vector.pipeline_extent(spec, GUIDE_ASSUME_STEPS, body_px)
        x, y = 100.0, 200.0
        stream = ContentStream(width_px=8000, height_px=8000, dpi=generator.dpi)
        guide_vector.draw_pipeline(
            stream, spec, GUIDE_ASSUME_STEPS, body_px, GUIDE_BODY_PT, x=x, y=y
        )
        # One pixel for the stream's 0.001 pt coordinate rounding, the same
        # slack the diagram-box assertion above allows itself.
        slack = 1.0
        outside = [
            (px, py)
            for px, py in self._inked_pixels(stream)
            if not (x - slack <= px <= x + width + slack)
            or not (y - slack <= py <= y + height + slack)
        ]

        assert len(self._inked_pixels(stream)) >= 8
        assert outside == [], ((x, y, width, height), outside[:4])

    def test_the_diagram_really_inks_something(self, profile):
        """Non-vacuity: a diagram that drew nothing would pass the test above."""
        generator = BookPDFGenerator(BOOKS[profile]())
        spec = generator.page_spec(GUIDE_PAGE_NUMBERS[0])
        for name, layout in self._layouts(spec):
            stream = ContentStream(width_px=4000, height_px=4000, dpi=generator.dpi)
            guide_vector.draw_line_diagram(
                stream, layout, ExampleStep("", "", frozenset({0}), frozenset())
            )

            assert len(self._inked_pixels(stream)) >= 4, name


# --------------------------------------------------------------------------
# AC-5 — a clue digit on the guide is NOT exempt from the floor
# --------------------------------------------------------------------------


class TestGuidePage_WorkedExampleClueDigitsAreNotExempt:
    """AC-5 — CON-020's clue-digit exemption does not reach this page.

    The exemption is **exactly** ``png._draw_clues`` and
    ``book_pdf_generator._write_clues`` (CARD-184 AC-3), and it is bounded
    that way for a reason that does not apply here: a *puzzle page's* clue
    digits are bound to their cell, and INV-006's cell floor puts them at
    8.4 pt, so no setting reaches 10 pt there without breaking the cell
    floor. The floor test's own docstring states the other half — *"The guide
    page's worked example draws its clue digits through ``_write_clues`` too
    ... those are the reader's instruction text and are **never** exempt"*.

    This medium has no ``_write_clues`` to tag, so the distinction is made
    deliberately rather than inherited.
    """

    def test_the_guide_sets_clue_digits_at_all(self, profile):
        digits = [
            face for page in drawn(profile) for face in page.faces if face.kind == CLUE_DIGIT
        ]

        assert len(digits) >= len(WORKED_EXAMPLE_STEPS) * len(WORKED_EXAMPLE_CLUE)

    def test_every_clue_digit_holds_the_floor(self, profile):
        under = [
            face.describe()
            for page in drawn(profile)
            for face in page.faces
            if face.kind == CLUE_DIGIT and face.size_pt < FLOOR_PT
        ]

        assert under == []

    def test_a_clue_digit_is_not_marked_exempt_and_nothing_here_can_mark_it(self):
        """Structurally: neither exempt function is reachable from this module."""
        source = Path(guide_vector.__file__).read_text(encoding="utf-8")

        assert EXEMPT_KINDS == frozenset()
        assert CLUE_DIGIT not in EXEMPT_KINDS
        for exempt in ("_write_clues", "_draw_clues"):
            assert f"{exempt}(" not in source, exempt

    def test_each_clue_digit_size_really_reaches_the_file(self, profile):
        """The claim is traced to the stream, not left standing on the record.

        Every size the writer says it set a clue digit at has to appear as a
        ``Tf`` operand in the written stream, and clear the floor there. A
        record that named a size the file does not carry would pass the two
        tests above and fail this one.
        """
        for page in drawn(profile):
            in_stream = set(pdf_vector.type_sizes("\n".join(page.stream.operators)))
            digits = {
                face.size_pt for face in page.faces if face.kind == CLUE_DIGIT
            }

            assert digits, page.page_number
            assert digits <= in_stream, sorted(digits - in_stream)
            assert min(digits) >= FLOOR_PT

    @needs_poppler
    def test_an_engine_that_did_not_write_the_file_reads_the_digits_back(self, tmp_path):
        """poppler extracts the worked example's clue, once per step.

        A text extraction rather than an ink measurement (ADR-0042/R6): it
        exercises the ``/Widths``, the ``/Encoding`` and the ``Tj`` operand
        together, which is the only check that the digits a reader can select
        are the ones the writer showed.
        """
        clue = " ".join(str(run) for run in WORKED_EXAMPLE_CLUE)
        text = pdf_vector.extracted_text(written("book1"), out_dir=tmp_path)

        assert text.count(clue) >= len(WORKED_EXAMPLE_STEPS), text


# --------------------------------------------------------------------------
# AC-3, as the page really stands — see this card's Worktree notes
# --------------------------------------------------------------------------


class TestGuidePage_DifficultyLegendCarriesNoRoundShapeToday:
    """AC-3's subject does not exist on this page, and that is measured here.

    **CARD-296's brief calls the difficulty legend's dots "the card's one
    genuinely new primitive". The legend has had no dots since CARD-221 fix
    1.** The owner's decision of 2026-10-14 stopped printing the three
    sentences (``GUIDE_DIFFICULTY_LABELS``), the ruled box that held them went
    with them, and what is left is three tier names in a row —
    ``book_pdf_generator._draw_difficulty_legend``, whose only drawing call is
    a ``draw.text``.

    The round mark the brief means is ``_draw_difficulty_dots``, which has
    **no production caller at all** today: CARD-207 (the puzzle page's band),
    **CARD-229** (the guide's key strip), CARD-231 and CARD-233 are the cards
    that will call it. CARD-229 is queued and gated, and CARD-296 G-1 forbids
    drawing its design here — *"this card ports today's design to the new
    medium, unchanged"*.

    So AC-3 is not assertable and is not asserted. What is asserted is the
    tripwire: this page draws no round shape today, and the day it does, it
    must come through ``ContentStream.round_mark``. That keeps
    ``TestVectorVocabulary_TheRoundMarkRouteTheOldGuardCannotSee``'s own alarm
    (CARD-294) intact rather than defusing it from this side.

    "No round shape", and the three routes that sentence has to cover
    ---------------------------------------------------------------------

    **This class used to say "PDF has no circle operator, so no ``c`` is
    exactly no round shape". That is false, and review cycle 1 measured it
    false**: ``ContentStream`` also carries
    :meth:`~nonogram.admin.book_vector.ContentStream.begin_path`,
    ``line_to``, ``close_path`` and ``paint`` — an arbitrary polygon builder
    that emits only ``m``, ``l``, ``h`` and a paint operator. A 32-gon filled
    disc was planted beside each tier name in ``draw_legend`` and **248 tests
    passed**, through the curve assertion, through ``round_mark(``, and through
    CARD-294's own alarm. A polyline disc is also the *cheaper* implementation
    of a difficulty dot than four Béziers, so it is the route CARD-229 is most
    likely to take.

    The route is closed here rather than carried as a limit, because the
    mechanism already exists in this tree one medium over
    (``tests/test_book_difficulty_dots.py``'s ``MAX_FLAT_VERTICES`` bounds
    ``draw.polygon``'s vertices for exactly this reason) and because the claim
    this class exists to make is the one AC-3 was declined on. A round shape
    reaches a content stream by one of three routes, and each has its own
    assertion below or its own named owner:

    1. **a curve** — the ``c`` operator, the only non-straight path segment
       PDF has: :meth:`test_no_guide_page_emits_a_curve_operator`;
    2. **a many-point polyline** — ``m`` plus a fan of ``l``, closed and
       filled: :meth:`test_no_guide_page_builds_a_round_shape_out_of_straight_segments`;
    3. **a round glyph** — ``●`` or a bullet inside a ``(…) Tj``, which is
       not a shape operator at all. Guarded package-wide and not here, by
       ``tests/test_book_difficulty_dots.py``'s dingbat rule
       (``ROUND_DINGBATS``), whose walk reads every string literal in
       ``src/nonogram/**`` and so covers this module the moment it lands.

    A path of at most :data:`MAX_PATH_POINTS` straight points is a triangle or
    a quadrilateral, and ``re`` is axis-aligned, so with 1 and 2 shut and 3
    held elsewhere there is no operator left in this vocabulary that inks a
    round shape. **The named limit**: the bound is per page kind, asserted over
    the pages *this* module writes. The guide is the only vector page kind in
    the tree today; CARD-298 owns ADR-0042/R1's derived check over every page
    kind and is where this becomes one check rather than one per card, and
    :func:`tests.helpers.pdf_vector.subpath_vertices` is in the shared reader
    so CARD-295 and CARD-297 inherit the count rather than rewriting it.
    """

    #: The most points a path on this page may be built from. The page's
    #: longest path is the pipeline's **arrow head** — ``m`` plus two ``l``,
    #: three points — asserted below so the bound's slack is a measurement and
    #: not a guess; four leaves room for a quadrilateral without leaving room
    #: for a circle.
    #:
    #: The same figure and the same reasoning as
    #: ``tests/test_book_difficulty_dots.py``'s ``MAX_FLAT_VERTICES``, written
    #: out here rather than imported: that bound counts the elements of a
    #: Python vertex display handed to Pillow, this one counts path operators
    #: in a written stream, and the two instruments have no code in common.
    MAX_PATH_POINTS = 4

    #: The pipeline's arrow head, in points — the page's longest path, and the
    #: reason :attr:`MAX_PATH_POINTS` is 4 and not 2.
    ARROW_HEAD_POINTS = 3

    def test_the_legend_sets_the_three_tier_names_and_nothing_else(self):
        names = [
            face.text
            for page in drawn("book1")
            for face in page.faces
            if face.kind == LEGEND_NAME
        ]

        assert names == [label.name for label in GUIDE_DIFFICULTY_LABELS]

    def test_no_guide_page_emits_a_curve_operator(self, profile):
        """Derived from the stream: no ``c`` is no **Bézier**, route 1 of three.

        PDF has no circle, ellipse or arc operator in a content stream
        (ADR-0042, CARD-294), so a *curved* outline is built out of ``c`` and
        nothing else — which makes this assertion exactly "this page draws no
        curve", and **not** "this page draws no round shape". The second
        statement needs the vertex bound beside this test as well; see the
        class docstring, which used to assert the equivalence and was measured
        false. Nothing is classified by eye either way.
        """
        curves = {
            page.page_number: pdf_vector.operator_tally(
                "\n".join(page.stream.operators)
            )["c"]
            for page in drawn(profile)
        }

        assert set(curves.values()) == {0}, curves

    def test_no_guide_page_builds_a_round_shape_out_of_straight_segments(self, profile):
        """Route 2: the polyline disc — ``begin_path`` plus a fan of ``line_to``.

        The route cycle 1 drove a 32-gon through with every other alarm green.
        Every subpath the page writes is counted off the stream and held to
        :attr:`MAX_PATH_POINTS`; the longest one it really writes is the
        pipeline's three-point arrow head, which is asserted too, so the bound
        cannot pass by the page having stopped drawing paths.
        """
        for page in drawn(profile):
            points = pdf_vector.subpath_vertices("\n".join(page.stream.operators))

            assert len(points) > 20, (page.page_number, len(points))
            assert max(points) <= self.MAX_PATH_POINTS, {
                "page": page.page_number,
                "longest path": max(points),
                "bound": self.MAX_PATH_POINTS,
            }

    def test_the_longest_path_the_page_writes_is_the_arrow_head(self):
        """What makes the bound above a measurement rather than a round number.

        ``book1`` draws the pipeline, whose arrow head is the page's one path
        longer than a segment. If this becomes 2 the diagram has gone; if it
        becomes 5 the bound has one point of slack nobody intended.
        """
        longest = max(
            max(pdf_vector.subpath_vertices("\n".join(page.stream.operators)))
            for page in drawn("book1")
        )

        assert longest == self.ARROW_HEAD_POINTS, longest

    def test_the_writer_never_reaches_the_round_mark_primitive(self):
        source = Path(guide_vector.__file__).read_text(encoding="utf-8")

        assert "round_mark(" not in source


# --------------------------------------------------------------------------
# EC(ADR-0042/R3) — the writer derives no geometry, in any book profile
# --------------------------------------------------------------------------


class TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims:
    """EC(ADR-0042/R3) — every width, tone and type size is traceable.

    The rule is *"every coordinate, width and tone it emits comes from
    COMP-007's Layout"*, and **two of those three are what this test reads**:
    the ``w`` stroke widths, the ``g``/``G`` tones and the ``Tf`` type sizes.
    Each emitted operand must be a member of a set this test builds **from
    ``compute_layout`` and from the page's own point constants**, with no help
    from the module under test — so an invented width or an invented size is a
    failure rather than a number nobody can place.

    **What it does not read: a coordinate** (review cycle 1, F-6). A derived
    coordinate shows up in an ``m``/``l``/``re``/``Td`` operand, and this test
    reads none of them, so the sentence above is a statement about widths,
    tones and type sizes and not about R3's whole operand surface. Coordinates
    are held from three other directions and deliberately not re-derived here:
    :class:`TestGuidePage_EveryDiagramStaysInsideItsOwnBox` for every line
    diagram's ink, ``guide_page``'s own ``fits_width`` for the blocks, and the
    owner's render comparison of the vector page against the raster page it
    ports (``~/Documents/nonogram-reviews/CARD-296/``). A derived-coordinate
    control that stands on its own is CARD-298's, with the rest of R1's
    per-page-kind checking.

    The tones are read through :func:`tests.helpers.pdf_vector.tones`, which
    sees the **inline** tone a text object carries as well as the standalone
    tone a path sets. A line-anchored regex here saw only the second, and the
    whole page could be set in 50 % grey with this test green (cycle 1, F-3).

    Default-DENY (ADR-0039/R2): the assertion is "the emitted set is a subset
    of the derived set", and an operand the derived set cannot account for
    reds the test. No ``hypothesis`` (it is not in ADR-0006/R1's baseline):
    the corpus is built by hand with ``random.Random`` and its size is
    asserted inside the test so it cannot silently shrink.

    **Named ``TestPropertyTest_...`` and not ``PropertyTest_...``.** This
    repository configures no ``python_classes``, so pytest's default ``Test*``
    applies and a ``PropertyTest_``-prefixed class collects ZERO tests with no
    skip and no error — CARD-294's review cycle 1 critical finding, now
    guarded by ``tests/test_collected_names.py``. The card's AC spells the
    name without the prefix; the prefix is what makes it run.
    """

    #: How many trims the corpus holds. Asserted inside the test.
    CORPUS = 24

    #: The seed, so the corpus is the same one on every host.
    SEED = 296

    #: Every ``(clue, length)`` pair the guide lays a line diagram out for,
    #: read off ``book_pdf_generator``'s own constants — which is data, not
    #: the function under test.
    @classmethod
    def line_pairs(cls) -> List[Tuple[Tuple[int, ...], int]]:
        pairs = [
            (GUIDE_BASIC_RULE_CLUE, GUIDE_BASIC_RULE_LENGTH),
            (WORKED_EXAMPLE_CLUE, WORKED_EXAMPLE_LENGTH),
        ]
        for entry in (*GUIDE_TECHNIQUES_1, *GUIDE_TECHNIQUES_2):
            pairs.append((entry.clue, entry.length))
        return pairs

    @classmethod
    def allowed(cls, spec, dpi: int) -> Tuple[frozenset, frozenset]:
        """``(stroke widths, type sizes)`` in points, derived independently.

        Every number comes from ``compute_layout`` on ``spec`` — the same door
        ADR-0036/R2 makes the only one — or from the page's own point
        constants. The title's fitted sizes are the whole ladder from
        ``GUIDE_TITLE_PT`` down to ``GUIDE_BODY_PT`` in the writer's declared
        step, because which rung a trim lands on is the trim's business.
        """
        to_points = 72.0 / dpi
        widths: set = set()
        sizes: set = {GUIDE_BODY_PT, FOLIO_PT}
        probe = compute_layout(((1,),), ((1,),), spec)
        widths.add(max(probe.thin_rule, 1) * to_points)
        layouts = [compute_layout(((0,),), ((0,),), spec)]
        for clue, length in cls.line_pairs():
            layouts.append(compute_layout((clue,), ((0,),) * length, spec))
        for layout in layouts:
            for line in (*layout.vertical_lines, *layout.horizontal_lines):
                widths.add(line.width * to_points)
            if layout.frame is not None:
                widths.add(layout.frame.width * to_points)
            widths.add(layout.thin_rule * to_points)
            sizes.add(layout.clue_font_size * to_points)
        rung = GUIDE_TITLE_PT
        while rung > GUIDE_BODY_PT:
            sizes.add(rung)
            rung = max(GUIDE_BODY_PT, rung - guide_vector._TITLE_FIT_STEP_PT)
        sizes.add(GUIDE_BODY_PT)
        return frozenset(round(value, 3) for value in widths), frozenset(
            round(value, 3) for value in sizes
        )

    def _corpus(self) -> List[Book]:
        rng = random.Random(self.SEED)
        books: List[Book] = []
        for index in range(self.CORPUS):
            width = round(rng.uniform(MIN_TRIM_CM, 21.0), 2)
            height = round(rng.uniform(max(width, 12.0), 27.0), 2)
            books.append(
                Book(
                    book_id=f"card-296-trim-{index}",
                    metadata=BookMetadata(
                        title="Winter Pictures",
                        description="A trim in CARD-296's corpus.",
                        theme="generic",
                        target_audience="adults",
                        size="",
                        page_count=0,
                    ),
                    trim_width_cm=f"{width:.2f}",
                    trim_height_cm=f"{height:.2f}",
                    gutter_margin_cm=MIN_TRIM_GUTTER_CM,
                    outside_margin_cm=MIN_TRIM_OUTSIDE_CM,
                )
            )
        return books

    def test_no_stroke_width_tone_or_type_size_is_invented(self):
        checked = 0
        for book in self._corpus():
            generator = BookPDFGenerator(book)
            for page in guide_pages(generator.page_spec, generator.dpi, **COUNTS):
                stream = "\n".join(page.stream.operators)
                widths, sizes = self.allowed(
                    generator.page_spec(page.page_number), generator.dpi
                )

                emitted = {round(value, 3) for value in pdf_vector.stroke_widths(stream)}
                assert emitted <= widths, {
                    "trim": (book.trim_width_cm, book.trim_height_cm),
                    "page": page.page_number,
                    "unaccounted widths": sorted(emitted - widths),
                }

                drawn_sizes = {
                    round(value, 3) for value in pdf_vector.type_sizes(stream)
                }
                assert drawn_sizes <= sizes, {
                    "trim": (book.trim_width_cm, book.trim_height_cm),
                    "page": page.page_number,
                    "unaccounted sizes": sorted(drawn_sizes - sizes),
                }

                inked = pdf_vector.tones(stream)
                assert {level for level, _operator in inked} <= {_BLACK_TONE}, {
                    "trim": (book.trim_width_cm, book.trim_height_cm),
                    "page": page.page_number,
                    "tones": sorted({level for level, _op in inked}),
                }
                # Non-vacuity, and the assertion that would have caught F-3:
                # ``ContentStream.text`` emits its fill tone inline, one per
                # text object, so the tones read here cannot be fewer than the
                # ``Tf`` operands. A reader blind to the inline spelling fails
                # this line instead of reading the path tones and stopping.
                assert len(inked) >= len(pdf_vector.type_sizes(stream)) > 0, (
                    page.page_number,
                    len(inked),
                    len(pdf_vector.type_sizes(stream)),
                )
                checked += 1

        assert checked == self.CORPUS * len(GUIDE_PAGE_NUMBERS) == 48

    def test_every_face_in_the_corpus_holds_the_ten_point_floor(self):
        """EC(CON-020) over 24 trims, not over the two profiles AC-2 names.

        The card scopes the floor to Book 1 and the minimum trim, and this
        class already builds a 24-trim corpus two classes down, so the floor
        was one loop away from covering it (review cycle 1, F-7). What makes it
        worth the loop is the measurement: **the smallest face across all 24
        trims is exactly 10.0 pt** — the folio, ``FOLIO_PT`` — so the margin
        above CON-020's floor is zero, and the next change to this page's type
        breaks the constraint on some trim in this sweep. A standing control
        says so where a one-off reading in a review does not.

        Read off the ``Tf`` operands, like AC-2's own test: the operand a
        reader's viewer obeys.
        """
        checked = 0
        smallest = []
        for book in self._corpus():
            generator = BookPDFGenerator(book)
            for page in guide_pages(generator.page_spec, generator.dpi, **COUNTS):
                sizes = pdf_vector.type_sizes("\n".join(page.stream.operators))

                assert sizes, (book.trim_width_cm, page.page_number)
                assert min(sizes) >= FLOOR_PT, {
                    "trim": (book.trim_width_cm, book.trim_height_cm),
                    "page": page.page_number,
                    "faces under the floor": sorted(
                        size for size in sizes if size < FLOOR_PT
                    ),
                }
                smallest.append(min(sizes))
                checked += 1

        assert checked == self.CORPUS * len(GUIDE_PAGE_NUMBERS)
        # And the zero margin, asserted rather than left in a comment: the
        # folio is the smallest face this page sets and it sits **on** the
        # floor. If this stops being true the sentence above is stale.
        assert min(smallest) == FOLIO_PT == FLOOR_PT, min(smallest)

    def test_the_corpus_really_holds_distinct_trims(self):
        """The minimum this property rests on: the sheets are not all one sheet.

        A corpus of 24 identical trims would pass the assertion above while
        measuring one page twice. The trims have to differ, and so must the
        geometry they produce — which is the point of sweeping them.
        """
        trims = {(book.trim_width_cm, book.trim_height_cm) for book in self._corpus()}

        assert len(trims) == self.CORPUS

        # The sheets really differ, and so does what the page does with them:
        # a small trim strips down to a more aggressive fallback form than a
        # large one. Both are asserted, because a corpus of 24 sheets that all
        # produced the same page would measure one page twenty-four times.
        #
        # NOT asserted on the clue type size: the line diagram's cell is
        # capped by the profile's ``cell_cap_mm``, so a six-cell line lands on
        # the same 55 px on every trim in this corpus. Measured, and worth
        # recording rather than quietly choosing another number.
        sheets = set()
        forms = set()
        for book in self._corpus():
            generator = BookPDFGenerator(book)
            for page in guide_pages(generator.page_spec, generator.dpi, **COUNTS):
                sheets.add((page.stream.width_px, page.stream.height_px))
                forms.add(page.fallback_level)

        assert len(sheets) > 1, sheets
        assert len(forms) > 1, forms
