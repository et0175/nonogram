"""CARD-331 premise probe: make PageKind.PUZZLE vector for a whole session.

Not a test and not under ``tests/`` (G-6). Loaded with ``-p`` so the
declaration is lifted before any test module imports, which is the state
CARD-322's conversion will actually produce.
"""

from nonogram.admin import book_pdf_generator as gen


def pytest_configure(config):
    gen._RASTER_DECLARATIONS.pop(gen.PageKind.PUZZLE, None)
