"""CARD-169 — the Finalise screen's guide preview shows the printed page's text.

    AC-1  TestFinaliseGuidePreview_TitledLikeThePrintedPage
    AC-2  TestFinaliseGuidePreview_ShowsTheWorkedExampleStepByStep
    AC-3  TestFinaliseGuidePreview_ReadsTheGeneratorsText
    AC-4  TestFinaliseGuidePreview_CountsIntroAndClosing

AC-5 (the hoist leaves the printed page pixel-identical) is carried by the
existing book baseline (``tests/fixtures/book_baseline_card167.json``) and
``tests/test_book_guide_page.py``, unedited.

The page is read structurally: a small ``html.parser`` reader collects the
guide card's marked elements (``data-guide-*``) and each strip cell's
``data-state``, so a test asserts what the owner sees in the card rather than
whether a substring happens to occur somewhere in the HTML.

The books are built the way ``tests/test_book_finalise_gutter.py`` builds
them — records written straight into the store, membership through the real
``add_puzzles_to_book`` — so rendering the screen costs no uniqueness proof.
"""

from __future__ import annotations

import dataclasses
import uuid
from html.parser import HTMLParser

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.book_pdf_generator as generator
from nonogram import clues
from nonogram.admin.book_manager import BookManager

#: The printed page's title, written out rather than read from the module, so
#: AC-1 also fails if the constant and the screen drift together.
TITLE = "How to Solve Nonograms"

#: The shipped worked example's four lines as the owner should see them, one
#: character per square: ``#`` filled, ``x`` crossed, ``.`` blank. Written out
#: by hand from the captions (step 2: squares 2-3 filled; step 3: 2-4 filled,
#: 1 and 5 crossed; step 4: square 6 filled too) — a second statement of the
#: example independent of WORKED_EXAMPLE_STEPS' index sets.
SHIPPED_STRIPS = ("......", ".##...", "x###x.", "x###x#")

STATE_CHAR = {"filled": "#", "crossed": "x", "blank": "."}

OLD_PREVIEW_PHRASES = (
    "How to use this book",
    "Have fun!",
    "Fill in the grid based on the clues",
    "Check your work against the answer key",
)


# --------------------------------------------------------------------------
# Reading the rendered page
# --------------------------------------------------------------------------


class GuideCard(HTMLParser):
    """The guide preview's marked parts, read out of the rendered page.

    Attributes:
        title, intro, example_heading, closing: the text of the element
            carrying that ``data-guide-*`` marker (``None`` if absent).
        counts: ``{"total"|"easy"|"medium"|"hard": text}``.
        steps: one ``{"caption": text, "cells": [state, ...], "strip":
            attrs}`` per ``data-guide-step``, in document order (``strip``
            is the ``.guide-strip`` element's attribute dict).
        text: every text node inside the guide preview, joined.
    """

    _FIELDS = {
        "data-guide-title": "title",
        "data-guide-intro": "intro",
        "data-guide-example-heading": "example_heading",
        "data-guide-closing": "closing",
    }

    def __init__(self, page: str):
        super().__init__(convert_charrefs=True)
        self.title = self.intro = self.example_heading = self.closing = None
        self.counts: dict[str, str] = {}
        self.steps: list[dict] = []
        self._chunks: list[str] = []
        self._depth = 0  # element depth inside the guide preview; 0 = outside
        self._capture: list[tuple[int, str, list[str]]] = []
        self.feed(page)
        self.close()
        self.text = " ".join(" ".join(self._chunks).split())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self._depth == 0:
            if "data-guide-preview" in attrs:
                self._depth = 1
            return
        self._depth += 1
        for marker, field in self._FIELDS.items():
            if marker in attrs:
                self._capture.append((self._depth, field, []))
        if "data-guide-count" in attrs:
            self._capture.append((self._depth, "count:" + attrs["data-guide-count"], []))
        if "data-guide-step" in attrs:
            self.steps.append({"caption": None, "cells": [], "strip": None})
        if "guide-step-caption" in (attrs.get("class") or "").split():
            self._capture.append((self._depth, "caption", []))
        if "guide-strip" in (attrs.get("class") or "").split():
            self.steps[-1]["strip"] = attrs
        if "guide-strip-cell" in (attrs.get("class") or "").split():
            self.steps[-1]["cells"].append(attrs.get("data-state"))

    def handle_endtag(self, tag):
        if self._depth == 0:
            return
        while self._capture and self._capture[-1][0] == self._depth:
            _, field, parts = self._capture.pop()
            value = " ".join("".join(parts).split())
            if field.startswith("count:"):
                self.counts[field[len("count:"):]] = value
            elif field == "caption":
                self.steps[-1]["caption"] = value
            else:
                setattr(self, field, value)
        self._depth -= 1

    def handle_data(self, data):
        if self._depth == 0:
            return
        self._chunks.append(data)
        for _, _, parts in self._capture:
            parts.append(data)


class ContentsCard(HTMLParser):
    """The text of the Contents card's interior list items."""

    def __init__(self, page: str):
        super().__init__(convert_charrefs=True)
        self.items: list[str] = []
        self._in_contents = False
        self._li: list[str] | None = None
        self._last_text = ""
        self.feed(page)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag == "li" and self._in_contents:
            self._li = []

    def handle_endtag(self, tag):
        if tag == "li" and self._li is not None:
            self.items.append(" ".join("".join(self._li).split()))
            self._li = None
        if tag == "ol" and self._in_contents:
            self._in_contents = False

    def handle_data(self, data):
        if data.strip() == "Interior PDF":
            self._in_contents = True
        if self._li is not None:
            self._li.append(data)


# --------------------------------------------------------------------------
# The panel, and one book on it (the pattern of test_book_finalise_gutter.py)
# --------------------------------------------------------------------------


def _record(tier: str, number: int) -> dict:
    """One approved 15 x 15 puzzle record, in the shape the store holds them."""
    grid = [[(x + y) % 3 == 0 for x in range(15)] for y in range(15)]
    found = clues.compute_clues(grid)
    return {
        "id": str(uuid.uuid4()),
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": 15,
        "height": 15,
        "puzzle_name": f"Picture {number}",
        "difficulty_tier": tier,
        "status": "approved",
        "book_id": None,
    }


@pytest.fixture
def panel(monkeypatch):
    """The admin panel in memory mode, with a book store of its own."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setattr(
        book_manager_module, "_book_manager", BookManager(session_factory=None)
    )
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return Panel(app)


class Panel:
    def __init__(self, app):
        self.client = app.test_client()
        self.books = app.book_manager
        self.store = app.puzzle_review_service

    def book(self, *tiers: str) -> str:
        """A draft book holding one puzzle per entry of ``tiers``."""
        book_id = self.books.create_book("Winter", "a book", "generic", "adults")
        records = [_record(tier, n) for n, tier in enumerate(tiers, start=1)]
        for record in records:
            self.store.puzzles[record["id"]] = record
        self.books.add_puzzles_to_book(book_id, [r["id"] for r in records])
        assert len(self.books.get_book(book_id).puzzle_ids) == len(tiers)
        return book_id

    def shown(self, book_id) -> str:
        """The finalise screen as the owner sees it."""
        response = self.client.get(f"/book/{book_id}/finalize")
        assert response.status_code == 200
        return response.get_data(as_text=True)


# --------------------------------------------------------------------------
# AC-1..AC-4
# --------------------------------------------------------------------------


class TestFinaliseGuidePreview_TitledLikeThePrintedPage:
    """AC-1: the card is headed with the printed page's title, and the old
    "How to use this book" preview is gone from the whole page."""

    def test_heading_is_the_guide_title(self, panel):
        card = GuideCard(panel.shown(panel.book("easy", "easy", "easy")))
        assert card.title == TITLE == generator.GUIDE_TITLE

    @pytest.mark.parametrize("phrase", OLD_PREVIEW_PHRASES)
    def test_old_preview_text_appears_nowhere(self, panel, phrase):
        page = panel.shown(panel.book("easy", "easy", "easy"))
        assert phrase not in page


class TestFinaliseGuidePreview_ShowsTheWorkedExampleStepByStep:
    """AC-2: every step's caption, in order, each over a strip whose cells
    are that step's filled / crossed / blank squares."""

    @pytest.fixture
    def card(self, panel):
        return GuideCard(panel.shown(panel.book("easy", "easy", "easy")))

    def test_every_caption_in_step_order(self, card):
        assert [step["caption"] for step in card.steps] == [
            step.caption for step in generator.WORKED_EXAMPLE_STEPS
        ]

    def test_every_strip_matches_its_steps_sets(self, card):
        assert len(card.steps) == len(generator.WORKED_EXAMPLE_STEPS) >= 4
        for shown, step in zip(card.steps, generator.WORKED_EXAMPLE_STEPS):
            assert len(shown["cells"]) == generator.WORKED_EXAMPLE_LENGTH
            for square, state in enumerate(shown["cells"]):
                expected = (
                    "filled" if square in step.filled
                    else "crossed" if square in step.crossed
                    else "blank"
                )
                assert state == expected, (step.label, square)

    def test_strips_draw_the_shipped_example(self, card):
        """The same check against the hand-written lines above, so a step
        whose sets and caption disagree does not pass by matching itself."""
        drawn = tuple(
            "".join(STATE_CHAR[state] for state in step["cells"]) for step in card.steps
        )
        assert drawn == SHIPPED_STRIPS

    def test_strips_are_hidden_behind_their_captions(self, card):
        """The caption is each strip's text equivalent: the strip is
        aria-hidden and carries no accessible name of its own."""
        for step in card.steps:
            assert step["caption"]
            assert step["strip"].get("aria-hidden") == "true"
            assert "role" not in step["strip"]
            assert "aria-label" not in step["strip"]

    def test_example_heading_names_the_clue_and_length(self, card):
        assert card.example_heading == (
            "Worked example: the clue 3 1 on a row of 6 squares."
        )
        assert card.example_heading == generator.GUIDE_EXAMPLE_HEADING


class TestFinaliseGuidePreview_ReadsTheGeneratorsText:
    """AC-3: with the generator's title, captions, intro, closing, example
    heading and row length replaced, the preview shows the replacements — it
    has no copy of its own."""

    def test_sentinels_render(self, panel, monkeypatch):
        book_id = panel.book("easy", "easy", "easy")
        title = "SENTINEL-TITLE-169"
        caption = "SENTINEL-CAPTION-169"
        steps = generator.WORKED_EXAMPLE_STEPS
        monkeypatch.setattr(generator, "GUIDE_TITLE", title)
        monkeypatch.setattr(
            generator,
            "WORKED_EXAMPLE_STEPS",
            (dataclasses.replace(steps[0], caption=caption),) + tuple(steps[1:]),
        )

        card = GuideCard(panel.shown(book_id))

        assert card.title == title
        assert card.steps[0]["caption"] == caption
        assert TITLE not in card.text
        assert steps[0].caption not in card.text

    def test_intro_closing_heading_and_length_sentinels_render(self, panel, monkeypatch):
        """The rest of the generator's text, and the row length the strips
        are drawn at, are read at request time too: a literal copy of any of
        them in the route would show the shipped value, not the sentinel."""
        book_id = panel.book("easy", "easy", "easy")
        intro = "SENTINEL-INTRO-169"
        closing = "SENTINEL-CLOSING-169"
        heading = "SENTINEL-HEADING-169"
        length = generator.WORKED_EXAMPLE_LENGTH + 1  # the shipped sets still fit
        shipped = (generator.GUIDE_INTRO, generator.GUIDE_CLOSING,
                   generator.GUIDE_EXAMPLE_HEADING)
        monkeypatch.setattr(generator, "GUIDE_INTRO", intro)
        monkeypatch.setattr(generator, "GUIDE_CLOSING", closing)
        monkeypatch.setattr(generator, "GUIDE_EXAMPLE_HEADING", heading)
        monkeypatch.setattr(generator, "WORKED_EXAMPLE_LENGTH", length)

        card = GuideCard(panel.shown(book_id))

        assert card.intro == intro
        assert card.closing == closing
        assert card.example_heading == heading
        for text in shipped:
            assert text not in card.text
        assert [len(step["cells"]) for step in card.steps] == (
            [length] * len(generator.WORKED_EXAMPLE_STEPS)
        )
        assert all(step["cells"][-1] == "blank" for step in card.steps)


class TestFinaliseGuidePreview_CountsIntroAndClosing:
    """AC-4: intro and closing are the generator's; the counts are the
    book's; the Contents card describes the new page."""

    @pytest.fixture
    def page(self, panel):
        return panel.shown(panel.book("easy", "easy", "medium", "hard"))

    def test_intro_and_closing_are_the_generators(self, page):
        card = GuideCard(page)
        assert card.intro == generator.GUIDE_INTRO
        assert card.closing == generator.GUIDE_CLOSING
        assert card.intro.startswith("Each number beside a row or above a column")
        assert card.closing == (
            "Every puzzle in this book has exactly one solution. "
            "The answers are at the back of the book."
        )

    def test_counts(self, page):
        assert GuideCard(page).counts == {
            "total": "4", "easy": "2", "medium": "1", "hard": "1",
        }

    def test_counts_are_not_swapped_between_tiers(self, panel):
        """AC-4's book has medium == hard; this one gives every tier its own
        count, so a count shown under the wrong tier cannot pass."""
        page = panel.shown(panel.book("easy", "medium", "medium", "hard", "hard", "hard"))
        assert GuideCard(page).counts == {
            "total": "6", "easy": "1", "medium": "2", "hard": "3",
        }

    def test_contents_line_describes_the_new_page(self, page):
        assert "instructions and difficulty summary" not in page
        items = ContentsCard(page).items
        assert items[0] == (
            "Guide page (how to solve, a worked example, and the difficulty summary)"
        )
