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
    (CARD-206 review cycle 1, F-102). The walk above visits only the expressions that
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
    2. **DOOR** — which calls are geometry doors (ADR-0036/R2). **Closed on
       callees this walk can anchor to a FIXED POINT over the alias chain**,
       with five named exemptions, each with a reading of its own. The arm
       **defaults to deny** (ADR-0039/R2), and what it denies by default is
       a callee it cannot anchor; a callee it *can* anchor is one whose every
       binding occurrence holds a name or attribute that is itself anchored,
       down to a binding this module's own text shows. What that terminal
       does **not** establish is the identity of what stands there at run
       time, and the sentence that used to be here — *"a geometry door cannot
       stand at such a terminal without being spelled, which the reference
       arm refuses"* — was false: a **decorator** puts an unspelled door at a
       ``def`` (CARD-276 cycle 1's F-2). A decorated definition is therefore
       not a terminal here and the chain onto it refuses; a definition
       rebound where this walk can see no store at all is passed, declared
       as the ``a chain whose terminal is a definition or an import``
       exemption class, and exposed by removing it. CARD-262 closed this
       axis **one step** only and
       declared the rest as the exemption class ``ONE_STEP_ANCHOR`` with six
       silent plants; CARD-276 deleted the class, which cost this module 0
       refusals, and the six plants are W30–W35 of :data:`DOOR_SHAPES`. The
       chain's own bound and its cycle check **refuse and report**
       (:data:`ANCHOR_RESOLUTION_DEPTH`), because a cap is not a closure.

       **Two sentences this axis claimed and no longer claims, kept visible
       beside the correction** — a docstring edited to match the code it was
       meant to constrain is worth nothing, and this axis has now been
       narrowed **four** times by measurement rather than by argument, the
       fourth being CARD-276's own cycle 1:

       - *"Closed on every callee this module's own text binds"* (fix 1).
         FALSE. ``getattr`` installs a door on a name this module's text
         never binds, and one further assignment hides even the bindings it
         does read.
       - *"A call whose callee's identity this walk cannot derive is a
         refusal"* (the pre-code SEMANTICS block, re-asserted as true by fix
         1). FALSE. "Anchored" is a **syntactic** property of one binding
         occurrence, not a derivation of identity: ``_x = getattr(self,
         "page_" + "spec"); _d = _x`` anchors ``_d`` to ``_x`` and the walk
         never follows ``_x``, so appending one assignment to any shape the
         arms refuse buys silence. The counterexample is the cross of this
         class's own rows W1 and W9 — each refuses alone, the cross did
         not — and it reaches the real geometry door with the literal.
         Measured, executed, declared in :data:`MEASURED_BLIND_SPOTS` with
         six siblings, and **narrowed — not closed — by CARD-276**. The fixed
         point made it true of the chain's *length*: the seven rows are
         refusals (W30–W35, plus the call-graph alias row) and so are chains
         two and three links longer. Cycle 1 then falsified it twice more,
         one level further in each time, which is this family's whole
         signature. The first of the two was the **KEY** the chain is keyed
         on, and it had **three vehicles, not one** — which is the correction
         cycle 2 made to the fourth version of this sentence, where this
         clause read *"one of the two is closed"* and counted only the
         vehicle that had been fixed. An attribute is keyed by spelling
         alone, so a resolving occurrence of the spelling skipped the
         own-instance surface rule and silenced a ``setattr``-installed door.
         Two of the three are **closed**: the occurrence in an *unrelated*
         class, by making the attribute branch's ``continue`` conditional on
         a refusal, with no row of :data:`DOOR_SHAPES` switchable off from
         outside itself
         (:meth:`test_no_door_shape_is_laundered_by_an_unrelated_resolving_occurrence`);
         and the spelling *already standing on the class's surface*, which
         was silent with **nothing appended at all** because the authority
         was built with ``ast.walk`` over the ``ClassDef`` and so claimed
         nine names nested inside ``BookPDFGenerator``'s own methods — closed
         by reading the holder's **direct** members, with the control cycle
         2's surviving mutant proved missing
         (:meth:`test_a_name_nested_inside_a_method_is_not_the_classs_attribute_surface`).
         The third is **declared**, not closed, and this card's own fix round
         is what opened the fallback it defeats: a resolving store of the
         same spelling **inside the calling class**, where one line both
         resolves the chain and puts the spelling on the surface, so neither
         condition of the fallback can fail independently
         (:data:`MEASURED_BLIND_SPOTS`' R9).
         The second of the two is **declared** likewise: the chain's terminal
         is read as the ``def``/``class``/``import`` this module's text
         shows, so a decorator at the terminal refuses but a definition
         rebound where this walk sees no store does not (R8). **So the
         sentence is still false** — of that residue, which is **two**
         declared rows and not one, both absorbed by the same named exemption
         class, which has its own step of the measured cost sequence (**0**,
         listed in :data:`CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING`
         and kept only by the blind-spot rows it absorbs) and a lever that
         names it, which is what the deleted ``ONE_STEP_ANCHOR`` had and
         what its deletion left unreplaced. The reason the sentence is kept is that it was
         re-asserted as true three times while it was false, and a reader of
         the fifth version should be able to see what that cost — including
         that the fourth version was itself one of the four, which is why
         this one counts vehicles instead of claiming an axis.

       That polarity is nonetheless the whole of the rest of it: the first
       version
       defaulted to ALLOW — a *positive* table of the bindings it had proved
       opaque, so "every binding occurrence holds a name or attribute" was
       vacuously true of a callee with **no binding occurrence at all** — and
       CARD-262 cycle 1's F-401 measured eight shapes reaching the real door
       through exactly that hole, the plainest of them (``_d =
       book_page_spec``) with no dynamic access in it whatsoever. Two
       closures, and no branch for any idiom (the control for that claim is
       :meth:`test_no_door_axis_arm_branches_on_a_dynamic_access_idiom`):
       the **callee-identity** closure reads every construct in the grammar
       that binds a name — the :data:`BINDERS_READ` store contexts,
       ``def``/``class``/``import``, parameters, and the constructs that hold
       their name as a *string* (``except ... as``, ``match ... as``,
       ``global``) — and refuses any callee it cannot anchor from them,
       including an attribute of this module's own instance that the class
       never spells, which is what a ``setattr`` or ``__set_name__`` install
       leaves behind; and the **door-spelling** closure refuses a
       :data:`GEOMETRY_DOORS` name held in any ``(class, field)`` pair
       outside :data:`DOOR_SPELLINGS_READ`, and a door **imported under
       another name**. Each arm is removable on its own (``door_arms``) and
       each catches a shape the other misses, as an equality per arm
       (:data:`SILENT_WITHOUT_ONE_ARM`). What that per-arm equality does
       **not** say — and what nothing said until CARD-262 cycle 2 — is the
       complement: *no shape escapes both arms*. One did, the cross of W1 and
       W9 was it, and CARD-262 declared the complement as a blind-spot row
       rather than asserting it. CARD-276's fixed point is what makes the
       complement a claim with a control instead:
       :class:`TestDoorAxis_TheNextIndirectionIsNotSilentEither` reads the
       cross, the six declared rows and chains **two** assignments longer,
       and reads the edge too — a chain that resolves must be read and not
       refused, or the closure is a cap. The exemptions are
       :data:`CALLEE_EXEMPTIONS`, each removable through
       ``callee_exemptions``, each with its own step of the measured refusal
       cost (760 → 0 on this module, every remaining step a strict drop) and
       each read twice on its own branch
       (:meth:`test_every_callee_exemption_is_read_twice_on_its_own_branch`).
       What this axis does **not** close is a door that reaches a callee
       through a parameter used as a callee or a ``*args`` forwarder: that is
       axis 5, still open and still declared.
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

    Axes 3, 4 and 5 are open **by declaration**. Each has a control that
    fails: :meth:`test_the_module_axis_bound_is_measured_rather_than_declared`
    for axis 3, and :meth:`test_the_declared_blind_spots_are_still_silent`
    for axes 4 and 5 and for the one axis-2 exemption class that absorbs a
    door-reaching shape, which asserts those shapes **are** silent so the
    bound reds when the code starts catching one — as it did on seven rows
    the moment CARD-276's fixed point landed, which is the whole point of
    writing a bound down that way.

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
        # An equality, not a floor (ADR-0039/R3; CARD-206 review cycle 2, F-201 filed
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
    #: signature, read from the signature rather than written here (CARD-206
    #: review cycle 2, F-203: a hard-wired ``args[0]`` fed ``book_page_spec`` its
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
        cls,
        source=None,
        doors=None,
        follow_terms=False,
        door_arms=None,
        callee_exemptions=None,
    ):
        """``([(line, kind, name, text, literals)], vocabulary, refusals)``.

        ``source`` defaults to the module's own text; a caller may pass one of
        its own — which is how every control below measures this analyser
        without a file on disk being mutated.

        **The reach this walk actually has, in the opening sentence rather
        than fifteen lines further down -- and no longer the word "whole".**
        On the door axis it refuses every ``ast.Call`` whose callee it cannot
        anchor to a **fixed point** over the alias chain, and every
        :data:`GEOMETRY_DOORS` spelling held outside the grammar it reads.
        What it does **not** close is the far side of a chain it *can*
        resolve: a terminal's identity is read off the ``def``, ``class`` or
        ``import`` this module's text shows. A **decorator** puts an
        unspelled door at exactly such a terminal, so a decorated definition
        is not read as one and the chain onto it refuses. Two shapes on that
        far side are **not** reached: a definition rebound where this walk can
        see no store at all -- ``globals()``, a module ``__dict__`` store, an
        importer's monkeypatch -- and a resolving store of the same spelling
        inside the **calling** class, where the store that resolves the chain
        is the store that puts the spelling on the own-instance surface. That
        residue is the ADR-0039/R3 exemption class ``a chain whose terminal is
        a definition or an import``, with one :data:`MEASURED_BLIND_SPOTS` row
        per shape (R8, R9), each read in both directions. This sentence said *"fails closed on the whole door
        axis"* for exactly one commit and was false when it shipped, for the
        third time in this family; the word it is missing now is **whole**.
        The position axis is closed on its **binding occurrences** only. The
        **module**, **value** and **call-graph** axes are open by
        declaration, with :data:`MEASURED_BLIND_SPOTS` and
        :meth:`test_the_module_axis_bound_is_measured_rather_than_declared`
        as their controls, and the door axis keeps five named ADR-0039/R3
        exemption classes, of which two -- an attribute of a receiver this
        module does not define, and the chain terminal above -- absorb a
        door-reaching shape and declare it (rows R3 and R8). The class
        docstring's axis table is the authority on all
        of it and this sentence is a pointer to that table, never a
        substitute for it. On the
        position axis, binding occurrences come from the module's own store
        contexts
        rather than from a list of statement kinds, so every shape a
        **position** can flow through that this walk does not read appends a
        refusal below instead of passing. On the door axis the default is
        **deny**: every ``ast.Call`` is refused unless this walk can
        positively anchor its callee from the constructs in this module's own
        text that bind a name, and no :data:`GEOMETRY_DOORS` name may be
        spelled, or imported under another name, where it cannot read it.
        *"Anchor"* means a fixed point over the alias chain down to a
        terminal this module's text shows, and what it does not establish is
        that terminal's run-time value, which is the one reach stated above
        and declared as an exemption class rather than left to be found a
        sixth time. A
        callee with no binding occurrence at all is therefore refused rather
        than anchored by default, which is cycle 1's F-401 (CARD-262; cycle
        3's F-301 before it).

        **Anchoring is a FIXED POINT** (CARD-276). Two sentences died here
        in turn and both are kept beside the correction, because the
        measurement that falsified each is worth more than the sentence:
        *"closed on every callee this module's own text binds"* — false,
        ``getattr`` installs a door on a name this module's text never binds
        — and *"a call whose callee's identity this walk cannot derive is a
        refusal"*, which was false for as long as "anchored" meant that
        **some binding occurrence of that one name** holds a syntactic
        ``Name`` or ``Attribute``. That says nothing about what the name it
        holds holds, and the walk did not follow it, so one appended
        assignment made any shape the arms refuse silent again — CARD-262
        cycle 2's F-501, declared then as the exemption class
        ``ONE_STEP_ANCHOR`` with six plants asserted silent.

        ``anchored_to_a_fixed_point`` follows the chain instead, which is the
        **level** rather than the instance: anchored only if every binding
        occurrence holds a name or attribute that is itself anchored, down to
        a binding this module's own text shows. The exemption class is
        **deleted**, its six declared plants are refusals and
        :data:`DOOR_SHAPES`' W30--W35, and the chain's own bound and its
        cycle check REFUSE rather than capping
        (:data:`ANCHOR_RESOLUTION_DEPTH`; a cap is not a closure). The class
        docstring's axis table is the authority on all of this.

        ``follow_terms`` removes the one :data:`EXEMPTION`; ``door_arms``
        removes either door-axis closure and ``callee_exemptions`` removes
        any of the five named :data:`CALLEE_EXEMPTIONS`, which is how each
        arm's and each exemption's own reading measures it.

        Three axes stay open by declaration rather than closure, each with
        its own control: the **module** axis (this walk reads one module's
        text), the **value** axis (a position spelled ``0`` or ``1``, or a
        count this walk does not read as an integer) and the **call-graph**
        axis (a position forwarded past a callee resolved by name — narrowed
        but not closed by the fixed point, which refuses an alias chain it
        cannot resolve and says nothing about a parameter used as a callee).
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
        # cannot see the call. Keyed on the node class of the *reference* and
        # no longer on `ast.Attribute` alone -- CARD-262 cycle 1's F-401, half 2: the
        # method door `self.page_spec` had this arm and the **imported** door
        # `book_page_spec` had none, so `_d = book_page_spec` (two real lines
        # with no dynamic access in them at all) was silent. A door's own
        # `def` or `import` statement is not a reference: a FunctionDef's name
        # and an `alias` hold their name as a *string*, so neither is an
        # `ast.Name` and neither reaches here.
        #
        # Which doors the `ast.Name` branch applies to is DERIVED from the
        # module's own text rather than written down: a door reachable as a
        # bare name is one this module binds at module level -- an import or a
        # module-level `def` -- while a door that is a *method* is reachable
        # only as an attribute. The distinction is not cosmetic and it is not
        # a hedge: this module holds ten local variables spelled `page_spec`
        # that carry a PageSpec rather than the door (`page_spec =
        # self._puzzle_page_spec(...)`, then `compute_layout(..., page_spec)`),
        # and keying the branch on the door TABLE instead of on the module's
        # own bindings made all ten refusals -- measured, which is how this
        # was chosen rather than reasoned.
        module_level = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    module_level.add(alias.asname or alias.name.split(".")[0])
        name_doors = tuple(door for door in doors if door in module_level)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in doors:
                spelled = node.attr
            elif isinstance(node, ast.Name) and node.id in name_doors:
                spelled = node.id
            else:
                continue
            above = parent.get(node)
            if isinstance(above, ast.Call) and above.func is node:
                continue
            refusals.append(
                (
                    node.lineno,
                    "a geometry door referenced without being called",
                    spelled,
                    segment(above),
                )
            )

        # ------------------------------------------------------------------
        # The DOOR axis (CARD-262, the SEMANTICS block's axis 2): a call whose
        # callee's identity this walk cannot derive is a REFUSAL. Two closures
        # over the grammar, and no arm *branches* on a dynamic-access idiom --
        # no string constant and no comparison in either closure is
        # `getattr`, `setattr`, `methodcaller`, `attrgetter` or `vars`; the
        # only `getattr` below is Python's own reflection on AST nodes, and
        # each arm catches a shape the other misses.
        #
        # **Default deny** (ADR-0039/R2, and CARD-262 cycle 1's F-401). The first
        # version of this arm built a *positive* table of the bindings it had
        # proved opaque and refused a callee only if it was in that table, so
        # a callee with **no binding occurrence at all** -- an attribute
        # installed by `setattr`, a `match`/`case` capture, an `except ... as`
        # name, a plain alias of an imported door -- was anchored by default,
        # and eight shapes that reach the real geometry door went silent. The
        # hole was the *quantifier*: "every binding occurrence holds a name or
        # attribute" is vacuously true of zero occurrences. So the polarity is
        # inverted: a callee is refused UNLESS this walk can positively anchor
        # it. The classes it cannot anchor on this module are the named
        # ADR-0039/R3 exemptions in :data:`CALLEE_EXEMPTIONS`, each removable
        # on its own (``callee_exemptions``) so that each one's cost is an
        # equality and not a sentence -- the raw inversion costs 760
        # refusals on this module's 816 calls, and the five classes take that
        # to 0.
        # ------------------------------------------------------------------
        if "callee identity" in arms:
            exempt = (
                cls.CALLEE_EXEMPTIONS
                if callee_exemptions is None
                else tuple(callee_exemptions)
            )
            # Every construct in the grammar that binds a name, keyed on
            # (storage, spelling) -- the two storages stay APART, because
            # `text = f"..."` and `draw.text(...)` share a spelling and
            # nothing else, and conflating them cost 51 refusals on a module
            # with no defect in it. The status is what this walk can say about
            # the value bound there, and a construct it cannot read is
            # RECORDED as unreadable rather than skipped: that silent `continue`
            # is what F-401 was.
            bound = {}

            def binding(key, status, line, value, text):
                bound.setdefault(key, []).append((status, line, value, text))

            for node in ast.walk(tree):
                if isinstance(node, (ast.Name, ast.Attribute)):
                    # `ast.Store`, not "not Load": a `del x` *unbinds*, so it
                    # cannot park a door there. Measured -- as refusals the
                    # module's six `del page` statements would have cost
                    # `page.convert(...)` and `page.save(...)`.
                    if not isinstance(getattr(node, "ctx", None), ast.Store):
                        continue
                    key = (
                        ("a local name", node.id)
                        if isinstance(node, ast.Name)
                        else ("an attribute", node.attr)
                    )
                    cursor = node
                    while isinstance(
                        parent.get(cursor), (ast.Tuple, ast.List, ast.Starred)
                    ):
                        cursor = parent[cursor]
                    binder = parent.get(cursor)
                    shape = type(binder).__name__
                    if shape not in cls.BINDERS_READ:
                        binding(
                            key,
                            f"bound in a {shape}, which this walk does not read",
                            node.lineno,
                            None,
                            segment(binder),
                        )
                        continue
                    value = getattr(binder, cls.BINDERS_READ[shape], None)
                    # An annotation-only `AnnAssign` (`field: int`) binds
                    # nothing at run time, so it cannot carry a door.
                    if value is None:
                        continue
                    binding(
                        key,
                        (
                            "anchored"
                            if isinstance(value, (ast.Name, ast.Attribute))
                            else "bound to an expression"
                        ),
                        node.lineno,
                        value,
                        segment(binder),
                    )
                elif isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    binding(
                        ("a local name", node.name),
                        "defined in this module's own text",
                        node.lineno,
                        # The NODE, not None: the terminal rule in
                        # `anchored_to_a_fixed_point` reads its
                        # `decorator_list`, because a decorated definition is
                        # a terminal whose run-time value is not what this
                        # text shows (CARD-276 cycle 1's F-2). `value` is
                        # read nowhere else for this status.
                        node,
                        f"{'class' if isinstance(node, ast.ClassDef) else 'def'} "
                        f"{node.name}",
                    )
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        binding(
                            (
                                "a local name",
                                alias.asname or alias.name.split(".")[0],
                            ),
                            "imported by this module's own text",
                            node.lineno,
                            None,
                            segment(node),
                        )
                elif isinstance(node, ast.arg):
                    binding(
                        ("a local name", node.arg),
                        "a parameter, whose callers are the call-graph axis",
                        node.lineno,
                        None,
                        node.arg,
                    )
                else:
                    # The binding constructs that hold their name as a STRING
                    # and so have no store node for the loop above to find at
                    # all -- which is how five of F-401's eight plants reached
                    # the door. Read by (class, field) rather than one branch
                    # each, so a construct this walk does not read is a
                    # refusal rather than a silent pass.
                    for field, classes in (
                        ("name", (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)),
                        ("rest", (ast.MatchMapping,)),
                    ):
                        spelled = (
                            getattr(node, field, None)
                            if isinstance(node, classes)
                            else None
                        )
                        if spelled:
                            binding(
                                ("a local name", spelled),
                                f"bound in {type(node).__name__}.{field}, which "
                                "this walk does not read",
                                getattr(node, "lineno", 0),
                                None,
                                segment(node),
                            )
                    if isinstance(node, (ast.Global, ast.Nonlocal)):
                        for spelled in node.names:
                            binding(
                                ("a local name", spelled),
                                f"declared {type(node).__name__.lower()}, so this "
                                "walk does not read where it is bound",
                                node.lineno,
                                None,
                                segment(node),
                            )

            # The surface of each class in this module, which is the authority
            # for an attribute callee on this module's OWN instance: the names
            # that class spells as a `def`, in its body, or as a `self.x`
            # store. An attribute this module's own class never spells cannot
            # be anchored by anything this walk can read -- it is an attribute
            # installed from outside the text (`setattr`, `__set_name__`, a
            # metaclass), which is F-401's P1/P5/P8.
            surface = {}
            for holder in [
                node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ]:
                spelled = set()
                for node in ast.walk(holder):
                    if (
                        isinstance(
                            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                        )
                        # A DIRECT member only. `ast.walk` reaches every nested
                        # `def` in every method, and nine such names already
                        # stand inside `BookPDFGenerator` (`produce` in
                        # `interior_stream`; `set_page`, `line_image`,
                        # `technique_rows`, `fits_width` in
                        # `create_guide_page`; `paragraph`, `picture`, `space`,
                        # `technique` in `set_page`). Claiming them as the
                        # class's attribute surface made
                        # `setattr(self, "produce", <a door>)` SILENT with no
                        # scaffolding at all -- cycle 2's F-1, the family's
                        # sixth appearance, and the comment above this loop
                        # already said "in its body" while the code walked
                        # everything. The `self.x` arm below stays broad on
                        # purpose: a store inside a method is how an instance
                        # attribute is really set.
                        and parent.get(node) is holder
                        # NOT also gated on `decorator_list`, and the reason is
                        # a measurement. Cycle 2 observed that `:2295` refuses
                        # a decorated module-level terminal while this arm
                        # admits a decorated method, and that the terminal rule
                        # is therefore applied in one of the two places a
                        # definition is read. True -- but adding `and not
                        # node.decorator_list` here costs this module **4
                        # refusals** on a tree with no defect in it (measured
                        # 2026-10-25; `BookPDFGenerator` has four decorated
                        # methods). By CARD-262's own precedent for choosing a
                        # shape by cost -- one shared opaque table cost 51
                        # refusals where keying on `(storage, spelling)` cost 0
                        # -- a shape that fires on a clean module is the wrong
                        # shape, and it needs either an exemption with its own
                        # control or a different formulation. That is a
                        # successor's decision with a review in front of it,
                        # not a last-mile edit: the narrowing above is free and
                        # closes F-1, and this would not be.
                    ):
                        spelled.add(node.name)
                    elif isinstance(node, ast.Attribute) and isinstance(
                        getattr(node, "ctx", None), ast.Store
                    ):
                        if isinstance(node.value, ast.Name) and node.value.id in (
                            "self",
                            "cls",
                        ):
                            spelled.add(node.attr)
                    elif (
                        isinstance(node, ast.Name)
                        and isinstance(getattr(node, "ctx", None), ast.Store)
                        and isinstance(
                            parent.get(parent.get(node)), ast.ClassDef
                        )
                    ):
                        spelled.add(node.id)
                surface[holder] = spelled

            def enclosing_class(node):
                cursor = parent.get(node)
                while cursor is not None and not isinstance(cursor, ast.ClassDef):
                    cursor = parent.get(cursor)
                return cursor

            class DepthBoundReached(Exception):
                """The receiver resolvers' bound, REPORTED rather than capped.

                `own_instance` capped at `depth > 4 -> return False` and
                `receiver_seen` at `depth > 4 -> return True`: two
                hand-written constants, opposite polarities, both failing
                **open** with no control (CARD-262 cycle 2's F-503 -- five
                aliases of `self` dropped a `setattr`-installed door out of
                the own-instance surface rule and into the external-attribute
                exemption, silently, while the same plant with four aliases
                refused). The pattern this walk already uses 500 lines above
                is the right one: the vocabulary fixed point RAISES when its
                own bound is reached rather than truncating its set. So both
                resolvers raise this, the call loop turns it into a refusal
                naming the call, and the bound costs this module 0 -- an
                equality, not a sentence.
                """

            def own_instance(node, depth=0):
                """Whether this receiver is an instance of a class in *this*
                module's text, so that this module's own class surface is the
                authority for its attributes. `self`, `cls`, and a local ANY
                binding of which is one of them (`_o = self`).

                `any`, not `all`, and that is the fail-closed direction: a
                local bound to `self` in one branch and to an external object
                in another would otherwise fall into the exemption class and
                take `_o._door(...)` with it. It costs this module nothing
                (asserted: the shipped arm's refusal count is 0)."""
                if depth > cls.RECEIVER_RESOLUTION_DEPTH:
                    raise DepthBoundReached("own_instance")
                if not isinstance(node, ast.Name):
                    return False
                if node.id in ("self", "cls"):
                    return True
                return any(
                    status == "anchored" and own_instance(value, depth + 1)
                    for status, _, value, _ in bound.get(("a local name", node.id), ())
                )

            def unreadable(key):
                return [
                    (line, status, text)
                    for status, line, _, text in bound.get(key, ())
                    if status not in ("anchored", "bound to an expression")
                    and not status.startswith(
                        ("a parameter", "defined in", "imported by")
                    )
                ]

            def opaque(key):
                return [
                    (line, status, text)
                    for status, line, _, text in bound.get(key, ())
                    if status == "bound to an expression"
                ]

            def statuses(key):
                return {status for status, _, _, _ in bound.get(key, ())}

            def nearest(found, line):
                """Every site, the one nearest the call first (F-405: the
                first site in `ast.walk` order named an unrelated binding
                2,500 lines from the defect and pointed the reader at it)."""
                return sorted(found, key=lambda site: (abs(site[0] - line), site[0]))

            class AnchorNotAFixedPoint(Exception):
                """The alias resolution's bound and its cycle check, both
                REPORTED rather than capped (CARD-276, G-7).

                The same discipline as :class:`DepthBoundReached` above, for
                the same reason: a resolution that ran out of steps, or went
                round in a circle, is a shape this walk could not analyse,
                which ADR-0039/R2 makes a FAILURE. A cap that returns a
                verdict -- either verdict -- is the fail-open shape CARD-262
                cycle 2's F-503 found twice over, and a cap is not a closure.
                """

            def anchor_key(value):
                """The ``bound`` key a syntactic ``Name``/``Attribute`` points
                at, in the storage it is held in."""
                return (
                    ("a local name", value.id)
                    if isinstance(value, ast.Name)
                    else ("an attribute", value.attr)
                )

            def anchored_to_a_fixed_point(key, depth=0, chain=()):
                """Whether every binding occurrence of ``key`` holds a name or
                attribute that is **itself** anchored, to a fixed point.

                This is CARD-276's whole subject. ``anchored`` was a
                **one-step** syntactic property -- some binding occurrence of
                that one name holds a ``Name`` or an ``Attribute`` -- which
                says nothing about what the name it holds holds, so appending
                one assignment to any shape the arms refuse bought silence
                (CARD-262 cycle 2's F-501, declared then as a bound). The
                remedy a *level* resolves is a fixed point and not a second
                step: the chain is followed until it reaches a binding this
                module's own text shows -- a ``def``, a ``class`` or an
                ``import`` -- or until it reaches something this walk cannot
                see, which is False and a refusal.

                **What a terminal does and does not establish** (CARD-276
                cycle 1's F-2, which falsified the sentence that stood here).
                It read: a ``def``/``class``/``import`` terminal's *"identity
                is therefore visible, and a geometry door cannot stand at
                [it] without being spelled, which the pre-existing reference
                arm refuses"*. A **decorator** does exactly that:
                ``@_mk`` on ``def _deco_door(...)``, where ``_mk`` returns
                ``getattr(sys.modules[__name__], "book_page_" + _S)``, puts
                the real imported door at a ``def`` whose name is assembled
                and never spelled, so the door-spelling arm never sees it. So
                a **decorated** definition is not a fixed point here and the
                chain onto it refuses
                (:data:`TestDoorAxis_TheNextIndirectionIsNotSilentEither.TERMINAL_SHAPES`).
                What is left is **two** shapes, and stating it as one is what
                cycle 2's F-2 falsified in this very paragraph. The first is a
                definition rebound where this walk can see no store at all --
                ``globals()[...]``, a module ``__dict__`` store, an importer's
                monkeypatch -- which no reading of this module's text can tell
                from the ``def`` itself; a rebind it *can* see as a store is
                already refused by the ``opaque`` branch. The second is a
                resolving store of the same spelling **inside the calling
                class**: fix round 1 made the attribute branch's ``continue``
                conditional on a refusal, so a resolved chain falls through to
                the own-instance surface rule instead of past it -- and that
                fallback is defeated by construction exactly there, because
                the store that resolves the chain *is* the store that puts the
                spelling on the surface. Both are the ADR-0039/R3 exemption
                class ``a chain whose terminal is a definition or an import``:
                with it in place a resolved chain passes, with it removed
                **every** resolved chain refuses and names itself, and each
                has its own :data:`MEASURED_BLIND_SPOTS` row -- R8 and R9 --
                read in both directions by
                :meth:`test_the_declared_blind_spots_are_still_silent`. That
                lever is what the deleted ``ONE_STEP_ANCHOR`` class used to
                supply by accident and what its deletion left unreplaced.
                Neither shape is closed by this card; R9 is the one its own
                fix round opened the fallback for, and closing it is a
                successor's.

                A parameter is deliberately **not** a terminal here: its
                callers are the call-graph axis, so a chain that ends in one
                has not been resolved, and saying so is the fail-closed
                direction. It is what refuses the declared R4 and R5 plants.

                Neither the bound nor a cycle returns a verdict: both raise,
                and the call loop turns the raise into a refusal naming the
                call.
                """
                if key in chain:
                    raise AnchorNotAFixedPoint(
                        "whose alias chain closes a cycle, so this walk cannot "
                        "resolve it to a fixed point: "
                        + " -> ".join(spelled for _, spelled in chain + (key,))
                    )
                if depth > cls.ANCHOR_RESOLUTION_DEPTH:
                    raise AnchorNotAFixedPoint(
                        "whose alias chain did not resolve to a fixed point "
                        f"within {cls.ANCHOR_RESOLUTION_DEPTH} steps: "
                        + " -> ".join(spelled for _, spelled in chain + (key,))
                    )
                occurrences = bound.get(key, ())
                if not occurrences:
                    return False
                for status, _, value, _ in occurrences:
                    if status == "anchored":
                        if not anchored_to_a_fixed_point(
                            anchor_key(value), depth + 1, chain + (key,)
                        ):
                            return False
                    elif status == "defined in this module's own text":
                        # A DECORATED definition is not a fixed point: the
                        # decorator replaces what the `def` binds, so the
                        # identity this walk reads off the text is not the
                        # identity at the call. `@_mk def _deco_door(...)`
                        # where `_mk` returns
                        # `getattr(sys.modules[__name__], "book_page_" + _S)`
                        # puts the real imported door at a `def` with its
                        # name assembled, which is cycle 1's F-2, and the
                        # sentence it falsified is kept in this method's
                        # docstring beside the correction.
                        if getattr(value, "decorator_list", None):
                            return False
                    elif status != "imported by this module's own text":
                        return False
                return True

            def anchor_refusal(key, call):
                """The refusal an unresolved alias chain earns, or ``None``
                when the chain reached a fixed point.

                One helper for both storages, because the one-step check was
                written twice and CARD-262's own declaration had to say so --
                blind-spot row R2 was *"the sibling copy of the `anchored`
                check"*, measured silent in the attribute storage alone.
                """
                try:
                    if anchored_to_a_fixed_point(key):
                        return None
                except AnchorNotAFixedPoint as reached:
                    return (
                        call.lineno,
                        f"a callee {reached}, so this walk reports the "
                        "resolution rather than capping it",
                        key[1],
                        segment(call),
                    )
                return (
                    call.lineno,
                    "a callee whose alias chain this walk followed to a name "
                    "it cannot anchor in turn, so it cannot tell whether the "
                    "chain starts at a geometry door",
                    key[1],
                    segment(call),
                )

            def receiver_seen(node, depth=0):
                """Whether this walk can see every construct that binds this
                receiver. A receiver bound where the walk cannot read it may
                hold anything, including a door.

                The bound raises rather than returning ``True`` (F-503): a
                receiver chain this walk did not finish resolving is a shape
                it could not analyse, which ADR-0039/R2 makes a failure."""
                if depth > cls.RECEIVER_RESOLUTION_DEPTH:
                    raise DepthBoundReached("receiver_seen")
                if isinstance(node, ast.Name):
                    key = ("a local name", node.id)
                    if node.id in ("self", "cls"):
                        return True
                    if not bound.get(key):
                        return node.id in frozenset(dir(builtins))
                    return not unreadable(key)
                if isinstance(node, ast.Attribute):
                    return receiver_seen(node.value, depth + 1)
                # A call, a constant, a subscript: an object this module never
                # named, whose attributes are the exemption's own class.
                return True

            for call in calls:
                func = call.func
                if not isinstance(func, (ast.Name, ast.Attribute)):
                    refusals.append(
                        (
                            call.lineno,
                            "a call whose callee is a "
                            f"{type(func).__name__}, so this walk cannot "
                            "tell whether it is a geometry door",
                            type(func).__name__,
                            segment(call),
                        )
                    )
                    continue
                key = (
                    ("a local name", func.id)
                    if isinstance(func, ast.Name)
                    else ("an attribute", func.attr)
                )
                blind = nearest(unreadable(key), call.lineno)
                if blind:
                    line, status, text = blind[0]
                    refusals.append(
                        (
                            call.lineno,
                            f"a callee this walk cannot anchor: {key[0]} "
                            f"{status} at line {line}"
                            + (
                                f" (and {len(blind) - 1} more: "
                                f"{[site[0] for site in blind[1:]]})"
                                if len(blind) > 1
                                else ""
                            ),
                            key[1],
                            text,
                        )
                    )
                    continue
                found = nearest(opaque(key), call.lineno)
                if found:
                    line, _, text = found[0]
                    refusals.append(
                        (
                            call.lineno,
                            f"a callee this walk cannot anchor: {key[0]} bound "
                            f"to an expression at line {line}"
                            + (
                                f" (and {len(found) - 1} more: "
                                f"{[site[0] for site in found[1:]]})"
                                if len(found) > 1
                                else ""
                            )
                            + ", so this walk cannot tell whether it is a "
                            "geometry door",
                            key[1],
                            text,
                        )
                    )
                    continue
                if isinstance(func, ast.Name):
                    # A FIXED POINT, not one step (CARD-276; CARD-262 cycle
                    # 2's F-501 is what made it necessary). What stood here
                    # read the binding occurrence and stopped: a binding
                    # occurrence holding a syntactic name or attribute says
                    # what THAT OCCURRENCE holds and nothing about what the
                    # name it holds holds, so `_x = getattr(self, "page_" +
                    # "spec"); _d = _x` anchored `_d` to `_x` while `_x` --
                    # which this walk did prove opaque -- was never a callee
                    # and so was never consulted. Two sentences died of that
                    # in turn ("closed on every callee this module's own text
                    # binds", then "a door could only have reached it by being
                    # SPELLED"), and the hole moved one level of indirection
                    # each time it was patched. `anchored_to_a_fixed_point`
                    # follows the chain instead, so appending assignments
                    # buys nothing; its bound and its cycle check REFUSE.
                    if "anchored" in statuses(key):
                        blocked = anchor_refusal(key, call)
                        if blocked is not None:
                            refusals.append(blocked)
                        elif (
                            "a chain whose terminal is a definition or an "
                            "import" not in exempt
                        ):
                            # The RESOLVED pass, gated. What stood here was
                            # an ungated silent pass: the one mechanism in
                            # this walk with no exemption class, no cost step
                            # and no control -- which is verbatim what
                            # CARD-262's `ONE_STEP_ANCHOR` docstring recorded
                            # about the hole it inherited, and what deleting
                            # that class left behind (CARD-276 cycle 1's
                            # F-2/F-4).
                            refusals.append(
                                (
                                    call.lineno,
                                    "a callee whose alias chain this walk "
                                    "resolved to a definition or an import "
                                    "in this module's own text, whose "
                                    "run-time value it therefore reads off "
                                    "that terminal",
                                    key[1],
                                    segment(call),
                                )
                            )
                    elif any(
                        status.startswith("a parameter") for status in statuses(key)
                    ):
                        if "parameters" not in exempt:
                            refusals.append(
                                (
                                    call.lineno,
                                    "a callee bound as a parameter, whose "
                                    "callers this walk does not read",
                                    key[1],
                                    segment(call),
                                )
                            )
                    elif statuses(key) & {
                        "defined in this module's own text",
                        "imported by this module's own text",
                    }:
                        if "definitions and imports" not in exempt:
                            refusals.append(
                                (
                                    call.lineno,
                                    "a callee bound by a definition or an "
                                    "import in this module's own text",
                                    key[1],
                                    segment(call),
                                )
                            )
                    elif not bound.get(key):
                        if func.id in frozenset(dir(builtins)):
                            if "builtins" not in exempt:
                                refusals.append(
                                    (
                                        call.lineno,
                                        "a callee that is a builtin and is "
                                        "bound nowhere in this module",
                                        key[1],
                                        segment(call),
                                    )
                                )
                        else:
                            refusals.append(
                                (
                                    call.lineno,
                                    "a callee with no binding occurrence "
                                    "anywhere in this module, so this walk "
                                    "cannot tell whether it is a geometry "
                                    "door",
                                    key[1],
                                    segment(call),
                                )
                            )
                    else:
                        # An `else` that REFUSES, and the only ungated arm of
                        # this branch. The chain above is exhaustive over the
                        # statuses `binding()` can record, so nothing reaches
                        # here on this module (asserted at 0 by
                        # :meth:`test_the_callee_arms_fall_through_refuses_and_costs_nothing`);
                        # a status added to `binding()` without a branch of
                        # its own lands here and refuses. What stood here was
                        # a bare `continue` -- a second, ungated silent pass,
                        # which is why CARD-262 cycle 2's `ME` mutant on the anchored
                        # branch was a NO-OP rather than a survivor: both
                        # paths passed silently.
                        refusals.append(
                            (
                                call.lineno,
                                "a callee whose binding occurrences this walk "
                                "recorded but has no branch for",
                                key[1],
                                segment(call),
                            )
                        )
                    continue
                # The RECEIVER is checked before the attribute is anchored,
                # and the order is load-bearing: `except _Hold as _e:
                # _e.door(...)` reaches the real door while `_Hold.__init__`
                # spells `self.door = door`, so the attribute looks anchored
                # while the receiver is bound by a construct this walk cannot
                # read at all. Anchoring the attribute first made that plant
                # silent -- measured, not reasoned.
                try:
                    seen = receiver_seen(func.value)
                except DepthBoundReached as reached:
                    refusals.append(
                        (
                            call.lineno,
                            "a callee whose receiver this walk did not "
                            f"resolve within {cls.RECEIVER_RESOLUTION_DEPTH} "
                            f"steps ({reached}), so the bound is reported "
                            "rather than capped",
                            key[1],
                            segment(func.value),
                        )
                    )
                    continue
                if not seen:
                    refusals.append(
                        (
                            call.lineno,
                            "a callee whose receiver this walk cannot see "
                            "bound, so this walk cannot tell whether the "
                            "attribute is a geometry door",
                            key[1],
                            segment(func.value),
                        )
                    )
                    continue
                # The same fixed point as the sibling branch above, in the
                # attribute storage: `self._x = getattr(self, "page_" + _S);
                # self._d = self._x` anchored `_d` to `self._x` and stopped,
                # which is CARD-262's declared row R2. One helper serves both
                # branches now, so the two storages cannot drift apart.
                if "anchored" in statuses(key):
                    blocked = anchor_refusal(key, call)
                    if blocked is not None:
                        refusals.append(blocked)
                        # `continue` on a REFUSAL only (CARD-276 cycle 1's
                        # F-1). What stood here continued on either outcome,
                        # so a resolved chain skipped the own-instance
                        # surface rule below -- and an attribute is keyed by
                        # spelling alone, across every receiver, class and
                        # scope. One unrelated resolving occurrence of the
                        # spelling, in a class with nothing to do with the
                        # call, therefore silenced a `setattr`-installed door
                        # on `self`: measured, four shapes, each refused
                        # without that one assignment and silent with it.
                        continue
                    if (
                        "a chain whose terminal is a definition or an import"
                        not in exempt
                    ):
                        refusals.append(
                            (
                                call.lineno,
                                "a callee whose alias chain this walk "
                                "resolved to a definition or an import in "
                                "this module's own text, whose run-time "
                                "value it therefore reads off that terminal",
                                key[1],
                                segment(call),
                            )
                        )
                try:
                    is_own = own_instance(func.value)
                except DepthBoundReached as reached:
                    refusals.append(
                        (
                            call.lineno,
                            "a callee whose receiver this walk did not "
                            f"resolve within {cls.RECEIVER_RESOLUTION_DEPTH} "
                            f"steps ({reached}), so the bound is reported "
                            "rather than capped",
                            key[1],
                            segment(func.value),
                        )
                    )
                    continue
                if is_own:
                    holder = enclosing_class(call)
                    if holder is None or key[1] not in surface.get(holder, ()):
                        refusals.append(
                            (
                                call.lineno,
                                "an attribute of this module's own instance "
                                "that "
                                + (
                                    f"{holder.name} never spells"
                                    if holder is not None
                                    else "no class of this module spells"
                                )
                                + ", so it was installed from outside this "
                                "text and may be a geometry door",
                                key[1],
                                segment(call),
                            )
                        )
                    continue
                if (
                    "an attribute of a receiver this module does not define"
                    not in exempt
                ):
                    refusals.append(
                        (
                            call.lineno,
                            "an attribute of a receiver this module does not "
                            "define, whose attribute surface this walk cannot "
                            "enumerate",
                            key[1],
                            segment(call),
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
            # A door IMPORTED UNDER ANOTHER NAME. `alias.name` holds the door
            # and `alias.asname` holds the name the call site uses, so the
            # door is spelled in a field this walk reads while nothing at the
            # call site names it (CARD-262 cycle 1's Q2 -- and ("alias", "asname") was
            # in :data:`DOOR_SPELLINGS_READ`, so this table whitelisted the
            # exact field through which the rename launders the door past both
            # arms; it is gone from that table too).
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                for alias in node.names:
                    if alias.asname and alias.name.split(".")[-1] in doors:
                        refusals.append(
                            (
                                node.lineno,
                                "a geometry door imported under another name, "
                                "so nothing at the call site spells it",
                                alias.asname,
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
    #: CARD-206 review cycle 2, F-201's own nine shapes (V0–V9) and ten more, each
    #: hiding the literal ``3`` in a page position, with the outcome this walk
    #: must produce: ``"offender"`` when it reads the literal, ``"refusal"``
    #: when it cannot follow the shape and says so. Eight of V1–V9 passed
    #: **silently** before CARD-206 cycle 3's round. V10–V15 are shapes this walk has
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

        CARD-206 review cycle 2, F-203: ``book_page_spec``'s slot used to be
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
    #: ``("alias", "asname")`` is deliberately **absent** (CARD-262 cycle 1's F-401 /
    #: Q2): it used to be here, which whitelisted the one field an
    #: `import ... as` rename needs to carry a door past both arms. A door
    #: *renamed* by an import is refused by the arm's own `alias` clause, and
    #: a door's name standing in an `asname` is refused by this table.
    DOOR_SPELLINGS_READ = (
        ("Attribute", "attr"),
        ("Name", "id"),
        ("FunctionDef", "name"),
        ("AsyncFunctionDef", "name"),
        ("alias", "name"),
        ("arg", "arg"),
        ("keyword", "arg"),
    )

    #: The two door-axis closures, each removable on its own so that
    #: ADR-0039/R1's "caught WITH, missed WITHOUT" can be measured per arm
    #: (:meth:`test_each_door_axis_arm_catches_a_shape_the_other_misses`).
    DOOR_ARMS = ("callee identity", "door spelling")

    #: The callee-identity arm defaults to **deny** (ADR-0039/R2), so the
    #: callee shapes it cannot anchor from this module's own text are named
    #: ADR-0039/R3 **exemptions** rather than silent passes. Each is
    #: removable on its own through ``callee_exemptions``, which is what
    #: makes its cost an equality
    #: (:meth:`test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`)
    #: and what gives each one a reading of its own on its own branch
    #: (:meth:`test_every_callee_exemption_is_read_twice_on_its_own_branch`).
    #: That reference named a per-class "must not absorb" control that
    #: CARD-262's final round **deleted** -- F-502 measured it as certifying
    #: a mechanism that runs before any exemption branch -- and replaced with
    #: :data:`CALLEE_EXEMPTION_REACH` and
    #: :meth:`test_each_door_reaching_shape_is_refused_by_the_mechanism_that_refuses_it`.
    #: The dead name stood here for a whole card: a claim pointing at a
    #: control that does not exist, ADR-0039/R1's own family in kind, and
    #: nothing could tell. Which is why
    #: :meth:`TestGuardProse_EveryNamedControlExists.test_no_docstring_names_a_test_that_does_not_exist`
    #: is a standing check now rather than something somebody notices.
    #: How many steps the two receiver resolvers (``own_instance``,
    #: ``receiver_seen``) follow a chain of local aliases before the bound is
    #: **reported**. It was a hand-written ``4`` inside each resolver, and
    #: each failed OPEN on reaching it -- ``own_instance`` by returning
    #: ``False`` (so five aliases of ``self`` dropped a ``setattr``-installed
    #: door out of the own-instance surface rule and into the
    #: external-attribute exemption) and ``receiver_seen`` by returning
    #: ``True``. Both raise now, the call loop turns that into a refusal, and
    #: the bound's cost on this module is asserted at 0 by
    #: :meth:`test_the_receiver_resolution_bound_is_reported_rather_than_capped`,
    #: which also reads a five-alias plant at two different bounds.
    RECEIVER_RESOLUTION_DEPTH = 4

    #: How many links of an **alias chain** ``anchored_to_a_fixed_point``
    #: follows before the bound is **reported**. Same discipline and same
    #: value as :data:`RECEIVER_RESOLUTION_DEPTH`, and for the same reason
    #: (CARD-262 cycle 2's F-503, extended by CARD-276's G-7): the resolution
    #: raises on reaching it, the call loop turns the raise into a refusal
    #: naming the call, and a chain that closes a **cycle** raises before the
    #: bound can be reached at all. A cap that returned a verdict -- either
    #: verdict -- would be the fail-open shape this board has now filed
    #: twice. Its cost on this module is asserted at 0, and the pair that
    #: measures it (a chain one link past the bound refusing by name, the
    #: same chain one link inside it resolving) is
    #: :meth:`TestDoorAxis_TheNextIndirectionIsNotSilentEither.test_the_anchor_resolution_bound_is_reported_rather_than_capped`.
    ANCHOR_RESOLUTION_DEPTH = 4

    #: CARD-262's fifth exemption class, ``ONE_STEP_ANCHOR`` -- *"a callee
    #: anchored one step and no further"* -- is **gone** (CARD-276 AC-4), not
    #: retired in place. It was the declared pass that made appending one
    #: assignment enough to silence any shape the arms refuse, its own step of
    #: the cost sequence below was **0**, and by this class's own narrowed
    #: rule a class that costs this module nothing is kept only by its
    #: blind-spot rows. ``anchored_to_a_fixed_point`` closes the axis those
    #: rows declared, so the rows left :data:`MEASURED_BLIND_SPOTS` in the
    #: same commit as the mechanism that closes them and the class left all
    #: three of its tables. Deleting it cost this module **0** refusals,
    #: measured, and turned six of its seven declared plants into refusals.
    #:
    #: **There is a fifth class again, and it is not that one back.**
    #: ``ONE_STEP_ANCHOR`` gated a callee by *how far* the chain had been
    #: followed; fix round 1's class gates the **terminal** the chain lands
    #: on, which is where cycle 1 measured the residue. The reason it exists
    #: at all is cycle 1's F-4: deleting ``ONE_STEP_ANCHOR`` on cost was
    #: right and left the silent pass it had been accidentally accounting for
    #: with no lever of its own. See the comment on the member itself.
    CALLEE_EXEMPTIONS = (
        "builtins",
        "definitions and imports",
        "parameters",
        "an attribute of a receiver this module does not define",
        # CARD-276 fix round 1, for cycle 1's F-2 and F-4. The RESOLVED pass
        # was the one mechanism in this walk with no class, no cost step and
        # no control: with the one-step anchor deleted, a callee bound by a
        # `def` was gated by "definitions and imports" while the same callee
        # one alias away was gated by nothing. This class is that lever, at
        # the level the fixed point actually works at -- the terminal, not
        # the step count. Its step is **0** on this module, so it is listed
        # in :data:`CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING` and
        # kept only by the blind-spot row it absorbs, which is the narrowed
        # rule doing its job rather than being vacuous.
        "a chain whose terminal is a definition or an import",
    )

    #: The **refusal cost** of default deny on this module, measured before
    #: the shape was chosen (CARD-262 cycle 1's Critical asked for exactly this
    #: sequence, and the 51 -> 0 measurement is its precedent): the raw
    #: inversion, then the remainder after each exemption class is added, in
    #: this order. **760** distinct refusals with no exemption at all, on a
    #: module of 816 calls with no defect in it, and the five classes take
    #: that to **0** -- which is what says which classes are load-bearing
    #: rather than decorative. The figure counts distinct refusal entries,
    #: which is what the walk returns (identical `(line, shape, name, text)`
    #: tuples are one entry), not calls. Asserted as a sequence of
    #: equalities, so a class that stops being needed (its step no longer
    #: drops) and a class that starts absorbing more than it did both red
    #: here.
    #: **Re-measured end to end by CARD-276**, with CARD-262's fifth class
    #: deleted and the anchor resolved to a fixed point. The sequence is
    #: unchanged through its four inherited steps and the transitive step's
    #: own number is **0**: not one of this module's 816 calls reaches a
    #: callee key with an ``anchored`` binding occurrence at all -- the
    #: ``unreadable`` and ``opaque`` branches run first and catch every one of
    #: them -- so following the chain further cannot refuse what stopping did
    #: not. The number is the deliverable and not a footnote, and it is 0 in
    #: both directions: deleting the class cost 0 and closing the level cost
    #: 0.
    #:
    #: The fifth step is the terminal class added by fix round 1, and it is
    #: **0 for the same measured reason** -- the branch it gates is
    #: unreachable on this module. That is why it is listed in
    #: :data:`CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING`: a class whose
    #: step is 0 is deletable unless it absorbs a declared blind-spot row,
    #: and this one absorbs R8. The alternative was to leave the resolved
    #: pass ungated, which is the accountability hole cycle 1 billed.
    CALLEE_EXEMPTION_COST = (
        ((), 760),
        (("builtins",), 509),
        (("builtins", "definitions and imports"), 203),
        (("builtins", "definitions and imports", "parameters"), 201),
        (
            (
                "builtins",
                "definitions and imports",
                "parameters",
                "an attribute of a receiver this module does not define",
            ),
            0,
        ),
        (CALLEE_EXEMPTIONS, 0),
    )

    #: The classes whose own step of :data:`CALLEE_EXEMPTION_COST` is **0**,
    #: held as an equality. The strict-drop rule -- *a class that costs this
    #: module nothing is a class that is no longer needed* -- is right for a
    #: class that exists to make the shipped module analysable, and CARD-262
    #: **narrowed** it rather than dropping it: a class may cost this module 0
    #: only if it is listed here AND it absorbs at least one row of
    #: :data:`MEASURED_BLIND_SPOTS`. CARD-276 applied that rule to the one
    #: class it kept alive and the tuple was **empty** for one commit, which
    #: made the second half of the narrowed rule vacuous -- stated at the
    #: time rather than left to be discovered.
    #:
    #: It is not vacuous now. Fix round 1 added the terminal class, whose own
    #: step is 0 and which is kept **only** because it absorbs
    #: :data:`MEASURED_BLIND_SPOTS`' R8: delete that row and
    #: :meth:`test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`
    #: reds on the subset assertion, which is the second half of the rule
    #: carrying a claim rather than describing one. The first equality still
    #: reds the moment any *unlisted* class's step is 0.
    CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING = (
        "a chain whose terminal is a definition or an import",
    )

    #: Shapes that reach the real geometry door, with the outcome this walk
    #: must produce. **A regression net over the door shapes measured so
    #: far, never a completeness argument** -- the completeness claim rests
    #: on the closures' own quantifiers (every ``ast.Call``; every
    #: ``(class, field)`` pair), which no table can establish. W0--W3 are
    #: CARD-206 cycle 3's F-301, the four shapes that reached the door with nothing
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
        # W18-W29 are the THIRD author's plants: CARD-262 cycle 1's review, whose
        # eight silent rows (W18-W25) were this card's Critical -- the axis it
        # was sliced out to close was open on every callee with no binding
        # occurrence at all, because the arm's `opaque` table was POSITIVE and
        # "every binding occurrence holds a name or attribute" is vacuously
        # true of none. The plainest of them, W18, uses no dynamic access
        # whatsoever. W26-W29 were already refused in CARD-262 cycle 1 and are here as
        # that fix's regression controls: each must keep refusing, and each
        # refuses for a reason the inverted arm did not change.
        (
            "W18 a plain local alias of the imported door (cycle 1's Q1)",
            """        _d = book_page_spec
        _d(None, 3 + len(section))
        #""",
            "",
            ("refusal",),
        ),
        (
            "W19 the imported door renamed by its own import (cycle 1's Q2)",
            """        _bps(None, 3 + len(section))
        #
        #""",
            "\nfrom nonogram.admin.book_page_spec import book_page_spec as _bps\n",
            ("refusal",),
        ),
        (
            "W20 a module-level rebind of the imported door (cycle 1's Q3)",
            """        _bps2(None, 3 + len(section))
        #
        #""",
            "\n_bps2 = book_page_spec\n",
            ("refusal",),
        ),
        (
            "W21 a setattr-installed attribute door (cycle 1's P1)",
            """        setattr(self, "_door", getattr(self, "page_" + _S))
        self._door(3 + len(section))
        #""",
            '\n_S = "spec"\n',
            ("refusal",),
        ),
        (
            "W22 a match/case capture of an opaque door (cycle 1's P2)",
            """        match [getattr(self, "page_" + _S)]:
            case [_d]:
                _d(3 + len(section))""",
            '\n_S = "spec"\n',
            ("refusal",),
        ),
        (
            "W23 a setattr-installed door on the colliding spelling text (cycle 1's P5)",
            """        setattr(self, "text", getattr(self, "page_" + _S))
        self.text(3 + len(section))
        #""",
            '\n_S = "spec"\n',
            ("refusal",),
        ),
        (
            "W24 a door carried by an except ... as name (cycle 1's P9)",
            """        try:
            raise _Hold(getattr(self, "page_" + _S))
        except _Hold as _e: _e.door(3 + len(section))""",
            '\n_S = "spec"\n\n\nclass _Hold(Exception):\n'
            "    def __init__(self, door):\n        self.door = door\n",
            ("refusal",),
        ),
        (
            "W25 __set_name__ installing the door with setattr (cycle 1's P8)",
            """        self._door(3 + len(section))
        #
        #""",
            '\n_S = "spec"\n\n\nclass _Install:\n'
            "    def __set_name__(self, owner, name):\n"
            '        setattr(owner, "_door", getattr(owner, "page_" + _S))\n',
            ("refusal",),
        ),
        (
            "W26 a door on the class through self.__class__ (cycle 1's P3)",
            """        self.__class__._door = getattr(self, "page_" + _S)
        self.__class__._door(3 + len(section))
        #""",
            '\n_S = "spec"\n',
            ("refusal",),
        ),
        (
            "W27 an opaque door in a local named text (cycle 1's P4)",
            """        text = getattr(self, "page_" + _S)
        text(3 + len(section))
        #""",
            '\n_S = "spec"\n',
            ("refusal",),
        ),
        (
            "W28 a type()-built class attribute door (cycle 1's P6)",
            """        _Dyn = type("_Dyn", (), {"d": None})
        _Dyn.d = getattr(self, "page_" + _S)
        _Dyn.d(3 + len(section))""",
            '\n_S = "spec"\n',
            ("refusal",),
        ),
        (
            "W29 __set_name__ with a spelled store (cycle 1's P7)",
            """        self._door(3 + len(section))
        #
        #""",
            '\n_S = "spec"\n\n\nclass _Install2:\n'
            "    def __set_name__(self, owner, name):\n"
            '        owner._door = getattr(owner, "page_" + _S)\n',
            ("refusal",),
        ),
        # W30-W35 are the FOURTH author's plants, and they arrive here from
        # :data:`MEASURED_BLIND_SPOTS` (CARD-276 AC-3). CARD-262 measured all
        # six silent, absorbed by the one-step anchor, and DECLARED them as a
        # bound with a control asserting that silence. CARD-276's fixed point
        # refuses every one, so the declaration red -- which is what a
        # falsifiable bound is for -- and the rows moved, in the same commit
        # as the mechanism that closes them, into the table that FORBIDS a
        # silent outcome rather than recording one. Their old row ids are
        # kept in the labels so the two tables can be read against each
        # other.
        (
            "W30 the cross of W1 and W9, one appended assignment (R1b)",
            """        _x = getattr(self, "page_" + "spec"); _d = _x
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("refusal",),
        ),
        (
            "W31 an assembled name aliased once (R1)",
            """        _x = getattr(self, "page_" + _S); _d = _x
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n',
            ("refusal",),
        ),
        (
            "W32 the same in the attribute storage (R2)",
            """        self._x = getattr(self, "page_" + _S); self._d = self._x
        self._d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n',
            ("refusal",),
        ),
        (
            "W33 a door held by a constructor parameter (R4)",
            """        _h = _Hold2(getattr(self, "page_" + _S))
        _h.door(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n\n\nclass _Hold2:\n'
            "    def __init__(self, door):\n        self.door = door\n",
            ("refusal",),
        ),
        (
            "W34 a door forwarded as a parameter and aliased once (R5)",
            """        _install(getattr(self, "page_" + _S), 3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        #""",
            '\n_S = "spec"\n\n\ndef _install(door, position):\n'
            "    _d = door\n    _d(position)\n",
            ("refusal",),
        ),
        (
            "W35 a two-step alias chain (R7)",
            """        _x = getattr(self, "page_" + _S); _y = _x; _d = _y
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n',
            ("refusal",),
        ),
    )

    #: The rows of :data:`DOOR_SHAPES` that fall **silent** when both
    #: door-axis closures are removed -- 30 of 36, measured, the six added by
    #: CARD-276 (W30--W35) among them. This is the
    #: "missed WITHOUT" half of ADR-0039/R1 for the door axis as a whole, and
    #: it is an equality rather than a floor so it reds in both directions:
    #: a row that stops falling silent means an arm is carrying it for a
    #: reason this card did not measure, and a new silent row means the
    #: closures lost one. The six rows NOT here -- W4, W6, W11, W17, W18, W20
    #: -- are caught by the PRE-EXISTING, non-removable "door referenced
    #: without being called" arm, and the last two of those are CARD-262 cycle 1's Q1
    #: and Q3, which that arm only catches because it now has an `ast.Name`
    #: branch as well as an `ast.Attribute` one (F-401, half 2).
    SILENT_WITHOUT_THE_DOOR_ARMS = (
        "W0 getattr with a literal door name (F-301's own plant)",
        "W1 getattr with an assembled name",
        "W2 a door through a local string variable",
        "W3 operator.methodcaller",
        "W5 the immediate call of a getattr result",
        "W7 operator.attrgetter",
        "W8 a vars() lookup with an assembled name",
        "W9 a chained alias of a getattr door",
        "W10 a door name taken from a module-level tuple",
        "W12 an attribute-stored getattr door, name never spelled",
        "W13 an attribute-stored door laundered through a helper",
        "W14 a __call__ object on an attribute, wrapping the door",
        "W15 an opaque door bound by a for target",
        "W16 an opaque door bound by a walrus callee",
        "W19 the imported door renamed by its own import (cycle 1's Q2)",
        "W21 a setattr-installed attribute door (cycle 1's P1)",
        "W22 a match/case capture of an opaque door (cycle 1's P2)",
        "W23 a setattr-installed door on the colliding spelling text (cycle 1's P5)",
        "W24 a door carried by an except ... as name (cycle 1's P9)",
        "W25 __set_name__ installing the door with setattr (cycle 1's P8)",
        "W26 a door on the class through self.__class__ (cycle 1's P3)",
        "W27 an opaque door in a local named text (cycle 1's P4)",
        "W28 a type()-built class attribute door (cycle 1's P6)",
        "W29 __set_name__ with a spelled store (cycle 1's P7)",
        "W30 the cross of W1 and W9, one appended assignment (R1b)",
        "W31 an assembled name aliased once (R1)",
        "W32 the same in the attribute storage (R2)",
        "W33 a door held by a constructor parameter (R4)",
        "W34 a door forwarded as a parameter and aliased once (R5)",
        "W35 a two-step alias chain (R7)",
    )

    #: The rows each arm carries ON ITS OWN, measured by removing the other
    #: one: an EQUALITY per arm rather than CARD-262 cycle 1's `assert silent`, which
    #: was a floor the callee arm could have fallen from seventeen rows to one
    #: without reddening (F-403). The division of labour is not symmetric and
    #: it is not decoration: the callee-identity arm carries every door whose
    #: name is never spelled -- assembled at run time, installed by `setattr`,
    #: captured by `match`/`case` or by `except ... as`, **and now every door
    #: behind an alias chain it cannot resolve** -- and the door-spelling arm
    #: carries the one row where the name IS spelled and nothing at the call
    #: site names it: W19's `import ... as` rename, refused by that arm's own
    #: `alias` clause.
    #:
    #: **W9 moved, and the move is the measurement.** Before CARD-276 the
    #: chained alias of a `getattr` door was the door-spelling arm's own row,
    #: silent with the callee arm alone; the fixed point refuses it too, so it
    #: is now carried by BOTH arms and is in neither per-arm list. That is the
    #: equality doing its job in the direction the docstring warns about -- a
    #: row that stops falling silent means an arm's reach moved -- and it
    #: narrows the door-spelling arm's exclusive reach to one row, which is
    #: stated rather than smoothed.
    SILENT_WITHOUT_ONE_ARM = {
        "callee identity": (
            "W1 getattr with an assembled name",
            "W5 the immediate call of a getattr result",
            "W8 a vars() lookup with an assembled name",
            "W12 an attribute-stored getattr door, name never spelled",
            "W13 an attribute-stored door laundered through a helper",
            "W14 a __call__ object on an attribute, wrapping the door",
            "W15 an opaque door bound by a for target",
            "W16 an opaque door bound by a walrus callee",
            "W21 a setattr-installed attribute door (cycle 1's P1)",
            "W22 a match/case capture of an opaque door (cycle 1's P2)",
            "W23 a setattr-installed door on the colliding spelling text (cycle 1's P5)",
            "W24 a door carried by an except ... as name (cycle 1's P9)",
            "W25 __set_name__ installing the door with setattr (cycle 1's P8)",
            "W26 a door on the class through self.__class__ (cycle 1's P3)",
            "W27 an opaque door in a local named text (cycle 1's P4)",
            "W28 a type()-built class attribute door (cycle 1's P6)",
            "W29 __set_name__ with a spelled store (cycle 1's P7)",
            "W30 the cross of W1 and W9, one appended assignment (R1b)",
            "W31 an assembled name aliased once (R1)",
            "W32 the same in the attribute storage (R2)",
            "W33 a door held by a constructor parameter (R4)",
            "W34 a door forwarded as a parameter and aliased once (R5)",
            "W35 a two-step alias chain (R7)",
        ),
        "door spelling": (
            "W19 the imported door renamed by its own import (cycle 1's Q2)",
        ),
    }

    #: The labels of :data:`DOOR_SHAPES`, spelled a second time so the table
    #: can be held to its own labels (F-407, and CARD-206's F-302 before it):
    #: every other assertion over the table reads each row's label on BOTH
    #: sides of its equality, so a row renamed -- or silently replaced by a
    #: different shape under the same name -- was invisible. Written once from
    #: the table and pinned here thereafter; a renamed row now reds.
    DOOR_SHAPE_LABELS = (
        "W0 getattr with a literal door name (F-301's own plant)",
        'W1 getattr with an assembled name',
        'W2 a door through a local string variable',
        'W3 operator.methodcaller',
        'W4 a local alias of the door (refused before this card)',
        'W5 the immediate call of a getattr result',
        'W6 a door out of a dict of callables (refused before this card)',
        'W7 operator.attrgetter',
        'W8 a vars() lookup with an assembled name',
        'W9 a chained alias of a getattr door',
        'W10 a door name taken from a module-level tuple',
        'W11 a conditional door expression (refused before this card)',
        'W12 an attribute-stored getattr door, name never spelled',
        'W13 an attribute-stored door laundered through a helper',
        'W14 a __call__ object on an attribute, wrapping the door',
        'W15 an opaque door bound by a for target',
        'W16 an opaque door bound by a walrus callee',
        'W17 a door in a dict on self, subscript callee',
        "W18 a plain local alias of the imported door (cycle 1's Q1)",
        "W19 the imported door renamed by its own import (cycle 1's Q2)",
        "W20 a module-level rebind of the imported door (cycle 1's Q3)",
        "W21 a setattr-installed attribute door (cycle 1's P1)",
        "W22 a match/case capture of an opaque door (cycle 1's P2)",
        "W23 a setattr-installed door on the colliding spelling text (cycle 1's P5)",
        "W24 a door carried by an except ... as name (cycle 1's P9)",
        "W25 __set_name__ installing the door with setattr (cycle 1's P8)",
        "W26 a door on the class through self.__class__ (cycle 1's P3)",
        "W27 an opaque door in a local named text (cycle 1's P4)",
        "W28 a type()-built class attribute door (cycle 1's P6)",
        "W29 __set_name__ with a spelled store (cycle 1's P7)",
        'W30 the cross of W1 and W9, one appended assignment (R1b)',
        'W31 an assembled name aliased once (R1)',
        'W32 the same in the attribute storage (R2)',
        'W33 a door held by a constructor parameter (R4)',
        'W34 a door forwarded as a parameter and aliased once (R5)',
        'W35 a two-step alias chain (R7)',
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
    def _plant_refusals(cls, body, extra="", **kwargs):
        """The refusals a plant is **answerable for**, and nothing else.

        A reading taken with an exemption class removed cannot be a count of
        the whole module's refusals: removing ``builtins`` costs this module
        251 of its own and removing the external-attribute class 201, so an
        ``== ("refusal",)`` on the module's total is satisfied by the module
        and says nothing about the plant. Attribution instead: the plant's own
        three lines (``_plant`` is line-count-preserving, so they are the
        three lines :data:`DERIVED_POSITION` occupied) plus every line of the
        text the plant appends after the module's end. The module's own 816
        calls are at neither, which is what makes a reading with a class
        removed the plant's.
        """
        from pathlib import Path

        source = (Path(__file__).resolve().parents[1] / cls.MODULE).read_text(
            encoding="utf-8"
        )
        first = source[: source.index(cls.DERIVED_POSITION)].count("\n") + 1
        last = first + len(cls.DERIVED_POSITION.splitlines()) - 1
        own = source.count("\n") + 1
        _, _, refusals = cls._page_positions(cls._plant(body, extra), **kwargs)
        return [
            refusal
            for refusal in refusals
            if first <= refusal[0] <= last or refusal[0] > own
        ]

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
        assert tuple(
            label for label, _, _, _ in self.DOOR_SHAPES
        ) == self.DOOR_SHAPE_LABELS, (
            "a row of DOOR_SHAPES was renamed, or replaced under its own "
            "label: the equality below reads each row's label on both sides, "
            "so nothing in it holds the table to its own labels (F-407)"
        )
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
        # A second node measured under the SHIPPED default, because every
        # other door-axis assertion passes `door_arms=` explicitly and is
        # therefore insensitive to :data:`DOOR_ARMS` -- CARD-262 cycle 1's per-arm
        # attribution found that removing either arm reds exactly ONE node,
        # which made the "caught WITH the arms" half of this axis rest on a
        # single assertion (F-403).
        refusing = [label for label, outcome in measured if "refusal" in outcome]
        assert len(refusing) == len(self.DOOR_SHAPES), (
            "a row of DOOR_SHAPES is no longer refused under the shipped "
            f"DOOR_ARMS: {sorted(set(self.DOOR_SHAPE_LABELS) - set(refusing))}"
        )

    def test_each_door_axis_arm_catches_a_shape_the_other_misses(self):
        """ADR-0039/R1 per arm, in both directions, over the whole table.

        The two closures are not one mechanism written twice. The
        callee-identity arm closes a door whose name is **never spelled** --
        assembled at run time (W1, W5, W8) or taken from data (W10) -- and the
        door-spelling arm closes a door whose name is spelled where nothing at
        the call site names it: W19's `import ... as` rename. So each arm
        still has a row the other leaves silent, which is asserted here rather
        than read off the code, and with **both** arms removed F-301's four
        shapes are silent again -- the "missed WITHOUT" direction stated as a
        reproduction of the finding rather than as a sentence.

        **CARD-276 moved one row and shrank one arm's exclusive reach to a
        single row.** W9's chained alias used to be the door-spelling arm's
        own; the fixed point refuses it as well, so it is carried twice and
        appears in neither list. One row is enough for the per-arm claim and
        the equality is what noticed the move, but it is worth saying plainly:
        if W19's clause were ever deleted, this arm would have nothing left
        that is only its own.
        """
        assert tuple(self.SILENT_WITHOUT_ONE_ARM) == self.DOOR_ARMS, (
            "an arm with no measured per-arm list of its own"
        )
        for arm in self.DOOR_ARMS:
            rest = tuple(a for a in self.DOOR_ARMS if a != arm)
            silent = [
                label
                for label, body, extra, _ in self.DOOR_SHAPES
                if self._outcome(self._plant(body, extra), door_arms=rest) == ()
            ]
            # An EQUALITY and not `assert silent` (F-403): a floor here let the
            # callee arm degrade from the eight rows it carries to one while
            # this control stayed green, which is the floor-where-the-rule-is-
            # an-equality shape AC-5 forbids three lines away.
            assert silent == list(self.SILENT_WITHOUT_ONE_ARM[arm]), (
                f"removing the {arm!r} arm no longer leaves exactly the rows "
                "this card measured silent, so that arm's reach has moved and "
                f"the per-arm claim is out of date: {silent}"
            )

        reproduced = [
            label
            for label, body, extra, _ in self.DOOR_SHAPES
            if self._outcome(self._plant(body, extra), door_arms=()) == ()
        ]
        assert reproduced == list(self.SILENT_WITHOUT_THE_DOOR_ARMS), (
            "with both door-axis arms removed, the rows that fall silent are "
            "no longer the ones this card measured, so either an arm is "
            "carrying a row it did not before or a row has changed shape: "
            f"{reproduced}"
        )
        kept = [
            label
            for label, _, _, _ in self.DOOR_SHAPES
            if label not in self.SILENT_WITHOUT_THE_DOOR_ARMS
        ]
        assert len(kept) == 6, kept

    def test_the_door_axis_arms_reach_every_call_and_refuse_none_of_them(self):
        """The door closure's quantifier and its cost on this module, both
        asserted (ADR-0039/R2, ADR-0039/R3, G-1).

        The completeness claim is the quantifier -- *every* ``ast.Call`` --
        so what is asserted is the partition: every call in the module is
        either a callee this walk anchored or a refusal it named. And the arms
        are **refusal-only**: with them removed the sites and the vocabulary
        are identical, so they change what the guard *sees* and nothing about
        what the module *does*.

        **The traversal is a different one, and that claim is narrowed to
        what is true** (CARD-262 cycle 2's F-506). This test used to call its count a
        *"second, independent walk"*; it was
        ``[node for node in ast.walk(...) if isinstance(node, ast.Call)]`` --
        the analyser's own expression character for character, confirmed by
        unparsing both, so any shared misuse of ``ast.walk`` would have been
        reproduced on both sides. The figure was right and the independence
        claim was not. It is an :class:`ast.NodeVisitor` subclass now, which
        dispatches on node type through ``visit_Call`` and recurses through
        ``generic_visit`` instead of flattening the tree -- a different
        mechanism reaching the same 816, which is what "independent" was
        supposed to mean.
        """
        import ast
        from pathlib import Path

        source = (Path(__file__).resolve().parents[1] / self.MODULE).read_text(
            encoding="utf-8"
        )

        class CallsByVisitor(ast.NodeVisitor):
            """Every ``Call`` by type dispatch rather than by ``ast.walk``."""

            def __init__(self):
                self.calls = []

            def visit_Call(self, node):  # noqa: N802 - NodeVisitor's own name
                self.calls.append(node)
                self.generic_visit(node)

        visitor = CallsByVisitor()
        visitor.visit(ast.parse(source))
        calls = visitor.calls
        flattened = [
            node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
        ]
        # The two traversals must AGREE, and that is the whole value of having
        # two of them. Without this assertion the visitor was decoration:
        # deleting its `generic_visit` recursion -- so that no call nested
        # inside another call's arguments is counted at all -- left both
        # assertions below green, measured as a real SURVIVOR by this round's
        # own kill-instrument run and closed here (N15). Neither figure is
        # pinned to 816 (CARD-262 cycle 1's F-404: an equality there reds on
        # any call added anywhere in 7,000 lines of production code), so a
        # floor and a partition are all they are -- and a floor cannot notice
        # a traversal that stopped traversing. An agreement between two
        # different mechanisms can, and it moves with production rather than
        # against it.
        assert len(calls) == len(flattened), (
            f"the type-dispatching traversal found {len(calls)} calls and the "
            f"flattening one {len(flattened)}: two derivations of one figure "
            "disagree, so one of them is wrong and neither count below can be "
            "read"
        )
        anchored = [
            node
            for node in calls
            if isinstance(node.func, (ast.Name, ast.Attribute))
        ]
        # The denominator is a LOWER BOUND and deliberately not an equality
        # (CARD-262 cycle 1's F-404, accepted). `len(anchored) == len(calls)` alone
        # would be satisfied by a module with no calls at all -- but that
        # degenerate case is already caught four other ways in this class (the
        # 23-site equality, the six-name vocabulary, the seven guide
        # expressions and the module-axis census), while an equality on 816
        # reds on any call added anywhere in 7,000 lines of production code,
        # door call or not. The equality that belongs to this axis is
        # `inside == 17` in
        # :meth:`test_the_module_axis_bound_is_measured_rather_than_declared`,
        # and that one stays an equality.
        assert len(calls) > 500, (
            f"this module holds {len(calls)} calls, so the door closure's "
            "quantifier is being measured over something far smaller than "
            "this module and the figures in the card's notes need re-measuring"
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

    #: Four door-reaching shapes, each **inside** one exemption class's
    #: branch and each refused -- which is worth a regression row. What it is
    #: **not** is a control for those classes, and CARD-262 cycle 2's F-502 measured
    #: why: every one of them is refused by a mechanism that runs **before**
    #: the class's own branch, so removing the class leaves the refusal in
    #: place and the "must NOT absorb" reading cannot fail on its own class.
    #: Two line-count-preserving mutants made the point: widening the
    #: external-attribute class to absorb its whole branch, and the same for
    #: `builtins`, left that test green while the cost sequence went red.
    #: So the table is held to the mechanism that **actually** refuses each
    #: shape, named per row and asserted; the per-class reading moved to
    #: :data:`CALLEE_EXEMPTION_REACH`. A control labelled for mechanism A
    #: while measuring mechanism B is the ADR-0039/R1 defect, and the remedy
    #: is to re-label it, not to keep the label and hope.
    CALLEE_SHAPES_REFUSED_BEFORE_ANY_EXEMPTION = (
        (
            "a builtin name this module rebinds to an opaque door",
            """        vars = getattr(self, "page_" + _S)
        vars(3 + len(section))
        #""",
            '\n_S = "spec"\n',
            "a local name bound to an expression",
        ),
        (
            "the door imported under another name",
            """        _bps(None, 3 + len(section))
        #
        #""",
            "\nfrom nonogram.admin.book_page_spec import book_page_spec as _bps\n",
            "a geometry door imported under another name",
        ),
        (
            "a name this module binds as a parameter and opaquely",
            """        payload = getattr(self, "page_" + _S)
        payload(3 + len(section))
        #""",
            '\n_S = "spec"\n',
            "a local name bound to an expression",
        ),
        (
            "an attribute of this module's OWN instance, installed by setattr",
            """        setattr(self, "_door", getattr(self, "page_" + _S))
        self._door(3 + len(section))
        #""",
            '\n_S = "spec"\n',
            "an attribute of this module's own instance",
        ),
    )

    #: One plant per member of :data:`CALLEE_EXEMPTIONS`, chosen so that it is
    #: refused by **that class's own branch and by nothing earlier** -- the
    #: F-502 remedy. Each is read **twice**: with every class in place the
    #: plant is **silent**, and with this one class removed the plant's own
    #: refusal appears, naming the callee in the row. That is ADR-0039/R3's
    #: "caught with the exemption removed, missed with it in place" measured
    #: on the class rather than on a mechanism that precedes it.
    #:
    #: One of the five reaches the real geometry door (the
    #: external-attribute class's, executed against a recording
    #: ``page_spec``). CARD-262's fifth row, the one-step anchor's, is gone
    #: with the class; fix round 1's terminal row stands in its place, one
    #: level further in -- a chain that **resolves**, silent with the class
    #: and refused without it, which is the reading the deleted class used to
    #: supply and the shipped walk then had for nothing. Its plant is in the
    #: **attribute** storage because the gate is written once per storage and
    #: :data:`MEASURED_BLIND_SPOTS`' R8 reads the local one; a single reading
    #: would have certified one gate and left a mutant on the other with no
    #: cell. The attribute storage therefore carries **both** readings of this
    #: class -- this row, which passes, and R9, the residue cycle 2 measured
    #: there -- so the gate's two directions and its declared hole sit in the
    #: same storage rather than being inferred across them. The other three cannot reach a door, and that is
    #: stated rather than implied: what the ``builtins`` class absorbs is a call to a
    #: **builtin name with no binding occurrence in this module**, and no door
    #: can hide behind one -- asserted below as
    #: ``set(GEOMETRY_DOORS).isdisjoint(dir(builtins))`` rather than argued.
    #: What ``definitions and imports`` and ``parameters`` absorb is a call to
    #: a name this module defines, imports or takes as a parameter; a door
    #: *behind* such a callee is the CALL-GRAPH axis, declared open in
    #: :data:`MEASURED_BLIND_SPOTS`. CARD-262's row R5 said the same of the
    #: `parameters` class's cost of 2 understating its reach; that row is a
    #: refusal now (W34), because the fixed point will not follow an alias
    #: chain into a parameter, so the understatement it recorded is closed in
    #: the one direction a door-axis closure can close it — the class's cost
    #: is still 2 and the call-graph axis is still open.
    CALLEE_EXEMPTION_REACH = (
        (
            "builtins",
            "vars",
            "        vars(toc_page_count)\n        #\n        #",
            "",
        ),
        (
            "definitions and imports",
            "interior_page_count",
            "        interior_page_count(toc_page_count)\n        #\n        #",
            "",
        ),
        (
            "parameters",
            "_cb",
            "        _forward(interior_page_count, toc_page_count)\n"
            "        #\n        #",
            "\n\ndef _forward(_cb, position):\n    return _cb(position)\n",
        ),
        (
            "an attribute of a receiver this module does not define",
            "_door",
            """        _h = _Box(); setattr(_h, "_door", getattr(self, "page_" + _S))
        _h._door(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n\n\nclass _Box:\n    pass\n',
        ),
        (
            # The ATTRIBUTE storage, deliberately. The gate is written once
            # per storage, and a reading taken in the local storage alone
            # certifies one of the two: a mutant on the attribute branch's
            # gate would red nothing. This row is the attribute branch's
            # reading and :data:`MEASURED_BLIND_SPOTS`' R8 is the local
            # branch's, so each gate has one.
            "a chain whose terminal is a definition or an import",
            "_d2",
            """        self._d2 = interior_page_count
        self._d2(toc_page_count)
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
        ),
    )

    def test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost(
        self,
    ):
        """ADR-0039/R2's *"the guard defaults to deny"*, with the price of it
        measured on this module (CARD-262 cycle 1's F-401, and AC-4).

        The first version of this arm was default-ALLOW: a positive table of
        the bindings it had proved opaque, so a callee with no binding
        occurrence at all was anchored by default and eight shapes that reach
        the real geometry door were silent. Inverting the polarity is not free
        and the cost is not a sentence: **760** of this module's 816 calls
        refuse with no exemption in place, on a module with no defect in it.
        What makes that affordable is five named exemption classes, and what
        makes each of them a claim rather than a hedge is this sequence --
        each class removable on its own, its own step in the cost asserted.

        Both directions red. A class that stops being needed no longer drops
        the count, which the strict-drop assertion catches; a class that
        starts absorbing more than it did moves its own step.

        **CARD-276 re-measured the sequence end to end and deleted a class.**
        CARD-262's fifth class, the one-step anchor, had a step of **0**: not
        one of this module's 816 calls reaches a callee key with an
        ``anchored`` binding occurrence at all, so the class its seven plants
        needed bought the shipped module nothing. By this class's own
        narrowed rule that made it deletable, and
        :data:`CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING` was **empty**
        for one commit: the four inherited classes strictly drop the count
        (251, 306, 2, 201), and a class whose step falls to 0 reds here
        rather than being excused. Closing the axis to a fixed point cost 0
        for the same reason, which is stated on
        :data:`CALLEE_EXEMPTION_COST` and asserted by the first equality
        below.

        **Fix round 1 put a fifth class back, and its step is 0.** Cycle 1's
        F-4 measured what the deletion cost: at the fork point a
        ``setattr``-installed door had a lever that *named* the mechanism
        (``ONE_STEP_ANCHOR``), and at HEAD the only surviving single-drop
        lever was ``builtins``, which fires on the plant's own ``getattr``
        call and not on anything that can see a door. A lever that fires on
        an unrelated feature of the plant's text is not accountability. So
        the terminal class gates the **resolved** pass, which is where the
        residue actually is, and the narrowed rule is what keeps it honest:
        it is listed as costing 0 **and** it absorbs R8, so deleting that row
        reds the subset assertion below rather than leaving a 0-cost class
        standing on nothing.
        """
        measured = [
            (
                exemptions,
                len(self._page_positions(callee_exemptions=exemptions)[2]),
            )
            for exemptions, _ in self.CALLEE_EXEMPTION_COST
        ]

        assert measured == [tuple(row) for row in self.CALLEE_EXEMPTION_COST], (
            "the refusal cost of default deny on this module is no longer the "
            f"sequence this card measured: {measured}"
        )
        assert measured[-1] == (self.CALLEE_EXEMPTIONS, 0), (
            "the shipped arm refuses a call in a module with no defect in it, "
            f"so it is not shippable as it stands: {measured[-1]}"
        )
        steps = {
            after[0][-1]: before[1] - after[1]
            for before, after in zip(measured, measured[1:])
        }
        assert tuple(steps) == self.CALLEE_EXEMPTIONS, (
            "every step of the sequence adds exactly one class, in the order "
            f"the classes are declared: {tuple(steps)}"
        )
        assert tuple(
            name for name, step in steps.items() if step == 0
        ) == self.CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING, (
            "an exemption class that costs this module nothing is a class "
            "that is no longer needed, and an unneeded exemption is deleted "
            f"rather than kept: {steps}"
        )
        assert set(self.CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING) <= {
            absorbed_by for _, _, _, absorbed_by, _ in self.MEASURED_BLIND_SPOTS
        }, (
            "a class that costs this module nothing is kept only because it "
            "absorbs a measured silent shape, and this one absorbs no row of "
            "MEASURED_BLIND_SPOTS, so nothing keeps it"
        )

    def test_each_door_reaching_shape_is_refused_by_the_mechanism_that_refuses_it(
        self,
    ):
        """Four door-reaching shapes, refused, and attributed to the right
        mechanism (CARD-262 cycle 2's F-502).

        These were shipped as the four exemption classes' "must-not-absorb"
        controls. They are not: each is refused by a mechanism that runs
        **before** the class's own branch -- the opaque branch for two of
        them, the door-spelling arm's `alias` clause for the import rename,
        and the own-instance surface rule for the `setattr` install -- so
        each certified that mechanism and not the class. Rather than delete
        four door-reaching regression rows, the claim is narrowed to what they
        measure: the shape refuses, **and** the refusal names the mechanism
        this card measured as the one responsible. Deleting any of those four
        mechanisms reds here by name.

        The per-class reading ADR-0039/R3 asks for lives in
        :meth:`test_every_callee_exemption_is_read_twice_on_its_own_branch`.
        """
        measured = []
        for label, body, extra, mechanism in (
            self.CALLEE_SHAPES_REFUSED_BEFORE_ANY_EXEMPTION
        ):
            refusals = self._plant_refusals(body, extra)
            measured.append(
                (
                    label,
                    tuple(sorted({mechanism in shape for _, shape, _, _ in refusals})),
                )
            )

        assert measured == [
            (label, (True,))
            for label, _, _, _ in self.CALLEE_SHAPES_REFUSED_BEFORE_ANY_EXEMPTION
        ], (
            "a door-reaching shape is either no longer refused, or is now "
            "refused by a mechanism other than the one this card attributed "
            f"it to: {measured}"
        )

    def test_every_callee_exemption_is_read_twice_on_its_own_branch(self):
        """ADR-0039/R3 per exemption class, read twice, on the class's own
        branch and not on a mechanism that precedes it (the F-502 remedy).

        With every class in place the plant is **silent**; with that one
        class removed the plant's own refusal appears and names the callee in
        the row. The reading is attributed to the plant
        (:meth:`_plant_refusals`) rather than counted over the module,
        because removing a class costs this module up to 251 refusals of its
        own and a count over the module would be satisfied by those.

        Two of the five plants reach the real geometry door; the three that
        cannot are documented on the table, and the ``builtins`` class's
        soundness is asserted here instead of argued: a geometry door is not
        a builtin name, so a callee with no binding occurrence in this module
        and a builtin's spelling cannot be one.
        """
        import builtins

        assert tuple(
            name for name, _, _, _ in self.CALLEE_EXEMPTION_REACH
        ) == self.CALLEE_EXEMPTIONS, (
            "an exemption class with no reading of its own, which is the "
            "ADR-0039/R1 defect this board has now filed four times"
        )
        assert set(self.GEOMETRY_DOORS).isdisjoint(dir(builtins)), (
            "a geometry door is spelled like a builtin, so the `builtins` "
            "class could absorb a door and its plant is no longer sound"
        )

        measured = []
        for name, callee, body, extra in self.CALLEE_EXEMPTION_REACH:
            rest = tuple(
                other for other in self.CALLEE_EXEMPTIONS if other != name
            )
            with_it = self._plant_refusals(body, extra)
            without = self._plant_refusals(body, extra, callee_exemptions=rest)
            measured.append(
                (
                    name,
                    [shape for _, shape, _, _ in with_it],
                    sorted({named for _, _, named, _ in without}),
                )
            )

        assert measured == [
            (name, [], [callee])
            for name, callee, _, _ in self.CALLEE_EXEMPTION_REACH
        ], (
            "an exemption class no longer reads twice on its own branch: "
            "either its plant is refused with the class in place (so the "
            "class is not what passes it) or removing the class does not "
            f"refuse the plant's own callee (so nothing measures it): {measured}"
        )

    def test_the_receiver_resolution_bound_is_reported_rather_than_capped(self):
        """The two recursion bounds, failing CLOSED, with the pair that
        measures them (CARD-262 cycle 2's F-503).

        ``own_instance`` capped at ``depth > 4 -> return False`` and
        ``receiver_seen`` at ``depth > 4 -> return True``: two hand-written
        constants, opposite polarities, both failing **open**, neither with a
        control. Five aliases of ``self`` plus a ``setattr``-installed door
        was **silent** -- the recursion ran out before it reached ``self``,
        ``own_instance`` returned False, and the call fell into the
        external-attribute exemption. The same plant with **four** aliases
        refused. That is a caught-WITH / missed-WITHOUT pair for the bound
        itself and nothing in the suite contained it.

        Both resolvers raise now and the call loop reports it, exactly as the
        vocabulary fixed point 500 lines above raises when its own bound of
        17 rounds is reached. The readings:

        * the five-alias plant refuses, naming the bound -- it is **not**
          silent and it is not the surface rule's refusal either;
        * the four-alias plant refuses, naming the own-instance surface rule,
          so the deeper plant is not simply being swallowed by the shallower
          rule's shape;
        * read the five-alias plant again with the bound raised past it and
          it refuses on the **surface rule** instead -- so at no bound is
          either plant silent, which is what "fails closed" means here;
        * and the bound costs this module **0** refusals, asserted, which is
          why reporting it rather than capping it was free.

        ``receiver_seen``'s own bound gets its own pair, because the plant
        above exercises only ``own_instance``: a receiver chain five
        attributes deep refuses, naming that resolver, and the same chain
        four deep is silent -- absorbed by the external-attribute class,
        which is the right class for an attribute of an object this module
        never defined. That pair measures the resolver's bound and is not
        claimed to reach a door; the five-alias pair above is the one that
        does (executed against a recording ``page_spec``, called with 5).
        """
        aliases = "        _a = self; _b = _a; _c = _b; _d2 = _c; _e = _d2\n"
        deep = (
            aliases
            + '        setattr(_e, "_door", getattr(self, "page_" + _S));'
            " _e._door(3 + len(section))\n"
            "        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT"
        )
        shallow = (
            "        _a = self; _b = _a; _c = _b; _d2 = _c\n"
            '        setattr(_d2, "_door", getattr(self, "page_" + _S));'
            " _d2._door(3 + len(section))\n"
            "        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT"
        )
        extra = '\n_S = "spec"\n'

        bound = f"did not resolve within {self.RECEIVER_RESOLUTION_DEPTH} steps"
        surface = "an attribute of this module's own instance"

        deep_shapes = [
            shape for _, shape, _, _ in self._plant_refusals(deep, extra)
        ]
        assert [bound in shape for shape in deep_shapes] == [True], (
            "the five-alias plant is no longer refused by the receiver "
            f"resolution bound: {deep_shapes}"
        )

        shallow_shapes = [
            shape for _, shape, _, _ in self._plant_refusals(shallow, extra)
        ]
        assert [surface in shape for shape in shallow_shapes] == [True], (
            "the four-alias plant -- inside the bound -- is no longer refused "
            f"by the own-instance surface rule: {shallow_shapes}"
        )

        original = type(self).RECEIVER_RESOLUTION_DEPTH
        try:
            type(self).RECEIVER_RESOLUTION_DEPTH = original + 4
            raised = [
                shape for _, shape, _, _ in self._plant_refusals(deep, extra)
            ]
        finally:
            type(self).RECEIVER_RESOLUTION_DEPTH = original
        assert [surface in shape for shape in raised] == [True], (
            "with the bound raised past it, the five-alias plant is no longer "
            f"refused by the own-instance surface rule either: {raised}"
        )

        chains = []
        for levels in (5, 4):
            chain = "self." + ".".join("abcde"[:levels])
            chains.append(
                [
                    bound in shape
                    for _, shape, _, _ in self._plant_refusals(
                        f"        {chain}._door(3 + len(section))\n"
                        "        first_answer_page = 1 + TITLE_PAGE_COUNT"
                        " + GUIDE_PAGE_COUNT\n        #"
                    )
                ]
            )
        assert chains == [[True], []], (
            "`receiver_seen`'s own bound no longer reports: a five-deep "
            "receiver chain must refuse naming the bound and a four-deep one "
            f"must not reach it at all, and this measured {chains}"
        )

        _, _, refusals = self._page_positions()
        assert [shape for _, shape, _, _ in refusals if bound in shape] == [], (
            "the receiver resolution bound now costs this module refusals, so "
            "its cost is no longer the 0 this card measured"
        )

    def test_the_callee_arms_fall_through_refuses_and_costs_nothing(self):
        """The arm's last exit, which used to be a bare ``continue``.

        CARD-262 cycle 2's ``ME`` mutant disabled the one-step-anchored pass and
        **nothing changed**: an anchored callee fell through every later
        branch and reached the arm's final ``continue``, which was the same
        silent pass. A mutant that cannot change behaviour is a mutant defect,
        and the defect it was hiding was a second ungated pass. The branch is
        an ``if``/``elif`` chain ending in an ``else`` that **refuses** now,
        so a status added to ``binding()`` without a branch of its own is a
        failure rather than a silent pass -- ADR-0039/R2's default deny
        applied to this walk's own future edits.

        Asserted in both directions a guard can state: the chain is
        exhaustive over the statuses this walk records today, so the
        fall-through costs this module **0** even with every exemption
        removed; and it is reachable code rather than a comment, which is
        what the second assertion reads off this file's own text.
        """
        import ast
        from pathlib import Path

        shape = "has no branch for"
        for exemptions in ((), self.CALLEE_EXEMPTIONS):
            _, _, refusals = self._page_positions(callee_exemptions=exemptions)
            assert [
                entry for entry in refusals if shape in entry[1]
            ] == [], (
                "the callee arm's fall-through refuses on this module, so the "
                "if/elif chain above it is no longer exhaustive over the "
                f"statuses binding() records (exemptions={exemptions})"
            )

        tree = ast.parse(Path(__file__).resolve().read_text(encoding="utf-8"))
        walk = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_page_positions"
        )
        refusing_else = [
            node
            for node in ast.walk(walk)
            if isinstance(node, ast.If)
            and node.orelse
            and not isinstance(node.orelse[0], ast.If)
            and any(
                isinstance(inner, ast.Constant)
                and isinstance(inner.value, str)
                and shape in inner.value
                for statement in node.orelse
                for inner in ast.walk(statement)
            )
        ]
        assert len(refusing_else) == 1, (
            "the callee arm's final `else` no longer appends a refusal, so "
            "the chain's last exit is a silent pass again (CARD-262 cycle 2's ME)"
        )

    #: The idioms CARD-206's three whack-a-mole attempts branched on, held
    #: here for **one** purpose: to prove the derived authority below is wide
    #: enough to cover them. The claim itself is no longer keyed on this
    #: tuple. As five hand-written names consumed by
    #: ``constants.isdisjoint(...)`` it was **inert** -- that assertion passes
    #: for any value of the tuple, including ``()``, so no member had a
    #: control in either direction and a sixth idiom was unconstrained
    #: (CARD-262 cycle 2's F-505, the fourth appearance of that shape on this board
    #: after CARD-206's F-203 on ``GEOMETRY_DOORS``, F-303 on
    #: ``BINDERS_READ`` and F-502's exemption controls). The authority is
    #: ``dir(builtins) + dir(operator)`` -- enumerable by the runtime, which
    #: is what ADR-0039/R2 asks of a guard's set -- and the empty set cannot
    #: satisfy the claim any more, because the authority's own size and its
    #: coverage of these five names are asserted first.
    IDIOMS_THE_AUTHORITY_MUST_HOLD = (
        "getattr",
        "setattr",
        "methodcaller",
        "attrgetter",
        "vars",
    )

    def test_no_door_axis_arm_branches_on_a_dynamic_access_idiom(self):
        """What makes these closures different from CARD-206's three
        whack-a-mole attempts, as a control rather than as prose.

        Cycle 1's F-408: the claim as it was written -- *"the executable arm
        code names none of getattr/setattr/methodcaller/attrgetter/vars"* --
        is false on a literal grep, because ``getattr`` occurs ten times in
        this walk as Python's **own** reflection on AST nodes
        (``getattr(node, "ctx", None)``, ``getattr(binder,
        cls.BINDERS_READ[shape])``) and two comments name the idioms. The
        substantive and checkable claim is the one asserted here: no arm
        branches on the **analysed module's text** naming an idiom, so no
        string constant anywhere in this walk is one of those names and no
        behaviour of it can depend on finding one.

        CARD-262 cycle 2's F-505: *which* names is now **derived** rather than
        written. The set was five hand-written strings consumed by
        ``isdisjoint``, which passes for any value including ``()`` -- an
        inert set with no control in either direction. The authority is
        ``dir(builtins) + dir(operator)``, every attribute-access callable a
        dynamic door could be reached through is in it, and the empty set
        cannot satisfy the claim because the authority's size and its
        coverage of the five idioms the three failed attempts branched on are
        asserted before the disjointness.
        """
        import ast
        import builtins
        import operator
        from pathlib import Path

        tree = ast.parse(Path(__file__).resolve().read_text(encoding="utf-8"))
        walks = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name in ("_page_positions", "_door_position_slots")
        ]
        assert len(walks) == 2, [node.name for node in walks]

        constants = {
            node.value
            for walk in walks
            for node in ast.walk(walk)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }

        authority = set(dir(builtins)) | set(dir(operator))
        assert set(self.IDIOMS_THE_AUTHORITY_MUST_HOLD) <= authority, (
            "the derived authority no longer holds the five idioms CARD-206's "
            "three attempts branched on, so the claim below no longer covers "
            "the shapes it exists for: "
            f"{sorted(set(self.IDIOMS_THE_AUTHORITY_MUST_HOLD) - authority)}"
        )
        assert len(authority) > 200, (
            "dir(builtins) + dir(operator) came back with "
            f"{len(authority)} names, so the authority is not the enumerable "
            "surface this claim is keyed on and the disjointness below would "
            "be satisfied vacuously"
        )
        assert len(constants) > 50, (
            f"only {len(constants)} string constants were found in the two "
            "walks, so the disjointness below is measuring almost nothing"
        )

        assert constants.isdisjoint(authority), (
            "an arm of this walk names a builtin or an `operator` callable as "
            "a string constant, which makes it a branch on an idiom rather "
            "than a closure over the grammar: "
            f"{sorted(constants.intersection(authority))}"
        )

    def test_a_refusal_names_the_binding_the_plant_made(self):
        """A refusal that misnames its site trains readers to ignore it
        (CARD-262 cycle 1's F-405).

        The arm used to keep the FIRST opaque binding found in `ast.walk`
        order, so a door parked in a local named `text` reported the module's
        own unrelated `text = str(page_number)` 4,500 lines away. Every
        binding for the key is reported now, nearest the call first.
        """
        from pathlib import Path

        source = (Path(__file__).resolve().parents[1] / self.MODULE).read_text(
            encoding="utf-8"
        )
        planted = source[: source.index(self.DERIVED_POSITION)].count("\n") + 1
        body = (
            '        text = getattr(self, "page_" + _S)\n'
            "        text(3 + len(section))\n        #"
        )

        _, _, refusals = self._page_positions(
            self._plant(body, '\n_S = "spec"\n')
        )

        named = [shape for _, shape, name, _ in refusals if name == "text"]
        assert named, (
            f"the planted door in a local named `text` is silent: {refusals}"
        )
        assert f"at line {planted}" in named[0], (
            "the refusal for the planted door names a binding other than the "
            f"plant's own at line {planted}, which points the reader away "
            f"from the defect: {named}"
        )

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

    #: The measured bounds of the axes this guard leaves open, each a
    #: shape an **independent** reviewer planted (AC-3) and this walk neither
    #: reads nor refuses. They are asserted to **be** silent, which is what
    #: gives a declared bound a control that can fail in **both** directions
    #: (ADR-0039/R3): a change that starts catching one of these reds here and
    #: forces the bound to be re-measured, instead of leaving a docstring
    #: claiming a reach nobody checked. That is the discipline whose absence
    #: escalated CARD-206 -- the bound is declared, never claimed sound.
    #:
    #: **Seven rows left this table in CARD-276, and the table is what said
    #: so.** Six were the one-step-anchor class's (R1, R1b, R2, R4, R5, R7)
    #: and one was the call-graph axis's alias row; the fixed point reaches
    #: all seven, ``test_the_declared_blind_spots_are_still_silent`` red on
    #: each of them, and they came out in the same commit as the mechanism
    #: that closes them (AC-3) rather than outliving their hole. The six are
    #: :data:`DOOR_SHAPES`' W30--W35 now, where a silent outcome is
    #: forbidden rather than declared; the alias row is
    #: :data:`TestDoorAxis_TheNextIndirectionIsNotSilentEither.CHAINS_THAT_MUST_NOT_BE_SILENT`'s
    #: I7. The call-graph **axis** stays open regardless, and the
    #: parameter-callee row below is what still witnesses it: the door axis's
    #: closure refuses a chain it cannot resolve, which is not the same thing
    #: as resolving the call graph.
    #:
    #: **Three of the six rows have no lever**, and that asymmetry
    #: is stated here rather than papered over: :meth:`_page_positions`
    #: exposes ``doors=``, ``follow_terms=``, ``door_arms=`` and
    #: ``callee_exemptions=`` and nothing for the VALUE or CALL-GRAPH axes, so
    #: those three rows assert silence only, with no "caught with the
    #: mechanism removed" direction. CARD-276 closed neither axis and so built
    #: neither lever; R3's row has one, because an exemption class is what
    #: absorbs it, and fix round 1's R8 and cycle 2's R9 have one for the same
    #: reason -- the same class absorbs both, which is why its reach statement
    #: had to name two shapes instead of one.
    #:
    #: **A lever has to name the mechanism it exposes.** Cycle 1's F-4
    #: measured that a ``setattr``-installed door, silent at the fork point,
    #: was exposed there by dropping ``ONE_STEP_ANCHOR`` -- the class that
    #: named the mechanism -- and at HEAD only by dropping ``builtins``,
    #: which fires because the plant's own three lines call ``getattr``. That
    #: is not accountability for the door axis, and the lesson is recorded
    #: here rather than on the card alone: a row whose only lever is
    #: ``builtins`` has no lever.
    MEASURED_BLIND_SPOTS = (
        (
            "the VALUE axis: the count spelled in ones",
            """        first_answer_page = (
            1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc_page_count + len(section) + 1 + 1 + 1 + 1
        )""",
            "",
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
            "",
            "`module_integers` reads only a top-level `ast.Assign` of a bare "
            "int Constant. The enumeration below is **PARTIAL and bounded by "
            "the mechanism rather than by the list** (cycle 1's F-5: the "
            "first version named three defeaters and omitted a fourth this "
            "card's own body named): anything that is not a top-level "
            "`ast.Assign` of a bare int Constant defeats V15's mechanism. "
            "Measured silent, each planted: an AnnAssign (`_HFM: int = 3`), "
            "`= 1 + 2`, a constant inside an `if` block, "
            "`len(_FRONT_MATTER_PAGES)` and `int(3.0)`. The VALUE axis is "
            "declared open with no lever, so none of them is a silent pass "
            "beyond declaration",
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
            "",
            "a parameter is an `ast.arg`, never a binding occurrence under one "
            "of BINDERS_READ's shapes, so it can never enter the opaque table; "
            "a lambda in the same place IS refused (V13), so the gap is "
            "specifically a nested `def` reached through a parameter",
        ),
        # ------------------------------------------------------------------
        # CARD-262 cycle 2's F-501, DECLARED then and CLOSED now: of the
        # seven shapes a fourth plant author measured silent -- every one of
        # which reaches the real geometry door with the literal-derived
        # position, executed rather than argued -- six were absorbed by the
        # one-step anchor and are refusals under CARD-276's fixed point, so
        # they are :data:`DOOR_SHAPES`' W30--W35 now. The seventh, R3, is
        # absorbed by the external-attribute class, which the fixed point
        # does not touch: it is the honest measurement of that class's real
        # reach and the reason its old "must-not-absorb" control was
        # mis-attributed (F-502), and it stays declared here.
        # ------------------------------------------------------------------
        (
            "the EXTERNAL-ATTRIBUTE class: a setattr install on a receiver "
            "this module does not define (R3)",
            """        _h = _Box(); setattr(_h, "_door", getattr(self, "page_" + _S))
        _h._door(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n\n\nclass _Box:\n    pass\n',
            "an attribute of a receiver this module does not define",
            "W21 with the receiver changed from `self` to any object: "
            "`own_instance` is False, so the own-instance surface rule is "
            "skipped and the call lands in the external-attribute exemption "
            "-- which is exactly the shape that class's old control claimed "
            "it must NOT absorb. It does absorb it. The claim is withdrawn "
            "and the reach declared here instead",
        ),
        # ------------------------------------------------------------------
        # CARD-276 cycle 1's F-2, the half that is DECLARED rather than
        # closed, and fix round 1's answer to F-4: the residue of the
        # resolved pass, with a lever that NAMES its mechanism instead of a
        # `builtins` drop that fires on the plant's own `getattr`.
        # ------------------------------------------------------------------
        (
            "the TERMINAL class: a definition rebound where this walk can "
            "see no store (R8)",
            """        _a = _plain_door; _b = _a
        _b(None, 3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\nimport sys as _sys\n\n\n'
            "def _plain_door(spec, position):\n    return position\n\n\n"
            '_sys.modules[__name__].__dict__["_plain_door"] = getattr(\n'
            '    _sys.modules[__name__], "book_page_" + _S\n'
            ")\n",
            "a chain whose terminal is a definition or an import",
            "the chain resolves onto `def _plain_door`, which this module's "
            "text does show, and the rebind that puts the real imported door "
            "there is a `__dict__` subscript store -- no `ast.Store` on the "
            "name, so no binding occurrence at all. The two neighbouring "
            "shapes ARE refused and that is what bounds this one: a "
            "DECORATED definition is refused by the terminal rule "
            "(TERMINAL_SHAPES), and a rebind this walk can see as a store is "
            "refused by the `opaque` branch (W20). What is left is a rebind "
            "it cannot see, which no reading of this module's text can tell "
            "from the `def` itself",
        ),
        # ------------------------------------------------------------------
        # CARD-276 cycle 2's F-2, DECLARED here rather than closed, and the
        # reason this card's own fix round is implicated in it. Fix round 1
        # made the attribute branch's `continue` conditional on a refusal, so
        # a RESOLVED chain falls through to the own-instance surface rule
        # instead of past it -- and that fallback is defeated by construction
        # whenever the laundering occurrence sits in the CALLING class,
        # because the store that resolves the chain is the store that puts
        # the spelling on the surface. The row is the same exemption class's
        # second shape (R8 is the first), which is what made the class's
        # one-shape reach statement false in three places.
        #
        # RE-MEASURED AGAINST THIS CARD'S OWN HEAD, not inherited from the
        # cycle-2 report: 084fa6d7 narrowed the surface rule's authority to
        # DIRECT members, which is the same mechanism this vehicle travels
        # through, so the reading had to be retaken after it. Silent at both
        # revisions, module cost unchanged (sites=23 vocabulary=6 refusals=0)
        # and all 36 DOOR_SHAPES rows still matching their declared outcomes.
        # ------------------------------------------------------------------
        (
            "the TERMINAL class: a resolving store of the same spelling "
            "inside the CALLING class (R9)",
            """        self._d = interior_page_count
        setattr(self, "_d", getattr(self, "page_" + _S)); self._d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n',
            "a chain whose terminal is a definition or an import",
            "the `setattr` runs after the store, so at run time `self._d` IS "
            "`self.page_spec` and the call reaches the real door with the bare "
            "literal 3. The store that makes the chain resolvable is the same "
            "store that puts `_d` on the class's attribute surface, so the "
            "fallback fix round 1 installed cannot fire: both of its "
            "conditions are met by one line. The ATTRIBUTION CONTROL is what "
            "says this is the resolved pass and not the surface rule in "
            "general -- the same plant with an OPAQUE store refuses before "
            "the anchor is consulted (`self._d = None` and `self._d = 1 + 2` "
            "both give ('refusal',), `self._d = interior_page_count` is "
            "silent) -- and a two-link variant "
            "(`self._y = interior_page_count; self._d = self._y`) is silent "
            "too, so it is the level and not the step count. Exhaustive over "
            "all 32 exemption subsets, 24 expose it and exactly two minimal "
            "sets do: `builtins`, which fires on the plant's own `getattr` "
            "and is therefore no lever, and this class, which yields exactly "
            "one refusal naming its own mechanism. Unlike R8 this shape is an "
            "ATTRIBUTE installed from outside the text under a spelled name "
            "-- territory the surface rule's own comment claims -- so the "
            "class absorbs a shape its reach statement did not name, which is "
            "CARD-262's F-502 pattern and is corrected in all three places "
            "rather than here alone",
        ),
    )

    #: The labels of :data:`MEASURED_BLIND_SPOTS`, spelled a second time for
    #: the same reason as :data:`DOOR_SHAPE_LABELS` (F-407).
    BLIND_SPOT_LABELS = (
        'the VALUE axis: the count spelled in ones',
        'the VALUE axis: an annotated module constant',
        'the CALL-GRAPH axis: a parameter used as a callee',
        'the EXTERNAL-ATTRIBUTE class: a setattr install on a receiver this '
        'module does not define (R3)',
        'the TERMINAL class: a definition rebound where this walk can see '
        'no store (R8)',
        'the TERMINAL class: a resolving store of the same spelling inside '
        'the CALLING class (R9)',
    )

    def test_the_declared_blind_spots_are_still_silent(self):
        """The DECLARED axes' and the declared exemption classes' control
        (AC-4).

        Renamed from ``..._are_still_exactly_these`` (CARD-262 cycle 2's F-504): this
        asserts that the listed shapes **are** silent, which is one real,
        falsifiable direction, and it cannot assert that nothing else is
        silent. *"Exactly these"* said it could, and CARD-262 cycle 2 supplied the
        counterexample -- seven shapes silent and not in the table, on the
        axis the class docstring then called CLOSED. The name claims only
        what the assertions do.

        An honest bound must be **declared, not claimed sound**. Every row
        here was planted by someone who did not write this walk. Asserting
        the silence is what makes the bound falsifiable: narrow the value
        axis, close the call-graph axis or follow the alias chain to a fixed
        point and this reds, naming the row, so the declaration is
        re-measured instead of standing while the code moves underneath it.

        **That is not hypothetical any more.** CARD-276 followed the alias
        chain to a fixed point and this test red on **seven** rows at once --
        six of CARD-262's F-501 rows and the call-graph axis's alias row --
        each of which had been measured silent and reaching the real geometry
        door with a literal-derived position. The rows left the table in the
        same commit as the mechanism that closes them (CARD-276 AC-3), which
        is the behaviour this table exists to force: a declaration must not
        outlive its hole.

        **Read twice where a lever exists.** A row absorbed by a named
        exemption class is read a second time with that class removed, and
        must then produce a refusal **attributable to the plant itself** --
        which is what says the silence is the class's doing and not the
        plant's inertness. R3 has that lever, and so do R8 and R9 -- fix
        round 1's row and cycle 2's, whose shared class gates the resolved
        pass and whose removal refuses every resolved chain by name. The
        other three rows -- two
        VALUE, one CALL-GRAPH -- do **not**: they are open axes rather than
        exemption classes, :meth:`_page_positions` exposes no lever for
        either axis, and CARD-276 closed neither, so it built neither. That
        asymmetry is stated here and on the table rather than papered over
        with a second reading that cannot fail.

        **And a lever has to name the mechanism it exposes.** Cycle 1's F-4
        measured a ``setattr``-installed door whose only surviving
        single-drop lever at ``ced5e648`` was ``builtins`` -- which fires
        because the plant's own three lines call ``getattr``, not because
        anything could see the door. A row whose only lever is ``builtins``
        has no lever, and R8's and R9's is its own class -- for R9 that is
        measured rather than asserted: 24 of the 32 exemption subsets expose
        it, and of the two minimal sets that do, one is ``builtins`` firing on
        the plant's own ``getattr`` and the other is the class itself,
        yielding exactly one refusal that names its own mechanism.

        It is deliberately **not** a row of :data:`DOOR_SHAPES` or
        :data:`PLANTED_SHAPES`: those tables forbid a silent outcome, and a
        blind spot parked in them as expected is the shape ADR-0039/R2
        forbids. A bound lives in its own table, with its own assertion.
        """
        assert tuple(
            label for label, _, _, _, _ in self.MEASURED_BLIND_SPOTS
        ) == self.BLIND_SPOT_LABELS, (
            "a declared blind spot was renamed or replaced under its own "
            "label, which both sides of the equality below read (F-407)"
        )
        assert {
            absorbed_by
            for _, _, _, absorbed_by, _ in self.MEASURED_BLIND_SPOTS
            if absorbed_by
        } <= set(self.CALLEE_EXEMPTIONS), (
            "a row names an absorbing class that is not one of "
            "CALLEE_EXEMPTIONS, so its second reading removes nothing"
        )
        measured = [
            (label, self._outcome(self._plant(body, extra)))
            for label, body, extra, _, _ in self.MEASURED_BLIND_SPOTS
        ]

        assert measured == [
            (label, ()) for label, _, _, _, _ in self.MEASURED_BLIND_SPOTS
        ], (
            "a declared blind spot is no longer silent, so the bound this "
            "guard declares is out of date and the docstring that rests on "
            f"it is claiming the wrong reach: {measured}"
        )

        absorbed = [
            (
                label,
                bool(
                    self._plant_refusals(
                        body,
                        extra,
                        callee_exemptions=tuple(
                            name
                            for name in self.CALLEE_EXEMPTIONS
                            if name != absorbed_by
                        ),
                    )
                ),
            )
            for label, body, extra, absorbed_by, _ in self.MEASURED_BLIND_SPOTS
            if absorbed_by
        ]

        assert absorbed == [
            (label, True)
            for label, _, _, absorbed_by, _ in self.MEASURED_BLIND_SPOTS
            if absorbed_by
        ], (
            "a row declared as absorbed by an exemption class is still silent "
            "with that class removed, so either the class is not what absorbs "
            f"it or the plant reaches no call at all: {absorbed}"
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
        # `args[1:]` here is CARD-206 review cycle 2's F-203 defect exactly, and it
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

        # 17 is settled, and the reconciliation is recorded here so no later
        # card re-opens it: the counting rule is one `ast.Call` whose callee
        # names a door, with nothing in a comment, a docstring or a string
        # literal counted. The generator holds 17 such CALLS plus exactly one
        # door DEFINITION -- `def page_spec` at `book_pdf_generator.py:4036` --
        # and 17 + 1 = 18 is CARD-206 cycle 2's figure, which counted door-name
        # occurrences in callee-ish position. Under the stated rule 17 is
        # right; CARD-262 cycle 1's review re-derived both independently.
        assert inside == 17, inside
        assert len(outside) == 6, outside
        assert tuple(with_position) == self.OUTSIDE_CALLERS_WITH_A_POSITION, (
            "a module outside the generator now computes a geometry-door "
            "position of its own, which is outside this walk's enumeration "
            f"rather than refused by it: {with_position}"
        )


# --------------------------------------------------------------------------
# CARD-276 — the door axis's anchor is a FIXED POINT, so the next
# indirection is not silent either
# --------------------------------------------------------------------------

#: The guard this class measures. Named rather than inherited on purpose: a
#: subclass would re-collect every one of that class's own tests, and this
#: file's guard class is already 95 % of its wall clock.
_GUARD = TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage

#: Every planted body whose text would not parse, so a derivation over the
#: plant tables cannot swallow a row (an error is a third thing, neither a
#: failure nor a pass, and a ``SyntaxError`` at import time would be a
#: collection error attributed to nothing).
_UNPARSED_PLANT_BODIES: list[str] = []


def _attribute_callee_laundering(body):
    """An unrelated class that resolves the alias chain of every
    **attribute** callee ``body`` spells, derived from the plant's own text.

    This is CARD-276 cycle 1's F-1 turned into an instrument. ``bound`` and
    ``anchor_key`` key an attribute as ``("an attribute", node.attr)`` --
    spelling alone, across every receiver, class and scope -- so one
    assignment of that spelling, anywhere in the module, used to make the
    attribute branch's ``continue`` skip the own-instance surface rule. The
    laundering text is deliberately in a class with nothing to do with the
    call: its only connection to the plant is the spelling.

    Returns ``""`` for a body with no attribute callee. The local-name
    storage has no analogue -- a bare local callee with no local binding
    other than a module-level resolving one *is* that resolved value, and the
    ``global``/``nonlocal`` routes are recorded unreadable and refuse -- so
    those rows are the ones the equality below excludes by name.
    """
    import ast
    import textwrap

    try:
        tree = ast.parse(textwrap.dedent(body))
    except SyntaxError:
        _UNPARSED_PLANT_BODIES.append(body)
        return ""
    spelled = sorted(
        {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
    )
    if not spelled:
        return ""
    return "\n\nclass _UnrelatedResolver:\n    def __init__(self):\n" + "".join(
        f"        self.{name} = interior_page_count\n" for name in spelled
    )


class TestDoorAxis_TheNextIndirectionIsNotSilentEither:
    """CARD-276 AC-1: the **level**, not the instance.

    Four gating findings on this board share one sentence — *the guard keeps
    claiming a reach it has not measured* — and each time the hole moved
    exactly **one level of indirection**: a list of shapes, then a storage,
    then a quantifier over an empty set, then one step of alias resolution.
    CARD-262 measured and declared the fourth: ``anchored`` held when *some*
    binding occurrence of one name held a syntactic ``Name``/``Attribute``,
    and the walk never followed the alias, so **appending one assignment to
    any shape the arms refuse bought silence**.

    The remedy a level resolves is a fixed point, not a second step, and the
    control for *that* is a chain the next card's counterexample would have
    to be longer than. So every row of
    :data:`CHAINS_THAT_MUST_NOT_BE_SILENT` is the same door reached through a
    chain of **two or more** further assignments, in both storages and across
    them, and each must be read or refused and never silent.

    What stops that from being the blanket refusal of every anchored callee —
    which would close the same counterexamples and be a *cap*, not a closure
    (G-7) — is :data:`CHAINS_THAT_RESOLVE`, the edge of the claim: a chain
    whose terminal **is** a binding this module's own text shows resolves, so
    the fixed point passes it. Both directions are measured here, so a mutant
    that refuses everything reds as loudly as one that refuses nothing.

    **Cycle 1 then found the level again, twice, one indirection further in
    each time.** This class holds the answer for the TERMINAL one and for
    **two of the KEY one's three vehicles** -- not "both answers", which is
    what it claimed until cycle 2 measured the third and found it silent with
    nothing appended. The correction is recorded here rather than quietly
    widened, because the claim being wider than the controls is this card's
    whole subject.

    The KEY the chain is keyed on: an attribute is keyed by spelling alone, so
    a resolving occurrence silenced a ``setattr``-installed door --
    :data:`SURFACE_SHAPES_LAUNDERED` and
    :meth:`test_no_door_shape_is_laundered_by_an_unrelated_resolving_occurrence`,
    which also reads every attribute-callee row of
    :data:`TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage.DOOR_SHAPES`
    so no row can be switched off from outside it. That is the
    unrelated-class vehicle. The class-surface vehicle is the second, answered
    by the direct-member authority and
    :meth:`test_a_name_nested_inside_a_method_is_not_the_classs_attribute_surface`
    below. The third -- a resolving store of the same spelling inside the
    **calling** class -- is answered **not at all**, and
    :data:`TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage.MEASURED_BLIND_SPOTS`'
    R9 declares it instead.

    And the TERMINAL the chain lands on: the sentence *"a door cannot stand at
    a ``def`` terminal without being spelled"* was false, because a decorator
    can -- :data:`TERMINAL_SHAPES`. What is left of that second one is a
    definition rebound where this walk can see no store at all, which is
    **declared** (R8), with a lever that names its own mechanism rather than
    one that fires on the plant's ``getattr``.
    """

    #: One row per indirection shape, each reaching the module's real geometry
    #: door through an alias chain the one-step anchor passed. A regression net
    #: over the shapes measured, never a completeness argument: the
    #: completeness claim is the fixed point's own quantifier (*every* binding
    #: occurrence, *to a fixed point*), and these rows are what says the
    #: quantifier is the one running.
    CHAINS_THAT_MUST_NOT_BE_SILENT = (
        (
            "I1 the cross of W1 and W9, one appended assignment (the card's own)",
            """        _x = getattr(self, "page_" + "spec"); _d = _x
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
        ),
        (
            "I2 TWO further assignments, local storage (the next indirection)",
            """        _x = getattr(self, "page_" + "spec"); _y = _x; _z = _y; _d = _z
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
        ),
        (
            "I3 TWO further assignments, attribute storage",
            """        self._x = getattr(self, "page_" + _S); self._y = self._x; self._z = self._y
        self._z(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n',
        ),
        (
            "I4 a chain that crosses the two storages",
            """        _x = getattr(self, "page_" + _S); self._y = _x; _d = self._y
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n',
        ),
        (
            "I5 two further assignments past a constructor parameter (R4 + 2)",
            """        _h = _Hold(getattr(self, "page_" + _S)); _m = _h.door; _d = _m
        _d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n\n\nclass _Hold:\n'
            "    def __init__(self, door):\n        self.door = door\n",
        ),
        (
            "I6 two further assignments past a forwarded parameter (R5 + 2)",
            """        _install(getattr(self, "page_" + _S), 3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        #""",
            '\n_S = "spec"\n\n\ndef _install(door, position):\n'
            "    _d = door\n    _e = _d\n    _f = _e\n    _f(position)\n",
        ),
        (
            "I7 the alias of a non-door position method, aliased twice more",
            """        _f = self.puzzle_pages; _g = _f; _h = _g
        _h([], 3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
        ),
    )

    #: The **edge** of the fixed point's claim, and the reason a blanket
    #: refusal of every anchored callee would red here (ADR-0039/R1: a mutant
    #: inside the claimed region and a mutant at its edge). A chain whose
    #: terminal is a ``def`` or an ``import`` in this module's own text is
    #: resolved rather than refused, because the terminal's own identity is
    #: visible — and a **door** at such a terminal is spelled, so the
    #: pre-existing "door referenced without being called" arm refuses it.
    #: Each row carries the plant's expected refusal shapes, so a row that
    #: starts refusing for a new reason reds rather than drifting.
    CHAINS_THAT_RESOLVE = (
        (
            "E1 a four-link chain onto a module-level def",
            """        _a = interior_page_count; _b = _a; _c = _b; _d2 = _c
        _d2(toc_page_count)
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            (),
        ),
        (
            "E2 the same chain onto an imported name",
            """        _a = book_page_spec; _b = _a; _c = _b; _d2 = _c
        _d2(None, toc_page_count)
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            ("a geometry door referenced without being called",),
        ),
        (
            # The edge of FIX 1 as well as of the fixed point. E1 and E2 are
            # both in the LOCAL-name storage, so a cap in the attribute
            # branch -- refuse every anchored attribute callee -- closed
            # every counterexample and red nothing. This row is an attribute
            # callee whose chain resolves AND whose spelling the calling
            # class spells, so the surface rule passes it: a cap reds here,
            # and so does a surface rule that stops reading its own class.
            "E3 an attribute callee the calling class spells, onto a "
            "module-level def",
            """        self._d2 = interior_page_count
        self._d2(toc_page_count)
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            "",
            (),
        ),
    )

    #: CARD-276 cycle 1's **F-1**, the Critical: a geometry door installed on
    #: ``self`` from outside this module's text, reached with a bare literal
    #: page position, refused by the own-instance surface rule -- and
    #: **silent** the moment one unrelated assignment of the same spelling
    #: resolved the alias chain. One occurrence, in a class with nothing to
    #: do with the call, was the whole difference.
    #:
    #: Each row is read **twice**, without its laundering text and with it,
    #: because a row that stopped reaching a call at all would satisfy a
    #: single "refuses" assertion for the wrong reason. At ``ced5e648`` the
    #: pair read ``('refusal',)`` then ``()``; both are ``('refusal',)``.
    #:
    #: Cycle 1 named four shapes. Its B1 **is** :data:`DOOR_SHAPES`' W25 and
    #: A2's near-twin is W21, so both are laundered over there instead, by
    #: :meth:`test_no_door_shape_is_laundered_by_an_unrelated_resolving_occurrence`
    #: -- which found a **third** row the finding did not name (W23, the
    #: colliding ``text`` spelling) and found that **W29 is not launderable
    #: at all**: its installer's store is *spelled*, so the ``opaque`` branch
    #: refuses it before the anchor is consulted, with or without a resolving
    #: occurrence. Cycle 1 and the fix brief both named W29 as the switchable
    #: row; the measurement says W25. S1 here is the Critical's own plant,
    #: kept under its own id, and S2/S3 are the two shapes with no
    #: :data:`DOOR_SHAPES` row anywhere.
    SURFACE_SHAPES_LAUNDERED = (
        (
            "S1 a setattr-installed door on self (cycle 1's own plant A2)",
            """        setattr(self, "_d", getattr(self, "page_" + "spec"))
        self._d(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '\n_S = "spec"\n',
        ),
        (
            "S2 a metaclass __getattr__ returning the door (cycle 1's B2)",
            """        self._d(3 + len(section))
        #
        #""",
            '\n_S = "spec"\n\n\nclass _Meta(type):\n'
            "    def __getattr__(cls, name):\n"
            '        return getattr(cls, "page_" + _S)\n',
        ),
        (
            "S3 a __getattr__ installed by setattr (cycle 1's B3)",
            """        self._d(3 + len(section))
        #
        #""",
            '\n_S = "spec"\n\n\ndef _fallback(self, name):\n'
            '    return getattr(self, "page_" + _S)\n\n\n'
            'setattr(BookPDFGenerator, "__getattr__", _fallback)\n',
        ),
    )

    #: CARD-276 cycle 1's **F-2**: a decorator puts the real imported door at
    #: a ``def`` terminal with its name assembled, so the chain resolves and
    #: the door-spelling arm never sees it. The sentence that made passing a
    #: resolved chain safe -- *"a geometry door cannot stand at such a
    #: terminal without being spelled"* -- was false, and these rows are what
    #: says it is no longer: a decorated definition is not a terminal and the
    #: chain onto it refuses.
    #:
    #: The **edge** is :data:`CHAINS_THAT_RESOLVE`: refusing every definition
    #: terminal would close both of these rows and reds E1 and E3, which is
    #: what tells the terminal rule from a cap. What the rule does **not**
    #: reach is a definition rebound where this walk can see no store at all,
    #: declared as row R8 of
    #: :data:`TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage.MEASURED_BLIND_SPOTS`,
    #: with a lever that names its own class.
    TERMINAL_SHAPES = (
        (
            "T1 a decorator putting the imported door at a `def` terminal",
            """        _a = _deco_door; _b = _a
        _b(None, 3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '_S = "spec"\nimport sys as _sys\n\n'
            "def _mk(f):\n"
            '    return getattr(_sys.modules[__name__], "book_page_" + _S)\n\n'
            "@_mk\ndef _deco_door(spec, position):\n    return position\n",
        ),
        (
            "T2 the same decorator returning a class-attribute door",
            """        _a = _cls_door; _b = _a
        _b(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT""",
            '_S = "spec"\n\n'
            "def _mk2(f):\n"
            '    return getattr(BookPDFGenerator, "page_" + _S)\n\n'
            "@_mk2\ndef _cls_door(position):\n    return position\n",
        ),
    )

    #: The rows of :data:`DOOR_SHAPES` the laundering derivation reaches,
    #: spelled here so a row that gains or loses an attribute callee reds
    #: rather than silently leaving the reading. Derived from the table by
    #: ``ast``, held to this equality: ADR-0039/R2's "the set comes from an
    #: enumerable authority" with the authority named and the derivation's
    #: own residue (the 22 rows with no attribute callee) stated rather than
    #: skipped quietly.
    LAUNDERABLE_DOOR_SHAPES = tuple(
        label
        for label, body, _, _ in _GUARD.DOOR_SHAPES
        if _attribute_callee_laundering(body)
    )

    LAUNDERABLE_DOOR_SHAPE_LABELS = (
        "W3 operator.methodcaller",
        "W7 operator.attrgetter",
        "W12 an attribute-stored getattr door, name never spelled",
        "W13 an attribute-stored door laundered through a helper",
        "W14 a __call__ object on an attribute, wrapping the door",
        "W21 a setattr-installed attribute door (cycle 1's P1)",
        "W23 a setattr-installed door on the colliding spelling text "
        "(cycle 1's P5)",
        "W24 a door carried by an except ... as name (cycle 1's P9)",
        "W25 __set_name__ installing the door with setattr (cycle 1's P8)",
        "W26 a door on the class through self.__class__ (cycle 1's P3)",
        "W28 a type()-built class attribute door (cycle 1's P6)",
        "W29 __set_name__ with a spelled store (cycle 1's P7)",
        "W32 the same in the attribute storage (R2)",
        "W33 a door held by a constructor parameter (R4)",
    )

    @pytest.mark.parametrize(
        "label,body,extra",
        CHAINS_THAT_MUST_NOT_BE_SILENT,
        ids=[row[0].split()[0] for row in CHAINS_THAT_MUST_NOT_BE_SILENT],
    )
    def test_a_chain_of_any_length_is_read_or_refused_and_never_silent(
        self, label, body, extra
    ):
        """AC-1, parametrised so each chain is its own node id.

        One ``FAILED`` line on a stacked assertion says nothing about the arms
        that never ran, and this is the table where a per-row reading is the
        whole point: the defect family is *one* shape going silent, not all of
        them.
        """
        assert _GUARD._outcome(_GUARD._plant(body, extra)) == ("refusal",), (
            f"{label} is silent: the alias chain was followed one step and "
            "stopped, which is this family's fifth appearance"
        )

    @pytest.mark.parametrize(
        "label,body,extra,shapes",
        CHAINS_THAT_RESOLVE,
        ids=[row[0].split()[0] for row in CHAINS_THAT_RESOLVE],
    )
    def test_a_chain_whose_terminal_this_module_shows_is_resolved_not_refused(
        self, label, body, extra, shapes
    ):
        """The edge of the claim, which a cap cannot satisfy (G-7).

        A fixed point that refuses every anchored callee closes every row of
        :data:`CHAINS_THAT_MUST_NOT_BE_SILENT` and is not a closure at all.
        These three rows are what tells the two apart: the chain's terminal is
        an **undecorated** ``def`` or an ``import``, and the anchored branch
        therefore **passes** it. E2's door is refused by the pre-existing
        reference arm rather than by the anchor, and that attribution is
        asserted rather than argued.

        **What passing a resolved chain is NOT.** It used to be documented
        here as *safe*, on the ground that a door at such a terminal would
        have to be spelled; cycle 1's F-2 falsified that with a decorator and
        the rows are now split three ways rather than two. A **decorated**
        terminal refuses
        (:data:`TERMINAL_SHAPES`); an undecorated one passes, which is these
        rows; and what the pass still cannot see -- a definition rebound where
        this walk finds no store -- is declared, absorbed by the
        ``a chain whose terminal is a definition or an import`` exemption
        class, and read in both directions by
        :meth:`test_the_declared_blind_spots_are_still_silent`. E3 is in the
        **attribute** storage on purpose: E1 and E2 are both local names, so a
        cap in the attribute branch would have closed every counterexample in
        this class and red nothing.
        """
        measured = sorted(
            {shape for _, shape, _, _ in _GUARD._plant_refusals(body, extra)}
        )
        assert measured == sorted(shapes), (
            f"{label} no longer refuses exactly what this card measured: the "
            "fixed point is either refusing a chain it resolved (a cap, not a "
            f"closure) or passing a door: {measured}"
        )

    @pytest.mark.parametrize(
        "label,body,extra",
        SURFACE_SHAPES_LAUNDERED,
        ids=[row[0].split()[0] for row in SURFACE_SHAPES_LAUNDERED],
    )
    def test_a_door_installed_from_outside_the_text_survives_one_resolving_occurrence(
        self, label, body, extra
    ):
        """CARD-276 cycle 1's F-1, the Critical, parametrised per shape.

        The attribute branch's ``continue`` used to fire on either outcome of
        the fixed point, so a **resolved** chain skipped the own-instance
        surface rule rather than falling through to it -- and an attribute is
        keyed by spelling alone, so one unrelated occurrence of the spelling
        anywhere in the module resolved it. Both readings are in one equality
        on purpose: a row that stops reaching a call at all would satisfy a
        bare "it refuses" for the wrong reason, and the pair is what makes
        the laundering the thing under measurement.
        """
        bare = _GUARD._outcome(_GUARD._plant(body, extra))
        laundered = _GUARD._outcome(
            _GUARD._plant(body, extra + _attribute_callee_laundering(body))
        )
        assert (bare, laundered) == (("refusal",), ("refusal",)), (
            f"{label}: a geometry door installed on `self` from outside this "
            "module's text is read differently with one unrelated assignment "
            "of its spelling appended, which is cycle 1's F-1 -- the pair is "
            f"{(bare, laundered)}"
        )

    def test_a_name_nested_inside_a_method_is_not_the_classs_attribute_surface(self):
        """CARD-276 cycle 2's F-1 — the family's **sixth** appearance, closed.

        FIX 1 made the own-instance surface rule load-bearing: a chain the
        fixed point *resolves* now falls through to it instead of past it. But
        that rule's authority was built with ``ast.walk`` over the ``ClassDef``,
        so **every nested ``def`` in every method** was claimed as part of the
        class's attribute surface — while the comment above the loop already
        said "the names that class spells as a ``def``, **in its body**". The
        claim and the code disagreed, in the one mechanism the fix had just
        made load-bearing.

        **Nine such names already stand inside ``BookPDFGenerator``** —
        ``produce`` in ``interior_stream``; ``set_page``, ``line_image``,
        ``technique_rows``, ``fits_width`` in ``create_guide_page``;
        ``paragraph``, ``picture``, ``space``, ``technique`` in ``set_page`` —
        so ``setattr(self, "produce", <a geometry door>)`` was **silent with no
        scaffolding at all**, where the shipped row W21/S1 refuses only because
        its plant happens to spell the name ``_d``. Every earlier appearance of
        this family needed something appended; this one needed nothing,
        because the module's own text already supplied the laundering
        occurrence. And it had **no lever**: under all 32 exemption subsets the
        only refusal shape is the plant's own ``builtins`` call, which by this
        file's own standard is not a lever at all.

        **Why this control exists and not just the fix.** Cycle 2's Step 8f
        aimed a mutant at the authority's breadth and it **SURVIVED** — 0 FAIL
        of 203 nodes, every cell identical to SHIPPED — after being proved
        non-no-op first. Narrowing or widening that authority changed the
        walk's verdict on nine shapes and **no assertion in this file could
        see it**. So the fix without this test would leave the next widening
        exactly as invisible as this one was.

        The names are **derived from the module's own AST**, never listed
        (ADR-0039/R2): a nested name added to any class tomorrow is covered
        here without anyone remembering to add it, and a tree where the walk
        finds none at all is a FAILURE rather than a vacuous pass.
        """
        import ast
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1] / _GUARD.MODULE
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        definition = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        owner = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}

        nested = set()
        for holder in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for node in ast.walk(holder):
                if isinstance(node, definition) and node is not holder:
                    if owner.get(node) is not holder:
                        nested.add(node.name)

        assert len(nested) >= 9, (
            "the walk finds fewer than the nine nested definitions measured "
            f"inside this module's classes on 2026-10-25, so this control "
            f"would pass vacuously: {sorted(nested)}"
        )

        silent = sorted(
            name
            for name in nested
            if not _GUARD._outcome(
                _GUARD._plant(
                    f'        setattr(self, "{name}", getattr(self, "page_" + _S))\n'
                    f"        self.{name}(3 + len(section))\n"
                    "        #",
                    '\n_S = "spec"\n',
                )
            )
        )
        assert silent == [], (
            "a geometry door installed with `setattr` under the name of a "
            "definition nested inside a method is SILENT, which is cycle 2's "
            "F-1: the class's attribute surface is being read with `ast.walk` "
            "rather than over its direct members, so the module's own nested "
            f"names launder the door for free. Silent spellings: {silent}"
        )

    def test_the_laundering_derivation_parsed_every_planted_body(self):
        """The derivation's own failure mode is a FAILURE, never a skip.

        ``_attribute_callee_laundering`` parses each plant's body to find its
        attribute callees. A body it cannot parse would silently contribute
        no laundering and drop out of the equality below, which is the
        default-ALLOW shape ADR-0039/R2 forbids, so it records the body
        instead and this is where that record reds.
        """
        assert _UNPARSED_PLANT_BODIES == [], (
            "a planted body no longer parses, so the laundering derivation "
            "is silently contributing nothing for it: "
            f"{_UNPARSED_PLANT_BODIES}"
        )

    def test_the_laundering_derivation_reaches_the_rows_it_declares(self):
        """ADR-0039/R2 on the derivation: the authority is
        :data:`TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage.DOOR_SHAPES`
        and the set it yields is held to an equality.

        14 of the 36 rows spell an attribute callee. The other 22 have no
        laundering analogue -- the local-name storage has none, which cycle 1
        measured and said why -- so their reading here would be byte-identical
        to :meth:`test_every_door_shape_is_read_or_refused_and_never_silent`'s
        and is not paid for twice. A row that gains or loses an attribute
        callee moves this equality rather than quietly entering or leaving
        the reading.
        """
        assert (
            self.LAUNDERABLE_DOOR_SHAPES == self.LAUNDERABLE_DOOR_SHAPE_LABELS
        ), (
            "the rows the laundering derivation reaches are no longer the "
            "rows this class declares, so either a DOOR_SHAPES row changed "
            "its callee or the derivation stopped reading one: "
            f"{self.LAUNDERABLE_DOOR_SHAPES}"
        )

    @pytest.mark.parametrize(
        "label,body,extra,outcome",
        [row for row in _GUARD.DOOR_SHAPES if _attribute_callee_laundering(row[1])],
        ids=[
            row[0].split()[0]
            for row in _GUARD.DOOR_SHAPES
            if _attribute_callee_laundering(row[1])
        ],
    )
    def test_no_door_shape_is_laundered_by_an_unrelated_resolving_occurrence(
        self, label, body, extra, outcome
    ):
        """A row of
        :data:`TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage.DOOR_SHAPES`
        that can be switched off from outside itself is not an assertion
        about anything (CARD-276 cycle 1's F-1).

        Measured at ``ced5e648``: **three** rows went silent when one
        unrelated assignment of their callee's spelling was appended -- W21,
        W23 and W25. Cycle 1 named one of them and attributed it to W29;
        W29 is in fact **not** launderable, because its installer's spelled
        store is opaque and the ``opaque`` branch runs before the anchor.
        That is why this reading is derived over every attribute-callee row
        rather than written for the row the finding named.
        """
        measured = _GUARD._outcome(
            _GUARD._plant(body, extra + _attribute_callee_laundering(body))
        )
        assert measured == outcome, (
            f"{label} no longer produces its declared outcome once an "
            "unrelated resolving occurrence of its callee's spelling is "
            f"appended, so the row can be switched off from outside it: "
            f"{measured} (declared {outcome})"
        )

    @pytest.mark.parametrize(
        "label,body,extra",
        TERMINAL_SHAPES,
        ids=[row[0].split()[0] for row in TERMINAL_SHAPES],
    )
    def test_a_decorated_definition_is_not_a_terminal_this_walk_can_read(
        self, label, body, extra
    ):
        """CARD-276 cycle 1's F-2: the premise that made passing a resolved
        chain safe, falsified and then narrowed.

        The sentence was *"a geometry door cannot stand at a ``def``/``import``
        terminal without being spelled"*. A decorator stands exactly there
        with its name assembled. The chain onto a decorated definition
        refuses now; the chain onto an undecorated one still resolves, which
        is :data:`CHAINS_THAT_RESOLVE`'s E1 and E3 and is what tells this
        rule from a cap (G-7).
        """
        assert _GUARD._outcome(_GUARD._plant(body, extra)) == ("refusal",), (
            f"{label} is no longer refused: a decorator puts the real "
            "imported door at a `def` terminal with its name assembled, so "
            "the door-spelling arm never sees it and the chain resolves"
        )

    def test_a_cycle_in_the_alias_chain_is_refused_rather_than_capped(self):
        """A cycle is a shape the walk cannot analyse, so it REFUSES (G-7).

        ``_p = _q; _q = _p`` is two anchored binding occurrences and no
        terminal. A fixed point computed without a cycle check either loops
        forever or needs a cap, and a cap that returns a verdict is the
        fail-open shape ADR-0039/R2 forbids. It raises and the call loop names
        it, exactly as the two receiver resolvers do.
        """
        body = """        _p = _q; _q = _p
        _p(3 + len(section))
        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT"""
        shapes = [shape for _, shape, _, _ in _GUARD._plant_refusals(body)]
        assert [self.CYCLE in shape for shape in shapes] == [True], (
            "a cyclic alias chain is no longer refused by name, so the fixed "
            f"point is capping it or looping: {shapes}"
        )

    #: The two substrings the refusals above and below are read by. Spelled
    #: once here rather than in each assertion, because a refusal renamed in
    #: the walk and in one control is a control that stops measuring.
    CYCLE = "whose alias chain closes a cycle"
    BOUND = "did not resolve to a fixed point within"

    def test_the_anchor_resolution_bound_is_reported_rather_than_capped(self):
        """The fixed point's own bound, failing CLOSED, with the pair that
        measures it (G-7, and CARD-262's F-503 discipline extended).

        CARD-262 moved two hand-written ``depth > 4`` caps from fail-open to a
        reported bound; re-introducing one here would fail this card whatever
        else it achieved. So the readings are a pair at the bound's edge:

        * a chain one link **past** the bound refuses, naming the bound;
        * the same chain one link **inside** it resolves, so the bound is what
          the deeper reading reports and not some other mechanism;
        * raise the bound past the deep chain and it resolves too, which is
          what says the refusal is the bound's and nothing else's;
        * and the bound costs this module **0** refusals, asserted.
        """
        terminal = "interior_page_count"
        inside = (
            f"        _a = {terminal}; _b = _a; _c = _b; _d2 = _c\n"
            "        _d2(toc_page_count)\n"
            "        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT"
        )
        past = (
            f"        _a = {terminal}; _b = _a; _c = _b; _d2 = _c; _e = _d2\n"
            "        _e(toc_page_count)\n"
            "        first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT"
        )

        deep = [shape for _, shape, _, _ in _GUARD._plant_refusals(past)]
        assert [self.BOUND in shape for shape in deep] == [True], (
            "a chain past the anchor resolution bound is no longer refused by "
            f"the bound: {deep}"
        )

        shallow = [shape for _, shape, _, _ in _GUARD._plant_refusals(inside)]
        assert shallow == [], (
            "a chain inside the bound no longer resolves, so the deeper "
            f"reading above is not the bound's doing: {shallow}"
        )

        original = _GUARD.ANCHOR_RESOLUTION_DEPTH
        try:
            _GUARD.ANCHOR_RESOLUTION_DEPTH = original + 4
            raised = [shape for _, shape, _, _ in _GUARD._plant_refusals(past)]
        finally:
            _GUARD.ANCHOR_RESOLUTION_DEPTH = original
        assert raised == [], (
            "with the bound raised past it the deep chain still refuses, so "
            f"what refused it was never the bound: {raised}"
        )

        _, _, refusals = _GUARD._page_positions()
        assert [
            shape for _, shape, _, _ in refusals if self.BOUND in shape
        ] == [], (
            "the anchor resolution bound now costs this module refusals, so "
            "its cost is no longer the 0 this card measured"
        )


class TestGuardProse_EveryNamedControlExists:
    """CARD-276 AC-6: a claim that points at a control that does not exist.

    CARD-262's final round deleted the per-class "must not absorb" control
    and replaced it with :data:`CALLEE_EXEMPTIONS`' own reach table; the
    ``CALLEE_EXEMPTIONS`` attribute doc went on naming the deleted test for
    a whole card, and its AC/EC/G gate is what found it. Cosmetic in effect
    and ADR-0039/R1's own family in kind: a reader cannot check a claim whose
    control does not exist, and nothing in this suite could tell.

    So the check is standing and **default-deny**: every ``test_*`` name this
    module's prose names in a Sphinx role or in backticks must resolve
    against a test this suite actually defines. Two details earn their place:

    * the references come from the module's **docstrings and its comments**,
      because the defect was in a ``#:`` attribute doc, which no docstring
      walk sees;
    * the authority is every ``def test_*`` under ``tests/``, derived by
      ``ast`` rather than listed, since a control named here may well live in
      another module of the suite.
    """

    #: A floor on the reference count, so the check cannot pass by finding
    #: nothing. A floor rather than an equality on purpose -- an equality
    #: here reds every time a docstring gains a cross-reference, which is the
    #: opposite of what this wants to encourage.
    #: :meth:`test_the_reference_scan_is_default_deny` is what says a *low*
    #: reading cannot be a vacuous pass.
    #:
    #: **The rationale sentence here used to carry a count of its own** --
    #: "this file's prose names fifteen distinct controls today and the one
    #: defect was one of sixteen" -- and cycle 1 recomputed it with this
    #: class's own resolver as **seventeen**: a stale figure inside the class
    #: built to catch stale prose (F-4). It is not restated with a corrected
    #: number, because a number nothing recomputes goes stale again and this
    #: file's own rule is that a figure's control is recomputation. The
    #: reading is printed by
    #: :meth:`test_no_docstring_names_a_test_that_does_not_exist` when the
    #: floor reds, which is where to read it.
    REFERENCES_AT_LEAST = 14

    @staticmethod
    def _prose(source):
        """Every docstring and every comment in ``source``, as one list.

        ``ast`` for the docstrings, ``tokenize`` for the comments. A ``#:``
        attribute doc is a comment, so a docstring-only walk would have
        missed the one defect this check exists for.
        """
        import ast
        import io
        import tokenize

        found = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(
                node,
                (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                text = ast.get_docstring(node, clean=False)
                if text:
                    found.append(text)
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                found.append(token.string)
        return found

    @classmethod
    def _named_tests(cls, source):
        """The ``test_*`` names ``source``'s prose names in a Sphinx role or
        in backticks, de-duplicated and sorted.

        Marked-up references only, and anchored: a bare mention of a path
        like ``tests/test_timeout.py`` is not a claim about a control and
        does not resolve to one.
        """
        import re

        marked = re.compile(
            r":(?:meth|func|class):`~?([^`]+)`|``([^`\n]+)``|`([^`\n]+)`"
        )
        anchored = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_]*\.)?(test_[A-Za-z0-9_]+)\Z")
        named = set()
        for text in cls._prose(source):
            for groups in marked.findall(text):
                for reference in groups:
                    hit = anchored.match(reference.strip())
                    if hit:
                        named.add(hit.group(1))
        return sorted(named)

    @staticmethod
    def _tests_this_suite_defines():
        """Every ``def test_*`` under ``tests/``, derived rather than listed."""
        import ast
        from pathlib import Path

        root = Path(__file__).resolve().parents[1] / "tests"
        defined = set()
        for path in sorted(root.rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and node.name.startswith("test_"):
                    defined.add(node.name)
        return defined

    @classmethod
    def _unresolved(cls, source):
        """``(named, defined, missing)`` for ``source``'s prose.

        **One resolution, used by the check and by its control**, which is
        the ADR-0039/R1 shape this card's own kill-instrument run caught in
        the first draft of this class: the control computed the missing list
        itself, so a mutant that emptied the *check's* list survived both.
        Now a mutant on this one line reds the control by name.
        """
        named = cls._named_tests(source)
        defined = cls._tests_this_suite_defines()
        return named, defined, [name for name in named if name not in defined]

    def test_no_docstring_names_a_test_that_does_not_exist(self):
        """The standing check (AC-6), default-deny over this module's prose."""
        from pathlib import Path

        source = Path(__file__).resolve().read_text(encoding="utf-8")
        named, defined, missing = self._unresolved(source)
        assert len(named) >= self.REFERENCES_AT_LEAST, (
            f"this module's prose names only {len(named)} controls, so the "
            "check below is measuring almost nothing and the reference scan "
            f"itself is the thing to look at: {named}"
        )

        assert len(defined) > 500, (
            f"the authority came back with {len(defined)} test names, so it "
            "is not the suite and every name below would resolve or fail for "
            "the wrong reason"
        )

        assert missing == [], (
            "this module's prose names a control this suite does not define, "
            "which is a claim its reader cannot check: "
            f"{missing}"
        )

    def test_the_authority_holds_tests_and_only_tests(self):
        """The authority's **membership**, not just its size.

        ``len(defined) > 500`` is satisfied by an authority that holds every
        function in ``tests/``, and this card's own instrument measured that
        mutant surviving (`M7`): widening the derivation to every ``def``
        changed nothing any assertion read. So the pair is asserted directly
        -- a test this class defines is in, and a helper of this very module
        is **not** -- which is the one reading that can fail in both
        directions.
        """
        _, defined, _ = self._unresolved("")
        assert "test_no_docstring_names_a_test_that_does_not_exist" in defined, (
            "the authority no longer holds a test this very class defines, so "
            "every name the check reads would be reported missing"
        )
        assert "_plant" not in defined, (
            "the authority holds `_plant`, a helper of this module and not a "
            "test, so it is no longer `every def test_* under tests/` and a "
            "dead claim could resolve against a helper's name"
        )

    def test_the_reference_scan_is_default_deny(self):
        """The control for the control, in both directions.

        A resolver that found no references, or one that resolved an unknown
        name, would pass the check above on a file full of dead claims. So
        **the same resolution** the check uses is read on prose this test
        owns: a name this suite does not define is **reported**, and the real
        name beside it is not. Without that pair the floor above is the only
        thing standing between this check and a default-allow scan.
        """
        source = (
            '"""A docstring naming '
            ":meth:`test_a_control_this_suite_does_not_define` and "
            ":meth:`test_no_docstring_names_a_test_that_does_not_exist`.\n"
            '"""\n'
            "#: And an attribute doc naming "
            "``test_another_control_this_suite_does_not_define``.\n"
            "FIELD = 1\n"
        )
        named, _, missing = self._unresolved(source)
        assert named == [
            "test_a_control_this_suite_does_not_define",
            "test_another_control_this_suite_does_not_define",
            "test_no_docstring_names_a_test_that_does_not_exist",
        ], (
            "the reference scan no longer reads a Sphinx role, a `#:` "
            f"attribute doc, or both: {named}"
        )

        assert missing == [
            "test_a_control_this_suite_does_not_define",
            "test_another_control_this_suite_does_not_define",
        ], (
            "the resolution the check uses no longer reports a name this "
            "suite does not define, so that check is default-ALLOW and would "
            "pass on any dead claim"
        )
