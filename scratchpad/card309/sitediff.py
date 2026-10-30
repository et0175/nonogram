import sys
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-309/src")
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-309")
import subprocess, pathlib
import tests.test_book_export_interior_cover as m
cls = m.TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage
head = subprocess.run(["git","show","HEAD:src/nonogram/admin/book_pdf_generator.py"],
                      cwd="/Users/omelnikova/PycharmProjects/PythonProject4-card-309",
                      capture_output=True, text=True).stdout
now = (pathlib.Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-309")/"src/nonogram/admin/book_pdf_generator.py").read_text()
a = {(k, n, t.strip()[:70]) for _l, k, n, t, _x in cls._page_positions(head)[0]}
b = {(k, n, t.strip()[:70]) for _l, k, n, t, _x in cls._page_positions(now)[0]}
print("HEAD sites:", len(a), " NOW sites:", len(b))
print("ADDED:")
for r in sorted(b - a): print("  ", r)
print("REMOVED:")
for r in sorted(a - b): print("  ", r)
import collections
print("HEAD by kind:", collections.Counter(k for k, _n, _t in a))
print("NOW  by kind:", collections.Counter(k for k, _n, _t in b))
