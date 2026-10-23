"""The puzzle review page's Book filter: the dropdown names its books.

Reported by the owner 2026-10-23 as "filter by books does not work — add books
in the dropdown and filter by them". Measured before anything was changed, and
the two halves turned out to be in different states:

* the **filter** half already worked. ``?book_id=<id>`` listed only that book's
  puzzles and ``?book_id=unassigned`` only the loose ones.
* the **dropdown** half rendered one ``<option>`` per book with the right
  ``value`` and an **empty label**::

      <option value="book_000001"></option>

  so every book was in the list and none of them could be seen or picked. From
  the page that reads as "there are no books to filter by", which is what was
  reported.

The cause is one attribute. ``book_manager.Book`` keeps its title in
``metadata.title`` (a ``BookMetadata``) and has no ``.title`` of its own, while
``puzzles_list.html`` asked for ``book.title``. Jinja's default undefined
renders as the empty string rather than raising, so the page stayed 200 and the
defect was silent.

The sweep that followed is the interesting part, because it says why this one
template was wrong and nine others right: wherever a **Book object** reaches a
template the template says ``book.metadata.title``
(``books_list``, ``book_create``, ``book_detail``, ``book_finalize``,
``book_setup_print``, ``book_arrange_puzzles``, ``_confirm_membership_change``),
and wherever a **dict** reaches one the server already flattened it — the
``books`` JSON at ``app.py:6132`` is built as
``{"id": b.book_id, "title": b.metadata.title}``, so ``_puzzle_table.html``'s
``book.title`` and ``puzzle_edit.html``'s are correct over *their* payloads.
``puzzles_list.html`` received a Book object and used the dict spelling.

So these tests pin the **label**, not the value: the value was never wrong, and
a test that only asserted the option existed would have passed throughout. That
is the control this page lacked — ``test_puzzles_list_pagination.py`` and
``test_card_066_status_filter.py`` cover this page's other filters, and
``test_admin_filter_side_range_and_name.py`` covers it on both stores, and none
of the three reads the Book dropdown's text.

Both stores, via the ``STORES`` fixture shape that CARD-160 established and
``test_admin_filter_side_range_and_name.py`` uses, because the panel the owner
runs is DB-backed (Postgres) and an in-memory-only test would say nothing about
it: the template is shared, but ``filter_puzzles``' book arm is two different
implementations — a dict comparison in memory, a ``UUID`` conversion and a SQL
predicate on a database. SQLite stands in for Postgres here following
``test_book_metadata_column.py``'s reasoning: the behaviour under test is which
attribute is read and which column is compared, not the backend, and a sqlite
file needs no server to be running.

The last class covers the same defect class one control over: the route's
``except ValueError`` branch rendered the page without ``strategies``, so a
rejected filter quietly emptied the Strategy dropdown — an undefined rendering
as nothing, exactly like ``book.title``.
"""

import re

import pytest

import nonogram.admin.image_manager as image_manager_module
from nonogram.admin import book_manager as book_manager_module
from nonogram.admin.book_manager import BookManager
from tests.helpers.db import sqlite_session_scope

#: ``book_manager.BOOK_THEMES`` — a book's theme is a closed vocabulary and
#: ``create_book`` refuses anything else, so the fixture needs a real one.
A_REAL_THEME = "christmas"

#: Both stores the panel runs on. The owner's panel is the second one.
STORES = ("memory", "sqlite")


def _build_app(store, scope, monkeypatch):
    """The panel on the named store — the shape CARD-160 established."""
    from nonogram.admin.app import create_app

    monkeypatch.setenv("TESTING", "true")
    image_manager_module._image_manager = None
    if store == "memory":
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # A module-level singleton holding its books in a dict, so without this
        # a book created by one test is still in the next test's dropdown.
        monkeypatch.setattr(
            book_manager_module, "_book_manager", BookManager(session_factory=None)
        )
    else:
        import nonogram.db

        monkeypatch.setenv("DATABASE_URL", "sqlite:///book-filter-test-only")
        monkeypatch.setattr(nonogram.db, "session_scope", scope)
    app = create_app()
    app.config["TESTING"] = True
    # Exercise the store named, never a silent fallback to the other one.
    assert (app.puzzle_review_service._session_factory is None) == (store == "memory")
    assert (app.book_manager._session_factory is None) == (store == "memory")
    return app


@pytest.fixture(params=STORES)
def panel(request, tmp_path, monkeypatch):
    scope = sqlite_session_scope(tmp_path, "book-filter.db") if request.param == "sqlite" else None
    app = _build_app(request.param, scope, monkeypatch)
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


def _make_book(panel, title):
    return panel.book_manager.create_book(
        title=title,
        description=f"{title} — a collection of nonograms.",
        theme=A_REAL_THEME,
        target_audience="seniors",
    )


def _add_puzzle(panel, source_image):
    """Store one approved 10x10 puzzle and return its id."""
    store = panel.puzzle_review_service
    puzzle_id = store.add_puzzle(
        grid=[[True] * 10 for _ in range(10)],
        clues_rows=[[10]] * 10,
        clues_cols=[[10]] * 10,
        width=10,
        height=10,
        theme="test",
        difficulty_score=10,
        difficulty_tier="Easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        source_image=source_image,
    )
    assert store.approve_puzzle(puzzle_id)
    return puzzle_id


def _options(html, name):
    """Every ``(value, label)`` in the named select, in document order.

    Parsed out of that one select rather than off the whole page, so a book
    title appearing elsewhere in the markup cannot satisfy an assertion about
    the dropdown.
    """
    block = re.search(rf'<select[^>]*name="{name}".*?</select>', html, re.S)
    assert block, f"the puzzle review page has no {name} dropdown at all"
    return [
        (value, label.strip())
        for value, label in re.findall(
            r'<option value="([^"]*)"[^>]*>(.*?)</option>', block.group(0), re.S
        )
    ]


def _page(panel, query=""):
    response = panel.test_client().get(f"/puzzles?{query}")
    assert response.status_code == 200, response.status_code
    return response.get_data(as_text=True)


class TestPuzzleReviewBookFilter_TheDropdownNamesItsBooks:
    """The Book dropdown's **labels** — the half that was broken."""

    def test_each_book_option_carries_the_book_title_as_its_label(self, panel):
        """A book in the dropdown is one the owner can read and therefore pick.

        Asserted on the label, because the value was already right before the
        fix: ``<option value="book_000001"></option>`` is in the list and
        invisible. Two books, so this also fails if the template renders one
        title for every option.
        """
        first = _make_book(panel, "Winter Logic Puzzles")
        second = _make_book(panel, "Spring Logic Puzzles")

        options = _options(_page(panel), "book_id")
        by_value = dict(options)

        assert by_value.get(first) == "Winter Logic Puzzles", options
        assert by_value.get(second) == "Spring Logic Puzzles", options

    def test_no_option_in_the_dropdown_is_nameless(self, panel):
        """The arm that reds on the original defect however it is reached.

        Independent of the two titles above: it would catch a book rendered
        under some *other* empty attribute, and it covers the fixed All and
        Unassigned entries too.
        """
        _make_book(panel, "Winter Logic Puzzles")

        options = _options(_page(panel), "book_id")

        assert all(label for _, label in options), f"a nameless option: {options}"

    def test_the_fixed_entries_keep_their_own_labels(self, panel):
        """"All" and "Unassigned" are not books and must survive the fix.

        A repair that mapped every option's label through a book would have
        emptied these two, and nothing else on the page would have said so.
        """
        _make_book(panel, "Winter Logic Puzzles")

        options = _options(_page(panel), "book_id")

        assert options[0] == ("", "All"), options
        assert options[1] == ("unassigned", "Unassigned"), options

    def test_with_no_books_the_dropdown_still_offers_all_and_unassigned(self, panel):
        """The empty case: no books is not an error and not a missing control."""
        assert _options(_page(panel), "book_id") == [("", "All"), ("unassigned", "Unassigned")]

    def test_the_selected_book_is_marked_so_the_page_shows_its_own_filter(self, panel):
        """Picking a book and reloading keeps the dropdown on that book."""
        book_id = _make_book(panel, "Winter Logic Puzzles")

        html = _page(panel, f"book_id={book_id}")
        block = re.search(r'<select[^>]*name="book_id".*?</select>', html, re.S).group(0)

        assert re.findall(r'<option value="([^"]*)"[^>]*\bselected\b', block) == [book_id], block


class TestPuzzleReviewBookFilter_FilteringByBook:
    """The filter half. It worked before the fix; these pin it so it stays.

    Without them the fix would be a page that *names* books over a filter
    nobody checks — and the owner reported the two halves as one defect. On the
    sqlite store this is also the only coverage of the ``UUID`` conversion the
    DB branch does, which the in-memory branch has no equivalent of.
    """

    @pytest.fixture
    def corpus(self, panel):
        in_book = _add_puzzle(panel, "in_book.png")
        _add_puzzle(panel, "loose.png")
        book_id = _make_book(panel, "Winter Logic Puzzles")
        assert panel.book_manager.add_puzzles_to_book(book_id, [in_book])
        return panel, book_id

    def test_a_books_own_puzzles_are_the_only_ones_listed(self, corpus):
        panel, book_id = corpus

        unfiltered = _page(panel)
        filtered = _page(panel, f"book_id={book_id}")

        # Caught WITH the filter, missed WITHOUT it: the unfiltered page is the
        # control, so this cannot pass on a page that happens to list nothing.
        assert "in_book.png" in unfiltered and "loose.png" in unfiltered
        assert "in_book.png" in filtered
        assert "loose.png" not in filtered

    def test_unassigned_lists_exactly_the_puzzles_no_book_holds(self, corpus):
        panel, _ = corpus

        filtered = _page(panel, "book_id=unassigned")

        assert "loose.png" in filtered
        assert "in_book.png" not in filtered

    def test_the_dropdown_offers_the_id_the_filter_accepts(self, corpus):
        """The two halves meet: the option's value filters when submitted.

        The defect was invisible partly because these were never checked
        together — a value nobody could pick is also a value nobody tried.
        """
        panel, book_id = corpus

        values = [value for value, _ in _options(_page(panel), "book_id")]
        assert book_id in values, values

        assert "in_book.png" in _page(panel, f"book_id={book_id}")


class TestPuzzleReviewBookFilter_AFilterErrorKeepsTheForm:
    """The same defect class one control over: an undefined that renders empty.

    The route's ``except ValueError`` branch re-rendered the page without
    ``strategies``, so a rejected filter emptied the Strategy dropdown while
    the page stayed 200 — invisible for the same reason ``book.title`` was.
    """

    def test_a_rejected_filter_offers_the_same_choices_as_an_accepted_one(self, panel):
        """The error page's dropdowns are compared against the normal page's.

        The obvious assertions here are both **vacuous**, and the first draft
        of this test used one: every one of these selects carries a static
        first option (``All`` for the book, ``Any`` for status and strategy),
        so "the dropdown has options" and "no option is nameless" are satisfied
        by that static entry alone — with ``strategies`` undefined the strategy
        select still renders ``Any`` and nothing else, and the test passed.
        Caught by reverting the fix and watching nothing go red.

        So the control is the accepted page: same options, same order, or the
        error branch has stopped passing something the form needs.
        """
        _make_book(panel, "Winter Logic Puzzles")

        accepted = _page(panel)
        # `limit` outside 1..100 is refused by `filter_puzzles` itself, so this
        # reaches the route's error branch rather than a 400 from parsing.
        rejected = _page(panel, "limit=999")

        assert "Filter error" in rejected, "the refusal is not reported to the owner"
        for name in ("book_id", "status", "strategy"):
            assert _options(rejected, name) == _options(accepted, name), (
                f"the {name} dropdown differs on the error page: "
                f"{_options(rejected, name)} vs {_options(accepted, name)}"
            )

    def test_the_strategy_dropdown_offers_more_than_its_static_entry(self, panel):
        """A floor under the comparison above, in case both pages lose them.

        An equality holds two things to each other and says nothing if they
        break together — if the route ever stopped passing ``strategies`` on
        *both* branches, every select would still match. This names the floor:
        the real choices are there, not only the static ``Any``.
        """
        options = _options(_page(panel), "strategy")

        assert options[0] == ("", "Any"), options
        assert len(options) > 1, f"only the static entry is offered: {options}"
