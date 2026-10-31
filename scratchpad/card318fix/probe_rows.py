import os
os.environ.pop("DATABASE_URL", None)
os.environ["TESTING"] = "true"
from pathlib import Path
from nonogram.admin.batch_generator import BatchGenerator
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.admin import image_manager as image_manager_module
from nonogram.admin.app import create_app
from nonogram.limits import MIN_SIZE

store = PuzzleReviewService()
gen = BatchGenerator(puzzle_review_service=store)
gen.create_batch(count=10, sizes=[MIN_SIZE], source="random")
row = next(iter(store.puzzles.values()))
print("RANDOM ROW KEYS:", sorted(row.keys()))
print("has grid:", "grid" in row, type(row.get("grid")))

image_manager_module._image_manager = None
app = create_app()
app.config["TESTING"] = True
app.config["MAX_CONTENT_LENGTH"] = 50*1024*1024
with app.app_context():
    client = app.test_client()
    with open(Path("tests/fixtures/bird1.jpg"), "rb") as h:
        client.post("/batch/from-images", data={"image_files": [(h, "bird1.jpg")]}, content_type="multipart/form-data")
    r = client.post("/batch/generate-puzzles", data={}, follow_redirects=False)
    import re
    bid = re.search(r"/batch/([^/]+)/generated-puzzles", r.location).group(1)
    rows = app.batch_generator.get_batch_puzzles(bid, offset=0, limit=100)
    print("IMAGE ROW KEYS:", sorted(rows[0].keys()))
    print("has grid:", "grid" in rows[0], type(rows[0].get("grid")))
