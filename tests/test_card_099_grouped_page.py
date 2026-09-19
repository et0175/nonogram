"""CARD-099 — the generated-puzzles page counts honestly and groups by picture.

    AC-1  one picture with two sizes reads as two puzzles from ONE picture
    AC-2  three pictures at one size each still reads three and three
    AC-3  the shortfall says what it can support, and no more
    AC-4  a picture's puzzles appear together, in extent order
    AC-5  a single-size batch is unchanged apart from the count   <- pinned FIRST

Read AC-5 first, then AC-1. AC-1 is a defect: CARD-069 changed the batch's
``total_count`` from the number of pictures to the number of planned puzzles,
and the page's summary line still calls that number "pictures", so one picture
with two sizes rendered "2 puzzles from 2 pictures". The pins here were taken
against that wording, so the sentence cannot quietly regress to it.

The grouping (AC-4) is option (a) of the three the card offered, at the owner's
pick: the cards are untouched, and a heading per picture precedes them.

Note what the page's incoming order is, because it is the reason grouping is
not free: ``PuzzleFilter``'s default sort is ``batch_id,-size,quality``, so
within one batch the puzzles arrive widest-first, interleaving the pictures.
The group order is therefore computed here, not inherited.
"""

from __future__ import annotations

import pytest

from nonogram.admin import image_manager as image_manager_module
from nonogram.admin.app import group_by_picture


def _grid(width: int, height: int):
    """A solid rectangle — a real grid the store will accept."""
    return [[True] * width for _ in range(height)]


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


def _batch(app, *, planned: int, source: str = "images"):
    """A batch whose ``total_count`` is the planned *puzzle* count (CARD-069)."""
    return app.batch_generator.create_batch(
        count=planned, sizes=[10], theme="image", source=source, quality_filter=0
    )


def _add(app, batch_id, *, source, width, height):
    return app.puzzle_review_service.add_puzzle(
        grid=_grid(width, height),
        clues_rows=[],
        clues_cols=[],
        width=width,
        height=height,
        theme="image",
        difficulty_score=10,
        difficulty_tier="easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=batch_id,
        source_image=source,
    )


def _page(app, batch_id) -> str:
    return app.test_client().get(f"/batch/{batch_id}/generated-puzzles").get_data(
        as_text=True
    )


def _lede(body: str) -> str:
    start = body.index('<p class="lede">') + len('<p class="lede">')
    return body[start : body.index("</p>", start)].strip()


# --------------------------------------------------------------------------
# AC-5 — the single-size batch, pinned first
# --------------------------------------------------------------------------


def test_three_pictures_at_one_size_each_still_reads_three_and_three(admin_app):
    """AC-2/AC-5: the case that was right before this card stays right."""
    batch_id = _batch(admin_app, planned=3)
    for name in ("a.png", "b.png", "c.png"):
        _add(admin_app, batch_id, source=name, width=10, height=10)

    assert _lede(_page(admin_app, batch_id)).startswith("3 puzzles from 3 pictures.")


def test_one_picture_one_size_is_singular_on_both_ends(admin_app):
    batch_id = _batch(admin_app, planned=1)
    _add(admin_app, batch_id, source="only.png", width=10, height=10)

    assert _lede(_page(admin_app, batch_id)).startswith("1 puzzle from 1 picture.")


def test_a_single_size_batch_keeps_a_control_pair_per_puzzle(admin_app):
    """G-3: grouping must not make one control stand for several puzzles."""
    batch_id = _batch(admin_app, planned=3)
    for name in ("a.png", "b.png", "c.png"):
        _add(admin_app, batch_id, source=name, width=10, height=10)

    body = _page(admin_app, batch_id)

    assert body.count('data-action="approve"') == 3
    assert body.count('data-action="reject"') == 3


# --------------------------------------------------------------------------
# AC-1 — the defect
# --------------------------------------------------------------------------


def test_one_picture_with_two_sizes_is_two_puzzles_from_one_picture(admin_app):
    """The measured regression: this rendered "2 puzzles from 2 pictures"."""
    batch_id = _batch(admin_app, planned=2)
    _add(admin_app, batch_id, source="eagle.png", width=10, height=17)
    _add(admin_app, batch_id, source="eagle.png", width=20, height=34)

    lede = _lede(_page(admin_app, batch_id))

    assert lede.startswith("2 puzzles from 1 picture.")
    assert "2 pictures" not in lede


def test_two_pictures_with_two_sizes_each_is_four_puzzles_from_two(admin_app):
    batch_id = _batch(admin_app, planned=4)
    for name in ("eagle.png", "konek.png"):
        _add(admin_app, batch_id, source=name, width=10, height=17)
        _add(admin_app, batch_id, source=name, width=20, height=34)

    assert _lede(_page(admin_app, batch_id)).startswith("4 puzzles from 2 pictures.")


# --------------------------------------------------------------------------
# AC-3 — the shortfall
# --------------------------------------------------------------------------


def test_the_shortfall_is_reported_without_blaming_the_quality_threshold(admin_app):
    """The page cannot tell filtered-out from never-made; it must not claim to.

    ``total_count`` is what the batch planned. A puzzle missing from the store
    was filtered by quality, skipped as too elongated, refused by the store, or
    never started when the clock ran out — and nothing on this page
    distinguishes them.
    """
    batch_id = _batch(admin_app, planned=3)
    _add(admin_app, batch_id, source="a.png", width=10, height=10)
    _add(admin_app, batch_id, source="b.png", width=10, height=10)

    lede = _lede(_page(admin_app, batch_id))

    assert "2 puzzles from 2 pictures" in lede
    assert "1 of the 3 planned was not made" in lede
    assert "quality threshold" not in lede


def test_no_shortfall_clause_when_every_planned_puzzle_was_made(admin_app):
    batch_id = _batch(admin_app, planned=2)
    _add(admin_app, batch_id, source="a.png", width=10, height=10)
    _add(admin_app, batch_id, source="b.png", width=10, height=10)

    assert "not made" not in _lede(_page(admin_app, batch_id))


def test_a_random_batch_claims_no_pictures_at_all(admin_app):
    """Random puzzles carry no ``source_image``; the page must not invent one.

    A random batch generates its own puzzles, so this one is the real thing
    rather than rows written by hand.
    """
    batch_id = _batch(admin_app, planned=10, source="random")

    lede = _lede(_page(admin_app, batch_id))

    assert lede.startswith("10 puzzles.")
    assert "picture" not in lede


# --------------------------------------------------------------------------
# AC-4 — the grouping
# --------------------------------------------------------------------------


def test_a_pictures_puzzles_are_grouped_under_one_heading(admin_app):
    batch_id = _batch(admin_app, planned=3)
    _add(admin_app, batch_id, source="eagle.png", width=10, height=17)
    _add(admin_app, batch_id, source="eagle.png", width=20, height=34)
    _add(admin_app, batch_id, source="konek.png", width=15, height=15)

    body = _page(admin_app, batch_id)

    assert body.count('class="picture-group"') == 2
    assert 'data-source="eagle.png"' in body
    assert 'data-source="konek.png"' in body
    # The heading says how many sizes only where there is more than one.
    assert "2 sizes" in body
    assert "1 size" not in body


def test_groups_hold_their_pictures_puzzles_and_only_those(admin_app):
    batch_id = _batch(admin_app, planned=3)
    _add(admin_app, batch_id, source="eagle.png", width=10, height=17)
    _add(admin_app, batch_id, source="eagle.png", width=20, height=34)
    _add(admin_app, batch_id, source="konek.png", width=15, height=15)

    body = _page(admin_app, batch_id)
    eagle = body[body.index('data-source="eagle.png"') : body.index('data-source="konek.png"')]

    assert eagle.count('class="result-card"') == 2
    assert "10×17" in eagle and "20×34" in eagle
    assert "15×15" not in eagle


def test_the_grouping_overrides_the_widest_first_order_it_is_given(admin_app):
    """The incoming order interleaves the pictures; the page must not.

    ``konek`` is uploaded second but is wider, so the default sort hands the
    page ``konek 30, eagle 20, eagle 10``. Grouped, it is eagle (10 then 20)
    followed by konek.
    """
    batch_id = _batch(admin_app, planned=3)
    _add(admin_app, batch_id, source="eagle.png", width=10, height=17)
    _add(admin_app, batch_id, source="eagle.png", width=20, height=34)
    _add(admin_app, batch_id, source="konek.png", width=30, height=30)

    body = _page(admin_app, batch_id)

    assert body.index('data-source="eagle.png"') < body.index('data-source="konek.png"')
    assert body.index("10×17") < body.index("20×34")


def test_a_random_batch_renders_one_unlabelled_group(admin_app):
    batch_id = _batch(admin_app, planned=10, source="random")

    body = _page(admin_app, batch_id)

    assert 'class="picture-group"' not in body
    assert body.count('class="result-card"') == 10


# --------------------------------------------------------------------------
# The grouping rule itself
# --------------------------------------------------------------------------


def test_group_by_picture_orders_pictures_by_first_made_and_sizes_by_area():
    puzzles = [
        {"source_image": "b.png", "width": 30, "height": 30, "created_at": "2026-09-19T10:00:02"},
        {"source_image": "a.png", "width": 20, "height": 34, "created_at": "2026-09-19T10:00:01"},
        {"source_image": "a.png", "width": 10, "height": 17, "created_at": "2026-09-19T10:00:00"},
    ]

    groups = group_by_picture(puzzles)

    assert [g.source for g in groups] == ["a.png", "b.png"]
    assert [(p["width"], p["height"]) for p in groups[0].puzzles] == [(10, 17), (20, 34)]


def test_group_by_picture_follows_the_upload_order_not_the_alphabet():
    """The two orders are separated deliberately.

    Every other case here happens to upload its pictures in alphabetical
    order, so a rule that sorted by name would pass them all — it did, until
    this test. The page is meant to read in the order the pictures were added
    to the batch.
    """
    puzzles = [
        {"source_image": "zebra.png", "width": 10, "height": 10, "created_at": "2026-09-19T10:00:00"},
        {"source_image": "apple.png", "width": 10, "height": 10, "created_at": "2026-09-19T10:00:01"},
    ]

    assert [g.source for g in group_by_picture(puzzles)] == ["zebra.png", "apple.png"]


def test_the_page_lists_pictures_in_upload_order(admin_app):
    batch_id = _batch(admin_app, planned=2)
    _add(admin_app, batch_id, source="zebra.png", width=10, height=10)
    _add(admin_app, batch_id, source="apple.png", width=10, height=10)

    body = _page(admin_app, batch_id)

    assert body.index('data-source="zebra.png"') < body.index('data-source="apple.png"')


def test_group_by_picture_puts_sourceless_puzzles_in_one_unnamed_group():
    puzzles = [
        {"source_image": None, "width": 10, "height": 10, "created_at": "2026-09-19T10:00:00"},
        {"source_image": None, "width": 20, "height": 20, "created_at": "2026-09-19T10:00:01"},
    ]

    groups = group_by_picture(puzzles)

    assert len(groups) == 1
    assert groups[0].source is None
    assert len(groups[0].puzzles) == 2


def test_group_by_picture_keeps_a_sourceless_puzzle_out_of_a_named_group():
    """A mixed batch is not expected, but it must not silently merge."""
    puzzles = [
        {"source_image": "a.png", "width": 10, "height": 10, "created_at": "2026-09-19T10:00:00"},
        {"source_image": None, "width": 10, "height": 10, "created_at": "2026-09-19T10:00:01"},
    ]

    groups = group_by_picture(puzzles)

    assert [g.source for g in groups] == ["a.png", None]


def test_group_by_picture_is_stable_when_two_puzzles_share_a_timestamp():
    same = "2026-09-19T10:00:00"
    puzzles = [
        {"source_image": "b.png", "width": 10, "height": 10, "created_at": same},
        {"source_image": "a.png", "width": 10, "height": 10, "created_at": same},
    ]

    assert [g.source for g in group_by_picture(puzzles)] == ["a.png", "b.png"]


def test_group_by_picture_tolerates_a_missing_timestamp():
    puzzles = [
        {"source_image": "b.png", "width": 10, "height": 10},
        {"source_image": "a.png", "width": 10, "height": 10, "created_at": "2026-09-19T10:00:00"},
    ]

    groups = group_by_picture(puzzles)

    assert {g.source for g in groups} == {"a.png", "b.png"}
    assert sum(len(g.puzzles) for g in groups) == 2
