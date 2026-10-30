import sys
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-309/src")
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-309")
import tests.test_book_export_interior_cover as m
cls = m.TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage
sites, vocab, refusals = cls._page_positions()
print("refusals:", len(refusals))
for r in refusals:
    print("  ", str(r)[:220])
print("vocab:", tuple(vocab))
print("sites:", len(sites), "declared:", cls.POSITION_SITE_COUNT)
