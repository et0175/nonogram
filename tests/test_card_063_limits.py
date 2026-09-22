"""CARD-063: the supported grid size range is defined once, in
``nonogram.limits``, and every enforced bound reads it (AC-2, AC-4). The
import-guard half (AC-3) lives with the guard in ``tests/test_cli.py``.
"""

import ast
import html
import inspect
import re
from pathlib import Path

import pytest
from PIL import Image as PILImage

from nonogram import difficulty, limits
from nonogram.admin.batch_generator import BatchGenerator
from nonogram.admin.book_plan import BUCKETS
from nonogram.admin.image_manager import ImageManager
from nonogram.admin.puzzle_review import PuzzleFilter, PuzzleReviewService
from nonogram.export import layout
from nonogram.sourcing import random_grid
from nonogram.web import metadata as web_metadata
from nonogram.web import pages

SRC = Path(__file__).resolve().parents[1] / "src" / "nonogram"
LOW, HIGH = limits.MIN_SIZE, limits.MAX_SIZE
#: (side, accepted) on both edges of the range.
EDGES = [(LOW, True), (HIGH, True), (LOW - 1, False), (HIGH + 1, False)]


def _assigned_names(path: Path) -> list[str]:
    names = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        names += [t.id for t in targets if isinstance(t, ast.Name)]
    return names


def test_the_range_is_assigned_in_limits_and_nowhere_else():
    owners = sorted(
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.py")
        for name in _assigned_names(path)
        if name in {"MIN_SIZE", "MAX_SIZE"}
    )
    assert owners == ["limits.py", "limits.py"]


def test_limits_imports_nothing():
    tree = ast.parse((SRC / "limits.py").read_text(encoding="utf-8"))
    assert not [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]


def test_core_modules_read_the_shared_range():
    assert (random_grid.MIN_SIZE, random_grid.MAX_SIZE) == (LOW, HIGH)


def test_the_scorer_no_longer_restates_the_range_at_all():
    """CARD-076: ``difficulty`` used to hold a *second* definition of the range.

    ``MIN_SUPPORTED_CELLS``/``MAX_SUPPORTED_CELLS`` existed only as the
    denominators of ADR-0013's size normalizer, and CARD-023 had to hand-edit
    the maximum alongside ``random_grid.MAX_SIZE`` — two definitions of one
    fact, kept in step by hand. ADR-0029 took size out of the score entirely
    (a 30x30 that never leaves simple overlap is exactly as Easy as a 10x10
    that never does), so the denominators went with it.

    Asserted as an *absence* rather than dropped silently: the strongest form
    of "these two definitions cannot drift" is that there is only one of them,
    and this is the test that says so.
    """
    assert not hasattr(difficulty, "MIN_SUPPORTED_CELLS")
    assert not hasattr(difficulty, "MAX_SUPPORTED_CELLS")


# --- admin validators ---------------------------------------------------------


@pytest.mark.parametrize("side, accepted", EDGES)
def test_admin_puzzle_filter_follows_the_range(side, accepted):
    service = PuzzleReviewService()
    request = PuzzleFilter(size=(side, side))
    if accepted:
        service.filter_puzzles(request)
    else:
        with pytest.raises(ValueError, match=f"{LOW}-{HIGH}"):
            service.filter_puzzles(request)


@pytest.mark.parametrize("side, accepted", EDGES)
def test_admin_batch_sizes_follow_the_range(side, accepted):
    generator = BatchGenerator()
    # "images" batches record the job without generating anything here.
    if accepted:
        generator.create_batch(count=1, sizes=[side], source="images")
    else:
        with pytest.raises(ValueError, match=f"{LOW}-{HIGH}"):
            generator.create_batch(count=1, sizes=[side], source="images")


@pytest.mark.parametrize("side, accepted", EDGES)
def test_admin_image_size_follows_the_range(tmp_path, side, accepted):
    path = tmp_path / "square.png"
    PILImage.new("L", (200, 200), color=0).save(path)
    manager = ImageManager(temp_dir=str(tmp_path / "store"))
    image = manager.add_image(str(path), "square.png")
    image.size_value = 20

    manager.update_image_size(image.file_id, "fixed", side)

    assert image.size_value == (side if accepted else 20)


# --- admin templates ----------------------------------------------------------

TEMPLATES = SRC / "admin" / "templates"


# book_select_puzzles.html has no size input since CARD-122 replaced its
# size-range filter with the four longest-side tabs (AC-216); the tabs read
# their bounds from book_plan, which reads nonogram.limits.
@pytest.mark.parametrize("name", ["image_preview.html", "puzzles_list.html"])
def test_admin_templates_take_the_range_from_jinja_globals(name):
    source = (TEMPLATES / name).read_text(encoding="utf-8")
    assert 'min="{{ MIN_SIZE }}"' in source and 'max="{{ MAX_SIZE }}"' in source
    assert not re.search(r'min="10"|max="30"|\b10-30\b', source)


@pytest.fixture
def admin_app(monkeypatch):
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


def _input_bounds(body: str, input_id: str) -> tuple:
    """``(min, max, placeholder)`` as rendered on the ``<input>`` with ``input_id``.

    Read off the rendered page, not the template source, so a bound wired to
    the wrong constant (``max="{{ MIN_SIZE }}"``) fails here.
    """
    tag = re.search(rf'<input[^>]*\bid="{re.escape(input_id)}"[^>]*>', body, re.DOTALL)
    assert tag, f"no <input id={input_id!r}> in the rendered page"
    attrs = dict(re.findall(r'\b(min|max|placeholder)="([^"]*)"', tag.group(0)))
    return attrs.get("min"), attrs.get("max"), attrs.get("placeholder")


def test_the_image_preview_page_renders_the_range(admin_app, tmp_path):
    import nonogram.admin.image_manager as image_manager_module

    client = admin_app.test_client()
    picture = tmp_path / "square.png"
    PILImage.new("L", (200, 200), color=0).save(picture)
    with open(picture, "rb") as f:
        response = client.post(
            "/batch/from-images",
            data={"image_files": [(f, "square.png")]},
            content_type="multipart/form-data",
        )
    assert response.status_code == 302
    (image,) = image_manager_module.get_image_manager().get_all_images()

    body = client.get("/batch/preview-images").get_data(as_text=True)

    assert _input_bounds(body, "globalSizeValue")[:2] == (str(LOW), str(HIGH))
    # The hint under that input, which no bound check would catch (CARD-065).
    assert f">{LOW}-{HIGH}</small>" in body
    assert _input_bounds(body, f"value_{image.file_id}")[:2] == (str(LOW), str(HIGH))
    assert f"{LOW}-{HIGH} cells" in body


def test_the_puzzle_list_filter_renders_the_range(admin_app):
    body = admin_app.test_client().get("/puzzles").get_data(as_text=True)
    # The side range is two inputs since the filter became from/to; both
    # carry the range.
    for input_id in ("size_from", "size_to"):
        assert _input_bounds(body, input_id) == (str(LOW), str(HIGH), f"{LOW}-{HIGH}")


def test_the_book_puzzle_step_spans_the_range_in_tabs(admin_app):
    """CARD-122 replaced this step's size-range inputs with the four
    longest-side tabs (AC-216), so the range is now shown as the tabs that
    tile it end to end rather than as two bounded number fields."""
    book_id = admin_app.book_manager.create_book(
        title="Range check", description="d", theme="christmas", target_audience="kids"
    )
    body = admin_app.test_client().get(f"/book/{book_id}/select-puzzles").get_data(as_text=True)

    for input_id in ("size_from", "size_to"):
        assert f'id="{input_id}"' not in body

    # What the page renders, not what BUCKETS holds: the four tab controls the
    # owner can actually press, in order, spanning the range end to end. The
    # pure partition property is tests/property/test_longest_side_buckets.py's
    # and is not restated here (review cycle 1, F-008).
    rendered = [
        html.unescape(label)
        for label in re.findall(r'name="go_bucket" value="([^"]+)"', body)
    ]

    assert rendered == [bucket.label for bucket in BUCKETS]
    assert rendered[0] == f"<={BUCKETS[0].high}", "the first tab must reach down to the floor"
    assert rendered[-1].endswith(f"-{HIGH}"), "the last tab must reach up to the ceiling"


def test_the_admin_app_exposes_the_range_to_templates(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from flask import render_template_string

    from nonogram.admin.app import create_app

    app = create_app()
    with app.test_request_context():
        assert render_template_string("{{ MIN_SIZE }}-{{ MAX_SIZE }}") == f"{LOW}-{HIGH}"


# --- web adapter --------------------------------------------------------------


def test_web_suggestions_default_to_the_shared_range():
    params = inspect.signature(web_metadata.suggest_dimensions).parameters
    assert (params["min_size"].default, params["max_size"].default) == (LOW, HIGH)


def test_both_form_pages_hand_the_range_to_metadata_js():
    tag = (
        f'<script src="/static/metadata.js" data-min-size="{LOW}" '
        f'data-max-size="{HIGH}"></script>'
    )
    assert tag in pages.FORM_PAGE
    source = (SRC / "web" / "pages.py").read_text(encoding="utf-8")
    # FORM_PAGE and form_with_result's page.
    assert source.count('data-max-size="{MAX_SIZE:d}"') == 2


def test_metadata_js_takes_the_range_from_its_script_tag():
    js = (SRC / "web" / "static" / "metadata.js").read_text(encoding="utf-8")
    assert "document.currentScript" in js
    assert not re.search(r"(minSize|maxSize)\s*=\s*\d", js)


# --- AC-4: the print table has to keep up with the range ---------------------


def test_the_print_cell_size_table_covers_the_whole_range():
    """Raising MAX_SIZE fails here until the printed cell size for the new top
    is measured and added (``docs/cell_size.md``), rather than printing an
    extrapolated one."""
    cells = [c for c, _ in layout.CELL_COMFORT_MM]
    assert cells[0] <= LOW and cells[-1] >= HIGH
