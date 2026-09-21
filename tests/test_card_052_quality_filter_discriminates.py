"""CARD-052 AC-3 — the Minimum Quality Score filter actually filters.

CARD-050 answered this card's other two criteria as it landed: an image-mode
batch stores an independently reproducible measurement, and a faithful
conversion outscores a degraded one by at least 20 points. What no test
anywhere exercised was the filter **discriminating**.

Before this file, `quality_filter` appeared in the suite exactly twice: once
checking the parameter is validated, and once checking a random batch — whose
scores are all `None` since CARD-050 — is no longer dropped or crashed by it.
Neither puts a real score either side of a threshold.

The whole filter is one line, in the image generate loop::

    if quality_score < quality_filter:
        continue

A comparison with nothing either side of it is exactly the line that inverts,
or becomes ``<=``, or starts reading the wrong variable, without anyone
noticing — and the visible symptom would be an empty batch, which looks like
"the pictures were no good" rather than like a bug.

So the threshold here is **derived from the picture**, not guessed: generate
once unfiltered to learn what this image actually scores, then bracket it. A
hardcoded threshold would pass on a machine where the score happened to fall
the right side of it and fail elsewhere.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
PICTURE = FIXTURES / "bird1.jpg"


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin import image_manager as image_manager_module
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    app = create_app()
    app.config["TESTING"] = True
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


@pytest.fixture
def client(admin_app):
    return admin_app.test_client()


def _generate(client, admin_app, quality_filter):
    """Upload the picture at a threshold and generate; return the puzzles."""
    with open(PICTURE, "rb") as handle:
        upload = client.post(
            "/batch/from-images",
            data={
                "image_files": [(handle, PICTURE.name)],
                "quality_filter": str(quality_filter),
            },
            content_type="multipart/form-data",
        )
    assert upload.status_code == 302, upload.data

    response = client.post("/batch/generate-puzzles", data={}, follow_redirects=False)
    assert response.status_code == 302, response.data
    match = re.search(r"/batch/([^/]+)/generated-puzzles", response.location or "")
    if match is None:
        # Everything was filtered out, so there is no batch page to land on.
        return []
    return admin_app.batch_generator.get_batch_puzzles(
        match.group(1), offset=0, limit=100
    )


def test_the_minimum_quality_filter_admits_and_excludes_the_same_picture(
    admin_app, client
):
    """AC-3. One picture, three thresholds, derived from what it scores.

    The same conversion is admitted below its own score and excluded above it.
    Using one picture rather than two is deliberate: two pictures could differ
    for any number of reasons, and the claim being tested is about the
    *threshold*, not about the images.
    """
    unfiltered = _generate(client, admin_app, quality_filter=0)
    assert unfiltered, "the picture produced no puzzle even with no filter"
    score = unfiltered[0]["quality_score"]
    assert isinstance(score, int), f"expected a real measurement, got {score!r}"
    assert 1 <= score <= 100

    # Below its own score: admitted. At exactly its score: admitted, because
    # the rule is `< threshold` — the boundary belongs to the puzzle.
    assert _generate(client, admin_app, quality_filter=max(1, score - 1))
    assert _generate(client, admin_app, quality_filter=score)

    # Above it: excluded. Nothing is stored at all.
    assert _generate(client, admin_app, quality_filter=min(100, score + 1)) == []


def test_a_filter_of_one_hundred_excludes_everything_short_of_perfect(
    admin_app, client
):
    """The end of the range, which is where an inverted comparison shows.

    A `>` in place of `<` passes the test above for any threshold that happens
    to sit the convenient side of the score; it cannot pass this one and the
    zero case together.
    """
    assert _generate(client, admin_app, quality_filter=100) == []


def test_a_filter_of_zero_admits_the_picture(admin_app, client):
    """The other end. Together these two bracket the comparison's direction."""
    assert _generate(client, admin_app, quality_filter=0)
