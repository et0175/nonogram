"""CARD-329's declaration-lifting session probe: PageKind.PUZZLE goes vector.

Not a test and not under ``tests/`` (G-7). This card's own probe -- CARD-331's
``scratchpad/card331/probe_puzzle_vector.py`` is the pattern, deliberately not
the import (a sibling card's scratchpad is not a dependency).

Loaded with ``-p`` so the declaration is lifted **before any test module
imports**, which is the state CARD-322's conversion will actually produce. The
lift is the whole mechanism: :func:`nonogram.admin.book_pdf_generator.page_medium`
returns VECTOR for every kind absent from ``_RASTER_DECLARATIONS``, so
removing PUZZLE's entry makes every puzzle page in the session operators
instead of a DCTDecode bitmap. ``src/`` is read, never edited (G-6) -- the
mutation is to the imported module object for one process, and the file on
disk is untouched.

Why PUZZLE alone and not the other three interior kinds: the puzzle page's
writer imports no generator, so ``book_pdf_generator`` composes it directly
and the lift needs no ``InteriorPageWriters``. The guide/TOC/answer kinds need
the assembly point (``book_interior_vector.interior_generator``), which a
plain ``BookPDFGenerator(book)`` does not carry -- lifting them too would
measure a REFUSAL, not a converted page, and that is a different experiment.
"""

from nonogram.admin import book_pdf_generator as generator

LIFTED = generator.PageKind.PUZZLE


def pytest_configure(config):
    removed = generator._RASTER_DECLARATIONS.pop(LIFTED, None)
    assert removed is not None, (
        "the probe found no PUZZLE declaration to lift: either the tree is "
        "already converted (CARD-322 has landed) or the registry moved"
    )
    assert generator.page_medium(LIFTED) is generator.PageMedium.VECTOR, (
        "the lift did not change the medium: page_medium no longer reads "
        "_RASTER_DECLARATIONS and this probe measures nothing"
    )
