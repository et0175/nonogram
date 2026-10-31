"""CARD-330 mutant driver. Run from the worktree root AFTER committing."""

from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-330")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"

MUTANTS = [
    # (id, file, old, new, node ids that MUST red, note)
    (
        "M1",
        "tests/test_book_pdf.py",
        "CELL_TOLERANCE_MM = 0.05\nEDGE_TOLERANCE_MM = 0.1\n",
        "CELL_TOLERANCE_MM = 0.05\nEDGE_TOLERANCE_MM = 0.3\n",
        [
            "tests/test_book_pdf.py::TestEdgeOffset_ATolerenceChangeCarriesItsExemption"
            "::test_the_bound_is_the_figure_the_criteria_state_and_nothing_is_exempt"
        ],
        "AC-4, inside the claimed region: the bound widened to admit the mitre, no exemption",
    ),
    (
        "M2",
        "tests/test_book_pdf.py",
        "CELL_TOLERANCE_MM = 0.05\nEDGE_TOLERANCE_MM = 0.1\n",
        "CELL_TOLERANCE_MM = 0.05\nEDGE_TOLERANCE_MM = 0.1001\n",
        [
            "tests/test_book_pdf.py::TestEdgeOffset_ATolerenceChangeCarriesItsExemption"
            "::test_the_bound_is_the_figure_the_criteria_state_and_nothing_is_exempt"
        ],
        "AC-4, at the edge: the smallest widening there is",
    ),
    (
        "M3",
        "src/nonogram/admin/book_page_spec.py",
        "    min_thin_rule_mm=0.25,",
        "    min_thin_rule_mm=0.5,",
        [
            "tests/test_book_pdf.py::TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels"
            "::test_the_rasters_ink_is_two_device_pixels_outside_the_stream_on_every_edge",
            "tests/test_book_pdf.py::TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels"
            "::test_that_two_pixels_is_half_a_rule_and_not_a_quantisation_step",
        ],
        "the 2 px claim, inside: the raster thin floor doubled, so the border is 12 px and the offset 5",
    ),
    (
        "M4",
        "src/nonogram/admin/book_page_spec.py",
        "    min_thin_rule_mm=0.25,",
        "    min_thin_rule_mm=0.2541,",
        [
            "tests/test_book_pdf.py::TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels"
            "::test_the_rasters_ink_is_two_device_pixels_outside_the_stream_on_every_edge",
            "tests/test_book_pdf.py::TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels"
            "::test_that_two_pixels_is_half_a_rule_and_not_a_quantisation_step",
        ],
        "the 2 px claim, at the edge: 0.2541 mm is 3.0012 px, the smallest floor that rounds up to 4",
    ),
    (
        "M5",
        "tests/test_book_pdf.py",
        "def _consecutive(indices: np.ndarray) -> list[list[int]]:",
        "def _a_placed_edge_site_that_reads_no_page() -> None:\n"
        "    assert 0.0 < EDGE_TOLERANCE_MM\n\n\n"
        "def _consecutive(indices: np.ndarray) -> list[list[int]]:",
        [
            "tests/test_book_pdf.py::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_every_site_reads_its_page_through_the_raster_ink_oracle"
        ],
        "the medium pin, inside: a new site naming the bound without reading a page",
    ),
    (
        "M6",
        "tests/test_book_pdf.py",
        '            "test_the_two_media_ink_differs_by_one_device_pixel_not_two",',
        '            "test_the_two_media_ink_differs_by_one_device_pixel_not_tw0",',
        [
            "tests/test_book_pdf.py::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_the_exemption_list_names_only_sites_that_exist",
            "tests/test_book_pdf.py::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_every_site_reads_its_page_through_the_raster_ink_oracle",
        ],
        "the medium pin, at the edge: one character off an exempt name, so the entry exempts nothing",
    ),
    (
        "M7",
        "tests/helpers/page_ink.py",
        "from PIL import Image, PdfParser",
        "from PIL import Image, PdfParser\n\nfrom tests.helpers import pdf_vector",
        [
            "tests/test_book_pdf.py::TestEdgeOffset_ThePixelOraclesStillReadPixels"
            "::test_neither_oracle_imports_the_content_stream_reader"
        ],
        "AC-5, inside: the oracle reaches for the content-stream reader",
    ),
    (
        "M8",
        "tests/helpers/page_ink.py",
        "    dark = _dark(page)\n    vertical = _rule_groups",
        "    dark = np.asarray(page.convert('L')) < INK_LEVEL\n    vertical = _rule_groups",
        [
            "tests/test_book_pdf.py::TestEdgeOffset_ThePixelOraclesStillReadPixels"
            "::test_the_measuring_functions_still_reduce_a_bitmap_to_a_mask"
        ],
        "AC-5, at the edge: still pixels, but no longer through the one shared ink reading",
    ),
]


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sweep() -> None:
    for pyc in ROOT.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def run(nodes: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        [PY, "-m", "pytest", *nodes, "-o", "addopts=", "-p", "no:randomly", "--tb=no", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return proc.returncode, proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-300:]


def main() -> None:
    rows = []
    for ident, rel, old, new, nodes, note in MUTANTS:
        target = ROOT / rel
        before = sha(target)
        sweep()
        text = target.read_text()
        assert old in text, (ident, rel, "anchor not found")
        assert text.count(old) == 1, (ident, rel, "anchor is not unique", text.count(old))
        target.write_text(text.replace(old, new, 1))
        assert sha(target) != before, (ident, "the mutant did not change the file")
        code, summary = run(nodes)
        sweep()
        subprocess.run(["git", "checkout", "--", rel], cwd=ROOT, check=True)
        after = sha(target)
        assert after == before, (ident, "restore did not return the file", before, after)
        sweep()
        verdict = "KILLED" if code != 0 else "SURVIVED"
        rows.append((ident, rel, verdict, summary, note))
        print(f"{ident:3} {verdict:9} {rel:40} {summary}")
        print(f"     {note}")
    print()
    survived = [row for row in rows if row[2] != "KILLED"]
    print("survivors:", survived or "none")


if __name__ == "__main__":
    main()
