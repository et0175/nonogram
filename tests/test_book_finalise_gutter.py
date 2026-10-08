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
that boundary: leaving the answer key out of it (AC-271) makes a 275-page
book (CARD-198: one full solved page per puzzle, up from the packed key's
155) look like a 125-page one, and counting the separate cover file into it
(AC-288) makes an exactly-150-page book look like a 151-page one. So the
counts here are exact numbers, and each is **measured off the export's own
page plan** in ``test_the_scenario_really_has_that_many_pages`` beside the
criterion it serves, rather than assumed.

The books are built from puzzle records written straight into the store, as
``tests/test_book_ready_gate.py``'s ``Shelf`` does and for the same reason: a
150-puzzle book would otherwise cost 150 uniqueness proofs, and the page plan
reads a record's grid, clues and tier and nothing else. Nothing here draws a
page: the interior's three counts are settled by ``interior_stream`` before a
pixel exists, which is why a 284-page book (CARD-198: up from 180) is
affordable as a test at all.
"""

from __future__ import annotations

import html
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
from nonogram.admin.app import FINALISE_ACTION_FAILED, PDF_EXPORT_FAILED
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

#: CARD-199's two new bands, written out the same way as ``KDP_BAND_TEXT``
#: above (G-2: that constant and the two bands it names are unchanged).
KDP_BAND_TEXT_301_500 = "1.59 cm (0.625 in) for 301-500 pages"
KDP_BAND_TEXT_501_590 = "1.91 cm (0.75 in) for 501-590 pages"


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
    a 7.5 mm shared cell, comfortably over FR-040's 7.0 mm — which is what
    AC-271 and CK-1 need: a book that pairs on the puzzle pages while its
    answer section still prints one full page per puzzle behind the
    SOLUTIONS divider (CARD-198).
    """
    return _record(21, 10, 5, tier, number)


def pairs_up_six(tier: str, number: int) -> dict:
    """A puzzle that pairs on its puzzle page **and** stays six-up packed.

    20 x 10 with 5-deep clues: 15 cells down, the same pairing shared cell
    as :func:`pairs_up`, but its longest side is 20, not 21 — the largest
    INV-011 ever kept at six answers to a page, before this card. CARD-198's
    own AC-8 needs exactly this combination: a book whose puzzle pages
    pairing already shortens, and whose answer pages the old packed key
    already packed as tightly as INV-011 allowed (six-up), so that book sat
    comfortably under the old 300-page ceiling — and *only* the switch to
    one full answer page per puzzle, unpacked, is what can now carry it past
    KDP's modelled table altogether.
    """
    return _record(20, 10, 5, tier, number)


def corpus(*runs) -> list[dict]:
    """``(builder, tier, count)`` runs, in order, as one book's records."""
    records, number = [], 0
    for builder, tier, count in runs:
        for _ in range(count):
            number += 1
            records.append(builder(tier, number))
    return records


#: AC-288's book: exactly 150 interior pages. **CARD-198 note (recomputed,
#: not the original corpus):** since the answer section is now one page per
#: puzzle rather than a packed tile, an all-``alone`` corpus like the one
#: this book used before CARD-198 adds exactly *two* pages (one puzzle page,
#: one answer page) per puzzle, never one — so no such corpus can sit one
#: puzzle away from another that is exactly one page longer, which is CK-1's
#: own premise. This corpus instead pairs its medium tier (``pairs_up``): at
#: an *odd* count one of them prints alone (same puzzle-page count as the
#: *even* count one more, where it pairs with the previously-alone one
#: instead), so the next puzzle adds exactly one *answer* page and nothing
#: else — the only way left to make two books differ by exactly one page.
#: 1 guide + 2 level dividers + 63 puzzle pages (42 easy alone + 21 medium,
#: 20 pairs and 1 alone) + the SOLUTIONS divider + 83 answer pages (one per
#: puzzle) = 150. Recomputed and checked against the generator's own page
#: plan, not asserted from this arithmetic alone
#: (``test_the_scenario_really_has_that_many_pages`` equivalents throughout
#: this module always measure the live plan).
AC288_CORPUS = ((alone, "easy", 42), (pairs_up, "medium", 41))
AC288_PAGES = 150

#: CK-1's other side: the same book with one more (pairing) medium puzzle,
#: which is exactly one page longer — see :data:`AC288_CORPUS`'s note. The
#: medium tier's 41 (odd, one alone) becomes 42 (even, all paired): the same
#: 21 puzzle pages either way, and one more answer page.
CK1_OVER_CORPUS = ((alone, "easy", 42), (pairs_up, "medium", 42))
CK1_OVER_PAGES = 151

#: AC-179's book: 1 + 2 dividers + 140 pages + 1 + 140 answer pages (CARD-198:
#: one per puzzle, where this book took 36 four-up pages before this card) =
#: 284. Still inside KDP's 151-300 band, same as the 180 pages this corpus
#: produced before CARD-198 — the corpus itself is unchanged; only what one
#: page per puzzle, unpacked, adds up to is bigger.
AC179_CORPUS = ((alone, "easy", 70), (alone, "medium", 70))
AC179_PAGES = 284

#: AC-271's book: 150 puzzles, each now with its own full answer page
#: (CARD-198: one per puzzle, where this book packed 30 before this card),
#: behind 125 interior pages — 1 guide + 2 dividers + 121 puzzle pages (29 of
#: them shared) + the SOLUTIONS divider. 275 interior pages in all.
AC271_CORPUS = (
    (alone_six_up, "easy", 90),
    (pairs_up, "medium", 58),
    (alone, "medium", 2),
)
AC271_PUZZLES = 150
AC271_ANSWER_PAGES = 150
AC271_PAGES_BEFORE_THE_KEY = 125
AC271_PAGES = 275

#: CARD-199 AC-5's book: inside the new 301-500 band. **CARD-198 note:** 200
#: medium `alone`s (down from 277 before this card, which would now land at
#: 557 pages — the 501-590 band, not this test's target): 1 guide + 1 level
#: divider + 200 puzzle pages + the SOLUTIONS divider + 200 answer pages
#: (CARD-198: one per puzzle, where this book packed 50 before this card) =
#: 403.
AC199_NEW_BAND_CORPUS = ((alone, "medium", 200),)
AC199_NEW_BAND_PAGES = 403

#: CARD-199 AC-6's book, unchanged by CARD-198 (the corpus, not the count):
#: 241 medium `alone`s. **CARD-198 note:** this book was pre-computed by
#: CARD-199 at CARD-198's own "roughly 305 pages" regression estimate, using
#: the *packed* key's arithmetic (1 + 1 + 241 + 1 + 61 = 305, ceil(241 / 4)
#: answer pages) as a stand-in for what CARD-198 would actually produce. The
#: real CARD-198 implementation is one answer page per puzzle, unpacked:
#: 1 + 1 + 241 + 1 + 241 = 485 — still inside the 301-500 band and still
#: over the *old* 300-page ceiling this test is about (where this book used
#: to be refused outright as "not modelled" before CARD-199's table), so the
#: test's own claim holds exactly as before; only the page count naming it
#: changed, recomputed against the real page plan rather than reused from
#: the earlier estimate.
AC199_CARD198_CORPUS = ((alone, "medium", 241),)
AC199_CARD198_PAGES = 485

#: CARD-198's own AC-8 book: a book that *was* inside the old 300-page
#: ceiling, purely because of the answer section's old packing, and crosses
#: even CARD-199's widened 590-page ceiling once that packing is gone. 444
#: one-tier :func:`pairs_up_six` puzzles, all pairing two-up and all
#: six-up-packable under the old key:
#:
#: * old (packed, pre-CARD-198) arithmetic: 1 guide + 1 divider + 222 paired
#:   puzzle pages + the SOLUTIONS divider + 74 six-up answer pages
#:   (ceil(444 / 6)) = 299 — inside the old 300-page ceiling, and the gutter
#:   this book stores (CON-018's own 0.5 in) was always enough for it;
#: * CARD-198: 1 + 1 + 222 + 1 + 444 (one answer page per puzzle) = 669 —
#:   over :data:`~nonogram.admin.book_kdp.MAX_MODELLED_PAGE_COUNT` (590)
#:   purely from the answer section's own growth, with the puzzle section
#:   unchanged.
AC8_CORPUS = ((pairs_up_six, "easy", 444),)
AC8_OLD_PACKED_PAGES = 299
AC8_PAGES = 669


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
    """The four bands the requirements record, and the silence above them."""

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
            # CARD-199 AC-1: the new 301-500 band, 0.625 in exactly.
            (301, 1.5875),
            (400, 1.5875),
            (500, 1.5875),
            # CARD-199 AC-2: the new 501-590 band, 0.75 in exactly.
            (501, 1.905),
            (550, 1.905),
            (590, 1.905),
        ],
    )
    def test_the_minimum_for_each_band(self, page_count, expected_cm) -> None:
        assert kdp_min_gutter_cm(page_count) == pytest.approx(expected_cm)

    def test_the_bands_are_the_four_the_requirements_state(self) -> None:
        """0.375 in to 150, 0.5 in to 300, 0.625 in to 500, 0.75 in to 590.

        Stated in inches, because that is how KDP states them (CON-018 for
        the first two; CARD-199's research for the last two, stopping at this
        project's one real trim's own page-count ceiling rather than KDP's
        general 828 — see the module docstring).
        """
        assert KDP_GUTTER_BANDS == (
            (150, Decimal("0.375")),
            (300, Decimal("0.5")),
            (500, Decimal("0.625")),
            (590, Decimal("0.75")),
        )
        assert MAX_MODELLED_PAGE_COUNT == 590

    @pytest.mark.parametrize(
        "page_count,expected_band",
        [
            (1, (1, 150)),
            (150, (1, 150)),
            (151, (151, 300)),
            (300, (151, 300)),
            # CARD-199 AC-1/AC-2: the two new bands.
            (301, (301, 500)),
            (400, (301, 500)),
            (500, (301, 500)),
            (501, (501, 590)),
            (550, (501, 590)),
            (590, (501, 590)),
        ],
    )
    def test_the_band_is_named_as_a_page_range(self, page_count, expected_band) -> None:
        assert kdp_page_band(page_count) == expected_band

    def test_the_real_kdp_ceiling_still_has_a_modelled_gutter(self) -> None:
        """CARD-199 AC-3: 590 is inside the table, not past it.

        The real KDP ceiling for this project's one trim (8.5"x11", CON-018's
        Book 1) falls *inside* the general table's 501-700 band, so the
        table this module records stops exactly at that reachable ceiling —
        and a book of exactly 590 pages still gets a modelled minimum rather
        than being refused as unmodelled.
        """
        assert kdp_page_band(MAX_MODELLED_PAGE_COUNT) == (501, 590)
        assert kdp_min_gutter_cm(MAX_MODELLED_PAGE_COUNT) == pytest.approx(1.905)

    @pytest.mark.parametrize("page_count", [591, 700, 10_000])
    def test_above_the_real_ceiling_it_refuses_rather_than_guessing(
        self, page_count
    ) -> None:
        """The one thing this module will not do: invent a band past 590.

        KDP's real table continues past 590 pages (CARD-199's research
        recorded exactly what with), but those page counts are unreachable
        for this project's one real trim — see the module docstring — so a
        page count above the recorded table is refused with what is missing
        rather than measured against a number that describes no real book.
        """
        with pytest.raises(KdpPageCountNotModelled) as refused:
            kdp_min_gutter_cm(page_count)
        assert "not modelled above 590 pages" in str(refused.value)

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

    @pytest.mark.parametrize(
        "page_count,minimum_as_the_project_spells_it",
        [(1, 0.95), (150, 0.95), (151, 1.27), (300, 1.27)],
    )
    def test_the_projects_own_spelling_of_each_minimum_still_passes(
        self, page_count, minimum_as_the_project_spells_it
    ) -> None:
        """CON-018 writes 0.375 in as "0.95 cm" and 0.5 in as "1.27 cm".

        Those two strings are the only forms the ``books`` margin columns can
        hold for those bands, and they are what every book created on the
        Book 1 profile stores. Refusing them would reject every such book —
        far worse than the sub-minimum window the flooring below closes — so
        this is pinned on both sides of the 150-page boundary.
        """
        assert gutter_refusal(page_count, minimum_as_the_project_spells_it) is None

    @pytest.mark.parametrize(
        "page_count,stored_cm,floored_cm",
        [
            # Below the two-decimal minimum, but close enough that half-up
            # rounding of the stored value promoted it to exactly that
            # minimum and let it through.
            (150, 0.945, "0.94"),
            (1, 0.9499, "0.94"),
            (300, 1.265, "1.26"),
            (151, 1.2699, "1.26"),
        ],
    )
    def test_a_stored_gutter_is_never_rounded_up_into_compliance(
        self, page_count, stored_cm, floored_cm
    ) -> None:
        """The stored value is floored to two decimals, never rounded half-up.

        Review cycle 1, F-003. Rounding the *stored* gutter half-up let a
        gutter in [0.945, 0.9525) read as "0.95" and pass the gate, so the
        book was accepted here and rejected at KDP upload — the exact failure
        this check exists to catch, and the unsafe direction for the error to
        point in. The minimum keeps its half-up rounding (that is CON-018's
        own spelling of it, pinned in the test above); only the value under
        test is floored, so it can read narrower than it is but never wider.

        The comparison is still made at the column's two decimals, so a stored
        value in [0.95, 0.9525) is accepted — that is CON-018's spelling of
        the band, not a hole. What is closed is the half-decimal below it.
        """
        refusal = gutter_refusal(page_count, stored_cm)
        assert refusal is not None, (
            f"{stored_cm} cm is below KDP's minimum for {page_count} pages "
            "and must not be rounded up into compliance"
        )
        assert f"stores {floored_cm} cm" in refusal

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
    """AC-271 (FR-042) — 125 pages before the key + 150 answer pages = 275.

    The criterion that matters most, re-pointed at CARD-198's own
    arithmetic: before this card, the *packed* key brought a 150-puzzle book
    back from over 300 pages to 155; since CARD-198 the answer section is
    one full page per puzzle, unpacked, so the same book is 275 — still well
    short of KDP's old 300-page ceiling (and comfortably inside CARD-199's
    widened table), but still the count that must include the answer
    section at all: a count that left it out would put this book at 125
    pages — inside KDP's 0.375 in band — and pass a book KDP would refuse at
    upload for its real 275.
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
        """Pin the criterion's own arithmetic: 125 + 150, and 125 alone passes.

        The 125 pages before the key are the guide page, the two level
        dividers, the 121 puzzle pages and the SOLUTIONS divider; 150 is one
        answer page per puzzle (CARD-198). The second assertion is the bug
        this criterion exists to make impossible — at 125 pages the very
        same gutter is accepted.
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
        """150 answers on 150 pages (CARD-198), each puzzle answered once."""
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
        assert 'data-unpaired-page-count="304"' in shown


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

    The two books differ by one puzzle and nothing else: the same builders, the
    same tiers, the same stored 0.375 in gutter. So the verdict that changes
    between them is the page count crossing 150 and can be nothing else.

    **CARD-198 note.** Since the answer section is one page per puzzle, an
    extra puzzle ordinarily costs *two* pages (its own puzzle page and its
    own answer page) — never the clean "+1" this boundary needs. The
    corpora's medium tier (:func:`pairs_up`) is what keeps it at one: 41 is
    odd, so one of them prints alone; 42 is even, so that same one now pairs
    with the new puzzle instead — the puzzle-page count does not move, and
    only the new puzzle's own answer page does.
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


# --------------------------------------------------------------------------
# CARD-199 — the table extended past the old 300-page ceiling
# --------------------------------------------------------------------------


class TestBookFinalise_RefusesGutterInANewBandBeyondThreeHundredPages:
    """AC-5 (FR-030) — 350 interior pages, storing the *old* band's minimum.

    Inside the new 301-500 band, KDP's minimum there (0.625 in / 1.59 cm) is
    wider than the old 151-300 band's (0.5 in / 1.27 cm) this book stores.
    The refusal must name the new band and its own minimum — not the old
    "not modelled" wording this page count got before this card, and not a
    silent accept either.
    """

    def test_finalise_is_refused_naming_the_new_band(self, panel) -> None:
        book_id = panel.book(AC199_NEW_BAND_CORPUS, gutter="1.27")

        shown = refusal_of(panel.finalise(book_id))

        assert f"{AC199_NEW_BAND_PAGES} pages" in shown
        assert KDP_BAND_TEXT_301_500 in shown
        assert "stores 1.27 cm" in shown
        assert "not modelled" not in shown
        assert panel.status(book_id) == DRAFT

    def test_the_stored_gutter_is_not_changed(self, panel) -> None:
        """G-1: finalise refuses; it never raises the gutter to make it fit."""
        book_id = panel.book(AC199_NEW_BAND_CORPUS, gutter="1.27")

        panel.finalise(book_id)

        assert panel.gutter(book_id) == "1.27"

    def test_the_scenario_really_has_that_many_pages(self, panel) -> None:
        """350 pages, measured off the export's own page plan, not assumed."""
        book_id = panel.book(AC199_NEW_BAND_CORPUS, gutter="1.27")

        assert panel.counts(book_id).page_count == AC199_NEW_BAND_PAGES
        assert kdp_page_band(AC199_NEW_BAND_PAGES) == (301, 500)
        assert gutter_refusal(AC199_NEW_BAND_PAGES, 1.27) is not None
        assert gutter_refusal(AC199_NEW_BAND_PAGES, 1.59) is None

    def test_at_the_new_bands_own_minimum_the_same_book_is_accepted(
        self, panel
    ) -> None:
        """The criterion is about the gutter, not about the 350 pages."""
        book_id = panel.book(AC199_NEW_BAND_CORPUS, gutter="1.59")

        response = panel.finalise(book_id)

        assert response.status_code == 302, refusal_of(response)
        assert panel.status(book_id) != DRAFT


class TestBookFinalise_ABookJustOverTheOldThreeHundredPageCeilingNowFinalises:
    """AC-6 (CARD-198's own regression scenario) — ~305 pages now finalises.

    Before this card, a book this size was refused outright with
    ``KdpPageCountNotModelled`` because the table stopped at 300 pages. This
    card's 301-500 band covers it, so the same book, storing that band's own
    minimum, finalises — no "not modelled" refusal.
    """

    def test_it_finalises_rather_than_refusing_as_not_modelled(self, panel) -> None:
        book_id = panel.book(AC199_CARD198_CORPUS, gutter="1.59")

        response = panel.finalise(book_id)

        assert response.status_code == 302, refusal_of(response)
        assert panel.status(book_id) == BookStatus.READY_FOR_PDF.value

    def test_the_scenario_really_has_that_many_pages(self, panel) -> None:
        book_id = panel.book(AC199_CARD198_CORPUS, gutter="1.59")

        assert panel.counts(book_id).page_count == AC199_CARD198_PAGES
        assert AC199_CARD198_PAGES > 300, "the old ceiling this card fixes"
        assert kdp_page_band(AC199_CARD198_PAGES) == (301, 500)
        assert gutter_refusal(AC199_CARD198_PAGES, 1.59) is None


class TestBookFinalise_AnswerSectionGrowthCanCrossTheThreeHundredPageCeiling:
    """AC-8 (CARD-198) — a book that used to finalise can now refuse outright.

    :data:`AC8_CORPUS` sat at 299 pages under the old *packed* answer key —
    comfortably inside the old 300-page ceiling, on the gutter CON-018's own
    profile stores — purely because its answers packed six-up as tightly as
    INV-011 ever allowed and its puzzle pages paired two-up. Since CARD-198
    replaced that packed key with one full answer page per puzzle, the exact
    same book, same gutter, same everything else, is 669 pages — over even
    CARD-199's widened 590-page ceiling. Finalise must refuse it cleanly with
    :class:`KdpPageCountNotModelled`'s own wording, never crash and never
    silently truncate the count to something that fits.

    This is CARD-198's own flagged consequence (not a hypothetical): the
    card's own "What to implement" names
    ``tests/helpers/book_corpus.py``'s 150-puzzle corpus as crossing from
    182 to roughly 305 pages, which stays inside 590 and still finalises —
    so this class's job is to name a book that genuinely crosses even the
    *new*, wider ceiling, which that corpus does not.
    """

    def test_the_old_packed_key_would_have_fit_comfortably(self, panel) -> None:
        """The premise: before CARD-198, this book was never a problem.

        Measured through the still-present, still-unedited packing
        machinery (``book_answer_key.pack_answer_pages``, G-5) over this
        book's own puzzle-page plan — not re-derived from the docstring's
        arithmetic alone.
        """
        from nonogram.admin.book_answer_key import Answer, pack_answer_pages
        from nonogram.admin.book_pdf_generator import _answer_extent, _pairable_tier

        book_id = panel.book(AC8_CORPUS)
        book = panel.books.get_book(book_id)
        rows = [panel.store.get_puzzle(pid) for pid in book.puzzle_ids]
        generator = BookPDFGenerator(book)
        payloads = [generator._payload(row) for row in rows]

        plan = generator.puzzle_pages(payloads, first_page=2)
        answers = [
            Answer(
                number=i + 1,
                width=_answer_extent(p, i + 1)[0],
                height=_answer_extent(p, i + 1)[1],
                level=_pairable_tier(p),
            )
            for i, p in enumerate(payloads)
        ]
        key = pack_answer_pages(answers)
        old_total = 1 + 1 + len(plan) + 1 + len(key)

        assert len(plan) < len(payloads), "the puzzle pages are expected to pair"
        assert all(answer.width <= 20 and answer.height <= 20 for answer in answers)
        assert old_total == AC8_OLD_PACKED_PAGES
        assert old_total <= 300, "the premise: this book fit before CARD-198"
        assert gutter_refusal(old_total, 1.27) is None, (
            "CON-018's own gutter was always enough for the old packed book"
        )

    def test_the_real_book_now_exceeds_the_modelled_ceiling(self, panel) -> None:
        """CARD-198's real page plan, measured — not assumed from the corpus note."""
        book_id = panel.book(AC8_CORPUS, gutter="1.27")

        counts = panel.counts(book_id)

        assert counts.page_count == AC8_PAGES
        assert counts.answer_page_count == 444, "one answer page per puzzle"
        assert AC8_PAGES > MAX_MODELLED_PAGE_COUNT

    def test_finalise_refuses_cleanly_with_the_not_modelled_wording(
        self, panel
    ) -> None:
        """Not a crash, not a silent truncation — the named, worded refusal."""
        book_id = panel.book(AC8_CORPUS, gutter="1.27")

        response = panel.finalise(book_id)
        shown = refusal_of(response)

        assert f"not modelled above {MAX_MODELLED_PAGE_COUNT} pages" in shown
        assert f"runs to {AC8_PAGES}" in shown
        assert panel.status(book_id) == DRAFT
        assert panel.gutter(book_id) == "1.27", "G-1: never silently widened"

    def test_the_book_is_not_silently_truncated_to_a_modelled_count(
        self, panel
    ) -> None:
        """The negative half: no band is named, because none applies."""
        book_id = panel.book(AC8_CORPUS, gutter="1.27")

        shown = refusal_of(panel.finalise(book_id))

        for band_text in (KDP_BAND_TEXT, KDP_BAND_TEXT_301_500, KDP_BAND_TEXT_501_590):
            assert band_text not in shown, (
                "a refusal naming a band would mean the count was quietly "
                "read as something inside KDP's table"
            )


class TestBookFinalise_AnswerPageCountAndBeforePairingReflectNoPacking:
    """AC-10 (CARD-198) — "Answer pages" and "Before pairing", read off the screen.

    Both figures are read straight off ``InteriorStream``/``InteriorCounts``
    through the template — neither is edited by this card (point 6 of "What
    to implement") — so what is pinned here is what those numbers *mean*
    now that there is no packing: "Answer pages" is the drawable-puzzle
    count exactly, and "Before pairing" differs from the paired count only
    by the two-up pairing term, never by a packing saving that no longer
    exists to bundle in.

    :data:`AC271_CORPUS` is reused for its already-measured shape: 150
    puzzles, 29 of which pair two-up, 150 pages for the answer section.
    """

    def test_answer_pages_equals_the_drawable_puzzle_count(self, panel) -> None:
        book_id = panel.book(AC271_CORPUS)

        shown = panel.shown(book_id)

        assert f'data-answer-page-count="{AC271_PUZZLES}"' in shown
        assert AC271_ANSWER_PAGES == AC271_PUZZLES, (
            "no packing: one answer page per puzzle is the drawable count"
        )

    def test_before_pairing_differs_from_the_paired_count_by_pairing_alone(
        self, panel
    ) -> None:
        book_id = panel.book(AC271_CORPUS)
        counts = panel.counts(book_id)

        shown = panel.shown(book_id)

        # The screen's own figures.
        assert f'data-interior-page-count="{AC271_PAGES}"' in shown
        assert f'data-unpaired-page-count="{counts.unpaired_page_count}"' in shown
        assert "− 29 shared" in html.unescape(shown)

        # What that 29 *is*: the answer-page term is identical on both sides
        # of the subtraction (CARD-198 — no packing saving left in it), so
        # the whole difference is the puzzle section's own two-up pairing.
        saved = counts.unpaired_page_count - counts.page_count
        assert saved == 29
        unpaired_answer_pages_if_still_packed = AC271_ANSWER_PAGES  # i.e. 150, not 30
        assert (
            counts.unpaired_page_count
            == 1 + 2 + AC271_PUZZLES + 1 + unpaired_answer_pages_if_still_packed
        ), "the answer term is the same 150 on both sides of the subtraction"

    def test_a_book_with_no_pairing_at_all_shows_no_saving(self, panel) -> None:
        """The control: nothing to subtract, nothing shown as saved."""
        book_id = panel.book(((alone_six_up, "easy", 5),))

        shown = panel.shown(book_id)

        assert "shared" not in shown
        counts = panel.counts(book_id)
        assert counts.unpaired_page_count == counts.page_count


# --------------------------------------------------------------------------
# CARD-153 — Finalise does not hide a broken page plan behind "About N"
# --------------------------------------------------------------------------
#
#   AC-1  TestFinaliseCounts_PlanTripwireIsNotAnEstimate
#   AC-2  TestFinaliseCounts_ShowsWhyTheCountIsApproximate
#   AC-3  TestFinalise_UncountableBookStaysInDraft
#   AC-4  TestFinaliseGutter_InexactRefusalSaysAbout
#   AC-5  is ``TestBookFinalise_OffersBothDownloads`` in
#         ``tests/test_book_export_interior_cover.py``, rewritten.

#: A three-puzzle book of :func:`alone` easy 22x22s, which never pair.
SMALL_CORPUS = ((alone, "easy", 3),)

#: Its interior, counted by hand rather than by the code under test: 1 guide
#: page + 1 easy divider + 3 single puzzle pages + the SOLUTIONS divider + 3
#: full solved answer pages (CARD-198: one per puzzle, where this book took
#: one packed four-up page before this card). Pairing nothing, this is both
#: its exact count on a legal sheet and its sheet-free bound on an illegal one.
SMALL_PAGES = 9

#: The sheet builder's reason for refusing AC-179's 0.60 cm, written out here.
REASON_060 = "book gutter_margin_cm is 0.6 cm, below the 0.635 cm minimum side margin"

#: The logger the panel logs through (``Flask(__name__)``'s own name).
PANEL_LOGGER = "nonogram.admin.app"


def _drop_last_planned_page(monkeypatch):
    """Break the section walk so it loses its last puzzle page.

    The real :meth:`interior_stream` then trips its *own* first plan tripwire
    ("the page plan prints ...") — the exporter bug the tripwire exists for —
    rather than a stand-in exception this test raised itself.
    """
    import dataclasses

    from nonogram.admin.book_pdf_generator import PuzzlePagePlan

    original = BookPDFGenerator.section_plan

    def broken(self, puzzles):
        plan = original(self, puzzles)
        last = max(
            i for i, page in enumerate(plan.pages) if isinstance(page, PuzzlePagePlan)
        )
        pages = [page for i, page in enumerate(plan.pages) if i != last]
        return dataclasses.replace(plan, pages=pages)

    monkeypatch.setattr(BookPDFGenerator, "section_plan", broken)
    return "the page plan prints"


#: CARD-198 removed the second tripwire this parametrize used to cover
#: ("the answer key holds ..."): since the answer section is no longer
#: packed, there is no second walk left for it to disagree with (see
#: ``interior_stream``'s own docstring). ``_drop_last_planned_page`` is the
#: one tripwire the plan can still fail on, and the only case left here.
TRIPWIRES = pytest.mark.parametrize(
    "break_the_plan",
    (_drop_last_planned_page,),
    ids=("page-plan",),
)


def _counts_of(panel, book_id):
    """What Finalise's own helper reports for ``book_id``."""
    from nonogram.admin.app import _interior_counts

    book = panel.books.get_book(book_id)
    return _interior_counts(book, [panel.store.get_puzzle(p) for p in book.puzzle_ids])


class TestFinaliseCounts_PlanTripwireIsNotAnEstimate:
    """AC-1 — a plan tripwire is an exporter bug, not an approximate count."""

    @TRIPWIRES
    def test_the_helper_logs_the_tripwire_with_its_traceback_and_lets_it_through(
        self, panel, monkeypatch, caplog, break_the_plan
    ) -> None:
        """Asked of the helper itself, outside a request, so the log record
        can only be the helper's own — not Flask's "Exception on ..." line,
        which a 500 would add whether or not the helper logged anything."""
        book_id = panel.book(SMALL_CORPUS)
        phrase = break_the_plan(monkeypatch)

        with caplog.at_level("ERROR", logger=PANEL_LOGGER):
            with pytest.raises(RuntimeError, match=phrase) as raised:
                _counts_of(panel, book_id)

        (record,) = [r for r in caplog.records if r.name == PANEL_LOGGER]
        assert record.exc_info[1] is raised.value
        assert record.exc_info[2] is not None  # the traceback itself
        assert book_id in record.getMessage()

    @TRIPWIRES
    def test_the_screen_shows_no_count_and_the_error_is_logged_with_its_traceback(
        self, panel, monkeypatch, caplog, break_the_plan
    ) -> None:
        book_id = panel.book(SMALL_CORPUS)
        phrase = break_the_plan(monkeypatch)
        panel.app.config["PROPAGATE_EXCEPTIONS"] = False

        with caplog.at_level("ERROR", logger=PANEL_LOGGER):
            response = panel.client.get(f"/book/{book_id}/finalize")
        body = response.get_data(as_text=True)

        assert response.status_code == 500
        assert "About " not in body
        assert "interior page" not in body
        assert "data-interior-page-count" not in body
        logged = [
            record
            for record in caplog.records
            if record.name == PANEL_LOGGER
            and record.exc_info
            and phrase in str(record.exc_info[1])
        ]
        # CARD-171 AC-2: once — by the helper; Flask no longer logs it again.
        assert len(logged) == 1, [r.getMessage() for r in caplog.records]
        assert isinstance(logged[0].exc_info[1], RuntimeError)
        assert logged[0].exc_info[2] is not None  # the traceback itself

    @TRIPWIRES
    def test_save_and_finish_does_not_let_the_book_leave_draft(
        self, panel, monkeypatch, break_the_plan
    ) -> None:
        book_id = panel.book(SMALL_CORPUS)
        break_the_plan(monkeypatch)
        panel.app.config["PROPAGATE_EXCEPTIONS"] = False

        response = panel.finalise(book_id)

        assert response.status_code != 302
        assert panel.status(book_id) == DRAFT

    def test_a_tripwire_in_a_book_with_a_malformed_row_is_not_read_as_uncountable(
        self, panel, monkeypatch, caplog
    ) -> None:
        """Review F-002: the rows failing the sheet-free count is not enough.

        A row that cannot build a payload is dropped from the plan before the
        answer key sees it, so its malformed grid does not stop the walk — but
        the sheet-free count still reads that grid and refuses it. The real
        page-plan tripwire then fires in a book whose rows *also* fail the
        sheet-free check, and it must surface as the exporter's error, logged
        at ERROR — not as "cannot be counted" (``None``) at WARNING.
        """
        book_id = panel.book(SMALL_CORPUS)
        first = panel.books.get_book(book_id).puzzle_ids[0]
        panel.store.puzzles[first]["grid"] = []  # sheet-free count refuses it
        panel.store.puzzles[first]["clues_rows"] = 5  # payload pass drops it
        phrase = _drop_last_planned_page(monkeypatch)

        with caplog.at_level("WARNING", logger=PANEL_LOGGER):
            with pytest.raises(RuntimeError, match=phrase) as raised:
                _counts_of(panel, book_id)

        (record,) = [r for r in caplog.records if r.name == PANEL_LOGGER]
        assert record.levelname == "ERROR"
        assert record.exc_info[1] is raised.value

    @TRIPWIRES
    def test_save_and_finish_names_the_tripwire_on_its_error_page_and_logs_it_once(
        self, panel, monkeypatch, caplog, break_the_plan
    ) -> None:
        """Review F-005: not flashed into a re-render that 500s a second time."""
        book_id = panel.book(SMALL_CORPUS)
        phrase = break_the_plan(monkeypatch)
        panel.app.config["PROPAGATE_EXCEPTIONS"] = False

        with caplog.at_level("ERROR", logger=PANEL_LOGGER):
            response = panel.finalise(book_id)
        body = html.unescape(response.get_data(as_text=True))

        assert response.status_code == 500
        assert phrase in body
        assert "status is not changed" in body
        assert panel.status(book_id) == DRAFT
        logged = [
            r for r in caplog.records if r.name == PANEL_LOGGER and r.exc_info
        ]
        assert len(logged) == 1, [r.getMessage() for r in logged]

    def test_an_error_after_the_sheet_exists_is_not_read_as_an_unlayable_spec(
        self, panel, monkeypatch
    ) -> None:
        """Only the constructor's ``ValueError`` means "cannot be laid out".

        The same exception class raised from the plan itself, on a sheet that
        exists, propagates — catching ``ValueError`` around the whole call
        would turn it back into an estimate.
        """
        book_id = panel.book(SMALL_CORPUS)

        def raising(self, puzzles):
            raise ValueError("a bug inside the plan")

        monkeypatch.setattr(BookPDFGenerator, "interior_stream", raising)

        with pytest.raises(ValueError, match="a bug inside the plan"):
            _counts_of(panel, book_id)

    def test_a_layout_abort_on_clean_rows_is_the_exporters_error(
        self, panel, monkeypatch, caplog
    ) -> None:
        """Review F-008: the cause's shape alone does not make a malformed row.

        The pairing walk wraps any failure of the shared-page layout as
        "puzzle <id> could not be laid out" — a ``RuntimeError`` caused by
        the original exception, the very shape a malformed row's abort takes.
        On rows the sheet-free count accepts, that abort is an exporter bug:
        it must be re-raised and logged at ERROR, not read as "cannot be
        counted" (``None``) at WARNING.
        """
        import nonogram.admin.book_pdf_generator as generator_module

        book_id = panel.book(((pairs_up, "easy", 2),))
        book = panel.books.get_book(book_id)
        rows = [panel.store.get_puzzle(p) for p in book.puzzle_ids]
        assert unpaired_interior_page_count(rows) > 0  # the rows are well-formed

        def broken_layout(*args, **kwargs):
            raise ValueError("a layout bug")

        monkeypatch.setattr(generator_module, "compute_pair_layout", broken_layout)

        with caplog.at_level("WARNING", logger=PANEL_LOGGER):
            with pytest.raises(RuntimeError, match="could not be laid out") as raised:
                _counts_of(panel, book_id)

        assert isinstance(raised.value.__cause__, ValueError)  # the abort's shape
        (record,) = [r for r in caplog.records if r.name == PANEL_LOGGER]
        assert record.levelname == "ERROR"
        assert record.exc_info[1] is raised.value
        assert record.exc_info[2] is not None  # the traceback itself


def _db_went_away(panel, monkeypatch):
    """Reading a row's book title fails — a database error, not the plan's."""

    def failing(*args, **kwargs):
        raise KeyError("db went away")

    monkeypatch.setattr(panel.books, "get_puzzle_title", failing)
    return KeyError, "db went away"


def _generator_cannot_start(panel, monkeypatch):
    """The generator's constructor fails with something other than its
    documented ``ValueError`` — the exporter's error, raised before any plan."""

    def failing(self, *args, **kwargs):
        raise TypeError("the generator could not start")

    monkeypatch.setattr(BookPDFGenerator, "__init__", failing)
    return TypeError, "the generator could not start"


class TestSaveAndFinish_OnlyThePlanFailureIsBlamedOnThePlan:
    """Review F-007 — Save and finish answers only the helper's own logged
    page-plan failure with its "page plan could not be built" page; any other
    error takes the route's ordinary path and is logged with its traceback."""

    @pytest.mark.parametrize(
        "break_something_else",
        (_db_went_away, _generator_cannot_start),
        ids=("row-read", "generator-constructor"),
    )
    def test_a_non_plan_error_is_logged_and_not_called_a_page_plan_failure(
        self, panel, monkeypatch, caplog, break_something_else
    ) -> None:
        book_id = panel.book(SMALL_CORPUS)
        error_type, message = break_something_else(panel, monkeypatch)
        panel.app.config["PROPAGATE_EXCEPTIONS"] = False

        with caplog.at_level("ERROR", logger=PANEL_LOGGER):
            response = panel.finalise(book_id)
        body = html.unescape(response.get_data(as_text=True))

        assert response.status_code == 500
        assert "page plan could not be built" not in body
        assert panel.status(book_id) == DRAFT
        logged = [
            r
            for r in caplog.records
            if r.name == PANEL_LOGGER
            and r.levelname == "ERROR"
            and r.exc_info
            and isinstance(r.exc_info[1], error_type)
            and message in str(r.exc_info[1])
        ]
        assert logged, [r.getMessage() for r in caplog.records]
        assert logged[0].exc_info[2] is not None  # the traceback itself


class TestFinaliseCounts_ShowsWhyTheCountIsApproximate:
    """AC-2 — an unlayable print spec: "About N", the reason, and Print setup."""

    @pytest.mark.parametrize(
        "column, value, reason",
        (
            ("gutter_margin_cm", GUTTER_060, REASON_060),
            ("trim_width_cm", "5", "book trim_width_cm is 5 cm, outside KDP's 10..30 cm"),
        ),
    )
    def test_the_screen_names_the_reason_and_points_to_print_setup(
        self, panel, column, value, reason
    ) -> None:
        book_id = panel.book(SMALL_CORPUS)
        setattr(panel.books.get_book(book_id), column, value)

        shown = panel.shown(book_id)

        assert f"About {SMALL_PAGES} interior pages" in shown
        assert 'data-interior-page-count-exact="false"' in shown
        assert "data-page-count-approximate" in shown
        assert reason in html.unescape(shown)
        assert f'href="/book/{book_id}/setup-print"' in shown
        assert "Print setup</a>" in shown

    def test_the_helper_carries_the_builders_reason(self, panel) -> None:
        book_id = panel.book(SMALL_CORPUS, gutter=GUTTER_060)

        counts = _counts_of(panel, book_id)

        assert counts.exact is False
        assert counts.page_count == SMALL_PAGES
        assert counts.unreadable == REASON_060

    def test_an_exact_count_carries_no_such_note(self, panel) -> None:
        book_id = panel.book(SMALL_CORPUS)

        shown = panel.shown(book_id)

        assert f"About {SMALL_PAGES}" not in shown
        assert "data-page-count-approximate" not in shown
        assert f'data-interior-page-count="{SMALL_PAGES}"' in shown


def _uncountable(panel, gutter: str = GUTTER_060) -> str:
    """A book with a row whose answer cannot be measured — by default on no sheet.

    The row is broken after it was added (``add_puzzles_to_book`` measures
    every member), the way a legacy or hand-edited row would reach the store.
    """
    book_id = panel.book(SMALL_CORPUS, gutter=gutter)
    first = panel.books.get_book(book_id).puzzle_ids[0]
    panel.store.puzzles[first]["grid"] = []
    return book_id


class TestFinalise_UncountableBookStaysInDraft:
    """AC-3 — no page count, no leaving draft; and the screen says why."""

    @pytest.mark.parametrize("gutter", (GUTTER_060, GUTTER_0375_IN), ids=("no-sheet", "sheet"))
    def test_the_book_cannot_be_counted_at_all(self, panel, gutter) -> None:
        """On a sheet too: a malformed row is the book's, not a plan tripwire."""
        assert _counts_of(panel, _uncountable(panel, gutter)) is None

    @pytest.mark.parametrize("gutter", (GUTTER_060, GUTTER_0375_IN), ids=("no-sheet", "sheet"))
    def test_save_and_finish_refuses_and_the_book_stays_in_draft(
        self, panel, gutter
    ) -> None:
        book_id = _uncountable(panel, gutter)

        shown = refusal_of(panel.finalise(book_id))

        assert panel.status(book_id) == DRAFT
        assert "interior pages cannot be counted" in shown
        assert "status is not changed" in shown
        assert panel.gutter(book_id) == gutter  # G-1: refused, not adjusted

    def test_a_book_past_draft_is_not_told_it_stays_in_draft(self, panel) -> None:
        """Review F-004: the refusal is true of a ``ready_for_pdf`` book too."""
        book_id = panel.book(SMALL_CORPUS)
        assert panel.finalise(book_id).status_code == 302
        ready = BookStatus.READY_FOR_PDF.value
        assert panel.status(book_id) == ready
        first = panel.books.get_book(book_id).puzzle_ids[0]
        panel.store.puzzles[first]["grid"] = []

        shown = refusal_of(panel.finalise(book_id))

        assert "interior pages cannot be counted" in shown
        assert "draft" not in shown.split("cannot be counted", 1)[1].split("</", 1)[0]
        assert "status is not changed" in shown
        assert panel.status(book_id) == ready

    def test_the_screen_says_the_pages_cannot_be_counted(self, panel) -> None:
        shown = panel.shown(_uncountable(panel))

        assert "Cannot be counted" in shown
        assert "data-interior-page-count=" not in shown


class TestFinaliseGutter_InexactRefusalSaysAbout:
    """AC-4 — the refusal and the screen agree on whether the count is exact."""

    def test_an_inexact_count_is_refused_as_about_n_pages(self, panel) -> None:
        book_id = panel.book(SMALL_CORPUS, gutter=GUTTER_060)

        shown = refusal_of(panel.finalise(book_id))

        assert f"runs to about {SMALL_PAGES} pages" in shown
        assert f"runs to {SMALL_PAGES} pages" not in shown
        assert f"About {SMALL_PAGES} interior pages" in shown
        assert panel.status(book_id) == DRAFT

    def test_an_exact_count_is_refused_without_about(self, panel) -> None:
        """The word is the count's exactness, not decoration on every refusal."""
        book_id = panel.book(CK1_OVER_CORPUS)

        shown = refusal_of(panel.finalise(book_id))

        assert f"runs to {CK1_OVER_PAGES} pages" in shown
        assert "runs to about" not in shown
        assert f"About {CK1_OVER_PAGES}" not in shown

    def test_an_unreadable_gutter_on_an_inexact_count_says_about(self) -> None:
        """The other refusal ``_kdp_gutter_refusal`` composes says it too."""
        from nonogram.admin.app import InteriorCounts, _kdp_gutter_refusal

        class Row:
            gutter_margin_cm = "wide"

        counts = InteriorCounts(
            page_count=SMALL_PAGES,
            unpaired_page_count=SMALL_PAGES,
            answer_page_count=None,
            exact=False,
            unreadable="book gutter_margin_cm must be a number of cm, not 'wide'",
        )

        refusal = _kdp_gutter_refusal(Row(), counts)

        assert f"its about {SMALL_PAGES} interior pages" in refusal

    @pytest.mark.parametrize("exact", (False, True), ids=("inexact", "exact"))
    def test_above_the_table_an_inexact_count_says_about(self, exact) -> None:
        """Review F-001: the not-modelled refusal says "about N" too.

        Above :data:`MAX_MODELLED_PAGE_COUNT` an inexact count is the
        sheet-free upper bound; "runs to 350." would state it as a fact.
        """
        from nonogram.admin.app import InteriorCounts, _kdp_gutter_refusal
        from nonogram.admin.book_kdp import MAX_MODELLED_PAGE_COUNT

        pages = MAX_MODELLED_PAGE_COUNT + 50

        class Row:
            gutter_margin_cm = GUTTER_060

        counts = InteriorCounts(
            page_count=pages,
            unpaired_page_count=pages,
            answer_page_count=None,
            exact=exact,
            unreadable=None if exact else REASON_060,
        )

        refusal = _kdp_gutter_refusal(Row(), counts)

        assert f"not modelled above {MAX_MODELLED_PAGE_COUNT} pages" in refusal
        if exact:
            assert f"runs to {pages}." in refusal
            assert "about" not in refusal
        else:
            assert f"runs to about {pages}." in refusal
            assert f"runs to {pages}" not in refusal

    def test_a_reworded_refusal_still_says_about(self) -> None:
        """Should ``book_kdp`` stop saying "runs to N", "about" is not lost."""
        from nonogram.admin.app import _about

        assert _about("KDP wants 0.95 cm for 7 pages.", 7).endswith(
            "(This book's interior page count is about 7, not exact.)"
        )
        assert _about("It runs to 7 pages.", 7) == "It runs to about 7 pages."


# --------------------------------------------------------------------------
# G-1's second half — the book is laid out on its stored gutter, and only once
# --------------------------------------------------------------------------

#: A gutter the sheet builder accepts (over its 0.635 cm side-margin floor)
#: but KDP refuses at every page count: a refusal on an **exact** count, so the
#: page plan really is built — the case a second layout at a raised gutter
#: would be tempted to "fix".
GUTTER_070 = "0.70"


class _LayoutSpy:
    """Every interior layout Finalise asks for, and the gutter it was asked on.

    Replaces ``BookPDFGenerator`` **where the panel looks it up**
    (``nonogram.admin.app``) with a subclass that records, before the real
    code runs, the gutter column of the book each generator is built on and
    the one each :meth:`interior_stream` lays out — read off the generator's
    own ``book`` at that moment, so a copy of the book carrying another
    gutter, or the stored one bumped for the call and put back, is caught
    either way. ``_interior_counts`` is wrapped too, so "laid out once" is
    asked per count rather than per request: a refused Save-and-finish counts
    in the action and again in the re-render beneath it, both on the stored
    gutter, and that is two counts, not a second layout of one.
    """

    def __init__(self, monkeypatch):
        import nonogram.admin.app as app_module

        self.built: list = []
        self.laid_out: list = []
        self.counts = 0
        spy = self

        class Spied(app_module.BookPDFGenerator):
            def __init__(self, book=None):
                spy.built.append(getattr(book, "gutter_margin_cm", None))
                super().__init__(book)

            def interior_stream(self, puzzles):
                spy.laid_out.append(getattr(self.book, "gutter_margin_cm", None))
                return super().interior_stream(puzzles)

        original_counts = app_module._interior_counts

        def counted(book, puzzles):
            spy.counts += 1
            return original_counts(book, puzzles)

        monkeypatch.setattr(app_module, "BookPDFGenerator", Spied)
        monkeypatch.setattr(app_module, "_interior_counts", counted)


class TestFinaliseGutter_NeverLaidOutAgainAtAnotherGutter:
    """G-1 (CARD-129's G-2): one layout per count, on the gutter the book stores.

    The first half of G-1 — the stored gutter is never raised or rewritten —
    is pinned by :class:`TestKdpGutterTable` and
    :class:`TestBookFinalise_RefusesGutterBelowKdpMinimumForPageCount`. This
    is the second half: Finalise never answers a refused gutter by laying the
    book out again at a wider one, on the screen (GET) or on Save-and-finish
    (POST), for a book whose spec can be laid out and for one whose cannot.
    """

    CASES = pytest.mark.parametrize(
        "runs, gutter, sheet",
        (
            (SMALL_CORPUS, GUTTER_070, True),
            (CK1_OVER_CORPUS, GUTTER_0375_IN, True),
            (SMALL_CORPUS, GUTTER_060, False),
        ),
        ids=("refused-exact-small", "refused-exact-151-pages", "no-sheet-inexact"),
    )

    @staticmethod
    def _assert_only_the_stored_gutter(spy, gutter, sheet) -> None:
        assert spy.counts >= 1
        # Every generator built, and every layout walked, on the stored value.
        assert spy.built and set(spy.built) == {gutter}, spy.built
        assert set(spy.laid_out) <= {gutter}, spy.laid_out
        # One layout per count at most: never a second pass at another gutter.
        assert len(spy.laid_out) <= spy.counts, (spy.laid_out, spy.counts)
        if sheet:
            assert len(spy.laid_out) == spy.counts
        else:
            # No sheet, no layout at all — the count is the sheet-free bound,
            # never a layout on some gutter the builder would accept.
            assert spy.laid_out == []

    @CASES
    def test_the_finalise_screen_lays_the_book_out_once_on_its_stored_gutter(
        self, panel, monkeypatch, runs, gutter, sheet
    ) -> None:
        book_id = panel.book(runs, gutter=gutter)
        spy = _LayoutSpy(monkeypatch)

        panel.shown(book_id)

        assert spy.counts == 1
        self._assert_only_the_stored_gutter(spy, gutter, sheet)
        assert len(spy.laid_out) == (1 if sheet else 0)
        assert panel.gutter(book_id) == gutter

    @CASES
    def test_a_refused_save_and_finish_never_lays_out_at_another_gutter(
        self, panel, monkeypatch, runs, gutter, sheet
    ) -> None:
        book_id = panel.book(runs, gutter=gutter)
        spy = _LayoutSpy(monkeypatch)

        response = panel.finalise(book_id)

        assert "KDP" in refusal_of(response)  # refused, not finalised
        self._assert_only_the_stored_gutter(spy, gutter, sheet)
        assert panel.gutter(book_id) == gutter
        assert panel.status(book_id) == DRAFT

    def test_an_uncountable_book_is_not_laid_out_at_another_gutter(
        self, panel, monkeypatch
    ) -> None:
        """AC-3's refusal too: on a sheet, the malformed row is not retried wider."""
        book_id = _uncountable(panel, GUTTER_0375_IN)
        spy = _LayoutSpy(monkeypatch)

        shown = refusal_of(panel.finalise(book_id))

        assert "interior pages cannot be counted" in shown
        self._assert_only_the_stored_gutter(spy, GUTTER_0375_IN, True)
        assert panel.gutter(book_id) == GUTTER_0375_IN


# --------------------------------------------------------------------------
# CARD-171 — Finalise names a page-plan error on GET, and logs what it flashes
# --------------------------------------------------------------------------
#
#   AC-1  TestFinaliseGet_NamesThePagePlanFailure
#   AC-2  TestFinaliseGet_NamesThePagePlanFailure::test_logs_it_once, and
#         ``test_the_screen_shows_no_count_and_the_error_is_logged_with_its_traceback``
#         above, tightened to one record
#   AC-3  TestFinaliseGet_OtherErrorsStayGeneric
#   AC-4  TestFinalisePost_TransientErrorIsLogged
#   AC-5  TestFinalisePost_PlanGateRefusalIsNotAnError

#: The text the panel's error page uses for the page-plan failure, written out.
PLAN_FAILURE_TEXT = "page plan could not be built"


def _panel_errors(caplog) -> list:
    """The ERROR records on the panel's logger."""
    return [
        r for r in caplog.records if r.name == PANEL_LOGGER and r.levelname == "ERROR"
    ]


class TestFinaliseGet_NamesThePagePlanFailure:
    """AC-1, AC-2 — GET answers the helper's logged plan failure itself."""

    @TRIPWIRES
    def test_the_page_names_the_failure_and_shows_no_count(
        self, panel, monkeypatch, break_the_plan
    ) -> None:
        book_id = panel.book(SMALL_CORPUS)
        phrase = break_the_plan(monkeypatch)
        panel.app.config["PROPAGATE_EXCEPTIONS"] = False

        response = panel.client.get(f"/book/{book_id}/finalize")
        body = html.unescape(response.get_data(as_text=True))

        assert response.status_code == 500
        assert PLAN_FAILURE_TEXT in body
        assert phrase in body
        assert "data-interior-page-count" not in body
        assert "interior page" not in body

    @TRIPWIRES
    def test_logs_it_once(self, panel, monkeypatch, caplog, break_the_plan) -> None:
        book_id = panel.book(SMALL_CORPUS)
        phrase = break_the_plan(monkeypatch)
        panel.app.config["PROPAGATE_EXCEPTIONS"] = False

        with caplog.at_level("ERROR", logger=PANEL_LOGGER):
            panel.client.get(f"/book/{book_id}/finalize")

        (record,) = _panel_errors(caplog)
        assert isinstance(record.exc_info[1], RuntimeError)
        assert phrase in str(record.exc_info[1])
        assert record.exc_info[2] is not None  # the traceback itself


class TestFinaliseGet_OtherErrorsStayGeneric:
    """AC-3 — an error the helper did not stamp keeps the global handler."""

    def test_a_non_plan_error_is_not_named_on_screen(
        self, panel, monkeypatch, caplog
    ) -> None:
        book_id = panel.book(SMALL_CORPUS)
        _error_type, marker = _generator_cannot_start(panel, monkeypatch)
        panel.app.config["PROPAGATE_EXCEPTIONS"] = False

        with caplog.at_level("ERROR", logger=PANEL_LOGGER):
            response = panel.client.get(f"/book/{book_id}/finalize")
        body = html.unescape(response.get_data(as_text=True))

        assert response.status_code == 500
        assert PLAN_FAILURE_TEXT not in body
        assert marker not in body
        # Re-raised unchanged: Flask's own log line carries it.
        assert any(
            isinstance(r.exc_info[1], TypeError) and marker in str(r.exc_info[1])
            for r in _panel_errors(caplog)
            if r.exc_info
        )


def _raise_once(monkeypatch, owner, name, error):
    """Make ``owner.name`` raise ``error`` on its first call, then behave."""
    original = getattr(owner, name)
    calls = []

    def once(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise error
        return original(*args, **kwargs)

    monkeypatch.setattr(owner, name, once)


def _clear_cover_fails_once(panel, monkeypatch, tmp_path, book_id, error):
    """A stored cover whose removal fails once."""
    from pathlib import Path

    panel.app.config["BOOK_COVER_DIR"] = str(tmp_path)
    cover = tmp_path / f"{book_id}_cover.png"
    cover.write_bytes(b"not read")
    with panel.client.session_transaction() as session:
        session[f"book_{book_id}_cover_path"] = str(cover)
        session[f"book_{book_id}_cover_data"] = True
    _raise_once(monkeypatch, Path, "unlink", error)
    return {"action": "clear_cover"}, 200, FINALISE_ACTION_FAILED


def _save_and_finish_fails_once(panel, monkeypatch, tmp_path, book_id, error):
    """The generator's constructor fails once — CARD-153's cycle-3 probe."""
    _raise_once(monkeypatch, BookPDFGenerator, "__init__", error)
    return {"action": "save_and_finish"}, 200, FINALISE_ACTION_FAILED


def _download_pdf_fails_once(panel, monkeypatch, tmp_path, book_id, error):
    """The export's generator fails once."""
    _raise_once(monkeypatch, BookPDFGenerator, "__init__", error)
    return {"action": "download_pdf"}, 302, PDF_EXPORT_FAILED


class TestFinalisePost_TransientErrorIsLogged:
    """AC-4 — an error that clears before the re-render is still logged once.

    CARD-177 AC-1: the flash is the fixed text, and the exception's own
    message (``marker``) is not on the screen.
    """

    @pytest.mark.parametrize(
        "fail_once",
        (_clear_cover_fails_once, _save_and_finish_fails_once, _download_pdf_fails_once),
        ids=("clear_cover", "save_and_finish", "download_pdf"),
    )
    def test_the_flash_is_shown_and_the_error_is_logged_once(
        self, panel, monkeypatch, caplog, tmp_path, fail_once
    ) -> None:
        book_id = panel.book(SMALL_CORPUS)
        marker = "transient-card177-marker"
        error = TypeError(marker)
        form, status, flashed = fail_once(panel, monkeypatch, tmp_path, book_id, error)

        with caplog.at_level("ERROR", logger=PANEL_LOGGER):
            response = panel.client.post(f"/book/{book_id}/finalize", data=form)

        assert response.status_code == status
        if status == 200:
            body = response.get_data(as_text=True)
            assert flashed in html.unescape(body)
            assert marker not in body and marker not in html.unescape(body)
        else:
            with panel.client.session_transaction() as session:
                flashes = session.get("_flashes", [])
            assert ("error", flashed) in flashes
            assert not any(marker in message for _, message in flashes)
            assert marker not in response.headers.get("Location", "")
        (record,) = _panel_errors(caplog)
        assert record.exc_info[1] is error
        assert record.exc_info[2] is not None  # the traceback itself
        assert book_id in record.getMessage()
        assert panel.status(book_id) == DRAFT


class TestFinalisePost_PlanGateRefusalIsNotAnError:
    """AC-5 — the plan gate's refusal is flashed, and is not an ERROR."""

    @pytest.mark.parametrize(
        "make_book",
        (
            lambda panel: panel.book(SMALL_CORPUS),
            lambda panel: _uncountable(panel),
        ),
        ids=("countable", "uncountable"),
    )
    def test_the_refusal_is_flashed_and_nothing_is_logged(
        self, panel, caplog, make_book
    ) -> None:
        book_id = make_book(panel)
        # A plan for three medium puzzles against a selection of three easy
        # ones: the gate (ADR-0035/R1) refuses the easy and the medium cell.
        panel.books.save_plan(book_id, plan_of(corpus((alone, "medium", 3))))

        with caplog.at_level("ERROR", logger=PANEL_LOGGER):
            response = panel.finalise(book_id)
        shown = html.unescape(refusal_of(response))

        assert "x medium: 0% against 100%" in shown, shown
        assert panel.status(book_id) == DRAFT
        assert _panel_errors(caplog) == []
