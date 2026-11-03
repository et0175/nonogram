"""CARD-338 AC-2/AC-3: the five-kind census over CARD-329's 20 modules plus
the 22nd, with the probe's own shadow split out of every number.

Not a test and not under ``tests/`` (G-2). Run from the worktree root::

    python scratchpad/card338/census_five_kinds.py                 # five kinds
    python scratchpad/card338/census_five_kinds.py --probe puzzle   # CARD-329's
    python scratchpad/card338/census_five_kinds.py --no-probe       # as committed
    python scratchpad/card338/census_five_kinds.py --only tests/test_book_pdf.py

``scratchpad/card329/measure_probe.py`` is the pattern; this is not an import
of it (a sibling card's scratchpad is not a dependency) and it adds the two
things this card owes: the five-kind probe, and the **split** between a red the
conversion causes and a red the instrument causes.

Discipline, every item of which has cost this board a round:

* the full environment is inherited (``dict(os.environ, ...)``) — a stripped
  ``PATH`` makes a platform-gated test SKIP, which reads as a pass;
* ``-o addopts=`` as **two** argv items, never one quoted string (``addopts =
  "-q"`` in ``pyproject.toml`` otherwise stacks to ``-qq`` and there is no
  count line at all);
* every call is file-scoped, and a zero collected count is an ERROR, not a
  pass (``-k`` selecting nothing exits 0, and a nodeless pytest call collects
  the whole suite);
* ``-rfs`` as **one** flag — ``-rf -rs`` as two silences the first — so every
  skip is attributed by the reason the gate printed, never named from memory;
* ``PYTHONDONTWRITEBYTECODE=1`` and ``__pycache__`` swept at both ends;
* the counts are located by pattern, never by reading the last line.

**``unaccounted``, and why it is a column.** Under ``--tb=line`` a *failure*
prints one ``path:lineno: Exception`` line, which the walk below reads. An
*error* -- one raised in a fixture or at setup -- prints in another shape
(``E   Exception`` under an ERRORS heading), which this walk does **not**
read, and ``-rfs`` leaves errors out of the short summary as well (``-rEfs``
puts them back). So a module's reds can exceed the causes the walk saw. That
difference is printed as ``unaccounted`` rather than left as a silent gap
between two totals: AC-3 forbids an "other" bucket, and a red the classifier
never sees is the quietest "other" there is. Resolve any non-zero
``unaccounted`` by re-running that module with ``-rEfs`` and reading the
ERRORS section; measured on 2026-11-01, all 23 were fixture-raised errors of
mechanisms the failures already name (band 10, memory 13).

**The artefact split (AC-2).** ``monkeypatch.delitem(_RASTER_DECLARATIONS,
kind)`` raises ``KeyError`` when the probe has already removed the key, unless
the site passes ``raising=False``. That red is the instrument's shadow and not
the conversion's, so a downstream card prices the conversion and not the probe.
Every red is classified from its ``--tb=line`` entry; the sites themselves are
derived by ``ast`` in ``derive_delitem_sites.py``.
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path("/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python")
HERE = Path(__file__).resolve().parent

PROBES = {
    "five": "probe_five_kinds",
    "puzzle": "probe_puzzle_operators",  # CARD-329's, for the comparison row
}

# CARD-329's census, module for module, so the two are comparable. Derived
# there by ``scratchpad/card329/derive_populations.py``; quoted here because
# the comparison is against *that* frame.
POPULATION_A = (
    "tests/property/test_book_export_interior.py",
    "tests/test_book_arrange_page_breaks.py",
    "tests/test_book_export_interior_cover.py",
    "tests/test_book_guide_page.py",
    "tests/test_book_interior_face.py",
    "tests/test_book_pdf.py",
    "tests/test_book_pdf_band.py",
    "tests/test_book_pdf_ink_mode.py",
    "tests/test_book_pdf_memory.py",
    "tests/test_book_proof_pages.py",
    "tests/test_book_solved_answer_key.py",
    "tests/test_book_trim_persistence.py",
)
POPULATION_B = (
    "tests/property/test_book_pairing.py",
    "tests/property/test_book_pdf_geometry.py",
    "tests/test_book_cell_size.py",
    "tests/test_book_difficulty_dots.py",
    "tests/test_book_divider_pages_option.py",
    "tests/test_book_pdf_levels.py",
    "tests/test_book_pdf_two_up.py",
    "tests/test_book_puzzle_frame.py",
)
B_HELPER = ("tests/helpers/book_corpus.py",)

#: The third population, derived by ``derive_medium_population.py`` — in
#: neither A nor B, reaching the hazard through the medium decision itself.
POPULATION_THIRD = ("tests/test_book_interior_type_floor.py",)

COUNT = re.compile(r"(\d+) (passed|failed|error|errors|skipped|xfailed|xpassed)")
SKIP_LINE = re.compile(r"^SKIPPED \[(\d+)\] (.+)$", re.M)
TB_LINE = re.compile(r"^(/?\S*\.py):(\d+): (.*)$", re.M)

#: The instrument's own shadow: a ``delitem`` site without ``raising=False``
#: reaching a key the probe has already popped.
ARTEFACT = re.compile(r"monkeypatch\.py:\d+: KeyError: <PageKind\.")


def sweep() -> None:
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def run(path: str, probe: str | None) -> str:
    sweep()
    argv = [str(PYTHON), "-m", "pytest", "-o", "addopts=", "-q", "-rfs", "--tb=line"]
    if probe:
        argv += ["-p", probe]
    argv.append(path)
    # Both scratchpads: this card's probe and CARD-329's, so ``--probe puzzle``
    # runs the SAME instrument that produced the figure being compared against
    # rather than a transcription of it.
    env = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=f"{HERE}{os.pathsep}{HERE.parent / 'card329'}",
    )
    done = subprocess.run(
        argv, cwd=str(ROOT), env=env, capture_output=True, text=True
    )
    sweep()
    return done.stdout + done.stderr


def tally(text: str) -> dict[str, int]:
    return {word: int(number) for number, word in COUNT.findall(text)}


def causes(text: str) -> collections.Counter:
    found: collections.Counter = collections.Counter()
    for where, lineno, message in TB_LINE.findall(text):
        found[f"{Path(where).name}:{lineno}: {message.strip()}"] += 1
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", default="five", choices=sorted(PROBES))
    parser.add_argument("--no-probe", action="store_true")
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--third", action="store_true",
                        help="include the third population (the 22nd module)")
    parser.add_argument("--causes", action="store_true",
                        help="print every red's --tb=line cause, grouped")
    args = parser.parse_args()

    probe = None if args.no_probe else PROBES[args.probe]
    if args.only:
        modules = tuple(args.only)
    else:
        modules = POPULATION_A + POPULATION_B
        if args.third:
            modules += POPULATION_THIRD
    label = f"probe={probe or 'NONE (as committed)'}"
    print(f"=== {label}: {len(modules)} modules, one file-scoped run each\n")

    rows = []
    for path in modules:
        out = run(path, probe)
        counts = tally(out)
        collected = sum(
            counts.get(key, 0)
            for key in ("passed", "failed", "error", "errors", "skipped",
                        "xfailed", "xpassed")
        )
        assert collected, (
            f"{path}: collected NOTHING -- a green exit is not a pass\n{out[-3000:]}"
        )
        red = counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0)
        found = causes(out)
        artefact = sum(n for cause, n in found.items() if ARTEFACT.search(cause))
        skips = SKIP_LINE.findall(out)
        accounted = sum(found.values())
        rows.append((path, counts, red, artefact, found, skips, accounted))
        mark = "RED " if red else "gree"
        # ``unaccounted`` is reds that printed no ``--tb=line`` entry this walk
        # could read -- an ERROR raised outside a test body prints in another
        # shape. AC-3 forbids an "other" bucket, and a red the classifier never
        # SEES is the quietest possible "other", so it is a column here rather
        # than a silent difference between two totals.
        print(
            f"{mark} {path:52} red={red:<4} artefact={artefact:<3} "
            f"conversion={red - artefact:<4} unaccounted={red - accounted:<4}"
            f" passed={counts.get('passed', 0):<5}"
            f" skipped={counts.get('skipped', 0)}"
        )
        for number, reason in skips:
            print(f"        SKIP x{number}: {reason}")
        if args.causes:
            for cause, number in found.most_common():
                tag = "ARTEFACT" if ARTEFACT.search(cause) else "conversion"
                print(f"        x{number:<4} [{tag}] {cause[:160]}")

    total_red = sum(row[2] for row in rows)
    total_artefact = sum(row[3] for row in rows)
    total_pass = sum(row[1].get("passed", 0) for row in rows)
    total_skip = sum(row[1].get("skipped", 0) for row in rows)
    total_unaccounted = sum(row[2] - row[6] for row in rows)
    reds = [row[0] for row in rows if row[2]]
    print(f"\n=== {label}")
    print(f"    modules red:  {len(reds)} / {len(rows)}")
    print(f"    failed+error: {total_red}  (conversion {total_red - total_artefact}"
          f" + probe artefact {total_artefact})")
    print(f"    unaccounted:  {total_unaccounted}  (reds with no --tb=line "
          f"entry this walk could read -- investigate, never bucket)")
    print(f"    passed:       {total_pass}")
    print(f"    skipped:      {total_skip}")
    for path in reds:
        print(f"    RED {path}")
    sweep()
    return 0


if __name__ == "__main__":
    sys.exit(main())
