"""CARD-336 AC-5: the plants, each with its matched control in the same run.

Not a test and not under ``tests/`` (G-7). Run from the worktree root::

    python scratchpad/card336/plants.py            # every plant
    python scratchpad/card336/plants.py a b1        # named plants only

Discipline, every item of which has cost this board a round:
* ``PYTHONDONTWRITEBYTECODE=1`` and ``__pycache__`` swept at BOTH ends;
* SHA-256 of every planted file before the plant and after the restore;
* planted **by text**, with the occurrence count asserted to be exactly 1 --
  the previous round had two plant attempts refused by that assertion
  (counts 2 and 0), so the anchor is checked rather than trusted;
* restored from **captured content**, never ``git checkout``;
* ``-o addopts=`` as two argv items, ``-rEfs`` as ONE flag, every call
  node-id-scoped, and ``0 skipped`` asserted;
* each plant names the cells that must RED and the cells that must stay
  GREEN in the same run, and both are checked.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PYTHON = pathlib.Path("/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python")
HERE = pathlib.Path(__file__).resolve().parent
PROBE = HERE.parent / "card338"
PAGE_INK = "tests/helpers/page_ink.py"
BOOK_PDF = "tests/test_book_pdf.py"

FRAME = "tests/test_book_puzzle_frame.py"
GEOM = "tests/property/test_book_pdf_geometry.py"

AC1 = f"{FRAME}::TestFrameCentre_TheReadingIsABoundaryInBothMedia"
AC3 = f"{FRAME}::TestFrameCentre_EveryPlacedEdgeSiteIsClassified"
PLACED = f"{FRAME}::TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame"
GEOM_1 = f"{GEOM}::test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages"
ORACLES = f"{BOOK_PDF}::TestEdgeOffset_ThePixelOraclesStillReadPixels"
PIN = f"{BOOK_PDF}::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"

COUNT = re.compile(r"(\d+) (passed|failed|error|errors|skipped|xfailed|xpassed)")
FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+)", re.M)


def sweep() -> None:
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def digest(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def run(node_ids: list[str], probe: bool) -> tuple[dict[str, int], set[str], str]:
    sweep()
    argv = [str(PYTHON), "-m", "pytest", "-o", "addopts=", "-q", "-rEfs", "--tb=line"]
    if probe:
        argv += ["-p", "probe_five_kinds"]
    argv += node_ids
    env = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=f"{PROBE}{os.pathsep}{HERE.parent / 'card329'}",
    )
    done = subprocess.run(argv, cwd=str(ROOT), env=env, capture_output=True, text=True)
    text = done.stdout + done.stderr
    sweep()
    tally = {word: int(number) for number, word in COUNT.findall(text)}
    return tally, {m.split("::", 1)[-1] for m in FAILED.findall(text)}, text


#: ``key -> (file, old text, new text, what it mutates, cells that must RED,
#: cells that must stay GREEN, run under the probe?)``
PLANTS: dict[str, tuple] = {
    "a": (
        PAGE_INK,
        """    return FrameCentre(
        frame_left=(left[0] + left[-1]) / 2,
        frame_top=(top[0] + top[-1]) / 2,""",
        """    return FrameCentre(
        frame_left=drawing.left,
        frame_top=drawing.top,""",
        "the boundary reading returns the ink extent again",
        # GEOM_1 is deliberately NOT a must-red class: under the probe that
        # node id is already red at its page-size claim (`abs(page.size[1] -
        # trim_height_px) <= 0.5`, measured 1.11 px -- poppler's rasterised
        # height, the conversion's), so a plant on the boundary reading adds
        # no visible red there and cannot be controlled by it. It is still in
        # the run, which is how that was measured.
        [AC1, PLACED],
        [AC3, ORACLES],
        True,
    ),
    "b1": (
        PAGE_INK,
        "    left = _rule_groups(_longest_runs(down.T.copy()))[0]\n",
        "    left = list(range(drawing.left, drawing.left + 6))\n",
        "the frame rule's extent taken as a CONSTANT six lines anchored on "
        "the drawing's own ink edge instead of read off the page",
        [AC1],
        [AC3, ORACLES],
        True,
    ),
    "b2": (
        PAGE_INK,
        """    return FrameCentre(
        frame_left=(left[0] + left[-1]) / 2,
        frame_top=(top[0] + top[-1]) / 2,""",
        """    return FrameCentre(
        frame_left=drawing.left + 0.5,
        frame_top=drawing.top + 0.5,""",
        "the ink-to-centre offset taken as the RASTER medium's own constant "
        "(+0.5 px) instead of read off the page",
        [AC1],
        [AC3, ORACLES],
        True,
    ),
    "c1": (
        PAGE_INK,
        "    dark = _dark(page)\n    down = dark[drawing.top : drawing.grid_bottom + 1]\n",
        "    from tests.helpers import pdf_vector  # noqa: F401\n\n"
        "    dark = _dark(page)\n    down = dark[drawing.top : drawing.grid_bottom + 1]\n",
        "the boundary oracle reaches the content-stream reader",
        [ORACLES],
        [AC3],
        False,
    ),
    "c2": (
        BOOK_PDF,
        """        page = _mirrored_pages()[FIRST_PUZZLE_PAGE - 1]  # interior page 6, left-hand (CARD-206)

        left_mm = _mm(drawing_of(page).left)

        assert abs(left_mm - 25.45) < EDGE_TOLERANCE_MM, left_mm
""",
        """        page = _mirrored_pages()[FIRST_PUZZLE_PAGE - 1]  # interior page 6, left-hand (CARD-206)
        if False:  # CARD-336 plant (c2): the crossing the pin exists to catch
            pdf_vector.rendered_page(b"", 300)

        left_mm = _mm(drawing_of(page).left)

        assert abs(left_mm - 25.45) < EDGE_TOLERANCE_MM, left_mm
""",
        "a PINNED placed-edge site reaches a content-stream reader without "
        "saying so -- planted in a module OUTSIDE this card's Touches, and "
        "restored from captured content so the file is byte-identical after",
        [PIN],
        [ORACLES],
        False,
    ),
    "d": (
        PAGE_INK,
        "        frame_top=(top[0] + top[-1]) / 2,\n",
        "        frame_top=float(top[0]),\n",
        "the boundary reading is correct in ONE medium only: the top side "
        "reports its rule's first inked line, which IS the boundary in raster",
        [AC1],
        [AC3, ORACLES],
        True,
    ),
}


def main() -> int:
    wanted = sys.argv[1:] or list(PLANTS)
    bad = [key for key in wanted if key not in PLANTS]
    assert not bad, f"no such plant: {bad}"
    verdicts = []
    for key in wanted:
        path, old, new, what, reds, greens, probe = PLANTS[key]
        target = ROOT / path
        content = target.read_text(encoding="utf-8")
        before = digest(path)
        occurrences = content.count(old)
        assert occurrences == 1, (
            f"plant ({key}) REFUSED: its anchor occurs {occurrences} times in "
            f"{path}, not exactly once"
        )
        node_ids = sorted(set(reds + greens))
        # The BASELINE first, unplanted, over the same node ids in the same
        # medium. Under the five-kind probe some cells are ALREADY red for
        # reasons that are not this card's --
        # `tests/test_book_pdf.py`'s `_interior` has no rasterising seam, so
        # `test_drawing_of_still_takes_a_page_and_not_a_file` meets a
        # `ContentStream` (the 30-cell family the re-cut routed to CARD-322's
        # conversion). A control is "green in the same run" relative to this,
        # and a plant's effect is the reds it ADDS. Measured, never assumed.
        base_tally, base_failed, _base_text = run(node_ids, probe)
        target.write_text(content.replace(old, new), encoding="utf-8")
        try:
            tally, failed, text = run(node_ids, probe)
        finally:
            target.write_text(content, encoding="utf-8")
        after = digest(path)
        assert after == before, f"plant ({key}): {path} was NOT restored"
        assert base_tally.get("skipped", 0) == 0, (key, "baseline skipped", base_tally)
        failed = failed - base_failed

        collected = tally.get("passed", 0) + tally.get("failed", 0) + tally.get("error", 0)
        reddened = {node for node in failed}
        want_red = {node.split("::", 1)[-1] for node in reds}
        want_green = {node.split("::", 1)[-1] for node in greens}
        red_ok = all(
            any(node.startswith(target_) for node in reddened) for target_ in want_red
        )
        green_ok = not any(
            any(node.startswith(target_) for node in reddened) for target_ in want_green
        )
        verdicts.append((key, what, tally, sorted(reddened), red_ok, green_ok,
                         before, after, probe))
        print(f"  BASELINE (unplanted, same medium): {base_tally}, "
              f"already red: {sorted(base_failed)}")
        print(f"\n===== PLANT ({key}) {'PROBE' if probe else 'as committed'} =====")
        print(f"  mutates: {what}")
        print(f"  file:    {path}")
        print(f"  sha256 before: {before}")
        print(f"  sha256 after:  {after}   {'IDENTICAL' if before == after else 'DIFFERENT'}")
        print(f"  tally:   {tally}  (collected {collected})")
        print(f"  skipped: {tally.get('skipped', 0)}")
        print(f"  reddened: {sorted(reddened)}")
        print(f"  must red   {sorted(want_red)} -> {'OK' if red_ok else 'MISSED'}")
        print(f"  must green {sorted(want_green)} -> {'OK' if green_ok else 'BROKEN'}")
    print("\n===== SUMMARY =====")
    ok = True
    for key, what, tally, reddened, red_ok, green_ok, before, after, probe in verdicts:
        good = red_ok and green_ok and tally.get("skipped", 0) == 0 and before == after
        ok &= good
        print(f"  ({key}) {'PASS' if good else 'FAIL'}  red={red_ok} green={green_ok} "
              f"skipped={tally.get('skipped', 0)} restored={before == after}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
