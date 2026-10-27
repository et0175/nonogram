"""CARD-292's ceiling probe -- the instrument AC-1 asks for, kept OUT of
``tests/`` (G-3) and named so pytest's ``python_files`` default never collects
it from a suite run.  It is a pytest FILE, but ``card292_*`` matches neither
``test_*.py`` nor ``*_test.py``, so the only way it runs is an explicit path
argument, which pytest honours through ``Session.isinitpath``.

Why a probe at all: the card records a test dying twice at **120.93 s and
120.98 s** -- two figures 50 ms apart at two different revisions -- with exit 1,
**zero bytes of output** and ``0 signals received``.  Two readings that close
agree are a *limit*, not a cost, and a cost does not produce zero bytes.  The
probe exists to find which limit, by paying a parameterised duration and
bisecting where the payment stops being accepted.

Usage (the duration is read from the environment so one file serves every
reading, and so the reading is visible in the shell line that took it)::

    CARD292_BURN=130 CARD292_MODE=sleep \
        python -m pytest meta/profiling/card292_ceiling_probe.py -o addopts='' -s

``CARD292_MODE``:

``sleep``
    wall clock with ~no CPU -- ``time.sleep`` in one call.
``spin``
    wall clock AND CPU -- a busy loop on the GIL.
``split``
    the same total wall clock divided over ``CARD292_PARTS`` separate TESTS in
    one pytest process, so that no single test is over the boundary.  This is
    the arm that separates a per-TEST limit from a per-PROCESS or per-SHELL
    one: if a limit is per test, ``split`` completes where ``sleep`` dies.
    (Measured: it does -- 3 tests of 45 s run 135.09 s in one process and
    pass, where one test of 130 s is killed.)

Every mode prints a monotonic stamp per second to stdout, so a kill leaves a
partial record of HOW FAR it got rather than only that it did not finish --
the card's whole-file runs died with ``[ 57%]`` and no summary, and that
percentage was the only surviving evidence.
"""

import os
import time

import pytest

#: Total seconds the probe is asked to pay.  Read at import so the collected
#: parametrisation reflects it.
BURN = float(os.environ.get("CARD292_BURN", "1"))
#: ``sleep`` | ``spin`` | ``split``
MODE = os.environ.get("CARD292_MODE", "sleep")
#: How many tests ``split`` divides :data:`BURN` over.
PARTS = int(os.environ.get("CARD292_PARTS", "3"))


def _pay(seconds, label):
    """Pay ``seconds`` of wall clock, printing one line per elapsed second.

    The print is the point: it is flushed, so whatever reads this process's
    stdout sees progress, and a truncated capture names the second it stopped.
    """
    started = time.monotonic()
    ticked = -1
    while True:
        elapsed = time.monotonic() - started
        if elapsed >= seconds:
            break
        whole = int(elapsed)
        if whole > ticked:
            ticked = whole
            print(
                f"CARD292 {label} t={whole}s "
                f"cpu={time.process_time():.2f} "
                f"wall={elapsed:.2f}",
                flush=True,
            )
        if MODE == "spin":
            # A busy loop, so CPU time tracks wall clock.  The bound keeps one
            # iteration short enough that the tick above stays once a second.
            for _ in range(200_000):
                pass
        else:
            time.sleep(min(0.25, seconds - elapsed))
    print(
        f"CARD292 {label} DONE wall={time.monotonic() - started:.2f} "
        f"cpu={time.process_time():.2f}",
        flush=True,
    )


# NO ``skipif`` ON EITHER TEST BELOW, and the reason is a tripwire this probe
# tripped on CARD-292's own commit. ``tests/test_suite_profile.py``'s
# ``test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones``
# enumerates every environment-dependent skip condition in the guarded tree --
# ``tests/`` AND ``meta/profiling/`` -- and asserts the set equal to a frozen
# ``MEASURED_SILENCES_ELSEWHERE``, because a skip keyed on host state is a
# verdict that depends on the host rather than on the code. It resolves the
# tree through ``git ls-files``, deliberately, so an untracked scratch file
# cannot decide a verdict: this probe passed that guard while it was untracked
# and reddened it the moment it was committed, which is the guard working.
#
# So the mode does not SILENCE a test, it decides what the test PAYS. The
# unused arm pays zero and passes, which costs nothing and registers no
# host-state silence.


def test_one_burn():
    """The whole of :data:`BURN` in ONE test -- zero in ``split`` mode."""
    _pay(0 if MODE == "split" else BURN, f"one[{MODE},{BURN}s]")


@pytest.mark.parametrize("part", range(PARTS))
def test_split_burn(part):
    """``PARTS`` tests, each paying ``BURN / PARTS`` -- none over the boundary
    on its own, the process over it in total. Zero outside ``split`` mode.

    This is the arm that separates a per-TEST bound from a per-PROCESS one.
    """
    _pay(0 if MODE != "split" else BURN / PARTS, f"split{part}[{BURN / PARTS:.1f}s]")
