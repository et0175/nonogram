"""CARD-095 — an image batch stops on its own clock, as a random batch does.

The image route ran every loaded picture inside one request with no time bound,
and one picture can cost up to three ``orchestrator.generate`` calls (the
predicted extent and two neighbours), each with its own 30 s deadline. Past
gunicorn's 120 s the worker is killed. The route now checks
``BATCH_BUDGET_SECONDS`` before *every* generate call, so the ceiling is the
same ``BATCH_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS`` the random path holds.

Owner decisions: pictures the clock never reached stay loaded for the next batch
(Q-1 a); a clock-stopped batch with puzzles is ``COMPLETE`` with a note, and
``ERROR`` only when nothing was made (Q-2).

``generate`` is scripted and the clock is fake: each scripted call *spends* a
chosen number of seconds on the fake clock, so a batch runs past the budget
without sleeping.
"""

from __future__ import annotations

import pytest
from PIL import Image as PILImage

from nonogram import orchestrator
from nonogram.admin.batch_generator import BatchGenerator, BatchStatus
from nonogram.errors import GenerationAbandoned
from nonogram.orchestrator import BATCH_BUDGET_SECONDS

_real_generate = orchestrator.generate


class _World:
    """A fake clock, a scripted ``generate`` that spends time on it, and a
    record of the app's batch generator and every status update it made."""

    def __init__(self, costs: list[float], abandon: set[int] = frozenset()) -> None:
        self.now = 0.0
        self.costs = costs
        self.abandon = abandon
        self.calls = 0
        self.generator: BatchGenerator | None = None
        self.puzzle_counts: list[int] = []

    def clock(self) -> float:
        return self.now

    def generate(self, request):
        index = self.calls
        self.calls += 1
        self.now += self.costs[index] if index < len(self.costs) else self.costs[-1]
        if index in self.abandon:
            raise GenerationAbandoned("the picture could not be made uniquely solvable")
        # A real, uniquely solvable 10x10 puzzle, made instantly.
        return _real_generate(
            orchestrator.GenerationRequest(mode="random", width=10, height=10, density=100, seed=1)
        )


@pytest.fixture
def world(monkeypatch):
    def install(costs, abandon=frozenset()):
        w = _World(costs, set(abandon))
        import nonogram.admin.app as app_module

        monkeypatch.setattr(app_module, "_batch_clock", w.clock)
        monkeypatch.setattr(orchestrator, "generate", w.generate)

        real_create = BatchGenerator.create_batch
        real_update = BatchGenerator._update_batch_status

        def create_batch(self, *args, **kwargs):
            w.generator = self
            return real_create(self, *args, **kwargs)

        def update(self, batch_id, status=None, **fields):
            if "puzzle_count" in fields:
                w.puzzle_counts.append(fields["puzzle_count"])
            return real_update(self, batch_id, status, **fields)

        monkeypatch.setattr(BatchGenerator, "create_batch", create_batch)
        monkeypatch.setattr(BatchGenerator, "_update_batch_status", update)
        return w

    return install


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    import nonogram.admin.image_manager as image_manager_module

    image_manager_module._image_manager = None
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app.test_client()
    image_manager_module._image_manager = None


def _loaded():
    import nonogram.admin.image_manager as image_manager_module

    return image_manager_module.get_image_manager().get_all_images()


def _upload(client, tmp_path, count: int) -> None:
    files = []
    for index in range(count):
        path = tmp_path / f"picture-{index}.png"
        PILImage.new("L", (200, 200), color=0).save(path)
        files.append((open(path, "rb"), path.name))
    try:
        response = client.post(
            "/batch/from-images", data={"image_files": files}, content_type="multipart/form-data"
        )
    finally:
        for handle, _ in files:
            handle.close()
    assert response.status_code == 302


def _run(client) -> str:
    return client.post("/batch/generate-puzzles", follow_redirects=True).get_data(as_text=True)


def _job(w: _World):
    (job,) = w.generator.jobs.values()
    return job


def test_pictures_after_the_budget_are_not_started(client, world, tmp_path):
    w = world(costs=[30.0])  # 30 s each: started at 0, 30, 60; 90 is past 75
    _upload(client, tmp_path, 5)

    body = _run(client)

    assert w.calls == 3
    assert "2 pictures were not started" in body
    job = _job(w)
    assert job.status is BatchStatus.COMPLETE
    assert job.puzzle_count == 3
    assert "not started" in job.error_message


def test_pictures_the_clock_never_reached_stay_loaded(client, world, tmp_path):
    world(costs=[30.0])
    _upload(client, tmp_path, 5)
    names_before = {image.original_filename for image in _loaded()}

    _run(client)

    remaining = _loaded()
    assert len(remaining) == 2
    assert {image.original_filename for image in remaining} <= names_before


def test_a_picture_cut_short_by_the_clock_does_not_try_its_neighbours(client, world, tmp_path):
    """The check that makes the ceiling 75 + 30 rather than 75 + 90."""
    w = world(costs=[BATCH_BUDGET_SECONDS + 5], abandon={0})
    _upload(client, tmp_path, 1)

    body = _run(client)

    assert w.calls == 1
    assert "not started" in body or "not finished" in body
    assert len(_loaded()) == 1


def test_a_clock_stop_before_any_puzzle_is_an_error(client, world, tmp_path):
    w = world(costs=[BATCH_BUDGET_SECONDS + 5], abandon={0})
    _upload(client, tmp_path, 3)

    _run(client)

    job = _job(w)
    assert job.puzzle_count == 0
    assert job.status is BatchStatus.ERROR
    assert "not started" in job.error_message or "not finished" in job.error_message


def test_the_puzzle_count_is_written_as_puzzles_are_stored(client, world, tmp_path):
    w = world(costs=[1.0])
    _upload(client, tmp_path, 3)

    _run(client)

    assert w.puzzle_counts[:3] == [1, 2, 3]


def test_a_batch_that_fits_is_unchanged(client, world, tmp_path):
    w = world(costs=[1.0])
    _upload(client, tmp_path, 3)

    body = _run(client)

    assert w.calls == 3
    assert "Generated 3 puzzle(s) from 3 image(s)" in body
    assert "not started" not in body
    assert _loaded() == []
    job = _job(w)
    assert job.status is BatchStatus.COMPLETE
    assert job.puzzle_count == 3
    assert job.error_message is None
