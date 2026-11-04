"""CARD-338 AC-2/AC-3: the five-kind census over CARD-329's 20 modules plus
the 22nd, with the ``delitem`` residue labelled as its own share of every
number -- a share OF the conversion's cost, never a deduction from it.

Not a test and not under ``tests/`` (G-2). Run from the worktree root::

    python scratchpad/card338/census_five_kinds.py                 # five kinds
    python scratchpad/card338/census_five_kinds.py --probe puzzle   # CARD-329's
    python scratchpad/card338/census_five_kinds.py --no-probe       # as committed
    python scratchpad/card338/census_five_kinds.py --only tests/test_book_pdf.py

``scratchpad/card329/measure_probe.py`` is the pattern; this is not an import
of it (a sibling card's scratchpad is not a dependency) and it adds the two
things this card owes: the five-kind probe, and the **split** of the
``delitem`` residue out of a number that is the conversion's in full.

Discipline, every item of which has cost this board a round:

* the full environment is inherited (``dict(os.environ, ...)``) — a stripped
  ``PATH`` makes a platform-gated test SKIP, which reads as a pass;
* ``-o addopts=`` as **two** argv items, never one quoted string (``addopts =
  "-q"`` in ``pyproject.toml`` otherwise stacks to ``-qq`` and there is no
  count line at all);
* every call is file-scoped, and a zero collected count is an ERROR, not a
  pass (``-k`` selecting nothing exits 0, and a nodeless pytest call collects
  the whole suite);
* ``-rEfs`` as **one** flag — ``-rf -rs`` as two silences the first, and
  ``-rfs`` without the ``E`` leaves ERRORs out of the short summary, which is
  how this card's own first walk under-counted 233 reds as 210 — so every skip
  is attributed by the reason the gate printed, never named from memory, and
  every error is in the summary as well as in the ERRORS section;
* ``PYTHONDONTWRITEBYTECODE=1`` and ``__pycache__`` swept at both ends;
* the counts are located by pattern, never by reading the last line.

**``unaccounted``, why it is a column, and why it is now a GATE.** Under
``--tb=line`` a *failure* prints one ``path:lineno: Exception`` line, which
``causes()`` reads. An *error* -- one raised in a fixture, at setup or at
teardown -- prints in another shape (``E   Exception`` under an ERRORS
heading), which that walk does **not** read, and ``-rfs`` without the ``E``
leaves errors out of the short summary as well. That is how this card's own
first walk saw 210 of 233 reds: 23 fixture-raised errors (band 10, memory 13)
printed where nothing was looking.

Both halves are closed here rather than disclosed in prose. ``error_causes()``
parses the ERRORS section into the **same** ``x<n> [tag] <cause>`` dump shape
the failures use, so ``classify_reds.py`` sees every red and an unclassified
one exits non-zero there; and ``unaccounted`` -- reds this walk could attribute
to no cause at all -- makes **this** script exit non-zero. AC-3 forbids an
"other" bucket, and a red the classifier never sees is the quietest "other"
there is, so neither number is advisory text any more.

**The ``delitem`` split (AC-2), and the framing this card RETRACTED.**
``monkeypatch.delitem(_RASTER_DECLARATIONS, kind)`` raises ``KeyError`` when
the key it names is already gone, unless the site passes ``raising=False``.
This script used to call that red "the instrument's shadow and not the
conversion's" and print ``conversion = red - artefact``. **That framing is
measured FALSE and is withdrawn** (ADR-0039/R4: a figure recomputed and refuted
is retracted everywhere it was written, the executable places included):
``fidelity_to_the_end_state.py`` ran the same modules against a tree whose five
entries are **deleted in src/ with no probe loaded at all** and counted the
**identical** KeyErrors. The probe's own artefact is therefore **0**, and these
reds are the conversion's residue -- a downstream card that subtracts them
under-prices itself by 13 over the 21 modules (5 + 1 + 7).

So the column below is named for what it counts, ``delitem``, and it is printed
beside a ``conversion`` figure that is the **full** red count, not the
difference. ``classify_reds.py``'s M1 rule carries the same verdict with the
same attribution. The sites themselves are derived by ``ast`` in
``derive_delitem_sites.py``.
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

#: The ``delitem`` residue: a site without ``raising=False`` reaching a key
#: that is gone. **Not** the instrument's shadow -- measured identical on a
#: tree with the five entries deleted in src/ and no probe loaded, so this is a
#: labelled SHARE of the conversion's cost and never a deduction from it.
DELITEM = re.compile(r"monkeypatch\.py:\d+: KeyError: <PageKind\.")

#: The reds that print under the ERRORS heading instead of as a ``--tb=line``
#: entry, parsed so the classifier sees them too (see the docstring).
ERRORS_HEADING = re.compile(r"^=+ ERRORS =+$", re.M)
HEADING = re.compile(r"^=+ [^=\n]+ =+$", re.M)
ERROR_HEAD = re.compile(r"^_+ ERROR (?P<what>.+?) _+$", re.M)
ERROR_MESSAGE = re.compile(r"^E\s{3}(?P<message>.*)$", re.M)


def sweep() -> None:
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def run(path: str, probe: str | None) -> str:
    sweep()
    # ``-rEfs`` as ONE flag: the ``E`` is this card's own finding -- ``-rfs``
    # omits ERRORs from the short summary, which under-counted 233 as 210.
    argv = [str(PYTHON), "-m", "pytest", "-o", "addopts=", "-q", "-rEfs", "--tb=line"]
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


def error_causes(text: str, path: str) -> collections.Counter:
    """The ERRORS section's causes, in the SAME shape ``causes()`` returns.

    One entry per ``ERROR at <phase> of <node>`` header, keyed by the first
    ``E   `` line under it and by the module (every run here is file-scoped, so
    the module is the path that was run). The node is deliberately **left out**
    of the key so identical mechanisms group instead of splitting one per test.
    """
    found: collections.Counter = collections.Counter()
    module = Path(path).name
    start = ERRORS_HEADING.search(text)
    if not start:
        return found
    rest = text[start.end():]
    following = HEADING.search(rest)
    block = rest[: following.start()] if following else rest
    heads = list(ERROR_HEAD.finditer(block))
    for index, head in enumerate(heads):
        end = heads[index + 1].start() if index + 1 < len(heads) else len(block)
        message = ERROR_MESSAGE.search(block[head.end():end])
        phase = head.group("what").split(" of ")[0]
        said = message.group("message").strip() if message else "<no E line printed>"
        found[f"{module}: ERROR {phase}: {said}"] += 1
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
        found.update(error_causes(out, path))
        delitem = sum(n for cause, n in found.items() if DELITEM.search(cause))
        skips = SKIP_LINE.findall(out)
        accounted = sum(found.values())
        rows.append((path, counts, red, delitem, found, skips, accounted))
        mark = "RED " if red else "gree"
        # ``delitem`` is a labelled SHARE of ``conversion``, not a deduction
        # from it: the artefact framing that printed ``red - artefact`` here is
        # withdrawn (see the docstring), so ``conversion`` is the full red count
        # and these two columns are not meant to add up to it.
        #
        # ``unaccounted`` is reds this walk could attribute to no cause at all,
        # now that the ERRORS section is parsed as well as the ``--tb=line``
        # entries. AC-3 forbids an "other" bucket and a red the classifier never
        # SEES is the quietest possible "other", so it is both a column and this
        # script's exit code.
        print(
            f"{mark} {path:52} red={red:<4} delitem={delitem:<3} "
            f"conversion={red:<4} unaccounted={red - accounted:<4}"
            f" passed={counts.get('passed', 0):<5}"
            f" skipped={counts.get('skipped', 0)}"
        )
        for number, reason in skips:
            print(f"        SKIP x{number}: {reason}")
        if args.causes:
            for cause, number in found.most_common():
                tag = "delitem" if DELITEM.search(cause) else "conversion"
                print(f"        x{number:<4} [{tag}] {cause[:160]}")

    total_red = sum(row[2] for row in rows)
    total_delitem = sum(row[3] for row in rows)
    total_pass = sum(row[1].get("passed", 0) for row in rows)
    total_skip = sum(row[1].get("skipped", 0) for row in rows)
    total_unaccounted = sum(row[2] - row[6] for row in rows)
    reds = [row[0] for row in rows if row[2]]
    print(f"\n=== {label}")
    print(f"    modules red:  {len(reds)} / {len(rows)}")
    print(f"    failed+error: {total_red}  (ALL {total_red} the conversion's; "
          f"{total_delitem} of them delitem residue, measured identical with the "
          f"five entries deleted in src/ and NO probe loaded -- a share, not a "
          f"deduction)")
    print(f"    unaccounted:  {total_unaccounted}  (reds this walk could "
          f"attribute to no cause -- investigate, never bucket)")
    print(f"    passed:       {total_pass}")
    print(f"    skipped:      {total_skip}")
    for path in reds:
        print(f"    RED {path}")
    sweep()
    if total_unaccounted > 0:
        print(f"\nFAIL: {total_unaccounted} red(s) carry no cause this walk could "
              f"read, so the classifier cannot see them. Re-run the module(s) above "
              f"with -rEfs and read the ERRORS section; a red nobody classifies is "
              f"the 'other' bucket AC-3 forbids.")
        return 1
    if total_unaccounted < 0:
        # The other direction, gated for the same reason: more causes than reds
        # means the walk is reading a `path.py:NN:` line that is not a red -- a
        # defect in THIS instrument, and one a count comparison would otherwise
        # hide inside a per-module column nobody adds up.
        print(f"\nFAIL: this walk read {-total_unaccounted} more cause(s) than "
              f"there are reds, so at least one `path.py:NN:` line it counted is "
              f"not a red. Fix the walk before quoting any number here.")
        return 1
    print("\nOK: every red carries a cause the classifier can read "
          "(unaccounted=0).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
