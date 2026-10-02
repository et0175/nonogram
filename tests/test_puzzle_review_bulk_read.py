"""CARD-157 — a book's puzzles are read in one query, not one session per puzzle.

    AC-1  test_PropertyTest_BulkRead_MatchesPerIdReads  (seeded corpus, >= 200 cases)
    AC-2  TestBookPaths_SessionCountDoesNotScaleWithBookSize
    AC-3  TestBulkRead_IgnoresTheMembershipMirror

``PuzzleReviewService.get_puzzles`` is held to ``get_puzzle``: for any mix of
present, absent and malformed ids it returns exactly the records the per-id
reads return, keyed by the id as the caller gave it, with every id that
``get_puzzle`` answers ``None`` for — or refuses with ``ValueError`` /
``TypeError``, the two every caller already treated as "no row" — left out.
The oracle is the per-id read itself, called one id at a time, never the bulk
method under test.

DB mode here is the real Postgres ``nonogram_test`` database (``db_session``
from ``tests/conftest.py``), not SQLite: the ``IN (...)`` query is the thing
under test and production runs it on Postgres.

The session counts of AC-2 are taken by wrapping the session factory the
panel's own services hold with a counter, so every session the three routes
open through the puzzle store or the book manager is counted, and the count
for a small book is compared with the count for a book ten times its size.

AC-3 empties and falsifies the ``puzzles.book_id`` mirror and checks that the
three paths still see the whole membership, because ADR-0033/R1 says
membership is the book's own ``puzzle_ids`` and nothing reads it from the
mirror.
"""

from __future__ import annotations

import html as html_module
import random
import re
import uuid

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import BookManager, BookStatus, DistributionPlan, Split
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.difficulty import Tier
from tests.helpers.db import make_batch

MODES = ("memory", "db")

#: The three graded tiers, as the store spells them.
EASY, MEDIUM, HARD = "easy", "medium", "hard"

#: The two book sizes AC-2 compares: a book and one ten times its size.
SMALL, LARGE = 6, 60


# --------------------------------------------------------------------------
# seeding: rows written straight into the store
# --------------------------------------------------------------------------


def seed(store, tiers, factory=None) -> list:
    """One stored, approved 10x10 puzzle per entry of ``tiers``; their ids.

    Written straight into the store rather than through ``add_puzzle`` — the
    paths under test read a record's size, clues and stored tier and nothing
    else, and a thirty-puzzle book would otherwise cost thirty uniqueness
    proofs. A one-cell clue pair lays out far above the 4.8 mm floor, so every
    one of them can join a book. In DB mode they are real ``puzzles`` rows
    under a real batch (``puzzles.batch_id`` is a foreign key).
    """
    ids = [str(uuid.uuid4()) for _ in tiers]
    if factory is None:
        for puzzle_id, tier in zip(ids, tiers):
            store.puzzles[puzzle_id] = {
                "id": puzzle_id,
                "width": 10,
                "height": 10,
                "grid": [[True] * 10 for _ in range(10)],
                "clues_rows": [[1]],
                "clues_cols": [[1]],
                "difficulty_tier": tier,
                "status": "approved",
                "book_id": None,
            }
        return ids

    from nonogram.db.models import Puzzle

    batch = make_batch(factory, source="random")
    with factory() as db:
        db.add_all(
            Puzzle(
                id=uuid.UUID(puzzle_id),
                batch_id=uuid.UUID(batch),
                grid=[[True] * 10 for _ in range(10)],
                clues_rows=[[1]],
                clues_cols=[[1]],
                width=10,
                height=10,
                difficulty_tier=tier,
                status="approved",
                source_image=f"{tier}-{puzzle_id[:8]}.png",
            )
            for puzzle_id, tier in zip(ids, tiers)
        )
    return ids


def per_id_reads(store, ids) -> dict:
    """The oracle: ``get_puzzle`` one id at a time, as every caller did.

    An id ``get_puzzle`` refuses with ``ValueError`` or ``TypeError`` is one no
    row can match — the verdict all three callers already reached by catching
    those two — and an id it answers ``None`` for matches no row.
    """
    expected = {}
    for puzzle_id in ids:
        try:
            record = store.get_puzzle(puzzle_id)
        except (ValueError, TypeError):
            continue
        if record is not None:
            expected[puzzle_id] = record
    return expected


class CountingFactory:
    """A session factory that counts the sessions opened through it."""

    def __init__(self, inner):
        self.inner = inner
        self.opened = 0

    def __call__(self):
        self.opened += 1
        return self.inner()


@pytest.fixture
def db_store(db_session):
    """A puzzle store over the real Postgres test database."""
    from nonogram.db import session_scope

    return PuzzleReviewService(session_factory=session_scope)


@pytest.fixture(params=MODES)
def store(request):
    """A puzzle store in one storage mode; DB mode is the real Postgres."""
    if request.param == "memory":
        return PuzzleReviewService(session_factory=None)
    return request.getfixturevalue("db_store")


# --------------------------------------------------------------------------
# AC-1: the bulk read is the per-id read, over a seeded corpus
# --------------------------------------------------------------------------


#: Strings that are not UUIDs, and so match no row in either mode.
MALFORMED = (
    "",
    "not-a-uuid",
    "123",
    "book_1",
    "00000000-0000-0000-0000",  # a UUID cut short
    "g" * 32,  # the right length, not hex
    " ",
)


def _corpus_case(rng, present, store):
    """One id list: present, absent and malformed ids, with repeats."""
    pool = []
    for _ in range(rng.randint(0, 12)):
        kind = rng.choice(("present", "present", "upper", "absent", "malformed", "uuid"))
        if kind == "present" and present:
            pool.append(rng.choice(present))
        elif kind == "upper" and present:
            # Another spelling of a present id: Postgres finds the row through
            # it, the in-memory dict does not. Either way the bulk read must
            # answer what the per-id read answers, under the id as given.
            pool.append(rng.choice(present).upper())
        elif kind == "uuid" and present:
            # A ``uuid.UUID`` rather than its string, which ``get_puzzle``
            # passes straight to the query.
            pool.append(uuid.UUID(rng.choice(present)))
        elif kind == "absent":
            pool.append(str(uuid.UUID(int=rng.getrandbits(128))))
        else:
            pool.append(rng.choice(MALFORMED))
    if pool and rng.random() < 0.3:
        pool.append(rng.choice(pool))  # a repeated id
    if store._session_factory is None and rng.random() < 0.1:
        # Memory mode only: an unhashable id, which the dict refuses with
        # TypeError. (DB mode would hand it to the driver, which no caller
        # does and no caller ever did.)
        pool.append(["not", "hashable"])
    return pool


def test_PropertyTest_BulkRead_MatchesPerIdReads(store) -> None:
    """AC-1: ``get_puzzles(ids)`` equals ``get_puzzle`` on each id, in both modes."""
    present = seed(store, [EASY, MEDIUM, HARD, None] * 6, store._session_factory)
    counter = None
    if store._session_factory is not None:
        counter = CountingFactory(store._session_factory)
        store._session_factory = counter

    rng = random.Random(157)
    cases = 0
    for _ in range(240):
        ids = _corpus_case(rng, present, store)
        expected = per_id_reads(store, ids)

        before = counter.opened if counter else 0
        got = store.get_puzzles(ids)
        opened = (counter.opened - before) if counter else 0

        assert got == expected, f"case {cases}: ids={ids!r}"
        # One session for the whole list in DB mode, never one per id.
        assert opened <= 1, f"case {cases}: {opened} sessions for {len(ids)} ids"
        cases += 1

    assert cases >= 200, f"the corpus shrank to {cases} cases"


class TestBulkRead_Edges:
    """The branches the corpus reaches only by chance, each pinned once."""

    def test_an_empty_list_reads_nothing(self, store) -> None:
        if store._session_factory is not None:
            store._session_factory = CountingFactory(store._session_factory)
        assert store.get_puzzles([]) == {}
        if store._session_factory is not None:
            assert store._session_factory.opened == 0

    def test_a_list_of_malformed_ids_opens_no_session(self, db_store) -> None:
        """No id can match a row, so there is nothing to ask the database."""
        store = db_store
        counter = CountingFactory(store._session_factory)
        store._session_factory = counter
        assert store.get_puzzles(list(MALFORMED)) == {}
        assert counter.opened == 0

    def test_malformed_ids_beside_a_present_one_are_left_out(self, store) -> None:
        (present,) = seed(store, [EASY], store._session_factory)
        got = store.get_puzzles(["not-a-uuid", present, ""])
        assert list(got) == [present]
        assert got[present]["id"] == present
        assert got[present]["difficulty_tier"] == EASY

    def test_an_absent_id_is_left_out(self, store) -> None:
        (present,) = seed(store, [HARD], store._session_factory)
        absent = str(uuid.uuid4())
        assert list(store.get_puzzles([absent, present])) == [present]

    def test_an_unhashable_id_is_left_out_in_memory(self) -> None:
        """``get_puzzle`` raises TypeError for it; callers skipped it."""
        store = PuzzleReviewService(session_factory=None)
        (present,) = seed(store, [MEDIUM])
        assert list(store.get_puzzles([["x"], present])) == [present]

    def test_two_spellings_of_one_row_are_two_records(self, db_store) -> None:
        """Each id gets its own record, as two ``get_puzzle`` calls would.

        The arrange screen writes into the record it is handed; one shared
        dict under two keys would let one row's numbering leak into the
        other's.
        """
        store = db_store  # only Postgres resolves another spelling of an id
        (present,) = seed(store, [EASY], store._session_factory)
        got = store.get_puzzles([present, present.upper()])
        assert got[present] == got[present.upper()]
        assert got[present] is not got[present.upper()]


# --------------------------------------------------------------------------
# the panel: the real routes over one storage mode
# --------------------------------------------------------------------------


class Panel:
    """The app, its store and its books, with the three paths as one-liners."""

    def __init__(self, app, mode):
        self.app = app
        self.mode = mode
        self.store = app.puzzle_review_service
        self.books = app.book_manager
        self.client = app.test_client()

    @property
    def factory(self):
        return self.store._session_factory

    def puzzles(self, tiers) -> list:
        return seed(self.store, tiers, self.factory)

    def book(self, tiers, title="Winter"):
        """A draft book holding one new puzzle per entry of ``tiers``."""
        book_id = self.books.create_book(title, "a book", "christmas", "adults")
        ids = self.puzzles(tiers)
        if ids:
            assert self.books.add_puzzles_to_book(book_id, ids)
        assert len(self.books.get_book(book_id).puzzle_ids) == len(ids)
        return book_id, ids

    def ids_of(self, book_id):
        return [str(pid) for pid in self.books.get_book(book_id).puzzle_ids]

    def tick(self, book_id, puzzle_ids):
        """Keep ``puzzle_ids`` ticked for this book, as a tab switch does."""
        response = self.client.post(
            f"/book/{book_id}/select-puzzles",
            data={"puzzle_ids": list(puzzle_ids), "go_bucket": "<=15"},
        )
        assert response.status_code == 302, response.status_code

    def select(self, book_id):
        return self.client.get(f"/book/{book_id}/select-puzzles")

    def set_status(self, book_id, status):
        return self.client.post(f"/book/{book_id}/status", data={"status": status})

    def move(self, book_id, puzzle_id, direction):
        return self.client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={"action": f"move_{direction}", "puzzle_id": puzzle_id},
        )

    def counting(self) -> CountingFactory:
        """Count every session the store and the book manager open from now on."""
        counter = CountingFactory(self.store._session_factory)
        self.store._session_factory = counter
        self.books._session_factory = counter
        return counter


@pytest.fixture
def memory_panel(monkeypatch):
    """The panel in in-memory mode, with a book manager of its own."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    book_manager_module._book_manager = BookManager(session_factory=None)
    app = create_app()
    app.config["TESTING"] = True
    try:
        with app.app_context():
            yield Panel(app, "memory")
    finally:
        image_manager_module._image_manager = None
        book_manager_module._book_manager = BookManager(session_factory=None)


@pytest.fixture
def db_panel(app):
    """The panel over the real Postgres test database."""
    assert app.puzzle_review_service._session_factory is not None
    with app.app_context():
        yield Panel(app, "db")


@pytest.fixture(params=MODES)
def panel(request):
    return request.getfixturevalue(f"{request.param}_panel")


def _text(fragment: str) -> str:
    """A fragment of HTML as the words it reads as."""
    return " ".join(html_module.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def _book_summary(page: str) -> str:
    """The selection step's whole-book planned-vs-selected line, as text."""
    match = re.search(r'<p class="stat-line" id="bookSummary">(.*?)</p>', page, re.S)
    assert match, "the selection step rendered no whole-book summary"
    return _text(match.group(1))


def _arranged_ids(page: str) -> list:
    """The puzzle ids the arrange screen lists, in the order it lists them."""
    return list(dict.fromkeys(re.findall(r'/api/puzzle/([0-9a-fA-F-]{36})/grid', page)))


# --------------------------------------------------------------------------
# AC-2: each path opens a bounded number of sessions
# --------------------------------------------------------------------------


def _tiers(count):
    """``count`` tiers cycling easy, medium, hard."""
    return [(EASY, MEDIUM, HARD)[i % 3] for i in range(count)]


def measure_paths(panel, size) -> dict:
    """Sessions each path opens for a book of ``size`` plus ``size`` ticks."""
    book_id, members = panel.book(_tiers(size), title=f"Book of {size}")
    panel.tick(book_id, panel.puzzles(_tiers(size)))

    counts = {}
    counter = panel.counting()

    response = panel.select(book_id)
    assert response.status_code == 200
    counts["select"] = counter.opened

    counter.opened = 0
    # Refused at both sizes — neither book is the default 150-puzzle plan —
    # but the refusal is decided on the selection the gate reads, which is
    # the read under test.
    response = panel.set_status(book_id, BookStatus.READY_FOR_PDF.value)
    assert response.status_code == 302
    counts["status"] = counter.opened

    # The book's first puzzle is an easy one with another easy one after it,
    # at both sizes, so the move is made — not refused — in both.
    order = panel.ids_of(book_id)
    counter.opened = 0
    response = panel.move(book_id, order[0], "down")
    assert response.status_code == 200
    counts["arrange"] = counter.opened

    assert panel.books.get_book(book_id).status == BookStatus.DRAFT.value
    assert panel.ids_of(book_id)[:2] == [order[1], order[0]]

    # Put the real factory back for the next measurement.
    panel.store._session_factory = counter.inner
    panel.books._session_factory = counter.inner
    return counts


class TestBookPaths_SessionCountDoesNotScaleWithBookSize:
    """AC-2: a ten-times-larger book costs each path the same sessions."""

    def test_the_three_paths_cost_the_same_at_both_sizes(self, db_panel) -> None:
        small = measure_paths(db_panel, SMALL)
        large = measure_paths(db_panel, LARGE)
        print(f"\nsessions per path: {SMALL}-puzzle book {small}, {LARGE}-puzzle book {large}")
        assert small == large, (
            f"sessions grew with the book: {SMALL} puzzles {small}, {LARGE} puzzles {large}"
        )


# --------------------------------------------------------------------------
# AC-3: membership is the book's own list, never the mirror
# --------------------------------------------------------------------------


class TestBulkRead_IgnoresTheMembershipMirror:
    """AC-3: a stale or empty ``puzzles.book_id`` changes nothing on any path.

    The book's four members are E1, E2, M1, H1. Two have their mirror
    cleared and two have it pointed at another book, and every mirror value
    is checked to be wrong before the paths are driven.
    """

    @pytest.fixture
    def corrupted(self, panel):
        book_id, members = panel.book([EASY, EASY, MEDIUM, HARD])
        decoy, _ = panel.book([], title="Decoy")
        panel.store.release_from_book(members[:2])
        panel.store.assign_to_book(members[2:], decoy)
        for puzzle_id in members:
            assert panel.store.get_puzzle(puzzle_id)["book_id"] != book_id
        return panel, book_id, members

    def test_book_selection_counts_every_member(self, corrupted) -> None:
        panel, book_id, _members = corrupted
        summary = _book_summary(body(panel.select(book_id)))
        # Selected against the default plan every new book is given (150).
        assert summary == (
            "whole book: easy 2 / 60 · medium 1 / 60 · hard 1 / 30 · total 4 / 150"
        ), summary

    def test_the_status_change_reads_every_member(self, corrupted) -> None:
        """The plan names all four; a gate reading fewer would refuse."""
        panel, book_id, _members = corrupted
        panel.books.save_plan(
            book_id,
            DistributionPlan(
                count=4,
                split=Split(50, 25, 25),
                cells=((2, 1, 1), (0, 0, 0), (0, 0, 0), (0, 0, 0)),
            ),
        )
        response = panel.set_status(book_id, BookStatus.READY_FOR_PDF.value)
        assert response.status_code == 302
        assert panel.books.get_book(book_id).status == BookStatus.READY_FOR_PDF.value

    def test_the_arrange_screen_lists_and_moves_every_member(self, corrupted) -> None:
        panel, book_id, members = corrupted
        e1, e2, m1, h1 = members
        page = body(panel.move(book_id, e1, "down"))
        assert panel.ids_of(book_id) == [e2, e1, m1, h1]
        assert _arranged_ids(page) == [e2, e1, m1, h1]

    def test_a_move_across_a_level_is_still_refused(self, corrupted) -> None:
        """The tiers come from the rows by id, so the boundary still holds."""
        panel, book_id, members = corrupted
        e1, e2, m1, h1 = members
        body(panel.move(book_id, m1, "up"))
        assert panel.ids_of(book_id) == [e1, e2, m1, h1]


class TestBulkRead_TheCallersKeepTheirVerdicts:
    """What each caller made of an absent or malformed id, it still makes."""

    def test_the_gate_reads_in_book_order_with_repeats_and_names_what_it_skipped(
        self, store, caplog
    ) -> None:
        books = BookManager(session_factory=store._session_factory, puzzle_store=store)
        easy, hard = seed(store, [EASY, HARD], store._session_factory)
        absent = str(uuid.uuid4())
        with caplog.at_level("WARNING", logger="nonogram.admin.book_manager"):
            records = books._selection_records([hard, "not-a-uuid", easy, absent, hard])
        assert [r["id"] for r in records] == [hard, easy, hard]
        (logged,) = [r.getMessage() for r in caplog.records if "no row matches" in r.getMessage()]
        assert "'not-a-uuid'" in logged and repr(absent) in logged, logged

    def test_the_gate_logs_nothing_when_every_id_resolves(self, store, caplog) -> None:
        books = BookManager(session_factory=store._session_factory, puzzle_store=store)
        ids = seed(store, [EASY, MEDIUM], store._session_factory)
        with caplog.at_level("WARNING", logger="nonogram.admin.book_manager"):
            assert len(books._selection_records(ids)) == 2
        assert not [r for r in caplog.records if "no row matches" in r.getMessage()]

    def test_the_order_lookup_is_total_and_reads_only_what_it_was_not_told(
        self, store
    ) -> None:
        books = BookManager(session_factory=store._session_factory, puzzle_store=store)
        easy, hard = seed(store, [EASY, HARD], store._session_factory)
        asked = []
        real = store.get_puzzles

        def recording(ids):
            asked.append(list(ids))
            return real(ids)

        store.get_puzzles = recording
        tier_of = books._tier_of([easy, hard, "not-a-uuid", easy], known={hard: None})
        # The known tier is carried, not re-read; the rest are read once, together.
        assert asked == [[easy, "not-a-uuid"]]
        assert tier_of(easy) is Tier.EASY
        assert tier_of(hard) is None
        assert tier_of("not-a-uuid") is None

    def test_the_order_lookup_without_a_store_answers_none(self) -> None:
        books = BookManager(session_factory=None, puzzle_store=None)
        tier_of = books._tier_of(["a", "b"])
        assert tier_of("a") is None and tier_of("b") is None

    def test_a_malformed_tick_does_not_break_book_selection(self, panel) -> None:
        """A ticked id no row can match counts towards no cell, as a missing one."""
        book_id, _members = panel.book([EASY, MEDIUM])
        panel.tick(book_id, ["not-a-uuid"])
        summary = _book_summary(body(panel.select(book_id)))
        assert summary == (
            "whole book: easy 1 / 60 · medium 1 / 60 · hard 0 / 30 · total 2 / 150"
        ), summary


    def test_the_order_lookup_names_what_it_could_not_place_at_debug(
        self, store, caplog
    ) -> None:
        """Review cycle 1, F-002: the unplaceable ids are named, once, at DEBUG."""
        books = BookManager(session_factory=store._session_factory, puzzle_store=store)
        (easy,) = seed(store, [EASY], store._session_factory)
        absent = str(uuid.uuid4())
        with caplog.at_level("DEBUG", logger="nonogram.admin.book_manager"):
            books._tier_of([easy, "not-a-uuid", absent])
        logged = [r for r in caplog.records if "resolve to no row" in r.getMessage()]
        assert len(logged) == 1, [r.getMessage() for r in logged]
        assert logged[0].levelname == "DEBUG"
        message = logged[0].getMessage()
        assert "'not-a-uuid'" in message and repr(absent) in message, message
        assert repr(easy) not in message, message

    def test_the_order_lookup_logs_nothing_when_every_id_resolves(
        self, store, caplog
    ) -> None:
        books = BookManager(session_factory=store._session_factory, puzzle_store=store)
        ids = seed(store, [EASY, HARD], store._session_factory)
        with caplog.at_level("DEBUG", logger="nonogram.admin.book_manager"):
            books._tier_of(ids)
        assert not [r for r in caplog.records if "resolve to no row" in r.getMessage()]


# --------------------------------------------------------------------------
# review cycle 1, F-001: the arrange screen shows each row's custom title
# --------------------------------------------------------------------------


def _name(panel, puzzle_id, name) -> None:
    """Give a stored puzzle a ``puzzle_name``, straight into the store."""
    if panel.factory is None:
        panel.store.puzzles[puzzle_id]["puzzle_name"] = name
        return
    from nonogram.db.models import Puzzle

    with panel.factory() as db:
        db.query(Puzzle).filter(Puzzle.id == uuid.UUID(puzzle_id)).update(
            {"puzzle_name": name}
        )
        db.commit()


def _title_value(page: str, puzzle_id: str) -> str:
    """The value of the arrange row's title input for ``puzzle_id``."""
    match = re.search(
        r'<input[^>]*id="title_' + re.escape(puzzle_id) + r'"[^>]*>', page, re.S
    )
    assert match, f"the arrange screen rendered no title input for {puzzle_id}"
    value = re.search(r'value="([^"]*)"', match.group(0))
    assert value, match.group(0)
    return html_module.unescape(value.group(1))


class TestBookArrange_ShowsTheCustomTitleOfEachRow:
    """The titles now come from one read of the book; each row still shows its own."""

    def test_a_custom_title_shows_and_an_untitled_row_falls_back_to_its_name(
        self, panel
    ) -> None:
        book_id, (titled, untitled) = panel.book([EASY, EASY])
        _name(panel, titled, "Stored name of the titled one")
        _name(panel, untitled, "Stored name of the untitled one")
        assert panel.books.set_puzzle_title(book_id, titled, "Snow & Stars")

        page = body(panel.client.get(f"/book/{book_id}/arrange-puzzles"))

        assert _title_value(page, titled) == "Snow & Stars"
        assert _title_value(page, untitled) == "Stored name of the untitled one"


def body(response) -> str:
    assert response.status_code == 200, response.status_code
    return response.get_data(as_text=True)
