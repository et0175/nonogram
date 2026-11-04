"""CARD-336: what the ink around a framed drawing's left/top edge actually
looks like, in each medium. Not a test, not under tests/ (G-7)."""
from __future__ import annotations

import sys
import numpy as np

MODE = sys.argv[1] if len(sys.argv) > 1 else "raster"
if MODE == "vector":
    import probe_five_kinds

    class _Config:
        pass

    probe_five_kinds.pytest_configure(_Config())

from PIL import Image  # noqa: E402
from nonogram.admin.book_pdf_generator import BookPDFGenerator  # noqa: E402
from tests.helpers.page_ink import _dark, _groups, drawing_of  # noqa: E402
from tests.helpers.two_up_ink import drawings_of  # noqa: E402
from tests.helpers.pdf_pages import interior_images  # noqa: E402

sys.path.insert(0, "tests")
import test_book_puzzle_frame as m  # noqa: E402


def runs_at(dark, line):
    return _groups(np.flatnonzero(line))


def report(tag, page, drawing):
    dark = _dark(page)
    row = (drawing.top + drawing.grid_bottom) // 2
    col = (drawing.left + drawing.grid_right) // 2
    print(f"--- {tag}: left={drawing.left} top={drawing.top} "
          f"grid=({drawing.grid_left},{drawing.grid_top},{drawing.grid_right},{drawing.grid_bottom}) "
          f"framed={drawing.framed} cell={drawing.cell:.3f}")
    rs = runs_at(dark, dark[row])
    near = [r for r in rs if r[0] - 12 <= drawing.left <= r[-1] + 12][:4]
    print(f"    row {row}: first 3 runs {[(r[0], r[-1]) for r in rs[:3]]}  near-left {[(r[0], r[-1]) for r in near]}")
    cs = runs_at(dark, dark[:, col])
    nearc = [r for r in cs if r[0] - 12 <= drawing.top <= r[-1] + 12][:4]
    print(f"    col {col}: first 3 runs {[(r[0], r[-1]) for r in cs[:3]]}  near-top {[(r[0], r[-1]) for r in nearc]}")


pages = interior_images(
    BookPDFGenerator(m._book()).interior_pages([
        m._book_puzzle(**m.UPPER_PUZZLE, puzzle_id="one"),
        m._book_puzzle(**m.LOWER_PUZZLE, puzzle_id="two"),
        m._book_puzzle(**m.SINGLE_PUZZLE, puzzle_id="three"),
    ])
)
print(f"MEDIUM={MODE} pages={len(pages)}")
single = pages[m.SINGLE_PAGE - 1]
report("single", single, drawing_of(single))
two_up = pages[m.TWO_UP_PAGE - 1]
for i, d in enumerate(drawings_of(two_up)):
    report(f"two_up[{i}]", two_up, d)

# the failing cell's own comparison
boxes = m._expected_pair_boxes(m.UPPER_PUZZLE, m.LOWER_PUZZLE)
for d, (left, top, right, bottom) in zip(drawings_of(two_up), boxes):
    print(f"    CELL: |drawing.left - left| = {abs(d.left - left):.4f}  "
          f"|drawing.top - top| = {abs(d.top - top):.4f}  (bound {m.EDGE_TOLERANCE_PX})")
