"""Is the `[\\w-]+` id pattern load-bearing, and is the listing really read off
the response?  Rendered twice: an EMPTY page and a page with two puzzles."""
import os, re, sys
os.environ.pop("DATABASE_URL", None)
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from nonogram.admin.app import create_app
from nonogram.admin import puzzle_review

STRICT = r"/api/puzzle/([\w-]+)/grid"
LOOSE  = r"/api/puzzle/([^/]+)/grid"

app = create_app(); app.config["TESTING"] = True
c = app.test_client()

empty = c.get("/puzzles").get_data(as_text=True)
print("empty page: strict =", sorted(set(re.findall(STRICT, empty))))
print("empty page: loose  =", sorted(set(re.findall(LOOSE, empty)))[:4],
      "count =", len(set(re.findall(LOOSE, empty))))
print("page carries the JS template literal:",
      "${escapeAttr(puzzle.id)}/grid" in empty)
print("page carries _puzzle_table include (thumb url present):",
      "/api/puzzle/" in empty)

# now store two puzzles the same way the test does
sys.path.insert(0, ".")
import tests.test_strategies as T
a = T._stored(app.puzzle_review_service, ["simple_overlap"])
b = T._stored(app.puzzle_review_service, ["line_dp", "guess"])
full = c.get("/puzzles").get_data(as_text=True)
print("\ntwo stored:", sorted([a, b]))
print("full page: strict =", sorted(set(re.findall(STRICT, full))))
print("strict == stored ids:", set(re.findall(STRICT, full)) == {a, b})
print("full page: loose  count =", len(set(re.findall(LOOSE, full))))
# and the filtered-away page, to show strict goes empty
filt = c.get("/puzzles?status=approved").get_data(as_text=True)
print("\nreally-filtered page (status=approved): strict =",
      sorted(set(re.findall(STRICT, filt))),
      "| loose count =", len(set(re.findall(LOOSE, filt))))
