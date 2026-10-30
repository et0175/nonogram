"""CARD-309's mutation harness. Lives in scratchpad/card309/, never the root.

Each mutant is (label, file, old, new, node ids expected to RED). The file is
checksummed before and after every mutant, byte-caches are swept before AND
after, and PYTHONDONTWRITEBYTECODE is set in the child's environment -- a
byte-length-preserving mutant restored within the same second otherwise leaves
a __pycache__ entry that still validates.
"""
import hashlib, os, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-309")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"

GEN = "src/nonogram/admin/book_pdf_generator.py"
ASM = "src/nonogram/admin/book_interior_vector.py"
PROOF = "src/nonogram/admin/book_proof.py"
TBP = "tests/test_book_pdf.py"


def sweep():
    for d in ROOT.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)
    for f in ROOT.rglob("*.pyc"):
        f.unlink(missing_ok=True)


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def run(nodes):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run(
        [PY, "-m", "pytest", "-o", "addopts=", "-q", "-p", "no:randomly",
         "--tb=no", "-rf", *nodes],
        cwd=ROOT, capture_output=True, text=True, env=env,
    )
    failed = sorted(
        line.split(" ", 1)[1].split(" ")[0]
        for line in done.stdout.splitlines() if line.startswith("FAILED")
    )
    last = [l for l in done.stdout.splitlines() if "passed" in l or "failed" in l or "error" in l]
    return failed, (last[-1] if last else done.stdout[-400:])


MUTANTS = [
    ("M1 inside: the guide gate ignores the writer set and draws the bitmap",
     GEN,
     "                if page_medium(PageKind.GUIDE) is PageMedium.VECTOR:\n"
     "                    page = _drawn_downstream(\n"
     "                        self.pages.guide,",
     "                if False:\n"
     "                    page = _drawn_downstream(\n"
     "                        self.pages.guide,",
     ["tests/test_book_pdf.py::TestAssemblyPoint_TheDownstreamWritersAreReachable::test_every_interior_page_is_written_as_operators",
      "tests/test_book_pdf.py::TestAssemblyPoint_TheDownstreamWritersAreReachable::test_a_generator_with_no_downstream_writer_refuses"]),

    ("M2 edge: default-DENY removed -- a missing writer falls through",
     GEN,
     "    if writer is None:\n        raise ValueError(",
     "    if False:\n        raise ValueError(",
     ["tests/test_book_pdf.py::TestAssemblyPoint_TheDownstreamWritersAreReachable::test_a_generator_with_no_downstream_writer_refuses",
      "tests/test_book_pdf.py::TestAssemblyPoint_TheDownstreamWritersAreReachable::test_a_partial_writer_set_refuses_only_the_kind_it_is_missing"]),

    ("M3 edge: the refusal fires on an incomplete SET rather than on the kind",
     GEN,
     "    if writer is None:\n        raise ValueError(\n            f\"a {kind.value} page is written as operators (ADR-0042/R1) and \"",
     "    if True:\n        raise ValueError(\n            f\"a {kind.value} page is written as operators (ADR-0042/R1) and \"",
     ["tests/test_book_pdf.py::TestAssemblyPoint_TheDownstreamWritersAreReachable::test_every_interior_page_is_written_as_operators",
      "tests/test_book_pdf.py::TestAssemblyPoint_TheDownstreamWritersAreReachable::test_the_four_writers_each_drew_their_own_page",
      "tests/test_book_pdf.py::TestAssemblyPoint_TheDownstreamWritersAreReachable::test_a_partial_writer_set_refuses_only_the_kind_it_is_missing"]),

    ("M4 inside: every vector interior kind is drawn by the puzzle writer",
     GEN,
     "                    page = _drawn_downstream(\n"
     "                        self.pages.toc,\n"
     "                        PageKind.TOC,\n"
     "                        rows,\n"
     "                        page_frame(self.page_spec(toc_page_number)),\n"
     "                        self.dpi,\n"
     "                        toc_page_number,\n"
     "                    )",
     "                    page = self.vector_title_page(toc_page_number)",
     ["tests/test_book_pdf.py::TestAssemblyPoint_TheDownstreamWritersAreReachable::test_the_four_writers_each_drew_their_own_page"]),

    ("M5 inside: the generator takes the cycle at module level",
     GEN,
     "from nonogram.admin.book_puzzle_vector import puzzle_page_stream, two_up_page_stream",
     "from nonogram.admin.book_puzzle_vector import puzzle_page_stream, two_up_page_stream\n"
     "if False:\n    from nonogram.admin.book_guide_vector import guide_page",
     ["tests/test_book_pdf.py::TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden::test_the_generator_imports_none_of_the_writers_that_import_it"]),

    ("M6 edge: the generator takes the cycle inside a function body",
     GEN,
     "    def interior_stream(self, puzzles: List[dict]) -> InteriorStream:",
     "    def interior_stream(self, puzzles: List[dict]) -> InteriorStream:\n"
     "        from nonogram.admin.book_toc_vector import toc_page_stream  # noqa: F401",
     ["tests/test_book_pdf.py::TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden::test_the_generator_imports_none_of_the_writers_that_import_it"]),

    ("M7 edge: another module imports the assembly point, so it is not a leaf",
     PROOF,
     "import io\nimport re",
     "import io\nimport re\nif False:\n    from nonogram.admin import book_interior_vector",
     ["tests/test_book_pdf.py::TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden::test_nothing_in_the_package_imports_the_assembly_point"]),

    ("M8 inside: the assembly point binds the wrong writer to the answer page",
     ASM,
     "    answer=answer_page,",
     "    answer=packed_answer_page,",
     ["tests/test_book_pdf.py::TestAssemblyPoint_TheDownstreamWritersAreReachable::test_each_of_the_four_bindings_was_used"]),

    ("M9 edge: the board's status vocabulary goes back to the unobserved spelling",
     TBP,
     '    {"done", "ready", "in_progress", "blocked", "parked", "skipped"}',
     '    {"done", "ready", "in progress", "blocked", "parked", "skipped"}',
     ["tests/test_book_pdf.py::test_no_declaration_outlives_the_cards_that_remove_it"]),

    ("M10 inside: a declaration goes back to naming the card that is closing",
     GEN,
     '''        expires_with=("CARD-299", "CARD-322"),
    ),
    PageKind.PUZZLE: RasterDeclaration(''',
     '''        expires_with=("CARD-299", "CARD-309"),
    ),
    PageKind.PUZZLE: RasterDeclaration(''',
     ["tests/test_book_pdf.py::test_no_declaration_names_the_card_that_is_closing"]),

    ("M11 edge: the injected writer is called through a local instead of a parameter",
     GEN,
     """                    page = _drawn_downstream(
                        self.pages.toc,
                        PageKind.TOC,
                        rows,""",
     """                    write_toc = self.pages.toc
                    page = write_toc(
                        rows,""",
     ["tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_the_page_position_set_is_derived_from_the_one_geometry_door",
      "tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost"]),
]


def main():
    sweep()
    baseline = {p: digest(p) for p in (GEN, ASM, PROOF, TBP)}
    nodes = sorted({n for *_rest, ns in MUTANTS for n in ns})
    failed, line = run(nodes)
    print(f"UNMUTATED: {line}  failures={failed}")
    assert failed == [], failed
    # Prove the recorder reports on a bare `assert x == y` whose AssertionError
    # carries an empty message -- a crashed recorder reports NOT-REACHED, which
    # is identical to a survivor.
    probe = ROOT / "scratchpad/card309/_probe_test.py"
    probe.write_text("def test_probe():\n    x, y = 1, 2\n    assert x == y\n")
    pf, pl = run([str(probe.relative_to(ROOT))])
    print(f"RECORDER PROBE: {pl}  failures={pf}")
    assert len(pf) == 1, pf
    probe.unlink()
    sweep()

    results = []
    for label, path, old, new, expect in MUTANTS:
        assert digest(path) == baseline[path], f"{path} not at baseline before {label}"
        target = ROOT / path
        text = target.read_text()
        assert text.count(old) == 1, (label, path, text.count(old))
        sweep()
        target.write_text(text.replace(old, new))
        try:
            failed, line = run(nodes)
        finally:
            target.write_text(text)
            sweep()
        assert digest(path) == baseline[path], f"{path} not restored after {label}"
        killed = sorted(set(expect) & set(failed))
        survived = sorted(set(expect) - set(failed))
        results.append((label, killed, survived, failed, line))
        print(f"\n{label}\n  summary: {line}\n  KILLED:    {killed}\n  SURVIVED:  {survived}")
        if set(failed) - set(expect):
            print(f"  also red:  {sorted(set(failed) - set(expect))}")

    sweep()
    failed, line = run(nodes)
    print(f"\nRESTORED: {line}  failures={failed}")
    assert failed == [], failed
    bad = [r[0] for r in results if r[2]]
    print("\nMUTANTS WITH SURVIVORS:", bad or "none")


main()
