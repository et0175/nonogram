"""COMP-003 / CAP-001 — the built-in image library source of a grid (FR-002).

The second grid origin after :mod:`nonogram.sourcing.random_grid`, and
deliberately the same shape of thing: a callable registered in the package's
mode table that returns one grid in the ADR-0012 boundary representation and
takes the run's injected ``random.Random`` (ADR-0015). Everything downstream —
clue derivation, the uniqueness check, POL-001's regenerate loop, export — is
reused unchanged.

A fixed set, not a registry (ADR-0007, guardrail G-5)
-----------------------------------------------------
ADR-0007 rejected the strategy/plugin-registry alternative outright: all the
sourcing modes are known up front and shipped in the same package, so
entry-point discovery would be machinery for a problem this tool does not have.
:data:`_TEMPLATES` is therefore a literal dict of explicitly imported modules —
no directory scan, no ``pkgutil.iter_modules``, no import hook. "Extensible"
means adding a file under ``templates/`` and a row here, and the set of valid
keys stays readable from the source.

A template is a shape, not a bitmap
-----------------------------------
Every template is drawn once at :data:`TEMPLATE_EDGE` cells square and rescaled
to whatever ``--size`` asks for, so ``--size 20 --library-key cat`` yields a
20x20 cat and ``--size 47`` a 47x47 one. The rescale is exact-area coverage
rather than nearest-neighbour: each target cell is mapped back onto the
rectangle of template cells it covers and :func:`coverage` computes what
*fraction* of that rectangle is filled, as an exact integer ratio (no floating
point until the very last comparison, so a cell that is wholly inside or wholly
outside the shape is recognised as such at every size, including the awkward
ones where the ratio is not a whole number).

Nearest-neighbour was the alternative. It is one line shorter and strictly
worse here: at a non-integer ratio it drops whole template rows and columns, so
a 16-cell whisker or a one-cell window frame can vanish entirely at ``--size
11`` while its neighbours double in width. Area coverage degrades those details
into partial cells instead of deleting them — which is also what gives the
retry loop something to work with, below.

What "regenerate" means for a deterministic source (POL-001)
-------------------------------------------------------------
The orchestrator's retry loop discards a candidate whose clues have zero or many
solutions and asks the source for another one. A library template, unlike a
random draw, has nothing obvious to vary: the card is explicit that a retry must
*not* switch key, so re-rendering "cat" at 20x20 would hand the loop the same
grid twenty times, twenty identical solver verdicts, and an abandonment that
took twenty times longer than it needed to.

What genuinely is a free choice — the "tie-break" the card names — is where the
boundary of the shape falls. A partially covered cell is one the rasteriser has
to rule on: it is neither inside nor outside the cat. So :func:`render` takes a
*threshold* on the coverage fraction and :func:`generate` draws it from
:data:`MIN_EDGE_THRESHOLD`..:data:`MAX_EDGE_THRESHOLD` off the injected RNG. A
low threshold renders the shape a touch fatter, a high one a touch leaner; cells
with coverage 0 or 1 are unaffected by construction, because the band is strictly
inside ``(0, 1)``. The cat stays the same cat at every threshold — only its
outline moves — while the clues change enough that a second attempt is a real
second chance at unique solvability rather than a repeat.

Two consequences, stated rather than hidden:

* Library mode is reproducible on the same terms as random mode and no other:
  the same seed and the same ``(key, size)`` reproduce the same grid, because
  the threshold is the only stochastic input and it comes from the run's RNG.
  It is *not* seed-independent — there is no single canonical "cat at 20x20".
  :data:`CANONICAL_THRESHOLD` is the midpoint of the band and exists so callers
  and tests can render the unjittered shape deliberately.
* When ``size`` is an exact whole-number *magnification* of
  :data:`TEMPLATE_EDGE` — 16, 32 and 48 for a 16-cell template within the
  supported 10..50 range — every target cell lands wholly inside one template
  cell, every coverage fraction is 0 or 1, no cell is on the boundary, and the
  threshold has nothing to act on. At those three sizes a retry really is a
  no-op and the loop will spend its budget confirming the same verdict. That is
  a property of a deterministic source, not a bug in the loop, and fixing it
  inside the loop would mean teaching the orchestrator that some sources are
  deterministic — new structure this card is forbidden to add (guardrail G-4)
  and that FR-002 does not ask for. At the other 38 supported sizes, including
  every one where the ratio merely *looks* round (20, 40: 16/20 is 0.8, not a
  whole number of template cells per grid cell), the boundary is genuinely
  jittered and consecutive attempts differ.

Layering (ADR-0007): a capability module. It imports its own package's
``random_grid`` for the shared size rule and ``templates`` for the data, and
``nonogram.errors``; never the adapter, the orchestrator or a sibling
capability.
"""

from __future__ import annotations

import random

from nonogram.errors import UnknownLibraryImage
from nonogram.sourcing import random_grid
from nonogram.sourcing.templates import cat, heart, house, moon

__all__ = [
    "CANONICAL_THRESHOLD",
    "EMPTY_CHAR",
    "FILLED_CHAR",
    "KEYS",
    "MAX_EDGE_THRESHOLD",
    "MIN_EDGE_THRESHOLD",
    "TEMPLATE_EDGE",
    "Template",
    "coverage",
    "generate",
    "parse_art",
    "render",
    "template_for",
]

#: A parsed template: row-major, ``True`` for a filled cell — the same shape as
#: the grids this module returns, at the template's own resolution.
Template = tuple[tuple[bool, ...], ...]

#: The two characters an ``ART`` string is built from (see ``templates``).
FILLED_CHAR = "#"
EMPTY_CHAR = "."

#: Every built-in template is drawn this many cells square. One resolution for
#: all of them so the rescale behaves identically whichever key is asked for,
#: and 16 because it is the smallest square that still holds a recognisable
#: silhouette with one-cell details (a whisker, a window frame) at the 10-cell
#: minimum grid size.
TEMPLATE_EDGE = 16

#: The band POL-001's tie-break is drawn from — see the module docstring. Both
#: ends are strictly inside ``(0, 1)``, which is what guarantees a fully covered
#: cell is always filled and an uncovered one always empty, whatever the draw.
#: The width is a judgement call: wide enough that consecutive attempts differ
#: on a visible number of boundary cells, narrow enough that the silhouette is
#: never mistaken for a different shape.
MIN_EDGE_THRESHOLD = 0.35
MAX_EDGE_THRESHOLD = 0.65

#: The midpoint of that band: "a cell belongs to the shape if the shape covers
#: most of it", the unjittered rendering. Not what :func:`generate` uses — it
#: draws — but the reference a caller renders against when it wants the shape
#: without the tie-break.
CANONICAL_THRESHOLD = 0.5


def parse_art(art: str) -> Template:
    """Parse a ``templates`` ``ART`` string into a :data:`Template`.

    Args:
        art: Lines of :data:`FILLED_CHAR` / :data:`EMPTY_CHAR`. A trailing
            newline is ignored; blank lines and unknown characters are not.

    Returns:
        The parsed shape, row-major.

    Raises:
        ValueError: the art is empty, not rectangular, or contains a character
            that is neither of the two. Not a ``nonogram.errors`` type: the art
            is in-package data this module ships, so a malformed one is a
            packaging bug rather than anything a user did.
    """
    lines = art.splitlines()
    if not lines or not lines[0]:
        raise ValueError("template art is empty")

    widths = {len(line) for line in lines}
    if len(widths) != 1:
        raise ValueError(f"template art is not rectangular; line widths: {sorted(widths)}")

    allowed = {FILLED_CHAR, EMPTY_CHAR}
    stray = sorted(set(art.replace("\n", "")) - allowed)
    if stray:
        raise ValueError(
            f"template art may only use {FILLED_CHAR!r} and {EMPTY_CHAR!r}, "
            f"found {stray}"
        )

    return tuple(tuple(char == FILLED_CHAR for char in line) for line in lines)


#: The library (guardrail G-5): explicit imports, explicit rows, no discovery.
#: Insertion order is the order the keys are advertised in ``--help`` and in the
#: unknown-key error, so it is alphabetical on purpose.
_TEMPLATES: dict[str, Template] = {
    "cat": parse_art(cat.ART),
    "heart": parse_art(heart.ART),
    "house": parse_art(house.ART),
    "moon": parse_art(moon.ART),
}

#: The keys this build can source a grid for, in registration order. The CLI's
#: ``--library-key`` deliberately does *not* mirror these as argparse
#: ``choices``: key membership is a domain rule (AC-006, ADR-0010), so an
#: unknown key must reach :func:`template_for` and come back as
#: ``UnknownLibraryImage``, not as a usage error.
KEYS: tuple[str, ...] = tuple(_TEMPLATES)


def template_for(key: str | None) -> Template:
    """Return the built-in template registered under ``key``.

    Args:
        key: A ``--library-key`` value, e.g. ``"cat"``. ``None`` — the flag
            omitted in library mode — is treated as an unknown key rather than
            defaulting to one, so the message tells the user what to pick from
            instead of silently generating a shape they did not ask for.

    Returns:
        The parsed shape.

    Raises:
        UnknownLibraryImage: no template is registered under ``key`` (AC-006).
            Both messages list :data:`KEYS`, because "dragon is not a thing" is
            only half of what the user needs to know. The missing-key wording is
            separate because ``named None`` would read as a bad key rather than
            as a forgotten flag.
    """
    if key is None:
        raise UnknownLibraryImage(
            "library mode needs a --library-key; "
            f"available keys: {', '.join(KEYS)}"
        )
    try:
        return _TEMPLATES[key]
    except KeyError:
        raise UnknownLibraryImage(
            f"no built-in library image named {key!r}; "
            f"available keys: {', '.join(KEYS)}"
        ) from None


def _axis_overlaps(source_len: int, target_len: int) -> list[list[tuple[int, int]]]:
    """How each target index along one axis maps back onto source indices.

    Returns, for every target index, the ``(source_index, width)`` pairs it
    covers, measured in sub-units where one *source* cell is ``target_len``
    wide. Each target cell therefore covers exactly ``source_len`` sub-units, so
    the widths of one entry always sum to ``source_len`` — which is what lets
    :func:`coverage` stay in exact integers.
    """
    overlaps: list[list[tuple[int, int]]] = []
    for target in range(target_len):
        low = target * source_len
        high = low + source_len
        spans: list[tuple[int, int]] = []
        for source in range(low // target_len, source_len):
            source_low = source * target_len
            if source_low >= high:
                break
            width = min(high, source_low + target_len) - max(low, source_low)
            if width > 0:
                spans.append((source, width))
        overlaps.append(spans)
    return overlaps


def coverage(template: Template, size: int) -> tuple[list[list[int]], int]:
    """How much of each target cell the shape covers, exactly.

    The rescale's arithmetic core, kept separate from :func:`render` so the
    geometry can be reasoned about (and tested) without a threshold in the way.

    Args:
        template: The shape, at its own resolution.
        size: The target square edge length. Assumed validated.

    Returns:
        ``(numerators, denominator)``: ``numerators[row][column]`` over the
        shared ``denominator`` is the filled fraction of the template area that
        target cell maps onto — ``0`` for a cell wholly outside the shape,
        ``denominator`` for one wholly inside, and something between for a cell
        the shape's boundary runs through. Integers throughout: whether a cell
        is *exactly* full or empty is the one judgement no rounding may blur.
    """
    height = len(template)
    width = len(template[0])
    row_overlaps = _axis_overlaps(height, size)
    column_overlaps = _axis_overlaps(width, size)

    numerators = [
        [
            sum(
                row_width * column_width
                for source_row, row_width in row_overlaps[row]
                for source_column, column_width in column_overlaps[column]
                if template[source_row][source_column]
            )
            for column in range(size)
        ]
        for row in range(size)
    ]
    return numerators, height * width


def render(template: Template, size: int, threshold: float) -> list[list[bool]]:
    """Rescale ``template`` to ``size``x``size``, filling at ``threshold``.

    Args:
        template: The shape to draw.
        size: The target square edge length. Assumed validated —
            :func:`generate` validates before calling.
        threshold: The coverage fraction at which a target cell counts as part
            of the shape. Within ``(0, 1)`` a cell the shape wholly covers is
            always filled and one it does not touch is always empty; only the
            boundary moves. Outside that range it would not be a tie-break any
            more, so :func:`generate` never goes there.

    Returns:
        A row-major ``list[list[bool]]``, ``True`` for filled (ADR-0012).
    """
    numerators, denominator = coverage(template, size)
    cut = threshold * denominator
    return [[numerator >= cut for numerator in row] for row in numerators]


def generate(
    key: str | None,
    size: int | None,
    rng: random.Random,
) -> list[list[bool]]:
    """Source one ``size``x``size`` solution grid from the built-in library.

    The mode table's entry point for ``library`` (FR-002, AC-005/AC-006). The
    argument order is the mode's own — key first, because it is what the mode is
    *about*, the way ``density`` leads for the random source — and the RNG comes
    last, as it does for every source.

    Args:
        key: Which built-in image to draw, e.g. ``"cat"``.
        size: Square grid edge length; the same supported range as every other
            mode, since it is a rule about the puzzle and not about the source
            (``random_grid.validate_size``, shared rather than restated).
        rng: The run's random source (ADR-0015). Required, not defaulted, for
            the same reason as in ``random_grid``. Consumed for exactly one
            draw: the boundary threshold this attempt renders at — POL-001's
            "different tie-break, same template" (see the module docstring).

    Returns:
        A row-major ``list[list[bool]]`` of ``size`` rows of ``size`` cells,
        ``True`` for filled (ADR-0012), whose fully-covered cells are the
        template's shape at that size regardless of the draw.

    Raises:
        UnknownLibraryImage: ``key`` names no built-in image (AC-006).
        SizeOutOfRange: ``size`` is outside the supported range.

    Both validations run before the draw, so a rejected request consumes no
    randomness — the same contract ``random_grid.generate`` keeps, and the
    reason a retry loop that swallowed an invalid request could not shift the
    grids a later valid one produces.
    """
    template = template_for(key)
    size = random_grid.validate_size(size)
    return render(template, size, rng.uniform(MIN_EDGE_THRESHOLD, MAX_EDGE_THRESHOLD))
