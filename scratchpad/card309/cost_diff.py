import sys, subprocess, pathlib, ast
ROOT = "/Users/omelnikova/PycharmProjects/PythonProject4-card-309"
sys.path.insert(0, ROOT + "/src"); sys.path.insert(0, ROOT)
import tests.test_book_export_interior_cover as m
cls = m.TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage
head = subprocess.run(["git","show","HEAD:src/nonogram/admin/book_pdf_generator.py"],
                      cwd=ROOT, capture_output=True, text=True).stdout
now = (pathlib.Path(ROOT)/"src/nonogram/admin/book_pdf_generator.py").read_text()
for label, src in (("HEAD", head), ("NOW", now)):
    seq = [(ex, len(cls._page_positions(src, callee_exemptions=ex)[2]))
           for ex, _ in cls.CALLEE_EXEMPTION_COST]
    print(label, [n for _ex, n in seq])
    steps = [b[1]-a[1] for b, a in zip(seq, seq[1:])]
    print("   steps:", steps)
    print("   ast.Call nodes:", sum(isinstance(n, ast.Call) for n in ast.walk(ast.parse(src))))
