import sys, pathlib, collections
ROOT = "/Users/omelnikova/PycharmProjects/PythonProject4-card-309"
sys.path.insert(0, ROOT + "/src"); sys.path.insert(0, ROOT)
import tests.test_book_export_interior_cover as m
cls = m.TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage
sites = cls._counting_expressions()
print("counting expressions NOW:", len(sites))
for line, _node, text in sites:
    print("   ", line, repr(text[:95]))
