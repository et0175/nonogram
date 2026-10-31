import io, sys
from pathlib import Path

target = Path("tests/test_solver_strategies.py")
src = target.read_text()

def swap(old: str, new: str, label: str) -> None:
    global src
    n = src.count(old)
    assert n == 1, f"{label}: expected 1 occurrence, found {n}"
    src = src.replace(old, new)
    print("ok:", label)


# ---- 1. the independent derivation helper, beside _strategies_of ----------
swap(
    '''class _DilatedClock:''',
    '''def _strategies_from_grid(grid: list[list[bool]]) -> tuple[str, ...]:
    """FR-029's list for ``grid``, re-derived here from the grid alone.

    AC-139's expected value is built in the test tree and never fetched from
    the admin path under test (G-5): the clues are recomputed from the stored
    grid, the grid is solved again, and :func:`_strategies_of` states FR-029's
    rule natively. Measured while writing this test, over 250 candidates
    across both call sites and four extents, it reproduced the list the
    generator handed over every time.
    """
    return _strategies_of(_solve(grid))


class _DilatedClock:''',
    "helper _strategies_from_grid",
)

# ---- 2. class docstring: say what is asserted ----------------------------
swap(
    '''    Why the stored row is not enough, measured
    -----------------------------------------
    ``add_puzzle`` **derives** the list from its own uniqueness proof whenever
    the caller hands it an empty one. So a generator that passed ``[]`` still
    produces rows whose column holds a real non-empty list, and a row-only
    assertion cannot tell the two apart: mutants that replaced both call sites'
    ``list(puzzle.strategies)`` with ``[]`` left an all-row check **green**.
    The AC's words are "that puzzle's real ... list", so what has to be
    observed is the value the *generator handed over*, and both tests below
    spy on the hand-off as well as reading the row back.
    """
''',
    '''    What is asserted: identity, on two arms
    ---------------------------------------
    Every stored row's list, and every list the generator handed
    ``add_puzzle``, is asserted **equal** to
    :func:`_strategies_from_grid` of that puzzle's own grid — not merely
    non-empty and not merely inside ``STRATEGY_NAMES``. The expectation is an
    independent re-derivation in the test tree (G-5); nothing is read back
    from the code under test to build it.

    Both arms are here because each is blind to what the other sees, and both
    blindnesses were measured rather than argued:

    * the **row** arm is the AC's own sentence, and it cannot see an empty
      hand-off at all — ``add_puzzle`` **derives** the list from its own
      uniqueness proof whenever its caller hands it an empty one, so the row
      holds a real list while the caller is wrong. Mutants replacing both call
      sites' ``list(puzzle.strategies)`` with ``[]`` left an all-row check
      green (CARD-318's M6/M9).
    * the **hand-off** arm sees that, and *with identity* it also sees a
      hand-off that is non-empty, in-vocabulary and wrong. The predicate this
      class carried before — truthy and a subset of ``STRATEGY_NAMES`` — did
      not: a hardcoded ``['simple_overlap']`` passed it at both call sites
      (cycle 1's R3/R4).

    Measured, per assertion: ``strategies_used=[]`` planted at either call
    site reds the hand-off arm; ``strategies_used=['simple_overlap']`` planted
    at either reds the identity arm. CARD-318's mutant table (R1-R4) names
    which assertion fired for which plant.

    The two corpora differ in what guarantees the identity assertion can
    discriminate a constant, and say so where they are built: the image half
    is deterministic and carries two ladders that differ, so no constant can
    satisfy it; the random half runs on an RNG that cannot be seeded from
    outside, so its non-degeneracy is **asserted** rather than arranged.
    """
''',
    "class docstring",
)

# ---- 3. the extent constant + SAMPLE ------------------------------------
swap(
    '''    SAMPLE = ["LineLogic", "ConstraintProp"]
''',
    '''    SAMPLE = ["LineLogic", "ConstraintProp"]

    #: The extent the random batch is generated at. ``MIN_SIZE`` will not do:
    #: measured, every 10x10 random candidate solves with the single rung
    #: ``('simple_overlap',)`` (10 of 10 in one batch, 8 of 8 across seeds), so
    #: there the truth *is* the constant R3 plants and the identity assertion
    #: below could not discriminate it. At 20x20, density 50 — the density
    #: ``orchestrator.generate_batch`` uses for every random candidate, not a
    #: number chosen here — 134 of 160 measured candidates carry a longer
    #: ladder, nothing was abandoned or timed out in 160, and a batch of ten
    #: costs 0.3-0.7s.
    LADDER_EXTENT = 20

    #: The pictures the image half is driven with. Two, and these two: the
    #: image path draws nothing from the RNG (``orchestrator`` notes the
    #: conversion and the nudge are RNG-free), so each picture's ladder is
    #: fixed, and these two are measured to differ — ``bird1.jpg`` solves with
    #: ``('simple_overlap',)`` and ``bird2.jpg`` with ``('simple_overlap',
    #: 'line_dp', 'probe_contradiction')``, identical on repeated runs. Two
    #: ladders that differ is what makes *every* constant fail the identity
    #: assertion here, which the random half can only make overwhelmingly
    #: likely.
    IMAGES = ("bird1.jpg", "bird2.jpg")
''',
    "LADDER_EXTENT + IMAGES",
)

# ---- 4. the spy records the grid beside the list -------------------------
swap(
    '''    @staticmethod
    def _spy_on(service: PuzzleReviewService) -> list[object]:
        """Record the ``strategies_used`` every ``add_puzzle`` call is given.

        The store's fallback is a genuine safety net and is not being removed;
        it just has to stop hiding its callers.
        """
        handed_over: list[object] = []
        real = service.add_puzzle

        def spying(*args: object, **kwargs: object):
            handed_over.append(kwargs.get("strategies_used"))
            return real(*args, **kwargs)  # type: ignore[arg-type]

        service.add_puzzle = spying  # type: ignore[method-assign]
        return handed_over

    def _assert_row_is_a_real_list(self, row: dict) -> None:
        names = row["strategies_used"]
        assert names, row["id"]
        assert names != self.SAMPLE, row["id"]
        assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names
''',
    '''    @staticmethod
    def _spy_on(service: PuzzleReviewService) -> list[tuple[list, list]]:
        """Record the ``(grid, strategies_used)`` every ``add_puzzle`` is given.

        The grid is recorded beside the list because it is what makes the
        expectation independent: the puzzle the caller is handing over is
        identified by its own grid, so the list it *should* have handed over
        can be re-derived without asking the caller anything.

        The store's fallback is a genuine safety net and is not being removed;
        it just has to stop hiding its callers.
        """
        handed_over: list[tuple[list, list]] = []
        real = service.add_puzzle

        def spying(*args: object, **kwargs: object):
            handed_over.append((kwargs.get("grid"), kwargs.get("strategies_used")))
            return real(*args, **kwargs)  # type: ignore[arg-type]

        service.add_puzzle = spying  # type: ignore[method-assign]
        return handed_over

    def _assert_row_is_a_real_list(self, row: dict) -> None:
        """The AC's sentence, on the row: *that puzzle's* real non-empty list.

        The identity assertion is the last one and the one that carries the
        criterion; the three before it are kept because they name the two
        specific wrong values the AC calls out (``[]`` and ``SAMPLE``) and
        because a vocabulary failure and an identity failure are different
        defects.
        """
        names = row["strategies_used"]
        assert names, row["id"]
        assert names != self.SAMPLE, row["id"]
        assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names
        assert tuple(names) == _strategies_from_grid(row["grid"]), row["id"]

    def _assert_hand_off_is_that_puzzles_list(
        self, handed_over: list[tuple[list, list]]
    ) -> None:
        """The same sentence, on the value the generator handed the store.

        Two assertions, in this order and for different mutants: the first
        catches an empty hand-off the row arm cannot see (R1/R2), the second
        catches a hand-off that is non-empty, in-vocabulary and not this
        puzzle's (R3/R4).
        """
        for grid, names in handed_over:
            assert names, "the caller handed the store an empty list"
            assert tuple(names) == _strategies_from_grid(grid), names
''',
    "spy + row/hand-off assertions",
)

# ---- 5. the random test -------------------------------------------------
swap(
    '''        # Ten is the smallest random batch the admin accepts (CARD-094).
        generator.create_batch(count=10, sizes=[MIN_SIZE], source="random")
        stored = list(store.puzzles.values())

        assert len(stored) == 10, len(stored)
        for row in stored:
            self._assert_row_is_a_real_list(row)

        # The generator's own contribution, not the store's fallback.
        assert len(handed_over) == 10, handed_over
        for names in handed_over:
            assert names, "the batch generator handed the store an empty list"
            assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names
''',
    '''        # Ten is the smallest random batch the admin accepts (CARD-094).
        generator.create_batch(count=10, sizes=[self.LADDER_EXTENT], source="random")
        stored = list(store.puzzles.values())

        assert len(stored) == 10, len(stored)
        for row in stored:
            self._assert_row_is_a_real_list(row)

        # The generator's own contribution, not the store's fallback.
        assert len(handed_over) == 10, handed_over
        for _grid, names in handed_over:
            assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names
        self._assert_hand_off_is_that_puzzles_list(handed_over)

        # The floor that keeps the identity assertion above able to
        # discriminate (ADR-0039/R1): in a corpus where every ladder is the
        # single rung ('simple_overlap',), that constant and the truth are the
        # same value. This batch's RNG cannot be seeded from outside —
        # orchestrator.generate draws its seed from secrets.randbits and
        # generate_batch builds an unseeded random.Random — so the property is
        # asserted here rather than arranged, the way this suite's other
        # corpora assert their per-arm floors. At the measured single-rung rate
        # for this extent (26 of 160 candidates) ten draws miss it with
        # probability ~1e-8; if it ever fires, the batch is degenerate and the
        # identity assertion has stopped meaning anything, which is exactly
        # what a reader needs told.
        assert any(len(names) > 1 for _grid, names in handed_over), handed_over
''',
    "random test body",
)

# ---- 6. the image test --------------------------------------------------
swap(
    '''        handed_over = self._spy_on(admin_app.puzzle_review_service)
        client = admin_app.test_client()
        with open(FIXTURES / "bird1.jpg", "rb") as handle:
            upload = client.post(
                "/batch/from-images",
                data={"image_files": [(handle, "bird1.jpg")]},
                content_type="multipart/form-data",
            )
        assert upload.status_code == 302, upload.data
''',
    '''        handed_over = self._spy_on(admin_app.puzzle_review_service)
        client = admin_app.test_client()
        with contextlib.ExitStack() as handles:
            upload = client.post(
                "/batch/from-images",
                data={
                    "image_files": [
                        (handles.enter_context(open(FIXTURES / name, "rb")), name)
                        for name in self.IMAGES
                    ]
                },
                content_type="multipart/form-data",
            )
        assert upload.status_code == 302, upload.data
''',
    "image upload",
)

swap(
    '''        assert stored, "the image batch stored no puzzle, so the column is untested"
        for row in stored:
            self._assert_row_is_a_real_list(row)

        # The route's own contribution, for the reason in the class docstring.
        assert handed_over, "the image route never reached add_puzzle"
        for names in handed_over:
            assert names, "the image route handed the store an empty list"
            assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names
''',
    '''        assert len(stored) == len(self.IMAGES), stored
        for row in stored:
            self._assert_row_is_a_real_list(row)

        # The route's own contribution, for the reason in the class docstring.
        assert len(handed_over) == len(self.IMAGES), handed_over
        for _grid, names in handed_over:
            assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names
        self._assert_hand_off_is_that_puzzles_list(handed_over)

        # Why two pictures: the ladders they solve with differ, so no single
        # constant can satisfy the identity assertion above — on this half
        # that is a fact about the fixtures, not a probability. Asserted
        # rather than left in the comment, because a solver change that made
        # these two solve alike would leave the identity assertion passing
        # while it no longer excluded a constant.
        assert len({tuple(names) for _grid, names in handed_over}) == len(
            self.IMAGES
        ), handed_over
''',
    "image test assertions",
)

# ---- 7. contextlib import ----------------------------------------------
swap(
    '''import dataclasses
import json
import re
''',
    '''import contextlib
import dataclasses
import json
import re
''',
    "contextlib import",
)

target.write_text(src)
print("written", target)
