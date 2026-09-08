"""COMP-001 tests: FR-014's nudge-count line at export time.

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-040  TestExport_ReportsNudgeCount        -> test_export_reports_nudge_count*
    AC-041  TestExport_OmitsNudgeCountWhenZero   -> test_export_omits_nudge_count_when_zero*

This is CARD-017: the count already exists on the ``Puzzle`` aggregate
(``puzzle.nudge.attempts``, carried by CARD-016's recovery loop) and this card
only prints it, at export time, in ``cli._run_generate``. All tests drive the
real CLI entry point end to end (``cli.main``) rather than calling
``orchestrator.generate``/``export_puzzle`` directly, because the criterion is
about what the *CLI* prints.

``bands.png`` at 10x10, seed 1 is the pinned two-nudge conversion
``tests/test_nudge.py::test_nudge_attempts_bounded_recovery_on_a_real_image``
already relies on (``puzzle.nudge.attempts == 2``); AC-040 reuses it rather
than re-deriving a fixture that happens to need nudging. AC-041 uses
``landscape.png`` at 20x20, seed 1 — the pinned zero-nudge conversion
``tests/test_nudge.py::test_a_unique_conversion_is_never_nudged`` already
relies on (``puzzle.nudge.attempts == 0``, ``ready_for_export is True``),
whose own docstring says it exists so "CARD-017 can report '0 nudges' as a
fact rather than as a default" — this is AC-041's actual given (an exported
puzzle whose *image conversion* reached uniqueness with zero nudges), which a
``--mode random`` run cannot reach at all (``orchestrator.generate`` gates the
nudge loop on ``request.mode == sourcing.IMAGE``).

The boundary test reuses ``tests/test_nudge.py``'s ``_ONE_SWITCH`` scripted
source and ``_install_source`` helper — the pinned single-nudge scenario
``test_nudge_attempts_bounded_recovery_repairs_an_ambiguous_conversion``
already relies on (``puzzle.nudge.attempts == 1``) — rather than hunting for a
new one-nudge image fixture; only the CLI-driving wrapper is new.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nonogram import cli

from tests.test_nudge import _ONE_SWITCH, _CountingSource, _install_source

FIXTURES = Path(__file__).parent / "fixtures"
BANDS = FIXTURES / "bands.png"
#: Re-pinned from ``wide.png`` by CARD-026 — see the note beside
#: ``tests/test_nudge.py``'s own ``LANDSCAPE``: a 3:1 source into a square grid
#: is now an FR-021 refusal, so the zero-nudge pin moved to a 3:2 one.
LANDSCAPE = FIXTURES / "landscape.png"


def test_export_reports_nudge_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-040: 2 pixel nudges -> a line stating 2 cells were nudged."""
    exit_code = cli.main(
        [
            "generate",
            "--mode",
            "image",
            "--image",
            str(BANDS),
            "--size",
            "10",
            "--seed",
            "1",
            "--export",
            "json",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.OK
    out = capsys.readouterr().out
    assert "2 cells were nudged" in out


def test_export_omits_nudge_count_when_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-041: an image conversion that reaches uniqueness with zero nudges ->
    no nudge-count line at all, not "0 cells nudged".

    Drives ``--mode image`` (not ``random``, which cannot reach the nudge
    branch at all) against the pinned zero-nudge conversion ``landscape.png``
    at size 20, seed 1 — see module docstring for the pin this reuses.
    """
    exit_code = cli.main(
        [
            "generate",
            "--mode",
            "image",
            "--image",
            str(LANDSCAPE),
            "--size",
            "20",
            "--seed",
            "1",
            "--export",
            "json",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.OK
    out = capsys.readouterr().out
    assert "nudged" not in out


def test_export_reports_singular_nudge_count(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-040 boundary: exactly 1 nudge -> the singular line, not the plural one.

    ``cli.py``'s singular/plural branch (``"cell"``/``"cells"``,
    ``"was"``/``"were"``) only fires when ``nudged == 1``; this is the only
    test in the repository that drives ``cli.main`` on such a run. Reuses
    ``tests/test_nudge.py``'s ``_ONE_SWITCH`` scripted source via
    ``_install_source`` (see module docstring) rather than inventing a new
    one-nudge image fixture.
    """
    source = _CountingSource(_ONE_SWITCH)
    _install_source(monkeypatch, source)

    exit_code = cli.main(
        [
            "generate",
            "--mode",
            "image",
            "--image",
            str(BANDS),
            "--size",
            "10",
            "--seed",
            "1",
            "--export",
            "json",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.OK
    out = capsys.readouterr().out
    assert "1 cell was nudged to reach a unique solution" in out
