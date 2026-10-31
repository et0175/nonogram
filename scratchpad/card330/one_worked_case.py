"""Print ONE corpus case's three numbers in millimetres, derived.

CARD-330 cycle 1's F-103 asks the card's own table to carry the millimetre
figures rather than only the relation. This prints them from the same helpers
the tests use, so the card's table is derived and not retyped.

    python scratchpad/card330/one_worked_case.py [index]
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from tests import test_book_pdf as t  # noqa: E402

index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
with tempfile.TemporaryDirectory() as tmp:
    reading = t._edge_case(index, pathlib.Path(tmp) / str(index))

print("label:", reading.label, "| bound:", reading.bound, "| framed:", reading.framed)
header = f"{'edge':14} {'specified':>11} {'stream':>11} {'raster ink':>11} {'vector ink':>11}"
print(header)
for edge in t._GRID_EDGES + t._DRAWING_EDGES:
    stream = reading.vector_stream.get(edge)
    print(
        f"{edge:14} {reading.specified[edge]:11.3f} "
        f"{'' if stream is None else f'{stream:11.3f}'} "
        f"{reading.raster_ink[edge]:11.3f} {reading.vector_ink[edge]:11.3f}"
    )
print()
print(f"1 device px at 300 DPI = {1 / t.PX_PER_MM:.6f} mm")
for edge in t._GRID_EDGES:
    d = (reading.vector_stream[edge] - reading.specified[edge]) * t.PX_PER_MM
    print(f"  {edge:14} stream - specified = {d:+.4f} px")
