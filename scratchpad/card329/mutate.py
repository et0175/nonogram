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


PIN_CLASS = "TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"

#: The two cells of the pin that a medium crossing written one frame in has
#: to red: the raster-oracle requirement (the site reads no page through
#: ``drawing_of``) and the closed deny (its page source reaches
#: ``interior_images`` -> ``page_image`` -> ``rendered_page``).
PIN_DENY_NODES = (
    f"{READER_TESTS}::{PIN_CLASS}"
    "::test_every_site_reads_its_page_through_the_raster_ink_oracle",
    f"{READER_TESTS}::{PIN_CLASS}"
    "::test_no_site_reaches_a_stream_reader_through_a_helper_either",
)

#: A module-level anchor, unique in the file, that the planted site is
#: inserted in front of. Located by text like every other plant here.
PLANT_ANCHOR = "class TestEdgeOffset_TheAdrRecordsTheCanonicalMedium:"


def planted_site(klass: str, bare: str) -> str:
    """A new placed-edge site whose page source crosses the medium **one
    frame in** -- the house one-line seam this card standardised across five
    modules and instructed CARD-322 to apply to nine more.

    The site's own body names no stream reader, so the depth-0 deny passes it
    (that is MUT-16b, a declared survivor); the crossing is in the
    module-level helper it calls.

    Two deliberate choices about the names, both so the plant cannot pollute
    anything while it is held:

    * ``klass`` is **not** ``Test*``-prefixed, so pytest collects nothing new
      and the node-id census is unchanged while the plant is in. The pin
      derives its sites with ``ast`` and filters on the presence of
      ``EDGE_TOLERANCE_MM``, never on a collection prefix, so the code path
      under measurement is identical;
    * ``bare`` is always a function name that **already exists** in
      ``tests/``. The validator's check-ref search is a TEXT search over
      tracked files, so an invented test-like symbol spelled in this file
      could resolve a ref that nothing in ``tests/`` defines
      (``ref_pollution_check.py`` is the control, and it reds on one).
      The matched pair's only variable is therefore whether that existing
      name is **registered** as an exemption, which is exactly the hazard.
    """
    return f'''def _plant_page_source(generator, puzzles):
    """CARD-329 plant only: the one-line seam at a page-source helper."""
    return interior_images(generator.interior_pages(puzzles))


class {klass}:
    def {bare}(self) -> None:
        source = _plant_page_source
        assert 0.0 <= EDGE_TOLERANCE_MM, (source, EDGE_TOLERANCE_MM)


{PLANT_ANCHOR}'''


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
        old="    if page_medium_of(page) == RASTER:\n        return page",
        new='    if page_medium_of(page) == RASTER:\n        return page.convert("RGB")',
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
        "defined nowhere joins the medium-blind register. Since cycle 1's "
        "F-002 the crossing set is DERIVED, so a dead name can no longer "
        "enter it -- the exemption register is now the only hand-written "
        "half, and a dead entry there exempts a reader that does not exist "
        "while reading as a considered decision",
        path=READER_TESTS,
        old='            "pdf_page_count",\n            "same_page",',
        new='            "pdf_page_count",\n            "same_page",\n            "rendered_interior_pages",',
        nodes=(
            f"{READER_TESTS}::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_every_public_reader_of_the_two_owners_is_classified",
        ),
    ),
    Mutant(
        name="MUT-15",
        what="the REASON the three pixel-returning readers are in the set "
        "goes false: `page_image` stops crossing the medium and hands an "
        "operators page straight back. A member justified by belief rather "
        "than by behaviour would survive this",
        path=HELPER,
        old="    if page_medium_of(page) == RASTER:\n        return page\n    if pdf_vector.PDFTOPPM is None:",
        new="    if page_medium_of(page) == RASTER:\n        return page\n    return page\n    if pdf_vector.PDFTOPPM is None:",
        nodes=(
            f"{READER_TESTS}::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_the_pixel_returning_stream_readers_really_cross_the_medium",
        ),
    ),
    # ------------------------------------------------------------------
    # Cycle 1's fix round. F-001, F-002 and F-003 each get a plant that
    # SURVIVED before the fix and has to be killed by it.
    # ------------------------------------------------------------------
    Mutant(
        name="MUT-16",
        what="F-001, THE PLANT THE REVIEW FIRED AND WATCHED SURVIVE: the "
        "same medium crossing as MUT-13, written one frame in at this "
        "module's own page-source helper `_interior` -- which is exactly the "
        "one-line seam this card standardised across five modules and "
        "exactly what CARD-322 is instructed to apply to nine more. Closed "
        "at depth 0 the pin could not see it",
        path=READER_TESTS,
        old="""def _interior(book: Book, puzzles: list[dict]) -> list:
    \"\"\"The book's interior pages in print order; ``pages[n - 1]`` is page ``n``.\"\"\"
    return BookPDFGenerator(book).interior_pages(puzzles)""",
        new="""def _interior(book: Book, puzzles: list[dict]) -> list:
    \"\"\"The book's interior pages in print order; ``pages[n - 1]`` is page ``n``.\"\"\"
    return interior_images(BookPDFGenerator(book).interior_pages(puzzles))""",
        nodes=(
            f"{READER_TESTS}::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_no_site_reaches_a_stream_reader_through_a_helper_either",
        ),
    ),
    Mutant(
        name="MUT-16b",
        what="F-001's control in the other direction: the SAME plant against "
        "the depth-0 cell, which must still SURVIVE it -- otherwise the new "
        "closed cell is measuring nothing the old one did not, and the two "
        "would be one assertion written twice",
        path=READER_TESTS,
        old="""def _interior(book: Book, puzzles: list[dict]) -> list:
    \"\"\"The book's interior pages in print order; ``pages[n - 1]`` is page ``n``.\"\"\"
    return BookPDFGenerator(book).interior_pages(puzzles)""",
        new="""def _interior(book: Book, puzzles: list[dict]) -> list:
    \"\"\"The book's interior pages in print order; ``pages[n - 1]`` is page ``n``.\"\"\"
    return interior_images(BookPDFGenerator(book).interior_pages(puzzles))""",
        nodes=(
            f"{READER_TESTS}::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_no_site_reads_a_content_stream",
        ),
        extra={"must": "SURVIVED"},
    ),
    Mutant(
        name="MUT-17",
        what="F-002: the derivation is replaced by the hand-written set this "
        "round retired -- the exact seven names, no more. `rendered_page`, "
        "the stream reader that returns pixels and the one `page_image` "
        "itself delegates to, drops out, and the completeness control is "
        "what notices. Under the old existence-only control this was the "
        "shipped state",
        path=READER_TESTS,
        old="        return frozenset(crossing & public)",
        new="""        return frozenset(
            {
                "content_streams",
                "operator_tokens",
                "operator_tally",
                "page_media",
                "page_image",
                "interior_images",
                "pdf_pages",
            }
        )""",
        nodes=(
            f"{READER_TESTS}::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"
            "::test_every_public_reader_of_the_two_owners_is_classified",
        ),
    ),
    Mutant(
        name="MUT-18",
        what="F-003: the poppler guard in `page_image` stops guarding, so a "
        "host without the engine reads a page anyway instead of saying the "
        "reading is MISSING (ADR-0038/R8). Nothing in the tree set "
        "`PDFTOPPM` to None before this round, so no control could reach "
        "this branch at all",
        path=HELPER,
        # The leading newline pins the indentation: `pdf_pages`' own copy of
        # this guard sits four spaces further in, and without it the shorter
        # text would match inside that one too.
        old="\n    if pdf_vector.PDFTOPPM is None:\n        raise PageMediumRefused(",
        new="\n    if False:\n        raise PageMediumRefused(",
        nodes=(
            f"{READER_TESTS}::TestPdfPagesReader_AnOperatorsPageIsNotAKeyError"
            "::test_a_missing_poppler_is_a_missing_reading_and_never_a_skip",
        ),
    ),
    Mutant(
        name="MUT-19",
        what="F-003's other branch: raster pages at DISAGREEING DPIs settle "
        "a scale anyway -- `_derived_dpi` pops one of the two rather than "
        "refusing, which is a reading in a domain nobody named. MUT-4 covers "
        "the zero-raster-page arm; this is the arm the docstring and the "
        "exception text both state and nothing drove",
        path=HELPER,
        old="    return derived.pop() if len(derived) == 1 else None",
        new="    return derived.pop() if derived else None",
        nodes=(
            f"{READER_TESTS}::TestPdfPagesReader_AnOperatorsPageIsNotAKeyError"
            "::test_raster_pages_at_disagreeing_dpis_are_refused_not_averaged",
            f"{READER_TESTS}::TestPdfPagesReader_AnOperatorsPageIsNotAKeyError"
            "::test_the_dpi_derivation_itself_answers_none_only_when_it_must",
        ),
    ),
    # ------------------------------------------------------------------
    # Cycle 2's F-008: the exemption register's lookup. The matched pair
    # is MUT-20/MUT-21 -- the SAME planted site and the SAME one-frame-in
    # helper, differing only in the planted test's bare name. Under the
    # pre-fix lookup (`self._bare(name) in self._BOUND_ONLY_SITES`, with a
    # bare register) MUT-20 left all five pin cells green; both must red
    # now, because the register is matched on the whole key.
    # ------------------------------------------------------------------
    Mutant(
        name="MUT-20",
        what="F-008: the house one-line seam planted at a new placed-edge "
        "site whose BARE name collides with a registered exemption in a "
        "DIFFERENT class. The qualified keys differ, so the collapse cell "
        "sees nothing; under the pre-fix bare lookup this site was exempt "
        "from the closed deny AND the raster-oracle requirement with "
        "nothing added to the register",
        path=READER_TESTS,
        old=PLANT_ANCHOR,
        new=planted_site(
            "PlantedSiteWhoseBareNameIsRegistered",
            "test_the_two_media_ink_differs_by_one_device_pixel_not_two",
        ),
        nodes=PIN_DENY_NODES,
    ),
    Mutant(
        name="MUT-21",
        what="F-008's matched control: the IDENTICAL site and helper under a "
        "bare name that also already exists in this module but is NOT "
        "registered. Caught before the fix too -- the pair isolates the "
        "lookup as the variable, because registration is the only thing "
        "that differs between MUT-20 and MUT-21",
        path=READER_TESTS,
        old=PLANT_ANCHOR,
        new=planted_site(
            "PlantedSiteWhoseBareNameIsNotRegistered",
            "test_the_drawing_sits_25_45_mm_from_the_left_trim_edge",
        ),
        nodes=PIN_DENY_NODES,
    ),
    Mutant(
        name="MUT-22",
        what="F-008's lookup degrades back: the raster-oracle cell matches "
        "the register through `_bare` again. That is the exact regression "
        "that opened the hole, and it fails silently in the permissive "
        "direction, so the control resolves it by `ast` rather than "
        "trusting a docstring",
        path=READER_TESTS,
        old="        for name, readers in self._sites().items():\n"
        "            if name in self._BOUND_ONLY_SITES:",
        new="        for name, readers in self._sites().items():\n"
        "            if self._bare(name) in self._BOUND_ONLY_SITES:",
        nodes=(
            f"{READER_TESTS}::{PIN_CLASS}"
            "::test_the_exemption_lookup_does_not_strip_the_class",
        ),
    ),
    Mutant(
        name="MUT-23",
        what="F-008's vacuity arm: the register collapses to an empty "
        "frozenset. Every subset assertion the existence cell had is "
        "satisfied by the empty set, so before the non-emptiness assertion "
        "a collapsed register passed while exempting nothing",
        path=READER_TESTS,
        old="""    _BOUND_ONLY_SITES = frozenset(
        {
            "TestEdgeOffset_ATolerenceChangeCarriesItsExemption"
            "::test_the_bound_is_the_figure_the_criteria_state_and_nothing_is_exempt",
            "TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels"
            "::test_the_two_media_ink_differs_by_one_device_pixel_not_two",
            "TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels"
            "::test_the_drawings_own_edge_is_where_the_media_pass_the_tolerance",
        }
    )""",
        new="    _BOUND_ONLY_SITES = frozenset()",
        nodes=(
            f"{READER_TESTS}::{PIN_CLASS}"
            "::test_the_exemption_list_names_only_sites_that_exist",
            f"{READER_TESTS}::{PIN_CLASS}"
            "::test_the_exemption_lookup_does_not_strip_the_class",
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
