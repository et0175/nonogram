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
import re
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


def test_cli_bare_size_token_reaches_the_domain_unsquared(
    captured_requests: list[orchestrator.GenerationRequest],
) -> None:
    """AC-063 / TestCLI_BareSizeTokenReachesTheDomainUnsquared (boundary).

    **Renamed by CARD-033's cycle-1 review.** Until then this was
    ``TestCLI_SquareSizeShorthandSetsBothSides`` /
    ``test_cli_square_size_shorthand_sets_both_sides``, which after the change
    below asserted the opposite of what it was called: the token now sets
    exactly *one* side. The rename is queued alongside AC-063's own amendment
    in ``meta/architecture/inputs/raw-requirements.md``, so the criterion's
    ``test:`` field and ``trace.yml``'s two rows move with it; both still name
    the old id until that intake line is processed.

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


@pytest.mark.parametrize("density", ["0", "100"])
def test_cli_degenerate_density_exits_like_any_out_of_range_density(
    density: str, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-A (CARD-078): the handoff checkpoint, verbatim.

    ``--density 0`` must exit in the same code family as ``--density 150`` and
    write nothing. The "writes nothing" half is asked with ``--export json``,
    because without it *no* run writes a file and the assertion would pass for
    a reason that has nothing to do with this card — the control below is what
    gives it meaning.
    """
    monkeypatch.chdir(tmp_path)
    export = ["--export", "json", "--out", str(tmp_path)]

    code = cli.main(["generate", "--mode", "random", "--size", "10", "--density", density, *export])

    assert code == cli.main(
        ["generate", "--mode", "random", "--size", "10", "--density", "150", *export]
    )
    assert code == cli.ExitCode.INVALID_INPUT
    assert list(tmp_path.iterdir()) == []

    # The control: the same command at a legal density does write one.
    assert cli.main(["generate", "--mode", "random", "--size", "10", "--density", "50", *export]) == cli.ExitCode.OK
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("density", ["1", "99"])
def test_cli_accepts_the_new_bounds(density: str, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The other half of the checkpoint: 1 and 99 still generate."""
    monkeypatch.chdir(tmp_path)

    code = cli.main(["generate", "--mode", "random", "--size", "10", "--density", density])

    assert code == cli.ExitCode.OK


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
    # CARD-234: a book title holding a character the packaged face has no
    # glyph for, refused rather than printed as .notdef boxes on a cover. Like
    # ``NotUniquelySolvable`` below, nothing in the CLI raises it — it comes
    # from the admin panel's book export — and like every row in this group,
    # what the user does about it is go and change what they typed.
    (errors.UnletterableTitle, cli.ExitCode.INVALID_INPUT),
    (errors.UnsupportedDifficulty, cli.ExitCode.INVALID_INPUT),
    (errors.GenerationAbandoned, cli.ExitCode.GENERATION_FAILED),
    (errors.SolverTimeout, cli.ExitCode.GENERATION_FAILED),
    # CARD-214: the reveal policy's refusal — a picture that could not be made
    # uniquely solvable within the share of its own answer we are willing to
    # give away. Grouped here with the other two for the reason the enum's
    # docstring gives: what the user does about it is "the run did not produce a
    # usable puzzle". Deliberately **not** a row in ``cli._EXIT_CODES`` either —
    # it subclasses ``GenerationAbandoned``, so ``exit_code_for``'s MRO walk
    # finds the group through the base class, the same extension path
    # ``SizeTooSmallForSource`` takes above for the input group.
    (errors.GivenCellsCapExceeded, cli.ExitCode.GENERATION_FAILED),
    # CARD-080: the admin's storage boundary refusing a grid the solver would
    # not certify. No CLI path raises it — the row exists because
    # ``test_every_domain_error_has_an_exit_code`` below requires every
    # declared domain error to be grouped, and "nothing reaches it from here"
    # is not a reason to leave it falling through to INTERNAL_ERROR, which is
    # reserved for a mapping gap.
    (errors.NotUniquelySolvable, cli.ExitCode.GENERATION_FAILED),
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
# without one (ADR-0019, Negative), so the set below is closed and is
# deliberately not a pattern: it grows only by a deliberate edit to that line,
# reviewed as the architectural change admitting an adapter is.
# ``test_the_adapter_allowlist_is_closed_and_grows_only_by_a_deliberate_edit``
# fails if it grows without one.
#
# The count lives in the set and nowhere else (CARD-264). This comment, that
# test's name and that test's first line each stated a count the set had
# already outgrown, directly above an assertion that pins it correctly -- and
# CARD-261 made this the first place a CLAUDE.md reader is sent, so a reader
# who believed the prose over the code would have deleted a correct entry.
# ``TestAdapterAllowlist_NoProseClaimsAStaleCount`` is why that cannot recur.
_ADAPTERS = frozenset({"cli", "web", "admin"})
_ORCHESTRATOR = "orchestrator"
_SHARED = frozenset({"errors", "limits"})

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
        "nonogram.limits",
    } <= set(_MODULES)


def test_the_adapter_allowlist_is_closed_and_grows_only_by_a_deliberate_edit() -> None:
    """ADR-0019's allowlist is closed, and staying closed is the rule.

    The exemption this guard grants is the weakest part of it (ADR-0019,
    Negative): every name in :data:`_ADAPTERS` is a module allowed to import
    the orchestrator, so the set growing quietly — by a rename, by a helper
    package someone thought of as "adapter-ish" — is exactly how the rule
    erodes. Pinning the literal set means admitting another adapter has to be
    a deliberate edit to this line, reviewed as the architectural change it is.

    The rule rather than a count (CARD-264). This test was named after a count
    and restated it here, while the assertion below had already outgrown it:
    ``admin`` was admitted, the pin did its job, and the prose did not move.
    A claim with no control, sitting on top of a control that works -- which
    is the shape ``admin`` itself would have been deleted over, once CARD-261
    pointed a CLAUDE.md reader at this line. Whatever :data:`_ADAPTERS` holds
    is the number, and it is written down once, below.
    """
    assert _ADAPTERS == {"cli", "web", "admin"}
    assert _rank("cli") == _rank("web") == _rank("admin") == _ADAPTER_RANK


#: A count of adapters *or of names*, in words or digits, up to two words
#: before the noun. A widened sibling of :data:`_ADAPTER_COUNT` rather than a
#: second copy of it, and the widening is the measured one: of the three stale
#: claims CARD-264 removed from this file, ``_ADAPTER_COUNT``'s shape reached
#: only one ("the two known adapters"); the other two counted *names* ("closed
#: at two names", "the allowlist is two names"), which is how a count of a set
#: gets written when the set's members are strings. The two patterns answer
#: different questions over different files and are deliberately not shared:
#: ``_ADAPTER_COUNT`` denies a count of adapters anywhere in CLAUDE.md, this
#: one denies a count of either kind in this module's own prose about
#: :data:`_ADAPTERS`.
_COUNT_CLAIM = re.compile(
    r"\b(?:no|one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:\w+\s+){0,2}(?:adapters?|names?)\b",
    re.IGNORECASE,
)


class TestAdapterAllowlist_NoProseClaimsAStaleCount:
    """AC-7 (CARD-264): the prose around :data:`_ADAPTERS`, held to the set.

    Routed in from CARD-261's review cycle 1 as one finding and measured as
    three: the comment above the set, the name of the test that pins it, and
    that test's first line each stated a count the set had already outgrown,
    while the assertion itself was correct the whole time. The mechanism
    worked and the prose lied -- this card's subject in one function.

    **Why it was urgent rather than cosmetic.** CARD-261 added a pointer from
    CLAUDE.md into :data:`_ADAPTERS`, which made this the first *reachable*
    route from the file every session loads to this prose. A reader who
    follows it, finds the correct members under prose stating a smaller count,
    and concludes the extra member is the erosion would **delete a correct
    entry** -- worse than the stale count it replaced, and reachable only
    because of CARD-261.

    The prose now states the rule; the count is held in exactly one place, by
    the assertion, and this class reads :data:`_ADAPTERS` for it rather than
    restating it.
    """

    #: Identifier tokens that carry digits without claiming a count.
    _IDS = re.compile(r"\b(?:ADR|CARD|COMP|CAP|FR|NFR|AC|CON|US|EC)-\d+")

    @classmethod
    def _count_claims(cls, prose: str) -> list[str]:
        """Every count-of-a-set claim in ``prose``.

        Underscores become spaces first, because a test *name* is prose here:
        ``..._at_the_two_known_adapters`` is the loudest of the three claims --
        it is what every verbose run and every failure report prints -- and a
        reader that only saw spaces would walk straight past it. Issue ids are
        stripped, so ``ADR-0019`` is not read as a number.
        """
        plain = cls._IDS.sub("", prose.replace("_", " ").replace("*", "").replace("`", ""))
        return [match.group(0).strip() for match in _COUNT_CLAIM.finditer(plain)]

    @staticmethod
    def _allowlist_prose() -> dict[str, str]:
        """The three places this module writes prose about :data:`_ADAPTERS`.

        Located from the code: the assignment is found by ast and the comment
        block is whatever runs of ``#`` sit directly above it, and the test is
        found by **the assertion it makes**, never by its name -- the name is
        one of the things under judgement here, and a rule that found its
        subject by name would have been retired by the rename that fixed it.
        Each of the three is required to exist (ADR-0039/R2): a comment block
        that has gone, or a second test pinning the set, is a FAILURE rather
        than a quietly smaller sweep.
        """
        source = Path(__file__).resolve().read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source)

        assignments = [
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "_ADAPTERS"
                for target in node.targets
            )
        ]
        assert len(assignments) == 1, "expected exactly one _ADAPTERS assignment"
        index = assignments[0].lineno - 1
        comment: list[str] = []
        while index > 0 and lines[index - 1].lstrip().startswith("#"):
            index -= 1
            comment.append(lines[index])
        assert comment, "the comment block above _ADAPTERS has gone"

        pinning = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and any(
                isinstance(assertion.test, ast.Compare)
                and isinstance(assertion.test.left, ast.Name)
                and assertion.test.left.id == "_ADAPTERS"
                for assertion in ast.walk(node)
                if isinstance(assertion, ast.Assert)
            )
        ]
        assert len(pinning) == 1, [node.name for node in pinning]

        return {
            "the comment above _ADAPTERS": "\n".join(reversed(comment)),
            "the name of the test that pins it": pinning[0].name,
            "that test's first line": (ast.get_docstring(pinning[0]) or "").split("\n")[0],
        }

    def test_no_prose_around_the_allowlist_claims_a_count(self) -> None:
        prose = self._allowlist_prose()
        assert len(prose) == 3, prose

        claims = {
            where: found
            for where, text in prose.items()
            if (found := self._count_claims(text))
        }

        assert claims == {}, (
            "prose around _ADAPTERS states a count of the set. The count is "
            f"len(_ADAPTERS) == {len(_ADAPTERS)} and belongs in the assertion "
            f"and nowhere else: {claims}"
        )

    @pytest.mark.parametrize(
        ("where", "prose"),
        [
            pytest.param(
                "so this set is closed at two names and is deliberately not a"
                " pattern — a third adapter is a decision, not a rename.",
                "two names",
                id="the-module-comment",
            ),
            pytest.param(
                "test_the_adapter_allowlist_is_closed_at_the_two_known_adapters",
                "two known adapters",
                id="the-test-name",
            ),
            pytest.param(
                "ADR-0019's allowlist is two names, and staying two names is the rule.",
                "two names",
                id="the-docstrings-first-line",
            ),
        ],
    )
    def test_each_claim_this_card_removed_is_still_caught(
        self, where: str, prose: str
    ) -> None:
        """ADR-0039/R1: caught WITH the defect, missed WITHOUT it. The three
        strings are the shipped ones verbatim, so the rule is held to the
        defect it was written for on every run and not only on the day it was
        written."""
        assert prose in self._count_claims(where), self._count_claims(where)

    def test_the_rule_passes_prose_that_states_the_rule_instead(self) -> None:
        """The other state: the replacements this card shipped, and the one
        shape next to them that must stay legal -- "a guard without one" is
        not a count of anything."""
        for text in (
            "the set below is closed and grows only by a deliberate edit",
            "A guard with an allowlist is weaker than a guard without one",
            "whatever _ADAPTERS holds is the number",
        ):
            assert self._count_claims(text) == [], text

    def test_the_pinned_literal_holds_as_many_names_as_the_set_does(self) -> None:
        """AC-7's control reads ``len(_ADAPTERS)`` rather than restating it.

        The pinned literal is read off the assertion with ast, so this
        compares the set the guard consults against the set the pin declares
        without either number being written down here.
        """
        source = Path(__file__).resolve().read_text(encoding="utf-8")
        pinned = [
            assertion.test.comparators[0]
            for assertion in ast.walk(ast.parse(source))
            if isinstance(assertion, ast.Assert)
            and isinstance(assertion.test, ast.Compare)
            and isinstance(assertion.test.left, ast.Name)
            and assertion.test.left.id == "_ADAPTERS"
        ]
        assert len(pinned) == 1, pinned
        literal = pinned[0]
        assert isinstance(literal, ast.Set), ast.unparse(literal)

        assert len(_ADAPTERS) == len(literal.elts)
        assert len(_ADAPTERS) == len({ast.literal_eval(name) for name in literal.elts})


def test_the_shared_layer_is_closed_at_errors_and_limits() -> None:
    """Every layer may import a shared module, so :data:`_SHARED` gets the same
    literal pin as :data:`_ADAPTERS`: a module slipped into it quietly would be
    an unguarded channel between capabilities that may not import each other.
    ``limits`` joined ``errors`` in CARD-063 (ADR-0007 History) because the
    grid size range is needed by capabilities on both sides of that rule.
    """
    assert _SHARED == {"errors", "limits"}
    assert _rank("errors") == _rank("limits") == _SHARED_RANK


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
        pytest.param("nonogram.limits", "sourcing", "shared -> capability", id="limits-reaches-back"),
        # Two shared modules share a rank, so neither may import the other:
        # ``limits`` stays import-free, and the shared layer cannot become a
        # chain.
        pytest.param("nonogram.limits", "errors", "shared -> shared", id="limits-to-errors"),
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
            "nonogram.sourcing": {"errors", "limits"},
            "nonogram.difficulty": {"errors", "limits"},  # capabilities share limits
            "nonogram.web.pages": {"limits"},  # adapters may too
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
# The component map (CARD-261)
# --------------------------------------------------------------------------


_CLAUDE_MD = Path(__file__).resolve().parents[1] / "CLAUDE.md"

# A row of the canonical map: a module or package name, then whitespace, then
# whatever the row says about it. ``errors.py`` and ``sourcing/`` are both rows;
# a continuation line of a row is indented past the name column and so cannot
# match.
_MAP_ROW = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\.py|/)\s+\S")

# The same row shape as CLAUDE.md's retired layout block wrote it, plus any
# line naming a component id at all. CARD-261 moved every row to
# ``src/nonogram/__init__.py``; these two patterns are what notices a copy
# coming back.
_CLAUDE_MD_ROW = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*(?:\.py|/)\s{2,}\S")
_COMPONENT_ID = re.compile(r"COMP-\d")

# A count of adapters, in words or digits, up to two words before the noun:
# "three inbound adapters", "2 adapters", "the two pipeline adapters".
_ADAPTER_COUNT = re.compile(
    r"\b(?:no|one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:\w+\s+){0,2}adapters?\b",
    re.IGNORECASE,
)

# The id authority (ADR-0039/R2). The C4 component diagram pairs each COMP id
# with its module, and -- for the five capability modules -- with its CAP id:
#
#   Component(clues, "COMP-004 Clue Derivation", "Python — clues.py",
#             "CAP-002: run-length encodes every row and column ...")
#
# The separator is an em dash (U+2014) and ``_PUML_MODULE`` matches that and not
# a hyphen: a hyphen there is a shape this parser cannot analyse, so it is
# denied and named rather than guessed at.
#
# Nine of the ten are written with ``Component(`` and ``db/`` with
# ``ComponentDb(``, so the macro is matched by *prefix*: a parser that knew only
# ``Component(`` would miss COMP-010 and report the id column green with one
# tenth of it unread.
_PUML = (
    Path(__file__).resolve().parents[1]
    / "meta"
    / "architecture"
    / "c4"
    / "components-CTX-001.puml"
)

# The second authority, used for a CAP id's *existence* -- a cross-check on the
# diagram rather than a restatement of it.
_CAPABILITIES = (
    Path(__file__).resolve().parents[1]
    / "meta"
    / "architecture"
    / "domain"
    / "capabilities.yml"
)

_COMPONENT_MACRO = re.compile(r"^\s*Component\w*\(")
_COMPONENT_DECL = re.compile(
    r'^\s*Component\w*\(\s*[^,]+,\s*"(COMP-\d+)[^"]*",\s*"([^"]*)",\s*"(.*)"\s*\)\s*$'
)
# The technology argument reads ``Python — web/ (stdlib http.server)``: the
# module is the first token after the em dash, and the trailing parenthetical
# is not part of it.
_PUML_MODULE = re.compile(r"^Python\s+—\s+([A-Za-z_][A-Za-z0-9_]*)(?:\.py|/)")
# A capability is paired with its component by *leading* the description.
_PUML_CAPABILITY = re.compile(r"^(CAP-\d+):")
_CAP_ID = re.compile(r"CAP-\d+")
_CAP_ID_DECL = re.compile(r"^\s*-\s+id:\s*(CAP-\d+)\s*$")

# A map row's three structured columns: the name, then the COMP id and the CAP
# id where the row carries them. What follows is the English description, which
# no control in this file reads.
_ROW_IDS = re.compile(
    r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\.py|/)\s+"
    r"(?:(?P<component>COMP-\d+)\s+)?(?:(?P<capability>CAP-\d+)\s+)?\S"
)

# The modules the import walk enumerates that the C4 diagram pairs with no COMP
# id at all. A named exemption under ADR-0039/R3, not a skipped case: the
# exemption is itself a claim, so ``_id_defects`` holds this set in *both*
# directions -- a module that gains a diagram entry while the map still shows
# no id reds, and so does one that gains an id in the map while the diagram
# still pairs it with none. The absences themselves are asserted by
# ``test_the_three_modules_with_no_component_id_are_named_not_skipped``.
_WITHOUT_A_COMPONENT_ID = frozenset({"analysis", "errors", "limits"})


def _component_modules(modules: dict[str, Path]) -> set[str]:
    """The component names the import walk enumerates.

    Derived from :data:`_MODULES` -- the same on-disk walk ADR-0007's layering
    guard runs -- rather than hand-written, so the authority for "what
    components exist" is the package itself (ADR-0039/R2). ``nonogram`` itself
    belongs to no component and drops out.
    """
    return {
        component
        for module in modules
        if (component := _component(module)) is not None
    }


def _canonical_map(doc: str) -> tuple[list[str], list[str]]:
    """Parse the canonical map out of ``src/nonogram/__init__.py``'s docstring.

    Returns ``(row names in order, lines the parser could not analyse)``. A map
    row is a line indented exactly four spaces whose first token is a module or
    package name. The indent is the whole rule: this parser never looks for
    ``::``, so its reach is *every* four-space-indented line in the docstring,
    inside one of the literal blocks or not. Prose sits at indent zero and a
    row's continuation lines sit past the name column, so neither is mistaken
    for a row.

    Default-deny (ADR-0039/R2): a four-space-indented line that is *not* a row
    is returned as unanalysable, and :func:`_map_defects` turns that into a
    failure. A map written in a shape this parser cannot read is never a silent
    pass.
    """
    rows: list[str] = []
    unanalysable: list[str] = []
    for line in doc.splitlines():
        if not line.startswith("    "):
            continue
        body = line[4:]
        if not body or body[0].isspace():
            continue
        match = _MAP_ROW.match(body)
        if match is None:
            unanalysable.append(body.rstrip())
        else:
            rows.append(match.group(1))
    return rows, unanalysable


def _claude_md_rows(text: str) -> list[str]:
    """Component-map rows CLAUDE.md states in its own right, as ``line: text``.

    AC-3 shipped the shape in which CLAUDE.md carries none: it points at
    ``src/nonogram/__init__.py``, which it already named as canonical, so there
    is exactly one place a row can drift from. This is what reds if a second
    copy is pasted back in.

    Two disjuncts, and the second is deliberately wider than "a row". A
    ``COMP-NNN`` id is searched for *anywhere* in *any* line of the whole file
    -- running prose and fenced code blocks included, with no scoping to the
    layout block -- because an id in this file is the first column of a second
    copy, and the cheapest moment to refuse one is before the rest of the row
    arrives. The cost is a false positive: a future card that wants to name a
    single component id in a sentence must edit this guard deliberately, which
    is the intent. Both the breadth and its limit are pinned by
    ``TestComponentMap_WhatTheClaudeMdReaderAbsorbs`` rather than asserted
    here, so the extent of the hole cannot drift in either direction without a
    red.
    """
    return [
        f"{number}: {line.strip()}"
        for number, line in enumerate(text.splitlines(), start=1)
        if _CLAUDE_MD_ROW.match(line) or _COMPONENT_ID.search(line)
    ]


def _adapter_counts(text: str) -> list[str]:
    """Every place CLAUDE.md states a *count* of adapters, as ``line: text``.

    F-101(a). The retired layout block's worst error was its adapter count,
    and a corrected count kept inline is still a second copy of a fact the
    canonical map holds and ``_ADAPTERS`` closes -- prose with no ids, which is
    precisely the shape ``_claude_md_rows`` is known to miss. Rather than
    widen that reader to all prose, this denies the one shape of it that
    matters here.

    Markdown emphasis and code quoting are stripped before the search, because
    the shipped clause wrote the number as ``**three**``: a reader that only
    saw bare words would have passed the exact line this function exists to
    refuse. Deny-side, so the cost is a false positive -- a future sentence
    that happens to put a number two words from "adapter" must reword or edit
    this guard -- and ``test_the_reader_finds_a_count_when_there_is_one`` pins
    both the match and the near miss.
    """
    plain = text.replace("*", "").replace("`", "")
    return [
        f"{number}: {line.strip()}"
        for number, line in enumerate(plain.splitlines(), start=1)
        if _ADAPTER_COUNT.search(line)
    ]


def _map_defects(
    components: set[str],
    rows: list[str],
    unanalysable: tuple[str, ...] | list[str] = (),
) -> dict[str, list[str]]:
    """Every way a component map and the package it describes can disagree.

    Takes the enumerated component set and the parsed rows rather than reading
    the disk itself, so the rule can be exercised against a fabricated package
    and a fabricated map below and cannot pass vacuously --
    :func:`_outward_imports` is written the same way and for the same reason.

    Default-deny in both directions. A component the walk found and no row
    names is a defect; a row naming something the walk did not find is a
    defect; a component named twice is a defect; and a line the parser could
    not analyse is a defect rather than a skipped line. Each is keyed by what
    went wrong and valued with the offending *names*, so a failure says which
    module or which row.

    The bound, stated rather than implied (AC-5): this holds the **row set**
    and nothing else -- the first column, as a set of names. It does not read
    the **COMP-id and CAP-id columns**, which are held separately and against
    their own authority by :func:`_id_defects`; naming them here because cycle
    1 found them folded into the word "description" and silently unheld. And it
    cannot judge a row's **English description** -- whether "scores 0..100 from
    the solver's rung tags" is an accurate account of ``difficulty.py`` is not a
    property any enumeration in this repository decides, and no test in this
    file claims it. A row may therefore be present, unique, correctly
    identified, and describe its module wrongly, and both controls will pass.
    Reviewing the English stays a human job; that is the one hole left, and
    ``test_a_wrong_description_is_the_one_hole_that_stays_open`` asserts it
    *is* a hole rather than leaving a reader to find out by experiment.
    """
    defects: dict[str, list[str]] = {}
    listed = set(rows)
    if missing := sorted(components - listed):
        defects["in the package, absent from the map"] = missing
    if dead := sorted(listed - components):
        defects["named by a row, absent from the package"] = dead
    if duplicated := sorted(name for name in listed if rows.count(name) > 1):
        defects["listed by more than one row"] = duplicated
    if unanalysable:
        defects["a map line the parser cannot analyse"] = sorted(unanalysable)
    return defects


def _c4_components(text: str) -> tuple[dict[str, tuple[str, str | None]], list[str]]:
    """Pair every component id with its module, from the C4 component diagram.

    Returns ``({module name: (COMP id, CAP id or None)}, declarations the
    parser could not analyse)``. This is the authority ADR-0039/R2 asks a
    guard's set to be derived from: the canonical map's id columns are checked
    against the model the project already keeps -- the same file
    ``meta/architecture/trace.yml`` and the C4 diagrams key on -- and not
    against a list of ids written in this file, which would be one more copy
    to drift (G-2).

    The CAP id is read from the description only where it *leads* it, which is
    the convention the diagram writes the five capability modules with. That is
    a narrower reach than "mentions a CAP id anywhere", and deliberately so: a
    description that names another capability in passing is making a reference,
    not a pairing. The declared cost of the narrowness is exactly one component
    today -- ``admin/``, whose description names CAP-006 mid-sentence, so this
    parser reads it as carrying none -- and
    ``test_the_capability_pairing_reads_only_a_leading_cap_id`` pins that set to
    one name, so a second component picking up the looser habit reds here
    instead of quietly dropping out of the CAP column's coverage.

    Default-deny (ADR-0039/R2). Every line whose first token is a
    ``Component*(`` macro must yield a COMP id *and* a module, or it is
    returned as unanalysable and :func:`_id_defects` turns that into a failure
    naming the line. Two declarations for one module are unanalysable too,
    because the dict would otherwise keep the last silently. The cost, declared
    as bound 3 of this card already declares its own: a macro added in a shape
    this parser cannot read -- an external-system component with no COMP id, a
    hyphen where the em dash is -- reds this file rather than passing silently,
    and the remedy the failure points at is to shape it as a declaration or to
    widen this parser on purpose.
    """
    pairs: dict[str, tuple[str, str | None]] = {}
    unanalysable: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if _COMPONENT_MACRO.match(line) is None:
            continue
        declaration = _COMPONENT_DECL.match(line)
        if declaration is None:
            unanalysable.append(f"{number}: {line.strip()[:72]}")
            continue
        component_id, technology, description = declaration.groups()
        module = _PUML_MODULE.match(technology)
        if module is None:
            unanalysable.append(f"{number}: cannot read a module from {technology!r}")
            continue
        if module.group(1) in pairs:
            unanalysable.append(f"{number}: a second declaration for {module.group(1)}")
            continue
        capability = _PUML_CAPABILITY.match(description)
        pairs[module.group(1)] = (
            component_id,
            capability.group(1) if capability is not None else None,
        )
    return pairs, unanalysable


def _capability_ids(text: str) -> set[str]:
    """Every capability id ``meta/architecture/domain/capabilities.yml`` lists.

    Existence, and nothing else. That file keys each CAP id to events,
    commands, aggregates, stories and requirements -- never to a component or a
    module -- so this is a second, independent authority for *is this a
    capability at all*, which is what kills an invented id such as ``CAP-009``
    even when it is paired with the right module. The pairing itself comes from
    the C4 diagram, and ``test_the_capability_registry_pairs_no_module``
    asserts that this file is not a second source for it.
    """
    return {
        match.group(1)
        for line in text.splitlines()
        if (match := _CAP_ID_DECL.match(line)) is not None
    }


def _map_row_ids(doc: str) -> list[tuple[str, str | None, str | None]]:
    """The canonical map's structured columns, row by row, in docstring order.

    ``(module name, COMP id or None, CAP id or None)``. Written beside
    :func:`_canonical_map` rather than folded into it so that function's
    signature, its callers and the mutants aimed at it stay as they shipped.

    Row selection is the same rule :func:`_canonical_map` applies -- a line
    indented exactly four spaces whose body does not itself start with
    whitespace -- and a line this pattern cannot read is skipped here rather
    than denied, because :func:`_canonical_map` has already returned that same
    line through its unanalysable channel and :func:`_map_defects` fails the
    suite on it. The two patterns accepting the same lines is not an assumption:
    ``test_the_two_row_readers_accept_exactly_the_same_lines`` pins it, so the
    skip above cannot become a silent pass if either pattern is narrowed.
    """
    rows: list[tuple[str, str | None, str | None]] = []
    for line in doc.splitlines():
        if not line.startswith("    "):
            continue
        body = line[4:]
        if not body or body[0].isspace():
            continue
        match = _ROW_IDS.match(body)
        if match is None:
            continue
        rows.append(
            (
                match.group("name"),
                match.group("component"),
                match.group("capability"),
            )
        )
    return rows


def _id_defects(
    components: set[str],
    authority: dict[str, tuple[str, str | None]],
    capability_ids: set[str],
    rows: list[tuple[str, str | None, str | None]],
    unanalysable: tuple[str, ...] | list[str] = (),
    exempt: frozenset[str] = _WITHOUT_A_COMPONENT_ID,
) -> dict[str, list[str]]:
    """Every way the canonical map's **id columns** and their authority disagree.

    :func:`_map_defects` holds the map's first column -- the set of names.
    This holds the two that follow it. Cycle 1 of this card found them unheld
    and demonstrated it: a wrong COMP id, a ``CAP-009`` belonging to nothing,
    and two rows claiming ``COMP-005`` while ``COMP-004`` vanished from the map
    entirely, all three green. A COMP id is not an English description -- it is
    a structured identifier with an authority -- so folding it into AC-5's
    description bound was the defect, not the authority's absence.

    Takes the enumerated sets rather than reading the disk, for the reason
    :func:`_map_defects` and :func:`_outward_imports` are written that way: the
    rule can then be exercised against a fabricated authority and a fabricated
    map and cannot pass vacuously.

    Ten defect kinds, each keyed by what went wrong and valued with the
    offending *names*. Four need no authority at all and hold unconditionally:
    an id claimed by two rows, an id no diagram enumerates, an id the diagram
    enumerates that no row carries, and a CAP id the capability registry does
    not list. Four compare the map's pairing against the diagram's in both
    directions. Two hold the ADR-0039/R3 exemption set itself, so a module
    moving in or out of "has no COMP id" is a red rather than a drift.

    The bound, stated rather than implied. A CAP id is paired here only where
    the diagram *leads* a description with it, and ``admin/``'s CAP-006 is
    named mid-sentence instead -- a hole of exactly one component, pinned to
    one component by ``test_the_capability_pairing_reads_only_a_leading_cap_id``
    rather than described. Beyond the ids, a row's English description stays
    unheld by anything (AC-5), and
    ``test_a_wrong_description_is_the_one_hole_that_stays_open`` asserts that it
    *is* a hole rather than leaving the next reader to find out by experiment.
    """
    defects: dict[str, list[str]] = {}
    if unanalysable:
        defects["a Component declaration the parser cannot analyse"] = sorted(
            unanalysable
        )

    claimed = [component for _, component, _ in rows if component is not None]
    if duplicated := sorted({name for name in claimed if claimed.count(name) > 1}):
        defects["a COMP id claimed by more than one row"] = duplicated

    enumerated = {component for component, _ in authority.values()}
    if invented := sorted(set(claimed) - enumerated):
        defects["a COMP id the component diagram does not enumerate"] = invented
    if unclaimed := sorted(enumerated - set(claimed)):
        defects["a COMP id the diagram enumerates and no row carries"] = unclaimed

    if mispaired := sorted(
        f"{name}: the map says {component or '-'}/{capability or '-'}, the "
        f"diagram says {authority[name][0]}/{authority[name][1] or '-'}"
        for name, component, capability in rows
        if name in authority and (component, capability) != authority[name]
    ):
        defects["a row whose ids are not the diagram's"] = mispaired

    if unpaired := sorted(components - exempt - set(authority)):
        defects["in the package, neither exempt nor paired by the diagram"] = unpaired
    if foreign := sorted(set(authority) - components):
        defects["paired by the diagram, absent from the package"] = foreign

    if stale := sorted(exempt & set(authority)):
        defects["exempted from a COMP id, but the diagram now pairs it"] = stale
    if labelled := sorted(
        name for name, component, _ in rows if name in exempt and component is not None
    ):
        defects["exempted from a COMP id, but the map now carries one"] = labelled

    if unknown := sorted(
        {capability for _, _, capability in rows if capability is not None}
        - capability_ids
    ):
        defects["a CAP id the capability registry does not enumerate"] = unknown
    return defects


class TestComponentMap_EveryComponentIsListedExactlyOnce:
    """AC-1. The canonical map and the package agree, name for name.

    The authority is the import walk above, not a list in this file.
    """

    def test_the_docstring_map_parses_into_rows(self) -> None:
        """Guard the guard: a parser that read nothing would pass AC-1 only by
        reporting every component missing -- but a parser that returned rows
        for *everything* would pass it vacuously. So the row count is pinned
        non-trivially before the comparison below is believed.
        """
        rows, unanalysable = _canonical_map(nonogram.__doc__ or "")

        assert not unanalysable, f"unanalysable map lines: {unanalysable}"
        assert len(rows) >= 10, rows

    def test_every_component_the_walk_finds_appears_exactly_once(self) -> None:
        rows, unanalysable = _canonical_map(nonogram.__doc__ or "")

        assert not _map_defects(_component_modules(_MODULES), rows, unanalysable), (
            "the canonical map in src/nonogram/__init__.py disagrees with the "
            "package the import walk enumerates: "
            f"{_map_defects(_component_modules(_MODULES), rows, unanalysable)}"
        )


class TestComponentMap_APlantedModuleAndAPlantedRowBothRed:
    """AC-2. The control defaults to deny, and the plants prove it.

    A derivation whose plant does not red is the defect this class exists to
    prevent, so each direction is shown against a fabricated package and a
    fabricated map -- and each failure is shown *naming* the offender, because
    a control that reds without saying what is wrong sends the next reader back
    to the diff.
    """

    def test_a_planted_module_absent_from_the_map_reds_naming_it(self) -> None:
        rows, _ = _canonical_map(nonogram.__doc__ or "")
        planted = _component_modules(_MODULES) | {"planted_component"}

        defects = _map_defects(planted, rows)

        assert defects == {"in the package, absent from the map": ["planted_component"]}

    def test_removing_the_planted_module_passes(self) -> None:
        rows, unanalysable = _canonical_map(nonogram.__doc__ or "")

        assert not _map_defects(_component_modules(_MODULES), rows, unanalysable)

    def test_a_planted_row_naming_nothing_reds_naming_the_row(self) -> None:
        rows, _ = _canonical_map(nonogram.__doc__ or "")

        defects = _map_defects(
            _component_modules(_MODULES), [*rows, "planted_row"]
        )

        assert defects == {"named by a row, absent from the package": ["planted_row"]}

    def test_a_second_row_for_one_component_reds_naming_it(self) -> None:
        rows, _ = _canonical_map(nonogram.__doc__ or "")

        defects = _map_defects(_component_modules(_MODULES), [*rows, "solver"])

        assert defects == {"listed by more than one row": ["solver"]}

    def test_a_line_the_parser_cannot_analyse_is_a_failure(self) -> None:
        """Not a silent pass (ADR-0039/R2)."""
        rows, _ = _canonical_map(nonogram.__doc__ or "")

        defects = _map_defects(
            _component_modules(_MODULES), rows, ["COMP-011  a row with no name"]
        )

        assert defects == {
            "a map line the parser cannot analyse": ["COMP-011  a row with no name"]
        }

    def test_the_parser_reports_a_row_it_cannot_read(self) -> None:
        """The plant one layer down: the unanalysable channel the test above
        feeds by hand is reachable from a real docstring, so a map rewritten in
        an unreadable shape reds instead of parsing to nothing.
        """
        rows, unanalysable = _canonical_map(
            "Layout::\n\n    COMP-012 no name here\n"
        )

        assert rows == []
        assert unanalysable == ["COMP-012 no name here"]


class TestComponentMap_ThereIsOneRowPerComponentAcrossBothFiles:
    """AC-3. One row per component in the whole repository, not one per file.

    The shape that shipped: CLAUDE.md's layout block carries no row of its own
    and points at ``src/nonogram/__init__.py``, which CLAUDE.md already named
    as canonical. Two copies of one statement is the defect (CARD-257,
    CARD-259), and a copy inside the file every session loads is the copy that
    drifted for 51 waves.

    Bound, stated rather than implied: this notices a row written in the
    tabular shape the retired block used, or any line naming a ``COMP-NNN``
    id. A component map restated as running **prose with no ids** would evade
    it -- and because a declared bound is a claim (ADR-0039/R3), that hole is
    not left as a sentence here.
    ``TestComponentMap_WhatTheClaudeMdReaderAbsorbs`` measures it: every shape
    this reader must catch and every shape it is known to miss is a committed
    case, so a reader can tell prose-that-reds from prose-that-evades without
    running the experiment, and the extent of the hole cannot change in either
    direction without a red.
    """

    def test_claude_md_carries_no_component_row_and_names_no_component_id(
        self,
    ) -> None:
        rows = _claude_md_rows(_CLAUDE_MD.read_text(encoding="utf-8"))

        assert not rows, (
            "CLAUDE.md carries a component-map row again, or names a COMP-NNN "
            "id -- AC-3 keeps the map in src/nonogram/__init__.py alone, and "
            "the id ban is wider than the row ban on purpose (see "
            f"_claude_md_rows): {rows}"
        )

    def test_a_planted_row_in_claude_md_reds_naming_it(self) -> None:
        """The plant for the direction above. The real file is read by the test
        before this one; this feeds the same reader a fabricated CLAUDE.md, so
        the green is not a reader that matches nothing.
        """
        planted = (
            "## Architecture\n"
            "\n"
            "```\n"
            "cli.py           COMP-001  the only inbound adapter\n"
            "```\n"
        )

        assert _claude_md_rows(planted) == [
            "4: cli.py           COMP-001  the only inbound adapter"
        ]

    def test_claude_md_points_at_the_canonical_map(self) -> None:
        """Dropping the rows is only half of AC-3: a reader of CLAUDE.md has to
        be told where the map went, or the instruction file simply stops
        describing the package.
        """
        text = _CLAUDE_MD.read_text(encoding="utf-8")

        assert "src/nonogram/__init__.py" in text


class TestComponentMap_TheIdColumnsAreHeldToTheC4Diagram:
    """F-102. The map's COMP id is the diagram's; its CAP id is a capability.

    Cycle 1 of this card showed the two id columns unheld and demonstrated it
    rather than arguing it: a wrong COMP id, a ``CAP-009`` belonging to
    nothing, and two rows claiming ``COMP-005`` while ``COMP-004`` vanished
    from the map entirely -- all three green, because :func:`_map_defects`
    reads only a row's first column. AC-5's bound said "description", and a
    structured identifier with an authority is not a description.

    The authority is ``meta/architecture/c4/components-CTX-001.puml``
    (ADR-0039/R2), cross-checked for CAP-id existence against
    ``meta/architecture/domain/capabilities.yml``. What stays unheld after this
    class is the English prose of a row, and the last test here asserts that it
    *is* unheld instead of leaving the next reader to discover it by plant.
    """

    def test_the_diagram_parses_into_component_id_pairs(self) -> None:
        """Guard the guard. A parser that read nothing would pass the
        comparison below by reporting every id unclaimed; a parser that read
        only ``Component(`` would pass it with one tenth of the column unread,
        because ``db/`` is declared with ``ComponentDb(``. Both readings are
        pinned here before the comparison is believed.
        """
        authority, unanalysable = _c4_components(_PUML.read_text(encoding="utf-8"))

        assert not unanalysable, f"unanalysable Component declarations: {unanalysable}"
        assert len(authority) >= 10, authority
        assert authority["db"] == ("COMP-010", None), (
            "the ComponentDb( arm is unreached -- a Component(-only parser "
            f"misses COMP-010 and says so by omission: {authority.get('db')}"
        )
        assert authority["sourcing"] == ("COMP-003", "CAP-001"), authority["sourcing"]

    def test_the_map_and_the_diagram_agree_on_every_id(self) -> None:
        authority, unanalysable = _c4_components(_PUML.read_text(encoding="utf-8"))
        capabilities = _capability_ids(_CAPABILITIES.read_text(encoding="utf-8"))
        rows = _map_row_ids(nonogram.__doc__ or "")

        defects = _id_defects(
            _component_modules(_MODULES), authority, capabilities, rows, unanalysable
        )

        assert not defects, (
            "the canonical map's id columns disagree with "
            f"meta/architecture/c4/components-CTX-001.puml: {defects}"
        )

    def test_a_wrong_component_id_reds_naming_the_row(self) -> None:
        """Cycle 1's plant C, as a committed case: one row carrying another
        component's COMP id and an invented CAP id.
        """
        authority = {"solver": ("COMP-005", "CAP-003"), "clues": ("COMP-004", "CAP-002")}
        planted = [("solver", "COMP-004", "CAP-009"), ("clues", "COMP-004", "CAP-002")]

        defects = _id_defects(
            {"solver", "clues"}, authority, {"CAP-002", "CAP-003"}, planted
        )

        assert defects == {
            "a COMP id claimed by more than one row": ["COMP-004"],
            "a COMP id the diagram enumerates and no row carries": ["COMP-005"],
            "a row whose ids are not the diagram's": [
                "solver: the map says COMP-004/CAP-009, the diagram says "
                "COMP-005/CAP-003"
            ],
            "a CAP id the capability registry does not enumerate": ["CAP-009"],
        }

    def test_two_rows_claiming_one_id_red_naming_it_and_the_vanished_one(self) -> None:
        """Cycle 1's plant D. This arm needs no authority at all -- "two rows
        claim one id" and "an id vanished from the map" are uniqueness and a
        bijection over the column itself -- which is why it is asserted
        separately from the pairing comparison above.
        """
        authority = {"clues": ("COMP-004", "CAP-002"), "solver": ("COMP-005", "CAP-003")}
        planted = [("clues", "COMP-005", "CAP-002"), ("solver", "COMP-005", "CAP-003")]

        defects = _id_defects(
            {"clues", "solver"}, authority, {"CAP-002", "CAP-003"}, planted
        )

        assert defects == {
            "a COMP id claimed by more than one row": ["COMP-005"],
            "a COMP id the diagram enumerates and no row carries": ["COMP-004"],
            "a row whose ids are not the diagram's": [
                "clues: the map says COMP-005/CAP-002, the diagram says "
                "COMP-004/CAP-002"
            ],
        }

    def test_a_cap_id_the_registry_does_not_enumerate_reds_naming_it(self) -> None:
        """The existence arm on its own. The map and the diagram agree here, so
        the only thing refusing ``CAP-009`` is the capability registry -- which
        is what makes it a second, independent authority rather than a
        restatement of the first.
        """
        defects = _id_defects(
            {"solver"},
            {"solver": ("COMP-005", "CAP-009")},
            {"CAP-001", "CAP-002", "CAP-003"},
            [("solver", "COMP-005", "CAP-009")],
        )

        assert defects == {
            "a CAP id the capability registry does not enumerate": ["CAP-009"]
        }

    @pytest.mark.parametrize(
        ("declaration", "offender"),
        [
            pytest.param(
                'Component_Ext(printer, "A Printer", "paper", "no id")',
                '1: Component_Ext(printer, "A Printer", "paper", "no id")',
                id="a macro whose label is not a COMP id",
            ),
            pytest.param(
                'Component(cli, "COMP-001 CLI", "Python - cli.py", "Thin.")',
                "1: cannot read a module from 'Python - cli.py'",
                id="a hyphen where the em dash is",
            ),
            pytest.param(
                'Component(cli, "COMP-001 CLI", "Python — cli.py", "Thin.")\n'
                'Component(two, "COMP-099 Again", "Python — cli.py", "Thin.")',
                "2: a second declaration for cli",
                id="two declarations for one module",
            ),
        ],
    )
    def test_a_declaration_the_parser_cannot_analyse_is_a_failure(
        self, declaration: str, offender: str
    ) -> None:
        """Default-deny, not a silent pass (ADR-0039/R2), and the failure names
        the line. Three shapes, because each reaches the deny by a different
        route: the label, the technology argument, and a module the dict would
        otherwise overwrite without a word.
        """
        _, unanalysable = _c4_components(declaration)

        assert unanalysable == [offender]
        assert _id_defects({"cli"}, {}, set(), [], unanalysable)[
            "a Component declaration the parser cannot analyse"
        ] == [offender]

    def test_the_three_modules_with_no_component_id_are_named_not_skipped(self) -> None:
        """The ADR-0039/R3 exemption, asserted rather than assumed. ``errors``,
        ``limits`` and ``analysis`` carry a row and no COMP id because the C4
        diagram pairs them with none. All four facts are checked here, so the
        exemption cannot quietly stop being true: the set is the three names,
        each is really in the package, the diagram really pairs none of them,
        and the map really labels none of them.
        """
        authority, _ = _c4_components(_PUML.read_text(encoding="utf-8"))
        components = _component_modules(_MODULES)
        rows = _map_row_ids(nonogram.__doc__ or "")

        assert _WITHOUT_A_COMPONENT_ID == {"analysis", "errors", "limits"}
        assert _WITHOUT_A_COMPONENT_ID <= components, sorted(
            _WITHOUT_A_COMPONENT_ID - components
        )
        assert not _WITHOUT_A_COMPONENT_ID & set(authority), (
            "a module exempted from the id column is now paired by the C4 "
            f"diagram: {sorted(_WITHOUT_A_COMPONENT_ID & set(authority))}"
        )
        assert not [
            name
            for name, component, _ in rows
            if name in _WITHOUT_A_COMPONENT_ID and component is not None
        ]

    def test_an_exempt_module_the_diagram_starts_pairing_reds(self) -> None:
        """One direction of the exemption's own control: the diagram gains an
        entry for ``errors`` and the map still shows no id for it.
        """
        defects = _id_defects(
            {"errors"}, {"errors": ("COMP-011", None)}, set(), [("errors", None, None)]
        )

        assert defects == {
            "a COMP id the diagram enumerates and no row carries": ["COMP-011"],
            "a row whose ids are not the diagram's": [
                "errors: the map says -/-, the diagram says COMP-011/-"
            ],
            "exempted from a COMP id, but the diagram now pairs it": ["errors"],
        }

    def test_an_exempt_module_the_map_starts_labelling_reds(self) -> None:
        """The other direction: the map gains an id for ``errors`` that no
        authority backs.
        """
        defects = _id_defects(
            {"errors"}, {}, set(), [("errors", "COMP-011", None)]
        )

        assert defects == {
            "a COMP id the component diagram does not enumerate": ["COMP-011"],
            "exempted from a COMP id, but the map now carries one": ["errors"],
        }

    def test_a_component_with_neither_a_diagram_entry_nor_an_exemption_reds(
        self,
    ) -> None:
        """The default-deny for a component the package gains. Its row keeps
        :func:`_map_defects` green, so without this arm a new directory could
        join the package with no id and no decision recorded either way.
        """
        defects = _id_defects({"planted"}, {}, set(), [("planted", None, None)])

        assert defects == {
            "in the package, neither exempt nor paired by the diagram": ["planted"]
        }

    def test_a_module_the_diagram_pairs_and_the_package_lacks_reds(self) -> None:
        defects = _id_defects(
            {"cli"}, {"retired": ("COMP-099", None)}, set(), [("cli", None, None)]
        )

        assert defects["paired by the diagram, absent from the package"] == ["retired"]

    def test_the_two_row_readers_accept_exactly_the_same_lines(self) -> None:
        """:func:`_map_row_ids` skips a line it cannot read instead of denying
        it, which is only safe while :func:`_canonical_map` denies that same
        line. This is what makes the skip a hand-off rather than a hole.
        """
        doc = nonogram.__doc__ or ""
        rows, unanalysable = _canonical_map(doc)

        assert not unanalysable
        assert len(rows) >= 10, rows
        assert [name for name, _, _ in _map_row_ids(doc)] == rows

    def test_the_capability_pairing_reads_only_a_leading_cap_id(self) -> None:
        """The declared narrowness of the CAP column, measured at one.

        :func:`_c4_components` pairs a capability with a component only where
        the description *leads* with it. ``admin/`` names CAP-006 mid-sentence,
        so it is read as carrying none -- and the canonical map's ``admin/``
        row carries none either, so the two agree. That hole is one component
        wide today, and this pins it there: a second component picking up the
        looser habit reds, rather than dropping silently out of the column.
        """
        loose: list[str] = []
        for line in _PUML.read_text(encoding="utf-8").splitlines():
            declaration = _COMPONENT_DECL.match(line)
            if declaration is None:
                continue
            module = _PUML_MODULE.match(declaration.group(2))
            if module is None:
                continue
            description = declaration.group(3)
            if _PUML_CAPABILITY.match(description) is None and _CAP_ID.search(
                description
            ):
                loose.append(module.group(1))

        assert sorted(loose) == ["admin"], (
            "the C4 diagram names a capability mid-description for a component "
            "this parser therefore reads as carrying none; widen "
            f"_PUML_CAPABILITY or shape the description: {sorted(loose)}"
        )

    def test_the_capability_registry_pairs_no_module(self) -> None:
        """Why the pairing authority is the C4 diagram and not this file.

        ``capabilities.yml`` keys each CAP id to events, commands, aggregates,
        stories and requirements -- never to a component or a module. Asserted,
        not assumed, because if it ever did pair them there would be two
        authorities for one fact and the next reader would have to guess which
        this control followed.
        """
        text = _CAPABILITIES.read_text(encoding="utf-8")
        data = [
            line for line in text.splitlines() if not line.lstrip().startswith("#")
        ]

        assert _capability_ids(text) == {f"CAP-00{n}" for n in range(1, 8)}
        assert not [line for line in data if _COMPONENT_ID.search(line)], (
            "capabilities.yml now names a component id outside a comment -- it "
            "may have become a second authority for the CAP-to-module pairing"
        )
        assert not [
            line
            for line in data
            if re.match(r"^\s+(components?|modules?):", line)
        ]

    def test_a_wrong_description_is_the_one_hole_that_stays_open(self) -> None:
        """AC-5's bound, now that the id columns are held: what is left is the
        English. The row below is the literal defect this card was raised for
        -- ``difficulty.py`` described as unbuilt -- and both controls pass on
        it. Asserting the hole is what makes it a measured exemption
        (ADR-0039/R3) rather than a sentence in a docstring; a later card that
        closes it will red here and remove this test deliberately.
        """
        lie = (
            "Map::\n"
            "\n"
            "    difficulty.py    COMP-006  CAP-004  not yet built (later card)\n"
        )
        rows, unanalysable = _canonical_map(lie)

        assert not _map_defects({"difficulty"}, rows, unanalysable)
        assert not _id_defects(
            {"difficulty"},
            {"difficulty": ("COMP-006", "CAP-004")},
            {"CAP-004"},
            _map_row_ids(lie),
        )


class TestComponentMap_WhatTheClaudeMdReaderAbsorbs:
    """F-101. The extent of :func:`_claude_md_rows`' reach, measured.

    AC-3's class above declares a bound in prose -- "a component map restated
    as running prose with no ids would evade it" -- and ADR-0039/R3 says an
    exemption is a claim that carries a control for what it must **not**
    absorb. Cycle 1 took that docstring at its word, appended a prose
    restatement of the map to CLAUDE.md carrying four of the exact falsehoods
    this card was raised for, and watched the whole file stay green. The hole
    was real; what was missing was a way to know its edges without running
    that experiment.

    So every shape this reader must catch and every shape it is known to miss
    is a committed case below, and the edge between them is asserted directly:
    prose evades only while it carries no component id. The extent cannot now
    change in either direction -- a narrowing that lets a tabular row through,
    or a widening that starts catching ordinary sentences -- without a red.
    """

    # (expected to be flagged, the line fed to the reader). Two of the False
    # cases are deliberately FALSE statements about this package rather than
    # true ones: they are the drift this card was raised for, kept here as
    # counterexamples, not as a copy of the map (G-2).
    CASES = (
        (True, "cli.py           COMP-001  inbound adapter (argparse)"),
        (True, "    export/          COMP-007  the renderers"),
        (True, "conftest.py      # shared fixtures"),
        (True, "The solver (COMP-005) is the correctness-critical component."),
        (True, "# COMP-009 runs as its own process"),
        (False, "docs/GENERATION_ALGORITHM.md   the generation pipeline"),
        (False, "tests/README.md    the suite guide"),
        (False, "`cli.py` is the only inbound adapter."),
        (False, "`difficulty.py` is not yet built."),
        (False, "sourcing covers CAP-001 and nothing else."),
    )

    def test_every_case_reads_the_way_this_class_says_it_does(self) -> None:
        """One assertion per case, so a case that flips is named rather than
        hidden behind a count, plus a floor on the corpus so it cannot silently
        shrink to the cases that happen to pass.
        """
        assert len(self.CASES) >= 10, self.CASES

        wrong = [
            line
            for flagged, line in self.CASES
            if bool(_claude_md_rows(line)) is not flagged
        ]

        assert not wrong, (
            "_claude_md_rows' reach has changed; these lines no longer read the "
            f"way TestComponentMap_WhatTheClaudeMdReaderAbsorbs says: {wrong}"
        )

    def test_each_disjunct_carries_a_case_the_other_does_not(self) -> None:
        """The reader is two patterns, and the cycle-1 kill matrix fused them
        into one arm, so whether each carries its own weight was unestablished.
        A line only the row pattern catches and a line only the id pattern
        catches settle it.
        """
        row_only = "conftest.py      # shared fixtures"
        id_only = "The solver (COMP-005) is the correctness-critical component."

        assert _CLAUDE_MD_ROW.match(row_only) is not None
        assert _COMPONENT_ID.search(row_only) is None
        assert _CLAUDE_MD_ROW.match(id_only) is None
        assert _COMPONENT_ID.search(id_only) is not None
        assert _claude_md_rows(row_only) and _claude_md_rows(id_only)

    def test_prose_with_no_ids_is_the_declared_hole_and_an_id_closes_it(self) -> None:
        """The hole, and its edge. The paragraph below is cycle 1's plant: a
        component map as running prose, every clause of it false of this
        package today and true of CLAUDE.md at some point in the past. The
        reader misses it, which is the declared bound. Adding a single
        component id to the same paragraph is caught -- so the hole is exactly
        "prose carrying no id", not "prose".
        """
        prose = (
            "The pipeline runs one way. `cli.py` is the only inbound adapter.\n"
            "Grid sourcing does random mode; library and image are future work.\n"
            "`difficulty.py` is not yet built, and neither is `export/`.\n"
        )

        assert _claude_md_rows(prose) == [], (
            "the declared hole has closed -- _claude_md_rows now catches prose "
            "with no ids, so AC-3's bound and this class must be rewritten: "
            f"{_claude_md_rows(prose)}"
        )
        assert _claude_md_rows(prose.replace("`cli.py` is", "`cli.py` (COMP-001) is"))

    def test_claude_md_states_no_count_of_adapters(self) -> None:
        """F-101(a). A *corrected* count is still a second copy.

        The retired block's worst error was "the only inbound adapter", and
        cycle 1 kept the correction inline as "there are three inbound
        adapters". Nothing could red on it: it is prose with no ids, which is
        the hole the test above measures. A count in this file is therefore the
        one shape of the hole that must not be allowed to sit in it -- so this
        denies the shape instead of relying on the reader.
        """
        counts = _adapter_counts(_CLAUDE_MD.read_text(encoding="utf-8"))

        assert not counts, (
            "CLAUDE.md states a count of adapters again. A corrected count is "
            "still an uncontrolled copy of the canonical map's adapter rows "
            "(F-101): point at src/nonogram/__init__.py and at "
            f"tests/test_cli.py's _ADAPTERS instead. {counts}"
        )

    def test_the_reader_finds_a_count_when_there_is_one(self) -> None:
        """The plant for the direction above, in both spellings the file uses
        -- markdown emphasis around the number, and a bare digit -- so the
        green above is not a reader that matches nothing.
        """
        assert _adapter_counts("there are **three** inbound adapters, not one") == [
            "1: there are three inbound adapters, not one"
        ]
        assert _adapter_counts("ADR-0019 closes the set at 2 adapters") == [
            "1: ADR-0019 closes the set at 2 adapters"
        ]
        assert _adapter_counts("which modules are adapters is the map's business") == []

    def test_claude_md_points_at_the_adapter_allowlist(self) -> None:
        """Dropping the count is half of F-101(a): a reader who came to
        CLAUDE.md for the adapter set has to be sent somewhere that reds when
        it changes, which is the canonical map and ``_ADAPTERS``.
        """
        text = _CLAUDE_MD.read_text(encoding="utf-8")

        assert "src/nonogram/__init__.py" in text
        assert "_ADAPTERS" in text


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
