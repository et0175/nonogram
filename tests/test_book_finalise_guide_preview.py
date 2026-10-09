"""CARD-169 — the Finalise screen's guide preview shows the printed page's text.

    AC-1  TestFinaliseGuidePreview_TitledLikeThePrintedPage
    AC-2  TestFinaliseGuidePreview_ShowsTheWorkedExampleStepByStep
    AC-3  TestFinaliseGuidePreview_ReadsTheGeneratorsText
    AC-4  TestFinaliseGuidePreview_CountsIntroAndClosing

AC-5 (the hoist leaves the printed page pixel-identical) is carried by the
existing book baseline (``tests/fixtures/book_baseline_card167.json``) and
``tests/test_book_guide_page.py``, unedited.

CARD-201 adds:

    AC-7  TestFinaliseGuidePreview_ShowsBothPages

— the 2-page tutorial's new content (the basic rule, the three cell states,
"start with certainty", page 2's own techniques, the assume/follow/breaks/
proved pipeline and the difficulty-label box), read live from
``book_pdf_generator`` exactly as the original AC-3 proved for the first
page's own constants (a monkeypatched sentinel on a new constant must appear
in the rendered preview too).

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
        title, intro, example_heading, closing, and (CARD-201) every other
        page-level heading/paragraph the template marks with a
        ``data-guide-*``/``data-guide2-*`` attribute: the text of that
        element (``None`` if absent).
        counts: ``{"total"|"easy"|"medium"|"hard": text}``.
        steps: one ``{"caption": text, "cells": [state, ...], "strip":
            attrs}`` per ``data-guide-step``, in document order (``strip``
            is the ``.guide-strip`` element's attribute dict) — CARD-167's
            original worked example, unmoved by CARD-201 except for where it
            sits on the page.
        techniques_1, techniques_2: one ``{"heading": text, "caption": text,
            "rows": [{"cells": [...], "note": text or None}, ...]}`` per
            ``data-guide-technique1``/``2``, in document order (CARD-201).
        cell_states: one ``{"heading": text, "caption": text, "cells": [...]}``
            per ``data-guide-cell-state`` (CARD-201; ``cells`` is the bare
            icon's one-cell strip).
        pipeline_steps: one ``{"label": text, "icon": the ``data-icon``
            value}`` per ``data-guide-pipeline-step`` (CARD-201).
        difficulty: one ``{"name": text, "text": text}`` per
            ``data-guide-difficulty`` (CARD-201).
        text: every text node inside the guide preview, joined.

    **How a strip/cell/note is routed to the right container.** Unlike the
    original (CARD-167) parser, which had exactly one repeating container
    (``data-guide-step``) and could always write to ``self.steps[-1]``,
    CARD-201 adds several more (a technique's several rows, a cell state's
    bare icon, a pipeline step's icon) nested at different depths on the
    same page. A stack of currently-open containers — pushed when a
    ``data-guide-*`` container attribute opens, popped when it closes at the
    matching depth — means a ``.guide-strip``/``.guide-strip-cell``/
    ``[data-guide-row-note]`` is always routed to whichever container is
    innermost at that point, however many are nested.
    """

    #: Page-level fields: one value each, captured by the text inside the
    #: element carrying the marker attribute.
    _FIELDS = {
        "data-guide-title": "title",
        "data-guide-intro": "intro",
        "data-guide-basic-rule-heading": "basic_rule_heading",
        "data-guide-basic-rule-text": "basic_rule_text",
        "data-guide-basic-rule-caption": "basic_rule_caption",
        "data-guide-cell-states-heading": "cell_states_heading",
        "data-guide-certainty-heading": "certainty_heading",
        "data-guide-switching-heading": "switching_heading",
        "data-guide-switching-text": "switching_text",
        "data-guide2-title": "guide2_title",
        "data-guide2-intro": "guide2_intro",
        "data-guide-assume-heading": "assume_heading",
        "data-guide-assume-text": "assume_text",
        "data-guide-assume-closing": "assume_closing",
        "data-guide-difficulty-heading": "difficulty_heading",
        "data-guide-example-heading": "example_heading",
        "data-guide-closing-heading": "closing_heading",
        "data-guide-closing": "closing",
    }

    #: Container markers: attribute -> (list to append a fresh dict to, the
    #: dict's own shape). Pushed onto ``self._containers`` while open.
    _CONTAINER_SHAPES = {
        "data-guide-technique1": lambda: {"heading": None, "caption": None, "rows": []},
        "data-guide-technique2": lambda: {"heading": None, "caption": None, "rows": []},
        "data-guide-cell-state": lambda: {"heading": None, "caption": None, "cells": []},
        "data-guide-pipeline-step": lambda: {"label": None, "icon": None},
        "data-guide-difficulty": lambda: {"name": None, "text": None},
    }

    def __init__(self, page: str):
        super().__init__(convert_charrefs=True)
        for field in self._FIELDS.values():
            setattr(self, field, None)
        self.counts: dict[str, str] = {}
        self.steps: list[dict] = []
        self.techniques_1: list[dict] = []
        self.techniques_2: list[dict] = []
        self.cell_states: list[dict] = []
        self.pipeline_steps: list[dict] = []
        self.difficulty: list[dict] = []
        self._chunks: list[str] = []
        self._depth = 0  # element depth inside the guide preview; 0 = outside
        self._capture: list[tuple[int, str, list[str]]] = []
        #: Stack of (depth it opened at, the container dict, which list it
        #: lives in: "technique1"/"technique2"/"cell_state"/"pipeline"/"difficulty").
        self._containers: list[tuple[int, dict, str]] = []
        self.feed(page)
        self.close()
        self.text = " ".join(" ".join(self._chunks).split())

    def _current(self, kind: str | None = None) -> dict | None:
        """The innermost open container, optionally restricted to ``kind``."""
        for _, container, container_kind in reversed(self._containers):
            if kind is None or container_kind == kind:
                return container
        return None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self._depth == 0:
            if "data-guide-preview" in attrs:
                self._depth = 1
            return
        self._depth += 1
        classes = (attrs.get("class") or "").split()

        for marker, field in self._FIELDS.items():
            if marker in attrs:
                self._capture.append((self._depth, field, []))
        if "data-guide-count" in attrs:
            self._capture.append((self._depth, "count:" + attrs["data-guide-count"], []))
        if "data-guide-technique-heading" in attrs:
            self._capture.append((self._depth, "container:heading", []))
        if "data-guide-technique-caption" in attrs:
            self._capture.append((self._depth, "container:caption", []))
        if "data-guide-cell-state-heading" in attrs:
            self._capture.append((self._depth, "container:heading", []))
        if "data-guide-cell-state-caption" in attrs:
            self._capture.append((self._depth, "container:caption", []))
        if "data-guide-pipeline-label" in attrs:
            self._capture.append((self._depth, "container:label", []))
        if "data-guide-difficulty-name" in attrs:
            self._capture.append((self._depth, "container:name", []))
        if "data-guide-difficulty-text" in attrs:
            self._capture.append((self._depth, "container:text", []))

        _TARGET_LISTS = {
            "step": self.steps,
            "technique1": self.techniques_1,
            "technique2": self.techniques_2,
            "cell_state": self.cell_states,
            "pipeline": self.pipeline_steps,
            "difficulty": self.difficulty,
        }
        if "data-guide-step" in attrs:
            container = {"caption": None, "cells": [], "strip": None}
            self.steps.append(container)
            self._containers.append((self._depth, container, "step"))
        for marker, kind in (
            ("data-guide-technique1", "technique1"),
            ("data-guide-technique2", "technique2"),
            ("data-guide-cell-state", "cell_state"),
            ("data-guide-pipeline-step", "pipeline"),
            ("data-guide-difficulty", "difficulty"),
        ):
            if marker in attrs:
                container = self._CONTAINER_SHAPES[marker]()
                _TARGET_LISTS[kind].append(container)
                self._containers.append((self._depth, container, kind))

        if "guide-step-caption" in classes and "data-guide-technique-heading" not in attrs:
            self._capture.append((self._depth, "caption", []))
        if "guide-strip" in classes:
            technique = self._current("technique1") or self._current("technique2")
            cell_state = self._current("cell_state")
            step = self._current("step")
            if technique is not None:
                technique["rows"].append({"cells": [], "note": None})
            elif cell_state is not None:
                pass  # the icon's own cells append straight to cell_state["cells"]
            elif step is not None:
                step["strip"] = attrs
        if "guide-strip-cell" in classes:
            technique = self._current("technique1") or self._current("technique2")
            cell_state = self._current("cell_state")
            step = self._current("step")
            if technique is not None:
                technique["rows"][-1]["cells"].append(attrs.get("data-state"))
            elif cell_state is not None:
                cell_state["cells"].append(attrs.get("data-state"))
            elif step is not None:
                step["cells"].append(attrs.get("data-state"))
        if "data-guide-row-note" in attrs:
            self._capture.append((self._depth, "container:row_note", []))
        if "data-icon" in attrs:
            pipeline = self._current("pipeline")
            if pipeline is not None:
                pipeline["icon"] = attrs["data-icon"]

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
            elif field == "container:heading":
                container = self._current("technique1") or self._current("technique2") or self._current("cell_state")
                container["heading"] = value
            elif field == "container:caption":
                container = self._current("technique1") or self._current("technique2") or self._current("cell_state")
                container["caption"] = value
            elif field == "container:label":
                self._current("pipeline")["label"] = value
            elif field == "container:name":
                self._current("difficulty")["name"] = value
            elif field == "container:text":
                self._current("difficulty")["text"] = value
            elif field == "container:row_note":
                technique = self._current("technique1") or self._current("technique2")
                if technique is not None and technique["rows"]:
                    technique["rows"][-1]["note"] = value
            else:
                setattr(self, field, value)
        while self._containers and self._containers[-1][0] == self._depth:
            self._containers.pop()
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
        assert card.intro == "Read the clues. Fill what must be black. Mark what must be empty."
        assert card.closing == (
            "Every puzzle in this book is checked by the solver before publication. "
            "There is exactly one solution, and no puzzle that requires guessing is "
            "included. The answers are at the back of the book."
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
            "Guide (2 pages): how to solve, a worked example, and what the "
            "difficulty labels mean"
        )


# --------------------------------------------------------------------------
# CARD-201 AC-7 — the 2-page tutorial's new content, read live
# --------------------------------------------------------------------------


class TestFinaliseGuidePreview_ShowsBothPages:
    """AC-7 — the preview shows page 2's content too, read live from the generator.

    Every one of CARD-201's new constants is checked the same way AC-3
    checked the original ones: read back structurally (not just "the text
    appears somewhere"), and proved live (not a copy in ``app.py`` or the
    template) with the same monkeypatched-sentinel technique.
    """

    @pytest.fixture
    def card(self, panel):
        return GuideCard(panel.shown(panel.book("easy", "easy", "medium", "hard")))

    def test_page_2_title_and_intro(self, card):
        assert card.guide2_title == generator.GUIDE2_TITLE == "When the Puzzle Gets Harder"
        assert card.guide2_intro == generator.GUIDE2_INTRO

    def test_page_1_new_headings_and_text(self, card):
        assert card.basic_rule_heading == generator.GUIDE_BASIC_RULE_HEADING
        assert card.basic_rule_text == generator.GUIDE_BASIC_RULE_TEXT
        assert card.basic_rule_caption == generator.GUIDE_BASIC_RULE_CAPTION
        assert card.cell_states_heading == generator.GUIDE_CELL_STATES_HEADING
        assert card.certainty_heading == generator.GUIDE_CERTAINTY_HEADING
        assert card.switching_heading == generator.GUIDE_SWITCHING_HEADING
        assert card.switching_text == generator.GUIDE_SWITCHING_TEXT

    def test_the_three_cell_states_in_order_with_their_bare_icon(self, card):
        assert len(card.cell_states) == len(generator.GUIDE_CELL_STATES) == 3
        for shown, state in zip(card.cell_states, generator.GUIDE_CELL_STATES):
            assert shown["heading"] == state.heading
            assert shown["caption"] == state.caption
            (cell,) = shown["cells"]
            expected = "filled" if state.filled else ("crossed" if state.crossed else "blank")
            assert cell == expected, state.heading

    def test_start_with_certainty_techniques_in_order_with_their_rows(self, card):
        assert len(card.techniques_1) == len(generator.GUIDE_TECHNIQUES_1) == 3
        for shown, technique in zip(card.techniques_1, generator.GUIDE_TECHNIQUES_1):
            assert shown["heading"] == technique.heading
            assert shown["caption"] == technique.caption
            assert len(shown["rows"]) == len(technique.rows)
            for shown_row, row in zip(shown["rows"], technique.rows):
                assert len(shown_row["cells"]) == technique.length
                for square, state in enumerate(shown_row["cells"]):
                    expected = (
                        "filled" if square in row.filled
                        else "crossed" if square in row.crossed
                        else "blank"
                    )
                    assert state == expected, (technique.heading, square)
                assert shown_row["note"] == (row.note or None)

    def test_page_2_techniques_in_order_with_their_rows(self, card):
        assert len(card.techniques_2) == len(generator.GUIDE_TECHNIQUES_2) == 2
        for shown, technique in zip(card.techniques_2, generator.GUIDE_TECHNIQUES_2):
            assert shown["heading"] == technique.heading
            assert shown["caption"] == technique.caption
            assert len(shown["rows"]) == len(technique.rows)
            for shown_row, row in zip(shown["rows"], technique.rows):
                assert len(shown_row["cells"]) == technique.length
                assert shown_row["note"] == (row.note or None)

    def test_the_assume_pipeline_in_order_with_its_icons(self, card):
        assert card.assume_heading == generator.GUIDE_ASSUME_HEADING
        assert card.assume_text == generator.GUIDE_ASSUME_TEXT
        assert card.assume_closing == generator.GUIDE_ASSUME_CLOSING
        assert len(card.pipeline_steps) == len(generator.GUIDE_ASSUME_STEPS) == 4
        for shown, step in zip(card.pipeline_steps, generator.GUIDE_ASSUME_STEPS):
            assert shown["label"] == step.label
            assert shown["icon"] == step.icon

    def test_the_difficulty_box_carries_the_three_sentences_verbatim(self, card):
        assert card.difficulty_heading == generator.GUIDE_DIFFICULTY_HEADING
        assert len(card.difficulty) == len(generator.GUIDE_DIFFICULTY_LABELS) == 3
        for shown, label in zip(card.difficulty, generator.GUIDE_DIFFICULTY_LABELS):
            assert shown["name"] == label.name
            assert shown["text"] == label.text

    def test_the_difficulty_sentences_appear_nowhere_else_in_contradictory_wording(
        self, card
    ):
        """The stats block elsewhere on this screen shows Easy/Medium/Hard
        puzzle *counts* (a number), never a sentence describing what the
        tier means — so there is no second, independently-worded
        description of the difficulty labels for this one to disagree with.
        Each of the three sentences this box carries appears in the page
        exactly once.
        """
        for label in generator.GUIDE_DIFFICULTY_LABELS:
            assert card.text.count(label.text) == 1, label.text

    def test_sentinels_on_the_new_constants_render_live(self, panel, monkeypatch):
        book_id = panel.book("easy", "easy", "medium", "hard")
        guide2_title = "SENTINEL-GUIDE2-TITLE-201"
        difficulty_text = "SENTINEL-DIFFICULTY-TEXT-201"
        assume_closing = "SENTINEL-ASSUME-CLOSING-201"
        original_labels = generator.GUIDE_DIFFICULTY_LABELS
        shipped = (
            generator.GUIDE2_TITLE,
            generator.GUIDE_DIFFICULTY_LABELS[0].text,
            generator.GUIDE_ASSUME_CLOSING,
        )

        monkeypatch.setattr(generator, "GUIDE2_TITLE", guide2_title)
        monkeypatch.setattr(
            generator,
            "GUIDE_DIFFICULTY_LABELS",
            (dataclasses.replace(original_labels[0], text=difficulty_text),)
            + tuple(original_labels[1:]),
        )
        monkeypatch.setattr(generator, "GUIDE_ASSUME_CLOSING", assume_closing)

        card = GuideCard(panel.shown(book_id))

        assert card.guide2_title == guide2_title
        assert card.difficulty[0]["text"] == difficulty_text
        assert card.assume_closing == assume_closing
        for text in shipped:
            assert text not in card.text
