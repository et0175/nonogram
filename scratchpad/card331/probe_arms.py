"""CARD-331 measurement probe: both arms, on real pages, before any test.

Not a test and not under ``tests/`` (G-6). Every figure the round quotes is
printed here.
"""
import math
import sys

sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-331/src")
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-331")

from PIL import Image, ImageDraw

from nonogram.admin import book_pdf_generator as gen
from nonogram.admin.book_pdf_generator import BookPDFGenerator, print_order
from nonogram.admin.book_plan import TIERS
from nonogram.admin.book_vector import ContentStream
from nonogram.export.layout import compute_layout, difficulty_dots, header_band
from tests.helpers.book_corpus import baseline_puzzles, corpus_book
from tests.helpers.round_ink import round_marks, round_stream_marks, stream_marks

DPI = 300
PT_PER_PX = 72.0 / DPI

generator = BookPDFGenerator(corpus_book())
rows = print_order(baseline_puzzles())
payloads = [BookPDFGenerator._payload(row) for row in rows]
plans = list(generator.puzzle_pages(payloads))
streams = list(generator.vector_puzzle_pages(payloads))
print(f"puzzle-page plans: {len(plans)}   vector streams: {len(streams)}")

for index, stream in enumerate(streams):
    marks = stream_marks("\n".join(stream.operators))
    rounds = round_stream_marks("\n".join(stream.operators))
    print(f"  page {index}: {len(stream.operators)} operators, "
          f"{len(marks)} painted subpaths, {len(rounds)} round")
    shaped = [m for m in marks if not m.is_degenerate]
    print(f"      {len(marks) - len(shaped)} degenerate (a rule), {len(shaped)} shaped")
    worst = min(
        shaped, key=lambda m: max(abs(m.aspect - 1.0) / 0.2, abs(m.fill - 1.0) / 0.12)
    )
    worst = (max(abs(worst.aspect - 1.0) / 0.2, abs(worst.fill - 1.0) / 0.12), worst)
    print(f"      closest to round: {worst[0]:.4f} tolerances away, "
          f"{worst[1].width:.2f}x{worst[1].height:.2f} pt, paint {worst[1].paint!r}, "
          f"aspect {worst[1].aspect:.4f} fill {worst[1].fill:.4f}")

# --- the declared vector dots: write them into a real page and read them back
PLANTED_TIER = TIERS[1]
sizes = generator.cell_sizes(payloads)
print("plans:", [(e.page_number, e.numbers, e.pair is not None) for e in plans])
entry = next(e for e in plans if e.pair is None)
payload = payloads[entry.numbers[0] - 1]
spec = generator._puzzle_page_spec(entry.page_number, sizes.get(generator._grid_size(payload)))
layout = compute_layout(payload.row_clues, payload.column_clues, spec)
stream = generator.vector_puzzle_page(payload, entry.numbers[0], entry.page_number, sizes)
print(f"\nmedia box {stream.media_box}, layout {layout.width}x{layout.height} px "
      f"-> {layout.width * PT_PER_PX:.3f}x{layout.height * PT_PER_PX:.3f} pt")

band = header_band(layout)
placement = layout.page
room = placement.usable_right - placement.usable_left
left = band.center_x - room // 2 + 4
top = band.center_y - band.height // 2
box = (left, top, left + min(2 * band.height, room // 4), top + band.height - 1)
dots = difficulty_dots(*box, filled=TIERS.index(PLANTED_TIER) + 1, total=len(TIERS))
print(f"band box {box}, dots {dots.dots}, stroke {dots.stroke}")

before = len(stream_marks("\n".join(stream.operators)))
for i, dot in enumerate(dots.dots):
    l, t, r, b = dot
    stream.round_mark((l + r) / 2.0, (t + b) / 2.0, (r - l) / 2.0,
                      paint="fill" if dots.is_filled(i) else "stroke")
text = "\n".join(stream.operators)
after = stream_marks(text)
rounds = round_stream_marks(text)
print(f"subpaths {before} -> {len(after)}; round {len(rounds)}")
for i, dot in enumerate(dots.dots):
    l, t, r, b = dot
    mark = after[before + i]
    want = (l * PT_PER_PX, (layout.height - b) * PT_PER_PX,
            r * PT_PER_PX, (layout.height - t) * PT_PER_PX)
    cx, cy, rad = (l + r) / 2.0, (t + b) / 2.0, (r - l) / 2.0
    want2 = ((cx - rad) * PT_PER_PX, (layout.height - cy - rad) * PT_PER_PX,
             (cx + rad) * PT_PER_PX, (layout.height - cy + rad) * PT_PER_PX)
    print(f"  dot {i}: filled={dots.is_filled(i)} paint={mark.paint!r} "
          f"fill={mark.fill:.6f} aspect={mark.aspect:.6f}")
    print(f"      read     {tuple(round(v,4) for v in mark.box)}")
    print(f"      declared {tuple(round(v,4) for v in want2)}  "
          f"max|diff| {max(abs(a-b2) for a,b2 in zip(mark.box, want2)):.6f} pt")

# --- the raster twin of the same glyph, for the domain statement
page = Image.new("RGB", (box[2] + 40, box[3] + 40), (255, 255, 255))
draw = ImageDraw.Draw(page)
gen._draw_difficulty_dots(draw, PLANTED_TIER, *box)
from tests.helpers.round_ink import ink_regions
print("\nraster: the SAME glyph, read as ink (device px, an ink extent):")
for reg in ink_regions(page, 208):
    print(f"   region {reg.box} aspect {reg.aspect:.4f} fill {reg.fill:.4f} round {reg.is_round}")
print(f"   round_marks -> {[m.box for m in round_marks(page)]}")
print(f"   declared dot boxes -> {dots.dots}")

# --- flattening cost
from tests.helpers import round_ink as RI
probe = ContentStream(width_px=1000, height_px=1000, dpi=300)
probe.round_mark(500, 500, 50, paint="fill")
one = stream_marks("\n".join(probe.operators))[0]
print(f"\nflattening at {RI._BEZIER_SEGMENTS}: fill {one.fill:.8f} aspect {one.aspect:.8f}")
RI._BEZIER_SEGMENTS = 64
two = stream_marks("\n".join(probe.operators))[0]
print(f"flattening at 64: fill {two.fill:.8f}  delta {abs(two.fill-one.fill):.3e}")
RI._BEZIER_SEGMENTS = 256
three = stream_marks("\n".join(probe.operators))[0]
print(f"flattening at 256: fill {three.fill:.8f}  delta vs 32 {abs(three.fill-one.fill):.3e}")
RI._BEZIER_SEGMENTS = 32
