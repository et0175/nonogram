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

So **no file's page scope changed** — the whole saving is in a teardown whose
outcome no test of the family can observe (which is why
:class:`TestBrowserFixtures_ThePollIntervalIsStillApplied` below times that
teardown directly: a saving nothing observes is a saving nothing defends), and
sharing a page would have bought a sixth of it for the whole of the
order-dependence risk. The guards below nonetheless prove the
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
Several of these tests spawn a child pytest, because "in reverse order",
"alone" and "after a deliberate failure" are claims about a *run*, not about a
value, and cannot be made in-process. They cost ~52 s between them against the
~126 s this card returns, and 41.8 s of that is the two orderings over
:data:`ORDER_PROBE_FILE` (21.51 s and 20.29 s, measured) — which is the
family's cheapest file that actually installs the page state an ordering could
expose, rather than its cheapest file outright. The whole of this file runs in
54.05 s on this host, and each child is capped at :data:`_RUN_TIMEOUT_S`. The
exhaustive sweeps they sample — every test of
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
import threading
import time
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

#: The family's per-test teardown as CARD-217 measured it, used to synthesise
#: the pre-fix behaviour and prove the bars below are not vacuous.
BEFORE_TEARDOWN_PER_TEST = 0.327

#: How much of the family AC-1 requires back.
#:
#: The structural saving is 422 x (0.327 - 0.028) = ~126 s of teardown, and the
#: A/B says the chosen interval adds nothing to ``call``. These are regression
#: tripwires set below that with headroom, not the claim: the claim is the
#: measured pair of figures, which ``test_the_document_records_the_before_and_
#: the_after`` pins to two decimal places. The headroom is there because
#: CARD-217 measured a 19 % run-to-run spread on this host and says to treat a
#: single-run difference under ~20 % as noise — a performance bar tight enough
#: to red the suite on noise is a bar that gets deleted.
#:
#: They are not vacuous: ``test_the_bars_reject_the_pre_fix_teardown`` feeds
#: the same comparison an artefact with the 0.5 s poll's teardown added back
#: and requires it to fail every one of them.
#:
#: What they do **not** cover, and what covers it instead: these bars compare
#: two committed artefacts, so no change to the code can move them. The saving
#: itself — the ``live`` fixture actually asking its serve loop to wake 20
#: times a second, and actually stopping promptly when it does —
#: is guarded behaviourally by
#: :class:`TestBrowserFixtures_ThePollIntervalIsStillApplied`. That class, not
#: these bars, is what fails if the fixture stops passing ``poll_interval``.
MIN_SECONDS_SAVED = 80.0
MIN_SHARE_POINTS_SAVED = 5.0
MIN_TEARDOWN_SECONDS_SAVED = 100.0
#: The family's cost as a multiple of the rest of the suite's. A ratio cancels
#: whatever made the whole host slower or faster between the two runs, which
#: neither of the absolute bars can do.
MAX_FAMILY_TO_REST_RATIO = 0.50

#: AC-3's recorded shuffle seed. Recorded, not drawn fresh, so that a failure
#: is reproducible — the point of a shuffled order is to find an ordering that
#: breaks, and an ordering nobody can replay is not evidence.
SHUFFLE_SEED = 20261015

#: AC-3 runs the real thing on one file of the family. The exhaustive
#: whole-family reverse and shuffled runs are in :data:`ORDER_RECORD`.
#:
#: ``resume.py`` and not the family's cheapest file (``mirror.py``, 5 tests,
#: 3.34 s): the cross-talk :data:`PAGE_ISOLATION` actually names is a
#: ``localStorage`` save surviving a reload, a ``page.route`` interceptor and a
#: context listener outliving the test that installed them — and ``mirror.py``
#: installs none of those, so an ordering over it could not expose any of them.
#: ``resume.py`` writes, corrupts and restores the save and reloads, and
#: installs a context ``request`` listener. It is the cheapest file that does
#: (15 tests, 16.11 s in :data:`AFTER_ARTEFACT`, so ~20 s per ordering against
#: ``marking.py``'s 72 tests and 39.58 s).
#: ``test_the_probe_file_installs_the_state_the_ordering_is_about`` keeps that
#: choice honest rather than leaving it to this comment.
ORDER_PROBE_FILE = "tests/test_puzzle_solver_resume.py"

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

#: Wall clock each child pytest below is allowed. The dearest of them is an
#: ordering over :data:`ORDER_PROBE_FILE`, measured at 21.51 s (it was 8.46 s
#: while the probe was the family's cheapest file); 90 s is ~4x that, which is
#: headroom for a loaded host without letting one hung child hold a gate for
#: ten minutes. There are six of these tests, so the old 600 s bound was up to
#: an hour of gate spent waiting on a child that was never going to finish.
_RUN_TIMEOUT_S = 90

#: ``socketserver.serve_forever``'s stdlib default poll interval — the wait
#: this card removed, quoted here as the thing the guards below must stay well
#: clear of. Not imported from ``socketserver``: the point is the 0.5 s the
#: measurements were taken against, not whatever a future stdlib defaults to.
STDLIB_POLL_INTERVAL_S = 0.5

#: The poll interval every committed artefact in this card was measured under.
#: Used only as a diagnostic: if the constant moves, the artefact comparisons
#: above are comparing runs taken under different intervals, and the failure
#: should say that rather than blaming the bars.
POLL_INTERVAL_AS_MEASURED = 0.05

#: How long the ``live`` fixture's teardown may take, as an absolute bound and
#: deliberately **not** derived from ``_SERVE_POLL_INTERVAL_S``: a bound
#: computed from the constant would move with it and could never fail on a
#: reverted interval. 0.2 s is under half the stdlib 0.5 s wait and 4x the
#: 0.05 s the fixture asks for, so it is clear of both.
MAX_LIVE_TEARDOWN_S = 0.2

#: Slept after the serve thread starts, before timing its stop, so that the
#: loop is measured *inside* a poll wait. Without it the stop can be timed
#: before the loop reaches its first wait, which is fast at any interval.
_SERVE_SETTLE_S = 0.05


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


def _phase_total(profile, phase: str, *, family: bool) -> float:
    return sum(
        record.phase(phase)
        for record in profile.tests.values()
        if record.file.startswith(FAMILY_PREFIX) is family
    )


def _saving(before, after) -> dict[str, float]:
    """Every figure AC-1 turns on, from two parsed profiles.

    One function so that the real comparison and the synthetic pre-fix
    comparison below cannot diverge — if the bars are checked one way for the
    committed artefact and another way for the mutant, the mutant proves
    nothing.
    """
    def family(profile) -> tuple[float, float]:
        for name, seconds, _count in ranker.group_totals(profile):
            if name.startswith("browser family"):
                return seconds, 100.0 * seconds / profile.attributed
        raise AssertionError("rank_durations no longer reports a browser-family row")

    before_seconds, before_share = family(before)
    after_seconds, after_share = family(after)
    rest_before = before.attributed - before_seconds
    rest_after = after.attributed - after_seconds
    return {
        "before_seconds": before_seconds,
        "after_seconds": after_seconds,
        "seconds_saved": before_seconds - after_seconds,
        "before_share": before_share,
        "after_share": after_share,
        "share_points_saved": before_share - after_share,
        "before_teardown": _phase_total(before, "teardown", family=True),
        "after_teardown": _phase_total(after, "teardown", family=True),
        "teardown_saved": (
            _phase_total(before, "teardown", family=True)
            - _phase_total(after, "teardown", family=True)
        ),
        "ratio_before": before_seconds / rest_before,
        "ratio_after": after_seconds / rest_after,
    }


def _failed_bars(saving: dict[str, float], after_tests: int) -> list[str]:
    """Which of AC-1's bars this saving misses. Empty means it clears them all."""
    missed = []
    if saving["seconds_saved"] < MIN_SECONDS_SAVED:
        missed.append(
            f"seconds: {saving['before_seconds']:.2f}s -> "
            f"{saving['after_seconds']:.2f}s is only "
            f"{saving['seconds_saved']:.2f}s, under {MIN_SECONDS_SAVED:.0f}s"
        )
    if saving["share_points_saved"] < MIN_SHARE_POINTS_SAVED:
        missed.append(
            f"share: {saving['before_share']:.2f}% -> {saving['after_share']:.2f}% "
            f"is only {saving['share_points_saved']:.2f} points"
        )
    if saving["teardown_saved"] < MIN_TEARDOWN_SECONDS_SAVED:
        missed.append(
            f"teardown: {saving['before_teardown']:.2f}s -> "
            f"{saving['after_teardown']:.2f}s is only "
            f"{saving['teardown_saved']:.2f}s"
        )
    if saving["ratio_after"] > MAX_FAMILY_TO_REST_RATIO:
        missed.append(
            f"ratio to the rest of the suite: {saving['ratio_before']:.3f} -> "
            f"{saving['ratio_after']:.3f}, over {MAX_FAMILY_TO_REST_RATIO}"
        )
    if saving["after_teardown"] / after_tests >= _SERVE_POLL_INTERVAL_S + 0.02:
        missed.append(
            f"per-test teardown {saving['after_teardown'] / after_tests:.3f}s is "
            f"not bounded by the {_SERVE_POLL_INTERVAL_S}s poll it now waits on"
        )
    return missed


def _with_pre_fix_teardown(text: str, ids: set[str]) -> str:
    """The after artefact as it would read with the 0.5 s poll interval back.

    Only the family's teardown rows are rewritten, to CARD-217's measured
    0.327 s mean. Nothing else is touched, so this is the one-change mutant of
    "somebody reverts the poll interval" and not a differently-shaped run.
    """
    out = []
    for line in text.splitlines():
        match = ranker._DURATION_LINE.match(line)
        if (
            match is not None
            and match["phase"] == "teardown"
            and match["nodeid"] in ids
        ):
            line = f"{BEFORE_TEARDOWN_PER_TEST:.2f}s teardown {match['nodeid']}"
        out.append(line)
    return "\n".join(out) + "\n"


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


def _recorded_poll_interval(call: dict[str, object]):
    """The poll interval a recorded ``threading.Thread(...)`` call hands on.

    ``threading.Thread`` forwards ``args``/``kwargs`` to its target, so the
    interval the serve loop will actually use is inside those, not among the
    ``Thread`` keywords themselves. Both forms are read — ``kwargs={...}`` as
    the ``live`` fixture spells it, and a positional ``args=(interval,)`` —
    so that a rewrite that keeps passing the interval differently still
    passes, and only one that stops passing it fails. ``None`` means the
    target was started with no interval at all.
    """
    target_kwargs = call.get("kwargs") or {}
    if isinstance(target_kwargs, dict) and "poll_interval" in target_kwargs:
        return target_kwargs["poll_interval"]
    target_args = call.get("args") or ()
    if target_args:
        return target_args[0]
    return None


def _fixture_function(fixture: object):
    """The undecorated generator function behind a ``@pytest.fixture``.

    So that the ``live`` fixture's own setup and teardown can be driven by hand
    and timed, which pytest gives no hook for: its teardown runs after the test
    has finished reporting. pytest 9 wraps the function in a
    ``FixtureFunctionDefinition``; older versions decorate the function itself.
    Both are handled, and an unrecognised shape raises rather than silently
    handing back something that is not the fixture.
    """
    getter = getattr(fixture, "_get_wrapped_function", None)
    if getter is not None:
        return getter()
    for attribute in ("_fixture_function", "__wrapped__"):
        function = getattr(fixture, attribute, None)
        if function is not None:
            return function
    if getattr(fixture, "_pytestfixturefunction", None) is not None:
        return fixture
    raise AssertionError(f"cannot unwrap {fixture!r}")


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
        """Four bars, measuring four different ways of being wrong.

        Seconds, because the share has the suite's own growth in its
        denominator and a share that fell is not on its own proof that the
        family got cheaper. Share, because that is what AC-1 is phrased in.
        Teardown, because a saving of the right size in the wrong phase would
        mean the diagnosis is wrong and something else changed. And the ratio
        to the rest of the suite, because that one figure cancels whatever
        made the host slower or faster between the two runs.
        """
        before, after = _profile(BEFORE_ARTEFACT), _profile(AFTER_ARTEFACT)
        saving = _saving(before, after)

        assert _failed_bars(saving, 422) == [], saving
        # The saving has to be per test, not a test that stopped running.
        assert _family_node_ids(AFTER_ARTEFACT) == _family_node_ids(BEFORE_ARTEFACT)

    def test_the_bars_reject_the_pre_fix_teardown(self) -> None:
        """The bars above bite: put the 0.5 s poll back and they all fail.

        Without this, "the family got faster" is a check on one committed
        number against another committed number, and nobody can tell whether
        the thresholds were set where a regression would trip them. The mutant
        is the one change somebody could actually make — restore the stdlib
        poll interval — expressed as CARD-217's own measured 0.327 s of
        teardown per family test, with every other row left alone.
        """
        before = _profile(BEFORE_ARTEFACT)
        reverted = ranker.parse_artefact(
            _with_pre_fix_teardown(
                AFTER_ARTEFACT.read_text(encoding="utf-8"),
                _family_node_ids(AFTER_ARTEFACT),
            )
        )

        missed = _failed_bars(_saving(before, reverted), 422)

        # Said first, and separately, because one of the five bars reads the
        # live constant: if the constant itself has moved, this test fails for
        # that reason and not because a bar went slack, and the message has to
        # say which. (The constant's *application* is guarded behaviourally by
        # TestBrowserFixtures_ThePollIntervalIsStillApplied, not here.)
        assert _SERVE_POLL_INTERVAL_S == POLL_INTERVAL_AS_MEASURED, (
            f"_SERVE_POLL_INTERVAL_S is now {_SERVE_POLL_INTERVAL_S}s, not the "
            f"{POLL_INTERVAL_AS_MEASURED}s both committed artefacts were "
            f"measured under. The bars above compare those two artefacts, so "
            f"they say nothing about the new interval: re-measure the after "
            f"profile at {_SERVE_POLL_INTERVAL_S}s and re-record the A/B, "
            f"rather than moving the constant alone"
        )
        assert len(missed) == 5, (
            f"a reverted poll interval still clears {5 - len(missed)} of AC-1's "
            f"five bars, so those bars have gone slack and would not trip on a "
            f"regression of this size: only {missed} failed"
        )

    def test_the_document_records_the_before_and_the_after(self) -> None:
        document = AFTER_DOCUMENT.read_text(encoding="utf-8")
        saving = _saving(_profile(BEFORE_ARTEFACT), _profile(AFTER_ARTEFACT))

        missing = [
            figure
            for figure in (
                f"{saving['before_seconds']:.2f} s",
                f"{saving['before_share']:.2f} %",
                f"{saving['after_seconds']:.2f} s",
                f"{saving['after_share']:.2f} %",
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
# AC-1 — and the saving itself, measured off the running fixture
# ==========================================================================


class TestBrowserFixtures_ThePollIntervalIsStillApplied:
    """The whole 126 s saving is one kwarg; these two tests are what holds it.

    Everything above compares two committed artefacts, which no edit to the
    code can move, so a fixture that stopped passing ``poll_interval`` — the
    most plausible shape of a future refactor, ``thread =
    threading.Thread(target=server.serve_forever, daemon=True)``, with the
    constant left defined and unused — would take the entire saving back and
    leave this file green. These tests pin the *application* of the constant
    and the *behaviour* that application buys, never its literal value:

    * :meth:`test_the_live_fixture_passes_its_poll_interval_to_the_serve_loop`
      records what the fixture hands ``threading.Thread`` and fails if the
      interval is not there, whatever the constant says;
    * :meth:`test_the_live_fixture_stops_well_inside_the_stdlib_wait` times the
      fixture's real teardown against an absolute 0.2 s, so it also fails if
      the constant is raised back to the stdlib 0.5 s while still being passed.

    Both drive the real ``live`` fixture by hand rather than re-building a
    server that resembles it: a copy of the fixture's own code would keep
    passing the interval after the fixture stopped. Together they cost 0.24 s
    (0.17 s + 0.07 s measured), and both fail on the mutant above.
    """

    def test_the_live_fixture_passes_its_poll_interval_to_the_serve_loop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The kwarg reaches ``serve_forever``, read off the real fixture."""
        recorded: list[dict[str, object]] = []
        real_thread = threading.Thread

        def spy(*args, **kwargs):
            recorded.append(kwargs)
            return real_thread(*args, **kwargs)

        monkeypatch.setattr(threading, "Thread", spy)

        generator = _fixture_function(_live_fixture)(tmp_path, monkeypatch)
        next(generator)
        try:
            serve_loops = [
                kwargs
                for kwargs in recorded
                if getattr(kwargs.get("target"), "__name__", "") == "serve_forever"
            ]
        finally:
            with pytest.raises(StopIteration):
                next(generator)

        assert len(serve_loops) == 1, (
            f"the live fixture started {len(serve_loops)} serve_forever threads; "
            f"this guard reads the poll interval off exactly one"
        )
        interval = _recorded_poll_interval(serve_loops[0])
        assert interval is not None, (
            "the live fixture no longer passes poll_interval to serve_forever, so "
            "its serve loop is back on socketserver's "
            f"{STDLIB_POLL_INTERVAL_S}s default and every browser test pays a "
            f"0-{STDLIB_POLL_INTERVAL_S}s teardown wait again — the whole of "
            f"CARD-235's ~126 s saving. Pass "
            "kwargs={'poll_interval': _SERVE_POLL_INTERVAL_S} as the fixture did"
        )
        assert interval == _SERVE_POLL_INTERVAL_S
        assert interval < STDLIB_POLL_INTERVAL_S

    def test_the_live_fixture_stops_well_inside_the_stdlib_wait(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """And the kwarg does what it is for: ``shutdown()`` returns promptly.

        The fixture's teardown is driven by hand because pytest runs the real
        one after the test has finished reporting, where nothing can time it.
        The sleep before the clock starts is what makes the measurement mean
        something: it puts the serve loop inside a poll wait, which is the
        state every real teardown finds it in.
        """
        generator = _fixture_function(_live_fixture)(tmp_path, monkeypatch)
        next(generator)
        time.sleep(_SERVE_SETTLE_S)

        started = time.perf_counter()
        with pytest.raises(StopIteration):
            next(generator)
        elapsed = time.perf_counter() - started

        assert elapsed < MAX_LIVE_TEARDOWN_S, (
            f"the live fixture took {elapsed:.3f}s to stop its server, over the "
            f"{MAX_LIVE_TEARDOWN_S}s bound and near socketserver's "
            f"{STDLIB_POLL_INTERVAL_S}s default poll. shutdown() cannot return "
            f"until the serve loop next wakes, so this is the wait CARD-235 "
            f"removed coming back: 422 browser tests pay it once each"
        )


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

    def test_the_probe_file_installs_the_state_the_ordering_is_about(self) -> None:
        """The probe has to be a file where an ordering could expose something.

        Running two orderings over a file that never saves to ``localStorage``,
        never intercepts a request and never installs a listener proves only
        that pytest can reorder tests. :data:`PAGE_ISOLATION` names those three
        mechanisms as the family's cross-talk risk, so the probe file is
        required to carry at least an interceptor or a listener as well as a
        save — which is why :data:`ORDER_PROBE_FILE` is not the cheapest file.
        """
        assert ORDER_PROBE_FILE in _family_files()
        source = (REPO_ROOT / ORDER_PROBE_FILE).read_text(encoding="utf-8")

        assert re.search(r"localStorage", source), (
            f"{ORDER_PROBE_FILE} touches no localStorage, so an ordering over "
            f"it cannot expose a save outliving the test that wrote it"
        )
        assert re.search(r"\.route\(|\.on\(", source), (
            f"{ORDER_PROBE_FILE} installs neither a page.route interceptor nor "
            f"a listener, which is what PAGE_ISOLATION names as the risk an "
            f"ordering is meant to find; point ORDER_PROBE_FILE at a file that "
            f"does"
        )

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
