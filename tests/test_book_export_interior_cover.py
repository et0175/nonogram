"""CARD-135 — the interior PDF holds no cover; the cover is its own file (FR-043).

    AC-283 (INV-013)  TestBookExport_InteriorStartsAtGuidePage
    AC-284 (INV-013)  TestBookExport_InteriorHoldsNoCoverPage
    AC-285            TestBookExport_CoverIsSeparateSinglePageFile
    AC-286 (INV-013)  TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover
    AC-289 (INV-013)  TestBookExport_EveryRouteSeparatesInteriorAndCover

The book of AC-283 is a Book 1 profile book (8.5 x 11 in trim) holding three
easy 20x20 puzzles, with a cover image uploaded through the Finalise screen —
the real upload, so the tests also cover the defect that the upload was
dropped before it reached any export. The PDFs are read back with Pillow's
own PDF parser (``tests/helpers/pdf_pages.py``), never by asking the
generator what it wrote.
"""

from __future__ import annotations

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
    """The guide page this book must open with — three easy puzzles."""
    return BookPDFGenerator().create_guide_page(puzzle_count, easy, 0, 0)


def _generated_title_cover():
    return BookPDFGenerator().create_cover_page(BOOK_TITLE)


@pytest.fixture
def covered_book(admin_app):
    """AC-283's book: cover uploaded on Finalise; (client, book_id)."""
    client = admin_app.test_client()
    book_id = _make_book(admin_app)
    _upload_cover(client, book_id, _cover_art())
    return client, book_id


class TestBookExport_InteriorStartsAtGuidePage:
    """AC-283 — the interior PDF's page 1 is the guide page."""

    def test_the_interiors_first_page_is_the_guide_page(self, covered_book):
        client, book_id = covered_book
        interior = pdf_pages(_download(client, "finalise", book_id, "interior"))

        assert same_page(interior[0], _guide_page(3, 3))

    def test_the_interior_runs_guide_puzzles_divider_answers(self, covered_book):
        """Only the cover moved: 1 guide + 3 puzzles + divider + 3 answers."""
        client, book_id = covered_book
        data = _download(client, "finalise", book_id, "interior")

        assert pdf_page_count(data) == 1 + 3 + 1 + 3

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
        assert export.interior_page_count == 4  # guide, puzzle, divider, answer


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

    def test_the_interior_still_starts_at_the_guide_page(self, bare_book):
        client, book_id = bare_book
        interior = pdf_pages(_download(client, "finalise", book_id, "interior"))

        assert same_page(interior[0], _guide_page(3, 3))
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
    def test_each_route_yields_a_guide_first_interior_and_a_cover_file(self, covered_book, route):
        client, book_id = covered_book
        interior = pdf_pages(_download(client, route, book_id, "interior"))
        cover = pdf_pages(_download(client, route, book_id, "cover"))

        assert same_page(interior[0], _guide_page(3, 3))
        assert len(interior) == 1 + 3 + 1 + 3
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
        assert same_page(pdf_pages(response.get_data())[0], _guide_page(3, 3))

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
        assert "~8</dd>" in body  # 1 guide + 3 puzzles + divider + 3 answers


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

        assert same_page(interior[0], _guide_page(3, 3))

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

        assert same_page(interior[0], _guide_page(3, 3))


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
    """

    @pytest.mark.parametrize("puzzle_count", (0, 1, 3))
    def test_the_plan_matches_the_written_interior(self, puzzle_count):
        from nonogram.admin.book_pdf_generator import interior_page_count

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
        interior = BookPDFGenerator().export_interior([puzzle] * puzzle_count)

        assert interior_page_count(puzzle_count) == pdf_page_count(interior.getvalue())

    @pytest.mark.parametrize("puzzle_count", (1, 3))
    def test_finalise_shows_the_downloaded_interiors_page_count(self, admin_app, puzzle_count):
        client = admin_app.test_client()
        book_id = _make_book(admin_app, puzzle_count)
        body = client.get(f"/book/{book_id}/finalize").get_data(as_text=True)
        pages = pdf_page_count(_download(client, "finalise", book_id, "interior"))

        assert f"~{pages}</dd>" in body
