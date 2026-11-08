"""CARD-395: the ``wave_close_only`` marker, applied by a registry and nothing else.

What this is for
----------------
A handful of tests re-prove a standing property over a seeded corpus or a mutant
grid (the book PDF geometry sweeps, the kill-matrix reproductions, the interior
parity sweep, the browser-order runs ...). They cannot go red on a card that did
not touch their subject, and the merge gate paid for them on every card: about
612 s of a quiet 3660 s full run at the very most; replayed over the last 60
merges with the real import graph (a marked test is lifted back whenever a
changed path reaches its subject) the mean saving is about 3.8 minutes per gate,
and the lift rule is not to be weakened to buy more
(``meta/profiling``, CARD-395 Worktree notes). The owner's
ruling (2026-11-07) moves them to the WAVE CLOSE, where the full suite still runs
bare and is the backstop. Only WHEN a test runs moves. What it asserts, how large
its corpus is and whether it exists do not.

How it works, and why it is a registry
--------------------------------------
:data:`REGISTRY` is a data table: per file, the node-id patterns to mark, the
SMOKE ids the gate keeps in that file, the CONTROLS (tests whose job is to fail
on a planted defect) the gate keeps, and the corpus FLOORS found inside the
marked tests. One hook, :func:`pytest_collection_modifyitems`, adds
``pytest.mark.wave_close_only`` to the matching items. It never removes, skips,
reorders or renames an item: a bare ``pytest`` collects and runs exactly what it
ran before, and ``-m "not wave_close_only"`` is the gate's deselection.

The marked test FILES are not edited, on purpose: CARD-390 and CARD-392 edit
three of them, and a decorator in each would collide. The price of a registry is
that a rename in a marked file must be followed here; ``tests/test_wave_close_marker.py``
makes that a red suite rather than a silent un-marking (every pattern must match
a collected node, every marked node must match a pattern).

The hook is a named plugin (``wave_close_marker``) so that ``-p no:wave_close_marker``
shows the suite without it: the standing proof that the marker swallows no test.

Adding an entry
---------------
Mark a test only if (a) its only job is to re-prove a property over a corpus or a
grid, (b) a cheaper sibling stays at the gate as the smoke slice, and (c) every
test in the file that can fail on a planted defect is listed under ``controls``.
Record the floors the marked test asserts; the floor test re-derives them with
``ast`` and reds on a lower or a removed one (CARD-220 AC-4, G-4 of the board).
"""

from __future__ import annotations

import fnmatch
import sys
from typing import NamedTuple

import pytest

#: The marker's name, as registered in ``pyproject.toml``.
MARKER = "wave_close_only"

#: The name this module is registered under (``-p no:wave_close_marker``).
PLUGIN_NAME = "wave_close_marker"


class Entry(NamedTuple):
    """One marked file.

    ``marked``    fnmatch patterns over the node id; what the gate defers.
    ``smoke``     patterns for the tests the gate KEEPS as this file's slice;
                  at least one, each must match a collected, unmarked node.
    ``controls``  patterns for tests that can fail on a planted defect; each
                  must match a collected, unmarked node (may be empty only when
                  the file has none, which the entry then says in ``note``).
    ``floors``    ``{test function: {asserted expression: minimum}}`` for the
                  ``assert <expr> >= N`` lines at the top level of a marked test.
    ``note``      what the marked tests re-prove and why the gate can skip them.
    """

    file: str
    marked: tuple[str, ...]
    smoke: tuple[str, ...]
    controls: tuple[str, ...]
    floors: dict[str, dict[str, int]]
    note: str


#: List 1 -- measured in ``gate-card388-rerun`` (a quiet full run, 3660 s).
LIST_1: tuple[Entry, ...] = (
    Entry(
        file="tests/property/test_book_pdf_geometry.py",
        marked=(
            "tests/property/test_book_pdf_geometry.py::test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages",
            "tests/property/test_book_pdf_geometry.py::test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages",
            "tests/property/test_book_pdf_geometry.py::test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity_pdf_pages",
        ),
        smoke=(
            "tests/property/test_book_pdf_geometry.py::test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_two_up_pages",
        ),
        controls=(
            "tests/property/test_book_pdf_geometry.py::test_a_page_box_one_pixel_off_the_trim_reds_the_trim_assertion",
        ),
        floors={
            "test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages": {
                "checked": 200,
                "at_cap": 20,
                "below_book_floor": 20,
            },
            "test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages": {
                "len(extents)": 120,
                "counted": 150,
                "overflowed": 1,
                "shared_binds": 1,
            },
            "test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity_pdf_pages": {
                "checked": 100,
                "mirrored": 50,
            },
        },
        note="three seeded page-geometry sweeps over the book PDF writer (142.9 + 69.4 + 56.6 s)",
    ),
    Entry(
        file="tests/property/test_book_export_interior.py",
        marked=(
            "tests/property/test_book_export_interior.py::test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage",
        ),
        smoke=(
            "tests/property/test_book_export_interior.py::test_PropertyTest_BookExport_ParityCountsFromTheTitlePage",
        ),
        controls=(
            "tests/property/test_book_export_interior.py::TestParity_TheBoundIsPinnedFromBothSides::*",
            "tests/property/test_book_export_interior.py::TestPlacementBound_IsPinnedFromBothSides::*",
            "tests/property/test_book_export_interior.py::TestInteriorReadings_TheStreamArmIsReached::*",
        ),
        floors={
            "test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage": {
                "len(cases)": 28,
                "seen['two-up page right-hand']": 2,
                "seen['two-up page left-hand']": 2,
                "seen['answer page']": 20,
                "seen['single answer page']": 5,
                "seen['packed answer page']": 1,
                "seen['finalise count with cover']": 4,
                "seen['finalise count without cover']": 4,
                "seen['finalise count with a shared page']": 3,
            },
        },
        note="the interior-without-cover and parity property over a seeded case corpus (95.8 s)",
    ),
    Entry(
        file="tests/property/test_book_pairing.py",
        marked=(
            "tests/property/test_book_pairing.py::test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly_interior_pages",
        ),
        smoke=(
            "tests/property/test_book_pairing.py::test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly",
            "tests/property/test_book_pairing.py::test_PropertyTest_BookPairing_ReserveIsTheBookSOwnScaleNotAPageNumber",
        ),
        controls=(),
        floors={
            "test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly_interior_pages": {
                "books": 15,
                "pages": 40,
                "paired": 8,
                "single": 25,
                "shared_binds": 3,
            },
        },
        note="the rendered-pages arm of the pairing property (23.3 s); the file has no planted-defect test, its two cheap properties are the slice",
    ),
    Entry(
        file="tests/test_kill_matrix.py",
        marked=("tests/test_kill_matrix.py::test_ac7_*",),
        smoke=("tests/test_kill_matrix.py::test_ac1_*",),
        controls=(
            "tests/test_kill_matrix.py::test_ac[1-6]_*",
            "tests/test_kill_matrix.py::test_g[1-5]_*",
        ),
        floors={},
        note="the two reproductions of CARD-257's four-arm grid and the lock-guard file (119.7 + 18.2 s); every other test of the file is the gate's",
    ),
    Entry(
        file="tests/test_browser_fixture_scope.py",
        marked=(
            "tests/test_browser_fixture_scope.py::TestBrowserFixtures_OrderIndependent::test_reverse_order_passes",
            "tests/test_browser_fixture_scope.py::TestBrowserFixtures_OrderIndependent::test_shuffled_order_passes",
        ),
        smoke=(
            "tests/test_browser_fixture_scope.py::TestBrowserFixtures_EveryTestPassesAlone::*",
            "tests/test_browser_fixture_scope.py::TestBrowserFixtures_AFailureDoesNotCascade::*",
        ),
        controls=(
            "tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::*",
            "tests/test_browser_fixture_scope.py::TestBrowserFixtures_OrderIndependent::test_the_probe_file_installs_the_state_the_ordering_is_about",
            "tests/test_browser_fixture_scope.py::TestBrowserFixtures_OrderIndependent::test_the_whole_family_was_run_in_both_orders",
        ),
        floors={},
        note="the probe file run in reverse and in a seeded shuffled order, each a child pytest (23.7 + 21.2 s)",
    ),
    Entry(
        file="tests/test_book_export_interior_cover.py",
        marked=(
            "tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_each_door_axis_arm_catches_a_shape_the_other_misses",
            "tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_every_door_shape_is_read_or_refused_and_never_silent",
            "tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_every_planted_position_shape_is_caught_or_refused",
            "tests/test_book_export_interior_cover.py::TestSourceSegment_TheMemoIsTheStdlibAnswer::test_a_seeded_corpus_of_the_real_module_segments_identically",
        ),
        smoke=(
            "tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_a_planted_bare_literal_is_caught_and_the_derivation_is_not",
        ),
        controls=(
            "tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_the_declared_blind_spots_are_still_silent",
            "tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_no_planted_shape_is_declared_silent",
            "tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_a_refusal_names_the_binding_the_plant_made",
            "tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_each_door_reaching_shape_is_refused_by_the_mechanism_that_refuses_it",
            "tests/test_book_export_interior_cover.py::TestBookExport_TitlePageCountedEverywhere::*",
        ),
        floors={
            "test_a_seeded_corpus_of_the_real_module_segments_identically": {
                "max((node.end_lineno for node in corpus))": 6001,
            },
        },
        note="the door-axis arm grid, the every-shape sweep and the seeded memo corpus (19.3 + 7.7 + 4.0 + 9.7 s); the one-case planted-literal test and the behavioural position tests stay",
    ),
)

#: List 2 -- the admin solver browser sweeps (about 40 to 100 s). Empty on
#: purpose: it is filled only on the owner's yes, in an edit of THIS TABLE alone
#: (CARD-395 item 2). Nothing else needs to change when it is.
LIST_2: tuple[Entry, ...] = ()

REGISTRY: tuple[Entry, ...] = LIST_1 + LIST_2


def matches(nodeid: str, patterns: tuple[str, ...]) -> bool:
    """Does ``nodeid`` match any of the fnmatch ``patterns``?

    A node id may carry ``[param]`` brackets, which fnmatch would read as a
    character class on the PATTERN side only; the patterns above are either
    exact ids or end in ``*``, so a parametrised node matches its stem.
    """
    return any(fnmatch.fnmatchcase(nodeid, pattern) for pattern in patterns)


def marked_patterns() -> tuple[str, ...]:
    """Every pattern in the registry, flattened."""
    return tuple(p for entry in REGISTRY for p in entry.marked)


def is_registered(nodeid: str) -> bool:
    """Is this node id one the registry defers to the wave close?"""
    return matches(nodeid, marked_patterns())


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """Add the marker to every registered item. Never remove or reorder one.

    ``tryfirst`` so the mark is on the item before pytest's own ``-m`` handling
    reads it. The loop only calls ``add_marker``: a bare run is unchanged.
    """
    patterns = marked_patterns()
    for item in items:
        if matches(item.nodeid, patterns):
            item.add_marker(pytest.mark.wave_close_only)



def register(config):
    """Register this module as the plugin :data:`PLUGIN_NAME`.

    Returns ``None`` when the name is blocked (``-p no:wave_close_marker``) or
    this module is already registered under another name (``-p
    tests.wave_close_marker``): the same two cases, and the same reason, as
    ``tests.helpers.undefined_table_report.register``.
    """
    if config.pluginmanager.is_registered(sys.modules[__name__]):
        return None
    return config.pluginmanager.register(sys.modules[__name__], PLUGIN_NAME)
