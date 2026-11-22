"""CARD-525 — where picture puzzles lose their difficulty or fail to generate.

Not a test and not part of the package: a one-shot measurement the owner reads.
It changes no product behaviour and edits nothing under ``src/``.

What it measures
----------------
Every request goes through the admin's own image path, exactly as CARD-517's
image mode does (and with CARD-517's corpus builders, imported, not copied):
``ImageFile.size_fits()`` in "fixed" mode picks the extent, then
``admin.app._generate_image_puzzle`` runs ``orchestrator.generate`` in image
mode with the batch's long-side +-1 retry. Inside that path a picture goes
through these stages (``sourcing.image.generate``): load, ink box, aspect guard,
trim, crop+resize (``binarize``, LANCZOS), threshold or dither (``convert``, with
the degenerate-ink fallback), then the uniqueness solve, up to
``MAX_NUDGE_ATTEMPTS`` pixel nudges, all under one ``GENERATION_BUDGET_SECONDS``
deadline per extent, and finally the grade (``difficulty.classify``, cutoff
90.0, untouched).

1. **Attribution** (``--variant today``): for each request, which stage decided
   it. Made: unique at the conversion, unique after N nudges, or made only at
   a neighbour extent. Failed: cannot fit, aspect refused, abandoned after the
   nudges at every extent tried, or the deadline (on the first solve of the
   conversion, or during the nudges). Easy puzzles also carry the shape of
   their grid: fill, run length, clues per line, left-right symmetry.
2. **Ablation**: the same requests under one change at a time (:data:`VARIANTS`
   says exactly what each changes). A variant is applied by swapping one named
   module attribute for the duration of the run (``unittest.mock.patch``), or
   by wrapping ``sourcing.image.convert`` with one extra step on the grid it
   returns. The source files are never written.
   ``rescue_easy`` (added in review round 1) is per request instead: today's
   puzzle stands unless it is easy, then ``cut_62`` and ``dither_all`` are tried
   and the first non-easy one at or above :data:`RESCUE_EASY_FLOOR` is kept.
   ``--signals`` reports three cheap line-art measurements of each picture
   (:func:`picture_signals`) against which pictures fail.
3. **Similarity** to the picture, two measures. ``smooth_corr`` (added in
   review round 1) is tied to no cut: :func:`smooth_corr`. The first: the ink IoU (filled cells
   in both / filled cells in either) between the puzzle's grid and a
   *reference* grid — the picture's ink box, cropped to the grid's ratio by
   the pipeline's own ``fit_crop_box``, area-averaged (``BOX``) to the grid's
   extent, and filled where at least half the cell is ink. Limits: the
   reference is almost today's threshold conversion, so it favours today and
   the variants near it; it measures cell agreement, not recognisability (an
   outline of a silhouette is recognisable and scores low by construction);
   and on a photograph the reference is itself a poor picture.

Corpus and reproducibility
--------------------------
CARD-517's: the committed picture fixtures (``fixture_pictures``) plus 20
silhouettes drawn from ``IMAGE_CORPUS_SEED`` (``seeded_pictures``), at the
twelve long sides ``IMAGE_SIZES``. Conversion draws no randomness, so the
corpus replays; only the deadline (a wall clock) can move a result, and
``--workers`` above 1 shares the machine between solves, so a run in parallel
can time out where a serial one did not. The fixture count and the request
count are asserted. ``--image-dir`` adds a private folder: the output for it
is aggregate only, and nothing printed or written names a picture.

Usage::

    ./.venv/bin/python scripts/picture_pipeline_experiment.py --pictures 2      # timing run
    ./.venv/bin/python scripts/picture_pipeline_experiment.py --workers 4 --json out.json
    ./.venv/bin/python scripts/picture_pipeline_experiment.py --variant outline --workers 4 --json b.json
    ./.venv/bin/python scripts/picture_pipeline_experiment.py --from-json out.json --from-json b.json --render DIR
"""

from __future__ import annotations

import argparse
import contextlib
import json
import statistics
import sys
import tempfile
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from unittest import mock

import numpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

import measure_difficulty_cutoff as card517  # noqa: E402  (CARD-517's corpus builders)

from nonogram import orchestrator, solver  # noqa: E402
from nonogram.difficulty import Tier, classify  # noqa: E402
from nonogram.errors import NonogramError, SolverTimeout  # noqa: E402
from nonogram.sourcing import image as image_source  # noqa: E402

Grid = list[list[bool]]

#: rescue_easy's similarity floor on :func:`smooth_corr`, fixed before the
#: variant was first run: the 10th percentile of today's made puzzles on the
#: reproducible corpus (fixtures and silhouettes, 343 puzzles), rounded down to
#: two places. An alternative must be at least as close to the picture as the
#: bottom tenth of what the pipeline already ships.
RESCUE_EASY_FLOOR = 0.96  # p10 measured 0.963 (343 puzzles); min 0.628, median 0.989

#: CARD-517's (picture, long side) count for its default corpus (37 pictures
#: x 12 sizes), repeats included. Asserted on a full run so a shrunken corpus
#: fails instead of thinning.
EXPECTED_FULL_REQUESTS = 444


# --- variants ----------------------------------------------------------------


def _despeckle(grid: Grid) -> Grid:
    """Flip isolated cells once: a filled cell with no filled 4-neighbour
    becomes empty; an empty cell whose in-grid 4-neighbours are all filled
    becomes filled. Read from the input grid, so the order does not matter."""
    height, width = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    for r in range(height):
        for c in range(width):
            near = [
                grid[r + dr][c + dc]
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                if 0 <= r + dr < height and 0 <= c + dc < width
            ]
            if grid[r][c] and not any(near):
                out[r][c] = False
            elif not grid[r][c] and near and all(near):
                out[r][c] = True
    return out


def _outline(grid: Grid) -> Grid:
    """Keep a filled cell only when a 4-neighbour is empty or off the grid:
    solid areas become a one-cell outline."""
    height, width = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    for r in range(height):
        for c in range(width):
            if not grid[r][c]:
                continue
            interior = all(
                0 <= r + dr < height and 0 <= c + dc < width and grid[r + dr][c + dc]
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
            )
            if interior:
                out[r][c] = False
    return out


def _fill_holes(grid: Grid) -> Grid:
    """Fill every empty cell not 4-connected to the grid's border: an outline
    drawing becomes a silhouette; a silhouette's enclosed holes close."""
    height, width = len(grid), len(grid[0])
    outside = [[False] * width for _ in range(height)]
    stack = [
        (r, c) for r in range(height) for c in range(width)
        if (r in (0, height - 1) or c in (0, width - 1)) and not grid[r][c]
    ]
    while stack:
        r, c = stack.pop()
        if outside[r][c]:
            continue
        outside[r][c] = True
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < height and 0 <= nc < width and not grid[nr][nc] and not outside[nr][nc]:
                stack.append((nr, nc))
    return [[grid[r][c] or not outside[r][c] for c in range(width)] for r in range(height)]


def _after_convert(step: Callable[[Grid], Grid]):
    """``sourcing.image.convert`` with ``step`` applied to the grid it returns
    (path reported unchanged). Pre-bound to the real function at import, so a
    patched module attribute cannot recurse into itself."""
    real = image_source.convert

    def convert(greyscale, width, height):
        grid, path = real(greyscale, width, height)
        return step(grid), path

    return convert


@dataclass(frozen=True)
class Variant:
    name: str
    changes: str
    #: ``(module, attribute, value)`` swapped for the run.
    patches: tuple[tuple[object, str, object], ...] = field(default=())
    #: rescue_easy only: variants tried, in order, when today's puzzle is easy.
    fallbacks: tuple[str, ...] = ()


VARIANTS: tuple[Variant, ...] = (
    Variant("today", "nothing: the pipeline as it ships"),
    Variant(
        "dither_all",
        "binarisation: Floyd-Steinberg dither for every picture "
        "(sourcing.image.DEFAULT_BINARISATION = DITHER; today the classifier picks, ~all threshold)",
        ((image_source, "DEFAULT_BINARISATION", image_source.DITHER),),
    ),
    Variant(
        "cut_62",
        "threshold cut: a cell is filled at >= ~62% ink instead of >= 50% "
        "(sourcing.image.INK_THRESHOLD 128 -> 96, read by binarize only; the ink box keeps 128)",
        ((image_source, "INK_THRESHOLD", 96),),
    ),
    Variant(
        "cut_37",
        "threshold cut: a cell is filled at >= ~37% ink instead of >= 50% "
        "(sourcing.image.INK_THRESHOLD 128 -> 160, binarize only)",
        ((image_source, "INK_THRESHOLD", 160),),
    ),
    Variant(
        "box_resize",
        "resize filter: area average (BOX) instead of LANCZOS (sourcing.image.RESAMPLING)",
        ((image_source, "RESAMPLING", image_source.Image.Resampling.BOX),),
    ),
    Variant(
        "despeckle",
        "grid clean-up after convert: isolated filled cells emptied, enclosed single holes filled "
        "(one pass; new step, script-only)",
        ((image_source, "convert", _after_convert(_despeckle)),),
    ),
    Variant(
        "outline",
        "grid step after convert: solid interiors emptied, a one-cell outline kept "
        "(new step, script-only)",
        ((image_source, "convert", _after_convert(_outline)),),
    ),
    Variant(
        "fill_holes",
        "grid step after convert: every empty area enclosed by ink is filled, so an outline "
        "drawing becomes a silhouette (new step, script-only)",
        ((image_source, "convert", _after_convert(_fill_holes)),),
    ),
    Variant(
        "nudges_15",
        "retry budget: up to 15 pixel nudges instead of 5 (orchestrator.MAX_NUDGE_ATTEMPTS)",
        ((orchestrator, "MAX_NUDGE_ATTEMPTS", 15),),
    ),
    Variant(
        "deadline_90",
        "deadline: 90 s per extent instead of 30 s (orchestrator.GENERATION_BUDGET_SECONDS)",
        ((orchestrator, "GENERATION_BUDGET_SECONDS", 90.0),),
    ),
    Variant(
        "rescue_easy",
        "per request, designed after reading runs A-C: today's puzzle stands unless it is easy; "
        "then cut_62, then dither_all, are tried at the same predicted extent and the first that "
        "is not easy and has smooth_corr >= RESCUE_EASY_FLOOR replaces it",
        fallbacks=("cut_62", "dither_all"),
    ),
)
VARIANT_BY_NAME = {variant.name: variant for variant in VARIANTS}


@contextlib.contextmanager
def applied(variant: Variant) -> Iterator[None]:
    with contextlib.ExitStack() as stack:
        for module, attribute, value in variant.patches:
            assert hasattr(module, attribute), f"{module!r} has no {attribute}"
            stack.enter_context(mock.patch.object(module, attribute, value))
        yield


# --- measures ----------------------------------------------------------------


def _runs(line: Sequence[bool]) -> list[int]:
    runs, current = [], 0
    for cell in line:
        if cell:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def grid_shape(grid: Grid) -> dict[str, float]:
    """Fill, mean run length as a share of its line, clues per line, and
    left-right mirror agreement."""
    columns = [list(column) for column in zip(*grid, strict=True)]
    lines = [*grid, *columns]
    runs = [(run, len(line)) for line in lines for run in _runs(line)]
    cells = sum(len(row) for row in grid)
    mirror = sum(row[c] == row[-1 - c] for row in grid for c in range(len(row)))
    return {
        "fill": sum(map(sum, grid)) / cells,
        "run_share": statistics.fmean(run / length for run, length in runs) if runs else 0.0,
        "clues_per_line": len(runs) / len(lines),
        "lr_symmetry": mirror / cells,
    }


def reference_grid(path: Path, width: int, height: int) -> Grid:
    """The picture thresholded at the grid's size: ink box, the pipeline's own
    aspect crop, area-averaged, filled where at least half the cell is ink."""
    from PIL import Image

    greyscale = image_source.load_greyscale(path)
    trimmed = greyscale.crop(image_source.ink_bounding_box(greyscale))
    scaled = trimmed.resize(
        (width, height),
        resample=Image.Resampling.BOX,
        box=image_source.fit_crop_box(*trimmed.size, width, height),
    )
    values = numpy.asarray(scaled)
    return [[bool(values[r, c] <= 127) for c in range(width)] for r in range(height)]


def coverage_map(path: Path, width: int, height: int) -> numpy.ndarray:
    """Each cell's ink coverage, 0..1, from the same crop as :func:`reference_grid`."""
    from PIL import Image

    greyscale = image_source.load_greyscale(path)
    trimmed = greyscale.crop(image_source.ink_bounding_box(greyscale))
    scaled = trimmed.resize(
        (width, height),
        resample=Image.Resampling.BOX,
        box=image_source.fit_crop_box(*trimmed.size, width, height),
    )
    return 1.0 - numpy.asarray(scaled, dtype=float) / 255.0


def _smoothed(values: numpy.ndarray) -> numpy.ndarray:
    """3x3 mean, edges padded by repetition."""
    padded = numpy.pad(values, 1, mode="edge")
    height, width = values.shape
    return sum(
        padded[dr : dr + height, dc : dc + width] for dr in range(3) for dc in range(3)
    ) / 9.0


def smooth_corr(grid: Grid, coverage: numpy.ndarray) -> float:
    """The second similarity measure, tied to no cut: the Pearson correlation
    of the grid and the picture's ink coverage, both blurred over 3x3 cells.

    A uniformly thicker or thinner conversion, or a dither whose local ink
    density follows the picture, keeps it high; cells moved to the wrong
    place lower it. 0.0 when either side is constant."""
    left = _smoothed(numpy.asarray(grid, dtype=float)).ravel()
    right = _smoothed(coverage).ravel()
    if left.std() == 0 or right.std() == 0:
        return 0.0
    return float(numpy.corrcoef(left, right)[0, 1])


def similarity(path: Path, grid: Grid) -> dict[str, float]:
    """Both measures for a made grid, at the grid's own extent."""
    height, width = len(grid), len(grid[0])
    return {
        "iou": ink_iou(grid, reference_grid(path, width, height)),
        "smooth_corr": smooth_corr(grid, coverage_map(path, width, height)),
    }


def ink_iou(grid: Grid, reference: Grid) -> float:
    both = either = 0
    for row, ref_row in zip(grid, reference, strict=True):
        for cell, ref in zip(row, ref_row, strict=True):
            both += cell and ref
            either += cell or ref
    return both / either if either else 1.0


# --- one picture, every size, one variant ------------------------------------


def run_picture(variant_name: str, kind: str, index: int, path_text: str, sizes: Sequence[int]) -> list[dict]:
    """Every requested long side of one picture under one variant.

    Returns one dict per request (a repeated extent is skipped, as CARD-517
    does). Top-level so a process pool can call it.
    """
    from nonogram.admin.image_manager import CANNOT_FIT

    variant = VARIANT_BY_NAME[variant_name]
    path = Path(path_text)
    label = f"{kind}-{index:02d}"
    results: list[dict] = []
    made: set[tuple[int, int]] = set()
    for long_side in sizes:
        image = card517._admin_image(path, label, long_side)
        fit = image.size_fits()[0].fit
        base = {
            "variant": variant_name,
            "kind": kind,
            "picture": index,
            "requested": long_side,
            "fit_status": fit.status,
            "predicted": list(fit.extent),
        }
        if fit.status == CANNOT_FIT:
            results.append({**base, "outcome": "failed", "stage": "sizing: cannot fit"})
            continue
        if fit.extent in made:
            # The same puzzle again (conversion is deterministic): kept as a
            # marker for the corpus count, left out of every table (CARD-517).
            results.append({**base, "outcome": "repeat", "stage": "repeat of a smaller size's extent"})
            continue
        made.add(fit.extent)
        row = _attempt(image, fit.extent, variant, path, base)
        if variant.fallbacks and row["outcome"] == "made" and row["tier"] == "easy":
            # rescue_easy: today's puzzle stands unless it is easy; then each
            # fallback is tried in order at the same predicted extent, and the
            # first non-easy one at or above the similarity floor replaces it.
            row["taken_from"] = "today"
            tried = []
            for name in variant.fallbacks:
                other = _attempt(image, fit.extent, VARIANT_BY_NAME[name], path, base)
                tried.append({"variant": name, "outcome": other["outcome"], "tier": other.get("tier"),
                              "smooth_corr": other.get("smooth_corr")})
                if (
                    other["outcome"] == "made"
                    and other["tier"] != "easy"
                    and other["smooth_corr"] >= RESCUE_EASY_FLOOR
                ):
                    other["taken_from"] = name
                    row = other
                    break
            row["tried"] = tried
        results.append(row)
    return results


def _attempt(image, extent, variant: Variant, path: Path, base: dict) -> dict:
    """One admin-path generation of ``image`` at ``extent`` under ``variant``'s
    patches, with spies on the extents tried and the solves made."""
    from nonogram.admin.app import _generate_image_puzzle

    real_generate = orchestrator.generate
    real_solve = solver.solve
    calls: list[dict] = []
    solves = [0]

    def counting_solve(*args, **kwargs):
        solves[0] += 1
        return real_solve(*args, **kwargs)

    def spying_generate(request):
        solves[0] = 0
        started = time.perf_counter()
        entry = {"extent": [request.width, request.height]}
        calls.append(entry)
        try:
            puzzle = real_generate(request)
        except NonogramError as exc:
            entry.update(result=type(exc).__name__, solves=solves[0])
            raise
        finally:
            entry["seconds"] = round(time.perf_counter() - started, 3)
        entry.update(result="made", solves=solves[0])
        return puzzle

    started = time.perf_counter()
    with applied(variant), mock.patch.object(orchestrator, "generate", spying_generate), \
            mock.patch.object(solver, "solve", counting_solve):
        try:
            puzzle, used = _generate_image_puzzle(image, *extent)
        except NonogramError as exc:
            puzzle, used, error = None, None, exc
        else:
            error = None
    row = {**base, "calls": calls, "seconds": round(time.perf_counter() - started, 3)}
    if puzzle is None:
        row.update(outcome="failed", error=type(error).__name__, stage=_failure_stage(error, calls))
        return row
    nudges = puzzle.nudge.attempts
    grid = [list(map(bool, line)) for line in puzzle.grid]
    if list(used) != list(extent):
        stage = "made at a neighbour extent"
    elif nudges:
        stage = "made after nudges"
    else:
        stage = "unique at conversion"
    row.update(
        outcome="made",
        stage=stage,
        used=list(used),
        nudges=nudges,
        binarisation=puzzle.binarisation,
        score=puzzle.difficulty_score,
        tier=classify(puzzle.difficulty_score).value,
        branch_nodes=puzzle.branch_nodes,
        rungs=list(puzzle.strategies),
        shape=grid_shape(grid),
        grid=["".join("#" if cell else "." for cell in line) for line in grid],
        **similarity(path, grid),
    )
    return row


def _failure_stage(error: NonogramError, calls: list[dict]) -> str:
    """Which stage decided a failed request, from the error and the extents tried."""
    name = type(error).__name__
    if name == "ImageNeedsManualCrop":
        return "aspect guard refused"
    if name == "UnreadableImage":
        return "unreadable"
    if isinstance(error, SolverTimeout):
        first = calls[0] if calls else {}
        return (
            "deadline on the conversion's first solve"
            if first.get("solves", 0) <= 1
            else "deadline during the nudges"
        )
    if name == "GenerationAbandoned":
        if any(call.get("result") == "SolverTimeout" for call in calls[1:]):
            return "abandoned (a neighbour then hit the deadline)"
        return "abandoned: not unique after the nudges, every extent"
    return f"other: {name}"


# --- corpus ------------------------------------------------------------------


def corpus(
    scratch: Path, cap: int | None, image_dirs: Sequence[Path], *, public: bool = True
) -> list[tuple[str, list[Path]]]:
    fixtures = card517.fixture_pictures()
    assert len(fixtures) >= card517.MIN_FIXTURES, f"only {len(fixtures)} picture fixtures"
    seeded_count = card517.SEEDED_PICTURES if cap is None else min(cap, card517.SEEDED_PICTURES)
    sources = [
        ("fixture", fixtures[:cap]),
        ("seeded", card517.seeded_pictures(seeded_count, scratch)),
    ]
    if not public:
        sources = []
    for number, folder in enumerate(image_dirs):
        sources.append((f"extra{number}", card517.folder_pictures(folder)[:cap]))
    return sources


def run_variant(
    variant: Variant,
    sources: Sequence[tuple[str, Sequence[Path]]],
    sizes: Sequence[int],
    workers: int,
) -> tuple[list[dict], float]:
    jobs = [
        (variant.name, kind, index, str(path), tuple(sizes))
        for kind, paths in sources
        for index, path in enumerate(paths)
    ]
    started = time.perf_counter()
    rows: list[dict] = []
    if workers <= 1:
        for job in jobs:
            rows += run_picture(*job)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for part in pool.map(run_picture, *zip(*jobs, strict=True)):
                rows += part
    return rows, time.perf_counter() - started


# --- line-art signals (F-002) ------------------------------------------------

#: Pictures are measured at this long side, so the signals do not depend on
#: the file's resolution.
SIGNAL_LONG_SIDE = 400


def picture_signals(path: Path) -> dict[str, float]:
    """Three cheap measurements of the picture itself, before any grid.

    * ``ink_share``: ink pixels (grey < 128, the pipeline's own ink test) over
      the ink box's area.
    * ``stroke``: twice the median erosion depth of the ink pixels (how many
      3x3 erosions a pixel survives), as a share of the ink box's long side:
      the typical stroke width. Thin outlines score low, solid shapes high.
    * ``enclosed``: blank pixels inside the ink box that are not 4-connected to
      its border, over all its blank pixels. An outline drawing encloses its
      interior; a silhouette encloses little.
    """
    from PIL import Image, ImageDraw, ImageFilter

    greyscale = image_source.load_greyscale(path)
    trimmed = greyscale.crop(image_source.ink_bounding_box(greyscale))
    scale = SIGNAL_LONG_SIDE / max(trimmed.size)
    size = (max(1, round(trimmed.width * scale)), max(1, round(trimmed.height * scale)))
    small = trimmed.resize(size, resample=Image.Resampling.BOX)
    mask = small.point(lambda value: 255 if value < image_source.INK_THRESHOLD else 0)
    ink = numpy.asarray(mask) > 0
    depth = numpy.zeros(ink.shape, dtype=int)
    eroded = mask
    for _ in range(SIGNAL_LONG_SIDE):
        current = numpy.asarray(eroded) > 0
        if not current.any():
            break
        depth += current
        eroded = eroded.filter(ImageFilter.MinFilter(3))
    padded = Image.new("L", (size[0] + 2, size[1] + 2), 0)
    padded.paste(mask, (1, 1))
    ImageDraw.floodfill(padded, (0, 0), 128)
    outside = numpy.asarray(padded)[1:-1, 1:-1] == 128
    blank = ~ink
    return {
        "ink_share": float(ink.mean()),
        "stroke": float(2 * numpy.median(depth[ink]) / SIGNAL_LONG_SIDE) if ink.any() else 0.0,
        "enclosed": float((blank & ~outside).sum() / blank.sum()) if blank.any() else 0.0,
    }


def report_signals(today: Sequence[dict], sources: Sequence[tuple[str, Sequence[Path]]]) -> None:
    """Could a cheap signal refuse the failing pictures without refusing good ones?

    A picture is *failing* when more than half of its requests fail today.
    For each signal, every threshold between observed values is tried on the
    fixtures, in the direction that catches failing pictures; the best (most
    caught minus wrongly refused) is reported, then applied unchanged to any
    ``--image-dir`` folder as a held-out check (aggregates only).
    """
    outcome: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in today:
        outcome[(row["kind"], row["picture"])].append(row)
    pictures = []
    for kind, paths in sources:
        if kind == "seeded":
            continue
        for index, path in enumerate(paths):
            rows = outcome[(kind, index)]
            failed = sum(row["outcome"] == "failed" for row in rows)
            tiers = _tiers(rows)
            pictures.append({
                "kind": kind,
                "index": index,
                "name": path.name,
                "failing": failed * 2 > len(rows),
                "failed": failed,
                "requests": len(rows),
                "nontrivial": tiers["medium"] + tiers["hard"],
                **picture_signals(path),
            })
    print("\n== F-002: line-art signals per fixture (failing = more than half its requests fail) ==")
    print(f"  {'fixture':<20} {'failed':>7} {'med+hard':>8} {'ink_share':>9} {'stroke':>7} {'enclosed':>8}")
    for item in pictures:
        if item["kind"] == "fixture":
            print(
                f"  {item['index']:02d} {item['name']:<17} {item['failed']:>3}/{item['requests']:<3}"
                f" {item['nontrivial']:>8} {item['ink_share']:9.3f} {item['stroke']:7.4f} {item['enclosed']:8.3f}"
                f"{'   FAILING' if item['failing'] else ''}"
            )
    fixtures = [item for item in pictures if item["kind"] == "fixture"]
    held_out = [item for item in pictures if item["kind"] != "fixture"]
    if not fixtures:
        print("  the thresholds are fitted on the fixtures; run without --only-image-dir")
        return
    if held_out:
        per = sorted((item["failed"] for item in held_out if item["failed"]), reverse=True)
        print(f"  --image-dir: {len(held_out)} pictures; failures per picture with any: {per};"
              f" failing (more than half): {sum(item['failing'] for item in held_out)}")
    print("\n  best single threshold per signal, chosen on the fixtures; then the same rule on --image-dir")
    for signal in ("ink_share", "stroke", "enclosed"):
        best = None
        values = sorted({item[signal] for item in fixtures})
        cuts = [(a + b) / 2 for a, b in zip(values, values[1:], strict=False)]
        for cut in cuts:
            for below in (True, False):
                refused = [item for item in fixtures if (item[signal] < cut) == below]
                caught = sum(item["failing"] for item in refused)
                wrong = len(refused) - caught
                key = (caught - wrong, -wrong)
                if best is None or key > best[0]:
                    best = (key, cut, below, caught, wrong, sum(item["nontrivial"] for item in refused if not item["failing"]))
        _, cut, below, caught, wrong, lost = best
        failing = sum(item["failing"] for item in fixtures)
        rule = f"{signal} {'<' if below else '>'} {cut:.4f}"
        line = (
            f"  {rule:<22} fixtures: caught {caught}/{failing} failing, wrongly refused {wrong}/{len(fixtures) - failing}"
            f" good (which gave {lost} medium/hard puzzles)"
        )
        if held_out:
            refused = [item for item in held_out if (item[signal] < cut) == below]
            h_caught = sum(item["failing"] for item in refused)
            h_failing = sum(item["failing"] for item in held_out)
            line += (
                f"; --image-dir: caught {h_caught}/{h_failing}, wrongly refused {len(refused) - h_caught}"
                f"/{len(held_out) - h_failing}"
            )
        print(line)
    # Two signals together (both must fire), same search, same held-out check.
    def candidates(signal: str) -> list[tuple[float, bool]]:
        values = sorted({item[signal] for item in fixtures})
        return [((a + b) / 2, below) for a, b in zip(values, values[1:], strict=False) for below in (True, False)]

    def fires(item: dict, signal: str, cut: float, below: bool) -> bool:
        return (item[signal] < cut) == below

    signals = ("ink_share", "stroke", "enclosed")
    best_pair = None
    for first_index, first in enumerate(signals):
        for second in signals[first_index + 1 :]:
            for cut_a, below_a in candidates(first):
                for cut_b, below_b in candidates(second):
                    refused = [
                        item for item in fixtures
                        if fires(item, first, cut_a, below_a) and fires(item, second, cut_b, below_b)
                    ]
                    caught = sum(item["failing"] for item in refused)
                    wrong = len(refused) - caught
                    key = (caught - wrong, -wrong)
                    if best_pair is None or key > best_pair[0]:
                        best_pair = (key, (first, cut_a, below_a), (second, cut_b, below_b), caught, wrong)
    _, rule_a, rule_b, caught, wrong = best_pair
    failing = sum(item["failing"] for item in fixtures)
    text = " and ".join(f"{name} {'<' if below else '>'} {cut:.4f}" for name, cut, below in (rule_a, rule_b))
    line = f"  {text}: fixtures caught {caught}/{failing}, wrongly refused {wrong}/{len(fixtures) - failing}"
    if held_out:
        refused = [item for item in held_out if fires(item, *rule_a) and fires(item, *rule_b)]
        h_caught = sum(item["failing"] for item in refused)
        h_failing = sum(item["failing"] for item in held_out)
        any_failure = [item for item in held_out if item["failed"]]
        line += (
            f"; --image-dir: caught {h_caught}/{h_failing}, wrongly refused {len(refused) - h_caught}"
            f"/{len(held_out) - h_failing}; of its {len(any_failure)} pictures with any failure it refuses"
            f" {sum(item in refused for item in any_failure)}"
        )
    print(line)
    print("  (thresholds fitted on 17 fixtures with 6 failing; the --image-dir columns are the held-out check)")
    if held_out:
        print("  --image-dir failing pictures' signals (aggregate): " + ", ".join(
            f"{signal} median {statistics.median(item[signal] for item in held_out if item['failing']):.4f}"
            f" (n={sum(item['failing'] for item in held_out)})"
            f" vs good {statistics.median(item[signal] for item in held_out if not item['failing']):.4f}"
            for signal in ("ink_share", "stroke", "enclosed")
        ) if any(item["failing"] for item in held_out) else "  --image-dir: no failing picture")


# --- report ------------------------------------------------------------------


def _pct(part: int, whole: int) -> str:
    return f"{100.0 * part / whole:.1f}%" if whole else "-"


def _tiers(rows: Sequence[dict]) -> Counter[str]:
    return Counter(row["tier"] for row in rows if row["outcome"] == "made")


def _is_private(kind: str) -> bool:
    return kind.startswith("extra")


def report_attribution(rows: Sequence[dict], kinds: Sequence[str]) -> None:
    print("\n== AC-1: today's pipeline, which stage decided each request ==")
    for kind in [*kinds, "all public"]:
        subset = [
            row for row in rows
            if (row["kind"] == kind if kind != "all public" else not _is_private(row["kind"]))
        ]
        if not subset:
            continue
        made = [row for row in subset if row["outcome"] == "made"]
        tiers = _tiers(subset)
        print(f"\n[{kind}] requests {len(subset)}, made {len(made)}, failed {len(subset) - len(made)}"
              f" ({_pct(len(subset) - len(made), len(subset))})")
        print(f"  made, tiers: easy {tiers['easy']} / medium {tiers['medium']} / hard {tiers['hard']}"
              f"  ({_pct(tiers['easy'], len(made))} / {_pct(tiers['medium'], len(made))}"
              f" / {_pct(tiers['hard'], len(made))})")
        for stage, count in sorted(Counter(row["stage"] for row in subset).items()):
            print(f"  {stage:<52} {count:>4}")
        paths = Counter(row.get("binarisation") for row in made)
        print(f"  binarisation of made puzzles: {dict(paths)}")
        spent = {
            outcome: sum(row.get("seconds", 0.0) for row in subset if row["outcome"] == outcome)
            for outcome in ("made", "failed")
        }
        print(f"  generation seconds: made {spent['made']:.0f}, failed {spent['failed']:.0f}")
        for stage in sorted({row["stage"] for row in subset if row["outcome"] == "failed"}):
            times = [row.get("seconds", 0.0) for row in subset if row["stage"] == stage]
            print(f"    {stage:<50} n={len(times):<3} seconds: total {sum(times):6.1f},"
                  f" median {statistics.median(times):6.2f}, max {max(times):6.2f}")
        failing = {(row["kind"], row["picture"]) for row in subset if row["outcome"] == "failed"}
        print(f"  pictures with at least one failure: {len(failing)}")
        failed_paths = Counter(row.get("binarisation") for row in subset if row["outcome"] == "failed")
        print(f"  binarisation of failed requests (conversion at the predicted extent): {dict(failed_paths)}")
        fallback = sum(
            row.get("classifier") == image_source.THRESHOLD and row.get("binarisation") == image_source.DITHER
            for row in subset if row["outcome"] == "failed"
        )
        print(f"  ...of which the classifier chose threshold and the blank-grid guard fell back to dither: {fallback}")
        easy = [row["shape"] for row in made if row["tier"] == "easy"]
        harder = [row["shape"] for row in made if row["tier"] != "easy"]
        print("  grid shape, median (easy n=%d | medium+hard n=%d):" % (len(easy), len(harder)))
        for key in ("fill", "run_share", "clues_per_line", "lr_symmetry"):
            left = statistics.median(s[key] for s in easy) if easy else float("nan")
            right = statistics.median(s[key] for s in harder) if harder else float("nan")
            print(f"    {key:<15} {left:6.3f} | {right:6.3f}")
    print("\n  per picture (public kinds only): kind#index  easy/medium/hard/failed")
    by_picture: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        if not _is_private(row["kind"]):
            by_picture[(row["kind"], row["picture"])].append(row)
    line = []
    for (kind, index), subset in sorted(by_picture.items()):
        tiers = _tiers(subset)
        failed = sum(row["outcome"] == "failed" for row in subset)
        line.append(f"{kind[:3]}{index:02d} {tiers['easy']}/{tiers['medium']}/{tiers['hard']}/{failed}")
        if len(line) == 6:
            print("   " + "   ".join(line))
            line = []
    if line:
        print("   " + "   ".join(line))


def report_ablation(by_variant: dict[str, list[dict]], kinds: Sequence[str]) -> None:
    today = {_key(row): row for row in by_variant["today"]}
    for kind in [*kinds, "all public"]:
        def keep(row: dict, kind: str = kind) -> bool:
            return row["kind"] == kind if kind != "all public" else not _is_private(row["kind"])

        if not any(keep(row) for row in by_variant["today"]):
            continue
        print(f"\n== AC-2: ablation [{kind}] (shares of requests; IoU over made puzzles) ==")
        print(f"  {'variant':<12} {'req':>4} {'made':>5} {'fail':>6} {'easy':>6} {'medium':>6} {'hard':>6} {'easy/made':>9}"
              f" {'pics m/h':>8} {'IoU med':>7} {'IoU mean':>8} {'SC med':>6} {'degen':>5}"
              f"   vs today: fail->made (IoU med) made->fail easy->harder harder->easy")
        for name, rows in by_variant.items():
            subset = [row for row in rows if keep(row)]
            made = [row for row in subset if row["outcome"] == "made"]
            tiers = _tiers(subset)
            n = len(subset)
            pictures = {(row["kind"], row["picture"]) for row in made if row["tier"] != "easy"}
            ious = [row["iou"] for row in made]
            degenerate = sum(image_source.is_degenerate(_cells(row)) for row in made)
            rescued: list[float] = []
            moves = Counter()
            movers: dict[str, set] = defaultdict(set)
            for row in subset:
                before = today.get(_key(row))
                if before is None:
                    continue
                was, now = _state(before), _state(row)
                if was == "failed" and now != "failed":
                    moves["fail->made"] += 1
                    movers["fail->made"].add((row["kind"], row["picture"]))
                    rescued.append(row["iou"])
                elif was != "failed" and now == "failed":
                    moves["made->fail"] += 1
                elif was == "easy" and now in ("medium", "hard"):
                    moves["easy->harder"] += 1
                    movers["easy->harder"].add((row["kind"], row["picture"]))
                elif was in ("medium", "hard") and now == "easy":
                    moves["harder->easy"] += 1
            print(
                f"  {name:<12} {n:>4} {len(made):>5} {_pct(n - len(made), n):>6}"
                f" {_pct(tiers['easy'], n):>6} {_pct(tiers['medium'], n):>6} {_pct(tiers['hard'], n):>6}"
                f" {_pct(tiers['easy'], len(made)):>9}"
                f" {len(pictures):>8} {statistics.median(ious) if ious else float('nan'):7.3f}"
                f" {statistics.fmean(ious) if ious else float('nan'):8.3f}"
                f" {statistics.median(row['smooth_corr'] for row in made) if made else float('nan'):6.3f}"
                f" {degenerate:>5}"
                f"   {moves['fail->made']:>10} ({statistics.median(rescued) if rescued else float('nan'):5.2f})"
                f" {moves['made->fail']:>10} {moves['easy->harder']:>12}"
                f" {moves['harder->easy']:>12}"
                f"   [pictures: {len(movers['fail->made'])} rescued, {len(movers['easy->harder'])} made harder]"
            )
    print("\n  pics m/h = distinct pictures with at least one medium or hard puzzle (the honest sample size)")
    print("  SC = smooth_corr, the cut-free measure (grid vs ink coverage, both blurred 3x3, correlated)")
    print("  degen = made puzzles whose grid is under 5% or over 95% ink (sourcing.image.is_degenerate):")
    print("          'made', but not a picture any more")
    print("  variants:")
    for variant in VARIANTS:
        if variant.name in by_variant:
            print(f"    {variant.name:<12} {variant.changes}")


def report_rescue(by_variant: dict[str, list[dict]], kinds: Sequence[str]) -> None:
    """What rescue_easy did, request by request, against today."""
    if "rescue_easy" not in by_variant:
        return
    today = {_key(row): row for row in by_variant["today"]}
    print("\n== rescue_easy: the requests it changed ==")
    for kind in kinds:
        rows = [row for row in by_variant["rescue_easy"] if row["kind"] == kind]
        changed = [row for row in rows if row.get("taken_from") not in (None, "today")]
        easy_today = [row for row in rows if row.get("taken_from") is not None]
        sources = Counter(row["taken_from"] for row in changed)
        per_picture = Counter(row["picture"] for row in changed)
        before = [today[_key(row)] for row in changed]
        print(f"  [{kind}] easy today {len(easy_today)}, replaced {len(changed)} ({dict(sources)}),"
              f" tiers now {dict(Counter(row['tier'] for row in changed))}, on {len(per_picture)} pictures,"
              f" most from one picture {max(per_picture.values(), default=0)}")
        if changed:
            for measure in ("iou", "smooth_corr"):
                print(f"    {measure:<11} of the replaced requests: today median"
                      f" {statistics.median(row[measure] for row in before):.3f} -> "
                      f"{statistics.median(row[measure] for row in changed):.3f}")
        if not _is_private(kind):
            print(f"    changed per picture: {dict(sorted(per_picture.items()))}")
        for fallback in ("cut_62", "dither_all"):
            part = [row for row in changed if row["taken_from"] == fallback]
            if not part:
                continue
            was = [today[_key(row)] for row in part]
            pictures = Counter(row["picture"] for row in part)
            below = sum(row["smooth_corr"] < RESCUE_EASY_FLOOR for row in was)
            sc_up_iou_down = sum(
                row["smooth_corr"] > old["smooth_corr"] and row["iou"] < old["iou"]
                for row, old in zip(part, was, strict=True)
            )
            line = (
                f"    by {fallback}: {len(part)} replaced on {len(pictures)} pictures,"
                f" tiers {dict(Counter(row['tier'] for row in part))};"
                f" IoU {statistics.median(row['iou'] for row in was):.3f} -> {statistics.median(row['iou'] for row in part):.3f},"
                f" smooth_corr {statistics.median(row['smooth_corr'] for row in was):.3f}"
                f" -> {statistics.median(row['smooth_corr'] for row in part):.3f};"
                f" today's grid already below the floor {below}; smooth_corr up while IoU down {sc_up_iou_down}"
            )
            if not _is_private(kind):
                line += f"; per picture {dict(sorted(pictures.items()))}"
            print(line)
        # The cut_62-only form, from the saved whole-corpus cut_62 run: the same
        # request at the same predicted extent converts the same way, so its
        # row is what rescue_easy's cut_62 attempt would have produced.
        if "cut_62" in by_variant:
            cut = {_key(row): row for row in by_variant["cut_62"] if row["kind"] == kind}
            form = []
            for row in rows:
                old = today[_key(row)]
                other = cut.get(_key(row))
                take = (
                    old["outcome"] == "made" and old["tier"] == "easy" and other is not None
                    and other["outcome"] == "made" and other["tier"] != "easy"
                    and other["smooth_corr"] >= RESCUE_EASY_FLOOR
                )
                form.append((other, old) if take else (old, None))
            made = [new for new, _ in form if new["outcome"] == "made"]
            replaced = [(new, old) for new, old in form if old is not None]
            easy = sum(new["tier"] == "easy" for new in made)
            line = (
                f"    cut_62-only form: easy {easy}/{len(made)} ({_pct(easy, len(made))}), replaced {len(replaced)}"
                f" on {len({new['picture'] for new, _ in replaced})} pictures,"
                f" tiers {dict(Counter(new['tier'] for new, _ in replaced))}"
            )
            if replaced:
                line += (
                    f"; IoU {statistics.median(old['iou'] for _, old in replaced):.3f}"
                    f" -> {statistics.median(new['iou'] for new, _ in replaced):.3f},"
                    f" smooth_corr {statistics.median(old['smooth_corr'] for _, old in replaced):.3f}"
                    f" -> {statistics.median(new['smooth_corr'] for new, _ in replaced):.3f}"
                )
            print(line)


def _report_replay(first: Sequence[dict], again: Sequence[dict]) -> None:
    """Each saved run re-ran 'today': say how many requests came out differently."""
    before = {_key(row): (_state(row), row.get("score")) for row in first}
    shared = [row for row in again if _key(row) in before]
    changed = {_key(row) for row in shared if before[_key(row)] != (_state(row), row.get("score"))}
    print(f"replay of 'today': {len(shared)} rows shared with the first run, {len(changed)} differ",
          file=sys.stderr)


def _cells(row: dict) -> Grid:
    return [[cell == "#" for cell in line] for line in row["grid"]]


def annotate_failures(by_variant: dict[str, list[dict]], sources: Sequence[tuple[str, Sequence[Path]]]) -> None:
    """For each failed request: which binarisation path its conversion took at
    the predicted extent (under that request's variant), and which path the
    classifier alone would pick. Deterministic and cheap (one conversion)."""
    paths = {(kind, index): path for kind, items in sources for index, path in enumerate(items)}
    for name, rows in by_variant.items():
        with applied(VARIANT_BY_NAME[name]):
            for row in rows:
                if row["outcome"] != "failed" or "predicted" not in row or row["stage"].startswith("sizing"):
                    continue
                path = paths[(row["kind"], row["picture"])]
                row["binarisation"] = image_source.binarisation_for(path, *row["predicted"])
                row["classifier"] = image_source.classify_binarisation(image_source.load_greyscale(path))


def backfill_similarity(by_variant: dict[str, list[dict]], sources: Sequence[tuple[str, Sequence[Path]]]) -> None:
    """Rows saved before ``smooth_corr`` existed get it now, from their stored grid."""
    paths = {(kind, index): path for kind, items in sources for index, path in enumerate(items)}
    for rows in by_variant.values():
        for row in rows:
            if row["outcome"] == "made" and "smooth_corr" not in row:
                row.update(similarity(paths[(row["kind"], row["picture"])], _cells(row)))


def _key(row: dict) -> tuple:
    return (row["kind"], row["picture"], row["requested"])


def _state(row: dict) -> str:
    return row["tier"] if row["outcome"] == "made" else row["outcome"]


# --- renders -------------------------------------------------------------------


def render(
    by_variant: dict[str, list[dict]],
    sources: Sequence[tuple[str, Sequence[Path]]],
    out_dir: Path,
    long_sides: Sequence[int],
    kinds: Sequence[str],
    variants: Sequence[str] = (),
    changed: str | None = None,
) -> list[tuple[str, str]]:
    """Picture | today | each variant, one PNG per (picture, long side).

    ``variants`` limits the panels; ``changed`` renders only the requests where
    that variant's outcome or tier differs from today's, at every size."""
    from PIL import Image, ImageDraw, ImageFont

    out_dir.mkdir(parents=True, exist_ok=True)
    panel, label_h, pad = 420, 54, 16
    names = [
        variant.name for variant in VARIANTS
        if variant.name in by_variant and (not variants or variant.name in variants or variant.name == "today")
    ]
    columns = 4
    rows_n = -(-(len(names) + 1) // columns)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
        small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    except OSError:
        font = small = ImageFont.load_default()
    # Keyed by the long side of the extent the admin predicted, not the size
    # asked for: a picture moved to Large at 10 makes its 30-long puzzle there.
    lookup = {(name, row["kind"], row["picture"], max(row["predicted"])): row
              for name, rows in by_variant.items() for row in reversed(rows) if "predicted" in row}
    written: list[tuple[str, str]] = []
    for kind, paths in sources:
        if kind not in kinds:
            continue
        for index, path in enumerate(paths):
            sides = long_sides
            if changed is not None:
                sides = sorted({side for (name, k, i, side) in lookup if name == changed and k == kind and i == index})
            for long_side in sides:
                if (names[0], kind, index, long_side) not in lookup:
                    continue
                if changed is not None and _state(lookup[(changed, kind, index, long_side)]) == _state(
                    lookup[("today", kind, index, long_side)]
                ):
                    continue
                sheet = Image.new("RGB", (columns * (panel + pad) + pad, rows_n * (panel + label_h + pad) + pad), "white")
                draw = ImageDraw.Draw(sheet)
                tiles: list[tuple[str, Image.Image]] = []
                picture = image_source.load_greyscale(path).convert("RGB")
                picture.thumbnail((panel, panel))
                tiles.append(("picture", picture))
                for name in names:
                    row = lookup[(name, kind, index, long_side)]
                    tiles.append((_caption(name, row), _grid_tile(row, path, panel)))
                for slot, (caption, tile) in enumerate(tiles):
                    x = pad + (slot % columns) * (panel + pad)
                    y = pad + (slot // columns) * (panel + label_h + pad)
                    first, _, second = caption.partition("\n")
                    draw.text((x, y), first, fill="black", font=font)
                    draw.text((x, y + 26), second, fill="#444444", font=small)
                    sheet.paste(tile, (x + (panel - tile.width) // 2, y + label_h + (panel - tile.height) // 2))
                name = f"{kind}-{index:02d}-long{long_side}.png"
                sheet.save(out_dir / name)
                note = ""
                if changed is not None:
                    note = f", {changed} took its grid from {lookup[(changed, kind, index, long_side)].get('taken_from')}"
                written.append((name, f"{kind} #{index:02d} ({path.name}){note}", long_side))
    return written


def write_index(out_dir: Path, written: Sequence[tuple[str, str, int]], names: Sequence[str]) -> None:
    """``index.html``: what each sheet shows, then the sheets themselves, large."""
    import html

    legend = "".join(
        f"<li><b>{html.escape(v.name)}</b>: {html.escape(v.changes)}</li>" for v in VARIANTS if v.name in names
    )
    items = "".join(
        f"<h2>{html.escape(label)}, long side {long_side}</h2>"
        f"<p>{html.escape(sheet)}: the picture, then today's grid, then one grid per variant.</p>"
        f'<img src="{html.escape(sheet)}" style="max-width:100%">'
        for sheet, label, long_side in written
    )
    out_dir.joinpath("index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>CARD-525 renders</title>"
        "<body style='font-family:sans-serif;background:#fff;color:#111;margin:16px'>"
        "<h1>CARD-525: picture, today's grid, and each variant's grid</h1>"
        "<p>Each sheet: the picture (top left), then one panel per variant. The panel title says the tier "
        "and score, or FAILED. Black grid = the puzzle made (after any nudges). Red grid = the conversion "
        "that did not become a puzzle. Below the title: extent used, the stage that decided it, and IoU "
        "(ink overlap with the picture thresholded at the grid's size; 1.0 = same cells).</p>"
        f"<ul>{legend}</ul>{items}</body>",
        encoding="utf-8",
    )


def _caption(name: str, row: dict) -> str:
    if row["outcome"] == "made":
        w, h = row["used"]
        source = f" (from {row['taken_from']})" if row.get("taken_from") not in (None, "today") else ""
        return (
            f"{name}{source}: {row['tier'].upper()} {row['score']:.1f}\n"
            f"{w}x{h}, {row['stage']}, IoU {row['iou']:.2f}, SC {row['smooth_corr']:.2f}"
        )
    return f"{name}: FAILED\n{row['stage']}"


def _grid_tile(row: dict, path: Path, panel: int):
    from PIL import Image, ImageDraw

    if row["outcome"] == "made":
        grid = _cells(row)
        colour = "black"
    else:
        width, height = row["predicted"]
        with applied(VARIANT_BY_NAME[row["variant"]]):
            try:
                grid = image_source.generate(path, width, height, None)
            except NonogramError:
                grid = [[False] * width for _ in range(height)]
        colour = "#b00020"  # the conversion that did not become a puzzle
    height, width = len(grid), len(grid[0])
    cell = max(4, panel // max(width, height))
    tile = Image.new("RGB", (width * cell + 1, height * cell + 1), "white")
    draw = ImageDraw.Draw(tile)
    for r, line in enumerate(grid):
        for c, filled in enumerate(line):
            box = (c * cell, r * cell, (c + 1) * cell, (r + 1) * cell)
            draw.rectangle(box, fill=colour if filled else "white", outline="#cccccc")
    return tile


# --- main ----------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", action="append", default=[], help="default: every variant")
    parser.add_argument("--pictures", type=int, default=None, help="at most this many per source (timing)")
    parser.add_argument("--sizes", type=int, nargs="+", default=list(card517.IMAGE_SIZES))
    parser.add_argument("--image-dir", type=Path, action="append", default=[])
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--only-image-dir", action="store_true",
        help="run the --image-dir folders alone, without the fixtures and silhouettes",
    )
    parser.add_argument("--json", type=Path, default=None, help="write every row here")
    parser.add_argument(
        "--from-json", type=Path, action="append", default=[],
        help="report/render saved runs (repeatable; each holds 'today', the first file's is used)",
    )
    parser.add_argument("--render", type=Path, default=None, help="write side-by-side sheets here")
    parser.add_argument("--render-sizes", type=int, nargs="+", default=[20, 30])
    parser.add_argument("--render-kinds", nargs="+", default=["fixture"])
    parser.add_argument("--render-variants", nargs="+", default=[], help="panels to show (default all)")
    parser.add_argument("--render-changed", default=None, help="only requests this variant changed")
    parser.add_argument("--signals", action="store_true", help="also report the line-art signals")
    args = parser.parse_args(argv)

    names = args.variant or [variant.name for variant in VARIANTS]
    unknown = set(names) - VARIANT_BY_NAME.keys()
    if unknown:
        parser.error(f"unknown variant(s): {sorted(unknown)}")
    if "today" not in names:
        names = ["today", *names]

    with tempfile.TemporaryDirectory(prefix="card525-silhouettes-") as scratch:
        sources = corpus(Path(scratch), args.pictures, args.image_dir, public=not args.only_image_dir)
        kinds = [kind for kind, _ in sources]
        if args.from_json:
            by_variant = {}
            for saved_path in args.from_json:
                saved = json.loads(saved_path.read_text(encoding="utf-8"))["rows"]
                if "today" in by_variant:
                    _report_replay(by_variant["today"], saved["today"])
                for name, rows in saved.items():
                    if name in names:
                        # A file adds only the picture kinds not already
                        # loaded: the first file's rows win, and files over
                        # different corpora (public, --image-dir) combine.
                        have = {row["kind"] for row in by_variant.get(name, [])}
                        by_variant.setdefault(name, []).extend(row for row in rows if row["kind"] not in have)
        else:
            by_variant = {}
            for name in names:
                rows, seconds = run_variant(VARIANT_BY_NAME[name], sources, args.sizes, args.workers)
                by_variant[name] = rows
                print(f"  variant {name:<12} {len(rows):>4} requests  {seconds:7.1f}s", file=sys.stderr, flush=True)
            if args.pictures is None and not args.image_dir and list(args.sizes) == list(card517.IMAGE_SIZES):
                considered = len(by_variant["today"])
                assert considered == EXPECTED_FULL_REQUESTS, (
                    f"{considered} (picture, size) pairs, expected {EXPECTED_FULL_REQUESTS}: the corpus changed"
                )
            if args.json is not None:
                args.json.write_text(json.dumps({"seed": card517.IMAGE_CORPUS_SEED, "sizes": args.sizes,
                                                 "workers": args.workers, "rows": by_variant}), encoding="utf-8")
        repeats = sum(row["outcome"] == "repeat" for row in by_variant["today"])
        by_variant = {
            name: [row for row in rows if row["outcome"] != "repeat"] for name, rows in by_variant.items()
        }
        counts = {name: len(rows) for name, rows in by_variant.items()}
        assert len(set(counts.values())) == 1, f"variants saw different request sets: {counts}"
        print("\n== corpus ==")
        print(f"silhouette seed {card517.IMAGE_CORPUS_SEED}; sizes {args.sizes}; workers {args.workers}")
        for kind, paths in sources:
            print(f"pictures ({kind}) {len(paths)}")
        print(f"requests per variant {counts['today']} (plus {repeats} repeats of an extent already made, not counted)")
        backfill_similarity(by_variant, sources)
        annotate_failures(by_variant, sources)
        report_attribution(by_variant["today"], kinds)
        report_ablation(by_variant, kinds)
        report_rescue(by_variant, kinds)
        if args.signals:
            report_signals(by_variant["today"], sources)
        if args.render is not None:
            written = render(
                by_variant, sources, args.render, args.render_sizes, args.render_kinds,
                args.render_variants, args.render_changed,
            )
            print(f"\nrendered {len(written)} sheets to {args.render}", file=sys.stderr)
            write_index(args.render, written, [name for name in by_variant])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
