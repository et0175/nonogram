"""NFR-001/AC-037 — the 5s p95 generation bound, in a file pytest opens.

CARD-301. The criterion's verifier lived in ``tests/bench_generate.py``, whose
basename matches neither default ``python_files`` pattern, so **it had never
executed once**: measured twice independently, a bare ``pytest`` run collects
9,224 (2026-10-25) and then 9,570 (2026-10-29, main ``6b0dfa30``) tests and
**0** of them were in that file, while its own docstring said it "runs inside
``pytest -q`` with the rest of the suite". A performance requirement read as
verified for as long as its gate was invisible.

The three node ids **moved here from the uncollected file** — not the whole
module, which declares eleven. They are written out in full because a check
ref is only alive if a ``git grep`` finds it in a code file (the lesson of
``tests/test_public_player.py``'s AC-383..AC-386 refs, which named node ids in
a file that did not exist), and the first of the three is the one the
architecture model points at from two places
(``requirements.yml``'s AC-037 ``test:`` and ``trace.yml``'s NFR-001
``tests:``), which is the ref
:func:`test_the_registry_names_this_module_and_every_ref_resolves` holds to
this list:

* ``tests/test_nfr001_generation_time.py::test_20x20_p95_is_under_5s``
* ``tests/test_nfr001_generation_time.py::test_the_corpus_is_fixed_and_the_p95_rank_is_the_nineteenth_of_twenty``
* ``tests/test_nfr001_generation_time.py::test_the_same_corpus_entry_replays_the_same_run``

The other eight names are CARD-301's own controls, enumerable with
``pytest -o addopts='' --collect-only -q`` and not listed here, because a list
of them kept in prose is the very thing this module exists to stop trusting.

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
* every other name in this module costs **0.02 s** or less, so the eleven
  collected tests add **14.03-14.05 s** — every setup, call and teardown row
  of the module summed, 33 rows over 11 tests, counted from the rows and not
  from the summary line, two readings — to every full-suite run. (Ten tests
  and 30 rows at 14.03-14.15 s before review cycle 1's fixes added
  :func:`test_the_trace_matrix_names_this_modules_gate_for_nfr001`, whose own
  three rows are 0.00 s: the eleventh test reads two files and asserts on
  text.) Against a suite of 1433.47 s on the board's last committed profile
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
  overshoot on a capped request was ≤ 2 ms. **State the headroom as a number,
  because crossing it is not a red test but ``_exit()`` of the whole
  session:** 20 x 5.0 s = 100.0 s against 120 s is **20 s of margin**, and
  100.0 s is a floor rather than a ceiling (it excludes per-request overhead
  outside the cooperative deadline). So ``P95_CAP_SECONDS`` and
  ``len(CORPUS)`` cannot both grow, and a card that raises the cap toward
  ADR-0001's 30 s hard timeout has to shrink the corpus in the same change —
  which is a second reason
  :func:`test_the_corpus_is_fixed_and_the_p95_rank_is_the_nineteenth_of_twenty`
  pins both;
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
seven are in artefacts this card is not to rewrite. **Eight over the whole
tracked tree**, and the eighth is the stronger half of the argument rather
than a correction to it: ``src/nonogram/orchestrator.py:338`` names the path
in a comment, in the one tree CARD-301's G-1 forbids this card to touch —
present identically on main, so it is a reference the ``docs``/``meta``
pathspec hid rather than declined. It stays true for the same reason the other
seven do: the benchmark itself does not move. Moving the gate's pytest
wrapper here keeps seven of the eight true as they stand — the corpus, the
cap, the statistic and the timing all stay in ``tests/bench_generate.py``,
which is now an honest standalone with a ``__main__`` door and no name
beginning ``test``. The one exception, ADR-0001's node id, is the reference
this card necessarily invalidates: the gate function cannot both leave that
file and stay in it, and it must leave for the pin over "files pytest never
opens" to
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
TRACE = REPO_ROOT / "meta" / "architecture" / "trace.yml"
THIS_MODULE = Path(__file__).relative_to(REPO_ROOT).as_posix()

#: The label AC-037 and NFR-001 carried as a ``test:`` ref before CARD-301 — a
#: string that resolved to no class, no function and no node id.
#:
#: **Assembled from two fragments on purpose, and that is load-bearing rather
#: than fussy.** forge's ``validators/utils.symbol_exists()`` is
#: ``git grep -lw <ref> -- . ':(exclude)meta/architecture' ':(exclude)*.md'`` —
#: a text search — so whichever *code* file writes the whole token out
#: contiguously is the file that makes the dead label read ALIVE to the
#: validator. On main ``6b0dfa30`` that file was ``tests/bench_generate.py``
#: (prose, at ``:3`` and ``:139``); CARD-301 review cycle 1 measured that this
#: module had inherited the job, which is the camouflage relocated rather than
#: removed. Concatenating at import means the token appears in no source line
#: here, so :func:`test_the_trace_matrix_names_this_modules_gate_for_nfr001`
#: can assert the label's absence without becoming the reason a future
#: re-introduction of it would look resolvable.
RETIRED_LABEL = "BenchGenerate" + "_20x20_p95Under5s"

#: The three claims ``tests/bench_generate.py``'s docstring made about its own
#: execution, each false and each measured false by CARD-301. Frozen as the
#: exact spellings that shipped, and that is the whole width of the rule:
#: **exact spellings only.** A *reworded* execution claim is not caught here,
#: and — narrowed by review cycle 1, which measured it rather than taking the
#: first cut's word for it — it is not caught by the positive
#: :data:`NON_COLLECTION_STATEMENT` requirement either. That requirement closes
#: the *replacement* case (delete the "pytest does not collect this file"
#: sentence and
#: :func:`test_the_benchmark_prose_claims_no_execution_context_it_does_not_have`
#: reds) and does nothing about the *coexistence* case, which is the case a
#: reworded claim actually takes: cycle 1's edge mutant added "The suite does
#: execute every function below on each ``pytest -q`` run" two lines under the
#: retained positive statement and three prose tests passed. A new sentence
#: gets added; the old one is rarely deleted.
#:
#: What does reach the general case is structural rather than textual, and it
#: is worth naming here because it is the reason the residue is tolerable:
#: :func:`test_the_benchmark_module_declares_no_name_pytest_would_have_to_collect`
#: pins both halves of the file being uncollected — no ``python_files``-matching
#: basename and no ``python_functions``-matching module-level name — so prose
#: claiming the suite runs this file is false *and cannot become true by
#: accident*. Catching the prose itself in arbitrary wording would need a
#: pattern rule over sentences, and the live docstring legitimately contains
#: both "suite" and "collected" in one sentence (about the other module), so
#: such a rule would red on arrival. Declared, not hidden.
#:
#: Whitespace is normalised before matching, because every one of the three
#: was wrapped across source lines.
RETIRED_CLAIMS: tuple[str, ...] = (
    "it runs inside ``pytest -q`` with the rest of the suite",
    "see ``tests/conftest.py`` for why a file named ``bench_generate.py`` is "
    "collected at all",
    "it fails when the cap is missed",
)

#: The other half of that rule: the benchmark must say plainly that it is not
#: collected. What this catches, exactly, is a docstring rewrite that *removes*
#: the statement — not one that contradicts it in a new sentence while leaving
#: it standing (see :data:`RETIRED_CLAIMS` for the mutant that establishes the
#: difference).
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
    """Pins the corpus's *content*, the statistic and the tolerance.

    Sample count, rank and tolerance are what turn "p95 <= 5s" into a decidable
    proposition; if a later change grew the corpus without revisiting the rank,
    the gate would quietly start measuring something else. Moved here by
    CARD-301 from the uncollected file, where it pinned nothing because it
    never ran — and it is the mechanism behind that card's G-5: a round that
    reshaped ``CORPUS``, ``DENSITIES``, ``SEEDS``, ``_P95_RANK``,
    ``_ALLOWED_OVER_CAP`` or the cap to make AC-037 green reds here.

    **The content pin is not decoration, and the shape pin on its own was not
    enough.** CARD-301 review cycle 1 measured the hole: with only
    ``len(CORPUS) == 20`` plus uniqueness asserted, swapping one line in the
    benchmark — ``DENSITIES = (30, 40, 50, 60)`` to ``(50, 60, 70, 80)`` —
    left this test *passing* (the band is still twenty unique pairs) and made
    the module's only red the gate's ``[XPASS(strict)]``, which under
    :data:`tests.bench_generate.XFAIL_REASON`'s own standing instruction reads
    as "the solver met the cap, remove the marker". It would not have been a
    hypothetical reshape: the same cycle's uncensored sweep times density 50 at
    0.008-0.041 s and density 60 at 0.004-0.011 s against density 40 at
    7.5-30.0 s, so the fast end of the supported band clears the 5 s cap by
    three orders of magnitude and a band swap is the cheapest possible way to
    fake AC-037.

    So the twenty requests are written out here, one row per seed, rather than
    rebuilt from ``DENSITIES``/``SEEDS`` with the benchmark's own comprehension:
    a second, independent spelling of the corpus is what CLAUDE.md asks for in
    place of re-deriving a value with the code under test, and writing it out
    also pins the **seed-major order** the early exit's cost argument depends
    on (interleaved densities, so the first six samples are a cross-section of
    the corpus and not one density's corner).
    """
    assert bench_generate.DENSITIES == (30, 40, 50, 60)
    assert bench_generate.SEEDS == (0, 1, 2, 3, 4)
    assert bench_generate.CORPUS == (
        (30, 0), (40, 0), (50, 0), (60, 0),
        (30, 1), (40, 1), (50, 1), (60, 1),
        (30, 2), (40, 2), (50, 2), (60, 2),
        (30, 3), (40, 3), (50, 3), (60, 3),
        (30, 4), (40, 4), (50, 4), (60, 4),
    ), bench_generate.CORPUS
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

    **Which mutant this test kills, corrected by review cycle 1 — M13, not
    M7.** Under M7 this test *passes*: it calls ``_time_one_request``, which
    renaming ``gate_verdict`` does not touch. M7 is the mutant that produced
    the insight (a strict xfail absorbs an ``AttributeError`` exactly as it
    absorbs a missed cap), and the cell that reds for it is
    :func:`test_the_benchmark_module_declares_no_name_pytest_would_have_to_collect`'s
    ``{"gate_verdict", "measure", "report", "main"} <= set(declared)``
    assertion. The mutant **this** cell is the only red for is M13 — deleting
    ``_time_one_request``'s body — where the gate still XFAILs green and
    ``test_the_same_corpus_entry_replays_the_same_run`` still passes (it calls
    ``orchestrator.generate``, not the timer). Both re-measured on the fix
    round's own harness.

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
    negative half can fail. :data:`RETIRED_CLAIMS` states the width of this
    rule and what it does not reach; read it before trusting this test to
    catch a claim in words it has not seen.
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

    It used to be the ``BenchGenerate…`` label :data:`RETIRED_LABEL` assembles,
    a string that existed in exactly one file — ``tests/bench_generate.py``, at
    ``:3`` and ``:139`` — and in both places as prose. No class, no function,
    no node id: a criterion that read as mechanically checked and was not,
    which is the family this board has a standing rule about.

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
    criterion cannot satisfy it. ``trace.yml``'s half of the same repair is
    :func:`test_the_trace_matrix_names_this_modules_gate_for_nfr001`.
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


def test_the_trace_matrix_names_this_modules_gate_for_nfr001() -> None:
    """AC-5's repair, one registry over: ``trace.yml``'s NFR-001 entry.

    ``requirements.yml`` and ``trace.yml`` are two halves of the same model and
    carried the same dead ref. CARD-301's first cut replaced it in one of them,
    which left the review cycle able to measure something sharper than a stale
    line: the branch had *relocated the camouflage*. On main the only file
    making :data:`RETIRED_LABEL` resolve to forge's ``git grep -lw`` was
    ``tests/bench_generate.py``'s own prose; on the branch it was this module's
    prose. So the label the card retired from one file was kept alive, for the
    validator's door, by the file the card added to close that family.

    Three things asserted, and the first two are the reason the third is not
    enough on its own:

    #. NFR-001's ``tests:`` list names this module's gate **by node id**, so a
       reader of the trace matrix looking for NFR-001's verifier finds
       something that resolves;
    #. the ref in that list is the *same string* AC-037 declares in
       ``requirements.yml``, read out of the registry rather than written twice
       here. That is ``validators/trace.py::_check_covered_tests`` gate 2's own
       rule ("every ``test:`` on the requirement's acceptance criteria must
       appear in the entry's ``tests:``") as a local control, which matters
       because all three of that validator's gates are conditioned on
       ``status: covered`` and NFR-001 is ``status: partial`` — the gate is
       **latent**, so nothing in forge reads this today and nothing in forge
       would have caught the line this test repairs;
    #. the retired label appears nowhere in the matrix at all, not merely
       nowhere in this entry. Gate 3's ``cs.exists()`` is a text search, so on
       the day a card flips NFR-001 to ``covered`` a dead label in the list is
       accepted *silently* while gate 2 ERRORs loudly about something else —
       the quiet half is the one that needs a control.
    """
    trace = TRACE.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")

    nfr001 = trace.index("- req: NFR-001")
    entry = trace[nfr001 : trace.index("- req: NFR-002", nfr001)]

    ac037 = registry.index("- id: AC-037")
    block = registry[ac037 : registry.index("- id: AC-038", ac037)]
    declared = re.findall(r"^\s*test: (\S+)$", block, flags=re.MULTILINE)
    assert declared == [f"{THIS_MODULE}::test_20x20_p95_is_under_5s"], declared

    assert f"- {declared[0]}" in entry, entry
    assert RETIRED_LABEL not in trace, RETIRED_LABEL
