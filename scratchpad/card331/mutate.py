"""CARD-331's mutation harness: plant by text, measure the node, restore.

Discipline, every item of which has cost this board a round:

* ``PYTHONDONTWRITEBYTECODE=1`` and ``__pycache__`` swept before **and** after
  every run, so a stale bytecode file cannot be what a verdict is read off.
* each plant is located **by text**, with its occurrence count asserted to be
  exactly 1 before it is applied.
* SHA-256 of every touched file asserted before the plant and after the
  restore, so a half-restored tree cannot be the next measurement's baseline.
* the full environment is inherited (``dict(os.environ, ...)``). A stripped
  ``PATH`` is how a platform-gated decorator turned a killed mutant into a
  false SURVIVED on CARD-330.
* ``-o addopts=`` passed as two argv items, never as one quoted string.
* **0 skipped asserted on every baseline**: asserting the collected count is
  not enough, because a skip keeps the count and removes the assertion.
* the matched control for every plant is the same node, green, measured before
  the plant in this same harness run.

Run from the worktree root. Not a test, and not under ``tests/`` (G-6).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-331")
PYTHON = (
    Path("/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python")
)
MODULE = "tests/test_book_difficulty_dots.py"
HELPER = "tests/helpers/round_ink.py"


@dataclass(frozen=True)
class Mutant:
    name: str
    what: str
    path: str
    old: str
    new: str
    nodes: tuple[str, ...]
    plugin: str | None = None
    extra: dict = field(default_factory=dict)


MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        name="MUT-1",
        what="the VECTOR arm's accounting source goes dead: the writer emits "
        "an empty stream",
        path=MODULE,
        old="        stream=generator.vector_puzzle_page(payload, 1, FIRST_PUZZLE_PAGE, sizes),",
        new="        stream=ContentStream(width_px=layout.width, height_px=layout.height, dpi=DPI),",
        nodes=(
            "TestDifficultyDots_AnArmWhoseMechanismIsDeadFails::"
            "test_each_arms_mechanism_is_still_exercised[vector]",
        ),
    ),
    Mutant(
        name="MUT-2",
        what="the RASTER arm's accounting source goes dead (the claim's other "
        "arm): the puzzle page arrives as operators",
        path=MODULE,
        old="        bitmap=generator._blank_page(payload, 1, FIRST_PUZZLE_PAGE, sizes),",
        new="        bitmap=generator.vector_puzzle_page(payload, 1, FIRST_PUZZLE_PAGE, sizes),",
        nodes=(
            "TestDifficultyDots_AnArmWhoseMechanismIsDeadFails::"
            "test_each_arms_mechanism_is_still_exercised[raster]",
        ),
    ),
    Mutant(
        name="MUT-3",
        what="the corpus is shrunk by ONE page",
        path=MODULE,
        old="        for number, payload in enumerate(payloads, start=1)",
        new="        for number, payload in enumerate(payloads[:-1], start=1)",
        nodes=(
            "TestDifficultyDots_TheVectorArmReadsTheStream::"
            "test_the_corpus_is_one_page_per_puzzle_of_both_books",
        ),
    ),
    Mutant(
        name="MUT-4",
        what="the claim is restated as a statement about a CALL",
        path=MODULE,
        old='''CLAIM_COUNT = (
    "a row carries one dot per tier the project has, and the tier's own "
    "1-based position on that ladder is how many of them are filled in"
)''',
        new='''CLAIM_COUNT = (
    "_draw_difficulty_dots was called with the tier and returned the dots"
)''',
        nodes=(
            "TestDifficultyDots_TheClaimIsAboutThePageNotTheCall::"
            "test_the_claim_is_stated_about_the_page_and_names_no_function",
        ),
    ),
    Mutant(
        name="MUT-5",
        what="the forbidden-name list is padded with a word that names nothing",
        path=MODULE,
        old='''    "monkeypatch",
)''',
        new='''    "monkeypatch",
    "page",
)''',
        nodes=(
            "TestDifficultyDots_TheClaimIsAboutThePageNotTheCall::"
            "test_the_forbidden_names_are_things_that_really_exist",
        ),
    ),
    Mutant(
        name="MUT-6",
        what="the raster arm starts hooking a production attribute",
        path=MODULE,
        old="    drawn = plant(ImageDraw.Draw(page), box)",
        new="    book_pdf_generator._set_band = book_pdf_generator._set_band\n"
        "    drawn = plant(ImageDraw.Draw(page), box)",
        nodes=(
            "TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct::"
            "test_this_arm_hooks_no_production_attribute",
        ),
    ),
    Mutant(
        name="MUT-7",
        what="AC-5, raster medium: one dot too few is declared",
        path=MODULE,
        old="            if drawn.is_filled(index)\n        ]",
        new="            if drawn.is_filled(index) and index > 0\n        ]",
        nodes=(
            "TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct::"
            "test_a_declared_glyph_is_found_as_ink_and_accounted_for",
            "TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct::"
            "test_a_wrong_count_on_the_bitmap_reds_this_arm",
        ),
    ),
    Mutant(
        name="MUT-8",
        what="AC-5, vector medium: one dot too few is declared",
        path=MODULE,
        old="        for dot in declared_dots\n    ]",
        new="        for dot in declared_dots[1:]\n    ]",
        nodes=(
            "TestDifficultyDots_TheVectorArmReadsTheStream::"
            "test_a_declared_glyph_is_found_in_the_stream_and_accounted_for",
            "TestDifficultyDots_TheVectorArmReadsTheStream::"
            "test_a_wrong_count_in_the_stream_reds_this_arm",
        ),
    ),
    Mutant(
        name="MUT-9",
        what="the Bezier flattening is coarsened to 4 segments",
        path=HELPER,
        old="_BEZIER_SEGMENTS = 32",
        new="_BEZIER_SEGMENTS = 4",
        nodes=(
            "TestDifficultyDots_TheVectorArmReadsTheStream::"
            "test_the_flattening_costs_far_less_than_the_tolerance_it_is_read_against",
        ),
    ),
    Mutant(
        name="MUT-10",
        what="the reader stops refusing a shape it cannot analyse (ADR-0039/R2)",
        path=HELPER,
        old='_REFUSED_PATH_OPERATORS = frozenset({"v", "y"})',
        new="_REFUSED_PATH_OPERATORS = frozenset()",
        nodes=(
            "TestDifficultyDots_TheVectorArmReadsTheStream::"
            "test_a_shape_the_reader_cannot_analyse_is_a_failure",
        ),
    ),
    Mutant(
        name="MUT-11",
        what="the vector arm's margin is declared rather than derived",
        path=MODULE,
        old="        derived = (4.0 / math.pi - 1.0) / ROUND_FILL_TOLERANCE",
        new="        derived = 2.0",
        nodes=(
            "TestDifficultyDots_TheVectorArmReadsTheStream::"
            "test_the_closest_a_vector_page_comes_to_a_round_mark_is_derived",
        ),
    ),
    Mutant(
        name="MUT-12",
        what="the arm set silently loses a member: both arms claim RASTER, so "
        "VECTOR has none (CARD-330's dropped-key family)",
        path=MODULE,
        old='        name="vector",\n        medium=PageMedium.VECTOR,',
        new='        name="vector",\n        medium=PageMedium.RASTER,',
        nodes=(
            "TestDifficultyDots_AnArmWhoseMechanismIsDeadFails::"
            "test_there_is_one_arm_per_medium_the_product_can_write",
            "TestDifficultyDots_AnArmWhoseMechanismIsDeadFails::"
            "test_exactly_one_arm_reads_the_medium_the_product_writes_today",
        ),
    ),
    Mutant(
        name="MUT-13",
        what="DECLARED NEGATIVE CONTROL: an arm is renamed and nothing else. "
        "The guard claims one arm per medium, not a set of names, so this "
        "mutant must SURVIVE -- a guard that reddened here would be pinning "
        "a spelling and calling it a medium",
        path=MODULE,
        old='    InstrumentArm(\n        name="raster",',
        new='    InstrumentArm(\n        name="the bitmap arm",',
        nodes=(
            "TestDifficultyDots_AnArmWhoseMechanismIsDeadFails::"
            "test_there_is_one_arm_per_medium_the_product_can_write",
        ),
        extra={"must": "SURVIVED"},
    ),
    Mutant(
        name="MUT-14",
        what="AC-5, raster medium, the VERDICT assertion rather than the count: "
        "the declared boxes are shifted one device pixel, so the counts still "
        "agree and the accounting does not",
        path=MODULE,
        old="            (0, dot)\n            for index, dot in enumerate(drawn.dots)",
        new="            (0, (dot[0] + 1, dot[1], dot[2], dot[3]))\n"
        "            for index, dot in enumerate(drawn.dots)",
        nodes=(
            "TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct::"
            "test_a_declared_glyph_is_found_as_ink_and_accounted_for",
        ),
    ),
    Mutant(
        name="MUT-15",
        what="AC-5, vector medium, the VERDICT assertion rather than the count: "
        "the declared boxes are flipped about the wrong page height, so the "
        "counts still agree and the accounting does not",
        path=MODULE,
        old="        (0, _at_the_streams_places(_declared_in_points(dot, height_px)))",
        new="        (0, _at_the_streams_places(_declared_in_points(dot, height_px + 1)))",
        nodes=(
            "TestDifficultyDots_TheVectorArmReadsTheStream::"
            "test_a_declared_glyph_is_found_in_the_stream_and_accounted_for",
        ),
    ),
    Mutant(
        name="MUT-16",
        what="the page extent the vector accounting flips y about drifts from "
        "the stream's own",
        path=MODULE,
        old="        height_px=layout.height,",
        new="        height_px=layout.height + 1,",
        nodes=(
            "TestDifficultyDots_TheVectorArmReadsTheStream::"
            "test_the_page_extent_this_arm_flips_y_about_is_the_streams_own",
        ),
    ),
    Mutant(
        name="MUT-17",
        what="the raster arm's probe stops noticing that the medium has moved "
        "-- the control's own control",
        path=MODULE,
        old="    if medium is not PageMedium.RASTER:",
        new="    if False:",
        nodes=(
            "TestDifficultyDots_AnArmWhoseMechanismIsDeadFails::"
            "test_each_arms_probe_reports_death_when_its_mechanism_goes",
        ),
    ),
)

COUNT = re.compile(r"(\d+) (passed|failed|error|errors|skipped)")


def sweep() -> None:
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def digest(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def run(nodes: tuple[str, ...], plugin: str | None = None) -> tuple[int, str]:
    sweep()
    argv = [str(PYTHON), "-m", "pytest", "-o", "addopts=", "-q", "-rs", "--tb=line"]
    if plugin:
        argv += ["-p", plugin]
    argv += [f"{MODULE}::{node}" for node in nodes] or [MODULE]
    env = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=str(Path(__file__).resolve().parent),
    )
    done = subprocess.run(
        argv, cwd=str(ROOT), env=env, capture_output=True, text=True
    )
    sweep()
    return done.returncode, done.stdout + done.stderr


def tally(text: str) -> dict[str, int]:
    return {word: int(number) for number, word in COUNT.findall(text)}


def main() -> int:
    sweep()
    print("=== BASELINE: the whole module, as committed")
    code, out = run(())
    counts = tally(out)
    print(f"    exit={code} {counts}")
    assert code == 0, "the committed module is not green"
    assert counts.get("passed", 0) == 189, counts
    assert counts.get("skipped", 0) == 0, f"SKIPS on the baseline: {counts}"
    assert counts.get("failed", 0) == 0, counts

    rows = []
    for mutant in MUTANTS:
        before = digest(mutant.path)
        text = (ROOT / mutant.path).read_text()
        occurrences = text.count(mutant.old)
        assert occurrences == 1, (
            f"{mutant.name}: the plant's text occurs {occurrences} times in "
            f"{mutant.path}, not once"
        )

        # matched control: the same nodes, green, right now
        code, out = run(mutant.nodes, mutant.plugin)
        control = tally(out)
        assert code == 0 and control.get("failed", 0) == 0, (
            f"{mutant.name}: its control node is not green before the plant\n{out}"
        )
        assert control.get("skipped", 0) == 0, f"{mutant.name}: control SKIPPED"
        assert control.get("passed", 0) == len(mutant.nodes), (
            f"{mutant.name}: control collected {control}, wanted "
            f"{len(mutant.nodes)} nodes"
        )

        (ROOT / mutant.path).write_text(text.replace(mutant.old, mutant.new, 1))
        try:
            code, out = run(mutant.nodes, mutant.plugin)
        finally:
            (ROOT / mutant.path).write_text(text)
            sweep()
        after = digest(mutant.path)
        assert after == before, f"{mutant.name}: {mutant.path} not restored"

        counts = tally(out)
        verdict = "KILLED" if counts.get("failed", 0) or code != 0 else "SURVIVED"
        wanted = mutant.extra.get("must", "KILLED")
        assert verdict == wanted, (
            f"{mutant.name} {verdict} and was declared to {wanted}\n{out}"
        )
        lines = [
            line.strip()
            for line in out.splitlines()
            if "test_book_difficulty_dots.py:" in line and ": " in line
        ]
        rows.append((mutant, verdict, counts, lines))
        print(f"\n=== {mutant.name}: {verdict}  {counts}")
        print(f"    {mutant.what}")
        for line in lines[:4]:
            print(f"    red at {line}")

    print("\n=== SUMMARY")
    for mutant, verdict, counts, lines in rows:
        print(f"{mutant.name:8} {verdict:9} {counts}  {mutant.nodes[0].split('::')[-1]}")
    sweep()
    return 0


if __name__ == "__main__":
    sys.exit(main())
