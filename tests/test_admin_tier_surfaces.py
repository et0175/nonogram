"""The admin surfaces that read a tier back, across all four members.

CARD-076 review, finding F-002. ADR-0025 added a fourth tier, and the card's
objective 4 is that every ``Tier`` consumer handles it. Four consumers were
missed, and all four shared one older defect that hid the gap: they compared a
row's ``difficulty_tier`` against a *display label* (``"Easy"``), while a row
written by the generation pipeline stores the enum *value* (``"easy"``) —
``orchestrator.Puzzle.difficulty_tier`` is a ``Tier``, and a ``StrEnum``'s
``str`` is its value. So the counts read 0 for every generated book and the
filter matched none of its rows, which looks like an empty book rather than
like a broken reader.

These tests are written over **pipeline spelling**, because that is the case
that was broken and the case that was not covered: ``test_book_scaffolding.py``
already had a ``test_difficulty_breakdown``, but it recomputed the production
expression inside the test body, so it asserted the formula against itself and
would have passed no matter what production did.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

import nonogram.admin

from nonogram.admin.book_pdf_generator import BookPDFGenerator, tier_breakdown
from nonogram.admin.puzzle_review import PuzzleFilter, PuzzleReviewService
from nonogram.difficulty import Tier


def _rows(*tiers: str | None) -> list[dict[str, object]]:
    return [{"id": f"p{i}", "difficulty_tier": t} for i, t in enumerate(tiers)]


# --------------------------------------------------------------------------
# The breakdown both the finalize screen and the printed guide page read
# --------------------------------------------------------------------------


def test_the_breakdown_counts_rows_written_by_the_pipeline() -> None:
    """The defect exactly: lowercase rows used to count as nothing."""
    counts = tier_breakdown(_rows("easy", "easy", "medium", "hard"))

    assert counts[Tier.EASY] == 2
    assert counts[Tier.MEDIUM] == 1
    assert counts[Tier.HARD] == 1


def test_the_breakdown_counts_both_spellings_as_one_tier() -> None:
    """A book may hold rows from before and after the pipeline wrote them."""
    counts = tier_breakdown(_rows("easy", "Easy", "HARD", "hard"))

    assert counts[Tier.EASY] == 2
    assert counts[Tier.HARD] == 2


def test_the_breakdown_counts_the_fourth_tier() -> None:
    """ADR-0025's Guess is a tier of the book, not a row that vanishes."""
    counts = tier_breakdown(_rows("guess", "Guess", "easy"))

    assert counts[Tier.GUESS] == 2
    assert counts[Tier.EASY] == 1


def test_unreadable_tiers_are_counted_in_no_tier_rather_than_guessed_at() -> None:
    """The totals must never exceed the puzzle count.

    A missing or junk tier is not evidence for any tier, so it is counted in
    none — the alternative, folding it into Easy or Hard, would put a puzzle
    nobody graded into a book that claims a grade for it.
    """
    rows = _rows("easy", None, "", "extreme", "guess")
    counts = tier_breakdown(rows)

    assert sum(counts.values()) == 2
    assert counts[Tier.EASY] == 1
    assert counts[Tier.GUESS] == 1


def test_every_tier_reads_zero_rather_than_missing_on_an_empty_book() -> None:
    """Indexable without a ``get`` — which is why it returns a Counter."""
    counts = tier_breakdown([])

    assert [counts[tier] for tier in Tier] == [0, 0, 0, 0]


# --------------------------------------------------------------------------
# The printed guide page
# --------------------------------------------------------------------------


def test_the_guide_page_renders_with_a_guess_count() -> None:
    """The fourth count is a real parameter, not a dict the template ignores."""
    guide = BookPDFGenerator().create_guide_page(
        puzzle_count=10, easy_count=3, medium_count=4, hard_count=2, guess_count=1
    )

    assert guide is not None
    assert guide.mode == "RGB"


def test_the_guide_page_still_takes_three_counts() -> None:
    """``guess_count`` defaults, so every existing caller keeps working.

    A book with no Guess puzzles omits the line entirely, so a book of
    line-solvable puzzles prints exactly the guide it printed before the tier
    existed.
    """
    guide = BookPDFGenerator().create_guide_page(
        puzzle_count=10, easy_count=3, medium_count=4, hard_count=3
    )

    assert guide is not None


# --------------------------------------------------------------------------
# The puzzle-list difficulty filter
# --------------------------------------------------------------------------


def _service_holding(*tiers: str | None) -> PuzzleReviewService:
    """An in-memory service (no session factory) holding one row per tier given.

    ``filter_puzzles`` takes the legacy in-memory branch when there is no
    session factory, which is the branch these tests need: the defect was the
    comparison, and the comparison is reachable without a database.
    """
    service = PuzzleReviewService()
    for index, tier in enumerate(tiers):
        service.puzzles[f"p{index}"] = {
            "id": f"p{index}",
            "puzzle_name": f"P{index}",
            "width": 10,
            "height": 10,
            "difficulty_tier": tier,
            "difficulty_score": 33,
            "quality_score": 50,
            "status": "approved",
            "created_at": datetime(2026, 9, 13, tzinfo=timezone.utc),
        }
    return service


def _ids(response: object) -> set[str]:
    return {puzzle["id"] for puzzle in response.puzzles}


@pytest.mark.parametrize("requested", ["easy", "Easy", "EASY", "  easy  "])
def test_the_filter_selects_pipeline_rows_whatever_the_form_submitted(
    requested: str,
) -> None:
    """The form submits a label; a pipeline row holds a value. Both must match.

    This is the defect end to end: before the fix, ``difficulty=Easy`` — which
    is exactly what the select element submits — returned an empty list on a
    page full of generated easy puzzles.
    """
    service = _service_holding("easy", "Easy", "hard", "medium")

    selected = service.filter_puzzles(PuzzleFilter(difficulty=requested))

    assert _ids(selected) == {"p0", "p1"}


def test_the_filter_selects_the_fourth_tier() -> None:
    """``guess`` is offered by the form, so it has to select its rows."""
    service = _service_holding("guess", "Guess", "hard")

    selected = service.filter_puzzles(PuzzleFilter(difficulty="Guess"))

    assert _ids(selected) == {"p0", "p1"}


def test_a_query_string_that_names_no_tier_does_not_widen_the_filter() -> None:
    """Junk must not silently return the whole table.

    The tolerant branch fires only when the requested value actually names a
    tier; anything else keeps the exact-string comparison it always had. A
    filter that matched everything on a typo would be a worse failure than the
    one being fixed, because it would look like it worked.
    """
    service = _service_holding("easy", "hard", "guess")

    selected = service.filter_puzzles(PuzzleFilter(difficulty="extreme"))

    assert _ids(selected) == set()


def test_a_row_with_no_tier_is_selected_by_no_tier_filter() -> None:
    """An ungraded row belongs to no band, so no band's filter may claim it."""
    service = _service_holding(None, "easy")

    for requested in ("easy", "medium", "hard", "guess"):
        selected = service.filter_puzzles(PuzzleFilter(difficulty=requested))
        assert "p0" not in _ids(selected), f"{requested} claimed an ungraded row"


# --------------------------------------------------------------------------
# The templates — one rendering of a tier, guarded structurally
# (CARD-076 review cycle 2: the cycle-1 fix corrected one badge and one option
#  list, and three more badges and a second option list survived it)
# --------------------------------------------------------------------------

_TEMPLATES = Path(nonogram.admin.__file__).parent / "templates"


def _macro(name: str):
    """``_tier.html``'s macros, loaded straight off the templates directory."""
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES)))
    return getattr(env.get_template("_tier.html").module, name)


def test_no_template_writes_its_own_tier_badge_or_option_list() -> None:
    """The structural guard, and the reason this finding recurred twice.

    Five copies of the badge expression and two of the option list had drifted
    into the same two defects at once — comparing against a display label that
    no pipeline-written row carries, and having no branch for ADR-0025's fourth
    tier. Cycle 1 fixed one of each and three badges plus an option list
    survived, because the fix was per-instance. This test makes the class of
    defect unrepeatable: a new template that hand-writes either fails here.
    """
    offences = [
        f"{path.name}: {line_number}"
        for path in sorted(_TEMPLATES.glob("*.html"))
        if path.name != "_tier.html"
        for line_number, line in enumerate(path.read_text().splitlines(), 1)
        if "difficulty_tier ==" in line or 'value="Easy"' in line
    ]

    assert offences == [], (
        "these templates render a tier themselves instead of importing "
        f"_tier.html's macro: {offences}"
    )


@pytest.mark.parametrize(
    ("stored", "colour"),
    [
        ("easy", "#27ae60"),
        ("Easy", "#27ae60"),
        ("medium", "#f39c12"),
        ("hard", "#e74c3c"),
        ("guess", "#8e44ad"),
        ("Guess", "#8e44ad"),
    ],
)
def test_the_badge_gives_every_tier_its_own_colour_in_either_spelling(
    stored: str, colour: str
) -> None:
    """Guess is not "a harder Hard" — it is the tier that is not a score band.

    Before this card every one of these rendered red, because the comparison
    matched no pipeline-written row and the ``else`` branch was Hard's colour.
    """
    rendered = str(_macro("badge")(stored))

    assert colour in rendered
    assert stored in rendered


@pytest.mark.parametrize("stored", [None, "", "extreme"])
def test_an_ungraded_row_is_grey_rather_than_borrowing_a_tier_colour(
    stored: object,
) -> None:
    """An ungraded row used to render in Hard's red, which reads as a grade."""
    rendered = str(_macro("badge")(stored))

    assert "#95a5a6" in rendered


def test_the_filter_offers_all_four_tiers() -> None:
    """An unofferable member is an unreachable one (ADR-0025's Negative)."""
    options = str(_macro("options")("guess"))

    assert options.count("<option") == len(Tier)
    for tier in Tier:
        assert f'value="{tier.label}"' in options
    assert 'value="Guess" selected' in options


# --------------------------------------------------------------------------
# The other PDF generator (CARD-077 review cycle 1, F-007)
# --------------------------------------------------------------------------
#
# There are two book PDF paths and they are not the same module:
# ``book_pdf_generator.py`` builds the guide page and counts tiers through
# ``tier_breakdown``, while ``pdf_generator.py`` renders the table of contents
# and the per-puzzle header. CARD-077 normalises every stored row to the enum
# value (``easy``), so the second path — which printed the column verbatim —
# started printing lowercase into a book the owner sells. These pin it.


@pytest.mark.parametrize(
    ("stored", "printed"),
    [
        pytest.param("easy", "Easy", id="pipeline-spelling"),
        pytest.param("medium", "Medium", id="pipeline-spelling-medium"),
        pytest.param("hard", "Hard", id="pipeline-spelling-hard"),
        pytest.param("guess", "Guess", id="the-fourth-tier"),
        pytest.param("Easy", "Easy", id="legacy-label-unchanged"),
        pytest.param("Hard", "Hard", id="legacy-label-unchanged-hard"),
    ],
)
def test_the_book_pdf_prints_a_tier_in_its_display_spelling(
    stored: str, printed: str
) -> None:
    from nonogram.admin.pdf_generator import get_pdf_generator

    assert get_pdf_generator()._tier_label({"difficulty_tier": stored}) == printed


@pytest.mark.parametrize(
    ("row", "printed"),
    [
        pytest.param({}, "N/A", id="no-tier-column"),
        pytest.param({"difficulty_tier": None}, "N/A", id="null-tier"),
        pytest.param({"difficulty_tier": ""}, "N/A", id="empty-tier"),
        pytest.param({"difficulty_tier": "extreme"}, "extreme", id="not-a-tier-at-all"),
    ],
)
def test_a_row_the_pdf_cannot_resolve_is_printed_not_invented(
    row: dict, printed: str
) -> None:
    """A spelling naming no tier is printed as it stands. A printed book is the
    wrong place to silently drop what the row actually says."""
    from nonogram.admin.pdf_generator import get_pdf_generator

    assert get_pdf_generator()._tier_label(row) == printed


@pytest.mark.parametrize("stored", ["easy", "guess", "Medium"])
def test_the_rendered_toc_and_page_header_carry_the_display_spelling(
    stored: str,
) -> None:
    """Through the rendered flowables, not through the helper.

    Asserting on ``_tier_label`` alone would leave the actual defect
    reachable: the helper could be correct while a call site still
    interpolated the column verbatim, which is exactly the shape the bug had.
    These two are the only places the tier reaches a page.
    """
    from nonogram.admin.pdf_generator import get_pdf_generator

    generator = get_pdf_generator()
    row = {
        "difficulty_tier": stored,
        "width": 10,
        "height": 10,
        "quality_score": 90,
        "grid": [[True]],
    }
    label = Tier(stored.lower()).label

    toc = " ".join(
        item.text for item in generator._create_table_of_contents({}, [row])
        if hasattr(item, "text")
    )
    page = " ".join(
        item.text for item in generator._create_puzzle_page(1, 1, row)
        if hasattr(item, "text")
    )

    for rendered, where in ((toc, "table of contents"), (page, "puzzle header")):
        assert f"Difficulty: {label}" in rendered or f"Difficulty: <b>{label}</b>" in rendered, (
            f"the {where} did not print {label!r}: {rendered!r}"
        )
        if stored != label:
            assert stored not in rendered, (
                f"the {where} still carries the stored spelling {stored!r}"
            )


def test_both_pdf_paths_agree_on_how_a_tier_is_spelled() -> None:
    """The defect was that one of the two normalised and the other did not.

    Asserted as agreement between them rather than against a literal, so the
    two cannot drift apart again without this failing.
    """
    from nonogram.admin.pdf_generator import get_pdf_generator

    generator = get_pdf_generator()
    for tier in Tier:
        assert generator._tier_label({"difficulty_tier": tier.value}) == tier.label
        assert generator._tier_label({"difficulty_tier": tier.label}) == tier.label
