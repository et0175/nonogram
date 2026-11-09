"""The book layout as it stood before the owner's 2026-11-09 polish, for ink readers.

Two owner decisions of 2026-11-09 changed what a book page *inks* without
moving any geometry:

* **No frame around the clues** (``book_page_spec.BOOK_PUZZLE_FRAME``). The
  frame is ink, not geometry (``PageSpec.framed``): a framed and an unframed
  layout differ in that field alone. Many readers in this tree
  (``tests/helpers/page_ink.py``'s ``frame_centre_of``, the frame-rule
  probes) measure a drawing's boundaries *off its frame rule*; on an unframed
  page there is no rule to read, so those tests switch the frame back on to
  measure geometry that the frame never decided.
* **Every answer packs** (``book_answer_key.PACKED_MAX_WIDTH/HEIGHT`` =
  ``limits.MAX_SIZE``): up to 30 x 30 now goes four to a page, so a book can
  no longer hold an answer too large to pack. CARD-198's full-page answer
  path is still code; the tests that exercise it put back the old 20 x 25
  threshold, so an answer of :data:`LEGACY_PACKED_MAX_WIDTH` ``+ 1`` cells
  still takes it.
* **Level dividers in the Solutions opener's style**
  (``book_pdf_generator.LEVEL_DIVIDER_OPENER``). Readers that name a divider
  by its one centred word (AC-254's page) switch the old page back on.

Use :func:`legacy_book_layout` as a context manager, or
:func:`module_fixture` to get an autouse fixture for a whole test module.
The shipped defaults themselves are pinned by
``tests/test_book_layout_polish.py``.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pytest

#: CARD-202's threshold before 2026-11-09: an answer this size or smaller packed.
LEGACY_PACKED_MAX_WIDTH = 20
LEGACY_PACKED_MAX_HEIGHT = 25


@contextmanager
def legacy_book_layout(
    *, frame: bool = True, packing: bool = True, dividers: bool = True
) -> Iterator[None]:
    """Put back the frame, the 20 x 25 packing threshold and/or the one-word dividers."""
    from nonogram.admin import book_answer_key, book_page_spec, book_pdf_generator

    with pytest.MonkeyPatch.context() as patch:
        if dividers:
            patch.setattr(book_pdf_generator, "LEVEL_DIVIDER_OPENER", False)
        if frame:
            patch.setattr(book_page_spec, "BOOK_PUZZLE_FRAME", True)
        if packing:
            patch.setattr(book_answer_key, "PACKED_MAX_WIDTH", LEGACY_PACKED_MAX_WIDTH)
            patch.setattr(book_answer_key, "PACKED_MAX_HEIGHT", LEGACY_PACKED_MAX_HEIGHT)
        yield


def module_fixture(*, frame: bool = True, packing: bool = True, dividers: bool = True):
    """An autouse, module-scoped fixture applying :func:`legacy_book_layout`.

    Bind it at module level (``_legacy = module_fixture(frame=True)``) so it
    is set up before any module- or class-scoped fixture that renders a book.
    """

    @pytest.fixture(scope="module", autouse=True)
    def _legacy_book_layout() -> Iterator[None]:
        with legacy_book_layout(frame=frame, packing=packing, dividers=dividers):
            yield

    return _legacy_book_layout
