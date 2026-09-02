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
works on an actual picture. ``bands.png`` at 10x10 really does convert to an
ambiguous grid that two nudges repair, and ``landscape.png`` at 22x22 really
does survive all five. Both are *pinned cases* in the sense
``tests/test_sourcing_image.py`` uses the phrase: if the dither, the solver or
the heuristic changes such that these sizes behave differently, re-pin them by
re-running a 10..25 sweep over the fixtures rather than deleting the test.
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
BANDS = FIXTURES / "bands.png"
WIDE = FIXTURES / "wide.png"
#: CARD-026 re-pinned the two real-image cases below onto this fixture.
#: ``wide.png`` is 60x20, a 3:1 source, and FR-021 now *refuses* it against a
#: square grid — it keeps only 33% of the picture — so it can no longer be
#: converted at 20x20 or 22x22 at all. ``landscape.png`` is 60x40, a 3:2 source
#: that keeps 67% and is comfortably inside the accepted band; a fresh 10..25
#: sweep (the module docstring's own re-pinning recipe) picked the same two
#: sizes, which is a coincidence worth naming rather than relying on.
LANDSCAPE = FIXTURES / "landscape.png"

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


def _differences(left: Grid, right: Grid) -> list[tuple[int, int]]:
    """Every cell where two same-shaped grids disagree, in row-major order."""
    return [
        (row, column)
        for row, (left_row, right_row) in enumerate(zip(left, right, strict=True))
        for column, (a, b) in enumerate(zip(left_row, right_row, strict=True))
        if a != b
    ]


def test_the_scripted_grids_are_what_the_ac_tests_assume() -> None:
    """Guard the fixtures: an AC test on a grid that is accidentally unique, or
    accidentally repairable, would pass while asserting nothing.

    Both facts come from the real solver, so this also states the arithmetic
    the cap tests rest on: six independent ambiguities, five permitted flips.
    """
    assert _solution_count(_ONE_SWITCH) == solver.MANY
    assert _solution_count(image.nudge(_ONE_SWITCH, 1)) == 1

    assert _solution_count(_SIX_SWITCHES) == solver.MANY
    assert all(
        _solution_count(image.nudge(_SIX_SWITCHES, attempt)) == solver.MANY
        for attempt in range(1, MAX_NUDGE_ATTEMPTS + 1)
    )


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
    assert _differences(_ONE_SWITCH, puzzle.grid) == [(3, 3)]


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
    real_solve = orchestrator.solver.solve
    solved: list[tuple[tuple[tuple[int, ...], ...], ...]] = []

    def recording(row_clues, column_clues, **kwargs):  # type: ignore[no-untyped-def]
        solved.append((row_clues, column_clues))
        return real_solve(row_clues, column_clues, **kwargs)

    monkeypatch.setattr(orchestrator.solver, "solve", recording)

    with pytest.raises(GenerationAbandoned):
        generate(_image_request())

    assert len(solved) == 1 + MAX_NUDGE_ATTEMPTS
    expected = [
        clues.compute_clues(_SIX_SWITCHES),
        *(
            clues.compute_clues(image.nudge(_SIX_SWITCHES, attempt))
            for attempt in range(1, MAX_NUDGE_ATTEMPTS + 1)
        ),
    ]
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

    ``bands.png`` at 10x10 was CARD-015's example of a genuinely ambiguous
    conversion — it is the run that card had ending in a failure — and two
    nudges now turn it into a puzzle. Two flipped pixels out of a hundred: the
    picture the user handed over is still their picture, which is the whole
    premise of nudging rather than re-drawing.
    """
    converted = image.generate(BANDS, 10, 10, random.Random(1))

    puzzle = generate(
        GenerationRequest(mode="image", image=BANDS, width=10, height=10, seed=1)
    )

    assert puzzle.nudge.attempts == 2
    assert puzzle.solution_count == 1
    assert puzzle.grid is not None
    assert len(_differences(converted, puzzle.grid)) == 2


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

    def recording(grid: Grid, attempt_number: int) -> Grid:
        attempts.append(attempt_number)
        return real_nudge(grid, attempt_number)

    monkeypatch.setattr(orchestrator.image_source, "nudge", recording)

    with pytest.raises(GenerationAbandoned):
        generate(_image_request())

    assert attempts == list(range(1, MAX_NUDGE_ATTEMPTS + 1))
    assert source.candidates_requested == 1


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

    ``landscape.png`` at 22x22 converts to a grid that all five nudges leave
    ambiguous, which is the run AC-035 describes end to end.
    """
    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(
            GenerationRequest(mode="image", image=LANDSCAPE, width=22, height=22, seed=1)
        )

    assert "pixel-nudge" in str(excinfo.value)


def test_nudge_reports_failure_at_cap_through_the_cli(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The user-visible end of the same run: a failure exit code, on stderr.

    ``GenerationAbandoned`` is mapped by COMP-001's one exit-code table, so this
    asserts the wiring rather than a second policy.
    """
    exit_code = cli.main(
        ["generate", "--mode", "image", "--image", str(LANDSCAPE), "--size", "22"]
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
    checked where the user reads it and not only where it is raised."""
    _install_source(monkeypatch, _CountingSource(_SIX_SWITCHES))

    exit_code = cli.main(
        ["generate", "--mode", "image", "--image", str(WIDE), "--size", "10"]
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
    """
    assert image.__all__ == [
        "RESAMPLING",
        "binarize",
        "fit_crop_box",
        "generate",
        "load_greyscale",
        "nudge",
        "nudge_cells",
        "probe_extent",
        "to_grid",
        "validate_aspect_ratio",
    ]
    assert not hasattr(image, "RetryCounter")
    assert not any(
        name.startswith("MAX_") or "attempts" in name.lower() for name in vars(image)
    )
    assert list(inspect.signature(image.nudge).parameters) == [
        "grid",
        "attempt_number",
    ]


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
# COMP-003 — the mechanism's contract (sourcing.image.nudge)
# --------------------------------------------------------------------------


def test_nudge_flips_exactly_one_cell_per_attempt() -> None:
    """The unit of a nudge, for every attempt number up to the cap."""
    for attempt in range(1, MAX_NUDGE_ATTEMPTS + 1):
        assert len(_differences(_SIX_SWITCHES, image.nudge(_SIX_SWITCHES, attempt))) == (
            attempt
        )


def test_nudge_attempts_nest_so_no_edit_is_ever_undone() -> None:
    """Attempt ``n`` is attempt ``n - 1`` plus one more flip.

    The property the orchestrator's loop depends on: because every round nudges
    the *conversion* rather than the previous round's grid, a later nudge must
    not be able to revert an earlier one — otherwise a five-attempt budget
    degenerates into an oscillation between two grids.
    """
    for attempt in range(2, MAX_NUDGE_ATTEMPTS + 1):
        earlier = set(
            _differences(_SIX_SWITCHES, image.nudge(_SIX_SWITCHES, attempt - 1))
        )
        later = set(_differences(_SIX_SWITCHES, image.nudge(_SIX_SWITCHES, attempt)))
        assert earlier < later
        assert len(later) == len(earlier) + 1


def test_nudge_is_deterministic_and_does_not_mutate_its_argument() -> None:
    """A nudge draws from no RNG and edits no caller's grid.

    Determinism is what keeps an image run reproducible without a seed (there
    is nothing random left in the mode at all), and the copy is what lets the
    loop hand the same conversion to all five attempts.
    """
    original = [row[:] for row in _ONE_SWITCH]

    first = image.nudge(_ONE_SWITCH, 3)
    second = image.nudge(_ONE_SWITCH, 3)

    assert first == second
    assert first is not second
    assert _ONE_SWITCH == original


def test_nudge_preserves_the_grid_shape_and_the_boundary_type() -> None:
    """ADR-0012: what comes back is the same boundary representation, same
    dimensions, plain ``bool`` — the clue derivation must not be able to tell a
    nudged grid from a converted one by its type."""
    nudged = image.nudge(_SIX_SWITCHES, 4)

    assert len(nudged) == len(_SIX_SWITCHES)
    assert {len(row) for row in nudged} == {len(_SIX_SWITCHES[0])}
    assert all(type(cell) is bool for row in nudged for cell in row)


def test_nudge_rejects_an_attempt_number_below_one() -> None:
    """A nudge is an attempt that has already been counted, so a zeroth one is
    a wiring bug in the caller — a plain ``ValueError``, not a domain error the
    CLI would map to an exit code."""
    with pytest.raises(ValueError, match="start at 1"):
        image.nudge(_ONE_SWITCH, 0)


def test_nudge_prefers_a_cell_inside_a_switching_block() -> None:
    """The heuristic's primary signal, isolated.

    A grid with one diagonal pair and one large solid block: the flip must land
    on the pair, which is where the ambiguity is, and not in the middle of the
    block, which is merely the biggest thing in the picture.
    """
    grid = [[False] * 12 for _ in range(12)]
    for row in range(7, 11):
        for column in range(7, 11):
            grid[row][column] = True
    grid[1][1] = grid[2][2] = True

    assert image.nudge_cells(grid, 1)[0] in {(1, 1), (1, 2), (2, 1), (2, 2)}


def test_nudge_spaces_its_flips_apart() -> None:
    """Why the ranking is not simply "the top n cells".

    All four cells of a switching block score identically, so an unspaced
    top-``n`` would spend the whole budget inside one block — and flipping both
    cells of a diagonal pair just produces the other diagonal, which is the
    same ambiguity again. Every pair of chosen cells is therefore at least two
    apart.
    """
    chosen = image.nudge_cells(_SIX_SWITCHES, MAX_NUDGE_ATTEMPTS)

    assert len(set(chosen)) == MAX_NUDGE_ATTEMPTS
    assert all(
        max(abs(a[0] - b[0]), abs(a[1] - b[1])) > 1
        for index, a in enumerate(chosen)
        for b in chosen[index + 1 :]
    )


def test_nudge_still_has_candidates_for_a_featureless_conversion() -> None:
    """A blank or solid conversion fires neither signal, and must still yield a
    full supply of distinct cells — otherwise the loop would re-check the same
    grid five times and burn the budget on one question.

    The fallback order is centre-outward, which is where a picture's subject
    would have been had there been one.
    """
    blank = [[False] * 10 for _ in range(10)]

    chosen = image.nudge_cells(blank, MAX_NUDGE_ATTEMPTS)

    assert len(set(chosen)) == MAX_NUDGE_ATTEMPTS
    assert chosen[0] in {(4, 4), (4, 5), (5, 4), (5, 5)}


def test_nudge_cells_asked_for_none_returns_none() -> None:
    """The degenerate end of the ranking's contract, since ``run_bounded``'s
    counter starts at zero and a future caller could ask."""
    assert image.nudge_cells(_ONE_SWITCH, 0) == ()
