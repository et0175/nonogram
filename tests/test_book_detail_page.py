"""CARD-158 — the book list and book page show what the book actually holds.

    AC-1  TestBookPages_OfferBothExportFiles
    AC-2  TestBookDetail_ListsPuzzlesByTitle
    AC-3  TestBookDetail_ShowsTheStoredTrim

Driven through the Flask test client against the real routes, in the
in-memory storage mode, so the suite runs everywhere (no Postgres needed).

The rendered page is read back with an independent ``HTMLParser`` reader
rather than a regex over the templates' own markup, and every expected value
is written out as a literal — the custom title the owner typed, the puzzle
name, the trim submitted on Print setup — never re-derived through the view
helper under test.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram import clues

#: The literals the criteria are checked against.
CUSTOM_TITLE = "First snow on the hill"
NAMES = ("Snowflake", "Angel", "Reindeer")
TIERS = ("easy", "medium", "hard")


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    # A fresh in-memory book store, restored afterwards, so this module's
    # books do not leak into later tests that build an in-memory app.
    monkeypatch.setattr(
        book_manager_module,
        "_book_manager",
        book_manager_module.BookManager(session_factory=None),
    )
    app = create_app()
    app.config["TESTING"] = True
    app.config["BOOK_COVER_DIR"] = str(tmp_path / "covers")
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


@pytest.fixture
def client(admin_app):
    return admin_app.test_client()


def _rectangle(width, height, left, top, right, bottom):
    """A filled rectangle — uniquely solvable, so the store accepts it."""
    return [
        [left <= x < right and top <= y < bottom for x in range(width)]
        for y in range(height)
    ]


def _add_puzzle(app, index, tier, name):
    grid = _rectangle(20, 20, index, index, 8 + 2 * index, 10 + index)
    found = clues.compute_clues(grid)
    puzzle_id = app.puzzle_review_service.add_puzzle(
        grid=grid,
        clues_rows=[list(c) for c in found.rows],
        clues_cols=[list(c) for c in found.columns],
        width=20,
        height=20,
        theme="winter",
        difficulty_score=10,
        difficulty_tier=tier,
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
    )
    if name is not None:
        assert app.puzzle_review_service.rename_puzzle(puzzle_id, name)
    return puzzle_id


def _make_book(app, title="Winter pictures", names=NAMES, tiers=TIERS, size="8x10"):
    """A book holding one named puzzle per entry of ``names``."""
    book_id = app.book_manager.create_book(
        title=title,
        description="Pictures of winter.",
        theme="generic",
        target_audience="adults",
        size=size,
    )
    ids = [
        _add_puzzle(app, i, tier, name)
        for i, (name, tier) in enumerate(zip(names, tiers))
    ]
    if ids:
        app.book_manager.add_puzzles_to_book(book_id, ids)
    return book_id, ids


def _lose_uploaded_cover(app, client, book_id):
    """Upload a cover on Finalise, then delete its file: the lost-upload case.

    The session still claims the upload, and the file is gone — the state
    ``_cover_upload_lost`` describes and the download route refuses.
    """
    art = Image.new("RGB", (1200, 1800), (20, 30, 90))
    buffer = BytesIO()
    art.save(buffer, format="PNG")
    buffer.seek(0)
    response = client.post(
        f"/book/{book_id}/finalize",
        data={"cover": (buffer, "cover.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code in (200, 302)
    (path,) = Path(app.config["BOOK_COVER_DIR"]).glob(f"{book_id}_cover.png")
    path.unlink()


# --------------------------------------------------------------------------
# Reading a rendered page
# --------------------------------------------------------------------------


class _Page(HTMLParser):
    """Forms, export buttons, member rows and the Trim size row, as read back.

    * ``forms``: every ``<form>`` with its ``action``, its hidden inputs and
      the ``data-export-part`` of each button inside it.
    * ``loose_buttons``: export buttons that sit in no form, with whether
      they are disabled.
    * ``rows``: each ``<tr data-puzzle-id>`` — its id attribute, the text of
      its ``.name`` label, the text of its ``.tier`` badge, the text of any
      ``<code>`` in it, and the text of its first cell, the "#" (``hash``).
    * ``trim``: the text and links of the ``<dd>`` that follows
      ``<dt>Trim size</dt>``.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list = []
        self.loose_buttons: list = []
        self.rows: list = []
        self.dts: list = []
        self.trim = None
        self._form = None
        self._row = None
        self._capture = None  # (target dict, key, tag, depth)
        self._dt = None
        self._dd = None
        self._last_dt = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "form":
            self._form = {"action": a.get("action"), "hidden": {}, "parts": []}
            self.forms.append(self._form)
        elif tag == "input" and self._form is not None and a.get("type") == "hidden":
            self._form["hidden"][a.get("name")] = a.get("value")
        elif tag == "button" and "data-export-part" in a:
            if self._form is not None:
                self._form["parts"].append(
                    {"part": a["data-export-part"], "disabled": "disabled" in a}
                )
            else:
                self.loose_buttons.append(
                    {"part": a["data-export-part"], "disabled": "disabled" in a}
                )
        elif tag == "tr" and "data-puzzle-id" in a:
            self._row = {
                "id": a["data-puzzle-id"], "name": "", "tier": "", "code": "", "hash": ""
            }
            self.rows.append(self._row)
        elif self._row is not None and self._capture is None:
            if tag == "td" and not self._row.get("_hash_seen"):
                # The first cell of a member row is its "#".
                self._row["_hash_seen"] = True
                self._capture = [self._row, "hash", tag, 0]
            elif "name" in classes:
                self._capture = [self._row, "name", tag, 0]
            elif "tier" in classes:
                self._capture = [self._row, "tier", tag, 0]
            elif tag == "code":
                self._capture = [self._row, "code", tag, 0]
        elif self._capture is not None and tag == self._capture[2]:
            self._capture[3] += 1
        if tag == "dt":
            self._dt = ""
        elif tag == "dd" and self._last_dt == "Trim size":
            self._dd = {"text": "", "links": []}
        elif tag == "a" and self._dd is not None:
            self._dd["links"].append(a.get("href"))

    def handle_endtag(self, tag):
        if tag == "form":
            self._form = None
        elif tag == "tr":
            self._row = None
        if self._capture is not None and tag == self._capture[2]:
            if self._capture[3] == 0:
                self._capture = None
            else:
                self._capture[3] -= 1
        if tag == "dt" and self._dt is not None:
            self._last_dt = self._dt.strip()
            self._dt = None
        elif tag == "dd":
            if self._dd is not None:
                self.trim = {"text": " ".join(self._dd["text"].split()), "links": self._dd["links"]}
                self._dd = None
            self._last_dt = None

    def handle_data(self, data):
        if self._capture is not None:
            target, key = self._capture[0], self._capture[1]
            target[key] += data
        if self._dt is not None:
            self._dt += data
        if self._dd is not None:
            self._dd["text"] += data

    # -- queries -------------------------------------------------------------

    def export_forms(self, part):
        """The forms holding a button for ``part``, with that button's state."""
        return [
            (form, button)
            for form in self.forms
            for button in form["parts"]
            if button["part"] == part
        ]


def _read(client, path) -> _Page:
    response = client.get(path)
    assert response.status_code == 200, path
    page = _Page()
    page.feed(response.get_data(as_text=True))
    return page


def _book_forms(page, book_id, part):
    """The ``part`` export forms that act on ``book_id``."""
    return [
        (form, button)
        for form, button in page.export_forms(part)
        if form["action"].startswith(f"/book/{book_id}/")
    ]


# --------------------------------------------------------------------------
# AC-1
# --------------------------------------------------------------------------


PAGES = ("detail", "list")


def _page_for(client, which, book_id):
    return _read(client, f"/book/{book_id}" if which == "detail" else "/books")


class TestBookPages_OfferBothExportFiles:
    """AC-1 — both pages offer the interior and the cover file (FR-043)."""

    @pytest.mark.parametrize("which", PAGES)
    def test_offers_an_interior_download(self, admin_app, client, which):
        book_id, _ = _make_book(admin_app)
        page = _page_for(client, which, book_id)

        (interior,) = _book_forms(page, book_id, "interior")
        form, button = interior
        assert not button["disabled"]
        assert form["action"] in (
            f"/book/{book_id}/download-pdf",
            f"/book/{book_id}/generate-pdf",
        )
        assert form["hidden"].get("part") == "interior"

    @pytest.mark.parametrize("which", PAGES)
    def test_offers_a_cover_download_that_submits_part_cover(self, admin_app, client, which):
        book_id, _ = _make_book(admin_app)
        page = _page_for(client, which, book_id)

        (cover,) = _book_forms(page, book_id, "cover")
        form, button = cover
        assert not button["disabled"]
        assert form["action"] == f"/book/{book_id}/download-pdf"
        assert form["hidden"] == {"part": "cover"}
        assert not [b for b in page.loose_buttons if b["part"] == "cover"]

    @pytest.mark.parametrize("which", PAGES)
    def test_the_cover_form_as_rendered_downloads_the_cover_file(
        self, admin_app, client, which
    ):
        """Submitting exactly what the page renders gets the cover PDF."""
        book_id, _ = _make_book(admin_app)
        page = _page_for(client, which, book_id)
        ((form, _button),) = _book_forms(page, book_id, "cover")

        response = client.post(form["action"], data=form["hidden"])

        assert response.status_code == 200
        assert response.mimetype == "application/pdf"
        assert "_cover.pdf" in response.headers["Content-Disposition"]
        assert response.data.startswith(b"%PDF")

    def test_a_book_with_no_puzzles_still_offers_its_cover(self, admin_app, client):
        """The cover is a title cover without puzzles; only the interior waits."""
        book_id, _ = _make_book(admin_app, names=(), tiers=())
        page = _read(client, f"/book/{book_id}")

        assert _book_forms(page, book_id, "interior") == []
        assert [b for b in page.loose_buttons if b["part"] == "interior"] == [
            {"part": "interior", "disabled": True}
        ]
        ((form, button),) = _book_forms(page, book_id, "cover")
        assert not button["disabled"]
        assert form["hidden"] == {"part": "cover"}

    @pytest.mark.parametrize("which", PAGES)
    def test_a_lost_cover_upload_disables_the_cover_button(
        self, admin_app, client, which
    ):
        """The route's rule: a claimed upload whose file is gone is refused.

        So the page does not offer a submission the route refuses: the cover
        button is disabled and in no form, while the interior is unaffected.
        """
        book_id, _ = _make_book(admin_app)
        _lose_uploaded_cover(admin_app, client, book_id)

        page = _page_for(client, which, book_id)

        assert _book_forms(page, book_id, "cover") == []
        assert {"part": "cover", "disabled": True} in page.loose_buttons
        ((_form, interior),) = _book_forms(page, book_id, "interior")
        assert not interior["disabled"]

        # The page's verdict is the route's: the same session is refused.
        refused = client.post(f"/book/{book_id}/download-pdf", data={"part": "cover"})
        assert refused.status_code == 302

    def test_the_book_page_says_why_a_lost_cover_is_unavailable(self, admin_app, client):
        book_id, _ = _make_book(admin_app)
        _lose_uploaded_cover(admin_app, client, book_id)

        body = client.get(f"/book/{book_id}").get_data(as_text=True)

        assert "no longer on disk" in body
        assert f'href="/book/{book_id}/finalize"' in body

    def test_an_intact_book_page_carries_no_lost_cover_note(self, admin_app, client):
        book_id, _ = _make_book(admin_app)
        body = client.get(f"/book/{book_id}").get_data(as_text=True)
        assert "no longer on disk" not in body

    def test_one_book_s_lost_cover_leaves_another_book_s_cover_on_the_list(
        self, admin_app, client
    ):
        lost_id, _ = _make_book(admin_app, title="Lost cover")
        intact_id, _ = _make_book(admin_app, title="Intact cover")
        _lose_uploaded_cover(admin_app, client, lost_id)

        page = _read(client, "/books")

        assert _book_forms(page, lost_id, "cover") == []
        ((form, button),) = _book_forms(page, intact_id, "cover")
        assert not button["disabled"]
        assert form["hidden"] == {"part": "cover"}

    def test_the_list_says_why_a_lost_cover_is_unavailable_in_visible_text(
        self, admin_app, client
    ):
        """The reason is page text, not only a title= a disabled button never shows.

        Only the lost book's row carries it; the intact book's row does not.
        """
        lost_id, _ = _make_book(admin_app, title="Lost cover")
        intact_id, _ = _make_book(admin_app, title="Intact cover")
        _lose_uploaded_cover(admin_app, client, lost_id)

        body = client.get("/books").get_data(as_text=True)

        def hint(book_id):
            return re.search(
                rf'<span class="text-muted small" id="cover-lost-{book_id}">(.*?)</span>',
                body,
                re.S,
            )

        found = hint(lost_id)
        assert found is not None
        assert "no longer on disk" in found.group(1)
        assert f'href="/book/{lost_id}/finalize"' in found.group(1)
        assert hint(intact_id) is None
        assert f'id="cover-lost-{intact_id}"' not in body


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestBookDetail_ListsPuzzlesByTitle:
    """AC-2 — members are listed by title (custom title, else puzzle name)."""

    def test_each_member_is_labelled_by_its_puzzle_name(self, admin_app, client):
        book_id, ids = _make_book(admin_app)
        page = _read(client, f"/book/{book_id}")

        assert [row["id"] for row in page.rows] == ids
        assert [row["name"].strip() for row in page.rows] == list(NAMES)

    def test_a_custom_title_wins_over_the_puzzle_name(self, admin_app, client):
        book_id, ids = _make_book(admin_app)
        assert admin_app.book_manager.set_puzzle_title(book_id, ids[0], CUSTOM_TITLE)

        page = _read(client, f"/book/{book_id}")
        labels = [row["name"].strip() for row in page.rows]

        assert labels == [CUSTOM_TITLE, NAMES[1], NAMES[2]]
        assert NAMES[0] not in labels

    def test_a_puzzle_without_a_custom_title_falls_back_to_its_name(
        self, admin_app, client
    ):
        """The other half of the fallback: only the titled member changes."""
        book_id, ids = _make_book(admin_app)
        assert admin_app.book_manager.set_puzzle_title(book_id, ids[2], CUSTOM_TITLE)

        page = _read(client, f"/book/{book_id}")

        assert [row["name"].strip() for row in page.rows] == [
            NAMES[0],
            NAMES[1],
            CUSTOM_TITLE,
        ]

    def test_the_raw_id_is_not_the_visible_label(self, admin_app, client):
        book_id, ids = _make_book(admin_app)
        page = _read(client, f"/book/{book_id}")
        body = client.get(f"/book/{book_id}").get_data(as_text=True)

        for row, puzzle_id in zip(page.rows, ids):
            assert puzzle_id not in row["name"]
            assert row["code"] == ""
            assert f"<code>{puzzle_id}</code>" not in body
        # The id is still on the page, for the "Add puzzles by ID" form.
        for puzzle_id in ids:
            assert puzzle_id in body

    def test_an_unnamed_member_without_a_custom_title_is_labelled_by_its_id(
        self, admin_app, client
    ):
        """The last rung of the fallback: no custom title and no name → the id.

        A blank rename stores ``puzzle_name = None``; without the id rung the
        label would be the literal text "None".
        """
        book_id, ids = _make_book(admin_app)
        service = admin_app.puzzle_review_service
        assert service.rename_puzzle(ids[1], "   ")
        assert service.get_puzzle(ids[1])["puzzle_name"] is None

        page = _read(client, f"/book/{book_id}")
        labels = [row["name"].strip() for row in page.rows]

        assert labels == [NAMES[0], ids[1], NAMES[2]]
        assert "None" not in labels

    def test_a_member_whose_puzzle_is_gone_is_labelled_by_its_id(
        self, admin_app, client
    ):
        """A member id no record matches is still listed: by its id, tier N/A."""
        book_id, ids = _make_book(admin_app)
        assert admin_app.puzzle_review_service.delete_puzzle(ids[0])
        assert ids[0] in admin_app.book_manager.get_book(book_id).puzzle_ids

        page = _read(client, f"/book/{book_id}")

        # CARD-165: the rows are in print order now, and a member with no
        # record is not printed, so it is listed after the printed ones.
        assert [row["id"] for row in page.rows] == [ids[1], ids[2], ids[0]]
        assert [row["name"].strip() for row in page.rows] == [NAMES[1], NAMES[2], ids[0]]
        assert [row["tier"].strip() for row in page.rows] == [TIERS[1], TIERS[2], "N/A"]

    def test_each_member_shows_its_tier(self, admin_app, client):
        book_id, _ = _make_book(admin_app)
        page = _read(client, f"/book/{book_id}")
        assert [row["tier"].strip() for row in page.rows] == list(TIERS)

    def test_titles_are_read_in_one_pass(self, admin_app, client, monkeypatch):
        """One ``get_puzzles`` read for the page, no per-member ``get_puzzle``."""
        book_id, ids = _make_book(admin_app)
        service = admin_app.puzzle_review_service
        bulk_calls = []
        real_get_puzzles = service.get_puzzles

        def counting_get_puzzles(puzzle_ids):
            bulk_calls.append(list(puzzle_ids))
            return real_get_puzzles(puzzle_ids)

        def refuse_get_puzzle(*_args, **_kwargs):
            raise AssertionError("book page read a member one at a time")

        monkeypatch.setattr(service, "get_puzzles", counting_get_puzzles)
        monkeypatch.setattr(service, "get_puzzle", refuse_get_puzzle)

        page = _read(client, f"/book/{book_id}")

        assert bulk_calls == [ids]
        assert [row["name"].strip() for row in page.rows] == list(NAMES)


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestBookDetail_ShowsTheStoredTrim:
    """AC-3 — the size row is the trim Print setup stored, or "not set"."""

    def test_shows_the_trim_print_setup_stored(self, admin_app, client):
        book_id, _ = _make_book(admin_app, size="8x10")
        response = client.post(
            f"/book/{book_id}/setup-print",
            data={"unit": "cm", "width": "15.24", "height": "22.86"},
        )
        assert response.status_code in (200, 302)
        assert admin_app.book_manager.get_book(book_id).trim_width_cm == "15.24"

        page = _read(client, f"/book/{book_id}")

        assert page.trim is not None
        assert page.trim["text"] == "15.24 × 22.86 cm"

    def test_a_new_book_shows_the_profile_it_was_created_on(self, admin_app, client):
        """create_book stores CON-018's 8.5 x 11 in profile (AC-181)."""
        book_id, _ = _make_book(admin_app, size="8x10")
        page = _read(client, f"/book/{book_id}")
        assert page.trim["text"] == "21.59 × 27.94 cm"
        assert "8x10" not in page.trim["text"]

    def test_a_book_with_no_print_spec_says_not_set_and_links_to_print_setup(
        self, admin_app, client
    ):
        book_id, _ = _make_book(admin_app, size="8x10")
        book = admin_app.book_manager.get_book(book_id)
        book.trim_width_cm = None
        book.trim_height_cm = None

        page = _read(client, f"/book/{book_id}")

        assert page.trim["text"].startswith("Not set")
        assert f"/book/{book_id}/setup-print" in page.trim["links"]
        assert "8x10" not in page.trim["text"]
        assert "21.59" not in page.trim["text"]

    def test_an_unreadable_stored_trim_says_so_and_links_to_print_setup(
        self, admin_app, client
    ):
        book_id, _ = _make_book(admin_app)
        admin_app.book_manager.get_book(book_id).trim_width_cm = "not-a-number"

        page = _read(client, f"/book/{book_id}")

        assert page.trim["text"].startswith("Cannot be read")
        assert f"/book/{book_id}/setup-print" in page.trim["links"]


# --------------------------------------------------------------------------
# CARD-165 — the "#" is the number the printed book gives each puzzle
# --------------------------------------------------------------------------

#: ADR-0037's band, written out rather than imported from ``band_identity``.
BAND = "Puzzle {number} · {tier}"
TIER_LABELS = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}
#: Print rank of a level (FR-041), restated for the test's own oracle.
LEVEL_RANK = {"easy": 0, "medium": 1, "hard": 2}

#: A stored order that mixes the levels, as a book stored before INV-009 can.
MIXED = (("M1", "medium"), ("E1", "easy"), ("H1", "hard"), ("E2", "easy"), ("M2", "medium"))


def _book_stored_as(app, members, title="Mixed levels"):
    """A book whose stored ``puzzle_ids`` are exactly ``members``' order.

    ``add_puzzles_to_book`` files each puzzle inside its level (INV-009), so the
    mixed order is written onto the in-memory book afterwards — the shape of a
    book stored before the grouping existed (AC-260).
    """
    book_id, ids = _make_book(
        app,
        title=title,
        names=[name for name, _ in members],
        tiers=[tier for _, tier in members],
    )
    app.book_manager.get_book(book_id).puzzle_ids = list(ids)
    return book_id, ids


def _hash_cell(row):
    """A row's "#" cell as one line: the dash and its reason space-separated."""
    return " ".join(row["hash"].replace("—", " — ").split())


def _make_undrawable(app, puzzle_id):
    """A record the export cannot build a payload from: it logs and drops it."""
    app.puzzle_review_service.puzzles[puzzle_id]["clues_rows"] = 12


def _bands_the_export_prints(app, client, monkeypatch, book_id):
    """``{puzzle id: band text}`` as the real interior download draws them.

    Spies on the step that writes the band onto a puzzle page's payload while
    ``/book/<id>/download-pdf`` renders the interior, and names each page's
    puzzle by its row clues, which differ from member to member.
    """
    from nonogram.admin.book_pdf_generator import BookPDFGenerator

    real = BookPDFGenerator._puzzle_payload
    drawn = []

    def spy(payload, puzzle_number):
        banded = real(payload, puzzle_number)
        drawn.append((payload.row_clues, banded.difficulty))
        return banded

    monkeypatch.setattr(BookPDFGenerator, "_puzzle_payload", staticmethod(spy))
    response = client.post(f"/book/{book_id}/download-pdf", data={"part": "interior"})
    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")

    service = app.puzzle_review_service
    by_clues = {}
    for puzzle_id in app.book_manager.get_book(book_id).puzzle_ids:
        record = service.puzzles.get(puzzle_id)
        if record is not None and isinstance(record["clues_rows"], list):
            by_clues[tuple(tuple(c) for c in record["clues_rows"])] = puzzle_id
    assert len(by_clues) == len(set(by_clues.values())), "members share clues"
    return {by_clues[row_clues]: band for row_clues, band in drawn}


class TestBookDetail_NumbersPuzzlesLikeTheBook:
    """AC-1 — print order on screen, and each "#" is the PDF band's number."""

    def test_lists_a_mixed_stored_order_in_print_order(self, admin_app, client):
        book_id, ids = _book_stored_as(admin_app, MIXED)
        page = _read(client, f"/book/{book_id}")

        assert [row["name"].strip() for row in page.rows] == ["E1", "E2", "M1", "M2", "H1"]
        assert [row["tier"].strip() for row in page.rows] == [
            "easy", "easy", "medium", "medium", "hard",
        ]

    def test_numbers_run_from_one_down_the_table(self, admin_app, client):
        book_id, _ = _book_stored_as(admin_app, MIXED)
        page = _read(client, f"/book/{book_id}")
        assert [row["hash"].strip() for row in page.rows] == ["1", "2", "3", "4", "5"]

    def test_each_number_is_the_band_the_exported_interior_prints(
        self, admin_app, client, monkeypatch
    ):
        book_id, ids = _book_stored_as(admin_app, MIXED)
        page = _read(client, f"/book/{book_id}")

        bands = _bands_the_export_prints(admin_app, client, monkeypatch, book_id)

        assert set(bands) == set(ids), "every member drew one page"
        for row in page.rows:
            tier = row["tier"].strip()
            assert bands[row["id"]] == BAND.format(
                number=row["hash"].strip(), tier=TIER_LABELS[tier]
            ), row

    def test_a_repeated_member_is_numbered_at_each_place_it_prints(
        self, admin_app, client
    ):
        """An id stored twice is two rows to the export (``_book_puzzles``)."""
        from nonogram.admin.book_pdf_generator import BookPDFGenerator

        book_id, ids = _book_stored_as(admin_app, (("E1", "easy"), ("M1", "medium")))
        book = admin_app.book_manager.get_book(book_id)
        book.puzzle_ids = [ids[1], ids[0], ids[0]]
        service = admin_app.puzzle_review_service
        plan = BookPDFGenerator(book).section_plan(
            [service.get_puzzle(p) for p in book.puzzle_ids]
        )
        assert plan.ids == [ids[0], ids[0], ids[1]]

        page = _read(client, f"/book/{book_id}")

        assert [(row["id"], row["hash"].strip()) for row in page.rows] == [
            (ids[0], "1"), (ids[0], "2"), (ids[1], "3"),
        ]

    def test_showing_the_page_does_not_rewrite_the_stored_order(self, admin_app, client):
        """G-1: the page reads the print order; it stores nothing."""
        book_id, ids = _book_stored_as(admin_app, MIXED)
        _read(client, f"/book/{book_id}")
        assert admin_app.book_manager.get_book(book_id).puzzle_ids == ids

    def test_numbers_equal_the_export_over_a_seeded_corpus(self, admin_app, client):
        """Property: for any mix of levels, undrawable and missing members.

        Two oracles, neither the page's code: a stable sort by level written
        here (FR-041), skipping undrawable rows when counting and listing
        missing ones last; and the export side's own coordinates — the page
        plan's ``numbers`` resolved through ``SectionPlan.ids`` over rows read
        one at a time with ``get_puzzle``, as ``_book_puzzles`` reads them.
        """
        import random

        from nonogram.admin.book_pdf_generator import BookPDFGenerator, PuzzlePagePlan

        rng = random.Random(165)
        service = admin_app.puzzle_review_service
        books = undrawn = missing = 0
        for b in range(14):
            size = rng.randint(2, 7)
            tiers = [rng.choice(TIERS) for _ in range(size)]
            members = [(f"P{b}-{i}", tier) for i, tier in enumerate(tiers)]
            book_id, ids = _book_stored_as(admin_app, members, title=f"Corpus {b}")
            stored = list(ids)
            rng.shuffle(stored)
            admin_app.book_manager.get_book(book_id).puzzle_ids = stored
            tier_of = dict(zip(ids, tiers))
            gone, broken = set(), set()
            for puzzle_id in stored:
                roll = rng.random()
                if roll < 0.12:
                    assert service.delete_puzzle(puzzle_id)
                    gone.add(puzzle_id)
                elif roll < 0.27:
                    _make_undrawable(admin_app, puzzle_id)
                    broken.add(puzzle_id)

            # Oracle 1: written here.
            present = [p for p in stored if p not in gone]
            ordered = sorted(present, key=lambda p: LEVEL_RANK[tier_of[p]])
            expected, n = [], 0
            for p in ordered:
                if p in broken:
                    expected.append((p, None))
                else:
                    n += 1
                    expected.append((p, n))
            expected += [(p, None) for p in stored if p in gone]

            # Oracle 2: the export side's own numbering.
            book = admin_app.book_manager.get_book(book_id)
            rows = [service.get_puzzle(p) for p in book.puzzle_ids]
            plan = BookPDFGenerator(book).section_plan([r for r in rows if r])
            exported = {
                plan.ids[number - 1]: number
                for entry in plan.pages
                if isinstance(entry, PuzzlePagePlan)
                for number in entry.numbers
            }

            page = _read(client, f"/book/{book_id}")
            shown = [
                (row["id"], int(row["hash"]) if row["hash"].strip().isdigit() else None)
                for row in page.rows
            ]
            assert shown == expected, (b, shown, expected)
            assert {p: n for p, n in shown if n is not None} == exported, b
            for row in page.rows:
                if row["id"] in broken | gone:
                    assert "—" in row["hash"] and "Not printed" in row["hash"], row

            books += 1
            undrawn += len(broken)
            missing += len(gone)

        assert books >= 14
        assert undrawn >= 3 and missing >= 3, (undrawn, missing)


class TestBookDetail_UndrawableMemberHasNoNumber:
    """AC-2 — a member the interior cannot draw shows "—" and why; no gap."""

    MEMBERS = (("E1", "easy"), ("E2", "easy"), ("E3", "easy"), ("M1", "medium"))

    def test_shows_a_dash_and_a_reason_instead_of_a_number(self, admin_app, client):
        book_id, ids = _book_stored_as(admin_app, self.MEMBERS)
        _make_undrawable(admin_app, ids[1])

        page = _read(client, f"/book/{book_id}")

        assert [row["id"] for row in page.rows] == ids, "still listed, in place"
        hashes = [_hash_cell(row) for row in page.rows]
        assert hashes[0] == "1"
        assert hashes[1] == "— Not printed: cannot be drawn"
        assert hashes[2:] == ["2", "3"], "the next row takes the next number"

    def test_the_other_numbers_still_match_the_pdf(self, admin_app, client, monkeypatch):
        book_id, ids = _book_stored_as(admin_app, self.MEMBERS)
        _make_undrawable(admin_app, ids[1])
        page = _read(client, f"/book/{book_id}")

        bands = _bands_the_export_prints(admin_app, client, monkeypatch, book_id)

        assert ids[1] not in bands, "the export drops the undrawable member"
        printed = [row for row in page.rows if row["id"] != ids[1]]
        assert {row["id"]: bands[row["id"]] for row in printed} == {
            row["id"]: BAND.format(
                number=row["hash"].strip(), tier=TIER_LABELS[row["tier"].strip()]
            )
            for row in printed
        }

    def test_a_member_with_no_record_has_no_number(self, admin_app, client):
        """The export skips an id with no record, so the page numbers none."""
        book_id, ids = _book_stored_as(admin_app, self.MEMBERS)
        assert admin_app.puzzle_review_service.delete_puzzle(ids[0])

        page = _read(client, f"/book/{book_id}")

        assert [row["id"] for row in page.rows] == [ids[1], ids[2], ids[3], ids[0]]
        hashes = [_hash_cell(row) for row in page.rows]
        assert hashes == ["1", "2", "3", "— Not printed: puzzle not found"]

    def test_a_book_whose_page_plan_cannot_be_built_shows_no_numbers(
        self, admin_app, client, caplog
    ):
        """An unreadable trim: no plan, so no numbers — and the page says so."""
        book_id, ids = _book_stored_as(admin_app, MIXED)
        admin_app.book_manager.get_book(book_id).trim_width_cm = "not-a-number"

        import logging

        with caplog.at_level(logging.WARNING):
            body = client.get(f"/book/{book_id}").get_data(as_text=True)
        # A failure the seam declares is a one-line warning, not a traceback,
        # so it can be told apart from a bug in the page's own code.
        assert any(
            r.levelno == logging.WARNING and "No page plan" in r.getMessage()
            for r in caplog.records
        ), caplog.text
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
        page = _Page()
        page.feed(body)

        assert 'id="numbers-unavailable"' in body
        assert [row["id"] for row in page.rows] == ids, "stored order, as stored"
        assert all(not row["hash"].strip()[:1].isdigit() for row in page.rows)
        assert all(
            _hash_cell(row) == "— Number unknown: no page plan" for row in page.rows
        )

    def test_an_unexpected_plan_failure_is_logged_with_its_traceback(
        self, admin_app, client, caplog, monkeypatch
    ):
        import logging

        from nonogram.admin.book_pdf_generator import BookPDFGenerator

        def broken(self, puzzles):
            raise KeyError("renamed field")

        monkeypatch.setattr(BookPDFGenerator, "section_plan", broken)
        book_id, ids = _book_stored_as(admin_app, MIXED)

        with caplog.at_level(logging.WARNING):
            body = client.get(f"/book/{book_id}").get_data(as_text=True)

        assert 'id="numbers-unavailable"' in body
        errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert errors and any(r.exc_info for r in errors), caplog.text

    def test_an_intact_book_carries_no_numbers_unavailable_note(self, admin_app, client):
        book_id, _ = _book_stored_as(admin_app, MIXED)
        body = client.get(f"/book/{book_id}").get_data(as_text=True)
        assert 'id="numbers-unavailable"' not in body
