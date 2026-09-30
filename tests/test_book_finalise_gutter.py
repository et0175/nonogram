"""CARD-129 — finalise refuses a gutter KDP would refuse at the page count.

    AC-179  TestBookFinalise_RefusesGutterBelowKdpMinimumForPageCount
    AC-271  TestBookFinalise_PageCountIncludesAnswerKeyPages
    AC-288  TestBookFinalise_PageCountExcludesCoverFile
    CK-1    TestBookFinalise_GutterCheckAtHundredFiftyPageBoundary

EC-034's page-count half — that the count finalise checks *is* the interior
PDF's own page count, for every book — is in
``tests/property/test_book_export_interior.py``, extending CARD-135's property.

**Why each of these is a boundary and not an example.** KDP asks for a wider
inside margin once a book passes 150 pages, and a book that goes up with too
narrow a one is rejected *at upload*, after everything else about it looked
finished. Every way of getting the count wrong lands within a page or two of
that boundary: leaving the answer key out of it (AC-271) makes a 155-page book
look like a 125-page one, and counting the separate cover file into it
(AC-288) makes an exactly-150-page book look like a 151-page one. So the
counts here are exact numbers, and each is **measured off the export's own
page plan** in ``test_the_scenario_really_has_that_many_pages`` beside the
criterion it serves, rather than assumed.

The books are built from puzzle records written straight into the store, as
``tests/test_book_ready_gate.py``'s ``Shelf`` does and for the same reason: a
150-puzzle book would otherwise cost 150 uniqueness proofs, and the page plan
reads a record's grid, clues and tier and nothing else. Nothing here draws a
page: the interior's three counts are settled by ``interior_stream`` before a
pixel exists, which is why a 180-page book is affordable as a test at all.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram import clues
from nonogram.admin.book_kdp import (
    KDP_GUTTER_BANDS,
    MAX_MODELLED_PAGE_COUNT,
    KdpPageCountNotModelled,
    gutter_refusal,
    kdp_min_gutter_cm,
    kdp_page_band,
    stored_gutter_cm,
    unpaired_interior_page_count,
)
from nonogram.admin.book_manager import BookManager, BookStatus
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.admin.book_plan import BUCKETS, TIERS, DistributionPlan, Split, bucket_of

DRAFT = BookStatus.DRAFT.value

#: CON-018's Book 1 trim, as the ``books`` columns store it.
TRIM_CM = ("21.59", "27.94")

#: The gutter KDP asks for up to 150 pages, in the two-decimal centimetre form
#: the column holds it in: 0.375 in is 0.9525 cm, which stores as "0.95".
GUTTER_0375_IN = "0.95"

#: AC-179's illustrative stored gutter. Below KDP's minimum at every page
#: count, and below the sheet builder's own 0.635 cm side-margin floor too —
#: see :class:`TestBookFinalise_RefusesGutterBelowKdpMinimumForPageCount`.
GUTTER_060 = "0.60"

#: The three phrases AC-179 and AC-271 ask the refusal to name, written out
#: here rather than built from the code that composes it.
KDP_BAND_TEXT = "1.27 cm (0.5 in) for 151-300 pages"


# --------------------------------------------------------------------------
# The corpora: puzzles whose page plan is arithmetic, not luck
# --------------------------------------------------------------------------


def _gutter_grid(columns: int, rows: int, depth: int) -> list[list[bool]]:
    """A grid whose row **and** column clues are exactly ``depth`` deep.

    Every other cell filled along both axes, stopped after ``depth`` runs, so
    a line that carries any ink carries ``depth`` isolated single cells. The
    clue depth is what decides how wide and how tall the *drawing* is, and
    therefore whether two of these can share a page (INV-010) — so it is set
    here rather than left to whatever a picture happens to produce.
    """
    limit = 2 * depth - 1
    if limit > min(columns, rows):
        raise ValueError(f"a {columns}x{rows} grid cannot carry {depth}-deep clues")
    return [
        [x % 2 == 0 and x < limit and y % 2 == 0 and y < limit for x in range(columns)]
        for y in range(rows)
    ]


def _record(columns: int, rows: int, depth: int, tier: str, number: int) -> dict:
    """One approved puzzle record, in the shape the store holds them."""
    grid = _gutter_grid(columns, rows, depth)
    found = clues.compute_clues(grid)
    return {
        "id": str(uuid.uuid4()),
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": f"Picture {number}",
        "difficulty_tier": tier,
        "status": "approved",
        "book_id": None,
    }


def alone(tier: str, number: int) -> dict:
    """A puzzle that prints on a page of its own, and takes a 4-up answer tile.

    22 x 22 with 6-deep clues: its drawing is 28 cells down, so two of them
    need a 4.2 mm shared cell against FR-040's 7.0 mm minimum and never pair —
    **at any gutter**, because the shared cell is decided by the page's
    *height*, which the side margins do not touch. That is what makes a book
    of these have the same page count on a legal gutter as on AC-179's
    illegal one. Its longest side is 22 > 20, so its answer takes a four-up
    page (INV-011).
    """
    return _record(22, 22, 6, tier, number)


def alone_six_up(tier: str, number: int) -> dict:
    """The same, but 20 x 20 — so its answer stays on a **six**-up page.

    20 x 20 with 6-deep clues is 26 cells down; two of them would need a
    4.5 mm shared cell, so these do not pair either. The longest side is
    exactly 20, the largest INV-011 keeps at six answers to a page.
    """
    return _record(20, 20, 6, tier, number)


def pairs_up(tier: str, number: int) -> dict:
    """A puzzle that **does** share a page with its same-tier neighbour.

    21 x 10 with 5-deep clues: 15 cells down, so two of them fit one page at
    a 7.5 mm shared cell, comfortably over FR-040's 7.0 mm. Its longest side
    is 21 > 20, so its answer still takes a four-up page — which is the
    combination AC-271 needs: a book that pairs on the puzzle pages and packs
    four answers to a page behind the SOLUTIONS divider.
    """
    return _record(21, 10, 5, tier, number)


def corpus(*runs) -> list[dict]:
    """``(builder, tier, count)`` runs, in order, as one book's records."""
    records, number = [], 0
    for builder, tier, count in runs:
        for _ in range(count):
            number += 1
            records.append(builder(tier, number))
    return records


#: AC-288's book: exactly 150 interior pages. 1 guide + 2 level dividers + 116
#: single puzzle pages + the SOLUTIONS divider + 30 four-up answer pages.
AC288_CORPUS = ((alone, "easy", 57), (alone, "medium", 59))
AC288_PAGES = 150

#: CK-1's other side: the same book with one more puzzle, which is 151 pages.
CK1_OVER_CORPUS = ((alone, "easy", 57), (alone, "medium", 60))
CK1_OVER_PAGES = 151

#: AC-179's book: 180 interior pages. 1 + 2 dividers + 140 pages + 1 + 36.
AC179_CORPUS = ((alone, "easy", 70), (alone, "medium", 70))
AC179_PAGES = 180

#: AC-271's book: 150 puzzles whose 150 answers pack onto 30 pages, behind 125
#: interior pages — 1 guide + 2 dividers + 121 puzzle pages (29 of them
#: shared) + the SOLUTIONS divider. 155 interior pages in all.
AC271_CORPUS = (
    (alone_six_up, "easy", 90),
    (pairs_up, "medium", 58),
    (alone, "medium", 2),
)
AC271_PUZZLES = 150
AC271_ANSWER_PAGES = 30
AC271_PAGES_BEFORE_THE_KEY = 125
AC271_PAGES = 155


# --------------------------------------------------------------------------
# The panel, and one book on it
# --------------------------------------------------------------------------


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
    """A panel, and the one call these tests make of it."""

    def __init__(self, app):
        self.app = app
        self.client = app.test_client()
        self.books = app.book_manager
        self.store = app.puzzle_review_service

    def book(self, runs, *, gutter: str = GUTTER_0375_IN, title="Winter") -> str:
        """A draft book holding ``runs``, storing ``gutter``, on its plan.

        The records go straight into the store (see the module docstring), the
        membership through the real ``add_puzzles_to_book`` — so every puzzle
        has passed the 4.8 mm floor (INV-006) — and the plan is the selection
        itself, so the readiness gate (ADR-0035/R1) has nothing to say and the
        only thing that can refuse this book at finalise is the KDP check.

        The gutter is written **after** the members are added, and that is not
        a convenience: ``add_puzzles_to_book`` measures every printed cell on
        the book's sheet, so a book storing AC-179's 0.60 cm could not have
        been curated at all. Such a value reaches the column only as a legacy
        or hand-edited row — which is exactly the book AC-179 describes — and
        the panel offers no margin field to write it with (``set_print_spec``
        writes the trim columns only).
        """
        book_id = self.books.create_book(title, "a book", "generic", "adults")
        records = corpus(*runs)
        for record in records:
            self.store.puzzles[record["id"]] = record
        self.books.add_puzzles_to_book(book_id, [r["id"] for r in records])
        self.books.save_plan(book_id, plan_of(records))
        stored = self.books.get_book(book_id)
        stored.trim_width_cm, stored.trim_height_cm = TRIM_CM
        stored.gutter_margin_cm = gutter
        stored.outside_margin_cm = GUTTER_0375_IN
        return book_id

    def finalise(self, book_id):
        """``POST /book/<id>/finalize`` with the Save-and-finish action."""
        return self.client.post(
            f"/book/{book_id}/finalize", data={"action": "save_and_finish"}
        )

    def shown(self, book_id) -> str:
        """The finalise screen as the owner sees it."""
        response = self.client.get(f"/book/{book_id}/finalize")
        assert response.status_code == 200
        return response.get_data(as_text=True)

    def status(self, book_id) -> str:
        return self.books.get_book(book_id).status

    def gutter(self, book_id) -> str:
        """The gutter margin the book **stores**, read back from the store."""
        return self.books.get_book(book_id).gutter_margin_cm

    def counts(self, book_id):
        """The interior's page plan for this book, as the export decides it."""
        book = self.books.get_book(book_id)
        rows = [self.store.get_puzzle(pid) for pid in book.puzzle_ids]
        return BookPDFGenerator(book).interior_stream(rows)


def plan_of(records) -> DistributionPlan:
    """A plan whose matrix **is** this selection, so the gate has no complaint.

    The split is the one whose tier counts the matrix's column totals already
    are, found by trying the whole-percent splits the column totals round to;
    the gate compares cells and not the split (``off_plan_cells``), so this
    only keeps the stored plan from disagreeing with itself.
    """
    count = len(records)
    cells = [[0] * len(TIERS) for _ in BUCKETS]
    for record in records:
        bucket = bucket_of(record["width"], record["height"])
        tier = next(t for t in TIERS if t.value == record["difficulty_tier"])
        cells[BUCKETS.index(bucket)][TIERS.index(tier)] += 1
    columns = tuple(sum(row[t] for row in cells) for t in range(len(TIERS)))
    matrix = tuple(tuple(row) for row in cells)
    rounded = [round(100 * column / count) for column in columns]
    rounded[0] += 100 - sum(rounded)
    guesses = [tuple(rounded)] + [
        (easy, medium, 100 - easy - medium)
        for easy in range(101)
        for medium in range(101 - easy)
    ]
    fallback = None
    for easy, medium, hard in guesses:
        candidate = DistributionPlan(
            count=count, split=Split(easy, medium, hard), cells=matrix
        )
        if not candidate.disagrees_with_split:
            return candidate
        fallback = fallback or candidate
    return fallback


def refusal_of(response) -> str:
    """The refusal the finalise screen came back carrying.

    The route re-renders rather than redirecting when it refuses, so the flash
    is read out of the rendered page — the template consumes it.
    """
    assert response.status_code == 200, response.status_code
    return response.get_data(as_text=True)


# --------------------------------------------------------------------------
# KDP's table itself (FR-030, CON-018)
# --------------------------------------------------------------------------


class TestKdpGutterTable:
    """The two bands the requirements record, and the silence above them."""

    @pytest.mark.parametrize(
        "page_count,expected_cm",
        [
            (1, 0.9525),
            (2, 0.9525),
            (149, 0.9525),
            (150, 0.9525),
            (151, 1.27),
            (299, 1.27),
            (300, 1.27),
        ],
    )
    def test_the_minimum_for_each_band(self, page_count, expected_cm) -> None:
        assert kdp_min_gutter_cm(page_count) == pytest.approx(expected_cm)

    def test_the_bands_are_the_two_the_requirements_state(self) -> None:
        """0.375 in up to 150 pages, 0.5 in to 300 — stated in inches."""
        assert KDP_GUTTER_BANDS == (
            (150, Decimal("0.375")),
            (300, Decimal("0.5")),
        )
        assert MAX_MODELLED_PAGE_COUNT == 300

    @pytest.mark.parametrize("page_count", [1, 150, 151, 300])
    def test_the_band_is_named_as_a_page_range(self, page_count) -> None:
        assert kdp_page_band(page_count) == ((1, 150) if page_count <= 150 else (151, 300))

    @pytest.mark.parametrize("page_count", [301, 400, 501, 10_000])
    def test_above_three_hundred_pages_it_refuses_rather_than_guessing(
        self, page_count
    ) -> None:
        """The one thing this module will not do: invent a fourth band.

        KDP's real table continues past 300 pages; which numbers it continues
        with is a business fact this project has not recorded, so a page count
        above the recorded table is refused with what is missing rather than
        measured against a number nobody chose.
        """
        with pytest.raises(KdpPageCountNotModelled) as refused:
            kdp_min_gutter_cm(page_count)
        assert "not modelled above 300 pages" in str(refused.value)

    @pytest.mark.parametrize("page_count", [0, -1, 1.5, True, None, "150"])
    def test_a_page_count_that_is_not_one_is_refused(self, page_count) -> None:
        with pytest.raises(ValueError):
            kdp_min_gutter_cm(page_count)

    def test_the_stored_two_decimal_form_of_a_band_is_that_band(self) -> None:
        """"0.95" is 0.375 in, because in that column it is the same number.

        The ``books`` margin columns hold two decimals, so 0.9525 cm can only
        be written as "0.95" — and a check made against the exact value would
        refuse every book that is *on* CON-018's profile. The comparison is
        therefore made at the column's own precision.
        """
        assert gutter_refusal(150, 0.95) is None
        assert gutter_refusal(1, 0.95) is None
        assert gutter_refusal(150, 0.94) is not None

    def test_the_refusal_reads_the_stored_column_and_writes_nothing(self) -> None:
        """A book-shaped object, unchanged by being checked (G-1)."""

        class Row:
            gutter_margin_cm = "0.60"

        row = Row()
        assert stored_gutter_cm(row) == pytest.approx(0.60)
        assert gutter_refusal(180, stored_gutter_cm(row)) is not None
        assert row.gutter_margin_cm == "0.60"

    def test_an_empty_column_is_the_profiles_own_gutter(self) -> None:
        """A legacy row with no margins is CON-018's 0.5 in, as the sheet is."""

        class Row:
            gutter_margin_cm = None

        assert stored_gutter_cm(Row()) == pytest.approx(1.27)
        assert gutter_refusal(300, stored_gutter_cm(Row())) is None


# --------------------------------------------------------------------------
# AC-179 — the refusal names KDP's band against the stored value
# --------------------------------------------------------------------------


class TestBookFinalise_RefusesGutterBelowKdpMinimumForPageCount:
    """AC-179 (FR-030) — 0.60 cm stored, 180 interior pages: refused.

    The reconciliation CARD-115's handover asked for. AC-179's illustrative
    0.60 cm is below ``book_page_spec``'s 0.635 cm side-margin floor, so such
    a book has no *sheet* and the page plan cannot measure its two-up pages —
    the builder refuses before finalise can name the KDP band. Two things make
    the band nameable anyway, and both are asserted below:

    * two-up pairing is the **only** term of the interior's make-up that needs
      a sheet, so the count falls back to the same book with every puzzle on a
      page of its own (``unpaired_interior_page_count``) — an upper bound,
      which can only name a band at or above the true one, and the refusal is
      certain regardless because a gutter below the sheet builder's floor is
      below *every* band of KDP's table;
    * this book pairs nothing at any gutter (see :func:`alone`), so that bound
      **is** its interior's page count: 180 pages on the illegal gutter, 180
      on a legal one, 180 before pairing. The "whose interior PDF runs to 180
      pages" of the criterion is measured, not assumed.
    """

    def test_finalise_is_refused_naming_the_band_against_the_stored_value(
        self, panel
    ) -> None:
        book_id = panel.book(AC179_CORPUS, gutter=GUTTER_060)

        shown = refusal_of(panel.finalise(book_id))

        assert f"{AC179_PAGES} pages" in shown
        assert KDP_BAND_TEXT in shown
        assert "stores 0.60 cm" in shown

    def test_the_stored_gutter_is_not_changed(self, panel) -> None:
        """G-1: finalise refuses; it never raises the gutter to make it fit."""
        book_id = panel.book(AC179_CORPUS, gutter=GUTTER_060)

        panel.finalise(book_id)

        assert panel.gutter(book_id) == GUTTER_060

    def test_the_book_does_not_leave_draft(self, panel) -> None:
        book_id = panel.book(AC179_CORPUS, gutter=GUTTER_060)

        panel.finalise(book_id)

        assert panel.status(book_id) == DRAFT

    def test_the_scenario_really_has_that_many_pages(self, panel) -> None:
        """180 interior pages, on a legal gutter and on AC-179's own.

        The same 140 rows, three ways: the export's page plan on CON-018's
        0.5 in gutter, the same plan on the 0.375 in one, and the sheet-free
        count the refusal above used. All 180 — which is what makes this
        book's page count a fact about the book rather than about its margins.
        """
        legal = panel.book(AC179_CORPUS)
        assert panel.counts(legal).page_count == AC179_PAGES
        assert panel.counts(legal).unpaired_page_count == AC179_PAGES

        book = panel.books.get_book(legal)
        book.gutter_margin_cm = "1.27"
        assert panel.counts(legal).page_count == AC179_PAGES

        rows = [panel.store.get_puzzle(pid) for pid in book.puzzle_ids]
        assert unpaired_interior_page_count(rows) == AC179_PAGES

    def test_at_the_profiles_own_gutter_the_same_book_is_accepted(
        self, panel
    ) -> None:
        """The criterion is about the gutter, not about the 180 pages.

        The same 180-page book storing CON-018's 0.5 in gutter — KDP's
        minimum for the 151-300 band — finalises. Without this the refusal
        above could be coming from the page count alone.
        """
        book_id = panel.book(AC179_CORPUS, gutter="1.27")

        response = panel.finalise(book_id)

        assert response.status_code == 302
        assert panel.status(book_id) != DRAFT


# --------------------------------------------------------------------------
# AC-271 — the answer key's pages count
# --------------------------------------------------------------------------


class TestBookFinalise_PageCountIncludesAnswerKeyPages:
    """AC-271 (FR-042) — 125 pages before the key + 30 answer pages = 155.

    The criterion that matters most. The packed answer key is what brings a
    150-puzzle book back from over 300 pages to the ~120-190-page model
    (FR-042), and a count that left it out would put this book at 125 pages —
    inside KDP's 0.375 in band — and pass a book KDP rejects at upload.
    """

    def test_finalise_is_refused_naming_the_band_for_a_hundred_and_fifty_five(
        self, panel
    ) -> None:
        book_id = panel.book(AC271_CORPUS)

        shown = refusal_of(panel.finalise(book_id))

        assert f"{AC271_PAGES} pages" in shown
        assert KDP_BAND_TEXT in shown
        assert panel.status(book_id) == DRAFT

    def test_the_answer_key_is_what_crosses_the_boundary(self, panel) -> None:
        """Pin the criterion's own arithmetic: 125 + 30, and 125 alone passes.

        The 125 pages before the key are the guide page, the two level
        dividers, the 121 puzzle pages and the SOLUTIONS divider; 30 is the
        packed key. The second assertion is the bug this criterion exists to
        make impossible — at 125 pages the very same gutter is accepted.
        """
        book_id = panel.book(AC271_CORPUS)
        counts = panel.counts(book_id)

        assert counts.answer_page_count == AC271_ANSWER_PAGES
        assert counts.page_count == AC271_PAGES
        assert counts.page_count - counts.answer_page_count == (
            AC271_PAGES_BEFORE_THE_KEY
        )
        assert AC271_PAGES_BEFORE_THE_KEY + AC271_ANSWER_PAGES == AC271_PAGES

        assert gutter_refusal(AC271_PAGES_BEFORE_THE_KEY, 0.95) is None
        assert gutter_refusal(AC271_PAGES, 0.95) is not None

    def test_the_book_really_holds_a_hundred_and_fifty_puzzles(self, panel) -> None:
        """150 answers on 30 pages, and every puzzle answered exactly once."""
        book_id = panel.book(AC271_CORPUS)
        counts = panel.counts(book_id)

        assert len(panel.books.get_book(book_id).puzzle_ids) == AC271_PUZZLES
        assert counts.unpaired_page_count - counts.page_count == 29, (
            "the book's two-up pages are what make it 121 puzzle pages"
        )

    def test_the_screen_reports_the_answer_page_count(self, panel) -> None:
        """The checkpoint's figures, on the screen the owner reads them from."""
        book_id = panel.book(AC271_CORPUS)

        shown = panel.shown(book_id)

        assert f'data-interior-page-count="{AC271_PAGES}"' in shown
        assert f'data-answer-page-count="{AC271_ANSWER_PAGES}"' in shown
        assert 'data-unpaired-page-count="184"' in shown


# --------------------------------------------------------------------------
# AC-288 — the cover file does not count
# --------------------------------------------------------------------------


class TestBookFinalise_PageCountExcludesCoverFile:
    """AC-288 (FR-043) — exactly 150 interior pages at 0.375 in: accepted.

    One page either way is the whole of this criterion. The cover is a second
    file of one page (INV-013), and a count that added it would make this book
    151 pages, push it into KDP's 151-300 band and refuse a book KDP accepts.
    """

    def test_a_hundred_and_fifty_interior_pages_is_not_refused(self, panel) -> None:
        book_id = panel.book(AC288_CORPUS)

        response = panel.finalise(book_id)

        assert response.status_code == 302, refusal_of(response)
        assert panel.status(book_id) == BookStatus.READY_FOR_PDF.value

    def test_the_cover_does_not_change_the_count(self, panel) -> None:
        """The same book with an uploaded cover is still 150 interior pages.

        The cover reaches the export through the session, so it is uploaded
        the way the owner uploads one and the count is asked again afterwards.
        """
        from io import BytesIO

        from PIL import Image

        book_id = panel.book(AC288_CORPUS)
        art = BytesIO()
        Image.new("RGB", (600, 900), "white").save(art, format="PNG")
        art.seek(0)
        uploaded = panel.client.post(
            f"/book/{book_id}/finalize",
            data={"cover": (art, "cover.png")},
            content_type="multipart/form-data",
        )
        assert uploaded.status_code == 200
        assert "Cover image uploaded" in uploaded.get_data(as_text=True)

        assert f'data-interior-page-count="{AC288_PAGES}"' in panel.shown(book_id)
        assert panel.finalise(book_id).status_code == 302
        assert panel.status(book_id) == BookStatus.READY_FOR_PDF.value

    def test_the_scenario_really_is_exactly_a_hundred_and_fifty(self, panel) -> None:
        """Measured off the page plan, and one page below the boundary."""
        book_id = panel.book(AC288_CORPUS)

        assert panel.counts(book_id).page_count == AC288_PAGES == 150
        assert kdp_page_band(AC288_PAGES) == (1, 150)
        assert gutter_refusal(AC288_PAGES, 0.95) is None
        assert gutter_refusal(AC288_PAGES + 1, 0.95) is not None


# --------------------------------------------------------------------------
# CK-1 — the boundary itself
# --------------------------------------------------------------------------


class TestBookFinalise_GutterCheckAtHundredFiftyPageBoundary:
    """CK-1 — at 150 pages a 0.375 in gutter finalises; at 151 it is refused.

    The two books differ by one puzzle and nothing else: the same builder, the
    same tiers, the same stored 0.375 in gutter. So the verdict that changes
    between them is the page count crossing 150 and can be nothing else.
    """

    def test_one_page_over_the_boundary_is_refused(self, panel) -> None:
        book_id = panel.book(CK1_OVER_CORPUS)

        shown = refusal_of(panel.finalise(book_id))

        assert f"{CK1_OVER_PAGES} pages" in shown
        assert KDP_BAND_TEXT in shown
        assert panel.status(book_id) == DRAFT
        assert panel.gutter(book_id) == GUTTER_0375_IN

    def test_at_the_boundary_it_is_accepted(self, panel) -> None:
        book_id = panel.book(AC288_CORPUS)

        assert panel.finalise(book_id).status_code == 302
        assert panel.status(book_id) == BookStatus.READY_FOR_PDF.value

    def test_the_two_books_differ_by_exactly_one_page(self, panel) -> None:
        at_the_boundary = panel.counts(panel.book(AC288_CORPUS)).page_count
        over_it = panel.counts(panel.book(CK1_OVER_CORPUS, title="Spring")).page_count

        assert (at_the_boundary, over_it) == (150, 151)
        assert over_it - at_the_boundary == 1
