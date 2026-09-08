"""COMP-003 — grid sourcing: the mode-dispatch surface over CAP-001 (FR-001).

A solution grid can be sourced three ways — drawn at random (FR-001/FR-004),
taken from the built-in image library (FR-002, CARD-008) or converted from an
uploaded image (FR-003, CARD-015). All three exist now, and each of the last
two landed as one row in :data:`_SOURCES` rather than as a reshaped dispatch,
which is what the split between "return the callable" and "assemble its
arguments" was for. The table is closed: the model names no fourth mode.

:func:`for_mode` returns the *sourcing callable* rather than calling it,
because the three modes do not share a parameter list — random takes a density,
library takes a key, image takes a path — and collapsing them behind one
signature now would either invent parameters the later cards have to change or
force a ``**kwargs`` surface with no contract at all. Two things every mode
*does* share sit in the same place in all three signatures: the grid's
``(width, height)`` extent (ADR-0022/R1, never one scalar) directly after the
mode's own leading argument, and the injected ``random.Random`` (ADR-0015)
last.

Since FR-023 (CARD-033) there is a **second** per-mode table beside the first:
:func:`shape_for_mode` returns the callable that reports a mode's *own shape*,
which is what a bare ``--size N`` is completed from before any grid is sourced.
Two tables rather than one wider row, because the two questions are asked at
different moments and with different arguments — a shape is a property of the
source alone, so it takes the mode's leading argument and no extent, whereas a
grid source takes the extent the shape helped decide.

Layering (ADR-0007): this is a capability package, so it imports only its own
submodules and ``nonogram.errors`` — never the adapter, the orchestrator or a
sibling capability.
"""

from __future__ import annotations

from collections.abc import Callable

from nonogram.sourcing import image, library, random_grid

__all__ = [
    "IMAGE",
    "LIBRARY",
    "MODES",
    "RANDOM",
    "GridSource",
    "SourceShape",
    "for_mode",
    "shape_for_mode",
]

#: The ``--mode`` value each source is selected by. The CLI's argparse
#: ``choices`` mirrors these strings (syntactic rejection of an unknown mode
#: happens there, ADR-0010); this table is the domain-side registry.
RANDOM = "random"
LIBRARY = "library"
IMAGE = "image"

#: What every mode's entry point looks like from the dispatcher's side: it
#: returns a grid in the ADR-0012 boundary representation. Arguments are
#: deliberately unconstrained — see the module docstring.
GridSource = Callable[..., list[list[bool]]]

_SOURCES: dict[str, GridSource] = {
    RANDOM: random_grid.generate,
    LIBRARY: library.generate,
    IMAGE: image.generate,
}

#: The modes this build can source a grid for, in registration order.
MODES: tuple[str, ...] = tuple(_SOURCES)

#: What every mode's *shape* entry point looks like (FR-023): it reports the
#: source's own extent as a ``(width, height)`` pixel (or template-cell) pair,
#: of which only the ratio is read. Arguments are the mode's own, as with
#: :data:`GridSource` — see :func:`shape_for_mode`.
SourceShape = Callable[..., tuple[int, int]]

#: The second per-mode table, deliberately alongside the first rather than
#: folded into it. A bare ``--size N`` is completed from "the source's own
#: shape" (ADR-0022/R4), which every mode has to be able to answer *before* a
#: grid is sourced — the orchestrator resolves the extent, then asks for the
#: grid at that extent. Random's answer being a square is a row in this table
#: like any other, not a branch in the derivation, which is what keeps "random
#: stays N x N" and "a rectangular template later just works" the same rule
#: (CARD-033 guardrail G-2).
_SHAPES: dict[str, SourceShape] = {
    RANDOM: random_grid.source_shape,
    LIBRARY: library.source_shape,
    IMAGE: image.source_shape,
}


def for_mode(mode: str) -> GridSource:
    """Return the grid source registered for ``mode``.

    Args:
        mode: A ``--mode`` value, e.g. ``"random"``.

    Returns:
        The callable that sources a grid for that mode. Call it with the
        mode's own arguments — ``(width, height, density, rng)`` for
        :data:`RANDOM`, ``(key, width, height, rng)`` for :data:`LIBRARY`,
        ``(path, width, height, rng)`` for :data:`IMAGE`. The orchestrator
        assembles that list per mode at its own call site, where an
        unregistered *argument list* is refused as loudly as an unregistered
        mode is here.

    Raises:
        ValueError: ``mode`` is not registered. Deliberately *not* a
            ``nonogram.errors`` type: a user typing an unsupported mode is
            rejected by argparse's ``choices`` at the adapter, so a bad mode
            arriving here is a wiring bug inside the pipeline, not invalid
            user input to be mapped onto an exit code.
    """
    try:
        return _SOURCES[mode]
    except KeyError:
        raise ValueError(
            f"unknown grid sourcing mode {mode!r}; known modes: "
            f"{', '.join(MODES)}"
        ) from None


def shape_for_mode(mode: str) -> SourceShape:
    """Return the source-shape reporter registered for ``mode`` (FR-023).

    The same shape of dispatcher as :func:`for_mode`, over :data:`_SHAPES`, and
    with the same reason for returning the callable rather than calling it: the
    three modes do not share a parameter list. Random takes nothing (it has no
    shape of its own), library takes the key, image takes the path — the mode's
    own leading argument in each case, and *only* that, since a shape is a
    property of the source and not of the grid being asked for. The orchestrator
    assembles the argument list per mode, exactly as it does for the grid
    sources.

    Args:
        mode: A ``--mode`` value, e.g. ``"image"``.

    Returns:
        The callable that reports that mode's source shape as a
        ``(width, height)`` pair — ``()`` for :data:`RANDOM`, ``(key,)`` for
        :data:`LIBRARY`, ``(path,)`` for :data:`IMAGE`.

    Raises:
        ValueError: ``mode`` is not registered. Same reasoning as
            :func:`for_mode`'s: an unknown mode here is a wiring bug, not user
            input, because argparse's ``choices`` already refused it.
    """
    try:
        return _SHAPES[mode]
    except KeyError:
        raise ValueError(
            f"unknown grid sourcing mode {mode!r}; known modes: "
            f"{', '.join(MODES)}"
        ) from None
