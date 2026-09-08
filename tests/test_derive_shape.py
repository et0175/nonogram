"""FR-023 / CARD-033 — a bare ``--size N`` derives the other side (ADR-0022/R4).

Acceptance criteria, by the card's test names:

    AC-092  TestDeriveShape_ImageBareSizeDerivesFromInkBoundingBoxRatio
                -> test_image_bare_size_derives_from_the_ink_bounding_box_ratio
    AC-093  TestDeriveShape_CorpusMeanRetentionRisesTo99Percent
                -> test_corpus_mean_retention_rises_to_99_percent
    AC-094  TestDeriveShape_LibraryTemplateRatioAppliesSquareToday
                -> test_library_template_ratio_applies_square_today
    AC-095  TestDeriveShape_RandomSourceStaysSquare
                -> test_random_source_stays_square
    AC-096  TestDeriveShape_ExplicitNxMBypassesDerivation
                -> test_explicit_nxm_bypasses_derivation
    AC-097  TestDeriveShape_WidestAcceptedRatioIsExactlyNOverFiveToOne
                -> test_widest_accepted_ratio_is_exactly_n_over_five_to_one
    AC-098  TestDeriveShape_RefusesBeyondCeilingNamingSmallestWorkingSize
                -> test_refuses_beyond_the_ceiling_naming_the_smallest_working_size

One file for all seven, because they are one rule seen from three source modes
and the interesting comparisons are *between* the modes: "random stays square"
and "a portrait picture gets a portrait grid" only mean something side by side.
The standing properties behind them — every N against every ratio, and the same
rule through all three modes end to end — are in
``tests/property/test_grid_dimensions.py``.

Where the derivation is observed
--------------------------------
At ``orchestrator._resolved_extent``, which is where the request's extent and
the source's own shape meet, rather than through ``orchestrator.generate``.
That is not a convenience: ``generate`` also solves, and whether a particular
picture at a particular extent happens to be uniquely solvable is a different
subject with its own tests, so routing a shape assertion through it would make
the test fail for reasons the criterion is not about. Where a criterion says
something about the *grid* rather than about the extent — AC-092's retention,
AC-097's acceptance — the real conversion or the real crop box is exercised
directly instead.

How "retained" is measured (AC-092, AC-093)
--------------------------------------------
By **pixel area**: the crop box ``sourcing.image.fit_crop_box`` returns for the
derived grid, over the area of the ink bounding box it was taken from. That is
deliberately *not* the ``min(r_src, r_tgt) / max(r_src, r_tgt)`` ratio formula
the production guard uses (``image._retained``): re-deriving the figure with
the function under test would assert nothing about it. Counting pixels is the
independent second implementation CLAUDE.md's test policy asks for, and it is
also what "how much of the picture survives" means to the person who typed the
command. The two agree to within the crop box's integer flooring — a fraction
of a percent at these extents.

The subject is the **ink bounding box** and not the file, throughout. That is
CARD-030's trim (FR-022) and ADR-0022's 2026-09-01 revision, and it is what
makes AC-093's figures the ones the card states: measured against raw file
extents the same 25 pictures give a mean of 91% and 7 under 90%, not 76% and
20. ``pictures/cat.jpg`` is the case that names why — a 580x580 *file* whose
ink box is 330x462, so the file says "square" and the drawing says "portrait".
"""

from __future__ import annotations

import random
from fractions import Fraction
from pathlib import Path

import pytest
from PIL import Image

from nonogram import orchestrator, sourcing
from nonogram.clues import compute_clues
from nonogram.errors import SizeTooSmallForSource
from nonogram.orchestrator import GenerationRequest
from nonogram.sourcing import image, library, random_grid

#: The 25 committed pictures AC-093 is stated over — the same corpus
#: ``tests/test_sourcing_image.py`` measures FR-022's trim against.
PICTURES = Path(__file__).resolve().parent.parent / "pictures"

#: AC-092's worked example. 563x980, and **ink-tight**: its ink bounding box is
#: its whole extent, so the file reading and the ink-box reading coincide and
#: the criterion's 0.574 is unambiguous. Asserted below rather than assumed.
EAGLE = PICTURES / "eagle-silhouette1.jpg"

#: The picture this card exists for. A 580x580 file whose ink box is 330x462,
#: so a square grid centre-crops 28.6% off the top and bottom — which is the
#: cat's ears. Byte-identical to ``silhouette/animals/ania/cat1.jpg``, the file
#: the project owner hit the defect on.
CAT = PICTURES / "cat.jpg"


def _rng() -> random.Random:
    """The argument every source takes; none of the shape reporters draws."""
    return random.Random(20260902)


def _ink_box(path: Path) -> tuple[int, int]:
    """The picture's own extent, as ``(width, height)`` — FR-022's trim."""
    box = image.ink_bounding_box(image.load_greyscale(path))
    return box[2] - box[0], box[3] - box[1]


def _retained_area(path: Path, width: int, height: int) -> Fraction:
    """What fraction of ``path``'s ink box survives the crop into this grid.

    Pixel area of ``fit_crop_box``'s rectangle over pixel area of the ink box
    — see the module docstring for why area and not the ratio formula.
    """
    box_width, box_height = _ink_box(path)
    left, upper, right, lower = image.fit_crop_box(
        box_width, box_height, width, height
    )
    return Fraction((right - left) * (lower - upper), box_width * box_height)


def _solid(directory: Path, width: int, height: int) -> Path:
    """A wholly black ``width`` x ``height`` picture.

    Solid rather than a silhouette on white, so its **ink bounding box is its
    whole extent** and the ratio the derivation reads is exactly the ratio
    written here. A shape inset in white would make the criterion's "long:short
    ratio is exactly 5:1" a claim about the drawing rather than about the file,
    and AC-097's boundary is exact.
    """
    path = directory / f"solid-{width}x{height}.png"
    Image.new("L", (width, height), 0).save(path)
    return path


def _derived(request: GenerationRequest) -> tuple[int, int]:
    """The grid extent ``request`` actually resolves to (FR-018 + FR-023)."""
    return orchestrator._resolved_extent(request)


def _ascii(grid: list[list[bool]]) -> str:
    """The grid as ``#``/``.`` rows — a failure message somebody can read.

    A shape assertion that fails prints two integers; a picture assertion that
    fails should print the picture, because the thing being asserted about the
    cat below is what the drawing looks like.
    """
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)


# --------------------------------------------------------------------------
# AC-092 — TestDeriveShape_ImageBareSizeDerivesFromInkBoundingBoxRatio
# --------------------------------------------------------------------------


def test_image_bare_size_derives_from_the_ink_bounding_box_ratio() -> None:
    """AC-092 (happy): the eagle at a bare ``--size 25`` becomes 14x25.

    ``round(25 * 563/980) = 14``, and 25 lands on the *height* because the
    picture is taller than it is wide — which is the whole of "N is the longer
    side" as a user meets it.

    The retention figures are the criterion's point rather than decoration:
    97% against the 57% the previous square reading kept. 43 points of a
    silhouette is its head and its feet.

    The grid is asserted twice over — the resolved extent, and then the real
    conversion's actual dimensions — because a derivation that produced the
    right pair and a conversion that ignored it would leave the first assertion
    green.
    """
    assert EAGLE.is_file()
    # Ink-tight, so file ratio and ink-box ratio coincide: the criterion's
    # "563x980" is true of both readings and needs no disambiguation.
    assert _ink_box(EAGLE) == (563, 980)
    assert Image.open(EAGLE).size == (563, 980)
    assert round(25 * 563 / 980) == 14

    extent = _derived(GenerationRequest(mode="image", image=EAGLE, width=25))

    assert extent == (14, 25)

    grid = image.generate(EAGLE, *extent, _rng())
    assert len(grid) == 25
    assert {len(row) for row in grid} == {14}

    derived_retention = _retained_area(EAGLE, *extent)
    square_retention = _retained_area(EAGLE, 25, 25)

    assert round(100 * float(derived_retention)) == 97
    assert round(100 * float(square_retention)) == 57
    assert derived_retention > square_retention


# --------------------------------------------------------------------------
# AC-093 — TestDeriveShape_CorpusMeanRetentionRisesTo99Percent
# --------------------------------------------------------------------------


def test_corpus_mean_retention_rises_to_99_percent() -> None:
    """AC-093 (boundary): the same rule over all 25 committed pictures.

    Mean retained content 76% -> 99%, and the count keeping under 90% falls
    from 20 of 25 to zero. The second number is the one with teeth: a mean can
    be carried by a few pictures, whereas "no picture under 90%" is a statement
    about every one of them, and 20 of 25 is what the square reading actually
    does to this collection.

    The corpus size is asserted inside the test so the figures cannot come to
    pass by the corpus shrinking — the same guard
    ``test_the_corpus_the_trim_criteria_are_stated_over_is_the_one_on_disk``
    puts on FR-022's criteria.
    """
    corpus = sorted(path for path in PICTURES.iterdir() if path.is_file())

    assert len(corpus) == 25, [path.name for path in corpus]

    square = [_retained_area(path, 25, 25) for path in corpus]
    derived = [
        _retained_area(
            path, *_derived(GenerationRequest(mode="image", image=path, width=25))
        )
        for path in corpus
    ]

    assert round(100 * float(sum(square) / len(square))) == 76
    assert round(100 * float(sum(derived) / len(derived))) == 99

    threshold = Fraction(9, 10)
    assert sum(1 for kept in square if kept < threshold) == 20
    assert sum(1 for kept in derived if kept < threshold) == 0

    # Nothing gets worse: the mean rising is compatible with a picture losing
    # ground, and no picture in this corpus does.
    assert all(
        after >= before for before, after in zip(square, derived, strict=True)
    )


# --------------------------------------------------------------------------
# AC-094 — TestDeriveShape_LibraryTemplateRatioAppliesSquareToday
# --------------------------------------------------------------------------


def test_library_template_ratio_applies_square_today() -> None:
    """AC-094 (boundary): ``cat`` at a bare ``--size 25`` is 25x25.

    And the criterion's "because" is what is asserted, not just the pair: the
    template's own ratio is 1:1 *today*. So this checks that the answer comes
    from :func:`library.source_shape` reading the parsed art — vary the art and
    the derived grid follows, with nothing in ``random_grid.derive_extent``
    knowing that a library exists (CARD-033 guardrail G-2). A square answer
    that came from a ``mode == LIBRARY`` branch would pass the first assertion
    and fail the last.
    """
    assert library.source_shape("cat") == (16, 16)
    assert {library.source_shape(key) for key in library.KEYS} == {(16, 16)}

    assert _derived(
        GenerationRequest(mode="library", library_key="cat", width=25)
    ) == (25, 25)

    # The rule, not the data: a 2:1 template would derive 25x12 through the very
    # same call, so "square today" is a fact about ``templates/`` and not about
    # the derivation. (12 and not 13 because ``round(25 * 16/32)`` is
    # ``round(12.5)`` and Python breaks that tie to even — pinned deliberately
    # here and again in
    # ``PropertyTest_DeriveShape_ShortSideIsRoundedRatioClampedAtMinOrRefused``,
    # since the tie is exactly where a reimplementation would silently disagree.)
    assert random_grid.derive_extent(25, None, 32, 16) == (25, 12)
    assert random_grid.derive_extent(25, None, 16, 32) == (12, 25)


# --------------------------------------------------------------------------
# AC-095 — TestDeriveShape_RandomSourceStaysSquare
# --------------------------------------------------------------------------


def test_random_source_stays_square() -> None:
    """AC-095 (happy): a random request at a bare ``--size 20`` is 20x20.

    "Since a random source has no shape of its own" is the criterion's reason,
    and it is expressible: :func:`random_grid.source_shape` answers the same
    question the other two modes answer, and answers it ``(1, 1)``. Random is
    not special-cased in the derivation — it is a row in ``sourcing._SHAPES``
    like the others (guardrail G-2), which is why the grid comes back square
    without ``derive_extent`` ever testing which mode it is serving.
    """
    assert random_grid.source_shape() == (1, 1)

    assert _derived(GenerationRequest(mode="random", width=20, density=30)) == (20, 20)

    # End to end, so the extent really reaches the source: 20 rows of 20. The
    # seed is pinned the way ``tests/test_orchestrator.py`` pins one — 8 is the
    # first that produces a uniquely-solvable 20x20 at 45%, in four attempts;
    # re-pin by re-running the sweep rather than deleting the assertion.
    puzzle = orchestrator.generate(
        GenerationRequest(mode="random", width=20, density=45, seed=8)
    )
    assert puzzle.extent == (20, 20)
    assert puzzle.grid is not None
    assert len(puzzle.grid) == 20
    assert {len(row) for row in puzzle.grid} == {20}


# --------------------------------------------------------------------------
# AC-096 — TestDeriveShape_ExplicitNxMBypassesDerivation
# --------------------------------------------------------------------------


def test_explicit_nxm_bypasses_derivation() -> None:
    """AC-096 (boundary): ``--size 15x30`` is 15 by 30, derivation or not.

    Asserted against a source whose own shape is *different* from the request —
    ``cat.jpg``'s ink box is 330x462, so the derivation would have produced
    something else — because a fully-stated extent is the case where the two
    could disagree, and only disagreement can show which one won.

    The second half is the one FR-023 actually promises and the first cannot
    show: an explicit extent never asks the source for its shape at all. Pinned
    by making the shape reporter explode; a passing test therefore proves it was
    not consulted, rather than that its answer was ignored.
    """
    request = GenerationRequest(mode="image", image=CAT, width=15, height=30)

    assert _ink_box(CAT) == (330, 462)
    assert _derived(request) == (15, 30)
    # ...and the derivation would not have chosen that.
    assert _derived(GenerationRequest(mode="image", image=CAT, width=15)) != (15, 30)

    def explode(*arguments: object) -> tuple[int, int]:
        raise AssertionError(
            "an explicit --size WxH must not consult the source's shape"
        )

    original = sourcing._SHAPES[sourcing.IMAGE]
    sourcing._SHAPES[sourcing.IMAGE] = explode
    try:
        assert _derived(request) == (15, 30)
    finally:
        sourcing._SHAPES[sourcing.IMAGE] = original


# --------------------------------------------------------------------------
# AC-097 — TestDeriveShape_WidestAcceptedRatioIsExactlyNOverFiveToOne
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stated", "ratio"),
    [(10, 2), (20, 4), (30, 6)],
    ids=["size-10-accepts-2to1", "size-20-accepts-4to1", "size-30-accepts-6to1"],
)
def test_widest_accepted_ratio_is_exactly_n_over_five_to_one(
    stated: int, ratio: int, tmp_path: Path
) -> None:
    """AC-097 (boundary): ``N/5 : 1`` is reached exactly, and accepted.

    The ceiling is exact arithmetic, not a sampled figure. At the clamp the
    grid's ratio is ``MIN_SIZE : N``, and FR-021's half-retention rule against a
    source of ratio ``short : long`` is ``2 * N * short >= MIN_SIZE * long`` —
    which rearranges to ``long : short <= N/5``. So 2:1 at ``--size 10``, 4:1 at
    20, 6:1 at 30.

    Two things are asserted at the boundary, and the second is what makes it a
    boundary rather than a sample: the short side lands **exactly** on
    ``MIN_SIZE``, the clamp reached and not overshot; and one pixel more
    elongated is refused. A rule that accepted the whole neighbourhood would
    pass the first assertion alone.

    Also asserted: the grid this produces really is acceptable to FR-021's own
    guard, unchanged and on its own ink-box terms (guardrail G-4). This card
    chooses which shape to request; it does not touch how one is judged.
    """
    source = _solid(tmp_path, 100, 100 * ratio)

    extent = _derived(GenerationRequest(mode="image", image=source, width=stated))

    assert extent == (random_grid.MIN_SIZE, stated)
    assert min(extent) == random_grid.MIN_SIZE
    # FR-021's guard, called directly on the ink box and the derived grid.
    image.validate_aspect_ratio(100, 100 * ratio, *extent)
    # ...and the conversion really runs at that extent.
    grid = image.generate(source, *extent, _rng())
    assert len(grid) == stated
    assert {len(row) for row in grid} == {random_grid.MIN_SIZE}

    # One pixel past the boundary is the other side of it.
    beyond = _solid(tmp_path, 1000, 1000 * ratio + 1)
    with pytest.raises(SizeTooSmallForSource):
        _derived(GenerationRequest(mode="image", image=beyond, width=stated))


# --------------------------------------------------------------------------
# AC-098 — TestDeriveShape_RefusesBeyondCeilingNamingSmallestWorkingSize
# --------------------------------------------------------------------------


def test_refuses_beyond_the_ceiling_naming_the_smallest_working_size(
    tmp_path: Path,
) -> None:
    """AC-098 (negative): 5:1 at ``--size 15`` is refused, and says ``--size 25``.

    The refusal is the interesting half of this card. What it has to do:

    * refuse rather than silently hand back a grid that stopped following the
      source — the clamp is where the source can no longer be tracked, and a
      quiet clamp is exactly the silent quality loss FR-021 exists to end;
    * name the smallest ``--size N`` that *would* take this picture. 25, and it
      is arithmetic rather than advice: ``5 * long/short`` for a 5:1 source;
    * **not** tell the user to crop the picture. That is FR-021's remedy for a
      different problem, and here it is wrong — cropping a 5:1 silhouette to fit
      a small puzzle throws away the thing the user wanted a puzzle of;
    * carry the counter-intuitive consequence out loud, because a user who is
      told to ask for a *bigger* puzzle after being refused a smaller one will
      otherwise assume the tool has it backwards.
    """
    source = _solid(tmp_path, 100, 500)

    with pytest.raises(SizeTooSmallForSource) as raised:
        _derived(GenerationRequest(mode="image", image=source, width=15))

    message = str(raised.value)

    assert "--size 25" in message
    assert "or larger" in message
    assert "LARGER puzzle accepts a picture that a smaller one refuses" in message
    # FR-021's advice, and pointedly absent: AC-077 requires that sentence of
    # the aspect guard and AC-098 requires its absence here.
    assert "Crop the picture yourself" not in message
    assert "Cropping the picture is not what fixes this" in message

    # The named size is not just plausible — it works, and 24 does not, so the
    # message names the *smallest* rather than a safe overestimate.
    assert _derived(GenerationRequest(mode="image", image=source, width=25)) == (10, 25)
    with pytest.raises(SizeTooSmallForSource):
        _derived(GenerationRequest(mode="image", image=source, width=24))


def test_a_refusal_no_supported_size_can_lift_says_so_instead(tmp_path: Path) -> None:
    """The other arm of the same refusal, which no AC names but a user will hit.

    Past ``MAX_SIZE/5 : 1`` — 6:1 — no supported ``--size`` follows the source,
    so there is no size to name. Telling such a user to "ask for --size None or
    larger" would be worse than useless, and here cropping genuinely *is* the
    remedy, so this arm says so. Pinned because it is the branch a reader of
    AC-098 would not think to check.
    """
    source = _solid(tmp_path, 100, 1000)

    with pytest.raises(SizeTooSmallForSource) as raised:
        _derived(GenerationRequest(mode="image", image=source, width=30))

    message = str(raised.value)

    assert "No supported --size can follow it" in message
    assert "even --size 30" in message
    assert "6:1" in message
    assert "or larger" not in message


# --------------------------------------------------------------------------
# The regression this card was cut for
# --------------------------------------------------------------------------


def test_the_cats_ears_survive_a_bare_size_25() -> None:
    """The defect in one assertion: a bare ``--size 25`` keeps the cat's ears.

    ``pictures/cat.jpg`` (byte-identical to the owner's
    ``silhouette/animals/ania/cat1.jpg``) is a 580x580 file whose ink box is
    330x462. Under the square reading a 25x25 grid centre-crops the ink box's
    long axis down to 330 pixels — 28.6% off the top and bottom — and the top of
    that crop is where the ears are. The derivation asks for 18x25 instead and
    discards 0.9%.

    Asserted on the *converted grid* rather than on the extent, because the
    extent is what the criteria above already cover and the ears are not a
    number. What *is* a number: an ear is a separate peak, so the top row of a
    grid that contains the ears has **two** runs of ink with paper between them,
    while a grid whose crop started below them has one — the flat top of a head
    cut through. Run-length encoding the top row is therefore the whole check,
    and it is the same encoding the puzzle's own clues are built from.

    Rendered, for the record (``#`` filled, ``.`` empty):

    ::

        derived 18x25, row 0     square 25x25, row 0
        ....##.........##.       .......################..
             ^^         ^^              one slab: no ears

    The square grid's first row is a single 16-cell run because the centred crop
    of a 330x462 ink box to 1:1 keeps rows 66..396 of it, and the ears are above
    that. Nothing was faint or dithered away — the pixels were discarded before
    the dither ran.
    """
    assert _ink_box(CAT) == (330, 462)

    derived = _derived(GenerationRequest(mode="image", image=CAT, width=25))
    assert derived == (18, 25)
    assert round(100 * float(_retained_area(CAT, *derived))) == 99

    derived_grid = image.generate(CAT, *derived, _rng())
    square_grid = image.generate(CAT, 25, 25, _rng())

    assert len(compute_clues(derived_grid).rows[0]) == 2, _ascii(derived_grid)
    assert len(compute_clues(square_grid).rows[0]) == 1, _ascii(square_grid)
