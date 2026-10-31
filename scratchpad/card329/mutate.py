"""CARD-329 AC-5: plant by text, measure the node, restore.

Not a test and not under ``tests/`` (G-7). Run from the worktree root.

Discipline, every item of which has cost this board a round:

* ``PYTHONDONTWRITEBYTECODE=1`` and ``__pycache__`` swept before **and**
  after every run, so a stale bytecode file cannot be what a verdict is read
  off;
* each plant is located **by text**, never by line number, with its
  occurrence count asserted to be exactly 1 before it is applied;
* SHA-256 of every touched file asserted before the plant and after the
  restore, so a half-restored tree cannot be the next measurement's baseline;
* the full environment is inherited (``dict(os.environ, ...)``) -- a stripped
  ``PATH`` hides poppler, and every vector reading in this card goes through
  ``pdftoppm``, so a stripped ``PATH`` would turn a killed mutant into a
  false SURVIVED;
* ``-o addopts=`` passed as **two** argv items, never as one quoted string;
* **0 skipped asserted on every control**: asserting the passed count is not
  enough, because a skip keeps the collected count and removes the assertion;
* the matched control for every plant is the same node, green, measured in
  this same harness run immediately before the plant goes in.

Two groups of plants:

* the **helper's** -- one inside the claimed region (the operators path) and
  one at the claim's **edge** (the raster path, which AC-2 says is unchanged
  byte for byte). Measured WITHOUT the probe: the reader's own tests stand
  their counterfactual up themselves.
* one **per repaired module** -- a plant that re-breaks that module's own
  repair by putting its page-source seam back the way it was. Measured UNDER
  the probe, because that is the only state in which the repair does
  anything: a repair with no plant is a claim, not a fix.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-329")
PYTHON = Path("/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python")
PROBE = "probe_puzzle_operators"

HELPER = "tests/helpers/pdf_pages.py"
READER_TESTS = "tests/test_book_pdf.py"


@dataclass(frozen=True)
class Mutant:
    name: str
    what: str
    path: str
    old: str
    new: str
    nodes: tuple[str, ...]
    probe: bool = False
    extra: dict = field(default_factory=dict)


MUTANTS: tuple[Mutant, ...] = (
    # ------------------------------------------------------------------
    # The helper. AC-5's pair: inside the claim, and at its edge.
    # ------------------------------------------------------------------
    Mutant(
        name="MUT-1",
        what="INSIDE THE CLAIM (the operators path): the reader returns a "
        "WRONG PAGE for an operators page -- a raster page it already "
        "decoded, handed back where the rasterised stream belongs. Every "
        "assertion about size and about the page carrying ink still passes, "
        "which is why AC-1's mixed-file cell compares the two pages' bytes",
        path=HELPER,
        old="""                images[index] = Image.fromarray(
                    np.asarray(rendered, dtype=np.uint8), mode="L"
                ).convert("RGB")""",
        new="                images[index] = next(iter(images.values()))",
        nodes=(
            f"{READER_TESTS}::TestPdfPagesReader_AnOperatorsPageIsNotAKeyError"
            "::test_an_operators_page_inside_a_file_reads_beside_its_raster_pages",
        ),
    ),
    Mutant(
        name="MUT-2",
        what="AT THE CLAIM'S EDGE (the raster path, which AC-2 says is "
        "unchanged byte for byte): a raster page is handed back as a "
        "CONVERTED COPY instead of the very object. Equal bytes, different "
        "object -- so only an identity assertion can see it, which is why "
        "AC-2 asserts identity and not equality",
        path=HELPER,
        old="    if page_medium_of(page) is RASTER:\n        return page",
        new='    if page_medium_of(page) is RASTER:\n        return page.convert("RGB")',
        nodes=(
            f"{READER_TESTS}::TestPdfPagesReader_ARasterPageIsUnchanged"
            "::test_a_live_raster_page_is_handed_back_as_the_very_same_object",
        ),
    ),
    Mutant(
        name="MUT-3",
        what="THE OTHER EDGE of the raster path: the decoded page's mode "
        "drifts from RGB to L. The page is still the right page and still "
        "carries the right ink; only the byte-for-byte comparison against "
        "the second implementation of CARD-135's reader can see it",
        path=HELPER,
        old="            images[index] = image.convert(\"RGB\")",
        new="            images[index] = image.convert(\"L\")",
        nodes=(
            f"{READER_TESTS}::TestPdfPagesReader_ARasterPageIsUnchanged"
            "::test_every_raster_page_of_a_whole_book_is_unchanged",
        ),
    ),
    Mutant(
        name="MUT-4",
        what="ADR-0039/R2 at the reader: the DPI it cannot establish is "
        "GUESSED instead of refused. `_derived_dpi` falls back to a number, "
        "so an all-operators file is silently rasterised at a scale nobody "
        "named -- the exact shape of a reading in an unnamed domain",
        path=HELPER,
        old="    return derived.pop() if len(derived) == 1 else None",
        new="    return derived.pop() if len(derived) == 1 else 300.0",
        nodes=(
            f"{READER_TESTS}::TestPdfPagesReader_AnOperatorsPageIsNotAKeyError"
            "::test_a_file_whose_dpi_cannot_be_established_is_refused_by_name",
        ),
    ),
    Mutant(
        name="MUT-5",
        what="ADR-0039/R2 at the classification: a page in neither medium is "
        "passed over as raster instead of refused",
        path=HELPER,
        old="""    raise PageMediumRefused(
        f"a book page is a bitmap or a content stream; this one is a "
        f"{type(page).__name__}, whose medium this reader cannot name"
    )""",
        new="    return RASTER",
        nodes=(
            f"{READER_TESTS}::TestPdfPagesReader_AnOperatorsPageIsNotAKeyError"
            "::test_a_page_in_neither_medium_is_a_failure_not_a_silent_pass",
        ),
    ),
    # ------------------------------------------------------------------
    # AC-3's derivation. Two plants: the filter, and the floor.
    # ------------------------------------------------------------------
    Mutant(
        name="MUT-6",
        what="AC-3's population-A FILTER slides from the reader to a mention "
        "-- `pdf_page_count` admitted alongside `pdf_pages`, which is "
        "precisely CARD-309's corrected 'a mention count is not a reader "
        "count' coming back",
        path=READER_TESTS,
        old='_READER_NAME = "pdf_pages"',
        new='_READER_NAME = "pdf_page"  # a prefix: admits pdf_page_count too',
        nodes=(
            f"{READER_TESTS}::TestPdfPagesReader_BothReaderPopulationsAreDerived"
            "::test_population_a_is_the_reader_and_not_a_mention",
            f"{READER_TESTS}::TestPdfPagesReader_BothReaderPopulationsAreDerived"
            "::test_population_a_reproduces_a_second_independent_reading",
        ),
    ),
    Mutant(
        name="MUT-7",
        what="AC-3's indirect half goes dead: the page-consumer walk loses "
        "its closure and falls back to depth 1, which is the state CARD-329 "
        "measured as NOT recognising `page_ink.drawing_of`",
        path=READER_TESTS,
        old="""    for _round in range(len(functions) + 1):
        grown = {
            name
            for name, params, node in functions
            if name not in consumers and hands_a_parameter_on(node, params)
        }
        if not grown:
            break
        consumers |= grown
    return consumers""",
        new="    return consumers",
        nodes=(
            f"{READER_TESTS}::TestPdfPagesReader_BothReaderPopulationsAreDerived"
            "::test_the_files_this_card_does_not_own_are_excluded_by_name_not_missed",
        ),
    ),
    # ------------------------------------------------------------------
    # AC-6: one plant per repaired module, each putting that module's own
    # page-source seam back the way it was. Measured UNDER the probe.
    # ------------------------------------------------------------------
    Mutant(
        name="MUT-8",
        what="AC-6, test_book_cell_size.py: the seam is put back, so the walk "
        "hands the module ContentStream pages again",
        path="tests/test_book_cell_size.py",
        old="""    return interior_images(
        BookPDFGenerator(
            book if book is not None else _book()
        ).interior_pages(puzzles)
    )""",
        new="    return BookPDFGenerator(\n"
        "        book if book is not None else _book()\n"
        "    ).interior_pages(puzzles)",
        nodes=(
            "tests/test_book_cell_size.py::TestBookCellSize_SameGridSizeSameCell"
            "::test_every_twenty_by_twenty_is_drawn_at_the_same_cell",
        ),
        probe=True,
    ),
    Mutant(
        name="MUT-9",
        what="AC-6, test_book_pdf_levels.py: the seam is put back",
        path="tests/test_book_pdf_levels.py",
        old="    return interior_images(BookPDFGenerator(_book()).interior_pages(list(puzzles)))",
        new="    return BookPDFGenerator(_book()).interior_pages(list(puzzles))",
        nodes=(
            "tests/test_book_pdf_levels.py::TestBookPdf_DifficultyOrderWithDividerPerLevel"
            "::test_the_puzzle_section_runs_divider_then_that_levels_puzzles",
        ),
        probe=True,
    ),
    Mutant(
        name="MUT-10",
        what="AC-6, test_book_pdf_two_up.py: the seam is put back",
        path="tests/test_book_pdf_two_up.py",
        old="    return interior_images(BookPDFGenerator(_book()).interior_pages(list(puzzles)))",
        new="    return BookPDFGenerator(_book()).interior_pages(list(puzzles))",
        nodes=(
            "tests/test_book_pdf_two_up.py::TestBookPdf_TwoSmallSameTierNeighboursShareAPage"
            "::test_both_puzzles_print_on_one_page",
        ),
        probe=True,
    ),
    # AC-6, property/test_book_pdf_geometry.py -- and the ONE place this card
    # cannot meet AC-5's "matched green control in the same run", said out
    # loud rather than papered over. All FOUR of that module's node ids are
    # red under the probe both before and after this card's seam edit, so
    # there is no green node in it to be a control: its reds moved from
    # `AttributeError: 'ContentStream' object has no attribute 'size'` to a
    # placed-edge disagreement of 0.254 mm, which ADR-0042 already records as
    # 3 device pixels of mitred corner and already assigns to CARD-322 (an
    # oracle that reads a frame rule's CENTRE rather than its first inked
    # line). The module is EDITED and NOT repaired, and the plant below is
    # the only claim that edit can carry on its own: without the probe the
    # seam is the identity on a raster page, so removing it must change
    # nothing. A DECLARED SURVIVOR -- a plant that reddened here would mean
    # the seam had altered a raster reading, which is AC-2 at module scope.
    Mutant(
        name="MUT-11",
        what="AC-2 at module scope, property/test_book_pdf_geometry.py: the "
        "seam is removed with no probe running. It must SURVIVE -- on a "
        "raster page `interior_images` is the identity, so the module's "
        "readings are byte-unchanged on `main`. See the note above for why "
        "this module has no green node under the probe to plant against",
        path="tests/property/test_book_pdf_geometry.py",
        old="    return interior_images(generator.interior_pages(puzzles))",
        new="    return generator.interior_pages(puzzles)",
        nodes=(
            "tests/property/test_book_pdf_geometry.py"
            "::test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages",
        ),
        probe=False,
        extra={"must": "SURVIVED"},
    ),
    Mutant(
        name="MUT-12",
        what="AC-6, test_book_puzzle_frame.py: the seam is put back",
        path="tests/test_book_puzzle_frame.py",
        old="""    pages = interior_images(
        BookPDFGenerator(_book()).interior_pages(
            [
                _book_puzzle(**UPPER_PUZZLE, puzzle_id="one"),
                _book_puzzle(**LOWER_PUZZLE, puzzle_id="two"),
                _book_puzzle(**SINGLE_PUZZLE, puzzle_id="three"),
            ]
        )
    )""",
        new="""    pages = BookPDFGenerator(_book()).interior_pages(
        [
            _book_puzzle(**UPPER_PUZZLE, puzzle_id="one"),
            _book_puzzle(**LOWER_PUZZLE, puzzle_id="two"),
            _book_puzzle(**SINGLE_PUZZLE, puzzle_id="three"),
        ]
    )""",
        nodes=(
            "tests/test_book_puzzle_frame.py::TestPuzzleFrame_PairIsFramedOnThePrintedPage"
            "::test_both_slots_read_back_as_framed_drawings",
        ),
        probe=True,
    ),
    # ------------------------------------------------------------------
    # The gap CARD-329's own helper opened in this module's placed-edge pin,
    # and the three plants that prove it is closed. `_STREAM_READERS` is the
    # set that decides whether a site under `EDGE_TOLERANCE_MM` has changed
    # medium; `pdf_pages.page_image` hands back PIXELS from a content stream,
    # so a site reading through it crosses the medium with `drawing_of` still
    # in its call set. CARD-318's F-009 in miniature.
    # ------------------------------------------------------------------
    Mutant(
        name="MUT-13",
        what="INSIDE THE CLAIM: a placed-edge site starts reading its page "
        "through `page_image`, i.e. through a poppler raster of a content "
        "stream, while still calling `drawing_of`. Before CARD-329 added the "
        "three pixel-returning readers to `_STREAM_READERS` this plant was "
        "INVISIBLE to the pin",
        path=READER_TESTS,
        old="""    def test_the_drawing_sits_25_45_mm_from_the_left_trim_edge(self):
        page = _mirrored_pages()[FIRST_PUZZLE_PAGE]  # interior page 7, right-hand

        left_mm = _mm(drawing_of(page).left)""",
        new="""    def test_the_drawing_sits_25_45_mm_from_the_left_trim_edge(self):
        page = page_image(_mirrored_pages()[FIRST_PUZZLE_PAGE])

        left_mm = _mm(drawing_of(page).left)""",
        nodes=(
            f"{READER_TESTS}::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_no_site_reads_a_content_stream",
        ),
    ),
    Mutant(
        name="MUT-14",
        what="AT THE CLAIM'S EDGE: a name that reads like a reader and is "
        "defined nowhere joins `_STREAM_READERS`. It forbids nothing, and "
        "without the existence cell the set would rot into a list of words "
        "while still reading as a guard",
        path=READER_TESTS,
        old='            "interior_images",\n            "pdf_pages",',
        new='            "interior_images",\n            "pdf_pages",\n            "rendered_interior_pages",',
        nodes=(
            f"{READER_TESTS}::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_every_stream_reader_named_here_is_a_real_reader",
        ),
    ),
    Mutant(
        name="MUT-15",
        what="the REASON the three pixel-returning readers are in the set "
        "goes false: `page_image` stops crossing the medium and hands an "
        "operators page straight back. A member justified by belief rather "
        "than by behaviour would survive this",
        path=HELPER,
        old="    if page_medium_of(page) is RASTER:\n        return page\n    if pdf_vector.PDFTOPPM is None:",
        new="    if page_medium_of(page) is RASTER:\n        return page\n    return page\n    if pdf_vector.PDFTOPPM is None:",
        nodes=(
            f"{READER_TESTS}::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_the_pixel_returning_stream_readers_really_cross_the_medium",
        ),
    ),
)

COUNT = re.compile(r"(\d+) (passed|failed|error|errors|skipped)")


def sweep() -> None:
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def digest(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def run(nodes: tuple[str, ...], *, probe: bool) -> tuple[int, str]:
    sweep()
    argv = [str(PYTHON), "-m", "pytest", "-o", "addopts=", "-q", "-rs", "--tb=line"]
    if probe:
        argv += ["-p", PROBE]
    argv += list(nodes)
    env = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=str(Path(__file__).resolve().parent),
    )
    done = subprocess.run(
        argv, cwd=str(ROOT), env=env, capture_output=True, text=True
    )
    sweep()
    return done.returncode, done.stdout + done.stderr


def tally(text: str) -> dict[str, int]:
    return {word: int(number) for number, word in COUNT.findall(text)}


def main() -> int:
    sweep()
    rows = []
    only = set(sys.argv[1:])
    for mutant in MUTANTS:
        if only and mutant.name not in only:
            continue
        before = digest(mutant.path)
        text = (ROOT / mutant.path).read_text()
        occurrences = text.count(mutant.old)
        assert occurrences == 1, (
            f"{mutant.name}: the plant's text occurs {occurrences} times in "
            f"{mutant.path}, not once"
        )

        # The matched control: the same nodes, green, right now, in this run.
        code, out = run(mutant.nodes, probe=mutant.probe)
        control = tally(out)
        assert code == 0 and not control.get("failed", 0), (
            f"{mutant.name}: its control node is NOT green before the plant"
            f"\n{out}"
        )
        assert not control.get("skipped", 0), (
            f"{mutant.name}: the control SKIPPED -- a skip keeps the "
            f"collected count and removes the assertion\n{out}"
        )
        assert control.get("passed", 0) == len(mutant.nodes), (
            f"{mutant.name}: control collected {control}, wanted "
            f"{len(mutant.nodes)} node(s)"
        )

        (ROOT / mutant.path).write_text(text.replace(mutant.old, mutant.new, 1))
        try:
            code, out = run(mutant.nodes, probe=mutant.probe)
        finally:
            (ROOT / mutant.path).write_text(text)
            sweep()
        assert digest(mutant.path) == before, (
            f"{mutant.name}: {mutant.path} was not restored"
        )

        counts = tally(out)
        verdict = "KILLED" if counts.get("failed", 0) or code != 0 else "SURVIVED"
        wanted = mutant.extra.get("must", "KILLED")
        reds = [
            line.strip()
            for line in out.splitlines()
            if re.search(r"\.py:\d+: ", line)
        ]
        rows.append((mutant, verdict, control, counts, reds))
        print(f"\n=== {mutant.name}: {verdict}   control={control} plant={counts}")
        print(f"    {mutant.what}")
        for line in reds[:3]:
            print(f"    red at {line}")
        assert verdict == wanted, (
            f"{mutant.name} {verdict} and was declared to {wanted}\n{out}"
        )

    print("\n=== SUMMARY (plant | verdict | control | under probe)")
    for mutant, verdict, control, counts, _reds in rows:
        print(
            f"{mutant.name:7} {verdict:9} control={control.get('passed', 0)} passed "
            f"{control.get('skipped', 0)} skipped | plant={counts} | "
            f"probe={'yes' if mutant.probe else 'no':3} | "
            f"{mutant.nodes[0].split('::')[-1][:58]}"
        )
    sweep()
    return 0


if __name__ == "__main__":
    sys.exit(main())
