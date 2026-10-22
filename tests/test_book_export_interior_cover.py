"""CARD-135 — the interior PDF holds no cover; the cover is its own file (FR-043).

    AC-283 (INV-013)  TestBookExport_InteriorOpensWithABlankTitlePage
    AC-284 (INV-013)  TestBookExport_InteriorHoldsNoCoverPage
    AC-285            TestBookExport_CoverIsSeparateSinglePageFile
    AC-286 (INV-013)  TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover
    AC-289 (INV-013)  TestBookExport_EveryRouteSeparatesInteriorAndCover

CARD-206's own two checks live here as well, named by its own ACs:

    AC-2 (CARD-206)   TestBookExport_TitlePageCountedEverywhere
    AC-6 (CARD-206)   TestBookExport_EmptyBookUnchanged

**CARD-206 (2026-10-22): the interior opens with a blank title page.** AC-283
was reworded with INV-013 on 2026-10-17 — interior page 1 is the book's
title / copyright page, carrying no folio and no ink at all, and the guide
follows on pages 2 and 3. ``TestBookExport_InteriorStartsAtGuidePage`` asserted
the retired statement and is renamed to the registry's own planned name above.

The book of AC-283 is a Book 1 profile book (8.5 x 11 in trim) holding three
easy 20x20 puzzles, with a cover image uploaded through the Finalise screen —
the real upload, so the tests also cover the defect that the upload was
dropped before it reached any export. The PDFs are read back with Pillow's
own PDF parser (``tests/helpers/pdf_pages.py``), never by asking the
generator what it wrote.
"""

from __future__ import annotations

import re
from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from nonogram import clues
from nonogram.admin import image_manager as image_manager_module
import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages, same_page

#: The 8.5 x 11 in trim at 300 DPI (AC-285).
TRIM_PX = (2550, 3300)
BOOK_TITLE = "Winter Pictures"


def _interior_pages(puzzle_count, answer_pages, levels=1, toc_pages=1):
    """The interior's page count: guide, TOC, levels, puzzles, divider, the key.

    FR-043's make-up with every variable term named rather than left as
    literals. ``levels`` is how many divider pages the puzzle section opens —
    one per non-empty level (CARD-128), and every book in this module is a
    book of easy puzzles, so one. ``puzzle_count`` is also the puzzle-**page** count for every book
    in this module: its puzzles are 20x20s, which never pair two-up here
    (FR-040). That premise is not assumed — it is asserted off a written
    interior by ``TestBookFinalise_PageCountIsTheExportsPagePlan``'s
    ``test_a_puzzle_of_this_module_never_shares_a_page_with_the_next``, so a
    pairing rule or profile that made it false is caught by name rather than
    as a page-count failure with no stated cause.
    ``answer_pages`` is how many pages the answer section takes (CARD-198:
    one full solved page per puzzle, no packing) — named at the call site
    for what it is now, not derived from a packing walk. A book with no
    puzzles has no divider, no TOC and no answer section at all.

    The title page's own term is **1** (CARD-206: the blank title /
    copyright page reserved as interior page 1) and the guide's own term is
    **2** (CARD-201's 2-page "how to solve" tutorial,
    up from 1 before that card) in both branches — both written out here as
    literals, like every other term, so this helper stays a second,
    independent statement of FR-043's make-up rather than a derivation from
    the constants the generator counts with. ``toc_pages`` (CARD-200)
    defaults to **1**: every book this module writes is a Book 1 profile
    (8.5 x 11 in) book of 1, 3 or 7 puzzles, and a TOC page on that trim
    holds far more than 7 rows (measured against
    ``book_pdf_generator.interior_page_count``'s own bare-count figures,
    which agree at this module's own puzzle counts) — a second, independent
    figure stated for this module's own small books rather than imported
    from the function under test, the same discipline every other term here
    already follows.
    """
    if puzzle_count == 0:
        return 1 + 2
    return 1 + 2 + toc_pages + levels + puzzle_count + 1 + answer_pages


#: This module's standard book: three easy 20x20s, one answer page each.
STANDARD_BOOK_PAGES = _interior_pages(3, 3)


def _rectangle(width, height, left, top, right, bottom):
    """A filled rectangle — uniquely solvable, so the store accepts it."""
    return [
        [left <= x < right and top <= y < bottom for x in range(width)]
        for y in range(height)
    ]


def _cover_art() -> Image.Image:
    """A cover no interior page could be mistaken for: dark, with a sun."""
    art = Image.new("RGB", (1200, 1800), (20, 30, 90))
    ImageDraw.Draw(art).ellipse((300, 500, 900, 1100), fill=(250, 210, 40))
    return art


def _png(image: Image.Image) -> BytesIO:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


@pytest.fixture
def admin_app(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    # A fresh in-memory book store, restored afterwards: the module singleton
    # would otherwise carry this test's books (and their puzzle ids) into
    # every later test that builds an in-memory app.
    monkeypatch.setattr(
        book_manager_module, "_book_manager", book_manager_module.BookManager(session_factory=None)
    )
    app = create_app()
    app.config["TESTING"] = True
    app.config["BOOK_COVER_DIR"] = str(tmp_path / "covers")
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


def _make_book(app, puzzle_count=3):
    """A Book 1 profile book holding ``puzzle_count`` easy 20x20 puzzles."""
    book_id = app.book_manager.create_book(
        title=BOOK_TITLE,
        description="Twenty winter pictures.",
        theme="generic",
        target_audience="adults",
        size="21.59×27.94",
    )
    ids = []
    for i in range(puzzle_count):
        grid = _rectangle(20, 20, i, i, 8 + 2 * i, 10 + i)
        found = clues.compute_clues(grid)
        ids.append(
            app.puzzle_review_service.add_puzzle(
                grid=grid,
                clues_rows=[list(c) for c in found.rows],
                clues_cols=[list(c) for c in found.columns],
                width=20,
                height=20,
                theme="winter",
                difficulty_score=10,
                difficulty_tier="easy",
                quality_score=50,
                recognizability="medium",
                strategies_used=[],
            )
        )
    app.book_manager.add_puzzles_to_book(book_id, ids)
    return book_id


def _upload_cover(client, book_id, art):
    response = client.post(
        f"/book/{book_id}/finalize",
        data={"cover": (_png(art), "cover.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200


def _download(client, route, book_id, part):
    """One part of the export through ``route``; the PDF bytes it returned."""
    if route == "finalise":
        response = client.post(
            f"/book/{book_id}/finalize",
            data={"action": "download_pdf", "part": part},
        )
    else:
        response = client.post(f"/book/{book_id}/{route}?part={part}")
    assert response.status_code == 200, (route, part, response.status_code)
    assert response.mimetype == "application/pdf"
    assert f"_{part}.pdf" in response.headers["Content-Disposition"]
    return response.get_data()


def _guide_page(puzzle_count, easy):
    """The guide page this book's **page 2** must hold — three easy puzzles.

    ``create_guide_page``'s own default position is the guide's first page,
    which since CARD-206 is interior page 2 (a verso), so this needs no
    position of its own.
    """
    return BookPDFGenerator().create_guide_page(puzzle_count, easy, 0, 0)


def _ink_pixels(page):
    """How many pixels of ``page`` are not pure white.

    CARD-206's AC-283 is "no ink of any kind", so it is measured as ink and
    not as "the page is not the guide": a folio, a rule or a one-word title
    would each be a handful of dark pixels on an otherwise white sheet, and
    a page comparison against a blank image would report them as "different"
    without saying that the difference *is* ink.
    """
    import numpy as np

    return int((np.asarray(page.convert("L")) < 255).sum())


def _generated_title_cover():
    return BookPDFGenerator().create_cover_page(BOOK_TITLE)


@pytest.fixture
def covered_book(admin_app):
    """AC-283's book: cover uploaded on Finalise; (client, book_id)."""
    client = admin_app.test_client()
    book_id = _make_book(admin_app)
    _upload_cover(client, book_id, _cover_art())
    return client, book_id


class TestBookExport_InteriorOpensWithABlankTitlePage:
    """AC-283 (CARD-206's AC-1) — page 1 is blank, page 2 is the guide's first.

    Two claims, measured two different ways, because neither implies the
    other: page 1 holds **no ink at all** (:func:`_ink_pixels`, a count over
    the page's own pixels) and page 2 **is** the guide's first page (a page
    comparison against ``create_guide_page``). A page that was blank but in
    the wrong place would pass the first alone; a guide page on page 2 with
    a folio printed on page 1 would pass the second alone.
    """

    def test_page_one_carries_no_ink_of_any_kind(self, covered_book):
        client, book_id = covered_book
        interior = pdf_pages(_download(client, "finalise", book_id, "interior"))

        assert interior[0].size == TRIM_PX
        assert _ink_pixels(interior[0]) == 0, (
            "interior page 1 is the blank title page — no folio, no title, "
            "no rule, no ink of any kind (AC-283)"
        )

    def test_the_ink_count_would_have_caught_a_folio(self, covered_book):
        """The negative has teeth: the measurement does see a page's marks.

        The control is the **divider** page, which is the least-inked page
        the generator draws that is not the title page — one centred word and
        a folio. If :func:`_ink_pixels` could not see that, it could not see
        a folio on the title page either.
        """
        divider = BookPDFGenerator().create_divider_page(1, "SOLUTIONS")

        assert _ink_pixels(divider) > 0

    def test_the_interiors_second_page_is_the_guides_first_page(self, covered_book):
        client, book_id = covered_book
        interior = pdf_pages(_download(client, "finalise", book_id, "interior"))

        assert same_page(interior[1], _guide_page(3, 3))

    def test_the_interior_runs_title_guide_puzzles_divider_answers(self, covered_book):
        """1 title + 2 guide + TOC + the "Easy" divider + 3 puzzles +
        SOLUTIONS + 3 answers.

        The answer section is three pages, one per puzzle (CARD-198) — FR-042
        packed it to one page for a while (CARD-134), before this card
        unpacked it again. What this AC is about is the *order* of the
        sections and the cover's absence from them; CARD-206 adds one page at
        the front and moves nothing else.
        """
        client, book_id = covered_book
        data = _download(client, "finalise", book_id, "interior")

        assert pdf_page_count(data) == STANDARD_BOOK_PAGES

    def test_the_generator_reports_the_interiors_own_page_count(self):
        grid = _rectangle(20, 20, 0, 0, 5, 5)
        found = clues.compute_clues(grid)
        puzzle = {
            "grid": grid,
            "clues_rows": found.rows,
            "clues_cols": found.columns,
            "width": 20,
            "height": 20,
            "difficulty_tier": "easy",
        }
        export = BookPDFGenerator().export_book(
            [puzzle], BOOK_TITLE, cover_image=_cover_art()
        )

        assert export.interior_page_count == pdf_page_count(export.interior.getvalue())
        # The blank title page (CARD-206), the 2-page guide (CARD-201), the
        # 1-page TOC (CARD-200), the "Easy" divider, the puzzle, SOLUTIONS,
        # its answer.
        assert export.interior_page_count == 8


class TestBookExport_InteriorHoldsNoCoverPage:
    """AC-284 — no interior page holds the cover image or a title cover."""

    def test_no_interior_page_is_the_uploaded_cover_or_a_title_cover(self, covered_book):
        client, book_id = covered_book
        interior = pdf_pages(_download(client, "finalise", book_id, "interior"))
        uploaded = _cover_art().resize(TRIM_PX)
        title_cover = _generated_title_cover()

        for number, page in enumerate(interior, start=1):
            assert not same_page(page, uploaded), f"interior page {number} is the cover"
            assert not same_page(page, title_cover), f"interior page {number} is a title cover"

    def test_page_one_is_the_blank_title_page_and_not_the_cover(self, covered_book):
        """CARD-206's AC-5, on the page the cover would have taken.

        The book has an uploaded cover, so the one page an interior could
        plausibly have grown a cover on is its new page 1. It is blank
        instead, and the cover is still its own one-page file.
        """
        client, book_id = covered_book
        interior = pdf_pages(_download(client, "finalise", book_id, "interior"))
        cover = pdf_pages(_download(client, "finalise", book_id, "cover"))

        assert _ink_pixels(interior[0]) == 0
        assert not same_page(interior[0], _cover_art().resize(TRIM_PX))
        assert len(cover) == 1 and cover[0].size == TRIM_PX
        assert same_page(cover[0], _cover_art().resize(TRIM_PX))

    def test_the_comparison_would_have_caught_the_old_file(self):
        """The negative has teeth: a cover page IS recognised as the cover."""
        cover = BookPDFGenerator().create_cover_page(BOOK_TITLE, _cover_art())
        buffer = BytesIO()
        cover.save(buffer, format="PDF", dpi=(300, 300))
        (page,) = pdf_pages(buffer.getvalue())

        assert same_page(page, _cover_art().resize(TRIM_PX))


class TestBookExport_CoverIsSeparateSinglePageFile:
    """AC-285 — a 1-page 2550 x 3300 px cover file holding the uploaded image."""

    def test_the_cover_file_is_one_trim_size_page_of_the_uploaded_image(self, covered_book):
        client, book_id = covered_book
        pages = pdf_pages(_download(client, "finalise", book_id, "cover"))

        assert len(pages) == 1
        assert pages[0].size == TRIM_PX
        assert same_page(pages[0], _cover_art().resize(TRIM_PX))
        assert not same_page(pages[0], _generated_title_cover())

    def test_the_cover_page_is_declared_at_eight_and_a_half_by_eleven_inches(self, covered_book):
        from PIL import PdfParser

        client, book_id = covered_book
        parser = PdfParser.PdfParser(buf=_download(client, "finalise", book_id, "cover"))
        try:
            (ref,) = parser.pages
            media_box = parser.read_indirect(ref)[b"MediaBox"]
        finally:
            parser.close()

        assert [float(v) for v in media_box] == [0.0, 0.0, 8.5 * 72, 11 * 72]

    def test_the_uploaded_cover_is_used_whatever_the_title_holds(self, covered_book):
        """CARD-234 AC-6 — the uploaded path never looks at the title.

        That card gave the **generated** title cover a packaged face and a
        refusal for a title the face cannot letter
        (``tests/test_book_cover.py``). This is the guard that the refusal
        cannot reach a book whose cover is an uploaded image: the title is
        returned past, not measured, so a book titled in a script the
        shipped font has no glyphs for still downloads its own cover.
        """
        client, book_id = covered_book
        uploaded = pdf_pages(_download(client, "finalise", book_id, "cover"))
        generator = BookPDFGenerator()

        direct = generator.create_cover_page("\u4e2d\u6587", _cover_art())

        assert len(uploaded) == 1
        assert same_page(uploaded[0], _cover_art().resize(TRIM_PX))
        assert same_page(direct, _cover_art().resize(TRIM_PX))


class TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover:
    """AC-286 — with no upload the cover file holds the generated title cover."""

    @pytest.fixture
    def bare_book(self, admin_app):
        return admin_app.test_client(), _make_book(admin_app)

    def test_the_cover_file_holds_the_generated_title_cover(self, bare_book):
        client, book_id = bare_book
        pages = pdf_pages(_download(client, "finalise", book_id, "cover"))

        assert len(pages) == 1
        assert pages[0].size == TRIM_PX
        assert same_page(pages[0], _generated_title_cover())

    def test_the_interior_still_starts_at_the_blank_title_page(self, bare_book):
        client, book_id = bare_book
        interior = pdf_pages(_download(client, "finalise", book_id, "interior"))

        assert _ink_pixels(interior[0]) == 0
        assert same_page(interior[1], _guide_page(3, 3))
        assert not any(same_page(p, _generated_title_cover()) for p in interior)

    def test_a_removed_cover_falls_back_to_the_title_cover(self, admin_app):
        """Clearing the upload must reach the export, not only the screen."""
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        _upload_cover(client, book_id, _cover_art())
        client.post(f"/book/{book_id}/finalize", data={"action": "clear_cover"})

        (page,) = pdf_pages(_download(client, "finalise", book_id, "cover"))
        assert same_page(page, _generated_title_cover())
        body = client.get(f"/book/{book_id}/finalize").get_data(as_text=True)
        assert "Cover image uploaded" not in body


ROUTES = ("finalise", "download-pdf", "generate-pdf")


class TestBookExport_EveryRouteSeparatesInteriorAndCover:
    """AC-289 — all three export routes yield the same interior + cover pair."""

    @pytest.mark.parametrize("route", ROUTES)
    def test_each_route_yields_a_title_page_first_interior_and_a_cover_file(
        self, covered_book, route
    ):
        client, book_id = covered_book
        interior = pdf_pages(_download(client, route, book_id, "interior"))
        cover = pdf_pages(_download(client, route, book_id, "cover"))

        assert _ink_pixels(interior[0]) == 0
        assert same_page(interior[1], _guide_page(3, 3))
        assert len(interior) == STANDARD_BOOK_PAGES
        assert len(cover) == 1 and cover[0].size == TRIM_PX
        assert same_page(cover[0], _cover_art().resize(TRIM_PX))
        assert not any(same_page(p, cover[0]) for p in interior)

    def test_the_three_routes_export_the_same_pair(self, covered_book):
        client, book_id = covered_book
        exports = {
            route: (
                pdf_pages(_download(client, route, book_id, "interior")),
                pdf_pages(_download(client, route, book_id, "cover")),
            )
            for route in ROUTES
        }
        first_interior, first_cover = exports[ROUTES[0]]
        for route in ROUTES[1:]:
            interior, cover = exports[route]
            assert len(interior) == len(first_interior), route
            assert all(same_page(a, b) for a, b in zip(interior, first_interior)), route
            assert same_page(cover[0], first_cover[0]), route

    @pytest.mark.parametrize("route", ("download-pdf", "generate-pdf"))
    def test_a_route_with_no_part_downloads_the_interior(self, covered_book, route):
        client, book_id = covered_book
        response = client.post(f"/book/{book_id}/{route}")

        assert response.status_code == 200
        assert "_interior.pdf" in response.headers["Content-Disposition"]
        assert same_page(pdf_pages(response.get_data())[1], _guide_page(3, 3))

    @pytest.mark.parametrize("route", ("download-pdf", "generate-pdf"))
    def test_an_unknown_part_is_refused_not_guessed(self, covered_book, route):
        client, book_id = covered_book
        response = client.post(f"/book/{book_id}/{route}?part=wrap")

        assert response.status_code == 302


class TestBookFinalise_OffersBothDownloads:
    """The Finalise screen offers the interior and the cover as two buttons."""

    def test_the_screen_renders_an_interior_and_a_cover_download(self, admin_app):
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        body = client.get(f"/book/{book_id}/finalize").get_data(as_text=True)

        assert 'data-export-part="interior"' in body
        assert 'data-export-part="cover"' in body
        assert 'name="part" value="interior"' in body
        assert 'name="part" value="cover"' in body
        # The cover is no longer listed as a page of the book.
        assert "Cover page (" not in body
        # Since CARD-129 the figure is the interior's **own** page count, not
        # the un-paired bound the screen used to print with a "~": a
        # 3-puzzle book of easy 20x20s is 1 guide + 1 divider + 3 puzzle
        # pages + SOLUTIONS + 3 answer pages (CARD-198: one per puzzle).
        assert f'data-interior-page-count="{_interior_pages(3, 3)}"' in body
        assert 'data-interior-page-count-exact="true"' in body
        # The figure the owner reads, not the attribute beside it: the text of
        # the very <dd> that carries the count is the bare number, with no
        # "~" in front (CARD-153, F-004 — the old split-and-slice looked only
        # at the attribute's own value and could never fail), and the
        # sentence under the interior's contents does not say "About".
        pages = _interior_pages(3, 3)
        (shown,) = re.findall(
            r'<dd[^>]*\bdata-interior-page-count="\d+"[^>]*>(.*?)</dd>', body, re.S
        )
        assert shown.strip() == str(pages)
        assert f"About {pages} interior pages" not in body
        assert f"{pages} interior pages" in body


# --- CARD-135 review cycle 1 --------------------------------------------------


def _stored_cover(app, book_id):
    """The one cover file the upload stored for ``book_id``."""
    from pathlib import Path

    (path,) = Path(app.config["BOOK_COVER_DIR"]).glob(f"{book_id}_cover.png")
    return path


def _flashes(client):
    with client.session_transaction() as sess:
        return [message for _, message in sess.get("_flashes", [])]


class TestBookFinalise_LostCoverFileIsNotPassedOffAsUploaded:
    """F-001 — "cover uploaded" means the stored file exists, not a session flag.

    The stored cover lives in a temp dir the OS may purge while the signed
    session cookie outlives it. The screen must stop promising the owner's
    art, and a cover download must not quietly print the title cover.
    """

    @pytest.fixture
    def lost_cover(self, admin_app):
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        _upload_cover(client, book_id, _cover_art())
        _stored_cover(admin_app, book_id).unlink()
        return client, book_id

    def test_finalise_stops_claiming_the_cover_and_says_why(self, lost_cover):
        client, book_id = lost_cover
        body = client.get(f"/book/{book_id}/finalize").get_data(as_text=True)

        assert "Cover image uploaded" not in body
        assert "your cover image" not in body
        assert "a generated title cover" in body
        assert "no longer on disk" in body

    @pytest.mark.parametrize("route", ROUTES)
    def test_a_cover_download_is_refused_not_silently_swapped(self, lost_cover, route):
        client, book_id = lost_cover
        if route == "finalise":
            response = client.post(
                f"/book/{book_id}/finalize", data={"action": "download_pdf", "part": "cover"}
            )
        else:
            response = client.post(f"/book/{book_id}/{route}?part=cover")

        assert response.status_code == 302
        assert response.mimetype != "application/pdf"
        assert any("no longer on disk" in m for m in _flashes(client))

    def test_the_interior_is_still_downloadable(self, lost_cover):
        client, book_id = lost_cover
        interior = pdf_pages(_download(client, "finalise", book_id, "interior"))

        assert _ink_pixels(interior[0]) == 0
        assert same_page(interior[1], _guide_page(3, 3))

    def test_once_the_screen_has_said_so_the_cover_is_the_title_cover(self, lost_cover):
        """After Finalise has shown the loss, screen and export agree again."""
        client, book_id = lost_cover
        client.get(f"/book/{book_id}/finalize")

        (page,) = pdf_pages(_download(client, "finalise", book_id, "cover"))
        assert same_page(page, _generated_title_cover())


class TestBookFinalise_CoverPathOutsideTheCoverDirIsIgnored:
    """F-006 — a session path outside BOOK_COVER_DIR is never read or deleted."""

    @pytest.fixture
    def foreign_path(self, admin_app, tmp_path):
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        outside = tmp_path / "not_a_cover.png"
        _cover_art().save(outside, format="PNG")
        with client.session_transaction() as sess:
            sess[f"book_{book_id}_cover_path"] = str(outside)
            sess[f"book_{book_id}_cover_data"] = True
        return client, book_id, outside

    def test_clear_cover_leaves_the_outside_file_in_place(self, foreign_path):
        client, book_id, outside = foreign_path
        client.post(f"/book/{book_id}/finalize", data={"action": "clear_cover"})

        assert outside.is_file()

    def test_finalise_does_not_claim_it_and_leaves_it_in_place(self, foreign_path):
        client, book_id, outside = foreign_path
        body = client.get(f"/book/{book_id}/finalize").get_data(as_text=True)

        assert "Cover image uploaded" not in body
        assert outside.is_file()

    @pytest.mark.parametrize("route", ROUTES)
    def test_no_export_prints_the_outside_file(self, foreign_path, route):
        client, book_id, outside = foreign_path
        if route == "finalise":
            response = client.post(
                f"/book/{book_id}/finalize", data={"action": "download_pdf", "part": "cover"}
            )
        else:
            response = client.post(f"/book/{book_id}/{route}?part=cover")

        if response.status_code == 200:
            (page,) = pdf_pages(response.get_data())
            assert not same_page(page, _cover_art().resize(TRIM_PX))
        else:
            assert response.status_code == 302
        assert outside.is_file()


class TestBookCover_StoredFileLifecycle:
    """F-002 — the stored cover is upright and leaves with its book."""

    def test_a_phone_photo_is_stored_upright(self, admin_app):
        """EXIF orientation 6 (rotate 90 CW) is applied before re-encoding."""
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        sideways = Image.new("RGB", (1800, 1200), (20, 30, 90))  # stored landscape
        exif = Image.Exif()
        exif[0x0112] = 6  # Orientation: rotate 90 CW to display
        jpeg = BytesIO()
        sideways.save(jpeg, format="JPEG", exif=exif.tobytes())
        jpeg.seek(0)
        client.post(
            f"/book/{book_id}/finalize",
            data={"cover": (jpeg, "phone.jpg")},
            content_type="multipart/form-data",
        )

        with Image.open(_stored_cover(admin_app, book_id)) as stored:
            assert stored.size == (1200, 1800)  # portrait, as the phone showed it

    def test_deleting_the_book_removes_its_cover_file(self, admin_app):
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        _upload_cover(client, book_id, _cover_art())
        stored = _stored_cover(admin_app, book_id)

        client.post(f"/book/{book_id}/delete")

        assert admin_app.book_manager.get_book(book_id) is None
        assert not stored.exists()


class TestBookExport_RoutesRenderOnlyTheRequestedPart:
    """F-004 — a cover download renders no interior page, and vice versa."""

    @pytest.mark.parametrize("route", ROUTES)
    def test_a_cover_download_renders_no_interior(self, covered_book, route, monkeypatch):
        client, book_id = covered_book

        def no_interior(*args, **kwargs):
            raise AssertionError("the interior was rendered for a cover download")

        monkeypatch.setattr(BookPDFGenerator, "interior_pages", no_interior)
        (page,) = pdf_pages(_download(client, route, book_id, "cover"))

        assert same_page(page, _cover_art().resize(TRIM_PX))

    @pytest.mark.parametrize("route", ROUTES)
    def test_an_interior_download_renders_no_cover(self, covered_book, route, monkeypatch):
        client, book_id = covered_book

        def no_cover(*args, **kwargs):
            raise AssertionError("a cover was rendered for an interior download")

        monkeypatch.setattr(BookPDFGenerator, "create_cover_page", no_cover)
        interior = pdf_pages(_download(client, route, book_id, "interior"))

        assert _ink_pixels(interior[0]) == 0
        assert same_page(interior[1], _guide_page(3, 3))


class TestBookExport_GeneratePdfRecordsOnlyTheInterior:
    """F-007 — a cover-only download on generate-pdf records no book PDF."""

    def test_a_cover_download_leaves_pdf_url_unset(self, covered_book, admin_app):
        client, book_id = covered_book
        _download(client, "generate-pdf", book_id, "cover")

        assert admin_app.book_manager.get_book(book_id).metadata.pdf_url is None
        assert "PDF generated successfully!" not in _flashes(client)

    def test_an_interior_download_records_it(self, covered_book, admin_app):
        client, book_id = covered_book
        _download(client, "generate-pdf", book_id, "interior")

        assert admin_app.book_manager.get_book(book_id).metadata.pdf_url is not None


class TestBookFinalise_PageCountIsTheExportsPagePlan:
    """F-005 — the count Finalise shows is the export's own page plan.

    Cross-checked against the page tree of the PDF the export writes, not
    against the plan function's own arithmetic.

    **What FR-042/CARD-198 changed here.** ``interior_page_count`` takes how
    many pages the *answers* take as well as how many the puzzles take, and
    both default to one page each. Called with the puzzle count alone —
    which is how the Finalise screen calls it — it is therefore the
    un-paired plan: an **upper bound**, which is what that screen has
    always labelled it ("~") and what CARD-129 owns making exact (EC-034).
    Since CARD-198 the answer term is no longer a packing saving to widen
    the bound with — one answer page per puzzle is exact either way — so
    what still widens the one-argument call beyond the real file is only
    the divider term, CARD-128's "the most dividers a book of that many
    puzzles could open": a three-puzzle book of one level plans 11 and
    writes 9.

    So the two statements are asserted separately, and both against the
    written file: the plan given every term is the file's page count exactly,
    and the screen's figure is never less than it.
    """

    #: How many answer pages these books take: one per puzzle, unconditionally
    #: (CARD-198). Written out here rather than asked of the generator.
    @staticmethod
    def _answer_pages(puzzle_count):
        return puzzle_count

    @staticmethod
    def _interior_of(puzzle_count):
        """The written interior of a book of ``puzzle_count`` easy 20x20s."""
        grid = _rectangle(20, 20, 0, 0, 5, 5)
        found = clues.compute_clues(grid)
        puzzle = {
            "grid": grid,
            "clues_rows": found.rows,
            "clues_cols": found.columns,
            "width": 20,
            "height": 20,
            "difficulty_tier": "easy",
        }
        return BookPDFGenerator().export_interior([puzzle] * puzzle_count)

    @pytest.mark.parametrize("puzzle_count", (1, 2, 3, 7))
    def test_a_puzzle_of_this_module_never_shares_a_page_with_the_next(
        self, puzzle_count
    ):
        """:func:`_interior_pages`'s one unstated premise, taken off the file.

        Every count this module writes reads ``puzzle_count`` as the
        puzzle-**page** count too. That is true only while no two of these
        puzzles pair two-up (FR-040) — true today, because they are 20x20s,
        and silently false the day the profile or the pairing rule moves,
        which would take every page-count assertion in this module down with
        it without naming the reason.

        So it is measured, not assumed: the written interior is the blank
        title page (CARD-206) + the 2-page
        guide (CARD-201) + the 1-page TOC (CARD-200, every book in this
        module is far under one TOC page's own capacity) + the one level's
        divider + puzzle pages + SOLUTIONS + key, so what is left after the
        **six** fixed pages and the key's own term is the puzzle-page count,
        and it is the puzzle count. These books are one tier throughout, so
        a pairing walk that paired anything at all would be seen here — and
        so would a second divider.
        """
        written = pdf_page_count(self._interior_of(puzzle_count).getvalue())
        puzzle_pages = written - 6 - self._answer_pages(puzzle_count)

        assert puzzle_pages == puzzle_count

    @pytest.mark.parametrize("puzzle_count", (0, 1, 3, 7))
    def test_the_plan_matches_the_written_interior(self, puzzle_count):
        from nonogram.admin.book_pdf_generator import interior_page_count

        written = pdf_page_count(self._interior_of(puzzle_count).getvalue())
        answer_pages = self._answer_pages(puzzle_count)

        # The file, against this module's own arithmetic — independent of the
        # plan function entirely.
        assert written == _interior_pages(puzzle_count, answer_pages)
        # And the plan function, given the same terms, against the file. A
        # 20x20 never pairs here, so the puzzle-page term is the count, and
        # these books are one level, so the divider term is 1 — 0 for the
        # empty book, which has no puzzle section at all.
        assert (
            interior_page_count(
                puzzle_count, puzzle_count, answer_pages, min(1, puzzle_count)
            )
            == written
        )

    @pytest.mark.parametrize("puzzle_count", (0, 1, 3, 7))
    def test_the_plan_called_with_the_count_alone_bounds_the_file(self, puzzle_count):
        """The Finalise screen's call, and what it promises: never too few.

        A stated page count below the file's would send a book to KDP under a
        spine width that does not fit it, which is the direction that costs
        money; above it is the "~" the screen prints.
        """
        from nonogram.admin.book_pdf_generator import interior_page_count

        written = pdf_page_count(self._interior_of(puzzle_count).getvalue())

        assert interior_page_count(puzzle_count) >= written

    @staticmethod
    def _one_per_level_interior():
        """The written interior of three 20x20s, one on each of the levels.

        Every other book in this module is easy throughout, so its puzzle
        section opens a single divider. This one opens the most a three-puzzle
        book can (CARD-128) — one per non-empty level, ADR-0031's three — and
        its key takes a page per level, since each level's answers start a new
        answer page (FR-042, AC-290).
        """
        grid = _rectangle(20, 20, 0, 0, 5, 5)
        found = clues.compute_clues(grid)
        return BookPDFGenerator().export_interior(
            [
                {
                    "grid": grid,
                    "clues_rows": found.rows,
                    "clues_cols": found.columns,
                    "width": 20,
                    "height": 20,
                    "difficulty_tier": tier,
                }
                for tier in ("easy", "medium", "hard")
            ]
        )

    def test_the_bound_holds_where_a_book_opens_a_divider_per_level(self):
        """The one-argument bound at the boundary it is tight on (EC-034).

        The two assertions above run only on this module's easy books — one
        level, one divider page — so neither would see the plan's divider term
        understate a book that opens three. Three puzzles across three levels
        is where the bound and the file meet exactly: it is the first book a
        narrower divider term stops bounding, and CARD-129's KDP refusal reads
        this number next.
        """
        from nonogram.admin.book_pdf_generator import interior_page_count

        written = pdf_page_count(self._one_per_level_interior().getvalue())

        # This module's own arithmetic first: the title page, the guide, a
        # divider per level, a
        # page per puzzle, SOLUTIONS, and an answer page per level.
        assert written == _interior_pages(3, 3, levels=3)
        assert interior_page_count(3) >= written
        # And the bound is not merely satisfied here, it is met — this is the
        # worst case, so any slack left would be slack the bound does not have.
        assert interior_page_count(3) == written

    @pytest.mark.parametrize("puzzle_count", (1, 3))
    def test_finalise_shows_that_bound_on_the_downloaded_interior(
        self, admin_app, puzzle_count
    ):
        from nonogram.admin.book_pdf_generator import interior_page_count

        client = admin_app.test_client()
        book_id = _make_book(admin_app, puzzle_count)
        body = client.get(f"/book/{book_id}/finalize").get_data(as_text=True)
        pages = pdf_page_count(_download(client, "finalise", book_id, "interior"))

        # The figure on the screen, against this module's own arithmetic and
        # not against the function that produced it. Since CARD-129 it is the
        # **exact** count of the file the button beside it downloads (EC-034):
        # the puzzle-page term is the count (a 20x20 never pairs here), and
        # since CARD-198 the answer term is the count too — one page each.
        exact = _interior_pages(
            puzzle_count, self._answer_pages(puzzle_count), min(1, puzzle_count)
        )
        assert f'data-interior-page-count="{exact}"' in body
        assert f'data-unpaired-page-count="{exact}"' in body, (
            "nothing pairs in this module's books, so the two counts are equal"
        )
        assert exact == pages, "the screen's figure is the downloaded file's"
        # The one-argument bound the screen used to print is still a bound.
        assert interior_page_count(puzzle_count) >= pages
        assert pages == _interior_pages(puzzle_count, self._answer_pages(puzzle_count))


# --------------------------------------------------------------------------
# CARD-206 AC-2 — the title page is counted everywhere a page count is made
# --------------------------------------------------------------------------


class TestBookExport_TitlePageCountedEverywhere:
    """CARD-206 AC-2 — the exported interior is one page longer than before,
    and every figure that states a page count states that same number.

    Three figures, three callers, one number: the written PDF's own page
    count, ``book_pdf_generator.interior_page_count`` (what the Finalise
    screen shows and ``interior_stream`` checks its own walk against) and
    ``book_kdp.unpaired_interior_page_count`` (the sheet-free estimate KDP's
    gutter band is read at when a book's stored print specification cannot be
    laid out). The third matters most and is the easiest to miss: it is the
    only one of the three that is never compared against a file in
    production, so a title page counted in the generator and not there would
    print a gutter margin for a book one page shorter than the one written.

    **"Exactly one more than before this card" is asserted against a figure
    written out here**, not against a saved artefact: the pre-card make-up
    was guide + TOC + dividers + puzzle pages + SOLUTIONS + answer pages, and
    :func:`_interior_pages` states it with the title page's own term added as
    a separate ``1``, so the difference is readable in one line.
    """

    @staticmethod
    def _rows(puzzle_count, tier="easy"):
        """``puzzle_count`` easy 20x20 rows, as both callers take them.

        Carries ``grid``/``clues_rows``/``clues_cols``, which is what
        ``book_kdp.unpaired_interior_page_count`` measures an answer's extent
        from (``book_kdp._grid_extent``), as well as what the generator draws.
        """
        grid = _rectangle(20, 20, 0, 0, 5, 5)
        found = clues.compute_clues(grid)
        return [
            {
                "grid": grid,
                "clues_rows": [list(c) for c in found.rows],
                "clues_cols": [list(c) for c in found.columns],
                "width": 20,
                "height": 20,
                "difficulty_tier": tier,
            }
            for _ in range(puzzle_count)
        ]

    @pytest.mark.parametrize("puzzle_count", (1, 3, 7))
    def test_every_figure_reports_the_interior_with_its_title_page(
        self, puzzle_count
    ):
        from nonogram.admin.book_kdp import unpaired_interior_page_count
        from nonogram.admin.book_pdf_generator import interior_page_count

        rows = self._rows(puzzle_count)
        written = pdf_page_count(
            BookPDFGenerator().export_interior(list(rows)).getvalue()
        )

        # This module's own arithmetic, with the title page's term in it.
        assert written == _interior_pages(puzzle_count, puzzle_count)
        # **Exactly one more page than before this card.** The pre-card
        # make-up of one of this module's easy books was 2 guide + 1 TOC +
        # 1 divider + n puzzle pages + SOLUTIONS + n answer pages, i.e.
        # `5 + 2n` — written out here as the figure it was, so the +1 is one
        # readable term rather than a diff against a deleted helper.
        assert written == (5 + 2 * puzzle_count) + 1
        # The generator's own formula, given every term, and the sheet-free
        # KDP estimate: nothing pairs or packs in a book of 20x20s, so all
        # three figures are the same number rather than merely ordered.
        assert (
            interior_page_count(puzzle_count, puzzle_count, puzzle_count, 1, toc_pages=1)
            == written
        )
        assert unpaired_interior_page_count(rows) == written

    @pytest.mark.parametrize("title_pages", (2, 3))
    def test_each_position_is_counted_from_the_constant_not_a_literal(
        self, monkeypatch, title_pages
    ):
        """Reserve a second (and a third) front-matter page and *everything*
        moves with it — which is what "derived from the constant" means.

        This is the card's own most likely defect, caught behaviourally
        rather than by reading: a position written as a literal ``3`` would
        agree with ``TITLE_PAGE_COUNT == 1`` for ever and disagree the moment
        the constant changes. So the constant is changed, and the written
        interior is re-read: the front matter is ``title_pages`` blank pages,
        the guide's first page follows them (and is still the guide's *first*
        half, not its second — the half selection is counted from the same
        constant), the puzzle section's own opening page moves by the same
        amount, and all three page-count figures move with it too.

        Monkeypatching the module global reaches every one of those positions
        because each reads it when it is called. Two positions do not, and
        are named here as the measured bound: ``puzzle_pages``' and
        ``puzzle_section``'s **default** ``first_page`` arguments are bound
        at import time, so this test cannot see them. Production never relies
        on either — ``section_plan`` passes its own ``first_page`` — and
        their value is read by the AST check in
        ``TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage``
        instead.
        """
        import numpy as np

        from nonogram.admin import book_kdp
        from nonogram.admin import book_pdf_generator as bpg

        rows = self._rows(3)
        monkeypatch.setattr(bpg, "TITLE_PAGE_COUNT", title_pages)
        generator = bpg.BookPDFGenerator()
        pages = list(generator.interior_stream(list(rows)).pages)

        blank = [
            number
            for number, page in enumerate(pages, start=1)
            if np.asarray(page.convert("L")).min() == 255
        ]
        assert blank == list(range(1, title_pages + 1)), (
            "the reserved front-matter pages are the interior's first pages "
            "and nothing after them is blank"
        )
        assert same_page(
            pages[title_pages], generator.create_guide_page(3, 3, 0, 0, page_number=title_pages + 1)
        ), "the guide's first half follows the reserved pages"
        assert generator.section_plan(list(rows)).pages[0].page_number == (
            title_pages + 2 + 1 + 1
        ), "the puzzle section opens after the title pages, the guide and the TOC"
        expected = len(pages)
        assert expected == 12 - 1 + title_pages
        assert (
            bpg.interior_page_count(3, 3, 3, 1, toc_pages=1) == expected
        ), "interior_page_count still counts a literal, not the constant"
        assert (
            book_kdp.unpaired_interior_page_count(rows) == expected
        ), "the KDP estimate still counts a literal, not the constant"


# --------------------------------------------------------------------------
# CARD-206 AC-6 — a book with no drawable puzzle is unchanged
# --------------------------------------------------------------------------


class TestBookExport_EmptyBookUnchanged:
    """CARD-206 AC-6 — the blank title page never becomes a book's only page.

    What "unchanged" is, exactly, and what it is not. The empty book's
    interior gains the title page like every other book's — that is the
    amended INV-013, which says nothing about a book's membership — so its
    page count moves from 2 to 3. What this AC forbids is the *shape*
    changing: the blank page must not be the only page (the guide still
    prints), no table of contents, divider, SOLUTIONS divider or answer page
    may appear, and the route that refuses to export an empty book must
    still refuse it with the same message.
    """

    @staticmethod
    def _empty_interior():
        return BookPDFGenerator().export_interior([])

    def test_the_interior_is_the_title_page_and_the_guide_and_nothing_else(self):
        from nonogram.admin.book_pdf_generator import interior_page_count

        pages = pdf_pages(self._empty_interior().getvalue())

        assert len(pages) == _interior_pages(0, 0) == 3
        assert interior_page_count(0) == len(pages)
        assert _ink_pixels(pages[0]) == 0
        assert same_page(pages[1], BookPDFGenerator().create_guide_page(0, 0, 0, 0))
        assert same_page(
            pages[2], BookPDFGenerator().create_guide_page(0, 0, 0, 0, page_number=3)
        )

    def test_the_blank_page_is_not_the_only_page(self):
        """The one thing AC-6 names outright."""
        pages = pdf_pages(self._empty_interior().getvalue())
        inked = [number for number, page in enumerate(pages, start=1)
                 if _ink_pixels(page) > 0]

        assert len(pages) > 1
        assert inked, "an empty book's interior still prints the guide"

    def test_the_generate_pdf_route_still_refuses_an_empty_book(self, admin_app):
        client = admin_app.test_client()
        book_id = admin_app.book_manager.create_book(
            title=BOOK_TITLE,
            description="No puzzles at all.",
            theme="generic",
            target_audience="adults",
            size="21.59×27.94",
        )

        response = client.post(f"/book/{book_id}/generate-pdf?part=interior")

        assert response.status_code == 302
        assert response.mimetype != "application/pdf"
        assert any(
            "no puzzles" in message for message in _flashes(client)
        ), "the empty-book refusal is unchanged"


# --------------------------------------------------------------------------
# CARD-206 AC-2, the structural half — enumerated, not read
# --------------------------------------------------------------------------


class TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage:
    """Every expression in the generator that counts the guide also counts the
    title page, and no page offset in one of them is a literal.

    The card's own most likely defect is a literal where a derivation belongs,
    and reading 7,000 lines for one is how a wrong count gets reported. So the
    module is parsed and the sites are enumerated: for every load of
    ``GUIDE_PAGE_COUNT`` the **outermost enclosing expression** is taken (the
    whole ``1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc_page_count`` term,
    the whole ``range(...)`` call, the whole ``return`` arithmetic), and that
    expression must also load ``TITLE_PAGE_COUNT``.

    **The bare-literal shape, and why it needed a second enumeration**
    (review cycle 1, F-102). The walk above visits only the expressions that
    load ``GUIDE_PAGE_COUNT``, so a position written as a bare literal with
    no constant in it at all — a ``first_page = 4`` — satisfies it vacuously.
    Cycle 1 declared that shape "covered behaviourally by
    ``TestBookExport_TitlePageCountedEverywhere``'s monkeypatch case", and
    the reviewer refuted it: that case moves ``TITLE_PAGE_COUNT`` and re-reads
    the written interior, so it can only see a position that reaches a byte of
    output. ``interior_stream``'s own ``first_answer_page = 3 + len(section)``
    did not — it built a spec that was read for its *size* — and it had
    survived CARD-200's TOC and this card's title page unnoticed.

    So the bound is not declared any more; it is closed.
    :meth:`_page_positions` enumerates the module's page positions, derived
    rather than listed: the seed is the geometry door every position must
    reach (:meth:`BookPDFGenerator.page_spec`, ADR-0036/R2's "one door"), the
    vocabulary of position names is grown from it to a fixed point, and every
    binding occurrence of a vocabulary name is a site. A site may hold the
    integer constants ``0`` and ``1`` (the term that turns a count of
    front-matter pages into the 1-based position after them) and nothing
    else, so ``3 + len(section)`` is a failure and
    ``1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + …`` is not.

    **The four axes, and what this walk does on each** (ADR-0039/R2;
    CARD-262's declared semantics). An axis is one question the walk must
    answer about a node, and its answer is exactly one of **READ** (analysed,
    its literals reported), **REFUSED** (a ``refusals`` entry naming line and
    shape, which reds) or **SILENT**. There is no fourth state and no
    "assumed clean"; SILENT is forbidden except as a named ADR-0039/R3
    exemption carrying a control that can fail.

    1. **POSITION** — which expressions are page positions. **Closed on
       binding occurrences**, by two closures over the grammar rather than
       over a list of shapes: every binding occurrence of a position name
       comes from the module's own non-``Load`` store contexts and its binder
       is looked up in :data:`BINDERS_READ` (a binder not in that table is a
       refusal), and a position name held as a bare string outside
       :data:`STRING_FIELDS_READ` is a refusal. **Not** closed on how a
       position reaches a callee — that is axis 5. Cycle 2's F-201 measured eight shapes passing the first
       version of this walk silently; these closures catch shapes nobody
       wrote a branch for — a ``match``/``case`` capture, a lambda parameter
       default, a module function's return value. One declared exemption,
       :data:`EXEMPTION`, removable with ``follow_terms``.
    2. **DOOR** — which calls are geometry doors (ADR-0036/R2). **Closed**
       (CARD-262; it was SILENT, and cycle 3's F-301 measured four shapes
       reaching the real door with nothing reported). *A call whose callee's
       identity this walk cannot derive is a refusal.* Two closures, and no
       branch for any idiom: the **callee-identity** closure requires every
       ``ast.Call``'s callee to be a name or attribute whose every binding
       occurrence **in its own storage** holds a syntactic name or attribute
       — which closes a door whose name is never spelled at all, whether it
       is parked in a local or on an attribute — and the
       **door-spelling** closure refuses a :data:`GEOMETRY_DOORS` name held
       in any ``(class, field)`` pair outside :data:`DOOR_SPELLINGS_READ` —
       which closes a door reached by spelling its name as data. Each arm is
       removable on its own (``door_arms``) and each catches a shape the
       other misses.
    3. **MODULE** — which text the walk reads at all. **Declared, not
       closed:** it parses one module, so a position computed elsewhere and
       passed in is outside the enumeration rather than refused by it.
       ``book_kdp`` states no front-matter term of its own — it delegates to
       :func:`interior_page_count`. The bound is asserted in
       :meth:`test_the_module_axis_bound_is_measured_rather_than_declared`.
    4. **VALUE** — which wrong positions an integer literal reveals.
       **Declared, not closed:** a position spelled ``0`` or ``1`` is
       indistinguishable from the legitimate 1-based term
       (:data:`POSITION_LITERALS`), and a literal outside the module's text
       is not in the AST. It overlaps
       :class:`TestBookExport_TitlePageCountedEverywhere`'s monkeypatch case,
       which covers every position reaching a byte of output, rather than
       leaning on it.
    5. **CALL-GRAPH** — how a position reaches a callee. **Declared, not
       closed.** Callees are resolved **by name** against the module's own
       ``defs``, so a position forwarded through an alias of a non-door
       function, through a callback parameter used as a callee, or through a
       ``*args`` forwarder is neither read nor refused. Found by an
       independent reviewer's plants, not by this walk's author, and bounded
       in :data:`MEASURED_BLIND_SPOTS`.

    Axes 3, 4 and 5 are open **by declaration**, each with a control that
    fails: :meth:`test_the_module_axis_bound_is_measured_rather_than_declared`
    for axis 3, and :meth:`test_the_declared_blind_spots_are_still_exactly_these`
    for axes 4 and 5, which asserts those shapes **are** silent so the bound
    reds in both directions.

    The site set is held to an equality rather than a floor.
    :data:`PLANTED_SHAPES` and :data:`DOOR_SHAPES` are **regression nets over
    the shapes measured so far, never completeness arguments** — the
    completeness claim rests on the closures' quantifiers, and the tables'
    own control is that no row may declare a silent outcome.
    """

    MODULE = "src/nonogram/admin/book_pdf_generator.py"

    @classmethod
    def _counting_expressions(cls):
        """``[(line, source of the expression)]`` for every guide-counting term.

        The outermost enclosing expression of each ``GUIDE_PAGE_COUNT`` load:
        walk up from the name while the parent is still an expression, so an
        argument default, a ``range`` call and a long ``return`` arithmetic
        each come back whole rather than as the one ``BinOp`` the name sits in.
        """
        import ast
        from pathlib import Path

        source = (Path(__file__).resolve().parents[1] / cls.MODULE).read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        parent = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent[child] = node

        found = []
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Name)
                and node.id == "GUIDE_PAGE_COUNT"
                and isinstance(node.ctx, ast.Load)
            ):
                continue
            outermost = node
            while isinstance(parent.get(outermost), ast.expr):
                outermost = parent[outermost]
            found.append((outermost.lineno, outermost, ast.get_source_segment(source, outermost)))
        return found

    def test_every_guide_counting_expression_counts_the_title_page(self):
        import ast

        sites = self._counting_expressions()
        # An equality, not a floor (ADR-0039/R3; review cycle 2, F-201 filed
        # the two floors below this one and this is the third): the positions
        # the card had to move are the guide's own range, the TOC's page
        # number, `section_plan`'s `first_page`, `first_answer_page`, the two
        # walk defaults and `interior_page_count`'s formula — seven, so one
        # appearing or vanishing reds here instead of drifting under a floor.
        assert len(sites) == 7, [text for _, _, text in sites]
        for line, node, text in sites:
            names = {
                inner.id for inner in ast.walk(node) if isinstance(inner, ast.Name)
            }
            assert "TITLE_PAGE_COUNT" in names, (
                f"{self.MODULE}:{line} counts the guide without the title "
                f"page in front of it: {text!r}"
            )

    def test_no_literal_page_offset_survives_in_one_of_them(self):
        """The literal-``3`` check, done by enumeration rather than by grep.

        Every integer constant in those same expressions is collected. The
        only ones that may appear are ``1`` — the term that turns a count of
        front-matter pages into the 1-based position of the page after them,
        and the ``+ 1`` of the SOLUTIONS divider — and the ``0`` of
        ``interior_page_count``'s own "no puzzles, no answer section" branch.
        A ``2``, ``3`` or ``4`` among them would be a front-matter page count
        spelled as a literal, which is exactly what this card must not ship.
        """
        import ast

        sites = self._counting_expressions()
        offenders = []
        for line, node, text in sites:
            for inner in ast.walk(node):
                if isinstance(inner, ast.Constant) and isinstance(inner.value, int):
                    if inner.value not in (0, 1):
                        offenders.append((line, inner.value, text))

        assert not offenders, (
            "a page offset is written as a literal rather than counted from "
            f"TITLE_PAGE_COUNT/GUIDE_PAGE_COUNT: {offenders}"
        )
    # ----------------------------------------------------------------------
    # CARD-206 review F-102 / F-201 — every page position the walk can
    # follow, and a loud refusal for every shape it cannot
    # ----------------------------------------------------------------------

    #: The seed of the derivation below: the module's door onto page geometry
    #: (ADR-0036/R2, :meth:`BookPDFGenerator.page_spec`'s own docstring, "the
    #: one door onto the book's geometry"). Every interior page position in
    #: this module is a value that reaches it, directly or through a
    #: parameter — which is what makes a *derived* set possible at all, and
    #: what :meth:`test_each_geometry_door_carries_a_site_of_its_own` removes
    #: one member at a time to show the catch depends on each of them.
    GEOMETRY_DOORS = ("page_spec", "book_page_spec")

    #: The parameter that carries an interior page position through a door.
    #: Each door is seeded at the index of *this* parameter in that door's own
    #: signature, read from the signature rather than written here (review
    #: cycle 2, F-203: a hard-wired ``args[0]`` fed ``book_page_spec`` its
    #: *book*). A door whose signature has no such parameter is a refusal.
    POSITION_PARAMETER = "page_number"

    #: The only integer constants a page-position expression may hold: the
    #: ``1`` that turns a count of front-matter pages into the 1-based
    #: position after them (and the ``- 1`` of the SOLUTIONS divider), and the
    #: ``0`` of an empty count. A ``2``, ``3`` or ``4`` is a front-matter page
    #: count spelled as a literal.
    POSITION_LITERALS = (0, 1)

    #: The two module-level integer names a position may be counted from. Any
    #: *other* module-level name bound to an integer literal is read as that
    #: literal wherever it appears in a position, so a front-matter count
    #: hidden behind a name of its own is still reported (shape V15 below).
    FRONT_MATTER_CONSTANTS = ("TITLE_PAGE_COUNT", "GUIDE_PAGE_COUNT")

    #: The ``(node class, field)`` pairs that may hold a position name as a
    #: bare string and that the walk reads. Any other one that holds a
    #: position name is a refusal — which is what closes the walk over the
    #: grammar instead of over the shapes that came to mind. V10 and V11
    #: below measure two of those refusals firing.
    STRING_FIELDS_READ = (
        ("Name", "id"),
        ("Attribute", "attr"),
        ("keyword", "arg"),
        ("arg", "arg"),
    )

    #: The binder shapes the walk reads, and the field of each holding the
    #: expression a position bound there is computed from. A binding of a
    #: position in any other shape is a refusal.
    BINDERS_READ = {
        "Assign": "value",
        "AnnAssign": "value",
        "AugAssign": "value",
        "For": "iter",
        "AsyncFor": "iter",
        "comprehension": "iter",
        "NamedExpr": "value",
        "withitem": "context_expr",
    }

    #: The guard's one exemption (ADR-0039/R3), and the only shape allowed
    #: silently rather than read or refused: a term of a position expression
    #: that is itself a **non-position** name or attribute is read for the
    #: literals written in the expression and not followed into its own
    #: bindings. ``follow_terms=True`` removes it; its control is
    #: :meth:`test_the_one_exemption_does_not_absorb_what_it_must_not` and its
    #: cost is the equality in
    #: :meth:`test_the_exemptions_cost_on_this_module_is_the_measured_one`.
    EXEMPTION = "a non-position term of a position expression is not followed"

    @classmethod
    def _door_position_slots(cls, tree, doors, source):
        """``({door: slot}, refusals)``, each slot read off the door's own
        signature rather than written down (F-203)."""
        import ast
        from pathlib import Path

        local = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        imported = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    imported[alias.asname or alias.name] = node.module

        slots, refusals = {}, []
        for door in doors:
            names = None
            if door in local:
                arguments = local[door].args
                names = [
                    argument.arg
                    for argument in arguments.posonlyargs + arguments.args
                ]
                if names and names[0] in ("self", "cls"):
                    names = names[1:]
            elif door in imported:
                where = (
                    Path(__file__).resolve().parents[1]
                    / "src"
                    / (imported[door].replace(".", "/") + ".py")
                )
                if where.exists():
                    for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
                        if (
                            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and node.name == door
                        ):
                            arguments = node.args
                            names = [
                                argument.arg
                                for argument in arguments.posonlyargs + arguments.args
                            ]
                            break
            if names is None or cls.POSITION_PARAMETER not in names:
                refusals.append(
                    (
                        0,
                        "a geometry door with no "
                        f"{cls.POSITION_PARAMETER} parameter to seed from",
                        door,
                        repr(names),
                    )
                )
                continue
            slots[door] = names.index(cls.POSITION_PARAMETER)
        return slots, refusals

    @classmethod
    def _page_positions(
        cls, source=None, doors=None, follow_terms=False, door_arms=None
    ):
        """``([(line, kind, name, text, literals)], vocabulary, refusals)``.

        ``source`` defaults to the module's own text; a caller may pass one of
        its own — which is how every control below measures this analyser
        without a file on disk being mutated.

        The walk fails closed on the door axis and on the position axis's
        **binding occurrences** (ADR-0039/R2, and the class docstring's axis
        table, which is the authority -- three of its five axes are open by
        declaration and this sentence is not a substitute for it). On the
        position axis, binding occurrences come from the module's own store
        contexts
        rather than from a list of statement kinds, so every shape a
        **position** can flow through that this walk does not read appends a
        refusal below instead of passing. On the door axis, every ``ast.Call``
        must have a callee this walk can anchor and no :data:`GEOMETRY_DOORS`
        name may be spelled where it cannot read it, so a door whose identity
        is not derivable is refused rather than dropped (CARD-262; cycle 3's
        F-301 measured four such doors passing silently). ``follow_terms``
        removes the one :data:`EXEMPTION`; ``door_arms`` removes either
        door-axis closure, which is how each arm's own control measures it.

        Three axes stay open by declaration rather than closure, each with
        its own control: the **module** axis (this walk reads one module's
        text), the **value** axis (a position spelled ``0`` or ``1``, or a
        count this walk does not read as an integer) and the **call-graph**
        axis (a position forwarded past a callee resolved by name).
        """
        import ast
        import builtins
        from pathlib import Path

        if source is None:
            source = (Path(__file__).resolve().parents[1] / cls.MODULE).read_text(
                encoding="utf-8"
            )
        doors = cls.GEOMETRY_DOORS if doors is None else tuple(doors)
        arms = cls.DOOR_ARMS if door_arms is None else tuple(door_arms)
        tree = ast.parse(source)
        parent = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent[child] = node

        slots, refusals = cls._door_position_slots(tree, doors, source)

        def segment(node):
            return "" if node is None else (ast.get_source_segment(source, node) or "")

        def called(call):
            if isinstance(call.func, ast.Attribute):
                return call.func.attr
            if isinstance(call.func, ast.Name):
                return call.func.id
            return None

        def positional(node):
            args = node.args.posonlyargs + node.args.args
            return args[1:] if args and args[0].arg in ("self", "cls") else args

        def resolve(expr):
            """The position names ``expr``'s value flows from, or ``None``
            when ``expr`` is an expression to be read rather than a reference
            to follow. Following an attribute by its own name and a subscript
            or star by its base is what makes a container, a star-call and a
            plan attribute analysable instead of opaque."""
            if isinstance(expr, ast.Name):
                return {expr.id}
            if isinstance(expr, ast.Attribute):
                return {expr.attr}
            if isinstance(expr, (ast.Subscript, ast.Starred)):
                return resolve(expr.value)
            return None

        defs = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs.setdefault(node.name, []).append(node)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]

        vocabulary, sites, seen = set(), [], set()

        def feed(expr, kind, name):
            names = resolve(expr)
            if names:
                vocabulary.update(names)
            elif id(expr) not in seen:
                seen.add(id(expr))
                sites.append((expr, kind, name))

        for call in calls:
            door = called(call)
            if door not in slots:
                continue
            slot = slots[door]
            given = [
                keyword.value
                for keyword in call.keywords
                if keyword.arg == cls.POSITION_PARAMETER
            ]
            if slot < len(call.args):
                given.append(call.args[slot])
            given.extend(
                argument.value
                for argument in call.args[: slot + 1]
                if isinstance(argument, ast.Starred)
            )
            if not given:
                refusals.append(
                    (
                        call.lineno,
                        "a geometry door called with nothing in its position slot",
                        door,
                        segment(call),
                    )
                )
            for expr in given:
                feed(expr, "door argument", door)

        # Grow to a fixed point: a parameter a position is passed to is itself
        # a position, so its default and every argument its callers give it are
        # sites too. Bounded rather than `while True` — the vocabulary only
        # grows and the module's call graph is shallow, and a bound that is
        # reached is reported rather than silently truncating the set.
        rounds = 0
        for rounds in range(1, 17):
            before = (len(vocabulary), len(sites))
            for call in calls:
                for keyword in call.keywords:
                    if keyword.arg in vocabulary:
                        feed(keyword.value, "keyword", f"{called(call)}({keyword.arg})")
            # And backwards: a name a position is *copied from* is a position
            # too. That is how ``puzzle_pages``' ``first_page`` is one — it
            # reaches the door only through ``page_number = first_page``.
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                copied = resolve(node.value)
                if not copied:
                    continue
                if any(
                    (isinstance(target, ast.Name) and target.id in vocabulary)
                    or (
                        isinstance(target, ast.Attribute)
                        and target.attr in vocabulary
                    )
                    for target in node.targets
                ):
                    vocabulary.update(copied)
            for name, nodes in defs.items():
                for node in nodes:
                    args = node.args
                    slots_here = positional(node)
                    offset = len(args.posonlyargs + args.args) - len(slots_here)
                    pairs = list(
                        zip(
                            args.posonlyargs + args.args,
                            [None] * (len(args.posonlyargs + args.args) - len(args.defaults))
                            + list(args.defaults),
                        )
                    ) + list(zip(args.kwonlyargs, args.kw_defaults))
                    for argument, default in pairs:
                        if default is not None and argument.arg in vocabulary:
                            feed(default, "parameter default", f"{name}({argument.arg})")
                    for call in calls:
                        if called(call) != name:
                            continue
                        for index, given in enumerate(call.args):
                            slot = index + offset
                            everything = args.posonlyargs + args.args
                            if slot < len(everything) and everything[slot].arg in vocabulary:
                                feed(given, "argument", f"{name}({everything[slot].arg})")
            if (len(vocabulary), len(sites)) == before:
                break
        else:  # pragma: no cover - the bound is a tripwire, not a path
            raise AssertionError(
                "the page-position vocabulary was still growing after "
                f"{rounds} rounds, so this enumeration is truncated and the "
                "set it reports is not the module's"
            )

        # Every *binding occurrence* of a position name, found from the
        # module's own store contexts rather than from a list of statement
        # kinds: a binder this walk does not read is a refusal, so a shape
        # nobody thought of reds instead of passing (V10, V12, V13 below).
        def bound_name(node):
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                return node.attr
            if isinstance(node, ast.Subscript):
                return bound_name(node.value)
            return None

        kinds = {
            "Assign": "assignment",
            "AnnAssign": "assignment",
            "AugAssign": "augmented",
            "For": "loop",
            "AsyncFor": "loop",
            "comprehension": "comprehension",
            "NamedExpr": "walrus",
            "withitem": "with",
        }
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
                continue
            if isinstance(getattr(node, "ctx", None), ast.Load):
                continue
            name = bound_name(node)
            if name not in vocabulary:
                continue
            cursor = node
            while isinstance(parent.get(cursor), (ast.Tuple, ast.List, ast.Starred)):
                cursor = parent[cursor]
            binder = parent.get(cursor)
            shape = type(binder).__name__
            if shape not in cls.BINDERS_READ:
                refusals.append(
                    (
                        node.lineno,
                        f"a position bound in a {shape}, which this walk does "
                        "not read",
                        name,
                        segment(binder),
                    )
                )
                continue
            value = getattr(binder, cls.BINDERS_READ[shape])
            if value is None or id(value) in seen:
                continue
            seen.add(id(value))
            sites.append((value, kinds[shape], name))

        # A position name held as a bare string anywhere this walk does not
        # read it — `MatchAs.name`, `alias.asname`, `Global.names`.
        for node in ast.walk(tree):
            held_in = type(node).__name__
            for field in getattr(node, "_fields", ()):
                value = getattr(node, field, None)
                if isinstance(value, str):
                    held = [value]
                elif isinstance(value, list):
                    held = [item for item in value if isinstance(item, str)]
                else:
                    held = []
                for text in held:
                    if text in vocabulary and (
                        held_in,
                        field,
                    ) not in cls.STRING_FIELDS_READ:
                        refusals.append(
                            (
                                getattr(node, "lineno", 0),
                                f"a position name held in {held_in}.{field}, "
                                "which this walk does not read",
                                text,
                                segment(node),
                            )
                        )

        # A position that is a parameter of something that is not a `def`, so
        # neither its default nor its callers' arguments were read.
        for node in ast.walk(tree):
            if not isinstance(node, ast.arg) or node.arg not in vocabulary:
                continue
            holder = parent.get(parent.get(node))
            while holder is not None and not isinstance(
                holder, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
            ):
                holder = parent.get(holder)
            if not isinstance(holder, (ast.FunctionDef, ast.AsyncFunctionDef)):
                refusals.append(
                    (
                        node.lineno,
                        "a position as a parameter of a "
                        f"{type(holder).__name__}, whose callers this walk "
                        "does not read",
                        node.arg,
                        segment(holder),
                    )
                )

        # A door handed around rather than called: a `functools.partial` of it,
        # or any other reference, carries the position somewhere this walk
        # cannot see the call.
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute) or node.attr not in doors:
                continue
            above = parent.get(node)
            if isinstance(above, ast.Call) and above.func is node:
                continue
            refusals.append(
                (
                    node.lineno,
                    "a geometry door referenced without being called",
                    node.attr,
                    segment(above),
                )
            )

        # ------------------------------------------------------------------
        # The DOOR axis (CARD-262, the SEMANTICS block's axis 2): a call
        # whose callee's identity this walk cannot derive is a REFUSAL. Two
        # closures over the grammar, not a list of dynamic-access idioms --
        # neither arm names `getattr`, `setattr`, `methodcaller`,
        # `attrgetter` or `vars`, and each catches a shape the other misses.
        # ------------------------------------------------------------------
        if "callee identity" in arms:
            # A callee name is *anchored* when every binding occurrence of it
            # in this module holds a value that is itself a syntactic name or
            # attribute -- in which case a door could only have reached it by
            # being spelled, which the arm above and the arm below then see.
            # A name bound anywhere to an arbitrary expression is NOT
            # anchored, and a call through it may be a geometry door this
            # walk never looked at. The binder table is the same
            # :data:`BINDERS_READ` the position axis uses, so the two axes
            # share one authority rather than two hand-written lists.
            # Keyed on (storage, spelling), and the two storages are kept
            # APART: `text = f"..."` and `draw.text(...)` share a spelling and
            # nothing else, and conflating them cost 51 refusals on a module
            # with no defect in it -- measured, which is how the separation
            # was chosen rather than reasoned. A local and an attribute of the
            # same name are different places a door can be parked.
            opaque = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    storage, spelling = "a local name", node.id
                elif isinstance(node, ast.Attribute):
                    storage, spelling = "an attribute", node.attr
                else:
                    continue
                if isinstance(getattr(node, "ctx", None), ast.Load):
                    continue
                cursor = node
                while isinstance(
                    parent.get(cursor), (ast.Tuple, ast.List, ast.Starred)
                ):
                    cursor = parent[cursor]
                binder = parent.get(cursor)
                shape = type(binder).__name__
                if shape not in cls.BINDERS_READ:
                    continue
                bound = getattr(binder, cls.BINDERS_READ[shape], None)
                # An annotation-only `AnnAssign` (`field: int`) binds nothing
                # at run time, so it cannot carry a door.
                if bound is None or isinstance(bound, (ast.Name, ast.Attribute)):
                    continue
                opaque.setdefault(
                    (storage, spelling), (node.lineno, segment(binder))
                )
            for call in calls:
                if not isinstance(call.func, (ast.Name, ast.Attribute)):
                    refusals.append(
                        (
                            call.lineno,
                            "a call whose callee is a "
                            f"{type(call.func).__name__}, so this walk cannot "
                            "tell whether it is a geometry door",
                            type(call.func).__name__,
                            segment(call),
                        )
                    )
                    continue
                if isinstance(call.func, ast.Name):
                    key = ("a local name", call.func.id)
                else:
                    key = ("an attribute", call.func.attr)
                if key in opaque:
                    where, text = opaque[key]
                    refusals.append(
                        (
                            call.lineno,
                            f"a callee this walk cannot anchor: {key[0]} bound "
                            f"to an expression at line {where}, so this walk "
                            "cannot tell whether it is a geometry door",
                            key[1],
                            text,
                        )
                    )
        if "door spelling" in arms:
            # The mirror of the position axis's string closure, keyed on the
            # doors: a door name spelled in any `(class, field)` pair outside
            # :data:`DOOR_SPELLINGS_READ` is a refusal. This is what closes a
            # door reached by spelling its name as *data* -- a `Constant`
            # handed to a dynamic lookup, a module-level tuple element, a
            # `methodcaller` argument -- without a branch for any of them.
            for node in ast.walk(tree):
                held_in = type(node).__name__
                for field in getattr(node, "_fields", ()):
                    value = getattr(node, field, None)
                    if isinstance(value, str):
                        held = [value]
                    elif isinstance(value, list):
                        held = [item for item in value if isinstance(item, str)]
                    else:
                        held = []
                    for text in held:
                        if text in doors and (
                            held_in,
                            field,
                        ) not in cls.DOOR_SPELLINGS_READ:
                            refusals.append(
                                (
                                    getattr(node, "lineno", 0),
                                    "a geometry door name spelled in "
                                    f"{held_in}.{field}, which this walk does "
                                    "not read",
                                    text,
                                    segment(node),
                                )
                            )

        module_integers = {}
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, int)
                and not isinstance(node.value.value, bool)
            ):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        module_integers[target.id] = node.value.value

        names_of = frozenset(dir(builtins))
        found = []
        for expr, kind, name in sites:
            literals = set()
            for inner in ast.walk(expr):
                if isinstance(inner, ast.Call) and called(inner) not in names_of:
                    refusals.append(
                        (
                            inner.lineno,
                            "a position computed through a call this walk "
                            "cannot follow",
                            name,
                            segment(inner),
                        )
                    )
            for inner in ast.walk(expr):
                if isinstance(inner, ast.Constant):
                    if isinstance(inner.value, bool):
                        continue
                    if isinstance(inner.value, int):
                        literals.add(inner.value)
                    elif isinstance(inner.value, str) and inner.value.strip().isdigit():
                        literals.add(int(inner.value.strip()))
                elif isinstance(inner, ast.Name) and isinstance(inner.ctx, ast.Load):
                    if (
                        inner.id in module_integers
                        and inner.id not in cls.FRONT_MATTER_CONSTANTS
                    ):
                        literals.add(module_integers[inner.id])
                    elif (
                        follow_terms
                        and inner.id not in vocabulary
                        and inner.id not in cls.FRONT_MATTER_CONSTANTS
                        and inner.id not in names_of
                    ):
                        literals.add(("not followed", inner.id))
                elif isinstance(inner, ast.Attribute) and isinstance(
                    inner.ctx, ast.Load
                ):
                    if follow_terms and inner.attr not in vocabulary:
                        literals.add(("not followed", "." + inner.attr))
            found.append(
                (
                    expr.lineno,
                    kind,
                    name,
                    ast.get_source_segment(source, expr),
                    sorted(literals, key=repr),
                )
            )
        return (
            sorted(found),
            sorted(vocabulary),
            sorted({(line, shape, name, text) for line, shape, name, text in refusals}),
        )

    @classmethod
    def _bare_literals(cls, sites):
        return [
            (line, kind, name, text, [v for v in literals if v not in cls.POSITION_LITERALS])
            for line, kind, name, text, literals in sites
            if any(v not in cls.POSITION_LITERALS for v in literals)
        ]

    #: The module's own derived ``first_answer_page``, which every planted
    #: shape below replaces line-count-preservingly in a copy of the module's
    #: text held in memory. It must occur exactly once, so an edit to it reds
    #: rather than quietly planting nothing.
    DERIVED_POSITION = """        first_answer_page = (
            1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc_page_count + len(section) + 1
        )"""

    #: **A regression net over the shapes measured so far, never a
    #: completeness argument** (CARD-262 step 3): it regresses only on the
    #: shapes its author chose, and the walk's completeness claim rests on
    #: the closures' own quantifiers instead. Its one own control is
    #: :meth:`test_no_planted_shape_is_declared_silent` -- no row may declare
    #: an empty outcome, so a blind spot cannot be parked here as expected.
    #:
    #: Review cycle 2, F-201's own nine shapes (V0–V9) and ten more, each
    #: hiding the literal ``3`` in a page position, with the outcome this walk
    #: must produce: ``"offender"`` when it reads the literal, ``"refusal"``
    #: when it cannot follow the shape and says so. Eight of V1–V9 passed
    #: **silently** before cycle 3's round. V10–V15 are shapes this walk has
    #: no branch for, and are here because the closures rather than a branch
    #: are what must catch them. V16–V19 give the four members of
    #: :data:`BINDERS_READ` that had no planted shape one each, so the per-
    #: member control below is not the only place any of the eight is
    #: measured (CARD-206 cycle 3's F-303).
    PLANTED_SHAPES = (
        (
            "V0 bare literal (the proven control)",
            """        first_answer_page = (
            3 + len(section)
        )""",
            "",
            ("offender",),
        ),
        (
            "V1 list container + subscript",
            """        _slots = [3 + len(section)]
        first_answer_page = _slots[0]
        #""",
            "",
            ("offender",),
        ),
        (
            "V2 dict container",
            """        _slots = {"answers": 3 + len(section)}
        first_answer_page = _slots["answers"]
        #""",
            "",
            ("offender",),
        ),
        (
            "V3 tuple-unpack assignment",
            """        first_answer_page, _spare = 3 + len(section), 0
        #
        #""",
            "",
            ("offender",),
        ),
        (
            "V4 augmented assignment (+= 3)",
            """        first_answer_page = len(section)
        first_answer_page += 3
        #""",
            "",
            ("offender",),
        ),
        (
            "V5 functools.partial onto the door",
            """        _door = functools.partial(self.page_spec)
        _door(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        (
            "V6 keyword-only call into the door",
            """        self.page_spec(page_number=3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        #""",
            "",
            ("offender",),
        ),
        (
            "V7 comprehension target",
            """        _specs = [p for first_answer_page in [3 + len(section)]
                  for p in [first_answer_page]]
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("offender",),
        ),
        (
            "V8 attribute assigned in this module",
            """        self.page_number = 3 + len(section)
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        #""",
            "",
            ("offender",),
        ),
        (
            "V9 starred call into the door",
            """        _args = [3 + len(section)]
        self.page_spec(*_args)
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("offender",),
        ),
        (
            "V10 match-case capture",
            """        match 3 + len(section):
            case int() as first_answer_page:
                pass""",
            "",
            ("refusal",),
        ),
        (
            "V11 import-as rebinding",
            """        import os as first_answer_page
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + 3
        #""",
            "",
            ("offender", "refusal"),
        ),
        (
            "V12 with-as target",
            """        with _positions(3 + len(section)) as first_answer_page:
            pass
        #""",
            "\n\ndef _positions(n):\n    return n\n",
            ("offender", "refusal"),
        ),
        (
            "V13 lambda parameter default",
            """        _f = lambda first_answer_page=3 + len(section): first_answer_page
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        #""",
            "",
            ("refusal",),
        ),
        (
            "V14 return value of a module function",
            """        first_answer_page = _hidden_position(section)
        #
        #""",
            "\n\ndef _hidden_position(section):\n    return 3 + len(section)\n",
            ("refusal",),
        ),
        (
            "V15 page count behind a module-level name",
            """        first_answer_page = (
            _HIDDEN_FRONT_MATTER + len(section)
        )""",
            "\n\n_HIDDEN_FRONT_MATTER = 3\n",
            ("offender",),
        ),
        (
            "V16 annotated assignment",
            """        first_answer_page: int = 3 + len(section)
        #
        #""",
            "",
            ("offender",),
        ),
        (
            "V17 for-loop target",
            """        for first_answer_page in [3 + len(section)]:
            pass
        #""",
            "",
            ("offender",),
        ),
        (
            "V18 async-for target",
            """        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        #
        #""",
            "\n\nasync def _ahidden(section):\n"
            "    async for first_answer_page in [3 + len(section)]:\n"
            "        pass\n",
            ("offender",),
        ),
        (
            "V19 walrus binding",
            """        _x = (first_answer_page := 3 + len(section))
        #
        #""",
            "",
            ("offender",),
        ),
    )

    #: A module shaped like ``interior_stream``'s own prelude, used by the
    #: control below: the defect F-102 found, and the derivation that replaced
    #: it, in a source this test owns. The two differ in that one assignment
    #: and nothing else, so the analyser's two answers differ in the literal
    #: and nothing else — which the control asserts rather than assumes, by
    #: comparing the vocabularies the two sources produce.
    PLANTED_LITERAL = '''
TITLE_PAGE_COUNT = 1
GUIDE_PAGE_COUNT = 2


class Generator:
    def page_spec(self, page_number):
        return (page_number,)

    def plan(self, section, toc_page_count):
        first_answer_page = 3 + len(section)
        return self.page_spec(first_answer_page)
'''

    DERIVED_INSTEAD = PLANTED_LITERAL.replace(
        "first_answer_page = 3 + len(section)",
        "first_answer_page = (\n"
        "            1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc_page_count\n"
        "            + len(section) + 1\n"
        "        )",
    )

    #: The one shape :data:`EXEMPTION` absorbs, and what it must not be read
    #: as covering: a front-matter count reached through a local name the
    #: walk does not follow. A source this test owns, so the control can
    #: measure both states of the exemption.
    EXEMPTED_TERM = '''
TITLE_PAGE_COUNT = 1
GUIDE_PAGE_COUNT = 2


class Generator:
    def page_spec(self, page_number=1):
        return (page_number,)

    def plan(self, section, toc_page_count):
        hidden = 3
        first_answer_page = hidden + len(section)
        return self.page_spec(first_answer_page)
'''

    #: The set this module holds today, as an equality rather than a floor
    #: (ADR-0039/R3): a site appearing or vanishing reds here and says which.
    #: ``book_page_spec``'s seed is counted in it now that its slot is read
    #: from its signature (F-203).
    POSITION_NAMES = (
        "first_answer_page",
        "first_page",
        "guide_page_number",
        "page_number",
        "puzzle_page",
        "title_page_number",
    )
    POSITION_SITE_COUNT = 23

    def test_the_page_position_set_is_derived_from_the_one_geometry_door(self):
        """The set is grown from the doors, and held to an equality.

        An enumeration that found nothing would make the literal check below
        pass by construction, which is the failure the narrower guard had.
        The count and the names are asserted exactly, so the day a position
        is added to or removed from the module this reds and names it.
        """
        sites, vocabulary, refusals = self._page_positions()

        assert refusals == [], refusals
        assert tuple(vocabulary) == self.POSITION_NAMES, vocabulary
        assert len(sites) == self.POSITION_SITE_COUNT, (
            f"the module holds {len(sites)} page-position sites, not "
            f"{self.POSITION_SITE_COUNT}: a position was added or removed, so "
            "this equality and the figure in the card's notes both need "
            f"re-measuring. {[(line, kind, name) for line, kind, name, _, _ in sites]}"
        )
        # ADR-0039/R1's own shape: the catch depends on the set member. Take
        # the doors away and the derivation has no seed, so it reports nothing
        # at all -- which is what makes "derived from the door" a measurement
        # rather than a sentence about the code above.
        without, no_vocabulary, no_refusals = self._page_positions(doors=())
        assert (without, no_vocabulary, no_refusals) == ([], [], []), (
            "the enumeration still finds page positions with no geometry "
            "door in its seed set, so it is not derived from the door"
        )

    def test_each_geometry_door_carries_a_site_of_its_own(self):
        """ADR-0039/R1, per member: every door catches something no other
        door does — caught with it in the set, missed without it.

        Review cycle 2, F-203: ``book_page_spec``'s slot used to be
        ``args[0]``, which is its *book*, so the member contributed no
        position at all and this control could not have existed. Its slot is
        read from its signature now.
        """
        full = {
            (line, kind, name)
            for line, kind, name, _, _ in self._page_positions()[0]
        }
        for door in self.GEOMETRY_DOORS:
            rest = tuple(d for d in self.GEOMETRY_DOORS if d != door)
            without = {
                (line, kind, name)
                for line, kind, name, _, _ in self._page_positions(doors=rest)[0]
            }
            assert full - without, (
                f"removing {door!r} from GEOMETRY_DOORS changes nothing this "
                "enumeration reports, so that member is inert and the set "
                "claims a reach one of its members does not carry"
            )

    def test_no_page_position_in_the_module_is_written_as_a_bare_literal(self):
        """F-102: the literal check over **every** position, not only the
        guide-derived ones.

        ``interior_stream``'s ``first_answer_page = 3 + len(section)`` is the
        site this was written for: it loads neither constant, so the
        guide-counting walk above never visited it, and it reached no byte of
        output, so the monkeypatch case could not see it either.
        """
        sites, _, _ = self._page_positions()

        assert self._bare_literals(sites) == [], (
            "an interior page position is written with a literal page count "
            "in it rather than counted from TITLE_PAGE_COUNT/"
            f"GUIDE_PAGE_COUNT: {self._bare_literals(sites)}"
        )

    def test_every_planted_position_shape_is_caught_or_refused(self):
        """F-201: the shape table, re-run against the module's own text.

        Eight of F-201's nine shapes passed silently. Each is planted here
        line-count-preservingly into a copy of the module's source held in
        memory — nothing on disk is mutated — and each must come back either
        as a literal this walk read or as a refusal it named. A shape that
        comes back clean is a silent pass, which is what ADR-0039/R2 forbids.
        """
        from pathlib import Path

        source = (Path(__file__).resolve().parents[1] / self.MODULE).read_text(
            encoding="utf-8"
        )
        assert source.count(self.DERIVED_POSITION) == 1, (
            "DERIVED_POSITION no longer occurs exactly once in "
            f"{self.MODULE}, so these shapes would plant nothing and pass "
            "vacuously"
        )

        measured = []
        for label, body, extra, _ in self.PLANTED_SHAPES:
            assert len(body.splitlines()) == 3, label
            planted = source.replace(self.DERIVED_POSITION, body) + extra
            sites, _, refusals = self._page_positions(planted)
            outcome = []
            if self._bare_literals(sites):
                outcome.append("offender")
            if refusals:
                outcome.append("refusal")
            measured.append((label, tuple(outcome)))

        assert measured == [
            (label, outcome) for label, _, _, outcome in self.PLANTED_SHAPES
        ], (
            "a planted page-position shape came back with an outcome this "
            f"table does not declare; an empty tuple is a silent pass: {measured}"
        )

    def test_a_planted_bare_literal_is_caught_and_the_derivation_is_not(self):
        """The control for the test above, in both states (ADR-0039/R3).

        A guard whose subject has been removed from the file can no longer
        fail on it, so what it catches has to be measured on a source that
        still holds the defect. Both sources are this test's own: one with
        F-102's literal in it, one with the derivation that replaced it.
        """
        planted, planted_vocabulary, _ = self._page_positions(self.PLANTED_LITERAL)
        derived, derived_vocabulary, _ = self._page_positions(self.DERIVED_INSTEAD)

        assert "first_answer_page" in planted_vocabulary, planted_vocabulary
        assert planted_vocabulary == derived_vocabulary, (
            "the two sources differ in more than the literal, so the "
            "comparison below would not be about the literal"
        )
        caught = self._bare_literals(planted)
        assert [(kind, name, bad) for _, kind, name, _, bad in caught] == [
            ("assignment", "first_answer_page", [3])
        ], caught
        assert self._bare_literals(derived) == [], (
            "the derived form is reported as a bare literal, so this guard "
            "would red on the fix as well as on the defect"
        )

    def test_the_one_exemption_does_not_absorb_what_it_must_not(self):
        """:data:`EXEMPTION`'s control, in both states (ADR-0039/R3).

        The exemption is that a non-position term of a position expression is
        read for the literals written in it and not followed into its own
        bindings. What it must **not** be read as covering is a front-matter
        count that is right there in the module behind such a term, and that
        is what this plants: with the exemption removed the walk reports it,
        with the exemption in place it does not.
        """
        kept, _, _ = self._page_positions(self.EXEMPTED_TERM)
        removed, _, _ = self._page_positions(self.EXEMPTED_TERM, follow_terms=True)

        assert self._bare_literals(kept) == [], (
            "the exemption no longer absorbs a non-position term, so its "
            "measured cost on the module is out of date too"
        )
        assert [
            (kind, name, bad) for _, kind, name, _, bad in self._bare_literals(removed)
        ] == [
            (
                "assignment",
                "first_answer_page",
                [("not followed", "hidden"), ("not followed", "section")],
            )
        ], self._bare_literals(removed)

    def test_the_exemptions_cost_on_this_module_is_the_measured_one(self):
        """What the exemption costs here, as a number rather than a sentence.

        Removing it reds on the module itself — five of its sites hold a term
        this walk does not follow — which is the measurement the exemption
        rests on, and it is asserted rather than written down so that it
        cannot go stale while the docstring keeps claiming it.
        """
        exempted = self._bare_literals(self._page_positions(follow_terms=True)[0])
        terms = sorted(
            {
                item[1]
                for _, _, _, _, bad in exempted
                for item in bad
                # A bare integer here would be a literal the walk read, not a
                # term it declined to follow; it belongs to the test above.
                if isinstance(item, tuple)
            }
        )

        assert len(exempted) == 5, exempted
        assert terms == ["index", "pages", "section", "toc_page_count"], terms

    # ----------------------------------------------------------------------
    # CARD-262 — the DOOR axis: a call whose callee's identity this walk
    # cannot derive is a refusal (the SEMANTICS block's axis 2)
    # ----------------------------------------------------------------------

    #: The ``(node class, field)`` pairs in which a geometry-door name may
    #: appear. The exact mirror of :data:`STRING_FIELDS_READ`, keyed on
    #: :data:`GEOMETRY_DOORS` instead of on the position vocabulary: a door
    #: name spelled anywhere else -- a ``Constant`` handed to ``getattr``, an
    #: element of a module-level tuple, a ``methodcaller`` argument -- is a
    #: refusal. No entry here names a builtin, so the closure is over the
    #: grammar rather than over the shapes that came to mind.
    DOOR_SPELLINGS_READ = (
        ("Attribute", "attr"),
        ("Name", "id"),
        ("FunctionDef", "name"),
        ("AsyncFunctionDef", "name"),
        ("alias", "name"),
        ("alias", "asname"),
        ("arg", "arg"),
        ("keyword", "arg"),
    )

    #: The two door-axis closures, each removable on its own so that
    #: ADR-0039/R1's "caught WITH, missed WITHOUT" can be measured per arm
    #: (:meth:`test_each_door_axis_arm_catches_a_shape_the_other_misses`).
    DOOR_ARMS = ("callee identity", "door spelling")

    #: Shapes that reach the real geometry door, with the outcome this walk
    #: must produce. **A regression net over the door shapes measured so
    #: far, never a completeness argument** -- the completeness claim rests
    #: on the closures' own quantifiers (every ``ast.Call``; every
    #: ``(class, field)`` pair), which no table can establish. W0--W3 are
    #: cycle 3's F-301, the four shapes that reached the door with nothing
    #: reported; W4 and W6 were already refused before this card and are
    #: here so a regression in *them* also reds; W9 is the shape the
    #: callee-identity arm misses and the door-spelling arm catches.
    DOOR_SHAPES = (
        (
            "W0 getattr with a literal door name (F-301's own plant)",
            """        _d = getattr(self, "page_spec")
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        (
            "W1 getattr with an assembled name",
            """        _d = getattr(self, "page_" + "spec")
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        (
            "W2 a door through a local string variable",
            """        _n = "page_spec"; _d = getattr(self, _n)
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        (
            "W3 operator.methodcaller",
            """        _d = operator.methodcaller("page_spec", 3 + len(section))
        _d(self)
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        (
            "W4 a local alias of the door (refused before this card)",
            """        _d = self.page_spec
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        (
            "W5 the immediate call of a getattr result",
            """        getattr(self, "page_" + "spec")(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        #""",
            "",
            ("refusal",),
        ),
        (
            "W6 a door out of a dict of callables (refused before this card)",
            """        _t = {"a": self.page_spec}; _t["a"](3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        #""",
            "",
            ("refusal",),
        ),
        (
            "W7 operator.attrgetter",
            """        _d = operator.attrgetter("page_spec")(self)
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        (
            "W8 a vars() lookup with an assembled name",
            """        _d = vars(type(self))["page_" + "spec"]
        _d(self, 3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        (
            "W9 a chained alias of a getattr door",
            """        _m = getattr(self, "page_spec"); _m2 = _m
        _m2(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        (
            "W10 a door name taken from a module-level tuple",
            """        _d = getattr(self, _DOOR_NAMES[0])
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n\n_DOOR_NAMES = ("page_spec",)\n',
            ("refusal",),
        ),
        (
            "W11 a conditional door expression (refused before this card)",
            """        _d = (self.page_spec if section else self.page_spec)
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        # W12-W17 are the independent reviewer's plants (AC-3). W12-W14 are
        # the STORAGE family that falsified this card's first declaration: the
        # door parked on an ATTRIBUTE rather than a local, which the first
        # draft of the callee-identity arm treated as self-evidently anchored
        # and passed SILENTLY. W12 is W0 with `_d` spelled `self._door`.
        (
            "W12 an attribute-stored getattr door, name never spelled",
            """        self._door = getattr(self, "page_" + _DOOR_SUFFIX)
        self._door(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n\n_DOOR_SUFFIX = "spec"\n',
            ("refusal",),
        ),
        (
            "W13 an attribute-stored door laundered through a helper",
            """        self._door = _pick(getattr(self, "page_" + _S))
        self._door(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n\n_S = "spec"\n\n\ndef _pick(door):\n    return door\n',
            ("refusal",),
        ),
        (
            "W14 a __call__ object on an attribute, wrapping the door",
            """        self._spec_for = _AnswerSpec(self)
        self._spec_for(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "\n\nclass _AnswerSpec:\n    def __init__(self, generator):\n"
            "        self._generator = generator\n\n"
            "    def __call__(self, page_number):\n"
            "        return self._generator.page_spec(page_number)\n",
            ("refusal",),
        ),
        (
            "W15 an opaque door bound by a for target",
            """        for _d in (getattr(self, "page_" + _S),):
            _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n\n_S = "spec"\n',
            ("refusal",),
        ),
        (
            "W16 an opaque door bound by a walrus callee",
            """        (_d := getattr(self, "page_" + _S))(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        #""",
            '\n\n_S = "spec"\n',
            ("refusal",),
        ),
        (
            "W17 a door in a dict on self, subscript callee",
            """        self._doors = {"answers": self.page_spec}
        self._doors["answers"](3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
    )

    @classmethod
    def _plant(cls, body, extra=""):
        """The module's own text with ``body`` in place of its one derived
        position, line-count-preservingly, in memory. Nothing on disk is
        mutated by any control in this class."""
        from pathlib import Path

        source = (Path(__file__).resolve().parents[1] / cls.MODULE).read_text(
            encoding="utf-8"
        )
        assert source.count(cls.DERIVED_POSITION) == 1, (
            "DERIVED_POSITION no longer occurs exactly once in "
            f"{cls.MODULE}, so this plant would plant nothing and pass vacuously"
        )
        assert len(body.splitlines()) == 3, body
        return source.replace(cls.DERIVED_POSITION, body) + extra

    @classmethod
    def _outcome(cls, planted, **kwargs):
        """``("offender"?, "refusal"?)`` -- an empty tuple is a silent pass."""
        sites, _, refusals = cls._page_positions(planted, **kwargs)
        outcome = []
        if cls._bare_literals(sites):
            outcome.append("offender")
        if refusals:
            outcome.append("refusal")
        return tuple(outcome)

    def test_every_door_shape_is_read_or_refused_and_never_silent(self):
        """AC-2 / ADR-0039/R2 on the DOOR axis: a call whose callee's identity
        this walk cannot derive is a refusal.

        Cycle 3's F-301 measured four shapes reaching the real geometry door
        with **nothing** reported -- ``refusals == []``, the vocabulary and
        site equalities intact, the position table green. They are W0--W3
        here, and W12--W14 are the storage family an independent reviewer
        found silent in this card's own first draft (AC-3). The kill for every row, W3's ``operator.methodcaller``
        included, is **this assertion**: the module's text is analysed in
        memory and never imported, so no row can be killed by production
        raising ``NameError`` for an unimported ``operator``.
        """
        measured = [
            (label, self._outcome(self._plant(body, extra)))
            for label, body, extra, _ in self.DOOR_SHAPES
        ]

        assert measured == [
            (label, outcome) for label, _, _, outcome in self.DOOR_SHAPES
        ], (
            "a planted geometry-door shape came back with an outcome this "
            f"table does not declare; an empty tuple is a silent pass: {measured}"
        )

    def test_each_door_axis_arm_catches_a_shape_the_other_misses(self):
        """ADR-0039/R1 per arm, in both directions, over the whole table.

        The two closures are not one mechanism written twice. The
        callee-identity arm closes a door whose name is **never spelled** --
        assembled at run time (W1, W5, W8) or taken from data (W10) -- and the
        door-spelling arm closes a door reached by spelling its name as
        **data** past a callee the other arm can anchor (W9). So each arm has
        a row the other leaves silent, which is asserted here rather than
        read off the code, and with **both** arms removed F-301's four shapes
        are silent again -- which is the "missed WITHOUT" direction stated as
        a reproduction of the finding rather than as a sentence.
        """
        for arm in self.DOOR_ARMS:
            rest = tuple(a for a in self.DOOR_ARMS if a != arm)
            silent = [
                label
                for label, body, extra, _ in self.DOOR_SHAPES
                if self._outcome(self._plant(body, extra), door_arms=rest) == ()
            ]
            assert silent, (
                f"removing the {arm!r} arm leaves every row of DOOR_SHAPES "
                "still caught, so that arm carries no shape of its own and "
                "the door axis claims a reach one of its arms does not hold"
            )

        reproduced = [
            label
            for label, body, extra, _ in self.DOOR_SHAPES
            if self._outcome(self._plant(body, extra), door_arms=()) == ()
        ]
        assert reproduced[:4] == [label for label, _, _, _ in self.DOOR_SHAPES[:4]], (
            "with both door-axis arms removed, cycle 3's four F-301 shapes "
            f"are no longer the silent ones: {reproduced}"
        )

    def test_the_door_axis_arms_reach_every_call_and_refuse_none_of_them(self):
        """The door closure's quantifier and its cost on this module, both
        asserted (ADR-0039/R2, ADR-0039/R3, G-1).

        The completeness claim is the quantifier -- *every* ``ast.Call`` --
        so what is asserted is the partition: every call in the module is
        either a callee this walk anchored or a refusal it named, counted by
        a second, independent walk written here rather than by re-calling the
        analyser. And the arms are **refusal-only**: with them removed the
        sites and the vocabulary are identical, so they change what the guard
        *sees* and nothing about what the module *does*.
        """
        import ast
        from pathlib import Path

        source = (Path(__file__).resolve().parents[1] / self.MODULE).read_text(
            encoding="utf-8"
        )
        calls = [
            node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
        ]
        anchored = [
            node
            for node in calls
            if isinstance(node.func, (ast.Name, ast.Attribute))
        ]
        # The denominator, as an equality: `len(anchored) == len(calls)`
        # alone would be satisfied by a module with no calls at all, so the
        # count the closure quantifies over is pinned too.
        assert len(calls) == 816, (
            f"this module holds {len(calls)} calls, not 816, so the door "
            "closure's denominator moved and the figure in the card's notes "
            "needs re-measuring"
        )
        assert len(anchored) == len(calls), (
            f"{len(calls) - len(anchored)} of this module's {len(calls)} calls "
            "have a callee that is not a syntactic name, so the door axis "
            "costs refusals here and the equality below is out of date"
        )

        sites, vocabulary, refusals = self._page_positions()
        assert refusals == [], refusals

        bare, bare_vocabulary, bare_refusals = self._page_positions(door_arms=())
        assert (sites, vocabulary) == (bare, bare_vocabulary), (
            "the door-axis arms changed which positions this walk reads; "
            "they may only add refusals"
        )
        assert bare_refusals == [], bare_refusals

    #: One tiny module per member of :data:`BINDERS_READ`, each binding a
    #: page position in that one shape with the literal ``3`` in it. The
    #: control below reads each twice -- with the member in the table and
    #: without -- so every member of a derived set has a control of its own
    #: (ADR-0039/R1; CARD-206 cycle 3's F-303 filed ``AsyncFor`` and
    #: ``NamedExpr`` as having none anywhere, and F-203 before it was the
    #: same shape on ``GEOMETRY_DOORS``).
    BINDER_BINDINGS = {
        "Assign": "        first_answer_page = 3 + len(section)",
        "AnnAssign": "        first_answer_page: int = 3 + len(section)",
        "AugAssign": (
            "        first_answer_page = len(section)\n"
            "        first_answer_page += 3"
        ),
        "For": (
            "        for first_answer_page in [3 + len(section)]:\n"
            "            pass"
        ),
        "AsyncFor": (
            "        async for first_answer_page in [3 + len(section)]:\n"
            "            pass"
        ),
        "comprehension": (
            "        _ = [p for first_answer_page in [3 + len(section)]\n"
            "             for p in [first_answer_page]]"
        ),
        "NamedExpr": "        _x = (first_answer_page := 3 + len(section))",
        "withitem": (
            "        with open(3 + len(section)) as first_answer_page:\n"
            "            pass"
        ),
    }

    @classmethod
    def _binder_source(cls, member):
        """A module this test owns, binding a position in ``member``'s shape.

        Small on purpose: the control below reads sixteen of these, and the
        generator's own 7,000 lines buy nothing here -- the shape under test
        is the binder, not the module.
        """
        keyword = "async def" if member == "AsyncFor" else "def"
        return (
            "TITLE_PAGE_COUNT = 1\n"
            "GUIDE_PAGE_COUNT = 2\n"
            "\n\n"
            "class Generator:\n"
            "    def page_spec(self, page_number=1):\n"
            "        return (page_number,)\n"
            "\n"
            f"    {keyword} plan(self, section):\n"
            f"{cls.BINDER_BINDINGS[member]}\n"
            "        return self.page_spec(first_answer_page)\n"
        )

    def test_every_binder_read_is_what_makes_its_own_shape_read(self):
        """F-303, closed for all eight members rather than for the two filed.

        A member of a derived set with no control is that set's own
        ADR-0039/R1 defect, and this is the third appearance of that shape on
        this board. So the control is per member and uniform: with the member
        in :data:`BINDERS_READ` its shape is **read** -- the literal ``3`` is
        reported and nothing is refused -- and with the member removed the
        very same source comes back as a **refusal** and the literal is not
        read. Neither state is silent, which is the point: removing a binder
        narrows what the walk reads without opening a hole.
        """
        assert set(self.BINDER_BINDINGS) == set(self.BINDERS_READ), (
            "BINDERS_READ and BINDER_BINDINGS have drifted apart, so a member "
            "could be added to the table with no control: "
            f"{set(self.BINDERS_READ) ^ set(self.BINDER_BINDINGS)}"
        )

        # Only `page_spec` is seeded: these sources define that door and not
        # `book_page_spec`, and an unseedable door is itself a refusal (F-203),
        # which would drown the one refusal this control is measuring.
        only = ("page_spec",)
        for member in self.BINDERS_READ:
            source = self._binder_source(member)
            with_it = self._outcome(source, doors=only)
            rest = {k: v for k, v in self.BINDERS_READ.items() if k != member}
            original = self.BINDERS_READ
            try:
                type(self).BINDERS_READ = rest
                without = self._outcome(source, doors=only)
            finally:
                type(self).BINDERS_READ = original

            assert with_it == ("offender",), (
                f"{member}'s own shape is not read with {member!r} in "
                f"BINDERS_READ: {with_it}"
            )
            assert without == ("refusal",), (
                f"removing {member!r} from BINDERS_READ does not turn its own "
                f"shape into a refusal, so that member is inert: {without}"
            )

    #: The measured bounds of the two axes this guard leaves open, each a
    #: shape an **independent** reviewer planted (AC-3) and this walk neither
    #: reads nor refuses. They are asserted to **be** silent, which is what
    #: gives a declared bound a control that can fail in **both** directions
    #: (ADR-0039/R3): a change that starts catching one of these reds here and
    #: forces the bound to be re-measured, instead of leaving a docstring
    #: claiming a reach nobody checked. That is the discipline whose absence
    #: escalated CARD-206 -- the bound is declared, never claimed sound.
    MEASURED_BLIND_SPOTS = (
        (
            "the VALUE axis: the count spelled in ones",
            """        first_answer_page = (
            1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc_page_count + len(section) + 1 + 1 + 1 + 1
        )""",
            "",
            "POSITION_LITERALS admits 1 and caps nothing, so three extra "
            "front-matter pages are added with the derivation, the vocabulary, "
            "the 23-site equality and the 7-site guide equality all intact",
        ),
        (
            "the VALUE axis: an annotated module constant",
            """        first_answer_page = (
            _HIDDEN_FRONT_MATTER + len(section)
        )""",
            "\n\n_HIDDEN_FRONT_MATTER: int = 3\n",
            "`module_integers` reads only a top-level `ast.Assign` of a bare "
            "int Constant, so V15's mechanism is defeated by an AnnAssign, by "
            "`= 1 + 2`, and by a constant inside an `if` block",
        ),
        (
            "the CALL-GRAPH axis: an alias of a non-door position method",
            """        _f = self.puzzle_pages
        _f([], 3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            "`puzzle_pages`' `first_page` is in the vocabulary, but callees "
            "are resolved by name against the module's own `defs`, so an "
            "alias of a NON-door function that carries a position is neither "
            "read nor refused -- the door axis refuses exactly this (W4)",
        ),
        (
            "the CALL-GRAPH axis: a parameter used as a callee",
            """        _plan_answer_specs(section, _spec_maker(self))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        #""",
            "\n\ndef _plan_answer_specs(section, make_spec):\n"
            "    return [make_spec(3 + len(section))]\n\n\n"
            "def _spec_maker(generator):\n"
            "    def _spec(page_number):\n"
            "        return generator.page_spec(page_number)\n\n"
            "    return _spec\n",
            "a parameter is an `ast.arg`, never a binding occurrence under one "
            "of BINDERS_READ's shapes, so it can never enter the opaque table; "
            "a lambda in the same place IS refused (V13), so the gap is "
            "specifically a nested `def` reached through a parameter",
        ),
    )

    def test_the_declared_blind_spots_are_still_exactly_these(self):
        """The two DECLARED axes' control, in both directions (AC-4).

        An honest bound must be **declared, not claimed sound**. These four
        shapes were planted by a reviewer who did not write this walk, and
        this walk neither reads nor refuses any of them. Asserting that they
        are silent is what makes the bound falsifiable: narrow the value axis
        or close the call-graph axis and this reds, naming the row, so the
        declaration is re-measured rather than left standing while the code
        has moved underneath it.

        It is deliberately **not** a row of :data:`DOOR_SHAPES` or
        :data:`PLANTED_SHAPES`: those tables forbid a silent outcome, and a
        blind spot parked in them as expected is the shape ADR-0039/R2
        forbids. A bound lives in its own table, with its own assertion.
        """
        measured = [
            (label, self._outcome(self._plant(body, extra)))
            for label, body, extra, _ in self.MEASURED_BLIND_SPOTS
        ]

        assert measured == [
            (label, ()) for label, _, _, _ in self.MEASURED_BLIND_SPOTS
        ], (
            "a declared blind spot is no longer silent, so the bound this "
            "guard declares is out of date and the docstring that rests on "
            f"it is claiming the wrong reach: {measured}"
        )

    def test_no_planted_shape_is_declared_silent(self):
        """:data:`PLANTED_SHAPES` and :data:`DOOR_SHAPES` are regression nets,
        and this is what stops either reading as a completeness argument.

        Neither table can argue completeness: each regresses only on the
        shapes its author chose, which is the lesson CARD-206's three cycles
        taught. What a table *can* be held to is that it never parks a blind
        spot in itself as acceptable -- a row whose declared outcome is the
        empty tuple is a silent pass recorded as expected, which ADR-0039/R2
        forbids. So every row of both tables must declare a non-empty
        outcome, and a shape that cannot be read or refused has to become a
        named ADR-0039/R3 exemption with a control instead of a table row.
        """
        silent = [
            label
            for table in (self.PLANTED_SHAPES, self.DOOR_SHAPES)
            for label, _, _, outcome in table
            if not outcome
        ]

        assert silent == [], (
            "a planted shape declares an empty outcome, which records a "
            f"silent pass as expected rather than refusing it: {silent}"
        )

    #: The one geometry-door call outside this module that passes a position
    #: that is neither absent nor a :data:`POSITION_LITERAL` -- the MODULE
    #: axis's declared bound (the SEMANTICS block's axis 3), held as an
    #: equality so a second one reds here instead of appearing silently.
    #: ``book_proof.py`` builds a standalone proof document with no front
    #: matter at all, so a front-matter-relative position cannot be wrong in
    #: it; every other caller passes the door its book and lets the door's
    #: own default stand.
    OUTSIDE_CALLERS_WITH_A_POSITION = (("nonogram/admin/book_proof.py", 767),)

    def test_the_module_axis_bound_is_measured_rather_than_declared(self):
        """AC-4 for the one axis this card leaves open, with its own control.

        This walk parses **one** module, so a position computed elsewhere and
        passed in is outside its enumeration rather than refused by it. That
        is declared, not closed -- closing it would make this a whole-program
        analyser. What is asserted instead is the bound: every geometry-door
        call anywhere in ``src/`` is enumerated, and of the ones outside this
        module, only the listed caller passes a position expression at all.
        A sixth caller, or a non-trivial position in any of the other five,
        reds here. CARD-206 cycle 2 stated this bound; it is re-derived here
        through this test's own walk rather than restated.
        """
        import ast
        from pathlib import Path

        root = Path(__file__).resolve().parents[1] / "src"
        # The slot a position sits in differs per door, so it is read from
        # each door's own signature rather than hard-wired -- writing
        # `args[1:]` here is review cycle 2's F-203 defect exactly, and it
        # made the first draft of this test report nothing.
        own = ast.parse((root.parent / self.MODULE).read_text(encoding="utf-8"))
        slots, slot_refusals = self._door_position_slots(
            own, self.GEOMETRY_DOORS, ""
        )
        assert slot_refusals == [], slot_refusals
        inside, outside, with_position = 0, [], []
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for node in ast.walk(ast.parse(text)):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = (
                    func.attr
                    if isinstance(func, ast.Attribute)
                    else getattr(func, "id", None)
                )
                if name not in self.GEOMETRY_DOORS:
                    continue
                where = str(path.relative_to(root))
                if where == self.MODULE.removeprefix("src/"):
                    inside += 1
                    continue
                outside.append((where, node.lineno))
                slot = slots[name]
                given = [
                    keyword.value
                    for keyword in node.keywords
                    if keyword.arg == self.POSITION_PARAMETER
                ] + ([node.args[slot]] if slot < len(node.args) else [])
                trivial = all(
                    isinstance(expr, ast.Constant)
                    and expr.value in self.POSITION_LITERALS
                    for expr in given
                )
                if given and not trivial:
                    with_position.append((where, node.lineno))

        assert inside == 17, inside
        assert len(outside) == 6, outside
        assert tuple(with_position) == self.OUTSIDE_CALLERS_WITH_A_POSITION, (
            "a module outside the generator now computes a geometry-door "
            "position of its own, which is outside this walk's enumeration "
            f"rather than refused by it: {with_position}"
        )
