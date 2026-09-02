"""COMP-001 tests: parser wiring, error-to-exit-code mapping, layering.

CARD-001 is traced to no FR, so nothing here asserts an acceptance criterion.
What it does assert is the skeleton's contract: the parser accepts the
increment-1 flag surface, argparse does *not* apply domain rules (guardrail
G-3), every domain error reaches the user as a message plus a documented
non-zero exit code, and the inward-only dependency rule (ADR-0007) holds.
"""

from __future__ import annotations

import argparse
import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import nonogram
from nonogram import cli, errors, orchestrator, web

# --------------------------------------------------------------------------
# Parser wiring
# --------------------------------------------------------------------------


def _parse(*argv: str) -> argparse.Namespace:
    return cli.build_parser().parse_args(list(argv))


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "nonogram" in out
    assert "generate" in out


def test_generate_help_lists_the_increment_one_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["generate", "--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for flag in ("--mode", "--size", "--density", "--seed", "--export", "--out"):
        assert flag in out


def test_generate_parses_the_full_flag_surface() -> None:
    args = _parse(
        "generate",
        "--mode",
        "random",
        "--size",
        "15",
        "--density",
        "45",
        "--seed",
        "1234",
        "--export",
        "json",
        "--out",
        "/tmp/puzzles",
    )
    assert args.command == "generate"
    assert args.mode == "random"
    # A bare token states one number, so one number is what it parses to
    # (FR-023, CARD-033); ``--size 15x15`` is how a user asks for a square.
    assert args.extent == (15, None)
    assert args.density == 45
    assert args.seed == 1234
    assert args.export_formats == ["json"]
    assert args.out == Path("/tmp/puzzles")


def test_generate_defaults_leave_every_optional_unset() -> None:
    args = _parse("generate")
    assert args.mode == "random"
    assert args.extent is None
    assert args.density is None
    assert args.seed is None
    assert args.export_formats is None
    assert args.out is None


def test_export_flag_repeats_into_a_list() -> None:
    assert _parse("generate", "--export", "json", "--export", "json").export_formats == [
        "json",
        "json",
    ]


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param([], id="no-subcommand"),
        pytest.param(["solve"], id="unknown-subcommand"),
        # Was ``library`` until CARD-008 registered it and ``image`` until
        # CARD-015 did. The case is about an *unregistered* ``--mode`` value
        # being argparse's to refuse; with all three modes the model names now
        # registered, the stand-in is a mode the tool deliberately does not
        # have — the same move the ``--export`` case below already had to make.
        pytest.param(["generate", "--mode", "webcam"], id="mode-not-registered"),
        # Was ``png`` until CARD-012 registered it and ``pdf`` until CARD-014
        # did. The case is about an *unregistered* ``--export`` value being
        # argparse's to refuse, whatever the registry happens to hold. With all
        # five planned formats now registered, the stand-in is a format the
        # tool deliberately does not have rather than one still to come —
        # ``xlsx``, the spreadsheet FR-012 answers with CSV instead.
        pytest.param(["generate", "--export", "xlsx"], id="format-not-registered"),
        pytest.param(["generate", "--size", "big"], id="size-not-an-integer"),
        pytest.param(["generate", "--seed", "x"], id="seed-not-an-integer"),
        pytest.param(["generate", "--nope"], id="unknown-flag"),
    ],
)
def test_malformed_command_line_is_a_usage_error(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.build_parser().parse_args(argv)
    assert excinfo.value.code == cli.ExitCode.USAGE


# --------------------------------------------------------------------------
# The `serve` subcommand (CARD-019, FR-017, ADR-0008/ADR-0019)
# --------------------------------------------------------------------------


def test_serve_is_a_sibling_subcommand_of_generate(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ADR-0008's one console entry point now has two subcommands.

    ``serve`` launches COMP-008 and ``generate`` still runs the CLI pipeline —
    two adapters, one command, and neither listed as a mode of the other.
    """
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])

    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "generate" in out
    assert "serve" in out


def test_serve_defaults_to_the_web_packages_port() -> None:
    """One default, defined in COMP-008 and read here (not copied)."""
    assert _parse("serve").port == web.DEFAULT_PORT


def test_serve_takes_a_port_and_nothing_else() -> None:
    """Guardrail G-1/AC-052: there is no ``--host`` for a user to widen.

    The bind address is a constant inside ``nonogram.web``, so the criterion
    is a property of the code rather than of how it was invoked. A flag here
    would undo that, which is why this test names the whole option surface
    rather than just checking ``--port`` exists.
    """
    assert set(vars(_parse("serve"))) == {"command", "handler", "port"}
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["serve", "--host", "0.0.0.0"])


def test_serve_does_not_range_check_the_port() -> None:
    """ADR-0010 again: argparse parses, something further in refuses.

    ``--port 99999`` is syntactically an integer and parses; the socket layer
    is what rejects it, which is why :func:`cli._run_serve` catches
    ``OverflowError`` alongside ``OSError``.
    """
    assert _parse("serve", "--port", "99999").port == 99999


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(OSError(48, "Address already in use"), id="port-in-use"),
        pytest.param(OSError(13, "Permission denied"), id="privileged-port"),
        pytest.param(OverflowError("bind(): port must be 0-65535."), id="port-out-of-range"),
    ],
)
def test_a_bind_failure_is_reported_as_invalid_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    """Failure matrix F-1/F-2: one message, exit code 3, no traceback.

    All three failures are the same instruction to the user — pass a different
    ``--port`` — which is the grouping rule ``_EXIT_CODES`` is built on. None of
    them becomes a ``NonogramError``: a busy socket is not a fact about puzzles
    (guardrails G-2, G-4).
    """

    def boom(port: int) -> None:
        raise error

    monkeypatch.setattr(web, "create_server", boom)

    assert cli.main(["serve"]) == cli.ExitCode.INVALID_INPUT
    captured = capsys.readouterr()
    assert captured.err.startswith("nonogram: error: ")
    assert "Traceback" not in captured.err


def test_a_failure_after_the_bind_is_not_reported_as_a_port_problem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failure matrix F-1: the ``except`` covers the bind and nothing else.

    Every failure that clause reports carries one implied instruction — pass a
    different ``--port`` — and that instruction is only true of a socket that
    would not bind. An ``OSError`` from *inside* the serve loop (a selector
    failure, an ``accept`` the stdlib re-raises) means something else entirely,
    so it must not be swallowed into ``INVALID_INPUT`` with that advice
    attached. It keeps its traceback instead.

    This is the test the two-call split in :func:`cli._run_serve` exists for: a
    single ``try`` around one combined call cannot tell the two apart, and would
    pass every other test in this file while telling the user the wrong thing.
    """
    monkeypatch.setattr(web, "create_server", lambda port: object())

    def boom_after_bind(server: object) -> None:
        raise OSError(9, "Bad file descriptor")

    monkeypatch.setattr(web, "serve_on", boom_after_bind)

    with pytest.raises(OSError):
        cli.main(["serve"])


def test_serve_exits_zero_when_the_server_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failure matrix F-6: Ctrl-C is a deliberate stop, not a failure.

    ``web.serve_on`` swallows the ``KeyboardInterrupt`` and returns once the
    port is released; the subcommand's contribution is turning that into exit 0.
    """
    monkeypatch.setattr(web, "create_server", lambda port: object())
    monkeypatch.setattr(web, "serve_on", lambda server: None)

    assert cli.main(["serve"]) == cli.ExitCode.OK


def test_serve_passes_the_requested_port_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """The whole of the subcommand's translation, in one assertion.

    The port reaches the *bind*, and the object the bind produced is what the
    serve loop is handed — the two halves of the split, pinned together so a
    later edit cannot quietly rebind inside the loop.
    """
    seen: list[int] = []
    served: list[object] = []
    bound = object()

    def bind(port: int) -> object:
        seen.append(port)
        return bound

    monkeypatch.setattr(web, "create_server", bind)
    monkeypatch.setattr(web, "serve_on", served.append)

    assert cli.main(["serve", "--port", "1234"]) == cli.ExitCode.OK
    assert seen == [1234]
    assert served == [bound]


def test_generate_is_unchanged_by_the_second_subcommand() -> None:
    """Guardrail G-1, as a comparison rather than as a promise.

    Every ``generate`` destination and its default, unchanged by ADR-0019's
    second adapter landing in the same parser. Spelled out here so that a flag
    quietly acquiring a default — or ``serve`` bleeding an option into the
    shared parser — fails rather than passing unnoticed.
    """
    assert vars(_parse("generate")) == {
        "command": "generate",
        "handler": cli._run_generate,
        "mode": "random",
        "library_key": None,
        "image": None,
        "extent": None,
        "density": None,
        "difficulty": None,
        "name": None,
        "seed": None,
        "export_formats": None,
        "out": None,
    }


# --------------------------------------------------------------------------
# Guardrail G-3: argparse parses, it does not judge
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("flag", "value", "dest", "expected"),
    [
        # The four bare-token rows CARD-023 left here, kept verbatim in what
        # they assert: a bare N is still one number the parser must not judge.
        # Only the *shape* of what it parses to has moved — first from ``N`` to
        # ``(N, N)`` (CARD-027), and now to ``(N, None)`` (CARD-033), because
        # the second number was never in the token and inventing it was a domain
        # default rather than parsing (FR-023, ADR-0010).
        ("--size", "0", "extent", (0, None)),
        ("--size", "9", "extent", (9, None)),
        ("--size", "31", "extent", (31, None)),
        ("--size", "-5", "extent", (-5, None)),
        # ...and the rectangular tokens the same rule now has to cover. Each
        # side is judged separately inward, so a token legal on one axis and
        # not the other must still reach the domain intact — which is exactly
        # what a range check in argparse would prevent.
        ("--size", "40x20", "extent", (40, 20)),
        ("--size", "20x40", "extent", (20, 40)),
        ("--size", "31x30", "extent", (31, 30)),
        ("--size", "30x9", "extent", (30, 9)),
        ("--size", "0x0", "extent", (0, 0)),
        ("--size", "9999x9999", "extent", (9999, 9999)),
        ("--density", "-1", "density", -1),
        ("--density", "0", "density", 0),
        ("--density", "101", "density", 101),
        ("--density", "9999", "density", 9999),
    ],
)
def test_out_of_domain_range_values_pass_the_parser_untouched(
    flag: str, value: str, dest: str, expected: object
) -> None:
    """Grid-side and density ranges are domain rules (ADR-0010, G-2/G-3).

    They must NOT be encoded as argparse ``type=``/``choices=`` checks, so the
    parser is required to accept these values and hand them inward unchanged.
    ``--size``'s ``type=`` is allowed to *split* ``WxH`` into two integers —
    that is syntax — and nothing else; every row here would be rejected by a
    parser that had learned the 10..30 bound.
    """
    args = _parse("generate", flag, value)
    assert getattr(args, dest) == expected


# --------------------------------------------------------------------------
# argv -> GenerationRequest
# --------------------------------------------------------------------------


@pytest.fixture
def captured_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> list[orchestrator.GenerationRequest]:
    """Replace the pipeline with a recorder.

    The adapter's job is to hand the request inward and translate what comes
    back; running the real generation here would test COMP-002 (which
    ``tests/test_orchestrator.py`` does) and make these argv tests stochastic.

    The export step is stubbed out for the same reason — and because it is the
    one part of the pipeline that writes to disk, so leaving it live would have
    these argv tests dropping files in the working directory. What the adapter
    does with the paths it gets back is covered in ``tests/test_export_json.py``.
    """
    seen: list[orchestrator.GenerationRequest] = []

    def fake_generate(request: orchestrator.GenerationRequest) -> orchestrator.Puzzle:
        seen.append(request)
        return orchestrator.Puzzle(request=request, seed=request.seed or 0)

    def fake_export(puzzle: orchestrator.Puzzle) -> tuple[Path, ...]:
        return ()

    monkeypatch.setattr(orchestrator, "generate", fake_generate)
    monkeypatch.setattr(orchestrator, "export_puzzle", fake_export)
    return seen


def test_main_hands_the_orchestrator_the_parsed_request(
    captured_requests: list[orchestrator.GenerationRequest],
) -> None:
    exit_code = cli.main(
        ["generate", "--size", "20", "--density", "50", "--seed", "7", "--export", "json"]
    )

    assert exit_code == cli.ExitCode.OK
    assert captured_requests == [
        orchestrator.GenerationRequest(
            mode="random",
            width=20,
            # ``None``, not 20: the bare ``--size 20`` token stated one number,
            # and since CARD-033 the adapter passes on what was typed instead of
            # squaring it (FR-023). What the run actually produces is 20x20 all
            # the same — the random source has no shape of its own — but that is
            # the *domain's* answer, reached in ``orchestrator._resolved_extent``
            # and recorded on ``Puzzle.extent``, not the adapter's.
            height=None,
            density=50,
            seed=7,
            export_formats=("json",),
            out=None,
        )
    ]


# --------------------------------------------------------------------------
# FR-018 — the `--size N` / `--size WxH` token (CARD-027, ADR-0022/R1+R2)
# --------------------------------------------------------------------------


def test_cli_parses_rectangular_size_token(
    captured_requests: list[orchestrator.GenerationRequest],
) -> None:
    """AC-062 / TestCLI_ParsesRectangularSizeToken (happy).

    ``--size 30x20`` reaches the domain as width 30, height 20 — width first,
    the order the token is written in and the order every signature inward of
    here takes. Asserted through ``cli.main`` rather than through the parser
    alone, because the criterion is about what the *request* carries.
    """
    assert cli.main(["generate", "--size", "30x20"]) == cli.ExitCode.OK

    request = captured_requests[0]
    assert (request.width, request.height) == (30, 20)


def test_cli_square_size_shorthand_sets_both_sides(
    captured_requests: list[orchestrator.GenerationRequest],
) -> None:
    """AC-063 / TestCLI_SquareSizeShorthandSetsBothSides (boundary).

    **Changed by CARD-033, as its predecessor's docstring said it would be.**
    CARD-027 wrote here that a bare N "is a square, and this test is what will
    have to change when [FR-023] lands". FR-023 has landed, so this is that
    change, and it is a change of *reading*, not of coverage: the criterion is
    still "what does the one-number token put on the request?", and the answer
    is now the one number that was typed.

    ``--size 30`` reaches the domain as ``width=30, height=None`` — a stated
    length and an unstated shape. Filling the second field in here would be the
    adapter claiming the user's source is square, which is a domain question and
    (for a picture) usually the wrong answer; ``orchestrator._resolved_extent``
    answers it from the source's own shape instead (FR-023, ADR-0022/R4,
    ADR-0010).

    Nothing a user types breaks: in the random mode this test runs, and in
    library mode while every template is 16x16, the derivation still yields
    30x30 — which ``TestDeriveShape_RandomSourceStaysSquare`` and
    ``TestDeriveShape_LibraryTemplateRatioAppliesSquareToday`` in
    ``tests/test_derive_shape.py`` assert end to end. What this test pins is the
    narrower thing it has always pinned: that the *adapter* judges nothing and
    invents nothing.

    AC-063's own wording ("carries width 30 and height 30") is superseded by
    this reading; the amendment is queued in
    ``meta/architecture/inputs/raw-requirements.md`` rather than hand-edited
    into ``requirements.yml``.
    """
    assert cli.main(["generate", "--size", "30"]) == cli.ExitCode.OK

    request = captured_requests[0]
    assert (request.width, request.height) == (30, None)


@pytest.mark.parametrize(
    "token",
    [
        pytest.param("30x", id="missing-height"),
        pytest.param("x20", id="missing-width"),
        pytest.param("3x4x5", id="three-parts"),
        pytest.param("30X20", id="uppercase-separator"),
        pytest.param("30*20", id="asterisk-separator"),
        pytest.param("30,20", id="comma-separator"),
        pytest.param("30.5", id="not-a-whole-number"),
        pytest.param("", id="empty"),
        pytest.param("x", id="separator-alone"),
    ],
)
def test_cli_rejects_malformed_size_token(
    token: str, captured_requests: list[orchestrator.GenerationRequest]
) -> None:
    """AC-064 / TestCLI_RejectsMalformedSizeToken (negative).

    A token that is neither ``N`` nor ``NxM`` is an argparse *usage* error: exit
    code 2, the flag named in the message, and — the half the criterion is
    really about — **no request constructed**. That last assertion is what
    separates this from an ordinary bad-value test: a malformed token must not
    reach the domain at all, whereas an out-of-range one must (the test below).

    ``30X20`` and ``30*20`` are here because the separator is ``x``, exactly
    (ADR-0022 chose it after reproducing zsh's glob failure on ``*``); a
    lookalike is a usage error rather than a silent synonym.
    """
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["generate", "--size", token])

    assert excinfo.value.code == cli.ExitCode.USAGE
    assert captured_requests == []


def test_cli_names_the_flag_in_a_malformed_token_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The other half of AC-064: the message has to say which flag."""
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["generate", "--size", "30x"])

    assert "--size" in capsys.readouterr().err


def test_cli_out_of_range_side_rejected_by_domain_not_argparse(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-065 / TestCLI_OutOfRangeSideRejectedByDomainNotArgparse (negative).

    ``--size 40x20`` is well formed, so it parses; the width is out of range, so
    the *domain* refuses it — the tool's own message, naming the offending side,
    and exit code 3. Never argparse's exit code 2, which is what a ``choices=``
    or a range-checking ``type=`` on the flag would produce (ADR-0010, G-2).

    The whole point is the pair of assertions: that the exit code is
    ``INVALID_INPUT`` *and* not ``USAGE``. Either alone would pass under the
    wrong placement.
    """
    exit_code = cli.main(["generate", "--size", "40x20"])

    assert exit_code == cli.ExitCode.INVALID_INPUT
    assert exit_code != cli.ExitCode.USAGE

    message = capsys.readouterr().err
    assert message.startswith(f"{cli.PROG}: error: ")
    assert "width" in message
    assert "40" in message


def test_cli_out_of_range_height_is_refused_by_the_domain_too() -> None:
    """The same claim on the other axis, so the rule is not "the first number".

    ``--size 30x9`` is legal on the width and one short on the height.
    """
    assert cli.main(["generate", "--size", "30x9"]) == cli.ExitCode.INVALID_INPUT


def test_the_size_help_documents_both_forms(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--help`` has to teach the rectangular form; nothing else advertises it."""
    with pytest.raises(SystemExit):
        cli.main(["generate", "--help"])

    out = capsys.readouterr().out
    assert "WxH" in out


def test_main_normalises_an_absent_export_flag_to_an_empty_tuple(
    captured_requests: list[orchestrator.GenerationRequest],
) -> None:
    cli.main(["generate"])
    assert captured_requests[0].export_formats == ()


# --------------------------------------------------------------------------
# Domain error -> exit code
# --------------------------------------------------------------------------

ERROR_EXIT_CODES = [
    (errors.SizeOutOfRange, cli.ExitCode.INVALID_INPUT),
    (errors.InvalidDensity, cli.ExitCode.INVALID_INPUT),
    (errors.UnknownLibraryImage, cli.ExitCode.INVALID_INPUT),
    # CARD-015 (AC-008): the user's own file being unreadable is an *input*
    # error, not the export failure the wide ``except OSError`` in ``main``
    # would once have reported it as.
    (errors.UnreadableImage, cli.ExitCode.INVALID_INPUT),
    # CARD-026 (AC-076/AC-077): a picture that read perfectly but is too
    # differently shaped from the requested grid. The same group for the same
    # reason — the user goes and changes what they passed in — and pointedly a
    # row of its own rather than a subclass of ``UnreadableImage``, since the
    # file is not what is wrong.
    (errors.ImageNeedsManualCrop, cli.ExitCode.INVALID_INPUT),
    # CARD-033 (AC-098): a bare ``--size N`` too small to follow the source's
    # own shape. The interesting row of this table, because it has **no entry
    # in ``cli._EXIT_CODES``** — it subclasses ``SizeOutOfRange``, so
    # ``exit_code_for``'s MRO walk finds the group through the base class. That
    # walk was written for exactly this, and this row is what pins it working:
    # break the subclassing and the parametrized test below reports
    # INTERNAL_ERROR while every other row stays green.
    (errors.SizeTooSmallForSource, cli.ExitCode.INVALID_INPUT),
    (errors.InvalidPuzzleName, cli.ExitCode.INVALID_INPUT),
    (errors.UnsupportedDifficulty, cli.ExitCode.INVALID_INPUT),
    (errors.GenerationAbandoned, cli.ExitCode.GENERATION_FAILED),
    (errors.SolverTimeout, cli.ExitCode.GENERATION_FAILED),
    (errors.ExportRejected, cli.ExitCode.EXPORT_REJECTED),
]


def test_every_domain_error_has_an_exit_code() -> None:
    """The mapping covers the whole hierarchy — no error can fall through."""
    declared = {
        obj
        for obj in vars(errors).values()
        if isinstance(obj, type)
        and issubclass(obj, errors.NonogramError)
        and obj is not errors.NonogramError
    }
    assert declared == {error for error, _ in ERROR_EXIT_CODES}


@pytest.mark.parametrize(
    ("error_class", "expected"),
    ERROR_EXIT_CODES,
    ids=[error.__name__ for error, _ in ERROR_EXIT_CODES],
)
def test_domain_error_maps_to_its_exit_code(
    error_class: type[errors.NonogramError],
    expected: cli.ExitCode,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(request: orchestrator.GenerationRequest) -> orchestrator.Puzzle:
        raise error_class("something the user needs to hear")

    monkeypatch.setattr(orchestrator, "generate", fail)

    exit_code = cli.main(["generate", "--size", "10"])

    assert exit_code == expected
    assert exit_code != cli.ExitCode.OK
    captured = capsys.readouterr()
    assert "something the user needs to hear" in captured.err
    assert captured.out == ""


def test_exit_code_lookup_follows_the_error_mro() -> None:
    class SizeFarTooLarge(errors.SizeOutOfRange):
        pass

    assert cli.exit_code_for(SizeFarTooLarge()) == cli.ExitCode.INVALID_INPUT


def test_unmapped_domain_error_is_reported_as_internal() -> None:
    class Unmapped(errors.NonogramError):
        pass

    assert cli.exit_code_for(Unmapped()) == cli.ExitCode.INTERNAL_ERROR


def test_non_domain_exceptions_are_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only NonogramError becomes an exit code; bugs keep their traceback."""

    def boom(request: orchestrator.GenerationRequest) -> orchestrator.Puzzle:
        raise RuntimeError("bug")

    monkeypatch.setattr(orchestrator, "generate", boom)
    with pytest.raises(RuntimeError):
        cli.main(["generate"])


# --------------------------------------------------------------------------
# Orchestrator stub and layering (ADR-0007)
# --------------------------------------------------------------------------


# ADR-0007's layers, innermost last. ``orchestrator`` is the only thing that
# composes capabilities, and ``errors`` is the shared foundation every layer
# may raise from. Everything *else* under ``nonogram/`` is a capability package
# (``sourcing/``, ``clues.py``, ``solver/``, ``difficulty.py``, ``export/``,
# and whatever a later card adds) — which is why the capability set is
# discovered from disk rather than listed.
#
# The inbound adapters are the one thing that *is* listed, and the listing is
# the point: ADR-0019 adds COMP-008 (``web``) as a sibling of COMP-001
# (``cli``) at the same rank, so both may import the orchestrator and nothing
# else about the rule changes. A guard with an allowlist is weaker than a guard
# without one (ADR-0019, Negative), so this set is closed at two names and is
# deliberately not a pattern — a third adapter is a decision, not a rename.
# ``test_the_adapter_allowlist_is_closed_at_the_two_known_adapters`` fails if it
# ever grows.
_ADAPTERS = frozenset({"cli", "web"})
_ORCHESTRATOR = "orchestrator"
_SHARED = frozenset({"errors"})

# The one import permitted *within* the adapter rank, in this direction only.
# ADR-0008 keeps a single ``[project.scripts]`` console entry point, and
# ADR-0019 puts ``nonogram serve`` in the argparse tree that entry point owns
# — so launching COMP-008 means ``cli`` imports ``web``. That is a launch edge,
# not a call between two request paths: the CLI never routes HTTP and the web
# adapter never parses argv. The reversed pair stays forbidden and is pinned as
# such by ``test_the_import_rule_rejects_each_forbidden_edge`` below, which is
# what keeps this exemption a single directed edge rather than "adapters may
# import each other".
_LAUNCH_EDGE = ("cli", "web")

_ADAPTER_RANK = 0
_ORCHESTRATOR_RANK = 1
_CAPABILITY_RANK = 2
_SHARED_RANK = 3

_PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "nonogram"
if not _PACKAGE_DIR.is_dir():  # pragma: no cover - installed-only checkout
    _PACKAGE_DIR = Path(nonogram.__file__).parent


def _discover_modules() -> dict[str, Path]:
    """Every module in the package, as ``{dotted name: file}``.

    Found by walking ``src/nonogram/**/*.py`` on disk, so a module a later card
    adds is covered from the moment it lands — this test never has to be edited
    to keep the ADR-0007 rule enforced.
    """
    modules: dict[str, Path] = {}
    for path in sorted(_PACKAGE_DIR.rglob("*.py")):
        parts = path.relative_to(_PACKAGE_DIR).with_suffix("").parts
        if parts[-1] == "__init__":  # a package is named by its directory
            parts = parts[:-1]
        modules[".".join(("nonogram", *parts))] = path
    return modules


_MODULES = _discover_modules()


def _component(module: str) -> str | None:
    """The top-level name under ``nonogram`` a module belongs to.

    ``nonogram.solver.line`` and ``nonogram.solver`` are both the ``solver``
    component; ``nonogram`` itself belongs to none.
    """
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else None


def _rank(component: str | None) -> int:
    if component in _ADAPTERS:
        return _ADAPTER_RANK
    if component is None or component == _ORCHESTRATOR:
        # ``nonogram/__init__.py`` is not a capability; it sits with the
        # orchestrator in that it may not reach outward to the adapter.
        return _ORCHESTRATOR_RANK
    if component in _SHARED:
        return _SHARED_RANK
    return _CAPABILITY_RANK


def _relative_base(module: str, path: Path, level: int, tail: str | None) -> str:
    """Resolve ``from ..x import y`` against the importing module."""
    base = module if path.name == "__init__.py" else module.rpartition(".")[0]
    for _ in range(level - 1):
        base = base.rpartition(".")[0]
    return f"{base}.{tail}" if tail else base


def _package_imports(module: str, path: Path) -> set[str]:
    """Names inside ``nonogram`` that ``module`` imports, read from its source."""
    imported: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = (
                _relative_base(module, path, node.level, node.module)
                if node.level
                else (node.module or "")
            )
            if not base:
                continue
            imported.add(base)
            imported.update(f"{base}.{alias.name}" for alias in node.names)
    return {
        name
        for name in imported
        if name == "nonogram" or name.startswith("nonogram.")
    }


def _imported_components(module: str, path: Path) -> set[str]:
    return {
        component
        for name in _package_imports(module, path)
        if (component := _component(name)) is not None
    }


def _outward_imports(imports: dict[str, set[str]]) -> dict[str, list[str]]:
    """The ADR-0007 rule itself: ``rank(imported) > rank(importer)``, always.

    Takes ``{dotted module: the components it imports}`` rather than reading
    the disk itself, so the rule can be exercised against a fabricated package
    below and cannot pass vacuously.

    Three imports are exempt. The first two are about *identity* rather than
    about direction:

    * a module importing its own component (``solver.search`` importing
      ``solver.propagate``) — that is a module's internals, not a dependency
      between layers;
    * the package root, ``nonogram`` itself, which appears in the walk for
      every ``from nonogram import x``. It re-exports nothing (pinned by
      ``test_package_root_imports_no_submodule``), so importing it couples the
      importer to nothing at all.

    The third, :data:`_LAUNCH_EDGE`, *is* about direction and is the only one:
    ``cli`` may import ``web`` because ADR-0008's single console entry point
    puts ``nonogram serve`` in ``cli.py``'s argparse tree. It is one ordered
    pair, not a rule about the adapter rank — ``web`` importing ``cli`` is
    still a violation, and so is every capability importing either of them.
    """
    offenders: dict[str, list[str]] = {}
    for module, components in imports.items():
        own = _component(module)
        outward = sorted(
            other
            for other in components
            if other is not None
            and other != own
            and (own, other) != _LAUNCH_EDGE
            and _rank(other) <= _rank(own)
        )
        if outward:
            offenders[module] = outward
    return offenders


def test_the_import_walk_actually_sees_the_package() -> None:
    """Guard the guard: an empty or misrooted walk must not pass silently."""
    assert {
        "nonogram",
        "nonogram.cli",
        "nonogram.web",
        "nonogram.orchestrator",
        "nonogram.errors",
    } <= set(_MODULES)


def test_the_adapter_allowlist_is_closed_at_the_two_known_adapters() -> None:
    """ADR-0019's allowlist is two names, and staying two names is the rule.

    The exemption this guard grants is the weakest part of it (ADR-0019,
    Negative): every name in :data:`_ADAPTERS` is a module allowed to import
    the orchestrator, so the set growing quietly — by a rename, by a helper
    package someone thought of as "adapter-ish" — is exactly how the rule
    erodes. Pinning the literal set means adding a third adapter has to be a
    deliberate edit to this line, reviewed as the architectural change it is.
    """
    assert _ADAPTERS == {"cli", "web"}
    assert _rank("cli") == _rank("web") == _ADAPTER_RANK


def test_the_launch_edge_is_closed_at_the_single_ordered_pair() -> None:
    """The *second* exemption gets the same pin as the first.

    :data:`_ADAPTERS` is pinned literally above because a set that grows
    quietly is how the rule erodes; :data:`_LAUNCH_EDGE` is an exemption of
    exactly the same kind and had no equivalent pin.
    ``test_the_import_rule_rejects_each_forbidden_edge[web-to-cli]`` catches the
    reverse pair being added, but not a *different* pair — turning this into a
    container of edges and adding, say, ``("export", "web")`` would be caught by
    nothing, because the forbidden-edge parametrisation enumerates named edges
    and that one is not among them.

    So the assertion is on the literal value and on its type: one ordered pair,
    not a set of them. Widening it has to be a deliberate edit to this line.
    """
    assert _LAUNCH_EDGE == ("cli", "web")
    assert isinstance(_LAUNCH_EDGE, tuple)
    assert len(_LAUNCH_EDGE) == 2


def test_every_import_in_the_package_points_inward() -> None:
    """ADR-0007's dependency rule, as the one invariant it actually is.

    ``cli -> orchestrator -> capability modules -> errors``: an import may only
    reach a *deeper* rank than the module making it. That single comparison
    covers all four directional edges at once — nothing inward of the adapter
    imports ``cli``; no capability imports another capability laterally; no
    capability reaches back out to the orchestrator (the edge this package had
    no real instance of until COMP-002 acquired a body); and ``errors`` — the
    innermost layer, which every layer may raise from — imports nothing back,
    so two capabilities cannot couple through it either.

    The rule is applied to every module the walk finds on disk, including ones
    no card has written yet, which is why this test never needs editing as the
    package grows.
    """
    imports = {
        module: _imported_components(module, path) for module, path in _MODULES.items()
    }

    assert not _outward_imports(imports), (
        "ADR-0007 violation — these imports point outward or sideways: "
        f"{_outward_imports(imports)}"
    )


@pytest.mark.parametrize(
    ("module", "imported", "edge"),
    [
        pytest.param("nonogram.solver.search", "cli", "capability -> adapter", id="cap-to-cli"),
        # The same edge against the *second* adapter. ADR-0019 widened the
        # allowlist, and this is the half of it that must not have widened:
        # a capability reaching COMP-008 is the same violation as reaching
        # COMP-001, and would be invisible if only ``cli`` were checked.
        pytest.param("nonogram.solver.search", "web", "capability -> web adapter", id="cap-to-web"),
        pytest.param("nonogram.solver.search", "export", "capability -> capability", id="lateral"),
        pytest.param(
            "nonogram.sourcing",
            "orchestrator",
            "capability -> orchestrator",
            id="cap-to-orchestrator",
        ),
        pytest.param("nonogram.errors", "solver", "shared -> capability", id="errors-reaches-back"),
        pytest.param("nonogram.orchestrator", "cli", "orchestrator -> adapter", id="orch-to-cli"),
        pytest.param(
            "nonogram.orchestrator", "web", "orchestrator -> web adapter", id="orch-to-web"
        ),
        # The reverse of :data:`_LAUNCH_EDGE`, and the reason that exemption is
        # an ordered pair rather than "the adapter rank is flat". ``cli``
        # importing ``web`` is ADR-0008's one console entry point launching
        # COMP-008; ``web`` importing ``cli`` would be the web adapter reaching
        # into argv parsing and exit codes, which is not a thing it has any
        # business doing.
        pytest.param("nonogram.web.server", "cli", "web adapter -> cli adapter", id="web-to-cli"),
    ],
)
def test_the_import_rule_rejects_each_forbidden_edge(
    module: str, imported: str, edge: str
) -> None:
    """Guard the guard, part two: a rank table that had silently degenerated
    (every module the same rank, say) would let the test above pass on an
    empty result. So the rule is shown rejecting one fabricated import per
    forbidden edge — including the capability -> orchestrator one that had no
    real instance in the package before CARD-005.
    """
    assert _outward_imports({module: {imported}}) == {module: [imported]}, edge


def test_the_import_rule_allows_the_legitimate_edges() -> None:
    """The mirror image: the arrows ADR-0007's component diagram does draw."""
    assert not _outward_imports(
        {
            "nonogram.cli": {"orchestrator", "errors", "web"},  # web: the launch edge
            "nonogram.web.handler": {"orchestrator", "errors", "export", "web"},
            "nonogram.orchestrator": {"sourcing", "clues", "solver", "errors"},
            "nonogram.solver.search": {"solver", "errors"},  # own package
            "nonogram.sourcing": {"errors"},
        }
    )


def test_the_adapter_does_import_the_orchestrator() -> None:
    """The one dependency arrow this card establishes (COMP-001 -> COMP-002)."""
    assert "nonogram.orchestrator" in _package_imports(
        "nonogram.cli", _MODULES["nonogram.cli"]
    )


def test_the_web_adapter_never_imports_the_cli_adapter() -> None:
    """ADR-0019's siblings, read off disk rather than off a fabricated dict.

    ``test_the_import_rule_rejects_each_forbidden_edge`` shows the *rule*
    rejecting ``web -> cli``; this shows the package not attempting it. The two
    fail for different reasons — the rule degenerating versus COMP-008 actually
    reaching for argv — and only this one would catch a real import landing in
    ``web/`` behind a rule that had been quietly loosened.

    What this loop consumes is the *filtered* set, not ``_MODULES`` — so the
    non-empty assertion has to be about the filter (AC-059). A selector that
    stopped matching (a renamed component, a moved package) would loop zero
    times and report green while enforcing nothing. The four modules are
    pinned by name rather than by count, so a module vanishing from the sweep
    fails and a module being added does not.
    """
    web_modules = {
        module: path for module, path in _MODULES.items() if _component(module) == "web"
    }
    missing = {
        "nonogram.web",
        "nonogram.web.handler",
        "nonogram.web.pages",
        "nonogram.web.server",
    } - set(web_modules)
    assert not missing, f"web modules missing from the sweep: {sorted(missing)}"

    for module, path in web_modules.items():
        assert "cli" not in _imported_components(module, path), module


def test_package_root_imports_no_submodule() -> None:
    """``nonogram/__init__.py`` re-exports nothing, so import order cannot leak.

    Importing a capability module must never drag the adapter in behind it.
    """
    assert not _package_imports("nonogram", _MODULES["nonogram"])
    assert nonogram.__version__


# --------------------------------------------------------------------------
# The installed console entry point (ADR-0008)
# --------------------------------------------------------------------------


def test_the_console_script_runs_as_an_installed_command() -> None:
    """``[project.scripts]`` is a contract only an out-of-process run checks.

    Every other test calls ``cli.main([...])`` directly, which would still pass
    if the entry point named a function that does not exist. Skipped rather
    than failed when the package is not installed in the running interpreter.
    """
    script = shutil.which("nonogram", path=str(Path(sys.executable).parent)) or shutil.which(
        "nonogram"
    )
    if script is None:
        pytest.skip("the `nonogram` console script is not installed on PATH")

    result = subprocess.run(
        [script, "--help"], capture_output=True, text=True, timeout=60, check=False
    )

    assert result.returncode == 0, result.stderr
    assert "generate" in result.stdout
