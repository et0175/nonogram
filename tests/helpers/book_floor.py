"""NFR-008's printed-cell floor, as a test-side literal (CARD-535).

The layout and PDF geometry tests work out their expectations without asking
the code under test: ``tests/test_layout_page_spec.py`` and
``tests/property/test_book_layout.py`` never import ``nonogram.admin``, and
``tests/property/test_book_pdf_geometry.py`` never imports ``book_page_spec``.
The floor in force lives in ``nonogram.admin.book_page_spec.FLOOR_MM``, so
those tests read this literal instead. It is held equal to ``FLOOR_MM`` by
``tests/property/test_book_membership_floor.py``, a test that may import it,
so a change to the floor fails there rather than leaving this copy behind.

This module imports nothing.
"""

#: NFR-008's book floor in millimetres (lowered from 4.8 mm on 2026-10-17).
BOOK_FLOOR_MM = 4.75
