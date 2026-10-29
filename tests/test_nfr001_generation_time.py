"""NFR-001/AC-037 — the 5s p95 generation bound, in a file pytest opens.

CARD-301. The criterion's verifier lived in ``tests/bench_generate.py``, whose
basename matches neither default ``python_files`` pattern, so **it had never
executed once**: measured twice independently, a bare ``pytest`` run collects
9,224 (2026-10-25) and then 9,570 (2026-10-29, main ``6b0dfa30``) tests and
**0** of them were in that file, while its own docstring said it "runs inside
``pytest -q`` with the rest of the suite". A performance requirement read as
verified for as long as its gate was invisible.

The node ids this module owns, written out because a check ref is only alive
if a ``git grep`` finds it in a code file (the lesson of
``tests/test_public_player.py``'s AC-383..AC-386 refs, which named node ids in
a file that did not exist):

* ``tests/test_nfr001_generation_time.py::test_20x20_p95_is_under_5s``
* ``tests/test_nfr001_generation_time.py::test_the_corpus_is_fixed_and_the_p95_rank_is_the_nineteenth_of_twenty``
* ``tests/test_nfr001_generation_time.py::test_the_same_corpus_entry_replays_the_same_run``

What this module does **not** claim
-----------------------------------

**It does not report NFR-001 as met.** AC-037 is *known missed*, and the gate
below is ``xfail(strict=True)``: it is green while the cap is missed and goes
red on the day the solver meets it, which is what forces CARD-018's marker to
be removed rather than left to rot. Collecting the gate restores the
*measurement*, not the verdict — the verdict is recorded as a miss, in
``requirements.yml`` where a reader of the registry sees it and not only in a
pytest marker.

Why the gate moved here instead of the file being renamed
---------------------------------------------------------

Measured on CARD-301's branch (Mac15,6 / Apple M3 Pro, Python 3.14.3, pytest
9.1.1), with ``-o addopts=''`` throughout so the stacked ``-q`` could not
swallow a count:

* the gate costs **14.0 s** of call time (``--durations=0`` on this module at
  HEAD). Five readings, because a timing is a claim and its control is
  recomputation: 13.85 s through pytest before the move, 13.97 s driven
  directly with no pytest in the picture, 13.98 s and 14.00 s through pytest
  here, 14.22 s as the standalone ``-m`` door including interpreter start.
  The 0.4 s spread is the solver's own noise, which is why this is carried to
  one decimal;
* every other name in this module costs **0.02 s** or less, so the ten
  collected tests add **14.03 s** — every setup, call and teardown row of the
  module summed, 30 rows over 10 tests, counted from the rows and not from
  the summary line — to every full-suite run. Against a suite of 1433.47 s on
  the board's last committed profile
  (``meta/profiling/suite-durations-20261023.txt``) that is **0.98 %**, and
  inside the run-to-run spread CARD-218 measured as "tens of seconds".
  Fourteen tests in that profile are individually slower than this gate, the
  slowest at 81.03 s;
* the gate settles after 6 of 20 samples. The same corpus with the early exit
  disabled costs **40.79 s** and puts 6 of 20 over the cap at p95 = 5.001 s,
  which is what this gate will cost on the day the margin narrows enough to
  stop the early exit. The ceiling is ``tests/hang_guard.py``'s 120 s per
  test (CARD-292), and the gate cannot reach it: every request is capped at
  ``P95_CAP_SECONDS``, 20 of them bound the test at ~100 s — measured
  overshoot on a capped request was ≤ 2 ms;
* **the uncensored sweep must stay out of the suite**, and that is measured
  rather than asserted: ``python -m tests.bench_generate --full`` — the same
  corpus under the production-shaped 30 s budget — took **122.04 s** and read
  p95 = **24.881 s** (6 of 20 over the 5 s cap, one of them still censored at
  30 s). 122.04 s is *past* the 120 s hang-guard ceiling, which ``_exit()``s
  the whole session rather than failing one test. That is why ``measure()``
  and ``report()`` stay standalone and only the capped, early-exiting
  :func:`tests.bench_generate.gate_verdict` is collected — and it is also the
  honest answer to "how far off is AC-037?", which the censored gate can only
  bound at >= 5.001 s.

What renaming the file would have cost *on top* of the same seconds is the
reason it was declined: **seven committed references** name the path
``tests/bench_generate.py`` as where the benchmark lives — one each in
ADR-0001 (as a node id, ``::test_20x20_p95_is_under_5s``), ADR-0029 and
``meta/architecture/handoff.md``, and four pages under
``docs/how-it-works/``; counted by ``git grep`` over ``docs`` and ``meta``
with ``meta/kanban`` and the ``meta/review`` snapshots excluded. Three of the
seven are in artefacts this card is not to rewrite. Moving the gate's pytest
wrapper here keeps six of the seven true as they stand — the corpus, the cap,
the statistic and the timing all stay in ``tests/bench_generate.py``, which is
now an honest standalone with a ``__main__`` door and no name beginning
``test``. The seventh, ADR-0001's node id, is the one reference this card
necessarily invalidates: the gate function cannot both leave that file and
stay in it, and it has to leave for the pin over "files pytest never opens" to
shrink. It is reported as owed rather than edited here, since
``decisions/adr/`` is outside this card's declared ``Touches``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tests import bench_generate

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = REPO_ROOT / "tests" / "bench_generate.py"
REGISTRY = REPO_ROOT / "meta" / "architecture" / "requirements.yml"
THIS_MODULE = Path(__file__).relative_to(REPO_ROOT).as_posix()

#: The three claims ``tests/bench_generate.py``'s docstring made about its own
#: execution, each false and each measured false by CARD-301. Frozen as the
#: exact spellings that shipped, and that is the width of the rule: a
#: *reworded* execution claim is not caught here, which is why
#: :func:`test_the_benchmark_prose_claims_no_execution_context_it_does_not_have`
#: also requires the positive statement in :data:`NON_COLLECTION_STATEMENT`.
#: Whitespace is normalised before matching, because every one of the three
#: was wrapped across source lines.
RETIRED_CLAIMS: tuple[str, ...] = (
    "it runs inside ``pytest -q`` with the rest of the suite",
    "see ``tests/conftest.py`` for why a file named ``bench_generate.py`` is "
    "collected at all",
    "it fails when the cap is missed",
)

#: The other half of that rule: the benchmark must say plainly that it is not
#: collected. A docstring that went back to claiming the suite runs it would
#: have to delete this sentence, which reds — and that is what the frozen list
#: above cannot do on its own.
NON_COLLECTION_STATEMENT = "pytest does not collect this file"


def _normalised(text: str) -> str:
    """``text`` with every run of whitespace collapsed to one space."""
    return " ".join(text.split())


def _module_level_functions(path: Path) -> list[str]:
    """Every module-level ``def``/``async def`` name in ``path``, by ``ast``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _prose_reports(source: str) -> list[str]:
    """Which of :data:`RETIRED_CLAIMS` ``source`` still makes.

    A pure function of the text so the control below can feed it a planted
    claim as a string instead of writing a lying docstring into the tree.
    """
    prose = _normalised(source)
    return [claim for claim in RETIRED_CLAIMS if _normalised(claim) in prose]


# --------------------------------------------------------------------------
# AC-037 — the gate itself
# --------------------------------------------------------------------------


@pytest.mark.xfail(reason=bench_generate.XFAIL_REASON, strict=True)
def test_20x20_p95_is_under_5s() -> None:
    """AC-037: p95 completion for a 20x20 request, retries included, <= 5s.

    The measurement is :func:`tests.bench_generate.gate_verdict` — the corpus,
    the cap, the censoring and the early exit are all documented there. This
    is the pytest half: the strict-xfail marker, and the two assertions that
    turn its three return values into a verdict.

    **Strict, and deliberately so.** AC-037 is missed today, so this test is
    *expected to fail*; the day the solver brings the whole density range
    under the cap it XPASSes, ``strict=True`` turns that into a failure, and
    the marker has to be removed by the card that earned it. Per CARD-006 and
    ADR-0009 the lever is the solver's propagation strength, never this
    threshold or a friendlier corpus.
    """
    over_cap, measured_p95, verdict = bench_generate.gate_verdict()

    assert over_cap <= bench_generate._ALLOWED_OVER_CAP, verdict
    assert measured_p95 <= bench_generate.P95_CAP_SECONDS, verdict


# --------------------------------------------------------------------------
# The benchmark's own contract — a gate that cannot fail is not a gate
# --------------------------------------------------------------------------


def test_the_corpus_is_fixed_and_the_p95_rank_is_the_nineteenth_of_twenty() -> None:
    """Pins determinism and the statistic, so neither can drift silently.

    Sample count, rank and tolerance are what turn "p95 <= 5s" into a decidable
    proposition; if a later change grew the corpus without revisiting the rank,
    the gate would quietly start measuring something else. Moved here by
    CARD-301 from the uncollected file, where it pinned nothing because it
    never ran — and it is now also the mechanism behind that card's G-5: a
    round that reshaped ``CORPUS``, ``_P95_RANK``, ``_ALLOWED_OVER_CAP`` or the
    cap to make AC-037 green reds here.
    """
    assert len(bench_generate.CORPUS) == 20
    assert len(set(bench_generate.CORPUS)) == len(bench_generate.CORPUS)
    assert bench_generate._P95_RANK == 19
    assert bench_generate._ALLOWED_OVER_CAP == 1
    assert bench_generate.P95_CAP_SECONDS == 5.0


def test_the_same_corpus_entry_replays_the_same_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-0015 determinism, checked on the benchmark's own inputs.

    A benchmark whose corpus drew fresh randomness each run would measure a
    different puzzle every time and could not gate anything. Timing is not
    compared here — only the *work*: same seed, same discarded candidates, same
    final grid.

    **What it adds over ``tests/test_orchestrator.py``'s
    ``test_the_same_seed_reproduces_the_same_run``**, which already verifies
    ADR-0015 for grid, clues and attempts, is narrow and worth stating rather
    than leaving to look wider: this one uses the benchmark's own request shape
    (20x20 at a corpus density, not the orchestrator fixture's) and it also
    compares ``solution_count``. Kept by CARD-301 for that reason and because
    it costs 0.02 s; retired it would leave the corpus's comparability claim
    with no control at the size the benchmark runs.
    """
    monkeypatch.setattr(
        bench_generate.orchestrator,
        "GENERATION_BUDGET_SECONDS",
        bench_generate.P95_CAP_SECONDS,
    )
    density, seed = 60, bench_generate.SEEDS[0]
    request = bench_generate.GenerationRequest(
        mode="random",
        width=bench_generate.SIZE,
        height=bench_generate.SIZE,
        density=density,
        seed=seed,
    )

    first = bench_generate.orchestrator.generate(request)
    second = bench_generate.orchestrator.generate(request)

    assert first.grid == second.grid
    assert first.regenerate.attempts == second.regenerate.attempts
    assert first.solution_count == second.solution_count


# --------------------------------------------------------------------------
# CARD-301's own controls: the gate is a gate, and the benchmark stops lying
# --------------------------------------------------------------------------


def test_the_gate_carries_card_018s_strict_xfail_marker_unweakened() -> None:
    """CARD-301 G-5: the marker is moved, not softened.

    Three things, each of which a round that "fixed" AC-037 by reaching for
    the marker would break:

    * the gate carries an ``xfail`` and it is ``strict`` — a non-strict xfail
      is green whether the cap is met or missed, which would delete the one
      signal the move exists to restore;
    * its reason **is** :data:`tests.bench_generate.XFAIL_REASON`, by
      identity, so the wrapper cannot paraphrase CARD-018's measurement into
      something milder;
    * that reason still carries its own standing instruction and the density
      band it rests on, so the text cannot be hollowed out while keeping the
      name.
    """
    markers = [
        mark for mark in test_20x20_p95_is_under_5s.pytestmark if mark.name == "xfail"
    ]
    assert len(markers) == 1, test_20x20_p95_is_under_5s.pytestmark
    assert markers[0].kwargs.get("strict") is True, markers[0]
    assert markers[0].kwargs.get("reason") is bench_generate.XFAIL_REASON

    reason = bench_generate.XFAIL_REASON
    assert "do not remove it on partial data" in reason
    assert "35/38/40%" in reason
    assert "CARD-018" in reason


def test_the_benchmarks_own_instrument_still_measures_a_request() -> None:
    """The one hole a strict xfail cannot cover: a broken benchmark reads green.

    **Measured, not reasoned** — CARD-301's mutant M7 renamed
    ``gate_verdict`` out of the benchmark, so the gate raised
    ``AttributeError``; ``xfail`` absorbs any exception, so the gate reported
    XFAIL, exactly as it does for a missed cap. A strict xfail therefore
    cannot witness its own instrument, and ``xfail`` is G-5's to keep rather
    than this card's to reshape. So the instrument is driven here instead,
    outside the marker: one request at the corpus's cheapest point (density
    60, measured 0.008 s), through the same
    :func:`tests.bench_generate._time_one_request` the gate times every sample
    with.

    What is asserted is the shape the gate's arithmetic depends on — a
    positive elapsed time and an outcome from the three the function's
    docstring names — and ``"unique"`` specifically, which is a statement
    about the pipeline and not only about the timer: ADR-0015 makes this
    request deterministic and it finishes three orders of magnitude inside
    the default budget, so neither the abandoned nor the timeout branch is
    reachable here.
    """
    elapsed, outcome = bench_generate._time_one_request(60, bench_generate.SEEDS[0])

    assert elapsed > 0.0, elapsed
    assert outcome in {"unique", "abandoned", "timeout"}, outcome
    assert outcome == "unique", (elapsed, outcome)


def test_the_benchmark_module_declares_no_name_pytest_would_have_to_collect(
    pytestconfig: pytest.Config,
) -> None:
    """AC-1/AC-2: the uncollected file no longer declares anything collectible.

    The hole CARD-301 closed was a file full of ``test_*`` functions that
    pytest never opened. It is closed from both ends: the gate moved into this
    module, and ``tests/bench_generate.py`` now declares no module-level name
    beginning with a ``python_functions`` prefix — so it claims nothing, and
    ``tests/test_collected_names.py``'s pin over "files pytest never opens"
    drops it in the same commit.

    The prefixes come from :meth:`pytest.Config.getini`, not from a copy of
    pytest's defaults, for ADR-0039/R2's reason: if ``python_functions`` ever
    changes, this moves with it. Both halves are asserted, because the file
    being uncollectible is only interesting while it is also uncollected: its
    basename must match no ``python_files`` pattern either.
    """
    files = tuple(pytestconfig.getini("python_files"))
    functions = tuple(pytestconfig.getini("python_functions"))
    assert files and functions

    import fnmatch

    assert not any(fnmatch.fnmatch(BENCHMARK.name, pattern) for pattern in files), files

    declared = _module_level_functions(BENCHMARK)
    assert declared, BENCHMARK
    reads_as_test = [
        name for name in declared if any(name.startswith(prefix) for prefix in functions)
    ]
    assert reads_as_test == [], (
        f"{BENCHMARK.name} declares {reads_as_test}, which pytest would collect "
        "if it ever opened the file and never runs while it does not"
    )
    # The measurement is still reachable by name, so "declares no test" did
    # not become "declares nothing": these are what the gate above and the
    # module's `__main__` door call.
    assert {"gate_verdict", "measure", "report", "main"} <= set(declared), declared


def test_the_benchmark_prose_claims_no_execution_context_it_does_not_have() -> None:
    """AC-3: the docstring stops lying about how it runs.

    ``TestGuardProse_EveryNamedControlExists``' family (CARD-276 AC-6), one
    file over: a claim nobody can check is worse than no claim, and this file's
    three were checkable and false. The rule is :func:`_prose_reports` over
    :data:`RETIRED_CLAIMS` plus the positive
    :data:`NON_COLLECTION_STATEMENT`, and
    :func:`test_the_prose_rule_catches_each_retired_claim` is what says the
    negative half can fail.
    """
    source = BENCHMARK.read_text(encoding="utf-8")

    assert _prose_reports(source) == []
    assert NON_COLLECTION_STATEMENT in _normalised(source)


def test_the_prose_rule_catches_each_retired_claim() -> None:
    """Control for the rule above, in both directions and claim by claim.

    Each retired spelling is planted on its own — line-wrapped, as it was in
    the file, so the whitespace normalisation is exercised and not just
    asserted — and must be reported. Then the whole group is planted at once
    and all three must come back, so the rule cannot report one and stop.
    """
    for claim in RETIRED_CLAIMS:
        wrapped = claim.replace(" ", "\n", 1)
        assert _prose_reports(f'"""A docstring that says {wrapped}."""\n') == [claim]

    everything = " ".join(RETIRED_CLAIMS)
    assert _prose_reports(f'"""{everything}"""\n') == list(RETIRED_CLAIMS)

    # And the file as it ships, with the statement that replaced them, is
    # clean: the live assertion above is not passing because the rule reads
    # nothing.
    assert _prose_reports(NON_COLLECTION_STATEMENT) == []


def test_the_registry_names_this_module_and_every_ref_resolves() -> None:
    """AC-5, first half: AC-037's ``test:`` is a node id that resolves.

    It used to be ``BenchGenerate_20x20_p95Under5s``, a string that existed in
    exactly one file — ``tests/bench_generate.py``, at ``:3`` and ``:139`` —
    and in both places as prose. No class, no function, no node id: a criterion
    that read as mechanically checked and was not, which is the family this
    board has a standing rule about.

    Both directions, derived from the registry rather than from a list kept
    here, exactly as ``tests/test_public_player.py``'s own ref test does:

    #. every ref the registry points at this module resolves to a module-level
       function in it — a rename reds here instead of going quietly dead;
    #. every one of them is written out in this module's docstring, which is
       what a ``git grep`` for a check ref actually reads.

    The registry is parsed with a regex rather than a YAML library: there is no
    YAML parser in the dependency baseline (ADR-0006/R1), and the shape being
    read is one line.
    """
    registry = REGISTRY.read_text(encoding="utf-8")
    refs = sorted(
        set(re.findall(rf"({re.escape(THIS_MODULE)}::[A-Za-z_][A-Za-z0-9_]*)", registry))
    )
    assert refs == [f"{THIS_MODULE}::test_20x20_p95_is_under_5s"], refs

    defined = {
        name
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    }
    assert len(defined) >= 8, sorted(defined)

    missing = [ref for ref in refs if ref.split("::", 1)[1] not in defined]
    assert missing == [], missing

    docstring = __doc__ or ""
    unnamed = [ref for ref in refs if ref not in docstring]
    assert unnamed == [], (
        "these refs resolve in pytest but a git grep for the node id will not "
        f"find them in any code file: {unnamed}"
    )


def test_the_registry_records_ac037_as_known_missed() -> None:
    """AC-5, second half: the registry stops reading as verified.

    The criterion's state was recorded in exactly one place — a pytest marker
    in a file pytest never opened — so ``requirements.yml`` showed AC-037 with
    a ``test:`` beside it and nothing to say the bound is missed. A reader of
    the registry now sees both the state and the card that owns closing it.

    Read as text for the same reason as above, and keyed on AC-037's own block
    rather than on the file, so a statement sitting beside a different
    criterion cannot satisfy it. ``trace.yml`` still carries the retired
    ``BenchGenerate_20x20_p95Under5s`` label at ``:539`` — outside this card's
    declared ``Touches`` and reported as owed rather than asserted here, since
    a test that asserted the state it wants would be red on arrival and a test
    that asserted the state it has would pin the defect.
    """
    registry = REGISTRY.read_text(encoding="utf-8")
    start = registry.index("- id: AC-037")
    block = registry[start : registry.index("- id: AC-038", start)]

    assert "status: unmet" in block, block
    assert "KNOWN MISSED" in block, block
    assert "CARD-018" in block, block
    assert f"test: {THIS_MODULE}::test_20x20_p95_is_under_5s" in block, block
    # The retired label is still *named* in the block, in the comment that
    # records what it resolved to; what must not come back is its use as a
    # `test:` value, which is the shape that read as a live check ref.
    assert "test: BenchGenerate" not in block, block
