"""EC(ADR-0022/R2) — PropertyTest_SizeRange_EverySourceModeRejectsSizeOutside10To30.

CON-011 narrowed the supported grid range to 10..30 cells a side. The standing
property that narrowing has to keep true is not "these four hand-picked sizes
are rejected" — it is:

    for **every** source mode, and for **every** integer outside 10..30, the
    request is refused by the one shared pure domain validator before any grid
    is produced; and the CLI adapter enforces no part of that range itself.

Three claims, each of which a per-mode example test can miss:

1. *Every* integer, not four of them. A mode that special-cased 9 and 51 would
   pass the example tests in ``tests/test_sourcing_random.py`` and friends.
   This walks a dense band across both bounds and a seeded sample of far-away
   magnitudes, and asserts a minimum case count so the corpus cannot silently
   shrink (no ``hypothesis`` here — CLAUDE.md's test policy).
2. *The shared validator*, not a per-mode restatement. Each mode's refusal is
   compared against ``random_grid.validate_size``'s own message for the same
   size, byte for byte. A mode that grew its own copy of the bound would still
   raise ``SizeOutOfRange`` and would still pass a test that only checked the
   exception type; it would not produce the same sentence, and it would drift
   the first time the bound moved — which is exactly what this card just did to
   it.
3. *Before any grid is produced.* The rejection is not a post-hoc check on a
   grid that was built anyway: each mode's source is called with arguments that
   would otherwise do real work (a real template key, a real image file), and
   nothing comes back.

The positive half is asserted too, because a validator that rejected
*everything* would satisfy all three claims above. Every integer inside the
range is accepted by every mode and yields a grid of exactly that size.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from nonogram import cli, difficulty, sourcing
from nonogram.errors import SizeOutOfRange
from nonogram.sourcing import random_grid

#: A real image, so image mode's refusal happens before the file is opened
#: rather than because there was nothing to open.
BANDS = Path(__file__).parent.parent / "fixtures" / "bands.png"

#: A real template key, for the same reason on the library side.
LIBRARY_KEY = "cat"

SEED = 20260831

#: The bounds this property is about, named rather than read from
#: ``random_grid`` — a property test that derives its expectation from the
#: constant under test follows that constant anywhere and asserts nothing about
#: where the boundary is. The constants are pinned against these numbers once,
#: below, and everything else is built from the numbers.
MIN_SUPPORTED = 10
MAX_SUPPORTED = 30

#: A dense band across both bounds: every integer from well below the minimum
#: to well above the maximum, so the two transitions are covered exhaustively
#: rather than sampled.
_BAND = range(-20, 81)


def _far_sizes(rng: random.Random) -> list[int]:
    """Magnitudes no hand-written band would reach, drawn reproducibly."""
    return [rng.randint(81, 10_000) for _ in range(60)] + [
        -rng.randint(81, 10_000) for _ in range(60)
    ]


def _corpus() -> tuple[list[int], list[int]]:
    """The (rejected, accepted) integer corpora this property runs over."""
    rng = random.Random(SEED)
    candidates = sorted({*_BAND, *_far_sizes(rng)})
    accepted = [s for s in candidates if MIN_SUPPORTED <= s <= MAX_SUPPORTED]
    rejected = [s for s in candidates if not MIN_SUPPORTED <= s <= MAX_SUPPORTED]
    return rejected, accepted


#: Each mode paired with a callable that takes only a size — the mode's other
#: arguments are the real ones, so a refusal cannot be an artefact of a missing
#: template or an absent file.
def _call_for(mode: str):  # type: ignore[no-untyped-def]
    source = sourcing.for_mode(mode)
    rng = random.Random(SEED)
    match mode:
        case sourcing.RANDOM:
            return lambda size: source(size, 30, rng)
        case sourcing.LIBRARY:
            return lambda size: source(LIBRARY_KEY, size, rng)
        case sourcing.IMAGE:
            return lambda size: source(BANDS, size, rng)
    raise AssertionError(f"unhandled source mode {mode!r}")


def test_the_range_this_property_is_written_around_is_the_one_in_force() -> None:
    """The one place this file reads the constants, so the rest can name numbers."""
    assert (random_grid.MIN_SIZE, random_grid.MAX_SIZE) == (
        MIN_SUPPORTED,
        MAX_SUPPORTED,
    )
    assert set(sourcing.MODES) == {sourcing.RANDOM, sourcing.LIBRARY, sourcing.IMAGE}


def test_difficultys_cell_span_agrees_with_the_source_range() -> None:
    """The range's *second* definition, bound to the first from the test tree.

    ``difficulty.py`` restates the supported range as cell counts —
    ``MIN_SUPPORTED_CELLS = 10 * 10`` and ``MAX_SUPPORTED_CELLS = 30 * 30`` —
    and CARD-023 had to hand-edit the maximum from ``50 * 50`` alongside
    ``random_grid.MAX_SIZE``. Two definitions of one fact, kept in step by
    hand, is a silent-drift hazard: the next range change can move one and
    leave the other, and nothing in ``tests/test_difficulty.py`` would fail
    because it imports difficulty's own constants.

    The duplication cannot be removed. ``difficulty`` (COMP-006) and
    ``random_grid`` (COMP-003) are both capability modules, and ADR-0007
    forbids a lateral import between them — the structural guard in
    ``tests/test_cli.py`` would fail the moment ``difficulty`` imported
    ``random_grid`` to derive the constant. So the binding has to live where
    a cross-boundary import is legal, which is here in the test tree.

    This is not a gate: ``difficulty`` clamps rather than raises, so a
    disagreement would skew difficulty scores rather than admit an
    out-of-range grid. It is exactly the kind of quiet wrongness that a
    property file about the range should refuse to leave unpinned.
    """
    assert difficulty.MIN_SUPPORTED_CELLS == random_grid.MIN_SIZE**2
    assert difficulty.MAX_SUPPORTED_CELLS == random_grid.MAX_SIZE**2


@pytest.mark.parametrize("mode", sourcing.MODES)
def test_every_source_mode_rejects_every_size_outside_ten_to_thirty(mode: str) -> None:
    """Claim 1 and 2: every out-of-range integer, refused by the shared rule."""
    rejected, _ = _corpus()
    call = _call_for(mode)

    assert len(rejected) >= 160, "the rejection corpus has shrunk"

    for size in rejected:
        with pytest.raises(SizeOutOfRange) as raised:
            call(size)

        with pytest.raises(SizeOutOfRange) as shared:
            random_grid.validate_size(size)

        assert str(raised.value) == str(shared.value), (mode, size)


@pytest.mark.parametrize("mode", sourcing.MODES)
def test_every_source_mode_accepts_every_size_inside_ten_to_thirty(mode: str) -> None:
    """The positive half: a validator that refused everything would be useless."""
    _, accepted = _corpus()
    call = _call_for(mode)

    assert accepted == list(range(10, 31)), "the acceptance corpus has shrunk"

    for size in accepted:
        grid = call(size)

        assert len(grid) == size, (mode, size)
        assert {len(row) for row in grid} == {size}, (mode, size)


def test_a_missing_size_is_the_same_domain_error_in_every_mode() -> None:
    """``None`` is the shape an omitted ``--size`` has when it reaches a source.

    It must be a domain error from the shared validator, never a ``TypeError``
    from comparing ``None`` with an int — the failure mode a per-mode
    reimplementation of the bound would be most likely to produce.
    """
    with pytest.raises(SizeOutOfRange) as shared:
        random_grid.validate_size(None)

    for mode in sourcing.MODES:
        with pytest.raises(SizeOutOfRange) as raised:
            _call_for(mode)(None)

        assert str(raised.value) == str(shared.value), mode


def test_the_cli_enforces_no_part_of_the_range_itself() -> None:
    """The other half of ADR-0022/R2: argparse parses, it does not judge.

    Every integer this property refuses inward must still *parse* at the
    adapter and arrive unchanged, so that the domain is what refuses it
    (ADR-0010). A ``type=``/``choices=`` range check in ``cli`` would make the
    tests above pass while moving the decision out of the domain.
    """
    rejected, accepted = _corpus()
    parser = cli.build_parser()

    for size in rejected + accepted:
        args = parser.parse_args(["generate", "--size", str(size)])

        assert args.size == size
