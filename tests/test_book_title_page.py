"""The title and copyright page's own lines (owner, 2026-11-09; migration 020).

Interior page 1 prints the book's title, and since migration 020 three
optional per-book lines beside it: the **series name** above the title, the
**subtitle** under it, and the **authors** ("by ...", and named in the
copyright notice). They are entered on the General info step, beside the
title they belong with, and follow ``player_domain``'s shape (migration 018):
nullable, no default, no backfill, NULL meaning "not set".

The owner's values for her first book are the fixture throughout, because
they are the ones that must print: an em dash, an ampersand and a typographic
apostrophe, each of which has to reach the page through the embedded face's
WinAnsi encoding rather than as a ``.notdef`` box.

Expectations about the page are read back out of the content stream
(:func:`tests.helpers.pdf_vector.placed_text`), never recomputed with the
layout code under test.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from nonogram.admin.book_manager import (
    TITLE_PAGE_FIELDS,
    TITLE_PAGE_TEXT_MAX,
    InvalidBookDetails,
    title_page_text,
)
from nonogram.admin.book_pdf_generator import BookPDFGenerator, _settable
from nonogram.admin.book_vector import encode_text
from tests.helpers.pdf_vector import placed_text
from tests.test_book_arrange_size_filter import Panel, panel  # noqa: F401
from tests.test_book_pdf import _book

#: The owner's first book, as she gave it.
TITLE = "Christmas Nonograms"
SUBTITLE = "160 Festive Puzzles — Easy, Medium & Hard"
SERIES = "Anna & Olga’s Ultimate Puzzle Selection"
AUTHORS = "Anna and Olga"

#: The tone the page sets secondary text in, as the request states it.
GREY = 0.37


# --------------------------------------------------------------------------
# The title page
# --------------------------------------------------------------------------


def _title_book(**lines):
    book = _book()
    book.metadata.title = TITLE
    book.created_at = datetime(2026, 11, 9)
    for name, value in lines.items():
        setattr(book, name, value)
    return book


def _placed(book, puzzle_count=160):
    stream = BookPDFGenerator(book).vector_title_contents(puzzle_count)
    return placed_text(stream.render().decode("cp1252"))


def _texts(book, puzzle_count=160):
    return [text for _x, _y, _size, text in _placed(book, puzzle_count)]


def _sized(book, wanted):
    """``(y, size)`` of the one placed string equal to ``wanted``."""
    found = [(y, size) for _x, y, size, text in _placed(book) if text == wanted]
    assert len(found) == 1, (wanted, _texts(book))
    return found[0]


class TestTitlePage_PrintsEachField:
    def test_the_owners_values_all_print(self) -> None:
        book = _title_book(subtitle=SUBTITLE, series_name=SERIES, authors=AUTHORS)
        texts = _texts(book)

        assert SERIES.upper() in texts
        assert TITLE in texts
        assert SUBTITLE in texts
        assert f"by {AUTHORS}" in texts
        assert f"Copyright © 2026 {AUTHORS}. All rights reserved." in texts
        assert "No part of this book may be reproduced without written permission." in texts

    def test_top_to_bottom_order_and_sizes(self) -> None:
        """Series above the title, then subtitle, then the author line.

        PDF y grows upwards, so "above" is a larger y.
        """
        book = _title_book(subtitle=SUBTITLE, series_name=SERIES, authors=AUTHORS)
        series = _sized(book, SERIES.upper())
        title = _sized(book, TITLE)
        subtitle = _sized(book, SUBTITLE)
        by = _sized(book, f"by {AUTHORS}")

        assert series[0] > title[0] > subtitle[0] > by[0]
        assert 10.0 <= series[1] <= 11.0
        assert title[1] == 32.0
        assert subtitle[1] == 14.0
        assert by[1] == 13.0

    def test_nothing_is_set_below_the_ten_point_floor(self) -> None:
        book = _title_book(subtitle=SUBTITLE, series_name=SERIES, authors=AUTHORS)
        assert min(size for _x, _y, size, _t in _placed(book)) >= 10.0

    def test_the_secondary_lines_are_grey_and_the_title_is_emboldened(self) -> None:
        book = _title_book(subtitle=SUBTITLE, series_name=SERIES, authors=AUTHORS)
        operators = BookPDFGenerator(book).vector_title_contents(160).operators

        def operator_for(text):
            [found] = [op for op in operators if f"({text})" in op]
            return found

        for text in (SERIES.upper(), SUBTITLE):
            assert operator_for(text).startswith(f"{GREY} g "), operator_for(text)
        title = operator_for(TITLE)
        assert " 2 Tr " in title and f" {32 * 0.04:g} w " in title, title

    def test_the_title_lines_are_centred_on_the_usable_width(self) -> None:
        """Each line's centre is the same x, whatever its length."""
        from nonogram.admin.book_vector import interior_face_metrics

        face = interior_face_metrics()
        book = _title_book(subtitle=SUBTITLE, series_name=SERIES, authors=AUTHORS)
        centres = {
            round(x + face.advance(text) * size / 2, 1)
            for x, _y, size, text in _placed(book)
        }
        assert len(centres) == 1, centres


class TestTitlePage_UnsetFieldsAreLeftOut:
    def test_no_lines_set_prints_the_count_and_the_plain_notice(self) -> None:
        texts = _texts(_title_book())

        assert texts[0] == TITLE
        assert "160 picture puzzles" in texts
        assert "Copyright © 2026. All rights reserved." in texts
        assert not any(text.startswith("by ") for text in texts)
        assert len(texts) == 4, texts

    def test_a_subtitle_replaces_the_puzzle_count(self) -> None:
        texts = _texts(_title_book(subtitle=SUBTITLE))

        assert SUBTITLE in texts
        assert not any("picture puzzle" in text for text in texts)

    def test_no_series_means_nothing_above_the_title(self) -> None:
        placed = _placed(_title_book(subtitle=SUBTITLE, authors=AUTHORS))
        title_y = next(y for _x, y, _s, text in placed if text == TITLE)
        assert not [text for _x, y, _s, text in placed if y > title_y]

    def test_authors_alone_print_the_by_line_and_name_the_holder(self) -> None:
        texts = _texts(_title_book(authors=AUTHORS))

        assert f"by {AUTHORS}" in texts
        assert "160 picture puzzles" in texts
        assert f"Copyright © 2026 {AUTHORS}. All rights reserved." in texts

    def test_a_blank_stored_line_counts_as_unset(self) -> None:
        assert _texts(_title_book(series_name="  ", subtitle="", authors=None)) == _texts(
            _title_book()
        )


class TestTitlePage_WinAnsi:
    def test_the_owners_characters_are_representable_as_they_are(self) -> None:
        """"—", "&", "’" and "©" are WinAnsi: none needs a substitute."""
        for character in "—&’©":
            encode_text(character)
            assert _settable(character) == character

    def test_an_unrepresentable_character_is_substituted_not_refused(self) -> None:
        book = _title_book(
            subtitle="Minus − one", series_name="Prőbe ☃", authors="A B"
        )
        texts = _texts(book)

        assert "Minus - one" in texts
        assert "PROBE ?" in texts
        assert "by A B" in texts


# --------------------------------------------------------------------------
# Storage: the domain's cleaning, the model and both storage modes
# --------------------------------------------------------------------------


class TestTitlePageText_LightValidation:
    def test_strips_and_blank_is_none(self) -> None:
        assert title_page_text("  Anna and Olga \n", "authors") == "Anna and Olga"
        assert title_page_text("   ", "authors") is None
        assert title_page_text("", "authors") is None
        assert title_page_text(None, "authors") is None

    def test_the_longest_line_is_kept_and_one_more_is_refused(self) -> None:
        assert title_page_text("x" * TITLE_PAGE_TEXT_MAX, "subtitle") == "x" * TITLE_PAGE_TEXT_MAX
        with pytest.raises(InvalidBookDetails) as refused:
            title_page_text("x" * (TITLE_PAGE_TEXT_MAX + 1), "subtitle")
        assert refused.value.fields == {"subtitle"}


def _general_info(book, **overrides):
    form = {
        "title": book.metadata.title,
        "description": book.metadata.description,
        "theme": book.metadata.theme,
        "target_audience": book.metadata.target_audience,
    }
    form.update(overrides)
    return form


class TestTitlePage_GeneralInfoForm:
    """The three lines live on General info, beside the title they go with."""

    def test_the_form_saves_shows_and_clears_them(self, panel) -> None:  # noqa: F811
        book_id = panel.books.create_book("Winter", "a book", "christmas", "adults")
        book = panel.books.get_book(book_id)
        assert (book.subtitle, book.series_name, book.authors) == (None, None, None)

        response = panel.client.post(
            f"/book/{book_id}/edit",
            data=_general_info(
                book, subtitle=f" {SUBTITLE} ", series_name=SERIES, authors=AUTHORS
            ),
        )
        assert response.status_code == 302, response.get_data(as_text=True)[:400]
        stored = panel.books.get_book(book_id)
        assert (stored.subtitle, stored.series_name, stored.authors) == (
            SUBTITLE,
            SERIES,
            AUTHORS,
        )

        page = panel.client.get(f"/book/{book_id}/edit").get_data(as_text=True)
        for name in TITLE_PAGE_FIELDS:
            assert f'name="{name}"' in page
        assert "Anna &amp; Olga" in page and AUTHORS in page

        panel.client.post(
            f"/book/{book_id}/edit",
            data=_general_info(stored, subtitle="  ", series_name="", authors=AUTHORS),
        )
        cleared = panel.books.get_book(book_id)
        assert (cleared.subtitle, cleared.series_name, cleared.authors) == (
            None,
            None,
            AUTHORS,
        )

    def test_a_form_without_the_fields_keeps_what_is_stored(self, panel) -> None:  # noqa: F811
        book_id = panel.books.create_book(
            "Winter", "a book", "christmas", "adults", authors=AUTHORS
        )
        book = panel.books.get_book(book_id)
        panel.client.post(f"/book/{book_id}/edit", data=_general_info(book, title="Renamed"))

        stored = panel.books.get_book(book_id)
        assert stored.metadata.title == "Renamed"
        assert stored.authors == AUTHORS

    def test_a_too_long_line_stores_nothing_and_is_marked(self, panel) -> None:  # noqa: F811
        book_id = panel.books.create_book("Winter", "a book", "christmas", "adults")
        book = panel.books.get_book(book_id)
        response = panel.client.post(
            f"/book/{book_id}/edit",
            data=_general_info(
                book, title="Renamed", subtitle="x" * (TITLE_PAGE_TEXT_MAX + 1), authors=AUTHORS
            ),
        )
        assert response.status_code == 200
        page = response.get_data(as_text=True)
        assert 'id="subtitle"' in page and "is-invalid" in page

        stored = panel.books.get_book(book_id)
        assert stored.metadata.title == "Winter"
        assert (stored.subtitle, stored.authors) == (None, None)

    def test_creation_takes_them_too(self, panel) -> None:  # noqa: F811
        response = panel.client.post(
            "/book/create",
            data={
                "title": TITLE,
                "description": "a book",
                "theme": "christmas",
                "target_audience": "adults",
                "subtitle": SUBTITLE,
                "series_name": "",
            },
        )
        assert response.status_code == 302
        [book] = [b for b in panel.books.get_all_books() if b.metadata.title == TITLE]
        assert (book.subtitle, book.series_name, book.authors) == (SUBTITLE, None, None)


class TestTitlePage_Migration020:
    def _module(self):
        import importlib.util
        import pathlib

        path = (
            pathlib.Path(__file__).resolve().parent.parent
            / "migrations"
            / "versions"
            / "020_book_title_page.py"
        )
        spec = importlib.util.spec_from_file_location("migration_020", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_it_follows_019(self) -> None:
        module = self._module()
        assert (module.revision, module.down_revision) == ("020", "019")
        assert set(module.TITLE_PAGE_COLUMNS) == set(TITLE_PAGE_FIELDS)

    def test_it_states_no_default_and_no_backfill(self) -> None:
        import inspect

        source = inspect.getsource(self._module().upgrade)
        assert "server_default" not in source
        assert "update()" not in source
        assert "nullable=True" in source

    def test_the_model_declares_the_same_three_nullable_columns(self) -> None:
        from nonogram.db.models import Book as DBBook

        for name in TITLE_PAGE_FIELDS:
            column = DBBook.__table__.columns[name]
            assert column.nullable
            assert column.default is None and column.server_default is None

    def test_upgrade_leaves_null_and_downgrade_drops_them(self, tmp_path, monkeypatch) -> None:
        import sqlalchemy as sa

        from tests.test_book_page_spec import _alembic

        url = f"sqlite:///{tmp_path / 'migrate-020.db'}"
        command, config = _alembic(url, monkeypatch)
        command.upgrade(config, "019")
        engine = sa.create_engine(url)
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO books (id, title, puzzle_ids, puzzle_titles,"
                    " book_metadata, status) VALUES ('b1', 'Winter', '[]', '{}',"
                    " '{}', 'draft')"
                )
            )

        command.upgrade(config, "020")
        with engine.begin() as conn:
            row = conn.execute(
                sa.text("SELECT subtitle, series_name, authors FROM books WHERE id = 'b1'")
            ).one()
            assert tuple(row) == (None, None, None)
            conn.execute(
                sa.text("UPDATE books SET authors = :a WHERE id = 'b1'"), {"a": AUTHORS}
            )
            assert conn.execute(
                sa.text("SELECT authors FROM books WHERE id = 'b1'")
            ).scalar() == AUTHORS

        command.downgrade(config, "019")
        with engine.begin() as conn:
            assert conn.execute(
                sa.text("SELECT title FROM books WHERE id = 'b1'")
            ).scalar() == "Winter"
            for name in TITLE_PAGE_FIELDS:
                with pytest.raises(Exception):
                    conn.execute(sa.text(f"SELECT {name} FROM books"))
