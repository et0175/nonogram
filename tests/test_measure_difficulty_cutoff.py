"""``scripts/measure_difficulty_cutoff.py``'s image mode (CARD-517).

The script is a measurement, not a package module, so it is loaded from its
path. One test, on a two-picture, two-size corpus: the full run is minutes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PIL import Image

import nonogram.admin.app as admin_app

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "measure_difficulty_cutoff.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("measure_difficulty_cutoff", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module by name
    spec.loader.exec_module(module)
    return module


def test_image_mode_scores_pictures_through_the_admin_path_and_self_checks(
    tmp_path, monkeypatch, capsys
):
    script = _load_script()
    calls = []
    real = admin_app._generate_image_puzzle

    def spy(image, width, height, may_start=None):
        calls.append((width, height))
        return real(image, width, height, may_start=may_start)

    monkeypatch.setattr(admin_app, "_generate_image_puzzle", spy)

    fixtures = script.fixture_pictures()
    assert len(fixtures) >= script.MIN_FIXTURES
    for path in fixtures:
        with Image.open(path) as picture:
            assert min(picture.size) >= script.FIXTURE_MIN_SIDE
    sources = [
        ("fixture", fixtures[:1]),
        ("seeded", script.seeded_pictures(1, tmp_path)),
    ]
    # The drawn silhouettes replay from the seed, byte for byte.
    again_dir = tmp_path / "again"
    again_dir.mkdir()
    again = script.seeded_pictures(1, again_dir)
    assert again[0].read_bytes() == sources[1][1][0].read_bytes()

    rows, failures, _ = script.build_image_corpus(sources, sizes=(10, 20), verbose=False)

    assert len(rows) + sum(failures.values()) == 4
    assert len(rows) >= 3
    # Every puzzle came from the admin's own image-batch generator.
    assert len(calls) == len(rows)
    assert {row.kind for row in rows} == {"fixture", "seeded"}
    script._self_check(rows)  # AC-2: the in-force row agrees with classify
    script.report_image(rows, failures, 0.0, sources, (10, 20))
    out = capsys.readouterr().out
    assert "cutoff sweep: easy / medium / hard shares" in out
    assert "90 *" in out
    # No picture's file name reaches the output.
    assert fixtures[0].stem not in out
