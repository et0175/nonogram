import sys, subprocess, pathlib, collections
ROOT = "/Users/omelnikova/PycharmProjects/PythonProject4-card-309"
sys.path.insert(0, ROOT + "/src"); sys.path.insert(0, ROOT)
import tests.test_book_export_interior_cover as m
cls = m.TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage
head = subprocess.run(["git","show","HEAD:src/nonogram/admin/book_pdf_generator.py"],
                      cwd=ROOT, capture_output=True, text=True).stdout
now = (pathlib.Path(ROOT)/"src/nonogram/admin/book_pdf_generator.py").read_text()

print("== 1. counting expressions ==")
for label, src in (("HEAD", head), ("NOW", now)):
    sites = cls._counting_expressions(src) if cls._counting_expressions.__code__.co_argcount > 1 else None
    print(label, "n/a" if sites is None else len(sites))
print("  (signature argcount:", cls._counting_expressions.__code__.co_argcount, cls._counting_expressions.__code__.co_varnames[:3], ")")

print("== 2. position sites ==")
for label, src in (("HEAD", head), ("NOW", now)):
    s, v, r = cls._page_positions(src)
    print(label, len(s), "vocab", tuple(v), "refusals", len(r))

print("== 3. exempted bare literals (follow_terms) ==")
for label, src in (("HEAD", head), ("NOW", now)):
    ex = cls._bare_literals(cls._page_positions(src, follow_terms=True)[0])
    terms = sorted({item[1] for _,_,_,_,bad in ex for item in bad if isinstance(item, tuple)})
    print(label, len(ex), terms)
