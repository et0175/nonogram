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
from nonogram import cli, errors, orchestrator

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
    assert args.size == 15
    assert args.density == 45
    assert args.seed == 1234
    assert args.export_formats == ["json"]
    assert args.out == Path("/tmp/puzzles")


def test_generate_defaults_leave_every_optional_unset() -> None:
    args = _parse("generate")
    assert args.mode == "random"
    assert args.size is None
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
        pytest.param(["generate", "--mode", "image"], id="mode-not-in-increment-1"),
        pytest.param(["generate", "--export", "png"], id="format-not-in-increment-1"),
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
# Guardrail G-3: argparse parses, it does not judge
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--size", "0"),
        ("--size", "9"),
        ("--size", "51"),
        ("--size", "-5"),
        ("--density", "-1"),
        ("--density", "0"),
        ("--density", "101"),
        ("--density", "9999"),
    ],
)
def test_out_of_domain_range_values_pass_the_parser_untouched(
    flag: str, value: str
) -> None:
    """Size and density ranges are domain rules (ADR-0010, G-3).

    They must NOT be encoded as argparse ``type=``/``choices=`` checks, so the
    parser is required to accept these values and hand them inward unchanged.
    """
    args = _parse("generate", flag, value)
    assert getattr(args, flag.lstrip("-")) == int(value)


# --------------------------------------------------------------------------
# argv -> GenerationRequest
# --------------------------------------------------------------------------


@pytest.fixture
def captured_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> list[orchestrator.GenerationRequest]:
    """Replace the (unimplemented) pipeline with a recorder."""
    seen: list[orchestrator.GenerationRequest] = []

    def fake_generate(request: orchestrator.GenerationRequest) -> orchestrator.Puzzle:
        seen.append(request)
        return orchestrator.Puzzle()

    monkeypatch.setattr(orchestrator, "generate", fake_generate)
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
            size=20,
            density=50,
            seed=7,
            export_formats=("json",),
            out=None,
        )
    ]


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
    (errors.InvalidPuzzleName, cli.ExitCode.INVALID_INPUT),
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


def test_orchestrator_generate_is_a_signature_only() -> None:
    """Guardrail G-4: the pipeline body belongs to CARD-005."""
    with pytest.raises(NotImplementedError):
        orchestrator.generate(orchestrator.GenerationRequest(mode="random"))


# ADR-0007's layers, innermost last. ``cli`` is the sole inbound adapter,
# ``orchestrator`` the only thing that composes capabilities, and ``errors`` is
# the shared foundation every layer may raise from. Everything *else* under
# ``nonogram/`` is a capability package (``sourcing/``, ``clues.py``,
# ``solver/``, ``difficulty.py``, ``export/``, and whatever a later card adds)
# — which is why the capability set is discovered from disk rather than listed.
_ADAPTER = "cli"
_ORCHESTRATOR = "orchestrator"
_SHARED = frozenset({"errors"})

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
    if component == _ADAPTER:
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


def test_the_import_walk_actually_sees_the_package() -> None:
    """Guard the guard: an empty or misrooted walk must not pass silently."""
    assert {"nonogram", "nonogram.cli", "nonogram.orchestrator", "nonogram.errors"} <= set(
        _MODULES
    )


def test_nothing_inward_of_the_adapter_imports_the_adapter() -> None:
    """ADR-0007, first half: dependencies point inward only.

    Only ``cli.py`` may know about ``cli.py``; every module the walk finds at a
    deeper rank is checked, including ones no later card has written yet.
    """
    offenders = {
        module
        for module, path in _MODULES.items()
        if _rank(_component(module)) != _ADAPTER_RANK
        and _ADAPTER in _imported_components(module, path)
    }
    assert not offenders, f"modules importing nonogram.cli: {sorted(offenders)}"


def test_capability_packages_never_import_each_other_laterally() -> None:
    """ADR-0007, second half: no lateral imports between capability modules.

    A capability's only outward-facing contact is the orchestrator that
    composes it into a run, so e.g. ``solver/`` importing ``export/`` is a
    violation even though both sit at the same rank.
    """
    lateral = {
        module: sorted(
            other
            for other in _imported_components(module, path)
            if other != _component(module) and _rank(other) == _CAPABILITY_RANK
        )
        for module, path in _MODULES.items()
        if _rank(_component(module)) == _CAPABILITY_RANK
    }
    offenders = {module: others for module, others in lateral.items() if others}
    assert not offenders, f"lateral capability imports: {offenders}"


def test_the_shared_error_hierarchy_reaches_into_nothing() -> None:
    """``errors.py`` is the innermost layer, so it closes the lateral loophole.

    Capability modules may all import it; if it could import them back, two
    capabilities could couple through it without a direct lateral import.
    """
    offenders = {
        module: sorted(_imported_components(module, path))
        for module, path in _MODULES.items()
        if _rank(_component(module)) == _SHARED_RANK
        and _imported_components(module, path)
    }
    assert not offenders, f"shared modules importing the package: {offenders}"


def test_the_adapter_does_import_the_orchestrator() -> None:
    """The one dependency arrow this card establishes (COMP-001 -> COMP-002)."""
    assert "nonogram.orchestrator" in _package_imports(
        "nonogram.cli", _MODULES["nonogram.cli"]
    )


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
