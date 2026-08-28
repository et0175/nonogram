"""Test-tree configuration: collect ``bench_generate.py`` alongside the tests.

pytest's default ``python_files`` is ``test_*.py`` / ``*_test.py``, so a file
named ``bench_generate.py`` is invisible to collection. AC-037's gate has to
actually run in ``pytest -q`` — a benchmark nobody runs is not a gate — and the
file's name is fixed by CARD-006's predicted **Touches**, so the choice is
between widening ``python_files`` in ``pyproject.toml`` and naming the one file
here.

Naming the file wins twice. ``pyproject.toml`` is outside this card's footprint
(guardrail G-5), and widening the glob project-wide would quietly enrol every
future ``bench_*.py`` and helper module in collection, which is a decision
about the whole test tree rather than about this benchmark. The hook below adds
exactly one file and nothing else.

Naming *inside* that module still follows pytest's defaults (``test_*``
functions, ``Test*`` classes), same as every other module here — this changes
which files are collected, not how their contents are read.
"""

from __future__ import annotations

from pathlib import Path

import pytest

#: Files that are part of the suite despite not matching ``python_files``.
_EXTRA_TEST_FILES = frozenset({"bench_generate.py"})


def pytest_collect_file(file_path: Path, parent: pytest.Collector) -> pytest.Module | None:
    """Collect :data:`_EXTRA_TEST_FILES` as ordinary test modules.

    ``isinitpath`` is the "somebody named this file on the command line" case:
    pytest collects an explicitly given ``.py`` file itself, whatever
    ``python_files`` says, so adding a second module for it there would run the
    benchmark twice under ``pytest tests/bench_generate.py`` while the plain
    ``pytest`` run stayed correct — the kind of discrepancy that makes a
    failing gate look like two failures.
    """
    if (
        file_path.name in _EXTRA_TEST_FILES
        and file_path.parent == Path(__file__).parent
        and not parent.session.isinitpath(file_path)
    ):
        return pytest.Module.from_parent(parent, path=file_path)
    return None
