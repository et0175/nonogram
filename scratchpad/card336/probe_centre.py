"""CARD-336: candidate frame-centre reading, measured in each medium."""
from __future__ import annotations
import sys
import numpy as np

MODE = sys.argv[1] if len(sys.argv) > 1 else "raster"
if MODE == "vector":
    import probe_five_kinds

    class _Config:
        pass

    probe_five_kinds.pytest_configure(_Config())

from nonogram.admin.book_pdf_generator import BookPDFGenerator  # noqa: E402
from tests.helpers.page_ink import drawing_of, frame_centre_of  # noqa: E402
from tests.helpers.two_up_ink import drawings_of  # noqa: E402
from tests.helpers.pdf_pages import interior_images  # noqa: E402

sys.path.insert(0, "tests")
import test_book_puzzle_frame as m  # noqa: E402


def centre(page, drawing):
    c = frame_centre_of(page, drawing)
    return {"left": c.frame_left, "top": c.frame_top,
            "rules": (c.left_rule_px, c.top_rule_px)}


pages = interior_images(
    BookPDFGenerator(m._book()).interior_pages([
        m._book_puzzle(**m.UPPER_PUZZLE, puzzle_id="one"),
        m._book_puzzle(**m.LOWER_PUZZLE, puzzle_id="two"),
        m._book_puzzle(**m.SINGLE_PUZZLE, puzzle_id="three"),
    ])
)
print(f"=== MEDIUM={MODE} ===")
single = pages[m.SINGLE_PAGE - 1]
d = drawing_of(single)
print("single ink  left/top:", d.left, d.top, "framed", d.framed)
print("single centre:", centre(single, d))

two_up = pages[m.TWO_UP_PAGE - 1]
boxes = m._expected_pair_boxes(m.UPPER_PUZZLE, m.LOWER_PUZZLE)
for i, (d, (left, top, right, bottom)) in enumerate(zip(drawings_of(two_up), boxes)):
    c = centre(two_up, d)
    print(f"two_up[{i}] ink left/top = {d.left}/{d.top}  expected {left:.4f}/{top:.4f}")
    print(f"    centre {c}")
    print(f"    INK residual  left {abs(d.left-left):.4f}  top {abs(d.top-top):.4f}  (bound {m.EDGE_TOLERANCE_PX})")
    print(f"    CTR residual  left {abs(c['left']-left):.4f}  top {abs(c['top']-top):.4f}")
