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
  tests the family held *when it was measured* is worth ~24 s — 2.6 % of the
  suite;
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
changes the timing every one of the 422 tests the family held *when it was
measured* runs under.

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
#: The structural saving is 422 (the family as it was measured) x
#: (0.327 - 0.028) = ~126 s of teardown, and the
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
    # CARD-270's file postdates ALONE_RECORD, so it is sampled here instead
    # (see test_the_record_reaches_every_file_in_the_family). This is its
    # test that leaves the most behind on a page: a viewport its pixel
    # readings are computed from, and two injected <style> elements that
    # override the board's own rules and that no navigation undoes.
    "tests/test_puzzle_solver_fifth_rule.py::"
    "TestSolverFifthRule_GeometryAndOtherMarksUnchanged::"
    "test_the_rules_against_paper_are_untouched",
    # CARD-267's file postdates ALONE_RECORD too, so it is sampled here for
    # the same reason. Of its tests this is the one whose verdict a
    # predecessor could most easily fake: it installs a CONTEXT request
    # listener — the one kind of listener that outlives a navigation — and its
    # whole claim is a count of what arrived on it, so a leftover listener or
    # a leftover request from a test before it is exactly the cross-talk
    # PAGE_ISOLATION names. Run alone, the count can only be its own.
    "tests/test_puzzle_solver_crosshair.py::"
    "TestSolverCrosshair_IsPureView::test_hovering_issues_no_request",
    # CARD-268's file postdates ALONE_RECORD too. Of its tests this is the
    # one a predecessor could most easily fake a verdict for: it installs a
    # CONTEXT request listener — the kind that outlives a navigation — and one
    # of its arms is a count of what arrived on it (G-2 for opening a probe
    # and marking inside one), so a leftover listener or a leftover request
    # from a test before it is exactly the cross-talk PAGE_ISOLATION names.
    "tests/test_puzzle_solver_probe.py::"
    "TestSolverProbe_MarksCarryTheTint::"
    "test_the_probes_marks_carry_the_marker_and_earlier_marks_do_not",
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
            f"removed coming back: the 422 browser tests the family held when "
            f"it was measured pay it once each"
        )


# ==========================================================================
# AC-2 — no *unrecorded* test added, and no test removed
# ==========================================================================

#: Node ids the browser family has gained since :data:`BEFORE_ARTEFACT` was
#: measured, each attributed to the card that added it and carrying the reason
#: that test exists.
#:
#: Why an allowlist rather than a number. CARD-235's AC-2 states its own scope
#: in its own words — *"no test lost: the collected test count and every test's
#: node id are unchanged — this card changes fixtures, never coverage"*. The
#: guard below was written to prove **CARD-235's own diff** changed no
#: coverage, but it was committed as a standing assertion over the repository,
#: where it reads instead as "no card may ever add a browser test again".
#: CARD-213 was the first card to try, and what it tripped on was a
#: hand-written ``assert len(ids) == 422`` — a snapshot, sitting in a test
#: whose own docstring says it compares against an independent record and not
#: against a snapshot.
#:
#: So the baseline is CARD-217's recorded set **plus this table**, and the
#: expected count is *derived* from that union by
#: :func:`_baseline_node_ids` — never written down again. The half of the
#: guard worth keeping still bites: an addition nobody recorded here fires
#: ``"tests added"``, and an allowlisted test that disappears without its
#: entry being struck fires ``"tests removed"``. An allowlist is a set a guard
#: consults, so it gets a control that can fail:
#: ``test_the_baseline_goes_red_in_both_directions`` drives the same derivation
#: over injected sets and shows a removal is caught **with** its entry and
#: missed **without** it (CARD-238's retrospective rule).
#:
#: Adding a browser test therefore means adding its node id here with a card
#: and a reason; deleting one means striking its entry. Neither is free, and
#: that is the point — the guard now catches an *unrecorded* change to the
#: family's coverage rather than any change at all.
ADDED_SINCE_BEFORE: dict[str, tuple[str, str]] = {
    "tests/test_puzzle_solver_clues.py::"
    "TestSolverClues_UniqueLengthCirclesAnywhere::"
    "test_the_unique_length_is_circled_where_its_run_is_closed": (
        "CARD-213",
        "AC-1: a clue value unique in its line is circled wherever its closed "
        "run sits, with undecided cells on both sides of it (rule C)",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "TestSolverClues_UniqueLengthCirclesAnywhere::"
    "test_rules_a_and_b_circle_none_of_them": (
        "CARD-213",
        "AC-1's control: rules A and B circle nothing on any of those lines, "
        "so every circle AC-1 asserts is rule C's and not an edge walk's",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "TestSolverClues_RepeatedLengthDoesNotCircle::"
    "test_the_repeated_value_circles_nothing": (
        "CARD-213",
        "AC-2: a closed run whose length occurs twice in the clue circles "
        "nothing, because rule C's uniqueness is per line and per value",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "TestSolverClues_RepeatedLengthDoesNotCircle::"
    "test_the_same_marks_circle_a_two_that_occurs_once": (
        "CARD-213",
        "AC-2's paired positive: the same marks under a clue where that value "
        "occurs once do circle it, so the negative is not vacuous",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "TestSolverClues_AmbiguousUniqueLengthCirclesNothing::"
    "test_two_matching_runs_circle_nothing_and_one_circles_the_three": (
        "CARD-213",
        "AC-3: two closed runs of the unique length are contradictory marks, "
        "so rule C circles nothing and must not take the leftmost; paired "
        "with the one-run half that does circle",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "TestSolverClues_OpenRunDoesNotCircle::"
    "test_the_open_run_does_not_circle_and_closing_it_does": (
        "CARD-213",
        "AC-4: a run with an undecided neighbour on either side is not "
        "closed, so rule C does not fire; paired with the closed half",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "TestSolverClues_RuleCOnlyAddsToTheOldTable::"
    "test_rule_c_adds_three_circles_and_removes_none": (
        "CARD-213",
        "AC-5 / G-4: against the frozen pre-card verdicts, rule C turns no "
        "True into a False and changes exactly three named lines, as a set",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "TestSolverClues_RuleCOnlyAddsToTheOldTable::"
    "test_the_old_table_is_covered": (
        "CARD-213",
        "AC-5's completeness check: the frozen BEFORE table covers every row "
        "of the two examples tables, so the comparison cannot skip a row",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "TestSolverClues_RuleCOnlyAddsToTheOldTable::"
    "test_the_reference_reproduces_the_pre_card_verdicts": (
        "CARD-213",
        "AC-5's calibration: the Python second implementation with rule C off "
        "reproduces all fifteen pre-card verdicts of the committed module",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "TestSolverClues_ZeroClueRuleUnchanged::"
    "test_the_zero_clue_and_the_same_marks_under_a_one": (
        "CARD-213",
        "AC-6: the [0] clue keeps its own rule — circled only on an all-white "
        "line — and the same marks under a clue of 1 show rule C still fires",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "test_PropertyTest_SolverClues_RuleCInvariantUnderTransposition": (
        "CARD-213",
        "AC-7: a seeded corpus of 180 boards and 4920 lines shows rule C is "
        "axis-independent, with asserted counts so it cannot hold vacuously",
    ),
    "tests/test_puzzle_solver_clues.py::"
    "test_PropertyTest_SolverClues_RuleCOnlyAddsToRulesAAndB": (
        "CARD-213",
        "G-4 as a property: over 3000 seeded lines rule C never loses a "
        "circle rules A and B give, with asserted changed/untouched counts",
    ),
    "tests/test_puzzle_solver_brush_menu.py::"
    "TestSolverBrushMenu_FourthBrushIsCalledClear::"
    "test_the_item_the_trigger_the_hint_and_the_confirmation_all_say_clear": (
        "CARD-247",
        "AC-1: the renamed fourth brush reads Clear in the menu item, the "
        "trigger text, its Brush: name, both hint sentences and the reset "
        "confirmation's body line (CARD-253 moved its title and accept "
        "button to Reset, so the label is read in three places now)",
    ),
    "tests/test_puzzle_solver_brush_menu.py::"
    "TestSolverBrushMenu_FourthBrushIsCalledClear::"
    "test_no_user_facing_string_in_the_player_says_undecided": (
        "CARD-247",
        "AC-1 over the whole rendered page rather than four literals, with a "
        "control requiring the sweep to find the word that replaced it",
    ),
    "tests/test_puzzle_solver_brush_menu.py::"
    "TestSolverBrushMenu_RenameDidNotTouchTheStateName::"
    "test_the_state_names_the_tool_values_and_the_order_are_unchanged": (
        "CARD-247",
        "AC-2: the label moved and the model did not — the four exported "
        "state constants, the data-player-tool values, the board's own "
        "data-state and the brush order are all unchanged",
    ),
    "tests/test_puzzle_solver_brush_menu.py::"
    "TestSolverRegion_ShowsThreeCellsInTheActiveBrush::"
    "test_it_renders_three_cells_and_no_region_text": (
        "CARD-247",
        "AC-3: the Region toggle's face is three rendered cells in a row with "
        "no text left in the button, and the run is aria-hidden decoration",
    ),
    "tests/test_puzzle_solver_brush_menu.py::"
    "TestSolverRegion_ShowsThreeCellsInTheActiveBrush::"
    "test_the_three_cells_follow_the_active_brush": (
        "CARD-247",
        "AC-3: all three cells carry the chosen brush's state for each of the "
        "four brushes, agree with the trigger, and really look different",
    ),
    "tests/test_puzzle_solver_brush_menu.py::"
    "TestSolverRegion_KeepsItsAccessibleNameAndPressedState::"
    "test_it_is_still_named_region_pressed_unpressed_and_across_brushes": (
        "CARD-247",
        "AC-4: the text that named the button is gone, so the name is "
        "asserted through Chromium's own computation, pressed, unpressed and "
        "under a brush change, with aria-pressed still flipping",
    ),
    "tests/test_puzzle_solver_marking.py::"
    "TestSolverReset_TheConfirmationNamesTheButtonThatOpensIt::"
    "test_the_confirmation_reads_reset_and_not_clear": (
        "CARD-253",
        "AC-1: the renamed reset confirmation reads 'Reset the board?' and "
        "'Reset board', the two literals this card changed",
    ),
    "tests/test_puzzle_solver_marking.py::"
    "TestSolverReset_TheConfirmationNamesTheButtonThatOpensIt::"
    "test_the_word_is_the_reset_buttons_and_is_not_the_brushs": (
        "CARD-253",
        "AC-2: the relation rather than an absence — the reset button's own "
        "word is the one its confirmation uses and is not the fourth brush's, "
        "all four labels read off the rendered page",
    ),
    "tests/test_puzzle_solver_marking.py::"
    "TestSolverReset_TheConfirmationNamesTheButtonThatOpensIt::"
    "test_the_dialog_announces_the_sentence_it_shows": (
        "CARD-253",
        "AC-2 through the accname algorithm: the alertdialog is named by the "
        "title element it displays, so the sentence announced is the one "
        "shown whatever that sentence becomes",
    ),
    "tests/test_puzzle_solver_marking.py::"
    "TestSolverReset_TheBrushKeepsItsName::"
    "test_the_fourth_brush_read_structurally_still_reads_clear": (
        "CARD-253",
        "AC-3 / G-1: the owner's decision that the brush keeps 'Clear', read "
        "through the structural locator AC-2's relation uses; the menu item, "
        "trigger text and Brush: name are CARD-247's test (cycle 1, F-003)",
    ),
    # CARD-270 — the first card to add a whole FILE to the family. A filled
    # cell's ink and every major rule are both --grid-ink, so runs of filled
    # cells merged into one blob across the every-fifth rules, the outer frame
    # and the clue gutters; the fix is an inset --player-thin hairline on the
    # filled cell. The file is listed in PAGE_ISOLATION like the others.
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::"
    "test_every_filled_cell_carries_the_inset_hairline": (
        "CARD-270",
        "AC-1's mechanism arm: every filled cell's computed box-shadow is one "
        "inset --player-thin hairline --player-rule wide, which is the "
        "regression net the pixel samples alone could not be",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::"
    "test_a_light_band_reads_across_the_fifth_rule[desktop-x]": (
        "CARD-270",
        "AC-1's pixel arm on the column axis at 1440x900: a light band reads "
        "between two filled cells across a .major-right fifth rule, with the "
        "same scanline read with the hairline suppressed as its control",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::"
    "test_a_light_band_reads_across_the_fifth_rule[desktop-y]": (
        "CARD-270",
        "AC-1's pixel arm on the row axis at 1440x900: the same reading across "
        "a .major-below fifth rule, which is a separate border property and so "
        "a separate way the fix could be half-applied",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::"
    "test_a_light_band_reads_across_the_fifth_rule[phone-x]": (
        "CARD-270",
        "the same FIGURES at 390x844, where the cell is 14.39 px — the size "
        "the card's Standards section names, and the only place a hairline "
        "that rounds away would show (CARD-270 review 1, F-002: the band "
        "figures used to be desktop-only)",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::"
    "test_a_light_band_reads_across_the_fifth_rule[phone-y]": (
        "CARD-270",
        "the row axis at 390x844: the phone viewport is where the @media "
        "floor and CARD-193's mirrored gutter change the layout, so each axis "
        "is measured there separately",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::"
    "test_an_ordinary_rule_reads_the_same_way[desktop-x]": (
        "CARD-270",
        "the card claims the division reads UNIFORMLY, so an ordinary thin "
        "rule between two filled cells is sampled on the column axis too",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::"
    "test_an_ordinary_rule_reads_the_same_way[desktop-y]": (
        "CARD-270",
        "the same uniformity claim on the row axis, where the thin rule is "
        "the cell's border-bottom rather than its border-right",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::"
    "test_an_ordinary_rule_reads_the_same_way[phone-x]": (
        "CARD-270",
        "the uniformity figure at 390x844 on the column axis: three "
        "contiguous --player-thin px is a different number from the major "
        "rule's 1/2/1, so it is its own way the hairline could collapse at "
        "the phone cell size",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::"
    "test_an_ordinary_rule_reads_the_same_way[phone-y]": (
        "CARD-270",
        "the uniformity figure at 390x844 on the row axis",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_EdgesAndGuttersToo::"
    "test_leaving_a_filled_cell_at_the_boards_edge_the_first_pixel_is_the_hairline"
    "[desktop]": (
        "CARD-270",
        "AC-2 at 1440x900: the defect class is any ink rule beside an ink "
        "fill, so the board's whole outer ring is swept — the outer frame and "
        "the clue gutters' edges are the other two places it bit",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_EdgesAndGuttersToo::"
    "test_leaving_a_filled_cell_at_the_boards_edge_the_first_pixel_is_the_hairline"
    "[phone]": (
        "CARD-270",
        "AC-2 at 390x844, where the 14 px cell floor and CARD-193's mirrored "
        "gutter put different rules on the ring's four sides",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_EdgesAndGuttersToo::"
    "test_the_sampled_edges_really_include_a_clue_gutter": (
        "CARD-270",
        "AC-2 is only about gutters while a gutter is flush against the grid; "
        "this measures that off the live boxes so the sweep above cannot "
        "quietly narrow to the frame alone",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_GeometryAndOtherMarksUnchanged::"
    "test_the_hairline_takes_no_part_in_layout[desktop]": (
        "CARD-270",
        "AC-3 at 1440x900: every cell measures the px --player-cell resolves "
        "to, which is the no-layout-shift claim measured rather than quoted "
        "from the box-shadow spec (its second arm, box-by-box against the "
        "hairline forced off, is the narrative one — MOVES-LAYOUT survives it "
        "and the first arm kills it)",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_GeometryAndOtherMarksUnchanged::"
    "test_the_hairline_takes_no_part_in_layout[phone]": (
        "CARD-270",
        "AC-3 at 390x844, the viewport whose cells are smallest and where a "
        "stray px of layout would show first",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_GeometryAndOtherMarksUnchanged::"
    "test_the_rules_against_paper_are_untouched": (
        "CARD-270",
        "AC-3: a BLANK board is pixel-for-pixel what it was under a control "
        "that suppresses box-shadow on EVERY .player-cell and not only the "
        "filled ones, so a hairline reaching a cell that is not filled reds "
        "it (measured with the REACHES-BLANK and BROADEN-UNKNOWN mutants; "
        "scoped to the filled state the comparison was equal by "
        "construction — CARD-270 review 1, F-001), and the major rules "
        "against paper are the weight they were",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_GeometryAndOtherMarksUnchanged::"
    "test_no_other_cell_state_gains_a_shadow": (
        "CARD-270",
        "AC-3: only the filled state has a box-shadow, and the empty dot and "
        "the '?' glyph still take their colour and size from their tokens",
    ),
    f"{FAMILY_PREFIX}_fifth_rule.py::"
    "TestSolverFifthRule_GeometryAndOtherMarksUnchanged::"
    "test_a_hinted_filled_cell_still_wears_the_hints_own_ring": (
        "CARD-270",
        "the edge of the claim: .is-hinted sets a box-shadow at the same "
        "specificity, so a cell that is filled AND hinted must still show "
        "CARD-183's paper ring and not this card's hairline",
    ),
    # CARD-271 — the owner's "clues sometimes are missed at the bottom and at
    # the left for big puzzles". CARD-212's duplicate gutters answer that only
    # where they FIT, and the biggest boards are exactly where they do not, so
    # each axis now keeps ONE gutter in view by sticking it to .player-stage's
    # scrollport — while it has the room, because a stuck band floats over the
    # cells it used to scroll away from and keeping the clues and keeping the
    # BOARD are the same space spent twice. Three existing files, no new one;
    # the room condition is what most of these entries are about, from one
    # side of its bar or the other.
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_TheStageIsTheScrollContainer::"
    "test_only_the_stage_scrolls_over_the_board": (
        "CARD-271",
        "\"What to implement\" item 3, which the card asks to be VERIFIED and "
        "not assumed: of the table's seven ancestors exactly one scrolls, so "
        "every sticky offset resolves against the box the fix intends",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_StayInViewOnAPlainBigBoard::"
    "test_the_bottom_right_cells_clues_are_in_view[the card's 1280x720--]": (
        "CARD-271",
        "AC-1 at the reported viewport: a 30x30 drawn plain, scrolled to its "
        "bottom-right cells, with that row's and that column's clues inside "
        "the stage and the cells passing UNDER the gutters, not over",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_StayInViewOnAPlainBigBoard::"
    "test_the_bottom_right_cells_clues_are_in_view[a short window, whole band gone--]": (
        "CARD-271",
        "AC-1 where the WHOLE column band scrolls off (211 px of overflow "
        "against a 135 px band), so the axis cannot be kept by luck of a "
        "partial scroll",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_StayInViewOnAPlainBigBoard::"
    "test_the_bottom_right_cells_clues_are_in_view[a narrow window, both axes--]": (
        "CARD-271",
        "AC-1 with BOTH axes overflowing at once, the case the card's three "
        "converging causes produce together and the one a single-axis fix "
        "would pass",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_StayInViewOnAPlainBigBoard::"
    "test_the_corner_sticks_on_both_axes": (
        "CARD-271",
        "AC-1's last clause: the corner is where the two bands cross, so it "
        "sticks on both axes and paints above both (z-index 3 against 2 and "
        "1) — otherwise the crossing is a hole the cells show through",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_DoubledGuttersAreNotStuck::"
    "test_the_duplicate_the_tfoot_and_its_corner_stay_put": (
        "CARD-271",
        "AC-4 as a positive claim rather than only as the unedited ladder "
        "gate: where CARD-212's duplicates fit, the duplicate, the tfoot band "
        "and the duplicate's corner are `static` at every zoom",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::"
    "test_each_axis_keeps_its_clues_exactly_when_it_has_the_room[1280x720]": (
        "CARD-271",
        "the room condition at the card's own viewport, with the decision "
        "re-derived from the page's own cover/port and solver.js's constant "
        "rather than read off the classes it set",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::"
    "test_each_axis_keeps_its_clues_exactly_when_it_has_the_room[1280x600]": (
        "CARD-271",
        "the deepest case the card has to FIX (0.364 of the stage), which is "
        "the lower edge the bar was measured against",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::"
    "test_each_axis_keeps_its_clues_exactly_when_it_has_the_room[900x700]": (
        "CARD-271",
        "the narrowest desktop measured: a plain big board scrolling on BOTH "
        "axes while still too wide to be mirrored",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::"
    "test_each_axis_keeps_its_clues_exactly_when_it_has_the_room[390x844]": (
        "CARD-271",
        "the one viewport at 100 % zoom where an axis GIVES UP (272.2 px of "
        "band over a 358 px stage), so the sample spans the bar from the "
        "refusing side and not only from the keeping side",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::"
    "test_each_axis_keeps_its_clues_exactly_when_it_has_the_room[600x844]": (
        "CARD-271",
        "the same board and mirror 210 px wider, where the same band CAN be "
        "kept — the pair with 390x844 is what makes the threshold a measured "
        "crossing rather than one viewport's answer",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::"
    "test_sticking_changes_neither_the_band_nor_the_overflow": (
        "CARD-271",
        "the rule must not feed back into its own input: sticking is "
        "layout-neutral and adds nothing to the scrollable overflow, so the "
        "board cannot flicker between the two answers on every resize",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_SmallBoardsUnaffectedByStickiness::"
    "test_a_15x15_moves_nothing[roomy]": (
        "CARD-271",
        "AC-5: a board that fits its stage observes nothing — every gutter "
        "box sits at its flow position, read as an offset from the TABLE so a "
        "sticky shift would show",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_SmallBoardsUnaffectedByStickiness::"
    "test_a_15x15_moves_nothing[laptop]": (
        "CARD-271",
        "AC-5 at a second viewport, so 'nothing changes' is not one window's "
        "coincidence",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_SmallBoardsUnaffectedByStickiness::"
    "test_a_15x15_moves_nothing[phone]": (
        "CARD-271",
        "AC-5 at phone width, where CARD-193's mirror would apply to a wider "
        "board and must still change nothing for this one",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_SmallBoardsUnaffectedByStickiness::"
    "test_a_resize_after_a_zoom_re_measures_the_room": (
        "CARD-271",
        "review cycle 1 F-001: a small board is `!isBig`, so before the fix "
        "no viewport change re-measured it and the classes set at load "
        "survived into a window refusing both axes — 105 of 140 visible cells "
        "then failed to take their own tap. Red at the pre-fix revision",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_SmallBoardsUnaffectedByStickiness::"
    "test_a_grown_window_re_measures_the_room_too": (
        "CARD-271",
        "F-001's other direction, because one direction of a bar is not a "
        "control for it: a board grown wider kept today's rendering where the "
        "rule says there is room, so the clues scrolled away",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_StickyGutterRendersCleanly::"
    "test_a_stuck_gutter_is_opaque_over_the_cells": (
        "CARD-271",
        "AC-6 in PIXELS, because no computed style can settle it: a "
        "transparent box under an opaque ancestor computes to alpha 1 too. "
        "All 900 cells filled, the board at its far corner, the colour at "
        "each stuck box's centre read out of a screenshot",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "TestSolverClues_StickyGutterRendersCleanly::"
    "test_a_stuck_gutter_keeps_its_heavy_edge_and_its_circles": (
        "CARD-271",
        "AC-6's other two halves: the gutter's heavy rule toward the grid is "
        "still drawn on a stuck band, and CARD-188's circled clue numbers "
        "ride along with the box they are a ::before of",
    ),
    f"{FAMILY_PREFIX}_clues.py::"
    "test_the_sticky_gutter_rules_declare_no_colour_but_the_one_token": (
        "CARD-271",
        "G-2 per rule: positioning declares no colour, so the four sticky "
        "rules must stay colour-free, and the one coloured value the card "
        "adds (.player-corner's background) must be a token — driven over the "
        "rule broken four ways, since a literal written as rgb(), as a named "
        "colour or inside color-mix is invisible to the whole-file hex sweep",
    ),
    f"{FAMILY_PREFIX}_phone.py::"
    "TestSolverPhone_MirroredGutterSticks::"
    "test_both_bands_are_in_view_at_every_corner": (
        "CARD-271",
        "AC-2: with CARD-193's mirror holding, the one row-clue gutter sticks "
        "to the scrollport's RIGHT and the column gutter to its top, at every "
        "corner including the one the board opens at, where the mirrored band "
        "sits a whole band-width off-screen",
    ),
    f"{FAMILY_PREFIX}_phone.py::"
    "TestSolverPhone_MirroredGutterSticks::"
    "test_the_mirrored_corner_sticks_to_the_right_too": (
        "CARD-271",
        "AC-2's corner: the mirror leaves ONE corner and it is the corner of "
        "both kept bands, so it carries both markers where a doubled board's "
        "right corner carries only the column one",
    ),
    f"{FAMILY_PREFIX}_phone.py::"
    "TestSolverPhone_MirroredGutterSticks::"
    "test_a_390px_phone_keeps_its_cells_rather_than_its_row_clues": (
        "CARD-271",
        "the card's one UNFIXED case, pinned as an owner decision rather than "
        "papered over: a 272.2 px band on a 358 px stage cannot be held in "
        "view without hiding the board, and both halves are asserted — the "
        "row clues really are gone, and a right-hand cell really does still "
        "take its own tap",
    ),
    f"{FAMILY_PREFIX}_zoom.py::"
    "TestSolverZoom_CluesStayInViewWhileZoomed::"
    "test_every_corner_keeps_that_cells_clues_in_view[plain 30x30 at 900x700-----]": (
        "CARD-271",
        "AC-3 on a plain board: zoomed and panned to each of the four "
        "corners, that cell's row clue and column clue are in view and a "
        "gutter paints over the cells, not the other way round",
    ),
    f"{FAMILY_PREFIX}_zoom.py::"
    "TestSolverZoom_CluesStayInViewWhileZoomed::"
    "test_every_corner_keeps_that_cells_clues_in_view[doubled 30x25 at 1920x1500-----]": (
        "CARD-271",
        "AC-3 on a DOUBLED board, the other layout a big board can settle "
        "on: the labelled gutter is the one that sticks and CARD-212's "
        "duplicates still scroll, as they always did",
    ),
    f"{FAMILY_PREFIX}_zoom.py::"
    "TestSolverZoom_CluesStayInViewWhileZoomed::"
    "test_each_axis_keeps_its_clues_up_to_the_zoom_its_band_outgrows": (
        "CARD-271",
        "AC-3's BOUNDARY, recorded as a limitation rather than left as a "
        "surprise: --player-zoom magnifies the band about as much as the "
        "cells, so each axis keeps only up to the zoom its band outgrows "
        "(rows to 225 %, columns to 150 % on this board). Owner decision 2",
    ),
    f"{FAMILY_PREFIX}_zoom.py::"
    "TestSolverZoom_CluesStayInViewWhileZoomed::"
    "test_zooming_and_panning_record_and_save_nothing": (
        "CARD-271",
        "G-4 / CON-021: a scroll and the sticky repaint it causes are not "
        "state. The whole solve-state snapshot — cells, errors, progress, "
        "hints, undo/redo aria, localStorage — is byte-identical across a "
        "zoom, five pans and a zoom back",
    ),
    # CARD-267's crosshair: a new file of the family, declared here and in
    # PAGE_ISOLATION like the thirteenth was (CARD-270).
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_RowColumnAndCluesLight::"
    "test_the_hovered_rows_column_and_clues_carry_the_marker": (
        "CARD-267",
        "AC-1: hovering (r, c) marks row r, column c and their clue boxes — "
        "asserted as an equality against the WHOLE board, so the 'and nothing "
        "else' half cannot drift out of it",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_RowColumnAndCluesLight::"
    "test_the_four_cell_states_stay_apart_under_the_tint": (
        "CARD-267",
        "Card item 5: all four data-state looks stay plainly apart under the "
        "tint on one hovered row — the three light states by distinct ::after "
        "content AND by each mark's own computed paint read against the "
        "tinted ground, the filled state by its ground's luma",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_RowColumnAndCluesLight::"
    "test_the_tint_changes_the_ground_of_both_a_cell_and_a_clue_box": (
        "CARD-267",
        "AC-1's class has to be worth something: the computed ground of a "
        "crossed cell and a crossed clue box changes and matches, while an "
        "uncrossed pair read in the same breath does not move",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_FollowsThePointer::"
    "test_a_move_clears_the_old_lines_and_marks_the_new": (
        "CARD-267",
        "AC-2: a move to another cell clears the old row/column/clues and "
        "marks exactly the new ones, with both snapshots compared against "
        "independently derived expectations",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_FollowsThePointer::"
    "test_a_move_inside_one_cell_writes_nothing": (
        "CARD-267",
        "Card item 4: a move that stays inside one cell costs no DOM write at "
        "all, counted by a MutationObserver that is then made to see a real "
        "write, so zero is a reading and not a blindness",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_LightsBothTwinsOnADoubledBoard::"
    "test_a_doubled_board_lights_two_row_boxes_and_two_column_boxes": (
        "CARD-267",
        "AC-3: on CARD-212's doubled gutters BOTH twins of the row clue and "
        "BOTH twins of the column clue carry the marker, because the parts "
        "are selected by axis plus data-line and never by DOM order",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_TouchKeepsTheLastCell::"
    "test_a_touch_drag_crosses_the_finger_and_the_crosshair_stays[chromium]": (
        "CARD-267",
        "AC-4: a real CDP touch drag crosses the cell under the finger, still "
        "marks exactly as today, and leaves the crosshair on the last touched "
        "cell after touchEnd — a phone has no hover to bring it back",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_TouchKeepsTheLastCell::"
    "test_a_single_tap_leaves_the_crosshair_on_the_tapped_cell[chromium]": (
        "CARD-267",
        "AC-4's other half: a tap can reach pointerup without one "
        "pointermove, which is why the crosshair follows pointerdown too",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_ClearsWhenThePointerLeaves::"
    "test_leaving_the_stage_clears_it_and_a_clue_box_does_not": (
        "CARD-267",
        "AC-5 and its boundary: leaving the stage clears the crosshair, while "
        "a pointer over a clue box keeps it — the second is what makes the "
        "first a boundary rather than a blanket",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_ClearsWhenThePointerLeaves::"
    "test_entering_and_leaving_without_ever_touching_a_cell_is_quiet": (
        "CARD-267",
        "AC-5's reachable error path: a pointer crossing a clue gutter and "
        "going out again leaves with nothing to clear, which is a TypeError "
        "in a pointer handler unless the empty case is guarded",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_IsPureView::"
    "test_a_long_hover_sequence_changes_no_state_no_history_and_no_save": (
        "CARD-267",
        "AC-6: forty hovers over a board that ALREADY HAS STATE change no "
        "data-state, no undo/redo aria, no counter, no clue circle and no "
        "localStorage entry — one snapshot compared whole, with every field "
        "asserted away from its virgin value first, so the equality reds on a "
        "field DESTROYED as well as on one written",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_IsPureView::"
    "test_hovering_issues_no_request": (
        "CARD-267",
        "G-3 / ADR-0038/R2: no request per mark and none per hover either, "
        "with the listener proved against the page's own loading requests "
        "before zero over the hovers is believed",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_IsPureView::"
    "test_the_state_module_knows_nothing_of_the_crosshair": (
        "CARD-267",
        "G-5 structural: solver_state.js mentions nothing of the crosshair "
        "and the renderer's crosshair code imports nothing — a crosshair that "
        "needed the state module would be designed wrong (ADR-0038/R4)",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_NoStaleMarkerAfterRedraw::"
    "test_a_redraw_clears_the_marker_and_the_same_cell_crosses_again": (
        "CARD-267",
        "AC-7: a redraw leaves no marker, and re-hovering the SAME cell "
        "crosses it again — the second half is the sharp one, since a "
        "remembered position with nothing painted paints nothing",
    ),
    # The editor page keeps the crosshair, on purpose (owner decision
    # 2026-10-28, review cycle 1's out-of-scope question).
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_ReachesTheManualEditor::"
    "test_hovering_the_editors_board_crosses_the_row_the_column_and_the_clues": (
        "CARD-267",
        "The manual editor loads the same solver.js into a .player-stage, so "
        "hovering ITS board crosses the row, the column and both clue axes "
        "too — the reach is a decision somebody made, not a side effect no "
        "test would notice losing",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_ReachesTheManualEditor::"
    "test_leaving_the_editors_stage_clears_it": (
        "CARD-267",
        "The crosshair's one stateful rule holds on the editor page as well: "
        "a pointer leaving that page's stage clears it, so the editor cannot "
        "keep a crosshair nothing is pointing at",
    ),
    f"{FAMILY_PREFIX}_crosshair.py::"
    "TestSolverCrosshair_AddsNoAria::"
    "test_hovering_adds_no_aria_attribute_and_announces_nothing": (
        "CARD-267",
        "AC-8's a11y half: hovering adds no ARIA attribute anywhere in the "
        "player and writes nothing to the live region, read element by "
        "element over the whole player in document order",
    ),
    # CARD-269 put the hint behind a three-rung ladder and added Check, which
    # is 28 node ids from the implementation; the seven
    # TestSolverHintLadder_EveryPressChangesSomethingSeen ids below it come
    # from the card's fix round 2, where review F-2's finding — every
    # sentence went only to the 1 x 1 clipped live region, so rung 2 changed
    # nothing a sighted player could see — was closed by promoting the
    # announcement into a visible line.
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_ThePureModule::test_the_ladder": (
        "CARD-269",
        "the ladder's pure half driven straight through solver_state.js: the "
        "four frozen authorities, the WHOLE rung x event transition table "
        "rather than a sample of it, the RangeErrors that make an unknown "
        "rung, an unknown event and a drifted cell loud instead of silent, "
        "the axis choice, hintReason on both near misses of each named case, "
        "and firstWrongRow's scan",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_FirstPressPointsAtALine::"
    "test_the_first_press_highlights_the_line_and_says_so": (
        "CARD-269",
        "AC-1: one press points at the line the next deduction lives on and "
        "does nothing else — no cell changes, Hints stays 0, nothing is "
        "recorded — with WHICH line that is taken from the Python line "
        "oracle in the test tree and not from solver_state.js, so the wrong "
        "line or the right line's wrong axis reds it",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_FirstPressPointsAtALine::"
    "test_the_cell_the_third_press_will_reveal_is_on_that_line": (
        "CARD-269",
        "card rule 5 (coherence) measured at rung 1 instead of inferred from "
        "the reset rule: the line this press highlights CONTAINS the cell the "
        "ladder will reveal two presses later",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_FirstPressPointsAtALine::"
    "test_the_highlight_survives_a_redraw": (
        "CARD-269",
        "AC-1's durability: a one-pixel resize replaces every cell and every "
        "clue box, so a highlight held as those ELEMENTS would vanish under "
        "the player still standing on the rung they pressed for (CARD-212's "
        "defect in the hinted outline); the board also doubles the row axis, "
        "so this covers the twin rule that both clue boxes carry the tint",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_SecondPressExplains::"
    "test_each_reason_is_announced_on_a_board_where_it_holds": (
        "CARD-269",
        "AC-2: rung 2 adds WHY on the same line and still records nothing, "
        "driven once per reason the pure module declares on a board where "
        "that precondition genuinely holds — and the set driven is asserted "
        "to BE the module's HINT_REASONS, so a reason added there without a "
        "board or without a sentence reds this rather than going untested "
        "(ADR-0039/R2)",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_ThirdPressRevealsTheSameSituation::"
    "test_the_third_press_reveals_the_cell_of_that_line": (
        "CARD-269",
        "AC-3: rung 3 is CARD-183's reveal unchanged, of a cell ON the line "
        "rungs 1 and 2 pointed at, announced in the shipped wording and "
        "still ONE undo step — one Undo takes the cell and the counter back "
        "together",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_ThirdPressRevealsTheSameSituation::"
    "test_the_ladder_is_back_on_rung_one": (
        "CARD-269",
        "AC-3's wrap, from the page: the press after a reveal points at a "
        "line again instead of revealing a second cell, which is nextRung's "
        "wrap where the player meets it",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_AnyChangeResetsTheLadder::"
    "test_the_next_press_is_rung_one_again[mark]": (
        "CARD-269",
        "AC-4 by a real click: a mark made while standing on rung 2 puts the "
        "next press back on rung 1 and takes the old highlight off the board",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_AnyChangeResetsTheLadder::"
    "test_the_next_press_is_rung_one_again[drag]": (
        "CARD-269",
        "AC-4 by a real drag, which commits a multi-cell stroke — its own "
        "case because 'every route goes through one place' is the claim being "
        "measured here, not the assumption the cases rest on",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_AnyChangeResetsTheLadder::"
    "test_the_next_press_is_rung_one_again[undo]": (
        "CARD-269",
        "AC-4 via Undo: a change that arrives from the history rather than "
        "from the pointer still drops the rung and clears the line",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_AnyChangeResetsTheLadder::"
    "test_the_next_press_is_rung_one_again[redo]": (
        "CARD-269",
        "AC-4 via Redo, the route a single 'a mark resets it' case would have "
        "left resting on the Undo half of the same history",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_AnyChangeResetsTheLadder::"
    "test_the_next_press_is_rung_one_again[reset]": (
        "CARD-269",
        "AC-4 via a confirmed Reset of the whole board — the change that is "
        "not an edit of one cell and goes through its own dialog",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_AnyChangeResetsTheLadder::"
    "test_the_next_press_is_rung_one_again[check]": (
        "CARD-269",
        "AC-4 via Check, which resets the ladder while putting its OWN line "
        "up — so this case asserts the highlight is not the ladder's old one "
        "rather than that it is empty, which is the one of the six that "
        "cannot be written like the others",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_AnyChangeResetsTheLadder::"
    "test_the_control_two_presses_with_no_change_between_them_do_climb": (
        "CARD-269",
        "the negative control for all six reset cases (ADR-0039/R4): with "
        "nothing happening between the presses the second DOES climb to rung "
        "2, so a ladder stuck on rung 1 for ever could not pass them",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_TheReasonIsNeverALie::"
    "test_every_named_reason_claimed_only_where_it_holds": (
        "CARD-269",
        "AC-8 over a seeded corpus of 1800 lines: a named reason is claimed "
        "only where its own precondition holds, with BOTH near misses "
        "counted and not merely present — an overlap window that still "
        "covers the cell but holds a known mark, and a line one run short of "
        "its clue — and the run named re-checked by enumeration rather than "
        "by the arithmetic under test",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_TheReasonIsNeverALie::"
    "test_the_page_never_says_a_reason_it_did_not_check": (
        "CARD-269",
        "AC-8 where the player meets it: on each reason's own board the "
        "announced sentence carries that reason's words and NEITHER of the "
        "other named case's words, both directions once per board",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_NeitherRungNorCheckIsSaved::"
    "test_the_save_is_byte_identical_and_a_reload_starts_at_rung_one": (
        "CARD-269",
        "AC-9 / G-7 / CON-021: the save written with the ladder on rung 2 and "
        "Check pressed is byte-for-byte the save of the same marks without "
        "either, and a reload brings the marks back but not the rung — the "
        "first press after it points at a line",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_NeitherRungNorCheckIsSaved::"
    "test_the_control_rung_three_does_change_the_save": (
        "CARD-269",
        "the control for that byte-identity (ADR-0039/R4): the SAME "
        "instrument read around a rung-3 press shows a different save, so "
        "'equal' is a measurement and not the only thing the comparison can "
        "say",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverCheck_NamesTheFirstWrongRow::"
    "test_check_highlights_and_names_the_row": (
        "CARD-269",
        "AC-6: Check names the ROW of the first wrong mark, row-major, and "
        "nothing else — no cell changes, no stroke recorded, neither counter "
        "moves, and the sentence names no column at all; this is the control "
        "that says out loud what AC-328's wrong-mark blindness left Hint "
        "silently dancing around",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverCheck_NamesTheFirstWrongRow::"
    "test_the_row_is_the_first_one_row_major": (
        "CARD-269",
        "AC-6's ordering control: three wrong marks in row 12 against one in "
        "row 3, and row 3 is the row named — which reds a scan that ran the "
        "other way round or that counted errors per row",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverCheck_NamesTheFirstWrongRow::"
    "test_check_does_not_move_the_hinted_cell": (
        "CARD-269",
        "AC-6 / ADR-0038/R6 — Check is a reader: it leaves the revealed "
        "cell's own highlight and the Hints counter exactly where they were "
        "and records nothing over them",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverCheck_CleanLockedAndEditMode::"
    "test_a_clean_board_with_question_marks": (
        "CARD-269",
        "AC-7: Check on a board with no wrong marks says so, highlights "
        "nothing and leaves the cells and both counters alone, with question "
        "marks on the board while it does",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverCheck_CleanLockedAndEditMode::"
    "test_a_question_mark_over_a_filled_cell_is_not_wrong": (
        "CARD-269",
        "AC-7's sharper half of CARD-186's 'a ? is never wrong': a question "
        "mark sitting on a cell the solution FILLS, which a scan comparing "
        "raw states would have reported as an error",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverCheck_CleanLockedAndEditMode::"
    "test_a_locked_board_disables_check": (
        "CARD-269",
        "AC-7: a solved and locked board disables Check, proved with a real "
        "forced click on the disabled control — which writes nothing and "
        "leaves the Solved announcement standing",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverCheck_CleanLockedAndEditMode::"
    "test_the_editor_page_has_no_check": (
        "CARD-269",
        "AC-7: edit mode ships neither Check nor Hint — the solution there is "
        "the grid being rewritten — asserted as ABSENT on the real editor "
        "page, with the player page as the control that the same locators do "
        "find both",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHint_FallsBackToTheSolution::"
    "test_the_first_two_presses_say_no_line_decides_and_point_at_nothing": (
        "CARD-269",
        "AC-5 and the defect at the card's centre: on an exhausted board the "
        "two cheap rungs change no cell, count nothing and highlight NOTHING "
        "while saying so — where CARD-183 revealed a cell announcing 'no cell "
        "follows from a single line yet', which a player reads as a line "
        "deduction they missed when there was none to miss",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHint_FallsBackToTheSolution::"
    "test_the_control_a_deducible_board_does_get_a_line": (
        "CARD-269",
        "the negative control for both halves of that claim (ADR-0039/R4): "
        "the same two instruments, on a board where a line DOES decide a "
        "cell, read a highlighted line and a 'look at' sentence — so neither "
        "zero above is an instrument that could only ever read empty",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHint_ReducedMotion::"
    "test_without_reduced_motion_the_line_highlight_animates[chromium]": (
        "CARD-269",
        "AC-10's second control: rung 1's line fades its tint in on the cells "
        "AND on the clue box, so the reduced-motion zero measured beside it "
        "is a real suppression and not a highlight that never animates "
        "anywhere (ADR-0039/R4)",
    ),
    # Fix round 2 — review cycle 1's F-2, closed by the owner's decision of
    # 2026-10-30 to promote the announcement into a visible line. These seven
    # are phrased the other way round from the card's ten ACs: they assert the
    # VISIBLE sentence and the visible difference, which is why they catch
    # what "the live region says ..." could not.
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_EveryPressChangesSomethingSeen::"
    "test_the_instrument_rises_and_does_not_rise": (
        "CARD-269",
        "the instrument's own proof in BOTH directions before anything is "
        "claimed with it (ADR-0039/R4): a blank board and a board after one "
        "press give different screenshot digests on the board and on the line "
        "region, and the same page measured twice with nothing between gives "
        "identical ones — so a difference reported below is the page and not "
        "the element screenshot scrolling its target into view",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_EveryPressChangesSomethingSeen::"
    "test_three_presses_are_three_visibly_different_pages": (
        "CARD-269",
        "F-2's gating property as a property: each of the three presses "
        "changes something seen, and rung 2 — the press F-2 measured as "
        "byte-identical on the board and the toolbar — now differs on the "
        "visible line; F-2's own measurement is kept alive as a bound rather "
        "than as byte-identity, with rung 3 as the in-test control that the "
        "same bound does report a real change",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_EveryPressChangesSomethingSeen::"
    "test_the_next_recorded_change_clears_the_line": (
        "CARD-269",
        "AC-4's reset rule in the new visible channel: a recorded change "
        "empties the line, because a sentence about the board as it used to "
        "be is worse than no sentence, and the next press starts the ladder "
        "again visibly",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_EveryPressChangesSomethingSeen::"
    "test_the_exhausted_board_shows_the_sentence_it_used_to_only_speak": (
        "CARD-269",
        "F-2's second dead-button case, and the card's DECLARED RESIDUAL "
        "asserted instead of left as prose: card rule 6 fixes one sentence "
        "for both exhausted rungs, so the first press is now visible through "
        "the line alone while the board stays indistinguishable, and the "
        "SECOND press there still changes nothing seen — a card that gives it "
        "its own copy changes these last assertions on purpose",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_EveryPressChangesSomethingSeen::"
    "test_check_on_a_clean_board_shows_the_sentence": (
        "CARD-269",
        "F-2's third dead-button case, the one a recoloured tint could never "
        "have answered: 'Check: no wrong marks.' highlights nothing, so the "
        "visible sentence carries the whole press — with the wrong-marks "
        "board as the control that the same instrument does see a board "
        "change when Check paints a row",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_EveryPressChangesSomethingSeen::"
    "test_the_announce_region_did_not_regress_and_the_visible_copy_is_out_of_the_tree": (
        "CARD-269",
        "the visible line is an ADDITION and not a replacement: the live "
        "region keeps its shipped 1 x 1 clipped geometry, its role and its "
        "aria-atomic and is still written on a real press, while the visible "
        "copy is aria-hidden so assistive technology meets each sentence "
        "once — read off Chromium's real accessibility tree through CDP "
        "(get_by_text counts DOM copies and knows nothing of aria-hidden), "
        "with the attribute taken off and put back as the both-directions "
        "control",
    ),
    f"{FAMILY_PREFIX}_hint.py::"
    "TestSolverHintLadder_EveryPressChangesSomethingSeen::"
    "test_the_line_moves_neither_the_toolbar_nor_the_board[chromium]": (
        "CARD-269",
        "the test that CHOSE the placement, and the owner's guarantee that "
        "fix round 1's captured toolbar is still the shipped one: every box "
        "of the head, board, toolbar, counters and progress is identical "
        "empty versus full at 1280 and at 1440, the empty line is already one "
        "line box tall, and scrollWidth against clientWidth refuses a "
        "silently ellipsised sentence",
    ),
    # CARD-268 — probe mode: a group of marks made under one hypothesis,
    # kept or abandoned as one transaction. The probe is a CHECKPOINT in the
    # stroke history (one number), membership is derived from it, and the
    # marker rides data-probe rather than a fifth CELL_STATES member. The
    # second file to be added whole to the family after CARD-270's; it is
    # listed in PAGE_ISOLATION and sampled by ALONE_PROBES like the others.
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_StateIsPureAndStatesAreFour::"
    "test_the_named_rule_cases_match_the_oracle": (
        "CARD-268",
        "AC-9's rule table: one named case per numbered semantics rule the "
        "pure half carries, each compared with a Python oracle written from "
        "the card rather than from solver_state.js"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_StateIsPureAndStatesAreFour::"
    "test_a_seeded_corpus_matches_the_oracle": (
        "CARD-268",
        "AC-9's corpus arm: 300 seeded op sequences (marks with every "
        "brush, undo/redo, open/keep/abandon) against the same oracle, with "
        "the reached states counted so the equality cannot be an agreement "
        "about nothing"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_StateIsPureAndStatesAreFour::"
    "test_the_checkpoint_prefix_is_a_savable_history": (
        "CARD-268",
        "rule 9's precondition: the prefix a save is written from still "
        "starts from a blank board, which is the only history "
        "serializeState accepts, and differs from the live board only on "
        "cells the probe owns"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_StateIsPureAndStatesAreFour::"
    "test_the_cell_states_are_four_and_an_unknown_event_is_refused": (
        "CARD-268",
        "G-4 and the module's standing discipline: CELL_STATES is exactly "
        "today's four members in today's order, and an unknown probe event "
        "is a RangeError rather than a quiet 'leave it as it was'"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_StateIsPureAndStatesAreFour::"
    "test_the_probe_is_pure_and_only_the_renderer_knows_the_attribute": (
        "CARD-268",
        "ADR-0038/R4: the probe's transitions are exported from "
        "solver_state.js, that file reaches no DOM name, and data-probe is "
        "written only in solver.js"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_MarksCarryTheTint::"
    "test_the_probes_marks_carry_the_marker_and_earlier_marks_do_not": (
        "CARD-268",
        "AC-1: marks made with each brush inside a probe keep their own "
        "data-state and gain the marker, marks made before it gain none, "
        "and no request is made by opening or marking (G-2's probe half)"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_MarksCarryTheTint::"
    "test_the_four_states_stay_apart_under_the_tint": (
        "CARD-268",
        "rule 3 measured in pixels: the three light states share the tinted "
        "ground and are told apart by their own ::after channel, filled by "
        "its ground's luma -- CARD-267's instrument for the same claim "
        "about its own tint"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_MarksCarryTheTint::"
    "test_the_crosshair_does_not_repaint_a_probe_cell": (
        "CARD-268",
        "the three-way tie between the board's ground tints, driven by a "
        "real pointer: a probed cell reads the same crossed or not, and not "
        "as the crosshair's own ground"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_MarksCarryTheTint::"
    "test_the_hint_lines_tint_does_not_repaint_a_probe_cell": (
        "CARD-268",
        "the same tie against CARD-269's line highlight; a stylesheet-order "
        "claim, so the competing class is put on by script and only "
        "computed styles are read"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_AbandonRestoresTheCheckpointBoard::"
    "test_abandon_restores_the_board_and_closes_the_probe": (
        "CARD-268",
        "AC-2: four strokes over a board B, one press of Contradiction, and "
        "the board is B cell for cell with the probe closed and no marker "
        "left"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_AbandonRestoresTheCheckpointBoard::"
    "test_a_stroke_redone_after_an_abandon_is_a_normal_stroke": (
        "CARD-268",
        "rule 4's redo edge, which the card flagged as possibly ambiguous: "
        "an abandon is a run of undos, so a redone stroke past a CLOSED "
        "probe's old checkpoint is a normal stroke and carries no marker"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_CommitKeepsCellsAndDropsTheTint::"
    "test_keep_keeps_every_cell_and_drops_every_marker": (
        "CARD-268",
        "AC-3: Keep is a change of status and not of cells -- every "
        "data-state is what it was, every marker is gone, and the undo "
        "stack still holds each probe stroke as its own step"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_UndoClampsTheCheckpoint::"
    "test_undo_pops_probe_strokes_first_then_clamps": (
        "CARD-268",
        "AC-4: probe strokes pop first and their markers clear with them, a "
        "probe undone to nothing stays open, and an undo PAST the "
        "checkpoint clamps it instead of adopting the pre-probe stroke it "
        "took back"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_OnlyOneProbeAtATime::"
    "test_a_second_press_opens_nothing": (
        "CARD-268",
        "AC-5 / rule 1: of the card's two options the toggle is the "
        "disabled one, and the arm that actually proves depth 1 is that "
        "abandoning afterwards reaches the FIRST checkpoint's board"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_SolvingCommitsTheProbe::"
    "test_the_solving_mark_commits_the_probe": (
        "CARD-268",
        "AC-7: a probe whose marks complete the solution was a correct "
        "hypothesis, so it commits -- the banner, the lock and the announce "
        "line are exactly today's and no marker is left"
    ),
    f"{FAMILY_PREFIX}_probe.py::"
    "TestSolverProbe_CountersSeeProbeMarksAsMarks::"
    "test_the_same_marks_read_the_same_inside_a_probe": (
        "CARD-268",
        "AC-8 / rule 8: the same run of real input made twice on one page, "
        "once plain and once inside a probe, reads the same error count, "
        "percent and circled set, so no shipped AC-3xx is amended"
    ),
    f"{FAMILY_PREFIX}_resume.py::"
    "TestSolverResume_AReloadAbandonsTheOpenProbe::"
    "test_the_save_is_the_save_as_of_the_checkpoint": (
        "CARD-268",
        "AC-6: with a probe open the stored entry is byte for byte the "
        "entry as of the checkpoint, the page carries rule 9's one-line "
        "notice, and a reload comes back to the pre-probe board with the "
        "undo history intact"
    ),
    f"{FAMILY_PREFIX}_resume.py::"
    "TestSolverResume_AReloadAbandonsTheOpenProbe::"
    "test_an_open_probe_saves_no_redo_stack": (
        "CARD-268",
        "the card's one recorded divergence from rule 9, measured so that "
        "it is a tested claim and not a comment: the checkpoint prefix "
        "carries no redo stack, and the live player's redo is untouched"
    ),
}


#: The three files CARD-247's moves are in, spelled once (the ids below are
#: long enough without repeating the path four times per entry).
_BRUSH_MENU = f"{FAMILY_PREFIX}_brush_menu.py::"
_MARKING = f"{FAMILY_PREFIX}_marking.py::"
_MAYBE = f"{FAMILY_PREFIX}_maybe.py::"

#: Node ids whose PARAMETER was renamed, with no change to what the test does.
#:
#: :data:`ADDED_SINCE_BEFORE` can only ever add, and a rename is not an
#: addition: it is one id leaving and another arriving, which the guard reports
#: as both "tests added" and "tests removed" — and the removal half cannot be
#: registered away, because an id CARD-217 recorded must not simply disappear.
#: CARD-213 was the first card to add a browser test; CARD-247 is the first to
#: rename a parameter of one, and renaming a parameter is exactly what a
#: user-facing label rename does to this family: eight node ids carried the
#: brush label "Undecided" in their parameter, and the owner renamed that
#: label to "Clear".
#:
#: So a rename is recorded here as a MOVE, ``old id -> (card, new id,
#: reason)``, and :func:`_recorded_node_ids` applies it to CARD-217's record
#: before anything is compared. Both directions still bite, and the table
#: cannot be used to lose a test:
#:
#: * an UNrecorded rename is still red in both directions
#:   (``test_a_recorded_rename_is_a_move_and_an_unrecorded_one_goes_red``);
#: * a recorded rename whose old id is still collected is red in both
#:   directions too, so the table describes a move that happened rather than
#:   excusing one that did not;
#: * a move may only change what is inside the ``[...]`` of a node id —
#:   ``test_every_rename_entry_moves_one_recorded_id_and_is_attributed``
#:   refuses an entry whose two sides name different test functions, which is
#:   how this table would otherwise become a way to delete coverage quietly.
RENAMED_SINCE_BEFORE: dict[str, tuple[str, str, str]] = {
    f"{_BRUSH_MENU}TestSolverBrushMenu_RegionIsItsOwnToggle::"
    "test_adding_it_leaves_the_tools_slot_at_its_old_width"
    "[chromium-Undecided-1280-720]": (
        "CARD-247",
        f"{_BRUSH_MENU}TestSolverBrushMenu_RegionIsItsOwnToggle::"
        "test_adding_it_leaves_the_tools_slot_at_its_old_width"
        "[chromium-Clear-1280-720]",
        "the case is parametrized over MENU_ORDER, whose fourth brush the "
        "owner renamed from Undecided to Clear; the measured layout claim is "
        "the same claim, re-measured in the same test",
    ),
    f"{_BRUSH_MENU}TestSolverBrushMenu_RegionIsItsOwnToggle::"
    "test_adding_it_leaves_the_tools_slot_at_its_old_width"
    "[chromium-Undecided-1440-900]": (
        "CARD-247",
        f"{_BRUSH_MENU}TestSolverBrushMenu_RegionIsItsOwnToggle::"
        "test_adding_it_leaves_the_tools_slot_at_its_old_width"
        "[chromium-Clear-1440-900]",
        "the same MENU_ORDER rename at the 1440x900 viewport; the brush is a "
        "parameter of the layout case and nothing about the case changed",
    ),
    f"{_BRUSH_MENU}TestSolverBrushMenu_RegionIsItsOwnToggle::"
    "test_adding_it_leaves_the_tools_slot_at_its_old_width"
    "[chromium-Undecided-390-844]": (
        "CARD-247",
        f"{_BRUSH_MENU}TestSolverBrushMenu_RegionIsItsOwnToggle::"
        "test_adding_it_leaves_the_tools_slot_at_its_old_width"
        "[chromium-Clear-390-844]",
        "the same MENU_ORDER rename at the 390x844 phone viewport; the brush "
        "is a parameter of the layout case and nothing about the case changed",
    ),
    f"{_BRUSH_MENU}TestSolverRegion_DoesNotChangeTheBrush::"
    "test_pressing_and_releasing_region_keeps_the_brush[Undecided]": (
        "CARD-247",
        f"{_BRUSH_MENU}TestSolverRegion_DoesNotChangeTheBrush::"
        "test_pressing_and_releasing_region_keeps_the_brush[Clear]",
        "the brush parametrize list names the four labels; the renamed label "
        "is the only thing that moved and the behaviour asserted is CARD-211's",
    ),
    f"{_MARKING}TestSolverMarking_DragMarksOneLine::"
    "test_each_tool_sets_its_state_along_the_line[Undecided]": (
        "CARD-247",
        f"{_MARKING}TestSolverMarking_DragMarksOneLine::"
        "test_each_tool_sets_its_state_along_the_line[Clear]",
        "the tool parametrize names the label the menu shows; the state the "
        "drag lays down is still unknown and the assertion is unchanged",
    ),
    f"{_MARKING}TestSolverMarking_KeyboardAndLabels::"
    "test_each_tool_acts_on_a_single_key_press[Undecided-Enter]": (
        "CARD-247",
        f"{_MARKING}TestSolverMarking_KeyboardAndLabels::"
        "test_each_tool_acts_on_a_single_key_press[Clear-Enter]",
        "the name parametrize names the label reached in the menu; the key "
        "and the keyboard claim of AC-310 are untouched",
    ),
    f"{_MARKING}TestSolverMarking_KeyboardAndLabels::"
    "test_each_tool_acts_on_a_single_key_press[Undecided-Space]": (
        "CARD-247",
        f"{_MARKING}TestSolverMarking_KeyboardAndLabels::"
        "test_each_tool_acts_on_a_single_key_press[Clear-Space]",
        "the same rename on the Space half of the same keyboard case, whose "
        "assertions CARD-247 did not touch",
    ),
    f"{_MAYBE}TestSolverMaybe_ClickWithTheMaybeTool::"
    "test_a_maybe_cell_clicked_with_another_tool_takes_its_state"
    "[Undecided-unknown]": (
        "CARD-247",
        f"{_MAYBE}TestSolverMaybe_ClickWithTheMaybeTool::"
        "test_a_maybe_cell_clicked_with_another_tool_takes_its_state"
        "[Clear-unknown]",
        "the parametrize pairs the brush label with the state it paints; the "
        "label moved to Clear and the state it is paired with is still unknown",
    ),
}


def _recorded_node_ids(
    renames: dict[str, tuple[str, str, str]] | None = None,
) -> set[str]:
    """CARD-217's recorded family, with every recorded rename applied.

    A rename is a move (see :data:`RENAMED_SINCE_BEFORE`): the id leaves and
    one id arrives, so this set is always the same size as the artefact's own.
    ``renames`` is a parameter only so the controls below can run the
    derivation against a table they have altered; every real caller passes
    nothing.
    """
    moves = RENAMED_SINCE_BEFORE if renames is None else renames
    return {
        moves[node][1] if node in moves else node
        for node in _family_node_ids(BEFORE_ARTEFACT)
    }


def _baseline_node_ids(
    allowlist: dict[str, tuple[str, str]] | None = None,
    renames: dict[str, tuple[str, str, str]] | None = None,
) -> set[str]:
    """The node ids the family is expected to hold: the record | the allowlist.

    CARD-217's committed artefact supplies the recorded part (through
    :func:`_recorded_node_ids`, which applies the recorded renames to it) and
    :data:`ADDED_SINCE_BEFORE` the part added since. ``allowlist`` and
    ``renames`` are parameters only so the controls below can run this same
    derivation against tables they have altered; every real caller passes
    nothing.
    """
    entries = ADDED_SINCE_BEFORE if allowlist is None else allowlist
    return _recorded_node_ids(renames) | set(entries)


def _rename_problems(table: dict[str, tuple[str, str, str]]) -> list[str]:
    """What is wrong with ``table`` as a record of moves, one line each.

    A function and not a loop inside its test, because ADR-0039/R3 asks an
    exemption to carry a control for what it must NOT absorb: the refusals
    below only ever run over the real (clean) table, so each of them would be
    a branch nothing executes. ``test_the_rename_table_refuses_what_it_claims_to``
    drives this over tables it has broken on purpose, one case per refusal,
    asserting each case against the message of the refusal it is for — so a
    refusal deleted here takes its own case red even though several of those
    tables trip more than one of the refusals below.

    The dangerous entry is not a badly-worded one, it is an entry whose two
    sides are different tests: that would let a card delete a browser test by
    "renaming" it into one that already exists, which is the hole the
    allowlist was careful not to leave. So a move must start at an id
    CARD-217 recorded, end at one it did not, name only a different parameter
    of the SAME test function, and appear in neither direction in
    :data:`ADDED_SINCE_BEFORE`.
    """
    before = _family_node_ids(BEFORE_ARTEFACT)
    problems: list[str] = []
    for old, entry in sorted(table.items()):
        if not isinstance(entry, tuple) or len(entry) != 3:
            problems.append(
                f"{old}: entry must be (card, new id, reason), not {entry!r}")
            continue
        card, new, reason = entry
        if old not in before:
            problems.append(
                f"{old}: not in CARD-217's record, so there is nothing here to "
                f"move; a test added since is the allowlist's")
        if new in before:
            problems.append(
                f"{old}: {new} is itself recorded, so this is not a move but a "
                f"merge of two tests into one")
        if new == old:
            problems.append(f"{old}: moves to itself")
        if not new.startswith(FAMILY_PREFIX) or "::" not in new:
            problems.append(f"{old}: {new} is not a node id of the browser family")
        if old.split("[")[0] != new.split("[")[0]:
            problems.append(
                f"{old}: a move may rename a PARAMETER, not a test — {new} "
                f"names a different test function, which is a coverage change "
                f"and belongs in neither table")
        if not re.fullmatch(r"CARD-\d+", card):
            problems.append(f"{old}: {card!r} does not name the card that moved it")
        if len(reason.split()) < 8:
            problems.append(f"{old}: the reason says too little: {reason!r}")
        if old in ADDED_SINCE_BEFORE or new in ADDED_SINCE_BEFORE:
            problems.append(
                f"{old}: also in ADDED_SINCE_BEFORE, so the derived baseline "
                f"counts it twice")
    return problems


def _collection_drift(
    collected: set[str], baseline: set[str]
) -> dict[str, list[str]]:
    """The two directions the baseline comparison can go red in."""
    return {
        "added": sorted(collected - baseline),
        "removed": sorted(baseline - collected),
    }


class TestBrowserFixtures_NoTestAddedOrRemoved:
    """AC-2: every node id, not just the count — and no node id written by hand.

    CARD-235 changed fixtures and no coverage, which is what AC-2 was about.
    The standing version of that claim is the weaker, still useful one: the
    family's coverage changes only where a card has written the change down
    (:data:`ADDED_SINCE_BEFORE`).
    """

    def test_the_family_collects_exactly_what_card_217_measured(self) -> None:
        """Compared against an independent record plus a recorded allowlist.

        Nothing here is a snapshot of today's tree. The recorded half is read
        out of CARD-217's committed ``--durations`` artefact — every test that
        ran, by node id, recorded before CARD-235 existed and by somebody
        else. The added half is :data:`ADDED_SINCE_BEFORE`, one entry per node
        id gained since, each naming the card that added it and why. The
        expected count is ``len`` of their union, **derived** by
        :func:`_baseline_node_ids`: a hand-written count is exactly what
        failed here when CARD-213 added ten tests to one of the twelve files,
        and a count regenerated from today's collection could only ever agree
        with today's collection.

        Both directions still bite. A test added without an entry in the
        allowlist is reported as ``"tests added"``; a test removed — whether
        CARD-217 recorded it or the allowlist did — is reported as
        ``"tests removed"``, so deleting an allowlisted test means striking
        its entry in the same diff.

        The set comparisons are asserted before the count because
        ``"tests added"`` with the node ids is the useful failure; the count is
        implied by them and is asserted last as a statement of the derivation.
        """
        collected = _pytest(*_family_files(), "--collect-only")
        assert collected.returncode == 0, collected.stdout[-4000:]
        ids = {
            line.strip()
            for line in collected.stdout.splitlines()
            if line.startswith("tests/") and "::" in line
        }

        baseline = _baseline_node_ids()
        drift = _collection_drift(ids, baseline)

        assert drift["added"] == [], (
            f"tests added: {drift['added']} are collected in the browser "
            f"family but recorded nowhere. CARD-217's artefact does not hold "
            f"them and ADDED_SINCE_BEFORE does not either. If they are "
            f"deliberate, add each node id to ADDED_SINCE_BEFORE with the "
            f"card that added it and one line of why"
        )
        assert drift["removed"] == [], (
            f"tests removed: {drift['removed']} are expected but not "
            f"collected. A test recorded by CARD-217's artefact must not "
            f"disappear; one added by a later card may, but its "
            f"ADDED_SINCE_BEFORE entry has to be struck in the same diff"
        )
        assert len(ids) == len(baseline), (
            f"the family collects {len(ids)} tests against a baseline of "
            f"{len(baseline)} = {len(_family_node_ids(BEFORE_ARTEFACT))} "
            f"recorded by CARD-217 + {len(ADDED_SINCE_BEFORE)} allowlisted "
            f"since, with the two set comparisons above clean — which should "
            f"be impossible, so one of them is no longer comparing sets"
        )

    def test_the_baseline_goes_red_in_both_directions(self) -> None:
        """The allowlist is a set the guard consults, so it gets a failing control.

        Driven over injected sets rather than over a real collection: the
        point is what the comparison does when the tree and the record
        disagree, and no real tree can be made to disagree on demand. Four
        claims, each one the guard would be worthless without:

        1. an addition that is **not** in the allowlist is reported as added,
           and the entry is what lets a recorded one through — the same tree
           against an empty allowlist reports it as added;
        2. an allowlisted test that disappears is caught **with** its entry
           and missed **without** it, which is precisely why striking an entry
           has to be a deliberate edit rather than a side effect;
        3. a test CARD-217 recorded is caught when it disappears whatever the
           allowlist says, because the allowlist can only ever add;
        4. the derived count moves with the allowlist, so it cannot silently
           become a snapshot again.
        """
        # The recorded family as it stands after the renames — the set an
        # empty allowlist derives. Claim 4 below is what pins it to the
        # artefact's own size, so a rename cannot quietly add or lose an id.
        before = _baseline_node_ids({})
        recorded = sorted(ADDED_SINCE_BEFORE)[0]
        one_entry = {recorded: ADDED_SINCE_BEFORE[recorded]}
        unrecorded = (
            "tests/test_puzzle_solver_clues.py::"
            "TestSolverClues_NotInTheAllowlist::test_an_unrecorded_addition"
        )
        assert unrecorded not in ADDED_SINCE_BEFORE
        assert unrecorded not in before
        tree = before | {recorded}

        # 1 — an unrecorded addition is caught; the entry is what lets the
        # recorded one through.
        assert _collection_drift(
            tree | {unrecorded}, _baseline_node_ids(one_entry)
        ) == {"added": [unrecorded], "removed": []}
        assert _collection_drift(tree, _baseline_node_ids(one_entry)) == {
            "added": [],
            "removed": [],
        }
        assert _collection_drift(tree, _baseline_node_ids({}))["added"] == [recorded]

        # 2 — the same test removed: caught with its entry, missed without it.
        assert _collection_drift(before, _baseline_node_ids(one_entry)) == {
            "added": [],
            "removed": [recorded],
        }
        assert _collection_drift(before, _baseline_node_ids({})) == {
            "added": [],
            "removed": [],
        }

        # 3 — a test CARD-217 recorded cannot be dropped under any allowlist.
        dropped = sorted(before)[0]
        for table in ({}, one_entry, ADDED_SINCE_BEFORE):
            baseline = _baseline_node_ids(table)
            assert _collection_drift(baseline - {dropped}, baseline) == {
                "added": [],
                "removed": [dropped],
            }

        # 4 — the count is a function of the allowlist, not a literal, and
        # the renames are moves, so they leave the recorded size alone.
        assert len(_baseline_node_ids({})) == len(_family_node_ids(BEFORE_ARTEFACT))
        assert len(_baseline_node_ids(one_entry)) == len(before) + 1
        assert len(_baseline_node_ids()) == len(before) + len(ADDED_SINCE_BEFORE)

    def test_every_allowlist_entry_is_attributed_and_not_already_recorded(
        self,
    ) -> None:
        """The allowlist has to read as a record, not as a mute set of strings.

        An entry whose reason says nothing is an entry nobody can review, and
        an entry already in CARD-217's artefact is dead weight that would also
        break the derived count's arithmetic (claim 4 of the control above).
        """
        before = _family_node_ids(BEFORE_ARTEFACT)
        wrong = []
        for node, entry in sorted(ADDED_SINCE_BEFORE.items()):
            if not isinstance(entry, tuple) or len(entry) != 2:
                wrong.append(f"{node}: entry must be (card, reason), not {entry!r}")
                continue
            card, reason = entry
            if not node.startswith(f"{FAMILY_PREFIX}") or "::" not in node:
                wrong.append(f"{node}: not a node id of the browser family")
            if not re.fullmatch(r"CARD-\d+", card):
                wrong.append(f"{node}: {card!r} does not name the card that added it")
            if len(reason.split()) < 8:
                wrong.append(f"{node}: the reason says too little: {reason!r}")
            if node in before:
                wrong.append(
                    f"{node}: already in CARD-217's record, so the entry adds "
                    f"nothing and double-counts in the derived baseline"
                )
        assert wrong == [], wrong

    def test_every_rename_entry_moves_one_recorded_id_and_is_attributed(
        self,
    ) -> None:
        """:data:`RENAMED_SINCE_BEFORE` has to read as a record of moves.

        The refusals themselves are :func:`_rename_problems`, so that the
        control below can show each of them firing *by its own message* — nine
        cases, nine named refusals, each one asserted on the line only that
        refusal writes (ADR-0039/R1: a claim about what a guard catches needs
        a control that can fail). What this test
        adds is the arithmetic the table has to keep: a move is 1 -> 1, so
        applying the whole table leaves the recorded family exactly as large
        as CARD-217 recorded it.
        """
        assert _rename_problems(RENAMED_SINCE_BEFORE) == []
        assert len(_recorded_node_ids()) == len(_family_node_ids(BEFORE_ARTEFACT)), (
            "applying the renames changed the recorded family's size, so one "
            "of them is not a move"
        )

    def test_the_rename_table_refuses_what_it_claims_to(self) -> None:
        """Each refusal, driven over a table broken on purpose and asserted by
        the message of THAT refusal.

        Without this the refusals are branches nothing executes: the real
        table is clean, so every one of them is true for every possible
        implementation of itself. Asserting only that SOMETHING was refused
        does not fix that, and this control measured it the hard way: several
        of the tables below trip two or three refusals at once — every legal
        ``old`` is by construction recorded, so an entry that "moves to
        itself" also reads as a merge — and against a non-empty assertion four
        of the nine refusals could be deleted one at a time with every case
        still green (CARD-247 review cycle 1, F-001).

        So each case names the refusal it exists for and asserts THAT line is
        among the problems. Neutralising any one of the nine then takes its
        own case red, which is measured branch by branch rather than claimed
        here — the nine results are recorded in CARD-247's worktree notes.

        The fragments have to discriminate, or the same defect moves one layer
        up: a fragment that another refusal's message would also satisfy pins
        nothing. Two checks keep that honest — each fragment matches exactly
        ONE of the problem lines its own case produces (0 means the refusal it
        names did not fire, 2 means the fragment cannot say which refusal
        did), and no fragment is a substring of another, so no case can be
        satisfied by a neighbour's wording.
        """
        old = sorted(RENAMED_SINCE_BEFORE)[0]
        card, new, reason = RENAMED_SINCE_BEFORE[old]
        recorded = sorted(_family_node_ids(BEFORE_ARTEFACT))[0]
        unrecorded = f"{FAMILY_PREFIX}_page.py::TestNotAThing::test_nothing[x]"

        # label -> (a table broken on purpose, the refusal it must provoke)
        broken = {
            "not a 3-tuple": (
                {old: (card, new)},
                "entry must be (card, new id, reason)"),
            "nothing to move": (
                {unrecorded: (card, f"{unrecorded}y", reason)},
                "not in CARD-217's record"),
            "a merge, not a move": (
                {old: (card, recorded, reason)},
                "is itself recorded, so this is not a move but a merge"),
            "moves to itself": (
                {old: (card, old, reason)},
                "moves to itself"),
            "not of this family": (
                {old: (card, "tests/test_cli.py::test_x", reason)},
                "is not a node id of the browser family"),
            "renames the test": (
                {old: (card, f"{old.split('[')[0]}_renamed[Clear]", reason)},
                "a move may rename a PARAMETER, not a test"),
            "unattributed": (
                {old: ("the brush rename", new, reason)},
                "does not name the card that moved it"),
            "mute reason": (
                {old: (card, new, "renamed")},
                "the reason says too little"),
            "double-counted": (
                {sorted(ADDED_SINCE_BEFORE)[0]: (card, new, reason)},
                "also in ADDED_SINCE_BEFORE"),
        }
        for label, (table, expected) in broken.items():
            problems = _rename_problems(table)
            hits = [problem for problem in problems if expected in problem]
            assert len(hits) == 1, (
                f"{label}: {expected!r} matched {len(hits)} of {problems} — "
                f"with 0 the refusal it names did not fire, so the rule it "
                f"states is narrative (or another refusal is standing in for "
                f"it); with 2 the fragment is too loose to say which refusal "
                f"fired"
            )
        fragments = [expected for _table, expected in broken.values()]
        assert len(set(fragments)) == len(fragments), fragments
        nested = [(one, other)
                  for one in fragments for other in fragments
                  if one != other and one in other]
        assert nested == [], (
            f"{nested}: one expected message contains another, so the case "
            f"naming the shorter one would stay green on the longer one's "
            f"refusal — the defect this control is for, one layer up"
        )
        # ... and the real table trips none of them, so the refusals above are
        # not simply refusing everything.
        assert _rename_problems(RENAMED_SINCE_BEFORE) == []
        assert _rename_problems({old: RENAMED_SINCE_BEFORE[old]}) == []

    def test_a_recorded_rename_is_a_move_and_an_unrecorded_one_goes_red(
        self,
    ) -> None:
        """The rename table is a set the guard consults, so it gets a control.

        Driven over injected sets, like the allowlist's control above, and over
        one real entry so the derivation is exercised as it actually runs.
        Three claims: a recorded move is clean, an unrecorded one is red in
        BOTH directions (which is what a rename looks like to the guard), and
        a recorded move whose old id is still being collected is red in both
        directions too — the table describes a move that happened, it does not
        excuse one that did not.
        """
        before = _family_node_ids(BEFORE_ARTEFACT)
        old = sorted(RENAMED_SINCE_BEFORE)[0]
        _card, new, _reason = RENAMED_SINCE_BEFORE[old]
        one_move = {old: RENAMED_SINCE_BEFORE[old]}
        tree = (before - {old}) | {new}

        assert _collection_drift(tree, _baseline_node_ids({}, one_move)) == {
            "added": [],
            "removed": [],
        }
        assert _collection_drift(tree, _baseline_node_ids({}, {})) == {
            "added": [new],
            "removed": [old],
        }
        assert _collection_drift(before, _baseline_node_ids({}, one_move)) == {
            "added": [old],
            "removed": [new],
        }

    def test_the_family_on_disk_is_the_family_the_registry_names(self) -> None:
        """The file set on disk is pinned to the registries — by its **set**,
        twice, through two doors that do not share a data structure.

        It used to be pinned to a hand-written 12 as well. CARD-270 added the
        thirteenth file and that literal is exactly the kind of snapshot
        ``ADDED_SINCE_BEFORE`` exists instead of (CARD-213's ``assert
        len(ids) == 422``, in this same class), so it is gone.

        What replaced it was, for one cycle, ``len(files) ==
        len(PAGE_ISOLATION)`` beside the set equality — and a count taken
        beside the set equality it is derived from carries nothing:
        :func:`_family_files` globs one directory, so its basenames are
        distinct and the count is implied by the set. Every state that failed
        the count failed the set equality first, and the test's name
        advertised a derivation it did not have (CARD-270 review 1, F-003). It
        is gone too.

        The second door is a different registry: the node-id registries, whose
        keys name files as a side effect of naming tests. Every family file on
        disk must appear in CARD-217's measured artefact, in
        ``ADDED_SINCE_BEFORE``, or as a rename target in
        ``RENAMED_SINCE_BEFORE`` — and no other file may. That reds on states
        the ``PAGE_ISOLATION`` equality cannot see, the sharpest being a file
        given a ``PAGE_ISOLATION`` entry but no test registration at all
        (measured: the ``PAGE_ISOLATION`` arm stays green there).
        """
        files = _family_files()
        assert {path.split("/")[-1] for path in files} == set(PAGE_ISOLATION)

        named_by_node_ids = (
            {node.split("::")[0] for node in _family_node_ids(BEFORE_ARTEFACT)}
            | {node.split("::")[0] for node in ADDED_SINCE_BEFORE}
            | {new.split("::")[0] for _card, new, _why in RENAMED_SINCE_BEFORE.values()}
        )
        assert named_by_node_ids == set(files), {
            "on disk, named by no test registry": sorted(
                set(files) - named_by_node_ids
            ),
            "named by a test registry, not on disk": sorted(
                named_by_node_ids - set(files)
            ),
        }


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
        """Every family file is sampled alone — so no file is unsampled.

        Two ways to be sampled, and a file may not pick: by
        :data:`ALONE_RECORD`, CARD-235's out-of-band run over the family **as
        it then stood**; or, for a file that did not exist then, by an entry
        in :data:`ALONE_PROBES`, where ``test_the_riskiest_tests_pass_alone``
        really runs one of its tests alone in a child pytest every time this
        file runs. Backdating a record is not a thing this board does.

        "Did not exist then" is not a name written in here: it is a file with
        no node id in the measured artefact. A file that *was* measured and
        has since dropped out of the record still fails, as it always did —
        the exemption cannot be claimed by going missing.
        """
        record = ALONE_RECORD.read_text(encoding="utf-8")
        seen = {
            line.partition(" ")[2].strip().split("::")[0]
            for line in record.splitlines()
            if line.startswith("PASSED ")
        }
        measured = {node.split("::")[0] for node in _family_node_ids(BEFORE_ARTEFACT)}
        probed = {node.split("::")[0] for node in ALONE_PROBES}

        assert measured & set(_family_files()) <= seen, sorted(
            (measured & set(_family_files())) - seen)
        unsampled = [
            path for path in _family_files()
            if path not in seen and path not in probed
        ]
        assert unsampled == [], (
            f"{unsampled} postdate the alone-record and name no ALONE_PROBES "
            f"test, so nothing ever runs them alone"
        )


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
