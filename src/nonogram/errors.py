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
``SizeOutOfRange``, ``InvalidDensity``, ``UnknownLibraryImage``,
``InvalidPuzzleName`` and ``UnsupportedDifficulty`` belong to the domain layer,
not to argparse. The CLI parses syntax only; AC-069/AC-070 (each grid side's
range), AC-011 (density range), AC-006 (library key), AC-045 (name validity)
and AC-021 (difficulty tier) are tested as domain rules against pure functions,
without going through argv.
"""


class NonogramError(Exception):
    """Base class for every domain error the CLI maps onto an exit code.

    An error added later that does not appear in the CLI's exit-code table is
    still caught and reported through this base class.
    """


class SizeOutOfRange(NonogramError):
    """A requested grid *side* falls outside the supported range (FR-019).

    The name predates ADR-0022 and is kept: renaming it would change the CLI's
    published exit-code table for no gain. What it reports is now one side, and
    the message says which — width or height (CON-011, ADR-0022/R2).
    """


class SizeTooSmallForSource(SizeOutOfRange):
    """A bare ``--size N`` is too small to follow this source's shape (FR-023).

    Raised by ``nonogram.sourcing.random_grid.derive_extent`` when completing a
    bare ``--size N`` from the source's own aspect ratio would put the derived
    side under ``MIN_SIZE``, hold it there, and thereby discard more than half
    the source — FR-021's own criterion, applied to the shape the derivation
    would have requested (ADR-0022/R4).

    A subclass of :class:`SizeOutOfRange` rather than of
    :class:`ImageNeedsManualCrop`, for two reasons. It *is* the requested size
    that is wrong — a larger ``--size N`` accepts the very picture a smaller one
    refuses, which is the counter-intuitive consequence FR-023 asks be carried
    in the message rather than deduced — and the remedy is emphatically **not**
    the manual crop ``ImageNeedsManualCrop`` is named for. Inheriting from
    ``SizeOutOfRange`` also means the CLI's exit-code table needs no new row:
    ``exit_code_for``'s MRO walk finds ``INVALID_INPUT`` through the base class,
    which is exactly the extension path that table was built for.
    """


class InvalidDensity(NonogramError):
    """Requested fill density is not a valid percentage (FR-004)."""


class UnknownLibraryImage(NonogramError):
    """No built-in library image is registered under the requested key (FR-002)."""


class UnreadableImage(NonogramError):
    """The uploaded image cannot be read (FR-003).

    Raised by ``nonogram.sourcing.image`` for every way a ``--image`` path can
    fail to become a picture: missing, unreadable, not an image at all,
    truncated, or the flag omitted in image mode (AC-008). It exists so that
    Pillow's own exception types never surface to the user — and, just as
    importantly, so that a failure to read the user's *input* is reported as an
    input error rather than travelling out as a bare ``OSError`` that the
    adapter would have to guess the origin of.
    """


class ImageNeedsManualCrop(NonogramError):
    """The uploaded image is too differently shaped from the grid (FR-021).

    Named for what the user has to do about it rather than for where it was
    raised: fitting this picture to this grid would centre-crop away more than
    half of it, so the tool refuses and asks the user to crop it themselves
    first (CON-012, ADR-0022/R3, AC-077). Deliberately *not* a subclass of
    ``UnreadableImage`` — the file read perfectly, and telling the user their
    picture is unreadable when it is merely the wrong shape sends them to fix
    the wrong thing. It is still an *input* error, and the CLI's exit-code table
    puts it in the same group.
    """


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


class UnsupportedDifficulty(NonogramError):
    """The requested difficulty tier is not one of Easy/Medium/Hard (FR-008).

    Raised by ``nonogram.difficulty.parse_tier``, inward of argparse: which
    tiers exist is a domain rule and not argument syntax, so ``--difficulty``
    carries no ``choices=`` (AC-021, ADR-0010, CARD-010 guardrail G-4).
    """
