"""``scripts/picture_pipeline_experiment.py`` (CARD-525): a smoke test.

The script is a measurement, not a package module, so it is loaded from its
path. One fixture at one size, two variants: the full run is an hour.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import nonogram.admin.app as admin_app
from nonogram import orchestrator
from nonogram.sourcing import image as image_source

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "picture_pipeline_experiment.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("picture_pipeline_experiment", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module by name
    spec.loader.exec_module(module)
    return module


def test_variants_run_through_the_admin_path_and_leave_the_pipeline_unchanged(monkeypatch, capsys):
    script = _load_script()
    calls = []
    real = admin_app._generate_image_puzzle

    def spy(image, width, height, may_start=None):
        calls.append((width, height))
        return real(image, width, height, may_start=may_start)

    monkeypatch.setattr(admin_app, "_generate_image_puzzle", spy)
    shipped = (image_source.INK_THRESHOLD, image_source.convert, orchestrator.MAX_NUDGE_ATTEMPTS)

    picture = script.card517.fixture_pictures()[0]
    today = script.run_picture("today", "fixture", 0, str(picture), (10,))
    thicker = script.run_picture("cut_37", "fixture", 0, str(picture), (10,))
    cleaned = script.run_picture("despeckle", "fixture", 0, str(picture), (10,))

    # Every request went through the admin's own image-batch generator.
    assert len(calls) == 3
    # The variants are undone after the run: the shipped pipeline is intact.
    assert (image_source.INK_THRESHOLD, image_source.convert, orchestrator.MAX_NUDGE_ATTEMPTS) == shipped
    (row,) = today
    assert row["outcome"] == "made" and row["tier"] in {"easy", "medium", "hard"}
    assert row["iou"] > 0.8
    # The variant was really applied: a lower cut fills more cells.
    assert thicker[0]["shape"]["fill"] > row["shape"]["fill"]
    reference = script.reference_grid(picture, *row["used"])
    assert script.ink_iou(reference, reference) == 1.0

    by_variant = {"today": today, "cut_37": thicker, "despeckle": cleaned}
    script.report_attribution(today, ["fixture"])
    script.report_ablation(by_variant, ["fixture"])
    out = capsys.readouterr().out
    assert "AC-1" in out and "AC-2" in out and "cut_37" in out
    assert picture.stem not in out  # no picture's file name reaches the output
