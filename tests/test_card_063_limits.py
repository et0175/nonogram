"""CARD-063: the supported grid size range is defined once, in
``nonogram.limits``, and every enforced bound reads it (AC-2, AC-4). The
import-guard half (AC-3) lives with the guard in ``tests/test_cli.py``.
"""

import ast
import inspect
import re
from pathlib import Path

import pytest
from PIL import Image as PILImage

from nonogram import difficulty, limits
from nonogram.admin.batch_generator import BatchGenerator
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
    assert difficulty.MIN_SUPPORTED_CELLS == LOW * LOW
    assert difficulty.MAX_SUPPORTED_CELLS == HIGH * HIGH


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


@pytest.mark.parametrize(
    "name", ["image_preview.html", "puzzles_list.html", "book_select_puzzles.html"]
)
def test_admin_templates_take_the_range_from_jinja_globals(name):
    source = (TEMPLATES / name).read_text(encoding="utf-8")
    assert 'min="{{ MIN_SIZE }}"' in source and 'max="{{ MAX_SIZE }}"' in source
    assert not re.search(r'min="10"|max="30"|\b10-30\b', source)


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
