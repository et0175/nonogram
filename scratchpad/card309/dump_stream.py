import sys
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-309/src")
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-309")
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from tests.test_book_pdf import _book, _puzzle

g = BookPDFGenerator(_book())
rows = [_puzzle(10, 10, 3, name=f"P{i}") for i in range(2)]
pages = g.interior_pages(rows)
for i, p in enumerate(pages, 1):
    print(i, type(p).__name__)
for i, p in enumerate(pages, 1):
    if type(p).__name__ == "ContentStream":
        ops = p.operators if isinstance(p.operators, str) else "\n".join(p.operators)
        lines = ops.split("\n")
        print("=== page", i, p.width_px, p.height_px, p.dpi, "lines:", len(lines))
        print("\n".join(lines[:45]))
        print("...")
        print("\n".join(lines[-20:]))
        break
