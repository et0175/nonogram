"""COMP-003 — grid sourcing: the mode-dispatch surface over CAP-001 (FR-001).

A solution grid can be sourced three ways — drawn at random (FR-001/FR-004),
taken from the built-in image library (FR-002, CARD-008) or converted from an
uploaded image (FR-003, CARD-015). The first two exist today; adding the third
means registering a callable in :data:`_SOURCES`, not reshaping the dispatch —
which is exactly what CARD-008 did to land the library row, one line.

:func:`for_mode` returns the *sourcing callable* rather than calling it,
because the three modes do not share a parameter list — random takes size and
density, library takes a key, image takes a path — and collapsing them behind
one signature now would either invent parameters the later cards have to
change or force a ``**kwargs`` surface with no contract at all. The one thing
every mode does share, the injected ``random.Random`` (ADR-0015), stays an
explicit argument of each callable.

Layering (ADR-0007): this is a capability package, so it imports only its own
submodules and ``nonogram.errors`` — never the adapter, the orchestrator or a
sibling capability.
"""

from __future__ import annotations

from collections.abc import Callable

from nonogram.sourcing import library, random_grid

__all__ = ["LIBRARY", "MODES", "RANDOM", "GridSource", "for_mode"]

#: The ``--mode`` value each source is selected by. The CLI's argparse
#: ``choices`` mirrors these strings (syntactic rejection of an unknown mode
#: happens there, ADR-0010); this table is the domain-side registry.
RANDOM = "random"
LIBRARY = "library"

#: What every mode's entry point looks like from the dispatcher's side: it
#: returns a grid in the ADR-0012 boundary representation. Arguments are
#: deliberately unconstrained — see the module docstring.
GridSource = Callable[..., list[list[bool]]]

_SOURCES: dict[str, GridSource] = {
    RANDOM: random_grid.generate,
    LIBRARY: library.generate,
    # CARD-015: IMAGE   -> image.generate
}

#: The modes this build can source a grid for, in registration order.
MODES: tuple[str, ...] = tuple(_SOURCES)


def for_mode(mode: str) -> GridSource:
    """Return the grid source registered for ``mode``.

    Args:
        mode: A ``--mode`` value, e.g. ``"random"``.

    Returns:
        The callable that sources a grid for that mode. Call it with the
        mode's own arguments — ``(size, density, rng)`` for :data:`RANDOM`,
        ``(key, size, rng)`` for :data:`LIBRARY`. The orchestrator assembles
        that list per mode at its own call site.

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
