"""CARD-331 premise probe (B): the puzzle page goes vector AND the instrument
is made "medium-tolerant" the obvious way -- non-Image pages are skipped.

This is the shape a converting card is tempted to write when the only symptom
is ``'ContentStream' object has no attribute 'convert'``. It is the scenario
AC-4 is really about: the raster accounting's source goes dead and the
accounting has nothing left to disagree with.

Not a test and not under ``tests/`` (G-6).
"""

from PIL import Image

from nonogram.admin import book_pdf_generator as gen


def pytest_configure(config):
    gen._RASTER_DECLARATIONS.pop(gen.PageKind.PUZZLE, None)
    original = gen.BookPDFGenerator.interior_pages

    def only_bitmaps(self, puzzles):
        return [p for p in original(self, puzzles) if isinstance(p, Image.Image)]

    gen.BookPDFGenerator.interior_pages = only_bitmaps
