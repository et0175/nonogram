import sys
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-309/src")
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-309")
from nonogram.admin import book_pdf_generator as g
from nonogram.admin.book_answer_key import PackedAnswerPage
from tests.test_book_pdf import _book, _puzzle

calls = {"answer": 0, "packed": 0, "guide": 0, "toc": 0}
import nonogram.admin.book_interior_vector as asm

def wrap(name, fn):
    def inner(*a, **k):
        calls[name] += 1
        return fn(*a, **k)
    return inner

for trial in (
    [(10,10,3),(10,10,3),(10,10,3)],
    [(30,30,10),(10,10,3)],
    [(30,30,10)],
    [(30,30,10),(30,30,10),(10,10,3),(10,10,3),(10,10,3)],
):
    for k in calls: calls[k] = 0
    rows = [_puzzle(w,h,d,name=f"P{i}") for i,(w,h,d) in enumerate(trial)]
    pages = g.InteriorPageWriters(
        guide=wrap("guide", asm.guide_page_stream),
        toc=wrap("toc", asm.toc_page_stream),
        answer=wrap("answer", asm.answer_page),
        packed_answer=wrap("packed", asm.packed_answer_page),
    )
    for kind in (g.PageKind.TITLE, g.PageKind.GUIDE, g.PageKind.TOC, g.PageKind.ANSWER, g.PageKind.PUZZLE):
        g._RASTER_DECLARATIONS.pop(kind, None)
    gen = g.BookPDFGenerator(_book(), pages=pages)
    try:
        gen.export_interior(rows)
        print(trial, "->", dict(calls))
    except Exception as e:
        print(trial, "-> EXC", type(e).__name__, e)
