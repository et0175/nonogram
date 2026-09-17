"""COMP-002/COMP-003 tests: POL-002's bounded pixel nudge and POL-003's stop.

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-034  TestNudge_AttemptsBoundedRecovery
                -> test_nudge_attempts_bounded_recovery*
    AC-035  TestNudge_ReportsFailureAtCap
                -> test_nudge_reports_failure_at_cap*
    AC-036  TestNudge_FailureMessageSuggestsRetry
                -> test_nudge_failure_message_suggests_retry*

What this file is about, and where the line between the two components falls
--------------------------------------------------------------------------
FR-013 is one policy split across two components (trace.yml's FR-013 note), so
the tests come in two halves and the halves assert different things.

*The policy* is COMP-002's: when a nudge fires, how many may fire, what stops
them, and what the user is told when they stop. Those are the AC tests, and
they run through ``orchestrator.generate`` with the **real** clue derivation
and the **real** solver — a nudged grid's uniqueness is never faked, because
CON-005 and guardrail G-4 are precisely the claim that it is not assumed
(``test_nudge_attempts_bounded_recovery_re_solves_every_nudged_grid``).

*The mechanism* is COMP-003's: which cell a nudge flips. Those tests call
``sourcing.image.nudge`` directly and assert its contract — deterministic,
non-mutating, nesting, one flip per attempt — rather than its taste. The
heuristic's *effectiveness* is not something a unit test can pin (it is the
risk CARD-016 exists to collapse); what is pinned instead is that it is
isolated behind one function, so it can be replaced without touching the loop.

Scripted grids, real solver
---------------------------
The scripted-source style of ``tests/test_orchestrator.py`` and
``tests/test_sourcing_image.py``: only the *grid* the mode produces is
scripted, and everything downstream of it is the real pipeline. Two grids do
most of the work:

``_ONE_SWITCH``   one diagonal pair of filled cells in an otherwise blank grid
                  — the smallest genuinely ambiguous conversion there is, and
                  one flip away from a uniquely-solvable puzzle.
``_SIX_SWITCHES`` six such pairs, spread out. Each nudge can break one, so five
                  nudges cannot break six: this is the conversion that reaches
                  the cap, by arithmetic rather than by luck.

Both are cross-checked against the real solver at the top of the module, so a
change to the heuristic that made them stop being one-flip-fixable or
cap-reaching fails loudly there instead of quietly turning an AC test vacuous.

Real images too
---------------
The scripted grids show the loop; two pinned fixture conversions show that it
works on an actual picture. ``owl1.png`` at 10x10 really does convert to an
ambiguous grid that two nudges repair, and the *same picture* at 15x15 really
does survive all five. One photograph doing both jobs is deliberate: it removes
"maybe the other fixture is just harder" as an explanation for the difference,
leaving the extent as the only variable.

Both are *pinned cases* in the sense ``tests/test_sourcing_image.py`` uses the
phrase: if the dither, the solver or the heuristic changes such that these sizes
behave differently, re-pin them by re-running a 10..25 sweep over the fixtures
rather than deleting the test.

These pins used to name ``bands.png`` at 10x10 and ``landscape.png`` at 22x22,
and they had **never** matched those files. The tests arrived in commit
``96da6ac`` (2026-09-08) referring to fixtures that were not in the repository;
two days later ``2aece6a``/``4295166`` and ``02a25a2`` created replacements to
make the suite runnable, and nobody re-derived the counts. The replacements are
32x32 and 60x40 hard black-and-white — two grey levels, no mid-tones — so the
Floyd-Steinberg dither has nothing to do and every conversion is trivially
unique. A 10..25 sweep over both finds **zero** nudges at every size, which is
why re-pinning the sizes (this module's own recipe, above) could not work here
and the pins had to move to a picture with actual tone in it. ``src/nonogram/
sourcing/image.py`` has not changed since those fixtures were written, so
nothing in the pipeline drifted — the pin and the fixture were simply never
taken from the same image (CARD-070).
"""

from __future__ import annotations

import inspect
import random
from pathlib import Path

import pytest

from nonogram import cli, clues, orchestrator, solver
from nonogram.errors import GenerationAbandoned
from nonogram.orchestrator import (
    MAX_NUDGE_ATTEMPTS,
    MAX_REGENERATE_ATTEMPTS,
    MAX_RESAMPLE_ATTEMPTS,
    MAX_RETRY_ATTEMPTS,
    GenerationRequest,
    Puzzle,
    generate,
)
from nonogram.sourcing import image

FIXTURES = Path(__file__).parent / "fixtures"
WIDE = FIXTURES / "wide.png"
#: CARD-026 re-pinned the two real-image cases below onto this fixture.
#: ``wide.png`` is 60x20, a 3:1 source, and FR-021 now *refuses* it against a
#: square grid — it keeps only 33% of the picture — so it can no longer be
#: converted at 20x20 or 22x22 at all. ``landscape.png`` is 60x40, a 3:2 source
#: that keeps 67% and is comfortably inside the accepted band; a fresh 10..25
#: sweep (the module docstring's own re-pinning recipe) picked the same two
#: sizes, which is a coincidence worth naming rather than relying on.
LANDSCAPE = FIXTURES / "landscape.png"

#: CARD-070 moved the two real-image pins here. ``owl1.png`` is a 405x500
#: photograph with 256 grey levels, so the dither actually dithers; a 10..25
#: sweep gives exactly 2 nudges at 10x10 and the cap at 15x15, and both are
#: seed-independent (image mode draws no randomness — the conversion is a pure
#: function of the file and the extent, so these are facts about the picture
#: rather than about a seed).
OWL = FIXTURES / "owl1.png"

Grid = list[list[bool]]


# --------------------------------------------------------------------------
# Grids, and the properties the tests below lean on
# --------------------------------------------------------------------------


def _switching_pairs(size: int, corners: tuple[tuple[int, int], ...]) -> Grid:
    """A blank ``size`` x ``size`` grid with a filled diagonal pair per corner.

    ``(r, c)`` fills ``(r, c)`` and ``(r + 1, c + 1)``. Two cells on a diagonal
    with nothing else near them are the textbook non-unique nonogram: the other
    diagonal has the same row clues and the same column clues, so no clue set
    can tell the two apart.
    """
    grid = [[False] * size for _ in range(size)]
    for row, column in corners:
        grid[row][column] = True
        grid[row + 1][column + 1] = True
    return grid


#: One ambiguity, one nudge away from a puzzle.
_ONE_SWITCH = _switching_pairs(10, ((2, 2),))

#: Six ambiguities, spread far enough apart that one flip cannot break two of
#: them. More ambiguities than the cap has nudges, which is what makes the
#: cap-exhaustion tests deterministic rather than dependent on the heuristic
#: happening to guess badly.
_SIX_SWITCHES = _switching_pairs(12, ((1, 1), (1, 5), (1, 9), (5, 1), (5, 5), (5, 9)))


def _solution_count(grid: Grid) -> int:
    """The real solver's verdict on ``grid``'s own clues (never a stand-in)."""
    grid_clues = clues.compute_clues(grid)
    return solver.solve(grid_clues.rows, grid_clues.columns).solution_count


def _verdict(grid: Grid) -> solver.SolveResult:
    """The real solver's verdict on ``grid``'s own clues (never a stand-in).

    Every witness pair and undecided mask below comes from here rather than
    from a hand-written literal: the cells ``next_nudge_cell`` chooses from are
    whatever COMP-005 actually reports, so a test that invented them could
    agree with the implementation and disagree with the solver.
    """
    grid_clues = clues.compute_clues(grid)
    return solver.solve(grid_clues.rows, grid_clues.columns)


def _differences(left: Grid, right: Grid) -> list[tuple[int, int]]:
    """Every cell where two same-shaped grids disagree, in row-major order."""
    return [
        (row, column)
        for row, (left_row, right_row) in enumerate(zip(left, right, strict=True))
        for column, (a, b) in enumerate(zip(left_row, right_row, strict=True))
        if a != b
    ]


def _nudge_run(original: Grid, cap: int = MAX_NUDGE_ATTEMPTS) -> list[Grid]:
    """The grids POL-002's loop judges for ``original``, attempt 1 first.

    COMP-002's loop replayed over COMP-003's two functions, so a test can name
    "the grid attempt 3 judged" without driving a whole run — the shape
    CARD-075 replaced ``image.nudge(grid, attempt)`` with, now that an attempt's
    cell depends on the solver's verdict on the attempt before it. It stops
    where the loop stops: at ``cap``, at a uniquely-solvable grid, or when
    there is no unflipped cell left to add.
    """
    cells: list[tuple[int, int]] = []
    judged = original
    verdict = _verdict(original)
    grids: list[Grid] = []
    for _ in range(cap):
        cell = image.next_nudge_cell(
            judged,
            cells,
            witnesses=verdict.witnesses,
            undecided_mask=verdict.undecided_mask,
        )
        if cell is None:
            break
        cells.append(cell)
        judged = image.nudge(original, cells)
        grids.append(judged)
        verdict = _verdict(judged)
        if verdict.solution_count == 1:
            break
    return grids


def test_the_scripted_grids_are_what_the_ac_tests_assume() -> None:
    """Guard the fixtures: an AC test on a grid that is accidentally unique, or
    accidentally repairable, would pass while asserting nothing.

    Both facts come from the real solver, so this also states the arithmetic
    the cap tests rest on: six independent ambiguities, five permitted flips.
    """
    assert _solution_count(_ONE_SWITCH) == solver.MANY
    one_switch = _nudge_run(_ONE_SWITCH)
    assert len(one_switch) == 1
    assert _solution_count(one_switch[0]) == 1

    assert _solution_count(_SIX_SWITCHES) == solver.MANY
    six_switches = _nudge_run(_SIX_SWITCHES)
    assert len(six_switches) == MAX_NUDGE_ATTEMPTS
    assert all(_solution_count(grid) == solver.MANY for grid in six_switches)


# --------------------------------------------------------------------------
# Scripted sources and captured aggregates
# --------------------------------------------------------------------------


class _CountingSource:
    """A grid source that reports how many candidates were asked of it.

    Kept identical in spirit to ``tests/test_sourcing_image.py``'s: image mode
    must never ask for a second candidate, and the count is how that is
    observed. A nudge is not a second candidate — it is an edit to the first —
    so this stays at ``1`` however many nudges a run applies.
    """

    def __init__(self, grid: Grid) -> None:
        self.grid = grid
        self.candidates_requested = 0

    def __call__(self, *arguments: object) -> Grid:
        self.candidates_requested += 1
        return [row[:] for row in self.grid]


def _install_source(monkeypatch: pytest.MonkeyPatch, source: _CountingSource) -> None:
    monkeypatch.setattr(orchestrator.sourcing, "for_mode", lambda mode: source)


def _capture_puzzles(monkeypatch: pytest.MonkeyPatch) -> list[Puzzle]:
    """Collect every aggregate ``generate`` builds, for a run that raises.

    A failed run has no return value to read counters off, and INV-003 is a
    statement about the aggregate rather than about the message — so the
    aggregate is captured on its way out of the constructor.
    """
    built: list[Puzzle] = []
    real_puzzle = orchestrator.Puzzle

    def capturing(*args: object, **kwargs: object) -> Puzzle:
        puzzle = real_puzzle(*args, **kwargs)  # type: ignore[arg-type]
        built.append(puzzle)
        return puzzle

    monkeypatch.setattr(orchestrator, "Puzzle", capturing)
    return built


def _image_request(**overrides: object) -> GenerationRequest:
    fields: dict[str, object] = {
        "mode": "image",
        "image": WIDE,
        "width": 10,
        "height": 10,
        "seed": 1,
    }
    fields.update(overrides)
    return GenerationRequest(**fields)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# AC-034 — TestNudge_AttemptsBoundedRecovery (POL-002, FR-013)
# --------------------------------------------------------------------------


def test_nudge_attempts_bounded_recovery_repairs_an_ambiguous_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The criterion itself: a conversion that fails the uniqueness check, with
    attempts left under the cap, is nudged **automatically** and re-checked.

    "Automatically" is the load-bearing word — nothing is passed to ask for it,
    the run simply comes back with a puzzle — and the counter is the evidence
    that the puzzle came from the nudge path rather than from the conversion.
    """
    source = _CountingSource(_ONE_SWITCH)
    _install_source(monkeypatch, source)

    puzzle = generate(_image_request())

    assert puzzle.nudge.attempts == 1
    assert puzzle.ready_for_export is True
    assert puzzle.solution_count == 1


def test_nudge_attempts_bounded_recovery_edits_the_grid_and_not_the_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """What a nudge *is*: one flipped cell of the conversion already in hand.

    The source is asked for exactly one candidate — an uploaded image converts
    to the same grid every time, so a second request would be a wasted decode of
    the same file (CARD-015's reasoning, unchanged by this card) — and POL-001's
    and POL-004's counters stay at zero, because this is a third loop and not a
    re-use of theirs.
    """
    source = _CountingSource(_ONE_SWITCH)
    _install_source(monkeypatch, source)

    puzzle = generate(_image_request())

    assert source.candidates_requested == 1
    assert puzzle.regenerate.attempts == 0
    assert puzzle.resample.attempts == 0
    assert puzzle.grid is not None
    assert _differences(_ONE_SWITCH, puzzle.grid) == [(2, 2)]


def test_nudge_attempts_bounded_recovery_re_solves_every_nudged_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CON-005 and guardrail G-4: the verdict on a nudged grid is the solver's.

    The strongest thing this card has to prove. A loop that "recovered" by
    assuming a nudged grid must be unique would produce a puzzle with two
    solutions and satisfy every other assertion in this file — so the solver is
    wrapped and every call counted, and each call is checked to be about the
    clues of the grid the aggregate is holding at that moment.

    Six solves for the cap-reaching run: one for the conversion, one per nudge.
    """
    source = _CountingSource(_SIX_SWITCHES)
    _install_source(monkeypatch, source)
    # Replayed *before* the solver is wrapped: `_nudge_run` solves too, and its
    # solves are not the ones this test is counting.
    expected = [
        clues.compute_clues(_SIX_SWITCHES),
        *(clues.compute_clues(grid) for grid in _nudge_run(_SIX_SWITCHES)),
    ]
    real_solve = orchestrator.solver.solve
    solved: list[tuple[tuple[tuple[int, ...], ...], ...]] = []

    def recording(row_clues, column_clues, **kwargs):  # type: ignore[no-untyped-def]
        solved.append((row_clues, column_clues))
        return real_solve(row_clues, column_clues, **kwargs)

    monkeypatch.setattr(orchestrator.solver, "solve", recording)

    with pytest.raises(GenerationAbandoned):
        generate(_image_request())

    assert len(solved) == 1 + MAX_NUDGE_ATTEMPTS
    assert solved == [(each.rows, each.columns) for each in expected]


def test_nudge_attempts_bounded_recovery_keeps_the_clues_matching_the_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-001 across a nudge: the accepted puzzle's clues encode *its* grid.

    A nudged grid reaches the aggregate through the same
    ``record_candidate`` as any other candidate, so the clues cannot be the
    pre-nudge conversion's — but that is exactly the kind of thing an edit to
    the loop could break silently, and INV-001 is a system-contract entry.
    """
    _install_source(monkeypatch, _CountingSource(_ONE_SWITCH))

    puzzle = generate(_image_request())

    assert puzzle.grid is not None
    assert puzzle.clues == clues.compute_clues(puzzle.grid)


def test_nudge_attempts_bounded_recovery_on_a_real_image() -> None:
    """The same recovery with nothing scripted at all (a pinned case).

    ``owl1.png`` at 10x10 converts to a genuinely ambiguous grid that **one**
    nudge turns into a puzzle. One flipped pixel out of a hundred: the picture
    the user handed over is still their picture, which is the whole premise of
    nudging rather than re-drawing.

    Re-pinned from ``bands.png`` by CARD-070 — see the module docstring for why
    that fixture could never have produced a count at all — and re-taken by
    CARD-075 from a fresh 10..25 sweep, which is this module's own recipe. It
    was 2 under the 2x2 switching-block ranking and is 1 under the solver's
    disagreement set: the same conversion, one fewer pixel of the user's
    picture spent. The sweep's other sizes moved the same way (the cap was
    reached at 15x15 before this card and is now reached at 24x24), which is
    the whole of CARD-075's measured effect showing up in one fixture.
    """
    converted = image.generate(OWL, 10, 10, random.Random(1))

    puzzle = generate(
        GenerationRequest(mode="image", image=OWL, width=10, height=10, seed=1)
    )

    assert puzzle.nudge.attempts == 1
    assert puzzle.solution_count == 1
    assert puzzle.grid is not None
    assert len(_differences(converted, puzzle.grid)) == 1


# --------------------------------------------------------------------------
# AC-035 — TestNudge_ReportsFailureAtCap (INV-003, POL-003)
# --------------------------------------------------------------------------


def test_nudge_reports_failure_at_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """The criterion: at the cap the tool reports failure rather than returning
    a puzzle it never verified, and says how far it went."""
    _install_source(monkeypatch, _CountingSource(_SIX_SWITCHES))

    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(_image_request())

    message = str(excinfo.value)
    assert f"{MAX_NUDGE_ATTEMPTS} pixel-nudge attempts" in message
    assert f"bound: {MAX_NUDGE_ATTEMPTS}" in message


def test_nudge_reports_failure_at_cap_without_exceeding_the_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-003 read off the aggregate: the counter stops *at* the bound.

    ``RetryCounter`` refuses to advance past its bound, so the assertion that
    matters is the pair — exhausted, and exactly at five, not five-plus-one
    recorded by a loop that checked its condition one line too late.
    """
    built = _capture_puzzles(monkeypatch)
    _install_source(monkeypatch, _CountingSource(_SIX_SWITCHES))

    with pytest.raises(GenerationAbandoned):
        generate(_image_request())

    assert len(built) == 1
    assert built[0].nudge.attempts == MAX_NUDGE_ATTEMPTS
    assert built[0].nudge.exhausted is True
    assert built[0].ready_for_export is False


def test_nudge_reports_failure_at_cap_stops_altering_the_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POL-003 and guardrail G-3, as a count of edits rather than as a message.

    "Stops altering the image" is only observable from outside as *how many
    times the mechanism was invoked* — a loop with an unbounded "one more try"
    after the cap would still raise the same error. So the nudge function is
    wrapped: exactly five calls, with attempt numbers 1..5 and no sixth, and
    the grid source untouched throughout.
    """
    source = _CountingSource(_SIX_SWITCHES)
    _install_source(monkeypatch, source)
    real_nudge = orchestrator.image_source.nudge
    attempts: list[int] = []

    def recording(original: Grid, cells: list[tuple[int, int]]) -> Grid:
        # How many cells the call applies *is* the attempt number, since the
        # loop appends exactly one per round before nudging.
        attempts.append(len(cells))
        return real_nudge(original, cells)

    monkeypatch.setattr(orchestrator.image_source, "nudge", recording)

    with pytest.raises(GenerationAbandoned):
        generate(_image_request())

    assert attempts == list(range(1, MAX_NUDGE_ATTEMPTS + 1))
    assert source.candidates_requested == 1


def test_nudge_reports_failure_at_cap_when_there_is_nothing_left_to_add(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The other way POL-002's budget runs out, since CARD-075.

    An attempt can now fail to find a cell at all — both regions used up — and
    the card's rule is that this costs an attempt like any other: the counter
    has already advanced when the callable runs, so the loop still reaches the
    cap and still raises POL-003's report rather than ending quietly with no
    puzzle and no explanation. Driven by exhausting the mechanism outright,
    because a conversion that exhausts it naturally is a fixture nobody can
    pin: it depends on the solver's witnesses agreeing everywhere they are
    allowed to.

    The grid is never nudged in this run, and the solver is asked exactly once
    — for the conversion itself. Those are the other two assertions, and the
    second is the one with teeth: re-judging the unchanged grid on every empty
    attempt would raise the same error after the same five attempts while
    spending five solves to ask one question, which is precisely the
    degeneration the "still has candidates" rule was written against.
    """
    built = _capture_puzzles(monkeypatch)
    _install_source(monkeypatch, _CountingSource(_SIX_SWITCHES))
    monkeypatch.setattr(
        orchestrator.image_source,
        "next_nudge_cell",
        lambda *arguments, **keywords: None,
    )
    nudged: list[object] = []
    monkeypatch.setattr(
        orchestrator.image_source,
        "nudge",
        lambda *arguments: nudged.append(arguments),
    )
    real_solve = orchestrator.solver.solve
    solves = 0

    def counting(*arguments, **keywords):  # type: ignore[no-untyped-def]
        nonlocal solves
        solves += 1
        return real_solve(*arguments, **keywords)

    monkeypatch.setattr(orchestrator.solver, "solve", counting)

    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(_image_request())

    assert built[0].nudge.attempts == MAX_NUDGE_ATTEMPTS
    assert nudged == []
    assert solves == 1
    assert "pixel-nudge" in str(excinfo.value)
    assert built[0].grid == _SIX_SWITCHES


def test_nudge_reports_failure_at_cap_never_drifts_from_the_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The other half of "stops altering": *how much* was altered, at most.

    Every attempt nudges the original conversion rather than the previous
    attempt's grid, so the run's worst case is the conversion plus
    :data:`MAX_NUDGE_ATTEMPTS` pixels — a bound the user can reason about,
    instead of a five-step walk to somewhere unrelated to their picture.
    """
    built = _capture_puzzles(monkeypatch)
    _install_source(monkeypatch, _CountingSource(_SIX_SWITCHES))

    with pytest.raises(GenerationAbandoned):
        generate(_image_request())

    final = built[0].grid
    assert final is not None
    assert len(_differences(_SIX_SWITCHES, final)) == MAX_NUDGE_ATTEMPTS


def test_nudge_reports_failure_at_cap_on_a_real_image() -> None:
    """The cap reached by an actual picture rather than a scripted grid (a
    pinned case, re-pinned by sweeping the fixtures — see the module docstring).

    ``owl1.png`` at 24x24 converts to a grid that all five nudges leave
    ambiguous, which is the run AC-035 describes end to end. The same
    photograph at 10x10 is repaired in one (the test above), so the pair
    isolates the extent: what reaches the cap is the conversion, not the
    picture.

    Re-pinned from ``landscape.png`` at 22x22 by CARD-070, which found that
    fixture needs zero nudges at every size from 10 to 25 and always did — see
    the module docstring. CARD-075 moved it again, from 15x15 to 24x24, by the
    same 10..25 sweep: under the solver's disagreement set the picture now
    converts at every size up to 23, so 15x15 is no longer a failure to pin and
    asserting it there would have made this test vacuous rather than green.
    """
    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(
            GenerationRequest(mode="image", image=OWL, width=24, height=24, seed=1)
        )

    assert "pixel-nudge" in str(excinfo.value)


def test_nudge_reports_failure_at_cap_through_the_cli(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The user-visible end of the same run: a failure exit code, on stderr.

    ``GenerationAbandoned`` is mapped by COMP-001's one exit-code table, so this
    asserts the wiring rather than a second policy.

    ``24x24`` rather than a bare ``24`` since CARD-033: a bare N follows the
    source's own shape (FR-023), and ``owl1.png``'s 386x486 ink box would ask
    for a 19x24 — measured, that conversion *is* recovered, in five nudges, so
    it is emphatically not the pinned failure this test is the CLI end of.

    Re-pinned from ``landscape.png`` at 22x22 by CARD-070, alongside the test
    above and for the same reason — see the module docstring — and moved from
    15x15 to 24x24 by CARD-075 with the test above.
    """
    exit_code = cli.main(
        ["generate", "--mode", "image", "--image", str(OWL), "--size", "24x24"]
    )

    assert exit_code == cli.ExitCode.GENERATION_FAILED
    assert "uniquely-solvable" in capsys.readouterr().err


# --------------------------------------------------------------------------
# AC-036 — TestNudge_FailureMessageSuggestsRetry
# --------------------------------------------------------------------------


def test_nudge_failure_message_suggests_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The criterion: the cap message says to retry with a different image or a
    different size — the two levers that actually change the answer.

    ``--seed`` is checked *not* to be offered: the conversion ignores the RNG
    and so does the nudge, so re-seeding an image run reproduces the same grid
    and the same five edits, and suggesting it would send the user in a circle.
    """
    _install_source(monkeypatch, _CountingSource(_SIX_SWITCHES))

    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(_image_request())

    message = str(excinfo.value)
    assert "retry with a different image" in message
    assert "--size" in message
    assert "--seed" not in message


def test_nudge_failure_message_suggests_retry_says_it_has_stopped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-036 read together with AC-035: the message has to leave the user sure
    that the tool is finished with their file.

    Without it, "abandoned after 5 pixel-nudge attempts" is ambiguous between
    "gave up" and "still going" — and the fact that the picture itself was
    never re-drawn (only the converted grid was edited) is the thing a user of
    random mode would otherwise assume the opposite of.
    """
    _install_source(monkeypatch, _CountingSource(_SIX_SWITCHES))

    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(_image_request())

    message = str(excinfo.value)
    assert "stopped altering it" in message
    assert "never re-drawn" in message


def test_nudge_failure_message_suggests_retry_reaches_the_user(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-036 says "when the failure is presented to the user", so the advice is
    checked where the user reads it and not only where it is raised.

    ``10x10`` rather than a bare ``10`` since CARD-033. The *grid* source is
    scripted here, but the source's own shape is not — a bare N would ask
    ``sourcing.image.source_shape`` about ``wide.png``, whose 3:1 box is past
    the 2:1 ceiling a bare ``--size 10`` can reach, and the run would be refused
    before the scripted source ever ran (FR-023). Stating the extent keeps the
    subject of this test the nudge message.
    """
    _install_source(monkeypatch, _CountingSource(_SIX_SWITCHES))

    exit_code = cli.main(
        ["generate", "--mode", "image", "--image", str(WIDE), "--size", "10x10"]
    )

    assert exit_code == cli.ExitCode.GENERATION_FAILED
    assert "retry with a different image" in capsys.readouterr().err


# --------------------------------------------------------------------------
# G-2 — one bound, one counter, one home (INV-003)
# --------------------------------------------------------------------------


def test_the_nudge_bound_is_five_and_is_its_own_constant() -> None:
    """ADR-0002 gives the nudge a genuinely different cap, and guardrail G-2
    asks that it be a separate constant rather than an alias.

    The inequality is the assertion with teeth: a later retune that collapsed
    the two families into one number would license twenty edits to somebody's
    photograph, which is not what "20 attempts" was ever decided about.
    """
    assert MAX_NUDGE_ATTEMPTS == 5
    assert MAX_NUDGE_ATTEMPTS != MAX_RETRY_ATTEMPTS
    assert MAX_REGENERATE_ATTEMPTS == MAX_RESAMPLE_ATTEMPTS == MAX_RETRY_ATTEMPTS


def test_the_nudge_counter_is_a_retry_counter_like_the_other_two() -> None:
    """INV-003 has one home and one mechanism: the third loop is a third
    ``RetryCounter`` field on the aggregate, not a bespoke integer."""
    puzzle = Puzzle(request=_image_request(), seed=1)

    assert isinstance(puzzle.nudge, orchestrator.RetryCounter)
    assert (puzzle.nudge.kind, puzzle.nudge.bound) == ("pixel-nudge", MAX_NUDGE_ATTEMPTS)
    assert puzzle.nudge.attempts == 0


def test_the_image_module_counts_nothing_itself() -> None:
    """Guardrail G-2 as an API-surface pin on COMP-003.

    CARD-015's version of this test asserted that no nudge existed here at all;
    the mechanism has now landed, so what is pinned instead is the split. The
    nudge *takes* its attempt number, which means it cannot have an opinion
    about the bound — no counter, no cap and no loop on this side of the line.

    The list moves when COMP-003's public surface moves, which is the point of
    pinning it. CARD-030 (FR-022) added ``INK_THRESHOLD`` and
    ``ink_bounding_box`` and removed ``probe_extent`` — the pre-decode aspect
    probe, retired by ADR-0022's 2026-09-01 revision because an ink bounding
    box cannot be read from a file header. CARD-033 (FR-023) added
    ``source_shape``, which reports the ink box's extent so a bare ``--size N``
    can be completed from it — and which, like ``nudge``, decides nothing and
    counts nothing.

    CARD-075 replaced ``nudge_cells`` with ``next_nudge_cell``, and the
    signatures are the interesting half of that. The old pair took an *attempt
    number* — the one place COMP-003 came close to knowing about the loop — and
    the new pair does not: ``next_nudge_cell`` is handed the cells already
    flipped and returns one more, ``nudge`` is handed cells and applies them.
    Neither can tell which attempt it is on or how many are left, which is
    INV-003's single home stated as an API rather than as a comment.

    CARD-079 added the binarisation vocabulary — two path names, the mid-tone
    band and its threshold, the pinned default, and the three functions that
    read them. None of them counts anything either: the classifier is a pure
    function of a picture, and ``DEFAULT_BINARISATION`` is a policy constant
    rather than a tally.
    """
    assert image.__all__ == [
        "DEFAULT_BINARISATION",
        "DITHER",
        "INK_THRESHOLD",
        "MIDTONE_BAND",
        "MIDTONE_SHARE_THRESHOLD",
        "RESAMPLING",
        "THRESHOLD",
        "binarisation_for",
        "binarize",
        "classify_binarisation",
        "fit_crop_box",
        "generate",
        "ink_bounding_box",
        "load_greyscale",
        "midtone_share",
        "next_nudge_cell",
        "nudge",
        "source_shape",
        "to_grid",
        "validate_aspect_ratio",
    ]
    assert not hasattr(image, "RetryCounter")
    assert not any(
        name.startswith("MAX_") or "attempts" in name.lower() for name in vars(image)
    )
    assert list(inspect.signature(image.next_nudge_cell).parameters) == [
        "grid",
        "flipped",
        "witnesses",
        "undecided_mask",
    ]
    assert list(inspect.signature(image.nudge).parameters) == ["original", "cells"]


# --------------------------------------------------------------------------
# What is deliberately *not* nudged
# --------------------------------------------------------------------------


def test_a_unique_conversion_is_never_nudged() -> None:
    """The loop is entered only by the branch that needs it: a conversion that
    passes the uniqueness check first time leaves the counter at zero, so
    CARD-017 can report "0 nudges" as a fact rather than as a default."""
    puzzle = generate(
        GenerationRequest(mode="image", image=LANDSCAPE, width=20, height=20, seed=1)
    )

    assert puzzle.nudge.attempts == 0
    assert puzzle.ready_for_export is True


def test_a_tier_miss_is_not_nudged(monkeypatch: pytest.MonkeyPatch) -> None:
    """POL-002 is a uniqueness remedy, not a difficulty dial.

    A conversion that *is* uniquely solvable but scores outside the requested
    band ends the run the way CARD-015 left it — nudging cells until the score
    drifts into a tier would be POL-004 by other means, and would alter the
    user's picture for a reason FR-013 never gave.
    """
    built = _capture_puzzles(monkeypatch)

    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(
            GenerationRequest(
                mode="image", image=LANDSCAPE, width=20, height=20, seed=1, difficulty="hard"
            )
        )

    assert built[0].nudge.attempts == 0
    assert "Hard band" in str(excinfo.value)


@pytest.mark.parametrize(
    "request_",
    [
        pytest.param(
            GenerationRequest(mode="random", width=10, height=10, density=40, seed=7),
            id="random",
        ),
        pytest.param(
            GenerationRequest(mode="library", library_key="cat", width=15, height=15, seed=7),
            id="library",
        ),
    ],
)
def test_the_other_modes_never_nudge(request_: GenerationRequest) -> None:
    """Guardrail G-1 as a behaviour: a source that *can* be re-drawn keeps
    POL-001, and gains nothing here. The nudge counter is image mode's alone."""
    puzzle = generate(request_)

    assert puzzle.nudge.attempts == 0


# --------------------------------------------------------------------------
# COMP-003 — the mechanism's contract (next_nudge_cell and nudge)
# --------------------------------------------------------------------------
#
# CARD-075 replaced the 2x2 switching-block ranking with the solver's own
# report. The two functions split the mechanism in half: :func:`next_nudge_cell`
# decides *which* cell the next attempt adds, and :func:`nudge` applies a set of
# cells to the original conversion. Neither counts anything (INV-003) and
# neither reads a clock or an rng (ADR-0015).


def _disagreeing_cells(witnesses: tuple[Grid, ...]) -> set[tuple[int, int]]:
    """Where the two witnesses differ — the test's own second implementation."""
    first, second = witnesses[0], witnesses[1]
    return {
        (row, column)
        for row, (first_row, second_row) in enumerate(zip(first, second, strict=True))
        for column, (left, right) in enumerate(
            zip(first_row, second_row, strict=True)
        )
        if left != right
    }


def _mask_of(size: int, cells: tuple[tuple[int, int], ...]) -> list[list[bool]]:
    """A grid-shaped undecided mask holding exactly ``cells``."""
    mask = [[False] * size for _ in range(size)]
    for row, column in cells:
        mask[row][column] = True
    return mask


# --------------------------------------------------------------------------
# AC-115 — TestNudge_AddsACellWhereTheWitnessesDisagree
# --------------------------------------------------------------------------


def test_nudge_adds_a_cell_where_the_witnesses_disagree() -> None:
    """The primary source of cells, from the solver rather than from a guess.

    CARD-096 measured the alternative: on the original conversion of every
    abandoned picture the two witnesses disagreed on 4 cells in 27 of 34 cases,
    while the undecided mask covered a median 35% of the grid. Ranking inside a
    mask that size is guessing again; the disagreement set *is* the ambiguity.
    """
    verdict = _verdict(_ONE_SWITCH)
    disagreeing = _disagreeing_cells(verdict.witnesses)

    cell = image.next_nudge_cell(
        _ONE_SWITCH,
        (),
        witnesses=verdict.witnesses,
        undecided_mask=verdict.undecided_mask,
    )

    assert disagreeing  # the fixture really is ambiguous (guarded above too)
    assert cell in disagreeing


def test_nudge_never_adds_a_cell_it_has_already_flipped() -> None:
    """``flipped`` is subtracted from the candidates, which is what makes the
    attempts nest: a cell already changed from the original can never be
    offered again, so no later attempt can undo an earlier one (EC-014)."""
    verdict = _verdict(_ONE_SWITCH)
    disagreeing = sorted(_disagreeing_cells(verdict.witnesses))

    for taken in range(1, len(disagreeing)):
        already = disagreeing[:taken]
        cell = image.next_nudge_cell(
            _ONE_SWITCH,
            already,
            witnesses=verdict.witnesses,
            undecided_mask=verdict.undecided_mask,
        )
        assert cell not in already
        assert cell in set(disagreeing) - set(already)


# --------------------------------------------------------------------------
# AC-116 — TestNudge_FallsBackToTheMaskThenStops / PrefersCellsNearestInkBoundary
# --------------------------------------------------------------------------


def test_nudge_falls_back_to_the_mask_then_stops() -> None:
    """Two rules in one walk, mirroring ``orchestrator.repair_candidate``.

    The disagreement set is preferred; the undecided mask is the fallback and
    is a live path, not a defensive branch (a solve that reported ``MANY`` has
    witnesses, but a run can exhaust their disagreement long before the cap).
    When neither holds an unflipped cell there is nothing to add, and saying so
    is how the attempt returns no candidate while the counter still advances.
    """
    grid = [[False] * 6 for _ in range(6)]
    mask = _mask_of(6, ((0, 0), (5, 5)))

    from_mask = image.next_nudge_cell(
        grid, (), witnesses=None, undecided_mask=mask
    )
    assert from_mask in {(0, 0), (5, 5)}

    exhausted = image.next_nudge_cell(
        grid, ((0, 0), (5, 5)), witnesses=None, undecided_mask=mask
    )
    assert exhausted is None

    assert image.next_nudge_cell(grid, (), witnesses=None, undecided_mask=None) is None


def test_nudge_falls_back_only_once_the_disagreement_set_is_used_up() -> None:
    """Ordering between the two sources, pinned on a case where they differ."""
    grid = [[False] * 6 for _ in range(6)]
    witnesses = ([row[:] for row in grid], [row[:] for row in grid])
    witnesses[1][2][2] = True
    mask = _mask_of(6, ((0, 0), (2, 2)))

    assert image.next_nudge_cell(
        grid, (), witnesses=witnesses, undecided_mask=mask
    ) == (2, 2)
    assert image.next_nudge_cell(
        grid, ((2, 2),), witnesses=witnesses, undecided_mask=mask
    ) == (0, 0)


def test_nudge_prefers_cells_nearest_the_ink_boundary() -> None:
    """The ranking inside whichever source supplied the candidates.

    A flip buried in a solid expanse splits a run in two or plants a stray dot
    — it changes the picture more than it changes the puzzle. A flip on the
    edge of the ink moves a boundary the clues are already arguing about. The
    distance is Chebyshev to the nearest differently-valued cell, so "on the
    boundary" is 1 and the middle of a blank corner is far.
    """
    grid = [[False] * 9 for _ in range(9)]
    for row in range(4, 7):
        for column in range(4, 7):
            grid[row][column] = True
    mask = _mask_of(9, ((0, 0), (3, 3)))

    assert image.next_nudge_cell(
        grid, (), witnesses=None, undecided_mask=mask
    ) == (3, 3)


def test_nudge_breaks_a_boundary_tie_by_row_then_column() -> None:
    """Full determinism: equal distance falls to reading order, so the same
    picture nudges the same way on every machine and in every run."""
    grid = [[False] * 9 for _ in range(9)]
    for row in range(4, 7):
        for column in range(4, 7):
            grid[row][column] = True
    mask = _mask_of(9, ((3, 5), (3, 3), (5, 3)))

    assert image.next_nudge_cell(
        grid, (), witnesses=None, undecided_mask=mask
    ) == (3, 3)


def test_nudge_still_chooses_when_no_cell_has_a_differing_neighbour() -> None:
    """A featureless conversion has no ink boundary at all, so every candidate
    scores the same distance and the tie-break carries the whole choice. The
    alternative — returning nothing — would spend the budget on one question."""
    blank = [[False] * 8 for _ in range(8)]
    mask = _mask_of(8, ((6, 6), (1, 4)))

    assert image.next_nudge_cell(
        blank, (), witnesses=None, undecided_mask=mask
    ) == (1, 4)


def test_next_nudge_cell_is_pure() -> None:
    """No rng, no clock, no mutation of anything handed in (ADR-0015, G-2)."""
    verdict = _verdict(_ONE_SWITCH)
    original = [row[:] for row in _ONE_SWITCH]
    flipped = [(2, 2)]

    first = image.next_nudge_cell(
        _ONE_SWITCH,
        flipped,
        witnesses=verdict.witnesses,
        undecided_mask=verdict.undecided_mask,
    )
    second = image.next_nudge_cell(
        _ONE_SWITCH,
        flipped,
        witnesses=verdict.witnesses,
        undecided_mask=verdict.undecided_mask,
    )

    assert first == second
    assert _ONE_SWITCH == original
    assert flipped == [(2, 2)]


# --------------------------------------------------------------------------
# sourcing.image.nudge — applying a set of cells to the original conversion
# --------------------------------------------------------------------------


def test_nudge_flips_exactly_the_cells_it_is_given() -> None:
    """The whole of what ``nudge`` decides, which is nothing: the caller passes
    attempt *n − 1*'s cells plus one, and nesting follows from that."""
    cells = ((1, 1), (5, 9), (9, 5))

    for length in range(len(cells) + 1):
        nudged = image.nudge(_SIX_SWITCHES, cells[:length])
        assert set(_differences(_SIX_SWITCHES, nudged)) == set(cells[:length])


def test_nudge_is_deterministic_and_does_not_mutate_its_argument() -> None:
    """A nudge draws from no RNG and edits no caller's grid.

    Determinism is what keeps an image run reproducible without a seed (there
    is nothing random left in the mode at all), and the copy is what lets the
    loop hand the same conversion to all five attempts.
    """
    original = [row[:] for row in _ONE_SWITCH]

    first = image.nudge(_ONE_SWITCH, ((2, 2), (3, 3)))
    second = image.nudge(_ONE_SWITCH, ((2, 2), (3, 3)))

    assert first == second
    assert first is not second
    assert _ONE_SWITCH == original


def test_nudge_preserves_the_grid_shape_and_the_boundary_type() -> None:
    """ADR-0012: what comes back is the same boundary representation, same
    dimensions, plain ``bool`` — the clue derivation must not be able to tell a
    nudged grid from a converted one by its type."""
    nudged = image.nudge(_SIX_SWITCHES, ((0, 0), (4, 4)))

    assert len(nudged) == len(_SIX_SWITCHES)
    assert {len(row) for row in nudged} == {len(_SIX_SWITCHES[0])}
    assert all(type(cell) is bool for row in nudged for cell in row)


def test_nudge_rejects_a_repeated_cell() -> None:
    """Flipping one cell twice would return it to its original value, which
    would break the "attempt *n* differs from the picture in exactly *n* cells"
    promise silently. A wiring bug in the caller, so a plain ``ValueError``."""
    with pytest.raises(ValueError, match="twice"):
        image.nudge(_ONE_SWITCH, ((2, 2), (2, 2)))


def test_nudge_rejects_a_cell_outside_the_grid() -> None:
    """The same reasoning, for a cell the conversion does not have."""
    with pytest.raises(ValueError, match="outside"):
        image.nudge(_ONE_SWITCH, ((0, 99),))


def test_nudge_of_no_cells_is_the_conversion_itself() -> None:
    """The degenerate end of the contract: the zeroth attempt's grid."""
    assert image.nudge(_ONE_SWITCH, ()) == _ONE_SWITCH
