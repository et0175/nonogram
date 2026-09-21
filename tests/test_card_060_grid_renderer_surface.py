"""CARD-060 — the two dead helpers in grid_renderer are gone, and stay gone.

AC-2 was written as "a fresh grep returns no matches". This is that grep, run
by the suite instead of by hand, so the answer keeps being checked rather than
being true on the day someone looked.

`grid_to_svg` is deliberately asserted present in the same test: the risk in a
deletion card is not only that dead code survives it but that live code goes
with it, and this module's one real function serves every
`/api/puzzle/<id>/grid` request.
"""

from __future__ import annotations

from pathlib import Path

from nonogram.admin import grid_renderer


REMOVED = ("grid_to_svg_bytes", "get_svg_filename")


def test_the_dead_helpers_are_gone():
    for name in REMOVED:
        assert not hasattr(grid_renderer, name), f"{name} is back"


def test_the_live_renderer_is_untouched():
    """G-1: the function this module exists for."""
    svg = grid_renderer.grid_to_svg([[True, False], [False, True]], cell_size=10)

    assert svg.startswith("<svg xmlns=")
    assert svg.count("<rect") == 5  # one background, four cells


def test_nothing_in_the_source_tree_names_them():
    """The grep itself: a caller would fail on import, a mention would not."""
    source = Path(grid_renderer.__file__).resolve().parents[2]
    offenders = [
        path
        for path in source.rglob("*.py")
        if any(name in path.read_text(encoding="utf-8") for name in REMOVED)
    ]

    assert offenders == []
