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

Layering (ADR-0007): this is a capability package, so it imports only its own
submodules and ``nonogram.errors`` — never the adapter, the orchestrator or a
sibling capability.
"""

from __future__ import annotations

from collections.abc import Callable

from nonogram.sourcing import image, library, random_grid

__all__ = ["IMAGE", "LIBRARY", "MODES", "RANDOM", "GridSource", "for_mode"]

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
