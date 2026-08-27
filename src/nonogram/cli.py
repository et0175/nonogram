"""COMP-001 — the CLI adapter, the tool's only inbound surface (CON-001).

Two rules shape this module.

*Direction* (ADR-0007): it imports the orchestrator; nothing inward of it ever
imports back. All this adapter does is translate — argv into a
``GenerationRequest`` on the way in, a domain error into a message plus an exit
code on the way out.

*Parsing only* (ADR-0010, guardrail G-3): argparse expresses syntax — is this
an integer, is this one of the known subcommands, is this a path — and nothing
else. Size range (AC-003/AC-004), density range (AC-011) and name validity
(AC-045) are domain rules enforced inward of this component, so they are
deliberately absent from the ``type=``/``choices=`` configuration below. A
50000-cell request parses fine here and is rejected inward.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from enum import IntEnum
from pathlib import Path

from nonogram import orchestrator
from nonogram.errors import (
    ExportRejected,
    GenerationAbandoned,
    InvalidDensity,
    InvalidPuzzleName,
    NonogramError,
    SizeOutOfRange,
    SolverTimeout,
    UnknownLibraryImage,
)

__all__ = ["ExitCode", "build_parser", "exit_code_for", "main"]

PROG = "nonogram"


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
    InvalidPuzzleName: ExitCode.INVALID_INPUT,
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


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Later cards extend *this* parser rather than adding a second one:
    ``--difficulty`` and ``--name`` (FR-008, FR-015), ``--image`` and the
    ``library``/``image`` modes (FR-002, FR-003), and the remaining export
    formats (FR-011, FR-012, FR-016).
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
        choices=["random"],
        default="random",
        help="How the solution grid is sourced (default: random).",
    )
    generate.add_argument(
        "--size",
        type=int,
        metavar="N",
        help=(
            "Square grid edge length. The supported range is a domain rule and "
            "is checked after parsing, not here."
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
    generate.add_argument(
        "--seed",
        type=int,
        metavar="N",
        help="Seed for the run's random source, for reproducible puzzles.",
    )
    generate.add_argument(
        "--export",
        action="append",
        choices=["json"],
        dest="export_formats",
        metavar="FORMAT",
        help="Export format; repeat the flag to request several.",
    )
    generate.add_argument(
        "--out",
        type=Path,
        metavar="PATH",
        help="Where exports are written (default: the working directory).",
    )

    return parser


def _run_generate(args: argparse.Namespace) -> int:
    """Translate the parsed ``generate`` arguments into one orchestrator call."""
    request = orchestrator.GenerationRequest(
        mode=args.mode,
        size=args.size,
        density=args.density,
        seed=args.seed,
        export_formats=tuple(args.export_formats or ()),
        out=args.out,
    )
    # The run outcome (export paths, echoed seed per ADR-0015, the FR-014 nudge
    # count) is reported to the user by later cards; CARD-001 only wires the call.
    orchestrator.generate(request)
    return ExitCode.OK


def main(argv: Sequence[str] | None = None) -> int:
    """Console-script entry point (``nonogram``). Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except NonogramError as error:
        print(f"{PROG}: error: {error}", file=sys.stderr)
        return exit_code_for(error)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
