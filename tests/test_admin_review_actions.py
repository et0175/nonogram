"""Admin review actions keep the owner's place, and a batch can be curated in bulk.

1 — approve/reject/delete/restore on the review list return to the same
    filters, sort and page; an action that empties the last page lands on the
    new last page instead of "no puzzles found".
2 — the image preview's "Predicted Output" follows the size controls.
3 — Generated Puzzles: approve all, reject all, delete rejected.
"""

import urllib.parse

import pytest
from PIL import Image

import nonogram.admin.image_manager as image_manager_module


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


def _add(app, status="draft", batch_id=None, name="p.png"):
    store = app.puzzle_review_service
    puzzle_id = store.add_puzzle(
        grid=[[True] * 10 for _ in range(10)],
        clues_rows=[[10]] * 10,
        clues_cols=[[10]] * 10,
        width=10,
        height=10,
        theme="test",
        difficulty_score=10,
        difficulty_tier="Easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=batch_id,
        source_image=name,
    )
    if status == "approved":
        store.approve_puzzle(puzzle_id)
    elif status == "rejected":
        store.reject_puzzle(puzzle_id)
    return puzzle_id


def _statuses(app):
    return {pid: p["status"] for pid, p in app.puzzle_review_service.puzzles.items()}


# --- 1: the list keeps its place -------------------------------------------


@pytest.mark.parametrize("action,status", [
    ("approve", "draft"), ("reject", "draft"), ("restore", "approved"), ("delete", "rejected"),
])
def test_action_returns_to_the_same_filters_and_page(admin_app, action, status):
    ids = [_add(admin_app, status) for _ in range(5)]
    query = f"status={status}&size=10&sort_by=-quality&limit=2&offset=2"

    response = admin_app.test_client().post(
        f"/puzzle/{ids[2]}/{action}", data={"return_to": query}
    )

    assert response.status_code == 302
    location = urllib.parse.urlsplit(response.headers["Location"])
    assert location.path == "/puzzles"
    assert urllib.parse.parse_qs(location.query) == urllib.parse.parse_qs(query)


def test_return_to_cannot_redirect_off_the_list(admin_app):
    puzzle_id = _add(admin_app)
    response = admin_app.test_client().post(
        f"/puzzle/{puzzle_id}/approve", data={"return_to": "//evil.example/x?status=draft"}
    )
    location = urllib.parse.urlsplit(response.headers["Location"])
    assert location.netloc in ("", "localhost")
    assert location.path == "/puzzles"


def test_list_forms_carry_the_current_query(admin_app):
    _add(admin_app, "draft")
    _add(admin_app, "rejected")
    body = admin_app.test_client().get("/puzzles?status=&size=10&limit=5").get_data(as_text=True)
    assert body.count('name="return_to" value="status=&amp;size=10&amp;limit=5"') == 3


def test_emptied_last_page_moves_to_the_new_last_page(admin_app):
    for _ in range(3):
        _add(admin_app, "draft")
    # limit=2: page 2 (offset 2) held one draft, which has since been approved.
    admin_app.puzzle_review_service.approve_puzzle(list(_statuses(admin_app))[2])

    response = admin_app.test_client().get("/puzzles?status=draft&limit=2&offset=2")

    assert response.status_code == 302
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(response.headers["Location"]).query)
    assert query == {"status": ["draft"], "limit": ["2"], "offset": ["0"]}


def test_delete_works_without_a_database(admin_app):
    puzzle_id = _add(admin_app, "rejected")
    admin_app.test_client().post(f"/puzzle/{puzzle_id}/delete")
    assert puzzle_id not in admin_app.puzzle_review_service.puzzles


# --- 2: predicted output follows the size controls -------------------------


@pytest.fixture
def wide_image(admin_app, tmp_path):
    path = tmp_path / "wide.png"
    image = Image.new("L", (400, 200), 255)
    image.paste(0, (0, 0, 400, 200))
    image.save(path)
    return image_manager_module.get_image_manager().add_image(str(path), "wide.png")


def test_size_change_returns_the_new_prediction(admin_app, wide_image):
    client = admin_app.test_client()

    first = client.post(f"/api/image/{wide_image.file_id}/size", data={"mode": "fixed", "value": 20}).get_json()
    second = client.post(f"/api/image/{wide_image.file_id}/size", data={"mode": "fixed", "value": 30}).get_json()

    assert first["extent"] == [20, 10]
    assert second["extent"] == [30, 15]
    assert wide_image.size_value == 30
    # the page, rendered again, agrees with what the endpoint said
    assert "30×15" in client.get("/batch/preview-images").get_data(as_text=True)


def test_size_change_rejects_out_of_range_values(admin_app, wide_image):
    response = admin_app.test_client().post(
        f"/api/image/{wide_image.file_id}/size", data={"mode": "fixed", "value": 999}
    )
    assert response.status_code == 400
    assert wide_image.size_value == 20


def test_size_change_on_unknown_image_is_404(admin_app):
    response = admin_app.test_client().post("/api/image/nope/size", data={"mode": "fixed", "value": 20})
    assert response.status_code == 404


# --- 3: bulk curation of a batch --------------------------------------------


@pytest.fixture
def batch(admin_app):
    batch_id = admin_app.batch_generator.create_batch(
        count=1, sizes=[10], theme="image", source="images", quality_filter=0
    )
    ids = {
        "draft": _add(admin_app, "draft", batch_id),
        "approved": _add(admin_app, "approved", batch_id),
        "rejected": _add(admin_app, "rejected", batch_id),
        "in_book": _add(admin_app, "draft", batch_id),
        "other_batch": _add(admin_app, "rejected"),
    }
    stored = admin_app.puzzle_review_service.puzzles[ids["in_book"]]
    stored.update(status="in_book", book_id="book-1")
    return batch_id, ids


@pytest.mark.parametrize("route,expected", [("approve-all", "approved"), ("reject-all", "rejected")])
def test_bulk_status_changes_the_batch_but_not_books_or_other_batches(admin_app, batch, route, expected):
    batch_id, ids = batch

    response = admin_app.test_client().post(f"/batch/{batch_id}/{route}")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/batch/{batch_id}/generated-puzzles")
    statuses = _statuses(admin_app)
    assert statuses[ids["draft"]] == statuses[ids["approved"]] == statuses[ids["rejected"]] == expected
    assert statuses[ids["in_book"]] == "in_book"
    assert statuses[ids["other_batch"]] == "rejected"


def test_delete_rejected_removes_only_this_batchs_rejected(admin_app, batch):
    batch_id, ids = batch

    admin_app.test_client().post(f"/batch/{batch_id}/delete-rejected")

    remaining = _statuses(admin_app)
    assert ids["rejected"] not in remaining
    assert {ids["draft"], ids["approved"], ids["in_book"], ids["other_batch"]} <= remaining.keys()


def test_generated_page_offers_bulk_actions_and_shows_status(admin_app, batch):
    batch_id, _ = batch
    body = admin_app.test_client().get(f"/batch/{batch_id}/generated-puzzles").get_data(as_text=True)
    for route in ("approve-all", "reject-all", "delete-rejected"):
        assert f'action="/batch/{batch_id}/{route}"' in body
    assert "✓ Approved</span>" in body and "✕ Rejected</span>" in body


def test_bulk_on_unknown_batch_does_nothing(admin_app, batch):
    _, ids = batch
    before = _statuses(admin_app)
    admin_app.test_client().post("/batch/00000000-0000-0000-0000-000000000000/reject-all")
    assert _statuses(admin_app) == before
