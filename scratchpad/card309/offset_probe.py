"""Measure the raster/vector placement offset CARD-295 recorded as a constant."""
import sys
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-309/src")
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-309")
from decimal import Decimal
import tests.test_book_puzzle_page_vector as m

gen = m.BookPDFGenerator(m.corpus_book())
row = m.print_order(m.baseline_puzzles())[0]
case = m._case(gen, row, 1, m.A_PUZZLE_PAGE, "probe")
payload = m.BookPDFGenerator._payload(row)
page = gen._blank_page(payload, 1, m.A_PUZZLE_PAGE, gen.cell_sizes([payload]))
drawing = m.page_ink.drawing_of(page)
verticals, horizontals = m._device_rules(case)
heavy = max(w for _p, w in verticals + horizontals)
major_x = sorted(p for p, w in verticals if w == heavy)
major_y = sorted(p for p, w in horizontals if w == heavy)
print("heavy pt:", heavy)
print("stream major x:", major_x[0], major_x[-1])
print("ink grid_left/right:", drawing.grid_left, drawing.grid_right)
print("stream major y:", major_y[0], major_y[-1])
print("ink grid_top/bottom:", drawing.grid_top, drawing.grid_bottom)
offs = {
    "left": Decimal(drawing.grid_left) - major_x[0],
    "right": Decimal(drawing.grid_right) - major_x[-1],
    "top": Decimal(drawing.grid_top) - major_y[0],
    "bottom": Decimal(drawing.grid_bottom) - major_y[-1],
}
print("offsets (device px):", offs)
print("in mm:", {k: float(v) / (300/25.4) for k, v in offs.items()})
print("ink left/top:", drawing.left, drawing.top, "framed:", drawing.framed,
      "columns/rows:", drawing.columns, drawing.rows, "cell:", drawing.cell)
