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

    **Its bound, stated rather than implied.** This catches the shape the card
    is at risk of — a position derived from the guide that forgot the page in
    front of it — and it is blind to a position written as a bare literal with
    no constant in it at all (a ``first_page = 4`` would satisfy it
    vacuously). That second shape is what
    ``TestBookExport_TitlePageCountedEverywhere``'s monkeypatch case measures
    behaviourally, by moving the constant and re-reading the written file; the
    two together are what cover the claim, and neither does alone.
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
        # The set is not empty, and it is not one site either: the positions
        # the card had to move are the guide's own range, the TOC's page
        # number, `section_plan`'s `first_page`, `first_answer_page`, the two
        # walk defaults and `interior_page_count`'s formula.
        assert len(sites) >= 6, [text for _, _, text in sites]
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
