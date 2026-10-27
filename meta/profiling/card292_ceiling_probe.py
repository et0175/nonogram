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


@pytest.mark.skipif(MODE == "split", reason="split mode uses the parts below")
def test_one_burn():
    """One test paying the whole of :data:`BURN`."""
    _pay(BURN, f"one[{MODE},{BURN}s]")


@pytest.mark.skipif(MODE != "split", reason="only split mode uses the parts")
@pytest.mark.parametrize("part", range(PARTS))
def test_split_burn(part):
    """``PARTS`` tests, each paying ``BURN / PARTS`` -- none over the boundary
    on its own, the process over it in total."""
    _pay(BURN / PARTS, f"split{part}[{BURN / PARTS:.1f}s]")
