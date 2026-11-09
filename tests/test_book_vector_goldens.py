"""CARD-322 item 18 -- vector goldens, and two absolute vector-side checks.

**What a golden is, and what it is not.** For each interior page type a stored
sha-256 of the page's DECODED content-stream bytes
(:func:`tests.helpers.pdf_vector.content_streams`), recorded for the fixed
baseline book (``corpus_book()`` + ``baseline_puzzles()``). It is a regression
TRIPWIRE: it pins the writer's own output, so it detects a change and proves
nothing about whether the page is right (D1: the page-content oracle gap stays
declared; no whole-page content claim is made here). It replaces, for the
interior, the recorded PIXEL baselines in ``tests/fixtures/book_baseline_*.json``
(which already skip the digest check for vector pages, and which this module
does not touch: D7). It does NOT replace an independent bitmap reference for
vector geometry; that is held now by the poppler-based
``tests/property/test_book_pdf_geometry.py`` and ``frame_centre_of``.

**Determinism, measured before it was relied on.** The 14-page baseline
interior was exported in two separate interpreters with different
``PYTHONHASHSEED`` (1 and 777), ``TZ`` (UTC and Asia/Tokyo) and ``LC_ALL`` (C
and en_US.UTF-8): all 14 per-page digests were equal. One host, one
interpreter (CPython 3.14, macOS). Residue NOT closed: across hosts the risks
are the float formatting of coordinates; the face is package data
(ADR-0006/R1) so it is not host-dependent. A golden that differs by a last
digit on another machine is a finding, not a re-record.

**Re-recording is deliberate and the suite never does it.** Run, by a person,
after reviewing the change against a render::

    NONOGRAM_RECORD_VECTOR_GOLDENS=1 python -m tests.test_book_vector_goldens

``main`` below is the only caller of :func:`record_goldens`
(``test_nothing_but_the_entry_point_can_re_record`` holds that by ``ast``), and
``test_the_suite_does_not_carry_the_re_record_switch`` asserts the switch is
unset in the process that runs the suite. A re-record is named in the commit
message with the render that justified it (G-16).

**The two absolute checks (AC-18)** take their expected values from the BOOK
and from literal strings written below, never from ``compute_layout`` or
``footer_pointer_text``: the grid-size label of each single puzzle page is
``"{columns} x {rows}"`` of THAT puzzle and a two-up page prints none; and
(CARD-391, replacing the per-puzzle QR caption and typed link that stood here)
each puzzle page's footer line ``Play puzzle 3 online · p. 11`` -- or, on a
two-up page, ONE line ``Play 1 and 2 online · p. 11`` -- is on its
page, below the grid and inside the usable area, read from the text layer
(poppler) of the same book with a stored player domain. The control: neither
``Solve it online`` nor ``nonogram.example`` is on any page of either export.
"""

from __future__ import annotations

import ast
import copy
import functools
import hashlib
import json
import os
import pathlib
import re
import sys
from typing import Any

import pytest

from nonogram.admin import book_pdf_generator as generator_module
from nonogram.admin.book_interior_vector import (
    DOWNSTREAM_WRITERS,
    interior_generator,
)
from nonogram.admin.book_pdf_generator import InteriorPageWriters
from tests.helpers import pdf_vector
from tests.helpers.book_corpus import baseline_puzzles, corpus_book

GOLDEN_FILE = (
    pathlib.Path(__file__).resolve().parent / "fixtures" / "book_vector_golden_card322.json"
)
RECORD_SWITCH = "NONOGRAM_RECORD_VECTOR_GOLDENS"

#: The baseline interior's plan, page by page, written out (an independent
#: statement of ``baseline_puzzles``' docstring: guide, "Easy", the two-up
#: page, "Medium", the 15x15, "Hard", the 30x30, SOLUTIONS, three answers).
EXPECTED_PLAN = [
    "title", "guide", "guide", "toc",
    "divider", "puzzle", "divider", "puzzle", "divider", "puzzle", "divider",
    "answer", "answer", "answer",
]  # fmt: skip

#: Interior page number (1-based) -> the golden's page-type label. The
#: dividers are raster (CARD-231) and are not goldened.
PAGE_TYPES = {
    1: "title",
    2: "guide_1",
    3: "guide_2",
    4: "toc",
    6: "puzzle_two_up",
    8: "puzzle_single_15x15",
    10: "puzzle_single_30x30",
    12: "answer_packed_two",
    13: "answer_packed_one",
    14: "answer_full",
}


#: The Play online page (CARD-390) exists only for a book with a stored player
#: domain, so the baseline book (which has none, and whose plan this file
#: pins) cannot carry it. Its golden is taken from the SAME baseline puzzles on
#: the same book with a domain set, where it is page 11 (the last puzzle page
#: is 10, a verso, so no blank precedes it).
PLAY_PAGE = 11
PLAY_DOMAIN = "https://nonogram.adverax.io"


@functools.lru_cache(maxsize=1)
def _play_export() -> bytes:
    book = copy.copy(corpus_book())
    book.player_domain = PLAY_DOMAIN
    return interior_generator(book).export_interior(baseline_puzzles()).getvalue()


def _export() -> tuple[list[str], bytes]:
    generator = interior_generator(corpus_book())
    puzzles = baseline_puzzles()
    kinds = [kind.value for kind in generator.interior_stream(puzzles).page_kinds]
    return kinds, generator.export_interior(puzzles).getvalue()


def digests_of(data: bytes) -> dict[str, str]:
    """``{page type: sha-256 of the decoded content stream}`` for ``data``."""
    streams = pdf_vector.content_streams(data)
    digests = {
        label: hashlib.sha256(streams[number - 1].encode("cp1252")).hexdigest()
        for number, label in PAGE_TYPES.items()
    }
    play = pdf_vector.content_streams(_play_export())[PLAY_PAGE - 1]
    digests["play"] = hashlib.sha256(play.encode("cp1252")).hexdigest()
    return digests


RE_RECORD_HINT = (
    f"A change to a vector writer is expected to move its page type's golden. "
    f"If the change is intended, review it against a RENDER of the page (not "
    f"against this digest) and re-record deliberately with "
    f"`{RECORD_SWITCH}=1 python -m tests.test_book_vector_goldens`, naming the "
    f"render in the commit message. Do not re-record to make a red go away."
)


def golden_findings(computed: dict[str, str], golden: dict[str, Any]) -> list[str]:
    """Every page type whose digest differs from, or is missing in, ``golden``."""
    stored = golden["digests"]
    findings = []
    for label in sorted(set(computed) | set(stored)):
        if computed.get(label) != stored.get(label):
            findings.append(f"{label}: {stored.get(label)} -> {computed.get(label)}")
    return findings


def record_goldens() -> None:  # pragma: no cover - the deliberate entry point
    kinds, data = _export()
    assert kinds == EXPECTED_PLAN, kinds
    GOLDEN_FILE.write_text(
        json.dumps(
            {
                "book": "tests.helpers.book_corpus.corpus_book() + baseline_puzzles()",
                "hash": "sha-256 of the decoded content stream (cp1252)",
                "plan": kinds,
                "digests": digests_of(data),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:  # pragma: no cover - never reached by the suite
    if not os.environ.get(RECORD_SWITCH):
        print(f"refusing: set {RECORD_SWITCH}=1 to re-record deliberately", file=sys.stderr)
        return 2
    record_goldens()
    print(f"recorded {GOLDEN_FILE}")
    return 0


@pytest.fixture(scope="module")
def exported() -> tuple[list[str], bytes]:
    return _export()


@pytest.fixture(scope="module")
def golden() -> dict[str, Any]:
    return json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))


class TestVectorGoldens_EveryInteriorPageTypeIsPinned:
    def test_the_plan_is_the_one_the_goldens_were_recorded_on(self, exported, golden) -> None:
        kinds, _ = exported
        assert kinds == EXPECTED_PLAN == golden["plan"], kinds
        for number, label in PAGE_TYPES.items():
            assert kinds[number - 1] == label.split("_")[0], (number, label, kinds)

    def test_each_interior_page_type_matches_its_golden(self, exported, golden) -> None:
        _, data = exported
        findings = golden_findings(digests_of(data), golden)
        assert findings == [], f"{findings}\n{RE_RECORD_HINT}"

    def test_the_title_golden_pins_blank_and_nothing_more(self, exported, golden) -> None:
        """Page 1 is the title and copyright page, no longer blank.

        The owner replaced the blank page on 2026-11-09
        (``BookPDFGenerator.vector_title_contents``). The name is kept (it is
        cited by id); what it pins now is that the title golden is NOT the
        empty stream's digest, and that the page it was recorded from sets the
        book's title and its copyright line and no folio.
        """
        _, data = exported
        assert golden["digests"]["title"] != hashlib.sha256(b"").hexdigest()
        texts = [text for *_, text in pdf_vector.placed_text(
            pdf_vector.content_streams(data)[0]
        )]
        assert "Winter Pictures" in texts, texts
        assert any(text.startswith("Copyright") for text in texts), texts
        assert not any(text.strip().isdigit() for text in texts), texts

    def test_the_failure_message_says_how_to_re_record(self) -> None:
        assert RECORD_SWITCH in RE_RECORD_HINT
        assert "RENDER" in RE_RECORD_HINT
        assert "python -m tests.test_book_vector_goldens" in RE_RECORD_HINT
        assert "Do not re-record to make a red go away" in RE_RECORD_HINT

    def test_every_page_type_is_goldened(self, golden) -> None:
        assert sorted(golden["digests"]) == sorted([*PAGE_TYPES.values(), "play"])


class TestVectorGoldens_AnOperatorChangeInAWriterRedsItsPageType:
    """The control: one extra ``0 0 m`` in ONE writer reds that page type's golden.

    The plant is installed in the writer that draws the page (through the
    assembly point's own ``pages=`` override for the three downstream writers,
    and at the names ``book_pdf_generator`` imports for the puzzle and title
    writers), so the digest is checked end to end. ``must_red`` is asserted
    non-empty, and a plant in one writer must NOT red the others' types.
    """

    @staticmethod
    def _planted(stream):
        stream._operators.append("0 0 m")
        return stream

    def _export_with(self, monkeypatch, which: str) -> dict[str, str]:
        planted = self._planted
        writers = DOWNSTREAM_WRITERS
        fields = {
            "guide": writers.guide,
            "toc": writers.toc,
            "answer": writers.answer,
            "packed_answer": writers.packed_answer,
        }
        if which in fields:
            original = fields[which]

            def wrapped(*args, **keywords):
                return planted(original(*args, **keywords))

            fields[which] = wrapped
        elif which == "puzzle_single":
            original_single = generator_module.puzzle_page_stream
            monkeypatch.setattr(
                generator_module,
                "puzzle_page_stream",
                lambda *a, **k: planted(original_single(*a, **k)),
            )
        elif which == "puzzle_two_up":
            original_pair = generator_module.two_up_page_stream
            monkeypatch.setattr(
                generator_module,
                "two_up_page_stream",
                lambda *a, **k: planted(original_pair(*a, **k)),
            )
        elif which == "title":
            # Page 1 is written by ``vector_title_contents`` since the owner
            # replaced the blank page (2026-11-09); ``vector_title_page`` is
            # now only the blank before the Play online page, which the
            # baseline book does not print.
            original_title = generator_module.BookPDFGenerator.vector_title_contents
            monkeypatch.setattr(
                generator_module.BookPDFGenerator,
                "vector_title_contents",
                lambda self, *a, **k: planted(original_title(self, *a, **k)),
            )
        else:  # pragma: no cover
            raise AssertionError(which)
        generator = interior_generator(corpus_book(), pages=InteriorPageWriters(**fields))
        return digests_of(generator.export_interior(baseline_puzzles()).getvalue())

    @pytest.mark.parametrize(
        ("which", "reds"),
        [
            ("title", {"title"}),
            ("guide", {"guide_1", "guide_2"}),
            ("toc", {"toc"}),
            ("answer", {"answer_full"}),
            ("packed_answer", {"answer_packed_two", "answer_packed_one"}),
            ("puzzle_single", {"puzzle_single_15x15", "puzzle_single_30x30"}),
            ("puzzle_two_up", {"puzzle_two_up"}),
        ],
    )
    def test_one_extra_operator_reds_exactly_its_page_types(
        self, monkeypatch, golden, which, reds
    ) -> None:
        computed = self._export_with(monkeypatch, which)
        red = {
            line.split(":")[0] for line in golden_findings(computed, golden)
        }
        assert red, "the plant did not move any golden: the control cannot fail"
        assert red == reds, (which, sorted(red))


class TestVectorGoldens_TheSuiteCannotReRecord:
    def test_the_suite_does_not_carry_the_re_record_switch(self) -> None:
        assert not os.environ.get(RECORD_SWITCH), (
            f"{RECORD_SWITCH} is set in the process that runs the suite"
        )

    def test_nothing_but_the_entry_point_can_re_record(self) -> None:
        tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
        callers: set[str] = set()
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(function):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "record_goldens"
                ):
                    callers.add(function.name)
        assert callers == {"main"}, callers
        # And the other repository text does not call it either.
        offenders = [
            str(path)
            for path in pathlib.Path(__file__).resolve().parent.rglob("*.py")
            if path != pathlib.Path(__file__).resolve()
            and "record_goldens" in path.read_text(encoding="utf-8")
        ]
        assert offenders == [], offenders


# --------------------------------------------------------------------------
# AC-18: the grid-size label and the QR link, expected values from the BOOK
# --------------------------------------------------------------------------

#: Single puzzle pages -> (columns, rows) of THAT puzzle, written out from
#: ``baseline_puzzles`` (Tree 15x15 on page 8, Snowflake 30x30 on page 10); the
#: two-up page 6 (Duck + Owl) prints none, by design.
LABELS = {8: (15, 15), 10: (30, 30)}
#: Interior page -> the footer line printed on it, in the book with a stored
#: player domain (``_play_export``, whose Play page is :data:`PLAY_PAGE`): the
#: puzzles' own numbers in the book (print order is easy, medium, hard: Duck 1,
#: Owl 2, Tree 3, Snowflake 4), written as LITERALS so they are independent of
#: the writer.
POINTERS = {
    6: "Play 1 and 2 online · p. 11",
    8: "Play puzzle 3 online · p. 11",
    10: "Play puzzle 4 online · p. 11",
}


def _words(data: bytes, page: int, tmp_path) -> list[pdf_vector.Word]:
    return pdf_vector.word_boxes(data, page=page, out_dir=tmp_path)


def label_findings(words, columns: int | None, rows: int | None) -> list[str]:
    """The ``"{c} x {r}"`` triple on a page: required for a single, absent on a two-up."""
    texts = [w.text for w in words]
    triples = [
        (texts[i], texts[i + 1], texts[i + 2])
        for i in range(len(texts) - 2)
        if texts[i + 1] == "x" and texts[i].isdigit() and texts[i + 2].isdigit()
    ]
    if columns is None:
        return [f"a grid-size label {t} on a page that prints none" for t in triples]
    if triples != [(str(columns), "x", str(rows))]:
        return [f"expected {[(str(columns), 'x', str(rows))]}, read {triples}"]
    return []


def pointer_findings(words, pointer, page_width_pt, page_height_pt, margin_pt) -> list[str]:
    """The pointer line is on the page once, below the grid, inside the margins."""
    findings: list[str] = []
    texts = [w.text for w in words]
    tokens = pointer.split()
    starts = [
        i for i in range(len(texts) - len(tokens) + 1) if texts[i : i + len(tokens)] == tokens
    ]
    if len(starts) != 1:
        return [f"pointer {pointer!r} read {len(starts)} times"]
    line = words[starts[0] : starts[0] + len(tokens)]
    top = min(w.top for w in line)
    # The grid's lowest text: the digit-only words (clue digits) above the line.
    grid_bottom = max(
        (w.bottom for w in words if w.text.isdigit() and w.top < top), default=0.0
    )
    if not top > grid_bottom:
        findings.append(f"pointer {pointer!r} is not below the grid ({top} <= {grid_bottom})")
    if not (
        min(w.left for w in line) >= margin_pt
        and max(w.right for w in line) <= page_width_pt - margin_pt
        and max(w.bottom for w in line) <= page_height_pt
    ):
        findings.append(f"pointer {pointer!r} is outside the usable area")
    return findings


def _trim_pt(data: bytes) -> tuple[float, float]:
    match = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]", data)
    assert match, "no MediaBox"
    return float(match.group(1)), float(match.group(2))


class TestVectorSide_TheGridSizeLabelAndThePointerAreTheBooks:
    def test_the_grid_size_label_is_columns_x_rows_and_a_two_up_page_prints_none(
        self, exported, tmp_path
    ) -> None:
        _, data = exported
        for page, (columns, rows) in LABELS.items():
            assert label_findings(_words(data, page, tmp_path), columns, rows) == [], page
        assert label_findings(_words(data, 6, tmp_path), None, None) == []

    def test_the_label_reading_fails_on_a_wrong_digit_and_a_missing_label(self) -> None:
        W = pdf_vector.Word
        good = [W("15", 1, 1, 2, 2), W("x", 3, 1, 4, 2), W("15", 5, 1, 6, 2)]
        assert label_findings(good, 15, 15) == []
        assert label_findings(good, 14, 15), "a wrong digit must red"
        assert label_findings(good[:1], 15, 15), "a missing label must red"
        assert label_findings(good, None, None), "a label on a two-up page must red"

    def test_each_puzzle_pages_pointer_is_on_its_page_below_the_grid(
        self, exported, tmp_path
    ) -> None:
        data = _play_export()
        width, height = _trim_pt(data)
        margin = min(
            float(corpus_book().gutter_margin_cm), float(corpus_book().outside_margin_cm)
        ) * 72 / 2.54
        for page, pointer in POINTERS.items():
            assert (
                pointer_findings(_words(data, page, tmp_path), pointer, width, height, margin)
                == []
            ), page
        # The control: the per-puzzle QR's words are on no page of either book.
        for export in (data, exported[1]):
            text = pdf_vector.extracted_text(export, out_dir=tmp_path)
            assert "Solve it online" not in text and "nonogram.example" not in text

    def test_the_pointer_reading_fails_on_a_wrong_digit_a_moved_line_and_a_missing_word(
        self, tmp_path
    ) -> None:
        data = _play_export()
        width, height = _trim_pt(data)
        words = _words(data, 8, tmp_path)
        margin = 36.0
        pointer = POINTERS[8]
        assert pointer_findings(words, pointer, width, height, margin) == []
        assert pointer_findings(words, "Play puzzle 9 online · p. 11", width, height, margin), (
            "a wrong digit must red"
        )
        line = set(pointer.split())
        moved = [
            w._replace(top=50.0, bottom=62.0) if w.text in line and w.bottom > 600 else w
            for w in words
        ]
        assert pointer_findings(moved, pointer, width, height, margin), (
            "a line moved above the grid must red"
        )
        outside = [
            w._replace(left=width - 10, right=width + 100) if w.text == "Play" else w
            for w in words
        ]
        assert pointer_findings(outside, pointer, width, height, margin), (
            "a line outside the area must red"
        )
        no_word = [w for w in words if w.text != "online"]
        assert pointer_findings(no_word, pointer, width, height, margin), (
            "a missing word must red"
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
