import os, re, sys
os.environ.pop("DATABASE_URL", None)
os.environ["TESTING"] = "true"
from pathlib import Path
from nonogram.admin import image_manager as image_manager_module
from nonogram.admin.app import create_app

FIXTURES = Path("tests/fixtures")
names = sys.argv[1:] or ["bird1.jpg"]

image_manager_module._image_manager = None
app = create_app()
app.config["TESTING"] = True
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
with app.app_context():
    handed = []
    svc = app.puzzle_review_service
    real = svc.add_puzzle
    def spying(*a, **k):
        handed.append((k.get("width"), k.get("height"), k.get("source_image"), k.get("strategies_used")))
        return real(*a, **k)
    svc.add_puzzle = spying
    client = app.test_client()
    handles = [open(FIXTURES / n, "rb") for n in names]
    data = {"image_files": [(h, n) for h, n in zip(handles, names)]}
    up = client.post("/batch/from-images", data=data, content_type="multipart/form-data")
    print("upload", up.status_code)
    r = client.post("/batch/generate-puzzles", data={}, follow_redirects=False)
    print("gen", r.status_code, r.location)
    for row in handed:
        print("HANDED", row)
