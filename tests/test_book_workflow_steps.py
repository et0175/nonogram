"""CARD-130 — a book reopens into its step workflow (FR-038).

    AC-222  TestBookDetail_LinksToEveryStep
    AC-223  TestBooksList_OpensBookInStepWorkflow
    AC-224  TestBookGeneralInfo_EditsExistingBook
    AC-225  TestBookSteps_ReachableWhateverStatus
    G-2     TestBookSteps_RevisitingDiscardsNothing                 (EC-026)
    CK-1    TestBookStepper_KeysAreTheOnesTheStepPagesStillPass

The user-facing half is driven through the Flask test client against the real
routes, because this project has no browser harness — the same convention
``tests/test_book_ready_gate.py`` and ``tests/test_book_select_floor_tiles.py``
follow. The storage half (``BookManager.update_book_details``) runs in **both**
storage modes: in memory, and DB mode against a real SQLite file.

The five step URLs are written out literally here rather than built through
``url_for`` or read back from the app's own mapping: the criteria are about the
pages the owner can reach, and a test that asks the code where its steps are
would agree with it however they moved.

G-2/EC-026 — revisiting a step discards nothing — is a standing property, not
one example, so it runs over a seeded corpus of books (varied membership,
arrangement, custom titles and statuses) built with stdlib ``random.Random``,
with the corpus size asserted inside the test so it cannot silently shrink.
"""

from __future__ import annotations

import random
import re
import uuid
from html.parser import HTMLParser

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import BookManager, BookStatus
from nonogram.admin.book_plan import BUCKETS, TIERS, LevelBoundary
from nonogram.admin.puzzle_review import PuzzleReviewService
from tests.helpers.db import make_batch, sqlite_session_scope

MODES = ("memory", "db")

#: Every status a book can be in, draft included.
EVERY_STATUS = tuple(status.value for status in BookStatus)


def step_paths(book_id: str) -> dict:
    """The five steps of the workflow, by the key the stepper matches on.

    Written out, not derived: these are the URLs the criteria name.
    """
    return {
        0: f"/book/{book_id}/edit",
        1: f"/book/{book_id}/setup-print",
        2: f"/book/{book_id}/select-puzzles",
        3: f"/book/{book_id}/arrange-puzzles",
        4: f"/book/{book_id}/finalize",
    }


#: The five labels the stepper prints, in order.
STEP_LABELS = (
    "General info",
    "Print setup",
    "Puzzle selection",
    "Arrangement",
    "Finalise & export",
)


# --------------------------------------------------------------------------
# Reading a rendered page
# --------------------------------------------------------------------------


class _Stepper(HTMLParser):
    """The one ``<ol class="stepper">`` of the book workflow, as read back.

    An independent reader rather than a regex over the macro's own markup:
    ``hrefs`` is every URL the list links to and ``labels`` is the text of
    each item, so a step rendered as plain text is visibly not a link.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found = False
        self._depth = 0
        self._muted = False
        self.hrefs: list = []
        self.labels: list = []
        self.current: list = []
        self._text: list = []

    def handle_starttag(self, tag, attrs) -> None:
        attributes = dict(attrs)
        if tag == "ol" and attributes.get("aria-label") == "Book scaffolding steps":
            self.found = True
            self._depth = 1
            return
        if not self._depth:
            return
        self._depth += 1
        if tag == "li":
            self._text = []
            if attributes.get("aria-current") == "step":
                self.current.append(len(self.labels))
        elif tag == "a" and attributes.get("href"):
            self.hrefs.append(attributes["href"])
        elif tag == "span" and attributes.get("class") == "step-n":
            # The printed number is not part of the label.
            self._muted = True
        elif tag == "small":
            # The hint under a label is not part of the label either.
            self._text.append("\x00")

    def handle_endtag(self, tag) -> None:
        if not self._depth:
            return
        if tag == "li":
            whole = "".join(self._text).split("\x00")[0]
            self.labels.append(" ".join(whole.split()))
        elif tag == "span" and self._muted:
            self._muted = False
        self._depth -= 1

    def handle_data(self, data) -> None:
        if self._depth and not self._muted:
            self._text.append(data)


def stepper_of(client, path: str) -> _Stepper:
    """The step list the page at ``path`` renders (it must render one)."""
    response = client.get(path)
    assert response.status_code == 200, f"{path} answered {response.status_code}"
    read = _Stepper()
    read.feed(response.get_data(as_text=True))
    assert read.found, f"{path} carries no book stepper"
    return read


def list_link_to(client, book_id: str) -> str:
    """The href /books offers for that book (it must offer exactly one)."""
    body = client.get("/books").get_data(as_text=True)
    hrefs = set(re.findall(r'href="([^"]+)"', body))
    opening = {href for href in hrefs if href.rstrip("/").endswith(f"/book/{book_id}")}
    assert len(opening) == 1, f"/books offers {sorted(opening)} for book {book_id}"
    return opening.pop()


# --------------------------------------------------------------------------
# The shelf: puzzles, books, and the panel over them
# --------------------------------------------------------------------------


class Shelf:
    """A book manager in one storage mode, with the store behind it.

    Puzzle records go straight into the store, as in ``test_book_ready_gate``:
    nothing here proves a puzzle unique, and a book of twenty would otherwise
    cost twenty uniqueness proofs. The one-cell clue pair keeps every puzzle
    well above the 4.8 mm floor, so membership is never refused (INV-006).
    """

    def __init__(self, mode, factory, *, store=None, books=None):
        self.mode = mode
        self.factory = factory
        self.store = store if store is not None else PuzzleReviewService(session_factory=factory)
        self.books = (
            books
            if books is not None
            else BookManager(session_factory=factory, puzzle_store=self.store)
        )
        self.batch = make_batch(factory, source="random") if factory is not None else None

    def puzzles(self, wanted) -> list:
        """One stored puzzle per ``(bucket, tier)`` pair, in the order given."""
        ids = [str(uuid.uuid4()) for _ in wanted]

        if self.factory is None:
            for puzzle_id, (bucket, tier) in zip(ids, wanted):
                self.store.puzzles[puzzle_id] = {
                    "id": puzzle_id,
                    "width": bucket.high,
                    "height": bucket.high,
                    "clues_rows": [[1]],
                    "clues_cols": [[1]],
                    "difficulty_tier": tier.value,
                    "status": "approved",
                    "book_id": None,
                }
            return ids

        from nonogram.db.models import Puzzle

        with self.factory() as db:
            db.add_all(
                Puzzle(
                    id=uuid.UUID(puzzle_id),
                    batch_id=uuid.UUID(self.batch),
                    grid=[[True]],
                    clues_rows=[[1]],
                    clues_cols=[[1]],
                    width=bucket.high,
                    height=bucket.high,
                    difficulty_tier=tier.value,
                    status="approved",
                )
                for puzzle_id, (bucket, tier) in zip(ids, wanted)
            )
        return ids

    def book(
        self,
        *,
        title="Winter Animals",
        description="a book",
        theme="christmas",
        audience="adults",
        members=(),
        status=None,
    ) -> str:
        """A book holding ``members`` — ``(bucket, tier)`` pairs — at ``status``."""
        book_id = self.books.create_book(title, description, theme, audience)
        if members:
            self.books.add_puzzles_to_book(book_id, self.puzzles(members))
        if status is not None and status != BookStatus.DRAFT.value:
            self.force_status(book_id, status)
        return book_id

    def force_status(self, book_id: str, status: str) -> None:
        """Put the book at ``status``, around the readiness gate.

        Arranging the state the criteria are stated against, not exercising
        the way out of draft — ADR-0035's gate is CARD-124's, and tested
        there. Written where storage keeps it, so DB mode is not pretended.
        """
        if self.factory is None:
            self.books.books[book_id].status = status
        else:
            from nonogram.db.models import Book as DBBook

            with self.factory() as db:
                db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).first().status = status
        assert self.books.get_book(book_id).status == status

    def details(self, book_id: str) -> tuple:
        """The four general-info fields as storage holds them."""
        metadata = self.books.get_book(book_id).metadata
        return (
            metadata.title,
            metadata.description,
            metadata.theme,
            metadata.target_audience,
        )

    def curation(self, book_id: str) -> tuple:
        """Everything a revisit must not disturb: membership, order, titles."""
        book = self.books.get_book(book_id)
        return (
            tuple(book.puzzle_ids),
            tuple(
                (pid, self.books.get_puzzle_title(book_id, pid)) for pid in book.puzzle_ids
            ),
            book.status,
        )


@pytest.fixture
def scope(tmp_path):
    return sqlite_session_scope(tmp_path, "workflow-steps.db")


@pytest.fixture(params=MODES)
def shelf(request, scope) -> Shelf:
    return Shelf(request.param, None if request.param == "memory" else scope)


@pytest.fixture
def panel(monkeypatch):
    """The admin panel in memory mode, and a shelf over its own store and books."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))

    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    shelf = Shelf("memory", None, store=app.puzzle_review_service, books=app.book_manager)
    return app, shelf


# --------------------------------------------------------------------------
# AC-222 — the detail page links to each of the five steps, at any status
# --------------------------------------------------------------------------


class TestBookDetail_LinksToEveryStep:
    """AC-222 — a pdf_generated book's detail page carries all five links."""

    def test_a_pdf_generated_book_links_to_every_step(self, panel) -> None:
        app, shelf = panel
        book_id = shelf.book(status=BookStatus.PDF_GENERATED.value)

        with app.test_client() as client:
            steps = stepper_of(client, f"/book/{book_id}")

        assert steps.labels == list(STEP_LABELS)
        for key, path in step_paths(book_id).items():
            assert path in steps.hrefs, f"step {key} ({path}) is not linked"

    def test_the_book_really_is_out_of_draft(self, panel) -> None:
        """The criterion's premise, checked rather than assumed."""
        _app, shelf = panel
        book_id = shelf.book(status=BookStatus.PDF_GENERATED.value)

        assert shelf.books.get_book(book_id).status == "pdf_generated"

    @pytest.mark.parametrize("status", EVERY_STATUS)
    def test_every_status_carries_every_link(self, panel, status) -> None:
        """"Whatever the book's status" — over the whole enum, not one of it."""
        app, shelf = panel
        book_id = shelf.book(status=status)

        with app.test_client() as client:
            steps = stepper_of(client, f"/book/{book_id}")

        assert set(step_paths(book_id).values()) <= set(steps.hrefs)

    def test_no_step_is_marked_current_on_the_book_itself(self, panel) -> None:
        """The detail page is the book, not one of its steps."""
        app, shelf = panel
        book_id = shelf.book()

        with app.test_client() as client:
            steps = stepper_of(client, f"/book/{book_id}")

        assert steps.current == []


# --------------------------------------------------------------------------
# AC-223 — opening a book from /books lands in the step workflow
# --------------------------------------------------------------------------


class TestBooksList_OpensBookInStepWorkflow:
    """AC-223 — the page /books opens carries the creation workflow's steps."""

    def test_the_page_the_list_opens_carries_the_step_navigation(self, panel) -> None:
        app, shelf = panel
        book_id = shelf.book(status=BookStatus.DRAFT.value)

        with app.test_client() as client:
            opened = list_link_to(client, book_id)
            steps = stepper_of(client, opened)

        assert steps.labels == list(STEP_LABELS)

    def test_it_is_the_same_navigation_the_creation_workflow_shows(self, panel) -> None:
        """Same list, same order — one macro, never a second copy."""
        app, shelf = panel
        book_id = shelf.book(status=BookStatus.DRAFT.value)

        with app.test_client() as client:
            creating = stepper_of(client, "/book/create")
            opened = stepper_of(client, list_link_to(client, book_id))

        assert opened.labels == creating.labels

    def test_the_creation_page_links_nothing_because_it_has_no_book_yet(
        self, panel
    ) -> None:
        """The empty-links state the macro keeps for /book/create."""
        app, _shelf = panel

        with app.test_client() as client:
            creating = stepper_of(client, "/book/create")

        assert creating.hrefs == []
        assert creating.current == [0]


# --------------------------------------------------------------------------
# AC-224 — the general-info step edits an existing book
# --------------------------------------------------------------------------


class TestBookGeneralInfo_EditsExistingBook:
    """AC-224 — "Winter Animals" submitted as "Winter Birds" is stored as such."""

    def test_the_submitted_title_is_the_stored_title(self, panel) -> None:
        app, shelf = panel
        book_id = shelf.book(title="Winter Animals")

        with app.test_client() as client:
            posted = client.post(
                f"/book/{book_id}/edit",
                data={
                    "title": "Winter Birds",
                    "description": "a book",
                    "theme": "christmas",
                    "target_audience": "adults",
                },
            )

        assert posted.status_code == 302
        assert shelf.details(book_id)[0] == "Winter Birds"

    def test_the_step_opens_on_the_book_it_edits(self, panel) -> None:
        app, shelf = panel
        book_id = shelf.book(title="Winter Animals", audience="seniors")

        with app.test_client() as client:
            body = client.get(f"/book/{book_id}/edit").get_data(as_text=True)

        assert 'value="Winter Animals"' in body
        assert 'value="seniors"' in body

    def test_creating_a_book_is_unchanged(self, panel) -> None:
        """The same form still creates, and still lands on Print setup."""
        app, shelf = panel

        with app.test_client() as client:
            created = client.post(
                "/book/create",
                data={
                    "title": "Autumn Leaves",
                    "description": "a new book",
                    "theme": "generic",
                    "target_audience": "kids",
                },
            )

        assert created.status_code == 302
        assert created.headers["Location"].endswith("/setup-print")
        titles = [book.metadata.title for book in shelf.books.get_all_books()]
        assert "Autumn Leaves" in titles

    @pytest.mark.parametrize("status", EVERY_STATUS)
    def test_the_step_edits_a_book_at_any_status(self, panel, status) -> None:
        app, shelf = panel
        book_id = shelf.book(title="Winter Animals", status=status)

        with app.test_client() as client:
            client.post(
                f"/book/{book_id}/edit",
                data={
                    "title": "Winter Birds",
                    "description": "a book",
                    "theme": "christmas",
                    "target_audience": "adults",
                },
            )

        assert shelf.details(book_id)[0] == "Winter Birds"
        assert shelf.books.get_book(book_id).status == status

    def test_the_four_fields_are_stored_in_both_storage_modes(self, shelf) -> None:
        book_id = shelf.book(title="Winter Animals")

        assert (
            shelf.books.update_book_details(
                book_id,
                title="Winter Birds",
                description="birds, mostly",
                theme="generic",
                target_audience="seniors",
            )
            is True
        )
        assert shelf.details(book_id) == (
            "Winter Birds",
            "birds, mostly",
            "generic",
            "seniors",
        )

    @pytest.mark.parametrize(
        "field,value",
        [
            ("title", "   "),
            ("title", ""),
            ("description", ""),
            ("theme", "winter"),
            ("target_audience", " "),
        ],
    )
    def test_a_refused_field_stores_nothing(self, shelf, field, value) -> None:
        """Revising a book obeys exactly the rules creating one obeys."""
        book_id = shelf.book(title="Winter Animals")
        before = shelf.details(book_id)

        submission = {
            "title": "Winter Birds",
            "description": "birds, mostly",
            "theme": "generic",
            "target_audience": "seniors",
        }
        submission[field] = value

        with pytest.raises(ValueError):
            shelf.books.update_book_details(book_id, **submission)
        assert shelf.details(book_id) == before

    def test_an_unknown_book_is_reported_not_created(self, shelf) -> None:
        assert (
            shelf.books.update_book_details(
                str(uuid.uuid4()),
                title="Winter Birds",
                description="a book",
                theme="christmas",
                target_audience="adults",
            )
            is False
        )


# --------------------------------------------------------------------------
# AC-225 — every step renders whatever the status
# --------------------------------------------------------------------------


class TestBookSteps_ReachableWhateverStatus:
    """AC-225 — a ready_for_kdp book's puzzle-selection step renders 200."""

    def test_puzzle_selection_of_a_ready_for_kdp_book_renders(self, panel) -> None:
        app, shelf = panel
        book_id = shelf.book(
            members=((BUCKETS[0], TIERS[0]),),
            status=BookStatus.READY_FOR_KDP.value,
        )

        with app.test_client() as client:
            answered = client.get(f"/book/{book_id}/select-puzzles")

        assert answered.status_code == 200

    @pytest.mark.parametrize("status", EVERY_STATUS)
    @pytest.mark.parametrize("step", sorted(step_paths("x")))
    def test_every_step_renders_at_every_status(self, panel, status, step) -> None:
        app, shelf = panel
        book_id = shelf.book(
            members=((BUCKETS[0], TIERS[0]), (BUCKETS[2], TIERS[1])),
            status=status,
        )

        with app.test_client() as client:
            answered = client.get(step_paths(book_id)[step])

        assert answered.status_code == 200

    @pytest.mark.parametrize("step", sorted(step_paths("x")))
    def test_the_step_it_is_on_is_the_current_one(self, panel, step) -> None:
        """Each step page marks itself, and offers the other four as links."""
        app, shelf = panel
        book_id = shelf.book(status=BookStatus.PUBLISHED.value)
        paths = step_paths(book_id)

        with app.test_client() as client:
            steps = stepper_of(client, paths[step])

        assert steps.current == [step], f"{paths[step]} marks {steps.current}"
        assert steps.hrefs == [
            path for key, path in sorted(paths.items()) if key != step
        ]

    @pytest.mark.parametrize("step", sorted(step_paths("x")))
    def test_an_unknown_book_still_goes_back_to_the_list(self, panel, step) -> None:
        """Removing the status guard did not remove the not-found one."""
        app, _shelf = panel

        with app.test_client() as client:
            answered = client.get(step_paths(str(uuid.uuid4()))[step])

        assert answered.status_code == 302
        assert answered.headers["Location"].endswith("/books")


# --------------------------------------------------------------------------
# G-2 / EC-026 — revisiting a step discards nothing
# --------------------------------------------------------------------------


#: How many books the corpus below must hold. Asserted inside the test so the
#: corpus cannot silently shrink to one lucky case.
CORPUS_SIZE = 24


def _corpus(shelf, seed: int = 20260923):
    """Seeded books: varied membership, arrangement, titles and status.

    Built with stdlib ``random.Random`` — this project carries no hypothesis
    (ADR-0006/R1) — and yielded with the state each one must still be in after
    every step of the workflow has been opened.
    """
    draw = random.Random(seed)
    for case in range(CORPUS_SIZE):
        members = [
            (draw.choice(BUCKETS), draw.choice(TIERS))
            for _ in range(draw.randint(0, 6))
        ]
        book_id = shelf.book(
            title=f"Corpus {case}",
            description=f"case {case}",
            theme=draw.choice(("christmas", "halloween", "easter", "valentine", "generic")),
            audience=draw.choice(("seniors", "kids", "adults")),
            members=tuple(members),
            status=draw.choice(EVERY_STATUS),
        )

        stored = list(shelf.books.get_book(book_id).puzzle_ids)
        # A custom title on some of them, and a move on some of those: the
        # arrangement a revisit is most likely to disturb.
        for puzzle_id in stored:
            if draw.random() < 0.5:
                shelf.books.set_puzzle_title(book_id, puzzle_id, f"Named {draw.randrange(1000)}")
        for puzzle_id in stored:
            if draw.random() < 0.3:
                try:
                    shelf.books.move_puzzle_down(book_id, puzzle_id)
                except LevelBoundary:
                    # INV-009 refused the move and wrote nothing; the
                    # arrangement this case carries is the one before it.
                    pass

        yield book_id, draw


class TestBookSteps_RevisitingDiscardsNothing:
    """G-2 (EC-026) — a GET changes nothing: not membership, order or titles."""

    def test_opening_every_step_leaves_every_book_exactly_as_it_was(
        self, panel
    ) -> None:
        app, shelf = panel
        seen = 0

        with app.test_client() as client:
            for book_id, draw in _corpus(shelf):
                seen += 1
                before = shelf.curation(book_id)
                details = shelf.details(book_id)

                visits = list(step_paths(book_id).values()) + [f"/book/{book_id}"]
                draw.shuffle(visits)
                for path in visits * 2:
                    assert client.get(path).status_code in (200, 302), path

                assert shelf.curation(book_id) == before
                assert shelf.details(book_id) == details

        assert seen == CORPUS_SIZE

    def test_the_corpus_really_varies(self, panel) -> None:
        """The corpus discriminates: it is not 24 copies of one empty draft."""
        _app, shelf = panel
        statuses, sizes, titled = set(), set(), 0

        for book_id, _draw in _corpus(shelf):
            book = shelf.books.get_book(book_id)
            statuses.add(book.status)
            sizes.add(len(book.puzzle_ids))
            titled += sum(
                1
                for pid in book.puzzle_ids
                if shelf.books.get_puzzle_title(book_id, pid)
            )

        assert len(statuses) >= 3
        assert len(sizes) >= 3
        assert max(sizes) >= 4
        assert titled >= 5


# --------------------------------------------------------------------------
# CK-1 — the stepper's keys, against the pages that still pass them
# --------------------------------------------------------------------------


class TestBookStepper_KeysAreTheOnesTheStepPagesStillPass:
    """The four pre-existing calls keep meaning what they meant.

    ``book_setup_print.html`` calls ``book_steps(1)`` and is owned by another
    card this wave (G-4), so the key it passes had to keep naming Print setup
    when general info joined the list. This reads the templates on disk and
    checks each page's call against the step it marks current, so a future
    renumbering that breaks one of them breaks this instead of the screen.
    """

    CALLS = {
        "book_create.html": 0,
        "book_setup_print.html": 1,
        "book_select_puzzles.html": 2,
        "book_arrange_puzzles.html": 3,
        "book_finalize.html": 4,
    }

    @pytest.mark.parametrize("template,key", sorted(CALLS.items()))
    def test_each_step_page_passes_its_own_key(self, template, key) -> None:
        from pathlib import Path

        import nonogram.admin as admin_package

        source = (
            Path(admin_package.__file__).parent / "templates" / template
        ).read_text(encoding="utf-8")
        calls = re.findall(r"book_steps\(\s*(\d+)\s*\)", source)

        assert calls == [str(key)], f"{template} calls book_steps{calls}"

    def test_the_printed_numbers_run_one_to_five(self, panel) -> None:
        """The key is not the number on the screen; the position is."""
        app, shelf = panel
        book_id = shelf.book()

        with app.test_client() as client:
            body = client.get(f"/book/{book_id}").get_data(as_text=True)

        printed = re.findall(r'<span class="step-n">(\d+)</span>', body)
        assert printed == ["1", "2", "3", "4", "5"]
