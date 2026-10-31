"""CARD-318 fix round 2 — what the /puzzles listing actually renders per row.

Establishes the marker the new AC-142 assertion extracts, before the test is
written: the per-row thumbnail url `/api/puzzle/<id>/grid` is one occurrence
per listed puzzle and nothing else in the page produces it.
"""
import os, re, sys

sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-318/src")
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
os.environ.pop("DATABASE_URL", None)

from nonogram.admin.app import create_app

app = create_app()
app.config["TESTING"] = True
service = app.puzzle_review_service
print("service type:", type(service).__name__)


def stored(strategies):
    grid = [[True] * 10 for _ in range(10)]
    return service.add_puzzle(
        grid=grid, clues_rows=[], clues_cols=[], width=10, height=10,
        theme="test", difficulty_score=10, difficulty_tier="easy",
        quality_score=50, recognizability="medium",
        strategies_used=strategies, batch_id=None, source_image="p.png",
    )


a = stored(["simple_overlap"])
b = stored(["simple_overlap", "line_dp", "guess"])
print("seeded:", a, b)

client = app.test_client()
MARK = re.compile(r"/api/puzzle/([0-9a-fA-F-]+)/grid")
for q in ("/puzzles", "/puzzles?strategy=LineLogic", "/puzzles?strategy=guess"):
    r = client.get(q, follow_redirects=True)
    body = r.get_data(as_text=True)
    found = MARK.findall(body)
    print(f"{q:<34} {r.status_code} rows={found} unknown_flash={'Unknown strategy' in body}")

from nonogram.admin.puzzle_review import PuzzleFilter
res = service.filter_puzzles(PuzzleFilter(limit=50))
print("direct filter_puzzles:", res.total_count, [p["id"] for p in res.puzzles])
r = client.get("/puzzles")
body = r.get_data(as_text=True)
print("len body", len(body))
import re as _re
print("no-puzzles marker:", "No puzzles" in body)
for pid in (a, b):
    print(pid, "in body:", pid in body)
print([l for l in body.splitlines() if "puzzle_00" in l][:5])
