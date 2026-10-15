"""CARD-235 — the browser family's per-test teardown, and the isolation it keeps.

What this card changed, and why it is not what the card predicted
----------------------------------------------------------------
CARD-217 measured the twelve ``tests/test_puzzle_solver_*.py`` files at
366.19 s, 39.78 % of a 930.81 s suite, and found that 137.97 s — 96 % of the
whole suite's teardown — was theirs, at ~0.33 s per test with no single test
above 0.52 s. It attributed that to Chromium's per-test page lifecycle, and
CARD-235 was cut to collapse it by widening the ``browser_page`` fixture's
scope.

Measurement says the page lifecycle is not the cost:

* one ``new_context`` + ``new_page`` + close costs **57 ms** on this host
  (20 iterations against a launched Chromium), so collapsing it for all 422
  tests is worth ~24 s — 2.6 % of the suite;
* the 0.33 s was ``socketserver.serve_forever``'s **0.5 s stdlib poll
  interval**: the ``live`` fixture's ``shutdown()`` cannot return until the
  serve loop next wakes, so every test paid a uniform 0–0.5 s wait. Dropping
  the interval to 0.05 s (``test_puzzle_solver_page._SERVE_POLL_INTERVAL_S``)
  takes the family's teardown from 137.97 s to ~12 s. 0.05 s and not the
  0.01 s its neighbour ``test_web_server._POLL_INTERVAL_S`` uses: a measured
  A/B over all twelve files says 0.01 s buys 8 s more teardown and costs 93 s
  of *call*, because a thread waking 100 times a second takes the GIL from a
  main thread driving Chromium through synchronous RPC. See
  ``meta/profiling/card-235-poll-interval-ab.txt``.

The profile's own evidence says so in hindsight: its teardown histogram was
bimodal with the mass at 0.3–0.5 s and "no tail at all, stopping dead at
0.520 s", which is the signature of a bounded poll wait rather than of a
browser teardown; the near-zero cluster is the family's non-browser tests,
which never ask for ``live``.

So **no file's page scope changed** — the whole saving is in a teardown that
no test can observe, and sharing a page would have bought a sixth of it for
the whole of the order-dependence risk. The guards below nonetheless prove the
family is order-independent, passes alone and does not cascade, because that is
what the card's acceptance criteria are for and because a faster teardown
changes the timing every one of those 422 tests runs under.

Why this file is not named ``test_puzzle_solver_*.py``
-----------------------------------------------------
``rank_durations.BROWSER_FAMILY_PREFIX`` is ``tests/test_puzzle_solver``, so a
thirteenth file under that name would join the family being measured and
inflate the very number AC-1 is about.

Cost discipline
---------------
Four of these tests spawn a child pytest, because "in reverse order", "alone"
and "after a deliberate failure" are claims about a *run*, not about a value,
and cannot be made in-process. They cost ~35 s between them against the
~126 s this card returns. The exhaustive sweeps they sample — every test of
the changed file run alone, and the whole family run in reverse and in a
shuffled order — were run out of band and are committed under
``meta/profiling/``; the tests below check those records are complete rather
than re-running them.
"""

from __future__ import annotations

import hashlib
import importlib.util
import random
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tests.test_puzzle_solver_page import (
    PAGE_ISOLATION,
    PAGE_ISOLATION_CATEGORIES,
    _SERVE_POLL_INTERVAL_S,
    browser_page as _browser_page_fixture,
    live as _live_fixture,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILING_DIR = REPO_ROOT / "meta" / "profiling"
RANKER_PATH = PROFILING_DIR / "rank_durations.py"

#: CARD-217's profile — the "before" of AC-1, and the independent record of
#: which tests the family held before this card touched it (AC-2).
BEFORE_ARTEFACT = PROFILING_DIR / "suite-durations-20261015.txt"
#: This card's own ``--durations`` run. Deliberately *not* named
#: ``suite-durations-<date>.txt``: that name is CARD-217's, one profile per
#: date, and ``tests/test_suite_profile.py`` holds the whole naming and
#: pairing contract around it. A second profile on the same date is this
#: card's artefact, not a second CARD-217 profile.
AFTER_ARTEFACT = PROFILING_DIR / "card-235-durations-after.txt"
#: Where the before and the after are written up together (AC-1).
AFTER_DOCUMENT = PROFILING_DIR / "card-235-browser-teardown.md"
#: Every test of the changed file, each run alone (AC-5).
ALONE_RECORD = PROFILING_DIR / "card-235-tests-alone.txt"
#: The whole family run in reverse and in a shuffled order (AC-3).
ORDER_RECORD = PROFILING_DIR / "card-235-order-independence.txt"

FAMILY_PREFIX = "tests/test_puzzle_solver"
#: The one file this card edits, and so the one AC-5 sweeps exhaustively.
CHANGED_FILE = "tests/test_puzzle_solver_page.py"

#: The family's share of attributed time as CARD-217 measured it. Restated
#: here as a literal so that a drifting artefact is a failure rather than a
#: silently moving baseline.
BEFORE_SHARE_PCT = 39.78
BEFORE_SECONDS = 366.19

#: How much of the family AC-1 requires back. The saving predicted from the
#: poll interval alone is ~134 s and ~10 points of share; these bars are set
#: well inside that, but far outside CARD-217's "treat any single-run
#: difference under ~20 % as noise" band for the absolute seconds.
MIN_SECONDS_SAVED = 100.0
MIN_SHARE_POINTS_SAVED = 5.0

#: AC-3's recorded shuffle seed. Recorded, not drawn fresh, so that a failure
#: is reproducible — the point of a shuffled order is to find an ordering that
#: breaks, and an ordering nobody can replay is not evidence.
SHUFFLE_SEED = 20261015

#: AC-3 runs the real thing on the family's smallest file. The exhaustive
#: whole-family reverse and shuffled runs are in :data:`ORDER_RECORD`.
ORDER_PROBE_FILE = "tests/test_puzzle_solver_mirror.py"

#: AC-5's in-suite sample: one test per kind of page state the declaration
#: names as un-resettable — a localStorage save restored across a reload, a
#: viewport the assertions are computed from, and a ``page.route`` interceptor.
ALONE_PROBES = (
    "tests/test_puzzle_solver_resume.py::"
    "TestSolverResume_ReloadRestoresBoardCountsAndHistory::test_reload_restores",
    "tests/test_puzzle_solver_phone.py::"
    "TestSolverPhone_FitAppliesOnlyAtOrBelowTheShellBreakpoint::"
    "test_820_fits_and_821_keeps_the_desktop_floor",
    "tests/test_puzzle_solver_marking.py::"
    "TestSolverMarking_ControlsStayHiddenWithoutABoard::"
    "test_a_refused_payload_shows_no_controls",
)

_RUN_TIMEOUT_S = 600


def _load_ranker() -> ModuleType:
    """The committed ranking tool, loaded by path (``meta/`` is not a package).

    CARD-235 derives every figure it states from this one script, exactly as
    CARD-217's hotspots document does, so that there is one implementation of
    "what the browser family costs" and not two (G-3).
    """
    name = "card235_rank_durations"
    spec = importlib.util.spec_from_file_location(name, RANKER_PATH)
    assert spec is not None and spec.loader is not None, RANKER_PATH
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ranker = _load_ranker()


def _profile(artefact: Path):
    return ranker.parse_artefact(artefact.read_text(encoding="utf-8"))


def _family(artefact: Path) -> tuple[float, float, int]:
    """``(seconds, share of attributed time as a percentage, tests)``.

    Read out of ``rank_durations.group_totals`` by the row's own name rather
    than re-summing the per-test records here, so the figure is the script's
    and cannot drift from the one its report prints.
    """
    profile = _profile(artefact)
    for name, seconds, count in ranker.group_totals(profile):
        if name.startswith("browser family"):
            return seconds, 100.0 * seconds / profile.attributed, count
    raise AssertionError("rank_durations no longer reports a browser-family row")


def _family_node_ids(artefact: Path) -> set[str]:
    return {
        record.nodeid
        for record in _profile(artefact).tests.values()
        if record.file.startswith(FAMILY_PREFIX)
    }


def _family_files() -> list[str]:
    return sorted(
        f"tests/{path.name}"
        for path in (REPO_ROOT / "tests").glob("test_puzzle_solver_*.py")
    )


def _fixture_scope(fixture: object) -> str:
    """The declared scope of a ``@pytest.fixture``-decorated object.

    pytest 9 hands back a ``FixtureFunctionDefinition`` carrying
    ``_fixture_function_marker``; earlier versions set
    ``_pytestfixturefunction`` on the function itself. Both are read so this
    guard keeps working rather than quietly finding no marker and passing.
    """
    for attribute in ("_fixture_function_marker", "_pytestfixturefunction"):
        marker = getattr(fixture, attribute, None)
        if marker is not None:
            return marker.scope
    raise AssertionError(f"{fixture!r} is not a pytest fixture")


def _pytest(*args: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Run a child pytest from the repo root and hand back the result."""
    import os

    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=_RUN_TIMEOUT_S,
        env=env,
    )


# A `-vv` progress line. The id has no file part when the module is outside
# rootdir (AC-6 runs a generated module from a tmp directory), hence `\S*`.
_VERBOSE_LINE = re.compile(r"^(?P<nodeid>\S*::\S+) (?P<verdict>PASSED|FAILED|ERROR|SKIPPED)")


def _run_order(stdout: str) -> list[tuple[str, str]]:
    """``(node id, verdict)`` in the order a ``-vv`` run reported them."""
    found = []
    for line in stdout.splitlines():
        match = _VERBOSE_LINE.match(line.strip())
        if match is not None:
            found.append((match["nodeid"], match["verdict"]))
    return found


# ==========================================================================
# AC-1 — the saving, measured by the committed script on solo runs
# ==========================================================================


class TestBrowserFixtures_FamilyShareIsRecorded:
    """AC-1: the family's share is materially below 39.78 %, and both are written down."""

    def test_both_profiles_are_solo_runs(self) -> None:
        """G-3: by CARD-217's method, which admits no contended artefact.

        ``is_admissible_profile`` is the script's own gate — a run that
        overlapped another suite is recorded as ``solo run: no`` and is not
        allowed to be the profile. Asserted on both halves of the comparison,
        because a contaminated "after" is exactly how a saving gets claimed.
        """
        for artefact in (BEFORE_ARTEFACT, AFTER_ARTEFACT):
            text = artefact.read_text(encoding="utf-8")
            assert ranker.missing_header_fields(text) == [], artefact.name
            assert ranker.is_admissible_profile(text), (
                f"{artefact.name} does not declare itself a solo run, so it "
                f"cannot be half of this card's measurement (G-3)"
            )

    def test_the_before_is_the_number_the_card_was_cut_on(self) -> None:
        seconds, share, tests = _family(BEFORE_ARTEFACT)

        assert tests == 422
        assert round(seconds, 2) == BEFORE_SECONDS
        assert round(share, 2) == BEFORE_SHARE_PCT

    def test_the_family_costs_materially_less_than_it_did(self) -> None:
        before_seconds, before_share, before_tests = _family(BEFORE_ARTEFACT)
        after_seconds, after_share, after_tests = _family(AFTER_ARTEFACT)

        # Seconds first: the share has the suite's own growth in its
        # denominator, so a share that fell is not on its own proof that the
        # family got cheaper. The seconds are.
        assert before_seconds - after_seconds >= MIN_SECONDS_SAVED, (
            f"the family went {before_seconds:.2f}s -> {after_seconds:.2f}s, "
            f"which is less than the {MIN_SECONDS_SAVED:.0f}s this card claims"
        )
        assert before_share - after_share >= MIN_SHARE_POINTS_SAVED, (
            f"the family's share went {before_share:.2f}% -> {after_share:.2f}%"
        )
        # The saving must be per-test, not a test that stopped running.
        assert after_tests == before_tests

    def test_the_saving_is_the_teardown_it_was_diagnosed_as(self) -> None:
        """The mechanism, not just the total: teardown is what collapsed.

        A saving of the right size in the wrong phase would mean the diagnosis
        is wrong and something else changed — a test body that got shorter, or
        a page that stopped loading.
        """
        def teardown(artefact: Path) -> float:
            return sum(
                record.phase("teardown")
                for record in _profile(artefact).tests.values()
                if record.file.startswith(FAMILY_PREFIX)
            )

        before, after = teardown(BEFORE_ARTEFACT), teardown(AFTER_ARTEFACT)

        assert before - after >= MIN_SECONDS_SAVED, (
            f"family teardown went {before:.2f}s -> {after:.2f}s; the saving "
            f"this card claims is a teardown saving"
        )
        # And it is bounded by the poll interval it now waits on, with room
        # for the page close that was always there. A regression that put the
        # stdlib 0.5s back would land at ~0.33s per test and fail here.
        assert after / 422 < _SERVE_POLL_INTERVAL_S + 0.02

    def test_the_document_records_the_before_and_the_after(self) -> None:
        document = AFTER_DOCUMENT.read_text(encoding="utf-8")
        before_seconds, before_share, _ = _family(BEFORE_ARTEFACT)
        after_seconds, after_share, _ = _family(AFTER_ARTEFACT)

        missing = [
            figure
            for figure in (
                f"{before_seconds:.2f} s",
                f"{before_share:.2f} %",
                f"{after_seconds:.2f} s",
                f"{after_share:.2f} %",
            )
            if figure not in document
        ]
        assert missing == [], (
            f"{AFTER_DOCUMENT.name} does not state {missing}; AC-1 is that the "
            f"before and the after are both recorded"
        )
        assert str(SHUFFLE_SEED) in document, "the shuffle seed is not recorded"

    def test_the_document_cites_and_quotes_its_own_artefact(self) -> None:
        """Pin the document to the run it describes, the way CARD-217's is.

        The sha256 says *which* artefact; the quoted deciding table says what
        the script actually printed about it. Both come from
        ``rank_durations`` itself, so this is a citation check and not a second
        implementation of the ranking.
        """
        document = AFTER_DOCUMENT.read_text(encoding="utf-8")
        digest = hashlib.sha256(AFTER_ARTEFACT.read_bytes()).hexdigest()
        assert digest in document, (
            f"{AFTER_DOCUMENT.name} does not cite the sha256 of "
            f"{AFTER_ARTEFACT.name}, so nothing pins it to that run"
        )

        report = ranker.report(_profile(AFTER_ARTEFACT), AFTER_ARTEFACT, digest)
        block = report.partition("## Cost families")[2].partition("\n## ")[0]
        assert block.strip(), "the report no longer has a cost-families block"
        assert block.strip() in document


# ==========================================================================
# AC-2 — no test added or removed
# ==========================================================================


class TestBrowserFixtures_NoTestAddedOrRemoved:
    """AC-2: every node id, not just the count. This card changes fixtures."""

    def test_the_family_collects_exactly_what_card_217_measured(self) -> None:
        """Compared against an independent record, not against a snapshot.

        The "before" set is read out of CARD-217's committed ``--durations``
        artefact — every test that ran, by node id, recorded before this card
        existed and by somebody else. A snapshot regenerated from today's tree
        could only ever agree with today's tree.
        """
        collected = _pytest(*_family_files(), "--collect-only")
        assert collected.returncode == 0, collected.stdout[-4000:]
        ids = {
            line.strip()
            for line in collected.stdout.splitlines()
            if line.startswith("tests/") and "::" in line
        }

        before = _family_node_ids(BEFORE_ARTEFACT)
        assert len(ids) == 422
        assert sorted(ids - before) == [], "tests added"
        assert sorted(before - ids) == [], "tests removed"

    def test_the_twelve_files_are_still_twelve(self) -> None:
        files = _family_files()
        assert len(files) == 12, files
        assert {path.split("/")[-1] for path in files} == set(PAGE_ISOLATION)


# ==========================================================================
# AC-3 — no order-dependence
# ==========================================================================


class TestBrowserFixtures_OrderIndependent:
    """AC-3: reverse order and a shuffled order with a recorded seed."""

    @staticmethod
    def _probe_ids() -> list[str]:
        """The probe file's tests, in collection order, from the artefact.

        Taken from CARD-217's record rather than by collecting again: AC-2
        already proves the two agree, and a child pytest per ordering is
        enough subprocess for one test.
        """
        ids = sorted(
            node
            for node in _family_node_ids(BEFORE_ARTEFACT)
            if node.startswith(f"{ORDER_PROBE_FILE}::")
        )
        assert len(ids) >= 5, ids
        return ids

    def _run_in(self, order: list[str]) -> None:
        completed = _pytest("-vv", *order)
        reported = _run_order(completed.stdout)

        assert completed.returncode == 0, completed.stdout[-6000:]
        # The ordering has to have actually happened: pytest is free to
        # reorder for higher-scoped parametrised fixtures, and a test that
        # silently ran in collection order would prove nothing.
        assert [node for node, _ in reported] == order
        assert {verdict for _, verdict in reported} == {"PASSED"}

    def test_reverse_order_passes(self) -> None:
        self._run_in(list(reversed(self._probe_ids())))

    def test_shuffled_order_passes(self) -> None:
        order = self._probe_ids()
        random.Random(SHUFFLE_SEED).shuffle(order)
        self._run_in(order)

    def test_the_whole_family_was_run_in_both_orders(self) -> None:
        """The exhaustive version of the two runs above, out of band.

        Reverse and shuffled runs of all twelve files take ~8 minutes, which
        does not belong in the suite; the record does, and it is checked for
        completeness rather than believed.
        """
        record = ORDER_RECORD.read_text(encoding="utf-8")

        assert f"seed: {SHUFFLE_SEED}" in record
        for order in ("reverse", "shuffled"):
            assert re.search(
                rf"^# {order}: 422 selected, 422 passed, 0 failed", record, re.M
            ), f"{ORDER_RECORD.name} does not record a passing {order}-order run"


# ==========================================================================
# AC-4 — isolation where it is needed, declared per file
# ==========================================================================


class TestBrowserFixtures_IsolationIsDeclaredPerFile:
    """AC-4: a test that mutates un-resettable page state keeps its own page."""

    def test_every_family_file_declares_a_category_and_a_reason(self) -> None:
        on_disk = {path.split("/")[-1] for path in _family_files()}

        assert set(PAGE_ISOLATION) == on_disk, (
            "PAGE_ISOLATION and tests/test_puzzle_solver_*.py disagree; a new "
            "file in the family must declare its page isolation"
        )
        wrong = []
        for name, (category, reason) in sorted(PAGE_ISOLATION.items()):
            if category not in PAGE_ISOLATION_CATEGORIES:
                wrong.append(f"{name}: unknown category {category!r}")
            if len(reason.split()) < 8:
                wrong.append(f"{name}: the reason says too little: {reason!r}")
        assert wrong == [], wrong

    def test_an_own_page_file_really_gets_its_own_page(self) -> None:
        """The declaration is checked against the fixtures, not trusted.

        ``own-page`` means two things, and both are read off the fixture
        objects: a page per test, and a server per test — the page would be
        useless on its own, since ``live``'s origin is where the save a test
        writes actually lives.
        """
        assert all(
            category == "own-page" for category, _ in PAGE_ISOLATION.values()
        ), "a file is declared shared-page; this test must then check its reset"

        for fixture in (_browser_page_fixture, _live_fixture):
            assert _fixture_scope(fixture) == "function", fixture

    def test_the_reasons_name_state_the_file_actually_touches(self) -> None:
        """Each reason has to be true of its file, not merely plausible.

        A reason nobody checks is how "we looked at it" becomes "we said we
        looked at it". Each file is grepped for the mechanism its reason
        claims, so a copied-and-pasted reason fails.
        """
        mechanisms = {
            "viewport": r"set_viewport_size",
            "localStorage": r"localStorage",
            "page.route": r"\.route\(",
            "listener": r"\.on\(",
            "reload": r"\.reload\(",
        }
        wrong = []
        for name, (_category, reason) in sorted(PAGE_ISOLATION.items()):
            source = (REPO_ROOT / "tests" / name).read_text(encoding="utf-8")
            claimed = [
                pattern
                for word, pattern in mechanisms.items()
                if word.lower() in reason.lower()
            ]
            if not claimed:
                wrong.append(f"{name}: the reason names no mechanism to check")
            for pattern in claimed:
                if not re.search(pattern, source):
                    wrong.append(f"{name}: reason claims {pattern}, file has none")
        assert wrong == [], wrong


# ==========================================================================
# AC-5 — each test alone
# ==========================================================================


class TestBrowserFixtures_EveryTestPassesAlone:
    """AC-5: the failure mode where a test depends on a predecessor's navigation."""

    @pytest.mark.browser
    @pytest.mark.parametrize("node_id", ALONE_PROBES, ids=lambda n: n.split("::")[0][6:-3])
    def test_the_riskiest_tests_pass_alone(self, node_id: str) -> None:
        completed = _pytest("-vv", node_id)

        assert completed.returncode == 0, completed.stdout[-6000:]
        assert _run_order(completed.stdout) == [(node_id, "PASSED")]

    def test_the_record_covers_every_test_of_the_changed_file(self) -> None:
        """The exhaustive version, out of band, checked for completeness.

        ``tests/test_puzzle_solver_page.py`` is the one file whose bytes this
        card changes, so it is the one AC-5 sweeps test by test. The record is
        cross-checked against the node ids CARD-217 measured, so a stale
        record — one taken before a test was renamed — fails here rather than
        being read as coverage.
        """
        record = ALONE_RECORD.read_text(encoding="utf-8")
        verdicts: dict[str, str] = {}
        for line in record.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            verdict, _, node_id = line.partition(" ")
            verdicts[node_id.strip()] = verdict

        wanted = {
            node
            for node in _family_node_ids(BEFORE_ARTEFACT)
            if node.startswith(f"{CHANGED_FILE}::")
        }
        assert len(wanted) == 67, len(wanted)
        assert sorted(wanted - set(verdicts)) == [], "not every test was run alone"
        assert sorted(node for node in wanted if verdicts[node] != "PASSED") == []

    def test_the_record_reaches_every_file_in_the_family(self) -> None:
        """Every one of the twelve is represented, so no file is unsampled."""
        record = ALONE_RECORD.read_text(encoding="utf-8")
        seen = {
            line.partition(" ")[2].strip().split("::")[0]
            for line in record.splitlines()
            if line.startswith("PASSED ")
        }

        assert set(_family_files()) <= seen, sorted(set(_family_files()) - seen)


# ==========================================================================
# AC-6 — a failing test does not poison its neighbours
# ==========================================================================


_CASCADE_MODULE = '''\
"""Generated by CARD-235's AC-6. Not collected by the suite."""

import pytest

from tests.test_puzzle_solver_page import (  # noqa: F401 - fixtures by name
    AC_GRID,
    browser_page,
    browser_type,
    live,
)
from tests.test_puzzle_solver_page import _open


@pytest.mark.browser
def test_before_the_failure(browser_page, live) -> None:
    _open(browser_page, live, live.store(AC_GRID))
    assert browser_page.evaluate("window.puzzlePlayer !== undefined") is True


@pytest.mark.browser
def test_the_deliberate_failure(browser_page, live) -> None:
    _open(browser_page, live, live.store(AC_GRID))
    assert False, "CARD-235 AC-6: deliberate"


@pytest.mark.browser
def test_after_the_failure(browser_page, live) -> None:
    _open(browser_page, live, live.store(AC_GRID))
    assert browser_page.evaluate("window.puzzlePlayer !== undefined") is True
'''


class TestBrowserFixtures_AFailureDoesNotCascade:
    """AC-6: a deliberate failure, and the tests after it in the same module."""

    @pytest.mark.browser
    def test_the_tests_after_a_failure_still_pass(self, tmp_path: Path) -> None:
        """One failure, and exactly one.

        This is the shape of order-dependence that a shared page would make
        possible, and it is also the one a teardown change can cause on its
        own: if stopping the ``live`` server on the failure path left the
        thread running or the port held, the next test would inherit it. The
        module is generated rather than committed because a committed module
        that fails on purpose is a red suite.
        """
        module = tmp_path / "test_card_235_cascade.py"
        module.write_text(_CASCADE_MODULE, encoding="utf-8")

        completed = _pytest(
            "-c",
            str(REPO_ROOT / "pyproject.toml"),
            "-vv",
            str(module),
            env_extra={"PYTHONPATH": str(REPO_ROOT)},
        )
        reported = _run_order(completed.stdout)

        assert completed.returncode == 1, completed.stdout[-6000:]
        names = [node.rpartition("::")[2] for node, _ in reported]
        assert names == [
            "test_before_the_failure",
            "test_the_deliberate_failure",
            "test_after_the_failure",
        ], reported
        assert [verdict for _, verdict in reported] == [
            "PASSED",
            "FAILED",
            "PASSED",
        ], reported
