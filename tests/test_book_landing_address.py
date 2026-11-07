"""CARD-389 — a book's landing address is computed once (ADR-0041/R7, R8).

    AC-1  a finalized, level-grouped book: the landing address and the bundle
          name the same slug, and ``book/<slug>.json`` exists
          (TestBookLanding_PrintedSlugIsTheBundlesSlug)
    AC-2  a book stored mixed (medium, easy, hard, easy): both sides compute
          the slug over print order, the book file lists keys in print order,
          and tile i is the puzzle the interior prints as number i
          (TestBookLanding_NumbersMatchPrintNumbers)
    AC-3  a grouped book's slug equals a literal captured from main before
          this change (TestBookLanding_GroupedBooksKeepTheirSlug)
    AC-4  no stored player domain, no address
          (TestBookLanding_NoDomainNoAddress)
    AC-5  the short form is typable: no scheme, no trailing slash
          (TestBookLanding_ShortAddressIsTypable)
    AC-6  a damaged row cannot shift the numbers
          (TestBookLanding_ADamagedRowCannotShiftNumbers)

**Independence.** The expected slug and keys are computed here by hand from
ADR-0041/R1 and R7's words (:func:`key_by_hand`, :func:`slug_by_hand`) and the
expected print order is the INV-009 grouping spelled out locally, so no
assertion compares :mod:`player_bundle` with itself. The interior's own numbers
come from the real :class:`BookPDFGenerator` ``section_plan`` over the same
rows, so "tile i is printed number i" is asked of the real interior and not of
a model of it.

**The grouped literals** (``GROUPED_SLUG``) were captured by running
``book_slug`` over the keys of these exact grids on main at 20e3815d, before
this card changed ``export_bundle``; they are not re-derived from the code
under test.
"""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from nonogram import clues
from nonogram.admin import player_bundle
from nonogram.admin.book_manager import BookStatus
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from tests.helpers.book_corpus import corpus_book

# The real panel (both storage modes), for the deleted-puzzle path.
from tests.test_book_arrange_size_filter import Panel, panel  # noqa: F401
from tests.test_book_player_domain import GRIDS, add_grid

DOMAIN = "https://nonogram.adverax.io"

#: Captured on main (20e3815d) for ``GROUPED_TIERS`` below, in stored order,
#: which for a grouped book is also print order.
GROUPED_SLUG = "93c416938c"
GROUPED_TIERS = ("easy", "easy", "medium", "hard")


def grid_of(index: int, side: int = 10) -> list[list[bool]]:
    """A distinct ``side``x``side`` grid per ``index`` (one filled diagonal band)."""
    return [
        [(x - y) % side == index % side or (x + y) % side == (index * 3) % side for x in range(side)]
        for y in range(side)
    ]


def record(puzzle_id: str, index: int, tier: str) -> dict:
    grid = grid_of(index)
    found = clues.compute_clues(grid)
    return {
        "id": puzzle_id,
        "grid": grid,
        "clues_rows": [list(c) for c in found.rows],
        "clues_cols": [list(c) for c in found.columns],
        "width": 10,
        "height": 10,
        "puzzle_name": f"Picture {index}",
        "difficulty_tier": tier,
    }


def key_by_hand(grid) -> str:
    """ADR-0041/R1 from its words: sha256 of ``WxH:`` and the cells, ten hex."""
    cells = "".join("1" if c else "0" for row in grid for c in row)
    text = f"{len(grid[0])}x{len(grid)}:{cells}"
    return hashlib.sha256(text.encode()).hexdigest()[:10]


def slug_by_hand(keys) -> str:
    """ADR-0041/R7 from its words: ``book:`` and the keys, no separator."""
    return hashlib.sha256(("book:" + "".join(keys)).encode()).hexdigest()[:10]


def grouped(rows):
    """INV-009 spelled out locally: easy, medium, hard, stable inside a level."""
    rank = {"easy": 0, "medium": 1, "hard": 2}
    return sorted(rows, key=lambda r: rank[r["difficulty_tier"]])


class Store:
    def __init__(self, rows):
        self.rows = {r["id"]: r for r in rows}

    def get_puzzles(self, ids):
        return {i: self.rows[i] for i in ids if i in self.rows}


class Shelf:
    """The two read methods ``export_bundle`` calls, over one finalized book."""

    def __init__(self, ids, title="Winter"):
        self.book = SimpleNamespace(
            status=BookStatus.READY_FOR_PDF.value,
            puzzle_ids=list(ids),
            metadata=SimpleNamespace(title=title),
        )

    def get_all_books(self):
        return [self.book]


def exported(rows, tmp_path, stored_order=None):
    ids = stored_order or [r["id"] for r in rows]
    report = player_bundle.export_bundle(Shelf(ids), Store(rows), tmp_path / "bundle")
    return report, tmp_path / "bundle"


def book_files(root):
    return sorted((root / "book").glob("*.json")) if (root / "book").exists() else []


def interior_numbers(rows) -> list[str]:
    """The ids the real interior prints as puzzle 1, 2, ... for ``rows``."""
    plan = BookPDFGenerator(corpus_book()).section_plan(list(rows))
    return list(plan.ids)


GROUPED_ROWS = [record(f"g{i}", i, t) for i, t in enumerate(GROUPED_TIERS)]
#: medium, easy, hard, easy: the legacy shape CARD-128 describes.
MIXED_ROWS = [
    record("m0", 20, "medium"),
    record("m1", 21, "easy"),
    record("m2", 22, "hard"),
    record("m3", 23, "easy"),
]


class TestBookLanding_PrintedSlugIsTheBundlesSlug:
    def test_the_address_and_the_bundle_name_one_slug(self, tmp_path):
        _, root = exported(GROUPED_ROWS, tmp_path)
        address = player_bundle.landing_address(GROUPED_ROWS, DOMAIN)

        files = book_files(root)
        assert [f.stem for f in files] == [address.slug]
        assert address.url == f"{DOMAIN}/b/{address.slug}"
        assert address.slug == slug_by_hand(key_by_hand(r["grid"]) for r in GROUPED_ROWS)

    def test_the_book_file_still_carries_only_its_three_fields(self, tmp_path):
        """AC-7: nothing new reaches a public asset."""
        _, root = exported(GROUPED_ROWS, tmp_path)
        payload = json.loads(book_files(root)[0].read_text())
        assert set(payload) == {"puzzle_keys", "slug", "title"}


class TestBookLanding_NumbersMatchPrintNumbers:
    def test_a_mixed_book_is_addressed_in_print_order_on_both_sides(self, tmp_path):
        stored = [r["id"] for r in MIXED_ROWS]
        report, root = exported(MIXED_ROWS, tmp_path, stored_order=stored)
        address = player_bundle.landing_address(MIXED_ROWS, DOMAIN)

        printed = interior_numbers(MIXED_ROWS)
        by_id = {r["id"]: r for r in MIXED_ROWS}
        expected_keys = [key_by_hand(by_id[i]["grid"]) for i in printed]

        # Control: the fixture really is mixed, so print order differs from stored.
        assert printed == [r["id"] for r in grouped(MIXED_ROWS)]
        assert printed != stored
        assert slug_by_hand(key_by_hand(r["grid"]) for r in MIXED_ROWS) != address.slug

        (book_file,) = book_files(root)
        payload = json.loads(book_file.read_text())
        assert book_file.stem == address.slug == slug_by_hand(expected_keys)
        assert payload["puzzle_keys"] == expected_keys  # tile i is printed number i

    def test_rows_already_in_print_order_give_the_same_address(self):
        """``print_order`` is idempotent: the interior may pass what it ordered."""
        once = player_bundle.landing_address(MIXED_ROWS, DOMAIN)
        again = player_bundle.landing_address(grouped(MIXED_ROWS), DOMAIN)
        assert once == again


class TestBookLanding_GroupedBooksKeepTheirSlug:
    def test_a_grouped_book_keeps_the_slug_main_gave_it(self, tmp_path):
        _, root = exported(GROUPED_ROWS, tmp_path)
        assert [f.stem for f in book_files(root)] == [GROUPED_SLUG]
        assert player_bundle.landing_address(GROUPED_ROWS, DOMAIN).slug == GROUPED_SLUG


class TestBookLanding_NoDomainNoAddress:
    @pytest.mark.parametrize("domain", [None, "", "   "])
    def test_no_domain_means_no_address(self, domain):
        assert player_bundle.landing_address(GROUPED_ROWS, domain) is None


class TestBookLanding_ADomainIsNotJoinedBlindly:
    @pytest.mark.parametrize(
        "domain", ["a.io", "http://a.io", "https://a.io/b/", "https://a.io/x", "https://a.io?q=1"]
    )
    def test_a_domain_that_is_not_an_https_origin_is_refused(self, domain):
        with pytest.raises(ValueError):
            player_bundle.landing_address(GROUPED_ROWS, domain)

    def test_one_trailing_slash_and_case_are_normalised_like_the_stored_column(self):
        address = player_bundle.landing_address(GROUPED_ROWS, "HTTPS://A.io:8443/")
        assert address.url == f"https://a.io:8443/b/{GROUPED_SLUG}"
        assert address.short == f"a.io:8443/b/{GROUPED_SLUG}"

    def test_the_public_api_is_exported(self):
        for name in ("landing_address", "LandingAddress", "print_ordered_keys", "BOOK_PATH"):
            assert name in player_bundle.__all__


class TestBookLanding_ShortAddressIsTypable:
    @pytest.mark.parametrize("domain", [DOMAIN, DOMAIN + "/"])
    def test_the_short_form_has_no_scheme_and_no_trailing_slash(self, domain):
        address = player_bundle.landing_address(GROUPED_ROWS, domain)
        assert address.short == f"nonogram.adverax.io/b/{GROUPED_SLUG}"
        assert address.url == f"https://nonogram.adverax.io/b/{GROUPED_SLUG}"


class TestBookLanding_ADamagedRowCannotShiftNumbers:
    def damaged(self):
        rows = [dict(r) for r in GROUPED_ROWS]
        rows[1]["grid"] = [[True, False], [True]]
        return rows

    def test_the_interior_refuses_such_a_book(self):
        """Premise, measured on the real interior: it does not print around the row."""
        generator = BookPDFGenerator(corpus_book())
        with pytest.raises(RuntimeError, match="g1"):
            generator.interior_stream(self.damaged())

    def test_the_bundle_writes_no_book_file_and_names_the_row(self, tmp_path):
        report, root = exported(self.damaged(), tmp_path)
        assert book_files(root) == []
        assert report.book_count == 0
        assert [pid for pid, _ in report.skipped] == ["g1"]
        # The readable puzzles stay published.
        assert report.puzzle_count == len(GROUPED_ROWS) - 1

    def test_the_refusal_is_reported_per_book(self, tmp_path):
        report, _ = exported(self.damaged(), tmp_path)
        assert [(title, pid) for title, pid, _ in report.refused_books] == [("Winter", "g1")]
        assert "ragged" in report.refused_books[0][2]

    def test_a_deleted_row_is_skipped_and_the_book_is_addressed_over_the_survivors(
        self, tmp_path
    ):
        """The panel's loader prints the survivors, so the book keeps a landing."""
        rows = [r for r in GROUPED_ROWS if r["id"] != "g1"]
        report, root = exported(rows, tmp_path, stored_order=[r["id"] for r in GROUPED_ROWS])
        survivors = player_bundle.landing_address(rows, DOMAIN)
        assert [f.stem for f in book_files(root)] == [survivors.slug]
        assert dict(report.skipped)["g1"] == "no stored puzzle with this id"
        assert report.refused_books == ()

    def test_the_bundle_serves_the_slug_the_real_interior_prints_after_a_deletion(
        self, panel, tmp_path, monkeypatch  # noqa: F811
    ):
        """B-1, through the panel's own loader (`_book_puzzles`) and the real interior."""
        book_id = panel.books.create_book("Winter", "a book", "christmas", "adults")
        ids = [add_grid(panel, GRIDS[name], name) for name in ("angel", "star", "box")]
        panel.books.add_puzzles_to_book(book_id, ids)
        assert panel.store.delete_puzzle(ids[1])
        book = panel.books.get_book(book_id)
        assert ids[1] in book.puzzle_ids  # premise: the book still names the deleted id

        printed = []
        real = BookPDFGenerator.section_plan

        def spy(self, puzzles):
            plan = real(self, puzzles)
            printed.append(list(plan.printed))
            return plan

        monkeypatch.setattr(BookPDFGenerator, "section_plan", spy)
        response = panel.client.post(f"/book/{book_id}/generate-pdf")
        assert response.status_code == 200, response.get_data(as_text=True)[:300]
        assert printed and [r["id"] for r in printed[-1]] == [ids[0], ids[2]]

        class Books:
            def get_all_books(self):
                return [
                    SimpleNamespace(
                        status=BookStatus.READY_FOR_PDF.value,
                        puzzle_ids=list(book.puzzle_ids),
                        metadata=book.metadata,
                    )
                ]

        player_bundle.export_bundle(Books(), panel.store, tmp_path / "bundle")
        expected = slug_by_hand(key_by_hand(r["grid"]) for r in printed[-1])
        assert [f.stem for f in book_files(tmp_path / "bundle")] == [expected]
        assert player_bundle.landing_address(printed[-1], DOMAIN).slug == expected

    def test_the_address_refuses_rather_than_renumber(self):
        with pytest.raises(ValueError):
            player_bundle.landing_address(self.damaged(), DOMAIN)

    def test_a_book_with_no_puzzles_has_no_address(self):
        with pytest.raises(ValueError):
            player_bundle.landing_address([], DOMAIN)


class TestBookLanding_APuzzleTheInteriorDropsTakesNoNumber:
    """F-2: the bundle's notion of 'printed' is the interior's own filter."""

    def malformed(self):
        rows = [dict(r) for r in GROUPED_ROWS]
        rows[1]["clues_rows"] = [5, 5]  # a valid grid, clues the interior cannot read
        return rows

    def test_the_interior_drops_the_row(self):
        plan = BookPDFGenerator(corpus_book()).section_plan(self.malformed())
        assert plan.ids == ["g0", "g2", "g3"]  # premise, on the real interior

    def test_the_bundle_numbers_exactly_what_the_interior_numbers(self, tmp_path):
        rows = self.malformed()
        plan = BookPDFGenerator(corpus_book()).section_plan(rows)
        expected = [key_by_hand(r["grid"]) for r in plan.printed]
        _, root = exported(rows, tmp_path)
        (book_file,) = book_files(root)
        assert json.loads(book_file.read_text())["puzzle_keys"] == expected
        assert book_file.stem == slug_by_hand(expected)
        assert player_bundle.landing_address(rows, DOMAIN).slug == book_file.stem
