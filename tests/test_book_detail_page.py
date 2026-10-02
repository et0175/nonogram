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
      its ``.name`` label, the text of its ``.tier`` badge and the text of any
      ``<code>`` in it.
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
            self._row = {"id": a["data-puzzle-id"], "name": "", "tier": "", "code": ""}
            self.rows.append(self._row)
        elif self._row is not None and self._capture is None:
            if "name" in classes:
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
