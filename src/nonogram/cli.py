"""COMP-001 — the CLI adapter, one of the tool's two inbound surfaces.

It was the only one until CARD-019: CON-007 supersedes CON-001's "no web/GUI"
and FR-017 adds a second adapter, COMP-008 (``nonogram.web``), a *sibling* of
this module rather than a layer around it (ADR-0019). The only thing that
crosses between them is the ``serve`` subcommand below, which exists here
because ADR-0008 keeps exactly one ``[project.scripts]`` console entry point —
one command, two subcommands, two adapters behind them.

Two rules shape this module.

*Direction* (ADR-0007): it imports the orchestrator; nothing inward of it ever
imports back. All this adapter does is translate — argv into a
``GenerationRequest`` on the way in, a domain error into a message plus an exit
code on the way out.

*Parsing only* (ADR-0010, guardrail G-3): argparse expresses syntax — is this
an integer, is this ``NxM``, is this one of the known subcommands, is this a
path — and nothing else. The per-side grid range (AC-069/AC-070), density range
(AC-011), name validity (AC-045) and which difficulty tiers exist (AC-021) are
domain rules enforced inward of this component, so they are deliberately absent
from the ``type=``/``choices=`` configuration below. A ``--size 40x20`` request
parses fine here and is rejected inward.

The distinction is at its sharpest on ``--size``, which is why
:func:`_extent_token` below is worth reading as the worked example of it:
splitting ``30x20`` into two numbers is *syntax* and belongs here, while
whether 30 and 20 are supported grid sides is a rule about puzzles and belongs
to ``sourcing.random_grid.validate_extent`` (ADR-0022/R2).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from enum import IntEnum
from pathlib import Path

from nonogram import difficulty, export, orchestrator, web
from nonogram.errors import (
    ExportRejected,
    GenerationAbandoned,
    ImageNeedsManualCrop,
    InvalidDensity,
    InvalidPuzzleName,
    NonogramError,
    SizeOutOfRange,
    SolverTimeout,
    UnknownLibraryImage,
    UnreadableImage,
    UnsupportedDifficulty,
)

__all__ = ["ExitCode", "build_parser", "exit_code_for", "main"]

PROG = "nonogram"

#: The separator in a ``--size WxH`` token. ``x`` and not ``*`` (ADR-0022,
#: tested rather than assumed): in zsh — the project owner's shell — an
#: unquoted ``--size 30*20`` fails with "no matches found" before the process
#: starts, or silently expands to a filename if the glob happens to match.
#: ``x`` is also the conventional separator for extents (screen resolutions,
#: ImageMagick). Lower case only: ``30X20`` is a usage error, not a synonym.
_EXTENT_SEPARATOR = "x"


class ExitCode(IntEnum):
    """Process exit codes.

    Grouped by what the user has to do about the failure rather than one code
    per exception class, so adding an error to an existing group later does not
    change the tool's observable exit-code contract. ``USAGE`` is argparse's own
    exit status for a malformed command line and is listed here for completeness
    only — argparse raises ``SystemExit(2)`` itself.
    """

    OK = 0
    INTERNAL_ERROR = 1
    USAGE = 2
    INVALID_INPUT = 3
    GENERATION_FAILED = 4
    EXPORT_REJECTED = 5


# Exit codes are an adapter concern, so the table lives here and not in
# errors.py — nothing inward of COMP-001 needs to know a process exit code
# exists.
_EXIT_CODES: dict[type[NonogramError], ExitCode] = {
    SizeOutOfRange: ExitCode.INVALID_INPUT,
    InvalidDensity: ExitCode.INVALID_INPUT,
    UnknownLibraryImage: ExitCode.INVALID_INPUT,
    # The user's own file, unreadable: an *input* error like an out-of-range
    # grid side or an
    # unknown library key, and pointedly not EXPORT_REJECTED — reading
    # ``--image`` and writing ``--out`` are opposite ends of the run, and the
    # difference is exactly what the user has to go and fix (AC-008).
    UnreadableImage: ExitCode.INVALID_INPUT,
    # Read fine, wrong shape (FR-021). A case of its own because the MRO walk
    # below reaches nothing else: ``ImageNeedsManualCrop`` deliberately does not
    # subclass ``UnreadableImage`` (the file is not the problem), so without
    # this row it would fall through to INTERNAL_ERROR. It is a bad *input* like
    # every other entry in this group — the user goes and changes what they
    # passed in, here by cropping the picture or asking for a differently
    # shaped grid.
    ImageNeedsManualCrop: ExitCode.INVALID_INPUT,
    InvalidPuzzleName: ExitCode.INVALID_INPUT,
    UnsupportedDifficulty: ExitCode.INVALID_INPUT,
    GenerationAbandoned: ExitCode.GENERATION_FAILED,
    SolverTimeout: ExitCode.GENERATION_FAILED,
    ExportRejected: ExitCode.EXPORT_REJECTED,
}


def exit_code_for(error: NonogramError) -> ExitCode:
    """Map a domain error onto its exit code.

    Walks the error's MRO, so a future error that subclasses a mapped one
    inherits its group. An unmapped ``NonogramError`` is reported as
    ``INTERNAL_ERROR`` — a mapping gap is a bug, not a user error.
    """
    for cls in type(error).__mro__:
        code = _EXIT_CODES.get(cls)  # type: ignore[arg-type]
        if code is not None:
            return code
    return ExitCode.INTERNAL_ERROR


def _extent_token(text: str) -> tuple[int, int]:
    """Parse a ``--size`` token into a ``(width, height)`` pair.

    The whole of what ADR-0010 lets this adapter do to ``--size``: turn one
    string into two integers, and refuse a string that is not one of the two
    documented shapes. ``"30"`` is the square shorthand and yields ``(30, 30)``;
    ``"30x20"`` yields ``(30, 20)``, 30 wide by 20 tall.

    It applies **no range check**, deliberately (ADR-0022/R2, guardrail G-2).
    ``"40x20"``, ``"0"``, ``"9"``, ``"31"`` and ``"-5"`` are all well-formed and
    all parse; each is refused inward by
    ``sourcing.random_grid.validate_extent``, with the tool's own message and
    exit code 3, rather than by argparse with a usage error and exit code 2.
    Encoding the bound here as a ``type=``/``choices=`` check would move that
    decision out of the domain and out of reach of the tests that exercise it as
    a pure function.

    Each half is converted with ``int``, which is what makes ``-5`` reach the
    domain (argparse hands a lone negative number through as a value) and which
    also accepts a leading sign, surrounding whitespace and Python's ``_`` digit
    separators. Those are ``int``'s documented semantics rather than a grammar
    of this tool's own, and every value they admit still faces the range rule
    inward, so no bound leaks out of the domain by tolerating them.

    Args:
        text: One ``--size`` token as the user typed it.

    Returns:
        ``(width, height)``, unvalidated.

    Raises:
        argparse.ArgumentTypeError: ``text`` is neither ``N`` nor ``NxM``
            (``"30x"``, ``"x20"``, ``"3x4x5"``, ``"big"``, ``"30X20"``).
            argparse turns this into its own usage error naming ``--size`` and
            exits ``ExitCode.USAGE`` before any request is built (AC-064).
    """
    parts = text.split(_EXTENT_SEPARATOR)
    if len(parts) > 2:
        raise argparse.ArgumentTypeError(
            f"expected N or N{_EXTENT_SEPARATOR}M, got {text!r}"
        )
    try:
        sides = [int(part) for part in parts]
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected N or N{_EXTENT_SEPARATOR}M with whole numbers, got {text!r}"
        ) from None
    width, height = sides if len(sides) == 2 else (sides[0], sides[0])
    return width, height


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Every card extends *this* parser rather than adding a second one:
    ``--mode library`` and ``--library-key`` (FR-002), ``--name`` (FR-015),
    ``--difficulty`` (FR-008), the export formats (FR-011, FR-012, FR-016) and
    now ``--mode image`` with ``--image`` (FR-003) all landed that way. What is
    still to come — CARD-017's nudge-count reporting — is output, not argv.
    """
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Generate uniquely-solvable black-and-white nonogram puzzles "
            "and export them for printing."
        ),
    )
    subcommands = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)

    generate = subcommands.add_parser(
        "generate",
        help="Generate one puzzle and export it.",
        description="Generate one puzzle and export it.",
    )
    generate.set_defaults(handler=_run_generate)
    generate.add_argument(
        "--mode",
        choices=["random", "library", "image"],
        default="random",
        help="How the solution grid is sourced (default: random).",
    )
    generate.add_argument(
        "--library-key",
        metavar="KEY",
        help=(
            "Which built-in image to draw in --mode library. Which keys exist "
            "is a domain rule and is checked after parsing, not here."
        ),
    )
    # ``type=Path`` and nothing else, deliberately (ADR-0010, guardrail G-5).
    # Turning a string into a Path is syntax — the same conversion ``--out``
    # gets — whereas "does this file exist and decode as a picture?" is a
    # question about the world, answered by the sourcing module and reported as
    # ``UnreadableImage`` -> exit code 3 (AC-008). An
    # ``argparse.FileType``/existence check here would spend that criterion's
    # message and exit code on a usage error instead.
    generate.add_argument(
        "--image",
        type=Path,
        metavar="PATH",
        help=(
            "Picture to convert in --mode image. Whether the file exists and "
            "can be read is a domain rule and is checked after parsing, not "
            "here."
        ),
    )
    # One flag for both dimensions, not two (ADR-0022, guardrail G-3): the user
    # is choosing an extent, and naming it twice would make the common square
    # case two flags while leaving ``--size`` as a third way to say the same
    # thing. ``dest`` is ``extent`` rather than ``size`` because the value is a
    # pair — the *flag* keeps its name so no existing invocation or documented
    # example breaks, but nothing in the code should read a pair out of
    # something called a size (ADR-0022/R1).
    generate.add_argument(
        "--size",
        type=_extent_token,
        dest="extent",
        metavar="N|WxH",
        help=(
            "Grid extent in cells: N for a square, or WxH for W wide by H "
            "tall (e.g. 30x20). The supported range for each side is a domain "
            "rule and is checked after parsing, not here."
        ),
    )
    generate.add_argument(
        "--density",
        type=int,
        metavar="PERCENT",
        help=(
            "Target share of filled cells, in percent. The valid range is a "
            "domain rule and is checked after parsing, not here."
        ),
    )
    # No ``choices=`` here, deliberately, and this is the one flag where that
    # is easy to get wrong: the three tiers are a closed set, so argparse
    # *could* enforce them — but AC-021 asks for an unsupported tier to be
    # rejected as a domain error with the tool's own message and exit code 3,
    # not as an argparse usage error with exit code 2 (ADR-0010, guardrail
    # G-4). The names below are still read from ``difficulty.Tier`` rather than
    # spelled out, so ``--help`` cannot drift from what ``parse_tier`` accepts;
    # what is read is the vocabulary, not the rule.
    generate.add_argument(
        "--difficulty",
        metavar="TIER",
        help=(
            f"Difficulty tier to generate for "
            f"({', '.join(difficulty.Tier)}). Candidates whose difficulty "
            "score misses the tier are discarded and resampled. Which tiers "
            "exist is a domain rule and is checked after parsing, not here."
        ),
    )
    generate.add_argument(
        "--name",
        metavar="NAME",
        help=(
            "Name for the puzzle, shown on the printed page and used for the "
            "export filename. Defaults to the library key, or to "
            "<mode>-<YYYY-MM-DD>-<HHMM>. What counts as a usable name is a "
            "domain rule and is checked after parsing, not here."
        ),
    )
    generate.add_argument(
        "--seed",
        type=int,
        metavar="N",
        help="Seed for the run's random source, for reproducible puzzles.",
    )
    # ``choices`` comes from COMP-007's registry rather than being repeated
    # here: the export formats are one list, in ``nonogram.export``, and this
    # adapter reads it. CARD-012 (PNG/SVG), CARD-013 (CSV) and CARD-014 (PDF)
    # therefore each add one registry row and their format becomes accepted,
    # documented in ``--help`` and rejected-when-misspelled without this file
    # being touched at all. (``--mode`` above still mirrors its strings by
    # hand; sourcing's three modes do not share a call signature, so there is
    # no equivalent single table to read.)
    generate.add_argument(
        "--export",
        action="append",
        choices=list(export.FORMATS),
        dest="export_formats",
        metavar="FORMAT",
        help=(
            f"Export format ({', '.join(export.FORMATS)}); repeat the flag to "
            "request several."
        ),
    )
    generate.add_argument(
        "--out",
        type=Path,
        metavar="DIR",
        help=(
            "Directory exports are written to, created if missing "
            "(default: the working directory). A directory rather than a file "
            "name because --export is repeatable and each format writes its "
            "own file."
        ),
    )

    # COMP-008's launcher (FR-017, ADR-0019), a *sibling* of ``generate`` and
    # not a mode of it: the two subcommands share this parser because ADR-0008
    # keeps one console entry point, and share nothing else. Adding it changes
    # no ``generate`` flag, default or exit code (guardrail G-1) — subparsers
    # were already required by ``required=True`` above, so even "no subcommand"
    # behaves exactly as before.
    serve = subcommands.add_parser(
        "serve",
        help="Serve the local web UI at http://127.0.0.1:8765/.",
        description=(
            "Serve the same generation options as a form in the browser. "
            "Listens on 127.0.0.1 only and requires no authentication: the "
            "loopback bind is the whole of the access control. Ctrl-C stops it."
        ),
    )
    serve.set_defaults(handler=_run_serve)
    # ``type=int`` and nothing else, for the same reason ``--size`` carries no
    # range (ADR-0010): syntax here, rejection further in. There is no domain
    # rule about port numbers to push inward, so the rejection comes from the
    # socket layer instead — ``--port 99999`` binds nothing and is reported by
    # :func:`_run_serve` below. No ``--host``: the bind address is a constant
    # in ``nonogram.web``, not an option, because NFR-003/AC-052 is a property
    # of the code and must not become a property of how it was invoked.
    serve.add_argument(
        "--port",
        type=int,
        default=web.DEFAULT_PORT,
        metavar="PORT",
        help=(
            f"TCP port to listen on (default: {web.DEFAULT_PORT}). "
            "Always on 127.0.0.1; the interface is not configurable."
        ),
    )

    return parser


def _run_generate(args: argparse.Namespace) -> int:
    """Translate the parsed ``generate`` arguments into one orchestrator call.

    Two calls inward, not one: the pipeline produces the puzzle and the export
    step writes it, because generation is pure and only the second touches the
    filesystem (CON-003). Both stay behind the orchestrator — the adapter never
    reaches into a capability module to render anything itself, and it does not
    decide whether the puzzle may be exported either (INV-002 is COMP-002's,
    and reaches the user here only as ``ExportRejected`` -> exit code 5).

    Reporting is the translation back out: the written paths, and the seed when
    the user did not choose one — ADR-0015 requires the auto-drawn seed be
    printed, since otherwise a reproducible run has nowhere to be read from
    until the export file is opened. Both go to stdout; a domain error goes to
    stderr in :func:`main`, and the one failure this function reports itself is
    the export ``OSError`` below.

    The FR-014 nudge count (CARD-017) joins them, printed after the written
    paths and only when ``puzzle.nudge.attempts`` is nonzero — the count is
    read directly off the ``Puzzle`` aggregate that CARD-016's recovery loop
    populated, never recomputed here (guardrail G-5), and its absence *is*
    the zero-nudges signal (AC-041, guardrail G-3).

    The ``OSError`` clause below is CARD-007's, moved down here from
    :func:`main` and narrowed to the one call it was always about (CARD-007
    review follow-up). It was written when export was the only thing in the
    process that touched the filesystem, which made "any ``OSError`` is a
    failed export" true by accident of scope; ``--mode image`` reads a
    user-supplied file, so wrapping the whole handler would report a missing
    picture as "export rejected". The picture is now doubly guarded — the
    sourcing module raises ``UnreadableImage`` for it, so no bare ``OSError``
    from a read reaches an exception handler at all — but the premise that made
    the wide clause safe is gone either way, and a clause is better scoped to
    what it can actually explain than left to catch whatever a later card adds.
    """
    # ``--size`` omitted is ``(None, None)``, not a default extent: which grid
    # a request with no ``--size`` should get is a domain question, and the
    # domain answers it by refusing (``SizeOutOfRange`` -> exit code 3), exactly
    # as it did when the flag carried one number.
    width, height = args.extent if args.extent is not None else (None, None)
    request = orchestrator.GenerationRequest(
        mode=args.mode,
        width=width,
        height=height,
        density=args.density,
        library_key=args.library_key,
        # A Path, not an opened file: readability is the domain's question
        # (AC-008), so a missing path travels inward and comes back as
        # UnreadableImage -> exit code 3.
        image=args.image,
        # Carried through exactly as typed, empty string included: FR-015's
        # name rule is domain validation (AC-045) and belongs inward of
        # argparse, not in a ``type=`` here (ADR-0010, guardrail G-5). It comes
        # back as InvalidPuzzleName -> exit code 3.
        name=args.name,
        # Same story as ``name``: carried through as typed, because "is
        # ``extreme`` a tier?" is FR-008's domain rule (AC-021) and not
        # argument syntax. It comes back as UnsupportedDifficulty -> exit
        # code 3.
        difficulty=args.difficulty,
        seed=args.seed,
        export_formats=tuple(args.export_formats or ()),
        out=args.out,
    )
    puzzle = orchestrator.generate(request)
    if request.seed is None:
        print(f"seed: {puzzle.seed}")
    try:
        written = orchestrator.export_puzzle(puzzle)
    except OSError as error:
        # Not a NonogramError: ``export.write`` documents that ``--out``
        # pointing at something unusable (an existing file in the way, an
        # unwritable directory, ...) raises the stdlib's own OSError rather
        # than a domain error. It still needs a clean report instead of a raw
        # traceback, and here — unlike in ``main`` — the error demonstrably
        # came from writing the export, so reporting it under the same exit
        # code as ExportRejected says something true about it.
        _report(error)
        return ExitCode.EXPORT_REJECTED
    for path in written:
        print(f"wrote {path}")
    # FR-014/CARD-017: printed here, after the "wrote {path}" lines, so that
    # the only run this placement actually suppresses the line for is one
    # whose export raised ``OSError`` above (that branch returns first). It is
    # not gated on ``--export`` actually being requested — with no
    # ``--export`` flag at all, ``written`` is simply empty and this still
    # prints — so "at export time" describes intent, not the implemented
    # condition. The count itself is read straight off the aggregate
    # (guardrail G-5) and printed only when it is nonzero — zero nudges
    # prints nothing at all (AC-041, guardrail G-3).
    nudged = puzzle.nudge.attempts
    if nudged > 0:
        cell_word = "cell" if nudged == 1 else "cells"
        verb = "was" if nudged == 1 else "were"
        print(f"{nudged} {cell_word} {verb} nudged to reach a unique solution")
    return ExitCode.OK


def _run_serve(args: argparse.Namespace) -> int:
    """Hand the process over to COMP-008 until the user stops it (FR-017).

    The whole subcommand is one call. Everything about HTTP — the socket, the
    router, the form page — belongs to ``nonogram.web``; this function's only
    job is the one thing COMP-008 must not own, which is the process exit code
    (the same division ``main`` already makes for domain errors).

    Ctrl-C is a deliberate stop and exits 0: ``web.serve_on`` swallows the
    ``KeyboardInterrupt`` and returns normally once the port is released.

    The ``except`` clause covers the *bind and nothing else*, which is why the
    call is split in two: ``web.create_server`` inside the ``try``, the serve
    loop outside it. Every failure this clause reports means the same thing to
    the user — pass a different ``--port`` — and that is only true of the bind.
    An ``OSError`` raised after a successful bind (a selector failure, an
    ``accept`` the stdlib re-raises) is a bug, not a port that is taken, and it
    keeps its traceback rather than being dressed up as bad input.

    The failure is deliberately not a ``NonogramError``: "this port is taken"
    is not a fact about puzzles, so the domain error hierarchy is not widened to
    carry it (guardrails G-2, G-4). ``OverflowError`` sits beside ``OSError``
    because CPython's socket layer raises it — not an ``OSError`` — for a port
    outside 0..65535, which is exactly what ``--port 99999`` produces. Both mean
    the same thing to the user and both get ``INVALID_INPUT``: the grouping rule
    :data:`_EXIT_CODES` is built on.
    """
    try:
        server = web.create_server(args.port)
    except (OSError, OverflowError) as error:
        _report(error)
        return ExitCode.INVALID_INPUT
    web.serve_on(server)
    return ExitCode.OK


def _report(error: BaseException) -> None:
    """Print one failure to stderr in the tool's single error format.

    One function so the two places that report a failure — the domain-error
    clause in :func:`main` and the export ``OSError`` clause in
    :func:`_run_generate` — cannot drift into two different-looking messages.
    """
    print(f"{PROG}: error: {error}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Console-script entry point (``nonogram``). Returns a process exit code.

    Every failure the tool has a word for is a :class:`NonogramError` and is
    reported here. The one exception a handler deals with itself is the
    ``OSError`` an export write can raise — see :func:`_run_generate` — which
    is caught around that call rather than around the whole handler, so this
    function does not have to guess where in a run an ``OSError`` came from.
    Anything else really is unexpected and keeps its traceback.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except NonogramError as error:
        _report(error)
        return exit_code_for(error)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
