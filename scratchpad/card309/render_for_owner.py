"""CARD-309 AC-6: the owner's render, and AC-4's size/time record.

Writes, into ~/Documents/nonogram-reviews/CARD-309/:
  interior-raster.pdf   the interior this branch SHIPS (every kind declared raster)
  interior-vector.pdf   the same book composed through the assembly point with
                        every interior declaration lifted -- what CARD-322 will ship
  vector-p*.png         poppler's render of the vector interior's pages
  raster-p*.png         the same pages of the raster interior, for a side by side
Kept out of tests/ (G-7, RENDER_HEAVY_SNAPSHOT).
"""
import os, pathlib, shutil, subprocess, sys, time

ROOT = pathlib.Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-309")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from nonogram.admin import book_pdf_generator as gen_mod
from nonogram.admin import book_interior_vector as assembly
from tests.test_book_pdf import _book, _puzzle

OUT = pathlib.Path.home() / "Documents" / "nonogram-reviews" / "CARD-309"
OUT.mkdir(parents=True, exist_ok=True)

BOOK = [(30, 30, 10), (20, 20, 6), (20, 20, 6), (10, 10, 3), (10, 10, 3), (10, 10, 3)]
rows = [_puzzle(w, h, d, name=f"Picture {i + 1}") for i, (w, h, d) in enumerate(BOOK)]

def timed(generator):
    start = time.perf_counter()
    data = generator.export_interior(rows).getvalue()
    return data, time.perf_counter() - start

raster = gen_mod.BookPDFGenerator(_book())
raster_kinds = raster.interior_stream(rows).page_kinds
raster_bytes, raster_s = timed(gen_mod.BookPDFGenerator(_book()))
(OUT / "interior-raster.pdf").write_bytes(raster_bytes)

for kind in list(gen_mod._RASTER_DECLARATIONS):
    if kind is not gen_mod.PageKind.COVER and kind is not gen_mod.PageKind.DIVIDER:
        del gen_mod._RASTER_DECLARATIONS[kind]
vector = assembly.interior_generator(_book())
vector_kinds = vector.interior_stream(rows).page_kinds
vector_bytes, vector_s = timed(assembly.interior_generator(_book()))
(OUT / "interior-vector.pdf").write_bytes(vector_bytes)

print("pages:", len(raster_kinds), [k.value for k in raster_kinds])
print(f"raster interior: {len(raster_bytes):>10,} B   {raster_s * 1000:8.1f} ms   "
      f"{len(raster_bytes) / len(raster_kinds):>10,.0f} B/page   "
      f"{raster_s * 1000 / len(raster_kinds):6.2f} ms/page")
print(f"vector interior: {len(vector_bytes):>10,} B   {vector_s * 1000:8.1f} ms   "
      f"{len(vector_bytes) / len(vector_kinds):>10,.0f} B/page   "
      f"{vector_s * 1000 / len(vector_kinds):6.2f} ms/page")
print(f"ratio: size {len(raster_bytes) / len(vector_bytes):.1f}x  "
      f"time {raster_s / vector_s:.1f}x")

pdftoppm = shutil.which("pdftoppm")
print("pdftoppm:", pdftoppm)
if pdftoppm:
    for label, name in (("vector", "interior-vector.pdf"), ("raster", "interior-raster.pdf")):
        for page in (2, 4, 6, 9):
            subprocess.run(
                [pdftoppm, "-r", "150", "-f", str(page), "-l", str(page), "-png",
                 str(OUT / name), str(OUT / f"{label}-p{page:02d}")],
                check=True, capture_output=True)
    print("rendered:", sorted(p.name for p in OUT.glob("*.png")))
print("out:", OUT)
