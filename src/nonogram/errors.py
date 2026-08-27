"""Domain error hierarchy for the Puzzle Creation context (CTX-001).

These are *domain* errors: they are raised inward of COMP-001, by the
orchestrator and the capability modules, whenever a domain rule is violated or
a bounded generation policy gives up. The CLI adapter (``nonogram.cli``) is the
only place that turns them into a message and a process exit code — the
exit-code table lives there, not here, so nothing inward of the adapter has to
know that a process exit code exists (ADR-0007, inward-only dependencies).

This module deliberately has no imports and no behaviour: every class is a
marker the raiser fills with a human-readable message.

Placement note (ADR-0010, guardrail G-3): the *checks* that raise
``SizeOutOfRange``, ``InvalidDensity``, ``UnknownLibraryImage`` and
``InvalidPuzzleName`` belong to the domain layer, not to argparse. The CLI
parses syntax only; AC-003/AC-004 (size range), AC-011 (density range),
AC-006 (library key) and AC-045 (name validity) are tested as domain rules
against pure functions, without going through argv.
"""


class NonogramError(Exception):
    """Base class for every domain error the CLI maps onto an exit code.

    An error added later that does not appear in the CLI's exit-code table is
    still caught and reported through this base class.
    """


class SizeOutOfRange(NonogramError):
    """Requested grid size falls outside the supported range (FR-001)."""


class InvalidDensity(NonogramError):
    """Requested fill density is not a valid percentage (FR-004)."""


class UnknownLibraryImage(NonogramError):
    """No built-in library image is registered under the requested key (FR-002)."""


class GenerationAbandoned(NonogramError):
    """A bounded generation loop hit its retry cap without a usable puzzle.

    Raised by the orchestrator's POL-005 abandonment path once POL-001
    (regenerate), POL-002 (pixel-nudge) or POL-004 (difficulty resample) has
    exhausted the maximum bound INV-003 fixes (NFR-002, ADR-0002).
    """


class SolverTimeout(NonogramError):
    """The uniqueness check passed its deadline before concluding.

    Cooperative deadline mechanism per ADR-0011, against the generation-time
    thresholds ADR-0001 sets (NFR-001).
    """


class ExportRejected(NonogramError):
    """Export was refused for a puzzle that is not exportable.

    The orchestrator's INV-002 gate — a puzzle may only be exported once its
    uniqueness check has confirmed exactly one solution (FR-011).
    """


class InvalidPuzzleName(NonogramError):
    """The supplied puzzle name cannot be used (FR-015)."""
