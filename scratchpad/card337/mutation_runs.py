"""CARD-337 AC-5: every repaired claim gets a plant that re-breaks it.

Not a test and not under ``tests/`` (G-8). Each plant mutates **by text**,
measures under the five-kind probe, and **restores from captured content** --
never ``git checkout``, so a dirty tree returns to exactly what it was.

Discipline (the shape ``seam_experiment.py`` established, each item paid for
once by this board):

* ``PYTHONDONTWRITEBYTECODE=1`` and ``__pycache__`` swept at BOTH ends;
* SHA-256 of every touched file before the plant and after the restore;
* every replacement's occurrence count asserted **exactly 1**;
* ``-rEfs`` as ONE flag; ``-o addopts=`` as TWO argv items;
* the whole environment inherited, so a gate skips for its own reason;
* a run collecting nothing is an ERROR;
* each plant names the cells it must RED and a matched CONTROL that must stay
  green **in the same run**, and ``0 skipped`` is asserted (ADR-0039/R1).

Run::

    python scratchpad/card337/mutation_runs.py            # every plant
    python scratchpad/card337/mutation_runs.py MUT-3      # one
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path("/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python")
MODULE = "tests/test_book_pdf_ink_mode.py"
SRC_VECTOR = "src/nonogram/admin/book_vector.py"
SRC_GENERATOR = "src/nonogram/admin/book_pdf_generator.py"

COUNT = re.compile(r"(\d+) (passed|failed|error|errors|skipped|xfailed|xpassed)")
FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+)", re.M)

#: key -> (what it mutates, [(file, old, new), ...], must-red cells,
#:         matched control cells that must stay GREEN in the same run)
PLANTS: dict[str, dict] = {
    # ---- the two test-side plants: each re-breaks this card's own repair ----
    "MUT-1": {
        "what": "the medium gate in pdf_page_declarations: read the XObject "
                "unconditionally again, as the module did before CARD-337",
        "edits": [(
            MODULE,
            '            xobjects = resources.get(b"XObject")\n'
            "            if xobjects:\n",
            '            xobjects = resources[b"XObject"]\n'
            "            if True:\n",
        )],
        "must_red": [
            "test_every_page_declares_devicegray_and_one_channel",
            "test_the_colour_export_of_the_same_book_declares_devicergb",
            "test_the_two_files_hold_the_same_marks_page_for_page",
            "test_the_file_the_owner_downloads_is_the_one_the_book_chose",
            "test_the_grayscale_file_is_materially_smaller",
            "test_export_book_writes_a_grey_interior_beside_a_colour_cover",
            "test_the_two_modes_agree_on_every_page_of_every_book",
            "test_no_mark_moves_on_any_page_bitmap",
        ],
        # The cover is raster by ADR-0042/R2 with an empty expires_with, so the
        # cover-only readings cannot be broken by a medium gate: they are the
        # matched control that distinguishes "the gate was removed" from "the
        # reader stopped working".
        "control": [
            "test_the_cover_file_of_a_black_and_white_book_is_devicergb",
            "test_the_cover_still_carries_colour",
            "test_the_generated_title_cover_is_devicergb_too",
        ],
    },
    "MUT-2": {
        "what": "the raster-write ordinal translation: use the write count as "
                "the interior page number again (the M10 cause line)",
        "edits": [(
            MODULE,
            "            number = raster_page_numbers[checked]\n",
            "            number = checked + 1\n",
        )],
        "must_red": ["test_no_mark_moves_on_any_page_bitmap"],
        # Everything else in the class reads the FILE, not the write ordinal,
        # so it must be untouched -- which is what says the plant hit the
        # ordinal and not the export.
        "control": [
            "test_every_page_declares_devicegray_and_one_channel",
            "test_the_two_files_hold_the_same_marks_page_for_page",
            "test_the_grayscale_file_is_materially_smaller",
        ],
    },
    # ---- three src/ plants: can the RE-EXPRESSED claims detect a real defect? ----
    "MUT-3": {
        "what": "ContentStream.fill_grey emits DeviceRGB (`rg`) instead of "
                "DeviceGray (`g`) -- a real colour-space regression on a "
                "vector page, which has no XObject to read it off",
        "edits": [(
            SRC_VECTOR,
            '        self._operators.append(f"{_number(_grey(level))} g")\n',
            '        self._operators.append(\n'
            '            f"{_number(_grey(level))} {_number(_grey(level))} '
            '{_number(_grey(level))} rg"\n'
            "        )\n",
        )],
        "must_red": [
            "test_every_page_declares_devicegray_and_one_channel",
            "test_the_colour_export_of_the_same_book_declares_devicergb",
            "test_the_file_the_owner_downloads_is_the_one_the_book_chose",
            "test_export_book_writes_a_grey_interior_beside_a_colour_cover",
            "test_the_two_modes_agree_on_every_page_of_every_book",
        ],
        "control": [
            "test_the_cover_file_of_a_black_and_white_book_is_devicergb",
            "test_no_mark_moves_on_any_page_bitmap",
        ],
    },
    "MUT-4": {
        "what": "a vector page's stream becomes export-dependent (one extra "
                "operator on the second export) -- the defect the re-expressed "
                "'not one mark moved' claim exists to catch on a vector page",
        # NOTE, kept because it cost a cycle and is why this harness asserts a
        # NAMED must-red list rather than "something went red": the first
        # version of this plant mutated every SECOND render. The baseline book
        # has an EVEN number of vector pages (10), so page k of the grey export
        # and page k of the colour export landed on the same parity and were
        # mutated IDENTICALLY -- the two files still agreed and
        # `test_the_two_files_hold_the_same_marks_page_for_page` stayed green
        # for a reason with nothing to do with the claim. EC-1's corpus holds
        # books with an ODD vector count, so it caught the plant anyway, which
        # is precisely how a parity artefact gets mistaken for evidence. Keyed
        # on ONE render now, so the misalignment is certain.
        "edits": [(
            SRC_VECTOR,
            "    def render(self) -> bytes:\n",
            "    _RENDERS = 0\n\n"
            "    def render(self) -> bytes:\n"
            "        type(self)._RENDERS += 1\n"
            "        if type(self)._RENDERS == 2:\n"
            '            self._operators = [*self._operators, "0.5 g"]\n',
        )],
        # One plant keyed on a GLOBAL render ordinal can only reach one of the
        # two cells: it fires once, during whichever export runs first. So the
        # mechanism is planted twice -- MUT-4 on the baseline pair, MUT-4b on
        # EC-1's corpus -- rather than one plant being credited with a cell it
        # never reached.
        "must_red": ["test_the_two_files_hold_the_same_marks_page_for_page"],
        "control": [
            "test_the_cover_file_of_a_black_and_white_book_is_devicergb",
            "test_the_corpus_is_the_size_it_claims_and_varies",
            "test_the_two_modes_agree_on_every_page_of_every_book",
        ],
    },
    "MUT-4b": {
        "what": "the same defect reaching EC-1's corpus: every SECOND vector "
                "page render carries an extra operator. The baseline book's "
                "even vector-page count makes the two exports align on parity "
                "(see MUT-4's note), so this plant is invisible to the "
                "baseline pair and is caught by the corpus's ONE odd-count "
                "book -- 1 of 14: book 11, 9 vector pages, measured by "
                "measure_ec1_media.py; the other thirteen are even. Stated as "
                "a count because the plural reads as redundancy there is none "
                "of -- lose that one book and this plant stops being killed. "
                "What makes that safe rather than silent is the harness: "
                "`must_red` names the cell, so a corpus without book 11 "
                "reports NOT KILLED by name rather than quietly passing",
        "edits": [(
            SRC_VECTOR,
            "    def render(self) -> bytes:\n",
            "    _RENDERS = 0\n\n"
            "    def render(self) -> bytes:\n"
            "        type(self)._RENDERS += 1\n"
            "        if type(self)._RENDERS % 2 == 0 and self._operators:\n"
            '            self._operators = [*self._operators, "0.5 g"]\n',
        )],
        "must_red": ["test_the_two_modes_agree_on_every_page_of_every_book"],
        "control": [
            "test_the_cover_file_of_a_black_and_white_book_is_devicergb",
            "test_the_corpus_is_the_size_it_claims_and_varies",
        ],
    },
    "MUT-5": {
        "what": "DIVIDER stops being a declared bitmap, so the interior holds "
                "NO raster page and the stored ink mode reaches nothing in the "
                "file -- the case assert_mode_reached_the_file's named-survivor "
                "floor exists to refuse (ADR-0039/R1)",
        "edits": [(
            SRC_GENERATOR,
            "def page_medium(kind: PageKind) -> PageMedium:\n",
            "def page_medium(kind: PageKind) -> PageMedium:\n"
            "    if kind is PageKind.DIVIDER:\n"
            "        return PageMedium.VECTOR\n",
        )],
        "must_red": [
            "test_every_page_declares_devicegray_and_one_channel",
            "test_the_colour_export_of_the_same_book_declares_devicergb",
            "test_the_file_the_owner_downloads_is_the_one_the_book_chose",
            "test_export_book_writes_a_grey_interior_beside_a_colour_cover",
            "test_the_grayscale_file_is_materially_smaller",
            "test_no_mark_moves_on_any_page_bitmap",
            "test_the_two_modes_agree_on_every_page_of_every_book",
        ],
        "control": [
            "test_the_cover_file_of_a_black_and_white_book_is_devicergb",
            "test_the_cover_still_carries_colour",
        ],
    },
}


def sweep() -> None:
    for path in ROOT.rglob("__pycache__"):
        if ".git" not in path.parts:
            shutil.rmtree(path, ignore_errors=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> tuple[dict[str, int], list[str], str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    argv = [
        str(PYTHON), "-m", "pytest",
        "-p", "scratchpad.card338.probe_five_kinds",
        MODULE,
        "-o", "addopts=",          # TWO argv items, never one quoted string
        "-rEfs",                   # ONE flag: -rfs omits ERRORs
        "--tb=no", "-q", "-p", "no:warnings",
    ]
    out = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True).stdout.decode()
    counts = {kind: int(n) for n, kind in COUNT.findall(out)}
    reds = sorted({m.split("::")[-1].split("[")[0] for m in FAILED.findall(out)})
    return counts, reds, out


def measure(key: str) -> bool:
    plant = PLANTS[key]
    files = sorted({edit[0] for edit in plant["edits"]})
    paths = {name: ROOT / name for name in files}
    before = {name: digest(path) for name, path in paths.items()}
    captured = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}

    sweep()
    try:
        for name, old, new in plant["edits"]:
            text = paths[name].read_text(encoding="utf-8")
            occurrences = text.count(old)
            assert occurrences == 1, (
                f"{key}: the plant text occurs {occurrences} times in {name}, "
                "not exactly 1 -- a 2-occurrence replace is a different "
                f"experiment. Text:\n{old!r}"
            )
            paths[name].write_text(text.replace(old, new), encoding="utf-8")
        counts, reds, out = run()
    finally:
        for name, path in paths.items():
            path.write_text(captured[name], encoding="utf-8")
        sweep()

    after = {name: digest(path) for name, path in paths.items()}
    restored = before == after

    collected = sum(counts.get(k, 0) for k in ("passed", "failed", "error", "errors"))
    missed = [cell for cell in plant["must_red"] if cell not in reds]
    broken_control = [cell for cell in plant["control"] if cell in reds]
    skipped = counts.get("skipped", 0)

    ok = (
        restored
        and collected > 0
        and not missed
        and not broken_control
        and skipped == 0
        and counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0) > 0
    )

    print(f"\n=== {key}: {plant['what']}")
    for name in files:
        print(f"    {name}")
        print(f"      sha256 before plant : {before[name]}")
        print(f"      sha256 after restore: {after[name]}  "
              f"{'IDENTICAL' if before[name] == after[name] else 'DIFFERS -- RESTORE FAILED'}")
    print(f"    counts: {counts}   collected={collected}")
    print(f"    reddened ({len(reds)}): {reds}")
    print(f"    must-red missed: {missed or 'none'}")
    print(f"    matched control GREEN in the same run: "
          f"{'yes -- ' + ', '.join(plant['control']) if not broken_control else 'NO: ' + str(broken_control)}")
    print(f"    skipped: {skipped} ({'0 asserted' if skipped == 0 else 'NON-ZERO -- a skip reads as a pass'})")
    print(f"    VERDICT: {'KILLED' if ok else 'NOT KILLED -- investigate'}")
    if not ok:
        print(out[-2500:])
    return ok


keys = sys.argv[1:] or list(PLANTS)
results = {key: measure(key) for key in keys}
print("\n=== summary")
for key, ok in results.items():
    print(f"    {key}: {'KILLED' if ok else 'NOT KILLED'}")
sys.exit(0 if all(results.values()) else 1)
