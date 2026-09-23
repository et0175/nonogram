"""CARD-138 — an admin batch can ask for a difficulty, and says so when it falls short.

The engine could always generate to a tier: ``GenerationRequest.difficulty``
drives POL-004's resample loop and the CLI exposes it as ``--difficulty``. The
admin batch generator passed ``difficulty_tier=None,  # Accept any difficulty``
instead, so the only way to fill a book's medium quota was to generate at random
and hope. This card plumbs the field through — form → route → ``create_batch``
→ ``orchestrator.generate_batch`` — and makes the batch note say *which* tier
came up short, because a candidate discarded for its grade is a different fact
from a candidate that could not be made unique, and the generator reports one
``abandoned`` number for both.

**The source is stubbed here, deliberately.** A real targeted batch runs the
resample loop against unseeded draws — ``generate_batch`` makes its own
``random.Random()`` and each candidate draws its own seed — so a real
end-to-end medium batch is neither fast nor reproducible: at the small extents
that would keep it fast, the medium share is a few percent of draws, which
makes an abandoned candidate (and therefore a red test) a matter of luck on any
given run. So ``orchestrator.generate`` is replaced by :class:`_ScriptedSource`,
which stands in for "draw a grid, solve it, grade it" with a *seeded* sequence
of grades. What it does **not** stand in for is the keep-or-resample decision:
that is the real ``Puzzle.record_difficulty`` return value — POL-004's own
predicate on a real ``GenerationRequest`` — so a tier that failed to reach the
request would show up here as puzzles of the wrong grade rather than as a
mocked-away assertion. The loop's *bound* is the generator's own and is tested
where it lives (``tests/test_resample.py``, ``tests/test_batch_abandonment.py``).

``tests/test_batch_keeps_partial_work.py`` is the precedent for scripting
``generate`` this way, and for the ``_Store`` double and the sqlite DB-mode
check below.
"""

from __future__ import annotations

import random
import time
import uuid
from contextlib import contextmanager

import pytest

from nonogram import difficulty, orchestrator
from nonogram.admin.batch_generator import (
    MIN_RANDOM_BATCH_COUNT,
    BatchGenerator,
    BatchStatus,
)
from nonogram.difficulty import Tier
from nonogram.errors import (
    GenerationAbandoned,
    NotUniquelySolvable,
    UnsupportedDifficulty,
)
from nonogram.orchestrator import (
    MAX_CONSECUTIVE_ABANDONMENTS,
    GenerationRequest,
    Puzzle,
)

#: Any uniquely-solvable grid: this file is about tiers and counts, and the
#: store double below does not look at it.
_GRID = [[True, True], [False, True]]

#: How a draw's grade is distributed, roughly as CARD-137 measured production
#: (easy ~64%, medium ~29%, hard ~7%). Only its *shape* matters — it is here so
#: that an "Any" batch comes back genuinely mixed and a targeted one has to
#: resample for real.
_DRAW_WEIGHTS = ((Tier.EASY, 64), (Tier.MEDIUM, 29), (Tier.HARD, 7))

#: Draws one candidate is allowed before the source gives up on it. Generous on
#: purpose: a stub that ran out of draws would make these tests fail by luck of
#: the weights (hard is 7% of them), and the shortfall tests script their
#: abandonments explicitly instead. The *real* bound is the generator's
#: MAX_RETRY_ATTEMPTS, tested where it lives; this number is not a second one.
#: A draw costs one small object, so 250 of them is still microseconds.
_DRAWS_PER_CANDIDATE = 250


def _score_inside(tier: Tier) -> float:
    """A score ``difficulty.classify`` files under ``tier``.

    The midpoint of the tier's own band, read off :attr:`Tier.band` rather than
    written out: this test states no cutoff of its own (G-1), and a
    recalibration like CARD-137's moves it without an edit here.
    """
    low, high = tier.band
    return (low + high) / 2


def _puzzle(request: GenerationRequest, tier: Tier) -> Puzzle:
    """A finished candidate of ``tier``, graded through the real aggregate.

    ``requested_tier`` is resolved exactly as ``orchestrator.generate`` resolves
    it — through ``difficulty.parse_tier``, from the request — because that is
    the field POL-004's predicate reads. A stub that left it unset would accept
    every candidate and quietly stop testing anything.
    """
    requested_tier = (
        difficulty.parse_tier(request.difficulty)
        if request.difficulty is not None
        else None
    )
    puzzle = Puzzle(request=request, seed=0, requested_tier=requested_tier)
    puzzle.record_candidate(_GRID)
    puzzle.confirm_uniqueness(1)
    puzzle.record_difficulty(_score_inside(tier), 0)
    return puzzle


class _ScriptedSource:
    """``orchestrator.generate`` with the grid source and solver replaced.

    Each call draws grades from a seeded sequence until one satisfies the
    request — asked through ``Puzzle.record_difficulty``, which is POL-004's
    real predicate — and abandons the candidate when its draws run out, exactly
    as an exhausted resample budget does.
    """

    def __init__(self, seed: int = 138, draws: int = _DRAWS_PER_CANDIDATE) -> None:
        self._rng = random.Random(seed)
        self._draws = draws
        #: Every request the batch made, so a test can see what reached the engine.
        self.requests: list[GenerationRequest] = []
        #: Grids drawn in total — more than one per candidate means the
        #: keep-or-resample decision really discarded something.
        self.drawn = 0

    def _draw(self) -> Tier:
        tiers = [tier for tier, _ in _DRAW_WEIGHTS]
        weights = [weight for _, weight in _DRAW_WEIGHTS]
        self.drawn += 1
        return self._rng.choices(tiers, weights=weights)[0]

    def generate(self, request: GenerationRequest) -> Puzzle:
        self.requests.append(request)
        for _ in range(self._draws):
            candidate = _puzzle(request, self._draw())
            if candidate.difficulty_in_requested_tier:
                return candidate
        raise GenerationAbandoned(
            f"abandoned after {self._draws} resamples: no candidate graded "
            f"{request.difficulty}"
        )

    def install(self, monkeypatch: pytest.MonkeyPatch) -> "_ScriptedSource":
        monkeypatch.setattr(orchestrator, "generate", self.generate)
        return self


class _Store:
    """The puzzle store, reduced to what a batch asks of it."""

    def __init__(self) -> None:
        self.stored: list[dict] = []

    def add_puzzle(self, **kwargs) -> str:
        self.stored.append(kwargs)
        return f"puzzle-{len(self.stored)}"

    @property
    def tiers(self) -> list:
        return [entry["difficulty_tier"] for entry in self.stored]


def _outcomes(monkeypatch: pytest.MonkeyPatch, script: list[object]) -> list[str]:
    """The n-th ``generate`` is ``script[n]``: ``"ok"``, or an exception to raise.

    For the shortfall tests, where the premise is an outcome rather than the
    grades that produced it. An ``"ok"`` comes out in the tier the request asked
    for — which is what the real loop guarantees — or medium when it asked for
    none.
    """
    calls: list[str] = []

    def fake_generate(request: GenerationRequest) -> Puzzle:
        outcome = script[len(calls)]
        calls.append("generate")
        if isinstance(outcome, BaseException):
            raise outcome
        tier = Tier(request.difficulty) if request.difficulty else Tier.MEDIUM
        return _puzzle(request, tier)

    monkeypatch.setattr(orchestrator, "generate", fake_generate)
    return calls


def _abandonment() -> GenerationAbandoned:
    return GenerationAbandoned("abandoned after 30 regenerate attempts")


def _budget_expires_after(monkeypatch: pytest.MonkeyPatch, candidates: int) -> None:
    """Make the batch's own clock run out once ``candidates`` have been made.

    ``generate_batch`` already takes ``budget_seconds`` and ``monotonic`` for
    this (CARD-088); the admin generator calls it without them, so the call is
    wrapped rather than the clock patched globally. No sleeping and no real
    deadline: the fake returns real time plus an offset that leaps once, which
    crosses only the batch's own deadline — a fake returning small absolute
    numbers would also poison each candidate's deadline, the trap CARD-086 hit.

    The loop reads the clock once to set the deadline and once before every
    candidate, so ``candidates + 1`` calls pass before the leap.
    """
    real_generate_batch = orchestrator.generate_batch
    base = time.monotonic()
    state = {"calls": 0}

    def clock() -> float:
        state["calls"] += 1
        return base + (0.0 if state["calls"] <= candidates + 1 else 999.0)

    def generate_batch(**kwargs):
        return real_generate_batch(budget_seconds=10.0, monotonic=clock, **kwargs)

    monkeypatch.setattr(orchestrator, "generate_batch", generate_batch)


class _RefusingStore(_Store):
    """A store that rejects every candidate — CARD-080's "unreachable" branch."""

    def add_puzzle(self, **kwargs) -> str:
        raise NotUniquelySolvable("the store refused this candidate")


@pytest.fixture
def admin_app(monkeypatch):
    """The panel in in-memory mode, as the other admin route tests build it."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    import nonogram.admin.image_manager as image_manager_module

    image_manager_module._image_manager = None
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


# ---------------------------------------------------------------------------
# AC-1 — a batch asked for Medium comes back medium (or short, with a note)
# ---------------------------------------------------------------------------


class TestBatchDifficulty_MediumBatchReturnsOnlyMediums:
    def test_every_stored_puzzle_is_medium(self, monkeypatch: pytest.MonkeyPatch) -> None:
        source = _ScriptedSource().install(monkeypatch)
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store)

        batch_id = generator.create_batch(count=20, sizes=[10], difficulty_tier="medium")

        assert generator.jobs[batch_id].status is BatchStatus.COMPLETE
        assert len(store.stored) == 20
        assert store.tiers == [Tier.MEDIUM] * 20
        assert source.drawn > 20, (
            "a targeted batch that kept every first draw would not be "
            "exercising POL-004's discard at all"
        )

    def test_the_tier_reaches_the_engine_on_every_request(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The plumbing this card is: the field on the request, not a filter
        applied afterwards. A generator that dropped it would still store
        mediums whenever the draws happened to be medium."""
        source = _ScriptedSource().install(monkeypatch)
        generator = BatchGenerator(puzzle_review_service=_Store())

        generator.create_batch(count=10, sizes=[10], difficulty_tier="medium")

        assert {request.difficulty for request in source.requests} == {"medium"}

    @pytest.mark.parametrize("spelling", ["Medium", " medium ", "MEDIUM"])
    def test_the_spelling_is_parse_tiers_business_and_arrives_canonical(
        self, monkeypatch: pytest.MonkeyPatch, spelling: str
    ) -> None:
        """``difficulty.parse_tier`` owns the vocabulary (G-1): the admin
        matches no tier name of its own, and what travels on is the canonical
        value so the second parse downstream cannot disagree with the first."""
        source = _ScriptedSource().install(monkeypatch)
        generator = BatchGenerator(puzzle_review_service=_Store())

        generator.create_batch(count=10, sizes=[10], difficulty_tier=spelling)

        assert {request.difficulty for request in source.requests} == {"medium"}

    def test_a_tier_that_does_not_exist_is_refused_before_any_work(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = _ScriptedSource().install(monkeypatch)
        generator = BatchGenerator(puzzle_review_service=_Store())

        with pytest.raises(UnsupportedDifficulty):
            generator.create_batch(count=20, sizes=[10], difficulty_tier="fiendish")

        assert generator.jobs == {}
        assert source.requests == []

    def test_each_tier_can_be_asked_for(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for tier in Tier:
            source = _ScriptedSource().install(monkeypatch)
            store = _Store()
            generator = BatchGenerator(puzzle_review_service=store)

            generator.create_batch(count=10, sizes=[10], difficulty_tier=tier.value)

            assert store.tiers == [tier] * 10, tier
            assert {request.difficulty for request in source.requests} == {tier.value}


# ---------------------------------------------------------------------------
# AC-2 — Any is the absence of a tier, and behaves exactly as before
# ---------------------------------------------------------------------------


class TestBatchDifficulty_AnyIsUnchanged:
    def test_no_tier_requested_means_no_tier_on_any_request(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = _ScriptedSource().install(monkeypatch)
        generator = BatchGenerator(puzzle_review_service=_Store())

        generator.create_batch(count=20, sizes=[10])

        assert [request.difficulty for request in source.requests] == [None] * 20

    def test_an_untargeted_batch_keeps_whatever_it_drew(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No filtering: the grades that come out are the grades that are
        stored, and one draw per candidate is all it takes."""
        source = _ScriptedSource().install(monkeypatch)
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store)

        generator.create_batch(count=20, sizes=[10], difficulty_tier=None)

        assert len(source.requests) == 20
        assert source.drawn == 20, "nothing was discarded, so nothing was filtered"
        assert len(store.stored) == 20
        assert len(set(store.tiers)) > 1, "an unfiltered batch is a mixed batch"

    def test_the_empty_string_is_not_a_word_for_any(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``None`` is the only way to say "any" — an empty string names no
        tier and is refused, the same answer the CLI and the orchestrator give
        it. The form sends no value at all for Any, which is why this can stay
        strict."""
        _ScriptedSource().install(monkeypatch)
        generator = BatchGenerator(puzzle_review_service=_Store())

        with pytest.raises(UnsupportedDifficulty):
            generator.create_batch(count=20, sizes=[10], difficulty_tier="")

    def test_the_shortfall_note_of_an_untargeted_batch_is_word_for_word_what_it_was(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CARD-083's sentence, unchanged. The tier wording is an *additional*
        branch, not a rewrite of this one."""
        _outcomes(monkeypatch, ["ok", _abandonment()] * 10)
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store)

        batch_id = generator.create_batch(count=20, sizes=[10])

        assert generator.jobs[batch_id].error_message == (
            "10 of 20 candidates could not be made uniquely solvable within "
            "the retry budget and were skipped, so this batch has 10 puzzles "
            "rather than 20. That is expected occasionally — it is how a "
            "random grid can come out — and the batch was kept rather than "
            "discarded (CARD-083). Re-run if you need the full count."
        )

    def test_a_clean_untargeted_batch_still_carries_no_note(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _ScriptedSource().install(monkeypatch)
        generator = BatchGenerator(puzzle_review_service=_Store())

        batch_id = generator.create_batch(count=10, sizes=[10])

        assert generator.jobs[batch_id].error_message is None


# ---------------------------------------------------------------------------
# AC-3 — the form offers Any / Easy / Medium / Hard, and Any is the default
# ---------------------------------------------------------------------------


class TestBatchDifficulty_FormOffersTheChoices:
    def test_the_form_offers_any_and_every_tier(self, admin_app) -> None:
        page = admin_app.test_client().get("/batch/create").get_data(as_text=True)

        assert 'name="difficulty"' in page
        assert '<option value="" selected>Any</option>' in page
        for tier in Tier:
            assert f'<option value="{tier.value}">{tier.label}</option>' in page

    def test_any_is_the_only_option_preselected(self, admin_app) -> None:
        page = admin_app.test_client().get("/batch/create").get_data(as_text=True)
        select = page.split('name="difficulty"', 1)[1].split("</select>", 1)[0]

        assert select.count("selected") == 1
        assert 'value="" selected' in select

    def test_choosing_any_sends_no_tier_and_the_route_passes_none(
        self, admin_app, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The form's Any option has an empty value, so the conversion to
        ``None`` happens once, at the route boundary — nothing further in owns
        a second spelling of "any"."""
        seen = {}

        def fake_create_batch(**kwargs) -> str:
            seen.update(kwargs)
            return str(uuid.uuid4())

        monkeypatch.setattr(admin_app.batch_generator, "create_batch", fake_create_batch)

        admin_app.test_client().post(
            "/batch/create",
            data={"source": "random", "count": "10", "sizes": "10", "difficulty": ""},
        )

        assert seen["difficulty_tier"] is None

    def test_choosing_a_tier_sends_it_through(
        self, admin_app, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen = {}

        def fake_create_batch(**kwargs) -> str:
            seen.update(kwargs)
            return str(uuid.uuid4())

        monkeypatch.setattr(admin_app.batch_generator, "create_batch", fake_create_batch)

        admin_app.test_client().post(
            "/batch/create",
            data={
                "source": "random",
                "count": "10",
                "sizes": "10",
                "difficulty": "medium",
            },
        )

        assert seen["difficulty_tier"] == "medium"

    def test_a_tier_nobody_supports_is_a_form_error_not_a_500(self, admin_app) -> None:
        response = admin_app.test_client().post(
            "/batch/create",
            data={
                "source": "random",
                "count": "10",
                "sizes": "10",
                "difficulty": "fiendish",
            },
            follow_redirects=True,
        )
        page = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "fiendish" in page
        # parse_tier's own message, which lists the tiers that exist.
        assert "supported tiers are" in page


# ---------------------------------------------------------------------------
# AC-4 — a batch that cannot fill the count keeps its work and names the shortfall
# ---------------------------------------------------------------------------


class TestBatchDifficulty_ShortfallIsReportedNotSilent:
    def test_the_note_names_the_tier_the_counts_and_the_cause(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _outcomes(monkeypatch, ["ok", _abandonment()] * 20)
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store)

        batch_id = generator.create_batch(count=40, sizes=[10], difficulty_tier="medium")

        job = generator.jobs[batch_id]
        assert job.status is BatchStatus.COMPLETE
        assert len(store.stored) == 20
        assert job.puzzle_count == 20
        note = job.error_message
        assert "20 of 40" in note
        assert "medium" in note
        assert "20 medium puzzles rather than 40" in note
        assert "The shortfall is the tier, not uniqueness" in note

    def test_the_untargeted_wording_is_not_reused_for_a_targeted_batch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """"Could not be made uniquely solvable" would be a lie here: with a
        tier asked for, a skipped candidate is far more often a good puzzle of
        the wrong grade."""
        _outcomes(monkeypatch, ["ok", _abandonment()] * 10)
        generator = BatchGenerator(puzzle_review_service=_Store())

        batch_id = generator.create_batch(count=20, sizes=[10], difficulty_tier="hard")

        assert "uniquely solvable within the retry budget" not in (
            generator.jobs[batch_id].error_message
        )

    def test_the_batch_completes_rather_than_failing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-4 and G-2: short is not failed. The puzzles it made are real and
        already stored."""
        _outcomes(monkeypatch, ["ok", _abandonment()] * 10)
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store)

        batch_id = generator.create_batch(count=20, sizes=[10], difficulty_tier="easy")

        assert generator.jobs[batch_id].status is BatchStatus.COMPLETE
        assert store.tiers == [Tier.EASY] * 10

    def test_a_targeted_batch_stopped_by_consecutive_abandonments_says_so(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CARD-093's stop rule is untouched (G-2) — only its note learns the
        tier. Three abandonments in a row still end the batch, and the five
        puzzles made before them are still kept."""
        script = ["ok"] * 5 + [_abandonment()] * MAX_CONSECUTIVE_ABANDONMENTS
        _outcomes(monkeypatch, script)
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store)

        batch_id = generator.create_batch(count=20, sizes=[10], difficulty_tier="medium")

        job = generator.jobs[batch_id]
        assert job.status is BatchStatus.COMPLETE
        assert len(store.stored) == 5
        assert "stopped early with 5 of 20 medium puzzles made" in job.error_message
        assert "asked for medium puzzles" in job.error_message

    def test_a_targeted_batch_that_made_nothing_is_still_an_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The other half of G-2: zero puzzles is a failed batch, exactly as
        before. A tier does not turn one into a short batch."""
        _outcomes(monkeypatch, [_abandonment()] * MAX_CONSECUTIVE_ABANDONMENTS)
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=_Store())

        with pytest.raises(GenerationAbandoned):
            generator.create_batch(count=20, sizes=[10], difficulty_tier="medium")

        (job,) = generator.jobs.values()
        assert job.status is BatchStatus.ERROR
        assert store.stored == []

    def test_the_database_record_says_the_same(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """The DB branch is the one production runs, and the tier reaches it
        as an argument — the batches table has no column for it and this card
        writes no migration."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from nonogram.db.models import Base, Batch

        engine = create_engine(f"sqlite:///{tmp_path / 'batches.db'}")
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)

        @contextmanager
        def scope():
            db = factory()
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        _outcomes(monkeypatch, ["ok", _abandonment()] * 10)
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store, session_factory=scope)

        batch_id = generator.create_batch(count=20, sizes=[10], difficulty_tier="medium")

        with scope() as db:
            row = db.get(Batch, uuid.UUID(batch_id))
            assert row.status == BatchStatus.COMPLETE.value
            assert row.puzzle_count == 10
            assert "10 medium puzzles rather than 20" in row.error_message
        assert len(store.stored) == 10


# ---------------------------------------------------------------------------
# AC-4, the other give-up mode — the batch's clock (review cycle 1, F-001)
# ---------------------------------------------------------------------------


class TestBatchDifficulty_TheClockShortfallNamesTheTierToo:
    """A targeted batch reaches its time budget *sooner*, and must say so.

    Every off-tier candidate is discarded and redrawn out of the one batch
    budget (POL-004), so asking for a tier makes this give-up mode more likely,
    not less — and it is reachable at ordinary settings, since the resample
    bound against ``BATCH_BUDGET_SECONDS`` lets a single 30x30 candidate spend
    a large share of the batch's clock. The note that comes out of it was the
    untargeted one word for word: no tier named, and remedial advice ("fewer
    puzzles, or a smaller size") that omitted the lever which dominates the
    cost here.
    """

    def test_the_clock_note_names_the_tier(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _ScriptedSource().install(monkeypatch)
        _budget_expires_after(monkeypatch, 5)
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store)

        batch_id = generator.create_batch(count=20, sizes=[10], difficulty_tier="hard")

        job = generator.jobs[batch_id]
        assert job.status is BatchStatus.COMPLETE
        assert len(store.stored) == 5, "the work done before the clock is kept"
        assert store.tiers == [Tier.HARD] * 5
        assert "15 of the 20 hard puzzles were never attempted" in job.error_message

    def test_the_clock_note_offers_any_difficulty_as_a_way_out(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The one lever that dominates the cost of a targeted batch. Advice
        that lists only "fewer" and "smaller" sends the owner to shrink a
        request whose real cost is the redraws."""
        _ScriptedSource().install(monkeypatch)
        _budget_expires_after(monkeypatch, 5)
        generator = BatchGenerator(puzzle_review_service=_Store())

        batch_id = generator.create_batch(count=20, sizes=[10], difficulty_tier="medium")
        note = generator.jobs[batch_id].error_message

        assert "for Any difficulty" in note
        assert "discarded and redrawn" in note
        assert "not bad luck" in note, "CARD-088's point survives: it will recur"

    def test_the_untargeted_clock_note_is_word_for_word_what_it_was(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CARD-088's sentence, byte for byte. The tier wording is an
        *additional* branch, not a rewrite of this one."""
        _ScriptedSource().install(monkeypatch)
        _budget_expires_after(monkeypatch, 5)
        generator = BatchGenerator(puzzle_review_service=_Store())

        batch_id = generator.create_batch(count=20, sizes=[10])

        assert generator.jobs[batch_id].error_message == (
            "15 of 20 were never attempted: the batch reached its time budget "
            "first. This is not bad luck — the same request will stop in the "
            "same place — so ask for fewer puzzles, or for a smaller size. A "
            "puzzle costs about 0.06s at 20x20 and about 3.9s at 30x30, which "
            "is the whole of the difference."
        )

    def test_the_store_refusal_sentence_stays_untiered(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deliberate, and the one sentence the tier does *not* reach.

        A candidate the store rejects as not uniquely solvable is a bug in the
        generation path (CARD-080, INV-002), not a shortfall against the
        requested tier. It means the same thing whatever was asked for, and
        naming the tier there would invite the owner to change their request to
        work around a defect that is not theirs.
        """
        _ScriptedSource().install(monkeypatch)
        generator = BatchGenerator(puzzle_review_service=_RefusingStore())

        batch_id = generator.create_batch(count=10, sizes=[10], difficulty_tier="medium")
        note = generator.jobs[batch_id].error_message

        assert "10 of 10 generated candidates were refused by the store" in note
        assert "medium" not in note.split("were refused by the store", 1)[1]
        assert "bug in the generation path" in note


# ---------------------------------------------------------------------------
# AC-3, the seam — the form really drives a batch, not just create_batch
# ---------------------------------------------------------------------------


class TestBatchDifficulty_TheFormDrivesARealBatch:
    def test_posting_the_form_with_a_tier_stores_puzzles_of_that_tier(
        self, admin_app, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End to end through the seam the other route tests mock away: form
        fields → route → ``create_batch`` → the engine → the store. A defect in
        either half alone (a field the route drops, a tier the generator
        ignores) shows up here; the route tests above pin only the first half."""
        _ScriptedSource().install(monkeypatch)
        store = _Store()
        monkeypatch.setattr(admin_app.batch_generator, "puzzle_review_service", store)

        response = admin_app.test_client().post(
            "/batch/create",
            data={
                "source": "random",
                "count": "10",
                "sizes": "10",
                "difficulty": "hard",
            },
        )

        assert response.status_code == 302
        assert store.tiers == [Tier.HARD] * 10

    def test_posting_the_form_with_any_stores_a_mixed_batch(
        self, admin_app, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _ScriptedSource().install(monkeypatch)
        store = _Store()
        monkeypatch.setattr(admin_app.batch_generator, "puzzle_review_service", store)

        admin_app.test_client().post(
            "/batch/create",
            data={"source": "random", "count": "20", "sizes": "10", "difficulty": ""},
        )

        assert len(store.stored) == 20
        assert len(set(store.tiers)) > 1, "Any filters nothing"


# ---------------------------------------------------------------------------
# The form's bounds are the generator's bounds (review cycle 1, minor)
# ---------------------------------------------------------------------------


class TestBatchDifficulty_TheFormStatesNoBoundOfItsOwn:
    def test_the_count_floor_comes_from_the_generator(self, admin_app) -> None:
        """One copy of the bound. It was a bare ``min="10"`` in the template
        against a bare ``10`` in ``create_batch`` — the same two-copies shape
        that let this layer accept a count the layer below refused (CARD-088)."""
        page = admin_app.test_client().get("/batch/create").get_data(as_text=True)
        field = page.split('id="random_count"', 1)[1].split(">", 1)[0]

        assert f'min="{MIN_RANDOM_BATCH_COUNT}"' in field

    def test_the_floor_the_form_shows_is_the_floor_the_generator_enforces(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _ScriptedSource().install(monkeypatch)
        generator = BatchGenerator(puzzle_review_service=_Store())

        with pytest.raises(ValueError):
            generator.create_batch(count=MIN_RANDOM_BATCH_COUNT - 1, sizes=[10])

        batch_id = generator.create_batch(count=MIN_RANDOM_BATCH_COUNT, sizes=[10])
        assert generator.jobs[batch_id].status is BatchStatus.COMPLETE
